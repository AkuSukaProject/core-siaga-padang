"""
Generator DBML (dbdiagram.io) untuk database Siaga Padang.

Skema dibaca langsung dari berkas SQLite hasil build_db.py sehingga ERD selalu sinkron dengan DB.
Catatan kolom & relasi logis didefinisikan di bawah; kolom tanpa catatan tetap ditulis apa adanya.
Keluaran: docs/siaga_padang_erd.dbml
"""
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join("hasil_build", "ranah_siaga_v4.db")
OUTPUT_PATH = os.path.join("docs", "siaga_padang_erd.dbml")

# Kelompok tabel (urutan = urutan di berkas DBML).
KELOMPOK = {
    "Graf_Jalan": ["tb_nodes", "tb_edges"],
    "Rute_TES_Vertikal": ["tb_tes", "tb_routes", "v_fasilitas_evakuasi"],
    "Rute_TEA_Horizontal": ["tb_tea", "tb_tea_routes", "tb_tea_next"],
    "Rute_Zona_Aman": ["tb_safe_routes_v2", "tb_safe_next_v2", "tb_safe_routes", "tb_safe_next"],
    "Zona_Spasial": ["tb_inundation_zones", "tb_safe_zones"],
    "Penugasan": ["tb_route_shares"],
    "Info_V4_Tambahan": ["tb_bridge_edges", "tb_fasilitas_info", "tb_node_info", "tb_kelurahan_info",
                         "tb_jalur_resmi", "tb_metadata"],
}

CATATAN_TABEL = {
    "tb_nodes": "Simpul persimpangan jalan (OSM). is_safe dari poligon zona merah (landaan KRB 2023-2027 + zona rawan peta evakuasi BPBD); jarak_pantai_m dari garis pantai OSM.",
    "tb_edges": "Ruas jalan untuk menggambar rute di peta.",
    "tb_tes": "TES yang dipakai routing; sumber BPBD (daftar resmi 2019) atau WARGA (Kelurahan Tangguh/latihan 2025). Nama unik.",
    "tb_routes": "Hingga 3 TES per node ZONA MERAH yang lolos syarat arah (menjauh > 15 derajat; <= 100 m tidak dinilai); jembatan >= 20 m hanya cadangan. Yang sempat <= 20 menit urut jarak pantai (terjauh = rank 1), lalu tercepat. rank 2/3 boleh kosong. ETA pada 1,2 m/s.",
    "tb_tea": "TEA yang dipakai routing (di luar area landaan).",
    "tb_tea_routes": "TEA utama & alternatif per node (urutan sama dengan TES: terjauh dari pantai yang sempat <= 20 menit).",
    "tb_tea_next": "Tabel next-hop menuju tiap TEA (rangkai rute di memori).",
    "tb_safe_routes_v2": "Navigasi zona aman (K-B6): per node ZONA MERAH, titik zona hijau terjauh dari pantai yang sempat <= 15 menit dan lolos syarat arah; bila tidak ada, batas zona hijau tercepat.",
    "tb_safe_next_v2": "Next-hop menuju zona aman per titik tujuan (kelompok milik node asal).",
    "tb_safe_routes": "Kontrak lama: batas zona hijau terdekat per node dari satu pohon global; simpul merah hanya bila tujuan lolos syarat arah. safe_eta = 0 = tujuan zona hijau (status tiba).",
    "tb_safe_next": "Kontrak: next-hop pohon global menuju zona aman.",
    "tb_inundation_zones": "Zona merah per kelurahan: landaan KRB + zona rawan peta evakuasi BPBD, dipotong ke daratan. tingkat_bahaya selalu 'Tinggi' (peta evakuasi hanya merah/hijau).",
    "tb_safe_zones": "Bagian darat kelurahan di luar zona merah (zona hijau).",
    "tb_route_shares": "Porsi penugasan warga per node ke TES/TEA/zona aman (greedy berkapasitas).",
    "tb_fasilitas_info": "Semua TES/TEA sumber BPBD termasuk yang tidak dipakai, beserta alasan & sumber kapasitas.",
    "tb_node_info": "Atribut tambahan node: kelurahan, jarak ke pantai, indeks bahaya, demand, ketergantungan jembatan.",
    "tb_kelurahan_info": "Profil tsunami per kelurahan dari tabel KRB 2023-2027.",
    "tb_bridge_edges": "edge_id tb_edges yang memuat jembatan >= 20 m (kontrak H-4).",
    "tb_jalur_resmi": "Ruas graf yang mengikuti jalur evakuasi resmi BPBD.",
    "tb_metadata": "Versi, sumber data, dan parameter build.",
    "v_fasilitas_evakuasi": "VIEW (bukan tabel): tb_tes UNION ALL tb_tea, untuk daftar dan peta fasilitas.",
}

