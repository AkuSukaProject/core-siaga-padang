import geopandas as gpd
import pandas as pd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")

# Kecamatan pesisir & dataran rendah terpapar tsunami BPBD
kecamatan_rawan = [
    'Padang Barat', 'Padang Utara', 'Padang Selatan', 'Koto Tangah', 
    'Bungus Teluk Kabung', 'Nanggalo', 'Padang Timur', 'Lubuk Begalung', 'Kuranji'
]

# Kecamatan daratan tinggi / pegunungan (Aman Tsunami)
kecamatan_aman = ['Lubuk Kilangan', 'Pauh']

# Khusus kelurahan pegunungan tinggi di kecamatan campuran
kelurahan_aman_khusus = ['Batu Gadang', 'Baringin', 'Indarung', 'Padang Besi', 'Koto Lalang', 'Tarantang', 'Banda Buek', 'Limau Manis', 'Limau Manis Selatan', 'Lambung Bukit', 'Koto Lua', 'Cupak Tangah', 'Kapalo Koto', 'Piai Tangah', 'Pisang']

gdf_kel['IS_RAWAN'] = gdf_kel['WADMKC'].isin(kecamatan_rawan) & (~gdf_kel['NAMOBJ'].isin(kelurahan_aman_khusus))

rawan = gdf_kel[gdf_kel['IS_RAWAN']]
aman = gdf_kel[~gdf_kel['IS_RAWAN']]

print("Total Kelurahan Rawan Tsunami (Merah):", len(rawan))
print("Total Kelurahan Zona Aman (Hijau)   :", len(aman))

print("\nCek Status Berok Nipah & Pasa Gadang:")
print(gdf_kel[gdf_kel['NAMOBJ'].isin(['Berok Nipah', 'Pasa Gadang'])][['NAMOBJ', 'WADMKC', 'IS_RAWAN']])
