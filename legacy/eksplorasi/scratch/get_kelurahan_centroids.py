import geopandas as gpd
import pandas as pd
import json

# Read kelurahan GeoJSON
gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
print("CRS:", gdf.crs)
print("Columns:", gdf.columns)

name_col = gdf.select_dtypes(include=['object', 'string']).columns[0]
print(f"Name column: {name_col}")

gdf_4326 = gdf.to_crs("EPSG:4326")

target_kelurahans = [
    'BATIPUH PANJANG',
    'KOTO PULAI',
    'BALAI GADANG',
    'KOTO PANJANG IKUA KOTO',
    'AIR PACAH', 'AIE PACAH',
    'DADOK TUNGGUL HITAM',
    'GUNUNG PANGILUN',
    'SUNGAI SAPIH',
    'KUBU MARAPALAM',
    'TELUK KABUNG UTARA', 'TALUAK KABUANG UTARA',
    'BANUARAN NAN XX', 'BANUARAN'
]

print("\n--- MATCHING KELURAHAN CENTROIDS & BOUNDS ---")
for tk in target_kelurahans:
    m = gdf_4326[gdf_4326[name_col].astype(str).str.upper().str.contains(tk, na=False)]
    if not m.empty:
        for idx, row in m.iterrows():
            c = row.geometry.centroid
            print(f"{row[name_col]} -> Centroid: Lat {c.y:.6f}, Lon {c.x:.6f}")
