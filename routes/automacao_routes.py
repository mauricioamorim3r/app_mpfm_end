from __future__ import annotations
import os
import sys
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask


class PetecRequest(BaseModel):
    date_from: str
    date_to: str


def register_automacao_routes(app, ctx: dict) -> None:
    db_path: Path = ctx["db_path"]
    automacao_dir = Path(__file__).resolve().parents[1] / "AUTOMACAO_HTML"

    if str(automacao_dir) not in sys.path:
        sys.path.insert(0, str(automacao_dir))

    @app.post("/api/automacao/gerar-petec")
    def gerar_petec(req: PetecRequest):
        import preencher_petec as pp
        from openpyxl import load_workbook

        try:
            first = pp.parse_datetime(req.date_from, end_of_day=False)
            last  = pp.parse_datetime(req.date_to,   end_of_day=True)
            first, last, _ = pp.normalize_window(first, last)
            if last < first or last - first > timedelta(hours=24):
                raise ValueError("A janela PETEC deve ter no máximo 24 horas.")
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        template = automacao_dir / "dados para PETEC.xlsx"
        if not template.exists():
            raise HTTPException(status_code=500, detail=f"Template não encontrado: {template}")
        if not db_path.exists():
            raise HTTPException(status_code=500, detail=f"Banco não encontrado: {db_path}")

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        try:
            shutil.copy2(template, tmp.name)
            df = pp.load_window_from_db(db_path, first, last)
            sep_rows = pp.load_sep_window_from_db(db_path, first, last)
            book = load_workbook(tmp.name)
            pp.fill_mpfm(book["MPFM"], df)
            pp.fill_sep(book["separador óleo "], sep_rows, "oil", first)
            pp.fill_sep(book["separador gás"], sep_rows, "gas", first)
            pp.fill_sep(book["separador agua"], sep_rows, "water", first)
            for ws in book.worksheets:
                ws.sheet_view.showGridLines = False
            book.save(tmp.name)
        except Exception as e:
            os.unlink(tmp.name)
            raise HTTPException(status_code=500, detail=str(e))

        fname = f"PETEC_{first:%Y%m%d}_{last:%Y%m%d}.xlsx"
        return FileResponse(
            tmp.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=fname,
            background=BackgroundTask(os.unlink, tmp.name),
        )

    @app.get("/api/automacao/relatorio-base-unica")
    def relatorio_base_unica(date_from: str = "", date_to: str = "", bank: str = ""):
        if not db_path.exists():
            raise HTTPException(status_code=500, detail=f"Banco não encontrado: {db_path}")

        import gerar_relatorio_db as gr

        conn = gr.conn_open(str(db_path))
        cur  = conn.cursor()
        try:
            df = date_from
            dt = date_to
            if not df or not dt:
                row = cur.execute(
                    "SELECT MIN(day_ref), MAX(day_ref) FROM measurements_active"
                ).fetchone()
                if not df:
                    df = row[0] or ""
                if not dt:
                    dt = row[1] or ""
            period = f"{df} a {dt}" + (f" · Banco: {bank}" if bank else "")
            data = {
                "executivo":   gr.q_executivo(cur, df, dt, bank),
                "comparacoes": gr.q_comparacoes(cur, df, dt),
                "separador":   gr.q_separador(cur, df, dt),
                "cobertura":   gr.q_cobertura(cur, df, dt),
                "pi":          gr.q_pi_vision(cur),
                "alarmes":     gr.q_alarmes(cur, df, dt),
                "detalhes":    gr.q_detalhes(cur, df, dt, bank),
                "auditoria":   gr.q_auditoria(cur),
                "validacao":   gr.q_validacao(cur),
                "xml042":      gr.q_xml042(cur, df, dt),
            }
        finally:
            conn.close()

        meta = {
            "db": str(db_path),
            "period": period,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        html_content = gr.build_html(data, meta)
        return HTMLResponse(html_content)
