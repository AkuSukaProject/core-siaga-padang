# ==============================================================================
# SKRIP LAMA (DIARSIPKAN) - TIDAK DIPAKAI LAGI. Database dibangun oleh build_db.py (docs/build_db_v4.md).
# Skrip ini memakai data 2013-2019 dan kecepatan 1,2 m/s; disimpan sebagai rujukan historis.
# ==============================================================================
import sqlite3
import pandas as pd
import numpy as np
import networkx as nx
from scipy.spatial import cKDTree
import time
import os
import shutil
import hashlib
from datetime import datetime

print("=" * 80)
print("BUILDER DATABASE HYBRID SIAGA PADANG V2 (DENGAN INTEGRASI RESMI TEA)")
print("=" * 80)
start_total = time.time()

source_db = "ranah_siaga.db"
target_db = "ranah_siaga_v2.db"

if not os.path.exists(source_db):
    print(f"[ERROR] Source database '{source_db}' tidak ditemukan!")
    exit(1)

# 1. Salin seluruh data eksisting dari ranah_siaga.db ke ranah_siaga_v2.db
print(f"\n[1/5] Menyalin baseline database dari '{source_db}' ke '{target_db}'...")
if os.path.exists(target_db):
    os.remove(target_db)
shutil.copyfile(source_db, target_db)
print(f"      [OK] Baseline database berhasil disalin ({os.path.getsize(target_db)/(1024*1024):.2f} MB)")

# 2. Memuat Graf Padang Full untuk Perhitungan Rute ke 12 TEA
print(f"\n[2/5] Membaca peta jaringan jalan 'padang_full.graphml'...")
t0 = time.time()
G = nx.read_graphml("padang_full.graphml").to_undirected()
print(f"      [OK] Graf dimuat dalam {time.time() - t0:.2f} detik ({len(G.nodes)} nodes, {len(G.edges)} edges)")

# Memastikan atribut t0 (waktu tempuh dasar jalan kaki menit)
for u, v, data in G.edges(data=True):
    length_m = float(data.get('length', 50.0))
    if 't0' not in data:
        data['t0'] = length_m / (1.2 * 60.0) # 1.2 m/s BNPB -> menit
    else:
        data['t0'] = float(data['t0'])
    data['length_m'] = length_m

# 3. Menghubungkan 12 TEA ke Node Graf Terdekat
print(f"\n[3/5] Memetakan 12 TEA resmi BPBD ke simpul (junction nodes)...")
df_tea = pd.read_csv("data_tea_padang_lengkap_berkoordinat.csv")

conn = sqlite3.connect(target_db)
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon FROM tb_nodes", conn)

node_coords = np.radians(df_nodes[['lat', 'lon']].values)
tree = cKDTree(node_coords)
tea_coords = np.radians(df_tea[['lat', 'lon']].values)
dists, indices = tree.query(tea_coords)

df_tea['nearest_node_id'] = [int(df_nodes.iloc[i]['node_id']) for i in indices]
df_tea['snap_dist_m'] = dists * 6371000.0

tea_nodes = [str(n) for n in df_tea['nearest_node_id'].tolist()]

tea_info_map = {}
for idx, r in df_tea.iterrows():
    tea_id = f"TEA_{r['kode'].replace('TEA ', '')}"
    n_node = str(int(r['nearest_node_id']))
    tea_info_map[n_node] = {
        'tea_id': tea_id,
        'kode': r['kode'],
        'sektor': r['sektor'],
        'nama': str(r['nama']).replace(' (Rekomendasi)', ''),
        'kelurahan': r['kelurahan'],
        'kecamatan': r['kecamatan'],
        'tipe': r['tipe'],
        'kapasitas': float(r['kapasitas']),
        'lat': float(r['lat']),
        'lon': float(r['lon']),
        'node_id': int(r['nearest_node_id']),
        'rute': r['jalur']
    }
    print(f"      - {r['kode']}: {r['nama'][:38]}... -> Node {n_node}")

# 4. Komputasi Reverse Dijkstra Rute Evakuasi Horizontal Menuju 12 TEA
print(f"\n[4/5] Menghitung rute evakuasi horizontal optimal (Reverse Dijkstra ke 12 TEA)...")
t_dijk = time.time()
tea_dijkstra = {}
for n_node in tea_nodes:
    if n_node in G:
        lengths, paths = nx.single_source_dijkstra(G, source=n_node, weight='t0')
        tea_dijkstra[n_node] = (lengths, paths)
print(f"      [OK] Perhitungan 12 Dijkstra selesai dalam {time.time() - t_dijk:.2f} detik")

# Bangun data rute TEA untuk seluruh node di Kota Padang
tea_routes_data = []
tea_next_edges = set()
all_nodes_list = list(G.nodes)

for node in all_nodes_list:
    candidates = []
    for t_node in tea_nodes:
        if t_node in tea_dijkstra:
            lengths, paths = tea_dijkstra[t_node]
            if node in lengths:
                info = tea_info_map[t_node]
                candidates.append({
                    'tea_id': info['tea_id'],
                    'nama': info['nama'],
                    'eta': float(lengths[node]),
                    'path': paths[node][::-1] # dari origin ke TEA
                })
    
    if candidates:
        candidates.sort(key=lambda x: x['eta'])
        r1 = candidates[0]
        r2 = candidates[1] if len(candidates) > 1 else r1
        
        # Populate next edges for R1 and R2
        r1_path = r1['path']
        for i in range(len(r1_path) - 1):
            tea_next_edges.add((r1['tea_id'], int(r1_path[i]), int(r1_path[i+1])))
            
        r2_path = r2['path']
        for i in range(len(r2_path) - 1):
            tea_next_edges.add((r2['tea_id'], int(r2_path[i]), int(r2_path[i+1])))
        
        # Hitung jarak meter r1
        dist_m = r1['eta'] * 1.2 * 60.0 # meter
        
        tea_routes_data.append((
            int(node),
            r1['tea_id'],
            r1['nama'],
            round(r1['eta'], 2),
            round(dist_m, 1),
            r2['tea_id'],
            r2['nama'],
            round(r2['eta'], 2)
        ))

