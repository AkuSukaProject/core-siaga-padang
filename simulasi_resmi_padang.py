import sys
sys.stdout.reconfigure(encoding='utf-8')

import networkx as nx
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import time
import os
import re
import json
from scipy.spatial import cKDTree
from pyproj import Transformer

print("=" * 85)
print("METODOLOGI UJI KONSISTENSI & ENGINE SIMULASI RESMI EVAKUASI HIBRIDA (TES+TEA) KOTA PADANG")
print("=" * 85)

start_total = time.time()

# ---------------------------------------------------------
# 1. KONFIGURASI RESMI & DOKUMENTASI LENGKAP
# ---------------------------------------------------------
RANDOM_SEED = 42
# Data lama (belum diselaraskan dengan data BPBD v4, lihat docs/simulasi_kanonis.md)
DIR_DATA_LAMA = os.path.join("legacy", "data")
TOTAL_AGEN = 20000
TSUNAMI_DEADLINE_MIN = 20.0
TES_TOLERANCE_FACTOR = 1.1  # 10% tolerance for overcapacity

np.random.seed(RANDOM_SEED)

print(f"[1/5] Memuat Jaringan Jalan Seluruh Kota Padang (padang_full.graphml)...")
G = nx.read_graphml("padang_full.graphml").to_undirected()

# Standarisasi Koordinat ke EPSG:4326 (WGS84)
sample_node = next(iter(G.nodes(data=True)))[1]
if 'x' in sample_node and abs(float(sample_node['x'])) > 180:
    transformer = Transformer.from_crs("EPSG:32747", "EPSG:4326", always_xy=True)
    for node, data in G.nodes(data=True):
        if 'x' in data and 'y' in data:
            nx_val, ny_val = transformer.transform(float(data['x']), float(data['y']))
            data['x'], data['y'] = float(nx_val), float(ny_val)
else:
    for node, data in G.nodes(data=True):
        if 'x' in data and 'y' in data:
            data['x'], data['y'] = float(data['x']), float(data['y'])

def bersihkan_angka(val, default=50.0):
    if pd.isna(val) or val is None: return default
    if isinstance(val, list): val = str(val[0])
    val = str(val).strip()
    if '-' in val: val = val.split('-')[0]
    match = re.search(r"(\d+(\.\d+)?)", val)
    return float(match.group(1)) if match else default

for u, v, data in G.edges(data=True):
    length = bersihkan_angka(data.get('length', 50.0))
    # Kecepatan evakuasi berjalan kaki standar BNPB = 1.2 m/s (72 m/menit)
    data['t0'] = length / 1.2 / 60.0 

# ---------------------------------------------------------
# 2. PEMETAAN 143 TES RESMI BPBD & 12 TEA
# ---------------------------------------------------------
print("[2/5] Memuat Data Resmi 143 Gedung TES & 12 TEA Kota Padang...")

# Load TES
df_tes = pd.read_csv(os.path.join(DIR_DATA_LAMA, "data_tes_padang_lengkap_berkoordinat.csv"))
if 'Sektor' in df_tes.columns:
    df_tes = df_tes[df_tes['Sektor'].astype(str).str.upper() != 'JUMLAH']
df_tes['Tipe_Fasilitas'] = 'TES'
df_tes['Nama_Fasilitas'] = df_tes.apply(lambda r: str(r['Nama_Bersih']) if not pd.isna(r['Nama_Bersih']) else str(r['Lokasi_TES']), axis=1)

# Load TEA
df_tea = pd.read_csv(os.path.join(DIR_DATA_LAMA, "data_tea_padang_lengkap_berkoordinat.csv"))
df_tea['Tipe_Fasilitas'] = 'TEA'
df_tea['Nama_Fasilitas'] = df_tea['nama'].astype(str).apply(lambda x: x.replace("(Rekomendasi)", "").strip())
df_tea['Latitude'] = df_tea['lat']
df_tea['Longitude'] = df_tea['lon']
df_tea['Kapasitas_TES'] = df_tea['kapasitas']

