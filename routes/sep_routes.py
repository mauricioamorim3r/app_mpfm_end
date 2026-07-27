from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, Request

from routes.date_utils import normalize_date_input, normalize_date_range
from repositories.sep import SepRepository
from services.sep import build_sep_fluid_rows, build_sep_pivot_rows


def register_sep_routes(app, ctx: dict) -> None:
    db_conn = ctx["db_conn"]
    db_upsert_sep_alignment = ctx["db_upsert_sep_alignment"]
    db_delete_sep_alignment = ctx["db_delete_sep_alignment"]
    recompute_alignment_resolution = ctx["recompute_alignment_resolution"]
    recompute_sep_source_resolution = ctx["recompute_sep_source_resolution"]
    output_dir = ctx["output_dir"]
    excel_name = ctx["excel_name"]
    build_monthly_base_unica = ctx["build_monthly_base_unica"]
    schedule_monthly_base_unica = ctx["schedule_monthly_base_unica"]
    cleanup_workbook = ctx["cleanup_workbook"]
    sep_detail_headers = ctx["sep_detail_headers"]
    sep_detail_kind = ctx["sep_detail_kind"]
    upsert_sep_detail_row = ctx["upsert_sep_detail_row"]
    sep_repo = SepRepository(db_conn)

    @app.get("/api/sep-alignments")
    def api_sep_alignments(date_from: str = "", date_to: str = "", bank: str = ""):
        date_from, date_to = normalize_date_range(date_from, date_to)
        conn = db_conn()
        cur = conn.cursor()
        if not date_to:
            date_to = cur.execute("SELECT MAX(production_date) FROM sep_alignments WHERE is_active=1").fetchone()[0] or ""
        if not date_from:
            date_from = date_to
        sql = "SELECT id, production_date, bank, mpfm_tag, sep_meter_id, sep_tag, notes, is_official, resolution_status, created_at, updated_at FROM sep_alignments WHERE is_active=1"
        params = []
        if date_from and date_to:
            sql += " AND production_date BETWEEN ? AND ?"
            params += [date_from, date_to]
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        sql += " ORDER BY production_date DESC, bank"
        rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
        conn.close()
        return {"rows": rows, "date_from": date_from, "date_to": date_to}

    @app.post("/api/sep-alignments")
    def api_sep_alignments_create(body: dict):
        production_date = normalize_date_input((body or {}).get("production_date", ""))
        bank = str((body or {}).get("bank", "")).strip().upper()
        if not production_date or not bank:
            raise HTTPException(400, "production_date e bank são obrigatórios")
        new_id = db_upsert_sep_alignment(
            production_date=production_date,
            bank=bank,
            mpfm_tag=str((body or {}).get("mpfm_tag", "")).strip(),
            sep_meter_id=str((body or {}).get("sep_meter_id", "")).strip(),
            sep_tag=str((body or {}).get("sep_tag", "SEP")).strip() or "SEP",
            notes=str((body or {}).get("notes", "")).strip(),
        )
        try:
            yr, mo = production_date[:4], production_date[5:7]
            outxls = output_dir / excel_name(yr, mo)
            if outxls.exists():
                schedule_monthly_base_unica(outxls, yr, mo)
        except Exception:
            pass
        return {"ok": True, "id": new_id}

    @app.delete("/api/sep-alignments/{alignment_id}")
    def api_sep_alignments_delete(alignment_id: int):
        conn = db_conn()
        cur = conn.cursor()
        row = cur.execute("SELECT production_date FROM sep_alignments WHERE id=?", (alignment_id,)).fetchone()
        conn.close()
        db_delete_sep_alignment(alignment_id)
        try:
            if row and row["production_date"]:
                yr, mo = row["production_date"][:4], row["production_date"][5:7]
                outxls = output_dir / excel_name(yr, mo)
                if outxls.exists():
                    schedule_monthly_base_unica(outxls, yr, mo)
        except Exception:
            pass
        return {"ok": True}

    @app.get("/api/duplicates/alignments")
    def api_alignment_duplicates(date_from: str = "", date_to: str = ""):
        date_from, date_to = normalize_date_range(date_from, date_to)
        conn = db_conn()
        cur = conn.cursor()
        if not date_to:
            date_to = cur.execute("SELECT MAX(production_date) FROM sep_alignments WHERE is_active=1").fetchone()[0] or ""
        if not date_from:
            date_from = date_to
        groups = [
            dict(r)
            for r in cur.execute(
                """
                SELECT production_date, bank, COUNT(*) AS candidates,
                       SUM(CASE WHEN COALESCE(is_official,1)=1 THEN 1 ELSE 0 END) AS official_count
                FROM sep_alignments
                WHERE is_active=1 AND production_date BETWEEN ? AND ?
                GROUP BY production_date, bank
                HAVING COUNT(*) > 1
                ORDER BY production_date DESC, bank
                """,
                (date_from, date_to),
            ).fetchall()
        ]
        for group in groups:
            group["items"] = [
                dict(r)
                for r in cur.execute(
                    "SELECT id, mpfm_tag, sep_meter_id, sep_tag, notes, is_official, resolution_status, created_at FROM sep_alignments WHERE is_active=1 AND production_date=? AND bank=? ORDER BY COALESCE(is_official,0) DESC, id DESC",
                    (group["production_date"], group["bank"]),
                ).fetchall()
            ]
        conn.close()
        return {"rows": groups}

    @app.post("/api/duplicates/alignments/resolve")
    async def api_alignment_duplicates_resolve(request: Request):
        body = await request.json()
        production_date = normalize_date_input(body.get("production_date", ""))
        bank = str(body.get("bank", "")).upper()
        action = body.get("action", "use")
        official_id = body.get("official_id")
        delete_ids = body.get("delete_ids") or []
        conn = db_conn()
        cur = conn.cursor()
        now = datetime.now().isoformat(timespec="seconds")
        try:
            ids = [r["id"] for r in cur.execute("SELECT id FROM sep_alignments WHERE is_active=1 AND production_date=? AND bank=?", (production_date, bank)).fetchall()]
            if not ids:
                raise HTTPException(404, "Conflito de alinhamento não encontrado")
            if action == "delete" and delete_ids:
                q = ",".join("?" * len(delete_ids))
                cur.execute(f"UPDATE sep_alignments SET is_active=0, is_official=0, resolution_status='deleted', updated_at=? WHERE id IN ({q})", [now] + delete_ids)
                conn.commit()
                chosen = recompute_alignment_resolution(production_date, bank)
            elif action == "pending":
                q = ",".join("?" * len(ids))
                cur.execute(f"UPDATE sep_alignments SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})", [now] + ids)
                conn.commit()
                chosen = None
            else:
                if not official_id:
                    raise HTTPException(400, "official_id é obrigatório")
                q = ",".join("?" * len(ids))
                cur.execute(f"UPDATE sep_alignments SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})", [now] + ids)
                cur.execute("UPDATE sep_alignments SET is_official=1, resolution_status='manual_official', updated_at=? WHERE id=?", (now, official_id))
                conn.commit()
                chosen = official_id
        finally:
            conn.close()
        try:
            if production_date and len(production_date) >= 7:
                yr, mo = production_date[:4], production_date[5:7]
                schedule_monthly_base_unica(output_dir / excel_name(yr, mo), yr, mo)
        except Exception:
            pass
        return {"ok": True, "chosen": chosen}

    @app.get("/api/duplicates/sep")
    def api_sep_duplicates(date_from: str = "", date_to: str = ""):
        date_from, date_to = normalize_date_range(date_from, date_to)
        conn = db_conn()
        cur = conn.cursor()
        if not date_to:
            date_to = cur.execute("SELECT MAX(production_date) FROM sep_source_files").fetchone()[0] or ""
        if not date_from:
            date_from = date_to
        groups = [
            dict(r)
            for r in cur.execute(
                """
                SELECT production_date, fluid_kind, meter_id, COUNT(*) AS candidates,
                       SUM(CASE WHEN is_official=1 THEN 1 ELSE 0 END) AS official_count,
                       GROUP_CONCAT(source_file, ' | ') AS files
                FROM sep_source_files
                WHERE is_active=1 AND production_date BETWEEN ? AND ?
                GROUP BY production_date, fluid_kind, meter_id
                HAVING COUNT(*) > 1
                ORDER BY production_date DESC, fluid_kind, meter_id
                """,
                (date_from, date_to),
            ).fetchall()
        ]
        for group in groups:
            group["items"] = [
                dict(r)
                for r in cur.execute(
                    """
                    SELECT id, source_file, report_kind, is_official, resolution_status, created_at
                    FROM sep_source_files
                    WHERE is_active=1 AND production_date=? AND fluid_kind=? AND meter_id=?
                    ORDER BY is_official DESC, CASE report_kind WHEN '24hours' THEN 0 WHEN 'daily' THEN 1 ELSE 2 END, id DESC
                    """,
                    (group["production_date"], group["fluid_kind"], group["meter_id"]),
                ).fetchall()
            ]
        conn.close()
        return {"rows": groups}

    @app.post("/api/duplicates/sep/resolve")
    async def api_sep_duplicates_resolve(request: Request):
        body = await request.json()
        production_date = normalize_date_input(body.get("production_date", ""))
        fluid_kind = body.get("fluid_kind", "")
        meter_id = body.get("meter_id", "")
        action = body.get("action", "use")
        official_id = body.get("official_id")
        delete_ids = body.get("delete_ids") or []
        conn = db_conn()
        cur = conn.cursor()
        now = datetime.now().isoformat(timespec="seconds")
        try:
            ids = [r["id"] for r in cur.execute("SELECT id FROM sep_source_files WHERE is_active=1 AND production_date=? AND fluid_kind=? AND meter_id=?", (production_date, fluid_kind, meter_id)).fetchall()]
            if not ids:
                raise HTTPException(404, "Conflito não encontrado")
            chosen = None
            if action == "delete" and delete_ids:
                q = ",".join("?" * len(delete_ids))
                cur.execute(f"UPDATE sep_source_files SET is_active=0, is_official=0, resolution_status='deleted', updated_at=? WHERE id IN ({q})", [now] + delete_ids)
                cur.execute(f"DELETE FROM measurements_curated WHERE source_record_id IN ({q})", delete_ids)
                conn.commit()
                chosen = recompute_sep_source_resolution(production_date, fluid_kind, meter_id)
            elif action == "pending":
                q = ",".join("?" * len(ids))
                cur.execute(f"UPDATE sep_source_files SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})", [now] + ids)
                cur.execute(f"UPDATE measurements_curated SET is_official=0 WHERE source_record_id IN ({q})", ids)
                conn.commit()
            else:
                if not official_id:
                    raise HTTPException(400, "official_id é obrigatório")
                q = ",".join("?" * len(ids))
                cur.execute(f"UPDATE sep_source_files SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})", [now] + ids)
                cur.execute("UPDATE sep_source_files SET is_official=1, resolution_status='manual_official', updated_at=? WHERE id=?", (now, official_id))
                cur.execute(f"UPDATE measurements_curated SET is_official=0 WHERE source_record_id IN ({q})", ids)
                cur.execute("UPDATE measurements_curated SET is_official=1 WHERE source_record_id=?", (official_id,))
                conn.commit()
                chosen = official_id
        finally:
            conn.close()
        try:
            if production_date and len(production_date) >= 7:
                yr, mo = production_date[:4], production_date[5:7]
                schedule_monthly_base_unica(output_dir / excel_name(yr, mo), yr, mo)
        except Exception:
            pass
        return {"ok": True, "chosen": chosen}

    @app.get("/api/sep/data")
    def api_sep_extracted(date_from: str = "", date_to: str = "", unit: str = ""):
        date_from, date_to = normalize_date_range(date_from, date_to)
        if not date_to:
            date_to = sep_repo.get_latest_sep_day()
        if not date_from:
            date_from = date_to
        rows = sep_repo.list_sep_measurements(date_from, date_to, unit)
        align_map = sep_repo.list_sep_alignment_map(date_from, date_to)
        pivot_rows, metric_cols = build_sep_pivot_rows(rows, align_map)
        return {"rows": pivot_rows, "metric_cols": metric_cols, "date_from": date_from, "date_to": date_to}

    @app.get("/api/sep/fluid-data")
    def api_sep_fluid_data(fluid: str, date_from: str = "", date_to: str = ""):
        date_from, date_to = normalize_date_range(date_from, date_to)
        fluid = (fluid or "").strip().lower()
        kind_map = {"oleo": "sep_oleo_detail", "gas": "sep_gas_detail", "agua": "sep_agua_detail"}
        if fluid not in kind_map:
            raise HTTPException(400, "fluid deve ser oleo, gas ou agua")
        if not date_to:
            date_to = sep_repo.get_latest_fluid_day(kind_map[fluid])
        if not date_from:
            date_from = date_to
        rows = sep_repo.list_fluid_measurements(kind_map[fluid], date_from, date_to)
        if not rows:
            latest = sep_repo.get_latest_fluid_day(kind_map[fluid])
            if latest:
                date_from = latest
                date_to = latest
                rows = sep_repo.list_fluid_measurements(kind_map[fluid], date_from, date_to)
        headers = ["Hour"] + sep_detail_headers(fluid)
        out = build_sep_fluid_rows(rows, fluid, sep_detail_headers(fluid))
        return {"headers": headers, "rows": out, "fluid": fluid, "date_from": date_from, "date_to": date_to}

    @app.post("/api/sep/fluid-row")
    async def api_sep_fluid_row_upsert(request: Request):
        body = await request.json()
        fluid = (body.get("fluid") or "").strip().lower()
        if fluid not in ("oleo", "gas", "agua"):
            raise HTTPException(400, "fluid inválido")
        day_ref = normalize_date_input(body.get("day_ref") or "")
        tag = (body.get("tag") or "").strip()
        if not day_ref or not tag:
            raise HTTPException(400, "day_ref e tag são obrigatórios")
        instrument = (body.get("instrument") or "").strip()
        hour_ref = body.get("hour_ref")
        values = body.get("values") or {}
        upsert_sep_detail_row(fluid, day_ref, hour_ref, tag, instrument, values, source_file="manual_ui")
        return {"ok": True}

    @app.delete("/api/sep/fluid-row")
    async def api_sep_fluid_row_delete(request: Request):
        body = await request.json()
        fluid = (body.get("fluid") or "").strip().lower()
        if fluid not in ("oleo", "gas", "agua"):
            raise HTTPException(400, "fluid inválido")
        day_ref = normalize_date_input(body.get("day_ref") or "")
        tag = (body.get("tag") or "").strip()
        hour_ref = body.get("hour_ref")
        if hour_ref in ("", None, "DAY"):
            hour_ref = None
        else:
            hour_ref = int(hour_ref)
        row_kind = sep_detail_kind(fluid)
        sep_repo.delete_sep_fluid_row(row_kind, day_ref, hour_ref, tag)
        return {"ok": True}

    @app.put("/api/measurements/{rec_id}")
    async def api_update_measurement(rec_id: int, request: Request):
        body = await request.json()
        value = body.get("value")
        try:
            new_value = sep_repo.update_measurement_value(rec_id, value)
            return {"ok": True, "id": rec_id, "value": new_value}
        except Exception as exc:
            raise HTTPException(400, str(exc))

    @app.delete("/api/measurements/{rec_id}")
    def api_delete_measurement(rec_id: int):
        sep_repo.delete_measurement(rec_id)
        return {"ok": True, "id": rec_id}

    @app.post("/api/measurements")
    async def api_insert_measurement(request: Request):
        body = await request.json()
        required = ["day_ref", "bank", "row_kind", "metric_name", "metric_value"]
        for field in required:
            if body.get(field) is None:
                raise HTTPException(400, f"Campo obrigatório: {field}")
        new_id = sep_repo.insert_measurement(body)
        return {"ok": True, "id": new_id}
