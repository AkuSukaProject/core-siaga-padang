"""
BUILDER DATABASE SIAGA PADANG V4 (DATA BPBD 2023-2027 & ATURAN EVAKUASI BPBD)

Menggantikan rantai lama core.py -> build_db_v2_with_tea.py -> spatial/1..4 (diarsipkan di legacy/pipeline_db/).
Seluruh aturan mengacu ke docs/aturan_evakuasi_bpbd.md.

Isi DB mengikuti kontrak DB aplikasi (repo siagapadang, docs/PEMBAGIAN_TUGAS_BPBD.md §1 dan §2.1).

Sumber data (folder "Data BPBD/", rincian & daftar data yang sengaja tidak dipakai: docs/build_db_v4.md):
  - SHP kecamatan/2_TES_TEA_Padang.shp      : titik TES & TEA (digitasi staf GIS BPBD, Kelurahan Tangguh / latihan 2025)
  - Daftar Shelter OK.xlsx                   : daftar resmi BPBD 2019 ("TES OK", penentu sumber BPBD) & verifikasi 2019
  - SHP kecamatan/Jalur_evakuasi_Padang.shp : jalur evakuasi resmi per RT/RW (diutamakan saat routing)
  - KRB .../03_TEMATIK/Bahaya.gdb            : raster Peta_Bahaya_Tsunami (zona merah)
  - KRB .../02_BASEMAP/Basemap.gdb           : batas kelurahan, sungai (cadangan jembatan), jejak bangunan
  - KRB .../04_TABEL/FINAL MATRIKS ...xlsx   : profil tsunami per kelurahan (penduduk terpapar, kelompok rentan, risiko)
Graf jalan: padang_full.graphml (OSM). Garis pantai & jembatan: data_osm/ (OSM, ODbL).

Pemakaian: python build_db.py [--versi 2026.10.12]

Keluaran (folder hasil_build/): ranah_siaga_v4.db, ranah_siaga_v4.db.zip, dataset_manifest.json,
dataset_manifest_android.json (format aset aplikasi), daftar_tes_tea.csv (H-1), bpbd_2019_tanpa_titik.csv,
peta_celah_kelurahan.csv (H-7).
"""
import sys
import os
import re
import time
import sqlite3
import hashlib
import json
import math
import argparse
import zipfile
import difflib
from datetime import datetime

import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import rasterio
import rasterio.features
import shapely
from shapely import wkt as shapely_wkt
from shapely.geometry import shape, LineString
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy import ndimage
from scipy.spatial import cKDTree
from pyproj import Transformer

sys.stdout.reconfigure(encoding='utf-8')
# Semua path relatif terhadap root repositori, dari folder mana pun skrip dijalankan.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

_arg = argparse.ArgumentParser(description="Bangun hasil_build/ranah_siaga_v4.db dari data BPBD")
_arg.add_argument("--versi", help="Label versi dataset (angka bertingkat, mis. 2026.10.12). Bawaan: tanggal build.")
ARGS = _arg.parse_args()

# ==============================================================================
# KONFIGURASI (rujukan: docs/aturan_evakuasi_bpbd.md)
# ==============================================================================
# Kecepatan berjalan orang paling lemah: 2 mph = 3,22 km/jam (FEMA P-646), dipakai BPBD
# untuk radius layanan 1 km / 20 menit (bagian 4). Dipakai untuk semua keputusan di engine.
KECEPATAN_JALAN_MS = 0.894
# Satuan kolom waktu tempuh yang dibaca aplikasi (rank_k_eta, safe_eta): kontrak DB
# (siagapadang docs/PEMBAGIAN_TUGAS_BPBD.md §2.1) menetapkan 1,2 m/s; aplikasi yang mengubahnya
# ke laju rujukan, supaya tidak terhitung dua kali. ETA tersimpan = ETA riil x 0,894 / 1,2.
KECEPATAN_TABEL_MS = 1.2
# Batas waktu evakuasi skenario terburuk BPBD (bagian 3).
BATAS_WAKTU_MENIT = 20.0
# Aturan menjauhi pantai (bagian 5.1.1), dua lapis penalti di jalur:
#  - setiap meter rute bergerak ke arah pantai dihitung seperti berjalan BOBOT meter tambahan
#    (mencegah rute "merayap" ke pantai lewat banyak ruas pendek; jalan sejajar pantai nyaris tak kena);
#  - ruas yang sekaligus mendekati pantai lebih dari toleransi dikalikan PENALTI.
# Nilai dipilih dari uji sensitivitas (docs/build_db_v4.md): larangan total membuat sebagian warga
# Koto Tangah tidak punya jalan keluar, jadi penalti dipakai alih-alih larangan.
TOLERANSI_MENDEKAT_PANTAI_M = 50.0
PENALTI_MENDEKAT_PANTAI = 50.0
BOBOT_PER_METER_MENDEKAT_PANTAI = 10.0
# Syarat arah tujuan (asumsi kerja K-B1, PEMBAGIAN_TUGAS_BPBD.md §1), berlaku untuk TES, TEA, dan
# zona aman: tujuan harus MENJAUH, yaitu (jarak_pantai tujuan - jarak_pantai asal) / jarak lurus
# > sin 15 derajat. Sejajar (dalam +-15 derajat) tidak boleh. Tujuan <= 100 m tidak dinilai arahnya.
# Skrip audit tim (docs/audit/analisis_masukan_bpbd.py) memakai ambang 0,26; engine menambah margin 0,01
# agar pembulatan jarak_pantai_m, proyeksi, dan garis pantai yang sedikit berbeda tidak membalik kelas arah.
ARAH_MIN_SIN = 0.26 + 0.01
ARAH_JARAK_DEKAT_M = 100.0
# Kantong aman: bagian zona aman yang dikelilingi zona merah dan luasnya < nilai ini tidak dijadikan
# tujuan evakuasi (warga harus keluar dari zona merah, bukan berhenti di pulau kecil di tengahnya).
LUAS_MIN_ZONA_AMAN_HA = 50.0
# Jembatan (asumsi kerja K-B2): yang dihindari jembatan >= 20 m. Rute dicari dulu pada graf tanpa
# jembatan itu; hanya bila tujuan tidak terjangkau tanpa jembatan, rute lewat jembatan dipakai sebagai
# cadangan (dengan penalti agar jembatan sesedikit mungkin) dan ditandai di tb_node_info.
JEMBATAN_MIN_M = 20.0
PENALTI_JEMBATAN = 20.0
# Bila data jembatan OSM (data_osm/jembatan_osm.json) belum ada, panjang badan jembatan diperkirakan
# dari lebar sungai BPBD yang dipotong ruas (+ kepala jembatan); lebar >= nilai ini dianggap >= 20 m.
JEMBATAN_LEBAR_SUNGAI_MIN_M = 10.0
# Lantai yang dianggap terendam landaan 8-10 m (bagian 6.1). Hanya dipakai untuk estimasi kapasitas
# (lantai di atasnya yang dihitung). Kelayakan TES mengikuti penilaian BPBD ("tidak potensial"), bukan
# angka lantai: di data BPBD 2019 bangunan 2 lantai hampir selalu "tidak potensial", kecuali Masjid Raya
# Sumbar yang dinilai potensial; tim aplikasi juga tidak menetapkan minimal lantai sendiri.
LANTAI_TERENDAM = 2
# Titik TES/TEA bernama & berjenis sama yang berjarak <= nilai ini dianggap tempat yang sama dan
# digabung (syarat nama unik H-1); yang lebih jauh dianggap tempat berbeda dan namanya dibedakan.
GABUNG_JARAK_M = 100.0
# Ambang kemiripan nama untuk mencocokkan TES 2025 dengan daftar verifikasi 2019.
AMBANG_KEMIRIPAN_NAMA = 0.88
# Jalur evakuasi resmi BPBD/Kelurahan Tangguh diutamakan ("ikuti rambu evakuasi", bagian 11):
# ruas yang >= 80% panjangnya berada <= 15 m dari jalur resmi mendapat faktor biaya 0,8.
JALUR_RESMI_JARAK_M = 15.0
JALUR_RESMI_FAKTOR = 0.8
# Estimasi kapasitas TES dari jejak bangunan (bila BPBD 2025 & 2019 kosong): hanya lantai di atas
# lantai 2 yang dihitung aman dari landaan 8-10 m (bagian 6.1), standar BPBD 1 m2/orang (bagian 6.3).
M2_PER_ORANG = 1.0
LANTAI_ASUMSI = 3
JARAK_MAKS_JEJAK_BANGUNAN_M = 25.0

CRS_METER = "EPSG:32747"  # UTM 47S
DIR_BPBD = "Data BPBD"
DIR_KRB = os.path.join(DIR_BPBD, "KRB Padang [2023-2027]")
FILE_TES_TEA = os.path.join(DIR_BPBD, "SHP kecamatan", "2_TES_TEA_Padang.shp")
FILE_JALUR = os.path.join(DIR_BPBD, "SHP kecamatan", "Jalur_evakuasi_Padang.shp")
FILE_BASEMAP = os.path.join(DIR_KRB, "02_BASEMAP", "Basemap.gdb")
RASTER_TSUNAMI = "OpenFileGDB:" + os.path.join(DIR_KRB, "03_TEMATIK", "Bahaya.gdb") + ":Peta_Bahaya_Tsunami"
FILE_KRB_TABEL = os.path.join(DIR_KRB, "04_TABEL", "FINAL MATRIKS KRB KOTA PADANG - DOKUMEN.xlsx")
FILE_SHELTER_2019 = os.path.join(DIR_BPBD, "Daftar Shelter OK.xlsx")
FILE_GRAF = "padang_full.graphml"
# Data OpenStreetMap pendukung (c) kontributor OSM, ODbL: garis pantai (natural=coastline) untuk
# jarak_pantai_m (kontrak H-3) dan, bila ada, ruas jembatan dengan panjang badannya (H-4).
FILE_PANTAI_OSM = os.path.join("data_osm", "pantai_osm.json")
FILE_JEMBATAN_OSM = os.path.join("data_osm", "jembatan_osm.json")
# Koordinat bangunan daftar resmi BPBD 2019 yang tidak punya titik di data 2025, dicari lewat OSM Nominatim
# dan diperiksa nama + jalannya (hasil: sudah_ada_di_data_2025 / baru_cocok / ragu / tidak_ditemukan).
FILE_GEOKODE_BPBD = os.path.join("data_osm", "geokode_daftar_resmi_bpbd.csv")
# Jarak maksimum titik geokode ke titik TES 2025 yang dianggap bangunan yang sama.
JARAK_MAKS_GEOKODE_M = 100.0
DIR_HASIL = "hasil_build"
DB_PATH = os.path.join(DIR_HASIL, "ranah_siaga_v4.db")
# Paket distribusi untuk aplikasi (zip deterministik) dan manifestnya.
ZIP_PATH = DB_PATH + ".zip"
MANIFEST_PATH = os.path.join(DIR_HASIL, "dataset_manifest.json")
# Format yang dibaca aplikasi dari assets/dataset_manifest.json (DatasetStorage.kt):
# checksum & size_bytes milik file .db tanpa zip.
MANIFEST_ANDROID_PATH = os.path.join(DIR_HASIL, "dataset_manifest_android.json")

INF = np.inf
start_total = time.time()


def langkah(teks):
    print(f"\n[{time.time() - start_total:6.1f}s] {teks}")


def bersihkan_angka_osm(val, default=50.0):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    val = str(val).strip()
    match = re.search(r"(\d+(\.\d+)?)", val)
    return float(match.group(1)) if match else default


