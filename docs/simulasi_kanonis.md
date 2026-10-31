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
Menghasilkan `ranah_siaga_v4.db` dari data BPBD (rincian: [build_db_v4.md](build_db_v4.md)). Skrip ini juga menghitung porsi TES berkapasitas (program linear, [kontrak_porsi_tujuan.md](kontrak_porsi_tujuan.md)) dan melaporkan jiwa yang punya tujuan sempat ≤ 15 menit (216.561 jiwa, 69,0%), pembanding silang hasil simulasi agen (68,2% selamat ≤ 20 menit).

## Parameter Resmi Simulasi

Sumber: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md).

| Parameter | Nilai |
|---|---|
| Kecepatan berjalan | **0,894 m/s** (orang terlemah, FEMA P-646), dibaca dari `tb_metadata`. Kolom ETA di DB (1,2 m/s, kontrak) dikonversi ke 0,894 m/s. 1,2 m/s hanya sebagai pembanding. |
| Batas waktu | **20 menit** (skenario terburuk BPBD) |
| Agen | **20.000**, dibangkitkan proporsional terhadap `tb_node_info.demand_jiwa` (313.943 jiwa: 242.750 jiwa terpapar KRB 2023–2027 + perkiraan 71.193 jiwa di zona tambahan peta evakuasi BPBD; 1 agen ≈ 15,70 jiwa). Semua agen berasal dari zona merah. |
| Fasilitas | 244 TES dan 22 TEA yang dipakai routing (`tb_fasilitas_info.dipakai = 1`) |
| Kapasitas | Kapasitas TES diskalakan ke jumlah agen (dibulatkan, minimal 1). Tanpa toleransi berdesakan. TEA dan zona aman tidak dibatasi. |

## Skenario

| | A. Baseline | B. Siaga Padang |
|---|---|---|
| Perilaku | Warga tanpa aplikasi berjalan ke TES/TEA **terdekat menurut jarak jalan murni** | Warga mengikuti rekomendasi database |
| Aturan arah & jembatan | Tidak | Ya (sudah tertanam di rute DB: tujuan menjauh > 15°, jembatan ≥ 20 m hanya cadangan) |
| Kandidat tujuan | 1 fasilitas terdekat | TES rank 1–3, TEA utama & alternatif, zona aman dari `tb_safe_routes_v2` (pembanding: tabel kontrak lama `tb_safe_routes`, opsi `--rute-aman kontrak`). Urutan sama dengan aplikasi (K-B6, 12 Oktober): yang sempat ≤ 15 menit lebih dulu (cadangan 5 menit), keluar zona (TEA/zona aman) sebelum TES, di dalam tiap kelompok terjauh dari pantai lebih dulu; yang tidak sempat menyusul menurut ETA. Kriteria selamat tetap tiba ≤ 20 menit |
| Kapasitas | Diabaikan saat memilih; yang datang setelah TES penuh tidak tertampung | TES penuh dilewati, agen pindah ke kandidat berikutnya |
| Urutan pemrosesan | Menurut ETA (yang lebih cepat masuk lebih dulu) | Menurut ETA kandidat pertama |

**Kriteria selamat**: tiba ≤ 20 menit **dan** tertampung. Untuk TES berarti belum penuh saat agen tiba; TEA dan zona aman selalu menampung.

## Hasil Resmi (27 Oktober 2026, data v4 versi 2026.10.18)

Simulasi tidak membaca `tb_route_shares`; tabel yang dibacanya identik dengan 2026.10.16, jadi hasilnya sama dengan 2026.10.16.

| Metrik | Baseline (terdekat) | Siaga Padang |
| :--- | :--- | :--- |
| TES melebihi kapasitas | **104** dari 244 | **0** dari 244 |
| Tiba ≤ 20 menit (tanpa melihat kapasitas) | 13.721 agen (68,6%) | 13.638 agen (68,2%) |
| **Selamat: tiba ≤ 20 menit & tertampung** | **7.341 agen (36,7%)** | **13.638 agen (68,2%)** |
| Tiba di TES tapi tidak tertampung | 11.523 agen | 0 |
| Rata-rata waktu tempuh | 18,20 menit | 23,12 menit |
| Rata-rata tambahan waktu karena pengalihan | 0 | 4,86 menit |
| Tujuan TES / TEA / zona aman (agen) | 18.847 / 1.153 / 0 | 5.914 / 430 / 13.656 |
| Pembanding 1,2 m/s: selamat | 37,8% | 76,1% |

