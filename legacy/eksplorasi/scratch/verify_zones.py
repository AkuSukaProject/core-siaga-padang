"""
Diagnosa lebih lanjut - cek apakah ada kelurahan yang:
1. Seharusnya ZONA HIJAU (aman) tapi masuk inundation_zones (merah/kuning/oranye)
2. Atau sebaliknya

Fokus pada kelurahan spesifik yang dari screenshot terlihat salah:
- BALAI GADANG: hardcoded safe, tapi terpapar=31 -> harusnya HIJAU ✓
- AIR MANIS: terpapar=3 -> saat ini KUNING, tapi ini pulau/bukit kecil -> debatable
- BUKIT GADO-GADO: terpapar=0 -> HIJAU ✓
- LUBUK BEGALUNG NAN XX: terpapar=0 -> HIJAU ✓

Yang perlu diperbaiki - kelurahan yang seharusnya RISIKO tapi warnanya salah:
Dari screenshot user di Android, terlihat beberapa polygon berwarna HIJAU padahal 
seharusnya berwarna risiko.

Coba cek: apakah BEROK NIPAH dan PASA GADANG sudah masuk ke inundation dengan benar?
"""
import sqlite3

conn = sqlite3.connect('ranah_siaga_v2.db')
cur = conn.cursor()

# Cek apakah BEROK NIPAH dan PASA GADANG ada di inundation
print("=== CEK KELURAHAN SPESIFIK ===")
for nama in ['BEROK NIPAH', 'PASA GADANG', 'BUKIT GADO-GADO', 'AIR MANIS', 'BALAI GADANG']:
    cur.execute("SELECT nama_zona, tingkat_bahaya FROM tb_inundation_zones WHERE nama_zona = ?", (nama,))
    r = cur.fetchone()
    if r:
        print(f"  {nama:30s} -> INUNDATION ({r[1]})")
    else:
        cur.execute("SELECT nama_zona, elevasi_m FROM tb_safe_zones WHERE nama_zona = ?", (nama,))
        r = cur.fetchone()
        if r:
            print(f"  {nama:30s} -> SAFE (elevasi {r[1]}m)")
        else:
            print(f"  {nama:30s} -> NOT FOUND IN EITHER TABLE!")

# Cek total
print(f"\n=== TOTAL ZONA ===")
cur.execute("SELECT COUNT(*) FROM tb_inundation_zones")
print(f"Inundation zones: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM tb_safe_zones")
print(f"Safe zones: {cur.fetchone()[0]}")

# Check if all kelurahan from GeoJSON are accounted for
cur.execute("SELECT nama_zona FROM tb_inundation_zones")
inund_names = set(r[0] for r in cur.fetchall())
cur.execute("SELECT nama_zona FROM tb_safe_zones")
safe_names = set(r[0] for r in cur.fetchall())

total = inund_names | safe_names
print(f"Total classified: {len(total)} (should be ~104 kelurahan)")

# Cek overlap
overlap = inund_names & safe_names
if overlap:
    print(f"\n[ERROR] OVERLAP: kelurahan ada di kedua tabel: {overlap}")

# Cek geometry validity
print("\n=== CEK GEOMETRY (sample) ===")
cur.execute("SELECT nama_zona, LENGTH(geometry_wkt) FROM tb_inundation_zones ORDER BY LENGTH(geometry_wkt) DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  INUND {r[0]:35s}: {r[1]:8d} chars")

cur.execute("SELECT nama_zona, LENGTH(geometry_wkt) FROM tb_safe_zones ORDER BY LENGTH(geometry_wkt) DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  SAFE  {r[0]:35s}: {r[1]:8d} chars")

conn.close()