def norm_nama(s):
    s = str(s).upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\bSDN\b", "SD", s)
    s = re.sub(r"\bSMPN\b", "SMP", s)
    s = re.sub(r"\bSMAN\b", "SMA", s)
    s = re.sub(r"\bPADANG\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_kel(s):
    return re.sub(r"\s+", " ", str(s).upper().replace("-", " ")).strip()


_ROMAWI = re.compile(r"^(?=[IVX]+$)X{0,3}(?:IX|IV|V?I{0,3})$", re.I)


def judul(teks):
    """Huruf awal kapital seperti str.title(), tetapi angka Romawi tetap kapital ("Nan XX", bukan "Nan Xx")."""
    if teks is None or (isinstance(teks, float) and np.isnan(teks)):
        return ""
    return " ".join(w.upper() if _ROMAWI.match(w) else w.capitalize() for w in str(teks).split())


def menit(meter):
    return meter / KECEPATAN_JALAN_MS / 60.0


def bulatkan_wkt(geom, desimal=6):
    return shapely.set_precision(geom, 10 ** -desimal).wkt if geom is not None else None


def wkt_multipolygon(geom, desimal=7):
    """WKT MULTIPOLYGON 2D dengan 7 desimal (kontrak §2.1), juga untuk poligon tunggal."""
    geom = shapely.set_precision(geom, 10 ** -desimal)
    bagian = [g for g in shapely.get_parts(geom) if g.geom_type == "Polygon" and not g.is_empty]
    return shapely.MultiPolygon(bagian).wkt


for f in [FILE_TES_TEA, FILE_JALUR, FILE_BASEMAP, FILE_KRB_TABEL, FILE_SHELTER_2019, FILE_GRAF]:
    if not os.path.exists(f):
        sys.exit(f"[ERROR] Berkas sumber tidak ditemukan: {f}\n"
                 f"        (shapefile TES/TEA diekstrak dari 'Data BPBD/SHP kecamatan.rar')")

print("=" * 80)
print("BUILDER DATABASE SIAGA PADANG V4 - DATA BPBD & ATURAN EVAKUASI BPBD")
print("=" * 80)

# ==============================================================================
# 1. DATA DASAR BPBD: KELURAHAN, LAUT, SUNGAI, RASTER BAHAYA TSUNAMI
# ==============================================================================
langkah("[1/9] Memuat basemap BPBD (kelurahan, batimetri, sungai, bangunan), jalur evakuasi, raster bahaya...")
gdf_kel = gpd.read_file(FILE_BASEMAP, layer="Batas_Administrasi_Kelurahan_AR").to_crs(CRS_METER)
gdf_kel["KEL"] = gdf_kel["Kelurahan"].map(norm_kel)
gdf_kel["KEC"] = gdf_kel["Kecamatan"].map(norm_kel)
gdf_kel = gdf_kel[["KEL", "KEC", "geometry"]]

# Garis pantai: OSM natural=coastline (kontrak H-3, sama dengan skrip audit tim aplikasi). Batimetri BPBD
# hanya cadangan bila berkas OSM tidak ada; selisih keduanya di zona merah: median 1 m, maks 70 m.
if os.path.exists(FILE_PANTAI_OSM):
    _ke_m = Transformer.from_crs("EPSG:4326", CRS_METER, always_xy=True)
    laut = shapely.union_all([LineString(list(zip(*_ke_m.transform([p["lon"] for p in w["geometry"]], [p["lat"] for p in w["geometry"]]))))
                              for w in json.load(open(FILE_PANTAI_OSM, encoding="utf-8"))["elements"]])
    SUMBER_PANTAI = "OpenStreetMap natural=coastline (data_osm/pantai_osm.json)"
else:
    laut = gpd.read_file(FILE_BASEMAP, layer="Bathimetri_Padang").to_crs(CRS_METER).union_all()
    SUMBER_PANTAI = "BPBD Basemap.gdb Bathimetri_Padang"
sungai = gpd.read_file(FILE_BASEMAP, layer="Sungai_AR").to_crs(CRS_METER).union_all()
shapely.prepare(laut)
shapely.prepare(sungai)

# Jejak bangunan RTRW (dipakai untuk sebaran penduduk & estimasi kapasitas TES).
bangunan = gpd.read_file(FILE_BASEMAP, layer="Bangunan_AR", columns=[]).to_crs(CRS_METER)
bangunan = bangunan[bangunan.geometry.notna() & ~bangunan.geometry.is_empty].reset_index(drop=True)
luas_bangunan = bangunan.area.to_numpy()
pusat_bangunan = bangunan.geometry.centroid
pohon_bangunan = shapely.STRtree(bangunan.geometry.values)

# Jalur evakuasi resmi (digitasi BPBD per RT/RW).
gdf_jalur = gpd.read_file(FILE_JALUR).to_crs(CRS_METER)
gdf_jalur = gdf_jalur[gdf_jalur.geometry.notna() & ~gdf_jalur.geometry.is_empty]
pohon_jalur = shapely.STRtree(gdf_jalur.geometry.values)


class Raster:
    """Pembaca nilai raster BPBD di titik (meter UTM). NaN = di luar data."""

    def __init__(self, path):
        self.src = rasterio.open(path)
        self.data = self.src.read(1, masked=True)
        self.crs = self.src.crs.to_wkt()
        self.ke_raster = Transformer.from_crs(CRS_METER, self.crs, always_xy=True)

    def sel(self, x_m, y_m):
        """(baris, kolom, di_dalam) sel raster untuk titik meter UTM."""
        rx, ry = self.ke_raster.transform(np.asarray(x_m, dtype=float), np.asarray(y_m, dtype=float))
        rows, cols = rasterio.transform.rowcol(self.src.transform, rx, ry)
        rows, cols = np.atleast_1d(rows), np.atleast_1d(cols)
        di_dalam = (rows >= 0) & (rows < self.src.height) & (cols >= 0) & (cols < self.src.width)
        return rows, cols, di_dalam

    def sampel(self, x_m, y_m):
        rows, cols, di_dalam = self.sel(x_m, y_m)
        hasil = np.full(rows.shape, np.nan)
        nilai = self.data[rows[di_dalam], cols[di_dalam]]
        hasil[di_dalam] = np.where(np.ma.getmaskarray(nilai), np.nan, np.ma.getdata(nilai))
        return hasil


r_tsunami = Raster(RASTER_TSUNAMI)
raster_src, raster_bahaya, raster_crs = r_tsunami.src, r_tsunami.data, r_tsunami.crs
sampel_bahaya = r_tsunami.sampel

print(f"      Kelurahan: {len(gdf_kel)} | Sel landaan tsunami: {raster_bahaya.count():,} "
      f"({raster_bahaya.count() * 0.09:,.0f} ha) | Bangunan: {len(bangunan):,} | Ruas jalur evakuasi resmi: {len(gdf_jalur):,}")

# ==============================================================================
# 2. GRAF JALAN: ATRIBUT NODE (ZONA MERAH, JARAK KE PANTAI, KELURAHAN)
# ==============================================================================
langkah("[2/9] Membaca graf jalan dan menghitung atribut node...")
G = nx.read_graphml(FILE_GRAF).to_undirected()
node_ids = np.array([int(n) for n in G.nodes])
lon = np.array([float(d["x"]) for _, d in G.nodes(data=True)])
lat = np.array([float(d["y"]) for _, d in G.nodes(data=True)])
N = len(node_ids)
idx_of = {str(n): i for i, n in enumerate(node_ids)}

ke_meter = Transformer.from_crs("EPSG:4326", CRS_METER, always_xy=True)
x_node, y_node = ke_meter.transform(lon, lat)
titik_node = shapely.points(x_node, y_node)

indeks_bahaya_node = sampel_bahaya(x_node, y_node)
is_safe = np.where(np.isnan(indeks_bahaya_node), 1, 0)
d_pantai = shapely.distance(titik_node, laut)

gdf_nodes = gpd.GeoDataFrame({"i": np.arange(N)}, geometry=titik_node, crs=CRS_METER)
join = gpd.sjoin(gdf_nodes, gdf_kel, how="left", predicate="within").drop_duplicates("i").sort_values("i")
kel_node = join["KEL"].fillna("").to_numpy()
print(f"      Node: {N:,} | di zona merah: {(is_safe == 0).sum():,} | di luar batas kota: {(kel_node == '').sum():,}")

# ==============================================================================
# 3. RUAS JALAN: BOBOT BERARAH (PENALTI PANTAI, JEMBATAN >= 20 M, JALUR RESMI)
# ==============================================================================
langkah("[3/9] Menyusun bobot ruas berarah (aturan pantai, jembatan, jalur resmi)...")
pasangan = {}
edge_rows, edge_jembatan_tag = [], []
for u, v, k, data in G.edges(keys=True, data=True):
    panjang = bersihkan_angka_osm(data.get("length", 50.0))
    geom_str = str(data.get("geometry", ""))
    edge_rows.append((int(u), int(v), float(panjang), geom_str))
    edge_jembatan_tag.append("yes" in str(data.get("bridge", "")) or "viaduct" in str(data.get("bridge", "")))
    iu, iv = idx_of[u], idx_of[v]
    if iu == iv:
        continue
    kunci = (min(iu, iv), max(iu, iv))
    lama = pasangan.get(kunci)
    if lama is None or panjang < lama[0]:
        pasangan[kunci] = (panjang, len(edge_rows) - 1, geom_str)

kunci_arr = np.array(list(pasangan.keys()))
nilai_pasangan = list(pasangan.values())
panjang_arr = np.array([p[0] for p in nilai_pasangan])


def garis_derajat_ruas(geom_str, a, b):
    """Geometri ruas (derajat, lon lat); ruas lurus tanpa geometri memakai kedua simpulnya."""
    if geom_str.startswith("LINESTRING"):
        return shapely_wkt.loads(geom_str)
    return LineString([(lon[a], lat[a]), (lon[b], lat[b])])


def ke_meter_arr(garis):
    return shapely.transform(garis, lambda c: np.column_stack(ke_meter.transform(c[:, 0], c[:, 1])))


# Geometri ruas dalam meter (satu kali proyeksi untuk semua koordinat).
garis_ruas = ke_meter_arr(np.array([garis_derajat_ruas(p[2], a, b) for p, (a, b) in zip(nilai_pasangan, kunci_arr)],
                                   dtype=object))

# Jembatan >= 20 m per baris tb_edges (kontrak H-4, tb_bridge_edges).
#  - Dengan data OSM: ruas memuat segmen way bridge=* yang panjang badannya >= 20 m (cara skrip audit tim).
#  - Tanpa data OSM: badan jembatan diperkirakan dari lebar sungai BPBD yang dipotong ruas.
baris_tag = np.flatnonzero(edge_jembatan_tag)
garis_tag = [garis_derajat_ruas(edge_rows[j][3], idx_of[str(edge_rows[j][0])], idx_of[str(edge_rows[j][1])]) for j in baris_tag]
jembatan_besar_baris = np.zeros(len(edge_rows), dtype=bool)
if os.path.exists(FILE_JEMBATAN_OSM):
    def rd6(x):
        return round(float(x), 6)
    pasangan_jembatan = set()
    for w in json.load(open(FILE_JEMBATAN_OSM, encoding="utf-8"))["elements"]:
        xs, ys = ke_meter.transform([p["lon"] for p in w["geometry"]], [p["lat"] for p in w["geometry"]])
        if LineString(list(zip(xs, ys))).length < JEMBATAN_MIN_M:
            continue
        titik = [(rd6(p["lon"]), rd6(p["lat"])) for p in w["geometry"]]
        pasangan_jembatan.update(frozenset(t) for t in zip(titik, titik[1:]))
    for j, g in zip(baris_tag, garis_tag):
        koord = [(rd6(x), rd6(y)) for x, y in g.coords]
        jembatan_besar_baris[j] = any(frozenset(t) in pasangan_jembatan for t in zip(koord, koord[1:]))
    SUMBER_JEMBATAN = "OpenStreetMap highway+bridge, badan jembatan >= 20 m (data_osm/jembatan_osm.json)"
else:
    sungai = gpd.read_file(FILE_BASEMAP, layer="Sungai_AR").to_crs(CRS_METER).union_all()
    shapely.prepare(sungai)
    lebar = shapely.length(shapely.intersection(ke_meter_arr(np.array(garis_tag, dtype=object)), sungai))
    jembatan_besar_baris[baris_tag] = lebar >= JEMBATAN_LEBAR_SUNGAI_MIN_M
    SUMBER_JEMBATAN = (f"Perkiraan: ruas OSM bertag bridge yang memotong sungai BPBD (Sungai_AR) selebar "
                       f">= {JEMBATAN_LEBAR_SUNGAI_MIN_M:.0f} m; diganti otomatis bila data_osm/jembatan_osm.json tersedia")
jembatan_besar = np.array([jembatan_besar_baris[p[1]] for p in nilai_pasangan])

# Jalur evakuasi resmi: >= 80% titik sampel ruas (5 titik) berada dekat jalur BPBD.
fraksi = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
sampel_titik = np.concatenate([shapely.line_interpolate_point(garis_ruas, f, normalized=True) for f in fraksi])
dekat = pohon_jalur.query(sampel_titik, predicate="dwithin", distance=JALUR_RESMI_JARAK_M)
titik_dekat = np.zeros(len(sampel_titik), dtype=bool)
titik_dekat[np.unique(dekat[0])] = True
jalur_resmi = titik_dekat.reshape(len(fraksi), -1).mean(axis=0) >= 0.8
print(f"      Ruas tb_edges: {len(edge_rows):,} | bertag jembatan: {len(baris_tag):,} | jembatan >= {JEMBATAN_MIN_M:.0f} m: "
      f"{jembatan_besar_baris.sum():,} | pasangan simpul unik: {len(kunci_arr):,} | di jalur evakuasi resmi: {jalur_resmi.sum():,}")
print(f"      Sumber jembatan: {SUMBER_JEMBATAN}")

# Dua arah untuk setiap ruas.
src = np.concatenate([kunci_arr[:, 0], kunci_arr[:, 1]])
dst = np.concatenate([kunci_arr[:, 1], kunci_arr[:, 0]])
waktu_riil = np.concatenate([menit(panjang_arr)] * 2)
lewat_jembatan = np.concatenate([jembatan_besar] * 2)
di_jalur_resmi = np.concatenate([jalur_resmi] * 2)
mendekat = (d_pantai[src] - d_pantai[dst]) > TOLERANSI_MENDEKAT_PANTAI_M
biaya = (waktu_riil
         * np.where(mendekat, PENALTI_MENDEKAT_PANTAI, 1.0)
         * np.where(di_jalur_resmi, JALUR_RESMI_FAKTOR, 1.0)
         + BOBOT_PER_METER_MENDEKAT_PANTAI * menit(np.maximum(d_pantai[src] - d_pantai[dst], 0.0)))

# Matriks transpose: Dijkstra dari tujuan pada graf terbalik = biaya dari setiap node MENUJU tujuan.
# Predecessor pada graf terbalik = node berikutnya (next hop) pada rute asli.
# W_tanpa: tanpa jembatan >= 20 m (dipakai lebih dulu). W_dengan: jembatan boleh, berpenalti (cadangan).
tanpa = ~lewat_jembatan
W_tanpa = csr_matrix((biaya[tanpa], (dst[tanpa], src[tanpa])), shape=(N, N))
W_dengan = csr_matrix((biaya * np.where(lewat_jembatan, PENALTI_JEMBATAN, 1.0), (dst, src)), shape=(N, N))
# Biaya tambahan rute cadangan lewat jembatan, agar selalu kalah dari tujuan mana pun tanpa jembatan.
BIAYA_CADANGAN_JEMBATAN = 1e6


def pohon_rute(sumber_idx, min_only=False):
    """(biaya, next_hop[, asal]) per tujuan; next_hop[n] = node berikutnya dari n menuju tujuan.
    Rute tanpa jembatan >= 20 m dipakai bila ada; selain itu rute lewat jembatan (cadangan) dengan biaya
    tambahan. Rantai gabungan tidak bisa berputar: begitu masuk simpul yang punya rute tanpa jembatan,
    seluruh sisa rantainya juga tanpa jembatan."""
    kw = dict(directed=True, indices=sumber_idx, return_predecessors=True, min_only=min_only)
    hasil_t = dijkstra(W_tanpa, **kw)
    hasil_d = dijkstra(W_dengan, **kw)
    pakai_tanpa = np.isfinite(hasil_t[0])
    biaya_g = np.where(pakai_tanpa, hasil_t[0], hasil_d[0] + BIAYA_CADANGAN_JEMBATAN)
    pred_g = np.where(pakai_tanpa, hasil_t[1], hasil_d[1])
    if min_only:
        return biaya_g, pred_g, np.where(pakai_tanpa, hasil_t[2], hasil_d[2])
    return biaya_g, pred_g


def akumulasi_riil_baris(next_hop):
    """Waktu tempuh riil (menit, tanpa penalti) & flag lewat jembatan >= 20 m sepanjang pohon rute (pointer jumping)."""
    valid = next_hop >= 0
    w = np.zeros(len(next_hop))
    b = np.zeros(len(next_hop), dtype=bool)
    if valid.any():
        s_idx = np.flatnonzero(valid)
        w[s_idx] = waktu_edge_vec(s_idx, next_hop[s_idx])
        b[s_idx] = jembatan_edge_vec(s_idx, next_hop[s_idx])
    ar = np.arange(len(next_hop))
    ptr = np.where(valid, next_hop, ar)
    while True:
        w = w + np.where(ptr != ar, w[ptr], 0.0)
        b = b | b[ptr]
        ptr_baru = ptr[ptr]
        if np.array_equal(ptr_baru, ptr):
            return w, b
        ptr = ptr_baru


# Lookup vektor waktu/jembatan per ruas berarah (CSR berindeks (src, dst)).
_W_riil = csr_matrix((waktu_riil, (src, dst)), shape=(N, N))
_W_jemb = csr_matrix((lewat_jembatan.astype(np.int8), (src, dst)), shape=(N, N))


def waktu_edge_vec(a, b):
    return np.asarray(_W_riil[a, b]).ravel()


def jembatan_edge_vec(a, b):
    return np.asarray(_W_jemb[a, b]).ravel().astype(bool)


def eta_tabel(eta_riil_menit):
    """ETA yang ditulis ke kolom aplikasi, dikonversi ke laju tabel 1,2 m/s (kontrak §2.1)."""
    return eta_riil_menit * KECEPATAN_JALAN_MS / KECEPATAN_TABEL_MS


def arah_boleh(d_tujuan, x_tujuan, y_tujuan, idx_asal):
    """Syarat arah K-B1: tujuan menjauh dari pantai (rasio > sin 15 derajat) atau <= 100 m dari asal.
    Mendukung broadcasting, misalnya tujuan (K x 1) terhadap asal (N,)."""
    jarak = np.hypot(x_node[idx_asal] - x_tujuan, y_node[idx_asal] - y_tujuan)
    with np.errstate(divide="ignore", invalid="ignore"):
        rasio = (d_tujuan - d_pantai[idx_asal]) / jarak
    return (jarak <= ARAH_JARAK_DEKAT_M) | (rasio > ARAH_MIN_SIN)


def jalur(n, next_hop):
    path = [n]
    while next_hop[path[-1]] >= 0:
        path.append(int(next_hop[path[-1]]))
    return path


def mendekat_pantai_m(path):
    """Seberapa jauh (m) rute pernah lebih dekat ke pantai daripada titik awalnya (0 = tidak pernah)."""
    return float(d_pantai[path[0]] - d_pantai[path].min())


# ==============================================================================
# 4. FASILITAS TES & TEA (BPBD 2025) + VERIFIKASI 2019
# ==============================================================================
langkah("[4/9] Memuat TES/TEA BPBD dan verifikasi BPBD 2019...")
fas = gpd.read_file(FILE_TES_TEA).to_crs(CRS_METER)
jumlah_awal = len(fas)
fas = fas[fas.geometry.notna() & fas["Jns_fasili"].isin(["TES", "TEA"])].copy()
fas["wkt"] = fas.geometry.to_wkt()
fas = fas.drop_duplicates(subset=["Nama_Fasum", "Jns_fasili", "wkt"]).copy()
fas["Nama_Fasum"] = fas["Nama_Fasum"].astype(str).str.strip()
fas["kapasitas_bpbd"] = pd.to_numeric(fas["Kapasitas"], errors="coerce")
fas["koordinat_sumber"] = "BPBD 2025 (2_TES_TEA_Padang.shp)"
fas["nama_geokode"] = None
# Bangunan daftar resmi BPBD yang tidak ada di data 2025 tetapi lokasinya ditemukan di OSM (nama & jalan cocok)
# ditambahkan sebagai TES. ID-nya diberi setelah ID titik 2025 agar ID lama tidak bergeser.
geokode = pd.read_csv(FILE_GEOKODE_BPBD, dtype=str).fillna("") if os.path.exists(FILE_GEOKODE_BPBD) else pd.DataFrame()
if len(geokode):
    baru_geo = geokode[geokode["hasil"] == "baru_cocok"]
    if len(baru_geo):
        tambah = gpd.GeoDataFrame({"Nama_Fasum": baru_geo["nama_bpbd"].str.strip(), "Jns_fasili": "TES",
                                   "kapasitas_bpbd": np.nan, "kelurahan": "", "Kecamatan": "",
                                   "koordinat_sumber": "OSM " + baru_geo["osm"] + " (geokode daftar resmi BPBD, perlu verifikasi)",
                                   "nama_geokode": baru_geo["nama_bpbd"].str.strip()},
                                  geometry=gpd.points_from_xy(baru_geo["lon"].astype(float), baru_geo["lat"].astype(float)),
                                  crs="EPSG:4326").to_crs(CRS_METER)
        fas = pd.concat([fas, tambah], ignore_index=True)
fas = gpd.sjoin(fas, gdf_kel, how="left", predicate="within").drop(columns="index_right")
fas["di_kota"] = fas["KEL"].notna()
fas["KEL"] = fas["KEL"].fillna(fas["kelurahan"].map(norm_kel))
fas["KEC"] = fas["KEC"].fillna(fas["Kecamatan"].map(norm_kel))
print(f"      Titik sumber: {jumlah_awal} | setelah buang duplikat persis + geokode daftar resmi BPBD: {len(fas)} "
      f"(TES {(fas['Jns_fasili'] == 'TES').sum()}, TEA {(fas['Jns_fasili'] == 'TEA').sum()})")

# Daftar verifikasi 2019: jumlah lantai & status potensial.
v19 = pd.read_excel(FILE_SHELTER_2019, sheet_name="TES (verifikasi)", header=None)
rows19, status = [], None
for _, r in v19.iterrows():
    kepala = str(r[1])
    if kepala.startswith("I. "):
        status = "potensial"
    elif kepala.startswith("II. "):
        status = "tidak potensial"
    elif status and pd.notna(r[2]) and str(r[1]).strip().isdigit():
        angka = [int(a) for a in re.findall(r"\d+", str(r[5]))]
        rows19.append({"nama19": str(r[2]).strip(), "lantai19": max(angka) if angka else None,
                       "kapasitas19": pd.to_numeric(r[7], errors="coerce"),
                       "status19": status, "ket19": r[10] if pd.notna(r[10]) else ""})
df19 = pd.DataFrame(rows19)
df19["norm"] = df19["nama19"].map(norm_nama)

# Daftar resmi BPBD (sheet "TES OK": 3 shelter + 59 bangunan potensial hasil Bidang RR dengan 5 parameter).
# Inilah "data BPBD" (masukan B2); TES yang cocok diberi sumber BPBD, selebihnya hasil digitasi
# Kelurahan Tangguh / latihan 2025 diberi sumber WARGA (lapis "Kesepakatan warga", K-B5).
vok = pd.read_excel(FILE_SHELTER_2019, sheet_name="TES OK", header=None)
rows_ok, status = [], None
for _, r in vok.iterrows():
    kepala = str(r[1])
    if kepala.startswith("I. "):
        status = "shelter"
    elif kepala.startswith("II. "):
        status = "potensial"
    elif status and pd.notna(r[2]) and str(r[1]).strip().isdigit():
        angka = [int(a) for a in re.findall(r"\d+", str(r[5]))]
        rows_ok.append({"nama_ok": str(r[2]).strip(), "alamat_ok": str(r[3]).strip() if pd.notna(r[3]) else "",
                        "status_ok": status, "lantai_ok": max(angka) if angka else None,
                        "kapasitas_ok": pd.to_numeric(r[7], errors="coerce")})
df_ok = pd.DataFrame(rows_ok)
df_ok["norm"] = df_ok["nama_ok"].map(norm_nama)


def cocokkan_2019(nama, daftar=df19):
    n = norm_nama(nama)
    angka = re.findall(r"\d+", n)
    # Nomor sekolah/gedung harus sama persis (SMPN 36 bukan SMPN 3).
    calon = daftar[daftar["norm"].map(lambda m: re.findall(r"\d+", m) == angka)]
    if calon.empty:
        return None
    skor = calon["norm"].map(lambda m: difflib.SequenceMatcher(None, n, m).ratio())
    j = skor.idxmax()
    return calon.loc[j] if skor[j] >= AMBANG_KEMIRIPAN_NAMA else None


info19 = [cocokkan_2019(n) if t == "TES" else None for n, t in zip(fas["Nama_Fasum"], fas["Jns_fasili"])]
fas["lantai_2019"] = [r["lantai19"] if r is not None else None for r in info19]
fas["status_2019"] = [r["status19"] if r is not None else None for r in info19]
fas["nama_2019"] = [r["nama19"] if r is not None else None for r in info19]
fas["kapasitas_2019"] = [r["kapasitas19"] if r is not None else np.nan for r in info19]
info_ok = [cocokkan_2019(n, df_ok) if t == "TES" else None for n, t in zip(fas["Nama_Fasum"], fas["Jns_fasili"])]
ok_by_nama = {r.nama_ok: r for r in df_ok.itertuples()}
# Titik hasil geokode langsung terhubung ke baris daftar resmi asalnya.
info_ok = [ok_by_nama[g]._asdict() if g else r for g, r in zip(fas["nama_geokode"], info_ok)]
# TES 2025 yang ternyata bangunan daftar resmi BPBD dengan nama lain (titik geokode <= 100 m).
jumlah_tertaut = 0
if len(geokode):
    for g in geokode[geokode["hasil"] == "sudah_ada_di_data_2025"].itertuples():
        x, y = Transformer.from_crs("EPSG:4326", CRS_METER, always_xy=True).transform(float(g.lon), float(g.lat))
        jarak = fas.geometry.distance(shapely.Point(x, y)).where(fas["Jns_fasili"] == "TES")
        j = jarak.idxmin()
        if jarak[j] <= JARAK_MAKS_GEOKODE_M and info_ok[j] is None:
            info_ok[j] = ok_by_nama[g.nama_bpbd]._asdict()
            jumlah_tertaut += 1
fas["nama_bpbd_ok"] = [r["nama_ok"] if r is not None else None for r in info_ok]
fas["lantai_ok"] = [r["lantai_ok"] if r is not None else None for r in info_ok]
fas["kapasitas_ok"] = [r["kapasitas_ok"] if r is not None else np.nan for r in info_ok]
fas["sumber"] = np.where(fas["nama_bpbd_ok"].notna(), "BPBD", "WARGA")
print(f"      Daftar resmi BPBD 2019: {fas['nama_bpbd_ok'].notna().sum()} TES tertaut (nama: "
      f"{fas['nama_bpbd_ok'].notna().sum() - jumlah_tertaut - fas['nama_geokode'].notna().sum()}, titik sama dengan nama lain: "
      f"{jumlah_tertaut}, titik baru dari geokode OSM: {fas['nama_geokode'].notna().sum()})")
# Jumlah lantai terbaik yang diketahui (daftar resmi, lalu verifikasi 2019).
fas["lantai"] = pd.to_numeric(fas["lantai_ok"], errors="coerce").fillna(pd.to_numeric(fas["lantai_2019"], errors="coerce"))

# Jejak bangunan RTRW yang memuat (atau terdekat <= 25 m dari) titik TES.
idx_fas, idx_bgn = pohon_bangunan.query_nearest(fas.geometry.values, max_distance=JARAK_MAKS_JEJAK_BANGUNAN_M, all_matches=False)
fas["luas_jejak_m2"] = np.nan
fas.iloc[idx_fas, fas.columns.get_loc("luas_jejak_m2")] = luas_bangunan[idx_bgn]

x_fas, y_fas = fas.geometry.x.to_numpy(), fas.geometry.y.to_numpy()
fas["indeks_bahaya"] = sampel_bahaya(x_fas, y_fas)
fas["d_pantai_m"] = shapely.distance(fas.geometry.values, laut)
fas["x_m"], fas["y_m"] = x_fas, y_fas

# Kelayakan untuk routing.
fas["dipakai"] = 1
fas["alasan_tidak_dipakai"] = ""
# TES keluar bila verifikasi BPBD 2019 menilainya "tidak potensial" (penilaian BPBD, yang sudah mencakup
# bangunan 2 lantai). Pencocokan 2019 mensyaratkan nomor gedung sama persis.
tes_tak_layak = (fas["Jns_fasili"] == "TES") & (fas["status_2019"] == "tidak potensial")
fas.loc[tes_tak_layak, ["dipakai", "alasan_tidak_dipakai"]] = [0, "Verifikasi BPBD 2019: tidak potensial"]
tea_di_landaan = (fas["Jns_fasili"] == "TEA") & fas["indeks_bahaya"].notna()
fas.loc[tea_di_landaan, ["dipakai", "alasan_tidak_dipakai"]] = [0, "TEA berada di dalam area landaan tsunami"]
# Syarat H-1: semua titik berada di Kota Padang (batas kelurahan BPBD).
luar_kota = ~fas["di_kota"] & (fas["dipakai"] == 1)
fas.loc[luar_kota, ["dipakai", "alasan_tidak_dipakai"]] = [0, "Di luar batas Kota Padang"]

# Kapasitas TES berurutan: BPBD 2025 -> daftar resmi BPBD 2019 -> verifikasi BPBD 2019 -> estimasi jejak
# bangunan -> median TES BPBD. Estimasi hanya dipakai engine untuk penugasan (opsi A); kolom tb_tes.kapasitas
# berisi angka dari data BPBD saja dan KOSONG bila tidak ada (kontrak §2.1: nilai bawaan tidak dipakai lagi).
# TEA tidak dibatasi kapasitas saat routing.
is_tes = fas["Jns_fasili"] == "TES"
median_tes = fas.loc[is_tes, "kapasitas_bpbd"].median()
fas["kapasitas"] = fas["kapasitas_bpbd"]
fas["kapasitas_sumber"] = np.where(fas["kapasitas_bpbd"].notna(), "BPBD 2025", "")

isi_ok = is_tes & fas["kapasitas"].isna() & fas["kapasitas_ok"].notna()
fas.loc[isi_ok, "kapasitas"] = fas.loc[isi_ok, "kapasitas_ok"]
fas.loc[isi_ok, "kapasitas_sumber"] = "BPBD 2019 (daftar resmi)"

isi_2019 = is_tes & fas["kapasitas"].isna() & fas["kapasitas_2019"].notna()
fas.loc[isi_2019, "kapasitas"] = fas.loc[isi_2019, "kapasitas_2019"]
fas.loc[isi_2019, "kapasitas_sumber"] = "BPBD 2019 (verifikasi)"

bukit = fas["Nama_Fasum"].str.contains(r"^(?:Bukit|Gunung)", case=False)
isi_jejak = is_tes & fas["kapasitas"].isna() & fas["luas_jejak_m2"].notna() & ~bukit
lantai = fas["lantai"].fillna(LANTAI_ASUMSI)
lantai_aman = (lantai - LANTAI_TERENDAM).clip(lower=1)
fas.loc[isi_jejak, "kapasitas"] = (fas["luas_jejak_m2"] * lantai_aman / M2_PER_ORANG).round()[isi_jejak]
fas.loc[isi_jejak, "kapasitas_sumber"] = "estimasi (jejak bangunan RTRW)"

kosong_tes = is_tes & fas["kapasitas"].isna()
fas.loc[kosong_tes, "kapasitas"] = median_tes
fas.loc[kosong_tes, "kapasitas_sumber"] = "estimasi (median TES BPBD)"
kosong_tea = (fas["Jns_fasili"] == "TEA") & fas["kapasitas"].isna()
fas.loc[kosong_tea, "kapasitas"] = 0.0
fas.loc[kosong_tea, "kapasitas_sumber"] = "tidak tersedia"
fas["kapasitas_data"] = np.where(fas["kapasitas_sumber"].str.startswith("BPBD"), fas["kapasitas"], np.nan)

# ID stabil: titik data 2025 diurutkan seperti sebelumnya; titik geokode menyusul dengan nomor berikutnya.
fas["_geo"] = fas["nama_geokode"].notna()
fas = fas.sort_values(["_geo", "Jns_fasili", "KEC", "KEL", "Nama_Fasum"]).reset_index(drop=True)
fas["facility_id"] = (fas["Jns_fasili"] + "_" + (fas.groupby("Jns_fasili").cumcount() + 1).astype(str).str.zfill(3))
fas = fas.sort_values(["Jns_fasili", "facility_id"]).reset_index(drop=True)

# Nama unik (syarat H-1). Dikerjakan setelah ID dibuat agar ID fasilitas lain tidak bergeser.
fas["nama_bpbd"] = fas["Nama_Fasum"]
# a) Nama & jenis sama dan berjarak <= GABUNG_JARAK_M: titik ganda untuk tempat yang sama, digabung.
#    Wakilnya titik berkapasitas BPBD 2025 (ID terkecil); kapasitasnya diambil yang terbesar dari BPBD 2025.
jumlah_digabung = 0
for _, grup in fas[fas["dipakai"] == 1].groupby([fas["Jns_fasili"], fas["Nama_Fasum"].str.lower()]):
    if len(grup) < 2:
        continue
    urut = grup.assign(_bpbd=grup["kapasitas_sumber"] != "BPBD 2025").sort_values(["_bpbd", "facility_id"])
    sisa = list(urut.index)
    while sisa:
        wakil = sisa.pop(0)
        dekat = [j for j in sisa if fas.geometry[wakil].distance(fas.geometry[j]) <= GABUNG_JARAK_M]
        if not dekat:
            continue
        kap_bpbd = fas.loc[[wakil] + dekat].query("kapasitas_sumber == 'BPBD 2025'")["kapasitas"]
        if len(kap_bpbd):
            fas.loc[wakil, ["kapasitas", "kapasitas_sumber", "kapasitas_data"]] = [kap_bpbd.max(), "BPBD 2025", kap_bpbd.max()]
        for j in dekat:
            jarak = fas.geometry[wakil].distance(fas.geometry[j])
            fas.loc[j, ["dipakai", "alasan_tidak_dipakai"]] = [
                0, f"Digabung ke {fas.at[wakil, 'facility_id']} (nama sama, berjarak {jarak:.0f} m)"]
            sisa.remove(j)
            jumlah_digabung += 1
# b) TES & TEA bernama sama (gedung dan halamannya): nama TEA diberi keterangan.
pakai = fas["dipakai"] == 1
kunci_nama = fas["Nama_Fasum"].str.lower()
nama_tes_aktif = set(kunci_nama[pakai & (fas["Jns_fasili"] == "TES")])
ganda_tea = pakai & (fas["Jns_fasili"] == "TEA") & kunci_nama.isin(nama_tes_aktif)
fas.loc[ganda_tea, "Nama_Fasum"] = fas.loc[ganda_tea, "Nama_Fasum"] + " (area evakuasi)"
# c) Nama sama di lokasi berbeda: tambahkan kelurahan, lalu nomor urut bila masih sama.
for tambahan in ("kelurahan", "nomor"):
    kunci_nama = fas["Nama_Fasum"].str.lower()
    ganda = pakai & kunci_nama.isin(kunci_nama[pakai][kunci_nama[pakai].duplicated()])
    for _, grup in fas[ganda].groupby(kunci_nama[ganda]):
        for urutan, (j, r) in enumerate(grup.sort_values("facility_id").iterrows(), start=1):
            fas.at[j, "Nama_Fasum"] = (f"{r.Nama_Fasum} ({judul(r.KEL)})" if tambahan == "kelurahan"
                                       else f"{r.Nama_Fasum} {urutan}")
nama_aktif = fas.loc[fas["dipakai"] == 1, "Nama_Fasum"].str.lower()
assert not nama_aktif.duplicated().any(), "Masih ada nama fasilitas ganda"
print(f"      Nama unik: {jumlah_digabung} titik ganda digabung, {ganda_tea.sum()} nama TEA diberi keterangan, "
      f"{(fas['Nama_Fasum'] != fas['nama_bpbd']).sum() - ganda_tea.sum()} nama dibedakan dengan kelurahan/nomor")

# Snap ke node terdekat.
tree = cKDTree(np.column_stack([x_node, y_node]))
jarak_snap, idx_snap = tree.query(np.column_stack([fas.geometry.x, fas.geometry.y]))
fas["node_idx"] = idx_snap
fas["snap_dist_m"] = jarak_snap
fas["akses_menit"] = menit(jarak_snap)
lonlat = gpd.GeoSeries(fas.geometry, crs=CRS_METER).to_crs("EPSG:4326")
fas["lon"], fas["lat"] = lonlat.x.to_numpy(), lonlat.y.to_numpy()

print(f"      TES dikeluarkan (verifikasi 2019): {tes_tak_layak.sum()} | TEA dikeluarkan (di landaan): {tea_di_landaan.sum()}")
print(f"      Kapasitas TES: " + ", ".join(f"{k} {v}" for k, v in fas.loc[fas['Jns_fasili'] == 'TES', 'kapasitas_sumber'].value_counts().items()))

# ==============================================================================
# 5. RUTE KE TES & TEA (REVERSE DIJKSTRA + SYARAT ARAH + JEMBATAN SEBAGAI CADANGAN)
# ==============================================================================
langkah("[5/9] Menghitung rute ke TES & TEA...")
aktif = fas[fas["dipakai"] == 1].reset_index(drop=True)
semua_node = np.arange(N)


def hitung_kandidat(sub):
    """Matriks biaya & ETA riil (K x N) dari setiap node ke setiap fasilitas di sub, setelah syarat arah."""
    node_unik, inv = np.unique(sub["node_idx"].to_numpy(), return_inverse=True)
    biaya_u, pred_u = pohon_rute(node_unik)
    eta_u = np.empty_like(biaya_u)
    jemb_u = np.zeros(biaya_u.shape, dtype=bool)
    for r in range(len(node_unik)):
        eta_u[r], jemb_u[r] = akumulasi_riil_baris(pred_u[r])
    akses = sub["akses_menit"].to_numpy()[:, None]
    biaya_k = biaya_u[inv] + akses
    eta_k = eta_u[inv] + akses
    # Aturan mutlak (K-B1): tujuan harus menjauh dari pantai, tidak boleh mendekat maupun sejajar.
    boleh = arah_boleh(sub["d_pantai_m"].to_numpy()[:, None], sub["x_m"].to_numpy()[:, None],
                       sub["y_m"].to_numpy()[:, None], semua_node[None, :])
    biaya_k = np.where(boleh & np.isfinite(biaya_k), biaya_k, INF)
    return biaya_k, eta_k, pred_u, inv, jemb_u


tes = aktif[aktif["Jns_fasili"] == "TES"].reset_index(drop=True)
tea = aktif[aktif["Jns_fasili"] == "TEA"].reset_index(drop=True)
biaya_tes, eta_tes, pred_tes, inv_tes, jemb_tes = hitung_kandidat(tes)
biaya_tea, eta_tea, pred_tea, inv_tea, jemb_tea = hitung_kandidat(tea)

# Peringkat TES (3 nama berbeda) per node; rank 2 dan 3 dibiarkan kosong bila tidak ada (kontrak §2.1).
# Catatan kompatibilitas: kolom rank_X_tes berisi NAMA gedung (unik), bukan tes_id.
nama_tes = tes["Nama_Fasum"].to_numpy()
urut_tes = np.argsort(biaya_tes, axis=0)
route_rows, rank1_tes = [], np.full(N, -1)
rank_tes = {}  # n -> [(indeks TES, eta riil)] untuk penugasan kapasitas
rank1_jembatan = np.zeros(N, dtype=bool)
rank1_mendekat = np.zeros(N)
# Rute TES hanya untuk node zona merah: warga di zona aman tidak perlu evakuasi vertikal.
for n in np.flatnonzero(is_safe == 0):
    pilihan = []
    for k in urut_tes[:, n]:
        if not np.isfinite(biaya_tes[k, n]):
            break
        pilihan.append(k)
        if len(pilihan) == 3:
            break
    if not pilihan:
        continue
    rank1_tes[n] = pilihan[0]
    rank_tes[n] = [(k, float(eta_tes[k, n])) for k in pilihan]
    baris = [int(node_ids[n])]
    for r, k in enumerate(pilihan):
        path = jalur(n, pred_tes[inv_tes[k]])
        if r == 0:
            rank1_mendekat[n] = mendekat_pantai_m(path)
        baris += [nama_tes[k], ",".join(str(node_ids[p]) for p in path), round(float(eta_tabel(eta_tes[k, n])), 2)]
    baris += [None, None, None] * (3 - len(pilihan))
    rank1_jembatan[n] = jemb_tes[inv_tes[pilihan[0]], n]
    route_rows.append(tuple(baris))

# TEA terdekat & alternatif (alternatif = TEA terdekat bila hanya ada satu yang memenuhi syarat).
urut_tea = np.argsort(biaya_tea, axis=0)
tea_route_rows, tea_r1, tea_r2 = [], np.full(N, -1), np.full(N, -1)
for n in range(N):
    k1 = urut_tea[0, n]
    if not np.isfinite(biaya_tea[k1, n]):
        continue
    k2 = urut_tea[1, n] if len(tea) > 1 and np.isfinite(biaya_tea[urut_tea[1, n], n]) else k1
    tea_r1[n], tea_r2[n] = k1, k2
    tea_route_rows.append((int(node_ids[n]), tea.at[k1, "facility_id"], tea.at[k2, "facility_id"]))


def tandai_rantai(next_hop, asal_mask):
    """Semua node yang dilalui rantai next_hop dari node-node asal (penelusuran pointer secara vektor)."""
    tanda = asal_mask.copy()
    while True:
        lanjut = next_hop[np.flatnonzero(tanda & (next_hop >= 0))]
        baru = tanda.copy()
        baru[lanjut] = True
        if np.array_equal(baru, tanda):
            return tanda
        tanda = baru


# tb_tea_next: transisi node untuk semua jalur r1/r2.
tea_next_rows = []
for k in range(len(tea)):
    nh = pred_tea[inv_tea[k]]
    tanda = tandai_rantai(nh, (tea_r1 == k) | (tea_r2 == k))
    for n in np.flatnonzero(tanda & (nh >= 0)):
        tea_next_rows.append((tea.at[k, "facility_id"], int(node_ids[n]), int(node_ids[nh[n]])))
print(f"      tb_routes: {len(route_rows):,} node (rank 2 kosong: {sum(r[4] is None for r in route_rows):,}, "
      f"rank 3 kosong: {sum(r[7] is None for r in route_rows):,}) | tb_tea_routes: {len(tea_route_rows):,} | "
      f"tb_tea_next: {len(tea_next_rows):,}")

# ==============================================================================
# 6. RUTE KE ZONA AMAN (KANTONG AMAN DIKELUARKAN + SYARAT ARAH PER WARGA)
# ==============================================================================
langkah("[6/9] Menghitung rute ke zona aman...")
# Kantong aman: komponen sel raster tanpa landaan (8-tetangga) yang tidak menyentuh tepi raster
# dan luasnya < LUAS_MIN_ZONA_AMAN_HA. Laut juga bernilai kosong, jadi tebing pantai yang
# bersambung dengan laut tidak dihitung kantong (aturan arah yang menyaringnya).
sel_aman = np.ma.getmaskarray(raster_bahaya)
label_aman, _ = ndimage.label(sel_aman, structure=np.ones((3, 3), dtype=int))
luas_sel_ha = abs(raster_src.transform.a * raster_src.transform.e) / 1e4
luas_komponen_ha = np.bincount(label_aman.ravel()) * luas_sel_ha
tepi = np.unique(np.concatenate([label_aman[0], label_aman[-1], label_aman[:, 0], label_aman[:, -1]]))
komponen_kantong = luas_komponen_ha < LUAS_MIN_ZONA_AMAN_HA
komponen_kantong[0] = False
komponen_kantong[tepi] = False
r_sel, c_sel, di_raster = r_tsunami.sel(x_node, y_node)
kantong_node = np.zeros(N, dtype=bool)
kantong_node[di_raster] = komponen_kantong[label_aman[r_sel[di_raster], c_sel[di_raster]]]
kantong_node &= is_safe == 1
tujuan_aman = (is_safe == 1) & ~kantong_node
print(f"      Kantong aman (< {LUAS_MIN_ZONA_AMAN_HA:.0f} ha, dikelilingi zona merah): {komponen_kantong.sum():,} "
      f"({luas_komponen_ha[komponen_kantong].sum():,.0f} ha) | node di kantong (bukan tujuan): {kantong_node.sum():,}")

# 6a. tb_safe_routes / tb_safe_next: satu pohon global untuk SEMUA node. Dipakai aplikasi untuk
#     safe_eta = 0 (penanda tujuan zona hijau, kontrak §2.1) dan kompatibilitas; tidak menjamin syarat arah.
safe_idx = np.flatnonzero(tujuan_aman)
biaya_aman, pred_aman, asal_aman = pohon_rute(safe_idx, min_only=True)
eta_aman, jemb_aman = akumulasi_riil_baris(pred_aman)
safe_route_rows, safe_next_rows = [], []


def nama_zona_aman(s):
    return f"Zona Aman - {judul(kel_node[s])}" if kel_node[s] else "Zona Aman"


# Node zona merah yang tujuan pohon global-nya tidak lolos syarat arah tidak diberi baris, supaya tabel ini
# tidak pernah menawarkan rute ke arah pantai; navigasinya lewat tb_safe_routes_v2 (atau TES/TEA).
ada_aman = np.isfinite(biaya_aman)
s_aman = np.where(ada_aman, asal_aman, 0)
lolos_arah = (is_safe == 1) | arah_boleh(d_pantai[s_aman], x_node[s_aman], y_node[s_aman], np.arange(N))
simpan_aman = ada_aman & lolos_arah
for n in np.flatnonzero(simpan_aman):
    s = int(asal_aman[n])
    safe_route_rows.append((int(node_ids[n]), int(node_ids[s]), nama_zona_aman(s), round(float(eta_tabel(eta_aman[n])), 2)))
for n in np.flatnonzero(tandai_rantai(pred_aman, simpan_aman) & (pred_aman >= 0)):
    safe_next_rows.append((int(node_ids[n]), int(node_ids[pred_aman[n]])))

# 6b. tb_safe_routes_v2 / tb_safe_next_v2: syarat arah (K-B1) dinilai per pasangan warga-tujuan.
#     Tujuan kandidat = "gerbang", yaitu node zona aman yang bertetangga dengan node bukan tujuan
#     (rute keluar zona selalu berakhir di gerbang pertama yang dicapainya). Untuk tiap node merah dipilih
#     gerbang berbiaya terkecil yang lolos syarat arah; rantainya disimpan per gerbang
#     (kolom kelompok = nomor gerbang), sama seperti tb_tea_next per TEA.
a_, b_ = kunci_arr[:, 0], kunci_arr[:, 1]
gerbang = np.unique(np.concatenate([a_[tujuan_aman[a_] & ~tujuan_aman[b_]], b_[tujuan_aman[b_] & ~tujuan_aman[a_]]]))
merah_idx = np.flatnonzero(is_safe == 0)
terbaik_biaya = np.full(len(merah_idx), INF)
terbaik_gerbang = np.full(len(merah_idx), -1)
UKURAN_POTONG = 400
for awal in range(0, len(gerbang), UKURAN_POTONG):
    potong = gerbang[awal:awal + UKURAN_POTONG]
    bt = dijkstra(W_tanpa, directed=True, indices=potong)[:, merah_idx]
    bd = dijkstra(W_dengan, directed=True, indices=potong)[:, merah_idx]
    b = np.where(np.isfinite(bt), bt, bd + BIAYA_CADANGAN_JEMBATAN)
    boleh = arah_boleh(d_pantai[potong][:, None], x_node[potong][:, None], y_node[potong][:, None], merah_idx[None, :])
    b = np.where(boleh, b, INF)
    j = np.argmin(b, axis=0)
    bj = b[j, np.arange(len(merah_idx))]
    lebih_baik = bj < terbaik_biaya
    terbaik_biaya[lebih_baik] = bj[lebih_baik]
    terbaik_gerbang[lebih_baik] = potong[j[lebih_baik]]

eta_aman2 = np.full(N, np.nan)
jemb_aman2 = np.zeros(N, dtype=bool)
mendekat_aman2 = np.full(N, np.nan)
safe2_route_rows, safe2_next_rows = [], []
gerbang_dipakai = np.unique(terbaik_gerbang[terbaik_gerbang >= 0])
for nomor, g in enumerate(gerbang_dipakai, start=1):
    asal = merah_idx[terbaik_gerbang == g]
    _, p_g = pohon_rute(np.array([g]))
    p_g = p_g[0]
    tanda = np.zeros(N, dtype=bool)
    tanda[asal] = True
    tanda = tandai_rantai(p_g, tanda)
    for n in np.flatnonzero(tanda & (p_g >= 0)):
        safe2_next_rows.append((nomor, int(node_ids[n]), int(node_ids[p_g[n]])))
    for n in asal:
        path = np.array(jalur(n, p_g))
        eta_aman2[n] = waktu_edge_vec(path[:-1], path[1:]).sum()
        jemb_aman2[n] = jembatan_edge_vec(path[:-1], path[1:]).any()
        mendekat_aman2[n] = mendekat_pantai_m(list(path))
        safe2_route_rows.append((int(node_ids[n]), nomor, int(node_ids[g]), nama_zona_aman(g),
                                 round(float(eta_tabel(eta_aman2[n])), 2), round(float(d_pantai[g]), 1),
                                 round(mendekat_aman2[n], 1)))
safe2_route_rows.sort()
print(f"      tb_safe_routes: {len(safe_route_rows):,} (node merah dibuang karena tujuan global tak lolos arah: "
      f"{(ada_aman & ~lolos_arah).sum():,}) | tb_safe_next: {len(safe_next_rows):,} | gerbang zona aman: "
      f"{len(gerbang):,} (dipakai {len(gerbang_dipakai):,}) | tb_safe_routes_v2: {len(safe2_route_rows):,} dari "
      f"{len(merah_idx):,} node merah | tb_safe_next_v2: {len(safe2_next_rows):,}")

# ==============================================================================
# 7. DEMAND PENDUDUK (KRB 2023-2027) & PENUGASAN BERBASIS KAPASITAS
# ==============================================================================
langkah("[7/9] Mendistribusikan penduduk terpapar (KRB) dan menghitung porsi tujuan...")
krb = pd.read_excel(FILE_KRB_TABEL, sheet_name="KELURAHAN", header=None, skiprows=7)
krb = krb[krb[0].astype(str).str.upper() == "TSUNAMI"].copy()
krb["KEL"] = krb[2].map(norm_kel)
jiwa_kel = dict(zip(krb["KEL"], pd.to_numeric(krb[8], errors="coerce").fillna(0)))

# Sebaran dasimetrik: jiwa terpapar per kelurahan dibagi menurut luas jejak bangunan RTRW yang berada
# di zona merah, lalu tiap bangunan ditempelkan ke node zona merah terdekat di kelurahan yang sama.
bx, by = shapely.get_x(pusat_bangunan.values), shapely.get_y(pusat_bangunan.values)
bangunan_merah = ~np.isnan(sampel_bahaya(bx, by))
gdf_bm = gpd.GeoDataFrame({"luas": luas_bangunan[bangunan_merah]},
                          geometry=pusat_bangunan.values[bangunan_merah], crs=CRS_METER)
gdf_bm = gpd.sjoin(gdf_bm, gdf_kel[["KEL", "geometry"]], how="inner", predicate="within")
demand = np.zeros(N)
kel_tanpa_bangunan, kel_tanpa_node_merah = [], []
for kel, jiwa in jiwa_kel.items():
    node_merah = np.flatnonzero((kel_node == kel) & (is_safe == 0))
    if len(node_merah) == 0:
        node_merah = np.flatnonzero(kel_node == kel)
        kel_tanpa_node_merah.append(kel)
    if len(node_merah) == 0:
        continue
    b = gdf_bm[gdf_bm["KEL"] == kel]
    if len(b) == 0:
        kel_tanpa_bangunan.append(kel)
        demand[node_merah] += jiwa / len(node_merah)
        continue
    _, terdekat = cKDTree(np.column_stack([x_node[node_merah], y_node[node_merah]])).query(
        np.column_stack([b.geometry.x, b.geometry.y]))
    bobot = np.bincount(terdekat, weights=b["luas"].to_numpy(), minlength=len(node_merah))
    demand[node_merah] += jiwa * bobot / bobot.sum()
print(f"      Penduduk terpapar KRB: {sum(jiwa_kel.values()):,.0f} jiwa di {len(jiwa_kel)} kelurahan | "
      f"terdistribusi: {demand.sum():,.0f} | bangunan di zona merah: {len(gdf_bm):,} | "
      f"node berpenghuni: {(demand > 0).sum():,}")

# Kandidat per node asal: 3 TES (berkapasitas), 2 TEA & zona aman (tak terbatas).
kand = []
for n, daftar in rank_tes.items():
    for k, eta in daftar:
        kand.append((n, "TES", tes.at[k, "facility_id"], eta))
for n in np.flatnonzero(tea_r1 >= 0):
    kand.append((n, "TEA", tea.at[tea_r1[n], "facility_id"], float(eta_tea[tea_r1[n], n])))
    kand.append((n, "TEA", tea.at[tea_r2[n], "facility_id"], float(eta_tea[tea_r2[n], n])))
# Zona aman: node merah memakai rute v2 (patuh aturan pantai); node aman berdemand memakai pohon global.
eta_aman_alok = np.where(is_safe == 0, eta_aman2, np.where(np.isfinite(biaya_aman), eta_aman, np.nan))
for n in np.flatnonzero(~np.isnan(eta_aman_alok)):
    kand.append((n, "ZONA_AMAN", "Zona Aman", float(eta_aman_alok[n])))
df_k = pd.DataFrame(kand, columns=["n", "jenis", "tujuan", "eta"]).drop_duplicates(["n", "jenis", "tujuan"])
df_k = df_k[demand[df_k["n"]] > 0]
# Greedy dua tahap: semua kandidat <= batas waktu dialokasikan dulu, lalu sisa warga memakai kandidat lain.
# Di antara kandidat yang sempat, keluar zona (TEA / zona aman) didahulukan sebelum TES (asumsi kerja K-B6:
# "bila sempat dalam 20 menit, keluar zona dulu; bila tidak, TES tercepat yang menjauh"), lalu urut ETA.
# TES penuh dilewati; TEA/zona aman selalu menampung sisa.
df_k["layak"] = df_k["eta"] <= BATAS_WAKTU_MENIT
df_k["urutan_jenis"] = np.where(df_k["layak"] & (df_k["jenis"] != "TES"), 0, 1)
df_k = df_k.sort_values(["layak", "urutan_jenis", "eta", "n", "tujuan"], ascending=[False, True, True, True, True])

kap_tes = dict(zip(tes["facility_id"], tes["kapasitas"]))
beban = {k: 0.0 for k in kap_tes}
sisa = demand.copy()
alokasi = {}
for n, jenis, tujuan, eta in df_k[["n", "jenis", "tujuan", "eta"]].itertuples(index=False):
    if sisa[n] <= 1e-9:
        continue
    jatah = min(sisa[n], max(0.0, kap_tes[tujuan] - beban[tujuan])) if jenis == "TES" else sisa[n]
    if jatah > 0:
        if jenis == "TES":
            beban[tujuan] += jatah
        sisa[n] -= jatah
        alokasi.setdefault(n, {}).setdefault((jenis, tujuan, eta), 0.0)
        alokasi[n][(jenis, tujuan, eta)] += jatah

nama_fas = dict(zip(fas["facility_id"], fas["Nama_Fasum"]))
share_rows = []
for n, d in alokasi.items():
    total = sum(d.values())
    for (jenis, tujuan, _), j in d.items():
        share_rows.append((int(node_ids[n]), jenis, nama_fas.get(tujuan, tujuan), j / total))

jiwa_selamat_20 = sum(j for d in alokasi.values() for (_, _, eta), j in d.items() if eta <= BATAS_WAKTU_MENIT)
jiwa_tanpa_tujuan = sisa.sum()

# ==============================================================================
# 8. POLIGON ZONA MERAH & ZONA AMAN (DARI RASTER BAHAYA TSUNAMI)
# ==============================================================================
langkah("[8/9] Membentuk poligon zona merah dan zona aman...")
mask_landaan = (~np.ma.getmaskarray(raster_bahaya)).astype(np.uint8)
poligon = [shape(g) for g, v in rasterio.features.shapes(mask_landaan, mask=mask_landaan.astype(bool),
                                                          transform=raster_src.transform) if v == 1]
landaan = gpd.GeoSeries(poligon, crs=raster_crs).to_crs(CRS_METER).union_all()
landaan = landaan.simplify(10).buffer(0)
inundation_rows, safe_zone_rows = [], []
for kel, geom in zip(gdf_kel["KEL"], gdf_kel.geometry):
    merah = geom.intersection(landaan)
    hijau = geom.difference(landaan).simplify(10)
    if not merah.is_empty and merah.area > 100:
        inundation_rows.append((judul(kel), "Tinggi", wkt_multipolygon(gpd.GeoSeries([merah], crs=CRS_METER).to_crs("EPSG:4326").iloc[0])))
    if not hijau.is_empty and hijau.area > 100:
        safe_zone_rows.append((judul(kel), None, wkt_multipolygon(gpd.GeoSeries([hijau], crs=CRS_METER).to_crs("EPSG:4326").iloc[0])))
print(f"      Zona merah: {len(inundation_rows)} poligon kelurahan | zona aman: {len(safe_zone_rows)}")

# ==============================================================================
# 9. TULIS SQLITE
# ==============================================================================
langkah(f"[9/9] Menulis {DB_PATH}...")
os.makedirs(DIR_HASIL, exist_ok=True)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# --- Tabel inti (kontrak DB aplikasi, siagapadang docs/PEMBAGIAN_TUGAS_BPBD.md §2.1) ---
# Kolom baru sesuai kontrak: tb_nodes.jarak_pantai_m (perlu penyesuaian NodeEntity di aplikasi),
# tb_tes.sumber/jarak_pantai_m/lantai, tb_tea.jarak_pantai_m, v_fasilitas_evakuasi.sumber, tb_bridge_edges.
cur.execute("CREATE TABLE tb_nodes (node_id INTEGER PRIMARY KEY, lat REAL, lon REAL, is_safe INTEGER DEFAULT 0, "
            "jarak_pantai_m INTEGER)")
cur.executemany("INSERT INTO tb_nodes VALUES (?, ?, ?, ?, ?)",
                [(int(node_ids[i]), float(lat[i]), float(lon[i]), int(is_safe[i]), int(round(float(d_pantai[i]))))
                 for i in range(N)])
cur.execute("CREATE INDEX idx_tb_nodes_lat_lon ON tb_nodes(lat, lon)")

# kapasitas: daya tampung dari data BPBD (2025 / daftar resmi 2019 / verifikasi 2019), KOSONG bila tidak ada.
cur.execute("CREATE TABLE tb_tes (tes_id TEXT PRIMARY KEY, nama_tes TEXT, zona TEXT, kapasitas REAL, lat REAL, lon REAL, "
            "sumber TEXT, jarak_pantai_m INTEGER, lantai INTEGER)")
cur.executemany("INSERT INTO tb_tes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r.facility_id, r.Nama_Fasum, judul(r.KEL), None if pd.isna(r.kapasitas_data) else float(r.kapasitas_data),
                  float(r.lat), float(r.lon), r.sumber, int(round(r.d_pantai_m)), None if pd.isna(r.lantai) else int(r.lantai))
                 for r in tes.itertuples()])

