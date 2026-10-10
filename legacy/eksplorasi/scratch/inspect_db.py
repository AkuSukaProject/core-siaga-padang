import sqlite3
import pandas as pd
import os

db_path = "ranah_siaga.db"
print("DB File exists:", os.path.exists(db_path))
if os.path.exists(db_path):
    print("DB File size:", round(os.path.getsize(db_path) / (1024*1024), 2), "MB")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("\nDaftar Tabel:", tables)

for t in tables:
    print("\n" + "="*60)
    print(f"TABEL: {t}")
    print("="*60)
    
    # Count rows
    cursor.execute(f"SELECT COUNT(*) FROM {t}")
    count = cursor.fetchone()[0]
    print(f"Jumlah Baris: {count:,}")
    
    # Table Info (Schema)
    cursor.execute(f"PRAGMA table_info({t})")
    columns = cursor.fetchall()
    print("Skema Kolom:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
        
    # Sample Data
    print("\nSample Data (3 Baris Pertama):")
    df_sample = pd.read_sql_query(f"SELECT * FROM {t} LIMIT 3", conn)
    print(df_sample.to_string(index=False))

conn.close()
