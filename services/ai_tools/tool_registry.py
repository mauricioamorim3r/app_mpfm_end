from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any


def _safe_text(value: Any, limit: int = 160) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "..."
    return text


def _query_words(question: str) -> set[str]:
    normalized = str(question or "").lower()
    for char in ",.;:!?()[]{}\n\t":
        normalized = normalized.replace(char, " ")
    return {part for part in normalized.split() if part}


def _wants_any(words: set[str], candidates: set[str]) -> bool:
    return bool(words & candidates)


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name=? AND type IN ('table','view')",
        (name,),
    ).fetchone()
    return bool(row)


def _has_column(conn, table: str, column: str) -> bool:
    try:
        return column in {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return False


def _explicit_month(question: str) -> str:
    match = re.search(r"\b(20\d{2})[-/](0[1-9]|1[0-2])\b", str(question or ""))
    return f"{match.group(1)}-{match.group(2)}" if match else ""


def _period_label(month: str = "") -> str:
    return f"mês={month[:7]}" if month else "todos os períodos disponíveis"


def _month_where(column: str, month: str, prefix: str = "WHERE") -> tuple[str, tuple[Any, ...]]:
    if month:
        return f" {prefix} substr({column},1,7)=?", (month[:7],)
    return "", ()


def _normalize_identifier(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _sql_normalized(column: str) -> str:
    return f"REPLACE(REPLACE(REPLACE(UPPER(COALESCE({column},'')), ' ', ''), '-', ''), '_', '')"


def _detect_known_measurement_filters(conn, table: str, question: str) -> dict[str, str]:
    question_norm = _normalize_identifier(question)
    filters: dict[str, str] = {}
    for column in ("tag", "bank", "instrument"):
        if not _has_column(conn, table, column):
            continue
        try:
            rows = conn.execute(
                f"""
                SELECT DISTINCT {column}
                FROM {table}
                WHERE COALESCE({column}, '')<>''
                ORDER BY LENGTH({column}) DESC, {column}
                LIMIT 500
                """
            ).fetchall()
        except Exception:
            continue
        for row in rows:
            value = str(row[0] or "").strip()
            normalized = _normalize_identifier(value)
            if normalized and normalized in question_norm:
                filters[column] = value
                break
    return filters


def _measurement_filter_sql(filters: dict[str, str], prefix: str = "AND") -> tuple[str, tuple[Any, ...]]:
    clauses = []
    params: list[Any] = []
    for column in ("bank", "tag", "instrument"):
        value = filters.get(column)
        if not value:
            continue
        clauses.append(f"({_sql_normalized(column)}=?)")
        params.append(_normalize_identifier(value))
    if not clauses:
        return "", ()
    return f" {prefix} " + " AND ".join(clauses), tuple(params)


def _source_catalog_lines() -> list[str]:
    return [
        "\n[guia: mapa_de_fontes_da_ia]",
        "Medições MPFM/SEP detalhadas: use measurements_active/measurements_curated para daily, hourly, sep e detalhes por fase; use measurements_raw para valores brutos/payload de importação quando disponível.",
        "Sensores e parâmetros brutos: pressão, temperatura, densidades, PVT e métricas de massa/volume estão em measurements_active por metric_name/metric_value e, quando necessário, em payload_json de measurements_raw.",
        "Alarmes e eventos: use alarm_records para listagem/detalhe, alarm_actions para ações/resolução, alarm_audit_log para histórico de alterações e alarm_reference_values para catálogos.",
        "Issues de validação: use validation_issues para detalhe por run/arquivo/referência e parsing_events_raw/source_files_raw para causa de parsing/importação.",
        "Prazos: use deadline_items para prazos ativos/concluídos quando registrados; documentos/evidências só aparecem se estiverem em notes/payloads ou em módulos documentais importados.",
        "Ativos e metadados: use well_catalog_042 para poços/tags subsea/XML042, pvt_params para configuração/calibração PVT/MPFM, sep_alignments para alinhamento MPFM x SEP e mpfm_monitoring_daily para estado operacional por banco/TAG.",
        "Reconciliação e calibração: use recon_runs/recon_campaigns/pvt_params para resultados, desvios, fator K, janela de teste, snapshots e parâmetros aplicados.",
        "Arquivos e rastreabilidade: use processing_runs, files_imported, source_files_raw, sep_source_files e parsing_events_raw para saber origem, hash, status e mensagens de importação.",
        "Painel do Operador/Radar ANP: use painel_operador_file_index para arquivos catalogados, painel_operador_anp_export_rows para exports ANP normalizados, painel_operador_comparisons para Fiscal/Radar raw/XML/ANP, painel_operador_calendar_* para calendário/pendências e measurements_curated para MPFM diário.",
        "Checklist Diário do Painel Operador: use painel_operador_daily_checklist_rows para abas e registros gerais, painel_operador_tank_balance para Tank, painel_operador_offspec_tank para Off Spec Tank, painel_operador_gas_balance para Balanço de Gás, painel_operador_mpfm_fiscal_oil para MPFM Subsea x Fiscal-Óleo, painel_operador_quality_lab_samples e painel_operador_api_weighted_daily para Lab/API/BSW.",
        "Dossiês por ponto de medição: consolide por TAG usando painel_operador_comparisons, painel_operador_anp_export_rows, painel_operador_measurement_limits, painel_operador_file_index, painel_operador_proposals/evidence e measurements_curated; sinalize cobertura parcial quando nao houver TAG MPFM equivalente.",
        "Radar ANP inteligente: trate docs/RADAR_ANP_PLANO_MESTRE.md como contrato operacional e docs/RADAR_ANP_TEMPLATE_GERAL_INGESTAO.md/templates/Radar_ANP_Template_Geral_Ingestao.xlsx como modelo de carga manual, evidencia e propostas.",
        "Limites/PAM e configuração CV: use painel_operador_measurement_limits para limites aprovados, painel_operador_cv_config_snapshots para snapshots Parameters/Security por dia e painel_operador_cv_config_changes para diferenças de configuração entre dias.",
        "Apuração por dia de produção: cruzar arquivos catalogados, Fiscal/Radar, exports ANP, MPFM diário e pendências; não comparar m3 com t como delta final sem regra explícita de unidade/densidade.",
        "Acesso temporal: não há restrição automática por mês; as ferramentas consultam todos os períodos disponíveis salvo quando o usuário pedir explicitamente um período.",
        "Ações da IA: por padrão a IA é read-only; escrita deve virar proposta em ai_action_requests, depender de aprovação humana e, se aprovada, valer somente para o item/escopo solicitado.",
        "Integrações externas CMMS/regulatório/alocação: não há conector direto garantido; responder usando dados importados na aplicação ou informar que a integração externa ainda não está disponível.",
    ]


def _app_context_lines(app_context: dict[str, Any] | None) -> list[str]:
    ctx = app_context or {}
    lines = []
    page = _safe_text(ctx.get("current_page") or ctx.get("page"), 80)
    month = _safe_text(ctx.get("selected_month") or ctx.get("month"), 20)
    if page or month:
        lines.append("=== Contexto do frontend ===")
        if page:
            lines.append(f"Tela atual: {page}.")
        if month:
            lines.append(f"Mês selecionado: {month}.")
    filters = ctx.get("filters")
    if isinstance(filters, dict) and filters:
        pairs = []
        for key, value in list(filters.items())[:18]:
            if value in (None, "", [], {}):
                continue
            pairs.append(f"{_safe_text(key, 40)}={_safe_text(value, 80)}")
        if pairs:
            lines.append("Filtros/controles visíveis: " + "; ".join(pairs) + ".")
    return lines


def _scalar(conn, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def _tool_app_overview(conn) -> list[str]:
    lines = ["\n[tool: app_overview]"]
    for table, label in [
        ("measurements_curated", "Medições curadas"),
        ("alarm_records", "Registros de alarme"),
        ("deadline_items", "Prazos"),
        ("validation_issues", "Issues de validação"),
        ("processing_runs", "Execuções de importação"),
        ("sep_source_files", "Arquivos fonte SEP"),
        ("recon_runs", "Execuções de reconciliação"),
        ("pvt_params", "Parâmetros PVT/MPFM"),
        ("well_catalog_042", "Cadastro XML042/poços"),
        ("painel_operador_file_index", "Painel Operador - arquivos catalogados"),
        ("painel_operador_anp_export_rows", "Painel Operador - exports ANP"),
        ("painel_operador_comparisons", "Painel Operador - Fiscal/Radar"),
        ("painel_operador_calendar_days", "Painel Operador - dias de produção"),
        ("painel_operador_calendar_pendencies", "Painel Operador - pendências"),
        ("painel_operador_measurement_limits", "Painel Operador - limites PAM/faixa"),
        ("painel_operador_cv_config_snapshots", "Painel Operador - snapshots CV"),
        ("painel_operador_cv_config_changes", "Painel Operador - mudanças CV"),
        ("painel_operador_daily_checklist_rows", "Painel Operador - checklist diário"),
        ("painel_operador_tank_balance", "Painel Operador - Tank"),
        ("painel_operador_offspec_tank", "Painel Operador - Off Spec Tank"),
        ("painel_operador_gas_balance", "Painel Operador - balanço de gás"),
        ("painel_operador_mpfm_fiscal_oil", "Painel Operador - MPFM Subsea x Fiscal-Óleo"),
    ]:
        try:
            count = _scalar(conn, f"SELECT COUNT(*) FROM {table}")
            lines.append(f"{label}: {count:,}.".replace(",", "."))
        except Exception:
            continue
    latest_day = _scalar(conn, "SELECT MAX(day_ref) FROM measurements_curated")
    if latest_day:
        lines.append(f"Último dia com medição carregada: {latest_day}.")
    return lines


def _tool_painel_operador(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: painel_operador]"]
    if not _table_exists(conn, "painel_operador_file_index"):
        lines.append("Tabelas painel_operador_* ainda não estão disponíveis nesta base.")
        return lines

    lines.append("Painel do Operador integrado no SQLite principal em tabelas painel_operador_*; dados são read-only para consulta da IA.")
    lines.append("Dossiês por ponto devem cruzar TAG, limites/PAM, Fiscal/Radar, export ANP, arquivos, evidências/propostas e MPFM diário sem misturar m3 com t como delta final.")
    for table, label in [
        ("painel_operador_file_index", "arquivos catalogados"),
        ("painel_operador_anp_export_rows", "linhas de export ANP"),
        ("painel_operador_comparisons", "comparações Fiscal/Radar"),
        ("painel_operador_measurement_points", "pontos de medição"),
        ("painel_operador_evidence", "evidências, requisitos e eventos"),
        ("painel_operador_alerts", "alertas"),
        ("painel_operador_proposals", "propostas"),
        ("painel_operador_calendar_days", "dias operacionais"),
        ("painel_operador_calendar_pendencies", "pendências do calendário"),
        ("painel_operador_measurement_limits", "limites PAM/faixa aprovados"),
        ("painel_operador_cv_config_snapshots", "snapshots de configuração CV"),
        ("painel_operador_cv_config_changes", "mudanças de configuração CV"),
    ]:
        if _table_exists(conn, table):
            lines.append(f"{table} ({label}): {(_scalar(conn, f'SELECT COUNT(*) FROM {table}') or 0):,}.".replace(",", "."))

    if _table_exists(conn, "painel_operador_file_index_runs"):
        run = conn.execute(
            """
            SELECT id, finished_at, total_files, indexed_files, ignored_files, duplicate_files, total_size_bytes
            FROM painel_operador_file_index_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if run:
            lines.append(f"Última varredura de arquivos: run #{run[0]} em {run[1]}; total={run[2]}; indexados={run[3]}; ignorados={run[4]}; duplicados={run[5]}; bytes={run[6]}.")

    if _table_exists(conn, "painel_operador_anp_export_runs"):
        run = conn.execute(
            """
            SELECT id, finished_at, total_files, total_rows, counts_json
            FROM painel_operador_anp_export_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if run:
            lines.append(f"Última importação ANP: run #{run[0]} em {run[1]}; arquivos={run[2]}; linhas={run[3]}.")

    period_file_where, period_file_params = _month_where("inferred_date", month, "AND")
    rows = conn.execute(
        f"""
        SELECT category, document_kind, COUNT(*) AS n
        FROM painel_operador_file_index
        WHERE ignored=0{period_file_where}
        GROUP BY category, document_kind
        ORDER BY n DESC
        LIMIT 12
        """,
        period_file_params,
    ).fetchall()
    if rows:
        lines.append(f"Categorias de arquivos do Painel ({_period_label(month)}):")
        for row in rows:
            lines.append(f"{row[0]}/{row[1]}: {row[2]}.")

    if _table_exists(conn, "painel_operador_anp_export_rows"):
        period_anp_where, period_anp_params = _month_where("reference_date", month, "AND")
        rows = conn.execute(
            f"""
            SELECT family, record_kind, COUNT(*) AS n, MIN(reference_date), MAX(reference_date), COUNT(DISTINCT tag)
            FROM painel_operador_anp_export_rows
            WHERE 1=1{period_anp_where}
            GROUP BY family, record_kind
            ORDER BY n DESC
            LIMIT 8
            """,
            period_anp_params,
        ).fetchall()
        for row in rows:
            lines.append(f"Export ANP {row[0]}/{row[1]}: {row[2]} linhas; tags={row[5]}; período={row[3] or 'n/d'} a {row[4] or 'n/d'}.")

    period_comp_where, period_comp_params = _month_where("comparison_date", month, "AND")
    if _table_exists(conn, "painel_operador_comparisons"):
        comp = conn.execute(
            f"""
            SELECT COUNT(*), COUNT(DISTINCT comparison_date), COUNT(DISTINCT tag),
                   SUM(COALESCE(anp_corrigido,0)),
                   SUM(CASE WHEN status<>'' AND status<>'ok' THEN 1 ELSE 0 END)
            FROM painel_operador_comparisons
            WHERE 1=1{period_comp_where}
            """,
            period_comp_params,
        ).fetchone()
        if comp:
            lines.append(f"Fiscal/Radar ({_period_label(month)}): linhas={comp[0]}; dias={comp[1]}; tags={comp[2]}; volume_m3={comp[3] or 0:.3f}; alertas={comp[4] or 0}.")

    if _table_exists(conn, "painel_operador_calendar_days"):
        period_cal_where, period_cal_params = _month_where("calendar_date", month, "AND")
        cal = conn.execute(
            f"""
            SELECT COUNT(*), SUM(COALESCE(open_pending_count,0)), SUM(CASE WHEN loaded=1 THEN 1 ELSE 0 END)
            FROM painel_operador_calendar_days
            WHERE 1=1{period_cal_where}
            """,
            period_cal_params,
        ).fetchone()
        if cal:
            lines.append(f"Calendário do Painel ({_period_label(month)}): dias={cal[0]}; com carga={cal[2] or 0}; pendências abertas={cal[1] or 0}.")

    rows = conn.execute(
        """
        WITH measured AS (
          SELECT 'fiscal_radar' AS source, comparison_date AS day, anp_corrigido AS fiscal_m3, NULL AS anp_m3, NULL AS mpfm_t
          FROM painel_operador_comparisons
          UNION ALL
          SELECT 'anp_export', reference_date, NULL,
                 CASE WHEN record_kind IN ('linear_oil','linear_gas','differential_gas') THEN volume_corrigido ELSE NULL END,
                 NULL
          FROM painel_operador_anp_export_rows
          UNION ALL
          SELECT 'mpfm_daily', day_ref, NULL, NULL,
                 CASE WHEN metric_name='MPFM corr HC (t)' THEN metric_value ELSE NULL END
          FROM measurements_curated
          WHERE row_kind='daily' AND COALESCE(is_official,1)=1
        )
        SELECT source, COUNT(*), COUNT(DISTINCT day), MIN(day), MAX(day),
               SUM(COALESCE(fiscal_m3,0)), SUM(COALESCE(anp_m3,0)), SUM(COALESCE(mpfm_t,0))
        FROM measured
        GROUP BY source
        ORDER BY source
        """
    ).fetchall()
    for row in rows:
        lines.append(f"Dados medidos fonte={row[0]}: linhas={row[1]}; dias={row[2]}; período={row[3] or 'n/d'} a {row[4] or 'n/d'}; fiscal_m3={row[5] or 0:.3f}; anp_m3={row[6] or 0:.3f}; mpfm_hc_t={row[7] or 0:.3f}.")
    lines.append("Observação: a apuração diária mostra cobertura e valores por fonte; status Completo/Parcial/Atenção não é fechamento regulatório definitivo.")
    return lines


def _latest_import_run_id(conn) -> int:
    if not _table_exists(conn, "painel_operador_daily_checklist_runs"):
        return 0
    return int(_scalar(conn, "SELECT MAX(id) FROM painel_operador_daily_checklist_runs") or 0)


def _run_where(latest_run_id: int, prefix: str = "WHERE") -> tuple[str, tuple[Any, ...]]:
    if not latest_run_id:
        return "", ()
    return f" {prefix} import_run_id=?", (latest_run_id,)


def _tool_painel_operador_operational_blocks(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: painel_operador_operational_blocks]"]
    latest_run_id = _latest_import_run_id(conn)
    if latest_run_id:
        run = conn.execute(
            """
            SELECT id, source_file, imported_at, selected_sheet_count, row_count
            FROM painel_operador_daily_checklist_runs
            WHERE id=?
            """,
            (latest_run_id,),
        ).fetchone()
        if run:
            lines.append(
                f"Último Checklist Diário importado: run #{run[0]} em {run[2]}; abas selecionadas={run[3]}; linhas={run[4]}; arquivo={_safe_text(run[1], 110)}."
            )
    else:
        lines.append("Checklist Diário ainda sem importação registrada nas tabelas painel_operador_daily_checklist_*.")

    if _table_exists(conn, "painel_operador_daily_checklist_rows"):
        run_where, run_params = _run_where(latest_run_id, "WHERE")
        month_clause = ""
        month_params: tuple[Any, ...] = ()
        if month:
            month_clause = (" AND " if run_where else " WHERE ") + "substr(record_date,1,7)=?"
            month_params = (month[:7],)
        rows = conn.execute(
            f"""
            SELECT sheet_name, record_domain, COUNT(*) AS n,
                   SUM(CASE WHEN COALESCE(status,'')<>'' AND LOWER(status) NOT IN ('ok','concluído','concluido') THEN 1 ELSE 0 END) AS attention_n,
                   MIN(record_date), MAX(record_date)
            FROM painel_operador_daily_checklist_rows
            {run_where}{month_clause}
            GROUP BY sheet_name, record_domain
            ORDER BY n DESC, sheet_name
            LIMIT 14
            """,
            (*run_params, *month_params),
        ).fetchall()
        if rows:
            lines.append(f"Checklist Diário por aba/domínio ({_period_label(month)}; {'último run' if latest_run_id else 'todos os runs'}):")
            for row in rows:
                lines.append(f"{row[0]} / {row[1] or 'n/d'}: {row[2]} linhas; atenção={row[3] or 0}; período={row[4] or 'n/d'} a {row[5] or 'n/d'}.")

    if (
        _table_exists(conn, "painel_operador_comparisons")
        and _table_exists(conn, "painel_operador_anp_export_rows")
        and _table_exists(conn, "painel_operador_calendar_days")
        and _table_exists(conn, "measurements_curated")
    ):
        month_comp_clause = "WHERE substr(day,1,7)=?" if month else ""
        month_params = (month[:7],) if month else ()
        closing_rows = conn.execute(
            f"""
            WITH days AS (
              SELECT comparison_date AS day FROM painel_operador_comparisons WHERE COALESCE(comparison_date,'')<>''
              UNION
              SELECT reference_date AS day FROM painel_operador_anp_export_rows WHERE COALESCE(reference_date,'')<>''
              UNION
              SELECT day_ref AS day FROM measurements_curated WHERE row_kind='daily' AND COALESCE(day_ref,'')<>''
            ),
            fiscal AS (
              SELECT comparison_date AS day, COUNT(*) AS rows_n, COUNT(DISTINCT tag) AS tags_n,
                     SUM(COALESCE(anp_corrigido,0)) AS fiscal_m3,
                     SUM(CASE WHEN status<>'' AND status<>'ok' THEN 1 ELSE 0 END) AS attention_n
              FROM painel_operador_comparisons
              GROUP BY comparison_date
            ),
            anp AS (
              SELECT reference_date AS day, COUNT(*) AS rows_n, COUNT(DISTINCT tag) AS tags_n,
                     SUM(CASE WHEN record_kind IN ('linear_oil','linear_gas','differential_gas') THEN COALESCE(volume_corrigido,0) ELSE 0 END) AS anp_m3
              FROM painel_operador_anp_export_rows
              GROUP BY reference_date
            ),
            mpfm AS (
              SELECT day_ref AS day, COUNT(*) AS rows_n, COUNT(DISTINCT tag) AS tags_n,
                     SUM(CASE WHEN metric_name='MPFM corr HC (t)' THEN COALESCE(metric_value,0) ELSE 0 END) AS mpfm_hc_t
              FROM measurements_curated
              WHERE row_kind='daily' AND COALESCE(is_official,1)=1
              GROUP BY day_ref
            ),
            pend AS (
              SELECT calendar_date AS day, SUM(COALESCE(open_pending_count,0)) AS open_pending_n
              FROM painel_operador_calendar_days
              GROUP BY calendar_date
            )
            SELECT days.day,
                   COALESCE(fiscal.fiscal_m3,0) AS fiscal_m3,
                   COALESCE(anp.anp_m3,0) AS anp_m3,
                   COALESCE(mpfm.mpfm_hc_t,0) AS mpfm_hc_t,
                   COALESCE(fiscal.tags_n,0) AS fiscal_tags,
                   COALESCE(anp.tags_n,0) AS anp_tags,
                   COALESCE(mpfm.tags_n,0) AS mpfm_tags,
                   COALESCE(fiscal.attention_n,0) AS fiscal_attention,
                   COALESCE(pend.open_pending_n,0) AS open_pending
            FROM days
            LEFT JOIN fiscal ON fiscal.day=days.day
            LEFT JOIN anp ON anp.day=days.day
            LEFT JOIN mpfm ON mpfm.day=days.day
            LEFT JOIN pend ON pend.day=days.day
            {month_comp_clause}
            ORDER BY days.day DESC
            LIMIT 10
            """,
            month_params,
        ).fetchall()
        if closing_rows:
            lines.append(f"Fechamento diário consolidado ({_period_label(month)}; dias mais recentes):")
            for row in closing_rows:
                coverage = []
                if row[1]:
                    coverage.append("Fiscal/Radar")
                if row[2]:
                    coverage.append("Export ANP")
                if row[3]:
                    coverage.append("MPFM")
                lines.append(
                    f"{row[0]}: fontes={','.join(coverage) or 'sem volume'}; fiscal_m3={row[1]:.3f}; anp_m3={row[2]:.3f}; "
                    f"mpfm_hc_t={row[3]:.3f}; tags fiscal/anp/mpfm={row[4]}/{row[5]}/{row[6]}; "
                    f"atenções_fiscal={row[7]}; pendências_abertas={row[8]}."
                )

    if _table_exists(conn, "painel_operador_tank_balance"):
        run_where, run_params = _run_where(latest_run_id, "WHERE")
        month_clause = (" AND substr(tank_date,1,7)=?" if month and run_where else " WHERE substr(tank_date,1,7)=?" if month else "")
        month_params = (month[:7],) if month else ()
        row = conn.execute(
            f"""
            SELECT COUNT(*), COUNT(DISTINCT tank_date), MIN(tank_date), MAX(tank_date),
                   SUM(COALESCE(delta_tank_m3,0)),
                   SUM(COALESCE(fiscal_meter_gsv_m3,0)),
                   SUM(COALESCE(fiscal_minus_tank_m3,0)),
                   MAX(ABS(COALESCE(delta_percent,0))),
                   SUM(CASE WHEN status='ok' THEN 0 ELSE 1 END)
            FROM painel_operador_tank_balance
            {run_where}{month_clause}
            """,
            (*run_params, *month_params),
        ).fetchone()
        if row and row[0]:
            lines.append(
                f"Tank ({_period_label(month)}): linhas={row[0]}; dias={row[1]}; período={row[2]} a {row[3]}; "
                f"delta_tanque_m3={row[4] or 0:.3f}; fiscal_meter_gsv_m3={row[5] or 0:.3f}; fiscal_menos_tanque_m3={row[6] or 0:.3f}; "
                f"maior_delta_pct_abs={row[7] or 0:.3f}; atenções={row[8] or 0}."
            )
            samples = conn.execute(
                f"""
                SELECT tank_date, fiscal_meter_gsv_m3, delta_tank_m3, fiscal_minus_tank_m3, delta_percent, status, measurement_failure, observations
                FROM painel_operador_tank_balance
                {run_where}{month_clause}
                ORDER BY tank_date DESC, row_number DESC
                LIMIT 5
                """,
                (*run_params, *month_params),
            ).fetchall()
            for item in samples:
                lines.append(f"Tank amostra {item[0]}: fiscal={item[1]} m3; delta_tank={item[2]} m3; fiscal-tanque={item[3]} m3; delta%={item[4]}; status={item[5]}; falha={_safe_text(item[6], 50)}; obs={_safe_text(item[7], 90)}.")

    if _table_exists(conn, "painel_operador_offspec_tank"):
        run_where, run_params = _run_where(latest_run_id, "WHERE")
        month_clause = (" AND substr(offspec_date,1,7)=?" if month and run_where else " WHERE substr(offspec_date,1,7)=?" if month else "")
        month_params = (month[:7],) if month else ()
        row = conn.execute(
            f"""
            SELECT COUNT(*), COUNT(DISTINCT offspec_date), MIN(offspec_date), MAX(offspec_date),
                   SUM(COALESCE(delta_tank_m3,0)),
                   SUM(COALESCE(directed_volume_m3,0)),
                   SUM(COALESCE(reprocessed_volume_m3,0)),
                   SUM(CASE WHEN status='offspec' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='reprocesso' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='pendente' THEN 1 ELSE 0 END)
            FROM painel_operador_offspec_tank
            {run_where}{month_clause}
            """,
            (*run_params, *month_params),
        ).fetchone()
        if row and row[0]:
            lines.append(
                f"Off Spec Tank ({_period_label(month)}): linhas={row[0]}; dias={row[1]}; período={row[2]} a {row[3]}; "
                f"delta_tank_m3={row[4] or 0:.3f}; enviado_offspec_m3={row[5] or 0:.3f}; reprocessado_m3={row[6] or 0:.3f}; "
                f"dias_offspec={row[7] or 0}; dias_reprocesso={row[8] or 0}; pendentes={row[9] or 0}."
            )

    if _table_exists(conn, "painel_operador_gas_balance"):
        run_where, run_params = _run_where(latest_run_id, "WHERE")
        month_clause = (" AND substr(gas_date,1,7)=?" if month and run_where else " WHERE substr(gas_date,1,7)=?" if month else "")
        month_params = (month[:7],) if month else ()
        row = conn.execute(
            f"""
            SELECT COUNT(*), COUNT(DISTINCT gas_date), MIN(gas_date), MAX(gas_date),
                   SUM(COALESCE(operational_total_mm3,0)),
                   SUM(COALESCE(fiscal_injection_total_mm3,0)),
                   SUM(COALESCE(delta_mm3,0)),
                   MAX(ABS(COALESCE(delta_percent,0))),
                   SUM(CASE WHEN status='ok' THEN 0 ELSE 1 END),
                   SUM(COALESCE(hp_flare_mm3,0)),
                   SUM(COALESCE(lp_flare_mm3,0)),
                   SUM(COALESCE(vent_tank_mm3,0))
            FROM painel_operador_gas_balance
            {run_where}{month_clause}
            """,
            (*run_params, *month_params),
        ).fetchone()
        if row and row[0]:
            lines.append(
                f"Balanço de Gás ({_period_label(month)}): linhas={row[0]}; dias={row[1]}; período={row[2]} a {row[3]}; "
                f"operacional_total_MM3={row[4] or 0:.6f}; fiscal_injecao_total_MM3={row[5] or 0:.6f}; delta_MM3={row[6] or 0:.6f}; "
                f"maior_delta_pct_abs={row[7] or 0:.3f}; atenções={row[8] or 0}; HP_flare={row[9] or 0:.6f}; LP_flare={row[10] or 0:.6f}; vent_tank={row[11] or 0:.6f}."
            )
            samples = conn.execute(
                f"""
                SELECT gas_date, operational_total_mm3, fiscal_injection_total_mm3, delta_mm3, delta_percent, status, comment
                FROM painel_operador_gas_balance
                {run_where}{month_clause}
                ORDER BY gas_date DESC, row_number DESC
                LIMIT 5
                """,
                (*run_params, *month_params),
            ).fetchall()
            for item in samples:
                lines.append(f"Gás amostra {item[0]}: operacional={item[1]} MM3; fiscal_inj={item[2]} MM3; delta={item[3]} MM3; delta%={item[4]}; status={item[5]}; comentário={_safe_text(item[6], 90)}.")

    if _table_exists(conn, "painel_operador_mpfm_fiscal_oil"):
        run_where, run_params = _run_where(latest_run_id, "WHERE")
        month_clause = (" AND substr(production_date,1,7)=?" if month and run_where else " WHERE substr(production_date,1,7)=?" if month else "")
        month_params = (month[:7],) if month else ()
        row = conn.execute(
            f"""
            SELECT COUNT(*), COUNT(DISTINCT production_date), MIN(production_date), MAX(production_date),
                   SUM(COALESCE(total_mpfm_oil_m3,0)), SUM(COALESCE(fiscal_oil_m3,0)),
                   MAX(ABS(COALESCE(variance_percent,0))),
                   SUM(CASE WHEN status='ok' THEN 0 ELSE 1 END)
            FROM painel_operador_mpfm_fiscal_oil
            {run_where}{month_clause}
            """,
            (*run_params, *month_params),
        ).fetchone()
        if row and row[0]:
            lines.append(
                f"MPFM Subsea x Fiscal-Óleo ({_period_label(month)}): linhas={row[0]}; dias={row[1]}; período={row[2]} a {row[3]}; "
                f"mpfm_oil_m3={row[4] or 0:.3f}; fiscal_oil_m3={row[5] or 0:.3f}; maior_variância_pct_abs={row[6] or 0:.3f}; atenções={row[7] or 0}."
            )

    if _table_exists(conn, "painel_operador_measurement_limits"):
        rows = conn.execute(
            """
            SELECT metric_name, approval_status, source_type, COUNT(*) AS n,
                   MIN(valid_from), MAX(valid_from)
            FROM painel_operador_measurement_limits
            WHERE COALESCE(active,1)=1
            GROUP BY metric_name, approval_status, source_type
            ORDER BY n DESC, metric_name
            LIMIT 12
            """
        ).fetchall()
        if rows:
            lines.append("Limites/PAM parametrizados e monitores ativos:")
            for row in rows:
                lines.append(f"métrica={row[0] or 'n/d'} status={row[1] or 'n/d'} fonte={row[2] or 'n/d'}: {row[3]} limites; vigência início {row[4] or 'n/d'} a {row[5] or 'n/d'}.")

    if _table_exists(conn, "painel_operador_cv_config_changes"):
        month_clause = "WHERE substr(current_date,1,7)=?" if month else ""
        month_params = (month[:7],) if month else ()
        rows = conn.execute(
            f"""
            SELECT current_date, flow_computer, tag, parameter_name, previous_value, current_value, severity
            FROM painel_operador_cv_config_changes
            {month_clause}
            ORDER BY current_date DESC, severity DESC, flow_computer, parameter_name
            LIMIT 12
            """,
            month_params,
        ).fetchall()
        lines.append(f"Mudanças CV retornadas ({_period_label(month)}): {len(rows)}.")
        for row in rows:
            lines.append(f"{row[0]} {row[1]}/{row[2]} {row[3]}: {row[4]} -> {row[5]} [{row[6]}].")

    lines.append("Regras de resposta: para fechamento diário, explique cobertura por fonte antes de concluir; para Tank/Off Spec/Gás, informe unidades; para Limites/CV, diferencie parâmetro aprovado, snapshot lido e mudança detectada.")
    return lines


def _tool_sep_detail(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: sep_detail]"]
    table = "measurements_active" if _table_exists(conn, "measurements_active") else "measurements_curated"
    period_where, period_params = _month_where("day_ref", month, "AND")
    rows = conn.execute(
        f"""
        SELECT day_ref, hour_ref, row_kind, bank, tag, metric_name, metric_value, metric_unit, source_file
        FROM {table}
        WHERE (row_kind='sep' OR row_kind LIKE 'sep_%') AND is_official=1{period_where}
        ORDER BY day_ref DESC, COALESCE(hour_ref, 99) DESC, row_kind, metric_name
        LIMIT 36
        """,
        period_params,
    ).fetchall()
    range_row = conn.execute(
        f"SELECT MIN(day_ref), MAX(day_ref), COUNT(*) FROM {table} WHERE (row_kind='sep' OR row_kind LIKE 'sep_%') AND is_official=1{period_where}",
        period_params,
    ).fetchone()
    if range_row and range_row[2]:
        lines.append(f"Detalhes SEP em {table}: {_period_label(month)}; cobertura={range_row[0]} a {range_row[1]}; linhas disponíveis={range_row[2]}; amostra={len(rows)}.")
    else:
        lines.append(f"Detalhes SEP em {table}: {_period_label(month)}; amostra={len(rows)}.")
    for row in rows[:24]:
        hour = f" h={row[1]}" if row[1] is not None else ""
        lines.append(f"{row[0]}{hour} {row[2]} {row[5]}={row[6]} {row[7] or ''} | fonte={_safe_text(row[8], 70)}")
    if _table_exists(conn, "sep_source_files"):
        sep_period_where, sep_period_params = _month_where("production_date", month, "AND")
        source_rows = conn.execute(
            """
            SELECT production_date, fluid_kind, meter_id, location, source_file, is_official, resolution_status
            FROM sep_source_files
            WHERE is_active=1
              {sep_period_where}
            ORDER BY production_date DESC, fluid_kind
            LIMIT 18
            """.replace("{sep_period_where}", sep_period_where),
            sep_period_params,
        ).fetchall()
        lines.append(f"Arquivos fonte SEP retornados: {len(source_rows)}.")
        for row in source_rows:
            lines.append(f"{row[0]} {row[1]} meter={row[2]} local={_safe_text(row[3], 50)} oficial={row[5]} status={row[6]} arquivo={_safe_text(row[4], 80)}")
    if _table_exists(conn, "sep_alignments"):
        align_period_where, align_period_params = _month_where("production_date", month, "AND")
        align_rows = conn.execute(
            """
            SELECT production_date, bank, mpfm_tag, sep_meter_id, sep_tag, notes
            FROM sep_alignments
            WHERE is_active=1
              {align_period_where}
            ORDER BY production_date DESC, bank
            LIMIT 12
            """.replace("{align_period_where}", align_period_where),
            align_period_params,
        ).fetchall()
        for row in align_rows:
            lines.append(f"Alinhamento {row[0]} banco={row[1]} MPFM={row[2]} SEP meter={row[3]} tag={row[4]} notas={_safe_text(row[5], 80)}")
    return lines


def _tool_production_summary(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: production_summary]"]
    lines.append(f"Período analisado: {_period_label(month)}.")
    period_where, period_params = _month_where("day_ref", month, "AND")
    row = conn.execute(
        f"""
        SELECT COUNT(DISTINCT day_ref), COUNT(DISTINCT bank), COUNT(*)
        FROM measurements_curated
        WHERE is_official=1{period_where}
        """,
        period_params,
    ).fetchone()
    if row:
        lines.append(f"Dias com dados: {row[0]}; bancos: {row[1]}; linhas curadas oficiais: {row[2]}.")
    rows = conn.execute(
           f"""
        SELECT bank,
             SUM(CASE WHEN row_kind='daily' AND lower(metric_name) LIKE '%leo%' THEN metric_value ELSE 0 END) AS oil_t,
             SUM(CASE WHEN row_kind='daily' AND (lower(metric_name) LIKE '%gas%' OR metric_name LIKE '%Gás%' OR metric_name LIKE 'MPFM corr G%') THEN metric_value ELSE 0 END) AS gas_t,
             SUM(CASE WHEN row_kind='daily' AND lower(metric_name) LIKE '%gua%' THEN metric_value ELSE 0 END) AS water_t,
             SUM(CASE WHEN row_kind='daily' AND metric_name LIKE '%HC%' THEN metric_value ELSE 0 END) AS hc_t
        FROM measurements_curated
           WHERE row_kind='daily' AND is_official=1 AND COALESCE(bank,'')<>''{period_where}
        GROUP BY bank
        ORDER BY bank
        LIMIT 12
        """,
           period_params,
    ).fetchall()
    for row in rows:
        lines.append(f"Banco {row[0]}: óleo={row[1] or 0:.1f}t; gás={row[2] or 0:.1f}t; água={row[3] or 0:.1f}t; HC={row[4] or 0:.1f}t.")
    return lines


def _tool_alarm_summary(conn) -> list[str]:
    lines = ["\n[tool: alarm_summary]"]
    total = _scalar(conn, "SELECT COUNT(*) FROM alarm_records WHERE active=1") or 0
    lines.append(f"Total ativo no módulo de alarmes: {total}.")
    rows = conn.execute(
        """
        SELECT source_kind, COUNT(*) AS total,
               SUM(CASE WHEN status_code NOT IN ('closed','cancelled') THEN 1 ELSE 0 END) AS open_n
        FROM alarm_records
        WHERE active=1
        GROUP BY source_kind
        ORDER BY total DESC
        """
    ).fetchall()
    for row in rows:
        lines.append(f"Origem {row[0] or 'n/d'}: {row[1]} ativos; {row[2] or 0} em aberto.")
    pdf = conn.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN record_type='event' THEN 1 ELSE 0 END) AS events,
               SUM(CASE WHEN record_type='incident' THEN 1 ELSE 0 END) AS incidents,
               SUM(CASE WHEN status_code NOT IN ('closed','cancelled') THEN 1 ELSE 0 END) AS open_n,
               SUM(CASE WHEN status_code='closed' THEN 1 ELSE 0 END) AS closed_n,
               MIN(production_date), MAX(production_date)
        FROM alarm_records
        WHERE active=1 AND source_kind='pdf'
        """
    ).fetchone()
    if pdf and pdf[0]:
        lines.append(
            f"Carga PDF FCS320 consolidada: {pdf[0]} registros; {pdf[1]} eventos; {pdf[2]} incidentes; "
            f"{pdf[4]} fechados; {pdf[3]} em aberto; período {pdf[5]} a {pdf[6]}."
        )
    rows = conn.execute(
        """
        SELECT record_type, status_code, severity_code, priority_code, COUNT(*)
        FROM alarm_records
        WHERE active=1 AND source_kind='pdf'
        GROUP BY record_type, status_code, severity_code, priority_code
        ORDER BY record_type, status_code, severity_code, priority_code
        LIMIT 20
        """
    ).fetchall()
    for row in rows:
        lines.append(f"PDF {row[0]} status={row[1]} severidade={row[2]} prioridade={row[3]}: {row[4]}.")
    return lines


def _tool_open_alarms(conn, words: set[str]) -> list[str]:
    lines = ["\n[tool: open_alarms]"]
    severity_filter = "critical" if {"critico", "crítico", "critical"} & words else ""
    wants_workbook = bool({"workbook", "planilha", "excel", "origem"} & words)
    params: list[Any] = []
    where = "active=1 AND status_code NOT IN ('closed','cancelled')"
    if wants_workbook:
        where += " AND source_kind<>'pdf'"
    if severity_filter:
        where += " AND severity_code=?"
        params.append(severity_filter)
    rows = conn.execute(
        f"""
        SELECT id, source_kind, record_type, production_date, event_at, measurement_point, tag, title,
               severity_code, priority_code, status_code, occurrence_count
        FROM alarm_records
        WHERE {where}
        ORDER BY production_date DESC, event_at DESC, id DESC
        LIMIT 20
        """,
        tuple(params),
    ).fetchall()
    lines.append(f"Alarmes abertos retornados: {len(rows)}; filtro origem={'workbook/importada' if wants_workbook else 'todas'}.")
    for row in rows:
        point = row[5] or row[6] or "ponto n/d"
        lines.append(f"#{row[0]} origem={row[1]} {row[2]} {row[3]} {row[4]} {point} - {row[7]} [{row[8]}/{row[9]}/{row[10]}] ocorrências={row[11] or 0}.")
    return lines


def _tool_alarm_resolution_history(conn) -> list[str]:
    lines = ["\n[tool: alarm_resolution_history]"]
    if not _table_exists(conn, "alarm_actions"):
        lines.append("Tabela alarm_actions não disponível.")
        return lines
    action_rows = conn.execute(
        """
        SELECT a.id, a.alarm_id, r.source_kind, r.title, a.action_type, a.description, a.owner,
               a.status_code, a.due_date, a.completion_date, a.effectiveness, a.updated_at
        FROM alarm_actions a
        LEFT JOIN alarm_records r ON r.id=a.alarm_id
        WHERE a.active=1
        ORDER BY COALESCE(a.updated_at, a.created_at) DESC, a.id DESC
        LIMIT 18
        """
    ).fetchall()
    lines.append(f"Ações/resoluções de alarmes retornadas: {len(action_rows)}.")
    for row in action_rows:
        lines.append(f"ação #{row[0]} alarme #{row[1]} origem={row[2] or 'n/d'} tipo={row[4]} status={row[7]} dono={row[6] or 'n/d'} venc={row[8] or 'n/d'} concluído={row[9] or 'n/d'} | {row[5]} | alarme={_safe_text(row[3], 70)}")
    if _table_exists(conn, "alarm_audit_log"):
        audit_rows = conn.execute(
            """
            SELECT id, alarm_id, action_id, event_type, field_name, old_value, new_value, notes, created_at
            FROM alarm_audit_log
            ORDER BY created_at DESC, id DESC
            LIMIT 18
            """
        ).fetchall()
        lines.append(f"Eventos de auditoria recentes de alarmes: {len(audit_rows)}.")
        for row in audit_rows:
            lines.append(f"audit #{row[0]} alarme={row[1] or '-'} ação={row[2] or '-'} {row[8]} {row[3]} campo={row[4] or '-'} {row[5] or ''}->{row[6] or ''} notas={_safe_text(row[7], 90)}")
    return lines


def _tool_deadlines(conn) -> list[str]:
    lines = ["\n[tool: deadlines]"]
    try:
        rows = conn.execute(
            """
            SELECT id, subject, category, start_date, due_date, periodicity, periodicity_days, notes
            FROM deadline_items
            WHERE is_active=1
            ORDER BY CASE WHEN COALESCE(due_date,'')='' THEN '9999-12-31' ELSE due_date END, id
            LIMIT 30
            """
        ).fetchall()
    except Exception:
        lines.append("Tabela de prazos não disponível.")
        return lines
    today = date.today().isoformat()
    overdue = [row for row in rows if row[4] and row[4] < today]
    lines.append(f"Prazos ativos: {len(rows)}; vencidos pela data local {today}: {len(overdue)}.")
    for row in rows[:16]:
        status = "vencido" if row[4] and row[4] < today else "em aberto"
        lines.append(f"#{row[0]} {row[1]} | categoria={row[2] or 'n/d'} | vencimento={row[4] or 'n/d'} | {status} | periodicidade={row[5] or 'custom'} {row[6] or ''} | notas={_safe_text(row[7], 120)}.")
    return lines


def _tool_deadline_history(conn) -> list[str]:
    lines = ["\n[tool: deadline_history]"]
    if not _table_exists(conn, "deadline_items"):
        lines.append("Tabela deadline_items não disponível.")
        return lines
    active = _scalar(conn, "SELECT COUNT(*) FROM deadline_items WHERE is_active=1") or 0
    inactive = _scalar(conn, "SELECT COUNT(*) FROM deadline_items WHERE COALESCE(is_active,1)=0") or 0
    lines.append(f"Prazos ativos={active}; concluídos/inativos registrados={inactive}.")
    rows = conn.execute(
        """
        SELECT id, subject, category, start_date, due_date, notes, is_active, updated_at
        FROM deadline_items
        ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
        LIMIT 16
        """
    ).fetchall()
    for row in rows:
        status = "ativo" if row[6] else "inativo/concluído"
        lines.append(f"#{row[0]} {row[1]} | {status} | categoria={row[2] or 'n/d'} | início={row[3] or 'n/d'} | venc={row[4] or 'n/d'} | notas/evidências={_safe_text(row[5], 120)}")
    lines.append("Observação: etapas, responsáveis e evidências só ficam disponíveis se registrados nos campos da tabela ou em módulos documentais importados.")
    return lines


def _tool_validation_issues(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: validation_issues]"]
    period_where, period_params = _month_where("day_ref", month, "WHERE")
    rows = conn.execute(
        f"""
        SELECT issue_type, severity, COUNT(*)
        FROM validation_issues
        {period_where}
        GROUP BY issue_type, severity
        ORDER BY COUNT(*) DESC
        LIMIT 16
        """,
        period_params,
    ).fetchall()
    if not rows:
        lines.append("Nenhuma issue encontrada para o filtro atual.")
        return lines
    for row in rows:
        lines.append(f"{row[0]} | {row[1]}: {row[2]}.")
    return lines


def _tool_validation_issue_details(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: validation_issue_details]"]
    period_where, period_params = _month_where("day_ref", month, "WHERE")
    rows = conn.execute(
        f"""
        SELECT id, run_id, excel_file, issue_type, severity, ref_key, day_ref, details, created_at
        FROM validation_issues
        {period_where}
        ORDER BY created_at DESC, id DESC
        LIMIT 24
        """,
        period_params,
    ).fetchall()
    lines.append(f"Detalhes de issues retornados ({_period_label(month)}): {len(rows)}.")
    for row in rows:
        lines.append(f"issue #{row[0]} run={row[1]} {row[6] or ''} {row[3]}/{row[4]} ref={_safe_text(row[5], 80)} arquivo={_safe_text(row[2], 70)} detalhes={_safe_text(row[7], 180)}")
    if _table_exists(conn, "parsing_events_raw"):
        events = conn.execute(
            """
            SELECT e.id, e.run_id, f.filename, e.parser_name, e.parser_stage, e.status, e.details_json, e.created_at
            FROM parsing_events_raw e
            LEFT JOIN source_files_raw f ON f.id=e.source_file_raw_id
            WHERE e.status IN ('error','warn','ignored')
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT 18
            """
        ).fetchall()
        lines.append(f"Eventos de parsing recentes com atenção: {len(events)}.")
        for row in events:
            lines.append(f"event #{row[0]} run={row[1]} arquivo={_safe_text(row[2], 80)} parser={row[3]}/{row[4]} status={row[5]} detalhes={_safe_text(row[6], 180)}")
    return lines


def _tool_asset_register(conn) -> list[str]:
    lines = ["\n[tool: asset_register]"]
    if _table_exists(conn, "well_catalog_042"):
        rows = conn.execute(
            """
            SELECT well_operator_name, well_anp_name, cod_cadastro_poco, subsea_tag, cod_campo, campo, cod_instalacao, instalacao
            FROM well_catalog_042
            WHERE active=1
            ORDER BY subsea_tag, well_operator_name
            LIMIT 24
            """
        ).fetchall()
        lines.append(f"Poços/tags no well_catalog_042: {len(rows)} amostras.")
        for row in rows:
            lines.append(f"poço={row[0]} ANP={row[1]} cadastro={row[2]} tag_subsea={row[3]} campo={row[5] or row[4]} instalação={row[7] or row[6]}")
    if _table_exists(conn, "pvt_params"):
        rows = conn.execute(
            """
            SELECT id, bank, tag, fe, rs, rho_oleo_std, rho_gas_std, rho_agua_std, valid_from, valid_to, source, author, notes
            FROM pvt_params
            ORDER BY COALESCE(valid_from,'' ) DESC, id DESC
            LIMIT 18
            """
        ).fetchall()
        lines.append(f"Configurações/PVT MPFM retornadas: {len(rows)}.")
        for row in rows:
            lines.append(f"PVT #{row[0]} banco={row[1]} tag={row[2]} FE={row[3]} RS={row[4]} rho_oil={row[5]} rho_gas={row[6]} rho_water={row[7]} vigência={row[8] or 'n/d'}->{row[9] or 'aberta'} fonte={_safe_text(row[10], 80)} notas={_safe_text(row[12], 90)}")
    if _table_exists(conn, "mpfm_monitoring_daily"):
        rows = conn.execute(
            """
            SELECT production_date, bank, tag, meter_type, instrument, loop, operation_mode, aligned_separator_test, event_status, observations
            FROM mpfm_monitoring_daily
            ORDER BY production_date DESC, bank, tag
            LIMIT 18
            """
        ).fetchall()
        lines.append(f"Monitoramento/cadastro operacional MPFM retornado: {len(rows)}.")
        for row in rows:
            lines.append(f"{row[0]} banco={row[1]} tag={row[2]} tipo={row[3]} instr={row[4]} loop={row[5]} modo={row[6]} sep={row[7]} status_evento={row[8]} obs={_safe_text(row[9], 90)}")
    return lines


def _tool_recon_calibration(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: recon_calibration]"]
    period_where, period_params = _month_where("day_ref", month, "WHERE")
    if _table_exists(conn, "recon_runs"):
        rows = conn.execute(
            f"""
            SELECT id, run_at, bank, tag, day_ref, campaign_id, campaign_phase, cobertura_pct,
                   status_linha, status_standard, status_final, author, notes, test_window_json, resumo_json
            FROM recon_runs
            {period_where}
            ORDER BY run_at DESC, id DESC
            LIMIT 18
            """,
            period_params,
        ).fetchall()
        lines.append(f"Execuções de reconciliação retornadas ({_period_label(month)}): {len(rows)}.")
        for row in rows:
            lines.append(f"recon #{row[0]} {row[4]} banco={row[2]} tag={row[3]} campanha={row[5] or '-'} fase={row[6]} cobertura={row[7]} status={row[10] or row[8] or row[9]} autor={row[11] or 'n/d'} janela={_safe_text(row[13], 100)} resumo={_safe_text(row[14], 160)}")
    if _table_exists(conn, "recon_campaigns"):
        rows = conn.execute(
            """
            SELECT id, bank, tag, baseline_day_ref, post_day_ref, proposal_status, proposed_k_factor_selected,
                   applied_k_factor, applied_at, baseline_desvio_hc_pct, baseline_desvio_total_pct,
                   post_desvio_hc_pct, post_desvio_total_pct, monitoring_status, author, notes
            FROM recon_campaigns
            ORDER BY updated_at DESC, id DESC
            LIMIT 16
            """
        ).fetchall()
        lines.append(f"Campanhas de reconciliação/calibração retornadas: {len(rows)}.")
        for row in rows:
            lines.append(f"campanha #{row[0]} banco={row[1]} tag={row[2]} baseline={row[3]} pós={row[4] or '-'} proposta={row[5]} k_proposto={row[6]} k_aplicado={row[7]} aplicado_em={row[8] or '-'} desvios HC {row[9]}->{row[11]} total {row[10]}->{row[12]} status={row[13]} notas={_safe_text(row[15], 90)}")
    return lines


def _tool_import_traceability(conn, month: str = "") -> list[str]:
    lines = ["\n[tool: import_traceability]"]
    runs = conn.execute(
        """
        SELECT id, started_at, finished_at, source_type, source_ref, files_count, status, notes_json
        FROM processing_runs
        ORDER BY started_at DESC, id DESC
        LIMIT 12
        """
    ).fetchall()
    lines.append(f"Processamentos recentes retornados: {len(runs)}.")
    for row in runs:
        lines.append(f"run #{row[0]} {row[1]} status={row[6]} fonte={row[3]} ref={_safe_text(row[4], 90)} arquivos={row[5]} notas={_safe_text(row[7], 120)}")
    if _table_exists(conn, "files_imported"):
        period_where, period_params = _month_where("content_date", month, "WHERE")
        rows = conn.execute(
            f"""
            SELECT id, run_id, filename, ext, file_type, unit_code, meter_id, content_date, processed_ok, message
            FROM files_imported
            {period_where}
            ORDER BY id DESC
            LIMIT 18
            """,
            period_params,
        ).fetchall()
        lines.append(f"Arquivos importados retornados ({_period_label(month)}): {len(rows)}.")
        for row in rows:
            lines.append(f"file #{row[0]} run={row[1]} {row[7]} {row[4]} unit={row[5]} meter={row[6]} ok={row[8]} nome={_safe_text(row[2], 80)} msg={_safe_text(row[9], 90)}")
    return lines


def _tool_ai_action_capabilities(conn) -> list[str]:
    lines = ["\n[tool: ai_action_capabilities]"]
    lines.append("Capacidade operacional atual: visualização read-only sem restrição automática de período e geração de propostas; alterações em alarmes, prazos, medições ou atividades exigem aprovação humana explícita na área do Assistente IA.")
    lines.append("Uma aprovação autoriza somente o item, alvo e escopo descritos na proposta aprovada; qualquer outro item exige nova proposta e nova aprovação.")
    if _table_exists(conn, "ai_action_requests"):
        rows = conn.execute(
            """
            SELECT status, target_area, COUNT(*)
            FROM ai_action_requests
            GROUP BY status, target_area
            ORDER BY status, target_area
            """
        ).fetchall()
        if rows:
            for row in rows:
                lines.append(f"Propostas IA status={row[0]} área={row[1]}: {row[2]}.")
        else:
            lines.append("Não há propostas de ação da IA registradas.")
    return lines


def _tool_external_integrations(conn) -> list[str]:
    lines = ["\n[tool: external_integrations]"]
    lines.append("CMMS/manutenção: sem conector direto identificado; só responder se houver dados importados em alarmes, ações, notas, documentos ou registros SGM-FM.")
    lines.append("Relatórios regulatórios/ANP: usar XML042, well_catalog_042, xml042_documents/xml042_imported_* quando a pergunta for sobre 042; outros sistemas externos não estão conectados diretamente.")
    lines.append("Alocação de produção: usar medições MPFM/SEP, reconciliação, XML042 e arquivos importados; se o usuário pedir sistema externo de alocação, informar limitação de integração.")
    return lines


def _tool_hourly_measurement_table(conn, table: str, filters: dict[str, str], month: str = "") -> list[str]:
    lines = ["\n[tabela: dados_horarios_mpfm]"]
    period_where, period_params = _month_where("day_ref", month, "AND")
    filter_where, filter_params = _measurement_filter_sql(filters, "AND")
    coverage = conn.execute(
        f"""
        SELECT MIN(day_ref), MAX(day_ref), COUNT(DISTINCT day_ref), COUNT(DISTINCT printf('%s|%s', bank, tag)), COUNT(*)
        FROM {table}
        WHERE row_kind='hourly' AND is_official=1{period_where}{filter_where}
        """,
        (*period_params, *filter_params),
    ).fetchone()
    if not coverage or not coverage[4]:
        lines.append("Não foram encontradas linhas horárias oficiais para o filtro solicitado.")
        return lines
    lines.append(
        f"Cobertura horária do filtro: {coverage[0]} a {coverage[1]}; dias={coverage[2]}; pontos={coverage[3]}; linhas longas={coverage[4]}."
    )
    metrics = [
        ("MPFM corr Óleo (t)", "oleo_t"),
        ("MPFM corr Gás (t)", "gas_t"),
        ("MPFM corr Água (t)", "agua_t"),
        ("MPFM corr HC (t)", "hc_t"),
        ("MPFM corr Total (t)", "total_t"),
        ("PVT @20 vol Óleo (m³)", "oleo_m3"),
        ("PVT @20 vol Gás (Sm³)", "gas_sm3"),
        ("PVT @20 vol Água (m³)", "agua_m3"),
        ("Pressão (barg)", "pressao_barg"),
        ("Temperatura (°C)", "temperatura_c"),
    ]
    select_metrics = ",\n               ".join(
        "MAX(CASE WHEN metric_name=? THEN metric_value END) AS " + alias
        for _, alias in metrics
    )
    rows = conn.execute(
        f"""
        SELECT day_ref, hour_ref, bank, tag,
               {select_metrics}
        FROM {table}
        WHERE row_kind='hourly' AND is_official=1{period_where}{filter_where}
        GROUP BY day_ref, hour_ref, bank, tag
        ORDER BY day_ref DESC, hour_ref DESC, bank, tag
        LIMIT 120
        """,
        (*(metric for metric, _ in metrics), *period_params, *filter_params),
    ).fetchall()
    lines.append(f"Linhas horárias pivotadas retornadas ao modelo: {len(rows)}. Se houver mais de 120 horas, esta tabela mostra as mais recentes e a cobertura acima informa o universo completo consultável.")
    lines.append("| Dia | Hora | Banco | TAG | Óleo t | Gás t | Água t | HC t | Total t | Óleo m3 | Gás Sm3 | Água m3 | Pressão barg | Temp C |")
    lines.append("| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in rows[:72]:
        values = [row[index] for index in range(4, 14)]
        formatted = ["" if value is None else f"{float(value):.4g}" for value in values]
        lines.append(
            f"| {row[0]} | {row[1]} | {row[2] or ''} | {row[3] or ''} | " + " | ".join(formatted) + " |"
        )
    return lines


def _tool_measurement_detail(conn, question: str, words: set[str], month: str = "") -> list[str]:
    lines = ["\n[tool: measurement_detail]"]
    table = "measurements_active" if _table_exists(conn, "measurements_active") else "measurements_curated"
    wants_hourly = _wants_any(words, {"hora", "horas", "hourly", "horário", "horários", "horario", "horarios", "horária", "horarias", "horárias"})
    wants_table = _wants_any(words, {"tabela", "tabular", "listar", "listagem", "mostrar", "gerar", "exibir"})
    wants_raw = _wants_any(words, {"bruto", "bruta", "raw", "sensor", "sensores", "pressão", "pressao", "temperatura", "densidade"})
    row_kinds = ("hourly",) if wants_hourly else ("daily", "hourly")
    placeholders = ",".join("?" for _ in row_kinds)
    period_where, period_params = _month_where("day_ref", month, "AND")
    filters = _detect_known_measurement_filters(conn, table, question)
    filter_where, filter_params = _measurement_filter_sql(filters, "AND")
    rows = conn.execute(
        f"""
        SELECT day_ref, hour_ref, row_kind, bank, tag, instrument, metric_name, metric_value, metric_unit, source_file
        FROM {table}
        WHERE row_kind IN ({placeholders}) AND is_official=1{period_where}{filter_where}
        ORDER BY day_ref DESC, COALESCE(hour_ref, 99) DESC, bank, tag, metric_name
        LIMIT 80
        """,
        (*row_kinds, *period_params, *filter_params),
    ).fetchall()
    range_row = conn.execute(
        f"SELECT MIN(day_ref), MAX(day_ref), COUNT(*) FROM {table} WHERE is_official=1{period_where}{filter_where}",
        (*period_params, *filter_params),
    ).fetchone()
    if range_row and range_row[2]:
        lines.append(f"Fonte consultada: {table}; {_period_label(month)}; cobertura={range_row[0]} a {range_row[1]}; linhas oficiais disponíveis={range_row[2]}.")
    if filters:
        lines.append("Filtro operacional detectado na pergunta: " + "; ".join(f"{key}={value}" for key, value in filters.items()) + ".")
    else:
        catalog_rows = conn.execute(
            f"""
            SELECT bank, tag, COUNT(DISTINCT day_ref) AS days, COUNT(*) AS rows_n
            FROM {table}
            WHERE row_kind IN ({placeholders}) AND is_official=1{period_where}
              AND COALESCE(bank,'')<>'' AND COALESCE(tag,'')<>''
            GROUP BY bank, tag
            ORDER BY rows_n DESC, bank, tag
            LIMIT 24
            """,
            (*row_kinds, *period_params),
        ).fetchall()
        if catalog_rows:
            lines.append("Pontos/Bancos/TAGs disponíveis para consulta ampla: " + "; ".join(f"{row[0]} {row[1]} ({row[2]} dias, {row[3]} linhas)" for row in catalog_rows) + ".")
    lines.append(f"Granularidade consultada={'hourly' if wants_hourly else 'daily/hourly'}; amostra retornada={len(rows)} linhas.")
    if wants_hourly and wants_table:
        lines.extend(_tool_hourly_measurement_table(conn, table, filters, month))
    for row in rows[:24]:
        hour = f" h={row[1]}" if row[1] is not None else ""
        lines.append(f"{row[0]}{hour} {row[2]} {row[3] or ''} {row[4] or ''} {row[6]}={row[7]} {row[8] or ''} | fonte={_safe_text(row[9], 70)}")
    if wants_raw and _table_exists(conn, "measurements_raw"):
        raw_period_where, raw_period_params = _month_where("content_date", month, "AND")
        raw_filter_where, raw_filter_params = _measurement_filter_sql(filters, "AND")
        raw_rows = conn.execute(
            """
            SELECT content_date, hour_ref, row_kind, bank, tag, instrument, metric_name, metric_value_raw, metric_unit_raw
            FROM measurements_raw
            WHERE (lower(metric_name) LIKE '%press%' OR lower(metric_name) LIKE '%temp%' OR lower(metric_name) LIKE '%dens%' OR lower(metric_name) LIKE '%pvt%')
              {raw_period_where}{raw_filter_where}
            ORDER BY content_date DESC, COALESCE(hour_ref, 99) DESC
            LIMIT 24
            """.replace("{raw_period_where}", raw_period_where).replace("{raw_filter_where}", raw_filter_where),
            (*raw_period_params, *raw_filter_params),
        ).fetchall()
        lines.append(f"Amostra de parâmetros brutos/sensores em measurements_raw ({_period_label(month)}): {len(raw_rows)} linhas.")
        for row in raw_rows:
            hour = f" h={row[1]}" if row[1] is not None else ""
            lines.append(f"raw {row[0]}{hour} {row[3] or ''} {row[4] or ''} {row[6]}={row[7]} {row[8] or ''}")
    return lines


def build_tool_context(db_conn, question: str, app_context: dict[str, Any] | None = None) -> str:
    """Runs read-only internal tools and returns a compact context block for the model."""
    words = _query_words(question)
    page = str((app_context or {}).get("current_page") or (app_context or {}).get("page") or "").lower()
    month = _explicit_month(question)

    wants_alarm = _wants_any(words, {"alarme", "alarmes", "fcs320", "alerta", "alertas", "evento", "eventos", "workbook", "resolucao", "resolução", "fechou", "fechado", "acao", "ação", "communication", "status"}) or page in {"alertas", "alarmes"}
    wants_deadline = _wants_any(words, {"prazo", "prazos", "atividade", "atividades", "vencido", "vencidos", "calibracao", "calibração", "pendencia", "pendência", "evidencia", "evidência", "documento", "documentos"}) or page == "prazos"
    wants_production = _wants_any(words, {"dados", "produção", "producao", "óleo", "oleo", "gas", "gás", "água", "agua", "mpfm", "sep", "separador", "banco", "bancos", "tag", "tags", "poço", "poco", "stream", "riser", "topside", "subsea", "hora", "horas", "horario", "horário", "diario", "diário", "densidade", "pressão", "pressao", "temperatura", "sensor", "sensores", "desvio", "tabela"}) or page in {"resumo", "mpfm", "separador", "monitoramento", "graficos"}
    wants_validation = _wants_any(words, {"validacao", "validação", "issue", "issues", "erro", "erros", "faltando", "duplicado", "duplicidade", "unknown_tag", "parsing", "causa"})
    wants_asset = _wants_any(words, {"ativo", "ativos", "asset", "cadastro", "register", "poço", "poco", "poços", "pocos", "riser", "stream", "mpfm", "calibração", "calibracao", "configuração", "configuracao", "modelo", "correlação", "correlacao"})
    wants_recon = _wants_any(words, {"reconciliacao", "reconciliação", "recon", "calibração", "calibracao", "k", "factor", "fator", "pvt", "desvio", "campanha", "certificado", "relatorio", "relatório"}) or page == "recon"
    wants_files = _wants_any(words, {"arquivo", "arquivos", "importação", "importacao", "origem", "fonte", "hash", "run", "processamento", "rastreabilidade"})
    wants_action = _wants_any(words, {"escrever", "alterar", "atualizar", "fechar", "registrar", "ação", "acao", "permissão", "permissao", "aprovar"})
    wants_external = _wants_any(words, {"cmms", "manutenção", "manutencao", "anp", "regulatório", "regulatorio", "alocação", "alocacao", "externo", "integração", "integracao"})
    wants_overview = _wants_any(words, {"aplicacao", "aplicação", "tudo", "todos", "todas", "ver", "acessar", "acesso", "enxerga", "existe", "existem", "status", "fonte", "fontes", "guia", "mapa"})
    wants_painel_operational = _wants_any(words, {"checklist", "diario", "diário", "fechamento", "apuracao", "apuração", "limite", "limites", "pam", "faixa", "cv", "parameters", "security", "configuração", "configuracao", "mudança", "mudancas", "mudanças", "gas", "gás", "balanço", "balanco", "tank", "tanque", "offspec", "off", "spec", "fiscal-óleo", "fiscal-oleo"})
    wants_painel = (
        _wants_any(words, {"painel", "operador", "radar", "anp", "fiscal", "xml", "apuração", "apuracao", "produção", "producao", "catalogado", "catalogados", "staging", "pendências", "pendencias"})
        or page == "painel-operador"
        or wants_painel_operational
    )

    selected_tools: list[str] = []
    if wants_overview:
        selected_tools.extend(["source_catalog", "app_overview"])
    if wants_painel or wants_overview:
        selected_tools.extend(["source_catalog", "painel_operador"])
    if wants_painel_operational or wants_overview or page == "painel-operador":
        selected_tools.append("painel_operador_operational_blocks")
    if wants_alarm or wants_overview:
        selected_tools.extend(["alarm_summary", "open_alarms", "alarm_resolution_history"])
    if wants_deadline or wants_overview:
        selected_tools.extend(["deadlines", "deadline_history"])
    if wants_production or wants_overview:
        selected_tools.extend(["production_summary", "measurement_detail", "sep_detail"])
    if wants_validation or wants_overview:
        selected_tools.extend(["validation_issues", "validation_issue_details"])
    if wants_asset or wants_overview:
        selected_tools.append("asset_register")
    if wants_recon or wants_overview:
        selected_tools.append("recon_calibration")
    if wants_files or wants_overview:
        selected_tools.append("import_traceability")
    if wants_action or wants_overview:
        selected_tools.append("ai_action_capabilities")
    if wants_external or wants_overview:
        selected_tools.append("external_integrations")
    if not selected_tools:
        selected_tools = ["source_catalog", "app_overview", "alarm_summary", "deadlines"]
    selected_tools = list(dict.fromkeys(selected_tools))

    lines = [
        "=== Ferramentas internas executadas ===",
        "As informações abaixo foram consultadas diretamente no banco SQLite da aplicação, em modo somente leitura.",
        "Acesso de leitura operacional: todos os bancos, TAGs, pontos e períodos disponíveis; filtros são aplicados somente quando aparecem no pedido do usuário.",
    ]
    lines.extend(_app_context_lines(app_context))

    conn = db_conn()
    try:
        conn.row_factory = None
        if "source_catalog" in selected_tools:
            lines.extend(_source_catalog_lines())
        if "app_overview" in selected_tools:
            lines.extend(_tool_app_overview(conn))
        if "painel_operador" in selected_tools:
            lines.extend(_tool_painel_operador(conn, month))
        if "painel_operador_operational_blocks" in selected_tools:
            lines.extend(_tool_painel_operador_operational_blocks(conn, month))
        if "production_summary" in selected_tools:
            lines.extend(_tool_production_summary(conn, month))
        if "measurement_detail" in selected_tools:
            lines.extend(_tool_measurement_detail(conn, question, words, month))
        if "sep_detail" in selected_tools:
            lines.extend(_tool_sep_detail(conn, month))
        if "alarm_summary" in selected_tools:
            lines.extend(_tool_alarm_summary(conn))
        if "open_alarms" in selected_tools:
            lines.extend(_tool_open_alarms(conn, words))
        if "alarm_resolution_history" in selected_tools:
            lines.extend(_tool_alarm_resolution_history(conn))
        if "deadlines" in selected_tools:
            lines.extend(_tool_deadlines(conn))
        if "deadline_history" in selected_tools:
            lines.extend(_tool_deadline_history(conn))
        if "validation_issues" in selected_tools:
            lines.extend(_tool_validation_issues(conn, month))
        if "validation_issue_details" in selected_tools:
            lines.extend(_tool_validation_issue_details(conn, month))
        if "asset_register" in selected_tools:
            lines.extend(_tool_asset_register(conn))
        if "recon_calibration" in selected_tools:
            lines.extend(_tool_recon_calibration(conn, month))
        if "import_traceability" in selected_tools:
            lines.extend(_tool_import_traceability(conn, month))
        if "ai_action_capabilities" in selected_tools:
            lines.extend(_tool_ai_action_capabilities(conn))
        if "external_integrations" in selected_tools:
            lines.extend(_tool_external_integrations(conn))
    finally:
        conn.close()
    return "\n".join(lines)
