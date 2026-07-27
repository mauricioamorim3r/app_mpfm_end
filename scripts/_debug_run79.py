import sqlite3, json

db = r'C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 07 Applications\7.1 MPFM_PDF_TXT\data\mpfm_local.db'
conn = sqlite3.connect(db)

print('=== Run 79 notas completas ===')
row = conn.execute("SELECT notes_json FROM processing_runs WHERE id=79").fetchone()
if row:
    notes = json.loads(row[0] or '{}')
    print(json.dumps(notes, indent=2, ensure_ascii=False))

print()
print('=== Files de run 79 com erro (primeiras 10) ===')
files = conn.execute("""
    SELECT filename, content_date, processed_ok, message
    FROM files_imported
    WHERE run_id=79
    ORDER BY content_date, filename
    LIMIT 10
""").fetchall()
for f in files:
    print(f"  {f[1]} {f[0][:40]} ok={f[2]} msg={f[3][:60] if f[3] else 'None'}")

print()
print('=== Issues de run 79 ===')
issues = conn.execute("""
    SELECT issue_type, severity, identifier, production_date, message
    FROM processing_issues
    WHERE run_id=79
    ORDER BY id
    LIMIT 20
""").fetchall()
for i in issues:
    print(f"  [{i[1]}] {i[0]} | {i[2]} | {i[3]} | {i[4][:80] if i[4] else 'None'}")

print()
print('=== Contagem de hourly por run nos dias 15-18 ===')
rows = conn.execute("""
    SELECT run_id, day_ref, COUNT(*) as cnt
    FROM measurements_curated
    WHERE bank='B15' AND row_kind='hourly' AND day_ref BETWEEN '2026-04-15' AND '2026-04-18'
    GROUP BY run_id, day_ref
    ORDER BY day_ref, run_id
""").fetchall()
for r in rows:
    print(f"  run={r[0]} day={r[1]} cnt={r[2]}")
if not rows:
    print("  (NENHUM REGISTRO)")

conn.close()
