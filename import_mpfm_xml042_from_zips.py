"""
Extrai arquivos XML 042 (MPFM) dos ZIPs da pasta DPB e importa na aplicação.

Uso:
  python import_mpfm_xml042_from_zips.py [--zip-folder "..."] [--app-url http://localhost:8765]

Os ZIPs processados têm nomes tipo: 07-07.zip, 06-07.zip, etc.
Dentro há: 042_bbbbbbbb_YYYYMMDD000000.xml → XML MPFM com medições por banco/riser.
"""
import argparse
import sys
import os
import zipfile
import urllib.request
import urllib.error
import json
import io
import re
from pathlib import Path

DEFAULT_ZIP_FOLDER = (
    r"C:\Users\MAUAM\OneDrive - Equinor"
    r"\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM"
    r"\3. Registros de Operação SGM Multifasico\3.7 Registros XML 042"
)
DEFAULT_APP_URL = "http://localhost:8765"
API_IMPORT = "/api/xml042/import"


def find_xml042_in_zip(zip_path: Path) -> list[tuple[str, bytes]]:
    """Retorna lista de (filename, content) dos XMLs 042 dentro do ZIP."""
    results = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for entry in zf.namelist():
                name = Path(entry).name
                if re.match(r"042_[a-zA-Z0-9_]+_\d{8}\d+", name) and name.endswith(".xml"):
                    results.append((name, zf.read(entry)))
    except zipfile.BadZipFile:
        print(f"  [AVISO] ZIP inválido: {zip_path.name}")
    except Exception as e:
        print(f"  [ERRO] {zip_path.name}: {e}")
    return results


def post_files_multipart(url: str, files: list[tuple[str, bytes]]) -> dict:
    """POST multipart/form-data com múltiplos arquivos."""
    boundary = "DPB_BOUNDARY_X42"
    body_parts = []
    for name, content in files:
        part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{name}"\r\n'
            f"Content-Type: application/xml\r\n\r\n"
        ).encode("utf-8") + content + b"\r\n"
        body_parts.append(part)
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(body_parts)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Importa XML 042 MPFM dos ZIPs para o app.")
    parser.add_argument("--zip-folder", default=DEFAULT_ZIP_FOLDER)
    parser.add_argument("--app-url", default=DEFAULT_APP_URL)
    parser.add_argument("--dry-run", action="store_true", help="Apenas lista, não importa")
    args = parser.parse_args()

    zip_folder = Path(args.zip_folder)
    if not zip_folder.exists():
        print(f"Pasta de ZIPs não encontrada: {zip_folder}")
        sys.exit(1)

    api_url = args.app_url.rstrip("/") + API_IMPORT

    # Encontrar todos os ZIPs (incluindo Old/)
    zip_files = sorted(zip_folder.glob("*.zip")) + sorted((zip_folder / "Old").glob("*.zip"))
    print(f"ZIPs encontrados: {len(zip_files)}")

    all_xmls: list[tuple[str, bytes, str]] = []  # (name, content, zip_source)
    for zp in zip_files:
        xmls = find_xml042_in_zip(zp)
        for name, content in xmls:
            all_xmls.append((name, content, zp.name))

    print(f"\nXMLs 042 encontrados nos ZIPs: {len(all_xmls)}")
    if not all_xmls:
        print("Nenhum XML 042 encontrado nos ZIPs.")
        sys.exit(0)

    # Mostrar o que foi encontrado
    for name, content, source in all_xmls:
        date_m = re.search(r"_(\d{8})", name)
        date_str = date_m.group(1) if date_m else "?"
        print(f"  {name}  [{len(content)} bytes]  ← {source}")

    if args.dry_run:
        print("\n[DRY RUN] Nenhuma importação realizada.")
        sys.exit(0)

    # Importar em lotes de 10
    BATCH = 10
    total_imported = total_dup = total_err = 0
    batches = [all_xmls[i:i+BATCH] for i in range(0, len(all_xmls), BATCH)]

    for idx, batch in enumerate(batches, 1):
        files = [(name, content) for name, content, _ in batch]
        try:
            result = post_files_multipart(api_url, files)
        except urllib.error.URLError as e:
            print(f"\n[ERRO conexão] Lote {idx}: {e}")
            print("Verifique se o app está rodando em", args.app_url)
            sys.exit(1)

        imp = result.get("imported", [])
        dup = result.get("duplicates", [])
        err = result.get("errors", [])
        total_imported += len(imp)
        total_dup += len(dup)
        total_err += len(err)
        print(f"  Lote {idx}/{len(batches)}: {len(imp)} importados | {len(dup)} duplicados | {len(err)} erros")
        for e in err:
            print(f"    [ERRO] {e.get('filename')}: {e.get('message')}")

    print(f"\n=== CONCLUÍDO ===")
    print(f"  Importados:  {total_imported}")
    print(f"  Duplicados:  {total_dup}")
    print(f"  Erros:       {total_err}")


if __name__ == "__main__":
    main()
