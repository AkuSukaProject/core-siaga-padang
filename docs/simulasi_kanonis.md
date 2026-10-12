# Simulasi Kanonis (Canonical Simulation)

Dalam proyek **Siaga Padang**, simulasi kanonis merujuk pada **skrip simulasi rujukan resmi (*single source of truth*)** yang digunakan untuk menghasilkan metrik evaluasi yang definitif, berulang (*reproducible*), dan diakui secara akademik (misal, untuk Tabel 6.4 pada proposal/laporan).

## Dua Skrip Kanonis Utama

### 1. `analisis/simulasi_resmi_padang.py` (Simulasi Evaluasi)
Membandingkan skenario Baseline dan Siaga Padang dengan agen yang sama.
* **Masukan**: hanya `ranah_siaga_v4.db`, sehingga simulasi memakai fasilitas, demand penduduk, dan rute yang persis sama dengan aplikasi.
* **Sifat**: deterministik (seed `42`). Dua kali dijalankan menghasilkan berkas keluaran yang identik.
* **Keluaran** (`analisis/output/`): peta berdampingan, beban per fasilitas, dan tingkat keselamatan per kelurahan.
* **Waktu jalan**: < 1 detik.

### 2. Pembangun Database (`build_db.py`)
Menghasilkan `ranah_siaga_v4.db` dari data BPBD (rincian: [build_db_v4.md](build_db_v4.md)). Skrip ini juga menghitung cakupan berbasis penugasan per jiwa (71,6% jiwa punya tujuan ≤ 20 menit), yang menjadi pembanding silang hasil simulasi agen (72,2%).

## Parameter Resmi Simulasi

Sumber: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md).

| Parameter | Nilai |
|---|---|
| Kecepatan berjalan | **0,894 m/s** (orang terlemah, FEMA P-646), dibaca dari `tb_metadata`. Kolom ETA di DB (1,2 m/s, kontrak) dikonversi ke 0,894 m/s. 1,2 m/s hanya sebagai pembanding. |
| Batas waktu | **20 menit** (skenario terburuk BPBD) |
| Agen | **20.000**, dibangkitkan proporsional terhadap `tb_node_info.demand_jiwa` (242.750 jiwa terpapar KRB 2023–2027; 1 agen ≈ 12,14 jiwa). Semua agen berasal dari zona merah. |
| Fasilitas | 244 TES dan 25 TEA yang dipakai routing (`tb_fasilitas_info.dipakai = 1`) |
| Kapasitas | Kapasitas TES diskalakan ke jumlah agen (dibulatkan, minimal 1). Tanpa toleransi berdesakan. TEA dan zona aman tidak dibatasi. |

## Skenario

| | A. Baseline | B. Siaga Padang |
|---|---|---|
| Perilaku | Warga tanpa aplikasi berjalan ke TES/TEA **terdekat menurut jarak jalan murni** | Warga mengikuti rekomendasi database |
| Aturan arah & jembatan | Tidak | Ya (sudah tertanam di rute DB: tujuan menjauh > 15°, jembatan ≥ 20 m hanya cadangan) |
| Kandidat tujuan | 1 fasilitas terdekat | TES rank 1–3, TEA utama & alternatif, zona aman dari `tb_safe_routes_v2` (pembanding: tabel kontrak lama `tb_safe_routes`, opsi `--rute-aman kontrak`). Urutan: di antara yang sempat ≤ 20 menit, yang paling jauh dari pantai lebih dulu; yang tidak sempat menyusul menurut ETA |
| Kapasitas | Diabaikan saat memilih; yang datang setelah TES penuh tidak tertampung | TES penuh dilewati, agen pindah ke kandidat berikutnya |
| Urutan pemrosesan | Menurut ETA (yang lebih cepat masuk lebih dulu) | Menurut ETA kandidat pertama |

**Kriteria selamat**: tiba ≤ 20 menit **dan** tertampung. Untuk TES berarti belum penuh saat agen tiba; TEA dan zona aman selalu menampung.

## Hasil Resmi (12 Oktober 2026, data v4 versi 2026.10.14)

| Metrik | Baseline (terdekat) | Siaga Padang |
| :--- | :--- | :--- |
| TES melebihi kapasitas | **83** dari 244 | **0** dari 244 |
| Tiba ≤ 20 menit (tanpa melihat kapasitas) | 13.542 agen (67,7%) | 14.441 agen (72,2%) |
| **Selamat: tiba ≤ 20 menit & tertampung** | **7.125 agen (35,6%)** | **14.441 agen (72,2%)** |
| Tiba di TES tapi tidak tertampung | 11.657 agen | 0 |
| Rata-rata waktu tempuh | 18,71 menit | 24,85 menit |
| Rata-rata tambahan waktu karena pengalihan | 0 | 3,17 menit |
| Tujuan TES / TEA / zona aman (agen) | 18.989 / 1.011 / 0 | 3.706 / 315 / 15.979 |
| Pembanding 1,2 m/s: selamat | 36,7% | 78,6% |

