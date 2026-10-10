import os
import re
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, LineString
from scipy.spatial import cKDTree
import folium
from folium.plugins import PolyLineTextPath
import webbrowser

print("=" * 80)
print("GENERATOR GAMBAR 5.6: SIMULASI 1 GEDUNG TES & 1 JALUR EVAKUASI (PADANG BARAT)")
print("DENGAN ICON PANAH PENUNJUK ARAH EVAKUASI & TOGGLE THEME")
print("========================================================================")

# 1. Memuat Graf Jaringan Jalan (padang.graphml)
file_graph = "padang.graphml"
print(f"[1/5] Membaca graf jaringan jalan: {file_graph}...")
G = nx.read_graphml(file_graph).to_undirected()

transformer = Transformer.from_crs("EPSG:32747", "EPSG:4326", always_xy=True)

def bersihkan_angka_osm(val, default=50.0):
    if pd.isna(val) or val is None: return default
    if isinstance(val, list): val = str(val[0])
    val = str(val).strip()
    if '-' in val: val = val.split('-')[0]
    match = re.search(r"(\d+(\.\d+)?)", val)
    return float(match.group(1)) if match else default

# Ekstraksi Koordinat Node & Pre-processing Length
node_coords = {}
nodes_list = []
coords_list = []
for node, data in G.nodes(data=True):
    if 'x' in data and 'y' in data:
        x_m, y_m = float(data['x']), float(data['y'])
        lon, lat = transformer.transform(x_m, y_m)
        node_coords[node] = (lon, lat)
        nodes_list.append(node)
        coords_list.append([lat, lon])

tree = cKDTree(coords_list)

for u, v, k, data in G.edges(keys=True, data=True):
    data['len_num'] = bersihkan_angka_osm(data.get('length', 50.0), 50.0)

# 2. Penentuan 1 Gedung TES & 1 Titik Awal Warga Pesisir di Padang Barat
print("[2/5] Menentukan 1 Gedung TES Utama & 1 Titik Awal Evakuasi Pesisir...")

# TES Target: Masjid Agung Nurul Iman, Padang Barat (-0.9525, 100.362154)
tes_nama = "Masjid Agung Nurul Iman (TES)"
tes_lat_target, tes_lon_target = -0.9525, 100.362154
_, idx_target = tree.query([tes_lat_target, tes_lon_target])
target_node = nodes_list[idx_target]

# Origin: Area Pesisir Pantai Padang / Purus, Padang Barat (-0.9555, 100.3508)
coastal_lat_origin, coastal_lon_origin = -0.9555, 100.3508
_, idx_origin = tree.query([coastal_lat_origin, coastal_lon_origin])
origin_node = nodes_list[idx_origin]

# 3. Menghitung Rute Evakuasi Tercepat
print("[3/5] Menhitung Jalur Evakuasi Tercepat...")
path_nodes = nx.shortest_path(G, source=origin_node, target=target_node, weight='len_num')
rute_coords = [(node_coords[n][1], node_coords[n][0]) for n in path_nodes] # (lat, lon)
rute_coords_lonlat = [(node_coords[n][0], node_coords[n][1]) for n in path_nodes] # (lon, lat)

def get_edge_len(u, v):
    e_data = G.get_edge_data(u, v)
    if e_data:
        first_key = list(e_data.keys())[0]
        return e_data[first_key].get('len_num', 50.0)
    return 50.0

total_jarak_m = sum(get_edge_len(u, v) for u, v in zip(path_nodes[:-1], path_nodes[1:]))
waktu_menit = (total_jarak_m / 1.2) / 60.0 # Kecepatan jalan kaki 1.2 m/s

print(f"      Jalur Evakuasi Ditemukan: {len(rute_coords)} titik node")
print(f"      Total Jarak Evakuasi    : {total_jarak_m:.1f} meter ({total_jarak_m/1000:.2f} km)")
print(f"      Estimasi Waktu Tempuh   : {waktu_menit:.1f} menit")

# Perhitungan Bearing Panah Penunjuk Arah
def hitung_bearing(lat1, lon1, lat2, lon2):
    dlon = np.radians(lon2 - lon1)
    lat1, lat2 = np.radians(lat1), np.radians(lat2)
    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    bearing = np.degrees(np.arctan2(x, y))
    return (bearing + 360) % 360

