# import osmnx as ox
# import networkx as nx
# import matplotlib.pyplot as plt
# import pandas as pd
# import numpy as np
# import polyline
# import sqlite3
# import time

# print(f"OSMnx Version: {ox.__version__}")
# # ==========================================
# # PENGATURAN AGRESIF JARINGAN & SERVER
# # ==========================================
# ox.settings.log_console = True
# ox.settings.use_cache = False 

# # KUNCI SERVER: Menggunakan server Rusia yang seringkali lebih stabil untuk parser OSMnx
# ox.settings.overpass_url = "https://maps.mail.ru/osm/tools/overpass/api"
# # Matikan fungsi fallback dan limitasi
# ox.settings.overpass_rate_limit = False

# # INJEKSI TIMEOUT: Set batas kesabaran mesin menjadi 15 menit (900 detik).
# # Penting: Kita harus menyuntikkan kwargs agar requests.get() yang digunakan oleh parser status tidak gagal.
# ox.settings.timeout = 900
# ox.settings.requests_kwargs = {'verify': False} 

# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# print("\n" + "=" * 50)
# print("FASE 1: PERSIAPAN DATA SHELTER & BOUNDING BOX")
# print("=" * 50)

# file_path = "Koordinat Evakuasi TES - Sheet1.csv"
# print(f"Membaca file data shelter: {file_path}...")
# df_shelter = pd.read_csv(file_path)

# def bersihkan_kordinat(nilai):
#     if pd.isna(nilai):
#         return None
#     teks = str(nilai).strip()
#     if teks.count('.') > 1:
#         teks = teks.replace('.', '')
#         if teks.startswith('-'):
#             teks = teks[:2] + '.' + teks[2:]
#         else:
#             teks = teks[:3] + '.' + teks[3:]
#     else:
#         teks = teks.replace(',', '.')
#     try:
#         return float(teks)
#     except:
#         return None

# df_shelter['Latitude'] = df_shelter['Latitude'].apply(bersihkan_kordinat)
# df_shelter['Longitude'] = df_shelter['Longitude'].apply(bersihkan_kordinat)
# df_valid = df_shelter.dropna(subset=['Latitude', 'Longitude']).copy()
# print(f"Total Shelter valid untuk kalkulasi batas wilayah: {len(df_valid)} lokasi.")

# # 2. Kalkulasi Bounding Box Cerdas
# padding = 0.005 
# utara = df_valid['Latitude'].max() + padding
# selatan = df_valid['Latitude'].min() - padding
# timur = df_valid['Longitude'].max() + padding
# barat = df_valid['Longitude'].min() - padding

# print(f"Mengunduh jaringan jalan secara dinamis dalam Bounding Box:")
# print(f"-> Utara: {utara:.4f} | Selatan: {selatan:.4f} | Timur: {timur:.4f} | Barat: {barat:.4f}")

# # 3. MENGUNDUH GRAF DENGAN CUSTOM FILTER (Saran Anda diterapkan)
# # Menggunakan filter agar tidak semua jenis footway diambil, mengurangi beban secara drastis
# custom_filter = '["highway"~"primary|secondary|tertiary|residential|pedestrian"]'
# print("Mengunduh graf dengan custom_filter untuk efisiensi...")
# print("timeout =", ox.settings.timeout)
# print("requests =", ox.settings.requests_kwargs)
# print("overpass =", ox.settings.overpass_url)
# G_mentah = ox.graph_from_bbox(bbox=(barat, selatan, timur, utara), custom_filter=custom_filter)
# jumlah_node_mentah = len(G_mentah.nodes)

# print("\nMemproyeksikan graf ke dalam satuan meter (UTM)...")
# G_proj = ox.project_graph(G_mentah)

# print("Membersihkan graf dari jalan yang terisolasi...")
# komponen_terhubung = max(nx.weakly_connected_components(G_proj), key=len)
# G_bersih = G_proj.subgraph(komponen_terhubung).copy()
# jumlah_node_bersih = len(G_bersih.nodes)

# node_dihapus = jumlah_node_mentah - jumlah_node_bersih
# print("\n" + "=" * 45)
# print("LAPORAN PRA-PEMROSESAN GRAF AREA EVAKUASI")
# print("=" * 45)
# print(f"Total Persimpangan Awal  : {jumlah_node_mentah} titik")
# print(f"Total Persimpangan Akhir : {jumlah_node_bersih} titik")
# print(f"Node Terisolasi Dihapus  : {node_dihapus} titik")
# print("=" * 45)

