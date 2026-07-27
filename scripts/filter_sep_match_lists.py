from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_INPUTS = {
    "agua": "agua_matches1.txt",
    "gas": "gas_matches1.txt",
    "oleo": "oleo_matches1.txt",
}

DEFAULT_ALLOWED_MARKERS = ("Run_Daily", "Run_24Hours")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filtra listas de matches SEP por padrao de arquivo.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Pasta onde estao os arquivos de listas.")
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=sorted(DEFAULT_INPUTS),
        default=["agua", "gas", "oleo"],
        help="Fases a filtrar.",
    )
    parser.add_argument(
        "--allowed-markers",
        nargs="+",
        default=list(DEFAULT_ALLOWED_MARKERS),
        help="Substrings aceitas no nome do arquivo.",
    )
    parser.add_argument(
        "--suffix",
        default="daily24",
        help="Sufixo do arquivo de saida, no formato <phase>_matches_<suffix>.txt.",
    )
    return parser.parse_args()


def filter_lines(lines: list[str], allowed_markers: tuple[str, ...]) -> tuple[list[str], int]:
    kept: list[str] = []
    dropped = 0
    for line in lines:
        value = line.strip()
        if not value:
            continue
        if any(marker in value for marker in allowed_markers):
            kept.append(value)
        else:
            dropped += 1
    return kept, dropped


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    allowed_markers = tuple(args.allowed_markers)

    if not data_dir.exists() or not data_dir.is_dir():
        print(f"ERRO|Pasta nao encontrada: {data_dir}")
        return 2

    for phase in args.phases:
        input_name = DEFAULT_INPUTS[phase]
        input_path = data_dir / input_name
        if not input_path.exists():
            print(f"WARN|Lista ausente: {input_path}")
            continue

        lines = input_path.read_text(encoding="utf-8").splitlines()
        kept, dropped = filter_lines(lines, allowed_markers)
        output_path = data_dir / f"{phase}_matches_{args.suffix}.txt"
        output_text = ("\n".join(kept) + "\n") if kept else ""
        output_path.write_text(output_text, encoding="utf-8")

        print(
            "RESULT|"
            f"phase={phase}|input={input_name}|output={output_path.name}|"
            f"kept={len(kept)}|dropped={dropped}|markers={','.join(allowed_markers)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())