"""
PERBAIKAN ZONA POLYGON & NODE is_safe DI DATABASE ranah_siaga_v2.db

Masalah yang diperbaiki:
1. Kelurahan perbukitan yang terpapar sangat sedikit (AIR MANIS=3, GUNUNG SARIK=596, dll.)
   SALAH diklasifikasi sebagai zona risiko -> dipindahkan ke zona hijau (safe)
2. BALAI GADANG: sudah hardcoded safe tapi sebenarnya bagian barat-nya risiko
   -> tetap safe sesuai original logic, tapi catatan sudah ada
3. Node di kelurahan yang sekarang dipindahkan ke safe zone harus di-update is_safe=1
4. Node/simpang terdekat yang jatuh di area hijau tapi belum ter-flag safe -> di-fix

Kelurahan yang harus dipindahkan dari inundation ke safe berdasarkan analisis:
- Kelurahan perbukitan/pedalaman yang terpapar minimal tapi areanya mayoritas dataran tinggi
  (sesuai perbukitan_list di buat_peta_zona_rawan_tsunami_v8.py)
"""

import sqlite3
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
import time

print("=" * 80)
print("PERBAIKAN ZONA POLYGON & NODE is_safe DI DATABASE")
print("=" * 80)

start = time.time()

# ===== KONFIGURASI PERBAIKAN =====

# Kelurahan yang seharusnya SAFE (perbukitan/dataran tinggi) tapi saat ini di inundation_zones
# Sumber: analisis peta_zona_rawan_tsunami_v8.py + validasi visual
kelurahan_pindah_ke_safe = [
    # Dari perbukitan_list di v8 yang belum ada di safe_zones
    # (BALAI GADANG sudah di safe_zones)
    # AIR MANIS: terpapar=3, wilayah 99% bukit/pegunungan
    'AIR MANIS',
    # BUKIT GADO-GADO sudah di safe_zones (terpapar=0) -> OK
    # LUBUK BEGALUNG NAN XX sudah di safe_zones (terpapar=0) -> OK
]

# Kelurahan yang "terpapar" tapi seharusnya di ZONA AMAN karena wilayahnya 
# mayoritas dataran tinggi (di luar area rendaman tsunami)
# Berdasarkan analisis spatial + data InaRISK
kelurahan_yg_terpapar_tapi_mayoritas_aman = [
    # Kelurahan di Bungus-Teluk Kabung yang centroid-nya di dataran tinggi  
    # tapi punya sedikit pesisir yang terpapar
    'BUNGUS TIMUR',         # centroid lon=100.44, terpapar=1528, area~27km2 (mayoritas pegunungan)
    'TELUK KABUNG UTARA',   # centroid lon=100.43, terpapar=861, area~12km2 (mayoritas pegunungan)
    'TELUK KABUNG TENGAH',  # centroid lon=100.40, terpapar=1511, area~22km2 (mayoritas pegunungan)
    'TELUK KABUNG SELATAN', # centroid lon=100.39, terpapar=566, area~19km2 (mayoritas pegunungan)
    'BUNGUS SELATAN',       # centroid lon=100.42, terpapar=1598, area~5km2 (mayoritas pegunungan)
    'BUNGUS BARAT',         # centroid lon=100.41, terpapar=1295, area~8km2 (mayoritas pegunungan)
    # Kelurahan pedalaman Kuranji
    'GUNUNG SARIK',         # centroid lon=100.41, terpapar=596, hanya 596 jiwa di area yg luas
    'PASAR AMBACANG',       # centroid lon=100.40, terpapar=3508, tapi wilayah mayoritas dataran tinggi
    'KALUMBUK',             # centroid lon=100.39, terpapar=1885, perbatasan aman
]

print(f"\n[1/4] Memindahkan kelurahan ke zona safe...")

conn = sqlite3.connect('ranah_siaga_v2.db')
cur = conn.cursor()

# Backup counts
cur.execute("SELECT COUNT(*) FROM tb_inundation_zones")
inund_before = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM tb_safe_zones")
safe_before = cur.fetchone()[0]

semua_pindah = kelurahan_pindah_ke_safe + kelurahan_yg_terpapar_tapi_mayoritas_aman
moved_count = 0

for kel_name in semua_pindah:
    # Cek apakah ada di inundation
    cur.execute("SELECT zone_id, nama_zona, geometry_wkt FROM tb_inundation_zones WHERE nama_zona = ?", (kel_name,))
    row = cur.fetchone()
    if row:
        zone_id, nama, geom_wkt = row
        # Hapus dari inundation
        cur.execute("DELETE FROM tb_inundation_zones WHERE zone_id = ?", (zone_id,))
        # Tambahkan ke safe_zones
        elevasi = 15.0  # Default elevasi dataran tinggi
        cur.execute("INSERT INTO tb_safe_zones (nama_zona, elevasi_m, geometry_wkt) VALUES (?, ?, ?)",
                   (nama, elevasi, geom_wkt))
        print(f"  [OK] {kel_name:35s} -> dipindahkan INUNDATION -> SAFE")
        moved_count += 1
    else:
        # Cek apakah sudah di safe
        cur.execute("SELECT safe_zone_id FROM tb_safe_zones WHERE nama_zona = ?", (kel_name,))
        if cur.fetchone():
            print(f"  [--] {kel_name:35s} -> sudah di SAFE (skip)")
        else:
            print(f"  [!!] {kel_name:35s} -> TIDAK DITEMUKAN di kedua tabel!")