cur.execute("CREATE TABLE tb_routes (origin_node_id INTEGER PRIMARY KEY, rank_1_tes TEXT, rank_1_path TEXT, rank_1_eta REAL, "
            "rank_2_tes TEXT, rank_2_path TEXT, rank_2_eta REAL, rank_3_tes TEXT, rank_3_path TEXT, rank_3_eta REAL)")
cur.executemany("INSERT INTO tb_routes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", route_rows)

cur.execute("CREATE TABLE tb_edges (edge_id INTEGER PRIMARY KEY AUTOINCREMENT, u INTEGER, v INTEGER, length REAL, geometry TEXT)")
cur.executemany("INSERT INTO tb_edges (u, v, length, geometry) VALUES (?, ?, ?, ?)", edge_rows)

cur.execute("CREATE TABLE tb_inundation_zones (zone_id INTEGER PRIMARY KEY AUTOINCREMENT, nama_zona TEXT, tingkat_bahaya TEXT, geometry_wkt TEXT)")
cur.executemany("INSERT INTO tb_inundation_zones (nama_zona, tingkat_bahaya, geometry_wkt) VALUES (?, ?, ?)", inundation_rows)
cur.execute("CREATE TABLE tb_safe_zones (safe_zone_id INTEGER PRIMARY KEY AUTOINCREMENT, nama_zona TEXT, elevasi_m REAL, geometry_wkt TEXT)")
cur.executemany("INSERT INTO tb_safe_zones (nama_zona, elevasi_m, geometry_wkt) VALUES (?, ?, ?)", safe_zone_rows)

