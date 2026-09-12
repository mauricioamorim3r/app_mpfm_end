import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
cur = conn.cursor()

n = cur.execute("SELECT COUNT(*) FROM measurements_curated WHERE day_ref LIKE '2026-07-%' AND row_kind IN ('hourly','daily','recon','sep')").fetchone()[0]
print("measurements_curated rows for July:", n)

n2 = cur.execute("SELECT COUNT(*) FROM validation_issues").fetchone()[0]
print("validation_issues total rows:", n2)
