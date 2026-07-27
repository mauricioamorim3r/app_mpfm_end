"""Debug: Analisa issues e parsing_events do run 79 para entender falha."""
import sqlite3
import json

db = r'data/mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== TABLES ===")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print([t['name'] for t in tables])
print()

print("=== import_issues para run 79 ===")
try:
    issues = conn.execute("SELECT * FROM import_issues WHERE run_id=79 ORDER BY id LIMIT 30").fetchall()
    for r in issues:
        print(dict(r))
except Exception as e:
    print(f"Erro: {e}")
print()

print("=== parsing_events para run 79 ===")
try:
    events = conn.execute("SELECT * FROM parsing_events WHERE run_id=79 ORDER BY id LIMIT 50").fetchall()
    for r in events:
        print(dict(r))
except Exception as e:
    print(f"Erro: {e}")
print()

print("=== files_imported para run 79 (sample) ===")
try:
    sample = conn.execute("SELECT id, filename, file_type, content_date, processed_ok, message FROM files_imported WHERE run_id=79 LIMIT 5").fetchall()
    for r in sample:
        print(dict(r))
except Exception as e:
    print(f"Erro: {e}")
print()

print("=== State April 2026 para B15 (processed_hours_by_key) ===")
try:
    import os
    state_file = r'data/state_2026_04.json'
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        hours_by_key = state.get('processed_hours_by_key', {})
        # Show B15 keys for days 15-21
        for k in sorted(hours_by_key.keys()):
            if 'B15' in k:
                day = k.split('_')[1]
                if day in ['15','16','17','18','19','20','21']:
                    print(f"  {k}: {hours_by_key[k]}")
except Exception as e:
    print(f"Erro: {e}")

conn.close()
print("\n=== DONE ===")
