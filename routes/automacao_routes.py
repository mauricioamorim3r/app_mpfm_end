from __future__ import annotations
import os
import sys
import shutil
import tempfile
from datetime import timedelta
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
    def relatorio_base_unica(date_from: str = "", date_to: str = ""):
        # Gera o relatório exatamente como a automação (gerar_base_unica_standalone.py):
        # republica o dashboard a partir do consolidado BASE_UNICA_TOTAL.xlsx, sem reler
        # PDFs/TXTs e sem alterar o consolidado (apenas leitura).
        import gerar_base_unica_standalone as gb

        master_path = automacao_dir / "EXCEL_GERADOS" / "BASE_UNICA_TOTAL.xlsx"
        if not master_path.exists():
            master_path = automacao_dir / "BASE_UNICA_TOTAL.xlsx"
        if not master_path.exists():
            raise HTTPException(status_code=500, detail=f"Consolidado não encontrado: {master_path}")

        master_df = gb.read_master_base_unica(master_path)
        if master_df.empty:
            raise HTTPException(status_code=500, detail=f"{master_path.name} não contém dados na aba consolidada.")

        all_days = sorted({str(d) for d in master_df["ProductionDate"] if str(d).strip()})
        if date_from and date_to:
            selected_days = [d for d in all_days if date_from <= d <= date_to]
        else:
            selected_days = all_days[-gb.DAYS_COUNT:]
        if not selected_days:
            raise HTTPException(status_code=422, detail="Nenhum dia com dados no intervalo informado.")

        master_window = master_df[master_df["ProductionDate"].astype(str).isin(set(selected_days))].copy()
        try:
            master_alarm_events = gb.read_master_alarm_events(master_path)
        except Exception:
            master_alarm_events = None

        tmp_dir = Path(tempfile.mkdtemp(prefix="relatorio_base_unica_"))
        try:
            dashboard_path = tmp_dir / "BASE_UNICA_TOTAL_RELATORIO_COMPLETO.html"
            gb.publish_dashboard(
                dashboard_path,
                master_window,
                selected_days,
                selected_days,
                [],
                master_path,
                master_alarm_events,
                aligned_bank=gb.SEP_ALIGNED_BANK,
                preloaded_master_df=master_df,
                source_workbook_path=master_path,
            )
            html_content = dashboard_path.read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        return HTMLResponse(html_content)

    @app.get("/api/automacao/exportar-base-unica-excel")
    def exportar_base_unica_excel(date_from: str = "", date_to: str = ""):
        """
        Exporta dados da BASE_UNICA_TOTAL.xlsx filtrados por período para um novo Excel.
        Útil para preparar datasets de treinamento de modelos ML.
        """
        import pandas as pd

        master_path = automacao_dir / "EXCEL_GERADOS" / "BASE_UNICA_TOTAL.xlsx"
        if not master_path.exists():
            master_path = automacao_dir / "BASE_UNICA_TOTAL.xlsx"
        if not master_path.exists():
            raise HTTPException(status_code=500, detail=f"Consolidado não encontrado: {master_path}")

        try:
            # Lê a aba BASE_UNICA_TOTAL (dados consolidados)
            df = pd.read_excel(master_path, sheet_name="BASE_UNICA_TOTAL")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler consolidado: {str(e)}")

        if df.empty:
            raise HTTPException(status_code=500, detail="Consolidado não contém dados.")

        # Filtra por período se especificado
        if date_from and date_to:
            df["ProductionDate"] = pd.to_datetime(df["ProductionDate"], errors="coerce")
            mask = (df["ProductionDate"] >= date_from) & (df["ProductionDate"] <= date_to)
            df = df[mask].copy()
            if df.empty:
                raise HTTPException(status_code=422, detail=f"Nenhum dado encontrado entre {date_from} e {date_to}.")

        # Gera arquivo temporário
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        try:
            # Salva dados filtrados em novo Excel
            with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Base_Unica", index=False)
        except Exception as e:
            os.unlink(tmp.name)
            raise HTTPException(status_code=500, detail=f"Erro ao gerar Excel: {str(e)}")

        # Nome do arquivo
        if date_from and date_to:
            fname = f"BASE_UNICA_{date_from}_a_{date_to}.xlsx"
        else:
            fname = f"BASE_UNICA_EXPORT_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return FileResponse(
            tmp.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=fname,
            background=BackgroundTask(os.unlink, tmp.name),
        )
