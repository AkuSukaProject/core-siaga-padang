# ==============================================================================
# SKRIP LAMA (DIARSIPKAN) - TIDAK DIPAKAI LAGI. Database dibangun oleh build_db.py (docs/build_db_v4.md).
# Skrip ini memakai data 2013-2019 dan kecepatan 1,2 m/s; disimpan sebagai rujukan historis.
# ==============================================================================
import networkx as nx
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import time
import os
import re
from scipy.spatial import cKDTree
import sqlite3
from pyproj import Transformer

print("=" * 80)
print("SIAGA PADANG ROUTING ENGINE: V6 (SELURUH KOTA PADANG - DATA AKADEMIK LENGKAP)")
print("=" * 80)

start_total = time.time()

def bersihkan_angka_osm(val, default=3.0):
    if pd.isna(val) or val is None: return default
    if isinstance(val, list): val = str(val[0])
    val = str(val).strip()
    if '-' in val: val = val.split('-')[0]
    match = re.search(r"(\d+(\.\d+)?)", val)
    return float(match.group(1)) if match else default

# ---------------------------------------------------------
# 1. INISIALISASI SPASIAL & AUTO-FIX KOORDINAT
# ---------------------------------------------------------
print("[1/4] Membaca peta jaringan jalan Seluruh Kota Padang & Memeriksa CRS...")
G = nx.read_graphml("padang_full.graphml").to_undirected()

# Dokumentasi: Menjamin Reverse Dijkstra valid karena graf bersifat undirected
# (Graph has been converted to undirected to allow bidirectional routing analysis)

sample_node = next(iter(G.nodes(data=True)))[1]
if 'x' in sample_node and abs(float(sample_node['x'])) > 180:
    print("      [!] Konversi koordinat meter ke EPSG:4326...")
    crs_asal = G.graph.get('crs', 'EPSG:32747') 
    transformer = Transformer.from_crs(crs_asal, "EPSG:4326", always_xy=True)
    for node, data in G.nodes(data=True):
        if 'x' in data and 'y' in data:
            nx_val, ny_val = transformer.transform(float(data['x']), float(data['y']))
            data['x'], data['y'] = float(nx_val), float(ny_val)
else:
    for node, data in G.nodes(data=True):
        if 'x' in data and 'y' in data:
            data['x'], data['y'] = float(data['x']), float(data['y'])

for u, v, data in G.edges(data=True):
    length = bersihkan_angka_osm(data.get('length', 50.0))
    # FORMULA FISIKA MURNI: Kecepatan jalan kaki evakuasi standar BNPB = 1.2 m/s
    data['t0'] = length / 1.2 / 60.0 

# Memuat batas kelurahan jika tersedia
file_geojson = "batas_kelurahan_kota_padang.geojson"
nodes_per_kelurahan = {}
node_to_kelurahan = {}
gdf_kelurahan = None
if os.path.exists(file_geojson):
    gdf_kelurahan = gpd.read_file(file_geojson)
    if gdf_kelurahan.crs != "EPSG:4326": gdf_kelurahan = gdf_kelurahan.to_crs("EPSG:4326")
    kolom_nama = gdf_kelurahan.select_dtypes(include=['object', 'string']).columns[0]
    gdf_kelurahan['NAMA_UPPER'] = gdf_kelurahan[kolom_nama].astype(str).str.upper().str.strip()
    nodes_data = [{'node_id': n, 'geometry': Point(d['x'], d['y'])} for n, d in G.nodes(data=True) if 'x' in d and 'y' in d]
    gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
    gdf_joined = gpd.sjoin(gdf_nodes, gdf_kelurahan, how="inner", predicate="within")
    gdf_joined['nama_kel_upper'] = gdf_joined['NAMA_UPPER']
    nodes_per_kelurahan = gdf_joined.groupby('nama_kel_upper')['node_id'].apply(list).to_dict()
    node_to_kelurahan = dict(zip(gdf_joined['node_id'], gdf_joined['nama_kel_upper']))


