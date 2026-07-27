#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_USERNAME = os.getenv("MPFM_AUTH_USER", "mpfm")
AUTH_PASSWORD = os.getenv("MPFM_AUTH_PASS", "mpfm2024")


def auth_headers() -> dict[str, str]:
    token = base64.b64encode(f"{AUTH_USERNAME}:{AUTH_PASSWORD}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request_json(base_url: str, path: str, method: str = "GET", data: dict | None = None) -> tuple[int, dict]:
    body = None
    headers = auth_headers()
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base_url + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8")
        return resp.status, json.loads(payload) if payload else {}


def request_bytes(base_url: str, path: str) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(base_url + path, headers=auth_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, resp.read(), dict(resp.headers.items())


def wait_for_health(base_url: str, timeout_s: float = 20.0) -> None:
    start = time.time()
    last_error = "server did not start"
    while time.time() - start < timeout_s:
        try:
            status, _ = request_json(base_url, "/api/health")
            if status == 200:
                return
        except Exception as exc:  # pragma: no cover - startup polling
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"healthcheck timeout: {last_error}")


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def xlsx_sheet_names(payload: bytes) -> set[str]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return {sheet.attrib.get("name", "") for sheet in workbook.findall(".//main:sheets/main:sheet", ns)}


def run_isolated_smoke() -> None:
    port = find_free_port()
    with tempfile.TemporaryDirectory(prefix="mpfm_smoke_") as tmp:
        data_dir = Path(tmp) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["MPFM_PORT"] = str(port)
        env["MPFM_DATA_DIR"] = str(data_dir)
        env["MPFM_DB_PATH"] = str(data_dir / "smoke.db")
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            wait_for_health(base_url)

            status, health = request_json(base_url, "/api/health")
            expect(status == 200, "health endpoint failed")
            expect(health.get("status") in {"ok", "degraded"}, "unexpected health status")

            status, prefs = request_json(base_url, "/api/user-prefs")
            expect(status == 200 and "prefs" in prefs, "prefs GET failed")
            status, payload = request_json(
                base_url,
                "/api/user-prefs",
                "POST",
                {"selected_metrics": ["MPFM corr HC (t)"], "summary_icons": {"BOE": "X"}},
            )
            expect(status == 200 and payload.get("ok") is True, "prefs POST failed")
            _, prefs2 = request_json(base_url, "/api/user-prefs")
            expect(prefs2.get("prefs", {}).get("summary_icons", {}).get("BOE") == "X", "prefs persistence failed")

            status, payload = request_json(
                base_url,
                "/api/deadlines",
                "POST",
                {
                    "subject": "Smoke",
                    "category": "Operacao",
                    "start_date": "2026-03-12",
                    "due_date": "2026-03-20",
                    "periodicity": "custom",
                    "periodicity_days": 10,
                    "notes": "smoke",
                    "icon": "P",
                },
            )
            expect(status == 200 and payload.get("id"), "deadline create failed")
            _, deadlines = request_json(base_url, "/api/deadlines")
            expect(len(deadlines.get("items", [])) == 1, "deadline listing failed")
            deadline_id = deadlines["items"][0]["id"]
            request_json(base_url, f"/api/deadlines/{deadline_id}", "DELETE")

            status, payload = request_json(
                base_url,
                "/api/sep-alignments",
                "POST",
                {
                    "production_date": "2026-03-12",
                    "bank": "B99",
                    "mpfm_tag": "PE_TEST",
                    "sep_meter_id": "MTR-1",
                    "sep_tag": "SEP",
                    "notes": "smoke",
                },
            )
            expect(status == 200 and payload.get("ok") is True, "sep alignment create failed")
            _, alignments = request_json(base_url, "/api/sep-alignments?date_from=2026-03-01&date_to=2026-03-31&bank=B99")
            expect(len(alignments.get("rows", [])) == 1, "sep alignment listing failed")
            alignment_id = alignments["rows"][0]["id"]
            request_json(base_url, f"/api/sep-alignments/{alignment_id}", "DELETE")

            status, payload = request_json(
                base_url,
                "/api/measurements",
                "POST",
                {
                    "day_ref": "2026-03-12",
                    "hour_ref": 1,
                    "bank": "B99",
                    "row_kind": "sep",
                    "metric_name": "oil_t",
                    "metric_value": 123.45,
                    "tag": "SEP",
                },
            )
            expect(status == 200 and payload.get("id"), "manual SEP measurement create failed")
            _, sep_rows = request_json(base_url, "/api/sep/data?date_from=2026-03-01&date_to=2026-03-31&unit=B99")
            expect(len(sep_rows.get("rows", [])) == 1, "manual SEP measurement list failed")

            status, payload = request_json(
                base_url,
                "/api/measurements",
                "POST",
                {
                    "day_ref": "2026-03-12",
                    "hour_ref": 1,
                    "bank": "B99",
                    "row_kind": "daily",
                    "metric_name": "MPFM corr HC (t)",
                    "metric_value": 321.0,
                    "tag": "PE_TEST",
                },
            )
            expect(status == 200 and payload.get("id"), "manual MPFM measurement create failed")
            _, mpfm_rows = request_json(
                base_url,
                "/api/ops/mpfm-data?date_from=2026-03-01&date_to=2026-03-31&bank=B99&tag=PE_TEST&row_kind=daily",
            )
            expect(len(mpfm_rows.get("rows", [])) == 1, "manual MPFM measurement list failed")

            _, chart_meta = request_json(base_url, "/api/ops/chart-meta?date_from=2026-03-01&date_to=2026-03-31")
            expect("banks" in chart_meta and "metrics" in chart_meta, "chart meta failed")
            _, chart_presets = request_json(base_url, "/api/ops/chart-presets-meta?date_from=2026-03-01&date_to=2026-03-31")
            expect("focus_pairs" in chart_presets and "compare_metrics" in chart_presets, "chart preset meta failed")
            _, chart_series = request_json(
                base_url,
                "/api/ops/chart-series?date_from=2026-03-01&date_to=2026-03-31&row_kind=daily&bank=B99&tag=PE_TEST&metric=MPFM%20corr%20HC%20(t)",
            )
            expect("labels" in chart_series and "values" in chart_series, "chart series failed")

            status, payload = request_json(
                base_url,
                "/api/pvt-params",
                "POST",
                {
                    "bank": "B99",
                    "tag": "PE_TEST",
                    "fe": 0.9,
                    "rs": 10.0,
                    "rho_oleo_std": 850.0,
                    "rho_gas_std": 1.1,
                    "rho_agua_std": 998.2,
                    "temp_ref_c": 20.0,
                    "pres_ref_bar": 1.01325,
                    "gsv_confirmed": 1,
                    "gor_mode": "fixed",
                    "limite_hc_pct": 5.0,
                    "limite_total_pct": 7.0,
                    "limite_agua_pct": 20.0,
                    "valid_from": "2026-03-01",
                    "valid_to": "2026-03-31",
                    "source": "smoke",
                    "author": "codex",
                    "notes": "ok",
                },
            )
            expect(status == 200 and payload.get("id"), "pvt create failed")

            status, payload = request_json(
                base_url,
                "/api/cards/manual",
                "POST",
                {
                    "production_date": "2026-03-12",
                    "bank": "B99",
                    "title": "Smoke Card",
                    "metric_key": "qa",
                    "value_text": "ok",
                },
            )
            expect(status == 200 and payload.get("id"), "manual card create failed")
            manual_card_id = payload["id"]
            _, cards = request_json(base_url, "/api/cards/daily?date_from=2026-03-12&date_to=2026-03-12&bank=B99")
            expect(
                any(card.get("id") == manual_card_id and card.get("title") == "Smoke Card" for card in cards.get("cards", [])),
                "manual card listing failed",
            )

            _, xml_catalog = request_json(base_url, "/api/xml042/catalog")
            expect("rows" in xml_catalog, "xml042 catalog failed")
            _, xml_candidates = request_json(base_url, "/api/xml042/candidates?month=2026-03")
            expect("rows" in xml_candidates and "summary" in xml_candidates, "xml042 candidates failed")
            status, xml_export, _ = request_bytes(base_url, "/api/xml042/imported-export?month=2026-03")
            expect(status == 200 and len(xml_export) > 100, "xml042 imported export failed")

            export_checks = [
                "/api/export-csv?date_from=2026-03-01&date_to=2026-03-31&bank=B99&tag=PE_TEST&row_kind=daily",
                "/api/export-excel?date_from=2026-03-01&date_to=2026-03-31&bank=B99&tag=PE_TEST&row_kind=daily",
                "/api/export-sep-csv?date_from=2026-03-01&date_to=2026-03-31&unit=B99",
                "/api/export-sep-excel?date_from=2026-03-01&date_to=2026-03-31&unit=B99",
                "/api/export-producao-excel?date_from=2026-03-01&date_to=2026-03-31&include_mpfm=1&include_sep=1&include_cards=1",
            ]
            for path in export_checks:
                status, payload_bytes, _ = request_bytes(base_url, path)
                expect(status == 200 and len(payload_bytes) > 0, f"export failed: {path}")
                if path.startswith("/api/export-producao-excel"):
                    expect("CARDS_RESUMO" not in xlsx_sheet_names(payload_bytes), "production export still includes CARDS_RESUMO")

            print("SMOKE TEST PASSED")
            print(f"Base URL: {base_url}")
            print(f"Data dir: {data_dir}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - safety shutdown
                proc.kill()


def run_external_readonly(base_url: str) -> None:
    checks = [
        "/api/health",
        "/api/dashboard",
        "/api/ops/month-summary",
        "/api/ops/processing-history",
        "/api/ops/mpfm-data?date_from=2026-03-01&date_to=2026-03-31",
        "/api/ops/sep-data?date_from=2026-03-01&date_to=2026-03-31",
        "/api/cards/daily?date_from=2026-03-01&date_to=2026-03-31",
        "/api/cadastro",
        "/api/user-prefs",
        "/api/pvt-params",
        "/api/xml042/catalog",
        "/api/ops/chart-meta",
        "/api/ops/chart-presets-meta",
    ]
    for path in checks:
        status, _ = request_json(base_url, path)
        expect(status == 200, f"failed GET {path}")
    print("READ-ONLY CHECK PASSED")
    print(f"Base URL: {base_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for the MPFM local API.")
    parser.add_argument("--base-url", help="Run read-only checks against an already running server.")
    args = parser.parse_args()
    try:
        if args.base_url:
            run_external_readonly(args.base_url.rstrip("/"))
        else:
            run_isolated_smoke()
    except (AssertionError, RuntimeError, urllib.error.URLError) as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
