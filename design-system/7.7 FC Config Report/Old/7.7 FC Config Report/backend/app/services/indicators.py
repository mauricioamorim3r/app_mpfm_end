import json
import re
from datetime import datetime
from pathlib import Path
from string import Formatter

from sqlalchemy import delete
from sqlalchemy.orm import Session, selectinload

from ..models import Asset, ConfigParameter, ConfigSnapshot, Event, IndicatorRecord, IndicatorRule, ReferenceRecord


INDICATOR_RULES_PATH = Path(__file__).resolve().parent.parent / 'reference_data' / 'indicator_rules.json'
NUMBER_PATTERN = re.compile(r'-?\d+(?:\.\d+)?')
CHROMATOGRAPHY_COMPONENTS: list[tuple[str, str, tuple[str, ...]]] = [
    ('methane', 'Metano', ('methane', 'metano', 'c1')),
    ('ethane', 'Etano', ('ethane', 'etano', 'c2')),
    ('propane', 'Propano', ('propane', 'propano', 'c3')),
    ('i-butane', 'i-Butano', ('i-butane', 'ibutane', 'iso butane', 'isobutane', 'ic4', 'i-c4')),
    ('n-butane', 'n-Butano', ('n-butane', 'nbutane', 'normal butane', 'n butane', 'nc4', 'n-c4')),
    ('i-pentane', 'i-Pentano', ('i-pentane', 'ipentane', 'iso pentane', 'isopentane', 'ic5', 'i-c5')),
    ('n-pentane', 'n-Pentano', ('n-pentane', 'npentane', 'normal pentane', 'n pentane', 'nc5', 'n-c5')),
    ('hexane+', 'Hexano+', ('hexane+', 'hexane plus', 'c6+', 'hexane', 'heptane')),
    ('nitrogen', 'Nitrogênio', ('nitrogen', 'nitrogeno', 'n2')),
    ('carbon dioxide', 'CO2', ('carbon dioxide', 'carbondioxide', 'co2')),
]


def _load_seed_rules() -> list[dict]:
    if not INDICATOR_RULES_PATH.exists():
        return []
    return json.loads(INDICATOR_RULES_PATH.read_text(encoding='utf-8'))


def seed_indicator_rules(session: Session) -> None:
    existing_rules = {rule.rule_key: rule for rule in session.query(IndicatorRule).all()}
    created = False
    for rule in _load_seed_rules():
        if rule['rule_key'] in existing_rules:
            continue
        session.add(
            IndicatorRule(
                rule_key=rule['rule_key'],
                name=rule['name'],
                applies_to_asset_key=rule.get('applies_to_asset_key'),
                rule_type=rule['rule_type'],
                category=rule['category'],
                severity=rule['severity'],
                target_field=rule.get('target_field'),
                match_text=rule.get('match_text'),
                expected_value=rule.get('expected_value'),
                min_value=rule.get('min_value'),
                max_value=rule.get('max_value'),
                threshold_count=rule.get('threshold_count', 1),
                description_template=rule['description_template'],
                recommendation=rule.get('recommendation'),
                enabled=rule.get('enabled', True),
                is_default=rule.get('is_default', True),
                source_label=rule.get('source_label', 'seed'),
            )
        )
        created = True
    if created:
        session.commit()


def _parse_numeric(value: str | None) -> float | None:
    if not value:
        return None
    match = NUMBER_PATTERN.search(value.replace(',', '.'))
    if match is None:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _safe_format(template: str, context: dict[str, str]) -> str:
    required_keys = {field_name for _, field_name, _, _ in Formatter().parse(template) if field_name}
    for key in required_keys:
        context.setdefault(key, '-')
    return template.format(**context)


def _rule_applies(rule: IndicatorRule, asset: Asset) -> bool:
    return rule.enabled and (rule.applies_to_asset_key in (None, '', asset.asset_key, asset.flow_computer_tag))


def _latest_snapshot(snapshots: list[ConfigSnapshot]) -> ConfigSnapshot | None:
    if not snapshots:
        return None
    return sorted(snapshots, key=lambda item: item.id, reverse=True)[0]


