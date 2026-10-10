import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from shapely.geometry import box

print("=" * 80)
print("GENERATOR PETA ZONA RAWAN TSUNAMI KOTA PADANG (V3 — BUFFER MENGELILINGI)")
print("=" * 80)

# ---------------------------------------------------------------------------
# KONSTANTA
# ---------------------------------------------------------------------------
CRS_UTM   = "EPSG:32747"        # UTM 47S — satuan meter, wajib untuk buffer
CRS_WGS   = "EPSG:4326"
BUFFER_M  = 2000                # lebar sabuk penyangga
BG_RAWAN_M = 3500               # jangkauan rawan Balai Gadang dari tepi barat
SLIVER_M2 = 1000                # buang serpihan poligon < 1000 m²

# Kandidat berkas land mask yang lebih luas dari batas Kota Padang.
# Cukup salah satu yang ada. Sumber: GADM level 2 Sumatera Barat, BIG, atau
# batas kabupaten/kota Sumbar apa pun. Tanpa ini buffer akan terpotong di
# batas administrasi kota (utara & selatan) — persis bug yang sedang diperbaiki.
KANDIDAT_LAND_MASK = [
    "batas_sumbar.geojson",
    "batas_kabkota_sumbar.geojson",
    "gadm41_IDN_2_sumbar.geojson",
    "land_mask.geojson",
]

# ---------------------------------------------------------------------------
# 1. BATAS KELURAHAN KOTA PADANG
# ---------------------------------------------------------------------------
gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
gdf_utm = gdf_kel.to_crs(CRS_UTM)

kolom_nama = gdf_utm.select_dtypes(include=['object', 'string']).columns[0]
gdf_utm['NAMA_UPPER'] = gdf_utm[kolom_nama].astype(str).str.upper().str.strip()

# ---------------------------------------------------------------------------
# 2. SEPARASI DARATAN UTAMA & PULAU LEPAS PANTAI
# ---------------------------------------------------------------------------
gdf_exp = gdf_utm.explode(index_parts=False).reset_index(drop=True)

is_pulau = gdf_exp.geometry.centroid.apply(
    lambda c: c.x < 647000 or (c.x < 651000 and c.y < 9890000)
)
gdf_mainland = gdf_exp[~is_pulau].copy()
gdf_islands  = gdf_exp[is_pulau].copy()

mainland_union = gdf_mainland.geometry.union_all()
island_union   = gdf_islands.geometry.union_all()

print(f"[1/6] Daratan utama: {mainland_union.area/1e6:6.1f} km² | "
      f"Pulau: {island_union.area/1e6:.1f} km² ({len(gdf_islands)} poligon)")

# ---------------------------------------------------------------------------
# 3. LAND MASK LUAS  — [FIX 1] inti perbaikan
#    Buffer dipotong oleh DARATAN, bukan oleh BATAS KOTA. Kalau dipotong batas
#    kota, sabuk 2 km lenyap di utara (Padang Pariaman) dan selatan (Pesisir
#    Selatan) karena zona merah menempel langsung ke batas administrasi.
# ---------------------------------------------------------------------------
land_union = None
for berkas in KANDIDAT_LAND_MASK:
    if os.path.exists(berkas):
        gdf_land = gpd.read_file(berkas).to_crs(CRS_UTM)
        land_union = gdf_land.geometry.union_all()
        print(f"[2/6] Land mask dimuat dari '{berkas}' ({land_union.area/1e6:.0f} km²)")
        break

if land_union is None:
    land_union = mainland_union
    print("[2/6] ⚠  Land mask luas TIDAK ditemukan. Buffer akan terpotong di batas")
    print("        Kota Padang (utara & selatan). Letakkan salah satu berkas ini")
    print("        di folder kerja untuk hasil yang benar:")
    for berkas in KANDIDAT_LAND_MASK:
        print(f"          - {berkas}")

# Daratan yang boleh ditempati buffer: land mask ∪ daratan kota ∪ pulau
land_mask_final = land_union.union(mainland_union).union(island_union)

# ---------------------------------------------------------------------------
# 4. KLASIFIKASI KELURAHAN RAWAN
# ---------------------------------------------------------------------------
df_pend = pd.read_csv("penduduk_kota_padang.csv")
bpbd_exposed = set(df_pend['DESA'].astype(str).str.upper().str.strip())

kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING',
    'BUKIK GADO GADO': 'BUKIT GADO-GADO', 'KAMPUNG JAO': 'KAMPUNG JAWA',
    'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI',
    'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH', 'MATO AIE': 'MATA AIR',
    'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX',
    'PASIR NAN TIGO': 'PASIE NAN TIGO', 'TALUAK BAYUA': 'TELUK BAYUR',
    'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX',
}

