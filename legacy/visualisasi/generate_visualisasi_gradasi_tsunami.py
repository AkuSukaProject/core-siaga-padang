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
from folium import plugins
from shapely.geometry import box, Polygon, MultiPolygon

print("=" * 85)
print("GENERATOR VISUALISASI GRADASI SPASIAL ZONA RAWAN TSUNAMI KOTA PADANG")
print("====================================================================================")

# -----------------------------------------------------------------------------
# 1. MEMUAT GEOJSON ADMINISTRASI RESMI KOTA PADANG
# -----------------------------------------------------------------------------
print("[1/5] Membaca GeoJSON Administrasi Kelurahan Kota Padang (EPSG:32747)...")
file_padang = "batas_kelurahan_kota_padang.geojson"

gdf_padang = gpd.read_file(file_padang).to_crs("EPSG:32747")
kolom_nama = 'NAMOBJ' if 'NAMOBJ' in gdf_padang.columns else gdf_padang.select_dtypes(include=['object', 'string']).columns[0]
gdf_padang['NAMA_UPPER'] = gdf_padang[kolom_nama].astype(str).str.upper().str.strip()

# Extract mainland geometry Kota Padang (membuang pulau lepas pantai di laut)
def get_mainland(gdf):
    gdf_exp = gdf.explode(index_parts=False).reset_index(drop=True)
    mainland_list = []
    for idx, r in gdf_exp.iterrows():
        c = r.geometry.centroid
        if not (c.x < 635000 or (c.x < 642000 and c.y < 9880000)):
            mainland_list.append(r.geometry)
    if len(mainland_list) == 0: return Polygon()
    return gpd.GeoSeries(mainland_list, crs="EPSG:32747").union_all()

land_padang = get_mainland(gdf_padang)

# Smooth shoreline boundary slightly (+30m then -30m) to seal micro-gaps along beach line
target_land = land_padang.buffer(30).buffer(-30)

# Helper geometry cleaner
def clean_poly(geom):
    if geom.is_empty: return Polygon()
    if geom.geom_type in ['Polygon', 'MultiPolygon']: return geom
    if hasattr(geom, 'geoms'):
        polys = [g for g in geom.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]
        if len(polys) == 0: return Polygon()
        elif len(polys) == 1: return polys[0]
        else: return MultiPolygon(polys)
    return Polygon()

# -----------------------------------------------------------------------------
# 2. DEFINISI SAMUDRA & GARIS PANTAI KOTA PADANG
# -----------------------------------------------------------------------------
print("[2/5] Mengonstruksi Garis Pantai Riil Kota Padang Samudra Hindia...")

# Ocean polygon covering western sea of Padang
ocean_box = box(500000, 9850000, 655000, 9950000)
ocean_area = ocean_box.difference(target_land)

# -----------------------------------------------------------------------------
# 3. KALKULASI BAND GRADASI KOTA PADANG (0m SAMPAI >3000m)
# -----------------------------------------------------------------------------
print("[3/5] Mengalkulasi 6 Band Gradasi Pantai ke Perbukitan Khusus Kota Padang...")

bands_config = [
    {
        "name": "Zona Inti Sangat Rawan",
        "desc": "Garis Pantai Utama (0 - 500m)",
        "min_d": 0, "max_d": 500,
        "color": "#dc2626", # Merah Pekat
        "risk": "Sangat Tinggi (Limpasan Gelombang Utama Tsunami)",
        "action": "Evakuasi Seketika (< 15 Menit) ke TES / Dataran Tinggi"
    },
    {
        "name": "Zona Rawan Utama",
        "desc": "Area Pesisir Dekat (500m - 1.000m)",
        "min_d": 500, "max_d": 1000,
        "color": "#ea580c", # Oranye Merah
        "risk": "Tinggi (Risiko Genangan Tsunami Tinggi)",
        "action": "Evakuasi Cepat Melalui Jalur Evakuasi Utama"
    },
    {
        "name": "Zona Rawan Sedang / Transisi",
        "desc": "Daratan Penyangga I (1.000m - 1.500m)",
        "min_d": 1000, "max_d": 1500,
        "color": "#f59e0b", # Oranye Kuning
        "risk": "Sedang (Limpasan Genangan & Kemacetan Evakuasi)",
        "action": "Siaga Evakuasi & Jauhi Aliran Sungai"
    },
    {
        "name": "Zona Waspada",
        "desc": "Daratan Penyangga II (1.500m - 2.000m)",
        "min_d": 1500, "max_d": 2000,
        "color": "#eab308", # Kuning Waspada
        "risk": "Waspada (Batas Jangkauan Gelombang Ekstrem)",
        "action": "Pantau Arahan Resmi BPBD & Siapkan Tas Siaga"
    },
    {
        "name": "Zona Siaga Evakuasi",
        "desc": "Ambang Evakuasi Aman (2.000m - 3.000m)",
        "min_d": 2000, "max_d": 3000,
        "color": "#84cc16", # Hijau Limau
        "risk": "Rendah (Zona Penampungan Evakuasi Horisontal)",
        "action": "Titik Kumpul Evakuasi Horisontal Pertama"
    },
    {
        "name": "Zona Sangat Aman",
        "desc": "Perbukitan & Daratan Tinggi Timur (> 3.000m)",
        "min_d": 3000, "max_d": 99999,
        "color": "#10b981", # Hijau Zamrud
        "risk": "Sangat Rendah / Bebas Tsunami",
        "action": "Lokasi Ideal Perlindungan Akhir & Tempat Evakuasi Akhir (TEA)"
    }
]

