import sqlite3
import random

def simulasi_pencarian_android(db_name="ranah_siaga.db", target_node_id=None):
    print("="*70)
    print("🧭 SIMULASI PENCARIAN RUTE APLIKASI ANDROID")
    print("="*70)

    try:
        # Buka koneksi ke SQLite
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # 1. Simulasi GPS: Jika tidak ada node yang dipilih, ambil satu node secara acak
        if target_node_id is None:
            cursor.execute("SELECT origin_node_id FROM tb_routes ORDER BY RANDOM() LIMIT 1")
            result = cursor.fetchone()
            if not result:
                print("❌ ERROR: Tabel tb_routes kosong!")
                return
            target_node_id = result[0]

        print(f"📱 Sinyal GPS Diterima -> Mapping ke Node ID: {target_node_id}")

        # 2. Kueri Pengambilan Rute (Persis seperti DAO di Room Database Android)
        query = """
            SELECT 
                rank_1_tes, rank_1_eta, rank_1_path,
                rank_2_tes, rank_2_eta, rank_2_path,
                rank_3_tes, rank_3_eta, rank_3_path
            FROM tb_routes 
            WHERE origin_node_id = ?
        """
        
        import time
        start_time = time.time()
        
        cursor.execute(query, (target_node_id,))
        rute = cursor.fetchone()
        
        waktu_kueri = (time.time() - start_time) * 1000 # dalam milidetik

        # 3. Menampilkan Hasil (Parsing Data)
        if rute:
            r1_tes, r1_eta, r1_path, r2_tes, r2_eta, r2_path, r3_tes, r3_eta, r3_path = rute
            
            print(f"⚡ Waktu Pencarian Data (Query Time) : {waktu_kueri:.4f} milidetik\n")
            
            print("🟢 RUTE UTAMA (Jika Kapasitas Aman):")
            print(f"   - Tujuan TES : Zona {r1_tes}")
            print(f"   - Waktu Tiba : {r1_eta:.2f} menit")
            # Menghitung jumlah belokan/titik dengan memecah string path berdasarkan koma
            titik_path = r1_path.split(',')
            print(f"   - Jml Titik  : {len(titik_path)} titik persimpangan")
            print(f"   - Jalur (5 Node Pertama) : {','.join(titik_path[:5])} ...\n")
            
            print("🟡 ALTERNATIF 1 (Jika Rute Utama Dinyatakan Penuh oleh BPBD):")
            print(f"   - Tujuan TES : Zona {r2_tes}")
            print(f"   - Waktu Tiba : {r2_eta:.2f} menit\n")
            
            print("🟠 ALTERNATIF 2 (Skenario Terburuk):")
            print(f"   - Tujuan TES : Zona {r3_tes}")
            print(f"   - Waktu Tiba : {r3_eta:.2f} menit")

        else:
            print(f"❌ Rute untuk Node ID {target_node_id} tidak ditemukan di database.")

        conn.close()
        print("\n" + "="*70)

    except Exception as e:
        print(f"❌ TERJADI KESALAHAN: {e}")

if __name__ == "__main__":
    # Anda bisa memasukkan ID Node spesifik di sini, misalnya: simulasi_pencarian_android(target_node_id=12345)
    # Jika dibiarkan kosong, skrip akan mengacak posisi pengguna.
    simulasi_pencarian_android()