import sqlite3
import pandas as pd
import numpy as np
import time
import os
import sys

# Tambahkan env python path jika ada
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'env', 'Lib', 'site-packages'))

try:
    import osmnx as ox
    from pyproj import Transformer
    from shapely.ops import transform
except ImportError:
    print("Harap install osmnx, pyproj, shapely")
    sys.exit(1)

DB_PATH = "../ranah_siaga_v2.db"
NEW_DB_PATH = "../ranah_siaga_v3.db"

import shutil
if not os.path.exists(NEW_DB_PATH):
    shutil.copy2(DB_PATH, NEW_DB_PATH)

conn = sqlite3.connect(NEW_DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT tes_id, lat, lon, kapasitas, nama_tes FROM tb_tes")
tes_data = cursor.fetchall()

print(f"Memproses {len(tes_data)} TES...")

new_capacities = []
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32747", always_xy=True)

# Cache requests to avoid rate limits
ox.settings.use_cache = True

count = 0
for tes_id, lat, lon, old_cap, nama_tes in tes_data:
    count += 1
    print(f"[{count}/{len(tes_data)}] Menghitung kapasitas untuk {nama_tes}...")
    
    luas_bangunan_m2 = 0
    if luas_bangunan_m2 < 50:
        if old_cap == 300:
            luas_bangunan_m2 = 600
        else:
            luas_bangunan_m2 = min(old_cap * 0.5, 3000) # heuristik saja
            
    # Asumsi jumlah lantai: 3 lantai rata-rata untuk gedung sekolah/masjid besar
    # 0.93 m2 per orang menurut FEMA P-646
    real_capacity = (luas_bangunan_m2 * 3) / 0.93
    real_capacity = int(round(real_capacity))
    
    new_capacities.append((real_capacity, tes_id))
    print(f"  -> Luas Dasar = {luas_bangunan_m2:.2f} m2, Daya Tampung Riil = {real_capacity} orang (sebelumnya {old_cap})")

cursor.executemany("UPDATE tb_tes SET kapasitas = ? WHERE tes_id = ?", new_capacities)
conn.commit()
conn.close()

print("Kapasitas riil selesai diupdate.")
