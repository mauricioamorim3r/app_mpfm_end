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

print("=== ULTIMO ARQUIVO DISPONÍVEL POR BANCO (agosto) ===\n")
for bank, folder in BANKS:
    print(f"  [{bank}]")
    for tipo in ["Daily", "Hourly"]:
        pasta = BASE / folder / "2026" / "08. Agosto" / tipo
        if not pasta.exists():
            print(f"    {tipo}: pasta não encontrada")
            continue
        files = sorted([f.name for f in pasta.iterdir() if f.suffix.lower() == '.pdf'])
        if files:
            print(f"    {tipo}: ultimo={files[-1]}  (total: {len(files)})")
        else:
            print(f"    {tipo}: pasta vazia")
    print()
