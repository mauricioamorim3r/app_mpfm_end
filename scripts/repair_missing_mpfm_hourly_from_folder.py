from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server


def _date_key(bank: str, production_date: str) -> str:
    return f"{bank}_{production_date[8:10]}_{production_date[5:7]}"


def _load_existing_status(bank: str, dates: list[str]) -> dict[str, dict[str, int]]:
    if not dates:
        return {}
    conn = server.db_conn()
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(dates))
    rows = conn.execute(
        f"""
        SELECT day_ref, row_kind, COUNT(*) AS n
        FROM measurements_curated
        WHERE bank=?
          AND COALESCE(is_official, 1)=1
          AND day_ref IN ({placeholders})
        GROUP BY day_ref, row_kind
        """,
        [bank] + dates,
    ).fetchall()
    conn.close()

    status = {day: {"daily": 0, "recon": 0, "hourly": 0} for day in dates}
    for row in rows:
        status.setdefault(row["day_ref"], {"daily": 0, "recon": 0, "hourly": 0})[row["row_kind"]] = int(row["n"] or 0)
    return status


def _load_sep_data_for_day(state: dict, bank: str, production_date: str) -> dict:
    alignment = server._get_sep_alignment(bank, production_date)
    if not alignment:
        return {}
    return server._des(state.get("sep_by_day", {}).get(production_date)) or server._load_sep_data_by_day(production_date)


def _build_recon_df_from_curated(bank: str, production_date: str):
    conn = server.db_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    daily_rows = cur.execute(
        """
        SELECT bank, loop, tipo, tag, instrument, metric_name, metric_value
        FROM measurements_curated
        WHERE row_kind='daily' AND bank=? AND day_ref=? AND COALESCE(is_official,1)=1
        ORDER BY tag, metric_name
        """,
        (bank, production_date),
    ).fetchall()
    hourly_rows = cur.execute(
        """
        SELECT hour_ref, tag, instrument, metric_name, metric_value
        FROM measurements_curated
        WHERE row_kind='hourly' AND bank=? AND day_ref=? AND COALESCE(is_official,1)=1
        ORDER BY hour_ref, tag, metric_name
        """,
        (bank, production_date),
    ).fetchall()
    conn.close()

    if not daily_rows:
        return None

    daily = {
        "date_from": production_date,
        "fpso_side": daily_rows[0]["loop"] or "",
        "unit_type": daily_rows[0]["tipo"] or "",
        "tags": {},
    }
    for row in daily_rows:
        tag = row["tag"] or ""
        entry = daily["tags"].setdefault(
            tag,
            {
                "instrument": row["instrument"] or "",
                "metrics": {
                    "mpfm_corr": {"gas": None, "oil": None, "hc": None, "water": None, "total": None},
                    "pvt_vol": {"gas": None, "oil": None, "water": None},
                },
            },
        )
        metric_map = server._RECON_DAILY_METRIC_MAP.get(row["metric_name"] or "")
        if metric_map:
            group_name, metric_name = metric_map
            entry["metrics"][group_name][metric_name] = float(row["metric_value"])

    hourly_records_map: dict[int, dict] = {}
    for row in hourly_rows:
        hour_ref = row["hour_ref"]
        if hour_ref is None:
            continue
        record = hourly_records_map.setdefault(
            int(hour_ref),
            {
                "hour": int(hour_ref),
                "date_from": production_date,
                "tags": {},
            },
        )
        tag_entry = record["tags"].setdefault(
            row["tag"] or "",
            {
                "instrument": row["instrument"] or "",
                "metrics": {
                    "mpfm_corr": {"gas": 0.0, "oil": 0.0, "hc": 0.0, "water": 0.0, "total": 0.0},
                    "pvt_vol": {"gas": 0.0, "oil": 0.0, "water": 0.0},
                },
            },
        )
        metric_map = server._RECON_HOURLY_METRIC_MAP.get(row["metric_name"] or "")
        if metric_map:
            group_name, metric_name = metric_map
            tag_entry["metrics"][group_name][metric_name] = float(row["metric_value"])

    hourly_records = [hourly_records_map[key] for key in sorted(hourly_records_map)]
    return server.engine.build_recon_df(daily, hourly_records, bank)


