"""
Twin MPFM — Motores de cálculo metrológico.

PRESERVA AS FÓRMULAS DO v4 LITERALMENTE. Nenhuma alteração funcional desta extração.
Referência canônica das equações:

    NSV_sep            = GSV_sep × (1 - BSW/100)
    V_STO              = NSV_sep × SF_sep_tank
    m_oil_REF          = V_STO × rho_oil_STO / 1000
    V_gas_flash_std    = V_STO × deltaRs_sep_tank
    V_gas_total_std    = V_gas_sep_std + V_gas_flash_std
    m_gas_REF          = V_gas_total_std × rho_gas_std / 1000
    V_water_oil_std    = GSV_sep × BSW/100
    V_water_total_std  = V_water_free_std + V_water_oil_std
    m_water_REF        = V_water_total_std × rho_water_20 / 1000
    m_HC_REF           = m_oil_REF + m_gas_REF
    m_total_REF        = m_HC_REF + m_water_REF
    GVF                = qg_actual / (qg_actual + qo + qw)
    WLR                = qw / (qo + qw)
    GOR                = qg / qo
    En_HC              = (x_MPFM - x_REF) / sqrt(U_MPFM^2 + U_REF^2)
    δ_phase (%)        = 100 × (x_MPFM - x_REF) / x_REF
"""
from __future__ import annotations
from math import sqrt
from typing import Any, Dict, List, Optional


# ==================== Constants ====================
CONSTANTS: Dict[str, Any] = {
    "T_STD_C": 20.0,
    "P_STD_MPA_ABS": 0.101325,
    "P_STD_BARA": 1.01325,
    "T_STD_K": 293.15,
    "Z_GAS_DEFAULT": 0.90,
    "RHO_WATER_PURE_20": 998.2,
    "IAJ_TARGET": 60.0,
    "HC_LIMIT_TRIAGE": 5.0,
    "TOTAL_LIMIT_TRIAGE": 7.0,
    "FCS320_MODE": "external_reference",
    "EOS_MODE": "independent_validation",
    "ROUTE_CONFIDENCE_DEFAULT": "inferred",
    "GAS_LIFT_DEFAULT_STATUS": "not_confirmed",
}

DEFAULT_SEPARATOR: Dict[str, float] = {
    "GSV_sep": 8.12 * 24,
    "BSW": 0.08,
    "SF_sep_tank": 0.87,
    "rho_oil_STO": 861.0,
    "V_gas_sep_std": 2198.41 * 24,
    "deltaRs_sep_tank": 62.11,
    "rho_gas_std": 0.734 * 1.225,
    "V_water_free_std": 0.05,
    "rho_water_20": 998.2,
    "U_MPFM": 3.0,
    "U_REF": 2.0,
}

DEFAULT_PVT: Dict[str, Any] = {
    "source": "Registro PVTSim / SLB / Backflash Validation",
    "eos": "SRK + Peneloux",
    "fluidId": "PE-4 / PW-104",
    "SF_sep_tank": 0.87,
    "deltaRs_sep_tank": 62.11,
    "rho_oil_STO": 861.0,
    "rho_gas_std": 0.899,
    "status": "validated_tabulated",
    "nativeFile": False,
}


# ==================== Utilities ====================
def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ==================== Classification ====================
def classify_envelope(gvf: float, wlr: float) -> str:
    """Envelope GVF × WLR — limites do v4 (triagem operacional)."""
    if gvf > 0.86 or wlr > 0.78 or (gvf > 0.68 and wlr > 0.52):
        return "Fora do Envelope"
    if gvf > 0.58 or wlr > 0.45 or (gvf > 0.42 and wlr > 0.34):
        return "Restrita"
    return "Apta"


def classify_iaj(iaj: float, envelope_status: str) -> str:
    """Status da janela combinando IAJ e envelope."""
    if envelope_status == "Fora do Envelope" or iaj < 55:
        return "Bloqueada"
    if envelope_status == "Restrita" or iaj < 80:
        return "Restrita"
    return "Apta"


