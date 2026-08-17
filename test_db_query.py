import sqlite3

DB_PATH = "data/mpfm_local.db"

print("Conectando ao banco...")
conn = sqlite3.connect(DB_PATH, timeout=30.0)
cur = conn.cursor()

print("Executando query para buscar runs recentes...")
sql = """
    SELECT id FROM processing_runs
    ORDER BY id DESC
    LIMIT ?
"""

try:
    rows = cur.execute(sql, (5,)).fetchall()
    print(f"Encontrados {len(rows)} runs")
    for row in rows:
        print(f"  Run ID: {row[0]}")
except Exception as e:
    print(f"ERRO: {e}")
finally:
    conn.close()
    print("Conexão fechada")
