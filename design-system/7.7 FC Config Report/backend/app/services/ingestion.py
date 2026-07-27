import hashlib
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi import UploadFile
from sqlalchemy.orm import Session

_log = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB por arquivo
MAX_ZIP_DECOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB total por ZIP
MAX_FILES_PER_BATCH = 10_000

from ..models import Asset, ConfigParameter, ConfigSnapshot, Event, IngestionBatch, MeasurementPoint, MeasurementReferenceParameter, MeterAnalysisSelection, RawFile
from ..parsers.configuration import parse_configuration
from ..parsers.detector import detect_document_type
from ..parsers.events import parse_events
from ..parsers.parameters_xml import parse_parameters_xml
from ..parsers.pam_pdf import parse_pam007126_pdf
from ..parsers.production_xml import parse_production_xml
from ..parsers.run_report import parse_run_report
from ..storage import raw_batch_dir, write_bytes
from .references import seed_technical_references


def _read_text(content: bytes) -> str:
    for encoding in ('utf-8', 'latin-1', 'cp1252'):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode('utf-8', errors='ignore')


def _normalize_token(value: str | None) -> str:
    return (value or '').strip().upper()


def _normalize_folder_name(value: str) -> str:
    return ' '.join(value.lower().replace('_', ' ').replace('-', ' ').split())


def _payload_signature(filename: str, payload: bytes) -> tuple[str, str]:
    return (filename.lower(), hashlib.sha256(payload).hexdigest())


def _folder_named(root: Path, names: set[str]) -> Path | None:
    normalized_names = {_normalize_folder_name(name) for name in names}
    if not root.exists() or not root.is_dir():
        return None
    for child in root.iterdir():
        if not child.is_dir():
            continue
        normalized_child = _normalize_folder_name(child.name)
        if normalized_child in normalized_names or any(normalized_child.endswith(f' {name}') for name in normalized_names):
            return child
    return None


def _persist_archive_entries(
    session: Session,
    batch_id: int,
    source_path: Path,
    payload: bytes,
    relative_dir: str,
    seen_signatures: set[tuple[str, str]] | None = None,
) -> None:
    with ZipFile(BytesIO(payload)) as archive:
        total_decompressed = 0
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            total_decompressed += entry.file_size
            if total_decompressed > MAX_ZIP_DECOMPRESSED_BYTES:
                _log.warning('ZIP %s excede limite de descompressao (%s bytes); entradas restantes ignoradas.', source_path, MAX_ZIP_DECOMPRESSED_BYTES)
                break
            if entry.file_size > MAX_FILE_SIZE_BYTES:
                _log.warning('Entrada ZIP %s (%s bytes) excede limite por arquivo; ignorada.', entry.filename, entry.file_size)
                continue
            filename = Path(entry.filename).name
            entry_payload = archive.read(entry.filename)
            signature = _payload_signature(filename, entry_payload)
            if seen_signatures is not None and signature in seen_signatures:
                continue
            if seen_signatures is not None:
                seen_signatures.add(signature)
            raw_file = _persist_file(session, batch_id, filename, entry_payload, relative_dir)
            _parse_if_supported(session, raw_file, entry_payload)


def _active_folder_selections(
    session: Session,
    selection_ids: list[int] | None = None,
    inline_selections: list[dict] | None = None,
    include_inactive: bool = False,
) -> list[MeterAnalysisSelection]:
    if inline_selections:
        transient: list[MeterAnalysisSelection] = []
        for item in inline_selections:
            transient.append(
                MeterAnalysisSelection(
                    flow_computer=_normalize_token(item.get('flow_computer')),
                    meter_id=_normalize_token(item.get('meter_id')),
                    is_active=item.get('is_active', True),
                    is_default=item.get('is_default', False),
                    source_label=item.get('source_label', 'request'),
                    notes=item.get('notes'),
                )
            )
        return [selection for selection in transient if include_inactive or selection.is_active]
    query = session.query(MeterAnalysisSelection)
    if selection_ids:
        query = query.filter(MeterAnalysisSelection.id.in_(selection_ids))
    if not include_inactive:
        query = query.filter(MeterAnalysisSelection.is_active.is_(True))
    return query.order_by(MeterAnalysisSelection.flow_computer, MeterAnalysisSelection.meter_id).all()