rawan_set = {kelurahan_alias.get(k, k) for k in bpbd_exposed}
rawan_set |= {'BEROK NIPAH', 'PASA GADANG'}

perbukitan = ['BALAI GADANG', 'LUBUK MINTURUN', 'KURANJI', 'BATU GADANG',
              'INDARUNG', 'PADANG BESI', 'KOTO LALANG', 'TARANTANG', 'BANDA BUEK']
rawan_set -= set(perbukitan)

gdf_coastal = gdf_mainland[gdf_mainland['NAMA_UPPER'].isin(rawan_set)]

# Balai Gadang: hanya sisi baratnya yang rawan.
bg_geom = gdf_mainland.loc[gdf_mainland['NAMA_UPPER'] == 'BALAI GADANG', 'geometry'].iloc[0]
bx0, by0, _, by1 = bg_geom.bounds
bg_red_part = bg_geom.intersection(box(bx0, by0, bx0 + BG_RAWAN_M, by1))

red_union_mainland = gpd.GeoSeries(
    list(gdf_coastal.geometry) + [bg_red_part], crs=CRS_UTM
).union_all()

# [FIX 2] Pulau digabung SEBELUM buffer dihitung, supaya pulau ikut punya sabuk.
red_union_full = red_union_mainland.union(island_union)

print(f"[3/6] Kelurahan rawan: {len(gdf_coastal)} | "
      f"Zona merah total: {red_union_full.area/1e6:.1f} km²")

# ---------------------------------------------------------------------------
# 5. BUFFER 2 KM
# ---------------------------------------------------------------------------
buffer_ring = red_union_full.buffer(BUFFER_M).difference(red_union_full)
buffer_2km_yellow = buffer_ring.intersection(land_mask_final)

# Zona aman = daratan Kota Padang di luar merah dan di luar buffer
safe_land_geom = (mainland_union
                  .difference(red_union_full)
                  .difference(buffer_2km_yellow))

print(f"[4/6] Buffer mentah: {buffer_ring.area/1e6:6.1f} km² → "
      f"setelah dipotong daratan: {buffer_2km_yellow.area/1e6:.1f} km²")

# ---------------------------------------------------------------------------
# 6. PEMBERSIH GEOMETRI  — [FIX 3]
#    Menangani GeometryCollection, memperbaiki poligon tak sahih, dan membuang
#    serpihan mikro sisa operasi difference.
# ---------------------------------------------------------------------------
def bersihkan_geometri(geom_union, label=""):
    gdf_tmp = gpd.GeoDataFrame(geometry=[geom_union], crs=CRS_UTM)
    gdf_tmp = gdf_tmp.explode(index_parts=False).reset_index(drop=True)

    # GeometryCollection perlu satu putaran explode lagi
    if (gdf_tmp.geometry.type == 'GeometryCollection').any():
        gdf_tmp = gdf_tmp.explode(index_parts=False).reset_index(drop=True)

    gdf_tmp = gdf_tmp[gdf_tmp.geometry.type.isin(['Polygon', 'MultiPolygon'])].copy()
    gdf_tmp['geometry'] = gdf_tmp.geometry.buffer(0)          # rapikan self-intersection
    sebelum = len(gdf_tmp)
    gdf_tmp = gdf_tmp[gdf_tmp.geometry.area > SLIVER_M2]
    if label and sebelum != len(gdf_tmp):
        print(f"        {label}: {sebelum - len(gdf_tmp)} serpihan <{SLIVER_M2} m² dibuang")
    return gdf_tmp

gdf_red    = bersihkan_geometri(red_union_full,    "merah").to_crs(CRS_WGS)
gdf_yellow = bersihkan_geometri(buffer_2km_yellow, "buffer").to_crs(CRS_WGS)
gdf_green  = bersihkan_geometri(safe_land_geom,    "aman").to_crs(CRS_WGS)
gdf_kel_wgs = gdf_utm.to_crs(CRS_WGS)

# ---------------------------------------------------------------------------
# 7. TITIK EVAKUASI SEMENTARA (TES)
# ---------------------------------------------------------------------------
file_tes = ("data_tes_padang_lengkap_berkoordinat.csv"
            if os.path.exists("data_tes_padang_lengkap_berkoordinat.csv")
            else "Koordinat Evakuasi TES - Sheet1.csv")
df_tes = pd.read_csv(file_tes)

