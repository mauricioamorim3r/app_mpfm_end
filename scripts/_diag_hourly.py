#!/usr/bin/env python3
"""Verifica se há arquivos Hourly nas subpastas e em pastas adjacentes."""
import pathlib

BASE = pathlib.Path(
    r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\DPB FPSO Bacalhau - Metering - 3.2 Daily Reports"
)
# Pasta pai (Desktop)
DESKTOP = BASE.parent

print("=== Buscando 'Hourly' em subpastas de Daily Reports ===")
for subdir in sorted(BASE.iterdir()):
    if not subdir.is_dir():
        continue
    hourly = [p for p in subdir.rglob("*.pdf") if "hourly" in p.name.lower()]
    if hourly:
        print(f"\n  {subdir.name}: {len(hourly)} Hourly PDFs")
        for h in hourly[:3]:
            print(f"    {h.name}")
    else:
        # Conta total para verificar se tem misturado
        all_pdfs = list(subdir.rglob("*.pdf"))
        daily_pdfs = [p for p in all_pdfs if "daily" in p.name.lower()]
        print(f"  {subdir.name}: {len(all_pdfs)} total, {len(daily_pdfs)} Daily, 0 Hourly")

print("\n=== Pastas adjacentes no Desktop que possam ter Hourly ===")
for item in sorted(DESKTOP.iterdir()):
    if not item.is_dir():
        continue
    if "hourly" in item.name.lower() or "metering" in item.name.lower():
        print(f"  {item.name}")
        pdfs = list(item.rglob("*.pdf"))[:3]
        for p in pdfs:
            print(f"    {p.name}")
