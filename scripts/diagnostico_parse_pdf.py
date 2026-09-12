"""
Diagnóstico de parse de PDFs e geração de Excel.

Mede o tempo para:
1. Ler e fazer parse de PDFs MPFM (operação pesada)
2. Processar dados com pandas
3. Gerar arquivo Excel

Uso:
    py -3 scripts/diagnostico_parse_pdf.py
"""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import time
from pypdf import PdfReader
import pandas as pd

MPFM_ROOT = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM/3.1 Registros Diarios MPFM")
BANK_FOLDER = "3.1.1_13-FT-0367 Riser P5 - Topside B03"  # Testar com B03
YEAR_MONTH = "08. Agosto"


def test_pdf_read_speed():
    """Testa velocidade de leitura de PDFs."""
    print("\n" + "="*80)
    print("TESTE 1: Velocidade de leitura de PDFs")
    print("="*80)

    hourly_dir = MPFM_ROOT / BANK_FOLDER / "2026" / YEAR_MONTH / "Hourly"

    if not hourly_dir.exists():
        print(f"❌ Pasta não encontrada: {hourly_dir}")
        return

    # Pega os primeiros 10 PDFs
    pdfs = list(hourly_dir.rglob("B03_MPFM_Hourly-*.pdf"))[:10]

    if not pdfs:
        print("❌ Nenhum PDF encontrado")
        return

    print(f"\nTestando leitura de {len(pdfs)} PDFs...")

    total_start = time.time()
    page_counts = []
    text_lengths = []

    for i, pdf_path in enumerate(pdfs, 1):
        try:
            start = time.time()

            # Ler PDF (operação pesada)
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)

            # Extrair texto (ainda mais pesado)
            text = ""
            for page in reader.pages:
                text += page.extract_text()

            elapsed = time.time() - start

            page_counts.append(num_pages)
            text_lengths.append(len(text))

            print(f"   PDF {i}: {num_pages} páginas, {len(text)} caracteres em {elapsed:.3f}s")

        except Exception as e:
            print(f"   PDF {i}: ❌ Erro - {e}")

    total_time = time.time() - total_start

    print(f"\n📊 RESUMO:")
    print(f"   Total de PDFs: {len(pdfs)}")
    print(f"   Tempo total: {total_time:.2f}s")
    print(f"   Tempo médio por PDF: {total_time / len(pdfs):.2f}s")
    print(f"   Páginas médias por PDF: {sum(page_counts) / len(page_counts):.1f}")

    # Extrapola para todos os 650 PDFs de um banco
    estimated_total = (total_time / len(pdfs)) * 650
    print(f"\n⏱️  EXTRAPOLAÇÃO:")
    print(f"   Para 650 PDFs hourly de B03: ~{estimated_total:.1f}s ({estimated_total/60:.1f} min)")
    print(f"   Para 6 bancos (3900 PDFs): ~{estimated_total * 6:.1f}s ({estimated_total * 6 / 60:.1f} min)")

    if estimated_total > 60:
        print(f"\n🔴 GARGALO IDENTIFICADO!")
        print(f"   Parse de PDFs é MUITO LENTO!")
        print(f"   Leva ~{estimated_total/60:.1f} minutos só para processar os PDFs de um banco.")


