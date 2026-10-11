# Kebijakan Kapasitas TES dan TEA dalam Sistem Siaga Padang

Dokumen ini menggarisbawahi rancangan keputusan (*By-Design*) terkait penanganan batas kapasitas fasilitas evakuasi (TES dan TEA), implikasinya terhadap klaim data proposal, serta panduan antarmuka (UI) dalam sistem Siaga Padang.

## 1. Perbedaan Algoritma untuk TES dan TEA

Sistem memberlakukan aturan perhitungan rute yang sangat berbeda untuk Tempat Evakuasi Sementara (TES) dan Tempat Evakuasi Akhir (TEA).

*   **TES (Gedung Vertikal) - *Capacity-Aware Routing*:**
    Bangunan TES memiliki batas ruang fisik yang absolut (misal: luas lantai yang aman dari tsunami). Jika kelebihan beban (*overcapacity*), risiko jatuhnya korban tak terhindarkan. Oleh karena itu, simulasi rute menuju TES **wajib** menggunakan sistem pembatasan kapasitas. Warga yang tidak mendapat kuota di TES terdekat akan dialihkan secara logis ke gedung alternatif (Rank 2 atau Rank 3).
*   **TEA (Lahan Terbuka/Perbukitan) - *Nearest-Distance Routing*:**
    TEA merupakan kawasan evakuasi horizontal menjauhi pantai berupa lahan terbuka yang luas. Angka kapasitas yang tertera di data TEA berfungsi sebagai estimasi logistik pengungsian pasca-bencana, bukan sebagai batas hidup/mati saat *Golden Hour*. 
    Memaksa warga yang sudah berjalan cepat dan tiba di zona aman/kaki bukit untuk berpindah ke bukit lain (hanya karena alasan kuota) sangatlah berbahaya. Oleh karena itu, rute menuju TEA **tidak dibatasi kapasitas**, dan hanya murni mencari waktu tempuh tercepat dari posisi warga.

## 2. Sumber angka kapasitas di database (versi 2026.10.12)

*   **`tb_tes.kapasitas`** hanya berisi daya tampung dari data BPBD, berurutan: titik TES/TEA 2025, daftar resmi BPBD 2019 ("TES OK"), lalu verifikasi BPBD 2019. Bila tidak ada, kolom **kosong** (77 dari 244 TES), sesuai kontrak DB aplikasi; nilai bawaan seperti 300 tidak dipakai lagi.
*   **Penugasan internal (opsi A, `tb_route_shares`)** tetap butuh angka untuk TES yang kosong. Engine memperkirakannya dari luas jejak bangunan RTRW × jumlah lantai di atas lantai 2 ÷ 1 m² per orang, atau median TES BPBD. Estimasi ini hanya ada di `tb_fasilitas_info` (`kapasitas_sumber` = "estimasi …") dan tidak ditampilkan sebagai data resmi.
*   **TEA**: `kapasitas = 0` berarti tidak ada data. TEA tidak dibatasi kapasitas.

## 3. Dampak terhadap metrik simulasi

Angka lama di proposal (74,49% selamat) dihitung dengan asumsi semua warga ke TES dan tidak dapat direproduksi. Simulasi kanonis dijalankan ulang dengan data BPBD terbaru, TES berbatas kapasitas, serta TEA dan zona aman tanpa batas ([simulasi_kanonis.md](simulasi_kanonis.md)):

*   **Baseline** (warga ke tempat terdekat, kapasitas diabaikan): 35,6% selamat, 82 TES kelebihan beban.
*   **Siaga Padang** (rekomendasi DB, tabel sesuai kontrak): **68,8%** selamat, **0** TES kelebihan beban (70,9% bila aplikasi memakai rute zona aman v2 yang opsional). Sekitar 81% warga diarahkan keluar zona (zona aman/TEA) karena kebijakan "keluar zona dulu bila sempat" (K-B6), sehingga beban TES jauh berkurang.
*   Angka tidak mendekati 100% karena aturan BPBD (tujuan harus menjauhi pantai, hindari jembatan) dan sebaran TES: sekitar 22% warga zona merah tidak sempat ke tempat evakuasi mana pun dalam 20 menit pada laju orang terlemah.

## 4. Kebijakan Antarmuka (UI) dan Mode Darurat

Prinsip utama aplikasi Siaga Padang pada saat Tsunami terjadi adalah **"Satu Instruksi pada Satu Waktu"**. Warga yang panik tidak boleh dibebani dilema saat melihat layar HP.

*   **Tanpa Pesan Peringatan Saat Darurat:** Aplikasi dilarang keras memunculkan peringatan seperti *"TEA ini diperkirakan padat, pertimbangkan jalur alternatif"* di layar navigasi evakuasi. Hal ini berpotensi membingungkan warga dan memicu mereka menggunakan kendaraan bermotor, yang bertentangan tajam dengan instruksi BPBD dan akan menyebabkan *gridlock* (kemacetan fatal).
*   **Lokasi Tampilan Informasi:** Prediksi kepadatan atau angka kapasitas TEA/TES **hanya boleh ditampilkan di halaman direktori/katalog informasi** saat masa tenang (Pra-Bencana). Fungsinya sebatas untuk literasi dan edukasi kesiapsiagaan warga. Kapasitas kosong ditulis "belum ada data", bukan 0.

## 5. Standar Terminologi Proyek (Aturan Kata)

Mulai saat ini, seluruh dokumen arsitektur, laporan, hingga instruksi teks (UI) di dalam aplikasi **tidak boleh lagi** menggunakan kata "berlari". Terminologi standar yang wajib digunakan sesuai dengan protokol keamanan evakuasi Tsunami BPBD adalah **"berjalan cepat"**.
