import sqlite3

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

DFROM, DTO = "2026-02-03", "2026-07-30"

def scalar(q, params=()):
    r = cur.execute(q, params).fetchone()
    return tuple(r) if r else None

print("date range daily overall:", scalar("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='daily'"))
print("date range hourly overall:", scalar("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='hourly'"))
print("date range sep overall:", scalar("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='sep'"))
print("date range sep_oleo_detail overall:", scalar("SELECT MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='sep_oleo_detail'"))

for tag in ("PE_4", "PE_2", "Riser_P2"):
    d = scalar("SELECT COUNT(DISTINCT day_ref), MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='daily' AND tag=? AND day_ref BETWEEN ? AND ?", (tag, DFROM, DTO))
    h = scalar("SELECT COUNT(DISTINCT day_ref), MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='hourly' AND tag=? AND day_ref BETWEEN ? AND ?", (tag, DFROM, DTO))
    print(tag, "daily:", d, "hourly:", h)

print("SEP daily(row_kind=sep) in range:", scalar("SELECT COUNT(DISTINCT day_ref), MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE row_kind='sep' AND day_ref BETWEEN ? AND ?", (DFROM, DTO)))
print("SEP oleo_detail daily rows (hour_ref IS NULL) in range:", scalar("SELECT COUNT(DISTINCT day_ref) FROM measurements_curated WHERE row_kind='sep_oleo_detail' AND hour_ref IS NULL AND day_ref BETWEEN ? AND ?", (DFROM, DTO)))
print("SEP oleo_detail hourly rows (hour_ref NOT NULL) in range:", scalar("SELECT COUNT(DISTINCT day_ref) FROM measurements_curated WHERE row_kind='sep_oleo_detail' AND hour_ref IS NOT NULL AND day_ref BETWEEN ? AND ?", (DFROM, DTO)))

# compare consolidated sep vs detail sums for a sample day
sample_day = scalar("SELECT MAX(day_ref) FROM measurements_curated WHERE row_kind='sep' AND day_ref BETWEEN ? AND ?", (DFROM, DTO))
print("sample day:", sample_day)
if sample_day and sample_day[0]:
    sd = sample_day[0]
    print("consolidated sep row:", [dict(r) for r in cur.execute("SELECT metric_name, metric_value FROM measurements_curated WHERE row_kind='sep' AND day_ref=?", (sd,))])
    print("oleo detail daily row:", [dict(r) for r in cur.execute("SELECT metric_name, metric_value FROM measurements_curated WHERE row_kind='sep_oleo_detail' AND hour_ref IS NULL AND day_ref=?", (sd,))])
    print("gas detail daily row:", [dict(r) for r in cur.execute("SELECT metric_name, metric_value FROM measurements_curated WHERE row_kind='sep_gas_detail' AND hour_ref IS NULL AND day_ref=?", (sd,))])
    print("agua detail daily row:", [dict(r) for r in cur.execute("SELECT metric_name, metric_value FROM measurements_curated WHERE row_kind='sep_agua_detail' AND hour_ref IS NULL AND day_ref=?", (sd,))])

print("\nis_official values distinct:", [dict(r) for r in cur.execute("SELECT DISTINCT is_official FROM measurements_curated")])

# measurements_active def
print("\nmeasurements_active is a table or view?")
print(scalar("SELECT type FROM sqlite_master WHERE name='measurements_active'"))