def _normalize_text(value: str | None) -> str:
    return (value or '').strip().lower()


def _resolve_gc_component(parameter_key: str | None, parameter_label: str | None) -> tuple[str | None, str | None]:
    text = f'{parameter_key or ""} {parameter_label or ""}'.lower().replace('_', ' ').replace('.', ' ')
    for component_key, component_label, aliases in CHROMATOGRAPHY_COMPONENTS:
        if any(alias in text for alias in aliases):
            return component_key, component_label
    return None, None


def _load_expected_gc_components(session: Session) -> list[tuple[str, str]]:
    record = (
        session.query(ReferenceRecord)
        .filter(
            ReferenceRecord.entity_type == 'metering_reference',
            ReferenceRecord.record_key == 'gc_component_profile',
        )
        .one_or_none()
    )
    if record is None:
        return []
    metadata = json.loads(record.metadata_json or '{}')
    components = metadata.get('components')
    if not isinstance(components, list):
        return []
    result: list[tuple[str, str]] = []
    for component in components:
        component_key = _normalize_text(str(component))
        component_label = next((label for key, label, _ in CHROMATOGRAPHY_COMPONENTS if key == component_key), str(component))
        result.append((component_key, component_label))
    return result


def _collect_snapshot_gc_parameters(snapshot: ConfigSnapshot | None) -> dict[str, ConfigParameter]:
    if snapshot is None:
        return {}
    result: dict[str, ConfigParameter] = {}
    for parameter in snapshot.parameters:
        component_key, _ = _resolve_gc_component(parameter.parameter_key, parameter.parameter_label)
        if component_key:
            result[component_key] = parameter
    return result


def _find_previous_snapshot(asset: Asset, current_snapshot: ConfigSnapshot | None, batch_id: int | None) -> ConfigSnapshot | None:
    if current_snapshot is None:
        return None
    ordered = sorted(asset.snapshots, key=lambda item: item.snapshot_at or datetime.min, reverse=True)
    for snapshot in ordered:
        if snapshot.id == current_snapshot.id:
            continue
        if batch_id is not None and snapshot.file.batch_id == batch_id:
            continue
        return snapshot
    return None


def _find_parameter(snapshot: ConfigSnapshot | None, target_field: str | None) -> ConfigParameter | None:
    if snapshot is None or not target_field:
        return None
    normalized_target = target_field.lower()
    for parameter in snapshot.parameters:
        if parameter.parameter_key.lower() == normalized_target or parameter.parameter_label.lower() == normalized_target:
            return parameter
    for parameter in snapshot.parameters:
        if normalized_target in parameter.parameter_key.lower() or normalized_target in parameter.parameter_label.lower():
            return parameter
    return None


def _find_parameter_by_reference(snapshot: ConfigSnapshot | None, metadata: dict) -> ConfigParameter | None:
    if snapshot is None:
        return None
    target_candidates = [
        str(metadata.get('target_field') or '').strip().lower(),
        str(metadata.get('target_label') or '').strip().lower(),
    ]
    target_candidates = [candidate for candidate in target_candidates if candidate]
    if not target_candidates:
        return None

    for parameter in snapshot.parameters:
        parameter_key = parameter.parameter_key.lower()
        parameter_label = parameter.parameter_label.lower()
        for candidate in target_candidates:
            if candidate == parameter_key or candidate == parameter_label:
                return parameter

    for parameter in snapshot.parameters:
        parameter_key = parameter.parameter_key.lower()
        parameter_label = parameter.parameter_label.lower()
        for candidate in target_candidates:
            if candidate in parameter_key or candidate in parameter_label:
                return parameter
    return None


def _format_limit_reference(metadata: dict) -> str:
    parts: list[str] = []
    for label, key in (
        ('LL', 'lower_low_limit'),
        ('L', 'lower_limit'),
        ('U', 'upper_limit'),
        ('HH', 'upper_high_limit'),
        ('Min', 'min_value'),
        ('Max', 'max_value'),
    ):
        value = metadata.get(key)
        if value not in (None, ''):
            parts.append(f'{label} {value}')
    return ' | '.join(parts)


