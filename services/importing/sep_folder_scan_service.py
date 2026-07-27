from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re

from routes.date_utils import normalize_date_input
from services.importing.input_classification_service import classify_input


DEFAULT_FOLDER_NAMES = ["FC13", "FC14", "FC17"]
REQUIRED_NAME_TOKEN = "run_24hours"
EXCLUDED_NAME_PREFIXES = (
    "alarmsandevents_hourly",
    "alarmsandevents_daily",
    "configuration",
    "run_daily",
    "parameters",
    "run_hourly",
    "_monthly",
)

TARGET_PHASE_BY_METER = {
    "20FT0247": "sep_oleo",
    "20FT0251": "sep_agua",
    "20FT0244": "sep_gas",
}

PHASE_LABELS = {
    "sep_oleo": "Oleo",
    "sep_agua": "Agua",
    "sep_gas": "Gas",
}


@dataclass(frozen=True)
class SepCandidate:
    path: Path
    name: str
    meter_id: str
    fluid_kind: str
    content_date: str
    report_start: str
    report_end: str
    location: str
    identity_key: str
    time_source: str
    folder_name: str


def _normalize_folder_name(value: str) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    match = re.match(r"^([A-Z]+)0*(\d+)$", raw)
    if match:
        return f"{match.group(1)}{int(match.group(2))}"
    return raw


