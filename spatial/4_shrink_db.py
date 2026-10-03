"""
Langkah 4: pengecilan DB agar memenuhi NF-03 (<= 75 MB desimal).

1. Hapus kolom tb_tea_routes yang tidak dibaca aplikasi maupun backend (aplikasi hanya membaca
   origin_node_id, nearest_tea_id, alt_tea_id).
2. Tulis ulang poligon tb_inundation_zones dan tb_safe_zones sebagai WKT 2D dengan 7 desimal
   (± 1 cm). Nilai Z semuanya 0 dan tidak dipakai; sebelumnya hanya label " Z" yang dihapus
   sehingga tiap titik masih berisi tiga angka.
3. Pastikan status zona setiap simpul (di dalam / di luar poligon) tidak berubah akibat pembulatan.
4. VACUUM.

Pemakaian (dari folder spatial/):
  python 4_shrink_db.py [--db ../ranah_siaga_v3.db]
"""
import argparse
import os
import sqlite3
import sys

import shapely
from shapely import wkt as shapely_wkt

sys.stdout.reconfigure(encoding="utf-8")

# 7 desimal derajat ± 1 cm. Dengan 6 desimal (± 0,1 m) tiga simpul yang berjarak < 1 cm dari batas
# dua kelurahan berpindah kelurahan, dan satu tujuan kawasan aman berpindah ke kelurahan yang
# dikecualikan; 7 desimal tidak mengubah keanggotaan satu simpul pun.
DESIMAL_KOORDINAT = 7
BATAS_NF03_BYTE = 75_000_000
KOLOM_TEA_TIDAK_DIPAKAI = ["nearest_tea_nama", "nearest_tea_eta", "nearest_tea_dist_m", "alt_tea_nama", "alt_tea_eta"]
TABEL_POLIGON = {"tb_inundation_zones": "zone_id", "tb_safe_zones": "safe_zone_id"}

parser = argparse.ArgumentParser(description="Kecilkan DB rilis.")
parser.add_argument("--db", default="../ranah_siaga_v3.db", help="berkas SQLite yang diperbarui")
args = parser.parse_args()
if not os.path.exists(args.db):
    sys.exit(f"[ERROR] DB '{args.db}' tidak ditemukan.")

conn = sqlite3.connect(args.db)
cursor = conn.cursor()

print("[1/4] Menghapus kolom tb_tea_routes yang tidak dipakai...")
existing = {row[1] for row in cursor.execute("PRAGMA table_info(tb_tea_routes)")}
for column in KOLOM_TEA_TIDAK_DIPAKAI:
    if column in existing:
        cursor.execute(f"ALTER TABLE tb_tea_routes DROP COLUMN {column}")
print("      Kolom tersisa:", [row[1] for row in cursor.execute("PRAGMA table_info(tb_tea_routes)")])

nodes = cursor.execute("SELECT node_id, lat, lon FROM tb_nodes").fetchall()
node_points = shapely.points([lon for _, _, lon in nodes], [lat for _, lat, _ in nodes])


def membership(table):
    """Pasangan (indeks simpul, id poligon) untuk setiap simpul yang berada di dalam poligon."""
    id_column = TABEL_POLIGON[table]
    rows = cursor.execute(f"SELECT {id_column}, geometry_wkt FROM {table}").fetchall()
    tree = shapely.STRtree([shapely_wkt.loads(w) for _, w in rows])
    point_index, polygon_index = tree.query(node_points, predicate="within")
    return {(int(i), rows[j][0]) for i, j in zip(point_index, polygon_index)}


print(f"[2/4] Menulis ulang poligon zona sebagai WKT 2D {DESIMAL_KOORDINAT} desimal...")
before = {table: membership(table) for table in TABEL_POLIGON}
for table, id_column in TABEL_POLIGON.items():
    rows = cursor.execute(f"SELECT {id_column}, geometry_wkt FROM {table}").fetchall()
    updates = []
    for row_id, wkt_text in rows:
        geometry = shapely.force_2d(shapely_wkt.loads(wkt_text))
        updates.append((shapely.to_wkt(geometry, rounding_precision=DESIMAL_KOORDINAT, trim=True), row_id))
    cursor.executemany(f"UPDATE {table} SET geometry_wkt = ? WHERE {id_column} = ?", updates)
    print(f"      {table}: {len(updates)} poligon")

print("[3/4] Memeriksa status zona setiap simpul setelah pembulatan...")
for table in TABEL_POLIGON:
    after = membership(table)
    if after != before[table]:
        conn.rollback()
        sys.exit(f"[ERROR] {len(after ^ before[table])} keanggotaan simpul di {table} berubah; pembulatan dibatalkan.")
    print(f"      {table}: {len(after):,} simpul di dalam poligon, tidak ada yang berubah")
conn.commit()

print("[4/4] VACUUM...")
cursor.execute("VACUUM")
conn.close()

size = os.path.getsize(args.db)
status = "memenuhi" if size <= BATAS_NF03_BYTE else "BELUM memenuhi"
print(f"Selesai: {size:,} byte ({size / 1e6:.2f} MB desimal) -> {status} NF-03 (<= 75 MB)")
