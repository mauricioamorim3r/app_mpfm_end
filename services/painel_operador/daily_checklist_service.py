from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zipfile import ZipFile


class DailyChecklistService:
    """Read and persist the Bacalhau daily checklist workbook without Excel automation."""

    NS = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    TAG_RE = re.compile(r"\b(?:\d{2}[A-Z]{2}\d{4}[A-Z]?|EST[-_]?VENT[-_]?TANK|XML\d{3}|PE\d|PW\s?\d{2,3})\b", re.I)
    KEY_SHEETS = {
        "Ocurrences": {"start": 9, "date": "F", "title": "H", "status": "M", "tag": "G", "domain": "occurrence"},
        "Lab-Report": {"start": 9, "date": "D", "title": "E", "status": "", "tag": "", "domain": "lab_report"},
        "API": {"start": 6, "date": "C", "title": "D", "status": "", "tag": "", "domain": "api_bsw"},
        "Tank ": {"start": 3, "date": "B", "title": "M", "status": "J", "tag": "", "domain": "tank_balance"},
        "Off Spec Tank": {"start": 10, "date": "A", "title": "E", "status": "E", "tag": "", "domain": "offspec_tank"},
        "MPFM Subsea x Fiscal- Óleo": {"start": 6, "date": "X", "title": "Z", "status": "Y", "tag": "", "domain": "mpfm_fiscal_oil"},
        "Balanço de Gás": {"start": 6, "date": "A", "title": "", "status": "", "tag": "", "domain": "gas_balance"},
    }

    def inspect_workbook(self, source_path: str, *, include_rows: bool = False) -> dict[str, Any]:
        path = self._resolve_path(source_path)
        scan = self._scan_workbook(path, include_rows=include_rows)
        critical = [s for s in scan["sheets"] if self._is_default_sheet(s["name"])]
        xml_like = [s for s in scan["sheets"] if ".xml" in s["name"].lower() or s["name"].startswith("XML.")]
        return {
            "source_file": str(path),
            "file_hash": self._file_hash(path),
            "size_bytes": path.stat().st_size,
            "sheet_count": len(scan["sheets"]),
            "critical_sheet_count": len(critical),
            "xml_reference_sheet_count": len(xml_like),
            "sheets": scan["sheets"],
            "coverage": self._coverage_notes(scan["sheets"]),
        }

    def import_workbook(self, db_conn_fn, source_path: str) -> dict[str, Any]:
        path = self._resolve_path(source_path)
        file_hash = self._file_hash(path)

        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            existing = cur.execute(
                """
                SELECT id, source_file, file_hash, imported_at, status, sheet_count,
                       selected_sheet_count, row_count
                FROM painel_operador_daily_checklist_runs
                WHERE file_hash=? AND status='ok'
                ORDER BY id DESC
                LIMIT 1
                """,
                (file_hash,),
            ).fetchone()
            if existing:
                return {
                    "ok": True,
                    "skipped": True,
                    "reason": "same_content",
                    "import_run_id": int(existing["id"]),
                    "source_file": str(path),
                    "file_hash": file_hash,
                    "imported_at": existing["imported_at"],
                    "sheet_count": int(existing["sheet_count"] or 0),
                    "selected_sheet_count": int(existing["selected_sheet_count"] or 0),
                    "rows_inserted": int(existing["row_count"] or 0),
                    "message": "Conteúdo idêntico já importado; nenhuma linha foi duplicada.",
                }

            # The expensive XLSM/XML scan only happens after the cheap hash
            # lookup establishes that this content is new.
            scan = self._scan_workbook(path, include_rows=True, selected_only=True)
            now = self._now()
            selected = [sheet for sheet in scan["sheets"] if self._is_default_sheet(sheet["name"])]
            cur.execute(
                """
                INSERT INTO painel_operador_daily_checklist_runs(
                    source_file, file_hash, imported_at, status, sheet_count,
                    selected_sheet_count, row_count, payload_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    str(path),
                    file_hash,
                    now,
                    "ok",
                    len(scan["sheets"]),
                    len(selected),
                    0,
                    json.dumps(
                        {
                            "size_bytes": path.stat().st_size,
                            "sheets": [
                                {k: v for k, v in s.items() if k != "rows"}
                                for s in scan["sheets"]
                            ],
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            run_id = int(cur.lastrowid)
            rows_inserted = 0
            by_sheet: dict[str, int] = {}
            for sheet in selected:
                headers = self._headers_for_sheet(sheet)
                rows = sheet.get("rows") or []
                start_row = self._sheet_config(sheet["name"]).get("start", 1)
                for row in rows:
                    if int(row["row"]) < int(start_row):
                        continue
                    if not self._has_meaningful_content(row.get("values") or {}):
                        continue
                    parsed = self._parse_record(sheet["name"], row, headers)
                    if not parsed["has_content"]:
                        continue
                    cur.execute(
                        """
                        INSERT INTO painel_operador_daily_checklist_rows(
                            import_run_id, source_file, file_hash, sheet_name, row_number,
                            record_date, record_domain, tag, title, status, responsible,
                            metric_name, metric_value, metric_unit, payload_json, created_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            run_id,
                            str(path),
                            file_hash,
                            sheet["name"],
                            row["row"],
                            parsed["record_date"],
                            parsed["record_domain"],
                            parsed["tag"],
                            parsed["title"],
                            parsed["status"],
                            parsed["responsible"],
                            parsed["metric_name"],
                            parsed["metric_value"],
                            parsed["metric_unit"],
                            json.dumps(parsed["payload"], ensure_ascii=False),
                            now,
                        ),
                    )
                    if sheet["name"] == "Tank ":
                        tank = self._parse_tank_balance(row, parsed, str(path), file_hash, run_id, now)
                        if tank:
                            cur.execute(
                                """
                                INSERT INTO painel_operador_tank_balance(
                                    import_run_id, source_file, file_hash, sheet_name, row_number,
                                    tank_date, opening_gsv_m3, closing_gsv_m3, delta_tank_m3,
                                    fiscal_meter_gsv_m3, fiscal_minus_tank_m3, delta_percent,
                                    chart_percent, measurement_failure, flowline_volume_m3,
                                    reprocessed_oil_gsv_m3, observations, status, payload_json, created_at
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    tank["import_run_id"],
                                    tank["source_file"],
                                    tank["file_hash"],
                                    tank["sheet_name"],
                                    tank["row_number"],
                                    tank["tank_date"],
                                    tank["opening_gsv_m3"],
                                    tank["closing_gsv_m3"],
                                    tank["delta_tank_m3"],
                                    tank["fiscal_meter_gsv_m3"],
                                    tank["fiscal_minus_tank_m3"],
                                    tank["delta_percent"],
                                    tank["chart_percent"],
                                    tank["measurement_failure"],
                                    tank["flowline_volume_m3"],
                                    tank["reprocessed_oil_gsv_m3"],
                                    tank["observations"],
                                    tank["status"],
                                    json.dumps(tank["payload"], ensure_ascii=False),
                                    now,
                                ),
                            )
                    if sheet["name"] == "Off Spec Tank":
                        offspec = self._parse_offspec_tank(row, parsed, str(path), file_hash, run_id, now)
                        if offspec:
                            cur.execute(
                                """
                                INSERT INTO painel_operador_offspec_tank(
                                    import_run_id, source_file, file_hash, sheet_name, row_number,
                                    offspec_date, opening_gsv_m3, closing_gsv_m3, delta_tank_m3,
                                    directed_to_offspec, directed_volume_m3, reprocessed_volume_m3,
                                    status, note, payload_json, created_at
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    offspec["import_run_id"],
                                    offspec["source_file"],
                                    offspec["file_hash"],
                                    offspec["sheet_name"],
                                    offspec["row_number"],
                                    offspec["offspec_date"],
                                    offspec["opening_gsv_m3"],
                                    offspec["closing_gsv_m3"],
                                    offspec["delta_tank_m3"],
                                    offspec["directed_to_offspec"],
                                    offspec["directed_volume_m3"],
                                    offspec["reprocessed_volume_m3"],
                                    offspec["status"],
                                    offspec["note"],
                                    json.dumps(offspec["payload"], ensure_ascii=False),
                                    now,
                                ),
                            )
                    if sheet["name"] == "Lab-Report":
                        lab = self._parse_lab_report(row, parsed, str(path), file_hash, run_id, now)
                        if lab:
                            cur.execute(
                                """
                                INSERT INTO painel_operador_quality_lab_samples(
                                    import_run_id, source_file, file_hash, sheet_name, row_number,
                                    sample_date, lab_report_id, api_gravity, api_deviation,
                                    density_kg_m3, density_cv_g_cm3, bsw_percent,
                                    bsw_flowline_percent, bsw_xml040_percent, method,
                                    blend_manual, status, payload_json, created_at
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    lab["import_run_id"],
                                    lab["source_file"],
                                    lab["file_hash"],
                                    lab["sheet_name"],
                                    lab["row_number"],
                                    lab["sample_date"],
                                    lab["lab_report_id"],
                                    lab["api_gravity"],
                                    lab["api_deviation"],
                                    lab["density_kg_m3"],
                                    lab["density_cv_g_cm3"],
                                    lab["bsw_percent"],
                                    lab["bsw_flowline_percent"],
                                    lab["bsw_xml040_percent"],
                                    lab["method"],
                                    lab["blend_manual"],
                                    lab["status"],
                                    json.dumps(lab["payload"], ensure_ascii=False),
                                    now,
                                ),
                            )
                    if sheet["name"] == "API":
                        api = self._parse_api_weighted(row, parsed, str(path), file_hash, run_id, now)
                        if api:
                            cur.execute(
                                """
                                INSERT INTO painel_operador_api_weighted_daily(
                                    import_run_id, source_file, file_hash, sheet_name, row_number,
                                    api_date, weighted_api, net_volume_m3, api_volume,
                                    weighted_bsw_percent, bsw_volume, total_volume_m3,
                                    status, payload_json, created_at
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    api["import_run_id"],
                                    api["source_file"],
                                    api["file_hash"],
                                    api["sheet_name"],
                                    api["row_number"],
                                    api["api_date"],
                                    api["weighted_api"],
                                    api["net_volume_m3"],
                                    api["api_volume"],
                                    api["weighted_bsw_percent"],
                                    api["bsw_volume"],
                                    api["total_volume_m3"],
                                    api["status"],
                                    json.dumps(api["payload"], ensure_ascii=False),
                                    now,
                                ),
                            )
                    if sheet["name"] == "MPFM Subsea x Fiscal- Óleo":
                        mpfm_oil = self._parse_mpfm_fiscal_oil(row, parsed, str(path), file_hash, run_id, now)
                        if mpfm_oil:
                            cur.execute(
                                """
                                INSERT INTO painel_operador_mpfm_fiscal_oil(
                                    import_run_id, source_file, file_hash, sheet_name, row_number,
                                    production_date, pe4_oil_m3, pe2_bank10_oil_m3,
                                    pe2_bank15_oil_m3, reprocess_oil_m3, total_mpfm_oil_m3,
                                    fiscal_oil_m3, variance_percent, comment, source_status,
                                    status, payload_json, created_at
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    mpfm_oil["import_run_id"],
                                    mpfm_oil["source_file"],
                                    mpfm_oil["file_hash"],
                                    mpfm_oil["sheet_name"],
                                    mpfm_oil["row_number"],
                                    mpfm_oil["production_date"],
                                    mpfm_oil["pe4_oil_m3"],
                                    mpfm_oil["pe2_bank10_oil_m3"],
                                    mpfm_oil["pe2_bank15_oil_m3"],
                                    mpfm_oil["reprocess_oil_m3"],
                                    mpfm_oil["total_mpfm_oil_m3"],
                                    mpfm_oil["fiscal_oil_m3"],
                                    mpfm_oil["variance_percent"],
                                    mpfm_oil["comment"],
                                    mpfm_oil["source_status"],
                                    mpfm_oil["status"],
                                    json.dumps(mpfm_oil["payload"], ensure_ascii=False),
                                    now,
                                ),
                            )
                    if sheet["name"] == "Balanço de Gás":
                        gas = self._parse_gas_balance(row, parsed, str(path), file_hash, run_id, now)
                        if gas:
                            cur.execute(
                                """
                                INSERT INTO painel_operador_gas_balance(
                                    import_run_id, source_file, file_hash, sheet_name, row_number,
                                    gas_date, hp_separator_mm3, test_separator_mm3,
                                    fwko_drum_mm3, first_stage_flash_mm3, second_stage_flash_mm3,
                                    gas_lift_riser_mm3, operational_total_mm3,
                                    gas_injection_riser1_mm3, gas_injection_riser2_mm3,
                                    hp_flare_mm3, igg_mm3, lp_flare_mm3, pilot_mm3,
                                    gtg_mm3, vent_tank_mm3, fiscal_injection_total_mm3,
                                    delta_mm3, delta_percent, comment, status, payload_json, created_at
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    gas["import_run_id"],
                                    gas["source_file"],
                                    gas["file_hash"],
                                    gas["sheet_name"],
                                    gas["row_number"],
                                    gas["gas_date"],
                                    gas["hp_separator_mm3"],
                                    gas["test_separator_mm3"],
                                    gas["fwko_drum_mm3"],
                                    gas["first_stage_flash_mm3"],
                                    gas["second_stage_flash_mm3"],
                                    gas["gas_lift_riser_mm3"],
                                    gas["operational_total_mm3"],
                                    gas["gas_injection_riser1_mm3"],
                                    gas["gas_injection_riser2_mm3"],
                                    gas["hp_flare_mm3"],
                                    gas["igg_mm3"],
                                    gas["lp_flare_mm3"],
                                    gas["pilot_mm3"],
                                    gas["gtg_mm3"],
                                    gas["vent_tank_mm3"],
                                    gas["fiscal_injection_total_mm3"],
                                    gas["delta_mm3"],
                                    gas["delta_percent"],
                                    gas["comment"],
                                    gas["status"],
                                    json.dumps(gas["payload"], ensure_ascii=False),
                                    now,
                                ),
                            )
                    rows_inserted += 1
                    by_sheet[sheet["name"]] = by_sheet.get(sheet["name"], 0) + 1
            cur.execute(
                "UPDATE painel_operador_daily_checklist_runs SET row_count=?, payload_json=? WHERE id=?",
                (
                    rows_inserted,
                    json.dumps({"sheet_rows": by_sheet, "file_hash": file_hash}, ensure_ascii=False),
                    run_id,
                ),
            )
            conn.commit()
            return {"ok": True, "run_id": run_id, "rows": rows_inserted, "sheets": by_sheet, "source_file": str(path)}
        finally:
            conn.close()

    def tank_balance(
        self,
        db_conn_fn,
        *,
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 120,
        offset: int = 0,
    ) -> dict[str, Any]:
        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            latest = cur.execute(
                "SELECT id FROM painel_operador_daily_checklist_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            latest_id = int(latest["id"]) if latest else 0
            where = []
            params: list[Any] = []
            if latest_id:
                where.append("import_run_id=?")
                params.append(latest_id)
            if date_from:
                where.append("tank_date>=?")
                params.append(date_from)
            if date_to:
                where.append("tank_date<=?")
                params.append(date_to)
            if status:
                where.append("status=?")
                params.append(status)
            if q:
                like = f"%{q}%"
                where.append("(observations LIKE ? OR measurement_failure LIKE ? OR payload_json LIKE ?)")
                params.extend([like, like, like])
            where_sql = "WHERE " + " AND ".join(where) if where else ""
            total = cur.execute(f"SELECT COUNT(*) FROM painel_operador_tank_balance {where_sql}", params).fetchone()[0]
            summary_row = cur.execute(
                f"""
                SELECT COUNT(*) AS rows_count,
                       COUNT(DISTINCT tank_date) AS date_count,
                       MIN(tank_date) AS first_date,
                       MAX(tank_date) AS last_date,
                       SUM(COALESCE(delta_tank_m3, 0)) AS total_delta_tank_m3,
                       SUM(COALESCE(fiscal_meter_gsv_m3, 0)) AS total_fiscal_meter_gsv_m3,
                       SUM(COALESCE(fiscal_minus_tank_m3, 0)) AS total_fiscal_minus_tank_m3,
                       MAX(ABS(COALESCE(delta_percent, 0))) AS max_abs_delta_percent,
                       SUM(CASE WHEN status='ok' THEN 0 ELSE 1 END) AS attention_count
                FROM painel_operador_tank_balance
                {where_sql}
                """,
                params,
            ).fetchone()
            rows = cur.execute(
                f"""
                SELECT *
                FROM painel_operador_tank_balance
                {where_sql}
                ORDER BY CASE WHEN tank_date='' THEN 1 ELSE 0 END, tank_date DESC, row_number DESC
                LIMIT ? OFFSET ?
                """,
                params + [self._limit(limit), max(0, int(offset or 0))],
            ).fetchall()
            trend = cur.execute(
                f"""
                SELECT tank_date,
                       SUM(COALESCE(delta_tank_m3, 0)) AS delta_tank_m3,
                       SUM(COALESCE(fiscal_meter_gsv_m3, 0)) AS fiscal_meter_gsv_m3,
                       SUM(COALESCE(fiscal_minus_tank_m3, 0)) AS fiscal_minus_tank_m3,
                       SUM(CASE WHEN status='ok' THEN 0 ELSE 1 END) AS attention_count
                FROM painel_operador_tank_balance
                {where_sql}
                GROUP BY tank_date
                ORDER BY tank_date
                """,
                params,
            ).fetchall()
            return {
                "total": total,
                "returned": len(rows),
                "summary": dict(summary_row) if summary_row else {},
                "trend": [dict(row) for row in trend],
                "items": [dict(row) for row in rows],
            }
        finally:
            conn.close()

    def offspec_tank(
        self,
        db_conn_fn,
        *,
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 120,
        offset: int = 0,
    ) -> dict[str, Any]:
        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            latest = cur.execute(
                "SELECT id FROM painel_operador_daily_checklist_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            latest_id = int(latest["id"]) if latest else 0
            where = []
            params: list[Any] = []
            if latest_id:
                where.append("import_run_id=?")
                params.append(latest_id)
            if date_from:
                where.append("offspec_date>=?")
                params.append(date_from)
            if date_to:
                where.append("offspec_date<=?")
                params.append(date_to)
            if status:
                where.append("status=?")
                params.append(status)
            if q:
                like = f"%{q}%"
                where.append("(note LIKE ? OR directed_to_offspec LIKE ? OR payload_json LIKE ?)")
                params.extend([like, like, like])
            where_sql = "WHERE " + " AND ".join(where) if where else ""
            total = cur.execute(f"SELECT COUNT(*) FROM painel_operador_offspec_tank {where_sql}", params).fetchone()[0]
            summary_row = cur.execute(
                f"""
                SELECT COUNT(*) AS rows_count,
                       COUNT(DISTINCT offspec_date) AS date_count,
                       MIN(offspec_date) AS first_date,
                       MAX(offspec_date) AS last_date,
                       SUM(COALESCE(delta_tank_m3, 0)) AS total_delta_tank_m3,
                       SUM(COALESCE(directed_volume_m3, 0)) AS total_directed_volume_m3,
                       SUM(COALESCE(reprocessed_volume_m3, 0)) AS total_reprocessed_volume_m3,
                       SUM(CASE WHEN status='offspec' THEN 1 ELSE 0 END) AS offspec_days,
                       SUM(CASE WHEN status='reprocesso' THEN 1 ELSE 0 END) AS reprocess_days,
                       SUM(CASE WHEN status='pendente' THEN 1 ELSE 0 END) AS pending_days
                FROM painel_operador_offspec_tank
                {where_sql}
                """,
                params,
            ).fetchone()
            rows = cur.execute(
                f"""
                SELECT *
                FROM painel_operador_offspec_tank
                {where_sql}
                ORDER BY CASE WHEN offspec_date='' THEN 1 ELSE 0 END, offspec_date DESC, row_number DESC
                LIMIT ? OFFSET ?
                """,
                params + [self._limit(limit), max(0, int(offset or 0))],
            ).fetchall()
            trend = cur.execute(
                f"""
                SELECT offspec_date,
                       SUM(COALESCE(directed_volume_m3, 0)) AS directed_volume_m3,
                       SUM(COALESCE(reprocessed_volume_m3, 0)) AS reprocessed_volume_m3,
                       SUM(COALESCE(delta_tank_m3, 0)) AS delta_tank_m3,
                       SUM(CASE WHEN status='offspec' THEN 1 ELSE 0 END) AS offspec_count,
                       SUM(CASE WHEN status='reprocesso' THEN 1 ELSE 0 END) AS reprocess_count
                FROM painel_operador_offspec_tank
                {where_sql}
                GROUP BY offspec_date
                ORDER BY offspec_date
                """,
                params,
            ).fetchall()
            return {
                "total": total,
                "returned": len(rows),
                "summary": dict(summary_row) if summary_row else {},
                "trend": [dict(row) for row in trend],
                "items": [dict(row) for row in rows],
            }
        finally:
            conn.close()

    def quality_samples(
        self,
        db_conn_fn,
        *,
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 160,
        offset: int = 0,
    ) -> dict[str, Any]:
        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            latest = cur.execute(
                "SELECT id FROM painel_operador_daily_checklist_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            latest_id = int(latest["id"]) if latest else 0
            where = []
            params: list[Any] = []
            if latest_id:
                where.append("import_run_id=?")
                params.append(latest_id)
            if date_from:
                where.append("sample_date>=?")
                params.append(date_from)
            if date_to:
                where.append("sample_date<=?")
                params.append(date_to)
            if status:
                where.append("status=?")
                params.append(status)
            if q:
                like = f"%{q}%"
                where.append("(lab_report_id LIKE ? OR method LIKE ? OR payload_json LIKE ?)")
                params.extend([like, like, like])
            where_sql = "WHERE " + " AND ".join(where) if where else ""
            total = cur.execute(f"SELECT COUNT(*) FROM painel_operador_quality_lab_samples {where_sql}", params).fetchone()[0]
            summary_row = cur.execute(
                f"""
                SELECT COUNT(*) AS rows_count,
                       COUNT(DISTINCT sample_date) AS date_count,
                       MIN(sample_date) AS first_date,
                       MAX(sample_date) AS last_date,
                       AVG(api_gravity) AS avg_api_gravity,
                       MIN(api_gravity) AS min_api_gravity,
                       MAX(api_gravity) AS max_api_gravity,
                       AVG(density_kg_m3) AS avg_density_kg_m3,
                       AVG(bsw_percent) AS avg_bsw_percent,
                       MAX(bsw_percent) AS max_bsw_percent,
                       SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) AS ok_count,
                       SUM(CASE WHEN status='atenção' THEN 1 ELSE 0 END) AS attention_count,
                       SUM(CASE WHEN status='pendente' THEN 1 ELSE 0 END) AS pending_count
                FROM painel_operador_quality_lab_samples
                {where_sql}
                """,
                params,
            ).fetchone()
            rows = cur.execute(
                f"""
                SELECT *
                FROM painel_operador_quality_lab_samples
                {where_sql}
                ORDER BY CASE WHEN sample_date='' THEN 1 ELSE 0 END, sample_date DESC, row_number DESC
                LIMIT ? OFFSET ?
                """,
                params + [self._limit(limit), max(0, int(offset or 0))],
            ).fetchall()
            trend = cur.execute(
                f"""
                SELECT sample_date,
                       AVG(api_gravity) AS api_gravity,
                       AVG(density_kg_m3) AS density_kg_m3,
                       AVG(bsw_percent) AS bsw_percent,
                       COUNT(*) AS sample_count,
                       SUM(CASE WHEN status='atenção' THEN 1 ELSE 0 END) AS attention_count
                FROM painel_operador_quality_lab_samples
                {where_sql}
                GROUP BY sample_date
                ORDER BY sample_date
                """,
                params,
            ).fetchall()
            api_rows = cur.execute(
                """
                SELECT *
                FROM painel_operador_api_weighted_daily
                WHERE import_run_id=?
                ORDER BY CASE WHEN api_date='' THEN 1 ELSE 0 END, api_date DESC, row_number DESC
                LIMIT 120
                """,
                (latest_id,),
            ).fetchall() if latest_id else []
            api_summary = cur.execute(
                """
                SELECT COUNT(*) AS rows_count,
                       COUNT(DISTINCT api_date) AS date_count,
                       MIN(api_date) AS first_date,
                       MAX(api_date) AS last_date,
                       AVG(weighted_api) AS avg_weighted_api,
                       AVG(weighted_bsw_percent) AS avg_weighted_bsw_percent,
                       SUM(COALESCE(total_volume_m3, 0)) AS total_volume_m3
                FROM painel_operador_api_weighted_daily
                WHERE import_run_id=?
                """,
                (latest_id,),
            ).fetchone() if latest_id else None
            return {
                "total": total,
                "returned": len(rows),
                "summary": dict(summary_row) if summary_row else {},
                "trend": [dict(row) for row in trend],
                "items": [dict(row) for row in rows],
                "api_weighted": {
                    "summary": dict(api_summary) if api_summary else {},
                    "items": [dict(row) for row in api_rows],
                },
            }
        finally:
            conn.close()

    def mpfm_fiscal_oil(
        self,
        db_conn_fn,
        *,
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 160,
        offset: int = 0,
    ) -> dict[str, Any]:
        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            latest = cur.execute(
                "SELECT id FROM painel_operador_daily_checklist_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            latest_id = int(latest["id"]) if latest else 0
            where = []
            params: list[Any] = []
            # Filtrar por import_run_id apenas se não houver filtro de data
            # Isso permite buscar dados de múltiplas importações quando necessário
            if latest_id and not date_from and not date_to:
                where.append("import_run_id=?")
                params.append(latest_id)
            if date_from:
                where.append("production_date>=?")
                params.append(date_from)
            if date_to:
                where.append("production_date<=?")
                params.append(date_to)
            if status:
                where.append("status=?")
                params.append(status)
            if q:
                like = f"%{q}%"
                where.append("(comment LIKE ? OR source_status LIKE ? OR payload_json LIKE ?)")
                params.extend([like, like, like])
            where_sql = "WHERE " + " AND ".join(where) if where else ""
            total = cur.execute(f"SELECT COUNT(*) FROM painel_operador_mpfm_fiscal_oil {where_sql}", params).fetchone()[0]
            summary_row = cur.execute(
                f"""
                SELECT COUNT(*) AS rows_count,
                       COUNT(DISTINCT production_date) AS date_count,
                       MIN(production_date) AS first_date,
                       MAX(production_date) AS last_date,
                       SUM(COALESCE(total_mpfm_oil_m3, 0)) AS total_mpfm_oil_m3,
                       SUM(COALESCE(fiscal_oil_m3, 0)) AS total_fiscal_oil_m3,
                       SUM(COALESCE(reprocess_oil_m3, 0)) AS total_reprocess_oil_m3,
                       AVG(variance_percent) AS avg_variance_percent,
                       MAX(ABS(COALESCE(variance_percent, 0))) AS max_abs_variance_percent,
                       SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) AS ok_count,
                       SUM(CASE WHEN status='atenção' THEN 1 ELSE 0 END) AS attention_count,
                       SUM(CASE WHEN status='pendente' THEN 1 ELSE 0 END) AS pending_count,
                       SUM(CASE WHEN status='falha' THEN 1 ELSE 0 END) AS failure_count
                FROM painel_operador_mpfm_fiscal_oil
                {where_sql}
                """,
                params,
            ).fetchone()
            rows = cur.execute(
                f"""
                SELECT *
                FROM painel_operador_mpfm_fiscal_oil
                {where_sql}
                ORDER BY CASE WHEN production_date='' THEN 1 ELSE 0 END, production_date DESC, row_number DESC
                LIMIT ? OFFSET ?
                """,
                params + [self._limit(limit), max(0, int(offset or 0))],
            ).fetchall()
            trend = cur.execute(
                f"""
                SELECT production_date,
                       SUM(COALESCE(total_mpfm_oil_m3, 0)) AS total_mpfm_oil_m3,
                       SUM(COALESCE(fiscal_oil_m3, 0)) AS fiscal_oil_m3,
                       SUM(COALESCE(reprocess_oil_m3, 0)) AS reprocess_oil_m3,
                       AVG(variance_percent) AS variance_percent,
                       SUM(CASE WHEN status='ok' THEN 0 ELSE 1 END) AS attention_count
                FROM painel_operador_mpfm_fiscal_oil
                {where_sql}
                GROUP BY production_date
                ORDER BY production_date
                """,
                params,
            ).fetchall()
            return {
                "total": total,
                "returned": len(rows),
                "summary": dict(summary_row) if summary_row else {},
                "trend": [dict(row) for row in trend],
                "items": [dict(row) for row in rows],
            }
        finally:
            conn.close()

    def gas_balance(
        self,
        db_conn_fn,
        *,
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 160,
        offset: int = 0,
    ) -> dict[str, Any]:
        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            latest = cur.execute(
                "SELECT id FROM painel_operador_daily_checklist_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            latest_id = int(latest["id"]) if latest else 0
            where = []
            params: list[Any] = []
            if latest_id:
                where.append("import_run_id=?")
                params.append(latest_id)
            if date_from:
                where.append("gas_date>=?")
                params.append(date_from)
            if date_to:
                where.append("gas_date<=?")
                params.append(date_to)
            if status:
                where.append("status=?")
                params.append(status)
            if q:
                like = f"%{q}%"
                where.append("(payload_json LIKE ?)")
                params.append(like)
            where_sql = "WHERE " + " AND ".join(where) if where else ""
            total = cur.execute(f"SELECT COUNT(*) FROM painel_operador_gas_balance {where_sql}", params).fetchone()[0]
            summary_row = cur.execute(
                f"""
                SELECT COUNT(*) AS rows_count,
                       COUNT(DISTINCT gas_date) AS date_count,
                       MIN(gas_date) AS first_date,
                       MAX(gas_date) AS last_date,
                       SUM(COALESCE(operational_total_mm3, 0)) AS total_operational_mm3,
                       SUM(COALESCE(fiscal_injection_total_mm3, 0)) AS total_fiscal_injection_mm3,
                       SUM(COALESCE(delta_mm3, 0)) AS total_delta_mm3,
                       AVG(delta_percent) AS avg_delta_percent,
                       MAX(ABS(COALESCE(delta_percent, 0))) AS max_abs_delta_percent,
                       SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) AS ok_count,
                       SUM(CASE WHEN status='atenção' THEN 1 ELSE 0 END) AS attention_count,
                       SUM(CASE WHEN status='pendente' THEN 1 ELSE 0 END) AS pending_count
                FROM painel_operador_gas_balance
                {where_sql}
                """,
                params,
            ).fetchone()
            rows = cur.execute(
                f"""
                SELECT *
                FROM painel_operador_gas_balance
                {where_sql}
                ORDER BY CASE WHEN gas_date='' THEN 1 ELSE 0 END, gas_date DESC, row_number DESC
                LIMIT ? OFFSET ?
                """,
                params + [self._limit(limit), max(0, int(offset or 0))],
            ).fetchall()
            trend = cur.execute(
                f"""
                SELECT gas_date,
                       SUM(COALESCE(operational_total_mm3, 0)) AS operational_total_mm3,
                       SUM(COALESCE(fiscal_injection_total_mm3, 0)) AS fiscal_injection_total_mm3,
                       SUM(COALESCE(delta_mm3, 0)) AS delta_mm3,
                       AVG(delta_percent) AS delta_percent,
                       SUM(CASE WHEN status='ok' THEN 0 ELSE 1 END) AS attention_count
                FROM painel_operador_gas_balance
                {where_sql}
                GROUP BY gas_date
                ORDER BY gas_date
                """,
                params,
            ).fetchall()
            return {
                "total": total,
                "returned": len(rows),
                "summary": dict(summary_row) if summary_row else {},
                "trend": [dict(row) for row in trend],
                "items": [dict(row) for row in rows],
            }
        finally:
            conn.close()

    def summary(self, db_conn_fn) -> dict[str, Any]:
        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            latest = cur.execute(
                """
                SELECT *
                FROM painel_operador_daily_checklist_runs
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            latest_id = int(latest["id"]) if latest else 0
            sheets = cur.execute(
                """
                SELECT sheet_name, COUNT(*) AS rows_count,
                       COUNT(DISTINCT record_date) AS date_count,
                       MIN(record_date) AS first_date,
                       MAX(record_date) AS last_date
                FROM painel_operador_daily_checklist_rows
                WHERE import_run_id=?
                GROUP BY sheet_name
                ORDER BY rows_count DESC, sheet_name
                """,
                (latest_id,),
            ).fetchall() if latest_id else []
            totals = {
                "runs": cur.execute("SELECT COUNT(*) FROM painel_operador_daily_checklist_runs").fetchone()[0],
                "rows": int(latest["row_count"] or 0) if latest else 0,
                "all_rows": cur.execute("SELECT COUNT(*) FROM painel_operador_daily_checklist_rows").fetchone()[0],
            }
            return {
                "latest_run": dict(latest) if latest else None,
                "totals": totals,
                "sheets": [dict(row) for row in sheets],
            }
        finally:
            conn.close()

    def list_rows(
        self,
        db_conn_fn,
        *,
        sheet_name: str = "",
        date_from: str = "",
        date_to: str = "",
        tag: str = "",
        q: str = "",
        limit: int = 120,
        offset: int = 0,
    ) -> dict[str, Any]:
        conn = db_conn_fn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        self._ensure_tables(cur)
        try:
            where = []
            params: list[Any] = []
            if sheet_name:
                where.append("sheet_name=?")
                params.append(sheet_name)
            if date_from:
                where.append("record_date>=?")
                params.append(date_from)
            if date_to:
                where.append("record_date<=?")
                params.append(date_to)
            if tag:
                where.append("tag=?")
                params.append(tag)
            if q:
                like = f"%{q}%"
                where.append("(title LIKE ? OR status LIKE ? OR responsible LIKE ? OR payload_json LIKE ?)")
                params.extend([like, like, like, like])
            latest = cur.execute(
                "SELECT id FROM painel_operador_daily_checklist_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if latest:
                where.append("import_run_id=?")
                params.append(int(latest["id"]))
            where_sql = "WHERE " + " AND ".join(where) if where else ""
            total = cur.execute(
                f"SELECT COUNT(*) FROM painel_operador_daily_checklist_rows {where_sql}",
                params,
            ).fetchone()[0]
            rows = cur.execute(
                f"""
                SELECT *
                FROM painel_operador_daily_checklist_rows
                {where_sql}
                ORDER BY CASE WHEN record_date='' THEN 1 ELSE 0 END, record_date DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                params + [self._limit(limit), max(0, int(offset or 0))],
            ).fetchall()
            return {"total": total, "returned": len(rows), "items": [dict(row) for row in rows]}
        finally:
            conn.close()

    def _scan_workbook(self, path: Path, *, include_rows: bool, selected_only: bool = False) -> dict[str, Any]:
        with ZipFile(path) as zf:
            shared = self._shared_strings(zf)
            sheet_paths = self._sheet_paths(zf)
            sheets = []
            for name, sheet_path in sheet_paths.items():
                if selected_only and not self._is_default_sheet(name):
                    sheets.append({
                        "name": name,
                        "dimension": "",
                        "non_empty_cells": 0,
                        "formula_cells": 0,
                        "max_row": 0,
                        "max_col": 0,
                        "default_import": False,
                        "header_candidates": [],
                    })
                    continue
                root = ET.fromstring(zf.read(sheet_path))
                dim = root.find("main:dimension", self.NS)
                rows = []
                non_empty_cells = 0
                formulas = 0
                max_row = 0
                max_col = 0
                for row_el in root.findall(".//main:sheetData/main:row", self.NS):
                    row_num = int(row_el.get("r", "0") or 0)
                    values: dict[str, str] = {}
                    for cell in row_el.findall("main:c", self.NS):
                        ref = cell.get("r") or ""
                        value = self._cell_value(cell, shared)
                        if cell.find("main:f", self.NS) is not None:
                            formulas += 1
                        if value != "":
                            col = self._cell_col(ref)
                            values[col] = value
                            non_empty_cells += 1
                            max_row = max(max_row, row_num)
                            max_col = max(max_col, self._col_to_idx(col))
                    if values:
                        rows.append({"row": row_num, "values": values})
                header_candidates = self._header_candidates(rows)
                sheet = {
                    "name": name,
                    "dimension": dim.get("ref") if dim is not None else "",
                    "non_empty_cells": non_empty_cells,
                    "formula_cells": formulas,
                    "max_row": max_row,
                    "max_col": max_col,
                    "default_import": self._is_default_sheet(name),
                    "header_candidates": header_candidates,
                }
                if include_rows:
                    sheet["rows"] = rows
                sheets.append(sheet)
            return {"sheets": sheets}

    def _shared_strings(self, zf: ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in zf.namelist():
            return []
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        out = []
        for item in root.findall("main:si", self.NS):
            out.append(self._clean("".join(t.text or "" for t in item.findall(".//main:t", self.NS))))
        return out

    def _sheet_paths(self, zf: ZipFile) -> dict[str, str]:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {rel.get("Id"): rel.get("Target") for rel in rels.findall("rel:Relationship", self.NS)}
        out = {}
        for sheet in wb.findall(".//main:sheet", self.NS):
            rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rid_to_target.get(rid, "")
            out[sheet.get("name") or ""] = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
        return out

    def _cell_value(self, cell, shared: list[str]) -> str:
        cell_type = cell.get("t")
        if cell_type == "inlineStr":
            return self._clean("".join(t.text or "" for t in cell.findall(".//main:t", self.NS)))
        value = cell.find("main:v", self.NS)
        formula = cell.find("main:f", self.NS)
        if value is None:
            return self._clean("=" + (formula.text or "")) if formula is not None and formula.text else ""
        raw = value.text or ""
        if cell_type == "s":
            try:
                return shared[int(raw)]
            except Exception:
                return raw
        return self._clean(raw)

    def _parse_record(self, sheet_name: str, row: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        cfg = self._sheet_config(sheet_name)
        values = row.get("values") or {}
        payload = {
            "headers": headers,
            "values": values,
        }
        title = self._pick(values, cfg.get("title")) or self._first_text(values)
        status = self._pick(values, cfg.get("status"))
        record_date = self._excel_date(self._pick(values, cfg.get("date"))) or self._first_date(values)
        tag = self._pick(values, cfg.get("tag")) or self._first_tag(values)
        responsible = values.get("J") if sheet_name == "Ocurrences" else ""
        metric_value, metric_unit = self._first_numeric(values)
        return {
            "has_content": bool(values),
            "record_date": record_date,
            "record_domain": cfg.get("domain", self._domain_for_sheet(sheet_name)),
            "tag": tag,
            "title": title,
            "status": status,
            "responsible": responsible,
            "metric_name": self._metric_name(sheet_name, headers, values),
            "metric_value": metric_value,
            "metric_unit": metric_unit,
            "payload": payload,
        }

    def _parse_tank_balance(
        self,
        row: dict[str, Any],
        parsed: dict[str, Any],
        source_file: str,
        file_hash: str,
        run_id: int,
        now: str,
    ) -> dict[str, Any] | None:
        values = row.get("values") or {}
        tank_date = self._excel_date(values.get("B", "")) or parsed.get("record_date") or ""
        opening = self._parse_decimal(values.get("C"))
        closing = self._parse_decimal(values.get("D"))
        delta_tank = self._parse_decimal(values.get("E"))
        fiscal_meter = self._parse_decimal(values.get("F"))
        fiscal_minus_tank = self._parse_decimal(values.get("G"))
        delta_percent = self._parse_decimal(values.get("H"))
        chart_percent = self._parse_decimal(values.get("I"))
        failure = self._clean(values.get("J", ""))
        flowline_volume = self._parse_decimal(values.get("K"))
        reprocessed_oil = self._parse_decimal(values.get("L"))
        observations = self._clean(values.get("M", ""))
        if not any(
            value not in (None, "")
            for value in [tank_date, opening, closing, delta_tank, fiscal_meter, fiscal_minus_tank, failure, observations]
        ):
            return None
        status = self._tank_status(tank_date, fiscal_meter, delta_tank, fiscal_minus_tank, delta_percent, failure, observations)
        return {
            "import_run_id": run_id,
            "source_file": source_file,
            "file_hash": file_hash,
            "sheet_name": "Tank ",
            "row_number": int(row.get("row") or 0),
            "tank_date": tank_date,
            "opening_gsv_m3": opening,
            "closing_gsv_m3": closing,
            "delta_tank_m3": delta_tank,
            "fiscal_meter_gsv_m3": fiscal_meter,
            "fiscal_minus_tank_m3": fiscal_minus_tank,
            "delta_percent": delta_percent,
            "chart_percent": chart_percent,
            "measurement_failure": failure,
            "flowline_volume_m3": flowline_volume,
            "reprocessed_oil_gsv_m3": reprocessed_oil,
            "observations": observations,
            "status": status,
            "payload": {
                "values": values,
                "parsed_at": now,
                "source_row": row.get("row"),
            },
        }

    def _parse_offspec_tank(
        self,
        row: dict[str, Any],
        parsed: dict[str, Any],
        source_file: str,
        file_hash: str,
        run_id: int,
        now: str,
    ) -> dict[str, Any] | None:
        values = row.get("values") or {}
        offspec_date = self._excel_date(values.get("A", "")) or parsed.get("record_date") or ""
        opening = self._parse_decimal(values.get("B"))
        closing = self._parse_decimal(values.get("C"))
        delta_tank = self._parse_decimal(values.get("D"))
        directed = self._clean(values.get("E", ""))
        if not any(value not in (None, "") for value in [offspec_date, opening, closing, delta_tank, directed]):
            return None
        status = self._offspec_status(offspec_date, delta_tank, directed)
        directed_volume = delta_tank if status == "offspec" and delta_tank is not None and delta_tank > 0 else None
        reprocessed_volume = abs(delta_tank) if status == "reprocesso" and delta_tank is not None else None
        return {
            "import_run_id": run_id,
            "source_file": source_file,
            "file_hash": file_hash,
            "sheet_name": "Off Spec Tank",
            "row_number": int(row.get("row") or 0),
            "offspec_date": offspec_date,
            "opening_gsv_m3": opening,
            "closing_gsv_m3": closing,
            "delta_tank_m3": delta_tank,
            "directed_to_offspec": directed,
            "directed_volume_m3": directed_volume,
            "reprocessed_volume_m3": reprocessed_volume,
            "status": status,
            "note": directed,
            "payload": {
                "values": values,
                "parsed_at": now,
                "source_row": row.get("row"),
            },
        }

    def _offspec_status(self, offspec_date: str, delta_tank: float | None, directed: str) -> str:
        normalized = directed.lower().strip()
        if normalized.startswith("sim"):
            return "offspec"
        if "reprocess" in normalized:
            return "reprocesso"
        if normalized.startswith("não") or normalized.startswith("nao"):
            return "ok"
        if not offspec_date or delta_tank is None:
            return "pendente"
        if abs(delta_tank) <= 0.001:
            return "ok"
        return "pendente"

    def _parse_lab_report(
        self,
        row: dict[str, Any],
        parsed: dict[str, Any],
        source_file: str,
        file_hash: str,
        run_id: int,
        now: str,
    ) -> dict[str, Any] | None:
        values = row.get("values") or {}
        lab_report_id = self._clean(values.get("E", ""))
        sample_date = self._excel_date(values.get("D", "")) or self._date_from_lab_report_id(lab_report_id) or parsed.get("record_date") or ""
        api_gravity = self._parse_decimal(values.get("F"))
        api_deviation = self._parse_decimal(values.get("G"))
        density = self._parse_decimal(values.get("H"))
        density_cv = self._parse_decimal(values.get("I"))
        bsw = self._parse_decimal(values.get("J"))
        bsw_flowline = self._parse_decimal(values.get("K"))
        bsw_xml040 = self._parse_decimal(values.get("M"))
        method = self._clean(values.get("L", ""))
        blend_manual = self._clean(values.get("AE", ""))
        if not any(value not in (None, "") for value in [sample_date, lab_report_id, api_gravity, density, bsw]):
            return None
        status = self._lab_status(sample_date, api_gravity, density, bsw)
        return {
            "import_run_id": run_id,
            "source_file": source_file,
            "file_hash": file_hash,
            "sheet_name": "Lab-Report",
            "row_number": int(row.get("row") or 0),
            "sample_date": sample_date,
            "lab_report_id": lab_report_id,
            "api_gravity": api_gravity,
            "api_deviation": api_deviation,
            "density_kg_m3": density,
            "density_cv_g_cm3": density_cv,
            "bsw_percent": bsw,
            "bsw_flowline_percent": bsw_flowline,
            "bsw_xml040_percent": bsw_xml040,
            "method": method,
            "blend_manual": blend_manual,
            "status": status,
            "payload": {
                "values": values,
                "parsed_at": now,
                "source_row": row.get("row"),
            },
        }

    def _parse_api_weighted(
        self,
        row: dict[str, Any],
        parsed: dict[str, Any],
        source_file: str,
        file_hash: str,
        run_id: int,
        now: str,
    ) -> dict[str, Any] | None:
        values = row.get("values") or {}
        api_date = self._excel_date(values.get("C", "")) or self._excel_date(values.get("J", "")) or parsed.get("record_date") or ""
        weighted_api = self._parse_decimal(values.get("D"))
        net_volume = self._parse_decimal(values.get("E"))
        api_volume = self._parse_decimal(values.get("F"))
        weighted_bsw = self._parse_decimal(values.get("G"))
        bsw_volume = self._parse_decimal(values.get("H"))
        total_volume = self._parse_decimal(values.get("O"))
        if not any(value not in (None, "") for value in [api_date, weighted_api, net_volume, weighted_bsw, total_volume]):
            return None
        status = "ok" if api_date and any(value not in (None, 0) for value in [weighted_api, net_volume, weighted_bsw, total_volume]) else "pendente"
        return {
            "import_run_id": run_id,
            "source_file": source_file,
            "file_hash": file_hash,
            "sheet_name": "API",
            "row_number": int(row.get("row") or 0),
            "api_date": api_date,
            "weighted_api": weighted_api,
            "net_volume_m3": net_volume,
            "api_volume": api_volume,
            "weighted_bsw_percent": weighted_bsw,
            "bsw_volume": bsw_volume,
            "total_volume_m3": total_volume,
            "status": status,
            "payload": {
                "values": values,
                "parsed_at": now,
                "source_row": row.get("row"),
            },
        }

    def _parse_mpfm_fiscal_oil(
        self,
        row: dict[str, Any],
        parsed: dict[str, Any],
        source_file: str,
        file_hash: str,
        run_id: int,
        now: str,
    ) -> dict[str, Any] | None:
        values = row.get("values") or {}
        production_date = (
            self._excel_date(values.get("X", ""))
            or self._excel_date(values.get("U", ""))
            or ""
        )
        pe4_oil = self._parse_decimal(values.get("B"))
        pe2_bank10_oil = self._parse_decimal(values.get("G"))
        pe2_bank15_oil = self._parse_decimal(values.get("L"))
        reprocess_oil = self._parse_decimal(values.get("Q"))
        total_mpfm_oil = self._parse_decimal(values.get("S"))
        fiscal_oil = self._parse_decimal(values.get("V"))
        variance = self._parse_decimal(values.get("Y"))
        comment = self._clean(values.get("Z", ""))
        source_values = [values.get(col, "") for col in ["B", "G", "L", "S", "Y"]]
        source_status = self._mpfm_source_status(source_values)
        if total_mpfm_oil is None:
            mpfm_parts = [pe4_oil, pe2_bank10_oil, pe2_bank15_oil]
            numeric_parts = [value for value in mpfm_parts if value is not None]
            if numeric_parts:
                total_mpfm_oil = sum(numeric_parts) + (reprocess_oil or 0)
        if variance is None and total_mpfm_oil is not None and fiscal_oil not in (None, 0):
            variance = ((total_mpfm_oil / fiscal_oil) - 1) * 100
        has_comparison_area = bool(values.get("U") or values.get("V") or values.get("X") or values.get("Y") or values.get("Z"))
        if not has_comparison_area or not any(
            value not in (None, "")
            for value in [production_date, total_mpfm_oil, reprocess_oil, fiscal_oil, variance, comment]
        ):
            return None
        status = self._mpfm_fiscal_oil_status(
            production_date=production_date,
            total_mpfm_oil=total_mpfm_oil,
            fiscal_oil=fiscal_oil,
            variance=variance,
            comment=comment,
            source_status=source_status,
        )
        return {
            "import_run_id": run_id,
            "source_file": source_file,
            "file_hash": file_hash,
            "sheet_name": "MPFM Subsea x Fiscal- Óleo",
            "row_number": int(row.get("row") or 0),
            "production_date": production_date,
            "pe4_oil_m3": pe4_oil,
            "pe2_bank10_oil_m3": pe2_bank10_oil,
            "pe2_bank15_oil_m3": pe2_bank15_oil,
            "reprocess_oil_m3": reprocess_oil,
            "total_mpfm_oil_m3": total_mpfm_oil,
            "fiscal_oil_m3": fiscal_oil,
            "variance_percent": variance,
            "comment": comment,
            "source_status": source_status,
            "status": status,
            "payload": {
                "values": values,
                "parsed_at": now,
                "source_row": row.get("row"),
                "source_status": source_status,
            },
        }

    def _mpfm_source_status(self, values: list[Any]) -> str:
        text = " ".join(str(value or "") for value in values).lower()
        if "no such host" in text or "[11001]" in text:
            return "erro_pi"
        if "#value" in text or "#ref" in text or "#div/0" in text:
            return "formula_sem_valor"
        if any(self._parse_decimal(value) is not None for value in values):
            return "numerico"
        return "sem_valor"

    def _mpfm_fiscal_oil_status(
        self,
        *,
        production_date: str,
        total_mpfm_oil: float | None,
        fiscal_oil: float | None,
        variance: float | None,
        comment: str,
        source_status: str,
    ) -> str:
        normalized_comment = comment.strip().lower()
        if source_status == "erro_pi":
            return "falha"
        if not production_date or total_mpfm_oil is None or fiscal_oil is None:
            return "pendente"
        if normalized_comment and normalized_comment not in {"-", "0", "0.0", "ok"}:
            return "atenção"
        if variance is not None and abs(variance) > 5:
            return "atenção"
        return "ok"

    def _parse_gas_balance(
        self,
        row: dict[str, Any],
        parsed: dict[str, Any],
        source_file: str,
        file_hash: str,
        run_id: int,
        now: str,
    ) -> dict[str, Any] | None:
        values = row.get("values") or {}
        if int(row.get("row") or 0) < 202:
            return None
        gas_date = self._excel_date(values.get("A", "")) or parsed.get("record_date") or ""
        hp_separator = self._parse_decimal(values.get("B"))
        test_separator = self._parse_decimal(values.get("C"))
        fwko_drum = self._parse_decimal(values.get("D"))
        first_stage = None
        second_stage = None
        gas_lift_riser = None
        operational_total = self._parse_decimal(values.get("E"))
        injection_riser1 = self._parse_decimal(values.get("F"))
        injection_riser2 = self._parse_decimal(values.get("G"))
        hp_flare = None
        igg = None
        lp_flare = None
        pilot = None
        gtg = None
        vent_tank = None
        fiscal_total = self._parse_decimal(values.get("H"))
        sheet_delta = self._parse_decimal(values.get("I"))
        comment = self._clean(values.get("K", ""))
        if operational_total is None:
            parts = [hp_separator, test_separator, fwko_drum, first_stage, second_stage, gas_lift_riser]
            numeric = [value for value in parts if value is not None]
            operational_total = sum(numeric) if numeric else None
        if fiscal_total is None:
            parts = [injection_riser1, injection_riser2, hp_flare, igg, lp_flare, pilot, gtg, vent_tank]
            numeric = [value for value in parts if value is not None]
            fiscal_total = sum(numeric) if numeric else None
        if operational_total is None and fiscal_total is None and not comment:
            return None
        if not any(value not in (None, "") for value in [gas_date, operational_total, fiscal_total, comment]):
            return None
        delta = None
        delta_percent = None
        if operational_total is not None and fiscal_total is not None:
            delta = sheet_delta if sheet_delta is not None else operational_total - fiscal_total
            base = max(abs(operational_total), abs(fiscal_total), 1)
            delta_percent = (delta / base) * 100
        status = self._gas_balance_status(gas_date, operational_total, fiscal_total, delta_percent, comment)
        return {
            "import_run_id": run_id,
            "source_file": source_file,
            "file_hash": file_hash,
            "sheet_name": "Balanço de Gás",
            "row_number": int(row.get("row") or 0),
            "gas_date": gas_date,
            "hp_separator_mm3": hp_separator,
            "test_separator_mm3": test_separator,
            "fwko_drum_mm3": fwko_drum,
            "first_stage_flash_mm3": first_stage,
            "second_stage_flash_mm3": second_stage,
            "gas_lift_riser_mm3": gas_lift_riser,
            "operational_total_mm3": operational_total,
            "gas_injection_riser1_mm3": injection_riser1,
            "gas_injection_riser2_mm3": injection_riser2,
            "hp_flare_mm3": hp_flare,
            "igg_mm3": igg,
            "lp_flare_mm3": lp_flare,
            "pilot_mm3": pilot,
            "gtg_mm3": gtg,
            "vent_tank_mm3": vent_tank,
            "fiscal_injection_total_mm3": fiscal_total,
            "delta_mm3": delta,
            "delta_percent": delta_percent,
            "comment": comment,
            "status": status,
            "payload": {
                "values": values,
                "parsed_at": now,
                "source_row": row.get("row"),
            },
        }

    def _gas_balance_status(
        self,
        gas_date: str,
        operational_total: float | None,
        fiscal_total: float | None,
        delta_percent: float | None,
        comment: str = "",
    ) -> str:
        if not gas_date or operational_total is None or fiscal_total is None:
            return "pendente"
        if operational_total == 0 and fiscal_total == 0:
            return "ok"
        normalized_comment = comment.strip().lower()
        if normalized_comment and normalized_comment not in {"-", "0", "0.0", "ok"}:
            return "atenção"
        if delta_percent is not None and abs(delta_percent) > 10:
            return "atenção"
        return "ok"

    def _lab_status(self, sample_date: str, api_gravity: float | None, density: float | None, bsw: float | None) -> str:
        if not sample_date or api_gravity is None or density is None or bsw is None:
            return "pendente"
        if bsw > 1.0 or api_gravity < 20 or api_gravity > 45 or density < 700 or density > 1000:
            return "atenção"
        return "ok"

    def _date_from_lab_report_id(self, value: str) -> str:
        match = re.search(r"(20\d{2})[-_](\d{2})[-_](\d{2})", str(value or ""))
        if not match:
            return ""
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"

    def _tank_status(
        self,
        tank_date: str,
        fiscal_meter: float | None,
        delta_tank: float | None,
        fiscal_minus_tank: float | None,
        delta_percent: float | None,
        failure: str,
        observations: str,
    ) -> str:
        if not tank_date or fiscal_meter is None or delta_tank is None:
            return "pendente"
        if failure and failure not in {"0", "0.0", "-"}:
            return "falha"
        if observations:
            return "atenção"
        if fiscal_meter == 0 and delta_tank and abs(delta_tank) > 0.001:
            return "atenção"
        base_volume = max(abs(fiscal_meter or 0), abs(delta_tank or 0), 1)
        tolerance_m3 = max(100, base_volume * 0.005)
        if fiscal_minus_tank is not None and abs(fiscal_minus_tank) > tolerance_m3:
            return "atenção"
        if delta_percent is not None and abs(delta_percent) > 0.005:
            return "atenção"
        return "ok"

    def _headers_for_sheet(self, sheet: dict[str, Any]) -> dict[str, str]:
        name = sheet["name"]
        header_rows = []
        if name == "Balanço de Gás":
            header_rows = [4, 5]
        elif name == "MPFM Subsea x Fiscal- Óleo":
            header_rows = [3, 4, 5]
        elif name in self.KEY_SHEETS:
            header_rows = [self.KEY_SHEETS[name]["start"] - 1]
        elif name.endswith("-Fx"):
            header_rows = [24]
        elif re.fullmatch(r"\d{2}d?", name):
            header_rows = [1, 2, 3]
        rows = {int(r["row"]): r.get("values") or {} for r in sheet.get("rows", [])}
        headers: dict[str, str] = {}
        for row_no in header_rows:
            for col, value in rows.get(row_no, {}).items():
                headers[col] = (headers.get(col, "") + " " + value).strip()
        return headers

    def _header_candidates(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for row in rows[:80]:
            values = list((row.get("values") or {}).values())
            text_count = sum(1 for value in values if re.search(r"[A-Za-zÀ-ÿ]", value))
            if len(values) >= 3 or text_count >= 2:
                out.append({"row": row["row"], "values": values[:18]})
            if len(out) >= 10:
                break
        return out

    def _is_default_sheet(self, name: str) -> bool:
        return name in self.KEY_SHEETS or bool(re.fullmatch(r"\d{2}d?", name)) or name.endswith("-Fx")

    def _sheet_config(self, name: str) -> dict[str, Any]:
        if name in self.KEY_SHEETS:
            return self.KEY_SHEETS[name]
        if name.endswith("-Fx"):
            return {"start": 25, "date": "A", "title": "P", "status": "D", "tag": "", "domain": "flow_computer_range"}
        if re.fullmatch(r"\d{2}d?", name):
            return {"start": 1, "date": "", "title": "", "status": "", "tag": "", "domain": "daily_verification"}
        return {"start": 1, "date": "", "title": "", "status": "", "tag": "", "domain": self._domain_for_sheet(name)}

    def _coverage_notes(self, sheets: list[dict[str, Any]]) -> list[dict[str, str]]:
        notes = {
            "Ocurrences": ("Importar como ocorrencias/tratativas; XML nao carrega responsavel, NFSM, SAP e acao executada.", "missing_import"),
            "Lab-Report": ("Importar analises API, densidade e BSW; parte pode vir de laudos, nao dos XMLs.", "partial"),
            "API": ("Recriar por volume ponderado e BSW usando Lab-Report + volumes fiscais.", "partial"),
            "Tank ": ("Necessario para balanco tanque x medidor fiscal; observacoes manuais nao vêm dos XMLs.", "missing_import"),
            "Off Spec Tank": ("Necessario para producao desviada ao offspec; XML cobre volume fiscal, nao o motivo operacional.", "missing_import"),
            "MPFM Subsea x Fiscal- Óleo": ("Aplicacao ja tem MPFM e fiscal; falta guardar a visao do checklist e comentarios.", "partial"),
            "Balanço de Gás": ("Aplicacao tem medicao de gas, mas precisa materializar balanco operacional x fiscal/injecao.", "partial"),
        }
        out = []
        for sheet in sheets:
            name = sheet["name"]
            if name in notes:
                note, status = notes[name]
                out.append({"sheet": name, "status": status, "note": note})
        return out

    def _metric_name(self, sheet_name: str, headers: dict[str, str], values: dict[str, str]) -> str:
        if sheet_name in {"Tank ", "Off Spec Tank", "Balanço de Gás"}:
            return "daily_balance"
        if sheet_name == "Lab-Report":
            return "api_density_bsw"
        if sheet_name == "API":
            return "weighted_api_bsw"
        if sheet_name.endswith("-Fx"):
            return headers.get("D") or "range_validation"
        return self._domain_for_sheet(sheet_name)

    def _domain_for_sheet(self, name: str) -> str:
        normalized = name.lower().replace(" ", "_")
        return re.sub(r"[^a-z0-9_]+", "_", normalized).strip("_") or "checklist"

    def _pick(self, values: dict[str, str], col: str | None) -> str:
        return values.get(str(col or "").upper(), "") if col else ""

    def _first_text(self, values: dict[str, str]) -> str:
        for value in values.values():
            if re.search(r"[A-Za-zÀ-ÿ]", value):
                return value[:300]
        return ""

    def _first_tag(self, values: dict[str, str]) -> str:
        joined = " ".join(values.values())
        match = self.TAG_RE.search(joined)
        return match.group(0).upper().replace(" ", "") if match else ""

    def _first_date(self, values: dict[str, str]) -> str:
        for value in values.values():
            parsed = self._excel_date(value)
            if parsed:
                return parsed
        return ""

    def _first_numeric(self, values: dict[str, str]) -> tuple[float | None, str]:
        for value in values.values():
            try:
                if value and not re.search(r"[A-Za-zÀ-ÿ#\\\\/]", value):
                    return float(str(value).replace(",", ".")), ""
            except ValueError:
                continue
        return None, ""

    def _parse_decimal(self, value: Any) -> float | None:
        raw = str(value or "").strip()
        if not raw or re.fullmatch(r"#(?:VALUE|REF|DIV/0|N/A|NAME|NULL|NUM)!?", raw, re.I):
            return None
        raw = raw.replace("%", "").replace(" ", "")
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    def _has_meaningful_content(self, values: dict[str, str]) -> bool:
        for value in values.values():
            raw = str(value or "").strip()
            if not raw:
                continue
            if re.fullmatch(r"#(?:VALUE|REF|DIV/0|N/A|NAME|NULL|NUM)!?", raw, re.I):
                continue
            return True
        return False

    def _excel_date(self, value: str) -> str:
        raw = str(value or "").strip()
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", raw):
            day, month, year = [int(x) for x in raw.split("/")]
            if year < 100:
                year += 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
        if not re.fullmatch(r"\d+(?:\.0+)?", raw):
            return ""
        serial = int(float(raw))
        if serial < 25000 or serial > 60000:
            return ""
        dt = datetime(1899, 12, 30) + timedelta(days=serial)
        return dt.strftime("%Y-%m-%d")

    def _cell_col(self, ref: str) -> str:
        match = re.match(r"([A-Z]+)", ref or "")
        return match.group(1) if match else ""

    def _col_to_idx(self, col: str) -> int:
        value = 0
        for ch in col:
            value = value * 26 + ord(ch) - 64
        return value

    def _clean(self, value: Any) -> str:
        text = html.unescape(str(value or "")).replace("\r", " ").replace("\n", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _resolve_path(self, source_path: str) -> Path:
        raw = str(source_path or "").strip().strip('"')
        if not raw:
            raise ValueError("Caminho do checklist nao informado.")
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"Checklist nao encontrado: {path}")
        if path.suffix.lower() not in {".xlsm", ".xlsx"}:
            raise ValueError("Use um arquivo .xlsm ou .xlsx.")
        return path

    def _file_hash(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _limit(self, value: int) -> int:
        return max(1, min(int(value or 120), 1000))

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _ensure_tables(self, cur) -> None:
        cur.executescript(
            """
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
            """
        )
        self._ensure_column(cur, "painel_operador_gas_balance", "comment", "TEXT DEFAULT ''")

    def _ensure_column(self, cur, table: str, column: str, definition: str) -> None:
        existing = {str(row[1]) for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
