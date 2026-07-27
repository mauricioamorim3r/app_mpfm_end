"""
Twin MPFM v4 backend regression suite.
Tests all v4 endpoints: health, constants, consultor/analyze, separator-balance,
analyses CRUD, pvt catalog, mpfm xlsx import.
"""
import io
import os
import pytest
import requests
from openpyxl import Workbook

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # Fallback only for local pytest runs; pipeline uses env var
    BASE_URL = "http://localhost:8001"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- health & constants ----------
class TestHealth:
    def test_health(self, session):
        r = session.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert d["app"] == "Twin MPFM"
        assert d["version"] == "4.0.0"

    def test_constants(self, session):
        r = session.get(f"{API}/constants", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # 13 expected keys per spec
        assert len(d) == 13
        assert d["T_STD_C"] == 20.0
        assert d["IAJ_TARGET"] == 60.0
        assert d["FCS320_MODE"] == "external_reference"


# ---------- consultor analyze ----------
class TestConsultorAnalyze:
    def test_analyze_full_payload(self, session):
        payload = {
            "input": {
                "well": "PE-4",
                "windowLabel": "TEST_window_1",
                "pressure": 203.5,
                "temperature": 67.8,
                "qo": 800.34,
                "qw": 0.04,
                "qg": 252796.0,
                "gasLift": 0.0,
                "comparisonPair": "Subsea × Topside",
            },
            "separator": {},
            "pvt": {},
            "persist": True,
        }
        r = session.post(f"{API}/consultor/analyze", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        # metrics shape
        m = d["metrics"]
        for k in ["gvf", "wlr", "gor", "iaj", "technicalStatus",
                  "factorSuggested", "enHC", "envelopeStatus"]:
            assert k in m, f"missing metric {k}"
        # balance shape
        b = d["balance"]
        for k in ["NSV_sep", "V_STO", "m_oil_REF", "m_gas_REF",
                  "m_water_REF", "m_HC_REF", "m_total_REF"]:
            assert k in b, f"missing balance {k}"
        # deviations shape
        dev = d["deviations"]
        for k in ["delta_oil", "delta_gas", "delta_water", "delta_HC", "delta_total"]:
            assert k in dev, f"missing dev {k}"
        assert "mpfmMasses" in d
        assert isinstance(d["alerts"], list) and len(d["alerts"]) >= 1
        assert "lineage" in d
        assert "analysis_id" in d
        # Save to module-level for reuse
        pytest.shared_analysis_id = d["analysis_id"]

    def test_analyze_no_persist(self, session):
        payload = {"persist": False}
        r = session.post(f"{API}/consultor/analyze", json=payload, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "analysis_id" not in d
        assert "metrics" in d


# ---------- separator balance ----------
class TestSeparatorBalance:
    def test_calculate(self, session):
        r = session.post(f"{API}/separator-balance/calculate", json={}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["NSV_sep", "V_STO", "m_HC_REF", "m_oil_REF",
                  "m_gas_REF", "m_water_REF", "m_total_REF"]:
            assert k in d
        # NSV_sep = GSV_sep * (1 - BSW/100); GSV_sep=8.12*24=194.88; BSW=0.08
        expected_nsv = 8.12 * 24 * (1 - 0.08 / 100)
        assert abs(d["NSV_sep"] - expected_nsv) < 1e-3


# ---------- analyses list/detail/memorial ----------
class TestAnalyses:
    def test_list(self, session):
        r = session.get(f"{API}/analyses", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        item = items[0]
        for k in ["id", "created_at", "well", "window_label",
                  "comparison_pair", "status", "gvf", "wlr", "gor",
                  "iaj", "factor_suggested"]:
            assert k in item, f"missing list field {k}"

    def test_detail(self, session):
        aid = getattr(pytest, "shared_analysis_id", None)
        assert aid, "analyze test must run first"
        r = session.get(f"{API}/analyses/{aid}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "metrics" in d
        assert "balance" in d

    def test_memorial(self, session):
        aid = getattr(pytest, "shared_analysis_id", None)
        assert aid
        r = session.get(f"{API}/analyses/{aid}/memorial", timeout=15)
        assert r.status_code == 200
        assert "text/plain" in r.headers.get("content-type", "")
        text = r.text
        for section in ["Identificação", "Consultor de Aplicabilidade",
                        "Balanço Separador", "Desvios relativos",
                        "Observações técnicas"]:
            assert section in text, f"missing memorial section: {section}"

    def test_detail_404(self, session):
        r = session.get(f"{API}/analyses/nope-xxx", timeout=10)
        assert r.status_code == 404


# ---------- PVT catalog ----------
class TestPVT:
    def test_catalog_initial(self, session):
        r = session.get(f"{API}/pvt/catalog", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_and_list(self, session):
        body = {
            "fluidId": "TEST_PE-4 / PW-104",
            "source": "SLB",
            "eos": "SRK + Peneloux",
            "SF_sep_tank": 0.87,
            "deltaRs_sep_tank": 62.11,
            "rho_oil_STO": 861.0,
            "rho_gas_std": 0.899,
            "status": "validated_tabulated",
        }
        r = session.post(f"{API}/pvt/catalog", json=body, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "created"
        assert "id" in d

        r2 = session.get(f"{API}/pvt/catalog", timeout=10)
        items = r2.json()
        found = [it for it in items if it.get("fluid_id") == body["fluidId"]]
        assert found, "created PVT not found in catalog"


# ---------- MPFM xlsx import ----------
class TestImport:
    def _make_xlsx(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["ProductionDate", "Entity", "Tag", "Tipo", "Bank", "Loop", "Value"])
        ws.append(["2026-01-01", "PE-4", "FT-101", "Flow", "B1", "L1", 800.5])
        ws.append(["2026-01-02", "PE-4", "FT-101", "Flow", "B1", "L1", 810.5])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    def test_upload_valid(self, session):
        buf = self._make_xlsx()
        files = {"file": ("TEST_mpfm.xlsx", buf,
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        # Remove Content-Type header so multipart boundary is set automatically
        r = requests.post(f"{API}/import/mpfm-xlsx", files=files, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["filename"] == "TEST_mpfm.xlsx"
        assert d["records_imported"] >= 2
        assert isinstance(d["sample"], list)
        # Novos campos de robustez (Correção #4)
        assert d["records_rejected"] == 0
        assert d["rejected"] == []

    def test_upload_invalid_ext(self, session):
        files = {"file": ("bad.txt", io.BytesIO(b"hello"), "text/plain")}
        r = requests.post(f"{API}/import/mpfm-xlsx", files=files, timeout=10)
        assert r.status_code == 400

    def test_upload_empty_xlsx(self, session):
        # Arquivo vazio com extensão .xlsx deve devolver 400 e não 500
        files = {"file": ("empty.xlsx", io.BytesIO(b""), "application/vnd.openxmlformats")}
        r = requests.post(f"{API}/import/mpfm-xlsx", files=files, timeout=10)
        assert r.status_code == 400

    def test_upload_corrupt_xlsx(self, session):
        # Conteúdo inválido com extensão correta deve devolver 400
        files = {"file": ("corrupt.xlsx", io.BytesIO(b"not really a zip"), "application/vnd.openxmlformats")}
        r = requests.post(f"{API}/import/mpfm-xlsx", files=files, timeout=10)
        assert r.status_code == 400

    def test_list_records(self, session):
        r = session.get(f"{API}/import/mpfm-records", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestValidation:
    """Correção #4 — validação Pydantic."""

    def test_negative_pressure_returns_422(self, session):
        payload = {"input": {"pressure": -10, "qo": 1, "qw": 0, "qg": 1}}
        r = session.post(f"{API}/consultor/analyze", json=payload, timeout=15)
        assert r.status_code == 422

    def test_negative_qo_returns_422(self, session):
        payload = {"input": {"pressure": 100, "qo": -1, "qw": 0, "qg": 1}}
        r = session.post(f"{API}/consultor/analyze", json=payload, timeout=15)
        assert r.status_code == 422

    def test_bsw_above_100_returns_422(self, session):
        payload = {"separator": {"BSW": 120.0}}
        r = session.post(f"{API}/consultor/analyze", json=payload, timeout=15)
        assert r.status_code == 422

    def test_zero_sf_sep_tank_returns_422(self, session):
        # SF deve ser > 0 (gt=0)
        payload = {"separator": {"SF_sep_tank": 0}}
        r = session.post(f"{API}/consultor/analyze", json=payload, timeout=15)
        assert r.status_code == 422
