from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronously rebuild a monthly workbook from the database.")
    parser.add_argument("month", help="Month in YYYY-MM format")
    args = parser.parse_args()

    target_month = str(args.month or "").strip()
    if len(target_month) != 7 or target_month[4] != "-":
        raise SystemExit("Use YYYY-MM")

    yr, mo = target_month.split("-", 1)
    workbook_path = server.OUTPUT_DIR / server.excel_name(yr, mo)
    print(f"rebuilding {workbook_path}")
    server.build_monthly_base_unica(workbook_path, yr, mo)
    server._cleanup_workbook(workbook_path)
    print(f"done {workbook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())