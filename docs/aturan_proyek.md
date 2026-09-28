# Aturan & Konvensi Proyek

Untuk memastikan lingkungan pengembangan yang terstandar, dapat direproduksi (*reproducible*), dan bersih, semua modifikasi serta kontribusi pada repositori ini harus mematuhi aturan-aturan berikut:

## 1. Konvensi Kode dan Penamaan File

*   **Prefix Eksperimen**: Semua skrip eksperimen atau uji coba sementara yang tidak terkait dengan keluaran produksi (Tabel 6.4 atau build `.db`) harus ditempatkan di direktori `scratch/`.
*   **Kejelasan Eksekusi**: File generator (seperti pembuatan peta atau ekstraksi data) harus menggunakan awalan deskriptif (contoh: `buat_peta_...`, `generate_...`, `ekstrak_...`).
*   **Encoding Teks**: Setiap pengolahan *String* atau akses standar *output/print* direkomendasikan mengonfigurasi encoding UTF-8 di awal skrip (`sys.stdout.reconfigure(encoding='utf-8')`) mengingat data lapangan di Indonesia banyak menggunakan karakter spasial khusus atau tanda baca lokal.

## 2. Aturan Data & Pembersihan

*   **Pembersihan Numerik Otomatis**: Data dari CSV/Excel resmi pemerintah sering kali mengandung notasi yang tidak konsisten (misal: "3000 Jiwa", "1.500", atau angka dalam list Python jika terpotong). Selalu gunakan fungsi pembersih *string-to-float* tahan banting (seperti fungsi `bersihkan_angka_osm()` atau `parse_kapasitas()`) sebelum komputasi matematis.
*   **Pemisah Desimal**: Data lokal cenderung menggunakan tanda koma (`,`) sebagai pemisah desimal koordinat/kapasitas. Penguraian *string* menjadi *float* harus menangani substitusi `,` ke `.` terlebih dahulu.
*   **Validasi Koordinat**: Koordinat yang bernilai 0.0, bernilai *NaN*, atau tidak rasional (berada jauh dari ekuator/wilayah Sumatera Barat) harus difilter secara langsung (dijatuhkan/di-*drop* dari *Dataframe*).

## 3. Reproduktibilitas Ilmiah

Karena proyek ini menghasilkan data evaluasi fisik untuk pengajuan riset akademik / kompetisi (Tabel 6.4 Proposal), ketegasan ilmiah adalah suatu keharusan:
*   **Fix Random Seed**: Semua proses pemilihan sampel (*random sampling* agen populasi demografi) harus menetapkan seed statis (misal `np.random.seed(42)`). Jika di-run 100 kali, harus keluar 100 hasil simulasi yang persis sama.
*   **Parameter Tidak Boleh Hard-Coded Asal-asalan**: Jauhi penggunaan *magic numbers*. Setiap konstanta kecepatan, konversi EPSG, batas waktu evakuasi harus dideklarasikan sebagai variabel global konfigurasi di bagian atas *script* dan diberikan anotasi rujukan asalnya (misal: `"Kecepatan jalan standar BNPB = 1.2 m/s"`).
*   **Hindari Duplikasi Skrip Engine Inti**: Bila ada perubahan logika distribusi agen ke TES, pastikan logika kanonisnya diperbaiki secara *upstream* di `core.py` dan disinkronkan ke `simulasi_resmi_padang.py`, bukan dengan membuat variasi duplikat `core_v7.py` di dalam *root directory*.
