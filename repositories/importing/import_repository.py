from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class ImportRepository:
    def __init__(self, db_conn, file_sha1_fn, infer_metric_unit_fn):
        self._db_conn = db_conn
        self._file_sha1 = file_sha1_fn
        self._infer_metric_unit = infer_metric_unit_fn
        self._batch_conn = None
        self._batch_depth = 0

    @contextmanager
    def batch_writes(self):
        if self._batch_conn is not None:
            self._batch_depth += 1
            try:
                yield self
            finally:
                self._batch_depth -= 1
            return

        conn = self._db_conn()
        self._batch_conn = conn
        self._batch_depth = 1
        try:
            yield self
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._batch_depth = 0
            self._batch_conn = None
            conn.close()

    def _borrow_conn(self):
        if self._batch_conn is not None:
            return self._batch_conn, False
        return self._db_conn(), True

    @staticmethod
    def _finish_read(conn, owns_conn: bool) -> None:
        if owns_conn:
            conn.close()

    @staticmethod
    def _finish_write(conn, owns_conn: bool) -> None:
        if owns_conn:
            conn.commit()
            conn.close()

    def log_file(
        self,
        run_id: int,
        filename: str,
        ext: str,
        file_type: str,
        unit_code: str,
        meter_id: str,
        location: str,
        content_date: str,
        report_start: str,
        report_end: str,
        excel_month: str,
        identity_key: str = "",
        time_source: str = "",
        file_hash: str = "",
        processed_ok: bool = True,
        message: str = "",
    ) -> None:
        conn, owns_conn = self._borrow_conn()
        try:
            conn.execute(
                """INSERT INTO files_imported(
                    run_id, filename, ext, file_type, unit_code, meter_id, location, content_date, report_start,
                    report_end, excel_month, identity_key, time_source, file_hash, processed_ok, message, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    filename,
                    ext,
                    file_type,
                    unit_code,
                    meter_id,
                    location,
                    content_date,
                    report_start,
                    report_end,
                    excel_month,
                    identity_key or "",
                    time_source or "",
                    file_hash or "",
                    1 if processed_ok else 0,
                    message,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        finally:
            self._finish_write(conn, owns_conn)

    def log_raw_file(self, run_id: int, source_path: Path, source_type: str, meta: dict) -> int | None:
        try:
            file_hash = self._file_sha1(str(source_path))
            file_size = source_path.stat().st_size
        except Exception:
            file_hash = ""
            file_size = 0
        conn, owns_conn = self._borrow_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO source_files_raw(
                    run_id, filename, original_path, source_type, ext, detected_type, unit_code, meter_id,
                    location, content_date, report_start, report_end, identity_key, time_source,
                    file_hash, file_size_bytes, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    source_path.name,
                    str(source_path),
                    source_type,
                    meta.get("ext", ""),
                    meta.get("file_type", ""),
                    meta.get("unit", ""),
                    meta.get("meter_id", ""),
                    meta.get("location", ""),
                    meta.get("content_date", ""),
                    meta.get("report_start", ""),
                    meta.get("report_end", ""),
                    meta.get("identity_key", ""),
                    meta.get("time_source", ""),
                    file_hash,
                    file_size,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            return cur.lastrowid
        finally:
            self._finish_write(conn, owns_conn)

    def find_latest_import_by_identity(self, identity_key: str) -> dict | None:
        if not str(identity_key or "").strip():
            return None
        conn, owns_conn = self._borrow_conn()
        try:
            row = conn.execute(
                """
                SELECT id, filename, ext, file_type, unit_code, meter_id, location, content_date,
                       report_start, report_end, excel_month, identity_key, time_source, file_hash,
                       processed_ok, message, created_at
                FROM files_imported
                WHERE identity_key=?
                ORDER BY id DESC
                LIMIT 1
                """,
                (identity_key,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            self._finish_read(conn, owns_conn)

    def find_latest_import_by_hash(self, file_hash: str) -> dict | None:
        if not str(file_hash or "").strip():
            return None
        conn, owns_conn = self._borrow_conn()
        try:
            row = conn.execute(
                """
                SELECT id, filename, ext, file_type, unit_code, meter_id, location, content_date,
                       report_start, report_end, excel_month, identity_key, time_source, file_hash,
                       processed_ok, message, created_at
                FROM files_imported
                WHERE file_hash=? AND COALESCE(processed_ok,1)=1
                ORDER BY id DESC
                LIMIT 1
                """,
                (file_hash,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            self._finish_read(conn, owns_conn)

    def log_parsing_event(
        self,
        run_id: int,
        source_file_raw_id: int | None,
        parser_name: str,
        parser_stage: str,
        status: str,
        details: dict | None = None,
    ) -> None:
        conn, owns_conn = self._borrow_conn()
        try:
            conn.execute(
                """INSERT INTO parsing_events_raw(
                    run_id, source_file_raw_id, parser_name, parser_stage, status, details_json, created_at
                ) VALUES(?,?,?,?,?,?,?)""",
                (
                    run_id,
                    source_file_raw_id,
                    parser_name,
                    parser_stage,
                    status,
                    __import__("json").dumps(details or {}, ensure_ascii=False),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        finally:
            self._finish_write(conn, owns_conn)

    def add_issue(
        self,
        run_id: int,
        excel_file: str,
        issue_type: str,
        severity: str,
        ref_key: str,
        day_ref: str,
        details: str,
    ) -> None:
        conn, owns_conn = self._borrow_conn()
        try:
            conn.execute(
                "INSERT INTO validation_issues(run_id, excel_file, issue_type, severity, ref_key, day_ref, details, created_at) VALUES(?,?,?,?,?,?,?,?)",
                (run_id, excel_file, issue_type, severity, ref_key, day_ref, details, datetime.now().isoformat(timespec="seconds")),
            )
        finally:
            self._finish_write(conn, owns_conn)

    def sanitize_files_imported_history(self, target_month: str = ""):
        conn = self._db_conn()
        conn.row_factory = lambda cursor, row: {
            cursor.description[idx][0]: row[idx] for idx in range(len(cursor.description))
        }
        cur = conn.cursor()
        where = ""
        params = []
        if target_month:
            where = """
            WHERE (
                substr(COALESCE(content_date,''),1,7)=?
                OR COALESCE(excel_month,'')=?
                OR substr(COALESCE(created_at,''),1,7)=?
            )
            """
            params = [target_month, target_month, target_month]

        duplicates = cur.execute(
            f"""
            SELECT
                filename, ext, file_type, unit_code, meter_id, location, content_date, excel_month,
                COALESCE(file_hash,'') AS file_hash,
                processed_ok, COALESCE(message,'') AS message,
                COUNT(*) AS n_rows,
                MAX(id) AS keep_id,
                GROUP_CONCAT(id) AS group_ids
            FROM files_imported
            {where}
            GROUP BY
                filename, ext, file_type, unit_code, meter_id, location, content_date, excel_month,
                COALESCE(file_hash,''), processed_ok, COALESCE(message,'')
            HAVING COUNT(*) > 1
            """,
            params,
        ).fetchall()

        removed_rows = 0
        for row in duplicates:
            group_ids = [int(raw_id) for raw_id in str(row["group_ids"] or "").split(",") if str(raw_id).strip()]
            delete_ids = [raw_id for raw_id in group_ids if raw_id != int(row["keep_id"])]
            if not delete_ids:
                continue
            placeholders = ",".join("?" * len(delete_ids))
            cur.execute(
                f"DELETE FROM files_imported WHERE id IN ({placeholders})",
                delete_ids,
            )
            removed_rows += cur.rowcount or 0

        conn.commit()
        conn.close()
        return {
            "ok": True,
            "month": target_month,
            "duplicate_groups": len(duplicates),
            "rows_removed": removed_rows,
        }

    def store_sheet_rows(self, run_id: int, excel_file: str, sheet_name: str, rows) -> None:
        conn, owns_conn = self._borrow_conn()
        try:
            now = datetime.now().isoformat(timespec="seconds")
            protected = {
                "Dia ref.",
                "Dia",
                "Hora",
                "Bank",
                "Loop",
                "Tipo",
                "TAG",
                "Instrumento",
                "Cobertura",
                "Horas",
                "Status Gás",
                "Status Óleo",
                "Status HC",
                "Status Água",
            }
            metric_rows = []
            for row in rows:
                day_ref = row.get("Dia ref.") or row.get("Dia") or ""
                hour_ref = row.get("Hora")
                bank = row.get("Bank", "")
                loop = row.get("Loop", "")
                tipo = row.get("Tipo", "")
                tag = row.get("TAG", "")
                instrument = row.get("Instrumento", "")
                row_kind = "hourly" if sheet_name.startswith("HOURLY_") else "daily" if sheet_name.startswith("DAILY_") else "recon"
                for col, value in row.items():
                    if col in protected:
                        continue
                    if isinstance(value, (int, float)) and not (isinstance(value, float) and value != value):
                        metric_rows.append(
                            (
                                run_id,
                                instrument or "",
                                excel_file,
                                sheet_name,
                                row_kind,
                                day_ref,
                                int(hour_ref) if isinstance(hour_ref, (int, float)) else None,
                                bank,
                                loop,
                                tipo,
                                tag,
                                instrument,
                                col,
                                float(value),
                                self._infer_metric_unit(col),
                                1,
                                now,
                            )
                        )
            if metric_rows:
                conn.executemany(
                    """INSERT INTO measurements_curated(
                        run_id, source_file, excel_file, sheet_name, row_kind, day_ref, hour_ref,
                        bank, loop, tipo, tag, instrument, metric_name, metric_value, metric_unit, is_official, created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    metric_rows,
                )
        finally:
            self._finish_write(conn, owns_conn)

    def _recompute_sep_source_resolution_with_conn(self, conn, production_date: str, fluid_kind: str, meter_id: str):
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, report_kind, created_at, resolution_status FROM sep_source_files
               WHERE is_active=1 AND production_date=? AND fluid_kind=? AND meter_id=?
               ORDER BY created_at, id""",
            (production_date, fluid_kind, meter_id),
        ).fetchall()
        if not rows:
            return None
        manual = [r for r in rows if (r["resolution_status"] or "") == "manual_official"]
        if manual:
            chosen = sorted(manual, key=lambda r: -(r["id"] or 0))[0]["id"]
        else:
            pri = {"24hours": 0, "daily": 1, "other": 2}
            chosen = sorted(rows, key=lambda r: (pri.get(r["report_kind"] or "other", 9), -(r["id"] or 0)))[0]["id"]
        now = datetime.now().isoformat(timespec="seconds")
        ids = [r["id"] for r in rows]
        q = ",".join("?" * len(ids))
        cur.execute(
            f"UPDATE sep_source_files SET is_official=0, resolution_status=CASE WHEN resolution_status='deleted' THEN resolution_status ELSE 'pending' END, updated_at=? WHERE id IN ({q})",
            [now] + ids,
        )
        cur.execute(
            "UPDATE sep_source_files SET is_official=1, resolution_status=COALESCE(NULLIF(resolution_status,'pending'),'official'), updated_at=? WHERE id=?",
            (now, chosen),
        )
        cur.execute(f"UPDATE measurements_curated SET is_official=0 WHERE source_record_id IN ({q})", ids)
        cur.execute("UPDATE measurements_curated SET is_official=1 WHERE source_record_id=?", (chosen,))
        conn.commit()
        return chosen

    def recompute_sep_source_resolution(self, production_date: str, fluid_kind: str, meter_id: str):
        conn = self._db_conn()
        try:
            return self._recompute_sep_source_resolution_with_conn(conn, production_date, fluid_kind, meter_id)
        finally:
            conn.close()

    def register_sep_source_file(
        self,
        file_path: str,
        fluid_kind: str,
        meter_id: str,
        location: str,
        production_date: str,
        report_start: str = "",
        report_end: str = "",
        identity_key: str = "",
        time_source: str = "content",
    ):
        source_hash = self._file_sha1(file_path)
        report_kind = self._txt_report_kind(Path(file_path).name)
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._db_conn()
        try:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT id, is_active, identity_key FROM sep_source_files WHERE source_hash=? ORDER BY id DESC LIMIT 1",
                (source_hash,),
            ).fetchone()
            if row:
                source_id = row["id"]
                if int(row["is_active"] or 0) == 1 and (not identity_key or (row["identity_key"] or "") == (identity_key or "")):
                    chosen = self._recompute_sep_source_resolution_with_conn(conn, production_date, fluid_kind, meter_id or "")
                    row = cur.execute("SELECT is_official FROM sep_source_files WHERE id=?", (source_id,)).fetchone()
                    return source_id, bool(row and row["is_official"]), chosen, "same_content"
                superseded_ids = []
                if identity_key:
                    superseded_ids = [
                        int(r["id"])
                        for r in cur.execute(
                            """
                            SELECT id FROM sep_source_files
                            WHERE identity_key=? AND is_active=1
                            ORDER BY id DESC
                            """,
                            (identity_key,),
                        ).fetchall()
                    ]
                    if superseded_ids:
                        q = ",".join("?" * len(superseded_ids))
                        cur.execute(
                            f"UPDATE sep_source_files SET is_active=0, is_official=0, resolution_status='superseded', updated_at=? WHERE id IN ({q})",
                            [now] + superseded_ids,
                        )
                        cur.execute(
                            f"UPDATE measurements_curated SET is_official=0 WHERE source_record_id IN ({q})",
                            superseded_ids,
                        )
                cur.execute(
                    """
                    UPDATE sep_source_files
                    SET production_date=?, fluid_kind=?, meter_id=?, location=?, report_kind=?, report_start=?, report_end=?,
                        identity_key=?, time_source=?, is_active=1, is_official=0, resolution_status='pending', updated_at=?
                    WHERE id=?
                    """,
                    (
                        production_date,
                        fluid_kind,
                        meter_id or "",
                        location or "",
                        report_kind,
                        report_start or "",
                        report_end or "",
                        identity_key or "",
                        time_source or "content",
                        now,
                        source_id,
                    ),
                )
                conn.commit()
                chosen = self._recompute_sep_source_resolution_with_conn(conn, production_date, fluid_kind, meter_id or "")
                row = cur.execute("SELECT is_official FROM sep_source_files WHERE id=?", (source_id,)).fetchone()
                return source_id, bool(row and row["is_official"]), chosen, "reactivated"
            superseded_ids = []
            if identity_key:
                superseded_ids = [
                    int(r["id"])
                    for r in cur.execute(
                        """
                        SELECT id FROM sep_source_files
                        WHERE identity_key=? AND is_active=1
                        ORDER BY id DESC
                        """,
                        (identity_key,),
                    ).fetchall()
                ]
                if superseded_ids:
                    q = ",".join("?" * len(superseded_ids))
                    cur.execute(
                        f"UPDATE sep_source_files SET is_active=0, is_official=0, resolution_status='superseded', updated_at=? WHERE id IN ({q})",
                        [now] + superseded_ids,
                    )
                    cur.execute(
                        f"UPDATE measurements_curated SET is_official=0 WHERE source_record_id IN ({q})",
                        superseded_ids,
                    )
                    conn.commit()
            cur.execute(
                """INSERT INTO sep_source_files(
                       production_date, fluid_kind, meter_id, location, report_kind, report_start, report_end,
                       identity_key, time_source, source_file, source_hash, is_active, is_official,
                       resolution_status, created_at, updated_at
                   )
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    production_date,
                    fluid_kind,
                    meter_id or "",
                    location or "",
                    report_kind,
                    report_start or "",
                    report_end or "",
                    identity_key or "",
                    time_source or "content",
                    Path(file_path).name,
                    source_hash,
                    1,
                    0,
                    "pending",
                    now,
                    now,
                ),
            )
            source_id = cur.lastrowid
            conn.commit()
            chosen = self._recompute_sep_source_resolution_with_conn(conn, production_date, fluid_kind, meter_id or "")
            row = cur.execute("SELECT is_official FROM sep_source_files WHERE id=?", (source_id,)).fetchone()
            return source_id, bool(row and row["is_official"]), chosen, ("superseded" if superseded_ids else "new")
        finally:
            conn.close()

    @staticmethod
    def _txt_report_kind(name: str) -> str:
        n = (name or "").lower()
        if "24hours" in n:
            return "24hours"
        if "daily" in n:
            return "daily"
        return "other"
