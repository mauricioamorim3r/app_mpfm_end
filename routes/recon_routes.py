from __future__ import annotations

import json

from fastapi import HTTPException, Request

from repositories.recon import ReconRepository
from recon_engine import (
    MPFMHoraInput,
    PVTParams,
    SepHoraInput,
    calcular_24h,
    calcular_hora,
    hora_to_dict,
    resumo_to_dict,
)
from services.recon import build_mpfm_horas, build_sep_horas_full


def register_recon_routes(app, ctx: dict) -> None:
    has_sep_alignment = ctx["has_sep_alignment"]
    get_sep_alignment = ctx["get_sep_alignment"]
    recon_repo = ReconRepository(ctx["db_conn"])

    def _build_analytical_snapshot(body: dict, pvt: PVTParams) -> dict:
        analytical = body.get("analytical") or {}
        return {
            "campaign_day": body.get("day_ref", ""),
            "window_mode": "24h_day",
            "flow_mode": analytical.get("flow_mode", "topside_sep"),
            "activity_kind": analytical.get("activity_kind", "calibracao_periodica"),
            "test_start_at": analytical.get("test_start_at", ""),
            "duration_hours": analytical.get("duration_hours"),
            "reference_system": analytical.get("reference_system", ""),
            "mpfm_pressure_barg": analytical.get("mpfm_pressure_barg"),
            "mpfm_temperature_c": analytical.get("mpfm_temperature_c"),
            "sep_pressure_barg": analytical.get("sep_pressure_barg"),
            "sep_temperature_c": analytical.get("sep_temperature_c"),
            "fe": pvt.fe,
            "rs": pvt.rs,
            "bsw_pct": analytical.get("bsw_pct"),
            "density_coriolis_kg_m3": analytical.get("density_coriolis_kg_m3"),
            "density_lab_kg_m3": analytical.get("density_lab_kg_m3"),
            "density_other_kg_m3": analytical.get("density_other_kg_m3"),
            "density_source": analytical.get("density_source", ""),
            "analysis_reference": analytical.get("analysis_reference", ""),
            "analysis_notes": analytical.get("analysis_notes", ""),
        }

    def _safe_ratio(ref_value, mpfm_value):
        if ref_value in (None, 0) or mpfm_value in (None, 0):
            return None
        try:
            return float(ref_value) / float(mpfm_value)
        except Exception:
            return None

    def _safe_improvement(before_value, after_value):
        if before_value is None or after_value is None:
            return None
        try:
            return round(abs(float(before_value)) - abs(float(after_value)), 6)
        except Exception:
            return None

    def _basis_limit_pct(pvt: PVTParams, proposal_mode: str) -> float:
        if proposal_mode == "total":
            return float(getattr(pvt, "limite_total_pct", 5.0) or 5.0)
        return float(getattr(pvt, "limite_hc_pct", 5.0) or 5.0)

    def _basis_desvio_pct(resumo, proposal_mode: str):
        if proposal_mode == "total":
            return getattr(resumo, "desvio_total_pct", None)
        return getattr(resumo, "desvio_hc_pct", None)

    def _build_k_proposal(body: dict, resumo) -> dict:
        current_k = body.get("current_k_factor")
        proposal_mode = body.get("proposal_mode") or "hc"
        proposed_manual = body.get("proposed_k_factor_manual")
        pvt: PVTParams = body.get("_pvt_model")
        try:
            current_k = float(current_k) if current_k not in ("", None) else None
        except Exception:
            current_k = None
        try:
            proposed_manual = float(proposed_manual) if proposed_manual not in ("", None) else None
        except Exception:
            proposed_manual = None

        factor_hc = None
        factor_total = None
        if current_k is not None:
            hc_ratio = _safe_ratio(getattr(resumo, "massa_hc_ref_t", None), getattr(resumo, "massa_hc_mpfm_t", None))
            total_ratio = _safe_ratio(getattr(resumo, "massa_total_ref_t", None), getattr(resumo, "massa_total_mpfm_t", None))
            factor_hc = round(current_k * hc_ratio, 6) if hc_ratio is not None else None
            factor_total = round(current_k * total_ratio, 6) if total_ratio is not None else None

        selected = None
        if proposal_mode == "manual":
            selected = proposed_manual
        elif proposal_mode == "total":
            selected = factor_total
        else:
            selected = factor_hc

        basis_name = "HC 24h" if proposal_mode != "total" else "Total 24h"
        basis_desvio = _basis_desvio_pct(resumo, proposal_mode)
        basis_limit = _basis_limit_pct(pvt, proposal_mode) if pvt else None

        proposal_status = "pending"
        if proposal_mode == "manual":
            proposal_status = "ready_manual" if proposed_manual is not None else "manual_required"
        elif current_k is None:
            proposal_status = "missing_current_k"
        elif not getattr(resumo, "consolidado_completo", False):
            proposal_status = "insufficient_window"
        elif selected is None:
            proposal_status = "missing_reference"
        elif basis_desvio is not None and basis_limit is not None and abs(float(basis_desvio)) <= float(basis_limit):
            proposal_status = "within_limits_no_change"
        else:
            proposal_status = "ready_for_application"

        recommendation = "Revisar dados da campanha."
        if proposal_status == "ready_manual":
            recommendation = "Aplicar o K manual informado e monitorar nova janela de 24h."
        elif proposal_status == "within_limits_no_change":
            recommendation = "Desvio dentro do limite. Manter o K atual e apenas monitorar."
        elif proposal_status == "ready_for_application":
            recommendation = "Aplicar o K proposto e monitorar nova janela de 24h no mesmo arranjo."
        elif proposal_status == "insufficient_window":
            recommendation = "Completar as 24h válidas antes de propor ajuste de K."
        elif proposal_status == "missing_current_k":
            recommendation = "Informar o K atual do medidor para calcular o novo K."
        elif proposal_status == "manual_required":
            recommendation = "Preencher o K manual para seguir com proposta manual."

        return {
            "current_k_factor": current_k,
            "proposal_mode": proposal_mode,
            "proposal_rule": "mass_ratio_24h",
            "proposal_status": proposal_status,
            "basis_name": basis_name,
            "basis_desvio_pct": basis_desvio,
            "basis_limit_pct": basis_limit,
            "acceptance_rule": "K_novo = K_atual x (massa_ref_24h / massa_mpfm_24h) na base selecionada, com janela completa de 24h.",
            "recommendation": recommendation,
            "proposed_k_factor_hc": factor_hc,
            "proposed_k_factor_total": factor_total,
            "proposed_k_factor_manual": proposed_manual,
            "proposed_k_factor_selected": selected,
            "proposal_is_indicative": False,
        }

    def _evaluate_monitoring(campaign: dict | None, resumo, pvt: PVTParams) -> dict:
        baseline_hc = campaign.get("baseline_desvio_hc_pct") if campaign else None
        baseline_total = campaign.get("baseline_desvio_total_pct") if campaign else None
        post_hc = getattr(resumo, "desvio_hc_pct", None)
        post_total = getattr(resumo, "desvio_total_pct", None)
        improvement_hc = _safe_improvement(baseline_hc, post_hc)
        improvement_total = _safe_improvement(baseline_total, post_total)
        limit_hc = float(getattr(pvt, "limite_hc_pct", 5.0) or 5.0)
        limit_total = float(getattr(pvt, "limite_total_pct", 5.0) or 5.0)
        within_hc = post_hc is not None and abs(float(post_hc)) <= limit_hc
        within_total = post_total is not None and abs(float(post_total)) <= limit_total

        monitoring_status = "pending"
        if not getattr(resumo, "consolidado_completo", False):
            monitoring_status = "insufficient_window"
        elif within_hc and within_total:
            monitoring_status = "accepted"
        elif getattr(resumo, "status_hc", "") == "VERIFICAR" or getattr(resumo, "status_total", "") == "VERIFICAR":
            monitoring_status = "rejected"
        elif (improvement_hc is not None and improvement_hc > 0) or (improvement_total is not None and improvement_total > 0):
            monitoring_status = "improved_not_accepted"
        elif getattr(resumo, "status_hc", "") == "ATENÇÃO" or getattr(resumo, "status_total", "") == "ATENÇÃO":
            monitoring_status = "monitoring_attention"
        else:
            monitoring_status = "stable_or_worse"

        return {
            "acceptance_rule": "Aceitar apenas quando HC e Total do monitoramento 24h ficarem dentro dos limites configurados no PVT.",
            "limit_hc_pct": limit_hc,
            "limit_total_pct": limit_total,
            "baseline_desvio_hc_pct": baseline_hc,
            "baseline_desvio_total_pct": baseline_total,
            "post_desvio_hc_pct": post_hc,
            "post_desvio_total_pct": post_total,
            "improvement_hc_pp": improvement_hc,
            "improvement_total_pp": improvement_total,
            "monitoring_status": monitoring_status,
        }

    def _serialize_campaign(row):
        if not row:
            return None
        data = dict(row)
        for key in ("pvt_snapshot", "analytical_snapshot", "sep_alignment_snapshot"):
            if data.get(key):
                try:
                    data[key] = json.loads(data[key])
                except Exception:
                    pass
        return data

    def _loads_json(value, default):
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return default

    def _as_number(value):
        try:
            if value is None or value == "":
                return None
            number = float(value)
            return number if number == number else None
        except Exception:
            return None

    def _pct_status(value, limit):
        number = _as_number(value)
        lim = _as_number(limit)
        if number is None or lim is None:
            return "warn"
        return "ok" if abs(number) <= lim else "critical"

    def _check_item(label: str, status: str, detail: str, evidence: str = "") -> dict:
        return {
            "label": label,
            "status": status,
            "detail": detail,
            "evidence": evidence,
        }

    def _first_valid_hour(calc_horas: list[dict]) -> dict:
        for row in calc_horas or []:
            if row.get("oleo_base_ref_sm3") is not None or row.get("massa_hc_ref_t") is not None:
                return row
        return (calc_horas or [{}])[0] if calc_horas else {}

    def _daily_metric_sources(cur, run: dict) -> list[str]:
        rows = cur.execute(
            """
            SELECT DISTINCT source_file
            FROM measurements_curated
            WHERE row_kind='daily'
              AND day_ref=?
              AND bank=?
              AND (
                tag=?
                OR REPLACE(REPLACE(REPLACE(UPPER(COALESCE(tag,'')), ' ', ''), '-', ''), '_', '') =
                   REPLACE(REPLACE(REPLACE(UPPER(?), ' ', ''), '-', ''), '_', '')
              )
              AND COALESCE(source_file,'')<>''
            ORDER BY source_file
            LIMIT 12
            """,
            (run["day_ref"], run["bank"], run["tag"], run["tag"]),
        ).fetchall()
        return [row["source_file"] for row in rows]

    def _separator_sources(cur, day_ref: str) -> list[dict]:
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

    def _build_memorial_context(run_row) -> dict:
        run = dict(run_row)
        for key, default in (
            ("sep_hourly_json", []),
            ("mpfm_hourly_json", []),
            ("calc_hourly_json", []),
            ("resumo_json", {}),
            ("pvt_snapshot", {}),
            ("analytical_snapshot", {}),
            ("test_window_json", None),
        ):
            run[key] = _loads_json(run.get(key), default)

        conn = ctx["db_conn"]()
        cur = conn.cursor()
        pvt_row = cur.execute("SELECT * FROM pvt_params WHERE id=?", (run.get("pvt_params_id"),)).fetchone() if run.get("pvt_params_id") else None
        campaign_row = cur.execute("SELECT * FROM recon_campaigns WHERE id=?", (run.get("campaign_id"),)).fetchone() if run.get("campaign_id") else None
        sep_sources = _separator_sources(cur, run.get("day_ref"))
        mpfm_sources = _daily_metric_sources(cur, run)
        sep_alignment = get_sep_alignment(run.get("bank"), run.get("day_ref")) if has_sep_alignment(run.get("bank"), run.get("day_ref")) else None
        conn.close()

        pvt = dict(pvt_row) if pvt_row else (run.get("pvt_snapshot") or {})
        campaign = _serialize_campaign(campaign_row) if campaign_row else None
        resumo = run.get("resumo_json") or {}
        analytical = run.get("analytical_snapshot") or {}
        calc_horas = run.get("calc_hourly_json") or []
        sample = _first_valid_hour(calc_horas)
        window_hours = resumo.get("horas_janela") or (len(run.get("test_window_json") or []) if isinstance(run.get("test_window_json"), list) else 24)
        coverage = _as_number(resumo.get("cobertura_pct") if resumo.get("cobertura_pct") is not None else run.get("cobertura_pct"))
        pvt_source = pvt.get("source") or analytical.get("analysis_reference") or "Snapshot do run"
        gsv_confirmed = bool(pvt.get("gsv_confirmed"))
        limits = {
            "hc_pct": pvt.get("limite_hc_pct"),
            "total_pct": pvt.get("limite_total_pct"),
            "agua_pct": pvt.get("limite_agua_pct"),
        }

        checklist = [
            _check_item(
                "MPFM real carregado",
                "ok" if run.get("mpfm_hourly_json") else "missing",
                f"{len(run.get('mpfm_hourly_json') or [])} hora(s) persistidas no run.",
                "; ".join(mpfm_sources[:3]) if mpfm_sources else "Fonte diária não informada no registro curado.",
            ),
            _check_item(
                "Separador real carregado",
                "ok" if run.get("sep_hourly_json") and sep_sources else "warn" if run.get("sep_hourly_json") else "missing",
                f"{len(run.get('sep_hourly_json') or [])} hora(s) no run; {len(sep_sources)} arquivo(s) de separador encontrados para a data.",
                "; ".join([s.get("source_file", "") for s in sep_sources[:3]]) or "Sem arquivo associado.",
            ),
            _check_item(
                "Alinhamento SEP x banco",
                "ok" if sep_alignment else "warn",
                "Alinhamento diário ativo encontrado." if sep_alignment else "Sem alinhamento formal ativo para este banco/data.",
                json.dumps(sep_alignment, ensure_ascii=False) if sep_alignment else "",
            ),
            _check_item(
                "PVT versionado",
                "ok" if pvt else "missing",
                f"FE={pvt.get('fe')} | RS={pvt.get('rs')} | base {pvt.get('temp_ref_c', 20)} °C / {pvt.get('pres_ref_bar', 1.01325)} bar(a).",
                pvt_source,
            ),
            _check_item(
                "GSV confirmado",
                "ok" if gsv_confirmed else "critical",
                "Subtração óleo/água habilitada." if gsv_confirmed else "O motor bloqueia óleo base quando GSV não está confirmado como gross liquid volume.",
                "pvt_params.gsv_confirmed",
            ),
            _check_item(
                "BSW ou água medida",
                "ok" if analytical.get("bsw_pct") is not None or sample.get("agua_sep_sm3") is not None else "warn",
                f"BSW campanha={analytical.get('bsw_pct', 'não informado')} | água amostra={sample.get('agua_sep_sm3', 'não disponível')}.",
                analytical.get("analysis_reference") or "Snapshot analítico / separador horário.",
            ),
            _check_item(
                "Janela de cálculo",
                "ok" if resumo.get("consolidado_completo") else "warn" if coverage and coverage > 0 else "missing",
                f"{resumo.get('horas_validas', run.get('horas_validas'))}/{window_hours}h válidas ({coverage if coverage is not None else '—'}%).",
                "recon_runs.resumo_json",
            ),
            _check_item(
                "Critério de aceitação",
                "warn" if limits.get("hc_pct") is not None and limits.get("total_pct") is not None else "missing",
                f"Limites operacionais cadastrados: HC {limits.get('hc_pct')}%, Total {limits.get('total_pct')}%, Água {limits.get('agua_pct')}%. Requer fonte documental do plano aprovado.",
                "pvt_params.limite_*",
            ),
            _check_item(
                "Incerteza expandida",
                "missing",
                "O run ainda não contém orçamento de incerteza GUM/En persistido. Manter decisão como técnica operacional até cadastrar os componentes.",
                "Memorial/planilhas enviadas indicam este bloco como necessário.",
            ),
        ]

        formula_rows = [
            {
                "name": "Óleo base do separador",
                "formula": "NSV_sep = GSV_sep - Agua_sep",
                "value": sample.get("oleo_base_ref_sm3"),
                "unit": "Sm3/h",
                "note": "A aplicação prioriza água medida do separador; é equivalente à remoção de BSW quando a água representa a fração aquosa do GSV.",
            },
            {
                "name": "Óleo estabilizado",
                "formula": "V_STO = NSV_sep x FE",
                "value": sample.get("oleo_std_reconc_sm3"),
                "unit": "Sm3/h",
                "note": f"FE={pvt.get('fe')} congelado no snapshot PVT.",
            },
            {
                "name": "Gás associado total",
                "formula": "V_gas_total = V_gas_sep + V_STO x RS",
                "value": sample.get("gas_total_reconc_sm3"),
                "unit": "Sm3/h",
                "note": f"RS={pvt.get('rs')} Sm3/Sm3; tratar como premissa PVT, não Rs total de reservatório sem validação.",
            },
            {
                "name": "Massa de óleo referência",
                "formula": "m_oil_REF = V_STO x rho_oil_std / 1000",
                "value": sample.get("massa_oleo_ref_t"),
                "unit": "t/h",
                "note": f"rho_oil_std={pvt.get('rho_oleo_std')} kg/m3.",
            },
            {
                "name": "Massa HC 24h",
                "formula": "m_HC = m_oil + m_gas",
                "value": resumo.get("massa_hc_ref_t"),
                "unit": "t",
                "note": f"MPFM={resumo.get('massa_hc_mpfm_t')} t; desvio={resumo.get('desvio_hc_pct')}%.",
            },
            {
                "name": "Desvio HC",
                "formula": "delta_HC = 100 x (m_HC_MPFM - m_HC_REF) / m_HC_REF",
                "value": resumo.get("desvio_hc_pct"),
                "unit": "%",
                "note": f"Status: {resumo.get('status_hc') or run.get('status_linha') or '-'}",
            },
            {
                "name": "Fator K proposto",
                "formula": "K_novo = K_atual x (massa_REF_24h / massa_MPFM_24h)",
                "value": (campaign or {}).get("proposed_k_factor_selected"),
                "unit": "-",
                "note": f"Regra: {(campaign or {}).get('proposal_rule') or 'mass_ratio_24h'}; proposta indicativa, dependente de aprovação e monitoramento.",
            },
        ]

        decisions = [
            {
                "label": "HC",
                "ref": resumo.get("massa_hc_ref_t"),
                "mpfm": resumo.get("massa_hc_mpfm_t"),
                "deviation_pct": resumo.get("desvio_hc_pct"),
                "limit_pct": limits.get("hc_pct"),
                "status": resumo.get("status_hc") or _pct_status(resumo.get("desvio_hc_pct"), limits.get("hc_pct")),
            },
            {
                "label": "Total",
                "ref": resumo.get("massa_total_ref_t"),
                "mpfm": resumo.get("massa_total_mpfm_t"),
                "deviation_pct": resumo.get("desvio_total_pct"),
                "limit_pct": limits.get("total_pct"),
                "status": resumo.get("status_total") or _pct_status(resumo.get("desvio_total_pct"), limits.get("total_pct")),
            },
            {
                "label": "Água",
                "ref": resumo.get("massa_agua_ref_t"),
                "mpfm": resumo.get("massa_agua_mpfm_t"),
                "deviation_pct": resumo.get("desvio_agua_pct"),
                "limit_pct": limits.get("agua_pct"),
                "status": resumo.get("status_agua") or _pct_status(resumo.get("desvio_agua_pct"), limits.get("agua_pct")),
            },
        ]

        qa_flags = resumo.get("qa_flags_consolidados") or ""
        if isinstance(qa_flags, str):
            qa_flags = [item for item in qa_flags.split("|") if item]

        recommendations = []
        if any(item["status"] == "missing" for item in checklist):
            recommendations.append("Completar evidências ausentes antes de emitir relatório técnico final.")
        if any(item["status"] == "critical" for item in checklist):
            recommendations.append("Resolver bloqueios técnicos críticos antes de aprovar fator K ou conclusão metrológica.")
        if not resumo.get("consolidado_completo"):
            recommendations.append("Registrar explicitamente a cobertura da janela; se o plano exigir 24h completas, repetir/complementar campanha.")
        if campaign and campaign.get("proposed_k_factor_selected") is not None:
            recommendations.append("Tratar o K calculado como proposta operacional e confirmar com monitoramento pós-aplicação.")
        recommendations.append("Cadastrar orçamento de incerteza quando a decisão precisar ser defendida como conformidade metrológica formal.")

        return {
            "ok": True,
            "run": {
                "id": run.get("id"),
                "run_at": run.get("run_at"),
                "bank": run.get("bank"),
                "tag": run.get("tag"),
                "day_ref": run.get("day_ref"),
                "campaign_id": run.get("campaign_id"),
                "campaign_phase": run.get("campaign_phase"),
                "author": run.get("author"),
                "notes": run.get("notes"),
                "status_final": run.get("status_final") or resumo.get("status_final"),
            },
            "summary": resumo,
            "pvt": pvt,
            "analytical": analytical,
            "campaign": campaign,
            "sample_hour": sample,
            "checklist": checklist,
            "formula_rows": formula_rows,
            "decisions": decisions,
            "qa_flags": qa_flags,
            "evidence": {
                "mpfm_sources": mpfm_sources,
                "sep_sources": sep_sources,
                "sep_alignment": sep_alignment,
            },
            "recommendations": recommendations,
        }

    @app.get("/api/pvt-params")
    def api_pvt_list(bank: str = "", tag: str = ""):
        return {"params": recon_repo.list_pvt_params(bank, tag)}

    @app.get("/api/recon/mpfm-tags")
    def api_recon_mpfm_tags(bank: str = ""):
        if not bank.strip():
            return {"tags": []}
        return {"tags": recon_repo.list_mpfm_tags(bank)}

    @app.post("/api/pvt-params")
    async def api_pvt_create(request: Request):
        body = await request.json()
        required = ["bank", "tag", "fe", "rs", "rho_oleo_std", "rho_gas_std", "rho_agua_std"]
        for field in required:
            if body.get(field) is None:
                raise HTTPException(400, f"Campo obrigatório: {field}")
        new_id = recon_repo.create_pvt_params(body)
        return {"ok": True, "id": new_id}

    @app.put("/api/pvt-params/{pvt_id}")
    async def api_pvt_update(pvt_id: int, request: Request):
        body = await request.json()
        try:
            recon_repo.update_pvt_params(pvt_id, body)
            return {"ok": True, "id": pvt_id}
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @app.delete("/api/pvt-params/{pvt_id}")
    def api_pvt_delete(pvt_id: int):
        recon_repo.delete_pvt_params(pvt_id)
        return {"ok": True, "id": pvt_id}

    def _load_pvt_params(pvt_id: int) -> PVTParams:
        try:
            return recon_repo.get_pvt_params_model(pvt_id)
        except LookupError:
            raise HTTPException(404, f"Parâmetros PVT id={pvt_id} não encontrados")

    @app.get("/api/recon/data-check")
    def api_recon_data_check(bank: str = "", tag: str = "", day_ref: str = "", pvt_id: int | None = None):
        """Retorna quantas horas de MPFM e SEP estão disponíveis para o dia/tag informados.
        Usado pelo frontend para mostrar preview antes do cálculo."""
        if not all([bank.strip(), tag.strip(), day_ref.strip()]):
            return {
                "mpfm_horas": [],
                "sep_horas": [],
                "mpfm_count": 0,
                "sep_count": 0,
                "pvt_count": 0,
                "selected_pvt_count": 0,
                "sep_alignment_exists": False,
                "has_data": False,
            }
        mpfm_rows = recon_repo.list_mpfm_hour_rows(bank, tag, day_ref)
        mpfm_hours = sorted(set(r[0] for r in mpfm_rows if r[0] is not None))
        sep_rows = recon_repo.list_sep_detail_hour_rows(day_ref)
        sep_hours = sorted(set(r[1] for r in sep_rows if r[1] is not None))
        if not sep_hours:
            legacy = recon_repo.list_sep_hour_rows(day_ref)
            sep_hours = sorted(set(r[0] for r in legacy if r[0] is not None))
        pvt_list = recon_repo.list_pvt_params(bank)
        selected_pvt_count = 0
        if pvt_id is not None:
            selected_pvt_count = 1 if any(int(p.get("id") or 0) == pvt_id for p in pvt_list) else 0
        return {
            "mpfm_horas": mpfm_hours,
            "sep_horas": sep_hours,
            "mpfm_count": len(mpfm_hours),
            "sep_count": len(sep_hours),
            "pvt_count": len(pvt_list),
            "selected_pvt_count": selected_pvt_count,
            "sep_alignment_exists": has_sep_alignment(bank, day_ref),
            "has_data": len(mpfm_hours) > 0 or len(sep_hours) > 0,
        }

    @app.post("/api/recon/calcular")
    async def api_recon_calcular(request: Request):
        body = await request.json()
        pvt_id = body.get("pvt_params_id")
        bank = body.get("bank", "")
        tag = body.get("tag", "")
        day_ref = body.get("day_ref", "")

        if not all([pvt_id, bank, tag, day_ref]):
            raise HTTPException(400, "Campos obrigatórios: pvt_params_id, bank, tag, day_ref")

        pvt = _load_pvt_params(int(pvt_id))
        campaign_phase = body.get("campaign_phase") or "baseline"
        campaign_id = body.get("campaign_id")
        analytical_snapshot = _build_analytical_snapshot(body, pvt)
        sep_horas = build_sep_horas_full(recon_repo, has_sep_alignment, bank, day_ref, analytical_snapshot)
        mpfm_horas = build_mpfm_horas(recon_repo, bank, tag, day_ref)

        if not sep_horas and not mpfm_horas:
            raise HTTPException(404, f"Sem dados para bank={bank} tag={tag} day_ref={day_ref}")

        # ── Janela de teste (opcional) ────────────────────────────────────────
        # Aceita: {"test_window": {"hora_inicio": 6, "hora_fim": 13}}
        # ou:     {"test_window": {"horas": [6, 7, 8, 9, 10, 11, 12, 13]}}
        # Se ausente, usa janela completa de 24h (comportamento padrão).
        test_window_raw = body.get("test_window")
        test_window_horas = None
        if test_window_raw:
            if "horas" in test_window_raw:
                test_window_horas = [int(h) for h in test_window_raw["horas"]]
            elif "hora_inicio" in test_window_raw and "hora_fim" in test_window_raw:
                h_ini = int(test_window_raw["hora_inicio"])
                h_fim = int(test_window_raw["hora_fim"])
                if h_fim >= h_ini:
                    test_window_horas = list(range(h_ini, h_fim + 1))
                else:
                    # Janela que atravessa meia-noite (ex: 22 às 5)
                    test_window_horas = list(range(h_ini, 24)) + list(range(0, h_fim + 1))
        test_window_json = json.dumps(test_window_horas) if test_window_horas is not None else None

        sep_map = {s.hora: s for s in sep_horas}
        mpfm_map = {m.hora: m for m in mpfm_horas}
        all_horas = sorted(set(list(sep_map.keys()) + list(mpfm_map.keys())))

        resultados = []
        for hour in all_horas:
            sep = sep_map.get(hour, SepHoraInput(hora=hour))
            mpfm = mpfm_map.get(hour, MPFMHoraInput(hora=hour))
            resultados.append(calcular_hora(sep, mpfm, pvt))

        resumo = calcular_24h(resultados, mpfm_horas, pvt, test_window_horas=test_window_horas)
        calc_json = json.dumps([hora_to_dict(r) for r in resultados])
        resumo_json = json.dumps(resumo_to_dict(resumo))
        sep_json = json.dumps(
            [
                {
                    "hora": s.hora,
                    "gsv_sep_sm3": s.gsv_sep_sm3,
                    "agua_gsv_sm3": s.agua_gsv_sm3,
                    "agua_mass_t": s.agua_mass_t,
                    "gas_vol_sm3": s.gas_vol_sm3,
                    "gas_mass_t": s.gas_mass_t,
                    "bsw_user_pct": s.bsw_user_pct,
                    "pressao_barg": s.pressao_barg,
                    "temperatura_c": s.temperatura_c,
                }
                for s in sep_horas
            ]
        )
        mpfm_json = json.dumps(
            [
                {
                    "hora": m.hora,
                    "oleo_corr_t": m.oleo_corr_t,
                    "gas_corr_t": m.gas_corr_t,
                    "agua_corr_t": m.agua_corr_t,
                    "hc_corr_t": m.hc_corr_t,
                    "total_corr_t": m.total_corr_t,
                    "oleo_st_t": m.oleo_st_t,
                    "gas_st_ksm3": m.gas_st_ksm3,
                    "oleo_st_m3": m.oleo_st_m3,
                    "agua_st_m3": m.agua_st_m3,
                    "pressao_barg": m.pressao_barg,
                    "temperatura_c": m.temperatura_c,
                }
                for m in mpfm_horas
            ]
        )

        proposal_body = dict(body)
        proposal_body["_pvt_model"] = pvt
        k_proposal = _build_k_proposal(proposal_body, resumo)
        run_body = dict(body)
        run_body["analytical_snapshot"] = analytical_snapshot
        run_body["campaign_phase"] = campaign_phase
        run_body["campaign_id"] = campaign_id
        run_body["test_window_json"] = test_window_json
        run_id = recon_repo.create_recon_run(run_body, pvt, sep_horas, mpfm_horas, resultados, resumo, hora_to_dict, resumo_to_dict)

        campaign = None
        sep_alignment = get_sep_alignment(bank, day_ref) if has_sep_alignment(bank, day_ref) else None
        if campaign_phase == "post" and campaign_id:
            recon_repo.assign_recon_run_campaign(run_id, int(campaign_id), "post")
            current_campaign = _serialize_campaign(recon_repo.get_recon_campaign(int(campaign_id)))
            monitoring_eval = _evaluate_monitoring(current_campaign or {}, resumo, pvt)
            recon_repo.update_recon_campaign_post_monitor(
                int(campaign_id),
                post_day_ref=day_ref,
                post_run_id=run_id,
                applied_k_factor=body.get("applied_k_factor"),
                applied_at=body.get("applied_at", ""),
                post_desvio_hc_pct=monitoring_eval["post_desvio_hc_pct"],
                post_desvio_total_pct=monitoring_eval["post_desvio_total_pct"],
                improvement_hc_pp=monitoring_eval["improvement_hc_pp"],
                improvement_total_pp=monitoring_eval["improvement_total_pp"],
                monitoring_status=monitoring_eval["monitoring_status"],
                notes=body.get("notes", ""),
            )
            recon_repo.update_recon_campaign_k_fields(
                int(campaign_id),
                {
                    "monitoring_status": monitoring_eval["monitoring_status"],
                    "status": monitoring_eval["monitoring_status"],
                },
            )
            campaign = _serialize_campaign(recon_repo.get_recon_campaign(int(campaign_id)))
        else:
            campaign_payload = {
                "bank": bank,
                "tag": tag,
                "baseline_day_ref": day_ref,
                "baseline_run_id": run_id,
                "pvt_params_id": int(pvt_id),
                "pvt_snapshot": {
                    "fe": pvt.fe,
                    "rs": pvt.rs,
                    "rho_oleo_std": pvt.rho_oleo_std,
                    "rho_gas_std": pvt.rho_gas_std,
                    "rho_agua_std": pvt.rho_agua_std,
                    "gsv_confirmed": pvt.gsv_confirmed,
                    "gor_mode": pvt.gor_mode,
                },
                "analytical_snapshot": analytical_snapshot,
                "sep_alignment_snapshot": sep_alignment or {},
                "current_k_factor": k_proposal["current_k_factor"],
                "proposal_mode": k_proposal["proposal_mode"],
                "proposal_rule": k_proposal["proposal_rule"],
                "proposal_status": k_proposal["proposal_status"],
                "proposed_k_factor_hc": k_proposal["proposed_k_factor_hc"],
                "proposed_k_factor_total": k_proposal["proposed_k_factor_total"],
                "proposed_k_factor_selected": k_proposal["proposed_k_factor_selected"],
                "proposed_k_factor_manual": k_proposal["proposed_k_factor_manual"],
                "baseline_desvio_hc_pct": getattr(resumo, "desvio_hc_pct", None),
                "baseline_desvio_total_pct": getattr(resumo, "desvio_total_pct", None),
                "author": body.get("author", ""),
                "notes": body.get("notes", ""),
                "status": "ready_for_k" if k_proposal["proposal_status"] in ("ready_for_application", "ready_manual", "within_limits_no_change") else "baseline_review",
            }
            campaign_id = recon_repo.create_recon_campaign(campaign_payload)
            recon_repo.assign_recon_run_campaign(run_id, int(campaign_id), "baseline")
            campaign = _serialize_campaign(recon_repo.get_recon_campaign(int(campaign_id)))

        return {
            "ok": True,
            "run_id": run_id,
            "calc_horas": [hora_to_dict(r) for r in resultados],
            "resumo": resumo_to_dict(resumo),
            "meta": {
                "bank": bank,
                "tag": tag,
                "day_ref": day_ref,
                "horas_validas": resumo.horas_validas,
                "cobertura_pct": resumo.cobertura_pct,
                "analytical_snapshot": analytical_snapshot,
                "k_proposal": k_proposal,
                "campaign": campaign,
                "monitoring": (_evaluate_monitoring(campaign or {}, resumo, pvt) if campaign_phase == "post" and campaign else None),
                "pvt": {
                    "fe": pvt.fe,
                    "rs": pvt.rs,
                    "rho_oleo_std": pvt.rho_oleo_std,
                    "rho_gas_std": pvt.rho_gas_std,
                    "rho_agua_std": pvt.rho_agua_std,
                    "gsv_confirmed": pvt.gsv_confirmed,
                    "gor_mode": pvt.gor_mode,
                    "limite_hc_pct": pvt.limite_hc_pct,
                    "limite_total_pct": pvt.limite_total_pct,
                },
            },
        }

    @app.get("/api/recon/runs")
    def api_recon_runs(bank: str = "", tag: str = "", limit: int = 50):
        return {"runs": recon_repo.list_recon_runs(bank, tag, limit)}

    @app.get("/api/recon/campaigns")
    def api_recon_campaigns(bank: str = "", tag: str = "", limit: int = 50):
        return {"campaigns": recon_repo.list_recon_campaigns(bank, tag, limit)}

    @app.get("/api/recon/campaigns/{campaign_id}")
    def api_recon_campaign_detail(campaign_id: int):
        row = recon_repo.get_recon_campaign(campaign_id)
        if not row:
            raise HTTPException(404, f"Campanha {campaign_id} não encontrada")
        return _serialize_campaign(row)

    @app.get("/api/recon/runs/{run_id}")
    def api_recon_run_detail(run_id: int):
        row = recon_repo.get_recon_run(run_id)
        if not row:
            raise HTTPException(404, f"Run {run_id} não encontrada")
        data = dict(row)
        for key in ("sep_hourly_json", "mpfm_hourly_json", "calc_hourly_json", "resumo_json", "pvt_snapshot", "analytical_snapshot"):
            if data.get(key):
                try:
                    data[key] = json.loads(data[key])
                except Exception:
                    pass
        return data

    @app.get("/api/recon/runs/{run_id}/memorial")
    def api_recon_run_memorial(run_id: int):
        row = recon_repo.get_recon_run(run_id)
        if not row:
            raise HTTPException(404, f"Run {run_id} não encontrada")
        return _build_memorial_context(row)
