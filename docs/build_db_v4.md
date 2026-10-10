# Pembangun Database V4 (`build_db.py`)

`build_db.py` membangun `ranah_siaga_v4.db` dari data BPBD dan menerapkan aturan di [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md). Skrip ini menggantikan rantai lama `core.py` → `build_db_v2_with_tea.py` → `spatial/1..4` (diarsipkan di `legacy/pipeline_db/`), yang memakai data 2013–2019 dan sudah tidak relevan.

```
env\Scripts\python.exe build_db.py      # ±25 detik, keluaran di hasil_build/ + laporan di terminal
```

Butuh `rasterio` (sudah ditambahkan ke `requirements.txt`) untuk membaca raster di File Geodatabase BPBD.

## Inventaris folder `Data BPBD/`

### Dipakai

| Data | Berkas | Dipakai untuk |
|---|---|---|
| Titik TES & TEA 2025 | `SHP kecamatan/2_TES_TEA_Padang.shp` (diekstrak dari `SHP kecamatan.rar`) | Fasilitas evakuasi dan kapasitas utama |
| Jalur evakuasi resmi per RT/RW | `SHP kecamatan/Jalur_evakuasi_Padang.shp` | Ruas di jalur resmi diutamakan saat routing (faktor biaya 0,8) |
| Raster bahaya tsunami | `KRB .../03_TEMATIK/Bahaya.gdb` → `Peta_Bahaya_Tsunami` | Zona merah (`is_safe`), poligon zona merah/aman, kelayakan TEA |
| Raster bahaya gempa | `KRB .../03_TEMATIK/Bahaya.gdb` → `Peta_Bahaya_Gempabumi` | Indeks bahaya gempa tiap jembatan sungai (kriteria 5.2.2) |
| Batas kelurahan | `KRB .../02_BASEMAP/Basemap.gdb` → `Batas_Administrasi_Kelurahan_AR` | Kelurahan node & fasilitas, poligon per kelurahan |
| Batimetri | `Basemap.gdb` → `Bathimetri_Padang` | Garis pantai untuk aturan menjauhi pantai |
| Sungai | `Basemap.gdb` → `Sungai_AR` | Membedakan jembatan sungai dari gorong-gorong |
| Jejak bangunan RTRW (190.556) | `Basemap.gdb` → `Bangunan_AR` | Sebaran penduduk per node dan estimasi kapasitas TES yang kosong |
| Tabel KRB tsunami per kelurahan | `KRB .../04_TABEL/FINAL MATRIKS KRB KOTA PADANG - DOKUMEN.xlsx` (sheet `KELURAHAN`) | Penduduk terpapar (demand) dan `tb_kelurahan_info` (kelompok rentan, risiko, kapasitas) |
| Verifikasi gedung BPBD 2019 | `Daftar Shelter OK.xlsx` (sheet `TES (verifikasi)`) | Jumlah lantai dan kapasitas TES |

### Tidak dipakai (dan alasannya)

| Data | Alasan |
|---|---|
| `SHP kecamatan/1_TES_TEA_Padang.shp`, `TES_TEA_Padang.shp` | Versi lebih lama dari `2_TES_TEA_Padang`. Hanya 11 titik yang tidak ada di versi terbaru (mis. Pasar Raya Fase I–IV, Mesjid Adabiah), yang dianggap sudah direvisi BPBD. |
| `SHP kecamatan/Jalur_Evakuasi Padang.rar` | Arsip berisi berkas yang sama dengan `Jalur_evakuasi_Padang.shp` |
| `KRB .../03_TEMATIK/*.gdb.rar` | Salinan arsip `Bahaya.gdb` |
| `Kerentanan_Bencana.gdb`, `Kapasitas_Bencana.gdb`, `Risiko_Bencana.gdb` | Raster indeks gabungan (0–1). Nilai per kelurahannya sudah tersedia di tabel KRB dan masuk `tb_kelurahan_info`. |
| Raster bahaya selain tsunami & gempa (banjir, longsor, dll.) | Di luar lingkup evakuasi tsunami |
| Sheet `KELURAHAN (2)` dan berkas `... - ALBUM PETA.xlsx` | Angka tsunaminya identik dengan sheet `KELURAHAN` yang dipakai (sudah dibandingkan, 56 baris sama) |
| Sheet `TES OK` & `Perkiraan kap` di `Daftar Shelter OK.xlsx` | `TES OK` adalah versi sebelum verifikasi. `Perkiraan kap` hanya berisi satu contoh perhitungan. |
| `Basemap.gdb` → `Jalan_LN`, `Sungai_LN`, `Toponimi_*`, batas kecamatan/kota/provinsi, `Bathimetri_Indonesia` | Jalan sudah dari OSM (lebih rinci). Sisanya label peta atau batas yang tidak dibutuhkan routing. |
| `01_MXD`, `05_LAYOUT`, `06_LOGO`, `07_DOKUMEN DAN ALBUM PETA` | Proyek ArcMap, PDF layout, logo, dan dokumen laporan, bukan data mentah |
| `Peta TES dan Potensial Shelter.png` | Gambar peta 2018, data lama yang menurut BPBD sudah tidak relevan |

