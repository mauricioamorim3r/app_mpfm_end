import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()
for rk in ('sep_oleo_detail', 'sep_gas_detail', 'sep_agua_detail'):
    print(f'--- {rk} metric_name where hour_ref IS NULL ---')
    for r in cur.execute(f"SELECT DISTINCT metric_name FROM measurements_curated WHERE row_kind='{rk}' AND hour_ref IS NULL"):
        print(' ', r[0])