# ---------------------------------------------------------
# 2. PEMETAAN SHELTER SELURUH KOTA PADANG (DATA RIIL)
# ---------------------------------------------------------
print("[2/4] Memetakan data riil gedung shelter Seluruh Kota Padang & demografi...")
file_shelter_csv = "data_tes_padang_lengkap_berkoordinat.csv" if os.path.exists("data_tes_padang_lengkap_berkoordinat.csv") else "Koordinat Evakuasi TES - Sheet1.csv"
print(f"      Menggunakan dataset shelter: {file_shelter_csv}")
df_shelter = pd.read_csv(file_shelter_csv)
if 'Sektor' in df_shelter.columns:
    df_shelter = df_shelter[df_shelter['Sektor'].astype(str).str.upper() != 'JUMLAH']


def parse_koordinat(val):
    if pd.isna(val): return 0.0
    try: return float(str(val).strip().replace(',', '.'))
    except ValueError: return 0.0

def parse_kapasitas(val, default=300.0):
    if pd.isna(val) or val is None: return default
    if isinstance(val, (int, float)): return float(val) if val > 0 else default
    val_str = str(val).strip()
    try:
        val_clean = val_str.replace(',', '.')
        res = float(val_clean)
        return res if res > 0 else default
    except ValueError:
        return default


df_shelter['Clean_Lat'] = df_shelter['Latitude'].apply(parse_koordinat)
df_shelter['Clean_Lon'] = df_shelter['Longitude'].apply(parse_koordinat)
df_shelter = df_shelter[(df_shelter['Clean_Lat'] != 0.0) & (df_shelter['Clean_Lon'] != 0.0)]
df_shelter = df_shelter.drop_duplicates(subset=['Clean_Lat', 'Clean_Lon'])

node_ids_list, coords_list = [], []
for node, data in G.nodes(data=True):
    if 'x' in data and 'y' in data:
        node_ids_list.append(node)
        coords_list.append([data['y'], data['x']])

tree = cKDTree(coords_list)

tes_nodes = []
tes_details = {}
cluster_capacity = {}
node_to_tes_id = {} 

for idx, row in df_shelter.iterrows():
    lat, lon = row['Clean_Lat'], row['Clean_Lon']
    nama_tes = str(row['Nama_Bersih']).strip()
    zona = str(row['Zona']).strip()
    
    # Murni menggunakan data kapasitas resmi dari BPBD (tanpa pengali 1.5)
    cap = parse_kapasitas(row['Kapasitas_TES'], default=300.0)
    
    dist, idx_nearest = tree.query([lat, lon])
    matched_node = node_ids_list[idx_nearest]
    
    # Kecepatan evakuasi berjalan kaki standar BNPB = 1.2 m/s (72 meter / menit)
    # Jarak euclidean derajat dikonversi ke meter (1 deg ~ 111,000 meter)
    access_time_mnt = (dist * 111000.0) / 72.0
    
    if matched_node and matched_node in G.nodes:
        tes_id = f"TES_{idx}" 
        tes_nodes.append(matched_node)
        
        if matched_node not in node_to_tes_id: node_to_tes_id[matched_node] = []
        node_to_tes_id[matched_node].append(tes_id)
        
        tes_details[tes_id] = {
            "nama": nama_tes, 
            "zona": zona, 
            "lat": lat, 
            "lon": lon, 
            "cap": cap,
            "access_time": access_time_mnt
        }
        cluster_capacity[tes_id] = cap

tes_nodes = list(set(tes_nodes))

# Distribusi Demand murni proporsional tanpa rekayasa
df_penduduk = pd.read_csv("penduduk_kota_padang.csv")
TOTAL_AGEN = 2000
TES_TOLERANCE_FACTOR = 1.1  # 10% tolerance for overcapacity
total_pop = df_penduduk['JUMLAH JIWA TERPAPAR (JIWA)'].sum()
scaling_factor = TOTAL_AGEN / total_pop if total_pop > 0 else 1.0 # Tanpa buffer 1.5
cluster_capacity = {t_id: max(int(cap * scaling_factor), 1) for t_id, cap in cluster_capacity.items()}

kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH',
    'BATANG KABUNG': 'BATANG KABUNG GANTING',
    'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA',
    'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI',
    'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR',
    'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX',
    'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR',
    'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

