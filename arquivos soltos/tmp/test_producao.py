import urllib.request, time
BASE = "http://localhost:8765"
url = BASE + "/api/export-producao-excel?date_from=2026-08-01&date_to=2026-08-07"
t0 = time.time()
r = urllib.request.urlopen(url, timeout=120)
data = r.read()
elapsed = round(time.time()-t0, 1)
ct = r.headers.get("Content-Type", "?")[:30]
print(f"Producao Excel: {len(data)//1024}KB em {elapsed}s [{ct}]")
