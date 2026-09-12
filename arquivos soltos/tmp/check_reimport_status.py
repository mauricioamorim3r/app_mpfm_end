import sqlite3
c=sqlite3.connect('data/mpfm_local.db')
print(c.execute('SELECT id,status,started_at,finished_at,files_count,source_ref FROM processing_runs ORDER BY id DESC LIMIT 3').fetchall())
c.close()