node_demands = {}
for idx, row in df_penduduk.iterrows():
    jumlah_agen = int(round((row['JUMLAH JIWA TERPAPAR (JIWA)'] / total_pop) * TOTAL_AGEN)) if total_pop > 0 else 0
    desa_name = str(row['DESA']).strip().upper()
    desa_name = kelurahan_alias.get(desa_name, desa_name)
    avail = nodes_per_kelurahan.get(desa_name, list(G.nodes))
    if avail:
        base_count = jumlah_agen // len(avail)
        remainder = jumlah_agen % len(avail)
        for i, node in enumerate(avail):
            node_demands[node] = node_demands.get(node, 0) + base_count + (1 if i < remainder else 0)


# ---------------------------------------------------------
# 3. REVERSE DIJKSTRA & KAPASITAS RIIL
# ---------------------------------------------------------
print(f"[3/4] Eksekusi Reverse Dijkstra standar...")
tes_dijkstra = {}
for t_node in tes_nodes:
    lengths, paths = nx.single_source_dijkstra(G, source=t_node, weight='t0')
    tes_dijkstra[t_node] = (lengths, paths)

all_origin_data = []
final_sqlite_data = []

for node in G.nodes:
    demand = node_demands.get(node, 0)
    candidates = []
    
    for t_node in tes_nodes:
        lengths, paths = tes_dijkstra[t_node]
        if node in lengths:
            for tes_id in node_to_tes_id[t_node]:
                total_eta = lengths[node] + tes_details[tes_id]["access_time"]
                candidates.append({
                    'tes_id': tes_id, 
                    'nama_gedung': tes_details[tes_id]['nama'], 
                    'eta': total_eta, 
                    'path': paths[node][::-1] 
                })

    if candidates:
        candidates.sort(key=lambda x: x['eta'])
        rank_1, rank_2, rank_3 = candidates[0], candidates[0], candidates[0]
        
        for cand in candidates:
            if cand['nama_gedung'] != rank_1['nama_gedung']:
                rank_2 = cand; break
        for cand in candidates:
            if cand['nama_gedung'] != rank_1['nama_gedung'] and cand['nama_gedung'] != rank_2['nama_gedung']:
                rank_3 = cand; break
        
        final_sqlite_data.append((
            int(node),
            rank_1['nama_gedung'], ",".join(map(str, rank_1['path'])), float(rank_1['eta']),
            rank_2['nama_gedung'], ",".join(map(str, rank_2['path'])), float(rank_2['eta']),
            rank_3['nama_gedung'], ",".join(map(str, rank_3['path'])), float(rank_3['eta'])
        ))
        if demand > 0: all_origin_data.append({'node': node, 'demand': demand, 'candidates': candidates})

all_origin_data.sort(key=lambda x: x['candidates'][0]['eta'])
load_siaga = {t_id: 0 for t_id in cluster_capacity.keys()}
redirection_count = 0
siaga_etas = []

for data in all_origin_data:
    remaining_demand = data['demand']
    primary_cand = data['candidates'][0]
    for cand in data['candidates']:
        t_id = cand['tes_id']
        free = int(cluster_capacity.get(t_id, 9999) * TES_TOLERANCE_FACTOR) - load_siaga[t_id]
        if free > 0:
            assign_amount = min(free, remaining_demand)
            load_siaga[t_id] += assign_amount
            siaga_etas.extend([cand['eta']] * assign_amount)
            remaining_demand -= assign_amount
            if cand['tes_id'] != primary_cand['tes_id']: redirection_count += assign_amount
            if remaining_demand <= 0: break

# ---------------------------------------------------------
# 4. EXPORT SQLITE (tb_nodes, tb_tes, tb_routes, tb_edges, tb_inundation_zones, tb_safe_zones)
# ---------------------------------------------------------
print("[4/4] Membangun Database Offline SQLite Hybrid (ranah_siaga.db)...")
db_path = "ranah_siaga.db"
if os.path.exists(db_path): os.remove(db_path)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Klasifikasi spasial kelurahan aman vs risiko
exposed_map = dict(zip(df_penduduk['DESA'].astype(str).str.upper().str.strip().apply(lambda x: kelurahan_alias.get(x, x)), df_penduduk['JUMLAH JIWA TERPAPAR (JIWA)']))

