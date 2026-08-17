from __future__ import annotations

import importlib.util
import csv
import sqlite3
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import gerar_base_unica_standalone as base

xml_spec = importlib.util.spec_from_file_location(
    "gerar_xml042_standalone",
    ROOT / "XML042_STANDALONE_PACOTE" / "gerar_xml042_standalone.py",
)
xml042 = importlib.util.module_from_spec(xml_spec)
sys.modules[xml_spec.name] = xml042
xml_spec.loader.exec_module(xml042)


def master_row(**updates):
    row = {column: "" for column in base.BASE_UNICA_COLUMNS}
    row.update(
        {
            "ProductionDate": "2026-08-01",
            "Granularity": "Daily",
            "Origin": "MPFM",
            "SourceType": "PDF",
            "Tipo": "Subsea",
            "MPFM corr HC (t)": 100.0,
            "MPFM corr Total (t)": 100.0,
        }
    )
    row.update(updates)
    return row


class ComparisonTests(unittest.TestCase):
    def test_b05_second_instrument_is_not_summed_into_pe04(self):
        frame = pd.DataFrame(
            [
                master_row(Bank="B05", Tag="18FT1506", Instrumento="18FT1506"),
                master_row(Bank="B05", Tag="18FT1706", Instrumento="18FT1706", **{"MPFM corr HC (t)": 50.0, "MPFM corr Total (t)": 50.0}),
                master_row(Bank="B03", Tag="13FT0367", Instrumento="13FT0367", Tipo="Topside"),
            ]
        )
        rows = base._official_deviation_rows(frame, ["2026-08-01"])
        pair_rows = [row for row in rows if row.get("Banco") == "PE-04 × Riser P5"]
        self.assertTrue(pair_rows)
        self.assertTrue(all(float(row["DesvioNum"]) == 0.0 for row in pair_rows))

    def test_incremental_requires_every_expected_instrument(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "master.xlsx"
            one = pd.DataFrame([master_row(Bank="B05", Instrumento="18FT1506", Tag="18FT1506")])
            one.to_excel(path, sheet_name=base.MASTER_SHEET_NAME, index=False)
            discovered = {"B05": {"2026-08-01": (Path("daily.pdf"), {"tags": ["18FT1506", "18FT1706"]})}}
            self.assertNotIn("2026-08-01", base.loaded_days_in_master(path, ["2026-08-01"], discovered))
            two = pd.concat([one, pd.DataFrame([master_row(Bank="B05", Instrumento="18FT1706", Tag="18FT1706")])])
            two.to_excel(path, sheet_name=base.MASTER_SHEET_NAME, index=False)
            self.assertIn("2026-08-01", base.loaded_days_in_master(path, ["2026-08-01"], discovered))

    def test_one_day_dashboard_falls_back_to_daily(self):
        frame = pd.DataFrame([master_row(Bank="B10", Instrumento="18FT0506", Tag="18FT0506")])
        self.assertEqual(base._dashboard_preferred_granularity(["2026-08-01"], frame), "Daily")

    def test_pe02_uses_actual_riser_p2_instrument(self):
        frame = pd.DataFrame([
            master_row(Bank="B10", Tag="18FT0506", Instrumento="18FT0506", **{"MPFM corr HC (t)": 108.0, "MPFM corr Total (t)": 107.0}),
            master_row(Bank="B08", Tag="Riser_P2", Instrumento="13FT0217", Tipo="Topside", **{"MPFM corr HC (t)": 100.0, "MPFM corr Total (t)": 100.0}),
        ])
        rows = base._official_deviation_rows(frame, ["2026-08-01"])
        pe02 = [row for row in rows if row.get("Banco") == "PE-02 × Riser P2"]
        self.assertTrue(pe02)
        hc = next(row for row in pe02 if row.get("MetricaChave") == "HC")
        total = next(row for row in pe02 if row.get("MetricaChave") == "Total")
        self.assertAlmostEqual(hc["DesvioNum"], 8.0)
        self.assertAlmostEqual(total["DesvioNum"], 7.0)

    def test_deviation_direction_and_low_reference_guard(self):
        self.assertAlmostEqual(base._official_deviation_pct(108.0, 100.0), 8.0)
        self.assertAlmostEqual(base._official_deviation_pct(92.0, 100.0), -8.0)
        self.assertTrue(pd.isna(base._official_deviation_pct(1.0, 0.05)))

    def test_daily_and_hourly_plausibility_baselines_are_separate(self):
        rows = []
        for hour in range(24):
            rows.extend([
                master_row(Hour=hour, Granularity="Hourly", Bank="B05", Tag="18FT1506", Instrumento="18FT1506", **{"MPFM corr HC (t)": 100.0, "MPFM corr Total (t)": 100.0}),
                master_row(Hour=hour, Granularity="Hourly", Bank="B03", Tag="13FT0367", Instrumento="13FT0367", Tipo="Topside", **{"MPFM corr HC (t)": 100.0, "MPFM corr Total (t)": 100.0}),
            ])
        rows.extend([
            master_row(Bank="B05", Tag="18FT1506", Instrumento="18FT1506", **{"MPFM corr HC (t)": 2400.0, "MPFM corr Total (t)": 2400.0}),
            master_row(Bank="B03", Tag="13FT0367", Instrumento="13FT0367", Tipo="Topside", **{"MPFM corr HC (t)": 2400.0, "MPFM corr Total (t)": 2400.0}),
        ])
        official = base._official_deviation_rows(pd.DataFrame(rows), ["2026-08-01"])
        daily = [row for row in official if row.get("Banco") == "PE-04 × Riser P5" and row.get("Granularidade") == "Daily"]
        self.assertTrue(daily)
        self.assertTrue(all(row["Status"] != "DADO SUSPEITO (revisar PDF fonte)" for row in daily))

    def test_separator_frontend_keeps_series_independent(self):
        rows = [
            master_row(Bank="B10", Tag="18FT0506", Instrumento="18FT0506", **{"SEP Status": "Alinhado", "Bancos alinhados": "B10"}),
            master_row(Bank="B08", Tag="13FT0217", Instrumento="13FT0217", Tipo="Topside"),
            master_row(Bank="SEP", Tag="TAG 20VA121", Instrumento="20VA121", Origin="SEP", SourceType="TXT", Tipo="Separador", **{"SEP HC (t)": 100.0, "SEP Total (t)": 100.0}),
        ]
        records = base._separator_frontend_records(pd.DataFrame(rows), ["2026-08-01"])
        self.assertEqual(len(records["mpfm"]), 2)
        self.assertEqual(len(records["sep"]), 1)
        self.assertFalse(any("pair" in row for row in records["mpfm"] + records["sep"]))
        self.assertFalse(any("aligned" in row for row in records["mpfm"]))
        panel = base._interactive_separator_comparison_panel(records, ["2026-08-01"])
        self.assertIn("Exportar comparação para Excel", panel)
        self.assertIn("INDICADOR ACIMA DO LIMITE", panel)
        self.assertNotIn("FORA DO LIMITE", panel)

    def test_mpfm_rows_reject_automatic_separator_merge(self):
        frame = pd.DataFrame([{"Dia": "2026-08-01"}])
        with self.assertRaisesRegex(ValueError, "vinculação automática"):
            base.daily_df_to_rows(frame, {"hc_t": 100.0})

    def test_historical_mpfm_separator_fields_are_cleaned(self):
        row = master_row(Bank="B10", **{"SEP Status": "Alinhado", "Bancos alinhados": "B10", "SEP HC (t)": 100.0, "Desvio HC (%)": 2.0})
        cleaned = base._normalize_master_columns(pd.DataFrame([row])).iloc[0]
        self.assertEqual(cleaned["SEP Status"], "")
        self.assertEqual(cleaned["Bancos alinhados"], "")
        self.assertEqual(cleaned["SEP HC (t)"], "")
        self.assertEqual(cleaned["Desvio HC (%)"], "")

    def test_monthly_cep_uses_entire_selected_month(self):
        frame = pd.DataFrame([
            master_row(ProductionDate="2026-08-01"),
            master_row(ProductionDate="2026-08-20"),
            master_row(ProductionDate="2026-09-01"),
        ])
        self.assertEqual(base._monthly_cep_days(frame, ["2026-08-20"]), ["2026-08-01", "2026-08-20"])

    def test_integrated_dashboard_joins_process_context_without_filling_missing_as_zero(self):
        frame = pd.DataFrame([
            master_row(Bank="B10", Tag="PE_2", Instrumento="18FT0506", **{"Pressão (barg)": 200.0}),
            master_row(Bank="B10", Tag="PE_2", Instrumento="18FT0506", Origin="RECON", SourceType="CALCULATED", **{"Recon Cobertura": "OK (24/24h)", "Recon Horas": "00,01"}),
        ])
        process = pd.DataFrame([{
            "Data": "2026-08-01", "Banco": "B10", "TAG": "PE_2",
            "GVF (%)": 5.25, "WLR (%)": 0.01, "GOR": 0.055,
            "Continuous Phase": "Oil=1.0; Water=0.0",
            "Calculation Mode": "Multiphase=1.0; Auto Switch=0.0",
        }])
        records = base._dashboard_mpfm_records(frame, ["2026-08-01"], process)
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0]["gvf"], 5.25)
        self.assertAlmostEqual(records[0]["gor"], 0.055)
        self.assertEqual(records[0]["reconCoverage"], "OK (24/24h)")
        self.assertIsNone(records[0]["temperature"])

    def test_integrated_dashboard_exposes_only_physical_pair_results(self):
        frame = pd.DataFrame([
            master_row(Bank="B10", Tag="18FT0506", Instrumento="18FT0506", **{"MPFM corr HC (t)": 108.0}),
            master_row(Bank="B08", Tag="Riser_P2", Instrumento="13FT0217", Tipo="Topside"),
        ])
        official = base._official_deviation_rows(frame, ["2026-08-01"])
        panel = base._leadership_dashboard_panel(frame, ["2026-08-01"], pd.DataFrame(), official)
        self.assertIn('id="leadPairSummary"', panel)
        self.assertIn("PE-02 × Riser P2", panel)
        self.assertNotIn("alinhamento automático", panel.lower())

    def test_lineage_panel_keeps_separator_independent(self):
        frame = pd.DataFrame([
            master_row(),
            master_row(Bank="SEP", Origin="SEP", SourceType="TXT", Tipo="Separador"),
        ])
        panel = base._data_lineage_panel(frame, ["2026-08-01"], {"sheets": []})
        self.assertIn("sem alinhamento automático", panel)
        self.assertIn("trava de unicidade", panel)


