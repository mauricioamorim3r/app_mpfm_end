from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import MeasurementPoint, MeasurementReferenceParameter

REFERENCE_DATA_DIR = Path(__file__).resolve().parents[1] / 'reference_data'
MEASUREMENT_POINTS_FILE = REFERENCE_DATA_DIR / 'measurement_points.json'


def normalize_tag(value: str | None) -> str:
    return ''.join(character for character in str(value or '').upper() if character.isalnum())


POINT_FIELDS = {
    'cv_tag_device': ('cv_tag_device', 'CV TAG Device'),
    'cv_serial_number': ('cv_serial_number', 'CV N/S'),
    'cv_version': ('cv_version', 'CV_Version'),
    'cv_application_name': ('cv_application_name', 'CV_AplicaoName', 'CV_AplicacaoName', 'CV_AplicaçãoName'),
    'cv_application_date': ('cv_application_date', 'CV_ApplicationDate'),
    'cv_application_version': ('cv_application_version', 'CV_ApplicationVersion'),
    'cv_ip_address': ('cv_ip_address', 'CV IP Address'),
    'cv_connected_system_name': ('cv_connected_system_name', 'CV_SistConectadoName'),
    'system_group': ('system_group', 'System / Group'),
    'fluid': ('fluid', 'Fluido'),
    'measurement_point_name': ('measurement_point_name', 'Nome Ponto Medicao', 'Nome Ponto Medição'),
    'measurement_technology': ('measurement_technology', 'Tecnologia'),
    'connected_system': ('connected_system', 'CV_SistConectadoName', 'Sistema Conectado'),
    'classification': ('classification', 'System / Group', 'Classificacao', 'Classificação'),
    'asset_key': ('asset_key',),
    'run_number': ('run_number',),
    'is_redundant': ('is_redundant',),
    'is_active': ('is_active',),
    'notes': ('notes',),
}


def _row_value(row: dict, *keys: str) -> object:
    for key in keys:
        if key in row and row[key] not in (None, ''):
            return row[key]
    return None


def _point_values(row: dict, *, source_label: str) -> dict:
    values: dict[str, object] = {}
    for field_name, keys in POINT_FIELDS.items():
        value = _row_value(row, *keys)
        if value is None:
            continue
        if field_name in {'is_redundant', 'is_active'}:
            if isinstance(value, str):
                values[field_name] = value.strip().lower() not in {'0', 'false', 'falso', 'nao', 'não', 'no'}
            else:
                values[field_name] = bool(value)
        elif field_name == 'run_number':
            try:
                values[field_name] = int(value)
            except (TypeError, ValueError):
                continue
        else:
            values[field_name] = str(value).strip()
    values.setdefault('source_label', source_label)
    return values


def seed_measurement_points(session: Session) -> None:
    if not MEASUREMENT_POINTS_FILE.exists():
        return
    rows = json.loads(MEASUREMENT_POINTS_FILE.read_text(encoding='utf-8'))
    active_seed_keys: set[tuple[str, str]] = set()
    for row in rows:
        cv_id = str(row.get('cv_id') or '').strip()
        tag = str(row.get('tag') or '').strip()
        if not cv_id or not tag:
            continue
        active_seed_keys.add((cv_id, tag))
        existing = (
            session.query(MeasurementPoint)
            .filter(MeasurementPoint.cv_id == cv_id, MeasurementPoint.tag == tag)
            .one_or_none()
        )
        values = _point_values(row, source_label='seed:cv-register')
        values.setdefault('fluid', '')
        values.setdefault('measurement_point_name', '')
        values.setdefault('measurement_technology', '')
        values.setdefault('classification', '')
        values.setdefault('connected_system', row.get('cv_connected_system_name') or row.get('CV_SistConectadoName'))
        values.setdefault('is_redundant', 'REDUNDANCIA' in normalize_tag(tag))
        values.setdefault('is_active', True)
        if existing is None:
            session.add(MeasurementPoint(cv_id=cv_id, tag=tag, **values))
        else:
            for field_name, value in values.items():
                setattr(existing, field_name, value)
    stale_seed_points = (
        session.query(MeasurementPoint)
        .filter(MeasurementPoint.source_label.like('seed:%'))
        .all()
    )
    for point in stale_seed_points:
        if (point.cv_id, point.tag) not in active_seed_keys:
            point.is_active = False
    session.commit()


