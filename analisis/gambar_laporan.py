"""
GAMBAR LAPORAN AKHIR SIAGA PADANG (Gambar 1.1, 3.1, 5.4) DARI DATABASE

Semua gambar dibuat dari basis data Siaga Padang (default hasil_build/ranah_siaga_v4.db; versi tercatat di
tb_metadata) dan Basemap BPBD, sehingga angka di gambar sama dengan angka di basis data dan dapat dibuat ulang.

Keluaran (analisis/output/gambar_laporan/<versi>/, PNG 300 dpi):
  - gambar_1_1_zona_dan_penduduk.png : (a) zona merah & zona hijau + TES/TEA, (b) jiwa terpapar KRB per kelurahan
  - gambar_3_1_cakupan_wilayah.png    : zona merah, zona penyangga 2 km, zona hijau, dan titik evakuasi
  - gambar_5_4_jaringan_jalan.png     : jaringan jalan pejalan kaki dan sebaran TES/TEA
  - gambar_pemodelan_kolektif_beban_tes.png : (sejak 2026.10.18) beban model tiap TES terhadap kapasitas dan
                                       kelompok porsi tujuan penduduk (tb_route_shares)

Pemakaian: env\\Scripts\\python.exe analisis\\gambar_laporan.py [--db <ranah_siaga_v4.db>] [--graf <padang_full.graphml>]
  --graf harus graf sumber basis data itu (dipakai untuk jenis jalan Gambar 5.4). Untuk versi lama, ambil keduanya dari
  riwayatnya, mis. 2026.10.16: berkas DB dari Release db-2026.10.16 dan `git show 23854a4:padang_full.graphml`.
"""
import argparse
import json
import os
import sqlite3
import sys

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from shapely import wkt
from pyproj import Transformer
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, ListedColormap
import matplotlib.patheffects as pe_

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
_arg = argparse.ArgumentParser()
_arg.add_argument("--db", default=os.path.join("hasil_build", "ranah_siaga_v4.db"))
_arg.add_argument("--graf", default="padang_full.graphml")
ARG = _arg.parse_args()
DB = ARG.db
BASEMAP = os.path.join("Data BPBD", "KRB Padang [2023-2027]", "02_BASEMAP", "Basemap.gdb")
M = "EPSG:32747"

# Palet (dipakai di ketiga gambar agar seragam).
LAUT, DARAT_LUAR, GARIS_KEC = "#dbe8f0", "#f4f2ec", "#7c8590"
MERAH, MERAH_TEPI = "#e0533d", "#a8301f"
HIJAU, HIJAU_TEPI = "#b7dcb0", "#5f9e5a"
TES_C, TEA_C = "#14365d", "#0e8a7e"
JALAN_C = "#3c8fa3"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold"})

def simpan(fig, nama):
    """Simpan lewat berkas sementara lalu ganti; ulangi bila berkas sedang dikunci (pratinjau gambar/antivirus)."""
    import time
    tujuan = os.path.join(OUT, nama)
    sementara = tujuan + ".tmp.png"
    for coba in range(10):
        try:
            fig.savefig(sementara, dpi=300)
            os.replace(sementara, tujuan)
            return
        except OSError:
            time.sleep(1.0)
    raise OSError(f"Gagal menyimpan {tujuan}; tutup pratinjau gambar lalu jalankan ulang")


c = sqlite3.connect(DB)
meta = dict(c.execute("select kunci, nilai from tb_metadata"))
VERSI = meta["versi"]
OUT = os.path.join("analisis", "output", "gambar_laporan", VERSI)
os.makedirs(OUT, exist_ok=True)


def baca_zona(tabel):
    return gpd.GeoSeries([wkt.loads(w) for (w,) in c.execute(f"select geometry_wkt from {tabel}")], crs=4326).to_crs(M)


merah = baca_zona("tb_inundation_zones")
hijau = baca_zona("tb_safe_zones")
kel = gpd.read_file(BASEMAP, layer="Batas_Administrasi_Kelurahan_AR").to_crs(M)
kec = gpd.read_file(BASEMAP, layer="Batas_Administrasi_Kecamatan_AR").to_crs(M)
kota = kec.union_all()
ke_m = Transformer.from_crs(4326, M, always_xy=True)
tes = pd.read_sql("select tes_id, nama_tes, sumber, lat, lon from tb_tes", c)
tea = pd.read_sql("select tea_id, nama_tea, lat, lon from tb_tea", c)
tes["x"], tes["y"] = ke_m.transform(tes.lon.to_numpy(), tes.lat.to_numpy())
tea["x"], tea["y"] = ke_m.transform(tea.lon.to_numpy(), tea.lat.to_numpy())

