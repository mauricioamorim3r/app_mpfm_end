from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session, selectinload

from ..models import ConfigParameter, ConfigSnapshot, Event, IngestionBatch, MeasurementPoint, RawFile, TechnicalReference
from ..schemas import BatchOperationalAnalysisSummary, FlowXMemorialItemSummary, OperationalAnalysisFindingSummary, ProposedAnalysisParameterSummary


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_DOCS_DIR = PROJECT_ROOT / 'referencias_doc'

FIXED_PARAMETER_PATTERNS = (
    'application version',
    'application checksum',
    'software',
    'serial nr',
    'meter serial',
    'meter model',
    'meter manufacturer',
    'high high limit',
    'hi hi limit',
    'hi limit',
    'lo limit',
    'lo lo limit',
    'full scale',
    'low fail',
    'high fail',
    'meter factor',
    'k factor',
    'molar mass method',
    'heating value method',
    'pipe exp coef',
    'device exp coef',
)

OPERATIONAL_UPDATE_PATTERNS = (
    'methane',
    'ethane',
    'propane',
    'butane',
    'pentane',
    'nitrogen',
    'carbon dioxide',
    'relative density',
    'specific gravity',
    'base density',
    'meter density',
    'observed density',
    'heating value',
    'wobbe',
    'shrink',
    'encolh',
    'gor',
    'solub',
    'solution',
)

FLOW_RATE_KEYS = ('base volume flow rate', 'gross volume flow rate', 'mass flow rate', 'energy flow rate')


@dataclass
class FindingBuilder:
    findings: list[OperationalAnalysisFindingSummary]
    counter: int = 0

    def add(self, **kwargs) -> None:
        self.counter += 1
        self.findings.append(OperationalAnalysisFindingSummary(id=f'finding-{self.counter}', **kwargs))


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = ' '.join(str(value).split())
    return text or None


def _number(value: str | None) -> float | None:
    text = _clean(value)
    if not text:
        return None
    matches = re.findall(r'[+-]?\d+(?:[.,]\d+)?', text)
    if not matches:
        return None
    try:
        return float(matches[-1].replace(',', '.'))
    except ValueError:
        return None


def _norm_text(value: str | None) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def _value_equal(left: str | None, right: str | None, tolerance: float = 0.001) -> bool:
    left_number = _number(left)
    right_number = _number(right)
    if left_number is not None and right_number is not None:
        return abs(left_number - right_number) <= tolerance
    return _norm_text(left) == _norm_text(right)


def _parameter_text(parameter: ConfigParameter) -> str:
    return _norm_text(f'{parameter.section} {parameter.parameter_key} {parameter.parameter_label}')


def _matches(parameter: ConfigParameter, patterns: tuple[str, ...]) -> bool:
    text = _parameter_text(parameter)
    return any(pattern in text for pattern in patterns)


def _snapshot_parameters(snapshot: ConfigSnapshot) -> dict[str, ConfigParameter]:
    return {parameter.parameter_key: parameter for parameter in snapshot.parameters}


def _point_for_tag(session: Session, tag: str | None) -> MeasurementPoint | None:
    if not tag:
        return None
    points = session.query(MeasurementPoint).filter(MeasurementPoint.tag == tag).all()
    active = [point for point in points if point.is_active]
    if len(active) == 1:
        return active[0]
    if len(points) == 1:
        return points[0]
    return None


def _point_label(point: MeasurementPoint | None, tag: str | None = None) -> str | None:
    if point is None:
        return tag
    return f'{point.cv_id} / {point.tag} - {point.measurement_point_name}'


def _previous_snapshot(session: Session, snapshot: ConfigSnapshot) -> ConfigSnapshot | None:
    query = (
        session.query(ConfigSnapshot)
        .options(selectinload(ConfigSnapshot.parameters), selectinload(ConfigSnapshot.file))
        .filter(ConfigSnapshot.asset_id == snapshot.asset_id, ConfigSnapshot.id != snapshot.id)
    )
    if snapshot.snapshot_at is not None:
        previous = query.filter(ConfigSnapshot.snapshot_at < snapshot.snapshot_at).order_by(ConfigSnapshot.snapshot_at.desc(), ConfigSnapshot.id.desc()).first()
        if previous is not None:
            return previous
    return query.filter(ConfigSnapshot.id < snapshot.id).order_by(ConfigSnapshot.id.desc()).first()


