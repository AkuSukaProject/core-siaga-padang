import networkx as nx
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import time
import os
import re
from scipy.spatial import cKDTree

# PEMBERIAN SEED UNTUK REPRODUSIBILITAS AKADEMIK
np.random.seed(42)

print("=" * 70)
print("FASE 3: ACAER (Adaptive Capacity-Aware Evacuation Routing Engine) - PROD V2 (FIXED)")
print("=" * 70)

start_total = time.time()

def bersihkan_angka_osm(val, default=3.0):
    if pd.isna(val) or val is None: return default
    if isinstance(val, list): val = str(val[0])
    val = str(val).strip()
    if '-' in val: val = val.split('-')[0]
    match = re.search(r"(\d+(\.\d+)?)", val)
    return float(match.group(1)) if match else default

def edge_key(u, v):
    return tuple(sorted((str(u), str(v))))

# HELPER: Ekstraksi atribut Edge yang aman untuk Graph dan MultiGraph
def safe_get_edge_attr(G, u, v, attr_key, default_val):
    edge_data = G.get_edge_data(u, v)
    if not edge_data: 
        return default_val
    if attr_key in edge_data:
        return float(edge_data.get(attr_key, default_val))
    try:
        first_key = next(iter(edge_data.keys()))
        return float(edge_data[first_key].get(attr_key, default_val))
    except Exception:
        return default_val

# ---------------------------------------------------------
# 1. INISIALISASI SPASIAL & JARINGAN JALAN
# ---------------------------------------------------------
print("[1/5] Membaca graf jaringan & parameter fisik...")
G = nx.read_graphml("padang.graphml").to_undirected()
graph_nodes_set = set(G.nodes)
df_penduduk = pd.read_csv("penduduk_padang_barat.csv")

for u, v, data in G.edges(data=True):
    length = bersihkan_angka_osm(data.get('length', 50.0))
    width = bersihkan_angka_osm(data.get('width', 3.0)) 
    data['capacity'] = max(width * 50.0, 10.0)
    data['t0'] = length / 1.2 / 60.0 
    data['weight_B'] = data['t0']

file_geojson = "batas_kelurahan_padang_barat.geojson"
nodes_per_kelurahan = {}
if os.path.exists(file_geojson):
    gdf_kelurahan = gpd.read_file(file_geojson)
    if gdf_kelurahan.crs != "EPSG:4326": gdf_kelurahan = gdf_kelurahan.to_crs("EPSG:4326")
    
    kolom_nama_wilayah = None
    for col in ['NAMA_KELURAHAN', 'NAMOBJ', 'WADMKD', 'DESA', 'KELURAHAN']:
        if col in gdf_kelurahan.columns:
            kolom_nama_wilayah = col
            break
    if not kolom_nama_wilayah:
        kolom_nama_wilayah = gdf_kelurahan.select_dtypes(include=['object']).columns[0]
        
    nodes_data = [{'node_id': node, 'geometry': Point(data['x'], data['y'])} for node, data in G.nodes(data=True) if 'x' in data and 'y' in data]
    gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
    gdf_joined = gpd.sjoin(gdf_nodes, gdf_kelurahan, how="inner", predicate="within")
    nodes_per_kelurahan = gdf_joined.groupby(kolom_nama_wilayah)['node_id'].apply(list).to_dict()

# ---------------------------------------------------------
# 2. cKDTree SNAPPING & KAPASITAS ZONA
# ---------------------------------------------------------
print("[2/5] Memetakan TES dan Kapasitas Zona Berbasis cKDTree...")
df_shelter = pd.read_csv("Koordinat Evakuasi TES - Sheet1.csv")
def parse_koordinat(val):
    if pd.isna(val): return 0.0
    try: return float(str(val).strip().replace(',', '.'))
    except ValueError: return 0.0

df_shelter['Clean_Lat'] = df_shelter['Latitude'].apply(parse_koordinat)
df_shelter['Clean_Lon'] = df_shelter['Longitude'].apply(parse_koordinat)
df_shelter = df_shelter[(df_shelter['Clean_Lat'] != 0.0) & (df_shelter['Clean_Lon'] != 0.0)]
df_shelter['Kapasitas_Zona'] = df_shelter['Kapasitas_TES'].fillna(df_shelter['Jumlah_Jiwa']).bfill().fillna(300)

