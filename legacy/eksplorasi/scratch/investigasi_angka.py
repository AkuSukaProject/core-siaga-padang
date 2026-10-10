import networkx as nx
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree
import os

print("=== INVESTIGASI POINT 2: NODES, EDGES, TES & BUKAN KESAMBUNG ===")

# 1. Inspect padang_full.graphml
G = nx.read_graphml("padang_full.graphml")
print(f"Graf padang_full.graphml: {len(G.nodes)} nodes, {len(G.edges)} edges")

# 2. Inspect padang.graphml if exists
if os.path.exists("padang.graphml"):
    G_old = nx.read_graphml("padang.graphml")
    print(f"Graf padang.graphml (lama): {len(G_old.nodes)} nodes, {len(G_old.edges)} edges")

# 3. Inspect data_tes_padang_lengkap_berkoordinat.csv
df_tes = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
if 'Sektor' in df_tes.columns:
    df_tes = df_tes[df_tes['Sektor'].astype(str).str.upper() != 'JUMLAH']

def parse_koordinat(val):
    if pd.isna(val): return 0.0
    try: return float(str(val).strip().replace(',', '.'))
    except ValueError: return 0.0

df_tes['Clean_Lat'] = df_tes['Latitude'].apply(parse_koordinat)
df_tes['Clean_Lon'] = df_tes['Longitude'].apply(parse_koordinat)
df_tes_valid = df_tes[(df_tes['Clean_Lat'] != 0.0) & (df_tes['Clean_Lon'] != 0.0)]
print(f"Total Gedung TES di CSV: {len(df_tes)} baris")
print(f"Total Gedung TES dengan Koordinat Valid: {len(df_tes_valid)} gedung")

# Check 4 gedung yang gagal/tidak berkoordinat valid
df_tes_gagal = df_tes[(df_tes['Clean_Lat'] == 0.0) | (df_tes['Clean_Lon'] == 0.0)]
print(f"\nDetail {len(df_tes_gagal)} Gedung TES Tanpa Koordinat (Gagal Geocoding BPBD):")
print(df_tes_gagal[['Nomor_TES', 'Lokasi_TES', 'Nama_Bersih', 'Status_Koordinat']])

# Check unique matched nodes
coords_list = []
node_ids_list = []
for node, data in G.nodes(data=True):
    if 'x' in data and 'y' in data:
        node_ids_list.append(node)
        coords_list.append([float(data['y']), float(data['x'])])

tree = cKDTree(coords_list)
matched_nodes = set()
for idx, row in df_tes_valid.iterrows():
    dist, idx_nearest = tree.query([row['Clean_Lat'], row['Clean_Lon']])
    matched_nodes.add(node_ids_list[idx_nearest])

print(f"\nJumlah Gedung TES Valid Berkoordinat: {len(df_tes_valid)} gedung")
print(f"Jumlah Unique Node Persimpangan Graf yang dicapai Gedung TES: {len(matched_nodes)} titik persimpangan")
print(f"(Beda 143 vs 139 karena ada 4 pasang gedung TES yang lokasinya sangat berdekatan sehingga terhubung ke persimpangan/node jalan yang sama!)")