def _evaluate_limit_metadata(value: str | None, metadata: dict) -> tuple[str | None, str | None]:
    current_number = _parse_numeric(value)
    if current_number is None:
        return None, None

    reference_kind = str(metadata.get('reference_kind') or '').strip().lower()
    lower_low = _parse_numeric(str(metadata.get('lower_low_limit') or '')) if metadata.get('lower_low_limit') not in (None, '') else None
    lower = _parse_numeric(str(metadata.get('lower_limit') or '')) if metadata.get('lower_limit') not in (None, '') else None
    upper = _parse_numeric(str(metadata.get('upper_limit') or '')) if metadata.get('upper_limit') not in (None, '') else None
    upper_high = _parse_numeric(str(metadata.get('upper_high_limit') or '')) if metadata.get('upper_high_limit') not in (None, '') else None
    min_value = _parse_numeric(str(metadata.get('min_value') or '')) if metadata.get('min_value') not in (None, '') else None
    max_value = _parse_numeric(str(metadata.get('max_value') or '')) if metadata.get('max_value') not in (None, '') else None

    if reference_kind == 'numeric_band':
        if min_value is not None and current_number < min_value:
            return 'desvio', f'abaixo do mínimo {min_value}'
        if max_value is not None and current_number > max_value:
            return 'desvio', f'acima do máximo {max_value}'
        if min_value is not None or max_value is not None:
            return 'ok', 'dentro da faixa configurada'
        return None, None

    if reference_kind in {'alarm_limits', 'critical_parameter'}:
        if lower_low is not None and current_number < lower_low:
            return 'critical', f'abaixo do limite baixo-baixo {lower_low}'
        if upper_high is not None and current_number > upper_high:
            return 'critical', f'acima do limite alto-alto {upper_high}'
        if lower is not None and current_number < lower:
            return ('critical' if reference_kind == 'critical_parameter' else 'desvio'), f'abaixo do limite inferior {lower}'
        if upper is not None and current_number > upper:
            return ('critical' if reference_kind == 'critical_parameter' else 'desvio'), f'acima do limite superior {upper}'
        if min_value is not None and current_number < min_value:
            return ('critical' if reference_kind == 'critical_parameter' else 'desvio'), f'abaixo do mínimo {min_value}'
        if max_value is not None and current_number > max_value:
            return ('critical' if reference_kind == 'critical_parameter' else 'desvio'), f'acima do máximo {max_value}'
        if any(item is not None for item in (lower_low, lower, upper, upper_high, min_value, max_value)):
            return 'ok', 'dentro do limite configurado'
        return None, None

    return None, None


def _build_fixed_reference_indicators(
    session: Session,
    asset: Asset,
    snapshot: ConfigSnapshot | None,
    batch_id: int | None = None,
) -> list[IndicatorRecord]:
    if snapshot is None:
        return []

    records = (
        session.query(ReferenceRecord)
        .filter(ReferenceRecord.entity_type.in_(('metering_reference', 'critical_parameter')))
        .order_by(ReferenceRecord.entity_type.asc(), ReferenceRecord.name.asc(), ReferenceRecord.id.asc())
        .all()
    )
    indicators: list[IndicatorRecord] = []
    for record in records:
        metadata = json.loads(record.metadata_json or '{}')
        reference_kind = str(metadata.get('reference_kind') or '').strip().lower()
        if reference_kind not in {'numeric_band', 'alarm_limits', 'critical_parameter'}:
            continue
        parameter = _find_parameter_by_reference(snapshot, metadata)
        if parameter is None:
            continue
        status, detail = _evaluate_limit_metadata(parameter.normalized_value, metadata)
        if status in (None, 'ok'):
            continue

        reference_display = _format_limit_reference(metadata)
        severity = 'high'
        if status == 'critical' or reference_kind == 'critical_parameter':
            severity = 'critical'
        elif reference_kind == 'alarm_limits':
            severity = 'high'
        else:
            severity = 'medium'

        indicators.append(
            IndicatorRecord(
                asset_id=asset.id,
                batch_id=batch_id,
                rule_id=None,
                title=record.name,
                category='metrologico',
                severity=severity,
                status='triggered',
                description=(
                    f"O ativo {asset.flow_computer_tag} apresentou {parameter.parameter_label} = "
                    f"{parameter.normalized_value or '-'}, {detail}. Referência configurada: {reference_display or 'sem detalhe'}."
                ),
                recommendation='Revisar o valor medido/configurado e confirmar se o limite cadastrado continua válido para este FC.',
                evidence_json=json.dumps(
                    {
                        'type': 'fixed_reference_limit',
                        'reference_record_id': record.id,
                        'reference_kind': reference_kind,
                        'parameter_key': parameter.parameter_key,
                        'parameter_label': parameter.parameter_label,
                        'current_value': parameter.normalized_value,
                        'status': status,
                        'reference_display': reference_display,
                    },
                    ensure_ascii=False,
                ),
            )
        )
    return indicators


