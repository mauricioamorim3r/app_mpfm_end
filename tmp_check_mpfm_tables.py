#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('mpfm_local.db')
cursor = conn.cursor()

# Listar todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [r[0] for r in cursor.fetchall()]

print("=== TABELAS RELACIONADAS A COMPARAÇÃO/FISCAL/MPFM ===\n")

relevant = [t for t in all_tables if any(word in t.lower() for word in ['fiscal', 'mpfm', 'compar', 'oil', 'gas'])]
for t in relevant:
    cursor.execute(f"SELECT COUNT(*) FROM {t}")
    count = cursor.fetchone()[0]
    print(f"{t}: {count} registros")

print("\n=== TABELA MPFM-FISCAL DO CHECKLIST ===\n")

# Verificar se existe tabela mpfm_fiscal_oil
if 'painel_operador_mpfm_fiscal_oil' in all_tables:
    cursor.execute("SELECT COUNT(*) FROM painel_operador_mpfm_fiscal_oil WHERE production_date >= '2026-07-01'")
    july_count = cursor.fetchone()[0]
    print(f"Registros em julho: {july_count}")
    
    cursor.execute("SELECT production_date, total_mpfm, fiscal, deviation_pct FROM painel_operador_mpfm_fiscal_oil WHERE production_date >= '2026-07-01' ORDER BY production_date LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        print("\nPrimeiras 5 linhas de julho:")
        for r in rows:
            print(f"  {r[0]}: MPFM={r[1]}, Fiscal={r[2]}, Desvio={r[3]}%")
    else:
        print("Nenhum registro encontrado para julho")
else:
    print("Tabela painel_operador_mpfm_fiscal_oil não existe")

conn.close()
