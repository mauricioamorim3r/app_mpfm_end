from __future__ import annotations

import threading as _threading
import time as _time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

# ---------------------------------------------------------------------------
# In-process metadata cache — months_available changes only on new imports
# ---------------------------------------------------------------------------
_meta_cache: dict = {"months": None, "ts": 0.0}
_meta_cache_lock = _threading.Lock()
_META_CACHE_TTL = 120.0  # seconds


def _get_months_available(cur) -> list[str]:
    """Return sorted distinct months from both data tables, cached for TTL."""
    now = _time.monotonic()
    with _meta_cache_lock:
        if _meta_cache["months"] is not None and now - _meta_cache["ts"] < _META_CACHE_TTL:
            return _meta_cache["months"]

    # Single optimised query: use the index on day_ref directly, avoid substr
    # in the SELECT which prevents index-only scan on DISTINCT.
    rows = cur.execute(
        "SELECT DISTINCT day_ref FROM measurements_curated "
        "WHERE day_ref > '' ORDER BY day_ref"
    ).fetchall()
    months_curated = {r[0][:7] for r in rows if r[0] and len(r[0]) >= 7}

    rows2 = cur.execute(
        "SELECT DISTINCT production_date FROM mpfm_monitoring_daily "
        "WHERE production_date > ''"
    ).fetchall()
    months_ann = {r[0][:7] for r in rows2 if r[0] and len(r[0]) >= 7}

    result = sorted(months_curated | months_ann, reverse=True)
    with _meta_cache_lock:
        _meta_cache["months"] = result
        _meta_cache["ts"] = _time.monotonic()
    return result


def invalidate_months_cache() -> None:
    """Call after a processing_run finishes so the next request refreshes."""
    with _meta_cache_lock:
        _meta_cache["months"] = None
        _meta_cache["ts"] = 0.0


HC_LIMIT_PCT = 10.0
TOTAL_LIMIT_PCT = 7.0
CONSECUTIVE_WARNING_DAYS = 8
PROTOCOL_TRIGGER_DAYS = 10

MONITORING_BOOL_FIELDS = {
    "event_occurred",
    "new_pvt_result",
    "new_k_factor_implemented",
    "aligned_separator_test",
}

MONITORING_TEXT_FIELDS = {
    "event_type",
    "event_status",
    "sensor_redundancy_ptdp",
    "integrity_communication",
    "operation_mode",
    "observations",
    "instrument",
    "loop",
}

MONITORING_FIELDS = (
    "event_occurred",
    "event_type",
    "event_status",
    "sensor_redundancy_ptdp",
    "integrity_communication",
    "new_pvt_result",
    "new_k_factor_implemented",
    "operation_mode",
    "aligned_separator_test",
    "observations",
    "instrument",
    "loop",
)


def _parse_month_bounds(month: str) -> tuple[str, str]:
    raw = str(month or "").strip()
    if len(raw) != 7 or raw[4] != "-":
        return "", ""
    return f"{raw}-01", f"{raw}-31"


