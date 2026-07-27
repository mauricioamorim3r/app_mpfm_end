from __future__ import annotations

import html


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _fmt_num(value, digits: int = 3) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except Exception:
        return _esc(value)
    if abs(number) < 1e-12:
        return "0"
    formatted = f"{number:,.{digits}f}"
    while formatted.endswith("0"):
        formatted = formatted[:-1]
    if formatted.endswith("."):
        formatted = formatted[:-1]
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def _fmt_pct(value) -> str:
    return _fmt_num(value, 2)


def _fmt_day(value: str) -> str:
    if not value:
        return ""
    if len(value) == 10 and value[4] == "-":
        return f"{value[8:10]}/{value[5:7]}/{value[:4]}"
    return _esc(value)


def _summary_cards(summary: dict) -> str:
    cards = [
        ("Dias no recorte", summary.get("days_in_period"), "período total"),
        ("Dias com MPFM", summary.get("days_with_mpfm"), "medição diária disponível"),
        ("Dias com Separador", summary.get("days_with_sep"), "separador de teste"),
        ("Dias com XML", summary.get("days_with_xml"), "XML 042 gerado/importado"),
        ("XMLs gerados", summary.get("xml_generated_count"), "pela aplicação"),
        ("XMLs importados", summary.get("xml_imported_count"), "histórico do mês"),
    ]
    return "".join(
        f"""
        <div class="mr-card">
          <div class="mr-card__k">{_esc(label)}</div>
          <div class="mr-card__v">{_esc(value)}</div>
          <div class="mr-card__m">{_esc(meta)}</div>
        </div>
        """
        for label, value, meta in cards
    )


