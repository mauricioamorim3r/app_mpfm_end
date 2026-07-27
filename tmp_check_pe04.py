import sqlite3

def check_db():
    conn = sqlite3.connect('data/mpfm_local.db')
    cur = conn.cursor()
    cur.execute("SELECT row_kind, COUNT(*), MIN(day_ref), MAX(day_ref) FROM measurements_curated WHERE bank='B05' GROUP BY row_kind")
    print(cur.fetchall())
    
if __name__ == '__main__':
    check_db()
