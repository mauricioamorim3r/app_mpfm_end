from pathlib import Path

from mpfm_engine import parse_sep_txt_set


def test_parse_sep_txt_set_recovers_concatenated_mass_token(tmp_path: Path):
    oil_path = tmp_path / "Run_24Hours_TEST_OLEO.txt"
    gas_path = tmp_path / "Run_24Hours_TEST_GAS.txt"
    water_path = tmp_path / "Run_24Hours_TEST_AGUA.txt"

    oil_path.write_text(
        "1 100 25 0 0 0 12.50000 13.50000 11243.3130010805.39600 0 0 0 0\n",
        encoding="utf-8",
    )
    gas_path.write_text(
        "1 0 0 0 0 0 0 2500 0 0 0\n",
        encoding="utf-8",
    )
    water_path.write_text(
        "1 100 25 0 0 0 8.50000 9.50000 123.45000 0 0 0 0\n",
        encoding="utf-8",
    )

    trace_events = []
    result = parse_sep_txt_set(
        oil_path,
        gas_path,
        water_path,
        density_sim=790.78,
        trace_hook=trace_events.append,
    )

    assert 1 in result
    assert result[1]["oil_t"] == 11243.313
    assert result[1]["gas_t"] == 2.5
    assert result[1]["water_t"] == 123.45
    assert trace_events
    assert trace_events[0]["code"] == "sep_parser_recovered_token"
    assert trace_events[0]["field_name"] == "mass_t"
    assert trace_events[0]["raw_token"] == "11243.3130010805.39600"
    assert trace_events[0]["recovered_token"] == "11243.31300"
    assert trace_events[0]["overflow_token"] == "10805.39600"