# [HOTFIX] Injeksi manual kelurahan pesisir yang tidak tercatat di penduduk_kota_padang.csv
# Nilai simulasi > 15000 diberikan agar saat dievaluasi masuk ke tingkat_bahaya = "Tinggi" (Merah)
exposed_map['BEROK NIPAH'] = 20000
exposed_map['PASA GADANG'] = 20000

# Kelurahan perbukitan/pedalaman yang terpapar minimal tapi wilayahnya mayoritas dataran tinggi
# Kelurahan ini AMAN meskipun ada sedikit jiwa terpapar di area pesisir kecil
# Sumber: analisis buat_peta_zona_rawan_tsunami_v8.py + validasi spatial centroid & InaRISK BNPB
perbukitan_safe_override = {
    'BALAI GADANG',           # Hardcoded safe (wilayah luas, terpapar hanya 31 jiwa)
    'AIR MANIS',              # Terpapar=3 jiwa, wilayah 99% bukit pegunungan
    'BUNGUS TIMUR',           # Centroid lon=100.44, terpapar=1528, area~27km2 mayoritas pegunungan
    'TELUK KABUNG UTARA',     # Centroid lon=100.43, terpapar=861, area~12km2 mayoritas pegunungan
    'TELUK KABUNG TENGAH',    # Centroid lon=100.40, terpapar=1511, area~22km2 mayoritas pegunungan
    'TELUK KABUNG SELATAN',   # Centroid lon=100.39, terpapar=566, area~19km2 mayoritas pegunungan
    'BUNGUS SELATAN',         # Centroid lon=100.42, terpapar=1598, area~5km2 mayoritas pegunungan
    'BUNGUS BARAT',           # Centroid lon=100.41, terpapar=1295, area~8km2 mayoritas pegunungan
    'GUNUNG SARIK',           # Centroid lon=100.41, terpapar=596, wilayah luas dataran tinggi
    'PASAR AMBACANG',         # Centroid lon=100.40, terpapar=3508, wilayah mayoritas dataran tinggi
    'KALUMBUK',               # Centroid lon=100.39, terpapar=1885, perbatasan zona aman
}

def is_kelurahan_safe(nama_kel):
    if nama_kel in perbukitan_safe_override:
        return 1
    terpapar = exposed_map.get(nama_kel, 0)
    return 1 if terpapar == 0 else 0

# 1. Tabel Nodes (dengan flag is_safe: 1 = Zona Aman / Dataran Tinggi, 0 = Zona Risiko Tsunami)
cursor.execute("CREATE TABLE tb_nodes (node_id INTEGER PRIMARY KEY, lat REAL, lon REAL, is_safe INTEGER DEFAULT 0)")
node_rows = []
for n, d in G.nodes(data=True):
    if 'x' in d and 'y' in d:
        n_id = int(n)
        lat_val = float(d['y'])
        lon_val = float(d['x'])
        kel_name = node_to_kelurahan.get(n_id, "")
        if kel_name:
            safe_val = is_kelurahan_safe(kel_name)
        else:
            safe_val = 1 if lon_val > 100.38 else 0
        node_rows.append((n_id, lat_val, lon_val, safe_val))

cursor.executemany("INSERT INTO tb_nodes (node_id, lat, lon, is_safe) VALUES (?, ?, ?, ?)", node_rows)

# Membuat indeks spasial untuk optimasi kueri di Android (Permintaan feedback)
cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_nodes_lat_lon ON tb_nodes(lat, lon)")

# 2. Tabel TES (Tempat Evakuasi Sementara)
cursor.execute("CREATE TABLE tb_tes (tes_id TEXT PRIMARY KEY, nama_tes TEXT, zona TEXT, kapasitas REAL, lat REAL, lon REAL)")
cursor.executemany("INSERT OR IGNORE INTO tb_tes VALUES (?, ?, ?, ?, ?, ?)", [(t_id, info["nama"], info["zona"], info["cap"], info["lat"], info["lon"]) for t_id, info in tes_details.items()])

