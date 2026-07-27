import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import delete, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .db import Base, SessionLocal, engine, get_db
from .models import (
    AlarmManagementRecord,
    Asset,
    Baseline,
    ConfigDiff,
    ConfigParameter,
    ConfigSnapshot,
    Event,
    IngestionBatch,
    ChangeRecord,
    IndicatorRecord,
    IndicatorRule,
    MeasurementPoint,
    MeasurementReferenceParameter,
    MeterAnalysisSelection,
    QaFlag,
    RawFile,
    ReferenceRecord,
    ReportExport,
    TechnicalReference,
)
from .schemas import (
    AlarmManagementUpdate,
    AssetSummary,
    BaselineSummary,
    BatchOperationalAnalysisSummary,
    BatchSummary,
    ComparisonCandidateSummary,
    ChangeRecordSummary,
    ChangeRecordUpdate,
    DiffRequest,
    DiffResponse,
    DiffRecordSummary,
    EventIntelligenceSummary,
    EventSummary,
    FileSummary,
    IndicatorRecordSummary,
    IndicatorRuleSummary,
    IndicatorRuleUpsert,
    MeasurementPointSummary,
    MeasurementPointUpsert,
    MeasurementReferenceParameterSummary,
    MeasurementReferenceParameterUpsert,
    MeterAnalysisSelectionSummary,
    MeterAnalysisSelectionUpsert,
    FolderIngestionRequest,
    ParameterSummary,
    ProcessReferenceSummary,
    ProcessReferenceUpsert,
    QaFlagSummary,
    ReferenceRecordSummary,
    ReferenceRecordUpsert,
    ReportRequest,
    ReportResponse,
    ReportExportSummary,
    SnapshotSummary,
    TechnicalReferenceSummary,
    TraceableComparisonRequest,
    TraceableComparisonResponse,
    XmlAlarmManagementSummary,
    XmlAlarmSummary,
    XmlMonitorSummary,
    XmlParameterValidationSummary,
)
from .services.change_records import create_change_records_for_diffs
from .services.diffs import compute_diff
from .services.event_intelligence import persist_event_flags, summarize_event_patterns
from .services.indicators import evaluate_indicators, seed_indicator_rules
from .services.ingestion import create_batch_from_folder, create_batch_from_upload
from .services.measurement_points import find_measurement_point_for_context, import_measurement_points_from_csv, list_measurement_points, normalize_tag, reference_parameter_matches, seed_measurement_points
from .services.meter_selections import list_meter_selections, seed_default_meter_selections, upsert_meter_selection
from .services.operational_analysis import build_operational_analysis
from .services.references import seed_reference_catalog
from .services.reports import create_report


app = FastAPI(title='SGMed Inspector API', version='0.1.0')
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / 'frontend' / 'dist'
FRONTEND_INDEX = FRONTEND_DIST / 'index.html'

CHROMATOGRAPHY_COMPONENTS: list[tuple[str, str, tuple[str, ...]]] = [
    ('methane', 'Metano', ('methane', 'metano', 'c1')),
    ('ethane', 'Etano', ('ethane', 'etano', 'c2')),
    ('propane', 'Propano', ('propane', 'propano', 'c3')),
    ('i-butane', 'i-Butano', ('i-butane', 'ibutane', 'iso butane', 'isobutane', 'ic4', 'i-c4')),
    ('n-butane', 'n-Butano', ('n-butane', 'nbutane', 'normal butane', 'n butane', 'nc4', 'n-c4')),
    ('i-pentane', 'i-Pentano', ('i-pentane', 'ipentane', 'iso pentane', 'isopentane', 'ic5', 'i-c5')),
    ('n-pentane', 'n-Pentano', ('n-pentane', 'npentane', 'normal pentane', 'n pentane', 'nc5', 'n-c5')),
    ('hexane+', 'Hexano+', ('hexane+', 'hexane plus', 'hexane pluses', 'c6+', 'c6 plus', 'hexane', 'heptane')),
    ('nitrogen', 'Nitrogênio', ('nitrogen', 'nitrogeno', 'n2')),
    ('carbon-dioxide', 'CO2', ('carbon dioxide', 'carbondioxide', 'co2')),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:5174',
        'http://127.0.0.1:5174',
        'http://127.0.0.1:4173',
        'http://127.0.0.1:4174',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text('PRAGMA table_info(indicator_records)'))}
        if 'batch_id' not in columns:
            connection.execute(text('ALTER TABLE indicator_records ADD COLUMN batch_id INTEGER'))
        measurement_columns = {row[1] for row in connection.execute(text('PRAGMA table_info(measurement_points)'))}
        measurement_column_defs = {
            'cv_tag_device': 'VARCHAR(100)',
            'cv_serial_number': 'VARCHAR(100)',
            'cv_version': 'VARCHAR(100)',
            'cv_application_name': 'VARCHAR(255)',
            'cv_application_date': 'VARCHAR(50)',
            'cv_application_version': 'VARCHAR(100)',
            'cv_ip_address': 'VARCHAR(100)',
            'cv_connected_system_name': 'VARCHAR(255)',
            'system_group': 'VARCHAR(255)',
        }
        for column_name, column_type in measurement_column_defs.items():
            if column_name not in measurement_columns:
                connection.execute(text(f'ALTER TABLE measurement_points ADD COLUMN {column_name} {column_type}'))
    with SessionLocal() as session:
        seed_reference_catalog(session)
        seed_measurement_points(session)
        seed_default_meter_selections(session)
        seed_indicator_rules(session)


@app.get('/api/health')
def healthcheck() -> dict[str, str]:
    return {'status': 'ok'}


def frontend_file_response(path: Path, *, cache_control: str | None = None) -> Response:
    response = FileResponse(path)
    if cache_control is not None:
        response.headers['Cache-Control'] = cache_control
    return response


FILE_TYPE_LABELS = {
    'production_xml': 'XML 001-004',
    'parameters_xml': 'Parameters.xml',
    'security_xml': 'Security.xml',
    'configuration_report': 'Configuração TXT',
    'events_snapshot': 'Eventos TXT',
    'alarms_events_daily': 'Alarmes/Eventos diário',
    'run_report': 'Run report',
    'pdf_report': 'PDF PAM/manual',
    'zip_archive': 'ZIP',
}


def _source_kind_and_path(source_name: str) -> tuple[str, str | None]:
    if source_name.startswith('folder:'):
        return 'folder', source_name.removeprefix('folder:')
    if source_name.lower().endswith('.zip'):
        return 'zip', source_name
    return 'upload', source_name


def _file_type_summary(files: list[RawFile]) -> str | None:
    if not files:
        return None
    counts = Counter(file.detected_type for file in files)
    preferred_order = ['production_xml', 'run_report', 'configuration_report', 'events_snapshot', 'alarms_events_daily', 'parameters_xml', 'security_xml', 'pdf_report', 'zip_archive']
    parts = []
    for file_type in preferred_order:
        count = counts.pop(file_type, 0)
        if count:
            parts.append(f'{count} {FILE_TYPE_LABELS.get(file_type, file_type)}')
    parts.extend(f'{count} {FILE_TYPE_LABELS.get(file_type, file_type)}' for file_type, count in sorted(counts.items()))
    return ', '.join(parts[:4]) + ('...' if len(parts) > 4 else '')


def _friendly_source_name(batch: IngestionBatch) -> str:
    source_kind, source_path = _source_kind_and_path(batch.source_name)
    total_files = len(batch.files)
    file_word = 'arquivo' if total_files == 1 else 'arquivos'
    summary = _file_type_summary(batch.files)
    suffix = f' - {total_files} {file_word}' + (f' ({summary})' if summary else '')
    if source_kind == 'folder' and source_path:
        folder_name = Path(source_path).name or source_path
        date_match = re.search(r'(20\d{2})[-_](\d{2})[-_](\d{2})', folder_name)
        day_label = f'{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}' if date_match else folder_name
        return f'Pasta diária {day_label}{suffix}'
    if source_kind == 'zip':
        return f'ZIP importado {Path(source_path or batch.source_name).name}{suffix}'
    return f'Arquivo importado {Path(batch.source_name).name}{suffix}'


def _serialize_batch(batch: IngestionBatch) -> BatchSummary:
    source_kind, source_path = _source_kind_and_path(batch.source_name)
    return BatchSummary(
        id=batch.id,
        source_name=_friendly_source_name(batch),
        source_path=source_path,
        source_kind=source_kind,
        file_type_summary=_file_type_summary(batch.files),
        created_at=batch.created_at,
        files=[
            FileSummary(
                id=file.id,
                original_name=file.original_name,
                detected_type=file.detected_type,
                sha256=file.sha256,
                size_bytes=file.size_bytes,
                parse_status=file.parse_status,
                parse_warning=file.parse_warning,
            )
            for file in batch.files
        ],
    )


def _serialize_snapshot(snapshot: ConfigSnapshot, *, include_parameters: bool = True) -> SnapshotSummary:
    return SnapshotSummary(
        id=snapshot.id,
        file_id=snapshot.file_id,
        batch_id=snapshot.file.batch_id if snapshot.file else None,
        batch_source_name=snapshot.file.batch.source_name if snapshot.file and snapshot.file.batch else None,
        source_file_name=snapshot.file.original_name if snapshot.file else None,
        snapshot_at=snapshot.snapshot_at,
        device_name=snapshot.device_name,
        device_type=snapshot.device_type,
        application_version=snapshot.application_version,
        serial_number=snapshot.serial_number,
        ip_address_1=snapshot.ip_address_1,
        ip_address_2=snapshot.ip_address_2,
        parser_version=snapshot.parser_version,
        parameters=[
            ParameterSummary(
                id=parameter.id,
                section=parameter.section,
                parameter_key=parameter.parameter_key,
                parameter_label=parameter.parameter_label,
                normalized_value=parameter.normalized_value,
                raw_value=parameter.raw_value,
            )
            for parameter in sorted(snapshot.parameters, key=lambda item: item.parameter_key)
        ]
        if include_parameters
        else [],
    )


def _serialize_asset(asset: Asset, batch_id: int | None = None) -> AssetSummary:
    baseline = asset.baselines[0] if asset.baselines else None
    is_new_in_local_base = False
    if batch_id is not None:
        snapshot_batch_ids = {
            snapshot.file.batch_id
            for snapshot in asset.snapshots
            if snapshot.file and snapshot.file.batch_id is not None
        }
        event_batch_ids = {
            event.file.batch_id
            for event in asset.events
            if event.file and event.file.batch_id is not None
        }
        related_batch_ids = snapshot_batch_ids | event_batch_ids
        is_new_in_local_base = len(related_batch_ids) == 1 and batch_id in related_batch_ids
    snapshots = [
        snapshot
        for snapshot in sorted(asset.snapshots, key=lambda item: item.id, reverse=True)
        if batch_id is None or (snapshot.file and snapshot.file.batch_id == batch_id)
    ]
    batch_events = [
        event
        for event in sorted(asset.events, key=lambda item: item.occurred_at or asset.last_seen_at, reverse=True)
        if batch_id is None or (event.file and event.file.batch_id == batch_id)
    ]
    latest_event = batch_events[0] if batch_events else None
    return AssetSummary(
        id=asset.id,
        asset_key=asset.asset_key,
        flow_computer_tag=asset.flow_computer_tag,
        system_tag=asset.system_tag,
        location=asset.location,
        company=asset.company,
        description=asset.description,
        last_seen_at=asset.last_seen_at,
        is_new_in_local_base=is_new_in_local_base,
        current_events_at=latest_event.occurred_at if latest_event else None,
        current_events_file_name=latest_event.file.original_name if latest_event and latest_event.file else None,
        baseline=BaselineSummary(
            id=baseline.id,
            snapshot_id=baseline.snapshot_id,
            selected_at=baseline.selected_at,
            status=baseline.status,
        )
        if baseline
        else None,
        snapshots=[_serialize_snapshot(snapshot, include_parameters=False) for snapshot in snapshots],
    )


