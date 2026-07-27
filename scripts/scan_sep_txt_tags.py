from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


PHASE_TAGS = {
    "agua": "20FT0251",
    "gas": "20FT0244",
    "oleo": "20FT0247",
}
PHASE_TAG_BYTES = {phase: tag.encode("ascii") for phase, tag in PHASE_TAGS.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Escaneia TXT e encontra TAGs de fases do separador de testes.")
    parser.add_argument("root", type=Path, help="Pasta raiz a ser escaneada")
    parser.add_argument("--sample-size", type=int, default=8, help="Quantidade de exemplos por fase")
    parser.add_argument("--output", type=Path, default=None, help="Arquivo opcional para salvar o relatorio")
    parser.add_argument("--glob", default="*.txt", help="Padrao de nome para os arquivos a escanear")
    parser.add_argument("--max-bytes", type=int, default=0, help="Ler somente os primeiros N bytes de cada arquivo. 0 = arquivo inteiro")
    return parser.parse_args()


def month_bucket(root: Path, path: Path) -> str:
    relative = path.relative_to(root)
    return relative.parts[0] if relative.parts else "root"


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR|root_not_found={root}")
        return 2

    phase_paths: dict[str, list[Path]] = {phase: [] for phase in PHASE_TAGS}
    monthly_counts: dict[str, dict[str, int]] = defaultdict(lambda: {phase: 0 for phase in PHASE_TAGS})
    total_txt = 0
    unreadable = 0
    print_every = 10000

    for path in root.rglob(args.glob):
        total_txt += 1
        try:
            blob = path.read_bytes()
            if args.max_bytes > 0:
                blob = blob[: args.max_bytes]
        except OSError:
            unreadable += 1
            continue
        matched_any = False
        bucket = month_bucket(root, path)
        for phase, tag in PHASE_TAG_BYTES.items():
            if tag in blob:
                phase_paths[phase].append(path)
                monthly_counts[bucket][phase] += 1
                matched_any = True
        if matched_any:
            monthly_counts[bucket].setdefault("matched_total", 0)
            monthly_counts[bucket]["matched_total"] += 1
        if total_txt % print_every == 0:
            print(f"PROGRESS={total_txt}", flush=True)

    lines: list[str] = []
    lines.append(f"TOTAL_TXT={total_txt}")
    lines.append(f"UNREADABLE_TXT={unreadable}")
    for phase in ("agua", "gas", "oleo"):
        lines.append(f"PHASE={phase}|TAG={PHASE_TAGS[phase]}|COUNT={len(phase_paths[phase])}")

    lines.append("MONTHLY_BREAKDOWN")
    for bucket in sorted(monthly_counts):
        row = monthly_counts[bucket]
        lines.append(
            f"MONTH={bucket}|AGUA={row.get('agua', 0)}|GAS={row.get('gas', 0)}|"
            f"OLEO={row.get('oleo', 0)}|MATCHED_TOTAL={row.get('matched_total', 0)}"
        )

    lines.append("SAMPLES")
    for phase in ("agua", "gas", "oleo"):
        lines.append(f"PHASE={phase}")
        for sample in phase_paths[phase][: args.sample_size]:
            lines.append(str(sample))

    report = "\n".join(lines)
    print(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())