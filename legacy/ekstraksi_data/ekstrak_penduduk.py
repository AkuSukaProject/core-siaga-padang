import pandas as pd

print("=" * 60)
print("EKSTRAKSI DATA PENDUDUK TERPAPAR TSUNAMI (BPBD) - KOTA PADANG")
print("=" * 60)

# 1. Menentukan nama file sumber
file_path = "LAMP 2 - TABEL KAJIAN RISIKO BENCANA TSUNAMI KOTA PADANG.xlsx"
print(f"Membaca file: {file_path}...")

try:
    # 2. Membaca Sheet 'TSUNAMI'
    # skiprows=2 untuk melewati judul kop tabel instansi
    df = pd.read_excel(file_path, sheet_name='TSUNAMI', skiprows=2)
    
    # 3. Filtering Data (Membuang Baris Kosong & Total)
    # Menghapus baris yang kolom Kecamatannya kosong (NaN)
    df = df[df['KECAMATAN'].notna()]
    
    # Menghapus baris rekapitulasi di bawah tabel (yang biasanya bertuliskan "JUMLAH" atau "TOTAL")
    # agar tidak terjadi penggandaan (double count) pada total populasi.
    df = df[~df['KECAMATAN'].astype(str).str.contains("JUMLAH|TOTAL", case=False, na=False)]
    
    # 4. Seleksi Kolom yang Relevan
    # Menambahkan kolom 'KECAMATAN' agar data CSV lebih terstruktur dan mudah dicek
    df_final = df[['KECAMATAN', 'DESA', 'JUMLAH JIWA TERPAPAR (JIWA)']].copy()
    
    # 5. Pembersihan Data (Handling Anomaly & Missing Values)
    # Mengisi nilai kosong dengan 0 untuk berjaga-jaga
    df_final['JUMLAH JIWA TERPAPAR (JIWA)'] = df_final['JUMLAH JIWA TERPAPAR (JIWA)'].fillna(0)
    
    # Memperbaiki anomali data di kelurahan 'BELAKANG TANGSI' (Asumsi salah ketik dari BPBD)
    for index, row in df_final.iterrows():
        if str(row['DESA']).strip() == 'BELAKANG TANGSI' and row['JUMLAH JIWA TERPAPAR (JIWA)'] > 100000:
            print(">> Peringatan: Memperbaiki anomali ketik pada data Belakang Tangsi...")
            df_final.at[index, 'JUMLAH JIWA TERPAPAR (JIWA)'] = 12492.09
            
    # Mengubah format angka menjadi bilangan bulat (integer)
    df_final['JUMLAH JIWA TERPAPAR (JIWA)'] = df_final['JUMLAH JIWA TERPAPAR (JIWA)'].astype(int)
    
    # 6. Menampilkan Hasil
    print("\nData Penduduk Terpapar - Seluruh Kota Padang:")
    print("-" * 60)
    # Hanya menampilkan 15 baris pertama agar terminal tidak penuh
    print(df_final.head(15).to_string(index=False)) 
    print("... (dan kelurahan lainnya)")
    
    total_jiwa = df_final['JUMLAH JIWA TERPAPAR (JIWA)'].sum()
    print("-" * 60)
    print(f"Total Kelurahan/Desa Terpapar : {len(df_final)} wilayah")
    print(f"Total Penduduk Terpapar       : {total_jiwa:,} Jiwa")
    
    # 7. Ekspor ke CSV untuk dimasukkan ke dalam core.py
    file_output = "penduduk_kota_padang.csv"
    df_final.to_csv(file_output, index=False)
    print(f"\n✅ Berhasil! Data skala kota telah diekspor ke '{file_output}'.")

except FileNotFoundError:
    print(f"ERROR: File Excel '{file_path}' tidak ditemukan. Pastikan namanya sama persis.")
except Exception as e:
    print(f"ERROR Tidak Terduga: {e}")