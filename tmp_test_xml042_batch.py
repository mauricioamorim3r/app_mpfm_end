import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient
from server import app

print("Iniciando teste de lote do XML 042...", flush=True)

client = TestClient(app)

# 1. Obter candidatos
r1 = client.get('/api/xml042/candidates?month=2026-07')
print(f"Candidates status: {r1.status_code}", flush=True)
assert r1.status_code == 200
data1 = r1.json()
rows = data1.get("rows", [])
summary = data1.get("summary", {})
print(f"Total candidatos: {summary.get('rows')}", flush=True)
print(f"Elegíveis: {summary.get('eligible')}", flush=True)
print(f"Já gerados: {summary.get('generated')}", flush=True)
print(f"Pendentes elegíveis: {summary.get('pending_eligible')}", flush=True)

# 2. Executar processamento em lote
target_folder = r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3. Registros de Operação SGM Multifasico\3.7 Registros XML 042"
batch_payload = {
    "month": "2026-07",
    "cnpj8": "04028583",
    "target_dir": target_folder,
    "only_pending": True,
    "generated_by": "test-batch-user"
}
r2 = client.post('/api/xml042/batch-process', json=batch_payload)
print(f"Batch process status: {r2.status_code}", flush=True)
assert r2.status_code == 200
res2 = r2.json()
print(f"Processados: {res2.get('processed_count')}, Sucessos: {res2.get('success_count')}, Erros: {res2.get('error_count')}", flush=True)

# 3. Recarregar candidatos para verificar atualização de status
r3 = client.get('/api/xml042/candidates?month=2026-07')
data3 = r3.json()
summary3 = data3.get("summary", {})
print(f"Pós-lote - Já gerados: {summary3.get('generated')}, Pendentes elegíveis: {summary3.get('pending_eligible')}", flush=True)

# 4. Verificar se arquivos foram criados na pasta de destino
dest_path = Path(target_folder)
xml_files = list(dest_path.glob("*.xml"))
print(f"Arquivos XML na pasta OneDrive SGM 3.7: {len(xml_files)} arquivos encontrados.", flush=True)

# 5. Testar download em ZIP
r4 = client.get('/api/xml042/download-batch-zip?month=2026-07')
print(f"Download ZIP status: {r4.status_code}, tamanho: {len(r4.content)} bytes", flush=True)
assert r4.status_code == 200

print("\n✓ TODOS OS TESTES DO XML 042 FORAM CONCLUÍDOS COM SUCESSO!", flush=True)
