#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador EXTERNO/STANDALONE de tabela Base_Unica (MPFM + SEP_Dados).

Este script é INDEPENDENTE do app_mpfm_end: não usa o banco de dados
(data/mpfm_local.db), não usa server.py/routes/ como servidor, e NÃO é
chamado por nenhuma rota/botão da aplicação. É pensado para rodar "por fora",
manualmente, sempre que alguém precisar de uma planilha Base_Unica pontual
com os últimos dias disponíveis de MPFM + Separador de Testes.

O QUE ELE FAZ
-------------
1. Varre as pastas de PDFs MPFM (Daily/Hourly) dos 6 bancos e descobre quais
   são os últimos N dias (padrão 5) com relatório Daily disponível.
2. Localiza os 3 TXT do Separador de Testes (óleo/gás/água) para cada um
   desses dias (pastas FC13/FC14/FC17), quando existirem.
3. Reaproveita as regras de extração JÁ VALIDADAS do próprio repositório
   (mpfm_engine.parse_pdf / build_*_df / parse_sep_txt_set) para não duplicar
   lógica de regex/parsing frágil.
4. Monta linhas no MESMO formato de colunas da aba BASE_UNICA_MES usada pelo
   app (uma linha por hora/dia/banco/tag), mesclando o SEP na MESMA linha do
   banco configurado em SEP_ALIGNED_BANK (o alinhamento é passado aqui como
   parâmetro/config — não existe tabela sep_alignments neste modo standalone).
5. Escreve um .xlsx simples (uma aba) com o resultado.

DEPENDÊNCIAS DE ARQUIVOS (para rodar fora deste repositório, copie também):
  - mpfm_engine.py
  - services/importing/sep_folder_scan_service.py
  - services/importing/input_classification_service.py
  - routes/date_utils.py
(mantendo a mesma estrutura de pastas relativa, pois são importados como
módulos Python normais). O restante da lógica deste arquivo é autocontido.

CONFIGURAÇÃO
------------
Ajuste as constantes na seção "CONFIG" abaixo antes de rodar.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG — ajuste antes de rodar
# ─────────────────────────────────────────────────────────────────────────────

# Raiz onde ficam as pastas 3.1.x de cada banco (relatórios Daily/Hourly em PDF)
MPFM_ROOT = Path(
    r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM"
)

# Raiz onde ficam as pastas de "Daily Reports" com FC13/FC14/FC17 (TXT do SEP)
SEP_ROOT = Path(
    r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 01 FPSO Bacalhau - Metering Management\03 REPORTS\00 - Daily Reports"
)

# Pasta de cada banco dentro de MPFM_ROOT
BANK_FOLDERS = {
    "B03": "3.1.1_13-FT-0367 Riser P5 - Topside B03",
    "B08": "3.1.2_13-FT-0167 Riser P2 - Topside B08",
    "B13": "3.1.3_13-FT-0317 Riser P4 - Topside B13",
    "B05": "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05",
    "B10": "3.1.5_18-FT-0506 PE 2 - Subsea B10",
    "B15": "3.1.6_18-FT-1106 PW_104DA - Subsea B15",
}

# Quantos dias (mais recentes disponíveis) exportar
DAYS_COUNT = 5

# Banco ao qual o Separador de Testes deve ser "alinhado" (mesclado na mesma
# linha). Não existe DB neste modo standalone, então isso é passado aqui.
SEP_ALIGNED_BANK = "B10"

# Arquivo de saída (se relativo, é criado ao lado deste script)
OUTPUT_PATH = Path(__file__).resolve().parent / f"BASE_UNICA_EXTERNA_{datetime.now():%Y%m%d_%H%M%S}.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap de imports (repo ao lado deste script)
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import mpfm_engine as engine  # noqa: E402
from services.importing.sep_folder_scan_service import scan_sep_folder  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# Constantes reaproveitadas do app (copiadas para manter este script autocontido)
# ─────────────────────────────────────────────────────────────────────────────

MONTH_PT = {
    1: "01. Janeiro", 2: "02. Fevereiro", 3: "03. Março", 4: "04. Abril",
    5: "05. Maio", 6: "06. Junho", 7: "07. Julho", 8: "08. Agosto",
    9: "09. Setembro", 10: "10. Outubro", 11: "11. Novembro", 12: "12. Dezembro",
}

