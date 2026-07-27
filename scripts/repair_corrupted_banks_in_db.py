import sqlite3
import sys
from pathlib import Path

INSTRUMENT_TO_BANK = {
    '18FT0506': 'B10', '18FT0306': 'B10', '18FT0106': 'B10',
    '18FT1506': 'B05', '18FT1406': 'B05', '18FT1706': 'B05', '18FT1806': 'B05',
    '18FT0706': 'B15', '18FT0906': 'B15', '18FT1206': 'B15', '18FT1106': 'B15',
    '13FT0167': 'B08', '13FT0217': 'B08',
    '13FT0267': 'B13', '13FT0317': 'B13',
    '13FT0367': 'B03', '13FT0417': 'B03',
    '20FT0244': 'SEP', '20FT0247': 'SEP', '20FT0251': 'SEP'
}

TAG_TO_BANK = {
    'PE_2': 'B10', 'PE_8': 'B10', 'PE_9': 'B10',
    'PE_4': 'B05', 'PE_EO10': 'B05', 'PE_EO105': 'B05', 'PE_EO4': 'B05',
    'PE_1': 'B15', 'PI_1': 'B15', 'PI_2': 'B15', 'PW-104DA': 'B15',
    'Riser_P1': 'B08', 'Riser_P2': 'B08',
    'Riser_P3': 'B13', 'Riser_P4': 'B13',
    'Riser_P5': 'B03', 'Riser_P6': 'B03',
}

WELL_TO_BANK = {
    'PE_2': 'B10', '7-BAC-1-SPS': 'B10',
    'PE_4': 'B05', '7-BAC-5A-SPS': 'B05', 'PE-4A': 'B05',
    'PW-104DA': 'B15', '7-BAC-4D-SPS': 'B15',
}

def repair_database():
    db_path = Path('data/mpfm_local.db')
    if not db_path.exists():
        print("Database not found!")
        return
        
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    conn.execute("PRAGMA busy_timeout = 30000;")
    cur = conn.cursor()
    
    print("=== REPAIRING measurements_curated ===")
    bad_banks = ['B12799', 'B145', 'B15153', 'B17525', 'B19109', 'B47', 'B52', 'UNK']
    placeholders = ','.join('?' for _ in bad_banks)
    cur.execute(f"""
        SELECT id, bank, tag, instrument 
        FROM measurements_curated 
        WHERE bank IN ({placeholders}) 
           OR (bank = 'B08' AND (instrument IN ('18FT0506','18FT0306','18FT0106') OR tag IN ('PE_2','PE_8','PE_9')))
    """, bad_banks)
    rows = cur.fetchall()
    
    updates_by_id = []
    for row_id, current_bank, tag, inst in rows:
        correct_bank = INSTRUMENT_TO_BANK.get(inst) or TAG_TO_BANK.get(tag)
        if correct_bank and correct_bank != current_bank:
            updates_by_id.append((correct_bank, row_id))
            
    print(f"Found {len(updates_by_id)} rows to update in measurements_curated.")
    
    cur.executemany("UPDATE measurements_curated SET bank = ? WHERE id = ?", updates_by_id)
    conn.commit()
    print(f"  Successfully updated {len(updates_by_id)} rows in measurements_curated!")

    print("\n=== REPAIRING files_imported & source_files_raw ===")
    cur.execute("SELECT DISTINCT run_id, bank FROM measurements_curated WHERE run_id IS NOT NULL AND bank IN ('B03','B05','B08','B10','B13','B15','SEP')")
    run_to_bank = dict(cur.fetchall())

    cur.execute("SELECT id, filename, unit_code, run_id FROM files_imported WHERE unit_code NOT IN ('B03','B05','B08','B10','B13','B15','SEP')")
    for file_id, filename, old_unit, run_id in cur.fetchall():
        new_unit = run_to_bank.get(run_id)
        if new_unit:
            cur.execute("UPDATE files_imported SET unit_code = ? WHERE id = ?", (new_unit, file_id))
            print(f"  files_imported ID {file_id} ({filename}): {old_unit} -> {new_unit}")

    cur.execute("SELECT id, filename, unit_code, run_id FROM source_files_raw WHERE unit_code NOT IN ('B03','B05','B08','B10','B13','B15','SEP')")
    for raw_id, filename, old_unit, run_id in cur.fetchall():
        new_unit = run_to_bank.get(run_id)
        if new_unit:
            cur.execute("UPDATE source_files_raw SET unit_code = ? WHERE id = ?", (new_unit, raw_id))
            print(f"  source_files_raw ID {raw_id} ({filename}): {old_unit} -> {new_unit}")

    print("\n=== REPAIRING xml042 tables ===")
    for well, correct_bank in WELL_TO_BANK.items():
        cur.execute("""
            UPDATE xml042_documents
            SET bank = ?
            WHERE (well_operator_name = ? OR cod_cadastro_poco = ?) AND bank != ?
        """, (correct_bank, well, well, correct_bank))
        if cur.rowcount > 0:
            print(f"  xml042_documents for {well}: updated to {correct_bank}")

        cur.execute("""
            UPDATE xml042_imported_files
            SET bank = ?
            WHERE (well_operator_name = ? OR subsea_tag = ?) AND bank != ?
        """, (correct_bank, well, well, correct_bank))
        if cur.rowcount > 0:
            print(f"  xml042_imported_files for {well}: updated to {correct_bank}")

        cur.execute("""
            UPDATE xml042_imported_rows
            SET bank = ?
            WHERE (well_operator_name = ? OR subsea_tag = ?) AND bank != ?
        """, (correct_bank, well, well, correct_bank))
        if cur.rowcount > 0:
            print(f"  xml042_imported_rows for {well}: updated to {correct_bank}")

    conn.commit()
    conn.close()
    print("\nDatabase repair complete!")

if __name__ == '__main__':
    repair_database()
