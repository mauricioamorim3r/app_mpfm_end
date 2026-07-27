from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pdfplumber


APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path.home() / "Downloads" / "Matriz_dos_Requisitos_Metrologicos_Operacionais_SGM1.pdf"
OUT_DIR = APP_DIR / "data"


def extract_rows(pdf_path: Path) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    header: list[str] | None = None
    with pdfplumber.open(pdf_path) as doc:
        for page_num, page in enumerate(doc.pages, start=1):
            for table in page.extract_tables() or []:
                for raw_row in table:
                    cells = [(cell or "").strip().replace("\n", " ") for cell in raw_row]
                    if cells and cells[0] == "ID":
                        header = cells
                        continue
                    if header and cells and re.match(r"RM-\d+", cells[0]):
                        padded = (cells + [""] * len(header))[: len(header)]
                        item = {header[i]: padded[i] for i in range(len(header))}
                        item["Página"] = page_num
                        rows.append(item)
    return rows


def main() -> None:
    pdf_path = DEFAULT_PDF
    if not pdf_path.exists():
        raise FileNotFoundError(f"Matriz SGM1 não encontrada em {pdf_path}")
    rows = extract_rows(pdf_path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "matriz_requisitos_sgm1.json"
    csv_path = OUT_DIR / "matriz_requisitos_sgm1.csv"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"rows": len(rows), "json": str(json_path), "csv": str(csv_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
