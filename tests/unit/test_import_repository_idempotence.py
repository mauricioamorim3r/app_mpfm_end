import sqlite3
from pathlib import Path

from repositories.importing.import_repository import ImportRepository


def _connect(path: Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def test_store_sheet_rows_replaces_same_measurement_window(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = _connect(db_path)
    conn.execute(
        """
        CREATE TABLE measurements_curated (
            id INTEGER PRIMARY KEY,
            run_id INTEGER,
            source_file TEXT,
            excel_file TEXT,
            sheet_name TEXT,
            row_kind TEXT,
            day_ref TEXT,
            hour_ref INTEGER,
            bank TEXT,
            loop TEXT,
            tipo TEXT,
            tag TEXT,
            instrument TEXT,
            metric_name TEXT,
            metric_value REAL,
            metric_unit TEXT,
            is_official INTEGER,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    repo = ImportRepository(lambda: _connect(db_path), lambda _: "", lambda _: "t")
    row = {
        "Dia ref.": "2026-08-01",
        "Hora": 0,
        "Bank": "B03",
        "Loop": "North",
        "Tipo": "Topside",
        "TAG": "Riser_P5",
        "Instrumento": "13FT0367",
        "MPFM corr Óleo (t)": 1.0,
    }

    repo.store_sheet_rows(1, "aug.xlsx", "HOURLY_B03_01_08", [row])
    row["MPFM corr Óleo (t)"] = 2.0
    repo.store_sheet_rows(2, "aug.xlsx", "HOURLY_B03_01_08", [row])

    conn = _connect(db_path)
    values = conn.execute(
        "SELECT run_id, metric_value FROM measurements_curated"
    ).fetchall()
    conn.close()
    assert [tuple(item) for item in values] == [(2, 2.0)]
