import sqlite3

def audit():
    conn = sqlite3.connect('data/mpfm_local.db')
    cur = conn.cursor()
    valid_banks = ('B03', 'B05', 'B08', 'B10', 'B13', 'B15', 'SEP')
    tables = [
        ('files_imported', 'unit_code'),
        ('source_files_raw', 'unit_code'),
        ('measurements_curated', 'bank'),
        ('sep_alignments', 'bank'),
        ('recon_runs', 'bank'),
        ('daily_cards', 'bank'),
        ('mpfm_monitoring_daily', 'bank'),
        ('xml042_documents', 'bank'),
        ('alarm_records', 'bank')
    ]
    for tbl, col in tables:
        try:
            placeholders = ','.join('?' for _ in valid_banks)
            cur.execute(f"SELECT {col}, COUNT(*) FROM {tbl} WHERE {col} NOT IN ({placeholders}) GROUP BY {col}", valid_banks)
            res = cur.fetchall()
            if res:
                print(f"{tbl}.{col}:", res)
        except Exception as e:
            print(f"Error checking {tbl}.{col}: {e}")

if __name__ == '__main__':
    audit()
