import geopandas as gpd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
geojson_names = sorted(list(gdf_kel[kolom_nama].astype(str).str.upper().str.strip()))
for name in geojson_names:
    print(name)
