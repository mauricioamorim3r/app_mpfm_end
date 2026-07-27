from __future__ import annotations

from datetime import datetime
import io
from pathlib import Path
import re
import zipfile

from fastapi import File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from routes.date_utils import normalize_date_input
from repositories.xml042 import Xml042Repository
from services.xml042 import (
    DEFAULT_AUTHOR,
    DEFAULT_XML042_CNPJ8,
    DEFAULT_XML042_DEST_DIR,
    build_xml042_import_workbook,
    build_xml042_seed_rows,
    generate_xml042_document,
    list_xml042_candidates,
    parse_xml042_import,
    summarize_imported_xml042,
)


def register_xml042_routes(app, ctx: dict) -> None:
    db_conn = ctx["db_conn"]
    output_dir = ctx["output_dir"]
    load_cadastro = ctx["load_cadastro"]
    normalize_tag_name = ctx["normalize_tag_name"]

    repo = Xml042Repository(db_conn, normalize_tag_name)
    repo.seed_catalog_if_empty(build_xml042_seed_rows(load_cadastro() or {}))

    @app.get("/api/xml042/catalog")
    def api_xml042_catalog(active_only: int = 0):
        return {"rows": repo.list_catalog(bool(active_only))}

    @app.post("/api/xml042/catalog")
    async def api_xml042_catalog_save(request: Request):
        body = await request.json()
        try:
            item_id = repo.upsert_catalog(body)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return {"ok": True, "id": item_id}

    @app.delete("/api/xml042/catalog/{item_id}")
    def api_xml042_catalog_delete(item_id: int):
        repo.delete_catalog(item_id)
        return {"ok": True}

    @app.get("/api/xml042/candidates")
    def api_xml042_candidates(month: str = "", day: str = "", bank: str = "", status: str = ""):
        day = normalize_date_input(day)
        return list_xml042_candidates(
            repo,
            month=month,
            production_day=day,
            bank=bank,
            status=status,
            normalize_tag_name=normalize_tag_name,
        )

    @app.post("/api/xml042/approve")
    async def api_xml042_approve(request: Request):
        body = await request.json()
        month = str(body.get("month") or "")[:7]
        production_day = normalize_date_input(body.get("production_day") or "")
        bank = str(body.get("bank") or "").strip().upper()
        well_operator_name = str(body.get("well_operator_name") or "").strip()
        subsea_tag = str(body.get("subsea_tag") or "").strip()
        candidates = list_xml042_candidates(
            repo,
            month=month,
            production_day=production_day,
            bank=bank,
            status="",
            normalize_tag_name=normalize_tag_name,
        )["rows"]
        target = None
        for row in candidates:
            if row["production_day"] == production_day and row["bank"] == bank and row["well_operator_name"] == well_operator_name and row["subsea_tag"] == subsea_tag:
                target = row
                break
        if not target:
            raise HTTPException(404, "Candidato não encontrado")
        if not target.get("eligible"):
            raise HTTPException(400, "Candidato não elegível para aprovação")
        item_id = repo.upsert_curated_candidate(
            {
                "production_day": target["production_day"],
                "bank": target["bank"],
                "well_operator_name": target["well_operator_name"],
                "subsea_tag": target["subsea_tag"],
                "source_daily_row_ref": target["source_daily_row_ref"],
                "oil_sm3_d_curated": target["oil_sm3"],
                "gas_sm3_d_raw": target["gas_sm3"],
                "gas_1000sm3_d_curated": target["gas_1000sm3"],
                "water_sm3_d_curated": target["water_sm3"],
                "catalog_match_status": target["catalog_match_status"],
                "catalog_match_id": target["catalog"]["id"],
                "qa_flags": target["qa_flags"],
                "approved_by_user": body.get("approved_by_user") or DEFAULT_AUTHOR,
                "approved_at": body.get("approved_at") or datetime.now().isoformat(timespec="seconds"),
            }
        )
        return {"ok": True, "id": item_id}

    @app.post("/api/xml042/generate")
    async def api_xml042_generate(request: Request):
        body = await request.json()
        month = str(body.get("month") or "")[:7]
        production_day = normalize_date_input(body.get("production_day") or "")
        bank = str(body.get("bank") or "").strip().upper()
        well_operator_name = str(body.get("well_operator_name") or "").strip()
        subsea_tag = str(body.get("subsea_tag") or "").strip()
        candidates = list_xml042_candidates(
            repo,
            month=month,
            production_day=production_day,
            bank=bank,
            status="",
            normalize_tag_name=normalize_tag_name,
        )["rows"]
        target = None
        for row in candidates:
            if row["production_day"] == production_day and row["bank"] == bank and row["well_operator_name"] == well_operator_name and row["subsea_tag"] == subsea_tag:
                target = row
                break
        if not target:
            raise HTTPException(404, "Candidato não encontrado")
        try:
            cnpj8 = str(body.get("cnpj8") or DEFAULT_XML042_CNPJ8).strip()
            if not re.fullmatch(r"\d{8}", cnpj8):
                raise ValueError("CNPJ 8 inválido. Use exatamente 8 dígitos.")
            target_dir_str = str(body.get("target_dir") or DEFAULT_XML042_DEST_DIR).strip()
            target_dir_path = Path(target_dir_str) if target_dir_str else None
            result = generate_xml042_document(
                repo,
                candidate=target,
                output_dir=Path(output_dir),
                cnpj8=cnpj8,
                author=str(body.get("generated_by") or DEFAULT_AUTHOR),
                target_dir=target_dir_path,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return {"ok": True, **result}

    @app.post("/api/xml042/batch-process")
    async def api_xml042_batch_process(request: Request):
        body = await request.json()
        month = str(body.get("month") or "")[:7]
        cnpj8 = str(body.get("cnpj8") or DEFAULT_XML042_CNPJ8).strip()
        if not re.fullmatch(r"\d{8}", cnpj8):
            raise HTTPException(400, "CNPJ 8 inválido. Use exatamente 8 dígitos.")

        target_dir_str = str(body.get("target_dir") or DEFAULT_XML042_DEST_DIR).strip()
        target_dir_path = Path(target_dir_str) if target_dir_str else None
        only_pending = bool(body.get("only_pending", True))
        author = str(body.get("generated_by") or DEFAULT_AUTHOR)

        candidates_data = list_xml042_candidates(
            repo,
            month=month,
            production_day="",
            bank=str(body.get("bank") or "").strip().upper(),
            status="",
            normalize_tag_name=normalize_tag_name,
        )
        all_rows = candidates_data.get("rows", [])

        to_process = []
        for row in all_rows:
            if not row.get("eligible"):
                continue
            if only_pending and row.get("generated"):
                continue
            to_process.append(row)

        success_count = 0
        error_count = 0
        saved_files = []
        errors = []
        now_str = datetime.now().isoformat(timespec="seconds")

        for row in to_process:
            try:
                if not row.get("approved"):
                    repo.upsert_curated_candidate(
                        {
                            "production_day": row["production_day"],
                            "bank": row["bank"],
                            "well_operator_name": row["well_operator_name"],
                            "subsea_tag": row["subsea_tag"],
                            "source_daily_row_ref": row["source_daily_row_ref"],
                            "oil_sm3_d_curated": row["oil_sm3"],
                            "gas_sm3_d_raw": row["gas_sm3"],
                            "gas_1000sm3_d_curated": row["gas_1000sm3"],
                            "water_sm3_d_curated": row["water_sm3"],
                            "catalog_match_status": row["catalog_match_status"],
                            "catalog_match_id": row["catalog"]["id"],
                            "qa_flags": row["qa_flags"],
                            "approved_by_user": author,
                            "approved_at": now_str,
                        }
                    )
                    row["approved"] = True
                    row["approved_at"] = now_str
                    row["approved_by_user"] = author

                gen_result = generate_xml042_document(
                    repo,
                    candidate=row,
                    output_dir=Path(output_dir),
                    cnpj8=cnpj8,
                    author=author,
                    target_dir=target_dir_path,
                )
                success_count += 1
                saved_files.append(
                    {
                        "production_day": row["production_day"],
                        "well": row["well_operator_name"],
                        "filename": gen_result["filename"],
                        "saved_to_target_dir": gen_result.get("saved_to_target_dir", False),
                        "target_file_path": gen_result.get("target_file_path", ""),
                    }
                )
            except Exception as exc:
                error_count += 1
                errors.append(
                    {
                        "production_day": row["production_day"],
                        "well": row["well_operator_name"],
                        "error": str(exc),
                    }
                )

        return {
            "ok": True,
            "processed_count": len(to_process),
            "success_count": success_count,
            "error_count": error_count,
            "target_dir": target_dir_str,
            "saved_files": saved_files,
            "errors": errors,
            "zip_download_url": f"/api/xml042/download-batch-zip?month={month}",
        }

    @app.get("/api/xml042/download-batch-zip")
    def api_xml042_download_batch_zip(month: str = ""):
        docs = repo.list_documents(month)
        if not docs:
            raise HTTPException(404, f"Nenhum XML 042 encontrado para o mês {month}")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in docs:
                p = Path(doc["file_path"])
                if p.exists():
                    zf.write(p, arcname=doc["filename"])
        buf.seek(0)
        zip_filename = f"xml042_lote_{month or 'todos'}.zip"
        return StreamingResponse(
            iter([buf.read()]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
        )

    @app.get("/api/xml042/documents")
    def api_xml042_documents(month: str = ""):
        return {"rows": repo.list_documents(month)}

    @app.post("/api/xml042/import")
    async def api_xml042_import(files: list[UploadFile] = File(...)):
        imported = []
        duplicates = []
        errors = []
        storage_dir = Path(output_dir) / "xml042_imported"
        storage_dir.mkdir(parents=True, exist_ok=True)

        for upload in files:
            name = Path(upload.filename or "").name
            if not name.lower().endswith(".xml"):
                errors.append({"filename": name or "arquivo-sem-nome", "message": "Arquivo ignorado: extensão inválida"})
                continue
            content = await upload.read()
            try:
                parsed = parse_xml042_import(content, name, repo=repo)
            except ValueError as exc:
                errors.append({"filename": name, "message": str(exc)})
                continue
            existing = repo.get_imported_file_by_hash(parsed["file_hash"])
            if existing:
                duplicates.append(
                    {
                        "filename": name,
                        "production_day": existing.get("production_day", ""),
                        "cod_cadastro_poco": existing.get("cod_cadastro_poco", ""),
                        "message": "Mesmo conteúdo já importado",
                    }
                )
                continue

            stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            stored_name = f"{stamp}_{name}"
            stored_path = storage_dir / stored_name
            stored_path.write_bytes(content)
            imported_at = datetime.now().isoformat(timespec="seconds")
            file_id = repo.save_imported_file(
                {
                    **parsed,
                    "filename": name,
                    "file_path": str(stored_path),
                    "file_size_bytes": len(content),
                    "import_status": "imported",
                    "import_message": "",
                    "imported_at": imported_at,
                }
            )
            row_id = repo.upsert_imported_row(
                {
                    **parsed,
                    "latest_file_id": file_id,
                }
            )
            imported.append(
                {
                    "id": row_id,
                    "filename": name,
                    "production_day": parsed["production_day"],
                    "cod_cadastro_poco": parsed["cod_cadastro_poco"],
                    "well_operator_name": parsed["well_operator_name"],
                    "bank": parsed["bank"],
                }
            )

        month_refs = sorted({item["production_day"][:7] for item in imported if item.get("production_day")})
        return {
            "ok": True,
            "imported": imported,
            "duplicates": duplicates,
            "errors": errors,
            "summary": {
                "imported": len(imported),
                "duplicates": len(duplicates),
                "errors": len(errors),
                "months": month_refs,
            },
        }

    @app.get("/api/xml042/imported")
    def api_xml042_imported(month: str = "", cod_cadastro_poco: str = ""):
        rows = repo.list_imported_rows(month=month, cod_cadastro_poco=cod_cadastro_poco)
        files = repo.list_imported_files(month=month, cod_cadastro_poco=cod_cadastro_poco)
        return {
            "rows": rows,
            "files": files,
            "summary": summarize_imported_xml042(rows, files),
        }

    @app.get("/api/xml042/imported-export")
    def api_xml042_imported_export(month: str = "", cod_cadastro_poco: str = ""):
        rows = repo.list_imported_rows(month=month, cod_cadastro_poco=cod_cadastro_poco)
        buffer = build_xml042_import_workbook(rows)
        suffix = month or "periodo"
        filename = f"xml042_importados_{suffix}.xlsx"
        return StreamingResponse(
            iter([buffer.read()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/xml042/download/{item_id}")
    def api_xml042_download(item_id: int):
        row = repo.get_document(item_id)
        if not row:
            raise HTTPException(404, "Documento não encontrado")
        path = Path(row["file_path"])
        if not path.exists():
            raise HTTPException(404, "Arquivo XML não encontrado em disco")
        return FileResponse(str(path), filename=row["filename"], media_type="application/xml")
