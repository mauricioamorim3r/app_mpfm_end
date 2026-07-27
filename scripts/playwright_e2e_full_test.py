"""
playwright_e2e_full_test.py
===========================
Teste end-to-end completo da aplicação MPFM.

Cobertura por bloco:
  [0] Pre-flight: saúde do servidor + validação de dados via API direta
  [1] Navegação: todas as 15 telas carregam sem erro crítico
  [2] Resumo — gráfico de desvio MPFM vs Separador
  [3] Monitoramento MPFM — cards HC % e Total %
  [4] Gráficos — renderização + bandas de desvio HC e Total
  [5] Exportar + download e validação do Excel
  [6] Carregamento automático (Rodar agora)
  [7] Validação de datas de produção

Pré-requisito: servidor rodando em http://localhost:8765
  python server.py

Execução:
  python scripts/playwright_e2e_full_test.py
"""

import urllib.request
import urllib.error
import json
import sys
import os
import re
import time
import tempfile

# ─────────────────────────────── Playwright ───────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("playwright não instalado. Execute: pip install playwright && playwright install chromium")
    sys.exit(1)

BASE = "http://localhost:8765"
API  = f"{BASE}/api"

# ──────────────────────────── Utilidades HTTP ─────────────────────────────────

def _api(path: str, *, method="GET", body=None) -> dict:
    """Chama a API diretamente e retorna JSON."""
    req = urllib.request.Request(f"{API}{path}", method=method)
    if body:
        payload = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
        req.data = payload
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _download_bytes(path: str) -> bytes:
    """Faz download de um arquivo e retorna bytes brutos."""
    url = f"{BASE}{path}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


# ──────────────────────────── Helpers Playwright ─────────────────────────────

def close_settings_modal(page):
    """Fecha o modal de configurações se estiver aberto."""
    try:
        modal = page.locator("#settingsModal")
        if modal.is_visible(timeout=600):
            close_btn = page.locator("#closeSettings")
            if close_btn.count() > 0:
                close_btn.click()
                modal.wait_for(state="hidden", timeout=4000)
    except Exception:
        pass


def nav_to(page, page_name: str, *, timeout=60_000):
    """Navega para uma página clicando no botão de navegação."""
    close_settings_modal(page)
    btn = page.locator(f".navbtn[data-page='{page_name}']")
    btn.wait_for(state="visible", timeout=5000)
    btn.click()
    # aguarda a seção se tornar ativa
    page.wait_for_selector(
        f"#page-{page_name}.active",
        state="attached",
        timeout=timeout,
    )


def ensure_month(page, month: str):
    """Garante que o seletor global de mês está no valor pedido."""
    sel = page.locator("#globalMonth")
    if sel.count() == 0:
        return
    current = sel.input_value()
    if current != month:
        page.evaluate(
            f"""
            const sel = document.getElementById('globalMonth');
            sel.value = '{month}';
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
            """
        )
        time.sleep(0.3)


# ──────────────────────────── Bloco 0: Pre-flight ────────────────────────────

