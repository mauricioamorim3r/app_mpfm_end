"""Ad-hoc: dispara /api/process-folder no servidor já rodando para os PDFs
Daily/Hourly de agosto/2026 dos 6 pontos MPFM, sem tocar em Monthly."""
import json
import urllib.request

BASE_URL = "http://localhost:8765"

ROOT = (
    r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - "
    r"02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM"
)

BANKS = [
    ("B03_Riser_P5", r"3.1.1_13-FT-0367 Riser P5 - Topside B03"),
    ("B08_Riser_P2", r"3.1.2_13-FT-0167 Riser P2 - Topside B08"),
    ("B13_Riser_P4", r"3.1.3_13-FT-0317 Riser P4 - Topside B13"),
    ("B05_PE_4", r"3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05"),
    ("B10_PE_2", r"3.1.5_18-FT-0506 PE 2 - Subsea B10"),
    ("B15_PW_104DA", r"3.1.6_18-FT-1106 PW_104DA - Subsea B15"),
]

SUBFOLDERS = ["Daily", "Hourly"]


def call_process_folder(folder: str) -> dict:
    payload = json.dumps({"folder": folder}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/process-folder",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    for label, folder_name in BANKS:
        for sub in SUBFOLDERS:
            folder = f"{ROOT}\\{folder_name}\\2026\\08. Agosto\\{sub}"
            print(f"\n=== {label} / {sub} ===")
            print(folder)
            try:
                result = call_process_folder(folder)
            except Exception as exc:
                print(f"ERRO: {exc}")
                continue
            log = result.get("log", [])
            print(f"ok={result.get('ok')} last_date={result.get('last_date')}")
            for line in log:
                print(" ", line)


if __name__ == "__main__":
    main()
