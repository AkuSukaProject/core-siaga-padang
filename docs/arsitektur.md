# Arsitektur Sistem & Database Siaga Padang

Dokumen ini menjelaskan struktur arsitektur pemrosesan data (backend/routing engine) dan skema basis data SQLite yang menjadi jembatan antara data spasial mentah dan aplikasi Android klien.

## Alur Arsitektur Spasial (Routing Engine)

Proses pencarian rute evakuasi di backend (`core.py`) beroperasi secara pra-komputasi (*pre-computed offline routing*):

1. **Graf Jaringan Jalan (NetworkX)**
   Jaringan jalan Kota Padang dimodelkan sebagai graf tak berarah (*undirected graph*) menggunakan format GraphML (`padang_full.graphml`). Bobot utama pada *edges* (ruas jalan) adalah estimasi waktu tempuh pejalan kaki `t0 = jarak_meter / (1.2 * 60)` dalam satuan menit.

2. **Standardisasi Koordinat Spasial**
   Banyak data spasial mentah menggunakan proyeksi meter (seperti `EPSG:32747`). Sistem secara mandiri (*auto-fix*) akan mentransformasikan koordinat tersebut menjadi proyeksi derajat Lintang/Bujur standar WGS84 (`EPSG:4326`) sebelum disimpan ke database, menggunakan pustaka `pyproj`.

3. **Algoritma Reverse Dijkstra**
   Alih-alih mencari rute dari ribuan warga ke puluhan gedung TES (*Tempat Evakuasi Sementara*), sistem menggunakan **Reverse Dijkstra**. Pencarian rute (*shortest path*) diinisiasi *dari* setiap node lokasi TES *menuju* seluruh node persimpangan jalan secara simultan.

4. **Kd-Tree Snapping**
   Pencocokan lokasi koordinat riil TES (dari Excel/CSV) ke node (persimpangan) terdekat di graf dilakukan menggunakan algoritma `cKDTree` dari SciPy, dengan konversi euclidean derajat ke meter.

## Skema Database Hybrid (`ranah_siaga.db`)

Untuk menghindari aplikasi seluler melakukan komputasi Dijkstra yang berat, *engine* ini mengekspor seluruh hasil pre-komputasi ke sebuah basis data SQLite lokal bernama `ranah_siaga.db`. Skema utamanya meliputi:

* **`tb_nodes`**
  Menyimpan seluruh node persimpangan jalan beserta koordinat Lintang/Bujur (`lat`, `lon`), dan flag keamanan (`is_safe` = 1 untuk zona tinggi/aman, 0 untuk zona rawan).

* **`tb_edges`**
  Menyimpan garis ruas jalan, merelasikan persimpangan asal (`u`) dan tujuan (`v`), panjang aktual, serta menyimpan koordinat poliline geometri (WKT LineString) untuk keperluan *rendering* lengkung jalan visual di Android.

* **`tb_tes`**
  Master data Tempat Evakuasi Sementara (TES). Berisi Nama Gedung, lokasi kelurahan, kapasitas riil BPBD, serta koordinat Lintang dan Bujur.

* **`tb_routes`**
  Tabel ini merupakan hasil pra-komputasi utama. Menampung relasi 1:1 dari `tb_nodes` (sebagai titik asal warga) ke **tiga peringkat rekomendasi rute TES sekaligus** (`rank_1`, `rank_2`, `rank_3`). Berisi nama TES tujuan, waktu tempuh (ETA), dan deretan node pembentuk rute.

* **`tb_inundation_zones` & `tb_safe_zones`**
  Menampung batas poligon WKT (Geometri) kelurahan/daerah yang dinyatakan rawan banjir rob/tsunami (Inundation) serta daerah perbukitan yang aman (Safe Zones). Digunakan Android untuk *spatial checking* posisi awal user.
