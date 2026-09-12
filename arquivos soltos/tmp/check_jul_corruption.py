import os
import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- PE_2 hourly coverage 2026-07-25 to 2026-08-02 ---")
rows = cur.execute(
    "SELECT day_ref, COUNT(DISTINCT hour_ref) hrs FROM measurements_curated "
    "WHERE row_kind='hourly' AND tag='PE_2' AND day_ref BETWEEN '2026-07-25' AND '2026-08-02' "
    "GROUP BY day_ref ORDER BY day_ref"
).fetchall()
for r in rows:
    print(dict(r))

print("\n--- PE_2 daily coverage late July ---")
rows = cur.execute(
    "SELECT day_ref, metric_name, metric_value FROM measurements_curated "
    "WHERE row_kind='daily' AND tag='PE_2' AND day_ref='2026-07-31'"
).fetchall()
print(f"count for 2026-07-31 daily: {len(rows)}")

print("\n--- files_imported entries mentioning JUL 31 hour 23 for B10 ---")
rows = cur.execute(
    "SELECT id, run_id, filename, processed_ok, message FROM files_imported "
    "WHERE filename LIKE 'B10_MPFM_Hourly-20260801%' ORDER BY id"
).fetchall()
for r in rows:
    print(dict(r))

path = os.path.join("data", "outputs", "MPFM_JUL_2026.xlsx")
print("\nMPFM_JUL_2026.xlsx size:", os.path.getsize(path), "bytes")
with open(path, "rb") as f:
    head = f.read(8)
print("first bytes:", head)
