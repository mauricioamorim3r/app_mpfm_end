from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from routes.date_utils import normalize_date_input, normalize_date_range

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_TEMPLATE_FILES = {
    "rotina": "rotina_diaria_mpfm_offshore_en.html",
    "logbook": "logbook_documentos_en.html",
    "pvt": "analise_pvt_en.html",
}


def register_sgmfm_routes(app, ctx: dict) -> None:
    repo = ctx["repo"]
    load_cadastro = ctx["load_cadastro"]
    build_schema_payload = ctx["build_schema_payload"]
    build_record_summary = ctx["build_record_summary"]
    build_prefill_payload = ctx["build_prefill_payload"]
    render_record_html = ctx["render_record_html"]
    generate_record_code = ctx["generate_record_code"]
    normalize_tag_name = ctx["normalize_tag_name"]
    db_conn = ctx["db_conn"]

    def _ensure_type(record_type: str) -> str:
        value = str(record_type or "").strip().lower()
        if value not in {"rotina", "logbook", "pvt"}:
            raise HTTPException(404, "Tipo de registro inválido")
        return value

    @app.get("/api/sgmfm/summary")
    def api_sgmfm_summary():
        counts = repo.summary_counts()
        today = datetime.now().strftime("%Y-%m-%d")
        rotina_today = len(repo.list_records("rotina", date_from=today, date_to=today))
        return {"summary": counts, "rotina_today": rotina_today}

    @app.get("/api/sgmfm/schema")
    def api_sgmfm_schema(record_type: str):
        key = _ensure_type(record_type)
        visibility = repo.get_visibility_prefs(key)
        return build_schema_payload(key, load_cadastro_fn=load_cadastro, visibility=visibility)

    @app.get("/api/sgmfm/visibility/{record_type}")
    def api_sgmfm_visibility(record_type: str):
        key = _ensure_type(record_type)
        return repo.get_visibility_prefs(key)

    @app.post("/api/sgmfm/visibility/{record_type}")
    async def api_sgmfm_visibility_save(record_type: str, request: Request):
        key = _ensure_type(record_type)
        body = await request.json()
        repo.save_visibility_prefs(key, body.get("visible_keys") or [])
        return {"ok": True}

    @app.get("/api/sgmfm/{record_type}")
    def api_sgmfm_list(record_type: str, q: str = "", status: str = "", date_from: str = "", date_to: str = "", bank: str = "", tag: str = ""):
        key = _ensure_type(record_type)
        date_from, date_to = normalize_date_range(date_from, date_to)
        rows = repo.list_records(key, q=q, status=status, date_from=date_from, date_to=date_to, bank=bank, tag=tag)
        return {"items": rows}

    @app.get("/api/sgmfm/{record_type}/prefill")
    def api_sgmfm_prefill(record_type: str, point_id: str = "", base_date: str = "", reference_date: str = ""):
        key = _ensure_type(record_type)
        base_date = normalize_date_input(base_date)
        reference_date = normalize_date_input(reference_date)
        payload = build_prefill_payload(
            key,
            db_conn_fn=db_conn,
            load_cadastro_fn=load_cadastro,
            normalize_tag_name_fn=normalize_tag_name,
            point_id=point_id,
            base_date=base_date,
            reference_date=reference_date,
        )
        return {"payload": payload}

    @app.get("/api/sgmfm/template/{record_type}")
    def api_sgmfm_download_template(record_type: str):
        key = _ensure_type(record_type)
        filename = _TEMPLATE_FILES.get(key)
        if not filename:
            raise HTTPException(404, "Template não disponível para este tipo de registro")
        path = _TEMPLATES_DIR / filename
        if not path.exists():
            raise HTTPException(404, "Arquivo de template não encontrado")
        return FileResponse(
            path=str(path),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/sgmfm/{record_type}/{record_id}")
    def api_sgmfm_get(record_type: str, record_id: int):
        key = _ensure_type(record_type)
        record = repo.get_record(key, record_id)
        if not record:
            raise HTTPException(404, "Registro não encontrado")
        return {"record": record}

    @app.post("/api/sgmfm/{record_type}")
    async def api_sgmfm_save(record_type: str, request: Request):
        key = _ensure_type(record_type)
        body = await request.json()
        payload = body.get("payload") or {}
        summary = build_record_summary(key, payload)
        data = {
            "id": body.get("id"),
            "record_code": body.get("record_code") or payload.get("record_code") or generate_record_code(key, payload.get("base_date") or payload.get("reference_date") or ""),
            "title": summary["title"],
            "status": body.get("status") or summary["status"],
            "base_date": payload.get("base_date", ""),
            "reference_date": payload.get("reference_date", ""),
            "analysis_date": payload.get("analysis_date", ""),
            "measurement_point": payload.get("measurement_point", ""),
            "bank": payload.get("bank", ""),
            "tag": payload.get("tag", ""),
            "instrument": payload.get("instrument", ""),
            "loop": payload.get("loop", ""),
            "meter_type": payload.get("meter_type", ""),
            "generated_html": body.get("generated_html", ""),
            "generated_at": body.get("generated_at", ""),
            "payload": payload,
        }
        new_id = repo.upsert_record(key, data)
        return {"ok": True, "id": new_id}

    @app.delete("/api/sgmfm/{record_type}/{record_id}")
    def api_sgmfm_delete(record_type: str, record_id: int):
        key = _ensure_type(record_type)
        repo.delete_record(key, record_id)
        return {"ok": True}

    @app.post("/api/sgmfm/{record_type}/{record_id}/duplicate")
    def api_sgmfm_duplicate(record_type: str, record_id: int):
        key = _ensure_type(record_type)
        source = repo.get_record(key, record_id)
        if not source:
            raise HTTPException(404, "Registro não encontrado")
        new_code = generate_record_code(key, source.get("base_date") or source.get("reference_date") or "")
        new_id = repo.duplicate_record(key, record_id, new_code)
        return {"ok": True, "id": new_id}

    @app.post("/api/sgmfm/{record_type}/{record_id}/generate-html")
    def api_sgmfm_generate_html(record_type: str, record_id: int):
        key = _ensure_type(record_type)
        record = repo.get_record(key, record_id)
        if not record:
            raise HTTPException(404, "Registro não encontrado")
        generated_at = datetime.now().replace(microsecond=0).isoformat()
        html = render_record_html(key, {**record, "generated_at": generated_at})
        source_payload = record.get("payload") or {}
        repo.upsert_record(
            key,
            {
                **record,
                "generated_html": html,
                "generated_at": generated_at,
                "payload": source_payload,
            },
        )
        return {"ok": True, "generated_at": generated_at}

    @app.get("/api/sgmfm/{record_type}/{record_id}/html")
    def api_sgmfm_open_html(record_type: str, record_id: int, print: int = 0):
        key = _ensure_type(record_type)
        record = repo.get_record(key, record_id)
        if not record:
            raise HTTPException(404, "Registro não encontrado")
        html = record.get("generated_html") or render_record_html(key, record)
        if print:
            separator = "&" if "?" in html else "?"
            html = html.replace("params.get('print') === '1'", "true")
        return HTMLResponse(html)
