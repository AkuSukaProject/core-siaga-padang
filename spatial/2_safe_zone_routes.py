"""
Langkah 2: rute ke kawasan aman terdekat (evakuasi horizontal keluar dari zona rendaman).

Tujuan rute adalah simpul `is_safe = 1` yang berada di kelurahan kawasan aman TANPA jiwa terpapar
menurut tabel KRB BPBD (`penduduk_kota_padang.csv`). Kelurahan yang dinyatakan aman lewat daftar
pengecualian manual `core.py` (misalnya Pasar Ambacang 3.508 jiwa terpapar, Kalumbuk 1.885) tidak
dipakai sebagai tujuan: tabel KRB masih mencatat warga terpapar di sana dan letaknya di dalam
kelurahan tidak diketahui, sehingga rute ke batasnya bisa berhenti di bagian yang terpapar.
Ambang ini dapat diubah dengan --ambang-jiwa-terpapar setelah ada konfirmasi BPBD.

Sejak `core.py` memetakan simpul ke kelurahan dengan benar, `is_safe = 1` sama dengan "berada di luar
semua poligon tb_inundation_zones". Skrip berhenti bila DB masukan masih memakai penanda lama yang
tidak cocok dengan poligon, karena rute dari DB seperti itu bisa berakhir di tengah zona rendaman.

Graf dibaca dari tb_edges di DB itu sendiri (bukan graphml), sehingga setiap langkah rute pasti
punya geometri ruas yang bisa digambar aplikasi.

Keluaran (pola sama dengan tb_tea_routes + tb_tea_next yang sudah dibaca aplikasi):
  tb_safe_routes(origin_node_id, safe_node_id, safe_zone_id, safe_eta)
      safe_eta dalam menit; 0 bila simpul asal sudah menjadi tujuan. safe_zone_id merujuk ke
      tb_safe_zones (nama_zona = kelurahan kawasan aman tempat simpul tujuan berada); disimpan
      sebagai angka, bukan teks nama, agar DB tetap <= 75 MB (NF-03).
  tb_safe_next(node_id, next_node_id)
      satu langkah berikutnya menuju kawasan aman terdekat untuk setiap simpul yang bukan tujuan.

Pemakaian (dari folder spatial/):
  python 2_safe_zone_routes.py [--db ../ranah_siaga_v3.db] [--ambang-jiwa-terpapar 0]
"""
import argparse
import os
import sqlite3
import sys
import time

import networkx as nx
import pandas as pd
import shapely
from shapely import wkt as shapely_wkt

sys.stdout.reconfigure(encoding="utf-8")

# Kecepatan berjalan kaki evakuasi 1,2 m/s (SOP BPBD Kota Padang / BNPB), sama dengan core.py.
KECEPATAN_JALAN_M_PER_MENIT = 1.2 * 60.0
# Batas panjang rantai saat verifikasi; rute terpanjang di Padang jauh di bawah angka ini.
BATAS_LANGKAH_VERIFIKASI = 10_000
# Tabel jiwa terpapar per kelurahan (KRB Tsunami BPBD Kota Padang), sumber yang sama dengan core.py.
BERKAS_PENDUDUK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "penduduk_kota_padang.csv")
# Ejaan kelurahan di tabel BPBD -> ejaan di batas_kelurahan_kota_padang.geojson (sama dengan core.py).
ALIAS_KELURAHAN = {
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
    'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX',
}

parser = argparse.ArgumentParser(description="Bangun tb_safe_routes dan tb_safe_next.")
parser.add_argument("--db", default="../ranah_siaga_v3.db", help="berkas SQLite yang diperbarui")
parser.add_argument(
    "--ambang-jiwa-terpapar", type=int, default=0,
    help="kelurahan kawasan aman dengan jiwa terpapar <= ambang ini boleh menjadi tujuan (bawaan 0)",
)
args = parser.parse_args()
if not os.path.exists(args.db):
    sys.exit(f"[ERROR] DB '{args.db}' tidak ditemukan.")

