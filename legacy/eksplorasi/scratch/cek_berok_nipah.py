import pandas as pd
import geopandas as gpd

df_penduduk = pd.read_csv("penduduk_kota_padang.csv")
print("Cari BEROK NIPAH dan PASA GADANG di penduduk_kota_padang.csv:")
print(df_penduduk[df_penduduk['DESA'].astype(str).str.contains('BEROK|NIPAH|PASA|GADANG', case=False, na=False)])

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()

print("\nCari BEROK NIPAH dan PASA GADANG di GeoJSON:")
print(gdf_kel[gdf_kel['NAMA_UPPER'].str.contains('BEROK|NIPAH|PASA|GADANG', case=False, na=False)][['NAMA_UPPER']])
