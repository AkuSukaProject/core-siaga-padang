import pandas as pd

def ekstrak_data_tes_lengkap(file_path):
    print("Membaca berkas Excel master...")
    # Membaca file excel tanpa header default agar struktur baris dan sel gabungan terbaca utuh
    df = pd.read_excel(file_path, header=None)
    
    current_sektor = None
    current_zona = None
    current_luas = None
    current_jiwa = None
    
    extracted_data = []
    
    # Data dimulai dari baris indeks ke-4 (setelah header tabel master)
    for idx in range(4, len(df)):
        row = df.iloc[idx]
        
        # Lewati baris kosong jika seluruh kolom utama bernilai NaN
        if pd.isna(row[0]) and pd.isna(row[2]) and pd.isna(row[6]) and pd.isna(row[7]):
            continue
            
        # Perbarui Sektor jika ada nilai baru di kolom 0
        if pd.notna(row[0]):
            current_sektor = str(row[0]).strip()
            
        # Perbarui Zona, Luas, dan Jumlah Jiwa jika ada nilai baru di kolom 2
        if pd.notna(row[2]):
            current_zona = str(row[2]).strip()
            current_luas = row[3]
            current_jiwa = row[4]
            
        tes_nomor = row[6]
        tes_lokasi = row[7]
        tes_kapasitas = row[8]
        
        # Penanganan khusus jika nomor/keterangan bertuliskan 'LANGSUNG MENUJU TEA'
        if pd.notna(tes_nomor) and "LANGSUNG MENUJU TEA" in str(tes_nomor):
            tes_lokasi = "LANGSUNG MENUJU TEA"
            
        # Membuat kolom Nama_Bersih (membuang keterangan tambahan seperti '(Bangunan yang diusulkan)')
        if pd.notna(tes_lokasi):
            nama_bersih = str(tes_lokasi).split('(')[0].strip()
        else:
            nama_bersih = None
            
        extracted_data.append({
            'Sektor': current_sektor,
            'Zona': current_zona,
            'Luas_Ha': current_luas,
            'Jumlah_Jiwa': current_jiwa,
            'Nomor_TES': tes_nomor,
            'Lokasi_TES': tes_lokasi,
            'Kapasitas_TES': tes_kapasitas,
            'Nama_Bersih': nama_bersih
        })
        
    df_result = pd.DataFrame(extracted_data)
    return df_result

if __name__ == "__main__":
    excel_filename = "LAMP 1 - TABEL IDENTIFIKASI KETERSEDIAAN DAN KEBUTUHAN FASILITAS EVAKUASI TINGKAT ZONA KOTA PADANG (CETAK).xlsx"
    
    # Eksekusi fungsi
    df_tes = ekstrak_data_tes_lengkap(excel_filename)
    
    print("\n--- 10 Baris Pertama Hasil Ekstraksi ---")
    print(df_tes.dropna(subset=['Lokasi_TES']).head(10))
    
    # Menyimpan hasil ke file CSV baru
    output_csv = "data_tes_lengkap_padang.csv"
    df_tes.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"\n[SUKSES] Seluruh data berhasil diekstrak dan disimpan ke '{output_csv}' (Total baris: {len(df_tes)})")