cur.execute("""CREATE TABLE tb_tea (
    tea_id TEXT PRIMARY KEY,
    kode_tea TEXT NOT NULL,
    sektor TEXT NOT NULL,
    nama_tea TEXT NOT NULL,
    kelurahan TEXT,
    kecamatan TEXT,
    tipe_fasilitas TEXT,
    kapasitas REAL NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    nearest_node_id INTEGER,
    rute_evakuasi TEXT,
    jarak_pantai_m INTEGER,
    sumber TEXT
)""")
cur.executemany("INSERT INTO tb_tea VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r.facility_id, r.facility_id.replace("_", " "), judul(r.KEC), r.Nama_Fasum, judul(r.KEL),
                  judul(r.KEC), "TEA", float(r.kapasitas), float(r.lat), float(r.lon),
                  int(node_ids[r.node_idx]), None, int(round(r.d_pantai_m)), r.sumber) for r in tea.itertuples()])
cur.execute("CREATE INDEX idx_tea_sektor ON tb_tea(sektor)")

cur.execute("CREATE TABLE tb_tea_routes (origin_node_id INTEGER PRIMARY KEY, nearest_tea_id TEXT, alt_tea_id TEXT)")
cur.executemany("INSERT INTO tb_tea_routes VALUES (?, ?, ?)", tea_route_rows)
cur.execute("CREATE INDEX idx_tea_routes_tea_id ON tb_tea_routes(nearest_tea_id)")

