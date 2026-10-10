import sqlite3
import pandas as pd

def uji_database(nama_file="ranah_siaga.db"):
    print("="*70)
    print(f"🔍 MEMULAI PENGUJIAN DATABASE: {nama_file}")
    print("="*70)

    try:
        # 1. Membuka Koneksi
        conn = sqlite3.connect(nama_file)

        # 2. Memeriksa Daftar Tabel
        query_tabel = "SELECT name FROM sqlite_master WHERE type='table';"
        df_tabel = pd.read_sql_query(query_tabel, conn)
        print("\n📌 1. DAFTAR TABEL DI DALAM DATABASE:")
        if df_tabel.empty:
            print("   [PERINGATAN] Tidak ada tabel ditemukan!")
            return
        print(df_tabel.to_string(index=False))

        # 3. Memeriksa Jumlah Baris Data
        print("\n📌 2. JUMLAH DATA PER TABEL:")
        for tabel in df_tabel['name']:
            jml = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {tabel}", conn).iloc[0]['total']
            print(f"   - Tabel '{tabel}': {jml:,} baris")

        # 4. Memeriksa Struktur dan Sampel Data Rute
        print("\n📌 3. SAMPEL DATA RUTE (tb_routes - 1 Baris Pertama):")
        # Mengambil 1 baris sampel untuk memastikan kolom dan isinya benar
        sampel_rute = pd.read_sql_query("SELECT * FROM tb_routes LIMIT 1", conn)
        
        if not sampel_rute.empty:
            # Di-transpose (.T) agar mudah dibaca ke bawah
            print(sampel_rute.T.to_string(header=False))
        else:
            print("   [PERINGATAN] Tabel tb_routes kosong!")

        # Menutup Koneksi
        conn.close()
        print("\n" + "="*70)
        print("✅ PENGUJIAN SELESAI. Jika tidak ada error, Database SIAP DIGUNAKAN!")
        print("="*70)

    except sqlite3.OperationalError as e:
        print(f"\n❌ GAGAL MEMBUKA DATABASE. Pastikan file '{nama_file}' berada di folder yang sama.")
        print(f"   Detail Error: {e}")
    except Exception as e:
        print(f"\n❌ TERJADI KESALAHAN SISTEM: {e}")

if __name__ == "__main__":
    uji_database()