# services/importing/import_pipeline_service.py — usado apenas como referência
# de fallback (não é necessário para este script pois já conhecemos o banco
# pela própria pasta que estamos varrendo).
INSTRUMENT_TO_BANK = {
    '18FT0506': 'B10', '18FT0306': 'B10', '18FT0106': 'B10',
    '18FT1506': 'B05', '18FT1406': 'B05', '18FT1706': 'B05', '18FT1806': 'B05',
    '18FT0706': 'B15', '18FT0906': 'B15', '18FT1206': 'B15', '18FT1106': 'B15',
    '13FT0167': 'B08', '13FT0217': 'B08',
    '13FT0267': 'B13', '13FT0317': 'B13',
    '13FT0367': 'B03', '13FT0417': 'B03',
}

# services/importing/monthly_workbook_service.py — colunas da Base_Unica
BASE_UNICA_COLUMNS = [
    "ProductionDate", "Hour", "Granularity", "Origin", "SourceType", "Area", "System", "Bank", "Loop", "Tipo", "Entity", "Tag", "Instrumento", "PI Tag",
    "MPFM uncorr Gás (t)", "MPFM uncorr Óleo (t)", "MPFM uncorr HC (t)", "MPFM uncorr Água (t)", "MPFM uncorr Total (t)",
    "MPFM corr Gás (t)", "MPFM corr Óleo (t)", "MPFM corr HC (t)", "MPFM corr Água (t)", "MPFM corr Total (t)",
    "PVT mass Gás (t)", "PVT mass Óleo (t)", "PVT mass HC (t)", "PVT mass Água (t)", "PVT mass Total (t)",
    "PVT vol Gás (Sm³)", "PVT vol Óleo (m³)", "PVT vol HC (m³)", "PVT vol Água (m³)", "PVT vol Total (m³)",
    "PVT @20 mass Gás (t)", "PVT @20 mass Óleo (t)", "PVT @20 mass HC (t)", "PVT @20 mass Água (t)", "PVT @20 mass Total (t)",
    "PVT @20 vol Gás (Sm³)", "PVT @20 vol Óleo (m³)", "PVT @20 vol HC (m³)", "PVT @20 vol Água (m³)", "PVT @20 vol Total (m³)",
    "Pressão (barg)", "Temperatura (°C)", "Dens. Gás (kg/m³)", "Dens. Óleo (kg/m³)", "Dens. Água (kg/m³)",
    "SEP TAG", "SEP Medidor", "SEP Local", "SEP Status", "Bancos alinhados",
    "SEP Óleo Vol. Bruto (m³) CV", "SEP Óleo (t) CV", "SEP Gás (t) CV", "SEP Água (t) CV", "SEP HC (t)", "SEP Total (t)", "SEP Temperatura Méd. (°C)", "SEP Pressão Méd. (barg)",
    "Desvio HC (%)", "Desvio Total (%)",
    "Recon Cobertura", "Recon Horas", "Recon Daily Gás (t)", "Recon Daily Óleo (t)", "Recon Daily HC (t)", "Recon Daily Água (t)",
    "Recon Soma h. Gás (t)", "Recon Soma h. Óleo (t)", "Recon Soma h. HC (t)", "Recon Soma h. Água (t)",
    "Recon Δ Gás (t)", "Recon Δ Óleo (t)", "Recon Δ HC (t)", "Recon Δ Água (t)",
    "Status Gás", "Status Óleo", "Status HC", "Status Água", "Fonte", "SourceFile", "IsOfficial",
]

RECON_MAP = {
    "Cobertura": "Recon Cobertura",
    "Horas": "Recon Horas",
    "Daily Gás (t)": "Recon Daily Gás (t)",
    "Daily Óleo (t)": "Recon Daily Óleo (t)",
    "Daily HC (t)": "Recon Daily HC (t)",
    "Daily Água (t)": "Recon Daily Água (t)",
    "Soma h. Gás (t)": "Recon Soma h. Gás (t)",
    "Soma h. Óleo (t)": "Recon Soma h. Óleo (t)",
    "Soma h. HC (t)": "Recon Soma h. HC (t)",
    "Soma h. Água (t)": "Recon Soma h. Água (t)",
    "Δ Gás (t)": "Recon Δ Gás (t)",
    "Δ Óleo (t)": "Recon Δ Óleo (t)",
    "Δ HC (t)": "Recon Δ HC (t)",
    "Δ Água (t)": "Recon Δ Água (t)",
    "Status Gás": "Status Gás",
    "Status Óleo": "Status Óleo",
    "Status HC": "Status HC",
    "Status Água": "Status Água",
}


