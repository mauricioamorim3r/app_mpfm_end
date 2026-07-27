"""
Import all XML 042 files from a folder (and subfolders) into the running app.
Usage:
  python import_xml042_folder.py "C:\path\to\folder"
"""
import sys
import urllib.request
import urllib.error
import json
import mimetypes
from pathlib import Path
import io
import uuid

API_URL = "http://localhost:8765/api/xml042/import"


def multipart_body(files: list[tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body_parts = []
    for name, content in files:
        part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{name}"\r\n'
            f"Content-Type: text/xml\r\n\r\n"
        ).encode("utf-8") + content + b"\r\n"
        body_parts.append(part)
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(body_parts), f"multipart/form-data; boundary={boundary}"


def import_folder(folder: str, batch_size: int = 20):
    root = Path(folder)
    if not root.exists():
        print(f"ERRO: pasta não encontrada: {folder}")
        sys.exit(1)

    xml_files = sorted(root.rglob("*.xml"))
    if not xml_files:
        print(f"Nenhum arquivo .xml encontrado em: {folder}")
        sys.exit(0)

    print(f"Encontrados {len(xml_files)} arquivo(s) XML em: {folder}")
    total_imported = 0
    total_duplicates = 0
    total_errors = 0

    batches = [xml_files[i:i + batch_size] for i in range(0, len(xml_files), batch_size)]
    for batch_idx, batch in enumerate(batches, 1):
        files = []
        for path in batch:
            try:
                files.append((path.name, path.read_bytes()))
            except OSError as e:
                print(f"  [ERRO leitura] {path.name}: {e}")
                total_errors += 1

        if not files:
            continue

        body, content_type = multipart_body(files)
        req = urllib.request.Request(API_URL, data=body, method="POST")
        req.add_header("Content-Type", content_type)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
        except urllib.error.URLError as e:
            print(f"  [ERRO conexão] batch {batch_idx}: {e}")
            print("  Verifique se o app está rodando em http://localhost:8765")
            total_errors += len(files)
            continue

        imp = result.get("imported", [])
        dup = result.get("duplicates", [])
        err = result.get("errors", [])
        total_imported += len(imp)
        total_duplicates += len(dup)
        total_errors += len(err)

        print(f"  Lote {batch_idx}/{len(batches)}: {len(imp)} importados, {len(dup)} duplicados, {len(err)} erros")
        for e in err:
            print(f"    [ERRO] {e.get('filename')}: {e.get('message')}")

    print()
    print(f"=== CONCLUÍDO ===")
    print(f"  Importados:  {total_imported}")
    print(f"  Duplicados:  {total_duplicates}")
    print(f"  Erros:       {total_errors}")


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3. Registros de Operação SGM Multifasico\3.7 Registros XML 042\2026"
    import_folder(folder)
