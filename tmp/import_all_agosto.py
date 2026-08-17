"""Importa as pastas de agosto de cada banco sequencialmente via API."""
import urllib.request, json, time

BASE_URL = "http://localhost:8765"
BASE_PASTA = (
    r"C:\Users\MAUAM\OneDrive - Equinor"
    r"\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM"
    r"\3.1 Registros Diarios MPFM"
)

FOLDERS = [
    ("B03", r"3.1.1_13-FT-0367 Riser P5 - Topside B03\2026\08. Agosto"),
    ("B08", r"3.1.2_13-FT-0167 Riser P2 - Topside B08\2026\08. Agosto"),
    ("B13", r"3.1.3_13-FT-0317 Riser P4 - Topside B13\2026\08. Agosto"),
    ("B05", r"3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05\2026\08. Agosto"),
    ("B10", r"3.1.5_18-FT-0506 PE 2 - Subsea B10\2026\08. Agosto"),
    ("B15", r"3.1.6_18-FT-1106 PW_104DA - Subsea B15\2026\08. Agosto"),
]

def post_folder(folder_path):
    payload = json.dumps({"folder": folder_path}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/process-folder",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())

def check_running():
    req = urllib.request.Request(f"{BASE_URL}/api/ops/processing-history?limit=1")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        # endpoint retorna lista ou dict com chave "runs"
        runs = data if isinstance(data, list) else data.get("runs", [])
        if runs and isinstance(runs[0], dict) and runs[0].get("status") == "running":
            return runs[0].get("id")
    return None

print("=== IMPORT AGOSTO — todos os bancos ===\n")

# Aguarda qualquer run em andamento antes de comecar
print("Aguardando runs anteriores...", flush=True)
for _ in range(60):
    run_id = check_running()
    if not run_id:
        break
    print(f"  run {run_id} ainda rodando, aguardando 10s...", flush=True)
    time.sleep(10)

for bank, sub in FOLDERS:
    folder = f"{BASE_PASTA}\\{sub}"
    print(f"\n[{bank}] {folder}", flush=True)
    t0 = time.time()
    try:
        result = post_folder(folder)
        elapsed = time.time() - t0
        status = result.get("status", "?")
        run_id = result.get("run_id", "?")
        imported = result.get("files_imported", "?")
        skipped = result.get("files_skipped", "?")
        print(f"  -> run {run_id} | status={status} | importados={imported} | skipped={skipped} | {elapsed:.0f}s", flush=True)
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  -> ERRO: {e} ({elapsed:.0f}s)", flush=True)

print("\n=== CONCLUÍDO ===")
