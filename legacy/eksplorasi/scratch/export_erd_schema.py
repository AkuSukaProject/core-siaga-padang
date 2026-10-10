import sqlite3

conn = sqlite3.connect("ranah_siaga.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cursor.fetchall() if r[0] != 'sqlite_sequence']

print("=== SCHEMAS UNTUK ERD SHEVA ===")
for t in tables:
    print(f"\n--- TABEL: {t} ---")
    cursor.execute(f"PRAGMA table_info({t})")
    cols = cursor.fetchall()
    for c in cols:
        pk_str = " (PRIMARY KEY)" if c[5] == 1 else ""
        print(f"  - {c[1]} : {c[2]}{pk_str}")

conn.close()
