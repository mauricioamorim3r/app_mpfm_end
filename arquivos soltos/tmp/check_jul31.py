import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
print(conn.execute("SELECT COUNT(*) FROM measurements_curated WHERE day_ref='2026-07-31'").fetchone())