# Generate exact geometry slices strictly clipped to Kota Padang target_land
b0 = clean_poly(ocean_area.buffer(500).intersection(target_land))
b1 = clean_poly(ocean_area.buffer(1000).intersection(target_land).difference(ocean_area.buffer(500)))
b2 = clean_poly(ocean_area.buffer(1500).intersection(target_land).difference(ocean_area.buffer(1000)))
b3 = clean_poly(ocean_area.buffer(2000).intersection(target_land).difference(ocean_area.buffer(1500)))
b4 = clean_poly(ocean_area.buffer(3000).intersection(target_land).difference(ocean_area.buffer(2000)))
b5 = clean_poly(target_land.difference(ocean_area.buffer(3000)))

geoms = [b0, b1, b2, b3, b4, b5]

gradient_gdfs = []
for idx, cfg in enumerate(bands_config):
    geom = geoms[idx]
    area_km2 = geom.area / 1e6
    gdf_band = gpd.GeoDataFrame({
        'name': [cfg['name']],
        'desc': [cfg['desc']],
        'color': [cfg['color']],
        'risk': [cfg['risk']],
        'action': [cfg['action']],
        'area_km2': [area_km2],
        'band_idx': [idx]
    }, geometry=[geom], crs="EPSG:32747").to_crs("EPSG:4326")
    gradient_gdfs.append(gdf_band)

# -----------------------------------------------------------------------------
# 4. MEMUAT DATA TES (TEMPAT EVAKUASI SEMENTARA) KOTA PADANG
# -----------------------------------------------------------------------------
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

gdf_padang_wgs = gdf_padang.to_crs("EPSG:4326")

# -----------------------------------------------------------------------------
# 5. GENERASI GAMBAR STATIS HIGH-RES (300 DPI) VIA MATPLOTLIB
# -----------------------------------------------------------------------------
print("[4/5] Merender Gambar Statis High-Resolution Gradasi Zona Kota Padang (300 DPI)...")

fig, ax = plt.subplots(figsize=(13, 15), dpi=300)
fig.patch.set_facecolor('#0f172a') # Dark slate background
ax.set_facecolor('#0f172a')

# Plot masing-masing band gradasi khusus Kota Padang
for gdf_b in gradient_gdfs:
    color = gdf_b['color'].iloc[0]
    gdf_b.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=0.2, alpha=0.7)

# Boundary Kelurahan Kota Padang
gdf_padang_wgs.boundary.plot(ax=ax, color='#ffffff', linewidth=0.5, linestyle=':', alpha=0.5)

# Shelter TES
ax.scatter(df_shelter['lon_c'], df_shelter['lat_c'], s=28, color='#38bdf8', edgecolor='#ffffff', linewidth=0.7, zorder=10)

# Bounds Limit Zoom khusus Kota Padang
bounds = gdf_padang_wgs.total_bounds
min_lon, min_lat, max_lon, max_lat = bounds
lon_margin = (max_lon - min_lon) * 0.05
lat_margin = (max_lat - min_lat) * 0.05
ax.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

# Custom Title & Subtitle
plt.title("VISUALISASI GRADASI SPASIAL ZONA RAWAN TSUNAMI KOTA PADANG", fontsize=14, fontweight='bold', color='#f8fafc', pad=22)
ax.text(0.5, 0.98, "Batas Wilayah Administrasi Resmi Kota Padang (0m Garis Pantai -> 3km+ Perbukitan Timur)", 
        transform=ax.transAxes, ha='center', fontsize=9.2, color='#cbd5e1', style='italic')