def _section_table(headers: list[str], rows: list[list[str]], empty_message: str) -> str:
    if not rows:
        return f"<div class='mr-empty'>{_esc(empty_message)}</div>"
    head_cells = []
    for index, item in enumerate(headers):
        is_exceptions = str(item).strip().lower() == "exceções"
        cls = " class='mr-col-exceptions'" if is_exceptions else ""
        if is_exceptions:
            head_cells.append(
                f"<th{cls}><div class='mr-th-content'>{_esc(item)}</div><button type='button' class='mr-col-resizer' data-resize-col='exceptions' aria-label='Ajustar largura da coluna Exceções' title='Arraste para ajustar a largura'></button></th>"
            )
        else:
            head_cells.append(f"<th{cls}>{_esc(item)}</th>")
    head = "".join(head_cells)
    body = []
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            header = headers[index] if index < len(headers) else ""
            is_exceptions = str(header).strip().lower() == "exceções"
            cls = " class='mr-col-exceptions'" if is_exceptions else ""
            content = f"<div class='mr-cell-content'>{cell}</div>" if is_exceptions else cell
            cells.append(f"<td{cls}>{content}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"""
    <div class="mr-tablewrap">
      <table class="mr-table">
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(body)}</tbody>
      </table>
    </div>
    """


def _xml_section(xml_rows: list[dict]) -> str:
    rows = []
    for item in xml_rows:
        rows.append(
            [
                _esc(_fmt_day(item.get("production_day") or "")),
                _esc(item.get("cod_cadastro_poco") or ""),
                _esc(item.get("well_operator_name") or ""),
                _esc(item.get("subsea_tag") or ""),
                _esc(item.get("bank") or ""),
                _esc(_fmt_num(item.get("oil_sm3"))),
                _esc(_fmt_num(item.get("gas_1000sm3"))),
                _esc(_fmt_num(item.get("water_sm3"))),
                _esc(item.get("source_label") or ""),
                _esc(item.get("status") or ""),
                _esc(item.get("filename") or ""),
            ]
        )
    return f"""
    <section class="mr-section">
      <h2>XML 042 do mês</h2>
      <p class="mr-copy">Conferência dos arquivos gerados pela aplicação e dos XMLs importados para retroanálise do fechamento.</p>
      {_section_table(
          ["Data", "Cód. poço", "Poço", "TAG subsea", "Banco", "Óleo (sm³)", "Gás (mil sm³)", "Água (sm³)", "Origem", "Status", "Arquivo"],
          rows,
          "Nenhum XML 042 encontrado para o recorte."
      )}
    </section>
    """


def _group_section(group: dict) -> str:
    rows = []
    for row in group.get("rows") or []:
        issue_text = "<br>".join(
            _esc(f"{item.get('issue_type')}: {item.get('details')}")
            for item in (row.get("issues") or [])
            if item.get("issue_type") or item.get("details")
        )
        rows.append(
            [
                _esc(_fmt_day(row.get("day_ref") or "")),
                _esc(_fmt_num(row.get("subsea_oil_t"))),
                _esc(_fmt_num(row.get("subsea_gas_t"))),
                _esc(_fmt_num(row.get("subsea_water_t"))),
                _esc(_fmt_num(row.get("topside_oil_t"))),
                _esc(_fmt_num(row.get("topside_gas_t"))),
                _esc(_fmt_num(row.get("topside_water_t"))),
                _esc(_fmt_pct(row.get("pct_hc_balance"))),
                _esc(_fmt_pct(row.get("pct_total_balance"))),
                _esc(_fmt_num(row.get("subsea_oil_sm3"))),
                _esc(_fmt_num(row.get("subsea_gas_sm3"))),
                _esc(_fmt_num(row.get("subsea_water_sm3"))),
                _esc(_fmt_num(row.get("sep_oil_t"))),
                _esc(_fmt_num(row.get("sep_gas_t"))),
                _esc(_fmt_num(row.get("sep_water_t"))),
                _esc(_fmt_num(row.get("xml_oil_sm3"))),
                _esc(_fmt_num(row.get("xml_gas_1000sm3"))),
                _esc(_fmt_num(row.get("xml_water_sm3"))),
                _esc(row.get("xml_source_label") or ""),
                _esc(row.get("sep_meters") or ""),
                issue_text,
            ]
        )
    return f"""
    <section class="mr-section">
      <div class="mr-group-head">
        <div>
          <h2>{_esc(group.get("title") or "")}</h2>
          <p class="mr-copy">Subsea {_esc(group.get("subsea_bank") or "")} · {_esc(group.get("subsea_tag") or "")} | Topside {_esc(group.get("topside_bank") or "")} · {_esc(group.get("topside_tag") or "")}</p>
        </div>
        <div class="mr-inline-stats" aria-label="Cobertura do grupo">
          <span class="mr-pill">MPFM: {_esc(group.get("stats", {}).get("days_with_mpfm", 0))}</span>
          <span class="mr-pill">SEP: {_esc(group.get("stats", {}).get("days_with_sep", 0))}</span>
          <span class="mr-pill">XML: {_esc(group.get("stats", {}).get("days_with_xml", 0))}</span>
        </div>
      </div>
      {_section_table(
          [
              "Data",
              "Subsea Óleo (t)", "Subsea Gás (t)", "Subsea Água (t)",
              "Topside Óleo (t)", "Topside Gás (t)", "Topside Água (t)",
              "%HC balanço", "%Total balanço",
              "Subsea Óleo (m³)", "Subsea Gás (sm³)", "Subsea Água (m³)",
              "SEP Óleo (t)", "SEP Gás (t)", "SEP Água (t)",
              "XML Óleo (sm³)", "XML Gás (mil sm³)", "XML Água (sm³)",
              "Origem XML", "Medidor SEP", "Exceções"
          ],
          rows,
          "Nenhuma linha disponível para este grupo no recorte."
      )}
    </section>
    """


def _exception_block(title: str, rows: list[dict], empty_message: str) -> str:
    payload = [
        [
            _esc(_fmt_day(item.get("day_ref") or "")),
            _esc(item.get("group_title") or item.get("ref_key") or ""),
            _esc(item.get("issue_type") or ""),
            _esc(item.get("details") or ""),
        ]
        for item in rows
    ]
    return f"""
    <div class="mr-subsection">
      <h3>{_esc(title)}</h3>
      {_section_table(["Data", "Referência", "Tipo", "Detalhe"], payload, empty_message)}
    </div>
    """


def render_monthly_report_html(payload: dict) -> str:
    meta = payload.get("meta") or {}
    summary = payload.get("summary") or {}
    groups = payload.get("groups") or []
    exceptions = payload.get("exceptions") or {}
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatório Mensal · {_esc(meta.get('month_label') or meta.get('month') or '')}</title>
<style>
  :root {{
    --bg:#e6ecf4; --panel:#ffffff; --panel2:#f2f6fb; --ink:#0c1b2e; --muted:#4e6278;
    --line:#cdd9e8; --accent:#0b74de; --accent-red:#c8252a; --radius:18px;
    --shadow:0 4px 24px rgba(12,27,46,.08);
    font-family:"Segoe UI", system-ui, sans-serif;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); padding:24px; line-height:1.5; }}
  .mr-page {{ max-width:1480px; margin:0 auto; }}
  .mr-hero {{ background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:28px; margin-bottom:18px; }}
  .mr-section {{ background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:22px 24px; margin-bottom:16px; }}
  .mr-title {{ margin:0 0 6px; font-size:28px; font-weight:800; line-height:1.1; letter-spacing:-.3px; }}
  .mr-copy {{ margin:4px 0 0; color:var(--muted); font-size:13px; }}
  .mr-hero-grid {{ display:grid; grid-template-columns:2fr 1fr; gap:20px; align-items:start; }}
  .mr-meta {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px; margin-top:18px; }}
  .mr-card {{ background:linear-gradient(160deg,#f8fbff,#eef4fc); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }}
  .mr-card__k {{ font-size:10px; text-transform:uppercase; letter-spacing:.09em; color:var(--muted); font-weight:600; }}
  .mr-card__v {{ font-size:26px; font-weight:800; margin-top:4px; color:var(--accent); }}
  .mr-card__m {{ color:var(--muted); font-size:11px; margin-top:4px; }}
  .mr-meta-note {{ background:var(--panel2); border:1px solid var(--line); border-radius:14px; padding:16px 18px; color:var(--muted); font-size:13px; line-height:1.7; }}
  .mr-meta-note strong {{ color:var(--ink); }}
  .mr-section h2 {{ margin:0 0 4px; font-size:20px; font-weight:700; letter-spacing:-.2px; border-left:4px solid var(--accent); padding-left:12px; }}
  .mr-section .mr-copy {{ margin-bottom:16px; }}
  .mr-subsection {{ background:var(--panel2); border:1px solid var(--line); border-radius:14px; padding:16px 20px; }}
  .mr-subsection h3 {{ margin:0 0 12px; font-size:14px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--accent); }}
  .mr-group-head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:14px; flex-wrap:wrap; }}
  .mr-inline-stats {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .mr-pill {{ border:1px solid rgba(11,116,222,.22); background:rgba(11,116,222,.09); color:var(--accent); padding:5px 12px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:.02em; }}
  .mr-pill.red {{ border-color:rgba(200,37,42,.22); background:rgba(200,37,42,.08); color:var(--accent-red); }}
  .mr-tablewrap {{ overflow:auto; border:1px solid var(--line); border-radius:14px; margin-top:4px; }}
  .mr-table {{ width:max-content; min-width:100%; border-collapse:collapse; font-size:12px; }}
  .mr-table th, .mr-table td {{ border-bottom:1px solid var(--line); padding:8px 11px; text-align:center; vertical-align:middle; min-width:80px; }}
  .mr-table th {{ background:linear-gradient(180deg,#dde8f5,#d3e2f0); color:#0e2d52; font-size:11px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; position:sticky; top:0; z-index:1; }}
  .mr-table tbody tr:nth-child(even) {{ background:#f4f8fd; }}
  .mr-table tbody tr:hover {{ background:#e8f0fb; }}
  .mr-table td:first-child {{ font-weight:600; color:var(--ink); }}
  .mr-th-content {{ position:relative; padding-right:14px; }}
  .mr-col-exceptions {{ min-width:320px; width:420px; text-align:left !important; vertical-align:top !important; }}
  .mr-col-exceptions .mr-cell-content {{ white-space:normal; line-height:1.45; overflow-wrap:anywhere; word-break:break-word; }}
  .mr-col-resizer {{ position:absolute; top:-8px; right:-6px; width:12px; height:calc(100% + 16px); padding:0; border:0; background:transparent; cursor:col-resize; z-index:3; }}
  .mr-col-resizer::after {{ content:""; position:absolute; top:8px; bottom:8px; left:50%; width:2px; transform:translateX(-50%); border-radius:999px; background:rgba(22,55,93,.22); }}
  .mr-col-resizer:hover::after, .mr-col-resizer.is-dragging::after {{ background:rgba(11,116,222,.62); }}
  .mr-empty {{ padding:16px 20px; color:var(--muted); border:1px dashed var(--line); border-radius:12px; font-size:13px; }}
  .mr-sections-grid {{ display:flex; flex-direction:column; gap:14px; }}
  .mr-balance-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px; margin-top:18px; }}
  .mr-balance-card {{ border-radius:14px; padding:14px 18px; border:1px solid var(--line); }}
  .mr-balance-card.oil {{ background:linear-gradient(160deg,#fff9f0,#fef3e2); border-color:#f5d89a; }}
  .mr-balance-card.gas {{ background:linear-gradient(160deg,#f0f8ff,#e3f1fd); border-color:#aacfef; }}
  .mr-balance-card.water {{ background:linear-gradient(160deg,#f0fbf6,#e2f5ec); border-color:#9fd4bc; }}
  .mr-balance-card strong {{ display:block; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin-bottom:8px; }}
  .mr-balance-card span {{ font-size:22px; font-weight:800; color:var(--ink); }}
  @media print {{
    body {{ padding:0; background:#fff; }}
    .mr-section, .mr-hero {{ box-shadow:none; break-inside:avoid; }}
    .mr-table th {{ background:#dde8f5 !important; }}
  }}
</style>
</head>
<body>
  <div class="mr-page">
    <section class="mr-hero">
      <div class="mr-hero-grid">
        <div>
          <h1 class="mr-title">Relatório Mensal de Fechamento e Validação</h1>
          <p class="mr-copy">Mês de referência: <strong>{_esc(meta.get("month_label") or meta.get("month") or "")}</strong> · {_esc(meta.get("mode_label") or "")}</p>
          <div class="mr-meta">{_summary_cards(summary)}</div>
        </div>
        <div class="mr-meta-note">
          <div><strong>Período:</strong> {_esc(_fmt_day(meta.get("date_from") or ""))} até {_esc(_fmt_day(meta.get("date_to") or ""))}</div>
          <div style="margin-top:8px"><strong>Gerado em:</strong> {_esc((meta.get("generated_at") or "").replace("T", " "))}</div>
          <div style="margin-top:8px"><strong>Regra:</strong> {_esc(meta.get("empty_rule") or "")}</div>
        </div>
      </div>
      <div class="mr-balance-row">
        <div class="mr-balance-card oil"><strong>MPFM Óleo (t)</strong><span>{_esc(_fmt_num(summary.get("mpfm_oil_t_sum")))}</span></div>
        <div class="mr-balance-card gas"><strong>MPFM Gás (t)</strong><span>{_esc(_fmt_num(summary.get("mpfm_gas_t_sum")))}</span></div>
        <div class="mr-balance-card water"><strong>MPFM Água (t)</strong><span>{_esc(_fmt_num(summary.get("mpfm_water_t_sum")))}</span></div>
        <div class="mr-balance-card oil"><strong>XML Óleo (sm³)</strong><span>{_esc(_fmt_num(summary.get("xml_oil_sm3_sum")))}</span></div>
        <div class="mr-balance-card gas"><strong>XML Gás (mil sm³)</strong><span>{_esc(_fmt_num(summary.get("xml_gas_1000sm3_sum")))}</span></div>
        <div class="mr-balance-card water"><strong>XML Água (sm³)</strong><span>{_esc(_fmt_num(summary.get("xml_water_sm3_sum")))}</span></div>
      </div>
    </section>
    {_xml_section(payload.get("xml_rows") or [])}
    {"".join(_group_section(group) for group in groups)}
    <section class="mr-section">
      <h2>Exceções e validação do mês</h2>
      <p class="mr-copy">Leitura operacional para pendências de cobertura, XML, reconciliação e aderência do separador.</p>
      <div class="mr-sections-grid">
        {_exception_block("Dias sem XML", exceptions.get("missing_xml") or [], "Sem faltas de XML no recorte.")}
        {_exception_block("Hourly incompleto", exceptions.get("missing_hours") or [], "Nenhum alerta de hourly incompleto.")}
        {_exception_block("Reconciliação parcial", exceptions.get("recon_partial") or [], "Nenhum dia com reconciliação parcial.")}
        {_exception_block("Status VERIFICAR", exceptions.get("verify") or [], "Nenhum status VERIFICAR registrado.")}
        {_exception_block("Separador / alinhamento", exceptions.get("separator") or [], "Nenhuma pendência do separador encontrada.")}
      </div>
    </section>
  </div>
  <script>
    (() => {{
      const MIN_WIDTH = 240;
      const MAX_WIDTH = 1200;

      function setExceptionsWidth(table, width) {{
        const nextWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, width));
        table.querySelectorAll('.mr-col-exceptions').forEach((cell) => {{
          cell.style.width = `${{nextWidth}}px`;
          cell.style.minWidth = `${{nextWidth}}px`;
        }});
      }}

      document.querySelectorAll('.mr-col-resizer[data-resize-col="exceptions"]').forEach((handle) => {{
        handle.addEventListener('pointerdown', (event) => {{
          const table = handle.closest('table');
          const header = handle.closest('.mr-col-exceptions');
          if (!table || !header) return;
          event.preventDefault();
          const startX = event.clientX;
          const startWidth = header.getBoundingClientRect().width;
          handle.classList.add('is-dragging');
          handle.setPointerCapture(event.pointerId);

          const onMove = (moveEvent) => {{
            const delta = moveEvent.clientX - startX;
            setExceptionsWidth(table, startWidth + delta);
          }};

          const onUp = () => {{
            handle.classList.remove('is-dragging');
            handle.removeEventListener('pointermove', onMove);
            handle.removeEventListener('pointerup', onUp);
            handle.removeEventListener('pointercancel', onUp);
          }};

          handle.addEventListener('pointermove', onMove);
          handle.addEventListener('pointerup', onUp);
          handle.addEventListener('pointercancel', onUp);
        }});

        handle.addEventListener('dblclick', () => {{
          const table = handle.closest('table');
          if (!table) return;
          setExceptionsWidth(table, 420);
        }});
      }});
    }})();

    const params = new URLSearchParams(window.location.search);
    if (params.get('print') === '1') {{
      window.addEventListener('load', () => setTimeout(() => window.print(), 220));
    }}
  </script>
</body>
</html>"""
