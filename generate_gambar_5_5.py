import os
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pyproj import Transformer
from shapely.geometry import Point, LineString
import folium

print("=" * 80)
print("GENERATOR GAMBAR 5.5: VISUALISASI GRAF JARINGAN JALAN PEJALAN KAKI")
print("KECAMATAN PADANG BARAT BESERTA WILAYAH PENYANGGA")
print("=" * 80)

# 1. Memuat Graf Jaringan Jalan (padang.graphml)
file_graph = "padang.graphml"
print(f"[1/5] Membaca graf jaringan jalan: {file_graph}...")
G = nx.read_graphml(file_graph)

# Transformasi Koordinat (EPSG:32747 -> EPSG:4326)
transformer = Transformer.from_crs("EPSG:32747", "EPSG:4326", always_xy=True)

nodes_dict = {}
nodes_gdf_list = []
for node, data in G.nodes(data=True):
    if 'x' in data and 'y' in data:
        x_m, y_m = float(data['x']), float(data['y'])
        lon, lat = transformer.transform(x_m, y_m)
        nodes_dict[node] = (lon, lat)
        nodes_gdf_list.append({'node_id': node, 'lon': lon, 'lat': lat, 'geometry': Point(lon, lat)})

gdf_nodes = gpd.GeoDataFrame(nodes_gdf_list, crs="EPSG:4326")
print(f"      Total Node: {len(G.nodes):,} | Total Edge: {len(G.edges):,}")

# Build Edge Geometries
edges_lines = []
for u, v, d in G.edges(data=True):
    if u in nodes_dict and v in nodes_dict:
        lon1, lat1 = nodes_dict[u]
        lon2, lat2 = nodes_dict[v]
        edges_lines.append({'u': u, 'v': v, 'geometry': LineString([(lon1, lat1), (lon2, lat2)])})

gdf_edges = gpd.GeoDataFrame(edges_lines, crs="EPSG:4326")

# 2. Memuat Batas Wilayah (Padang Barat & Seluruh Kota Padang untuk Buffer)
print("[2/5] Membaca GeoJSON Batas Kelurahan & Kecamatan...")
file_pb = "batas_kelurahan_padang_barat.geojson"
gdf_pb = gpd.read_file(file_pb) if os.path.exists(file_pb) else None
if gdf_pb is not None and gdf_pb.crs != "EPSG:4326":
    gdf_pb = gdf_pb.to_crs("EPSG:4326")

file_padang_full = "batas_kelurahan_kota_padang.geojson"
gdf_kota = gpd.read_file(file_padang_full) if os.path.exists(file_padang_full) else None
if gdf_kota is not None and gdf_kota.crs != "EPSG:4326":
    gdf_kota = gdf_kota.to_crs("EPSG:4326")

# 3. Memuat Lokasi Gedung TES (Evakuasi Tsunami)
print("[3/5] Membaca Data Lokasi TES...")
file_shelter = "shelter_padang_barat_berkoordinat_rapi.csv" if os.path.exists("shelter_padang_barat_berkoordinat_rapi.csv") else "Koordinat Evakuasi TES - Sheet1.csv"
df_shelter = pd.read_csv(file_shelter)

def parse_coord(val):
    try: return float(str(val).strip().replace(',', '.'))
    except: return np.nan

lat_col = 'Latitude' if 'Latitude' in df_shelter.columns else 'Clean_Lat'
lon_col = 'Longitude' if 'Longitude' in df_shelter.columns else 'Clean_Lon'

df_shelter['lat_clean'] = df_shelter[lat_col].apply(parse_coord)
df_shelter['lon_clean'] = df_shelter[lon_col].apply(parse_coord)
df_shelter = df_shelter.dropna(subset=['lat_clean', 'lon_clean']).copy()

gdf_shelter = gpd.GeoDataFrame(
    df_shelter, 
    geometry=gpd.points_from_xy(df_shelter['lon_clean'], df_shelter['lat_clean']),
    crs="EPSG:4326"
)