# Daratan dari garis pantai OSM (sama dengan build_db.py), untuk latar laut/darat tanpa ubin peta.
garis = []
for w in json.load(open(os.path.join("data_osm", "pantai_osm.json"), encoding="utf-8"))["elements"]:
    if w.get("geometry"):
        x, y = ke_m.transform([p["lon"] for p in w["geometry"]], [p["lat"] for p in w["geometry"]])
        garis.append(shapely.LineString(np.column_stack([x, y])))
kotak = shapely.box(*kota.buffer(3000).bounds)  # sama dengan build_db.py; kotak lebih besar membuat garis pantai tidak membelah laut dan darat
muka = shapely.get_parts(shapely.polygonize(shapely.get_parts(shapely.union_all([shapely.union_all(garis).intersection(kotak), kotak.boundary]))))
isi = np.array([f.intersection(kota).area for f in muka])
darat = shapely.union_all([f for f, a in zip(muka, isi) if a > 0.5 * f.area or a > 0.1 * kota.area
                           or (a == 0 and f.area < 5e6 and not f.touches(kotak.boundary))])
# Uji kewarasan latar: daratan tidak boleh memuat laut (sebagian besar zona merah & kota di darat, laut di luar).
assert darat.area < kotak.area * 0.85 and kota.difference(darat).area < 0.01 * kota.area, "Poligon daratan memuat laut"
ha_merah = merah.area.sum() / 1e4
ha_hijau = hijau.area.sum() / 1e4


def kerangka(ax, batas, judul=None):
    """Latar laut & daratan, batas kota & kecamatan, skala batang, dan panah utara."""
    x0, y0, x1, y1 = batas
    ax.set_facecolor(LAUT)
    gpd.GeoSeries([darat], crs=M).plot(ax=ax, color=DARAT_LUAR, linewidth=0, zorder=0)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#9aa3ab")
    if judul:
        ax.set_title(judul, loc="left", pad=8)


# Kecamatan pesisir yang sempit diberi label di laut (barat) atau di zona hijau (timur) dengan garis penunjuk.
GESER_LABEL = {"PADANG UTARA": (-6500, 900), "PADANG BARAT": (-6500, 0), "PADANG SELATAN": (-6500, -400),
               "NANGGALO": (4800, 2600), "PADANG TIMUR": (5200, 1900), "LUBUK BEGALUNG": (5200, -300)}
HALO = [pe_.withStroke(linewidth=2.2, foreground="white")]


def batas_kec(ax, label=True):
    kec.boundary.plot(ax=ax, color=GARIS_KEC, linewidth=0.6, linestyle=(0, (4, 2)), zorder=4)
    gpd.GeoSeries([kota], crs=M).boundary.plot(ax=ax, color="#3d4650", linewidth=1.1, zorder=5)
    if label:
        for _, r in kec.iterrows():
            nama = r["Kecamatan"].upper()
            p = r.geometry.representative_point()
            dx, dy = GESER_LABEL.get(nama, (0, 0))
            if dx or dy:
                ax.annotate(nama, (p.x, p.y), xytext=(p.x + dx, p.y + dy), ha="right" if dx < 0 else "left", va="center",
                            fontsize=6.5, color="#2a3037", fontweight="bold", zorder=11, path_effects=HALO,
                            arrowprops=dict(arrowstyle="-", color="#2a3037", lw=0.6, shrinkA=1, shrinkB=0))
            else:
                ax.annotate(nama, (p.x, p.y), ha="center", va="center", fontsize=6.5, color="#2a3037",
                            zorder=11, fontweight="bold", path_effects=HALO)


