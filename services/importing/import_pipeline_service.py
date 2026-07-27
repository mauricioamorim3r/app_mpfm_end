from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path

from services.importing.input_classification_service import build_measurement_identity, classify_input
from services.importing.import_validation_service import validate_pdf_import_rule, validate_txt_import_rule


INSTRUMENT_TO_BANK = {
    '18FT0506': 'B10', '18FT0306': 'B10', '18FT0106': 'B10',
    '18FT1506': 'B05', '18FT1406': 'B05', '18FT1706': 'B05', '18FT1806': 'B05',
    '18FT0706': 'B15', '18FT0906': 'B15', '18FT1206': 'B15', '18FT1106': 'B15',
    '13FT0167': 'B08', '13FT0217': 'B08',
    '13FT0267': 'B13', '13FT0317': 'B13',
    '13FT0367': 'B03', '13FT0417': 'B03',
    '20FT0244': 'SEP', '20FT0247': 'SEP', '20FT0251': 'SEP'
}

TAG_TO_BANK = {
    'PE_2': 'B10', 'PE_8': 'B10', 'PE_9': 'B10',
    'PE_4': 'B05', 'PE_EO10': 'B05', 'PE_EO105': 'B05', 'PE_EO4': 'B05',
    'PE_1': 'B15', 'PI_1': 'B15', 'PI_2': 'B15', 'PW-104DA': 'B15',
    'Riser_P1': 'B08', 'Riser_P2': 'B08',
    'Riser_P3': 'B13', 'Riser_P4': 'B13',
    'Riser_P5': 'B03', 'Riser_P6': 'B03',
}

def resolve_bank_from_record(record: dict, fallback_unit: str | None) -> str:
    tags = record.get("tags") or {}
    for tag_name, td in tags.items():
        instrument = (td.get("instrument") or "").strip()
        if instrument in INSTRUMENT_TO_BANK:
            return INSTRUMENT_TO_BANK[instrument]
        if tag_name in TAG_TO_BANK:
            return TAG_TO_BANK[tag_name]
    if fallback_unit and fallback_unit in {"B03", "B05", "B08", "B10", "B13", "B15", "SEP"}:
        return fallback_unit
    return "UNK"


def _normalize_tag_name(tag: str) -> str:
    value = str(tag or "").strip()
    if not value:
        return ""
    value = re.sub(r"[-_\s]+", "", value)
    return value.upper()


