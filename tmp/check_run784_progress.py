import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()
print('rows for run_id=784:', cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE run_id=784").fetchone()[0])
print('max created_at run_id=784:', cur.execute("SELECT MAX(created_at) FROM measurements_curated WHERE run_id=784").fetchone()[0])
print('rows for run_id=782 (old attempt):', cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE run_id=782").fetchone()[0])
