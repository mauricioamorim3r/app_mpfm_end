from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import json

from routes.date_utils import normalize_date_input, normalize_validation_issue_day_ref


DEFAULT_MONTHLY_REPORT_GROUPS = [
    {
        "key": "PE4_RISERP5",
        "title": "PE-04 × Riser P5",
        "subsea_bank": "B05",
        "subsea_tag": "PE_4",
        "topside_bank": "B03",
        "topside_tag": "Riser_P5",
    },
    {
        "key": "PE2_RISERP2",
        "title": "PE-02 × Riser P2",
        "subsea_bank": "B10",
        "subsea_tag": "PE_2",
        "topside_bank": "B08",
        "topside_tag": "Riser_P2",
    },
    {
        "key": "PW104_RISERP4",
        "title": "PW-104DA × Riser P4",
        "subsea_bank": "B15",
        "subsea_tag": "PW-104DA",
        "topside_bank": "B13",
        "topside_tag": "Riser_P4",
    },
]

_GROUP_INDEX = {item["key"]: item for item in DEFAULT_MONTHLY_REPORT_GROUPS}
_DAILY_METRICS = {
    "oil_t": "MPFM corr Óleo (t)",
    "gas_t": "MPFM corr Gás (t)",
    "water_t": "MPFM corr Água (t)",
    "hc_t": "MPFM corr HC (t)",
    "total_t": "MPFM corr Total (t)",
    "oil_sm3": "PVT vol Óleo (m³)",
    "gas_sm3": "PVT vol Gás (Sm³)",
    "water_sm3": "PVT vol Água (m³)",
}
_SEP_METRICS = {
    "oil_t": "SEP Óleo (t) CV",
    "gas_t": "SEP Gás (t) CV",
    "water_t": "SEP Água (t) CV",
    "hc_t": "SEP HC (t)",
    "total_t": "SEP Total (t)",
}