def _sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_ingestion_batches(
    paths_names,
    run_id: int,
    source_type: str,
    parse_pdf_fn,
    build_cadastro_index_fn,
    log_raw_file_fn,
    log_file_fn,
    find_existing_import_by_identity_fn,
    find_existing_import_by_hash_fn,
    log_parsing_event_fn,
    add_issue_fn,
    force_overwrite: bool = False,
):
    log = []
    parsed_pdfs = []
    txt_files = []
    seen_identity_hashes = {}

    def _pdf_report_meta(record: dict, unit_code: str, report_type: str) -> dict:
        if report_type == "daily":
            report_start = f"{record.get('date_from', '')} 00:00:00" if record.get("date_from") else ""
            report_end = f"{record.get('date_to', '')} 00:00:00" if record.get("date_to") else ""
        else:
            report_start = str(record.get("dt_from") or "").strip()
            report_end = str(record.get("dt_to") or "").strip()
            if report_start and len(report_start) == 16:
                report_start = f"{report_start}:00"
            if report_end and len(report_end) == 16:
                report_end = f"{report_end}:00"
        content_date = str(record.get("date_from") or "").strip()
        identity_key = build_measurement_identity("pdf", unit_code, report_type, report_start, report_end)
        return {
            "content_date": content_date,
            "report_start": report_start,
            "report_end": report_end,
            "identity_key": identity_key,
            "time_source": "content" if report_start else "filename_fallback",
        }

    for path, name in paths_names:
        info = classify_input(path, name)
        try:
            file_hash = _sha1_file(Path(path))
        except Exception:
            file_hash = ""
        ext = info["ext"]
        file_type = info["file_type"]
        unit = info["unit"]
        meter_id = info.get("meter_id", "")
        location = info.get("location", "")
        content_date = info.get("content_date", "")

        if ext == "txt":
            rule_errors = validate_txt_import_rule(info)
            if rule_errors:
                raw_file_id = log_raw_file_fn(run_id, Path(path), source_type, info)
                message = " | ".join(rule_errors)
                log_file_fn(
                    run_id,
                    name,
                    ext,
                    file_type,
                    unit or "",
                    meter_id,
                    location,
                    content_date,
                    info.get("report_start", ""),
                    info.get("report_end", ""),
                    content_date[:7],
                    info.get("identity_key", ""),
                    info.get("time_source", ""),
                    file_hash or "",
                    False,
                    message,
                )
                log_parsing_event_fn(
                    run_id,
                    raw_file_id,
                    "classify_input",
                    "validate_txt_rules",
                    "error",
                    {"errors": rule_errors, "meter_id": meter_id, "content_date": content_date, "filename": name},
                )
                add_issue_fn(run_id, "", "txt_rule_validation_failed", "error", name, content_date, message)
                log.append(f"❌ {name}  →  regra TXT inválida: {message}")
                continue
            identity_key = info.get("identity_key", "") or ""
            if identity_key and seen_identity_hashes.get(identity_key) == file_hash:
                log_file_fn(
                    run_id,
                    name,
                    ext,
                    file_type,
                    unit or "",
                    meter_id,
                    location,
                    content_date,
                    info.get("report_start", ""),
                    info.get("report_end", ""),
                    content_date[:7],
                    identity_key,
                    info.get("time_source", ""),
                    file_hash or "",
                    True,
                    "Conteudo identico ja incluido neste lote - ignorado",
                )
                log.append(f"ℹ️  {name}  →  TXT identico no mesmo lote - ignorado")
                continue
            raw_file_id = log_raw_file_fn(run_id, Path(path), source_type, info)
            existing = find_existing_import_by_identity_fn(identity_key) if identity_key else None
            if not force_overwrite and existing and (existing.get("file_hash") or "") == (file_hash or ""):
                log_file_fn(
                    run_id,
                    name,
                    ext,
                    file_type,
                    unit or "",
                    meter_id,
                    location,
                    content_date,
                    info.get("report_start", ""),
                    info.get("report_end", ""),
                    content_date[:7],
                    identity_key,
                    info.get("time_source", ""),
                    file_hash or "",
                    True,
                    "Conteudo identico ja importado anteriormente - ignorado",
                )
                log_parsing_event_fn(run_id, raw_file_id, "classify_input", "classify_txt", "ignored", info)
                log.append(f"ℹ️  {name}  →  TXT identico ja importado - ignorado")
                continue
            if identity_key:
                seen_identity_hashes[identity_key] = file_hash or ""
            overwrite_existing = bool(existing and ((existing.get("file_hash") or "") != (file_hash or "") or force_overwrite))
            info["_overwrite_existing"] = overwrite_existing
            info["_previous_import_id"] = existing.get("id") if existing else None
            txt_files.append((path, name, file_type, unit, meter_id, location, content_date, file_hash, dict(info)))
            log_parsing_event_fn(run_id, raw_file_id, "classify_input", "classify_txt", "ok", info)
            if overwrite_existing:
                log.append(f'♻️  {name}  →  {file_type} [{unit or "UNK"}] {meter_id or ""} sobrescreve janela existente')
            else:
                log.append(f'📄 {name}  →  {file_type} [{unit or "UNK"}] {meter_id or ""}')
            continue

        if ext == "pdf":
            report_type = file_type if file_type in ("daily", "hourly") else "daily"
            if not force_overwrite and file_hash:
                existing_by_hash = find_existing_import_by_hash_fn(file_hash)
                if existing_by_hash:
                    raw_file_id = log_raw_file_fn(run_id, Path(path), source_type, info)
                    log_file_fn(
                        run_id,
                        name,
                        ext,
                        report_type,
                        unit or existing_by_hash.get("unit_code") or "",
                        meter_id,
                        location,
                        content_date or existing_by_hash.get("content_date") or "",
                        info.get("report_start", "") or existing_by_hash.get("report_start", ""),
                        info.get("report_end", "") or existing_by_hash.get("report_end", ""),
                        (content_date or existing_by_hash.get("content_date") or "")[:7],
                        existing_by_hash.get("identity_key", ""),
                        existing_by_hash.get("time_source", ""),
                        file_hash,
                        True,
                        "Conteudo identico ja importado anteriormente - ignorado antes do parse",
                    )
                    log_parsing_event_fn(
                        run_id,
                        raw_file_id,
                        "mpfm_engine.parse_pdf",
                        "pre_parse_hash_check",
                        "ignored",
                        {
                            "matched_import_id": existing_by_hash.get("id"),
                            "matched_filename": existing_by_hash.get("filename", ""),
                            "file_hash": file_hash,
                        },
                    )
                    log.append(f"ℹ️  {name}  →  PDF identico ja importado - parse ignorado")
                    continue
            try:
                record = parse_pdf_fn(str(path), report_type)
                unit_code = resolve_bank_from_record(record, unit)
                meta = _pdf_report_meta(record, unit_code, report_type)
                date_from = meta["content_date"] or "0000-00-00"
                record["unit_code"] = unit_code
                record["_report_start"] = meta["report_start"]
                record["_report_end"] = meta["report_end"]
                record["_identity_key"] = meta["identity_key"]
                record["_time_source"] = meta["time_source"]
                rule_errors = validate_pdf_import_rule(record, unit_code, report_type, meta)
                if rule_errors:
                    raw_file_id = log_raw_file_fn(
                        run_id,
                        Path(path),
                        source_type,
                        {
                            "ext": ext,
                            "file_type": report_type,
                            "unit": unit_code,
                            "meter_id": "",
                            "location": "",
                            "content_date": date_from,
                            "report_start": meta["report_start"],
                            "report_end": meta["report_end"],
                            "identity_key": meta["identity_key"],
                            "time_source": meta["time_source"],
                        },
                    )
                    message = " | ".join(rule_errors)
                    log_file_fn(
                        run_id,
                        name,
                        ext,
                        report_type,
                        unit_code,
                        "",
                        "",
                        date_from,
                        meta["report_start"],
                        meta["report_end"],
                        date_from[:7],
                        meta["identity_key"],
                        meta["time_source"],
                        file_hash,
                        False,
                        message,
                    )
                    log_parsing_event_fn(
                        run_id,
                        raw_file_id,
                        "mpfm_engine.parse_pdf",
                        "validate_pdf_rules",
                        "error",
                        {"errors": rule_errors, "report_type": report_type, "content_date": date_from, "filename": name},
                    )
                    add_issue_fn(run_id, "", "pdf_rule_validation_failed", "error", name, date_from, message)
                    log.append(f"❌ {name}  →  regra PDF inválida: {message}")
                    continue
                if meta["identity_key"] and seen_identity_hashes.get(meta["identity_key"]) == file_hash:
                    log_file_fn(
                        run_id,
                        name,
                        ext,
                        report_type,
                        unit_code,
                        "",
                        "",
                        date_from,
                        meta["report_start"],
                        meta["report_end"],
                        date_from[:7],
                        meta["identity_key"],
                        meta["time_source"],
                        file_hash,
                        True,
                        "Conteudo identico ja incluido neste lote - ignorado",
                    )
                    log.append(f"ℹ️  {name}  →  PDF identico no mesmo lote - ignorado")
                    continue
                raw_file_id = log_raw_file_fn(
                    run_id,
                    Path(path),
                    source_type,
                    {
                        "ext": ext,
                        "file_type": report_type,
                        "unit": unit_code,
                        "meter_id": "",
                        "location": "",
                        "content_date": date_from,
                        "report_start": meta["report_start"],
                        "report_end": meta["report_end"],
                        "identity_key": meta["identity_key"],
                        "time_source": meta["time_source"],
                    },
                )
                existing = find_existing_import_by_identity_fn(meta["identity_key"]) if meta["identity_key"] else None
                if not force_overwrite and existing and (existing.get("file_hash") or "") == (file_hash or ""):
                    log_file_fn(
                        run_id,
                        name,
                        ext,
                        report_type,
                        unit_code,
                        "",
                        "",
                        date_from,
                        meta["report_start"],
                        meta["report_end"],
                        date_from[:7],
                        meta["identity_key"],
                        meta["time_source"],
                        file_hash,
                        True,
                        "Conteudo identico ja importado anteriormente - ignorado",
                    )
                    log_parsing_event_fn(
                        run_id,
                        raw_file_id,
                        "mpfm_engine.parse_pdf",
                        "parse_pdf",
                        "ignored",
                        {"report_type": report_type, "content_date": date_from, "identity_key": meta["identity_key"]},
                    )
                    log.append(f"ℹ️  {name}  →  PDF identico ja importado - ignorado")
                    continue
                if meta["identity_key"]:
                    seen_identity_hashes[meta["identity_key"]] = file_hash or ""
                overwrite_existing = bool(existing and ((existing.get("file_hash") or "") != (file_hash or "") or force_overwrite))
                record["_overwrite_existing"] = overwrite_existing
                record["_previous_import_id"] = existing.get("id") if existing else None
                parsed_pdfs.append((record, unit_code, report_type, name, date_from))
                log_file_fn(
                    run_id,
                    name,
                    ext,
                    report_type,
                    unit_code,
                    "",
                    "",
                    date_from,
                    meta["report_start"],
                    meta["report_end"],
                    date_from[:7],
                    meta["identity_key"],
                    meta["time_source"],
                    file_hash,
                    True,
                    "Sobrescreve import anterior da mesma janela de medicao" if overwrite_existing else "",
                )
                log_parsing_event_fn(
                    run_id,
                    raw_file_id,
                    "mpfm_engine.parse_pdf",
                    "parse_pdf",
                    "ok",
                    {"report_type": report_type, "content_date": date_from, "unit_code": unit_code},
                )
                tags = list((record.get("tags") or {}).keys())
                if report_type == "daily":
                    cadastro = build_cadastro_index_fn()
                    expected = cadastro["expected_tags"].get(unit_code, set())
                    normalized_tags = {_normalize_tag_name(tag) for tag in tags if _normalize_tag_name(tag)}
                    unknown = [tag for tag in sorted(normalized_tags - expected) if tag]
                    missing = [tag for tag in sorted(expected - normalized_tags) if tag]
                    note = ""
                    if unknown:
                        note += f" ⚠️ TAG desconhecido: {unknown}"
                    if missing:
                        note += f" ℹ️ TAG faltando: {missing}"
                    if not unknown and not missing and expected:
                        note = " ✅ cadastro OK"
                    prefix = "♻️" if overwrite_existing else "📊"
                    log.append(f"{prefix} {name}  →  DAILY [{date_from}] TAGs:{tags}{note}")
                else:
                    prefix = "♻️" if overwrite_existing else "🕐"
                    log.append(f'{prefix} {name}  →  HOURLY [{date_from}] h{record.get("hour", "?")}')
            except Exception as exc:
                raw_file_id = log_raw_file_fn(run_id, Path(path), source_type, info)
                log_file_fn(
                    run_id,
                    name,
                    ext,
                    report_type,
                    unit or "",
                    "",
                    "",
                    content_date,
                    info.get("report_start", ""),
                    info.get("report_end", ""),
                    "",
                    info.get("identity_key", ""),
                    info.get("time_source", ""),
                    file_hash,
                    False,
                    str(exc),
                )
                log_parsing_event_fn(
                    run_id,
                    raw_file_id,
                    "mpfm_engine.parse_pdf",
                    "parse_pdf",
                    "error",
                    {"report_type": report_type, "content_date": content_date, "error": str(exc)},
                )
                log.append(f"❌ Erro ao ler {name}: {exc}")

    by_month = defaultdict(
        lambda: {
            "daily": {},
            "hourly": defaultdict(dict),
            # TXT SEP precisa ser agrupado por unidade + dia operacional real.
            # Agrupar só por unidade no mês mistura trios de dias diferentes.
            "txts": defaultdict(lambda: defaultdict(list)),
        }
    )

    for record, unit, report_type, name, date_from in parsed_pdfs:
        year, month = date_from[:4], date_from[5:7]
        day_tag = date_from[8:10] + "_" + date_from[5:7]
        key = f"{unit}_{day_tag}"
        if report_type == "daily":
            by_month[(year, month)]["daily"][key] = (record, unit)
        else:
            identity_key = record.get("_identity_key") or f"{record.get('dt_from') or ''}|{record.get('hour')}"
            by_month[(year, month)]["hourly"][key][identity_key] = record

    for path, name, file_type, unit, meter_id, location, content_date, file_hash, info in txt_files:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", str(content_date or "")):
            year, month = content_date[:4], content_date[5:7]
        else:
            month_match = re.search(r"(\d{4})(\d{2})\d{2}", name)
            year = month = ""
            if month_match:
                year, month = month_match.group(1), month_match.group(2)
        if year and month:
            day_bucket = str(content_date or info.get("report_start", "")[:10] or "").strip()
            group_key = (unit or "UNK", day_bucket)
            by_month[(year, month)]["txts"][group_key][file_type].append(
                {"path": str(path), "name": name}
            )
            log_file_fn(
                run_id,
                name,
                "txt",
                file_type,
                unit or "",
                meter_id,
                location,
                content_date,
                info.get("report_start", ""),
                info.get("report_end", ""),
                f"{year}-{month}",
                info.get("identity_key", ""),
                info.get("time_source", ""),
                file_hash or "",
                True,
                "Sobrescreve import anterior da mesma janela de medicao" if info.get("_overwrite_existing") else "",
            )
            continue
        elif len(by_month) == 1:
            year, month = list(by_month.keys())[0]
            day_bucket = str(content_date or info.get("report_start", "")[:10] or "").strip()
            group_key = (unit or "UNK", day_bucket)
            by_month[(year, month)]["txts"][group_key][file_type].append(
                {"path": str(path), "name": name}
            )
            log_file_fn(
                run_id,
                name,
                "txt",
                file_type,
                unit or "",
                meter_id,
                location,
                content_date,
                info.get("report_start", ""),
                info.get("report_end", ""),
                f"{year}-{month}",
                info.get("identity_key", ""),
                info.get("time_source", ""),
                file_hash or "",
                True,
                "Sobrescreve import anterior da mesma janela de medicao" if info.get("_overwrite_existing") else "",
            )
            continue
        add_issue_fn(run_id, "", "txt_month_not_detected", "warn", name, "", "Mês não detectado no TXT")
        log_file_fn(
            run_id,
            name,
            "txt",
            file_type,
            unit or "",
            meter_id,
            location,
            content_date,
            info.get("report_start", ""),
            info.get("report_end", ""),
            "",
            info.get("identity_key", ""),
            info.get("time_source", ""),
            file_hash or "",
            False,
            "Mês não detectado no TXT",
        )
        log.append(f"⚠️  Mês não detectado em TXT: {name} — ignorado")

    for month_bucket in by_month.values():
        for key, records_by_identity in list(month_bucket["hourly"].items()):
            month_bucket["hourly"][key] = list(records_by_identity.values())

    return {
        "log": log,
        "parsed_pdfs": parsed_pdfs,
        "txt_files": txt_files,
        "by_month": by_month,
        "months_found": sorted(by_month.keys()),
    }
