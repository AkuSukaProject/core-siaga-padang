import sys, networkx as nx, pandas as pd, numpy as np, geopandas as gpd, time, os, re, json
from scipy.spatial import cKDTree
from pyproj import Transformer
from shapely.geometry import Point

RANDOM_SEED = 42
TOTAL_AGEN = 20000
TSUNAMI_DEADLINE_MIN = 20.0
np.random.seed(RANDOM_SEED)

G = nx.read_graphml("padang_full.graphml").to_undirected()
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
    data['t0'] = bersihkan_angka(data.get('length', 50.0)) / 1.2 / 60.0 

df_shelter = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
if 'Sektor' in df_shelter.columns:
    df_shelter = df_shelter[df_shelter['Sektor'].astype(str).str.upper() != 'JUMLAH']

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
    tes_details[idx] = {'node': matched_node}

tes_nodes_unique = list(set(tes_nodes_list))
df_pend = pd.read_csv("penduduk_kota_padang.csv")
total_pop = df_pend['JUMLAH JIWA TERPAPAR (JIWA)'].sum()
scaling_factor = TOTAL_AGEN / total_pop
df_shelter['Scaled_Cap'] = df_shelter['Cap_Raw'].apply(lambda c: max(int(round(c * scaling_factor)), 1))

file_geojson = "batas_kelurahan_kota_padang.geojson"
nodes_per_kel = {}
if os.path.exists(file_geojson):
    gdf_kel = gpd.read_file(file_geojson)
    gdf_kel = gdf_kel.to_crs("EPSG:4326")
    kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
    gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()
    nodes_gdf_list = [{'node_id': n, 'geometry': Point(d['x'], d['y'])} for n, d in G.nodes(data=True) if 'x' in d and 'y' in d]
    gdf_nodes = gpd.GeoDataFrame(nodes_gdf_list, crs="EPSG:4326")
    gdf_joined = gpd.sjoin(gdf_nodes, gdf_kel, how="inner", predicate="within")
    nodes_per_kel = gdf_joined.groupby('NAMA_UPPER')['node_id'].apply(list).to_dict()

kelurahan_alias = {'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO', 'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH', 'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO', 'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'}

agent_origins = []
for idx, r in df_pend.iterrows():
    k_name = str(r['DESA']).strip().upper()
    k_name = kelurahan_alias.get(k_name, k_name)
    n_agen = int(round((r['JUMLAH JIWA TERPAPAR (JIWA)'] / total_pop) * TOTAL_AGEN))
    avail = nodes_per_kel.get(k_name, node_ids)
    if avail:
        agent_origins.extend(np.random.choice(avail, size=n_agen, replace=True))

tes_dijkstra = {}
for t_node in tes_nodes_unique:
    lengths, paths = nx.single_source_dijkstra(G, source=t_node, weight='t0')
    tes_dijkstra[t_node] = lengths

agent_candidates = []
for agent_id, origin_node in enumerate(agent_origins):
    cands = []
    for idx_shelter, row_s in df_shelter.iterrows():
        t_node = tes_details[idx_shelter]['node']
        if origin_node in tes_dijkstra[t_node]:
            cands.append({'tes_idx': idx_shelter, 'eta': tes_dijkstra[t_node][origin_node]})
    if cands:
        cands.sort(key=lambda x: x['eta'])
        agent_candidates.append({'cands': cands})

sorted_agent_candidates = sorted(agent_candidates, key=lambda x: x['cands'][0]['eta'])

siaga_b_load = {idx: 0 for idx in df_shelter.index}
siaga_etas = []
siaga_assigned_count = 0
for item in sorted_agent_candidates:
    assigned = False
    for cand in item['cands']:
        idx_tes = cand['tes_idx']
        cap = df_shelter.loc[idx_tes, 'Scaled_Cap']
        if siaga_b_load[idx_tes] < cap:
            siaga_b_load[idx_tes] += 1
            siaga_etas.append(cand['eta'])
            siaga_assigned_count += 1
            assigned = True
            break

s_safe = sum(1 for eta in siaga_etas if eta <= TSUNAMI_DEADLINE_MIN)
print(f"OLD Siaga Safe: {s_safe} ({(s_safe/TOTAL_AGEN)*100:.2f}%)")