def test_pandas_processing():
    """Testa velocidade de processamento pandas."""
    print("\n" + "="*80)
    print("TESTE 2: Velocidade de processamento pandas")
    print("="*80)

    print("\nCriando DataFrame simulado (27 dias x 24 horas x 6 bancos)...")

    start = time.time()

    # Simula dados de um mês: 27 dias, 24 horas, 6 bancos
    num_rows = 27 * 24 * 6  # 3888 linhas

    df = pd.DataFrame({
        "ProductionDate": ["2026-08-01"] * num_rows,
        "Hour": list(range(24)) * (num_rows // 24),
        "Bank": ["B03", "B08", "B13", "B05", "B10", "B15"] * (num_rows // 6),
        "Oil": [100.5] * num_rows,
        "Water": [50.2] * num_rows,
        "Gas": [75.8] * num_rows,
        "BSW": [35.1] * num_rows,
        "GOR": [150.3] * num_rows,
        "Pressure": [85.4] * num_rows,
        "Temperature": [65.2] * num_rows,
    })

    create_time = time.time() - start

    print(f"   DataFrame criado: {len(df)} linhas em {create_time:.3f}s")

    # Teste: operações típicas de processamento
    print("\nExecutando operações típicas...")

    start = time.time()
    grouped = df.groupby(["ProductionDate", "Bank"]).agg({
        "Oil": "sum",
        "Water": "sum",
        "Gas": "sum"
    })
    group_time = time.time() - start
    print(f"   GroupBy + Agregação: {group_time:.3f}s")

    start = time.time()
    merged = df.merge(df, on=["ProductionDate", "Hour", "Bank"], how="left", suffixes=("_1", "_2"))
    merge_time = time.time() - start
    print(f"   Merge com si mesmo: {merge_time:.3f}s ({len(merged)} linhas)")

    start = time.time()
    sorted_df = df.sort_values(["ProductionDate", "Bank", "Hour"])
    sort_time = time.time() - start
    print(f"   Sort: {sort_time:.3f}s")

    total_pandas = group_time + merge_time + sort_time

    print(f"\n⏱️  TOTAL pandas: {total_pandas:.3f}s")

    if total_pandas > 1.0:
        print("⚠️  Processamento pandas moderadamente lento")
    else:
        print("✅ Processamento pandas rápido")


def test_excel_write():
    """Testa velocidade de escrita de Excel."""
    print("\n" + "="*80)
    print("TESTE 3: Velocidade de escrita de Excel")
    print("="*80)

    # Cria DataFrame grande simulado
    num_rows = 10000  # 10k linhas (típico de um relatório mensal)

    df = pd.DataFrame({
        f"Col_{i}": [f"Value_{i}_{j}" for j in range(num_rows)]
        for i in range(20)  # 20 colunas
    })

    print(f"\nCriando Excel com {len(df)} linhas e {len(df.columns)} colunas...")

    output_path = "AUTOMACAO_HTML/HTML_GERADOS/teste_performance.xlsx"

    start = time.time()
    df.to_excel(output_path, index=False, engine="openpyxl")
    write_time = time.time() - start

    # Tamanho do arquivo
    file_size = Path(output_path).stat().st_size / 1024  # KB

    print(f"   Excel criado: {file_size:.1f} KB em {write_time:.2f}s")

    # Cleanup
    Path(output_path).unlink()

    print(f"\n⏱️  Tempo de escrita: {write_time:.2f}s")

    if write_time > 5.0:
        print("🔴 Escrita de Excel é LENTA!")
    elif write_time > 2.0:
        print("⚠️  Escrita de Excel moderadamente lenta")
    else:
        print("✅ Escrita de Excel rápida")


def main():
    print("="*80)
    print("DIAGNÓSTICO DE PARSE DE PDFs E GERAÇÃO DE EXCEL")
    print("="*80)

    print("\nEste diagnóstico mede as operações PESADAS:")
    print("  1. Parse de PDFs (pypdf.PdfReader + extract_text)")
    print("  2. Processamento pandas (groupby, merge, sort)")
    print("  3. Escrita de Excel (openpyxl)")
    print("\nEstas são as operações que REALMENTE demoram,")
    print("não o scan de arquivos (que já vimos que está rápido).")

    try:
        test_pdf_read_speed()
    except Exception as e:
        print(f"\n❌ Erro no teste de PDF: {e}")
        import traceback
        traceback.print_exc()

    try:
        test_pandas_processing()
    except Exception as e:
        print(f"\n❌ Erro no teste pandas: {e}")
        import traceback
        traceback.print_exc()

    try:
        test_excel_write()
    except Exception as e:
        print(f"\n❌ Erro no teste de Excel: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("CONCLUSÃO")
    print("="*80)

    print("\nSe o parse de PDFs está demorando >1 min por banco:")
    print("  - Considere cache dos PDFs já processados")
    print("  - Ou processamento paralelo com multiprocessing")
    print("  - Ou pré-processar PDFs em batch offline")

    print("\nSe a geração de Excel está demorando >5s:")
    print("  - Use engine='xlsxwriter' em vez de openpyxl")
    print("  - Ou gere CSV em vez de Excel quando possível")


if __name__ == "__main__":
    main()
