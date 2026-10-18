# Arsitektur Sistem & Database Siaga Padang

Dokumen ini menjelaskan alur pemrosesan data (*routing engine*) dan basis data SQLite yang menjembatani data spasial BPBD dengan aplikasi Android. Rincian sumber data, parameter, dan hasil build ada di [build_db_v4.md](build_db_v4.md). Struktur tabel ada di [erd_siaga_padang.md](erd_siaga_padang.md).

## Gambaran besar

```
Data BPBD/ (KRB 2023-2027, TES/TEA 2025, jalur evakuasi, verifikasi 2019) ─┐
padang_full.graphml (jaringan jalan OSM) ───────────────────────────────────┼─► build_db.py ─► hasil_build/ranah_siaga_v4.db ─► Android (Room, offline)
docs/aturan_evakuasi_bpbd.md (aturan dari wawancara BPBD) ─────────────────┘                        │
                                                                                                     └─► generate_dbml_file.py ─► docs/siaga_padang_erd.dbml
```

Semua rute dihitung di depan (*pre-computed offline routing*). Aplikasi tidak menjalankan algoritma graf, hanya membaca tabel dan merangkai rute dari daftar node atau tabel *next-hop*.

## Alur `build_db.py`

Isi DB mengikuti kontrak DB aplikasi (`siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §1 dan §2.1).

1. **Data dasar.** Batas kelurahan, sungai, dan jejak bangunan dari `Basemap.gdb`; jalur evakuasi resmi; raster bahaya tsunami dari `Bahaya.gdb` (dibaca dengan `rasterio`); garis pantai OSM dari `data_osm/`.
2. **Atribut node.** Setiap simpul graf diberi:
   - `is_safe`: 0 jika berada di sel landaan raster bahaya tsunami (zona merah), 1 jika tidak.
   - `jarak_pantai_m`: jarak ke garis pantai OSM (`natural=coastline`).
   - Kelurahan dari batas administrasi BPBD.
3. **Bobot ruas berarah dan dua graf.** Graf tak berarah diubah menjadi dua arah karena biaya bergantung arah:
   - Biaya dasar = panjang / 0,894 m/s (orang terlemah, FEMA).
   - + 10 m jalan untuk setiap meter ruas bergerak ke arah pantai, dan ×50 jika ruas mendekati pantai lebih dari 50 m.
   - ×0,8 jika ruas mengikuti jalur evakuasi resmi BPBD.
   - Ruas yang memuat jembatan ≥ 20 m (`tb_bridge_edges`) dikeluarkan dari graf utama. Graf cadangan memuatnya dengan biaya ×20, dan hanya dipakai untuk tujuan yang tidak terjangkau tanpa jembatan.

   Penalti hanya memengaruhi pemilihan rute. Waktu tempuh dihitung dari panjang asli.
4. **Fasilitas.** TES/TEA dari `2_TES_TEA_Padang.shp`. Langkahnya:
   - duplikat persis dibuang, dan titik di luar Kota Padang dikeluarkan;
   - TES dicocokkan dengan daftar resmi BPBD 2019 (`sumber` BPBD atau WARGA) dan verifikasi 2019 (lantai, kapasitas, status);
   - TES ≤ 2 lantai atau "tidak potensial", serta TEA di dalam landaan, dikeluarkan;
   - nama dibuat unik (titik ganda ≤ 100 m digabung).
   Kapasitas di `tb_tes` hanya dari data BPBD; estimasi internal (jejak bangunan, median) hanya untuk penugasan.
5. **Reverse Dijkstra.** Dijalankan dari setiap TES/TEA pada graf terbalik (`scipy.sparse.csgraph.dijkstra`), sehingga satu pencarian menghasilkan biaya dari *semua* node menuju fasilitas itu. *Predecessor* pada graf terbalik adalah *next-hop* pada rute asli. Waktu riil dan flag jembatan diakumulasi dengan *pointer jumping*.
6. **Syarat arah (filter keras, K-B1).** Fasilitas hanya menjadi kandidat untuk node asal bila menjauh dari pantai lebih dari 15°, yaitu (jarak pantai tujuan − asal) ÷ jarak lurus > sin 15°. Tujuan ≤ 100 m tidak dinilai. Rank 2 dan 3 boleh kosong.
7. **Zona aman.** Kantong aman (< 50 ha, dikelilingi zona merah) tidak dijadikan tujuan.
   - **Pohon global** dari semua node aman (`tb_safe_routes` / `tb_safe_next`): `safe_eta = 0` menandai tujuan zona hijau.
   - Simpul merah di pohon global hanya diberi baris bila tujuannya lolos syarat arah (pola tabel sesuai kontrak).
   - **Rute v2, navigasi zona aman** (`tb_safe_routes_v2` / `tb_safe_next_v2`): Dijkstra maju dari tiap node merah; dipilih titik zona hijau **terjauh dari pantai** yang sempat ≤ 15 menit dan lolos syarat arah (bila tidak ada, batas zona hijau yang tercepat dicapai); rantainya disimpan per titik tujuan (`kelompok`).
8. **Demand & penugasan (opsi A).** Jiwa terpapar per kelurahan (tabel KRB) disebar ke node zona merah menurut luas jejak bangunan, lalu dialokasikan secara *greedy*. Tujuan yang sempat ≤ 15 menit (cadangan 5 menit) didahulukan; di antaranya keluar zona (TEA/zona aman) sebelum TES, dan yang terjauh dari pantai lebih dulu (K-B6). TES dibatasi kapasitas, TEA dan zona aman tidak.
9. **Zona spasial.** Zona merah dibentuk di awal build (langkah 1) dari raster landaan dengan kontur sub-piksel, ditambah zona rawan peta evakuasi BPBD (`data_bpbd_digitasi/`), dipotong ke daratan menurut garis pantai OSM, dan dipakai bersama untuk `is_safe`, TEA di landaan, dan sebaran penduduk. Pita pantai di luar batas kelurahan dibagi ke kelurahan terdekat, lalu zona merah dan zona hijau (kelurahan di darat − zona merah) dipotong per kelurahan, lalu disimpan sebagai WKT `MULTIPOLYGON` 7 desimal.
10. **SQLite & paket.** Kolom ETA ditulis pada 1,2 m/s (kontrak). Tabel ditulis, lalu `VACUUM`. DB dipaketkan ke `ranah_siaga_v4.db.zip`; checksum ditulis ke `dataset_manifest.json` dan `dataset_manifest_android.json`. Ikut ditulis: `daftar_tes_tea.csv`, `bpbd_2019_tanpa_titik.csv`, `peta_celah_kelurahan.csv`. Laporan build dicetak di terminal.

Build bersifat deterministik: input dan label versi (`--versi`) yang sama menghasilkan SHA-256 DB dan zip yang sama.

## Cara aplikasi memakai database

| Kebutuhan di aplikasi | Tabel |
|---|---|
| Posisi pengguna di zona merah atau aman | `tb_nodes.is_safe` di node terdekat, atau pemeriksaan poligon `tb_inundation_zones` / `tb_safe_zones` |
| Rute ke TES (evakuasi vertikal) | `tb_routes` (hanya ada untuk node zona merah) → `rank_X_path` |
| Rute ke TEA (evakuasi horizontal) | `tb_tea_routes` → rangkai dari `tb_tea_next` dalam satu kueri |
| Rute keluar ke zona aman | `tb_safe_routes_v2` → rangkai dari `tb_safe_next_v2` dengan `kelompok` node asal (tabel lama `tb_safe_routes` / `tb_safe_next` tetap ada untuk status tiba dan cadangan) |
| Status tiba di zona aman | `tb_safe_routes.safe_eta = 0` pada node terdekat |
| Keterangan "lewat jembatan" | `tb_bridge_edges` (edge_id ruas rute) |
| Daftar & peta fasilitas | `v_fasilitas_evakuasi` |
| Jalan tidak bisa dilewati | Cek tetangga di `tb_edges` lalu pakai rute tetangga ([konsep_pengalihan_rute_lokal.md](konsep_pengalihan_rute_lokal.md)) |

## Pipeline lama (diarsipkan)

`core.py` → `build_db_v2_with_tea.py` → `spatial/1..5` (sekarang di [`legacy/pipeline_db/`](../legacy/pipeline_db/)) menghasilkan `ranah_siaga.db` → `ranah_siaga_v2.db` → `ranah_siaga_v3.db`. Pipeline ini memakai data TES 2013–2019, zona merah berbasis kelurahan, dan kecepatan 1,2 m/s. Kodenya disimpan di `legacy/pipeline_db/` sebagai rujukan, tetapi tidak boleh dipakai untuk membangun DB.
