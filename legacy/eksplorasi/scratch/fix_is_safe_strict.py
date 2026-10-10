import sqlite3
import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point
import time

print("=" * 60)
print("PERBAIKAN STRICT NODE is_safe BERDASARKAN POLIGON ZONA")
print("=" * 60)

start = time.time()
conn = sqlite3.connect('ranah_siaga_v2.db')
cur = conn.cursor()

# 1. Load Nodes
print("[1/4] Memuat koordinat node...")
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon FROM tb_nodes", conn)
gdf_nodes = gpd.GeoDataFrame(
    df_nodes, 
    geometry=[Point(lon, lat) for lon, lat in zip(df_nodes['lon'], df_nodes['lat'])],
    crs="EPSG:4326"
)

# 2. Load Polygons from Database (Source of Truth)
print("[2/4] Memuat poligon Inundation dan Safe dari DB...")
# Inundation (Risk)
cur.execute("SELECT zone_id, geometry_wkt FROM tb_inundation_zones")
inund_geom = [wkt.loads(row[1]) for row in cur.fetchall()]
gdf_inund = gpd.GeoDataFrame(geometry=inund_geom, crs="EPSG:4326")

# Safe
cur.execute("SELECT safe_zone_id, geometry_wkt FROM tb_safe_zones")
safe_geom = [wkt.loads(row[1]) for row in cur.fetchall()]
gdf_safe = gpd.GeoDataFrame(geometry=safe_geom, crs="EPSG:4326")

# 3. Spatial Join
print("[3/4] Melakukan pencocokan spasial (Spatial Join)...")
# Default all to 0 (Risk)
updates = {node_id: 0 for node_id in df_nodes['node_id']}

# Cek node di Safe Zones
joined_safe = gpd.sjoin(gdf_nodes, gdf_safe, how='inner', predicate='intersects')
for node_id in joined_safe['node_id']:
    updates[node_id] = 1

# Cek node di Inundation Zones (Akan menimpa jika ada overlap, tapi seharusnya disjoint)
joined_inund = gpd.sjoin(gdf_nodes, gdf_inund, how='inner', predicate='intersects')
for node_id in joined_inund['node_id']:
    updates[node_id] = 0

# Untuk node yang tidak kena poligon manapun, kita tetapkan berdasarkan longitude 
# sebagai fallback terakhir, tapi karena ini perbatasan kota Padang, jarang terjadi.
unmatched_nodes = set(df_nodes['node_id']) - set(joined_safe['node_id']) - set(joined_inund['node_id'])
for node_id in unmatched_nodes:
    lon = df_nodes.loc[df_nodes['node_id'] == node_id, 'lon'].values[0]
    updates[node_id] = 1 if lon > 100.38 else 0

# 4. Update Database
print("[4/4] Mengupdate database...")
batch_size = 1000
update_data = [(val, nid) for nid, val in updates.items()]

for i in range(0, len(update_data), batch_size):
    cur.executemany("UPDATE tb_nodes SET is_safe = ? WHERE node_id = ?", update_data[i:i+batch_size])

conn.commit()

# Verifikasi Akhir
cur.execute("SELECT is_safe, COUNT(*) FROM tb_nodes GROUP BY is_safe")
stats = cur.fetchall()
print(f"\nDistribusi Final is_safe:")
for is_safe, count in stats:
    label = "Aman" if is_safe == 1 else "Risiko"
    print(f"  {label} (is_safe={is_safe}): {count}")

conn.close()
print(f"\n[SUKSES] Selesai dalam {time.time() - start:.2f} detik")
