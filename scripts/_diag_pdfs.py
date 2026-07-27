#!/usr/bin/env python3
"""Diagnóstico: lista todos os PDFs nas subpastas de medição com seus nomes reais."""
import pathlib

BASE = pathlib.Path(
    r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\DPB FPSO Bacalhau - Metering - 3.2 Daily Reports"
)

SKIP = ("ALARMES", "ZIP", "RANP44")

for subdir in sorted(BASE.iterdir()):
    if not subdir.is_dir():
        continue
    if any(s in subdir.name.upper() for s in SKIP):
        continue
    pdfs = sorted(subdir.rglob("*.pdf"))
    print(f"\n=== {subdir.name} ({len(pdfs)} PDFs) ===")
    for p in pdfs[:10]:
        print(f"  {p.name}")
    if len(pdfs) > 10:
        print(f"  ... +{len(pdfs)-10} mais")
