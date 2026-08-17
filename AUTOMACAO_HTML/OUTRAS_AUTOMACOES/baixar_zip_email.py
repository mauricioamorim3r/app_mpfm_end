#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DPB FPSO Bacalhau - Download automático de ZIPs por e-mail.

Critérios:
- Conta: mauam@equinor.com
- Remetente: MeteringTech.BAC@modec.com
- Assunto deve conter: Metering Daily Reports
- E-mail deve ter anexo
- Anexo deve ser .zip
- Nome do anexo deve conter:
    1) configuration-
    2) FPSO-Bacalhau_Daily

Após baixar os ZIPs, opcionalmente executa o script principal:
dpb_bacalhau_ultimo_zip.py
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import win32com.client


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

WORKSPACE_ROOT = Path(os.environ.get("DPB_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent)).expanduser()

MAILBOX = os.environ.get("DPB_MAILBOX", "").strip()

REQUIRED_SENDER = os.environ.get("DPB_REQUIRED_SENDER", "meteringtech.bac@modec.com").strip().lower()

REQUIRED_SUBJECT_TEXT = "Metering Daily Reports"

ZIP_NAME_PATTERNS = [
    "configuration-",
    "FPSO-Bacalhau_Daily",
    "FCVs update",  # Aceita tanto "FCVs update" quanto "FCVs updated"
    "Events_Snapshot",  # Download automático de ZIPs de eventos
]

ZIP_DESTINATION_FOLDER = Path(
    WORKSPACE_ROOT / "Zip"
)

PROCESSED_EMAIL_DB = ZIP_DESTINATION_FOLDER / "dpb_processed_email_attachments.json"

LOG_FILE = ZIP_DESTINATION_FOLDER / f"DPB_Email_Download_Log_{datetime.now().strftime('%Y-%m-%d')}.txt"

# Quantos dias para trás procurar e-mails.
# Para rotina diária, 3 dias dá margem para finais de semana, atrasos ou execução perdida.
LOOKBACK_DAYS = 3

# Executar o script principal após baixar os ZIPs?
RUN_MAIN_DPB_SCRIPT = os.environ.get("DPB_EMAIL_RUN_MAIN", "1").strip().lower() not in {"0", "false", "no", "n", "nao", "não"}

MAIN_DPB_SCRIPT = Path(__file__).with_name("dpb_bacalhau_todos_zips.py")

# Pasta destino para descompactação dos Daily Reports
DAILY_REPORTS_DESTINATION = Path(os.environ.get("DPB_DAILY_REPORTS_DESTINATION", str(WORKSPACE_ROOT / "Daily Reports")))

# Descompactar automaticamente os ZIPs de Daily Reports?
AUTO_EXTRACT_DAILY_REPORTS = True

# Pasta destino para descompactação dos FCVs Updated
FCVS_DESTINATION = Path(os.environ.get("DPB_FCVS_DESTINATION", str(WORKSPACE_ROOT / "FCVs Updated")))


def safe_extract_zip(zip_ref: zipfile.ZipFile, destination: Path) -> None:
    """Bloqueia caminhos absolutos/ZipSlip antes da extração."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    members = zip_ref.infolist()
    max_files = int(os.environ.get("DPB_ZIP_MAX_FILES", "20000"))
    max_bytes = int(os.environ.get("DPB_ZIP_MAX_UNCOMPRESSED_BYTES", str(5 * 1024**3)))
    if len(members) > max_files or sum(item.file_size for item in members) > max_bytes:
        raise RuntimeError("ZIP excede os limites seguros configurados.")
    for member in members:
        target = (destination / member.filename).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"Entrada suspeita no ZIP: {member.filename}") from exc
    zip_ref.extractall(destination)

# Descompactar automaticamente os ZIPs de FCVs Updated?
AUTO_EXTRACT_FCVS = True

# Pasta para mover arquivos processados
PROCESSED_FILES_FOLDER = ZIP_DESTINATION_FOLDER / "Registros Automacao Email"

# Mover arquivos processados automaticamente?
AUTO_MOVE_PROCESSED = True


# =============================================================================
# LOG
# =============================================================================

def setup_logger() -> logging.Logger:
    ZIP_DESTINATION_FOLDER.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("DPB_EMAIL_DOWNLOADER")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info("Log iniciado: %s", LOG_FILE)
    return logger


# =============================================================================
# CONTROLE DE PROCESSADOS
# =============================================================================

def load_processed_db() -> dict:
    if not PROCESSED_EMAIL_DB.exists():
        return {}

    try:
        return json.loads(PROCESSED_EMAIL_DB.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_processed_db(data: dict) -> None:
    PROCESSED_EMAIL_DB.parent.mkdir(parents=True, exist_ok=True)
    tmp = PROCESSED_EMAIL_DB.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(PROCESSED_EMAIL_DB)


# =============================================================================
# UTILITÁRIOS
# =============================================================================

def normalize_email(value: str) -> str:
    if not value:
        return ""
    return value.strip().lower()


def attachment_name_is_valid(filename: str) -> bool:
    name = filename or ""

    if not name.lower().endswith(".zip"):
        return False

    return any(pattern.lower() in name.lower() for pattern in ZIP_NAME_PATTERNS)


def safe_filename(filename: str) -> str:
    """
    Remove caracteres problemáticos para Windows.
    """
    filename = filename.strip()
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    return filename


def unique_destination(path: Path) -> Path:
    """
    Evita sobrescrever arquivo existente.
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix

    for i in range(1, 1000):
        candidate = path.with_name(f"{stem}_{i:03d}{suffix}")
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Não foi possível gerar nome único para: {path}")


def get_sender_smtp_address(message) -> str:
    """
    Tenta obter o endereço SMTP real do remetente.

    Em ambiente Exchange/Outlook, SenderEmailAddress às vezes retorna DN interno,
    e não o SMTP. Esta função tenta resolver a propriedade SMTP quando aplicável.
    """
    try:
        sender_email = message.SenderEmailAddress
        if sender_email and "@" in sender_email:
            return normalize_email(sender_email)
    except Exception:
        pass

    try:
        sender = message.Sender
        if sender is not None:
            exch_user = sender.GetExchangeUser()
            if exch_user is not None:
                smtp = exch_user.PrimarySmtpAddress
                if smtp:
                    return normalize_email(smtp)
    except Exception:
        pass

    return ""


def message_identity(message, attachment_filename: str) -> str:
    """
    Identidade para evitar reprocessamento.
    Usa EntryID do e-mail + nome do anexo.
    """
    try:
        entry_id = message.EntryID
    except Exception:
        entry_id = ""

    try:
        received = message.ReceivedTime.strftime("%Y%m%d%H%M%S")
    except Exception:
        received = ""

    return f"{entry_id}|{received}|{attachment_filename}"


# =============================================================================
# OUTLOOK
# =============================================================================

def get_inbox_folder(logger: logging.Logger):
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    # 6 = olFolderInbox
    inbox = namespace.GetDefaultFolder(6)

    logger.info("Inbox acessada com sucesso.")
    return inbox


def download_matching_attachments(logger: logging.Logger) -> list[Path]:
    ZIP_DESTINATION_FOLDER.mkdir(parents=True, exist_ok=True)

    processed = load_processed_db()
    downloaded_files: list[Path] = []

    inbox = get_inbox_folder(logger)

    items = inbox.Items
    items.Sort("[ReceivedTime]", True)

    since = datetime.now() - timedelta(days=LOOKBACK_DAYS)

    logger.info("Procurando e-mails recebidos desde: %s", since.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("Remetente obrigatório: %s", REQUIRED_SENDER)
    logger.info("Texto obrigatório no assunto: %s", REQUIRED_SUBJECT_TEXT)
    logger.info("Pasta destino de ZIPs: %s", ZIP_DESTINATION_FOLDER)

    checked = 0
    matched_messages = 0

    for message in items:
        checked += 1

        try:
            received_time = message.ReceivedTime.replace(tzinfo=None)
        except Exception:
            continue

        # Como os itens estão ordenados do mais novo para o mais antigo,
        # pode parar quando sair da janela de busca.
        if received_time < since:
            break

        try:
            subject = message.Subject or ""
        except Exception:
            subject = ""

        if REQUIRED_SUBJECT_TEXT.lower() not in subject.lower():
            continue

        sender_email = get_sender_smtp_address(message)

        if sender_email != REQUIRED_SENDER:
            logger.info(
                "E-mail ignorado por remetente diferente. Remetente=%s | Assunto=%s",
                sender_email,
                subject,
            )
            continue

        try:
            has_attachments = bool(message.Attachments.Count > 0)
        except Exception:
            has_attachments = False

        if not has_attachments:
            logger.warning(
                "E-mail atende remetente/assunto, mas não possui anexo. Assunto=%s",
                subject,
            )
            continue

        matched_messages += 1

        logger.info(
            "E-mail elegível encontrado. Recebido=%s | Remetente=%s | Assunto=%s | Anexos=%s",
            received_time.strftime("%Y-%m-%d %H:%M:%S"),
            sender_email,
            subject,
            message.Attachments.Count,
        )

        for i in range(1, message.Attachments.Count + 1):
            attachment = message.Attachments.Item(i)
            original_filename = attachment.FileName

            if not attachment_name_is_valid(original_filename):
                logger.info(
                    "Anexo ignorado por não atender critérios de nome/formato: %s",
                    original_filename,
                )
                continue

            identity = message_identity(message, original_filename)

            if identity in processed:
                logger.info(
                    "Anexo já processado anteriormente, ignorado: %s",
                    original_filename,
                )
                continue

            filename = safe_filename(original_filename)
            destination = unique_destination(ZIP_DESTINATION_FOLDER / filename)

            attachment.SaveAsFile(str(destination))

            processed[identity] = {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "received_time": received_time.isoformat(timespec="seconds"),
                "sender": sender_email,
                "subject": subject,
                "attachment_name": original_filename,
                "saved_path": str(destination),
            }

            downloaded_files.append(destination)

            logger.info("ZIP salvo com sucesso: %s", destination)

    save_processed_db(processed)

    logger.info("E-mails avaliados: %s", checked)
    logger.info("E-mails elegíveis encontrados: %s", matched_messages)
    logger.info("ZIPs baixados nesta execução: %s", len(downloaded_files))

    return downloaded_files


# =============================================================================
# DESCOMPACTAÇÃO DE DAILY REPORTS
# =============================================================================

def get_month_name(month: int) -> str:
    """
    Retorna o nome do mês em português com formato: "01. Janeiro"
    """
    months = {
        1: "01. Janeiro",
        2: "02. Fevereiro",
        3: "03. Março",
        4: "04. Abril",
        5: "05. Maio",
        6: "06. Junho",
        7: "07. Julho",
        8: "08. Agosto",
        9: "09. Setembro",
        10: "10. Outubro",
        11: "11. Novembro",
        12: "12. Dezembro",
    }
    return months.get(month, f"{month:02d}. Mês")


def validate_extracted_structure(extract_path: Path, logger: logging.Logger) -> dict:
    """
    Valida a estrutura do ZIP descompactado.
    Retorna um dicionário com status de cada pasta/arquivo esperado.
    """
    validation = {
        "success": True,
        "missing_folders": [],
        "cv_reports_folders": [],
        "ihm_reports_files": [],
        "xml_folders": [],
    }

    # Verificar se a pasta existe
    if not extract_path.exists():
        logger.error("Pasta extraída não encontrada: %s", extract_path)
        validation["success"] = False
        validation["missing_folders"] = ["01 - CV_Reports", "03 - IHM_Reports", "05 - XML"]
        return validation

    # Verificar pasta 01 - CV_Reports
    cv_reports_path = extract_path / "01 - CV_Reports"
    if not cv_reports_path.exists():
        validation["success"] = False
        validation["missing_folders"].append("01 - CV_Reports")
    else:
        # Verificar 21 pastas FC01 a FC21
        for i in range(1, 22):
            fc_folder = f"FC{i:02d}"
            found = False
            for folder in cv_reports_path.iterdir():
                if folder.is_dir() and fc_folder in folder.name:
                    validation["cv_reports_folders"].append(fc_folder)
                    found = True
                    break
            if not found:
                logger.warning("Pasta %s não encontrada em 01 - CV_Reports", fc_folder)

    # Verificar pasta 03 - IHM_Reports
    ihm_reports_path = extract_path / "03 - IHM_Reports"
    if not ihm_reports_path.exists():
        validation["success"] = False
        validation["missing_folders"].append("03 - IHM_Reports")
    else:
        # Verificar 4 arquivos Excel
        expected_files = ["daily_gas", "daily_oil", "daily_water", "gasBalance"]
        for expected in expected_files:
            found = False
            for file in ihm_reports_path.iterdir():
                if file.is_file() and expected.lower() in file.name.lower():
                    validation["ihm_reports_files"].append(expected)
                    found = True
                    break
            if not found:
                logger.warning("Arquivo com '%s' não encontrado em 03 - IHM_Reports", expected)

    # Verificar pasta 05 - XML
    xml_path = extract_path / "05 - XML"
    if not xml_path.exists():
        validation["success"] = False
        validation["missing_folders"].append("05 - XML")
    else:
        # Verificar 4 arquivos/pastas: 001, 002, 003, 004
        expected_items = ["001", "002", "003", "004"]
        for expected in expected_items:
            found = False
            for item in xml_path.iterdir():
                if expected in item.name:
                    validation["xml_folders"].append(expected)
                    found = True
                    break
            if not found:
                logger.warning("Item com '%s' não encontrado em 05 - XML", expected)

    return validation


def extract_daily_reports(downloaded_files: list[Path], logger: logging.Logger) -> tuple[int, list[Path]]:
    """
    Descompacta arquivos ZIP de Daily Reports nas pastas de ano/mês correspondentes.
    Retorna (exit_code, processed_files):
        - exit_code: 0 se sucesso, código de erro caso contrário
        - processed_files: lista de arquivos que foram processados com sucesso
    """
    if not downloaded_files:
        return 0, []

    logger.info("==== INICIANDO DESCOMPACTAÇÃO DE DAILY REPORTS ====")

    # Filtrar arquivos que contêm "FPSO-Bacalhau_Daily reports" OU "configuration-" (case-insensitive)
    daily_report_zips = [
        f for f in downloaded_files 
        if "FPSO-Bacalhau_Daily reports" in f.name or f.name.lower().startswith("configuration-")
    ]

    if not daily_report_zips:
        logger.info("Nenhum arquivo de Daily Reports para descompactar.")
        return 0, []

    logger.info("Arquivos de Daily Reports encontrados: %d", len(daily_report_zips))

    extracted_count = 0
    errors = []
    successfully_processed = []  # Lista de arquivos processados com sucesso

    for zip_file in daily_report_zips:
        try:
            # Extrair data do nome do arquivo - suporta dois formatos:
            # 1) FPSO-Bacalhau_Daily reports_2026-07-05.zip (formato YYYY-MM-DD)
            # 2) Configuration-1.20260708060057.zip (formato YYYYMMDD)
            
            year = None
            month = None
            day = None
            
            # Tentar primeiro formato: YYYY-MM-DD (com hífens)
            match = re.search(r"(\d{4})-(\d{2})-(\d{2})", zip_file.name)
            if match:
                year = match.group(1)
                month = match.group(2)
                day = match.group(3)
            else:
                # Tentar segundo formato: YYYYMMDD (sem hífens, 8 dígitos seguidos)
                match = re.search(r"(\d{4})(\d{2})(\d{2})", zip_file.name)
                if match:
                    year = match.group(1)
                    month = match.group(2)
                    day = match.group(3)
            
            if not year or not month or not day:
                logger.warning("Não foi possível extrair data do nome: %s", zip_file.name)
                continue

            # Criar caminho de destino: ano/mês
            month_name = get_month_name(int(month))
            destination = DAILY_REPORTS_DESTINATION / year / month_name

            # Criar pastas se não existirem
            destination.mkdir(parents=True, exist_ok=True)

            logger.info("Descompactando %s para %s", zip_file.name, destination)

            # Descompactar
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                safe_extract_zip(zip_ref, destination)

            logger.info("ZIP descompactado com sucesso: %s", zip_file.name)

            # A pasta extraída tem o nome do ZIP (sem extensão)
            extracted_folder_name = zip_file.stem  # Remove .zip
            extracted_folder = destination / extracted_folder_name

            # Validar estrutura descompactada APENAS para arquivos FPSO-Bacalhau_Daily
            # (arquivos Configuration podem ter estrutura diferente)
            if "FPSO-Bacalhau_Daily" in zip_file.name:
                validation = validate_extracted_structure(extracted_folder, logger)

                if validation["missing_folders"]:
                    logger.error(
                        "Pastas principais faltando após descompactação: %s",
                        ", ".join(validation["missing_folders"]),
                    )
                    errors.append(f"{zip_file.name}: Pastas faltando - {validation['missing_folders']}")
                else:
                    logger.info("✓ Todas as 3 pastas principais foram descompactadas")

                # Relatório de validação
                logger.info(
                    "Validação - CV_Reports: %d/21 pastas FC encontradas",
                    len(validation["cv_reports_folders"]),
                )
                logger.info(
                    "Validação - IHM_Reports: %d/4 arquivos Excel encontrados",
                    len(validation["ihm_reports_files"]),
                )
                logger.info(
                    "Validação - XML: %d/4 pastas encontradas",
                    len(validation["xml_folders"]),
                )
            else:
                # Para arquivos Configuration, organizar TODOS os arquivos .txt por dia
                logger.info("Processando arquivos .txt extraídos...")
                
                # Pegar TODOS os arquivos .txt extraídos diretamente na pasta do mês
                # (Configuration, Events_Snapshot, e qualquer outro .txt)
                all_txt_files = list(destination.glob("*.txt"))
                
                moved_count = 0
                for txt_file in all_txt_files:
                    try:
                        # Extrair data do nome do arquivo: Configuration-1.YYYYMMDDHHMMSS.txt
                        match = re.search(r"(\d{4})(\d{2})(\d{2})", txt_file.name)
                        if not match:
                            logger.warning("Não foi possível extrair data de: %s", txt_file.name)
                            continue
                        
                        file_year = match.group(1)
                        file_month = match.group(2)
                        file_day = match.group(3)
                        
                        # Construir nome da pasta do dia
                        day_folder_name = f"FPSO-Bacalhau_Daily reports_{file_year}-{file_month}-{file_day}"
                        day_folder = destination / day_folder_name
                        
                        # Verificar se a pasta do dia existe
                        if not day_folder.exists():
                            logger.warning("Pasta do dia não encontrada: %s", day_folder_name)
                            logger.info("Arquivo %s permanecerá na pasta do mês", txt_file.name)
                            continue
                        
                        # Mover arquivo para a pasta do dia
                        target_path = day_folder / txt_file.name
                        
                        # Se já existe, adicionar timestamp
                        if target_path.exists():
                            timestamp = datetime.now().strftime("%H%M%S")
                            stem = target_path.stem
                            suffix = target_path.suffix
                            target_path = day_folder / f"{stem}_{timestamp}{suffix}"
                        
                        txt_file.rename(target_path)
                        logger.info("✓ Movido: %s → %s", txt_file.name, day_folder_name)
                        moved_count += 1
                        
                    except Exception as e:
                        logger.warning("Erro ao mover %s: %s", txt_file.name, e)
                
                logger.info("Arquivos Configuration organizados: %d/%d movidos para pastas do dia", 
                           moved_count, len(all_txt_files))

            extracted_count += 1
            successfully_processed.append(zip_file)  # Adiciona à lista de processados

        except zipfile.BadZipFile:
            logger.error("Arquivo ZIP corrompido: %s", zip_file)
            errors.append(f"{zip_file.name}: Arquivo corrompido")
        except Exception as exc:
            logger.exception("Erro ao descompactar %s: %s", zip_file.name, exc)
            errors.append(f"{zip_file.name}: {str(exc)}")

    logger.info("==== DESCOMPACTAÇÃO FINALIZADA ====")
    logger.info("Total descompactado: %d/%d", extracted_count, len(daily_report_zips))

    if errors:
        logger.warning("Erros durante descompactação:")
        for error in errors:
            logger.warning(" - %s", error)
        return 1, successfully_processed

    # Após processar com sucesso, organizar arquivos .txt órfãos no mês/ano atual
    if successfully_processed:
        organize_orphan_txt_files(logger)

    return 0, successfully_processed


def organize_orphan_txt_files(logger: logging.Logger):
    """
    Procura arquivos .txt soltos nas pastas de mês do ano atual e os organiza
    nas pastas de dia correspondentes, caso existam.
    
    Esta função é chamada automaticamente após processar um Daily Reports ZIP
    para garantir que arquivos Configuration/Events extraídos anteriormente
    sejam organizados quando a pasta do dia for criada.
    """
    logger.info("==== VERIFICANDO ARQUIVOS .TXT ÓRFÃOS ====")
    
    # Obter ano e mês atual
    now = datetime.now()
    current_year = str(now.year)
    current_month = now.month
    month_name = get_month_name(current_month)
    
    # Caminho da pasta do mês atual
    month_folder = DAILY_REPORTS_DESTINATION / current_year / month_name
    
    if not month_folder.exists():
        logger.info("Pasta do mês atual não existe: %s", month_folder)
        return
    
    # Procurar arquivos .txt soltos diretamente na pasta do mês
    orphan_txt_files = [f for f in month_folder.glob("*.txt") if f.is_file()]
    
    if not orphan_txt_files:
        logger.info("Nenhum arquivo .txt órfão encontrado na pasta do mês")
        return
    
    logger.info("Arquivos .txt órfãos encontrados: %d", len(orphan_txt_files))
    
    moved_count = 0
    skipped_count = 0
    
    for txt_file in orphan_txt_files:
        try:
            # Extrair data do nome do arquivo: YYYYMMDDHHMMSS
            match = re.search(r"(\d{4})(\d{2})(\d{2})", txt_file.name)
            if not match:
                logger.warning("Data não encontrada no nome: %s", txt_file.name)
                skipped_count += 1
                continue
            
            file_year = match.group(1)
            file_month = match.group(2)
            file_day = match.group(3)
            
            # Construir nome da pasta do dia
            day_folder_name = f"FPSO-Bacalhau_Daily reports_{file_year}-{file_month}-{file_day}"
            day_folder = month_folder / day_folder_name
            
            # Verificar se a pasta do dia existe
            if not day_folder.exists():
                logger.info("Pasta do dia ainda não existe: %s (arquivo: %s)", 
                           day_folder_name, txt_file.name)
                skipped_count += 1
                continue
            
            # Mover arquivo para a pasta do dia
            target_path = day_folder / txt_file.name
            
            # Se já existe, adicionar timestamp
            if target_path.exists():
                timestamp = datetime.now().strftime("%H%M%S")
                stem = target_path.stem
                suffix = target_path.suffix
                target_path = day_folder / f"{stem}_{timestamp}{suffix}"
            
            txt_file.rename(target_path)
            logger.info("✓ Órfão organizado: %s → %s", txt_file.name, day_folder_name)
            moved_count += 1
            
        except Exception as e:
            logger.warning("Erro ao organizar %s: %s", txt_file.name, e)
            skipped_count += 1
    
    logger.info("==== VERIFICAÇÃO CONCLUÍDA ====")
    logger.info("Arquivos organizados: %d | Aguardando pasta do dia: %d", 
               moved_count, skipped_count)


def extract_fcvs_updated(downloaded_files: list[Path], logger: logging.Logger) -> tuple[int, list[Path]]:
    """
    Descompacta arquivos ZIP de FCVs Updated nas pastas de ano/mês correspondentes.
    Formato esperado do nome: "FCVs update DD MM YYYY" (ex: FCVs update 04 07 2026)
    Retorna (exit_code, processed_files):
        - exit_code: 0 se sucesso, código de erro caso contrário
        - processed_files: lista de arquivos que foram processados com sucesso
    """
    if not downloaded_files:
        return 0, []

    logger.info("==== INICIANDO DESCOMPACTAÇÃO DE FCVs UPDATED ====")

    # Filtrar apenas arquivos que contêm "FCVs update" (aceita update ou updated)
    fcvs_zips = [f for f in downloaded_files if "FCVs update" in f.name]

    if not fcvs_zips:
        logger.info("Nenhum arquivo de FCVs Updated para descompactar.")
        return 0, []

    logger.info("Arquivos de FCVs Updated encontrados: %d", len(fcvs_zips))

    extracted_count = 0
    errors = []
    successfully_processed = []  # Lista de arquivos processados com sucesso

    for zip_file in fcvs_zips:
        try:
            # Extrair data do nome do arquivo: FCVs update(d) DD MM YYYY
            # Exemplo: FCVs updated 04 07 2026.zip ou FCVs update 04 07 2026.zip
            match = re.search(r"FCVs update[d]?\s+(\d{2})\s+(\d{2})\s+(\d{4})", zip_file.name, re.IGNORECASE)
            if not match:
                logger.warning("Não foi possível extrair data do nome: %s", zip_file.name)
                continue

            day = match.group(1)
            month = match.group(2)
            year = match.group(3)

            # Criar caminho de destino: ano/mês
            month_name = get_month_name(int(month))
            destination = FCVS_DESTINATION / year / month_name

            # Criar pastas se não existirem
            destination.mkdir(parents=True, exist_ok=True)

            logger.info("Descompactando %s para %s", zip_file.name, destination)

            # Descompactar
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                safe_extract_zip(zip_ref, destination)

            logger.info("ZIP descompactado com sucesso: %s", zip_file.name)
            logger.info("Data extraída: %s/%s/%s", day, month, year)

            extracted_count += 1
            successfully_processed.append(zip_file)  # Adiciona à lista de processados

        except zipfile.BadZipFile:
            logger.error("Arquivo ZIP corrompido: %s", zip_file)
            errors.append(f"{zip_file.name}: Arquivo corrompido")
        except Exception as exc:
            logger.exception("Erro ao descompactar %s: %s", zip_file.name, exc)
            errors.append(f"{zip_file.name}: {str(exc)}")

    logger.info("==== DESCOMPACTAÇÃO DE FCVs FINALIZADA ====")
    logger.info("Total descompactado: %d/%d", extracted_count, len(fcvs_zips))

    if errors:
        logger.warning("Erros durante descompactação de FCVs:")
        for error in errors:
            logger.warning(" - %s", error)
        return 1, successfully_processed

    return 0, successfully_processed


# =============================================================================
# MOVIMENTAÇÃO DE ARQUIVOS PROCESSADOS
# =============================================================================

def move_processed_files(processed_files: list[Path], logger: logging.Logger) -> int:
    """
    Move arquivos processados com sucesso para a pasta de registros.
    Isso mantém a pasta Zip limpa, contendo apenas arquivos pendentes de processamento.
    
    Args:
        processed_files: Lista de arquivos que foram processados com sucesso
        logger: Logger para registrar operações
        
    Returns:
        0 se sucesso, 1 se houve erros
    """
    if not processed_files:
        logger.info("Nenhum arquivo para mover.")
        return 0

    logger.info("==== MOVENDO ARQUIVOS PROCESSADOS ====")
    
    # Criar pasta de registros se não existir
    PROCESSED_FILES_FOLDER.mkdir(parents=True, exist_ok=True)
    logger.info("Pasta de destino: %s", PROCESSED_FILES_FOLDER)
    
    moved_count = 0
    errors = []
    
    for file_path in processed_files:
        try:
            if not file_path.exists():
                logger.warning("Arquivo não encontrado, ignorando: %s", file_path)
                continue
            
            destination = PROCESSED_FILES_FOLDER / file_path.name
            
            # Se já existe um arquivo com o mesmo nome no destino, adiciona timestamp
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = destination.stem
                suffix = destination.suffix
                destination = PROCESSED_FILES_FOLDER / f"{stem}_{timestamp}{suffix}"
                logger.info("Arquivo já existe no destino, usando nome: %s", destination.name)
            
            # Mover arquivo
            file_path.rename(destination)
            logger.info("✓ Movido: %s → %s", file_path.name, destination.name)
            moved_count += 1
            
        except Exception as exc:
            logger.exception("Erro ao mover arquivo %s: %s", file_path.name, exc)
            errors.append(f"{file_path.name}: {str(exc)}")
    
    logger.info("==== MOVIMENTAÇÃO FINALIZADA ====")
    logger.info("Total de arquivos movidos: %d/%d", moved_count, len(processed_files))
    
    if errors:
        logger.warning("Erros durante movimentação:")
        for error in errors:
            logger.warning(" - %s", error)
        return 1
    
    return 0


def cleanup_all_processed_zips(logger: logging.Logger) -> int:
    """
    Verifica TODOS os arquivos ZIP na pasta Zip e move para Registros os que já foram processados.
    Isso inclui:
    - ZIPs baixados por este script (dpb_processed_email_attachments.json)
    - ZIPs processados pelo dpb_bacalhau_ultimo_zip.py (dpb_processed_zips.json)
    
    Mantém a pasta Zip limpa, contendo apenas arquivos pendentes de processamento.
    """
    logger.info("==== LIMPEZA DE ZIPs JÁ PROCESSADOS ====")
    
    # Carregar banco de dados de ZIPs processados pelo dpb_bacalhau_ultimo_zip.py
    dpb_processed_zips_db = ZIP_DESTINATION_FOLDER / "dpb_processed_zips.json"
    processed_by_dpb = set()
    
    if dpb_processed_zips_db.exists():
        try:
            dpb_data = json.loads(dpb_processed_zips_db.read_text(encoding="utf-8"))
            processed_by_dpb = set(dpb_data.keys()) if isinstance(dpb_data, dict) else set()
            logger.info("Banco dpb_processed_zips.json carregado: %d ZIPs", len(processed_by_dpb))
        except Exception as e:
            logger.warning("Erro ao carregar dpb_processed_zips.json: %s", e)
    
    # Carregar banco de dados de anexos processados por este script
    processed_by_email = load_processed_db()
    
    # Coletar nomes de arquivos dos anexos já processados
    processed_attachments = set()
    for identity in processed_by_email.values():
        # Cada identity tem o formato "EntryID|ReceivedTime|FileName"
        if isinstance(identity, str) and "|" in identity:
            filename = identity.split("|")[-1]
            processed_attachments.add(filename)
    
    logger.info("Anexos já processados: %d arquivos", len(processed_attachments))
    
    # Criar pasta de registros se não existir
    PROCESSED_FILES_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Procurar todos os ZIPs na pasta Zip
    all_zips = list(ZIP_DESTINATION_FOLDER.glob("*.zip"))
    
    if not all_zips:
        logger.info("Nenhum arquivo ZIP encontrado na pasta.")
        return 0
    
    logger.info("ZIPs encontrados na pasta: %d", len(all_zips))
    
    moved_count = 0
    skipped_count = 0
    
    for zip_file in all_zips:
        try:
            # Verificar se o ZIP já foi processado
            is_processed = False
            reason = ""
            
            # Verificar no banco do dpb_bacalhau_ultimo_zip.py
            if zip_file.name in processed_by_dpb:
                is_processed = True
                reason = "processado por dpb_bacalhau_ultimo_zip.py"
            
            # Verificar no banco de anexos de email
            elif zip_file.name in processed_attachments:
                is_processed = True
                reason = "baixado e processado por email"
            
            if not is_processed:
                logger.info("Mantido: %s (ainda não processado)", zip_file.name)
                skipped_count += 1
                continue
            
            # Mover para pasta de registros
            destination = PROCESSED_FILES_FOLDER / zip_file.name
            
            # Se já existe, adicionar timestamp
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = destination.stem
                suffix = destination.suffix
                destination = PROCESSED_FILES_FOLDER / f"{stem}_{timestamp}{suffix}"
            
            zip_file.rename(destination)
            logger.info("✓ Movido: %s → Registros (%s)", zip_file.name, reason)
            moved_count += 1
            
        except Exception as e:
            logger.warning("Erro ao processar %s: %s", zip_file.name, e)
    
    logger.info("==== LIMPEZA CONCLUÍDA ====")
    logger.info("ZIPs movidos para Registros: %d | ZIPs mantidos: %d", moved_count, skipped_count)
    
    return 0


# =============================================================================
# EXECUÇÃO DO SCRIPT PRINCIPAL
# =============================================================================

def run_main_script(logger: logging.Logger) -> int:
    if not MAIN_DPB_SCRIPT.exists():
        logger.error("Script principal não encontrado: %s", MAIN_DPB_SCRIPT)
        return 2

    logger.info("Executando script principal: %s", MAIN_DPB_SCRIPT)

    cmd = [
        sys.executable,
        str(MAIN_DPB_SCRIPT),
    ]

    env = os.environ.copy()
    env["DPB_ZIP_FOLDER"] = str(ZIP_DESTINATION_FOLDER)

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(60, int(os.environ.get("DPB_SUBPROCESS_TIMEOUT_SECONDS", "900"))),
    )

    if result.stdout:
        logger.info("Saída do script principal:\n%s", result.stdout)

    if result.stderr:
        logger.warning("STDERR do script principal:\n%s", result.stderr)

    logger.info("Script principal finalizado com código: %s", result.returncode)

    return result.returncode


def cleanup_email_logs(logger: logging.Logger) -> int:
    """Move old email download logs to Registros Automacao Email folder.
    Excludes the current log file being used.
    Returns: count of files moved"""
    registros_folder = PROCESSED_FILES_FOLDER
    registros_folder.mkdir(parents=True, exist_ok=True)
    
    moved = 0
    pattern = "DPB_Email_Download_Log_*.txt"
    
    for file_path in ZIP_DESTINATION_FOLDER.glob(pattern):
        # Não mover o log atual
        if file_path == LOG_FILE:
            continue
        
        dest = registros_folder / file_path.name
        # Se já existe, adicionar timestamp
        if dest.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = file_path.stem
            suffix = file_path.suffix
            dest = registros_folder / f"{stem}_{timestamp}{suffix}"
        
        try:
            file_path.rename(dest)
            moved += 1
            logger.info("✓ Movido para Registros: %s", file_path.name)
        except Exception as exc:
            logger.error("Erro ao mover log %s: %s", file_path.name, exc)
    
    return moved


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    logger = setup_logger()

    logger.info("==== INÍCIO DPB EMAIL DOWNLOADER ====")

    try:
        downloaded = download_matching_attachments(logger)

        # Lista para rastrear todos os arquivos processados com sucesso
        all_processed_files = []
        
        dpb_script_result = 0

        if downloaded:
            logger.info("Arquivos ZIP novos baixados:")
            for file in downloaded:
                logger.info(" - %s", file)

            # Descompactar Daily Reports automaticamente
            if AUTO_EXTRACT_DAILY_REPORTS:
                extract_result, processed_daily = extract_daily_reports(downloaded, logger)
                all_processed_files.extend(processed_daily)
                if extract_result != 0:
                    logger.warning("Descompactação de Daily Reports concluída com erros.")

            # Descompactar FCVs Updated automaticamente
            if AUTO_EXTRACT_FCVS:
                extract_result, processed_fcvs = extract_fcvs_updated(downloaded, logger)
                all_processed_files.extend(processed_fcvs)
                if extract_result != 0:
                    logger.warning("Descompactação de FCVs Updated concluída com erros.")

            # Executar script principal de processamento antes de mover os ZIPs.
            # Assim o organizador ainda encontra os anexos na pasta Zip.
            if RUN_MAIN_DPB_SCRIPT:
                dpb_script_result = run_main_script(logger)

            # Mover arquivos processados para pasta de registros
            if AUTO_MOVE_PROCESSED and all_processed_files:
                move_result = move_processed_files(all_processed_files, logger)
                if move_result != 0:
                    logger.warning("Movimentação de arquivos concluída com erros.")
        else:
            logger.info("Nenhum ZIP novo baixado nesta execução.")

        # Sempre executar limpeza de ZIPs já processados (mesmo sem novos downloads)
        cleanup_all_processed_zips(logger)

        return dpb_script_result

    except Exception as exc:
        logger.exception("Falha geral na automação: %s", exc)
        return 1

    finally:
        # Limpar logs antigos antes de finalizar
        logger.info("==== LIMPEZA DE LOGS ANTIGOS ====")
        moved = cleanup_email_logs(logger)
        logger.info("Logs movidos para Registros: %d", moved)
        logger.info("==== FIM DPB EMAIL DOWNLOADER ====")


if __name__ == "__main__":
    raise SystemExit(main())
