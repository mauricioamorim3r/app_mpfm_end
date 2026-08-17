import json
import urllib.request

BASE_URL = "http://localhost:8765"
FOLDER = (
    r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - "
    r"02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM\3.1.5_18-FT-0506 "
    r"PE 2 - Subsea B10\2026\07. Julho\Hourly"
)


def call_process_folder(folder: str):
    req = urllib.request.Request(
        f"{BASE_URL}/api/process-folder",
        data=json.dumps({"folder": folder, "force_overwrite": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=1200) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    result = call_process_folder(FOLDER)
    print("status:", result.get("status"))
    print("run_id:", result.get("run_id"))
    for line in result.get("log", []):
        print(line)
