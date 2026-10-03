# Spatial Pipeline - Siaga Padang Final

## Penjelasan Metodologi

### 1. Kapasitas Riil TES
Nilai kapasitas di tabel DB versi 2 didominasi angka default (300) atau populasi zona keseluruhan yang diambil dari tabel rekomendasi. Pada rilis ini (`ranah_siaga_v3.db`), kapasitas sungguhan dihitung ulang menggunakan estimasi footprint bangunan dari OSM di sekitar titik shelter, lalu dihitung menggunakan standar **FEMA P-646 (2012)**:
`Kapasitas = (Luas Lantai Total) / 0.93 m^2 per orang`
Karena data elevasi/jumlah lantai tidak ada di dataset awal, diasumsikan TES (rata-rata sekolah/masjid besar) memiliki 3 lantai. Jika data footprint OSM gagal ditarik, digunakan estimasi heuristik kasar dari kapasitas sebelumnya untuk mengisi nilai luas dasar minimal 500m^2.

> **Catatan (28 Sep 2026):** kode `1_update_capacity.py` saat ini belum menarik footprint OSM. `luas_bangunan_m2` selalu 0 lalu diisi heuristik (600 m² bila kapasitas lama 300, selain itu `min(kapasitas lama × 0,5, 3000)`). Angka hasilnya bukan kapasitas riil. Karena itu langkah 1 dan 3 tidak ikut dalam DB rilis aplikasi (lihat "DB Rilis Aplikasi") sampai daya tampung dari SK BPBD atau footprint sungguhan tersedia.

### 1b. Rute ke Kawasan Aman (`2_safe_zone_routes.py`)
Dijkstra multisumber (graf dari `tb_edges` di DB) menuju simpul tujuan kawasan aman, disimpan dengan pola yang sama dengan TEA:
- `tb_safe_routes(origin_node_id, safe_node_id, safe_zone_id, safe_eta)`: `safe_eta` dalam menit (1,2 m/s), `safe_zone_id` merujuk ke `tb_safe_zones`.
- `tb_safe_next(node_id, next_node_id)`: satu langkah berikutnya menuju tujuan.

Aturan tujuan:
- Simpul `is_safe = 1` di kelurahan kawasan aman yang **jiwa terpaparnya 0** menurut tabel KRB BPBD (`penduduk_kota_padang.csv`). Kelurahan dari daftar pengecualian manual `core.py` (Pasar Ambacang 3.508 jiwa, Kalumbuk 1.885, Bungus Barat 1.295, dst.) tidak menjadi tujuan, karena letak warga terpaparnya di dalam kelurahan tidak diketahui. Ambang dapat diubah dengan `--ambang-jiwa-terpapar` setelah konfirmasi BPBD.
- Skrip berhenti bila ada simpul `is_safe = 1` di dalam poligon zona rendaman. DB 2026.09.26 lama (SHA `b29422ac…`) punya 5.616 simpul seperti itu karena bug kunci str/int di `core.py` (sudah diperbaiki). DB `ranah_siaga_v2.db` terbaru sudah cocok.
- Verifikasi otomatis: setiap rantai berakhir di simpul tujuan tanpa putaran, dan panjangnya sama dengan jarak Dijkstra.

Hasil pada `ranah_siaga_v2.db`: 8.228 simpul tujuan; semua 19.784 simpul berisiko punya rute (median 48,4 menit, 16,3% dalam 20 menit). Simpul berisiko yang tidak punya tujuan mana pun dalam 20 menit (TES, TEA, atau kawasan aman) turun dari 4.604 menjadi 3.409.

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
- Penghapusan kolom redundant dari tabel `tb_tea_routes`. Aplikasi hanya membaca `origin_node_id`, `nearest_tea_id`, `alt_tea_id`; kode backend tidak membaca tabel ini.
- Penulisan ulang WKT `tb_inundation_zones` dan `tb_safe_zones` sebagai 2D dengan **7** angka di belakang koma (± 1 cm). Nilai Z benar-benar dibuang (sebelumnya hanya label " Z" yang hilang, angka ketiga tetap ada). Dengan 6 desimal, tiga simpul yang berjarak < 1 cm dari batas kelurahan berpindah kelurahan; skrip kini memeriksa bahwa keanggotaan setiap simpul tidak berubah.
- Proses `VACUUM` pada SQLite.

## DB Rilis Aplikasi (`rilis_aplikasi.bat`)
`ranah_siaga_v2.db` → langkah 2 → langkah 4 → `ranah_siaga_rilis.db` (tidak masuk Git, distribusi lewat Drive). Hasil 28 Sep 2026: 74.407.936 byte (74,41 MB desimal, memenuhi NF-03), SHA-256 `b14e687b9ffdd6313fcc2f6b45341caae9ceda5b4143828346804e1d5f53cb88`. Pembuatannya deterministik: dijalankan ulang menghasilkan SHA yang sama.

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
