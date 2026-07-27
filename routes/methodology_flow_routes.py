from __future__ import annotations

from datetime import datetime
import json
from typing import Any

from fastapi import HTTPException, Request


def _loads(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _round(value: Any, digits: int = 3):
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _fmt_metric(value: Any, unit: str = "", digits: int = 3) -> str:
    num = _round(value, digits)
    if num is None:
        return "-"
    text = f"{num:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} {unit}".strip()


def _status_kind(status: str) -> str:
    value = str(status or "").upper()
    if value in {"OK", "APPROVED", "ACEITO", "ACCEPTED"}:
        return "ok"
    if value in {"ATENCAO", "ATENÇÃO", "WARN", "WARNING"}:
        return "warn"
    if value in {"VERIFICAR", "REJECTED", "REJEITADO"}:
        return "err"
    return "info"


def _safe_pct(mpfm_value: Any, ref_value: Any):
    try:
        ref = float(ref_value)
        if ref == 0:
            return None
        return round((float(mpfm_value) / ref - 1.0) * 100.0, 4)
    except Exception:
        return None


def register_methodology_flow_routes(app, ctx: dict) -> None:
    db_conn = ctx["db_conn"]

    def _now() -> str:
        return datetime.now().replace(microsecond=0).isoformat()

    def _row_dict(row) -> dict:
        if not row:
            return {}
        data = dict(row)
        data["payload"] = _loads(data.get("payload_json"), {})
        return data

    def _ensure_flow_items_table(cur) -> None:
        cur.executescript(
            """
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
            """
        )

    def _flow_items(cur, run_id: int | None = None, item_type: str = "", status: str = "", limit: int = 80) -> list[dict]:
        _ensure_flow_items_table(cur)
        sql = "SELECT * FROM methodology_flow_items WHERE COALESCE(active,1)=1"
        params: list[Any] = []
        if run_id:
            sql += " AND run_id=?"
            params.append(int(run_id))
        if item_type:
            sql += " AND item_type=?"
            params.append(item_type)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(max(1, min(int(limit or 80), 200)))
        return [_row_dict(row) for row in cur.execute(sql, params).fetchall()]

    def _latest_run(cur, bank: str = "", tag: str = "", day_ref: str = ""):
        sql = "SELECT * FROM recon_runs WHERE 1=1"
        params: list[Any] = []
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        if day_ref:
            sql += " AND day_ref=?"
            params.append(day_ref)
        sql += " ORDER BY id DESC LIMIT 1"
        return cur.execute(sql, params).fetchone()

    def _run_list(cur, bank: str = "", tag: str = "", limit: int = 40):
        sql = """
            SELECT id, run_at, bank, tag, day_ref, campaign_id, campaign_phase,
                   horas_validas, cobertura_pct, status_final, notes
            FROM recon_runs
            WHERE 1=1
        """
        params: list[Any] = []
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in cur.execute(sql, params).fetchall()]

    def _daily_metrics(cur, run: dict) -> dict[str, dict]:
        rows = cur.execute(
            """
            SELECT metric_name, metric_value, metric_unit, source_file
            FROM measurements_curated
            WHERE row_kind='daily'
              AND day_ref=?
              AND bank=?
              AND (
                tag=?
                OR REPLACE(REPLACE(REPLACE(UPPER(COALESCE(tag,'')), ' ', ''), '-', ''), '_', '') =
                   REPLACE(REPLACE(REPLACE(UPPER(?), ' ', ''), '-', ''), '_', '')
              )
            ORDER BY metric_name
            """,
            (run["day_ref"], run["bank"], run["tag"], run["tag"]),
        ).fetchall()
        out: dict[str, dict] = {}
        for row in rows:
            out[row["metric_name"]] = {
                "value": row["metric_value"],
                "unit": row["metric_unit"],
                "source_file": row["source_file"],
            }
        return out

    def _sep_sources(cur, day_ref: str) -> list[dict]:
        return [
            dict(row)
            for row in cur.execute(
                """
                SELECT id, production_date, fluid_kind, meter_id, location, report_kind,
                       report_start, report_end, source_file, is_official, resolution_status
                FROM sep_source_files
                WHERE production_date=?
                ORDER BY fluid_kind, meter_id, source_file
                """,
                (day_ref,),
            ).fetchall()
        ]

    def _deadline_rows(cur, day_ref: str) -> list[dict]:
        month = str(day_ref or "")[:7]
        rows = cur.execute(
            """
            SELECT id, subject, category, start_date, due_date, periodicity, notes, icon, is_active
            FROM deadline_items
            WHERE COALESCE(is_active,1)=1
              AND (
                category IN ('Verificação','Investigação','Relatório','Contingência')
                OR subject LIKE '%MPFM%'
                OR subject LIKE '%PVT%'
                OR subject LIKE '%Recon%'
              )
            ORDER BY due_date, id
            LIMIT 12
            """
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["related_to_month"] = bool(month and (str(item.get("start_date") or "").startswith(month) or str(item.get("due_date") or "").startswith(month)))
            result.append(item)
        return result

    def _alarm_rows(cur, run: dict) -> list[dict]:
        try:
            return [
                dict(row)
                for row in cur.execute(
                    """
                    SELECT id, production_date, event_at, bank, tag, instrument,
                           severity_code, status_code, title, message
                    FROM alarm_records
                    WHERE production_date=?
                      AND (
                        COALESCE(bank,'') IN ('', ?)
                        OR COALESCE(tag,'')=?
                        OR COALESCE(instrument,'') LIKE ?
                      )
                    ORDER BY id DESC
                    LIMIT 8
                    """,
                    (run["day_ref"], run["bank"], run["tag"], f"%{run['tag']}%"),
                ).fetchall()
            ]
        except Exception:
            return []

    def _campaign(cur, campaign_id):
        if not campaign_id:
            return None
        row = cur.execute("SELECT * FROM recon_campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        for key in ("pvt_snapshot", "analytical_snapshot", "sep_alignment_snapshot", "applied_k_factors_json"):
            data[key] = _loads(data.get(key), {} if key.endswith("snapshot") else None)
        return data

    def _pvt(cur, pvt_id):
        if not pvt_id:
            return None
        row = cur.execute("SELECT * FROM pvt_params WHERE id=?", (pvt_id,)).fetchone()
        return dict(row) if row else None

    def _build_steps(run: dict, context: dict) -> list[dict]:
        resumo = context["resumo"] or {}
        pvt = context["pvt"] or context["pvt_snapshot"] or {}
        analytical = context["analytical_snapshot"] or {}
        daily = context["daily_metrics"] or {}
        campaign = context.get("campaign") or {}
        calc_horas = context.get("calc_horas") or []
        sep_sources = context.get("sep_sources") or []
        alarms = context.get("alarms") or []
        deadlines = context.get("deadlines") or []

        status_final = str(run.get("status_final") or resumo.get("status_final") or "")
        decision_kind = _status_kind(status_final)
        cobertura = run.get("cobertura_pct")
        horas_validas = run.get("horas_validas")
        qa_flags = resumo.get("qa_flags_consolidados") or []

        mpfm_hc = resumo.get("massa_hc_mpfm_t")
        ref_hc = resumo.get("massa_hc_ref_t")
        mpfm_total = resumo.get("massa_total_mpfm_t")
        ref_total = resumo.get("massa_total_ref_t")
        mpfm_agua = resumo.get("massa_agua_mpfm_t")
        ref_agua = resumo.get("massa_agua_ref_t")

        return [
            {
                "id": "calib",
                "num": "1",
                "title": "Calibracao e parametros PVT",
                "kind": "ok" if pvt else "warn",
                "summary": "Fonte versionada de FE, Rs, densidades standard, limites e condicao de referencia.",
                "metrics": [
                    {"label": "PVT", "value": f"#{pvt.get('id')}" if pvt.get("id") else "-"},
                    {"label": "Banco/TAG", "value": f"{run.get('bank','-')} / {run.get('tag','-')}"},
                    {"label": "Fonte", "value": pvt.get("source") or run.get("notes") or "-"},
                ],
                "evidence": [
                    "Tabela pvt_params",
                    f"Vigencia: {pvt.get('valid_from') or '-'} a {pvt.get('valid_to') or 'aberta'}",
                    f"Temp/pressao ref.: {_fmt_metric(pvt.get('temp_ref_c'), 'C', 1)} / {_fmt_metric(pvt.get('pres_ref_bar'), 'bar(a)', 5)}",
                ],
            },
            {
                "id": "comiss",
                "num": "2",
                "title": "Comissionamento e configuracao",
                "kind": "ok" if pvt.get("fe") and pvt.get("rs") else "warn",
                "summary": "Parametros usados para converter a referencia do separador para a mesma base de comparacao do MPFM.",
                "metrics": [
                    {"label": "SF/FE", "value": _fmt_metric(pvt.get("fe"), "", 6)},
                    {"label": "Delta Rs", "value": _fmt_metric(pvt.get("rs"), "Sm3/Sm3", 4)},
                    {"label": "GOR mode", "value": pvt.get("gor_mode") or "-"},
                    {"label": "GSV confirmado", "value": "Sim" if pvt.get("gsv_confirmed") else "Nao"},
                ],
                "evidence": [
                    f"rho oleo: {_fmt_metric(pvt.get('rho_oleo_std'), 'kg/m3', 2)}",
                    f"rho gas: {_fmt_metric(pvt.get('rho_gas_std'), 'kg/Sm3', 4)}",
                    f"rho agua: {_fmt_metric(pvt.get('rho_agua_std'), 'kg/m3', 2)}",
                ],
            },
            {
                "id": "op",
                "num": "3",
                "title": "Operacao continua MPFM",
                "kind": "ok" if daily else "warn",
                "summary": "Medições daily/hourly do MPFM carregadas da base curada para o periodo do run.",
                "metrics": [
                    {"label": "MPFM HC", "value": _fmt_metric((daily.get("MPFM corr HC (t)") or {}).get("value"), "t")},
                    {"label": "MPFM Total", "value": _fmt_metric((daily.get("MPFM corr Total (t)") or {}).get("value"), "t")},
                    {"label": "Pressao", "value": _fmt_metric((daily.get("Pressão (barg)") or {}).get("value"), "barg", 2)},
                    {"label": "Temperatura", "value": _fmt_metric((daily.get("Temperatura (°C)") or {}).get("value"), "C", 2)},
                ],
                "evidence": [
                    f"Dia: {run.get('day_ref')}",
                    f"Run: #{run.get('id')} ({run.get('campaign_phase') or 'baseline'})",
                    f"Fonte MPFM: {(next((m.get('source_file') for m in daily.values() if m.get('source_file')), '') or '-')}",
                ],
            },
            {
                "id": "verif",
                "num": "4",
                "title": "Verificacao MPFM x Separador",
                "kind": "ok" if calc_horas else "warn",
                "summary": "Balanço de massa por fase conforme memorial, com conversao PVT e comparacao por janela.",
                "metrics": [
                    {"label": "Cobertura", "value": _fmt_metric(cobertura, "%", 1)},
                    {"label": "Horas validas", "value": f"{horas_validas or 0}"},
                    {"label": "HC REF", "value": _fmt_metric(ref_hc, "t")},
                    {"label": "HC MPFM", "value": _fmt_metric(mpfm_hc, "t")},
                ],
                "evidence": [
                    f"Fontes SEP: {len(sep_sources)} arquivo(s)",
                    f"Janela: {analytical.get('window_start_at') or '-'} ate {analytical.get('window_end_at') or '-'}",
                    "Calculo backend: recon_engine.calcular_hora/calcular_24h",
                ],
            },
            {
                "id": "dec",
                "num": "5",
                "title": "Decisao tecnica",
                "kind": decision_kind,
                "summary": "Resultado consolidado considerando limites PVT, cobertura e flags de QA.",
                "metrics": [
                    {"label": "Status", "value": status_final or "-"},
                    {"label": "Desvio HC", "value": _fmt_metric(resumo.get("desvio_hc_pct") or _safe_pct(mpfm_hc, ref_hc), "%", 3)},
                    {"label": "Desvio Total", "value": _fmt_metric(resumo.get("desvio_total_pct") or _safe_pct(mpfm_total, ref_total), "%", 3)},
                    {"label": "Desvio Agua", "value": _fmt_metric(resumo.get("desvio_agua_pct") or _safe_pct(mpfm_agua, ref_agua), "%", 3)},
                ],
                "evidence": [
                    f"Limite HC: {_fmt_metric(pvt.get('limite_hc_pct'), '%', 2)}",
                    f"Limite Total: {_fmt_metric(pvt.get('limite_total_pct'), '%', 2)}",
                    f"Flags: {', '.join(qa_flags[:4]) if qa_flags else 'sem flags criticas'}",
                ],
            },
            {
                "id": "aprov",
                "num": "6",
                "title": "Aprovado / manter K",
                "kind": "ok" if decision_kind == "ok" else "info",
                "summary": "Quando o resultado fica dentro do criterio, o fluxo recomenda manter a medicao e programar proxima verificacao.",
                "metrics": [
                    {"label": "Campanha", "value": f"#{campaign.get('id')}" if campaign.get("id") else "-"},
                    {"label": "Proposta", "value": campaign.get("proposal_status") or "-"},
                    {"label": "K selecionado", "value": _fmt_metric(campaign.get("proposed_k_factor_selected"), "", 6)},
                ],
                "evidence": [
                    "Critério do memorial: compatibilidade por incerteza/envelope; limite fixo só como regra interna.",
                    f"Notas: {run.get('notes') or campaign.get('notes') or '-'}",
                ],
            },
            {
                "id": "inv",
                "num": "7",
                "title": "Investigar causa raiz",
                "kind": "err" if decision_kind == "err" else "info",
                "summary": "Quando ha desvio fora do criterio, separar erro de sensor, PVT/EOS, BSW, GSV e fonte SEP antes de intervencao.",
                "metrics": [
                    {"label": "Alarmes no dia", "value": str(len(alarms))},
                    {"label": "QA flags", "value": str(len(qa_flags))},
                    {"label": "BSW medio gap", "value": _fmt_metric(resumo.get("qa_gap_bsw_medio_pp"), "pp", 4)},
                ],
                "evidence": [
                    f"Alarmes: {alarms[0].get('title') if alarms else 'sem vinculo direto no dia'}",
                    f"GSV bloqueado: {'sim' if resumo.get('flag_gsv_nao_confirmado') else 'nao'}",
                    f"GOR fixo: {'sim' if resumo.get('flag_gor_fixed_caution') else 'nao'}",
                ],
            },
            {
                "id": "diag",
                "num": "8",
                "title": "Diagnostico diferencial",
                "kind": "warn" if qa_flags else "ok",
                "summary": "Usar trilha padrao, linha e PVT para confirmar se o desvio vem do instrumento, da EOS ou de premissas do teste.",
                "metrics": [
                    {"label": "Oleo std", "value": _fmt_metric(resumo.get("desvio_oleo_st_pct"), "%", 3)},
                    {"label": "Gas std", "value": _fmt_metric(resumo.get("desvio_gas_st_pct"), "%", 3)},
                    {"label": "Agua std", "value": _fmt_metric(resumo.get("desvio_agua_st_pct"), "%", 3)},
                ],
                "evidence": [
                    "Memorial: nao usar densidade Coriolis como rho_oil_STO sem validacao.",
                    "Memorial: Delta Rs deve ser incremental separador->tanque.",
                    f"Atividades relacionadas: {len(deadlines)} prazo(s)",
                ],
            },
        ]

    def _context_payload(cur, run_row, run_list: list[dict]) -> dict:
        if not run_row:
            return {"ok": False, "runs": run_list, "message": "Nenhuma reconciliação encontrada."}
        run = dict(run_row)
        for key in ("sep_hourly_json", "mpfm_hourly_json", "calc_hourly_json", "resumo_json", "pvt_snapshot", "analytical_snapshot", "test_window_json", "availability_json", "separator_authorized_json", "phase_k_proposal_json", "final_approval_json"):
            run[key] = _loads(run.get(key), [] if key.endswith("_json") and key not in {"resumo_json", "pvt_snapshot", "analytical_snapshot"} else {})

        pvt = _pvt(cur, run.get("pvt_params_id")) or run.get("pvt_snapshot") or {}
        campaign = _campaign(cur, run.get("campaign_id"))
        context = {
            "run": run,
            "runs": run_list,
            "pvt": pvt,
            "pvt_snapshot": run.get("pvt_snapshot") or {},
            "analytical_snapshot": run.get("analytical_snapshot") or {},
            "resumo": run.get("resumo_json") or {},
            "calc_horas": run.get("calc_hourly_json") or [],
            "sep_horas": run.get("sep_hourly_json") or [],
            "mpfm_horas": run.get("mpfm_hourly_json") or [],
            "daily_metrics": _daily_metrics(cur, run),
            "sep_sources": _sep_sources(cur, run.get("day_ref")),
            "campaign": campaign,
            "deadlines": _deadline_rows(cur, run.get("day_ref")),
            "alarms": _alarm_rows(cur, run),
            "flow_items": _flow_items(cur, run.get("id")),
        }
        context["steps"] = _build_steps(run, context)
        context["ok"] = True
        return context

    def _as_float(value: Any):
        try:
            if value is None:
                return None
            num = float(value)
            return num if num == num else None
        except Exception:
            return None

    def _find_hour(rows: list[dict], hour: int) -> dict:
        for row in rows or []:
            try:
                if int(row.get("hora")) == int(hour):
                    return row
            except Exception:
                continue
        return {}

    def _sum_metric(rows: list[dict], key: str):
        total = 0.0
        found = False
        for row in rows or []:
            value = _as_float(row.get(key))
            if value is not None:
                total += value
                found = True
        return round(total, 6) if found else None

    def _syn_status(status: str, default: str = "info") -> str:
        kind = _status_kind(status)
        return kind if kind != "info" else default

    def _node_status(kind: str, status: str, message: str = "") -> dict:
        return {"kind": kind, "status": status or "-", "message": message or ""}

    def _qa_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _build_synoptic_payload(context: dict) -> dict:
        run = context.get("run") or {}
        resumo = context.get("resumo") or {}
        pvt = context.get("pvt") or context.get("pvt_snapshot") or {}
        analytical = context.get("analytical_snapshot") or {}
        campaign = context.get("campaign") or {}
        calc_rows = context.get("calc_horas") or []
        mpfm_rows = context.get("mpfm_horas") or []
        sep_rows = context.get("sep_horas") or []
        daily = context.get("daily_metrics") or {}
        alarms = context.get("alarms") or []
        qa_flags = _qa_list(resumo.get("qa_flags_consolidados"))

        status_final = resumo.get("status_final") or resumo.get("status_linha") or run.get("status_final") or run.get("status_linha") or "-"
        hc_limit = _as_float(pvt.get("limite_hc_pct")) or 10.0
        total_limit = _as_float(pvt.get("limite_total_pct")) or 7.0
        ref_method = analytical.get("reference_system") or "Separador de Testes"
        comparison = "SS x SEP" if analytical.get("flow_mode") == "subsea_sep" else "TS x SEP"
        if "subsea" in str(analytical.get("flow_mode") or "").lower():
            comparison = "SS x SEP"

        hourly: list[dict] = []
        hours = sorted(
            {
                int(row.get("hora"))
                for row in (calc_rows + mpfm_rows + sep_rows)
                if str(row.get("hora", "")).strip().lstrip("-").isdigit()
            }
        )
        if not hours:
            hours = list(range(24))
        for hour in hours:
            if hour < 0 or hour > 23:
                continue
            calc = _find_hour(calc_rows, hour)
            mpfm = _find_hour(mpfm_rows, hour)
            sep = _find_hour(sep_rows, hour)
            dev_hc = _as_float(calc.get("desvio_hc_linha_pct"))
            dev_total = _as_float(calc.get("desvio_total_linha_pct"))
            valid = bool(calc.get("hora_valida")) or bool(_as_float(mpfm.get("hc_corr_t")) is not None and _as_float(calc.get("massa_hc_ref_t")) is not None)
            hour_status = "OK" if valid and (dev_hc is None or abs(dev_hc) <= hc_limit) and (dev_total is None or abs(dev_total) <= total_limit) else ("VERIFICAR" if valid else "SEM DADOS")
            oil_st = _as_float(mpfm.get("oleo_st_m3"))
            water_st = _as_float(mpfm.get("agua_st_m3"))
            gas_st = _as_float(mpfm.get("gas_st_ksm3"))
            wlr = round((water_st / (oil_st + water_st)) * 100, 4) if oil_st is not None and water_st is not None and (oil_st + water_st) else None
            gor = round((gas_st * 1000) / oil_st, 4) if gas_st is not None and oil_st else None
            hourly.append(
                {
                    "hour": hour,
                    "label": f"{hour:02d}:00",
                    "timestamp": calc.get("dt_str") or "",
                    "valid": valid,
                    "status": hour_status,
                    "mpfm": {
                        "oil_t": _as_float(mpfm.get("oleo_corr_t")),
                        "gas_t": _as_float(mpfm.get("gas_corr_t")),
                        "water_t": _as_float(mpfm.get("agua_corr_t")),
                        "hc_t": _as_float(mpfm.get("hc_corr_t")),
                        "total_t": _as_float(mpfm.get("total_corr_t")),
                        "oil_st_m3": oil_st,
                        "gas_st_ksm3": gas_st,
                        "water_st_m3": water_st,
                        "pressure_barg": _as_float(mpfm.get("pressao_barg")),
                        "temperature_c": _as_float(mpfm.get("temperatura_c")),
                        "wlr_pct": wlr,
                        "gor_sm3_sm3": gor,
                    },
                    "separator": {
                        "gsv_sm3": _as_float(sep.get("gsv_sep_sm3") or calc.get("gsv_sep_sm3")),
                        "gas_sm3": _as_float(sep.get("gas_vol_sm3") or calc.get("gas_livre_sep_sm3")),
                        "water_sm3": _as_float(sep.get("agua_gsv_sm3") or calc.get("agua_sep_sm3")),
                        "bsw_pct": _as_float(sep.get("bsw_user_pct") or calc.get("bsw_user_pct")),
                        "pressure_barg": _as_float(sep.get("pressao_barg")),
                        "temperature_c": _as_float(sep.get("temperatura_c")),
                        "hc_ref_t": _as_float(calc.get("massa_hc_ref_t")),
                        "total_ref_t": _as_float(calc.get("massa_total_ref_t")),
                    },
                    "deviations": {
                        "hc_pct": dev_hc,
                        "total_pct": dev_total,
                        "water_pct": _as_float(calc.get("desvio_agua_linha_pct")),
                        "oil_st_pct": _as_float(calc.get("desvio_oleo_st_pct")),
                        "gas_st_pct": _as_float(calc.get("desvio_gas_st_pct")),
                    },
                    "qa": {
                        "bsw": calc.get("flag_bsw") or "",
                        "line": calc.get("status_linha") or hour_status,
                    },
                }
            )

        alerts = []
        alerts.extend(qa_flags[:5])
        alerts.extend([str(item.get("title") or item.get("message") or "").strip() for item in alarms[:3] if str(item.get("title") or item.get("message") or "").strip()])

        mpfm_hc = _as_float(resumo.get("massa_hc_mpfm_t")) or _sum_metric(mpfm_rows, "hc_corr_t")
        mpfm_total = _as_float(resumo.get("massa_total_mpfm_t")) or _sum_metric(mpfm_rows, "total_corr_t")
        sep_hc = _as_float(resumo.get("massa_hc_ref_t")) or _sum_metric(calc_rows, "massa_hc_ref_t")
        sep_total = _as_float(resumo.get("massa_total_ref_t")) or _sum_metric(calc_rows, "massa_total_ref_t")

        return {
            "campaign": {
                "id": f"CMP-{campaign.get('id') or run.get('campaign_id') or run.get('id') or '-'}",
                "name": campaign.get("notes") or f"{run.get('bank') or '-'} / {run.get('tag') or '-'}",
                "wellRiser": run.get("tag") or "-",
                "comparison": comparison,
                "reference": ref_method,
                "productionDay": run.get("day_ref") or "",
                "window": analytical.get("window_mode") or "24h_day",
                "mode": "time_shifted" if analytical.get("test_start_at") else "daily",
                "status": status_final,
                "decision": status_final,
                "phase": run.get("campaign_phase") or "baseline",
            },
            "config": {
                "mainFlow": analytical.get("flow_mode") or "topside_sep",
                "gasLiftTreatment": "not_informed",
                "timeShift": {
                    "enabled": bool(analytical.get("test_start_at")),
                    "startAt": analytical.get("test_start_at") or "",
                    "durationHours": analytical.get("duration_hours"),
                },
                "referenceConditions": {
                    "fe": _as_float(pvt.get("fe")),
                    "rs": _as_float(pvt.get("rs")),
                    "rhoOilStd": _as_float(pvt.get("rho_oleo_std")),
                    "rhoGasStd": _as_float(pvt.get("rho_gas_std")),
                    "rhoWaterStd": _as_float(pvt.get("rho_agua_std")),
                    "source": pvt.get("source") or "pvt_params / snapshot",
                },
            },
            "totals": {
                "ss": {"available": False},
                "ts": {
                    "oil_t": _sum_metric(mpfm_rows, "oleo_corr_t"),
                    "gas_t": _sum_metric(mpfm_rows, "gas_corr_t"),
                    "water_t": _sum_metric(mpfm_rows, "agua_corr_t"),
                    "hc_t": mpfm_hc,
                    "total_t": mpfm_total,
                },
                "sep": {
                    "oil_ref_t": _sum_metric(calc_rows, "massa_oleo_ref_t"),
                    "gas_ref_t": _sum_metric(calc_rows, "massa_gas_ref_t"),
                    "water_ref_t": _as_float(resumo.get("massa_agua_ref_t")) or _sum_metric(calc_rows, "massa_agua_ref_t"),
                    "hc_ref_t": sep_hc,
                    "total_ref_t": sep_total,
                    "gsv_sm3": _sum_metric(sep_rows, "gsv_sep_sm3"),
                    "gas_sm3": _sum_metric(sep_rows, "gas_vol_sm3"),
                    "water_sm3": _sum_metric(sep_rows, "agua_gsv_sm3"),
                },
                "fcs": {
                    "allocated_hc_t": mpfm_hc,
                    "allocated_total_t": mpfm_total,
                    "status": status_final,
                },
                "gasLift": {"available": False, "mass_t": None},
            },
            "kFactors": {
                "mode": campaign.get("proposal_mode") or "hc",
                "rule": campaign.get("proposal_rule") or "mass_ratio_24h",
                "current": _as_float(campaign.get("current_k_factor")),
                "proposedHc": _as_float(campaign.get("proposed_k_factor_hc")),
                "proposedTotal": _as_float(campaign.get("proposed_k_factor_total")),
                "selected": _as_float(campaign.get("proposed_k_factor_selected")),
                "applied": _as_float(campaign.get("applied_k_factor")),
                "status": campaign.get("proposal_status") or status_final,
            },
            "monitoring": {
                "coveragePct": _as_float(resumo.get("cobertura_pct") or run.get("cobertura_pct")),
                "validHours": _as_float(resumo.get("horas_validas") or run.get("horas_validas")),
                "windowHours": _as_float(resumo.get("horas_janela")) or 24,
                "limits": {"hcPct": hc_limit, "totalPct": total_limit},
                "deviations": {
                    "hcPct": _as_float(resumo.get("desvio_hc_pct")),
                    "totalPct": _as_float(resumo.get("desvio_total_pct")),
                    "waterPct": _as_float(resumo.get("desvio_agua_pct")),
                },
                "qaFlags": qa_flags,
                "alarmCount": len(alarms),
                "alertMessages": alerts,
            },
            "hourly": hourly,
            "status": {
                "well": _node_status("ok", "ATIVO", "Run real selecionado."),
                "gasLift": _node_status("info", "NAO INFORMADO", "Sem massa de gas lift dedicada no run atual."),
                "ss": _node_status("warn", "SEM FONTE", "Sem serie subsea dedicada neste run."),
                "flowline": _node_status("ok", "RASTREADO", "Riser/TAG e banco vinculados ao run."),
                "ts": _node_status("ok" if mpfm_hc is not None else "warn", "NORMAL" if mpfm_hc is not None else "SEM DADOS", "Dados MPFM carregados da base curada."),
                "sep": _node_status("ok" if sep_hc is not None else "warn", "REFERENCIA OK" if sep_hc is not None else "VERIFICAR", "Separador convertido com PVT/snapshot."),
                "fcs": _node_status(_syn_status(status_final), status_final, "Decisao final da reconciliacao."),
            },
            "executionSteps": context.get("steps") or [],
            "source": {
                "runId": run.get("id"),
                "bank": run.get("bank"),
                "tag": run.get("tag"),
                "dataContract": "SynopticApiPayload.v1",
            },
        }

    @app.get("/api/methodology-flow/context")
    def api_methodology_flow_context(run_id: int | None = None, bank: str = "", tag: str = "", day_ref: str = ""):
        conn = db_conn()
        cur = conn.cursor()
        try:
            runs = _run_list(cur, bank, tag)
            if run_id:
                run_row = cur.execute("SELECT * FROM recon_runs WHERE id=?", (run_id,)).fetchone()
            else:
                run_row = _latest_run(cur, bank, tag, day_ref)
            return _context_payload(cur, run_row, runs)
        finally:
            conn.close()

    @app.get("/api/methodology-flow/items")
    def api_methodology_flow_items(run_id: int | None = None, item_type: str = "", status: str = "", limit: int = 80):
        conn = db_conn()
        cur = conn.cursor()
        try:
            return {"items": _flow_items(cur, run_id, item_type, status, limit)}
        finally:
            conn.close()

    @app.post("/api/methodology-flow/items")
    async def api_methodology_flow_item_create(request: Request):
        body = await request.json()
        title = str(body.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Informe um título para o registro.")
        now = _now()
        payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
        conn = db_conn()
        cur = conn.cursor()
        try:
            _ensure_flow_items_table(cur)
            cur.execute(
                """
                INSERT INTO methodology_flow_items(
                    run_id, item_type, scope, item_key, title, status, owner, due_date,
                    summary, payload_json, active, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    body.get("run_id"),
                    str(body.get("item_type") or "nota").strip() or "nota",
                    str(body.get("scope") or "run").strip() or "run",
                    str(body.get("item_key") or "").strip(),
                    title,
                    str(body.get("status") or "aberto").strip() or "aberto",
                    str(body.get("owner") or "").strip(),
                    str(body.get("due_date") or "").strip(),
                    str(body.get("summary") or "").strip(),
                    json.dumps(payload, ensure_ascii=False),
                    1,
                    now,
                    now,
                ),
            )
            conn.commit()
            item_id = int(cur.lastrowid)
            row = cur.execute("SELECT * FROM methodology_flow_items WHERE id=?", (item_id,)).fetchone()
            return {"ok": True, "item": _row_dict(row)}
        finally:
            conn.close()

    @app.put("/api/methodology-flow/items/{item_id}")
    async def api_methodology_flow_item_update(item_id: int, request: Request):
        body = await request.json()
        title = str(body.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Informe um título para o registro.")
        now = _now()
        payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
        conn = db_conn()
        cur = conn.cursor()
        try:
            _ensure_flow_items_table(cur)
            exists = cur.execute(
                "SELECT id FROM methodology_flow_items WHERE id=? AND COALESCE(active,1)=1",
                (item_id,),
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Registro da trilha não encontrado.")
            cur.execute(
                """
                UPDATE methodology_flow_items
                SET run_id=?, item_type=?, scope=?, item_key=?, title=?, status=?, owner=?,
                    due_date=?, summary=?, payload_json=?, updated_at=?
                WHERE id=?
                """,
                (
                    body.get("run_id"),
                    str(body.get("item_type") or "nota").strip() or "nota",
                    str(body.get("scope") or "run").strip() or "run",
                    str(body.get("item_key") or "").strip(),
                    title,
                    str(body.get("status") or "aberto").strip() or "aberto",
                    str(body.get("owner") or "").strip(),
                    str(body.get("due_date") or "").strip(),
                    str(body.get("summary") or "").strip(),
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    item_id,
                ),
            )
            conn.commit()
            row = cur.execute("SELECT * FROM methodology_flow_items WHERE id=?", (item_id,)).fetchone()
            return {"ok": True, "item": _row_dict(row)}
        finally:
            conn.close()

    @app.delete("/api/methodology-flow/items/{item_id}")
    def api_methodology_flow_item_delete(item_id: int):
        conn = db_conn()
        cur = conn.cursor()
        try:
            _ensure_flow_items_table(cur)
            cur.execute(
                "UPDATE methodology_flow_items SET active=0, updated_at=? WHERE id=? AND COALESCE(active,1)=1",
                (_now(), item_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Registro da trilha não encontrado.")
            return {"ok": True}
        finally:
            conn.close()

    @app.get("/api/twin/synoptic")
    def api_twin_synoptic(run_id: int | None = None, bank: str = "", tag: str = "", day_ref: str = ""):
        conn = db_conn()
        cur = conn.cursor()
        try:
            runs = _run_list(cur, bank, tag)
            if run_id:
                run_row = cur.execute("SELECT * FROM recon_runs WHERE id=?", (run_id,)).fetchone()
            else:
                run_row = _latest_run(cur, bank, tag, day_ref)
            context = _context_payload(cur, run_row, runs)
            if not context.get("ok"):
                return context
            return {**context, "synoptic": _build_synoptic_payload(context)}
        finally:
            conn.close()
