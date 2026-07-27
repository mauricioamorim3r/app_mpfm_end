#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

conn = sqlite3.connect('mpfm_local.db')
cursor = conn.cursor()

# Verificar tabela existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'painel_operador_comparacao%'")
tables = cursor.fetchall()
print("Tabelas de comparação encontradas:")
for t in tables:
    print(f"  - {t[0]}")

# Verificar dados em julho
cursor.execute("""
    SELECT COUNT(*) FROM painel_operador_comparacao_fiscal_mpfm 
    WHERE production_date >= '2026-07-01' AND production_date <= '2026-07-31'
""")
count_july = cursor.fetchone()[0]
print(f"\nRegistros em julho/2026: {count_july}")

# Verificar período disponível
cursor.execute("""
    SELECT 
        MIN(production_date) as min_date,
        MAX(production_date) as max_date,
        COUNT(*) as total
    FROM painel_operador_comparacao_fiscal_mpfm
""")
result = cursor.fetchone()
print(f"Período disponível: {result[0]} até {result[1]}")
print(f"Total de registros: {result[2]}")

# Últimas 10 datas
cursor.execute("""
    SELECT DISTINCT production_date 
    FROM painel_operador_comparacao_fiscal_mpfm 
    ORDER BY production_date DESC 
    LIMIT 10
""")
dates = cursor.fetchall()
print("\nÚltimas 10 datas:")
for d in dates:
    print(f"  {d[0]}")

conn.close()
