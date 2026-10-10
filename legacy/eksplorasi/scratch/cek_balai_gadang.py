import geopandas as gpd
import pandas as pd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()

df_pend = pd.read_csv("penduduk_kota_padang.csv")
bg = df_pend[df_pend['DESA'].astype(str).str.upper().str.contains('BALAI GADANG')]
print("Data Balai Gadang di CSV BPBD:")
print(bg)

bg_geom = gdf_kel[gdf_kel['NAMA_UPPER'] == 'BALAI GADANG']
print("\nData Balai Gadang di GeoJSON:")
print(bg_geom[['NAMA_UPPER', 'WADMKC']])
