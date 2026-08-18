#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Relatório Completo — lê diretamente do mpfm_local.db
Uso:
    python gerar_relatorio_db.py
    python gerar_relatorio_db.py --db ../data/mpfm_local.db --output relatorio.html
    python gerar_relatorio_db.py --date-from 2026-06-01 --date-to 2026-08-31
"""

from __future__ import annotations
import argparse
import html as html_mod
import json
import os
import sqlite3
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── Caminhos padrão ───────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
DEFAULT_DB = _HERE.parent / "data" / "mpfm_local.db"
DEFAULT_OUT = _HERE / "HTML_GERADOS" / f"RELATORIO_DB_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

# ── Dados resolvidos (tabelas criadas em 2026-08-18) ─────────────────────────
DADOS_RESOLVIDOS = [
    {
        "dado": "Extração PI Vision (séries temporais)",
        "resolucao": "Tabela pi_vision_readings criada com colunas: tag, variable_name, channel, "
                     "group_name, timestamp, day_ref, value, quality, source, source_file, run_id. "
                     "Serviço services/importing/pi_vision_import_service.py criado. "
                     "Endpoint: POST /api/admin/pi-vision/import (body: {excel_path, only_authorized_variables}).",
    },
    {
        "dado": "Choke % dos poços (PITimeDat)",
        "resolucao": "Tabela well_choke_history criada (tag, day_ref, choke_pct, source). "
                     "Serviço services/importing/choke_history_import_service.py criado. "
                     "Endpoint: POST /api/admin/choke-history/import-excel (upload do Excel com valores resolvidos).",
    },
    {
        "dado": "Dados do Painel do Operador (balanços sem referência temporal explícita)",
        "resolucao": "Coluna day_ref adicionada em painel_operador_tank_balance (778 linhas), "
                     "painel_operador_gas_balance (640 linhas) e painel_operador_offspec_tank (754 linhas). "
                     "Retroativamente preenchida a partir do campo de data existente em cada tabela.",
    },
]

# ── Dados que ainda NÃO estão em uma tabela dedicada no banco ─────────────────
DADOS_FORA_DO_BANCO = [
    {
        "dado": "Valores PI Vision — tabela criada, aguarda ingestão",
        "situacao": "A tabela pi_vision_readings existe e o serviço de importação está pronto. "
                    "O Excel do coletor PI (PI_EXTRACT_TOTAL) ainda não foi importado.",
        "sugestao": "Executar: POST /api/admin/pi-vision/import com {\"excel_path\": \"C:\\\\PI_Vision_Collector\\\\saida_v4\\\\Historico_V49_Geometrico.xlsx\"} "
                    "ou configurar a variável de ambiente BASE_UNICA_PI_OUTPUT.",
    },
    {
        "dado": "Choke % dos poços — tabela criada, aguarda ingestão",
        "situacao": "A tabela well_choke_history existe e o serviço de captura está pronto. "
                    "O Choke % resolve via fórmula PITimeDat no Excel com PI DataLink.",
        "sugestao": "Gerar Excel de produção → abrir no Excel com PI DataLink instalado → salvar → "
                    "fazer upload em POST /api/admin/choke-history/import-excel (multipart/form-data, campo 'file').",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def esc(s):
    return html_mod.escape(str(s) if s is not None else "")

def js(obj):
    return json.dumps(obj, ensure_ascii=False, default=str)

def conn_open(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ── Queries por aba ───────────────────────────────────────────────────────────

def q_executivo(cur, date_from, date_to, bank):
    filt = "AND day_ref BETWEEN ? AND ?" if date_from and date_to else ""
    bfilt = "AND bank=?" if bank else ""
    params_base = []
    if date_from and date_to:
        params_base += [date_from, date_to]
    if bank:
        params_base.append(bank)

    # KPIs gerais
    kpi_sql = (
        f"SELECT COUNT(DISTINCT day_ref) as dias, COUNT(DISTINCT bank) as bancos, "
        f"COUNT(DISTINCT tag) as tags "
        f"FROM measurements_active WHERE row_kind='daily' AND COALESCE(is_official,1)=1 {filt} {bfilt}"
    )
    kpi = dict(cur.execute(kpi_sql, params_base).fetchone())

    # totais de produção (métricas chave)
    prod_sql = (
        f"SELECT metric_name, SUM(metric_value) as total "
        f"FROM measurements_active WHERE row_kind='daily' AND COALESCE(is_official,1)=1 {filt} {bfilt} "
        f"AND metric_name IN ('MPFM corr HC (t)','MPFM corr Óleo (t)','MPFM corr Gás (t)','MPFM corr Água (t)','MPFM corr Total (t)') "
        f"GROUP BY metric_name"
    )
    prod = {r["metric_name"]: r["total"] for r in cur.execute(prod_sql, params_base)}

    # pivot diário por tag (top 10 tags por volume HC)
    pivot_sql = (
        f"SELECT day_ref, bank, tag, metric_name, metric_value "
        f"FROM measurements_active WHERE row_kind='daily' AND COALESCE(is_official,1)=1 {filt} {bfilt} "
        f"AND metric_name IN ('MPFM corr HC (t)','MPFM corr Óleo (t)','MPFM corr Gás (t)','MPFM corr Total (t)') "
        f"ORDER BY day_ref, bank, tag, metric_name"
    )
    rows_pivot = defaultdict(dict)
    for r in cur.execute(pivot_sql, params_base):
        k = (r["day_ref"], r["bank"], r["tag"])
        rows_pivot[k][r["metric_name"]] = r["metric_value"]

    table_rows = []
    for (day, bank_n, tag), metrics in sorted(rows_pivot.items()):
        table_rows.append({
            "Data": day, "Banco": bank_n, "TAG": tag,
            "HC (t)": metrics.get("MPFM corr HC (t)", ""),
            "Óleo (t)": metrics.get("MPFM corr Óleo (t)", ""),
            "Gás (t)": metrics.get("MPFM corr Gás (t)", ""),
            "Total (t)": metrics.get("MPFM corr Total (t)", ""),
        })

    # trend HC por dia
    trend_sql = (
        f"SELECT day_ref, SUM(metric_value) as v FROM measurements_active "
        f"WHERE row_kind='daily' AND metric_name='MPFM corr HC (t)' AND COALESCE(is_official,1)=1 {filt} {bfilt} "
        f"GROUP BY day_ref ORDER BY day_ref"
    )
    trend = [(r["day_ref"], round(r["v"] or 0, 2)) for r in cur.execute(trend_sql, params_base)]

    return {"kpi": kpi, "prod": prod, "table": table_rows, "trend": trend}


def q_comparacoes(cur, date_from, date_to):
    filt = "AND comparison_date BETWEEN ? AND ?" if date_from and date_to else ""
    params = [date_from, date_to] if date_from and date_to else []
    rows = cur.execute(
        f"SELECT comparison_date, family_name, tag, fluid, status, raw_ok, anp_ok, "
        f"raw_corrigido, xml_corrigido, anp_corrigido, note "
        f"FROM painel_operador_comparisons WHERE 1=1 {filt} ORDER BY comparison_date DESC, family_name, tag "
        f"LIMIT 5000",
        params,
    ).fetchall()
    cols = ["comparison_date","family_name","tag","fluid","status","raw_ok",
            "anp_ok","raw_corrigido","xml_corrigido","anp_corrigido","note"]
    return {"cols": cols, "rows": [dict(r) for r in rows]}


def q_separador(cur, date_from, date_to):
    filt = "AND day_ref BETWEEN ? AND ?" if date_from and date_to else ""
    params = [date_from, date_to] if date_from and date_to else []

    # SEP source files coverage
    cov = cur.execute(
        f"SELECT COUNT(DISTINCT production_date) as dias, fluid_kind, COUNT(*) as cnt "
        f"FROM sep_source_files WHERE 1=1 "
        + ("AND production_date BETWEEN ? AND ?" if date_from and date_to else "")
        + " GROUP BY fluid_kind",
        params,
    ).fetchall()

    # Detailed SEP data — pivot by day/hour/tag
    sep_rows_raw = cur.execute(
        f"SELECT day_ref, hour_ref, tag, metric_name, metric_value, row_kind "
        f"FROM measurements_active WHERE row_kind IN ('sep','sep_oleo_detail','sep_gas_detail','sep_agua_detail') "
        f"AND COALESCE(is_official,1)=1 {filt} ORDER BY day_ref, row_kind, tag, metric_name LIMIT 10000",
        params,
    ).fetchall()

    piv = defaultdict(dict)
    for r in sep_rows_raw:
        k = (r["day_ref"], r["hour_ref"], r["row_kind"], r["tag"])
        piv[k][r["metric_name"]] = r["metric_value"]

    rows = []
    for (day, hr, rk, tag), metrics in sorted(piv.items(), key=lambda x: (x[0][0] or "", x[0][1] if x[0][1] is not None else -1, x[0][2] or "", x[0][3] or "")):
        row = {"Data": day, "Hora": hr if hr is not None else "DAY",
               "Fluido": rk.replace("sep_","").replace("_detail",""), "TAG": tag}
        row.update({k: round(v, 4) if isinstance(v, float) else v for k, v in metrics.items()})
        rows.append(row)

    return {"cobertura": [dict(r) for r in cov], "rows": rows}


def q_cobertura(cur, date_from, date_to):
    filt = "AND calendar_date BETWEEN ? AND ?" if date_from and date_to else ""
    params = [date_from, date_to] if date_from and date_to else []
    cal = cur.execute(
        f"SELECT calendar_date, day_number, loaded, status, closing_status, points_count "
        f"FROM painel_operador_calendar_days WHERE 1=1 {filt} ORDER BY calendar_date DESC LIMIT 365",
        params,
    ).fetchall()
    runs = cur.execute(
        "SELECT id, started_at, finished_at, source_type, source_ref, files_count, status "
        "FROM processing_runs ORDER BY id DESC LIMIT 50"
    ).fetchall()
    return {"calendar": [dict(r) for r in cal], "runs": [dict(r) for r in runs]}


def q_pi_vision(cur):
    # Tenta ler de pi_vision_readings (tabela estruturada criada em 2026-08-18)
    pi_count = cur.execute("SELECT COUNT(*) FROM pi_vision_readings").fetchone()[0]
    pi_rows = []
    if pi_count > 0:
        pi_rows = [dict(r) for r in cur.execute(
            "SELECT tag, timestamp, value, quality, source, created_at "
            "FROM pi_vision_readings ORDER BY timestamp DESC LIMIT 500"
        ).fetchall()]

    # Log de parsing como contexto complementar
    events = cur.execute(
        "SELECT pe.id, pe.parser_name, pe.parser_stage, pe.status, pe.created_at, "
        "sf.filename "
        "FROM parsing_events_raw pe "
        "LEFT JOIN source_files_raw sf ON sf.id=pe.source_file_raw_id "
        "ORDER BY pe.id DESC LIMIT 200"
    ).fetchall()
    total = cur.execute("SELECT COUNT(*) FROM parsing_events_raw").fetchone()[0]
    ok = cur.execute("SELECT COUNT(*) FROM parsing_events_raw WHERE status='ok'").fetchone()[0]
    return {"pi_count": pi_count, "pi_rows": pi_rows,
            "total": total, "ok": ok, "events": [dict(r) for r in events]}


def q_alarmes(cur, date_from, date_to):
    filt = "AND event_at BETWEEN ? AND ?" if date_from and date_to else ""
    params = [date_from, date_to] if date_from and date_to else []
    by_cat = cur.execute(
        f"SELECT category_code, COUNT(*) as cnt, SUM(CASE WHEN status_code='open' THEN 1 ELSE 0 END) as open_cnt "
        f"FROM alarm_records WHERE 1=1 {filt} GROUP BY category_code ORDER BY cnt DESC",
        params,
    ).fetchall()
    recentes = cur.execute(
        f"SELECT external_code, tag, category_code, severity_code, status_code, event_at, title "
        f"FROM alarm_records WHERE 1=1 {filt} ORDER BY event_at DESC LIMIT 200",
        params,
    ).fetchall()
    audit_cnt = cur.execute("SELECT COUNT(*) FROM alarm_audit_log").fetchone()[0]
    return {"by_cat": [dict(r) for r in by_cat],
            "recentes": [dict(r) for r in recentes],
            "audit_cnt": audit_cnt}


def q_detalhes(cur, date_from, date_to, bank):
    filt = "AND day_ref BETWEEN ? AND ?" if date_from and date_to else ""
    bfilt = "AND bank=?" if bank else ""
    params = []
    if date_from and date_to:
        params += [date_from, date_to]
    if bank:
        params.append(bank)
    rows = cur.execute(
        f"SELECT day_ref, bank, loop, tipo, tag, instrument, metric_name, metric_value, metric_unit, is_official "
        f"FROM measurements_active WHERE row_kind='daily' AND COALESCE(is_official,1)=1 {filt} {bfilt} "
        f"ORDER BY day_ref DESC, bank, tag, metric_name LIMIT 20000",
        params,
    ).fetchall()
    # also distinct banks and tags for filter
    banks = [r[0] for r in cur.execute("SELECT DISTINCT bank FROM measurements_active WHERE bank IS NOT NULL ORDER BY bank").fetchall()]
    tags = [r[0] for r in cur.execute("SELECT DISTINCT tag FROM measurements_active WHERE row_kind='daily' AND tag IS NOT NULL ORDER BY tag LIMIT 200").fetchall()]
    return {"rows": [dict(r) for r in rows], "banks": banks, "tags": tags}


def q_auditoria(cur):
    runs = cur.execute(
        "SELECT id, started_at, finished_at, source_type, source_ref, density, files_count, status "
        "FROM processing_runs ORDER BY id DESC LIMIT 100"
    ).fetchall()
    fi = cur.execute(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN processed_ok=1 THEN 1 ELSE 0 END) as ok_cnt, "
        "SUM(CASE WHEN processed_ok!=1 THEN 1 ELSE 0 END) as err_cnt "
        "FROM files_imported"
    ).fetchone()
    sf = cur.execute(
        "SELECT COUNT(*) as total, MIN(created_at) as first, MAX(created_at) as last FROM source_files_raw"
    ).fetchone()
    return {"runs": [dict(r) for r in runs],
            "files_imported": dict(fi),
            "source_files": dict(sf)}


def q_validacao(cur):
    by_sev = cur.execute(
        "SELECT severity, COUNT(*) as cnt FROM validation_issues GROUP BY severity ORDER BY cnt DESC"
    ).fetchall()
    by_type = cur.execute(
        "SELECT severity, issue_type, COUNT(*) as cnt FROM validation_issues "
        "GROUP BY severity, issue_type ORDER BY cnt DESC LIMIT 30"
    ).fetchall()
    recentes = cur.execute(
        "SELECT severity, issue_type, day_ref, ref_key, details FROM validation_issues "
        "ORDER BY id DESC LIMIT 300"
    ).fetchall()
    return {"by_sev": [dict(r) for r in by_sev],
            "by_type": [dict(r) for r in by_type],
            "recentes": [dict(r) for r in recentes]}


def q_xml042(cur, date_from, date_to):
    filt = "AND production_day BETWEEN ? AND ?" if date_from and date_to else ""
    params = [date_from, date_to] if date_from and date_to else []
    docs = cur.execute(
        f"SELECT production_day, cod_cadastro_poco, well_operator_name, subsea_tag, bank, "
        f"filename, status FROM xml042_documents WHERE 1=1 {filt} ORDER BY production_day DESC LIMIT 500",
        params,
    ).fetchall()
    by_status = cur.execute(
        "SELECT status, COUNT(*) as cnt FROM xml042_documents GROUP BY status"
    ).fetchall()
    imported = cur.execute(
        "SELECT COUNT(*) as total, MIN(production_day) as first, MAX(production_day) as last "
        "FROM xml042_documents"
    ).fetchone()
    return {"docs": [dict(r) for r in docs],
            "by_status": [dict(r) for r in by_status],
            "imported": dict(imported)}


# ── HTML builder ─────────────────────────────────────────────────────────────

CSS = """
:root{--navy:#071e41;--navy2:#0a2d5d;--teal:#007d8a;--cyan:#11a8b7;--ink:#102238;--muted:#627287;
--line:#d9e1e8;--bg:#f5f8fb;--card:#fff;--green:#1b8e47;--amber:#e98a00;--red:#d73535;
--blue:#1565c0;--shadow:0 8px 22px rgba(16,34,56,.07);}
*{box-sizing:border-box;}
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:var(--bg);color:var(--ink);font-size:14px;}
header{background:var(--navy);color:#fff;padding:20px 32px;border-bottom:4px solid var(--teal);}
header h1{margin:4px 0;font-size:22px;letter-spacing:-.02em;}
header p{margin:2px 0;font-size:12px;color:#b8d4e0;}
main{padding:20px 28px;max-width:1680px;margin:0 auto;}
h2{color:var(--navy);font-size:20px;border-left:4px solid var(--teal);padding-left:10px;margin:20px 0 12px;}
h3{color:var(--navy2);font-size:16px;margin:18px 0 8px;}
.tab-nav{display:flex;flex-wrap:wrap;gap:6px;padding:8px;margin:0 0 20px;background:#fff;
border:1px solid var(--line);border-radius:6px;position:sticky;top:8px;z-index:10;
box-shadow:var(--shadow);}
.tab-btn{border:1px solid var(--line);background:#fff;color:var(--muted);padding:8px 12px;
border-radius:4px;font-weight:700;font-size:12px;cursor:pointer;}
.tab-btn:hover{background:#eef3f8;color:var(--navy);}
.tab-btn.active{background:var(--blue);color:#fff;border-color:var(--blue);}
.tab-panel[hidden]{display:none!important;}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:14px 0;}
.card{background:#fff;border-left:4px solid var(--teal);border-radius:6px;padding:14px 16px;
box-shadow:var(--shadow);}
.card b{display:block;font-size:26px;margin:4px 0;color:var(--navy);}
.card small{color:var(--muted);font-size:11px;}
.card.good{border-left-color:var(--green);}
.card.warn{border-left-color:var(--amber);}
.card.bad{border-left-color:var(--red);}
.table-wrap{max-height:460px;overflow:auto;border:1px solid var(--line);border-radius:6px;margin:10px 0;}
.dt{border-collapse:collapse;width:100%;font-size:12px;}
.dt th{background:#0f3b40;color:#fff;font-size:10px;font-weight:700;text-transform:uppercase;
letter-spacing:.03em;padding:9px 10px;position:sticky;top:0;z-index:1;white-space:nowrap;}
.dt th.sortable{cursor:pointer;}
.dt th.sortable:after{content:" ↕";opacity:.5;}
.dt td{border-bottom:1px solid #edf1f4;padding:8px 10px;white-space:nowrap;}
.dt tr:hover td{background:#eaf4fb;}
.dt tr:nth-child(even) td{background:#f7fbfc;}
.info-box{background:#e4f1f8;border-left:4px solid var(--blue);border-radius:4px;
padding:12px 14px;margin:10px 0;color:#244858;line-height:1.5;}
.warn-box{background:#fff7ed;border-left:4px solid var(--amber);border-radius:4px;
padding:12px 14px;margin:10px 0;}
.danger-box{background:#fde8e7;border-left:4px solid var(--red);border-radius:4px;
padding:12px 14px;margin:10px 0;}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;align-items:flex-end;}
.controls label{display:flex;flex-direction:column;gap:3px;font-size:11px;font-weight:700;color:var(--muted);}
.controls select,.controls input{padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;
background:#fff;color:var(--ink);font-size:13px;}
.bar-row{display:grid;grid-template-columns:180px 60px 1fr;gap:10px;align-items:center;margin:4px 0;}
.bar-track{height:16px;background:#e2e8f0;border-radius:999px;overflow:hidden;}
.bar-fill{height:100%;border-radius:999px;background:var(--teal);}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;}
.pill-ok{background:#dcfce7;color:#166534;}
.pill-warn{background:#fef9c3;color:#854d0e;}
.pill-err{background:#fee2e2;color:#991b1b;}
.pill-info{background:#e0f2fe;color:#0369a1;}
canvas{max-width:100%;max-height:280px;}
@media(max-width:800px){.tab-nav{position:static;}}
"""

JS_SHARED = """
// Tab navigation
document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const t=btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.tab===t));
    document.querySelectorAll('.tab-panel').forEach(p=>p.hidden=p.dataset.tabGroup!==t);
  });
});
// Activate first tab
const first=document.querySelector('.tab-btn'); if(first) first.click();

// Table sort + filter
function setupTable(tableId, filterId){
  const table=document.getElementById(tableId);
  if(!table) return;
  const tbody=table.querySelector('tbody');
  const rows=[...tbody.querySelectorAll('tr')];
  let sortCol=-1, sortAsc=true;
  table.querySelectorAll('th.sortable').forEach((th,ci)=>{
    th.addEventListener('click',()=>{
      if(sortCol===ci) sortAsc=!sortAsc; else{sortCol=ci;sortAsc=true;}
      rows.sort((a,b)=>{
        const av=a.cells[ci]?.innerText||'', bv=b.cells[ci]?.innerText||'';
        const an=parseFloat(av), bn=parseFloat(bv);
        if(!isNaN(an)&&!isNaN(bn)) return sortAsc?an-bn:bn-an;
        return sortAsc?av.localeCompare(bv):bv.localeCompare(av);
      });
      rows.forEach(r=>tbody.appendChild(r));
    });
  });
  if(filterId){
    document.getElementById(filterId)?.addEventListener('input',e=>{
      const q=e.target.value.toLowerCase();
      rows.forEach(r=>r.hidden=!r.innerText.toLowerCase().includes(q));
    });
  }
}
"""


def pill(val):
    if val in ("ok","closed","generated","good"): return f'<span class="pill pill-ok">{esc(val)}</span>'
    if val in ("warn","warning","partial"): return f'<span class="pill pill-warn">{esc(val)}</span>'
    if val in ("error","open","failed","bad"): return f'<span class="pill pill-err">{esc(val)}</span>'
    if val in ("info",): return f'<span class="pill pill-info">{esc(val)}</span>'
    return esc(val)


def make_table(rows, cols=None, table_id="", sortable=True, limit=2000):
    if not rows:
        return "<p class='muted'>Sem dados no período.</p>"
    cols = cols or list(rows[0].keys())
    th = "".join(f'<th class="{"sortable" if sortable else ""}">{esc(c)}</th>' for c in cols)
    trs = []
    for r in rows[:limit]:
        tds = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                v = f"{v:,.4f}".rstrip("0").rstrip(".")
            tds.append(f"<td>{pill(str(v)) if c in ('status','status_code','severity','severity_code') else esc(v)}</td>")
        trs.append(f"<tr>{''.join(tds)}</tr>")
    id_attr = f' id="{table_id}"' if table_id else ""
    note = f'<p class="muted" style="font-size:11px">Mostrando primeiros {limit:,} de {len(rows):,} registros.</p>' if len(rows) > limit else ""
    return (f'{note}<div class="table-wrap"><table{id_attr} class="dt"><thead><tr>{th}</tr></thead>'
            f"<tbody>{''.join(trs)}</tbody></table></div>")


def section_executivo(d):
    kpi = d["kpi"]
    prod = d["prod"]
    trend_labels = js([x[0] for x in d["trend"]])
    trend_vals = js([x[1] for x in d["trend"]])

    cards = f"""
    <div class="cards">
      <div class="card good"><small>Dias cobertos</small><b>{kpi.get('dias',0)}</b><small>no período</small></div>
      <div class="card"><small>Bancos</small><b>{kpi.get('bancos',0)}</b><small>ativos</small></div>
      <div class="card"><small>TAGs distintas</small><b>{kpi.get('tags',0)}</b><small>produção diária</small></div>
      <div class="card accent"><small>HC corrigido</small>
        <b>{prod.get('MPFM corr HC (t)',0):,.1f}</b><small>t — soma do período</small></div>
      <div class="card"><small>Óleo corrigido</small>
        <b>{prod.get('MPFM corr Óleo (t)',0):,.1f}</b><small>t</small></div>
      <div class="card"><small>Gás corrigido</small>
        <b>{prod.get('MPFM corr Gás (t)',0):,.1f}</b><small>t</small></div>
      <div class="card warn"><small>Total corrigido</small>
        <b>{prod.get('MPFM corr Total (t)',0):,.1f}</b><small>t</small></div>
    </div>
    """

    chart = f"""
    <h3>Tendência HC corrigido (t/dia)</h3>
    <canvas id="trendChart" height="100"></canvas>
    <script>
    (function(){{
      var ctx=document.getElementById('trendChart').getContext('2d');
      new Chart(ctx,{{type:'line',data:{{labels:{trend_labels},
        datasets:[{{label:'HC corr (t)',data:{trend_vals},
        borderColor:'#007d8a',backgroundColor:'rgba(0,125,138,.08)',
        pointRadius:2,tension:.3,fill:true}}]}},
        options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:false}}}}}}
      }});
    }})();
    </script>
    """

    table_html = make_table(d["table"], table_id="execTable")
    return f"""
    <h2>Visão Integrada do MPFM</h2>
    <div class="info-box">Dados consultados em tempo real de <b>measurements_active</b> (measurements_curated filtrado por tags ativas). Granularidade: diária.</div>
    {cards}
    {chart}
    <h3>Dados diários detalhados</h3>
    <div class="controls">
      <label>Buscar<input id="execFilter" type="text" placeholder="TAG, banco, data…" style="min-width:200px"></label>
    </div>
    {table_html}
    <script>setupTable('execTable','execFilter');</script>
    """


def section_comparacoes(d):
    table_html = make_table(d["rows"], d["cols"], table_id="cmpTable")
    return f"""
    <h2>Comparações MPFM × Referência</h2>
    <div class="info-box">Fonte: tabela <b>painel_operador_comparisons</b> — {len(d['rows']):,} registros no período.</div>
    <div class="controls">
      <label>Buscar<input id="cmpFilter" type="text" placeholder="família, TAG, status…" style="min-width:200px"></label>
    </div>
    {table_html}
    <script>setupTable('cmpTable','cmpFilter');</script>
    """


def section_separador(d):
    cov_html = "".join(
        f'<div class="card"><small>{esc(r.get("fluid_kind",""))}</small>'
        f'<b>{r.get("dias",0)}</b><small>dias · {r.get("cnt",0)} arquivos</small></div>'
        for r in d["cobertura"]
    )
    table_html = make_table(d["rows"], table_id="sepTable")
    return f"""
    <h2>Dados do Separador de Testes</h2>
    <div class="info-box">Fonte: <b>measurements_active</b> (row_kind sep / sep_oleo_detail / sep_gas_detail / sep_agua_detail) + <b>sep_source_files</b>.</div>
    <h3>Cobertura por fluido</h3>
    <div class="cards">{cov_html}</div>
    <h3>Leituras detalhadas</h3>
    <div class="controls">
      <label>Buscar<input id="sepFilter" type="text" placeholder="fluido, TAG, data…" style="min-width:200px"></label>
    </div>
    {table_html}
    <script>setupTable('sepTable','sepFilter');</script>
    """


def section_cobertura(d):
    cal = d["calendar"]
    runs = d["runs"]
    cal_html = make_table(cal, table_id="calTable")
    runs_html = make_table(runs, table_id="runsTable")
    return f"""
    <h2>Cobertura e Rastreabilidade de Dados</h2>
    <div class="info-box">Calendário: <b>painel_operador_calendar_days</b> ({len(cal)} dias). Histórico de importação: <b>processing_runs</b>.</div>
    <h3>Calendário de cobertura</h3>
    <div class="controls">
      <label>Buscar<input id="calFilter" type="text" placeholder="data, status…" style="min-width:200px"></label>
    </div>
    {cal_html}
    <script>setupTable('calTable','calFilter');</script>
    <h3>Últimas importações</h3>
    {runs_html}
    <script>setupTable('runsTable',null);</script>
    """


def section_pi(d):
    if d["pi_count"] > 0:
        pi_table = make_table(d["pi_rows"], table_id="piValTable")
        pi_section = f"""
        <div class="info-box">Fonte: <b>pi_vision_readings</b> — {d['pi_count']:,} leituras estruturadas. Últimas 500 exibidas.</div>
        {pi_table}
        <script>setupTable('piValTable',null);</script>"""
    else:
        pi_section = """
        <div class="warn-box">
          <b>Tabela pi_vision_readings criada mas ainda sem dados.</b><br>
          Aguardando integração do parser PI para persistir os valores extraídos (tag, timestamp, value, quality).
        </div>"""

    events_table = make_table(d["events"], table_id="piTable")
    return f"""
    <h2>Extração PI Vision</h2>
    {pi_section}
    <h3>Log de parsing — parsing_events_raw ({d['total']:,} eventos, {d['ok']:,} OK)</h3>
    {events_table}
    <script>setupTable('piTable',null);</script>
    """


def section_alarmes(d):
    max_cnt = max((r["cnt"] for r in d["by_cat"]), default=1)
    bars = "".join(
        f'<div class="bar-row">'
        f'<span>{esc(r["category_code"])}</span>'
        f'<span>{r["cnt"]}</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{100*r["cnt"]/max_cnt:.1f}%"></div></div>'
        f'</div>'
        for r in d["by_cat"]
    )
    table_html = make_table(d["recentes"], table_id="alarmTable")
    return f"""
    <h2>Alarmes e Eventos</h2>
    <div class="info-box">Fonte: <b>alarm_records</b> ({sum(r['cnt'] for r in d['by_cat']):,} registros). Log de auditoria: <b>alarm_audit_log</b> ({d['audit_cnt']:,} entradas).</div>
    <h3>Distribuição por categoria</h3>
    {bars}
    <h3>Eventos recentes</h3>
    <div class="controls">
      <label>Buscar<input id="alarmFilter" type="text" placeholder="TAG, categoria, status…" style="min-width:200px"></label>
    </div>
    {table_html}
    <script>setupTable('alarmTable','alarmFilter');</script>
    """


def section_detalhes(d):
    table_html = make_table(d["rows"], table_id="detTable")
    banks_opts = "".join(f'<option value="{esc(b)}">{esc(b)}</option>' for b in d["banks"])
    tags_opts = "".join(f'<option value="{esc(t)}">{esc(t)}</option>' for t in d["tags"])
    return f"""
    <h2>Detalhes — Medições Diárias</h2>
    <div class="info-box">Fonte: <b>measurements_active</b> WHERE row_kind='daily'. Todos os pares TAG × métrica no período.</div>
    <div class="controls">
      <label>Banco<select id="detBank"><option value="">Todos</option>{banks_opts}</select></label>
      <label>TAG<select id="detTag"><option value="">Todos</option>{tags_opts}</select></label>
      <label>Buscar<input id="detFilter" type="text" placeholder="métrica, data…" style="min-width:200px"></label>
    </div>
    {table_html}
    <script>
    setupTable('detTable','detFilter');
    document.getElementById('detBank').addEventListener('change',applyDetFilters);
    document.getElementById('detTag').addEventListener('change',applyDetFilters);
    document.getElementById('detFilter').addEventListener('input',applyDetFilters);
    function applyDetFilters(){{
      var bank=document.getElementById('detBank').value.toLowerCase();
      var tag=document.getElementById('detTag').value.toLowerCase();
      var q=document.getElementById('detFilter').value.toLowerCase();
      document.querySelectorAll('#detTable tbody tr').forEach(r=>{{
        var t=r.innerText.toLowerCase();
        r.hidden = (bank&&!t.includes(bank))||(tag&&!t.includes(tag))||(q&&!t.includes(q));
      }});
    }}
    </script>
    """


def section_auditoria(d):
    fi = d["files_imported"]
    sf = d["source_files"]
    table_html = make_table(d["runs"], table_id="runTable")
    return f"""
    <h2>Auditoria e Rastreabilidade</h2>
    <div class="info-box">Rastreabilidade completa de cada arquivo importado até as medições curadas.</div>
    <div class="cards">
      <div class="card"><small>Arquivos importados</small><b>{fi.get('total',0):,}</b><small>total em files_imported</small></div>
      <div class="card good"><small>Importações OK</small><b>{fi.get('ok_cnt',0):,}</b></div>
      <div class="card bad"><small>Com erro</small><b>{fi.get('err_cnt',0):,}</b></div>
      <div class="card"><small>Arquivos fonte</small><b>{sf.get('total',0):,}</b><small>em source_files_raw</small></div>
      <div class="card"><small>Primeiro arquivo</small><b style="font-size:14px">{esc(sf.get('first',''))}</b></div>
      <div class="card"><small>Último arquivo</small><b style="font-size:14px">{esc(sf.get('last',''))}</b></div>
    </div>
    <h3>Histórico de runs de processamento</h3>
    <div class="controls">
      <label>Buscar<input id="runFilter" type="text" placeholder="tipo, status, ref…" style="min-width:200px"></label>
    </div>
    {table_html}
    <script>setupTable('runTable','runFilter');</script>
    """


def section_validacao(d):
    sev_html = "".join(
        f'<div class="card {"bad" if r["severity"]=="error" else "warn" if r["severity"]=="warn" else ""}">'
        f'<small>{esc(r["severity"])}</small><b>{r["cnt"]:,}</b></div>'
        for r in d["by_sev"]
    )
    type_html = make_table(d["by_type"], table_id="valTypeTable")
    rec_html = make_table(d["recentes"], table_id="valRecTable")
    return f"""
    <h2>Validação Final</h2>
    <div class="info-box">Fonte: <b>validation_issues</b> — {sum(r['cnt'] for r in d['by_sev']):,} issues registrados.</div>
    <div class="cards">{sev_html}</div>
    <h3>Por tipo de issue</h3>
    {type_html}
    <script>setupTable('valTypeTable',null);</script>
    <h3>Issues recentes</h3>
    <div class="controls">
      <label>Buscar<input id="valFilter" type="text" placeholder="tipo, severidade, data…" style="min-width:200px"></label>
    </div>
    {rec_html}
    <script>setupTable('valRecTable','valFilter');</script>
    """


def section_xml042(d):
    st_html = "".join(
        f'<div class="card {"good" if r["status"]=="generated" else "warn"}">'
        f'<small>{esc(r["status"])}</small><b>{r["cnt"]}</b></div>'
        for r in d["by_status"]
    )
    table_html = make_table(d["docs"], table_id="xmlTable")
    imp = d["imported"]
    return f"""
    <h2>XML 042 (ANP)</h2>
    <div class="info-box">Fonte: <b>xml042_documents</b> + <b>xml042_imported_rows</b>. Período: {esc(imp.get('first',''))} a {esc(imp.get('last',''))}.</div>
    <div class="cards">
      <div class="card"><small>Documentos totais</small><b>{imp.get('total',0):,}</b></div>
      {st_html}
    </div>
    <div class="controls">
      <label>Buscar<input id="xmlFilter" type="text" placeholder="poço, TAG, status…" style="min-width:200px"></label>
    </div>
    {table_html}
    <script>setupTable('xmlTable','xmlFilter');</script>
    """


def section_dados_fora(items):
    resolved_html = "".join(
        f'<div style="margin:8px 0;padding:10px 14px;border-left:4px solid var(--green);background:var(--card)">'
        f'<b>&#10003; {esc(it["dado"])}</b><br>'
        f'<span style="color:var(--muted)">{esc(it["resolucao"])}</span>'
        f'</div>'
        for it in DADOS_RESOLVIDOS
    )
    pending_html = "".join(
        f'<div class="warn-box" style="margin:8px 0">'
        f'<b>{esc(it["dado"])}</b><br>'
        f'<span style="color:var(--muted)">{esc(it["situacao"])}</span><br>'
        f'<span style="color:var(--green)">&#128161; {esc(it["sugestao"])}</span>'
        f'</div>'
        for it in items
    )
    return f"""
    <h2>Dados registrados fora do banco</h2>
    <div class="info-box">Itens identificados que existem no fluxo de trabalho mas ainda requerem integração com o banco.</div>
    <h3 style="color:var(--green)">Resolvidos (2026-08-18)</h3>
    {resolved_html}
    <h3>Pendentes — aguardam integração</h3>
    {pending_html if items else '<div class="info-box">Nenhum item pendente.</div>'}
    """


def build_html(data: dict, meta: dict) -> str:
    tabs = [
        ("executivo","Visão integrada"),
        ("comparacoes","Comparações"),
        ("separador","Separador"),
        ("cobertura","Cobertura"),
        ("pi","PI Vision"),
        ("alarmes","Alarmes/eventos"),
        ("detalhes","Detalhes"),
        ("auditoria","Auditoria"),
        ("validacao","Validação final"),
        ("xml042","XML 042 (ANP)"),
        ("dados_fora","⚠ Fora do banco"),
    ]
    tab_btns = "".join(f'<button class="tab-btn" data-tab="{tid}">{esc(label)}</button>' for tid, label in tabs)

    sections = {
        "executivo": section_executivo(data["executivo"]),
        "comparacoes": section_comparacoes(data["comparacoes"]),
        "separador": section_separador(data["separador"]),
        "cobertura": section_cobertura(data["cobertura"]),
        "pi": section_pi(data["pi"]),
        "alarmes": section_alarmes(data["alarmes"]),
        "detalhes": section_detalhes(data["detalhes"]),
        "auditoria": section_auditoria(data["auditoria"]),
        "validacao": section_validacao(data["validacao"]),
        "xml042": section_xml042(data["xml042"]),
        "dados_fora": section_dados_fora(DADOS_FORA_DO_BANCO),
    }

    panels = "".join(
        f'<section class="tab-panel" data-tab-group="{tid}" hidden>{content}</section>'
        for tid, content in sections.items()
    )

    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório MPFM — {esc(meta["period"])}</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Relatório de Monitoramento Multifásico</h1>
  <p>Banco: <b>{esc(meta["db"])}</b> &nbsp;·&nbsp; Período: <b>{esc(meta["period"])}</b>
     &nbsp;·&nbsp; Gerado em: <b>{esc(meta["generated_at"])}</b></p>
</header>
<main>
<nav class="tab-nav" role="tablist">{tab_btns}</nav>
{panels}
</main>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script>{JS_SHARED}</script>
</body>
</html>"""


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gerador de relatório a partir do mpfm_local.db")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Caminho para mpfm_local.db")
    parser.add_argument("--output", default=str(DEFAULT_OUT), help="Caminho do HTML gerado")
    parser.add_argument("--date-from", default="", help="Data inicial YYYY-MM-DD")
    parser.add_argument("--date-to", default="", help="Data final YYYY-MM-DD")
    parser.add_argument("--bank", default="", help="Filtrar por banco (B03, B04, …)")
    parser.add_argument("--no-open", action="store_true", help="Não abrir o HTML no browser")
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(f"ERRO: banco não encontrado: {db_path}", file=sys.stderr)
        sys.exit(1)

    date_from = args.date_from
    date_to   = args.date_to
    bank      = args.bank

    print(f"Conectando em: {db_path}")
    conn = conn_open(db_path)
    cur  = conn.cursor()

    # Se não foi informado período, usa últimos 90 dias disponíveis
    if not date_from or not date_to:
        row = cur.execute("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_active").fetchone()
        if not date_from:
            date_from = row[0] or ""
        if not date_to:
            date_to = row[1] or ""
    period = f"{date_from} a {date_to}" + (f" · Banco: {bank}" if bank else "")
    print(f"Período: {period}")

    print("Consultando dados…")
    data = {
        "executivo":   q_executivo(cur, date_from, date_to, bank),
        "comparacoes": q_comparacoes(cur, date_from, date_to),
        "separador":   q_separador(cur, date_from, date_to),
        "cobertura":   q_cobertura(cur, date_from, date_to),
        "pi":          q_pi_vision(cur),
        "alarmes":     q_alarmes(cur, date_from, date_to),
        "detalhes":    q_detalhes(cur, date_from, date_to, bank),
        "auditoria":   q_auditoria(cur),
        "validacao":   q_validacao(cur),
        "xml042":      q_xml042(cur, date_from, date_to),
    }
    conn.close()

    meta = {
        "db": str(db_path),
        "period": period,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    print("Gerando HTML…")
    html_content = build_html(data, meta)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"Relatório gerado: {out_path}  ({size_kb} KB)")

    if not args.no_open:
        webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
