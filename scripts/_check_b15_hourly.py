import sqlite3

db = r'C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 07 Applications\7.1 MPFM_PDF_TXT\data\mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== processing_runs - ultimas 10 ===")
runs = conn.execute("""
    SELECT id, started_at, finished_at, source_ref, files_count, status, notes_json
    FROM processing_runs
    ORDER BY started_at DESC
    LIMIT 10
""").fetchall()
for r in runs:
    notes = str(r['notes_json'] or '')[:150]
    src = str(r['source_ref'] or '')[-60:]
    print(f"  run={r['id']} status={r['status']} files={r['files_count']} started={r['started_at']}")
    print(f"    src: ...{src}")
    print(f"    notes: {notes}")

print()
print("=== measurements_curated - B15 todos os dias de abril (por origem) ===")
rows = conn.execute("""
    SELECT DATE(day_ref) as dia, excel_file, source_file, row_kind, COUNT(*) as qtd
    FROM measurements_curated
    WHERE bank = 'B15' AND day_ref >= '2026-04-01' AND day_ref <= '2026-04-21'
    GROUP BY DATE(day_ref), excel_file, row_kind
    ORDER BY dia
""").fetchall()
for r in rows:
    print(f"  dia={r['dia']}  qtd={r['qtd']}  rk={r['row_kind']}")
    print(f"    excel={str(r['excel_file'] or '')[:60]}")
    print(f"    source={str(r['source_file'] or '')[:60]}")
if not rows:
    print("  Sem dados.")

print()
print("=== source_files_raw - B15 HOURLY dias 15-20 ===")
rows3 = conn.execute("""
    SELECT id, run_id, filename, detected_type, unit_code, created_at
    FROM source_files_raw
    WHERE filename LIKE '%B15%Hourly%'
      AND (filename LIKE '%20260415%' OR filename LIKE '%20260416%'
           OR filename LIKE '%20260417%' OR filename LIKE '%20260418%'
           OR filename LIKE '%20260419%' OR filename LIKE '%20260420%')
    ORDER BY filename
""").fetchall()
if rows3:
    for r in rows3:
        print(f"  {r['filename'][:58]}  run={r['run_id']}  unit={r['unit_code']}  at={r['created_at']}")
else:
    print("  Nenhum arquivo B15 Hourly dias 15-20 em source_files_raw.")

print()
print("=== source_files_raw - B15 HOURLY todos de abril (count) ===")
cnt = conn.execute("""
    SELECT substr(filename,instr(filename,'202604')+6,2) as day_num, COUNT(*) as n
    FROM source_files_raw
    WHERE filename LIKE '%B15%Hourly%202604%'
    GROUP BY day_num ORDER BY day_num
""").fetchall()
for r in cnt:
    print(f"  dia 2026-04-{r['day_num']}: {r['n']} arquivos registrados")

conn.close()
