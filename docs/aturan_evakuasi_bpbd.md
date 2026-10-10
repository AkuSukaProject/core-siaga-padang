# Aturan & Konteks Evakuasi Tsunami Kota Padang (Hasil Wawancara BPBD)

Dokumen ini merangkum seluruh aturan, standar, dan konteks lapangan evakuasi tsunami Kota Padang yang diperoleh dari wawancara dengan BPBD Kota Padang. Dokumen ini menjadi rujukan utama ketika menentukan logika *routing*, parameter simulasi, isi panduan, dan desain antarmuka aplikasi Siaga Padang.

**Sumber transkrip** (folder [`wawancara bpbd/`](wawancara%20bpbd/)):

| Kode | Narasumber | Peran | Berkas |
|---|---|---|---|
| **[R]** | Pak/Bang Resko (Rizko) | Bidang Pencegahan & Kesiapsiagaan (PK); pemegang data TES/TEA, peneliti tesis tempat evakuasi tsunami | `Bang resko 1.txt`, `Bang resko 2.txt`, `wawancara bang resko.txt` |
| **[D]** | Pak Deny | Pejabat BPBD, atasan Pak Resko | `wawancara pak deny.txt` |
| **[K]** | Pak Ricky | Bidang Kedaruratan, Manajer Pusdalops | `wawancara pak ricky.txt`, `wawancara pak ricky v2.txt` |

> **Catatan keandalan.** Transkrip dihasilkan oleh *speech-to-text* dengan banyak salah dengar (logat Minang, nama tempat terdistorsi). Angka dan nama tempat yang ditandai **(perlu verifikasi)** belum pasti dan harus dikonfirmasi ke Bidang PK sebelum dipakai di proposal atau aplikasi. Jika narasumber berbeda pendapat, yang diutamakan adalah pernyataan Bidang PK [R], karena bidang itulah pemilik data dan rencana evakuasi.

---

## 1. Ringkasan Aturan Inti

Aturan berikut wajib dipatuhi oleh engine *routing*, simulasi, dan aplikasi:

1. **Batas waktu 20 menit.** Gunakan skenario terburuk: warga harus sudah tiba di TES/TEA dalam **20 menit** setelah gempa. [R]
2. **Selalu menjauhi pantai (mutlak).** TES yang dekat tetapi letaknya ke arah pantai tidak boleh dipilih. Warga harus bergerak menjauhi pantai menuju zona aman, TES, atau TEA di arah daratan. Rute juga tidak boleh berjalan sejajar pantai. [R] Implementasinya ada di 5.1.1.
3. **Rencana evakuasi tidak boleh melewati jembatan.** Jembatan dianggap runtuh pada skenario terburuk. [R] Jika jembatan adalah satu-satunya jalur, lihat kebijakan di 5.2.1.
4. **Berjalan cepat, bukan berlari, bukan berkendara.** Kendaraan hanya untuk kelompok rentan. [R][D]
5. **Peta evakuasi hanya memakai merah dan hijau.** Merah berarti harus keluar dari zona itu. Warna kuning hanya dipakai di peta kajian risiko. [R][D]
6. **Satu tanda alam saja: gempa terasa lebih dari 30 detik terus-menerus** (lemah maupun kuat), maka langsung evakuasi. Air surut **tidak** berlaku untuk Padang. [R]
7. **Jangan kembali menjemput barang atau anak di zona merah.** [R][D]
8. **TES adalah tempat transit dan TEA adalah tujuan akhir.** Setelah situasi jelas, warga bergerak dari TES ke TEA. Jika waktunya cukup, warga langsung menuju TEA. [D]

---

## 2. Definisi Istilah

| Istilah | Definisi menurut BPBD |
|---|---|
| **TES** (Tempat Evakuasi Sementara) | Tempat aman untuk berpindah sementara saat ancaman berlangsung, biasanya **evakuasi vertikal** ke gedung tinggi. Konsepnya "berpindah sementara". [R] |
| **TEA** (Tempat Evakuasi Akhir) | Tempat yang **tidak terkena bencana itu sendiri**, misalnya di atas ±18 m dpl, berupa lapangan, masjid, rumah ibadah lain, atau rumah warga yang dipinjamkan. Jika berupa tanah lapang, BPBD memasang tenda. [D] |
| **Shelter** | Tempat aman yang sudah dilengkapi **semua penunjang kehidupan** (tempat istirahat, air, tempat tidur, dll.). Konsepnya lebih dekat ke TEA daripada TES. Dalam konteks proyek ini, "shelter" dari data BPBD disamakan dengan TES. [R] |
| **Potensi shelter** | Bangunan yang diidentifikasi berpotensi menjadi shelter tetapi belum lolos verifikasi struktur. [R] |
| **Tempat pengungsian** | Lokasi pasca-kejadian di zona aman. Kriterianya: ada **sumber air** dan **mudah diakses kendaraan**. [K] |
| **Zona merah** | Zona genangan (landaan) tsunami menurut peta rencana evakuasi. Seluruh kelurahan terdampak (±52 kelurahan [R], disebut 53 oleh [D], **perlu verifikasi**) berstatus zona merah. |
| **Zona hijau / safe zone** | Area di luar landaan. Di lapangan, batasnya ditandai **cat biru pada aspal** sebagai titik ±11 m dpl. [D] |
| **Assembly point** | Titik kumpul pertama, misalnya di sekolah atau kelurahan, sebelum warga bergerak bersama ke TES/TEA. [D] |
| **Kelurahan Tangguh Bencana (Katana)** | Program pendampingan BPBD. Masyarakat menyusun sendiri rencana evakuasinya per RT/RW. [R][D] |
| **KSB** | Kelompok Siaga Bencana di kelurahan yang membantu warga bergerak ke lokasi evakuasi. [D] |

