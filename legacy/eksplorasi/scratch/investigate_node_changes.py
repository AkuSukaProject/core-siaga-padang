"""
Investigasi: mengapa 5061 nodes pindah ke is_safe=0?
Node-node ini sebelumnya is_safe=1 tapi sekarang jadi is_safe=0.

Kemungkinan penyebab:
1. Spatial join mendapat kelurahan yang berbeda dari sebelumnya
2. Kelurahan yang sebelumnya TIDAK ditemukan (lon > 100.38 fallback -> safe)
   sekarang DITEMUKAN dan ternyata kelurahan risiko

Mari kita periksa distribusi kelurahan dari node-node yang berubah.
"""
import sqlite3
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import numpy as np

# Load original DB (ranah_siaga.db) for comparison
conn_old = sqlite3.connect('ranah_siaga.db')
df_old = pd.read_sql_query("SELECT node_id, is_safe FROM tb_nodes", conn_old)
conn_old.close()

conn_new = sqlite3.connect('ranah_siaga_v2.db')
df_new = pd.read_sql_query("SELECT node_id, lat, lon, is_safe FROM tb_nodes", conn_new)

# Find which nodes changed
merged = pd.merge(df_old, df_new, on='node_id', suffixes=('_old', '_new'))

changed = merged[merged['is_safe_old'] != merged['is_safe_new']]
print(f"Total nodes changed: {len(changed)}")

to_safe = changed[changed['is_safe_new'] == 1]
to_risk = changed[changed['is_safe_new'] == 0]
print(f"  Changed to SAFE: {len(to_safe)}")
print(f"  Changed to RISK: {len(to_risk)}")

# Check lon distribution of nodes that changed to risk
if len(to_risk) > 0:
    print(f"\nNodes changed to RISK - longitude stats:")
    print(f"  Min lon: {to_risk['lon'].min():.4f}")
    print(f"  Max lon: {to_risk['lon'].max():.4f}")
    print(f"  Mean lon: {to_risk['lon'].mean():.4f}")
    print(f"  Nodes with lon > 100.38: {len(to_risk[to_risk['lon'] > 100.38])}")
    print(f"  Nodes with lon > 100.40: {len(to_risk[to_risk['lon'] > 100.40])}")

# Spatial join to check which kelurahan these are in
gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

to_risk_gdf = gpd.GeoDataFrame(
    to_risk,
    geometry=[Point(lon, lat) for lon, lat in zip(to_risk['lon'], to_risk['lat'])],
    crs="EPSG:4326"
)
joined = gpd.sjoin(to_risk_gdf, gdf[['NAMA_UPPER', 'geometry']], how='left', predicate='within')

kel_counts = joined.groupby('NAMA_UPPER')['node_id'].count().sort_values(ascending=False)
print(f"\nKelurahan of nodes that changed to RISK:")
for kel, count in kel_counts.items():
    print(f"  {kel:45s}: {count:5d} nodes")

unmatched = joined[joined['NAMA_UPPER'].isna()]
print(f"  (Unmatched/outside polygons):                       {len(unmatched):5d} nodes")

conn_new.close()
