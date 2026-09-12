import json, time, urllib.request
from pathlib import Path

BASE = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM")
FOLDERS = [
    ("B03", "3.1.1_13-FT-0367 Riser P5 - Topside B03"),
    ("B08", "3.1.2_13-FT-0167 Riser P2 - Topside B08"),
    ("B13", "3.1.3_13-FT-0317 Riser P4 - Topside B13"),
    ("B05", "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05"),
    ("B10", "3.1.5_18-FT-0506 PE 2 - Subsea B10"),
    ("B15", "3.1.6_18-FT-1106 PW_104DA - Subsea B15"),
]

for bank, folder in FOLDERS:
    path = BASE / folder / "2026" / "08. Agosto"
    print(f"[{bank}] {path}", flush=True)
    if not path.exists():
        print("  pasta inexistente", flush=True)
        continue
    body = json.dumps({"folder": str(path)}).encode()
    req = urllib.request.Request(
        "http://localhost:8765/api/process-folder",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        started = time.time()
        with urllib.request.urlopen(req, timeout=900) as response:
            result = json.loads(response.read())
        print(f"  resultado={result.get('status')} run={result.get('run_id')} tempo={time.time()-started:.0f}s", flush=True)
    except Exception as exc:
        print(f"  ERRO: {exc}", flush=True)

print("REIMPORTACAO CONCLUIDA", flush=True)
