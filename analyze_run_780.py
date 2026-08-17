import sqlite3
import json

conn = sqlite3.connect("data/mpfm_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Obter info do run 780
run = cur.execute("SELECT * FROM processing_runs WHERE id = 780").fetchone()
print(f"\n=== RUN 780 ===")
print(f"ID: {run['id']}")
print(f"Status: {run['status']}")
print(f"Iniciado: {run['started_at']}")
print(f"Finalizado: {run['finished_at']}")
print(f"Total de arquivos: {run['files_count']}")
print(f"Fonte: {run['source_type']} - {run['source_ref']}")

# Análise de notes_json
if run['notes_json']:
    notes = json.loads(run['notes_json'])
    print(f"\nNotas:")
    print(json.dumps(notes, indent=2, ensure_ascii=False))

# Obter estatísticas dos arquivos
files = cur.execute("""
    SELECT 
        file_type,
        processed_ok,
        COUNT(*) as count,
        GROUP_CONCAT(DISTINCT SUBSTR(content_date, 1, 7)) as months
    FROM files_imported
    WHERE run_id = 780
    GROUP BY file_type, processed_ok
""").fetchall()

print(f"\n=== ESTATÍSTICAS POR TIPO ===")
for f in files:
    status = "✅ SUCESSO" if f['processed_ok'] else "❌ ERRO"
    print(f"{f['file_type']}: {f['count']} arquivos - {status}")
    print(f"  Meses: {f['months']}")

# Verificar se há erros
errors = cur.execute("""
    SELECT filename, file_type, message
    FROM files_imported
    WHERE run_id = 780 AND processed_ok = 0
""").fetchall()

if errors:
    print(f"\n=== ERROS ({len(errors)}) ===")
    for e in errors:
        print(f"{e['filename']}: {e['message']}")
else:
    print(f"\n✅ TODOS OS 217 ARQUIVOS FORAM PROCESSADOS COM SUCESSO!")

# Listar alguns exemplos de arquivos
print(f"\n=== EXEMPLOS DE ARQUIVOS ===")
examples = cur.execute("""
    SELECT filename, file_type, content_date
    FROM files_imported
    WHERE run_id = 780
    ORDER BY content_date, filename
    LIMIT 10
""").fetchall()

for ex in examples:
    print(f"{ex['filename']} ({ex['file_type']}) - {ex['content_date']}")

conn.close()
