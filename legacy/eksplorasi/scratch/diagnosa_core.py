import pandas as pd
import geopandas as gpd
import networkx as nx

print("=== DIAGNOSA PERTAMA: SUMMARY ROW JUMLAH DIBACA SEBAGAI SHELTER ===")
df_shelter = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
print("Jumlah baris total CSV shelter:", len(df_shelter))
row_jumlah = df_shelter[df_shelter['Sektor'].astype(str).str.upper() == 'JUMLAH']
print("Baris dengan Sektor 'JUMLAH':")
print(row_jumlah[['Sektor', 'Nama_Bersih', 'Kapasitas_TES', 'Latitude', 'Longitude']])

print("\n=== DIAGNOSA KEDUA: MATCHING KELURAHAN PENDUDUK VS GEOJSON ===")
df_penduduk = pd.read_csv("penduduk_kota_padang.csv")
gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
geojson_kel_set = set(gdf_kel[kolom_nama].astype(str).str.upper().str.strip())
csv_kel_set = set(df_penduduk['DESA'].astype(str).str.upper().str.strip())

matched = csv_kel_set.intersection(geojson_kel_set)
unmatched = csv_kel_set - geojson_kel_set

print(f"Total Kelurahan di CSV Penduduk: {len(csv_kel_set)}")
print(f"Total Kelurahan di GeoJSON: {len(geojson_kel_set)}")
print(f"Kelurahan Cocok: {len(matched)}")
print(f"Kelurahan TIDAK Cocok ({len(unmatched)}):")
for u in sorted(unmatched):
    print("  -", u)
