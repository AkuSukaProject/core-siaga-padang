"""
PERBAIKAN FINAL: 
1. Polygon zona: pindahkan kelurahan perbukitan ke safe ✓ (sudah dilakukan)
2. Node is_safe: REVERT 5061 node yang salah diubah, kembalikan ke is_safe=1 (generous boundary)
3. Tambahkan node/simpang terdekat dari zona hijau ke is_safe=1

Strategi: 
- Zona polygon mengikuti batas kelurahan resmi 
- Tapi node is_safe menggunakan pendekatan generous: 
  node di area perbatasan tetap is_safe=1 untuk memberi opsi routing yang lebih baik
"""

import sqlite3
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
from scipy.spatial import cKDTree
import time

print("=" * 80)
print("PERBAIKAN FINAL: REVERT NODE + TAMBAH NODE TERDEKAT KE ZONA HIJAU")
print("=" * 80)

start = time.time()

conn = sqlite3.connect('ranah_siaga_v2.db')
cur = conn.cursor()

# ===== STEP 1: Revert 5061 nodes kembali ke is_safe=1 =====
print("\n[1/3] Mengembalikan node di batas zona ke is_safe=1 (generous boundary)...")

# Nodes yang sebelumnya safe (dari ranah_siaga.db) tapi di-update ke risk oleh script sebelumnya
# harus dikembalikan ke is_safe=1
conn_orig = sqlite3.connect('ranah_siaga.db')
df_orig = pd.read_sql_query("SELECT node_id, is_safe FROM tb_nodes", conn_orig)
conn_orig.close()

df_curr = pd.read_sql_query("SELECT node_id, is_safe FROM tb_nodes", conn)

# Merge to find nodes that were originally safe but now risk
merged = pd.merge(df_orig, df_curr, on='node_id', suffixes=('_orig', '_curr'))
wrongly_changed = merged[
    (merged['is_safe_orig'] == 1) & (merged['is_safe_curr'] == 0)
]['node_id'].tolist()

if wrongly_changed:
    # Update in batches
    batch_size = 500
    for i in range(0, len(wrongly_changed), batch_size):
        batch = wrongly_changed[i:i+batch_size]
        placeholders = ','.join(['?' for _ in batch])
        cur.execute(f"UPDATE tb_nodes SET is_safe = 1 WHERE node_id IN ({placeholders})", batch)
    print(f"  [OK] {len(wrongly_changed)} node dikembalikan ke is_safe=1")

# ===== STEP 2: Tambahkan node yang JELAS harus safe (dari kelurahan yang baru dipindah) =====
print("\n[2/3] Menambahkan node di kelurahan safe baru ke is_safe=1...")

# Load GeoJSON
gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

# Kelurahan yang baru dipindahkan ke safe
new_safe_kelurahan = [
    'AIR MANIS', 'BUNGUS TIMUR', 'TELUK KABUNG UTARA', 'TELUK KABUNG TENGAH',
    'TELUK KABUNG SELATAN', 'BUNGUS SELATAN', 'BUNGUS BARAT', 'GUNUNG SARIK',
    'PASAR AMBACANG', 'KALUMBUK'
]

# Get all nodes with coordinates
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon, is_safe FROM tb_nodes", conn)

# Spatial join nodes with new safe kelurahan
gdf_safe = gdf[gdf['NAMA_UPPER'].isin(new_safe_kelurahan)]
if len(gdf_safe) > 0:
    gdf_nodes = gpd.GeoDataFrame(
        df_nodes,
        geometry=[Point(lon, lat) for lon, lat in zip(df_nodes['lon'], df_nodes['lat'])],
        crs="EPSG:4326"
    )
    joined = gpd.sjoin(gdf_nodes, gdf_safe[['NAMA_UPPER', 'geometry']], how='inner', predicate='within')
    
    nodes_to_update = joined[joined['is_safe'] == 0]['node_id'].tolist()
    if nodes_to_update:
        batch_size = 500
        for i in range(0, len(nodes_to_update), batch_size):
            batch = [int(n) for n in nodes_to_update[i:i+batch_size]]
            placeholders = ','.join(['?' for _ in batch])
            cur.execute(f"UPDATE tb_nodes SET is_safe = 1 WHERE node_id IN ({placeholders})", batch)
        print(f"  [OK] {len(nodes_to_update)} node di kelurahan safe baru diupdate ke is_safe=1")
    else:
        print("  [--] Semua node di kelurahan safe baru sudah is_safe=1")

# ===== STEP 3: Tambahkan node TERDEKAT di sekitar batas zona hijau =====
print("\n[3/3] Menambahkan node/simpang terdekat ke zona hijau (buffer 200m dari batas zona safe)...")

# Re-read nodes after updates
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon, is_safe FROM tb_nodes", conn)

# Get safe nodes as anchor points
safe_nodes = df_nodes[df_nodes['is_safe'] == 1]
risk_nodes = df_nodes[df_nodes['is_safe'] == 0]

if len(safe_nodes) > 0 and len(risk_nodes) > 0:
    # Build KD-Tree of safe nodes
    safe_coords = np.radians(safe_nodes[['lat', 'lon']].values)
    tree = cKDTree(safe_coords)
    
    # For each risk node, find distance to nearest safe node
    risk_coords = np.radians(risk_nodes[['lat', 'lon']].values)
    dists, indices = tree.query(risk_coords)
    
    # Convert distance to meters (approximate)
    dist_m = dists * 6371000.0
    
    # Nodes within 200m of safe zone boundary should be added to safe
    BUFFER_METERS = 200
    nearby_mask = dist_m <= BUFFER_METERS
    nearby_nodes = risk_nodes.iloc[nearby_mask]['node_id'].tolist()
    
    if nearby_nodes:
        batch_size = 500
        for i in range(0, len(nearby_nodes), batch_size):
            batch = [int(n) for n in nearby_nodes[i:i+batch_size]]
            placeholders = ','.join(['?' for _ in batch])
            cur.execute(f"UPDATE tb_nodes SET is_safe = 1 WHERE node_id IN ({placeholders})", batch)
        print(f"  [OK] {len(nearby_nodes)} node terdekat (< {BUFFER_METERS}m dari batas hijau) ditambahkan ke zona hijau")
    else:
        print(f"  [--] Tidak ada node dalam radius {BUFFER_METERS}m")

# ===== VERIFIKASI AKHIR =====
print("\n" + "=" * 80)
print("VERIFIKASI AKHIR")
print("=" * 80)

cur.execute("SELECT COUNT(*) FROM tb_inundation_zones")
print(f"  Zona Inundation (risiko): {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM tb_safe_zones")
print(f"  Zona Safe (hijau):        {cur.fetchone()[0]}")

cur.execute("SELECT is_safe, COUNT(*) FROM tb_nodes GROUP BY is_safe")
for r in cur.fetchall():
    label = "AMAN (Hijau)" if r[0] == 1 else "RISIKO"
    print(f"  Node is_safe={r[0]} ({label:15s}): {r[1]:6d}")

# Show sample of new safe kelurahan
print("\n  === Kelurahan Safe (total dari DB) ===")
cur.execute("SELECT nama_zona FROM tb_safe_zones ORDER BY nama_zona")
for r in cur.fetchall():
    print(f"    - {r[0]}")

# Commit
conn.commit()
cur.execute("VACUUM")
conn.commit()
conn.close()

print(f"\n[SUKSES] Perbaikan final selesai dalam {time.time() - start:.2f} detik!")
