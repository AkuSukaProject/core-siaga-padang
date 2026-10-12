"""
DIGITASI "ZONA RAWAN TSUNAMI" DARI PETA EVAKUASI BPBD KOTA PADANG

Sumber: Data BPBD/Peta TES dan Potensial Shelter.png ("Peta Tempat Evakuasi Sementara dan Lokasi Potensial
Shelter", 1:15.000, dengan Blue Line). Gambar ini tidak bergeoreferensi, jadi:
  1. Georeferensi: pola air di peta (laut + sungai, biru muda) dicocokkan dengan air nyata (laut di luar
     daratan garis pantai OSM + Sungai_AR Basemap BPBD). Skala dicari lewat korelasi silang (utara di atas),
     lalu transformasi afin diperhalus dengan meminimalkan jarak tepi air peta ke tepi air nyata.
  2. Uji: titik kuning "Potensial Shelter" dibandingkan dengan koordinat TES di DB.
  3. Zona: piksel merah "Zona Rawan Tsunami"; jalan, label, panah, dan air diisi kelas terdekat (merah/krem);
     lubang < 1 ha (teks label) diisi; dipotong ke daratan OSM.

Keluaran: data_bpbd_digitasi/zona_rawan_peta_evakuasi_bpbd.geojson (EPSG:4326) berisi dua fitur:
  - "zona_rawan_peta_evakuasi": zona merah peta evakuasi,
  - "cakupan_peta": daratan yang tergambar di peta (di luar ini peta tidak memberi informasi).
Dipakai build_db.py (zona merah = landaan KRB + zona ini). Jalankan ulang hanya bila gambar sumber berganti.

Pemakaian: env\\Scripts\\python.exe data_bpbd_digitasi\\digitasi_peta_evakuasi.py
"""
import json
import os
import sqlite3
import sys

import numpy as np
import geopandas as gpd
import shapely
import rasterio.features
from affine import Affine
from PIL import Image
from pyproj import Transformer
from scipy import ndimage, optimize
from scipy.signal import fftconvolve
from scipy.spatial import cKDTree
from shapely.geometry import shape

sys.stdout.reconfigure(encoding="utf-8")
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
PETA = os.path.join("Data BPBD", "Peta TES dan Potensial Shelter.png")
BASEMAP = os.path.join("Data BPBD", "KRB Padang [2023-2027]", "02_BASEMAP", "Basemap.gdb")
KELUARAN = os.path.join("data_bpbd_digitasi", "zona_rawan_peta_evakuasi_bpbd.geojson")
M = "EPSG:32747"
# Bingkai peta di gambar (piksel): panel informasi mulai kolom 5885; kotak legenda + inset di kiri bawah.
KOLOM_PANEL = 5885
LEGENDA = (0, 6600, 1180, None)  # x0, y0, x1, y1 (None = sampai bawah)
LUAS_MAKS_LUBANG_HA = 1.0

im = np.asarray(Image.open(PETA).convert("RGB")).astype(np.int16)
H, W, _ = im.shape
bingkai = np.zeros((H, W), bool)
bingkai[:, :KOLOM_PANEL] = True
bingkai[LEGENDA[1]:, LEGENDA[0]:LEGENDA[2]] = False
R, G, B = im[..., 0], im[..., 1], im[..., 2]
air = (np.abs(im - np.array([146, 218, 242])).sum(-1) < 40) & bingkai
merah = (R > 200) & (G < 130) & (B < 130) & bingkai
krem = (R > 235) & (G > 235) & (B > 170) & (B < 245) & bingkai

# --- Air nyata: laut (di luar daratan OSM) + sungai BPBD -------------------------------------------------
gk = gpd.read_file(BASEMAP, layer="Batas_Administrasi_Kelurahan_AR").to_crs(M)
kota = gk.union_all()
ke_m = Transformer.from_crs(4326, M, always_xy=True)
garis = []
for w in json.load(open(os.path.join("data_osm", "pantai_osm.json"), encoding="utf-8"))["elements"]:
    if w.get("geometry"):
        x, y = ke_m.transform([p["lon"] for p in w["geometry"]], [p["lat"] for p in w["geometry"]])
        garis.append(shapely.LineString(np.column_stack([x, y])))