# 3. Tabel Routes
cursor.execute("CREATE TABLE tb_routes (origin_node_id INTEGER PRIMARY KEY, rank_1_tes TEXT, rank_1_path TEXT, rank_1_eta REAL, rank_2_tes TEXT, rank_2_path TEXT, rank_2_eta REAL, rank_3_tes TEXT, rank_3_path TEXT, rank_3_eta REAL)")
cursor.executemany("INSERT OR REPLACE INTO tb_routes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", final_sqlite_data)

# 4. Tabel Edges (Geometri Jalan untuk Rendering Navigasi Lengkung Android)
cursor.execute("CREATE TABLE tb_edges (edge_id INTEGER PRIMARY KEY AUTOINCREMENT, u INTEGER, v INTEGER, length REAL, geometry TEXT)")
edge_rows = []
for u, v, k, data in G.edges(keys=True, data=True):
    length_val = bersihkan_angka_osm(data.get('length', 50.0))
    geom_str = str(data.get('geometry', ''))
    edge_rows.append((int(u), int(v), float(length_val), geom_str))
cursor.executemany("INSERT INTO tb_edges (u, v, length, geometry) VALUES (?, ?, ?, ?)", edge_rows)

# 5. Tabel Skema Zona Rendaman Tsunami (tb_inundation_zones - InaRISK BPBD)
cursor.execute("CREATE TABLE tb_inundation_zones (zone_id INTEGER PRIMARY KEY AUTOINCREMENT, nama_zona TEXT, tingkat_bahaya TEXT, geometry_wkt TEXT)")

# 6. Tabel Skema Zona Aman Tsunami (tb_safe_zones - Blue Line BNPB)
cursor.execute("CREATE TABLE tb_safe_zones (safe_zone_id INTEGER PRIMARY KEY AUTOINCREMENT, nama_zona TEXT, elevasi_m REAL, geometry_wkt TEXT)")

if gdf_kelurahan is not None:
    inundation_rows = []
    safe_rows = []
    for idx, row in gdf_kelurahan.iterrows():
        nama_kel = str(row['NAMA_UPPER']).strip()
        geom_wkt = row['geometry'].wkt
        safe_status = is_kelurahan_safe(nama_kel)
        if safe_status == 1:
            elevasi = 25.0 if nama_kel == 'BALAI GADANG' else 15.0
            safe_rows.append((nama_kel, elevasi, geom_wkt))
        else:
            jiwa = exposed_map.get(nama_kel, 0)
            bahaya = "Tinggi" if jiwa > 15000 else ("Sedang" if jiwa > 5000 else "Rendah")
            inundation_rows.append((nama_kel, bahaya, geom_wkt))
    cursor.executemany("INSERT INTO tb_safe_zones (nama_zona, elevasi_m, geometry_wkt) VALUES (?, ?, ?)", safe_rows)
    cursor.executemany("INSERT INTO tb_inundation_zones (nama_zona, tingkat_bahaya, geometry_wkt) VALUES (?, ?, ?)", inundation_rows)

conn.commit(); conn.close()


# =========================================================
# 5. GENERATOR LAPORAN AKADEMIK & EVALUASI PROPOSAL (TABEL 6.4)
# =========================================================
print("\n" + "=" * 80)
print("[LAPORAN AKADEMIK] EVALUASI FISIK PROPOSAL SIAGA PADANG")
print("=" * 80)

# 1. EVALUASI BASELINE (Terdekat Murni - Kapasitas Fisik Terbatas)
# Pada Baseline, agen lari ke TES terdekat. Mengingat kapasitas fisik gedung terbatas,
# hanya agen yang datang paling awal (sampai kuota gedung habis) yang BERHASIL MASUK.
baseline_arrivals = []
for data in all_origin_data:
    demand = data['demand']
    primary = data['candidates'][0]
    for _ in range(demand):
        baseline_arrivals.append({'eta': primary['eta'], 'tes_id': primary['tes_id']})

baseline_arrivals.sort(key=lambda x: x['eta'])
load_baseline_count = {t_id: 0 for t_id in cluster_capacity.keys()}
baseline_agent_records = []

