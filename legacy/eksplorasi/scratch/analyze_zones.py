import geopandas as gpd
import pandas as pd
import json

# Load GeoJSON
gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

# Load population data
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

# HOTFIX from core.py
exposed_map['BEROK NIPAH'] = 20000
exposed_map['PASA GADANG'] = 20000

# Check each GeoJSON kelurahan
geojson_names = sorted(gdf['NAMA_UPPER'].unique())
pop_names = sorted(exposed_map.keys())

print("=== KELURAHAN IN GEOJSON ===")
print(f"Total: {len(geojson_names)}")
print()

print("=== CLASSIFICATION RESULTS ===")
safe_list = []
risk_list = []
unmatched = []

for name in geojson_names:
    if name == 'BALAI GADANG':
        safe_list.append((name, 'SAFE (hardcoded)'))
        continue
    
    terpapar = exposed_map.get(name, 0)
    if terpapar == 0:
        safe_list.append((name, f'SAFE (terpapar=0)'))
    else:
        bahaya = "Tinggi" if terpapar > 15000 else ("Sedang" if terpapar > 5000 else "Rendah")
        risk_list.append((name, f'RISK ({bahaya}, terpapar={terpapar})'))
    
    if name not in exposed_map and name != 'BALAI GADANG':
        unmatched.append(name)

print("\n--- SAFE ZONES (Green) ---")
for name, detail in sorted(safe_list):
    print(f"  {name:45s} {detail}")

print(f"\n--- RISK ZONES (Red/Yellow/Orange) ---")
for name, detail in sorted(risk_list):
    print(f"  {name:45s} {detail}")

print(f"\n--- UNMATCHED (not in population CSV => defaults to SAFE) ---")
for name in sorted(unmatched):
    print(f"  {name}")

# Check centroids for known-wrong zones
print("\n\n=== CENTROID ANALYSIS FOR SUSPICIOUS ZONES ===")
for idx, row in gdf.iterrows():
    name = row['NAMA_UPPER']
    centroid = row['geometry'].centroid
    lon, lat = centroid.x, centroid.y
    terpapar = exposed_map.get(name, -1)
    is_safe = 1 if (terpapar == 0 or name == 'BALAI GADANG') else (1 if terpapar == -1 else 0)
    # Print coastal kelurahan that might be incorrectly classified
    if lon < 100.38 and is_safe == 1:
        print(f"  [!SUSPICIOUS SAFE] {name:40s} centroid=({lat:.4f}, {lon:.4f}), terpapar={terpapar}")
    if lon > 100.40 and is_safe == 0:
        print(f"  [!SUSPICIOUS RISK] {name:40s} centroid=({lat:.4f}, {lon:.4f}), terpapar={terpapar}")