kotak = shapely.box(*kota.buffer(3000).bounds)
muka = shapely.get_parts(shapely.polygonize(shapely.get_parts(shapely.union_all([shapely.union_all(garis).intersection(kotak), kotak.boundary]))))
isi_kota = np.array([f.intersection(kota).area for f in muka])
darat = shapely.union_all([f for f, a in zip(muka, isi_kota) if a > 0.5 * f.area or a > 0.1 * kota.area])
sungai = gpd.read_file(BASEMAP, layer="Sungai_AR").to_crs(M).union_all()
X0, Y1, LEBAR_M, TINGGI_M = 640000, 9925000, 30000, 45000


def air_nyata(res):
    w, h = int(LEBAR_M / res), int(TINGGI_M / res)
    tf = Affine(res, 0, X0, 0, -res, Y1)
    d = rasterio.features.rasterize([(darat, 1)], (h, w), transform=tf).astype(bool)
    s = rasterio.features.rasterize([(sungai, 1)], (h, w), transform=tf, all_touched=True).astype(bool)
    return ~d | s, tf


# --- 1a. Skala & posisi awal (korelasi silang, utara di atas) -------------------------------------------
F = 8
blok = lambda a: a[: H // F * F, : W // F * F].reshape(H // F, F, W // F, F).mean(axis=(1, 3))
air_ds, bingkai_ds = blok(air), blok(bingkai) > 0.5
templat = np.where(bingkai_ds, air_ds - air_ds[bingkai_ds].mean(), 0).astype(np.float32)
terbaik = None
for s_px in np.arange(0.90, 1.61, 0.02):
    nyata, tf = air_nyata(s_px * F)
    kor = fftconvolve(nyata.astype(np.float32), templat[::-1, ::-1], mode="valid")
    k = np.unravel_index(np.argmax(kor), kor.shape)
    if terbaik is None or kor[k] > terbaik[0]:
        terbaik = (kor[k], s_px, k, tf)
_, s_px, (r0, c0), tf = terbaik
p0 = np.array([s_px, 0, tf.c + c0 * F * s_px, 0, -s_px, tf.f - r0 * F * s_px])
print(f"Skala awal {s_px:.2f} m/piksel")

# --- 1b. Perhalus transformasi afin (jarak tepi air peta ke tepi air nyata) -----------------------------
RES = 2.0
nyata, tfn = air_nyata(RES)
jarak_tepi = ndimage.distance_transform_edt(~(nyata ^ ndimage.binary_erosion(nyata))) * RES
tepi_peta = air ^ ndimage.binary_erosion(air, iterations=2)
rr, cc = np.nonzero(tepi_peta)
pilih = np.random.default_rng(0).choice(len(rr), 60000, replace=False)
rr, cc = rr[pilih] + 0.5, cc[pilih] + 0.5


def ke_utm(p, c, r):
    return p[0] * c + p[1] * r + p[2], p[3] * c + p[4] * r + p[5]


def biaya(p):
    x, y = ke_utm(p, cc, rr)
    ci, ri = (x - X0) / RES, (Y1 - y) / RES
    ok = (ci >= 0) & (ci < jarak_tepi.shape[1] - 1) & (ri >= 0) & (ri < jarak_tepi.shape[0] - 1)
    d = np.full(len(x), 60.0)
    d[ok] = ndimage.map_coordinates(jarak_tepi, [ri[ok], ci[ok]], order=1)
    return np.mean(np.minimum(d, 60.0))


langkah = np.array([1e-3, 1e-3, 10, 1e-3, 1e-3, 10])
hasil = optimize.minimize(lambda q: biaya(p0 + q * langkah), np.zeros(6), method="Powell",
                          options={"xtol": 1e-3, "ftol": 1e-4, "maxfev": 6000})
p = p0 + hasil.x * langkah
A = Affine(*p[:3], *p[3:])
print(f"Jarak rata-rata tepi air peta ke tepi air nyata: {biaya(p0):.1f} m -> {biaya(p):.1f} m")

# --- 2. Uji dengan titik kuning "Potensial Shelter" vs TES di DB ----------------------------------------
kuning = (np.abs(im - np.array([250, 248, 0])).sum(-1) < 60) & bingkai
lab, n = ndimage.label(kuning)
pusat = np.array(ndimage.center_of_mass(kuning, lab, range(1, n + 1)))
uk = ndimage.sum(kuning, lab, range(1, n + 1))
pusat = pusat[(uk > 300) & (uk < 5000)]
db = os.path.join("hasil_build", "ranah_siaga_v4.db")
uji = {}
if os.path.exists(db):
    tes = np.array(sqlite3.connect(db).execute("select lon, lat from tb_fasilitas_info where jenis = 'TES'").fetchall())
    tx, ty = ke_m.transform(tes[:, 0], tes[:, 1])
    d, _ = cKDTree(np.column_stack([tx, ty])).query(np.column_stack(ke_utm(p, pusat[:, 1] + 0.5, pusat[:, 0] + 0.5)))
    uji = {"titik_shelter": int(len(d)), "median_m": round(float(np.median(d)), 1), "dalam_50m": round(float((d <= 50).mean()), 3)}
    print(f"Titik shelter peta vs TES DB: {len(d)} titik, median {np.median(d):.0f} m, <= 50 m: {(d <= 50).mean():.0%}")

# --- 3. Zona merah -------------------------------------------------------------------------------------
kelas = np.zeros((H, W), np.int8)
kelas[merah] = 1
kelas[krem] = 2
_, (ir, ic) = ndimage.distance_transform_edt(kelas == 0, return_indices=True)
zona = (kelas[ir, ic] == 1) & bingkai
lab, n = ndimage.label(zona)
uk = ndimage.sum(zona, lab, range(1, n + 1))
zona = np.isin(lab, 1 + np.flatnonzero(uk >= 20000))            # buang simbol merah lepas
lubang = ndimage.binary_fill_holes(zona) & ~zona
lab, n = ndimage.label(lubang)
uk = ndimage.sum(lubang, lab, range(1, n + 1))
zona |= np.isin(lab, 1 + np.flatnonzero(uk * A.a * -A.e < LUAS_MAKS_LUBANG_HA * 1e4))   # teks label
F = 2
zs = zona[: H // F * F, : W // F * F].reshape(H // F, F, W // F, F).mean(axis=(1, 3)) >= 0.5
pol = [shape(g) for g, v in rasterio.features.shapes(zs.astype(np.uint8), mask=zs, transform=A * Affine.scale(F)) if v == 1]
zona_utm = shapely.make_valid(shapely.union_all(pol)).simplify(3).intersection(darat)
cakupan = shapely.difference(shapely.box(0, 0, KOLOM_PANEL, H), shapely.box(LEGENDA[0], LEGENDA[1], LEGENDA[2], H))
cakupan = shapely.affinity.affine_transform(cakupan, [A.a, A.b, A.d, A.e, A.c, A.f]).intersection(darat)
print(f"Zona rawan peta evakuasi: {zona_utm.area / 1e4:,.0f} ha | cakupan peta (darat): {cakupan.area / 1e4:,.0f} ha")

gdf = gpd.GeoDataFrame({"nama": ["zona_rawan_peta_evakuasi", "cakupan_peta"],
                        "luas_ha": [round(zona_utm.area / 1e4, 1), round(cakupan.area / 1e4, 1)]},
                       geometry=[zona_utm, cakupan], crs=M).to_crs(4326)
gdf["geometry"] = shapely.set_precision(gdf.geometry.values, 1e-6)
fc = json.loads(gdf.to_json(drop_id=True))
fc["metadata"] = {"sumber": "BPBD Kota Padang, Peta Tempat Evakuasi Sementara dan Lokasi Potensial Shelter (1:15.000), PNG",
                  "afin_utm47s": [round(v, 6) for v in p], "jarak_tepi_air_m": round(biaya(p), 1), "uji_shelter": uji}
with open(KELUARAN, "w", encoding="utf-8") as f:
    json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))
print(f"Ditulis: {KELUARAN}")