CATATAN_KOLOM = {
    ("tb_nodes", "is_safe"): "0 = zona merah (area landaan), 1 = zona aman",
    ("tb_tes", "nama_tes"): "Target relasi logis rank_X_tes",
    ("tb_tes", "zona"): "Kelurahan",
    ("tb_tes", "kapasitas"): "Jiwa, dari data BPBD; NULL bila tidak ada (estimasi hanya di tb_fasilitas_info)",
    ("tb_tes", "sumber"): "BPBD atau WARGA",
    ("tb_routes", "rank_1_eta"): "Menit pada 1,2 m/s (laju tabel kontrak); waktu riil = x 1,2 / 0,894",
    ("tb_routes", "rank_1_path"): "ID node dipisah koma, dari asal ke TES",
    ("tb_tea", "kapasitas"): "0 = tidak tersedia (TEA tidak dibatasi kapasitas saat routing)",
    ("tb_safe_zones", "elevasi_m"): "NULL (belum ada data elevasi)",
    ("tb_route_shares", "jenis"): "TES / TEA / ZONA_AMAN",
    ("tb_safe_routes_v2", "kelompok"): "Nomor titik tujuan; kunci penelusuran tb_safe_next_v2",
    ("tb_safe_routes_v2", "mendekat_pantai_maks_m"): "Seberapa jauh rute sempat lebih dekat ke pantai daripada asal",
    ("tb_node_info", "kantong_aman"): "1 = zona aman kecil (< 50 ha) dikelilingi zona merah; bukan tujuan evakuasi",
    ("tb_fasilitas_info", "dipakai"): "1 = dipakai routing",
    ("tb_fasilitas_info", "d_pantai_m"): "Jarak ke garis pantai (batimetri BPBD)",
    ("tb_fasilitas_info", "indeks_bahaya"): "Indeks bahaya tsunami; NULL = di luar landaan",
    ("tb_node_info", "demand_jiwa"): "Jiwa terpapar KRB disebar menurut jejak bangunan, ditambah perkiraan penduduk zona merah peta evakuasi",
}

# Relasi logis (bukan foreign key SQLite): (tabel, kolom) -> "tabel.kolom".
RELASI = {
    ("tb_edges", "u"): "tb_nodes.node_id",
    ("tb_edges", "v"): "tb_nodes.node_id",
    ("tb_routes", "origin_node_id"): "tb_nodes.node_id",
    ("tb_routes", "rank_1_tes"): "tb_tes.nama_tes",
    ("tb_routes", "rank_2_tes"): "tb_tes.nama_tes",
    ("tb_routes", "rank_3_tes"): "tb_tes.nama_tes",
    ("tb_tea", "nearest_node_id"): "tb_nodes.node_id",
    ("tb_tea_routes", "origin_node_id"): "tb_nodes.node_id",
    ("tb_tea_routes", "nearest_tea_id"): "tb_tea.tea_id",
    ("tb_tea_routes", "alt_tea_id"): "tb_tea.tea_id",
    ("tb_tea_next", "tea_id"): "tb_tea.tea_id",
    ("tb_tea_next", "node_id"): "tb_nodes.node_id",
    ("tb_tea_next", "next_node_id"): "tb_nodes.node_id",
    ("tb_safe_routes", "origin_node_id"): "tb_nodes.node_id",
    ("tb_safe_routes", "safe_node_id"): "tb_nodes.node_id",
    ("tb_safe_routes", "safe_zone_id"): "tb_safe_zones.safe_zone_id",
    ("tb_safe_routes_v2", "safe_zone_id"): "tb_safe_zones.safe_zone_id",
    ("tb_safe_next", "node_id"): "tb_nodes.node_id",
    ("tb_safe_next", "next_node_id"): "tb_nodes.node_id",
    ("tb_safe_routes_v2", "origin_node_id"): "tb_nodes.node_id",
    ("tb_safe_routes_v2", "safe_node_id"): "tb_nodes.node_id",
    ("tb_safe_next_v2", "node_id"): "tb_nodes.node_id",
    ("tb_safe_next_v2", "next_node_id"): "tb_nodes.node_id",
    ("tb_route_shares", "origin_node_id"): "tb_nodes.node_id",
    ("tb_fasilitas_info", "nearest_node_id"): "tb_nodes.node_id",
    ("tb_node_info", "node_id"): "tb_nodes.node_id",
    ("tb_bridge_edges", "edge_id"): "tb_edges.edge_id",
    ("tb_jalur_resmi", "u"): "tb_nodes.node_id",
    ("tb_jalur_resmi", "v"): "tb_nodes.node_id",
}
# Relasi 1:1 (PK yang juga merujuk node).
SATU_SATU = {("tb_routes", "origin_node_id"), ("tb_tea_routes", "origin_node_id"),
             ("tb_safe_routes", "origin_node_id"), ("tb_safe_routes_v2", "origin_node_id"),
             ("tb_node_info", "node_id")}