# Legend Handles
legend_elements = []
for idx, cfg in enumerate(bands_config):
    gdf_b = gradient_gdfs[idx]
    area = gdf_b['area_km2'].iloc[0]
    label_txt = f"{cfg['name']} ({cfg['desc']}) — {area:.1f} km²"
    legend_elements.append(mpatches.Patch(facecolor=cfg['color'], edgecolor=cfg['color'], linewidth=0.5, alpha=0.8, label=label_txt))

legend_elements.append(Line2D([0], [0], marker='o', color='w', label=f'Shelter Evakuasi TES ({len(df_shelter)} Unit)', markerfacecolor='#38bdf8', markersize=7))

ax.legend(handles=legend_elements, loc='lower right', facecolor='#1e293b', edgecolor='#334155', 
          fontsize=8.5, labelcolor='#f8fafc', framealpha=0.95, borderpad=1.0, title="Tingkat Kerentanan & Luas Area (Kota Padang)", title_fontsize=9)

ax.tick_params(colors='#94a3b8', labelsize=8)
ax.grid(True, color='#1e293b', linestyle=':', linewidth=0.5, alpha=0.7)
ax.set_xlabel("Bujur (Longitude)", color='#cbd5e1', fontsize=9, labelpad=8)
ax.set_ylabel("Lintang (Latitude)", color='#cbd5e1', fontsize=9, labelpad=8)

png_path_local = r"c:\gemastik\peta_gradasi_zona_tsunami_padang.png"
png_path_artifact = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\6e25ee83-e7a5-43ef-bb35-d49386fe793a\peta_gradasi_zona_tsunami_padang.png"
os.makedirs(os.path.dirname(png_path_artifact), exist_ok=True)

plt.savefig(png_path_local, bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=300)
plt.savefig(png_path_artifact, bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=300)
plt.close()

print(f"[SUKSES] Gambar PNG Gradasi Kota Padang disimpan di:\n  - {png_path_local}\n  - {png_path_artifact}")

# -----------------------------------------------------------------------------
# 6. MEMBUAT PETA INTERAKTIF WEB FOLIUM (HTML) KHUSUS KOTA PADANG
# -----------------------------------------------------------------------------
print("[5/5] Membangun Peta Interaktif HTML Folium Khusus Kota Padang...")

center_lat = (min_lat + max_lat) / 2
center_lon = (min_lon + max_lon) / 2

peta_web = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles='CartoDB dark_matter'
)

folium.TileLayer('CartoDB positron', name='🗺️ Terang (Positron)').add_to(peta_web)
folium.TileLayer('OpenStreetMap', name='🗺️ Standard OSM').add_to(peta_web)

# Add Gradient Layers from Safe to High-Risk (Reverse order for proper overlay rendering)
for idx in reversed(range(len(bands_config))):
    cfg = bands_config[idx]
    gdf_b = gradient_gdfs[idx]
    area = gdf_b['area_km2'].iloc[0]
    color = cfg['color']

    tooltip_html = f"""
    <div style="font-family: 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; color: #1e293b; padding: 4px;">
        <div style="background-color: {color}; color: white; padding: 4px 8px; font-weight: bold; border-radius: 4px; font-size: 14px;">
            {cfg['name']} (Kota Padang)
        </div>
        <table style="margin-top: 6px; width: 100%; border-collapse: collapse;">
            <tr><td><b>Jangkauan Jarak:</b></td> <td>{cfg['desc']}</td></tr>
            <tr><td><b>Tingkat Risiko:</b></td> <td>{cfg['risk']}</td></tr>
            <tr><td><b>Luas Area Padang:</b></td> <td>{area:.2f} km²</td></tr>
            <tr><td><b>Rekomendasi:</b></td> <td>{cfg['action']}</td></tr>
        </table>
    </div>
    """

    folium.GeoJson(
        gdf_b,
        name=f"<span style='color:{color}; font-weight:bold;'>█</span> {cfg['name']} ({cfg['desc']})",
        style_function=lambda x, col=color: {
            'fillColor': col,
            'color': col,
            'weight': 0.5,
            'fillOpacity': 0.60
        },
        tooltip=folium.Tooltip(tooltip_html, sticky=True)
    ).add_to(peta_web)

# Layer Batas Kelurahan Kota Padang
folium.GeoJson(
    gdf_padang_wgs,
    name="📍 Batas Kelurahan Kota Padang",
    style_function=lambda x: {
        'fillColor': 'transparent',
        'color': '#ffffff',
        'weight': 1.0,
        'dashArray': '4, 4'
    },
    tooltip=folium.GeoJsonTooltip(fields=['NAMA_UPPER'], aliases=['Kelurahan:'])
).add_to(peta_web)

