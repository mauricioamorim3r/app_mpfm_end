import sqlite3

conn = sqlite3.connect('data/mpfm_local.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

pairs = [
    ('B05', 'PE_4'), ('B10', 'PE_2'), ('B15', 'PW-104DA'),
    ('B08', 'Riser_P2'), ('B13', 'Riser_P4'), ('B03', 'Riser_P5'),
]

print('=== Row counts per (bank, tag) in range, row_kind daily/hourly ===')
for bank, tag in pairs:
    row = cur.execute(
        """
        SELECT row_kind, COUNT(*), MIN(day_ref), MAX(day_ref)
        FROM measurements_curated
        WHERE bank=? AND tag=? AND day_ref BETWEEN '2026-02-01' AND '2026-07-31'
        GROUP BY row_kind
        """,
        (bank, tag),
    ).fetchall()
    print(bank, tag, '->', [tuple(r) for r in row])

print()
print('=== Distinct metric_name for row_kind=daily (all banks/tags in pairs) ===')
placeholders = ','.join(['(?,?)'] * len(pairs))
params = [v for p in pairs for v in p]
rows = cur.execute(
    f"""
    SELECT DISTINCT metric_name FROM measurements_curated
    WHERE row_kind='daily' AND day_ref BETWEEN '2026-02-01' AND '2026-07-31'
      AND (bank,tag) IN ({placeholders})
    ORDER BY metric_name
    """,
    params,
).fetchall()
for r in rows:
    print(r[0])

print()
print('=== Distinct metric_name for row_kind=hourly ===')
rows = cur.execute(
    f"""
    SELECT DISTINCT metric_name FROM measurements_curated
    WHERE row_kind='hourly' AND day_ref BETWEEN '2026-02-01' AND '2026-07-31'
      AND (bank,tag) IN ({placeholders})
    ORDER BY metric_name
    """,
    params,
).fetchall()
for r in rows:
    print(r[0])

print()
print('=== SEP related row_kinds, counts, distinct metric_name ===')
rows = cur.execute(
    """
    SELECT row_kind, COUNT(*), MIN(day_ref), MAX(day_ref)
    FROM measurements_curated
    WHERE bank='SEP' AND day_ref BETWEEN '2026-02-01' AND '2026-07-31'
    GROUP BY row_kind
    """
).fetchall()
for r in rows:
    print(tuple(r))

for rk in ('sep', 'sep_oleo_detail', 'sep_gas_detail', 'sep_agua_detail'):
    print(f'--- metric_name for row_kind={rk} ---')
    rows = cur.execute(
        """
        SELECT DISTINCT metric_name FROM measurements_curated
        WHERE bank='SEP' AND row_kind=? AND day_ref BETWEEN '2026-02-01' AND '2026-07-31'
        ORDER BY metric_name
        """,
        (rk,),
    ).fetchall()
    for r in rows:
        print(' ', r[0])

print()
print('=== distinct tag for bank=SEP ===')
rows = cur.execute("SELECT DISTINCT tag FROM measurements_curated WHERE bank='SEP'").fetchall()
for r in rows:
    print(r[0])

print()
print('=== sample sep row ===')
row = cur.execute("SELECT * FROM measurements_curated WHERE bank='SEP' LIMIT 3").fetchall()
for r in row:
    print(dict(r))
