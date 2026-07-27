from __future__ import annotations

import sqlite3
from pathlib import Path
import sys

ROOT = Path(".").resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server

db_path = ROOT / "data" / "mpfm_local.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

months = [
    r[0]
    for r in cur.execute(
        """
        SELECT DISTINCT substr(day_ref,1,7) AS month_key
        FROM measurements_curated
        WHERE day_ref LIKE '2026-%'
          AND row_kind IN ('hourly','daily','recon','sep')
        ORDER BY month_key
        """
    ).fetchall()
]
conn.close()

print("DB:", db_path)
print("Months:", ", ".join(months) if months else "none")

for month_key in months:
    yr, mo = month_key.split("-")
    workbook_path = server.OUTPUT_DIR / server.excel_name(yr, mo)
    print(f"[MONTHLY] rebuilding {workbook_path.name}")
    server.build_monthly_base_unica(workbook_path, yr, mo)
    server._cleanup_workbook(workbook_path)

print("DONE - monthly only, no annual file generated")
