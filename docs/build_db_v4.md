# Pembangun Database V4 (`build_db.py`)

`build_db.py` membangun `hasil_build/ranah_siaga_v4.db` dari data BPBD. DB ini mengikuti dua acuan:
- aturan di [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md);
- **kontrak DB aplikasi** di repo `siagapadang`, `docs/PEMBAGIAN_TUGAS_BPBD.md` §1 (asumsi kerja K-B1–K-B8) dan §2.1 (isi DB).

Skrip ini menggantikan rantai lama `core.py` → `build_db_v2_with_tea.py` → `spatial/1..4` (diarsipkan di `legacy/pipeline_db/`).

```
env\Scripts\python.exe build_db.py --versi 2026.10.12   # ±25 detik, keluaran di hasil_build/ + laporan di terminal
```

Tanpa `--versi`, label versi diambil dari tanggal build. Satu label versi hanya boleh dipakai untuk satu isi DB. Butuh `rasterio` untuk membaca raster di File Geodatabase BPBD.

## Inventaris data

### Dipakai

| Data | Berkas | Dipakai untuk |
|---|---|---|
| Titik TES & TEA 2025 | `Data BPBD/SHP kecamatan/2_TES_TEA_Padang.shp` (dari `SHP kecamatan.rar`) | Fasilitas evakuasi dan kapasitas utama. Hasil digitasi staf GIS BPBD atas kesepakatan Kelurahan Tangguh/latihan 2025, jadi `sumber = WARGA` kecuali cocok dengan daftar resmi |
| Daftar resmi BPBD 2019 | `Daftar Shelter OK.xlsx`, sheet `TES OK` (3 shelter + 59 bangunan potensial, 5 parameter Bidang RR) dan koordinat hasil geokode `data_osm/geokode_daftar_resmi_bpbd.csv` | Penentu `sumber = BPBD`, lantai, dan kapasitas. Tidak berkoordinat: 45 bangunan tertaut ke titik (nama, lokasi sama, atau geokode OSM); 17 sisanya dicatat di `hasil_build/bpbd_2019_tanpa_titik.csv` |
| Verifikasi gedung BPBD 2019 | `Daftar Shelter OK.xlsx`, sheet `TES (verifikasi)` | Jumlah lantai, kapasitas, status "tidak potensial" |
| Jalur evakuasi resmi per RT/RW | `Data BPBD/SHP kecamatan/Jalur_evakuasi_Padang.shp` | Ruas di jalur resmi diutamakan (faktor biaya 0,8) |
| Raster bahaya tsunami | `KRB .../03_TEMATIK/Bahaya.gdb` → `Peta_Bahaya_Tsunami` | Zona merah (`is_safe`), poligon zona merah/hijau, kantong aman, kelayakan TEA |
| Batas kelurahan | `KRB .../02_BASEMAP/Basemap.gdb` → `Batas_Administrasi_Kelurahan_AR` | Kelurahan node & fasilitas, syarat "semua titik di Kota Padang", poligon per kelurahan |
| Jejak bangunan RTRW (190.556) | `Basemap.gdb` → `Bangunan_AR` | Sebaran penduduk per node dan estimasi kapasitas internal TES tanpa data |
| Tabel KRB tsunami per kelurahan | `KRB .../04_TABEL/FINAL MATRIKS KRB KOTA PADANG - DOKUMEN.xlsx` (sheet `KELURAHAN`) | Penduduk terpapar (demand) dan `tb_kelurahan_info` |
| Graf jalan pejalan kaki | `padang_full.graphml` (OSM) | Simpul, ruas, tag `bridge` |
| Garis pantai | `data_osm/pantai_osm.json` (OSM `natural=coastline`, ODbL) | `jarak_pantai_m` dan syarat arah (kontrak H-3, sama dengan skrip audit tim). Selisih dengan batimetri BPBD di zona merah: median 1 m, maks 70 m |
| Jembatan OSM | `data_osm/jembatan_osm.json` (OSM `highway`+`bridge`, 602 way, ODbL) | Panjang badan jembatan untuk `tb_bridge_edges` (≥ 20 m: 176 ruas; pembanding tim 177) |

### Tidak dipakai (dan alasannya)

