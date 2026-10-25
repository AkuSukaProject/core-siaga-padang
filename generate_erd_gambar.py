"""
Gambar ERD database Siaga Padang (hasil_build/ranah_siaga_v4.db), dibaca langsung dari DB.

Keluaran di docs/erd/:
  erd_siaga_padang_lengkap.svg / .png  semua kolom + keterangan singkat (lampiran, layar)
  erd_siaga_padang_ringkas.svg / .png  kunci dan kolom utama saja (Gambar 5.3 laporan)
  erd_siaga_padang.html                ERD interaktif + kamus data (semua kolom, % NULL, contoh nilai)

Jumlah baris dan kardinalitas tiap relasi dihitung dari isi DB, bukan ditulis tangan. Relasinya logis
(SQLite tidak memakai foreign key). Tanda "dibaca aplikasi" dicek dengan git grep di branch aplikasi.
PNG dibuat dengan Chrome/Edge headless (skala 2x).

Pemakaian: env\\Scripts\\python.exe generate_erd_gambar.py [--db <ranah_siaga_v4.db>] [--keluaran <folder>]
  Tanpa argumen: DB hasil build, keluaran docs/erd/. Untuk versi lain (mis. DB dari Release), beri path absolut.
"""
import argparse
import html
import json
import math
import os
import sqlite3
import subprocess
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

_arg = argparse.ArgumentParser()
_arg.add_argument("--db", default=os.path.join("hasil_build", "ranah_siaga_v4.db"))
_arg.add_argument("--keluaran", default=os.path.join("docs", "erd"))
_ARG = _arg.parse_args()
DB_PATH, OUT_DIR = _ARG.db, _ARG.keluaran
REPO_APLIKASI, BRANCH_APLIKASI = "C:/siagapadang", "origin/feat/final-keselamatan-navigasi"
BROWSER = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]

GRUP = {
    "graf": ("Graf jalan", "#475569"),
    "tes": ("Rute TES (vertikal)", "#c2410c"),
    "tea": ("Rute TEA (horizontal)", "#15803d"),
    "aman": ("Rute zona aman", "#0e7490"),
    "zona": ("Zona spasial", "#b91c1c"),
    "info": ("Penugasan dan info engine", "#6d28d9"),
}

# Susunan kolom gambar (kiri ke kanan), tiap kolom berisi tabel dari atas ke bawah.
TATA_LETAK = [
    ["tb_tes", "tb_routes", "v_fasilitas_evakuasi", "tb_fasilitas_info"],
    ["tb_tea", "tb_tea_routes", "tb_tea_next", "tb_route_shares"],
    ["tb_edges", "tb_bridge_edges", "tb_jalur_resmi", "tb_nodes", "tb_node_info"],
    ["tb_safe_routes_v2", "tb_safe_next_v2", "tb_safe_routes", "tb_safe_next"],
    ["tb_safe_zones", "tb_inundation_zones", "tb_kelurahan_info", "tb_metadata"],
]