---

## 3. Waktu Evakuasi (*Golden Time*)

- Pada pemodelan, tsunami tiba sekitar **menit ke-31** setelah gempa. [R]
- Saat edukasi, BPBD menyampaikan rentang **20–30 menit** setelah gempa. [R][K]
- **Skenario terburuk yang dipakai untuk perencanaan: 20 menit.** Warga harus sudah tiba di TES **atau** TEA dalam 20 menit. Aplikasi sebaiknya mengutamakan angka 20 menit. [R]
- Pak Ricky merujuk kejadian Aceh (20–30 menit) dan menegaskan tidak ada teknologi yang bisa memastikan waktu kedatangan tsunami secara tepat. [K]

**Jika warga tidak bisa tiba dalam 20 menit** (prosedur yang dipakai BPBD saat latihan) [R]:
1. Ulangi dengan **berjalan cepat**. Jika masih tidak sampai, ulangi dengan lebih cepat lagi saat latihan berikutnya.
2. Jika tetap tidak sampai, **pindah ke tempat evakuasi lain** yang lebih dekat.
3. Jika tidak ada alternatif (kasus Koto Tangah), tetap evakuasi secepat mungkin ke tujuan yang ada.

---

## 4. Kecepatan Berjalan & Radius Layanan

| Parameter | Nilai | Sumber |
|---|---|---|
| Kecepatan berjalan orang paling lemah | **2 mph ≈ 3,22 km/jam (≈ 0,89 m/s)** | FEMA (P-646), disebut [R] (edisi 2015/2019, **perlu verifikasi**) |
| Jarak tempuh 20 menit | **±1 km** (perhitungan Pak Resko: 1,07 km) | [R] |
| Jarak tempuh 30 menit | **±1,6 km** | [R] |

Saran desain dari Pak Resko [R]:
- **Radius layanan sebaiknya berpusat pada orang, bukan pada TES.** Jika setiap ikon TES diberi lingkaran radius, peta menjadi ramai dan informasinya kabur. Lebih baik pengguna melihat lingkaran ±1 km di sekitar posisinya, sehingga langsung tahu bangunan mana yang terjangkau dalam 20 menit berjalan kaki.
- Dengan jarak yang sama, waktu tempuh bisa berbeda karena **kepadatan penduduk** (misal Padang Utara vs Padang Selatan). Kalau tidak ingin memodelkan kepadatan, cukup pakai satu parameter: kecepatan orang paling lemah.
- Radius layanan yang memperhitungkan kepadatan adalah topik penelitian lanjutan (ada kajian "kesiapan bangunan publik sebagai TES" yang bisa diikuti).

---

## 5. Aturan Rute

### 5.1 Arah: menjauhi pantai
- **Tidak boleh mendekati arah pantai.** Bangunan di dekat pantai bisa runtuh, dan warga yang sudah berjalan beberapa menit ke arah laut harus berbalik lagi sehingga waktunya habis. [R]
- **Tidak boleh sejajar pantai.** Harus bergerak menjauh, baik menuju TES maupun TEA, dan baik saat keluar dari zona merah maupun saat naik ke bangunan. [R]
- **Aturan ini mutlak, bukan sekadar preferensi.** TES yang paling dekat tetap **tidak boleh** dipilih jika letaknya ke arah pantai. Warga harus mengamankan diri dengan bergerak menjauhi pantai menuju zona aman, TES, atau TEA yang ada di arah daratan. [R]
- Jika tidak ada TES atau TEA di arah menjauhi pantai yang terjangkau dalam 20 menit, warga tetap bergerak menjauhi pantai menuju zona aman (evakuasi horizontal). Jangan memilih TES ke arah laut hanya karena lebih dekat. Ini sejalan dengan kasus Koto Tangah, tempat warga tetap evakuasi walaupun waktunya lebih dari 20 menit. [R]

#### 5.1.1 Implementasi di engine

Ukuran "arah" yang dipakai adalah **jarak ke garis pantai** (`d_pantai`), bukan arah mata angin. Dengan ukuran ini, pantai yang melengkung (misal Teluk Bayur dan Bungus) tetap tertangani dengan benar.