def normalize_meter_type(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw.startswith("sub"):
        return "Subsea"
    if raw.startswith("top"):
        return "Topside"
    return str(value or "").strip().title() or ""


def _ratio_pct(numerator_value, denominator_value):
    try:
        numerator = float(numerator_value)
        denominator = float(denominator_value)
        if not denominator:
            return None
        return ((numerator / denominator) - 1.0) * 100.0
    except Exception:
        return None


def _parse_iso_date(value: str):
    try:
        return datetime.strptime(str(value or "").strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _status_label_for_streak(days_outside_limits: int, protocol_required: bool) -> str:
    if protocol_required:
        return "Iniciar protocolo de tratamento de desvios no SGM-FM"
    if days_outside_limits >= CONSECUTIVE_WARNING_DAYS:
        return f"{days_outside_limits} dias consecutivos fora do limite"
    return "Fora do limite"


def _rounded(value, digits: int = 3):
    try:
        parsed = float(value)
        return round(parsed, digits)
    except Exception:
        return None


def build_monitoring_pair_map(cadastro: dict, normalize_tag_name: Callable[[str], str]) -> dict:
    topside_by_system = {}
    for entry in cadastro.get("banks_topside", []):
        if not entry.get("ativo", True):
            continue
        bank = str(entry.get("bank_code") or "").strip().upper()
        tag = str(entry.get("sistema") or "").strip()
        tag_norm = normalize_tag_name(tag)
        if not bank or not tag_norm:
            continue
        topside_by_system[tag_norm] = {
            "bank": bank,
            "tag": tag,
            "tag_norm": tag_norm,
            "instrument": str(entry.get("tag_associado") or "").strip(),
            "loop": str(entry.get("loop") or "").strip(),
            "meter_type": "Topside",
        }

    subsea_by_riser = {}
    pair_map = {}
    for entry in cadastro.get("banks_subsea", []):
        if not entry.get("ativo", True):
            continue
        bank = str(entry.get("bank_code") or "").strip().upper()
        tag = str(entry.get("sistema") or "").strip()
        tag_norm = normalize_tag_name(tag)
        riser_norm = normalize_tag_name(entry.get("chega_riser") or "")
        if not bank or not tag_norm:
            continue
        subsea_info = {
            "bank": bank,
            "tag": tag,
            "tag_norm": tag_norm,
            "instrument": str(entry.get("tag_associado") or "").strip(),
            "loop": str(entry.get("loop") or "").strip(),
            "meter_type": "Subsea",
        }
        if riser_norm:
            subsea_by_riser[riser_norm] = subsea_info
            topside_info = topside_by_system.get(riser_norm)
            if topside_info:
                pair_map[("Subsea", bank, tag_norm)] = topside_info

    for entry in cadastro.get("banks_topside", []):
        if not entry.get("ativo", True):
            continue
        bank = str(entry.get("bank_code") or "").strip().upper()
        tag = str(entry.get("sistema") or "").strip()
        tag_norm = normalize_tag_name(tag)
        if not bank or not tag_norm:
            continue
        subsea_info = subsea_by_riser.get(tag_norm)
        if subsea_info:
            pair_map[("Topside", bank, tag_norm)] = subsea_info

    return pair_map


def list_monitoring_rows(
    db_conn_fn,
    *,
    month: str,
    bank: str = "",
    tag: str = "",
    meter_type: str = "",
    event_status: str = "",
    only_outside_limits: bool = False,
    load_cadastro_fn,
    normalize_tag_name: Callable[[str], str],
) -> dict:
    date_from, date_to = _parse_month_bounds(month)
    if not date_from:
        return {
            "month": "",
            "months_available": [],
            "rows": [],
            "banks": [],
            "tags": [],
            "meter_types": ["Subsea", "Topside"],
            "summary": {},
            "limits": {"hc_pct": HC_LIMIT_PCT, "total_pct": TOTAL_LIMIT_PCT},
        }

    conn = db_conn_fn()
    cur = conn.cursor()

    months_available = _get_months_available(cur)

    base_rows = cur.execute(
        """
        SELECT
            day_ref AS production_date,
            bank,
            COALESCE(loop,'') AS loop,
            COALESCE(tipo,'') AS meter_type,
            COALESCE(tag,'') AS tag,
            COALESCE(instrument,'') AS instrument,
            COUNT(DISTINCT CASE WHEN row_kind='hourly' THEN hour_ref END) AS hours_available,
            MAX(CASE WHEN row_kind='daily' AND metric_name='PVT vol Óleo (m³)' THEN metric_value END) AS oil_sm3,
            MAX(CASE WHEN row_kind='daily' AND metric_name='PVT vol Gás (Sm³)' THEN metric_value END) AS gas_sm3,
            MAX(CASE WHEN row_kind='daily' AND metric_name='PVT vol Água (m³)' THEN metric_value END) AS water_sm3,
            MAX(CASE WHEN row_kind='daily' AND metric_name='PVT mass Óleo (t)' THEN metric_value END) AS oil_t,
            MAX(CASE WHEN row_kind='daily' AND metric_name='PVT mass Gás (t)' THEN metric_value END) AS gas_t,
            MAX(CASE WHEN row_kind='daily' AND metric_name='PVT mass Água (t)' THEN metric_value END) AS water_t,
            COALESCE(
                MAX(CASE WHEN row_kind='daily' AND metric_name='Pressão (barg)' THEN metric_value END),
                AVG(CASE WHEN row_kind='hourly' AND metric_name='Pressão (barg)' THEN metric_value END)
            ) AS pressure_barg,
            COALESCE(
                MAX(CASE WHEN row_kind='daily' AND metric_name='Temperatura (°C)' THEN metric_value END),
                AVG(CASE WHEN row_kind='hourly' AND metric_name='Temperatura (°C)' THEN metric_value END)
            ) AS temperature_c
        FROM measurements_active
        WHERE day_ref BETWEEN ? AND ?
          AND bank<>'' AND bank<>'SEP'
          AND row_kind IN ('daily','hourly')
        GROUP BY day_ref, bank, COALESCE(loop,''), COALESCE(tipo,''), COALESCE(tag,''), COALESCE(instrument,'')
        ORDER BY day_ref, bank, meter_type, tag
        """,
        (date_from, date_to),
    ).fetchall()

    annotation_rows = [
        dict(row)
        for row in cur.execute(
            """
            SELECT
                id,
                production_date,
                bank,
                tag,
                meter_type,
                instrument,
                loop,
                event_occurred,
                event_type,
                event_status,
                sensor_redundancy_ptdp,
                integrity_communication,
                new_pvt_result,
                new_k_factor_implemented,
                operation_mode,
                aligned_separator_test,
                observations,
                created_at,
                updated_at
            FROM mpfm_monitoring_daily
            WHERE production_date BETWEEN ? AND ?
            ORDER BY production_date, bank, meter_type, tag
            """,
            (date_from, date_to),
        ).fetchall()
    ]
    conn.close()

    annotations_by_key = {}
    for row in annotation_rows:
        normalized_type = normalize_meter_type(row.get("meter_type"))
        key = (
            str(row.get("production_date") or ""),
            str(row.get("bank") or "").strip().upper(),
            normalize_tag_name(row.get("tag") or ""),
            normalized_type,
        )
        row["meter_type"] = normalized_type
        annotations_by_key[key] = row

    merged_rows = []
    merged_by_key = {}

    for row in base_rows:
        production_date = str(row["production_date"] or "")
        row_bank = str(row["bank"] or "").strip().upper()
        row_tag = str(row["tag"] or "").strip()
        row_tag_norm = normalize_tag_name(row_tag)
        row_type = normalize_meter_type(row["meter_type"])
        key = (production_date, row_bank, row_tag_norm, row_type)
        note = annotations_by_key.get(key) or {}

        oil_t = row["oil_t"]
        gas_t = row["gas_t"]
        water_t = row["water_t"]
        hc_t = None if oil_t is None and gas_t is None else (oil_t or 0) + (gas_t or 0)
        total_t = None if hc_t is None and water_t is None else (hc_t or 0) + (water_t or 0)
        source_mode = "Medição"
        if note:
            source_mode = "Medição + anotação"

        merged = {
            "id": note.get("id"),
            "production_date": production_date,
            "bank": row_bank,
            "tag": row_tag,
            "tag_norm": row_tag_norm,
            "meter_type": row_type,
            "instrument": note.get("instrument") or row["instrument"] or "",
            "loop": note.get("loop") or row["loop"] or "",
            "hours_available": int(row["hours_available"] or 0),
            "oil_sm3": _rounded(row["oil_sm3"]),
            "gas_sm3": _rounded(row["gas_sm3"]),
            "water_sm3": _rounded(row["water_sm3"]),
            "oil_t": _rounded(oil_t),
            "gas_t": _rounded(gas_t),
            "water_t": _rounded(water_t),
            "hc_t": _rounded(hc_t),
            "total_t": _rounded(total_t),
            "pressure_barg": _rounded(row["pressure_barg"]),
            "temperature_c": _rounded(row["temperature_c"]),
            "source_mode": source_mode,
            "has_measurement": True,
            "event_occurred": note.get("event_occurred", ""),
            "event_type": note.get("event_type", ""),
            "event_status": note.get("event_status", ""),
            "sensor_redundancy_ptdp": note.get("sensor_redundancy_ptdp", ""),
            "integrity_communication": note.get("integrity_communication", ""),
            "new_pvt_result": note.get("new_pvt_result", ""),
            "new_k_factor_implemented": note.get("new_k_factor_implemented", ""),
            "operation_mode": note.get("operation_mode", ""),
            "aligned_separator_test": note.get("aligned_separator_test", ""),
            "observations": note.get("observations", ""),
            "created_at": note.get("created_at", ""),
            "updated_at": note.get("updated_at", ""),
        }
        merged_by_key[key] = merged
        merged_rows.append(merged)

    for key, note in annotations_by_key.items():
        if key in merged_by_key:
            continue
        merged = {
            "id": note.get("id"),
            "production_date": note.get("production_date", ""),
            "bank": str(note.get("bank") or "").strip().upper(),
            "tag": note.get("tag", ""),
            "tag_norm": key[2],
            "meter_type": normalize_meter_type(note.get("meter_type")),
            "instrument": note.get("instrument", ""),
            "loop": note.get("loop", ""),
            "hours_available": 0,
            "oil_sm3": None,
            "gas_sm3": None,
            "water_sm3": None,
            "oil_t": None,
            "gas_t": None,
            "water_t": None,
            "hc_t": None,
            "total_t": None,
            "pressure_barg": None,
            "temperature_c": None,
            "source_mode": "Anotação manual",
            "has_measurement": False,
            "event_occurred": note.get("event_occurred", ""),
            "event_type": note.get("event_type", ""),
            "event_status": note.get("event_status", ""),
            "sensor_redundancy_ptdp": note.get("sensor_redundancy_ptdp", ""),
            "integrity_communication": note.get("integrity_communication", ""),
            "new_pvt_result": note.get("new_pvt_result", ""),
            "new_k_factor_implemented": note.get("new_k_factor_implemented", ""),
            "operation_mode": note.get("operation_mode", ""),
            "aligned_separator_test": note.get("aligned_separator_test", ""),
            "observations": note.get("observations", ""),
            "created_at": note.get("created_at", ""),
            "updated_at": note.get("updated_at", ""),
        }
        merged_by_key[key] = merged
        merged_rows.append(merged)

    pair_map = build_monitoring_pair_map(load_cadastro_fn() or {}, normalize_tag_name)
    for row in merged_rows:
        pair_ref = pair_map.get((row["meter_type"], row["bank"], row["tag_norm"]))
        if not pair_ref:
            row["pair_label"] = ""
            row["pair_bank"] = ""
            row["pair_tag"] = ""
            row["pair_meter_type"] = ""
            row["pair_key"] = ""
            row["hc_reference"] = None
            row["hc_compare"] = None
            row["total_reference"] = None
            row["total_compare"] = None
            row["hc_deviation_pct"] = None
            row["total_deviation_pct"] = None
            row["limit_status"] = ""
            row["status_label"] = ""
            row["days_outside_limits"] = 0
            row["outside_hc_limit"] = False
            row["outside_total_limit"] = False
            row["outside_limits"] = False
            row["attention_threshold_reached"] = False
            row["protocol_required"] = False
            row["monthly_hc_deviation_pct"] = None
            row["monthly_total_deviation_pct"] = None
            row["monthly_days_paired"] = 0
            row["monthly_outside_days"] = 0
            row["monthly_max_consecutive_outside_days"] = 0
            continue

        row["pair_label"] = f'{pair_ref["bank"]} · {pair_ref["tag"]}'
        row["pair_bank"] = pair_ref["bank"]
        row["pair_tag"] = pair_ref["tag"]
        row["pair_meter_type"] = pair_ref["meter_type"]
        row["pair_key"] = ""
        counterpart_key = (
            row["production_date"],
            pair_ref["bank"],
            pair_ref["tag_norm"],
            pair_ref["meter_type"],
        )
        counterpart = merged_by_key.get(counterpart_key)
        if not counterpart:
            row["hc_reference"] = None
            row["hc_compare"] = None
            row["total_reference"] = None
            row["total_compare"] = None
            row["hc_deviation_pct"] = None
            row["total_deviation_pct"] = None
            row["limit_status"] = "Sem par no dia"
            row["status_label"] = "Sem par no dia"
            row["days_outside_limits"] = 0
            row["outside_hc_limit"] = False
            row["outside_total_limit"] = False
            row["outside_limits"] = False
            row["attention_threshold_reached"] = False
            row["protocol_required"] = False
            row["monthly_hc_deviation_pct"] = None
            row["monthly_total_deviation_pct"] = None
            row["monthly_days_paired"] = 0
            row["monthly_outside_days"] = 0
            row["monthly_max_consecutive_outside_days"] = 0
            continue

        if row["meter_type"] == "Subsea":
            base_row = row
            compare_row = counterpart
        else:
            base_row = counterpart
            compare_row = row

        row["pair_key"] = f'{base_row["bank"]}|{base_row["tag_norm"]}|{compare_row["bank"]}|{compare_row["tag_norm"]}'
        row["hc_reference"] = _rounded(base_row.get("hc_t"))
        row["hc_compare"] = _rounded(compare_row.get("hc_t"))
        row["total_reference"] = _rounded(base_row.get("total_t"))
        row["total_compare"] = _rounded(compare_row.get("total_t"))
        hc_pct = _ratio_pct(base_row.get("hc_t"), compare_row.get("hc_t"))
        total_pct = _ratio_pct(base_row.get("total_t"), compare_row.get("total_t"))
        row["hc_deviation_pct"] = _rounded(hc_pct)
        row["total_deviation_pct"] = _rounded(total_pct)
        row["days_outside_limits"] = 0
        row["attention_threshold_reached"] = False
        row["protocol_required"] = False
        row["monthly_hc_deviation_pct"] = None
        row["monthly_total_deviation_pct"] = None
        row["monthly_days_paired"] = 0
        row["monthly_outside_days"] = 0
        row["monthly_max_consecutive_outside_days"] = 0
        if hc_pct is None or total_pct is None:
            row["outside_hc_limit"] = False
            row["outside_total_limit"] = False
            row["outside_limits"] = False
            row["limit_status"] = "Par sem base"
            row["status_label"] = "Par sem base"
        else:
            row["outside_hc_limit"] = abs(hc_pct) > HC_LIMIT_PCT
            row["outside_total_limit"] = abs(total_pct) > TOTAL_LIMIT_PCT
            row["outside_limits"] = row["outside_hc_limit"] or row["outside_total_limit"]
            if row["outside_limits"]:
                row["limit_status"] = "Fora do limite"
                row["status_label"] = "Fora do limite"
            else:
                row["limit_status"] = "Dentro do limite"
                row["status_label"] = "Dentro do limite"

    monthly_pair_entries = {}
    for row in merged_rows:
        if row.get("meter_type") != "Subsea":
            continue
        if not row.get("pair_key"):
            continue
        if row.get("hc_deviation_pct") is None and row.get("total_deviation_pct") is None:
            continue
        counterpart_key = (
            row["production_date"],
            row["pair_bank"],
            normalize_tag_name(row["pair_tag"]),
            row["pair_meter_type"],
        )
        counterpart = merged_by_key.get(counterpart_key)
        pair_entry = monthly_pair_entries.setdefault(
            row["pair_key"],
            {
                "key": row["pair_key"],
                "subsea_bank": row["bank"],
                "subsea_tag": row["tag"],
                "subsea_tag_norm": row["tag_norm"],
                "topside_bank": row["pair_bank"],
                "topside_tag": row["pair_tag"],
                "topside_tag_norm": normalize_tag_name(row.get("pair_tag") or ""),
                "days": {},
            },
        )
        pair_entry["days"][row["production_date"]] = {
            "date": row["production_date"],
            "subsea": row,
            "topside": counterpart,
        }

    monthly_pairs = []
    for pair_key, pair_entry in monthly_pair_entries.items():
        day_keys = sorted(pair_entry["days"].keys())
        consecutive_days_outside = 0
        max_consecutive_days_outside = 0
        previous_date = None
        protocol_triggered_in_month = False
        outside_days = 0

        valid_hc_pairs = []
        valid_total_pairs = []
        for day_key in day_keys:
            entry = pair_entry["days"][day_key]
            subsea_row = entry["subsea"]
            topside_row = entry["topside"]
            current_date = _parse_iso_date(day_key)
            is_consecutive_calendar_day = (
                previous_date is not None and current_date is not None and current_date == previous_date + timedelta(days=1)
            )
            is_outside = bool(subsea_row.get("outside_limits"))
            if is_outside:
                consecutive_days_outside = consecutive_days_outside + 1 if is_consecutive_calendar_day else 1
                outside_days += 1
            else:
                consecutive_days_outside = 0
            previous_date = current_date or previous_date
            max_consecutive_days_outside = max(max_consecutive_days_outside, consecutive_days_outside)
            attention_threshold_reached = is_outside and consecutive_days_outside >= CONSECUTIVE_WARNING_DAYS
            protocol_required = is_outside and consecutive_days_outside >= PROTOCOL_TRIGGER_DAYS
            protocol_triggered_in_month = protocol_triggered_in_month or protocol_required
            status_label = _status_label_for_streak(consecutive_days_outside, protocol_required) if is_outside else "Dentro do limite"

            if subsea_row.get("hc_reference") is not None and subsea_row.get("hc_compare") is not None:
                valid_hc_pairs.append((float(subsea_row["hc_reference"]), float(subsea_row["hc_compare"])))
            if subsea_row.get("total_reference") is not None and subsea_row.get("total_compare") is not None:
                valid_total_pairs.append((float(subsea_row["total_reference"]), float(subsea_row["total_compare"])))

            for pair_row in (subsea_row, topside_row):
                if not pair_row:
                    continue
                pair_row["days_outside_limits"] = consecutive_days_outside if is_outside else 0
                pair_row["attention_threshold_reached"] = attention_threshold_reached
                pair_row["protocol_required"] = protocol_required
                pair_row["status_label"] = status_label

        hc_reference_month = sum(item[0] for item in valid_hc_pairs) if valid_hc_pairs else None
        hc_compare_month = sum(item[1] for item in valid_hc_pairs) if valid_hc_pairs else None
        total_reference_month = sum(item[0] for item in valid_total_pairs) if valid_total_pairs else None
        total_compare_month = sum(item[1] for item in valid_total_pairs) if valid_total_pairs else None
        monthly_hc_deviation_pct = _rounded(_ratio_pct(hc_reference_month, hc_compare_month))
        monthly_total_deviation_pct = _rounded(_ratio_pct(total_reference_month, total_compare_month))
        current_consecutive_days_outside = 0
        if day_keys:
            last_subsea_row = pair_entry["days"][day_keys[-1]]["subsea"]
            current_consecutive_days_outside = int(last_subsea_row.get("days_outside_limits") or 0)

        pair_summary = {
            "key": f'{pair_entry["subsea_tag_norm"]}|{pair_entry["topside_tag_norm"]}',
            "pair_key": pair_key,
            "subsea_bank": pair_entry["subsea_bank"],
            "subsea_tag": pair_entry["subsea_tag"],
            "topside_bank": pair_entry["topside_bank"],
            "topside_tag": pair_entry["topside_tag"],
            "days_paired": len(day_keys),
            "outside_days": outside_days,
            "latest_date": day_keys[-1] if day_keys else "",
            "monthly_hc_deviation_pct": monthly_hc_deviation_pct,
            "monthly_total_deviation_pct": monthly_total_deviation_pct,
            "current_consecutive_outside_days": current_consecutive_days_outside,
            "max_consecutive_outside_days": max_consecutive_days_outside,
            "warning_threshold_reached": max_consecutive_days_outside >= CONSECUTIVE_WARNING_DAYS,
            "protocol_required": current_consecutive_days_outside >= PROTOCOL_TRIGGER_DAYS,
            "protocol_triggered_in_month": protocol_triggered_in_month,
        }
        monthly_pairs.append(pair_summary)

        for day_key in day_keys:
            for pair_row in (pair_entry["days"][day_key]["subsea"], pair_entry["days"][day_key]["topside"]):
                if not pair_row:
                    continue
                pair_row["monthly_hc_deviation_pct"] = monthly_hc_deviation_pct
                pair_row["monthly_total_deviation_pct"] = monthly_total_deviation_pct
                pair_row["monthly_days_paired"] = len(day_keys)
                pair_row["monthly_outside_days"] = outside_days
                pair_row["monthly_max_consecutive_outside_days"] = max_consecutive_days_outside

    filtered_rows = []
    bank_filter = str(bank or "").strip().upper()
    tag_filter = normalize_tag_name(tag or "")
    meter_type_filter = normalize_meter_type(meter_type) if meter_type else ""
    event_status_filter = str(event_status or "").strip().lower()
    for row in merged_rows:
        if bank_filter and row["bank"] != bank_filter:
            continue
        if tag_filter and row["tag_norm"] != tag_filter:
            continue
        if meter_type_filter and row["meter_type"] != meter_type_filter:
            continue
        if event_status_filter and str(row.get("event_status") or "").strip().lower() != event_status_filter:
            continue
        if only_outside_limits and row.get("limit_status") != "Fora do limite":
            continue
        filtered_rows.append(row)

    filtered_rows.sort(
        key=lambda item: (
            item["production_date"],
            item["bank"],
            item["meter_type"],
            item["tag"],
        )
    )

    def _has_event(row):
        return str(row.get("event_occurred") or "").strip().lower() in {"sim", "yes", "true", "1"}

    summary = {
        "rows": len(filtered_rows),
        "paired": sum(1 for row in filtered_rows if row.get("pair_label")),
        "outside_hc": sum(1 for row in filtered_rows if row.get("hc_deviation_pct") is not None and abs(row["hc_deviation_pct"]) > HC_LIMIT_PCT),
        "outside_total": sum(1 for row in filtered_rows if row.get("total_deviation_pct") is not None and abs(row["total_deviation_pct"]) > TOTAL_LIMIT_PCT),
        "with_event": sum(1 for row in filtered_rows if _has_event(row)),
        "without_counterpart": sum(1 for row in filtered_rows if row.get("pair_label") and row.get("hc_deviation_pct") is None),
        "warning_pairs": len({row.get("pair_key") for row in filtered_rows if row.get("pair_key") and row.get("attention_threshold_reached")}),
        "protocol_pairs": len({row.get("pair_key") for row in filtered_rows if row.get("pair_key") and row.get("protocol_required")}),
    }

    banks = sorted({row["bank"] for row in merged_rows if row["bank"]})
    tags = sorted({row["tag"] for row in merged_rows if row["tag"]})
    event_statuses = sorted({row["event_status"] for row in merged_rows if row.get("event_status")})

    for row in filtered_rows:
        row.pop("tag_norm", None)

    return {
        "month": month,
        "months_available": months_available,
        "banks": banks,
        "tags": tags,
        "meter_types": ["Subsea", "Topside"],
        "event_statuses": event_statuses,
        "rows": filtered_rows,
        "summary": summary,
        "limits": {"hc_pct": HC_LIMIT_PCT, "total_pct": TOTAL_LIMIT_PCT},
        "monthly_pairs": monthly_pairs,
    }


def upsert_monitoring_annotation(db_conn_fn, payload: dict) -> int:
    production_date = str(payload.get("production_date") or "").strip()
    bank = str(payload.get("bank") or "").strip().upper()
    tag = str(payload.get("tag") or "").strip()
    meter_type = normalize_meter_type(payload.get("meter_type") or "")
    if not (production_date and bank and tag and meter_type):
        raise ValueError("production_date, bank, tag e meter_type são obrigatórios")

    values = {}
    for field in MONITORING_FIELDS:
        raw = payload.get(field, "")
        values[field] = "" if raw is None else str(raw).strip()

    now = datetime.now().isoformat(timespec="seconds")
    conn = db_conn_fn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO mpfm_monitoring_daily (
            production_date, bank, tag, meter_type, instrument, loop,
            event_occurred, event_type, event_status, sensor_redundancy_ptdp,
            integrity_communication, new_pvt_result, new_k_factor_implemented,
            operation_mode, aligned_separator_test, observations,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(production_date, bank, tag, meter_type) DO UPDATE SET
            instrument=excluded.instrument,
            loop=excluded.loop,
            event_occurred=excluded.event_occurred,
            event_type=excluded.event_type,
            event_status=excluded.event_status,
            sensor_redundancy_ptdp=excluded.sensor_redundancy_ptdp,
            integrity_communication=excluded.integrity_communication,
            new_pvt_result=excluded.new_pvt_result,
            new_k_factor_implemented=excluded.new_k_factor_implemented,
            operation_mode=excluded.operation_mode,
            aligned_separator_test=excluded.aligned_separator_test,
            observations=excluded.observations,
            updated_at=excluded.updated_at
        """,
        (
            production_date,
            bank,
            tag,
            meter_type,
            values["instrument"],
            values["loop"],
            values["event_occurred"],
            values["event_type"],
            values["event_status"],
            values["sensor_redundancy_ptdp"],
            values["integrity_communication"],
            values["new_pvt_result"],
            values["new_k_factor_implemented"],
            values["operation_mode"],
            values["aligned_separator_test"],
            values["observations"],
            now,
            now,
        ),
    )
    row = cur.execute(
        """
        SELECT id FROM mpfm_monitoring_daily
        WHERE production_date=? AND bank=? AND tag=? AND meter_type=?
        """,
        (production_date, bank, tag, meter_type),
    ).fetchone()
    conn.commit()
    conn.close()
    return int(row[0]) if row else 0


def delete_monitoring_annotation(db_conn_fn, item_id: int) -> None:
    conn = db_conn_fn()
    conn.execute("DELETE FROM mpfm_monitoring_daily WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
