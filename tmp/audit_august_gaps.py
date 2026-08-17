from pathlib import Path
import re, sqlite3

ROOT = Path(r"C:\Users\MAUAM\OneDrive - Equinor - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM")
# Correct root used by the workspace
ROOT = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM")
BANKS = {
    "B03": "3.1.1_13-FT-0367 Riser P5 - Topside B03",
    "B08": "3.1.2_13-FT-0167 Riser P2 - Topside B08",
    "B13": "3.1.3_13-FT-0317 Riser P4 - Topside B13",
    "B05": "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05",
    "B10": "3.1.5_18-FT-0506 PE 2 - Subsea B10",
    "B15": "3.1.6_18-FT-1106 PW_104DA - Subsea B15",
}
expected = {f"2026-08-{d:02d}" for d in range(1,14)}

source = {}
for bank, folder in BANKS.items():
    base = ROOT / folder / "2026" / "08. Agosto"
    daily = set()
    hourly = set()
    for f in (base / "Daily").glob("*.pdf"):
        m = re.search(r"Daily-(202608\d{2})-", f.name)
        if m:
            from datetime import datetime, timedelta
            generated = datetime.strptime(m.group(1), "%Y%m%d").date()
            daily.add((generated - timedelta(days=1)).isoformat())
    for f in (base / "Hourly").glob("*.pdf"):
        m = re.search(r"Hourly-(202608\d{2})-(\d{2})", f.name)
        if m:
            hourly.add(f"2026-08-{m.group(1)[-2:]}")
    source[bank] = (daily, hourly)

conn = sqlite3.connect("data/mpfm_local.db")
c = conn.cursor()
print("=== COBERTURA POR BANCO/DIA ===")
for bank in BANKS:
    db_daily = {r[0] for r in c.execute("SELECT DISTINCT day_ref FROM measurements_curated WHERE day_ref LIKE '2026-08%' AND bank=? AND row_kind='daily'", (bank,))}
    db_hourly = {r[0] for r in c.execute("SELECT DISTINCT day_ref FROM measurements_curated WHERE day_ref LIKE '2026-08%' AND bank=? AND row_kind='hourly'", (bank,))}
    sd, sh = source[bank]
    print(f"{bank}: fonte daily={len(sd)} hourly_days={len(sh)} | banco daily={len(db_daily)} hourly_days={len(db_hourly)}")
    print("  daily faltante:", sorted(sd-db_daily))
    print("  hourly faltante:", sorted(sh-db_hourly))

print("\n=== INSTRUMENTOS NO BANCO POR DIA ===")
for bank in BANKS:
    rows = c.execute("SELECT day_ref, group_concat(DISTINCT instrument) FROM measurements_curated WHERE day_ref LIKE '2026-08%' AND bank=? AND row_kind='daily' GROUP BY day_ref ORDER BY day_ref", (bank,)).fetchall()
    print(bank, rows)

print("\n=== ARQUIVOS IMPORTADOS POR DATA/TYPE ===")
for r in c.execute("SELECT content_date,file_type,COUNT(*),SUM(processed_ok) FROM files_imported WHERE content_date LIKE '2026-08%' GROUP BY content_date,file_type ORDER BY content_date,file_type"):
    print(r)
conn.close()