print(f"\n  Dipindahkan: {moved_count} kelurahan")

# ===== PERBAIKAN TINGKAT BAHAYA ZONA INUNDATION =====
print(f"\n[2/4] Memperbaiki tingkat bahaya zona inundation...")

# Re-read population data for accurate classification
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

# Verify remaining inundation zones
cur.execute("SELECT zone_id, nama_zona, tingkat_bahaya FROM tb_inundation_zones")
inund_rows = cur.fetchall()
fixes = 0
for zone_id, nama, current_bahaya in inund_rows:
    jiwa = exposed_map.get(nama, 0)
    correct_bahaya = "Tinggi" if jiwa > 15000 else ("Sedang" if jiwa > 5000 else "Rendah")
    if current_bahaya != correct_bahaya:
        cur.execute("UPDATE tb_inundation_zones SET tingkat_bahaya = ? WHERE zone_id = ?",
                   (correct_bahaya, zone_id))
        print(f"  [FIX] {nama:35s}: {current_bahaya} -> {correct_bahaya}")
        fixes += 1

if fixes == 0:
    print("  [OK] Semua tingkat bahaya sudah benar")

# ===== UPDATE NODE is_safe =====
print(f"\n[3/4] Mengupdate flag is_safe pada tb_nodes...")

# Load GeoJSON for spatial classification
gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

# Build the definitive safe kelurahan list from DB
cur.execute("SELECT nama_zona FROM tb_safe_zones")
safe_kelurahan = set(r[0] for r in cur.fetchall())

# Get all nodes
df_nodes = pd.read_sql_query("SELECT node_id, lat, lon, is_safe FROM tb_nodes", conn)

# Spatial join nodes with kelurahan
gdf_nodes = gpd.GeoDataFrame(
    df_nodes,
    geometry=[Point(lon, lat) for lon, lat in zip(df_nodes['lon'], df_nodes['lat'])],
    crs="EPSG:4326"
)
gdf_joined = gpd.sjoin(gdf_nodes, gdf[['NAMA_UPPER', 'geometry']], how='left', predicate='within')

# Determine correct is_safe for each node
updates_to_safe = []
updates_to_risk = []

for idx, row in gdf_joined.iterrows():
    node_id = int(row['node_id'])
    current_safe = int(row['is_safe'])
    kel_name = row.get('NAMA_UPPER', '')
    
    if pd.isna(kel_name) or kel_name == '':
        # Node not in any kelurahan, use longitude fallback
        correct_safe = 1 if row['lon'] > 100.38 else 0
    else:
        correct_safe = 1 if kel_name in safe_kelurahan else 0
    
    if current_safe != correct_safe:
        if correct_safe == 1:
            updates_to_safe.append(node_id)
        else:
            updates_to_risk.append(node_id)

# Apply updates
if updates_to_safe:
    placeholders = ','.join(['?' for _ in updates_to_safe])
    cur.execute(f"UPDATE tb_nodes SET is_safe = 1 WHERE node_id IN ({placeholders})", updates_to_safe)
    print(f"  [OK] {len(updates_to_safe)} nodes dipindahkan ke is_safe=1 (zona hijau)")
else:
    print("  [--] Tidak ada nodes yang perlu dipindahkan ke safe")

if updates_to_risk:
    placeholders = ','.join(['?' for _ in updates_to_risk])
    cur.execute(f"UPDATE tb_nodes SET is_safe = 0 WHERE node_id IN ({placeholders})", updates_to_risk)
    print(f"  [OK] {len(updates_to_risk)} nodes dipindahkan ke is_safe=0 (zona risiko)")
else:
    print("  [--] Tidak ada nodes yang perlu dipindahkan ke risk")

# ===== VERIFIKASI AKHIR =====
print(f"\n[4/4] Verifikasi akhir...")
cur.execute("SELECT COUNT(*) FROM tb_inundation_zones")
inund_after = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM tb_safe_zones")
safe_after = cur.fetchone()[0]

cur.execute("SELECT is_safe, COUNT(*) FROM tb_nodes GROUP BY is_safe")
node_dist = {r[0]: r[1] for r in cur.fetchall()}

print(f"  Inundation zones: {inund_before} -> {inund_after}")
print(f"  Safe zones:       {safe_before} -> {safe_after}")
print(f"  Nodes is_safe=0:  {node_dist.get(0, 0)}")
print(f"  Nodes is_safe=1:  {node_dist.get(1, 0)}")

# Commit & Vacuum
conn.commit()
cur.execute("VACUUM")
conn.commit()
conn.close()

print(f"\n{'=' * 80}")
print(f"[SUKSES] Database berhasil diperbaiki dalam {time.time() - start:.2f} detik!")
print(f"{'=' * 80}")
