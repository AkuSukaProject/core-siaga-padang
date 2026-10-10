import sqlite3

conn = sqlite3.connect('ranah_siaga.db')
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
for name, sql in cur.fetchall():
    print(f"=== TABLE: {name} ===")
    print(sql)
    cur.execute(f'SELECT COUNT(*) FROM "{name}"')
    print(f"Count: {cur.fetchone()[0]}\n")

conn.close()
