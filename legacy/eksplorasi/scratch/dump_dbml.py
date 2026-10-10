import sqlite3, os

print("=== INSPEKSI SCHEMA UNTUK DBDAGRAM.IO ===")

for db_path in ['ranah_siaga.db', 'database_evakuasi_padang.sqlite']:
    if not os.path.exists(db_path):
        continue
    print(f"\n==================== DATABASE: {db_path} ====================")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall() if r[0] != 'sqlite_sequence']
    
    for tname in tables:
        cursor.execute(f"PRAGMA table_info({tname});")
        cols = cursor.fetchall()
        print(f"\nTabel `{tname}` ({len(cols)} kolom):")
        for c in cols:
            pk_flag = " [pk]" if c[5] >= 1 else ""
            not_null = " [not null]" if c[3] == 1 else ""
            print(f"  {c[1]:<25} {c[2]:<10}{pk_flag}{not_null}")
            
        cursor.execute(f"PRAGMA foreign_key_list({tname});")
        fks = cursor.fetchall()
        if fks:
            print("  Foreign Keys:")
            for fk in fks:
                print(f"    Ref: {c[1]} -> {fk[2]}.{fk[4]}")
    conn.close()
