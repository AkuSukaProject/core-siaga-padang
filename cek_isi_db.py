import sqlite3
import pandas as pd
import os

db_filename = "ranah_siaga_v3.db"

if not os.path.exists(db_filename):
    print(f"[ERROR] File database '{db_filename}' tidak ditemukan di direktori saat ini.")
    exit()

print("=" * 70)
print(f"  INSPEKSI LENGKAP DATABASE: {db_filename}")
print("=" * 70)

conn = sqlite3.connect(db_filename)
cur = conn.cursor()

# 1. Ambil Semua Daftar Tabel
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [t[0] for t in cur.fetchall()]

print(f"\n[INFO] Total Tabel Ditemukan: {len(tables)} tabel\n")

# 2. Iterasi & Tampilkan Detail Setiap Tabel
for idx, table_name in enumerate(tables, 1):
    # Jumlah Baris
    cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    row_count = cur.fetchone()[0]
    
    # Struktur Kolom
    cur.execute(f'PRAGMA table_info("{table_name}")')
    columns = cur.fetchall()
    col_details = [f"{col[1]} ({col[2]})" for col in columns]
    
    print(f"{'='*60}")
    print(f" {idx}. TABEL: '{table_name}'")
    print(f"    - Jumlah Baris : {row_count:,} data")
    print(f"    - Jumlah Kolom : {len(columns)}")
    print(f"    - Daftar Kolom : {', '.join(col_details)}")
    print(f"{'-'*60}")
    
    # Tampilkan 3 Sampel Data Pertama
    try:
        df_sample = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT 3', conn)
        print("    [Sampel Data 3 Baris Pertama]:")
        # Truncate kolom panjang jika ada
        pd.set_option('display.max_columns', 10)
        pd.set_option('display.width', 1000)
        print(df_sample.to_string(index=False))
    except Exception as e:
        print(f"    [NOTE] Tidak dapat menampilkan sampel: {e}")
    print("\n")

conn.close()
print("=" * 70)
print("  PEMERIKSAAN DATABASE SELESAI")
print("=" * 70)