def _cv_report_matches_selections(filename: str, payload: bytes, relative_path: str, selections: list[MeterAnalysisSelection]) -> bool:
    if not selections:
        return False
    detected_type = detect_document_type(filename)
    if detected_type not in {'configuration_report', 'events_snapshot', 'alarms_events_daily', 'run_report', 'parameters_xml', 'security_xml'}:
        return False
    text = _read_text(payload)
    upper_text = text.upper()
    upper_path = relative_path.upper()
    selected_meter_ids = {_normalize_token(selection.meter_id) for selection in selections if selection.meter_id}
    selected_flow_computers = {_normalize_token(selection.flow_computer) for selection in selections if selection.flow_computer}
    if detected_type == 'run_report':
        parsed = parse_run_report(text)
        flow_computer = _normalize_token(parsed['asset'].get('flow_computer_tag'))
        meter_id = _normalize_token(parsed['asset'].get('system_tag'))
        return any(
            meter_id == _normalize_token(selection.meter_id)
            and (
                flow_computer == _normalize_token(selection.flow_computer)
                or _normalize_token(selection.flow_computer) in upper_path
                or not flow_computer
            )
            for selection in selections
        )
    if detected_type == 'configuration_report':
        parsed = parse_configuration(text)
        flow_computer = _normalize_token(parsed['asset'].get('flow_computer_tag'))
        return any(
            _normalize_token(selection.meter_id) in upper_text
            and (
                flow_computer == _normalize_token(selection.flow_computer)
                or _normalize_token(selection.flow_computer) in upper_path
                or _normalize_token(selection.meter_id) in upper_text
            )
            for selection in selections
        )
    if detected_type in {'parameters_xml', 'security_xml'}:
        return any(flow_computer and flow_computer in upper_path for flow_computer in selected_flow_computers)
    if any(flow_computer and (flow_computer in upper_text or flow_computer in upper_path) for flow_computer in selected_flow_computers):
        return True
    return any(meter_id and meter_id in upper_text for meter_id in selected_meter_ids)


def _find_or_create_asset(session: Session, parsed_asset: dict) -> Asset:
    asset_key = parsed_asset.get('flow_computer_tag') or parsed_asset.get('system_tag') or 'unknown-asset'
    asset = session.query(Asset).filter(Asset.asset_key == asset_key).one_or_none()
    if asset is None:
        asset = Asset(
            asset_key=asset_key,
            flow_computer_tag=parsed_asset.get('flow_computer_tag') or asset_key,
            system_tag=parsed_asset.get('system_tag'),
            location=parsed_asset.get('location'),
            company=parsed_asset.get('company'),
            description=parsed_asset.get('description'),
            last_seen_at=datetime.utcnow(),
        )
        session.add(asset)
        session.flush()
        return asset
    asset.flow_computer_tag = parsed_asset.get('flow_computer_tag') or asset.flow_computer_tag
    asset.system_tag = parsed_asset.get('system_tag') or asset.system_tag
    asset.location = parsed_asset.get('location') or asset.location
    asset.company = parsed_asset.get('company') or asset.company
    asset.description = parsed_asset.get('description') or asset.description
    asset.last_seen_at = datetime.utcnow()
    session.flush()
    return asset


def _persist_configuration(session: Session, raw_file: RawFile, content: str) -> None:
    parsed = parse_configuration(content)
    asset = _find_or_create_asset(session, parsed['asset'])
    snapshot = ConfigSnapshot(
        asset_id=asset.id,
        file_id=raw_file.id,
        snapshot_at=parsed['metadata']['snapshot_at'],
        device_name=parsed['metadata']['device_name'],
        device_type=parsed['metadata']['device_type'],
        application_version=parsed['metadata']['application_version'],
        serial_number=parsed['metadata']['serial_number'],
        ip_address_1=parsed['metadata']['ip_address_1'],
        ip_address_2=parsed['metadata']['ip_address_2'],
        parser_version=parsed['parser_version'],
    )
    session.add(snapshot)
    session.flush()
    for record in parsed['records']:
        session.add(
            ConfigParameter(
                snapshot_id=snapshot.id,
                section=record['section'],
                parameter_key=record['parameter_key'],
                parameter_label=record['parameter_label'],
                normalized_value=record['normalized_value'],
                raw_value=record['raw_value'],
                unit=record['unit'],
                evidence_excerpt=record['evidence_excerpt'],
            )
        )
    raw_file.parse_status = 'parsed'


