"""
Analisis mendalam: Node mana di dekat perbatasan zona hijau yang seharusnya is_safe=1?

Logika saat ini di core.py (line 285-289):
- Jika node ada di kelurahan yang diketahui: pakai is_kelurahan_safe()
- Jika node TIDAK ada di kelurahan manapun: pakai lon > 100.38 sebagai fallback

Masalah:
1. Beberapa kelurahan di DATARAN TINGGI memiliki terpapar > 0 (misal: AIR MANIS=3, GUNUNG SARIK=596)
   padahal seharusnya wilayah ini aman
2. Node yang jatuh di luar semua polygon kelurahan menggunakan fallback longitude saja
   yang mungkin tidak akurat

Kita perlu: menambahkan node/simpang terdekat ke zona hijau yang seharusnya aman
"""
import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

# Connect to DB
conn = sqlite3.connect('ranah_siaga_v2.db')

# Get current node classification
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon, is_safe FROM tb_nodes", conn)

# Get inundation zones
df_inund = pd.read_sql_query("SELECT nama_zona, tingkat_bahaya FROM tb_inundation_zones", conn)
df_safe = pd.read_sql_query("SELECT nama_zona FROM tb_safe_zones", conn)

print(f"Total nodes: {len(df_nodes)}")
print(f"  is_safe=0 (risiko): {len(df_nodes[df_nodes['is_safe']==0])}")
print(f"  is_safe=1 (aman):   {len(df_nodes[df_nodes['is_safe']==1])}")

# Load GeoJSON for spatial check
gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

# Identify nodes that are currently is_safe=0 but are actually inland / high elevation
# Using a more sophisticated check: InaRISK BNPB blue line ~ roughly at longitude 100.38-100.40
# But this depends on the kelurahan

# Check nodes at the boundary
boundary_nodes = df_nodes[
    (df_nodes['is_safe'] == 0) & 
    (df_nodes['lon'] > 100.38)
].copy()

print(f"\nNodes currently RISK but lon > 100.38 (possibly safe): {len(boundary_nodes)}")

# Let's check which kelurahan these boundary nodes belong to
# by spatial join with GeoJSON
gdf_boundary = gpd.GeoDataFrame(
    boundary_nodes,
    geometry=[Point(lon, lat) for lon, lat in zip(boundary_nodes['lon'], boundary_nodes['lat'])],
    crs="EPSG:4326"
)
gdf_joined = gpd.sjoin(gdf_boundary, gdf[['NAMA_UPPER', 'geometry']], how='left', predicate='within')

# Count by kelurahan
kel_counts = gdf_joined.groupby('NAMA_UPPER')['node_id'].count().sort_values(ascending=False)
print(f"\nKelurahan containing RISK nodes with lon > 100.38:")
for kel, count in kel_counts.items():
    print(f"  {kel:45s}: {count} nodes")

# Now check how many nodes are NOT in any kelurahan
unmatched = gdf_joined[gdf_joined['NAMA_UPPER'].isna()]
print(f"\nNodes RISK lon>100.38 NOT in any kelurahan: {len(unmatched)}")

# Also check nodes that are currently is_safe=1 but might be in a risk area
safe_coastal = df_nodes[
    (df_nodes['is_safe'] == 1) & 
    (df_nodes['lon'] < 100.37)
]
print(f"\nNodes currently SAFE but lon < 100.37 (possibly at risk): {len(safe_coastal)}")

conn.close()