def _mpfm_hour_from_sep_hour(sep_hour_ref):
    """TXT do separador numera hora 1-24; PDFs MPFM numeram 0-23 (24 -> 0)."""
    if sep_hour_ref is None:
        return None
    try:
        hour = int(sep_hour_ref)
    except Exception:
        return None
    return 0 if hour == 24 else hour


def _sep_desvio_pct(mpfm_value, sep_value):
    try:
        if mpfm_value in (None, "") or sep_value in (None, ""):
            return ""
        mpfm_f = float(mpfm_value)
        sep_f = float(sep_value)
        if sep_f == 0:
            return ""
        return round((mpfm_f - sep_f) / sep_f * 100, 2)
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Descoberta de dias disponíveis (PDF Daily) por banco
# ─────────────────────────────────────────────────────────────────────────────

def _months_to_scan(reference: datetime, back: int = 2):
    """Retorna lista de (year, month) cobrindo o mês atual e os `back` meses
    anteriores, para lidar com a virada de mês perto do início do mês."""
    months = []
    y, m = reference.year, reference.month
    for _ in range(back + 1):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return months


def _bank_month_dir(bank_code: str, year: int, month: int, sub: str) -> Path:
    return MPFM_ROOT / BANK_FOLDERS[bank_code] / str(year) / MONTH_PT[month] / sub


_FILENAME_DATE_RE = re.compile(r"-(\d{8})-")


def _filename_date_iso(path: Path) -> str | None:
    """Extrai a data (YYYY-MM-DD) embutida no nome do arquivo, ex.:
    B10_MPFM_Daily-20260803-000000+0000.pdf -> '2026-08-03'.
    Usado só para FILTRAR quais PDFs vale a pena abrir/parsear — o dia
    "de verdade" de cada registro sempre vem do conteúdo (parse_pdf)."""
    m = _FILENAME_DATE_RE.search(path.name)
    if not m:
        return None
    raw = m.group(1)
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def _candidate_daily_paths(bank_code: str, months: list, keep: int) -> list:
    """Lista (sem parsear) os PDFs Daily mais recentes pelo nome do arquivo,
    limitando a quantidade de PDFs que precisarão ser abertos."""
    paths = []
    for year, month in months:
        daily_dir = _bank_month_dir(bank_code, year, month, "Daily")
        if daily_dir.is_dir():
            paths.extend(daily_dir.glob(f"{bank_code}_MPFM_Daily-*.pdf"))
    paths.sort(key=lambda p: _filename_date_iso(p) or "", reverse=True)
    return paths[:keep]


def discover_daily_records(bank_code: str, months: list, keep: int) -> dict:
    """Faz parse apenas dos `keep` PDFs Daily mais recentes (pelo nome do
    arquivo) do banco, e retorna {date_from (conteúdo real): (pdf_path, record)}.
    """
    out = {}
    for pdf_path in _candidate_daily_paths(bank_code, months, keep):
        try:
            record = engine.parse_pdf(str(pdf_path), "daily")
        except Exception as exc:
            print(f"  ⚠️  falha ao ler {pdf_path.name}: {exc}")
            continue
        day = record.get("date_from")
        if not day:
            continue
        out.setdefault(day, (pdf_path, record))
    return out


def discover_hourly_records_for_days(bank_code: str, months: list, target_days: set) -> dict:
    """Localiza (pelo nome do arquivo) só os PDFs Hourly cuja data no nome
    seja um dos `target_days` ou o dia seguinte (a hora 0 do dia D é
    reportada em um arquivo datado D+1), parseia apenas esses, e agrupa por
    dia de conteúdo real (record['date_from'])."""
    relevant_names = set(target_days)
    for d in target_days:
        dt = datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)
        relevant_names.add(dt.strftime("%Y-%m-%d"))

    by_day = defaultdict(list)
    for year, month in months:
        hourly_dir = _bank_month_dir(bank_code, year, month, "Hourly")
        if not hourly_dir.is_dir():
            continue
        for pdf_path in sorted(hourly_dir.glob(f"{bank_code}_MPFM_Hourly-*.pdf")):
            if _filename_date_iso(pdf_path) not in relevant_names:
                continue
            try:
                record = engine.parse_pdf(str(pdf_path), "hourly")
            except Exception as exc:
                print(f"  ⚠️  falha ao ler {pdf_path.name}: {exc}")
                continue
            day = record.get("date_from")
            hour = record.get("hour")
            if not day or hour is None or day not in target_days:
                continue
            by_day[day].append(record)
    return by_day


