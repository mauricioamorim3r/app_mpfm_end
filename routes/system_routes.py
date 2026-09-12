from __future__ import annotations

import calendar
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from routes.date_utils import normalize_date_input
from services.importing.sep_folder_scan_service import DEFAULT_FOLDER_NAMES, scan_sep_folder



def register_system_routes(app, ctx: dict) -> None:
    db_conn = ctx["db_conn"]
    process_file_list = ctx["process_file_list"]
    default_density = ctx["default_density"]
    upload_dir = ctx["upload_dir"]
    output_dir = ctx["output_dir"]
    static_dir = ctx["static_dir"]
    work_dir = ctx["work_dir"]
    app_title = ctx["app_title"]
    app_version = ctx["app_version"]
    public_base_url = ctx["public_base_url"]
    db_path = ctx["db_path"]
    is_monthly_workbook_rebuilding = ctx["is_monthly_workbook_rebuilding"]
    prefs_path = work_dir / "user_prefs.json"

    _B05_OLD_FOLDER = "3.1.4_18-FT-1506 PE 4 - Subsea B05"
    _B05_OFFICIAL_FOLDER = "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05"

    def _canonical_monitor_folder_path(folder_path: str) -> str:
        """Mantém PE-4A e PE-EO105 na única pasta oficial compartilhada."""
        return str(folder_path or "").strip().replace(_B05_OLD_FOLDER, _B05_OFFICIAL_FOLDER)

    def _monitor_folder_root_path(folder_path: str) -> str:
        path = Path(_canonical_monitor_folder_path(folder_path))
        parts = list(path.parts)
        if len(parts) >= 2 and re.match(r"^\d{2}\.", parts[-1] or "") and re.match(r"^\d{4}$", parts[-2] or ""):
            path = Path(*parts[:-2])
        parts = list(path.parts)
        for idx, part in enumerate(parts):
            if part.startswith("3. Registros de Opera") and idx + 1 < len(parts) and parts[idx + 1] == "3.1 Registros Diarios MPFM":
                candidate = Path(parts[0], *parts[1:idx], *parts[idx + 1:])
                if candidate.exists():
                    return str(candidate)
        return str(path)
    
    allowed_output_patterns = (
        re.compile(r"^MPFM_(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)_\d{4}\.xlsx$", re.IGNORECASE),
        re.compile(r"^SEP_Dados_\d{4}-\d{2}-\d{2}_a_\d{4}-\d{2}-\d{2}\.xlsx$", re.IGNORECASE),
        re.compile(r"^dados_producao_\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.xlsx$", re.IGNORECASE),
        re.compile(r"^mpfm_export_\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.xlsx$", re.IGNORECASE),
    )

    def _now_local_iso() -> str:
        return datetime.now().replace(microsecond=0).isoformat()

    def _is_supported_output_workbook(path: Path) -> bool:
        name = path.name
        if name.lower() == "mpfm.xlsx":
            return True
        return any(pattern.match(name) for pattern in allowed_output_patterns)

    def _resolve_safe(base: Path, name: str) -> Path:
        resolved = (base / name).resolve()
        if not resolved.is_relative_to(base.resolve()):
            raise HTTPException(400, "Caminho de arquivo inválido")
        return resolved

    def _loaded_operational_days(limit: int = 62) -> list[str]:
        conn = db_conn()
        try:
            rows = conn.execute(
                """
                SELECT day
                FROM (
                    SELECT DISTINCT substr(day_ref,1,10) AS day
                    FROM measurements_curated
                    WHERE day_ref NOT LIKE '0000%'
                      AND day_ref >= '1900-01-01'
                      AND row_kind IN ('daily','hourly','recon','sep')
                    UNION
                    SELECT DISTINCT substr(content_date,1,10) AS day
                    FROM files_imported
                    WHERE processed_ok=1
                      AND content_date NOT LIKE '0000%'
                      AND content_date >= '1900-01-01'
                )
                WHERE day GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                ORDER BY day DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def _discover_measurement_files(folder: str | Path) -> list[Path]:
        """Return PDF/TXT/ZIP candidates for production imports, skipping reserved app subfolders."""
        base = Path(folder).resolve()
        reserved_dirs = {"alarme", "alarmes", "alarm", "alarms"}
        all_files = []
        for ext in ("*.pdf", "*.txt", "*.zip"):
            all_files.extend(sorted(glob.glob(os.path.join(str(base), "**", ext), recursive=True)))
        candidates: list[Path] = []
        for path_str in all_files:
            path = Path(path_str)
            try:
                relative = path.resolve().relative_to(base)
            except ValueError:
                relative = path
            if any(part.lower() in reserved_dirs for part in relative.parts[:-1]):
                continue
            if path.suffix.lower() != ".zip" and not _is_measurement_filename(path.name):
                continue
            candidates.append(path)
        return candidates

    def _is_measurement_filename(filename: str) -> bool:
        name = Path(filename).name
        return bool(
            re.search(r"B\d{2}_MPFM_(Daily|Hourly)-\d{8}-\d{6}", name, re.IGNORECASE)
            or re.match(r"Run_24Hours[12]-1\.\d{14}", name, re.IGNORECASE)
        )

    def _zip_measurement_entries(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
        entries: list[zipfile.ZipInfo] = []
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            entry_name = Path(entry.filename).name
            if entry_name and Path(entry_name).suffix.lower() in {".pdf", ".txt"} and _is_measurement_filename(entry_name):
                entries.append(entry)
        return entries

    def _known_imported_filenames(filenames: set[str]) -> set[str]:
        names = {name for name in filenames if name}
        if not names:
            return set()
        conn = db_conn()
        cur = conn.cursor()
        known: set[str] = set()
        try:
            names_list = sorted(names)
            for offset in range(0, len(names_list), 900):
                chunk = names_list[offset : offset + 900]
                placeholders = ",".join("?" * len(chunk))
                known.update(
                    row[0]
                    for row in cur.execute(
                        f"SELECT DISTINCT filename FROM files_imported WHERE filename IN ({placeholders})",
                        chunk,
                    ).fetchall()
                    if row[0]
                )
                known.update(
                    row[0]
                    for row in cur.execute(
                        f"SELECT DISTINCT source_file FROM sep_source_files WHERE source_file IN ({placeholders})",
                        chunk,
                    ).fetchall()
                    if row[0]
                )
                known.update(
                    row[0]
                    for row in cur.execute(
                        f"SELECT DISTINCT filename FROM source_files_raw WHERE filename IN ({placeholders})",
                        chunk,
                    ).fetchall()
                    if row[0]
                )
        finally:
            conn.close()
        return known

    def _folder_duplicate_items(paths: list[Path]) -> tuple[list[dict], list[str]]:
        items: list[dict] = []
        log: list[str] = []
        for path in paths:
            if path.suffix.lower() != ".zip":
                items.append({"file_id": str(path), "filename": path.name, "file_hash": _file_sha1(path)})
                continue
            try:
                with zipfile.ZipFile(path) as archive:
                    entries = _zip_measurement_entries(archive)
                    for entry in entries:
                        entry_name = Path(entry.filename).name
                        items.append({"file_id": f"{path}::{entry.filename}", "filename": entry_name, "file_hash": ""})
                    log.append(f"📦 {path.name} → {len(entries)} PDF/TXT interno(s) localizado(s)")
            except zipfile.BadZipFile:
                log.append(f"⚠ {path.name} ignorado: ZIP inválido/corrompido")
            except OSError as exc:
                log.append(f"⚠ {path.name} ignorado: falha ao ler ZIP ({exc})")
        return items, log

    def _materialize_process_pairs(paths: list[Path], tmp_parent: Path, *, skip_known_zip_entries: bool = True) -> tuple[list[tuple[Path, str]], list[str]]:
        pairs: list[tuple[Path, str]] = []
        log: list[str] = []
        for path in paths:
            if path.suffix.lower() != ".zip":
                pairs.append((path, path.name))
                continue
            zip_tmp = Path(tempfile.mkdtemp(prefix=f"zip_{path.stem[:30]}_", dir=tmp_parent))
            extracted = 0
            skipped_known = 0
            try:
                with zipfile.ZipFile(path) as archive:
                    entries = _zip_measurement_entries(archive)
                    known_names = _known_imported_filenames({Path(entry.filename).name for entry in entries}) if skip_known_zip_entries else set()
                    for entry in entries:
                        entry_name = Path(entry.filename).name
                        if entry_name in known_names:
                            skipped_known += 1
                            continue
                        entry_parent = zip_tmp / hashlib.sha1(entry.filename.encode("utf-8", errors="ignore")).hexdigest()[:10]
                        entry_parent.mkdir(parents=True, exist_ok=True)
                        dest = entry_parent / entry_name
                        with archive.open(entry) as source, dest.open("wb") as target:
                            shutil.copyfileobj(source, target)
                        pairs.append((dest, entry_name))
                        extracted += 1
                detail = f"📦 {path.name} → {extracted} PDF/TXT extraído(s) para processamento"
                if skipped_known:
                    detail += f"; {skipped_known} já importado(s) ignorado(s) pelo nome rastreável"
                log.append(detail)
            except zipfile.BadZipFile:
                log.append(f"⚠ {path.name} ignorado: ZIP inválido/corrompido")
            except OSError as exc:
                log.append(f"⚠ {path.name} ignorado: falha ao extrair ZIP ({exc})")
        return pairs, log

    def _incremental_folder_candidates(paths: list[Path], *, scan_all: bool = False, max_files: int = 30) -> tuple[list[Path], str]:
        def _mtime(path: Path) -> float:
            try:
                return path.stat().st_mtime if path.exists() else 0.0
            except OSError:
                return 0.0

        ordered = sorted(paths, key=_mtime, reverse=True)
        if scan_all or len(ordered) <= max_files:
            return ordered, "histórico completo"
        loaded_days = _loaded_operational_days(1)
        cutoff_ts = None
        if loaded_days:
            try:
                latest_loaded = datetime.strptime(loaded_days[0], "%Y-%m-%d") - timedelta(days=3)
                cutoff_ts = latest_loaded.timestamp()
            except ValueError:
                cutoff_ts = None
        recent = [path for path in ordered if cutoff_ts is not None and _mtime(path) >= cutoff_ts]
        if len(recent) < min(max_files, len(ordered)):
            chosen = ordered[:max_files]
        else:
            chosen = recent
        return chosen, f"incremental recente ({len(chosen)} de {len(ordered)} arquivo(s); use scan_all=true para histórico completo)"

    def _sep_folder_scan_from_body(body: dict) -> tuple[Path, list, dict]:
        folder = str((body or {}).get("folder") or (body or {}).get("source_root") or "").strip()
        if not folder or not os.path.isdir(folder):
            raise HTTPException(400, f"Pasta não encontrada: {folder}")

        date_from = normalize_date_input(str((body or {}).get("date_from") or "").strip())
        date_to = normalize_date_input(str((body or {}).get("date_to") or "").strip())
        if date_from and not re.match(r"^\d{4}-\d{2}-\d{2}$", date_from):
            raise HTTPException(400, "Data inicial inválida. Use YYYY-MM-DD ou DD/MM/YYYY.")
        if date_to and not re.match(r"^\d{4}-\d{2}-\d{2}$", date_to):
            raise HTTPException(400, "Data final inválida. Use YYYY-MM-DD ou DD/MM/YYYY.")
        if date_from and date_to and date_from > date_to:
            raise HTTPException(400, "Data inicial maior que data final.")

        raw_folders = (body or {}).get("folder_names") or DEFAULT_FOLDER_NAMES
        if isinstance(raw_folders, str):
            raw_folders = [item.strip() for item in re.split(r"[,;]", raw_folders)]
        folder_names = [str(item).strip() for item in raw_folders if str(item).strip()] or list(DEFAULT_FOLDER_NAMES)
        include_incomplete = bool((body or {}).get("include_incomplete_days"))

        source_root = Path(folder).resolve()
        _candidates, selected, preview = scan_sep_folder(
            source_root,
            date_from=date_from,
            date_to=date_to,
            folder_names=folder_names,
            include_incomplete_days=include_incomplete,
        )
        return source_root, selected, preview

    def _download_readiness(path: Path) -> dict:
        rebuilding = bool(path.suffix.lower() == ".xlsx" and is_monthly_workbook_rebuilding(path))
        return {
            "is_rebuilding": rebuilding,
            "rebuild_message": "Workbook mensal em atualização assíncrona. Aguarde alguns segundos e atualize a tela." if rebuilding else "",
        }

    def _load_monitor_prefs() -> dict:
        base = {"enabled": False, "stability_seconds": 20, "schedule_enabled": False, "schedule_times": ["09:00", "12:00", "18:00"], "interval_enabled": True, "folders": []}
        if prefs_path.exists():
            try:
                payload = json.loads(prefs_path.read_text("utf-8"))
                current = payload.get("auto_folder_monitor") or {}
                if isinstance(current, dict):
                    base.update({k: current[k] for k in ("enabled", "stability_seconds", "schedule_enabled", "schedule_times", "interval_enabled") if k in current})
                    base["folders"] = current.get("folders") or []
            except Exception:
                pass
        base["enabled"] = bool(base.get("enabled"))
        base["schedule_enabled"] = bool(base.get("schedule_enabled"))
        base["interval_enabled"] = bool(base.get("interval_enabled", True))
        try:
            base["stability_seconds"] = max(5, min(300, int(base.get("stability_seconds") or 20)))
        except Exception:
            base["stability_seconds"] = 20
        raw_st = base.get("schedule_times") or []
        if isinstance(raw_st, str):
            raw_st = [t.strip() for t in raw_st.split(",")]
        valid_st = [t for t in raw_st if re.match(r"^\d{2}:\d{2}$", str(t).strip())]
        base["schedule_times"] = valid_st if valid_st else ["09:00", "12:00", "18:00"]
        folders = []
        for idx, item in enumerate(base.get("folders") or []):
            if not isinstance(item, dict):
                continue
            folder_path = _monitor_folder_root_path(item.get("path") or "")
            if not folder_path:
                continue
            duplicate_policy = str(item.get("duplicate_policy") or "skip").strip().lower()
            if duplicate_policy not in {"skip", "overwrite"}:
                duplicate_policy = "skip"
            try:
                interval_seconds = max(30, min(3600, int(item.get("interval_seconds") or 300)))
            except Exception:
                interval_seconds = 300
            folders.append(
                {
                    "id": str(item.get("id") or f"folder-{idx+1}"),
                    "label": str(item.get("label") or "").strip(),
                    "path": folder_path,
                    "active": item.get("active", True) is not False,
                    "interval_seconds": interval_seconds,
                    "duplicate_policy": duplicate_policy,
                }
            )
        base["folders"] = folders
        return base

    def _save_monitor_prefs(config: dict) -> dict:
        current = {}
        if prefs_path.exists():
            try:
                current = json.loads(prefs_path.read_text("utf-8"))
            except Exception:
                current = {}
        raw_st = (config or {}).get("schedule_times") or []
        if isinstance(raw_st, str):
            raw_st = [t.strip() for t in raw_st.split(",")]
        valid_st = [t for t in raw_st if re.match(r"^\d{2}:\d{2}$", str(t).strip())]
        sanitized = _load_monitor_prefs() | {
            "enabled": bool((config or {}).get("enabled")),
            "stability_seconds": max(5, min(300, int((config or {}).get("stability_seconds") or 20))),
            "schedule_enabled": bool((config or {}).get("schedule_enabled")),
            "schedule_times": valid_st if valid_st else ["09:00", "12:00", "18:00"],
            "interval_enabled": bool((config or {}).get("interval_enabled", True)),
            "folders": [],
        }
        for idx, item in enumerate((config or {}).get("folders") or []):
            if not isinstance(item, dict):
                continue
            folder_path = _monitor_folder_root_path(item.get("path") or "")
            if not folder_path:
                continue
            duplicate_policy = str(item.get("duplicate_policy") or "skip").strip().lower()
            if duplicate_policy not in {"skip", "overwrite"}:
                duplicate_policy = "skip"
            try:
                interval_seconds = max(30, min(3600, int(item.get("interval_seconds") or 300)))
            except Exception:
                interval_seconds = 300
            sanitized["folders"].append(
                {
                    "id": str(item.get("id") or f"folder-{idx+1}"),
                    "label": str(item.get("label") or "").strip(),
                    "path": folder_path,
                    "active": item.get("active", True) is not False,
                    "interval_seconds": interval_seconds,
                    "duplicate_policy": duplicate_policy,
                }
            )
        current["auto_folder_monitor"] = sanitized
        prefs_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), "utf-8")
        return sanitized

    monitor_state = {
        "lock": threading.Lock(),
        "wake_event": threading.Event(),
        "stop_event": threading.Event(),
        "thread": None,
        "schedule_triggered": set(),
        "status": {
            "running": False,
            "last_cycle_at": "",
            "last_cycle_message": "Monitor automático inativo.",
            "folders": {},
        },
    }

    def _file_sha1(path: Path) -> str:
        digest = hashlib.sha1()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _find_duplicates(payload_items: list[dict]) -> list[dict]:
        if not payload_items:
            return []
        conn = db_conn()
        cur = conn.cursor()
        results = []
        try:
            for item in payload_items:
                file_id = item.get("file_id") or item.get("filename") or ""
                fname = item.get("filename") or ""
                file_hash = (item.get("file_hash") or "").strip().lower()
                row = None
                mode = ""
                if file_hash:
                    row = cur.execute(
                        """SELECT filename, detected_type, content_date, created_at, meter_id, location
                           FROM source_files_raw WHERE file_hash=? ORDER BY id DESC LIMIT 1""",
                        (file_hash,),
                    ).fetchone()
                    mode = "same_content" if row else ""
                    if not row:
                        row = cur.execute(
                            """SELECT source_file AS filename, fluid_kind AS file_type, production_date AS content_date,
                                      updated_at AS created_at, meter_id, location
                               FROM sep_source_files WHERE source_hash=? ORDER BY id DESC LIMIT 1""",
                            (file_hash,),
                        ).fetchone()
                        mode = "same_content" if row else ""
                if not row and fname and not fname.lower().endswith(".txt"):
                    row = cur.execute(
                        """SELECT filename, file_type, content_date, created_at, meter_id, location
                           FROM files_imported WHERE filename=? ORDER BY id DESC LIMIT 1""",
                        (fname,),
                    ).fetchone()
                    mode = "same_name" if row else ""
                if not row and fname and fname.lower().endswith(".txt"):
                    row = cur.execute(
                        """SELECT source_file AS filename, fluid_kind AS file_type, production_date AS content_date,
                                  updated_at AS created_at, meter_id, location
                           FROM sep_source_files WHERE source_file=? ORDER BY id DESC LIMIT 1""",
                        (fname,),
                    ).fetchone()
                    mode = "same_name" if row else ""
                if row:
                    results.append(
                        {
                            "file_id": file_id,
                            "filename": fname,
                            "file_type": row[1] or "",
                            "content_date": row[2] or "",
                            "last_imported": (row[3] or "")[:16].replace("T", " "),
                            "meter_id": row[4] or "",
                            "location": row[5] or "",
                            "duplicate_mode": mode or "same_content",
                        }
                    )
        finally:
            conn.close()
        return results

    def _serialize_folder_status(folder_cfg: dict) -> dict:
        status = monitor_state["status"]["folders"].get(folder_cfg["id"], {})
        return {
            "id": folder_cfg["id"],
            "label": folder_cfg.get("label") or Path(folder_cfg["path"]).name,
            "path": folder_cfg["path"],
            "active": folder_cfg.get("active", True),
            "interval_seconds": folder_cfg.get("interval_seconds", 300),
            "duplicate_policy": folder_cfg.get("duplicate_policy", "skip"),
            "last_scan_at": status.get("last_scan_at", ""),
            "last_action_at": status.get("last_action_at", ""),
            "last_action_trigger": status.get("last_action_trigger", ""),
            "last_result": status.get("last_result", ""),
            "last_scan_result": status.get("last_scan_result", ""),
            "last_found": status.get("last_found", 0),
            "last_processed": status.get("last_processed", 0),
            "last_skipped": status.get("last_skipped", 0),
            "last_error": status.get("last_error", ""),
            "next_scan_at": status.get("next_scan_at_iso", ""),
        }

    def _update_folder_status_summary(
        entry: dict,
        trigger: str,
        processed: int,
        result_text: str,
        *,
        force_display: bool = False,
    ) -> None:
        entry["last_scan_result"] = result_text
        if force_display or trigger == "manual" or processed > 0 or not entry.get("last_action_at"):
            entry["last_result"] = result_text
            entry["last_action_at"] = entry.get("last_scan_at", "")
            entry["last_action_trigger"] = trigger

    def _stable_folder_files(folder: str, stability_seconds: int) -> list[Path]:
        now = time.time()
        stable = []
        for path in _discover_measurement_files(folder):
            try:
                if not path.is_file():
                    continue
                age = now - path.stat().st_mtime
                if age < stability_seconds:
                    continue
                stable.append(path)
            except OSError:
                continue
        return stable

    def _parse_mpfm_pdf_filename(path: Path) -> dict | None:
        match = re.search(r"(?P<bank>B\d{2})_MPFM_(?P<kind>Daily|Hourly)-(?P<date>\d{8})-(?P<time>\d{6})", path.name, re.IGNORECASE)
        if not match:
            return None
        kind = match.group("kind").lower()
        try:
            end_dt = datetime.strptime(f'{match.group("date")}{match.group("time")}', "%Y%m%d%H%M%S")
        except ValueError:
            return None
        if kind == "daily":
            production_day = (end_dt.date() - timedelta(days=1)).isoformat()
            hour = None
        else:
            start_dt = end_dt - timedelta(hours=1)
            production_day = start_dt.date().isoformat()
            hour = start_dt.hour
        return {
            "path": path,
            "name": path.name,
            "bank": match.group("bank").upper(),
            "report_type": kind,
            "production_day": production_day,
            "hour": hour,
        }

    def _active_mpfm_monitor_folders() -> list[dict]:
        return [folder for folder in monitor_prefs.get("folders", []) if folder.get("active", True)]

    def _candidate_existing_mpfm_roots(folder_path: str) -> list[Path]:
        raw = Path(_canonical_monitor_folder_path(folder_path))
        variants: list[Path] = []
        if str(raw):
            variants.append(raw)
            parts = list(raw.parts)
            for idx, part in enumerate(parts):
                if part == "3. Registros de Operação SGM Multifasico" and idx + 1 < len(parts) and parts[idx + 1] == "3.1 Registros Diarios MPFM":
                    try:
                        variants.append(Path(parts[0], *parts[1:idx], *parts[idx + 1:]))
                    except Exception:
                        pass
                    break

        roots: list[Path] = []
        seen: set[str] = set()
        for variant in variants:
            if not variant.exists() or not variant.is_dir():
                continue
            scan_roots = [variant]
            if re.match(r"^\d{2}\.", variant.name or "") and variant.parent.is_dir() and re.match(r"^\d{4}$", variant.parent.name or ""):
                scan_roots = [
                    item
                    for item in variant.parent.iterdir()
                    if item.is_dir() and re.match(r"^\d{2}\.", item.name or "")
                ] or [variant]
            else:
                year_dirs = [
                    item
                    for item in variant.iterdir()
                    if item.is_dir() and re.match(r"^\d{4}$", item.name or "")
                ]
                month_dirs = [
                    month_dir
                    for year_dir in year_dirs
                    for month_dir in year_dir.iterdir()
                    if month_dir.is_dir() and re.match(r"^\d{2}\.", month_dir.name or "")
                ]
                if month_dirs:
                    scan_roots = month_dirs
            for root in scan_roots:
                key = str(root.resolve()).casefold()
                if key in seen:
                    continue
                seen.add(key)
                roots.append(root.resolve())
        return sorted(roots, key=lambda item: str(item).casefold())

    def _discover_mpfm_pdf_files_fast(scan_root: Path) -> list[Path]:
        candidates: list[Path] = []
        if scan_root.name.lower() in {"daily", "hourly"}:
            candidates.extend(scan_root.glob("*.pdf"))
        else:
            seen_dirs: set[str] = set()
            for child_name in ("Daily", "DAILY", "daily", "Hourly", "HOURLY", "hourly"):
                child = scan_root / child_name
                dir_key = str(child).casefold()
                if dir_key in seen_dirs:
                    continue
                seen_dirs.add(dir_key)
                if child.is_dir():
                    candidates.extend(child.glob("*.pdf"))
            candidates.extend(scan_root.glob("*.pdf"))
        seen: set[str] = set()
        result: list[Path] = []
        for path in candidates:
            if not path.is_file():
                continue
            resolved = path.resolve()
            key = str(resolved).casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(resolved)
        return sorted(result, key=lambda item: item.name.casefold())

    _PT_MONTH_NAMES = {
        1: "01. Janeiro", 2: "02. Fevereiro", 3: "03. Março", 4: "04. Abril",
        5: "05. Maio", 6: "06. Junho", 7: "07. Julho", 8: "08. Agosto",
        9: "09. Setembro", 10: "10. Outubro", 11: "11. Novembro", 12: "12. Dezembro",
    }

    def _meter_root_from_monitor_path(folder_path: str) -> Path | None:
        """Strip the trailing \\{ano}\\{mês} segments from a configured monitor
        folder path, returning the meter's root folder (one level above the year)."""
        path = Path(_monitor_folder_root_path(folder_path))
        parts = list(path.parts)
        if len(parts) >= 2 and re.match(r"^\d{2}\.", parts[-1] or "") and re.match(r"^\d{4}$", parts[-2] or ""):
            return Path(*parts[:-2])
        if path.is_dir() and any(item.is_dir() and re.match(r"^\d{4}$", item.name or "") for item in path.iterdir()):
            return path
        return None

    def _scan_month_source_coverage(month: str) -> dict:
        """Compara, para todos os bancos MPFM configurados, os arquivos existentes
        em disco (pasta por pasta, subpasta por subpasta) com o que já está
        importado em measurements_curated para o mês pedido. Não escreve nada."""
        match = re.match(r"^(?P<year>\d{4})-(?P<mon>\d{2})$", str(month or "").strip())
        if not match:
            raise HTTPException(400, "Mês inválido. Use o formato YYYY-MM.")
        year = int(match.group("year"))
        mon = int(match.group("mon"))
        month_name = _PT_MONTH_NAMES.get(mon)
        if not month_name:
            raise HTTPException(400, "Mês inválido.")

        days_in_month = calendar.monthrange(year, mon)[1]
        month_start = f"{year:04d}-{mon:02d}-01"
        month_end = f"{year:04d}-{mon:02d}-{days_in_month:02d}"

        _t_scan0 = time.monotonic()
        print(f"[gap-scan] {month}: iniciando", flush=True)

        _t_sql0 = time.monotonic()
        conn = db_conn()
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT bank, day_ref, row_kind, hour_ref FROM measurements_curated "
            "WHERE row_kind IN ('daily','hourly') AND bank<>'' AND bank<>'SEP' "
            "AND day_ref BETWEEN ? AND ?",
            (month_start, month_end),
        ).fetchall()
        conn.close()
        print(f"[gap-scan] {month}: query SQL concluida em {time.monotonic()-_t_sql0:.2f}s ({len(rows)} linhas)", flush=True)

        db_daily: set[tuple[str, str]] = set()
        db_hours: dict[tuple[str, str], set[int]] = {}
        for bank, day_ref, row_kind, hour_ref in rows:
            if row_kind == "daily":
                db_daily.add((bank, day_ref))
            elif row_kind == "hourly" and hour_ref is not None:
                db_hours.setdefault((bank, day_ref), set()).add(int(hour_ref))

        today = datetime.now().date()
        last_day = min(days_in_month, today.day) if (today.year == year and today.month == mon) else days_in_month
        all_month_days = [f"{year:04d}-{mon:02d}-{day:02d}" for day in range(1, last_day + 1)]

        banks_out: list[dict] = []
        pending_files: list[dict] = []
        total_pending = 0
        total_source_gap = 0

        _t_folders0 = time.monotonic()
        monitor_folders = _active_mpfm_monitor_folders()
        print(f"[gap-scan] {month}: _active_mpfm_monitor_folders concluido em {time.monotonic()-_t_folders0:.2f}s ({len(monitor_folders)} pasta(s))", flush=True)

        for folder in monitor_folders:
            _t_bank0 = time.monotonic()
            folder_path = str(folder.get("path") or "").strip()
            label = folder.get("label") or Path(folder_path).name
            bank_match = re.search(r"\bB\d{2}\b", folder_path, re.IGNORECASE)
            expected_bank = bank_match.group(0).upper() if bank_match else ""
            bank_entry = {
                "bank": expected_bank,
                "label": label,
                "folder_path": folder_path,
                "scan_roots": [],
                "found_on_disk": False,
                "pending_count": 0,
                "source_gap_count": 0,
                "days": [],
                "error": "",
            }
            if not expected_bank:
                bank_entry["error"] = "Não foi possível identificar o código do banco (B##) na pasta configurada."
                banks_out.append(bank_entry)
                continue
            meter_root = _meter_root_from_monitor_path(folder_path)
            if meter_root is None:
                bank_entry["error"] = f"Estrutura de pasta inesperada (esperado .../{{ano}}/{{mês}}): {folder_path}"
                banks_out.append(bank_entry)
                continue

            synthetic_path = str(meter_root / f"{year:04d}" / month_name)
            _t_roots0 = time.monotonic()
            scan_roots = _candidate_existing_mpfm_roots(synthetic_path)
            print(f"[gap-scan] {month}: {expected_bank} _candidate_existing_mpfm_roots concluido em {time.monotonic()-_t_roots0:.2f}s ({len(scan_roots)} raiz(es))", flush=True)
            bank_entry["scan_roots"] = [str(item) for item in scan_roots]
            bank_entry["found_on_disk"] = bool(scan_roots)
            if not scan_roots:
                bank_entry["error"] = f"Pasta do mês não encontrada em disco: {synthetic_path}"

            disk_daily: dict[str, Path] = {}
            disk_hours: dict[str, dict[int, Path]] = {}
            files: list[Path] = []
            _t_files0 = time.monotonic()
            for scan_root in scan_roots:
                files.extend(_discover_mpfm_pdf_files_fast(scan_root))
            if not files and scan_roots:
                for scan_root in scan_roots:
                    files.extend(_discover_measurement_files(scan_root))
            print(f"[gap-scan] {month}: {expected_bank} descoberta de arquivos concluida em {time.monotonic()-_t_files0:.2f}s ({len(files)} arquivo(s))", flush=True)
            for path in files:
                meta = _parse_mpfm_pdf_filename(path)
                if not meta or meta["bank"] != expected_bank:
                    continue
                day = meta["production_day"]
                if not day.startswith(f"{year:04d}-{mon:02d}"):
                    continue
                if meta["report_type"] == "daily":
                    disk_daily[day] = meta["path"]
                elif meta.get("hour") is not None:
                    disk_hours.setdefault(day, {})[meta["hour"]] = meta["path"]

            day_reports = []
            bank_pending = 0
            bank_gap = 0
            for day in all_month_days:
                key = (expected_bank, day)
                missing_hours: list[int] = []
                pending_hours: list[dict] = []
                for hour in range(24):
                    if hour in db_hours.get(key, set()):
                        continue
                    disk_path = disk_hours.get(day, {}).get(hour)
                    if disk_path is not None:
                        pending_hours.append({"hour": hour, "path": str(disk_path)})
                        pending_files.append({"bank": expected_bank, "day": day, "hour": hour, "path": str(disk_path)})
                    else:
                        missing_hours.append(hour)
                daily_pending = False
                daily_missing = False
                if key not in db_daily:
                    disk_daily_path = disk_daily.get(day)
                    if disk_daily_path is not None:
                        daily_pending = True
                        pending_files.append({"bank": expected_bank, "day": day, "hour": "daily", "path": str(disk_daily_path)})
                    else:
                        daily_missing = True
                if missing_hours or pending_hours or daily_pending or daily_missing:
                    day_reports.append(
                        {
                            "day": day,
                            "missing_hours": missing_hours,
                            "pending_hours": pending_hours,
                            "daily_missing": daily_missing,
                            "daily_pending": daily_pending,
                        }
                    )
                bank_pending += len(pending_hours) + (1 if daily_pending else 0)
                bank_gap += len(missing_hours) + (1 if daily_missing else 0)

            bank_entry["pending_count"] = bank_pending
            bank_entry["source_gap_count"] = bank_gap
            bank_entry["days"] = day_reports
            total_pending += bank_pending
            total_source_gap += bank_gap
            banks_out.append(bank_entry)
            print(f"[gap-scan] {month}: {expected_bank} banco finalizado em {time.monotonic()-_t_bank0:.2f}s (total acumulado {time.monotonic()-_t_scan0:.2f}s)", flush=True)

        print(f"[gap-scan] {month}: FINALIZADO em {time.monotonic()-_t_scan0:.2f}s", flush=True)
        return {
            "ok": True,
            "month": f"{year:04d}-{mon:02d}",
            "days_scanned": len(all_month_days),
            "banks": banks_out,
            "pending_files": pending_files,
            "summary": {
                "total_pending": total_pending,
                "total_source_gap": total_source_gap,
                "banks_scanned": len(banks_out),
            },
        }

    def _scan_latest_day_ingestion(body: dict | None = None) -> dict:
        body = body or {}
        requested_day = normalize_date_input(str(body.get("target_day") or body.get("production_day") or "").strip())
        try:
            days_count = max(1, min(31, int(body.get("days_count") or body.get("last_days") or 1)))
        except Exception:
            days_count = 1
        if requested_day and not re.match(r"^\d{4}-\d{2}-\d{2}$", requested_day):
            raise HTTPException(400, "Data de produção inválida. Use YYYY-MM-DD ou DD/MM/YYYY.")
        configured_folders = _active_mpfm_monitor_folders()
        folder_candidates: list[dict] = []
        folder_summaries: list[dict] = []

        for folder in configured_folders:
            folder_path = str(folder.get("path") or "").strip()
            label = folder.get("label") or Path(folder_path).name
            summary = {
                "folder_id": folder.get("id") or "",
                "label": label,
                "path": folder_path,
                "exists": False,
                "scan_roots": [],
                "daily_found": 0,
                "hourly_found": 0,
                "selected": 0,
                "missing": [],
                "error": "",
            }
            scan_roots = _candidate_existing_mpfm_roots(folder_path)
            summary["exists"] = bool(scan_roots)
            summary["scan_roots"] = [str(path) for path in scan_roots]
            if not scan_roots:
                summary["error"] = f"Pasta não encontrada: {folder_path}"
                folder_summaries.append(summary)
                continue
            try:
                files = []
                for scan_root in scan_roots:
                    files.extend(_discover_mpfm_pdf_files_fast(scan_root))
            except Exception as exc:
                summary["error"] = str(exc)
                folder_summaries.append(summary)
                continue
            for path in files:
                meta = _parse_mpfm_pdf_filename(path)
                if not meta:
                    continue
                meta["folder_id"] = summary["folder_id"]
                meta["folder_label"] = label
                folder_candidates.append(meta)
            folder_summaries.append(summary)

        loaded_days = _loaded_operational_days(max(62, days_count * 2))
        loaded_day_set = set(loaded_days)
        available_days = sorted(
            {item["production_day"] for item in folder_candidates} | loaded_day_set,
            reverse=True,
        )
        if requested_day:
            end_day = datetime.strptime(requested_day, "%Y-%m-%d").date()
            start_day = end_day - timedelta(days=days_count - 1)
            target_days = [(start_day + timedelta(days=offset)).isoformat() for offset in range(days_count)]
        else:
            target_days = available_days[:days_count]
        target_day = target_days[0] if target_days else ""
        target_day_set = set(target_days)
        selected_mpfm = [item for item in folder_candidates if item["production_day"] in target_day_set] if target_days else []
        selected_paths = {str(item["path"].resolve()) for item in selected_mpfm}

        by_folder_type: dict[tuple[str, str], int] = {}
        by_folder_day_type: dict[tuple[str, str, str], int] = {}
        for item in selected_mpfm:
            key = (item.get("folder_id") or "", item["report_type"])
            by_folder_type[key] = by_folder_type.get(key, 0) + 1
            day_key = (item.get("folder_id") or "", item["production_day"], item["report_type"])
            by_folder_day_type[day_key] = by_folder_day_type.get(day_key, 0) + 1
        for summary in folder_summaries:
            summary["daily_found"] = by_folder_type.get((summary["folder_id"], "daily"), 0)
            summary["hourly_found"] = by_folder_type.get((summary["folder_id"], "hourly"), 0)
            summary["selected"] = summary["daily_found"] + summary["hourly_found"]
            if summary["exists"] and target_days:
                for day in sorted(target_days):
                    day_daily = by_folder_day_type.get((summary["folder_id"], day, "daily"), 0)
                    day_hourly = by_folder_day_type.get((summary["folder_id"], day, "hourly"), 0)
                    if day_daily < 1:
                        summary["missing"].append(f"{day} daily")
                    elif day_daily > 1:
                        summary["missing"].append(f"{day} daily {day_daily}/1 excesso/duplicado")
                    if day_hourly < 24:
                        summary["missing"].append(f"{day} hourly {day_hourly}/24")
                    elif day_hourly > 24:
                        summary["missing"].append(f"{day} hourly {day_hourly}/24 excesso/duplicado")

        sep_root_raw = str(body.get("sep_root") or body.get("sep_folder") or "").strip()
        raw_folders = body.get("sep_folder_names") or body.get("folder_names") or DEFAULT_FOLDER_NAMES
        if isinstance(raw_folders, str):
            raw_folders = [item.strip() for item in re.split(r"[,;]", raw_folders)]
        sep_selected = []
        sep_preview = {
            "enabled": bool(sep_root_raw),
            "source_root": sep_root_raw,
            "selected_count": 0,
            "candidate_count": 0,
            "complete": False,
            "message": "Pasta SEP não informada; a rotina seguirá apenas com PDFs MPFM.",
        }
        if sep_root_raw:
            if not os.path.isdir(sep_root_raw):
                sep_preview["message"] = f"Pasta SEP não encontrada: {sep_root_raw}"
            elif target_days:
                try:
                    sep_date_from = min(target_days)
                    sep_date_to = max(target_days)
                    _sep_candidates, sep_selected, raw_preview = scan_sep_folder(
                        Path(sep_root_raw),
                        date_from=sep_date_from,
                        date_to=sep_date_to,
                        folder_names=raw_folders,
                        include_incomplete_days=True,
                    )
                    sep_selected = [item for item in sep_selected if item.content_date in target_day_set]
                    stats = raw_preview.get("stats") or {}
                    day_rows = raw_preview.get("days") or []
                    complete_days = {row.get("date") for row in day_rows if row.get("is_complete")}
                    sep_preview = {
                        **raw_preview,
                        "enabled": True,
                        "selected_count": len(sep_selected),
                        "candidate_count": int(stats.get("candidate_count") or 0),
                        "complete": all(day in complete_days for day in target_days),
                        "message": f"{len(sep_selected)} TXT(s) SEP elegível(is) para {sep_date_from} a {sep_date_to}.",
                    }
                except Exception as exc:
                    sep_preview["message"] = f"Falha na varredura SEP: {exc}"

        items = []
        for item in sorted(selected_mpfm, key=lambda row: (row["folder_label"], row["report_type"], row.get("hour") if row.get("hour") is not None else -1, row["name"])):
            items.append(
                {
                    "file_id": str(item["path"].resolve()),
                    "filename": item["name"],
                    "path": str(item["path"].resolve()),
                    "kind": f"mpfm_{item['report_type']}",
                    "bank": item.get("bank") or "",
                    "folder_label": item.get("folder_label") or "",
                    "production_day": item["production_day"],
                    "hour": item.get("hour"),
                    "file_hash": "",
                }
            )
        for item in sep_selected:
            path_key = str(item.path.resolve())
            if path_key in selected_paths:
                continue
            items.append(
                {
                    "file_id": path_key,
                    "filename": item.name,
                    "path": path_key,
                    "kind": item.fluid_kind,
                    "bank": "SEP",
                    "folder_label": item.folder_name,
                    "production_day": item.content_date,
                    "hour": None,
                    "file_hash": "",
                }
            )

        duplicates = _find_duplicates(items)
        loaded_selected_days = sorted(target_day_set & loaded_day_set)
        return {
            "ok": True,
            "requested_day": requested_day,
            "target_day": target_day,
            "target_days": target_days,
            "days_count": len(target_days) or days_count,
            "has_eligible": bool(items),
            "has_loaded_data": bool(loaded_selected_days),
            "loaded_days": loaded_selected_days,
            "mpfm_count": len(selected_mpfm),
            "sep_count": len(sep_selected),
            "files_count": len(items),
            "duplicates_count": len(duplicates),
            "folders": folder_summaries,
            "sep": sep_preview,
            "items": items,
            "duplicates": duplicates,
            "message": (
                f"Sim: {len(items)} arquivo(s) elegível(is) encontrados para {target_days[0] if len(target_days) == 1 else f'{min(target_days)} a {max(target_days)}'}."
                if items
                else (
                    f"Dados já salvos no banco para {loaded_selected_days[0] if len(loaded_selected_days) == 1 else f'{min(loaded_selected_days)} a {max(loaded_selected_days)}'}; nenhum PDF/TXT novo elegível foi encontrado para reprocessar."
                    if loaded_selected_days
                    else f"Não: nenhum arquivo elegível encontrado para {target_day or 'o último dia'}."
                )
            )
        }

    def _process_latest_day_ingestion(body: dict | None = None) -> dict:
        body = body or {}
        preview = _scan_latest_day_ingestion(body)
        if not preview.get("items"):
            loaded_days = preview.get("loaded_days") or []
            log = [
                f"Último dia vigente: {preview.get('target_day') or (loaded_days[0] if loaded_days else '')}",
                preview.get("message") or "Nenhum arquivo elegível.",
            ]
            return {
                **preview,
                "processed": 0,
                "skipped": 0,
                "log": log,
                "last_date": preview.get("target_day") or (loaded_days[0] if loaded_days else ""),
            }
        overwrite_map = body.get("overwrite_map") or {}
        pairs = []
        skipped_log = []
        for item in preview.get("items") or []:
            path = item.get("path") or ""
            filename = item.get("filename") or Path(path).name
            decision = overwrite_map.get(path) or overwrite_map.get(filename) or overwrite_map.get(item.get("file_id") or "")
            if decision == "skip":
                skipped_log.append(f"⏭️  {filename}  →  ignorado por decisão do usuário")
                continue
            pairs.append((Path(path), filename))
        if not pairs:
            return {**preview, "processed": 0, "skipped": len(skipped_log), "log": skipped_log + ["⚠ Nenhum arquivo para processar (todos ignorados)."]}
        force_overwrite = bool(body.get("force_overwrite") or any(value == "overwrite" for value in overwrite_map.values()))
        result = process_file_list(
            pairs,
            default_density,
            source_type="latest-day",
            source_ref=f"latest-day:{','.join(preview.get('target_days') or [preview.get('target_day') or ''])}",
            force_overwrite=force_overwrite,
        )
        result["log"] = skipped_log + result.get("log", [])
        conn = db_conn()
        cur = conn.cursor()
        last_date = cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""
        conn.close()
        return {**preview, **result, "ok": True, "processed": len(pairs), "skipped": len(skipped_log), "last_date": last_date}

    def _run_monitored_folder(folder_cfg: dict, trigger: str = "interval") -> dict:
        with monitor_state["lock"]:
            entry = monitor_state["status"]["folders"].setdefault(folder_cfg["id"], {})
            entry["last_scan_at"] = _now_local_iso()
            entry["last_error"] = ""
            entry["trigger"] = trigger
            if not folder_cfg.get("active", True) and trigger != "manual":
                _update_folder_status_summary(entry, trigger, 0, "Pasta desativada.", force_display=True)
                return {"ok": True, "processed": 0, "skipped": 0, "found": 0, "log": ["Pasta desativada."]}
            folder = (folder_cfg.get("path") or "").strip()
            if not folder or not os.path.isdir(folder):
                entry["last_error"] = f"Pasta não encontrada: {folder}"
                _update_folder_status_summary(entry, trigger, 0, entry["last_error"], force_display=True)
                return {"ok": False, "processed": 0, "skipped": 0, "found": 0, "log": [entry["last_error"]]}
            stable_files_all = _stable_folder_files(folder, monitor_prefs["stability_seconds"])
            stable_files, scan_scope = _incremental_folder_candidates(stable_files_all, scan_all=False)
            tmp = Path(tempfile.mkdtemp(prefix="monitor_zip_", dir=upload_dir))
            materialized_pairs, zip_log = _materialize_process_pairs(stable_files, tmp, skip_known_zip_entries=True)
            items = [{"file_id": str(path), "filename": filename, "file_hash": _file_sha1(path)} for path, filename in materialized_pairs]
            duplicates = {dup["file_id"]: dup for dup in _find_duplicates(items)}
            pairs = []
            skipped_log = []
            skipped = 0
            for path, filename in materialized_pairs:
                duplicate = duplicates.get(str(path))
                if duplicate and duplicate.get("duplicate_mode") == "same_content":
                    skipped += 1
                    skipped_log.append(f"⏭️  {filename}  →  ignorado (mesmo conteúdo já importado)")
                    continue
                if duplicate and folder_cfg.get("duplicate_policy") == "skip":
                    skipped += 1
                    skipped_log.append(f"⏭️  {filename}  →  ignorado (mesmo nome já importado)")
                    continue
                pairs.append((path, filename))
            if not pairs:
                entry["last_found"] = len(stable_files_all)
                entry["last_processed"] = 0
                entry["last_skipped"] = skipped
                _update_folder_status_summary(entry, trigger, 0, "Nenhum arquivo novo elegível.")
                try:
                    shutil.rmtree(tmp)
                except Exception:
                    pass
                return {"ok": True, "processed": 0, "skipped": skipped, "found": len(stable_files_all), "log": [f"Escopo: {scan_scope}"] + zip_log + skipped_log + ["⚠ Nenhum arquivo novo elegível."]}
            try:
                result = process_file_list(pairs, default_density, source_type="auto-folder", source_ref=folder)
                entry["last_found"] = len(stable_files_all)
                entry["last_processed"] = len(pairs)
                entry["last_skipped"] = skipped
                _update_folder_status_summary(
                    entry,
                    trigger,
                    len(pairs),
                    f"{len(pairs)} arquivo(s) processado(s), {skipped} ignorado(s)",
                )
                return {
                    "ok": True,
                    "processed": len(pairs),
                    "skipped": skipped,
                    "found": len(stable_files_all),
                    "log": [f"Escopo: {scan_scope}"] + zip_log + skipped_log + result.get("log", []),
                }
            finally:
                try:
                    shutil.rmtree(tmp)
                except Exception:
                    pass

    monitor_prefs = _load_monitor_prefs()

    def _refresh_monitor_next_scan(force_folder_id: str | None = None) -> None:
        now = time.time()
        folders = {folder["id"]: folder for folder in monitor_prefs.get("folders", [])}
        for folder_id, status in list(monitor_state["status"]["folders"].items()):
            if folder_id not in folders:
                monitor_state["status"]["folders"].pop(folder_id, None)
        # Stagger initial scan times: daily=300s, hourly=600s between each folder
        accumulated_stagger = 0
        for idx, folder in enumerate(monitor_prefs.get("folders", [])):
            status = monitor_state["status"]["folders"].setdefault(folder["id"], {})
            if folder.get("active", True) is False and not (force_folder_id and folder["id"] == force_folder_id):
                status.pop("next_scan_ts", None)
                status["next_scan_at_iso"] = ""
                continue
            if force_folder_id and folder["id"] == force_folder_id:
                status["next_scan_ts"] = now
            elif "next_scan_ts" not in status:
                status["next_scan_ts"] = now + accumulated_stagger
            _stagger = 600 if int(folder.get("interval_seconds") or 300) >= 600 else 300
            accumulated_stagger += _stagger
            status["next_scan_at_iso"] = datetime.fromtimestamp(status["next_scan_ts"]).isoformat()

    def _monitor_snapshot() -> dict:
        _refresh_monitor_next_scan()
        return {
            "config": monitor_prefs,
            "runtime": {
                "running": monitor_state["status"]["running"],
                "last_cycle_at": monitor_state["status"]["last_cycle_at"],
                "last_cycle_message": monitor_state["status"]["last_cycle_message"],
                "folders": [_serialize_folder_status(folder) for folder in monitor_prefs.get("folders", [])],
            },
        }

    def _monitor_loop() -> None:
        while not monitor_state["stop_event"].is_set():
            if not monitor_prefs.get("enabled"):
                monitor_state["status"]["running"] = False
                monitor_state["status"]["last_cycle_message"] = "Monitor automático desativado."
                monitor_state["wake_event"].wait(timeout=5)
                monitor_state["wake_event"].clear()
                continue
            monitor_state["status"]["running"] = True
            cycle_messages = []
            now = time.time()
            now_dt = datetime.now()
            today_str = now_dt.strftime("%Y-%m-%d")
            current_hhmm = now_dt.strftime("%H:%M")
            active_folders = [folder for folder in monitor_prefs.get("folders", []) if folder.get("active", True)]

            # ── Scheduled time triggers (09:00, 12:00, 18:00, etc.) ──────────
            if monitor_prefs.get("schedule_enabled"):
                triggered = monitor_state["schedule_triggered"]
                for stime in (monitor_prefs.get("schedule_times") or []):
                    key = f"{today_str}|{stime}"
                    if current_hhmm == stime and key not in triggered:
                        triggered.add(key)
                        # Run folders strictly sequentially: finish one, wait 5 min, then start the next.
                        # Never run more than one folder at the same time.
                        _SCHED_GAP_S = 300  # 5 minutes between consecutive folders
                        for seq_idx, folder in enumerate(active_folders):
                            try:
                                result = _run_monitored_folder(folder, trigger=f"agendado-{stime}")
                                fstatus = monitor_state["status"]["folders"].setdefault(folder["id"], {})
                                cycle_messages.append(
                                    f"[{stime}] {folder.get('label') or Path(folder['path']).name}: "
                                    f"{result['processed']} processado(s), {result['skipped']} ignorado(s)"
                                )
                            except Exception as exc:
                                fstatus = monitor_state["status"]["folders"].setdefault(folder["id"], {})
                                fstatus["last_error"] = str(exc)
                                cycle_messages.append(f"[{stime}] {folder.get('label') or Path(folder['path']).name}: erro")
                            # Wait 5 min between folders; no gap after the last one
                            if seq_idx < len(active_folders) - 1:
                                time.sleep(_SCHED_GAP_S)
                # Remove keys from previous days to keep the set small
                monitor_state["schedule_triggered"] = {k for k in triggered if k.startswith(today_str)}

            # ── Interval-based triggers ───────────────────────────────────────
            if monitor_prefs.get("interval_enabled", True):
                for folder in active_folders:
                    status = monitor_state["status"]["folders"].setdefault(folder["id"], {})
                    next_scan_ts = status.get("next_scan_ts", now)
                    if next_scan_ts > now:
                        continue
                    try:
                        result = _run_monitored_folder(folder, trigger="interval")
                        cycle_messages.append(f"{folder.get('label') or Path(folder['path']).name}: {result['processed']} processado(s), {result['skipped']} ignorado(s)")
                    except Exception as exc:
                        status["last_error"] = str(exc)
                        status["last_result"] = f"Erro: {exc}"
                        cycle_messages.append(f"{folder.get('label') or Path(folder['path']).name}: erro")
                    status["next_scan_ts"] = time.time() + max(30, int(folder.get("interval_seconds") or 300))
                    status["next_scan_at_iso"] = datetime.fromtimestamp(status["next_scan_ts"]).isoformat()
            monitor_state["status"]["last_cycle_at"] = _now_local_iso()
            if cycle_messages:
                monitor_state["status"]["last_cycle_message"] = " | ".join(cycle_messages)
            elif not monitor_prefs.get("folders"):
                monitor_state["status"]["last_cycle_message"] = "Nenhuma pasta monitorada configurada."
            elif not active_folders:
                monitor_state["status"]["last_cycle_message"] = "Nenhuma pasta ativa no monitor automático."
            elif not monitor_prefs.get("schedule_enabled") and not monitor_prefs.get("interval_enabled", True):
                monitor_state["status"]["last_cycle_message"] = "Monitor ligado, mas sem agenda nem intervalo habilitados."
            monitor_state["wake_event"].wait(timeout=5)
            monitor_state["wake_event"].clear()

    def _start_monitor_thread() -> None:
        if monitor_state["thread"] and monitor_state["thread"].is_alive():
            return
        monitor_state["stop_event"].clear()
        _refresh_monitor_next_scan()
        thread = threading.Thread(target=_monitor_loop, name="auto-folder-monitor", daemon=True)
        monitor_state["thread"] = thread
        thread.start()

    def _stop_monitor_thread() -> None:
        monitor_state["stop_event"].set()
        monitor_state["wake_event"].set()

    @app.on_event("startup")
    async def on_startup():
        _start_monitor_thread()

    @app.on_event("shutdown")
    async def on_shutdown():
        _stop_monitor_thread()

    @app.get("/static/{filename:path}")
    def api_static(filename: str):
        path = _resolve_safe(static_dir, filename)
        if not path.exists():
            raise HTTPException(404, "Arquivo estático não encontrado")
        media_type = "application/javascript" if str(path).endswith(".js") else None
        return FileResponse(str(path), media_type=media_type, headers={"Cache-Control": "no-cache, must-revalidate"})

    @app.get("/twin/{filename:path}")
    def api_twin_static(filename: str):
        twin_dir = Path(__file__).resolve().parent.parent / "twin"
        path = _resolve_safe(twin_dir, filename or "index.html")
        if not path.exists() or not path.is_file():
            raise HTTPException(404, "Arquivo twin não encontrado")
        if path.suffix.lower() == ".html":
            return HTMLResponse(path.read_text("utf-8"))
        return FileResponse(str(path))

    @app.get("/", response_class=HTMLResponse)
    def root():
        idx = Path(__file__).resolve().parent.parent / "index.html"
        return HTMLResponse(idx.read_text("utf-8") if idx.exists() else "<h1>index.html não encontrado</h1>")

    @app.post("/api/admin/repair-banks")
    def api_repair_banks():
        instrument_to_bank = {
            '18FT0506': 'B10', '18FT0306': 'B10', '18FT0106': 'B10',
            '18FT1506': 'B05', '18FT1406': 'B05', '18FT1706': 'B05', '18FT1806': 'B05',
            '18FT0706': 'B15', '18FT0906': 'B15', '18FT1206': 'B15', '18FT1106': 'B15',
            '13FT0167': 'B08', '13FT0217': 'B08',
            '13FT0267': 'B13', '13FT0317': 'B13',
            '13FT0367': 'B03', '13FT0417': 'B03',
            '20FT0244': 'SEP', '20FT0247': 'SEP', '20FT0251': 'SEP'
        }
        tag_to_bank = {
            'PE_2': 'B10', 'PE_8': 'B10', 'PE_9': 'B10',
            'PE_4': 'B05', 'PE_EO10': 'B05', 'PE_EO105': 'B05', 'PE_EO4': 'B05',
            'PE_1': 'B15', 'PI_1': 'B15', 'PI_2': 'B15', 'PW-104DA': 'B15',
            'Riser_P1': 'B08', 'Riser_P2': 'B08',
            'Riser_P3': 'B13', 'Riser_P4': 'B13',
            'Riser_P5': 'B03', 'Riser_P6': 'B03',
        }
        well_to_bank = {
            'PE_2': 'B10', '7-BAC-1-SPS': 'B10',
            'PE_4': 'B05', '7-BAC-5A-SPS': 'B05', 'PE-4A': 'B05',
            'PW-104DA': 'B15', '7-BAC-4D-SPS': 'B15',
        }
        conn = db_conn()
        cur = conn.cursor()
        
        # 1. repair measurements_curated
        bad_banks = ['B12799', 'B145', 'B15153', 'B17525', 'B19109', 'B47', 'B52', 'UNK']
        placeholders = ','.join('?' for _ in bad_banks)
        cur.execute(f"""
            SELECT id, bank, tag, instrument 
            FROM measurements_curated 
            WHERE bank IN ({placeholders}) 
               OR (bank = 'B08' AND (instrument IN ('18FT0506','18FT0306','18FT0106') OR tag IN ('PE_2','PE_8','PE_9')))
        """, bad_banks)
        rows = cur.fetchall()
        
        updates_by_id = []
        for row_id, current_bank, tag, inst in rows:
            correct_bank = instrument_to_bank.get(inst) or tag_to_bank.get(tag)
            if correct_bank and correct_bank != current_bank:
                updates_by_id.append((correct_bank, row_id))
                
        if updates_by_id:
            cur.executemany("UPDATE measurements_curated SET bank = ? WHERE id = ?", updates_by_id)
            
        # 2. repair files_imported
        cur.execute("""
            SELECT DISTINCT f.id, f.filename, f.unit_code, m.bank
            FROM files_imported f
            JOIN measurements_curated m ON f.run_id = m.run_id
            WHERE f.unit_code != m.bank AND m.bank IN ('B03','B05','B08','B10','B13','B15','SEP')
        """)
        file_fixes = cur.fetchall()
        for file_id, filename, old_unit, new_unit in file_fixes:
            cur.execute("UPDATE files_imported SET unit_code = ? WHERE id = ?", (new_unit, file_id))

        # 3. repair source_files_raw
        cur.execute("""
            SELECT DISTINCT s.id, s.filename, s.unit_code, m.bank
            FROM source_files_raw s
            JOIN measurements_curated m ON s.run_id = m.run_id
            WHERE s.unit_code != m.bank AND m.bank IN ('B03','B05','B08','B10','B13','B15','SEP')
        """)
        raw_fixes = cur.fetchall()
        for raw_id, filename, old_unit, new_unit in raw_fixes:
            cur.execute("UPDATE source_files_raw SET unit_code = ? WHERE id = ?", (new_unit, raw_id))

        # 4. repair xml042 tables
        for well, correct_bank in well_to_bank.items():
            cur.execute("""
                UPDATE xml042_documents
                SET bank = ?
                WHERE (well_operator_name = ? OR cod_cadastro_poco = ?) AND bank != ?
            """, (correct_bank, well, well, correct_bank))

            cur.execute("""
                UPDATE xml042_imported_files
                SET bank = ?
                WHERE (well_operator_name = ? OR subsea_tag = ?) AND bank != ?
            """, (correct_bank, well, well, correct_bank))

            cur.execute("""
                UPDATE xml042_imported_rows
                SET bank = ?
                WHERE (well_operator_name = ? OR subsea_tag = ?) AND bank != ?
            """, (correct_bank, well, well, correct_bank))

        conn.commit()
        conn.close()
        return {"status": "ok", "updated_measurements": len(updates_by_id), "file_fixes": len(file_fixes), "raw_fixes": len(raw_fixes)}

    @app.get("/api/health")
    def api_health():
        conn = db_conn()
        try:
            cur = conn.cursor()
            latest_day = cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""
            counts = {
                "processing_runs": cur.execute("SELECT COUNT(*) FROM processing_runs").fetchone()[0],
                "source_files_raw": cur.execute("SELECT COUNT(*) FROM source_files_raw").fetchone()[0],
                "measurements_curated": cur.execute("SELECT COUNT(*) FROM measurements_curated").fetchone()[0],
                "validation_issues": cur.execute("SELECT COUNT(*) FROM validation_issues").fetchone()[0],
            }
            status = "ok"
            detail = ""
        except sqlite3.Error as exc:
            # Keep the health endpoint usable even before the local DB schema exists.
            latest_day = ""
            counts = {
                "processing_runs": 0,
                "source_files_raw": 0,
                "measurements_curated": 0,
                "validation_issues": 0,
            }
            status = "degraded"
            detail = str(exc)
        finally:
            conn.close()
        return {
            "status": status,
            "app": app_title,
            "version": app_version,
            "public_base_url": public_base_url,
            "db_path": str(db_path),
            "work_dir": str(work_dir),
            "latest_day_ref": latest_day,
            "counts": counts,
            "detail": detail,
        }

    @app.post("/api/check-duplicates")
    async def api_check_duplicates(request: Request):
        import asyncio
        body = await request.json()
        items = body.get("items", [])
        filenames = body.get("filenames", [])
        if not items and not filenames:
            return {"duplicates": []}
        payload_items = items or [{"file_id": fname, "filename": fname, "file_hash": ""} for fname in filenames]
        duplicates = await asyncio.to_thread(_find_duplicates, payload_items)
        return {"duplicates": duplicates}

    @app.get("/api/browse-folder")
    def api_browse_folder():
        """Opens a native OS folder picker dialog (tkinter) and returns the selected path."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory(title="Selecionar pasta para monitorar", parent=root)
            root.destroy()
            if selected:
                return {"ok": True, "path": str(Path(selected))}
            return {"ok": False, "path": ""}
        except Exception as exc:
            raise HTTPException(500, f"Não foi possível abrir o seletor de pasta: {exc}")

    @app.post("/api/check-folder-duplicates")
    def api_check_folder_duplicates(body: dict):
        folder = (body.get("folder") or "").strip()
        if not folder or not os.path.isdir(folder):
            raise HTTPException(400, f"Pasta não encontrada: {folder}")
        all_files = _discover_measurement_files(folder)
        if not all_files:
            return {"duplicates": [], "items": []}
        scoped_files, scan_scope = _incremental_folder_candidates(all_files, scan_all=bool((body or {}).get("scan_all")))
        items, zip_log = _folder_duplicate_items(scoped_files)
        return {
            "items": items,
            "duplicates": _find_duplicates(items),
            "log": [f"Escopo: {scan_scope}"] + zip_log,
            "found": len(all_files),
            "scanned": len(scoped_files),
        }

    @app.post("/api/process-files")
    async def api_process_files(request: Request):
        form = await request.form()
        files = form.getlist("files")
        file_manifest_raw = form.get("file_manifest", None)
        file_manifest = json.loads(file_manifest_raw) if file_manifest_raw else []
        overwrite_map_raw = form.get("overwrite_map", None)
        overwrite_map = json.loads(overwrite_map_raw) if overwrite_map_raw else None

        tmp = Path(tempfile.mkdtemp(dir=upload_dir))
        pairs = []
        skipped_log = []
        for idx, file in enumerate(files):
            meta = file_manifest[idx] if idx < len(file_manifest) and isinstance(file_manifest[idx], dict) else {}
            fname = (meta.get("filename") or file.filename or f"upload_{idx}").strip()
            file_id = (meta.get("file_id") or fname or f"upload_{idx}").strip()
            if overwrite_map and (overwrite_map.get(file_id) == "skip" or overwrite_map.get(fname) == "skip"):
                skipped_log.append(f"⏭️  {fname}  →  ignorado (duplicado)")
                continue
            safe_name = Path(fname).name or f"upload_{idx}"
            dest = tmp / f"{idx:04d}_{safe_name}"
            dest.write_bytes(await file.read())
            pairs.append((dest, fname))

        if not pairs:
            try:
                shutil.rmtree(tmp)
            except Exception:
                pass
            return {"ok": True, "log": skipped_log + ["⚠ Nenhum arquivo para processar (todos ignorados)."], "last_date": ""}

        force_overwrite = bool(overwrite_map and any(v == "overwrite" for v in overwrite_map.values()))
        result = process_file_list(pairs, default_density, source_type="upload", source_ref="ui-upload", force_overwrite=force_overwrite)
        result["log"] = skipped_log + result.get("log", [])
        try:
            shutil.rmtree(tmp)
        except Exception:
            pass
        conn = db_conn()
        cur = conn.cursor()
        last_date = cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""
        conn.close()
        return {**result, "ok": True, "last_date": last_date}

    @app.post("/api/process-folder")
    def api_process_folder(body: dict):
        folder = body.get("folder", "").strip()
        if not folder or not os.path.isdir(folder):
            raise HTTPException(400, f"Pasta não encontrada: {folder}")
        overwrite_map = body.get("overwrite_map") or {}
        all_files = _discover_measurement_files(folder)
        if not all_files:
            raise HTTPException(400, "Nenhum PDF, TXT ou ZIP encontrado.")
        force_overwrite = bool((body or {}).get("force_overwrite"))
        scoped_files, scan_scope = _incremental_folder_candidates(all_files, scan_all=bool((body or {}).get("scan_all")))
        tmp = Path(tempfile.mkdtemp(prefix="folder_zip_", dir=upload_dir))
        materialized_pairs, zip_log = _materialize_process_pairs(scoped_files, tmp, skip_known_zip_entries=not force_overwrite)
        pairs = []
        skipped_log = []
        for path, fname in materialized_pairs:
            if overwrite_map and (overwrite_map.get(str(path)) == "skip" or overwrite_map.get(fname) == "skip"):
                skipped_log.append(f"⏭️  {fname}  →  ignorado (duplicado)")
                continue
            pairs.append((path, fname))
        if not pairs:
            try:
                shutil.rmtree(tmp)
            except Exception:
                pass
            return {"ok": True, "log": [f"Escopo: {scan_scope}"] + zip_log + skipped_log + ["⚠ Nenhum arquivo para processar (todos ignorados)."], "last_date": ""}
        try:
            result = process_file_list(
                pairs,
                default_density,
                source_type="folder",
                source_ref=folder,
                force_overwrite=force_overwrite,
            )
            result["log"] = [f"Escopo: {scan_scope}"] + zip_log + skipped_log + result.get("log", [])
            conn = db_conn()
            cur = conn.cursor()
            last_date = cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""
            conn.close()
            return {**result, "ok": True, "last_date": last_date}
        finally:
            try:
                shutil.rmtree(tmp)
            except Exception:
                pass

    @app.post("/api/latest-day-ingestion/preview")
    def api_latest_day_ingestion_preview(body: dict):
        return _scan_latest_day_ingestion(body or {})

    @app.post("/api/latest-day-ingestion/process")
    def api_latest_day_ingestion_process(body: dict):
        return _process_latest_day_ingestion(body or {})

    @app.get("/api/monthly-gap-scan")
    def api_monthly_gap_scan(month: str = ""):
        target_month = str(month or "").strip() or datetime.now().strftime("%Y-%m")
        return _scan_month_source_coverage(target_month)

    @app.post("/api/monthly-gap-scan/import")
    def api_monthly_gap_scan_import(body: dict):
        body = body or {}
        month = str(body.get("month") or "").strip()
        if not month:
            raise HTTPException(400, "Informe o mês (YYYY-MM).")
        scan = _scan_month_source_coverage(month)
        pending_files = scan.get("pending_files") or []

        requested_paths = body.get("paths")
        if requested_paths:
            wanted = {str(p).strip() for p in requested_paths if str(p).strip()}
            pending_files = [item for item in pending_files if item.get("path") in wanted]

        if not pending_files:
            return {"ok": True, "scan": scan, "processed": 0, "skipped": 0, "log": ["Nenhum arquivo pendente para importar."], "last_date": ""}

        pairs = [(Path(item["path"]), Path(item["path"]).name) for item in pending_files if Path(item["path"]).is_file()]
        if not pairs:
            return {"ok": True, "scan": scan, "processed": 0, "skipped": 0, "log": ["Arquivos pendentes não foram encontrados no disco (podem ter sido movidos)."], "last_date": ""}

        result = process_file_list(pairs, default_density, source_type="monthly-gap-scan", source_ref=month, force_overwrite=False)
        conn = db_conn()
        cur = conn.cursor()
        last_date = cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""
        conn.close()
        return {**result, "ok": True, "scan": scan, "last_date": last_date}

    @app.post("/api/calendar-repair/run")
    def api_calendar_repair_run(body: dict | None = None):
        body = body or {}
        month = str(body.get("month") or "").strip() or datetime.now().strftime("%Y-%m")
        if not re.match(r"^\d{4}-\d{2}$", month):
            raise HTTPException(400, "Mês inválido. Use o formato YYYY-MM.")
        full_scan = bool(body.get("full_scan") or body.get("diagnostic") or body.get("scan_month"))

        monitor_results = []
        if body.get("run_monitor", True) is not False:
            active_folders = _active_mpfm_monitor_folders()
            folders_to_run = active_folders if full_scan else [
                folder for folder in active_folders
                if "zip" in str(folder.get("id") or "").lower() or "zip" in str(folder.get("path") or "").lower()
            ]
            if not folders_to_run:
                folders_to_run = active_folders
            for folder in folders_to_run:
                result = _run_monitored_folder(folder, trigger="manual-repair")
                monitor_results.append(
                    {
                        "folder_id": folder.get("id") or "",
                        "label": folder.get("label") or Path(folder.get("path") or "").name,
                        "processed": result.get("processed", 0),
                        "skipped": result.get("skipped", 0),
                        "found": result.get("found", 0),
                        "ok": result.get("ok", False),
                    }
                )

        scan_before_import = None
        scan_after_import = None
        import_result = {"processed": 0, "skipped": 0, "log": ["Nenhum arquivo pendente para importar."]}
        remaining_pending = None
        remaining_source_gap = None
        if full_scan:
            scan_before_import = _scan_month_source_coverage(month)
            pending_files = scan_before_import.get("pending_files") or []
            if pending_files:
                pairs = [(Path(item["path"]), Path(item["path"]).name) for item in pending_files if Path(item["path"]).is_file()]
                if pairs:
                    import_result = process_file_list(
                        pairs,
                        default_density,
                        source_type="calendar-repair",
                        source_ref=month,
                        force_overwrite=False,
                    )
                else:
                    import_result = {"processed": 0, "skipped": 0, "log": ["Arquivos pendentes não foram encontrados no disco."]}
            scan_after_import = _scan_month_source_coverage(month)
            remaining_pending = int((scan_after_import.get("summary") or {}).get("total_pending") or 0)
            remaining_source_gap = int((scan_after_import.get("summary") or {}).get("total_source_gap") or 0)

        conn = db_conn()
        cur = conn.cursor()
        last_date = cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""
        conn.close()
        monitor_processed = sum(int(item.get("processed") or 0) for item in monitor_results)
        import_processed = int(import_result.get("processed") or 0)
        return {
            "ok": True,
            "mode": "full" if full_scan else "quick",
            "month": month,
            "monitor_results": monitor_results,
            "import_result": import_result,
            "scan_before_import": scan_before_import,
            "scan_after_import": scan_after_import,
            "last_date": last_date,
            "status": "ok" if remaining_pending in (None, 0) else "pending",
            "message": (
                f"Ronda rápida concluída: {monitor_processed + import_processed} arquivo(s) novo(s) processado(s). Atualize/abra o detalhe do dia; vermelho restante indica arquivo de fechamento ainda ausente."
                if not full_scan else
                "Calendário conferido. Não há arquivos elegíveis pendentes; o que permanecer vermelho é fonte ainda ausente."
                if remaining_pending == 0
                else f"Calendário conferido, mas ainda há {remaining_pending} arquivo(s) existente(s) no disco sem importar."
            ),
            "remaining_pending": remaining_pending,
            "remaining_source_gap": remaining_source_gap,
        }

    @app.post("/api/sep-folder/preview")
    def api_sep_folder_preview(body: dict):
        _source_root, _selected, preview = _sep_folder_scan_from_body(body or {})
        return {"ok": True, "preview": preview}

    @app.post("/api/sep-folder/import")
    def api_sep_folder_import(body: dict):
        source_root, selected, preview = _sep_folder_scan_from_body(body or {})
        if not selected:
            return {"ok": True, "preview": preview, "log": ["Nenhum TXT SEP elegível para importar."], "last_date": ""}

        items = [(item.path, item.name) for item in selected]
        result = process_file_list(
            items,
            default_density,
            source_type="manual-sep-folder",
            source_ref=str(source_root),
            force_overwrite=bool((body or {}).get("force_overwrite")),
        )
        conn = db_conn()
        cur = conn.cursor()
        last_date = cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or ""
        conn.close()
        return {**result, "ok": True, "preview": preview, "last_date": last_date}

    @app.get("/api/auto-folder-monitor")
    def api_get_auto_folder_monitor():
        return _monitor_snapshot()

    @app.post("/api/auto-folder-monitor")
    async def api_save_auto_folder_monitor(request: Request):
        nonlocal monitor_prefs
        body = await request.json()
        monitor_prefs = _save_monitor_prefs(body or {})
        _refresh_monitor_next_scan()
        monitor_state["wake_event"].set()
        return {"ok": True, **_monitor_snapshot()}

    @app.post("/api/auto-folder-monitor/run-now")
    async def api_run_auto_folder_monitor_now(request: Request):
        import asyncio
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        folder_id = str((body or {}).get("folder_id") or "").strip() or None
        configured_folders = list(monitor_prefs.get("folders", []))
        if folder_id:
            folders = [folder for folder in configured_folders if folder["id"] == folder_id]
        else:
            folders = [folder for folder in configured_folders if folder.get("active", True)]
        if not folders:
            message = "Pasta monitorada não encontrada." if folder_id else "Nenhuma pasta ativa selecionada."
            return {"ok": True, "message": message, **_monitor_snapshot()}
        
        def _run_sync():
            results = []
            for folder in folders:
                result = _run_monitored_folder(folder, trigger="manual")
                status = monitor_state["status"]["folders"].setdefault(folder["id"], {})
                if folder.get("active", True):
                    status["next_scan_ts"] = time.time() + max(30, int(folder.get("interval_seconds") or 300))
                    status["next_scan_at_iso"] = datetime.fromtimestamp(status["next_scan_ts"]).isoformat()
                else:
                    status.pop("next_scan_ts", None)
                    status["next_scan_at_iso"] = ""
                results.append(
                    {
                        "folder_id": folder["id"],
                        "label": folder.get("label") or Path(folder["path"]).name,
                        "processed": result.get("processed", 0),
                        "skipped": result.get("skipped", 0),
                        "found": result.get("found", 0),
                        "ok": result.get("ok", False),
                    }
                )
                monitor_state["status"]["last_cycle_at"] = _now_local_iso()
            monitor_state["status"]["last_cycle_message"] = " | ".join(
                f"{item['label']}: {item['processed']} processado(s), {item['skipped']} ignorado(s)" for item in results
            )
            return results

        results = await asyncio.to_thread(_run_sync)
        return {"ok": True, "results": results, **_monitor_snapshot()}

    @app.get("/api/list-outputs")
    def api_list_outputs():
        files = sorted(
            (file for file in output_dir.glob("*.xlsx") if _is_supported_output_workbook(file)),
            key=lambda file: file.stat().st_mtime,
            reverse=True,
        )
        payload = []
        for file in files:
            payload.append(
                {
                    "name": file.name,
                    "size_kb": round(file.stat().st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).strftime("%d-%m-%Y %H:%M"),
                    **_download_readiness(file),
                }
            )
        return {"files": payload}

    @app.get("/api/download/{filename}")
    def api_download(filename: str):
        path = _resolve_safe(output_dir, filename)
        if not path.exists():
            raise HTTPException(404, "Arquivo não encontrado")
        readiness = _download_readiness(path)
        if readiness["is_rebuilding"]:
            raise HTTPException(409, readiness["rebuild_message"])
        return FileResponse(str(path), filename=filename)

    @app.delete("/api/outputs/{filename}")
    def api_delete(filename: str):
        path = _resolve_safe(output_dir, filename)
        if path.exists():
            path.unlink()
        return {"ok": True}

    @app.get("/api/sheets/{filename}")
    def api_list_sheets(filename: str):
        path = _resolve_safe(output_dir, filename)
        if not path.exists():
            raise HTTPException(404, "Arquivo não encontrado")
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        sheets = workbook.sheetnames
        workbook.close()
        return {"sheets": sheets}

    @app.get("/api/view/{filename}")
    def api_view_compat(filename: str):
        return api_list_sheets(filename)

    @app.get("/api/view/{filename}/{sheet}")
    def api_view_sheet(filename: str, sheet: str):
        path = _resolve_safe(output_dir, filename)
        if not path.exists():
            raise HTTPException(404, "Arquivo não encontrado")
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        if sheet not in workbook.sheetnames:
            workbook.close()
            raise HTTPException(404, f'Aba "{sheet}" não encontrada')
        ws = workbook[sheet]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 501:
                break
            rows.append(["" if v is None else ("NaN" if isinstance(v, float) and math.isnan(v) else v) for v in row])
        workbook.close()
        headers = rows[0] if rows else []
        data = rows[1:] if len(rows) > 1 else []
        return {"headers": headers, "rows": data, "total": len(data)}
