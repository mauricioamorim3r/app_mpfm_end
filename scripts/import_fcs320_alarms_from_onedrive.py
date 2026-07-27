"""Import FCS320 alarm PDFs directly from the OneDrive source folder into the app DB.

Scans:
  3.1.7_ALARMES_FCS_320/2026/<mes>/*.pdf
under the shared OneDrive site, skips files whose basename (normalized) already
has a matching source_ref in alarm_records, skips exact-content duplicates
(e.g. "..._001.pdf" reprints), and imports the rest via the existing
services.alarme pipeline (same code path used by the upload API).

Usage:
    python scripts/import_fcs320_alarms_from_onedrive.py            # dry-run preview
    python scripts/import_fcs320_alarms_from_onedrive.py --commit    # actually import
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_config import DB_PATH
from db_schema import apply_schema, run_migrations
from repositories.alarme import AlarmRepository
from services.alarme.alarm_service import _incident_rows, _parse_fcs320_pdf

ONEDRIVE_ROOT = Path(
    r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM"
    r"\3. Registros de Operação SGM Multifasico\3.1 Registros Diarios MPFM\3.1.7_ALARMES_FCS_320\2026"
)


def _norm(name: str) -> str:
    return re.sub(r"[\s_]+", "_", name.strip().lower())


def db_conn():
    db_target = str(DB_PATH)
    conn = sqlite3.connect(db_target, uri=db_target.startswith("file:"), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _imported_basenames() -> set[str]:
    conn = db_conn()
    try:
        refs = [r[0] for r in conn.execute(
            "SELECT DISTINCT source_ref FROM alarm_records WHERE source_kind='pdf'"
        ).fetchall()]
    finally:
        conn.close()
    seen = set()
    for ref in refs:
        for part in ref.split(";"):
            part = part.strip()
            if part.lower().startswith("pdf:"):
                part = part[4:]
            name = Path(part).name if ("\\" in part or "/" in part) else part
            if name.lower().endswith(".pdf"):
                seen.add(_norm(name))
    return seen


def _content_hash(rows: list[dict]) -> str:
    key = "|".join(f"{r.get('event_at')}:{r.get('tag')}:{r.get('message')}" for r in rows)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Actually write to the DB (default is dry-run)")
    args = parser.parse_args()

    all_files = sorted(ONEDRIVE_ROOT.glob("*/*.pdf"))
    imported_basenames = _imported_basenames()

    candidates = [p for p in all_files if _norm(p.name) not in imported_basenames]

    to_import: list[tuple[Path, list[dict]]] = []
    skipped_duplicate_content: list[Path] = []
    seen_hashes: dict[str, Path] = {}
    for i, path in enumerate(candidates, start=1):
        print(f"[{i}/{len(candidates)}] reading {path.name}...", flush=True)
        rows = _parse_fcs320_pdf(path)
        digest = _content_hash(rows)
        if digest in seen_hashes:
            skipped_duplicate_content.append(path)
            continue
        seen_hashes[digest] = path
        to_import.append((path, rows))

    print(f"Files found under OneDrive tree: {len(all_files)}")
    print(f"Already imported (by basename): {len(all_files) - len(candidates)}")
    print(f"New candidates: {len(candidates)}")
    print(f"Skipped exact-duplicate content: {len(skipped_duplicate_content)}")
    for p in skipped_duplicate_content:
        print(f"  duplicate skipped: {p.relative_to(ONEDRIVE_ROOT)}")
    print(f"Will import: {len(to_import)} files")

    if not args.commit:
        print("\nDry-run only. Re-run with --commit to write to the database.")
        return

    conn = db_conn()
    cur = conn.cursor()
    apply_schema(cur)
    run_migrations(cur)
    conn.commit()
    conn.close()

    repo = AlarmRepository(db_conn)
    total_imported = 0
    for path, events in to_import:
        incidents = _incident_rows(events)
        imported = 0
        for row in (*events, *incidents):
            alarm_id = repo.save_alarm(row)
            if alarm_id:
                imported += 1
        total_imported += imported
        print(f"  {path.relative_to(ONEDRIVE_ROOT)} -> imported {imported} rows ({len(events)} events, {len(incidents)} incidents)", flush=True)

    print(f"\nDONE. Total rows imported: {total_imported}")


if __name__ == "__main__":
    main()