1. **Hitung `d_pantai` untuk setiap node** di graf, yaitu jarak ke garis pantai (poligon batimetri BPBD).
2. **Filter tujuan (aturan keras) untuk semua jenis tujuan.** TES, TEA, dan titik zona aman hanya boleh menjadi tujuan jika `d_pantai(tujuan) > d_pantai(posisi warga)`. TES yang lebih dekat ke laut daripada posisi warga dibuang dari daftar kandidat, sedekat apa pun jaraknya.
   - Untuk TES dan TEA, filter dihitung per pasangan warga–fasilitas.
   - Untuk zona aman, warga zona merah dikelompokkan per 100 m jarak pantai. Tiap kelompok punya pohon rute sendiri yang hanya menuju titik zona aman yang lebih jauh dari batas atas kelompoknya (`tb_safe_routes_v2` + `tb_safe_next_v2`). Hasilnya: semua 8.812 node zona merah punya rute zona aman, dan semuanya berakhir lebih jauh dari pantai.
3. **Kantong aman kecil bukan tujuan.** Bagian zona aman yang dikelilingi zona merah dan luasnya < 50 ha (84 kantong, 123 ha) tidak dijadikan tujuan. Warga harus keluar dari zona merah, bukan berhenti di pulau kecil di tengahnya.
4. **Bobot rute (penalti), dua lapis.** Supaya rute tidak memutar mendekati laut atau berjalan sejajar pantai:
   - setiap meter rute bergerak ke arah pantai dihitung seperti berjalan 10 m tambahan. Lapis ini mencegah rute "merayap" ke pantai lewat banyak ruas pendek yang masing-masing hanya sedikit mendekat, sedangkan jalan yang benar-benar sejajar pantai hampir tidak terkena penalti;
   - ruas yang sekaligus mendekati pantai lebih dari 50 m biayanya dikalikan 50.
   - Edge tidak dihapus. Jalan kota berbentuk grid dan sering berbelok, sehingga rute yang secara keseluruhan menjauhi pantai kadang perlu melewati ruas yang sedikit mendekat. Uji larangan total: 7,9% node zona merah (terutama Koto Tangah) kehilangan jalan keluar sama sekali.
   - Nilai penalti dipilih dari uji sensitivitas (lihat [build_db_v4.md](build_db_v4.md)).
5. **Sisa yang tidak terhindarkan dilaporkan.** Rute yang tetap sempat mendekati pantai > 50 m dicatat per node (`tb_node_info.rute_tes_mendekat_pantai_m`, `rute_aman_mendekat_pantai_m`) dan per kelurahan (`tb_kelurahan_info.jiwa_rute_aman_mendekat_pantai`). Lokasi ini diusulkan ke BPBD sebagai prioritas TES vertikal atau jalur evakuasi baru.
6. Waktu tempuh yang ditampilkan ke pengguna tetap dihitung dari panjang rute asli, bukan dari bobot penalti.

Untuk pengguna yang **sudah berada di dalam TES** atau di zona aman, aturan ini tidak berlaku lagi. Perpindahan TES ke TEA mengikuti bagian 7.

### 5.2 Jembatan
- BPBD **tidak memiliki data jembatan yang tahan gempa**. Pada skenario terburuk (Renkon/rencana kontinjensi Kota Padang dan rencana evakuasi masyarakat), **jembatan diasumsikan runtuh**. [R]
- **Dalam perencanaan, rute evakuasi tidak boleh melewati jembatan.** Jika TES terdekat harus dicapai lewat jembatan, rekomendasikan TES lain yang lebih jauh tetapi tanpa jembatan. [R]
- Saat kejadian nyata, keputusan akhir ada di masyarakat (jika jembatan ternyata utuh). Namun **rencana tetap tidak boleh melewati jembatan**. [R]

#### 5.2.1 Jika jembatan adalah satu-satunya jalur (kebijakan proyek, **perlu dikonfirmasi ke BPBD**)

BPBD tidak memberi aturan eksplisit untuk kasus ini. Kebijakan di bawah diturunkan dari tiga pernyataan BPBD: rencana tidak boleh lewat jembatan, keputusan saat kejadian ada di masyarakat, dan warga yang tidak punya alternatif tetap harus evakuasi (kasus Koto Tangah) [R].

Urutan keputusan:
1. **Evakuasi vertikal di sisi yang sama.** Arahkan ke TES atau gedung tinggi terdekat yang bisa dicapai tanpa menyeberang jembatan, walaupun lebih jauh.
2. **Jika tidak ada, lewat jembatan sebagai pilihan terakhir.** Tetap tinggal di zona merah tanpa tempat aman hampir pasti berbahaya, sedangkan jembatan runtuh baru sebatas kemungkinan. Sebaiknya menyeberang sedini mungkin, karena tsunami merambat lebih cepat lewat alur sungai. (Pertimbangan ini diambil dari kejadian tsunami di tempat lain, bukan dari wawancara.)
3. **Jika jembatan dilaporkan putus** (fitur lapor jalan oleh pengguna), arahkan ke bangunan tertinggi terdekat di sisi tersebut.

