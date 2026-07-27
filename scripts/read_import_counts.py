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
    print("runs=" + str(cur.execute("SELECT COUNT(*) FROM processing_runs").fetchone()[0]))
    print("source_files_raw=" + str(cur.execute("SELECT COUNT(*) FROM source_files_raw").fetchone()[0]))
    print("measurements_curated=" + str(cur.execute("SELECT COUNT(*) FROM measurements_curated").fetchone()[0]))
    print("validation_issues=" + str(cur.execute("SELECT COUNT(*) FROM validation_issues").fetchone()[0]))
    print("sep_source_files=" + str(cur.execute("SELECT COUNT(*) FROM sep_source_files").fetchone()[0]))
    print(
        "sep_measurements_curated="
        + str(cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE source_record_id IS NOT NULL").fetchone()[0])
    )
    print("last_day_ref=" + str(cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())