def _previous_snapshot_by_file_type(session: Session, snapshot: ConfigSnapshot, detected_types: set[str]) -> ConfigSnapshot | None:
    query = (
        session.query(ConfigSnapshot)
        .options(selectinload(ConfigSnapshot.parameters), selectinload(ConfigSnapshot.file))
        .join(RawFile, ConfigSnapshot.file_id == RawFile.id)
        .filter(ConfigSnapshot.asset_id == snapshot.asset_id, ConfigSnapshot.id != snapshot.id, RawFile.detected_type.in_(detected_types))
    )
    if snapshot.snapshot_at is not None:
        previous = query.filter(ConfigSnapshot.snapshot_at < snapshot.snapshot_at).order_by(ConfigSnapshot.snapshot_at.desc(), ConfigSnapshot.id.desc()).first()
        if previous is not None:
            return previous
    return query.filter(ConfigSnapshot.id < snapshot.id).order_by(ConfigSnapshot.id.desc()).first()


def _batch_snapshots(session: Session, batch_id: int) -> list[ConfigSnapshot]:
    return (
        session.query(ConfigSnapshot)
        .options(selectinload(ConfigSnapshot.parameters), selectinload(ConfigSnapshot.file), selectinload(ConfigSnapshot.asset))
        .join(RawFile, ConfigSnapshot.file_id == RawFile.id)
        .filter(RawFile.batch_id == batch_id)
        .order_by(ConfigSnapshot.id)
        .all()
    )


def _batch_events(session: Session, batch_id: int) -> list[Event]:
    return (
        session.query(Event)
        .options(selectinload(Event.file), selectinload(Event.asset))
        .join(RawFile, Event.file_id == RawFile.id)
        .filter(RawFile.batch_id == batch_id)
        .order_by(Event.occurred_at.desc().nullslast(), Event.id.desc())
        .all()
    )


def _event_for_change(events: list[Event], parameter: ConfigParameter) -> Event | None:
    label = _norm_text(parameter.parameter_label)
    key = _norm_text(parameter.parameter_key.split('.')[-1])
    for event in events:
        message = _norm_text(event.message)
        if event.event_type == 'parameter_changed' and (label in message or key in message):
            return event
    return None


def _first_param(snapshot: ConfigSnapshot, patterns: tuple[str, ...]) -> ConfigParameter | None:
    for parameter in snapshot.parameters:
        if _matches(parameter, patterns):
            return parameter
    return None


