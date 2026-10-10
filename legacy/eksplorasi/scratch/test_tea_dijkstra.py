import networkx as nx
import sqlite3
import pandas as pd
import numpy as np
import time

print("=== PENGUJIAN KECEPATAN DIJKSTRA DARI 12 TEA ===")
start = time.time()

# 1. Buka padang_full.graphml
print("[1/3] Membaca padang_full.graphml...")
t0 = time.time()
G = nx.read_graphml("padang_full.graphml").to_undirected()
print(f"Graf selesai dibaca dalam {time.time() - t0:.2f} detik. Total node: {len(G.nodes)}, total edge: {len(G.edges)}")

# Pastikan bobot t0 ada di setiap edge
# Jika t0 belum ada, hitung t0 = length / (1.2 m/s * 60 s/menit)
for u, v, data in G.edges(data=True):
    if 't0' not in data:
        length_m = float(data.get('length', 50.0))
        data['t0'] = length_m / (1.2 * 60.0) # dalam menit
    else:
        data['t0'] = float(data['t0'])

# 2. Ambil 12 nearest node ID
df_tea = pd.read_csv("data_tea_padang_lengkap_berkoordinat.csv")
conn = sqlite3.connect("ranah_siaga.db")
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon FROM tb_nodes", conn)
conn.close()

from scipy.spatial import cKDTree
node_coords = np.radians(df_nodes[['lat', 'lon']].values)
tree = cKDTree(node_coords)
tea_coords = np.radians(df_tea[['lat', 'lon']].values)
dists, indices = tree.query(tea_coords)
df_tea['nearest_node_id'] = [str(df_nodes.iloc[i]['node_id']) for i in indices]

tea_nodes = df_tea['nearest_node_id'].tolist()
print(f"[2/3] 12 TEA nodes: {tea_nodes}")

# 3. Jalankan Dijkstra dari 12 TEA
print("[3/3] Menjalankan Reverse Dijkstra dari 12 TEA...")
t_dijk = time.time()
tea_dijkstra = {}
for idx, t_node in enumerate(tea_nodes):
    if t_node in G:
        lengths, paths = nx.single_source_dijkstra(G, source=t_node, weight='t0')
        tea_dijkstra[t_node] = (lengths, paths)
        print(f"  - TEA #{idx+1} ({t_node}) selesai: mencakup {len(lengths)} titik.")
    else:
        print(f"  [!] Node {t_node} tidak ditemukan di graf!")

print(f"Seluruh 12 Reverse Dijkstra selesai dalam {time.time() - t_dijk:.2f} detik!")
