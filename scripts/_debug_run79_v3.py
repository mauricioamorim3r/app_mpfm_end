"""Debug: Verifica tabelas chave do run 79."""
import sqlite3

db = r'data/mpfm_local.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== COLUNAS parsing_events_raw ===")
cols = [r[1] for r in conn.execute("PRAGMA table_info(parsing_events_raw)").fetchall()]
print(cols)

print()
print("=== COLUNAS validation_issues ===")
try:
    cols2 = [r[1] for r in conn.execute("PRAGMA table_info(validation_issues)").fetchall()]
    print(cols2)
except:
    print("Tabela não encontrada")

print()
print("=== COLUNAS source_files_raw ===")
cols3 = [r[1] for r in conn.execute("PRAGMA table_info(source_files_raw)").fetchall()]
print(cols3)

print()
print("=== validation_issues for run 79 ===")
try:
    rows = conn.execute("SELECT * FROM validation_issues WHERE run_id=79 LIMIT 10").fetchall()
    for r in rows:
        print(dict(r))
    if not rows:
        print("(nenhum)")
except Exception as e:
    print(f"Erro: {e}")

print()
print("=== parsing_events_raw for run 79 (sample) ===")
rows = conn.execute("SELECT * FROM parsing_events_raw WHERE run_id=79 LIMIT 5").fetchall()
for r in rows:
    print(dict(r))

print()
print("=== measurements_curated for run 79 ===")
cnt = conn.execute("SELECT COUNT(*) FROM measurements_curated WHERE run_id=79").fetchone()[0]
print(f"Total: {cnt}")
cnt_h = conn.execute("SELECT COUNT(*) FROM measurements_curated WHERE run_id=79 AND row_kind='hourly'").fetchone()[0]
print(f"Hourly: {cnt_h}")
cnt_d = conn.execute("SELECT COUNT(*) FROM measurements_curated WHERE run_id=79 AND row_kind='daily'").fetchone()[0]
print(f"Daily: {cnt_d}")

print()
print("=== source_files_raw for run 79 (sample) ===")
rows = conn.execute("SELECT * FROM source_files_raw WHERE run_id=79 LIMIT 3").fetchall()
for r in rows:
    print(dict(r))

conn.close()
print("\n=== DONE ===")
