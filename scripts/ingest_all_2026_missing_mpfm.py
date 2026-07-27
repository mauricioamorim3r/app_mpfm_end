import re
import sys
import time
import sqlite3
import subprocess
from pathlib import Path

base_dir = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3. Registros de Operação SGM Multifasico\3.1 Registros Diarios MPFM")

banks_folders = [
    ('B03', '3.1.1_13-FT-0367 Riser P5 - Topside B03'),
    ('B08', '3.1.2_13-FT-0167 Riser P2 - Topside B08'),
    ('B13', '3.1.3_13-FT-0317 Riser P4 - Topside B13'),
    ('B05', '3.1.4_18-FT-1506 PE 4 - Subsea B05'),
    ('B10', '3.1.5_18-FT-0506 PE 2 - Subsea B10'),
    ('B15', '3.1.6_18-FT-1106 PW_104DA - Subsea B15'),
]

daily_script = Path(r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\NOVO\scripts\repair_missing_mpfm_daily_from_folder.py")
hourly_script = Path(r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\NOVO\scripts\repair_missing_mpfm_hourly_from_folder.py")

def extract_date(filename):
    m = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None

def main():
    conn = sqlite3.connect('data/mpfm_local.db')
    cur = conn.cursor()

    tasks = []
    
    for bank, folder_name in banks_folders:
        y2026 = base_dir / folder_name / '2026'
        if not y2026.exists():
            continue
            
        cur.execute("SELECT DISTINCT day_ref FROM measurements_curated WHERE bank=? AND row_kind='daily'", (bank,))
        db_daily_days = set(r[0] for r in cur.fetchall())

        cur.execute("SELECT DISTINCT day_ref FROM measurements_curated WHERE bank=? AND row_kind='hourly'", (bank,))
        db_hourly_days = set(r[0] for r in cur.fetchall())

        for month_dir in sorted(y2026.iterdir()):
            if not month_dir.is_dir():
                continue
            m_name = month_dir.name
            
            # Daily
            daily_dir = month_dir / 'Daily'
            if daily_dir.exists():
                daily_pdfs = list(daily_dir.glob('*.pdf'))
                pdf_dates = set(filter(None, [extract_date(p.name) for p in daily_pdfs]))
                missing_daily = pdf_dates - db_daily_days
                if missing_daily:
                    tasks.append((bank, 'daily', m_name, daily_dir, sorted(missing_daily)))

            # Hourly
            hourly_dir = month_dir / 'Hourly'
            if hourly_dir.exists():
                hourly_pdfs = list(hourly_dir.glob('*.pdf'))
                pdf_dates = set(filter(None, [extract_date(p.name) for p in hourly_pdfs]))
                missing_hourly = pdf_dates - db_hourly_days
                if missing_hourly:
                    tasks.append((bank, 'hourly', m_name, hourly_dir, sorted(missing_hourly)))

    conn.close()

    print(f"============================================================")
    print(f"FOUND {len(tasks)} MISSING INGESTION TASKS FOR 2026")
    print(f"============================================================")
    for idx, (bank, kind, month, path, missing_days) in enumerate(tasks, 1):
        print(f"{idx:02d}. Bank {bank:<4} | {kind.upper():<6} | {month:<15} | Missing days: {len(missing_days)}")

    print("\nStarting ingestion process...\n")
    
    for idx, (bank, kind, month, path, missing_days) in enumerate(tasks, 1):
        print(f"\n------------------------------------------------------------")
        print(f"[{idx}/{len(tasks)}] Processing Bank {bank} - {kind.upper()} ({month})")
        print(f"Path: {path}")
        print(f"Missing days to ingest: {missing_days}")
        print(f"------------------------------------------------------------")
        
        script = daily_script if kind == 'daily' else hourly_script
        cmd = [sys.executable, str(script), "--bank", bank, "--folder", str(path)]
        
        try:
            res = subprocess.run(cmd, check=True)
            print(f"SUCCESS: {bank} {kind} ({month})")
        except subprocess.CalledProcessError as e:
            print(f"ERROR processing {bank} {kind} ({month}): Exit code {e.returncode}")

        print("Pausing 3 seconds before next batch...")
        time.sleep(3)

    print("\n============================================================")
    print("ALL 2026 INGESTION TASKS COMPLETED!")
    print("============================================================")

if __name__ == "__main__":
    main()
