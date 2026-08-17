import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()
print('--- metric_name where hour_ref IS NULL ---')
for r in cur.execute("SELECT DISTINCT metric_name FROM measurements_curated WHERE row_kind='sep' AND hour_ref IS NULL"):
    print(' ', r[0])
print('--- metric_name where hour_ref IS NOT NULL ---')
for r in cur.execute("SELECT DISTINCT metric_name FROM measurements_curated WHERE row_kind='sep' AND hour_ref IS NOT NULL"):
    print(' ', r[0])
print('counts:')
print('null hour rows:', cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE row_kind='sep' AND hour_ref IS NULL").fetchone()[0])
print('not null hour rows:', cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE row_kind='sep' AND hour_ref IS NOT NULL").fetchone()[0])
print('day_ref range null-hour:', cur.execute("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='sep' AND hour_ref IS NULL").fetchone())
print('day_ref range hourly:', cur.execute("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='sep' AND hour_ref IS NOT NULL").fetchone())