cur.execute("""CREATE TABLE tb_tea_next (
    tea_id       TEXT    NOT NULL,
    node_id      INTEGER NOT NULL,
    next_node_id INTEGER NOT NULL,
    PRIMARY KEY (tea_id, node_id)
) WITHOUT ROWID""")
cur.executemany("INSERT INTO tb_tea_next VALUES (?, ?, ?)", tea_next_rows)

# safe_zone_id merujuk ke tb_safe_zones (zona hijau kelurahan tempat node tujuan berada). Kolom ini
# dipakai aplikasi sejak dataset 2026.09.28 (JOIN ke tb_safe_zones untuk nama zona).
id_zona_aman = {nama: i + 1 for i, (nama, _, _) in enumerate(safe_zone_rows)}


def id_zona_node(node_id):
    return id_zona_aman.get(judul(kel_node[idx_of[str(node_id)]]))


cur.execute("CREATE TABLE tb_safe_routes (origin_node_id INTEGER PRIMARY KEY, safe_node_id INTEGER, safe_zone_nama TEXT, "
            "safe_eta REAL, safe_zone_id INTEGER)")
cur.executemany("INSERT INTO tb_safe_routes VALUES (?, ?, ?, ?, ?)", [r + (id_zona_node(r[1]),) for r in safe_route_rows])
cur.execute("CREATE TABLE tb_safe_next (node_id INTEGER, next_node_id INTEGER, PRIMARY KEY (node_id, next_node_id))")
cur.executemany("INSERT INTO tb_safe_next VALUES (?, ?)", safe_next_rows)

