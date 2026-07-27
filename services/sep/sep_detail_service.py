from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path


LIQUID_DETAIL_COLS = [
    "Pressure_kPa",
    "Pressure_barg",
    "Temperature_degC",
    "SD_kg_sm3",
    "MD_kg_m3",
    "IV_m3",
    "GV_m3",
    "GSV_sm3",
    "Mass_ton",
    "NSV_sm3",
    "BSW_pct",
    "CPL",
    "CTL",
]

GAS_DETAIL_COLS = [
    "Pressure_kPa_g",
    "Temperature_degC",
    "SD_kg_sm3",
    "DT_kg_m3",
    "GrVol_m3",
    "StVol_m3",
    "Mass_t",
    "Energy_GJ",
    "DiffPress_kPa",
    "Flowtime_min",
]


def store_sep_measurements(
    db_conn_fn,
    run_id: int,
    excel_file: str,
    unit: str,
    sep_data: dict,
    year: str,
    month: str,
    actual_day: str = None,
    source_file: str = "",
    source_record_id: int = None,
    is_official: bool = True,
):
    conn = db_conn_fn()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    sep_metrics = ["oil_m3", "oil_t", "gas_t", "water_t", "hc_t", "total_t", "temp", "pressure_barg", "density_sim"]
    sep_units = {
        "oil_m3": "m³",
        "oil_t": "t",
        "gas_t": "t",
        "water_t": "t",
        "hc_t": "t",
        "total_t": "t",
        "temp": "°C",
        "pressure_barg": "barg",
        "density_sim": "kg/m³",
    }

    base_day = actual_day if actual_day and len(actual_day) == 10 else f"{year}-{month}-01"
    for hour_key, hour_data in sep_data.items():
        hour_ref = None if hour_key == "DAY" else int(hour_key)
        day_ref = base_day
        for metric, value in hour_data.items():
            if metric not in sep_metrics or value is None:
                continue
            try:
                float_value = float(value)
                if float_value != float_value:
                    continue
            except Exception:
                continue
            unit_str = sep_units.get(metric, "")
            cur.execute(
                """DELETE FROM measurements_curated
                WHERE row_kind='sep' AND bank='SEP' AND metric_name=? AND hour_ref IS ?
                AND day_ref=? AND ((source_record_id IS NULL AND ? IS NULL) OR source_record_id=?)""",
                (metric, hour_ref, day_ref, source_record_id, source_record_id),
            )
            cur.execute(
                """INSERT INTO measurements_curated(
                    run_id, source_file, source_record_id, excel_file, sheet_name, row_kind, day_ref, hour_ref,
                    bank, loop, tipo, tag, instrument, metric_name, metric_value, metric_unit, is_official, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    source_file or "",
                    source_record_id,
                    excel_file,
                    "SEP",
                    "sep",
                    day_ref,
                    hour_ref,
                    "SEP",
                    "",
                    "",
                    "SEP",
                    unit or "",
                    metric,
                    float_value,
                    unit_str,
                    1 if is_official else 0,
                    now,
                ),
            )
    conn.commit()
    conn.close()


def sep_detail_headers(fluid: str):
    if fluid == "oleo":
        return LIQUID_DETAIL_COLS
    if fluid == "agua":
        return [col for col in LIQUID_DETAIL_COLS if col != "Pressure_barg"]
    return GAS_DETAIL_COLS


def sep_detail_kind(fluid: str) -> str:
    return {"oleo": "sep_oleo_detail", "gas": "sep_gas_detail", "agua": "sep_agua_detail"}[fluid]


def upsert_sep_detail_row(
    db_conn_fn,
    fluid: str,
    day_ref: str,
    hour_ref,
    tag: str,
    instrument: str = "",
    values: dict | None = None,
    source_file: str = "",
    source_record_id: int | None = None,
    is_official: bool = True,
):
    values = values or {}
    row_kind = sep_detail_kind(fluid)
    hour_ref = None if hour_ref in ("", None, "DAY") else int(hour_ref)
    headers = sep_detail_headers(fluid)
    conn = db_conn_fn()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    for metric in headers:
        if metric not in values:
            continue
        value = values.get(metric)
        if value in ("", None):
            cur.execute(
                "DELETE FROM measurements_curated WHERE row_kind=? AND bank='SEP' AND day_ref=? AND ((hour_ref IS NULL AND ? IS NULL) OR hour_ref=?) AND tag=? AND metric_name=? AND COALESCE(is_official,1)=1",
                (row_kind, day_ref, hour_ref, hour_ref, tag, metric),
            )
            continue
        try:
            float_value = float(value)
        except Exception:
            continue
        cur.execute(
            "DELETE FROM measurements_curated WHERE row_kind=? AND bank='SEP' AND day_ref=? AND ((hour_ref IS NULL AND ? IS NULL) OR hour_ref=?) AND tag=? AND metric_name=? AND COALESCE(is_official,1)=1",
            (row_kind, day_ref, hour_ref, hour_ref, tag, metric),
        )
        cur.execute(
            "INSERT INTO measurements_curated(run_id, source_file, source_record_id, excel_file, sheet_name, row_kind, day_ref, hour_ref, bank, loop, tipo, tag, instrument, metric_name, metric_value, metric_unit, is_official, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                None,
                source_file or f"manual_sep_{fluid}",
                source_record_id,
                "",
                row_kind,
                row_kind,
                day_ref,
                hour_ref,
                "SEP",
                "",
                f"sep_{fluid}",
                tag,
                instrument or tag,
                metric,
                float_value,
                "",
                1 if is_official else 0,
                now,
            ),
        )
    conn.commit()
    conn.close()


def store_sep_fluid_detail(
    db_conn_fn,
    inspect_txt_content_fn,
    run_id: int,
    excel_file: str,
    fluid_kind: str,
    file_path: str,
    actual_day: str = None,
    source_record_id: int = None,
    is_official: bool = True,
):
    info = inspect_txt_content_fn(Path(file_path))
    meter_id = info.get("meter_id", "") or ""
    if fluid_kind == "sep_oleo":
        parsed = _parse_sep_liquid_detail(file_path)
        cols = LIQUID_DETAIL_COLS
    elif fluid_kind == "sep_agua":
        parsed = _parse_sep_liquid_detail(file_path)
        cols = [col for col in LIQUID_DETAIL_COLS if col != "Pressure_barg"]
    elif fluid_kind == "sep_gas":
        parsed = _parse_sep_gas_detail(file_path)
        cols = GAS_DETAIL_COLS
    else:
        return
    if not actual_day or len(actual_day) != 10:
        actual_day = info.get("content_date", "") or ""
    if not actual_day or len(actual_day) != 10:
        match = re.search(r"(\d{4})(\d{2})(\d{2})", os.path.basename(file_path))
        actual_day = f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else ""
    if not actual_day:
        return
    row_kind = f"{fluid_kind}_detail"
    tag = meter_id or fluid_kind
    conn = db_conn_fn()
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    for hour_key, values in parsed.items():
        hour_ref = None if hour_key == "DAY" else int(hour_key)
        cur.execute(
            "DELETE FROM measurements_curated WHERE row_kind=? AND bank='SEP' AND day_ref=? AND ((hour_ref IS NULL AND ? IS NULL) OR hour_ref=?) AND tag=? AND ((source_record_id IS NULL AND ? IS NULL) OR source_record_id=?)",
            (row_kind, actual_day, hour_ref, hour_ref, tag, source_record_id, source_record_id),
        )
        for metric in cols:
            value = values.get(metric)
            if value is None:
                continue
            try:
                float_value = float(value)
            except Exception:
                continue
            cur.execute(
                "INSERT INTO measurements_curated(run_id, source_file, source_record_id, excel_file, sheet_name, row_kind, day_ref, hour_ref, bank, loop, tipo, tag, instrument, metric_name, metric_value, metric_unit, is_official, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    os.path.basename(file_path),
                    source_record_id,
                    excel_file,
                    row_kind,
                    row_kind,
                    actual_day,
                    hour_ref,
                    "SEP",
                    "",
                    fluid_kind,
                    tag,
                    meter_id,
                    metric,
                    float_value,
                    "",
                    1 if is_official else 0,
                    now,
                ),
            )
    conn.commit()
    conn.close()


def _is_number_local(value):
    try:
        float(value)
        return True
    except Exception:
        return False


def _parse_sep_liquid_detail(path: str):
    rows = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\r\n").split()
            if not parts:
                continue
            key = parts[0].upper()
            if key == "DAY" and len(parts) >= 13:
                rows["DAY"] = {
                    "Pressure_kPa": float(parts[1]),
                    "Pressure_barg": float(parts[1]) / 100.0,
                    "Temperature_degC": float(parts[2]),
                    "SD_kg_sm3": float(parts[3]),
                    "MD_kg_m3": float(parts[4]),
                    "IV_m3": float(parts[5]),
                    "GV_m3": float(parts[6]),
                    "GSV_sm3": float(parts[7]),
                    "Mass_ton": float(parts[8]),
                    "NSV_sm3": float(parts[9]),
                    "BSW_pct": float(parts[10]),
                    "CPL": float(parts[11]),
                    "CTL": float(parts[12]),
                }
            elif key.isdigit() and len(parts) >= 13:
                rows[int(key)] = {
                    "Pressure_kPa": float(parts[1]),
                    "Pressure_barg": float(parts[1]) / 100.0,
                    "Temperature_degC": float(parts[2]),
                    "SD_kg_sm3": float(parts[3]),
                    "MD_kg_m3": float(parts[4]),
                    "IV_m3": float(parts[5]),
                    "GV_m3": float(parts[6]),
                    "GSV_sm3": float(parts[7]),
                    "Mass_ton": float(parts[8]),
                    "NSV_sm3": float(parts[9]),
                    "BSW_pct": float(parts[10]),
                    "CPL": float(parts[11]),
                    "CTL": float(parts[12]),
                }
    return rows


def _parse_sep_gas_detail(path: str):
    rows = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\r\n").split()
            if not parts:
                continue
            key = parts[0].upper()
            if key == "DAILY":
                nums = [part for part in parts[1:] if _is_number_local(part)]
                if len(nums) >= 4:
                    rows["DAY"] = {
                        "Pressure_kPa_g": None,
                        "Temperature_degC": None,
                        "SD_kg_sm3": None,
                        "DT_kg_m3": None,
                        "GrVol_m3": float(nums[0]),
                        "StVol_m3": float(nums[1]),
                        "Mass_t": float(nums[2]) / 1000.0,
                        "Energy_GJ": float(nums[3]),
                        "DiffPress_kPa": float(nums[4]) if len(nums) > 4 else None,
                        "Flowtime_min": float(nums[5]) if len(nums) > 5 else None,
                    }
            elif key.isdigit() and len(parts) >= 11:
                rows[int(key)] = {
                    "Pressure_kPa_g": float(parts[1]),
                    "Temperature_degC": float(parts[2]),
                    "SD_kg_sm3": float(parts[3]),
                    "DT_kg_m3": float(parts[4]),
                    "GrVol_m3": float(parts[5]),
                    "StVol_m3": float(parts[6]),
                    "Mass_t": float(parts[7]) / 1000.0,
                    "Energy_GJ": float(parts[8]),
                    "DiffPress_kPa": float(parts[9]),
                    "Flowtime_min": float(parts[10]),
                }
    return rows
