import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect(r"data/mpfm_local.db", timeout=30)
conn.execute(
    "UPDATE processing_runs SET finished_at=?, status=?, notes_json=? WHERE id=? AND status='running'",
    (
        datetime.now().isoformat(timespec="seconds"),
        "error",
        json.dumps({"log": ["Run marcado manualmente como erro: processo travado sem progresso por 18+ minutos (openpyxl merge / purge de overwrite lento para reprocesso completo do mes)."]}, ensure_ascii=False),
        784,
    ),
)
conn.commit()
cur = conn.execute("SELECT id, status, finished_at FROM processing_runs WHERE id=784")
print(cur.fetchone())
conn.close()
