import geopandas as gpd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
print(gdf_kel[['NAMOBJ', 'WADMKC']].drop_duplicates().to_string())
print("\nDaftar Kecamatan di GeoJSON Padang:")
print(gdf_kel['WADMKC'].value_counts())
