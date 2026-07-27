from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import db_conn


def main() -> int:
    conn = db_conn()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, status, source_type, files_count, started_at, finished_at, COALESCE(source_ref, '')
        FROM processing_runs
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()
    for row in rows:
        print("|".join("" if value is None else str(value) for value in row))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())