def normalize_folder_names(folder_names: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in folder_names or DEFAULT_FOLDER_NAMES:
        value = _normalize_folder_name(item)
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized or list(DEFAULT_FOLDER_NAMES)


def inside_date_range(day: str, date_from: str = "", date_to: str = "") -> bool:
    if not day:
        return False
    if date_from and day < date_from:
        return False
    if date_to and day > date_to:
        return False
    return True


def iter_search_roots(source_root: Path, folder_names: list[str] | None = None) -> list[Path]:
    allowed = {value.casefold() for value in normalize_folder_names(folder_names)}
    roots: list[Path] = []
    seen: set[Path] = set()

    if _normalize_folder_name(source_root.name).casefold() in allowed:
        resolved = source_root.resolve()
        roots.append(resolved)
        seen.add(resolved)

    for path in source_root.rglob("*"):
        if not path.is_dir():
            continue
        if _normalize_folder_name(path.name).casefold() not in allowed:
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(resolved)

    return sorted(roots, key=lambda item: str(item).casefold())


def _is_allowed_txt_name(path: Path) -> bool:
    lower_name = path.name.casefold()
    if not lower_name.endswith(".txt"):
        return False
    if any(lower_name.startswith(prefix) for prefix in EXCLUDED_NAME_PREFIXES):
        return False
    return REQUIRED_NAME_TOKEN in lower_name


def collect_candidates(
    source_root: Path,
    *,
    date_from: str = "",
    date_to: str = "",
    folder_names: list[str] | None = None,
) -> tuple[list[SepCandidate], dict[str, int], list[str]]:
    candidates: list[SepCandidate] = []
    search_roots = iter_search_roots(source_root, folder_names)
    stats = {
        "search_root_count": len(search_roots),
        "txt_seen": 0,
        "txt_ignored_by_name": 0,
        "txt_ignored_by_meter": 0,
        "txt_ignored_by_date": 0,
        "classification_errors": 0,
    }
    warnings: list[str] = []
    seen: set[Path] = set()

    for search_root in search_roots:
        for path in search_root.rglob("*.txt"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            stats["txt_seen"] += 1
            if not _is_allowed_txt_name(path):
                stats["txt_ignored_by_name"] += 1
                continue
            try:
                info = classify_input(path, path.name)
            except Exception as exc:
                stats["classification_errors"] += 1
                warnings.append(f"WARN|classificacao_falhou|{path}|{exc}")
                continue

            meter_id = str(info.get("meter_id") or "").strip().upper()
            if meter_id not in TARGET_PHASE_BY_METER:
                stats["txt_ignored_by_meter"] += 1
                continue

            content_date = normalize_date_input(str(info.get("content_date") or "").strip())
            if not inside_date_range(content_date, date_from, date_to):
                stats["txt_ignored_by_date"] += 1
                continue

            candidates.append(
                SepCandidate(
                    path=resolved,
                    name=path.name,
                    meter_id=meter_id,
                    fluid_kind=TARGET_PHASE_BY_METER[meter_id],
                    content_date=content_date,
                    report_start=str(info.get("report_start") or "").strip(),
                    report_end=str(info.get("report_end") or "").strip(),
                    location=str(info.get("location") or "").strip(),
                    identity_key=str(info.get("identity_key") or "").strip(),
                    time_source=str(info.get("time_source") or "").strip(),
                    folder_name=search_root.name,
                )
            )

    candidates.sort(key=lambda item: (item.content_date, item.fluid_kind, item.name.casefold(), str(item.path).casefold()))
    return candidates, stats, warnings


def _serialize_candidate(item: SepCandidate) -> dict:
    return {
        "path": str(item.path),
        "name": item.name,
        "meter_id": item.meter_id,
        "fluid_kind": item.fluid_kind,
        "fluid_label": PHASE_LABELS.get(item.fluid_kind, item.fluid_kind),
        "content_date": item.content_date,
        "report_start": item.report_start,
        "report_end": item.report_end,
        "location": item.location,
        "identity_key": item.identity_key,
        "time_source": item.time_source,
        "folder_name": item.folder_name,
    }


def selected_for_import(candidates: list[SepCandidate], include_incomplete_days: bool) -> tuple[list[SepCandidate], list[str]]:
    by_day: dict[str, dict[str, list[SepCandidate]]] = defaultdict(lambda: defaultdict(list))
    for item in candidates:
        by_day[item.content_date][item.fluid_kind].append(item)

    selected: list[SepCandidate] = []
    skipped: list[str] = []
    required = set(PHASE_LABELS)
    for day in sorted(by_day):
        phase_map = by_day[day]
        present = set(phase_map)
        missing = [PHASE_LABELS[phase] for phase in sorted(required - present)]
        if missing and not include_incomplete_days:
            skipped.append(f"{day}: dia incompleto ignorado ({', '.join(missing)} ausente(s))")
            continue
        for phase in sorted(phase_map):
            selected.extend(sorted(phase_map[phase], key=lambda item: (item.name.casefold(), str(item.path).casefold())))
    return selected, skipped


def build_preview_payload(
    source_root: Path,
    candidates: list[SepCandidate],
    selected: list[SepCandidate],
    stats: dict[str, int],
    warnings: list[str],
    skipped: list[str],
    *,
    date_from: str = "",
    date_to: str = "",
    folder_names: list[str] | None = None,
    include_incomplete_days: bool = False,
) -> dict:
    by_day: dict[str, dict[str, list[SepCandidate]]] = defaultdict(lambda: defaultdict(list))
    for item in candidates:
        by_day[item.content_date][item.fluid_kind].append(item)

    days = []
    for day in sorted(by_day):
        phase_map = by_day[day]
        present = sorted(phase_map)
        days.append(
            {
                "date": day,
                "phase_labels": [PHASE_LABELS[phase] for phase in present],
                "is_complete": len(present) == len(PHASE_LABELS),
                "items": [_serialize_candidate(item) for phase in sorted(phase_map) for item in phase_map[phase]],
            }
        )

    return {
        "source_root": str(source_root),
        "date_from": date_from,
        "date_to": date_to,
        "folder_names": normalize_folder_names(folder_names),
        "include_incomplete_days": bool(include_incomplete_days),
        "stats": {
            **stats,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "day_count": len(days),
        },
        "days": days,
        "samples": [_serialize_candidate(item) for item in selected[:50]],
        "skipped": skipped,
        "warnings": warnings,
    }


def scan_sep_folder(
    source_root: Path,
    *,
    date_from: str = "",
    date_to: str = "",
    folder_names: list[str] | None = None,
    include_incomplete_days: bool = False,
) -> tuple[list[SepCandidate], list[SepCandidate], dict]:
    normalized_from = normalize_date_input(date_from)
    normalized_to = normalize_date_input(date_to)
    candidates, stats, warnings = collect_candidates(
        source_root.resolve(),
        date_from=normalized_from,
        date_to=normalized_to,
        folder_names=folder_names,
    )
    selected, skipped = selected_for_import(candidates, include_incomplete_days)
    preview = build_preview_payload(
        source_root.resolve(),
        candidates,
        selected,
        stats,
        warnings,
        skipped,
        date_from=normalized_from,
        date_to=normalized_to,
        folder_names=folder_names,
        include_incomplete_days=include_incomplete_days,
    )
    return candidates, selected, preview
