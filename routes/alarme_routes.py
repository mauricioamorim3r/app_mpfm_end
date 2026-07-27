from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List

from fastapi import File, HTTPException, Request, UploadFile

from app_config import UPLOAD_DIR
from routes.date_utils import normalize_date_range
from services.alarme import (
    import_alarm_pdfs,
    import_alarm_workbook,
    inspect_alarm_workbook,
    normalize_alarm_action_payload,
    normalize_alarm_payload,
    preview_alarm_pdf_import,
    preview_alarm_workbook_import,
)


def register_alarme_routes(app, ctx: dict) -> None:
    repo = ctx["repo"]

    def _latest_alarm_workbook_path() -> Path | None:
        target_dir = Path(UPLOAD_DIR) / "alarmes"
        if not target_dir.exists():
            return None
        candidates = sorted(
            [path for path in target_dir.iterdir() if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm"}],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    def _latest_alarm_pdf_paths() -> list[Path]:
        """Return all PDFs in the alarmes upload folder, newest first."""
        target_dir = Path(UPLOAD_DIR) / "alarmes"
        if not target_dir.exists():
            return []
        return sorted(
            [p for p in target_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    @app.get("/api/alarmes/reference")
    def api_alarmes_reference():
        return {"catalog": repo.get_reference_catalog()}

    @app.get("/api/alarmes/summary")
    def api_alarmes_summary(source_ref: str = ""):
        return {"summary": repo.summary_counts(source_ref=source_ref)}

    @app.get("/api/alarmes")
    def api_alarmes_list(
        q: str = "",
        source_ref: str = "",
        record_type: str = "",
        status: str = "",
        severity: str = "",
        priority: str = "",
        category: str = "",
        family: str = "",
        bank: str = "",
        measurement_point: str = "",
        tag: str = "",
        owner: str = "",
        source_sheet: str = "",
        date_from: str = "",
        date_to: str = "",
        active_only: int = 1,
        limit: int = 0,
    ):
        date_from, date_to = normalize_date_range(date_from, date_to)
        items = repo.list_alarms(
            q=q,
            source_ref=source_ref,
            record_type=record_type,
            status=status,
            severity=severity,
            priority=priority,
            category=category,
            family=family,
            bank=bank,
            measurement_point=measurement_point,
            tag=tag,
            owner=owner,
            source_sheet=source_sheet,
            date_from=date_from,
            date_to=date_to,
            active_only=bool(active_only),
            limit=limit,
        )
        return {"items": items}

    @app.get("/api/alarmes/workbook-inspect")
    def api_alarmes_workbook_inspect(path: str):
        try:
            return inspect_alarm_workbook(path)
        except FileNotFoundError:
            raise HTTPException(404, "Workbook não encontrado")
        except Exception as exc:
            raise HTTPException(400, f"Falha ao inspecionar workbook: {exc}") from exc

    @app.get("/api/alarmes/workbook-preview")
    def api_alarmes_workbook_preview(path: str):
        try:
            return preview_alarm_workbook_import(path)
        except FileNotFoundError:
            raise HTTPException(404, "Workbook não encontrado")
        except Exception as exc:
            raise HTTPException(400, f"Falha ao gerar preview de importação: {exc}") from exc

    @app.get("/api/alarmes/latest-workbook-preview")
    def api_alarmes_latest_workbook_preview():
        latest_path = _latest_alarm_workbook_path()
        if not latest_path:
            raise HTTPException(404, "Nenhum workbook de alarmes foi enviado ainda")
        try:
            return {
                "file": {
                    "name": latest_path.name,
                    "saved_path": str(latest_path),
                    "modified_at": latest_path.stat().st_mtime,
                },
                "preview": preview_alarm_workbook_import(latest_path),
            }
        except Exception as exc:
            raise HTTPException(400, f"Falha ao ler o último workbook enviado: {exc}") from exc

    @app.post("/api/alarmes/import-workbook")
    async def api_alarmes_import_workbook(request: Request):
        body = await request.json()
        path = str(body.get("path") or "").strip()
        if not path:
            raise HTTPException(400, "path é obrigatório")
        try:
            return import_alarm_workbook(path, repo=repo)
        except FileNotFoundError:
            raise HTTPException(404, "Workbook não encontrado")
        except Exception as exc:
            raise HTTPException(400, f"Falha ao importar workbook: {exc}") from exc

    @app.post("/api/alarmes/upload-workbook")
    async def api_alarmes_upload_workbook(file: UploadFile = File(...)):
        original_name = str(file.filename or "alarme_mpfm.xlsx").strip() or "alarme_mpfm.xlsx"
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name)
        if not safe_name.lower().endswith((".xlsx", ".xlsm")):
            raise HTTPException(400, "Envie um arquivo Excel .xlsx ou .xlsm")
        target_dir = Path(UPLOAD_DIR) / "alarmes"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
        try:
            with target_path.open("wb") as handle:
                shutil.copyfileobj(file.file, handle)
        finally:
            await file.close()
        try:
            result = import_alarm_workbook(target_path, repo=repo)
            return {
                "ok": True,
                "file": {
                    "name": original_name,
                    "saved_path": str(target_path),
                },
                "import_result": result,
                "summary": repo.summary_counts(source_ref=str(target_path)),
            }
        except Exception as exc:
            raise HTTPException(400, f"Falha ao processar workbook enviado: {exc}") from exc

    @app.post("/api/alarmes/upload-pdfs")
    async def api_alarmes_upload_pdfs(files: List[UploadFile] = File(...)):
        if not files:
            raise HTTPException(400, "Envie ao menos um arquivo PDF")
        saved_paths: list[Path] = []
        target_dir = Path(UPLOAD_DIR) / "alarmes"
        target_dir.mkdir(parents=True, exist_ok=True)
        for upload in files:
            original_name = str(upload.filename or "alarme_fcs320.pdf").strip() or "alarme_fcs320.pdf"
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name)
            if not safe_name.lower().endswith(".pdf"):
                raise HTTPException(400, f"'{original_name}' não é um PDF. Envie somente arquivos .pdf")
            target_path = target_dir / safe_name
            try:
                with target_path.open("wb") as handle:
                    shutil.copyfileobj(upload.file, handle)
            finally:
                await upload.close()
            saved_paths.append(target_path)
        try:
            result = import_alarm_pdfs(saved_paths, repo=repo)
            return {
                "ok": True,
                "files": [{"name": p.name, "saved_path": str(p)} for p in saved_paths],
                "import_result": result,
                "summary": result.get("summary") or repo.summary_counts(source_ref=result["path"]),
            }
        except Exception as exc:
            raise HTTPException(400, f"Falha ao processar PDFs enviados: {exc}") from exc

    @app.get("/api/alarmes/latest-pdf-preview")
    def api_alarmes_latest_pdf_preview():
        pdf_paths = _latest_alarm_pdf_paths()
        if not pdf_paths:
            raise HTTPException(404, "Nenhum PDF de alarmes FCS320 foi enviado ainda")
        try:
            preview = preview_alarm_pdf_import(pdf_paths)
            return {
                "files": [{"name": p.name, "saved_path": str(p), "modified_at": p.stat().st_mtime} for p in pdf_paths],
                "file": {"name": pdf_paths[0].name, "saved_path": str(pdf_paths[0])},
                "preview": preview,
            }
        except Exception as exc:
            raise HTTPException(400, f"Falha ao ler os PDFs enviados: {exc}") from exc

    @app.get("/api/alarmes/{alarm_id}")
    def api_alarmes_get(alarm_id: int):
        record = repo.get_alarm(alarm_id)
        if not record:
            raise HTTPException(404, "Alarme não encontrado")
        return {
            "record": record,
            "actions": repo.list_actions(alarm_id),
            "audit": repo.list_audit(alarm_id),
        }

    @app.post("/api/alarmes")
    async def api_alarmes_save(request: Request):
        body = await request.json()
        payload = normalize_alarm_payload(body)
        if not payload.get("title"):
            raise HTTPException(400, "title é obrigatório")
        alarm_id = repo.save_alarm(payload)
        return {"ok": True, "id": alarm_id}

    @app.post("/api/alarmes/{alarm_id}/acknowledge")
    async def api_alarmes_acknowledge(alarm_id: int, request: Request):
        body = await request.json()
        try:
            repo.set_alarm_status(
                alarm_id,
                str(body.get("status_code") or "in_progress").strip().lower(),
                notes=str(body.get("notes") or "").strip(),
                acknowledged_by=str(body.get("acknowledged_by") or body.get("owner") or "").strip(),
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"ok": True}

    @app.post("/api/alarmes/{alarm_id}/close")
    async def api_alarmes_close(alarm_id: int, request: Request):
        body = await request.json()
        try:
            repo.set_alarm_status(alarm_id, "closed", notes=str(body.get("notes") or "").strip())
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"ok": True}

    @app.get("/api/alarmes/{alarm_id}/actions")
    def api_alarmes_actions(alarm_id: int):
        if not repo.get_alarm(alarm_id):
            raise HTTPException(404, "Alarme não encontrado")
        return {"items": repo.list_actions(alarm_id)}

    @app.post("/api/alarmes/{alarm_id}/actions")
    async def api_alarmes_add_action(alarm_id: int, request: Request):
        if not repo.get_alarm(alarm_id):
            raise HTTPException(404, "Alarme não encontrado")
        payload = normalize_alarm_action_payload(await request.json())
        if not payload.get("description"):
            raise HTTPException(400, "description é obrigatório")
        action_id = repo.add_action(alarm_id, payload)
        return {"ok": True, "id": action_id}
