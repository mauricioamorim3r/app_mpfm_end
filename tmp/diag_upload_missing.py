import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- max day_ref per tag (daily) for target tags ---")
for tag in ("PE_4", "PE_2", "PW-104DA", "Riser_P2", "PE_EO4", "PE_EO105", "PE_EO10"):
    row = cur.execute(
        "SELECT MAX(day_ref) FROM measurements_curated WHERE row_kind='daily' AND tag=?",
        (tag,),
    ).fetchone()
    print(tag, "->", row[0])

print("\n--- rows for day_ref=2026-07-31 for these tags ---")
for tag in ("PE_4", "PE_2", "PW-104DA", "Riser_P2", "PE_EO4", "PE_EO105", "PE_EO10"):
    row = cur.execute(
        "SELECT COUNT(*) FROM measurements_curated WHERE row_kind='daily' AND tag=? AND day_ref='2026-07-31'",
        (tag,),
    ).fetchone()
    print(tag, "->", row[0])

print("\n--- rows for day_ref in 2026-08-01/02/03 (any tag) ---")
for d in ("2026-08-01", "2026-08-02", "2026-08-03"):
    row = cur.execute(
        "SELECT COUNT(*), COUNT(DISTINCT tag) FROM measurements_curated WHERE row_kind='daily' AND day_ref=?",
        (d,),
    ).fetchone()
    print(d, "->", dict(zip(("rows", "distinct_tags"), row)))

print("\n--- distinct tags with day_ref=2026-08-01 ---")
for r in cur.execute("SELECT DISTINCT tag FROM measurements_curated WHERE day_ref='2026-08-01'"):
    print(dict(r))

print("\n--- recent processing_runs (last 15) ---")
try:
    for r in cur.execute("SELECT id, status, created_at, kind, notes FROM processing_runs ORDER BY id DESC LIMIT 15"):
        print(dict(r))
except Exception as e:
    print("error:", e)
    print(cur.execute("PRAGMA table_info(processing_runs)").fetchall())
