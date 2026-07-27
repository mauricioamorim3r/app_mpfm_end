from __future__ import annotations

import os
import re
from pathlib import Path


def process_monthly_sep_inputs(
    txt_groups,
    *,
    run_id: int,
    excel_file: str,
    year: str,
    month: str,
    density: float,
    state: dict,
    engine,
    inspect_txt_content_fn,
    register_sep_source_file_fn,
    store_sep_fluid_detail_fn,
    store_sep_measurements_fn,
    add_issue_fn,
    ser_fn,
    logger,
):
    inspect_cache = {}

    def inspect_file(file_path):
        path_str = str(Path(file_path))
        if path_str not in inspect_cache:
            inspect_cache[path_str] = inspect_txt_content_fn(Path(file_path))
        return inspect_cache[path_str]

    for unit_group, group in txt_groups.items():
        if isinstance(unit_group, tuple):
            unit, seeded_day = unit_group
        else:
            unit, seeded_day = unit_group, ""
        sep_date = None
        official_paths = {}
        try:
            for fluid_type in ("sep_oleo", "sep_gas", "sep_agua"):
                for entry in list(group.get(fluid_type, [])):
                    file_path = entry.get("path")
                    info = inspect_file(file_path)
                    day_ref = info.get("content_date", "") or seeded_day or sep_date
                    if day_ref and not sep_date:
                        sep_date = day_ref
                    source_id, is_official, _chosen, _action = register_sep_source_file_fn(
                        file_path,
                        fluid_type,
                        info.get("meter_id", "") or "",
                        info.get("location", "") or "",
                        day_ref or "",
                        info.get("report_start", "") or "",
                        info.get("report_end", "") or "",
                        info.get("identity_key", "") or "",
                        info.get("time_source", "content") or "content",
                    )
                    if _action == "same_content":
                        logger(f"  ℹ️  SEP {unit}/{fluid_type}: conteudo identico ja importado - ignorado")
                        continue
                    store_sep_fluid_detail_fn(
                        run_id,
                        excel_file,
                        fluid_type,
                        file_path,
                        actual_day=day_ref,
                        source_record_id=source_id,
                        is_official=is_official,
                    )
                    if is_official:
                        official_paths[fluid_type] = file_path
                if len(group.get(fluid_type, [])) > 1:
                    add_issue_fn(
                        run_id,
                        excel_file,
                        "sep_duplicate_candidate",
                        "info",
                        f"{unit}/{fluid_type}",
                        sep_date or "",
                        f"{len(group.get(fluid_type, []))} arquivos candidatos para {fluid_type}. Um ficou oficial e os demais pendentes para rastreabilidade.",
                    )
        except Exception as exc:
            add_issue_fn(run_id, excel_file, "sep_detail_parse_error", "warn", unit, sep_date or "", str(exc))
            logger(f"  ⚠️  Detalhe SEP {unit}: {exc}")

        if all(key in official_paths for key in ("sep_oleo", "sep_gas", "sep_agua")):
            try:
                oil_path = official_paths["sep_oleo"]
                gas_path = official_paths["sep_gas"]
                water_path = official_paths["sep_agua"]
                sep_trace_events = []

                def _trace_sep_parser(event):
                    sep_trace_events.append(dict(event or {}))

                sep = engine.parse_sep_txt_set(
                    oil_path,
                    gas_path,
                    water_path,
                    density,
                    trace_hook=_trace_sep_parser,
                )
                logger(f'  ✅ Separador extraído: {len([k for k in sep if k != "DAY"])}h')
                if not sep_date:
                    sep_date = inspect_file(oil_path).get("content_date", "") or seeded_day or ""
                for event in sep_trace_events:
                    trace_path = event.get("file_path") or ""
                    trace_file = os.path.basename(trace_path) if trace_path else "arquivo_desconhecido"
                    trace_row = event.get("row_key") or "?"
                    trace_field = event.get("field_name") or "campo_desconhecido"
                    raw_token = event.get("raw_token") or ""
                    recovered_token = event.get("recovered_token") or ""
                    overflow_token = event.get("overflow_token") or ""
                    message = (
                        f"Parser SEP recuperou token numerico concatenado em {trace_file} "
                        f"(linha {trace_row}, campo {trace_field}): bruto='{raw_token}', "
                        f"usado='{recovered_token}', excedente='{overflow_token}'. "
                        f"Verificar a origem do TXT para evitar reincidencia."
                    )
                    add_issue_fn(run_id, excel_file, "sep_parser_recovered_token", "warn", unit, sep_date or "", message)
                    logger(f"  ⚠️  SEP {unit}: {message}")
                if sep_date:
                    state.setdefault("sep_by_day", {})[sep_date] = ser_fn(sep)
                    if sep_date not in state.get("sep_days", []):
                        state.setdefault("sep_days", []).append(sep_date)
                oil_info = inspect_file(oil_path)
                source_id, _is_official, _chosen, _action = register_sep_source_file_fn(
                    oil_path,
                    "sep_oleo",
                    oil_info.get("meter_id", "") or "",
                    oil_info.get("location", "") or "",
                    sep_date or "",
                    oil_info.get("report_start", "") or "",
                    oil_info.get("report_end", "") or "",
                    oil_info.get("identity_key", "") or "",
                    oil_info.get("time_source", "content") or "content",
                )
                store_sep_measurements_fn(
                    run_id,
                    excel_file,
                    unit,
                    sep,
                    year,
                    month,
                    actual_day=sep_date,
                    source_file=os.path.basename(str(oil_path or "")),
                    source_record_id=source_id,
                    is_official=True,
                )
            except Exception as exc:
                add_issue_fn(run_id, excel_file, "sep_parse_error", "error", unit, "", str(exc))
                logger(f"  ❌ Erro no Separador {unit}: {exc}")
        else:
            missing = [key for key in ("sep_oleo", "sep_gas", "sep_agua") if key not in official_paths]
            add_issue_fn(run_id, excel_file, "sep_missing_files", "warn", unit, "", "Faltam TXTs oficiais: " + ", ".join(missing))
            logger(f'  ⚠️  {unit}: faltam TXTs oficiais: {", ".join(missing)}')
