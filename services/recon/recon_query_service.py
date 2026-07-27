from __future__ import annotations

from collections import defaultdict

from recon_engine import MPFMHoraInput, SepHoraInput


def _metric(block: dict, *names):
    for name in names:
        value = block.get(name)
        if value is not None:
            return value
    return None


def build_sep_horas_full(recon_repo, has_sep_alignment, bank: str, day_ref: str, analytical_snapshot: dict | None = None) -> list:
    rows = recon_repo.list_sep_detail_hour_rows(day_ref)
    analytical_snapshot = analytical_snapshot or {}
    bsw_user_pct = analytical_snapshot.get("bsw_pct")

    if not rows:
        legacy_rows = recon_repo.list_sep_hour_rows(day_ref)
        hora_data = defaultdict(lambda: defaultdict(dict))
        for hour_ref, tag, metric, value in legacy_rows:
            if hour_ref is None:
                continue
            hora_data[hour_ref][tag][metric] = value
        result = []
        for hour in sorted(hora_data.keys()):
            tags = hora_data[hour]
            combined = tags.get("SEP") or {}
            oleo = tags.get("sep_oleo") or combined
            agua = tags.get("sep_agua") or combined
            gas = tags.get("sep_gas") or combined
            result.append(
                SepHoraInput(
                    hora=hour,
                    dt_str="",
                    gsv_sep_sm3=oleo.get("oil_m3"),
                    agua_gsv_sm3=agua.get("water_t"),
                    agua_nsv_sm3=None,
                    agua_mass_t=agua.get("water_t"),
                    gas_vol_sm3=None,
                    gas_mass_t=gas.get("gas_t"),
                    bsw_user_pct=bsw_user_pct,
                    pressao_barg=oleo.get("pressure_barg"),
                    temperatura_c=oleo.get("temp"),
                )
            )
        return result

    hora_data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for row_kind, hour_ref, tag, metric, value in rows:
        if hour_ref is None:
            continue
        hour = hour_ref
        hora_data[hour][row_kind][tag][metric] = value

    result = []
    for hour in sorted(hora_data.keys()):
        blocks = hora_data[hour]
        oleo = next(iter((blocks.get("sep_oleo_detail") or {}).values()), {})
        agua = next(iter((blocks.get("sep_agua_detail") or {}).values()), {})
        gas = next(iter((blocks.get("sep_gas_detail") or {}).values()), {})
        pressure_kpa = _metric(oleo, "Pressure_kPa")
        result.append(
            SepHoraInput(
                hora=hour,
                dt_str="",
                gsv_sep_sm3=_metric(oleo, "GSV_sm3", "GV_m3", "IV_m3"),
                agua_gsv_sm3=_metric(agua, "GSV_sm3", "GV_m3", "IV_m3"),
                agua_nsv_sm3=_metric(agua, "NSV_sm3"),
                agua_mass_t=_metric(agua, "Mass_ton"),
                gas_vol_sm3=_metric(gas, "StVol_m3", "GrVol_m3"),
                gas_mass_t=_metric(gas, "Mass_t"),
                bsw_user_pct=bsw_user_pct if bsw_user_pct is not None else _metric(oleo, "BSW_pct"),
                pressao_barg=_metric(oleo, "Pressure_barg") or ((float(pressure_kpa) / 100.0) if pressure_kpa is not None else None),
                temperatura_c=_metric(oleo, "Temperature_degC"),
            )
        )
    return result


def build_mpfm_horas(recon_repo, bank: str, tag: str, day_ref: str) -> list:
    rows = recon_repo.list_mpfm_hour_rows(bank, tag, day_ref)

    hora_data = defaultdict(dict)
    for hour_ref, metric, value in rows:
        if hour_ref is None:
            continue
        hour = hour_ref
        hora_data[hour][metric] = value

    metric_map = {
        "MPFM corr Óleo (t)": "oleo_corr_t",
        "MPFM corr Gás (t)": "gas_corr_t",
        "MPFM corr Água (t)": "agua_corr_t",
        "MPFM corr HC (t)": "hc_corr_t",
        "MPFM corr Total (t)": "total_corr_t",
        "PVT @20 mass Óleo (t)": "oleo_st_t",
        "PVT @20 mass Gás (t)": "gas_st_t",
        "PVT @20 mass Água (t)": "agua_st_t",
        "PVT @20 vol Óleo (m³)": "oleo_st_m3",
        "PVT @20 vol Gás (Sm³)": "gas_st_ksm3",
        "PVT @20 vol Água (m³)": "agua_st_m3",
        "Pressão (barg)": "pressao_barg",
        "Temperatura (°C)": "temperatura_c",
        "Dens. Óleo (kg/m³)": "rho_oleo_linha",
        "Dens. Gás (kg/m³)": "rho_gas_linha",
        "Dens. Água (kg/m³)": "rho_agua_linha",
    }

    result = []
    for hour in sorted(hora_data.keys()):
        data = hora_data[hour]
        kwargs = {"hora": hour, "dt_str": ""}
        for metric_name, field_name in metric_map.items():
            if metric_name in data:
                value = data[metric_name]
                if field_name == "gas_st_ksm3" and value is not None:
                    value = value / 1000.0
                kwargs[field_name] = value
        result.append(MPFMHoraInput(**kwargs))
    return result