def _persist_events(session: Session, raw_file: RawFile, content: str) -> None:
    parsed = parse_events(content)
    asset = _find_or_create_asset(session, parsed['asset'])
    for record in parsed['records']:
        session.add(
            Event(
                asset_id=asset.id,
                file_id=raw_file.id,
                occurred_at=record['occurred_at'],
                run_number=record['run_number'],
                event_type=record['event_type'],
                category=record['category'],
                severity=record['severity'],
                actor=record['actor'],
                source_ip=record['source_ip'],
                message=record['message'],
                old_value=record['old_value'],
                new_value=record['new_value'],
                evidence_excerpt=record['evidence_excerpt'],
            )
        )
    raw_file.parse_status = 'parsed'


def _find_asset_from_same_batch(session: Session, raw_file: RawFile) -> Asset | None:
    snapshot = (
        session.query(ConfigSnapshot)
        .join(RawFile, ConfigSnapshot.file_id == RawFile.id)
        .filter(RawFile.batch_id == raw_file.batch_id)
        .order_by(ConfigSnapshot.id.desc())
        .first()
    )
    return snapshot.asset if snapshot else None


def _persist_parameters_xml(session: Session, raw_file: RawFile, content: str) -> None:
    parsed = parse_parameters_xml(content)
    asset = _find_asset_from_same_batch(session, raw_file) or _find_or_create_asset(session, parsed['asset'])
    snapshot = ConfigSnapshot(
        asset_id=asset.id,
        file_id=raw_file.id,
        snapshot_at=parsed['metadata']['snapshot_at'],
        device_name=parsed['metadata']['device_name'],
        device_type=parsed['metadata']['device_type'],
        application_version=parsed['metadata']['application_version'],
        serial_number=parsed['metadata']['serial_number'],
        ip_address_1=parsed['metadata']['ip_address_1'],
        ip_address_2=parsed['metadata']['ip_address_2'],
        parser_version=parsed['parser_version'],
    )
    session.add(snapshot)
    session.flush()
    for record in parsed['records']:
        session.add(
            ConfigParameter(
                snapshot_id=snapshot.id,
                section=record['section'],
                parameter_key=record['parameter_key'],
                parameter_label=record['parameter_label'],
                normalized_value=record['normalized_value'],
                raw_value=record['raw_value'],
                unit=record['unit'],
                evidence_excerpt=record['evidence_excerpt'],
            )
        )
    raw_file.parse_status = 'parsed'


def _persist_run_report(session: Session, raw_file: RawFile, content: str) -> None:
    parsed = parse_run_report(content)
    asset = _find_or_create_asset(session, parsed['asset'])
    snapshot = ConfigSnapshot(
        asset_id=asset.id,
        file_id=raw_file.id,
        snapshot_at=parsed['metadata']['snapshot_at'],
        device_name=parsed['metadata']['device_name'],
        device_type=parsed['metadata']['device_type'],
        application_version=parsed['metadata']['application_version'],
        serial_number=parsed['metadata']['serial_number'],
        ip_address_1=parsed['metadata']['ip_address_1'],
        ip_address_2=parsed['metadata']['ip_address_2'],
        parser_version=parsed['parser_version'],
    )
    session.add(snapshot)
    session.flush()
    for record in parsed['records']:
        session.add(
            ConfigParameter(
                snapshot_id=snapshot.id,
                section=record['section'],
                parameter_key=record['parameter_key'],
                parameter_label=record['parameter_label'],
                normalized_value=record['normalized_value'],
                raw_value=record['raw_value'],
                unit=record['unit'],
                evidence_excerpt=record['evidence_excerpt'],
            )
        )
    raw_file.parse_status = 'parsed'


def _reference_kind_for_parameter(parameter_key: str, parameter_label: str) -> str | None:
    text = f'{parameter_key} {parameter_label}'.lower()
    if any(token in text for token in ('limite', 'alarme', 'sprr', 'infr', 'cutoff', 'meter_factor', 'k_factor', 'cromatografia')):
        return 'critical_parameter' if any(token in text for token in ('meter_factor', 'k_factor', 'cromatografia')) else 'alarm_limits'
    return None


