from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_dashboard_data as radar


class BuildDashboardDataParsingTests(unittest.TestCase):
    def test_as_number_accepts_brazilian_decimal_format(self) -> None:
        self.assertEqual(radar.as_number("1.234,56"), 1234.56)
        self.assertEqual(radar.as_number("pressao -12.5 bar"), -12.5)
        self.assertIsNone(radar.as_number("sem valor"))

    def test_as_number_uses_first_numeric_token_in_multi_value_text(self) -> None:
        self.assertEqual(radar.as_number("pressao 10 bar, temperatura 25 C"), 10)
        self.assertEqual(radar.as_number("range 0-100 bar"), 0)

    def test_fmt_date_normalizes_common_date_inputs(self) -> None:
        self.assertEqual(radar.fmt_date("16/06/2026"), "2026-06-16")
        self.assertEqual(radar.fmt_date("2026-06-16"), "2026-06-16")
        self.assertEqual(radar.fmt_date("2026-06-16T14:30:00"), "2026-06-16")
        self.assertEqual(radar.fmt_date("1/6/2026"), "2026-06-01")
        self.assertEqual(radar.fmt_date("29/02/2024"), "2024-02-29")
        self.assertIsNone(radar.fmt_date("29/02/2023"))
        self.assertIsNone(radar.fmt_date("data invalida"))

    def test_model_csv_helpers_classify_operational_sources(self) -> None:
        source = r"\\AFBRA\BRA\Performance Monitoring\MPM Wells\PE_2|Oil.MeterA.VolumeFlowRate"

        self.assertEqual(radar.classify_model_domain("BAC_SUB Well MPFM monitoring.csv", source), "well_mpfm")
        self.assertEqual(radar.classify_signal_kind(source), "oil")
        self.assertEqual(radar.extract_model_asset(source), "PE_2")
        self.assertEqual(radar.source_label(source), "PE_2|Oil.MeterA.VolumeFlowRate")

    def test_parse_model_timestamp_accepts_pi_export_timestamp(self) -> None:
        parsed = radar.parse_model_timestamp("2026-06-17 22:31:30,966003")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.date().isoformat(), "2026-06-17")

    def test_column_exists_accepts_configured_operator_panel_aliases(self) -> None:
        accepted = {"Início Período Medição": ["Inicio Período Medição"]}

        self.assertTrue(radar.column_exists(["Inicio Período Medição", "Tag do Ponto Medição"], "Início Período Medição", accepted))
        self.assertTrue(radar.column_exists([" Tag do Ponto Medição "], "Tag do Ponto Medição", accepted))
        self.assertFalse(radar.column_exists(["Tag"], "Volume Bruto Corrigido (m3)", accepted))

    def test_classify_parameter_event_maps_density_to_expected_evidence(self) -> None:
        event = radar.classify_parameter_event(
            "Parameter Oil Density was changed from 850 to 851.2 by operador"
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["parameter"], "Oil Density")
        self.assertEqual(event["oldValue"], "850")
        self.assertEqual(event["newValue"], "851.2")
        self.assertEqual(event["actor"], "operador")
        self.assertIn("density_bsw", event["expectedEvidenceTypes"])

    def test_classify_parameter_event_defaults_unknown_parameter_to_pam_limits(self) -> None:
        event = radar.classify_parameter_event(
            "Parameter Custom Setpoint was changed from A to B by engenharia"
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["expectedEvidenceTypes"], ["pam_limits"])


