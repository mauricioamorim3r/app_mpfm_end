import sqlite3
import time

DB_PATH = "data/mpfm_local.db"

print("Conectando ao banco...")
conn = sqlite3.connect(DB_PATH, timeout=30.0)
cur = conn.cursor()

print("1. Buscando runs recentes...")
recent_runs_sql = """
    SELECT id FROM processing_runs
    ORDER BY id DESC
    LIMIT ?
"""
start = time.time()
recent_run_ids = [row[0] for row in cur.execute(recent_runs_sql, (5,)).fetchall()]
print(f"   Encontrados {len(recent_run_ids)} runs em {time.time()-start:.3f}s")
print(f"   IDs: {recent_run_ids}")

if recent_run_ids:
    print("\n2. Buscando arquivos dessas runs...")
    placeholders = ','.join('?' * len(recent_run_ids))
    sql = f"""
        SELECT
            pr.id, pr.started_at, pr.finished_at, pr.source_type,
            pr.source_ref, pr.files_count, pr.status, pr.notes_json,
            fi.filename, fi.file_type, fi.content_date, fi.processed_ok, fi.message
        FROM processing_runs pr
        LEFT JOIN files_imported fi ON fi.run_id = pr.id
        WHERE pr.id IN ({placeholders})
        ORDER BY pr.id DESC, fi.id
    """
    
    start = time.time()
    rows = cur.execute(sql, tuple(recent_run_ids)).fetchall()
    print(f"   Retornou {len(rows)} linhas em {time.time()-start:.3f}s")
    
    # Agrupar
    print("\n3. Agrupando dados...")
    runs_dict = {}
    for row in rows:
        run_id = row[0]
        if run_id not in runs_dict:
            runs_dict[run_id] = {"id": run_id, "files": [], "months": set()}
        if row[8]:  # filename
            runs_dict[run_id]["files"].append(row[8])
            if row[10]:  # content_date
                runs_dict[run_id]["months"].add(row[10][:7])
    
    print(f"   Runs agrupados: {len(runs_dict)}")
    for rid, data in runs_dict.items():
        print(f"     Run {rid}: {len(data['files'])} arquivos, meses: {sorted(data['months'])}")

conn.close()
print("\n✅ Teste concluído")
