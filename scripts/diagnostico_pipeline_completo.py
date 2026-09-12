"""
Diagnóstico completo do pipeline de import + geração de Excel.

Simula o fluxo real da aplicação para os últimos 3 dias e identifica
onde está o gargalo de performance.

Uso:
    py -3 scripts/diagnostico_pipeline_completo.py
"""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import time
import sqlite3
from app_config import DB_PATH

BASE_PATH = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 01 FPSO Bacalhau - Metering Management/03 REPORTS/00 - Daily Reports/2026/08. Agosto")

DAYS_TO_TEST = [
    "FPSO-Bacalhau_Daily reports_2026-08-25",
    "FPSO-Bacalhau_Daily reports_2026-08-26",
    "FPSO-Bacalhau_Daily reports_2026-08-27",
]


def time_operation(name, func):
    """Executa operação e mede tempo."""
    start = time.time()
    result = func()
    elapsed = time.time() - start
    return elapsed, result


def test_pdf_scan(folder_path):
    """Testa scan de arquivos PDF."""
    def scan():
        pdf_files = list(folder_path.rglob("*.pdf"))
        return len(pdf_files)

    elapsed, count = time_operation("PDF scan", scan)
    return {"count": count, "time": elapsed}


def test_txt_scan(folder_path):
    """Testa scan de arquivos TXT."""
    def scan():
        txt_files = list(folder_path.rglob("*.txt"))
        run_24h = [f for f in txt_files if "run_24hours" in f.name.lower()]
        return {"total": len(txt_files), "run_24h": len(run_24h)}

    elapsed, counts = time_operation("TXT scan", scan)
    return {**counts, "time": elapsed}


def test_db_query_measurements(date_str):
    """Testa consulta de medições no banco."""
    def query():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Query similar ao que a aplicação faz
        result = cur.execute(
            "SELECT COUNT(*) FROM measurements_curated WHERE day_ref = ?",
            (date_str,)
        ).fetchone()

        conn.close()
        return result[0] if result else 0

    elapsed, count = time_operation(f"DB query {date_str}", query)
    return {"count": count, "time": elapsed}


def test_db_query_sep(date_str):
    """Testa consulta de separador no banco."""
    def query():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Query similar ao que a aplicação faz
        result = cur.execute(
            "SELECT COUNT(*) FROM sep_measurements WHERE DATE(start_time) = ?",
            (date_str,)
        ).fetchone()

        conn.close()
        return result[0] if result else 0

    elapsed, count = time_operation(f"SEP query {date_str}", query)
    return {"count": count, "time": elapsed}


