import sqlite3
import re
import os

DB_PATH = "../ranah_siaga_v3.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Menghapus kolom yang tidak dipakai di tb_tea_routes...")
# SQLite >= 3.35.0 supports ALTER TABLE DROP COLUMN
try:
    cursor.execute("ALTER TABLE tb_tea_routes DROP COLUMN nearest_tea_nama")
    cursor.execute("ALTER TABLE tb_tea_routes DROP COLUMN nearest_tea_eta")
    cursor.execute("ALTER TABLE tb_tea_routes DROP COLUMN nearest_tea_dist_m")
    cursor.execute("ALTER TABLE tb_tea_routes DROP COLUMN alt_tea_nama")
    cursor.execute("ALTER TABLE tb_tea_routes DROP COLUMN alt_tea_eta")
except Exception as e:
    print(f"Peringatan DROP COLUMN: {e}")
    # Fallback to recreate table if older SQLite
    cursor.execute("CREATE TABLE tb_tea_routes_new AS SELECT origin_node_id, nearest_tea_id, alt_tea_id FROM tb_tea_routes")
    cursor.execute("DROP TABLE tb_tea_routes")
    cursor.execute("ALTER TABLE tb_tea_routes_new RENAME TO tb_tea_routes")


print("Membulatkan koordinat WKT ke 6 desimal dan menghapus Z...")

def process_wkt(wkt_str):
    if not wkt_str: return wkt_str
    # Hapus Z atau M (hanya butuh POLYGON/MULTIPOLYGON)
    wkt_str = wkt_str.replace(" Z", "").replace(" ZM", "").replace(" M", "")
    
    # Cari semua angka koordinat
    def round_match(match):
        num_str = match.group(0)
        try:
            return f"{float(num_str):.6f}".rstrip('0').rstrip('.')
        except:
            return num_str
            
    # Regex untuk float/int coordinate
    new_wkt = re.sub(r"-?\d+\.\d+", round_match, wkt_str)
    return new_wkt

tables = ["tb_inundation_zones", "tb_safe_zones"]
for tbl in tables:
    try:
        cursor.execute(f"SELECT rowid, geometry_wkt FROM {tbl}")
        rows = cursor.fetchall()
        updates = []
        for rowid, wkt in rows:
            new_wkt = process_wkt(wkt)
            updates.append((new_wkt, rowid))
            
        cursor.executemany(f"UPDATE {tbl} SET geometry_wkt = ? WHERE rowid = ?", updates)
        print(f"  {tbl} diproses ({len(updates)} baris).")
    except Exception as e:
        print(f"  Skip {tbl}: {e}")

conn.commit()

print("Menjalankan VACUUM untuk mengompres ukuran file...")
cursor.execute("VACUUM")
conn.close()

size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
print(f"Selesai! Ukuran DB akhir: {size_mb:.2f} MB")
