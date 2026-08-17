import sqlite3

conn = sqlite3.connect('data/mpfm_local.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('--- distinct bank values (measurements_curated) ---')
for r in cur.execute("SELECT DISTINCT bank FROM measurements_curated ORDER BY bank"):
    print(r[0])

print('--- distinct row_kind ---')
for r in cur.execute("SELECT DISTINCT row_kind FROM measurements_curated"):
    print(r[0])

print('--- sample rows for one bank/day ---')
for r in cur.execute("SELECT * FROM measurements_curated LIMIT 5"):
    print(dict(r))

print('--- distinct metric_name count ---')
print(cur.execute("SELECT COUNT(DISTINCT metric_name) FROM measurements_curated").fetchone())

print('--- day_ref min/max ---')
print(cur.execute("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated").fetchone())
