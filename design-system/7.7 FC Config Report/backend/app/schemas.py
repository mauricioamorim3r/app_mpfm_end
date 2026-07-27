from typing import Any

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class FileSummary(BaseModel):
    id: int
    original_name: str
    detected_type: str
    sha256: str
    size_bytes: int
    parse_status: str
    parse_warning: str | None = None


class BatchSummary(BaseModel):
    id: int
    source_name: str
    source_path: str | None = None
    source_kind: str
    file_type_summary: str | None = None
    created_at: datetime
    files: list[FileSummary]


class ParameterSummary(BaseModel):
    id: int
    section: str | None = None
    parameter_key: str
    parameter_label: str
    normalized_value: str | None = None
    raw_value: str | None = None


class SnapshotSummary(BaseModel):
    id: int
    file_id: int | None = None
    batch_id: int | None = None
    batch_source_name: str | None = None
    source_file_name: str | None = None
    snapshot_at: datetime | None = None
    device_name: str | None = None
    device_type: str | None = None
    application_version: str | None = None
    serial_number: str | None = None
    ip_address_1: str | None = None
    ip_address_2: str | None = None
    parser_version: str
    parameters: list[ParameterSummary] = Field(default_factory=list)


class BaselineSummary(BaseModel):
    id: int
    snapshot_id: int
    selected_at: datetime
    status: str


class AssetSummary(BaseModel):
    id: int
    asset_key: str
    flow_computer_tag: str
    system_tag: str | None = None
    location: str | None = None
    company: str | None = None
    description: str | None = None
    last_seen_at: datetime
    is_new_in_local_base: bool = False
    current_events_at: datetime | None = None
    current_events_file_name: str | None = None
    baseline: BaselineSummary | None = None
    snapshots: list[SnapshotSummary] = Field(default_factory=list)


class DiffRecordSummary(BaseModel):
    id: int
    parameter_key: str
    parameter_label: str
    context_label: str | None = None
    tag_label: str | None = None
    group_label: str | None = None
    left_value: str | None = None
    right_value: str | None = None
    change_type: str
    category: str
    severity: str
    impact_summary: str
    reference_value: str | None = None
    reference_status: str | None = None
    reference_label: str | None = None


class DiffRequest(BaseModel):
    left_snapshot_id: int
    right_snapshot_id: int


class DiffResponse(BaseModel):
    left_snapshot_id: int
    right_snapshot_id: int
    left_snapshot: SnapshotSummary | None = None
    right_snapshot: SnapshotSummary | None = None
    records: list[DiffRecordSummary]


class ComparisonCandidateSummary(BaseModel):
    asset_id: int
    asset_key: str
    flow_computer_tag: str
    current_snapshot: SnapshotSummary | None = None
    previous_day_snapshot: SnapshotSummary | None = None
    available_snapshots: list[SnapshotSummary] = Field(default_factory=list)


class MeasurementPointUpsert(BaseModel):
    cv_id: str
    cv_tag_device: str | None = None
    cv_serial_number: str | None = None
    cv_version: str | None = None
    cv_application_name: str | None = None
    cv_application_date: str | None = None
    cv_application_version: str | None = None
    cv_ip_address: str | None = None
    cv_connected_system_name: str | None = None
    system_group: str | None = None
    fluid: str
    measurement_point_name: str
    measurement_technology: str
    tag: str
    connected_system: str | None = None
    classification: str
    asset_key: str | None = None
    run_number: int | None = None
    is_redundant: bool = False
    is_active: bool = True
    source_label: str = 'user-config'
    notes: str | None = None


class MeasurementReferenceParameterUpsert(BaseModel):
    parameter_key: str
    parameter_label: str
    reference_kind: str = 'critical_parameter'
    unit: str | None = None
    expected_value: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    lower_low_limit: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    upper_high_limit: float | None = None
    tolerance: float | None = None
    severity: str = 'high'
    source_label: str = 'user-config'
    notes: str | None = None


class MeasurementReferenceParameterSummary(MeasurementReferenceParameterUpsert):
    id: int
    measurement_point_id: int
    created_at: datetime
    updated_at: datetime


class MeasurementPointSummary(MeasurementPointUpsert):
    id: int
    created_at: datetime
    updated_at: datetime
    reference_parameters: list[MeasurementReferenceParameterSummary] = Field(default_factory=list)


