from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from routes.date_utils import normalize_date_range
from services.mpfm_adjustment_workbook_service import export_adjustment_workbook, import_adjustment_workbook


def register_mpfm_adjustment_routes(app, ctx: dict) -> None:
    db_conn = ctx["db_conn"]
    invalidate_cache = ctx.get("invalidate_cache")

    def _cleanup(path: str) -> None:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    async def _save_upload(file: UploadFile) -> Path:
        filename = Path(file.filename or "ajustes_mpfm.xlsx").name
        if not filename.lower().endswith(".xlsx"):
            raise HTTPException(400, "Envie um arquivo .xlsx exportado pela aplicação.")
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        temp_path = Path(temp.name)
        try:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                temp.write(chunk)
        finally:
            temp.close()
        return temp_path

    @app.get("/api/mpfm-adjustments/export")
    def api_mpfm_adjustments_export(date_from: str = "", date_to: str = "", bank: str = "", tag: str = ""):
        date_from, date_to = normalize_date_range(date_from, date_to)
        temp_path = export_adjustment_workbook(db_conn, date_from, date_to, bank=bank, tag=tag)
        safe_from = date_from or "inicio"
        safe_to = date_to or safe_from
        suffix = f"_{bank}" if bank else ""
        filename = f"registro_ajustes_mpfm_{safe_from}_{safe_to}{suffix}.xlsx"
        return FileResponse(
            temp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
            background=BackgroundTask(_cleanup, temp_path),
        )

    @app.post("/api/mpfm-adjustments/import/preview")
    async def api_mpfm_adjustments_import_preview(file: UploadFile = File(...)):
        temp_path = await _save_upload(file)
        try:
            return import_adjustment_workbook(db_conn, temp_path, author="preview", apply=False, source_name=file.filename or "")
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        finally:
            _cleanup(str(temp_path))

    @app.post("/api/mpfm-adjustments/import/apply")
    async def api_mpfm_adjustments_import_apply(
        file: UploadFile = File(...),
        author: str = Form(""),
        notes: str = Form(""),
    ):
        temp_path = await _save_upload(file)
        try:
            result = import_adjustment_workbook(db_conn, temp_path, author=author, notes=notes, apply=True, source_name=file.filename or "")
            if callable(invalidate_cache):
                try:
                    invalidate_cache()
                except Exception:
                    pass
            return result
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        finally:
            _cleanup(str(temp_path))