class BuildDashboardDataEvidenceTests(unittest.TestCase):
    def test_parameter_terms_adds_compound_terms(self) -> None:
        terms = radar.parameter_terms("Carbon Dioxide Dynamic Viscosity")

        self.assertIn("carbon dioxide", terms)
        self.assertIn("dynamic viscosity", terms)
        self.assertNotIn("parameter", terms)

    def test_numeric_variants_preserve_scientific_and_decimal_forms(self) -> None:
        variants = radar.numeric_variants("1.2300e+03 kg")

        self.assertIn("1.2300e+03 kg", variants)
        self.assertIn("1230", variants)

    def test_find_content_snippet_reports_near_parameter_and_value(self) -> None:
        text = "Relatorio PVT informa dynamic viscosity revisada para 1.23 conforme boletim."
        snippet, hits, distance = radar.find_content_snippet(
            text,
            ["dynamic viscosity"],
            ["1.23"],
        )

        self.assertIsNotNone(snippet)
        self.assertIn("parametro:dynamic viscosity", hits)
        self.assertIn("valor:1.23", hits)
        self.assertIsNotNone(distance)
        self.assertLess(distance, 80)

    def test_score_evidence_match_prioritizes_type_tag_and_date(self) -> None:
        event = {
            "expectedEvidenceTypes": ["density_bsw"],
            "tags": ["43FT0102"],
            "timestamp": "2026-06-16T12:00:00",
            "system": "PMAE 004",
            "flowComputer": "PMAE 004",
        }
        evidence = {
            "evidenceTypes": ["density_bsw"],
            "tags": ["43FT0102"],
            "date": "2026-06-14",
            "name": "PMAE 004 boletim densidade.pdf",
            "path": "docs/PMAE 004 boletim densidade.pdf",
        }

        score, reasons = radar.score_evidence_match(event, evidence)

        self.assertGreaterEqual(score, 10)
        self.assertIn("tipo esperado", reasons)
        self.assertIn("tag/equipamento", reasons)
        self.assertIn("data proxima", reasons)

    def test_date_distance_days_handles_boundaries_and_invalid_values(self) -> None:
        self.assertEqual(radar.date_distance_days("2026-06-16T12:00:00", "2026-06-09"), 7)
        self.assertEqual(radar.date_distance_days("2026-06-16", "2026-05-02"), 45)
        self.assertEqual(radar.date_distance_days("2026-06-16", "2025-06-11"), 370)
        self.assertIsNone(radar.date_distance_days("2026-06-16", "data invalida"))

    def test_score_evidence_match_returns_zero_without_expected_type_overlap(self) -> None:
        score, reasons = radar.score_evidence_match(
            {"expectedEvidenceTypes": ["density_bsw"], "tags": ["43FT0102"]},
            {"evidenceTypes": ["pam_limits"], "tags": ["43FT0102"]},
        )

        self.assertEqual(score, 0)
        self.assertEqual(reasons, [])


class BuildDashboardDataGovernanceTests(unittest.TestCase):
    def test_stable_id_is_deterministic_for_same_identity(self) -> None:
        first = radar.stable_id("PEND", "2026-06-16", "xml", ["a001"])
        second = radar.stable_id("PEND", "2026-06-16", "xml", ["a001"])

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("PEND-"))

    def test_unique_pending_items_removes_duplicate_ids(self) -> None:
        items = [
            {"id": "PEND-1", "title": "primeira"},
            {"id": "PEND-1", "title": "duplicada"},
            {"id": "PEND-2", "title": "segunda"},
        ]

        unique = radar.unique_pending_items(items)

        self.assertEqual([item["id"] for item in unique], ["PEND-1", "PEND-2"])
        self.assertEqual(unique[0]["title"], "primeira")

    def test_operational_calendar_covers_may_and_june_2026(self) -> None:
        calendar = radar.build_operational_calendar(
            ["2026-06-02"],
            [],
            [{"date": "2026-06-02", "rawOk": True, "anpOk": True}],
            [],
            [],
        )

        self.assertEqual(calendar["start"], "2026-05-01")
        self.assertEqual(calendar["end"], "2026-06-30")
        self.assertEqual(calendar["summary"]["days"], 61)
        self.assertIn("2026-06-02", [day["date"] for day in calendar["days"] if day["loaded"]])

    def test_proposal_confidence_and_risk_follow_governance_rules(self) -> None:
        self.assertEqual(radar.proposal_confidence("confirmed", 7), "alta")
        self.assertEqual(radar.proposal_confidence("supporting", 3), "media")
        self.assertEqual(radar.proposal_confidence("candidate", 9), "baixa")

        self.assertEqual(radar.proposal_risk("Oil Density"), "alto")
        self.assertEqual(radar.proposal_risk("Pressure limit"), "medio")
        self.assertEqual(radar.proposal_risk("Display label"), "baixo")


if __name__ == "__main__":
    unittest.main()