arrow_markers = []
step = max(1, len(rute_coords) // 6)
for i in range(0, len(rute_coords) - 1, step):
    p1 = rute_coords[i]
    p2 = rute_coords[min(i + 1, len(rute_coords) - 1)]
    bearing = hitung_bearing(p1[0], p1[1], p2[0], p2[1])
    arrow_markers.append({
        'lat': p1[0], 'lon': p1[1],
        'next_lat': p2[0], 'next_lon': p2[1],
        'bearing': bearing
    })

# Memuat Batas Kelurahan & Kecamatan
file_pb = "batas_kelurahan_padang_barat.geojson"
gdf_pb = gpd.read_file(file_pb) if os.path.exists(file_pb) else None
if gdf_pb is not None and gdf_pb.crs != "EPSG:4326":
    gdf_pb = gdf_pb.to_crs("EPSG:4326")

file_kota = "batas_kelurahan_kota_padang.geojson"
gdf_kota = gpd.read_file(file_kota) if os.path.exists(file_kota) else None
if gdf_kota is not None and gdf_kota.crs != "EPSG:4326":
    gdf_kota = gdf_kota.to_crs("EPSG:4326")

# 4. MERENDER GAMBAR 5.6 (HIGH-RESOLUTION PNG 300 DPI - WHITE BACKGROUND)
print("[4/5] Merender Gambar 5.6 High-Resolution PNG (WHITE BACKGROUND)...")

fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#ffffff')

# Plot Wilayah Kota Padang Background (Clean Light Slate / White Canvas)
if gdf_kota is not None:
    gdf_kota.plot(ax=ax, facecolor='#f8fafc', edgecolor='#cbd5e1', linewidth=0.9, alpha=0.9)

# Plot Wilayah Utama Padang Barat (Soft Ocean Blue Accent Highlight)
if gdf_pb is not None:
    gdf_pb.plot(ax=ax, facecolor='#e0f2fe', edgecolor='#0284c7', linewidth=1.8, alpha=0.6)
    gdf_pb.boundary.plot(ax=ax, color='#0284c7', linewidth=1.5, linestyle='--')

# Plot Line Jalur Evakuasi Tsunami (Vibrant Blue matching screenshot)
ax.plot([c[0] for c in rute_coords_lonlat], [c[1] for c in rute_coords_lonlat], color='#6366f1', linewidth=5.5, alpha=0.95, zorder=5, label='Jalur Evakuasi Tsunami')
ax.plot([c[0] for c in rute_coords_lonlat], [c[1] for c in rute_coords_lonlat], color='#ffffff', linewidth=1.5, alpha=0.9, zorder=6)

# Plot Panah Penunjuk Arah di Matplotlib
for arr in arrow_markers:
    ax.annotate(
        '', xy=(arr['next_lon'], arr['next_lat']), xytext=(arr['lon'], arr['lat']),
        arrowprops=dict(facecolor='#6366f1', edgecolor='#ffffff', arrowstyle='->', lw=2.2, mutation_scale=18),
        zorder=7
    )

# Plot Origin Point Marker (Posisi Warga Pesisir)
ax.scatter(rute_coords_lonlat[0][0], rute_coords_lonlat[0][1], s=140, color='#3b82f6', edgecolor='#1d4ed8', linewidth=2.0, zorder=8)
ax.annotate(
    "Titik Awal Evakuasi Warga (Pesisir Pantai Padang)",
    xy=(rute_coords_lonlat[0][0], rute_coords_lonlat[0][1]),
    xytext=(rute_coords_lonlat[0][0] - 0.012, rute_coords_lonlat[0][1] - 0.005),
    arrowprops=dict(facecolor='#3b82f6', edgecolor='#1d4ed8', arrowstyle='->', lw=1.2),
    fontsize=8.5, fontweight='bold', color='#1e293b',
    bbox=dict(boxstyle='round,pad=0.35', facecolor='#ffffff', edgecolor='#3b82f6', alpha=0.95, lw=1.0),
    zorder=9
)

# Plot Target TES Marker (Masjid Agung Nurul Iman)
ax.scatter(rute_coords_lonlat[-1][0], rute_coords_lonlat[-1][1], s=160, color='#facc15', edgecolor='#dc2626', linewidth=2.2, zorder=8)
ax.annotate(
    f"TES: {tes_nama}\n(Estimasi {waktu_menit:.1f} mnt — {total_jarak_m/1000:.2f} km)",
    xy=(rute_coords_lonlat[-1][0], rute_coords_lonlat[-1][1]),
    xytext=(rute_coords_lonlat[-1][0] + 0.004, rute_coords_lonlat[-1][1] + 0.005),
    arrowprops=dict(facecolor='#dc2626', edgecolor='#dc2626', arrowstyle='->', lw=1.2),
    fontsize=8.5, fontweight='bold', color='#1e293b',
    bbox=dict(boxstyle='round,pad=0.35', facecolor='#ffffff', edgecolor='#dc2626', alpha=0.95, lw=1.0),
    zorder=9
)

# Bounds Focus Padang Barat & Rute
min_lon, max_lon = min(c[0] for c in rute_coords_lonlat) - 0.015, max(c[0] for c in rute_coords_lonlat) + 0.015
min_lat, max_lat = min(c[1] for c in rute_coords_lonlat) - 0.012, max(c[1] for c in rute_coords_lonlat) + 0.012
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)