df_penduduk = pd.read_csv(BERKAS_PENDUDUK)
jiwa_terpapar = dict(zip(
    df_penduduk["DESA"].astype(str).str.upper().str.strip().map(lambda x: ALIAS_KELURAHAN.get(x, x)),
    df_penduduk["JUMLAH JIWA TERPAPAR (JIWA)"],
))

conn = sqlite3.connect(args.db)
cursor = conn.cursor()

print("[1/5] Membaca simpul dan ruas jalan dari DB...")
nodes = {int(n): (lat, lon, int(s)) for n, lat, lon, s in cursor.execute(
    "SELECT node_id, lat, lon, is_safe FROM tb_nodes")}
G = nx.Graph()
G.add_nodes_from(nodes)
for u, v, length in cursor.execute("SELECT u, v, length FROM tb_edges"):
    u, v, length = int(u), int(v), float(length)
    if u == v:
        continue
    # tb_edges bisa menyimpan lebih dari satu ruas untuk pasangan yang sama; aplikasi memilih yang
    # terpendek (ORDER BY length), jadi Dijkstra juga memakai yang terpendek.
    if not G.has_edge(u, v) or length < G[u][v]["length"]:
        G.add_edge(u, v, length=length)
print(f"      {G.number_of_nodes():,} simpul, {G.number_of_edges():,} pasangan ruas")

print("[2/5] Memeriksa kecocokan is_safe dengan poligon zona rendaman...")
inundation = [shapely_wkt.loads(w) for (w,) in cursor.execute(
    "SELECT geometry_wkt FROM tb_inundation_zones")]
inundation_tree = shapely.STRtree(inundation)
safe_ids = [n for n, (_, _, s) in nodes.items() if s == 1]
safe_points = shapely.points([nodes[n][1] for n in safe_ids], [nodes[n][0] for n in safe_ids])
hits = inundation_tree.query(safe_points, predicate="within")
mismatched = sorted({safe_ids[i] for i in hits[0]})
if mismatched:
    sys.exit(
        f"[ERROR] {len(mismatched):,} simpul is_safe = 1 berada di dalam poligon zona rendaman "
        f"(contoh: {mismatched[:5]}). DB ini masih memakai penanda lama; bangun ulang tb_nodes dengan "
        "core.py yang sudah diperbaiki sebelum membuat rute kawasan aman."
    )
print(f"      Cocok: {len(safe_ids):,} simpul aman, tidak ada yang di dalam poligon zona rendaman")

print("[3/5] Memilih simpul tujuan di kelurahan kawasan aman (tb_safe_zones)...")
safe_zone_rows = cursor.execute(
    "SELECT safe_zone_id, nama_zona, geometry_wkt FROM tb_safe_zones").fetchall()
safe_zone_tree = shapely.STRtree([shapely_wkt.loads(w) for _, _, w in safe_zone_rows])
zone_of_safe_node = {}
zone_id_of_safe_node = {}
point_index, zone_index = safe_zone_tree.query(safe_points, predicate="within")
for i, j in zip(point_index, zone_index):
    zone_of_safe_node.setdefault(safe_ids[i], safe_zone_rows[j][1])
    zone_id_of_safe_node.setdefault(safe_ids[i], safe_zone_rows[j][0])
# Simpul di luar semua poligon kawasan aman (di luar batas kota) tidak dipakai sebagai tujuan karena
# jiwa terpaparnya tidak diketahui.
target_ids = {
    n for n, zone in zone_of_safe_node.items()
    if jiwa_terpapar.get(zone, 0) <= args.ambang_jiwa_terpapar
}
excluded_zones = sorted(
    {zone for zone in zone_of_safe_node.values() if jiwa_terpapar.get(zone, 0) > args.ambang_jiwa_terpapar}
)
print(f"      {len(target_ids):,} dari {len(safe_ids):,} simpul aman menjadi tujuan "
      f"(ambang jiwa terpapar {args.ambang_jiwa_terpapar})")