# Gabungkan TES dan TEA
cols = ['Nama_Fasilitas', 'Tipe_Fasilitas', 'Kapasitas_TES', 'Latitude', 'Longitude']
df_shelter = pd.concat([df_tes[cols], df_tea[cols]], ignore_index=True)

def parse_coord(val):
    try: return float(str(val).strip().replace(',', '.'))
    except: return np.nan

def parse_cap(val):
    try:
        v = float(str(val).replace(',', '.'))
        return v if v > 0 else 300.0
    except: return 300.0

df_shelter['Clean_Lat'] = df_shelter['Latitude'].apply(parse_coord)
df_shelter['Clean_Lon'] = df_shelter['Longitude'].apply(parse_coord)
df_shelter = df_shelter.dropna(subset=['Clean_Lat', 'Clean_Lon']).drop_duplicates(subset=['Clean_Lat', 'Clean_Lon']).reset_index(drop=True)
df_shelter['Cap_Raw'] = df_shelter['Kapasitas_TES'].apply(parse_cap)

# Build cKDTree untuk snapping lokasi TES/TEA ke node jaringan terdekat
node_ids, coords = [], []
for n, d in G.nodes(data=True):
    if 'x' in d and 'y' in d:
        node_ids.append(n)
        coords.append([d['y'], d['x']])

tree_nodes = cKDTree(coords)

tes_details = {}
node_to_tes_idx = {}
tes_nodes_list = []

for idx, r in df_shelter.iterrows():
    d, i = tree_nodes.query([r['Clean_Lat'], r['Clean_Lon']])
    matched_node = node_ids[i]
    tes_nodes_list.append(matched_node)
    
    if matched_node not in node_to_tes_idx: node_to_tes_idx[matched_node] = []
    node_to_tes_idx[matched_node].append(idx)
    
    tes_details[idx] = {
        'nama': r['Nama_Fasilitas'],
        'tipe': r['Tipe_Fasilitas'],
        'lat': r['Clean_Lat'],
        'lon': r['Clean_Lon'],
        'cap_raw': r['Cap_Raw'],
        'node': matched_node
    }

tes_nodes_unique = list(set(tes_nodes_list))
total_tes = len(df_tes)
total_tea = len(df_tea)
print(f"      Total Fasilitas: {len(df_shelter)} Titik ({total_tes} TES & {total_tea} TEA)")

# ---------------------------------------------------------
# 3. DISTRIBUSI AGEN DEPT DEMOGRAFI & RESCALING KAPASITAS
# ---------------------------------------------------------
print("[3/5] Pembangkitan Agen Berbasis Data Demografi BPS/BPBD...")
df_pend = pd.read_csv(os.path.join(DIR_DATA_LAMA, "penduduk_kota_padang.csv"))
total_pop = df_pend['JUMLAH JIWA TERPAPAR (JIWA)'].sum()

# Skala kapasitas TES disesuaikan secara proporsional terhadap rasio sampel agen (20.000 / 524.728)
# Untuk TEA, kapasitas ditetapkan tak terbatas (999999999) sesuai desain Hibrida V2
scaling_factor = TOTAL_AGEN / total_pop
def get_scaled_cap(row):
    if row['Tipe_Fasilitas'] == 'TEA':
        return 999999999
    return max(int(round(row['Cap_Raw'] * scaling_factor)), 1)
df_shelter['Scaled_Cap'] = df_shelter.apply(get_scaled_cap, axis=1)

# Snap node per kelurahan
file_geojson = os.path.join(DIR_DATA_LAMA, "batas_kelurahan_kota_padang.geojson")
nodes_per_kel = {}
if os.path.exists(file_geojson):
    gdf_kel = gpd.read_file(file_geojson)
    if gdf_kel.crs != "EPSG:4326": gdf_kel = gdf_kel.to_crs("EPSG:4326")
    kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
    gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()
    
    nodes_gdf_list = [{'node_id': n, 'geometry': Point(d['x'], d['y'])} for n, d in G.nodes(data=True) if 'x' in d and 'y' in d]
    gdf_nodes = gpd.GeoDataFrame(nodes_gdf_list, crs="EPSG:4326")
    gdf_joined = gpd.sjoin(gdf_nodes, gdf_kel, how="inner", predicate="within")
    nodes_per_kel = gdf_joined.groupby('NAMA_UPPER')['node_id'].apply(list).to_dict()

kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

agent_origins = []
for idx, r in df_pend.iterrows():
    k_name = str(r['DESA']).strip().upper()
    k_name = kelurahan_alias.get(k_name, k_name)
    n_agen = int(round((r['JUMLAH JIWA TERPAPAR (JIWA)'] / total_pop) * TOTAL_AGEN))
    avail = nodes_per_kel.get(k_name, node_ids)
    if avail:
        agent_origins.extend(np.random.choice(avail, size=n_agen, replace=True))

print(f"      Total Agen Terbangkitkan: {len(agent_origins):,} Agen")

# Pre-calculate Reverse Dijkstra Shortest Path dari seluruh Node TES & TEA
print("[4/5] Menghitung Rute Terpendek Jaringan Jalan (Reverse Dijkstra)...")
tes_dijkstra = {}
for t_node in tes_nodes_unique:
    lengths, paths = nx.single_source_dijkstra(G, source=t_node, weight='t0')
    tes_dijkstra[t_node] = (lengths, paths)

# Dynamic Agent Candidates Retrieval
agent_candidates = []
for agent_id, origin_node in enumerate(agent_origins):
    cands = []
    for idx_shelter, row_s in df_shelter.iterrows():
        t_node = tes_details[idx_shelter]['node']
        lengths, paths = tes_dijkstra[t_node]
        if origin_node in lengths:
            eta = lengths[origin_node]
            cands.append({
                'tes_idx': idx_shelter,
                'eta': eta,
                'path': paths[origin_node][::-1]
            })
    if cands:
        cands.sort(key=lambda x: x['eta'])
        agent_candidates.append({
            'agent_id': agent_id,
            'origin': origin_node,
            'cands': cands
        })

print(f"      Evaluasi kandidat rute selesai untuk {len(agent_candidates):,} agen.")

# ---------------------------------------------------------
# SIMULASI A: BASELINE (Semua ke TES/TEA Terdekat - Tanpa Batas Kapasitas)
# ---------------------------------------------------------
print("\n[EKSEKUSI A] Simulasi Baseline (Nearest Shelter Unconstrained)...")
baseline_b_load = {idx: 0 for idx in df_shelter.index}
baseline_etas = []

for item in agent_candidates:
    primary = item['cands'][0]
    tes_idx = primary['tes_idx']
    baseline_b_load[tes_idx] += 1
    baseline_etas.append(primary['eta'])

df_shelter['Baseline_Load'] = df_shelter.index.map(baseline_b_load)

# Murni Evaluasi Tanpa Pemaksaan Kode (Beban > Kapasitas)
# TEA kapasitasnya 999M, jadi tidak pernah Baseline_Over = True
df_shelter['Baseline_Over'] = df_shelter['Baseline_Load'] > df_shelter['Scaled_Cap']

b_over_count = int(df_shelter['Baseline_Over'].sum())
b_assigned = len(baseline_etas)
b_unassigned = len(agent_origins) - b_assigned
b_safe = sum(1 for eta in baseline_etas if eta <= TSUNAMI_DEADLINE_MIN)
b_unsafe = b_assigned - b_safe
b_mean_eta = np.mean(baseline_etas) if baseline_etas else 0
b_detour = 0.0

# ---------------------------------------------------------
# SIMULASI B: SIAGA PADANG (Capacity-Aware Assignment Hibrida V2)
# ---------------------------------------------------------
print("[EKSEKUSI B] Simulasi Siaga Padang Hibrida V2 (Capacity-Aware TES + Bebas TEA)...")