class MeterAnalysisSelectionUpsert(BaseModel):
    flow_computer: str
    meter_id: str
    measurement_point_id: int | None = None
    is_active: bool = True
    is_default: bool = False
    source_label: str = 'user-config'
    notes: str | None = None


class MeterAnalysisSelectionSummary(MeterAnalysisSelectionUpsert):
    id: int
    created_at: datetime
    updated_at: datetime


class FolderIngestionRequest(BaseModel):
    root_path: str = Field(..., min_length=1, max_length=4096)
    selection_ids: list[int] | None = None
    selections: list[MeterAnalysisSelectionUpsert] | None = None
    include_inactive: bool = False

    @model_validator(mode='after')
    def _validate_root_path(self) -> 'FolderIngestionRequest':
        if '\x00' in self.root_path:
            raise ValueError('root_path contém caractere nulo.')
        if not self.root_path.strip():
            raise ValueError('root_path não pode ser vazio.')
        return self


class TraceableComparisonRequest(BaseModel):
    left_snapshot_id: int | None = None
    right_snapshot_id: int
    measurement_point_id: int | None = None
    allow_cross_equipment: bool = False
    create_change_records: bool = True


class ChangeRecordUpdate(BaseModel):
    status: str | None = None
    approval_owner: str | None = None
    closure_notes: str | None = None
    recommendation: str | None = None


class ChangeRecordSummary(BaseModel):
    id: int
    measurement_point_id: int | None = None
    asset_id: int | None = None
    diff_id: int | None = None
    event_id: int | None = None
    source_file_id: int | None = None
    cv_id: str | None = None
    tag: str | None = None
    run_number: int | None = None
    parameter_key: str | None = None
    parameter_label: str
    old_value: str | None = None
    new_value: str | None = None
    unit: str | None = None
    change_type: str
    category: str
    severity: str
    status: str
    actor: str | None = None
    source_ip: str | None = None
    occurred_at: datetime | None = None
    detected_at: datetime
    impact_summary: str
    recommendation: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    approval_owner: str | None = None
    closure_notes: str | None = None
    updated_at: datetime


class TraceableComparisonResponse(BaseModel):
    left_snapshot_id: int
    right_snapshot_id: int
    measurement_point: MeasurementPointSummary | None = None
    is_cross_equipment: bool = False
    records: list[DiffRecordSummary]
    change_records: list[ChangeRecordSummary] = Field(default_factory=list)


class ProcessReferenceSummary(BaseModel):
    reference_record_id: int | None = None
    parameter_key: str
    parameter_label: str
    current_value: str | None = None
    reference_value: str | None = None
    reference_source: str | None = None
    snapshot_id: int
    is_reference_defined: bool
    kind: str
    component_key: str | None = None
    component_label: str | None = None
    sort_order: int | None = None


class ProcessReferenceUpsert(BaseModel):
    snapshot_id: int
    parameter_key: str


class EventSummary(BaseModel):
    id: int
    file_id: int | None = None
    batch_id: int | None = None
    source_file_name: str | None = None
    occurred_at: datetime | None = None
    run_number: int | None = None
    event_type: str
    category: str
    severity: str
    actor: str | None = None
    source_ip: str | None = None
    message: str
    old_value: str | None = None
    new_value: str | None = None


class EventInsightItem(BaseModel):
    title: str
    count: int
    severity: str
    detail: str


class EventIntelligenceSummary(BaseModel):
    asset_id: int | None = None
    batch_id: int | None = None
    total_events: int
    recurring_patterns: list[EventInsightItem] = Field(default_factory=list)
    chattering_patterns: list[EventInsightItem] = Field(default_factory=list)
    operator_windows: list[EventInsightItem] = Field(default_factory=list)


class XmlParameterValidationSummary(BaseModel):
    parameter_id: int
    snapshot_id: int
    file_id: int
    source_file_name: str | None = None
    document_code: str
    asset_id: int | None = None
    asset_key: str | None = None
    cv_id: str | None = None
    run_number: int | None = None
    tag: str | None = None
    application: str | None = None
    system: str | None = None
    section: str | None = None
    parameter_key: str
    parameter_label: str
    current_value: str | None = None
    previous_value: str | None = None
    changed: bool
    reference_value: str | None = None
    validation_status: str
    validation_message: str


class AlarmManagementUpdate(BaseModel):
    priority: str | None = None
    management_status: str | None = None
    assignee: str | None = None
    action_correction: str | None = None
    notes: str | None = None
    acknowledged_by: str | None = None
    closed_by: str | None = None