# print("\n" + "=" * 50)
# print("FASE 2: INJEKSI PARAMETER EVAKUASI")
# print("=" * 50)

# kecepatan_m_per_detik = 1.5 

# for u, v, key, data in G_bersih.edges(keys=True, data=True):
#     jarak_meter = data['length']
#     data['waktu_tempuh_dasar'] = jarak_meter / kecepatan_m_per_detik
    
#     tipe_jalan = data.get('highway', 'residential')
#     if isinstance(tipe_jalan, list): tipe_jalan = tipe_jalan[0] 
        
#     lebar_meter = 3.0 
#     if 'primary' in tipe_jalan or 'secondary' in tipe_jalan:
#         lebar_meter = 6.0
#     elif 'tertiary' in tipe_jalan:
#         lebar_meter = 4.0
#     elif 'pedestrian' in tipe_jalan or 'footway' in tipe_jalan or 'path' in tipe_jalan:
#         lebar_meter = 1.5
        
#     if 'width' in data:
#         try:
#             w_val = data['width']
#             if isinstance(w_val, list): w_val = w_val[0]
#             lebar_meter = float(w_val)
#         except ValueError:
#             pass
            
#     data['lebar_estimasi'] = lebar_meter
#     data['kapasitas_maksimal'] = lebar_meter * 50

# print("Injeksi bobot dan kapasitas jalan selesai!")

# print("\n" + "=" * 50)
# print("FASE 3: PRA-KOMPUTASI RUTE ALTERNATIF & DB MOBILE")
# print("=" * 50)

# # Graf sementara (berbasis koordinat Lintang/Bujur) untuk pencocokan lokasi shelter
# G_mentah_bersih = G_mentah.subgraph(G_bersih.nodes)

# print("Mengikat (snapping) koordinat shelter ke persimpangan terdekat...")
# node_shelters = ox.distance.nearest_nodes(
#     G_mentah_bersih,  
#     X=df_valid['Longitude'].values, 
#     Y=df_valid['Latitude'].values
# )
# df_valid['Node_ID'] = node_shelters

# dict_shelter = dict(zip(df_valid['Node_ID'], df_valid['Nama_Bersih']))
# daftar_node_shelter = list(dict_shelter.keys())

# # Setup SQLite Database
# db_koneksi = sqlite3.connect("database_evakuasi_padang.sqlite")
# kursor = db_koneksi.cursor()
# kursor.execute('''
#     CREATE TABLE IF NOT EXISTS tabel_rute (
#         id_persimpangan_asal TEXT PRIMARY KEY,
#         rute_utama_nama TEXT, rute_utama_waktu REAL, rute_utama_poly TEXT,
#         rute_alt1_nama TEXT, rute_alt1_waktu REAL, rute_alt1_poly TEXT,
#         rute_alt2_nama TEXT, rute_alt2_waktu REAL, rute_alt2_poly TEXT
#     )
# ''')
# kursor.execute("DELETE FROM tabel_rute") 

# def ekstrak_polyline(G, rute_node):
#     koordinat_rute = []
#     for node in rute_node:
#         lat = G.nodes[node]['x'] 
#         lon = G.nodes[node]['y']
#         koordinat_rute.append((lat, lon))
#     return polyline.encode(koordinat_rute)

# print("\nMemulai simulasi pencarian 3 rute alternatif (Dijkstra)...")
# mulai_waktu = time.time()

# semua_persimpangan = list(G_bersih.nodes())
# data_rute_final = []

# for asal in semua_persimpangan[:10]:
#     hasil_rute_sementara = []
#     for tujuan in daftar_node_shelter:
#         try:
#             waktu_tempuh = nx.shortest_path_length(G_bersih, source=asal, target=tujuan, weight='waktu_tempuh_dasar')
#             rute = nx.shortest_path(G_bersih, source=asal, target=tujuan, weight='waktu_tempuh_dasar')
#             hasil_rute_sementara.append({
#                 'nama': dict_shelter[tujuan],
#                 'waktu': waktu_tempuh,
#                 'rute_nodes': rute
#             })
#         except nx.NetworkXNoPath:
#             continue
            
