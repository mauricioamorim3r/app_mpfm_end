from __future__ import annotations

import sqlite3
from pathlib import Path

from services.painel_operador.daily_checklist_service import DailyChecklistService


def test_same_checklist_hash_is_skipped_before_workbook_scan(tmp_path: Path):
    db_path = tmp_path / "checklist.db"
    source = tmp_path / "checklist.xlsm"
    source.write_bytes(b"same workbook content")
    service = DailyChecklistService()

    seed = sqlite3.connect(db_path)
    service._ensure_tables(seed.cursor())
    seed.execute(
        """
        INSERT INTO painel_operador_daily_checklist_runs(
            source_file, file_hash, imported_at, status, sheet_count,
            selected_sheet_count, row_count, payload_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (str(source), service._file_hash(source), "2026-07-29T10:00:00", "ok", 10, 4, 123, "{}"),
    )
    seed.commit()
    seed.close()

    def fail_scan(*_args, **_kwargs):
        raise AssertionError("duplicate workbook must not be scanned")

    service._scan_workbook = fail_scan
    result = service.import_workbook(lambda: sqlite3.connect(db_path), str(source))

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["reason"] == "same_content"
    assert result["rows_inserted"] == 123

    verify = sqlite3.connect(db_path)
    assert verify.execute("SELECT COUNT(*) FROM painel_operador_daily_checklist_runs").fetchone()[0] == 1
    verify.close()