# ─────────────────────────────────────────────────────────────────────────────
# SEP: localizar e parsear os 3 TXT (óleo/gás/água) de um dia
# ─────────────────────────────────────────────────────────────────────────────

def load_sep_data_for_days(days_iso: list) -> dict:
    """Usa scan_sep_folder (já validado no app) para localizar os TXT do
    separador cobrindo o intervalo de dias solicitado. Retorna
    {day_iso: {'oleo': path, 'gas': path, 'agua': path}} apenas para dias com
    o trio completo."""
    if not days_iso:
        return {}
    date_from = min(days_iso)
    date_to = max(days_iso)
    candidates, selected, preview = scan_sep_folder(
        SEP_ROOT, date_from=date_from, date_to=date_to, include_incomplete_days=True
    )
    by_day = defaultdict(dict)
    fluid_key = {"sep_oleo": "oleo", "sep_gas": "gas", "sep_agua": "agua"}
    for item in candidates:
        key = fluid_key.get(item.fluid_kind)
        if not key or item.content_date not in days_iso:
            continue
        by_day[item.content_date][key] = item.path

    result = {}
    for day, phases in by_day.items():
        if all(k in phases for k in ("oleo", "gas", "agua")):
            result[day] = phases
        else:
            missing = [k for k in ("oleo", "gas", "agua") if k not in phases]
            print(f"  ⚠️  SEP incompleto em {day}: faltando {', '.join(missing)} — dia ignorado no merge SEP")
    return result


