import networkx as nx
import pandas as pd
import numpy as np
import os

# Read core logic simulation data
# Let's run the exact simulation logic from core.py to test the new metrics

# Load inputs
G = nx.read_graphml("padang_full.graphml").to_undirected()

# Road travel time
for u, v, data in G.edges(data=True):
    length = float(data.get('length', 50.0)) if not isinstance(data.get('length'), list) else float(data.get('length')[0])
    data['t0'] = length / 1.2 / 60.0

# Load shelter dataset
df_shelter = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
if 'Sektor' in df_shelter.columns:
    df_shelter = df_shelter[df_shelter['Sektor'].astype(str).str.upper() != 'JUMLAH']

def parse_koordinat(val):
    if pd.isna(val): return 0.0
    try: return float(str(val).strip().replace(',', '.'))
    except ValueError: return 0.0

def parse_kapasitas(val, default=300.0):
    if pd.isna(val) or val is None: return default
    val_str = str(val).strip().replace('.', '').replace(',', '.')
    try: return float(val_str)
    except ValueError: return default

df_shelter['Clean_Lat'] = df_shelter['Latitude'].apply(parse_koordinat)
df_shelter['Clean_Lon'] = df_shelter['Longitude'].apply(parse_koordinat)
df_shelter = df_shelter[(df_shelter['Clean_Lat'] != 0.0) & (df_shelter['Clean_Lon'] != 0.0)]
df_shelter = df_shelter.drop_duplicates(subset=['Clean_Lat', 'Clean_Lon'])

from scipy.spatial import cKDTree
coords_list, node_ids_list = [], []
for node, data in G.nodes(data=True):
    if 'x' in data and 'y' in data:
        node_ids_list.append(node)
        coords_list.append([float(data['y']), float(data['x'])])

tree = cKDTree(coords_list)
tes_nodes, tes_details, cluster_capacity, node_to_tes_id = [], {}, {}, {}

for idx, row in df_shelter.iterrows():
    lat, lon = row['Clean_Lat'], row['Clean_Lon']
    nama_tes = str(row['Nama_Bersih']).strip()
    zona = str(row['Zona']).strip()
    cap = parse_kapasitas(row['Kapasitas_TES'], default=300.0)
    dist, idx_nearest = tree.query([lat, lon])
    matched_node = node_ids_list[idx_nearest]
    access_time_mnt = (dist * 111000.0) / 72.0
    
    if matched_node and matched_node in G.nodes:
        tes_id = f"TES_{idx}"
        tes_nodes.append(matched_node)
        if matched_node not in node_to_tes_id: node_to_tes_id[matched_node] = []
        node_to_tes_id[matched_node].append(tes_id)
        tes_details[tes_id] = {"nama": nama_tes, "zona": zona, "lat": lat, "lon": lon, "cap": cap, "access_time": access_time_mnt}
        cluster_capacity[tes_id] = cap

tes_nodes = list(set(tes_nodes))

# Population demand
df_penduduk = pd.read_csv("penduduk_kota_padang.csv")
TOTAL_AGEN = 2000
total_pop = df_penduduk['JUMLAH JIWA TERPAPAR (JIWA)'].sum()
scaling_factor = TOTAL_AGEN / total_pop if total_pop > 0 else 1.0
cluster_capacity = {t_id: max(int(cap * scaling_factor), 1) for t_id, cap in cluster_capacity.items()}

# Kelurahan GeoJSON matching
import geopandas as gpd
from shapely.geometry import Point
gdf_kelurahan = gpd.read_file("batas_kelurahan_kota_padang.geojson")
if gdf_kelurahan.crs != "EPSG:4326": gdf_kelurahan = gdf_kelurahan.to_crs("EPSG:4326")
kolom_nama = gdf_kelurahan.select_dtypes(include=['object', 'string']).columns[0]
nodes_data = [{'node_id': n, 'geometry': Point(d['x'], d['y'])} for n, d in G.nodes(data=True) if 'x' in d and 'y' in d]
gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
gdf_joined = gpd.sjoin(gdf_nodes, gdf_kelurahan, how="inner", predicate="within")
gdf_joined['nama_kel_upper'] = gdf_joined[kolom_nama].astype(str).str.upper().str.strip()
nodes_per_kelurahan = gdf_joined.groupby('nama_kel_upper')['node_id'].apply(list).to_dict()

kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
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

# Dijkstra
tes_dijkstra = {}
for t_node in tes_nodes:
    lengths, paths = nx.single_source_dijkstra(G, source=t_node, weight='t0')
    tes_dijkstra[t_node] = (lengths, paths)

all_origin_data = []
for node in G.nodes:
    demand = node_demands.get(node, 0)
    candidates = []
    for t_node in tes_nodes:
        lengths, paths = tes_dijkstra[t_node]
        if node in lengths:
            for tes_id in node_to_tes_id[t_node]:
                total_eta = lengths[node] + tes_details[tes_id]["access_time"]
                candidates.append({'tes_id': tes_id, 'nama_gedung': tes_details[tes_id]['nama'], 'eta': total_eta})
    if candidates:
        candidates.sort(key=lambda x: x['eta'])
        if demand > 0: all_origin_data.append({'node': node, 'demand': demand, 'candidates': candidates})

