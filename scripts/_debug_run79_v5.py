"""Debug: Inspeciona rows recon armazenadas para run 79."""
import sqlite3
import json

db = r'data/mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== Amostra rows recon para run 79 ===")
rows = conn.execute(
    "SELECT run_id, bank, day_ref, hour_ref, row_kind, tag, sheet_name FROM measurements_curated WHERE run_id=79 LIMIT 10"
).fetchall()
for r in rows:
    print(dict(r))

print()
print("=== Distribuição de day_ref para run 79 ===")
rows = conn.execute(
    "SELECT day_ref, row_kind, COUNT(*) as cnt FROM measurements_curated WHERE run_id=79 GROUP BY day_ref, row_kind ORDER BY day_ref"
).fetchall()
for r in rows:
    print(dict(r))

print()
print("=== files_imported para run 79 - distribuição por file_type ===")
rows = conn.execute(
    "SELECT file_type, COUNT(*) as cnt FROM files_imported WHERE run_id=79 GROUP BY file_type"
).fetchall()
for r in rows:
    print(dict(r))

print()
print("=== files_imported para run 79 - daily files ===")
rows = conn.execute(
    "SELECT filename, content_date, file_type FROM files_imported WHERE run_id=79 AND file_type='daily'"
).fetchall()
for r in rows:
    print(dict(r))
if not rows:
    print("(nenhum)")

print()
print("=== COLUNAS measurements_curated ===")
cols = [r[1] for r in conn.execute("PRAGMA table_info(measurements_curated)").fetchall()]
print(cols)

conn.close()
print("\nDONE")