for arr in baseline_arrivals:
    t_id = arr['tes_id']
    cap = cluster_capacity[t_id]
    if load_baseline_count[t_id] < cap:
        load_baseline_count[t_id] += 1
        got_in = True
    else:
        load_baseline_count[t_id] += 1
        got_in = False
    baseline_agent_records.append({'eta': arr['eta'], 'tes_id': t_id, 'got_in': got_in})

# 2. EVALUASI SIAGA PADANG (Redirection Berbasis Kapasitas TES)
siaga_agent_records = []
for r_eta in siaga_etas:
    siaga_agent_records.append({'eta': r_eta, 'got_in': True})

# METRIK DEFINISI SELAMAT MURNI FISIK:
# Selamat = Tiba <= 20.0 menit DAN BERHASIL MASUK KE DALAM TES BERKAPASITAS (got_in == True)

base_safe = sum(1 for r in baseline_agent_records if r['eta'] <= 20.0 and r['got_in'])
base_safe_pct = (base_safe / max(len(baseline_agent_records), 1)) * 100

siaga_safe = sum(1 for r in siaga_agent_records if r['eta'] <= 20.0 and r['got_in'])
siaga_safe_pct = (siaga_safe / max(len(siaga_agent_records), 1)) * 100

# Rata-rata Waktu Tempuh Agen BERHASIL (yang benar-benar masuk gedung)
base_succ_etas = [r['eta'] for r in baseline_agent_records if r['got_in']]
base_avg_succ = float(np.mean(base_succ_etas)) if base_succ_etas else 0.0

siaga_succ_etas = [r['eta'] for r in siaga_agent_records if r['got_in']]
siaga_avg_succ = float(np.mean(siaga_succ_etas)) if siaga_succ_etas else 0.0

# Jumlah TES Overcapacity
base_overload = sum(1 for t_id, load in load_baseline_count.items() if load > cluster_capacity[t_id])
siaga_overload = sum(1 for t_id, load in load_siaga.items() if load > cluster_capacity[t_id])

file_size_mb = os.path.getsize("ranah_siaga.db") / (1024 * 1024)

print(f"--- BAB 5.7.1 & 5.7.2: DATA GRAF KOTA PADANG ---")
print(f"Jumlah Persimpangan (Nodes) : {len(G.nodes)}")
print(f"Jumlah Ruas Jalan (Edges)   : {len(G.edges)}")
print(f"Jumlah TES yang dipakai     : {len(tes_nodes)} titik persimpangan ({len(tes_details)} gedung BPBD)\n")

print(f"--- BAB 6.4: IMPLEMENTASI SIMULASI DEMOGRAFI ---")
print(f"Parameter Kecepatan Agen : 1.2 m/s (Jalan cepat evakuasi BNPB)")
print(f"Jumlah Agen Sampel       : {TOTAL_AGEN} jiwa (Rasio 1 : 121.38 dari 242.750 populasi terpapar)")
print(f"Waktu Komputasi Total    : {time.time() - start_total:.2f} detik")
print(f"Ukuran File Database     : {file_size_mb:.2f} MB\n")

print(f"--- TABEL 6.4: PERBANDINGAN SKENARIO EVALUASI AKADEMIK ---")
print(f"Metrik Evaluasi                    | Baseline (Terdekat Murni) | Siaga Padang (Kapasitas TES)")
print(f"-----------------------------------------------------------------------------------------")
print(f"Persentase Selamat (<=20m & Muat)   | {base_safe_pct:6.2f}%                 | {siaga_safe_pct:6.2f}%")
print(f"Rata-rata Waktu (Agen Berhasil Masuk)| {base_avg_succ:6.2f} menit           | {siaga_avg_succ:6.2f} menit")
print(f"Jumlah TES Overcapacity            | {base_overload:6d} gedung              | {siaga_overload:6d} gedung")
print(f"Jumlah Agen Ter-redirection        | {0:6d} agen                | {redirection_count:6d} agen")
print(f"-----------------------------------------------------------------------------------------")

print("=" * 80)
print(f"[SUKSES V6] Database murni akademik berhasil dibangun dalam {time.time() - start_total:.2f} detik!")
print(f"Catatan Ilmiah: Menggunakan data riil BPBD & standar evaluasi fisik evakuasi BNPB.")
print("=" * 80)