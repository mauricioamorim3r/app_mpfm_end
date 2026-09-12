import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- hourly rows for 2026-08-03 by tag ---")
for r in cur.execute(
    "SELECT tag, COUNT(*) c, MAX(hour_ref) mh FROM measurements_curated WHERE row_kind='hourly' AND day_ref='2026-08-03' GROUP BY tag ORDER BY tag"
):
    print(dict(r))

print("\n--- hourly rows for 2026-08-02 by tag (for comparison) ---")
for r in cur.execute(
    "SELECT tag, COUNT(*) c, MAX(hour_ref) mh FROM measurements_curated WHERE row_kind='hourly' AND day_ref='2026-08-02' GROUP BY tag ORDER BY tag"
):
    print(dict(r))

print("\n--- processing_runs schema ---")
print([r[1] for r in cur.execute("PRAGMA table_info(processing_runs)").fetchall()])

print("\n--- last 15 processing_runs ---")
for r in cur.execute("SELECT * FROM processing_runs ORDER BY id DESC LIMIT 15"):
    print(dict(r))

print("\n--- files_imported schema ---")
print([r[1] for r in cur.execute("PRAGMA table_info(files_imported)").fetchall()])

print("\n--- last 25 files_imported ---")
for r in cur.execute("SELECT * FROM files_imported ORDER BY id DESC LIMIT 25"):
    print(dict(r))
