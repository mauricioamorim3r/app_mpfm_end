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

conn = sqlite3.connect('data/mpfm_local.db')
cur = conn.cursor()
bad_banks = ['B12799', 'B145', 'B15153', 'B17525', 'B19109', 'B47', 'B52', 'UNK']
placeholders = ','.join('?' for _ in bad_banks)
cur.execute(f"""
    SELECT id, bank, tag, instrument 
    FROM measurements_curated 
    WHERE bank IN ({placeholders}) 
       OR (bank = 'B08' AND (instrument IN ('18FT0506','18FT0306','18FT0106') OR tag IN ('PE_2','PE_8','PE_9')))
""", bad_banks)
rows = cur.fetchall()

print(f"Exact bad rows count: {len(rows)}")
for r in rows[:10]:
    inst = str(r[3] or "").strip()
    tag = str(r[2] or "").strip()
    target = INSTRUMENT_TO_BANK.get(inst) or TAG_TO_BANK.get(tag)
    print(f"  Row ID {r[0]}: current '{r[1]}' -> target '{target}' (tag {tag}, inst {inst})")

