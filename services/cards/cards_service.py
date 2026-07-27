from __future__ import annotations

import json


def metric_pick(metrics: dict, *names):
    for name in names:
        if name in metrics and metrics[name] is not None:
            return metrics[name]
    return None


def safe_pct(num, den):
    try:
        num = float(num)
        den = float(den)
        if abs(den) < 1e-12:
            return None
        return abs(num / den) * 100.0
    except Exception:
        return None


def bubble_point_status(pressure_barg, card_type: str = ""):
    try:
        pressure = float(pressure_barg)
    except Exception:
        return {"state": "N/D", "icon": "⚪", "color": "#6b7280", "label": "Sem pressão"}
    if "subsea" not in str(card_type or "").lower():
        return {"state": "N/A", "icon": "⚪", "color": "#6b7280", "label": "Não aplicável"}
    if pressure > 490.0:
        return {"state": "Acima do ponto de bolha", "icon": "🟢", "color": "#16a34a", "label": "Acima do ponto de bolha"}
    return {"state": "Abaixo do ponto de bolha", "icon": "🔴", "color": "#dc2626", "label": "Abaixo do ponto de bolha"}


def build_daily_cards(card_repo, date_from: str, date_to: str, bank: str = ""):
    daily_rows = card_repo.list_daily_measurement_rows(date_from, date_to, bank)
    recon_rows = card_repo.list_recon_measurement_rows(date_from, date_to, bank)
    sep_rows = card_repo.list_sep_measurement_rows(date_from, date_to)

    groups = {}
    for row in daily_rows:
        key = (row["day_ref"], row["bank"], row["tipo"] or "", row["tag"] or "", row["instrument"] or "", row["loop"] or "")
        group = groups.setdefault(key, {"metrics": {}})
        group["metrics"][row["metric_name"]] = row["metric_value"]

    recon = {}
    for row in recon_rows:
        key = (row["day_ref"], row["bank"], row["tag"] or "")
        recon.setdefault(key, {})[row["metric_name"]] = row["metric_value"]

    sep_lookup = {}
    for row in sep_rows:
        key = (row["day_ref"], row["tag"] or "")
        sep_lookup.setdefault(key, {})[row["metric_name"]] = row["metric_value"]

    cards = []
    for (day_ref, bank_code, tipo, tag, instrument, loop), group in groups.items():
        metrics = group["metrics"]
        recon_metrics = recon.get((day_ref, bank_code, tag), {})
        daily_total = sum(value for value in [recon_metrics.get("Daily Gás (t)"), recon_metrics.get("Daily Óleo (t)"), recon_metrics.get("Daily Água (t)")] if value is not None)
        delta_total = sum(value for value in [recon_metrics.get("Δ Gás (t)"), recon_metrics.get("Δ Óleo (t)"), recon_metrics.get("Δ Água (t)")] if value is not None)
        card_type = f"MPFM {tipo or 'Medição'}"
        override = card_repo.fetch_card_override(day_ref, bank_code, card_type, tag, instrument)
        cards.append(
            {
                "id": override.get("id") if override else None,
                "production_date": day_ref,
                "bank": bank_code,
                "loop": loop,
                "card_type": card_type,
                "tag": tag,
                "instrument": instrument,
                "title": (override.get("title") if override and override.get("title") else f"{tag.replace('_', '-')} - {instrument}"),
                "source": "MPFM",
                "volumes": {
                    "oil_sm3": metric_pick(metrics, "PVT @20 vol Óleo (m³)", "PVT vol Óleo (m³)"),
                    "gas_msm3": (lambda value: (value / 1000.0) if value is not None else None)(metric_pick(metrics, "PVT @20 vol Gás (Sm³)", "PVT vol Gás (Sm³)")),
                    "water_sm3": metric_pick(metrics, "PVT @20 vol Água (m³)", "PVT vol Água (m³)"),
                },
                "masses": {
                    "oil_t": metric_pick(metrics, "PVT @20 mass Óleo (t)", "PVT mass Óleo (t)", "MPFM corr Óleo (t)"),
                    "gas_t": metric_pick(metrics, "PVT @20 mass Gás (t)", "PVT mass Gás (t)", "MPFM corr Gás (t)"),
                    "water_t": metric_pick(metrics, "PVT @20 mass Água (t)", "PVT mass Água (t)", "MPFM corr Água (t)"),
                },
                "control": {
                    "flow_velocity_ms": override.get("flow_velocity_ms") if override else None,
                    "dp_value": override.get("dp_value") if override else None,
                    "pressure_barg": metric_pick(metrics, "Pressão (barg)"),
                    "temperature_c": metric_pick(metrics, "Temperatura (°C)"),
                    "dens_gas": metric_pick(metrics, "Dens. Gás (kg/m³)"),
                    "dens_oil": metric_pick(metrics, "Dens. Óleo (kg/m³)"),
                    "dens_water": metric_pick(metrics, "Dens. Água (kg/m³)"),
                    "bubble_point": bubble_point_status(metric_pick(metrics, "Pressão (barg)"), card_type),
                    "sep_test_aligned": (override.get("sep_test_aligned") if override else ""),
                },
                "balance": {
                    "hc_pct": safe_pct(recon_metrics.get("Δ HC (t)"), recon_metrics.get("Daily HC (t)")),
                    "total_pct": safe_pct(delta_total, daily_total),
                    "mpfm_x_fiscal_pct": safe_pct(recon_metrics.get("Δ HC (t)"), recon_metrics.get("Daily HC (t)")),
                    "balanco_gas_pct": safe_pct(recon_metrics.get("Δ Gás (t)"), recon_metrics.get("Daily Gás (t)")),
                },
                "observations": (override.get("observations") if override else "") or "",
                "manual": {"has_override": bool(override), "editable_fields": ["flow_velocity_ms", "dp_value", "sep_test_aligned", "observations"]},
            }
        )

    aligns = card_repo.list_sep_alignments(date_from, date_to, bank)
    for alignment in aligns:
        day_ref = alignment["production_date"]
        bank_code = alignment["bank"]
        sep_tag = alignment["sep_tag"] or "SEP"
        sep_metrics = sep_lookup.get((day_ref, sep_tag), {})
        if not sep_metrics:
            continue
        override = card_repo.fetch_card_override(day_ref, bank_code, "Separador", sep_tag, alignment["sep_meter_id"] or "")
        mp_metrics = None
        for key, group in groups.items():
            if key[0] == day_ref and key[1] == bank_code and key[3] == (alignment["mpfm_tag"] or ""):
                mp_metrics = group["metrics"]
                break
        mp_total = None
        mp_hc = None
        if mp_metrics:
            mp_total = sum(
                value
                for value in [
                    metric_pick(mp_metrics, "PVT @20 mass Gás (t)", "PVT mass Gás (t)", "MPFM corr Gás (t)"),
                    metric_pick(mp_metrics, "PVT @20 mass Óleo (t)", "PVT mass Óleo (t)", "MPFM corr Óleo (t)"),
                    metric_pick(mp_metrics, "PVT @20 mass Água (t)", "PVT mass Água (t)", "MPFM corr Água (t)"),
                ]
                if value is not None
            )
            mp_hc = sum(
                value
                for value in [
                    metric_pick(mp_metrics, "PVT @20 mass Gás (t)", "PVT mass Gás (t)", "MPFM corr Gás (t)"),
                    metric_pick(mp_metrics, "PVT @20 mass Óleo (t)", "PVT mass Óleo (t)", "MPFM corr Óleo (t)"),
                ]
                if value is not None
            )
        cards.append(
            {
                "id": override.get("id") if override else None,
                "production_date": day_ref,
                "bank": bank_code,
                "loop": "",
                "card_type": "Separador",
                "tag": sep_tag,
                "instrument": alignment["sep_meter_id"] or "",
                "title": (override.get("title") if override and override.get("title") else f"Separador - {alignment['sep_meter_id'] or sep_tag}"),
                "source": "SEP",
                "volumes": {"oil_sm3": sep_metrics.get("oil_m3"), "gas_msm3": None, "water_sm3": None},
                "masses": {"oil_t": sep_metrics.get("oil_t"), "gas_t": sep_metrics.get("gas_t"), "water_t": sep_metrics.get("water_t")},
                "control": {
                    "flow_velocity_ms": override.get("flow_velocity_ms") if override else None,
                    "dp_value": override.get("dp_value") if override else None,
                    "pressure_barg": sep_metrics.get("pressure_barg"),
                    "temperature_c": sep_metrics.get("temp"),
                    "dens_gas": None,
                    "dens_oil": None,
                    "dens_water": None,
                    "bubble_point": bubble_point_status(sep_metrics.get("pressure_barg"), "Separador"),
                    "sep_test_aligned": (override.get("sep_test_aligned") if override else ""),
                },
                "balance": {
                    "hc_pct": safe_pct((sep_metrics.get("hc_t") or 0) - (mp_hc or 0), sep_metrics.get("hc_t") or mp_hc or 0),
                    "total_pct": safe_pct((sep_metrics.get("total_t") or 0) - (mp_total or 0), sep_metrics.get("total_t") or mp_total or 0),
                    "mpfm_x_fiscal_pct": safe_pct((sep_metrics.get("hc_t") or 0) - (mp_hc or 0), sep_metrics.get("hc_t") or mp_hc or 0),
                    "balanco_gas_pct": None,
                },
                "observations": ((override.get("observations") if override else "") or alignment["notes"] or ""),
                "manual": {"has_override": bool(override), "editable_fields": ["flow_velocity_ms", "dp_value", "sep_test_aligned", "observations"]},
            }
        )

    for row in card_repo.list_manual_cards(date_from, date_to, bank):
        payload = {}
        try:
            payload = json.loads(row["manual_payload"] or "{}")
        except Exception:
            payload = {}
        cards.append(
            {
                "id": row["id"],
                "production_date": row["production_date"],
                "bank": row["bank"],
                "loop": "",
                "card_type": "Manual",
                "tag": row["tag"] or "",
                "instrument": row["instrument"] or "",
                "title": row["title"] or "Card Manual",
                "source": "MANUAL",
                "volumes": payload.get("volumes", {"oil_sm3": None, "gas_msm3": None, "water_sm3": None}),
                "masses": payload.get("masses", {"oil_t": None, "gas_t": None, "water_t": None}),
                "control": {
                    "flow_velocity_ms": row["flow_velocity_ms"],
                    "dp_value": row["dp_value"],
                    "pressure_barg": payload.get("pressure_barg"),
                    "temperature_c": payload.get("temperature_c"),
                    "dens_gas": payload.get("dens_gas"),
                    "dens_oil": payload.get("dens_oil"),
                    "dens_water": payload.get("dens_water"),
                    "bubble_point": bubble_point_status(payload.get("pressure_barg"), row["card_type"]),
                    "sep_test_aligned": row["sep_test_aligned"] or payload.get("sep_test_aligned") or "",
                },
                "balance": payload.get("balance", {"hc_pct": None, "total_pct": None, "mpfm_x_fiscal_pct": None, "balanco_gas_pct": None}),
                "observations": row["observations"] or "",
                "manual": {"has_override": True, "editable_fields": ["flow_velocity_ms", "dp_value", "sep_test_aligned", "observations"]},
            }
        )

    cards.sort(key=lambda card: (card["production_date"], card["bank"], card["card_type"], card["title"]))
    return cards