print(f"      [OK] Berhasil mengkalkulasi rute TEA untuk {len(tea_routes_data):,} titik persimpangan.")

# 5. Menulis Tabel tb_tea, tb_tea_routes, dan View v_fasilitas_evakuasi ke SQLite
print(f"\n[5/5] Memperbarui skema database '{target_db}'...")
cur = conn.cursor()

# Buat Tabel tb_tea
cur.execute("DROP TABLE IF EXISTS tb_tea")
cur.execute("""
CREATE TABLE tb_tea (
    tea_id TEXT PRIMARY KEY,
    kode_tea TEXT NOT NULL,
    sektor TEXT NOT NULL,
    nama_tea TEXT NOT NULL,
    kelurahan TEXT,
    kecamatan TEXT,
    tipe_fasilitas TEXT,
    kapasitas REAL NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    nearest_node_id INTEGER,
    rute_evakuasi TEXT
)
""")

tea_rows = []
for idx, r in df_tea.iterrows():
    t_info = tea_info_map[str(int(r['nearest_node_id']))]
    tea_rows.append((
        t_info['tea_id'],
        t_info['kode'],
        t_info['sektor'],
        t_info['nama'],
        t_info['kelurahan'],
        t_info['kecamatan'],
        t_info['tipe'],
        t_info['kapasitas'],
        t_info['lat'],
        t_info['lon'],
        t_info['node_id'],
        t_info['rute']
    ))

cur.executemany("INSERT INTO tb_tea VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tea_rows)
print(f"      [OK] Tabel 'tb_tea' berhasil dibuat ({len(tea_rows)} baris).")

# Buat Tabel tb_tea_routes
cur.execute("DROP TABLE IF EXISTS tb_tea_routes")
cur.execute("""
CREATE TABLE tb_tea_routes (
    origin_node_id INTEGER PRIMARY KEY,
    nearest_tea_id TEXT,
    nearest_tea_nama TEXT,
    nearest_tea_eta REAL,
    nearest_tea_dist_m REAL,
    alt_tea_id TEXT,
    alt_tea_nama TEXT,
    alt_tea_eta REAL
)
""")
cur.executemany("INSERT INTO tb_tea_routes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", tea_routes_data)
print(f"      [OK] Tabel 'tb_tea_routes' berhasil dibuat ({len(tea_routes_data):,} baris rute).")

# Buat VIEW Unified Facilities: v_fasilitas_evakuasi
cur.execute("DROP VIEW IF EXISTS v_fasilitas_evakuasi")
cur.execute("""
CREATE VIEW v_fasilitas_evakuasi AS
SELECT 
    tes_id AS facility_id,
    tes_id AS kode,
    nama_tes AS nama,
    'TES' AS jenis,
    'Vertikal' AS tipe_evakuasi,
    zona AS zona_sektor,
    kapasitas,
    lat,
    lon
FROM tb_tes
UNION ALL
SELECT 
    tea_id AS facility_id,
    kode_tea AS kode,
    nama_tea AS nama,
    'TEA' AS jenis,
    'Horizontal' AS tipe_evakuasi,
    sektor AS zona_sektor,
    kapasitas,
    lat,
    lon
FROM tb_tea
""")
print("      [OK] View 'v_fasilitas_evakuasi' (143 TES + 12 TEA) berhasil dibuat.")

# Buat Indeks Performa untuk Kueri Cepat di Android/Mobile
cur.execute("CREATE INDEX IF NOT EXISTS idx_tea_sektor ON tb_tea(sektor)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_tea_routes_tea_id ON tb_tea_routes(nearest_tea_id)")

# Buat Tabel tb_tea_next
cur.execute("DROP TABLE IF EXISTS tb_tea_next")
cur.execute("""
CREATE TABLE tb_tea_next (
    tea_id       TEXT    NOT NULL,
    node_id      INTEGER NOT NULL,
    next_node_id INTEGER NOT NULL,
    PRIMARY KEY (tea_id, node_id)
) WITHOUT ROWID;
""")

tea_next_list = list(tea_next_edges)
cur.executemany("INSERT INTO tb_tea_next VALUES (?, ?, ?)", tea_next_list)
print(f"      [OK] Tabel 'tb_tea_next' berhasil dibuat ({len(tea_next_list):,} baris).")

# Vacuum
print(f"\n      [OPTIMASI] Menjalankan VACUUM untuk mengecilkan ukuran file...")
conn.commit() # commit transaction before vacuum
cur.execute("VACUUM")

conn.commit()
conn.close()

# Generate Hash
def get_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

final_size_bytes = os.path.getsize(target_db)
final_size_mib = final_size_bytes / (1024 * 1024)
db_hash = get_sha256(target_db)
version_str = datetime.now().strftime("%Y.%m.%d")

print("\n" + "=" * 80)
print(f"[SUKSES] Database Baru Berhasil Dibangun: '{target_db}'")
print(f"Versi Data DB         : {version_str}")
print(f"Ukuran Database Final : {final_size_bytes:,} Byte ({final_size_mib:.2f} MiB)")
print(f"Checksum SHA-256      : {db_hash}")
print(f"Total Waktu Proses    : {time.time() - start_total:.2f} detik")
print("=" * 80)
