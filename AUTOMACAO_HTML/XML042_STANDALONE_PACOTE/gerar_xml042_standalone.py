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
import gc
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config_xml042_standalone.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "xml042_gerados"
DEFAULT_HISTORY_MANIFEST = SCRIPT_DIR / "historico_emissoes_xml042.csv"
REGISTRY_FILENAME = "xml042_registry.sqlite3"
DEFAULT_CNPJ8 = "04028583"
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
    production_status: str
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
    """Aceita tanto o arquivo Excel quanto a pasta do pacote Base_Unica."""
    path = resolve_path(value)
    if path.is_dir():
        for name in ("BASE_UNICA_TOTAL.xlsx", "BASE_UNICA.xlsx", "Base_Unica.xlsx"):
            candidate = path / name
            if candidate.is_file():
                return candidate.resolve()
        available = ", ".join(item.name for item in sorted(path.glob("*.xlsx"))) or "nenhum .xlsx"
        raise FileNotFoundError(
            f"O caminho informado é uma pasta, mas não encontrei o Excel Base_Unica nela: {path}. "
            f"Arquivos Excel encontrados: {available}. Informe o caminho completo do arquivo .xlsx."
        )
    if path.suffix.lower() not in {".xlsx", ".xlsm", ".xls"}:
        raise ValueError(
            f"O caminho informado não é um arquivo Excel: {path}. "
            "Informe BASE_UNICA_TOTAL.xlsx ou a pasta que contém esse arquivo."
        )
    return path


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
        names.update(norm_key(alias) for alias in (row.get("aliases") or []) if alias)
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
    if is_truthy(config.get("require_is_official"), True):
        if "IsOfficial" not in work.columns:
            raise ValueError("A coluna IsOfficial é obrigatória quando require_is_official=true.")
        mask &= work["IsOfficial"].map(lambda value: is_truthy(value, False))
    return work.loc[mask].copy()