class XmlAlarmManagementSummary(BaseModel):
    id: int | None = None
    priority: str | None = None
    management_status: str
    assignee: str | None = None
    action_correction: str | None = None
    notes: str | None = None
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    closed_by: str | None = None
    closed_at: datetime | None = None
    updated_at: datetime | None = None


class XmlAlarmSummary(BaseModel):
    event_id: int
    file_id: int | None = None
    batch_id: int | None = None
    source_file_name: str | None = None
    source_document: str
    source_record_type: str
    occurred_at: datetime | None = None
    cv_id: str | None = None
    run_number: int | None = None
    application: str | None = None
    system: str | None = None
    tag: str | None = None
    alarm_text: str
    alarm_status: str
    priority: str
    executor: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    severity: str
    management: XmlAlarmManagementSummary


class XmlMonitorSummary(BaseModel):
    batch_id: int
    batch_name: str
    xml_files: list[FileSummary] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
    alarms: list[XmlAlarmSummary] = Field(default_factory=list)
    parameters: list[XmlParameterValidationSummary] = Field(default_factory=list)


class QaFlagSummary(BaseModel):
    id: int
    related_entity_type: str
    related_entity_id: int
    flag_type: str
    severity: str
    message: str
    created_at: datetime


class ReportExportSummary(BaseModel):
    id: int
    scope_type: str
    scope_id: int
    format: str
    file_path: str
    created_at: datetime


class ReportRequest(BaseModel):
    batch_id: int | None = None
    diff_left_snapshot_id: int | None = None
    diff_right_snapshot_id: int | None = None
    format: str = 'markdown'


class ReportResponse(BaseModel):
    report_id: int
    file_path: str
    content: str
    format: str


class ReferenceRecordSummary(BaseModel):
    id: int
    entity_type: str
    record_key: str
    name: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_label: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ReferenceRecordUpsert(BaseModel):
    entity_type: str
    record_key: str
    name: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_label: str = 'user-config'
    is_default: bool = False


class TechnicalReferenceSummary(BaseModel):
    id: int
    topic_key: str
    category: str
    title: str
    summary: str
    guidance: str
    source_ref: str
    source_excerpt: str
    severity: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class OperationalAnalysisFindingSummary(BaseModel):
    id: str
    category: str
    check_name: str
    status: str
    severity: str
    cv_id: str | None = None
    tag: str | None = None
    measurement_point: str | None = None
    source_file: str | None = None
    source_a: str | None = None
    source_b: str | None = None
    observed_value: str | None = None
    reference_value: str | None = None
    unit: str | None = None
    difference: str | None = None
    actor: str | None = None
    source_ip: str | None = None
    occurred_at: datetime | None = None
    evidence: str
    recommendation: str | None = None


class FlowXMemorialItemSummary(BaseModel):
    title: str
    source_ref: str
    summary: str
    evidence: str


class ProposedAnalysisParameterSummary(BaseModel):
    parameter_key: str
    parameter_label: str
    reason: str
    status: str = 'proposed'


class BatchOperationalAnalysisSummary(BaseModel):
    batch_id: int
    source_name: str
    generated_at: datetime
    findings: list[OperationalAnalysisFindingSummary] = Field(default_factory=list)
    memorial: list[FlowXMemorialItemSummary] = Field(default_factory=list)
    proposed_parameters: list[ProposedAnalysisParameterSummary] = Field(default_factory=list)


class IndicatorRuleSummary(BaseModel):
    id: int
    rule_key: str
    name: str
    applies_to_asset_key: str | None = None
    rule_type: str
    category: str
    severity: str
    target_field: str | None = None
    match_text: str | None = None
    expected_value: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    threshold_count: int
    description_template: str
    recommendation: str | None = None
    enabled: bool
    is_default: bool
    source_label: str
    created_at: datetime
    updated_at: datetime


class IndicatorRuleUpsert(BaseModel):
    rule_key: str
    name: str
    applies_to_asset_key: str | None = None
    rule_type: str
    category: str
    severity: str
    target_field: str | None = None
    match_text: str | None = None
    expected_value: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    threshold_count: int = 1
    description_template: str
    recommendation: str | None = None
    enabled: bool = True
    is_default: bool = False
    source_label: str = 'user-config'


class IndicatorRecordSummary(BaseModel):
    id: int
    asset_id: int | None = None
    batch_id: int | None = None
    rule_id: int | None = None
    title: str
    category: str
    severity: str
    status: str
    description: str
    recommendation: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
