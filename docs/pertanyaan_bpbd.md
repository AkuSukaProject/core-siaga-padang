# Pertanyaan Lanjutan untuk BPBD Kota Padang

**Disusun:** 11 Oktober 2026 · **Untuk:** Bidang Pencegahan dan Kesiapsiagaan (PK) BPBD Kota Padang (Bang Resko) · **Dasar:** DB rute evakuasi versi 2026.10.14

Daftar ini melanjutkan pertanyaan di `siagapadang/docs/MASUKAN_BPBD_WAWANCARA.md` §6. Isinya hal-hal yang muncul setelah data BPBD diolah menjadi database aplikasi. Pertanyaan bertanda ⭐ paling berpengaruh pada isi aplikasi; jawabannya kami butuhkan sebelum **15 Oktober 2026** (DB final 16 Oktober, titik putus 18 Oktober).

> **Catatan untuk tim:** kirim lewat Mikail atau dengan sepengetahuannya, supaya hanya ada satu jalur pertanyaan ke BPBD. Pertanyaan A1, A2, A4, dan A5 adalah asumsi kerja di `PEMBAGIAN_TUGAS_BPBD.md` §1. Lampiran CSV ada di folder `hasil_build/` repo engine.

---

## Pesan siap kirim

Assalamu'alaikum, Bang Resko.

Terima kasih atas data dan masukan dari BPBD. Data KRB 2023–2027, titik TES/TEA 2025, jalur evakuasi, dan daftar shelter 2019 sudah kami olah menjadi database rute evakuasi aplikasi Siaga Padang. Ada beberapa hal yang perlu kami pastikan agar isi aplikasi sesuai arahan BPBD. Yang bertanda ⭐ kami butuhkan paling lambat 15 Oktober, Bang.

### A. Aturan arah dan rute

1. ⭐ **Batas "sejajar pantai".** Tujuan kami anggap menjauh dari pantai bila arahnya lebih dari 15° menjauhi garis pantai; yang kurang dari itu kami anggap sejajar dan tidak dipakai. Apakah batas 15° ini sesuai?
2. ⭐ **Tujuan yang sangat dekat.** TES/TEA dalam 100 m dari posisi warga tidak kami nilai arahnya, walaupun sedikit ke arah pantai. Apakah ini boleh, atau tetap tidak boleh sama sekali?
3. **Bukit di tepi pantai.** Bolehkah bukit di tepi pantai (misalnya Gunung Padang, Bukit Lampu) menjadi tujuan bagi warga di kakinya?
4. ⭐ **Jembatan.** Kami menghindari jembatan dengan badan ≥ 20 m. Rute lewat jembatan hanya diberikan bila tidak ada tujuan tanpa jembatan, dengan keterangan "lewat jembatan". Apakah batas 20 m sesuai? Apakah BPBD punya daftar jembatan yang dianggap rawan runtuh?
5. **Keluar zona dulu.** Bila warga sempat mencapai zona hijau atau TEA dalam 20 menit, aplikasi mengarahkan ke sana lebih dulu, baru ke TES bila tidak sempat. Apakah urutan ini sesuai?

### B. Tempat evakuasi sementara (TES)

6. ⭐ **Minimal jumlah lantai.** Di verifikasi BPBD 2019, 6 dari 7 bangunan ≤ 2 lantai dinilai "tidak potensial". Apakah BPBD menetapkan minimal 3 lantai untuk TES, atau penilaiannya per bangunan seperti di verifikasi 2019?
7. ⭐ **Masjid Raya Sumbar** tercatat 2 lantai tetapi dinilai "potensial" dengan daya tampung 15.000 orang. Apakah tetap layak sebagai TES? Bila ya, apakah di bagian tertentu saja (misalnya lantai atas/atap)?
8. ⭐ **17 bangunan daftar shelter 2019 belum punya titik koordinat** (Lampiran 1). Mohon koordinat atau titik lokasinya.
9. **14 bangunan daftar shelter 2019 yang lokasinya kami cari sendiri** dari peta OpenStreetMap (Lampiran 2). Nama dan jalannya cocok dengan alamat BPBD, tetapi titiknya belum dicek di lapangan. Mohon dikoreksi bila ada yang salah.
10. **24 titik berlabel TES tetapi berupa bukit** (Lampiran 3). Apakah sebenarnya TEA (evakuasi horizontal)?
11. **Titik ganda di data 2025.** Incasi Raya, Youth Center, dan FK Unand masing-masing tercatat dua kali di lokasi hampir sama; sudah kami gabung. Bukit Lampu, Bukit Karan, Bukit Simpang Rawang, dan Dealer Honda dipakai untuk dua tempat berbeda; kami bedakan dengan nama kelurahan. Apakah ini benar?
12. **Universitas Taman Siswa** berstatus "tidak potensial" di verifikasi 2019, sehingga tidak kami pakai. Apakah statusnya masih sama?
13. **77 TES belum punya angka daya tampung.** Apakah BPBD punya datanya? Bila daya tampung dihitung dari luas lantai, standar mana yang dipakai: 0,5, 1, atau 2 m² per orang?

