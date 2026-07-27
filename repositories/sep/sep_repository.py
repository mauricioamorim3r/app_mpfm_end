from __future__ import annotations

from datetime import datetime


class SepRepository:
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_latest_sep_day(self) -> str:
        conn = self._db_conn()
        cur = conn.cursor()
        value = (
            cur.execute("SELECT MAX(day_ref) FROM measurements_curated WHERE row_kind='sep'").fetchone()[0]
            or cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0]
            or ""
        )
        conn.close()
        return value

    def list_sep_measurements(self, date_from: str, date_to: str, unit: str = "") -> list[dict]:
        conn = self._db_conn()
        cur = conn.cursor()
        sql = """
            SELECT id, day_ref, hour_ref, bank, tag, metric_name, metric_value, metric_unit, source_file, source_record_id, COALESCE(is_official,1) AS is_official, created_at
            FROM measurements_curated
            WHERE row_kind='sep' AND COALESCE(is_official,1)=1 AND day_ref BETWEEN ? AND ?
        """
        params = [date_from, date_to]
        if unit:
            sql += " AND bank=?"
            params.append(unit)
        sql += " ORDER BY day_ref DESC, COALESCE(hour_ref,-1), bank, tag, metric_name"
        rows = [dict(row) for row in cur.execute(sql, params).fetchall()]
        conn.close()
        return rows

    def list_sep_alignment_map(self, date_from: str, date_to: str) -> dict[str, str]:
        conn = self._db_conn()
        cur = conn.cursor()
        mapping = {}
        for row in cur.execute(
            """
            SELECT production_date, GROUP_CONCAT(bank, ', ') AS banks
            FROM sep_alignments
            WHERE is_active=1 AND production_date BETWEEN ? AND ?
            GROUP BY production_date
            """,
            (date_from, date_to),
        ).fetchall():
            mapping[row["production_date"]] = row["banks"] or ""
        conn.close()
        return mapping

    def get_sep_alignment(self, bank: str, production_date: str) -> dict | None:
        if not bank or not production_date:
            return None
        conn = self._db_conn()
        row = conn.execute(
            "SELECT id, production_date, bank, mpfm_tag, sep_meter_id, sep_tag, notes, is_active, is_official, resolution_status FROM sep_alignments WHERE production_date=? AND bank=? AND is_active=1 AND COALESCE(is_official,1)=1 ORDER BY id DESC LIMIT 1",
            (production_date, bank),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def recompute_alignment_resolution(self, production_date: str, bank: str):
        conn = self._db_conn()
        cur = conn.cursor()
        now = datetime.now().isoformat(timespec="seconds")
        rows = cur.execute(
            "SELECT id FROM sep_alignments WHERE production_date=? AND bank=? AND is_active=1 ORDER BY COALESCE(is_official,0) DESC, id DESC",
            (production_date, bank),
        ).fetchall()
        if not rows:
            conn.commit()
            conn.close()
            return None
        chosen = rows[0][0]
        ids = [row[0] for row in rows]
        q = ",".join("?" * len(ids))
        cur.execute(f"UPDATE sep_alignments SET is_official=0, resolution_status='pending', updated_at=? WHERE id IN ({q})", [now] + ids)
        cur.execute("UPDATE sep_alignments SET is_official=1, resolution_status='official', updated_at=? WHERE id=?", (now, chosen))
        conn.commit()
        conn.close()
        return chosen

    def rebuild_sep_summary_from_detail(
        self,
        production_date: str,
        *,
        unit_code: str = "",
        run_id: int | None = None,
        excel_file: str = "",
    ) -> dict:
        conn = self._db_conn()
        conn.row_factory = getattr(conn, "row_factory", None) or None
        cur = conn.cursor()
        oil_source = cur.execute(
            """
            SELECT id, source_file, meter_id
            FROM sep_source_files
            WHERE production_date=? AND fluid_kind='sep_oleo' AND is_active=1 AND is_official=1
            ORDER BY id DESC
            LIMIT 1
            """,
            (production_date,),
        ).fetchone()
        if not oil_source:
            conn.close()
            return {"production_date": production_date, "rebuilt": False, "reason": "missing_official_oil_source"}

        source_record_id = oil_source["id"]
        source_file = oil_source["source_file"] or ""
        instrument = unit_code or ""
        now = datetime.now().isoformat(timespec="seconds")

        rows = cur.execute(
            """
            SELECT row_kind, hour_ref, metric_name, metric_value
            FROM measurements_curated
            WHERE day_ref=?
              AND bank='SEP'
              AND row_kind IN ('sep_oleo_detail','sep_gas_detail','sep_agua_detail')
              AND COALESCE(is_official,1)=1
            ORDER BY COALESCE(hour_ref, 999), row_kind, metric_name
            """,
            (production_date,),
        ).fetchall()
        if not rows:
            conn.close()
            return {"production_date": production_date, "rebuilt": False, "reason": "missing_official_detail_rows"}

        grouped: dict[object, dict[str, dict[str, float]]] = {}
        for row_kind, hour_ref, metric_name, metric_value in rows:
            grouped.setdefault(hour_ref, {}).setdefault(row_kind, {})[metric_name] = metric_value

        sep_units = {
            "oil_m3": "m³",
            "oil_t": "t",
            "gas_t": "t",
            "water_t": "t",
            "hc_t": "t",
            "total_t": "t",
            "temp": "°C",
            "pressure_barg": "barg",
            "density_sim": "kg/m³",
        }

        def _metric(block: dict, *names):
            for name in names:
                if name in block and block[name] is not None:
                    return float(block[name])
            return None

        def _sum_pair(a, b):
            if a is None or b is None:
                return None
            return float(a) + float(b)

        rebuilt_rows = []
        for hour_ref, blocks in grouped.items():
            oil = blocks.get("sep_oleo_detail", {})
            gas = blocks.get("sep_gas_detail", {})
            water = blocks.get("sep_agua_detail", {})
            oil_t = _metric(oil, "Mass_ton")
            gas_t = _metric(gas, "Mass_t")
            water_t = _metric(water, "Mass_ton")
            hc_t = _sum_pair(oil_t, gas_t)
            total_t = _sum_pair(hc_t, water_t)
            payload = {
                "temp": _metric(oil, "Temperature_degC"),
                "pressure_barg": _metric(oil, "Pressure_barg") or (
                    (_metric(oil, "Pressure_kPa") / 100.0) if _metric(oil, "Pressure_kPa") is not None else None
                ),
                "oil_m3": _metric(oil, "GV_m3", "IV_m3", "GSV_sm3"),
                "oil_t": oil_t,
                "gas_t": gas_t,
                "water_t": water_t,
                "hc_t": hc_t,
                "total_t": total_t,
            }
            for metric_name, metric_value in payload.items():
                if metric_value is None:
                    continue
                rebuilt_rows.append(
                    (
                        run_id,
                        source_file,
                        source_record_id,
                        excel_file,
                        "SEP",
                        "sep",
                        production_date,
                        hour_ref,
                        "SEP",
                        "",
                        "",
                        "SEP",
                        instrument,
                        metric_name,
                        float(metric_value),
                        sep_units.get(metric_name, ""),
                        1,
                        now,
                    )
                )

        cur.execute("DELETE FROM measurements_curated WHERE row_kind='sep' AND day_ref=?", (production_date,))
        if rebuilt_rows:
            cur.executemany(
                """
                INSERT INTO measurements_curated(
                    run_id, source_file, source_record_id, excel_file, sheet_name, row_kind, day_ref, hour_ref,
                    bank, loop, tipo, tag, instrument, metric_name, metric_value, metric_unit, is_official, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                rebuilt_rows,
            )
        conn.commit()
        conn.close()
        return {
            "production_date": production_date,
            "rebuilt": bool(rebuilt_rows),
            "rows_inserted": len(rebuilt_rows),
            "source_record_id": source_record_id,
            "source_file": source_file,
            "instrument": instrument,
        }

    def get_latest_fluid_day(self, row_kind: str) -> str:
        conn = self._db_conn()
        cur = conn.cursor()
        value = cur.execute(
            "SELECT MAX(day_ref) FROM measurements_curated WHERE row_kind=? AND COALESCE(is_official,1)=1",
            (row_kind,),
        ).fetchone()[0] or ""
        conn.close()
        return value

    def list_fluid_measurements(self, row_kind: str, date_from: str, date_to: str) -> list[dict]:
        conn = self._db_conn()
        cur = conn.cursor()
        rows = [
            dict(row)
            for row in cur.execute(
                "SELECT day_ref, hour_ref, tag, instrument, metric_name, metric_value, source_file FROM measurements_curated WHERE row_kind=? AND COALESCE(is_official,1)=1 AND day_ref BETWEEN ? AND ? ORDER BY day_ref DESC, COALESCE(hour_ref,-1), tag, metric_name",
                (row_kind, date_from, date_to),
            ).fetchall()
        ]
        conn.close()
        return rows

    def delete_sep_fluid_row(self, row_kind: str, day_ref: str, hour_ref, tag: str) -> None:
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM measurements_curated WHERE row_kind=? AND bank='SEP' AND day_ref=? AND ((hour_ref IS NULL AND ? IS NULL) OR hour_ref=?) AND tag=? AND COALESCE(is_official,1)=1",
            (row_kind, day_ref, hour_ref, hour_ref, tag),
        )
        conn.commit()
        conn.close()

    def update_measurement_value(self, rec_id: int, value) -> float:
        numeric_value = float(value)
        conn = self._db_conn()
        conn.execute("UPDATE measurements_curated SET metric_value=? WHERE id=?", (numeric_value, rec_id))
        conn.commit()
        conn.close()
        return numeric_value

    def delete_measurement(self, rec_id: int) -> None:
        conn = self._db_conn()
        conn.execute("DELETE FROM measurements_curated WHERE id=?", (rec_id,))
        conn.commit()
        conn.close()

    def insert_measurement(self, body: dict) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        metric_name = body.get("metric_name", "")
        unit = ""
        if "(" in metric_name and ")" in metric_name:
            unit = metric_name.split("(", 1)[1].split(")", 1)[0]
        conn = self._db_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO measurements_curated(
                run_id, source_file, excel_file, sheet_name, row_kind, day_ref, hour_ref,
                bank, loop, tipo, tag, instrument, metric_name, metric_value, metric_unit, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                None,
                body.get("source_file", "manual"),
                "",
                "",
                body["row_kind"],
                body["day_ref"],
                body.get("hour_ref"),
                body["bank"],
                body.get("loop", ""),
                body.get("tipo", ""),
                body.get("tag", ""),
                body.get("instrument", ""),
                metric_name,
                float(body["metric_value"]),
                unit,
                now,
            ),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return new_id
