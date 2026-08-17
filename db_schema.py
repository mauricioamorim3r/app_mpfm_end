from __future__ import annotations


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS processing_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    source_type TEXT,
    source_ref TEXT,
    density REAL,
    files_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    notes_json TEXT
);

CREATE TABLE IF NOT EXISTS files_imported (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    filename TEXT NOT NULL,
    ext TEXT,
    file_type TEXT,
    unit_code TEXT,
    meter_id TEXT,
    location TEXT,
    content_date TEXT,
    report_start TEXT,
    report_end TEXT,
    excel_month TEXT,
    identity_key TEXT,
    time_source TEXT,
    file_hash TEXT,
    processed_ok INTEGER DEFAULT 1,
    message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES processing_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_files_imported_lookup
    ON files_imported(content_date, ext, file_type, meter_id);

CREATE TABLE IF NOT EXISTS source_files_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    filename TEXT NOT NULL,
    original_path TEXT,
    source_type TEXT,
    ext TEXT,
    detected_type TEXT,
    unit_code TEXT,
    meter_id TEXT,
    location TEXT,
    content_date TEXT,
    report_start TEXT,
    report_end TEXT,
    identity_key TEXT,
    time_source TEXT,
    file_hash TEXT,
    file_size_bytes INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES processing_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_source_files_raw_lookup
    ON source_files_raw(run_id, filename, content_date);

CREATE TABLE IF NOT EXISTS parsing_events_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source_file_raw_id INTEGER,
    parser_name TEXT NOT NULL,
    parser_stage TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES processing_runs(id),
    FOREIGN KEY(source_file_raw_id) REFERENCES source_files_raw(id)
);
CREATE INDEX IF NOT EXISTS idx_parsing_events_raw_lookup
    ON parsing_events_raw(run_id, source_file_raw_id, parser_stage);

CREATE TABLE IF NOT EXISTS measurements_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source_file_raw_id INTEGER,
    source_record_id INTEGER,
    row_kind TEXT,
    content_date TEXT,
    hour_ref INTEGER,
    bank TEXT,
    tag TEXT,
    instrument TEXT,
    metric_name TEXT NOT NULL,
    metric_value_raw TEXT,
    metric_unit_raw TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES processing_runs(id),
    FOREIGN KEY(source_file_raw_id) REFERENCES source_files_raw(id)
);
CREATE INDEX IF NOT EXISTS idx_measurements_raw_lookup
    ON measurements_raw(content_date, row_kind, bank, tag, metric_name);

CREATE TABLE IF NOT EXISTS measurements_curated (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source_file TEXT,
    source_record_id INTEGER,
    excel_file TEXT,
    sheet_name TEXT,
    row_kind TEXT,
    day_ref TEXT,
    hour_ref INTEGER,
    bank TEXT,
    loop TEXT,
    tipo TEXT,
    tag TEXT,
    instrument TEXT,
    metric_name TEXT,
    metric_value REAL,
    metric_unit TEXT,
    is_official INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES processing_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_measurements_curated_lookup
    ON measurements_curated(day_ref, row_kind, bank, tag, metric_name);
CREATE INDEX IF NOT EXISTS idx_measurements_curated_source
    ON measurements_curated(source_record_id, is_official);

CREATE TABLE IF NOT EXISTS mpfm_adjustment_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_hash TEXT DEFAULT '',
    author TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    rows_seen INTEGER DEFAULT 0,
    rows_marked INTEGER DEFAULT 0,
    metrics_changed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'applied',
    summary_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS mpfm_adjustment_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL,
    day_ref TEXT NOT NULL,
    hour_ref INTEGER,
    row_kind TEXT NOT NULL,
    bank TEXT DEFAULT '',
    loop TEXT DEFAULT '',
    tipo TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    metric_name TEXT NOT NULL,
    old_value REAL,
    new_value REAL,
    reason TEXT DEFAULT '',
    responsible TEXT DEFAULT '',
    observation TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_id) REFERENCES mpfm_adjustment_imports(id)
);
CREATE INDEX IF NOT EXISTS idx_mpfm_adjustment_items_lookup
    ON mpfm_adjustment_items(day_ref, row_kind, bank, tag, metric_name);

CREATE TABLE IF NOT EXISTS measurement_dimensions (
    dimension_kind TEXT NOT NULL,
    dimension_value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(dimension_kind, dimension_value)
);
CREATE INDEX IF NOT EXISTS idx_measurement_dimensions_lookup
    ON measurement_dimensions(dimension_kind, dimension_value);

CREATE TABLE IF NOT EXISTS validation_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    excel_file TEXT,
    issue_type TEXT,
    severity TEXT,
    ref_key TEXT,
    day_ref TEXT,
    details TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES processing_runs(id)
);

CREATE TABLE IF NOT EXISTS alarm_reference_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    code TEXT NOT NULL,
    label TEXT NOT NULL,
    description TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    is_terminal INTEGER DEFAULT 0,
    is_default INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(domain, code)
);
CREATE INDEX IF NOT EXISTS idx_alarm_reference_values_lookup
    ON alarm_reference_values(domain, active, sort_order);

CREATE TABLE IF NOT EXISTS alarm_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_kind TEXT DEFAULT 'manual',
    source_ref TEXT DEFAULT '',
    record_type TEXT DEFAULT 'event',
    source_sheet TEXT DEFAULT '',
    external_code TEXT DEFAULT '',
    title TEXT NOT NULL,
    message TEXT DEFAULT '',
    category_code TEXT DEFAULT '',
    family_code TEXT DEFAULT '',
    severity_code TEXT DEFAULT '',
    priority_code TEXT DEFAULT '',
    status_code TEXT DEFAULT 'open',
    bank TEXT DEFAULT '',
    measurement_point TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    instrument TEXT DEFAULT '',
    loop TEXT DEFAULT '',
    meter_type TEXT DEFAULT '',
    measurement_state TEXT DEFAULT '',
    event_at TEXT DEFAULT '',
    detected_at TEXT DEFAULT '',
    production_date TEXT DEFAULT '',
    occurrence_count INTEGER DEFAULT 0,
    distinct_alarm_count INTEGER DEFAULT 0,
    owner TEXT DEFAULT '',
    due_date TEXT DEFAULT '',
    acknowledged_by TEXT DEFAULT '',
    acknowledged_at TEXT DEFAULT '',
    closed_at TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    impact TEXT DEFAULT '',
    cause TEXT DEFAULT '',
    immediate_action TEXT DEFAULT '',
    corrective_action TEXT DEFAULT '',
    reference TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alarm_records_lookup
    ON alarm_records(active, status_code, severity_code, production_date, bank, tag);
CREATE INDEX IF NOT EXISTS idx_alarm_records_event
    ON alarm_records(event_at, category_code, priority_code);
CREATE INDEX IF NOT EXISTS idx_alarm_records_record_type
    ON alarm_records(record_type, source_sheet, measurement_point, family_code);
CREATE INDEX IF NOT EXISTS idx_alarm_records_external
    ON alarm_records(source_kind, source_ref, source_sheet, record_type, external_code);

CREATE TABLE IF NOT EXISTS alarm_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_id INTEGER NOT NULL,
    action_type TEXT DEFAULT 'corrective',
    description TEXT NOT NULL,
    owner TEXT DEFAULT '',
    priority_code TEXT DEFAULT '',
    status_code TEXT DEFAULT 'open',
    due_date TEXT DEFAULT '',
    completion_date TEXT DEFAULT '',
    effectiveness TEXT DEFAULT '',
    verification TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(alarm_id) REFERENCES alarm_records(id)
);
CREATE INDEX IF NOT EXISTS idx_alarm_actions_lookup
    ON alarm_actions(alarm_id, active, status_code, due_date);

CREATE TABLE IF NOT EXISTS alarm_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_id INTEGER,
    action_id INTEGER,
    event_type TEXT NOT NULL,
    field_name TEXT DEFAULT '',
    old_value TEXT DEFAULT '',
    new_value TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(alarm_id) REFERENCES alarm_records(id),
    FOREIGN KEY(action_id) REFERENCES alarm_actions(id)
);
CREATE INDEX IF NOT EXISTS idx_alarm_audit_log_lookup
    ON alarm_audit_log(alarm_id, action_id, created_at);

