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
from shapely.geometry import box, Polygon, MultiPolygon
from pyproj import Transformer

print("=" * 80)
print("GENERATOR PETA ZONA RAWAN TSUNAMI KOTA PADANG, BUFFER 2 KM CONTINUOUS & ZONA AMAN")
print("=================================================================================")

# 1. Memuat GeoJSON Batas Kelurahan Kota Padang
file_geojson = "batas_kelurahan_kota_padang.geojson"
gdf_kel = gpd.read_file(file_geojson)

# Transformasi CRS ke EPSG:32747 (UTM Zone 47S)
gdf_utm = gdf_kel.to_crs("EPSG:32747")

kolom_nama = gdf_utm.select_dtypes(include=['object', 'string']).columns[0]
gdf_utm['NAMA_UPPER'] = gdf_utm[kolom_nama].astype(str).str.upper().str.strip()

# Memuat Data Penduduk BPBD & Klasifikasi Kelurahan Pesisir
df_pend = pd.read_csv("penduduk_kota_padang.csv")
bpbd_exposed = set(df_pend['DESA'].astype(str).str.upper().str.strip())

kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

rawan_set = set([kelurahan_alias.get(k, k) for k in bpbd_exposed])
coastal_additions = ['BEROK NIPAH', 'PASA GADANG']
for c in coastal_additions: rawan_set.add(c)

# Kelurahan perbukitan/pedalaman dikeluarkan dari rawan 100%
perbukitan_list = ['BALAI GADANG', 'LUBUK MINTURUN', 'KURANJI', 'BATU GADANG', 'INDARUNG', 'PADANG BESI', 'KOTO LALANG', 'TARANTANG', 'BANDA BUEK']
for p in perbukitan_list:
    if p in rawan_set: rawan_set.remove(p)

# 2. Konstruksi Geometris Zona Spasial Presisi
# A. Pesisir Rawan Murni
gdf_coastal = gdf_utm[gdf_utm['NAMA_UPPER'].isin(rawan_set)].copy()

# B. Balai Gadang: Bagian Barat Rawan Tsunami, Bagian Tengah Buffer 2 km, Bagian Timur Aman
bg_geom = gdf_utm[gdf_utm['NAMA_UPPER'] == 'BALAI GADANG'].geometry.iloc[0]
bg_bounds = bg_geom.bounds
bg_red_box = box(bg_bounds[0], bg_bounds[1], bg_bounds[0] + 3500, bg_bounds[3])
bg_red_part = bg_geom.intersection(bg_red_box)

# Combine into RED Tsunami Rawan Zone
red_geoms = list(gdf_coastal.geometry) + [bg_red_part]
red_union = gpd.GeoSeries(red_geoms, crs="EPSG:32747").union_all()

# Buffer 2 km (2000m) dari Garis Batas Zona Rawan (Red Zone)
buffer_2km_raw = red_union.buffer(2000)
buffer_2km_ring = buffer_2km_raw.difference(red_union)

# Tentukan Mask Laut: Laut berada di sebelah barat garis pantai
padang_bounds = gdf_utm.total_bounds
# Ocean box di sebelah barat garis pantai
ocean_box = box(padang_bounds[0] - 20000, padang_bounds[1] - 10000, padang_bounds[0], padang_bounds[3] + 10000)

# Buffer 2 km Hanya Daratan (Melingkupi dari Utara, Timur, hingga Selatan Padang - Non Laut)
buffer_2km_land_geom = buffer_2km_ring.difference(ocean_box)

# Full Land Union (Seluruh Daratan Kota Padang)
land_union = gdf_utm.geometry.union_all()

# Zona Aman (Green) = Daratan Kota Padang di luar Red Zone & Yellow Buffer
safe_land_geom = land_union.difference(red_union).difference(buffer_2km_land_geom)

# Konversi ke GeoDataFrame EPSG:4326 (WGS84)
gdf_red = gpd.GeoDataFrame(geometry=[red_union], crs="EPSG:32747").to_crs("EPSG:4326")
gdf_yellow = gpd.GeoDataFrame(geometry=[buffer_2km_land_geom], crs="EPSG:32747").to_crs("EPSG:4326")
gdf_green = gpd.GeoDataFrame(geometry=[safe_land_geom], crs="EPSG:32747").to_crs("EPSG:4326")
gdf_kel_wgs = gdf_utm.to_crs("EPSG:4326")

# Memuat Gedung TES (Shelter Evakuasi)
file_shelter = "data_tes_padang_lengkap_berkoordinat.csv" if os.path.exists("data_tes_padang_lengkap_berkoordinat.csv") else "Koordinat Evakuasi TES - Sheet1.csv"
df_shelter = pd.read_csv(file_shelter)

def parse_coord(val):
    try: return float(str(val).strip().replace(',', '.'))
    except: return np.nan

lat_col = 'Latitude' if 'Latitude' in df_shelter.columns else 'Clean_Lat'
lon_col = 'Longitude' if 'Longitude' in df_shelter.columns else 'Clean_Lon'