Implementasi:
- **Jembatan diberi penalti bobot yang sangat besar, bukan dihapus dari graf.** Dengan penalti besar, Dijkstra otomatis menghindari jembatan selama ada alternatif dan hanya memakainya jika tidak ada jalan lain. Jika edge dihapus, node di seberang tidak punya rute sama sekali dan aplikasi tidak bisa memberi arahan apa pun.
- Waktu tempuh yang ditampilkan ke pengguna dihitung dari panjang asli, bukan dari bobot penalti.
- Penalti hanya berlaku untuk **jembatan sungai**. Gorong-gorong atau jembatan kecil di atas saluran drainase diperlakukan sebagai jalan biasa (lihat 5.2.2).
- Di simulasi, agen yang hanya bisa selamat lewat jembatan dilaporkan sebagai kategori tersendiri, **"bergantung pada jembatan"**. Lokasi asal mereka dipetakan sebagai **kantong terisolasi**, yaitu kandidat lokasi TES vertikal baru untuk direkomendasikan ke BPBD.

#### 5.2.2 Menilai risiko jembatan

BPBD tidak memiliki data ketahanan gempa jembatan [R]. Penilaian risiko jembatan disusun dari kriteria akademik dan data yang tersedia:

| Kriteria | Dasar | Indikator praktis |
|---|---|---|
| Tipologi struktur | Kurva *fragility* HAZUS/FEMA. Jembatan satu bentang paling tahan gempa, jembatan banyak bentang dengan perletakan sederhana paling rentan. | Panjang jembatan sebagai proksi jumlah bentang |
| Era standar desain | SNI 2833:2016 memakai beban gempa jauh lebih besar dari SNI 2833:2008 | Tahun bangun: sebelum 2008 / 2008–2016 / setelah 2016 |
| Likuifaksi | Tanah permukaan Padang dominan pasir halus lepas | Atlas Zona Kerentanan Likuifaksi (Badan Geologi & BNPB, 2019), **perlu dicek cakupan Padang** |
| Bahaya tsunami di alur sungai | Tsunami merambat lewat muara sungai | Jembatan sungai besar di dalam zona merah |
| Guncangan lokal | Peta bahaya gempa | `Data BPBD/KRB Padang [2023-2027]/03_TEMATIK/Bahaya.gdb` |

Kondisi data saat ini:
- Graf `padang_full.graphml` memuat **1.044 edge** bertag `bridge=yes`. Sekitar 73% di antaranya tidak bernama dan berada di jalan `residential` atau `living_street`, jadi kemungkinan besar gorong-gorong. Panjang edge di graf sudah tergabung dengan segmen jalan di sekitarnya, sehingga tidak bisa dipakai sebagai panjang jembatan.
- Langkah berikutnya: ambil ulang jembatan dari OSM sebagai *way* terpisah, lalu tumpangkan dengan `waterway=river` untuk memisahkan jembatan sungai dari gorong-gorong.
- Data struktur jembatan (tahun bangun, bentang, nilai kondisi) dapat diminta ke pemegangnya: BBPJN Sumbar untuk jalan nasional, Dinas PUPR Sumbar untuk jalan provinsi, dan Dinas PUPR Kota Padang untuk jalan kota.

Karena data struktur belum tersedia, simulasi dijalankan dalam **tiga skenario** dan hasilnya dilaporkan sebagai rentang:
1. Semua jembatan utuh.
2. Semua jembatan sungai putus.
3. Berbasis skor risiko.

**Perlu dikonfirmasi ke BPBD:** apa yang dimaksud "jembatan" dalam aturan rencana evakuasi (hanya jembatan sungai, atau termasuk gorong-gorong), dan apakah urutan keputusan di 5.2.1 dapat diterima.

### 5.3 Moda dan cara bergerak
- **Berjalan cepat.** Kata "berlari" tidak dipakai di panduan karena berlari saat bencana berbahaya. "Berlari kecil" masih dapat diterima. [D] Simulasi BPBD pun dilakukan dengan berjalan kaki. [R]
- **Penekanan pertama: dilarang menggunakan kendaraan.** Jalan utama (misal *by pass*) sudah macet pada kondisi normal. Pemerintah juga tidak mengganti kendaraan yang rusak atau hilang. [R]
- **Pengecualian:** lansia, penyandang disabilitas, dan kelompok yang punya hambatan mobilitas boleh memakai kursi roda, sepeda motor, becak, atau mobil sesuai rencana evakuasi keluarga/kelurahannya. [R]
- Di beberapa daerah yang volume kendaraannya rendah dan landaannya pendek, kendaraan dipakai secara **situasional** (misal satu keluarga sekaligus). Ini bukan anjuran umum. [R]

### 5.4 Pembagian wilayah layanan
- Data TES versi BPBD **tidak membagi wilayah layanan**. Siapa pun yang berada di sekitar suatu gedung (misal Polda Sumbar) diasumsikan memakai gedung itu. [R]
- Rencana Kelurahan Tangguh **membagi per RT/RW** (RT 1 ke gedung X, RT 2 ke gedung Y, dst.), lengkap dengan rencana A/B/C. [R][D]
- Satu RW tidak diarahkan ke RW lain yang jauh. Setiap RW memakai TES/TEA yang dekat dengannya. [D]

