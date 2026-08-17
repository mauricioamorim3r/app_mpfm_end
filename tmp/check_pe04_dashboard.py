import sqlite3, urllib.request
conn=sqlite3.connect('data/mpfm_local.db')
for bank in ('B05','B03'):
    print(bank)
    rows=conn.execute("SELECT day_ref,tag,instrument,COUNT(*) FROM measurements_curated WHERE day_ref BETWEEN '2026-08-01' AND '2026-08-13' AND bank=? AND row_kind='daily' GROUP BY day_ref,tag,instrument ORDER BY day_ref,tag",(bank,)).fetchall()
    for row in rows: print(row)
conn.close()
url='http://localhost:8765/api/ops/poco-riser-diario?date_from=2026-08-01&date_to=2026-08-13&source_kind=daily'
data=urllib.request.urlopen(url,timeout=20).read().decode()
print('API PE4 entries:', data.count('PE4_RISERP5'))
start=data.find('PE4_RISERP5')
print(data[max(0,start-150):start+700])
