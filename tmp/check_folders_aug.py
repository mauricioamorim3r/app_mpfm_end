import os, re
from pathlib import Path

BASE = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3. Registros de Operação SGM Multifasico\3.1 Registros Diarios MPFM")

BANKS = [
    ("B03", "3.1.1_13-FT-0367 Riser P5 - Topside B03"),
    ("B08", "3.1.2_13-FT-0167 Riser P2 - Topside B08"),
    ("B13", "3.1.3_13-FT-0317 Riser P4 - Topside B13"),
    ("B05", "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05"),
    ("B10", "3.1.5_18-FT-0506 PE 2 - Subsea B10"),
    ("B15", "3.1.6_18-FT-1106 PW_104DA - Subsea B15"),
]

# Filtra arquivos a partir de 20260807
DATE_MIN = "20260807"

print(f"=== ARQUIVOS DAILY/HOURLY disponíveis a partir de 07/ago ===")
print()

total_new = 0
for bank, folder in BANKS:
    daily_folder = BASE / folder / "2026" / "08. Agosto" / "Daily"
    hourly_folder = BASE / folder / "2026" / "08. Agosto" / "Hourly"
    
    daily_files = []
    hourly_files = []
    
    if daily_folder.exists():
        for f in sorted(daily_folder.iterdir()):
            m = re.search(r'(\d{8})', f.name)
            if m and m.group(1) >= DATE_MIN:
                daily_files.append(f.name)
    else:
        daily_files = ["[PASTA NAO ENCONTRADA]"]
    
    if hourly_folder.exists():
        for f in sorted(hourly_folder.iterdir()):
            m = re.search(r'(\d{8})', f.name)
            if m and m.group(1) >= DATE_MIN:
                hourly_files.append(f.name)
    else:
        hourly_files = ["[PASTA NAO ENCONTRADA]"]
    
    nd = len([x for x in daily_files if x != "[PASTA NAO ENCONTRADA]"])
    nh = len([x for x in hourly_files if x != "[PASTA NAO ENCONTRADA]"])
    total_new += nd + nh
    
    print(f"  [{bank}] {folder[:40]}...")
    if nd == 0:
        print(f"    Daily:  NENHUM arquivo novo >=07/ago")
    else:
        for fn in daily_files[:5]:
            print(f"    Daily:  {fn}")
        if nd > 5:
            print(f"    Daily:  ... +{nd-5} arquivo(s)")
    
    if nh == 0:
        print(f"    Hourly: NENHUM arquivo novo >=07/ago")
    else:
        print(f"    Hourly: {nh} arquivo(s) disponíveis (ex: {hourly_files[0] if hourly_files else '?'})")
    print()

print(f"TOTAL de arquivos novos >= 07/ago: {total_new}")
