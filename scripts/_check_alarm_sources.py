import sqlite3, os
db = r'C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 07 Applications\7.1 MPFM_PDF_TXT\data\mpfm_local.db'
conn = sqlite3.connect(db)
rows = conn.execute(
    "SELECT source_ref, source_kind, COUNT(*) as total, "
    "SUM(CASE WHEN active=1 THEN 1 ELSE 0 END) as ativo, "
    "MIN(production_date) as min_dt, MAX(production_date) as max_dt "
    "FROM alarm_records GROUP BY source_ref, source_kind ORDER BY max_dt DESC"
).fetchall()
print(f"{'SOURCE_REF':<60} {'KIND':<12} {'TOTAL':>6} {'ATIVO':>6} {'MIN_DT':<12} {'MAX_DT':<12}")
print("-"*110)
for r in rows:
    print(f"{str(r[0])[-58:]:<60} {str(r[1]):<12} {r[2]:>6} {r[3]:>6} {str(r[4]):<12} {str(r[5]):<12}")
conn.close()
