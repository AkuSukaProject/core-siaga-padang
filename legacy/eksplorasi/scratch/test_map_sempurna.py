import geopandas as gpd
import pandas as pd

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()

# 1. Start from BPBD official exposed kelurahan from penduduk_kota_padang.csv
df_pend = pd.read_csv("penduduk_kota_padang.csv")
bpbd_exposed = set(df_pend['DESA'].astype(str).str.upper().str.strip())

# Add alias mapping
kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

rawan_set = set([kelurahan_alias.get(k, k) for k in bpbd_exposed])

# Add coastal kelurahan right on beach/estuary (Padang Barat & Padang Selatan coastal)
coastal_additions = ['BEROK NIPAH', 'PASA GADANG']
for c in coastal_additions:
    rawan_set.add(c)

# Explicitly exclude inland mountain kelurahan
inland_safe = ['LUBUK MINTURUN', 'KURANJI', 'BALAI GADANG', 'BATU GADANG', 'BARINGIN', 'INDARUNG', 'PADANG BESI', 'KOTO LALANG', 'TARANTANG', 'BANDA BUEK']
for s in inland_safe:
    if s in rawan_set:
        rawan_set.remove(s)

gdf_kel['IS_RAWAN'] = gdf_kel['NAMA_UPPER'].isin(rawan_set)

rawan_gdf = gdf_kel[gdf_kel['IS_RAWAN']]
aman_gdf = gdf_kel[~gdf_kel['IS_RAWAN']]

print(f"Total Kelurahan MERAH (Rawan Tsunami BPBD + Pesisir): {len(rawan_gdf)}")
print(f"Total Kelurahan HIJAU (Zona Aman / Perbukitan)     : {len(aman_gdf)}")

print("\nCek Status Kelurahan Kunci:")
test_names = ['BEROK NIPAH', 'PASA GADANG', 'LUBUK MINTURUN', 'KURANJI', 'PASIE NAN TIGO', 'PURUS', 'BALAI GADANG', 'INDARUNG']
for t in test_names:
    res = "[RAWAN / MERAH]" if t in rawan_set else "[AMAN / HIJAU]"
    print(f"  - {t:<20} : {res}")
