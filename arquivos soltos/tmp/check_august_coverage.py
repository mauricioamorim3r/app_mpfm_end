import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- runs 805-820 ---")
for r in cur.execute("SELECT id, status, started_at, finished_at, source_type, files_count, substr(source_ref,-40) as ref_tail FROM processing_runs WHERE id BETWEEN 805 AND 820 ORDER BY id"):
    print(dict(r))

print("\n--- coverage day_ref for August, row_kind=daily, all target tags ---")
for tag in ("PE_4", "PE_2", "PW-104DA", "Riser_P2", "Riser_P4", "Riser_P5"):
    rows = cur.execute(
        "SELECT day_ref, COUNT(*) c FROM measurements_curated WHERE row_kind='daily' AND tag=? AND day_ref>='2026-08-01' GROUP BY day_ref ORDER BY day_ref",
        (tag,),
    ).fetchall()
    print(tag, "->", [dict(r) for r in rows])

print("\n--- coverage hourly for August, PE_2 ---")
rows = cur.execute(
    "SELECT day_ref, COUNT(DISTINCT hour_ref) hrs FROM measurements_curated WHERE row_kind='hourly' AND tag='PE_2' AND day_ref>='2026-08-01' GROUP BY day_ref ORDER BY day_ref"
).fetchall()
print([dict(r) for r in rows])