def _compare_xml_txt(session: Session, builder: FindingBuilder, snapshots: list[ConfigSnapshot]) -> None:
    xml_by_tag: dict[str, list[ConfigSnapshot]] = {}
    config_snapshots = [snapshot for snapshot in snapshots if snapshot.file and snapshot.file.detected_type == 'configuration_report']
    run_reports = [snapshot for snapshot in snapshots if snapshot.file and snapshot.file.detected_type == 'run_report']
    for snapshot in snapshots:
        if not snapshot.file or snapshot.file.detected_type != 'production_xml' or not snapshot.device_name:
            continue
        xml_by_tag.setdefault(snapshot.device_name, []).append(snapshot)

    for report in run_reports:
        tag = report.device_name
        point = _point_for_tag(session, tag)
        matching_xml = xml_by_tag.get(tag or '', [])
        builder.add(
            category='Consistencia XML x TXT',
            check_name='Ponto de medicao presente nas fontes do dia',
            status='ok' if matching_xml else 'attention',
            severity='high' if not matching_xml else 'info',
            cv_id=point.cv_id if point else None,
            tag=tag,
            measurement_point=_point_label(point, tag),
            source_file=report.file.original_name if report.file else None,
            source_a='TXT Run report',
            source_b='XML 001/002/003',
            observed_value=tag,
            reference_value=', '.join(sorted({xml.file.original_name for xml in matching_xml if xml.file})) or None,
            evidence='O Meter ID do TXT foi confrontado com COD_TAG_PONTO_MEDICAO dos XML de producao.',
            recommendation=None if matching_xml else 'Verificar se o XML 001/002/003 do mesmo ponto foi enviado no dia.',
        )
        for key in FLOW_RATE_KEYS:
            parameter = _first_param(report, (key,))
            if parameter is None:
                continue
            builder.add(
                category='Consistencia XML x TXT',
                check_name=f'{parameter.parameter_label}: equivalente direto no XML',
                status='not_available',
                severity='medium',
                cv_id=point.cv_id if point else None,
                tag=tag,
                measurement_point=_point_label(point, tag),
                source_file=report.file.original_name if report.file else None,
                source_a='TXT Run report',
                source_b='XML 001/002/003',
                observed_value=parameter.normalized_value,
                evidence=f'{parameter.parameter_label} foi extraido do TXT, mas os XML atuais trazem parametrizacao/cadastro e alarmes, nao o total operacional equivalente.',
                recommendation='Manter este item como pendencia de conciliacao caso exista XML operacional com totais fiscais no pacote oficial.',
            )

    software_xml = next((param for snapshot_list in xml_by_tag.values() for snapshot in snapshot_list for param in snapshot.parameters if param.parameter_label == 'DSC_VERSAO_SOFTWARE'), None)
    software_txt = next((param for snapshot in config_snapshots for param in snapshot.parameters if _norm_text(param.parameter_label) == 'software'), None)
    if software_xml is not None and software_txt is not None:
        builder.add(
            category='Consistencia XML x TXT',
            check_name='Versao de software do Flow-X',
            status='ok' if _value_equal(software_xml.normalized_value, software_txt.normalized_value) else 'critical',
            severity='critical',
            source_file=software_xml.snapshot.file.original_name if software_xml.snapshot.file else None,
            source_a='XML DSC_VERSAO_SOFTWARE',
            source_b='TXT Configuration / Module Software',
            observed_value=software_xml.normalized_value,
            reference_value=software_txt.normalized_value,
            evidence='Comparacao entre versao declarada no XML de producao e versao do modulo no relatorio de configuracao.',
            recommendation=None if _value_equal(software_xml.normalized_value, software_txt.normalized_value) else 'Abrir verificacao de versao/aprovacao do software antes de aceitar a carga.',
        )


