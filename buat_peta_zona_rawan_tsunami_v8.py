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
import shutil

print("=" * 80)
print("GENERATOR PETA ZONA RAWAN TSUNAMI KOTA PADANG & BUFFER 2 KM (DENGAN PESSEL & SOLOK)")
print("====================================================================================")

# 1. Memuat GeoJSON Administrasi Resmi (Kota Padang, Pesisir Selatan, Solok)
print("[1/5] Membaca GeoJSON Resmi Kota Padang, Pesisir Selatan & Solok...")
file_padang = "batas_kelurahan_kota_padang.geojson"
file_pessel = "wilayah_pessel.geojson"
file_solok = "wilayah_solok.geojson"

gdf_padang = gpd.read_file(file_padang).to_crs("EPSG:32747")
gdf_pessel = gpd.read_file(file_pessel).to_crs("EPSG:32747")
gdf_solok = gpd.read_file(file_solok).to_crs("EPSG:32747")

# Filter poligon daratan utama (mainland) dari ketiga kabupaten/kota (membuang pulau lepas pantai di laut)
def get_mainland_union(gdf):
    gdf_exp = gdf.explode(index_parts=False).reset_index(drop=True)
    mainland_list = []
    for idx, r in gdf_exp.iterrows():
        c = r.geometry.centroid
        if not (c.x < 647000 or (c.x < 651000 and c.y < 9890000)):
            mainland_list.append(r.geometry)
    return gpd.GeoSeries(mainland_list, crs="EPSG:32747").union_all()

land_padang = get_mainland_union(gdf_padang)
land_pessel = get_mainland_union(gdf_pessel)
land_solok = get_mainland_union(gdf_solok)

# Combined Landmass Union (Daratan Riil Padang + Pessel + Solok)
full_land_all = land_padang.union(land_pessel).union(land_solok)

# 2. Konstruksi Geometris Zona Rawan (Red) & Buffer 2 km (Yellow)
kolom_nama = gdf_padang.select_dtypes(include=['object', 'string']).columns[0]
gdf_padang['NAMA_UPPER'] = gdf_padang[kolom_nama].astype(str).str.upper().str.strip()

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

gdf_coastal = gdf_padang[gdf_padang['NAMA_UPPER'].isin(rawan_set)].copy()

# Balai Gadang split (Barat Red, Tengah Yellow Buffer, Timur Green)
bg_geom = gdf_padang[gdf_padang['NAMA_UPPER'] == 'BALAI GADANG'].geometry.iloc[0]
bg_bounds = bg_geom.bounds
bg_red_box = box(bg_bounds[0], bg_bounds[1], bg_bounds[0] + 3500, bg_bounds[3])
bg_red_part = bg_geom.intersection(bg_red_box)

red_geoms = list(gdf_coastal.geometry) + [bg_red_part]
red_union = gpd.GeoSeries(red_geoms, crs="EPSG:32747").union_all()

# Buffer 2 km (2000m) dari Garis Zona Merah
buffer_2km_raw = red_union.buffer(2000)

# Buffer 2 km Presisi Daratan Riil Padang + Pessel + Solok (Laut 100% Bebas Buffer!)
buffer_2km_land_real = buffer_2km_raw.intersection(full_land_all).difference(red_union)

# Zona Aman (Green) di Dalam Kota Padang
safe_land_padang = land_padang.difference(red_union).difference(buffer_2km_land_real)

# Cleaning geometries helper for Shapefile compatibility
def clean_polygon_geom(geom):
    if geom.is_empty:
        return Polygon()
    if geom.geom_type in ['Polygon', 'MultiPolygon']:
        return geom
    if hasattr(geom, 'geoms'):
        polys = [g for g in geom.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]
        if len(polys) == 0:
            return Polygon()
        elif len(polys) == 1:
            return polys[0]
        else:
            return MultiPolygon(polys)
    return Polygon()

red_poly = clean_polygon_geom(red_union)
yellow_poly = clean_polygon_geom(buffer_2km_land_real)
green_poly = clean_polygon_geom(safe_land_padang)