def _month_range(month: str) -> tuple[str, str]:
    raw = str(month or "").strip()
    if len(raw) != 7 or raw[4] != "-":
        raise ValueError("Mês inválido. Use YYYY-MM.")
    year = int(raw[:4])
    month_num = int(raw[5:7])
    start = date(year, month_num, 1)
    end = date(year + (1 if month_num == 12 else 0), 1 if month_num == 12 else month_num + 1, 1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _iter_days(date_from: str, date_to: str) -> list[str]:
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _norm(normalize_tag_name, value: str) -> str:
    return normalize_tag_name(value or "") if normalize_tag_name else str(value or "").strip().upper()


def _month_label(month: str, month_pt: dict | None = None) -> str:
    label_map = month_pt or {}
    year, mo = month.split("-")
    return f"{label_map.get(mo, mo)}/{year}"


def _source_label(item: dict) -> str:
    return "Gerado na aplicação" if item.get("source") == "generated" else "Importado"


def _empty_to_none(value):
    return value if value not in ("", None) else None


def _pick_primary(subsea: dict, topside: dict, metric_key: str):
    subsea_value = subsea.get(metric_key)
    if subsea_value is not None:
        return subsea_value
    return topside.get(metric_key)


def _resolve_groups(mode: str, group_key: str, custom: dict) -> list[dict]:
    if mode != "custom":
        return [dict(item) for item in DEFAULT_MONTHLY_REPORT_GROUPS]
    if group_key and group_key in _GROUP_INDEX:
        return [dict(_GROUP_INDEX[group_key])]
    title = str(custom.get("title") or "").strip() or "Grupo customizado"
    subsea_bank = str(custom.get("subsea_bank") or "").strip().upper()
    subsea_tag = str(custom.get("subsea_tag") or "").strip()
    topside_bank = str(custom.get("topside_bank") or "").strip().upper()
    topside_tag = str(custom.get("topside_tag") or "").strip()
    if not all([subsea_bank, subsea_tag, topside_bank, topside_tag]):
        raise ValueError("No modo customizado, escolha um grupo padrão ou preencha banco/TAG subsea e topside.")
    return [
        {
            "key": "CUSTOM",
            "title": title,
            "subsea_bank": subsea_bank,
            "subsea_tag": subsea_tag,
            "topside_bank": topside_bank,
            "topside_tag": topside_tag,
        }
    ]


def _build_daily_maps(cur, date_from: str, date_to: str, normalize_tag_name):
    rows = [
        dict(row)
        for row in cur.execute(
            """
            SELECT day_ref, bank, tag, instrument, tipo, metric_name, metric_value
            FROM measurements_active
            WHERE day_ref BETWEEN ? AND ?
              AND row_kind='daily'
              AND COALESCE(is_official,1)=1
            ORDER BY day_ref, bank, tag, metric_name
            """,
            (date_from, date_to),
        ).fetchall()
    ]
    by_point: dict[tuple[str, str, str], dict] = {}
    field_balance = defaultdict(lambda: {"hc_t": 0.0, "total_t": 0.0})
    for row in rows:
        bank = str(row.get("bank") or "").strip().upper()
        if not bank or bank == "SEP":
            continue
        tag = str(row.get("tag") or "").strip()
        key = (str(row.get("day_ref") or ""), bank, _norm(normalize_tag_name, tag))
        entry = by_point.setdefault(
            key,
            {
                "day_ref": row.get("day_ref") or "",
                "bank": bank,
                "tag": tag,
                "instrument": row.get("instrument") or "",
                "tipo": row.get("tipo") or "",
            },
        )
        metric_name = str(row.get("metric_name") or "")
        metric_value = row.get("metric_value")
        for item_key, expected_metric in _DAILY_METRICS.items():
            if metric_name == expected_metric:
                entry[item_key] = metric_value
                if item_key == "hc_t":
                    field_balance[entry["day_ref"]]["hc_t"] += float(metric_value or 0)
                if item_key == "total_t":
                    field_balance[entry["day_ref"]]["total_t"] += float(metric_value or 0)
                break
    return by_point, field_balance


def _build_separator_map(cur, date_from: str, date_to: str):
    rows = [
        dict(row)
        for row in cur.execute(
            """
            SELECT day_ref, metric_name, metric_value
            FROM measurements_active
            WHERE day_ref BETWEEN ? AND ?
              AND row_kind='sep'
              AND bank='SEP'
              AND COALESCE(is_official,1)=1
            ORDER BY day_ref, metric_name
            """,
            (date_from, date_to),
        ).fetchall()
    ]
    data = defaultdict(dict)
    for row in rows:
        day_ref = str(row.get("day_ref") or "")
        metric_name = str(row.get("metric_name") or "")
        for item_key, expected_metric in _SEP_METRICS.items():
            if metric_name == expected_metric:
                data[day_ref][item_key] = row.get("metric_value")
                break
    return data


def _build_separator_alignment_map(cur, date_from: str, date_to: str, normalize_tag_name):
    rows = [
        dict(row)
        for row in cur.execute(
            """
            SELECT production_date, bank, mpfm_tag, sep_meter_id
            FROM sep_alignments
            WHERE is_active=1
              AND production_date BETWEEN ? AND ?
            ORDER BY production_date, bank, mpfm_tag
            """,
            (date_from, date_to),
        ).fetchall()
    ]
    alignment = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("production_date") or ""),
            str(row.get("bank") or "").strip().upper(),
            _norm(normalize_tag_name, row.get("mpfm_tag") or ""),
        )
        alignment[key].append(str(row.get("sep_meter_id") or "").strip())
    return alignment