node_ids_list, coords_list = [], []
for node, data in G.nodes(data=True):
    if 'x' in data and 'y' in data:
        node_ids_list.append(node)
        coords_list.append([float(data['y']), float(data['x'])])

tree = cKDTree(coords_list)
tes_nodes, node_to_cluster, cluster_capacity = [], {}, {}

for idx, row in df_shelter.iterrows():
    lat, lon = row['Clean_Lat'], row['Clean_Lon']
    dist, idx_nearest = tree.query([lat, lon])
    matched_node = node_ids_list[idx_nearest]
    
    if matched_node and matched_node in G.nodes:
        tes_nodes.append(matched_node)
        nama_zona = str(row['Zona'])
        if matched_node not in node_to_cluster: node_to_cluster[matched_node] = set()
        node_to_cluster[matched_node].add(nama_zona)
        if nama_zona not in cluster_capacity: cluster_capacity[nama_zona] = float(row['Kapasitas_Zona'])

tes_nodes = list(set(tes_nodes))

# ---------------------------------------------------------
# 3. DISTRIBUSI AGEN & PREPROCESSING
# ---------------------------------------------------------
print("[3/5] Membangkitkan Permintaan Agen & Preprocessing Ranking TES...")
TOTAL_AGEN = 5000
total_pop = df_penduduk['JUMLAH JIWA TERPAPAR (JIWA)'].sum()

scaling_factor = TOTAL_AGEN / total_pop
cluster_capacity = {z: max(int(cap * scaling_factor), 1) for z, cap in cluster_capacity.items()}

agent_origins = []
for idx, row in df_penduduk.iterrows():
    porsi = row['JUMLAH JIWA TERPAPAR (JIWA)'] / total_pop
    jumlah_agen = int(round(porsi * TOTAL_AGEN))
    avail = nodes_per_kelurahan.get(row['DESA'], list(graph_nodes_set))
    agent_origins.extend(np.random.choice(avail, size=jumlah_agen, replace=True))

all_edges_normalized = set(edge_key(u, v) for u, v in G.edges())

# =========================================================
# 4. BASELINE ENGINE (Dijkstra Terdekat + BPR Iteratif)
# =========================================================
print("\n[4.1/5] Menjalankan Baseline Engine (Nearest + BPR)...")
for u, v, data in G.edges(data=True):
    data['weight_B'] = data['t0']

volume_baseline = {ekey: 0 for ekey in all_edges_normalized}
baseline_paths = {}

for k in range(1, 6): 
    vol_b_iter = {ekey: 0 for ekey in all_edges_normalized}
    temp_b_paths = {}
    
    for idx, origin in enumerate(agent_origins):
        try:
            lengths_o, paths_o = nx.single_source_dijkstra(G, source=origin, weight='weight_B')
            nearest_t = min([t for t in tes_nodes if t in lengths_o], key=lambda t: lengths_o[t])
            path_chosen = paths_o[nearest_t]
            temp_b_paths[idx] = path_chosen
            for u, v in zip(path_chosen[:-1], path_chosen[1:]):
                vol_b_iter[edge_key(u, v)] += 1
        except:
            continue
            
    if k == 5: baseline_paths = temp_b_paths
    
    for u, v, data in G.edges(data=True):
        ekey = edge_key(u, v)
        V = vol_b_iter.get(ekey, 0)
        C = max(data.get('capacity', 50), 1)
        t0 = data['t0']
        w_new = t0 * (1 + 0.15 * ((V / C) ** 4))
        data['weight_B'] = data['weight_B'] + (1/k) * (w_new - data['weight_B'])
    volume_baseline = vol_b_iter.copy()

# Evaluasi beban & waktu baseline final
beban_baseline_raw = {cluster: 0 for cluster in cluster_capacity.keys()}
for idx, path in baseline_paths.items():
    if path:
        dest_node = path[-1]
        for z in node_to_cluster.get(dest_node, []):
            beban_baseline_raw[z] += 1

