import sqlite3
conn = sqlite3.connect('data/mpfm_local.db', timeout=2)
print(conn.execute('SELECT id,status,started_at,finished_at,source_type FROM processing_runs ORDER BY id DESC LIMIT 3').fetchall())
conn.close()
