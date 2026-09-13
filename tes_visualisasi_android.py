import sqlite3
import folium
import webbrowser
import os

def visualisasi_rute_dari_db(db_name="ranah_siaga.db", target_node_id=None):
    print("="*70)
    print("VISUALISASI RUTE ANDROID DARI SQLITE (FOLIUM)")
    print("="*70)

    try:
        if not os.path.exists(db_name):
            print(f"[ERROR] File database '{db_name}' tidak ditemukan!")
            return

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # 1. Tentukan Titik Awal (Origin)
        if target_node_id is None:
            cursor.execute("SELECT origin_node_id FROM tb_routes ORDER BY RANDOM() LIMIT 1")
            hasil = cursor.fetchone()
            if not hasil:
                print("[ERROR] Tabel tb_routes kosong!")
                return
            target_node_id = hasil[0]

        print(f"[+] Menyiapkan Peta untuk Posisi Pengguna (Node ID): {target_node_id}")

        # 2. Tarik Data Rute dari tb_routes
        cursor.execute("SELECT * FROM tb_routes WHERE origin_node_id = ?", (target_node_id,))
        rute_data = cursor.fetchone()
        
        if not rute_data:
            print(f"[ERROR] Rute untuk Node {target_node_id} tidak ditemukan.")
            return

        # Unpack data rute
        (orig_id, 
         r1_tes, r1_path_str, r1_eta, 
         r2_tes, r2_path_str, r2_eta, 
         r3_tes, r3_path_str, r3_eta) = rute_data

        # Fungsi Helper untuk menerjemahkan deretan Node ID menjadi daftar (Lat, Lon)
        def get_koordinat_jalur(path_str):
            node_ids = path_str.split(',')
            koordinat_list = []
            for nid in node_ids:
                cursor.execute("SELECT lat, lon FROM tb_nodes WHERE node_id = ?", (nid,))
                baris = cursor.fetchone()
                if baris:
                    koordinat_list.append((baris[0], baris[1]))
            return koordinat_list

        # Fungsi Helper untuk mendapatkan koordinat TES
        def get_koordinat_tes(nama_tes):
            cursor.execute("SELECT lat, lon, nama_tes FROM tb_tes WHERE nama_tes = ?", (nama_tes,))
            return cursor.fetchone()

        # Tarik koordinat untuk menggambar garis
        print("[...] Menerjemahkan Node ID ke Titik Koordinat (GPS)...")
        jalur_utama = get_koordinat_jalur(r1_path_str)
        jalur_alt1 = get_koordinat_jalur(r2_path_str)
        jalur_alt2 = get_koordinat_jalur(r3_path_str)

        if not jalur_utama:
            print("[ERROR] Gagal mendapatkan koordinat jalur.")
            return

        koordinat_awal = jalur_utama[0]

        # Ambil koordinat presisi titik tujuan TES
        tes_utama = get_koordinat_tes(r1_tes)
        tes_alt1 = get_koordinat_tes(r2_tes)
        tes_alt2 = get_koordinat_tes(r3_tes)

        # Sambungkan garis rute langsung ke titik lokasi pin bendera TES
        if tes_utama and jalur_utama:
            jalur_utama.append((tes_utama[0], tes_utama[1]))
        if tes_alt1 and jalur_alt1:
            jalur_alt1.append((tes_alt1[0], tes_alt1[1]))
        if tes_alt2 and jalur_alt2:
            jalur_alt2.append((tes_alt2[0], tes_alt2[1]))

        # 3. Inisialisasi Peta Folium
        peta = folium.Map(location=koordinat_awal, zoom_start=15, tiles="CartoDB positron")

        # 4. Tambahkan Marker Posisi Pengguna (Titik Awal)
        folium.Marker(
            location=koordinat_awal,
            popup="<b>Posisi Anda Saat Ini</b>",
            icon=folium.Icon(color="red", icon="user")
        ).add_to(peta)

        # 5. Gambar Rute Utama (Hijau - Aman & Tercepat)
        folium.PolyLine(
            locations=jalur_utama,
            color="green",
            weight=6,
            opacity=0.8,
            tooltip=f"RUTE UTAMA: {r1_tes} (ETA: {r1_eta:.1f} mnt)"
        ).add_to(peta)
        
        if tes_utama:
            folium.Marker(
                location=(tes_utama[0], tes_utama[1]),
                popup=f"<b>{tes_utama[2]}</b><br>Rute Utama (ETA: {r1_eta:.1f} mnt)",
                icon=folium.Icon(color="green", icon="flag")
            ).add_to(peta)

        # 6. Gambar Rute Alternatif 1 (Kuning/Orange - Jika TES Utama Penuh)
        if r2_path_str != r1_path_str:
            folium.PolyLine(
                locations=jalur_alt1,
                color="orange",
                weight=4,
                opacity=0.7,
                dash_array='10, 10',
                tooltip=f"ALTERNATIF 1: {r2_tes} (ETA: {r2_eta:.1f} mnt)"
            ).add_to(peta)
            
            if tes_alt1:
                folium.Marker(
                    location=(tes_alt1[0], tes_alt1[1]),
                    popup=f"<b>{tes_alt1[2]}</b><br>Alternatif 1 (ETA: {r2_eta:.1f} mnt)",
                    icon=folium.Icon(color="orange", icon="flag")
                ).add_to(peta)

        # 7. Gambar Rute Alternatif 2 (Biru)
        if r3_path_str != r1_path_str and r3_path_str != r2_path_str:
            folium.PolyLine(
                locations=jalur_alt2,
                color="blue",
                weight=3,
                opacity=0.6,
                dash_array='5, 5',
                tooltip=f"ALTERNATIF 2: {r3_tes} (ETA: {r3_eta:.1f} mnt)"
            ).add_to(peta)
            
            tes_alt2 = get_koordinat_tes(r3_tes)
            if tes_alt2:
                folium.Marker(
                    location=(tes_alt2[0], tes_alt2[1]),
                    popup=f"<b>{tes_alt2[2]}</b><br>Alternatif 2 (ETA: {r3_eta:.1f} mnt)",
                    icon=folium.Icon(color="blue", icon="flag")
                ).add_to(peta)

        # 8. Simpan dan Buka di Browser
        nama_file_output = "peta_simulasi_android.html"
        peta.save(nama_file_output)
        print(f"[SUKSES] Peta berhasil dibuat! Menyimpan ke '{nama_file_output}'...")
        
        # Buka otomatis di browser bawaan
        filepath = "file://" + os.path.realpath(nama_file_output)
        webbrowser.open(filepath)

    except Exception as e:
        print(f"[ERROR] TERJADI KESALAHAN: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    visualisasi_rute_dari_db()