import os, re
from pathlib import Path

BASE = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM")

BANKS = [
    ("B03", "3.1.1_13-FT-0367 Riser P5 - Topside B03"),
    ("B08", "3.1.2_13-FT-0167 Riser P2 - Topside B08"),
    ("B13", "3.1.3_13-FT-0317 Riser P4 - Topside B13"),
    ("B05", "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05"),
    ("B10", "3.1.5_18-FT-0506 PE 2 - Subsea B10"),
    ("B15", "3.1.6_18-FT-1106 PW_104DA - Subsea B15"),
]

TARGET_DATES = ("20260812", "20260813", "20260814")

print("=== ARQUIVOS 12/13/14-ago nas pastas ===\n")
total = 0
for bank, folder in BANKS:
    print(f"[{bank}]")
    for tipo in ("Daily", "Hourly"):
        pasta = BASE / folder / "2026" / "08. Agosto" / tipo
        if not pasta.exists():
            print(f"  {tipo}: pasta NAO encontrada")
            continue
        found = sorted(
            f.name for f in pasta.iterdir()
            if f.suffix.lower() == ".pdf" and any(d in f.name for d in TARGET_DATES)
        )
        if found:
            for fn in found:
                print(f"  {tipo}: {fn}")
            total += len(found)
        else:
            all_pdfs = sorted(f.name for f in pasta.iterdir() if f.suffix.lower() == ".pdf")
            ultimo = all_pdfs[-1] if all_pdfs else "vazia"
            print(f"  {tipo}: SEM arquivos 12/13/14-ago  (ultimo disponivel: {ultimo})")
    print()

print(f"Total arquivos 12/13/14-ago encontrados: {total}")