| Data | Alasan |
|---|---|
| `SHP kecamatan/1_TES_TEA_Padang.shp`, `TES_TEA_Padang.shp` | Versi lebih lama dari `2_TES_TEA_Padang` (280 dari 284 dan 185 dari 188 titiknya ada di versi 2) |
| `SHP kecamatan/Jalur_Evakuasi Padang.rar`, `KRB .../03_TEMATIK/*.gdb.rar` | Salinan arsip berkas yang sudah dipakai |
| `Bathimetri_Padang`, `Sungai_AR` | Cadangan bila berkas di `data_osm/` tidak ada (garis pantai; perkiraan panjang jembatan dari lebar sungai) |
| `Kerentanan_Bencana.gdb`, `Kapasitas_Bencana.gdb`, `Risiko_Bencana.gdb`, raster bahaya lain (termasuk gempa) | Nilai per kelurahannya sudah ada di tabel KRB, atau di luar lingkup evakuasi tsunami |
| Sheet `KELURAHAN (2)`, `... - ALBUM PETA.xlsx`, sheet `Perkiraan kap` | Identik dengan yang dipakai, atau hanya contoh perhitungan |
| `Basemap.gdb` → `Jalan_LN`, `Sungai_LN`, `Toponimi_*`, batas lain, `Bathimetri_Indonesia` | Jalan sudah dari OSM; sisanya label peta atau batas yang tidak dibutuhkan |
| `01_MXD`, `05_LAYOUT`, `06_LOGO`, `07_DOKUMEN DAN ALBUM PETA`, `Peta TES dan Potensial Shelter.png` | Proyek ArcMap, layout, dan gambar, bukan data mentah |

## Aturan yang diterapkan

| Aturan | Implementasi | Konstanta |
|---|---|---|
| Laju orang terlemah (FEMA, K-B3) | Semua keputusan engine (20 menit, penugasan, simulasi) memakai 0,894 m/s | `KECEPATAN_JALAN_MS` |
| Satuan kolom ETA (kontrak §2.1) | `rank_k_eta` dan `safe_eta` disimpan pada **1,2 m/s**; aplikasi mengalikan 1,2 ÷ 0,89. 20 menit riil = 14,9 menit tabel | `KECEPATAN_TABEL_MS` |
| Zona merah = area landaan | Node di sel raster bahaya tsunami → `is_safe = 0` | – |
| Arah tujuan (K-B1) | TES, TEA, dan zona aman hanya menjadi tujuan bila menjauh dari pantai: (jarak_pantai tujuan − asal) ÷ jarak lurus > 0,27 (ambang 0,26 ≈ sin 15° milik skrip audit tim + margin 0,01). Sejajar tidak boleh. Tujuan ≤ 100 m tidak dinilai. Arah tidak pernah dilonggarkan | `ARAH_MIN_SIN`, `ARAH_JARAK_DEKAT_M` |
| Zona aman per warga | Tujuan kandidat = "gerbang" (node zona aman yang bertetangga dengan node di luarnya); untuk tiap node merah dipilih gerbang termurah yang lolos syarat arah; rantai disimpan per gerbang (`tb_safe_next_v2.kelompok`) | – |
| Kantong aman bukan tujuan | Komponen sel raster tanpa landaan yang dikelilingi zona merah dan < 50 ha | `LUAS_MIN_ZONA_AMAN_HA` |
| Jalur menjauhi pantai (penalti) | Biaya + 10 m jalan per meter mendekat ke pantai; ruas yang mendekat > 50 m dikalikan 50 | `BOBOT_PER_METER_MENDEKAT_PANTAI`, `TOLERANSI_MENDEKAT_PANTAI_M`, `PENALTI_MENDEKAT_PANTAI` |
| Jembatan ≥ 20 m (K-B2) | Rute dicari dulu pada graf tanpa jembatan itu. Hanya bila tujuan tidak terjangkau tanpa jembatan, rute lewat jembatan (penalti ×20) dipakai sebagai cadangan. Ruasnya di `tb_bridge_edges` | `JEMBATAN_MIN_M`, `PENALTI_JEMBATAN`, `JEMBATAN_LEBAR_SUNGAI_MIN_M` |
| Keluar zona dulu (K-B6) | Penugasan (`tb_route_shares`): di antara tujuan ≤ 20 menit, TEA/zona aman didahulukan sebelum TES | – |
| Ikuti jalur evakuasi resmi | Ruas yang ≥ 80% berada ≤ 15 m dari jalur BPBD diberi faktor biaya 0,8 | `JALUR_RESMI_JARAK_M`, `JALUR_RESMI_FAKTOR` |
| Sumber (K-B5) | `BPBD` bila cocok dengan daftar resmi 2019 (nomor gedung harus sama persis), selain itu `WARGA`; keduanya dipakai routing | – |
| Kapasitas TES | Data BPBD: 2025 → daftar resmi 2019 → verifikasi 2019; selain itu `tb_tes.kapasitas` **kosong**. Untuk penugasan internal, kekosongan diisi estimasi jejak bangunan × (lantai − 2) ÷ 1 m² atau median (tercatat di `tb_fasilitas_info`) | `M2_PER_ORANG`, `LANTAI_ASUMSI` |
| TES tidak layak | Dinilai "tidak potensial" di verifikasi BPBD 2019. Jumlah lantai tidak dipakai sebagai syarat sendiri: di data BPBD, 6 dari 7 bangunan ≤ 2 lantai memang "tidak potensial", kecuali Masjid Raya Sumbar yang dinilai potensial; tim aplikasi juga tidak menetapkan minimal lantai | – |
| TEA harus di luar landaan | TEA di dalam raster bahaya dikeluarkan | – |
| Semua titik di Kota Padang (H-1) | Titik di luar batas kelurahan BPBD dikeluarkan (tidak ada pada data ini) | – |
| Nama fasilitas unik (H-1) | Nama & jenis sama ≤ 100 m digabung; TEA bernama sama dengan TES diberi "(area evakuasi)"; nama sama di lokasi berbeda diberi kelurahan (dan nomor). ID tidak bergeser | `GABUNG_JARAK_M` |
| Format poligon | WKT `MULTIPOLYGON` 2D, 7 desimal | – |
| Penulisan nama wilayah | Angka Romawi tetap kapital ("Gates Nan XX") | – |