#     hasil_rute_sementara = sorted(hasil_rute_sementara, key=lambda x: x['waktu'])[:3]
#     if len(hasil_rute_sementara) > 0:
#         baris_data = [str(asal)]
#         for i in range(3):
#             if i < len(hasil_rute_sementara):
#                 r = hasil_rute_sementara[i]
#                 baris_data.extend([
#                     r['nama'], 
#                     round(r['waktu'] / 60, 2), 
#                     ekstrak_polyline(G_bersih, r['rute_nodes'])
#                 ])
#             else:
#                 baris_data.extend([None, None, None])
#         data_rute_final.append(baris_data)

# kursor.executemany('''
#     INSERT INTO tabel_rute VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
# ''', data_rute_final)
# db_koneksi.commit()
# db_koneksi.close()

# selesai_waktu = time.time()
# print(f"Berhasil! Data diekspor ke 'database_evakuasi_padang.sqlite' dalam {selesai_waktu - mulai_waktu:.2f} detik.")
# ox.save_graphml(G_bersih, "padang.graphml")



import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import polyline
import sqlite3
import time
import urllib3

print(f"OSMnx Version: {ox.__version__}")
# ==========================================
# PENGATURAN AGRESIF JARINGAN & SERVER
# ==========================================
ox.settings.log_console = True
ox.settings.use_cache = False 

ox.settings.overpass_url = "https://maps.mail.ru/osm/tools/overpass/api"
ox.settings.overpass_rate_limit = False
ox.settings.timeout = 900
ox.settings.requests_kwargs = {'verify': False} 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("\n" + "=" * 50)
print("FASE 1: PERSIAPAN DATA SHELTER & BOUNDING BOX")
print("=" * 50)

file_path = "Koordinat Evakuasi TES - Sheet1.csv"
print(f"Membaca file data shelter: {file_path}...")
df_shelter = pd.read_csv(file_path)

def bersihkan_kordinat(nilai):
    if pd.isna(nilai): return None
    teks = str(nilai).strip()
    if teks.count('.') > 1:
        teks = teks.replace('.', '')
        if teks.startswith('-'): teks = teks[:2] + '.' + teks[2:]
        else: teks = teks[:3] + '.' + teks[3:]
    else: teks = teks.replace(',', '.')
    try: return float(teks)
    except: return None

df_shelter['Latitude'] = df_shelter['Latitude'].apply(bersihkan_kordinat)
df_shelter['Longitude'] = df_shelter['Longitude'].apply(bersihkan_kordinat)
df_valid = df_shelter.dropna(subset=['Latitude', 'Longitude']).copy()
print(f"Total Shelter valid: {len(df_valid)} lokasi.")

padding = 0.005 
utara = df_valid['Latitude'].max() + padding
selatan = df_valid['Latitude'].min() - padding
timur = df_valid['Longitude'].max() + padding
barat = df_valid['Longitude'].min() - padding

print(f"Mengunduh jaringan jalan secara dinamis dalam Bounding Box:")
print(f"-> Utara: {utara:.4f} | Selatan: {selatan:.4f} | Timur: {timur:.4f} | Barat: {barat:.4f}")

custom_filter = '["highway"~"primary|secondary|tertiary|residential|pedestrian"]'
G_mentah = ox.graph_from_bbox(bbox=(barat, selatan, timur, utara), custom_filter=custom_filter)

print("\nMemproyeksikan graf ke dalam satuan meter (UTM)...")
G_proj = ox.project_graph(G_mentah)
komponen_terhubung = max(nx.weakly_connected_components(G_proj), key=len)
G_bersih = G_proj.subgraph(komponen_terhubung).copy()

# ==========================================
# MENYIAPKAN GRAF LINTANG/BUJUR UNTUK POLYLINE (Solusi 1)
# ==========================================
# Menyalin graf mentah (yang masih WGS84) khusus untuk node yang lolos pembersihan
G_latlon = G_mentah.subgraph(G_bersih.nodes()).copy()

print("\n" + "=" * 50)
print("FASE 2: INJEKSI PARAMETER EVAKUASI")
print("=" * 50)

kecepatan_m_per_detik = 1.5 

for u, v, key, data in G_bersih.edges(keys=True, data=True):
    jarak_meter = float(data.get('length', 1.0))
    data['waktu_tempuh_dasar'] = jarak_meter / kecepatan_m_per_detik

print("Injeksi bobot waktu selesai!")

print("\n" + "=" * 50)
print("FASE 3: PRA-KOMPUTASI DIJKSTRA TERBALIK (REVERSE) & DB")
print("=" * 50)