def _load_xml_rows(cur, date_from: str, date_to: str, normalize_tag_name):
    generated = []
    for row in cur.execute(
        """
        SELECT production_day, cod_cadastro_poco, well_operator_name, subsea_tag, bank, filename, status, generated_at, payload_json
        FROM xml042_documents
        WHERE production_day BETWEEN ? AND ?
        ORDER BY production_day, cod_cadastro_poco
        """,
        (date_from, date_to),
    ).fetchall():
        item = dict(row)
        try:
            payload = json.loads(item.get("payload_json") or "{}")
        except Exception:
            payload = {}
        generated.append(
            {
                "source": "generated",
                "production_day": item.get("production_day") or "",
                "cod_cadastro_poco": item.get("cod_cadastro_poco") or "",
                "well_operator_name": item.get("well_operator_name") or "",
                "subsea_tag": item.get("subsea_tag") or "",
                "bank": item.get("bank") or "",
                "filename": item.get("filename") or "",
                "status": item.get("status") or "generated",
                "recorded_at": item.get("generated_at") or "",
                "oil_sm3": _empty_to_none(payload.get("oil_sm3")),
                "gas_1000sm3": _empty_to_none(payload.get("gas_1000sm3")),
                "water_sm3": _empty_to_none(payload.get("water_sm3")),
            }
        )

    imported = []
    for row in cur.execute(
        """
        SELECT r.production_day, r.cod_cadastro_poco, r.well_operator_name, r.subsea_tag, r.bank,
               f.filename, f.import_status, f.imported_at, r.oil_sm3, r.gas_1000sm3, r.water_sm3
        FROM xml042_imported_rows r
        LEFT JOIN xml042_imported_files f ON f.id = r.latest_file_id
        WHERE r.production_day BETWEEN ? AND ?
        ORDER BY r.production_day, r.cod_cadastro_poco
        """,
        (date_from, date_to),
    ).fetchall():
        item = dict(row)
        imported.append(
            {
                "source": "imported",
                "production_day": item.get("production_day") or "",
                "cod_cadastro_poco": item.get("cod_cadastro_poco") or "",
                "well_operator_name": item.get("well_operator_name") or "",
                "subsea_tag": item.get("subsea_tag") or "",
                "bank": item.get("bank") or "",
                "filename": item.get("filename") or "",
                "status": item.get("import_status") or "imported",
                "recorded_at": item.get("imported_at") or "",
                "oil_sm3": item.get("oil_sm3"),
                "gas_1000sm3": item.get("gas_1000sm3"),
                "water_sm3": item.get("water_sm3"),
            }
        )

    xml_lookup = {}
    for item in generated + imported:
        key = (
            str(item.get("production_day") or ""),
            _norm(normalize_tag_name, item.get("subsea_tag") or item.get("well_operator_name") or ""),
        )
        current = xml_lookup.get(key)
        if current and current.get("source") == "generated":
            continue
        xml_lookup[key] = item
    return generated, imported, xml_lookup


def _load_validation_issues(cur, date_from: str, date_to: str):
    rows = []
    for row in cur.execute(
        """
        SELECT day_ref, severity, issue_type, ref_key, details, created_at
        FROM validation_issues
        ORDER BY created_at, id
        """
    ).fetchall():
        item = dict(row)
        normalized = normalize_validation_issue_day_ref(item.get("day_ref", ""), item.get("created_at", ""))
        if not normalized or normalized < date_from or normalized > date_to:
            continue
        item["day_ref"] = normalized
        rows.append(item)
    categories = {
        "missing_xml": [],
        "missing_hours": [],
        "recon_partial": [],
        "verify": [],
        "separator": [],
    }
    by_day = defaultdict(list)
    for item in rows:
        by_day[item["day_ref"]].append(item)
        issue_type = str(item.get("issue_type") or "").lower()
        details = str(item.get("details") or "").lower()
        target = None
        if "missing_hours" in issue_type:
            target = "missing_hours"
        elif "recon_partial" in issue_type:
            target = "recon_partial"
        elif "verify" in issue_type or "verificar" in details:
            target = "verify"
        elif "sep" in issue_type or "separator" in details or "separador" in details:
            target = "separator"
        if target:
            categories[target].append(item)
    return rows, by_day, categories


def _row_alerts_for_group(day_issues: list[dict], group: dict, normalize_tag_name):
    related = []
    tags = {
        _norm(normalize_tag_name, group.get("subsea_tag") or ""),
        _norm(normalize_tag_name, group.get("topside_tag") or ""),
    }
    banks = {str(group.get("subsea_bank") or "").upper(), str(group.get("topside_bank") or "").upper()}
    for item in day_issues:
        ref = f"{item.get('ref_key') or ''} {item.get('details') or ''}"
        normalized_ref = _norm(normalize_tag_name, ref)
        if any(tag and tag in normalized_ref for tag in tags) or any(bank and bank in ref.upper() for bank in banks):
            related.append(item)
    return related


