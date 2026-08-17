#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
DPB FPSO Bacalhau - Automação oficial de extração/organização de ZIPs MPFM/FCS-320.

Esta versão substitui os arquivos antigos/corrompidos LE_*.py.
Modos:
    ULTIMO -> processa somente o ZIP mais recente da pasta.
    TODOS  -> processa todos os ZIPs disponíveis/não processados da pasta.

Regras principais:
    - Daily e Hourly são relatórios de medição e entram na verificação de completude.
    - PVTCalibration é cadastro/evidência de calibração/PVT e NÃO entra na completude Daily/Hourly.
    - Alarmes FCS-320 são organizados por Ano/Mês.
"""

from __future__ import annotations

import calendar
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODE = "TODOS"  # "ULTIMO" ou "TODOS"

WORKSPACE_ROOT = Path(os.environ.get("DPB_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent)).expanduser()

DEFAULT_ZIP_FOLDER = str(WORKSPACE_ROOT / "Zip")
PROCESSED_DB = "dpb_processed_zips.json"

BASE_DESTINATIONS = {
    "alarmes": str(WORKSPACE_ROOT / "3.1.7_ALARMES_FCS_320"),
    "eventos": str(WORKSPACE_ROOT / "3.1.8_EVENTOS_FCS320"),
    "Bank03":  str(WORKSPACE_ROOT / "3.1.1_13-FT-0367 Riser P5 - Topside B03"),
    "Bank05":  str(WORKSPACE_ROOT / "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05"),
    "Bank08":  str(WORKSPACE_ROOT / "3.1.2_13-FT-0167 Riser P2 - Topside B08"),
    "Bank10":  str(WORKSPACE_ROOT / "3.1.5_18-FT-0506 PE 2 - Subsea B10"),
    "Bank13":  str(WORKSPACE_ROOT / "3.1.3_13-FT-0317 Riser P4 - Topside B13"),
    "Bank15":  str(WORKSPACE_ROOT / "3.1.6_18-FT-1106 PW_104DA - Subsea B15"),
}

MONTHS_PT = {
    "01": "01. Janeiro", "02": "02. Fevereiro", "03": "03. Março", "04": "04. Abril",
    "05": "05. Maio", "06": "06. Junho", "07": "07. Julho", "08": "08. Agosto",
    "09": "09. Setembro", "10": "10. Outubro", "11": "11. Novembro", "12": "12. Dezembro",
}

BANK_CODE = {"Bank03": "B03", "Bank05": "B05", "Bank08": "B08", "Bank10": "B10", "Bank13": "B13", "Bank15": "B15"}

VALID_EXT_BY_KEY = {
    "eventos": {".pdf", ".txt"},
}

BANK_ALIASES = {
    "Bank03": ["bank03", "b03", "13ft0367", "13-ft-0367", "13_ft_0367", "ft0367", "ft-0367", "ft_0367"],
    "Bank05": [
        "bank05", "b05", "18ft1506", "18-ft-1506", "18_ft_1506", "ft1506", "ft-1506", "ft_1506",
        "18ft1706", "18-ft-1706", "18_ft_1706", "ft1706", "ft-1706", "ft_1706",
        "18ft1406", "18-ft-1406", "18_ft_1406", "ft1406", "ft-1406", "ft_1406",
        "18ft1806", "18-ft-1806", "18_ft_1806", "ft1806", "ft-1806", "ft_1806",
        "pe4", "pe-4", "pe_4", "pe4a", "pe-4a", "pe_4a", "pe04", "pe-04", "pe_04",
        "peeo105", "pe-eo105", "pe_eo105", "eo105", "pe105", "pe-105", "pe_105",
        "peeo10", "pe-eo10", "pe_eo10", "eo10", "peeo4", "pe-eo4", "pe_eo4",
    ],
    "Bank08": ["bank08", "b08", "13ft0167", "13-ft-0167", "13_ft_0167", "ft0167", "ft-0167", "ft_0167"],
    "Bank10": ["bank10", "b10", "18ft0506", "18-ft-0506", "18_ft_0506", "ft0506", "ft-0506", "ft_0506"],
    "Bank13": ["bank13", "b13", "13ft0317", "13-ft-0317", "13_ft_0317", "ft0317", "ft-0317", "ft_0317"],
    "Bank15": ["bank15", "b15", "18ft1106", "18-ft-1106", "18_ft_1106", "ft1106", "ft-1106", "ft_1106", "pw104da", "pw_104da", "pw-104da"],
    "eventos": ["eventos", "evento", "events", "event"],
    "alarmes": ["alarmes", "alarme", "alarm", "fcs320", "fcs-320", "fcs_320"],
}

@dataclass
class Counters:
    zips_found: int = 0
    zips_processed: int = 0
    zips_skipped: int = 0
    stage1_moved: int = 0
    stage1_unmatched: int = 0
    stage1_invalid_ext: int = 0
    stage1_errors: int = 0
    stage2_moved: int = 0
    stage2_duplicates_renamed: int = 0
    stage2_errors: int = 0
    stage3_missing: int = 0
    errors: List[str] = field(default_factory=list)
    unmatched_files: List[str] = field(default_factory=list)
    invalid_files: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)


def setup_logger(log_path: Path) -> logging.Logger:
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"DPB_{MODE}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    logger.info("Log iniciado: %s", log_path)
    return logger


def post_teams(text: str, logger: logging.Logger) -> None:
    webhook_url = os.environ.get("DPB_TEAMS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.info("Teams webhook não configurado. Mensagem não enviada.")
        return
    try:
        payload = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
        req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        with urlopen(req, timeout=20) as response:
            logger.info("Mensagem Teams enviada. HTTP %s", response.status)
    except (HTTPError, URLError, Exception) as exc:
        logger.error("Falha ao enviar Teams: %s", exc)


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "sim", "s"}


def month_folder_name(mm: int | str) -> str:
    return MONTHS_PT.get(f"{int(mm):02d}", f"{int(mm):02d}. Mês")


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def unique_destination(dst: Path) -> Tuple[Path, bool]:
    if not dst.exists():
        return dst, False
    for i in range(1, 1000):
        candidate = dst.with_name(f"{dst.stem}_{i:03d}{dst.suffix}")
        if not candidate.exists():
            return candidate, True
    raise RuntimeError(f"Não foi possível gerar nome único para {dst}")


def zip_identity(zip_path: Path) -> str:
    st = zip_path.stat()
    return f"{zip_path.name}|{st.st_size}|{int(st.st_mtime)}"


def load_processed_db(db_path: Path, logger: logging.Logger) -> Dict[str, dict]:
    if not db_path.exists():
        return {}
    try:
        data = json.loads(db_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {item: {"legacy": True} for item in data}
    except Exception as exc:
        logger.warning("Não foi possível ler banco de processados: %s", exc)
    return {}


def save_processed_db(db_path: Path, data: Dict[str, dict], logger: logging.Logger) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(db_path)
    logger.info("Banco de processados atualizado: %s", db_path)


def infer_destination_key(path: Path) -> Optional[str]:
    text = normalize(str(path))
    for key in ["Bank03", "Bank05", "Bank08", "Bank10", "Bank13", "Bank15", "eventos", "alarmes"]:
        for alias in BANK_ALIASES[key]:
            if normalize(alias) in text:
                return key
    return None


def parse_bank_type(name: str) -> Optional[str]:
    lower = name.lower()
    if "hourly" in lower:
        return "Hourly"
    if "daily" in lower:
        return "Daily"
    if "monthly" in lower:
        return "Monthly"
    if "pvtcalibration" in lower or "pvt_calibration" in lower or "pvt-calibration" in lower:
        return "PVTCalibration"
    return None


def parse_bank_datetime(name: str) -> Optional[Tuple[int, int, int]]:
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name)
    if not m:
        return None
    try:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        date(y, mo, d)
        return y, mo, d
    except ValueError:
        return None


def parse_hourly_actual(name: str) -> Optional[Tuple[date, int]]:
    m = re.search(r"hourly-(20\d{2})(\d{2})(\d{2})-(\d{2})\d{4}\+0000", name.lower())
    if not m:
        m = re.search(r"hourly.*?(20\d{2})(\d{2})(\d{2}).*?(\d{2})\d{4}", name.lower())
    if not m:
        return None
    y, mo, d, h = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    if not 0 <= h <= 23:
        return None
    try:
        return date(y, mo, d), h
    except ValueError:
        return None


def parse_daily_actual(name: str) -> Optional[date]:
    m = re.search(r"daily-(20\d{2})(\d{2})(\d{2})-000000\+0000", name.lower())
    if not m:
        m = re.search(r"daily.*?(20\d{2})(\d{2})(\d{2}).*?000000", name.lower())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) - timedelta(days=1)
    except ValueError:
        return None


def parse_pvt_actual(name: str) -> Optional[date]:
    m = re.search(r"pvt(?:_|-)?calibration.*?-(20\d{2})(\d{2})(\d{2})-\d{6}\+0000", name.lower())
    if not m:
        dt = parse_bank_datetime(name)
        return date(*dt) if dt else None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def parse_monthly_actual(name: str) -> Optional[date]:
    """Parse Monthly report date. Format: B03_MPFM_Monthly-20260701-000000+0000.pdf
    The date represents the first day of the month being reported."""
    m = re.search(r"monthly-(20\d{2})(\d{2})(\d{2})-\d{6}\+0000", name.lower())
    if not m:
        m = re.search(r"monthly.*?(20\d{2})(\d{2})(\d{2})", name.lower())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def parse_alarm_date_from_name(name: str, fallback_year: int) -> Optional[date]:
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(?<!\d)(\d{2})[-_.](\d{2})(?!\d)", name)
    if m:
        first, second = int(m.group(1)), int(m.group(2))
        # nome pode vir como DD.MM (padrão) ou MM.DD (ex.: "07.17.2026"); tenta
        # DD.MM primeiro e inverte quando essa leitura resultar em mês inválido.
        for day, month in ((first, second), (second, first)):
            try:
                return date(fallback_year, month, day)
            except ValueError:
                continue
        return None
    return None


def safe_extract(zip_path: Path, extract_to: Path, logger: logging.Logger) -> None:
    extract_to.mkdir(parents=True, exist_ok=True)
    root = extract_to.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target = (extract_to / member.filename).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                raise RuntimeError(f"Entrada suspeita no ZIP (ZipSlip): {member.filename}")
        zf.extractall(extract_to)
    logger.info("ZIP extraído: %s", zip_path.name)


def process_one_zip(zip_path: Path, logger: logging.Logger, counters: Counters) -> None:
    logger.info("==== PROCESSANDO ZIP: %s ====", zip_path.name)
    with tempfile.TemporaryDirectory(prefix=f"dpb_{MODE.lower()}_") as tmp:
        extract_to = Path(tmp)
        safe_extract(zip_path, extract_to, logger)
        files = [p for p in extract_to.rglob("*") if p.is_file()]
        if not files:
            counters.stage1_errors += 1
            counters.add_error(f"ZIP sem arquivos: {zip_path.name}")
            return
        for src in files:
            key = infer_destination_key(src)
            if key is None:
                counters.stage1_unmatched += 1
                counters.unmatched_files.append(f"{zip_path.name}: {src.relative_to(extract_to)}")
                logger.warning("[STAGE1] Arquivo não identificado no ZIP %s: %s", zip_path.name, src.relative_to(extract_to))
                continue
            if src.suffix.lower() not in VALID_EXT_BY_KEY.get(key, {".pdf"}):
                counters.stage1_invalid_ext += 1
                counters.invalid_files.append(f"{zip_path.name}: {src.relative_to(extract_to)}")
                logger.warning("[STAGE1] Extensão não suportada para %s no ZIP %s: %s", key, zip_path.name, src.relative_to(extract_to))
                continue
            dest_base = Path(BASE_DESTINATIONS[key])
            dest_base.mkdir(parents=True, exist_ok=True)
            dst, renamed = unique_destination(dest_base / src.name)
            shutil.move(str(src), str(dst))
            counters.stage1_moved += 1
            logger.info("[STAGE1] Movido para base %s: %s", key, dst)


def organize_alarms_file(file_path: Path, base_alarm_dir: Path, logger: logging.Logger, counters: Counters, touched_alarm_months: Set[Tuple[int, int]], label: str = "ALARMES") -> None:
    fallback_year = datetime.now().year
    for part in file_path.parts:
        if re.fullmatch(r"20\d{2}", part):
            fallback_year = int(part)
            break
    dt = parse_alarm_date_from_name(file_path.name, fallback_year)
    if not dt:
        counters.stage2_errors += 1
        counters.add_error(f"[STAGE2][{label}] Data não identificada: {file_path.name}")
        logger.error("[STAGE2][%s] Data não identificada: %s", label, file_path.name)
        return
    target_dir = base_alarm_dir / str(dt.year) / month_folder_name(dt.month)
    target_dir.mkdir(parents=True, exist_ok=True)
    dst, renamed = unique_destination(target_dir / file_path.name)
    shutil.move(str(file_path), str(dst))
    counters.stage2_moved += 1
    if renamed:
        counters.stage2_duplicates_renamed += 1
    touched_alarm_months.add((dt.year, dt.month))
    logger.info("[STAGE2][%s] Organizado: %s", label, dst)


def organize_bank_file(file_path: Path, bank_base_dir: Path, logger: logging.Logger, counters: Counters, touched_bank_months: Dict[str, Set[Tuple[int, int]]], bank_key: str) -> None:
    ftype = parse_bank_type(file_path.name)
    if ftype is None:
        counters.stage2_errors += 1
        counters.add_error(f"[STAGE2][{bank_key}] Tipo não identificado: {file_path.name}")
        logger.error("[STAGE2][%s] Tipo Daily/Hourly/PVTCalibration não identificado: %s", bank_key, file_path.name)
        return

    if ftype == "Hourly":
        parsed = parse_hourly_actual(file_path.name)
        if not parsed:
            counters.stage2_errors += 1
            counters.add_error(f"[STAGE2][{bank_key}] Data/hora Hourly inválida: {file_path.name}")
            return
        actual_date = parsed[0]
    elif ftype == "Daily":
        actual_date = parse_daily_actual(file_path.name)
        if not actual_date:
            dt = parse_bank_datetime(file_path.name)
            if not dt:
                counters.stage2_errors += 1
                counters.add_error(f"[STAGE2][{bank_key}] Data Daily inválida: {file_path.name}")
                return
            actual_date = date(*dt)
    elif ftype == "PVTCalibration":
        actual_date = parse_pvt_actual(file_path.name)
        if not actual_date:
            counters.stage2_errors += 1
            counters.add_error(f"[STAGE2][{bank_key}] Data PVTCalibration inválida: {file_path.name}")
            return
    elif ftype == "Monthly":
        actual_date = parse_monthly_actual(file_path.name)
        if not actual_date:
            counters.stage2_errors += 1
            counters.add_error(f"[STAGE2][{bank_key}] Data Monthly inválida: {file_path.name}")
            return
    else:
        counters.stage2_errors += 1
        counters.add_error(f"[STAGE2][{bank_key}] Tipo não suportado: {file_path.name}")
        return

    target_dir = bank_base_dir / str(actual_date.year) / month_folder_name(actual_date.month) / ftype
    target_dir.mkdir(parents=True, exist_ok=True)
    dst, renamed = unique_destination(target_dir / file_path.name)
    shutil.move(str(file_path), str(dst))
    counters.stage2_moved += 1
    if renamed:
        counters.stage2_duplicates_renamed += 1
    if ftype in {"Daily", "Hourly"}:
        touched_bank_months.setdefault(bank_key, set()).add((actual_date.year, actual_date.month))
    logger.info("[STAGE2][%s] %s organizado/cadastrado: %s", bank_key, ftype, dst)


def stage2_organize_base_folders(logger: logging.Logger, counters: Counters, touched_alarm_months: Set[Tuple[int, int]], touched_bank_months: Dict[str, Set[Tuple[int, int]]], touched_event_months: Optional[Set[Tuple[int, int]]] = None) -> None:
    alarm_base = Path(BASE_DESTINATIONS["alarmes"])
    if alarm_base.exists():
        for f in list(alarm_base.iterdir()):
            if f.is_file() and f.suffix.lower() == ".pdf":
                organize_alarms_file(f, alarm_base, logger, counters, touched_alarm_months)
    events_base = Path(BASE_DESTINATIONS["eventos"])
    if touched_event_months is not None and events_base.exists():
        for f in list(events_base.iterdir()):
            if f.is_file() and f.suffix.lower() in VALID_EXT_BY_KEY["eventos"]:
                organize_alarms_file(f, events_base, logger, counters, touched_event_months, label="EVENTOS")
    for bank_key in BANK_CODE:
        bank_base = Path(BASE_DESTINATIONS[bank_key])
        if bank_base.exists():
            for f in list(bank_base.iterdir()):
                if f.is_file() and f.suffix.lower() == ".pdf":
                    organize_bank_file(f, bank_base, logger, counters, touched_bank_months, bank_key)


def list_pdf_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*.pdf") if p.is_file()]


def days_in_month(year: int, month: int) -> List[date]:
    return [date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)]


def expected_hourly_name(bank_code: str, d: date, hour: int) -> str:
    return f"{bank_code}_MPFM_Hourly-{d.strftime('%Y%m%d')}-{hour:02d}0000+0000.pdf"


def expected_daily_name(bank_code: str, d: date) -> str:
    gen = d + timedelta(days=1)
    return f"{bank_code}_MPFM_Daily-{gen.strftime('%Y%m%d')}-000000+0000.pdf"


def verify_month_alarm(alarm_base: Path, year: int, month: int) -> List[str]:
    month_dir = alarm_base / str(year) / month_folder_name(month)
    existing: Set[int] = set()
    for p in list_pdf_files(month_dir):
        dt = parse_alarm_date_from_name(p.name, year)
        if dt and dt.year == year and dt.month == month:
            existing.add(dt.day)
    return [f"ALARMES ausente: {d.isoformat()}" for d in days_in_month(year, month) if d.day not in existing]


def verify_month_bank(bank_base: Path, bank_code: str, year: int, month: int) -> List[str]:
    scan_roots = [bank_base / str(year)]
    if month == 12:
        scan_roots.append(bank_base / str(year + 1))
    hourly_present: Dict[date, Set[int]] = defaultdict(set)
    daily_present: Set[date] = set()
    for root in scan_roots:
        for p in list_pdf_files(root):
            if bank_code.lower() not in p.name.lower():
                continue
            hp = parse_hourly_actual(p.name)
            if hp:
                hourly_present[hp[0]].add(hp[1])
                continue
            dp = parse_daily_actual(p.name)
            if dp:
                daily_present.add(dp)
    missing: List[str] = []
    for d in days_in_month(year, month):
        if d not in daily_present:
            missing.append(f"{bank_code} Daily ausente: {d.isoformat()} esperado {expected_daily_name(bank_code, d)}")
        for hour in range(24):
            if hour not in hourly_present.get(d, set()):
                missing.append(f"{bank_code} Hourly ausente: {d.isoformat()} {hour:02d}:00 esperado {expected_hourly_name(bank_code, d, hour)}")
    return missing


def stage3_verify(logger: logging.Logger, counters: Counters, touched_alarm_months: Set[Tuple[int, int]], touched_bank_months: Dict[str, Set[Tuple[int, int]]], zip_folder: Path) -> Optional[Path]:
    if not touched_alarm_months and not touched_bank_months:
        logger.info("Nenhum mês Daily/Hourly/Alarmes tocado; Stage 3 não executada.")
        return None
    lines: List[str] = ["===== STAGE 3 - VERIFICAÇÃO DE COMPLETUDE ====="]
    total_missing = 0
    for year, month in sorted(touched_alarm_months):
        missing = verify_month_alarm(Path(BASE_DESTINATIONS["alarmes"]), year, month)
        total_missing += len(missing)
        lines.append(f"ALARMES {year}-{month:02d}: faltantes={len(missing)}")
        lines.extend(f"  - {m}" for m in missing[:300])
        if len(missing) > 300:
            lines.append(f"  - ... {len(missing)-300} itens adicionais omitidos")
    for bank_key, months in sorted(touched_bank_months.items()):
        for year, month in sorted(months):
            bank_code = BANK_CODE[bank_key]
            missing = verify_month_bank(Path(BASE_DESTINATIONS[bank_key]), bank_code, year, month)
            total_missing += len(missing)
            lines.append(f"{bank_key}/{bank_code} {year}-{month:02d}: faltantes={len(missing)}")
            lines.extend(f"  - {m}" for m in missing[:300])
            if len(missing) > 300:
                lines.append(f"  - ... {len(missing)-300} itens adicionais omitidos")
    counters.stage3_missing = total_missing
    lines.append(f"TOTAL DE ITENS FALTANTES: {total_missing}")
    for line in lines:
        if "faltantes=0" in line or line.startswith("=====") or line.startswith("TOTAL"):
            logger.info(line)
        else:
            logger.warning(line)
    report = zip_folder / f"DPB_{MODE}_Verification_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Relatório Stage 3 salvo: %s", report)
    return report


def build_summary(c: Counters, log_file: Path, report: Optional[Path]) -> str:
    status = "OK" if not c.errors and not c.stage1_errors and not c.stage2_errors and c.stage3_missing == 0 else "ATENÇÃO"
    lines = [
        f"DPB Bacalhau - {MODE} concluído com status: {status}",
        f"Data/hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"ZIPs encontrados/avaliados: {c.zips_found}",
        f"ZIPs processados: {c.zips_processed}",
        f"ZIPs ignorados por já processados: {c.zips_skipped}",
        f"Stage 1 - PDFs movidos para base: {c.stage1_moved}",
        f"Stage 1 - não identificados: {c.stage1_unmatched}",
        f"Stage 1 - extensão inválida/não-PDF: {c.stage1_invalid_ext}",
        f"Stage 2 - PDFs organizados/cadastrados: {c.stage2_moved}",
        f"Stage 2 - duplicidades renomeadas: {c.stage2_duplicates_renamed}",
        f"Stage 2 - erros: {c.stage2_errors}",
        f"Stage 3 - itens faltantes: {c.stage3_missing}",
        f"Log: {log_file}",
    ]
    if report:
        lines.append(f"Relatório de verificação: {report}")
    if c.errors:
        lines.append("Erros principais:")
        lines.extend(f"- {e}" for e in c.errors[:30])
    if c.unmatched_files:
        lines.append("Arquivos não identificados no ZIP:")
        lines.extend(f"- {x}" for x in c.unmatched_files[:30])
    return "\n".join(lines)


def candidate_zips(zip_folder: Path) -> List[Path]:
    zips = sorted(zip_folder.glob("*.zip"), key=lambda p: p.stat().st_mtime)
    if MODE == "ULTIMO":
        return zips[-1:] if zips else []
    return zips


def cleanup_processed_zips(zip_folder: Path, processed_db: Dict[str, dict], logger: logging.Logger) -> Tuple[int, int]:
    """Move ZIPs already processed to Registros Automacao Email folder.
    Returns: (moved_count, kept_count)"""
    registros_folder = zip_folder / "Registros Automacao Email"
    registros_folder.mkdir(parents=True, exist_ok=True)
    
    moved = 0
    kept = 0
    
    for zip_path in zip_folder.glob("*.zip"):
        zid = zip_identity(zip_path)
        if zid in processed_db or zip_path.name in processed_db:
            # ZIP já processado, mover para registros
            dest = registros_folder / zip_path.name
            if dest.exists():
                # Se já existe, adicionar timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = zip_path.stem
                dest = registros_folder / f"{stem}_{timestamp}.zip"
            try:
                shutil.move(str(zip_path), str(dest))
                moved += 1
                logger.info("✓ Movido para Registros: %s", zip_path.name)
            except Exception as exc:
                logger.error("Erro ao mover ZIP %s: %s", zip_path.name, exc)
        else:
            kept += 1
            logger.info("Mantido (não processado): %s", zip_path.name)
    
    return moved, kept


def cleanup_execution_files(zip_folder: Path, current_log: Path, logger: logging.Logger) -> int:
    """Move logs and control files to Registros Automação MPFM folder.
    Excludes the current log file being used.
    Returns: count of files moved"""
    registros_mpfm = zip_folder / "Registros Automação MPFM"
    registros_mpfm.mkdir(parents=True, exist_ok=True)
    
    # Padrões de arquivos a mover
    patterns = [
        "DPB_TODOS_Log_*.txt",
        "DPB_ULTIMO_Log_*.txt",
        "DPB_TODOS_Verification_*.txt",
        "DPB_ULTIMO_Verification_*.txt",
        "DPB_Duplicados_*.txt",
        "DPB_Duplicados_*.csv"
    ]
    
    moved = 0
    for pattern in patterns:
        for file_path in zip_folder.glob(pattern):
            # Não mover o log atual
            if file_path == current_log:
                continue
            
            dest = registros_mpfm / file_path.name
            # Se já existe, adicionar timestamp
            if dest.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = file_path.stem
                suffix = file_path.suffix
                dest = registros_mpfm / f"{stem}_{timestamp}{suffix}"
            
            try:
                shutil.move(str(file_path), str(dest))
                moved += 1
                logger.info("✓ Movido para Registros MPFM: %s", file_path.name)
            except Exception as exc:
                logger.error("Erro ao mover arquivo %s: %s", file_path.name, exc)
    
    return moved


def main() -> int:
    zip_folder = Path(os.environ.get("DPB_ZIP_FOLDER", DEFAULT_ZIP_FOLDER)).expanduser()
    zip_folder.mkdir(parents=True, exist_ok=True)
    log_file = zip_folder / f"DPB_{MODE}_Log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    logger = setup_logger(log_file)
    logger.info("Modo: %s", MODE)
    logger.info("Pasta de ZIPs: %s", zip_folder)

    counters = Counters()
    db_path = zip_folder / PROCESSED_DB
    processed_db = load_processed_db(db_path, logger)
    reprocess = env_flag("DPB_REPROCESS")

    zips = candidate_zips(zip_folder)
    counters.zips_found = len(zips)
    if not zips:
        msg = f"Nenhum ZIP encontrado em: {zip_folder}"
        logger.warning(msg)
        post_teams(msg, logger)
        # Limpar logs antigos mesmo sem ZIPs para processar
        logger.info("==== LIMPEZA DE ARQUIVOS DE EXECUÇÃO ====")
        files_moved = cleanup_execution_files(zip_folder, log_file, logger)
        logger.info("Arquivos movidos para Registros MPFM: %d", files_moved)
        return 2

    touched_alarm_months: Set[Tuple[int, int]] = set()
    touched_event_months: Set[Tuple[int, int]] = set()
    touched_bank_months: Dict[str, Set[Tuple[int, int]]] = {}

    for zip_path in zips:
        zid = zip_identity(zip_path)
        if not reprocess and (zid in processed_db or zip_path.name in processed_db):
            counters.zips_skipped += 1
            logger.info("ZIP já processado; ignorado: %s", zip_path.name)
            continue
        try:
            process_one_zip(zip_path, logger, counters)
            counters.zips_processed += 1
            processed_db[zid] = {
                "name": zip_path.name,
                "path": str(zip_path),
                "size": zip_path.stat().st_size,
                "mtime": datetime.fromtimestamp(zip_path.stat().st_mtime).isoformat(timespec="seconds"),
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "mode": MODE,
            }
        except Exception as exc:
            counters.stage1_errors += 1
            counters.add_error(f"Erro ao processar ZIP {zip_path.name}: {exc}")
            logger.exception("Erro ao processar ZIP %s: %s", zip_path.name, exc)

    stage2_organize_base_folders(logger, counters, touched_alarm_months, touched_bank_months, touched_event_months)
    report = stage3_verify(logger, counters, touched_alarm_months, touched_bank_months, zip_folder)
    save_processed_db(db_path, processed_db, logger)
    
    # Limpar ZIPs já processados
    logger.info("==== LIMPEZA DE ZIPs PROCESSADOS ====")
    moved, kept = cleanup_processed_zips(zip_folder, processed_db, logger)
    logger.info("==== LIMPEZA CONCLUÍDA ====")
    logger.info("ZIPs movidos para Registros: %d | ZIPs mantidos: %d", moved, kept)
    
    # Limpar logs e arquivos de controle antigos
    logger.info("==== LIMPEZA DE ARQUIVOS DE EXECUÇÃO ====")
    files_moved = cleanup_execution_files(zip_folder, log_file, logger)
    logger.info("==== LIMPEZA CONCLUÍDA ====")
    logger.info("Arquivos movidos para Registros MPFM: %d", files_moved)
    
    summary = build_summary(counters, log_file, report)
    logger.info("\n%s", summary)
    post_teams(summary, logger)

    if counters.stage1_errors or counters.stage2_errors or counters.errors:
        return 1
    if counters.stage3_missing:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

