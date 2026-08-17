from __future__ import annotations

import time


def process_monthly_mpfm_inputs(
    data,
    *,
    run_id: int,
    excel_file: str,
    year: str,
    month: str,
    state: dict,
    engine,
    dataframe_to_records_fn,
    day_tag_to_iso_fn,
    get_sep_alignment_fn,
    deserialize_sep_fn,
    load_sep_data_by_day_fn,
    has_sep_alignment_fn,
    validate_with_cadastro_fn,
    add_issue_fn,
    logger,
):
    area_rows = []
    sheet_records_for_db = []

    all_keys = sorted(set(list(data["daily"]) + list(data["hourly"])))
    print(f"[diag] process_monthly_mpfm_inputs: {len(all_keys)} dia(s) a processar", flush=True)
    for _key_idx, key in enumerate(all_keys, 1):
        _key_t0 = time.monotonic()
        daily_rec, unit_code = data["daily"].get(key, (None, key.split("_")[0]))
        hourly_recs_all = list(data["hourly"].get(key, []))
        day_tag_check = "_".join(key.split("_")[1:])
        already_hours = set(state.get("processed_hours_by_key", {}).get(key, []))
        hourly_recs = [record for record in hourly_recs_all if record.get("hour") not in already_hours]
        hourly_recs.sort(key=lambda record: record.get("hour") if record.get("hour") is not None else 0)
        has_new_daily = daily_rec is not None and key not in state.get("processed", [])
        has_new_hourly = len(hourly_recs) > 0

        if not has_new_daily and not has_new_hourly:
            skipped = len(hourly_recs_all)
            if skipped:
                logger(f"  ⏭️  {key}: {skipped}h já registradas — ignoradas")
            else:
                logger(f"  ⏭️  {key}: já processado — sem dados novos")
            continue
        if len(hourly_recs_all) > len(hourly_recs):
            duplicated = len(hourly_recs_all) - len(hourly_recs)
            add_issue_fn(run_id, excel_file, "duplicate_hourly", "info", key, day_tag_check, f"{duplicated} hora(s) duplicadas ignoradas")
            logger(f"  ℹ️  {key}: {duplicated}h duplicadas ignoradas, {len(hourly_recs)}h novas")

        day_tag = "_".join(key.split("_")[1:])
        production_date = day_tag_to_iso_fn(year, month, day_tag)
        alignment = get_sep_alignment_fn(unit_code, production_date)
        sep_data = {}
        if alignment:
            sep_data = deserialize_sep_fn(state.get("sep_by_day", {}).get(production_date)) or load_sep_data_by_day_fn(production_date)
        logger(f'  📦 {unit_code} {day_tag}  {len(hourly_recs)}h  sep:{"✔" if sep_data else "–"}{" alinhado" if alignment else ""}')

        persisted_hours = []
        if hourly_recs:
            sheet_name = f"HOURLY_{unit_code}_{day_tag}"
            df_hourly = engine.build_hourly_df_with_sep(hourly_recs, unit_code, sep_data)
            if not df_hourly.empty:
                hourly_rows = dataframe_to_records_fn(df_hourly)
                if hourly_rows:
                    sheet_records_for_db.append((sheet_name, hourly_rows))
                    persisted_hours = [record.get("hour") for record in hourly_recs if record.get("hour") is not None]
            else:
                add_issue_fn(
                    run_id,
                    excel_file,
                    "empty_hourly_df",
                    "warn",
                    key,
                    day_tag,
                    "Registros hourly parseados nao geraram linhas para persistencia.",
                )
                logger(f"  ⚠️  {key}: hourly parseado sem linhas persistiveis")

        if daily_rec:
            daily_sheet = f"DAILY_{unit_code}_{day_tag}"
            recon_sheet = f"RECON_{unit_code}_{day_tag}"
            df_daily = engine.build_daily_df(daily_rec, unit_code)
            df_recon = engine.build_recon_df(daily_rec, hourly_recs_all, unit_code)
            daily_records = dataframe_to_records_fn(df_daily)
            recon_records = dataframe_to_records_fn(df_recon)
            sheet_records_for_db.append((daily_sheet, daily_records))
            sheet_records_for_db.append((recon_sheet, recon_records))
            area_total = engine.build_area_totals_row(daily_rec, unit_code)
            if area_total:
                area_rows.append(area_total)

            rec_hours = sorted(set(record.get("hour") for record in hourly_recs_all if record.get("hour") is not None))
            missing_hours = sorted(set(range(24)) - set(rec_hours))
            if missing_hours:
                details = "Horas faltando: " + ", ".join(f"{hour:02d}" for hour in missing_hours)
                add_issue_fn(run_id, excel_file, "missing_hours", "warn", key, day_tag, details)
                logger(f"  ⚠️  {key}: {details}")
            if has_sep_alignment_fn(unit_code, production_date) and not sep_data:
                add_issue_fn(
                    run_id,
                    excel_file,
                    "missing_sep",
                    "warn",
                    key,
                    day_tag,
                    f"Banco {unit_code} possui alinhamento de separador para {production_date}, mas não há dados extraídos do SEP para este dia.",
                )
                logger(f"  ⚠️  {key}: alinhamento SEP definido, mas dados do separador ausentes em {production_date}")

            daily_tags = list((daily_rec.get("tags") or {}).keys()) if daily_rec else []
            validate_with_cadastro_fn(run_id, excel_file, unit_code, daily_tags, day_tag.replace("_", "-", 1))
            for recon_row in recon_records:
                coverage = recon_row.get("Cobertura", "")
                if isinstance(coverage, str) and "PARCIAL" in coverage:
                    add_issue_fn(run_id, excel_file, "recon_partial", "warn", key, day_tag, coverage)
                for status_column in ["Status Gás", "Status Óleo", "Status HC", "Status Água"]:
                    if recon_row.get(status_column) == "VERIFICAR":
                        add_issue_fn(run_id, excel_file, "recon_verify", "warn", key, day_tag, f"{status_column} = VERIFICAR")

        if key not in state["processed"] and daily_rec is not None:
            state["processed"].append(key)
        if persisted_hours:
            existing = state.setdefault("processed_hours_by_key", {}).get(key, [])
            state["processed_hours_by_key"][key] = sorted(set(existing + persisted_hours))
            day_existing = state.setdefault("processed_hours", {}).get(day_tag, [])
            state["processed_hours"][day_tag] = sorted(set(day_existing + persisted_hours))

        print(f"[diag] ({_key_idx}/{len(all_keys)}) {key}: {time.monotonic()-_key_t0:.2f}s", flush=True)

    return {
        "area_rows": area_rows,
        "sheet_records_for_db": sheet_records_for_db,
        "state": state,
    }
