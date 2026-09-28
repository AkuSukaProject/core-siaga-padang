# Spatial Pipeline - Siaga Padang Final

## Penjelasan Metodologi

### 1. Kapasitas Riil TES
Nilai kapasitas di tabel DB versi 2 didominasi angka default (300) atau populasi zona keseluruhan yang diambil dari tabel rekomendasi. Pada rilis ini (`ranah_siaga_v3.db`), kapasitas sungguhan dihitung ulang menggunakan estimasi footprint bangunan dari OSM di sekitar titik shelter, lalu dihitung menggunakan standar **FEMA P-646 (2012)**:
`Kapasitas = (Luas Lantai Total) / 0.93 m^2 per orang`
Karena data elevasi/jumlah lantai tidak ada di dataset awal, diasumsikan TES (rata-rata sekolah/masjid besar) memiliki 3 lantai. Jika data footprint OSM gagal ditarik, digunakan estimasi heuristik kasar dari kapasitas sebelumnya untuk mengisi nilai luas dasar minimal 500m^2.

### 2. Distribusi Penduduk per Simpul (Demand)
Penduduk dari kelurahan rawan (ditarik dari `penduduk_kota_padang.csv`) didistribusikan secara proporsional ke semua simpul jalan raya (nodes) dalam batas poligon kelurahan tersebut yang berstatus `is_safe = 0`. Cara pembagian:
`Demand per node = Total Penduduk Terpapar Kelurahan / Jumlah Simpul (is_safe=0) di Kelurahan tersebut`.

### 3. Simulasi Penugasan (Opsi A) dan Porsi
Algoritma Greedy Assignment digunakan untuk mendistribusikan warga secara bertahap dari semua sumber dengan urutan berbasis ETA tercepat:
1. Hanya TES/TEA/Zona Aman dalam radius ETA <= 20 menit yang dianggap layak (feasible).
2. Jika TES penuh, sisa warga di simpul tersebut dialihkan ke tujuan selanjutnya (TES rank 2, TEA, atau Zona Aman).
3. Tabel `tb_route_shares` mencatat pecahan probabilitas (porsi) tujuan akhir untuk setiap asal (contoh: 0.7 ke TES_A, 0.3 ke TEA_B).

### 4. Pengecilan Ukuran Database (Target <= 75 MB)
Sesuai persyaratan, ukuran database diperkecil menggunakan:
- Penghapusan kolom redundant dari tabel `tb_tea_routes` (harus dikonfirmasi ke Sheva bahwa kolom ini memang tidak dipakai Backend).
- Pembulatan koordinat pada WKT `tb_inundation_zones` dan `tb_safe_zones` menjadi 6 angka di belakang koma, serta penghapusan nilai Z (Elevasi) yang tidak digunakan oleh renderer 2D.
- Proses `VACUUM` pada SQLite.

### 5. Rujukan Asumsi Simulasi Agen (Opsi C)
Saat memodelkan dinamika evakuasi:
- **Kecepatan Rentan/Lansia:** Beragam hingga 0.91 m/s merujuk pada standar FEMA P-646.
- **Waktu Tunda (Departure Delay):** Waktu respons diasumsikan 10-15 menit sesuai paper Lindell & Prater (2007) terkait pemodelan Evacuation Time Estimate.
- **Efek Kepadatan (Congestion):** Merujuk Fundamental Diagram Pedestrian dari Fruin (1971) atau Weidmann (1993), kecepatan pejalan kaki akan turun drastis (melambat) ketika kepadatan > 1.2 orang/m^2.

## Cara Menjalankan
1. Pastikan Anda berada di direktori `c:\gemastik\spatial`.
2. Aktifkan virtual environment (`..\env\Scripts\activate`).
3. Jalankan `run_all.bat` (atau jalankan satu per satu).
4. Hasil keluaran adalah file `ranah_siaga_v3.db` di folder root (`c:\gemastik`).

## Checksum / Manifest
Setelah skrip selesai, hitung SHA256 dari `ranah_siaga_v3.db` dan sesuaikan `dataset_manifest.json` sebelum diserahkan ke tim Backend/Android.
