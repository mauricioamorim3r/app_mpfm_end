import sqlite3, json
conn=sqlite3.connect('data/mpfm_local.db')
conn.row_factory=sqlite3.Row
c=conn.cursor()
for run_id in (845,844):
    r=c.execute('select id,status,source_ref,notes_json from processing_runs where id=?',(run_id,)).fetchone()
    print('\nRUN',run_id, dict(r) if r else None)
    rows=c.execute('select file_type,unit_code,meter_id,content_date,filename,processed_ok,message from files_imported where run_id=? order by content_date,file_type,filename',(run_id,)).fetchall()
    print('files',len(rows))
    for row in rows:
        print(dict(row))
conn.close()