def skala_utara(ax, panjang_km=5):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bx, by = x0 + 0.05 * (x1 - x0), y0 + 0.04 * (y1 - y0)
    tinggi = 0.008 * (y1 - y0)
    for i in range(panjang_km):
        ax.add_patch(Rectangle((bx + i * 1000, by), 1000, tinggi, facecolor="#2a3037" if i % 2 == 0 else "white",
                               edgecolor="#2a3037", linewidth=0.6, zorder=10))
    for km in (0, panjang_km // 2, panjang_km):
        ax.text(bx + km * 1000, by + 2.2 * tinggi, f"{km}", ha="center", va="bottom", fontsize=7, zorder=10)
    ax.text(bx + panjang_km * 1000 + 300, by + tinggi / 2, "km", ha="left", va="center", fontsize=7, zorder=10)
    ux, uy = x1 - 0.06 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.annotate("", xy=(ux, uy + 0.07 * (y1 - y0)), xytext=(ux, uy), zorder=10,
                arrowprops=dict(arrowstyle="-|>", color="#2a3037", lw=1.4))
    ax.text(ux, uy + 0.08 * (y1 - y0), "U", ha="center", va="bottom", fontsize=10, fontweight="bold", zorder=10)


def titik_evakuasi(ax, ukuran=1.0):
    ax.scatter(tes.x, tes.y, s=14 * ukuran, marker="s", color=TES_C, edgecolor="white", linewidth=0.5, zorder=8)
    ax.scatter(tea.x, tea.y, s=26 * ukuran, marker="o", color=TEA_C, edgecolor="white", linewidth=0.6, zorder=8)


bx0, by0, bx1, by1 = kota.bounds
BATAS = (bx0 - 1500, by0 - 1500, bx1 + 1500, by1 + 1500)
SUMBER = (f"Sumber: basis data Siaga Padang versi {VERSI}; zona merah dari raster bahaya tsunami KRB 2023–2027 BPBD dan zona rawan "
          "peta evakuasi BPBD (Blue Line), dipotong garis pantai OpenStreetMap; batas administrasi Basemap BPBD.")

# ==============================================================================
# GAMBAR 1.1  (a) zona rawan tsunami, (b) jiwa terpapar per kelurahan (KRB)
# ==============================================================================
fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 6.9))
kerangka(a, BATAS, "(a) Zona merah dan zona hijau")
hijau.plot(ax=a, color=HIJAU, edgecolor="none", zorder=1)
merah.plot(ax=a, color=MERAH, edgecolor=MERAH_TEPI, linewidth=0.3, zorder=2)
batas_kec(a)
titik_evakuasi(a)
skala_utara(a)
a.legend(handles=[Patch(facecolor=MERAH, edgecolor=MERAH_TEPI, label=f"Zona merah ({ha_merah / 100:,.1f} km²)".replace(".", ",")),
                  Patch(facecolor=HIJAU, edgecolor=HIJAU_TEPI, label=f"Zona hijau ({ha_hijau / 100:,.0f} km²)".replace(",", ".")),
                  Line2D([], [], marker="s", ls="", color=TES_C, markeredgecolor="white", markersize=6, label=f"TES ({len(tes)})"),
                  Line2D([], [], marker="o", ls="", color=TEA_C, markeredgecolor="white", markersize=7, label=f"TEA ({len(tea)})"),
                  Line2D([], [], color=GARIS_KEC, ls=(0, (4, 2)), lw=0.8, label="Batas kecamatan")],
         loc="upper left", fontsize=8.5, frameon=True, framealpha=0.95, edgecolor="#c9cdd2")

kerangka(b, BATAS, "(b) Jiwa terpapar tsunami per kelurahan")
info = pd.read_sql("select kelurahan, jiwa_terpapar from tb_kelurahan_info", c)
kel["nama"] = kel["Kelurahan"].str.upper().str.replace("-", " ").str.split().str.join(" ")
info["nama"] = info["kelurahan"].str.upper().str.replace("-", " ").str.split().str.join(" ")
kj = kel.merge(info[["nama", "jiwa_terpapar"]], on="nama", how="left")
kj["jiwa_terpapar"] = kj["jiwa_terpapar"].fillna(0)
batas_kelas = [1, 2000, 4000, 6000, 10000, 20000]
warna = ["#fde8cf", "#f9c08c", "#f08e4f", "#d9572a", "#9e2d12"]
peta_warna, norma = ListedColormap(warna), BoundaryNorm(batas_kelas, 5)
kj[kj.jiwa_terpapar <= 0].plot(ax=b, color="#eef0ee", edgecolor="#c9cdd2", linewidth=0.3, zorder=1)
kj[kj.jiwa_terpapar > 0].plot(ax=b, column="jiwa_terpapar", cmap=peta_warna, norm=norma, edgecolor="white", linewidth=0.4, zorder=2)
merah.boundary.plot(ax=b, color="#5b1408", linewidth=0.35, alpha=0.6, zorder=3)
batas_kec(b)
skala_utara(b)
label_kelas = ["< 2.000", "2.000–4.000", "4.000–6.000", "6.000–10.000", "≥ 10.000"]
total = int(round(info["jiwa_terpapar"].sum()))
b.legend(handles=[Patch(facecolor=w, edgecolor="#c9cdd2", label=l) for w, l in zip(warna, label_kelas)]
         + [Patch(facecolor="#eef0ee", edgecolor="#c9cdd2", label="Tidak terpapar"),
            Line2D([], [], color="#5b1408", lw=0.8, label="Tepi zona merah")],
         title=f"Jiwa terpapar (total {total:,})".replace(",", "."), loc="upper left", fontsize=8.5, title_fontsize=8.5,
         frameon=True, framealpha=0.95, edgecolor="#c9cdd2")