class XmlZeroProductionTests(unittest.TestCase):
    catalog = [
        {
            "well_operator_name": "PE_2",
            "cod_cadastro_poco": "86316029925",
            "subsea_tag": "18FT0506",
            "bank": "B10",
            "enabled_042": True,
            "active": True,
        }
    ]

    @staticmethod
    def xml_row(oil=0.0, gas=0.0, water=0.0):
        return {
            "__day": "2026-08-01",
            "Bank": "B10",
            "Entity": "PE_2",
            "Tag": "18FT0506",
            "Instrumento": "18FT0506",
            "PVT vol Óleo (m³)": oil,
            "PVT vol Gás (Sm³)": gas,
            "PVT vol Água (m³)": water,
        }

    def test_official_zero_production_is_valid_and_classified(self):
        candidates, rejected = xml042.candidates_from_base(
            pd.DataFrame([self.xml_row()]), self.catalog, {"allow_zero_production": True}
        )
        self.assertFalse(rejected)
        self.assertEqual(candidates[0].production_status, "PRODUCAO_ZERADA_OFICIAL")
        data = xml042.build_xml042_text(candidates[0]).encode("iso-8859-1")
        xml042.validate_xml042_data(data)
        self.assertIn(b"<MED_POTENCIAL_OLEO>0,00000</MED_POTENCIAL_OLEO>", data)

    def test_negative_volume_is_rejected(self):
        candidates, rejected = xml042.candidates_from_base(
            pd.DataFrame([self.xml_row(oil=-1.0)]), self.catalog, {"allow_zero_production": True}
        )
        self.assertFalse(candidates)
        self.assertEqual(rejected[0]["reason"], "volume negativo")

    def test_duplicate_day_well_rows_are_rejected_instead_of_choosing_last(self):
        frame = pd.DataFrame([self.xml_row(oil=1.0), self.xml_row(oil=2.0)])
        candidates, rejected = xml042.candidates_from_base(frame, self.catalog, {"allow_zero_production": True})
        self.assertFalse(candidates)
        self.assertIn("duplicidade crítica dia+poço", rejected[-1]["reason"])

    def test_xml_is_unique_across_output_names_and_overwrite_requests(self):
        candidate = xml042.Candidate(
            production_day="2026-08-01", bank="B10", well_operator_name="PE_2",
            subsea_tag="18FT0506", loop="", oil_sm3=10.0, gas_sm3=1000.0,
            gas_1000sm3=1.0, water_sm3=2.0, oil_t=None, gas_t=None, water_t=None,
            source_file="base.xlsx", production_status="PRODUCAO_POSITIVA_OFICIAL",
            catalog={"cod_cadastro_poco": "86316029925", "well_anp_name": "7-BAC-1-SPS", "subsea_tag": "18FT0506"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {"cnpj8": "04028583", "registry_path": str(root / "control" / "registry.sqlite3"), "overwrite_existing_day_well": True}
            first = xml042.generate_xml_files([candidate], root / "saida_a", config)
            changed = replace(candidate, oil_sm3=999.0)
            second = xml042.generate_xml_files([changed], root / "saida_b", config)
            self.assertEqual(first["generated"], 1)
            self.assertEqual(second["generated"], 0)
            self.assertEqual(second["skipped_existing"], 1)
            self.assertFalse(second["blocked_rows"][0]["same_content"])
            self.assertEqual(len(list((root / "saida_a").glob("042_*.xml"))), 1)
            self.assertEqual(len(list((root / "saida_b").glob("042_*.xml"))), 0)
            with sqlite3.connect(root / "control" / "registry.sqlite3") as connection:
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM xml042_emissions WHERE production_day='2026-08-01' AND cod_cadastro_poco='86316029925'"
                ).fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM xml042_attempts WHERE result='BLOCKED_DUPLICATE'").fetchone()[0], 1)

    def test_cnpj_must_have_exactly_eight_digits(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                xml042.build_anp_filename("123", Path(tmp), set())

    def test_known_history_manifest_has_unique_day_well_keys(self):
        history = ROOT / "XML042_STANDALONE_PACOTE" / "historico_emissoes_xml042.csv"
        with history.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter=";"))
        keys = [(row["production_day"], row["cod_cadastro_poco"]) for row in rows]
        self.assertEqual(len(rows), 9)
        self.assertEqual(len(keys), len(set(keys)))

    def test_historical_xml_directory_blocks_new_emission(self):
        candidate = xml042.Candidate(
            production_day="2026-07-01", bank="B10", well_operator_name="PE_2",
            subsea_tag="18FT0506", loop="", oil_sm3=10.0, gas_sm3=1000.0,
            gas_1000sm3=1.0, water_sm3=2.0, oil_t=None, gas_t=None, water_t=None,
            source_file="base.xlsx", production_status="PRODUCAO_POSITIVA_OFICIAL",
            catalog={"cod_cadastro_poco": "86316029925", "well_anp_name": "7-BAC-1-SPS", "subsea_tag": "18FT0506"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); history = root / "history"; history.mkdir()
            (history / "042_04028583_20260702120000.xml").write_bytes(
                xml042.build_xml042_text(candidate).encode("iso-8859-1")
            )
            result = xml042.generate_xml_files(
                [candidate], root / "output",
                {"cnpj8": "04028583", "registry_path": str(root / "registry.sqlite3"), "history_dirs": [str(history)]},
            )
            self.assertEqual(result["generated"], 0)
            self.assertEqual(result["skipped_existing"], 1)


if __name__ == "__main__":
    unittest.main()