def block0_preflight() -> list[str]:
    """Valida dados via API sem abrir o browser."""
    errs = []

    # 0a. Health
    h = _api("/health")
    if h.get("status") != "ok":
        errs.append(f"[0a] health.status != ok: {h.get('status')}")
    latest_day = h.get("latest_day_ref") or ""
    if not re.match(r"\d{4}-\d{2}-\d{2}", latest_day):
        errs.append(f"[0a] latest_day_ref inválido: {latest_day!r}")
    runs = h.get("counts", {}).get("processing_runs", 0)
    if runs < 1:
        errs.append(f"[0a] nenhuma processing_run registrada (runs={runs})")

    # 0b. Dados de monitoramento MPFM
    month = latest_day[:7] if latest_day else "2026-04"
    mon = _api(f"/ops/mpfm-monitoring?month={month}")
    rows = mon.get("rows", [])
    if len(rows) < 1:
        errs.append(f"[0b] monitoramento sem linhas para {month}")
    else:
        # Verifica campos obrigatórios
        first = rows[0]
        for fld in ("production_date", "hc_deviation_pct", "total_deviation_pct"):
            if fld not in first:
                errs.append(f"[0b] campo '{fld}' ausente nas linhas de monitoramento")
        # Verifica datas válidas
        bad_dates = [r["production_date"] for r in rows if not re.match(r"\d{4}-\d{2}-\d{2}", str(r.get("production_date", "")))]
        if bad_dates:
            errs.append(f"[0b] {len(bad_dates)} linhas com data inválida: ex. {bad_dates[0]}")
        # Datas não devem ser futuras
        from datetime import date as _date
        today_str = _date.today().isoformat()
        future = [r["production_date"] for r in rows if str(r.get("production_date", "")) > today_str]
        if future:
            errs.append(f"[0b] {len(future)} linha(s) com data futura: ex. {future[0]}")

    # 0c. Arquivos Excel disponíveis
    out = _api("/list-outputs")
    files = out.get("files", [])
    if len(files) < 1:
        errs.append("[0c] nenhum arquivo Excel gerado em /api/list-outputs")
    else:
        # Verifica que todos têm nome e tamanho
        broken = [f for f in files if not f.get("name") or not f.get("size_kb")]
        if broken:
            errs.append(f"[0c] {len(broken)} arquivo(s) com name/size_kb ausente")

    return errs


# ──────────────────────────── Bloco 1: Navegação ─────────────────────────────

PAGES_ALL = [
    "resumo", "upload", "mpfm", "monitoramento", "xml042",
    "relatorios", "separador", "cards", "graficos", "alertas",
    "prazos", "cadastro", "recon", "sgmfm", "exportar",
]

def block1_all_pages(page) -> list[str]:
    """Navega para cada uma das 15 telas e verifica carregamento sem crash."""
    errs = []
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    for pg in PAGES_ALL:
        try:
            close_settings_modal(page)
            nav_to(page, pg, timeout=30_000)
            # Seção ativa deve estar visível
            section = page.locator(f"#page-{pg}")
            if not section.is_visible():
                errs.append(f"[1] página '{pg}': seção não ficou visível após navegação")
        except PWTimeout:
            errs.append(f"[1] timeout ao navegar para '{pg}'")
        except Exception as e:
            errs.append(f"[1] erro ao navegar para '{pg}': {e}")

    # Filtra erros de console relevantes (ignora warnings de chart.js lib interna)
    critical_console = [
        m for m in console_errors
        if "Uncaught" in m or "TypeError" in m or "ReferenceError" in m or "SyntaxError" in m
    ]
    if critical_console:
        for m in critical_console[:5]:
            errs.append(f"[1] console error: {m[:200]}")

    return errs


# ──────────────────────────── Bloco 2: Resumo + Desvio Chart ─────────────────

def block2_resumo_chart(page) -> list[str]:
    """Valida que o gráfico de desvio MPFM vs Separador é renderizado."""
    errs = []
    try:
        close_settings_modal(page)
        nav_to(page, "resumo")
        ensure_month(page, "2026-04")

        # Aguarda o gráfico de desvio aparecer (canvas com dados)
        canvas = page.locator("#desvioChart")
        canvas.wait_for(state="visible", timeout=15_000)

        # Wrapper não deve estar escondido
        wrap = page.locator("#desvioChartWrap")
        if wrap.count() > 0:
            wrap_display = page.evaluate("document.getElementById('desvioChartWrap').style.display")
            if wrap_display == "none":
                errs.append("[2] #desvioChartWrap com display:none — gráfico não renderizado")

        # Área de empty não deve estar visível (= gráfico tem dados)
        empty = page.locator("#desvioChartEmpty")
        if empty.count() > 0 and empty.is_visible():
            errs.append("[2] #desvioChartEmpty visível — gráfico sem dados para 2026-04")

        # Título deve mencionar "Desvio"
        title = page.locator("#desvioChartTitle")
        if title.count() > 0:
            title_txt = title.inner_text()
            if "Desvio" not in title_txt and "desvio" not in title_txt:
                errs.append(f"[2] título inesperado: {title_txt!r}")

    except PWTimeout:
        errs.append("[2] timeout aguardando gráfico de desvio")
    except Exception as e:
        errs.append(f"[2] erro inesperado: {e}")
    return errs


