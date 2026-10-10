"""
BUILDER DATABASE SIAGA PADANG V4 (DATA BPBD 2023-2027 & ATURAN EVAKUASI BPBD)

Menggantikan rantai lama core.py -> build_db_v2_with_tea.py -> spatial/1..4 (diarsipkan di legacy/pipeline_db/).
Seluruh aturan mengacu ke docs/aturan_evakuasi_bpbd.md.

Sumber data (folder "Data BPBD/", rincian & daftar data yang sengaja tidak dipakai: docs/build_db_v4.md):
  - SHP kecamatan/2_TES_TEA_Padang.shp      : titik TES & TEA hasil digitasi BPBD (Kelurahan Tangguh / Drill 2025)
  - SHP kecamatan/Jalur_evakuasi_Padang.shp : jalur evakuasi resmi per RT/RW (diutamakan saat routing)
  - KRB .../03_TEMATIK/Bahaya.gdb            : raster Peta_Bahaya_Tsunami (zona merah) & Peta_Bahaya_Gempabumi (jembatan)
  - KRB .../02_BASEMAP/Basemap.gdb           : batas kelurahan, batimetri (garis pantai), sungai, jejak bangunan
  - KRB .../04_TABEL/FINAL MATRIKS ...xlsx   : profil tsunami per kelurahan (penduduk terpapar, kelompok rentan, risiko)
  - Daftar Shelter OK.xlsx                   : verifikasi BPBD 2019 (jumlah lantai & kapasitas)
Graf jalan: padang_full.graphml (OSM).

Keluaran: ranah_siaga_v4.db. Skema tabel lama dipertahankan persis (Android memakai Room);
informasi baru ditaruh di tabel tambahan (tb_fasilitas_info, tb_node_info, tb_kelurahan_info,
tb_jembatan_sungai, tb_jalur_resmi, tb_metadata).
"""
import sys
import os
import re
import time
import sqlite3
import hashlib
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
from scipy.spatial import cKDTree
from pyproj import Transformer

sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# KONFIGURASI (rujukan: docs/aturan_evakuasi_bpbd.md)
# ==============================================================================
# Kecepatan berjalan orang paling lemah: 2 mph = 3,22 km/jam (FEMA P-646), dipakai BPBD
# untuk radius layanan 1 km / 20 menit (bagian 4).
KECEPATAN_JALAN_MS = 0.894
# Batas waktu evakuasi skenario terburuk BPBD (bagian 3).
BATAS_WAKTU_MENIT = 20.0
# Aturan menjauhi pantai (bagian 5.1.1): ruas yang mendekati pantai lebih dari toleransi diberi penalti.
TOLERANSI_MENDEKAT_PANTAI_M = 50.0
PENALTI_MENDEKAT_PANTAI = 10.0
# Aturan jembatan (bagian 5.2.1): jembatan sungai diberi penalti, bukan dihapus.
PENALTI_JEMBATAN_SUNGAI = 20.0
# TES dengan jumlah lantai <= nilai ini (menurut verifikasi BPBD 2019) dikeluarkan (bagian 6.1).
LANTAI_MAKS_TIDAK_LAYAK = 2
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
RASTER_GEMPA = "OpenFileGDB:" + os.path.join(DIR_KRB, "03_TEMATIK", "Bahaya.gdb") + ":Peta_Bahaya_Gempabumi"
FILE_KRB_TABEL = os.path.join(DIR_KRB, "04_TABEL", "FINAL MATRIKS KRB KOTA PADANG - DOKUMEN.xlsx")
FILE_SHELTER_2019 = os.path.join(DIR_BPBD, "Daftar Shelter OK.xlsx")
FILE_GRAF = "padang_full.graphml"
DB_PATH = "ranah_siaga_v4.db"

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


def menit(meter):
    return meter / KECEPATAN_JALAN_MS / 60.0


def bulatkan_wkt(geom, desimal=6):
    return shapely.set_precision(geom, 10 ** -desimal).wkt if geom is not None else None


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