---

## 6. Kriteria Tempat Evakuasi

### 6.1 Ketinggian aman
- **TES/safe zone: minimal ±11 m dpl.** Menurut kajian ahli, ketinggian rendaman berada di kisaran **11–18 m**. Titik 11 m dipetakan dengan alat, dengan berjalan dari pantai ke darat. [D]
- **TEA: di atas ±18 m dpl** atau lebih tinggi. [D]
- Pakar geologi memperkirakan tinggi gelombang di garis pantai sekitar **14–15 m**. Semakin dekat ke pantai, bangunan harus semakin tinggi. Dengan tinggi ±4 m per lantai, bangunan dekat pantai **minimal 3 lantai** dan bisa lebih. Perkiraan batas zona aman disebut sekitar SPBU Ampang **(perlu verifikasi)**. [K]
- Di beberapa lokasi landaan diperkirakan 8–10 m, sehingga **bangunan 2 lantai tidak layak** menjadi TES. [R]

### 6.2 Struktur bangunan
- Bangunan tinggi yang **belum diuji kekuatan strukturnya tidak dapat dinyatakan aman** oleh BPBD, termasuk sekolah yang mengklaim dirinya shelter. [D]
- "Aman dari gempa" tidak sama dengan "aman dari tsunami". Contohnya kantor BCA Sawahan, yang mengklaim aman padahal yang dimaksud hanya ketahanan gempa. [D]
- Jika bangunan berada tepat di jalur patahan, sekuat apa pun strukturnya tetap bisa runtuh. Kejadian 2009 menjadi contohnya (Hotel Ambacang dan hotel lain di Padang). [D][K]
- Saran kepada sekolah yang mengklaim aman: tetap siapkan rencana cadangan jika sebagian gedung runtuh. Misalnya sebagian siswa naik ke bagian yang masih berdiri, sisanya langsung berjalan ke zona aman. [D]

### 6.3 Identifikasi gedung oleh BPBD
| Kajian | Parameter | Hasil |
|---|---|---|
| **BPBD Bidang RR, 2019** (data resmi yang biasa diberikan BPBD) | 5 parameter: administrasi & manajemen gedung, daya tampung, akses masuk bangunan, uji kelayakan struktur, kepemilikan | ±59–60 bangunan |
| **Tesis Pak Resko** (rujukan pribadi, bukan atas nama BPBD) | 23 parameter (FEMA, SNI, dll.) | **26 layak**: 3 shelter khusus + 7 bangunan publik + 16 bangunan berpotensi. Ke-26 bangunan ini sudah termasuk dalam data 2019. |

- Daya tampung pada data 2019 dihitung dengan beberapa standar luas per orang: **0,5 m², 1 m², dan 2 m² per orang** (untuk perbandingan). [R]
- Shelter milik pemerintah yang pasti ada: shelter Tabing, Ulak Karang, dan beberapa lainnya **(nama perlu verifikasi)**. Ada juga gedung swasta/instansi yang sudah ber-MoU, misalnya Kantor Gubernur, Polda, dan Plaza Andalas **(perlu verifikasi)**. [K]
- TES di dalam zona merah tetap sah, misalnya Rusunawa Pantai Padang. [D]

### 6.4 Data lama yang tidak boleh dipakai
- Peta dengan **base data 2013 sudah tidak relevan**, termasuk jalurnya. [R]
- Peta 2014 dan revisi 2017 masih memuat kesalahan. Contohnya **SMP 4** dan sebuah SMP lain yang hanya 2 lantai ditandai sebagai shelter (hijau) atau potensi shelter (kuning). [R]
- Data InaRISK diunggah ulang tidak sesuai tahun pembuatannya, sehingga kebenarannya perlu dicek. [R]

### 6.5 Tempat evakuasi versi masyarakat
- Dalam program Kelurahan Tangguh, masyarakat mengidentifikasi sendiri TES dengan asumsi: **bangunan yang berdiri sejak/selamat dari gempa 2009 dan lebih dari 3 lantai**. Hasilnya berupa toko, rumah warga, masjid, dan gedung lain, yang **banyak tidak ada di data BPBD**. [R]
- Contoh Kampung Pondok: ±6.000 orang beraktivitas di sana, dan semuanya sudah dibagi habis ke bangunan-bangunan lokal. Contoh nama bangunannya adalah Masjid Ansarullah, gedung Suzuki, Menara Agung, dan Pondok Minang. [R]
- Cakupan program: **32 dari 52 kelurahan** terdampak sudah didampingi, dan **±25 di antaranya sudah punya rencana evakuasi** lengkap dengan TES dan TEA. [R]
- **Drill serentak November 2025**: ±70.000–80.000 peserta. Workshop sebelumnya dihadiri ±1.000 perwakilan (±20 orang per kelurahan: RT, RW, LPM, relawan) dan menghasilkan **kesepakatan TES/TEA baru**. Data ini sudah didigitasi oleh Bang Dio (GIS BPBD). [R]
- Menggabungkan **data resmi BPBD** dengan **data persepsi masyarakat** dinilai sebagai **nilai tambah** untuk lomba. [R]

