import pdfplumber
import pandas as pd

# 1. Definisi Nama File (Pastikan nama file PDF-nya sesuai dengan yang ingin diekstrak)
nama_file_pdf = "LAMP 2 - PETA JALUR EVAKUASI & TABEL IDENTIFIKASI KOTA PADANG.pdf"
nama_file_excel = "Data_Shelter_Jalur_Evakuasi.xlsx"
nama_file_csv = "Data_Shelter_Jalur_Evakuasi.csv"

# Wadah penampung seluruh baris dari semua tabel
semua_baris = []

print(f"Membuka dokumen: {nama_file_pdf}...")

# 2. Proses Ekstraksi Semua Tabel
with pdfplumber.open(nama_file_pdf) as pdf:
    total_halaman = len(pdf.pages)
    
    for i, halaman in enumerate(pdf.pages):
        print(f"Memindai halaman {i + 1} dari {total_halaman}...")
        
        # Menggunakan extract_tables() (Jamak) untuk mengambil semua tabel di halaman
        tabel_tabel = halaman.extract_tables()
        
        for tabel in tabel_tabel:
            for baris in tabel:
                semua_baris.append(baris)

# 3. Proses Filter dan Pembersihan Data (Logika Baru)
if semua_baris:
    # A. Mencari jumlah kolom terbanyak (Tabel utama pasti paling panjang)
    # Ini menghindari error jika ada baris kosong (None)
    max_kolom = max(len(baris) for baris in semua_baris if baris is not None)
    print(f"\nTarget jumlah kolom utama terdeteksi: {max_kolom} kolom.")

    # B. Menyaring data: Hanya ambil baris yang jumlah kolomnya persis sama dengan max_kolom
    baris_bersih = [baris for baris in semua_baris if baris is not None and len(baris) == max_kolom]

    if baris_bersih:
        print("Membangun DataFrame Pandas...")
        
        # Baris pertama dari data yang sudah disaring dijadikan Judul Kolom (Header)
        df = pd.DataFrame(baris_bersih[1:], columns=baris_bersih[0])
        
        # Membersihkan karakter enter/newline (\n) yang merusak format
        df = df.replace('\n', ' ', regex=True)
        
        # 4. Menyimpan Hasil
        df.to_csv(nama_file_csv, index=False)
        df.to_excel(nama_file_excel, index=False)
        
        print("-" * 40)
        print("EKSTRAKSI BERHASIL BOS!")
        print(f"Data tersimpan dengan rapi di: {nama_file_excel}")
        print("-" * 40)
    else:
        print("Gagal: Tidak dapat menyaring tabel utama.")
else:
    print("Gagal: Tidak ada tabel yang terdeteksi di dokumen PDF.")