def _build_event_indicator(asset: Asset, rule: IndicatorRule, events: list[Event], batch_id: int | None = None) -> IndicatorRecord | None:
    match_text = (rule.match_text or '').lower()
    matched_events = [event for event in events if match_text in event.message.lower()]
    if len(matched_events) < rule.threshold_count:
        return None
    last_event = matched_events[0]
    context = {
        'asset': asset.flow_computer_tag,
        'count': str(len(matched_events)),
        'event_message': last_event.message,
        'match_text': rule.match_text or '-',
    }
    evidence = {
        'rule_type': rule.rule_type,
        'match_text': rule.match_text,
        'count': len(matched_events),
        'events': [
            {
                'occurred_at': event.occurred_at.isoformat() if event.occurred_at else None,
                'message': event.message,
                'severity': event.severity,
            }
            for event in matched_events[:5]
        ],
    }
    return IndicatorRecord(
        asset_id=asset.id,
        batch_id=batch_id,
        rule_id=rule.id,
        title=rule.name,
        category=rule.category,
        severity=rule.severity,
        status='triggered',
        description=_safe_format(rule.description_template, context),
        recommendation=rule.recommendation,
        evidence_json=json.dumps(evidence, ensure_ascii=False),
    )


def _build_parameter_limit_indicator(
    asset: Asset,
    rule: IndicatorRule,
    snapshot: ConfigSnapshot | None,
    batch_id: int | None = None,
) -> IndicatorRecord | None:
    parameter = _find_parameter(snapshot, rule.target_field)
    if parameter is None:
        return None
    numeric_value = _parse_numeric(parameter.normalized_value)
    if numeric_value is None:
        return None
    out_of_range = False
    if rule.min_value is not None and numeric_value < rule.min_value:
        out_of_range = True
    if rule.max_value is not None and numeric_value > rule.max_value:
        out_of_range = True
    if not out_of_range:
        return None
    context = {
        'asset': asset.flow_computer_tag,
        'parameter_label': parameter.parameter_label,
        'value': parameter.normalized_value or '-',
        'min_value': str(rule.min_value) if rule.min_value is not None else '-',
        'max_value': str(rule.max_value) if rule.max_value is not None else '-',
    }
    evidence = {
        'rule_type': rule.rule_type,
        'parameter_key': parameter.parameter_key,
        'parameter_label': parameter.parameter_label,
        'value': parameter.normalized_value,
        'min_value': rule.min_value,
        'max_value': rule.max_value,
    }
    return IndicatorRecord(
        asset_id=asset.id,
        batch_id=batch_id,
        rule_id=rule.id,
        title=rule.name,
        category=rule.category,
        severity=rule.severity,
        status='triggered',
        description=_safe_format(rule.description_template, context),
        recommendation=rule.recommendation,
        evidence_json=json.dumps(evidence, ensure_ascii=False),
    )


