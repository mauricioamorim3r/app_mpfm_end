"""Import B03's pending files (present on disk, not yet in the DB) for 2026,
using the app's existing POST /api/monthly-gap-scan/import endpoint (same
pipeline as manual upload, force_overwrite=False). Reads the path list
produced by scan_b03_2026_pending.py (tmp_b03_2026_scan.json).

Usage:
    py -3 scripts/import_b03_2026_pending.py
"""
from __future__ import annotations

import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8765"


def post_import(month: str, paths: list[str]) -> dict:
    url = f"{BASE}/api/monthly-gap-scan/import"
    body = json.dumps({"month": month, "paths": paths}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    with open("tmp_b03_2026_scan.json", encoding="utf-8") as fh:
        scan = json.load(fh)

    pending_by_month = scan["pending_files_by_month"]
    only_months = sys.argv[1:]
    months = only_months if only_months else sorted(pending_by_month.keys())
    grand_processed = 0
    grand_skipped = 0
    for month in months:
        items = pending_by_month[month]
        paths = [item["path"] for item in items]
        print(f"\n=== Importando {month}: {len(paths)} arquivo(s) ===", flush=True)
        result = post_import(month, paths)
        processed = result.get("processed", 0)
        skipped = result.get("skipped", 0)
        grand_processed += processed
        grand_skipped += skipped
        print(f"  processed={processed} skipped={skipped} last_date={result.get('last_date')}")
        for line in result.get("log") or []:
            print(f"  log: {line}")

    print(f"\n=== TOTAL: processed={grand_processed} skipped={grand_skipped} ===")


if __name__ == "__main__":
    main()