---

## 7. Alur TES ke TEA

- Warga yang berada di TES **menunggu kepastian** apakah gempa memicu tsunami. Jika memicu, mereka bergerak ke TEA. [D]
- Kegagalan yang pernah terjadi: warga **turun kembali** dari TES karena ada anggota keluarga yang belum datang. [D]
- **Jika waktunya cukup, langsung menuju TEA** dan jangan menumpuk di TES (contoh arahan: "arahkan ke Gadut"). [D]
- KSB dan tokoh masyarakat yang dibina melalui Kelurahan Tangguh membantu mengarahkan warga ke lokasi yang sudah disepakati. [D]
- Pusdalops perlu mengetahui **berapa orang dan dari mana saja** warga yang berada di tiap TES/TEA untuk distribusi logistik ke posko pengungsian. [K]

---

## 8. Kelompok Rentan

- BPBD **tidak memiliki prosedur resmi tunggal**, karena kondisi tiap daerah berbeda. Namun lansia dan penyandang disabilitas memiliki hak yang sama untuk selamat. [R]
- Rencana evakuasi Kelurahan Tangguh mencatat **siapa yang mengevakuasi** (umumnya keluarga atau tetangga sesuai kesepakatan), alat bantunya (kursi roda/motor/becak/mobil), jumlah jiwa per RT, lokasi TES, rencana A/B/C, rute, estimasi waktu tempuh, dan lokasi TEA. [R]
- Prioritas rumah ibadah sebagai tempat evakuasi diberikan kepada **perempuan, bayi, dan lansia uzur**. [D]
- Rumah ibadah harus terbuka bagi semua pengungsi tanpa memandang agama, dan cara penyampaiannya harus hati-hati. [D]

---

## 9. Rencana Evakuasi Keluarga

- **Jangan menjemput anak ke sekolah di zona merah saat gempa.** Orang tua yang menjemput berisiko besar menjadi korban. [D]
- Ajarkan anak sejak masa tenang ke mana ia harus pergi dari sekolahnya dan di mana ia menunggu orang tua. [D]
- Fitur "Rencana Keluarga" di aplikasi (titik temu keluarga yang disusun saat masa tenang) **didukung BPBD**. Kalimatnya jangan kaku, agar orang tua tidak memaksa anak pulang ke rumah. [D]
- Masukan pengembangan: izinkan pengguna memasukkan **lokasi kustom** sebagai tujuan, misalnya rumah saudara di luar zona landaan (contoh: Simpang Haru), karena di lapangan banyak warga mengungsi ke rumah kerabat. [R]
- Pak Ricky mengingatkan bahwa secara naluri orang akan **mencari keluarga dulu**. Karena itu rencana keluarga yang disepakati sebelumnya sangat penting. [K]

---

## 10. Tanda Alam & Pemicu Evakuasi

- **Untuk Kota Padang, air surut tidak dapat dijadikan tanda tsunami.** Menurut pemodelan, Kepulauan Mentawai naik sementara daratan pesisir barat Sumatera turun, sehingga surutnya air tidak akan terlihat. Kondisi ini berbeda dengan Aceh yang tidak memiliki pulau penghalang. [R]
- **Gunakan satu tanda saja:** **gempa yang dirasakan lebih dari 30 detik secara terus-menerus, baik pelan maupun kuat.** Gempa seperti ini berpotensi tsunami dan warga harus langsung evakuasi. [R]
  - Dasar pemodelan: gempa M7 berdurasi 2 menit atau M8 berdurasi 1 menit dapat memicu tsunami. Untuk Padang, ambang yang dipakai adalah **30 detik** sebagai margin keselamatan. [R]
  - Contoh: gempa Mentawai 2010 terjadi malam hari dan terasa lemah, tetapi menelan ±500 korban jiwa akibat tsunami. [R]
- Suara gemuruh bersifat kasuistik dan tidak dijadikan tanda utama. [R]
- Kekuatan gempa naik 1 magnitudo berarti energinya **±32 kali lipat** (gempa 2009 M7,6). Ini dipakai untuk edukasi. [R]

> **Tidak diadopsi:** Pak Ricky menyebut bahwa tsunami harus didahului gempa susulan [K]. Pernyataan ini bertentangan dengan acuan Bidang PK dan tidak memiliki dasar rujukan. Jangan gunakan pernyataan ini sebagai syarat pemicu di aplikasi.

---

## 11. Panduan Tindakan untuk Masyarakat (Teks Aplikasi)

Prinsip penulisan: **singkat**, karena orang hanya bisa mengingat ±3 hal. Pakai ilustrasi dan jangan terlalu banyak informasi. [R]

