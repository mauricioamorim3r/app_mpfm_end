#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Gerador XML 042 Multifásico — STANDALONE.

Lê um Excel Base_Unica já gerado, extrai as linhas Daily/MPFM/Subsea da janela
informada pelo usuário e gera os arquivos XML 042 no padrão ANP:

    042_<CNPJ8>_<AAAAMMDDHHmmSS>.xml

Não depende do app, do server.py nem do banco SQLite.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config_xml042_standalone.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "xml042_gerados"
DEFAULT_MONTHLY_OUTPUTS_DIR = SCRIPT_DIR.parent.parent / "data" / "outputs"
DEFAULT_CNPJ8 = "04028583"
MONTH_CODES_PTBR = {
    1: "JAN",
    2: "FEV",
    3: "MAR",
    4: "ABR",
    5: "MAI",
    6: "JUN",
    7: "JUL",
    8: "AGO",
    9: "SET",
    10: "OUT",
    11: "NOV",
    12: "DEZ",
}
BASE_SHEET_CANDIDATES = [
    "BASE_UNICA_TOTAL",
    "BASE_UNICA_MES",
    "BASE_UNICA_STANDALONE",
    "Base_Unica",
    "BASE_UNICA",
]
REQUIRED_COLUMNS = [
    "ProductionDate",
    "Granularity",
    "Origin",
    "Bank",
    "Entity",
    "Tag",
    "Instrumento",
    "PVT vol Óleo (m³)",
    "PVT vol Gás (Sm³)",
    "PVT vol Água (m³)",
]


@dataclass(frozen=True)
class Candidate:
    production_day: str
    bank: str
    well_operator_name: str
    subsea_tag: str
    loop: str
    oil_sm3: float
    gas_sm3: float
    gas_1000sm3: float
    water_sm3: float
    oil_t: float | None
    gas_t: float | None
    water_t: float | None
    source_file: str
    catalog: dict[str, Any]


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text("utf-8"))


def normalize_date_input(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw or raw.lower() in {"nan", "nat", "none"}:
        return ""
    if " " in raw:
        raw = raw.split(" ", 1)[0]
    raw = raw.replace(".", "/").replace("-", "/")
    for fmt in ("%Y/%m/%d", "%d/%m/%Y", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return ""


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "nat", "none", "-"}:
        return None
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        parsed = float(raw)
    except Exception:
        return None
    return parsed if parsed == parsed else None


def fmt_decimal_ptbr(value: Any, digits: int = 5) -> str:
    parsed = to_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.{digits}f}".replace(".", ",")


def xml_datetime(day_iso: str) -> str:
    return datetime.strptime(day_iso, "%Y-%m-%d").strftime("%d/%m/%Y 00:00:00")


