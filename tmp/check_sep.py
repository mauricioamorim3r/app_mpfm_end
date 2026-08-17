import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
c = conn.cursor()

print('=== SEP: cobertura por row_kind ===')
rows = c.execute(
    "SELECT row_kind, MIN(day_ref), MAX(day_ref), COUNT(*) "
    "FROM measurements_curated WHERE row_kind LIKE 'sep%' "
    "GROUP BY row_kind ORDER BY row_kind"
).fetchall()
if rows:
    for r in rows:
        print(f'  {r[0]:25} | {r[1]} -> {r[2]} | {r[3]:,} linhas')
else:
    print('  Sem dados SEP no banco')

print()
print('=== SEP (diario) ultimo dia por banco ===')
rows2 = c.execute(
    "SELECT bank, tag, MIN(day_ref), MAX(day_ref), COUNT(*) "
    "FROM measurements_curated WHERE row_kind='sep' "
    "GROUP BY bank, tag ORDER BY bank, tag"
).fetchall()
for r in rows2:
    print(f'  {r[1]:15} ({r[0]}) | {r[2]} -> {r[3]} | {r[4]} dias')

print()
print('=== Runs em andamento ===')
rows3 = c.execute(
    "SELECT id, status, started_at FROM processing_runs "
    "WHERE status='running' ORDER BY id DESC"
).fetchall()
if rows3:
    for r in rows3:
        print(f'  run {r[0]} | {r[1]} | {r[2]}')
else:
    print('  Nenhum run rodando')

conn.close()
