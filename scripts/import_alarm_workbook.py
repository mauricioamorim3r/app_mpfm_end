from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app_config import DB_PATH
from db_schema import apply_schema, run_migrations
from repositories.alarme import AlarmRepository
from services.alarme import import_alarm_workbook, preview_alarm_workbook_import


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview ou importa workbook de alarmes para o SQLite local.")
    parser.add_argument("path", type=Path, help="Caminho do arquivo .xlsx")
    parser.add_argument("--preview", action="store_true", help="Apenas mostra o resumo de importação")
    parser.add_argument("--pretty", action="store_true", help="Imprime JSON formatado")
    return parser.parse_args()


def db_conn():
    db_target = str(DB_PATH)
    conn = sqlite3.connect(db_target, uri=db_target.startswith("file:"), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    return conn


def init_db() -> None:
    conn = db_conn()
    cur = conn.cursor()
    apply_schema(cur)
    run_migrations(cur)
    conn.commit()
    conn.close()


def main() -> int:
    args = parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    init_db()
    repo = AlarmRepository(db_conn)
    payload = preview_alarm_workbook_import(args.path) if args.preview else import_alarm_workbook(args.path, repo=repo)
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())