fig.text(0.01, 0.012, SUMBER + " Jiwa terpapar: tabel KRB Kota Padang 2023–2027 per kelurahan.", fontsize=7, color="#5d6670", wrap=True)
fig.tight_layout(rect=(0, 0.035, 1, 1))
simpan(fig, "gambar_1_1_zona_dan_penduduk.png")
plt.close(fig)

# ==============================================================================
# GAMBAR 3.1  cakupan wilayah: zona merah, zona penyangga 2 km, zona hijau, dan titik evakuasi
# ==============================================================================
# Zona penyangga (kuning) = daratan sampai PENYANGGA_M dari tepi zona merah. Ini visualisasi perencanaan, bukan
# zona resmi BPBD: aplikasi tetap hanya mengenal zona merah dan zona hijau (K-B4).
PENYANGGA_M = 2000
KUNING, KUNING_TEPI = "#f6c453", "#c58f12"


def km2(v_m2, desimal=1):
    return f"{v_m2 / 1e6:,.{desimal}f}".replace(",", "#").replace(".", ",").replace("#", ".")


merah_u, hijau_u = merah.union_all(), hijau.union_all()
penyangga = merah_u.buffer(PENYANGGA_M).intersection(darat).difference(merah_u)
peny_kota, peny_luar = penyangga.intersection(kota), penyangga.difference(kota)
hijau_lain = hijau_u.difference(penyangga)
pe = gpd.read_file(os.path.join("data_bpbd_digitasi", "zona_rawan_peta_evakuasi_bpbd.geojson")).to_crs(M).set_index("nama").geometry
lx0, ly0, lx1, ly1 = penyangga.bounds
B31 = (min(BATAS[0], lx0 - 1000), min(BATAS[1], ly0 - 1000), max(BATAS[2], lx1 + 1000), max(BATAS[3], ly1 + 1000))
fig, ax = plt.subplots(figsize=(8.8, 9.6))
kerangka(ax, B31)
gpd.GeoSeries([hijau_lain], crs=M).plot(ax=ax, color=HIJAU, edgecolor="none", zorder=1)
gpd.GeoSeries([peny_kota], crs=M).plot(ax=ax, color=KUNING, edgecolor="none", zorder=1)
gpd.GeoSeries([peny_luar], crs=M).plot(ax=ax, facecolor="#fbe7b3", edgecolor=KUNING_TEPI, hatch="////", linewidth=0, zorder=1)
merah.plot(ax=ax, color=MERAH, edgecolor=MERAH_TEPI, linewidth=0.3, zorder=2)
gpd.GeoSeries([pe["cakupan_peta"]], crs=M).boundary.plot(ax=ax, color="#2a3037", linewidth=0.9, linestyle=(0, (1.5, 1.5)), zorder=6)
batas_kec(ax)
titik_evakuasi(ax)
skala_utara(ax)
ax.legend(handles=[Patch(facecolor=MERAH, edgecolor=MERAH_TEPI, label=f"Zona merah, rawan tsunami ({km2(merah_u.area)} km²)"),
                   Patch(facecolor=KUNING, label=f"Zona penyangga {PENYANGGA_M // 1000} km ({km2(peny_kota.area)} km²)"),
                   Patch(facecolor="#fbe7b3", edgecolor=KUNING_TEPI, hatch="////", label=f"Penyangga di luar Kota Padang ({km2(peny_luar.area)} km²)"),
                   Patch(facecolor=HIJAU, label=f"Zona hijau di luar penyangga ({km2(hijau_lain.area, 0)} km²)"),
                   Line2D([], [], color="#2a3037", ls=(0, (1.5, 1.5)), lw=1, label="Cakupan peta evakuasi BPBD"),
                   Line2D([], [], marker="s", ls="", color=TES_C, markeredgecolor="white", markersize=6, label=f"TES ({len(tes)} lokasi)"),
                   Line2D([], [], marker="o", ls="", color=TEA_C, markeredgecolor="white", markersize=7, label=f"TEA ({len(tea)} lokasi)")],
          title="Cakupan wilayah data Kota Padang", loc="upper left", fontsize=8.5, title_fontsize=9.5,
          frameon=True, framealpha=0.95, edgecolor="#c9cdd2")
