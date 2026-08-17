import requests
import json

try:
    print("Testando API de histórico...")
    response = requests.get("http://127.0.0.1:8765/api/ops/processing-history?limit=2", timeout=10)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Runs retornados: {len(data.get('runs', []))}")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
except Exception as e:
    print(f"ERRO: {e}")
