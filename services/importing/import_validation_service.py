from __future__ import annotations

import re
from datetime import datetime

_SEP_CANONICAL_TAG_BY_PHASE: dict[str, str] = {
    "sep_oleo": "20FT0247",
    "sep_agua": "20FT0251",
    "sep_gas":  "20FT0244",
}


def _parse_iso_date(value: str):
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None


def _parse_iso_datetime(value: str):
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?", raw):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def validate_pdf_import_rule(record: dict, unit_code: str, report_type: str, meta: dict | None = None) -> list[str]:
    errors: list[str] = []
    meta = meta or {}
    tags = record.get("tags") or {}
    if not str(unit_code or "").strip():
        errors.append("Banco/unidade do PDF não identificado.")
    if not isinstance(tags, dict) or not tags:
        errors.append("PDF sem TAGs de medição reconhecidas.")

    date_from = str(record.get("date_from") or "").strip()
    if not _parse_iso_date(date_from):
        errors.append("Data inicial da medição não encontrada no conteúdo do PDF.")

    identity_key = str(meta.get("identity_key") or record.get("_identity_key") or "").strip()
    if not identity_key:
        errors.append("Chave de identidade da medição não foi gerada.")

    if report_type == "daily":
        date_to = str(record.get("date_to") or "").strip()
        dt_start = _parse_iso_datetime(str(meta.get("report_start") or "").strip())
        dt_end = _parse_iso_datetime(str(meta.get("report_end") or "").strip())
        parsed_date_from = _parse_iso_date(date_from)
        parsed_date_to = _parse_iso_date(date_to)
        if not parsed_date_to:
            errors.append("Data final da janela diária não encontrada no conteúdo do PDF.")
        elif parsed_date_from and parsed_date_to <= parsed_date_from:
            errors.append("Janela diária inválida: término menor ou igual ao início.")
        if dt_start and dt_end:
            if int((dt_end - dt_start).total_seconds()) != 86400:
                errors.append("Janela diária inválida: o PDF deveria cobrir 24 horas.")
            if parsed_date_from and dt_start.date() != parsed_date_from.date():
                errors.append("Data operacional do PDF diário diverge do início da janela interna.")
        if record.get("hour") is not None:
            errors.append("PDF diário não deveria carregar hora operacional.")
    else:
        dt_from = _parse_iso_datetime(str(record.get("dt_from") or "").strip())
        dt_to = _parse_iso_datetime(str(record.get("dt_to") or "").strip())
        if not dt_from or not dt_to:
            errors.append("Janela horária não encontrada no conteúdo do PDF.")
        else:
            if dt_to <= dt_from:
                errors.append("Janela horária inválida: término menor ou igual ao início.")
            elif int((dt_to - dt_from).total_seconds()) != 3600:
                errors.append("Janela horária inválida: o PDF deveria cobrir 1 hora.")
            if date_from and dt_from.strftime("%Y-%m-%d") != date_from:
                errors.append("Dia operacional do PDF horário diverge do início da janela interna.")
            expected_hour = dt_from.hour
            actual_hour = record.get("hour")
            if actual_hour is None:
                errors.append("Hora operacional do PDF horário não foi identificada.")
            elif int(actual_hour) != int(expected_hour):
                errors.append(
                    f"Hora operacional inválida: esperado h{expected_hour:02d}, recebido h{int(actual_hour):02d}."
                )

    return errors


def validate_txt_import_rule(info: dict) -> list[str]:
    errors: list[str] = []
    meter_id = str(info.get("meter_id") or "").strip()
    content_date = str(info.get("content_date") or "").strip()
    report_start = str(info.get("report_start") or "").strip()
    report_end = str(info.get("report_end") or "").strip()
    identity_key = str(info.get("identity_key") or "").strip()
    file_type = str(info.get("file_type") or "").strip()

    if not meter_id:
        errors.append("Meter ID do TXT não identificado no conteúdo.")
    if file_type not in {"sep_oleo", "sep_agua", "sep_gas"}:
        errors.append("Tipo do TXT não reconhecido para o separador de teste.")
    if meter_id and file_type in _SEP_CANONICAL_TAG_BY_PHASE:
        canonical = _SEP_CANONICAL_TAG_BY_PHASE[file_type]
        if meter_id != canonical:
            errors.append(
                f"Tag '{meter_id}' não está no escopo da aplicação para a fase '{file_type}' "
                f"(ponto de medição esperado: '{canonical}'). "
                "Arquivo não pode ser carregado."
            )
    if not _parse_iso_date(content_date):
        errors.append("Dia operacional do TXT não identificado a partir do Start/Period start.")
    if not identity_key:
        errors.append("Chave de identidade da medição TXT não foi gerada.")

    dt_start = _parse_iso_datetime(report_start)
    dt_end = _parse_iso_datetime(report_end)
    if not dt_start or not dt_end:
        errors.append("Janela de medição do TXT não foi identificada completamente.")
    else:
        if dt_end <= dt_start:
            errors.append("Janela do TXT inválida: término menor ou igual ao início.")
        elif int((dt_end - dt_start).total_seconds()) != 86400:
            errors.append("Janela do TXT inválida: o arquivo deveria cobrir 24 horas.")
        if content_date and dt_start.strftime("%Y-%m-%d") != content_date:
            errors.append("Dia operacional do TXT diverge do campo Start/Period start.")

    return errors
