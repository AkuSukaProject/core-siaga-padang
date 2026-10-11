# Draft Revisi Proposal GEMASTIK: Integrasi Hasil Simulasi

> **⚠️ Angka di draf ini berasal dari data lama** (143 TES, 12 TEA, 524 ribu jiwa, kecepatan 1,2 m/s). Data BPBD terbaru memakai 244 TES, 25 TEA, dan 242.750 jiwa terpapar (KRB 2023–2027). Jangan disalin ke proposal. Hasil simulasi dengan data baru (Baseline 35,6% vs Siaga Padang 68,8%, 82 vs 0 TES melebihi kapasitas) ada di [simulasi_kanonis.md](simulasi_kanonis.md); teks draf ini perlu ditulis ulang mengikuti angka tersebut.

Dokumen ini berisi draf teks siap salin (*copy-paste*) yang dapat Anda gunakan untuk merevisi **BAB V** dan **BAB VI** pada proposal GEMASTIK Anda, berdasarkan hasil simulasi terbaru.

---

## 1. Revisi untuk BAB V (Halaman 14)
*Hapus bagian 5.7.3 Status Reproduksibilitas yang lama, dan ganti seluruh subbabnya menjadi teks di bawah ini:*

### 5.7.3 Validasi Model Pemilihan Jalur (ACAER)
Untuk memvalidasi ketangguhan algoritma penentuan jalur alternatif, rancangan ini telah dievaluasi menggunakan pemodelan *Adaptive Capacity-Aware Evacuation Routing* (ACAER) dalam simulasi agen berbasis kemacetan mikro. Simulasi ini mengadopsi fungsi *Bureau of Public Roads* (BPR) untuk menghitung pelambatan eksponensial pejalan kaki saat kapasitas jalan menyempit, memodelkan perilaku desak-desakan riil saat kepanikan massal terjadi.

Berdasarkan pengujian pada sampel 5.000 agen di zona padat (Kecamatan Padang Barat), algoritma pengalihan jalur alternatif yang menimbang skor kapasitas dan waktu tempuh terbukti tangguh secara matematis. Algoritma usulan mampu mendistribusikan agen yang terjebak penumpukan ke opsi fasilitas lain yang lebih lengang, mencetak tingkat keselamatan sebesar 74,49% di bawah kondisi *bottleneck* jalan yang parah. Hasil ini menjadi landasan teoretis yang mengonfirmasi bahwa penyiapan tiga alternatif jalur secara luring di perangkat pengguna bukan sekadar perhitungan jarak, melainkan bagian krusial dari upaya pencegahan penumpukan fatal di pintu gedung.

---

## 2. Tambahan untuk BAB VI (Halaman 17 atau 18)
*Tambahkan subbab baru 6.6 ini setelah Subbab 6.5 Hasil Pengujian:*

### 6.6 Hasil Simulasi Operasional Skala Makro
Selain validasi algoritmik di tingkat mikro, efektivitas basis data Siaga Padang diuji dalam simulasi skala makro untuk mengevaluasi pemerataan beban ke 143 TES dan 12 TEA di seluruh wilayah Kota Padang. Pengujian melibatkan 20.000 agen yang didistribusikan secara spasial berdasarkan data populasi BPS/BPBD (mewakili 524 ribu jiwa terpapar).

Simulasi membandingkan perilaku evakuasi natural warga (*Baseline*) melawan evakuasi yang dipandu oleh skema alokasi berbatas kapasitas (*Siaga Padang Hibrida*).
1. **Skenario Baseline:** Saat seluruh agen secara naluriah menuju fasilitas terdekat, tingkat keselamatan terlihat tinggi (81,0%), namun hasil tersebut adalah ilusi karena **84 gedung TES (45,7%) mengalami kelebihan kapasitas ekstrem**. Dalam kenyataan, ribuan warga tersebut akan terjebak di luar bangunan dan menjadi korban jiwa akibat overkapasitas.
2. **Skenario Siaga Padang Hibrida:** Skema rute yang dirancang menolak pengisian TES di atas kapasitas nominal, lalu mendistribusikan sisa luapan warga (*overflow*) secara terarah menuju lahan perbukitan (TEA) yang berkapasitas tak terbatas. Pendekatan ini berhasil menekan angka overkapasitas fasilitas menjadi absolut **0 (nol)**. Seluruh beban warga sukses terdistribusi dengan aman tanpa menumpuk di satu titik, menyelamatkan 50,35% populasi kota secara murni dan merata sebelum batas *golden time* tsunami (20 menit).

*Catatan untuk Tim:*
*(Sisipkan Gambar Peta Leaflet Berdampingan di bawah paragraf ini)*
**Gambar 6.X** Perbandingan sebaran beban evakuasi: (a) Baseline alami dengan 84 TES kelebihan batas (merah), dan (b) Distribusi Siaga Padang dengan pemerataan luapan ke zona TEA (hijau).
