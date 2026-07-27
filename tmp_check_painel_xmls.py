#!/usr/bin/env python3
"""Verifica se os XMLs do Painel do Operador (a001, a002, a003, a004) foram importados"""
import sqlite3
from pathlib import Path

db_path = Path("data/mpfm_local.db")
if not db_path.exists():
    print(f"Banco de dados não encontrado: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Listar todas as tabelas
print("=" * 80)
print("TABELAS NO BANCO DE DADOS")
print("=" * 80)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [r[0] for r in cur.fetchall()]
painel_tables = [t for t in all_tables if 'painel' in t.lower()]

print(f"\nTotal de tabelas: {len(all_tables)}")
print(f"\nTabelas do Painel do Operador:")
for t in painel_tables:
    print(f"  • {t}")

# Verificar se há dados nas tabelas do painel
print("\n" + "=" * 80)
print("DADOS DO PAINEL DO OPERADOR (XMLs a001-a004)")
print("=" * 80)

try:
    # Verificar painel_operador_sources
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            MIN(source_date) as primeira_data,
            MAX(source_date) as ultima_data
        FROM painel_operador_sources 
        WHERE family IN ('a001', 'a002', 'a003', 'a004')
    """)
    total, min_date, max_date = cur.fetchone()
    print(f"\n📁 painel_operador_sources:")
    print(f"   Total de fontes XML: {total}")
    if total > 0:
        print(f"   Período: {min_date} até {max_date}")
    
    # Detalhar por família
    cur.execute("""
        SELECT family, COUNT(*) as total
        FROM painel_operador_sources 
        WHERE family IN ('a001', 'a002', 'a003', 'a004')
        GROUP BY family
        ORDER BY family
    """)
    families = cur.fetchall()
    if families:
        print(f"\n   Por família:")
        for fam, count in families:
            print(f"     {fam}: {count} arquivos")
    
    # Verificar últimos dias
    cur.execute("""
        SELECT source_date, family, COUNT(*) as total
        FROM painel_operador_sources 
        WHERE family IN ('a001', 'a002', 'a003', 'a004')
          AND source_date >= '2026-07-01'
        GROUP BY source_date, family
        ORDER BY source_date DESC, family
    """)
    recent = cur.fetchall()
    if recent:
        print(f"\n   Arquivos de Julho 2026:")
        for dt, fam, count in recent:
            print(f"     {dt} - {fam}: {count} arquivo(s)")
    
    # Verificar painel_operador_sync_runs
    cur.execute("""
        SELECT COUNT(*), MAX(finished_at), MIN(finished_at)
        FROM painel_operador_sync_runs
    """)
    sync_total, sync_max, sync_min = cur.fetchone()
    print(f"\n📊 painel_operador_sync_runs:")
    print(f"   Total de execuções: {sync_total}")
    if sync_total > 0:
        print(f"   Primeira execução: {sync_min}")
        print(f"   Última execução: {sync_max}")

except sqlite3.OperationalError as e:
    print(f"\n⚠️ Erro ao consultar: {e}")

conn.close()

print("\n" + "=" * 80)
