from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class IngestionBatch(Base):
    __tablename__ = 'ingestion_batches'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    files: Mapped[list['RawFile']] = relationship(back_populates='batch', cascade='all, delete-orphan')


class RawFile(Base):
    __tablename__ = 'files_raw'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingestion_batches.id'))
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    detected_type: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    parse_status: Mapped[str] = mapped_column(String(50), default='pending')
    parse_warning: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch: Mapped[IngestionBatch] = relationship(back_populates='files')
    snapshots: Mapped[list['ConfigSnapshot']] = relationship(back_populates='file')
    events: Mapped[list['Event']] = relationship(back_populates='file')


class Asset(Base):
    __tablename__ = 'assets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_key: Mapped[str] = mapped_column(String(255), unique=True)
    flow_computer_tag: Mapped[str] = mapped_column(String(255))
    system_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    snapshots: Mapped[list['ConfigSnapshot']] = relationship(back_populates='asset')
    events: Mapped[list['Event']] = relationship(back_populates='asset')
    baselines: Mapped[list['Baseline']] = relationship(back_populates='asset')


class MeasurementPoint(Base):
    __tablename__ = 'measurement_points'
    __table_args__ = (UniqueConstraint('cv_id', 'tag', name='uq_measurement_point_cv_tag'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_id: Mapped[str] = mapped_column(String(100), index=True)
    cv_tag_device: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    cv_serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    cv_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cv_application_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cv_application_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cv_application_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cv_ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    cv_connected_system_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_group: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    fluid: Mapped[str] = mapped_column(String(100), index=True)
    measurement_point_name: Mapped[str] = mapped_column(String(255))
    measurement_technology: Mapped[str] = mapped_column(String(255))
    tag: Mapped[str] = mapped_column(String(100), index=True)
    connected_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[str] = mapped_column(String(100), index=True)
    asset_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    run_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_redundant: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_label: Mapped[str] = mapped_column(String(255), default='user-config')
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reference_parameters: Mapped[list['MeasurementReferenceParameter']] = relationship(
        back_populates='measurement_point',
        cascade='all, delete-orphan',
    )
    change_records: Mapped[list['ChangeRecord']] = relationship(back_populates='measurement_point')


class MeasurementReferenceParameter(Base):
    __tablename__ = 'measurement_reference_parameters'
    __table_args__ = (UniqueConstraint('measurement_point_id', 'parameter_key', name='uq_measurement_reference_parameter'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    measurement_point_id: Mapped[int] = mapped_column(ForeignKey('measurement_points.id'))
    parameter_key: Mapped[str] = mapped_column(String(255), index=True)
    parameter_label: Mapped[str] = mapped_column(String(255))
    reference_kind: Mapped[str] = mapped_column(String(100), default='critical_parameter')
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_low_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_high_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    tolerance: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(50), default='high')
    source_label: Mapped[str] = mapped_column(String(255), default='user-config')
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    measurement_point: Mapped[MeasurementPoint] = relationship(back_populates='reference_parameters')


class MeterAnalysisSelection(Base):
    __tablename__ = 'meter_analysis_selections'
    __table_args__ = (UniqueConstraint('flow_computer', 'meter_id', name='uq_meter_analysis_selection'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flow_computer: Mapped[str] = mapped_column(String(100), index=True)
    meter_id: Mapped[str] = mapped_column(String(100), index=True)
    measurement_point_id: Mapped[int | None] = mapped_column(ForeignKey('measurement_points.id'), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    source_label: Mapped[str] = mapped_column(String(255), default='user-config')
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    measurement_point: Mapped[MeasurementPoint | None] = relationship()


class ConfigSnapshot(Base):
    __tablename__ = 'config_snapshots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    file_id: Mapped[int] = mapped_column(ForeignKey('files_raw.id'))
    snapshot_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    application_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(50))

    asset: Mapped[Asset] = relationship(back_populates='snapshots')
    file: Mapped[RawFile] = relationship(back_populates='snapshots')
    parameters: Mapped[list['ConfigParameter']] = relationship(
        back_populates='snapshot',
        cascade='all, delete-orphan',
    )


class ConfigParameter(Base):
    __tablename__ = 'config_parameters'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('config_snapshots.id'))
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parameter_key: Mapped[str] = mapped_column(String(255))
    parameter_label: Mapped[str] = mapped_column(String(255))
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    snapshot: Mapped[ConfigSnapshot] = relationship(back_populates='parameters')


class Baseline(Base):
    __tablename__ = 'baselines'
    __table_args__ = (UniqueConstraint('asset_id', name='uq_baseline_asset_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('config_snapshots.id'))
    status: Mapped[str] = mapped_column(String(50), default='official')
    selected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    selected_by: Mapped[str] = mapped_column(String(255), default='local-user')

    asset: Mapped[Asset] = relationship(back_populates='baselines')


class ConfigDiff(Base):
    __tablename__ = 'config_diffs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    left_snapshot_id: Mapped[int] = mapped_column(ForeignKey('config_snapshots.id'))
    right_snapshot_id: Mapped[int] = mapped_column(ForeignKey('config_snapshots.id'))
    parameter_key: Mapped[str] = mapped_column(String(255))
    parameter_label: Mapped[str] = mapped_column(String(255))
    left_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    right_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_type: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(50))
    impact_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChangeRecord(Base):
    __tablename__ = 'change_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    measurement_point_id: Mapped[int | None] = mapped_column(ForeignKey('measurement_points.id'), nullable=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey('assets.id'), nullable=True)
    diff_id: Mapped[int | None] = mapped_column(ForeignKey('config_diffs.id'), nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey('events.id'), nullable=True)
    source_file_id: Mapped[int | None] = mapped_column(ForeignKey('files_raw.id'), nullable=True)
    cv_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tag: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    run_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    parameter_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    parameter_label: Mapped[str] = mapped_column(String(255))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_type: Mapped[str] = mapped_column(String(100), default='detected_change')
    category: Mapped[str] = mapped_column(String(100), default='operational')
    severity: Mapped[str] = mapped_column(String(50), default='medium')
    status: Mapped[str] = mapped_column(String(50), default='open')
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    impact_summary: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str] = mapped_column(Text, default='{}')
    approval_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closure_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    measurement_point: Mapped[MeasurementPoint | None] = relationship(back_populates='change_records')


class Event(Base):
    __tablename__ = 'events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey('assets.id'), nullable=True)
    file_id: Mapped[int] = mapped_column(ForeignKey('files_raw.id'))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    run_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(50))
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    old_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    asset: Mapped[Asset | None] = relationship(back_populates='events')
    file: Mapped[RawFile] = relationship(back_populates='events')


class AlarmManagementRecord(Base):
    __tablename__ = 'alarm_management_records'
    __table_args__ = (UniqueConstraint('event_id', name='uq_alarm_management_event_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'), index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    management_status: Mapped[str] = mapped_column(String(50), default='open')
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event: Mapped[Event] = relationship()


class QaFlag(Base):
    __tablename__ = 'qa_flags'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    related_entity_type: Mapped[str] = mapped_column(String(50))
    related_entity_id: Mapped[int] = mapped_column(Integer)
    flag_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportExport(Base):
    __tablename__ = 'report_exports'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(50))
    scope_id: Mapped[int] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReferenceRecord(Base):
    __tablename__ = 'reference_records'
    __table_args__ = (UniqueConstraint('entity_type', 'record_key', name='uq_reference_entity_record_key'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    record_key: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default='{}')
    source_label: Mapped[str] = mapped_column(String(255), default='user-config')
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TechnicalReference(Base):
    __tablename__ = 'technical_references'
    __table_args__ = (UniqueConstraint('topic_key', name='uq_technical_reference_topic_key'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_key: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    guidance: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(String(255))
    source_excerpt: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(50), default='medium')
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IndicatorRule(Base):
    __tablename__ = 'indicator_rules'
    __table_args__ = (UniqueConstraint('rule_key', name='uq_indicator_rule_key'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    applies_to_asset_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(50))
    target_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_count: Mapped[int] = mapped_column(Integer, default=1)
    description_template: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    source_label: Mapped[str] = mapped_column(String(255), default='seed')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IndicatorRecord(Base):
    __tablename__ = 'indicator_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey('assets.id'), nullable=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey('ingestion_batches.id'), nullable=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey('indicator_rules.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default='triggered')
    description: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
