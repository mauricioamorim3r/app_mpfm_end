import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')

# Corrige run fantasma 831
sql = (
    "UPDATE processing_runs "
    "SET status='error', finished_at=datetime('now','localtime'), "
    "    notes_json='{\"log_error\":\"Servidor reiniciado - run fantasma corrigido 2026-08-14\"}' "
    "WHERE id=831 AND status='running'"
)
conn.execute(sql)
conn.commit()
n = conn.execute("SELECT changes()").fetchone()[0]
print(f"Linhas corrigidas: {n}")

# Confirma
row = conn.execute("SELECT id, status, finished_at FROM processing_runs WHERE id=831").fetchone()
print(f"run 831: status={row[1]}, finished_at={row[2]}")

conn.close()
