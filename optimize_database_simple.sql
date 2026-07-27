-- ═══════════════════════════════════════════════════════════════════
-- ÍNDICES CRÍTICOS DE PERFORMANCE - MPFM Manager (VERSÃO CORRIGIDA)
-- Baseado no schema real do banco de dados
-- ═══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────────
-- 1. measurements_curated (tabela MAIS usada)
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

CREATE INDEX IF NOT EXISTS idx_measurements_day_bank_metric
    ON measurements_curated(day_ref, bank, metric_name);

-- ────────────────────────────────────────────────────────────────────
-- 2. daily_cards
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_cards_production_bank_type
    ON daily_cards(production_date, bank, card_type);

CREATE INDEX IF NOT EXISTS idx_cards_tag_instrument
    ON daily_cards(tag, instrument);

CREATE INDEX IF NOT EXISTS idx_cards_active_production
    ON daily_cards(is_active, production_date);

-- ────────────────────────────────────────────────────────────────────
-- 3. sep_source_files
-- ────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_sep_production_fluid_meter
    ON sep_source_files(production_date, fluid_kind, meter_id);

CREATE INDEX IF NOT EXISTS idx_sep_official_production
    ON sep_source_files(is_official, production_date);

CREATE INDEX IF NOT EXISTS idx_sep_identity_key
    ON sep_source_files(identity_key);

-- ────────────────────────────────────────────────────────────────────
-- 4. files_imported
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
-- 5. Atualiza estatísticas
-- ────────────────────────────────────────────────────────────────────

ANALYZE;
