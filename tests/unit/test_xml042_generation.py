import sqlite3

from repositories.xml042.xml042_repository import Xml042Repository
from services.xml042.xml042_service import generate_xml042_document


class FakeXml042Repo:
    def __init__(self):
        self.rows = []

    def get_document_by_key(self, production_day, cod_cadastro_poco):
        return None

    def save_document(self, payload):
        self.rows.append(payload)
        return len(self.rows)


def _candidate(day, code):
    return {
        "eligible": True,
        "approved": True,
        "production_day": day,
        "bank": "B03",
        "well_operator_name": "PE_2",
        "subsea_tag": "18FT0506",
        "oil_sm3": 1.2,
        "gas_sm3": 3000.0,
        "gas_1000sm3": 3.0,
        "water_sm3": 0.4,
        "catalog": {
            "cod_cadastro_poco": code,
            "well_anp_name": "7-BAC-1-SPS",
        },
    }


def test_xml042_generation_filename_uses_anp_pattern_and_stays_unique(tmp_path):
    repo = FakeXml042Repo()

    first = generate_xml042_document(
        repo,
        candidate=_candidate("2026-07-23", "86316029925"),
        output_dir=tmp_path,
        cnpj8="04028583",
        author="test",
        target_dir=tmp_path / "target",
    )
    second = generate_xml042_document(
        repo,
        candidate=_candidate("2026-07-23", "86316030256"),
        output_dir=tmp_path,
        cnpj8="04028583",
        author="test",
        target_dir=tmp_path / "target",
    )

    assert first["filename"] != second["filename"]
    assert first["filename"].startswith("042_04028583_")
    assert second["filename"].startswith("042_04028583_")
    assert first["filename"].endswith(".xml")
    assert second["filename"].endswith(".xml")
    assert len(first["filename"]) == len("042_04028583_20260723000000.xml")
    assert len(second["filename"]) == len("042_04028583_20260723000000.xml")
    assert "86316029925" not in first["filename"]
    assert "86316030256" not in second["filename"]
    assert (tmp_path / "xml042" / first["filename"]).exists()
    assert (tmp_path / "xml042" / second["filename"]).exists()


def test_xml042_candidates_prefer_pvt_volume_at_20c():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE measurements_curated (
            day_ref TEXT,
            bank TEXT,
            tag TEXT,
            instrument TEXT,
            loop TEXT,
            tipo TEXT,
            row_kind TEXT,
            hour_ref INTEGER,
            metric_name TEXT,
            metric_value REAL
        )
        """
    )
    base = {
        "day_ref": "2026-08-27",
        "bank": "B10",
        "tag": "PE_2",
        "instrument": "18FT0506",
        "loop": "",
        "tipo": "Subsea",
        "row_kind": "daily",
        "hour_ref": None,
    }
    metrics = {
        "PVT vol Óleo (m³)": 111.0,
        "PVT @20 vol Óleo (m³)": 222.0,
        "PVT vol Gás (Sm³)": 333000.0,
        "PVT @20 vol Gás (Sm³)": 444000.0,
        "PVT vol Água (m³)": 5.0,
        "PVT @20 vol Água (m³)": 6.0,
    }
    for metric_name, metric_value in metrics.items():
        conn.execute(
            """
            INSERT INTO measurements_curated (
                day_ref, bank, tag, instrument, loop, tipo, row_kind, hour_ref, metric_name, metric_value
            ) VALUES (:day_ref, :bank, :tag, :instrument, :loop, :tipo, :row_kind, :hour_ref, :metric_name, :metric_value)
            """,
            {**base, "metric_name": metric_name, "metric_value": metric_value},
        )
    conn.commit()

    repo = Xml042Repository(lambda: conn, lambda value: str(value or "").strip().upper())
    rows = repo.list_daily_subsea_candidates("2026-08-01", "2026-08-31")

    assert len(rows) == 1
    assert rows[0]["oil_sm3"] == 222.0
    assert rows[0]["gas_sm3"] == 444000.0
    assert rows[0]["water_sm3"] == 6.0