# ──────────────────────────── Bloco 3: Monitoramento ─────────────────────────

def block3_monitoramento(page) -> list[str]:
    """Valida cards de monitoramento com desvios HC e Total."""
    errs = []
    try:
        close_settings_modal(page)
        nav_to(page, "monitoramento")

        # Aguarda cards renderizados (auto-carregam ao navegar)
        focus_grid = page.locator("#monitoringFocusPairs")
        focus_grid.wait_for(state="visible", timeout=15_000)

        # Devem aparecer exatamente 3 cards
        cards = page.locator(".monitoring-focus-card")
        cards.first.wait_for(state="visible", timeout=10_000)
        n_cards = cards.count()
        if n_cards < 3:
            errs.append(f"[3] esperado ≥3 focus cards, encontrado {n_cards}")

        # Cada card deve ter badge HC com valor numérico (não "—")
        hc_badges = page.locator(".monitoring-focus-card__stats .badge")
        n_badges = hc_badges.count()
        if n_badges < 6:  # 3 cards × 2 badges (HC + Total) mínimo
            errs.append(f"[3] poucos badges em focus cards: {n_badges} (esperado ≥6)")

        dashes = 0
        for i in range(n_badges):
            txt = hc_badges.nth(i).inner_text()
            if "—" in txt:
                dashes += 1

        # Pelo menos metade dos badges deve ter valor real (não "—")
        if n_badges > 0 and dashes > n_badges // 2:
            errs.append(f"[3] {dashes}/{n_badges} badges mostram '—' em vez de valor numérico")

        # Tabela de monitoramento detalhado (se existir)
        mon_table = page.locator("#monitoringTable, .monitoring-table")
        if mon_table.count() > 0:
            rows_count = page.locator("#monitoringTable tbody tr, .monitoring-table tbody tr").count()
            if rows_count == 0:
                errs.append("[3] tabela de monitoramento vazia")

    except PWTimeout:
        errs.append("[3] timeout aguardando cards de monitoramento")
    except Exception as e:
        errs.append(f"[3] erro inesperado: {e}")
    return errs


# ──────────────────────────── Bloco 4: Gráficos ──────────────────────────────

def block4_graficos(page) -> list[str]:
    """Valida renderização de gráfico e ativação de bandas de desvio HC/Total."""
    errs = []
    try:
        close_settings_modal(page)
        nav_to(page, "graficos")
        ensure_month(page, "2026-04")

        # Aguarda carregamento inicial (loadChartsPage chamado automaticamente)
        time.sleep(1.5)

        # Verifica se o canvas do gráfico existe
        canvas = page.locator("#mainChart")
        canvas.wait_for(state="attached", timeout=10_000)

        # #cEmpty deve estar oculto se há dados (ou o chart não carregou ainda — re-tenta via plot)
        empty_el = page.locator("#cEmpty")
        is_empty_visible = empty_el.is_visible() if empty_el.count() > 0 else False

        if is_empty_visible:
            # Tenta disparar um plot explícito
            plot_btn = page.locator("#cPlot")
            if plot_btn.count() > 0 and plot_btn.is_visible():
                plot_btn.click()
                time.sleep(2.0)
                is_empty_visible = empty_el.is_visible() if empty_el.count() > 0 else False

        # Verifica wrap visível
        wrap = page.locator("#cWrap")
        if wrap.count() > 0:
            wrap_visible = wrap.is_visible()
            if not wrap_visible and not is_empty_visible:
                errs.append("[4] #cWrap oculto e #cEmpty oculto — estado indefinido")
            if wrap_visible:
                # Ativa checkbox desvio HC
                dev_hc = page.locator("#devHC")
                if dev_hc.count() > 0:
                    if not dev_hc.is_checked():
                        dev_hc.click()
                # Ativa checkbox desvio Total
                dev_tot = page.locator("#devTotal")
                if dev_tot.count() > 0:
                    if not dev_tot.is_checked():
                        dev_tot.click()
                # Roda plot com bandas ativas
                plot_btn = page.locator("#cPlot")
                if plot_btn.count() > 0 and plot_btn.is_visible():
                    plot_btn.click()
                    time.sleep(1.5)

                # Chart ainda deve estar visível com as bandas
                if not wrap.is_visible():
                    errs.append("[4] #cWrap sumiu após ativar bandas de desvio")

        elif is_empty_visible:
            errs.append("[4] gráfico principal sem dados para 2026-04")
        else:
            errs.append("[4] #cWrap não encontrado na página de gráficos")

    except PWTimeout:
        errs.append("[4] timeout na tela de gráficos")
    except Exception as e:
        errs.append(f"[4] erro inesperado: {e}")
    return errs


