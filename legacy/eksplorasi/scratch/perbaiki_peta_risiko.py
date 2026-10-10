import geopandas as gpd
import pandas as pd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()

print("Daftar seluruh 104 Kelurahan di GeoJSON Padang:")

# Kelurahan Pesisir & Dataran Rendah Rawan Tsunami di Padang (Koto Tangah, Padang Utara, Padang Barat, Padang Selatan, Padang Timur, Nanggalo, Lubuk Begalung, Bungus)
# Kita bisa mengklasifikasikan berdasarkan Kecamatan atau Kedekatan Pesisir

# Cek kolom apa saja di GeoJSON
print("Kolom di GeoJSON:", gdf_kel.columns.tolist())
print(gdf_kel[['NAMA_UPPER']].head(30))
