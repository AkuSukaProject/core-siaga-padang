"""
CONTOH RUTE EVAKUASI DARI DATABASE V4 (PETA FOLIUM)

Menggambar rute evakuasi yang akan ditampilkan aplikasi untuk satu posisi warga:
  - TES rekomendasi rank 1-3 (tb_routes)
  - TEA terdekat (tb_tea_routes + tb_tea_next) dan zona aman terdekat (tb_safe_routes_v2 + tb_safe_next_v2)
  - zona merah, radius 1 km (jangkauan 20 menit orang terlemah, saran BPBD), dan ruas jembatan >= 20 m di rute

Mode pemilihan:
  python analisis/contoh_rute_evakuasi.py                 -> TES acak, lalu warga acak yang rute utamanya ke TES itu
  python analisis/contoh_rute_evakuasi.py --tes "Hotel HW" -> TES tertentu (nama atau tes_id)
  python analisis/contoh_rute_evakuasi.py --node 123456    -> posisi warga tertentu (node zona merah)
  tambahkan --seed N agar hasil acak dapat diulang, --jumlah N untuk membuat beberapa peta, --buka untuk membuka browser.

Keluaran: analisis/output/contoh_rute_<node>.html
"""
import sys
import os
import argparse
import random
import sqlite3
import webbrowser

import folium
from shapely import wkt as shapely_wkt

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "hasil_build", "ranah_siaga_v4.db")
DIR_OUTPUT = os.path.join(ROOT, "analisis", "output")
# Radius jangkauan 20 menit untuk orang terlemah (FEMA 2 mph), dipakai BPBD (docs/aturan_evakuasi_bpbd.md bagian 4).
RADIUS_JANGKAUAN_M = 1000
WARNA_RANK = ["#16a34a", "#f59e0b", "#2563eb"]


def argumen():
    p = argparse.ArgumentParser(description="Gambar contoh rute evakuasi dari ranah_siaga_v4.db")
    p.add_argument("--tes", help="Nama atau tes_id TES tujuan (default: acak)")
    p.add_argument("--node", type=int, help="node_id posisi warga (harus di zona merah)")
    p.add_argument("--seed", type=int, help="Seed acak agar contoh dapat diulang")
    p.add_argument("--jumlah", type=int, default=1, help="Jumlah peta contoh yang dibuat")
    p.add_argument("--buka", action="store_true", help="Buka peta di browser setelah dibuat")
    return p.parse_args()