# Urutkan agen berdasarkan waktu tempuh tercepat agar alokasi efisien
sorted_agent_candidates = sorted(agent_candidates, key=lambda x: x['cands'][0]['eta'])

siaga_b_load = {idx: 0 for idx in df_shelter.index}
siaga_etas = []
siaga_detours = []
siaga_assigned_count = 0
siaga_unassigned_count = 0

for item in sorted_agent_candidates:
    assigned = False
    primary_eta = item['cands'][0]['eta']
    
    for cand in item['cands']:
        idx_tes = cand['tes_idx']
        cap = df_shelter.loc[idx_tes, 'Scaled_Cap']
        
        # Alokasi jika kapasitas belum penuh (dengan batas toleransi pembulatan ke bawah agar aman)
        max_allowed = int(cap * TES_TOLERANCE_FACTOR) if cap < 999999999 else cap
        if siaga_b_load[idx_tes] < max_allowed:
            siaga_b_load[idx_tes] += 1
            siaga_etas.append(cand['eta'])
            siaga_detours.append(cand['eta'] - primary_eta)
            siaga_assigned_count += 1
            assigned = True
            break
            
    if not assigned:
        siaga_unassigned_count += 1

df_shelter['Siaga_Load'] = df_shelter.index.map(siaga_b_load)

# Murni Evaluasi Tanpa Pemaksaan Kode (Beban > Kapasitas)
df_shelter['Siaga_Over'] = df_shelter['Siaga_Load'] > df_shelter['Scaled_Cap']

s_over_count = int(df_shelter['Siaga_Over'].sum())
s_safe = sum(1 for eta in siaga_etas if eta <= TSUNAMI_DEADLINE_MIN)
s_unsafe = siaga_assigned_count - s_safe
s_mean_eta = np.mean(siaga_etas) if siaga_etas else 0
s_mean_detour = np.mean(siaga_detours) if siaga_detours else 0

# ---------------------------------------------------------
# 5. LAPORAN HASIL SIMULASI AKADEMIK RESMI
# ---------------------------------------------------------
print("\n" + "=" * 90)
print("[METRIK] HASIL SIMULASI EVAKUASI RESMI KOTA PADANG HIBRIDA V2 (TES + TEA)")
print("=" * 90)
print(f"Konfigurasi Parameter Fixed:")
print(f"  - Random Seed        : {RANDOM_SEED}")
print(f"  - Jumlah Agen        : {TOTAL_AGEN:,} Agen (Representasi {total_pop:,} Jiwa)")
print(f"  - Sumber Data        : {total_tes} Gedung TES & {total_tea} TEA")
print(f"  - Metode Jarak       : Jaringan Jalan Pedestrian Graf (Dijkstra Shortest Path)")
print(f"  - Kriteria Overload  : Murni (Beban TES > Kapasitas TES, TEA = Infinite)")
print("-" * 90)
print(f"{'Metrik Evaluasi Evakuasi':<42} | {'Baseline (Nearest)':<20} | {'Siaga Padang (Hibrida V2)':<25}")
print("-" * 90)
print(f"{'Jumlah TES Melebihi Kapasitas':<42} | {b_over_count} Gedung ({(b_over_count/total_tes)*100:.1f}%)   | {s_over_count} Gedung ({(s_over_count/total_tes)*100:.1f}%)")
print(f"{'Agen Memperoleh Tempat (Assigned)':<42} | {b_assigned:,} Agen ({b_assigned/TOTAL_AGEN*100:.1f}%)   | {siaga_assigned_count:,} Agen ({siaga_assigned_count/TOTAL_AGEN*100:.1f}%)")
print(f"{'Agen Tidak Memperoleh Tempat (Overflow)':<42} | {b_unassigned:,} Agen ({b_unassigned/TOTAL_AGEN*100:.1f}%)    | {siaga_unassigned_count:,} Agen ({siaga_unassigned_count/TOTAL_AGEN*100:.1f}%)")
print(f"{'Tingkat Keselamatan (Tiba <= 20 min)':<42} | {b_safe:,} Agen ({b_safe/TOTAL_AGEN*100:.1f}%)    | {s_safe:,} Agen ({s_safe/TOTAL_AGEN*100:.1f}%)")
print(f"{'Risiko Terpapar (Tiba > 20 min)':<42} | {b_unsafe:,} Agen ({b_unsafe/TOTAL_AGEN*100:.1f}%)     | {s_unsafe:,} Agen ({s_unsafe/TOTAL_AGEN*100:.1f}%)")
print(f"{'Rata-rata Waktu Tempuh Evakuasi':<42} | {b_mean_eta:.2f} menit           | {s_mean_eta:.2f} menit")
print(f"{'Rata-rata Waktu Tempuh Tambahan (Detour)':<42} | {b_detour:.2f} menit           | {s_mean_detour:.2f} menit")
print("=" * 90)

