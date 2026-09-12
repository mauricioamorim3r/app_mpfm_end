import urllib.request, os, time

t0 = time.time()
url = "http://localhost:8765/api/export-sep-excel?date_from=2026-06-01&date_to=2026-08-13"
out = "data/outputs/SEP_JUN_AGO_v2.xlsx"
req = urllib.request.Request(url)
with urllib.request.urlopen(req, timeout=300) as resp:
    data = resp.read()
with open(out, "wb") as f:
    f.write(data)
elapsed = time.time() - t0
print(f"OK: {os.path.getsize(out)/1024:.1f} KB em {elapsed:.1f}s")
