# Simulasi Kanonis (Canonical Simulation)

Dalam proyek **Siaga Padang**, simulasi kanonis merujuk pada **skrip simulasi rujukan resmi (*single source of truth*)** yang digunakan untuk menghasilkan metrik evaluasi yang definitif, berulang (*reproducible*), dan diakui secara akademik (misal, untuk Tabel 6.4 pada proposal/laporan).

## Dua Skrip Kanonis Utama

Bergantung pada tujuannya, terdapat dua skrip utama yang memegang peran kanonis di repositori ini:

### 1. `simulasi_resmi_padang.py` (Engine Simulasi Evaluasi Murni)
Skrip ini didedikasikan secara eksklusif untuk menjalankan eksperimen simulasi komparatif formal (Skenario Baseline vs Skenario Siaga Padang).
* **Sifat**: Deterministik, menggunakan *fixed random seed* (`42`).
* **Status Terkini (Oktober 2026)**: ⚠️ **Belum diselaraskan dengan data BPBD dan aturan evakuasi terbaru.** Skrip masih membaca CSV lama dari `legacy/data/` (143 TES, 12 TEA, `penduduk_kota_padang.csv`), memakai kecepatan 1,2 m/s, dan menulis petanya ke `legacy/output/`. Hasil di bagian bawah dokumen ini adalah hasil versi Hibrida V2 dan **tidak boleh dipakai sebagai angka final** sampai skrip dijalankan ulang dengan masukan yang sama dengan `build_db.py` (lihat "Pekerjaan yang tersisa").

### 2. Pembangun Database (`build_db.py`)
Satu skrip yang menghasilkan `ranah_siaga_v4.db` untuk Android langsung dari data BPBD, menggantikan rantai lama `core.py` → `build_db_v2_with_tea.py` → `spatial/` (diarsipkan di `legacy/pipeline_db/`). Skrip ini juga menghitung metrik cakupan berbasis penugasan (jiwa dengan tujuan ≤ 20 menit). Rincian: [build_db_v4.md](build_db_v4.md).

## Parameter Resmi Simulasi

Semua simulasi kanonis di repositori ini harus mematuhi parameter berikut (sumber: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md)):

1. **Kecepatan Evakuasi Pejalan Kaki**: `0.894 m/s` (2 mph, kecepatan orang terlemah menurut FEMA P-646, dipakai BPBD untuk radius 1 km / 20 menit). Kecepatan 1,2 m/s boleh dipakai hanya sebagai skenario pembanding (rata-rata), dan harus disebut demikian.
2. **Batas Waktu Tiba (*Golden Time*) Tsunami**: `20.0 menit` (skenario terburuk BPBD).
3. **Populasi**: 242.750 jiwa terpapar dari tabel KRB 2023–2027, disebar ke node zona merah menurut jejak bangunan RTRW. Jumlah agen sampel boleh berbeda, tetapi harus proporsional terhadap sebaran ini.
4. **Aturan Rute**: Tujuan dan rute harus menjauhi pantai; jembatan sungai diberi penalti; jalur evakuasi resmi diutamakan.
5. **Skenario Evaluasi**:
   * **Baseline**: Agen berjalan cepat ke TES (*Tempat Evakuasi Sementara*) terdekat secara murni (tanpa batasan kapasitas; memungkinkan kelebihan beban ekstrem).
   * **Siaga Padang**: Sistem alokasi gabungan, di mana:
     - Evakuasi menuju TES menghormati kapasitas gedung (*Capacity-Aware*), memaksa agen mencari rute alternatif jika penuh.
     - Evakuasi menuju TEA dan zona aman memakai waktu tempuh tercepat tanpa batas kapasitas.

## Aturan & Alur Logika Evakuasi (Skenario Siaga Padang)

Agar simulasi berjalan valid dan menyerupai kondisi nyata, skrip kanonis wajib mengimplementasikan alur evakuasi dengan aturan ketat berikut:

1. **Prioritas Pencarian Rute (TES vs TEA)**
   * Sistem secara *default* akan mengkalkulasi ETA (Estimasi Waktu Tiba) dari titik awal (node asal) warga menuju seluruh opsi TES vertikal terdekat maupun kawasan aman TEA horizontal terdekat.
   * Warga akan diarahkan ke opsi fasilitas (TES atau TEA) dengan **waktu tempuh tercepat (ETA terendah)** yang masih memiliki kapasitas.

2. **Aturan Kapasitas Ketat TES (Evakuasi Vertikal)**
   * Gedung TES memiliki **kuota maksimal** (kapasitas fisik).
   * Dalam simulasi, agen yang tiba lebih dulu (*first come, first serve* secara kalkulasi komputasi) akan mengambil kuota gedung.
   * Jika TES terdekat (Rekomendasi Utama) ternyata sudah **penuh**, agen tersebut dilarang memaksakan diri masuk dan **wajib dialihkan (*redirected*)** ke TES alternatif ke-2 atau ke-3.