laut = gpd.read_file(FILE_BASEMAP, layer="Bathimetri_Padang").to_crs(CRS_METER).union_all()
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

    def sampel(self, x_m, y_m):
        rx, ry = self.ke_raster.transform(np.asarray(x_m, dtype=float), np.asarray(y_m, dtype=float))
        rows, cols = rasterio.transform.rowcol(self.src.transform, rx, ry)
        rows, cols = np.atleast_1d(rows), np.atleast_1d(cols)
        hasil = np.full(rows.shape, np.nan)
        di_dalam = (rows >= 0) & (rows < self.src.height) & (cols >= 0) & (cols < self.src.width)
        nilai = self.data[rows[di_dalam], cols[di_dalam]]
        hasil[di_dalam] = np.where(np.ma.getmaskarray(nilai), np.nan, np.ma.getdata(nilai))
        return hasil


r_tsunami = Raster(RASTER_TSUNAMI)
r_gempa = Raster(RASTER_GEMPA)
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
# 3. RUAS JALAN: BOBOT BERARAH (PENALTI MENDEKATI PANTAI & JEMBATAN SUNGAI)
# ==============================================================================
langkah("[3/9] Menyusun bobot ruas berarah (aturan pantai, jembatan, jalur resmi)...")
pasangan = {}
edge_rows = []
for u, v, k, data in G.edges(keys=True, data=True):
    panjang = bersihkan_angka_osm(data.get("length", 50.0))
    geom_str = str(data.get("geometry", ""))
    edge_rows.append((int(u), int(v), float(panjang), geom_str))
    iu, iv = idx_of[u], idx_of[v]
    if iu == iv:
        continue
    kunci = (min(iu, iv), max(iu, iv))
    jembatan = "yes" in str(data.get("bridge", "")) or "viaduct" in str(data.get("bridge", ""))
    lama = pasangan.get(kunci)
    if lama is None or panjang < lama[0]:
        pasangan[kunci] = (panjang, jembatan, geom_str)

kunci_arr = np.array(list(pasangan.keys()))
nilai_pasangan = list(pasangan.values())
panjang_arr = np.array([p[0] for p in nilai_pasangan])
jembatan_arr = np.array([p[1] for p in nilai_pasangan])

# Geometri ruas dalam meter (satu kali proyeksi untuk semua koordinat).
garis_derajat = np.array([shapely_wkt.loads(p[2]) if p[2].startswith("LINESTRING")
                          else LineString([(lon[a], lat[a]), (lon[b], lat[b])])
                          for p, (a, b) in zip(nilai_pasangan, kunci_arr)], dtype=object)
garis_ruas = shapely.transform(garis_derajat, lambda c: np.column_stack(ke_meter.transform(c[:, 0], c[:, 1])))

# Jembatan sungai = ruas bertag bridge yang memotong poligon sungai BPBD (gorong-gorong tidak kena).
jembatan_sungai = np.zeros(len(kunci_arr), dtype=bool)
jembatan_sungai[jembatan_arr] = shapely.intersects(garis_ruas[jembatan_arr], sungai)
tengah_ruas = shapely.line_interpolate_point(garis_ruas, 0.5, normalized=True)
gempa_jembatan = r_gempa.sampel(shapely.get_x(tengah_ruas), shapely.get_y(tengah_ruas))

# Jalur evakuasi resmi: >= 80% titik sampel ruas (5 titik) berada dekat jalur BPBD.
fraksi = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
sampel_titik = np.concatenate([shapely.line_interpolate_point(garis_ruas, f, normalized=True) for f in fraksi])
dekat = pohon_jalur.query(sampel_titik, predicate="dwithin", distance=JALUR_RESMI_JARAK_M)
titik_dekat = np.zeros(len(sampel_titik), dtype=bool)
titik_dekat[np.unique(dekat[0])] = True
jalur_resmi = titik_dekat.reshape(len(fraksi), -1).mean(axis=0) >= 0.8
print(f"      Ruas unik: {len(kunci_arr):,} | bertag jembatan: {jembatan_arr.sum():,} | "
      f"jembatan sungai (diberi penalti): {jembatan_sungai.sum():,} | di jalur evakuasi resmi: {jalur_resmi.sum():,}")