# Relasi yang tidak bisa ditulis sebagai ref satu kolom (satu kolom ke dua tabel, kunci kelompok, atau lewat nama),
# ditulis sebagai blok Ref terpisah. Sama dengan RELASI di generate_erd_gambar.py.
REF_TAMBAHAN = [
    ("tb_safe_routes_v2.kelompok", "<>", "tb_safe_next_v2.kelompok", "kunci kelompok pohon next-hop v2"),
    ("tb_route_shares.nama_tujuan", ">", "tb_tes.nama_tes", "bila jenis = 'TES'"),
    ("tb_route_shares.nama_tujuan", ">", "tb_tea.nama_tea", "bila jenis = 'TEA'"),
    ("tb_tes.tes_id", "-", "tb_fasilitas_info.facility_id", "TES yang dipakai routing"),
    ("tb_tea.tea_id", "-", "tb_fasilitas_info.facility_id", "TEA yang dipakai routing"),
    ("tb_node_info.kelurahan", ">", "tb_kelurahan_info.kelurahan", "lewat nama; hanya 56 kelurahan terpapar"),
    ("tb_inundation_zones.nama_zona", "-", "tb_kelurahan_info.kelurahan", "lewat nama"),
    ("tb_safe_zones.nama_zona", "-", "tb_kelurahan_info.kelurahan", "lewat nama"),
]


def esc(teks):
    return teks.replace('"', "'")


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"[ERROR] {DB_PATH} tidak ditemukan. Jalankan build_db.py terlebih dahulu.")
    conn = sqlite3.connect(DB_PATH)
    tabel_db = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'")}
    versi = dict(conn.execute("SELECT kunci, nilai FROM tb_metadata")).get("versi", "?") if "tb_metadata" in tabel_db else "?"

    out = [
        "// DBML Schema Definition for dbdiagram.io",
        f"// Dibangkitkan otomatis oleh generate_dbml_file.py dari {DB_PATH} (versi data {versi}). Jangan diedit manual.",
        "",
        "Project SiagaPadangERD {",
        "  database_type: 'SQLite'",
        "  Note: '''",
        f"    Database lokal Android Siaga Padang ({DB_PATH}).",
        "    Relasi adalah keterkaitan logis yang dipakai aplikasi, bukan foreign key constraint SQLite.",
        "  '''",
        "}",
        "",
    ]
    tertulis = []
    for grup, daftar in KELOMPOK.items():
        for t in daftar:
            if t not in tabel_db:
                continue
            tertulis.append(t)
            info = conn.execute(f"PRAGMA table_info({t})").fetchall()
            pk_cols = [c[1] for c in sorted(info, key=lambda c: c[5]) if c[5] > 0]
            out.append(f"Table {t} {{")
            for _, nama, tipe, notnull, default, pk in info:
                atribut = []
                if pk and len(pk_cols) == 1:
                    atribut.append("pk")
                if notnull and not pk:
                    atribut.append("not null")
                if default is not None:
                    atribut.append(f"default: {default}")
                ref = RELASI.get((t, nama))
                if ref:
                    atribut.append(f"ref: {'-' if (t, nama) in SATU_SATU else '>'} {ref}")
                cat = CATATAN_KOLOM.get((t, nama))
                if cat:
                    atribut.append(f'note: "{esc(cat)}"')
                out.append(f"  {nama} {tipe or 'TEXT'}" + (f" [{', '.join(atribut)}]" if atribut else ""))
            if len(pk_cols) > 1:
                out += ["", "  indexes {", f"    ({', '.join(pk_cols)}) [pk]", "  }"]
            out += ["", f'  Note: "{esc(CATATAN_TABEL.get(t, ""))}"', "}", ""]
        anggota = [t for t in daftar if t in tabel_db]
        if anggota:
            out += [f"TableGroup {grup} {{"] + [f"  {t}" for t in anggota] + ["}", ""]

    out.append("// Relasi tambahan (logis)")
    for asal, jenis, tujuan, cat in REF_TAMBAHAN:
        assert asal.split(".")[0] in tertulis and tujuan.split(".")[0] in tertulis, (asal, tujuan)
        out.append(f"Ref: {asal} {jenis} {tujuan} // {cat}")
    out.append("")

    lain = sorted(tabel_db - set(tertulis))
    if lain:
        print(f"[PERINGATAN] Tabel belum dikelompokkan, tidak ditulis: {', '.join(lain)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"DBML ditulis ke {OUTPUT_PATH} ({len(tertulis)} tabel, versi data {versi})")


if __name__ == "__main__":
    main()
