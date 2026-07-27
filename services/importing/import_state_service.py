from __future__ import annotations

import json


def load_import_state(work_dir, yr, mo):
    path = work_dir / f"state_{yr}_{mo}.json"
    if path.exists():
        try:
            return json.loads(path.read_text("utf-8"))
        except Exception:
            pass
    return {
        "yr": yr,
        "mo": mo,
        "processed": [],
        "sep_by_day": {},
        "processed_hours": {},
        "processed_hours_by_key": {},
        "sep_days": [],
        "file_notes": [],
    }


def save_import_state(work_dir, state: dict):
    path = work_dir / f"state_{state['yr']}_{state['mo']}.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")
