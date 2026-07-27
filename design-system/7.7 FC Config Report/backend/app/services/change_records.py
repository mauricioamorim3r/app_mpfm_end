from __future__ import annotations

import json
import re
from datetime import timedelta

from sqlalchemy.orm import Session

from ..models import ChangeRecord, ConfigDiff, ConfigSnapshot, Event, MeasurementPoint
from .measurement_points import find_measurement_point_for_context

CRITICAL_PARAMETER_TOKENS = (
    'hart high scale',
    'high high alarm',
    'high alarm',
    'low low alarm',
    'low alarm',
    'override',
    'meter factor',
    'k-factor',
    'calibration',
    'density',
    'composition',
    'pulse',
    'range',
    'dpa',
    'diff. pressure',
    'differential pressure',
)


def _extract_run_number(text: str | None) -> int | None:
    match = re.search(r'run\s+(\d+)', text or '', flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _classify_change(parameter_label: str, category: str, severity: str) -> tuple[str, str, str]:
    label = parameter_label.lower()
    if any(token in label for token in CRITICAL_PARAMETER_TOKENS):
        if any(token in label for token in ('meter factor', 'k-factor', 'calibration', 'density', 'composition')):
            return 'metrological', 'critical', 'Mudanca em parametro metrologico critico requer registro formal e verificacao.'
        return 'metrological', 'high', 'Mudanca pode afetar range, alarmes, override ou comportamento de medicao.'
    return category, severity, 'Mudanca operacional detectada e registrada para rastreabilidade.'


def _find_related_event(session: Session, snapshot: ConfigSnapshot, diff: ConfigDiff) -> Event | None:
    if snapshot.asset_id is None or snapshot.snapshot_at is None:
        return None
    run_number = _extract_run_number(f'{diff.parameter_key} {diff.parameter_label}')
    lower_label = diff.parameter_label.lower()
    window_start = snapshot.snapshot_at - timedelta(days=3)
    window_end = snapshot.snapshot_at + timedelta(days=1)
    query = (
        session.query(Event)
        .filter(Event.asset_id == snapshot.asset_id)
        .filter(Event.occurred_at >= window_start, Event.occurred_at <= window_end)
    )
    if run_number is not None:
        query = query.filter((Event.run_number == run_number) | Event.message.ilike(f'%Run {run_number}%'))
    events = query.order_by(Event.occurred_at.desc()).all()
    for event in events:
        message = event.message.lower()
        if diff.left_value and str(diff.left_value).lower() in message and diff.right_value and str(diff.right_value).lower() in message:
            return event
        label_tokens = [token for token in re.split(r'\W+', lower_label) if len(token) > 3]
        if any(token in message for token in label_tokens):
            return event
    return None


def create_change_records_for_diffs(
    session: Session,
    *,
    left_snapshot_id: int,
    right_snapshot_id: int,
    measurement_point: MeasurementPoint | None = None,
) -> list[ChangeRecord]:
    right_snapshot = session.get(ConfigSnapshot, right_snapshot_id)
    if right_snapshot is None:
        raise ValueError('Snapshot not found.')
    diffs = (
        session.query(ConfigDiff)
        .filter(ConfigDiff.left_snapshot_id == left_snapshot_id, ConfigDiff.right_snapshot_id == right_snapshot_id)
        .order_by(ConfigDiff.severity.desc(), ConfigDiff.parameter_label.asc())
        .all()
    )
    created: list[ChangeRecord] = []
    for diff in diffs:
        if diff.severity not in {'critical', 'high'}:
            continue
        run_number = _extract_run_number(f'{diff.parameter_key} {diff.parameter_label}')
        point = measurement_point or find_measurement_point_for_context(
            session,
            asset_key=right_snapshot.asset.asset_key if right_snapshot.asset else None,
            run_number=run_number,
            parameter_text=f'{diff.parameter_key} {diff.parameter_label}',
        )
        event = _find_related_event(session, right_snapshot, diff)
        category, severity, impact_summary = _classify_change(diff.parameter_label, diff.category, diff.severity)
        existing = session.query(ChangeRecord).filter(ChangeRecord.diff_id == diff.id).one_or_none()
        if existing is not None:
            created.append(existing)
            continue
        evidence = {
            'left_snapshot_id': left_snapshot_id,
            'right_snapshot_id': right_snapshot_id,
            'source_file': right_snapshot.file.original_name if right_snapshot.file else None,
            'event_message': event.message if event else None,
            'event_old_value': event.old_value if event else None,
            'event_new_value': event.new_value if event else None,
        }
        record = ChangeRecord(
            measurement_point_id=point.id if point else None,
            asset_id=right_snapshot.asset_id,
            diff_id=diff.id,
            event_id=event.id if event else None,
            source_file_id=right_snapshot.file_id,
            cv_id=point.cv_id if point else None,
            tag=point.tag if point else None,
            run_number=run_number or (point.run_number if point else None),
            parameter_key=diff.parameter_key,
            parameter_label=diff.parameter_label,
            old_value=diff.left_value,
            new_value=diff.right_value,
            change_type=diff.change_type,
            category=category,
            severity=severity,
            status='open',
            actor=event.actor if event else None,
            source_ip=event.source_ip if event else None,
            occurred_at=event.occurred_at if event else right_snapshot.snapshot_at,
            impact_summary=impact_summary,
            recommendation='Abrir/atualizar registro formal de mudanca, confirmar justificativa tecnica, aprovacao e impacto metrologico.',
            evidence_json=json.dumps(evidence, ensure_ascii=False),
        )
        session.add(record)
        created.append(record)
    session.commit()
    return created