def parse_coord(val):
    try:
        return float(str(val).strip().replace(',', '.'))
    except (ValueError, TypeError):
        return np.nan

lat_col = 'Latitude'  if 'Latitude'  in df_tes.columns else 'Clean_Lat'
lon_col = 'Longitude' if 'Longitude' in df_tes.columns else 'Clean_Lon'

df_tes['lat_c'] = df_tes[lat_col].apply(parse_coord)
df_tes['lon_c'] = df_tes[lon_col].apply(parse_coord)
df_tes = df_tes.dropna(subset=['lat_c', 'lon_c']).drop_duplicates(subset=['lat_c', 'lon_c'])

# [FIX 4] Batas kotak Kota Padang penuh, bukan hanya ambang bujur barat.
# Titik di luar kotak dilaporkan, tidak dibuang diam-diam.
KOTAK_PADANG = (100.29, -1.42, 100.55, -0.72)   # lon_min, lat_min, lon_max, lat_max
di_dalam = (df_tes['lon_c'].between(KOTAK_PADANG[0], KOTAK_PADANG[2]) &
            df_tes['lat_c'].between(KOTAK_PADANG[1], KOTAK_PADANG[3]))

if (~di_dalam).any():
    print(f"[5/6] ⚠  {(~di_dalam).sum()} titik TES di luar kotak Kota Padang, "
          f"kemungkinan galat koordinat:")
    for _, r in df_tes[~di_dalam].iterrows():
        nama = r.get('Nama_Bersih', r.get('Lokasi_TES', '(tanpa nama)'))
        print(f"          {nama} → ({r['lat_c']}, {r['lon_c']})")

df_tes = df_tes[di_dalam].copy()
print(f"[5/6] TES dipakai: {len(df_tes)} titik")

# ---------------------------------------------------------------------------
# 8. RENDER PNG 300 DPI
# ---------------------------------------------------------------------------
print("[6/6] Merender PNG dan peta web...")

fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
fig.patch.set_facecolor('#0f172a')
ax.set_facecolor('#0f172a')

gdf_green.plot(ax=ax, facecolor='#10b981', edgecolor='#047857', linewidth=1.0, alpha=0.50)
gdf_yellow.plot(ax=ax, facecolor='#f59e0b', edgecolor='#d97706', linewidth=1.5, alpha=0.65)
gdf_red.plot(ax=ax, facecolor='#ef4444', edgecolor='#b91c1c', linewidth=1.2, alpha=0.65)
gdf_kel_wgs.boundary.plot(ax=ax, color='#ffffff', linewidth=0.4, linestyle=':', alpha=0.35)

ax.scatter(df_tes['lon_c'], df_tes['lat_c'], s=24, color='#38bdf8',
           edgecolor='#ffffff', linewidth=0.6, zorder=5)

# [FIX 5] Bingkai dari gabungan merah + kuning, bukan kuning saja — kalau buffer
# terpotong, peta tidak lagi ikut terpotong bersamanya.
min_lon, min_lat, max_lon, max_lat = pd.concat([gdf_red, gdf_yellow]).total_bounds
m_lon = (max_lon - min_lon) * 0.08
m_lat = (max_lat - min_lat) * 0.08
ax.set_xlim(min_lon - m_lon, max_lon + m_lon)
ax.set_ylim(min_lat - m_lat, max_lat + m_lat)

plt.title("Peta Zona Rawan Tsunami Kota Padang, Buffer Zone 2 km & Zona Aman",
          fontsize=14, fontweight='bold', color='#f8fafc', pad=18)
ax.text(0.5, 0.975, "Sabuk penyangga 2 km mengelilingi zona merah di atas daratan — "
        "area laut bebas buffer", transform=ax.transAxes, ha='center',
        fontsize=9.2, color='#94a3b8', style='italic')

# [FIX 6] Istilah "shelter" diganti "TES" sesuai aturan kata proyek.
legenda = [
    mpatches.Patch(facecolor='#ef4444', edgecolor='#b91c1c', alpha=0.65,
                   label=f'Zona Rawan Tsunami ({red_union_full.area/1e6:.1f} km²)'),
    mpatches.Patch(facecolor='#f59e0b', edgecolor='#d97706', alpha=0.65,
                   label=f'Buffer Zone 2 km Daratan ({buffer_2km_yellow.area/1e6:.1f} km²)'),
    mpatches.Patch(facecolor='#10b981', edgecolor='#047857', alpha=0.50,
                   label=f'Zona Aman Perbukitan ({safe_land_geom.area/1e6:.1f} km²)'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#38bdf8', markersize=6,
           label=f'Gedung TES ({len(df_tes)} lokasi)'),
]
ax.legend(handles=legenda, loc='lower right', facecolor='#0f172a', edgecolor='#334155',
          fontsize=8.5, labelcolor='#f8fafc', framealpha=0.92, borderpad=0.8)