# Judul Gambar 5.6
plt.title("Gambar 5.6 Simulasi 1 Gedung TES & 1 Jalur Evakuasi Padang Barat", fontsize=14, fontweight='bold', color='#0f172a', pad=18)
ax.text(0.5, 0.975, "Visualisasi Jalur Evakuasi Tsunami dengan Icon Panah Penunjuk Arah Evakuasi Warga Pesisir", 
        transform=ax.transAxes, ha='center', fontsize=10, color='#475569', style='italic')

# Legend Elements (White Clean Background Mode)
legend_elements = [
    Line2D([0], [0], color='#6366f1', lw=3.5, label=f'Jalur Evakuasi Tsunami ({total_jarak_m/1000:.2f} km)'),
    Line2D([0], [0], marker='o', color='w', label='Titik Awal Warga (Pesisir Pantai)', markerfacecolor='#3b82f6', markeredgecolor='#1d4ed8', markersize=9),
    Line2D([0], [0], marker='o', color='w', label=f'TES: {tes_nama}', markerfacecolor='#facc15', markeredgecolor='#dc2626', markersize=9),
    mpatches.Patch(facecolor='#e0f2fe', edgecolor='#0284c7', linewidth=1.5, alpha=0.6, label='Batas Wilayah Padang Barat'),
    mpatches.Patch(facecolor='#f8fafc', edgecolor='#cbd5e1', linewidth=1.0, alpha=0.9, label='Batas Wilayah Kota Padang')
]

legend = ax.legend(handles=legend_elements, loc='lower right', facecolor='#ffffff', edgecolor='#cbd5e1', 
                   fontsize=8.5, labelcolor='#0f172a', framealpha=0.95, borderpad=0.8)

ax.tick_params(colors='#475569', labelsize=8)
ax.grid(True, color='#e2e8f0', linestyle=':', linewidth=0.6, alpha=0.8)
ax.set_xlabel("Bujur (Longitude)", color='#334155', fontsize=9, labelpad=8)
ax.set_ylabel("Lintang (Latitude)", color='#334155', fontsize=9, labelpad=8)

png_filename = r"c:\gemastik\gambar_5_6_titik_penumpukan.png"

plt.savefig(png_filename, bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=300)
plt.close()
print(f"[SUKSES] Gambar PNG High-Resolution (White Background) disimpan di: '{png_filename}'")

# 5. MEMBUAT PETA INTERAKTIF FOLIUM (HTML - DARK & LIGHT MODE WITH TOGGLE & NAVIGATION ICONS)
print("[5/5] Membangun Peta Web Interaktif HTML (MATCHING SCREENSHOT DESIGN)...")
center_lat = (rute_coords[0][0] + rute_coords[-1][0]) / 2
center_lon = (rute_coords[0][1] + rute_coords[-1][1]) / 2

peta_web = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=16,
    tiles=None # Base tiles diset via TileLayer
)

# Base Tile Layers for Toggle (Default Light Mode match screenshot)
tile_light = folium.TileLayer(
    tiles='CartoDB positron',
    name='☀️ Mode Terang (Light)',
    control=True
).add_to(peta_web)

tile_dark = folium.TileLayer(
    tiles='CartoDB dark_matter',
    name='🌙 Mode Gelap (Dark)',
    control=True
).add_to(peta_web)

# Layer 1: Boundary Kota Padang
if gdf_kota is not None:
    folium.GeoJson(
        gdf_kota,
        name="📍 Batas Wilayah Kota Padang",
        style_function=lambda x: {
            'fillColor': '#1e293b',
            'color': '#3b82f6',
            'weight': 1.2,
            'fillOpacity': 0.15
        }
    ).add_to(peta_web)