# Dua arah untuk setiap ruas.
src = np.concatenate([kunci_arr[:, 0], kunci_arr[:, 1]])
dst = np.concatenate([kunci_arr[:, 1], kunci_arr[:, 0]])
waktu_riil = np.concatenate([menit(panjang_arr)] * 2)
lewat_jembatan = np.concatenate([jembatan_sungai] * 2)
di_jalur_resmi = np.concatenate([jalur_resmi] * 2)
mendekat = (d_pantai[src] - d_pantai[dst]) > TOLERANSI_MENDEKAT_PANTAI_M
biaya = (waktu_riil
         * np.where(mendekat, PENALTI_MENDEKAT_PANTAI, 1.0)
         * np.where(lewat_jembatan, PENALTI_JEMBATAN_SUNGAI, 1.0)
         * np.where(di_jalur_resmi, JALUR_RESMI_FAKTOR, 1.0))

# Matriks transpose: Dijkstra dari tujuan pada graf terbalik = biaya dari setiap node MENUJU tujuan.
# Predecessor pada graf terbalik = node berikutnya (next hop) pada rute asli.
W_balik = csr_matrix((biaya, (dst, src)), shape=(N, N))


def pohon_rute(sumber_idx):
    """Kembalikan (biaya, next_hop) per tujuan. next_hop[n] = node berikutnya dari n menuju tujuan."""
    return dijkstra(W_balik, directed=True, indices=sumber_idx, return_predecessors=True)


def akumulasi_riil_baris(next_hop):
    """Waktu tempuh riil (menit, tanpa penalti) & flag lewat jembatan sungai sepanjang pohon rute (pointer jumping)."""
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