def _numeric_or_none(value: str | None) -> float | None:
    if value in (None, ''):
        return None
    try:
        return float(str(value).replace(',', '.'))
    except ValueError:
        return None


def _upsert_measurement_reference_from_record(session: Session, tag: str | None, record: dict) -> None:
    if not tag:
        return
    reference_kind = _reference_kind_for_parameter(record['parameter_key'], record['parameter_label'])
    if reference_kind is None:
        return
    matching_points = session.query(MeasurementPoint).filter(MeasurementPoint.tag == tag).all()
    if len(matching_points) != 1:
        return
    point = matching_points[0]
    parameter_key = str(record['parameter_key'])
    existing = (
        session.query(MeasurementReferenceParameter)
        .filter(
            MeasurementReferenceParameter.measurement_point_id == point.id,
            MeasurementReferenceParameter.parameter_key == parameter_key,
        )
        .one_or_none()
    )
    numeric_value = _numeric_or_none(record.get('normalized_value'))
    label = str(record['parameter_label'])
    values = {
        'parameter_label': label,
        'reference_kind': reference_kind,
        'unit': record.get('unit'),
        'expected_value': record.get('normalized_value') if numeric_value is None else None,
        'severity': 'critical' if reference_kind == 'critical_parameter' else 'high',
        'source_label': 'production-xml',
        'notes': 'Referencia criada automaticamente a partir de XML de producao.',
    }
    if any(token in label.upper() for token in ('SPRR', 'SUPER', 'HIGH', 'LIMITE_SPRR')):
        values['upper_limit'] = numeric_value
    elif any(token in label.upper() for token in ('INFR', 'INFER', 'LOW', 'LMTE_INFR')):
        values['lower_limit'] = numeric_value
    elif numeric_value is not None:
        values['expected_value'] = record.get('normalized_value')
    if existing is None:
        session.add(MeasurementReferenceParameter(measurement_point_id=point.id, parameter_key=parameter_key, **values))
        return
    for field_name, value in values.items():
        if value is not None:
            setattr(existing, field_name, value)


def _persist_production_xml(session: Session, raw_file: RawFile, content: str) -> None:
    parsed = parse_production_xml(content, raw_file.original_name)
    for config in parsed['configs']:
        asset = _find_or_create_asset(session, config['asset'])
        snapshot = ConfigSnapshot(
            asset_id=asset.id,
            file_id=raw_file.id,
            snapshot_at=config['metadata']['snapshot_at'],
            device_name=config['metadata']['device_name'],
            device_type=config['metadata']['device_type'],
            application_version=config['metadata']['application_version'],
            serial_number=config['metadata']['serial_number'],
            ip_address_1=config['metadata']['ip_address_1'],
            ip_address_2=config['metadata']['ip_address_2'],
            parser_version=parsed['parser_version'],
        )
        session.add(snapshot)
        session.flush()
        tag = config['metadata'].get('measurement_tag')
        for record in config['records']:
            session.add(
                ConfigParameter(
                    snapshot_id=snapshot.id,
                    section=record['section'],
                    parameter_key=record['parameter_key'],
                    parameter_label=record['parameter_label'],
                    normalized_value=record['normalized_value'],
                    raw_value=record['raw_value'],
                    unit=record['unit'],
                    evidence_excerpt=record['evidence_excerpt'],
                )
            )
            _upsert_measurement_reference_from_record(session, tag, record)
    for event_item in parsed['events']:
        asset = _find_or_create_asset(session, event_item['asset'])
        record = event_item['record']
        session.add(
            Event(
                asset_id=asset.id,
                file_id=raw_file.id,
                occurred_at=record['occurred_at'],
                run_number=record['run_number'],
                event_type=record['event_type'],
                category=record['category'],
                severity=record['severity'],
                actor=record['actor'],
                source_ip=record['source_ip'],
                message=record['message'],
                old_value=record['old_value'],
                new_value=record['new_value'],
                evidence_excerpt=record['evidence_excerpt'],
            )
        )
    raw_file.parse_status = 'parsed'


def _persist_pdf_reference(session: Session, raw_file: RawFile, payload: bytes) -> None:
    parsed = parse_pam007126_pdf(payload, raw_file.original_name)
    if parsed['references']:
        seed_technical_references(session, commit=False)
        raw_file.parse_status = 'parsed'
        raw_file.parse_warning = 'PAM007126 reconhecida; referencias tecnicas Inmetro/Dimel carregadas no catalogo.'
        return
    raw_file.parse_status = 'skipped'
    raw_file.parse_warning = 'PDF reconhecido, mas nao corresponde a PAM007126/Dimel 064-2020.'


