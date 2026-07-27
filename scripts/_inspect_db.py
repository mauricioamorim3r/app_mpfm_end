import sqlite3, os, sys

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mpfm_local.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("Tabelas no banco:", tables)
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    count = cur.fetchone()[0]
    print(f"  {t}: {count} registros")
conn.close()