# grup, peran singkat (gambar ringkas), uraian (gambar lengkap), kolom tambahan gambar ringkas, keterangan kolom.
TABEL = {
    "tb_nodes": dict(grup="graf", peran="Simpul jalan pejalan kaki (OSM)",
        uraian="Simpul graf jalan pejalan kaki OSM ({sumber_jalan}). is_safe sama persis dengan poligon zona merah: {merah} merah, {hijau} hijau.",
        ringkas=["lat", "lon", "is_safe", "jarak_pantai_m"],
        ket={"node_id": "ID simpul OSM (tetap antar-build)", "lat": "WGS 84", "lon": "WGS 84",
             "is_safe": "0 = zona merah, 1 = zona hijau", "jarak_pantai_m": "m ke garis pantai OSM (bulat)"}),
    "tb_edges": dict(grup="graf", peran="Ruas jalan (gambar rute)",
        uraian="Ruas jalan tak berarah untuk menggambar rute; {ruas_ganda} pasangan u-v punya lebih dari satu ruas (jalan sejajar).",
        ringkas=["length", "geometry"],
        ket={"edge_id": "nomor ruas (diberi ulang tiap build)", "u": "simpul ujung", "v": "simpul ujung",
             "length": "meter", "geometry": "WKT LineString (lon lat)"}),
    "tb_bridge_edges": dict(grup="graf", peran="Ruas berjembatan >= 20 m",
        uraian="Ruas yang memuat badan jembatan >= 20 m (OSM). Rute lewat jembatan hanya dipakai bila tidak ada pilihan lain.",
        ket={"edge_id": "ruas berjembatan"}),
    "tb_jalur_resmi": dict(grup="graf", peran="Ruas di jalur evakuasi resmi BPBD",
        uraian="Ruas graf yang berimpit dengan jalur evakuasi resmi BPBD (Jalur_evakuasi_Padang.shp); biayanya dikali {faktor_jalur}.",
        ket={"u": "simpul ujung", "v": "simpul ujung"}),
    "tb_node_info": dict(grup="info", peran="Atribut analitik per simpul",
        uraian="Atribut engine per simpul: kelurahan, bahaya, penduduk yang berangkat dari simpul, dan ketergantungan rute pada jembatan.",
        ringkas=["kelurahan", "demand_jiwa"],
        ket={"node_id": "1:1 dengan tb_nodes", "kelurahan": "nama kelurahan (104)", "d_pantai_m": "m ke pantai (presisi penuh)",
             "indeks_bahaya": "raster KRB; NULL di luar landaan", "demand_jiwa": "jiwa yang berangkat dari simpul",
             "rute_tes_lewat_jembatan": "1 = rute TES lewat jembatan", "rute_aman_lewat_jembatan": "1 = rute zona aman lewat jembatan",
             "kantong_aman": "1 = kantong hijau < 50 ha", "rute_tes_mendekat_pantai_m": "maks. mendekat pantai di rute TES",
             "rute_aman_mendekat_pantai_m": "maks. mendekat pantai di rute aman"}),
    "tb_tes": dict(grup="tes", peran="Tempat evakuasi sementara (gedung)",
        uraian="TES (evakuasi vertikal) yang dipakai routing: {tes_bpbd} sumber BPBD, {tes_warga} kesepakatan warga. Nama unik.",
        ringkas=["nama_tes", "kapasitas", "lantai"],
        ket={"tes_id": "TES_001 ...", "nama_tes": "unik; dirujuk rank_k_tes", "zona": "nama kelurahan",
             "kapasitas": "jiwa; NULL = tidak ada data", "lat": "WGS 84", "lon": "WGS 84", "sumber": "BPBD / WARGA",
             "jarak_pantai_m": "m ke garis pantai", "lantai": "jumlah lantai"}),
    "tb_routes": dict(grup="tes", peran="Hingga 3 TES per simpul zona merah",
        uraian="Hingga 3 TES per simpul zona merah, semuanya lolos syarat arah. Urutan: terjauh dari pantai yang sempat <= 20 menit, lalu tercepat. Rank 2/3 boleh NULL.",
        ringkas=["rank_1_tes", "rank_1_path", "rank_1_eta"],
        ket={"origin_node_id": "simpul zona merah", "rank_1_tes": "nama TES", "rank_1_path": "ID simpul dipisah koma",
             "rank_1_eta": "menit pada 1,2 m/s", "rank_2_tes": "boleh NULL", "rank_2_path": "", "rank_2_eta": "",
             "rank_3_tes": "boleh NULL", "rank_3_path": "", "rank_3_eta": ""}),
    "v_fasilitas_evakuasi": dict(grup="tes", peran="VIEW: gabungan TES + TEA",
        uraian="VIEW gabungan tb_tes (Vertikal) dan tb_tea (Horizontal) untuk daftar dan peta fasilitas.",
        ringkas=["facility_id", "nama", "jenis"],
        ket={"facility_id": "tes_id / tea_id", "kode": "tes_id / kode_tea", "nama": "nama_tes / nama_tea",
             "jenis": "'TES' / 'TEA'", "tipe_evakuasi": "'Vertikal' / 'Horizontal'", "zona_sektor": "zona / sektor",
             "kapasitas": "", "lat": "", "lon": "", "sumber": ""}),
    "tb_fasilitas_info": dict(grup="info", peran="Semua TES/TEA sumber + alasan",
        uraian="Semua TES/TEA sumber ({fas_total}), termasuk {fas_tidak} yang tidak dipakai beserta alasannya, sumber kapasitas, dan sumber koordinat.",
        ringkas=["jenis", "nama", "dipakai", "kapasitas"],
        ket={"facility_id": "= tes_id / tea_id", "jenis": "TES / TEA", "nama": "nama yang dipakai", "dipakai": "1 = dipakai routing",
             "alasan_tidak_dipakai": "NULL bila dipakai", "kapasitas": "jiwa, termasuk estimasi", "kapasitas_sumber": "BPBD 2025/2019 atau estimasi",
             "d_pantai_m": "m ke garis pantai", "indeks_bahaya": "raster KRB; NULL di luar landaan",
             "jumlah_lantai_2019": "verifikasi BPBD 2019", "status_bpbd_2019": "potensial / tidak", "nama_bpbd_2019": "",
             "kapasitas_2019": "", "luas_jejak_bangunan_m2": "dasar estimasi kapasitas", "nearest_node_id": "simpul tujuan",
             "snap_dist_m": "jarak ke simpul", "nama_bpbd": "nama asli shapefile", "sumber": "BPBD / WARGA",
             "nama_daftar_resmi_bpbd": "padanan Daftar Shelter OK", "lantai": "", "koordinat_sumber": "shapefile 2025 / geokode OSM",
             "kelurahan": "", "kecamatan": "", "lat": "", "lon": ""}),
    "tb_tea": dict(grup="tea", peran="Tempat evakuasi akhir (lapangan/bukit)",
        uraian="TEA (evakuasi horizontal) di luar zona merah. kapasitas 0 = tidak ada data; TEA tidak dibatasi kapasitas saat routing.",
        ringkas=["nama_tea", "kapasitas", "nearest_node_id"],
        ket={"tea_id": "TEA_001 ...", "kode_tea": "", "sektor": "kecamatan", "nama_tea": "unik", "kelurahan": "nama kelurahan",
             "kecamatan": "", "tipe_fasilitas": "'TEA'", "kapasitas": "0 = tidak ada data", "lat": "WGS 84", "lon": "WGS 84",
             "nearest_node_id": "simpul tujuan rute", "rute_evakuasi": "NULL (cadangan)", "jarak_pantai_m": "m ke garis pantai",
             "sumber": "BPBD / WARGA"}),
    "tb_tea_routes": dict(grup="tea", peran="TEA utama dan alternatif per simpul",
        uraian="TEA utama dan alternatif untuk setiap simpul ({tea_merah} merah, {tea_hijau} hijau); urutan sama dengan TES. alt = utama bila tidak ada TEA lain yang layak.",
        ket={"origin_node_id": "simpul asal", "nearest_tea_id": "TEA utama", "alt_tea_id": "TEA alternatif"}),
    "tb_tea_next": dict(grup="tea", peran="Next-hop menuju tiap TEA",
        uraian="Pohon next-hop per TEA: dari node_id lanjut ke next_node_id, diulang sampai nearest_node_id TEA.",
        ket={"tea_id": "pohon milik TEA", "node_id": "simpul sekarang", "next_node_id": "langkah berikutnya"}),
    "tb_route_shares": dict(grup="info", peran="Porsi penugasan per simpul",
        uraian="Porsi warga per simpul ke TES/TEA/zona aman (penugasan greedy berkapasitas). Jumlah porsi per simpul = 1.",
        ringkas=["jenis", "nama_tujuan", "porsi"],
        ket={"origin_node_id": "simpul asal", "jenis": "TES / TEA / ZONA_AMAN", "nama_tujuan": "nama TES/TEA, atau 'Zona Aman'",
             "porsi": "0-1"}),
    "tb_safe_routes_v2": dict(grup="aman", peran="Navigasi zona aman (K-B6)",
        uraian="Navigasi zona aman K-B6 untuk semua simpul merah: titik zona hijau terjauh dari pantai yang sempat <= 15 menit; bila tidak ada, batas zona hijau tercepat.",
        ringkas=["kelompok", "safe_node_id", "safe_eta"],
        ket={"origin_node_id": "simpul zona merah", "kelompok": "ID pohon tujuan", "safe_node_id": "titik tujuan di zona hijau",
             "safe_zone_nama": "'Zona Aman - <kelurahan>'", "safe_eta": "menit pada 1,2 m/s", "safe_d_pantai_m": "jarak pantai tujuan",
             "mendekat_pantai_maks_m": "maks. mendekat pantai di rute", "safe_zone_id": "NULL bila di luar poligon"}),
    "tb_safe_next_v2": dict(grup="aman", peran="Next-hop per titik tujuan v2",
        uraian="Pohon next-hop menuju titik tujuan v2, satu pohon per kelompok ({kelompok} kelompok).",
        ket={"kelompok": "pohon milik titik tujuan", "node_id": "simpul sekarang", "next_node_id": "langkah berikutnya"}),
    "tb_safe_routes": dict(grup="aman", peran="Batas zona hijau terdekat (kontrak lama)",
        uraian="Kontrak lama: batas zona hijau terdekat dari satu pohon global. safe_eta = 0 berarti sudah di zona hijau (status tiba). Simpul merah hanya yang tujuannya lolos syarat arah.",
        ringkas=["safe_node_id", "safe_eta"],
        ket={"origin_node_id": "semua simpul", "safe_node_id": "batas zona hijau", "safe_zone_nama": "'Zona Aman - <kelurahan>'",
             "safe_eta": "menit; 0 = di zona hijau", "safe_zone_id": "NULL bila di luar poligon"}),
    "tb_safe_next": dict(grup="aman", peran="Next-hop pohon global",
        uraian="Next-hop pohon global tb_safe_routes.",
        ket={"node_id": "simpul sekarang", "next_node_id": "langkah berikutnya"}),
    "tb_safe_zones": dict(grup="zona", peran="Poligon zona hijau per kelurahan",
        uraian="Poligon zona hijau per kelurahan: daratan di luar zona merah, tanpa celah dan tidak tumpang tindih.",
        ringkas=["nama_zona", "geometry_wkt"],
        ket={"safe_zone_id": "", "nama_zona": "nama kelurahan", "elevasi_m": "NULL (belum ada data)",
             "geometry_wkt": "MULTIPOLYGON lon lat, 7 desimal"}),
    "tb_inundation_zones": dict(grup="zona", peran="Poligon zona merah per kelurahan",
        uraian="Poligon zona merah per kelurahan: landaan KRB digabung zona rawan peta evakuasi BPBD, dipotong ke daratan ({luas_merah} ha).",
        ringkas=["nama_zona", "geometry_wkt"],
        ket={"zone_id": "", "nama_zona": "nama kelurahan", "tingkat_bahaya": "selalu 'Tinggi'",
             "geometry_wkt": "MULTIPOLYGON lon lat, 7 desimal"}),
    "tb_kelurahan_info": dict(grup="info", peran="Profil risiko tsunami kelurahan",
        uraian="Profil risiko tsunami {kel_info} kelurahan terpapar (tabel KRB 2023-2027) ditambah ringkasan hasil routing.",
        ringkas=["kelurahan", "jiwa_terpapar", "kelas_risiko"],
        ket={"kecamatan": "", "kelurahan": "unik; kunci nama", "luas_bahaya_rendah_ha": "ha", "luas_bahaya_sedang_ha": "ha",
             "luas_bahaya_tinggi_ha": "ha", "luas_bahaya_total_ha": "ha", "kelas_bahaya": "", "jiwa_terpapar": "jiwa (KRB)",
             "jiwa_umur_rentan": "", "jiwa_miskin": "", "jiwa_disabilitas": "", "kelas_penduduk_terpapar": "",
             "kerugian_total_juta_rp": "juta Rp", "kelas_kerentanan": "", "indeks_kesiapsiagaan": "", "kelas_kesiapsiagaan": "",
             "indeks_kapasitas": "", "kelas_kapasitas": "", "indeks_risiko": "", "kelas_risiko": "RENDAH / SEDANG / TINGGI",
             "node_zona_merah": "jumlah simpul merah", "jiwa_rute_aman_mendekat_pantai": "hasil routing",
             "jiwa_tanpa_rute_aman": "hasil routing", "jiwa_tambahan_peta_evakuasi": "di zona merah peta evakuasi"}),
    "tb_metadata": dict(grup="info", peran="Versi, sumber data, parameter",
        uraian="Pasangan kunci-nilai: versi, sumber data, dan parameter build ({meta} kunci).",
        ringkas=["kunci", "nilai"],
        ket={"kunci": "mis. versi, kecepatan_jalan_ms", "nilai": "teks"}),
}