def _persist_file(session: Session, batch_id: int, filename: str, payload: bytes, relative_dir: str) -> RawFile:
    target = raw_batch_dir(batch_id) / relative_dir / filename
    sha256, size_bytes = write_bytes(target, payload)
    raw_file = RawFile(
        batch_id=batch_id,
        original_name=filename,
        stored_path=str(target),
        detected_type=detect_document_type(filename),
        sha256=sha256,
        size_bytes=size_bytes,
        parse_status='pending',
    )
    session.add(raw_file)
    session.flush()
    return raw_file


def _parse_if_supported(session: Session, raw_file: RawFile, payload: bytes) -> None:
    if raw_file.detected_type not in {'configuration_report', 'events_snapshot', 'alarms_events_daily', 'run_report', 'parameters_xml', 'production_xml', 'pdf_report'}:
        raw_file.parse_status = 'skipped'
        if raw_file.detected_type in {'security_xml'}:
            raw_file.parse_warning = 'Tipo de arquivo reconhecido; parser detalhado sera implementado em fase seguinte.'
        return
    if raw_file.detected_type == 'pdf_report':
        try:
            _persist_pdf_reference(session, raw_file, payload)
        except Exception as exc:  # noqa: BLE001
            raw_file.parse_status = 'error'
            raw_file.parse_warning = str(exc)
        return
    text = _read_text(payload)
    try:
        if raw_file.detected_type == 'configuration_report':
            _persist_configuration(session, raw_file, text)
        elif raw_file.detected_type in {'events_snapshot', 'alarms_events_daily'}:
            _persist_events(session, raw_file, text)
        elif raw_file.detected_type == 'run_report':
            _persist_run_report(session, raw_file, text)
        elif raw_file.detected_type == 'parameters_xml':
            _persist_parameters_xml(session, raw_file, text)
        else:
            _persist_production_xml(session, raw_file, text)
    except Exception as exc:  # noqa: BLE001
        raw_file.parse_status = 'error'
        raw_file.parse_warning = str(exc)


def create_batch_from_upload(session: Session, upload: UploadFile) -> IngestionBatch:
    payload = upload.file.read()
    batch = IngestionBatch(source_name=upload.filename or 'upload')
    session.add(batch)
    session.flush()

    primary_file = _persist_file(session, batch.id, upload.filename or 'upload.bin', payload, 'incoming')
    if primary_file.detected_type == 'zip_archive':
        with ZipFile(BytesIO(payload)) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                entry_payload = archive.read(entry.filename)
                filename = Path(entry.filename).name
                raw_file = _persist_file(session, batch.id, filename, entry_payload, 'extracted')
                _parse_if_supported(session, raw_file, entry_payload)
    else:
        _parse_if_supported(session, primary_file, payload)
    session.commit()
    session.refresh(batch)
    return batch


def _should_skip_path(source_path: Path, max_bytes: int) -> bool:
    if source_path.is_symlink():
        _log.warning('Link simbolico ignorado: %s', source_path)
        return True
    try:
        size = source_path.stat().st_size
    except OSError:
        return True
    if size > max_bytes:
        _log.warning('Arquivo ignorado (%.1f MB > limite %.0f MB): %s', size / 1024 / 1024, max_bytes / 1024 / 1024, source_path)
        return True
    return False


