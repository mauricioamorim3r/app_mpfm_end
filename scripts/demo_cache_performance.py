"""
Demonstração de ganho de performance com cache de PDFs.

Compara tempo de processamento COM e SEM cache.

Uso:
    py -3 scripts/demo_cache_performance.py
"""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import time
from pypdf import PdfReader
from services.pdf_cache_service import PDFCache

MPFM_ROOT = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM/3.1 Registros Diarios MPFM")
BANK_FOLDER = "3.1.1_13-FT-0367 Riser P5 - Topside B03"
YEAR_MONTH = "08. Agosto"


def parse_pdf_simple(pdf_path: Path) -> dict:
    """
    Função simples de parse de PDF.

    Extrai: número de páginas, texto completo, tamanho.
    """
    reader = PdfReader(pdf_path)

    text = ""
    for page in reader.pages:
        text += page.extract_text()

    return {
        "file": pdf_path.name,
        "num_pages": len(reader.pages),
        "text_length": len(text),
        "file_size": pdf_path.stat().st_size,
        "text_preview": text[:200] if text else "",
    }


def test_without_cache(pdf_paths: list[Path]) -> tuple[list, float]:
    """Testa parse SEM cache."""
    print("\n🔴 TESTE 1: SEM CACHE")
    print("="*60)

    results = []
    start = time.time()

    for i, pdf_path in enumerate(pdf_paths, 1):
        try:
            data = parse_pdf_simple(pdf_path)
            results.append(data)

            if i % 10 == 0:
                elapsed = time.time() - start
                print(f"   Processados: {i}/{len(pdf_paths)} ({elapsed:.1f}s)")

        except Exception as e:
            print(f"   ❌ Erro em {pdf_path.name}: {e}")

    elapsed = time.time() - start

    print(f"\n⏱️  Tempo total SEM cache: {elapsed:.2f}s")
    print(f"   Taxa: {len(pdf_paths) / elapsed:.2f} PDF/s")

    return results, elapsed


def test_with_cache(pdf_paths: list[Path], cache: PDFCache) -> tuple[list, float]:
    """Testa parse COM cache."""
    print("\n🟢 TESTE 2: COM CACHE")
    print("="*60)

    results = []
    start = time.time()

    for i, pdf_path in enumerate(pdf_paths, 1):
        try:
            # Usa cache
            data = cache.get_or_parse(pdf_path, parse_pdf_simple)
            results.append(data)

            if i % 10 == 0:
                elapsed = time.time() - start
                print(f"   Processados: {i}/{len(pdf_paths)} ({elapsed:.1f}s)")

        except Exception as e:
            print(f"   ❌ Erro em {pdf_path.name}: {e}")

    elapsed = time.time() - start

    print(f"\n⏱️  Tempo total COM cache: {elapsed:.2f}s")
    print(f"   Taxa: {len(pdf_paths) / elapsed:.2f} PDF/s")

    # Mostra estatísticas do cache
    stats = cache.get_stats()
    print(f"\n📊 Estatísticas do cache:")
    print(f"   Hits: {stats['hits']} ({stats['hit_rate_pct']}%)")
    print(f"   Misses: {stats['misses']}")
    print(f"   Erros: {stats['errors']}")

    return results, elapsed