# Relasi logis: (tabel asal, [kolom asal], tabel tujuan, kolom tujuan, jenis, syarat WHERE di tabel asal, label).
# jenis: id = kunci ID, nama = dicocokkan lewat nama, grup = kunci kelompok (bukan unik di kedua sisi), turunan = VIEW.
RELASI = [
    ("tb_edges", ["u", "v"], "tb_nodes", "node_id", "id", None, "u, v"),
    ("tb_bridge_edges", ["edge_id"], "tb_edges", "edge_id", "id", None, "edge_id"),
    ("tb_jalur_resmi", ["u", "v"], "tb_nodes", "node_id", "id", None, "u, v"),
    ("tb_node_info", ["node_id"], "tb_nodes", "node_id", "id", None, "node_id"),
    ("tb_routes", ["origin_node_id"], "tb_nodes", "node_id", "id", None, "origin_node_id"),
    ("tb_routes", ["rank_1_tes", "rank_2_tes", "rank_3_tes"], "tb_tes", "nama_tes", "nama", None, "rank_1..3_tes"),
    ("tb_tea", ["nearest_node_id"], "tb_nodes", "node_id", "id", None, "nearest_node_id"),
    ("tb_tea_routes", ["origin_node_id"], "tb_nodes", "node_id", "id", None, "origin_node_id"),
    ("tb_tea_routes", ["nearest_tea_id", "alt_tea_id"], "tb_tea", "tea_id", "id", None, "nearest / alt"),
    ("tb_tea_next", ["tea_id"], "tb_tea", "tea_id", "id", None, "tea_id"),
    ("tb_tea_next", ["node_id", "next_node_id"], "tb_nodes", "node_id", "id", None, "node_id, next_node_id"),
    ("tb_route_shares", ["origin_node_id"], "tb_nodes", "node_id", "id", None, "origin_node_id"),
    ("tb_route_shares", ["nama_tujuan"], "tb_tes", "nama_tes", "nama", "jenis = 'TES'", "nama_tujuan (jenis TES)"),
    ("tb_route_shares", ["nama_tujuan"], "tb_tea", "nama_tea", "nama", "jenis = 'TEA'", "nama_tujuan (jenis TEA)"),
    ("tb_safe_routes_v2", ["origin_node_id"], "tb_nodes", "node_id", "id", None, "origin_node_id"),
    ("tb_safe_routes_v2", ["safe_node_id"], "tb_nodes", "node_id", "id", None, "safe_node_id"),
    ("tb_safe_routes_v2", ["kelompok"], "tb_safe_next_v2", "kelompok", "grup", None, "kelompok"),
    ("tb_safe_routes_v2", ["safe_zone_id"], "tb_safe_zones", "safe_zone_id", "id", None, "safe_zone_id"),
    ("tb_safe_next_v2", ["node_id", "next_node_id"], "tb_nodes", "node_id", "id", None, "node_id, next_node_id"),
    ("tb_safe_routes", ["origin_node_id"], "tb_nodes", "node_id", "id", None, "origin_node_id"),
    ("tb_safe_routes", ["safe_node_id"], "tb_nodes", "node_id", "id", None, "safe_node_id"),
    ("tb_safe_routes", ["safe_zone_id"], "tb_safe_zones", "safe_zone_id", "id", None, "safe_zone_id"),
    ("tb_safe_next", ["node_id", "next_node_id"], "tb_nodes", "node_id", "id", None, "node_id, next_node_id"),
    ("tb_fasilitas_info", ["nearest_node_id"], "tb_nodes", "node_id", "id", None, "nearest_node_id"),
    ("tb_tes", ["tes_id"], "tb_fasilitas_info", "facility_id", "id", None, "tes_id = facility_id"),
    ("tb_tea", ["tea_id"], "tb_fasilitas_info", "facility_id", "id", None, "tea_id = facility_id"),
    ("tb_node_info", ["kelurahan"], "tb_kelurahan_info", "kelurahan", "nama", None, "kelurahan"),
    ("tb_inundation_zones", ["nama_zona"], "tb_kelurahan_info", "kelurahan", "nama", None, "nama_zona"),
    ("tb_safe_zones", ["nama_zona"], "tb_kelurahan_info", "kelurahan", "nama", None, "nama_zona"),
    ("v_fasilitas_evakuasi", ["facility_id"], "tb_tes", "tes_id", "turunan", "jenis = 'TES'", "UNION ALL (TES)"),
    ("v_fasilitas_evakuasi", ["facility_id"], "tb_tea", "tea_id", "turunan", "jenis = 'TEA'", "UNION ALL (TEA)"),
]