### C. Tempat evakuasi akhir (TEA)

14. ⭐ **Daftar TEA resmi.** Data TEA kami dari digitasi Kelurahan Tangguh/latihan 2025. Apakah ada daftar TEA yang ditetapkan BPBD?
15. ⭐ **21 TEA berada di dalam zona landaan** menurut peta bahaya tsunami KRB 2023–2027 (Lampiran 4), misalnya Bundaran Siti Nurbaya, Lapangan SSAG, dan LANTAMAL. Untuk sementara tidak kami pakai. Apakah titiknya salah plot, atau memang tidak layak sebagai TEA?

### D. Zona, ketinggian, dan penduduk

16. **Garis biru batas 11 m.** Bolehkah kami meminta data titik atau garis biru batas zona aman? Saat ini batas zona hijau kami ambil dari peta bahaya tsunami KRB.
17. **Jumlah jiwa terpapar.** Kami memakai 242.750 jiwa di 56 kelurahan (tabel KRB 2023–2027). Di wawancara juga disebut sekitar 260.000. Angka mana yang dipakai BPBD?

### E. Hasil untuk BPBD

18. Dari perhitungan kami, sekitar **22% warga zona merah tidak sempat mencapai tempat evakuasi mana pun dalam 20 menit** (berjalan 0,89 m/s), terutama di Batang Kabung, Padang Sarai, Pasir Nan Tigo, dan Bungo Pasang (Koto Tangah). Rinciannya per kelurahan ada di Lampiran 5. Apakah data ini berguna bagi BPBD sebagai masukan penempatan TES baru?

Terima kasih banyak, Bang. Bila lebih mudah dijelaskan lewat telepon atau bertemu langsung, kami siap menyesuaikan.

Salam,
Tim Siaga Padang

---

## Lampiran 1. Bangunan daftar shelter 2019 yang belum punya titik (pertanyaan 8)

Berkas: `hasil_build/bpbd_2019_tanpa_titik.csv`.

| No | Nama (daftar BPBD) | Alamat | Lantai | Catatan pencarian kami |
|---|---|---|---|---|
| 1 | Wisma Indah Warta Bunda | Jl. Sumatera, Ulak Karang Utara | 4 | Tidak ditemukan di peta |
| 2 | Shelter Darussalam | Kel. Bungo Pasang | 6 | Tidak ditemukan di peta |
| 3 | Bank Nagari | Jl. Pemuda | 6 | Yang ditemukan kantor cabang Jl. Adinegoro, bukan kantor pusat |
| 4 | Bappeda Prov. Sumbar | Jl. Khatib Sulaiman | 4 | Tidak ditemukan di peta |
| 5 | Dinas PU dan Pemukiman Prov. Sumbar | Jl. Taman Siswa No. 1 | 3 | Yang ditemukan Dinas PUPR Kota Padang (Jl. Duku) |
| 6 | Pustaka Daerah | Jl. Khairil Anwar | 5 | Yang ditemukan Perpustakaan Daerah Kota Padang (Jl. Batang Kampar) |
| 7 | Telkom | Jl. Bagindo Azis Chan | 7 | Yang ditemukan di Jl. Ahmad Khatib, alamat tidak cocok |
| 8 | PT AMP | Jl. Hamka, Parupuk Tabing | 4 | Tidak ditemukan di peta |
| 9 | Pasar Inpres | Jl. Sandang Pangan (Pasar Raya) | 4 | Tidak ditemukan di peta |
| 10 | Villa Hadis | Jl. Khatib Sulaiman | – | Tidak ditemukan di peta |
| 11 | Sekolah Al Azhar 32 | Jl. Khatib Sulaiman | 3 | Tidak ditemukan di peta |
| 12 | SD Agnes | Jl. Bandar Gereja | 3 | Tidak ditemukan di peta |
| 13 | SDN 23 dan 24 Ujung Gurun | Jl. Veteran No. 82 | 4 | Tidak ditemukan di peta |
| 14 | Perpustakaan UNP | Jl. Hamka, Air Tawar | 6 | Yang ditemukan Perpustakaan Fakultas Ekonomi UNP |
| 15 | AMIK Indonesia | Jl. Khatib Sulaiman | 3 | Tidak ditemukan di peta |
| 16 | SPR Plaza | Jl. M. Yamin | – | Tidak ditemukan di peta |
| 17 | Hotel Daima | Jl. Sudirman | 6 | Yang ditemukan di Jl. Raya Azizi, alamat tidak cocok |

