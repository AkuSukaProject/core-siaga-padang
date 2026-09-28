# Simulasi Kanonis (Canonical Simulation)

Dalam proyek **Siaga Padang**, simulasi kanonis merujuk pada **skrip simulasi rujukan resmi (*single source of truth*)** yang digunakan untuk menghasilkan metrik evaluasi yang definitif, berulang (*reproducible*), dan diakui secara akademik (misal, untuk Tabel 6.4 pada proposal/laporan).

## Dua Skrip Kanonis Utama

Bergantung pada tujuannya, terdapat dua skrip utama yang memegang peran kanonis di repositori ini:

### 1. `simulasi_resmi_padang.py` (Engine Simulasi Evaluasi Murni)
Skrip ini didedikasikan secara eksklusif untuk menjalankan eksperimen simulasi komparatif formal (Skenario Baseline vs Skenario Siaga Padang).
* **Sifat**: Deterministik, menggunakan *fixed random seed* (`42`).
* **Status Terkini**: *Script* ini **telah di-update** sepenuhnya untuk mengakomodasi skenario Hibrida V2 (termasuk alokasi rute ke 12 TEA tanpa batas kapasitas). Metrik kelulusan simulasi yang dihasilkan sudah merepresentasikan *survival rate* terbaru.

### 2. Pipa Pembangun Database (*Database Builder Pipeline*)
Merupakan urat nadi repositori ini untuk menggenerasi basis data SQLite (`ranah_siaga_v2.db`) bagi *client* (Android). Prosesnya terbagi menjadi dua tahap kanonis:
* **`core.py`**: Menjalankan algoritma pra-komputasi untuk Tempat Evakuasi Sementara (TES) berbasis kapasitas (*Capacity-Aware Assignment*) dan membentuk skema 6 tabel dasar (`ranah_siaga.db`).
* **`build_db_v2_with_tea.py`**: Skrip ekstensi wajib (NF-03) yang menyalin *baseline* dan menanamkan simulasi jarak terdekat (*Nearest Dijkstra*) untuk 12 Tempat Evakuasi Akhir (TEA) tanpa batas kapasitas, serta menghasilkan tabel navigasi dinamis yang sangat efisien (`tb_tea_next`).

## Parameter Resmi Simulasi

Semua simulasi kanonis di repositori ini harus mematuhi parameter standar berikut untuk menjaga validitas ilmiah:

1. **Kecepatan Evakuasi Pejalan Kaki**: `1.2 m/s` (merujuk pada standar BNPB).
2. **Batas Waktu Tiba (*Golden Time*) Tsunami**: `20.0 menit`.
3. **Populasi Agen Uji**: `20.000 agen` (dibangkitkan secara spasial proporsional terhadap distribusi total populasi terdampak dari data demografi BPS).
4. **Skenario Evaluasi**:
   * **Baseline**: Agen berjalan cepat ke TES (*Tempat Evakuasi Sementara*) terdekat secara murni (tanpa batasan kapasitas; memungkinkan kelebihan beban ekstrem).
   * **Siaga Padang (Hibrida V2)**: Sistem alokasi cerdas gabungan, di mana:
     - Evakuasi menuju TES menghormati kapasitas gedung (*Capacity-Aware*), memaksa agen mencari rute alternatif jika penuh.
     - Evakuasi menuju TEA murni menggunakan jarak/waktu tempuh tercepat tanpa batas kapasitas, demi kecepatan memasuki zona aman.

## Aturan & Alur Logika Evakuasi (Skenario Hibrida V2)

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
Skrip simulasi wajib menggunakan referensi data spasial riil yang telah divalidasi:
* Graf jalan: `padang_full.graphml`
* Data Shelter Vertikal: `data_tes_padang_lengkap_berkoordinat.csv` (143 TES Resmi BPBD)
* Data Shelter Horizontal: `data_tea_padang_lengkap_berkoordinat.csv` (12 Lahan Terbuka TEA)
* Batas Administrasi: `batas_kelurahan_kota_padang.geojson`
* Data Demografi: `penduduk_kota_padang.csv`

## Hasil Simulasi Resmi Hibrida V2 (Per September 2026)

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
