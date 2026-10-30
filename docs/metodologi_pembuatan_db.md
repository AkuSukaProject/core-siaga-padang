# Aturan, Konteks, dan Metode Pembuatan Database Siaga Padang

Dokumen ini merangkum dalam satu tempat **mengapa**, **berdasarkan aturan apa**, dan **dengan metode apa** basis data `ranah_siaga_v4.db` dibangun. Angka mengacu pada **DB versi 2026.10.18** (graf OSM 8 Agustus 2026). Rincian teknis tiap bagian tetap ada di dokumen sumbernya (lihat [§9](#9-rujukan-dokumen)); bila ada perbedaan, dokumen sumber dan `tb_metadata` di DB yang berlaku.

---

## 1. Tujuan dan Ruang Lingkup

`ranah_siaga_v4.db` adalah basis data SQLite yang dibawa aplikasi Android Siaga Padang secara **luring**. Isinya rute evakuasi tsunami yang **dihitung di depan** (*pre-computed offline routing*) dari setiap simpang jalan di zona merah Kota Padang menuju:

- **TES** (Tempat Evakuasi Sementara): evakuasi vertikal ke gedung, berkapasitas terbatas;
- **TEA** (Tempat Evakuasi Akhir): evakuasi horizontal ke lahan tinggi/terbuka, tidak dibatasi kapasitas;
- **zona aman (zona hijau)**: area di luar landaan tsunami.

Aplikasi tidak menjalankan algoritma graf. Aplikasi hanya membaca tabel, lalu merangkai rute dari daftar simpul atau tabel *next-hop*. Simulasi kanonis (`analisis/simulasi_resmi_padang.py`) membaca DB yang sama, jadi aplikasi dan evaluasi akademik memakai data dan aturan yang identik.

---

## 2. Konteks

### 2.1 Masalah

- Kota Padang berhadapan langsung dengan zona megathrust Mentawai. Pada pemodelan BPBD, tsunami tiba sekitar menit ke-31 setelah gempa; untuk perencanaan, BPBD memakai **skenario terburuk 20 menit**.
- Zona merah mencakup ±7.272 ha daratan dengan **313.943 jiwa** (242.750 jiwa terpapar menurut KRB 2023–2027, ditambah perkiraan 71.193 jiwa di zona tambahan peta evakuasi BPBD).
- Saat darurat, jaringan seluler bisa terputus, sehingga rute harus tersedia di HP tanpa internet.
- Tanpa panduan, warga cenderung menuju tempat terdekat. Dalam simulasi, cara itu membuat 104 dari 244 TES kelebihan beban, dan sebagian tempat terdekat justru berada ke arah laut.

### 2.2 Pemangku kepentingan dan pembagian kerja

| Pihak | Peran terhadap DB |
|---|---|
| BPBD Kota Padang (Bidang PK, Kedaruratan/Pusdalops, Bidang RR) | Pemilik data (KRB, TES/TEA, jalur evakuasi, verifikasi gedung) dan sumber aturan evakuasi melalui wawancara |
| Tim core engine (repo ini) | Membangun DB dengan `build_db.py`, menjalankan simulasi kanonis, menulis dokumentasi |
| Tim aplikasi Android (repo `siagapadang`) | Pemilik **kontrak DB** (`docs/PEMBAGIAN_TUGAS_BPBD.md` §1 asumsi kerja K-B1–K-B8, §2.1 isi DB), pemakai DB lewat Room |
| Tim backend | Mendistribusikan berkas DB (zip + manifest + checksum) ke aplikasi |

### 2.3 Dua acuan wajib

1. **Aturan evakuasi BPBD** dari wawancara: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md). Bila narasumber berbeda pendapat, yang diutamakan adalah Bidang PK, pemilik data dan rencana evakuasi.
2. **Kontrak DB aplikasi**: nama tabel, kolom, satuan, dan asumsi kerja yang disepakati dengan tim Android. Bila kontrak berubah, engine disesuaikan dan **versi DB baru diterbitkan**. Satu label versi tidak boleh dipakai untuk dua isi DB.

### 2.4 Riwayat singkat

Pipeline lama (`core.py` → `build_db_v2_with_tea.py` → `spatial/`) memakai data TES 2013–2019, zona merah per kelurahan, dan laju 1,2 m/s. Menurut BPBD, data tersebut sudah tidak relevan. Pipeline itu kini diarsipkan di `legacy/pipeline_db/` dan diganti oleh satu skrip, `build_db.py`.

---

## 3. Sumber Data

### 3.1 Data yang dipakai

| Data | Sumber | Fungsi dalam DB |
|---|---|---|
| Titik TES & TEA 2025 | BPBD, `2_TES_TEA_Padang.shp` (digitasi staf GIS atas kesepakatan Kelurahan Tangguh) | Daftar fasilitas dan kapasitas utama |
| Daftar resmi shelter 2019 | BPBD Bidang RR, `Daftar Shelter OK.xlsx` sheet `TES OK` + geokode OSM | Penentu `sumber = BPBD`, lantai, kapasitas |
| Verifikasi gedung 2019 | BPBD, sheet `TES (verifikasi)` | Lantai, kapasitas, status "tidak potensial" |
| Raster bahaya tsunami | BPBD, KRB 2023–2027 `Bahaya.gdb` → `Peta_Bahaya_Tsunami` (sel 30 m) | Zona merah, `is_safe`, kelayakan TEA |
| Peta evakuasi BPBD (Blue Line) | BPBD, `Peta TES dan Potensial Shelter.png` 1:15.000, didigitasi | Zona merah tambahan di luar landaan KRB |
| Batas kelurahan, jejak bangunan | BPBD, `Basemap.gdb` (190.556 bangunan RTRW) | Kelurahan simpul/fasilitas, sebaran penduduk |
| Tabel KRB per kelurahan | BPBD, `FINAL MATRIKS KRB KOTA PADANG - DOKUMEN.xlsx` | Jumlah penduduk terpapar |
| Jalur evakuasi resmi per RT/RW | BPBD, `Jalur_evakuasi_Padang.shp` | Ruas resmi diutamakan |
| Jaringan jalan pejalan kaki | OpenStreetMap lewat OSMnx (`network_type="walk"`), 8 Agustus 2026 | Graf routing: 31.813 simpul, 39.216 ruas |
| Garis pantai | OSM `natural=coastline` | `jarak_pantai_m`, syarat arah, pemotongan zona ke daratan |
| Jembatan | OSM `highway` + `bridge` (602 *way*) | Ruas jembatan ≥ 20 m |

### 3.2 Aturan sumber data

- **Data BPBD adalah sumber utama.** Data lama (peta 2013/2014/2017 dan CSV turunannya) tidak boleh dipakai untuk produksi.
- **Data sumber tidak diubah.** Koreksi seperti duplikat, salah ketik, atau kapasitas kosong dilakukan di dalam skrip dan dicatat (`kapasitas_sumber`, `alasan_tidak_dipakai`). Data yang meragukan dilaporkan ke BPBD ([pertanyaan_bpbd.md](pertanyaan_bpbd.md)).
- **Kapasitas TES tidak dikarang.** Kolom `tb_tes.kapasitas` hanya diisi dari data BPBD, dengan urutan 2025 → daftar resmi 2019 → verifikasi 2019. Bila tidak ada, kolom dibiarkan kosong (77 dari 244 TES). Estimasi dari jejak bangunan hanya dicatat sebagai pembanding di `tb_fasilitas_info`.
- **Proyeksi.** Jarak dan luas dihitung di UTM 47S (`EPSG:32747`). Koordinat yang disimpan memakai WGS84 (`EPSG:4326`).
- **Pencocokan nama.** Nomor di nama gedung harus sama persis (SMPN 3 ≠ SMPN 36). Kemiripan teks saja tidak cukup.

Inventaris lengkap, termasuk data yang tidak dipakai beserta alasannya, ada di [build_db_v4.md](build_db_v4.md).

---

## 4. Aturan yang Diterapkan

### 4.1 Dari aturan BPBD ke parameter engine

| Aturan BPBD / kontrak | Bentuk di engine | Nilai | Konstanta |
|---|---|---|---|
| Batas waktu skenario terburuk | Tujuan dinilai terhadap batas 20 menit | 20 menit | `BATAS_WAKTU_MENIT` |
| Laju orang terlemah (FEMA P-646, K-B3) | Semua keputusan engine dan simulasi | 0,894 m/s | `KECEPATAN_JALAN_MS` |
| Batas "sempat" (K-B6) | 20 menit dikurangi cadangan 5 menit | 15 menit riil (eta tabel ≤ 11,175) | `BATAS_SEMPAT_MENIT` |
| Satuan kolom ETA (kontrak §2.1) | `rank_k_eta`, `safe_eta`, `eta_tabel` disimpan pada laju tabel; waktu riil = eta × 1,2 ÷ 0,894 | 1,2 m/s | `KECEPATAN_TABEL_MS` |
| **Selalu menjauhi pantai, tidak boleh sejajar (mutlak, K-B1)** | Filter keras: (jarak pantai tujuan − asal) ÷ jarak lurus > 0,27 (≈ sin 15° + margin). Tujuan ≤ 100 m tidak dinilai. Tidak pernah dilonggarkan | 0,27; 100 m | `ARAH_MIN_SIN`, `ARAH_JARAK_DEKAT_M` |
| Jalur tidak memutar ke arah laut | Penalti biaya: +10 m per meter mendekat pantai; ruas yang mendekat > 50 m dikali 50 | 10; 50 m; ×50 | `BOBOT_PER_METER_MENDEKAT_PANTAI`, `TOLERANSI_MENDEKAT_PANTAI_M`, `PENALTI_MENDEKAT_PANTAI` |
| Rencana tidak boleh lewat jembatan (K-B2) | Jembatan ≥ 20 m dikeluarkan dari graf utama. Graf cadangan (×20) hanya dipakai bila tujuan tak terjangkau tanpa jembatan | 20 m; ×20 | `JEMBATAN_MIN_M`, `PENALTI_JEMBATAN` |
| Ikuti jalur evakuasi resmi | Ruas yang ≥ 80% berada ≤ 15 m dari jalur BPBD mendapat faktor biaya 0,8 | 15 m; ×0,8 | `JALUR_RESMI_JARAK_M`, `JALUR_RESMI_FAKTOR` |
| Peta evakuasi hanya merah/hijau | Zona merah = landaan KRB ∪ zona rawan peta evakuasi. Selain itu zona hijau | – | – |
| Kantong aman kecil bukan tujuan | Bagian aman yang dikelilingi zona merah dan < 50 ha tidak dijadikan tujuan | 50 ha | `LUAS_MIN_ZONA_AMAN_HA` |
| TEA tidak terkena bencana | TEA di dalam zona merah dikeluarkan | – | – |
| Gedung tidak layak | TES berstatus "tidak potensial" di verifikasi BPBD 2019 dikeluarkan. Jumlah lantai tidak dijadikan syarat sendiri; engine mengikuti penilaian BPBD | – | – |
| Sumber fasilitas (K-B5) | `BPBD` bila cocok dengan daftar resmi 2019, selain itu `WARGA`. Keduanya dipakai routing | – | – |
| Nama fasilitas unik (H-1) | Nama dan jenis sama dalam ≤ 100 m digabung; nama sama di lokasi berbeda diberi kelurahan | 100 m | `GABUNG_JARAK_M` |
| TES dibatasi kapasitas, TEA tidak | Porsi TES lewat program linear dengan beban ≤ kapasitas. TEA dan zona aman tanpa batas | – | – |

Semua parameter di atas juga ditulis ke tabel `tb_metadata`, sehingga setiap DB membawa aturan yang dipakai untuk membangunnya.

### 4.2 Kaidah pemilihan tujuan (K-B6, keputusan tim 12 Oktober)

1. Bila **TEA atau zona hijau sempat** (≤ 15 menit riil), keluar zona lebih dulu dan pilih yang **terjauh dari pantai**.
2. Bila tidak, pilih **TES** dari porsi berkapasitas (`tb_route_shares`) di antara yang sempat.
3. Bila tidak ada yang sempat, pilih **tujuan tercepat** yang lolos syarat arah.
4. Rute tanpa jembatan ≥ 20 m selalu didahulukan. Semua tujuan wajib lolos syarat arah.
5. Urutan `rank_1..3` (TES) dan `nearest/alt` (TEA): terjauh dari pantai di antara yang ≤ 20 menit, lalu yang tercepat.

Cadangan 5 menit menampung waktu gempa yang meleset, orang yang lebih lambat, dan jalan yang tertutup. Tanpa cadangan, 27,7% warga tiba di 5 menit terakhir; dengan cadangan, angkanya 8,5%.

### 4.3 Aturan antarmuka yang memengaruhi isi DB

- Istilah yang dipakai adalah **"berjalan cepat"**, bukan "berlari".
- Saat darurat, tidak ada peringatan kepadatan di layar navigasi (prinsip satu instruksi pada satu waktu). Angka kapasitas hanya tampil di direktori fasilitas saat masa tenang. Kapasitas kosong ditulis "belum ada data", bukan 0.

---

## 5. Metode

Seluruh langkah dijalankan oleh satu skrip, `build_db.py`, dalam ±2,5–3 menit.

```
Data BPBD/ ──────────────┐
OSM (graf, pantai, jembatan) ──┼─► build_db.py ─► hasil_build/ranah_siaga_v4.db (+ zip, manifest, CSV laporan)
aturan BPBD + kontrak DB ──────┘
```

### 5.1 Penyiapan data dasar

- Batas kelurahan, jejak bangunan, dan raster bahaya dibaca dari geodatabase BPBD (`rasterio`, `geopandas`), lalu ditransformasikan ke UTM 47S.
- Angka dibersihkan (koma desimal, teks seperti "3000 Jiwa"). Koordinat 0, NaN, atau di luar wilayah dibuang.

### 5.2 Pembentukan zona merah dan zona hijau

1. Raster `Peta_Bahaya_Tsunami` diubah menjadi poligon dengan **kontur sub-piksel**, sehingga tepinya mengikuti raster tanpa bentuk tangga 30 m.
2. Poligon digabung dengan **zona rawan peta evakuasi BPBD** yang didigitasi (+1.108 ha, terutama Padang tengah dan utara).
3. Poligon dipotong ke daratan menurut garis pantai OSM, sehingga tidak ada zona di laut.
4. Lubang kering dan serpihan hijau < 1 ha yang dikelilingi zona merah ikut menjadi merah.
5. Pita pantai di luar batas kelurahan dibagi ke kelurahan terdekat. Zona hijau = daratan kelurahan − zona merah. Kantong hijau < 50 ha ditandai sebagai bukan tujuan.
6. Hasilnya disimpan sebagai WKT `MULTIPOLYGON` 2D dengan 7 desimal (`tb_inundation_zones` 68 poligon, `tb_safe_zones` 81 poligon).

Poligon yang sama dipakai untuk `is_safe` simpul, kelayakan TEA, dan sebaran penduduk, sehingga peta dan rute selalu sepakat (0 simpul yang `is_safe`-nya berbeda dengan poligon).

### 5.3 Atribut simpul

Setiap simpul graf diberi:

- `is_safe` (0 = di zona merah): 11.418 simpul merah, 20.395 simpul aman;
- `jarak_pantai_m` ke garis pantai OSM;
- kelurahan dari batas administrasi BPBD.

### 5.4 Graf berbobot berarah

Graf OSM tak berarah dijadikan dua arah karena biayanya bergantung pada arah gerak:

```
biaya = (panjang / 0,894)
        + penalti mendekat pantai (+10 m per meter mendekat; ×50 bila mendekat > 50 m)
        × 0,8 bila ruas mengikuti jalur evakuasi resmi
```

Dibentuk dua graf: **graf utama** tanpa jembatan ≥ 20 m dan **graf cadangan** dengan jembatan berbiaya ×20. Penalti hanya memengaruhi *pilihan* rute. Waktu tempuh yang disimpan selalu dihitung dari panjang jalan asli.

### 5.5 Penyiapan fasilitas

1. Duplikat persis dibuang (366 → 280 titik), dan titik di luar Kota Padang dikeluarkan.
2. TES dicocokkan dengan daftar resmi 2019 (nama, lokasi sama, atau geokode OSM) untuk menentukan `sumber`, lantai, dan kapasitas.
3. TES "tidak potensial" dan TEA di zona merah dikeluarkan, alasannya dicatat di `tb_fasilitas_info`.
4. Nama dibuat unik tanpa menggeser ID.

Hasilnya: **244 TES** (45 BPBD, 199 WARGA; 167 berkapasitas) dan **22 TEA**.

### 5.6 Reverse Dijkstra per fasilitas

Untuk setiap TES/TEA, Dijkstra dijalankan pada **graf terbalik** (`scipy.sparse.csgraph.dijkstra`). Satu kali pencarian memberi biaya dari *semua* simpul menuju fasilitas tersebut. *Predecessor* pada graf terbalik adalah *next-hop* pada rute asli. Waktu riil dan penanda jembatan diakumulasi dengan *pointer jumping*. Bila tujuan tak terjangkau di graf utama, graf cadangan dipakai.

### 5.7 Filter arah dan pemeringkatan

Untuk setiap pasangan simpul merah–fasilitas, syarat arah (§4.1) diperiksa sebagai **filter keras**. Kandidat yang lolos diurutkan menurut kaidah §4.2. Rank 2 dan 3 boleh kosong; 730 simpul tidak punya TES yang lolos dan tetap punya TEA atau zona aman.

### 5.8 Rute zona aman

- **v2 (navigasi, `tb_safe_routes_v2`/`tb_safe_next_v2`):** Dijkstra maju dari setiap simpul merah ke semua titik zona hijau (bukan kantong). Dipilih titik **terdalam** (terjauh dari pantai) yang sempat ≤ 15 menit dan lolos arah. Bila tidak ada, dipilih batas zona hijau yang **tercepat** dicapai. Rantai disimpan per titik tujuan (`kelompok`). Seluruh 11.418 simpul merah mendapat rute.
- **Tabel kontrak lama (`tb_safe_routes`/`tb_safe_next`):** satu pohon global dari semua simpul aman. `safe_eta = 0` menandai tiba di zona hijau. Tabel ini dipakai untuk status tiba dan kompatibilitas.

### 5.9 Sebaran penduduk (demand)

Jiwa terpapar per kelurahan (tabel KRB) disebar ke bangunan di zona merah menurut luas jejak bangunan, lalu ke simpul terdekat (9.844 simpul, 81.749 bangunan). Untuk zona tambahan peta evakuasi, penduduk diperkirakan dari kepadatan per luas bangunan di kelurahan yang sama (median kota bila kelurahan itu tidak punya landaan KRB). Hasilnya disimpan di `tb_node_info.demand_jiwa`.

### 5.10 Porsi TES berkapasitas (program linear, sejak 2026.10.18)

Simpang dikelompokkan pada t = 0:

| Kelompok | Syarat | Cara mengisi porsi |
|---|---|---|
| beban | Tidak ada TEA/zona hijau sempat; ada TES berkapasitas sempat | **Program linear serentak** (`scipy.optimize.linprog`, HiGHS): minimum Σ jiwa × menit tempuh, dengan beban tiap TES ≤ kapasitas |
| cadangan | TEA/zona hijau sempat | Sebanding sisa kapasitas TES yang sempat (tidak ikut beban) |
| tanpa kapasitas | Hanya TES tanpa kapasitas yang sempat | Porsi 1 ke yang tercepat |
| tidak sempat | Tidak ada TES sempat | Porsi 1 ke TES tercepat |

Model ini deterministik: tidak memakai bilangan acak, solusi seri dipecah dengan biaya 1e-6 menit per nomor TES, dan simpang tanpa penduduk dihitung 0,001 jiwa. Hasilnya `tb_route_shares` (maks. 10 baris per simpang) dan rantai `tb_tes_next`. Spesifikasi lengkap: [kontrak_porsi_tujuan.md](kontrak_porsi_tujuan.md).

### 5.11 Penulisan dan pengemasan

Tabel ditulis ke SQLite, lalu `VACUUM`. DB dikemas ke zip deterministik, dan checksum SHA-256 ditulis ke `dataset_manifest.json` dan `dataset_manifest_android.json`. Ikut ditulis laporan CSV: `daftar_tes_tea.csv`, `beban_tes.csv`, `peta_celah_kelurahan.csv`, dan `bpbd_2019_tanpa_titik.csv`.

---

## 6. Isi Database (2026.10.18)

| Tabel | Baris | Isi |
|---|---|---|
| `tb_nodes` / `tb_node_info` | 31.813 | Simpul graf, `is_safe`, jarak pantai, kelurahan, demand, catatan per simpul |
| `tb_edges` | 39.216 | Ruas jalan (untuk pengalihan lokal) |
| `tb_bridge_edges` | 176 | Ruas jembatan ≥ 20 m |
| `tb_jalur_resmi` | 4.980 | Ruas di jalur evakuasi resmi BPBD |
| `tb_tes` / `tb_tea` | 244 / 22 | Fasilitas yang dipakai routing |
| `tb_fasilitas_info` | 294 | Semua fasilitas sumber, termasuk yang dikeluarkan beserta alasannya |
| `tb_routes` | 10.688 | Rute TES rank 1–3 per simpul merah |
| `tb_tea_routes` / `tb_tea_next` | 22.084 / 47.031 | Rute TEA utama/alternatif dan rantai *next-hop* |
| `tb_safe_routes_v2` / `tb_safe_next_v2` | 11.418 / 28.894 | Navigasi zona aman (v2) |
| `tb_safe_routes` / `tb_safe_next` | 30.839 / 10.612 | Pohon global zona aman (kontrak lama, status tiba) |
| `tb_route_shares` / `tb_tes_next` | 32.201 / 40.677 | Porsi TES berkapasitas dan rantainya |
| `tb_inundation_zones` / `tb_safe_zones` | 68 / 81 | Poligon zona merah / hijau |
| `tb_kelurahan_info` | 56 | Ringkasan per kelurahan |
| `tb_metadata` | 34 | Versi, sumber data, parameter, dan kaidah |
| `v_fasilitas_evakuasi` (view) | 266 | Daftar fasilitas untuk peta dan direktori |

Ukuran DB ±37 MB. Struktur kolom dan relasi: [erd_siaga_padang.md](erd_siaga_padang.md) dan [DBML](siaga_padang_erd.dbml).

---

## 7. Validasi dan Reproduktibilitas

### 7.1 Prinsip

- **Satu engine kanonis.** DB hanya boleh dibangun oleh `build_db.py`. Perubahan logika dilakukan di skrip itu, bukan di salinan skrip.
- **Deterministik.** Input dan `--versi` yang sama menghasilkan SHA-256 DB dan zip yang sama (`173b8010…`, dicek 27 Oktober 2026).
- **Parameter bernama dan beranotasi.** Setiap konstanta dideklarasikan di bagian atas skrip dengan rujukannya, lalu disalin ke `tb_metadata`.
- **Satu label versi untuk satu isi DB.**

Perintah build:

```
git show 23854a4:padang_full.graphml > cache\graf_2026.10.16.graphml
env\Scripts\python.exe build_db.py --versi 2026.10.18 --graf cache\graf_2026.10.16.graphml
```

### 7.2 Pemeriksaan setelah build

| Pemeriksaan | Hasil 2026.10.18 |
|---|---|
| Skema tabel inti sesuai kontrak Room Android | Sesuai |
| Tujuan mendekat / sejajar pantai (skrip audit tim, dijalankan apa adanya) | 0% / 0% (DB 2026.09.28: 35,2% / 18,5%) |
| Verifikasi engine untuk TES rank 1–3, TEA, dan zona aman v2 | 0% melanggar arah |
| `is_safe` simpul sesuai poligon zona | 0 selisih |
| Zona di laut, celah, atau tumpang tindih poligon | 0 |
| Jumlah `porsi` per simpang = 1; rantai `tb_tes_next` tersambung; panjang rantai cocok dengan `eta_tabel` (≤ 0,01 menit) | Lolos |
| Simpul merah dengan rute zona aman v2 | 11.418 dari 11.418 |

### 7.3 Uji sensitivitas penalti pantai

Lima varian penalti dibandingkan (persentase simpul yang rutenya sempat mendekati pantai dibanding jiwa yang terjangkau ≤ 20 menit). Varian gabungan dipilih karena memberi pelanggaran terendah (TES rank-1 > 50 m: 13,8%) tanpa mengorbankan keterjangkauan (71,4%). Larangan total ruas yang mendekat ditolak karena membuat 7,9% simpul merah tidak punya jalan keluar. Tabel lengkap ada di [build_db_v4.md](build_db_v4.md).

### 7.4 Evaluasi melalui simulasi kanonis

Simulasi agen (20.000 agen, seed 42, kriteria selamat = tiba ≤ 20 menit **dan** tertampung):

| | Baseline (tempat terdekat) | Siaga Padang (DB) |
|---|---|---|
| Selamat | 36,7% | **68,2%** |
| TES melebihi kapasitas | 104 dari 244 | **0** |

Hasil ini konsisten dengan angka keterjangkauan dari build: 69,0% jiwa punya tujuan yang sempat ≤ 15 menit. Rincian dan interpretasinya ada di [simulasi_kanonis.md](simulasi_kanonis.md).

---

## 8. Batasan dan Hal yang Masih Terbuka

### 8.1 Batasan metode

- Kemacetan pejalan kaki, antrean tangga, dan waktu tunda keberangkatan tidak dimodelkan.
- Satu laju (0,894 m/s) dipakai untuk semua orang. Pengaruh kepadatan terhadap kecepatan tidak dimodelkan.
- Arah "menjauhi pantai" diukur dari selisih jarak ke garis pantai, bukan arah mata angin. Cara ini menangani pantai yang melengkung, tetapi ambang 15° dan pengecualian 100 m masih asumsi kerja tim.
- Graf jalan berasal dari OSM, jadi kelengkapannya bergantung pada kontributor OSM.
- Sekitar 21,4% jiwa (67.070 jiwa) tidak sempat ke tujuan mana pun dalam 20 menit pada laju orang terlemah. Ini keterbatasan sebaran fasilitas, bukan kesalahan engine. Kelurahan yang terdampak direkap di `peta_celah_kelurahan.csv` sebagai usulan lokasi TES baru.
- Aturan arah memiliki harga: di 9 dari 67 kelurahan berpenghuni, keselamatan simulasi lebih rendah daripada Baseline karena tempat terdekat berada ke arah laut atau sejajar pantai.

### 8.2 Menunggu konfirmasi BPBD

- 17 bangunan daftar resmi 2019 belum punya koordinat; 14 TES hasil geokode OSM (TES_235–TES_248) perlu verifikasi lokasi.
- 77 TES belum punya daya tampung.
- 21 TEA berada di dalam landaan menurut raster KRB sendiri; 24 titik berlabel TES bernama bukit/gunung, yang secara konsep adalah TEA.
- Definisi "jembatan" yang dihindari (hanya jembatan sungai atau termasuk gorong-gorong) dan urutan keputusan bila jembatan adalah satu-satunya jalur.
- Ambang "sejajar" 15°, pengecualian 100 m, dan perlakuan bukit di tepi pantai.

Daftar lengkap siap kirim: [pertanyaan_bpbd.md](pertanyaan_bpbd.md).

---

## 9. Rujukan Dokumen

| Topik | Dokumen |
|---|---|
| Aturan evakuasi dari wawancara BPBD | [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md) |
| Konvensi kode dan aturan data | [aturan_proyek.md](aturan_proyek.md) |
| Kebijakan kapasitas TES/TEA | [kebijakan_kapasitas_tes_tea.md](kebijakan_kapasitas_tes_tea.md) |
| Alur `build_db.py` dan pemakaian tabel oleh aplikasi | [arsitektur.md](arsitektur.md) |
| Inventaris data, parameter, hasil build | [build_db_v4.md](build_db_v4.md) |
| Porsi TES (`tb_route_shares`, `tb_tes_next`) | [kontrak_porsi_tujuan.md](kontrak_porsi_tujuan.md) |
| Struktur tabel | [erd_siaga_padang.md](erd_siaga_padang.md) |
| Simulasi kanonis | [simulasi_kanonis.md](simulasi_kanonis.md) |
| Integrasi aplikasi dan backend | [handoff_android.md](handoff_android.md), [handoff_backend.md](handoff_backend.md) |
