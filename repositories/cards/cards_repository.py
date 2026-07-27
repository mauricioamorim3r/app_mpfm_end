from __future__ import annotations

import json
from datetime import datetime


class CardsRepository:
    def __init__(self, db_conn):
        self._db_conn = db_conn

    @staticmethod
    def _normalize_date_input(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return raw

    def get_latest_daily_day(self) -> str:
        conn = self._db_conn()
        cur = conn.cursor()
        value = cur.execute("SELECT MAX(day_ref) FROM measurements_curated WHERE row_kind='daily'").fetchone()[0] or ""
        conn.close()
        return value

    def get_latest_card_day(self) -> str:
        conn = self._db_conn()
        cur = conn.cursor()
        value = cur.execute("SELECT MAX(production_date) FROM daily_cards WHERE is_active=1").fetchone()[0] or ""
        conn.close()
        return value

    def fetch_card_override(self, production_date: str, bank: str, card_type: str, tag: str = "", instrument: str = "") -> dict | None:
        conn = self._db_conn()
        row = conn.execute(
            "SELECT * FROM daily_cards WHERE production_date=? AND bank=? AND card_type=? AND COALESCE(tag,'')=? AND COALESCE(instrument,'')=? AND is_active=1 AND COALESCE(is_official,1)=1 ORDER BY id DESC LIMIT 1",
            (production_date, bank, card_type, tag or "", instrument or ""),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def upsert_card_override(self, payload: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        production_date = payload.get("production_date") or ""
        bank = payload.get("bank") or ""
        card_type = payload.get("card_type") or ""
        tag = payload.get("tag") or ""
        instrument = payload.get("instrument") or ""
        card_id_in = payload.get("id") or payload.get("card_id")
        force_new = bool(payload.get("force_new"))
        conn = self._db_conn()
        cur = conn.cursor()
        row = None
        if card_id_in:
            row = cur.execute("SELECT * FROM daily_cards WHERE id=? AND is_active=1", (card_id_in,)).fetchone()
        if row is None and not force_new:
            row = cur.execute(
                "SELECT * FROM daily_cards WHERE production_date=? AND bank=? AND card_type=? AND COALESCE(tag,'')=? AND COALESCE(instrument,'')=? AND is_active=1 AND COALESCE(is_official,1)=1 ORDER BY id DESC LIMIT 1",
                (production_date, bank, card_type, tag, instrument),
            ).fetchone()
        fields = {
            "title": payload.get("title", "") or "",
            "flow_velocity_ms": payload.get("flow_velocity_ms"),
            "dp_value": payload.get("dp_value"),
            "sep_test_aligned": payload.get("sep_test_aligned", "") or "",
            "observations": payload.get("observations", "") or "",
            "manual_payload": json.dumps(payload.get("manual_payload") or {}, ensure_ascii=False),
        }
        if row:
            old = dict(row)
            cur.execute(
                "UPDATE daily_cards SET title=?, flow_velocity_ms=?, dp_value=?, sep_test_aligned=?, observations=?, manual_payload=?, updated_at=? WHERE id=?",
                (fields["title"], fields["flow_velocity_ms"], fields["dp_value"], fields["sep_test_aligned"], fields["observations"], fields["manual_payload"], now, old["id"]),
            )
            for field_name, new_value in fields.items():
                old_value = old.get(field_name)
                if (old_value or "") != (new_value or ""):
                    cur.execute(
                        "INSERT INTO daily_card_edits(daily_card_id, field_name, old_value, new_value, reason, edited_at) VALUES(?,?,?,?,?,?)",
                        (old["id"], field_name, "" if old_value is None else str(old_value), "" if new_value is None else str(new_value), payload.get("reason", "manual_edit"), now),
                    )
            card_id = old["id"]
        else:
            existing_official = cur.execute(
                "SELECT id FROM daily_cards WHERE production_date=? AND bank=? AND card_type=? AND COALESCE(tag,'')=? AND COALESCE(instrument,'')=? AND is_active=1 AND COALESCE(is_official,1)=1 ORDER BY id DESC LIMIT 1",
                (production_date, bank, card_type, tag, instrument),
            ).fetchone()
            is_official = 0 if existing_official else 1
            status = "pending" if existing_official else "official"
            cur.execute(
                "INSERT INTO daily_cards(production_date, bank, card_type, tag, instrument, title, flow_velocity_ms, dp_value, sep_test_aligned, observations, manual_payload, created_at, updated_at, is_active, is_official, resolution_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
                (production_date, bank, card_type, tag, instrument, fields["title"], fields["flow_velocity_ms"], fields["dp_value"], fields["sep_test_aligned"], fields["observations"], fields["manual_payload"], now, now, is_official, status),
            )
            card_id = cur.lastrowid
        conn.commit()
        conn.close()
        return card_id

    def list_daily_measurement_rows(self, date_from: str, date_to: str, bank: str = "", limit: int = None, offset: int = 0):
        """
        ✅ OTIMIZADO: Adiciona paginação opcional para evitar carregar milhões de registros

        Args:
            limit: Número máximo de registros (None = sem limite, padrão antigo)
            offset: Offset para paginação (padrão: 0)
        """
        conn = self._db_conn()
        params = [date_from, date_to]
        sql = "SELECT day_ref, bank, loop, tipo, tag, instrument, metric_name, metric_value FROM measurements_curated WHERE row_kind='daily' AND day_ref BETWEEN ? AND ?"
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        sql += " ORDER BY day_ref, bank, tipo, tag, instrument"

        # Adiciona paginação se solicitado
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def list_recon_measurement_rows(self, date_from: str, date_to: str, bank: str = "", limit: int = None, offset: int = 0):
        """
        ✅ OTIMIZADO: Adiciona paginação opcional

        Args:
            limit: Número máximo de registros (None = sem limite)
            offset: Offset para paginação
        """
        conn = self._db_conn()
        params = [date_from, date_to]
        sql = "SELECT day_ref, bank, tag, metric_name, metric_value FROM measurements_curated WHERE row_kind='recon' AND day_ref BETWEEN ? AND ?"
        if bank:
            sql += " AND bank=?"
            params.append(bank)

        # Adiciona paginação se solicitado
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def list_sep_measurement_rows(self, date_from: str, date_to: str, limit: int = None, offset: int = 0):
        """
        ✅ OTIMIZADO: Adiciona paginação opcional

        Args:
            limit: Número máximo de registros (None = sem limite)
            offset: Offset para paginação
        """
        conn = self._db_conn()
        params = [date_from, date_to]
        sql = "SELECT day_ref, bank, tag, metric_name, metric_value FROM measurements_curated WHERE row_kind='sep' AND bank='SEP' AND COALESCE(is_official,1)=1 AND day_ref BETWEEN ? AND ?"

        # Adiciona paginação se solicitado
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def list_sep_alignments(self, date_from: str, date_to: str, bank: str = ""):
        conn = self._db_conn()
        params = [date_from, date_to]
        sql = "SELECT * FROM sep_alignments WHERE is_active=1 AND production_date BETWEEN ? AND ?"
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def list_manual_cards(self, date_from: str, date_to: str, bank: str = ""):
        conn = self._db_conn()
        params = [date_from, date_to]
        sql = "SELECT * FROM daily_cards WHERE is_active=1 AND COALESCE(is_official,1)=1 AND production_date BETWEEN ? AND ? AND card_type='Manual'"
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def list_card_duplicates(self, date_from: str, date_to: str, bank: str = "") -> list[dict]:
        conn = self._db_conn()
        cur = conn.cursor()

        # ✅ OTIMIZADO: Query única com window function ao invés de N+1
        sql = """
            WITH duplicate_groups AS (
                SELECT
                    production_date, bank, card_type,
                    COALESCE(tag,'') AS tag,
                    COALESCE(instrument,'') AS instrument,
                    COUNT(*) OVER (PARTITION BY production_date, bank, card_type, COALESCE(tag,''), COALESCE(instrument,'')) AS candidates,
                    SUM(CASE WHEN COALESCE(is_official,1)=1 THEN 1 ELSE 0 END) OVER (PARTITION BY production_date, bank, card_type, COALESCE(tag,''), COALESCE(instrument,'')) AS official_count,
                    id, title, observations, is_official, resolution_status, created_at, updated_at
                FROM daily_cards
                WHERE is_active=1 AND production_date BETWEEN ? AND ?
        """
        params = [date_from, date_to]
        if bank:
            sql += " AND bank=?"
            params.append(bank)

        sql += """
            )
            SELECT * FROM duplicate_groups
            WHERE candidates > 1
            ORDER BY production_date DESC, bank, card_type,
                     COALESCE(is_official,0) DESC, id DESC
        """

        # Agrupa resultados
        groups_dict = {}
        for row in cur.execute(sql, params).fetchall():
            # Cria chave única para o grupo
            key = (row[0], row[1], row[2], row[3], row[4])  # production_date, bank, card_type, tag, instrument

            if key not in groups_dict:
                groups_dict[key] = {
                    "production_date": row[0],
                    "bank": row[1],
                    "card_type": row[2],
                    "tag": row[3],
                    "instrument": row[4],
                    "candidates": row[5],
                    "official_count": row[6],
                    "items": []
                }

            # Adiciona item ao grupo
            groups_dict[key]["items"].append({
                "id": row[7],
                "title": row[8],
                "observations": row[9],
                "is_official": row[10],
                "resolution_status": row[11],
                "created_at": row[12],
                "updated_at": row[13]
            })

        conn.close()
        return list(groups_dict.values())

    def get_card_duplicate_ids(self, production_date: str, bank: str, card_type: str, tag: str, instrument: str) -> list[int]:
        conn = self._db_conn()
        cur = conn.cursor()
        ids = [
            row["id"]
            for row in cur.execute(
                "SELECT id FROM daily_cards WHERE is_active=1 AND production_date=? AND bank=? AND card_type=? AND COALESCE(tag,'')=? AND COALESCE(instrument,'')=?",
                (production_date, bank, card_type, tag, instrument),
            ).fetchall()
        ]
        conn.close()
        return ids

    def resolve_card_duplicates(self, ids: list[int], action: str, official_id, delete_ids: list[int]) -> int | None:
        conn = self._db_conn()
        cur = conn.cursor()
        now = datetime.now().isoformat(timespec="seconds")
        chosen = None
        if action == "delete" and delete_ids:
            q = ",".join("?" * len(delete_ids))
            cur.execute(
                f"UPDATE daily_cards SET is_active=0, is_official=0, resolution_status='deleted', updated_at=? WHERE id IN ({q})",
                [now] + delete_ids,
            )
        elif action == "pending":
            q = ",".join("?" * len(ids))
            cur.execute(
                f"UPDATE daily_cards SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})",
                [now] + ids,
            )
        else:
            q = ",".join("?" * len(ids))
            cur.execute(
                f"UPDATE daily_cards SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})",
                [now] + ids,
            )
            cur.execute(
                "UPDATE daily_cards SET is_official=1, resolution_status='manual_official', updated_at=? WHERE id=?",
                (now, official_id),
            )
            chosen = official_id
        conn.commit()
        conn.close()
        return chosen

    def get_card_by_id(self, card_id: int):
        conn = self._db_conn()
        row = conn.execute("SELECT * FROM daily_cards WHERE id=?", (card_id,)).fetchone()
        conn.close()
        return row

    def soft_delete_card(self, card_id: int) -> None:
        conn = self._db_conn()
        conn.execute(
            "UPDATE daily_cards SET is_active=0, is_official=0, resolution_status='deleted', updated_at=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), card_id),
        )
        conn.commit()
        conn.close()

    def recompute_card_resolution(self, production_date: str, bank: str, card_type: str, tag: str = "", instrument: str = ""):
        conn = self._db_conn()
        cur = conn.cursor()
        now = datetime.now().isoformat(timespec="seconds")
        rows = cur.execute(
            "SELECT id FROM daily_cards WHERE production_date=? AND bank=? AND card_type=? AND COALESCE(tag,'')=? AND COALESCE(instrument,'')=? AND is_active=1 ORDER BY COALESCE(is_official,0) DESC, id DESC",
            (production_date, bank, card_type, tag or "", instrument or ""),
        ).fetchall()
        if not rows:
            conn.commit()
            conn.close()
            return None
        chosen = rows[0][0]
        ids = [row[0] for row in rows]
        q = ",".join("?" * len(ids))
        cur.execute(f"UPDATE daily_cards SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})", [now] + ids)
        cur.execute("UPDATE daily_cards SET is_official=1, resolution_status='official', updated_at=? WHERE id=?", (now, chosen))
        conn.commit()
        conn.close()
        return chosen

    def list_deadlines(self, active_only: int):
        conn = self._db_conn()
        rows = conn.execute(
            "SELECT * FROM deadline_items WHERE (?=0 OR is_active=1) ORDER BY COALESCE(due_date,''), id",
            (active_only,),
        ).fetchall()
        conn.close()
        return rows

    def upsert_deadline(self, body: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        start_date = self._normalize_date_input(body.get("start_date", ""))
        due_date = self._normalize_date_input(body.get("due_date", ""))
        vals = (
            body.get("subject", "").strip(),
            body.get("category", "").strip(),
            start_date,
            due_date,
            body.get("periodicity", "custom").strip(),
            int(body.get("periodicity_days") or 0),
            body.get("notes", "").strip(),
            body.get("icon", "⏳").strip() or "⏳",
            body.get("source_ref", "").strip(),
            body.get("source_file", "").strip(),
            body.get("norm_ref", "").strip(),
            body.get("evidence_required", "").strip(),
            body.get("responsible_area", "").strip(),
            body.get("trigger_event", "").strip(),
            body.get("risk_level", "").strip(),
            body.get("recommended_action", "").strip(),
            self._normalize_date_input(body.get("completion_date", "")),
            body.get("source_status", "").strip(),
        )
        conn = self._db_conn()
        cur = conn.cursor()
        item_id = body.get("id")
        if item_id:
            cur.execute(
                """
                UPDATE deadline_items
                SET subject=?, category=?, start_date=?, due_date=?, periodicity=?, periodicity_days=?,
                    notes=?, icon=?, source_ref=?, source_file=?, norm_ref=?, evidence_required=?,
                    responsible_area=?, trigger_event=?, risk_level=?, recommended_action=?,
                    completion_date=?, source_status=?, updated_at=?
                WHERE id=?
                """,
                vals + (now, item_id),
            )
            new_id = item_id
        else:
            cur.execute(
                """
                INSERT INTO deadline_items(
                    subject, category, start_date, due_date, periodicity, periodicity_days,
                    notes, icon, source_ref, source_file, norm_ref, evidence_required,
                    responsible_area, trigger_event, risk_level, recommended_action,
                    completion_date, source_status, is_active, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)
                """,
                vals + (now, now),
            )
            new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def delete_deadline(self, item_id: int) -> None:
        conn = self._db_conn()
        conn.execute(
            "UPDATE deadline_items SET is_active=0, updated_at=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), item_id),
        )
        conn.commit()
        conn.close()
