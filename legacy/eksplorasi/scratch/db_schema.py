import sqlite3

db_path = 'c:/gemastik/ranah_siaga_v2.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

for table in tables:
    cursor.execute(f"PRAGMA table_info({table[0]})")
    print(f'\nSchema for {table[0]}:')
    for col in cursor.fetchall():
        print(f'  {col[1]} ({col[2]})')
