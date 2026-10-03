import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os
import sys

DB_PATH = "../ranah_siaga_v3.db"

print("Memuat batas kelurahan dan memetakan node ke kelurahan...")
conn = sqlite3.connect(DB_PATH)
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon, is_safe FROM tb_nodes", conn)

gdf_nodes = gpd.GeoDataFrame(df_nodes, geometry=gpd.points_from_xy(df_nodes.lon, df_nodes.lat), crs="EPSG:4326")
print("Menghitung demand penduduk (distribusi seragam ke simpul rawan)...")
df_penduduk = pd.read_csv("../penduduk_kota_padang.csv")
total_pop = df_penduduk['JUMLAH JIWA TERPAPAR (JIWA)'].sum()
unsafe_nodes = df_nodes[df_nodes['is_safe'] == 0]['node_id'].tolist()
pop_per_node = total_pop / len(unsafe_nodes) if len(unsafe_nodes) > 0 else 0

node_demands = {nid: pop_per_node for nid in unsafe_nodes}
print(f"Total populasi terekstrak ke simpul: {sum(node_demands.values()):.0f} ({pop_per_node:.2f} per simpul)")

print(f"Total populasi terekstrak ke simpul: {sum(node_demands.values()):.0f}")

print("Membaca data kandidat rute dan kapasitas TES...")
df_tes = pd.read_sql_query("SELECT nama_tes, kapasitas FROM tb_tes", conn)
tes_capacity = dict(zip(df_tes['nama_tes'], df_tes['kapasitas']))

df_routes = pd.read_sql_query("SELECT * FROM tb_routes", conn)
try:
    df_tea = pd.read_sql_query("SELECT origin_node_id, nearest_tea_nama, nearest_tea_eta, alt_tea_nama, alt_tea_eta FROM tb_tea_routes", conn)
except:
    df_tea = pd.DataFrame()
try:
    df_safe = pd.read_sql_query(
        "SELECT r.origin_node_id, z.nama_zona AS safe_zone_nama, r.safe_eta "
        "FROM tb_safe_routes r JOIN tb_safe_zones z ON z.safe_zone_id = r.safe_zone_id", conn)
except:
    df_safe = pd.DataFrame()

# Gabungkan semua kandidat
all_candidates = [] # list of (node_id, type, name, eta, capacity)

for idx, row in df_routes.iterrows():
    nid = row['origin_node_id']
    if pd.notna(row['rank_1_tes']) and pd.notna(row['rank_1_eta']):
        all_candidates.append((nid, 'TES', row['rank_1_tes'], row['rank_1_eta'], tes_capacity.get(row['rank_1_tes'], 0)))
    if pd.notna(row['rank_2_tes']) and pd.notna(row['rank_2_eta']):
        all_candidates.append((nid, 'TES', row['rank_2_tes'], row['rank_2_eta'], tes_capacity.get(row['rank_2_tes'], 0)))
    if pd.notna(row['rank_3_tes']) and pd.notna(row['rank_3_eta']):
        all_candidates.append((nid, 'TES', row['rank_3_tes'], row['rank_3_eta'], tes_capacity.get(row['rank_3_tes'], 0)))

if not df_tea.empty:
    for idx, row in df_tea.iterrows():
        nid = row['origin_node_id']
        if pd.notna(row['nearest_tea_nama']) and pd.notna(row['nearest_tea_eta']):
            all_candidates.append((nid, 'TEA', row['nearest_tea_nama'], row['nearest_tea_eta'], float('inf')))
        if pd.notna(row['alt_tea_nama']) and pd.notna(row['alt_tea_eta']):
            all_candidates.append((nid, 'TEA', row['alt_tea_nama'], row['alt_tea_eta'], float('inf')))

if not df_safe.empty:
    for idx, row in df_safe.iterrows():
        nid = row['origin_node_id']
        if pd.notna(row['safe_zone_nama']) and pd.notna(row['safe_eta']):
            all_candidates.append((nid, 'ZONA_AMAN', row['safe_zone_nama'], row['safe_eta'], float('inf')))

