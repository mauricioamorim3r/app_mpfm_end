from __future__ import annotations

import sqlite3

from services.measurement_dimensions import (
    ensure_measurement_dimensions,
    load_measurement_dimensions,
    refresh_measurement_dimensions,
)


def _database() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE measurements_curated(
            run_id INTEGER, bank TEXT, metric_name TEXT, tag TEXT
        );
        CREATE VIEW measurements_active AS SELECT * FROM measurements_curated;
        CREATE TABLE measurement_dimensions(
            dimension_kind TEXT NOT NULL,
            dimension_value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(dimension_kind, dimension_value)
        );
        """
    )
    return conn


def test_dimensions_are_backfilled_and_loaded_sorted():
    conn = _database()
    conn.executemany(
        "INSERT INTO measurements_curated VALUES(?,?,?,?)",
        [(1, "B08", "oil", "PE_4"), (1, "B03", "gas", "PE_2")],
    )

    inserted = ensure_measurement_dimensions(conn)
    assert inserted == {"bank": 2, "metric": 2, "tag": 2}
    assert load_measurement_dimensions(conn) == {
        "banks": ["B03", "B08"],
        "metrics": ["gas", "oil"],
        "tags": ["PE_2", "PE_4"],
    }
    assert ensure_measurement_dimensions(conn) == {"bank": 0, "metric": 0, "tag": 0}


def test_dimensions_refresh_only_the_new_run():
    conn = _database()
    conn.execute("INSERT INTO measurements_curated VALUES(1,'B03','gas','PE_2')")
    ensure_measurement_dimensions(conn)
    conn.executemany(
        "INSERT INTO measurements_curated VALUES(?,?,?,?)",
        [(2, "B10", "water", "Riser_P4"), (3, "B15", "oil", "Riser_P5")],
    )

    inserted = refresh_measurement_dimensions(conn, run_id=2)
    assert inserted == {"bank": 1, "metric": 1, "tag": 1}
    loaded = load_measurement_dimensions(conn)
    assert "B10" in loaded["banks"]
    assert "B15" not in loaded["banks"]
