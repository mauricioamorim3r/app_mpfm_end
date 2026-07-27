-- ═══════════════════════════════════════════════════════════════════
-- ÍNDICES CRÍTICOS DE PERFORMANCE - MPFM Manager
-- Execução estimada: 30-60 segundos (database 1.6GB)
-- Ganho esperado: 5-10x mais rápido em queries filtradas
-- ═══════════════════════════════════════════════════════════════════

BEGIN TRANSACTION;

-- ────────────────────────────────────────────────────────────────────
-- 1. measurements_curated (tabela mais usada, ~80% das queries)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_measurements_row_kind_day
    ON measurements_curated(row_kind, day_ref);

CREATE INDEX IF NOT EXISTS idx_measurements_bank_day
    ON measurements_curated(bank, day_ref);

CREATE INDEX IF NOT EXISTS idx_measurements_source_record
    ON measurements_curated(source_record_id);

CREATE INDEX IF NOT EXISTS idx_measurements_official_day
    ON measurements_curated(is_official, day_ref);

CREATE INDEX IF NOT EXISTS idx_measurements_tag_instrument
    ON measurements_curated(tag, instrument);

-- Índice composto para queries de séries temporais
CREATE INDEX IF NOT EXISTS idx_measurements_day_bank_metric
    ON measurements_curated(day_ref, bank, metric_name);

-- ────────────────────────────────────────────────────────────────────
-- 2. daily_cards (segunda tabela mais consultada)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_cards_production_bank_type
    ON daily_cards(production_date, bank, card_type);

CREATE INDEX IF NOT EXISTS idx_cards_tag_instrument
    ON daily_cards(tag, instrument);

CREATE INDEX IF NOT EXISTS idx_cards_active_production
    ON daily_cards(is_active, production_date);

-- Para busca de duplicatas
CREATE INDEX IF NOT EXISTS idx_cards_duplicate_check
    ON daily_cards(production_date, bank, card_type, tag, instrument)
    WHERE is_active = 1;

-- ────────────────────────────────────────────────────────────────────
-- 3. sep_source_files (importação SEP)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_sep_production_fluid_meter
    ON sep_source_files(production_date, fluid_kind, meter_id);

CREATE INDEX IF NOT EXISTS idx_sep_official_production
    ON sep_source_files(is_official, production_date);

CREATE INDEX IF NOT EXISTS idx_sep_identity_key
    ON sep_source_files(identity_key);

-- Para recompute_sep_source_resolution()
CREATE INDEX IF NOT EXISTS idx_sep_resolution_check
    ON sep_source_files(production_date, fluid_kind, meter_id, is_official);

-- ────────────────────────────────────────────────────────────────────
-- 4. files_imported (histórico de importações)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_files_identity_key
    ON files_imported(identity_key);

CREATE INDEX IF NOT EXISTS idx_files_hash
    ON files_imported(file_hash);

CREATE INDEX IF NOT EXISTS idx_files_run_id
    ON files_imported(run_id);

CREATE INDEX IF NOT EXISTS idx_files_created_at
    ON files_imported(created_at DESC);

-- ────────────────────────────────────────────────────────────────────
-- 5. sep_alignments (reconciliação)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_alignments_active_date
    ON sep_alignments(is_active, production_date);

CREATE INDEX IF NOT EXISTS idx_alignments_duplicate_check
    ON sep_alignments(production_date, bank, meter_id)
    WHERE is_active = 1;

-- ────────────────────────────────────────────────────────────────────
-- 6. alarm_records (sistema de alarmes)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_alarm_active_date
    ON alarm_records(is_active, alarm_date DESC);

CREATE INDEX IF NOT EXISTS idx_alarm_status
    ON alarm_records(status, alarm_date DESC);

-- ────────────────────────────────────────────────────────────────────
-- 7. painel_operador_* (dashboard operacional)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_painel_calendar_date
    ON painel_operador_calendar_days(day_ref DESC);

CREATE INDEX IF NOT EXISTS idx_painel_export_run_date
    ON painel_operador_anp_export_runs(export_date DESC);

-- ────────────────────────────────────────────────────────────────────
-- 8. processing_runs (monitoramento de processamento)
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_processing_started_at
    ON processing_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_processing_status
    ON processing_runs(status, started_at DESC);

-- ────────────────────────────────────────────────────────────────────
-- 9. Estatísticas e análise
-- ────────────────────────────────────────────────────────────────────

-- Atualiza estatísticas do SQLite para otimizador de queries
ANALYZE;

COMMIT;

-- ────────────────────────────────────────────────────────────────────
-- Verificação: Lista todos os índices criados
-- ────────────────────────────────────────────────────────────────────

SELECT
    name as index_name,
    tbl_name as table_name,
    sql
FROM sqlite_master
WHERE type = 'index'
  AND name LIKE 'idx_%'
ORDER BY tbl_name, name;