Penalti hanya memengaruhi pemilihan rute. ETA yang disimpan selalu dari panjang jalan asli.

### Uji sensitivitas penalti pantai (versi 2026.10.11)

Uji ini dibuat sebelum kontrak diterapkan, dengan syarat tujuan "lebih jauh dari pantai". Persentase node zona merah yang rutenya sempat lebih dekat ke pantai daripada titik awalnya:

| Varian penalti | TES rank-1 > 50 m | > 200 m | Zona aman > 50 m | > 200 m | Jiwa ≤ 20 menit |
|---|---|---|---|---|---|
| ×10 per ruas > 50 m (versi awal) | 18,1% | 4,8% | 14,5% | 3,0% | 71,8% |
| ×50 per ruas > 50 m | 15,9% | 3,2% | 13,5% | 2,6% | 71,7% |
| ×50 per ruas > 0 m (toleransi dihapus) | 17,8% | 6,0% | 12,7% | 1,9% | 65,2% |
| +10 m per meter mendekat | 15,4% | 4,0% | 11,3% | 1,4% | 71,6% |
| **Gabungan (dipakai)** | **13,8%** | **2,8%** | **11,2%** | **1,7%** | **71,4%** |
| Larangan total ruas > 50 m | – | – | – | – | 7,9% node tanpa jalan keluar |

## Hasil build versi 2026.10.12

| Metrik | Nilai |
|---|---|
| Fasilitas sumber → setelah buang duplikat persis | 366 → 280 (234 TES, 46 TEA) |
| Dipakai untuk routing | 244 TES (45 BPBD, 199 WARGA), 25 TEA |
| Dikeluarkan | TES: Taman Siswa ("tidak potensial"); Incasi Raya, Youth Center, FK Unand (titik ganda). TEA: 21 di dalam landaan |
| Kapasitas TES dari data BPBD | 167 (BPBD 2025 155, daftar resmi 2019 11, verifikasi 2019 1); 77 kosong |
| Daftar resmi BPBD 2019 (62 bangunan) | 45 tertaut: 20 lewat nama, 11 titik sama dengan nama lain, 14 titik baru dari geokode OSM (TES_235–TES_248). 17 belum punya titik |
| Node zona merah / zona aman | 8.812 / 23.001 |
| Penduduk terpapar (KRB) | 242.750 jiwa di 56 kelurahan, disebar ke 7.678 node lewat 64.247 bangunan |
| Arah tujuan | Skrip audit tim `docs/audit/analisis_masukan_bpbd.py`, dijalankan apa adanya: tujuan utama **0% mendekat, 0% sejajar** (DB 2026.09.28: 35,2% dan 18,5%). Verifikasi engine: TES rank 1–3, TEA, zona aman v2 juga 0% |
| `tb_routes` | 8.728 node merah; rank 2 kosong 187, rank 3 kosong 869; 84 node tanpa TES yang lolos syarat (tetap punya TEA/zona aman) |
| Zona aman | v2: 8.795 dari 8.812 node merah (441 gerbang, 324 dipakai); 17 node tanpa zona aman yang lolos syarat. Tabel lama: 1.019 node merah dibuang karena tujuan pohon global tidak lolos arah |
| Jembatan ≥ 20 m | 176 ruas (OSM). Rute TES rank-1 yang terpaksa lewat jembatan (cadangan): 2.061 node (58.538 jiwa) |
| Tidak sempat ke tujuan mana pun (0,894 m/s) | 20 menit: 24,5% node, 53.907 jiwa (22,2%) · 30 menit: 14,4% node, 31.152 jiwa (12,8%). Per kelurahan: `hasil_build/peta_celah_kelurahan.csv` |
| Penugasan berkapasitas (opsi A, K-B6) | 172.866 jiwa (71,2%) punya tujuan ≤ 20 menit; TES 37.343 · TEA 4.264 · zona aman 201.144 jiwa |
| Ruas rute TES rank-1 di jalur evakuasi resmi | 29,2% |
| Ukuran DB / waktu build | 29,97 MB / ±25 detik |

Keluaran di `hasil_build/`: `ranah_siaga_v4.db`, `ranah_siaga_v4.db.zip` (deterministik, tidak di-commit), `dataset_manifest.json` (checksum zip dan `.db`), `dataset_manifest_android.json` (format aset aplikasi), `daftar_tes_tea.csv` (H-1: nama unik, koordinat, sumber, daya tampung, lantai), `bpbd_2019_tanpa_titik.csv`, dan `peta_celah_kelurahan.csv` (H-7).

## Hal yang perlu dikonfirmasi ke BPBD

Daftar pertanyaan lengkap yang siap dikirim: [pertanyaan_bpbd.md](pertanyaan_bpbd.md). Ringkasnya:


- **17 bangunan daftar resmi BPBD 2019 tanpa titik koordinat** (`bpbd_2019_tanpa_titik.csv`): 11 tidak ada di OpenStreetMap, 6 hasil OSM-nya meragukan (bangunan lain/cabang lain).
- **14 TES baru berkoordinat OSM** (TES_235–TES_248) perlu verifikasi lokasi.
- **Masjid Raya Sumbar** (TES_205) tercatat 2 lantai tetapi dinilai potensial dengan daya tampung 15.000; tetap dipakai sesuai penilaian BPBD.
- **21 TEA berada di dalam area landaan** menurut raster KRB BPBD sendiri (misalnya Bundaran Siti Nurbaya, R.M Jaso Mande, Lapangan SSAG, LANTAMAL).
- **24 titik berlabel TES bernama bukit/gunung** (misalnya Bukit Lampu, Gunung Padang). Secara konsep ini TEA.
- **77 TES tanpa daya tampung dari BPBD.**
- **Titik ganda di data 2025**: Incasi Raya, Youth Center, dan FK Unand tercatat dua kali di lokasi hampir sama; Bukit Lampu, Bukit Karan, Bukit Simpang Rawang, dan Dealer Honda dipakai untuk dua tempat berbeda.
- Asumsi kerja yang masih menunggu jawaban (kontrak §7): batas "sejajar" 15° dan pengecualian 100 m, jembatan mana yang dihindari, bukit di tepi pantai.