## Lampiran 2. Bangunan daftar shelter 2019 yang lokasinya kami cari dari peta (pertanyaan 9)

Koordinat dari OpenStreetMap; sudah dipakai di aplikasi sebagai TES bersumber BPBD. Berkas: `data_osm/geokode_daftar_resmi_bpbd.csv`.

| ID | Nama | Kelurahan | Lantai | Lintang, bujur |
|---|---|---|---|---|
| TES_235 | Hotel Inna Muara | Belakang Tangsi | 6 | -0.95691, 100.35684 |
| TES_236 | Hotel Rocky | Kampung Jao | – | -0.94685, 100.35937 |
| TES_237 | Axana Hotel | Kampung Pondok | – | -0.95457, 100.35936 |
| TES_238 | Bumi Minang Hotel | Kampung Pondok | 8 | -0.95579, 100.35865 |
| TES_239 | Damar Plaza | Olo | 5 | -0.94431, 100.35490 |
| TES_240 | Masjid Al Wustha | Padang Pasir | 4 | -0.93819, 100.35486 |
| TES_241 | PT Sutan Kasim | Padang Pasir | 4 | -0.94093, 100.35553 |
| TES_242 | Rusunawa | Purus | 5 | -0.93702, 100.35179 |
| TES_243 | Hotel Grand Zuri | Alang Laweh | 8 | -0.95469, 100.36432 |
| TES_244 | Dinas Peternakan Prov. Sumbar | Jati Baru | 3 | -0.93188, 100.36175 |
| TES_245 | Basko Hotel & Plaza | Air Tawar Timur | 8 | -0.90220, 100.35103 |
| TES_246 | Hotel Ibis | Alai Parak Kopi | 12 | -0.92966, 100.36298 |
| TES_247 | Daihatsu & ACC Finance | Ulak Karang Utara | 3 | -0.90800, 100.35293 |
| TES_248 | Universitas Bung Hatta | Ulak Karang Utara | 4 | -0.90649, 100.34353 |

Selain itu, 11 bangunan daftar 2019 ternyata sudah ada di data 2025 dengan nama berbeda (titiknya < 70 m), misalnya Polda Sumbar = "POLDA Sumatera Barat", Masjid Raya Sumbar = "Masjid Raya Syekh Ahmad Khatib", RS M. Jamil = "RSUP Dr. M. Djamil". Daftarnya ada di berkas yang sama (`hasil = sudah_ada_di_data_2025`).

## Lampiran 3. Titik berlabel TES yang berupa bukit (pertanyaan 10)

Bukit Air Manis · Bukit Belakag Tugu Kapal · Bukit Belakang Mushola Al-Kautsar · Bukit Belakang Perumnas Cendakir · Bukit Belakang SDN 13 Sungai Pisang · Bukit Jalan Teluk Bayur · Bukit Kacik · Bukit Kacik Tanah Sirah · Bukit Karan (Gates Nan XX) · Bukit Karan (Taluak Bayua) · Bukit Keran · Bukit Kuburan · Bukit Lampu (Bungus Barat) · Bukit Lampu (Gates Nan XX) · Bukit Lubuk Hitam · Bukit Nila · Bukit Parak Batung · Bukit Peti-peti · Bukit SDN 13 Sungai Baremas · Bukit Simpang Rawang (Bungus Selatan) 1 dan 2 · Bukit Tanah Sirah · Bukit Tanah Sirah Kayu Aro · Gunung Padang

