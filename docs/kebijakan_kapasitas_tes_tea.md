# Kebijakan Kapasitas TES dan TEA dalam Sistem Siaga Padang

Dokumen ini menggarisbawahi rancangan keputusan (*By-Design*) terkait penanganan batas kapasitas fasilitas evakuasi (TES dan TEA), implikasinya terhadap klaim data proposal, serta panduan antarmuka (UI) dalam sistem Siaga Padang.

## 1. Perbedaan Algoritma untuk TES dan TEA

Sistem memberlakukan aturan perhitungan rute yang sangat berbeda untuk Tempat Evakuasi Sementara (TES) dan Tempat Evakuasi Akhir (TEA).

*   **TES (Gedung Vertikal) - *Capacity-Aware Routing*:**
    Bangunan TES memiliki batas ruang fisik yang absolut (misal: luas lantai yang aman dari tsunami). Jika kelebihan beban (*overcapacity*), risiko jatuhnya korban tak terhindarkan. Oleh karena itu, simulasi rute menuju TES **wajib** menggunakan sistem pembatasan kapasitas. Warga yang tidak mendapat kuota di TES terdekat akan dialihkan secara logis ke gedung alternatif (Rank 2 atau Rank 3).
*   **TEA (Lahan Terbuka/Perbukitan) - *Nearest-Distance Routing*:**
    TEA merupakan kawasan evakuasi horizontal menjauhi pantai berupa lahan terbuka yang luas. Angka kapasitas yang tertera di data TEA berfungsi sebagai estimasi logistik pengungsian pasca-bencana, bukan sebagai batas hidup/mati saat *Golden Hour*. 
    Memaksa warga yang sudah berjalan cepat dan tiba di zona aman/kaki bukit untuk berpindah ke bukit lain (hanya karena alasan kuota) sangatlah berbahaya. Oleh karena itu, rute menuju TEA **tidak dibatasi kapasitas**, dan hanya murni mencari waktu tempuh tercepat dari posisi warga.

## 2. Dampak Terhadap Metrik Simulasi (P2-03)

Penggabungan skenario TEA (tanpa batas kapasitas) membawa konsekuensi besar namun positif terhadap metrik keselamatan:

*   **Peringanan Beban TES:** Dengan dimasukkannya TEA, sekitar ±32% titik simpul persimpangan kini akan menyalurkan warga langsung ke TEA. Hal ini secara drastis mengurangi tekanan jumlah warga yang memperebutkan kuota di TES.
*   **Tindakan Wajib (Jalankan Ulang Simulasi):** Klaim angka keberhasilan evakuasi di proposal (yaitu sebesar **74,49%** warga selamat tanpa ada TES *overcapacity*) dihitung menggunakan asumsi awal bahwa *semua warga lari ke TES*. 
*   **Kesimpulan:** Angka tersebut tidak lagi relevan. Tim peneliti (P2-03) **wajib menjalankan ulang simulasi spasial** dengan skema hibrida TES + TEA yang baru. Sangat besar kemungkinan angka keberhasilan akan meningkat mendekati angka sempurna karena beban TES sudah didistribusikan ke TEA.

## 3. Kebijakan Antarmuka (UI) dan Mode Darurat

Prinsip utama aplikasi Siaga Padang pada saat Tsunami terjadi adalah **"Satu Instruksi pada Satu Waktu"**. Warga yang panik tidak boleh dibebani dilema saat melihat layar HP.

*   **Tanpa Pesan Peringatan Saat Darurat:** Aplikasi dilarang keras memunculkan peringatan seperti *"TEA ini diperkirakan padat, pertimbangkan jalur alternatif"* di layar navigasi evakuasi. Hal ini berpotensi membingungkan warga dan memicu mereka menggunakan kendaraan bermotor, yang bertentangan tajam dengan instruksi BPBD dan akan menyebabkan *gridlock* (kemacetan fatal).
*   **Lokasi Tampilan Informasi:** Prediksi kepadatan atau angka kapasitas TEA/TES **hanya boleh ditampilkan di halaman direktori/katalog informasi** saat masa tenang (Pra-Bencana). Fungsinya sebatas untuk literasi dan edukasi kesiapsiagaan warga.

## 4. Standar Terminologi Proyek (Aturan Kata)

Mulai saat ini, seluruh dokumen arsitektur, laporan, hingga instruksi teks (UI) di dalam aplikasi **tidak boleh lagi** menggunakan kata "berlari". Terminologi standar yang wajib digunakan sesuai dengan protokol keamanan evakuasi Tsunami BPBD adalah **"berjalan cepat"**.
