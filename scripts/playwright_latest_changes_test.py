#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8765"
MONTH = "2026-04"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "mpfm_local.db"


def req_json(path: str, method: str = "GET", data: dict | None = None) -> dict:
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
        return json.loads(payload) if payload else {}


def processing_runs_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        return int(conn.execute("select count(*) from processing_runs").fetchone()[0])
    finally:
        conn.close()


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"  OK   {message}")
        return
    print(f"  FAIL {message}")
    sys.exit(1)


def chart_dataset_count(page) -> int:
    return int(page.evaluate(
        """() => {
            const chart = window._desvioChart;
            if (!chart) return -1;
            const data = chart.cfg ? chart.cfg.data : chart.data;
            return Array.isArray(data?.datasets) ? data.datasets.length : -1;
        }"""
    ))


def install_window_open_capture(page) -> None:
    page.evaluate(
        """() => {
            window.__openedReports = [];
            window.__originalOpen = window.__originalOpen || window.open;
            window.open = function(...args) {
                const record = { args, html: '' };
                const fakeWindow = {
                    document: {
                        open() { record.html = ''; },
                        write(chunk) { record.html += String(chunk || ''); },
                        close() { window.__openedReports.push(record); },
                    },
                    close() {},
                    focus() {},
                    print() {},
                };
                return fakeWindow;
            };
        }"""
    )


def reset_window_open_capture(page) -> None:
    page.evaluate("""() => { window.__openedReports = []; }""")


def last_opened_report_html(page) -> str:
    return str(page.evaluate("""() => (window.__openedReports?.at(-1)?.html || '')"""))


def current_chart_payload_info(page) -> dict:
    return page.evaluate(
        """() => ({
            hasPayload: !!((typeof state !== 'undefined' ? state : window.state)?.summaryChart?.currentPayload),
            rowCount: ((typeof state !== 'undefined' ? state : window.state)?.summaryChart?.currentPayload?.tableRows?.length || 0),
            title: ((typeof state !== 'undefined' ? state : window.state)?.summaryChart?.currentPayload?.title || ''),
        })"""
    )


def wait_summary_ready(page) -> None:
    page.wait_for_function(
        """() => {
            const month = document.getElementById('globalMonth');
            const reportButton = document.getElementById('btnDesvioChartReport');
            const anpRadio = document.getElementById('desvioModeAnp');
            return !!month && !!reportButton && !!window._desvioChart && typeof anpRadio?.onchange === 'function';
        }""",
        timeout=60000,
    )


def close_settings_modal(page) -> None:
    if not page.locator("#settingsModal.show").count():
        return
    page.locator("#closeSettings").click()
    page.wait_for_function(
        """() => !document.getElementById('settingsModal')?.classList.contains('show')""",
        timeout=15000,
    )


def ensure_month(page, month: str) -> None:
    current = page.locator("#globalMonth").input_value()
    if current == month:
        return
    page.locator("#globalMonth").select_option(month)
    page.wait_for_timeout(2000)


def find_runtime_folder(snapshot: dict, folder_id: str) -> dict | None:
    for folder in snapshot.get("runtime", {}).get("folders", []):
        if folder.get("id") == folder_id:
            return folder
    return None