fig.text(0.01, 0.01, SUMBER + f" Zona penyangga: daratan sampai {PENYANGGA_M // 1000} km dari tepi zona merah "
         "(visualisasi perencanaan, bukan zona resmi BPBD; aplikasi hanya membedakan zona merah dan zona hijau).",
         fontsize=7, color="#5d6670", wrap=True)
fig.tight_layout(rect=(0, 0.04, 1, 1))
simpan(fig, "gambar_3_1_cakupan_wilayah.png")
plt.close(fig)
print(f"Gambar 3.1: merah {km2(merah_u.area)} km², penyangga kota {km2(peny_kota.area)} km², penyangga luar {km2(peny_luar.area)} km², "
      f"hijau lain {km2(hijau_lain.area)} km²")

# ==============================================================================
# GAMBAR 5.4  jaringan jalan pejalan kaki (geometri asli tiap ruas, menurut jenis jalan OSM) dan TES/TEA
# ==============================================================================
import re as _re
import networkx as nx
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
from matplotlib.ticker import FuncFormatter

# Jenis jalan tiap ruas dari graf sumber DB (tb_edges tidak menyimpan tag highway).
G = nx.read_graphml(ARG.graf)
assert G.number_of_nodes() == c.execute("select count(*) from tb_nodes").fetchone()[0], \
    f"{ARG.graf} bukan graf sumber basis data {VERSI}"
KELAS = {"utama": {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link"},
         "setapak": {"footway", "path", "pedestrian", "steps", "track", "bridleway", "corridor"}}
jenis = {}
for u, v, d in G.edges(data=True):
    hw = set(_re.findall(r"[a-z_]+", d.get("highway", "")))
    k = "utama" if hw & KELAS["utama"] else "setapak" if hw and hw <= KELAS["setapak"] else "lingkungan"
    jenis[(int(u), int(v))] = jenis[(int(v), int(u))] = min(jenis.get((int(u), int(v)), k), k, key=["utama", "lingkungan", "setapak"].index)
nd = dict((n, (lo, la)) for n, la, lo in c.execute("select node_id, lat, lon from tb_nodes"))
seg = {"utama": [], "lingkungan": [], "setapak": []}
for u, v, g in c.execute("select u, v, geometry from tb_edges"):
    xy = np.asarray(wkt.loads(g).coords) if g and g.startswith("LINESTRING") else np.array([nd[u], nd[v]])
    seg[jenis.get((u, v), "lingkungan")].append(xy)
n_ruas = sum(len(v) for v in seg.values())
GAYA = {"utama": dict(colors="#1f4e6b", linewidths=0.75), "lingkungan": dict(colors="#5fa3bd", linewidths=0.22),
        "setapak": dict(colors="#c2873a", linewidths=0.22)}
LABEL = {"utama": "Jalan utama", "lingkungan": "Jalan lingkungan", "setapak": "Jalan setapak/tangga"}
km_kelas = {k: sum(np.hypot(*(np.diff(a, axis=0) * [111.32 * np.cos(np.radians(0.95)), 110.57]).T).sum() for a in v)
            for k, v in seg.items()}
sumber_jalan = meta.get("sumber_jaringan_jalan", "OpenStreetMap")
# Tanggal data OSM: dari tb_metadata (sejak 2026.10.17), atau tanggal unduh graf OSMnx untuk versi sebelumnya.
tanggal = (_re.search(r"per (\d{4})-(\d{2})-(\d{2})", sumber_jalan)
           or _re.match(r"(\d{4})-(\d{2})-(\d{2})", G.graph.get("created_date", "")))
BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
per = f"{int(tanggal.group(3))} {BULAN[int(tanggal.group(2))]} {tanggal.group(1)}" if tanggal else "(tanggal tidak tercatat)"


def gambar_jalan(ax, skala=1.0):
    for k in ("setapak", "lingkungan", "utama"):
        g = GAYA[k]
        ax.add_collection(LineCollection(seg[k], colors=g["colors"], linewidths=g["linewidths"] * skala, rasterized=True,
                                         zorder={"setapak": 1, "lingkungan": 2, "utama": 3}[k]))
    for t in (ax.scatter(tes.lon, tes.lat, s=12 * skala ** 0.6, marker="s", color="#d1452f", edgecolor="white", linewidth=0.4, zorder=5),
              ax.scatter(tea.lon, tea.lat, s=22 * skala ** 0.6, marker="o", color="#13804f", edgecolor="white", linewidth=0.5, zorder=5)):
        t.set_clip_path(ax.patch)


fig, ax = plt.subplots(figsize=(8.6, 8.0))
gambar_jalan(ax)
xs = np.concatenate([a[:, 0] for v in seg.values() for a in v])
ys = np.concatenate([a[:, 1] for v in seg.values() for a in v])
ax.set_xlim(xs.min() - 0.01, xs.max() + 0.01)
ax.set_ylim(ys.min() - 0.01, ys.max() + 0.01)
ax.set_aspect(1 / np.cos(np.radians(ys.mean())))
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",") + "° BT"))
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{abs(v):.2f}".replace(".", ",") + "° LS"))
ax.set_xlabel("Bujur")
ax.set_ylabel("Lintang")
ax.grid(color="#e3e6e8", linewidth=0.5)
ax.set_axisbelow(True)
ax.set_title("Jaringan jalan pejalan kaki pada basis data lokal")
# Inset: pusat kota (Padang Barat dan sekitarnya) agar geometri tiap ruas terlihat.
ins = ax.inset_axes([0.015, 0.02, 0.32, 0.35])
gambar_jalan(ins, skala=2.2)
ins.set_xlim(100.348, 100.372)
ins.set_ylim(-0.962, -0.938)
ins.set_aspect(1 / np.cos(np.radians(0.95)))
ins.set_xticks([])
ins.set_yticks([])
ins.set_facecolor("white")
for sp in ins.spines.values():
    sp.set_color("#2a3037")
