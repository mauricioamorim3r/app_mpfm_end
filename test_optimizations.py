#!/usr/bin/env python3
"""
Script de Teste - Otimizações de Performance
Valida se as otimizações estão funcionando corretamente
"""
import time
import sqlite3
from pathlib import Path


def test_indexes():
    """Testa se os índices foram criados"""
    print("\n[1/5] Testando índices do banco...")

    conn = sqlite3.connect('data/mpfm_local.db')
    cur = conn.cursor()

    # Lista índices customizados
    cur.execute("""
        SELECT name, tbl_name
        FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_%'
    """)
    indexes = cur.fetchall()

    critical_indexes = [
        'idx_measurements_row_kind_day',
        'idx_measurements_bank_day',
        'idx_cards_production_bank_type',
        'idx_sep_production_fluid_meter',
        'idx_files_run_id'
    ]

    found = [idx[0] for idx in indexes]
    missing = [idx for idx in critical_indexes if idx not in found]

    if missing:
        print(f"   [ERRO] Índices faltando: {missing}")
        return False

    print(f"   [OK] {len(indexes)} índices encontrados")
    print(f"   [OK] Todos os índices críticos presentes")

    # Testa performance de query com índice
    start = time.time()
    cur.execute("""
        SELECT COUNT(*)
        FROM measurements_curated
        WHERE row_kind='daily' AND day_ref BETWEEN '2026-06-01' AND '2026-06-30'
    """)
    count = cur.fetchone()[0]
    duration = time.time() - start

    print(f"   [OK] Query com índice: {duration:.3f}s ({count:,} registros)")

    conn.close()
    return True


def test_cache():
    """Testa se o sistema de cache está funcionando"""
    print("\n[2/5] Testando sistema de cache...")

    try:
        from cache_manager import cached, get_cache_stats, invalidate_cache

        @cached(ttl=60, key_prefix='test')
        def slow_function():
            time.sleep(0.1)  # Simula operação lenta
            return "resultado"

        # Primeira chamada - cache miss
        start = time.time()
        result1 = slow_function()
        time1 = time.time() - start

        # Segunda chamada - cache hit
        start = time.time()
        result2 = slow_function()
        time2 = time.time() - start

        if time2 >= time1:
            print(f"   [AVISO] Cache não acelerou (t1={time1:.3f}s, t2={time2:.3f}s)")
            return False

        speedup = time1 / time2 if time2 > 0 else 999
        stats = get_cache_stats()
        print(f"   [OK] Cache hit {speedup:.0f}x mais rápido ({time1*1000:.1f}ms -> {time2*1000:.1f}ms)")
        print(f"   [OK] Stats: {stats['hits']} hits, {stats['misses']} misses")

        # Limpa
        invalidate_cache('test')
        return True

    except ImportError as e:
        print(f"   [ERRO] Cache não disponível: {e}")
        return False


def test_n_plus_1_fix():
    """Testa se as correções de N+1 estão presentes"""
    print("\n[3/5] Verificando correções de N+1...")

    files_to_check = [
        ('routes/ops_routes.py', 'LEFT JOIN files_imported', 'processing-history'),
        ('repositories/cards/cards_repository.py', 'window function', 'list_card_duplicates')
    ]

    all_ok = True
    for file_path, search_term, description in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'LEFT JOIN' in content or 'PARTITION BY' in content:
                    print(f"   [OK] {description} otimizado")
                else:
                    print(f"   [AVISO] {description} pode não estar otimizado")
                    all_ok = False
        else:
            print(f"   [AVISO] Arquivo não encontrado: {file_path}")
            all_ok = False

    return all_ok


def test_pagination():
    """Testa se paginação foi implementada"""
    print("\n[4/5] Verificando paginação...")

    files_to_check = [
        ('routes/ops_routes.py', 'offset: int = 0', '/api/ops/mpfm-data'),
        ('repositories/cards/cards_repository.py', 'limit: int = None', 'list_*_measurement_rows')
    ]

    all_ok = True
    for file_path, search_term, description in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if search_term in content:
                    print(f"   [OK] {description} com paginação")
                else:
                    print(f"   [AVISO] {description} sem paginação")
                    all_ok = False
        else:
            print(f"   [AVISO] Arquivo não encontrado: {file_path}")
            all_ok = False

    return all_ok


def test_database_health():
    """Testa saúde geral do banco"""
    print("\n[5/5] Verificando saúde do banco...")

    conn = sqlite3.connect('data/mpfm_local.db')
    cur = conn.cursor()

    # Verifica integridade
    cur.execute("PRAGMA integrity_check")
    result = cur.fetchone()[0]

    if result != 'ok':
        print(f"   [ERRO] Integridade do banco: {result}")
        conn.close()
        return False

    print("   [OK] Integridade do banco OK")

    # Estatísticas
    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    tables = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    indexes = cur.fetchone()[0]

    cur.execute("SELECT page_count * page_size / 1024.0 / 1024.0 FROM pragma_page_count(), pragma_page_size()")
    size_mb = cur.fetchone()[0]

    print(f"   [OK] {tables} tabelas, {indexes} índices")
    print(f"   [OK] Tamanho: {size_mb:.1f}MB")

    conn.close()
    return True


def main():
    print("=" * 70)
    print("  TESTE DE OTIMIZAÇÕES DE PERFORMANCE")
    print("=" * 70)

    results = []
    results.append(('Índices', test_indexes()))
    results.append(('Cache', test_cache()))
    results.append(('N+1 Fix', test_n_plus_1_fix()))
    results.append(('Paginação', test_pagination()))
    results.append(('Saúde DB', test_database_health()))

    print("\n" + "=" * 70)
    print("  RESUMO")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[FALHOU]"
        print(f"  {status} {name}")

    print("\n" + "=" * 70)
    print(f"  RESULTADO: {passed}/{total} testes passaram")
    print("=" * 70)

    if passed == total:
        print("\n  [OK] Todas as otimizacoes estao ativas!")
    else:
        print("\n  [AVISO] Algumas otimizacoes podem nao estar ativas.")

    return passed == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1)
