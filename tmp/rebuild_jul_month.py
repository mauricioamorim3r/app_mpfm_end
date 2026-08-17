import json
import urllib.request

req = urllib.request.Request(
    "http://localhost:8765/api/admin/recovery/rebuild-month",
    data=json.dumps({"month": "2026-07"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    print(json.loads(resp.read().decode("utf-8")))
