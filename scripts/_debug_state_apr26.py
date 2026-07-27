"""Debug: Inspeciona o state de abril 2026."""
import json
import os

state_file = r'data/state_2026_04.json'
if not os.path.exists(state_file):
    print("State file not found!")
else:
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    print("=== Top-level keys ===")
    print(list(state.keys()))
    
    print("\n=== 'processed' list (daily PDFs) ===")
    processed = state.get('processed', [])
    print(f"Total: {len(processed)}")
    for k in sorted(processed):
        print(f"  {k}")

    print("\n=== 'processed_hours_by_key' for B15 ===")
    phbk = state.get('processed_hours_by_key', {})
    for k in sorted(phbk.keys()):
        if 'B15' in k:
            print(f"  {k}: {phbk[k]}")

    print("\n=== 'daily_data' or 'daily_records' in state? ===")
    for k in state.keys():
        v = state[k]
        if isinstance(v, dict):
            print(f"  {k}: dict with {len(v)} keys, sample: {list(v.keys())[:3]}")
        elif isinstance(v, list):
            print(f"  {k}: list with {len(v)} items")
        else:
            print(f"  {k}: {repr(v)[:50]}")

print("\nDONE")