print("Mengikat (snapping) koordinat shelter ke persimpangan terdekat...")
df_valid['Node_ID'] = ox.distance.nearest_nodes(
    G_latlon,  
    X=df_valid['Longitude'].values, 
    Y=df_valid['Latitude'].values
)

dict_shelter = dict(zip(df_valid['Node_ID'], df_valid['Nama_Bersih']))
daftar_node_shelter = list(dict_shelter.keys())

db_koneksi = sqlite3.connect("database_evakuasi_padang.sqlite")
kursor = db_koneksi.cursor()
kursor.execute('''
    CREATE TABLE IF NOT EXISTS tabel_rute (
        id_persimpangan_asal TEXT PRIMARY KEY,
        rute_utama_nama TEXT, rute_utama_waktu REAL, rute_utama_poly TEXT,
        rute_alt1_nama TEXT, rute_alt1_waktu REAL, rute_alt1_poly TEXT,
        rute_alt2_nama TEXT, rute_alt2_waktu REAL, rute_alt2_poly TEXT
    )
''')
kursor.execute("DELETE FROM tabel_rute") 

# FUNGSI POLYLINE DIPERBAIKI (Menggunakan G_latlon dan atribut 'y', 'x')
def ekstrak_polyline(G_wgs, rute_node):
    koordinat_rute = []
    for node in rute_node:
        lat = G_wgs.nodes[node]['y'] 
        lon = G_wgs.nodes[node]['x']
        koordinat_rute.append((lat, lon))
    return polyline.encode(koordinat_rute)

print("\nMemulai Optimasi Dijkstra (Pencarian Mundur / Reverse Search)...")
mulai_waktu = time.time()

# MEMUTAR BALIK ARAH JALAN (REVERSE GRAPH)
# Agar kita bisa mencari dari Shelter -> Warga, bukan Warga -> Shelter
G_balik = G_bersih.reverse(copy=True)

# Membuat struktur data untuk menampung rute pemenang bagi setiap persimpangan
rute_pemenang = {node: [] for node in G_bersih.nodes()}

# Kita lakukan Dijkstra terpusat HANYA sebanyak 82 kali (jumlah shelter)
# bukan 700.000+ kali!
for shelter_node in daftar_node_shelter:
    nama_shelter = dict_shelter[shelter_node]
    
    # nx.single_source_dijkstra akan mencari jarak & rute dari 1 shelter ke SEMUA persimpangan sekaligus!
    try:
        waktu_tempuh, rute_mundur = nx.single_source_dijkstra(G_balik, source=shelter_node, weight='waktu_tempuh_dasar')
        
        # Iterasi hasil dan masukkan ke memori kandidat pemenang tiap persimpangan
        for asal, waktu in waktu_tempuh.items():
            rute_asli = rute_mundur[asal][::-1] # Balikkan kembali urutan node (Warga -> Shelter)
            rute_pemenang[asal].append({
                'nama': nama_shelter,
                'waktu': waktu,
                'rute_nodes': rute_asli
            })
    except nx.NetworkXNoPath:
        continue # Lewati jika ada shelter yang terisolasi

data_rute_final = []
# [UJI COBA]: Saat ini dibatasi 10 titik agar cepat. Hapus '[:10]' nanti untuk full run.
semua_persimpangan = list(G_bersih.nodes())

for asal in semua_persimpangan[:10]:
    # Ambil semua kandidat rute untuk persimpangan ini, urutkan dari yang tercepat
    kandidat = sorted(rute_pemenang[asal], key=lambda x: x['waktu'])[:3]
    
    if len(kandidat) > 0:
        baris_data = [str(asal)]
        for i in range(3):
            if i < len(kandidat):
                r = kandidat[i]
                baris_data.extend([
                    r['nama'], 
                    round(r['waktu'] / 60, 2), # Menit
                    ekstrak_polyline(G_latlon, r['rute_nodes'])
                ])
            else:
                baris_data.extend([None, None, None])
        data_rute_final.append(baris_data)

kursor.executemany('INSERT INTO tabel_rute VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data_rute_final)
db_koneksi.commit()
db_koneksi.close()

ox.save_graphml(G_bersih, "padang.graphml")

selesai_waktu = time.time()
print(f"Berhasil! Eksekusi Selesai dalam {selesai_waktu - mulai_waktu:.2f} detik.")