# Layer 2: Boundary Padang Barat
if gdf_pb is not None:
    folium.GeoJson(
        gdf_pb,
        name="📍 Batas Kecamatan Padang Barat",
        style_function=lambda x: {
            'fillColor': '#38bdf8',
            'color': '#0284c7',
            'weight': 2.0,
            'fillOpacity': 0.12
        }
    ).add_to(peta_web)

# Layer 3: PolyLine Jalur Evakuasi Tsunami (Vibrant Blue/Indigo matching screenshot)
route_polyline = folium.PolyLine(
    rute_coords,
    color='#6366f1',
    weight=7,
    opacity=0.9,
    tooltip=f"<b>Jalur Evakuasi Tsunami</b><br/>Menuju {tes_nama}<br/>Jarak: {total_jarak_m/1000:.2f} km | Waktu: {waktu_menit:.1f} mnt"
).add_to(peta_web)

# Layer 4: Navigation Arrow Origin Marker (Location Arrow in Blue Circle Ring)
initial_bearing = arrow_markers[0]['bearing'] if arrow_markers else 0
origin_icon_html = f'''
<div style="
    width: 44px; height: 44px;
    border: 2.5px solid #3b82f6;
    border-radius: 50%;
    background: rgba(59, 130, 246, 0.18);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
">
    <svg width="26" height="26" viewBox="0 0 24 24" style="transform: rotate({initial_bearing - 45}deg); filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.4));">
        <path fill="#6366f1" stroke="#ffffff" stroke-width="1.8" d="M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z"/>
    </svg>
</div>
'''
folium.Marker(
    location=rute_coords[0],
    icon=folium.DivIcon(html=origin_icon_html, icon_size=(44, 44), icon_anchor=(22, 22)),
    popup="<b>📍 Titik Awal Evakuasi Warga Pesisir</b>",
    tooltip="📍 Posisi Awal Evakuasi Warga"
).add_to(peta_web)

# Layer 5: Destination Pin Marker (Yellow Pin with Red Circle Ring & Red Dot)
dest_pin_html = '''
<div style="
    position: relative;
    width: 28px;
    height: 38px;
    display: flex;
    flex-direction: column;
    align-items: center;
    filter: drop-shadow(0px 3px 6px rgba(0,0,0,0.4));
">
    <div style="
        width: 24px;
        height: 24px;
        background: #facc15;
        border: 3px solid #dc2626;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    ">
        <div style="width: 7px; height: 7px; background: #dc2626; border-radius: 50%;"></div>
    </div>
    <div style="
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 8px solid #dc2626;
        margin-top: -2px;
    "></div>
</div>
'''
folium.Marker(
    location=rute_coords[-1],
    icon=folium.DivIcon(html=dest_pin_html, icon_size=(28, 38), icon_anchor=(14, 38)),
    popup=f"<b>🏢 {tes_nama}</b><br/>Tujuan Evakuasi Tsunami Padang Barat",
    tooltip=f"🏢 TES: {tes_nama}"
).add_to(peta_web)

