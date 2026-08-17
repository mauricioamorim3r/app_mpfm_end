from pathlib import Path
import re, sqlite3

ROOT = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM")
BANKS = {
    "B03": "3.1.1_13-FT-0367 Riser P5 - Topside B03",
    "B08": "3.1.2_13-FT-0167 Riser P2 - Topside B08",
    "B13": "3.1.3_13-FT-0317 Riser P4 - Topside B13",
    "B05": "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05",
    "B10": "3.1.5_18-FT-0506 PE 2 - Subsea B10",
    "B15": "3.1.6_18-FT-1106 PW_104DA - Subsea B15",
}

print("=== ARQUIVOS NA ORIGEM: AGOSTO/2026 ===")
for bank, folder in BANKS.items():
    base = ROOT / folder / "2026" / "08. Agosto"
    print(f"\n[{bank}] {base}")
    for kind in ("Daily", "Hourly"):
        files = sorted(base.joinpath(kind).glob("*.pdf")) if base.joinpath(kind).exists() else []
        dates = sorted({match.group(1) for f in files for match in re.finditer(r"(202608\d{2})", f.name)})
        print(f"  {kind}: {len(files)} arquivos | nomes: {dates[0] if dates else '-'} -> {dates[-1] if dates else '-'}")
        if files:
            print(f"    primeiro={files[0].name}; ultimo={files[-1].name}")

conn = sqlite3.connect("data/mpfm_local.db")
c = conn.cursor()
print("\n=== IMPORTADO NO SQLITE: AGOSTO/2026 ===")
print("files_imported por file_type:")
for r in c.execute("SELECT file_type, COUNT(*), MIN(content_date), MAX(content_date), SUM(processed_ok) FROM files_imported WHERE content_date LIKE '2026-08%' GROUP BY file_type ORDER BY file_type"):
    print(" ", r)
print("measurements_curated por row_kind:")
for r in c.execute("SELECT row_kind, COUNT(*), MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE day_ref LIKE '2026-08%' GROUP BY row_kind ORDER BY row_kind"):
    print(" ", r)
print("por banco e row_kind:")
for r in c.execute("SELECT bank, row_kind, COUNT(DISTINCT day_ref), COUNT(*) FROM measurements_curated WHERE day_ref LIKE '2026-08%' AND bank<>'SEP' GROUP BY bank,row_kind ORDER BY bank,row_kind"):
    print(" ", r)
print("ultimos runs:")
for r in c.execute("SELECT id,status,started_at,finished_at,files_count,source_ref FROM processing_runs ORDER BY id DESC LIMIT 8"):
    print(" ", r[:5], str(r[5])[-100:])
conn.close()