# Filter spatial bounding box untuk visualisasi
min_lon, max_lon = gdf_edges.total_bounds[0], gdf_edges.total_bounds[2]
min_lat, max_lat = gdf_edges.total_bounds[1], gdf_edges.total_bounds[3]

# 4. MEMBUAT PUBLICATION-QUALITY PNG MAP IMAGE (GAMBAR 5.5)
print("[4/5] Merender Gambar 5.5 High-Resolution (PNG)...")

fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
fig.patch.set_facecolor('#0b1329')
ax.set_facecolor('#0b1329')

# Plot Wilayah Penyangga (Kecamatan Sekitar)
if gdf_kota is not None:
    gdf_kota.plot(ax=ax, facecolor='#111c38', edgecolor='#1e2d54', linewidth=0.8, alpha=0.7, label='Wilayah Penyangga')

# Plot Wilayah Utama (Kecamatan Padang Barat)
if gdf_pb is not None:
    gdf_pb.plot(ax=ax, facecolor='#1e3a8a', edgecolor='#38bdf8', linewidth=1.8, alpha=0.45, label='Kecamatan Padang Barat')
    gdf_pb.boundary.plot(ax=ax, color='#38bdf8', linewidth=2.0, linestyle='--')

# Plot Jaringan Jalan (Edges Graph)
gdf_edges.plot(ax=ax, color='#06b6d4', linewidth=0.55, alpha=0.75, label='Ruas Jalan Pejalan Kaki (Edges)')

# Plot Simpang/Persimpangan (Nodes Graph)
ax.scatter(gdf_nodes['lon'], gdf_nodes['lat'], s=1.2, color='#a5f3fc', alpha=0.5, zorder=3, label='Persimpangan/Node (9.354 Nodes)')

# Plot Gedung Tempat Evakuasi Sementara (TES)
ax.scatter(df_shelter['lon_clean'], df_shelter['lat_clean'], s=38, color='#ef4444', edgecolor='#ffffff', linewidth=0.8, zorder=5, label='Bangunan TES Evakuasi')

# Set Bounding Box Zoom dengan Margin
lon_margin = (max_lon - min_lon) * 0.04
lat_margin = (max_lat - min_lat) * 0.04
ax.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

# Judul Gambar 5.5
plt.title("Gambar 5.5 Jaringan jalan pejalan kaki wilayah kajian", fontsize=15, fontweight='bold', color='#f8fafc', pad=18)
ax.text(0.5, 0.975, "Visualisasi Graf Jaringan Jalan Pejalan Kaki Kecamatan Padang Barat Beserta Wilayah Penyangga", 
        transform=ax.transAxes, ha='center', fontsize=11, color='#94a3b8', style='italic')

# Custom Legend
legend_elements = [
    mpatches.Patch(facecolor='#1e3a8a', edgecolor='#38bdf8', linewidth=1.5, alpha=0.6, label='Kecamatan Padang Barat (Wilayah Utama)'),
    mpatches.Patch(facecolor='#111c38', edgecolor='#1e2d54', linewidth=0.8, label='Wilayah Penyangga (Buffer Zone)'),
    Line2D([0], [0], color='#06b6d4', lw=1.2, label=f'Ruas Jalan Pejalan Kaki ({len(G.edges):,} Edges)'),
    Line2D([0], [0], marker='o', color='w', label=f'Node/Persimpangan Jalan ({len(G.nodes):,} Nodes)', markerfacecolor='#a5f3fc', markersize=4),
    Line2D([0], [0], marker='o', color='w', label=f'Gedung TES Shelter ({len(df_shelter)} Lokasi)', markerfacecolor='#ef4444', markersize=7)
]

legend = ax.legend(handles=legend_elements, loc='lower right', facecolor='#0f172a', edgecolor='#334155', 
                   fontsize=9, labelcolor='#f8fafc', framealpha=0.92, borderpad=0.8)

