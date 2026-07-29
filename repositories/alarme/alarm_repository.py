from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable


class AlarmRepository:
    def __init__(self, db_conn: Callable[[], Any]):
        self.db_conn = db_conn

    def _source_refs(self, source_ref: str = "") -> list[str]:
        return [part.strip() for part in str(source_ref or "").split(";") if part.strip()]

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _dicts(self, rows) -> list[dict]:
        return [dict(row) for row in rows]

    def get_reference_catalog(self) -> dict[str, list[dict]]:
        conn = self.db_conn()
        try:
            rows = conn.execute(
                """
                SELECT domain, code, label, description, sort_order, is_terminal, is_default
                FROM alarm_reference_values
                WHERE active=1
                ORDER BY domain, sort_order, label
                """
            ).fetchall()
            catalog: dict[str, list[dict]] = {}
            for row in rows:
                item = dict(row)
                catalog.setdefault(item.pop("domain"), []).append(item)
            return catalog
        finally:
            conn.close()

    def summary_counts(self, source_ref: str = "") -> dict:
        conn = self.db_conn()
        try:
            params: list[Any] = []
            where = "active=1"
            source_refs = self._source_refs(source_ref)
            if source_refs:
                where += f" AND source_ref IN ({', '.join('?' for _ in source_refs)})"
                params.extend(source_refs)

            def scalar(sql: str, extra: tuple[Any, ...] = ()) -> int:
                return int((conn.execute(sql.format(where=where), (*params, *extra)).fetchone() or [0])[0] or 0)

            summary = {
                "total_active": scalar("SELECT COUNT(*) FROM alarm_records WHERE {where}"),
                "events": scalar("SELECT COUNT(*) FROM alarm_records WHERE {where} AND record_type='event'"),
                "incidents": scalar("SELECT COUNT(*) FROM alarm_records WHERE {where} AND record_type='incident'"),
                "open": scalar("SELECT COUNT(*) FROM alarm_records WHERE {where} AND status_code='open'"),
                "critical": scalar("SELECT COUNT(*) FROM alarm_records WHERE {where} AND severity_code='critical'"),
                "in_progress": scalar("SELECT COUNT(*) FROM alarm_records WHERE {where} AND status_code='in_progress'"),
                "monitoring": scalar("SELECT COUNT(*) FROM alarm_records WHERE {where} AND status_code='monitoring'"),
                "actions_open": 0,
                "overdue": 0,
            }
            action_filter = "a.active=1 AND a.status_code <> 'closed'"
            if source_refs:
                action_filter += f" AND r.source_ref IN ({', '.join('?' for _ in source_refs)})"
            summary["actions_open"] = int(conn.execute(
                f"""
                SELECT COUNT(*)
                FROM alarm_actions a
                LEFT JOIN alarm_records r ON r.id=a.alarm_id
                WHERE {action_filter}
                """,
                params,
            ).fetchone()[0] or 0)
            summary["overdue"] = int(conn.execute(
                f"""
                SELECT COUNT(*)
                FROM alarm_actions a
                LEFT JOIN alarm_records r ON r.id=a.alarm_id
                WHERE {action_filter} AND a.due_date<>'' AND a.due_date < date('now')
                """,
                params,
            ).fetchone()[0] or 0)
            return summary
        finally:
            conn.close()

    def list_alarms(self, **filters) -> list[dict]:
        conn = self.db_conn()
        try:
            clauses = []
            params: list[Any] = []
            if filters.get("active_only", True):
                clauses.append("active=1")
            source_refs = self._source_refs(filters.get("source_ref", ""))
            if source_refs:
                clauses.append(f"source_ref IN ({', '.join('?' for _ in source_refs)})")
                params.extend(source_refs)
            mapping = {
                "record_type": "record_type",
                "status": "status_code",
                "severity": "severity_code",
                "priority": "priority_code",
                "category": "category_code",
                "family": "family_code",
                "bank": "bank",
                "measurement_point": "measurement_point",
                "tag": "tag",
                "owner": "owner",
                "source_sheet": "source_sheet",
            }
            for key, col in mapping.items():
                value = str(filters.get(key) or "").strip()
                if value:
                    clauses.append(f"{col}=?")
                    params.append(value)
            if filters.get("date_from"):
                clauses.append("COALESCE(production_date, event_at, detected_at) >= ?")
                params.append(filters["date_from"])
            if filters.get("date_to"):
                clauses.append("COALESCE(production_date, event_at, detected_at) <= ?")
                params.append(filters["date_to"])
            q = str(filters.get("q") or "").strip()
            if q:
                like = f"%{q}%"
                clauses.append("(title LIKE ? OR message LIKE ? OR tag LIKE ? OR instrument LIKE ? OR external_code LIKE ?)")
                params.extend([like, like, like, like, like])
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            limit = int(filters.get("limit") or 0)
            offset = int(filters.get("offset") or 0)
            sql = f"SELECT * FROM alarm_records{where} ORDER BY COALESCE(event_at, detected_at, production_date) DESC, id DESC"
            if limit > 0:
                sql += " LIMIT ?"
                params.append(limit)
            if offset > 0:
                sql += " OFFSET ?"
                params.append(offset)
            return self._dicts(conn.execute(sql, params).fetchall())
        finally:
            conn.close()

    def get_alarm(self, alarm_id: int) -> dict | None:
        conn = self.db_conn()
        try:
            row = conn.execute("SELECT * FROM alarm_records WHERE id=?", (alarm_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_actions(self, alarm_id: int) -> list[dict]:
        conn = self.db_conn()
        try:
            return self._dicts(conn.execute(
                "SELECT * FROM alarm_actions WHERE alarm_id=? AND active=1 ORDER BY due_date, id",
                (alarm_id,),
            ).fetchall())
        finally:
            conn.close()

    def list_audit(self, alarm_id: int) -> list[dict]:
        conn = self.db_conn()
        try:
            return self._dicts(conn.execute(
                "SELECT * FROM alarm_audit_log WHERE alarm_id=? ORDER BY created_at DESC, id DESC LIMIT 100",
                (alarm_id,),
            ).fetchall())
        finally:
            conn.close()

    def save_alarm(self, payload: dict) -> int:
        conn = self.db_conn()
        try:
            now = self._now()
            data = dict(payload)
            data.setdefault("created_at", now)
            data["updated_at"] = now
            if not data.get("title"):
                data["title"] = data.get("message") or data.get("external_code") or "Alarme FCS320"
            if not isinstance(data.get("payload_json"), str):
                data["payload_json"] = json.dumps(data.get("payload_json") or {}, ensure_ascii=False)
            columns = [row[1] for row in conn.execute("PRAGMA table_info(alarm_records)").fetchall()]
            allowed = {key: value for key, value in data.items() if key in columns and key != "id"}
            existing_id = None
            if allowed.get("source_kind") and allowed.get("source_ref") and allowed.get("external_code"):
                row = conn.execute(
                    """
                    SELECT id FROM alarm_records
                    WHERE source_kind=? AND source_ref=? AND source_sheet=? AND record_type=? AND external_code=?
                    LIMIT 1
                    """,
                    (
                        allowed.get("source_kind", ""),
                        allowed.get("source_ref", ""),
                        allowed.get("source_sheet", ""),
                        allowed.get("record_type", "event"),
                        allowed.get("external_code", ""),
                    ),
                ).fetchone()
                existing_id = int(row[0]) if row else None
            if existing_id:
                assignments = ", ".join(f"{key}=?" for key in allowed if key != "created_at")
                values = [value for key, value in allowed.items() if key != "created_at"]
                conn.execute(f"UPDATE alarm_records SET {assignments} WHERE id=?", (*values, existing_id))
                alarm_id = existing_id
            else:
                cols = list(allowed.keys())
                placeholders = ", ".join("?" for _ in cols)
                conn.execute(
                    f"INSERT INTO alarm_records({', '.join(cols)}) VALUES({placeholders})",
                    [allowed[key] for key in cols],
                )
                alarm_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            conn.execute(
                "INSERT INTO alarm_audit_log(alarm_id, event_type, notes, created_at) VALUES(?, ?, ?, ?)",
                (alarm_id, "save", "Registro salvo", now),
            )
            conn.commit()
            return alarm_id
        finally:
            conn.close()

    def set_alarm_status(self, alarm_id: int, status_code: str, notes: str = "", acknowledged_by: str = "") -> None:
        conn = self.db_conn()
        try:
            row = conn.execute("SELECT status_code FROM alarm_records WHERE id=?", (alarm_id,)).fetchone()
            if not row:
                raise ValueError("Alarme nao encontrado")
            now = self._now()
            fields = ["status_code=?", "updated_at=?"]
            values: list[Any] = [status_code, now]
            if status_code in {"in_progress", "monitoring"}:
                fields.append("acknowledged_at=?")
                values.append(now)
                if acknowledged_by:
                    fields.append("acknowledged_by=?")
                    values.append(acknowledged_by)
            if status_code == "closed":
                fields.append("closed_at=?")
                values.append(now)
            values.append(alarm_id)
            conn.execute(f"UPDATE alarm_records SET {', '.join(fields)} WHERE id=?", values)
            conn.execute(
                """
                INSERT INTO alarm_audit_log(alarm_id, event_type, field_name, old_value, new_value, notes, created_at)
                VALUES(?, 'status_change', 'status_code', ?, ?, ?, ?)
                """,
                (alarm_id, row[0], status_code, notes, now),
            )
            conn.commit()
        finally:
            conn.close()

    def add_action(self, alarm_id: int, payload: dict) -> int:
        conn = self.db_conn()
        try:
            now = self._now()
            if not conn.execute("SELECT id FROM alarm_records WHERE id=?", (alarm_id,)).fetchone():
                raise ValueError("Alarme nao encontrado")
            data = dict(payload)
            data["alarm_id"] = alarm_id
            data.setdefault("created_at", now)
            data["updated_at"] = now
            if not isinstance(data.get("payload_json"), str):
                data["payload_json"] = json.dumps(data.get("payload_json") or {}, ensure_ascii=False)
            columns = [row[1] for row in conn.execute("PRAGMA table_info(alarm_actions)").fetchall()]
            allowed = {key: value for key, value in data.items() if key in columns and key != "id"}
            cols = list(allowed.keys())
            placeholders = ", ".join("?" for _ in cols)
            conn.execute(f"INSERT INTO alarm_actions({', '.join(cols)}) VALUES({placeholders})", [allowed[key] for key in cols])
            action_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            conn.execute(
                "INSERT INTO alarm_audit_log(alarm_id, action_id, event_type, notes, created_at) VALUES(?, ?, 'action_add', ?, ?)",
                (alarm_id, action_id, allowed.get("description", ""), now),
            )
            conn.commit()
            return action_id
        finally:
            conn.close()
