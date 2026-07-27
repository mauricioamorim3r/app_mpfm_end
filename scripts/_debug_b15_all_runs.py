"""Debug: Investigar origem dos dados para B15 dias 15-19 em todos os runs."""
import sqlite3

db = r'data/mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== files_imported para B15 hourly dias 15-20 (TODOS os runs) ===")
rows = conn.execute("""
    SELECT run_id, filename, file_type, content_date, processed_ok
    FROM files_imported
    WHERE file_type='hourly' AND content_date >= '2026-04-15' AND content_date <= '2026-04-20'
    AND filename LIKE '%B15%'
    ORDER BY run_id, content_date
""").fetchall()
for r in rows:
    print(f"  run={r['run_id']:3d}  date={r['content_date']}  ok={r['processed_ok']}  file={r['filename'][:60]}")

print(f"\nTotal: {len(rows)} registros")

print("\n=== measurements_curated para B15 dias 15-20 por run e row_kind ===")
rows2 = conn.execute("""
    SELECT run_id, row_kind, day_ref, COUNT(*) as cnt
    FROM measurements_curated
    WHERE bank='B15' AND day_ref >= '2026-04-15' AND day_ref <= '2026-04-20'
    GROUP BY run_id, row_kind, day_ref
    ORDER BY run_id, day_ref, row_kind
""").fetchall()
for r in rows2:
    print(f"  run={r['run_id']:3d}  day={r['day_ref']}  kind={r['row_kind']:7s}  cnt={r['cnt']}")

print("\n=== processing_runs para runs relacionados ===")
relevant_runs = {r['run_id'] for r in rows}
if rows2:
    relevant_runs.update({r['run_id'] for r in rows2})
if relevant_runs:
    qs = ','.join('?' * len(relevant_runs))
    runs = conn.execute(f"""
        SELECT id, started_at, status
        FROM processing_runs
        WHERE id IN ({qs})
        ORDER BY id
    """, list(relevant_runs)).fetchall()
    for r in runs:
        print(f"  run={r['id']:3d}  started={r['started_at']}  status={r['status']}")

conn.close()
print("\nDONE")
