import urllib.request, time, sys

BASE = "http://localhost:8765"
tests = [
    ("GET", "/api/export-sep-excel?date_from=2026-08-01&date_to=2026-08-07", "SEP Excel (7 dias)"),
    ("GET", "/api/export-sep-csv?date_from=2026-08-01&date_to=2026-08-07", "SEP CSV"),
    ("GET", "/api/export-producao-excel?date_from=2026-08-01&date_to=2026-08-07", "Producao Excel"),
    ("GET", "/api/export-excel?date_from=2026-08-01&date_to=2026-08-07", "MPFM Excel"),
    ("GET", "/api/ops/poco-riser-diario/export-excel?date_from=2026-08-01&date_to=2026-08-07", "Poco-Riser Excel"),
    ("GET", "/api/mpfm-adjustments/export?date_from=2026-08-01&date_to=2026-08-07", "Ajustes MPFM Excel"),
]

print("=== EXPORTS EXCEL / DOWNLOAD ===")
for method, path, label in tests:
    try:
        t0 = time.time()
        r = urllib.request.urlopen(BASE + path, timeout=90)
        data = r.read()
        elapsed = round(time.time() - t0, 1)
        ct = r.headers.get("Content-Type", "?")[:30]
        kb = len(data) // 1024
        status = "OK  "
        print(f"  {status} {label}: {kb} KB em {elapsed}s  [{ct}]")
    except Exception as e:
        print(f"  ERR  {label}: {e}")

print()
print("Todos os testes concluidos.")
