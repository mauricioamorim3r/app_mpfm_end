from __future__ import annotations

import json
from datetime import datetime

from recon_engine import PVTParams


class ReconRepository:
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def list_pvt_params(self, bank: str = "", tag: str = "") -> list[dict]:
        conn = self._db_conn()
        cur = conn.cursor()
        sql = "SELECT * FROM pvt_params WHERE 1=1"
        params = []
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        sql += " ORDER BY bank, tag, valid_from DESC"
        rows = [dict(row) for row in cur.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def create_pvt_params(self, body: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO pvt_params(
                bank,tag,fe,rs,rho_oleo_std,rho_gas_std,rho_agua_std,
                temp_ref_c,pres_ref_bar,gsv_confirmed,gor_mode,
                limite_hc_pct,limite_total_pct,limite_agua_pct,
                valid_from,valid_to,source,author,notes,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                body["bank"],
                body["tag"],
                float(body["fe"]),
                float(body["rs"]),
                float(body["rho_oleo_std"]),
                float(body["rho_gas_std"]),
                float(body["rho_agua_std"]),
                float(body.get("temp_ref_c", 20.0)),
                float(body.get("pres_ref_bar", 1.01325)),
                int(bool(body.get("gsv_confirmed", False))),
                body.get("gor_mode", "unknown"),
                float(body.get("limite_hc_pct", 5.0)),
                float(body.get("limite_total_pct", 5.0)),
                float(body.get("limite_agua_pct", 20.0)),
                body.get("valid_from", ""),
                body.get("valid_to", ""),
                body.get("source", ""),
                body.get("author", ""),
                body.get("notes", ""),
                now,
            ),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def update_pvt_params(self, pvt_id: int, body: dict) -> None:
        conn = self._db_conn()
        fields = [
            "fe",
            "rs",
            "rho_oleo_std",
            "rho_gas_std",
            "rho_agua_std",
            "temp_ref_c",
            "pres_ref_bar",
            "gsv_confirmed",
            "gor_mode",
            "limite_hc_pct",
            "limite_total_pct",
            "limite_agua_pct",
            "valid_from",
            "valid_to",
            "source",
            "author",
            "notes",
        ]
        sets = []
        values = []
        for field in fields:
            if field in body:
                sets.append(f"{field}=?")
                value = body[field]
                if field == "gsv_confirmed":
                    value = int(bool(value))
                elif field in (
                    "fe",
                    "rs",
                    "rho_oleo_std",
                    "rho_gas_std",
                    "rho_agua_std",
                    "temp_ref_c",
                    "pres_ref_bar",
                    "limite_hc_pct",
                    "limite_total_pct",
                    "limite_agua_pct",
                ):
                    value = float(value)
                values.append(value)
        if not sets:
            conn.close()
            raise ValueError("Nenhum campo para atualizar")
        values.append(pvt_id)
        conn.execute(f'UPDATE pvt_params SET {", ".join(sets)} WHERE id=?', values)
        conn.commit()
        conn.close()

    def delete_pvt_params(self, pvt_id: int) -> None:
        conn = self._db_conn()
        conn.execute("DELETE FROM pvt_params WHERE id=?", (pvt_id,))
        conn.commit()
        conn.close()

    def get_pvt_params(self, pvt_id: int):
        conn = self._db_conn()
        row = conn.execute("SELECT * FROM pvt_params WHERE id=?", (pvt_id,)).fetchone()
        conn.close()
        return row

    def get_pvt_params_model(self, pvt_id: int) -> PVTParams:
        row = self.get_pvt_params(pvt_id)
        if not row:
            raise LookupError(pvt_id)
        data = dict(row)
        return PVTParams(
            bank=data["bank"],
            tag=data["tag"],
            fe=data["fe"],
            rs=data["rs"],
            rho_oleo_std=data["rho_oleo_std"],
            rho_gas_std=data["rho_gas_std"],
            rho_agua_std=data["rho_agua_std"],
            temp_ref_c=data.get("temp_ref_c", 20.0),
            pres_ref_bar=data.get("pres_ref_bar", 1.01325),
            gsv_confirmed=bool(data.get("gsv_confirmed", 0)),
            gor_mode=data.get("gor_mode", "unknown"),
            limite_hc_pct=data.get("limite_hc_pct", 5.0),
            limite_total_pct=data.get("limite_total_pct", 5.0),
            limite_agua_pct=data.get("limite_agua_pct", 20.0),
            source=data.get("source", ""),
            author=data.get("author", ""),
            notes=data.get("notes", ""),
            valid_from=data.get("valid_from", ""),
            valid_to=data.get("valid_to", ""),
        )

    def list_sep_hour_rows(self, day_ref: str):
        conn = self._db_conn()
        rows = conn.execute(
            """
            SELECT hour_ref, tag, metric_name, metric_value
            FROM measurements_curated
            WHERE row_kind='sep' AND bank='SEP' AND COALESCE(is_official,1)=1 AND day_ref=?
            ORDER BY hour_ref, tag, metric_name
            """,
            (day_ref,),
        ).fetchall()
        conn.close()
        return rows

    def list_sep_detail_hour_rows(self, day_ref: str):
        conn = self._db_conn()
        rows = conn.execute(
            """
            SELECT row_kind, hour_ref, tag, metric_name, metric_value
            FROM measurements_curated
            WHERE row_kind IN ('sep_oleo_detail','sep_gas_detail','sep_agua_detail')
              AND bank='SEP'
              AND COALESCE(is_official,1)=1
              AND day_ref=?
            ORDER BY hour_ref, row_kind, tag, metric_name
            """,
            (day_ref,),
        ).fetchall()
        conn.close()
        return rows

    def list_mpfm_hour_rows(self, bank: str, tag: str, day_ref: str):
        conn = self._db_conn()
        rows = conn.execute(
            """
            SELECT hour_ref, metric_name, metric_value
            FROM measurements_curated
            WHERE row_kind='hourly' AND bank=? AND tag=? AND day_ref=?
            ORDER BY hour_ref, metric_name
            """,
            (bank, tag, day_ref),
        ).fetchall()
        conn.close()
        return rows

    def list_mpfm_tags(self, bank: str) -> list[str]:
        conn = self._db_conn()
        rows = conn.execute(
            """
            SELECT DISTINCT tag
            FROM measurements_curated
            WHERE row_kind='hourly'
              AND bank=?
              AND COALESCE(tag, '')<>''
            ORDER BY tag
            """,
            (bank,),
        ).fetchall()
        conn.close()
        return [row[0] for row in rows]

    def create_recon_run(self, body: dict, pvt, sep_horas, mpfm_horas, resultados, resumo, hora_to_dict, resumo_to_dict) -> int:
        calc_json = json.dumps([hora_to_dict(item) for item in resultados])
        resumo_json = json.dumps(resumo_to_dict(resumo))
        sep_json = json.dumps(
            [
                {
                    "hora": item.hora,
                    "gsv_sep_sm3": item.gsv_sep_sm3,
                    "agua_gsv_sm3": item.agua_gsv_sm3,
                    "agua_mass_t": item.agua_mass_t,
                    "gas_vol_sm3": item.gas_vol_sm3,
                    "gas_mass_t": item.gas_mass_t,
                    "bsw_user_pct": item.bsw_user_pct,
                    "pressao_barg": item.pressao_barg,
                    "temperatura_c": item.temperatura_c,
                }
                for item in sep_horas
            ]
        )
        mpfm_json = json.dumps(
            [
                {
                    "hora": item.hora,
                    "oleo_corr_t": item.oleo_corr_t,
                    "gas_corr_t": item.gas_corr_t,
                    "agua_corr_t": item.agua_corr_t,
                    "hc_corr_t": item.hc_corr_t,
                    "total_corr_t": item.total_corr_t,
                    "oleo_st_t": item.oleo_st_t,
                    "gas_st_ksm3": item.gas_st_ksm3,
                    "oleo_st_m3": item.oleo_st_m3,
                    "agua_st_m3": item.agua_st_m3,
                    "pressao_barg": item.pressao_barg,
                    "temperatura_c": item.temperatura_c,
                }
                for item in mpfm_horas
            ]
        )
        pvt_snapshot = json.dumps(
            {
                "fe": pvt.fe,
                "rs": pvt.rs,
                "rho_oleo_std": pvt.rho_oleo_std,
                "rho_gas_std": pvt.rho_gas_std,
                "rho_agua_std": pvt.rho_agua_std,
                "gsv_confirmed": pvt.gsv_confirmed,
                "gor_mode": pvt.gor_mode,
                "limite_hc_pct": pvt.limite_hc_pct,
                "limite_total_pct": pvt.limite_total_pct,
            }
        )
        analytical_snapshot = json.dumps(body.get("analytical_snapshot") or {})
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO recon_runs(
                run_at, bank, tag, day_ref, campaign_id, campaign_phase, pvt_params_id, pvt_snapshot, analytical_snapshot,
                sep_hourly_json, mpfm_hourly_json, calc_hourly_json, resumo_json,
                horas_validas, cobertura_pct, status_linha, status_standard, status_final,
                author, notes, test_window_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                now,
                body["bank"],
                body["tag"],
                body["day_ref"],
                body.get("campaign_id"),
                body.get("campaign_phase", "baseline"),
                body["pvt_params_id"],
                pvt_snapshot,
                analytical_snapshot,
                sep_json,
                mpfm_json,
                calc_json,
                resumo_json,
                resumo.horas_validas,
                resumo.cobertura_pct,
                resumo.status_linha,
                resumo.status_standard,
                resumo.status_final,
                body.get("author", ""),
                body.get("notes", ""),
                body.get("test_window_json"),
            ),
        )
        run_id = cur.lastrowid
        conn.commit()
        conn.close()
        return run_id

    def assign_recon_run_campaign(self, run_id: int, campaign_id: int, campaign_phase: str = "baseline") -> None:
        conn = self._db_conn()
        conn.execute(
            "UPDATE recon_runs SET campaign_id=?, campaign_phase=? WHERE id=?",
            (campaign_id, campaign_phase, run_id),
        )
        conn.commit()
        conn.close()

    def create_recon_campaign(self, payload: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO recon_campaigns(
                created_at, updated_at, bank, tag, baseline_day_ref, baseline_run_id, post_day_ref, post_run_id,
                pvt_params_id, pvt_snapshot, analytical_snapshot, sep_alignment_snapshot,
                current_k_factor, proposal_mode, proposal_rule, proposal_status,
                proposed_k_factor_hc, proposed_k_factor_total, proposed_k_factor_selected, proposed_k_factor_manual,
                applied_k_factor, applied_at,
                baseline_desvio_hc_pct, baseline_desvio_total_pct,
                post_desvio_hc_pct, post_desvio_total_pct,
                improvement_hc_pp, improvement_total_pp, monitoring_status,
                author, notes, status
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                now,
                now,
                payload["bank"],
                payload["tag"],
                payload["baseline_day_ref"],
                payload.get("baseline_run_id"),
                payload.get("post_day_ref", ""),
                payload.get("post_run_id"),
                payload.get("pvt_params_id"),
                json.dumps(payload.get("pvt_snapshot") or {}),
                json.dumps(payload.get("analytical_snapshot") or {}),
                json.dumps(payload.get("sep_alignment_snapshot") or {}),
                payload.get("current_k_factor"),
                payload.get("proposal_mode", "hc"),
                payload.get("proposal_rule", "mass_ratio_24h"),
                payload.get("proposal_status", "pending"),
                payload.get("proposed_k_factor_hc"),
                payload.get("proposed_k_factor_total"),
                payload.get("proposed_k_factor_selected"),
                payload.get("proposed_k_factor_manual"),
                payload.get("applied_k_factor"),
                payload.get("applied_at", ""),
                payload.get("baseline_desvio_hc_pct"),
                payload.get("baseline_desvio_total_pct"),
                payload.get("post_desvio_hc_pct"),
                payload.get("post_desvio_total_pct"),
                payload.get("improvement_hc_pp"),
                payload.get("improvement_total_pp"),
                payload.get("monitoring_status", ""),
                payload.get("author", ""),
                payload.get("notes", ""),
                payload.get("status", "baseline"),
            ),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def update_recon_campaign_post_monitor(
        self,
        campaign_id: int,
        *,
        post_day_ref: str,
        post_run_id: int,
        applied_k_factor,
        applied_at: str,
        post_desvio_hc_pct=None,
        post_desvio_total_pct=None,
        improvement_hc_pp=None,
        improvement_total_pp=None,
        monitoring_status: str = "",
        notes: str = "",
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._db_conn()
        conn.execute(
            """
            UPDATE recon_campaigns
            SET post_day_ref=?,
                post_run_id=?,
                applied_k_factor=COALESCE(?, applied_k_factor),
                applied_at=CASE WHEN ?<>'' THEN ? ELSE applied_at END,
                post_desvio_hc_pct=?,
                post_desvio_total_pct=?,
                improvement_hc_pp=?,
                improvement_total_pp=?,
                monitoring_status=?,
                notes=CASE WHEN ?<>'' THEN ? ELSE notes END,
                status='monitoring',
                updated_at=?
            WHERE id=?
            """,
            (
                post_day_ref,
                post_run_id,
                applied_k_factor,
                applied_at or "",
                applied_at or "",
                post_desvio_hc_pct,
                post_desvio_total_pct,
                improvement_hc_pp,
                improvement_total_pp,
                monitoring_status,
                notes or "",
                notes or "",
                now,
                campaign_id,
            ),
        )
        conn.commit()
        conn.close()

    def update_recon_campaign_k_fields(self, campaign_id: int, payload: dict) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        allowed = [
            "current_k_factor",
            "proposal_mode",
            "proposal_rule",
            "proposal_status",
            "proposed_k_factor_hc",
            "proposed_k_factor_total",
            "proposed_k_factor_selected",
            "proposed_k_factor_manual",
            "baseline_desvio_hc_pct",
            "baseline_desvio_total_pct",
            "monitoring_status",
            "status",
            "notes",
        ]
        sets = []
        values = []
        for field in allowed:
            if field in payload:
                sets.append(f"{field}=?")
                values.append(payload[field])
        if not sets:
            return
        sets.append("updated_at=?")
        values.append(now)
        values.append(campaign_id)
        conn = self._db_conn()
        conn.execute(f"UPDATE recon_campaigns SET {', '.join(sets)} WHERE id=?", values)
        conn.commit()
        conn.close()

    def list_recon_campaigns(self, bank: str = "", tag: str = "", limit: int = 50) -> list[dict]:
        conn = self._db_conn()
        sql = """
            SELECT id, created_at, updated_at, bank, tag, baseline_day_ref, post_day_ref,
                   current_k_factor, proposal_mode, proposal_rule, proposal_status,
                   proposed_k_factor_selected, applied_k_factor,
                   baseline_desvio_hc_pct, baseline_desvio_total_pct,
                   post_desvio_hc_pct, post_desvio_total_pct,
                   improvement_hc_pp, improvement_total_pp,
                   monitoring_status, status, author
            FROM recon_campaigns
            WHERE 1=1
        """
        params = []
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def get_recon_campaign(self, campaign_id: int):
        conn = self._db_conn()
        row = conn.execute("SELECT * FROM recon_campaigns WHERE id=?", (campaign_id,)).fetchone()
        conn.close()
        return row

    def list_recon_runs(self, bank: str = "", tag: str = "", limit: int = 50) -> list[dict]:
        conn = self._db_conn()
        sql = "SELECT id,run_at,bank,tag,day_ref,campaign_id,campaign_phase,horas_validas,cobertura_pct,status_linha,status_standard,status_final,author,notes FROM recon_runs WHERE 1=1"
        params = []
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        sql += " ORDER BY run_at DESC LIMIT ?"
        params.append(limit)
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def get_recon_run(self, run_id: int):
        conn = self._db_conn()
        row = conn.execute("SELECT * FROM recon_runs WHERE id=?", (run_id,)).fetchone()
        conn.close()
        return row
