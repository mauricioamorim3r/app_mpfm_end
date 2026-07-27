"""
Unit tests dos motores de cálculo metrológico (sem dependência de HTTP/Mongo).

Cada teste valida UMA fórmula contra valor analítico esperado.
NÃO altere os valores esperados sem justificativa metrológica documentada.
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

# Garantir import do pacote services quando executado via pytest na raiz
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from services.calculations import (
    CONSTANTS,
    DEFAULT_PVT,
    DEFAULT_SEPARATOR,
    analyze,
    build_alerts,
    build_memorial,
    calculate_iaj,
    classify_envelope,
    classify_iaj,
    clamp,
    deviations,
    estimate_mpfm_masses,
    normalized_error,
    separator_balance,
)


# ==================== Constantes & utilitários ====================
class TestConstants:
    def test_thirteen_keys(self):
        assert len(CONSTANTS) == 13

    def test_t_std(self):
        assert CONSTANTS["T_STD_C"] == 20.0
        assert CONSTANTS["T_STD_K"] == 293.15

    def test_pressure_std(self):
        assert CONSTANTS["P_STD_BARA"] == pytest.approx(1.01325)
        assert CONSTANTS["P_STD_MPA_ABS"] == pytest.approx(0.101325)

    def test_fcs320_external(self):
        assert CONSTANTS["FCS320_MODE"] == "external_reference"

    def test_eos_independent(self):
        assert CONSTANTS["EOS_MODE"] == "independent_validation"


def test_clamp():
    assert clamp(0.5, 0, 1) == 0.5
    assert clamp(-1, 0, 1) == 0
    assert clamp(2, 0, 1) == 1
    assert clamp(0.0, 0, 1) == 0.0


# ==================== Classificação Envelope / IAJ ====================
class TestClassifyEnvelope:
    def test_apta_baixa_gvf_baixa_wlr(self):
        assert classify_envelope(0.3, 0.2) == "Apta"

    def test_restrita_por_gvf_alta(self):
        assert classify_envelope(0.6, 0.2) == "Restrita"

    def test_restrita_por_wlr_alta(self):
        assert classify_envelope(0.3, 0.5) == "Restrita"

    def test_restrita_por_combinacao(self):
        assert classify_envelope(0.45, 0.36) == "Restrita"

    def test_fora_por_gvf_critica(self):
        assert classify_envelope(0.9, 0.2) == "Fora do Envelope"

    def test_fora_por_wlr_critica(self):
        assert classify_envelope(0.3, 0.85) == "Fora do Envelope"

    def test_fora_por_combinacao_critica(self):
        assert classify_envelope(0.7, 0.55) == "Fora do Envelope"


class TestClassifyIAJ:
    def test_apta_iaj_alto_envelope_apta(self):
        assert classify_iaj(90, "Apta") == "Apta"

    def test_restrita_quando_envelope_restrita(self):
        assert classify_iaj(95, "Restrita") == "Restrita"

    def test_restrita_quando_iaj_baixo(self):
        assert classify_iaj(70, "Apta") == "Restrita"

    def test_bloqueada_quando_iaj_critico(self):
        assert classify_iaj(40, "Apta") == "Bloqueada"

    def test_bloqueada_quando_fora_envelope(self):
        assert classify_iaj(99, "Fora do Envelope") == "Bloqueada"


# ==================== Balanço Separador (fórmulas-chave) ====================
class TestSeparatorBalance:
    """Valida cada fórmula contra cálculo analítico independente."""

    def _expected(self, s):
        NSV = s["GSV_sep"] * (1 - s["BSW"] / 100)
        VSTO = NSV * s["SF_sep_tank"]
        m_oil = VSTO * s["rho_oil_STO"] / 1000
        V_flash = VSTO * s["deltaRs_sep_tank"]
        V_gas_tot = s["V_gas_sep_std"] + V_flash
        m_gas = V_gas_tot * s["rho_gas_std"] / 1000
        V_w_oil = s["GSV_sep"] * (s["BSW"] / 100)
        V_w_tot = s["V_water_free_std"] + V_w_oil
        m_water = V_w_tot * s["rho_water_20"] / 1000
        m_HC = m_oil + m_gas
        m_total = m_HC + m_water
        return locals()

    def test_default_separator_matches_analytical(self):
        e = self._expected(DEFAULT_SEPARATOR)
        r = separator_balance(DEFAULT_SEPARATOR)
        assert r["NSV_sep"] == pytest.approx(e["NSV"], rel=1e-9)
        assert r["V_STO"] == pytest.approx(e["VSTO"], rel=1e-9)
        assert r["m_oil_REF"] == pytest.approx(e["m_oil"], rel=1e-9)
        assert r["V_gas_flash_std"] == pytest.approx(e["V_flash"], rel=1e-9)
        assert r["V_gas_total_std"] == pytest.approx(e["V_gas_tot"], rel=1e-9)
        assert r["m_gas_REF"] == pytest.approx(e["m_gas"], rel=1e-9)
        assert r["V_water_oil_std"] == pytest.approx(e["V_w_oil"], rel=1e-9)
        assert r["V_water_total_std"] == pytest.approx(e["V_w_tot"], rel=1e-9)
        assert r["m_water_REF"] == pytest.approx(e["m_water"], rel=1e-9)
        assert r["m_HC_REF"] == pytest.approx(e["m_HC"], rel=1e-9)
        assert r["m_total_REF"] == pytest.approx(e["m_total"], rel=1e-9)

    def test_zero_BSW(self):
        s = {**DEFAULT_SEPARATOR, "BSW": 0}
        r = separator_balance(s)
        assert r["NSV_sep"] == DEFAULT_SEPARATOR["GSV_sep"]
        assert r["V_water_oil_std"] == 0
        assert r["V_water_total_std"] == DEFAULT_SEPARATOR["V_water_free_std"]

    def test_total_eq_oil_plus_gas_plus_water(self):
        r = separator_balance(DEFAULT_SEPARATOR)
        # m_total_REF == m_oil_REF + m_gas_REF + m_water_REF (forma alternativa)
        assert r["m_total_REF"] == pytest.approx(
            r["m_oil_REF"] + r["m_gas_REF"] + r["m_water_REF"], rel=1e-9
        )

    def test_partial_override_keeps_defaults(self):
        r = separator_balance({"BSW": 1.0})
        # GSV_sep deve cair de volta no default
        expected_NSV = DEFAULT_SEPARATOR["GSV_sep"] * (1 - 1.0 / 100)
        assert r["NSV_sep"] == pytest.approx(expected_NSV, rel=1e-9)

    def test_empty_dict_falls_back_to_defaults(self):
        r = separator_balance({})
        r_default = separator_balance(DEFAULT_SEPARATOR)
        for k in r:
            assert r[k] == pytest.approx(r_default[k], rel=1e-9)


# ==================== Massas MPFM ====================
class TestEstimateMpfmMasses:
    def test_default_input(self):
        i = {"qo": 800.34, "qw": 0.04, "qg": 252796, "gasLift": 0}
        m = estimate_mpfm_masses(i, DEFAULT_SEPARATOR)
        assert m["m_oil_MPFM"] == pytest.approx(800.34 * 861.0 / 1000, rel=1e-9)
        assert m["m_water_MPFM"] == pytest.approx(0.04 * 998.2 / 1000, rel=1e-9)
        assert m["m_gas_MPFM"] == pytest.approx(
            252796 * (0.734 * 1.225) / 1000, rel=1e-9
        )
        assert m["m_HC_MPFM"] == pytest.approx(m["m_oil_MPFM"] + m["m_gas_MPFM"], rel=1e-9)
        assert m["m_total_MPFM"] == pytest.approx(
            m["m_oil_MPFM"] + m["m_gas_MPFM"] + m["m_water_MPFM"], rel=1e-9
        )

    def test_gas_lift_subtracts_from_gas(self):
        i = {"qo": 100, "qw": 0, "qg": 1000, "gasLift": 200}
        s = {**DEFAULT_SEPARATOR, "rho_gas_std": 1.0}
        m = estimate_mpfm_masses(i, s)
        assert m["m_gas_MPFM"] == pytest.approx((1000 - 200) * 1.0 / 1000, rel=1e-9)

    def test_gas_lift_larger_than_qg_floors_at_zero(self):
        i = {"qo": 0, "qw": 0, "qg": 100, "gasLift": 500}
        m = estimate_mpfm_masses(i, DEFAULT_SEPARATOR)
        assert m["m_gas_MPFM"] == 0.0


# ==================== Desvios ====================
class TestDeviations:
    def test_zero_when_equal(self):
        m = {"m_oil_MPFM": 10, "m_gas_MPFM": 5, "m_water_MPFM": 1,
             "m_HC_MPFM": 15, "m_total_MPFM": 16}
        b = {"m_oil_REF": 10, "m_gas_REF": 5, "m_water_REF": 1,
             "m_HC_REF": 15, "m_total_REF": 16}
        d = deviations(m, b)
        assert all(v == 0 for v in d.values())

    def test_positive_when_mpfm_above_ref(self):
        m = {"m_oil_MPFM": 110, "m_gas_MPFM": 110, "m_water_MPFM": 110,
             "m_HC_MPFM": 220, "m_total_MPFM": 330}
        b = {"m_oil_REF": 100, "m_gas_REF": 100, "m_water_REF": 100,
             "m_HC_REF": 200, "m_total_REF": 300}
        d = deviations(m, b)
        for v in d.values():
            assert v == pytest.approx(10.0, rel=1e-9)

    def test_ref_zero_returns_zero(self):
        m = {"m_oil_MPFM": 1, "m_gas_MPFM": 1, "m_water_MPFM": 1,
             "m_HC_MPFM": 2, "m_total_MPFM": 3}
        b = {"m_oil_REF": 0, "m_gas_REF": 0, "m_water_REF": 0,
             "m_HC_REF": 0, "m_total_REF": 0}
        d = deviations(m, b)
        assert all(v == 0.0 for v in d.values())


# ==================== En normalizado ====================
class TestNormalizedError:
    def test_zero_when_equal(self):
        assert normalized_error(100, 100, 3, 2) == 0.0

    def test_known_value(self):
        # En = (110-100)/sqrt(9+4) = 10/sqrt(13) ≈ 2.7735
        assert normalized_error(110, 100, 3, 2) == pytest.approx(10 / math.sqrt(13), rel=1e-9)

    def test_negative_when_below(self):
        en = normalized_error(90, 100, 3, 2)
        assert en < 0
        assert abs(en) == pytest.approx(10 / math.sqrt(13), rel=1e-9)

    def test_zero_uncertainties_returns_zero(self):
        # Convenção do v4: denom=0 ⇒ 0 (proteção contra div by zero)
        assert normalized_error(110, 100, 0, 0) == 0.0


# ==================== IAJ (pesos) ====================
class TestCalculateIAJ:
    def test_perfect_window(self):
        # Janela ideal: Apta, gvf baixo, wlr baixo, desvios zero, gas lift > 0
        dev = {"delta_HC": 0.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.3, 0.2, "Apta", dev, gas_lift=100)
        # Penalidades: -5 (rota inferida). Demais zerados.
        assert iaj == 95

    def test_gas_lift_absent_subtracts_4(self):
        dev = {"delta_HC": 0.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.3, 0.2, "Apta", dev, gas_lift=0)
        # Penalidades: -5 (rota) -4 (gas lift)
        assert iaj == 91

    def test_envelope_restrita_subtracts_18(self):
        dev = {"delta_HC": 0.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.3, 0.2, "Restrita", dev, gas_lift=100)
        # -5 -18
        assert iaj == 77

    def test_envelope_fora_subtracts_42(self):
        dev = {"delta_HC": 0.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.3, 0.2, "Fora do Envelope", dev, gas_lift=100)
        # -5 -42
        assert iaj == 53

    def test_high_gvf_penalty(self):
        dev = {"delta_HC": 0.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.7, 0.2, "Apta", dev, gas_lift=100)
        # -5 -12
        assert iaj == 83

    def test_high_wlr_penalty(self):
        dev = {"delta_HC": 0.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.3, 0.6, "Apta", dev, gas_lift=100)
        # -5 -10
        assert iaj == 85

    def test_hc_dev_over_limit(self):
        dev = {"delta_HC": 6.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.3, 0.2, "Apta", dev, gas_lift=100)
        # -5 -14
        assert iaj == 81

    def test_iaj_floors_at_zero(self):
        dev = {"delta_HC": 100.0, "delta_total": 100.0}
        iaj = calculate_iaj(0.95, 0.95, "Fora do Envelope", dev, gas_lift=0)
        assert iaj == 0

    def test_iaj_ceils_at_hundred(self):
        # Caso hipotético: nenhum decréscimo + rota confirmada (não acontece no MVP,
        # mas confirmando o clamp). Aqui chegamos a 95 no melhor caso real.
        dev = {"delta_HC": 0.0, "delta_total": 0.0}
        iaj = calculate_iaj(0.0, 0.0, "Apta", dev, gas_lift=100)
        assert 0 <= iaj <= 100


# ==================== Alertas ====================
class TestBuildAlerts:
    def _ctx(self, **overrides):
        ctx = {"gvf": 0.3, "wlr": 0.2, "iaj": 90, "enHC": 0.1, "technicalStatus": "Apta"}
        ctx.update(overrides)
        return ctx

    def test_gas_lift_absent_generates_alert(self):
        a = build_alerts({"gasLift": 0}, self._ctx())
        assert any("Gas lift" in x["title"] for x in a)

    def test_route_inferred_always_alert(self):
        a = build_alerts({"gasLift": 10}, self._ctx())
        assert any("Roteamento" in x["title"] for x in a)

    def test_en_above_one_is_bad(self):
        a = build_alerts({"gasLift": 10}, self._ctx(enHC=1.5))
        assert any(x["type"] == "bad" and "normalizado" in x["title"].lower() for x in a)

    def test_en_below_one_is_ok(self):
        a = build_alerts({"gasLift": 10}, self._ctx(enHC=0.5))
        assert any(x["type"] == "ok" for x in a)

    def test_high_gvf_alert(self):
        a = build_alerts({"gasLift": 10}, self._ctx(gvf=0.7))
        assert any("GVF" in x["title"] for x in a)


# ==================== Pipeline analyze completo ====================
class TestAnalyze:
    def test_default_v4_inputs(self):
        i = {"well": "PE-4", "windowLabel": "TEST",
             "pressure": 203.5, "temperature": 67.8,
             "qo": 800.34, "qw": 0.04, "qg": 252796.0,
             "gasLift": 0, "comparisonPair": "Subsea × Topside"}
        r = analyze(i, {}, {})
        # contrato (chaves obrigatórias)
        for k in ("input", "separator", "pvt", "metrics",
                  "balance", "mpfmMasses", "deviations", "alerts", "lineage"):
            assert k in r
        m = r["metrics"]
        assert 0 <= m["gvf"] <= 1
        assert 0 <= m["wlr"] <= 1
        assert m["technicalStatus"] in ("Apta", "Restrita", "Bloqueada")
        assert isinstance(m["iaj"], int)
        # lineage rastreável
        assert r["lineage"]["FCS320_MODE"] == "external_reference"
        assert r["lineage"]["gas_lift_status"] == "not_confirmed"
        assert r["lineage"]["native_pvt_available"] is False

    def test_gas_lift_provided_changes_lineage(self):
        i = {"qo": 100, "qw": 1, "qg": 1000, "gasLift": 50,
             "pressure": 200, "temperature": 60}
        r = analyze(i, {}, {})
        assert r["lineage"]["gas_lift_status"] == "provided"

    def test_factor_suggested_eq_ratio(self):
        i = {"qo": 800.34, "qw": 0.04, "qg": 252796.0, "gasLift": 0,
             "pressure": 200, "temperature": 60}
        r = analyze(i, {}, {})
        ratio = r["balance"]["m_HC_REF"] / r["mpfmMasses"]["m_HC_MPFM"]
        assert r["metrics"]["factorSuggested"] == pytest.approx(ratio, rel=1e-9)

    def test_zero_qo_returns_zero_gor(self):
        r = analyze({"qo": 0, "qw": 1, "qg": 1000,
                     "pressure": 200, "temperature": 60}, {}, {})
        assert r["metrics"]["gor"] == 0.0

    def test_zero_inputs_safe(self):
        r = analyze({}, {}, {})
        assert "metrics" in r


# ==================== Memorial (preservação do layout v4) ====================
class TestBuildMemorial:
    def test_sections_present(self):
        i = {"qo": 800.34, "qw": 0.04, "qg": 252796.0, "gasLift": 0,
             "pressure": 200, "temperature": 60}
        r = analyze(i, {}, {})
        md = build_memorial(r)
        for section in ("Identificação", "Consultor de Aplicabilidade",
                        "Balanço Separador / Referência",
                        "Desvios relativos", "Observações técnicas"):
            assert section in md, f"section missing: {section}"

    def test_memorial_contains_key_quantities(self):
        i = {"qo": 800.34, "qw": 0.04, "qg": 252796.0, "gasLift": 0,
             "pressure": 200, "temperature": 60}
        r = analyze(i, {}, {})
        md = build_memorial(r)
        # Garante que as quantidades-chave foram impressas no memorial
        for token in ("NSV_sep", "V_STO", "m_HC_REF", "m_total_REF",
                      "δ_HC", "δ_total", "En_HC", "GVF", "WLR", "GOR",
                      "IAJ", "Fator sugerido"):
            assert token in md, f"missing memorial token: {token}"

    def test_memorial_declares_limitations(self):
        # Regra do projeto: NÃO declarar equivalência plena com FCS320/PVTPack.
        r = analyze({"pressure": 200, "temperature": 60, "qo": 1, "qw": 0, "qg": 1}, {}, {})
        md = build_memorial(r)
        assert "SF_sep→tank" in md
        assert "Critérios fixos" in md