## Aturan yang diterapkan

| Aturan | Implementasi | Konstanta |
|---|---|---|
| Kecepatan orang terlemah (FEMA) | Semua ETA = jarak / 0,894 m/s | `KECEPATAN_JALAN_MS` |
| Batas waktu 20 menit | Tujuan ≤ 20 menit dialokasikan lebih dulu di `tb_route_shares` | `BATAS_WAKTU_MENIT` |
| Zona merah = area landaan | Node di sel raster bahaya tsunami → `is_safe = 0` | – |
| Tujuan menjauhi pantai (mutlak) | TES, TEA, dan zona aman hanya boleh menjadi tujuan jika jaraknya ke pantai > jarak posisi warga. Zona aman dihitung per kelompok jarak pantai 100 m (`tb_safe_routes_v2`/`tb_safe_next_v2`). | `LEBAR_KELOMPOK_PANTAI_M` |
| Kantong aman bukan tujuan | Komponen sel raster tanpa landaan yang dikelilingi zona merah dan < 50 ha tidak dijadikan tujuan zona aman (`tb_node_info.kantong_aman = 1`) | `LUAS_MIN_ZONA_AMAN_HA` |
| Rute menjauhi pantai (penalti) | Biaya + 10 m jalan per meter mendekat ke pantai; ruas yang mendekat > 50 m dikalikan 50 | `BOBOT_PER_METER_MENDEKAT_PANTAI`, `TOLERANSI_MENDEKAT_PANTAI_M`, `PENALTI_MENDEKAT_PANTAI` |
| Hindari jembatan sungai | Ruas `bridge=yes` yang memotong poligon sungai BPBD diberi bobot ×20, tidak dihapus | `PENALTI_JEMBATAN_SUNGAI` |
| Ikuti jalur evakuasi resmi | Ruas yang ≥ 80% berada ≤ 15 m dari jalur BPBD diberi faktor biaya 0,8 | `JALUR_RESMI_JARAK_M`, `JALUR_RESMI_FAKTOR` |
| Kapasitas TES | BPBD 2025 → verifikasi 2019 → jejak bangunan × (lantai − 2) / 1 m² per orang → median TES BPBD | `M2_PER_ORANG`, `LANTAI_ASUMSI` |
| Sebaran penduduk | Jiwa terpapar KRB per kelurahan dibagi menurut luas jejak bangunan di zona merah, ditempel ke node zona merah terdekat | – |
| TEA harus di luar landaan | TEA di dalam raster bahaya dikeluarkan dari routing | – |
| TES ≤ 2 lantai tidak layak | Dicocokkan ke verifikasi 2019 (nomor gedung harus sama persis) | `LANTAI_MAKS_TIDAK_LAYAK` |
| TES berkapasitas, TEA/zona aman tidak | Greedy dua tahap berbasis ETA | – |

Penalti hanya memengaruhi **pemilihan** rute. ETA yang disimpan selalu dihitung dari panjang jalan asli.

### Uji sensitivitas penalti pantai

Persentase node zona merah yang rutenya sempat lebih dekat ke pantai daripada titik awalnya (semua varian sudah memakai filter tujuan per kelompok):

| Varian penalti | TES rank-1 > 50 m | > 200 m | Zona aman > 50 m | > 200 m | Jiwa ≤ 20 menit |
|---|---|---|---|---|---|
| ×10 per ruas > 50 m (versi awal) | 18,1% | 4,8% | 14,5% | 3,0% | 71,8% |
| ×50 per ruas > 50 m | 15,9% | 3,2% | 13,5% | 2,6% | 71,7% |
| ×50 per ruas > 0 m (toleransi dihapus) | 17,8% | 6,0% | 12,7% | 1,9% | 65,2% |
| +10 m per meter mendekat | 15,4% | 4,0% | 11,3% | 1,4% | 71,6% |
| **Gabungan: +10 m per meter & ×50 per ruas > 50 m (dipakai)** | **13,8%** | **2,8%** | **11,2%** | **1,7%** | **71,4%** |
| Larangan total ruas > 50 m | – | – | – | – | 7,9% node tanpa jalan keluar |

Menaikkan penalti di atas nilai ini hampir tidak mengubah hasil: sisa pelanggaran bersifat struktural, karena jalannya memang hanya ke arah itu (Batang Kabung, Bungo Pasang, Padang Sarai, Air Tawar Barat, Pasir Nan Tigo). Lokasi ini tercatat di `tb_kelurahan_info.jiwa_rute_aman_mendekat_pantai` sebagai usulan TES/jalur baru ke BPBD.

Ada imbal-baliknya. Dibanding versi awal, lebih banyak rute memilih melintasi jembatan sungai daripada mendekati pantai: jiwa yang rute TES rank-1-nya lewat jembatan naik dari 66.965 menjadi 76.040. Porsi ruas yang berada di jalur evakuasi resmi juga turun dari 31,0% menjadi 27,8%.

## Perubahan untuk tim Android

