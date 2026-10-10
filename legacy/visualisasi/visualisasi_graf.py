import networkx as nx
import folium
from pyproj import Transformer
import time

print("="*60)
print("VISUALISASI JARINGAN JALAN KOTA PADANG (WEB INTERAKTIF)")
print("="*60)

start_time = time.time()

print("[1/4] Membaca data padang.graphml...")
G = nx.read_graphml("padang_full.graphml")

print("[2/4] Mengekstrak & Menstandarisasi Koordinat (Lat/Lon)...")
sample_node = next(iter(G.nodes(data=True)))[1]
is_meter = 'x' in sample_node and abs(float(sample_node['x'])) > 180

if is_meter:
    crs_asal = G.graph.get('crs', 'EPSG:32747')
    transformer = Transformer.from_crs(crs_asal, "EPSG:4326", always_xy=True)

koordinat_node = {}
for node, data in G.nodes(data=True):
    if 'x' in data and 'y' in data:
        x_val, y_val = float(data['x']), float(data['y'])
        if is_meter:
            x_val, y_val = transformer.transform(x_val, y_val)
        
        # Folium membutuhkan format (Latitude, Longitude) yang berarti (Y, X)
        koordinat_node[node] = (y_val, x_val)

# Mencari titik tengah peta agar kamera otomatis fokus ke Padang
semua_lat = [coords[0] for coords in koordinat_node.values()]
semua_lon = [coords[1] for coords in koordinat_node.values()]
center_lat = sum(semua_lat) / len(semua_lat)
center_lon = sum(semua_lon) / len(semua_lon)

print("[3/4] Membangun Peta Web Interaktif...")
# Membuat kanvas peta dengan tema gelap
peta_web = folium.Map(
    location=[center_lat, center_lon], 
    zoom_start=14, 
    tiles='cartodbdark_matter' # Tema gelap yang elegan
)

# Mengumpulkan semua garis jalan ke dalam satu list (untuk efisiensi render browser)
garis_jalan = []
for u, v in G.edges():
    if u in koordinat_node and v in koordinat_node:
        garis_jalan.append([koordinat_node[u], koordinat_node[v]])

# Menggambar seluruh jaringan jalan sekaligus menggunakan Multi-PolyLine
folium.PolyLine(
    garis_jalan, 
    color='#00ffcc', # Warna Cyan menyala
    weight=1.5, 
    opacity=0.6
).add_to(peta_web)

print("[4/4] Menyimpan ke file HTML...")
output_filename = "peta_interaktif_padang.html"
peta_web.save(output_filename)

print(f"\n✅ SUKSES! Peta interaktif selesai dalam {time.time() - start_time:.2f} detik.")
print(f"Silakan klik ganda (double-click) file '{output_filename}' untuk membukanya di browser Chrome/Edge Anda!")