import json
import sqlite3
from pathlib import Path


def main() -> None:
    conn = sqlite3.connect("data/mpfm_local.db")
    conn.row_factory = sqlite3.Row

    print("RUN COUNTS")
    rows = conn.execute(
        """
        SELECT run_id, row_kind, COUNT(*) AS cnt
        FROM measurements_curated
        WHERE run_id IN (79, 97)
        GROUP BY run_id, row_kind
        ORDER BY run_id, row_kind
        """
    ).fetchall()
    for row in rows:
        print(dict(row))

    print("\nRUN 79 HOURLY GROUPED")
    rows = conn.execute(
        """
        SELECT run_id, row_kind, COALESCE(day_ref, '<NULL>') AS day_ref,
               COALESCE(CAST(hour_ref AS TEXT), '<NULL>') AS hour_ref,
               COALESCE(bank, '') AS bank,
               COUNT(*) AS cnt
        FROM measurements_curated
        WHERE run_id = 79 AND row_kind = 'hourly'
        GROUP BY run_id, row_kind, day_ref, hour_ref, bank
        ORDER BY day_ref, hour_ref, bank
        LIMIT 50
        """
    ).fetchall()
    for row in rows:
        print(dict(row))

    print("\nRUN 97 HOURLY GROUPED")
    rows = conn.execute(
        """
        SELECT run_id, row_kind, COALESCE(day_ref, '<NULL>') AS day_ref,
               COALESCE(CAST(hour_ref AS TEXT), '<NULL>') AS hour_ref,
               COALESCE(bank, '') AS bank,
               COUNT(*) AS cnt
        FROM measurements_curated
        WHERE run_id = 97 AND row_kind = 'hourly'
        GROUP BY run_id, row_kind, day_ref, hour_ref, bank
        ORDER BY day_ref, hour_ref, bank
        LIMIT 50
        """
    ).fetchall()
    for row in rows:
        print(dict(row))

    print("\nFILES_IMPORTED RUN 79 HOURLY")
    rows = conn.execute(
        """
        SELECT id, filename, content_date, report_start, report_end, identity_key,
               processed_ok, COALESCE(message, '') AS message
        FROM files_imported
        WHERE run_id = 79 AND file_type = 'hourly'
        ORDER BY id
        LIMIT 20
        """
    ).fetchall()
    for row in rows:
        print(dict(row))

    print("\nFILES_IMPORTED RUN 97 HOURLY")
    rows = conn.execute(
        """
        SELECT id, filename, content_date, report_start, report_end, identity_key,
               processed_ok, COALESCE(message, '') AS message
        FROM files_imported
        WHERE run_id = 97 AND file_type = 'hourly'
        ORDER BY id
        LIMIT 30
        """
    ).fetchall()
    for row in rows:
        print(dict(row))

    print("\nB15 APR 15-19 COUNTS")
    rows = conn.execute(
        """
        SELECT day_ref, row_kind, COUNT(*) AS cnt
        FROM measurements_curated
        WHERE bank = 'B15'
          AND day_ref BETWEEN '2026-04-15' AND '2026-04-19'
        GROUP BY day_ref, row_kind
        ORDER BY day_ref, row_kind
        """
    ).fetchall()
    for row in rows:
        print(dict(row))

    print("\nLATEST PROCESSING RUNS")
    rows = conn.execute(
        """
        SELECT id, source_type, status, started_at, finished_at
        FROM processing_runs
        ORDER BY id DESC
        LIMIT 5
        """
    ).fetchall()
    for row in rows:
        print(dict(row))

    state_path = Path("data/state_2026_04.json")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    print("\nSTATE B15 15-18")
    for key in ["B15_15_04", "B15_16_04", "B15_17_04", "B15_18_04"]:
        print(key, state.get("processed_hours_by_key", {}).get(key))

    conn.close()


if __name__ == "__main__":
    main()