# ──────────────────────────── Bloco 5: Exportar + Excel ──────────────────────

def block5_exportar_excel(page) -> list[str]:
    """Valida lista de exports e download de arquivo Excel."""
    errs = []
    try:
        close_settings_modal(page)
        nav_to(page, "exportar")

        time.sleep(1.0)

        # Tabela de arquivos deve ter linhas
        rows = page.locator("#outputRows tr")
        rows.first.wait_for(state="visible", timeout=10_000)
        n_files = rows.count()
        if n_files == 0:
            errs.append("[5] #outputRows sem linhas — nenhum Excel disponível")
            return errs

        # Coleta links de download visíveis
        links = page.locator("#outputRows a.btn")
        n_links = links.count()
        if n_links == 0:
            errs.append("[5] nenhum botão de download encontrado (todos em rebuilding?)")
        else:
            # Baixa o primeiro arquivo via HTTP direto
            href = links.first.get_attribute("href") or ""
            # href é geralmente /api/download/<filename>
            if not href.startswith("/api"):
                # Tenta extrair da URL completa
                href = "/" + href.split("localhost:8765/", 1)[-1] if "localhost" in href else href

            if href:
                try:
                    data = _download_bytes(href)
                    if len(data) < 10_000:
                        errs.append(f"[5] arquivo muito pequeno: {len(data)} bytes (esperado ≥10 KB)")
                    # Magic bytes de ZIP/XLSX: PK\x03\x04
                    if not data[:4].startswith(b"PK\x03\x04"):
                        errs.append(f"[5] arquivo não começa com magic bytes de ZIP/XLSX: {data[:4]!r}")
                    else:
                        # Verifica que contém pelo menos [Content_Types].xml (padrão OOXML)
                        if b"[Content_Types].xml" not in data[:2048] and b"xl/" not in data[:4096]:
                            errs.append("[5] arquivo parece ZIP mas não é OOXML Excel válido")
                except urllib.error.HTTPError as he:
                    errs.append(f"[5] HTTP {he.code} ao baixar Excel: {href}")
                except Exception as de:
                    errs.append(f"[5] erro ao baixar Excel: {de}")

        # Contexto cards devem mostrar contagem de arquivos > 0
        ctx = page.locator("#outputsContext .outputs-context-card .v")
        if ctx.count() > 0:
            first_val = ctx.first.inner_text().strip()
            try:
                n = int(first_val)
                if n == 0:
                    errs.append("[5] contexto mostra 0 arquivos")
            except ValueError:
                pass  # valor pode ser texto como "—"

    except PWTimeout:
        errs.append("[5] timeout na tela de exportar")
    except Exception as e:
        errs.append(f"[5] erro inesperado: {e}")
    return errs


# ──────────────────────────── Bloco 6: Rodar Agora ───────────────────────────