print(f"      Kawasan aman yang tidak dipakai sebagai tujuan: "
      + ", ".join(f"{z} ({jiwa_terpapar.get(z, 0):,} jiwa)" for z in excluded_zones))
if not target_ids:
    sys.exit("[ERROR] Tidak ada simpul tujuan kawasan aman.")

print("[4/5] Dijkstra multisumber dari semua simpul tujuan...")
t0 = time.time()
distances, paths = nx.multi_source_dijkstra(G, sources=target_ids, weight="length")
print(f"      Selesai dalam {time.time() - t0:.2f} detik; {len(distances):,} simpul terjangkau")

routes_data = []
next_data = []
for node_id, path in paths.items():
    # path berawal di simpul aman (sumber) dan berakhir di node_id; bagi warga urutannya dibalik.
    safe_node_id = path[0]
    routes_data.append((
        node_id,
        safe_node_id,
        zone_id_of_safe_node[safe_node_id],
        round(distances[node_id] / KECEPATAN_JALAN_M_PER_MENIT, 3),
    ))
    if len(path) > 1:
        next_data.append((node_id, path[-2]))
unreachable = len(nodes) - len(routes_data)

print("[5/5] Menulis tb_safe_routes dan tb_safe_next...")
cursor.execute("DROP TABLE IF EXISTS tb_safe_routes")
cursor.execute("DROP TABLE IF EXISTS tb_safe_next")
cursor.execute("""
CREATE TABLE tb_safe_routes (
    origin_node_id INTEGER PRIMARY KEY,
    safe_node_id   INTEGER NOT NULL,
    safe_zone_id   INTEGER NOT NULL,
    safe_eta       REAL    NOT NULL
) WITHOUT ROWID
""")
cursor.execute("""
CREATE TABLE tb_safe_next (
    node_id      INTEGER PRIMARY KEY,
    next_node_id INTEGER NOT NULL
) WITHOUT ROWID
""")
cursor.executemany("INSERT INTO tb_safe_routes VALUES (?, ?, ?, ?)", routes_data)
cursor.executemany("INSERT INTO tb_safe_next VALUES (?, ?)", next_data)
conn.commit()

# Verifikasi: setiap rantai berakhir di simpul aman yang tercatat, tanpa putaran, dan panjangnya
# sama dengan jarak Dijkstra.
next_of = dict(next_data)
target_of = {r[0]: r[1] for r in routes_data}
worst_gap_m = 0.0
for origin in next_of:
    current, walked, steps = origin, 0.0, 0
    while current in next_of:
        following = next_of[current]
        walked += G[current][following]["length"]
        current = following
        steps += 1
        if steps > BATAS_LANGKAH_VERIFIKASI:
            sys.exit(f"[ERROR] Rantai dari simpul {origin} berputar")
    if current != target_of[origin] or current not in target_ids:
        sys.exit(f"[ERROR] Rantai dari simpul {origin} tidak berakhir di kawasan aman tercatat")
    worst_gap_m = max(worst_gap_m, abs(walked - distances[origin]))
conn.close()

risk_etas = sorted(r[3] for r in routes_data if nodes[r[0]][2] == 0)
print(f"      tb_safe_routes: {len(routes_data):,} baris; tb_safe_next: {len(next_data):,} baris")
print(f"      Simpul tanpa jalan ke kawasan aman: {unreachable:,}")
print(f"      Verifikasi rantai: semua berakhir di simpul tujuan, selisih panjang maks {worst_gap_m:.6f} m")
if risk_etas:
    within_20 = sum(1 for e in risk_etas if e <= 20.0) / len(risk_etas) * 100
    print(f"      Simpul berisiko: median {risk_etas[len(risk_etas) // 2]:.1f} menit ke kawasan aman, "
          f"maks {risk_etas[-1]:.1f} menit, {within_20:.1f}% dalam 20 menit")
