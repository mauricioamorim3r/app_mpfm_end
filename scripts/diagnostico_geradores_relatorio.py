"""
Diagnóstico de performance dos geradores de relatórios.

Mede o tempo de operações críticas nos scripts de geração:
- gerar_base_unica_standalone.py
- preencher_petec.py

Identifica gargalos específicos nos últimos 3 dias.

Uso:
    py -3 scripts/diagnostico_geradores_relatorio.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import time

# Caminhos base
DAILY_REPORTS = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 01 FPSO Bacalhau - Metering Management/03 REPORTS/00 - Daily Reports/2026/08. Agosto")
MPFM_ROOT = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM/3.1 Registros Diarios MPFM")

DAYS_TO_TEST = [
    ("2026-08-25", "FPSO-Bacalhau_Daily reports_2026-08-25"),
    ("2026-08-26", "FPSO-Bacalhau_Daily reports_2026-08-26"),
    ("2026-08-27", "FPSO-Bacalhau_Daily reports_2026-08-27"),
]

BANK_FOLDERS = {
    "B03": "3.1.1_13-FT-0367 Riser P5 - Topside B03",
    "B08": "3.1.2_13-FT-0167 Riser P2 - Topside B08",
    "B13": "3.1.3_13-FT-0317 Riser P4 - Topside B13",
    "B05": "3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05",
    "B10": "3.1.5_18-FT-0506 PE 2 - Subsea B10",
    "B15": "3.1.6_18-FT-1106 PW_104DA - Subsea B15",
}


def test_rglob_hourly_pdfs(bank_code, year_month):
    """
    Simula o rglob que o script Base Única faz para encontrar PDFs hourly.

    Linha 3178 do script:
        for pdf_path in hourly_dir.rglob(f"{bank_code}_MPFM_Hourly-*.pdf"):

    Este é um dos gargalos potenciais porque rglob é RECURSIVO.
    """
    bank_folder = BANK_FOLDERS.get(bank_code)
    if not bank_folder:
        return {"time": 0, "count": 0, "error": "Bank não configurado"}

    bank_root = MPFM_ROOT / bank_folder
    if not bank_root.exists():
        return {"time": 0, "count": 0, "error": "Pasta não encontrada"}

    # Estrutura: bank_root / 2026 / 08. Agosto / Hourly
    hourly_dir = bank_root / "2026" / year_month / "Hourly"

    if not hourly_dir.exists():
        return {"time": 0, "count": 0, "error": "Hourly dir não existe"}

    start = time.time()
    pdfs = list(hourly_dir.rglob(f"{bank_code}_MPFM_Hourly-*.pdf"))
    elapsed = time.time() - start

    return {"time": elapsed, "count": len(pdfs), "error": None}


def test_glob_daily_pdfs(bank_code, year_month):
    """
    Simula o glob que o script Base Única faz para encontrar PDFs daily.

    Linha 3133 do script:
        for path in daily_dir.glob(f"{bank_code}_MPFM_Daily-*.pdf"):

    glob (não recursivo) deve ser mais rápido.
    """
    bank_folder = BANK_FOLDERS.get(bank_code)
    if not bank_folder:
        return {"time": 0, "count": 0, "error": "Bank não configurado"}

    bank_root = MPFM_ROOT / bank_folder
    if not bank_root.exists():
        return {"time": 0, "count": 0, "error": "Pasta não encontrada"}

    daily_dir = bank_root / "2026" / year_month / "Daily"

    if not daily_dir.exists():
        return {"time": 0, "count": 0, "error": "Daily dir não existe"}

    start = time.time()
    pdfs = list(daily_dir.glob(f"{bank_code}_MPFM_Daily-*.pdf"))
    elapsed = time.time() - start

    return {"time": elapsed, "count": len(pdfs), "error": None}


def test_sep_txt_scan(date_str, folder_name):
    """
    Simula o scan de TXTs do separador no Daily Reports.

    Linha 3225 do script:
        for txt_path in day_dir.glob("Run_24Hours*.txt"):
    """
    day_dir = DAILY_REPORTS / folder_name / "01 - CV_Reports"

    if not day_dir.exists():
        return {"time": 0, "fc_counts": {}, "total": 0, "error": "Daily Reports dir não existe"}

    start = time.time()

    fc_counts = {}
    total = 0

    # Para cada Flow Computer (FC13, FC14, FC17)
    for fc in ["FC13", "FC14", "FC17"]:
        fc_dir = day_dir / fc
        if fc_dir.exists():
            txts = list(fc_dir.glob("Run_24Hours*.txt"))
            fc_counts[fc] = len(txts)
            total += len(txts)

    elapsed = time.time() - start

    return {"time": elapsed, "fc_counts": fc_counts, "total": total, "error": None}


def test_events_rglob(date_str, folder_name):
    """
    Simula o rglob recursivo para arquivos de eventos.

    Linhas 3388-3390 do script:
        candidates.extend(year_dir.rglob("*.txt"))
        candidates.extend(year_dir.rglob("*.pdf"))

    Este é MUITO PERIGOSO porque faz rglob em pastas enormes.
    """
    day_dir = DAILY_REPORTS / folder_name

    if not day_dir.exists():
        return {"time": 0, "txt_count": 0, "pdf_count": 0, "error": "Dir não existe"}

    start = time.time()
    txts = list(day_dir.rglob("*.txt"))
    txt_time = time.time() - start

    start = time.time()
    pdfs = list(day_dir.rglob("*.pdf"))
    pdf_time = time.time() - start

    total_time = txt_time + pdf_time

    return {
        "time": total_time,
        "txt_time": txt_time,
        "pdf_time": pdf_time,
        "txt_count": len(txts),
        "pdf_count": len(pdfs),
        "error": None
    }


def test_day(date_str, folder_name, year_month):
    """Testa todas as operações de scan para um dia."""
    print(f"\n{'='*80}")
    print(f"Testando: {date_str}")
    print(f"{'='*80}")

    results = {
        "date": date_str,
        "daily_pdfs": {},
        "hourly_pdfs": {},
        "sep_txts": {},
        "events_rglob": {},
    }

    # 1. Scan Daily PDFs (glob não recursivo - deve ser rápido)
    print("\n1️⃣  Scan Daily PDFs (todos os bancos)...")
    daily_total_time = 0
    daily_total_count = 0
    for bank in BANK_FOLDERS.keys():
        result = test_glob_daily_pdfs(bank, year_month)
        results["daily_pdfs"][bank] = result
        if not result["error"]:
            daily_total_time += result["time"]
            daily_total_count += result["count"]
            print(f"   {bank}: {result['count']} PDFs em {result['time']:.3f}s")
        else:
            print(f"   {bank}: {result['error']}")

    print(f"   TOTAL: {daily_total_count} PDFs em {daily_total_time:.3f}s")

    # 2. Scan Hourly PDFs (rglob RECURSIVO - pode ser lento!)
    print("\n2️⃣  Scan Hourly PDFs - RGLOB RECURSIVO (todos os bancos)...")
    hourly_total_time = 0
    hourly_total_count = 0
    for bank in BANK_FOLDERS.keys():
        result = test_rglob_hourly_pdfs(bank, year_month)
        results["hourly_pdfs"][bank] = result
        if not result["error"]:
            hourly_total_time += result["time"]
            hourly_total_count += result["count"]
            print(f"   {bank}: {result['count']} PDFs em {result['time']:.3f}s")
        else:
            print(f"   {bank}: {result['error']}")

    print(f"   TOTAL: {hourly_total_count} PDFs em {hourly_total_time:.3f}s")

    # 3. Scan SEP TXTs (glob não recursivo)
    print("\n3️⃣  Scan SEP TXTs - Daily Reports...")
    sep_result = test_sep_txt_scan(date_str, folder_name)
    results["sep_txts"] = sep_result
    if not sep_result["error"]:
        print(f"   Total: {sep_result['total']} TXTs em {sep_result['time']:.3f}s")
        for fc, count in sep_result["fc_counts"].items():
            print(f"   {fc}: {count} TXTs")
    else:
        print(f"   {sep_result['error']}")

    # 4. Scan Events (rglob RECURSIVO - MUITO PERIGOSO!)
    print("\n4️⃣  Scan Events - RGLOB RECURSIVO EM PASTA DAILY REPORTS...")
    print("   ⚠️  ALERTA: Esta operação escaneia ~2000 arquivos por pasta!")
    events_result = test_events_rglob(date_str, folder_name)
    results["events_rglob"] = events_result
    if not events_result["error"]:
        print(f"   TXTs: {events_result['txt_count']} em {events_result['txt_time']:.2f}s")
        print(f"   PDFs: {events_result['pdf_count']} em {events_result['pdf_time']:.2f}s")
        print(f"   TOTAL: {events_result['time']:.2f}s")
    else:
        print(f"   {events_result['error']}")

    # Resumo
    total_time = (
        daily_total_time +
        hourly_total_time +
        sep_result.get("time", 0) +
        events_result.get("time", 0)
    )

    print(f"\n⏱️  TEMPO TOTAL DE SCAN: {total_time:.2f}s")

    # Identifica gargalo
    operations = [
        ("Daily PDFs glob", daily_total_time),
        ("Hourly PDFs rglob", hourly_total_time),
        ("SEP TXTs glob", sep_result.get("time", 0)),
        ("Events rglob", events_result.get("time", 0)),
    ]

    slowest = max(operations, key=lambda x: x[1])
    print(f"🔴 GARGALO: {slowest[0]} ({slowest[1]:.2f}s)")

    return results


def main():
    print("="*80)
    print("DIAGNÓSTICO DE GERADORES DE RELATÓRIO")
    print("="*80)

    print("\nEste diagnóstico mede operações de scan nos scripts:")
    print("  - gerar_base_unica_standalone.py")
    print("  - preencher_petec.py")
    print("\nOperações testadas:")
    print("  1. glob() para PDFs Daily (não recursivo)")
    print("  2. rglob() para PDFs Hourly (RECURSIVO)")
    print("  3. glob() para TXTs SEP em Daily Reports")
    print("  4. rglob() para eventos (RECURSIVO, PERIGOSO)")

    all_results = []

    for date_str, folder_name in DAYS_TO_TEST:
        year_month = "08. Agosto"
        try:
            result = test_day(date_str, folder_name, year_month)
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ Erro ao processar {date_str}: {e}")
            import traceback
            traceback.print_exc()

    # Comparação final
    print(f"\n{'='*80}")
    print("COMPARAÇÃO ENTRE OS 3 DIAS")
    print(f"{'='*80}")

    for result in all_results:
        date = result["date"]
        events = result["events_rglob"]

        total_scan_time = (
            sum(r.get("time", 0) for r in result["daily_pdfs"].values()) +
            sum(r.get("time", 0) for r in result["hourly_pdfs"].values()) +
            result["sep_txts"].get("time", 0) +
            events.get("time", 0)
        )

        print(f"\n{date}:")
        print(f"  Tempo total de scan: {total_scan_time:.2f}s")
        print(f"  Events rglob: {events.get('time', 0):.2f}s ({events.get('txt_count', 0)} TXT + {events.get('pdf_count', 0)} PDF)")

    # Análise final
    print(f"\n{'='*80}")
    print("CONCLUSÃO")
    print(f"{'='*80}")

    if all_results:
        avg_events_time = sum(r["events_rglob"].get("time", 0) for r in all_results) / len(all_results)

        print(f"\nMédia de tempo para rglob de eventos: {avg_events_time:.2f}s")

        if avg_events_time > 5.0:
            print("\n🔴 PROBLEMA IDENTIFICADO:")
            print("  O rglob recursivo para eventos está MUITO LENTO!")
            print(f"  Ele escaneia ~2000 arquivos por pasta Daily Reports.")
            print("\nSolução:")
            print("  Substituir rglob por glob não recursivo ou indexação prévia.")
        elif avg_events_time > 1.0:
            print("\n⚠️  AVISO:")
            print("  O rglob recursivo para eventos está moderadamente lento.")
            print("  Considere otimizar se a lentidão persistir.")
        else:
            print("\n✅ Performance adequada para scan de eventos.")


if __name__ == "__main__":
    main()