def _looks_like_tag_value(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip()
    if len(normalized) < 4:
        return False
    return bool(re.search(r'[A-Za-z]', normalized) and re.search(r'\d', normalized))


def _extract_parameter_context(parameter: ConfigParameter | None) -> tuple[str | None, str | None, str | None]:
    if parameter is None:
        return None, None, None
    section = (parameter.section or '').strip()
    if not section:
        return None, None, None
    segments = [segment.strip() for segment in section.split('/') if segment.strip()]
    if not segments:
        return None, None, None
    tag_label = segments[-1] if _looks_like_tag_value(segments[-1]) else None
    context_segments = segments[:-1] if tag_label else segments
    context_label = ' / '.join(context_segments) if context_segments else None
    group_label = tag_label or context_label or parameter.parameter_label
    return context_label, tag_label, group_label


def _reference_record_key(asset_key: str, parameter_key: str) -> str:
    return f'{asset_key}::{parameter_key}'


def _looks_like_process_reference(parameter_key: str, parameter_label: str) -> tuple[bool, str]:
    label = f'{parameter_key} {parameter_label}'.lower()
    if any(token in label for token in ('density', 'dens', 'specific gravity')):
        return True, 'density'
    if any(
        token in label
        for token in (
            'chromat',
            'gc',
            'composition',
            'component mole',
            'gas quality',
            'methane',
            'ethane',
            'propane',
            'nitrogen',
            'carbon dioxide',
            'co2',
            'n2',
            'c1',
            'c2',
            'c3',
            'ic4',
            'nc4',
            'ic5',
            'nc5',
            'hexane',
            'heptane',
        )
    ):
        return True, 'chromatography'
    return False, 'other'


def _get_chromatography_component_info(parameter_key: str, parameter_label: str) -> tuple[str | None, str | None, int | None]:
    label = f'{parameter_key} {parameter_label}'.lower().replace('_', ' ').replace('.', ' ')
    for index, (component_key, component_label, aliases) in enumerate(CHROMATOGRAPHY_COMPONENTS):
        if any(alias in label for alias in aliases):
            return component_key, component_label, index
    return None, None, None


def _load_process_reference_map(db: Session, asset_key: str) -> dict[str, dict]:
    records = (
        db.query(ReferenceRecord)
        .filter(
            ReferenceRecord.entity_type == 'process_reference',
            ReferenceRecord.record_key.like(f'{asset_key}::%'),
        )
        .all()
    )
    result: dict[str, dict] = {}
    for record in records:
        metadata = json.loads(record.metadata_json or '{}')
        parameter_key = str(metadata.get('parameter_key') or '').strip()
        if parameter_key:
            result[parameter_key] = {
                'id': record.id,
                'value': metadata.get('reference_value'),
                'label': record.name,
                'source': record.description or record.source_label,
                'component_key': metadata.get('component_key'),
                'component_label': metadata.get('component_label'),
                'sort_order': metadata.get('sort_order'),
            }
    return result


def _parse_numeric_reference_value(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(',', '.'))
    except ValueError:
        return None


def _reference_field_matches(parameter: ConfigParameter | None, target_field: str | None, target_label: str | None) -> bool:
    if parameter is None:
        return False
    candidates = [str(target_field or '').strip().lower(), str(target_label or '').strip().lower()]
    candidates = [candidate for candidate in candidates if candidate]
    if not candidates:
        return False
    parameter_key = parameter.parameter_key.lower()
    parameter_label = parameter.parameter_label.lower()
    for candidate in candidates:
        if candidate == parameter_key or candidate == parameter_label:
            return True
        if candidate in parameter_key or candidate in parameter_label:
            return True
    return False


def _build_limit_reference_display(metadata: dict[str, object]) -> str | None:
    reference_kind = str(metadata.get('reference_kind') or '').strip().lower()
    if reference_kind == 'numeric_band':
        min_value = metadata.get('min_value')
        max_value = metadata.get('max_value')
        parts: list[str] = []
        if min_value not in (None, ''):
            parts.append(f'Min {min_value}')
        if max_value not in (None, ''):
            parts.append(f'Max {max_value}')
        return ' | '.join(parts) if parts else None
    if reference_kind in {'alarm_limits', 'critical_parameter'}:
        parts: list[str] = []
        lower_low = metadata.get('lower_low_limit')
        lower = metadata.get('lower_limit')
        upper = metadata.get('upper_limit')
        upper_high = metadata.get('upper_high_limit')
        min_value = metadata.get('min_value')
        max_value = metadata.get('max_value')
        if lower_low not in (None, ''):
            parts.append(f'LL {lower_low}')
        if lower not in (None, ''):
            parts.append(f'L {lower}')
        if upper not in (None, ''):
            parts.append(f'U {upper}')
        if upper_high not in (None, ''):
            parts.append(f'HH {upper_high}')
        if not parts:
            if min_value not in (None, ''):
                parts.append(f'Min {min_value}')
            if max_value not in (None, ''):
                parts.append(f'Max {max_value}')
        return ' | '.join(parts) if parts else None
    return None


def _evaluate_limit_reference_status(current_value: str | None, metadata: dict[str, object], fallback_severity: str) -> str | None:
    current_number = _parse_numeric_reference_value(current_value)
    if current_number is None:
        return None
    reference_kind = str(metadata.get('reference_kind') or '').strip().lower()
    min_value = _parse_numeric_reference_value(str(metadata.get('min_value') or '')) if metadata.get('min_value') not in (None, '') else None
    max_value = _parse_numeric_reference_value(str(metadata.get('max_value') or '')) if metadata.get('max_value') not in (None, '') else None
    lower_low = _parse_numeric_reference_value(str(metadata.get('lower_low_limit') or '')) if metadata.get('lower_low_limit') not in (None, '') else None
    lower = _parse_numeric_reference_value(str(metadata.get('lower_limit') or '')) if metadata.get('lower_limit') not in (None, '') else None
    upper = _parse_numeric_reference_value(str(metadata.get('upper_limit') or '')) if metadata.get('upper_limit') not in (None, '') else None
    upper_high = _parse_numeric_reference_value(str(metadata.get('upper_high_limit') or '')) if metadata.get('upper_high_limit') not in (None, '') else None

    if reference_kind == 'numeric_band':
        if min_value is not None and current_number < min_value:
            return 'desvio'
        if max_value is not None and current_number > max_value:
            return 'desvio'
        if min_value is not None or max_value is not None:
            return 'ok'
        return None

    if reference_kind in {'alarm_limits', 'critical_parameter'}:
        if lower_low is not None and current_number < lower_low:
            return 'critical'
        if upper_high is not None and current_number > upper_high:
            return 'critical'
        if lower is not None and current_number < lower:
            return 'critical' if reference_kind == 'critical_parameter' else 'desvio'
        if upper is not None and current_number > upper:
            return 'critical' if reference_kind == 'critical_parameter' else 'desvio'
        if min_value is not None and current_number < min_value:
            return 'critical' if reference_kind == 'critical_parameter' else 'desvio'
        if max_value is not None and current_number > max_value:
            return 'critical' if reference_kind == 'critical_parameter' else 'desvio'
        if any(value is not None for value in (lower_low, lower, upper, upper_high, min_value, max_value)):
            return 'ok'
        return None

    return None


def _load_fixed_reference_map(db: Session) -> list[dict[str, object]]:
    records = (
        db.query(ReferenceRecord)
        .filter(ReferenceRecord.entity_type.in_(('metering_reference', 'critical_parameter')))
        .order_by(ReferenceRecord.entity_type.asc(), ReferenceRecord.name.asc(), ReferenceRecord.id.asc())
        .all()
    )
    result: list[dict[str, object]] = []
    for record in records:
        metadata = json.loads(record.metadata_json or '{}')
        reference_kind = str(metadata.get('reference_kind') or '').strip().lower()
        if reference_kind not in {'numeric_band', 'alarm_limits', 'critical_parameter'}:
            continue
        result.append(
            {
                'id': record.id,
                'label': record.name,
                'source': record.description or record.source_label,
                'metadata': metadata,
                'entity_type': record.entity_type,
                'priority': 0 if reference_kind == 'critical_parameter' else 1 if reference_kind == 'alarm_limits' else 2,
            }
        )
    return sorted(
        result,
        key=lambda item: (int(item.get('priority', 99)), str(item.get('label') or '')),
    )


def _resolve_parameter_reference(
    parameter: ConfigParameter | None,
    process_reference_map: dict[str, dict],
    fixed_reference_map: list[dict[str, object]],
    fallback_severity: str,
) -> tuple[str | None, str | None, str | None]:
    if parameter is None:
        return None, None, None

    process_reference = process_reference_map.get(parameter.parameter_key)
    if process_reference is not None:
        reference_value = process_reference.get('value')
        return (
            reference_value,
            process_reference.get('label'),
            _evaluate_reference_status(parameter.normalized_value, reference_value, fallback_severity),
        )

    for fixed_reference in fixed_reference_map:
        metadata = fixed_reference.get('metadata')
        if not isinstance(metadata, dict):
            continue
        if not _reference_field_matches(
            parameter,
            str(metadata.get('target_field') or ''),
            str(metadata.get('target_label') or ''),
        ):
            continue
        return (
            _build_limit_reference_display(metadata),
            str(fixed_reference.get('label') or ''),
            _evaluate_limit_reference_status(parameter.normalized_value, metadata, fallback_severity),
        )

    return None, None, None


def _evaluate_reference_status(current_value: str | None, reference_value: str | None, severity: str) -> str | None:
    if current_value is None or reference_value is None:
        return None
    try:
        current_number = float(str(current_value).replace(',', '.'))
        reference_number = float(str(reference_value).replace(',', '.'))
        if abs(current_number - reference_number) < 1e-9:
            return 'ok'
        return 'critical' if severity in {'critical', 'high'} else 'desvio'
    except ValueError:
        if str(current_value).strip().lower() == str(reference_value).strip().lower():
            return 'ok'
        return 'critical' if severity in {'critical', 'high'} else 'desvio'


def _score_process_reference_parameter(parameter_key: str, parameter_label: str, normalized_value: str | None) -> int:
    value = str(normalized_value or '').strip()
    compact_value = value.replace(' ', '')
    if not value or compact_value in {'-', '--', '---'}:
        return -1
    if value.lower().startswith('display:'):
        return -1

    label = f'{parameter_key} {parameter_label}'.lower()
    if any(
        token in label
        for token in (
            'setup',
            'configuration',
            'input',
            'station density',
            'densitometer',
            'density conversion',
            'density cor factor',
            'density correction factor',
            'density of water',
            'delay',
            'mode',
            'hi lim',
            'lo lim',
            'unit',
            'ugc_k',
        )
    ):
        return -1
    if any(token in label for token in ('methane', 'ethane', 'propane', 'nitrogen', 'carbon dioxide', 'co2', 'n2', 'c1', 'c2', 'c3', 'ic4', 'nc4', 'ic5', 'nc5', 'hexane', 'heptane')):
        try:
            numeric_value = float(value.replace(',', '.'))
            if 0 <= numeric_value <= 100:
                return 10
        except ValueError:
            return -1

    score = 0
    if any(character.isdigit() for character in value):
        score += 4
    if value.lower() in {'enabled', 'disabled', 'yes', 'no'}:
        score += 1
    if any(token in label for token in ('standard dens override', 'standard_density', 'observed_density')):
        score += 4
    if any(token in label for token in ('chromat', 'gc', 'composition', 'mole', 'gas quality')):
        score += 3
    return score


def _select_best_process_reference_parameter(parameters: list, parameter_key: str):
    matches = [item for item in parameters if item.parameter_key == parameter_key]
    if not matches:
        return None
    scored_matches = sorted(
        matches,
        key=lambda item: _score_process_reference_parameter(
            item.parameter_key,
            item.parameter_label,
            item.normalized_value,
        ),
        reverse=True,
    )
    return scored_matches[0]


def _snapshot_sort_key(snapshot: ConfigSnapshot) -> tuple[int, object, int]:
    if snapshot.snapshot_at is not None:
        return (1, snapshot.snapshot_at, snapshot.id)
    return (0, snapshot.id, snapshot.id)


def _build_comparison_candidate(asset: Asset, batch_id: int) -> ComparisonCandidateSummary:
    current_snapshots = [
        snapshot
        for snapshot in sorted(asset.snapshots, key=_snapshot_sort_key, reverse=True)
        if snapshot.file and snapshot.file.batch_id == batch_id
    ]
    current_snapshot = current_snapshots[0] if current_snapshots else None
    historical_snapshots = [
        snapshot
        for snapshot in sorted(asset.snapshots, key=_snapshot_sort_key, reverse=True)
        if snapshot.file and snapshot.file.batch_id != batch_id
    ]
    previous_day_snapshot = None
    if current_snapshot and current_snapshot.snapshot_at:
        expected_previous_day = (current_snapshot.snapshot_at - timedelta(days=1)).date()
        for snapshot in historical_snapshots:
            if snapshot.snapshot_at and snapshot.snapshot_at.date() == expected_previous_day:
                previous_day_snapshot = snapshot
                break
    return ComparisonCandidateSummary(
        asset_id=asset.id,
        asset_key=asset.asset_key,
        flow_computer_tag=asset.flow_computer_tag,
        current_snapshot=_serialize_snapshot(current_snapshot, include_parameters=True) if current_snapshot else None,
        previous_day_snapshot=_serialize_snapshot(previous_day_snapshot, include_parameters=False) if previous_day_snapshot else None,
        available_snapshots=[_serialize_snapshot(snapshot, include_parameters=False) for snapshot in historical_snapshots],
    )


def _serialize_reference_record(record: ReferenceRecord) -> ReferenceRecordSummary:
    return ReferenceRecordSummary(
        id=record.id,
        entity_type=record.entity_type,
        record_key=record.record_key,
        name=record.name,
        description=record.description,
        metadata=json.loads(record.metadata_json or '{}'),
        source_label=record.source_label,
        is_default=record.is_default,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _serialize_technical_reference(record: TechnicalReference) -> TechnicalReferenceSummary:
    return TechnicalReferenceSummary(
        id=record.id,
        topic_key=record.topic_key,
        category=record.category,
        title=record.title,
        summary=record.summary,
        guidance=record.guidance,
        source_ref=record.source_ref,
        source_excerpt=record.source_excerpt,
        severity=record.severity,
        is_default=record.is_default,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _serialize_measurement_reference(reference: MeasurementReferenceParameter) -> MeasurementReferenceParameterSummary:
    return MeasurementReferenceParameterSummary(
        id=reference.id,
        measurement_point_id=reference.measurement_point_id,
        parameter_key=reference.parameter_key,
        parameter_label=reference.parameter_label,
        reference_kind=reference.reference_kind,
        unit=reference.unit,
        expected_value=reference.expected_value,
        min_value=reference.min_value,
        max_value=reference.max_value,
        lower_low_limit=reference.lower_low_limit,
        lower_limit=reference.lower_limit,
        upper_limit=reference.upper_limit,
        upper_high_limit=reference.upper_high_limit,
        tolerance=reference.tolerance,
        severity=reference.severity,
        source_label=reference.source_label,
        notes=reference.notes,
        created_at=reference.created_at,
        updated_at=reference.updated_at,
    )


def _serialize_measurement_point(point: MeasurementPoint, *, include_references: bool = True) -> MeasurementPointSummary:
    return MeasurementPointSummary(
        id=point.id,
        cv_id=point.cv_id,
        cv_tag_device=point.cv_tag_device,
        cv_serial_number=point.cv_serial_number,
        cv_version=point.cv_version,
        cv_application_name=point.cv_application_name,
        cv_application_date=point.cv_application_date,
        cv_application_version=point.cv_application_version,
        cv_ip_address=point.cv_ip_address,
        cv_connected_system_name=point.cv_connected_system_name,
        system_group=point.system_group,
        fluid=point.fluid,
        measurement_point_name=point.measurement_point_name,
        measurement_technology=point.measurement_technology,
        tag=point.tag,
        connected_system=point.connected_system,
        classification=point.classification,
        asset_key=point.asset_key,
        run_number=point.run_number,
        is_redundant=point.is_redundant,
        is_active=point.is_active,
        source_label=point.source_label,
        notes=point.notes,
        created_at=point.created_at,
        updated_at=point.updated_at,
        reference_parameters=[_serialize_measurement_reference(reference) for reference in point.reference_parameters]
        if include_references
        else [],
    )


def _serialize_meter_selection(selection: MeterAnalysisSelection) -> MeterAnalysisSelectionSummary:
    return MeterAnalysisSelectionSummary(
        id=selection.id,
        flow_computer=selection.flow_computer,
        meter_id=selection.meter_id,
        measurement_point_id=selection.measurement_point_id,
        is_active=selection.is_active,
        is_default=selection.is_default,
        source_label=selection.source_label,
        notes=selection.notes,
        created_at=selection.created_at,
        updated_at=selection.updated_at,
    )


def _serialize_change_record(record: ChangeRecord) -> ChangeRecordSummary:
    return ChangeRecordSummary(
        id=record.id,
        measurement_point_id=record.measurement_point_id,
        asset_id=record.asset_id,
        diff_id=record.diff_id,
        event_id=record.event_id,
        source_file_id=record.source_file_id,
        cv_id=record.cv_id,
        tag=record.tag,
        run_number=record.run_number,
        parameter_key=record.parameter_key,
        parameter_label=record.parameter_label,
        old_value=record.old_value,
        new_value=record.new_value,
        unit=record.unit,
        change_type=record.change_type,
        category=record.category,
        severity=record.severity,
        status=record.status,
        actor=record.actor,
        source_ip=record.source_ip,
        occurred_at=record.occurred_at,
        detected_at=record.detected_at,
        impact_summary=record.impact_summary,
        recommendation=record.recommendation,
        evidence=json.loads(record.evidence_json or '{}'),
        approval_owner=record.approval_owner,
        closure_notes=record.closure_notes,
        updated_at=record.updated_at,
    )


def _serialize_indicator_rule(rule: IndicatorRule) -> IndicatorRuleSummary:
    return IndicatorRuleSummary(
        id=rule.id,
        rule_key=rule.rule_key,
        name=rule.name,
        applies_to_asset_key=rule.applies_to_asset_key,
        rule_type=rule.rule_type,
        category=rule.category,
        severity=rule.severity,
        target_field=rule.target_field,
        match_text=rule.match_text,
        expected_value=rule.expected_value,
        min_value=rule.min_value,
        max_value=rule.max_value,
        threshold_count=rule.threshold_count,
        description_template=rule.description_template,
        recommendation=rule.recommendation,
        enabled=rule.enabled,
        is_default=rule.is_default,
        source_label=rule.source_label,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _serialize_indicator(record: IndicatorRecord) -> IndicatorRecordSummary:
    return IndicatorRecordSummary(
        id=record.id,
        asset_id=record.asset_id,
        batch_id=record.batch_id,
        rule_id=record.rule_id,
        title=record.title,
        category=record.category,
        severity=record.severity,
        status=record.status,
        description=record.description,
        recommendation=record.recommendation,
        evidence=json.loads(record.evidence_json or '{}'),
        created_at=record.created_at,
    )


def _document_code_from_snapshot(snapshot: ConfigSnapshot) -> str:
    text_value = f'{snapshot.device_type or ""} {snapshot.file.original_name if snapshot.file else ""}'.lower()
    match = re.search(r'a?00([1-4])', text_value)
    if match:
        return f'XML 00{match.group(1)}'
    match = re.search(r'\ba00([1-4])\b', text_value)
    if match:
        return f'XML 00{match.group(1)}'
    return 'XML'


def _source_document_for_event(event: Event) -> str:
    file_name = event.file.original_name if event.file else ''
    if event.file and event.file.detected_type == 'production_xml':
        match = re.match(r'00([1-4])_', file_name)
        return f'XML 00{match.group(1)}' if match else 'XML 004'
    return FILE_TYPE_LABELS.get(event.file.detected_type if event.file else '', 'Evento TXT')


def _numeric_from_text(value: str | None) -> float | None:
    if value in (None, ''):
        return None
    text_value = str(value).strip().replace(',', '.')
    try:
        return float(text_value)
    except ValueError:
        return None


def _reference_value_label(reference: MeasurementReferenceParameter | None) -> str | None:
    if reference is None:
        return None
    parts: list[str] = []
    if reference.expected_value not in (None, ''):
        parts.append(f'Esperado {reference.expected_value}')
    if reference.min_value is not None or reference.max_value is not None:
        parts.append(f'Faixa {reference.min_value if reference.min_value is not None else "-"} a {reference.max_value if reference.max_value is not None else "-"}')
    if reference.lower_low_limit is not None:
        parts.append(f'LL {reference.lower_low_limit}')
    if reference.lower_limit is not None:
        parts.append(f'L {reference.lower_limit}')
    if reference.upper_limit is not None:
        parts.append(f'H {reference.upper_limit}')
    if reference.upper_high_limit is not None:
        parts.append(f'HH {reference.upper_high_limit}')
    if reference.tolerance is not None:
        parts.append(f'Tol. {reference.tolerance}')
    return '; '.join(parts) if parts else None


def _validate_xml_parameter(parameter: ConfigParameter, reference: MeasurementReferenceParameter | None, previous_value: str | None) -> tuple[str, str, str | None]:
    current_value = parameter.normalized_value or parameter.raw_value
    changed = previous_value is not None and previous_value != current_value
    reference_label = _reference_value_label(reference)
    if reference is None:
        if changed:
            return 'changed_without_reference', 'Valor mudou em relação à versão anterior e ainda não há referência cadastrada.', None
        return 'not_configured', 'Sem referência cadastrada para validação automática.', None

    current_number = _numeric_from_text(current_value)
    if current_number is not None:
        lower_bounds = [value for value in (reference.min_value, reference.lower_low_limit, reference.lower_limit) if value is not None]
        upper_bounds = [value for value in (reference.max_value, reference.upper_limit, reference.upper_high_limit) if value is not None]
        if lower_bounds and current_number < min(lower_bounds):
            return 'out_of_reference', 'Valor abaixo do limite/reference cadastrado.', reference_label
        if upper_bounds and current_number > max(upper_bounds):
            return 'out_of_reference', 'Valor acima do limite/reference cadastrado.', reference_label
        if reference.expected_value not in (None, '') and str(current_number) != str(reference.expected_value):
            expected_number = _numeric_from_text(reference.expected_value)
            if expected_number is not None and reference.tolerance is not None and abs(current_number - expected_number) > reference.tolerance:
                return 'out_of_reference', 'Valor fora da tolerância cadastrada.', reference_label
    elif reference.expected_value not in (None, '') and str(current_value or '').strip() != str(reference.expected_value).strip():
        return 'out_of_reference', 'Valor diferente do esperado no cadastro.', reference_label

    if changed:
        return 'changed', 'Valor mudou em relação à versão anterior, mas está dentro da referência cadastrada.', reference_label
    return 'ok', 'Valor sem desvio identificado.', reference_label


def _previous_parameter_value(db: Session, snapshot: ConfigSnapshot, parameter: ConfigParameter) -> str | None:
    previous = (
        db.query(ConfigParameter)
        .join(ConfigSnapshot, ConfigParameter.snapshot_id == ConfigSnapshot.id)
        .join(RawFile, ConfigSnapshot.file_id == RawFile.id)
        .filter(
            ConfigSnapshot.asset_id == snapshot.asset_id,
            ConfigParameter.parameter_key == parameter.parameter_key,
            ConfigSnapshot.id != snapshot.id,
            RawFile.detected_type == 'production_xml',
            ConfigSnapshot.id < snapshot.id,
        )
        .order_by(ConfigSnapshot.id.desc())
        .first()
    )
    return (previous.normalized_value or previous.raw_value) if previous else None


def _point_from_asset(db: Session, asset: Asset | None, run_number: int | None = None, text_value: str | None = None) -> MeasurementPoint | None:
    if asset is None:
        return find_measurement_point_for_context(db, run_number=run_number, parameter_text=text_value)
    point = find_measurement_point_for_context(
        db,
        asset_key=asset.asset_key,
        tag=asset.flow_computer_tag,
        run_number=run_number,
        parameter_text=text_value,
    )
    if point is not None:
        return point
    linked_assets = db.query(Asset).filter(Asset.system_tag == asset.flow_computer_tag).all()
    for linked_asset in linked_assets:
        point = find_measurement_point_for_context(
            db,
            asset_key=linked_asset.asset_key,
            tag=linked_asset.flow_computer_tag,
            run_number=run_number,
            parameter_text=text_value,
        )
        if point is not None:
            return point
    return find_measurement_point_for_context(db, run_number=run_number, parameter_text=text_value)


def _point_from_candidates(points: list[MeasurementPoint], asset: Asset | None, run_number: int | None = None, text_value: str | None = None) -> MeasurementPoint | None:
    normalized_text = normalize_tag(text_value)
    normalized_asset_tag = normalize_tag(asset.flow_computer_tag if asset else None)
    for point in points:
        point_tag = normalize_tag(point.tag)
        point_cv_device = normalize_tag(point.cv_tag_device)
        point_cv_serial = normalize_tag(point.cv_serial_number)
        if normalized_asset_tag and point_tag == normalized_asset_tag:
            return point
        if normalized_asset_tag and normalized_asset_tag in {point_cv_device, point_cv_serial} and (run_number is None or point.run_number == run_number):
            return point
        if normalized_text and point_tag and point_tag in normalized_text:
            return point
    if asset is not None:
        asset_matches = [point for point in points if point.asset_key == asset.asset_key]
        if len(asset_matches) == 1:
            return asset_matches[0]
        if run_number is not None:
            for point in asset_matches:
                if point.run_number == run_number:
                    return point
    if run_number is not None and normalized_text:
        for point in points:
            if point.run_number == run_number and normalize_tag(point.tag) in normalized_text:
                return point
    return None


def _alarm_status(event: Event) -> str:
    if event.category == 'xml_event':
        return 'Registrado'
    text_value = f'{event.message} {event.new_value or ""}'.lower()
    if re.search(r'\b(ok|normal|norma)\b', text_value) and not re.search(r'to\s+(high|low)', text_value):
        return 'Normalizado'
    if 'alarm' in text_value or 'alm' in text_value or any(token in text_value for token in ('high', 'low', 'failure')):
        return 'Ativo'
    return 'Indefinido'


def _xml004_record_type(event: Event) -> str:
    if event.category == 'xml_event' or event.event_type == 'parameter_changed':
        return 'Evento'
    return 'Alarme'


def _alarm_priority(event: Event) -> str:
    text_value = f'{event.message} {event.old_value or ""} {event.new_value or ""}'.lower()
    if any(token in text_value for token in ('high high', 'low low', 'lo lo', 'hh', 'll')):
        return 'Alta'
    if any(token in text_value for token in ('high', 'low', 'failure', 'out of range')):
        return 'Média'
    return 'Baixa'


def _serialize_alarm_management(record: AlarmManagementRecord | None) -> XmlAlarmManagementSummary:
    return XmlAlarmManagementSummary(
        id=record.id if record else None,
        priority=record.priority if record else None,
        management_status=record.management_status if record else 'open',
        assignee=record.assignee if record else None,
        action_correction=record.action_correction if record else None,
        notes=record.notes if record else None,
        acknowledged_by=record.acknowledged_by if record else None,
        acknowledged_at=record.acknowledged_at if record else None,
        closed_by=record.closed_by if record else None,
        closed_at=record.closed_at if record else None,
        updated_at=record.updated_at if record else None,
    )


def _serialize_xml_alarm(event: Event, management: AlarmManagementRecord | None, db: Session, points: list[MeasurementPoint] | None = None) -> XmlAlarmSummary:
    point = _point_from_candidates(points, event.asset, event.run_number, event.message) if points is not None else _point_from_asset(db, event.asset, event.run_number, event.message)
    derived_priority = _alarm_priority(event)
    return XmlAlarmSummary(
        event_id=event.id,
        file_id=event.file_id,
        batch_id=event.file.batch_id if event.file else None,
        source_file_name=event.file.original_name if event.file else None,
        source_document=_source_document_for_event(event),
        source_record_type=_xml004_record_type(event),
        occurred_at=event.occurred_at,
        cv_id=point.cv_id if point else None,
        run_number=event.run_number or (point.run_number if point else None),
        application=point.classification if point else None,
        system=point.connected_system if point else (event.asset.system_tag if event.asset else None),
        tag=point.tag if point else (event.asset.flow_computer_tag if event.asset else None),
        alarm_text=event.message,
        alarm_status=_alarm_status(event),
        priority=management.priority if management and management.priority else derived_priority,
        executor=(management.assignee if management and management.assignee else event.actor),
        old_value=event.old_value,
        new_value=event.new_value,
        severity=event.severity,
        management=_serialize_alarm_management(management),
    )


def _serialize_xml_parameter(
    snapshot: ConfigSnapshot,
    parameter: ConfigParameter,
    db: Session,
    points: list[MeasurementPoint] | None = None,
    previous_values: dict[int, str | None] | None = None,
) -> XmlParameterValidationSummary:
    text_value = f'{parameter.parameter_key} {parameter.parameter_label} {parameter.normalized_value or parameter.raw_value or ""}'
    point = _point_from_candidates(points, snapshot.asset, text_value=text_value) if points is not None else _point_from_asset(db, snapshot.asset, text_value=text_value)
    reference = None
    if point:
        reference = next((item for item in point.reference_parameters if reference_parameter_matches(parameter.parameter_key, item)), None)
    previous_value = previous_values.get(parameter.id) if previous_values is not None else _previous_parameter_value(db, snapshot, parameter)
    status, message, reference_label = _validate_xml_parameter(parameter, reference, previous_value)
    current_value = parameter.normalized_value or parameter.raw_value
    return XmlParameterValidationSummary(
        parameter_id=parameter.id,
        snapshot_id=snapshot.id,
        file_id=snapshot.file_id,
        source_file_name=snapshot.file.original_name if snapshot.file else None,
        document_code=_document_code_from_snapshot(snapshot),
        asset_id=snapshot.asset_id,
        asset_key=snapshot.asset.asset_key if snapshot.asset else None,
        cv_id=point.cv_id if point else None,
        run_number=point.run_number if point else None,
        tag=point.tag if point else (snapshot.asset.flow_computer_tag if snapshot.asset else None),
        application=point.classification if point else None,
        system=point.connected_system if point else (snapshot.asset.system_tag if snapshot.asset else None),
        section=parameter.section,
        parameter_key=parameter.parameter_key,
        parameter_label=parameter.parameter_label,
        current_value=current_value,
        previous_value=previous_value,
        changed=previous_value is not None and previous_value != current_value,
        reference_value=reference_label,
        validation_status=status,
        validation_message=message,
    )


def _build_diff_record_summary(
    record: ConfigDiff,
    left_parameter: ConfigParameter | None,
    right_parameter: ConfigParameter | None,
    process_reference_map: dict[str, dict],
    fixed_reference_map: list[dict[str, object]],
) -> DiffRecordSummary:
    context_label, tag_label, group_label = _extract_parameter_context(right_parameter or left_parameter)
    reference_value, reference_label, reference_status = _resolve_parameter_reference(
        right_parameter or left_parameter,
        process_reference_map,
        fixed_reference_map,
        record.severity,
    )
    return DiffRecordSummary(
        id=record.id,
        parameter_key=record.parameter_key,
        parameter_label=record.parameter_label,
        context_label=context_label,
        tag_label=tag_label,
        group_label=group_label,
        left_value=record.left_value,
        right_value=record.right_value,
        change_type=record.change_type,
        category=record.category,
        severity=record.severity,
        impact_summary=record.impact_summary,
        reference_value=reference_value,
        reference_label=reference_label,
        reference_status=reference_status,
    )


@app.post('/api/ingestion/batches', response_model=BatchSummary)
def upload_batch(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BatchSummary:
    batch = create_batch_from_upload(db, file)
    db.refresh(batch)
    batch = (
        db.query(IngestionBatch)
        .options(selectinload(IngestionBatch.files))
        .filter(IngestionBatch.id == batch.id)
        .one()
    )
    return _serialize_batch(batch)


@app.post('/api/ingestion/folder', response_model=BatchSummary)
def ingest_folder(payload: FolderIngestionRequest, db: Session = Depends(get_db)) -> BatchSummary:
    try:
        batch = create_batch_from_folder(
            db,
            payload.root_path,
            selection_ids=payload.selection_ids,
            inline_selections=[selection.model_dump() for selection in payload.selections] if payload.selections else None,
            include_inactive=payload.include_inactive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    batch = (
        db.query(IngestionBatch)
        .options(selectinload(IngestionBatch.files))
        .filter(IngestionBatch.id == batch.id)
        .one()
    )
    return _serialize_batch(batch)


@app.get('/api/ingestion/batches', response_model=list[BatchSummary])
def list_batches(db: Session = Depends(get_db)) -> list[BatchSummary]:
    batches = db.query(IngestionBatch).options(selectinload(IngestionBatch.files)).order_by(IngestionBatch.created_at.desc()).all()
    return [_serialize_batch(batch) for batch in batches]


@app.get('/api/ingestion/batches/{batch_id}', response_model=BatchSummary)
def get_batch(batch_id: int, db: Session = Depends(get_db)) -> BatchSummary:
    batch = (
        db.query(IngestionBatch)
        .options(selectinload(IngestionBatch.files))
        .filter(IngestionBatch.id == batch_id)
        .one_or_none()
    )
    if batch is None:
        raise HTTPException(status_code=404, detail='Batch not found.')
    return _serialize_batch(batch)


@app.get('/api/analysis/batches/{batch_id}/operational', response_model=BatchOperationalAnalysisSummary)
def get_batch_operational_analysis(batch_id: int, db: Session = Depends(get_db)) -> BatchOperationalAnalysisSummary:
    try:
        return build_operational_analysis(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get('/api/xml-monitor/batches/{batch_id}', response_model=XmlMonitorSummary)
def get_xml_monitor(batch_id: int, db: Session = Depends(get_db)) -> XmlMonitorSummary:
    batch = (
        db.query(IngestionBatch)
        .options(selectinload(IngestionBatch.files))
        .filter(IngestionBatch.id == batch_id)
        .one_or_none()
    )
    if batch is None:
        raise HTTPException(status_code=404, detail='Importação não encontrada.')

    snapshots = (
        db.query(ConfigSnapshot)
        .options(
            selectinload(ConfigSnapshot.file),
            selectinload(ConfigSnapshot.asset),
            selectinload(ConfigSnapshot.parameters),
        )
        .join(RawFile, ConfigSnapshot.file_id == RawFile.id)
        .filter(RawFile.batch_id == batch_id, RawFile.detected_type == 'production_xml')
        .order_by(ConfigSnapshot.id.asc())
        .all()
    )
    events = (
        db.query(Event)
        .options(selectinload(Event.file), selectinload(Event.asset))
        .filter(
            Event.file.has(batch_id=batch_id),
            or_(
                Event.category == 'alarm',
                Event.category == 'xml_event',
                Event.event_type == 'alarm_state_changed',
                Event.message.ilike('%alarm%'),
                Event.message.ilike('% alm%'),
                Event.message.ilike('%out of range%'),
            ),
        )
        .order_by(Event.occurred_at.desc(), Event.id.desc())
        .all()
    )
    management_records = {
        record.event_id: record
        for record in db.query(AlarmManagementRecord).filter(AlarmManagementRecord.event_id.in_([event.id for event in events] or [-1])).all()
    }
    points = (
        db.query(MeasurementPoint)
        .options(selectinload(MeasurementPoint.reference_parameters))
        .filter(MeasurementPoint.is_active.is_(True))
        .all()
    )
    current_parameter_ids = {parameter.id for snapshot in snapshots for parameter in snapshot.parameters}
    previous_values: dict[int, str | None] = {}
    history_by_key: dict[tuple[int, str], str | None] = {}
    asset_ids = {snapshot.asset_id for snapshot in snapshots if snapshot.asset_id is not None}
    parameter_keys = {parameter.parameter_key for snapshot in snapshots for parameter in snapshot.parameters}
    if asset_ids and parameter_keys:
        history_rows = (
            db.query(ConfigParameter, ConfigSnapshot)
            .join(ConfigSnapshot, ConfigParameter.snapshot_id == ConfigSnapshot.id)
            .join(RawFile, ConfigSnapshot.file_id == RawFile.id)
            .filter(
                ConfigSnapshot.asset_id.in_(asset_ids),
                ConfigParameter.parameter_key.in_(parameter_keys),
                RawFile.detected_type == 'production_xml',
            )
            .order_by(ConfigSnapshot.asset_id.asc(), ConfigParameter.parameter_key.asc(), ConfigSnapshot.id.asc(), ConfigParameter.id.asc())
            .all()
        )
        for parameter, history_snapshot in history_rows:
            history_key = (history_snapshot.asset_id, parameter.parameter_key)
            if parameter.id in current_parameter_ids:
                previous_values[parameter.id] = history_by_key.get(history_key)
            history_by_key[history_key] = parameter.normalized_value or parameter.raw_value
    parameters = [
        _serialize_xml_parameter(snapshot, parameter, db, points, previous_values)
        for snapshot in snapshots
        for parameter in sorted(snapshot.parameters, key=lambda item: item.parameter_key)
    ]
    alarms = [_serialize_xml_alarm(event, management_records.get(event.id), db, points) for event in events]
    totals = {
        'xml_files': len([file for file in batch.files if file.detected_type == 'production_xml']),
        'xml_001_003_parameters': len(parameters),
        'alarms': len(alarms),
        'xml_004_alarms': len([alarm for alarm in alarms if alarm.source_document == 'XML 004']),
        'xml_004_events': len([alarm for alarm in alarms if alarm.source_document == 'XML 004' and alarm.source_record_type == 'Evento']),
        'changed_parameters': len([parameter for parameter in parameters if parameter.changed]),
        'out_of_reference': len([parameter for parameter in parameters if parameter.validation_status == 'out_of_reference']),
        'without_reference': len([parameter for parameter in parameters if parameter.validation_status in {'not_configured', 'changed_without_reference'}]),
    }
    xml_files = [file for file in _serialize_batch(batch).files if file.detected_type == 'production_xml']
    return XmlMonitorSummary(
        batch_id=batch.id,
        batch_name=_friendly_source_name(batch),
        xml_files=xml_files,
        totals=totals,
        alarms=alarms,
        parameters=parameters,
    )


@app.put('/api/xml-monitor/alarms/{event_id}', response_model=XmlAlarmSummary)
def update_xml_alarm_management(event_id: int, payload: AlarmManagementUpdate, db: Session = Depends(get_db)) -> XmlAlarmSummary:
    event = (
        db.query(Event)
        .options(selectinload(Event.file), selectinload(Event.asset))
        .filter(Event.id == event_id)
        .one_or_none()
    )
    if event is None:
        raise HTTPException(status_code=404, detail='Alarme/evento não encontrado.')
    record = db.query(AlarmManagementRecord).filter(AlarmManagementRecord.event_id == event_id).one_or_none()
    if record is None:
        record = AlarmManagementRecord(event_id=event_id)
        db.add(record)
        db.flush()
    values = payload.model_dump(exclude_unset=True)
    for field_name in ('priority', 'management_status', 'assignee', 'action_correction', 'notes'):
        if field_name in values:
            setattr(record, field_name, values[field_name])
    if 'acknowledged_by' in values:
        record.acknowledged_by = values['acknowledged_by']
        record.acknowledged_at = datetime.utcnow() if values['acknowledged_by'] else None
    if 'closed_by' in values:
        record.closed_by = values['closed_by']
        record.closed_at = datetime.utcnow() if values['closed_by'] else None
        if values['closed_by']:
            record.management_status = 'closed'
    db.commit()
    db.refresh(record)
    return _serialize_xml_alarm(event, record, db)


def _unlink_paths(paths: list[Path]) -> None:
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            continue


def _delete_batch_records(batch_id: int, db: Session) -> tuple[list[Path], list[Path]]:
    batch = (
        db.query(IngestionBatch)
        .options(
            selectinload(IngestionBatch.files).selectinload(RawFile.snapshots).selectinload(ConfigSnapshot.parameters),
            selectinload(IngestionBatch.files).selectinload(RawFile.events),
        )
        .filter(IngestionBatch.id == batch_id)
        .one_or_none()
    )
    if batch is None:
        raise HTTPException(status_code=404, detail='Importação não encontrada.')

    file_paths = [Path(file.stored_path) for file in batch.files if file.stored_path]
    file_ids = [file.id for file in batch.files]
    snapshot_ids = [snapshot.id for file in batch.files for snapshot in file.snapshots]
    event_ids = [event.id for file in batch.files for event in file.events]
    asset_ids = sorted({snapshot.asset_id for file in batch.files for snapshot in file.snapshots if snapshot.asset_id is not None} | {event.asset_id for file in batch.files for event in file.events if event.asset_id is not None})
    diff_ids = [
        diff_id
        for (diff_id,) in db.query(ConfigDiff.id)
        .filter(or_(ConfigDiff.left_snapshot_id.in_(snapshot_ids or [-1]), ConfigDiff.right_snapshot_id.in_(snapshot_ids or [-1])))
        .all()
    ]
    export_paths = [
        Path(export.file_path)
        for export in db.query(ReportExport)
        .filter(ReportExport.scope_type == 'batch', ReportExport.scope_id == batch_id)
        .all()
        if export.file_path
    ]

    process_reference_records = db.query(ReferenceRecord).filter(ReferenceRecord.entity_type == 'process_reference').all()
    process_reference_ids_to_delete: list[int] = []
    for record in process_reference_records:
        metadata = json.loads(record.metadata_json or '{}')
        if metadata.get('batch_id') == batch_id or metadata.get('snapshot_id') in snapshot_ids:
            process_reference_ids_to_delete.append(record.id)

    if file_ids or event_ids or diff_ids:
        change_delete = delete(ChangeRecord).where(
            or_(
                ChangeRecord.source_file_id.in_(file_ids or [-1]),
                ChangeRecord.event_id.in_(event_ids or [-1]),
                ChangeRecord.diff_id.in_(diff_ids or [-1]),
            )
        )
        db.execute(change_delete)

    if snapshot_ids:
        db.execute(delete(Baseline).where(Baseline.snapshot_id.in_(snapshot_ids)))
        db.execute(
            delete(ConfigDiff).where(
                or_(ConfigDiff.left_snapshot_id.in_(snapshot_ids), ConfigDiff.right_snapshot_id.in_(snapshot_ids))
            )
        )
        db.execute(delete(ConfigParameter).where(ConfigParameter.snapshot_id.in_(snapshot_ids)))
        db.execute(
            delete(QaFlag).where(
                QaFlag.related_entity_type == 'config_snapshot',
                QaFlag.related_entity_id.in_(snapshot_ids),
            )
        )
        db.execute(delete(ConfigSnapshot).where(ConfigSnapshot.id.in_(snapshot_ids)))

    if event_ids:
        db.execute(delete(AlarmManagementRecord).where(AlarmManagementRecord.event_id.in_(event_ids)))
        db.execute(
            delete(QaFlag).where(
                QaFlag.related_entity_type == 'event',
                QaFlag.related_entity_id.in_(event_ids),
            )
        )
        db.execute(delete(Event).where(Event.id.in_(event_ids)))

    if file_ids:
        db.execute(delete(RawFile).where(RawFile.id.in_(file_ids)))

    db.execute(delete(IndicatorRecord).where(IndicatorRecord.batch_id == batch_id))
    db.execute(delete(ReportExport).where(ReportExport.scope_type == 'batch', ReportExport.scope_id == batch_id))
    if process_reference_ids_to_delete:
        db.execute(delete(ReferenceRecord).where(ReferenceRecord.id.in_(process_reference_ids_to_delete)))
    db.execute(delete(IngestionBatch).where(IngestionBatch.id == batch_id))

    if asset_ids:
        orphan_asset_ids = [
            asset_id
            for (asset_id,) in db.query(Asset.id)
            .filter(Asset.id.in_(asset_ids))
            .filter(~Asset.snapshots.any(), ~Asset.events.any())
            .all()
        ]
        if orphan_asset_ids:
            db.execute(delete(IndicatorRecord).where(IndicatorRecord.asset_id.in_(orphan_asset_ids)))
            db.execute(delete(Asset).where(Asset.id.in_(orphan_asset_ids)))

    return file_paths, export_paths


@app.delete('/api/ingestion/batches')
def delete_all_batches(confirm: str = Query(...), db: Session = Depends(get_db)) -> dict[str, int | bool]:
    if confirm != 'APAGAR_TODAS_IMPORTACOES':
        raise HTTPException(status_code=400, detail='Confirmação inválida. Use APAGAR_TODAS_IMPORTACOES.')

    batch_ids = [batch_id for (batch_id,) in db.query(IngestionBatch.id).all()]
    file_paths: list[Path] = []
    export_paths: list[Path] = []
    for batch_id in batch_ids:
        batch_file_paths, batch_export_paths = _delete_batch_records(batch_id, db)
        file_paths.extend(batch_file_paths)
        export_paths.extend(batch_export_paths)

    db.commit()

    _unlink_paths(file_paths)
    _unlink_paths(export_paths)

    return {'deleted': True, 'batches_deleted': len(batch_ids)}


@app.delete('/api/ingestion/batches/{batch_id}')
def delete_batch(batch_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    file_paths, export_paths = _delete_batch_records(batch_id, db)
    db.commit()

    _unlink_paths(file_paths)
    _unlink_paths(export_paths)

    return {'deleted': True}


@app.get('/api/assets', response_model=list[AssetSummary])
def list_assets(batch_id: int | None = None, db: Session = Depends(get_db)) -> list[AssetSummary]:
    query = db.query(Asset).options(
        selectinload(Asset.snapshots).selectinload(ConfigSnapshot.parameters),
        selectinload(Asset.snapshots).selectinload(ConfigSnapshot.file),
        selectinload(Asset.baselines),
        selectinload(Asset.events).selectinload(Event.file),
    )
    if batch_id is not None:
        query = query.filter(
            or_(
                Asset.snapshots.any(ConfigSnapshot.file.has(batch_id=batch_id)),
                Asset.events.any(Event.file.has(batch_id=batch_id)),
            )
        )
    assets = query.order_by(Asset.flow_computer_tag.asc()).all()
    return [_serialize_asset(asset, batch_id=batch_id) for asset in assets]


@app.get('/api/assets/{asset_id}', response_model=AssetSummary)
def get_asset(asset_id: int, db: Session = Depends(get_db)) -> AssetSummary:
    asset = (
        db.query(Asset)
        .options(
            selectinload(Asset.snapshots).selectinload(ConfigSnapshot.parameters),
            selectinload(Asset.snapshots).selectinload(ConfigSnapshot.file),
            selectinload(Asset.baselines),
        )
        .filter(Asset.id == asset_id)
        .one_or_none()
    )
    if asset is None:
        raise HTTPException(status_code=404, detail='Asset not found.')
    return _serialize_asset(asset)


@app.get('/api/assets/{asset_id}/snapshots', response_model=list[SnapshotSummary])
def get_asset_snapshots(asset_id: int, db: Session = Depends(get_db)) -> list[SnapshotSummary]:
    asset = (
        db.query(Asset)
        .options(selectinload(Asset.snapshots).selectinload(ConfigSnapshot.parameters))
        .filter(Asset.id == asset_id)
        .one_or_none()
    )
    if asset is None:
        raise HTTPException(status_code=404, detail='Asset not found.')
    return [_serialize_snapshot(snapshot, include_parameters=True) for snapshot in asset.snapshots]


@app.post('/api/assets/{asset_id}/baseline', response_model=BaselineSummary)
def set_baseline(asset_id: int, snapshot_id: int = Query(...), db: Session = Depends(get_db)) -> BaselineSummary:
    asset = db.get(Asset, asset_id)
    snapshot = db.get(ConfigSnapshot, snapshot_id)
    if asset is None or snapshot is None or snapshot.asset_id != asset_id:
        raise HTTPException(status_code=400, detail='Invalid asset or snapshot.')
    baseline = db.query(Baseline).filter(Baseline.asset_id == asset_id).one_or_none()
    if baseline is None:
        baseline = Baseline(asset_id=asset_id, snapshot_id=snapshot_id, selected_by='local-user')
        db.add(baseline)
    else:
        baseline.snapshot_id = snapshot_id
    db.commit()
    db.refresh(baseline)
    return BaselineSummary(id=baseline.id, snapshot_id=baseline.snapshot_id, selected_at=baseline.selected_at, status=baseline.status)


@app.post('/api/diffs', response_model=DiffResponse)
def create_diff(payload: DiffRequest, db: Session = Depends(get_db)) -> DiffResponse:
    left_snapshot = (
        db.query(ConfigSnapshot)
        .options(
            selectinload(ConfigSnapshot.parameters),
            selectinload(ConfigSnapshot.file).selectinload(RawFile.batch),
            selectinload(ConfigSnapshot.asset),
        )
        .filter(ConfigSnapshot.id == payload.left_snapshot_id)
        .one_or_none()
    )
    right_snapshot = (
        db.query(ConfigSnapshot)
        .options(
            selectinload(ConfigSnapshot.parameters),
            selectinload(ConfigSnapshot.file).selectinload(RawFile.batch),
            selectinload(ConfigSnapshot.asset),
        )
        .filter(ConfigSnapshot.id == payload.right_snapshot_id)
        .one_or_none()
    )
    if left_snapshot is None or right_snapshot is None:
        raise HTTPException(status_code=404, detail='Snapshot de comparação não encontrado.')
    try:
        records = compute_diff(db, payload.left_snapshot_id, payload.right_snapshot_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    left_parameter_map = {parameter.parameter_key: parameter for parameter in left_snapshot.parameters}
    right_parameter_map = {parameter.parameter_key: parameter for parameter in right_snapshot.parameters}
    process_reference_map = _load_process_reference_map(
        db,
        right_snapshot.asset.asset_key if right_snapshot.asset else left_snapshot.asset.asset_key,
    )
    fixed_reference_map = _load_fixed_reference_map(db)
    return DiffResponse(
        left_snapshot_id=payload.left_snapshot_id,
        right_snapshot_id=payload.right_snapshot_id,
        left_snapshot=_serialize_snapshot(left_snapshot, include_parameters=False),
        right_snapshot=_serialize_snapshot(right_snapshot, include_parameters=False),
        records=[
            _build_diff_record_summary(
                record,
                left_parameter_map.get(record.parameter_key),
                right_parameter_map.get(record.parameter_key),
                process_reference_map,
                fixed_reference_map,
            )
            for record in records
        ],
    )


@app.get('/api/diffs/{diff_id}', response_model=DiffRecordSummary)
def get_diff_record(diff_id: int, db: Session = Depends(get_db)) -> DiffRecordSummary:
    record = db.get(ConfigDiff, diff_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Diff record not found.')
    left_snapshot = db.get(ConfigSnapshot, record.left_snapshot_id)
    asset_key = None
    if left_snapshot is not None and left_snapshot.asset_id is not None:
        left_asset = db.get(Asset, left_snapshot.asset_id)
        asset_key = left_asset.asset_key if left_asset else None
    process_reference_map = _load_process_reference_map(db, asset_key) if asset_key else {}
    fixed_reference_map = _load_fixed_reference_map(db)
    left_parameter = None
    right_parameter = None
    if left_snapshot is not None:
        left_snapshot = (
            db.query(ConfigSnapshot)
            .options(selectinload(ConfigSnapshot.parameters))
            .filter(ConfigSnapshot.id == left_snapshot.id)
            .one_or_none()
        )
        if left_snapshot is not None:
            left_parameter = next((item for item in left_snapshot.parameters if item.parameter_key == record.parameter_key), None)
    right_snapshot = (
        db.query(ConfigSnapshot)
        .options(selectinload(ConfigSnapshot.parameters))
        .filter(ConfigSnapshot.id == record.right_snapshot_id)
        .one_or_none()
    )
    if right_snapshot is not None:
        right_parameter = next((item for item in right_snapshot.parameters if item.parameter_key == record.parameter_key), None)
    return _build_diff_record_summary(
        record,
        left_parameter,
        right_parameter,
        process_reference_map,
        fixed_reference_map,
    )


@app.get('/api/comparisons/candidates', response_model=list[ComparisonCandidateSummary])
def list_comparison_candidates(
    batch_id: int = Query(...),
    asset_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ComparisonCandidateSummary]:
    query = db.query(Asset).options(
        selectinload(Asset.snapshots).selectinload(ConfigSnapshot.parameters),
        selectinload(Asset.snapshots).selectinload(ConfigSnapshot.file),
        selectinload(Asset.events).selectinload(Event.file),
    )
    query = query.filter(
        or_(
            Asset.snapshots.any(ConfigSnapshot.file.has(batch_id=batch_id)),
            Asset.events.any(Event.file.has(batch_id=batch_id)),
        )
    )
    if asset_id is not None:
        query = query.filter(Asset.id == asset_id)
    assets = query.order_by(Asset.flow_computer_tag.asc()).all()
    return [_build_comparison_candidate(asset, batch_id) for asset in assets]


@app.get('/api/process-references', response_model=list[ProcessReferenceSummary])
def list_process_references(
    asset_id: int = Query(...),
    snapshot_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ProcessReferenceSummary]:
    asset = (
        db.query(Asset)
        .options(selectinload(Asset.snapshots).selectinload(ConfigSnapshot.parameters))
        .filter(Asset.id == asset_id)
        .one_or_none()
    )
    if asset is None:
        raise HTTPException(status_code=404, detail='Equipamento não encontrado.')
    selected_snapshot = None
    if snapshot_id is not None:
        selected_snapshot = next((snapshot for snapshot in asset.snapshots if snapshot.id == snapshot_id), None)
        if selected_snapshot is None:
            raise HTTPException(status_code=404, detail='Versão de configuração não encontrada para este equipamento.')
    else:
        selected_snapshot = next(
            iter(sorted(asset.snapshots, key=_snapshot_sort_key, reverse=True)),
            None,
        )
    if selected_snapshot is None:
        return []
    reference_map = _load_process_reference_map(db, asset.asset_key)
    candidates_by_key: dict[str, tuple[int, object]] = {}
    for parameter in sorted(selected_snapshot.parameters, key=lambda item: item.parameter_key):
        is_process_reference, kind = _looks_like_process_reference(parameter.parameter_key, parameter.parameter_label)
        if not is_process_reference:
            continue
        score = _score_process_reference_parameter(
            parameter.parameter_key,
            parameter.parameter_label,
            parameter.normalized_value,
        )
        if score <= 0:
            continue
        current_best = candidates_by_key.get(parameter.parameter_key)
        if current_best and current_best[0] >= score:
            continue
        candidates_by_key[parameter.parameter_key] = (score, parameter)

    summaries: list[ProcessReferenceSummary] = []
    for parameter_key, (_, parameter) in candidates_by_key.items():
        _, kind = _looks_like_process_reference(parameter.parameter_key, parameter.parameter_label)
        reference_item = reference_map.get(parameter.parameter_key, {})
        component_key, component_label, sort_order = _get_chromatography_component_info(
            parameter.parameter_key,
            parameter.parameter_label,
        )
        summaries.append(
            ProcessReferenceSummary(
                reference_record_id=reference_item.get('id'),
                parameter_key=parameter.parameter_key,
                parameter_label=parameter.parameter_label,
                current_value=parameter.normalized_value,
                reference_value=reference_item.get('value'),
                reference_source=reference_item.get('source'),
                snapshot_id=selected_snapshot.id,
                is_reference_defined=parameter.parameter_key in reference_map,
                kind=kind,
                component_key=component_key or reference_item.get('component_key'),
                component_label=component_label or reference_item.get('component_label'),
                sort_order=sort_order if sort_order is not None else reference_item.get('sort_order'),
            )
        )
    return sorted(
        summaries,
        key=lambda item: (
            0 if item.kind == 'density' else 1,
            item.sort_order if item.sort_order is not None else 999,
            item.component_label or item.parameter_label,
        ),
    )


@app.post('/api/process-references', response_model=ProcessReferenceSummary)
def save_process_reference(payload: ProcessReferenceUpsert, db: Session = Depends(get_db)) -> ProcessReferenceSummary:
    snapshot = (
        db.query(ConfigSnapshot)
        .options(selectinload(ConfigSnapshot.parameters), selectinload(ConfigSnapshot.asset), selectinload(ConfigSnapshot.file))
        .filter(ConfigSnapshot.id == payload.snapshot_id)
        .one_or_none()
    )
    if snapshot is None or snapshot.asset is None:
        raise HTTPException(status_code=404, detail='Versão de configuração não encontrada.')
    parameter = _select_best_process_reference_parameter(snapshot.parameters, payload.parameter_key)
    if parameter is None:
        raise HTTPException(status_code=404, detail='Parâmetro não encontrado nesta versão.')
    is_process_reference, kind = _looks_like_process_reference(parameter.parameter_key, parameter.parameter_label)
    if not is_process_reference:
        raise HTTPException(status_code=400, detail='Este parâmetro não usa referência dinâmica.')
    record_key = _reference_record_key(snapshot.asset.asset_key, parameter.parameter_key)
    metadata = {
        'asset_key': snapshot.asset.asset_key,
        'flow_computer_tag': snapshot.asset.flow_computer_tag,
        'parameter_key': parameter.parameter_key,
        'parameter_label': parameter.parameter_label,
        'reference_value': parameter.normalized_value,
        'snapshot_id': snapshot.id,
        'batch_id': snapshot.file.batch_id if snapshot.file else None,
        'saved_at': snapshot.snapshot_at.isoformat() if snapshot.snapshot_at else None,
        'kind': kind,
    }
    component_key, component_label, sort_order = _get_chromatography_component_info(
        parameter.parameter_key,
        parameter.parameter_label,
    )
    if component_key:
        metadata['component_key'] = component_key
        metadata['component_label'] = component_label
        metadata['sort_order'] = sort_order
    record = (
        db.query(ReferenceRecord)
        .filter(ReferenceRecord.entity_type == 'process_reference', ReferenceRecord.record_key == record_key)
        .one_or_none()
    )
    if record is None:
        record = ReferenceRecord(
            entity_type='process_reference',
            record_key=record_key,
            name=parameter.parameter_label,
            description=f'Referência dinâmica de {kind} para {snapshot.asset.flow_computer_tag}',
            metadata_json=json.dumps(metadata, ensure_ascii=False),
            source_label='snapshot-derived',
            is_default=False,
        )
        db.add(record)
    else:
        record.name = parameter.parameter_label
        record.description = f'Referência dinâmica de {kind} para {snapshot.asset.flow_computer_tag}'
        record.metadata_json = json.dumps(metadata, ensure_ascii=False)
        record.source_label = 'snapshot-derived'
    db.commit()
    reference_map = _load_process_reference_map(db, snapshot.asset.asset_key)
    reference_item = reference_map.get(parameter.parameter_key, {})
    return ProcessReferenceSummary(
        reference_record_id=record.id,
        parameter_key=parameter.parameter_key,
        parameter_label=parameter.parameter_label,
        current_value=parameter.normalized_value,
        reference_value=reference_item.get('value'),
        reference_source=reference_item.get('source'),
        snapshot_id=snapshot.id,
        is_reference_defined=True,
        kind=kind,
        component_key=component_key or reference_item.get('component_key'),
        component_label=component_label or reference_item.get('component_label'),
        sort_order=sort_order if sort_order is not None else reference_item.get('sort_order'),
    )


@app.delete('/api/process-references/{record_id}')
def delete_process_reference(record_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    record = (
        db.query(ReferenceRecord)
        .filter(ReferenceRecord.id == record_id, ReferenceRecord.entity_type == 'process_reference')
        .one_or_none()
    )
    if record is None:
        raise HTTPException(status_code=404, detail='Referência viva não encontrada.')
    db.delete(record)
    db.commit()
    return {'deleted': True}


@app.get('/api/meter-analysis-selections', response_model=list[MeterAnalysisSelectionSummary])
def api_list_meter_analysis_selections(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[MeterAnalysisSelectionSummary]:
    return [_serialize_meter_selection(selection) for selection in list_meter_selections(db, include_inactive)]


@app.post('/api/meter-analysis-selections', response_model=MeterAnalysisSelectionSummary)
def api_upsert_meter_analysis_selection(
    payload: MeterAnalysisSelectionUpsert,
    db: Session = Depends(get_db),
) -> MeterAnalysisSelectionSummary:
    selection = upsert_meter_selection(db, payload.model_dump())
    return _serialize_meter_selection(selection)


@app.put('/api/meter-analysis-selections/{selection_id}', response_model=MeterAnalysisSelectionSummary)
def api_update_meter_analysis_selection(
    selection_id: int,
    payload: MeterAnalysisSelectionUpsert,
    db: Session = Depends(get_db),
) -> MeterAnalysisSelectionSummary:
    selection = db.get(MeterAnalysisSelection, selection_id)
    if selection is None:
        raise HTTPException(status_code=404, detail='Seleção não encontrada.')
    for field_name, value in payload.model_dump().items():
        if field_name in {'flow_computer', 'meter_id'} and isinstance(value, str):
            value = value.strip().upper()
        setattr(selection, field_name, value)
    db.commit()
    db.refresh(selection)
    return _serialize_meter_selection(selection)


@app.delete('/api/meter-analysis-selections/{selection_id}')
def api_delete_meter_analysis_selection(selection_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    selection = db.get(MeterAnalysisSelection, selection_id)
    if selection is None:
        raise HTTPException(status_code=404, detail='Seleção não encontrada.')
    db.delete(selection)
    db.commit()
    return {'deleted': True}


@app.get('/api/measurement-points', response_model=list[MeasurementPointSummary])
def api_list_measurement_points(
    search: str | None = None,
    cv_id: str | None = None,
    tag: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[MeasurementPointSummary]:
    points = list_measurement_points(db, search=search, cv_id=cv_id, tag=tag, include_inactive=include_inactive)
    return [_serialize_measurement_point(point, include_references=False) for point in points]


@app.get('/api/measurement-points/{point_id}', response_model=MeasurementPointSummary)
def api_get_measurement_point(point_id: int, db: Session = Depends(get_db)) -> MeasurementPointSummary:
    point = (
        db.query(MeasurementPoint)
        .options(selectinload(MeasurementPoint.reference_parameters))
        .filter(MeasurementPoint.id == point_id)
        .one_or_none()
    )
    if point is None:
        raise HTTPException(status_code=404, detail='Ponto de medição não encontrado.')
    return _serialize_measurement_point(point)


@app.post('/api/measurement-points', response_model=MeasurementPointSummary)
def api_create_measurement_point(payload: MeasurementPointUpsert, db: Session = Depends(get_db)) -> MeasurementPointSummary:
    point = MeasurementPoint(**payload.model_dump())
    db.add(point)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Já existe ponto cadastrado para este CV ID e tag.') from exc
    db.refresh(point)
    return _serialize_measurement_point(point)


@app.put('/api/measurement-points/{point_id}', response_model=MeasurementPointSummary)
def api_update_measurement_point(point_id: int, payload: MeasurementPointUpsert, db: Session = Depends(get_db)) -> MeasurementPointSummary:
    point = db.get(MeasurementPoint, point_id)
    if point is None:
        raise HTTPException(status_code=404, detail='Ponto de medição não encontrado.')
    for field_name, value in payload.model_dump().items():
        setattr(point, field_name, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Já existe outro ponto cadastrado para este CV ID e tag.') from exc
    db.refresh(point)
    return _serialize_measurement_point(point)


@app.delete('/api/measurement-points/{point_id}')
def api_delete_measurement_point(point_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    point = db.get(MeasurementPoint, point_id)
    if point is None:
        raise HTTPException(status_code=404, detail='Ponto de medição não encontrado.')
    db.delete(point)
    db.commit()
    return {'deleted': True}


@app.post('/api/measurement-points/import-csv')
def api_import_measurement_points_csv(upload: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, int]:
    content = upload.file.read().decode('utf-8-sig')
    return import_measurement_points_from_csv(db, content, source_label=upload.filename or 'csv-import')


@app.post('/api/measurement-points/{point_id}/references', response_model=MeasurementReferenceParameterSummary)
def api_create_measurement_reference(
    point_id: int,
    payload: MeasurementReferenceParameterUpsert,
    db: Session = Depends(get_db),
) -> MeasurementReferenceParameterSummary:
    if db.get(MeasurementPoint, point_id) is None:
        raise HTTPException(status_code=404, detail='Ponto de medição não encontrado.')
    reference = MeasurementReferenceParameter(measurement_point_id=point_id, **payload.model_dump())
    db.add(reference)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Já existe referência para este parâmetro no ponto.') from exc
    db.refresh(reference)
    return _serialize_measurement_reference(reference)


@app.put('/api/measurement-points/{point_id}/references/{reference_id}', response_model=MeasurementReferenceParameterSummary)
def api_update_measurement_reference(
    point_id: int,
    reference_id: int,
    payload: MeasurementReferenceParameterUpsert,
    db: Session = Depends(get_db),
) -> MeasurementReferenceParameterSummary:
    reference = db.get(MeasurementReferenceParameter, reference_id)
    if reference is None or reference.measurement_point_id != point_id:
        raise HTTPException(status_code=404, detail='Referência não encontrada.')
    for field_name, value in payload.model_dump().items():
        setattr(reference, field_name, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Já existe outra referência para este parâmetro no ponto.') from exc
    db.refresh(reference)
    return _serialize_measurement_reference(reference)


@app.delete('/api/measurement-points/{point_id}/references/{reference_id}')
def api_delete_measurement_reference(point_id: int, reference_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    reference = db.get(MeasurementReferenceParameter, reference_id)
    if reference is None or reference.measurement_point_id != point_id:
        raise HTTPException(status_code=404, detail='Referência não encontrada.')
    db.delete(reference)
    db.commit()
    return {'deleted': True}


@app.post('/api/comparisons/traceable', response_model=TraceableComparisonResponse)
def api_traceable_comparison(payload: TraceableComparisonRequest, db: Session = Depends(get_db)) -> TraceableComparisonResponse:
    right_snapshot = db.get(ConfigSnapshot, payload.right_snapshot_id)
    if right_snapshot is None:
        raise HTTPException(status_code=404, detail='Snapshot atual não encontrado.')
    left_snapshot_id = payload.left_snapshot_id
    if left_snapshot_id is None:
        historical = (
            db.query(ConfigSnapshot)
            .filter(ConfigSnapshot.asset_id == right_snapshot.asset_id, ConfigSnapshot.id != right_snapshot.id)
            .order_by(ConfigSnapshot.snapshot_at.desc(), ConfigSnapshot.id.desc())
            .first()
        )
        if historical is None:
            raise HTTPException(status_code=400, detail='Nenhum snapshot de referência encontrado para este ativo.')
        left_snapshot_id = historical.id
    left_snapshot = db.get(ConfigSnapshot, left_snapshot_id)
    if left_snapshot is None:
        raise HTTPException(status_code=404, detail='Snapshot de referência não encontrado.')
    is_cross_equipment = left_snapshot.asset_id != right_snapshot.asset_id
    if is_cross_equipment and not payload.allow_cross_equipment:
        raise HTTPException(status_code=409, detail='Comparação entre equipamentos diferentes exige confirmação explícita.')
    point = db.get(MeasurementPoint, payload.measurement_point_id) if payload.measurement_point_id else None
    try:
        diff_records = compute_diff(db, left_snapshot_id, payload.right_snapshot_id)
        change_records = (
            create_change_records_for_diffs(
                db,
                left_snapshot_id=left_snapshot_id,
                right_snapshot_id=payload.right_snapshot_id,
                measurement_point=point,
            )
            if payload.create_change_records
            else []
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    left_snapshot = (
        db.query(ConfigSnapshot)
        .options(selectinload(ConfigSnapshot.parameters), selectinload(ConfigSnapshot.asset))
        .filter(ConfigSnapshot.id == left_snapshot_id)
        .one()
    )
    right_snapshot = (
        db.query(ConfigSnapshot)
        .options(selectinload(ConfigSnapshot.parameters), selectinload(ConfigSnapshot.asset))
        .filter(ConfigSnapshot.id == payload.right_snapshot_id)
        .one()
    )
    left_parameter_map = {parameter.parameter_key: parameter for parameter in left_snapshot.parameters}
    right_parameter_map = {parameter.parameter_key: parameter for parameter in right_snapshot.parameters}
    process_reference_map = _load_process_reference_map(
        db,
        right_snapshot.asset.asset_key if right_snapshot.asset else left_snapshot.asset.asset_key,
    )
    fixed_reference_map = _load_fixed_reference_map(db)
    return TraceableComparisonResponse(
        left_snapshot_id=left_snapshot_id,
        right_snapshot_id=payload.right_snapshot_id,
        measurement_point=_serialize_measurement_point(point, include_references=False) if point else None,
        is_cross_equipment=is_cross_equipment,
        records=[
            _build_diff_record_summary(
                record,
                left_parameter_map.get(record.parameter_key),
                right_parameter_map.get(record.parameter_key),
                process_reference_map,
                fixed_reference_map,
            )
            for record in diff_records
        ],
        change_records=[_serialize_change_record(record) for record in change_records],
    )


@app.get('/api/change-records', response_model=list[ChangeRecordSummary])
def api_list_change_records(
    measurement_point_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
) -> list[ChangeRecordSummary]:
    query = db.query(ChangeRecord)
    if measurement_point_id is not None:
        query = query.filter(ChangeRecord.measurement_point_id == measurement_point_id)
    if status:
        query = query.filter(ChangeRecord.status == status)
    if severity:
        query = query.filter(ChangeRecord.severity == severity)
    records = query.order_by(ChangeRecord.detected_at.desc()).limit(300).all()
    return [_serialize_change_record(record) for record in records]


@app.put('/api/change-records/{record_id}', response_model=ChangeRecordSummary)
def api_update_change_record(record_id: int, payload: ChangeRecordUpdate, db: Session = Depends(get_db)) -> ChangeRecordSummary:
    record = db.get(ChangeRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Registro de alteração não encontrado.')
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field_name, value)
    db.commit()
    db.refresh(record)
    return _serialize_change_record(record)


@app.get('/api/events', response_model=list[EventSummary])
def list_events(asset_id: int | None = None, batch_id: int | None = None, db: Session = Depends(get_db)) -> list[EventSummary]:
    query = db.query(Event).options(selectinload(Event.file))
    if asset_id is not None:
        query = query.filter(Event.asset_id == asset_id)
    if batch_id is not None:
        query = query.filter(Event.file.has(batch_id=batch_id))
    events = query.order_by(Event.occurred_at.desc()).limit(200).all()
    return [
        EventSummary(
            id=event.id,
            file_id=event.file_id,
            batch_id=event.file.batch_id if event.file else None,
            source_file_name=event.file.original_name if event.file else None,
            occurred_at=event.occurred_at,
            run_number=event.run_number,
            event_type=event.event_type,
            category=event.category,
            severity=event.severity,
            actor=event.actor,
            source_ip=event.source_ip,
            message=event.message,
            old_value=event.old_value,
            new_value=event.new_value,
        )
        for event in events
    ]


@app.get('/api/assets/{asset_id}/events', response_model=list[EventSummary])
def list_asset_events(asset_id: int, db: Session = Depends(get_db)) -> list[EventSummary]:
    return list_events(asset_id=asset_id, db=db)


@app.get('/api/events/intelligence', response_model=EventIntelligenceSummary)
def event_intelligence(asset_id: int | None = None, batch_id: int | None = None, db: Session = Depends(get_db)) -> EventIntelligenceSummary:
    summary = summarize_event_patterns(db, asset_id=asset_id, batch_id=batch_id)
    persist_event_flags(db, summary)
    return EventIntelligenceSummary(**summary)


@app.get('/api/qa-flags', response_model=list[QaFlagSummary])
def list_qa_flags(
    asset_id: int | None = None,
    related_entity_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[QaFlagSummary]:
    query = db.query(QaFlag)
    if asset_id is not None:
        query = query.filter(QaFlag.related_entity_type == 'asset', QaFlag.related_entity_id == asset_id)
    if related_entity_type is not None:
        query = query.filter(QaFlag.related_entity_type == related_entity_type)
    flags = query.order_by(QaFlag.created_at.desc()).limit(200).all()
    return [
        QaFlagSummary(
            id=flag.id,
            related_entity_type=flag.related_entity_type,
            related_entity_id=flag.related_entity_id,
            flag_type=flag.flag_type,
            severity=flag.severity,
            message=flag.message,
            created_at=flag.created_at,
        )
        for flag in flags
    ]


@app.get('/api/reports/exports', response_model=list[ReportExportSummary])
def list_report_exports(db: Session = Depends(get_db)) -> list[ReportExportSummary]:
    exports = db.query(ReportExport).order_by(ReportExport.created_at.desc()).limit(100).all()
    return [
        ReportExportSummary(
            id=export.id,
            scope_type=export.scope_type,
            scope_id=export.scope_id,
            format=export.format,
            file_path=export.file_path,
            created_at=export.created_at,
        )
        for export in exports
    ]


@app.post('/api/reports/technical', response_model=ReportResponse)
def generate_report(payload: ReportRequest, db: Session = Depends(get_db)) -> ReportResponse:
    try:
        export, content = create_report(
            db,
            batch_id=payload.batch_id,
            left_snapshot_id=payload.diff_left_snapshot_id,
            right_snapshot_id=payload.diff_right_snapshot_id,
            export_format=payload.format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ReportResponse(report_id=export.id, file_path=export.file_path, content=content, format=export.format)


@app.get('/api/config/reference-records', response_model=list[ReferenceRecordSummary])
def list_reference_records(
    entity_type: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> list[ReferenceRecordSummary]:
    query = db.query(ReferenceRecord)
    if entity_type:
        query = query.filter(ReferenceRecord.entity_type == entity_type)
    if search:
        token = f'%{search.strip()}%'
        query = query.filter(
            or_(
                ReferenceRecord.name.ilike(token),
                ReferenceRecord.record_key.ilike(token),
                ReferenceRecord.description.ilike(token),
            )
        )
    records = query.order_by(ReferenceRecord.entity_type.asc(), ReferenceRecord.name.asc()).all()
    return [_serialize_reference_record(record) for record in records]


@app.post('/api/config/reference-records', response_model=ReferenceRecordSummary)
def create_reference_record(payload: ReferenceRecordUpsert, db: Session = Depends(get_db)) -> ReferenceRecordSummary:
    record = ReferenceRecord(
        entity_type=payload.entity_type,
        record_key=payload.record_key,
        name=payload.name,
        description=payload.description,
        metadata_json=json.dumps(payload.metadata, ensure_ascii=False),
        source_label=payload.source_label,
        is_default=payload.is_default,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ja existe um cadastro com este tipo e chave.') from exc
    db.refresh(record)
    return _serialize_reference_record(record)


@app.put('/api/config/reference-records/{record_id}', response_model=ReferenceRecordSummary)
def update_reference_record(
    record_id: int,
    payload: ReferenceRecordUpsert,
    db: Session = Depends(get_db),
) -> ReferenceRecordSummary:
    record = db.get(ReferenceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Reference record not found.')
    record.entity_type = payload.entity_type
    record.record_key = payload.record_key
    record.name = payload.name
    record.description = payload.description
    record.metadata_json = json.dumps(payload.metadata, ensure_ascii=False)
    record.source_label = payload.source_label
    record.is_default = payload.is_default
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ja existe outro cadastro com este tipo e chave.') from exc
    db.refresh(record)
    return _serialize_reference_record(record)


@app.delete('/api/config/reference-records/{record_id}')
def delete_reference_record(record_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    record = db.get(ReferenceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Reference record not found.')
    db.delete(record)
    db.commit()
    return {'deleted': True}


@app.get('/api/config/technical-references', response_model=list[TechnicalReferenceSummary])
def list_technical_references(
    category: str | None = None,
    db: Session = Depends(get_db),
) -> list[TechnicalReferenceSummary]:
    query = db.query(TechnicalReference)
    if category:
        query = query.filter(TechnicalReference.category == category)
    records = query.order_by(TechnicalReference.category.asc(), TechnicalReference.title.asc()).all()
    return [_serialize_technical_reference(record) for record in records]


@app.get('/api/config/indicator-rules', response_model=list[IndicatorRuleSummary])
def list_indicator_rules(db: Session = Depends(get_db)) -> list[IndicatorRuleSummary]:
    rules = db.query(IndicatorRule).order_by(IndicatorRule.name.asc()).all()
    return [_serialize_indicator_rule(rule) for rule in rules]


@app.post('/api/config/indicator-rules', response_model=IndicatorRuleSummary)
def create_indicator_rule(payload: IndicatorRuleUpsert, db: Session = Depends(get_db)) -> IndicatorRuleSummary:
    rule = IndicatorRule(**payload.model_dump())
    db.add(rule)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ja existe uma regra com esta chave.') from exc
    db.refresh(rule)
    return _serialize_indicator_rule(rule)


@app.put('/api/config/indicator-rules/{rule_id}', response_model=IndicatorRuleSummary)
def update_indicator_rule(rule_id: int, payload: IndicatorRuleUpsert, db: Session = Depends(get_db)) -> IndicatorRuleSummary:
    rule = db.get(IndicatorRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail='Indicator rule not found.')
    for field_name, value in payload.model_dump().items():
        setattr(rule, field_name, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ja existe outra regra com esta chave.') from exc
    db.refresh(rule)
    return _serialize_indicator_rule(rule)


@app.delete('/api/config/indicator-rules/{rule_id}')
def delete_indicator_rule(rule_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    rule = db.get(IndicatorRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail='Indicator rule not found.')
    db.delete(rule)
    db.commit()
    return {'deleted': True}


@app.get('/api/indicators', response_model=list[IndicatorRecordSummary])
def list_indicators(asset_id: int | None = None, batch_id: int | None = None, db: Session = Depends(get_db)) -> list[IndicatorRecordSummary]:
    records = evaluate_indicators(db, asset_id=asset_id, batch_id=batch_id)
    return [_serialize_indicator(record) for record in records]


@app.get('/', response_model=None)
def serve_frontend_root():
    if FRONTEND_INDEX.exists():
        return frontend_file_response(FRONTEND_INDEX, cache_control='no-store')
    return JSONResponse(
        status_code=503,
        content={
            'detail': 'Frontend compilado não encontrado. Gere frontend/dist antes de distribuir o pacote.',
        },
    )


@app.get('/carga-pasta', response_model=None)
def serve_folder_ingestion_page():
    page = FRONTEND_DIST / 'carga-pasta.html'
    if page.exists():
        return frontend_file_response(page, cache_control='no-store')
    raise HTTPException(status_code=404, detail='Página de carga por pasta não encontrada.')


@app.get('/xml-monitor', response_model=None)
def serve_xml_monitor_page():
    page = FRONTEND_DIST / 'xml-monitor.html'
    if page.exists():
        return frontend_file_response(page, cache_control='no-store')
    raise HTTPException(status_code=404, detail='Página de monitoramento XML não encontrada.')


@app.get('/{full_path:path}', response_model=None)
def serve_frontend_asset(full_path: str):
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='API route not found.')
    if not FRONTEND_DIST.exists():
        return JSONResponse(
            status_code=503,
            content={
                'detail': 'Frontend compilado não encontrado. Gere frontend/dist antes de distribuir o pacote.',
            },
        )

    candidate = (FRONTEND_DIST / full_path).resolve()
    try:
        candidate.relative_to(FRONTEND_DIST.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Asset not found.') from exc

    if candidate.is_file():
        cache_control = 'public, max-age=31536000, immutable' if candidate.suffix in {'.js', '.css'} else 'no-store'
        return frontend_file_response(candidate, cache_control=cache_control)
    if FRONTEND_INDEX.exists():
        return frontend_file_response(FRONTEND_INDEX, cache_control='no-store')
    raise HTTPException(status_code=404, detail='Asset not found.')