df_shelter['lat_c'] = df_shelter[lat_col].apply(parse_coord)
df_shelter['lon_c'] = df_shelter[lon_col].apply(parse_coord)
df_shelter = df_shelter.dropna(subset=['lat_c', 'lon_c']).drop_duplicates(subset=['lat_c', 'lon_c']).copy()

# 3. MERENDER GAMBAR PNG HIGH-RESOLUTION (300 DPI)
print("[3/5] Merender Gambar PNG High-Resolution (300 DPI)...")

fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
fig.patch.set_facecolor('#0f172a')
ax.set_facecolor('#0f172a')

# Plot Zona Aman (Green)
gdf_green.plot(ax=ax, facecolor='#10b981', edgecolor='#047857', linewidth=1.0, alpha=0.5, label='Zona Aman Daratan / Perbukitan')

# Plot Buffer Zone 2 km (Yellow/Amber - Menyambung dari Utara ke Selatan)
gdf_yellow.plot(ax=ax, facecolor='#f59e0b', edgecolor='#d97706', linewidth=1.5, alpha=0.6, label='Buffer Zone 2 km (Sabuk Daratan Penyangga Menyambung)')

# Plot Inti Wilayah Rawan Tsunami (Red)
gdf_red.plot(ax=ax, facecolor='#ef4444', edgecolor='#b91c1c', linewidth=1.2, alpha=0.65, label='Inti Wilayah Rawan Tsunami (Pesisir & Barat Balai Gadang)')

# Plot Garis Batas Kelurahan
gdf_kel_wgs.boundary.plot(ax=ax, color='#ffffff', linewidth=0.4, linestyle=':', alpha=0.35)

# Plot Titik Gedung TES
ax.scatter(df_shelter['lon_c'], df_shelter['lat_c'], s=24, color='#38bdf8', edgecolor='#ffffff', linewidth=0.6, zorder=5, label=f'Gedung TES Evakuasi ({len(df_shelter)} Unit)')

# Bounds Limit Zoom
bounds = gdf_yellow.total_bounds
min_lon, min_lat, max_lon, max_lat = bounds
lon_margin = (max_lon - min_lon) * 0.08
lat_margin = (max_lat - min_lat) * 0.08
ax.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

plt.title("Peta Zona Rawan Tsunami Kota Padang, Buffer Zone 2 km & Zona Aman", fontsize=14, fontweight='bold', color='#f8fafc', pad=18)
ax.text(0.5, 0.975, "Sabuk Buffer 2 km Menyambung Utara (Koto Tangah) - Timur (Balai Gadang/Pauh) - Selatan (Bungus)", 
        transform=ax.transAxes, ha='center', fontsize=9.5, color='#94a3b8', style='italic')

legend_elements = [
    mpatches.Patch(facecolor='#ef4444', edgecolor='#b91c1c', linewidth=1.2, alpha=0.65, label=f'Zona Rawan Tsunami ({red_union.area/1e6:.1f} km²)'),
    mpatches.Patch(facecolor='#f59e0b', edgecolor='#d97706', linewidth=1.5, alpha=0.6, label=f'Buffer Zone 2 km Daratan ({buffer_2km_land_geom.area/1e6:.1f} km²)'),
    mpatches.Patch(facecolor='#10b981', edgecolor='#047857', linewidth=1.0, alpha=0.5, label=f'Zona Aman Perbukitan ({safe_land_geom.area/1e6:.1f} km²)'),
    Line2D([0], [0], marker='o', color='w', label=f'Gedung TES Evakuasi ({len(df_shelter)} Lokasi)', markerfacecolor='#38bdf8', markersize=6)
]

ax.legend(handles=legend_elements, loc='lower right', facecolor='#0f172a', edgecolor='#334155', 
          fontsize=8.5, labelcolor='#f8fafc', framealpha=0.92, borderpad=0.8)

ax.tick_params(colors='#94a3b8', labelsize=8)
ax.grid(True, color='#1e293b', linestyle=':', linewidth=0.5, alpha=0.7)
ax.set_xlabel("Bujur (Longitude)", color='#cbd5e1', fontsize=9, labelpad=8)
ax.set_ylabel("Lintang (Latitude)", color='#cbd5e1', fontsize=9, labelpad=8)

png_path_local = r"c:\gemastik\peta_zona_rawan_tsunami_padang.png"
png_path_artifact = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\5660f7ac-beb1-4b49-93ef-6ffb6ce437c8\peta_zona_rawan_tsunami_padang.png"
os.makedirs(os.path.dirname(png_path_artifact), exist_ok=True)

plt.savefig(png_path_local, bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=300)
plt.savefig(png_path_artifact, bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=300)
plt.close()

print(f"[SUKSES] Gambar PNG disimpan di '{png_path_local}' dan '{png_path_artifact}'")

# 4. MEMBUAT PETA INTERAKTIF FOLIUM (HTML)
print("[4/5] Membangun Peta Web Interaktif (HTML)...")
center_lat = (min_lat + max_lat) / 2
center_lon = (min_lon + max_lon) / 2