def candidates_from_base(
    df: pd.DataFrame,
    catalog_rows: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    config = config or {}
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
        volumes = (oil_sm3, gas_sm3, water_sm3)
        if any(value < 0 for value in volumes):
            rejected.append({"day": day, "bank": bank, "entity": entity, "instrumento": instrumento, "reason": "volume negativo"})
            continue
        zero_tolerance = abs(float(config.get("zero_tolerance", 1e-9)))
        production_status = "PRODUCAO_ZERADA_OFICIAL" if all(abs(value) <= zero_tolerance for value in volumes) else "PRODUCAO_POSITIVA_OFICIAL"
        if production_status == "PRODUCAO_ZERADA_OFICIAL" and not is_truthy(config.get("allow_zero_production"), True):
            rejected.append({"day": day, "bank": bank, "entity": entity, "instrumento": instrumento, "reason": "produção zerada desabilitada na configuração"})
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
        if not matches and instrumento:
            # Alguns relatórios usam um alias operacional do poço (por exemplo,
            # PE_4 em vez de PE_4A). Se o tag + banco identificarem um único
            # cadastro ativo, o tag é a referência técnica mais confiável.
            instrument_key = norm_key(instrumento)
            tag_matches = []
            for item in catalog_rows:
                if not is_truthy(item.get("active"), True) or not is_truthy(item.get("enabled_042"), True):
                    continue
                item_tags = {norm_key(item.get("subsea_tag")), norm_key(item.get("tag_associado"))}
                item_bank = str(item.get("bank") or "").strip().upper()
                if instrument_key in item_tags and (not bank or not item_bank or item_bank == bank):
                    tag_matches.append(item)
            matches = tag_matches
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
                production_status=production_status,
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

    # XML regulatório não pode escolher silenciosamente entre duas linhas da
    # mesma data/poço. Qualquer duplicidade bloqueia a chave até a Base ser
    # corrigida, mesmo quando os valores aparentam ser idênticos.
    grouped: dict[tuple[str, str], list[Candidate]] = {}
    for item in candidates:
        grouped.setdefault((item.production_day, item.catalog["cod_cadastro_poco"]), []).append(item)
    unique_candidates = []
    for (day, code), items in grouped.items():
        if len(items) > 1:
            rejected.append({
                "day": day, "bank": items[0].bank, "entity": items[0].well_operator_name,
                "instrumento": items[0].subsea_tag,
                "reason": f"duplicidade crítica dia+poço ({len(items)} linhas; código {code})",
            })
            continue
        unique_candidates.append(items[0])
    return sorted(unique_candidates, key=lambda item: (item.production_day, item.bank, item.well_operator_name)), rejected


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


def validate_xml042_data(data: bytes) -> None:
    """Validação estrutural mínima e independente do XSD externo."""
    root = ET.fromstring(data)
    test = root.find("./LISTA_TESTE_POCO/TESTE_POCO")
    if test is None:
        raise ValueError("XML042 sem LISTA_TESTE_POCO/TESTE_POCO.")
    required = [
        "COD_CADASTRO_POCO", "IND_TIPO_TESTE", "DHA_TESTE", "DHA_APLICACAO",
        "IND_VALIDO", "MED_POTENCIAL_OLEO", "MED_POTENCIAL_GAS", "MED_POTENCIAL_AGUA",
    ]
    for tag in required:
        if not str(test.findtext(tag) or "").strip():
            raise ValueError(f"XML042 sem valor obrigatório em {tag}.")
    for tag in ("MED_POTENCIAL_OLEO", "MED_POTENCIAL_GAS", "MED_POTENCIAL_AGUA"):
        value = to_float(test.findtext(tag))
        if value is None or value < 0:
            raise ValueError(f"XML042 com volume inválido em {tag}.")


def build_anp_filename(cnpj8: str, output_dir: Path, used_names: set[str]) -> str:
    cnpj = re.sub(r"\D", "", str(cnpj8 or ""))
    if len(cnpj) != 8:
        raise ValueError("CNPJ raiz inválido: informe exatamente 8 dígitos para o nome do XML 042.")
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


def resolve_registry_path(config: dict[str, Any]) -> Path:
    """Registro persistente de emissões, separado da pasta dos XMLs.

    No Windows, o padrão fica no perfil local do usuário. Para impedir
    duplicidade entre vários computadores, configure ``registry_path`` para
    um caminho corporativo compartilhado com controle de acesso.
    """
    configured = str(config.get("registry_path") or "").strip()
    if configured:
        return resolve_path(configured)
    local_root = os.environ.get("LOCALAPPDATA")
    if local_root:
        return (Path(local_root) / "Equinor" / "BaseUnica" / REGISTRY_FILENAME).resolve()
    return (Path.home() / ".local" / "share" / "Equinor" / "BaseUnica" / REGISTRY_FILENAME).resolve()


def _mark_hidden_windows(path: Path) -> None:
    if os.name != "nt" or not path.exists():
        return
    try:
        import ctypes
        hidden = 0x02
        current = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if current != -1:
            ctypes.windll.kernel32.SetFileAttributesW(str(path), current | hidden)
    except Exception:
        # A ocultação é uma conveniência de interface. A unicidade continua
        # garantida pela chave primária do SQLite e pelas permissões da pasta.
        pass


def open_emission_registry(registry_path: Path) -> sqlite3.Connection:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(registry_path, timeout=30)
    # DELETE evita arquivos WAL persistentes e bloqueios residuais no Windows.
    # A rotina já serializa a emissão com BEGIN IMMEDIATE e timeout.
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=FULL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS xml042_emissions (
            production_day TEXT NOT NULL,
            cod_cadastro_poco TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            filename TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            source_file TEXT,
            status TEXT NOT NULL DEFAULT 'GENERATED',
            PRIMARY KEY (production_day, cod_cadastro_poco)
        );
        CREATE TABLE IF NOT EXISTS xml042_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempted_at TEXT NOT NULL,
            production_day TEXT NOT NULL,
            cod_cadastro_poco TEXT NOT NULL,
            requested_hash TEXT,
            result TEXT NOT NULL,
            detail TEXT
        );
        """
    )
    connection.commit()
    _mark_hidden_windows(registry_path)
    return connection


def bootstrap_registry_from_manifest(connection: sqlite3.Connection, manifest_path: Path) -> int:
    """Importa o histórico visível antigo quando o registro nasce vazio."""
    if not manifest_path.exists():
        return 0
    imported = 0
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            day = str(row.get("production_day") or "").strip()
            code = str(row.get("cod_cadastro_poco") or "").strip()
            if not day or not code:
                continue
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO xml042_emissions
                (production_day, cod_cadastro_poco, content_hash, filename, generated_at, source_file, status)
                VALUES (?, ?, ?, ?, ?, ?, 'GENERATED')
                """,
                (
                    day, code, str(row.get("file_hash") or "MANIFESTO_LEGADO"),
                    str(row.get("filename") or ""), str(row.get("generated_at") or ""),
                    str(row.get("source_file") or ""),
                ),
            )
            imported += int(cursor.rowcount > 0)
    connection.commit()
    return imported


