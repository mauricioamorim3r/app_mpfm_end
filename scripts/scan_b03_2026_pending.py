"""Scan B03 (3.1.1 Riser P5 - Topside) across all of 2026 via the live app's
/api/monthly-gap-scan endpoint, separating pending-import files from genuine
source gaps (no file on disk). Read-only: does not import anything.

Usage:
    py -3 scripts/scan_b03_2026_pending.py
"""
from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8765"
MONTHS = [f"2026-{m:02d}" for m in range(1, 9)]  # Jan..Aug 2026 (today is 2026-08-26)
BANK = "B03"


def fetch_month(month: str) -> dict:
    url = f"{BASE}/api/monthly-gap-scan?month={month}"
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    all_pending = []  # list of dict(month, day, hour_or_'daily', path)
    all_source_gaps = []  # list of dict(month, day, hour_or_'daily')
    per_month_summary = []

    pending_files_by_month = {}
    for month in MONTHS:
        print(f"Consultando {month}...", flush=True)
        data = fetch_month(month)
        banks = data.get("banks") or []
        b03 = next((b for b in banks if b.get("bank") == BANK), None)
        if b03 is None:
            print(f"{month}: bank B03 not found in response")
            continue
        if b03.get("error"):
            print(f"{month}: ERROR - {b03['error']}")
            per_month_summary.append((month, 0, 0, b03["error"]))
            continue

        pending_count = b03.get("pending_count", 0)
        gap_count = b03.get("source_gap_count", 0)
        per_month_summary.append((month, pending_count, gap_count, ""))

        for day_report in b03.get("days") or []:
            day = day_report["day"]
            for hour in day_report.get("pending_hours") or []:
                all_pending.append({"month": month, "day": day, "hour": hour})
            if day_report.get("daily_pending"):
                all_pending.append({"month": month, "day": day, "hour": "daily"})
            for hour in day_report.get("missing_hours") or []:
                all_source_gaps.append({"month": month, "day": day, "hour": hour})
            if day_report.get("daily_missing"):
                all_source_gaps.append({"month": month, "day": day, "hour": "daily"})

        scan_roots = set(b03.get("scan_roots") or [])
        folder_path = b03.get("folder_path") or ""
        all_pending_files = data.get("pending_files") or []
        matched = [
            item for item in all_pending_files
            if any(str(item.get("path", "")).startswith(root) for root in scan_roots)
            or str(item.get("path", "")).startswith(folder_path)
        ]
        if matched:
            pending_files_by_month[month] = matched

    print("=== Resumo por mes (B03) ===")
    for month, pending, gap, err in per_month_summary:
        note = f" ERRO: {err}" if err else ""
        print(f"  {month}: pendentes(horas/dias)={pending} lacunas_origem(horas/dias)={gap}{note}")

    print(f"\n=== Total pendente (import) por dia/hora: {len(all_pending)} ===")
    print(f"=== Total lacuna de origem (sem arquivo): {len(all_source_gaps)} ===")

    print("\n=== Arquivos pendentes encontrados no disco (por mes) ===")
    total_files = 0
    for month, items in pending_files_by_month.items():
        print(f"  {month}: {len(items)} arquivo(s)")
        total_files += len(items)
    print(f"  TOTAL arquivos a importar: {total_files}")

    with open("tmp_b03_2026_scan.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "per_month_summary": per_month_summary,
                "pending_hours_days": all_pending,
                "source_gaps": all_source_gaps,
                "pending_files_by_month": pending_files_by_month,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )
    print("\nDetalhes salvos em tmp_b03_2026_scan.json")


if __name__ == "__main__":
    main()