## Lampiran 4. TEA yang berada di dalam zona landaan (pertanyaan 15)

Indeks bahaya dari raster Peta Bahaya Tsunami KRB 2023–2027 (0–1).

| ID | Nama | Kelurahan | Indeks bahaya |
|---|---|---|---|
| TEA_001 | Bukit Simpang TPI | Bungus Barat | 0,96 |
| TEA_002 | Lapangan di Bawah Bukit | Bungus Selatan | 0,90 |
| TEA_007 | Lapangan Sungai Pisang | Teluk Kabung Selatan | 0,96 |
| TEA_009 | R.M Nenek | Teluk Kabung Tengah | 0,92 |
| TEA_010 | Halaman Polsek | Teluk Kabung Utara | 0,96 |
| TEA_011 | Kantor KAN | Teluk Kabung Utara | 0,96 |
| TEA_012 | R.M Jaso Mande | Teluk Kabung Utara | 0,96 |
| TEA_023 | Lapangan SSAG | Gates Nan XX | 0,94 |
| TEA_024 | SDN 21 Teluk Nibung | Gates Nan XX | 0,94 |
| TEA_025 | LANTAMAL | Pampangan Nan XX | 0,81 |
| TEA_026 | PGRI Convention Center | Kampung Olo | 0,70 |
| TEA_027 | Polsek Nanggalo | Kampung Olo | 0,69 |
| TEA_028 | Bank Danamon | Belakang Tangsi | 0,01 |
| TEA_029 | Dinas Pendidikan | Belakang Tangsi | 0,36 |
| TEA_030 | Tanah Hibah Masjid | Belakang Tangsi | 0,24 |
| TEA_032 | Bundaran Siti Nurbaya | Batang Arau | 0,97 |
| TEA_034 | Masjid Maryam Ranah | Ranah Parak Rumbio | 0,47 |
| TEA_039 | Mushola Jbal Tsur | Seberang Palinggam | 0,60 |
| TEA_040 | Lapangan Voli | Taluak Bayua | 0,92 |
| TEA_042 | Lapangan TVRI | Jati | 0,29 |
| TEA_043 | Dinas PU Sumatera Barat | Alai Parak Kopi | 0,88 |

## Lampiran 5. Warga yang tidak sempat ke tempat evakuasi mana pun (pertanyaan 18)

Berkas: `hasil_build/peta_celah_kelurahan.csv` (56 kelurahan; simpul jalan dan jiwa yang tidak sempat dalam 20 dan 30 menit pada 0,89 m/s). Enam kelurahan teratas menurut jiwa yang tidak sempat dalam 20 menit: Batang Kabung (12.215), Padang Sarai (11.079), Pasir Nan Tigo (5.704), Bungo Pasang (4.243), Kampung Olo (3.771), Batipuh Panjang (2.788).

---

## Setelah BPBD menjawab

| Jawaban | Yang diubah di engine (`build_db.py`) |
|---|---|
| A1, A2 (batas arah) | `ARAH_MIN_SIN`, `ARAH_JARAK_DEKAT_M` |
| A3 (bukit tepi pantai) | Pengecualian syarat arah untuk TES/TEA bukit |
| A4 (jembatan) | `JEMBATAN_MIN_M` atau daftar jembatan BPBD |
| B6, B7 (lantai) | Syarat kelayakan TES di langkah 4 |
| B8, B9, C14, C15 | `data_osm/geokode_daftar_resmi_bpbd.csv` atau data titik BPBD baru |
| B10 (bukit = TEA) | Jenis fasilitas di langkah 4 |
| B13 (daya tampung) | `M2_PER_ORANG` dan sumber kapasitas |
| D16 (garis biru) | Zona hijau di langkah 8 |

Setiap perubahan isi DB diterbitkan sebagai versi baru (`build_db.py --versi …`) dan dikabarkan ke tim Android dan backend.
