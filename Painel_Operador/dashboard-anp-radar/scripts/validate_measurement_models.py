from __future__ import annotations

import json
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = APP_DIR / "src" / "data" / "dashboard-data.json"


data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
summary = data.get("measurementModels", {}).get("summary", {})
required = ["files", "rows", "numericRows", "signals", "dailyAggregatesTotal", "dailyAggregatesPublished", "outputTruncated", "warnings"]
missing = [field for field in required if field not in summary]
if missing:
    raise SystemExit("missing measurement model summary fields: " + ", ".join(missing))
if summary.get("files", 0) <= 0:
    raise SystemExit("no model files ingested")
published = summary.get("dailyAggregatesPublished", 0)
total = summary.get("dailyAggregatesTotal", 0)
if not (0 <= published <= 5000):
    raise SystemExit(f"published aggregate count out of range: {published}")
if total < published:
    raise SystemExit(f"total aggregate count below published count: {total} < {published}")
operator_health = data.get("operatorPanelHealth", {})
operator_required = ["status", "required", "ready", "missingFiles", "missingInformation", "exports", "message"]
operator_missing = [field for field in operator_required if field not in operator_health]
if operator_missing:
    raise SystemExit("missing operator panel health fields: " + ", ".join(operator_missing))
if operator_health.get("required") != len(operator_health.get("exports") or []):
    raise SystemExit("operator panel required count does not match exports")
print("measurement models ok")
print(json.dumps(summary, ensure_ascii=False))
print("operator panel health ok")
print(json.dumps(operator_health, ensure_ascii=False))
