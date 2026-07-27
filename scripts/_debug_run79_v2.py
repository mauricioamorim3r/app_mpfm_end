"""Debug: Verifica validation_issues e parsing_events_raw do run 79."""
import sqlite3
import json

db = r'data/mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== validation_issues for run 79 ===")
rows = conn.execute("SELECT * FROM validation_issues WHERE run_id=79 LIMIT 20").fetchall()
for r in rows:
    print(dict(r))

print()
print("=== parsing_events_raw for run 79 (non-ok) ===")
rows = conn.execute("SELECT * FROM parsing_events_raw WHERE run_id=79 AND result != 'ok' LIMIT 20").fetchall()
for r in rows:
    print(dict(r))

print()
print("=== measurements_curated for run 79 (check if any) ===")
cnt = conn.execute("SELECT COUNT(*) FROM measurements_curated WHERE run_id=79").fetchone()[0]
print(f"measurements_curated rows for run 79: {cnt}")
cnt_h = conn.execute("SELECT COUNT(*) FROM measurements_curated WHERE run_id=79 AND row_kind='hourly'").fetchone()[0]
print(f"hourly measurements for run 79: {cnt_h}")

print()
print("=== measurements_raw for run 79 ===")
cnt_raw = conn.execute("SELECT COUNT(*) FROM measurements_raw WHERE run_id=79").fetchone()[0]
print(f"measurements_raw rows for run 79: {cnt_raw}")

print()
print("=== source_files_raw for run 79 ===")
rows = conn.execute("SELECT id, filename, file_type, content_date, result FROM source_files_raw WHERE run_id=79 LIMIT 5").fetchall()
for r in rows:
    print(dict(r))

conn.close()
print("\n=== DONE ===")
