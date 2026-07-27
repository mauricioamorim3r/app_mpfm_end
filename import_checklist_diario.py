"""
Importa automaticamente os arquivos de Checklist Diário mensais (2026) na aplicação.
Usa o endpoint POST /api/painel-operador/daily-checklist/import

Uso:
  python import_checklist_diario.py [--app-url http://localhost:8765] [--year 2026]
"""
import argparse
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

DEFAULT_APP_URL = "http://localhost:8765"
CHECKLIST_BASE = (
    r"C:\Users\MAUAM\OneDrive - Equinor"
    r"\DPB FPSO Bacalhau - Metering - 01 FPSO Bacalhau - Metering Management"
    r"\02 INTERNAL CONTROL\00 - Check Diário\2026"
)

API_IMPORT = "/api/painel-operador/daily-checklist/import"
API_INSPECT = "/api/painel-operador/daily-checklist/inspect"


def find_checklist_files(base: str) -> list[Path]:
    """Busca todos os .xlsm de checklist diário nas subpastas mensais."""
    root = Path(base)
    if not root.exists():
        print(f"Pasta não encontrada: {root}")
        sys.exit(1)
    found = []
    for xlsm in sorted(root.rglob("Bacalhau - Checklist Diario*.xlsm")):
        found.append(xlsm)
    return found


def api_call(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-url", default=DEFAULT_APP_URL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base_url = args.app_url.rstrip("/")
    files = find_checklist_files(CHECKLIST_BASE)

    if not files:
        print("Nenhum arquivo de checklist encontrado.")
        sys.exit(0)

    print(f"Encontrados {len(files)} arquivos de checklist:\n")
    for f in files:
        print(f"  {f}")

    if args.dry_run:
        print("\n[DRY RUN] Nenhuma importação realizada.")
        sys.exit(0)

    print()
    total_imported = 0
    for path in files:
        print(f"Importando: {path.name} ...")
        try:
            result = api_call(base_url + API_IMPORT, {"path": str(path)})
            n = result.get("imported_rows", 0) or result.get("rows_imported", 0)
            sheets = len(result.get("sheets", []))
            print(f"  ✓ {n} linhas importadas, {sheets} abas processadas")
            total_imported += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"  ✗ HTTP {e.code}: {body[:200]}")
        except urllib.error.URLError as e:
            print(f"  ✗ Conexão: {e}")
            print(f"    Verifique se o app está rodando em {args.app_url}")
            sys.exit(1)
        except Exception as e:
            print(f"  ✗ Erro: {e}")

    print(f"\n=== CONCLUÍDO: {total_imported}/{len(files)} arquivos importados ===")


if __name__ == "__main__":
    main()