# FeatureGroup Shelter Evakuasi TES
tes_group = folium.FeatureGroup(name=f"🏢 Shelter Evakuasi TES ({len(df_shelter)} Unit)")
for _, row in df_shelter.iterrows():
    nama_tes = row.get('Nama TES', row.get('NAMA_SHELTER', 'Shelter Evakuasi'))
    alamat = row.get('Alamat', row.get('ALAMAT', 'Kota Padang'))
    kapasitas = row.get('Kapasitas (Orang)', row.get('KAPASITAS', 'Tersedia'))
    
    popup_tes = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; width: 220px;">
        <b style="color: #0369a1; font-size: 13px;">🏢 {nama_tes}</b><br/>
        <hr style="margin: 4px 0; border: 0; border-top: 1px solid #cbd5e1;"/>
        <b>Alamat:</b> {alamat}<br/>
        <b>Kapasitas:</b> {kapasitas} orang<br/>
        <b>Koordinat:</b> {row['lat_c']:.5f}, {row['lon_c']:.5f}
    </div>
    """
    
    folium.CircleMarker(
        location=[row['lat_c'], row['lon_c']],
        radius=5,
        color='#ffffff',
        weight=1.2,
        fill=True,
        fill_color='#0284c7',
        fill_opacity=0.9,
        popup=folium.Popup(popup_tes, max_width=260),
        tooltip=f"<b>🏢 {nama_tes}</b>"
    ).add_to(tes_group)

tes_group.add_to(peta_web)

# Layer Control
folium.LayerControl(collapsed=False).add_to(peta_web)

# Custom Floating HTML/CSS Legend with Gradient Bar
legend_html = """
<div id="gradasi-legend" style="
    position: fixed; 
    bottom: 25px; 
    right: 25px; 
    z-index: 9999; 
    background: rgba(15, 23, 42, 0.90); 
    backdrop-filter: blur(8px);
    color: #f8fafc; 
    padding: 16px 20px; 
    border-radius: 12px; 
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 12px;
    max-width: 330px;
">
    <div style="font-weight: 700; font-size: 14px; margin-bottom: 6px; color: #38bdf8; display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 16px;">🌊</span> Gradasi Zona Tsunami Kota Padang
    </div>
    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 12px; line-height: 1.3;">
        Pola Gradasi Khusus Wilayah Administrasi Resmi Kota Padang (684.6 km²).
    </div>

    <!-- Gradient Bar Visual -->
    <div style="margin-bottom: 12px;">
        <div style="height: 14px; border-radius: 7px; background: linear-gradient(to right, #dc2626, #ea580c, #f59e0b, #eab308, #84cc16, #10b981); border: 1px solid rgba(255,255,255,0.2);"></div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #cbd5e1; margin-top: 4px;">
            <span>0m (Pantai Padang)</span>
            <span>1.5km</span>
            <span>>3km (Perbukitan Timur)</span>
        </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 6px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 14px; height: 14px; background: #dc2626; border-radius: 3px; display: inline-block;"></span>
            <span><b>Sangat Rawan</b> (0 - 500 m)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 14px; height: 14px; background: #ea580c; border-radius: 3px; display: inline-block;"></span>
            <span><b>Rawan Utama</b> (500m - 1 km)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 14px; height: 14px; background: #f59e0b; border-radius: 3px; display: inline-block;"></span>
            <span><b>Rawan Sedang</b> (1 km - 1.5 km)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 14px; height: 14px; background: #eab308; border-radius: 3px; display: inline-block;"></span>
            <span><b>Zona Waspada</b> (1.5 km - 2 km)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 14px; height: 14px; background: #84cc16; border-radius: 3px; display: inline-block;"></span>
            <span><b>Siaga Evakuasi</b> (2 km - 3 km)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 14px; height: 14px; background: #10b981; border-radius: 3px; display: inline-block;"></span>
            <span><b>Zona Sangat Aman</b> (> 3 km)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
            <span style="width: 10px; height: 10px; background: #0284c7; border: 2px solid white; border-radius: 50%; display: inline-block;"></span>
            <span><b>Shelter TES Evakuasi (143 Unit)</b></span>
        </div>
    </div>
</div>
"""

peta_web.get_root().html.add_child(folium.Element(legend_html))

html_path_local = r"c:\gemastik\peta_gradasi_zona_tsunami_padang.html"
html_path_artifact = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\6e25ee83-e7a5-43ef-bb35-d49386fe793a\peta_gradasi_zona_tsunami_padang.html"

peta_web.save(html_path_local)
peta_web.save(html_path_artifact)

print(f"[SUKSES] Peta Interaktif HTML Gradasi Khusus Kota Padang disimpan di:\n  - {html_path_local}\n  - {html_path_artifact}")
print("=" * 85)
print("PROSES SELESAI DENGAN SUKSES!")
