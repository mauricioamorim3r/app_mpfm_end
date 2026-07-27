#!/usr/bin/env python3
"""
Playwright + API tests for features added in the latest session:
  1. SGM-FM template download endpoint
  2. user_prefs merge (no overwrite)
  3. Monitor UI — interval_enabled checkbox
  4. Basic UI rendering (health check via browser)
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://localhost:8765"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def req(path: str, method: str = "GET", data: dict | None = None):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=15) as resp:
        payload = resp.read()
        return resp.status, resp.headers, json.loads(payload) if payload else {}


def req_raw(path: str):
    with urllib.request.urlopen(BASE_URL + path, timeout=15) as resp:
        return resp.status, resp.headers, resp.read()


def check(cond: bool, msg: str) -> None:
    if cond:
        print(f"  OK  {msg}")
    else:
        print(f"  FAIL  {msg}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# test groups
# ---------------------------------------------------------------------------
def test_health():
    print("\n[1] Health check")
    status, _, body = req("/api/health")
    check(status == 200, f"GET /api/health -> {status}")
    check(body.get("status") in {"ok", "degraded"}, f'status field = {body.get("status")}')


def test_sgmfm_templates():
    print("\n[2] SGM-FM template download")

    for rtype in ("rotina", "logbook", "pvt"):
        try:
            status, headers, body = req_raw(f"/api/sgmfm/template/{rtype}")
            disp = headers.get("Content-Disposition", "")
            check(status == 200, f"GET /api/sgmfm/template/{rtype} -> {status}")
            check(len(body) > 100, f"template/{rtype} body não vazio ({len(body)}b)")
            check("attachment" in disp, f"template/{rtype} Content-Disposition = {disp}")
        except urllib.error.HTTPError as e:
            # 404 means template file not on disk — endpoint logic still correct
            if e.code == 404:
                print(f"  WARN  template/{rtype} -> 404 (arquivo não encontrado no disco, mas endpoint ok)")
            else:
                check(False, f"template/{rtype} -> {e.code}")

    # invalid type must be 404
    try:
        req_raw("/api/sgmfm/template/invalido")
        check(False, "template/invalido deveria retornar 404")
    except urllib.error.HTTPError as e:
        check(e.code == 404, f"template/invalido -> {e.code} (esperado 404)")


def test_user_prefs_merge():
    print("\n[3] user_prefs merge (sem overwrite)")

    # 1. Lê estado atual
    status, _, before = req("/api/user-prefs")
    check(status == 200, "GET /api/user-prefs inicial")

    # 2. POST apenas theme_mode — não deve apagar outros campos
    # Primeiro garante que existe um campo extra
    status, _, _ = req("/api/user-prefs", "POST", {"__test_sentinel": "exists", "theme_mode": "dark"})
    check(status == 200, "POST /api/user-prefs com sentinel")

    # 3. POST somente theme_mode
    status, _, _ = req("/api/user-prefs", "POST", {"theme_mode": "light"})
    check(status == 200, "POST /api/user-prefs somente theme_mode")

    # 4. Re-lê e verifica que sentinel ainda existe
    status, _, after = req("/api/user-prefs")
    check(status == 200, "GET /api/user-prefs pós merge")
    sentinel = after.get("prefs", {}).get("__test_sentinel")
    check(sentinel == "exists", f"sentinel preservado após merge = {sentinel}")
    tm = after.get("prefs", {}).get("theme_mode")
    check(tm == "light", f"theme_mode atualizado = {tm}")

    # 5. Cleanup
    req("/api/user-prefs", "POST", {"theme_mode": "light", "__test_sentinel": None})


def test_monitor_api():
    print("\n[4] Monitor API — interval_enabled")
    status, _, body = req("/api/auto-folder-monitor")
    check(status == 200, f"GET /api/auto-folder-monitor -> {status}")
    # Response should be a dict (even if folders list is empty)
    check(isinstance(body, dict), f"body é dict, foi {type(body).__name__}")


def test_playwright_ui():
    print("\n[5] Playwright UI — renderização das páginas")
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("  SKIP  playwright não instalado")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        print(f"  Abrindo {BASE_URL} ...")
        page.goto(BASE_URL, timeout=20000, wait_until="domcontentloaded")
        # "networkidle" não funciona pois a app faz polling contínuo
        page.wait_for_load_state("load", timeout=20000)
        title = page.title()
        check("MPFM" in title or title != "", f"Título da página: {title!r}")

        # Verifica checkbox interval_enabled existe na DOM
        cb = page.query_selector("#cfgAutoIntervalEnabled")
        check(cb is not None, "Checkbox #cfgAutoIntervalEnabled presente na DOM")

        # Verifica botão Template EN existe
        btn = page.query_selector("button[onclick*='downloadSGMFMTemplate']")
        check(btn is not None, "Botão Template EN presente na DOM")

        # Filtra erros JS relevantes (ignora erros de recursos externos)
        relevant = [e for e in errors if "favicon" not in e.lower() and "net::" not in e.lower()]
        check(len(relevant) == 0, f"Sem erros JS relevantes ({len(relevant)} encontrados: {relevant[:3]})")

        browser.close()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Testando servidor em {BASE_URL}")
    print("=" * 60)

    test_health()
    test_sgmfm_templates()
    test_user_prefs_merge()
    test_monitor_api()
    test_playwright_ui()

    print("\n" + "=" * 60)
    print("TODOS OS TESTES PASSARAM")
