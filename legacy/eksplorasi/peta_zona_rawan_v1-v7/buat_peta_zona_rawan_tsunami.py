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
from pyproj import Transformer

print("=" * 80)
print("Peta Area Zona Rawan Tsunami dan Buffer Zone 2 Km (Daratan)")
print("=" * 80)

file_geojson = "batas_kelurahan_kota_padang.geojson"
print(f"[1/5] Membaca GeoJSON: {file_geojson}...")
gdf_kel = gpd.read_file(file_geojson)


gdf_utm = gdf_kel.to_crs("EPSG:32747")


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
for c in coastal_additions:
    rawan_set.add(c)

kolom_nama = gdf_utm.select_dtypes(include=['object', 'string']).columns[0]
gdf_utm['NAMA_UPPER'] = gdf_utm[kolom_nama].astype(str).str.upper().str.strip()
gdf_utm['IS_INTI_RAWAN'] = gdf_utm['NAMA_UPPER'].isin(rawan_set)

gdf_inti_utm = gdf_utm[gdf_utm['IS_INTI_RAWAN']].copy()
gdf_non_inti_utm = gdf_utm[~gdf_utm['IS_INTI_RAWAN']].copy()

print(f"      Inti Kelurahan Rawan Tsunami: {len(gdf_inti_utm)} Kelurahan")
print(f"      Kelurahan Non-Inti / Daratan Lain: {len(gdf_non_inti_utm)} Kelurahan")

print("[2/5] Menghitung Buffer Zone 2 km Daratan (Laut Dikeluarkannya)...")
inti_union = gdf_inti_utm.geometry.union_all()
land_union = gdf_utm.geometry.union_all()


buffer_2km_raw = inti_union.buffer(2000)

buffer_2km_land_geom = buffer_2km_raw.intersection(land_union).difference(inti_union)

luas_inti_km2 = inti_union.area / 1e6
luas_buffer_km2 = buffer_2km_land_geom.area / 1e6

print(f"      Luas Inti Wilayah Rawan Tsunami : {luas_inti_km2:.2f} km²")
print(f"      Luas Buffer Zone 2 km (Daratan) : {luas_buffer_km2:.2f} km²")

gdf_inti_wgs = gdf_inti_utm.to_crs("EPSG:4326")
gdf_non_inti_wgs = gdf_non_inti_utm.to_crs("EPSG:4326")

gdf_buffer_2km = gpd.GeoDataFrame(geometry=[buffer_2km_land_geom], crs="EPSG:32747").to_crs("EPSG:4326")

file_shelter = "data_tes_padang_lengkap_berkoordinat.csv"
df_shelter = pd.read_csv(file_shelter) if os.path.exists(file_shelter) else pd.read_csv("Koordinat Evakuasi TES - Sheet1.csv")

def parse_coord(val):
    try: return float(str(val).strip().replace(',', '.'))
    except: return np.nan

lat_col = 'Latitude' if 'Latitude' in df_shelter.columns else 'Clean_Lat'
lon_col = 'Longitude' if 'Longitude' in df_shelter.columns else 'Clean_Lon'

df_shelter['lat_c'] = df_shelter[lat_col].apply(parse_coord)
df_shelter['lon_c'] = df_shelter[lon_col].apply(parse_coord)
df_shelter = df_shelter.dropna(subset=['lat_c', 'lon_c']).drop_duplicates(subset=['lat_c', 'lon_c']).copy()

print("[3/5] Merender Gambar PNG High-Resolution (300 DPI)...")

fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
fig.patch.set_facecolor('#0f172a')
ax.set_facecolor('#0f172a')

gdf_non_inti_wgs.plot(ax=ax, facecolor='#1e293b', edgecolor='#334155', linewidth=0.8, alpha=0.7, label='Zona Aman Daratan / Perbukitan')


gdf_buffer_2km.plot(ax=ax, facecolor='#f59e0b', edgecolor='#d97706', linewidth=1.5, alpha=0.55, label='Buffer Zone 2 km (Daratan Penyangga)')


gdf_inti_wgs.plot(ax=ax, facecolor='#ef4444', edgecolor='#b91c1c', linewidth=1.2, alpha=0.65, label='Inti Wilayah Rawan Tsunami (Pesisir)')

ax.scatter(df_shelter['lon_c'], df_shelter['lat_c'], s=24, color='#38bdf8', edgecolor='#ffffff', linewidth=0.6, zorder=5, label=f'Gedung TES Evakuasi ({len(df_shelter)} Unit)')