3. **Aturan Bebas Kapasitas TEA (Evakuasi Horizontal)**
   * TEA (Kawasan Perbukitan/Lahan Terbuka Timur Padang) dianulir dari limitasi kapasitas karena luasannya yang sangat masif.
   * Jika semua opsi TES penuh, atau jika lari ke perbukitan (TEA) terbukti jauh lebih cepat daripada mencari TES alternatif, warga langsung dievakuasi ke TEA.

4. **Metrik Keselamatan Kritis (*Survival Criteria*)**
   * Seorang agen **hanya** dikategorikan `SELAMAT` jika berhasil tiba di dalam batas area TES (yang belum penuh) atau telah melewati garis demarkasi kawasan aman TEA dalam durasi **`<= 20.0 menit`**.
   * Agen yang baru tiba pada menit `20.1`, atau kehabisan tempat di TES dan terlambat lari ke TEA, dikategorikan `TIDAK SELAMAT` (Terpapar).

## Dataset Kanonis
Skrip simulasi dan pembangun DB wajib memakai data berikut (rincian di [build_db_v4.md](build_db_v4.md)):
* Graf jalan: `padang_full.graphml`
* TES & TEA: `Data BPBD/SHP kecamatan/2_TES_TEA_Padang.shp` (BPBD 2025), setelah filter di `build_db.py` (234 TES, 25 TEA). Cara termudah: baca dari `tb_tes`, `tb_tea`, dan `tb_fasilitas_info` di `ranah_siaga_v4.db`.
* Zona merah: raster `Peta_Bahaya_Tsunami` KRB 2023–2027 (`tb_nodes.is_safe`).
* Batas administrasi: `Basemap.gdb` → `Batas_Administrasi_Kelurahan_AR`.
* Penduduk: tabel KRB 2023–2027 (`tb_node_info.demand_jiwa`, `tb_kelurahan_info`).

## Pekerjaan yang tersisa
* Selaraskan `simulasi_resmi_padang.py` dengan dataset dan parameter di atas, lalu jalankan ulang Baseline vs Siaga Padang.
* Perbarui angka di [draft_revisi_proposal.md](draft_revisi_proposal.md) (143 TES, 12 TEA, 524 ribu jiwa, 81,0% / 53,2%) dengan hasil simulasi baru.

## Arsip: Hasil Simulasi Hibrida V2 (September 2026, data lama)

> Angka di bagian ini dihasilkan dengan data dan parameter lama (143 TES, 12 TEA, 1,2 m/s). Disimpan sebagai rujukan historis, bukan hasil resmi.

Berdasarkan eksekusi terbaru dari skrip `simulasi_resmi_padang.py` menggunakan 20.000 agen (merepresentasikan total 524.728 jiwa populasi terpapar), didapatkan metrik evaluasi definitif sebagai berikut:

| Metrik Evaluasi | Skenario Baseline | Skenario Siaga Padang (Hibrida V2) |
| :--- | :--- | :--- |
| **Gedung TES Overcapacity** | **84 Gedung** (45.7%) | **135 Gedung** *(Berdesakan toleransi 10%)* |
| **Tingkat Keselamatan (≤ 20 mnt)** | 81.0% (16.197 Agen) | **53.2% (10.632 Agen)** |
| **Rata-rata Waktu Tempuh** | 12.16 menit | 24.95 menit |
| **Rata-rata *Detour* (Pengalihan)** | 0.00 menit | +12.79 menit |

### Analisis *Illusory Survival Rate* (Angka Keselamatan Semu)
Sekilas, tingkat keselamatan *Baseline* (81.0%) terlihat jauh lebih tinggi dari *Siaga Padang* (53.2%). Namun dalam literatur kebencanaan, angka *Baseline* ini disebut sebagai **Angka Keselamatan Semu (*Illusory Survival Rate*)**.

Pada *Baseline*, sistem hanya mengukur waktu tempuh tanpa mempedulikan batas fisik bangunan. Ribuan warga berlari ke TES yang sama secara brutal. Hasilnya, meskipun secara matematis mereka tiba tepat waktu (<20 menit), **84 Gedung TES lumpuh akibat *overcapacity***. Di dunia nyata, kelebihan kapasitas ekstrem ini berujung pada korban jiwa akibat desak-desakan (*stampede*) dan kerumunan yang tertahan di luar gedung lalu tersapu tsunami.

Skenario **Siaga Padang (Hibrida V2)** hadir untuk memberikan **Angka Keselamatan Nyata (*Effective Survival Rate*)**. Algoritma *Capacity-Aware* mendistribusikan beban evakuasi dengan mengizinkan batas toleransi "berdesakan" maksimal 10% (*TOLERANCE_FACTOR = 1.1*). Hasilnya, 135 Gedung TES dimaksimalkan kapasitasnya dalam batas aman tanpa ada yang lumpuh, menghasilkan lonjakan keselamatan nyata menjadi 53.2%. Meskipun warga terpaksa berjalan sedikit lebih jauh (*detour* rata-rata 12.79 menit) ke TES alternatif atau TEA, 53.2% warga ini diproyeksikan **pasti selamat dan terhindar dari tragedi kerumunan**. Inilah nilai *novelty* (kebaruan) tertinggi dari sistem Siaga Padang untuk mitigasi massal.
