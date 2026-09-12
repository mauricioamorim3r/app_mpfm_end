"""
Diagnóstico de lentidão no carregamento de arquivos TXT do separador.

Mede o tempo de iteração sobre arquivos TXT em pastas Daily Reports
e identifica possíveis gargalos.

Uso:
    py -3 scripts/diagnostico_lentidao_sep.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import time

BASE_PATH = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 01 FPSO Bacalhau - Metering Management/03 REPORTS/00 - Daily Reports/2026/08. Agosto")

DAYS_TO_TEST = [
    "FPSO-Bacalhau_Daily reports_2026-08-25",
    "FPSO-Bacalhau_Daily reports_2026-08-26",
    "FPSO-Bacalhau_Daily reports_2026-08-27",
]


def test_rglob_performance(folder_path):
    """Testa performance de rglob sobre arquivos TXT."""
    print(f"\n{'='*80}")
    print(f"Testando: {folder_path.name}")
    print(f"{'='*80}")

    # Teste 1: rglob("*.txt") - o que o scanner faz
    start = time.time()
    txt_files = list(folder_path.rglob("*.txt"))
    elapsed_rglob = time.time() - start
    print(f"\n1️⃣  rglob('*.txt')")
    print(f"   Arquivos encontrados: {len(txt_files)}")
    print(f"   Tempo: {elapsed_rglob:.2f}s")

    # Teste 2: Filtrar por nome (Run_24Hours)
    start = time.time()
    run_24h = [f for f in txt_files if "run_24hours" in f.name.lower()]
    elapsed_filter = time.time() - start
    print(f"\n2️⃣  Filtrar Run_24Hours do resultado")
    print(f"   Run_24Hours: {len(run_24h)}")
    print(f"   Tempo: {elapsed_filter:.3f}s")

    # Teste 3: Acessar .is_file() de cada arquivo
    start = time.time()
    file_checks = sum(1 for f in txt_files[:100] if f.is_file())
    elapsed_isfile = time.time() - start
    print(f"\n3️⃣  Verificar .is_file() (primeiros 100)")
    print(f"   Arquivos válidos: {file_checks}")
    print(f"   Tempo: {elapsed_isfile:.2f}s")
    print(f"   Tempo estimado para {len(txt_files)}: {elapsed_isfile * len(txt_files) / 100:.2f}s")

    # Teste 4: Ler tamanho de alguns arquivos
    start = time.time()
    sizes = [f.stat().st_size for f in txt_files[:10]]
    elapsed_stat = time.time() - start
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    print(f"\n4️⃣  Ler .stat().st_size (primeiros 10)")
    print(f"   Tamanho médio: {avg_size / 1024:.1f} KB")
    print(f"   Tempo: {elapsed_stat:.3f}s")
    print(f"   Tempo estimado para {len(txt_files)}: {elapsed_stat * len(txt_files) / 10:.2f}s")

    # Resumo
    total_estimated = elapsed_rglob + elapsed_filter + (elapsed_isfile * len(txt_files) / 100)
    print(f"\n📊 RESUMO")
    print(f"   Tempo total de scan estimado: {total_estimated:.2f}s")
    print(f"   Gargalo: ", end="")
    if elapsed_rglob > 10:
        print("rglob (OneDrive sync?)")
    elif (elapsed_isfile * len(txt_files) / 100) > 10:
        print(".is_file() em massa (I/O)")
    else:
        print("Normal")

    return {
        "total_files": len(txt_files),
        "run_24h": len(run_24h),
        "rglob_time": elapsed_rglob,
        "filter_time": elapsed_filter,
        "isfile_time_estimated": elapsed_isfile * len(txt_files) / 100,
        "total_estimated": total_estimated,
    }


def main():
    print("="*80)
    print("DIAGNÓSTICO DE LENTIDÃO - SEPARADOR TXT")
    print("="*80)
    print("\nO scanner sep_folder_scan_service.py usa:")
    print("  1. rglob('*.txt') para encontrar todos os arquivos")
    print("  2. Verifica se 'run_24hours' está no nome (rejeita Run_Hourly)")
    print("  3. Chama .is_file() em cada arquivo")
    print("\nVamos medir cada etapa para identificar o gargalo...")

    results = []
    for day_name in DAYS_TO_TEST:
        folder = BASE_PATH / day_name
        if not folder.exists():
            print(f"\n⚠️  Pasta não encontrada: {day_name}")
            continue

        try:
            result = test_rglob_performance(folder)
            results.append((day_name, result))
        except Exception as e:
            print(f"\n❌ Erro ao processar {day_name}: {e}")

    # Comparação final
    print(f"\n{'='*80}")
    print("COMPARAÇÃO ENTRE OS 3 DIAS")
    print(f"{'='*80}")

    for day_name, result in results:
        print(f"\n{day_name}:")
        print(f"  Total TXT: {result['total_files']}")
        print(f"  Run_24Hours: {result['run_24h']}")
        print(f"  Tempo scan total: {result['total_estimated']:.2f}s")
        print(f"  Breakdown:")
        print(f"    - rglob: {result['rglob_time']:.2f}s")
        print(f"    - is_file checks: {result['isfile_time_estimated']:.2f}s")

    print(f"\n{'='*80}")
    print("CONCLUSÃO")
    print(f"{'='*80}")
    print("\nProblema identificado:")
    print("  O scanner itera sobre ~1982 arquivos TXT por dia")
    print("  Apenas 51 são Run_24Hours (aceitos)")
    print("  1224 são Run_Hourly (rejeitados)")
    print("  707 são outros TXT (Alarms/Events)")
    print("\nSoluções possíveis:")
    print("  1. Filtrar no rglob: usar glob('**/Run_24Hours*.txt')")
    print("  2. OneDrive: garantir que arquivos estão em 'Always Keep'")
    print("  3. Cache: manter lista de arquivos já escaneados")
    print("  4. Indexação: pré-processar estrutura de pastas")


if __name__ == "__main__":
    main()
