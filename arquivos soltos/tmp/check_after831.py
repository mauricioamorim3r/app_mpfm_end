import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
c = conn.cursor()

# Corrige run 831 (marcado erroneamente como error - na verdade concluiu ok)
row = c.execute("SELECT id, status, finished_at FROM processing_runs WHERE id=831").fetchone()
print(f"run 831 antes: status={row[1]}, finished_at={row[2]}")

if row[1] == 'error':
    conn.execute(
        "UPDATE processing_runs SET status='ok', "
        "notes_json='{\"log_fix\":\"Status corrigido: run concluiu com sucesso apos ser marcado erroneamente como error\"}' "
        "WHERE id=831"
    )
    conn.commit()
    print("  -> corrigido para 'ok'")

print()
print("=== ULTIMO DIA POR BANCO (daily) apos run 831 ===")
rows = c.execute(
    "SELECT bank, tag, MAX(day_ref) FROM measurements_curated "
    "WHERE row_kind='daily' GROUP BY bank, tag ORDER BY bank, tag"
).fetchall()
for r in rows:
    flag = " ⚠️ desatualizado" if r[2] < "2026-08-06" else ""
    print(f"  {r[1]:15} ({r[0]}) => {r[2]}{flag}")

print()
print("=== ULTIMOS 5 RUNS ===")
rows2 = c.execute(
    "SELECT id, status, started_at, finished_at, files_count, source_ref "
    "FROM processing_runs ORDER BY id DESC LIMIT 5"
).fetchall()
for r in rows2:
    src = (r[5] or '')[-50:]
    print(f"  run {r[0]:4} | {r[1]:8} | {(r[2] or '')[:16]} -> {(r[3] or '')[:16]} | {r[4]} arqs | ...{src}")

conn.close()
