import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()
rows = cur.execute("SELECT DISTINCT tag FROM measurements_curated WHERE row_kind='sep'").fetchall()
print('tags for row_kind=sep:', [r[0] for r in rows])
rows = cur.execute("SELECT DISTINCT hour_ref FROM measurements_curated WHERE row_kind='sep' ORDER BY hour_ref").fetchall()
print('hour_ref for row_kind=sep:', [r[0] for r in rows])
row = cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE row_kind='sep' AND tag='SEP'").fetchone()
print('count tag=SEP:', row[0])
