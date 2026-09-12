import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()
for rk in ('sep_oleo_detail', 'sep_gas_detail', 'sep_agua_detail'):
    n_null = cur.execute(f"SELECT COUNT(*) FROM measurements_curated WHERE row_kind='{rk}' AND hour_ref IS NULL").fetchone()[0]
    n_not = cur.execute(f"SELECT COUNT(*) FROM measurements_curated WHERE row_kind='{rk}' AND hour_ref IS NOT NULL").fetchone()[0]
    print(rk, 'null=', n_null, 'not_null=', n_not)