def block6_rodar_agora(page) -> list[str]:
    """Aciona 'Rodar agora' do primeiro folder via API direta e verifica resultado."""
    errs = []
    try:
        # Obtém folders configurados via API /api/ops/prefs ou user_prefs
        # Primeiro tentamos pegar o folder_id da configuração
        prefs_data = None
        for path in ("/ops/prefs", "/prefs"):
            try:
                prefs_data = _api(path)
                break
            except urllib.error.HTTPError:
                continue

        folder_id = None
        if prefs_data:
            folders = (prefs_data.get("auto_folder_monitor") or {}).get("folders", [])
            if folders:
                folder_id = folders[0].get("id")

        if not folder_id:
            # Fallback: lê diretamente do arquivo de prefs local
            prefs_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "user_prefs.json"
            )
            if os.path.exists(prefs_path):
                with open(prefs_path, encoding="utf-8") as fh:
                    prefs_file = json.load(fh)
                folders = (prefs_file.get("auto_folder_monitor") or {}).get("folders", [])
                if folders:
                    folder_id = folders[0].get("id")

        if not folder_id:
            errs.append("[6] nenhum folder monitorado configurado — 'Rodar agora' não testável")
            return errs

        # Chama run-now via API direta (timeout generoso: servidor é síncrono)
        req = urllib.request.Request(
            f"{API}/auto-folder-monitor/run-now",
            method="POST",
        )
        payload = json.dumps({"folder_id": folder_id}).encode()
        req.add_header("Content-Type", "application/json")
        req.data = payload

        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read())

        results_list = result.get("results") or []
        msg = result.get("message") or ""

        # Deve retornar lista de resultados OU mensagem de conclusão
        if not results_list and not msg:
            errs.append("[6] run-now retornou resposta vazia")

        # Se houver resultados, cada item deve ter label + processed + skipped
        for item in results_list:
            for fld in ("label", "processed", "skipped"):
                if fld not in item:
                    errs.append(f"[6] resultado de run-now sem campo '{fld}': {item}")
                    break

        # Confirma na página que o log do monitor foi atualizado
        close_settings_modal(page)
        nav_to(page, "upload")
        time.sleep(1.5)  # aguarda renderAploadAutoMonitorStatus

        log_el = page.locator("#autoFolderMonitorLog")
        if log_el.count() > 0 and log_el.is_visible():
            log_text = log_el.inner_text()
            if len(log_text.strip()) == 0:
                errs.append("[6] log do monitor está vazio após navegação para upload")

    except urllib.error.HTTPError as he:
        errs.append(f"[6] HTTP {he.code} chamando run-now via API")
    except urllib.error.URLError as ue:
        errs.append(f"[6] timeout/connection ao chamar run-now: {ue}")
    except Exception as e:
        errs.append(f"[6] erro inesperado: {e}")
    return errs


# ──────────────────────────── Bloco 7: Validação de datas ────────────────────

def block7_datas(page) -> list[str]:
    """Valida consistência das datas de produção nos dados carregados."""
    errs = []
    from datetime import date as _date, datetime as _dt

    try:
        # 7a. latest_day_ref do health
        h = _api("/health")
        latest_day = h.get("latest_day_ref") or ""
        if latest_day:
            ld = _dt.strptime(latest_day, "%Y-%m-%d").date()
            if ld > _date.today():
                errs.append(f"[7a] latest_day_ref {latest_day} é data futura")
            if (ld.year < 2020):
                errs.append(f"[7a] latest_day_ref {latest_day} muito antiga")

        # 7b. Datas nas linhas de monitoramento
        month = latest_day[:7] if latest_day else "2026-04"
        mon = _api(f"/ops/mpfm-monitoring?month={month}")
        rows = mon.get("rows", [])

        dates = []
        for r in rows:
            d_str = str(r.get("production_date", ""))
            if re.match(r"\d{4}-\d{2}-\d{2}", d_str):
                dates.append(d_str)

        if not dates:
            errs.append(f"[7b] sem datas válidas nas linhas de monitoramento de {month}")
        else:
            future_dates = [d for d in dates if d > _date.today().isoformat()]
            if future_dates:
                errs.append(f"[7b] {len(future_dates)} data(s) futuras: ex. {future_dates[0]}")

            # Datas devem pertencer ao mês solicitado
            wrong_month = [d for d in dates if not d.startswith(month)]
            if wrong_month:
                errs.append(f"[7b] {len(wrong_month)} data(s) fora do mês {month}: ex. {wrong_month[0]}")

            # Intervalo das datas deve ser coerente (max - min ≤ 31 dias)
            max_d = max(dates)
            min_d = min(dates)
            delta = (_dt.strptime(max_d, "%Y-%m-%d") - _dt.strptime(min_d, "%Y-%m-%d")).days
            if delta > 31:
                errs.append(f"[7b] intervalo de datas igual a {delta} dias (esperado ≤31)")

        # 7c. Datas na UI: tela de resumo mostra mês correto
        close_settings_modal(page)
        nav_to(page, "resumo")
        ensure_month(page, month)
        time.sleep(1.5)

        # Título da página deve estar presente
        title = page.locator("#pageTitle")
        if title.count() > 0:
            if "Resumo" not in title.inner_text():
                errs.append(f"[7c] título da página de resumo inesperado: {title.inner_text()!r}")

    except urllib.error.HTTPError as he:
        errs.append(f"[7] HTTP {he.code} durante validação de datas")
    except Exception as e:
        errs.append(f"[7] erro inesperado: {e}")
    return errs


