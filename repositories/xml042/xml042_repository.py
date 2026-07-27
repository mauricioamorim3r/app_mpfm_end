from __future__ import annotations

import json
from datetime import datetime


class Xml042Repository:
    def __init__(self, db_conn, normalize_tag_name):
        self._db_conn = db_conn
        self._normalize_tag_name = normalize_tag_name

    def list_catalog(self, active_only: bool = False):
        conn = self._db_conn()
        sql = "SELECT * FROM well_catalog_042"
        if active_only:
            sql += " WHERE active=1"
        sql += " ORDER BY active DESC, enabled_042 DESC, well_operator_name, subsea_tag, id"
        rows = [dict(row) for row in conn.execute(sql).fetchall()]
        conn.close()
        return rows

    def upsert_catalog(self, payload: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        item_id = payload.get("id")
        values = {
            "well_operator_name": str(payload.get("well_operator_name") or "").strip(),
            "well_anp_name": str(payload.get("well_anp_name") or "").strip(),
            "cod_cadastro_poco": str(payload.get("cod_cadastro_poco") or "").strip(),
            "subsea_tag": str(payload.get("subsea_tag") or "").strip(),
            "cod_campo": str(payload.get("cod_campo") or "").strip(),
            "campo": str(payload.get("campo") or "").strip(),
            "cod_instalacao": str(payload.get("cod_instalacao") or "").strip(),
            "instalacao": str(payload.get("instalacao") or "").strip(),
            "enabled_042": 1 if payload.get("enabled_042", True) else 0,
            "active": 1 if payload.get("active", True) else 0,
            "valid_from": str(payload.get("valid_from") or "").strip(),
            "valid_to": str(payload.get("valid_to") or "").strip(),
            "notes": str(payload.get("notes") or "").strip(),
        }
        if not all([values["well_operator_name"], values["well_anp_name"], values["cod_cadastro_poco"], values["subsea_tag"]]):
            raise ValueError("well_operator_name, well_anp_name, cod_cadastro_poco e subsea_tag são obrigatórios")

        conn = self._db_conn()
        cur = conn.cursor()
        if item_id:
            cur.execute(
                """
                UPDATE well_catalog_042
                SET well_operator_name=?, well_anp_name=?, cod_cadastro_poco=?, subsea_tag=?,
                    cod_campo=?, campo=?, cod_instalacao=?, instalacao=?, enabled_042=?, active=?,
                    valid_from=?, valid_to=?, notes=?, updated_at=?
                WHERE id=?
                """,
                (
                    values["well_operator_name"],
                    values["well_anp_name"],
                    values["cod_cadastro_poco"],
                    values["subsea_tag"],
                    values["cod_campo"],
                    values["campo"],
                    values["cod_instalacao"],
                    values["instalacao"],
                    values["enabled_042"],
                    values["active"],
                    values["valid_from"],
                    values["valid_to"],
                    values["notes"],
                    now,
                    item_id,
                ),
            )
            record_id = int(item_id)
        else:
            cur.execute(
                """
                INSERT INTO well_catalog_042(
                    well_operator_name, well_anp_name, cod_cadastro_poco, subsea_tag, cod_campo, campo,
                    cod_instalacao, instalacao, enabled_042, active, valid_from, valid_to, notes, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    values["well_operator_name"],
                    values["well_anp_name"],
                    values["cod_cadastro_poco"],
                    values["subsea_tag"],
                    values["cod_campo"],
                    values["campo"],
                    values["cod_instalacao"],
                    values["instalacao"],
                    values["enabled_042"],
                    values["active"],
                    values["valid_from"],
                    values["valid_to"],
                    values["notes"],
                    now,
                    now,
                ),
            )
            record_id = int(cur.lastrowid)
        conn.commit()
        conn.close()
        return record_id

    def delete_catalog(self, item_id: int) -> None:
        conn = self._db_conn()
        conn.execute("DELETE FROM well_catalog_042 WHERE id=?", (item_id,))
        conn.commit()
        conn.close()

    def seed_catalog_if_empty(self, seed_rows: list[dict]) -> int:
        conn = self._db_conn()
        cur = conn.cursor()
        current = cur.execute("SELECT COUNT(*) FROM well_catalog_042").fetchone()[0] or 0
        if current:
            conn.close()
            return 0
        now = datetime.now().isoformat(timespec="seconds")
        inserted = 0
        for row in seed_rows:
            cur.execute(
                """
                INSERT INTO well_catalog_042(
                    well_operator_name, well_anp_name, cod_cadastro_poco, subsea_tag, cod_campo, campo,
                    cod_instalacao, instalacao, enabled_042, active, valid_from, valid_to, notes, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row.get("well_operator_name", ""),
                    row.get("well_anp_name", ""),
                    row.get("cod_cadastro_poco", ""),
                    row.get("subsea_tag", ""),
                    row.get("cod_campo", ""),
                    row.get("campo", ""),
                    row.get("cod_instalacao", ""),
                    row.get("instalacao", ""),
                    1 if row.get("enabled_042", True) else 0,
                    1 if row.get("active", True) else 0,
                    row.get("valid_from", ""),
                    row.get("valid_to", ""),
                    row.get("notes", ""),
                    now,
                    now,
                ),
            )
            inserted += 1
        conn.commit()
        conn.close()
        return inserted

    def list_daily_subsea_candidates(self, date_from: str, date_to: str, bank: str = "", production_day: str = ""):
        conn = self._db_conn()
        params: list[object] = [date_from, date_to]
        sql = """
            SELECT
                day_ref AS production_day,
                bank,
                COALESCE(tag,'') AS well_operator_name,
                COALESCE(instrument,'') AS subsea_tag,
                COALESCE(loop,'') AS loop,
                MAX(CASE WHEN metric_name='PVT vol Óleo (m³)' THEN metric_value END) AS oil_sm3,
                MAX(CASE WHEN metric_name='PVT vol Gás (Sm³)' THEN metric_value END) AS gas_sm3,
                MAX(CASE WHEN metric_name='PVT vol Água (m³)' THEN metric_value END) AS water_sm3,
                MAX(CASE WHEN metric_name='PVT mass Óleo (t)' THEN metric_value END) AS oil_t,
                MAX(CASE WHEN metric_name='PVT mass Gás (t)' THEN metric_value END) AS gas_t,
                MAX(CASE WHEN metric_name='PVT mass Água (t)' THEN metric_value END) AS water_t,
                COUNT(DISTINCT CASE WHEN row_kind='hourly' THEN hour_ref END) AS hours_available
            FROM measurements_curated
            WHERE row_kind IN ('daily', 'hourly')
              AND day_ref BETWEEN ? AND ?
              AND bank<>'' AND bank<>'SEP'
              AND UPPER(COALESCE(tipo,''))='SUBSEA'
        """
        if bank:
            sql += " AND bank=?"
            params.append(bank)
        if production_day:
            sql += " AND day_ref=?"
            params.append(production_day)
        sql += """
            GROUP BY day_ref, bank, COALESCE(tag,''), COALESCE(instrument,''), COALESCE(loop,'')
            ORDER BY day_ref DESC, bank, well_operator_name
        """
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def list_curated_rows(self, date_from: str, date_to: str, production_day: str = ""):
        conn = self._db_conn()
        params: list[object] = [date_from, date_to]
        sql = """
            SELECT * FROM tpoc_daily_potential_curated
            WHERE production_day BETWEEN ? AND ?
        """
        if production_day:
            sql += " AND production_day=?"
            params.append(production_day)
        sql += " ORDER BY production_day DESC, bank, well_operator_name, subsea_tag"
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def upsert_curated_candidate(self, payload: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        values = {
            "production_day": str(payload.get("production_day") or "").strip(),
            "bank": str(payload.get("bank") or "").strip().upper(),
            "well_operator_name": str(payload.get("well_operator_name") or "").strip(),
            "subsea_tag": str(payload.get("subsea_tag") or "").strip(),
            "source_daily_row_ref": str(payload.get("source_daily_row_ref") or "").strip(),
            "oil_sm3_d_curated": payload.get("oil_sm3_d_curated"),
            "gas_sm3_d_raw": payload.get("gas_sm3_d_raw"),
            "gas_1000sm3_d_curated": payload.get("gas_1000sm3_d_curated"),
            "water_sm3_d_curated": payload.get("water_sm3_d_curated"),
            "catalog_match_status": str(payload.get("catalog_match_status") or "").strip(),
            "catalog_match_id": payload.get("catalog_match_id"),
            "qa_flags": json.dumps(payload.get("qa_flags") or [], ensure_ascii=False),
            "approved_by_user": str(payload.get("approved_by_user") or "").strip(),
            "approved_at": str(payload.get("approved_at") or "").strip(),
        }
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tpoc_daily_potential_curated(
                production_day, bank, well_operator_name, subsea_tag, source_daily_row_ref,
                oil_sm3_d_curated, gas_sm3_d_raw, gas_1000sm3_d_curated, water_sm3_d_curated,
                catalog_match_status, catalog_match_id, qa_flags, approved_by_user, approved_at, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(production_day, bank, well_operator_name, subsea_tag) DO UPDATE SET
                source_daily_row_ref=excluded.source_daily_row_ref,
                oil_sm3_d_curated=excluded.oil_sm3_d_curated,
                gas_sm3_d_raw=excluded.gas_sm3_d_raw,
                gas_1000sm3_d_curated=excluded.gas_1000sm3_d_curated,
                water_sm3_d_curated=excluded.water_sm3_d_curated,
                catalog_match_status=excluded.catalog_match_status,
                catalog_match_id=excluded.catalog_match_id,
                qa_flags=excluded.qa_flags,
                approved_by_user=excluded.approved_by_user,
                approved_at=excluded.approved_at,
                updated_at=excluded.updated_at
            """,
            (
                values["production_day"],
                values["bank"],
                values["well_operator_name"],
                values["subsea_tag"],
                values["source_daily_row_ref"],
                values["oil_sm3_d_curated"],
                values["gas_sm3_d_raw"],
                values["gas_1000sm3_d_curated"],
                values["water_sm3_d_curated"],
                values["catalog_match_status"],
                values["catalog_match_id"],
                values["qa_flags"],
                values["approved_by_user"],
                values["approved_at"],
                now,
                now,
            ),
        )
        row = cur.execute(
            """
            SELECT id FROM tpoc_daily_potential_curated
            WHERE production_day=? AND bank=? AND well_operator_name=? AND subsea_tag=?
            """,
            (
                values["production_day"],
                values["bank"],
                values["well_operator_name"],
                values["subsea_tag"],
            ),
        ).fetchone()
        conn.commit()
        conn.close()
        return int(row[0]) if row else 0

    def save_document(self, payload: dict) -> int:
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO xml042_documents(
                production_day, cod_cadastro_poco, well_operator_name, subsea_tag, bank,
                filename, file_path, file_hash, status, generated_at, generated_by, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(production_day, cod_cadastro_poco) DO UPDATE SET
                well_operator_name=excluded.well_operator_name,
                subsea_tag=excluded.subsea_tag,
                bank=excluded.bank,
                filename=excluded.filename,
                file_path=excluded.file_path,
                file_hash=excluded.file_hash,
                status=excluded.status,
                generated_at=excluded.generated_at,
                generated_by=excluded.generated_by,
                payload_json=excluded.payload_json
            """,
            (
                payload["production_day"],
                payload["cod_cadastro_poco"],
                payload["well_operator_name"],
                payload["subsea_tag"],
                payload["bank"],
                payload["filename"],
                payload["file_path"],
                payload["file_hash"],
                payload.get("status", "generated"),
                payload["generated_at"],
                payload.get("generated_by", ""),
                json.dumps(payload.get("payload_json") or {}, ensure_ascii=False),
            ),
        )
        row = cur.execute(
            """
            SELECT id FROM xml042_documents
            WHERE production_day=? AND cod_cadastro_poco=?
            """,
            (payload["production_day"], payload["cod_cadastro_poco"]),
        ).fetchone()
        conn.commit()
        conn.close()
        return int(row[0]) if row else 0

    def list_documents(self, month: str = ""):
        conn = self._db_conn()
        params: list[object] = []
        sql = "SELECT * FROM xml042_documents"
        if month:
            sql += " WHERE substr(production_day,1,7)=?"
            params.append(month)
        sql += " ORDER BY production_day DESC, generated_at DESC, cod_cadastro_poco"
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def get_document(self, item_id: int):
        conn = self._db_conn()
        row = conn.execute("SELECT * FROM xml042_documents WHERE id=?", (item_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_document_by_key(self, production_day: str, cod_cadastro_poco: str):
        conn = self._db_conn()
        row = conn.execute(
            "SELECT * FROM xml042_documents WHERE production_day=? AND cod_cadastro_poco=?",
            (production_day, cod_cadastro_poco),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_catalog_by_code(self, cod_cadastro_poco: str):
        conn = self._db_conn()
        row = conn.execute(
            """
            SELECT * FROM well_catalog_042
            WHERE cod_cadastro_poco=?
            ORDER BY active DESC, enabled_042 DESC, updated_at DESC, id DESC
            LIMIT 1
            """,
            (str(cod_cadastro_poco or "").strip(),),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_imported_file_by_hash(self, file_hash: str):
        conn = self._db_conn()
        row = conn.execute(
            "SELECT * FROM xml042_imported_files WHERE file_hash=?",
            (str(file_hash or "").strip(),),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def save_imported_file(self, payload: dict) -> int:
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO xml042_imported_files(
                month_ref, production_day, cod_cadastro_poco, well_operator_name, subsea_tag, bank,
                filename, file_path, file_hash, file_size_bytes, import_status, import_message, imported_at, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload["month_ref"],
                payload["production_day"],
                payload["cod_cadastro_poco"],
                payload.get("well_operator_name", ""),
                payload.get("subsea_tag", ""),
                payload.get("bank", ""),
                payload["filename"],
                payload["file_path"],
                payload["file_hash"],
                int(payload.get("file_size_bytes") or 0),
                payload.get("import_status", "imported"),
                payload.get("import_message", ""),
                payload["imported_at"],
                json.dumps(payload.get("payload_json") or {}, ensure_ascii=False),
            ),
        )
        item_id = int(cur.lastrowid)
        conn.commit()
        conn.close()
        return item_id

    def upsert_imported_row(self, payload: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO xml042_imported_rows(
                month_ref, production_day, cod_cadastro_poco, well_operator_name, subsea_tag, bank,
                ind_tipo_teste, dha_teste, dha_aplicacao, ind_valido,
                oil_sm3, gas_1000sm3, water_sm3, latest_file_id, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(production_day, cod_cadastro_poco) DO UPDATE SET
                month_ref=excluded.month_ref,
                well_operator_name=excluded.well_operator_name,
                subsea_tag=excluded.subsea_tag,
                bank=excluded.bank,
                ind_tipo_teste=excluded.ind_tipo_teste,
                dha_teste=excluded.dha_teste,
                dha_aplicacao=excluded.dha_aplicacao,
                ind_valido=excluded.ind_valido,
                oil_sm3=excluded.oil_sm3,
                gas_1000sm3=excluded.gas_1000sm3,
                water_sm3=excluded.water_sm3,
                latest_file_id=excluded.latest_file_id,
                updated_at=excluded.updated_at
            """,
            (
                payload["month_ref"],
                payload["production_day"],
                payload["cod_cadastro_poco"],
                payload.get("well_operator_name", ""),
                payload.get("subsea_tag", ""),
                payload.get("bank", ""),
                payload.get("ind_tipo_teste", ""),
                payload.get("dha_teste", ""),
                payload.get("dha_aplicacao", ""),
                payload.get("ind_valido", ""),
                payload.get("oil_sm3"),
                payload.get("gas_1000sm3"),
                payload.get("water_sm3"),
                payload.get("latest_file_id"),
                now,
                now,
            ),
        )
        row = cur.execute(
            """
            SELECT id FROM xml042_imported_rows
            WHERE production_day=? AND cod_cadastro_poco=?
            """,
            (payload["production_day"], payload["cod_cadastro_poco"]),
        ).fetchone()
        conn.commit()
        conn.close()
        return int(row[0]) if row else 0

    def list_imported_rows(self, month: str = "", cod_cadastro_poco: str = ""):
        conn = self._db_conn()
        params: list[object] = []
        sql = """
            SELECT
                rows.*,
                files.filename,
                files.imported_at,
                files.import_status,
                files.import_message
            FROM xml042_imported_rows rows
            LEFT JOIN xml042_imported_files files ON files.id = rows.latest_file_id
        """
        filters = []
        if month:
            filters.append("rows.month_ref=?")
            params.append(month)
        if cod_cadastro_poco:
            filters.append("rows.cod_cadastro_poco LIKE ?")
            params.append(f"%{str(cod_cadastro_poco).strip()}%")
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY rows.cod_cadastro_poco, rows.production_day, rows.id"
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def list_imported_files(self, month: str = "", cod_cadastro_poco: str = ""):
        conn = self._db_conn()
        params: list[object] = []
        sql = "SELECT * FROM xml042_imported_files"
        filters = []
        if month:
            filters.append("month_ref=?")
            params.append(month)
        if cod_cadastro_poco:
            filters.append("cod_cadastro_poco LIKE ?")
            params.append(f"%{str(cod_cadastro_poco).strip()}%")
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY imported_at DESC, filename"
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows
