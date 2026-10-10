# Pembangun Database V4 (`build_db.py`)

`build_db.py` membangun `ranah_siaga_v4.db` dari data BPBD dan menerapkan aturan di [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md). Skrip ini menggantikan rantai lama `core.py` → `build_db_v2_with_tea.py` → `spatial/1..4` (diarsipkan di `legacy/pipeline_db/`), yang memakai data 2013–2019 dan sudah tidak relevan.

```
env\Scripts\python.exe build_db.py      # ±22 detik, keluaran ranah_siaga_v4.db + laporan di terminal
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
| Menjauhi pantai (mutlak) | TES/TEA hanya boleh menjadi tujuan jika jaraknya ke pantai > jarak posisi warga. Ruas yang mendekati pantai > 50 m diberi bobot ×10. | `TOLERANSI_MENDEKAT_PANTAI_M`, `PENALTI_MENDEKAT_PANTAI` |
| Hindari jembatan sungai | Ruas `bridge=yes` yang memotong poligon sungai BPBD diberi bobot ×20, tidak dihapus | `PENALTI_JEMBATAN_SUNGAI` |
| Ikuti jalur evakuasi resmi | Ruas yang ≥ 80% berada ≤ 15 m dari jalur BPBD diberi faktor biaya 0,8 | `JALUR_RESMI_JARAK_M`, `JALUR_RESMI_FAKTOR` |
| Kapasitas TES | BPBD 2025 → verifikasi 2019 → jejak bangunan × (lantai − 2) / 1 m² per orang → median TES BPBD | `M2_PER_ORANG`, `LANTAI_ASUMSI` |
| Sebaran penduduk | Jiwa terpapar KRB per kelurahan dibagi menurut luas jejak bangunan di zona merah, ditempel ke node zona merah terdekat | – |
| TEA harus di luar landaan | TEA di dalam raster bahaya dikeluarkan dari routing | – |
| TES ≤ 2 lantai tidak layak | Dicocokkan ke verifikasi 2019 (nomor gedung harus sama persis) | `LANTAI_MAKS_TIDAK_LAYAK` |
| TES berkapasitas, TEA/zona aman tidak | Greedy dua tahap berbasis ETA | – |

Penalti hanya memengaruhi **pemilihan** rute. ETA yang disimpan selalu dihitung dari panjang jalan asli.

## Perubahan untuk tim Android

Ringkasan perubahan perilaku dan panduan integrasi ada di [handoff_android.md](handoff_android.md). Skema 12 tabel inti dan view sama persis dengan v3.

Tabel baru di v4 (opsional, dibaca dengan `@SkipQueryVerification`):

| Tabel | Isi |
|---|---|
| `tb_fasilitas_info` | Semua TES/TEA termasuk yang tidak dipakai beserta alasannya, sumber kapasitas, jarak ke pantai, indeks bahaya, lantai & kapasitas 2019, luas jejak bangunan |
| `tb_node_info` | Kelurahan, jarak ke pantai, indeks bahaya, demand jiwa, flag rute lewat jembatan sungai |
| `tb_jembatan_sungai` | Ruas jembatan sungai (u, v), panjang, indeks bahaya gempa |
| `tb_jalur_resmi` | Ruas graf yang mengikuti jalur evakuasi resmi BPBD (u, v) |
| `tb_kelurahan_info` | Profil tsunami 56 kelurahan dari tabel KRB: luas bahaya, jiwa terpapar, umur rentan, miskin, disabilitas, indeks kesiapsiagaan/kapasitas/risiko |
| `tb_metadata` | Versi, sumber data, dan parameter build |

Manifest Android belum diperbarui. Setelah DB disetujui, hitung SHA-256 `ranah_siaga_v4.db` (dicetak di akhir build) lalu perbarui `dataset_manifest.json`.

## Hasil build 10 Oktober 2026

| Metrik | Nilai |
|---|---|
| Fasilitas sumber → setelah buang duplikat persis | 366 → 280 (234 TES, 46 TEA) |
| Dipakai untuk routing | 234 TES, 25 TEA |
| TEA dikeluarkan karena berada di landaan | 21 |
| Sumber kapasitas TES | BPBD 2025: 157 · BPBD 2019: 2 · jejak bangunan: 66 · median: 9 |
| Node zona merah / zona aman | 8.812 / 23.001 |
| Penduduk terpapar (KRB) | 242.750 jiwa di 56 kelurahan, disebar ke 7.678 node lewat 64.247 bangunan di zona merah |
| Jiwa dengan tujuan ≤ 20 menit (berjalan 0,894 m/s) | 180.328 (74,3%) |
| Alokasi tujuan akhir | TES 59.677 · TEA 2.394 · zona aman 180.679 jiwa |
| Jiwa yang rute TES rank-1-nya lewat jembatan sungai | 66.965, terutama Koto Tangah (Padang Sarai, Lubuk Buaya, Batang Kabung) |
| Jembatan sungai | 263 ruas, rata-rata indeks bahaya gempa 0,79 |
| Ruas rute TES rank-1 di jalur evakuasi resmi | 31,0% |
| Ukuran DB / waktu build | 29,0 MB / ±22 detik |

## Hal yang perlu dikonfirmasi ke BPBD

- **21 TEA berada di dalam area landaan** menurut raster KRB BPBD sendiri, misalnya Bundaran Siti Nurbaya, R.M Jaso Mande, Lapangan SSAG, dan LANTAMAL. Perlu dipastikan apakah titiknya salah plot atau memang tidak layak.
- **24 titik berlabel TES bernama bukit/gunung** (misal Bukit Lampu, Gunung Padang). Secara konsep ini evakuasi horizontal (TEA) dan tidak seharusnya dibatasi kapasitas.
- **75 TES tanpa angka kapasitas dari BPBD.** 66 diestimasi dari jejak bangunan RTRW (bisa meleset jika titik TES dekat bangunan lain yang lebih kecil), 9 memakai median.
- Kebijakan jembatan (bagian 5.2.1) dan definisi "jembatan" (sungai saja atau termasuk gorong-gorong).
