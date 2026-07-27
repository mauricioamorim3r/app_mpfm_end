import sqlite3

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

def analyze_mismatches():
    conn = sqlite3.connect('data/mpfm_local.db')
    cur = conn.cursor()
    
    cur.execute("""
        SELECT bank, tag, instrument, day_ref, source_file, COUNT(*)
        FROM measurements_curated
        GROUP BY bank, tag, instrument, day_ref, source_file
    """)
    rows = cur.fetchall()
    
    mismatches = []
    for bank, tag, instrument, day_ref, source_file, count in rows:
        expected = INSTRUMENT_TO_BANK.get(instrument) or TAG_TO_BANK.get(tag)
        if expected and bank != expected:
            mismatches.append((bank, expected, tag, instrument, day_ref, source_file, count))
            
    print(f"Total mismatched groups found: {len(mismatches)}")
    for m in mismatches:
        print(f"Current Bank: {m[0]:<10} -> Expected: {m[1]:<5} | Tag: {m[2]:<10} | Inst: {m[3]:<10} | Day: {m[4]} | File: {m[5]}")

if __name__ == '__main__':
    analyze_mismatches()