# Konversi ke GeoDataFrame EPSG:4326 (WGS84)
gdf_red = gpd.GeoDataFrame(geometry=[red_poly], crs="EPSG:32747").to_crs("EPSG:4326")
gdf_yellow = gpd.GeoDataFrame(geometry=[yellow_poly], crs="EPSG:32747").to_crs("EPSG:4326")
gdf_green = gpd.GeoDataFrame(geometry=[green_poly], crs="EPSG:32747").to_crs("EPSG:4326")
gdf_padang_wgs = gdf_padang.to_crs("EPSG:4326")

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
df_shelter = df_shelter[df_shelter['lon_c'] >= 100.31].copy()

# 3. MERENDER GAMBAR PNG HIGH-RESOLUTION (300 DPI)
print("[3/5] Merender Gambar PNG High-Resolution (300 DPI)...")

fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
fig.patch.set_facecolor('#0f172a')
ax.set_facecolor('#0f172a')

# Plot Zona Aman (Green)
gdf_green.plot(ax=ax, facecolor='#10b981', edgecolor='#047857', linewidth=1.0, alpha=0.5, label='Zona Aman Daratan / Perbukitan')

# Plot Buffer Zone 2 km (Yellow/Amber - Presisi Daratan 3 Wilayah)
gdf_yellow.plot(ax=ax, facecolor='#f59e0b', edgecolor='#d97706', linewidth=1.5, alpha=0.6, label='Buffer Zone 2 km (Daratan Penyangga - Padang, Pessel & Solok)')

# Plot Inti Wilayah Rawan Tsunami (Red)
gdf_red.plot(ax=ax, facecolor='#ef4444', edgecolor='#b91c1c', linewidth=1.2, alpha=0.65, label='Inti Wilayah Rawan Tsunami (Pesisir Padang & Barat Balai Gadang)')

# Plot Garis Batas Kelurahan
gdf_padang_wgs.boundary.plot(ax=ax, color='#ffffff', linewidth=0.4, linestyle=':', alpha=0.35)

# Plot Titik Gedung TES
ax.scatter(df_shelter['lon_c'], df_shelter['lat_c'], s=24, color='#38bdf8', edgecolor='#ffffff', linewidth=0.6, zorder=5, label=f'Gedung TES Evakuasi ({len(df_shelter)} Unit)')

# Bounds Limit Zoom
bounds = gdf_padang_wgs.total_bounds
min_lon, min_lat, max_lon, max_lat = bounds
lon_margin = (max_lon - min_lon) * 0.08
lat_margin = (max_lat - min_lat) * 0.08
ax.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

plt.title("Peta Zona Rawan Tsunami Kota Padang, Buffer Zone 2 km & Zona Aman", fontsize=14, fontweight='bold', color='#f8fafc', pad=18)
ax.text(0.5, 0.975, "Buffer 2 km Berbasis Geometri Presisi Daratan Kota Padang, Pesisir Selatan & Solok", 
        transform=ax.transAxes, ha='center', fontsize=9.2, color='#94a3b8', style='italic')