df_cand = pd.DataFrame(all_candidates, columns=['node_id', 'jenis', 'nama_tujuan', 'eta', 'kapasitas'])

print("Melakukan penugasan (Greedy)...")
# Cepat: pisahkan menjadi yang <= 20 dan yang tidak
df_cand['is_feasible'] = df_cand['eta'] <= 20.0

# Dapatkan node yang PUNYA tujuan <= 20
feasible_nodes = df_cand[df_cand['is_feasible']]['node_id'].unique()

# Bagi df jadi 2:
# 1. Yang punya tujuan feasible (ambil semua baris feasible-nya)
df_feasible = df_cand[(df_cand['node_id'].isin(feasible_nodes)) & (df_cand['is_feasible'])]

# 2. Yang tidak punya tujuan feasible (ambil SATU tujuan tercepat per node)
df_unfeasible = df_cand[~df_cand['node_id'].isin(feasible_nodes)]
idx_min = df_unfeasible.groupby('node_id')['eta'].idxmin()
df_fallback = df_unfeasible.loc[idx_min] if not idx_min.empty else pd.DataFrame()

df_valid = pd.concat([df_feasible, df_fallback]).drop_duplicates()

# Sort by ETA untuk greedy assignment
df_valid = df_valid.sort_values('eta')

tes_loads = {nama: 0.0 for nama in df_tes['nama_tes']}
node_assignments = {} # nid -> {tujuan: assigned_pop}

for idx, row in df_valid.iterrows():
    nid = row['node_id']
    if nid not in node_demands or node_demands[nid] <= 0:
        continue
    
    demand = node_demands[nid]
    tujuan = row['nama_tujuan']
    jenis = row['jenis']
    
    if jenis == 'TES':
        cap = tes_capacity.get(tujuan, 0)
        curr_load = tes_loads.get(tujuan, 0)
        avail = max(0, cap - curr_load)
        
        assign = min(demand, avail)
        tes_loads[tujuan] += assign
    else:
        # TEA / Zona Aman = tak terhingga
        assign = demand
        
    if assign > 0:
        node_demands[nid] -= assign
        if nid not in node_assignments:
            node_assignments[nid] = {}
        # gunakan tuple (jenis, nama_tujuan) sebagai key
        key = (jenis, tujuan)
        node_assignments[nid][key] = node_assignments[nid].get(key, 0) + assign

# Sisa demand yang tidak kebagian (seharusnya tidak ada karena ada TEA/Zona Aman yang infinite) dipaksa ke tercepat
for nid, rem_demand in node_demands.items():
    if rem_demand > 0.01:
        group = df_cand[df_cand['node_id'] == nid]
        if not group.empty:
            fastest = group.loc[group['eta'].idxmin()]
            jenis = fastest['jenis']
            tujuan = fastest['nama_tujuan']
            if nid not in node_assignments:
                node_assignments[nid] = {}
            key = (jenis, tujuan)
            node_assignments[nid][key] = node_assignments[nid].get(key, 0) + rem_demand

print("Menyimpan porsi ke database...")
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS tb_route_shares")
cursor.execute('''CREATE TABLE tb_route_shares (
                    origin_node_id INTEGER,
                    jenis TEXT,
                    nama_tujuan TEXT,
                    porsi REAL
                )''')

shares_data = []
for nid, assignments in node_assignments.items():
    total_assign = sum(assignments.values())
    if total_assign > 0:
        for (jenis, tujuan), assign in assignments.items():
            porsi = assign / total_assign
            shares_data.append((nid, jenis, tujuan, porsi))

cursor.executemany("INSERT INTO tb_route_shares VALUES (?, ?, ?, ?)", shares_data)

# Buat indeks
cursor.execute("CREATE INDEX IF NOT EXISTS idx_shares_origin ON tb_route_shares(origin_node_id)")

conn.commit()
conn.close()

print(f"Berhasil membuat tabel tb_route_shares dengan {len(shares_data)} baris.")