ins.set_title("Pusat kota (± 2,7 × 2,7 km)", fontsize=8.5, pad=3)
mark_inset(ax, ins, loc1=1, loc2=3, fc="none", ec="#2a3037", lw=0.7)
ax.legend(handles=[Line2D([], [], color=GAYA[k]["colors"], lw=1.6 if k == "utama" else 1.1,
                          label=f"{LABEL[k]} ({km_kelas[k]:,.0f} km)".replace(",", ".")) for k in ("utama", "lingkungan", "setapak")]
          + [Line2D([], [], marker="s", ls="", color="#d1452f", markeredgecolor="white", markersize=6, label=f"TES ({len(tes)})"),
             Line2D([], [], marker="o", ls="", color="#13804f", markeredgecolor="white", markersize=7, label=f"TEA ({len(tea)})")],
          loc="lower right", fontsize=8.5, frameon=True, framealpha=0.95)
titik = lambda n: f"{n:,}".replace(",", ".")
fig.text(0.01, 0.01, f"Sumber: basis data Siaga Padang versi {VERSI} ({titik(len(nd))} simpul; {titik(n_ruas)} ruas). Jalan: OpenStreetMap per {per} "
         "(graf pejalan kaki OSMnx);\ngaris mengikuti geometri asli tiap ruas.", fontsize=7, color="#5d6670")
fig.tight_layout(rect=(0, 0.04, 1, 1))
simpan(fig, "gambar_5_4_jaringan_jalan.png")
plt.close(fig)
print("Gambar 5.4: " + ", ".join(f"{LABEL[k]} {len(seg[k]):,} ruas / {km_kelas[k]:,.0f} km" for k in seg) + f" | jalan per {per}")

n_simpul, n_merah = c.execute("select count(*), sum(is_safe = 0) from tb_nodes").fetchone()
print(f"Basis data {VERSI}: zona merah {ha_merah:,.0f} ha, zona hijau {ha_hijau:,.0f} ha, simpul merah {n_merah:,}/{n_simpul:,}, "
      f"TES {len(tes)}, TEA {len(tea)}, ruas {n_ruas:,}, jiwa terpapar KRB {total:,} | keluaran: {OUT}")

