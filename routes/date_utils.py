from __future__ import annotations

from datetime import datetime


def normalize_date_input(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def normalize_date_range(date_from: str, date_to: str) -> tuple[str, str]:
    return normalize_date_input(date_from), normalize_date_input(date_to)


def normalize_validation_issue_day_ref(day_ref: str, created_at: str = "") -> str:
    raw = str(day_ref or "").strip()
    if not raw:
        return normalize_date_input((created_at or "")[:10])

    normalized = normalize_date_input(raw)
    if normalized and normalized != raw:
        return normalized

    if len(raw) == 5 and raw[2] == "_" and raw[:2].isdigit() and raw[3:].isdigit():
        year = ""
        created_prefix = str(created_at or "").strip()[:4]
        if len(created_prefix) == 4 and created_prefix.isdigit():
            year = created_prefix
        if year:
            return f"{year}-{raw[3:5]}-{raw[0:2]}"
    return raw
