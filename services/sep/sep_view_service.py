from __future__ import annotations

from collections import defaultdict


def build_sep_pivot_rows(rows: list[dict], align_map: dict[str, str]) -> tuple[list[dict], list[str]]:
    pivot_map = defaultdict(dict)
    pivot_meta = {}
    for row in rows:
        key = (row["day_ref"], row["hour_ref"], row["tag"])
        pivot_map[key][row["metric_name"]] = {"value": row["metric_value"], "id": row["id"]}
        source_name = row.get("source_file") or ""
        source_kind = "manual" if source_name.lower().startswith("manual") else "arquivo"
        pivot_meta[key] = {
            "day_ref": row["day_ref"],
            "hour_ref": row["hour_ref"],
            "bank": row["bank"],
            "tag": row["tag"],
            "source": source_name,
            "source_kind": source_kind,
            "source_record_id": row.get("source_record_id"),
            "is_official": row.get("is_official", 1),
            "aligned_banks": align_map.get(row["day_ref"], ""),
        }
    metric_cols = list(dict.fromkeys(row["metric_name"] for row in rows))
    pivot_rows = []
    for key in sorted(pivot_map.keys(), key=lambda item: (item[0] or "", item[1] if isinstance(item[1], int) else -1, item[2] or "")):
        row = dict(pivot_meta[key])
        row["sep_status"] = "aplicado" if row["aligned_banks"] else "extraido"
        row["source_label"] = "Manual" if row["source_kind"] == "manual" else "TXT oficial"
        for metric in metric_cols:
            entry = pivot_map[key].get(metric, {})
            row[metric] = entry.get("value")
            row[f"__id_{metric}"] = entry.get("id")
        pivot_rows.append(row)
    return pivot_rows, metric_cols


def build_sep_fluid_rows(rows: list[dict], fluid: str, headers: list[str]) -> list[dict]:
    pivot = defaultdict(dict)
    meta = {}
    for row in rows:
        key = (row["day_ref"], row["hour_ref"], row["tag"])
        pivot[key][row["metric_name"]] = row["metric_value"]
        meta[key] = {
            "day_ref": row["day_ref"],
            "hour_ref": row["hour_ref"],
            "tag": row["tag"],
            "instrument": row["instrument"],
            "source_file": row["source_file"],
            "source_kind": "manual" if str(row.get("source_file") or "").lower().startswith("manual") else "arquivo",
        }
    out = []
    for key in sorted(pivot.keys(), key=lambda item: (item[0] or "", -1 if item[1] is None else int(item[1]), item[2] or "")):
        row = dict(meta[key])
        row["Hour"] = "DAY" if row.get("hour_ref") is None else int(row.get("hour_ref"))
        row["__row_key"] = {
            "fluid": fluid,
            "day_ref": row.get("day_ref"),
            "hour_ref": row.get("hour_ref"),
            "tag": row.get("tag"),
            "instrument": row.get("instrument"),
        }
        for header in headers:
            row[header] = pivot[key].get(header)
        out.append(row)
    return out