# Styling Axis & Grid
ax.tick_params(colors='#94a3b8', labelsize=8)
ax.grid(True, color='#1e293b', linestyle=':', linewidth=0.5, alpha=0.7)
ax.set_xlabel("Bujur (Longitude)", color='#cbd5e1', fontsize=9, labelpad=8)
ax.set_ylabel("Lintang (Latitude)", color='#cbd5e1', fontsize=9, labelpad=8)

# Simpan PNG High-Res
png_filename = "gambar_5_5_graf_padang_barat.png"
plt.savefig(png_filename, bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=300)
plt.close()
print(f"[SUKSES] Gambar PNG High-Resolution disimpan: '{png_filename}'")

# 5. MEMBUAT PETA INTERAKTIF FOLIUM (HTML)
print("[5/5] Membangun Peta Web Interaktif (HTML)...")
center_lat = (min_lat + max_lat) / 2
center_lon = (min_lon + max_lon) / 2

peta_web = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=14,
    tiles='cartodbdark_matter'
)

# Layer 1: Boundary Padang Barat
if gdf_pb is not None:
    folium.GeoJson(
        gdf_pb,
        name="📍 Batas Kecamatan Padang Barat",
        style_function=lambda x: {
            'fillColor': '#0284c7',
            'color': '#38bdf8',
            'weight': 2.5,
            'fillOpacity': 0.2
        },
        tooltip=folium.GeoJsonTooltip(fields=['NAMOBJ'], aliases=['Kelurahan:'])
    ).add_to(peta_web)

# Layer 2: Edges Graf Jalan
garis_jalan = [[(lat1, lon1), (lat2, lon2)] for u, v in G.edges() if u in nodes_dict and v in nodes_dict for lon1, lat1 in [nodes_dict[u]] for lon2, lat2 in [nodes_dict[v]]]

folium.PolyLine(
    garis_jalan,
    color='#06b6d4',
    weight=1.2,
    opacity=0.7,
    tooltip="Ruas Jalan Pejalan Kaki"
).add_to(peta_web)

# Layer 3: TES Markers
for idx, row in df_shelter.iterrows():
    nama = row.get('Nama_Bersih', row.get('Lokasi_TES', 'Gedung TES'))
    folium.CircleMarker(
        location=[row['lat_clean'], row['lon_clean']],
        radius=5,
        color='#dc2626',
        fill=True,
        fill_color='#ef4444',
        fill_opacity=0.9,
        popup=f"<b>{nama}</b>",
        tooltip=f"🏢 TES: {nama}"
    ).add_to(peta_web)

# Floating Title Badge
title_html = """
<div style="
    position: fixed; 
    top: 15px; left: 60px; width: 420px;
    background: rgba(15, 23, 42, 0.92);
    backdrop-filter: blur(8px);
    color: white;
    padding: 12px 16px;
    border-radius: 10px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    font-family: 'Segoe UI', Arial, sans-serif;
    z-index: 9999;
    border: 1px solid rgba(255,255,255,0.15);
">
    <div style="font-size: 13px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.5px;">
        GAMBAR 5.5
    </div>
    <div style="font-size: 12px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
        Jaringan Jalan Pejalan Kaki Wilayah Kajian
    </div>
    <div style="font-size: 11px; color: #94a3b8; margin-top: 4px; line-height: 1.4;">
        Visualisasi Graf Jaringan Jalan Kecamatan Padang Barat beserta Wilayah Penyangga (9.354 Node, 22.137 Edges).
    </div>
</div>
"""
peta_web.get_root().html.add_child(folium.Element(title_html))
folium.LayerControl().add_to(peta_web)

html_filename = "gambar_5_5_graf_padang_barat.html"
peta_web.save(html_filename)
print(f"[SUKSES] Peta Interaktif HTML disimpan: '{html_filename}'")