### Interpretasi
* **Angka keselamatan semu.** Tanpa memperhatikan kapasitas, 67,8% warga Baseline "tiba tepat waktu", tetapi 83 TES kelebihan beban dan 11.657 agen tidak tertampung. Keselamatan nyata Baseline hanya 35,6%.
* **Siaga Padang menggandakan keselamatan nyata** menjadi 72,2% tanpa satu pun TES kelebihan kapasitas. Sekitar 81% warga diarahkan keluar zona (zona aman/TEA), karena titik zona hijau yang sempat dicapai hampir selalu lebih jauh dari pantai daripada TES di zona merah.
* **Rata-rata waktu tempuh lebih panjang, dan memang disengaja.** Warga yang masih sempat diarahkan ke tujuan terjauh dari pantai yang masih terjangkau ≤ 20 menit, bukan ke tujuan tercepat. Waktu tempuhnya bertambah, tetapi tetap di bawah 20 menit dan posisinya lebih aman.
* **Ada harga dari aturan arah.** Tujuan harus menjauh dari pantai lebih dari 15° (sejajar tidak boleh) dan jembatan ≥ 20 m hanya cadangan. Di 7 dari 56 kelurahan, keselamatan Siaga Padang lebih rendah daripada Baseline: Batang Kabung (0,2% vs 1,1%), Air Tawar Timur (23,1% vs 29,3%), Bungus Selatan (52,3% vs 64,1%), Bungus Barat (68,8% vs 81,5%), Air Manis, Teluk Kabung Selatan, dan Gates Nan XX. Di wilayah ini tujuan terdekat berada di arah laut atau sejajar pantai sehingga tidak boleh direkomendasikan. Selisih itu konsekuensi aturan BPBD; Baseline sendiri melanggar aturan tersebut.
* **Kantong rawan.** Kelurahan dengan keselamatan terendah (Batang Kabung, Pasir Nan Tigo, Padang Sarai, Bungo Pasang di Koto Tangah) adalah kandidat lokasi TES vertikal baru untuk direkomendasikan ke BPBD. Rinciannya di `analisis/output/hasil_simulasi_kelurahan.csv` dan peta celah `hasil_build/peta_celah_kelurahan.csv` (H-7).

### Pembanding: tabel zona aman kontrak lama

Bila aplikasi tetap memakai `tb_safe_routes` (kontrak §2.1 lama: pohon global ke batas zona hijau terdekat; 1.048 simpul merah tanpa baris karena tujuannya tidak lolos syarat arah):

| Metrik Siaga Padang | `tb_safe_routes_v2` (resmi, usulan wajib) | `tb_safe_routes` (kontrak lama) |
| :--- | :--- | :--- |
| Selamat: tiba ≤ 20 menit & tertampung | **72,2%** | 68,9% |
| TES melebihi kapasitas | 0 | 0 |
| Rata-rata waktu tempuh | 24,85 menit | 23,67 menit |
| Tujuan TES / TEA / zona aman (agen) | 3.706 / 315 / 15.979 | 7.425 / 1.390 / 11.185 |
| Pembanding 1,2 m/s: selamat | 78,6% | 75,8% |

Dengan tabel lama, tujuan zona aman berhenti di batas zona hijau yang dekat pantai, sehingga TES/TEA lebih sering terpilih sebagai "yang terjauh", dan warga tanpa baris zona aman harus ke tujuan yang lebih lama. Jalankan: `env\Scripts\python.exe analisis\simulasi_resmi_padang.py --rute-aman kontrak` (keluaran berakhiran `_kontrak`).

Riwayat: DB 2026.10.12 (aturan "tercepat yang lolos syarat", keluar zona didahulukan) menghasilkan 68,8% dengan tabel kontrak dan 70,9% dengan v2.

Catatan: cakupan penugasan di `build_db.py` (71,6% jiwa punya tujuan ≤ 20 menit) memakai aturan dan rute v2 yang sama.

## Batasan Model
* Tidak memodelkan kemacetan pejalan kaki atau antrean tangga (lihat simulasi mikro BPR di `legacy/simulasi/`).
* Tidak memodelkan waktu tunda keberangkatan; ETA dihitung sejak warga mulai berjalan.
* Kapasitas 75 TES masih estimasi (lihat [build_db_v4.md](build_db_v4.md)).
* Baseline mengasumsikan warga tahu fasilitas terdekat; dalam kenyataan sebagian warga tidak tahu sama sekali, sehingga Baseline cenderung optimistis.

## Arsip: Hasil Hibrida V2 (September 2026, data lama)

Dengan data lama (143 TES, 12 TEA, 524.728 jiwa, 1,2 m/s, toleransi berdesakan 10%), hasilnya Baseline 81,0% dan Siaga Padang 53,2%, dengan 84 vs 135 TES "overcapacity". Angka ini **tidak dipakai lagi**: datanya sudah tidak relevan menurut BPBD, dan angka 135 TES adalah artefak karena kuota diberi toleransi +10% sementara pengecekan *overcapacity* tidak. Skrip versi lama tersimpan di riwayat git.