cur.execute("CREATE TABLE tb_route_shares (origin_node_id INTEGER, jenis TEXT, nama_tujuan TEXT, porsi REAL)")
cur.executemany("INSERT INTO tb_route_shares VALUES (?, ?, ?, ?)", share_rows)
cur.execute("CREATE INDEX idx_shares_origin ON tb_route_shares(origin_node_id)")

cur.execute("""CREATE VIEW v_fasilitas_evakuasi AS
SELECT tes_id AS facility_id, tes_id AS kode, nama_tes AS nama, 'TES' AS jenis, 'Vertikal' AS tipe_evakuasi,
       zona AS zona_sektor, kapasitas, lat, lon, sumber FROM tb_tes
UNION ALL
SELECT tea_id AS facility_id, kode_tea AS kode, nama_tea AS nama, 'TEA' AS jenis, 'Horizontal' AS tipe_evakuasi,
       sektor AS zona_sektor, kapasitas, lat, lon, sumber FROM tb_tea""")

# Ruas tb_edges yang memuat jembatan >= 20 m (kontrak H-4); aplikasi memberi keterangan "lewat jembatan".
cur.execute("CREATE TABLE tb_bridge_edges (edge_id INTEGER PRIMARY KEY)")
cur.executemany("INSERT INTO tb_bridge_edges VALUES (?)", [(int(j) + 1,) for j in np.flatnonzero(jembatan_besar_baris)])