def ribu(n):
    return f"{n:,}".replace(",", ".")


# ---------------------------------------------------------------- isi DB
con = sqlite3.connect(DB_PATH)
q = lambda s, *a: con.execute(s, a).fetchall()
meta = dict(q("select kunci, nilai from tb_metadata"))
VERSI = meta["versi"]
objek = {n: t for n, t in q("select name, type from sqlite_master where type in ('table','view') and name not like 'sqlite_%'")}
tak_dikenal = set(objek) - set(TABEL)
assert not tak_dikenal, f"tabel belum dideskripsikan: {tak_dikenal}"
assert {t for kol in TATA_LETAK for t in kol} == set(TABEL)

KOLOM, BARIS = {}, {}
for t in TABEL:
    info = q(f'pragma table_info("{t}")')
    KOLOM[t] = [dict(nama=n, tipe=(tp or "-").upper(), nn=bool(nn), pk=pk) for _, n, tp, nn, _, pk in info]
    BARIS[t] = q(f'select count(*) from "{t}"')[0][0]
    for k in KOLOM[t]:
        assert k["nama"] in TABEL[t]["ket"], f"{t}.{k['nama']} belum punya keterangan"


def luas_ha(t):
    import geopandas as gpd
    from shapely import wkt
    g = gpd.GeoSeries([wkt.loads(w) for (w,) in q(f"select geometry_wkt from {t}")], crs=4326).to_crs(32747)
    return g.union_all().area / 1e4


stat = dict(
    sumber_jalan=("OSM per " + meta["sumber_jaringan_jalan"].split("data OSM per ")[-1][:10]
                  if "sumber_jaringan_jalan" in meta else "OSM"),
    merah=ribu(q("select count(*) from tb_nodes where is_safe = 0")[0][0]),
    hijau=ribu(q("select count(*) from tb_nodes where is_safe = 1")[0][0]),
    ruas_ganda=ribu(q("select count(*) from (select 1 from tb_edges group by min(u, v), max(u, v) having count(*) > 1)")[0][0]),
    faktor_jalur=meta.get("jalur_resmi_faktor", "?").replace(".", ","),
    tes_bpbd=q("select count(*) from tb_tes where sumber = 'BPBD'")[0][0],
    tes_warga=q("select count(*) from tb_tes where sumber = 'WARGA'")[0][0],
    fas_total=BARIS["tb_fasilitas_info"], fas_tidak=q("select count(*) from tb_fasilitas_info where dipakai = 0")[0][0],
    tea_merah=ribu(q("select count(*) from tb_tea_routes r join tb_nodes n on n.node_id = r.origin_node_id where n.is_safe = 0")[0][0]),
    tea_hijau=ribu(q("select count(*) from tb_tea_routes r join tb_nodes n on n.node_id = r.origin_node_id where n.is_safe = 1")[0][0]),
    kelompok=ribu(q("select count(distinct kelompok) from tb_safe_next_v2")[0][0]),
    kel_info=BARIS["tb_kelurahan_info"], meta=BARIS["tb_metadata"],
    luas_merah=ribu(round(luas_ha("tb_inundation_zones"))),
)
for t, d in TABEL.items():
    d["uraian"] = d["uraian"].format(**stat)


def nilai(t, kol, where=None):
    return [r[0] for r in q(f'select "{kol}" from "{t}"' + (f" where {where}" if where else ""))]


def kardinalitas(asal, kols, tujuan, kol_t, where):
    """(penanda di sisi asal, penanda di sisi tujuan). Sisi asal = banyak baris asal per baris tujuan; sisi tujuan = banyak
    baris tujuan per baris asal. Juga mengembalikan jumlah rujukan yang tidak ketemu (yatim)."""
    nilai_t = Counter(nilai(tujuan, kol_t))
    rujukan = Counter()
    ada_null = yatim = 0
    for kol in kols:
        for v in nilai(asal, kol, where):
            if v is None:
                ada_null += 1
            elif v in nilai_t:
                rujukan[v] += 1
            else:
                yatim += 1
    sisi_t = ("0" if ada_null or yatim else "1") + ("N" if any(nilai_t[v] > 1 for v in rujukan) else "1")
    sisi_a = ("0" if len(rujukan) < len(nilai_t) else "1") + ("N" if any(n > 1 for n in rujukan.values()) else "1")
    return sisi_a, sisi_t, yatim


REL = []
for asal, kols, tujuan, kol_t, jenis, where, label in RELASI:
    sa, st, yatim = kardinalitas(asal, kols, tujuan, kol_t, where)
    if jenis == "id":
        assert yatim == 0, f"{asal}.{kols} -> {tujuan}.{kol_t}: {yatim} rujukan yatim"
    REL.append(dict(asal=asal, kols=kols, tujuan=tujuan, kol_t=kol_t, jenis=jenis, where=where, label=label,
                    sa=sa, st=st, yatim=yatim))

