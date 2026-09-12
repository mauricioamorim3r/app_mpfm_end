import urllib.request, shutil

url = "http://localhost:8765/api/export-sep-excel?date_from=2026-06-01&date_to=2026-08-13"
out = "data/outputs/SEP_JUN_AGO_2026.xlsx"

print(f"Gerando: {url}")
req = urllib.request.Request(url)
with urllib.request.urlopen(req, timeout=300) as resp:
    with open(out, "wb") as f:
        shutil.copyfileobj(resp, f)

import os
size = os.path.getsize(out) / 1024
print(f"Salvo: {out} ({size:.1f} KB)")
