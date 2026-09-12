import threading
from pathlib import Path

import server


def test_monthly_refresh_coalesces_updates_arriving_during_build(tmp_path, monkeypatch):
    output = tmp_path / "MPFM_AGO_2026.xlsx"
    started = threading.Event()
    release = threading.Event()
    calls = []

    def fake_build(path: Path, year: str, month: str):
        calls.append((year, month))
        if len(calls) == 1:
            started.set()
            assert release.wait(timeout=5)
        Path(path).write_bytes(str(len(calls)).encode())

    monkeypatch.setattr(server, "build_monthly_base_unica", fake_build)
    monkeypatch.setattr(server, "_monthly_refresh_tmp_dir", tmp_path / "refresh")
    server._monthly_refresh_guard.clear()
    server._monthly_refresh_pending.clear()
    server._monthly_refresh_threads.clear()

    assert server.schedule_monthly_base_unica(output, "2026", "08")
    assert started.wait(timeout=5)
    assert server.schedule_monthly_base_unica(output, "2026", "08")
    release.set()

    key = str(output.resolve())
    server._monthly_refresh_threads[key].join(timeout=10)
    assert calls == [("2026", "08"), ("2026", "08")]
    assert output.read_bytes() == b"2"
    assert not server.is_monthly_workbook_rebuilding(output)