def import_history_xml_directories(connection: sqlite3.Connection, directories: list[str | Path]) -> dict[str, int]:
    """Importa XMLs antigos e bloqueia conflito histórico de dia + poço."""
    imported = existing_count = 0
    for raw_directory in directories:
        directory = resolve_path(raw_directory)
        if not directory.is_dir():
            raise FileNotFoundError(f"Pasta histórica de XML não encontrada: {directory}")
        for file_path in sorted(directory.rglob("042_*.xml")):
            data = file_path.read_bytes()
            validate_xml042_data(data)
            root = ET.fromstring(data)
            test = root.find("./LISTA_TESTE_POCO/TESTE_POCO")
            day = normalize_date_input(test.findtext("DHA_TESTE") if test is not None else "")
            code = str(test.findtext("COD_CADASTRO_POCO") if test is not None else "").strip()
            if not day or not code:
                raise ValueError(f"XML histórico sem data/poço identificável: {file_path}")
            content_hash = hashlib.sha256(data).hexdigest()
            generated_at = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(timespec="seconds")
            existing = connection.execute(
                "SELECT content_hash, filename FROM xml042_emissions WHERE production_day=? AND cod_cadastro_poco=?",
                (day, code),
            ).fetchone()
            if existing:
                existing_count += 1
                if existing[0] not in {content_hash, "MANIFESTO_LEGADO"}:
                    detail = f"Conflito histórico: {existing[1]} × {file_path.name}"
                    connection.execute(
                        """INSERT INTO xml042_attempts
                           (attempted_at, production_day, cod_cadastro_poco, requested_hash, result, detail)
                           VALUES (?, ?, ?, ?, 'HISTORY_CONFLICT', ?)""",
                        (datetime.now().isoformat(timespec="seconds"), day, code, content_hash, detail),
                    )
                    connection.commit()
                    raise ValueError(f"{detail} para {day} / poço {code}. A geração foi bloqueada.")
                if existing[0] == "MANIFESTO_LEGADO":
                    connection.execute(
                        "UPDATE xml042_emissions SET content_hash=?, filename=?, source_file=? WHERE production_day=? AND cod_cadastro_poco=?",
                        (content_hash, file_path.name, str(file_path), day, code),
                    )
                continue
            connection.execute(
                """INSERT INTO xml042_emissions
                   (production_day, cod_cadastro_poco, content_hash, filename, generated_at, source_file, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'GENERATED')""",
                (day, code, content_hash, file_path.name, generated_at, str(file_path)),
            )
            connection.execute(
                """INSERT INTO xml042_attempts
                   (attempted_at, production_day, cod_cadastro_poco, requested_hash, result, detail)
                   VALUES (?, ?, ?, ?, 'IMPORTED_HISTORY', ?)""",
                (datetime.now().isoformat(timespec="seconds"), day, code, content_hash, str(file_path)),
            )
            imported += 1
    connection.commit()
    return {"imported": imported, "existing": existing_count}