### Saat guncangan
- **Jika bisa keluar ruangan, segera keluar.** Jika tidak bisa, **berlindung**: merunduk, berlindung di bawah meja sambil berpegangan pada kaki meja, atau di sudut ruangan sambil melindungi kepala. Jauhi kaca dan benda yang bisa jatuh. [R][D]
- Berlindung tidak harus selalu di bawah meja. **Prioritasnya: selamat dari gempa dulu, baru dari tsunami.** [R]
- **Di lantai 3 ke atas: jangan turun saat gempa, naik ke atas.** Di lantai 1–2, boleh langsung keluar jika yakin sempat. Contohnya Hotel Ambacang 2009, tempat banyak korban jatuh karena turun dari lantai 3 ke kolam renang di lantai 1. [K]
- **Jangan panik.** [K]

### Setelah guncangan (berlangsung lebih dari 30 detik)
- **Segera keluar bangunan dan langsung evakuasi.** [R]
- **Cek informasi resmi di HP sambil berjalan**, jangan berhenti untuk membaca. [R]
- **Jangan kembali menjemput barang.** [R][D]

### Saat evakuasi
- **Berjalan cepat, jangan berlari**, dan jangan berebut. Ikuti rambu evakuasi. [R][D]
- Menjauhi pantai. [R]

### Di tempat evakuasi
- Tetap di tempat evakuasi sambil menunggu informasi resmi dari **BMKG, BPBD, atau Pemerintah Kota (Diskominfo)**. [R]
- Ikuti arahan petugas atau koordinator (guru di sekolah, tokoh masyarakat atau KSB di kelurahan). [D]

---

## 12. Sistem Peringatan Dini

- **Sirene EWS tsunami ±37 titik** yang mencakup hampir seluruh pesisir dari Koto Tangah sampai Bungus. Sirene berbunyi untuk gempa berpotensi tsunami (ambang disebut M≥7, **perlu verifikasi**) dan memakai panel surya sehingga tetap berfungsi saat listrik padam. Sirene diuji **setiap tanggal 26** bersama EWS banjir. [D]
- BMKG mengirimkan **SMS blast**, dan Pusdalops memandu masyarakat lewat radio (frekuensi Pusdalops), media, dan Instagram kebencanaan. [R][K]
- **API BMKG bersifat publik dan boleh dipakai dengan mencantumkan sumber "BMKG".** [K]
- Saran fitur: **pop-up peringatan layar penuh** seperti sistem di Jepang, yang berbunyi berulang sampai aplikasi dibuka. Fitur ini berguna karena ada warga yang tidak merasakan gempa. [R]
- Sumber informasi resmi tidak hanya BMKG, tetapi juga BPBD dan Pemkot. [R]

---

## 13. Kondisi Lapangan dari Latihan (Drill)

- Tingkatan latihan BPBD: sosialisasi, workshop, latihan di ruang/TTX (latihan memakai peta untuk menguji berapa jauh warga tiba dalam 2 atau 5 menit), lalu drill lapangan. [R]
- **Hasil waktu tempuh:** sebagian besar peserta tiba dalam **20–30 menit**, dengan ±90% tepat waktu **(perlu verifikasi)**. [R]
- **Pengecualian Koto Tangah:** daerah ini minim bangunan tinggi sehingga warga harus keluar ke zona hijau. Contohnya rute dari sebuah SD ke **Kantor SAR yang memakan ±45 menit**, sementara alternatif TES lain tidak ada. [R]
- **Bottleneck:** sejauh ini **tidak ada bottleneck di sepanjang jalur**. Penumpukan terjadi di **pintu masuk atau tangga TES** saat ribuan orang (siswa, mahasiswa, warga) masuk bersamaan. [R]
- **Hambatan terbesar adalah mengajak masyarakat.** Banyak warga apatis karena belum pernah menjadi korban, menganggap evakuasi hanya "lari-larian", atau enggan ikut tanpa uang transport atau makan. [R]
- **BPBD tidak punya data sebaran penduduk siang dan malam.** Yang tersedia hanya data jumlah penduduk. [R]

---

## 14. Masukan Desain Aplikasi dari BPBD

| Masukan | Narasumber |
|---|---|
| Peta mode evakuasi cukup merah dan hijau. Jangan ada "merah 1, merah 2". Masyarakat Padang sudah paham arti merah. | [R][D] |
| Prinsip "satu instruksi pada satu waktu", dengan teks panduan singkat dan berilustrasi | [R] |
| Tampilkan nama jalan di peta offline karena warga tidak tahu posisinya tanpa nama jalan | [K] |
| Urutkan daftar TES berdasarkan jarak dari posisi pengguna, bukan daftar semua TES | [K] |
| Validasi ulang zona. Contohnya bukit di dekat Masjid Al-Hakim yang ditandai "bahaya tinggi" dan perlu dicek | [K] |
| Tampilkan radius ±1 km (20 menit berjalan) di sekitar pengguna | [R] |
| Label "diragukan" pada bangunan TES harus netral agar tidak menyudutkan pemilik gedung tertentu | [D] |
| Laporan jalan tidak bisa dilewati dilakukan manual oleh pengguna. Pastikan fitur ini tetap berfungsi tanpa internet. | [K] |
| Pop-up peringatan layar penuh dari data BMKG | [R] |
| Input lokasi kustom (rumah kerabat) di rencana keluarga | [R] |