def _check_fixed_parameters(builder: FindingBuilder, session: Session, snapshots: list[ConfigSnapshot], events: list[Event]) -> None:
    config_snapshots = [snapshot for snapshot in snapshots if snapshot.file and snapshot.file.detected_type in {'configuration_report', 'parameters_xml'}]
    for snapshot in config_snapshots:
        previous = _previous_snapshot_by_file_type(session, snapshot, {snapshot.file.detected_type})
        if previous is None:
            builder.add(
                category='Parametrizacao fixa CV',
                check_name='Base anterior para comparacao',
                status='not_available',
                severity='medium',
                source_file=snapshot.file.original_name if snapshot.file else None,
                observed_value=str(snapshot.snapshot_at) if snapshot.snapshot_at else None,
                evidence='Nao existe snapshot anterior salvo para este ativo; a carga atual passa a servir como base local para proximas comparacoes.',
                recommendation='Definir baseline oficial ou carregar dia anterior para detectar alteracoes de parametrizacao fixa.',
            )
            continue
        previous_parameters = _snapshot_parameters(previous)
        compared = 0
        changed = 0
        for parameter in snapshot.parameters:
            if not _matches(parameter, FIXED_PARAMETER_PATTERNS):
                continue
            previous_parameter = previous_parameters.get(parameter.parameter_key)
            if previous_parameter is None:
                continue
            compared += 1
            if _value_equal(parameter.normalized_value, previous_parameter.normalized_value):
                continue
            changed += 1
            event = _event_for_change(events, parameter)
            builder.add(
                category='Parametrizacao fixa CV',
                check_name=parameter.parameter_label,
                status='critical',
                severity='critical',
                source_file=snapshot.file.original_name if snapshot.file else None,
                source_a=previous.file.original_name if previous.file else 'snapshot anterior',
                source_b=snapshot.file.original_name if snapshot.file else 'snapshot atual',
                observed_value=parameter.normalized_value,
                reference_value=previous_parameter.normalized_value,
                actor=event.actor if event else None,
                source_ip=event.source_ip if event else None,
                occurred_at=event.occurred_at if event else None,
                evidence=event.message if event else parameter.evidence_excerpt or 'Diferenca detectada entre snapshots salvos.',
                recommendation='Registrar justificativa, aprovador e evidencia de autorizacao da alteracao antes de fechar a divergencia.',
            )
        if not compared:
            builder.add(
                category='Parametrizacao fixa CV',
                check_name='Parametros fixos com chave equivalente anterior',
                status='not_available',
                severity='medium',
                source_file=snapshot.file.original_name if snapshot.file else None,
                source_a=previous.file.original_name if previous.file else 'snapshot anterior',
                source_b=snapshot.file.original_name if snapshot.file else 'snapshot atual',
                evidence='Houve snapshot anterior para o ativo, mas os parametros fixos rastreados ainda nao tiveram chave equivalente suficiente para comparacao direta.',
                recommendation='Confirmar baseline oficial e normalizar chaves de parametros fixos por run/tag para ampliar a comparacao automatica.',
            )
        if compared and not changed:
            builder.add(
                category='Parametrizacao fixa CV',
                check_name='Parametros fixos comparados com snapshot anterior',
                status='ok',
                severity='info',
                source_file=snapshot.file.original_name if snapshot.file else None,
                source_a=previous.file.original_name if previous.file else 'snapshot anterior',
                source_b=snapshot.file.original_name if snapshot.file else 'snapshot atual',
                observed_value=f'{compared} parametro(s) verificado(s)',
                evidence='Nao foram encontradas alteracoes nos parametros fixos rastreados.',
            )


def _check_pam_ranges(session: Session, builder: FindingBuilder, snapshots: list[ConfigSnapshot]) -> None:
    run_reports = [snapshot for snapshot in snapshots if snapshot.file and snapshot.file.detected_type == 'run_report']
    for report in run_reports:
        tag = report.device_name
        point = _point_for_tag(session, tag)
        flow_parameter = _first_param(report, ('base volume flow rate',)) or _first_param(report, ('gross volume flow rate',))
        value = _number(flow_parameter.normalized_value if flow_parameter else None)
        range_refs = [] if point is None else [ref for ref in point.reference_parameters if ref.reference_kind in {'pam_range', 'measurement_range'} or 'pam' in ref.parameter_key.lower()]
        reference = next((ref for ref in range_refs if ref.min_value is not None or ref.max_value is not None), None)
        if reference is None:
            builder.add(
                category='Faixa PAM',
                check_name='Faixa minima/maxima obrigatoria',
                status='critical',
                severity='critical',
                cv_id=point.cv_id if point else None,
                tag=tag,
                measurement_point=_point_label(point, tag),
                source_file=report.file.original_name if report.file else None,
                observed_value=flow_parameter.normalized_value if flow_parameter else None,
                unit=flow_parameter.unit if flow_parameter else None,
                evidence='O ponto possui vazao operacional no TXT, mas nao ha faixa minima/maxima PAM cadastrada de forma estruturada para validar conformidade.',
                recommendation='Cadastrar Qmin/Qmax da PAM aplicavel ao medidor; este item permanece obrigatorio e bloqueante para conclusao da analise.',
            )
            continue
        status = 'ok'
        if value is None or (reference.min_value is not None and value < reference.min_value) or (reference.max_value is not None and value > reference.max_value):
            status = 'critical'
        builder.add(
            category='Faixa PAM',
            check_name=reference.parameter_label,
            status=status,
            severity='critical',
            cv_id=point.cv_id if point else None,
            tag=tag,
            measurement_point=_point_label(point, tag),
            source_file=report.file.original_name if report.file else None,
            observed_value=flow_parameter.normalized_value if flow_parameter else None,
            reference_value=f'{reference.min_value or "-"} a {reference.max_value or "-"}',
            unit=reference.unit,
            evidence='Comparacao da vazao operacional do TXT com a faixa minima/maxima cadastrada para a PAM.',
            recommendation=None if status == 'ok' else 'Investigar operacao fora da faixa aprovada pela PAM e registrar tratamento metrologico.',
        )