def _build_parameter_expected_indicator(
    asset: Asset,
    rule: IndicatorRule,
    snapshot: ConfigSnapshot | None,
    batch_id: int | None = None,
) -> IndicatorRecord | None:
    parameter = _find_parameter(snapshot, rule.target_field)
    if parameter is None:
        return None
    current_value = parameter.normalized_value or ''
    if (rule.expected_value or '').lower() in current_value.lower():
        return None
    context = {
        'asset': asset.flow_computer_tag,
        'parameter_label': parameter.parameter_label,
        'value': current_value or '-',
        'expected_value': rule.expected_value or '-',
    }
    evidence = {
        'rule_type': rule.rule_type,
        'parameter_key': parameter.parameter_key,
        'parameter_label': parameter.parameter_label,
        'value': parameter.normalized_value,
        'expected_value': rule.expected_value,
    }
    return IndicatorRecord(
        asset_id=asset.id,
        batch_id=batch_id,
        rule_id=rule.id,
        title=rule.name,
        category=rule.category,
        severity=rule.severity,
        status='triggered',
        description=_safe_format(rule.description_template, context),
        recommendation=rule.recommendation,
        evidence_json=json.dumps(evidence, ensure_ascii=False),
    )


def _build_gc_indicators(
    session: Session,
    asset: Asset,
    snapshot: ConfigSnapshot | None,
    previous_snapshot: ConfigSnapshot | None,
    batch_id: int | None = None,
) -> list[IndicatorRecord]:
    if snapshot is None:
        return []

    indicators: list[IndicatorRecord] = []
    expected_components = _load_expected_gc_components(session)
    current_gc = _collect_snapshot_gc_parameters(snapshot)
    previous_gc = _collect_snapshot_gc_parameters(previous_snapshot)

    changed_components: list[str] = []
    for component_key, parameter in current_gc.items():
        previous_parameter = previous_gc.get(component_key)
        if previous_parameter is None:
            continue
        if _normalize_text(parameter.normalized_value) != _normalize_text(previous_parameter.normalized_value):
            component_label = next((label for key, label, _ in CHROMATOGRAPHY_COMPONENTS if key == component_key), component_key)
            changed_components.append(component_label)

    if changed_components:
        indicators.append(
            IndicatorRecord(
                asset_id=asset.id,
                batch_id=batch_id,
                rule_id=None,
                title='Mudança em cromatografia / GC',
                category='metrologico',
                severity='high',
                status='triggered',
                description=f"O ativo {asset.flow_computer_tag} apresentou mudança em componente(s) de GC: {', '.join(changed_components)}.",
                recommendation='Validar se a mudança de composição faz sentido para o processo e se precisa virar nova referência viva de GC.',
                evidence_json=json.dumps(
                    {
                        'type': 'gc_component_change',
                        'components': changed_components,
                        'current_snapshot_id': snapshot.id,
                        'previous_snapshot_id': previous_snapshot.id if previous_snapshot else None,
                    },
                    ensure_ascii=False,
                ),
            )
        )

    if expected_components:
        missing_components = [label for component_key, label in expected_components if component_key not in current_gc]
        if missing_components:
            severity = 'medium' if current_gc else 'high'
            indicators.append(
                IndicatorRecord(
                    asset_id=asset.id,
                    batch_id=batch_id,
                    rule_id=None,
                    title='Componentes esperados de GC ausentes',
                    category='metrologico',
                    severity=severity,
                    status='triggered',
                    description=f"O ativo {asset.flow_computer_tag} não apresentou os seguintes componentes esperados de GC nesta versão: {', '.join(missing_components)}.",
                    recommendation='Confirmar se o arquivo realmente deveria conter GC, se o perfil esperado está correto e se a leitura foi exportada pelo Flow-X.',
                    evidence_json=json.dumps(
                        {
                            'type': 'gc_expected_component_missing',
                            'missing_components': missing_components,
                            'current_snapshot_id': snapshot.id,
                            'found_components': list(current_gc.keys()),
                        },
                        ensure_ascii=False,
                    ),
                )
            )

    gc_reference_records = (
        session.query(ReferenceRecord)
        .filter(
            ReferenceRecord.entity_type == 'process_reference',
            ReferenceRecord.record_key.like(f'{asset.asset_key}::%'),
        )
        .all()
    )
    saved_components: list[str] = []
    for record in gc_reference_records:
        metadata = json.loads(record.metadata_json or '{}')
        if metadata.get('kind') != 'chromatography':
            continue
        if metadata.get('snapshot_id') != snapshot.id:
            continue
        component_label = metadata.get('component_label') or metadata.get('parameter_label') or record.name
        if component_label not in saved_components:
            saved_components.append(str(component_label))

    if saved_components:
        indicators.append(
            IndicatorRecord(
                asset_id=asset.id,
                batch_id=batch_id,
                rule_id=None,
                title='GC salvo como referência viva',
                category='auditoria',
                severity='low',
                status='triggered',
                description=f"O ativo {asset.flow_computer_tag} já possui componente(s) de GC salvos como referência viva nesta versão: {', '.join(saved_components)}.",
                recommendation='Se esta referência foi confirmada pelo usuário, manter. Caso contrário, revisar antes da próxima comparação.',
                evidence_json=json.dumps(
                    {
                        'type': 'gc_reference_saved',
                        'components': saved_components,
                        'snapshot_id': snapshot.id,
                    },
                    ensure_ascii=False,
                ),
            )
        )

    return indicators


