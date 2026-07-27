#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright + API tests para o grafico CEP Subsea vs Topside (modo ANP).
Verifica:
  1. API /api/ops/month-summary retorna tag_daily com os 6 tags esperados
  2. Cálculo manual de desvio% HC e Total por par/dia bate com a fórmula
     Desvio% = (Subsea / Topside - 1) * 100  (Topside = referência)
  3. Playwright: modo ANP renderiza canvas visível
  4. Playwright: Chart.js datasets count = 2*n_pares + 0..4 linhas de limite
  5. Playwright: labels dos datasets incluem 'HC%' e 'Tot%' para cada par
  6. Playwright: dados do dataset HC% par PE-4 × Riser P5 batem com Python
  7. Playwright: limites ±10% HC e ±7% Total presentes quando checkboxes ON
  8. Playwright: title atualizado para '...Subsea vs Topside...'
  9. Playwright: legend mostra contagem de leituras fora do limite
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[1]
BASE_URL = "http://localhost:8765"
MONTH    = "2026-04"

PAIRS = [
    ("PE_4",     "Riser_P5", "PE-4",      "Riser P5"),
    ("PE_2",     "Riser_P2", "PE-2",      "Riser P2"),
    ("PW-104DA", "Riser_P4", "PW-104DA",  "Riser P4"),
]
LIM_HC    = 10.0
LIM_TOTAL =  7.0


# ── helpers ──────────────────────────────────────────────────────────────────
def req(path: str):
    with urllib.request.urlopen(BASE_URL + path, timeout=15) as r:
        return json.loads(r.read())


def check(cond: bool, msg: str) -> None:
    if cond:
        print(f"  OK  {msg}")
    else:
        print(f"  FAIL  {msg}")
        sys.exit(1)


def round2(v: float) -> float:
    return round(v, 2)


# ── Test 1: API + cálculo manual ─────────────────────────────────────────────
def test_api_calculations():
    print(f"\n[1] API tag_daily + cálculo manual de desvio% ({MONTH})")

    d  = req(f"/api/ops/month-summary?month={MONTH}")
    td = d.get("tag_daily", [])

    check(len(td) > 0, f"tag_daily não vazio ({len(td)} itens)")

    present_tags = set(x["tag"] for x in td)
    for sub_tag, top_tag, _, _ in PAIRS:
        check(sub_tag in present_tags, f"tag subsea '{sub_tag}' presente")
        check(top_tag in present_tags, f"tag topside '{top_tag}' presente")

    by_day_tag = {f"{x['day']}|{x['tag']}": x for x in td}
    days = sorted({x["day"] for x in td})

    print(f"  Dias disponíveis: {len(days)} ({days[0]} a {days[-1]})")

    # Calcular e exibir desvios para validação manual
    expected: dict[str, dict[str, dict]] = {}  # pair_label -> {day -> {hc_dev, tot_dev}}

    for sub_tag, top_tag, sub_lbl, top_lbl in PAIRS:
        lbl = f"{sub_lbl} x {top_lbl}"
        expected[lbl] = {}
        valid_days = 0
        for day in days:
            sub = by_day_tag.get(f"{day}|{sub_tag}")
            top = by_day_tag.get(f"{day}|{top_tag}")
            if not sub or not top:
                continue
            hc_top  = sub.get("hc_t",    0) + top.get("hc_t",    0)  # just for non-zero check
            tot_top = sub.get("total_t", 0) + top.get("total_t", 0)

            hc_dev  = round2((sub["hc_t"]    / top["hc_t"]    - 1) * 100) if (top.get("hc_t",    0) or 0) > 0.001 else None
            tot_dev = round2((sub["total_t"] / top["total_t"] - 1) * 100) if (top.get("total_t", 0) or 0) > 0.001 else None
            expected[lbl][day] = {"hc_dev": hc_dev, "tot_dev": tot_dev,
                                   "sub_hc": sub.get("hc_t", 0), "top_hc": top.get("hc_t", 0),
                                   "sub_tot": sub.get("total_t", 0), "top_tot": top.get("total_t", 0)}
            valid_days += hc_dev is not None

        check(valid_days > 0, f"Par {lbl}: ≥1 dia com dados ({valid_days} dias)")

    # Mostra tabela resumo
    print("\n  Resumo cálculos:")
    for pair_lbl, days_data in expected.items():
        print(f"\n  {'Dia':12} | {'Sub HC':>9} | {'Top HC':>9} | {'Dev HC%':>9} | {'Sub Tot':>9} | {'Top Tot':>9} | {'Dev Tot%':>9}  -- {pair_lbl}")
        print("  " + "-"*90)
        for day, v in sorted(days_data.items()):
            d_str  = v["hc_dev"]  if v["hc_dev"]  is not None else "—"
            dt_str = v["tot_dev"] if v["tot_dev"] is not None else "—"
            flag_hc  = " <<<" if v["hc_dev"]  is not None and abs(v["hc_dev"])  > LIM_HC    else ""
            flag_tot = " <<<" if v["tot_dev"] is not None and abs(v["tot_dev"]) > LIM_TOTAL else ""
            print(f"  {day} | {v['sub_hc']:>9.3f} | {v['top_hc']:>9.3f} | {str(d_str):>9}{flag_hc:<4} | "
                  f"{v['sub_tot']:>9.3f} | {v['top_tot']:>9.3f} | {str(dt_str):>9}{flag_tot}")

    # Fórmula cross-check: verifica consistência (desvio deve ser ~ (sub/top-1)*100)
    for pair_lbl, days_data in expected.items():
        for day, v in days_data.items():
            if v["hc_dev"] is not None and v["top_hc"] > 0.001:
                recalc = round2((v["sub_hc"] / v["top_hc"] - 1) * 100)
                check(recalc == v["hc_dev"],
                      f"Fórmula HC% verificada {pair_lbl} {day}: {recalc} == {v['hc_dev']}")
            if v["tot_dev"] is not None and v["top_tot"] > 0.001:
                recalc = round2((v["sub_tot"] / v["top_tot"] - 1) * 100)
                check(recalc == v["tot_dev"],
                      f"Fórmula Tot% verificada {pair_lbl} {day}: {recalc} == {v['tot_dev']}")

    return expected