class Db:
    def __init__(self):
        if not os.path.exists(DB_PATH):
            sys.exit(f"[ERROR] {DB_PATH} tidak ditemukan. Jalankan build_db.py terlebih dahulu.")
        self.c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        self.koord = {n: (la, lo) for n, la, lo in self.c.execute("SELECT node_id, lat, lon FROM tb_nodes")}
        # Geometri ruas (ambil yang terpendek bila ada ruas ganda).
        self.ruas = {}
        for u, v, panjang, geom in self.c.execute("SELECT u, v, length, geometry FROM tb_edges"):
            kunci = (min(u, v), max(u, v))
            if kunci not in self.ruas or panjang < self.ruas[kunci][0]:
                self.ruas[kunci] = (panjang, geom)
        self.jembatan = {(min(u, v), max(u, v)) for u, v in self.c.execute(
            "SELECT u, v FROM tb_edges WHERE edge_id IN (SELECT edge_id FROM tb_bridge_edges)")}
        meta = dict(self.c.execute("SELECT kunci, nilai FROM tb_metadata"))
        self.kecepatan = float(meta["kecepatan_jalan_ms"])
        # Kolom ETA disimpan pada 1,2 m/s (kontrak DB aplikasi); dikonversi ke waktu riil orang terlemah.
        self.konversi_eta = float(meta.get("kecepatan_kolom_eta_ms", self.kecepatan)) / self.kecepatan
        self.fas = {r[0]: r for r in self.c.execute(
            "SELECT facility_id, jenis, nama, kelurahan, kapasitas, kapasitas_sumber, nearest_node_id, lat, lon "
            "FROM tb_fasilitas_info WHERE dipakai = 1")}

    def garis(self, path):
        """Koordinat (lat, lon) sepanjang path node, mengikuti lekuk jalan."""
        titik = [self.koord[path[0]]]
        for a, b in zip(path, path[1:]):
            _, geom = self.ruas[(min(a, b), max(a, b))]
            if geom and geom.startswith("LINESTRING"):
                seg = [(y, x) for x, y in shapely_wkt.loads(geom).coords]
                # Samakan arah segmen dengan arah perjalanan a -> b.
                la, lo = self.koord[a]
                if (seg[-1][0] - la) ** 2 + (seg[-1][1] - lo) ** 2 < (seg[0][0] - la) ** 2 + (seg[0][1] - lo) ** 2:
                    seg.reverse()
                titik.extend(seg[1:])
            else:
                titik.append(self.koord[b])
        return titik

    def panjang(self, path):
        return sum(self.ruas[(min(a, b), max(a, b))][0] for a, b in zip(path, path[1:]))

    def lewat_jembatan(self, path):
        return [(a, b) for a, b in zip(path, path[1:]) if (min(a, b), max(a, b)) in self.jembatan]

    def rantai(self, tabel, kolom_filter=None, nilai=None, awal=None):
        """Rangkai path dari tabel next-hop (tb_tea_next / tb_safe_next_v2) seperti di aplikasi."""
        if kolom_filter:
            nxt = dict(self.c.execute(f"SELECT node_id, next_node_id FROM {tabel} WHERE {kolom_filter} = ?", (nilai,)))
        else:
            nxt = dict(self.c.execute(f"SELECT node_id, next_node_id FROM {tabel}"))
        path = [awal]
        while path[-1] in nxt and len(path) < 20000:
            path.append(nxt[path[-1]])
        return path

    def tes_dari_nama(self, nama):
        for fid, jenis, nm, kel, kap, sumber, node, la, lo in self.fas.values():
            if jenis == "TES" and nm == nama:
                yield self.fas[fid]


def pilih_asal(db, args, rng):
    """Kembalikan (node_asal, nama_tes_tujuan_utama)."""
    if args.node:
        baris = db.c.execute("SELECT rank_1_tes FROM tb_routes WHERE origin_node_id = ?", (args.node,)).fetchone()
        if not baris:
            sys.exit(f"[ERROR] Node {args.node} tidak punya rute TES (bukan node zona merah atau tidak ada di DB).")
        return args.node, baris[0]

    if args.tes:
        cocok = [f for f in db.fas.values() if f[1] == "TES" and args.tes in (f[0], f[2])]
        if not cocok:
            sys.exit(f"[ERROR] TES '{args.tes}' tidak ditemukan di tb_fasilitas_info (dipakai = 1).")
        calon_tes = [cocok[0][2]]
    else:
        calon_tes = sorted({nama for (nama,) in db.c.execute("SELECT DISTINCT rank_1_tes FROM tb_routes")})
        rng.shuffle(calon_tes)

    for nama in calon_tes:
        asal = [n for (n,) in db.c.execute("SELECT origin_node_id FROM tb_routes WHERE rank_1_tes = ?", (nama,))]
        if asal:
            return rng.choice(asal), nama
    sys.exit(f"[ERROR] Tidak ada warga zona merah yang rute utamanya menuju '{calon_tes[0]}'. "
             f"TES ini mungkin hanya muncul sebagai rank 2/3.")