waktu_baseline_list = []
for idx, path in baseline_paths.items():
    if path and len(path) > 1:
        path_cost = sum(safe_get_edge_attr(G, u, v, 'weight_B', 1.0) for u, v in zip(path[:-1], path[1:]))
        waktu_baseline_list.append(path_cost)

rata_baseline = np.mean(waktu_baseline_list) if waktu_baseline_list else 0
selamat_baseline = np.mean(np.array(waktu_baseline_list) <= 20) * 100 if waktu_baseline_list else 0
zona_over_baseline = sum(1 for z, beban in beban_baseline_raw.items() if beban > cluster_capacity.get(z, 0))

# Perbaikan aman komputasi jalan overload baseline
jalan_over_baseline = 0
for ekey, v_vol in volume_baseline.items():
    u, v_node = ekey
    cap = safe_get_edge_attr(G, u, v_node, 'capacity', 50.0)
    if v_vol > max(cap, 1):
        jalan_over_baseline += 1

# =========================================================
# [4.2/5] ACAER CORE ENGINE (Capacity-Aware + BPR Iteratif)
# =========================================================
print("[4.2/5] Menjalankan ACAER 2-Stage Engine...")
for u, v, data in G.edges(data=True):
    data['weight_B'] = data['t0']

volume_old = {ekey: 0 for ekey in all_edges_normalized}
MAX_ITER = 10
W_ETA, W_CAP, W_DET, W_SAFE = 0.35, 0.25, 0.15, 0.25
TSUNAMI_WARNING_TIME = 25.0 

final_agent_paths = {}
redirection_count = 0

for k in range(1, MAX_ITER + 1):
    volume_new = {ekey: 0 for ekey in all_edges_normalized}
    beban_cluster_iter = {cluster: 0 for cluster in cluster_capacity.keys()}
    temp_paths = {}
    local_redirection = 0
    
    for idx, origin in enumerate(agent_origins):
        try:
            lengths_o, paths_o = nx.single_source_dijkstra(G, source=origin, weight='weight_B')
        except (nx.NodeNotFound, KeyError):
            continue
            
        raw_candidates = []
        for t_node in tes_nodes:
            if t_node not in lengths_o: continue
            eta = lengths_o[t_node]
            path_route = paths_o[t_node]
            zones = node_to_cluster.get(t_node, [])
            z_name = list(zones)[0] if zones else "Unknown"
            raw_candidates.append({'tes_node': t_node, 'zone': z_name, 'eta': eta, 'path': path_route})
            
        if not raw_candidates: continue
        raw_candidates.sort(key=lambda x: x['eta'])
        
        assigned_path = None
        primary_candidate = raw_candidates[0]
        z_primary = primary_candidate['zone']
        
        if beban_cluster_iter.get(z_primary, 0) < cluster_capacity.get(z_primary, float('inf')):
            beban_cluster_iter[z_primary] += 1
            assigned_path = primary_candidate['path']
        else:
            local_redirection += 1
            fallback_candidates = raw_candidates[1:] 
            if fallback_candidates:
                etas = [c['eta'] for c in fallback_candidates]
                min_eta, max_eta = min(etas), max(etas)
                eta_range = (max_eta - min_eta) if max_eta != min_eta else 1.0
                total_cands = len(fallback_candidates)
                
                scored_candidates = []
                for rank_idx, cand in enumerate(fallback_candidates):
                    eta_norm = (cand['eta'] - min_eta) / eta_range
                    detour_delta = cand['eta'] - primary_candidate['eta']
                    detour_norm = min(max(detour_delta / 20.0, 0.0), 1.0) 
                    
                    current_load = beban_cluster_iter.get(cand['zone'], 0)
                    max_cap = cluster_capacity.get(cand['zone'], 300)
                    cap_norm = min((current_load + 1) / max_cap if max_cap > 0 else 1.0, 1.0)
                    
                    safety_score = max(0.0, (TSUNAMI_WARNING_TIME - cand['eta']) / TSUNAMI_WARNING_TIME)
                    safety_risk_norm = 1.0 - min(safety_score, 1.0) 
                    
                    utility_score = (W_ETA * eta_norm) + (W_CAP * cap_norm) + (W_DET * detour_norm) + (W_SAFE * safety_risk_norm)
                    cand['score'] = utility_score
                    scored_candidates.append(cand)
                    
                scored_candidates.sort(key=lambda x: x['score'])
                for cand in scored_candidates:
                    z = cand['zone']
                    if beban_cluster_iter.get(z, 0) < cluster_capacity.get(z, float('inf')):
                        beban_cluster_iter[z] += 1
                        assigned_path = cand['path']
                        break
                        
        if not assigned_path:
            fallback = raw_candidates[0]
            beban_cluster_iter[fallback['zone']] = beban_cluster_iter.get(fallback['zone'], 0) + 1
            assigned_path = fallback['path']
            
        temp_paths[idx] = assigned_path
        if assigned_path:
            for u, v in zip(assigned_path[:-1], assigned_path[1:]):
                volume_new[edge_key(u, v)] += 1

    if k == MAX_ITER:
        final_agent_paths = temp_paths
        redirection_count = local_redirection
        final_beban_acaer = beban_cluster_iter

    max_diff = max((abs(volume_new.get(e, 0) - volume_old.get(e, 0)) for e in all_edges_normalized), default=0)
    sum_old = sum(volume_old.values())
    flow_change = max_diff / max(sum_old, 1.0)
    print(f"      -> Iterasi {k:02d} | Max Link Flow Change: {flow_change:.4f} | Redirection: {local_redirection}")

    for u, v, data in G.edges(data=True):
        ekey = edge_key(u, v)
        V = volume_new.get(ekey, 0)
        C = max(data.get('capacity', 50), 1)
        t0 = data['t0']
        w_new = t0 * (1 + 0.15 * ((V / C) ** 4))
        data['weight_B'] = data['weight_B'] + (1/k) * (w_new - data['weight_B'])
        
    volume_old = volume_new.copy()