def main():
    print("="*80)
    print("DEMONSTRAÇÃO DE GANHO DE PERFORMANCE COM CACHE")
    print("="*80)

    # Localiza PDFs
    hourly_dir = MPFM_ROOT / BANK_FOLDER / "2026" / YEAR_MONTH / "Hourly"

    if not hourly_dir.exists():
        print(f"❌ Pasta não encontrada: {hourly_dir}")
        return

    # Pega primeiros 50 PDFs para demonstração
    pdf_paths = list(hourly_dir.rglob("B03_MPFM_Hourly-*.pdf"))[:50]

    if not pdf_paths:
        print("❌ Nenhum PDF encontrado")
        return

    print(f"\n📁 Encontrados {len(pdf_paths)} PDFs para teste")
    print(f"   Pasta: {hourly_dir}")

    # Cria cache
    cache = PDFCache()

    # Limpa cache anterior para teste limpo
    removed = cache.clear()
    if removed > 0:
        print(f"\n🗑️  Cache limpo: {removed} arquivos removidos")

    print(f"\n📍 Cache localizado em: {cache.cache_dir}")

    # RODADA 1: Sem cache (baseline)
    results_no_cache, time_no_cache = test_without_cache(pdf_paths)

    # RODADA 2: Com cache (primeira vez = cache miss)
    print("\n" + "="*80)
    print("RODADA 2: Primeira execução com cache (populando cache)")
    print("="*80)

    cache.stats = {"hits": 0, "misses": 0, "errors": 0}  # Reset stats
    results_with_cache_1, time_with_cache_1 = test_with_cache(pdf_paths, cache)

    # RODADA 3: Com cache (segunda vez = cache hit!)
    print("\n" + "="*80)
    print("RODADA 3: Segunda execução com cache (usando cache)")
    print("="*80)

    cache.stats = {"hits": 0, "misses": 0, "errors": 0}  # Reset stats
    results_with_cache_2, time_with_cache_2 = test_with_cache(pdf_paths, cache)

    # Comparação final
    print("\n" + "="*80)
    print("COMPARAÇÃO FINAL")
    print("="*80)

    print(f"\n📊 Tempos medidos:")
    print(f"   Sem cache:                    {time_no_cache:.2f}s")
    print(f"   Com cache (1ª vez - miss):    {time_with_cache_1:.2f}s")
    print(f"   Com cache (2ª vez - hit):     {time_with_cache_2:.2f}s")

    speedup = time_no_cache / time_with_cache_2 if time_with_cache_2 > 0 else 0

    print(f"\n🚀 GANHO DE PERFORMANCE:")
    print(f"   Speedup: {speedup:.1f}x mais rápido")
    print(f"   Tempo economizado: {time_no_cache - time_with_cache_2:.2f}s")

    # Extrapolação
    total_pdfs = 3900  # 6 bancos x 650 PDFs
    time_no_cache_full = (time_no_cache / len(pdf_paths)) * total_pdfs
    time_with_cache_full = (time_with_cache_2 / len(pdf_paths)) * total_pdfs

    print(f"\n📈 EXTRAPOLAÇÃO para {total_pdfs} PDFs:")
    print(f"   Sem cache: {time_no_cache_full:.0f}s ({time_no_cache_full / 60:.1f} min)")
    print(f"   Com cache: {time_with_cache_full:.0f}s ({time_with_cache_full / 60:.1f} min)")
    print(f"   Economia: {(time_no_cache_full - time_with_cache_full) / 60:.1f} minutos!")

    print("\n" + "="*80)
    print("CONCLUSÃO")
    print("="*80)

    if speedup > 10:
        print(f"\n✅ Cache MUITO EFETIVO! ({speedup:.0f}x mais rápido)")
    elif speedup > 5:
        print(f"\n✅ Cache efetivo! ({speedup:.0f}x mais rápido)")
    elif speedup > 2:
        print(f"\n✅ Cache útil ({speedup:.0f}x mais rápido)")
    else:
        print(f"\n⚠️  Cache com ganho modesto ({speedup:.1f}x)")

    print("\n💡 Para usar em produção:")
    print("   1. Integre PDFCache no script gerar_base_unica_standalone.py")
    print("   2. Use cache.get_or_parse() em vez de parse direto")
    print("   3. Cache é automático - não precisa gerenciar manualmente")

    print(f"\n📁 Arquivos em cache: {len(list(cache.cache_dir.glob('*.cache.json')))}")
    print(f"   Localização: {cache.cache_dir}")
    print(f"   Para limpar: cache.clear()")


if __name__ == "__main__":
    main()
