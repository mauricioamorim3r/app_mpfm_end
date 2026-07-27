from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import DEFAULT_DENSITY, db_conn, process_file_list
from services.importing import classify_input


DEFAULT_SOURCE_ROOT = Path(
    "C:/Users/MAUAM/OneDrive - Equinor/Desktop/DPB FPSO Bacalhau - Metering - 00 - Daily Reports/2026"
)
DEFAULT_MATCHES_DIR = Path("data")
DEFAULT_MATCH_FILES = {
    "agua": "agua_matches.txt",
    "gas": "gas_matches.txt",
    "oleo": "oleo_matches.txt",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importa TXTs do separador a partir das listas geradas por fase.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT, help="Raiz dos relatórios TXT 2026.")
    parser.add_argument("--matches-dir", type=Path, default=DEFAULT_MATCHES_DIR, help="Pasta com os arquivos *_matches.txt.")
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=sorted(DEFAULT_MATCH_FILES),
        default=["agua", "gas", "oleo"],
        help="Fases a importar.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limita o numero total de arquivos desta execucao. 0 = todos.")
    parser.add_argument("--dry-run", action="store_true", help="Somente valida os arquivos e mostra o resumo.")
    return parser.parse_args()


def read_counts() -> dict[str, int | str]:
    conn = db_conn()
    cur = conn.cursor()
    counts = {
        "runs": cur.execute("SELECT COUNT(*) FROM processing_runs").fetchone()[0],
        "raw": cur.execute("SELECT COUNT(*) FROM source_files_raw").fetchone()[0],
        "curated": cur.execute("SELECT COUNT(*) FROM measurements_curated").fetchone()[0],
        "issues": cur.execute("SELECT COUNT(*) FROM validation_issues").fetchone()[0],
        "sep_source_files": cur.execute("SELECT COUNT(*) FROM sep_source_files").fetchone()[0],
        "sep_curated": cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE source_record_id IS NOT NULL").fetchone()[0],
        "last_day": cur.execute("SELECT MAX(day_ref) FROM measurements_curated").fetchone()[0] or "",
    }
    conn.close()
    return counts


def _phase_match_path(matches_dir: Path, phase: str) -> Path:
    return matches_dir / DEFAULT_MATCH_FILES[phase]


def collect_files(source_root: Path, matches_dir: Path, phases: list[str], limit: int) -> tuple[list[tuple[Path, str]], list[str]]:
    items: list[tuple[Path, str]] = []
    errors: list[str] = []
    seen: set[Path] = set()

    for phase in phases:
        match_path = _phase_match_path(matches_dir, phase)
        if not match_path.exists():
            errors.append(f"Lista nao encontrada: {match_path}")
            continue
        for raw_line in match_path.read_text(encoding="utf-8").splitlines():
            relative = raw_line.strip()
            if not relative:
                continue
            path = (source_root / Path(relative)).resolve()
            if path in seen:
                continue
            seen.add(path)
            if not path.exists() or not path.is_file():
                errors.append(f"Arquivo ausente: {path}")
                continue
            items.append((path, path.name))
            if limit and len(items) >= limit:
                return items, errors
    return items, errors


def summarize_files(items: list[tuple[Path, str]]) -> dict[str, Counter]:
    file_types: Counter[str] = Counter()
    meter_ids: Counter[str] = Counter()
    months: Counter[str] = Counter()
    for path, name in items:
        info = classify_input(path, name)
        file_types.update([str(info.get("file_type") or "")])
        meter_ids.update([str(info.get("meter_id") or "")])
        months.update([str(info.get("content_date") or "")[:7]])
    return {
        "file_types": file_types,
        "meter_ids": meter_ids,
        "months": months,
    }


def print_counter(prefix: str, counter: Counter[str]) -> None:
    for key, value in sorted(counter.items()):
        print(f"{prefix}|{key}={value}")


def print_counts(prefix: str, counts: dict[str, int | str]) -> None:
    parts = [f"{key}={counts[key]}" for key in ["runs", "raw", "curated", "issues", "sep_source_files", "sep_curated", "last_day"]]
    print(prefix + "|" + "|".join(parts))


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    matches_dir = args.matches_dir.resolve()

    if not source_root.exists() or not source_root.is_dir():
        print(f"ERRO|Pasta raiz nao encontrada: {source_root}")
        return 2
    if not matches_dir.exists() or not matches_dir.is_dir():
        print(f"ERRO|Pasta de listas nao encontrada: {matches_dir}")
        return 2

    items, errors = collect_files(source_root, matches_dir, args.phases, args.limit)
    if errors:
        for error in errors:
            print(f"WARN|{error}")
    if not items:
        print("ERRO|Nenhum arquivo elegivel encontrado.")
        return 2

    print(f"SOURCE_ROOT={source_root}")
    print(f"MATCHES_DIR={matches_dir}")
    print(f"PHASES={','.join(args.phases)}")
    print(f"FILES={len(items)}")
    summary = summarize_files(items)
    print_counter("FILE_TYPE", summary["file_types"])
    print_counter("METER_ID", summary["meter_ids"])
    print_counter("MONTH", summary["months"])
    for path, _ in items[:6]:
        print(f"SAMPLE|{path}")

    before = read_counts()
    print_counts("BEFORE", before)

    if args.dry_run:
        print("DRY_RUN=1")
        return 0

    result = process_file_list(
        items,
        DEFAULT_DENSITY,
        source_type="bulk-sep-txt-match-list",
        source_ref=f"{source_root}|{','.join(args.phases)}|files={len(items)}",
    )
    after = read_counts()
    print_counts("AFTER", after)
    print(
        "DELTA|"
        f"runs={after['runs'] - before['runs']}|"
        f"raw={after['raw'] - before['raw']}|"
        f"curated={after['curated'] - before['curated']}|"
        f"issues={after['issues'] - before['issues']}|"
        f"sep_source_files={after['sep_source_files'] - before['sep_source_files']}|"
        f"sep_curated={after['sep_curated'] - before['sep_curated']}"
    )
    print(f"RUN_ID={result.get('run_id')}")
    print(f"STATUS={result.get('status', 'ok')}")
    print(f"LOG_LINES={len(result.get('log', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())