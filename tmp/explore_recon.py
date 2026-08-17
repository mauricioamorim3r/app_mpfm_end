import sqlite3

conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()

pairs = [
    ('B05', 'PE_4'), ('B10', 'PE_2'), ('B15', 'PW-104DA'),
    ('B08', 'Riser_P2'), ('B13', 'Riser_P4'), ('B03', 'Riser_P5'),
]
placeholders = ','.join(['(?,?)'] * len(pairs))
params = [v for p in pairs for v in p]

rows = cur.execute(
    f"""
    SELECT DISTINCT metric_name FROM measurements_curated
    WHERE row_kind='recon' AND day_ref BETWEEN '2026-02-01' AND '2026-07-31'
      AND (bank,tag) IN ({placeholders})
    ORDER BY metric_name
    """,
    params,
).fetchall()
print('recon metric_names:')
for r in rows:
    print(' ', r[0].encode('utf-8'))

print()
print(cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone())