bounds = gdf_inti_wgs.total_bounds
min_lon, min_lat, max_lon, max_lat = bounds
lon_margin = (max_lon - min_lon) * 0.15
lat_margin = (max_lat - min_lat) * 0.15
ax.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

plt.title("Peta Zona Rawan Tsunami Kota Padang & Buffer Zone 2 km (Daratan)", fontsize=14, fontweight='bold', color='#f8fafc', pad=18)
ax.text(0.5, 0.975, "Inti Wilayah Rawan Tsunami Pesisir beserta Penyangga Daratan 2 km (Laut Dikeluarkannya)", 
        transform=ax.transAxes, ha='center', fontsize=10.5, color='#94a3b8', style='italic')

legend_elements = [
    mpatches.Patch(facecolor='#ef4444', edgecolor='#b91c1c', linewidth=1.2, alpha=0.65, label=f'Inti Wilayah Rawan Tsunami ({luas_inti_km2:.1f} km²)'),
    mpatches.Patch(facecolor='#f59e0b', edgecolor='#d97706', linewidth=1.5, alpha=0.55, label=f'Buffer Zone 2 km Daratan ({luas_buffer_km2:.1f} km²)'),
    mpatches.Patch(facecolor='#1e293b', edgecolor='#334155', linewidth=0.8, alpha=0.7, label='Zona Aman Daratan / Perbukitan'),
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

print(f"[SUKSES] Gambar PNG disimpan: '{png_path_local}'")

print("[4/5] Membangun Peta Web Interaktif (HTML)...")
center_lat = (min_lat + max_lat) / 2
center_lon = (min_lon + max_lon) / 2

peta_web = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles='CartoDB positron'
)

folium.GeoJson(
    gdf_buffer_2km,
    name="🟡 Buffer Zone 2 km (Daratan Penyangga - Non Laut)",
    style_function=lambda x: {
        'fillColor': '#f59e0b',
        'color': '#d97706',
        'weight': 2.0,
        'fillOpacity': 0.45
    },
    tooltip=folium.Tooltip("<b>Buffer Zone 2 km (Daratan Penyangga)</b><br/>Area penyangga daratan di luar wilayah inti rawan tsunami (Laut dikeluarkannya).")
).add_to(peta_web)

folium.GeoJson(
    gdf_inti_wgs,
    name="🔴 Inti Wilayah Rawan Tsunami (Pesisir Padang)",
    style_function=lambda x: {
        'fillColor': '#ef4444',
        'color': '#b91c1c',
        'weight': 1.5,
        'fillOpacity': 0.55
    },
    tooltip=folium.GeoJsonTooltip(fields=['NAMA_UPPER'], aliases=['Kelurahan Rawan:'])
).add_to(peta_web)

folium.GeoJson(
    gdf_non_inti_wgs,
    name="🟢 Zona Aman Daratan / Perbukitan",
    style_function=lambda x: {
        'fillColor': '#10b981',
        'color': '#047857',
        'weight': 1.0,
        'fillOpacity': 0.25
    },
    tooltip=folium.GeoJsonTooltip(fields=['NAMA_UPPER'], aliases=['Kelurahan Zona Aman:'])
).add_to(peta_web)

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

banner_html = f"""
<div style="
    position: fixed; 
    top: 15px; left: 60px; width: 440px;
    background: rgba(15, 23, 42, 0.92);
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
        PETA ZONA RAWAN TSUNAMI & BUFFER 2 KM
    </div>
    <div style="font-size: 12px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
        KOTA PADANG (DENGAN ISOLASI WILAYAH LAUT)
    </div>
    <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px; line-height: 1.6;">
        <div>🔴 <strong>Inti Rawan Tsunami:</strong> {luas_inti_km2:.1f} km² ({len(gdf_inti_wgs)} Kelurahan Pesisir)</div>
        <div>🟡 <strong>Buffer Zone 2 km:</strong> {luas_buffer_km2:.1f} km² (Daratan Penyangga - Non Laut)</div>
        <div>🏢 <strong>Fasilitas TES:</strong> {len(df_shelter)} Gedung Shelter Evakuasi</div>
    </div>
</div>
"""
peta_web.get_root().html.add_child(folium.Element(banner_html))
folium.LayerControl().add_to(peta_web)

html_filename = "peta_zona_rawan_tsunami_padang.html"
peta_web.save(html_filename)
print(f"[SUKSES] Peta Interaktif HTML disimpan: '{html_filename}'")
