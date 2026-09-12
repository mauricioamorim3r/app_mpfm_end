import sqlite3
import json

conn = sqlite3.connect("data/mpfm_local.db")
cur = conn.cursor()
cur.execute(
    "UPDATE processing_runs SET status='error', finished_at=?, notes_json=? WHERE id=795 AND status='running'",
    (
        "2026-08-03T17:57:00",
        json.dumps(
            {
                "log": [
                    "Run marcado manualmente como erro: processo travado sem concluir "
                    "(running desde 2026-08-03T12:52:33, ~5h). Parsing dos 3 arquivos OK "
                    "(processed_ok=1) mas etapa de commit/postcheck nao finalizou."
                ]
            },
            ensure_ascii=False,
        ),
    ),
)
conn.commit()
print("rows updated:", cur.rowcount)
row = conn.execute("SELECT id, status, finished_at FROM processing_runs WHERE id=795").fetchone()
print(row)
conn.close()