legend_elements = [
    mpatches.Patch(facecolor='#ef4444', edgecolor='#b91c1c', linewidth=1.2, alpha=0.65, label=f'Zona Rawan Tsunami ({red_union.area/1e6:.1f} km²)'),
    mpatches.Patch(facecolor='#f59e0b', edgecolor='#d97706', linewidth=1.5, alpha=0.6, label=f'Buffer Zone 2 km Daratan ({buffer_2km_land_real.area/1e6:.1f} km²)'),
    mpatches.Patch(facecolor='#10b981', edgecolor='#047857', linewidth=1.0, alpha=0.5, label=f'Zona Aman Perbukitan ({safe_land_padang.area/1e6:.1f} km²)'),
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

# Layer 2: Buffer Zone 2 km (Yellow/Amber - Presisi Daratan 3 Wilayah)
folium.GeoJson(
    gdf_yellow,
    name="🟡 Buffer Zone 2 km (Daratan Penyangga 3 Wilayah - Laut Bebas)",
    style_function=lambda x: {
        'fillColor': '#f59e0b',
        'color': '#d97706',
        'weight': 2.0,
        'fillOpacity': 0.55
    },
    tooltip=folium.Tooltip("<b>🟡 Buffer Zone 2 km (Daratan Penyangga Presisi)</b><br/>Buffer 2 km meluas ke utara, timur (Solok) & selatan (Pesisir Selatan) mengikuti garis pantai riil (Laut 100% bebas buffer).")
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

# Layer 4: Batas Kelurahan Kota Padang
folium.GeoJson(
    gdf_padang_wgs,
    name="📍 Batas Administrasi Kelurahan Padang",
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

# Floating Banner & Legend Card Header (Diperbesar & Diperjelas)
banner_html = f"""
<style>
    .leaflet-control-layers {{
        background: rgba(15, 23, 42, 0.95) !important;
        color: #f8fafc !important;
        border: 1.5px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        font-size: 13px !important;
        font-family: 'Segoe UI', Arial, sans-serif !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
    }}
    .leaflet-control-layers-toggle {{
        width: 44px !important;
        height: 44px !important;
    }}
    .leaflet-control-layers-overlays label {{
        margin-bottom: 6px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
    }}
</style>

<div style="
    position: fixed; 
    top: 20px; left: 60px; width: 520px;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(12px);
    color: white;
    padding: 20px 24px;
    border-radius: 16px;
    box-shadow: 0 14px 35px rgba(0,0,0,0.55);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    z-index: 9999;
    border: 1.5px solid rgba(255, 255, 255, 0.2);
">
    <!-- Header Title -->
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
        <span style="font-size: 20px;">🗺️</span>
        <div style="font-size: 15px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.8px;">
            LEGENDA ZONA RAWAN TSUNAMI & BUFFER 2 KM
        </div>
    </div>
    <div style="font-size: 13px; font-weight: 700; color: #cbd5e1; margin-left: 30px; margin-bottom: 14px;">
        Kota Padang, Pesisir Selatan & Solok (Daratan Riil)
    </div>

    <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.15); margin: 10px 0 14px 0;">

    <!-- Legend Items -->
    <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px; line-height: 1.5;">
        <!-- Item 1: Zona Rawan -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); padding: 8px 12px; border-radius: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="width: 16px; height: 16px; background-color: #ef4444; border: 1px solid #b91c1c; border-radius: 4px; display: inline-block; flex-shrink: 0;"></span>
                <span style="color: #f8fafc; font-weight: 700;">🔴 Inti Rawan Tsunami</span>
            </div>
            <span style="color: #fca5a5; font-weight: 800; font-size: 13.5px;">{red_union.area/1e6:.1f} km²</span>
        </div>

        <!-- Item 2: Buffer Zone 2 km -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); padding: 8px 12px; border-radius: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="width: 16px; height: 16px; background-color: #f59e0b; border: 1px solid #d97706; border-radius: 4px; display: inline-block; flex-shrink: 0;"></span>
                <span style="color: #f8fafc; font-weight: 700;">🟡 Buffer Zone 2 km (Daratan Penyangga)</span>
            </div>
            <span style="color: #fcd34d; font-weight: 800; font-size: 13.5px;">{buffer_2km_land_real.area/1e6:.1f} km²</span>
        </div>

        <!-- Item 3: Zona Aman -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); padding: 8px 12px; border-radius: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="width: 16px; height: 16px; background-color: #10b981; border: 1px solid #047857; border-radius: 4px; display: inline-block; flex-shrink: 0;"></span>
                <span style="color: #f8fafc; font-weight: 700;">🟢 Zona Aman (Perbukitan Timur)</span>
            </div>
            <span style="color: #6ee7b7; font-weight: 800; font-size: 13.5px;">{safe_land_padang.area/1e6:.1f} km²</span>
        </div>

        <!-- Item 4: TES -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); padding: 8px 12px; border-radius: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="width: 14px; height: 14px; background-color: #38bdf8; border: 2px solid #ffffff; border-radius: 50%; display: inline-block; flex-shrink: 0;"></span>
                <span style="color: #f8fafc; font-weight: 700;">🏢 Gedung Evakuasi TES</span>
            </div>
            <span style="color: #7dd3fc; font-weight: 800; font-size: 13.5px;">{len(df_shelter)} Lokasi</span>
        </div>
    </div>
</div>
"""
peta_web.get_root().html.add_child(folium.Element(banner_html))
folium.LayerControl().add_to(peta_web)

html_filename = "peta_zona_rawan_tsunami_padang.html"
peta_web.save(html_filename)
print(f"[SUKSES] Peta Interaktif HTML disimpan: '{html_filename}'")

# 5. EKSPOR SHAPEFILE (.SHP) UNTUK QGIS & GIS SOFTWARE
print("[5/5] Mengekspor Hasil Spasial ke Format Shapefile (.shp) untuk QGIS...")
dir_shp = "shp_output"
os.makedirs(dir_shp, exist_ok=True)

df_attr_zones = pd.DataFrame([
    {
        'ZONE_ID': 1,
        'KODE_ZONA': 'RAWAN',
        'ZONA_NAME': 'Zona Rawan Tsunami',
        'LUAS_KM2': round(red_union.area / 1e6, 2),
        'COLOR_HEX': '#ef4444'
    },
    {
        'ZONE_ID': 2,
        'KODE_ZONA': 'BUFFER_2KM',
        'ZONA_NAME': 'Buffer Zone 2 km (Daratan Penyangga 3 Wilayah)',
        'LUAS_KM2': round(buffer_2km_land_real.area / 1e6, 2),
        'COLOR_HEX': '#f59e0b'
    },
    {
        'ZONE_ID': 3,
        'KODE_ZONA': 'AMAN',
        'ZONA_NAME': 'Zona Aman Perbukitan',
        'LUAS_KM2': round(safe_land_padang.area / 1e6, 2),
        'COLOR_HEX': '#10b981'
    }
])

gdf_all_zones_wgs = gpd.GeoDataFrame(df_attr_zones, geometry=[red_poly, yellow_poly, green_poly], crs="EPSG:32747").to_crs("EPSG:4326")
shp_zones_path = os.path.join(dir_shp, "zona_rawan_tsunami_padang.shp")

try:
    gdf_all_zones_wgs.to_file(shp_zones_path, driver="ESRI Shapefile")
except Exception:
    shp_zones_path = os.path.join(dir_shp, "zona_rawan_tsunami_padang_v8.shp")
    gdf_all_zones_wgs.to_file(shp_zones_path, driver="ESRI Shapefile")

# Shapefile Gedung TES
nama_col = 'Nama_Bersih' if 'Nama_Bersih' in df_shelter.columns else 'Lokasi_TES'
cap_col = 'Scaled_Cap' if 'Scaled_Cap' in df_shelter.columns else 'Kapasitas'

df_tes_export = pd.DataFrame({
    'NAMA_TES': df_shelter[nama_col].astype(str),
    'KAPASITAS': df_shelter[cap_col].fillna(0).astype(int) if cap_col in df_shelter.columns else 0,
    'LATITUDE': df_shelter['lat_c'],
    'LONGITUDE': df_shelter['lon_c']
})

gdf_tes = gpd.GeoDataFrame(
    df_tes_export,
    geometry=gpd.points_from_xy(df_shelter['lon_c'], df_shelter['lat_c']),
    crs="EPSG:4326"
)
shp_tes_path = os.path.join(dir_shp, "tes_shelter_padang.shp")

try:
    gdf_tes.to_file(shp_tes_path, driver="ESRI Shapefile")
except Exception:
    shp_tes_path = os.path.join(dir_shp, "tes_shelter_padang_v8.shp")
    gdf_tes.to_file(shp_tes_path, driver="ESRI Shapefile")

zip_file = shutil.make_archive("shp_output_zona_tsunami_padang", 'zip', dir_shp)

import webbrowser

print(f"[SUKSES] Shapefile (.shp) berhasil dibuat di folder '{dir_shp}/':")
print(f"  1. Poligon Zonasi  : '{shp_zones_path}' (Siap buka di QGIS)")
print(f"  2. Titik Gedung TES: '{shp_tes_path}' (Siap buka di QGIS)")
print(f"  3. Archive ZIP     : '{zip_file}'")

try:
    html_abs_path = os.path.abspath(html_filename)
    webbrowser.open(f"file:///{html_abs_path.replace('\\', '/')}")
    print(f"[BROWSER] Membuka '{html_filename}' secara otomatis di web browser...")
except Exception as e:
    print(f"[NOTE] Anda dapat membuka '{html_filename}' secara manual di browser.")
