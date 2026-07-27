from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import MeasurementPoint, MeterAnalysisSelection

DEFAULT_FLOW_COMPUTERS = {'FC01', 'FC03', 'FC16', 'FC17', 'FC18'}


def seed_default_meter_selections(session: Session) -> None:
    points = (
        session.query(MeasurementPoint)
        .filter(MeasurementPoint.cv_id.in_(DEFAULT_FLOW_COMPUTERS), MeasurementPoint.is_active.is_(True))
        .all()
    )
    for point in points:
        existing = (
            session.query(MeterAnalysisSelection)
            .filter(
                MeterAnalysisSelection.flow_computer == point.cv_id,
                MeterAnalysisSelection.meter_id == point.tag,
            )
            .one_or_none()
        )
        if existing is not None:
            continue
        session.add(
            MeterAnalysisSelection(
                flow_computer=point.cv_id,
                meter_id=point.tag,
                measurement_point_id=point.id,
                is_active=True,
                is_default=True,
                source_label='default',
                notes='Selecao default criada a partir do cadastro de pontos de medicao.',
            )
        )
    session.commit()


def list_meter_selections(session: Session, include_inactive: bool = False) -> list[MeterAnalysisSelection]:
    query = session.query(MeterAnalysisSelection).order_by(MeterAnalysisSelection.flow_computer, MeterAnalysisSelection.meter_id)
    if not include_inactive:
        query = query.filter(MeterAnalysisSelection.is_active.is_(True))
    return query.all()


def upsert_meter_selection(session: Session, values: dict) -> MeterAnalysisSelection:
    flow_computer = values['flow_computer'].strip().upper()
    meter_id = values['meter_id'].strip().upper()
    existing = (
        session.query(MeterAnalysisSelection)
        .filter(MeterAnalysisSelection.flow_computer == flow_computer, MeterAnalysisSelection.meter_id == meter_id)
        .one_or_none()
    )
    point_id = values.get('measurement_point_id')
    if point_id is None:
        point = (
            session.query(MeasurementPoint)
            .filter(MeasurementPoint.cv_id == flow_computer, MeasurementPoint.tag == meter_id)
            .one_or_none()
        )
        point_id = point.id if point else None
    payload = {
        'flow_computer': flow_computer,
        'meter_id': meter_id,
        'measurement_point_id': point_id,
        'is_active': values.get('is_active', True),
        'is_default': values.get('is_default', False),
        'source_label': values.get('source_label', 'user-config'),
        'notes': values.get('notes'),
    }
    if existing is None:
        selection = MeterAnalysisSelection(**payload)
        session.add(selection)
        session.commit()
        session.refresh(selection)
        return selection
    for field_name, value in payload.items():
        setattr(existing, field_name, value)
    session.commit()
    session.refresh(existing)
    return existing
