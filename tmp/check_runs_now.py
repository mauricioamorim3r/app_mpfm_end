import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- last 5 processing_runs ---")
for r in cur.execute("SELECT id, status, started_at, finished_at, source_type, source_ref, files_count FROM processing_runs ORDER BY id DESC LIMIT 5"):
    print(dict(r))