def list_measurement_points(
    session: Session,
    *,
    search: str | None = None,
    cv_id: str | None = None,
    tag: str | None = None,
    include_inactive: bool = False,
) -> list[MeasurementPoint]:
    query = session.query(MeasurementPoint)
    if not include_inactive:
        query = query.filter(MeasurementPoint.is_active.is_(True))
    if cv_id:
        query = query.filter(MeasurementPoint.cv_id == cv_id)
    if tag:
        normalized = normalize_tag(tag)
        query = query.filter(MeasurementPoint.tag.ilike(f'%{normalized}%') | MeasurementPoint.tag.ilike(f'%{tag.strip()}%'))
    if search:
        token = f'%{search.strip()}%'
        query = query.filter(
            or_(
                MeasurementPoint.cv_id.ilike(token),
                MeasurementPoint.tag.ilike(token),
                MeasurementPoint.measurement_point_name.ilike(token),
                MeasurementPoint.connected_system.ilike(token),
                MeasurementPoint.classification.ilike(token),
                MeasurementPoint.fluid.ilike(token),
                MeasurementPoint.cv_tag_device.ilike(token),
                MeasurementPoint.cv_serial_number.ilike(token),
                MeasurementPoint.cv_application_name.ilike(token),
                MeasurementPoint.cv_ip_address.ilike(token),
                MeasurementPoint.cv_connected_system_name.ilike(token),
                MeasurementPoint.system_group.ilike(token),
            )
        )
    return query.order_by(MeasurementPoint.cv_id.asc(), MeasurementPoint.tag.asc()).all()


def find_measurement_point_for_context(
    session: Session,
    *,
    asset_key: str | None = None,
    tag: str | None = None,
    run_number: int | None = None,
    parameter_text: str | None = None,
) -> MeasurementPoint | None:
    candidates = session.query(MeasurementPoint).filter(MeasurementPoint.is_active.is_(True)).all()
    if not candidates:
        return None
    normalized_text = normalize_tag(parameter_text)
    normalized_tag = normalize_tag(tag)
    for candidate in candidates:
        candidate_tag = normalize_tag(candidate.tag)
        candidate_cv_device = normalize_tag(candidate.cv_tag_device)
        candidate_cv_serial = normalize_tag(candidate.cv_serial_number)
        if normalized_tag and candidate_tag == normalized_tag:
            return candidate
        if normalized_tag and normalized_tag in {candidate_cv_device, candidate_cv_serial} and (run_number is None or candidate.run_number == run_number):
            return candidate
        if normalized_text and candidate_tag and candidate_tag in normalized_text:
            return candidate
    if asset_key:
        asset_candidates = [candidate for candidate in candidates if candidate.asset_key == asset_key]
        if len(asset_candidates) == 1:
            return asset_candidates[0]
        if run_number is not None:
            for candidate in asset_candidates:
                if candidate.run_number == run_number:
                    return candidate
    if run_number is not None and normalized_text:
        for candidate in candidates:
            if candidate.run_number == run_number and normalize_tag(candidate.tag) in normalized_text:
                return candidate
    return None


def reference_parameter_matches(parameter_key: str, reference: MeasurementReferenceParameter) -> bool:
    key = parameter_key.lower()
    reference_key = reference.parameter_key.lower()
    return key == reference_key or reference_key in key or key in reference_key


def import_measurement_points_from_csv(session: Session, text: str, *, source_label: str = 'csv-import') -> dict[str, int]:
    reader = csv.DictReader(text.splitlines())
    created = 0
    updated = 0
    for row in reader:
        cv_id = (row.get('cv_id') or row.get('CV ID') or '').strip()
        tag = (row.get('tag') or row.get('TAG') or '').strip()
        if not cv_id or not tag:
            continue
        record = session.query(MeasurementPoint).filter(MeasurementPoint.cv_id == cv_id, MeasurementPoint.tag == tag).one_or_none()
        values = {
            **_point_values(row, source_label=source_label),
        }
        if record is None:
            session.add(MeasurementPoint(cv_id=cv_id, tag=tag, **values))
            created += 1
        else:
            for field_name, value in values.items():
                setattr(record, field_name, value)
            updated += 1
    session.commit()
    return {'created': created, 'updated': updated}