ax.tick_params(colors='#94a3b8', labelsize=8)
ax.grid(True, color='#1e293b', linestyle=':', linewidth=0.5, alpha=0.7)
ax.set_xlabel("Bujur (Longitude)", color='#cbd5e1', fontsize=9, labelpad=8)
ax.set_ylabel("Lintang (Latitude)", color='#cbd5e1', fontsize=9, labelpad=8)

plt.savefig("peta_zona_rawan_tsunami_padang.png", bbox_inches='tight',
            facecolor=fig.get_facecolor(), dpi=300)
plt.close()
print("        PNG  → peta_zona_rawan_tsunami_padang.png")

# ---------------------------------------------------------------------------
# 9. PETA INTERAKTIF FOLIUM
# ---------------------------------------------------------------------------
peta_web = folium.Map(location=[(min_lat + max_lat) / 2, (min_lon + max_lon) / 2],
                      zoom_start=12, tiles='CartoDB positron')

def tambah_layer(gdf, nama, isi, garis, tebal, opasitas):
    folium.GeoJson(gdf, name=nama, style_function=lambda _x, i=isi, g=garis,
                   t=tebal, o=opasitas: {
                       'fillColor': i, 'color': g, 'weight': t, 'fillOpacity': o
                   }).add_to(peta_web)

tambah_layer(gdf_green,  "🟢 Zona Aman Daratan / Perbukitan", '#10b981', '#047857', 1.5, 0.40)
tambah_layer(gdf_yellow, "🟡 Buffer Zone 2 km (Daratan)",     '#f59e0b', '#d97706', 2.0, 0.55)
tambah_layer(gdf_red,    "🔴 Zona Rawan Tsunami",             '#ef4444', '#b91c1c', 1.8, 0.55)

folium.GeoJson(
    gdf_kel_wgs, name="📍 Batas Administrasi Kelurahan",
    style_function=lambda _x: {'fillColor': 'transparent', 'color': '#475569',
                               'weight': 0.8, 'dashArray': '3, 3'},
    tooltip=folium.GeoJsonTooltip(fields=['NAMA_UPPER'], aliases=['Kelurahan:'])
).add_to(peta_web)

grup_tes = folium.FeatureGroup(name="🏢 Gedung TES")
for _, r in df_tes.iterrows():
    nama = r.get('Nama_Bersih', r.get('Lokasi_TES', 'Gedung TES'))
    folium.CircleMarker(
        location=[r['lat_c'], r['lon_c']], radius=5,
        color='#0284c7', fill=True, fill_color='#38bdf8', fill_opacity=0.9,
        popup=f"<b>{nama}</b>", tooltip=f"TES: {nama}"
    ).add_to(grup_tes)
grup_tes.add_to(peta_web)

banner = f"""
<div style="position: fixed; top: 15px; left: 60px; width: 460px;
    background: rgba(15,23,42,0.94); backdrop-filter: blur(10px); color: white;
    padding: 14px 18px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    font-family: 'Segoe UI', Arial, sans-serif; z-index: 9999;
    border: 1px solid rgba(255,255,255,0.15);">
  <div style="font-size:13px; font-weight:800; color:#38bdf8;
       text-transform:uppercase; letter-spacing:0.5px;">
    PETA ZONA RAWAN, BUFFER 2 KM &amp; ZONA AMAN
  </div>
  <div style="font-size:11px; color:#cbd5e1; margin-top:6px; line-height:1.6;">
    <div>🔴 <strong>Zona Rawan Tsunami:</strong> {red_union_full.area/1e6:.1f} km²</div>
    <div>🟡 <strong>Buffer Zone 2 km:</strong> {buffer_2km_yellow.area/1e6:.1f} km²</div>
    <div>🟢 <strong>Zona Aman Perbukitan:</strong> {safe_land_geom.area/1e6:.1f} km²</div>
    <div>🏢 <strong>Gedung TES:</strong> {len(df_tes)} lokasi</div>
  </div>
</div>
"""
peta_web.get_root().html.add_child(folium.Element(banner))
folium.LayerControl().add_to(peta_web)
peta_web.save("peta_zona_rawan_tsunami_padang.html")
print("        HTML → peta_zona_rawan_tsunami_padang.html")
print("=" * 80)