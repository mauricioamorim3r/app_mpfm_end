from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from server import DEFAULT_DENSITY, db_conn, process_file_list


DEFAULT_SOURCE_ROOT = Path(
    "C:/Users/MAUAM/OneDrive - Equinor/Desktop/DPB FPSO Bacalhau - Metering - 3.2 Daily Reports"
)

VALID_NAME_MARKERS = ("MPFM_DAILY", "MPFM_HOURLY")
MONTH_RE = re.compile(r"(20\d{2})(\d{2})(\d{2})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importa PDFs MPFM externos em lotes mensais.")
    parser.add_argument("--root", type=Path, default=DEFAULT_SOURCE_ROOT, help="Pasta raiz com os PDFs.")
    parser.add_argument(
        "--limit-batches",
        type=int,
        default=0,
        help="Limita o numero de lotes processados nesta execucao. 0 = todos.",
    )
    return parser.parse_args()


def month_key_from_name(filename: str) -> str:
    match = MONTH_RE.search(filename)
    if not match:
        return "unknown"
    return f"{match.group(1)}-{match.group(2)}"


def is_valid_mpfm_pdf(path: Path) -> bool:
    upper_name = path.name.upper()
    return path.suffix.lower() == ".pdf" and any(marker in upper_name for marker in VALID_NAME_MARKERS)


def top_level_group(root: Path, path: Path) -> str:
    relative = path.relative_to(root)
    return relative.parts[0] if relative.parts else root.name


def discover_batches(root: Path) -> tuple[list[tuple[str, str, list[tuple[Path, str]]]], int]:
    grouped: dict[tuple[str, str], list[tuple[Path, str]]] = defaultdict(list)
    ignored = 0
    for path in root.rglob("*.pdf"):
        if not is_valid_mpfm_pdf(path):
            ignored += 1
            continue
        folder = top_level_group(root, path)
        month = month_key_from_name(path.name)
        grouped[(folder, month)].append((path, path.name))

    batches = []
    for (folder, month), files in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        files.sort(key=lambda item: item[1])
        batches.append((folder, month, files))
    return batches, ignored


def read_counts() -> dict[str, str | int]:
    conn = db_conn()
    cur = conn.cursor()
    counts = {
        "runs": cur.execute("SELECT COUNT(*) FROM processing_runs").fetchone()[0],
        "raw": cur.execute("SELECT COUNT(*) FROM source_files_raw").fetchone()[0],
        "curated": cur.execute("SELECT COUNT(*) FROM measurements_curated").fetchone()[0],
        "issues": cur.execute("SELECT COUNT(*) FROM validation_issues").fetchone()[0],
        "last_day": cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or "",
    }
    conn.close()
    return counts


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERRO|Pasta nao encontrada: {root}")
        return 2

    batches, ignored = discover_batches(root)
    total_files = sum(len(files) for _, _, files in batches)
    print(f"SOURCE_ROOT={root}")
    print(f"BATCHES={len(batches)}")
    print(f"VALID_FILES={total_files}")
    print(f"IGNORED_FILES={ignored}")

    processed_batches = 0
    for folder, month, files in batches:
        if args.limit_batches and processed_batches >= args.limit_batches:
            break
        source_ref = f"{root}|{folder}|{month}"
        print(f"BATCH_START|folder={folder}|month={month}|files={len(files)}", flush=True)
        try:
            result = process_file_list(files, DEFAULT_DENSITY, source_type="bulk-folder-batch", source_ref=source_ref)
            counts = read_counts()
            print(
                "BATCH_DONE|"
                f"folder={folder}|month={month}|files={len(files)}|"
                f"runs={counts['runs']}|raw={counts['raw']}|curated={counts['curated']}|"
                f"issues={counts['issues']}|last_day={counts['last_day']}|log={len(result.get('log', []))}",
                flush=True,
            )
        except Exception as exc:
            print(f"BATCH_ERROR|folder={folder}|month={month}|files={len(files)}|error={exc}", flush=True)
        processed_batches += 1

    final_counts = read_counts()
    print(
        "FINAL|"
        f"runs={final_counts['runs']}|raw={final_counts['raw']}|curated={final_counts['curated']}|"
        f"issues={final_counts['issues']}|last_day={final_counts['last_day']}|processed_batches={processed_batches}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())