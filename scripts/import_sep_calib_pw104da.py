"""
Importa arquivos TXT de separador da pasta Calib PW104DA.

Arquivos disponíveis:
- FC13 - 27_08_2026: 18 arquivos TXT (horas 01-18)
- FC14 - 27_08_2026: 18 arquivos TXT (horas 01-18)
- FC17 - 27_08_2026: 18 arquivos TXT (horas 01-18)

Total: 54 arquivos TXT de medições horárias do separador.

Uso:
    py -3 scripts/import_sep_calib_pw104da.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8765"
SOURCE_DIR = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM/3.1 Registros Diarios MPFM/Zip/Calib PW104DA/Calib PW104DA")


def scan_txt_files():
    """Escaneia recursivamente os arquivos TXT na pasta fonte."""
    txt_files = []
    for txt_path in SOURCE_DIR.rglob("*.txt"):
        txt_files.append(str(txt_path))
    return sorted(txt_files)


def import_sep_folder(folder_path: str, txt_paths: list[str]):
    """
    Importa arquivos TXT via endpoint /api/sep-folder/import.

    Nota: O endpoint espera um body com:
    - source_root: caminho da pasta raiz
    - force_overwrite: se deve sobrescrever dados existentes
    """
    url = f"{BASE_URL}/api/sep-folder/import"

    # O endpoint aceita um body com source_root
    # mas precisa escanear a pasta internamente
    # Então vamos passar o caminho da pasta raiz
    body = {
        "source_root": folder_path,
        "force_overwrite": False
    }

    print(f"📤 Enviando requisição para importar TXT de separador...")
    print(f"   Pasta: {folder_path}")
    print(f"   Arquivos encontrados: {len(txt_paths)}")

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=1800) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        print(f"\n✅ Importação concluída!")
        print(f"   Processados: {result.get('processed', 0)}")
        print(f"   Ignorados: {result.get('skipped', 0)}")
        print(f"   Última data: {result.get('last_date', 'N/A')}")

        if result.get("log"):
            print(f"\n📋 Log:")
            for line in result["log"]:
                print(f"   {line}")

        return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"\n❌ Erro HTTP {e.code}: {e.reason}")
        print(f"   {error_body}")
        return None
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return None


def main():
    print("=" * 80)
    print("IMPORTAÇÃO DE ARQUIVOS TXT - CALIB PW104DA")
    print("=" * 80)

    # Verifica se a pasta existe
    if not SOURCE_DIR.exists():
        print(f"❌ Pasta não encontrada: {SOURCE_DIR}")
        return

    # Escaneia arquivos
    txt_files = scan_txt_files()

    if not txt_files:
        print(f"⚠️  Nenhum arquivo TXT encontrado em {SOURCE_DIR}")
        return

    print(f"\n📁 Arquivos TXT encontrados: {len(txt_files)}")

    # Agrupa por pasta (FC13, FC14, FC17)
    by_folder = {}
    for txt_path in txt_files:
        folder = Path(txt_path).parent.name
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(txt_path)

    print("\n📊 Distribuição por pasta:")
    for folder, files in sorted(by_folder.items()):
        print(f"   {folder}: {len(files)} arquivos")

    # Mostra exemplos
    print("\n📄 Exemplos de arquivos:")
    for txt_path in txt_files[:5]:
        print(f"   {Path(txt_path).name}")
    if len(txt_files) > 5:
        print(f"   ... e mais {len(txt_files) - 5} arquivos")

    # Importação automática
    print(f"\n⚠️  Iniciando importação via endpoint /api/sep-folder/import")
    print(f"   Servidor: {BASE_URL}")
    print(f"   Pasta fonte: {SOURCE_DIR}")

    # Executa importação
    result = import_sep_folder(str(SOURCE_DIR), txt_files)

    if result:
        print("\n" + "=" * 80)
        print("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print("\n💡 Próximos passos:")
        print("   1. Verificar os dados importados na aplicação")
        print("   2. Gerar o Excel do separador com os novos dados")
        print("   3. Validar as medições horárias")
    else:
        print("\n" + "=" * 80)
        print("❌ IMPORTAÇÃO FALHOU!")
        print("=" * 80)
        print("\n💡 Verifique:")
        print("   1. Se o servidor está rodando (http://127.0.0.1:8765)")
        print("   2. Se os arquivos TXT estão no formato correto")
        print("   3. Os logs de erro acima")


if __name__ == "__main__":
    main()