### Interpretasi
* **Angka keselamatan semu.** Tanpa memperhatikan kapasitas, 68,6% warga Baseline "tiba tepat waktu", tetapi 104 TES kelebihan beban dan 11.523 agen tidak tertampung. Keselamatan nyata Baseline hanya 36,7%.
* **Siaga Padang menggandakan keselamatan nyata** menjadi 68,2% tanpa satu pun TES kelebihan kapasitas. Sekitar 70% warga diarahkan keluar zona (zona aman/TEA), karena keluar zona didahulukan bila sempat dalam 15 menit.
* **Rata-rata waktu tempuh lebih panjang, dan memang disengaja.** Warga yang sempat diarahkan ke tujuan terjauh dari pantai yang masih terjangkau ≤ 15 menit, bukan ke tujuan tercepat. Waktu tempuhnya bertambah, tetapi tetap dengan cadangan 5 menit sebelum batas 20 menit.
* **Ada harga dari aturan arah.** Tujuan harus menjauh dari pantai lebih dari 15° (sejajar tidak boleh) dan jembatan ≥ 20 m hanya cadangan. Di 9 dari 67 kelurahan berpenghuni, keselamatan Siaga Padang lebih rendah daripada Baseline. Selisih terbesar: Koto Baru Nan XX (47,5% vs 76,3%), Bungus Barat (55,6% vs 79,1%), Teluk Kabung Selatan (87,1% vs 100%), Air Tawar Timur (25,3% vs 34,3%), dan Bungus Selatan (46,3% vs 53,7%); sisanya Belakang Pondok, Parupuk Tabing, Air Tawar Barat, dan Batang Kabung dengan selisih di bawah 8 poin (sebagian karena jumlah agen per kelurahan kecil). Di wilayah ini tujuan terdekat berada di arah laut atau sejajar pantai sehingga tidak boleh direkomendasikan. Selisih itu konsekuensi aturan BPBD; Baseline sendiri melanggar aturan tersebut.
* **Kantong rawan.** Kelurahan dengan keselamatan terendah (Batang Kabung 0,5%, Pasir Nan Tigo 17,7%, Air Tawar Timur 25,3%, Padang Sarai 33,9%, Parupuk Tabing 34,7%) adalah kandidat lokasi TES vertikal baru untuk direkomendasikan ke BPBD. Rinciannya di `analisis/output/hasil_simulasi_kelurahan.csv` dan peta celah `hasil_build/peta_celah_kelurahan.csv` (H-7).

### Pembanding: tabel zona aman kontrak lama

Bila aplikasi tetap memakai `tb_safe_routes` (kontrak §2.1 lama: pohon global ke batas zona hijau terdekat; 974 simpul merah tanpa baris karena tujuannya tidak lolos syarat arah):

| Metrik Siaga Padang | `tb_safe_routes_v2` (resmi) | `tb_safe_routes` (kontrak lama) |
| :--- | :--- | :--- |
| Selamat: tiba ≤ 20 menit & tertampung | **68,2%** | 66,0% |
| TES melebihi kapasitas | 0 | 0 |
| Rata-rata waktu tempuh | 23,12 menit | 22,83 menit |
| Tujuan TES / TEA / zona aman (agen) | 5.914 / 430 / 13.656 | 6.342 / 1.401 / 12.257 |
| Pembanding 1,2 m/s: selamat | 76,1% | 73,7% |

Dengan tabel lama, 974 simpul merah tidak punya baris zona aman, sehingga warganya harus ke TES/TEA yang lebih lama. Jalankan: `env\Scripts\python.exe analisis\simulasi_resmi_padang.py --rute-aman kontrak` (keluaran berakhiran `_kontrak`).

Riwayat: DB 2026.10.17 (jaringan jalan OSM 20 Oktober 2026, tidak dipakai lagi) menghasilkan 68,3%. DB 2026.10.16 (graf 8 Agustus 2026, sama dengan 2026.10.18) menghasilkan 68,2%. DB 2026.10.15 (batas sempat 20 menit, tujuan terjauh dari pantai di semua jenis) menghasilkan 68,5%. DB 2026.10.14 (zona merah hanya landaan KRB, 242.750 jiwa) menghasilkan 72,2%. DB 2026.10.12 (aturan "tercepat yang lolos syarat", keluar zona didahulukan) menghasilkan 68,8% dengan tabel kontrak dan 70,9% dengan v2.

Catatan: angka tujuan sempat di `build_db.py` (69,0% jiwa punya tujuan ≤ 15 menit pada t = 0) memakai aturan dan rute v2 yang sama, tetapi menghitung keterjangkauan, bukan agen yang tertampung.

## Batasan Model
* Tidak memodelkan kemacetan pejalan kaki atau antrean tangga (lihat simulasi mikro BPR di `legacy/simulasi/`).
* Tidak memodelkan waktu tunda keberangkatan; ETA dihitung sejak warga mulai berjalan.
* Kapasitas 75 TES masih estimasi (lihat [build_db_v4.md](build_db_v4.md)).
* Baseline mengasumsikan warga tahu fasilitas terdekat; dalam kenyataan sebagian warga tidak tahu sama sekali, sehingga Baseline cenderung optimistis.

## Arsip: Hasil Hibrida V2 (September 2026, data lama)

Dengan data lama (143 TES, 12 TEA, 524.728 jiwa, 1,2 m/s, toleransi berdesakan 10%), hasilnya Baseline 81,0% dan Siaga Padang 53,2%, dengan 84 vs 135 TES "overcapacity". Angka ini **tidak dipakai lagi**: datanya sudah tidak relevan menurut BPBD, dan angka 135 TES adalah artefak karena kuota diberi toleransi +10% sementara pengecekan *overcapacity* tidak. Skrip versi lama tersimpan di riwayat git.