Ringkasan perubahan perilaku dan panduan integrasi ada di [handoff_android.md](handoff_android.md). Skema 12 tabel inti dan view sama dengan v3, ditambah `tb_safe_routes.safe_zone_id` (→ `tb_safe_zones`) yang dipakai aplikasi sejak dataset 2026.09.28.

Tabel baru di v4 (opsional, dibaca dengan `@SkipQueryVerification`):

| Tabel | Isi |
|---|---|
| `tb_fasilitas_info` | Semua TES/TEA termasuk yang tidak dipakai beserta alasannya, sumber kapasitas, jarak ke pantai, indeks bahaya, lantai & kapasitas 2019, luas jejak bangunan |
| `tb_safe_routes_v2` | Zona aman per node zona merah yang patuh aturan pantai: `kelompok`, `safe_node_id`, nama, `safe_eta`, jarak tujuan ke pantai, seberapa jauh rute sempat mendekati pantai. **Menggantikan `tb_safe_routes` untuk aplikasi.** |
| `tb_safe_next_v2` | Next-hop per (`kelompok`, `node_id`), dirangkai seperti `tb_tea_next` |
| `tb_node_info` | Kelurahan, jarak ke pantai, indeks bahaya, demand jiwa, flag rute lewat jembatan sungai, `kantong_aman`, seberapa jauh rute TES rank-1 / zona aman sempat mendekati pantai |
| `tb_jembatan_sungai` | Ruas jembatan sungai (u, v), panjang, indeks bahaya gempa |
| `tb_jalur_resmi` | Ruas graf yang mengikuti jalur evakuasi resmi BPBD (u, v) |
| `tb_kelurahan_info` | Profil tsunami 56 kelurahan dari tabel KRB: luas bahaya, jiwa terpapar, umur rentan, miskin, disabilitas, indeks kesiapsiagaan/kapasitas/risiko; ditambah jiwa yang rute zona amannya terpaksa mendekati pantai |
| `tb_metadata` | Versi, sumber data, dan parameter build |

Semua keluaran ada di folder `hasil_build/`. Selain `ranah_siaga_v4.db`, setiap build juga menulis `ranah_siaga_v4.db.zip` (zip deterministik, ±6 MB, tidak di-commit) `dataset_manifest.json` berisi versi, ukuran, dan SHA-256 zip maupun `.db`, serta `dataset_manifest_android.json` dalam format aset aplikasi (`version`, `checksum`, `size_bytes` milik file `.db`).

## Hasil build 10 Oktober 2026

| Metrik | Nilai |
|---|---|
| Fasilitas sumber → setelah buang duplikat persis | 366 → 280 (234 TES, 46 TEA) |
| Dipakai untuk routing | 234 TES, 25 TEA |
| TEA dikeluarkan karena berada di landaan | 21 |
| Sumber kapasitas TES | BPBD 2025: 157 · BPBD 2019: 2 · jejak bangunan: 66 · median: 9 |
| Node zona merah / zona aman | 8.812 / 23.001 |
| Penduduk terpapar (KRB) | 242.750 jiwa di 56 kelurahan, disebar ke 7.678 node lewat 64.247 bangunan di zona merah |
| Jiwa dengan tujuan ≤ 20 menit (berjalan 0,894 m/s) | 173.433 (71,4%) |
| Alokasi tujuan akhir | TES 60.549 · TEA 4.443 · zona aman 177.759 jiwa |
| Rute zona aman yang berakhir lebih jauh dari pantai | 8.812 dari 8.812 node zona merah (40 kelompok, 22.853 baris next-hop) |
| Kantong aman yang tidak dijadikan tujuan | 84 kantong, 123 ha |
| Rute yang sempat mendekati pantai > 50 m / > 200 m | TES rank-1: 13,8% / 2,8% node · zona aman: 11,2% / 1,7% node |
| Jiwa yang rute TES rank-1-nya lewat jembatan sungai | 76.040, terutama Koto Tangah (Padang Sarai, Lubuk Buaya, Batang Kabung) |
| Jembatan sungai | 263 ruas, rata-rata indeks bahaya gempa 0,79 |
| Ruas rute TES rank-1 di jalur evakuasi resmi | 27,8% |
| Ukuran DB / waktu build | 29,5 MB / ±22 detik |

## Hal yang perlu dikonfirmasi ke BPBD

- **21 TEA berada di dalam area landaan** menurut raster KRB BPBD sendiri, misalnya Bundaran Siti Nurbaya, R.M Jaso Mande, Lapangan SSAG, dan LANTAMAL. Perlu dipastikan apakah titiknya salah plot atau memang tidak layak.
- **24 titik berlabel TES bernama bukit/gunung** (misal Bukit Lampu, Gunung Padang). Secara konsep ini evakuasi horizontal (TEA) dan tidak seharusnya dibatasi kapasitas.
- **75 TES tanpa angka kapasitas dari BPBD.** 66 diestimasi dari jejak bangunan RTRW (bisa meleset jika titik TES dekat bangunan lain yang lebih kecil), 9 memakai median.
- Kebijakan jembatan (bagian 5.2.1) dan definisi "jembatan" (sungai saja atau termasuk gorong-gorong).