peta_web = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles='CartoDB positron'
)

# Layer 1: Zona Aman (Green)
folium.GeoJson(
    gdf_green,
    name="🟢 Zona Aman Daratan / Perbukitan",
    style_function=lambda x: {
        'fillColor': '#10b981',
        'color': '#047857',
        'weight': 1.5,
        'fillOpacity': 0.40
    },
    tooltip=folium.Tooltip("<b>🟢 Zona Aman Perbukitan Timur</b><br/>Area bebas tsunami (> 2 km di luar zona rawan).")
).add_to(peta_web)

# Layer 2: Buffer Zone 2 km (Yellow/Amber - Menyambung dari Utara ke Selatan)
folium.GeoJson(
    gdf_yellow,
    name="🟡 Buffer Zone 2 km (Sabuk Daratan Penyangga Menyambung - Non Laut)",
    style_function=lambda x: {
        'fillColor': '#f59e0b',
        'color': '#d97706',
        'weight': 2.0,
        'fillOpacity': 0.50
    },
    tooltip=folium.Tooltip("<b>🟡 Sabuk Buffer Zone 2 km (Menyambung Utara-Selatan)</b><br/>Buffer 2 km melingkupi utara (Koto Tangah), timur (Balai Gadang/Pauh/Lubuk Begalung), hingga selatan (Bungus Teluk Kabung) di luar wilayah rawan tsunami (Laut dikeluarkannya).")
).add_to(peta_web)

# Layer 3: Zona Rawan Tsunami Inti (Red)
folium.GeoJson(
    gdf_red,
    name="🔴 Zona Rawan Tsunami (Pesisir & Barat Balai Gadang)",
    style_function=lambda x: {
        'fillColor': '#ef4444',
        'color': '#b91c1c',
        'weight': 1.8,
        'fillOpacity': 0.55
    },
    tooltip=folium.Tooltip("<b>🔴 Zona Rawan Tsunami</b><br/>Wilayah pesisir rawan tsunami serta bagian barat Balai Gadang.")
).add_to(peta_web)

# Layer 4: Batas Kelurahan
folium.GeoJson(
    gdf_kel_wgs,
    name="📍 Batas Administrasi Kelurahan",
    style_function=lambda x: {
        'fillColor': 'transparent',
        'color': '#475569',
        'weight': 0.8,
        'dashArray': '3, 3'
    },
    tooltip=folium.GeoJsonTooltip(fields=['NAMA_UPPER'], aliases=['Kelurahan:'])
).add_to(peta_web)

# Layer 5: Gedung TES
for idx, r in df_shelter.iterrows():
    nama = r.get('Nama_Bersih', r.get('Lokasi_TES', 'Gedung TES'))
    folium.CircleMarker(
        location=[r['lat_c'], r['lon_c']],
        radius=5,
        color='#0284c7',
        fill=True,
        fill_color='#38bdf8',
        fill_opacity=0.9,
        popup=f"<b>{nama}</b>",
        tooltip=f"🏢 TES: {nama}"
    ).add_to(peta_web)

# Floating Banner Card Header
banner_html = f"""
<div style="
    position: fixed; 
    top: 15px; left: 60px; width: 460px;
    background: rgba(15, 23, 42, 0.94);
    backdrop-filter: blur(10px);
    color: white;
    padding: 14px 18px;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    font-family: 'Segoe UI', Arial, sans-serif;
    z-index: 9999;
    border: 1px solid rgba(255,255,255,0.15);
">
    <div style="font-size: 13px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.5px;">
        PETA ZONA RAWAN, BUFFER 2 KM CONTINUOUS & ZONA AMAN
    </div>
    <div style="font-size: 12px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
        SABUK BUFFER 2 KM MENYAMBUNG UTARA HINGGA SELATAN (NON LAUT)
    </div>
    <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px; line-height: 1.6;">
        <div>🔴 <strong>Zona Rawan Tsunami:</strong> {red_union.area/1e6:.1f} km² (Pesisir & Barat Balai Gadang)</div>
        <div>🟡 <strong>Buffer Zone 2 km:</strong> {buffer_2km_land_geom.area/1e6:.1f} km² (Menyambung 2 km Utara-Timur-Selatan)</div>
        <div>🟢 <strong>Zona Aman Perbukitan:</strong> {safe_land_geom.area/1e6:.1f} km² (Timur Balai Gadang & Perbukitan)</div>
        <div>🏢 <strong>Fasilitas TES:</strong> {len(df_shelter)} Gedung Shelter Evakuasi</div>
    </div>
</div>
"""
peta_web.get_root().html.add_child(folium.Element(banner_html))
folium.LayerControl().add_to(peta_web)

html_filename = "peta_zona_rawan_tsunami_padang.html"
peta_web.save(html_filename)
print(f"[SUKSES] Peta Interaktif HTML disimpan: '{html_filename}'")
