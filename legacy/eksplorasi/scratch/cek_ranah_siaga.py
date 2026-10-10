import sqlite3
import pandas as pd

db_path = "ranah_siaga.db"
print(f"=== INSPEKSI DATABASE: {db_path} ===")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]

print(f"Ditemukan {len(tables)} tabel:")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM \"{t}\"")
    cnt = cur.fetchone()[0]
    print(f"\n[TABEL] '{t}' ({cnt:,} baris)")
    
    # Structure
    cur.execute(f"PRAGMA table_info(\"{t}\")")
    cols = cur.fetchall()
    col_names = [c[1] for c in cols]
    col_types = [c[2] for c in cols]
    print("   Struktur Kolom:", ", ".join([f"{name} ({tp})" for name, tp in zip(col_names, col_types)]))
    
    # Sample
    df_sample = pd.read_sql_query(f"SELECT * FROM \"{t}\" LIMIT 3", conn)
    print("   Sampel Data (3 baris pertama):")
    print(df_sample.to_string(index=False))

conn.close()