---

## 15. Sumber Data yang Disarankan BPBD

| Data | Keterangan | Cara memperoleh |
|---|---|---|
| Tabel TES/TEA BPBD 2019 (5 parameter) | Data resmi "atas nama BPBD" | Bidang PK, Pak Resko |
| Daftar 26 bangunan layak (tesis) | Pembanding, tidak atas nama BPBD | Pak Resko |
| Rencana evakuasi Kelurahan Tangguh | ±25 kelurahan; TES, TEA, rute per RT | Link laporan dari Pak Resko |
| TES/TEA hasil workshop Drill 2025 | Sudah didigitasi dalam GIS | Bang Dio (GIS BPBD) |
| Peta di website Padang Sigap | Hanya format JPEG | Website Padang Sigap |
| Data di folder `Data BPBD/` | `Daftar Shelter OK.xlsx`, KRB Padang 2023–2027 | Sudah tersedia di repo |

---

## 16. Kesesuaian dengan Engine Saat Ini

Status per 10 Oktober 2026. Pembangun DB sekarang adalah [`build_db.py`](../build_db.py) (keluaran `ranah_siaga_v4.db`), menggantikan rantai lama `core.py` → `build_db_v2_with_tea.py` → `spatial/1..4` (diarsipkan di `legacy/pipeline_db/`). Rincian teknisnya ada di [build_db_v4.md](build_db_v4.md).

| Aturan BPBD | Kondisi engine (`build_db.py`) | Status |
|---|---|---|
| Batas waktu 20 menit | `BATAS_WAKTU_MENIT = 20`; tujuan ≤ 20 menit dialokasikan lebih dulu | ✅ Sesuai |
| Kecepatan acuan orang terlemah (FEMA, ±1 km / 20 menit) | `KECEPATAN_JALAN_MS = 0.894` (3,22 km/jam) untuk semua ETA | ✅ Sesuai |
| Tujuan harus menjauhi pantai | Filter keras untuk TES, TEA, dan zona aman (`tb_safe_routes_v2`): 100% tujuan lebih jauh dari pantai daripada posisi warga. Kantong aman < 50 ha bukan tujuan. Garis pantai dari batimetri BPBD. | ✅ Sesuai |
| Rute tidak mendekati/sejajar pantai | Penalti 10 m per meter mendekat + ×50 untuk ruas yang mendekat > 50 m. Sisa rute yang terpaksa mendekat > 50 m: TES rank-1 13,8%, zona aman 11,2% node zona merah (> 200 m: 2,8% dan 1,7%), terutama di Koto Tangah, karena jalannya memang hanya ke arah itu. Dicatat per node & kelurahan. | ⚠️ Sesuai sejauh jaringan jalan memungkinkan |
| Rute tidak melewati jembatan | Jembatan sungai (tag OSM `bridge` yang memotong poligon sungai BPBD) diberi penalti ×20, tidak dihapus. Ketergantungan jembatan dicatat di `tb_node_info`. | ✅ Sesuai kebijakan 5.2.1 (masih perlu konfirmasi BPBD) |
| Zona merah = area landaan | `is_safe` dan poligon zona merah diambil dari raster `Peta_Bahaya_Tsunami` KRB 2023–2027 | ✅ Sesuai |
| Peta evakuasi hanya merah/hijau | `tb_inundation_zones.tingkat_bahaya` diisi `Tinggi` untuk semua zona merah | ✅ Sesuai |
| TEA tidak terkena bencana | TEA yang titiknya berada di area landaan dikeluarkan dari routing (21 titik, lihat laporan build) | ✅ Sesuai, daftar perlu dikonfirmasi BPBD |
| Data TES bangunan ≤ 2 lantai atau "tidak potensial" dikeluarkan | Dicocokkan dengan verifikasi BPBD 2019 (Universitas Taman Siswa keluar karena "tidak potensial"). Hanya sebagian TES yang punya data lantai. | ⚠️ Sebagian (data lantai 2025 belum ada) |
| TEA tanpa batas kapasitas, TES *capacity-aware* | Penugasan greedy di `tb_route_shares` | ✅ Sesuai |
| Daya tampung per orang | Urutan sumber: BPBD 2025 → verifikasi 2019 → jejak bangunan RTRW × (lantai − 2) / 1 m² per orang → median. Estimasi ditandai di `kapasitas_sumber`. | ⚠️ Kapasitas 75 TES masih estimasi |
| Ikuti jalur/rambu evakuasi | Ruas di jalur evakuasi resmi BPBD diberi faktor biaya 0,8 | ✅ Sesuai |
| Ketinggian safe zone ≥ 11 m (TES) / ≥ 18 m (TEA) | Tidak ada data elevasi; `tb_safe_zones.elevasi_m` dikosongkan | ⚠️ Butuh DEM |
| Istilah "berjalan cepat" | Sudah ditetapkan di kebijakan UI | ✅ Sesuai |
