"""
Investigasi mendalam: kelurahan mana yang salah klasifikasi zona?

Berdasarkan data BPBD, kelurahan TERPAPAR tsunami = ada data jiwa terpapar > 0.
Namun beberapa kelurahan PESISIR (longitude kecil / dekat pantai) yang punya data terpapar SANGAT KECIL
sebenarnya tidak seharusnya berwarna risiko karena wilayahnya mayoritas di DATARAN TINGGI,
sementara ada kelurahan daratan yang warnanya benar.

ISSUE 1: AIR MANIS terpapar=3 -> harusnya SAFE/Hijau (hampir tidak ada jiwa terpapar, wilayahnya dataran tinggi)
ISSUE 2: BUKIT GADO-GADO terpapar=0 -> sudah SAFE (benar)
ISSUE 3: LUBUK BEGALUNG NAN XX terpapar=0 -> sudah SAFE (benar)

Tapi masalah sesungguhnya lebih dari itu. Kita perlu mengerti PETA ZONA TSUNAMI berdasarkan
data resmi InaRISK BNPB, bukan hanya berdasarkan jumlah jiwa terpapar.

Dari screenshot user, masalah pewarnaan zona:
- Zona di pesisir Padang bagian barat berwarna campuran merah/kuning/oranye (ini benar - risiko)
- Zona di timur (dataran tinggi) berwarna hijau (ini benar - aman)
- TAPI ada beberapa zona di perbatasan yang SALAH WARNA

Mari kita cek mana kelurahan yang "di perbatasan" dan seharusnya beda klasifikasi
"""

import geopandas as gpd
import pandas as pd

gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

df_pop = pd.read_csv("penduduk_kota_padang.csv")
kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH',
    'BATANG KABUNG': 'BATANG KABUNG GANTING',
    'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA',
    'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI',
    'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR',
    'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX',
    'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR',
    'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

exposed_map = dict(zip(
    df_pop['DESA'].astype(str).str.upper().str.strip().apply(lambda x: kelurahan_alias.get(x, x)),
    df_pop['JUMLAH JIWA TERPAPAR (JIWA)']
))
exposed_map['BEROK NIPAH'] = 20000
exposed_map['PASA GADANG'] = 20000

# Periksa kelurahan yang terpapar sangat kecil tapi mayoritas wilayahnya di dataran tinggi
print("=== KELURAHAN TERPAPAR MINIMAL (mungkin seharusnya SAFE) ===")
for name in sorted(exposed_map.keys()):
    terpapar = exposed_map[name]
    if terpapar > 0 and terpapar <= 100:
        print(f"  {name:45s} terpapar={terpapar}")

# Check all kecamatan mapping
print("\n=== KECAMATAN MAPPING ===")
kec_map = dict(zip(
    df_pop['DESA'].astype(str).str.upper().str.strip().apply(lambda x: kelurahan_alias.get(x, x)),
    df_pop['KECAMATAN']
))

# Focus on kelurahan yang dari screenshot terlihat salah warna
# Berdasarkan screenshot: zona di area timur (inland) yang masih berwarna risiko padahal seharusnya hijau
# Ini biasanya karena kelurahan-kelurahan yang TERPAPAR SEDIKIT tapi areanya luas sampai ke dataran tinggi

print("\n=== KELURAHAN YANG MUNGKIN SALAH KLASIFIKASI ===")
print("(Terpapar sangat kecil / area wilayah besar sampai ke dataran tinggi)")
candidates = []
for idx, row in gdf.iterrows():
    name = row['NAMA_UPPER']
    terpapar = exposed_map.get(name, 0)
    geom = row['geometry']
    centroid = geom.centroid
    bounds = geom.bounds  # minx, miny, maxx, maxy
    
    if terpapar > 0:
        # Kelurahan risiko yang punya area sampai timur (dataran tinggi)
        if bounds[2] > 100.40:  # maxx > 100.40
            area_km2 = geom.area * 111 * 111  # rough conversion
            print(f"  RISK extending east: {name:40s} terpapar={terpapar:6d}, centroid=({centroid.y:.4f},{centroid.x:.4f}), bounds_east={bounds[2]:.4f}, area~{area_km2:.1f}km2")

print("\n=== KELURAHAN SAFE YANG CENTROID-NYA DI PESISIR ===")
for idx, row in gdf.iterrows():
    name = row['NAMA_UPPER']
    terpapar = exposed_map.get(name, 0)
    geom = row['geometry']
    centroid = geom.centroid
    
    is_safe = (terpapar == 0 or name == 'BALAI GADANG') if name in exposed_map else True
    if is_safe and centroid.x < 100.38:
        print(f"  SAFE but coastal: {name:40s} centroid=({centroid.y:.4f},{centroid.x:.4f})")
