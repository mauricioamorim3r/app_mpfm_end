import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
c = conn.cursor()

print("=== ULTIMOS 10 RUNS ===")
rows = c.execute(
    "SELECT id, status, source_ref, started_at, files_count "
    "FROM processing_runs ORDER BY id DESC LIMIT 10"
).fetchall()
for r in rows:
    src = (r[2] or '')[-45:]
    print(f"  run {r[0]:4} | {r[1]:8} | {(r[3] or '')[:16]} | {r[4]:3} arqs | ...{src}")

print()
print("=== ULTIMO DIA IMPORTADO POR BANCO (daily) ===")
rows = c.execute(
    "SELECT bank, tag, MAX(day_ref) as ultimo_dia "
    "FROM measurements_curated "
    "WHERE row_kind = 'daily' "
    "GROUP BY bank, tag "
    "ORDER BY bank"
).fetchall()
today = "2026-08-14"
for r in rows:
    diff = (len(today) > 0)  # placeholder
    print(f"  {(r[1] or ''):15} ({r[0]:4}) => ultimo daily: {r[2]}")

print()
print("=== ULTIMO DIA IMPORTADO POR BANCO (hourly) ===")
rows2 = c.execute(
    "SELECT bank, tag, MAX(day_ref) as ultimo_dia "
    "FROM measurements_curated "
    "WHERE row_kind = 'hourly' "
    "GROUP BY bank, tag "
    "ORDER BY bank"
).fetchall()
for r in rows2:
    print(f"  {(r[1] or ''):15} ({r[0]:4}) => ultimo hourly: {r[2]}")

print()
print("=== RUNS COM ERRO (ultimos 20) ===")
rows3 = c.execute(
    "SELECT id, status, started_at, source_ref "
    "FROM processing_runs WHERE status IN ('error','running') ORDER BY id DESC LIMIT 20"
).fetchall()
if rows3:
    for r in rows3:
        print(f"  run {r[0]} | {r[1]} | {(r[2] or '')[:16]} | {(r[3] or '')[-50:]}")
else:
    print("  Nenhum run com erro ou travado.")

conn.close()