def test_full_day_pipeline(folder_path, date_str):
    """Testa pipeline completo de um dia."""
    print(f"\n{'='*80}")
    print(f"Pipeline completo: {folder_path.name}")
    print(f"{'='*80}")

    total_start = time.time()

    # Etapa 1: Scan PDF
    print("\n1️⃣  Escaneando PDFs...")
    pdf_result = test_pdf_scan(folder_path)
    print(f"   PDFs encontrados: {pdf_result['count']}")
    print(f"   Tempo: {pdf_result['time']:.2f}s")

    # Etapa 2: Scan TXT
    print("\n2️⃣  Escaneando TXTs...")
    txt_result = test_txt_scan(folder_path)
    print(f"   TXTs total: {txt_result['total']}")
    print(f"   Run_24Hours: {txt_result['run_24h']}")
    print(f"   Tempo: {txt_result['time']:.2f}s")

    # Etapa 3: Consultar banco - MPFM
    print("\n3️⃣  Consultando banco - MPFM...")
    mpfm_result = test_db_query_measurements(date_str)
    print(f"   Registros MPFM: {mpfm_result['count']}")
    print(f"   Tempo: {mpfm_result['time']:.3f}s")

    # Etapa 4: Consultar banco - SEP
    print("\n4️⃣  Consultando banco - SEP...")
    sep_result = test_db_query_sep(date_str)
    print(f"   Registros SEP: {sep_result['count']}")
    print(f"   Tempo: {sep_result['time']:.3f}s")

    # Etapa 5: Simular comparação disco vs banco
    print("\n5️⃣  Comparando disco vs banco (simulado)...")
    compare_start = time.time()

    # Encontrar PDFs que precisariam ser importados
    # (simplificado - não faz a comparação real)
    pending = max(0, pdf_result['count'] - (mpfm_result['count'] // 24))

    compare_time = time.time() - compare_start
    print(f"   Arquivos pendentes estimados: {pending}")
    print(f"   Tempo: {compare_time:.3f}s")

    total_time = time.time() - total_start

    print(f"\n⏱️  TEMPO TOTAL: {total_time:.2f}s")

    # Identificar gargalo
    steps = [
        ("Scan PDF", pdf_result['time']),
        ("Scan TXT", txt_result['time']),
        ("Query MPFM", mpfm_result['time']),
        ("Query SEP", sep_result['time']),
        ("Comparação", compare_time),
    ]

    slowest = max(steps, key=lambda x: x[1])
    print(f"\n🔴 Gargalo: {slowest[0]} ({slowest[1]:.2f}s)")

    return {
        "date": date_str,
        "total_time": total_time,
        "pdf": pdf_result,
        "txt": txt_result,
        "mpfm_db": mpfm_result,
        "sep_db": sep_result,
        "compare_time": compare_time,
        "bottleneck": slowest[0],
    }


def main():
    print("="*80)
    print("DIAGNÓSTICO COMPLETO - PIPELINE IMPORT + EXCEL")
    print("="*80)

    print("\nEste diagnóstico simula o fluxo completo da aplicação:")
    print("  1. Scan de PDFs na pasta Daily Reports")
    print("  2. Scan de TXTs (separador)")
    print("  3. Consulta ao banco de dados (MPFM)")
    print("  4. Consulta ao banco de dados (SEP)")
    print("  5. Comparação disco vs banco (para identificar pendentes)")
    print("\nMedindo performance dos últimos 3 dias...")

    results = []

    for day_name in DAYS_TO_TEST:
        folder = BASE_PATH / day_name
        if not folder.exists():
            print(f"\n⚠️  Pasta não encontrada: {day_name}")
            continue

        # Extrai data do nome da pasta: FPSO-Bacalhau_Daily reports_2026-08-27
        date_str = day_name.split("_")[-1]  # 2026-08-27

        try:
            result = test_full_day_pipeline(folder, date_str)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Erro ao processar {day_name}: {e}")
            import traceback
            traceback.print_exc()

    # Comparação final
    print(f"\n{'='*80}")
    print("COMPARAÇÃO ENTRE OS 3 DIAS")
    print(f"{'='*80}")

    for result in results:
        print(f"\n{result['date']}:")
        print(f"  Tempo total: {result['total_time']:.2f}s")
        print(f"  PDFs: {result['pdf']['count']} arquivos ({result['pdf']['time']:.2f}s)")
        print(f"  TXTs: {result['txt']['total']} arquivos ({result['txt']['time']:.2f}s)")
        print(f"  Banco MPFM: {result['mpfm_db']['count']} registros ({result['mpfm_db']['time']:.3f}s)")
        print(f"  Banco SEP: {result['sep_db']['count']} registros ({result['sep_db']['time']:.3f}s)")
        print(f"  🔴 Gargalo: {result['bottleneck']}")

    # Análise de tendência
    print(f"\n{'='*80}")
    print("ANÁLISE DE TENDÊNCIA")
    print(f"{'='*80}")

    if len(results) >= 2:
        first = results[0]
        last = results[-1]

        delta = last['total_time'] - first['total_time']
        pct = (delta / first['total_time'] * 100) if first['total_time'] > 0 else 0

        print(f"\nTempo de pipeline:")
        print(f"  {first['date']}: {first['total_time']:.2f}s")
        print(f"  {last['date']}: {last['total_time']:.2f}s")
        print(f"  Diferença: {delta:+.2f}s ({pct:+.1f}%)")

        if abs(pct) > 20:
            print(f"\n⚠️  ALERTA: Variação significativa de {pct:.1f}%!")
        else:
            print(f"\n✅ Variação normal (< 20%)")

    print(f"\n{'='*80}")
    print("CONCLUSÃO")
    print(f"{'='*80}")

    avg_total = sum(r['total_time'] for r in results) / len(results) if results else 0
    avg_pdf = sum(r['pdf']['time'] for r in results) / len(results) if results else 0
    avg_txt = sum(r['txt']['time'] for r in results) / len(results) if results else 0

    print(f"\nMédia de tempo por dia:")
    print(f"  Total: {avg_total:.2f}s")
    print(f"  Scan PDF: {avg_pdf:.2f}s")
    print(f"  Scan TXT: {avg_txt:.2f}s")

    print("\nRecomendações:")
    if avg_txt > 1.0:
        print("  1. Otimizar scan TXT: usar glob específico '**/Run_24Hours*.txt'")
    if avg_pdf > 2.0:
        print("  2. Otimizar scan PDF: considerar cache de lista de arquivos")
    if avg_total > 5.0:
        print("  3. Pipeline lento: considerar processamento assíncrono")
    else:
        print("  ✅ Pipeline está performando adequadamente")

    print(f"\nNota: Este diagnóstico NÃO inclui:")
    print("  - Leitura real do conteúdo dos arquivos")
    print("  - Parse de PDFs/TXTs")
    print("  - Insert no banco de dados")
    print("  - Geração de Excel")
    print("\nSe a lentidão persiste, o gargalo está em uma dessas etapas adicionais.")


if __name__ == "__main__":
    main()