# Title Badge UI Card with Theme Switcher Button (Default Light Mode match screenshot)
title_html = f"""
<style>
.leaflet-container {{
    background-color: #ffffff !important;
}}
</style>

<div id="title-card" style="
    position: fixed; 
    top: 15px; left: 60px; width: 470px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    color: #0f172a;
    padding: 14px 18px;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    font-family: 'Segoe UI', Arial, sans-serif;
    z-index: 9999;
    border: 1px solid rgba(0, 0, 0, 0.12);
    transition: all 0.3s ease;
">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div id="card-badge" style="font-size: 13px; font-weight: 800; color: #dc2626; text-transform: uppercase; letter-spacing: 0.5px;">
            SIMULASI RUTE EVAKUASI (LIGHT MODE)
        </div>
        <button id="theme-toggle-btn" onclick="window.toggleTheme && window.toggleTheme()" style="
            background: #0f172a;
            color: #ffffff;
            border: 1px solid #334155;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        ">
            🌙 Mode Gelap
        </button>
    </div>
    <div id="card-title" style="font-size: 12px; font-weight: 700; color: #0f172a; margin-top: 6px;">
        Visualisasi 1 Gedung TES & 1 Jalur Evakuasi Tsunami Padang Barat
    </div>
    <div id="card-desc" style="font-size: 11px; color: #475569; margin-top: 4px; line-height: 1.5;">
        Tujuan: <b>{tes_nama}</b> ({total_jarak_m/1000:.2f} km — ~{waktu_menit:.1f} mnt) dengan Panah Navigasi.
    </div>
</div>

<script>
window.currentMode = 'light';

window.toggleTheme = function() {{
    var mainMap = null;
    for (var key in window) {{
        if (key.indexOf('map_') === 0 && window[key] && typeof window[key].addLayer === 'function') {{
            mainMap = window[key];
            break;
        }}
    }}
    
    if (!mainMap) {{
        console.warn("Leaflet Map object not found yet.");
        return;
    }}

    if (!window.darkTileLayer) {{
        window.darkTileLayer = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CartoDB',
            maxZoom: 19
        }});
    }}
    if (!window.lightTileLayer) {{
        window.lightTileLayer = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CartoDB',
            maxZoom: 19
        }});
    }}

    var card = document.getElementById('title-card');
    var badge = document.getElementById('card-badge');
    var titleText = document.getElementById('card-title');
    var descText = document.getElementById('card-desc');
    var toggleBtn = document.getElementById('theme-toggle-btn');

    if (window.currentMode === 'light') {{
        window.currentMode = 'dark';
        
        mainMap.eachLayer(function(layer) {{
            if (layer instanceof L.TileLayer) {{
                mainMap.removeLayer(layer);
            }}
        }});
        mainMap.addLayer(window.darkTileLayer);

        if (card) {{
            card.style.background = 'rgba(15, 23, 42, 0.88)';
            card.style.color = '#f8fafc';
            card.style.border = '1px solid rgba(255, 255, 255, 0.15)';
            card.style.boxShadow = '0 10px 25px rgba(0,0,0,0.5)';
        }}
        if (badge) {{
            badge.style.color = '#ff2a6d';
            badge.innerText = 'SIMULASI RUTE EVAKUASI (DARK MODE)';
        }}
        if (titleText) titleText.style.color = '#f8fafc';
        if (descText) descText.style.color = '#cbd5e1';
        if (toggleBtn) {{
            toggleBtn.innerHTML = '☀️ Mode Terang';
            toggleBtn.style.background = 'rgba(255, 255, 255, 0.15)';
            toggleBtn.style.color = '#ffffff';
            toggleBtn.style.border = '1px solid rgba(255, 255, 255, 0.3)';
        }}
    }} else {{
        window.currentMode = 'light';
        
        mainMap.eachLayer(function(layer) {{
            if (layer instanceof L.TileLayer) {{
                mainMap.removeLayer(layer);
            }}
        }});
        mainMap.addLayer(window.lightTileLayer);

        if (card) {{
            card.style.background = 'rgba(255, 255, 255, 0.95)';
            card.style.color = '#0f172a';
            card.style.border = '1px solid rgba(0, 0, 0, 0.12)';
            card.style.boxShadow = '0 10px 25px rgba(0,0,0,0.15)';
        }}
        if (badge) {{
            badge.style.color = '#dc2626';
            badge.innerText = 'SIMULASI RUTE EVAKUASI (LIGHT MODE)';
        }}
        if (titleText) titleText.style.color = '#0f172a';
        if (descText) descText.style.color = '#475569';
        if (toggleBtn) {{
            toggleBtn.innerHTML = '🌙 Mode Gelap';
            toggleBtn.style.background = '#0f172a';
            toggleBtn.style.color = '#ffffff';
            toggleBtn.style.border = '1px solid #334155';
        }}
    }}
}};
</script>
"""
peta_web.get_root().html.add_child(folium.Element(title_html))
peta_web.fit_bounds([[min(c[0] for c in rute_coords), min(c[1] for c in rute_coords)], [max(c[0] for c in rute_coords), max(c[1] for c in rute_coords)]])
folium.LayerControl().add_to(peta_web)

html_filename = "gambar_5_6_titik_penumpukan.html"
peta_web.save(html_filename)
html_abs_path = os.path.abspath(html_filename)

print(f"[SUKSES] Peta Interaktif HTML Rute Evakuasi & Panah Penunjuk disimpan: '{html_filename}'")
print(f"[INFO] Jalur Absolut HTML: file:///{html_abs_path.replace('\\', '/')}")

try:
    webbrowser.open(f"file:///{html_abs_path.replace('\\', '/')}")
    print(f"[BROWSER] Membuka '{html_filename}' secara otomatis di web browser...")
except Exception as e:
    print(f"[NOTE] Anda dapat membuka '{html_filename}' secara manual di browser.")