def parse_sep_data(day_iso: str, paths: dict) -> dict | None:
    if not paths:
        return None
    try:
        return engine.parse_sep_txt_set(paths["oleo"], paths["gas"], paths["agua"])
    except Exception as exc:
        print(f"  ⚠️  falha ao ler TXT do SEP em {day_iso}: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Conversão dos DataFrames legados (mpfm_engine) -> linhas Base_Unica
# ─────────────────────────────────────────────────────────────────────────────

SEP_COLS_PASSTHROUGH = [
    "SEP Temperatura Méd. (°C)", "SEP Pressão Méd. (barg)", "SEP Óleo Vol. Bruto (m³) CV",
    "SEP Óleo (t) CV", "SEP Gás (t) CV", "SEP Água (t) CV", "SEP HC (t)", "SEP Total (t)",
    "Desvio HC (%)", "Desvio Total (%)",
]


def _new_row() -> dict:
    return {col: "" for col in BASE_UNICA_COLUMNS}


def hourly_df_to_rows(df, sep_merged: bool) -> list:
    rows = []
    for _, r in df.iterrows():
        row = _new_row()
        row.update({
            "ProductionDate": r["Dia ref."],
            "Hour": r["Hora"],
            "Granularity": "Hourly",
            "Origin": "MPFM",
            "SourceType": "PDF",
            "Bank": r["Bank"],
            "Loop": r["Loop"],
            "Tipo": r["Tipo"],
            "Entity": r["TAG"],
            "Tag": r["TAG"],
            "Instrumento": r["Instrumento"],
            "Fonte": "MPFM",
            "SourceFile": r["Fonte"],
            "IsOfficial": 1,
        })
        for col in BASE_UNICA_COLUMNS:
            if col in df.columns and col not in row:
                row[col] = r[col]
        for col in [
            "MPFM uncorr Gás (t)", "MPFM uncorr Óleo (t)", "MPFM uncorr HC (t)", "MPFM uncorr Água (t)", "MPFM uncorr Total (t)",
            "MPFM corr Gás (t)", "MPFM corr Óleo (t)", "MPFM corr HC (t)", "MPFM corr Água (t)", "MPFM corr Total (t)",
            "PVT mass Gás (t)", "PVT mass Óleo (t)", "PVT mass Água (t)",
            "PVT vol Gás (Sm³)", "PVT vol Óleo (m³)", "PVT vol Água (m³)",
            "PVT @20 mass Gás (t)", "PVT @20 mass Óleo (t)", "PVT @20 mass Água (t)",
            "PVT @20 vol Gás (Sm³)", "PVT @20 vol Óleo (m³)", "PVT @20 vol Água (m³)",
            "Pressão (barg)", "Temperatura (°C)", "Dens. Gás (kg/m³)", "Dens. Óleo (kg/m³)", "Dens. Água (kg/m³)",
        ]:
            row[col] = r[col]
        if sep_merged:
            for col in SEP_COLS_PASSTHROUGH:
                if col in df.columns:
                    row[col] = r[col]
            row["SEP TAG"] = "SEP_Dados"
            row["SEP Medidor"] = "20FT0244/20FT0247/20FT0251"
            row["SEP Local"] = "Separador de Testes"
            row["SEP Status"] = "Alinhado"
            row["Bancos alinhados"] = row["Bank"]
        rows.append(row)
    return rows


def daily_df_to_rows(df, sep_day: dict | None) -> list:
    rows = []
    for _, r in df.iterrows():
        row = _new_row()
        row.update({
            "ProductionDate": r["Dia"],
            "Hour": "",
            "Granularity": "Daily",
            "Origin": "MPFM",
            "SourceType": "PDF",
            "Bank": r["Bank"],
            "Loop": r["Loop"],
            "Tipo": r["Tipo"],
            "Entity": r["TAG"],
            "Tag": r["TAG"],
            "Instrumento": r["Instrumento"],
            "Fonte": "MPFM",
            "SourceFile": r["Fonte (Daily)"],
            "IsOfficial": 1,
        })
        for col in [
            "MPFM uncorr Gás (t)", "MPFM uncorr Óleo (t)", "MPFM uncorr HC (t)", "MPFM uncorr Água (t)", "MPFM uncorr Total (t)",
            "MPFM corr Gás (t)", "MPFM corr Óleo (t)", "MPFM corr HC (t)", "MPFM corr Água (t)", "MPFM corr Total (t)",
            "PVT mass Gás (t)", "PVT mass Óleo (t)", "PVT mass Água (t)",
            "PVT vol Gás (Sm³)", "PVT vol Óleo (m³)", "PVT vol Água (m³)",
            "PVT @20 mass Gás (t)", "PVT @20 mass Óleo (t)", "PVT @20 mass Água (t)",
            "PVT @20 vol Gás (Sm³)", "PVT @20 vol Óleo (m³)", "PVT @20 vol Água (m³)",
            "Pressão (barg)", "Temperatura (°C)", "Dens. Gás (kg/m³)", "Dens. Óleo (kg/m³)", "Dens. Água (kg/m³)",
        ]:
            row[col] = r[col]
        if sep_day:
            mpfm_hc = row["MPFM corr HC (t)"]
            mpfm_tot = row["MPFM corr Total (t)"]
            row["SEP Temperatura Méd. (°C)"] = sep_day.get("temp", "")
            row["SEP Pressão Méd. (barg)"] = sep_day.get("pressure_barg", "")
            row["SEP Óleo Vol. Bruto (m³) CV"] = sep_day.get("oil_m3", "")
            row["SEP Óleo (t) CV"] = sep_day.get("oil_t", "")
            row["SEP Gás (t) CV"] = sep_day.get("gas_t", "")
            row["SEP Água (t) CV"] = sep_day.get("water_t", "")
            row["SEP HC (t)"] = sep_day.get("hc_t", "")
            row["SEP Total (t)"] = sep_day.get("total_t", "")
            row["Desvio HC (%)"] = _sep_desvio_pct(mpfm_hc, sep_day.get("hc_t"))
            row["Desvio Total (%)"] = _sep_desvio_pct(mpfm_tot, sep_day.get("total_t"))
            row["SEP TAG"] = "SEP_Dados"
            row["SEP Medidor"] = "20FT0244/20FT0247/20FT0251"
            row["SEP Local"] = "Separador de Testes"
            row["SEP Status"] = "Alinhado"
            row["Bancos alinhados"] = row["Bank"]
        rows.append(row)
    return rows


def recon_df_to_rows(df) -> list:
    rows = []
    for _, r in df.iterrows():
        row = _new_row()
        row.update({
            "ProductionDate": r["Dia"],
            "Hour": "",
            "Granularity": "Daily",
            "Origin": "RECON",
            "SourceType": "CALC",
            "Bank": r["Bank"],
            "Loop": r["Loop"],
            "Tipo": r["Tipo"],
            "Entity": r["TAG"],
            "Tag": r["TAG"],
            "Instrumento": r["Instrumento"],
            "Fonte": "Reconciliação",
            "SourceFile": "",
            "IsOfficial": 1,
        })
        for metric, column in RECON_MAP.items():
            if metric in df.columns:
                row[column] = r[metric]
        rows.append(row)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now()
    months = _months_to_scan(today, back=1)

    print("📅 Descobrindo dias disponíveis (Daily PDF) por banco...")
    daily_by_bank = {}
    for bank_code in BANK_FOLDERS:
        daily_by_bank[bank_code] = discover_daily_records(bank_code, months, keep=DAYS_COUNT + 5)
        print(f"  {bank_code}: {len(daily_by_bank[bank_code])} dia(s) encontrados")

    all_days = sorted({day for recs in daily_by_bank.values() for day in recs}, reverse=True)
    if not all_days:
        print("❌ Nenhum dia com PDF Daily encontrado em nenhum banco. Abortando.")
        return

    target_days = sorted(all_days[:DAYS_COUNT])
    target_days_set = set(target_days)
    print(f"\n✅ Últimos {len(target_days)} dia(s) selecionados: {', '.join(target_days)}")

    most_recent = max(all_days)
    expected_most_recent = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if most_recent < expected_most_recent:
        print(
            f"⚠️  ATENÇÃO: o dia mais recente disponível ({most_recent}) é anterior a ontem "
            f"({expected_most_recent}). Os dados podem não estar em dia."
        )

    for bank_code in BANK_FOLDERS:
        missing = [d for d in target_days if d not in daily_by_bank[bank_code]]
        if missing:
            print(f"⚠️  {bank_code}: sem Daily PDF para {', '.join(missing)}")

    print("\n📄 Lendo relatórios Hourly (apenas dos dias selecionados)...")
    hourly_by_bank_day = {}
    for bank_code in BANK_FOLDERS:
        hourly_by_bank_day[bank_code] = discover_hourly_records_for_days(bank_code, months, target_days_set)
        total_hours = sum(len(v) for v in hourly_by_bank_day[bank_code].values())
        print(f"  {bank_code}: {total_hours} registro(s) horário(s)")

    print("\n🧪 Localizando TXT do Separador de Testes (FC13/FC14/FC17)...")
    sep_paths_by_day = load_sep_data_for_days(target_days)
    sep_data_by_day = {
        day: parse_sep_data(day, paths) for day, paths in sep_paths_by_day.items()
    }
    for day in target_days:
        if day not in sep_data_by_day:
            print(f"  ⚠️  SEP não disponível para {day} — banco {SEP_ALIGNED_BANK} ficará sem colunas SEP nesse dia")

    all_rows = []
    for day in target_days:
        for bank_code in BANK_FOLDERS:
            daily_entry = daily_by_bank[bank_code].get(day)
            hourly_recs = hourly_by_bank_day[bank_code].get(day, [])
            is_aligned = bank_code == SEP_ALIGNED_BANK
            sep_data = sep_data_by_day.get(day) if is_aligned else None

            if hourly_recs:
                df_hourly = engine.build_hourly_df_with_sep(hourly_recs, bank_code, sep_data)
                all_rows.extend(hourly_df_to_rows(df_hourly, sep_merged=bool(sep_data)))

            if daily_entry:
                _, daily_record = daily_entry
                df_daily = engine.build_daily_df(daily_record, bank_code)
                sep_day = sep_data.get("DAY") if sep_data else None
                all_rows.extend(daily_df_to_rows(df_daily, sep_day))

                df_recon = engine.build_recon_df(daily_record, hourly_recs, bank_code)
                all_rows.extend(recon_df_to_rows(df_recon))

        print(f"  📦 {day}: processado")

    if not all_rows:
        print("❌ Nenhuma linha gerada. Abortando sem escrever arquivo.")
        return

    import pandas as pd

    df_out = pd.DataFrame(all_rows, columns=BASE_UNICA_COLUMNS)
    df_out.sort_values(
        by=["ProductionDate", "Bank", "Granularity", "Hour", "Tag"],
        inplace=True,
        na_position="last",
        key=lambda col: col.astype(str) if col.name != "Hour" else col,
    )
    df_out.to_excel(OUTPUT_PATH, sheet_name="BASE_UNICA_EXTERNA", index=False)
    print(f"\n✅ Concluído: {len(df_out)} linha(s) gravadas em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