# -------------------------------------------------------------
# CALCULATE BASELINE VS SIAGA PADANG WITH REAL PHYSICAL DEFINITION
# -------------------------------------------------------------

# 1. BASELINE (TERDEKAT MURNI)
# In baseline, everyone rushes to candidates[0]['tes_id'] (nearest TES).
# Since building capacity is LIMITED in physical reality,
# only the first cap_limit agents arriving at that building get in!
baseline_agent_records = [] # list of dict: {'eta': float, 'tes_id': str, 'got_in': bool}
load_baseline_count = {t_id: 0 for t_id in cluster_capacity.keys()}

# Sort all agent arrivals by ETA so earlier arrivals fill the building first
baseline_arrivals = []
for data in all_origin_data:
    demand = data['demand']
    primary = data['candidates'][0]
    for _ in range(demand):
        baseline_arrivals.append({'eta': primary['eta'], 'tes_id': primary['tes_id']})

baseline_arrivals.sort(key=lambda x: x['eta'])
for arr in baseline_arrivals:
    t_id = arr['tes_id']
    cap = cluster_capacity[t_id]
    if load_baseline_count[t_id] < cap:
        load_baseline_count[t_id] += 1
        got_in = True
    else:
        load_baseline_count[t_id] += 1 # keep track of total overflow
        got_in = False
    baseline_agent_records.append({'eta': arr['eta'], 'tes_id': t_id, 'got_in': got_in})


# 2. SIAGA PADANG (CAPACITY-AWARE REDIRECTION)
all_origin_data.sort(key=lambda x: x['candidates'][0]['eta'])
load_siaga_count = {t_id: 0 for t_id in cluster_capacity.keys()}
siaga_agent_records = []
redirection_count = 0

for data in all_origin_data:
    demand = data['demand']
    primary_cand = data['candidates'][0]
    rem = demand
    for cand in data['candidates']:
        t_id = cand['tes_id']
        free = cluster_capacity[t_id] - load_siaga_count[t_id]
        if free > 0:
            assign = min(free, rem)
            load_siaga_count[t_id] += assign
            rem -= assign
            if cand['tes_id'] != primary_cand['tes_id']: redirection_count += assign
            for _ in range(assign):
                siaga_agent_records.append({'eta': cand['eta'], 'tes_id': t_id, 'got_in': True})
            if rem <= 0: break
    if rem > 0:
        # If total city capacity were somehow exceeded (not the case here)
        for _ in range(rem):
            siaga_agent_records.append({'eta': primary_cand['eta'], 'tes_id': primary_cand['tes_id'], 'got_in': False})

# METRICS COMPUTATION:
# Definition of SELAMAT: Arrive <= 20.0 minutes AND got_in == True (building had capacity)

base_safe = sum(1 for r in baseline_agent_records if r['eta'] <= 20.0 and r['got_in'])
base_safe_pct = (base_safe / len(baseline_agent_records)) * 100

siaga_safe = sum(1 for r in siaga_agent_records if r['eta'] <= 20.0 and r['got_in'])
siaga_safe_pct = (siaga_safe / len(siaga_agent_records)) * 100

# Average Travel Time for SUCCESSFUL agents (who got inside building)
base_succ_etas = [r['eta'] for r in baseline_agent_records if r['got_in']]
base_avg_succ = np.mean(base_succ_etas) if base_succ_etas else 0.0

siaga_succ_etas = [r['eta'] for r in siaga_agent_records if r['got_in']]
siaga_avg_succ = np.mean(siaga_succ_etas) if siaga_succ_etas else 0.0

# Overall Avg Time (all agents)
base_avg_all = np.mean([r['eta'] for r in baseline_agent_records])
siaga_avg_all = np.mean([r['eta'] for r in siaga_agent_records])

# Overcapacity TES count
base_overload = sum(1 for t_id, load in load_baseline_count.items() if load > cluster_capacity[t_id])
siaga_overload = sum(1 for t_id, load in load_siaga_count.items() if load > cluster_capacity[t_id])

print("="*70)
print("HASIL BARU TABEL 6.4 DENGAN DEFINISI SELAMAT YANG BENAR (KAPASITAS MURNI)")
print("="*70)
print(f"Metrik                             | Baseline (Terdekat) | Siaga Padang (Kapasitas)")
print(f"----------------------------------------------------------------------------------")
print(f"Persentase Selamat (<=20 mnt & Muat)| {base_safe_pct:6.2f}%              | {siaga_safe_pct:6.2f}%")
print(f"Rata-rata Waktu (Agen Berhasil)     | {base_avg_succ:6.2f} menit        | {siaga_avg_succ:6.2f} menit")
print(f"Rata-rata Waktu (Seluruh Agen)      | {base_avg_all:6.2f} menit        | {siaga_avg_all:6.2f} menit")
print(f"Jumlah TES Overcapacity             | {base_overload:6d} gedung           | {siaga_overload:6d} gedung")
print(f"Jumlah Agen Ter-redirection         | {0:6d} agen             | {redirection_count:6d} agen")
print(f"----------------------------------------------------------------------------------")