def buat_peta(db, node):
    rute = db.c.execute("SELECT * FROM tb_routes WHERE origin_node_id = ?", (node,)).fetchone()
    info = db.c.execute("SELECT kelurahan, d_pantai_m, indeks_bahaya FROM tb_node_info WHERE node_id = ?", (node,)).fetchone()
    asal = db.koord[node]
    peta = folium.Map(location=asal, zoom_start=15, tiles="CartoDB positron", control_scale=True)

    # Zona merah.
    lapis_zona = folium.FeatureGroup(name="Zona merah (landaan tsunami)")
    for nama, geom in db.c.execute("SELECT nama_zona, geometry_wkt FROM tb_inundation_zones"):
        folium.GeoJson(shapely_wkt.loads(geom).__geo_interface__, tooltip=f"Zona merah: {nama}",
                       style_function=lambda _: {"color": "#dc2626", "weight": 0.5, "fillColor": "#ef4444", "fillOpacity": 0.15}
                       ).add_to(lapis_zona)
    lapis_zona.add_to(peta)

    folium.Circle(asal, radius=RADIUS_JANGKAUAN_M, color="#64748b", weight=1, fill=False, dash_array="6 6",
                  tooltip="Radius 1 km: jangkauan 20 menit berjalan orang terlemah").add_to(peta)
    folium.Marker(asal, icon=folium.Icon(color="red", icon="user", prefix="fa"),
                  popup=folium.Popup(f"<b>Posisi warga</b><br>Node {node}<br>Kelurahan {info[0]}<br>"
                                     f"Jarak ke pantai: {info[1]:.0f} m<br>Indeks bahaya tsunami: {info[2]}", max_width=260)
                  ).add_to(peta)

    ringkas = []
    # TES rank 1-3.
    dipakai = set()
    for r in range(3):
        nama, path_str, eta = rute[1 + 3 * r], rute[2 + 3 * r], rute[3 + 3 * r]
        if nama is None:  # rank 2/3 boleh kosong
            continue
        eta *= db.konversi_eta
        path = [int(x) for x in path_str.split(",")]
        if (nama, path[-1]) in dipakai:
            continue
        dipakai.add((nama, path[-1]))
        tes = next(f for f in db.tes_dari_nama(nama) if f[6] == path[-1])
        jembatan = db.lewat_jembatan(path)
        lapis = folium.FeatureGroup(name=f"TES rank {r + 1}: {nama}")
        folium.PolyLine(db.garis(path) + [(tes[7], tes[8])], color=WARNA_RANK[r], weight=7 - 2 * r, opacity=0.85,
                        dash_array=None if r == 0 else "10 8",
                        tooltip=f"Rank {r + 1}: {nama} — {eta:.1f} menit, {db.panjang(path):,.0f} m").add_to(lapis)
        for a, b in jembatan:
            folium.PolyLine([db.koord[a], db.koord[b]], color="#7c3aed", weight=10, opacity=0.6,
                            tooltip="Jembatan >= 20 m (hanya dipakai bila tidak ada rute tanpa jembatan)").add_to(lapis)
        folium.Marker((tes[7], tes[8]), icon=folium.Icon(color=["green", "orange", "blue"][r], icon="building", prefix="fa"),
                      popup=folium.Popup(f"<b>{nama}</b> (TES rank {r + 1})<br>Kelurahan {tes[3]}<br>"
                                         f"Kapasitas: {tes[4]:,.0f} jiwa ({tes[5]})<br>ETA: {eta:.1f} menit", max_width=260)
                      ).add_to(lapis)
        lapis.add_to(peta)
        ringkas.append((f"TES rank {r + 1}", nama, eta, db.panjang(path), len(jembatan)))

    # TEA terdekat.
    tea_id = db.c.execute("SELECT nearest_tea_id FROM tb_tea_routes WHERE origin_node_id = ?", (node,)).fetchone()
    if tea_id:
        tea = db.fas[tea_id[0]]
        path = db.rantai("tb_tea_next", "tea_id", tea_id[0], node)
        if path[-1] == tea[6]:
            lapis = folium.FeatureGroup(name=f"TEA terdekat: {tea[2]}", show=False)
            folium.PolyLine(db.garis(path) + [(tea[7], tea[8])], color="#059669", weight=4, opacity=0.8, dash_array="2 8",
                            tooltip=f"TEA: {tea[2]} — {db.panjang(path):,.0f} m").add_to(lapis)
            folium.Marker((tea[7], tea[8]), icon=folium.Icon(color="darkgreen", icon="tree", prefix="fa"),
                          popup=f"<b>{tea[2]}</b> (TEA)<br>Kelurahan {tea[3]}").add_to(lapis)
            lapis.add_to(peta)
            ringkas.append(("TEA terdekat", tea[2], db.panjang(path) / db.kecepatan / 60, db.panjang(path), len(db.lewat_jembatan(path))))

    # Zona aman terdekat.
    aman = db.c.execute("SELECT safe_node_id, safe_zone_nama, safe_eta, kelompok FROM tb_safe_routes_v2 "
                        "WHERE origin_node_id = ?", (node,)).fetchone()
    if aman:
        path = db.rantai("tb_safe_next_v2", "kelompok", aman[3], awal=node)
        lapis = folium.FeatureGroup(name=f"Zona aman terdekat: {aman[1]}", show=False)
        folium.PolyLine(db.garis(path), color="#0f766e", weight=4, opacity=0.8, dash_array="1 6",
                        tooltip=f"{aman[1]} — {aman[2] * db.konversi_eta:.1f} menit").add_to(lapis)
        folium.Marker(db.koord[path[-1]], icon=folium.Icon(color="cadetblue", icon="flag", prefix="fa"),
                      popup=f"<b>{aman[1]}</b><br>Batas zona aman").add_to(lapis)
        lapis.add_to(peta)
        ringkas.append(("Zona aman", aman[1], aman[2] * db.konversi_eta, db.panjang(path), len(db.lewat_jembatan(path))))

    # Panel ringkasan.
    baris = "".join(f"<tr><td>{j}</td><td>{n}</td><td style='text-align:right'>{e:.1f}</td>"
                    f"<td style='text-align:right'>{p:,.0f}</td><td style='text-align:center'>{'ya' if b else '-'}</td></tr>"
                    for j, n, e, p, b in ringkas)
    panel = f"""
    <div style="position:fixed; top:12px; left:52px; z-index:9999; background:white; padding:10px 14px; border-radius:8px;
                box-shadow:0 2px 10px rgba(0,0,0,.25); font:12px sans-serif; max-width:460px;">
      <b>Contoh rute evakuasi — node {node} ({info[0]})</b><br>
      <span style="color:#555">Kecepatan 0,894 m/s · batas 20 menit · data ranah_siaga_v4.db</span>
      <table style="margin-top:6px; border-collapse:collapse; width:100%">
        <tr style="border-bottom:1px solid #ddd"><th align=left>Tujuan</th><th align=left>Nama</th><th>Menit</th><th>Meter</th><th>Jembatan</th></tr>
        {baris}
      </table>
    </div>"""
    peta.get_root().html.add_child(folium.Element(panel))
    folium.LayerControl(collapsed=False).add_to(peta)

    os.makedirs(DIR_OUTPUT, exist_ok=True)
    path_html = os.path.join(DIR_OUTPUT, f"contoh_rute_{node}.html")
    peta.save(path_html)
    return path_html, ringkas


def main():
    args = argumen()
    rng = random.Random(args.seed)
    db = Db()
    for _ in range(args.jumlah):
        node, nama = pilih_asal(db, args, rng)
        path_html, ringkas = buat_peta(db, node)
        print(f"\nNode {node} -> TES utama: {nama}")
        for j, n, e, p, b in ringkas:
            print(f"  {j:<14} {n[:42]:<42} {e:6.1f} menit {p:8,.0f} m" + ("  [lewat jembatan]" if b else ""))
        print(f"  Peta: {os.path.relpath(path_html, ROOT)}")
        if args.buka:
            webbrowser.open("file://" + os.path.abspath(path_html))


if __name__ == "__main__":
    main()
