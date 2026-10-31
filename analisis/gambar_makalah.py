"""
Gambar untuk makalah GEMASTIK (format dua kolom, lebar satu kolom 8,9 cm).

Gambar dibuat dari basis data Siaga Padang (default hasil_build/ranah_siaga_v4.db) dengan perhitungan yang sama
seperti analisis/gambar_laporan.py, tetapi diringkas agar terbaca pada lebar satu kolom dan saat dicetak hitam-putih
(status beban dibedakan dengan warna sekaligus bentuk penanda).

Keluaran (analisis/output/gambar_makalah/<versi>/):
  - makalah_peta_beban_tes.png  : beban model tiap TES berkapasitas terhadap kapasitasnya (kelompok pembagian 89.158 jiwa)
  - makalah_waktu_ponsel.png    : waktu pemrosesan arahan pada tujuh ponsel (Tabel 6.5 laporan akhir, data 2026.10.16)

Pemakaian: env\\Scripts\\python.exe analisis\\gambar_makalah.py [--db <ranah_siaga_v4.db>]
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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
_arg = argparse.ArgumentParser()
_arg.add_argument("--db", default=os.path.join("hasil_build", "ranah_siaga_v4.db"))
ARG = _arg.parse_args()
BASEMAP = os.path.join("Data BPBD", "KRB Padang [2023-2027]", "02_BASEMAP", "Basemap.gdb")
M = "EPSG:32747"
CM = 1 / 2.54
LEBAR_KOLOM = 8.9 * CM

# Palet sama dengan gambar_laporan.py; huruf Arial mengikuti label gambar Helvetica pada templat makalah.
LAUT, DARAT_LUAR, GARIS_KEC = "#dbe8f0", "#f4f2ec", "#7c8590"
TEKS, TEKS_REDUP = "#2a3037", "#5d6670"
plt.rcParams.update({"font.family": "Arial", "font.size": 7, "axes.linewidth": 0.6})

c = sqlite3.connect(ARG.db)
VERSI = dict(c.execute("select kunci, nilai from tb_metadata"))["versi"]
OUT = os.path.join("analisis", "output", "gambar_makalah", VERSI)
os.makedirs(OUT, exist_ok=True)
ttk = lambda v: f"{v:,.0f}".replace(",", ".")


def simpan(fig, nama):
    fig.savefig(os.path.join(OUT, nama), dpi=400)
    plt.close(fig)


# ==============================================================================
# Latar peta: zona merah, daratan dari garis pantai OSM, batas kecamatan (sama dengan gambar_laporan.py)
# ==============================================================================
merah = gpd.GeoSeries([wkt.loads(w) for (w,) in c.execute("select geometry_wkt from tb_inundation_zones")], crs=4326).to_crs(M)
kec = gpd.read_file(BASEMAP, layer="Batas_Administrasi_Kecamatan_AR").to_crs(M)
kota = kec.union_all()
ke_m = Transformer.from_crs(4326, M, always_xy=True)
garis = []
for w in json.load(open(os.path.join("data_osm", "pantai_osm.json"), encoding="utf-8"))["elements"]:
    if w.get("geometry"):
        x, y = ke_m.transform([p["lon"] for p in w["geometry"]], [p["lat"] for p in w["geometry"]])
        garis.append(shapely.LineString(np.column_stack([x, y])))
kotak = shapely.box(*kota.buffer(3000).bounds)
muka = shapely.get_parts(shapely.polygonize(shapely.get_parts(shapely.union_all([shapely.union_all(garis).intersection(kotak), kotak.boundary]))))
isi = np.array([f.intersection(kota).area for f in muka])
darat = shapely.union_all([f for f, a in zip(muka, isi) if a > 0.5 * f.area or a > 0.1 * kota.area
                           or (a == 0 and f.area < 5e6 and not f.touches(kotak.boundary))])
assert darat.area < kotak.area * 0.85 and kota.difference(darat).area < 0.01 * kota.area, "Poligon daratan memuat laut"

# ==============================================================================
# GAMBAR: beban model tiap TES berkapasitas (logika sama dengan gambar_pemodelan_kolektif_beban_tes.png)
# ==============================================================================
sr = pd.read_sql("select r.*, i.demand_jiwa from tb_route_shares r join tb_node_info i on i.node_id = r.origin_node_id", c)
pos = sr[sr.porsi > 0]
per_simpul = pos.groupby("origin_node_id").agg(cad=("cadangan", "max"), kap=("kapasitas_tercatat", "min"),
                                              sempat=("sempat_15", "min"))
beban_ids = per_simpul.index[(per_simpul.cad == 0) & (per_simpul.sempat == 1) & (per_simpul.kap == 1)]
b_rows = pos[pos.origin_node_id.isin(beban_ids)]
beban = (b_rows.demand_jiwa * b_rows.porsi).groupby(b_rows.facility_id).sum()
tk = pd.read_sql("select tes_id, kapasitas, lat, lon from tb_tes", c).set_index("tes_id")
tk["x"], tk["y"] = ke_m.transform(tk.lon.to_numpy(), tk.lat.to_numpy())
tk["beban"] = beban.reindex(tk.index).fillna(0.0)
tk["rasio"] = tk.beban / tk.kapasitas
berkap = tk[tk.kapasitas.notna()]
tanpa_kap = tk[tk.kapasitas.isna()]
tanpa_beban = berkap[berkap.beban < 0.5]
dapat = berkap[berkap.beban >= 0.5]
# Warna dan bentuk berbeda agar tetap terbaca pada cetakan hitam-putih.
STATUS = [("≤ 100%", "#0ca30c", "o", (dapat.rasio <= 1.0005)),
          ("100–200%", "#fab219", "^", (dapat.rasio > 1.0005) & (dapat.rasio <= 2)),
          ("> 200%", "#d03b3b", "s", (dapat.rasio > 2))]
lebih = (berkap.beban - berkap.kapasitas).clip(lower=0).sum()
n_lebih = int((dapat.rasio > 1.0005).sum())

x0, y0 = berkap.x.min() - 1200, berkap.y.min() - 1200
x1, y1 = berkap.x.max() + 1200, berkap.y.max() + 1200
lebar_peta = 3.3 * CM
tinggi_peta = lebar_peta * (y1 - y0) / (x1 - x0)
fig = plt.figure(figsize=(LEBAR_KOLOM, tinggi_peta + 0.2 * CM))
ax = fig.add_axes([0.005, 0.1 * CM / (tinggi_peta + 0.2 * CM), lebar_peta / LEBAR_KOLOM, tinggi_peta / (tinggi_peta + 0.2 * CM)])
ax.set_facecolor(LAUT)
gpd.GeoSeries([darat], crs=M).plot(ax=ax, color=DARAT_LUAR, linewidth=0, zorder=0)
merah.plot(ax=ax, color="#f3d9d3", edgecolor="#d9a79c", linewidth=0.2, zorder=1)
kec.boundary.plot(ax=ax, color=GARIS_KEC, linewidth=0.35, linestyle=(0, (4, 2)), zorder=2)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_color("#9aa3ab")
ukuran = lambda kap: 4 + 40 * np.sqrt(kap / berkap.kapasitas.max())
ax.scatter(tanpa_kap.x, tanpa_kap.y, s=6, marker="x", color="#8a8f96", linewidth=0.5, zorder=4)
ax.scatter(tanpa_beban.x, tanpa_beban.y, s=ukuran(tanpa_beban.kapasitas), facecolor="white", edgecolor="#8a8f96",
           linewidth=0.5, zorder=5)
for _, warna, bentuk, syarat in STATUS:
    d = dapat[syarat]
    ax.scatter(d.x, d.y, s=ukuran(d.kapasitas), marker=bentuk, color=warna, edgecolor=TEKS, linewidth=0.4, zorder=6)
# Skala 2 km dan panah utara
bx, by = x0 + 0.06 * (x1 - x0), y0 + 0.025 * (y1 - y0)
for i in range(2):
    ax.add_patch(Rectangle((bx + i * 1000, by), 1000, 0.006 * (y1 - y0), facecolor=TEKS if i == 0 else "white",
                           edgecolor=TEKS, linewidth=0.4, zorder=10))
ax.text(bx, by + 0.012 * (y1 - y0), "0", ha="center", fontsize=5.5, zorder=10)
ax.text(bx + 2000, by + 0.012 * (y1 - y0), "2 km", ha="center", fontsize=5.5, zorder=10)
ux, uy = x1 - 0.12 * (x1 - x0), y0 + 0.03 * (y1 - y0)
ax.annotate("", xy=(ux, uy + 0.045 * (y1 - y0)), xytext=(ux, uy), arrowprops=dict(arrowstyle="-|>", color=TEKS, lw=0.8), zorder=10)
ax.text(ux, uy + 0.05 * (y1 - y0), "U", ha="center", va="bottom", fontsize=6.5, fontweight="bold", zorder=10)

n_stat = [int(s.sum()) for *_, s in STATUS]
legenda = ([Line2D([], [], marker=b, ls="", color=w, markeredgecolor=TEKS, markeredgewidth=0.4, markersize=5,
                   label=f"{l} ({n} TES)") for (l, w, b, _), n in zip(STATUS, n_stat)]
           + [Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor="#8a8f96", markersize=5,
                     label=f"Tanpa beban ({len(tanpa_beban)} TES)"),
              Line2D([], [], marker="x", ls="", color="#8a8f96", markersize=4.5,
                     label=f"Tanpa angka daya\ntampung ({len(tanpa_kap)} TES)"),
              Patch(facecolor="#f3d9d3", edgecolor="#d9a79c", label="Zona merah"),
              Line2D([], [], color=GARIS_KEC, ls=(0, (4, 2)), lw=0.6, label="Batas kecamatan")])
fig.legend(handles=legenda, title="Beban terhadap\ndaya tampung TES", loc="upper left", alignment="left",
           bbox_to_anchor=(lebar_peta / LEBAR_KOLOM + 0.02, 0.99), fontsize=6.5, title_fontsize=6.5,
           frameon=False, handletextpad=0.5, labelspacing=0.75)
fig.text(lebar_peta / LEBAR_KOLOM + 0.03, 0.03,
         f"Ukuran titik sebanding\ndengan daya tampung.\n\nBeban {ttk(berkap.beban.sum())} jiwa\nke {len(dapat)} TES; "
         f"kelebihan\n{ttk(lebih)} jiwa di {n_lebih} TES.", fontsize=6, color=TEKS_REDUP, va="bottom", linespacing=1.3)
simpan(fig, "makalah_peta_beban_tes.png")
print(f"Peta beban TES: {len(dapat)} TES menerima beban, {n_lebih} melebihi daya tampung, kelebihan {ttk(lebih)} jiwa, "
      f"tinggi {tinggi_peta / CM + 0.2:.1f} cm")

# ==============================================================================
# GAMBAR: waktu pemrosesan arahan per ponsel (Tabel 6.5 laporan akhir; 20 koordinat, data 2026.10.16)
# ==============================================================================
PONSEL = [  # nama, median, persentil ke-95, maksimum (ms)
    ("Infinix X6855 (Helio G100)", 706, 789, 884),
    ("Galaxy A15 (Helio G99)", 454, 531, 624),
    ("POCO F5 (Snapdragon 7+ Gen 2)", 354, 414, 447),
    ("Galaxy A55 (Exynos 1480)", 271, 333, 351),
    ("Infinix GT 20 Pro (Dimensity 8200)", 240, 291, 294),
    ("POCO F7 (Snapdragon SM8735)", 222, 267, 269),
    ("Xiaomi 15 (Snapdragon 8 Elite)", 152, 209, 225),
]
fig, ax = plt.subplots(figsize=(LEBAR_KOLOM, 4.1 * CM))
yy = np.arange(len(PONSEL))[::-1]
for y_, (_, med, p95, mx) in zip(yy, PONSEL):
    ax.plot([med, mx], [y_, y_], color="#7c8590", lw=1.0, zorder=2)
    ax.plot([p95], [y_], marker="|", color=TEKS, markersize=5, zorder=3)
    ax.plot([med], [y_], marker="o", color="#2a78d6", markeredgecolor=TEKS, markeredgewidth=0.4, markersize=4.5, zorder=4)
    ax.text(mx + 20, y_, f"{mx}", va="center", fontsize=6, color=TEKS_REDUP)
ax.axvline(1000, color="#d03b3b", lw=0.8, ls=(0, (4, 2)), zorder=1)
ax.text(985, yy.max() + 0.55, "Target < 1 detik", ha="right", va="center", fontsize=6, color="#d03b3b")
ax.set_yticks(yy, [p[0] for p in PONSEL], fontsize=5.8)
ax.set_xlim(0, 1050); ax.set_ylim(-0.6, len(PONSEL) - 0.1)
ax.set_xticks([0, 200, 400, 600, 800, 1000])
ax.set_xlabel("Waktu pemrosesan setelah koordinat diterima (ms)", fontsize=6.3)
ax.tick_params(axis="x", labelsize=6)
ax.tick_params(axis="y", length=0)
for s_ in ("top", "right", "left"):
    ax.spines[s_].set_visible(False)
ax.spines["bottom"].set_color("#9aa3ab")
ax.grid(axis="x", color="#e1e0d9", linewidth=0.5); ax.set_axisbelow(True)
ax.legend(handles=[Line2D([], [], marker="o", ls="", color="#2a78d6", markeredgecolor=TEKS, markeredgewidth=0.4, markersize=4.5, label="Median"),
                   Line2D([], [], marker="|", ls="", color=TEKS, markersize=5, label="Persentil ke-95"),
                   Line2D([], [], color="#7c8590", lw=1.0, label="Median–maksimum")],
          loc="lower right", fontsize=6, frameon=True, framealpha=0.95, edgecolor="#c9cdd2", handletextpad=0.4)
fig.subplots_adjust(left=0.41, right=0.97, top=0.93, bottom=0.25)
simpan(fig, "makalah_waktu_ponsel.png")
print("Grafik waktu ponsel: 7 ponsel, maksimum", max(p[3] for p in PONSEL), "ms")