def create_batch_from_folder(
    session: Session,
    root_path: str,
    selection_ids: list[int] | None = None,
    inline_selections: list[dict] | None = None,
    include_inactive: bool = False,
) -> IngestionBatch:
    root = Path(root_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f'Pasta nao encontrada ou inacessivel: {root_path}')
    selections = _active_folder_selections(session, selection_ids, inline_selections, include_inactive)
    selected_flow_computers = {_normalize_token(selection.flow_computer) for selection in selections if selection.flow_computer}
    seen_signatures: set[tuple[str, str]] = set()
    files_processed = 0
    batch = IngestionBatch(source_name=f'folder:{root}')
    session.add(batch)
    session.flush()

    xml_dir = _folder_named(root, {'XML'})
    if xml_dir is not None:
        for source_path in sorted(xml_dir.rglob('*')):
            if files_processed >= MAX_FILES_PER_BATCH:
                _log.warning('Limite de %s arquivos por lote atingido; processamento interrompido.', MAX_FILES_PER_BATCH)
                break
            if not source_path.is_file() or source_path.suffix.lower() not in {'.xml', '.zip'}:
                continue
            if _should_skip_path(source_path, MAX_FILE_SIZE_BYTES):
                continue
            payload = source_path.read_bytes()
            files_processed += 1
            if source_path.suffix.lower() == '.zip':
                _persist_archive_entries(session, batch.id, source_path, payload, f'extracted/XML/{source_path.stem}', seen_signatures)
                continue
            detected_type = detect_document_type(source_path.name)
            if detected_type != 'production_xml':
                continue
            signature = _payload_signature(source_path.name, payload)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            raw_file = _persist_file(session, batch.id, source_path.name, payload, f'extracted/XML/{source_path.parent.name}')
            _parse_if_supported(session, raw_file, payload)

    cv_reports_dir = _folder_named(root, {'CV reports', 'CV_Reports', 'CV-Reports'})
    if cv_reports_dir is not None:
        for source_path in sorted(cv_reports_dir.rglob('*')):
            if files_processed >= MAX_FILES_PER_BATCH:
                _log.warning('Limite de %s arquivos por lote atingido; processamento interrompido.', MAX_FILES_PER_BATCH)
                break
            if not source_path.is_file() or source_path.suffix.lower() not in {'.txt', '.xml'}:
                continue
            if _should_skip_path(source_path, MAX_FILE_SIZE_BYTES):
                continue
            relative_path = str(source_path.relative_to(cv_reports_dir))
            upper_relative_path = relative_path.upper()
            if selected_flow_computers and not any(flow_computer in upper_relative_path for flow_computer in selected_flow_computers):
                continue
            if source_path.name.lower().startswith('run_hourly'):
                continue
            payload = source_path.read_bytes()
            files_processed += 1
            if not _cv_report_matches_selections(source_path.name, payload, relative_path, selections):
                continue
            signature = _payload_signature(source_path.name, payload)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            raw_file = _persist_file(session, batch.id, source_path.name, payload, f'extracted/CV_Reports/{source_path.parent.name}')
            _parse_if_supported(session, raw_file, payload)

    if xml_dir is None and cv_reports_dir is None:
        for source_path in sorted(root.rglob('*')):
            if files_processed >= MAX_FILES_PER_BATCH:
                _log.warning('Limite de %s arquivos por lote atingido; processamento interrompido.', MAX_FILES_PER_BATCH)
                break
            if not source_path.is_file() or source_path.suffix.lower() not in {'.txt', '.xml', '.pdf', '.zip'}:
                continue
            if _should_skip_path(source_path, MAX_FILE_SIZE_BYTES):
                continue
            if source_path.name.lower().startswith('run_hourly'):
                continue
            payload = source_path.read_bytes()
            files_processed += 1
            if source_path.suffix.lower() == '.zip':
                _persist_archive_entries(session, batch.id, source_path, payload, f'extracted/{source_path.stem}', seen_signatures)
                continue
            detected_type = detect_document_type(source_path.name)
            relative_path = str(source_path.relative_to(root))
            if detected_type in {'configuration_report', 'events_snapshot', 'alarms_events_daily', 'run_report'} and not _cv_report_matches_selections(source_path.name, payload, relative_path, selections):
                continue
            if detected_type in {'parameters_xml', 'security_xml'} and selected_flow_computers and not any(flow_computer in relative_path.upper() for flow_computer in selected_flow_computers):
                continue
            signature = _payload_signature(source_path.name, payload)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            raw_file = _persist_file(session, batch.id, source_path.name, payload, f'extracted/{source_path.parent.name}')
            _parse_if_supported(session, raw_file, payload)

    if not batch.files:
        batch.notes = 'Nenhum arquivo aplicavel encontrado em XML ou CV_Reports para as selecoes informadas. IHM_Reports foi ignorada.'
    else:
        batch.notes = 'Carga por pasta diaria. XML processado globalmente; CV_Reports filtrado por Flow Computer e Meter ID; IHM_Reports ignorada.'
    session.commit()
    session.refresh(batch)
    return batch