CREATE TABLE IF NOT EXISTS pvt_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank TEXT NOT NULL,
    tag TEXT NOT NULL,
    fe REAL NOT NULL,
    rs REAL NOT NULL,
    rho_oleo_std REAL NOT NULL,
    rho_gas_std REAL NOT NULL,
    rho_agua_std REAL NOT NULL,
    temp_ref_c REAL DEFAULT 20.0,
    pres_ref_bar REAL DEFAULT 1.01325,
    gsv_confirmed INTEGER DEFAULT 0,
    gor_mode TEXT DEFAULT 'unknown',
    limite_hc_pct REAL DEFAULT 5.0,
    limite_total_pct REAL DEFAULT 5.0,
    limite_agua_pct REAL DEFAULT 20.0,
    valid_from TEXT,
    valid_to TEXT,
    source TEXT,
    author TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_key TEXT NOT NULL,
    decision_summary TEXT NOT NULL,
    rationale TEXT DEFAULT '',
    impact_notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO alarm_reference_values(domain, code, label, description, sort_order, is_terminal, is_default, active, created_at, updated_at)
VALUES
('severity', 'info', 'Info', 'Evento informativo', 10, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('severity', 'warning', 'Atenção', 'Requer acompanhamento operacional', 20, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('severity', 'critical', 'Crítica', 'Requer ação prioritária', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('priority', 'low', 'Baixa', 'Baixa prioridade de tratamento', 10, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('priority', 'medium', 'Média', 'Prioridade média de tratamento', 20, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('priority', 'high', 'Alta', 'Alta prioridade de tratamento', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('priority', 'urgent', 'Urgente', 'Tratamento imediato', 40, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('status', 'open', 'Aberta', 'Ocorrência aberta', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('status', 'in_progress', 'Em andamento', 'Tratamento em curso', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('status', 'monitoring', 'Monitoramento', 'Acompanhamento ativo', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('status', 'closed', 'Concluída', 'Ocorrência concluída', 40, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('status', 'cancelled', 'Cancelada', 'Ocorrência cancelada', 50, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('action_status', 'open', 'Aberta', 'Ação aberta', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('action_status', 'in_progress', 'Em andamento', 'Ação em andamento', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('action_status', 'closed', 'Concluída', 'Ação concluída', 30, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('action_status', 'cancelled', 'Cancelada', 'Ação cancelada', 40, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('action_type', 'immediate', 'Ação imediata', 'Resposta imediata ao alarme', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('action_type', 'corrective', 'Ação corretiva', 'Ação corretiva planejada', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('action_type', 'preventive', 'Ação preventiva', 'Ação preventiva vinculada ao alarme', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('source_kind', 'manual', 'Manual', 'Registro manual operacional', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('source_kind', 'import', 'Importado', 'Origem externa importada', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('source_kind', 'system', 'Sistema', 'Gerado automaticamente pelo sistema', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'communication', 'Comunicação', 'Falhas de comunicação, congelamento ou indisponibilidade', 10, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'warning', 'Alarmes / warnings', 'Alarmes e advertências do medidor', 20, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'mode_change', 'Eventos / mudança indevida', 'Mudanças indevidas de modo ou fallback', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'redundancy', 'Transmissor / A/B', 'Redundância ou troca A/B', 40, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'pvt', 'PVT / condição padrão', 'Condição padrão e coerência PVT', 50, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'deviation', 'Desvio topside vs subsea', 'Desvio entre sistemas de medição', 60, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'critical_variable', 'Variável crítica', 'Anomalia em variáveis críticas de processo', 70, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('category', 'other', 'Outro', 'Ocorrência classificada manualmente', 80, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS sep_source_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_date TEXT NOT NULL,
    fluid_kind TEXT NOT NULL,
    meter_id TEXT NOT NULL,
    location TEXT DEFAULT '',
    report_kind TEXT DEFAULT '',
    report_start TEXT DEFAULT '',
    report_end TEXT DEFAULT '',
    identity_key TEXT DEFAULT '',
    time_source TEXT DEFAULT 'content',
    source_file TEXT NOT NULL,
    source_hash TEXT NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1,
    is_official INTEGER DEFAULT 0,
    resolution_status TEXT DEFAULT 'official',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sep_source_key
    ON sep_source_files(production_date, fluid_kind, meter_id, is_active);

CREATE TABLE IF NOT EXISTS sep_alignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_date TEXT NOT NULL,
    bank TEXT NOT NULL,
    mpfm_tag TEXT DEFAULT '',
    sep_meter_id TEXT DEFAULT '',
    sep_tag TEXT DEFAULT 'SEP',
    notes TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    is_official INTEGER DEFAULT 1,
    resolution_status TEXT DEFAULT 'official',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sep_alignments_key
    ON sep_alignments(production_date, bank, is_active);

CREATE TABLE IF NOT EXISTS recon_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at TEXT NOT NULL,
    bank TEXT NOT NULL,
    tag TEXT NOT NULL,
    day_ref TEXT NOT NULL,
    campaign_id INTEGER,
    campaign_phase TEXT DEFAULT 'baseline',
    pvt_params_id INTEGER,
    pvt_snapshot TEXT,
    analytical_snapshot TEXT,
    sep_hourly_json TEXT,
    mpfm_hourly_json TEXT,
    calc_hourly_json TEXT,
    resumo_json TEXT,
    horas_validas INTEGER DEFAULT 0,
    cobertura_pct REAL DEFAULT 0,
    status_linha TEXT,
    status_standard TEXT,
    status_final TEXT,
    author TEXT,
    notes TEXT,
    test_window_json TEXT,
    FOREIGN KEY(pvt_params_id) REFERENCES pvt_params(id)
);

CREATE TABLE IF NOT EXISTS recon_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    bank TEXT NOT NULL,
    tag TEXT NOT NULL,
    baseline_day_ref TEXT NOT NULL,
    baseline_run_id INTEGER,
    post_day_ref TEXT DEFAULT '',
    post_run_id INTEGER,
    pvt_params_id INTEGER,
    pvt_snapshot TEXT DEFAULT '{}',
    analytical_snapshot TEXT DEFAULT '{}',
    sep_alignment_snapshot TEXT DEFAULT '{}',
    current_k_factor REAL,
    proposal_mode TEXT DEFAULT 'hc',
    proposal_rule TEXT DEFAULT 'mass_ratio_24h',
    proposal_status TEXT DEFAULT 'pending',
    proposed_k_factor_hc REAL,
    proposed_k_factor_total REAL,
    proposed_k_factor_selected REAL,
    proposed_k_factor_manual REAL,
    applied_k_factor REAL,
    applied_at TEXT DEFAULT '',
    baseline_desvio_hc_pct REAL,
    baseline_desvio_total_pct REAL,
    post_desvio_hc_pct REAL,
    post_desvio_total_pct REAL,
    improvement_hc_pp REAL,
    improvement_total_pp REAL,
    monitoring_status TEXT DEFAULT '',
    author TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'baseline',
    FOREIGN KEY(pvt_params_id) REFERENCES pvt_params(id),
    FOREIGN KEY(baseline_run_id) REFERENCES recon_runs(id),
    FOREIGN KEY(post_run_id) REFERENCES recon_runs(id)
);

CREATE TABLE IF NOT EXISTS methodology_flow_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    item_type TEXT NOT NULL DEFAULT 'nota',
    scope TEXT DEFAULT 'run',
    item_key TEXT DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'aberto',
    owner TEXT DEFAULT '',
    due_date TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES recon_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_methodology_flow_items_lookup
    ON methodology_flow_items(active, run_id, item_type, status, item_key);

CREATE TABLE IF NOT EXISTS daily_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_date TEXT NOT NULL,
    bank TEXT NOT NULL,
    card_type TEXT NOT NULL,
    tag TEXT DEFAULT '',
    instrument TEXT DEFAULT '',
    title TEXT DEFAULT '',
    flow_velocity_ms REAL,
    dp_value REAL,
    sep_test_aligned TEXT DEFAULT '',
    observations TEXT DEFAULT '',
    manual_payload TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    is_official INTEGER DEFAULT 1,
    resolution_status TEXT DEFAULT 'official'
);
CREATE INDEX IF NOT EXISTS idx_daily_cards_key
    ON daily_cards(production_date, bank, card_type, tag, instrument, is_active);

CREATE TABLE IF NOT EXISTS daily_card_edits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_card_id INTEGER,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT DEFAULT '',
    edited_at TEXT NOT NULL,
    FOREIGN KEY(daily_card_id) REFERENCES daily_cards(id)
);

CREATE TABLE IF NOT EXISTS deadline_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    category TEXT DEFAULT '',
    start_date TEXT DEFAULT '',
    due_date TEXT DEFAULT '',
    periodicity TEXT DEFAULT 'custom',
    periodicity_days INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    icon TEXT DEFAULT '⏳',
    source_ref TEXT DEFAULT '',
    source_file TEXT DEFAULT '',
    norm_ref TEXT DEFAULT '',
    evidence_required TEXT DEFAULT '',
    responsible_area TEXT DEFAULT '',
    trigger_event TEXT DEFAULT '',
    risk_level TEXT DEFAULT '',
    recommended_action TEXT DEFAULT '',
    completion_date TEXT DEFAULT '',
    source_status TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT '',
    source_page TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_lookup
    ON ai_conversations(active, updated_at);

CREATE TABLE IF NOT EXISTS ai_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    provider TEXT DEFAULT '',
    model TEXT DEFAULT '',
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id)
);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation
    ON ai_messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS ai_action_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    message_id INTEGER,
    action_type TEXT DEFAULT 'record_note',
    target_area TEXT DEFAULT 'nota',
    title TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    source_content TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'pending',
    requested_by TEXT DEFAULT 'user',
    approved_by TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    approved_at TEXT DEFAULT '',
    applied_at TEXT DEFAULT '',
    result_json TEXT DEFAULT '{}',
    FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id),
    FOREIGN KEY(message_id) REFERENCES ai_messages(id)
);
CREATE INDEX IF NOT EXISTS idx_ai_action_requests_status
    ON ai_action_requests(status, target_area, created_at);

CREATE TABLE IF NOT EXISTS mpfm_monitoring_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_date TEXT NOT NULL,
    bank TEXT NOT NULL,
    tag TEXT NOT NULL,
    meter_type TEXT NOT NULL,
    instrument TEXT DEFAULT '',
    loop TEXT DEFAULT '',
    event_occurred TEXT DEFAULT '',
    event_type TEXT DEFAULT '',
    event_status TEXT DEFAULT '',
    sensor_redundancy_ptdp TEXT DEFAULT '',
    integrity_communication TEXT DEFAULT '',
    new_pvt_result TEXT DEFAULT '',
    new_k_factor_implemented TEXT DEFAULT '',
    operation_mode TEXT DEFAULT '',
    aligned_separator_test TEXT DEFAULT '',
    observations TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mpfm_monitoring_daily_unique
    ON mpfm_monitoring_daily(production_date, bank, tag, meter_type);
CREATE INDEX IF NOT EXISTS idx_mpfm_monitoring_daily_lookup
    ON mpfm_monitoring_daily(production_date, bank, meter_type);

CREATE TABLE IF NOT EXISTS well_catalog_042 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_operator_name TEXT NOT NULL,
    well_anp_name TEXT NOT NULL,
    cod_cadastro_poco TEXT NOT NULL,
    subsea_tag TEXT NOT NULL,
    cod_campo TEXT DEFAULT '',
    campo TEXT DEFAULT '',
    cod_instalacao TEXT DEFAULT '',
    instalacao TEXT DEFAULT '',
    enabled_042 INTEGER DEFAULT 1,
    active INTEGER DEFAULT 1,
    valid_from TEXT DEFAULT '',
    valid_to TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_well_catalog_042_lookup
    ON well_catalog_042(well_operator_name, subsea_tag, active, enabled_042);
CREATE INDEX IF NOT EXISTS idx_well_catalog_042_cod
    ON well_catalog_042(cod_cadastro_poco);

CREATE TABLE IF NOT EXISTS tpoc_daily_potential_curated (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_day TEXT NOT NULL,
    bank TEXT NOT NULL,
    well_operator_name TEXT NOT NULL,
    subsea_tag TEXT NOT NULL,
    source_daily_row_ref TEXT DEFAULT '',
    oil_sm3_d_curated REAL,
    gas_sm3_d_raw REAL,
    gas_1000sm3_d_curated REAL,
    water_sm3_d_curated REAL,
    catalog_match_status TEXT DEFAULT '',
    catalog_match_id INTEGER,
    qa_flags TEXT DEFAULT '',
    approved_by_user TEXT DEFAULT '',
    approved_at TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(production_day, bank, well_operator_name, subsea_tag)
);
CREATE INDEX IF NOT EXISTS idx_tpoc_daily_potential_lookup
    ON tpoc_daily_potential_curated(production_day, bank, well_operator_name, subsea_tag);

CREATE TABLE IF NOT EXISTS xml042_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_day TEXT NOT NULL,
    cod_cadastro_poco TEXT NOT NULL,
    well_operator_name TEXT NOT NULL,
    subsea_tag TEXT NOT NULL,
    bank TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    status TEXT DEFAULT 'generated',
    generated_at TEXT NOT NULL,
    generated_by TEXT DEFAULT '',
    payload_json TEXT DEFAULT '',
    UNIQUE(production_day, cod_cadastro_poco)
);
CREATE INDEX IF NOT EXISTS idx_xml042_documents_lookup
    ON xml042_documents(production_day, bank, cod_cadastro_poco);

CREATE TABLE IF NOT EXISTS xml042_imported_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_ref TEXT NOT NULL,
    production_day TEXT NOT NULL,
    cod_cadastro_poco TEXT NOT NULL,
    well_operator_name TEXT DEFAULT '',
    subsea_tag TEXT DEFAULT '',
    bank TEXT DEFAULT '',
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    file_size_bytes INTEGER DEFAULT 0,
    import_status TEXT DEFAULT 'imported',
    import_message TEXT DEFAULT '',
    imported_at TEXT NOT NULL,
    payload_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_xml042_imported_files_lookup
    ON xml042_imported_files(month_ref, cod_cadastro_poco, production_day);

CREATE TABLE IF NOT EXISTS xml042_imported_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_ref TEXT NOT NULL,
    production_day TEXT NOT NULL,
    cod_cadastro_poco TEXT NOT NULL,
    well_operator_name TEXT DEFAULT '',
    subsea_tag TEXT DEFAULT '',
    bank TEXT DEFAULT '',
    ind_tipo_teste TEXT DEFAULT '',
    dha_teste TEXT DEFAULT '',
    dha_aplicacao TEXT DEFAULT '',
    ind_valido TEXT DEFAULT '',
    oil_sm3 REAL,
    gas_1000sm3 REAL,
    water_sm3 REAL,
    latest_file_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(production_day, cod_cadastro_poco),
    FOREIGN KEY(latest_file_id) REFERENCES xml042_imported_files(id)
);
CREATE INDEX IF NOT EXISTS idx_xml042_imported_rows_lookup
    ON xml042_imported_rows(month_ref, cod_cadastro_poco, production_day);

CREATE TABLE IF NOT EXISTS painel_operador_sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    source_data_path TEXT NOT NULL,
    source_data_hash TEXT NOT NULL,
    status TEXT DEFAULT 'ok',
    counts_json TEXT DEFAULT '{}',
    notes TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_sync_runs_lookup
    ON painel_operador_sync_runs(finished_at, source_data_hash);

CREATE TABLE IF NOT EXISTS painel_operador_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    source_kind TEXT DEFAULT '',
    source_date TEXT DEFAULT '',
    family TEXT DEFAULT '',
    family_name TEXT DEFAULT '',
    source_path TEXT DEFAULT '',
    local_path TEXT DEFAULT '',
    source_name TEXT DEFAULT '',
    records_count INTEGER DEFAULT 0,
    file_exists INTEGER DEFAULT 0,
    file_size_bytes INTEGER DEFAULT 0,
    file_hash TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_sources_lookup
    ON painel_operador_sources(source_date, family, source_kind, source_name);

CREATE TABLE IF NOT EXISTS painel_operador_measurement_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    point_date TEXT DEFAULT '',
    family TEXT DEFAULT '',
    family_name TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    fluid TEXT DEFAULT '',
    principal TEXT DEFAULT '',
    secondary TEXT DEFAULT '',
    meter_type TEXT DEFAULT '',
    active_status TEXT DEFAULT '',
    computador_vazao TEXT DEFAULT '',
    volume_corrigido REAL,
    volume_bruto REAL,
    volume_liquido REAL,
    temperatura REAL,
    pressao REAL,
    in_range INTEGER DEFAULT 0,
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_points_lookup
    ON painel_operador_measurement_points(point_date, family, tag, fluid);

CREATE TABLE IF NOT EXISTS painel_operador_comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    comparison_date TEXT DEFAULT '',
    family TEXT DEFAULT '',
    family_name TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    fluid TEXT DEFAULT '',
    status TEXT DEFAULT '',
    raw_ok INTEGER DEFAULT 0,
    anp_ok INTEGER DEFAULT 0,
    raw_corrigido REAL,
    xml_corrigido REAL,
    anp_corrigido REAL,
    raw_source TEXT DEFAULT '',
    raw_source_local TEXT DEFAULT '',
    xml_source TEXT DEFAULT '',
    xml_source_local TEXT DEFAULT '',
    note TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_comparisons_lookup
    ON painel_operador_comparisons(comparison_date, family, tag, status);

CREATE TABLE IF NOT EXISTS painel_operador_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    evidence_kind TEXT DEFAULT '',
    event_at TEXT DEFAULT '',
    requirement_id TEXT DEFAULT '',
    title TEXT DEFAULT '',
    status TEXT DEFAULT '',
    evidence_state TEXT DEFAULT '',
    source_path TEXT DEFAULT '',
    local_path TEXT DEFAULT '',
    target_id TEXT DEFAULT '',
    target_type TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_evidence_lookup
    ON painel_operador_evidence(evidence_kind, event_at, requirement_id, status);

CREATE TABLE IF NOT EXISTS painel_operador_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    alert_kind TEXT DEFAULT '',
    severity TEXT DEFAULT '',
    alert_date TEXT DEFAULT '',
    title TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    area TEXT DEFAULT '',
    target_id TEXT DEFAULT '',
    status TEXT DEFAULT '',
    source_path TEXT DEFAULT '',
    local_path TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_alerts_lookup
    ON painel_operador_alerts(alert_kind, severity, alert_date, area, status);

CREATE TABLE IF NOT EXISTS painel_operador_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    proposal_id TEXT DEFAULT '',
    proposal_kind TEXT DEFAULT '',
    domain TEXT DEFAULT '',
    title TEXT DEFAULT '',
    target_type TEXT DEFAULT '',
    target_id TEXT DEFAULT '',
    field_name TEXT DEFAULT '',
    current_value_json TEXT DEFAULT 'null',
    proposed_value_json TEXT DEFAULT 'null',
    unit TEXT DEFAULT '',
    confidence TEXT DEFAULT '',
    risk TEXT DEFAULT '',
    status TEXT DEFAULT '',
    requires_approval INTEGER DEFAULT 0,
    source_type TEXT DEFAULT '',
    source_path TEXT DEFAULT '',
    local_path TEXT DEFAULT '',
    source_name TEXT DEFAULT '',
    evidence_state TEXT DEFAULT '',
    evidence_text TEXT DEFAULT '',
    recommended_action TEXT DEFAULT '',
    created_at_source TEXT DEFAULT '',
    authorized_by TEXT DEFAULT '',
    authorized_at TEXT DEFAULT '',
    decision_note TEXT DEFAULT '',
    audit_trail_json TEXT DEFAULT '[]',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_proposals_lookup
    ON painel_operador_proposals(status, risk, domain, target_id);
CREATE INDEX IF NOT EXISTS idx_painel_operador_proposals_source
    ON painel_operador_proposals(source_type, evidence_state, created_at_source);

CREATE TABLE IF NOT EXISTS painel_operador_calendar_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    calendar_date TEXT DEFAULT '',
    day_number INTEGER DEFAULT 0,
    loaded INTEGER DEFAULT 0,
    status TEXT DEFAULT '',
    closing_status TEXT DEFAULT '',
    points_count INTEGER DEFAULT 0,
    xml_families_json TEXT DEFAULT '[]',
    package_families_json TEXT DEFAULT '[]',
    missing_xml_families_json TEXT DEFAULT '[]',
    raw_pending INTEGER DEFAULT 0,
    anp_pending INTEGER DEFAULT 0,
    alert_count INTEGER DEFAULT 0,
    pending_count INTEGER DEFAULT 0,
    open_pending_count INTEGER DEFAULT 0,
    resolved_pending_count INTEGER DEFAULT 0,
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_calendar_days_lookup
    ON painel_operador_calendar_days(calendar_date, status, loaded);

CREATE TABLE IF NOT EXISTS painel_operador_calendar_pendencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    pendency_id TEXT DEFAULT '',
    calendar_date TEXT DEFAULT '',
    pendency_type TEXT DEFAULT '',
    severity TEXT DEFAULT '',
    status TEXT DEFAULT '',
    title TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    recommended_action TEXT DEFAULT '',
    resolution_mode TEXT DEFAULT '',
    closed_by TEXT DEFAULT '',
    closed_at TEXT DEFAULT '',
    decision_note TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(sync_run_id) REFERENCES painel_operador_sync_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_calendar_pendencies_lookup
    ON painel_operador_calendar_pendencies(calendar_date, status, severity, pendency_type);

CREATE TABLE IF NOT EXISTS painel_operador_decision_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_db_id INTEGER,
    previous_status TEXT DEFAULT '',
    decision_status TEXT NOT NULL,
    decision_mode TEXT DEFAULT '',
    decided_by TEXT DEFAULT '',
    decided_at TEXT NOT NULL,
    decision_note TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_decision_audit_lookup
    ON painel_operador_decision_audit(target_type, target_id, decided_at);

CREATE TABLE IF NOT EXISTS painel_operador_file_index_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    module_root TEXT NOT NULL,
    status TEXT DEFAULT 'ok',
    total_files INTEGER DEFAULT 0,
    indexed_files INTEGER DEFAULT 0,
    ignored_files INTEGER DEFAULT 0,
    duplicate_files INTEGER DEFAULT 0,
    total_size_bytes INTEGER DEFAULT 0,
    counts_json TEXT DEFAULT '{}',
    notes TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_file_index_runs_lookup
    ON painel_operador_file_index_runs(finished_at, status);

CREATE TABLE IF NOT EXISTS painel_operador_file_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    index_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL,
    full_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT DEFAULT '',
    file_size_bytes INTEGER DEFAULT 0,
    modified_at TEXT DEFAULT '',
    file_hash TEXT DEFAULT '',
    duplicate_key TEXT DEFAULT '',
    is_duplicate INTEGER DEFAULT 0,
    category TEXT DEFAULT '',
    document_kind TEXT DEFAULT '',
    source_group TEXT DEFAULT '',
    inferred_date TEXT DEFAULT '',
    inferred_tag TEXT DEFAULT '',
    inferred_family TEXT DEFAULT '',
    parse_priority TEXT DEFAULT 'normal',
    ignored INTEGER DEFAULT 0,
    ignore_reason TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(index_run_id) REFERENCES painel_operador_file_index_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_file_index_lookup
    ON painel_operador_file_index(category, document_kind, inferred_date, inferred_tag, extension);
CREATE INDEX IF NOT EXISTS idx_painel_operador_file_index_duplicate
    ON painel_operador_file_index(duplicate_key, is_duplicate);
CREATE INDEX IF NOT EXISTS idx_painel_operador_file_index_path
    ON painel_operador_file_index(relative_path);

CREATE TABLE IF NOT EXISTS painel_operador_anp_export_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    module_root TEXT NOT NULL,
    status TEXT DEFAULT 'ok',
    total_files INTEGER DEFAULT 0,
    total_rows INTEGER DEFAULT 0,
    counts_json TEXT DEFAULT '{}',
    notes TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_anp_export_runs_lookup
    ON painel_operador_anp_export_runs(finished_at, status);

CREATE TABLE IF NOT EXISTS painel_operador_anp_export_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    stable_key TEXT NOT NULL UNIQUE,
    source_file TEXT NOT NULL,
    source_path TEXT NOT NULL,
    sheet_name TEXT DEFAULT '',
    row_number INTEGER DEFAULT 0,
    family TEXT DEFAULT '',
    export_name TEXT DEFAULT '',
    record_kind TEXT DEFAULT '',
    installation TEXT DEFAULT '',
    installation_code TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    element_tag TEXT DEFAULT '',
    serial_number TEXT DEFAULT '',
    reference_date TEXT DEFAULT '',
    period_start TEXT DEFAULT '',
    period_end TEXT DEFAULT '',
    event_at TEXT DEFAULT '',
    detected_at TEXT DEFAULT '',
    returned_at TEXT DEFAULT '',
    collection_at TEXT DEFAULT '',
    file_loaded_at TEXT DEFAULT '',
    volume_corrigido REAL,
    volume_bruto REAL,
    volume_liquido REAL,
    bsw_percent REAL,
    bsw_max_percent REAL,
    pressure_kpa REAL,
    temperature_c REAL,
    failure_code TEXT DEFAULT '',
    notification_type TEXT DEFAULT '',
    failure_type TEXT DEFAULT '',
    received_file TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_anp_export_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_anp_export_rows_lookup
    ON painel_operador_anp_export_rows(family, record_kind, reference_date, tag);
CREATE INDEX IF NOT EXISTS idx_painel_operador_anp_export_rows_source
    ON painel_operador_anp_export_rows(source_file, row_number);
CREATE INDEX IF NOT EXISTS idx_painel_operador_anp_export_rows_failure
    ON painel_operador_anp_export_rows(failure_type, notification_type);

CREATE TABLE IF NOT EXISTS painel_operador_measurement_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    active INTEGER DEFAULT 1,
    family TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    metric_name TEXT DEFAULT '',
    value_unit TEXT DEFAULT '',
    calibrated_min REAL,
    calibrated_max REAL,
    pam_min REAL,
    pam_max REAL,
    alarm_low REAL,
    alarm_high REAL,
    valid_from TEXT DEFAULT '',
    valid_to TEXT DEFAULT '',
    source_type TEXT DEFAULT '',
    source_path TEXT DEFAULT '',
    evidence_ref TEXT DEFAULT '',
    approval_status TEXT DEFAULT 'draft',
    notes TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_limits_lookup
    ON painel_operador_measurement_limits(active, family, tag, metric_name, valid_from, valid_to);

CREATE TABLE IF NOT EXISTS painel_operador_cv_config_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_date TEXT DEFAULT '',
    flow_computer TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    source_file TEXT DEFAULT '',
    file_hash TEXT DEFAULT '',
    parameter_path TEXT DEFAULT '',
    parameter_name TEXT DEFAULT '',
    parameter_value TEXT DEFAULT '',
    value_unit TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_cv_snapshots_lookup
    ON painel_operador_cv_config_snapshots(production_date, flow_computer, tag, parameter_name);
CREATE INDEX IF NOT EXISTS idx_painel_operador_cv_snapshots_source
    ON painel_operador_cv_config_snapshots(source_file);

CREATE TABLE IF NOT EXISTS painel_operador_cv_config_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    previous_date TEXT DEFAULT '',
    current_date TEXT DEFAULT '',
    flow_computer TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    parameter_name TEXT DEFAULT '',
    previous_value TEXT DEFAULT '',
    current_value TEXT DEFAULT '',
    delta_value REAL,
    change_type TEXT DEFAULT '',
    severity TEXT DEFAULT '',
    source_file TEXT DEFAULT '',
    evidence_ref TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_cv_changes_lookup
    ON painel_operador_cv_config_changes("current_date", severity, flow_computer, tag, parameter_name);

CREATE TABLE IF NOT EXISTS painel_operador_daily_checklist_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    status TEXT DEFAULT 'ok',
    sheet_count INTEGER DEFAULT 0,
    selected_sheet_count INTEGER DEFAULT 0,
    row_count INTEGER DEFAULT 0,
    payload_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_checklist_runs_lookup
    ON painel_operador_daily_checklist_runs(imported_at, file_hash);

CREATE TABLE IF NOT EXISTS painel_operador_daily_checklist_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    row_number INTEGER DEFAULT 0,
    record_date TEXT DEFAULT '',
    record_domain TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    title TEXT DEFAULT '',
    status TEXT DEFAULT '',
    responsible TEXT DEFAULT '',
    metric_name TEXT DEFAULT '',
    metric_value REAL,
    metric_unit TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_daily_checklist_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_checklist_rows_lookup
    ON painel_operador_daily_checklist_rows(sheet_name, record_date, tag, status);
CREATE INDEX IF NOT EXISTS idx_painel_operador_checklist_rows_run
    ON painel_operador_daily_checklist_rows(import_run_id, sheet_name, row_number);

CREATE TABLE IF NOT EXISTS painel_operador_tank_balance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_name TEXT DEFAULT 'Tank ',
    row_number INTEGER DEFAULT 0,
    tank_date TEXT DEFAULT '',
    opening_gsv_m3 REAL,
    closing_gsv_m3 REAL,
    delta_tank_m3 REAL,
    fiscal_meter_gsv_m3 REAL,
    fiscal_minus_tank_m3 REAL,
    delta_percent REAL,
    chart_percent REAL,
    measurement_failure TEXT DEFAULT '',
    flowline_volume_m3 REAL,
    reprocessed_oil_gsv_m3 REAL,
    observations TEXT DEFAULT '',
    status TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_daily_checklist_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_tank_balance_lookup
    ON painel_operador_tank_balance(import_run_id, tank_date, status);
CREATE INDEX IF NOT EXISTS idx_painel_operador_tank_balance_file
    ON painel_operador_tank_balance(file_hash, row_number);

CREATE TABLE IF NOT EXISTS painel_operador_offspec_tank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_name TEXT DEFAULT 'Off Spec Tank',
    row_number INTEGER DEFAULT 0,
    offspec_date TEXT DEFAULT '',
    opening_gsv_m3 REAL,
    closing_gsv_m3 REAL,
    delta_tank_m3 REAL,
    directed_to_offspec TEXT DEFAULT '',
    directed_volume_m3 REAL,
    reprocessed_volume_m3 REAL,
    status TEXT DEFAULT '',
    note TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_daily_checklist_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_offspec_tank_lookup
    ON painel_operador_offspec_tank(import_run_id, offspec_date, status);
CREATE INDEX IF NOT EXISTS idx_painel_operador_offspec_tank_file
    ON painel_operador_offspec_tank(file_hash, row_number);

CREATE TABLE IF NOT EXISTS painel_operador_quality_lab_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_name TEXT DEFAULT 'Lab-Report',
    row_number INTEGER DEFAULT 0,
    sample_date TEXT DEFAULT '',
    lab_report_id TEXT DEFAULT '',
    api_gravity REAL,
    api_deviation REAL,
    density_kg_m3 REAL,
    density_cv_g_cm3 REAL,
    bsw_percent REAL,
    bsw_flowline_percent REAL,
    bsw_xml040_percent REAL,
    method TEXT DEFAULT '',
    blend_manual TEXT DEFAULT '',
    status TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_daily_checklist_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_quality_lab_lookup
    ON painel_operador_quality_lab_samples(import_run_id, sample_date, status);
CREATE INDEX IF NOT EXISTS idx_painel_operador_quality_lab_file
    ON painel_operador_quality_lab_samples(file_hash, row_number);

CREATE TABLE IF NOT EXISTS painel_operador_api_weighted_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_name TEXT DEFAULT 'API',
    row_number INTEGER DEFAULT 0,
    api_date TEXT DEFAULT '',
    weighted_api REAL,
    net_volume_m3 REAL,
    api_volume REAL,
    weighted_bsw_percent REAL,
    bsw_volume REAL,
    total_volume_m3 REAL,
    status TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_daily_checklist_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_api_weighted_lookup
    ON painel_operador_api_weighted_daily(import_run_id, api_date, status);
CREATE INDEX IF NOT EXISTS idx_painel_operador_api_weighted_file
    ON painel_operador_api_weighted_daily(file_hash, row_number);

CREATE TABLE IF NOT EXISTS painel_operador_mpfm_fiscal_oil (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_name TEXT DEFAULT 'MPFM Subsea x Fiscal- Óleo',
    row_number INTEGER DEFAULT 0,
    production_date TEXT DEFAULT '',
    pe4_oil_m3 REAL,
    pe2_bank10_oil_m3 REAL,
    pe2_bank15_oil_m3 REAL,
    reprocess_oil_m3 REAL,
    total_mpfm_oil_m3 REAL,
    fiscal_oil_m3 REAL,
    variance_percent REAL,
    comment TEXT DEFAULT '',
    source_status TEXT DEFAULT '',
    status TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_daily_checklist_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_mpfm_fiscal_oil_lookup
    ON painel_operador_mpfm_fiscal_oil(import_run_id, production_date, status);
CREATE INDEX IF NOT EXISTS idx_painel_operador_mpfm_fiscal_oil_file
    ON painel_operador_mpfm_fiscal_oil(file_hash, row_number);

CREATE TABLE IF NOT EXISTS painel_operador_gas_balance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_name TEXT DEFAULT 'Balanço de Gás',
    row_number INTEGER DEFAULT 0,
    gas_date TEXT DEFAULT '',
    hp_separator_mm3 REAL,
    test_separator_mm3 REAL,
    fwko_drum_mm3 REAL,
    first_stage_flash_mm3 REAL,
    second_stage_flash_mm3 REAL,
    gas_lift_riser_mm3 REAL,
    operational_total_mm3 REAL,
    gas_injection_riser1_mm3 REAL,
    gas_injection_riser2_mm3 REAL,
    hp_flare_mm3 REAL,
    igg_mm3 REAL,
    lp_flare_mm3 REAL,
    pilot_mm3 REAL,
    gtg_mm3 REAL,
    vent_tank_mm3 REAL,
    fiscal_injection_total_mm3 REAL,
    delta_mm3 REAL,
    delta_percent REAL,
    comment TEXT DEFAULT '',
    status TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_run_id) REFERENCES painel_operador_daily_checklist_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_painel_operador_gas_balance_lookup
    ON painel_operador_gas_balance(import_run_id, gas_date, status);
CREATE INDEX IF NOT EXISTS idx_painel_operador_gas_balance_file
    ON painel_operador_gas_balance(file_hash, row_number);

CREATE TABLE IF NOT EXISTS sgmfm_rotina_diaria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_code TEXT NOT NULL,
    title TEXT DEFAULT '',
    status TEXT DEFAULT '',
    base_date TEXT DEFAULT '',
    reference_date TEXT DEFAULT '',
    analysis_date TEXT DEFAULT '',
    measurement_point TEXT DEFAULT '',
    bank TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    instrument TEXT DEFAULT '',
    loop TEXT DEFAULT '',
    meter_type TEXT DEFAULT '',
    generated_html TEXT DEFAULT '',
    generated_at TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sgmfm_rotina_lookup
    ON sgmfm_rotina_diaria(active, base_date, bank, tag);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sgmfm_rotina_key
    ON sgmfm_rotina_diaria(base_date, measurement_point, active);

CREATE TABLE IF NOT EXISTS sgmfm_logbook (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_code TEXT NOT NULL,
    title TEXT DEFAULT '',
    status TEXT DEFAULT '',
    base_date TEXT DEFAULT '',
    reference_date TEXT DEFAULT '',
    analysis_date TEXT DEFAULT '',
    measurement_point TEXT DEFAULT '',
    bank TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    instrument TEXT DEFAULT '',
    loop TEXT DEFAULT '',
    meter_type TEXT DEFAULT '',
    generated_html TEXT DEFAULT '',
    generated_at TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sgmfm_logbook_lookup
    ON sgmfm_logbook(active, reference_date, bank, tag);

CREATE TABLE IF NOT EXISTS sgmfm_analise_pvt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_code TEXT NOT NULL,
    title TEXT DEFAULT '',
    status TEXT DEFAULT '',
    base_date TEXT DEFAULT '',
    reference_date TEXT DEFAULT '',
    analysis_date TEXT DEFAULT '',
    measurement_point TEXT DEFAULT '',
    bank TEXT DEFAULT '',
    tag TEXT DEFAULT '',
    instrument TEXT DEFAULT '',
    loop TEXT DEFAULT '',
    meter_type TEXT DEFAULT '',
    generated_html TEXT DEFAULT '',
    generated_at TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sgmfm_pvt_lookup
    ON sgmfm_analise_pvt(active, analysis_date, bank, tag);

CREATE TABLE IF NOT EXISTS sgmfm_visibility_prefs (
    record_type TEXT PRIMARY KEY,
    visible_keys_json TEXT DEFAULT '[]',
    updated_at TEXT NOT NULL
);
"""


def apply_schema(cur) -> None:
    cur.executescript(SCHEMA_SQL)


import re as _re
_TAG_SAFE_RE = _re.compile(r'^[A-Za-z0-9_\-]+$')


def rebuild_active_view(conn, inactive_tags: list[str]) -> None:
    """Drop and recreate measurements_active VIEW based on current cadastro ativo flags.

    The view exposes all rows from measurements_curated except those whose
    tag_associado is listed as ativo=False in cadastro.json.  All display
    queries should read from this view so inactive instruments never appear
    in the UI.  Import / DELETE operations continue to target the underlying
    measurements_curated table directly.
    """
    cur = conn.cursor()
    cur.execute("DROP VIEW IF EXISTS measurements_active")
    # SQLite does not support parameters (?) in DDL statements, so string
    # interpolation is unavoidable here.  We mitigate injection risk by
    # whitelisting: only tags matching ^[A-Za-z0-9_\-]+$ are included.
    safe_tags = [t for t in inactive_tags if _TAG_SAFE_RE.match(t)]
    if safe_tags:
        placeholders = ",".join(f"'{t}'" for t in safe_tags)
        view_sql = (
            f"CREATE VIEW measurements_active AS "
            f"SELECT * FROM measurements_curated "
            f"WHERE tag NOT IN ({placeholders})"
        )
    else:
        view_sql = "CREATE VIEW measurements_active AS SELECT * FROM measurements_curated"
    cur.execute(view_sql)
    conn.commit()


def run_migrations(cur) -> None:
    files_cols = [r[1] for r in cur.execute("PRAGMA table_info(files_imported)").fetchall()]
    files_sql_row = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='files_imported'"
    ).fetchone()
    files_sql = (files_sql_row[0] or "") if files_sql_row else ""
    needs_files_rebuild = ("file_hash" not in files_cols) or ("UNIQUE(filename, content_date)" in files_sql)
    if needs_files_rebuild:
        cur.execute("ALTER TABLE files_imported RENAME TO files_imported_legacy")
        cur.executescript(
            """
CREATE TABLE IF NOT EXISTS files_imported (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    filename TEXT NOT NULL,
    ext TEXT,
    file_type TEXT,
    unit_code TEXT,
    meter_id TEXT,
    location TEXT,
    content_date TEXT,
    report_start TEXT,
    report_end TEXT,
    excel_month TEXT,
    identity_key TEXT,
    time_source TEXT,
    file_hash TEXT,
    processed_ok INTEGER DEFAULT 1,
    message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES processing_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_files_imported_lookup
    ON files_imported(content_date, ext, file_type, meter_id);
CREATE INDEX IF NOT EXISTS idx_files_imported_hash
    ON files_imported(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_imported_identity
    ON files_imported(identity_key);
"""
        )
        cur.execute(
            """
            INSERT INTO files_imported(
                id, run_id, filename, ext, file_type, unit_code, meter_id, location,
                content_date, report_start, report_end, excel_month, identity_key, time_source,
                file_hash, processed_ok, message, created_at
            )
            SELECT
                id, run_id, filename, ext, file_type, unit_code, meter_id, location,
                content_date, '', '', excel_month, '', '', '', processed_ok, message, created_at
            FROM files_imported_legacy
            """
        )
        cur.execute("DROP TABLE files_imported_legacy")
    else:
        if "file_hash" not in files_cols:
            cur.execute("ALTER TABLE files_imported ADD COLUMN file_hash TEXT")
        if "report_start" not in files_cols:
            cur.execute("ALTER TABLE files_imported ADD COLUMN report_start TEXT")
        if "report_end" not in files_cols:
            cur.execute("ALTER TABLE files_imported ADD COLUMN report_end TEXT")
        if "identity_key" not in files_cols:
            cur.execute("ALTER TABLE files_imported ADD COLUMN identity_key TEXT")
        if "time_source" not in files_cols:
            cur.execute("ALTER TABLE files_imported ADD COLUMN time_source TEXT")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_files_imported_lookup ON files_imported(content_date, ext, file_type, meter_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_files_imported_hash ON files_imported(file_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_files_imported_identity ON files_imported(identity_key)")

    raw_cols = [r[1] for r in cur.execute("PRAGMA table_info(source_files_raw)").fetchall()]
    if "report_start" not in raw_cols:
        cur.execute("ALTER TABLE source_files_raw ADD COLUMN report_start TEXT")
    if "report_end" not in raw_cols:
        cur.execute("ALTER TABLE source_files_raw ADD COLUMN report_end TEXT")
    if "identity_key" not in raw_cols:
        cur.execute("ALTER TABLE source_files_raw ADD COLUMN identity_key TEXT")
    if "time_source" not in raw_cols:
        cur.execute("ALTER TABLE source_files_raw ADD COLUMN time_source TEXT")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_source_files_raw_identity ON source_files_raw(identity_key)")

    cols = [r[1] for r in cur.execute("PRAGMA table_info(measurements_curated)").fetchall()]
    if "source_record_id" not in cols:
        cur.execute("ALTER TABLE measurements_curated ADD COLUMN source_record_id INTEGER")
    if "is_official" not in cols:
        cur.execute("ALTER TABLE measurements_curated ADD COLUMN is_official INTEGER DEFAULT 1")
    cur.execute("UPDATE measurements_curated SET is_official=1 WHERE is_official IS NULL")

    try:
        cur.execute("DROP INDEX IF EXISTS idx_sep_alignments_unique_active")
    except Exception:
        pass

    cols2 = [r[1] for r in cur.execute("PRAGMA table_info(sep_alignments)").fetchall()]
    if "is_official" not in cols2:
        cur.execute("ALTER TABLE sep_alignments ADD COLUMN is_official INTEGER DEFAULT 1")
    if "resolution_status" not in cols2:
        cur.execute("ALTER TABLE sep_alignments ADD COLUMN resolution_status TEXT DEFAULT 'official'")
    cur.execute("UPDATE sep_alignments SET is_official=1 WHERE is_official IS NULL")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sep_alignments_key ON sep_alignments(production_date, bank, is_active)")

    try:
        cur.execute("DROP INDEX IF EXISTS idx_daily_cards_unique_active")
    except Exception:
        pass

    cols3 = [r[1] for r in cur.execute("PRAGMA table_info(daily_cards)").fetchall()]
    if "is_official" not in cols3:
        cur.execute("ALTER TABLE daily_cards ADD COLUMN is_official INTEGER DEFAULT 1")
    if "resolution_status" not in cols3:
        cur.execute("ALTER TABLE daily_cards ADD COLUMN resolution_status TEXT DEFAULT 'official'")
    if "sep_test_aligned" not in cols3:
        cur.execute("ALTER TABLE daily_cards ADD COLUMN sep_test_aligned TEXT DEFAULT ''")
    cur.execute("UPDATE daily_cards SET is_official=1 WHERE is_official IS NULL")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_cards_key ON daily_cards(production_date, bank, card_type, tag, instrument, is_active)")

    deadline_cols = [r[1] for r in cur.execute("PRAGMA table_info(deadline_items)").fetchall()]
    deadline_extra_cols = {
        "source_ref": "TEXT DEFAULT ''",
        "source_file": "TEXT DEFAULT ''",
        "norm_ref": "TEXT DEFAULT ''",
        "evidence_required": "TEXT DEFAULT ''",
        "responsible_area": "TEXT DEFAULT ''",
        "trigger_event": "TEXT DEFAULT ''",
        "risk_level": "TEXT DEFAULT ''",
        "recommended_action": "TEXT DEFAULT ''",
        "completion_date": "TEXT DEFAULT ''",
        "source_status": "TEXT DEFAULT ''",
    }
    for col, ddl in deadline_extra_cols.items():
        if col not in deadline_cols:
            cur.execute(f"ALTER TABLE deadline_items ADD COLUMN {col} {ddl}")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deadline_items_source ON deadline_items(source_file, source_ref)")

    monitoring_cols = [r[1] for r in cur.execute("PRAGMA table_info(mpfm_monitoring_daily)").fetchall()]
    if monitoring_cols:
        if "instrument" not in monitoring_cols:
            cur.execute("ALTER TABLE mpfm_monitoring_daily ADD COLUMN instrument TEXT DEFAULT ''")
        if "loop" not in monitoring_cols:
            cur.execute("ALTER TABLE mpfm_monitoring_daily ADD COLUMN loop TEXT DEFAULT ''")
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_mpfm_monitoring_daily_unique ON mpfm_monitoring_daily(production_date, bank, tag, meter_type)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_mpfm_monitoring_daily_lookup ON mpfm_monitoring_daily(production_date, bank, meter_type)"
        )

    catalog_cols = [r[1] for r in cur.execute("PRAGMA table_info(well_catalog_042)").fetchall()]
    if catalog_cols:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_well_catalog_042_lookup ON well_catalog_042(well_operator_name, subsea_tag, active, enabled_042)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_well_catalog_042_cod ON well_catalog_042(cod_cadastro_poco)"
        )

    tpoc_cols = [r[1] for r in cur.execute("PRAGMA table_info(tpoc_daily_potential_curated)").fetchall()]
    if tpoc_cols:
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tpoc_daily_potential_unique ON tpoc_daily_potential_curated(production_day, bank, well_operator_name, subsea_tag)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_tpoc_daily_potential_lookup ON tpoc_daily_potential_curated(production_day, bank, well_operator_name, subsea_tag)"
        )

    xml042_cols = [r[1] for r in cur.execute("PRAGMA table_info(xml042_documents)").fetchall()]
    if xml042_cols:
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_xml042_documents_unique ON xml042_documents(production_day, cod_cadastro_poco)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_xml042_documents_lookup ON xml042_documents(production_day, bank, cod_cadastro_poco)"
        )

    sep_source_cols = [r[1] for r in cur.execute("PRAGMA table_info(sep_source_files)").fetchall()]
    if sep_source_cols:
        if "report_start" not in sep_source_cols:
            cur.execute("ALTER TABLE sep_source_files ADD COLUMN report_start TEXT DEFAULT ''")
        if "report_end" not in sep_source_cols:
            cur.execute("ALTER TABLE sep_source_files ADD COLUMN report_end TEXT DEFAULT ''")
        if "identity_key" not in sep_source_cols:
            cur.execute("ALTER TABLE sep_source_files ADD COLUMN identity_key TEXT DEFAULT ''")
        if "time_source" not in sep_source_cols:
            cur.execute("ALTER TABLE sep_source_files ADD COLUMN time_source TEXT DEFAULT 'content'")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sep_source_identity ON sep_source_files(identity_key)")

    alarm_reference_cols = [r[1] for r in cur.execute("PRAGMA table_info(alarm_reference_values)").fetchall()]
    if alarm_reference_cols:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarm_reference_values_lookup ON alarm_reference_values(domain, active, sort_order)"
        )

    alarm_record_cols = [r[1] for r in cur.execute("PRAGMA table_info(alarm_records)").fetchall()]
    if alarm_record_cols:
        if "record_type" not in alarm_record_cols:
            cur.execute("ALTER TABLE alarm_records ADD COLUMN record_type TEXT DEFAULT 'event'")
        if "source_sheet" not in alarm_record_cols:
            cur.execute("ALTER TABLE alarm_records ADD COLUMN source_sheet TEXT DEFAULT ''")
        if "family_code" not in alarm_record_cols:
            cur.execute("ALTER TABLE alarm_records ADD COLUMN family_code TEXT DEFAULT ''")
        if "measurement_point" not in alarm_record_cols:
            cur.execute("ALTER TABLE alarm_records ADD COLUMN measurement_point TEXT DEFAULT ''")
        if "measurement_state" not in alarm_record_cols:
            cur.execute("ALTER TABLE alarm_records ADD COLUMN measurement_state TEXT DEFAULT ''")
        if "occurrence_count" not in alarm_record_cols:
            cur.execute("ALTER TABLE alarm_records ADD COLUMN occurrence_count INTEGER DEFAULT 0")
        if "distinct_alarm_count" not in alarm_record_cols:
            cur.execute("ALTER TABLE alarm_records ADD COLUMN distinct_alarm_count INTEGER DEFAULT 0")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarm_records_lookup ON alarm_records(active, status_code, severity_code, production_date, bank, tag)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarm_records_event ON alarm_records(event_at, category_code, priority_code)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarm_records_record_type ON alarm_records(record_type, source_sheet, measurement_point, family_code)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarm_records_external ON alarm_records(source_kind, source_ref, source_sheet, record_type, external_code)"
        )

    alarm_action_cols = [r[1] for r in cur.execute("PRAGMA table_info(alarm_actions)").fetchall()]
    if alarm_action_cols:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarm_actions_lookup ON alarm_actions(alarm_id, active, status_code, due_date)"
        )

    alarm_audit_cols = [r[1] for r in cur.execute("PRAGMA table_info(alarm_audit_log)").fetchall()]
    if alarm_audit_cols:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarm_audit_log_lookup ON alarm_audit_log(alarm_id, action_id, created_at)"
        )

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT DEFAULT '',
            source_page TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_ai_conversations_lookup
            ON ai_conversations(active, updated_at);

        CREATE TABLE IF NOT EXISTS ai_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            provider TEXT DEFAULT '',
            model TEXT DEFAULT '',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation
            ON ai_messages(conversation_id, created_at);

        CREATE TABLE IF NOT EXISTS ai_action_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            message_id INTEGER,
            action_type TEXT DEFAULT 'record_note',
            target_area TEXT DEFAULT 'nota',
            title TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            source_content TEXT DEFAULT '',
            payload_json TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            requested_by TEXT DEFAULT 'user',
            approved_by TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            approved_at TEXT DEFAULT '',
            applied_at TEXT DEFAULT '',
            result_json TEXT DEFAULT '{}',
            FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id),
            FOREIGN KEY(message_id) REFERENCES ai_messages(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ai_action_requests_status
            ON ai_action_requests(status, target_area, created_at);
        """
    )

    cur.executescript(
        """
        INSERT OR IGNORE INTO alarm_reference_values(domain, code, label, description, sort_order, is_terminal, is_default, active, created_at, updated_at)
        VALUES
        ('severity', 'info', 'Info', 'Evento informativo', 10, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('severity', 'warning', 'Atenção', 'Requer acompanhamento operacional', 20, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('severity', 'critical', 'Crítica', 'Requer ação prioritária', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('priority', 'low', 'Baixa', 'Baixa prioridade de tratamento', 10, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('priority', 'medium', 'Média', 'Prioridade média de tratamento', 20, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('priority', 'high', 'Alta', 'Alta prioridade de tratamento', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('priority', 'urgent', 'Urgente', 'Tratamento imediato', 40, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('status', 'open', 'Aberta', 'Ocorrência aberta', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('status', 'in_progress', 'Em andamento', 'Tratamento em curso', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('status', 'monitoring', 'Monitoramento', 'Acompanhamento ativo', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('status', 'closed', 'Concluída', 'Ocorrência concluída', 40, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('status', 'cancelled', 'Cancelada', 'Ocorrência cancelada', 50, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('action_status', 'open', 'Aberta', 'Ação aberta', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('action_status', 'in_progress', 'Em andamento', 'Ação em andamento', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('action_status', 'closed', 'Concluída', 'Ação concluída', 30, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('action_status', 'cancelled', 'Cancelada', 'Ação cancelada', 40, 1, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('action_type', 'immediate', 'Ação imediata', 'Resposta imediata ao alarme', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('action_type', 'corrective', 'Ação corretiva', 'Ação corretiva planejada', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('action_type', 'preventive', 'Ação preventiva', 'Ação preventiva vinculada ao alarme', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('source_kind', 'manual', 'Manual', 'Registro manual operacional', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('source_kind', 'import', 'Importado', 'Origem externa importada', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('source_kind', 'system', 'Sistema', 'Gerado automaticamente pelo sistema', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('source_kind', 'workbook', 'Workbook', 'Importação a partir de workbook operacional', 40, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('record_type', 'event', 'Evento', 'Ocorrência unitária de alarme', 10, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('record_type', 'incident', 'Incidente', 'Agrupamento operacional de eventos', 20, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'communication', 'Comunicação', 'Falhas de comunicação, congelamento ou indisponibilidade', 10, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'warning', 'Alarmes / warnings', 'Alarmes e advertências do medidor', 20, 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'mode_change', 'Eventos / mudança indevida', 'Mudanças indevidas de modo ou fallback', 30, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'redundancy', 'Transmissor / A/B', 'Redundância ou troca A/B', 40, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'pvt', 'PVT / condição padrão', 'Condição padrão e coerência PVT', 50, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'deviation', 'Desvio topside vs subsea', 'Desvio entre sistemas de medição', 60, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'critical_variable', 'Variável crítica', 'Anomalia em variáveis críticas de processo', 70, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('category', 'other', 'Outro', 'Ocorrência classificada manualmente', 80, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """
    )

    recon_cols = [r[1] for r in cur.execute("PRAGMA table_info(recon_runs)").fetchall()]
    if recon_cols and "analytical_snapshot" not in recon_cols:
        cur.execute("ALTER TABLE recon_runs ADD COLUMN analytical_snapshot TEXT")
    if recon_cols and "campaign_id" not in recon_cols:
        cur.execute("ALTER TABLE recon_runs ADD COLUMN campaign_id INTEGER")
    if recon_cols and "campaign_phase" not in recon_cols:
        cur.execute("ALTER TABLE recon_runs ADD COLUMN campaign_phase TEXT DEFAULT 'baseline'")
    if recon_cols and "test_window_json" not in recon_cols:
        cur.execute("ALTER TABLE recon_runs ADD COLUMN test_window_json TEXT")

    campaign_cols = [r[1] for r in cur.execute("PRAGMA table_info(recon_campaigns)").fetchall()]
    if campaign_cols:
        if "current_k_factor" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN current_k_factor REAL")
        if "proposal_mode" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN proposal_mode TEXT DEFAULT 'hc'")
        if "proposal_rule" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN proposal_rule TEXT DEFAULT 'mass_ratio_24h'")
        if "proposal_status" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN proposal_status TEXT DEFAULT 'pending'")
        if "proposed_k_factor_hc" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN proposed_k_factor_hc REAL")
        if "proposed_k_factor_total" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN proposed_k_factor_total REAL")
        if "proposed_k_factor_selected" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN proposed_k_factor_selected REAL")
        if "proposed_k_factor_manual" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN proposed_k_factor_manual REAL")
        if "applied_k_factor" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN applied_k_factor REAL")
        if "applied_at" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN applied_at TEXT DEFAULT ''")
        if "baseline_desvio_hc_pct" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN baseline_desvio_hc_pct REAL")
        if "baseline_desvio_total_pct" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN baseline_desvio_total_pct REAL")
        if "post_desvio_hc_pct" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN post_desvio_hc_pct REAL")
        if "post_desvio_total_pct" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN post_desvio_total_pct REAL")
        if "improvement_hc_pp" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN improvement_hc_pp REAL")
        if "improvement_total_pp" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN improvement_total_pp REAL")
        if "monitoring_status" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN monitoring_status TEXT DEFAULT ''")
        if "baseline_run_id" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN baseline_run_id INTEGER")
        if "post_day_ref" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN post_day_ref TEXT DEFAULT ''")
        if "post_run_id" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN post_run_id INTEGER")
        if "pvt_snapshot" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN pvt_snapshot TEXT DEFAULT '{}'")
        if "analytical_snapshot" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN analytical_snapshot TEXT DEFAULT '{}'")
        if "sep_alignment_snapshot" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN sep_alignment_snapshot TEXT DEFAULT '{}'")
        if "status" not in campaign_cols:
            cur.execute("ALTER TABLE recon_campaigns ADD COLUMN status TEXT DEFAULT 'baseline'")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_recon_campaigns_lookup ON recon_campaigns(bank, tag, baseline_day_ref, status)")
