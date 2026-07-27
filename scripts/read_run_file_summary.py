from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import db_conn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume arquivos processados em um run.")
    parser.add_argument("--run-id", type=int, default=0, help="ID do run. 0 = run mais recente.")
    return parser.parse_args()


def resolve_run_id(cur, run_id: int) -> int:
    if run_id:
        return run_id
    row = cur.execute("SELECT id FROM processing_runs ORDER BY id DESC LIMIT 1").fetchone()
    return int(row[0]) if row else 0


def main() -> int:
    args = parse_args()
    conn = db_conn()
    cur = conn.cursor()
    run_id = resolve_run_id(cur, args.run_id)
    if not run_id:
        print("ERRO|Nenhum run encontrado")
        conn.close()
        return 2

    row = cur.execute(
        "SELECT id, status, source_type, files_count, started_at, finished_at FROM processing_runs WHERE id=?",
        (run_id,),
    ).fetchone()
    print("RUN|" + "|".join("" if value is None else str(value) for value in row))

    for item in cur.execute(
        """
        SELECT file_type, processed_ok, COUNT(*)
        FROM files_imported
        WHERE run_id=?
        GROUP BY file_type, processed_ok
        ORDER BY file_type, processed_ok
        """,
        (run_id,),
    ).fetchall():
        print("FILE_TYPE|" + "|".join(str(value) for value in item))

    for item in cur.execute(
        """
        SELECT CASE WHEN COALESCE(message, '') = '' THEN '(empty)' ELSE message END AS message, COUNT(*)
        FROM files_imported
        WHERE run_id=?
        GROUP BY message
        ORDER BY COUNT(*) DESC, message
        LIMIT 15
        """,
        (run_id,),
    ).fetchall():
        print("MESSAGE|" + "|".join(str(value) for value in item))

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())