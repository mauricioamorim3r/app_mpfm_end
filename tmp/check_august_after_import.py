import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
print('agosto=', conn.execute("SELECT row_kind, count(*) FROM measurements_curated WHERE substr(day_ref,1,7)='2026-08' GROUP BY row_kind").fetchall())
print('dias=', conn.execute("SELECT min(day_ref), max(day_ref), count(distinct day_ref) FROM measurements_curated WHERE substr(day_ref,1,7)='2026-08'").fetchone())
print('runs=', conn.execute("SELECT id,status,source_type FROM processing_runs ORDER BY id DESC LIMIT 2").fetchall())
conn.close()
