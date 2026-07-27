from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


SEP_SOURCE_UNIT_CODE = "SEP"

SEP_UNIT_BY_METER = {
    "20FT0247": SEP_SOURCE_UNIT_CODE,
    "20FT0251": SEP_SOURCE_UNIT_CODE,
    "20FT0244": SEP_SOURCE_UNIT_CODE,
}

TXT_PATTERNS = {
    "sep_oleo": [r"\b20FT0247\b", r"Test Separator\s*&\s*FW Knockout"],
    "sep_agua": [r"\b20FT0251\b", r"Produced Water"],
    "sep_gas": [r"\b20FT0244\b", r"Orifice", r"Gas Lift"],
}

SEP_CANONICAL_TAG_BY_PHASE: dict[str, str] = {
    "sep_oleo": "20FT0247",
    "sep_agua": "20FT0251",
    "sep_gas":  "20FT0244",
}


def _parse_txt_period(text: str) -> tuple[str, str, str]:
    patterns = [
        (
            r"Period\s+start\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2}).*?"
            r"Period\s+end\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})",
            re.I | re.S,
        ),
        (
            r"Start\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2}).*?"
            r"End\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})",
            re.I | re.S,
        ),
    ]
    for pattern, flags in patterns:
        match = re.search(pattern, text, flags)
        if not match:
            continue
        start_raw = f"{match.group(1)} {match.group(2)}"
        end_raw = f"{match.group(3)} {match.group(4)}"
        try:
            report_start = datetime.strptime(start_raw, "%d/%m/%y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            report_end = datetime.strptime(end_raw, "%d/%m/%y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            production_day = report_start[:10]
            return report_start, report_end, production_day
        except Exception:
            continue
    return "", "", ""


def build_measurement_identity(prefix: str, *parts: str) -> str:
    values = [str(part or "").strip() for part in parts]
    if not all(values):
        return ""
    return "|".join([prefix] + values)


def classify_pdf_name(filename: str):
    name_upper = filename.upper()
    unit_match = re.search(r"(?<![A-Z0-9])(B03|B05|B08|B10|B13|B15|SEP)(?![A-Z0-9])", name_upper)
    unit = unit_match.group(1) if unit_match else None
    if "DAILY" in name_upper:
        return "daily", unit
    if "HOURLY" in name_upper:
        return "hourly", unit
    return "unknown", unit


def inspect_txt_content(path: Path) -> dict:
    text = path.read_text("utf-8", errors="replace")
    meter_id_match = re.search(r"Meter ID\s+([^\s]+)", text, re.I)
    location_match = re.search(r"Location\s+(.+)", text, re.I)

    meter_id = meter_id_match.group(1).strip() if meter_id_match else ""
    location = location_match.group(1).splitlines()[0].strip() if location_match else ""

    subtype = "unknown"
    upper_text = text.upper()
    if "WOBBE" in upper_text or "HEATING VALUE" in upper_text or "METER TYPE ORIFICE" in upper_text:
        subtype = "sep_gas"
    elif "PRODUCED WATER" in upper_text or meter_id == "20FT0251":
        subtype = "sep_agua"
    elif "FW KNOCKOUT" in upper_text or meter_id == "20FT0247":
        subtype = "sep_oleo"
    else:
        for candidate, patterns in TXT_PATTERNS.items():
            if any(re.search(pattern, text, re.I) for pattern in patterns):
                subtype = candidate
                break

    unit = SEP_UNIT_BY_METER.get(
        meter_id,
        SEP_SOURCE_UNIT_CODE if subtype.startswith("sep_") else "UNK",
    )

    report_start, report_end, content_date = _parse_txt_period(text)
    time_source = "content" if content_date else "filename_fallback"
    if not content_date:
        date_match = re.search(r"(\d{4})(\d{2})(\d{2})", path.name)
        content_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}" if date_match else ""
        if content_date:
            report_start = f"{content_date} 00:00:00"
            report_end = ""

    identity_key = build_measurement_identity("txt", meter_id, report_start, report_end)

    return {
        "file_type": subtype,
        "unit": unit,
        "meter_id": meter_id,
        "location": location,
        "content_date": content_date,
        "report_start": report_start,
        "report_end": report_end,
        "identity_key": identity_key,
        "time_source": time_source,
        "raw_preview": text[:400],
    }


def classify_input(path: Path, name: str) -> dict:
    lower_name = name.lower()
    if lower_name.endswith(".pdf"):
        file_type, unit = classify_pdf_name(name)
        return {
            "ext": "pdf",
            "file_type": file_type,
            "unit": unit,
            "meter_id": "",
            "location": "",
            "content_date": "",
            "report_start": "",
            "report_end": "",
            "identity_key": "",
            "time_source": "",
        }
    if lower_name.endswith(".txt"):
        info = inspect_txt_content(path)
        info["ext"] = "txt"
        return info
    return {
        "ext": "",
        "file_type": "unknown",
        "unit": None,
        "meter_id": "",
        "location": "",
        "content_date": "",
        "report_start": "",
        "report_end": "",
        "identity_key": "",
        "time_source": "",
    }
