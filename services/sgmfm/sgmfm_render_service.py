from __future__ import annotations

from datetime import datetime
import html

from .sgmfm_service import get_record_definition


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _fmt(value) -> str:
    text = str(value or "").strip()
    return text or "—"


def _render_field(label: str, value) -> str:
    return f"""
    <div class="field">
      <div class="field__label">{_esc(label)}</div>
      <div class="field__value">{_esc(_fmt(value))}</div>
    </div>
    """


def _render_repeatable(section: dict, rows: list[dict]) -> str:
    cols = section.get("columns") or []
    if not rows:
        return f"<div class='empty'>Sem registros em {html.escape(section['label'])}.</div>"
    header = "".join(f"<th>{_esc(col['label'])}</th>" for col in cols)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{_esc(_fmt(row.get(col['key'], '')))}</td>" for col in cols) + "</tr>")
    return f"""
    <div class="tablewrap">
      <table>
        <thead><tr>{header}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """


def render_record_html(record_type: str, record: dict) -> str:
    definition = get_record_definition(record_type)
    payload = record.get("payload") or {}
    grouped: dict[str, list[dict]] = {}
    for field in definition.get("fields") or []:
        grouped.setdefault(field["section"], []).append(field)

    sections_html = []
    for section in definition.get("sections") or []:
        field_html = "".join(_render_field(field["label"], payload.get(field["key"])) for field in grouped.get(section["id"], []))
        sections_html.append(
            f"""
            <section class="section">
              <h2>{_esc(section['label'])}</h2>
              <div class="field-grid">{field_html}</div>
            </section>
            """
        )
    for repeatable in definition.get("repeatable_sections") or []:
        sections_html.append(
            f"""
            <section class="section">
              <h2>{_esc(repeatable['label'])}</h2>
              {_render_repeatable(repeatable, payload.get(repeatable['id']) or [])}
            </section>
            """
        )

    generated_at = record.get("generated_at") or datetime.now().replace(microsecond=0).isoformat()
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(definition['title'])}</title>
<style>
  :root {{
    --bg:#f4f7fb; --panel:#ffffff; --ink:#1d2530; --muted:#5f6b7a; --line:#d7dde6;
    --brand:#002060; --accent:#ef2b2d;
    font-family: "Segoe UI", system-ui, sans-serif;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); padding:24px; }}
  .page {{ max-width:1180px; margin:0 auto; }}
  .hero {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:24px; margin-bottom:18px; }}
  .hero h1 {{ margin:0 0 6px; color:var(--brand); font-size:28px; }}
  .hero p {{ margin:0; color:var(--muted); }}
  .meta {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-top:16px; }}
  .meta-card {{ background:#f7f9fc; border:1px solid var(--line); border-radius:14px; padding:12px; }}
  .meta-card .k {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
  .meta-card .v {{ margin-top:4px; font-weight:700; color:var(--brand); }}
  .section {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:18px; margin-bottom:16px; }}
  .section h2 {{ margin:0 0 12px; font-size:18px; color:var(--brand); }}
  .field-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
  .field {{ background:#f9fbff; border:1px solid var(--line); border-radius:12px; padding:10px 12px; }}
  .field__label {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin-bottom:6px; }}
  .field__value {{ white-space:pre-wrap; }}
  .tablewrap {{ overflow:auto; border:1px solid var(--line); border-radius:12px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ border-bottom:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
  th {{ background:#eef3f9; color:var(--brand); position:sticky; top:0; }}
  .empty {{ color:var(--muted); padding:10px 0; }}
  @media print {{
    body {{ background:#fff; padding:0; }}
    .section,.hero {{ break-inside:avoid; box-shadow:none; }}
  }}
</style>
</head>
<body>
  <div class="page">
    <div class="hero">
      <h1>{_esc(definition['title'])}</h1>
      <p>Registro gerado na aplicação local do MPFM Manager.</p>
      <div class="meta">
        <div class="meta-card"><div class="k">Código</div><div class="v">{_esc(record.get('record_code') or '')}</div></div>
        <div class="meta-card"><div class="k">Status</div><div class="v">{_esc(record.get('status') or '')}</div></div>
        <div class="meta-card"><div class="k">Ponto</div><div class="v">{_esc(record.get('measurement_point') or record.get('tag') or '')}</div></div>
        <div class="meta-card"><div class="k">Gerado em</div><div class="v">{_esc(generated_at)}</div></div>
      </div>
    </div>
    {''.join(sections_html)}
  </div>
  <script>
    const params = new URLSearchParams(window.location.search);
    if (params.get('print') === '1') {{
      window.addEventListener('load', () => setTimeout(() => window.print(), 200));
    }}
  </script>
</body>
</html>"""
