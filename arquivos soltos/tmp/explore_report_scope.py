import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- distinct row_kind (measurements_curated) ---")
for r in cur.execute("SELECT DISTINCT row_kind FROM measurements_curated"):
    print(dict(r))

print("\n--- distinct bank/tag for row_kind='daily' ---")
for r in cur.execute("SELECT DISTINCT bank, tag FROM measurements_curated WHERE row_kind='daily' ORDER BY bank"):
    print(dict(r))

print("\n--- date range available (daily) ---")
print(cur.execute("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='daily'").fetchone())

print("\n--- SEP bank/tag/row_kind combos ---")
for r in cur.execute("SELECT DISTINCT row_kind, bank, tag FROM measurements_curated WHERE bank='SEP' OR tag IN ('SEP','20FT0247','20FT0244','20FT0251')"):
    print(dict(r))

print("\n--- metric_name list for PE_2 daily ---")
for r in cur.execute("SELECT DISTINCT metric_name FROM measurements_curated WHERE row_kind='daily' AND tag='PE_2' ORDER BY metric_name"):
    print(dict(r))

print("\n--- metric_name list for SEP daily(-like) row_kinds ---")
for r in cur.execute("SELECT DISTINCT row_kind, metric_name FROM measurements_curated WHERE bank='SEP' ORDER BY row_kind, metric_name"):
    print(dict(r))

print("\n--- is_official / measurements_active existence check ---")
try:
    cur.execute("SELECT COUNT(*) FROM measurements_active LIMIT 1")
    print("measurements_active exists, count sample:", cur.fetchone())
except Exception as e:
    print("no measurements_active view/table:", e)

print("\n--- counts per tag daily in requested period 2026-02-03..2026-07-30 ---")
for tag in ("PE_4", "PE_2", "Riser_P2"):
    row = cur.execute(
        "SELECT COUNT(DISTINCT day_ref) FROM measurements_curated WHERE row_kind='daily' AND tag=? AND day_ref BETWEEN '2026-02-03' AND '2026-07-30'",
        (tag,),
    ).fetchone()
    print(tag, row)

row = cur.execute(
    "SELECT COUNT(DISTINCT day_ref) FROM measurements_curated WHERE bank='SEP' AND day_ref BETWEEN '2026-02-03' AND '2026-07-30'"
).fetchone()
print("SEP", row)

print("\n--- hourly row_kind check ---")
for r in cur.execute("SELECT DISTINCT row_kind FROM measurements_curated WHERE row_kind LIKE '%hour%'"):
    print(dict(r))