def jalur(n, next_hop):
    path = [n]
    while next_hop[path[-1]] >= 0:
        path.append(int(next_hop[path[-1]]))
    return path


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
fas = gpd.sjoin(fas, gdf_kel, how="left", predicate="within").drop(columns="index_right")
fas["KEL"] = fas["KEL"].fillna(fas["kelurahan"].map(norm_kel))
fas["KEC"] = fas["KEC"].fillna(fas["Kecamatan"].map(norm_kel))
print(f"      Titik sumber: {jumlah_awal} | setelah buang duplikat persis: {len(fas)} "
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


def cocokkan_2019(nama):
    n = norm_nama(nama)
    angka = re.findall(r"\d+", n)
    # Nomor sekolah/gedung harus sama persis (SMPN 36 bukan SMPN 3).
    calon = df19[df19["norm"].map(lambda m: re.findall(r"\d+", m) == angka)]
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

# Jejak bangunan RTRW yang memuat (atau terdekat <= 25 m dari) titik TES.
idx_fas, idx_bgn = pohon_bangunan.query_nearest(fas.geometry.values, max_distance=JARAK_MAKS_JEJAK_BANGUNAN_M, all_matches=False)
fas["luas_jejak_m2"] = np.nan
fas.iloc[idx_fas, fas.columns.get_loc("luas_jejak_m2")] = luas_bangunan[idx_bgn]

x_fas, y_fas = fas.geometry.x.to_numpy(), fas.geometry.y.to_numpy()
fas["indeks_bahaya"] = sampel_bahaya(x_fas, y_fas)
fas["d_pantai_m"] = shapely.distance(fas.geometry.values, laut)

# Kelayakan untuk routing.
fas["dipakai"] = 1
fas["alasan_tidak_dipakai"] = ""
# Hanya jumlah lantai yang dipakai sebagai syarat keluar; status "tidak potensial" 2019 punya alasan lain
# (mis. masih dibangun, kapasitas staf saja) yang bisa sudah berubah, jadi hanya disimpan sebagai info.
tes_tak_layak = (fas["Jns_fasili"] == "TES") & (pd.to_numeric(fas["lantai_2019"], errors="coerce") <= LANTAI_MAKS_TIDAK_LAYAK)
fas.loc[tes_tak_layak, ["dipakai", "alasan_tidak_dipakai"]] = [0, f"Verifikasi BPBD 2019: <= {LANTAI_MAKS_TIDAK_LAYAK} lantai"]
tea_di_landaan = (fas["Jns_fasili"] == "TEA") & fas["indeks_bahaya"].notna()
fas.loc[tea_di_landaan, ["dipakai", "alasan_tidak_dipakai"]] = [0, "TEA berada di dalam area landaan tsunami"]

# Kapasitas TES berurutan: BPBD 2025 -> verifikasi BPBD 2019 -> estimasi jejak bangunan -> median TES BPBD.
# TEA tidak dibatasi kapasitas saat routing.
is_tes = fas["Jns_fasili"] == "TES"
median_tes = fas.loc[is_tes, "kapasitas_bpbd"].median()
fas["kapasitas"] = fas["kapasitas_bpbd"]
fas["kapasitas_sumber"] = np.where(fas["kapasitas_bpbd"].notna(), "BPBD 2025", "")

isi_2019 = is_tes & fas["kapasitas"].isna() & fas["kapasitas_2019"].notna()
fas.loc[isi_2019, "kapasitas"] = fas.loc[isi_2019, "kapasitas_2019"]
fas.loc[isi_2019, "kapasitas_sumber"] = "BPBD 2019 (verifikasi)"

bukit = fas["Nama_Fasum"].str.contains(r"^(?:Bukit|Gunung)", case=False)
isi_jejak = is_tes & fas["kapasitas"].isna() & fas["luas_jejak_m2"].notna() & ~bukit
lantai = pd.to_numeric(fas["lantai_2019"], errors="coerce").fillna(LANTAI_ASUMSI)
lantai_aman = (lantai - LANTAI_MAKS_TIDAK_LAYAK).clip(lower=1)
fas.loc[isi_jejak, "kapasitas"] = (fas["luas_jejak_m2"] * lantai_aman / M2_PER_ORANG).round()[isi_jejak]
fas.loc[isi_jejak, "kapasitas_sumber"] = "estimasi (jejak bangunan RTRW)"

kosong_tes = is_tes & fas["kapasitas"].isna()
fas.loc[kosong_tes, "kapasitas"] = median_tes
fas.loc[kosong_tes, "kapasitas_sumber"] = "estimasi (median TES BPBD)"
kosong_tea = (fas["Jns_fasili"] == "TEA") & fas["kapasitas"].isna()
fas.loc[kosong_tea, "kapasitas"] = 0.0
fas.loc[kosong_tea, "kapasitas_sumber"] = "tidak tersedia"

# ID stabil.
fas = fas.sort_values(["Jns_fasili", "KEC", "KEL", "Nama_Fasum"]).reset_index(drop=True)
fas["facility_id"] = (fas["Jns_fasili"] + "_" + (fas.groupby("Jns_fasili").cumcount() + 1).astype(str).str.zfill(3))

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
# 5. RUTE KE TES & TEA (REVERSE DIJKSTRA + ATURAN MENJAUHI PANTAI)
# ==============================================================================
langkah("[5/9] Menghitung rute ke TES & TEA...")
aktif = fas[fas["dipakai"] == 1].reset_index(drop=True)


def hitung_kandidat(sub):
    """Matriks biaya & ETA riil (K x N) dari setiap node ke setiap fasilitas di sub, setelah filter pantai."""
    node_unik, inv = np.unique(sub["node_idx"].to_numpy(), return_inverse=True)
    biaya_u, pred_u = pohon_rute(node_unik)
    eta_u = np.empty_like(biaya_u)
    jemb_u = np.zeros(biaya_u.shape, dtype=bool)
    for r in range(len(node_unik)):
        eta_u[r], jemb_u[r] = akumulasi_riil_baris(pred_u[r])
    akses = sub["akses_menit"].to_numpy()[:, None]
    biaya_k = biaya_u[inv] + akses
    eta_k = eta_u[inv] + akses
    # Aturan mutlak: tujuan harus lebih jauh dari pantai daripada posisi warga.
    boleh = sub["d_pantai_m"].to_numpy()[:, None] > d_pantai[None, :]
    biaya_k = np.where(boleh & np.isfinite(biaya_k), biaya_k, INF)
    return biaya_k, eta_k, pred_u, inv, jemb_u


tes = aktif[aktif["Jns_fasili"] == "TES"].reset_index(drop=True)
tea = aktif[aktif["Jns_fasili"] == "TEA"].reset_index(drop=True)
biaya_tes, eta_tes, pred_tes, inv_tes, jemb_tes = hitung_kandidat(tes)
biaya_tea, eta_tea, pred_tea, inv_tea, jemb_tea = hitung_kandidat(tea)

# Peringkat TES (3 nama berbeda) per node.
# Catatan kompatibilitas: kolom rank_X_tes berisi NAMA gedung (seperti DB lama), bukan tes_id.
nama_tes = tes["Nama_Fasum"].to_numpy()
urut_tes = np.argsort(biaya_tes, axis=0)
route_rows, rank1_tes = [], np.full(N, -1)
rank_tes = {}  # n -> [(indeks TES, eta)] untuk penugasan kapasitas
rank1_jembatan = np.zeros(N, dtype=bool)
# Rute TES hanya untuk node zona merah: warga di zona aman tidak perlu evakuasi vertikal.
for n in np.flatnonzero(is_safe == 0):
    pilihan = []
    for k in urut_tes[:, n]:
        if not np.isfinite(biaya_tes[k, n]):
            break
        if all(nama_tes[k] != nama_tes[p] for p in pilihan):
            pilihan.append(k)
            if len(pilihan) == 3:
                break
    if not pilihan:
        continue
    while len(pilihan) < 3:
        pilihan.append(pilihan[0])
    rank1_tes[n] = pilihan[0]
    rank_tes[n] = [(k, float(eta_tes[k, n])) for k in dict.fromkeys(pilihan)]
    baris = [int(node_ids[n])]
    for k in pilihan:
        path = jalur(n, pred_tes[inv_tes[k]])
        baris += [nama_tes[k], ",".join(str(node_ids[p]) for p in path), round(float(eta_tes[k, n]), 2)]
    rank1_jembatan[n] = jemb_tes[inv_tes[pilihan[0]], n]
    route_rows.append(tuple(baris))

# TEA terdekat & alternatif.
urut_tea = np.argsort(biaya_tea, axis=0)
tea_route_rows, tea_r1, tea_r2 = [], np.full(N, -1), np.full(N, -1)
for n in range(N):
    k1 = urut_tea[0, n]
    if not np.isfinite(biaya_tea[k1, n]):
        continue
    k2 = urut_tea[1, n] if len(tea) > 1 and np.isfinite(biaya_tea[urut_tea[1, n], n]) else k1
    tea_r1[n], tea_r2[n] = k1, k2
    tea_route_rows.append((int(node_ids[n]), tea.at[k1, "facility_id"], tea.at[k2, "facility_id"]))

# tb_tea_next: transisi node untuk semua jalur r1/r2 (penelusuran pointer secara vektor).
tea_next_rows = []
for k in range(len(tea)):
    nh = pred_tea[inv_tea[k]]
    tanda = (tea_r1 == k) | (tea_r2 == k)
    while True:
        lanjut = nh[np.flatnonzero(tanda & (nh >= 0))]
        baru = tanda.copy()
        baru[lanjut] = True
        if np.array_equal(baru, tanda):
            break
        tanda = baru
    for n in np.flatnonzero(tanda & (nh >= 0)):
        tea_next_rows.append((tea.at[k, "facility_id"], int(node_ids[n]), int(node_ids[nh[n]])))
print(f"      tb_routes: {len(route_rows):,} node | tb_tea_routes: {len(tea_route_rows):,} | tb_tea_next: {len(tea_next_rows):,}")

# ==============================================================================
# 6. RUTE KE ZONA AMAN (MULTI-SOURCE)
# ==============================================================================
langkah("[6/9] Menghitung rute ke zona aman terdekat...")
safe_idx = np.flatnonzero(is_safe == 1)
biaya_aman, pred_aman, asal_aman = dijkstra(W_balik, directed=True, indices=safe_idx,
                                             return_predecessors=True, min_only=True)
# Node yang sudah di zona aman adalah sumbernya sendiri (tidak punya next hop).
eta_aman, jemb_aman = akumulasi_riil_baris(pred_aman)
safe_route_rows, safe_next_rows = [], []
for n in np.flatnonzero(np.isfinite(biaya_aman)):
    s = int(asal_aman[n])
    nama = f"Zona Aman - {kel_node[s].title()}" if kel_node[s] else "Zona Aman"
    safe_route_rows.append((int(node_ids[n]), int(node_ids[s]), nama, round(float(eta_aman[n]), 2)))
    if pred_aman[n] >= 0:
        safe_next_rows.append((int(node_ids[n]), int(node_ids[pred_aman[n]])))
print(f"      tb_safe_routes: {len(safe_route_rows):,} | tb_safe_next: {len(safe_next_rows):,}")

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
for n in np.flatnonzero(np.isfinite(biaya_aman)):
    kand.append((n, "ZONA_AMAN", "Zona Aman", float(eta_aman[n])))
df_k = pd.DataFrame(kand, columns=["n", "jenis", "tujuan", "eta"]).drop_duplicates(["n", "jenis", "tujuan"])
df_k = df_k[demand[df_k["n"]] > 0]
# Greedy dua tahap: semua kandidat <= batas waktu dialokasikan dulu (urut ETA), lalu sisa warga
# memakai kandidat lain. TES penuh dilewati; TEA/zona aman selalu menampung sisa.
df_k["layak"] = df_k["eta"] <= BATAS_WAKTU_MENIT
df_k = df_k.sort_values(["layak", "eta"], ascending=[False, True])

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
        inundation_rows.append((kel.title(), "Tinggi", bulatkan_wkt(gpd.GeoSeries([merah], crs=CRS_METER).to_crs("EPSG:4326").iloc[0])))
    if not hijau.is_empty and hijau.area > 100:
        safe_zone_rows.append((kel.title(), None, bulatkan_wkt(gpd.GeoSeries([hijau], crs=CRS_METER).to_crs("EPSG:4326").iloc[0])))
print(f"      Zona merah: {len(inundation_rows)} poligon kelurahan | zona aman: {len(safe_zone_rows)}")

# ==============================================================================
# 9. TULIS SQLITE
# ==============================================================================
langkah(f"[9/9] Menulis {DB_PATH}...")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# --- Tabel lama (skema dipertahankan persis) ---
cur.execute("CREATE TABLE tb_nodes (node_id INTEGER PRIMARY KEY, lat REAL, lon REAL, is_safe INTEGER DEFAULT 0)")
cur.executemany("INSERT INTO tb_nodes VALUES (?, ?, ?, ?)",
                [(int(node_ids[i]), float(lat[i]), float(lon[i]), int(is_safe[i])) for i in range(N)])
cur.execute("CREATE INDEX idx_tb_nodes_lat_lon ON tb_nodes(lat, lon)")

cur.execute("CREATE TABLE tb_tes (tes_id TEXT PRIMARY KEY, nama_tes TEXT, zona TEXT, kapasitas REAL, lat REAL, lon REAL)")
cur.executemany("INSERT INTO tb_tes VALUES (?, ?, ?, ?, ?, ?)",
                [(r.facility_id, r.Nama_Fasum, str(r.KEL).title(), float(r.kapasitas), float(r.lat), float(r.lon))
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
    rute_evakuasi TEXT
)""")
cur.executemany("INSERT INTO tb_tea VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r.facility_id, r.facility_id.replace("_", " "), str(r.KEC).title(), r.Nama_Fasum, str(r.KEL).title(),
                  str(r.KEC).title(), "TEA", float(r.kapasitas), float(r.lat), float(r.lon),
                  int(node_ids[r.node_idx]), None) for r in tea.itertuples()])
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

cur.execute("CREATE TABLE tb_safe_routes (origin_node_id INTEGER PRIMARY KEY, safe_node_id INTEGER, safe_zone_nama TEXT, safe_eta REAL)")
cur.executemany("INSERT INTO tb_safe_routes VALUES (?, ?, ?, ?)", safe_route_rows)
cur.execute("CREATE TABLE tb_safe_next (node_id INTEGER, next_node_id INTEGER, PRIMARY KEY (node_id, next_node_id))")
cur.executemany("INSERT INTO tb_safe_next VALUES (?, ?)", safe_next_rows)

cur.execute("CREATE TABLE tb_route_shares (origin_node_id INTEGER, jenis TEXT, nama_tujuan TEXT, porsi REAL)")
cur.executemany("INSERT INTO tb_route_shares VALUES (?, ?, ?, ?)", share_rows)
cur.execute("CREATE INDEX idx_shares_origin ON tb_route_shares(origin_node_id)")

cur.execute("""CREATE VIEW v_fasilitas_evakuasi AS
SELECT tes_id AS facility_id, tes_id AS kode, nama_tes AS nama, 'TES' AS jenis, 'Vertikal' AS tipe_evakuasi,
       zona AS zona_sektor, kapasitas, lat, lon FROM tb_tes
UNION ALL
SELECT tea_id AS facility_id, kode_tea AS kode, nama_tea AS nama, 'TEA' AS jenis, 'Horizontal' AS tipe_evakuasi,
       sektor AS zona_sektor, kapasitas, lat, lon FROM tb_tea""")

# --- Tabel tambahan V4 ---
cur.execute("""CREATE TABLE tb_fasilitas_info (
    facility_id TEXT PRIMARY KEY, jenis TEXT, nama TEXT, kelurahan TEXT, kecamatan TEXT,
    dipakai INTEGER, alasan_tidak_dipakai TEXT, kapasitas REAL, kapasitas_sumber TEXT,
    d_pantai_m REAL, indeks_bahaya REAL, jumlah_lantai_2019 INTEGER, status_bpbd_2019 TEXT, nama_bpbd_2019 TEXT,
    kapasitas_2019 REAL, luas_jejak_bangunan_m2 REAL,
    nearest_node_id INTEGER, snap_dist_m REAL, lat REAL, lon REAL)""")
cur.executemany("INSERT INTO tb_fasilitas_info VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r.facility_id, r.Jns_fasili, r.Nama_Fasum, str(r.KEL).title(), str(r.KEC).title(), int(r.dipakai),
                  r.alasan_tidak_dipakai or None, float(r.kapasitas), r.kapasitas_sumber, round(float(r.d_pantai_m), 1),
                  None if np.isnan(r.indeks_bahaya) else round(float(r.indeks_bahaya), 4),
                  None if pd.isna(r.lantai_2019) else int(r.lantai_2019), r.status_2019, r.nama_2019,
                  None if pd.isna(r.kapasitas_2019) else float(r.kapasitas_2019),
                  None if pd.isna(r.luas_jejak_m2) else round(float(r.luas_jejak_m2), 1),
                  int(node_ids[r.node_idx]), round(float(r.snap_dist_m), 1), float(r.lat), float(r.lon))
                 for r in fas.itertuples()])

cur.execute("""CREATE TABLE tb_node_info (
    node_id INTEGER PRIMARY KEY, kelurahan TEXT, d_pantai_m REAL, indeks_bahaya REAL, demand_jiwa REAL,
    rute_tes_lewat_jembatan INTEGER, rute_aman_lewat_jembatan INTEGER)""")
cur.executemany("INSERT INTO tb_node_info VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(int(node_ids[i]), kel_node[i].title() or None, round(float(d_pantai[i]), 1),
                  None if np.isnan(indeks_bahaya_node[i]) else round(float(indeks_bahaya_node[i]), 4),
                  round(float(demand[i]), 3), int(rank1_jembatan[i]), int(jemb_aman[i])) for i in range(N)])

cur.execute("CREATE TABLE tb_jembatan_sungai (u INTEGER, v INTEGER, panjang_ruas_m REAL, indeks_bahaya_gempa REAL, PRIMARY KEY (u, v))")
cur.executemany("INSERT INTO tb_jembatan_sungai VALUES (?, ?, ?, ?)",
                [(int(node_ids[kunci_arr[j][0]]), int(node_ids[kunci_arr[j][1]]), round(float(panjang_arr[j]), 1),
                  None if np.isnan(gempa_jembatan[j]) else round(float(gempa_jembatan[j]), 4))
                 for j in np.flatnonzero(jembatan_sungai)])

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
tb_kel["kecamatan"] = tb_kel["kecamatan"].astype(str).str.title()
tb_kel["node_zona_merah"] = [int(((kel_node == k) & (is_safe == 0)).sum()) for k in krb["KEL"]]
tb_kel.to_sql("tb_kelurahan_info", conn, index=False)

versi = datetime.now().strftime("%Y.%m.%d")
metadata = {
    "versi": versi,
    "sumber_tes_tea": "BPBD Kota Padang - 2_TES_TEA_Padang.shp (digitasi Kelurahan Tangguh / Drill 2025)",
    "sumber_zona_merah": "BPBD - KRB Kota Padang 2023-2027, raster Peta_Bahaya_Tsunami",
    "sumber_penduduk": "BPBD - KRB Kota Padang 2023-2027, penduduk terpapar tsunami per kelurahan",
    "sumber_verifikasi_gedung": "BPBD - Daftar Shelter OK.xlsx (verifikasi 2019: lantai & kapasitas)",
    "sumber_jalur_resmi": "BPBD - Jalur_evakuasi_Padang.shp (jalur per RT/RW Kelurahan Tangguh)",
    "sumber_sebaran_penduduk": "BPBD - Basemap.gdb Bangunan_AR (jejak bangunan RTRW di zona merah)",
    "sumber_bahaya_gempa_jembatan": "BPBD - KRB 2023-2027, raster Peta_Bahaya_Gempabumi",
    "jalur_resmi_faktor": str(JALUR_RESMI_FAKTOR),
    "m2_per_orang_estimasi_kapasitas": str(M2_PER_ORANG),
    "kecepatan_jalan_ms": str(KECEPATAN_JALAN_MS),
    "batas_waktu_menit": str(BATAS_WAKTU_MENIT),
    "toleransi_mendekat_pantai_m": str(TOLERANSI_MENDEKAT_PANTAI_M),
    "penalti_mendekat_pantai": str(PENALTI_MENDEKAT_PANTAI),
    "penalti_jembatan_sungai": str(PENALTI_JEMBATAN_SUNGAI),
    "catatan_tingkat_bahaya": "tb_inundation_zones.tingkat_bahaya bernilai 'Tinggi' untuk seluruh zona merah (peta evakuasi hanya merah/hijau)",
}
cur.execute("CREATE TABLE tb_metadata (kunci TEXT PRIMARY KEY, nilai TEXT)")
cur.executemany("INSERT INTO tb_metadata VALUES (?, ?)", list(metadata.items()))

conn.commit()
cur.execute("VACUUM")
conn.close()

sha = hashlib.sha256(open(DB_PATH, "rb").read()).hexdigest()
ukuran = os.path.getsize(DB_PATH)

# ==============================================================================
# LAPORAN
# ==============================================================================
total_jiwa = demand.sum()
merah = is_safe == 0
tanpa_tes = merah & (rank1_tes < 0)
print("\n" + "=" * 80)
print("LAPORAN BUILD")
print("=" * 80)
print(f"Kecepatan jalan                  : {KECEPATAN_JALAN_MS} m/s ({KECEPATAN_JALAN_MS * 3.6:.2f} km/jam), batas {BATAS_WAKTU_MENIT:.0f} menit")
print(f"TES dipakai / TEA dipakai        : {len(tes)} / {len(tea)}")
print(f"Node zona merah tanpa TES valid  : {tanpa_tes.sum():,} dari {merah.sum():,} (arahan: TEA / zona aman)")
print(f"Jiwa dengan tujuan <= {BATAS_WAKTU_MENIT:.0f} menit   : {jiwa_selamat_20:,.0f} dari {total_jiwa:,.0f} ({jiwa_selamat_20 / max(total_jiwa, 1) * 100:.1f}%)")
print(f"Jiwa belum teralokasi            : {jiwa_tanpa_tujuan:,.0f}")
print(f"Jiwa yang rute TES-nya lewat jembatan sungai: {demand[rank1_jembatan].sum():,.0f}")
print(f"Jiwa yang rute zona amannya lewat jembatan  : {demand[jemb_aman.astype(bool)].sum():,.0f}")
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
        print(f"  - {r.facility_id} {r.Nama_Fasum} ({str(r.KEL).title()}): {r.alasan_tidak_dipakai}"
                + (f" [cocok 2019: {r.nama_2019}, {r.lantai_2019} lantai]" if pd.notna(r.nama_2019) else "")
              + (f" [indeks bahaya {r.indeks_bahaya:.2f}]" if r.Jns_fasili == "TEA" else ""))
cocok = fas[fas["nama_2019"].notna()]
print(f"TES yang cocok dengan verifikasi BPBD 2019: {len(cocok)}")
for r in cocok.itertuples():
    print(f"  - {r.Nama_Fasum}  <->  {r.nama_2019} ({r.status_2019}, {r.lantai_2019} lantai)")
print(f"\nDatabase  : {DB_PATH} ({ukuran / 1024 / 1024:.2f} MB)")
print(f"SHA-256   : {sha}")
print(f"Versi     : {versi}")
print(f"Waktu     : {time.time() - start_total:.1f} detik")
print("=" * 80)