# --- Tabel tambahan V4 ---
# Rute zona aman yang patuh syarat arah, per node zona merah. kelompok = nomor gerbang tujuan (kunci rantai);
# aplikasi menelusuri tb_safe_next_v2 dengan kelompok milik node asal sampai node tanpa next hop.
cur.execute("""CREATE TABLE tb_safe_routes_v2 (
    origin_node_id INTEGER PRIMARY KEY, kelompok INTEGER NOT NULL, safe_node_id INTEGER NOT NULL,
    safe_zone_nama TEXT, safe_eta REAL, safe_d_pantai_m REAL, mendekat_pantai_maks_m REAL, safe_zone_id INTEGER)""")
cur.executemany("INSERT INTO tb_safe_routes_v2 VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [r + (id_zona_node(r[2]),) for r in safe2_route_rows])
cur.execute("""CREATE TABLE tb_safe_next_v2 (
    kelompok     INTEGER NOT NULL,
    node_id      INTEGER NOT NULL,
    next_node_id INTEGER NOT NULL,
    PRIMARY KEY (kelompok, node_id)
) WITHOUT ROWID""")
cur.executemany("INSERT INTO tb_safe_next_v2 VALUES (?, ?, ?)", safe2_next_rows)

cur.execute("""CREATE TABLE tb_fasilitas_info (
    facility_id TEXT PRIMARY KEY, jenis TEXT, nama TEXT, kelurahan TEXT, kecamatan TEXT,
    dipakai INTEGER, alasan_tidak_dipakai TEXT, kapasitas REAL, kapasitas_sumber TEXT,
    d_pantai_m REAL, indeks_bahaya REAL, jumlah_lantai_2019 INTEGER, status_bpbd_2019 TEXT, nama_bpbd_2019 TEXT,
    kapasitas_2019 REAL, luas_jejak_bangunan_m2 REAL,
    nearest_node_id INTEGER, snap_dist_m REAL, lat REAL, lon REAL, nama_bpbd TEXT,
    sumber TEXT, nama_daftar_resmi_bpbd TEXT, lantai INTEGER, koordinat_sumber TEXT)""")
cur.executemany("INSERT INTO tb_fasilitas_info VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r.facility_id, r.Jns_fasili, r.Nama_Fasum, judul(r.KEL), judul(r.KEC), int(r.dipakai),
                  r.alasan_tidak_dipakai or None, float(r.kapasitas), r.kapasitas_sumber, round(float(r.d_pantai_m), 1),
                  None if np.isnan(r.indeks_bahaya) else round(float(r.indeks_bahaya), 4),
                  None if pd.isna(r.lantai_2019) else int(r.lantai_2019), r.status_2019, r.nama_2019,
                  None if pd.isna(r.kapasitas_2019) else float(r.kapasitas_2019),
                  None if pd.isna(r.luas_jejak_m2) else round(float(r.luas_jejak_m2), 1),
                  int(node_ids[r.node_idx]), round(float(r.snap_dist_m), 1), float(r.lat), float(r.lon), r.nama_bpbd,
                  r.sumber, r.nama_bpbd_ok, None if pd.isna(r.lantai) else int(r.lantai), r.koordinat_sumber)
                 for r in fas.itertuples()])

cur.execute("""CREATE TABLE tb_node_info (
    node_id INTEGER PRIMARY KEY, kelurahan TEXT, d_pantai_m REAL, indeks_bahaya REAL, demand_jiwa REAL,
    rute_tes_lewat_jembatan INTEGER, rute_aman_lewat_jembatan INTEGER,
    kantong_aman INTEGER, rute_tes_mendekat_pantai_m REAL, rute_aman_mendekat_pantai_m REAL)""")
jemb_aman_node = np.where(is_safe == 0, jemb_aman2, jemb_aman.astype(bool))
cur.executemany("INSERT INTO tb_node_info VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(int(node_ids[i]), judul(kel_node[i]) or None, round(float(d_pantai[i]), 1),
                  None if np.isnan(indeks_bahaya_node[i]) else round(float(indeks_bahaya_node[i]), 4),
                  round(float(demand[i]), 3), int(rank1_jembatan[i]), int(jemb_aman_node[i]), int(kantong_aman_i),
                  round(float(rank1_mendekat[i]), 1) if rank1_tes[i] >= 0 else None,
                  None if np.isnan(mendekat_aman2[i]) else round(float(mendekat_aman2[i]), 1))
                 for i, kantong_aman_i in zip(range(N), kantong_node)])

cur.execute("CREATE TABLE tb_jalur_resmi (u INTEGER, v INTEGER, PRIMARY KEY (u, v))")
cur.executemany("INSERT INTO tb_jalur_resmi VALUES (?, ?)",
                [(int(node_ids[a]), int(node_ids[b])) for (a, b) in kunci_arr[jalur_resmi]])

# Profil tsunami per kelurahan dari tabel KRB 2023-2027 (kolom sesuai urutan tabel BPBD).
kolom_krb = {3: "luas_bahaya_rendah_ha", 4: "luas_bahaya_sedang_ha", 5: "luas_bahaya_tinggi_ha", 6: "luas_bahaya_total_ha",
             7: "kelas_bahaya", 8: "jiwa_terpapar", 9: "jiwa_umur_rentan", 10: "jiwa_miskin", 11: "jiwa_disabilitas",
             12: "kelas_penduduk_terpapar", 15: "kerugian_total_juta_rp", 19: "kelas_kerentanan",
             22: "indeks_kesiapsiagaan", 23: "kelas_kesiapsiagaan", 24: "indeks_kapasitas", 25: "kelas_kapasitas",
             30: "indeks_risiko", 31: "kelas_risiko"}
tb_kel = krb[[1, 2] + list(kolom_krb)].rename(columns={1: "kecamatan", 2: "kelurahan", **kolom_krb})
tb_kel["kecamatan"] = tb_kel["kecamatan"].astype(str).map(judul)
tb_kel["node_zona_merah"] = [int(((kel_node == k) & (is_safe == 0)).sum()) for k in krb["KEL"]]
# Sisa pelanggaran yang tak terhindarkan: jiwa yang rute zona aman v2-nya sempat mendekati pantai
# lebih dari toleransi (jalan memang hanya ke arah itu) -> usulan lokasi TES/jalur baru ke BPBD.
mendekat_berarti = (is_safe == 0) & (np.nan_to_num(mendekat_aman2) > TOLERANSI_MENDEKAT_PANTAI_M)
tanpa_rute_aman = (is_safe == 0) & np.isnan(eta_aman2)
tb_kel["jiwa_rute_aman_mendekat_pantai"] = [round(float(demand[(kel_node == k) & mendekat_berarti].sum()), 1) for k in krb["KEL"]]
tb_kel["jiwa_tanpa_rute_aman"] = [round(float(demand[(kel_node == k) & tanpa_rute_aman].sum()), 1) for k in krb["KEL"]]
tb_kel.to_sql("tb_kelurahan_info", conn, index=False)

versi = ARGS.versi or datetime.now().strftime("%Y.%m.%d")
if not re.fullmatch(r"\d+(?:\.\d+)*", versi):
    sys.exit(f"[ERROR] Versi harus angka bertingkat (mis. 2026.10.12), bukan {versi!r}")
metadata = {
    "versi": versi,
    "sumber_tes_tea": "2_TES_TEA_Padang.shp (digitasi staf GIS BPBD atas kesepakatan Kelurahan Tangguh / latihan 2025)",
    "sumber_label_bpbd": "TES yang cocok dengan Daftar Shelter OK.xlsx sheet 'TES OK' (3 shelter + 59 bangunan potensial "
                         "Bidang RR 2019) diberi sumber BPBD; selebihnya WARGA (lapis 'Kesepakatan warga')",
    "sumber_garis_pantai": SUMBER_PANTAI,
    "sumber_jembatan": SUMBER_JEMBATAN,
    "sumber_zona_merah": "BPBD - KRB Kota Padang 2023-2027, raster Peta_Bahaya_Tsunami",
    "sumber_penduduk": "BPBD - KRB Kota Padang 2023-2027, penduduk terpapar tsunami per kelurahan",
    "sumber_verifikasi_gedung": "BPBD - Daftar Shelter OK.xlsx (verifikasi 2019: lantai & kapasitas)",
    "sumber_jalur_resmi": "BPBD - Jalur_evakuasi_Padang.shp (jalur per RT/RW Kelurahan Tangguh)",
    "sumber_sebaran_penduduk": "BPBD - Basemap.gdb Bangunan_AR (jejak bangunan RTRW di zona merah)",
    "jalur_resmi_faktor": str(JALUR_RESMI_FAKTOR),
    "m2_per_orang_estimasi_kapasitas": str(M2_PER_ORANG),
    "kecepatan_jalan_ms": str(KECEPATAN_JALAN_MS),
    "kecepatan_kolom_eta_ms": str(KECEPATAN_TABEL_MS),
    "catatan_eta": "rank_k_eta dan safe_eta disimpan pada 1,2 m/s (kontrak §2.1); waktu riil pada 0,894 m/s = eta x 1,2 / 0,894. "
                   "Batas 20 menit riil setara eta tabel <= 14,9 menit.",
    "arah_min_sin": f"{ARAH_MIN_SIN:.4f}",
    "arah_jarak_dekat_m": str(ARAH_JARAK_DEKAT_M),
    "jembatan_min_m": str(JEMBATAN_MIN_M),
    "batas_waktu_menit": str(BATAS_WAKTU_MENIT),
    "toleransi_mendekat_pantai_m": str(TOLERANSI_MENDEKAT_PANTAI_M),
    "penalti_mendekat_pantai": str(PENALTI_MENDEKAT_PANTAI),
    "bobot_per_meter_mendekat_pantai": str(BOBOT_PER_METER_MENDEKAT_PANTAI),
    "penalti_jembatan": str(PENALTI_JEMBATAN),
    "gabung_jarak_m": str(GABUNG_JARAK_M),
    "luas_min_zona_aman_ha": str(LUAS_MIN_ZONA_AMAN_HA),
    "catatan_rute_aman": "Navigasi zona aman: tb_safe_routes_v2 + tb_safe_next_v2 (kelompok milik node asal), tujuan lolos "
                         "syarat arah. tb_safe_routes (semua node, safe_eta = 0 di tujuan zona hijau) untuk status tiba; "
                         "rantainya tidak menjamin syarat arah.",
    "catatan_tingkat_bahaya": "tb_inundation_zones.tingkat_bahaya bernilai 'Tinggi' untuk seluruh zona merah (peta evakuasi hanya merah/hijau)",
}
cur.execute("CREATE TABLE tb_metadata (kunci TEXT PRIMARY KEY, nilai TEXT)")
cur.executemany("INSERT INTO tb_metadata VALUES (?, ?)", list(metadata.items()))