# Perbaikan ETA final ACAER
waktu_acaer_list = []
for idx, path in final_agent_paths.items():
    if path and len(path) > 1:
        cost = sum(safe_get_edge_attr(G, u, v, 'weight_B', 1.0) for u, v in zip(path[:-1], path[1:]))
        waktu_acaer_list.append(cost)

rata_acaer = np.mean(waktu_acaer_list) if waktu_acaer_list else 0
selamat_acaer = np.mean(np.array(waktu_acaer_list) <= 20) * 100 if waktu_acaer_list else 0
jalan_over_acaer = sum(1 for u, v, data in G.edges(data=True) if volume_old.get(edge_key(u, v), 0) > data.get('capacity', 50))
zona_over_acaer = sum(1 for z, beban in final_beban_acaer.items() if beban > cluster_capacity.get(z, 0))

# ---------------------------------------------------------
# 5. LAPORAN KOMPARATIF ILMIAH
# ---------------------------------------------------------
print("\n" + "=" * 80)
print("📊 TABEL KINERJA ILMIAH: ACAER VS. BASELINE (FAIR BPR EVALUATION)")
print("=" * 80)
print(f"{'Metrik Evaluasi Performa':<32} | {'Baseline (Nearest + BPR)':<25} | {'ACAER Engine (Usulan)':<22}")
print("-" * 80)
print(f"{'Rata-rata Waktu Tempuh':<32} | {rata_baseline:.2f} menit                | {rata_acaer:.2f} menit")
print(f"{'Tingkat Keselamatan (<20 min)':<32} | {selamat_baseline:.2f}%                    | {selamat_acaer:.2f}%")
print(f"{'Ruas Jalan Overload (Macet)':<32} | {jalan_over_baseline} ruas                   | {jalan_over_acaer} ruas")
print(f"{'Zona/Shelter Overload':<32} | {zona_over_baseline} zona                   | {zona_over_acaer} zona")
print(f"{'Agen Mengalami Redirection':<32} | 0 agen                    | {redirection_count} agen")
print("=" * 80)

print(f"\nTotal Waktu Eksekusi: {time.time() - start_total:.2f} detik")