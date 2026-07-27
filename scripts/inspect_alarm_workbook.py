from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.alarme import inspect_alarm_workbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspeciona a estrutura de um workbook de alarmes.")
    parser.add_argument("path", type=Path, help="Caminho do arquivo .xlsx")
    parser.add_argument("--pretty", action="store_true", help="Imprime JSON formatado")
    parser.add_argument("--summary", action="store_true", help="Imprime um resumo textual compacto das abas.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    payload = inspect_alarm_workbook(args.path)
    if args.summary:
        for sheet in payload.get("sheets", []):
            print(f"SHEET={sheet['name']}|ROWS={sheet['rows']}|COLS={sheet['cols']}")
            if sheet.get("header"):
                print("HEADER=" + " || ".join(str(value or "") for value in sheet["header"]))
            for row in (sheet.get("preview_rows") or [])[1:4]:
                print("ROW=" + " || ".join(str(value or "") for value in row))
            print("---")
    elif args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())