import geopandas as gpd
import pandas as pd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
geojson_names = sorted(list(gdf_kel[kolom_nama].astype(str).str.upper().str.strip()))

print("Terdapat", len(geojson_names), "kelurahan di GeoJSON.")

unmatched_csv = [
    'AIR PACAH', 'BATANG KABUNG', 'BUKIK GADO GADO', 'KAMPUNG JAO', 
    'KAMPUNG LAPAI BARU', 'KUBU PARAK KARAKAH', 'MATO AIE', 
    'PARAK LAWEH PULAU AIR NAN XX', 'PASIR NAN TIGO', 'TALUAK BAYUA', 'TANJUANG AUR NAN XX'
]

for name in unmatched_csv:
    # Cari nama paling mirip di GeoJSON
    candidates = [g for g in geojson_names if any(w in g for w in name.split() if len(w) > 3)]
    print(f"CSV: '{name}' -> Candidates di GeoJSON: {candidates}")
