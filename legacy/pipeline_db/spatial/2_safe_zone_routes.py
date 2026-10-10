import sqlite3
import pandas as pd
import networkx as nx
import time
import os

DB_PATH = "../ranah_siaga_v3.db"

print("Memuat data jaringan jalan...")
G = nx.read_graphml("../padang_full.graphml").to_undirected()

# Hitung bobot waktu jalan kaki (t0)
for u, v, data in G.edges(data=True):
    length_m = float(data.get('length', 50.0))
    if 't0' not in data:
        data['t0'] = length_m / (1.2 * 60.0) 
    else:
        data['t0'] = float(data['t0'])

print("Koneksi ke database untuk mencari node aman (is_safe = 1)...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Hapus tabel jika sudah ada
cursor.execute("DROP TABLE IF EXISTS tb_safe_routes")
cursor.execute("DROP TABLE IF EXISTS tb_safe_next")

cursor.execute('''CREATE TABLE tb_safe_routes (
                    origin_node_id INTEGER PRIMARY KEY, 
                    safe_node_id INTEGER, 
                    safe_zone_nama TEXT, 
                    safe_eta REAL)''')

cursor.execute('''CREATE TABLE tb_safe_next (
                    node_id INTEGER, 
                    next_node_id INTEGER,
                    PRIMARY KEY (node_id, next_node_id))''')

cursor.execute("SELECT node_id FROM tb_nodes WHERE is_safe = 1")
safe_nodes_db = [str(r[0]) for r in cursor.fetchall()]

# Filter yang ada di graph
safe_nodes = [n for n in safe_nodes_db if n in G.nodes]
print(f"Jumlah node aman: {len(safe_nodes)}")

print("Menjalankan Multi-source Dijkstra (Reverse)...")
t0 = time.time()
lengths, paths = nx.multi_source_dijkstra(G, sources=safe_nodes, weight='t0')
print(f"Dijkstra selesai dalam {time.time() - t0:.2f} detik.")

routes_data = []
next_data = set()

# Paths adalah dari safe_node (source) ke origin_node (target).
# Untuk warga, rutenya adalah origin_node -> safe_node.
# Jadi path-nya dibalik.
print("Membangun rute untuk disimpan ke database...")
count = 0
for target_node, path_from_safe in paths.items():
    if target_node not in lengths: continue
    
    eta = lengths[target_node]
    # Balik rutenya agar menjadi origin -> ... -> safe
    path_to_safe = path_from_safe[::-1]
    
    safe_node_id = int(path_to_safe[-1])
    origin_node_id = int(target_node)
    
    routes_data.append((origin_node_id, safe_node_id, "Zona Aman (Dataran Tinggi)", eta))
    
    # Simpan langkah selanjutnya
    for i in range(len(path_to_safe) - 1):
        u = int(path_to_safe[i])
        v = int(path_to_safe[i+1])
        next_data.add((u, v))

cursor.executemany("INSERT INTO tb_safe_routes VALUES (?, ?, ?, ?)", routes_data)
cursor.executemany("INSERT OR IGNORE INTO tb_safe_next VALUES (?, ?)", list(next_data))

conn.commit()
conn.close()
print(f"Berhasil menyimpan {len(routes_data)} rute ke zona aman.")