conn.commit()
cur.execute("VACUUM")
conn.close()

sha = hashlib.sha256(open(DB_PATH, "rb").read()).hexdigest()
ukuran = os.path.getsize(DB_PATH)

# Zip dengan tanggal tetap supaya checksum zip ikut deterministik.
info = zipfile.ZipInfo(os.path.basename(DB_PATH), date_time=(1980, 1, 1, 0, 0, 0))
info.compress_type = zipfile.ZIP_DEFLATED
with zipfile.ZipFile(ZIP_PATH, "w") as zf:
    with open(DB_PATH, "rb") as f:
        zf.writestr(info, f.read(), compresslevel=9)
sha_zip = hashlib.sha256(open(ZIP_PATH, "rb").read()).hexdigest()
with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
    json.dump({
        "version": versi,
        "filename": os.path.basename(ZIP_PATH),
        "size_bytes": os.path.getsize(ZIP_PATH),
        "checksum_sha256": sha_zip.upper(),
        "db_filename": os.path.basename(DB_PATH),
        "db_size_bytes": ukuran,
        "db_checksum_sha256": sha.upper(),
        "description": "Siaga Padang V4 Database (data BPBD KRB 2023-2027, TES/TEA 2025, aturan evakuasi BPBD)",
    }, f, indent=2)
    f.write("\n")
with open(MANIFEST_ANDROID_PATH, "w", encoding="utf-8") as f:
    json.dump({"version": versi, "checksum": sha, "size_bytes": ukuran}, f, indent=2)
    f.write("\n")

# ==============================================================================
# KELUARAN PENDUKUNG: DAFTAR TES/TEA (H-1) & PETA CELAH (H-7)
# ==============================================================================
total_jiwa = demand.sum()
merah = is_safe == 0
# Daftar TES/TEA bersih: nama unik, koordinat, sumber, daya tampung, lantai.
kol_csv = ["facility_id", "Jns_fasili", "Nama_Fasum", "nama_bpbd", "sumber", "dipakai", "alasan_tidak_dipakai", "KEL", "KEC",
           "lat", "lon", "kapasitas_data", "kapasitas_sumber", "lantai", "d_pantai_m", "nama_bpbd_ok", "koordinat_sumber"]
daftar = fas[kol_csv].rename(columns={"Jns_fasili": "jenis", "Nama_Fasum": "nama", "nama_bpbd": "nama_asli",
                                      "KEL": "kelurahan", "KEC": "kecamatan", "kapasitas_data": "kapasitas",
                                      "d_pantai_m": "jarak_pantai_m", "nama_bpbd_ok": "nama_daftar_resmi_bpbd"})
daftar["kelurahan"] = daftar["kelurahan"].map(judul)
daftar["kecamatan"] = daftar["kecamatan"].map(judul)
daftar["kapasitas_sumber"] = np.where(daftar["kapasitas"].notna(), daftar["kapasitas_sumber"], "")
daftar["jarak_pantai_m"] = daftar["jarak_pantai_m"].round().astype(int)
daftar["lantai"] = daftar["lantai"].astype("Int64")
daftar["lat"], daftar["lon"] = daftar["lat"].round(7), daftar["lon"].round(7)
daftar.to_csv(os.path.join(DIR_HASIL, "daftar_tes_tea.csv"), index=False, encoding="utf-8")
# Daftar resmi BPBD 2019 yang tidak punya titik di data 2025 (perlu koordinat dari BPBD).
cocok_ok = set(fas["nama_bpbd_ok"].dropna())
tanpa_titik = df_ok[~df_ok["nama_ok"].isin(cocok_ok)][["nama_ok", "alamat_ok", "status_ok", "lantai_ok", "kapasitas_ok"]]
tanpa_titik.columns = ["nama", "alamat", "status", "lantai", "kapasitas"]
tanpa_titik.to_csv(os.path.join(DIR_HASIL, "bpbd_2019_tanpa_titik.csv"), index=False, encoding="utf-8")

# Peta celah (H-7): waktu riil (0,894 m/s) ke tujuan tercepat yang lolos aturan, per node zona merah.
eta_min = np.full(N, INF)
for n, daftar_k in rank_tes.items():
    eta_min[n] = min(eta for _, eta in daftar_k)
ada_tea = np.flatnonzero(tea_r1 >= 0)
eta_min[ada_tea] = np.minimum(eta_min[ada_tea], eta_tea[tea_r1[ada_tea], ada_tea])
eta_min = np.fmin(eta_min, np.where(np.isnan(eta_aman2), INF, eta_aman2))
celah_rows = []
for kel in krb["KEL"]:
    m = merah & (kel_node == kel)
    if not m.any():
        continue
    celah_rows.append({"kelurahan": judul(kel), "kecamatan": judul(gdf_kel.loc[gdf_kel["KEL"] == kel, "KEC"].iloc[0])
                       if (gdf_kel["KEL"] == kel).any() else "",
                       "simpul_zona_merah": int(m.sum()),
                       "simpul_tidak_sempat_20_mnt": int((m & (eta_min > 20)).sum()),
                       "simpul_tidak_sempat_30_mnt": int((m & (eta_min > 30)).sum()),
                       "jiwa_terpapar": round(float(demand[m].sum())),
                       "jiwa_tidak_sempat_20_mnt": round(float(demand[m & (eta_min > 20)].sum())),
                       "jiwa_tidak_sempat_30_mnt": round(float(demand[m & (eta_min > 30)].sum()))})
celah = pd.DataFrame(celah_rows).sort_values("jiwa_tidak_sempat_20_mnt", ascending=False)
celah.to_csv(os.path.join(DIR_HASIL, "peta_celah_kelurahan.csv"), index=False, encoding="utf-8")

# ==============================================================================
# LAPORAN
# ==============================================================================
tanpa_tes = merah & (rank1_tes < 0)
print("\n" + "=" * 80)
print("LAPORAN BUILD")
print("=" * 80)
print(f"Kecepatan jalan                  : {KECEPATAN_JALAN_MS} m/s ({KECEPATAN_JALAN_MS * 3.6:.2f} km/jam), batas {BATAS_WAKTU_MENIT:.0f} menit; "
      f"kolom ETA disimpan pada {KECEPATAN_TABEL_MS} m/s")
print(f"TES dipakai / TEA dipakai        : {len(tes)} / {len(tea)} | TES sumber BPBD: {(tes['sumber'] == 'BPBD').sum()}, "
      f"WARGA: {(tes['sumber'] == 'WARGA').sum()} | daftar resmi BPBD tanpa titik: {len(tanpa_titik)}")
print(f"TES tanpa daya tampung dari data BPBD (kolom kapasitas kosong): {tes['kapasitas_data'].isna().sum()}")
print(f"Node zona merah tanpa TES valid  : {tanpa_tes.sum():,} dari {merah.sum():,} (arahan: TEA / zona aman)")
print(f"Node zona merah tanpa tujuan apa pun yang lolos syarat arah: {(merah & ~np.isfinite(eta_min)).sum():,}")
for w in (20, 30):
    print(f"Tidak sempat {w} menit (0,894 m/s): {(merah & (eta_min > w)).sum() / merah.sum() * 100:.1f}% node zona merah, "
          f"{demand[merah & (eta_min > w)].sum():,.0f} jiwa ({demand[merah & (eta_min > w)].sum() / total_jiwa * 100:.1f}%)")
print(f"Jiwa dengan tujuan <= {BATAS_WAKTU_MENIT:.0f} menit (penugasan): {jiwa_selamat_20:,.0f} dari {total_jiwa:,.0f} "
      f"({jiwa_selamat_20 / max(total_jiwa, 1) * 100:.1f}%) | belum teralokasi: {jiwa_tanpa_tujuan:,.0f}")
print(f"Rute cadangan lewat jembatan >= {JEMBATAN_MIN_M:.0f} m: TES rank-1 {rank1_jembatan[merah].sum():,} node "
      f"({demand[rank1_jembatan & merah].sum():,.0f} jiwa) | zona aman v2 {jemb_aman2[merah].sum():,} node")
v2_ada = merah & ~np.isnan(mendekat_aman2)
print(f"Rute zona aman v2: {v2_ada.sum():,} dari {merah.sum():,} node merah | tanpa rute: {tanpa_rute_aman.sum():,} "
      f"({demand[tanpa_rute_aman].sum():,.0f} jiwa)")
for ambang in (TOLERANSI_MENDEKAT_PANTAI_M, 200.0):
    print(f"Rute sempat mendekati pantai > {ambang:.0f} m : TES rank-1 {(rank1_mendekat[merah & (rank1_tes >= 0)] > ambang).mean() * 100:.1f}% node | "
          f"zona aman v2 {(mendekat_aman2[v2_ada] > ambang).mean() * 100:.1f}% node")
print("Kelurahan dengan jiwa terbanyak yang tidak sempat 20 menit: "
      + ", ".join(f"{r.kelurahan} ({r.jiwa_tidak_sempat_20_mnt:,})" for r in celah.head(6).itertuples()))
tes_rank1 = [r[2] for r in route_rows]
pasangan_resmi = {(int(node_ids[a]), int(node_ids[b])) for a, b in kunci_arr[jalur_resmi]}
ruas_rute = [(min(int(p), int(q)), max(int(p), int(q))) for path in tes_rank1 for p, q in zip(path.split(",")[:-1], path.split(",")[1:])]
pasangan_resmi |= {(b, a) for a, b in pasangan_resmi}
print(f"Ruas rute TES rank-1 yang berada di jalur evakuasi resmi: {sum(r in pasangan_resmi for r in ruas_rute) / max(len(ruas_rute), 1) * 100:.1f}%")
if kel_tanpa_bangunan:
    print(f"Kelurahan tanpa jejak bangunan di zona merah (demand dibagi rata): {', '.join(kel_tanpa_bangunan)}")
if kel_tanpa_node_merah:
    print(f"Kelurahan KRB tanpa node zona merah (demand dibagi ke semua node): {', '.join(kel_tanpa_node_merah)}")
bukit_tes = fas[(fas["Jns_fasili"] == "TES") & fas["Nama_Fasum"].str.contains(r"^(?:Bukit|Gunung)", case=False)]
if len(bukit_tes):
    print(f"Perlu dicek: {len(bukit_tes)} titik berlabel TES tapi bernama bukit/gunung: "
          f"{', '.join(sorted(bukit_tes['Nama_Fasum'].unique()))}")
tidak = fas[fas["dipakai"] == 0]
if len(tidak):
    print("Fasilitas dikeluarkan dari routing:")
    for r in tidak.itertuples():
        print(f"  - {r.facility_id} {r.Nama_Fasum} ({judul(r.KEL)}): {r.alasan_tidak_dipakai}")
print(f"TES bersumber BPBD (cocok daftar resmi 2019): " + ", ".join(sorted(tes.loc[tes["sumber"] == "BPBD", "Nama_Fasum"])))
print(f"\nDatabase  : {DB_PATH} ({ukuran / 1024 / 1024:.2f} MB)")
print(f"SHA-256   : {sha}")
print(f"Paket     : {ZIP_PATH} ({os.path.getsize(ZIP_PATH) / 1024 / 1024:.2f} MB), manifest: {MANIFEST_PATH}, {MANIFEST_ANDROID_PATH}")
print(f"Versi     : {versi}")
print(f"Waktu     : {time.time() - start_total:.1f} detik")
print("=" * 80)
