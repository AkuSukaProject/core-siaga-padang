import pandas as pd
import geopandas as gpd

df_pend = pd.read_csv("penduduk_kota_padang.csv")
print("=== DEMOGRAFI TERPAPAR BPBD (penduduk_kota_padang.csv) ===")
print("Total Kelurahan di CSV BPBD:", len(df_pend))

# Cek Lubuk Minturun
lm_in_csv = df_pend[df_pend['DESA'].astype(str).str.upper().str.contains('LUBUK MINTURUN|MINTURUN')]
print("\nLubuk Minturun di CSV BPBD:")
print(lm_in_csv)

# Cek Kuranji (Kelurahan Kuranji)
kr_in_csv = df_pend[df_pend['DESA'].astype(str).str.upper() == 'KURANJI']
print("\nKelurahan KURANJI di CSV BPBD:")
print(kr_in_csv)

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()

print("\nCek Lubuk Minturun di GeoJSON Padang:")
print(gdf_kel[gdf_kel['NAMA_UPPER'].str.contains('MINTURUN')][['NAMA_UPPER', 'WADMKC']])

print("\nCek Kelurahan KURANJI di GeoJSON Padang:")
print(gdf_kel[gdf_kel['NAMA_UPPER'] == 'KURANJI'][['NAMA_UPPER', 'WADMKC']])