def _wait_for_workbook_refresh(workbook_path: Path, timeout_seconds: float = 60.0) -> bool:
    started = time.time()
    while time.time() - started < timeout_seconds:
        if not server.is_monthly_workbook_rebuilding(workbook_path):
            return True
        time.sleep(0.25)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover missing MPFM hourly/recon data from a folder of hourly PDFs.")
    parser.add_argument("--bank", required=True, help="Bank code, e.g. B15")
    parser.add_argument("--folder", required=True, help="Folder containing hourly PDF files")
    parser.add_argument("--date-from", default="", help="Optional inclusive production-date lower bound (YYYY-MM-DD)")
    parser.add_argument("--date-to", default="", help="Optional inclusive production-date upper bound (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Repair all parsed days even when hourly rows already exist")
    args = parser.parse_args()

    bank = str(args.bank or "").strip().upper()
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    import re
    all_pdfs = sorted(folder.glob("*.pdf"))
    if not all_pdfs:
        print("No PDF files found in folder.")
        return 0

    if not args.force:
        # Fast path: pre-check candidate dates from filenames
        candidate_dates = set()
        pdf_date_map = {}
        for pdf_path in all_pdfs:
            m = re.search(r"(\d{4})(\d{2})(\d{2})", pdf_path.name)
            if m:
                d_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                candidate_dates.add(d_str)
                pdf_date_map[pdf_path] = d_str

        if candidate_dates:
            status = _load_existing_status(bank, sorted(candidate_dates))
            missing_dates = {d for d, s in status.items() if s.get("hourly", 0) == 0}
            if not missing_dates:
                print("All candidate dates already present in DB. Nothing to repair.")
                return 0
            # Filter PDFs to only those matching missing dates or unmapped filenames
            all_pdfs = [p for p in all_pdfs if pdf_date_map.get(p) in missing_dates or p not in pdf_date_map]

    parsed_by_date: dict[str, dict[str, dict]] = defaultdict(dict)
    for pdf_path in all_pdfs:
        record = server.engine.parse_pdf(str(pdf_path), "hourly")
        production_date = str(record.get("date_from") or "").strip()
        if not production_date:
            continue
        if args.date_from and production_date < args.date_from:
            continue
        if args.date_to and production_date > args.date_to:
            continue
        identity_key = str(record.get("dt_from") or record.get("hour") or pdf_path.name)
        parsed_by_date[production_date][identity_key] = record

    if not parsed_by_date:
        raise SystemExit("No valid hourly PDFs found for the selected date range.")

    parsed_dates = sorted(parsed_by_date)
    status = _load_existing_status(bank, parsed_dates)
    targets = []
    for production_date in parsed_dates:
        day_status = status.get(production_date, {"daily": 0, "recon": 0, "hourly": 0})
        needs_repair = args.force or day_status.get("hourly", 0) == 0
        if needs_repair:
            targets.append((production_date, [parsed_by_date[production_date][key] for key in sorted(parsed_by_date[production_date])]))

    print(f"Parsed days: {parsed_dates}")
    print(f"Target days: {[day for day, _ in targets]}")
    if not targets:
        print("Nothing to repair.")
        return 0

    run_id = server.start_run("repair-mpfm-hourly-folder", str(folder), server.DEFAULT_DENSITY, len(targets))
    workbook_payloads: dict[tuple[str, str], dict[str, object]] = defaultdict(lambda: {"sheets": {}})
    state_by_month: dict[tuple[str, str], dict] = {}
    repaired_days: list[str] = []
    failed_days: list[dict[str, str]] = []

    try:
        for production_date, hourly_records in targets:
            yr = production_date[:4]
            mo = production_date[5:7]
            month_key = (yr, mo)
            state = state_by_month.setdefault(month_key, server.load_state(yr, mo))
            excel_file = server.excel_name(yr, mo)
            day_tag = f"{production_date[8:10]}_{production_date[5:7]}"
            state_key = _date_key(bank, production_date)
            hourly_sheet = f"HOURLY_{bank}_{day_tag}"
            recon_sheet = f"RECON_{bank}_{day_tag}"

            try:
                sep_data = _load_sep_data_for_day(state, bank, production_date)
                df_hourly = server.engine.build_hourly_df_with_sep(hourly_records, bank, sep_data)
                hourly_rows = server.dataframe_to_records(df_hourly)
                if not hourly_rows:
                    raise RuntimeError("Hourly dataframe did not produce any rows.")

                server._purge_mpfm_rows(bank, production_date, "hourly")
                server._purge_mpfm_rows(bank, production_date, "recon")
                server.db_store_sheet_rows(run_id, excel_file, hourly_sheet, hourly_rows)

                df_recon = _build_recon_df_from_curated(bank, production_date)
                if df_recon is None or df_recon.empty:
                    raise RuntimeError("Unable to rebuild recon from curated daily/hourly rows.")
                recon_rows = server.dataframe_to_records(df_recon)
                server.db_store_sheet_rows(run_id, excel_file, recon_sheet, recon_rows)

                hours = sorted({int(record.get("hour")) for record in hourly_records if record.get("hour") is not None})
                state.setdefault("processed_hours_by_key", {})[state_key] = hours
                state.setdefault("processed_hours", {})[day_tag] = hours

                bucket = workbook_payloads[month_key]
                bucket["sheets"][hourly_sheet] = df_hourly
                bucket["sheets"][recon_sheet] = df_recon

                server.db_add_issue(
                    run_id,
                    excel_file,
                    "hourly_recovered_from_folder",
                    "info",
                    f"{bank}/{production_date}",
                    production_date,
                    f"Dados hourly/recon recuperados a partir de {len(hourly_records)} PDF(s) da pasta {folder.name}.",
                )
                repaired_days.append(production_date)
                print(f"repaired {production_date} -> {excel_file} ({len(hourly_records)} records)")
            except Exception as exc:
                failed_days.append({"day": production_date, "error": str(exc)})
                print(f"failed {production_date}: {exc}")

        for (yr, mo), payload in workbook_payloads.items():
            state = state_by_month[(yr, mo)]
            status_df = server.engine.build_status_sheet(state)
            if status_df is not None and not status_df.empty:
                payload["sheets"]["STATUS_MES"] = status_df

            server.save_state(state)
            workbook_path = server.OUTPUT_DIR / server.excel_name(yr, mo)
            server.engine._merge_excel(str(workbook_path), payload["sheets"], [])
            server.schedule_monthly_base_unica(workbook_path, yr, mo)
            refreshed = _wait_for_workbook_refresh(workbook_path)
            print(f"workbook {workbook_path.name} refreshed={refreshed}")

        status_text = "ok" if not failed_days else "warn"
        server.finish_run(
            run_id,
            status_text,
            {
                "bank": bank,
                "folder": str(folder),
                "repaired_days": repaired_days,
                "failed_days": failed_days,
            },
        )
    except Exception:
        server.finish_run(
            run_id,
            "error",
            {
                "bank": bank,
                "folder": str(folder),
                "repaired_days": repaired_days,
                "failed_days": failed_days,
            },
        )
        raise

    if failed_days:
        print("FAILED DAYS")
        for item in failed_days:
            print(item)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())