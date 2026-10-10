import sqlite3
import os
import zipfile
import gzip
import shutil

db_file = "ranah_siaga_v2.db"
orig_size = os.path.getsize(db_file) / (1024 * 1024)
print(f"1. Ukuran Database Asli : {orig_size:.2f} MB")

# 1. Analisis Ukuran Tiap Tabel dengan PRAGMA page_count
conn = sqlite3.connect(db_file)
cur = conn.cursor()

# Coba VACUUM dulu untuk melihat apakah ada sisa fragmen
t0 = os.path.getsize(db_file)
cur.execute("VACUUM")
conn.commit()
conn.close()

vacuum_size = os.path.getsize(db_file) / (1024 * 1024)
print(f"2. Ukuran Setelah VACUUM : {vacuum_size:.2f} MB")

# 2. Uji Kompresi Lossless (GZIP & ZIP)
zip_file = "ranah_siaga_v2.db.zip"
with zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    zf.write(db_file, arcname="ranah_siaga_v2.db")
zip_size = os.path.getsize(zip_file) / (1024 * 1024)
print(f"3. Ukuran Kompresi ZIP (.zip) : {zip_size:.2f} MB (Hemat: {(1 - zip_size/orig_size)*100:.1f}%)")

gz_file = "ranah_siaga_v2.db.gz"
with open(db_file, 'rb') as f_in, gzip.open(gz_file, 'wb', compresslevel=9) as f_out:
    shutil.copyfileobj(f_in, f_out)
gz_size = os.path.getsize(gz_file) / (1024 * 1024)
print(f"4. Ukuran Kompresi GZIP (.gz) : {gz_size:.2f} MB (Hemat: {(1 - gz_size/orig_size)*100:.1f}%)")

# 3. Analisis apa yang paling memakan tempat di dalam tabel
conn = sqlite3.connect(db_file)
cur = conn.cursor()
tables = ['tb_nodes', 'tb_edges', 'tb_tes', 'tb_routes', 'tb_tea', 'tb_tea_routes', 'tb_inundation_zones', 'tb_safe_zones']
print("\n--- ANALISIS ISI DATA PER TABEL ---")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    
    # Ambil sampel rata-rata panjang teks per baris
    cur.execute(f"PRAGMA table_info({t})")
    cols = [c[1] for c in cur.fetchall()]
    print(f"Tabel {t:<18} : {cnt:,} baris | Kolom: {', '.join(cols[:4])}...")

conn.close()
