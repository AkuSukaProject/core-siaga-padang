import geopandas as gpd
import pandas as pd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()

mapping = {
    'AIR PACAH': 'AIE PACAH',
    'BATANG KABUNG': 'BATANG KABUNG GANTING',
    'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', # let's check kecamatan/geom
    'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI',
    'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR',
    'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX',
    'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR',
    'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

df_penduduk = pd.read_csv("penduduk_kota_padang.csv")
csv_kel = df_penduduk['DESA'].astype(str).str.upper().str.strip().tolist()

geojson_set = set(gdf_kel['NAMA_UPPER'])

unmapped = []
for c in csv_kel:
    target = mapping.get(c, c)
    if target not in geojson_set:
        unmapped.append((c, target))

print("Unmapped count:", len(unmapped))
print("Unmapped items:", unmapped)
