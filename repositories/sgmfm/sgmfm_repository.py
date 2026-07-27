from __future__ import annotations

import json
from datetime import datetime


TABLES = {
    "rotina": "sgmfm_rotina_diaria",
    "logbook": "sgmfm_logbook",
    "pvt": "sgmfm_analise_pvt",
}


class SgmfmRepository:
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def _table(self, record_type: str) -> str:
        table = TABLES.get(str(record_type or "").strip().lower())
        if not table:
            raise ValueError(f"record_type inválido: {record_type}")
        return table

    def list_records(self, record_type: str, *, q: str = "", status: str = "", date_from: str = "", date_to: str = "", bank: str = "", tag: str = "") -> list[dict]:
        table = self._table(record_type)
        conn = self._db_conn()
        cur = conn.cursor()
        sql = f"""
            SELECT id, record_code, title, status, base_date, reference_date, analysis_date,
                   measurement_point, bank, tag, instrument, meter_type, generated_html, generated_at,
                   created_at, updated_at
            FROM {table}
            WHERE active=1
        """
        params: list[object] = []
        q_norm = str(q or "").strip().lower()
        if q_norm:
            sql += """
              AND (
                    lower(COALESCE(record_code,'')) LIKE ?
                 OR lower(COALESCE(title,'')) LIKE ?
                 OR lower(COALESCE(measurement_point,'')) LIKE ?
                 OR lower(COALESCE(bank,'')) LIKE ?
                 OR lower(COALESCE(tag,'')) LIKE ?
                 OR lower(COALESCE(instrument,'')) LIKE ?
              )
            """
            like = f"%{q_norm}%"
            params.extend([like, like, like, like, like, like])
        if status:
            sql += " AND COALESCE(status,'')=?"
            params.append(status)
        if bank:
            sql += " AND COALESCE(bank,'')=?"
            params.append(bank)
        if tag:
            sql += " AND COALESCE(tag,'')=?"
            params.append(tag)
        if date_from:
            sql += " AND COALESCE(base_date, reference_date, analysis_date, '') >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND COALESCE(base_date, reference_date, analysis_date, '') <= ?"
            params.append(date_to)
        sql += " ORDER BY COALESCE(base_date, reference_date, analysis_date, '') DESC, updated_at DESC, id DESC"
        rows = [dict(row) for row in cur.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def get_record(self, record_type: str, record_id: int) -> dict | None:
        table = self._table(record_type)
        conn = self._db_conn()
        row = conn.execute(f"SELECT * FROM {table} WHERE id=? AND active=1", (record_id,)).fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        try:
            data["payload"] = json.loads(data.get("payload_json") or "{}")
        except Exception:
            data["payload"] = {}
        return data

    def find_rotina_by_key(self, base_date: str, measurement_point: str) -> dict | None:
        conn = self._db_conn()
        row = conn.execute(
            """
            SELECT * FROM sgmfm_rotina_diaria
            WHERE active=1 AND base_date=? AND measurement_point=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (base_date, measurement_point),
        ).fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        try:
            data["payload"] = json.loads(data.get("payload_json") or "{}")
        except Exception:
            data["payload"] = {}
        return data

    def upsert_record(self, record_type: str, data: dict) -> int:
        table = self._table(record_type)
        now = datetime.now().replace(microsecond=0).isoformat()
        payload_json = json.dumps(data.get("payload") or {}, ensure_ascii=False)
        row_id = data.get("id")
        existing = None
        conn = self._db_conn()
        cur = conn.cursor()
        if row_id:
            existing = cur.execute(f"SELECT * FROM {table} WHERE id=? AND active=1", (row_id,)).fetchone()
        elif record_type == "rotina" and data.get("base_date") and data.get("measurement_point"):
            existing = cur.execute(
                """
                SELECT * FROM sgmfm_rotina_diaria
                WHERE active=1 AND base_date=? AND measurement_point=?
                ORDER BY id DESC
                LIMIT 1
                """,
                (data["base_date"], data["measurement_point"]),
            ).fetchone()
        columns = [
            "record_code",
            "title",
            "status",
            "base_date",
            "reference_date",
            "analysis_date",
            "measurement_point",
            "bank",
            "tag",
            "instrument",
            "loop",
            "meter_type",
            "generated_html",
            "generated_at",
            "payload_json",
        ]
        values = (
            data.get("record_code", ""),
            data.get("title", ""),
            data.get("status", ""),
            data.get("base_date", ""),
            data.get("reference_date", ""),
            data.get("analysis_date", ""),
            data.get("measurement_point", ""),
            data.get("bank", ""),
            data.get("tag", ""),
            data.get("instrument", ""),
            data.get("loop", ""),
            data.get("meter_type", ""),
            data.get("generated_html", ""),
            data.get("generated_at", ""),
            payload_json,
        )
        if existing:
            sql = f"UPDATE {table} SET " + ", ".join(f"{col}=?" for col in columns) + ", updated_at=? WHERE id=?"
            cur.execute(sql, values + (now, existing["id"]))
            new_id = existing["id"]
        else:
            sql = f"""
                INSERT INTO {table}(
                    {", ".join(columns)}, active, created_at, updated_at
                ) VALUES(
                    {", ".join("?" for _ in columns)}, 1, ?, ?
                )
            """
            cur.execute(sql, values + (now, now))
            new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def delete_record(self, record_type: str, record_id: int) -> None:
        table = self._table(record_type)
        conn = self._db_conn()
        conn.execute(
            f"UPDATE {table} SET active=0, updated_at=? WHERE id=?",
            (datetime.now().replace(microsecond=0).isoformat(), record_id),
        )
        conn.commit()
        conn.close()

    def duplicate_record(self, record_type: str, record_id: int, new_record_code: str) -> int:
        source = self.get_record(record_type, record_id)
        if not source:
            raise ValueError("Registro não encontrado")
        source["id"] = None
        source["record_code"] = new_record_code
        source["generated_html"] = ""
        source["generated_at"] = ""
        return self.upsert_record(record_type, source)

    def get_visibility_prefs(self, record_type: str) -> dict:
        record_type = str(record_type or "").strip().lower()
        conn = self._db_conn()
        row = conn.execute(
            "SELECT visible_keys_json FROM sgmfm_visibility_prefs WHERE record_type=?",
            (record_type,),
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            return {"visible_keys": []}
        try:
            return {"visible_keys": json.loads(row[0])}
        except Exception:
            return {"visible_keys": []}

    def save_visibility_prefs(self, record_type: str, visible_keys: list[str]) -> None:
        record_type = str(record_type or "").strip().lower()
        now = datetime.now().replace(microsecond=0).isoformat()
        payload = json.dumps(list(dict.fromkeys(visible_keys or [])), ensure_ascii=False)
        conn = self._db_conn()
        cur = conn.cursor()
        row = cur.execute(
            "SELECT record_type FROM sgmfm_visibility_prefs WHERE record_type=?",
            (record_type,),
        ).fetchone()
        if row:
            cur.execute(
                "UPDATE sgmfm_visibility_prefs SET visible_keys_json=?, updated_at=? WHERE record_type=?",
                (payload, now, record_type),
            )
        else:
            cur.execute(
                "INSERT INTO sgmfm_visibility_prefs(record_type, visible_keys_json, updated_at) VALUES(?,?,?)",
                (record_type, payload, now),
            )
        conn.commit()
        conn.close()

    def summary_counts(self) -> dict:
        conn = self._db_conn()
        cur = conn.cursor()
        out = {}
        for record_type, table in TABLES.items():
            out[record_type] = {
                "total": cur.execute(f"SELECT COUNT(*) FROM {table} WHERE active=1").fetchone()[0] or 0,
                "with_html": cur.execute(f"SELECT COUNT(*) FROM {table} WHERE active=1 AND COALESCE(generated_html,'')<>''").fetchone()[0] or 0,
                "latest": cur.execute(
                    f"SELECT MAX(COALESCE(base_date, reference_date, analysis_date, created_at)) FROM {table} WHERE active=1"
                ).fetchone()[0]
                or "",
            }
        conn.close()
        return out