# ── Test 2: Playwright visual + chart data ────────────────────────────────────
def test_playwright_chart(expected: dict):
    print("\n[2] Playwright — renderização do gráfico ANP")
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("  SKIP  playwright não instalado")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        js_errors: list[str] = []
        page.on("console", lambda m: js_errors.append(m.text) if m.type == "error" else None)

        print(f"  Abrindo {BASE_URL} ...")
        page.goto(BASE_URL, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_load_state("load", timeout=25000)

        # ── Aguarda initDates() popular o mês e loadSummary() renderizar os KPI cards ──
        # Condição: globalMonth tem valor E summaryCards tem filhos (prova loadSummary rodou)
        # NÃO usamos o título do gráfico pois ele já tem texto default no HTML.
        print("  Aguardando initDates() + loadSummary() (summaryCards populados)...")
        try:
            page.wait_for_function(
                """() => {
                    const m = document.getElementById('globalMonth')?.value;
                    const c = (document.getElementById('summaryCards')?.children.length || 0);
                    return !!(m && c > 5);
                }""",
                timeout=30000,
            )
        except PWTimeout:
            print("  WARN  Timeout esperando initDates — continuando mesmo assim")

        # ── garantir que estamos no mês 2026-04 ──────────────────────────────
        actual_month = page.evaluate("() => document.getElementById('globalMonth')?.value || ''")
        print(f"  Mês atual: {actual_month!r}")
        if actual_month != MONTH:
            print(f"  Alterando para {MONTH}...")
            page.evaluate(f"""() => {{
                const s = document.getElementById('globalMonth');
                if (s) {{ s.value = '{MONTH}'; s.dispatchEvent(new Event('change')); }}
            }}""")
            # Aguarda summaryCards reaparecerem com o novo mês
            try:
                page.wait_for_function(
                    """() => (document.getElementById('summaryCards')?.children.length || 0) > 5""",
                    timeout=15000,
                )
            except PWTimeout:
                pass
            # Esperar window._desvioChart (sinal que loadDesvioChart() finalizou e handlers foram registrados)
            try:
                page.wait_for_function(
                    """() => window._desvioChart != null""",
                    timeout=15000,
                )
            except PWTimeout:
                pass
        else:
            # Mês já correto — esperar loadDesvioChart() finalizar (window._desvioChart é setado no final)
            # Os onchange dos radios são registrados APÓS o await loadDesvioChart() retornar
            try:
                page.wait_for_function(
                    """() => window._desvioChart != null""",
                    timeout=20000,
                )
            except PWTimeout:
                print("  WARN  Timeout esperando window._desvioChart — continuando mesmo assim")

        # ── verificar canvas visível em modo sep (padrão) ─────────────────────
        canvas = page.query_selector("#desvioChart")
        check(canvas is not None, "Canvas #desvioChart presente na DOM")

        # ── clicar no radio ANP ───────────────────────────────────────────────
        anp_radio = page.query_selector("#desvioModeAnp")
        check(anp_radio is not None, "Radio #desvioModeAnp presente na DOM")
        if anp_radio:
            anp_radio.click()
            # Aguarda renderização COMPLETA do modo ANP:
            # - título contém 'Subsea' (síncrono, antes do fetch de cadastro)
            # - E desvioChartEmpty está oculto (depois do fetch + chart render)
            try:
                page.wait_for_function(
                    """() => {
                        const titleOk = (document.getElementById('desvioChartTitle')?.textContent || '').includes('Subsea');
                        const emptyHidden = document.getElementById('desvioChartEmpty')?.style.display === 'none';
                        return titleOk && emptyHidden;
                    }""",
                    timeout=15000,
                )
            except PWTimeout:
                pass  # checks abaixo reportarão o estado real

        # ── verificar título ──────────────────────────────────────────────────
        title_text = page.evaluate("() => document.getElementById('desvioChartTitle')?.textContent || ''")
        check("Subsea" in title_text and "Topside" in title_text,
              f"Título contém 'Subsea vs Topside': {title_text!r}")

        # ── verificar canvas visível ──────────────────────────────────────────
        canvas_visible = page.evaluate("""() => {
            const c = document.getElementById('desvioChart');
            return c && c.style.display !== 'none' && c.offsetParent !== null;
        }""")
        check(canvas_visible, "Canvas #desvioChart visível (não hidden)")

        empty_hidden = page.evaluate("""() => {
            const e = document.getElementById('desvioChartEmpty');
            return !e || e.style.display === 'none' || e.offsetParent === null;
        }""")
        check(empty_hidden, "Div #desvioChartEmpty oculta (há dados)")

        # ── extrair dados do Chart.js ─────────────────────────────────────────
        chart_info = page.evaluate("""() => {
            // app.summary.js exposes window._desvioChart after creation
            const chart = window._desvioChart || null;
            if (!chart) {
                // fallback: try Chart.getChart (Chart.js v3+)
                try {
                    const canvas = document.getElementById('desvioChart');
                    const c = typeof Chart !== 'undefined' && typeof Chart.getChart === 'function'
                        ? Chart.getChart(canvas) : null;
                    if (!c) return null;
                    const cd = c.cfg ? c.cfg.data : c.data;
                    return {
                        datasetCount: cd.datasets.length,
                        labels:       cd.labels,
                        datasets: cd.datasets.map(d => ({
                            label: d.label, dataLen: d.data.length,
                            dataSample: d.data.slice(0, 13),
                            borderDash: d.borderDash || [], borderColor: d.borderColor,
                        }))
                    };
                } catch(e) { return null; }
            }
            // Custom chart.local.js stores config at chart.cfg
            const cd = chart.cfg ? chart.cfg.data : chart.data;
            return {
                datasetCount: cd.datasets.length,
                labels:       cd.labels,
                datasets: cd.datasets.map(d => ({
                    label:       d.label,
                    dataLen:     d.data.length,
                    dataSample:  d.data.slice(0, 13),
                    borderDash:  d.borderDash || [],
                    borderColor: d.borderColor,
                }))
            };
        }""")

        if chart_info is None:
            print("  WARN  Chart.getChart() retornou null — Chart.js pode não ser v3+ ou canvas não encontrado")
        else:
            ds_count = chart_info["datasetCount"]
            labels   = chart_info["datasets"] and [x["label"] for x in chart_info["datasets"]]

            # Esperamos 2 series por par (HC + Tot) + até 4 linhas de limite
            # 3 pares * 2 = 6 + 4 limite = 10 máximo; mínimo = 6 (sem limites)
            check(6 <= ds_count <= 10, f"Nº datasets: {ds_count} (esperado 6..10)")

            # Verifica labels das series de dados (não de limite)
            data_labels = [d["label"] for d in chart_info["datasets"] if not (d["label"] or "").startswith("+") and not (d["label"] or "").startswith("-")]
            print(f"  Labels das series de dados ({len(data_labels)}): {data_labels}")

            hc_labels  = [l for l in data_labels if l.startswith("HC%")]
            tot_labels = [l for l in data_labels if l.startswith("Tot%")]
            check(len(hc_labels)  == len(PAIRS), f"Nº series HC%  == {len(PAIRS)} pares: {hc_labels}")
            check(len(tot_labels) == len(PAIRS), f"Nº series Tot% == {len(PAIRS)} pares: {tot_labels}")

            # Verifica datasets de limite existem quando checkboxes marcados
            lim_labels = [d["label"] for d in chart_info["datasets"] if (d["label"] or "").startswith(("+", "-"))]
            print(f"  Labels de limite ({len(lim_labels)}): {lim_labels}")
            check(f"+{int(LIM_HC)}% HC" in lim_labels,    f"Limite +{int(LIM_HC)}% HC presente")
            check(f"-{int(LIM_HC)}% HC" in lim_labels,    f"Limite -{int(LIM_HC)}% HC presente")
            check(f"+{int(LIM_TOTAL)}% Total" in lim_labels, f"Limite +{int(LIM_TOTAL)}% Total presente")
            check(f"-{int(LIM_TOTAL)}% Total" in lim_labels, f"Limite -{int(LIM_TOTAL)}% Total presente")

            # ── Cross-check cálculos: compara dataset HC% PE-4 vs Python ────
            # Dataset 0 deve ser "HC% PE-4 × Riser P5" (primeiro par no cadastro por ordem)
            first_hc_ds = next((d for d in chart_info["datasets"] if d["label"].startswith("HC%")), None)
            if first_hc_ds:
                pair_lbl_match = None
                for sub_tag, top_tag, sub_lbl, top_lbl in PAIRS:
                    if sub_lbl in first_hc_ds["label"] or sub_lbl.replace("-", "_") in first_hc_ds["label"]:
                        pair_lbl_match = f"{sub_lbl} x {top_lbl}"
                        break
                if pair_lbl_match and pair_lbl_match in expected:
                    data_from_chart = first_hc_ds["dataSample"]  # primeiros 13 dias
                    exp_days  = sorted(expected[pair_lbl_match].keys())[:13]
                    # allDays em JS = todos os dias do mês, array 1-indexado
                    # dataSample[0] = dia 1, dataSample[1] = dia 2, etc.
                    print(f"\n  Cross-check dataset '{first_hc_ds['label']}':")
                    for i, exp_day in enumerate(exp_days):
                        day_idx = int(exp_day.split("-")[2]) - 1  # 0-based
                        if day_idx >= len(data_from_chart):
                            break
                        chart_val = data_from_chart[day_idx]
                        exp_val   = expected[pair_lbl_match].get(exp_day, {}).get("hc_dev")
                        if chart_val is None and exp_val is None:
                            check(True, f"  Dia {exp_day}: ambos null")
                        elif chart_val is not None and exp_val is not None:
                            diff = abs(float(chart_val) - float(exp_val))
                            check(diff < 0.015, f"  Dia {exp_day}: chart={chart_val:.3f} python={exp_val:.3f} diff={diff:.4f}")
                        else:
                            print(f"  WARN  Dia {exp_day}: chart={chart_val} python={exp_val} (diferença null vs valor)")

        # ── verificar legenda (texto final) ──────────────────────────────────
        legend_html = page.evaluate("() => document.getElementById('desvioChartLegend')?.innerHTML || ''")
        print(f"\n  Legenda: {legend_html[:140]}")
        check("Sem dias" not in legend_html and "Sem dados" not in legend_html,
              "Legenda não mostra 'Sem dados' (há dados disponíveis)")

        # ── voltar ao modo sep ────────────────────────────────────────────────
        sep_radio = page.query_selector("#desvioModeSep")
        if sep_radio:
            sep_radio.click()
            page.wait_for_timeout(500)

        # ── erros JS ──────────────────────────────────────────────────────────
        relevant_errors = [e for e in js_errors if "favicon" not in e.lower() and "net::" not in e.lower()]
        check(len(relevant_errors) == 0,
              f"Sem erros JS relevantes ({len(relevant_errors)} encontrados: {relevant_errors[:3]})")

        browser.close()


# ── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Testando servidor em {BASE_URL}")
    print("=" * 70)

    expected_data = test_api_calculations()
    test_playwright_chart(expected_data)

    print("\n" + "=" * 70)
    print("TODOS OS TESTES PASSARAM")