def evaluate_indicators(session: Session, asset_id: int | None = None, batch_id: int | None = None) -> list[IndicatorRecord]:
    query = session.query(Asset).options(
        selectinload(Asset.snapshots).selectinload(ConfigSnapshot.parameters),
        selectinload(Asset.events),
    )
    if asset_id is not None:
        query = query.filter(Asset.id == asset_id)
    if batch_id is not None:
        query = query.filter(
            Asset.snapshots.any(ConfigSnapshot.file.has(batch_id=batch_id))
            | Asset.events.any(Event.file.has(batch_id=batch_id))
        )
    assets = query.order_by(Asset.flow_computer_tag.asc()).all()
    rules = session.query(IndicatorRule).filter(IndicatorRule.enabled.is_(True)).order_by(IndicatorRule.name.asc()).all()

    asset_ids = [asset.id for asset in assets]
    if asset_ids:
        indicator_delete = delete(IndicatorRecord).where(IndicatorRecord.asset_id.in_(asset_ids))
        if batch_id is not None:
            indicator_delete = indicator_delete.where(IndicatorRecord.batch_id == batch_id)
        session.execute(indicator_delete)
        session.commit()

    created_records: list[IndicatorRecord] = []
    for asset in assets:
        asset_snapshots = [
            snapshot
            for snapshot in asset.snapshots
            if batch_id is None or snapshot.file.batch_id == batch_id
        ]
        snapshot = _latest_snapshot(asset_snapshots)
        previous_snapshot = _find_previous_snapshot(asset, snapshot, batch_id)
        events = sorted(
            [
                event
                for event in asset.events
                if batch_id is None or event.file.batch_id == batch_id
            ],
            key=lambda item: item.occurred_at or datetime.min,
            reverse=True,
        )
        for rule in rules:
            if not _rule_applies(rule, asset):
                continue
            indicator: IndicatorRecord | None = None
            if rule.rule_type == 'event_match':
                indicator = _build_event_indicator(asset, rule, events, batch_id=batch_id)
            elif rule.rule_type == 'parameter_limit':
                indicator = _build_parameter_limit_indicator(asset, rule, snapshot, batch_id=batch_id)
            elif rule.rule_type == 'parameter_expected':
                indicator = _build_parameter_expected_indicator(asset, rule, snapshot, batch_id=batch_id)
            if indicator is not None:
                session.add(indicator)
                created_records.append(indicator)
        for indicator in _build_gc_indicators(
            session,
            asset,
            snapshot,
            previous_snapshot,
            batch_id=batch_id,
        ):
            session.add(indicator)
            created_records.append(indicator)
        for indicator in _build_fixed_reference_indicators(
            session,
            asset,
            snapshot,
            batch_id=batch_id,
        ):
            session.add(indicator)
            created_records.append(indicator)
    session.commit()
    result_query = session.query(IndicatorRecord)
    if asset_id is not None:
        result_query = result_query.filter(IndicatorRecord.asset_id == asset_id)
    if batch_id is not None:
        result_query = result_query.filter(IndicatorRecord.batch_id == batch_id)
    return result_query.order_by(IndicatorRecord.created_at.desc()).all()