# ==============================================================================
# GAMBAR BARU (sejak 2026.10.18): hasil pemodelan pergerakan kolektif -- beban TES dan kelompok porsi
# ==============================================================================
# Dibuat hanya bila tb_route_shares memakai kontrak porsi (docs/kontrak_porsi_tujuan.md). Semua angka dari DB:
# beban TES = jumlah demand_jiwa x porsi pada baris kelompok "beban" (bukan cadangan, TES berkapasitas, sempat).
kol_porsi = {r[1] for r in c.execute("pragma table_info(tb_route_shares)")}
if "facility_id" in kol_porsi:
    ttk = lambda v: f"{v:,.0f}".replace(",", ".")
    sr = pd.read_sql("select r.*, i.demand_jiwa from tb_route_shares r join tb_node_info i on i.node_id = r.origin_node_id", c)
    pos = sr[sr.porsi > 0]
    per_simpang = pos.groupby("origin_node_id").agg(cad=("cadangan", "max"), kap=("kapasitas_tercatat", "min"),
                                                   sempat=("sempat_15", "min"), jiwa=("demand_jiwa", "first"))
    def kelompok(r):
        if r.cad: return "cadangan"
        if not r.sempat: return "tidak_sempat"
        return "beban" if r.kap else "tanpa_kapasitas"
    per_simpang["kel"] = per_simpang.apply(kelompok, axis=1)
    beban_ids = set(per_simpang.index[per_simpang.kel == "beban"])
    b_rows = pos[pos.origin_node_id.isin(beban_ids)]
    beban = (b_rows.demand_jiwa * b_rows.porsi).groupby(b_rows.facility_id).sum()
    tk = pd.read_sql("select tes_id, nama_tes, kapasitas, lat, lon from tb_tes", c).set_index("tes_id")
    tk["x"], tk["y"] = ke_m.transform(tk.lon.to_numpy(), tk.lat.to_numpy())
    tk["beban"] = beban.reindex(tk.index).fillna(0.0)
    tk["rasio"] = tk.beban / tk.kapasitas
    berkap_t = tk[tk.kapasitas.notna()]
    tanpa_kap = tk[tk.kapasitas.isna()]
    STATUS = [("≤ 100% kapasitas", "#0ca30c", lambda r: (r > 0) & (r <= 1.0005)),
              ("100–200% kapasitas", "#fab219", lambda r: (r > 1.0005) & (r <= 2)),
              ("> 200% kapasitas", "#d03b3b", lambda r: r > 2)]
    merah_n = int(c.execute("select count(*) from tb_nodes where is_safe = 0").fetchone()[0])
    jiwa_merah = float(c.execute("select sum(i.demand_jiwa) from tb_node_info i join tb_nodes n using(node_id) "
                                 "where n.is_safe = 0").fetchone()[0])
    tanpa_tes = c.execute("select count(*), sum(i.demand_jiwa) from tb_nodes n join tb_node_info i using(node_id) where n.is_safe = 0 "
                          "and n.node_id not in (select origin_node_id from tb_route_shares)").fetchone()

    fig = plt.figure(figsize=(12.5, 7.4))
    ax = fig.add_axes([0.01, 0.07, 0.52, 0.86])
    xs_, ys_ = berkap_t.x, berkap_t.y
    bx = (xs_.min() - 2500, ys_.min() - 2500, xs_.max() + 2500, ys_.max() + 2500)
    kerangka(ax, bx, "(a) Beban model tiap TES berkapasitas")
    merah.plot(ax=ax, color="#f3d9d3", edgecolor="#d9a79c", linewidth=0.3, zorder=1)
    batas_kec(ax, label=False)
    ukuran = lambda kap: 12 + 110 * np.sqrt(kap / berkap_t.kapasitas.max())
    ax.scatter(tanpa_kap.x, tanpa_kap.y, s=10, marker="x", color="#8a8f96", linewidth=0.7, zorder=4)
    tanpa_beban = berkap_t[berkap_t.beban < 0.5]
    ax.scatter(tanpa_beban.x, tanpa_beban.y, s=ukuran(tanpa_beban.kapasitas), facecolor="white", edgecolor="#8a8f96",
               linewidth=0.8, zorder=5)
    for lbl, warna, syarat in STATUS:
        d = berkap_t[syarat(berkap_t.rasio) & (berkap_t.beban >= 0.5)]
        ax.scatter(d.x, d.y, s=ukuran(d.kapasitas), color=warna, edgecolor="white", linewidth=0.8, zorder=6)
    skala_utara(ax, 2)
    n_stat = [int((syarat(berkap_t.rasio) & (berkap_t.beban >= 0.5)).sum()) for _, _, syarat in STATUS]
    fig.legend(handles=[Line2D([], [], marker="o", ls="", color=w, markeredgecolor="white", markersize=8,
                               label=f"{l} ({n} TES)") for (l, w, _), n in zip(STATUS, n_stat)]
               + [Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor="#8a8f96", markersize=8,
                         label=f"Tidak menerima beban ({len(tanpa_beban)} TES)"),
                  Line2D([], [], marker="x", ls="", color="#8a8f96", markersize=6,
                         label=f"Tanpa kapasitas, hanya cadangan ({len(tanpa_kap)} TES)"),
                  Patch(facecolor="#f3d9d3", edgecolor="#d9a79c", label="Zona merah")],
               title="Peta (a): beban model terhadap kapasitas TES (ukuran titik = kapasitas)", loc="lower left",
               bbox_to_anchor=(0.51, 0.12), ncol=2, fontsize=8.5, title_fontsize=8.5, frameon=True, framealpha=0.95,
               edgecolor="#c9cdd2")

    ax2 = fig.add_axes([0.70, 0.43, 0.27, 0.47])
    urutan_kel = [("beban", "Ke TES berkapasitas (dibagi model)"), ("cadangan", "Keluar zona (TEA/zona hijau)"),
                  ("tidak_sempat", "Tidak ada TES yang sempat"), ("tanpa_kapasitas", "Hanya TES tanpa kapasitas"),
                  ("tanpa_tes", "Tanpa TES lolos syarat arah")]
    nilai = {k: (per_simpang[per_simpang.kel == k].jiwa.sum(), int((per_simpang.kel == k).sum())) for k, _ in urutan_kel[:4]}
    nilai["tanpa_tes"] = (float(tanpa_tes[1] or 0), int(tanpa_tes[0]))
    yy = np.arange(len(urutan_kel))[::-1]
    jiwa_k = [nilai[k][0] for k, _ in urutan_kel]
    ribu = np.array(jiwa_k) / 1000
    ax2.barh(yy, ribu, height=0.62, color="#2a78d6", edgecolor="white", linewidth=2)
    for y_, (k, lbl) in zip(yy, urutan_kel):
        j, s = nilai[k]
        persen = f"{j / jiwa_merah * 100:.1f}".replace(".", ",")
        ax2.text(j / 1000 + ribu.max() * 0.03, y_, f"{ttk(j)} jiwa ({persen}%)\n{ttk(s)} simpang",
                 va="center", fontsize=8, color="#2a3037", linespacing=1.25)
    ax2.set_yticks(yy, [lbl for _, lbl in urutan_kel], fontsize=9)
    ax2.set_xlim(0, ribu.max() * 1.6)
    ax2.set_xticks([0, 25, 50, 75, 100])
    ax2.set_xlabel("Ribu jiwa (t = 0, batas 15 menit)", fontsize=9)
    for s_ in ("top", "right"):
        ax2.spines[s_].set_visible(False)
    ax2.spines["left"].set_color("#c3c2b7"); ax2.spines["bottom"].set_color("#c3c2b7")
    ax2.grid(axis="x", color="#e1e0d9", linewidth=0.6); ax2.set_axisbelow(True)
    ax2.set_title("(b) Tujuan penduduk menurut kelompok porsi", loc="right")
    lebih = (berkap_t.beban - berkap_t.kapasitas).clip(lower=0).sum()
    fig.text(0.51, 0.05, f"Kapasitas 167 TES: {ttk(berkap_t.kapasitas.sum())} jiwa. Beban model {ttk(berkap_t.beban.sum())} jiwa ke "
             f"{int((berkap_t.beban >= 0.5).sum())} TES; kelebihan {ttk(lebih)} jiwa di {n_stat[1] + n_stat[2]} TES.\n"
             f"Persentase (b) terhadap {ttk(jiwa_merah)} jiwa di {ttk(merah_n)} simpang zona merah.", fontsize=8, color="#5d6670")
    fig.text(0.01, 0.012, f"Sumber: basis data Siaga Padang versi {VERSI} (tb_route_shares, tb_node_info, tb_tes); program linear "
             "minimum jiwa × menit dengan batas kapasitas, laju 0,894 m/s; kapasitas: perkiraan kesepakatan warga (BPBD 2025) "
             "dan daftar BPBD 2019.", fontsize=7, color="#5d6670")
    simpan(fig, "gambar_pemodelan_kolektif_beban_tes.png")
    plt.close(fig)
    print(f"Gambar pemodelan kolektif: beban {ttk(berkap_t.beban.sum())} jiwa, {int((berkap_t.beban >= 0.5).sum())} TES, "
          f"melebihi {n_stat[1] + n_stat[2]} TES (kelebihan {ttk(lebih)} jiwa)")