def append_manifest(manifest_path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "generated_at", "production_day", "cod_cadastro_poco", "well_operator_name", "well_anp_name",
        "subsea_tag", "bank", "production_status", "oil_sm3", "gas_1000sm3", "water_sm3", "filename", "file_hash", "source_file",
    ]
    exists = manifest_path.exists()
    with manifest_path.open("a", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=";")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_rejected_report(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["day", "bank", "entity", "instrumento", "reason"]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def generate_xml_files(candidates: list[Candidate], output_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifesto_xml042.csv"
    registry_path = resolve_registry_path(config)
    registry = open_emission_registry(registry_path)
    bootstrap_registry_from_manifest(registry, manifest_path)
    default_manifest = DEFAULT_OUTPUT_DIR / "manifesto_xml042.csv"
    if default_manifest.resolve() != manifest_path.resolve():
        bootstrap_registry_from_manifest(registry, default_manifest)
    bootstrap_registry_from_manifest(registry, DEFAULT_HISTORY_MANIFEST)
    history_dirs = config.get("history_dirs") or []
    if isinstance(history_dirs, (str, Path)):
        history_dirs = [history_dirs]
    history_dirs = [*history_dirs, *(config.get("_cli_history_dirs") or [])]
    if history_dirs:
        import_history_xml_directories(registry, history_dirs)
    used_names = {path.name for path in output_dir.glob("042_*.xml")}
    generated_rows: list[dict[str, Any]] = []
    skipped_existing = 0
    blocked_rows: list[dict[str, Any]] = []

    try:
        for candidate in candidates:
            production_day = candidate.production_day
            code = str(candidate.catalog["cod_cadastro_poco"])
            xml_text = build_xml042_text(candidate)
            data = xml_text.encode("iso-8859-1", errors="xmlcharrefreplace")
            validate_xml042_data(data)
            content_hash = hashlib.sha256(data).hexdigest()
            generated_at = datetime.now().isoformat(timespec="seconds")

            registry.execute("BEGIN IMMEDIATE")
            duplicate_content = registry.execute(
                """SELECT production_day, cod_cadastro_poco, filename, generated_at
                   FROM xml042_emissions
                   WHERE content_hash=? AND status IN ('RESERVED','GENERATED')
                   ORDER BY generated_at LIMIT 1""",
                (content_hash,),
            ).fetchone()
            if duplicate_content:
                detail = f"conteúdo idêntico já emitido para {duplicate_content[0]} / poço {duplicate_content[1]}: {duplicate_content[2]}"
                registry.execute(
                    """INSERT INTO xml042_attempts
                       (attempted_at, production_day, cod_cadastro_poco, requested_hash, result, detail)
                       VALUES (?, ?, ?, ?, 'BLOCKED_DUPLICATE_CONTENT', ?)""",
                    (generated_at, production_day, code, content_hash, detail),
                )
                registry.commit()
                skipped_existing += 1
                blocked_rows.append({
                    "production_day": production_day,
                    "cod_cadastro_poco": code,
                    "existing_filename": duplicate_content[2],
                    "existing_generated_at": duplicate_content[3],
                    "same_content": True,
                    "detail": detail,
                })
                print(f"BLOQUEADO: {production_day} / poço {code} — {detail}")
                continue
            existing = registry.execute(
                """SELECT content_hash, filename, generated_at, status
                   FROM xml042_emissions
                   WHERE production_day=? AND cod_cadastro_poco=?""",
                (production_day, code),
            ).fetchone()
            if existing:
                same_content = existing[0] == content_hash
                detail = (
                    f"XML já emitido em {existing[2]}: {existing[1]}"
                    + ("; conteúdo idêntico" if same_content else "; conteúdo atual diverge do já emitido")
                )
                registry.execute(
                    """INSERT INTO xml042_attempts
                       (attempted_at, production_day, cod_cadastro_poco, requested_hash, result, detail)
                       VALUES (?, ?, ?, ?, 'BLOCKED_DUPLICATE', ?)""",
                    (generated_at, production_day, code, content_hash, detail),
                )
                registry.commit()
                skipped_existing += 1
                blocked_rows.append({
                    "production_day": production_day,
                    "cod_cadastro_poco": code,
                    "existing_filename": existing[1],
                    "existing_generated_at": existing[2],
                    "same_content": same_content,
                    "detail": detail,
                })
                print(f"BLOQUEADO: {production_day} / poço {code} — {detail}")
                continue

            filename = build_anp_filename(str(config.get("cnpj8") or DEFAULT_CNPJ8), output_dir, used_names)
            file_path = output_dir / filename
            registry.execute(
                """INSERT INTO xml042_emissions
                   (production_day, cod_cadastro_poco, content_hash, filename, generated_at, source_file, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'RESERVED')""",
                (production_day, code, content_hash, filename, generated_at, candidate.source_file),
            )
            registry.commit()

            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(dir=output_dir, prefix=".xml042_", suffix=".tmp", delete=False) as temporary:
                    temporary.write(data)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                    temporary_path = Path(temporary.name)
                temporary_path.replace(file_path)
                registry.execute(
                    "UPDATE xml042_emissions SET status='GENERATED' WHERE production_day=? AND cod_cadastro_poco=?",
                    (production_day, code),
                )
                registry.execute(
                    """INSERT INTO xml042_attempts
                       (attempted_at, production_day, cod_cadastro_poco, requested_hash, result, detail)
                       VALUES (?, ?, ?, ?, 'GENERATED', ?)""",
                    (generated_at, production_day, code, content_hash, filename),
                )
                registry.commit()
            except Exception as exc:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
                registry.execute(
                    "DELETE FROM xml042_emissions WHERE production_day=? AND cod_cadastro_poco=? AND status='RESERVED'",
                    (production_day, code),
                )
                registry.execute(
                    """INSERT INTO xml042_attempts
                       (attempted_at, production_day, cod_cadastro_poco, requested_hash, result, detail)
                       VALUES (?, ?, ?, ?, 'FAILED', ?)""",
                    (generated_at, production_day, code, content_hash, str(exc)),
                )
                registry.commit()
                raise

            generated_rows.append({
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "production_day": production_day,
                "cod_cadastro_poco": code,
                "well_operator_name": candidate.well_operator_name,
                "well_anp_name": candidate.catalog.get("well_anp_name", ""),
                "subsea_tag": candidate.subsea_tag,
                "bank": candidate.bank,
                "production_status": candidate.production_status,
                "oil_sm3": candidate.oil_sm3,
                "gas_1000sm3": candidate.gas_1000sm3,
                "water_sm3": candidate.water_sm3,
                "filename": filename,
                "file_hash": content_hash,
                "source_file": candidate.source_file,
            })
    finally:
        # Encerra o WAL explicitamente antes de devolver o controle ao chamador.
        # Isso evita que o arquivo permaneça bloqueado no Windows (por exemplo,
        # em testes, rotinas de backup ou na troca do pacote de saída).
        try:
            registry.commit()
            registry.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            registry.execute("PRAGMA journal_mode=DELETE")
            registry.commit()
        finally:
            registry.close()
            del registry
            gc.collect()

    append_manifest(manifest_path, generated_rows)
    return {
        "generated": len(generated_rows),
        "skipped_existing": skipped_existing,
        "manifest_path": str(manifest_path),
        "registry_path": str(registry_path),
        "generated_rows": generated_rows,
        "blocked_rows": blocked_rows,
    }


def prompt_if_empty(label: str, current: str = "") -> str:
    current = str(current or "").strip()
    if current:
        return current
    return input(label).strip().strip('"')


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera XML 042 Multifásico a partir de Excel Base_Unica, standalone.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Arquivo JSON de configuração.")
    parser.add_argument("--base-unica", default="", help="Caminho do Excel Base_Unica de entrada.")
    parser.add_argument("--sheet", default="", help="Nome da aba Base_Unica. Se omitido, detecta automaticamente.")
    parser.add_argument("--date-from", default="", help="Data inicial da janela (DD/MM/AAAA ou AAAA-MM-DD).")
    parser.add_argument("--date-to", default="", help="Data final da janela (DD/MM/AAAA ou AAAA-MM-DD).")
    parser.add_argument("--output-dir", default="", help="Pasta onde os XMLs serão salvos. Padrão: xml042_gerados ao lado do script.")
    parser.add_argument("--cnpj8", default="", help="CNPJ raiz com 8 dígitos usado no nome ANP.")
    parser.add_argument("--history-dir", action="append", default=[], help="Pasta com XMLs 042 antigos a registrar antes da geração. Pode ser repetido.")
    parser.add_argument("--overwrite", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-prompt", action="store_true", help="Falha em vez de perguntar valores ausentes.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config_path = resolve_path(args.config)
    config = load_config(config_path)

    base_unica_raw = args.base_unica or str(config.get("base_unica_excel") or "")
    date_from_raw = args.date_from or str(config.get("date_from") or "")
    date_to_raw = args.date_to or str(config.get("date_to") or "")
    output_raw = args.output_dir or str(config.get("output_dir") or "") or str(DEFAULT_OUTPUT_DIR)
    sheet_name = args.sheet or str(config.get("sheet_name") or "")

    if args.cnpj8:
        config["cnpj8"] = args.cnpj8
    if args.overwrite:
        print("AVISO: --overwrite foi desativado. XML 042 já emitido nunca será gerado novamente.")
    config["_cli_history_dirs"] = list(args.history_dir or [])

    if not args.no_prompt:
        base_unica_raw = prompt_if_empty("Caminho do Excel Base_Unica ou da pasta do pacote: ", base_unica_raw)
        date_from_raw = prompt_if_empty("Data inicial da janela (DD/MM/AAAA): ", date_from_raw)
        date_to_raw = prompt_if_empty("Data final da janela (DD/MM/AAAA): ", date_to_raw)

    if not base_unica_raw:
        raise ValueError("Informe o caminho do Excel Base_Unica (--base-unica ou config).")
    date_from = normalize_date_input(date_from_raw)
    date_to = normalize_date_input(date_to_raw)
    if not date_from or not date_to:
        raise ValueError("Informe data inicial e final válidas para a janela.")
    if date_from > date_to:
        raise ValueError("Data inicial maior que data final.")

    base_unica_path = resolve_base_unica_path(base_unica_raw)
    output_dir = resolve_path(output_raw)
    if not base_unica_path.exists():
        raise FileNotFoundError(f"Excel Base_Unica não encontrado: {base_unica_path}")

    print("=" * 72)
    print("GERADOR XML 042 MULTIFÁSICO — STANDALONE")
    print("=" * 72)
    print(f"Base_Unica : {base_unica_path}")
    print(f"Janela     : {date_from} a {date_to}")
    print(f"Saída XML  : {output_dir}")

    df, detected_sheet = load_base_unica(base_unica_path, sheet_name)
    print(f"Aba lida   : {detected_sheet} ({len(df)} linhas)")

    filtered = filter_daily_mpfm_subsea(df, date_from, date_to, config)
    print(f"Elegíveis brutos Daily/MPFM/Subsea na janela: {len(filtered)}")

    catalog_rows = config.get("catalog") or []
    if not catalog_rows:
        raise ValueError("Configuração sem catálogo XML042. Preencha 'catalog' no JSON.")
    candidates, rejected = candidates_from_base(filtered, catalog_rows, config)
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
    print(f"Registro persistente de unicidade: {result['registry_path']}")
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
