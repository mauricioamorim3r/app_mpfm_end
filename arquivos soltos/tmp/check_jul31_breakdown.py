import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- breakdown by row_kind for day_ref=2026-07-31 ---")
for r in cur.execute("SELECT row_kind, tag, COUNT(*) c FROM measurements_curated WHERE day_ref='2026-07-31' GROUP BY row_kind, tag ORDER BY row_kind, tag"):
    print(dict(r))

print("\n--- daily row_kind for target tags on 2026-07-31 ---")
for tag in ("PE_4", "PE_2", "PW-104DA", "Riser_P2", "PE_EO4", "PE_EO105", "PE_EO10"):
    row = cur.execute(
        "SELECT COUNT(*) FROM measurements_curated WHERE row_kind='daily' AND tag=? AND day_ref='2026-07-31'",
        (tag,),
    ).fetchone()
    print(tag, "->", row[0])

print("\n--- run 795 status now ---")
print(dict(cur.execute("SELECT id, status, started_at, finished_at FROM processing_runs WHERE id=795").fetchone()))