# ---------------------------------------------------------
# 6. REGENERASI PETA BERDAMPINGAN DENGAN HASIL ALAMI RESMI
# ---------------------------------------------------------
print("\n[6/5] Mengubah templat peta berdampingan (peta_simulasi_berdampingan.html) sesuai data alami...")

tes_data_json = []
for idx, row in df_shelter.iterrows():
    cap = int(row['Scaled_Cap'])
    raw_cap_bpbd = int(row['Cap_Raw'])
    
    b_load = int(row['Baseline_Load'])
    b_over = bool(row['Baseline_Over'])
    b_pct = round((b_load / cap) * 100, 1) if cap > 0 else 0
    
    s_load = int(row['Siaga_Load'])
    s_over = bool(row['Siaga_Over'])
    s_pct = round((s_load / cap) * 100, 1) if cap > 0 else 0
    
    tes_data_json.append({
        'id': int(idx),
        'nama': str(row['Nama_Fasilitas']),
        'tipe': str(row['Tipe_Fasilitas']),
        'lat': float(row['Clean_Lat']),
        'lon': float(row['Clean_Lon']),
        'cap': cap,
        'cap_bpbd': raw_cap_bpbd,
        'b_load': b_load,
        'b_over': b_over,
        'b_pct': b_pct,
        's_load': s_load,
        's_over': s_over,
        's_pct': s_pct
    })

json_str = json.dumps(tes_data_json, indent=2)

