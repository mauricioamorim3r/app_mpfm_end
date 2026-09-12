import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
cur = conn.cursor()
cur.execute(
    "UPDATE processing_runs SET status='error', finished_at=?, notes_json=? "
    "WHERE id=817 AND status='running'",
    (
        "2026-08-03T18:12:00",
        "Run travado dentro de _merge_excel (mes AGO/2026, B10 Hourly). "
        "Processo python (PID 30520) morto manualmente e run marcado como erro; "
        "servidor reiniciado. Reproducao do bug conhecido documentado em "
        "/memories/repo/mpfm-server-notes.md.",
    ),
)
conn.commit()
print("rows updated:", cur.rowcount)
row = cur.execute("SELECT id, status, finished_at FROM processing_runs WHERE id=817").fetchone()
print(row)
