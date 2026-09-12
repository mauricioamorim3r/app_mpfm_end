import sqlite3

conn = sqlite3.connect('data/mpfm_local.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
rows = cur.execute(
    'SELECT id, started_at, finished_at, status, files_count, source_ref FROM processing_runs ORDER BY id DESC LIMIT 4'
).fetchall()
for r in rows:
    print(dict(r))
run_id = rows[0]['id']
c2 = conn.execute(
    'SELECT COUNT(*), SUM(processed_ok) FROM files_imported WHERE run_id=?', (run_id,)
).fetchone()
print('files_imported count / processed_ok sum:', c2)