# ──────────────────────────── Runner principal ────────────────────────────────

BLOCK_LABELS = {
    0: "Pre-flight API",
    1: "Navegação (15 telas)",
    2: "Resumo — desvio chart",
    3: "Monitoramento MPFM",
    4: "Gráficos — bandas HC/Total",
    5: "Exportar + download Excel",
    6: "Carregamento automático",
    7: "Validação de datas",
}


def run_all():
    total_ok = 0
    total_fail = 0
    summary: list[tuple[int, str, list[str]]] = []

    print("\n" + "═" * 72)
    print("  MPFM — Teste E2E Completo")
    print("═" * 72)

    # ── Bloco 0 (sem browser) ─────────────────────────────────────────────────
    bnum = 0
    label = BLOCK_LABELS[bnum]
    print(f"\n[{bnum}] {label}")
    try:
        errs = block0_preflight()
    except Exception as e:
        errs = [f"EXCEPTION: {e}"]
    _display_block(bnum, label, errs)
    summary.append((bnum, label, errs))
    total_ok += int(not errs)
    total_fail += int(bool(errs))

    # ── Blocos 1–7 (com browser) ──────────────────────────────────────────────
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=120)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()

        pg.goto(f"{BASE}/", wait_until="networkidle", timeout=30_000)
        time.sleep(1.5)  # aguarda init JS

        for bnum, fn in [
            (1, block1_all_pages),
            (2, block2_resumo_chart),
            (3, block3_monitoramento),
            (4, block4_graficos),
            (5, block5_exportar_excel),
            (6, block6_rodar_agora),
            (7, block7_datas),
        ]:
            label = BLOCK_LABELS[bnum]
            print(f"\n[{bnum}] {label}")
            try:
                errs = fn(pg)
            except Exception as e:
                errs = [f"EXCEPTION: {e}"]
            _display_block(bnum, label, errs)
            summary.append((bnum, label, errs))
            total_ok += int(not errs)
            total_fail += int(bool(errs))

        ctx.close()
        browser.close()

    # ── Sumário final ─────────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print(f"  RESULTADO FINAL: {total_ok + total_fail} blocos — "
          f"✓ {total_ok} OK   ✗ {total_fail} COM FALHAS")
    print("═" * 72)
    for bnum, label, errs in summary:
        mark = "✓" if not errs else "✗"
        print(f"  {mark}  [{bnum}] {label}")
        for e in errs:
            print(f"       → {e}")
    print()

    return total_fail == 0


def _display_block(bnum, label, errs):
    if not errs:
        print(f"     ✓  OK — {label}")
    else:
        print(f"     ✗  FALHOU — {label} ({len(errs)} issue(s)):")
        for e in errs:
            print(f"         • {e}")


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
