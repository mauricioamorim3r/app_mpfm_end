"""Debug: Testar parse de um PDF hourly B15 dias 15-18 vs dia 19."""
import sys, os
sys.path.insert(0, '.')

import sqlite3

db = r'data/mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== source_files_raw para runs 79 e 97 (primeiros 3 arquivos de cada dia/run) ===")
rows = conn.execute("""
    SELECT run_id, filename, original_path, detected_type, content_date
    FROM source_files_raw
    WHERE run_id IN (79, 85, 97) AND detected_type='hourly'
    AND (content_date='2026-04-15' OR content_date='2026-04-19')
    GROUP BY run_id, content_date
    ORDER BY run_id, content_date, filename
    LIMIT 6
""").fetchall()
for r in rows:
    print(f"  run={r['run_id']} date={r['content_date']} type={r['detected_type']}")
    print(f"    file: {r['filename']}")
    print(f"    path: {r['original_path']}")

conn.close()

# Now test parsing a B15 hourly PDF from each day
print("\n=== Testando parse de PDF hourly B15 ===")
import mpfm_engine as engine

# Find any B15 hourly PDF from April 15-18
import glob, pathlib

search_paths = [
    r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 07 Applications\7.1 MPFM_PDF_TXT\data\uploads",
    r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\DPB FPSO Bacalhau - Metering - 3.2 Daily Reports\3.2.6_18-FT-1106  PW_104DA - Subsea B15\2026\Abr-26\HOURLY",
]

found_15 = None
found_19 = None

for base in search_paths:
    if os.path.exists(base):
        print(f"  Scanning: {base}")
        for f in glob.glob(os.path.join(base, '**', 'B15_MPFM_Hourly-202604*.pdf'), recursive=True):
            fname = os.path.basename(f)
            if '20260415' in fname and found_15 is None:
                found_15 = f
            if '20260419' in fname and found_19 is None:
                found_19 = f

print(f"  PDF dia 15: {found_15}")
print(f"  PDF dia 19: {found_19}")

for label, pdf_path in [("DIA 15", found_15), ("DIA 19", found_19)]:
    if pdf_path and os.path.exists(pdf_path):
        print(f"\n--- Parsing {label}: {os.path.basename(pdf_path)} ---")
        try:
            rec = engine.parse_pdf(pdf_path, 'hourly')
            tags = rec.get('tags', {})
            print(f"  Tags count: {len(tags)}")
            print(f"  Tags: {list(tags.keys())[:5]}")
            print(f"  Hour: {rec.get('hour')}")
            print(f"  date_from: {rec.get('date_from')}")
            if tags:
                first_tag = list(tags.values())[0]
                print(f"  First tag metrics: {first_tag.get('metrics', {})}")
            
            # Try build_hourly_df_with_sep
            df = engine.build_hourly_df_with_sep([rec], 'B15', {})
            print(f"  DF empty: {df.empty}  shape: {df.shape}")
        except Exception as e:
            import traceback
            print(f"  ERRO: {e}")
            traceback.print_exc()
    else:
        print(f"\n--- {label}: arquivo não encontrado ({pdf_path}) ---")

print("\nDONE")