html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hasil Simulasi Evakuasi Resmi Hibrida V2: Baseline vs Siaga Padang</title>
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>

    <!-- Leaflet Sync Plugin for Dual-Map Syncing -->
    <script src="https://cdn.jsdelivr.net/npm/leaflet.sync@0.2.4/L.Map.Sync.min.js"></script>
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif; background: #0f172a; color: #f8fafc;
            height: 100vh; display: flex; flex-direction: column; overflow: hidden;
        }}
        .top-header {{
            background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding: 10px 24px;
            display: flex; justify-content: space-between; align-items: center; z-index: 10000;
        }}
        .header-title {{
            font-size: 15px; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: flex; gap: 10px;
        }}
        .header-stats {{ display: flex; gap: 14px; font-size: 11px; }}
        .stat-badge {{
            background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 5px 12px; border-radius: 20px; display: flex; gap: 6px;
        }}
        .maps-container {{ flex: 1; display: flex; width: 100%; height: calc(100vh - 56px); position: relative; }}
        .map-wrapper {{ flex: 1; height: 100%; position: relative; border-right: 2px solid rgba(255, 255, 255, 0.15); }}
        .map-wrapper:last-child {{ border-right: none; }}
        .map-instance {{ width: 100%; height: 100%; background: #0f172a; }}
        .map-label-card {{
            position: absolute; top: 14px; left: 50%; transform: translateX(-50%); z-index: 9999;
            background: rgba(15, 23, 42, 0.94); backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 12px; padding: 10px 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4); width: 92%; max-width: 480px;
        }}
        .card-title {{ font-size: 13px; font-weight: 700; display: flex; justify-content: space-between; margin-bottom: 4px; }}
        .card-subtitle {{ font-size: 11px; color: #94a3b8; line-height: 1.45; }}
        .tag-red {{ background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.4); padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }}
        .tag-gray {{ background: rgba(148,163,184,0.2); color: #cbd5e1; border: 1px solid rgba(148,163,184,0.4); padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }}
        .floating-legend {{
            position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 9999;
            background: rgba(15, 23, 42, 0.94); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.15);
            border-radius: 30px; padding: 8px 22px; display: flex; gap: 20px; box-shadow: 0 12px 30px rgba(0,0,0,0.5); font-size: 11px;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; color: #cbd5e1; }}
        .legend-dot {{ width: 13px; height: 13px; border-radius: 50%; display: inline-block; }}
        .leaflet-popup-content-wrapper {{ background: #1e293b !important; color: #f8fafc !important; border-radius: 10px !important; border: 1px solid rgba(255,255,255,0.15) !important; }}
        .leaflet-popup-tip {{ background: #1e293b !important; }}
    </style>
</head>
<body>
    <div class="top-header">
        <div class="header-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 17 22 12"></polyline>
            </svg>
            HASIL SIMULASI HIBRIDA V2 KOTA PADANG (TES + TEA)
        </div>
        <div class="header-stats">
            <div class="stat-badge"><span style="color: #94a3b8;">Total Agen:</span><strong style="color: #38bdf8;">{TOTAL_AGEN:,}</strong></div>
            <div class="stat-badge"><span style="color: #94a3b8;">Fasilitas:</span><strong style="color: #f8fafc;">{total_tes} TES & {total_tea} TEA</strong></div>
            <div class="stat-badge"><span style="color: #94a3b8;">Seed:</span><strong style="color: #cbd5e1;">42</strong></div>
        </div>
    </div>

    <div class="maps-container">
        <!-- BASELINE -->
        <div class="map-wrapper">
            <div class="map-label-card">
                <div class="card-title">
                    <span style="color: #f8fafc;">(a) Baseline — Semua ke TES/TEA Terdekat</span>
                    <span class="tag-red">🔴 {b_over_count} Gedung Overcapacity</span>
                </div>
                <div class="card-subtitle">
                    Seluruh agen memilih fasilitas paling dekat. TEA tidak memiliki batas kapasitas. Murni <strong>{b_over_count} TES (merah)</strong> mengalami beban > kapasitas. Tingkat keselamatan (&le;20 mnt): <strong>{(b_safe/TOTAL_AGEN)*100:.1f}%</strong>.
                </div>
            </div>
            <div id="map-a" class="map-instance"></div>
        </div>

        <!-- SIAGA PADANG -->
        <div class="map-wrapper">
            <div class="map-label-card">
                <div class="card-title">
                    <span style="color: #f8fafc;">(b) Siaga Padang — Hibrida V2 (Capacity-Aware)</span>
                    <span class="tag-gray">🔘 {s_over_count} Gedung Overcapacity</span>
                </div>
                <div class="card-subtitle">
                    Alokasi TES dialihkan saat penuh, TEA menyerap sisa overflow. <strong>{s_over_count} TES overcapacity</strong>, teralokasi: <strong>{siaga_assigned_count:,} agen</strong>. Tingkat keselamatan (&le;20 mnt): <strong>{(s_safe/TOTAL_AGEN)*100:.1f}%</strong>.
                </div>
            </div>
            <div id="map-b" class="map-instance"></div>
        </div>

        <div class="floating-legend">
            <div class="legend-item"><span class="legend-dot" style="background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.8);"></span><span><strong>Hijau:</strong> Lahan TEA (Kapasitas Tak Terbatas)</span></div>
            <div class="legend-item"><span class="legend-dot" style="background: #ef4444;"></span><span><strong>Merah:</strong> TES Overcapacity (Bahaya)</span></div>
            <div class="legend-item"><span class="legend-dot" style="background: #eab308;"></span><span><strong>Kuning:</strong> TES Berdesakan (Toleransi)</span></div>
            <div class="legend-item"><span class="legend-dot" style="background: #64748b; border: 1px solid #94a3b8;"></span><span><strong>Abu-abu:</strong> TES Aman</span></div>
        </div>
    </div>

    <script>
        const tesData = {json_str};
        const mapA = L.map('map-a', {{center: [-0.92, 100.36], zoom: 12}});
        const mapB = L.map('map-b', {{center: [-0.92, 100.36], zoom: 12}});
        const tileUrl = 'https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png';
        L.tileLayer(tileUrl, {{maxZoom: 19}}).addTo(mapA);
        L.tileLayer(tileUrl, {{maxZoom: 19}}).addTo(mapB);
        mapA.sync(mapB); mapB.sync(mapA);

        function createMarker(mapInst, tes, isSiaga) {{
            const isTEA = tes.tipe === 'TEA';
            const load = isSiaga ? tes.s_load : tes.b_load;
            const over = isSiaga ? tes.s_over : tes.b_over;
            const pct = isSiaga ? tes.s_pct : tes.b_pct;
            
            const radius = Math.max(isTEA ? 8 : 4, Math.min(24, Math.sqrt(load) * 1.5));
            let fillColor, strokeColor;
            
            if (isTEA) {{
                fillColor = "#22c55e"; strokeColor = "#166534";
            }} else if (pct > 110) {{
                fillColor = "#ef4444"; strokeColor = "#991b1b"; // Merah
            }} else if (pct > 100) {{
                fillColor = "#eab308"; strokeColor = "#854d0e"; // Kuning
            }} else {{
                fillColor = "#64748b"; strokeColor = "#475569"; // Abu-abu
            }}

            const circle = L.circleMarker([tes.lat, tes.lon], {{
                radius: radius, fillColor: fillColor, color: strokeColor,
                weight: 1.5, opacity: 1.0, fillOpacity: (pct > 100) ? 0.85 : 0.70
            }}).addTo(mapInst);

            let capHtml = isTEA ? '∞ (Lahan Terbuka)' : `${{tes.cap.toLocaleString()}} agen (Resmi BPBD: ${{tes.cap_bpbd.toLocaleString()}})`;
            let statusHtml = isTEA ? '🟢 KAWASAN AMAN (TEA)' : (pct > 110 ? `🔴 BAHAYA OVERKAPASITAS (${{pct}}%)` : (pct > 100 ? `🟡 BERDESAKAN (TOLERANSI) (${{pct}}%)` : `🔘 KAPASITAS AMAN (${{pct}}%)`));
            let statusColor = isTEA ? '#22c55e' : (pct > 110 ? '#f87171' : (pct > 100 ? '#fde047' : '#cbd5e1'));
            
            const popup = `
                <div style="font-size: 12px; line-height: 1.6;">
                    <strong style="font-size: 13px; color: #38bdf8;">${{tes.nama}}</strong><br/>
                    <div style="margin-top: 6px;"><strong>Tipe Fasilitas:</strong> ${{tes.tipe}}</div>
                    <div><strong>Beban Pengungsi:</strong> <span style="color: #cbd5e1;">${{load.toLocaleString()}} agen</span></div>
                    <div><strong>Batas Kapasitas:</strong> ${{capHtml}}</div>
                    <div style="margin-top: 6px; font-weight: 700; color: ${{statusColor}};">${{statusHtml}}</div>
                </div>
            `;
            circle.bindPopup(popup);
            circle.bindTooltip(`<b>${{tes.nama}} (${{tes.tipe}})</b><br/>Beban: ${{load.toLocaleString()}} agen`);
        }}

        tesData.forEach(tes => {{
            createMarker(mapA, tes, false);
            createMarker(mapB, tes, true);
        }});
    </script>
</body>
</html>
"""

output_filename = os.path.join("legacy", "output", "peta_simulasi_berdampingan.html")
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"\n[SUKSES] Peta simulasi berdampingan berhasil diperbarui murni alami: '{output_filename}'")
print(f"Total Eksekusi: {time.time() - start_total:.2f} detik")