FK = {(r["asal"], k) for r in REL if r["jenis"] != "turunan" for k in r["kols"]}
TARGET = {(r["tujuan"], r["kol_t"]) for r in REL}
UK = {(t, k) for t, k in TARGET if not any(c["nama"] == k and c["pk"] for c in KOLOM[t])
      and q(f'select count(*) = count(distinct "{k}") from "{t}"')[0][0]}


def dibaca_aplikasi():
    hasil = {}
    for t in TABEL:
        r = subprocess.run(["git", "-C", REPO_APLIKASI, "grep", "-l", "-w", t, BRANCH_APLIKASI, "--", "android/app/src/main"],
                           capture_output=True, text=True)
        hasil[t] = bool(r.stdout.strip())
    commit = subprocess.run(["git", "-C", REPO_APLIKASI, "log", "-1", "--format=%h %cs", BRANCH_APLIKASI],
                            capture_output=True, text=True).stdout.strip()
    return hasil, commit


APLIKASI, COMMIT_APLIKASI = dibaca_aplikasi()
assert any(APLIKASI.values()), "branch aplikasi tidak terbaca"


# ---------------------------------------------------------------- gambar SVG
MONO = "Consolas, 'Cascadia Mono', Menlo, 'DejaVu Sans Mono', monospace"
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
LEBAR_HURUF = 0.61  # lebar satu huruf monospace / ukuran huruf (Consolas 0,55; Menlo 0,60), diberi kelonggaran


def lebar(teks, ukuran):
    return len(teks) * ukuran * LEBAR_HURUF


def bungkus(teks, maks):
    baris, kini = [], ""
    for kata in teks.split():
        if kini and len(kini) + 1 + len(kata) > maks:
            baris.append(kini)
            kini = kata
        else:
            kini = f"{kini} {kata}".strip()
    return baris + ([kini] if kini else [])


def e(s):
    return html.escape(str(s), quote=True)


