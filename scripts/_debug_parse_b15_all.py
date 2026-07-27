"""Debug: Parse varios PDFs de dias 15 e 19 para checar horas e date_from."""
import sys, os
sys.path.insert(0, '.')
import glob
import mpfm_engine as engine

base = r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\DPB FPSO Bacalhau - Metering - 3.2 Daily Reports\3.2.6_18-FT-1106  PW_104DA - Subsea B15\2026\Abr-26\HOURLY"

pdfs = sorted(glob.glob(os.path.join(base, 'B15_MPFM_Hourly-202604*.pdf')))
print(f"Total PDFs no diretório: {len(pdfs)}")

# Parse todos e listar date_from + hour
print("\nFilename | date_from | hour | tags_count | df_empty")
print("-" * 70)

day_15_recs = []
day_19_recs = []

for pdf in pdfs:
    fname = os.path.basename(pdf)
    try:
        rec = engine.parse_pdf(pdf, 'hourly')
        date_from = rec.get('date_from', '?')
        hour = rec.get('hour')
        n_tags = len(rec.get('tags', {}))
        print(f"{fname[:50]}  | {date_from} | {str(hour):>4} | {n_tags:2d}")
        if date_from == '2026-04-15':
            day_15_recs.append(rec)
        if date_from == '2026-04-19':
            day_19_recs.append(rec)
    except Exception as e:
        print(f"{fname[:50]}  | ERROR: {e}")

print(f"\n=== Records com date_from='2026-04-15': {len(day_15_recs)} ===")
print(f"=== Records com date_from='2026-04-19': {len(day_19_recs)} ===")

# Test build_hourly_df_with_sep for day 15
if day_15_recs:
    print(f"\n--- build_hourly_df_with_sep para day 15 ({len(day_15_recs)} recs) ---")
    df = engine.build_hourly_df_with_sep(day_15_recs, 'B15', {})
    print(f"  DF empty: {df.empty}  shape: {df.shape}")
    if not df.empty:
        print(f"  Primeiras linhas:\n{df.head(2).to_string()}")

if day_19_recs:
    print(f"\n--- build_hourly_df_with_sep para day 19 ({len(day_19_recs)} recs) ---")
    df = engine.build_hourly_df_with_sep(day_19_recs, 'B15', {})
    print(f"  DF empty: {df.empty}  shape: {df.shape}")
    if not df.empty:
        print(f"  Primeiras linhas:\n{df.head(2).to_string()}")

print("\nDONE")
