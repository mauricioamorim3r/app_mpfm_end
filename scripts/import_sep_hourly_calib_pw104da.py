"""
Importa arquivos TXT horárias de separador da pasta Calib PW104DA.

Usa a função interna process_file_list() para bypass do scanner sep_folder,
que rejeita arquivos "Run_Hourly" (procura apenas "run_24hours").

Arquivos disponíveis:
- FC13 - 27_08_2026: 18 arquivos TXT (óleo - 20FT0247)
- FC14 - 27_08_2026: 18 arquivos TXT (água - 20FT0251)
- FC17 - 27_08_2026: 18 arquivos TXT (gás - 20FT0244)

Uso:
    py -3 scripts/import_sep_hourly_calib_pw104da.py
"""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import sqlite3
from app_config import DB_PATH, DEFAULT_DENSITY
from server import process_file_list

SOURCE_DIR = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM/3.1 Registros Diarios MPFM/Zip/Calib PW104DA/Calib PW104DA")


def scan_txt_files():
    """Escaneia recursivamente os arquivos TXT na pasta fonte."""
    txt_files = []
    for txt_path in SOURCE_DIR.rglob("*.txt"):
        if txt_path.is_file():
            txt_files.append(txt_path)
    return sorted(txt_files, key=lambda p: (p.parent.name, p.name))


def main():
    print("=" * 80)
    print("IMPORTAÇÃO DIRETA DE TXT HORÁRIOS - CALIB PW104DA")
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
        folder = txt_path.parent.name
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(txt_path)

    print("\n📊 Distribuição por pasta:")
    for folder, files in sorted(by_folder.items()):
        print(f"   {folder}: {len(files)} arquivos")

    # Mostra exemplos
    print("\n📄 Exemplos de arquivos:")
    for txt_path in txt_files[:5]:
        print(f"   {txt_path.relative_to(SOURCE_DIR)}")
    if len(txt_files) > 5:
        print(f"   ... e mais {len(txt_files) - 5} arquivos")

    # Prepara lista de (path, name) para process_file_list
    pairs = [(txt_path, txt_path.name) for txt_path in txt_files]

    print(f"\n📤 Iniciando importação direta via process_file_list...")
    print(f"   Total de arquivos: {len(pairs)}")
    print(f"   Densidade padrão: {DEFAULT_DENSITY}")

    try:
        result = process_file_list(
            pairs,
            DEFAULT_DENSITY,
            source_type="sep-hourly-calib-pw104da",
            source_ref=str(SOURCE_DIR),
            force_overwrite=False
        )

        print(f"\n✅ Importação concluída!")
        print(f"   Processados: {result.get('processed', 0)}")
        print(f"   Ignorados: {result.get('skipped', 0)}")

        if result.get("log"):
            print(f"\n📋 Log:")
            for line in result["log"]:
                print(f"   {line}")

        print("\n" + "=" * 80)
        print("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print("\n💡 Próximos passos:")
        print("   1. Verificar os dados importados na aplicação")
        print("   2. Consultar API: GET /api/sep/data?date_from=2026-08-27&date_to=2026-08-27")
        print("   3. Gerar o Excel do separador com os novos dados")
        print("   4. Validar as medições horárias")

    except Exception as e:
        print(f"\n❌ Erro durante importação: {e}")
        import traceback
        traceback.print_exc()

        print("\n" + "=" * 80)
        print("❌ IMPORTAÇÃO FALHOU!")
        print("=" * 80)
        print("\n💡 Verifique:")
        print("   1. Se o banco de dados está acessível")
        print("   2. Se os arquivos TXT estão no formato correto")
        print("   3. Os logs de erro acima")


if __name__ == "__main__":
    main()