def campur(hex_warna, t):
    """Campur warna dengan putih (t = 0 warna asli, 1 putih)."""
    r, g, b = (int(hex_warna[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(c + (255 - c) * t) for c in (r, g, b))


def gambar(mode):
    lengkap = mode == "lengkap"
    UK_NAMA, UK_TIPE, UK_KET = (12.5, 10.5, 10.5) if lengkap else (14, 11.5, 0)
    TINGGI_BARIS = 19 if lengkap else 21
    TINGGI_KEPALA = 30 if lengkap else 32
    UK_URAIAN, TINGGI_URAIAN = 10.5, 14
    JARAK_KOLOM, JARAK_TABEL, TEPI = (120, 30, 40) if lengkap else (120, 36, 40)

    kotak = {}
    for t, d in TABEL.items():
        kolom = KOLOM[t]
        tampil = kolom if lengkap else [k for k in kolom if k["pk"] or (t, k["nama"]) in FK | TARGET or k["nama"] in d.get("ringkas", [])]
        sembunyi = len(kolom) - len(tampil)
        lebar_nama = max(lebar(k["nama"], UK_NAMA) for k in tampil)
        lebar_tipe = max(lebar(k["tipe"] + (" NN" if k["nn"] and not k["pk"] else ""), UK_TIPE) for k in tampil)
        lebar_ket = max([lebar(d["ket"].get(k["nama"], ""), UK_KET) for k in tampil] + [0]) if lengkap else 0
        x_nama = 40
        x_tipe = x_nama + lebar_nama + 12
        x_ket = x_tipe + lebar_tipe + 14
        w = max(x_ket + lebar_ket + 10 if lengkap else x_tipe + lebar_tipe + 12,
                lebar(t, 14) + 46 + lebar(ribu(BARIS[t]) + " baris", 10.5) + (34 if APLIKASI[t] else 0),
                250 if lengkap else 0)
        uraian = bungkus(d["uraian"] if lengkap else d["peran"], max(28, int((w - 20) / (UK_URAIAN * LEBAR_HURUF * 0.92))))
        h = TINGGI_KEPALA + len(uraian) * TINGGI_URAIAN + 8 + TINGGI_BARIS * (len(tampil) + (1 if sembunyi else 0)) + 4
        kotak[t] = dict(w=w, h=h, tampil=tampil, sembunyi=sembunyi, uraian=uraian, x_nama=x_nama, x_tipe=x_tipe, x_ket=x_ket)

    # Posisi: kolom kiri ke kanan; tiap kolom ditengahkan vertikal terhadap kolom tertinggi.
    Y0 = 118 if lengkap else 110
    tinggi_kolom = [sum(kotak[t]["h"] for t in kol) + JARAK_TABEL * (len(kol) - 1) for kol in TATA_LETAK]
    H_ISI = max(tinggi_kolom)
    x = TEPI + 70  # ruang untuk garis lengkung relasi sesama kolom pertama
    for i, kol in enumerate(TATA_LETAK):
        wk = max(kotak[t]["w"] for t in kol)
        y = Y0 + (H_ISI - tinggi_kolom[i]) / 2 if i != 2 else Y0 + (H_ISI - tinggi_kolom[i]) / 2
        for t in kol:
            b = kotak[t]
            b.update(x=x + (wk - b["w"]) / 2, y=y, kol=i)
            y += b["h"] + JARAK_TABEL
        x += wk + JARAK_KOLOM
    W = x - JARAK_KOLOM + TEPI

    def y_kolom(t, nama):
        b = kotak[t]
        for i, k in enumerate(b["tampil"]):
            if k["nama"] == nama:
                return b["y"] + TINGGI_KEPALA + len(b["uraian"]) * TINGGI_URAIAN + 8 + TINGGI_BARIS * (i + 0.5)
        raise KeyError(f"{t}.{nama}")

    # Legenda di bawah isi.
    Y_LEG = Y0 + H_ISI + 34
    H = Y_LEG + 150
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" '
           f'font-family="{e(SANS)}" class="erd">',
           "<defs><style>.erd .mono{font-family:%s}.erd .rel path.g{fill:none;stroke-width:1.6}.erd .rel .m{fill:none;stroke-width:1.6}"
           ".erd .rel .mo{fill:#fff;stroke-width:1.5}</style></defs>" % MONO.replace("'", "&apos;"),
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']

    jumlah_kolom = sum(len(KOLOM[t]) for t in TABEL)
    n_tabel = sum(1 for t in objek.values() if t == "table")
    n_view = sum(1 for t in objek.values() if t == "view")
    judul = "Entity Relationship Diagram: Basis Data Lokal Siaga Padang" + ("" if lengkap else " (ringkas)")
    sub = (f"ranah_siaga_v4.db versi {VERSI} | {n_tabel} tabel + {n_view} view, {jumlah_kolom} kolom | "
           f"{ribu(BARIS['tb_nodes'])} simpul, {ribu(BARIS['tb_edges'])} ruas, {BARIS['tb_tes']} TES, {BARIS['tb_tea']} TEA, "
           f"{BARIS['tb_inundation_zones']} poligon zona merah")
    out.append(f'<text x="{TEPI}" y="48" font-size="26" font-weight="700" fill="#0f172a">{e(judul)}</text>')
    out.append(f'<text x="{TEPI}" y="76" font-size="14.5" fill="#334155">{e(sub)}</text>')
    if not lengkap:
        out.append(f'<text x="{TEPI}" y="96" font-size="12.5" fill="#64748b">Hanya kolom kunci dan kolom utama yang ditampilkan; '
                   f'daftar kolom lengkap ada di ERD lengkap dan kamus data.</text>')
    else:
        out.append(f'<text x="{TEPI}" y="96" font-size="12.5" fill="#64748b">Relasi adalah keterkaitan logis yang dipakai aplikasi '
                   f'(SQLite tanpa foreign key). Jumlah baris dan kardinalitas dihitung dari isi DB.</text>')

    # Relasi digambar lebih dulu supaya berada di bawah kotak.
    rel_svg = []
    for idx, r in enumerate(REL):
        a, b = kotak[r["asal"]], kotak[r["tujuan"]]
        ya, yb = y_kolom(r["asal"], r["kols"][0]), y_kolom(r["tujuan"], r["kol_t"])
        if a["kol"] == b["kol"]:
            sisi = -1 if a["kol"] == 0 else 1
            xa = a["x"] + (a["w"] if sisi > 0 else 0)
            xb = b["x"] + (b["w"] if sisi > 0 else 0)
            da = db = sisi
            off_a = off_b = 46 + abs(yb - ya) * 0.06
            if sisi > 0:
                tepi = max(xa, xb)
                off_a, off_b = tepi - xa + off_a, tepi - xb + off_b
            else:
                tepi = min(xa, xb)
                off_a, off_b = xa - tepi + off_a, xb - tepi + off_b
        else:
            ke_kanan = b["kol"] > a["kol"]
            xa = a["x"] + (a["w"] if ke_kanan else 0)
            xb = b["x"] + (0 if ke_kanan else b["w"])
            da, db = (1, -1) if ke_kanan else (-1, 1)
            off_a = off_b = max(55, abs(xb - xa) * 0.42)
        warna = GRUP[TABEL[r["asal"]]["grup"]][1]
        garis = {"id": "", "nama": ' stroke-dasharray="7 4"', "grup": ' stroke-dasharray="10 3 2 3"', "turunan": ' stroke-dasharray="2 3"'}[r["jenis"]]
        lebar_garis = 1.6 if r["jenis"] != "turunan" else 1.3
        p = (f"M{xa:.1f},{ya:.1f} C{xa + da * off_a:.1f},{ya:.1f} {xb + db * off_b:.1f},{yb:.1f} {xb:.1f},{yb:.1f}")
        g = [f'<g class="rel" data-a="{r["asal"]}" data-b="{r["tujuan"]}" stroke="{warna}">',
             f'<title>{e(r["asal"])}.{e(", ".join(r["kols"]))} -> {e(r["tujuan"])}.{e(r["kol_t"])}</title>',
             f'<path class="g" d="{p}" stroke-opacity="0.78" stroke-width="{lebar_garis}"{garis}/>']
        if r["jenis"] != "turunan":
            g.append(penanda(xa, ya, da, r["sa"], warna))
            g.append(penanda(xb, yb, db, r["st"], warna))
        else:
            # panah sederhana di ujung tabel sumber VIEW
            g.append(f'<path class="m" d="M{xb + db * 9:.1f},{yb - 4.5:.1f} L{xb:.1f},{yb:.1f} L{xb + db * 9:.1f},{yb + 4.5:.1f}"/>')
        g.append("</g>")
        rel_svg.append("".join(g))
    out.append('<g class="lapis-relasi">' + "".join(rel_svg) + "</g>")

    for t, d in TABEL.items():
        b = kotak[t]
        warna = GRUP[d["grup"]][1]
        x0, y0, w = b["x"], b["y"], b["w"]
        g = [f'<g class="tbl" data-t="{t}">',
             f'<rect x="{x0 + 2:.1f}" y="{y0 + 3:.1f}" width="{w:.1f}" height="{b["h"]:.1f}" rx="7" fill="#0f172a" fill-opacity="0.07"/>',
             f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{b["h"]:.1f}" rx="7" fill="#ffffff" stroke="{warna}" stroke-width="1.4"'
             + (' stroke-dasharray="5 3"' if objek[t] == "view" else "") + "/>",
             f'<path d="M{x0:.1f},{y0 + TINGGI_KEPALA:.1f} V{y0 + 7:.1f} a7,7 0 0 1 7,-7 H{x0 + w - 7:.1f} a7,7 0 0 1 7,7 V{y0 + TINGGI_KEPALA:.1f} Z" fill="{warna}"/>',
             f'<text class="mono" x="{x0 + 12:.1f}" y="{y0 + TINGGI_KEPALA / 2 + 5:.1f}" font-size="14" font-weight="700" fill="#ffffff">{e(t)}</text>',
             f'<text x="{x0 + w - 10:.1f}" y="{y0 + TINGGI_KEPALA / 2 + 4:.1f}" font-size="10.5" fill="#ffffff" fill-opacity="0.92" text-anchor="end">'
             f'{ribu(BARIS[t])} baris</text>']
        if APLIKASI[t]:
            xa = x0 + w - 10 - lebar(ribu(BARIS[t]) + " baris", 10.5) * 0.92 - 30
            g.append(f'<rect x="{xa:.1f}" y="{y0 + TINGGI_KEPALA / 2 - 7:.1f}" width="26" height="14" rx="3" fill="#ffffff" fill-opacity="0.95"/>'
                     f'<text x="{xa + 13:.1f}" y="{y0 + TINGGI_KEPALA / 2 + 3.5:.1f}" font-size="9" font-weight="700" fill="{warna}" text-anchor="middle">APP</text>')
        yu = y0 + TINGGI_KEPALA
        g.append(f'<rect x="{x0 + 0.7:.1f}" y="{yu:.1f}" width="{w - 1.4:.1f}" height="{len(b["uraian"]) * TINGGI_URAIAN + 7:.1f}" fill="{campur(warna, 0.9)}"/>')
        for i, s in enumerate(b["uraian"]):
            g.append(f'<text x="{x0 + 10:.1f}" y="{yu + 12 + i * TINGGI_URAIAN:.1f}" font-size="{UK_URAIAN}" fill="#1e293b">{e(s)}</text>')
        yr = yu + len(b["uraian"]) * TINGGI_URAIAN + 8
        for i, k in enumerate(b["tampil"] + ([None] if b["sembunyi"] else [])):
            yb = yr + i * TINGGI_BARIS
            if i % 2 == 1:
                g.append(f'<rect x="{x0 + 0.7:.1f}" y="{yb:.1f}" width="{w - 1.4:.1f}" height="{TINGGI_BARIS}" fill="#f8fafc"/>')
            ty = yb + TINGGI_BARIS / 2 + 4.3
            if k is None:
                g.append(f'<text x="{x0 + b["x_nama"]:.1f}" y="{ty:.1f}" font-size="{UK_TIPE}" font-style="italic" fill="#64748b">'
                         f'... +{b["sembunyi"]} kolom lain</text>')
                continue
            kunci = []
            if k["pk"]:
                kunci.append(("PK", "#a16207", "#fef3c7"))
            if (t, k["nama"]) in FK:
                kunci.append(("FK", "#1d4ed8", "#dbeafe"))
            if (t, k["nama"]) in UK:
                kunci.append(("UK", "#7e22ce", "#f3e8ff"))
            for j, (lbl, fg, bg) in enumerate(kunci[:2]):
                bx = x0 + 6 + j * 16 if len(kunci) > 1 else x0 + 9
                lw = 15 if len(kunci) > 1 else 22
                g.append(f'<rect x="{bx:.1f}" y="{yb + 3.5:.1f}" width="{lw}" height="{TINGGI_BARIS - 7}" rx="2.5" fill="{bg}"/>'
                         f'<text x="{bx + lw / 2:.1f}" y="{ty - 0.6:.1f}" font-size="{8 if len(kunci) > 1 else 9}" font-weight="700" fill="{fg}" text-anchor="middle">{lbl}</text>')
            tebal = ' font-weight="700"' if k["pk"] else ""
            g.append(f'<text class="mono" x="{x0 + b["x_nama"]:.1f}" y="{ty:.1f}" font-size="{UK_NAMA}"{tebal} fill="#0f172a">{e(k["nama"])}</text>')
            tipe = k["tipe"] + (" NN" if k["nn"] and not k["pk"] else "")
            g.append(f'<text class="mono" x="{x0 + b["x_tipe"]:.1f}" y="{ty:.1f}" font-size="{UK_TIPE}" fill="#64748b">{e(tipe)}</text>')
            if lengkap and d["ket"].get(k["nama"]):
                g.append(f'<text x="{x0 + b["x_ket"]:.1f}" y="{ty:.1f}" font-size="{UK_KET}" fill="#475569" font-style="italic">{e(d["ket"][k["nama"]])}</text>')
        g.append("</g>")
        out.append("".join(g))

    out.append(legenda(TEPI, Y_LEG, W))
    out.append(f'<text x="{W - TEPI:.0f}" y="{H - 14:.0f}" font-size="11" fill="#94a3b8" text-anchor="end">'
               f'Dibangkitkan oleh generate_erd_gambar.py dari ranah_siaga_v4.db versi {e(VERSI)}; '
               f'APP = dibaca aplikasi Android (branch feat/final-keselamatan-navigasi, commit {e(COMMIT_APLIKASI)}).</text>')
    out.append("</svg>")
    return "\n".join(out), W, H


def penanda(x, y, d, kode, warna):
    """Notasi crow's foot di ujung garis. kode: '01' nol atau satu, '11' tepat satu, '0N' nol atau banyak, '1N' satu atau banyak."""
    minimal, maks = kode
    s = []
    if maks == "N":
        s.append(f'<path class="m" d="M{x + d * 13:.1f},{y:.1f} L{x:.1f},{y - 6.5:.1f} M{x + d * 13:.1f},{y:.1f} L{x:.1f},{y + 6.5:.1f} '
                 f'M{x + d * 13:.1f},{y:.1f} L{x:.1f},{y:.1f}"/>')
    else:
        s.append(f'<path class="m" d="M{x + d * 8:.1f},{y - 6:.1f} V{y + 6:.1f}"/>')
    if minimal == "0":
        s.append(f'<circle class="mo" cx="{x + d * 20:.1f}" cy="{y:.1f}" r="4.2"/>')
    else:
        s.append(f'<path class="m" d="M{x + d * 18:.1f},{y - 6:.1f} V{y + 6:.1f}"/>')
    return "".join(s)


def legenda(x, y, W):
    s = [f'<g class="legenda"><rect x="{x}" y="{y}" width="{W - 2 * x:.0f}" height="112" rx="8" fill="#f8fafc" stroke="#e2e8f0"/>']
    cx, cy = x + 18, y + 26
    s.append(f'<text x="{cx}" y="{cy}" font-size="12.5" font-weight="700" fill="#0f172a">Kelompok tabel</text>')
    for i, (_, (nama, warna)) in enumerate(GRUP.items()):
        xx, yy = cx + (i % 2) * 190, cy + 20 + (i // 2) * 21
        s.append(f'<rect x="{xx}" y="{yy - 10}" width="14" height="14" rx="3" fill="{warna}"/>'
                 f'<text x="{xx + 21}" y="{yy + 1.5}" font-size="12" fill="#334155">{e(nama)}</text>')
    cx += 420
    s.append(f'<text x="{cx}" y="{cy}" font-size="12.5" font-weight="700" fill="#0f172a">Garis relasi (logis)</text>')
    jenis = [("", "kunci ID"), ("7 4", "dicocokkan lewat nama"), ("10 3 2 3", "kunci kelompok (bukan unik)"), ("2 3", "sumber VIEW (UNION ALL)")]
    for i, (dash, nama) in enumerate(jenis):
        yy = cy + 20 + i * 18
        s.append(f'<path d="M{cx},{yy - 4} h46" stroke="#475569" stroke-width="1.6"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>"
                 f'<text x="{cx + 56}" y="{yy}" font-size="12" fill="#334155">{e(nama)}</text>')
    cx += 300
    s.append(f'<text x="{cx}" y="{cy}" font-size="12.5" font-weight="700" fill="#0f172a">Kardinalitas (crow\'s foot)</text>')
    for i, (kode, nama) in enumerate([("11", "tepat satu"), ("01", "nol atau satu"), ("1N", "satu atau banyak"), ("0N", "nol atau banyak")]):
        xx, yy = cx + (i % 2) * 170, cy + 24 + (i // 2) * 26
        s.append(f'<g class="rel" stroke="#475569"><path class="g" d="M{xx},{yy} h40"/>{penanda(xx, yy, 1, kode, "#475569")}</g>'
                 f'<text x="{xx + 50}" y="{yy + 4}" font-size="12" fill="#334155">{e(nama)}</text>')
    cx += 370
    s.append(f'<text x="{cx}" y="{cy}" font-size="12.5" font-weight="700" fill="#0f172a">Tanda kolom</text>')
    tanda = [("PK", "#a16207", "#fef3c7", "primary key"), ("FK", "#1d4ed8", "#dbeafe", "merujuk tabel lain (logis)"),
             ("UK", "#7e22ce", "#f3e8ff", "unik, target rujukan nama"), ("NN", "#64748b", "#ffffff", "NOT NULL"),
             ("APP", "#475569", "#e2e8f0", "tabel dibaca aplikasi Android")]
    for i, (lbl, fg, bg, nama) in enumerate(tanda):
        xx, yy = cx + (i % 2) * 230, cy + 20 + (i // 2) * 21
        s.append(f'<rect x="{xx}" y="{yy - 10}" width="26" height="14" rx="3" fill="{bg}" stroke="#cbd5e1" stroke-width="0.6"/>'
                 f'<text x="{xx + 13}" y="{yy + 0.5}" font-size="9" font-weight="700" fill="{fg}" text-anchor="middle">{lbl}</text>'
                 f'<text x="{xx + 34}" y="{yy + 1.5}" font-size="12" fill="#334155">{e(nama)}</text>')
    s.append("</g>")
    return "".join(s)


def ke_png(svg_path, png_path, W, H):
    browser = next((b for b in BROWSER if os.path.exists(b)), None)
    if not browser:
        print("  [lewati PNG] Chrome/Edge tidak ditemukan")
        return
    wadah = os.path.abspath(svg_path) + ".html"
    with open(wadah, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html><body style='margin:0;background:#fff'>"
                f"<img src='{os.path.basename(svg_path)}' width='{W:.0f}' height='{H:.0f}'></body></html>")
    try:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size={W:.0f},{H:.0f}", f"--screenshot={os.path.abspath(png_path)}",
                        "file:///" + wadah.replace(os.sep, "/")], check=True, capture_output=True, timeout=120)
    finally:
        os.remove(wadah)


def kamus_data():
    """Profil tiap kolom untuk kamus data HTML: % NULL, jumlah nilai berbeda, rentang/contoh."""
    hasil = {}
    for t in TABEL:
        n = BARIS[t]
        baris = []
        for k in KOLOM[t]:
            c = k["nama"]
            nul, beda = q(f'select sum("{c}" is null), count(distinct "{c}") from "{t}"')[0]
            if k["tipe"] in ("INTEGER", "REAL"):
                lo, hi = q(f'select min("{c}"), max("{c}") from "{t}"')[0]
                fmt = lambda v: "-" if v is None else (ribu(int(v)) if float(v).is_integer() else f"{v:.6g}".replace(".", ","))
                contoh = f"{fmt(lo)} s.d. {fmt(hi)}" if lo is not None else "-"
            else:
                atas = q(f'select "{c}", count(*) from "{t}" where "{c}" is not null group by 1 order by 2 desc, 1 limit 3')
                if beda <= 6:
                    contoh = ", ".join(f"{str(v)[:40]} ({ribu(m)})" for v, m in atas)
                else:
                    v = q(f'select "{c}" from "{t}" where "{c}" is not null limit 1')
                    contoh = (str(v[0][0])[:60] + ("..." if len(str(v[0][0])) > 60 else "")) if v else "-"
            rujuk = next((f'{r["tujuan"]}.{r["kol_t"]}' for r in REL if r["asal"] == t and c in r["kols"] and r["jenis"] != "turunan"), "")
            baris.append(dict(nama=c, tipe=k["tipe"], pk=bool(k["pk"]), nn=k["nn"], fk=rujuk, uk=(t, c) in UK,
                              ket=TABEL[t]["ket"].get(c, ""), null=f"{(nul or 0) / n * 100:.1f}".replace(".", ",") if n else "-",
                              beda=ribu(beda), contoh=contoh))
        hasil[t] = baris
    return hasil


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    keluaran = {}
    for mode in ("lengkap", "ringkas"):
        svg, W, H = gambar(mode)
        p = os.path.join(OUT_DIR, f"erd_siaga_padang_{mode}.svg")
        with open(p, "w", encoding="utf-8") as f:
            f.write(svg)
        ke_png(p, p[:-4] + ".png", W, H)
        keluaran[mode] = svg
        print(f"{mode}: {p} ({W:.0f} x {H:.0f} px; PNG 2x)")
    data = dict(
        versi=VERSI, commit_aplikasi=COMMIT_APLIKASI, grup={k: list(v) for k, v in GRUP.items()},
        tabel=[dict(nama=t, jenis=objek[t], grup=TABEL[t]["grup"], uraian=TABEL[t]["uraian"], baris=ribu(BARIS[t]),
                    aplikasi=APLIKASI[t]) for kol in TATA_LETAK for t in kol],
        kolom=kamus_data(),
        relasi=[dict(asal=r["asal"], kols=r["kols"], tujuan=r["tujuan"], kol_t=r["kol_t"], jenis=r["jenis"], where=r["where"],
                     sa=r["sa"], st=r["st"], yatim=r["yatim"]) for r in REL],
        metadata=q("select kunci, nilai from tb_metadata"),
        indeks=q("select name, tbl_name, sql from sqlite_master where type = 'index' and sql is not null order by tbl_name"),
    )
    with open(os.path.join("docs", "erd", "templat_erd.html"), encoding="utf-8") as f:
        halaman = f.read()
    for kunci, isi in (("__SVG_LENGKAP__", keluaran["lengkap"]), ("__SVG_RINGKAS__", keluaran["ringkas"]),
                       ("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))):
        assert halaman.count(kunci) == 1, kunci
        halaman = halaman.replace(kunci, isi)
    with open(os.path.join(OUT_DIR, "erd_siaga_padang.html"), "w", encoding="utf-8") as f:
        f.write(halaman)
    print(f"HTML interaktif: {os.path.join(OUT_DIR, 'erd_siaga_padang.html')} ({len(halaman) / 1e6:.2f} MB)")
    print("Relasi:")
    for r in REL:
        print(f"  {r['asal']}.{','.join(r['kols'])} [{r['sa']}] -- [{r['st']}] {r['tujuan']}.{r['kol_t']} ({r['jenis']})"
              + (f" yatim {r['yatim']}" if r["yatim"] else ""))


if __name__ == "__main__":
    main()