def main() -> None:
    print(f"Testando ultimas alteracoes em {BASE_URL}")
    print("=" * 72)

    health = req_json("/api/health")
    check(health.get("status") in {"ok", "degraded"}, f"Health endpoint respondeu com status={health.get('status')!r}")

    before_monitor = req_json("/api/auto-folder-monitor")
    folders = before_monitor.get("config", {}).get("folders", [])
    check(bool(folders), "Monitor de pastas possui pastas cadastradas")
    first_folder = folders[0]
    folder_id = str(first_folder.get("id") or "")
    folder_label = str(first_folder.get("label") or first_folder.get("path") or "pasta sem nome")
    before_runs = processing_runs_count()
    print(f"  Baseline processing_runs: {before_runs}")
    print(f"  Pasta usada no teste manual: {folder_label}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright nao esta instalado neste ambiente Python.")
        sys.exit(1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        js_errors: list[str] = []
        dialogs: list[str] = []
        page.on("console", lambda msg: js_errors.append(msg.text) if msg.type == "error" else None)
        page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        install_window_open_capture(page)

        print("\n[1] Resumo e grafico")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("load", timeout=60000)
        install_window_open_capture(page)
        wait_summary_ready(page)
        ensure_month(page, MONTH)

        check(page.locator("#sumChartShowPointLabels").is_visible(), "Toggle de labels do grafico presente")
        check(page.locator("#btnDesvioChartReport").is_visible(), "Botao de pagina imprimivel do grafico presente")

        page.locator("#desvioModeAnp").click()
        page.wait_for_function(
            """() => {
                const title = document.getElementById('desvioChartTitle')?.textContent || '';
                const bar = document.getElementById('desvioPairFilterBar');
                const count = document.querySelectorAll('#desvioPairFilterList label.summary-pair-chip').length;
                return title.includes('Subsea') && !!bar && bar.hidden === false && count > 0;
            }""",
            timeout=30000,
        )
        chips = page.locator("#desvioPairFilterList label.summary-pair-chip")
        check(chips.count() >= 3, f"Filtro de pares do modo ANP carregou {chips.count()} chips")
        datasets_all = chart_dataset_count(page)
        check(datasets_all >= 6, f"Grafico ANP com todos os pares carregou {datasets_all} datasets")

        page.locator("#btnDesvioPairsNone").click()
        page.wait_for_timeout(1200)
        check("Nenhum par selecionado" in page.locator("#desvioPairFilterMeta").text_content(), "Estado vazio do filtro aparece ao limpar pares")

        first_checkbox = page.locator("#desvioPairFilterList input[type='checkbox']").first
        first_checkbox.check()
        page.wait_for_timeout(2000)
        datasets_one = chart_dataset_count(page)
        check(0 < datasets_one < datasets_all, f"Filtrar para um par reduz datasets ({datasets_all} -> {datasets_one})")

        page.locator("#sumChartShowPointLabels").check()
        page.wait_for_timeout(1000)
        check(page.locator("#sumChartShowPointLabels").is_checked(), "Toggle de labels fica ativo sem erro JS")

        payload_info = current_chart_payload_info(page)
        check(payload_info["hasPayload"], f"Grafico possui payload para relatório ({payload_info['title'] or 'sem titulo'})")
        check(payload_info["rowCount"] > 0, f"Grafico possui linhas na tabela do relatório ({payload_info['rowCount']})")
        dialogs.clear()
        page.evaluate("""() => openDesvioChartReport()""")
        check(not dialogs, f"Sem alertas inesperados ao gerar relatório do gráfico ({len(dialogs)})")

        print("\n[2] Configuracoes e pagina de equacoes")
        page.locator("#btnSettings").click()
        page.locator("#settingsModal.show").wait_for(timeout=15000)
        check(page.locator("#btnOpenEquationGuide").is_visible(), "Botao da pagina imprimivel de equacoes presente")
        reset_window_open_capture(page)
        page.evaluate("""() => openEquationReferencePrintView()""")
        page.wait_for_timeout(1000)
        eq_status = page.locator("#equationGuideStatus").text_content()
        check("Página imprimível aberta" in eq_status or "Pagina imprimivel aberta" in eq_status, "Acionamento da pagina de equacoes atualiza o status da UI")

        print("\n[3] Botao manual do monitor de pastas")
        page.locator("#btnRunAutoMonitorConfigNow").click()
        page.wait_for_function(
            """() => {
                const text = document.getElementById('autoFolderMonitorLog')?.textContent || '';
                return text.includes('Nenhuma pasta ativa selecionada.');
            }""",
            timeout=20000,
        )
        check("Nenhuma pasta ativa selecionada." in page.locator("#autoFolderMonitorLog").text_content(), "Botao global manual respeita regra de pastas ativas")

        folder_row = page.locator(".monitor-folder-row", has_text=folder_label).first
        check(folder_row.count() == 1, f"Linha da pasta '{folder_label}' encontrada nas configuracoes")
        folder_row.get_by_role("button", name="Rodar agora").click()
        page.wait_for_function(
            """(label) => {
                const text = document.getElementById('autoFolderMonitorLog')?.textContent || '';
                return text.includes(label) && (text.includes('processado') || text.includes('ignorado') || text.includes('erro'));
            }""",
            arg=folder_label,
            timeout=120000,
        )
        manual_log = page.locator("#autoFolderMonitorLog").text_content()
        check(folder_label in manual_log, "Execucao manual por pasta gerou retorno no log da UI")

        print("\n[4] Monitoramento MPFM")
        close_settings_modal(page)
        page.locator(".navbtn[data-page='monitoramento']").click()
        page.wait_for_function(
            """() => {
                const host = document.getElementById('monitoringFocusPairs');
                return (host?.children.length || 0) > 0;
            }""",
            timeout=60000,
        )
        focus_text = page.locator("#monitoringFocusPairs").inner_text(timeout=10000)
        check("Referência da razão" in focus_text or "Referencia da razao" in focus_text, "Card de monitoramento mostra a nota da referencia da razao")
        check("Topside" in focus_text, "Card de monitoramento explicita Topside como referencia")

        relevant_js_errors = [
            error for error in js_errors
            if "favicon" not in error.lower() and "net::" not in error.lower()
        ]
        check(not relevant_js_errors, f"Sem erros JS relevantes durante a navegacao ({len(relevant_js_errors)})")

        context.close()
        browser.close()

    after_monitor = req_json("/api/auto-folder-monitor")
    after_runs = processing_runs_count()
    runtime_folder = find_runtime_folder(after_monitor, folder_id)
    check(runtime_folder is not None, "Snapshot do monitor retornou a pasta executada manualmente")
    check(runtime_folder.get("last_action_trigger") == "manual", "Execucao da pasta foi registrada como trigger manual")
    check(not runtime_folder.get("last_error"), f"Execucao manual nao registrou erro ({runtime_folder.get('last_error', '')!r})")

    delta = after_runs - before_runs
    print("\n[5] Resultado da atualizacao manual")
    print(f"  processing_runs antes: {before_runs}")
    print(f"  processing_runs depois: {after_runs}")
    print(f"  delta: {delta}")
    print(f"  ultima acao da pasta: {runtime_folder.get('last_result') or runtime_folder.get('last_scan_result') or 'sem mensagem'}")
    if delta > 0:
        print("  OK   Houve atualizacao real de dados a partir da execucao manual.")
    else:
        print("  INFO Nenhum novo processamento foi gravado; a varredura manual executou, mas nao encontrou arquivo novo para importar ou apenas ignorou duplicados.")

    print("\n" + "=" * 72)
    print("TESTE DIRECIONADO DAS ULTIMAS ALTERACOES CONCLUIDO")


if __name__ == "__main__":
    main()