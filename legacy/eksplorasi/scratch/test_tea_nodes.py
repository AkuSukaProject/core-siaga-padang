import networkx as nx
import sqlite3
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import time
import os

print("=== PENGUJIAN ROUTING KE 12 TEA DENGAN DIJKSTRA ===")
start = time.time()

# 1. Buka database yang sudah ada atau baca graf
print("[1/3] Membaca tabel nodes dari ranah_siaga.db...")
conn = sqlite3.connect("ranah_siaga.db")
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon FROM tb_nodes", conn)
conn.close()
print(f"Total nodes: {len(df_nodes)}")

# 2. Buka CSV TEA
df_tea = pd.read_csv("data_tea_padang_lengkap_berkoordinat.csv")
print(f"Total TEA: {len(df_tea)}")

# 3. KDTree untuk mencari nearest node untuk masing-masing TEA
node_coords = np.radians(df_nodes[['lat', 'lon']].values)
tree = cKDTree(node_coords)

tea_coords = np.radians(df_tea[['lat', 'lon']].values)
dists, indices = tree.query(tea_coords)

df_tea['nearest_node_id'] = df_nodes.iloc[indices]['node_id'].values
df_tea['snap_dist_m'] = dists * 6371000.0 # meter

for idx, r in df_tea.iterrows():
    print(f"TEA {r['kode']}: {r['nama'][:30]}... -> Node {r['nearest_node_id']} (snap dist: {r['snap_dist_m']:.1f} m)")

print(f"\nWaktu pengujian KDTree: {time.time() - start:.2f} detik")
