import sys
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server

base_dir = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3. Registros de Operação SGM Multifasico\3.1 Registros Diarios MPFM")

banks_folders = [
    ('B03', '3.1.1_13-FT-0367 Riser P5 - Topside B03'),
    ('B08', '3.1.2_13-FT-0167 Riser P2 - Topside B08'),
    ('B13', '3.1.3_13-FT-0317 Riser P4 - Topside B13'),
    ('B05', '3.1.4_18-FT-1506 PE 4 - Subsea B05'),
    ('B10', '3.1.5_18-FT-0506 PE 2 - Subsea B10'),
    ('B15', '3.1.6_18-FT-1106 PW_104DA - Subsea B15'),
]

conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()

def verify_all():
    total_unloaded_pdfs = 0

    for bank, folder_name in banks_folders:
        y2026 = base_dir / folder_name / '2026'
        if not y2026.exists():
            continue

        cur.execute("SELECT DISTINCT day_ref FROM measurements_curated WHERE bank=? AND row_kind='daily'", (bank,))
        db_daily_days = set(r[0] for r in cur.fetchall())

        cur.execute("SELECT DISTINCT day_ref FROM measurements_curated WHERE bank=? AND row_kind='hourly'", (bank,))
        db_hourly_days = set(r[0] for r in cur.fetchall())

        print(f"\n==========================================")
        print(f"=== Bank {bank} ({folder_name}) ===")
        print(f"==========================================")

        for month_dir in sorted(y2026.iterdir()):
            if not month_dir.is_dir():
                continue
            m_name = month_dir.name

            # Daily
            daily_dir = month_dir / 'Daily'
            if daily_dir.exists():
                daily_pdfs = list(daily_dir.glob('*.pdf'))
                missing_daily_count = 0
                for p in daily_pdfs:
                    rec = server.engine.parse_pdf(str(p), 'daily')
                    pday = str(rec.get('date_from') or '').strip()
                    if pday and pday not in db_daily_days:
                        missing_daily_count += 1
                        total_unloaded_pdfs += 1
                if missing_daily_count > 0:
                    print(f"  [{m_name}] DAILY has {missing_daily_count} PDFs not in DB!")
                else:
                    print(f"  [{m_name}] DAILY: 100% of {len(daily_pdfs)} PDFs ingested into DB")

            # Hourly
            hourly_dir = month_dir / 'Hourly'
            if hourly_dir.exists():
                hourly_pdfs = list(hourly_dir.glob('*.pdf'))
                missing_hourly_count = 0
                for p in hourly_pdfs:
                    rec = server.engine.parse_pdf(str(p), 'hourly')
                    pday = str(rec.get('date_from') or '').strip()
                    if pday and pday not in db_hourly_days:
                        missing_hourly_count += 1
                        total_unloaded_pdfs += 1
                if missing_hourly_count > 0:
                    print(f"  [{m_name}] HOURLY has {missing_hourly_count} PDFs not in DB!")
                else:
                    print(f"  [{m_name}] HOURLY: 100% of {len(hourly_pdfs)} PDFs ingested into DB")

    conn.close()
    print(f"\n==========================================")
    print(f"FINAL RESULT: Total unloaded PDFs across all 2026 folders = {total_unloaded_pdfs}")
    print(f"==========================================")

if __name__ == '__main__':
    verify_all()


