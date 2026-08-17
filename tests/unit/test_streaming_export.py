from __future__ import annotations

from services.streaming_export import iter_pivoted_measurements


def test_pivoted_measurements_stream_one_group_at_a_time():
    rows = iter(
        [
            ("2026-07-01", None, "B03", "L1", "Subsea", "PE_2", "gas", 10.0),
            ("2026-07-01", None, "B03", "L1", "Subsea", "PE_2", "oil", 20.0),
            ("2026-07-01", 1, "B03", "L1", "Subsea", "PE_2", "gas", 1.0),
            ("2026-07-01", 1, "B03", "L1", "Subsea", "PE_2", "oil", 2.0),
        ]
    )

    result = list(iter_pivoted_measurements(rows, ["oil", "gas", "water"]))

    assert result == [
        ["2026-07-01", "", "B03", "L1", "Subsea", "PE_2", 20.0, 10.0, None],
        ["2026-07-01", "01:00", "B03", "L1", "Subsea", "PE_2", 2.0, 1.0, None],
    ]


def test_empty_measurement_cursor_yields_no_rows():
    assert list(iter_pivoted_measurements(iter(()), ["oil"])) == []
