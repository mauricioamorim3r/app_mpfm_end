r"""Cria as abas normalizadas da Base Única sem remover a estrutura legada.

Uso:
    C:\Python313\python.exe migrar_base_unica_normalizada.py
    C:\Python313\python.exe migrar_base_unica_normalizada.py --base "D:\dados\BASE_UNICA_TOTAL.xlsx"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gerar_base_unica_standalone import migrate_master_to_normalized_model


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra a Base Única para as abas normalizadas.")
    parser.add_argument(
        "--base",
        default=str(Path(__file__).resolve().parent / "BASE_UNICA_TOTAL.xlsx"),
        help="Caminho da Base Única a migrar.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Arquivo de saída opcional. Use para validar a migração sem tocar na Base original.",
    )
    args = parser.parse_args()
    base = Path(args.base).expanduser().resolve()
    if not base.exists():
        parser.error(f"Arquivo não encontrado: {base}")
    output = Path(args.output).expanduser().resolve() if args.output.strip() else None
    result = migrate_master_to_normalized_model(base, output)
    print(
        "[OK] Modelo normalizado criado: "
        f"MPFM={result['mpfm']}; SEP={result['sep']}; "
        f"RECON={result['recon']}; legado preservado={result['total']}; saída={result['output']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