def _check_operational_updates(builder: FindingBuilder, session: Session, snapshots: list[ConfigSnapshot], events: list[Event]) -> None:
    for snapshot in snapshots:
        if not snapshot.file or snapshot.file.detected_type not in {'run_report', 'configuration_report', 'production_xml'}:
            continue
        previous = _previous_snapshot(session, snapshot)
        previous_parameters = _snapshot_parameters(previous) if previous is not None else {}
        found = 0
        changed = 0
        for parameter in snapshot.parameters:
            if not _matches(parameter, OPERATIONAL_UPDATE_PATTERNS):
                continue
            found += 1
            previous_parameter = previous_parameters.get(parameter.parameter_key)
            if previous_parameter is None:
                continue
            if _value_equal(parameter.normalized_value, previous_parameter.normalized_value):
                continue
            changed += 1
            event = _event_for_change(events, parameter)
            builder.add(
                category='Atualizacoes operacionais',
                check_name=parameter.parameter_label,
                status='attention',
                severity='high',
                tag=snapshot.device_name,
                source_file=snapshot.file.original_name if snapshot.file else None,
                source_a=previous.file.original_name if previous and previous.file else 'snapshot anterior',
                source_b=snapshot.file.original_name if snapshot.file else 'snapshot atual',
                observed_value=parameter.normalized_value,
                reference_value=previous_parameter.normalized_value,
                actor=event.actor if event else None,
                source_ip=event.source_ip if event else None,
                occurred_at=event.occurred_at if event else None,
                evidence=event.message if event else parameter.evidence_excerpt or 'Valor operacional alterado entre snapshots.',
                recommendation='Confirmar origem da atualizacao operacional e manter evidencia junto ao fechamento da analise.',
            )
        if found and previous is not None and not changed:
            builder.add(
                category='Atualizacoes operacionais',
                check_name='Cromatografia/densidade/GOR/fatores monitorados',
                status='ok',
                severity='info',
                tag=snapshot.device_name,
                source_file=snapshot.file.original_name if snapshot.file else None,
                observed_value=f'{found} valor(es) monitorado(s)',
                evidence='Nao foram detectadas alteracoes nos valores operacionais monitorados contra o snapshot anterior.',
            )

    for event in events:
        if event.event_type != 'parameter_changed':
            continue
        message = _norm_text(event.message)
        if not any(pattern in message for pattern in OPERATIONAL_UPDATE_PATTERNS):
            continue
        builder.add(
            category='Atualizacoes operacionais',
            check_name='Evento de alteracao operacional',
            status='attention',
            severity=event.severity,
            source_file=event.file.original_name if event.file else None,
            observed_value=event.new_value,
            reference_value=event.old_value,
            actor=event.actor,
            source_ip=event.source_ip,
            occurred_at=event.occurred_at,
            evidence=event.message,
            recommendation='Vincular o evento ao motivo operacional/metrologico antes de concluir a analise diaria.',
        )


