import sqlite3
conn = sqlite3.connect('data/mpfm_local.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
print('--- ultimas 6 runs ---')
for r in cur.execute("SELECT id, source_type, source_ref, status, started_at, finished_at, files_count FROM processing_runs ORDER BY id DESC LIMIT 6"):
    print(dict(r))

print()
print('--- runs em status running ---')
for r in cur.execute("SELECT id, source_type, source_ref, status, started_at FROM processing_runs WHERE status='running'"):
    print(dict(r))