# ==================== Balanço Separador / Referência ====================
def separator_balance(separator: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Calcula referência por balanço de massas a partir das medições do separador.

    Fórmulas conforme cabeçalho do módulo. Não alterar sem justificativa.
    """
    s = {**DEFAULT_SEPARATOR, **(separator or {})}
    GSV_sep = float(s.get("GSV_sep") or 0)
    BSW = float(s.get("BSW") or 0)
    SF = float(s.get("SF_sep_tank") or 0)
    rho_oil = float(s.get("rho_oil_STO") or 0)
    V_gas_sep = float(s.get("V_gas_sep_std") or 0)
    dRs = float(s.get("deltaRs_sep_tank") or 0)
    rho_gas = float(s.get("rho_gas_std") or 0)
    V_water_free = float(s.get("V_water_free_std") or 0)
    rho_water = float(s.get("rho_water_20") or CONSTANTS["RHO_WATER_PURE_20"])

    NSV_sep = GSV_sep * (1 - BSW / 100)
    V_STO = NSV_sep * SF
    m_oil_REF = V_STO * rho_oil / 1000
    V_gas_flash_std = V_STO * dRs
    V_gas_total_std = V_gas_sep + V_gas_flash_std
    m_gas_REF = V_gas_total_std * rho_gas / 1000
    V_water_oil_std = GSV_sep * (BSW / 100)
    V_water_total_std = V_water_free + V_water_oil_std
    m_water_REF = V_water_total_std * rho_water / 1000
    m_HC_REF = m_oil_REF + m_gas_REF
    m_total_REF = m_HC_REF + m_water_REF
    return {
        "NSV_sep": NSV_sep,
        "V_STO": V_STO,
        "m_oil_REF": m_oil_REF,
        "V_gas_flash_std": V_gas_flash_std,
        "V_gas_total_std": V_gas_total_std,
        "m_gas_REF": m_gas_REF,
        "V_water_oil_std": V_water_oil_std,
        "V_water_total_std": V_water_total_std,
        "m_water_REF": m_water_REF,
        "m_HC_REF": m_HC_REF,
        "m_total_REF": m_total_REF,
    }


# ==================== Massas estimadas do MPFM ====================
def estimate_mpfm_masses(input_data: Dict[str, Any], separator: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Converte vazões padrão do MPFM em massas por fase (t)."""
    s = {**DEFAULT_SEPARATOR, **(separator or {})}
    qo = float(input_data.get("qo") or 0)
    qw = float(input_data.get("qw") or 0)
    qg = float(input_data.get("qg") or 0)
    gas_lift = float(input_data.get("gasLift") or 0)
    m_oil = qo * float(s.get("rho_oil_STO") or 0) / 1000
    m_gas = max(qg - gas_lift, 0.0) * float(s.get("rho_gas_std") or 0) / 1000
    m_water = qw * float(s.get("rho_water_20") or CONSTANTS["RHO_WATER_PURE_20"]) / 1000
    return {
        "m_oil_MPFM": m_oil,
        "m_gas_MPFM": m_gas,
        "m_water_MPFM": m_water,
        "m_HC_MPFM": m_oil + m_gas,
        "m_total_MPFM": m_oil + m_gas + m_water,
    }


# ==================== Desvios relativos ====================
def deviations(m: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    """δ_phase (%) = 100 × (x_MPFM - x_REF) / x_REF."""
    def rel(value: float, ref: float) -> float:
        return 100 * (value - ref) / ref if ref else 0.0
    return {
        "delta_oil": rel(m["m_oil_MPFM"], b["m_oil_REF"]),
        "delta_gas": rel(m["m_gas_MPFM"], b["m_gas_REF"]),
        "delta_water": rel(m["m_water_MPFM"], b["m_water_REF"]),
        "delta_HC": rel(m["m_HC_MPFM"], b["m_HC_REF"]),
        "delta_total": rel(m["m_total_MPFM"], b["m_total_REF"]),
    }


# ==================== Erro normalizado (En) ====================
def normalized_error(x_mpfm: float, x_ref: float, u_mpfm: float, u_ref: float) -> float:
    """En = (x_MPFM - x_REF) / sqrt(U_MPFM^2 + U_REF^2)."""
    denom = sqrt(float(u_mpfm) ** 2 + float(u_ref) ** 2)
    return (x_mpfm - x_ref) / denom if denom else 0.0


# ==================== IAJ (Índice de Aplicabilidade da Janela) ====================
def calculate_iaj(gvf: float, wlr: float, envelope_status: str,
                  dev: Dict[str, float], gas_lift: float) -> int:
    """IAJ 0–100 com decomposição por pesos do v4. Não alterar sem justificativa."""
    score = 100.0
    if envelope_status == "Restrita":
        score -= 18
    if envelope_status == "Fora do Envelope":
        score -= 42
    if gvf > 0.65:
        score -= 12
    if wlr > 0.50:
        score -= 10
    if abs(dev.get("delta_HC", 0)) > CONSTANTS["HC_LIMIT_TRIAGE"]:
        score -= 14
    if abs(dev.get("delta_total", 0)) > CONSTANTS["TOTAL_LIMIT_TRIAGE"]:
        score -= 14
    if gas_lift <= 0:
        score -= 4
    score -= 5  # rota inferida no MVP
    return int(round(clamp(score, 0, 100)))


# ==================== Alertas RCA ====================
def build_alerts(input_data: Dict[str, Any], r: Dict[str, Any]) -> List[Dict[str, str]]:
    alerts: List[Dict[str, str]] = []
    if input_data.get("gasLift", 0) <= 0:
        alerts.append({"type": "warn", "title": "Gas lift não confirmado",
                       "detail": "Cálculo executado sem compensação de gas lift."})
    alerts.append({"type": "warn", "title": "Roteamento inferido",
                   "detail": "Alinhamento real de válvulas não disponível no MVP."})
    if r["gvf"] > 0.65:
        alerts.append({"type": "bad", "title": "GVF elevado",
                       "detail": "Ponto próximo ou acima de zona crítica."})
    if r["wlr"] > 0.45:
        alerts.append({"type": "warn", "title": "WLR elevado",
                       "detail": "Verificar representatividade de água e estabilidade da janela."})
    if abs(r["enHC"]) > 1:
        alerts.append({"type": "bad", "title": "Erro normalizado acima de 1",
                       "detail": f"En_HC={r['enHC']:.3f}."})
    else:
        alerts.append({"type": "ok", "title": "Compatibilidade por En",
                       "detail": f"En_HC={r['enHC']:.3f}."})
    return alerts


# ==================== Pipeline analyze completo ====================
def _compute_kinematic_metrics(pressure: float, temperature: float,
                               qo: float, qw: float, qg: float) -> Dict[str, float]:
    """Calcula qg_actual, GVF, WLR, GOR a partir das vazões e P/T da janela.

    qg_actual = qg × (P_std/P_abs) × (T/T_std) / Z   (correção P/T/Z)
    GVF       = qg_actual / (qg_actual + qo + qw)
    WLR       = qw / (qo + qw)
    GOR       = qg / qo
    """
    p_abs_bara = max(pressure + CONSTANTS["P_STD_BARA"], CONSTANTS["P_STD_BARA"])
    t_k = temperature + 273.15
    qg_actual = qg * (CONSTANTS["P_STD_BARA"] / p_abs_bara) * (t_k / CONSTANTS["T_STD_K"]) / CONSTANTS["Z_GAS_DEFAULT"]
    liquid = max(qo + qw, 1e-6)
    gvf = clamp(qg_actual / max(qg_actual + liquid, 1e-6), 0, 1)
    wlr = clamp(qw / liquid, 0, 1)
    gor = qg / qo if qo > 0 else 0.0
    return {"qgActual": qg_actual, "gvf": gvf, "wlr": wlr, "gor": gor}


def analyze(input_data: Dict[str, Any],
            separator: Optional[Dict[str, Any]] = None,
            pvt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Orquestra todo o pipeline da janela e devolve o dicionário canônico.

    Estrutura preserva contrato esperado pelo frontend e pelo memorial.
    """
    i = input_data or {}
    s = {**DEFAULT_SEPARATOR, **(separator or {})}
    qo = float(i.get("qo") or 0)
    qw = float(i.get("qw") or 0)
    qg = float(i.get("qg") or 0)
    gas_lift = float(i.get("gasLift") or 0)

    km = _compute_kinematic_metrics(
        pressure=float(i.get("pressure") or 0),
        temperature=float(i.get("temperature") or 0),
        qo=qo, qw=qw, qg=qg,
    )
    envelope_status = classify_envelope(km["gvf"], km["wlr"])
    balance = separator_balance(s)
    mpfm = estimate_mpfm_masses(i, s)
    dev = deviations(mpfm, balance)
    iaj = calculate_iaj(km["gvf"], km["wlr"], envelope_status, dev, gas_lift)
    technical_status = classify_iaj(iaj, envelope_status)
    factor_suggested = balance["m_HC_REF"] / mpfm["m_HC_MPFM"] if mpfm["m_HC_MPFM"] > 0 else 1.0
    en_hc = normalized_error(mpfm["m_HC_MPFM"], balance["m_HC_REF"],
                             s.get("U_MPFM", 0), s.get("U_REF", 0))
    alerts = build_alerts(i, {"gvf": km["gvf"], "wlr": km["wlr"], "iaj": iaj,
                              "enHC": en_hc, "technicalStatus": technical_status})
    return {
        "input": i,
        "separator": s,
        "pvt": {**DEFAULT_PVT, **(pvt or {})},
        "metrics": {
            **km,
            "envelopeStatus": envelope_status,
            "iaj": iaj,
            "technicalStatus": technical_status,
            "factorSuggested": factor_suggested,
            "enHC": en_hc,
        },
        "balance": balance,
        "mpfmMasses": mpfm,
        "deviations": dev,
        "alerts": alerts,
        "lineage": {
            "FCS320_MODE": CONSTANTS["FCS320_MODE"],
            "EOS_MODE": CONSTANTS["EOS_MODE"],
            "route_confidence": CONSTANTS["ROUTE_CONFIDENCE_DEFAULT"],
            "gas_lift_status": "provided" if gas_lift > 0 else CONSTANTS["GAS_LIFT_DEFAULT_STATUS"],
            "native_pvt_available": False,
        },
    }


# ==================== Memorial auditável ====================
def build_memorial(analysis_doc: Dict[str, Any]) -> str:
    """Memorial Markdown — preserva lógica/lay-out do v4 (regra do projeto)."""
    i = analysis_doc["input"]
    m = analysis_doc["metrics"]
    b = analysis_doc["balance"]
    d = analysis_doc["deviations"]
    lin = analysis_doc["lineage"]
    return f"""# Memorial da Janela — Twin MPFM

## Identificação
- Poço / corrente: {i.get('well', '')}
- Janela: {i.get('windowLabel', '')}
- Par de comparação: {i.get('comparisonPair', '')}
- Condição padrão: {CONSTANTS['T_STD_C']:.0f} °C e {CONSTANTS['P_STD_MPA_ABS']} MPa abs
- FCS320/PVTPack: {lin['FCS320_MODE']}
- Rota: {lin['route_confidence']}
- Gas lift: {lin['gas_lift_status']}

## Consultor de Aplicabilidade
- GVF: {m['gvf']:.6f}
- WLR: {m['wlr']:.6f}
- GOR: {m['gor']:.6f} Sm³/Sm³
- Envelope: {m['envelopeStatus']}
- IAJ: {m['iaj']}
- Status: {m['technicalStatus']}
- Fator sugerido: {m['factorSuggested']:.6f} — requer aprovação metrológica

## Balanço Separador / Referência
- NSV_sep: {b['NSV_sep']:.6f} m³ @20°C
- V_STO: {b['V_STO']:.6f} Sm³ @20°C
- m_oil_REF: {b['m_oil_REF']:.6f} t
- V_gas_flash_std: {b['V_gas_flash_std']:.6f} Sm³
- V_gas_total_std: {b['V_gas_total_std']:.6f} Sm³
- m_gas_REF: {b['m_gas_REF']:.6f} t
- V_water_total_std: {b['V_water_total_std']:.6f} m³ @20°C
- m_water_REF: {b['m_water_REF']:.6f} t
- m_HC_REF: {b['m_HC_REF']:.6f} t
- m_total_REF: {b['m_total_REF']:.6f} t

## Desvios relativos
- δ_oil: {d['delta_oil']:.6f} %
- δ_gas: {d['delta_gas']:.6f} %
- δ_water: {d['delta_water']:.6f} %
- δ_HC: {d['delta_HC']:.6f} %
- δ_total: {d['delta_total']:.6f} %
- En_HC: {m['enHC']:.6f}

## Observações técnicas
- SF_sep→tank não é tratado como 1/Bo genérico sem equivalência demonstrada.
- ΔRs_sep→tank é tratado como gás incremental separador→tanque, não como Rs total de reservatório.
- Densidade Coriolis, quando disponível, é diagnóstico de coerência e não substitui automaticamente ρ_oil_STO.
- Critérios fixos são triagem; compatibilidade por incerteza/En deve prevalecer quando houver incertezas.
"""