@lru_cache(maxsize=1)
def _pdf_reference_hints() -> list[FlowXMemorialItemSummary]:
    items: list[FlowXMemorialItemSummary] = []
    if not REFERENCE_DOCS_DIR.exists():
        return items
    manual_names = [path.name for path in REFERENCE_DOCS_DIR.glob('Flow-X*.pdf')]
    pam_names = [path.name for path in REFERENCE_DOCS_DIR.glob('PAM*.pdf')]
    if manual_names:
        items.append(
            FlowXMemorialItemSummary(
                title='Memorial Flow-X - documentos do fabricante',
                source_ref=', '.join(manual_names[:4]),
                summary='Foram localizados manuais de usuario, configuracao gas metric, liquid e software para compor o memorial descritivo do Flow-X/C.',
                evidence='Usar esses manuais como fonte para arquitetura do computador de vazao, versoes, configuracao de gas/liquido, alarmes, comunicacao e trilha de auditoria.',
            )
        )
    if pam_names:
        items.append(
            FlowXMemorialItemSummary(
                title='Referencias PAM/Dimel disponiveis',
                source_ref=', '.join(pam_names[:8]) + ('...' if len(pam_names) > 8 else ''),
                summary=f'{len(pam_names)} PDF(s) de PAM/Dimel foram encontrados para apoiar faixas de medicao e aprovacao metrologica.',
                evidence='As faixas Qmin/Qmax precisam ser cadastradas de forma estruturada por ponto/tecnologia antes de liberar conclusao automatica de conformidade PAM.',
            )
        )
    return items


def _memorial_from_catalog(session: Session) -> list[FlowXMemorialItemSummary]:
    references = (
        session.query(TechnicalReference)
        .filter(TechnicalReference.category.in_(['flowx', 'pam', 'metrology', 'regulatory']))
        .order_by(TechnicalReference.topic_key)
        .limit(8)
        .all()
    )
    items = [
        FlowXMemorialItemSummary(
            title=reference.title,
            source_ref=reference.source_ref,
            summary=reference.summary,
            evidence=reference.source_excerpt,
        )
        for reference in references
    ]
    items.extend(_pdf_reference_hints())
    return items


def _proposed_parameters() -> list[ProposedAnalysisParameterSummary]:
    return [
        ProposedAnalysisParameterSummary(parameter_key='software_checksum', parameter_label='Versao e checksum do software', reason='Confirma aderencia do Flow-X/C ao software aprovado e detecta troca de firmware/configuracao.'),
        ProposedAnalysisParameterSummary(parameter_key='meter_factor_k_factor', parameter_label='Meter factor, K-factor e curva', reason='Impacta diretamente totalizacao e deve ser rastreado por medidor e faixa.'),
        ProposedAnalysisParameterSummary(parameter_key='input_scaling_failure_limits', parameter_label='Escalas e limites de falha dos transmissores', reason='Mudancas em full scale, low fail e high fail alteram interpretacao de pressao, temperatura e dP.'),
        ProposedAnalysisParameterSummary(parameter_key='calculation_standards', parameter_label='Metodos AGA/API/ISO e unidades', reason='Garante que calculo, compressibilidade, poder calorifico e unidades permanecem conforme referencia.'),
        ProposedAnalysisParameterSummary(parameter_key='access_security_audit', parameter_label='Login, logout, ajuste de hora e seguranca', reason='Relaciona autoria, IP e janela operacional com alteracoes de parametros.'),
    ]


def build_operational_analysis(session: Session, batch_id: int) -> BatchOperationalAnalysisSummary:
    batch = session.query(IngestionBatch).filter(IngestionBatch.id == batch_id).one_or_none()
    if batch is None:
        raise ValueError(f'Batch {batch_id} nao encontrado.')
    snapshots = _batch_snapshots(session, batch_id)
    events = _batch_events(session, batch_id)
    builder = FindingBuilder(findings=[])
    _compare_xml_txt(session, builder, snapshots)
    _check_fixed_parameters(builder, session, snapshots, events)
    _check_pam_ranges(session, builder, snapshots)
    _check_operational_updates(builder, session, snapshots, events)
    if not builder.findings:
        builder.add(
            category='Analise operacional',
            check_name='Dados disponiveis',
            status='not_available',
            severity='medium',
            evidence='Nenhum snapshot operacional/configuracao foi encontrado neste batch para gerar analise.',
            recommendation='Verificar filtros de FC/Meter ID ou arquivos enviados.',
        )
    return BatchOperationalAnalysisSummary(
        batch_id=batch.id,
        source_name=batch.source_name,
        generated_at=datetime.utcnow(),
        findings=builder.findings,
        memorial=_memorial_from_catalog(session),
        proposed_parameters=_proposed_parameters(),
    )