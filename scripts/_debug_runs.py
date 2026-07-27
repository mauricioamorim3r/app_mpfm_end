import sqlite3, json

db = r'C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 07 Applications\7.1 MPFM_PDF_TXT\data\mpfm_local.db'
conn = sqlite3.connect(db)

print('=== Todas as runs com B15 HOURLY ===')
runs = conn.execute("""
    SELECT id, started_at, files_count, status, source_ref, notes_json
    FROM processing_runs
    WHERE source_ref LIKE '%B15%HOURLY%' OR source_ref LIKE '%18-FT-1106%'
    ORDER BY started_at
""").fetchall()
for r in runs:
    notes = json.loads(r[5] or '{}')
    ck = notes.get('import_check', {})
    cf = ck.get('checked_files', '?')
    vf = ck.get('validated_files', '?')
    pf = len(ck.get('problem_files', []))
    print(f'  run={r[0]} files={r[2]} status={r[3]} started={r[1]}')
    print(f'    checked={cf} validated={vf} problems={pf}')
    ref = r[4] or ''
    print(f'    ref=...{ref[-60:]}')

print()
print('=== measurements_curated por dia (B15 Abr 2026) ===')
rows = conn.execute("""
    SELECT day_ref, row_kind, COUNT(*) as cnt, MIN(run_id), MAX(run_id)
    FROM measurements_curated
    WHERE bank='B15' AND day_ref LIKE '2026-04-%'
    GROUP BY day_ref, row_kind
    ORDER BY day_ref, row_kind
""").fetchall()
for row in rows:
    print(f"  {row[0]} {row[1]:7s} cnt={row[2]} runs={row[3]}..{row[4]}")

print()
print('=== files_imported para dias 15-20 (run=97) ===')
files = conn.execute("""
    SELECT filename, content_date, processed_ok, message
    FROM files_imported
    WHERE run_id=97 AND content_date >= '2026-04-15'
    ORDER BY content_date, filename
    LIMIT 20
""").fetchall()
for f in files:
    print(f"  {f[1]} {f[0]} ok={f[2]} msg={f[3]}")

conn.close()
