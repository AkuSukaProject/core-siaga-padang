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
Menghasilkan `ranah_siaga_v4.db` dari data BPBD (rincian: [build_db_v4.md](build_db_v4.md)). Skrip ini juga menghitung cakupan berbasis penugasan per jiwa (71,4% jiwa punya tujuan ≤ 20 menit), yang menjadi pembanding silang hasil simulasi agen (71,3%).

## Parameter Resmi Simulasi

Sumber: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md).

| Parameter | Nilai |
|---|---|
| Kecepatan berjalan | **0,894 m/s** (orang terlemah, FEMA P-646), dibaca dari `tb_metadata`. 1,2 m/s hanya sebagai pembanding. |
| Batas waktu | **20 menit** (skenario terburuk BPBD) |
| Agen | **20.000**, dibangkitkan proporsional terhadap `tb_node_info.demand_jiwa` (242.750 jiwa terpapar KRB 2023–2027; 1 agen ≈ 12,14 jiwa). Semua agen berasal dari zona merah. |
| Fasilitas | 230 TES dan 25 TEA yang dipakai routing (`tb_fasilitas_info.dipakai = 1`) |
| Kapasitas | Kapasitas TES diskalakan ke jumlah agen (dibulatkan, minimal 1). Tanpa toleransi berdesakan. TEA dan zona aman tidak dibatasi. |

## Skenario

| | A. Baseline | B. Siaga Padang |
|---|---|---|
| Perilaku | Warga tanpa aplikasi berjalan ke TES/TEA **terdekat menurut jarak jalan murni** | Warga mengikuti rekomendasi database |
| Aturan pantai & jembatan | Tidak | Ya (sudah tertanam di rute DB) |
| Kandidat tujuan | 1 fasilitas terdekat | TES rank 1–3, TEA utama & alternatif, zona aman (`tb_safe_routes_v2`, selalu lebih jauh dari pantai), diurutkan menurut ETA |
| Kapasitas | Diabaikan saat memilih; yang datang setelah TES penuh tidak tertampung | TES penuh dilewati, agen pindah ke kandidat berikutnya |
| Urutan pemrosesan | Menurut ETA (yang lebih cepat masuk lebih dulu) | Menurut ETA kandidat pertama |

**Kriteria selamat**: tiba ≤ 20 menit **dan** tertampung. Untuk TES berarti belum penuh saat agen tiba; TEA dan zona aman selalu menampung.

## Hasil Resmi (11 Oktober 2026, data v4 versi 2026.10.11)

| Metrik | Baseline (terdekat) | Siaga Padang |
| :--- | :--- | :--- |
| TES melebihi kapasitas | **80** dari 230 | **0** dari 230 |
| Tiba ≤ 20 menit (tanpa melihat kapasitas) | 13.554 agen (67,8%) | 14.258 agen (71,3%) |
| **Selamat: tiba ≤ 20 menit & tertampung** | **6.832 agen (34,2%)** | **14.258 agen (71,3%)** |
| Tiba di TES tapi tidak tertampung | 11.898 agen | 0 |
| Rata-rata waktu tempuh | 18,80 menit | 18,00 menit |
| Rata-rata tambahan waktu karena pengalihan | 0 | 4,28 menit |
| Tujuan TES / TEA / zona aman (agen) | 18.980 / 1.020 / 0 | 4.835 / 356 / 14.809 |
| Pembanding 1,2 m/s: selamat | 35,4% | 79,6% |

### Interpretasi
* **Angka keselamatan semu.** Tanpa memperhatikan kapasitas, 67,8% warga Baseline "tiba tepat waktu", tetapi 80 TES kelebihan beban dan 11.898 agen tidak tertampung. Keselamatan nyata Baseline hanya 34,2%.
* **Siaga Padang menggandakan keselamatan nyata** menjadi 71,3% tanpa satu pun TES kelebihan kapasitas. Sebagian besar warga (±75%) diarahkan keluar ke zona aman terdekat karena itu tujuan tercepat yang tersedia; TES dipakai bila memang lebih cepat dan masih ada tempat.
* **Ada harga dari aturan menjauhi pantai.** Aturan ini sekarang ditegakkan untuk semua tujuan, termasuk zona aman (`tb_safe_routes_v2`). Akibatnya keselamatan turun dari 74,1% (versi yang zona amannya belum disaring) menjadi 71,3%. Di 9 dari 56 kelurahan, keselamatan Siaga Padang lebih rendah daripada Baseline: Batang Kabung (0,3% vs 1,1%), Pasir Nan Tigo (16,1% vs 18,8%), Air Tawar Timur (18,8% vs 29,3%), Bungus Selatan, Bungus Barat, Air Manis, Rawang, Air Tawar Barat, dan Taluak Bayua. Di wilayah ini, tujuan terdekat berada di arah laut sehingga tidak boleh direkomendasikan. Selisih itu adalah konsekuensi aturan BPBD, bukan kesalahan algoritma; Baseline sendiri melanggar aturan tersebut.
* **Kantong rawan.** Kelurahan dengan keselamatan terendah (Batang Kabung, Pasir Nan Tigo, Padang Sarai, Bungo Pasang di Koto Tangah) adalah kandidat lokasi TES vertikal baru untuk direkomendasikan ke BPBD. Rinciannya di `analisis/output/hasil_simulasi_kelurahan.csv`.

## Batasan Model
* Tidak memodelkan kemacetan pejalan kaki atau antrean tangga (lihat simulasi mikro BPR di `legacy/simulasi/`).
* Tidak memodelkan waktu tunda keberangkatan; ETA dihitung sejak warga mulai berjalan.
* Kapasitas 75 TES masih estimasi (lihat [build_db_v4.md](build_db_v4.md)).
* Baseline mengasumsikan warga tahu fasilitas terdekat; dalam kenyataan sebagian warga tidak tahu sama sekali, sehingga Baseline cenderung optimistis.

## Arsip: Hasil Hibrida V2 (September 2026, data lama)

Dengan data lama (143 TES, 12 TEA, 524.728 jiwa, 1,2 m/s, toleransi berdesakan 10%), hasilnya Baseline 81,0% dan Siaga Padang 53,2%, dengan 84 vs 135 TES "overcapacity". Angka ini **tidak dipakai lagi**: datanya sudah tidak relevan menurut BPBD, dan angka 135 TES adalah artefak karena kuota diberi toleransi +10% sementara pengecekan *overcapacity* tidak. Skrip versi lama tersimpan di riwayat git.
