"""Debug: Verifica row_kind distribution para run 79."""
import sqlite3

db = r'data/mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("row_kind distribution for run 79:")
rows = conn.execute(
    "SELECT row_kind, COUNT(*) as cnt FROM measurements_curated WHERE run_id=79 GROUP BY row_kind"
).fetchall()
for r in rows:
    print(dict(r))

print()
print("Sample measurements_curated rows for run 79:")
sample = conn.execute(
    "SELECT run_id, bank, day_ref, hour_ref, row_kind, tag FROM measurements_curated WHERE run_id=79 LIMIT 5"
).fetchall()
for r in sample:
    print(dict(r))

print()
print("=== _postcheck_run_payload logic ===")
print("Check files_imported for run 79 that have row_kind='hourly':")
hourly_files = conn.execute(
    "SELECT filename, content_date, file_type FROM files_imported WHERE run_id=79 AND file_type='hourly' LIMIT 5"
).fetchall()
for r in hourly_files:
    print(dict(r))

print()
print("Check measurements_curated for B15, 2026-04-15, hourly:")
mc_rows = conn.execute(
    "SELECT run_id, bank, day_ref, hour_ref, row_kind, tag FROM measurements_curated WHERE bank='B15' AND day_ref='2026-04-15' AND row_kind='hourly' LIMIT 5"
).fetchall()
for r in mc_rows:
    print(dict(r))
if not mc_rows:
    print("(nenhum)")

conn.close()
print("\nDONE")