def build_monthly_report_payload(
    db_conn_fn,
    *,
    month: str,
    mode: str = "default",
    group_key: str = "",
    custom: dict | None = None,
    normalize_tag_name=None,
    month_pt: dict | None = None,
):
    date_from, date_to = _month_range(month)
    custom = custom or {}
    if mode == "custom":
        date_from = normalize_date_input(custom.get("date_from") or date_from) or date_from
        date_to = normalize_date_input(custom.get("date_to") or date_to) or date_to
    days = _iter_days(date_from, date_to)
    groups = _resolve_groups(mode, group_key, custom)

    conn = db_conn_fn()
    cur = conn.cursor()
    daily_points, field_balance = _build_daily_maps(cur, date_from, date_to, normalize_tag_name)
    sep_daily = _build_separator_map(cur, date_from, date_to)
    sep_alignment = _build_separator_alignment_map(cur, date_from, date_to, normalize_tag_name)
    xml_generated, xml_imported, xml_lookup = _load_xml_rows(cur, date_from, date_to, normalize_tag_name)
    validation_rows, validation_by_day, validation_categories = _load_validation_issues(cur, date_from, date_to)
    conn.close()

    all_xml_rows = sorted(
        [{**item, "source_label": _source_label(item)} for item in (xml_generated + xml_imported)],
        key=lambda item: (item.get("production_day") or "", item.get("cod_cadastro_poco") or "", item.get("source") or ""),
    )
    xml_days = {item.get("production_day") for item in all_xml_rows if item.get("production_day")}
    sep_days = {day_ref for day_ref, metrics in sep_daily.items() if metrics}
    mpfm_days = {day_ref for day_ref, _, _ in daily_points.keys()}

    report_groups = []
    monthly_group_totals = {"subsea_oil_t": 0.0, "subsea_gas_t": 0.0, "subsea_water_t": 0.0}
    for group in groups:
        rows = []
        subsea_bank = str(group.get("subsea_bank") or "").strip().upper()
        topside_bank = str(group.get("topside_bank") or "").strip().upper()
        subsea_norm = _norm(normalize_tag_name, group.get("subsea_tag") or "")
        topside_norm = _norm(normalize_tag_name, group.get("topside_tag") or "")
        for day_ref in days:
            subsea = daily_points.get((day_ref, subsea_bank, subsea_norm), {})
            topside = daily_points.get((day_ref, topside_bank, topside_norm), {})
            xml_row = xml_lookup.get((day_ref, subsea_norm)) or xml_lookup.get((day_ref, topside_norm)) or {}
            sep_metrics = sep_daily.get(day_ref, {})
            primary_hc = _pick_primary(subsea, topside, "hc_t")
            primary_total = _pick_primary(subsea, topside, "total_t")
            balance_hc = field_balance.get(day_ref, {}).get("hc_t") or 0
            balance_total = field_balance.get(day_ref, {}).get("total_t") or 0
            row_issues = _row_alerts_for_group(validation_by_day.get(day_ref, []), group, normalize_tag_name)
            sep_meters = []
            for item_key in ((day_ref, subsea_bank, subsea_norm), (day_ref, topside_bank, topside_norm)):
                sep_meters.extend(sep_alignment.get(item_key, []))
            row = {
                "day_ref": day_ref,
                "subsea_oil_t": subsea.get("oil_t"),
                "subsea_gas_t": subsea.get("gas_t"),
                "subsea_water_t": subsea.get("water_t"),
                "subsea_oil_sm3": subsea.get("oil_sm3"),
                "subsea_gas_sm3": subsea.get("gas_sm3"),
                "subsea_water_sm3": subsea.get("water_sm3"),
                "topside_oil_t": topside.get("oil_t"),
                "topside_gas_t": topside.get("gas_t"),
                "topside_water_t": topside.get("water_t"),
                "topside_oil_sm3": topside.get("oil_sm3"),
                "topside_gas_sm3": topside.get("gas_sm3"),
                "topside_water_sm3": topside.get("water_sm3"),
                "pct_hc_balance": (float(primary_hc) / balance_hc * 100.0) if primary_hc is not None and balance_hc else None,
                "pct_total_balance": (float(primary_total) / balance_total * 100.0) if primary_total is not None and balance_total else None,
                "sep_oil_t": sep_metrics.get("oil_t"),
                "sep_gas_t": sep_metrics.get("gas_t"),
                "sep_water_t": sep_metrics.get("water_t"),
                "xml_oil_sm3": xml_row.get("oil_sm3"),
                "xml_gas_1000sm3": xml_row.get("gas_1000sm3"),
                "xml_water_sm3": xml_row.get("water_sm3"),
                "xml_status": xml_row.get("status") or "",
                "xml_source_label": xml_row.get("source_label") or "",
                "xml_filename": xml_row.get("filename") or "",
                "sep_meters": ", ".join(item for item in sep_meters if item),
                "issues_count": len(row_issues),
                "issues": [
                    {
                        "issue_type": item.get("issue_type") or "",
                        "details": item.get("details") or "",
                        "severity": item.get("severity") or "",
                    }
                    for item in row_issues[:3]
                ],
            }
            rows.append(row)
            monthly_group_totals["subsea_oil_t"] += float(subsea.get("oil_t") or 0)
            monthly_group_totals["subsea_gas_t"] += float(subsea.get("gas_t") or 0)
            monthly_group_totals["subsea_water_t"] += float(subsea.get("water_t") or 0)
        report_groups.append(
            {
                **group,
                "rows": rows,
                "stats": {
                    "days_with_mpfm": sum(1 for row in rows if row["subsea_oil_t"] is not None or row["topside_oil_t"] is not None),
                    "days_with_sep": sum(1 for row in rows if row["sep_oil_t"] is not None or row["sep_gas_t"] is not None or row["sep_water_t"] is not None),
                    "days_with_xml": sum(1 for row in rows if row["xml_oil_sm3"] is not None or row["xml_gas_1000sm3"] is not None or row["xml_water_sm3"] is not None),
                },
            }
        )

    validation_categories["missing_xml"] = []
    for day_ref in days:
        for group in groups:
            subsea_norm = _norm(normalize_tag_name, group.get("subsea_tag") or "")
            topside_norm = _norm(normalize_tag_name, group.get("topside_tag") or "")
            xml_row = xml_lookup.get((day_ref, subsea_norm)) or xml_lookup.get((day_ref, topside_norm))
            if xml_row:
                continue
            has_group_measurement = (
                (day_ref, str(group.get("subsea_bank") or "").upper(), subsea_norm) in daily_points
                or (day_ref, str(group.get("topside_bank") or "").upper(), topside_norm) in daily_points
            )
            if has_group_measurement:
                validation_categories["missing_xml"].append(
                    {
                        "day_ref": day_ref,
                        "group_title": group["title"],
                        "details": "Há medição diária do grupo, mas não existe XML 042 associado.",
                    }
                )

    summary = {
        "month": month,
        "month_label": _month_label(month, month_pt),
        "date_from": date_from,
        "date_to": date_to,
        "days_in_period": len(days),
        "days_with_mpfm": len(mpfm_days.intersection(days)),
        "days_with_sep": len(sep_days.intersection(days)),
        "days_with_xml": len(xml_days.intersection(days)),
        "groups_count": len(report_groups),
        "xml_generated_count": len(xml_generated),
        "xml_imported_count": len(xml_imported),
        "mpfm_oil_t_sum": monthly_group_totals["subsea_oil_t"],
        "mpfm_gas_t_sum": monthly_group_totals["subsea_gas_t"],
        "mpfm_water_t_sum": monthly_group_totals["subsea_water_t"],
        "xml_oil_sm3_sum": sum(float(item.get("oil_sm3") or 0) for item in all_xml_rows if item.get("source") == "generated") or 0.0,
        "xml_gas_1000sm3_sum": sum(float(item.get("gas_1000sm3") or 0) for item in all_xml_rows if item.get("source") == "generated") or 0.0,
        "xml_water_sm3_sum": sum(float(item.get("water_sm3") or 0) for item in all_xml_rows if item.get("source") == "generated") or 0.0,
        "exception_count": sum(len(items) for items in validation_categories.values()),
    }

    return {
        "meta": {
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            "mode": mode,
            "mode_label": "Modo customizado" if mode == "custom" else "Fechamento mensal padrão",
            "month": month,
            "month_label": _month_label(month, month_pt),
            "date_from": date_from,
            "date_to": date_to,
            "empty_rule": "Campo vazio = sem dado. Valor 0 = dado existente com valor zero.",
        },
        "summary": summary,
        "groups": report_groups,
        "xml_rows": all_xml_rows,
        "exceptions": validation_categories,
        "validation_rows": validation_rows,
    }
