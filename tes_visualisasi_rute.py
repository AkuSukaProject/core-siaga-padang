import sqlite3
import polyline
import folium
import webbrowser
import os

print("Membaca database rute evakuasi...")
# 1. Buka Koneksi ke Database
db_koneksi = sqlite3.connect("database_evakuasi_padang.sqlite")
kursor = db_koneksi.cursor()

# 2. Ambil 5 sampel rute secara acak untuk diuji coba
kursor.execute("SELECT * FROM tabel_rute ORDER BY RANDOM() LIMIT 5")
sampel_rute = kursor.fetchall()
db_koneksi.close()

if not sampel_rute:
    print("Database kosong! Pastikan komputasi sebelumnya berhasil.")
    exit()

# 3. Buat Kanvas Peta (Berpusat di Padang Barat)
peta_padang = folium.Map(location=[-0.9400, 100.3600], zoom_start=14, tiles='CartoDB positron')

# Warna untuk membedakan rute
warna_rute = ['blue', 'green', 'purple', 'orange', 'darkred']

print("Menggambar rute ke atas peta...")
# 4. Iterasi dan Gambar Rute
for indeks, baris in enumerate(sampel_rute):
    id_asal = baris[0]
    nama_shelter = baris[1]
    waktu_menit = baris[2]
    poly_sandi = baris[3] # Rute Utama
    
    if poly_sandi:
        # Dekode polyline menjadi kumpulan titik Lintang/Bujur
        koordinat_rute = polyline.decode(poly_sandi)
        
        # Titik Awal (Posisi Warga) - Warna Merah
        titik_awal = koordinat_rute[0]
        folium.Marker(
            location=titik_awal,
            popup=f"Titik Awal Warga<br>ID: {id_asal}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(peta_padang)
        
        # Titik Akhir (Shelter) - Warna Biru
        titik_akhir = koordinat_rute[-1]
        folium.Marker(
            location=titik_akhir,
            popup=f"Tujuan: {nama_shelter}<br>Estimasi Waktu: {waktu_menit} Menit",
            icon=folium.Icon(color="blue", icon="flag")
        ).add_to(peta_padang)
        
        # Gambar Garis Rute (Jalan Evakuasi)
        folium.PolyLine(
            koordinat_rute,
            color=warna_rute[indeks % len(warna_rute)],
            weight=5,
            opacity=0.8,
            tooltip=f"Menuju {nama_shelter} ({waktu_menit} mnt)"
        ).add_to(peta_padang)

# 5. Simpan dan Buka di Browser
nama_file_peta = "tes_peta_evakuasi.html"
peta_padang.save(nama_file_peta)

print(f"Peta berhasil dibuat! Membuka {nama_file_peta} di browser Anda...")
webbrowser.open('file://' + os.path.realpath(nama_file_peta))