def norm_key(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def is_truthy(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"1", "true", "sim", "s", "yes", "y"}:
        return True
    if raw in {"0", "false", "nao", "não", "n", "no"}:
        return False
    return default


def resolve_path(value: str | Path, *, base: Path = SCRIPT_DIR) -> Path:
    path = Path(str(value or "").strip().strip('"'))
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def resolve_base_unica_path(value: str | Path) -> Path:
    """Accept either an Excel file path or a folder containing Base_Unica.

    Users commonly paste the folder where `BASE_UNICA_TOTAL.xlsx` lives. In that
    case, locate the most likely workbook instead of trying to open the folder as
    an Excel file.
    """
    path = resolve_path(value)
    if path.is_file():
        return path
    if not path.exists():
        raise FileNotFoundError(f"Caminho não encontrado: {path}")
    if not path.is_dir():
        raise FileNotFoundError(f"Caminho inválido para Base_Unica: {path}")

    priority_patterns = [
        "BASE_UNICA_TOTAL.xlsx",
        "BASE_UNICA.xlsx",
        "BASE_UNICA_TOTAL*.xlsx",
        "BASE_UNICA_STANDALONE*.xlsx",
        "*BASE_UNICA*.xlsx",
    ]
    for pattern in priority_patterns:
        matches = sorted(
            (item for item in path.glob(pattern) if item.is_file() and not item.name.startswith("~$")),
            key=lambda item: (item.name.upper() != "BASE_UNICA_TOTAL.XLSX", item.name.upper()),
        )
        if matches:
            return matches[0].resolve()

    for pattern in priority_patterns:
        matches = sorted(
            (item for item in path.rglob(pattern) if item.is_file() and not item.name.startswith("~$")),
            key=lambda item: (len(item.relative_to(path).parts), item.name.upper()),
        )
        if matches:
            return matches[0].resolve()

    raise FileNotFoundError(
        f"Nenhum Excel Base_Unica encontrado dentro da pasta: {path}. "
        "Informe o arquivo .xlsx diretamente ou coloque BASE_UNICA_TOTAL.xlsx nesta pasta."
    )


def iter_months(date_from: str, date_to: str) -> list[tuple[int, int]]:
    start = datetime.strptime(date_from, "%Y-%m-%d").replace(day=1)
    end = datetime.strptime(date_to, "%Y-%m-%d").replace(day=1)
    months: list[tuple[int, int]] = []
    current = start
    while current <= end:
        months.append((current.year, current.month))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def resolve_monthly_outputs_dir(value: str | Path | None = "") -> Path:
    raw = str(value or "").strip()
    if raw:
        return resolve_path(raw)
    return DEFAULT_MONTHLY_OUTPUTS_DIR.resolve()


def find_monthly_workbook(outputs_dir: Path, year: int, month: int) -> Path:
    if not outputs_dir.exists():
        raise FileNotFoundError(f"Pasta de arquivos mensais não encontrada: {outputs_dir}")
    month_code = MONTH_CODES_PTBR[month]
    exact_name = f"MPFM_{month_code}_{year}.xlsx"
    exact_path = outputs_dir / exact_name
    if exact_path.is_file():
        return exact_path.resolve()

    patterns = [
        f"MPFM_{month_code}_{year}*.xlsx",
        f"*MPFM*{month_code}*{year}*.xlsx",
        f"*{month:02d}*{year}*.xlsx",
    ]
    for pattern in patterns:
        matches = sorted(
            (
                item
                for item in outputs_dir.glob(pattern)
                if item.is_file()
                and not item.name.startswith("~$")
                and "corrupted" not in item.name.lower()
                and not item.name.lower().endswith(".bak")
            ),
            key=lambda item: (item.name.upper() != exact_name.upper(), item.stat().st_mtime),
            reverse=True,
        )
        if matches:
            return matches[0].resolve()

    raise FileNotFoundError(
        f"Arquivo mensal MPFM não encontrado para {month_code}/{year} em {outputs_dir}. "
        f"Nome esperado: {exact_name}"
    )


def find_monthly_workbooks_for_window(outputs_dir: Path, date_from: str, date_to: str) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for year, month in iter_months(date_from, date_to):
        path = find_monthly_workbook(outputs_dir, year, month)
        if path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def discover_base_sheet(excel_path: Path, requested_sheet: str = "") -> str:
    workbook = pd.ExcelFile(excel_path)
    sheets = workbook.sheet_names
    if requested_sheet:
        if requested_sheet not in sheets:
            raise ValueError(f'Aba informada não encontrada: "{requested_sheet}". Abas disponíveis: {", ".join(sheets)}')
        return requested_sheet
    for name in BASE_SHEET_CANDIDATES:
        if name in sheets:
            return name
    for name in sheets:
        if name.upper().startswith("BASE_UNICA"):
            return name
    raise ValueError(f"Não encontrei uma aba Base_Unica no arquivo. Abas disponíveis: {', '.join(sheets)}")


def load_base_unica(excel_path: Path, sheet_name: str = "") -> tuple[pd.DataFrame, str]:
    sheet = discover_base_sheet(excel_path, sheet_name)
    df = pd.read_excel(excel_path, sheet_name=sheet, dtype=object)
    df.columns = [str(col).strip() for col in df.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Aba {sheet} não possui colunas obrigatórias: {', '.join(missing)}")
    return df, sheet


def load_base_unica_many(excel_paths: list[Path], sheet_name: str = "") -> tuple[pd.DataFrame, str]:
    frames: list[pd.DataFrame] = []
    sheets: list[str] = []
    for excel_path in excel_paths:
        df, sheet = load_base_unica(excel_path, sheet_name)
        df = df.copy()
        df["__workbook"] = str(excel_path)
        frames.append(df)
        sheets.append(f"{excel_path.name}:{sheet} ({len(df)} linhas)")
    if not frames:
        raise ValueError("Nenhum arquivo Excel informado para leitura.")
    return pd.concat(frames, ignore_index=True), "; ".join(sheets)


def collect_candidates_from_excel(
    excel_paths: list[Path],
    sheet_name: str,
    date_from: str,
    date_to: str,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str, pd.DataFrame, list[Candidate], list[dict[str, Any]]]:
    df, detected_sheet = load_base_unica_many(excel_paths, sheet_name)
    filtered = filter_daily_mpfm_subsea(df, date_from, date_to, config)
    catalog_rows = config.get("catalog") or []
    if not catalog_rows:
        raise ValueError("Configuração sem catálogo XML042. Preencha 'catalog' no JSON.")
    candidates, rejected = candidates_from_base(filtered, catalog_rows)
    return df, detected_sheet, filtered, candidates, rejected


def build_catalog_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if not is_truthy(row.get("active"), True) or not is_truthy(row.get("enabled_042"), True):
            continue
        names = {
            norm_key(row.get("well_operator_name")),
            norm_key(row.get("well_anp_name")),
            norm_key(row.get("poco_equinor")),
        }
        tags = {norm_key(row.get("subsea_tag")), norm_key(row.get("tag_associado"))}
        for name in {item for item in names if item}:
            for tag in {item for item in tags if item}:
                index.setdefault((name, tag), []).append(row)
    return index


def first_existing(row: pd.Series, names: list[str], default: Any = "") -> Any:
    for name in names:
        if name in row.index:
            value = row.get(name)
            if value is not None and str(value).strip().lower() not in {"", "nan", "nat", "none"}:
                return value
    return default


def filter_daily_mpfm_subsea(df: pd.DataFrame, date_from: str, date_to: str, config: dict[str, Any]) -> pd.DataFrame:
    work = df.copy()
    work["__day"] = work["ProductionDate"].map(normalize_date_input)
    mask = work["__day"].astype(str).ne("")
    if date_from:
        mask &= work["__day"] >= date_from
    if date_to:
        mask &= work["__day"] <= date_to
    mask &= work["Granularity"].astype(str).str.upper().eq("DAILY")
    mask &= work["Origin"].astype(str).str.upper().eq("MPFM")
    if "SourceType" in work.columns:
        mask &= work["SourceType"].astype(str).str.upper().isin(["PDF", "", "NAN"])
    if is_truthy(config.get("require_subsea"), True) and "Tipo" in work.columns:
        mask &= work["Tipo"].astype(str).str.upper().eq("SUBSEA")
    if is_truthy(config.get("require_is_official"), True) and "IsOfficial" in work.columns:
        mask &= work["IsOfficial"].map(lambda value: is_truthy(value, False))
    return work.loc[mask].copy()


def candidates_from_base(df: pd.DataFrame, catalog_rows: list[dict[str, Any]]) -> tuple[list[Candidate], list[dict[str, Any]]]:
    catalog_index = build_catalog_index(catalog_rows)
    candidates: list[Candidate] = []
    rejected: list[dict[str, Any]] = []

    group_cols = ["__day", "Bank", "Entity", "Tag", "Instrumento"]
    for col in group_cols:
        if col not in df.columns:
            df[col] = ""

    for _, row in df.iterrows():
        day = str(row.get("__day") or "").strip()
        bank = str(row.get("Bank") or "").strip().upper()
        entity = str(first_existing(row, ["Entity", "System", "Tag"])).strip()
        tag = str(first_existing(row, ["Tag", "Entity", "System"])).strip()
        instrumento = str(first_existing(row, ["Instrumento", "Instrument", "PI Tag"])).strip()
        loop = str(first_existing(row, ["Loop", "Area"])).strip()
        source_file = str(first_existing(row, ["SourceFile", "Fonte", "Fonte (Daily)"])).strip()

        oil_sm3 = to_float(row.get("PVT vol Óleo (m³)"))
        gas_sm3 = to_float(row.get("PVT vol Gás (Sm³)"))
        water_sm3 = to_float(row.get("PVT vol Água (m³)"))
        if oil_sm3 is None or gas_sm3 is None or water_sm3 is None:
            rejected.append({"day": day, "bank": bank, "entity": entity, "instrumento": instrumento, "reason": "volume crítico ausente"})
            continue

        matches = []
        for well_name in {norm_key(entity), norm_key(tag), norm_key(first_existing(row, ["System"]))}:
            if not well_name:
                continue
            for inst in {norm_key(instrumento), norm_key(first_existing(row, ["PI Tag"]))}:
                if not inst:
                    continue
                matches.extend(catalog_index.get((well_name, inst), []))
        if bank:
            matches = [item for item in matches if not str(item.get("bank") or "").strip() or str(item.get("bank") or "").strip().upper() == bank]
        unique: dict[tuple[str, str], dict[str, Any]] = {}
        for item in matches:
            unique[(str(item.get("cod_cadastro_poco") or ""), str(item.get("subsea_tag") or item.get("tag_associado") or ""))] = item
        matches = list(unique.values())

        if not matches:
            rejected.append({"day": day, "bank": bank, "entity": entity, "instrumento": instrumento, "reason": "sem cadastro XML042"})
            continue
        if len(matches) > 1:
            rejected.append({"day": day, "bank": bank, "entity": entity, "instrumento": instrumento, "reason": "cadastro XML042 ambíguo"})
            continue

        catalog = matches[0]
        candidates.append(
            Candidate(
                production_day=day,
                bank=bank,
                well_operator_name=entity or str(catalog.get("well_operator_name") or ""),
                subsea_tag=instrumento or str(catalog.get("subsea_tag") or catalog.get("tag_associado") or ""),
                loop=loop,
                oil_sm3=oil_sm3,
                gas_sm3=gas_sm3,
                gas_1000sm3=round(gas_sm3 / 1000.0, 5),
                water_sm3=water_sm3,
                oil_t=to_float(row.get("PVT mass Óleo (t)")),
                gas_t=to_float(row.get("PVT mass Gás (t)")),
                water_t=to_float(row.get("PVT mass Água (t)")),
                source_file=source_file,
                catalog={
                    "well_operator_name": str(catalog.get("well_operator_name") or entity or ""),
                    "well_anp_name": str(catalog.get("well_anp_name") or ""),
                    "cod_cadastro_poco": str(catalog.get("cod_cadastro_poco") or ""),
                    "subsea_tag": str(catalog.get("subsea_tag") or catalog.get("tag_associado") or instrumento or ""),
                    "cod_campo": str(catalog.get("cod_campo") or "4735"),
                    "campo": str(catalog.get("campo") or "BACALHAU"),
                    "cod_instalacao": str(catalog.get("cod_instalacao") or "38480"),
                    "instalacao": str(catalog.get("instalacao") or "FPSO BACALHAU"),
                },
            )
        )

    # Se houver duplicidade no Excel para mesmo dia+poço, mantém a última linha lida.
    dedup: dict[tuple[str, str], Candidate] = {}
    for item in candidates:
        dedup[(item.production_day, item.catalog["cod_cadastro_poco"])] = item
    return sorted(dedup.values(), key=lambda item: (item.production_day, item.bank, item.well_operator_name)), rejected


def build_xml042_text(candidate: Candidate) -> str:
    root = ET.Element("a042", {"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance", "xsi:noNamespaceSchemaLocation": "042.xsd"})
    lista = ET.SubElement(root, "LISTA_TESTE_POCO")
    teste = ET.SubElement(lista, "TESTE_POCO")
    values = {
        "COD_CADASTRO_POCO": candidate.catalog["cod_cadastro_poco"],
        "IND_TIPO_TESTE": "M",
        "DHA_TESTE": xml_datetime(candidate.production_day),
        "DHA_APLICACAO": xml_datetime(candidate.production_day),
        "IND_VALIDO": "S",
        "MED_POTENCIAL_OLEO": fmt_decimal_ptbr(candidate.oil_sm3),
        "MED_POTENCIAL_GAS": fmt_decimal_ptbr(candidate.gas_1000sm3),
        "MED_POTENCIAL_AGUA": fmt_decimal_ptbr(candidate.water_sm3),
    }
    for tag, text in values.items():
        ET.SubElement(teste, tag).text = text
    ET.SubElement(teste, "LISTA_SEPARADOR")
    rough = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    # ElementTree não preserva a ordem visual/indentação do serviço original; montamos
    # a saída final explicitamente para ficar igual ao XML usado pelo app.
    return (
        '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        '<a042 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="042.xsd">\n'
        '  <LISTA_TESTE_POCO>\n'
        '    <TESTE_POCO>\n'
        f'      <COD_CADASTRO_POCO>{values["COD_CADASTRO_POCO"]}</COD_CADASTRO_POCO>\n'
        '      <IND_TIPO_TESTE>M</IND_TIPO_TESTE>\n'
        f'      <DHA_TESTE>{values["DHA_TESTE"]}</DHA_TESTE>\n'
        f'      <DHA_APLICACAO>{values["DHA_APLICACAO"]}</DHA_APLICACAO>\n'
        '      <IND_VALIDO>S</IND_VALIDO>\n'
        f'      <MED_POTENCIAL_OLEO>{values["MED_POTENCIAL_OLEO"]}</MED_POTENCIAL_OLEO>\n'
        f'      <MED_POTENCIAL_GAS>{values["MED_POTENCIAL_GAS"]}</MED_POTENCIAL_GAS>\n'
        f'      <MED_POTENCIAL_AGUA>{values["MED_POTENCIAL_AGUA"]}</MED_POTENCIAL_AGUA>\n'
        '      <LISTA_SEPARADOR/>\n'
        '    </TESTE_POCO>\n'
        '  </LISTA_TESTE_POCO>\n'
        '</a042>\n'
    )


def build_anp_filename(cnpj8: str, output_dir: Path, used_names: set[str]) -> str:
    cnpj = re.sub(r"\D", "", str(cnpj8 or ""))[:8] or DEFAULT_CNPJ8
    current = datetime.now().replace(microsecond=0)
    for offset in range(86400):
        stamp = (current + timedelta(seconds=offset)).strftime("%Y%m%d%H%M%S")
        filename = f"042_{cnpj}_{stamp}.xml"
        if filename in used_names or (output_dir / filename).exists():
            continue
        used_names.add(filename)
        return filename
    raise RuntimeError("Não foi possível gerar nome ANP único para XML042.")


def load_existing_manifest(manifest_path: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    if not manifest_path.exists():
        return keys
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            day = str(row.get("production_day") or "").strip()
            code = str(row.get("cod_cadastro_poco") or "").strip()
            if day and code:
                keys.add((day, code))
    return keys


def append_manifest(manifest_path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "generated_at", "production_day", "cod_cadastro_poco", "well_operator_name", "well_anp_name",
        "subsea_tag", "bank", "oil_sm3", "gas_1000sm3", "water_sm3", "filename", "file_hash", "source_file",
    ]
    exists = manifest_path.exists()
    with manifest_path.open("a", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=";")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_rejected_report(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = ["day", "bank", "entity", "instrumento", "reason"]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def generate_xml_files(candidates: list[Candidate], output_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifesto_xml042.csv"
    existing_keys = load_existing_manifest(manifest_path)
    overwrite = is_truthy(config.get("overwrite_existing_day_well"), False)
    used_names = {path.name for path in output_dir.glob("042_*.xml")}
    generated_rows: list[dict[str, Any]] = []
    skipped_existing = 0

    for candidate in candidates:
        key = (candidate.production_day, candidate.catalog["cod_cadastro_poco"])
        if key in existing_keys and not overwrite:
            skipped_existing += 1
            continue
        xml_text = build_xml042_text(candidate)
        data = xml_text.encode("iso-8859-1", errors="xmlcharrefreplace")
        filename = build_anp_filename(str(config.get("cnpj8") or DEFAULT_CNPJ8), output_dir, used_names)
        file_path = output_dir / filename
        file_path.write_bytes(data)
        generated_rows.append(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "production_day": candidate.production_day,
                "cod_cadastro_poco": candidate.catalog["cod_cadastro_poco"],
                "well_operator_name": candidate.well_operator_name,
                "well_anp_name": candidate.catalog.get("well_anp_name", ""),
                "subsea_tag": candidate.subsea_tag,
                "bank": candidate.bank,
                "oil_sm3": candidate.oil_sm3,
                "gas_1000sm3": candidate.gas_1000sm3,
                "water_sm3": candidate.water_sm3,
                "filename": filename,
                "file_hash": hashlib.sha256(data).hexdigest(),
                "source_file": candidate.source_file,
            }
        )

    append_manifest(manifest_path, generated_rows)
    return {
        "generated": len(generated_rows),
        "skipped_existing": skipped_existing,
        "manifest_path": str(manifest_path),
        "generated_rows": generated_rows,
    }


def prompt_if_empty(label: str, current: str = "") -> str:
    current = str(current or "").strip()
    if current:
        return current
    return input(label).strip().strip('"')


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera XML 042 Multifásico a partir de Excel Base_Unica, standalone.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Arquivo JSON de configuração.")
    parser.add_argument("--base-unica", default="", help="Caminho do Excel Base_Unica de entrada ou da pasta onde ele está.")
    parser.add_argument("--monthly-dir", default="", help="Pasta com arquivos mensais MPFM_MES_ANO.xlsx usada como fallback.")
    parser.add_argument("--sheet", default="", help="Nome da aba Base_Unica. Se omitido, detecta automaticamente.")
    parser.add_argument("--date-from", default="", help="Data inicial da janela (DD/MM/AAAA ou AAAA-MM-DD).")
    parser.add_argument("--date-to", default="", help="Data final da janela (DD/MM/AAAA ou AAAA-MM-DD).")
    parser.add_argument("--output-dir", default="", help="Pasta onde os XMLs serão salvos. Padrão: xml042_gerados ao lado do script.")
    parser.add_argument("--cnpj8", default="", help="CNPJ raiz com 8 dígitos usado no nome ANP.")
    parser.add_argument("--overwrite", action="store_true", help="Gera novamente mesmo se o manifesto já tiver o mesmo dia+poço.")
    parser.add_argument("--no-prompt", action="store_true", help="Falha em vez de perguntar valores ausentes.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config_path = resolve_path(args.config)
    config = load_config(config_path)

    base_unica_raw = args.base_unica or str(config.get("base_unica_excel") or "")
    monthly_dir_raw = args.monthly_dir or str(config.get("monthly_outputs_dir") or "")
    date_from_raw = args.date_from or str(config.get("date_from") or "")
    date_to_raw = args.date_to or str(config.get("date_to") or "")
    output_raw = args.output_dir or str(config.get("output_dir") or "") or str(DEFAULT_OUTPUT_DIR)
    sheet_name = args.sheet or str(config.get("sheet_name") or "")

    if args.cnpj8:
        config["cnpj8"] = args.cnpj8
    if args.overwrite:
        config["overwrite_existing_day_well"] = True

    if not args.no_prompt:
        base_unica_raw = prompt_if_empty("Caminho do Excel Base_Unica ou da pasta onde ele está: ", base_unica_raw)
        date_from_raw = prompt_if_empty("Data inicial da janela (DD/MM/AAAA): ", date_from_raw)
        date_to_raw = prompt_if_empty("Data final da janela (DD/MM/AAAA): ", date_to_raw)

    date_from = normalize_date_input(date_from_raw)
    date_to = normalize_date_input(date_to_raw)
    if not date_from or not date_to:
        raise ValueError("Informe data inicial e final válidas para a janela.")
    if date_from > date_to:
        raise ValueError("Data inicial maior que data final.")

    base_unica_path: Path | None = None
    base_error: Exception | None = None
    if base_unica_raw:
        try:
            base_unica_path = resolve_base_unica_path(base_unica_raw)
        except Exception as exc:
            base_error = exc
    monthly_outputs_dir = resolve_monthly_outputs_dir(monthly_dir_raw)
    output_dir = resolve_path(output_raw)

    print("=" * 72)
    print("GERADOR XML 042 MULTIFÁSICO — STANDALONE")
    print("=" * 72)
    print(f"Base_Unica : {base_unica_path or '(não localizada / não informada)'}")
    print(f"Fallback mensal: {monthly_outputs_dir}")
    print(f"Janela     : {date_from} a {date_to}")
    print(f"Saída XML  : {output_dir}")

    rejected: list[dict[str, Any]] = []
    candidates: list[Candidate] = []
    if base_unica_path:
        try:
            df, detected_sheet, filtered, candidates, rejected = collect_candidates_from_excel(
                [base_unica_path], sheet_name, date_from, date_to, config
            )
            print("Fonte lida : Base_Unica")
            print(f"Aba lida   : {detected_sheet}")
            print(f"Linhas totais da fonte: {len(df)}")
            print(f"Elegíveis brutos Daily/MPFM/Subsea na janela: {len(filtered)}")
        except Exception as exc:
            base_error = exc
            print(f"Aviso: falha ao ler/processar Base_Unica: {exc}")

    if not candidates:
        if base_error:
            print(f"Acionando fallback mensal porque a Base_Unica falhou: {base_error}")
        else:
            print("Acionando fallback mensal porque a Base_Unica não gerou candidatos XML042 para a janela.")
        monthly_paths = find_monthly_workbooks_for_window(monthly_outputs_dir, date_from, date_to)
        df, detected_sheet, filtered, candidates, rejected = collect_candidates_from_excel(
            monthly_paths, "", date_from, date_to, config
        )
        print("Fonte lida : Excel mensal")
        print("Arquivos mensais:")
        for path in monthly_paths:
            print(f"  - {path}")
        print(f"Aba lida   : {detected_sheet}")
        print(f"Linhas totais da fonte: {len(df)}")
        print(f"Elegíveis brutos Daily/MPFM/Subsea na janela: {len(filtered)}")

    print(f"Candidatos com cadastro XML042 e volumes completos: {len(candidates)}")
    print(f"Linhas rejeitadas/ignoradas: {len(rejected)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rejected_path = output_dir / "linhas_rejeitadas_xml042.csv"
    write_rejected_report(rejected_path, rejected)
    if rejected:
        print(f"Relatório de rejeitadas: {rejected_path}")

    result = generate_xml_files(candidates, output_dir, config)
    print("-" * 72)
    print(f"XMLs gerados nesta execução : {result['generated']}")
    print(f"Ignorados por já constarem no manifesto: {result['skipped_existing']}")
    print(f"Manifesto: {result['manifest_path']}")
    print("Concluído.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nExecução cancelada pelo usuário.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
