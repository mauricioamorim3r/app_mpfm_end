import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

run = dict(cur.execute("SELECT * FROM processing_runs WHERE id=817").fetchone())
print("run:", run)

started = datetime.fromisoformat(run["started_at"])
print("elapsed seconds:", (datetime.now() - started).total_seconds())

print("\nfiles_imported for run 817:")
rows = cur.execute("SELECT filename, processed_ok, message FROM files_imported WHERE run_id=817 ORDER BY id").fetchall()
print(f"count so far: {len(rows)}")
for r in rows:
    print(dict(r))
