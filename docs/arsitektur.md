# Arsitektur Sistem & Database Siaga Padang

Dokumen ini menjelaskan alur pemrosesan data (*routing engine*) dan basis data SQLite yang menjembatani data spasial BPBD dengan aplikasi Android. Rincian sumber data, parameter, dan hasil build ada di [build_db_v4.md](build_db_v4.md). Struktur tabel ada di [erd_siaga_padang.md](erd_siaga_padang.md).

## Gambaran besar

```
Data BPBD/ (KRB 2023-2027, TES/TEA 2025, jalur evakuasi, verifikasi 2019) ─┐
padang_full.graphml (jaringan jalan OSM) ───────────────────────────────────┼─► build_db.py ─► ranah_siaga_v4.db ─► Android (Room, offline)
docs/aturan_evakuasi_bpbd.md (aturan dari wawancara BPBD) ─────────────────┘                        │
                                                                                                     └─► generate_dbml_file.py ─► docs/siaga_padang_erd.dbml
```

Semua rute dihitung di depan (*pre-computed offline routing*). Aplikasi tidak menjalankan algoritma graf, hanya membaca tabel dan merangkai rute dari daftar node atau tabel *next-hop*.

## Alur `build_db.py`

1. **Data dasar BPBD.** Memuat batas kelurahan, batimetri (garis pantai), sungai, dan jejak bangunan dari `Basemap.gdb`; jalur evakuasi resmi; raster bahaya tsunami dan gempa dari `Bahaya.gdb` (dibaca dengan `rasterio`).
2. **Atribut node.** Setiap simpul graf diberi:
   - `is_safe`: 0 jika berada di sel landaan raster bahaya tsunami (zona merah), 1 jika tidak.
   - `d_pantai`: jarak ke laut (poligon batimetri), dipakai untuk aturan menjauhi pantai.
   - Kelurahan dari batas administrasi BPBD.
3. **Bobot ruas berarah.** Graf tak berarah diubah menjadi dua arah karena biaya bergantung arah:
   - Biaya dasar = panjang / 0,894 m/s (orang terlemah, FEMA).
   - ×10 jika ruas mendekati pantai lebih dari 50 m.
   - ×20 jika ruas adalah jembatan sungai (tag OSM `bridge` yang memotong poligon sungai BPBD).
   - ×0,8 jika ruas mengikuti jalur evakuasi resmi BPBD.

   Penalti hanya memengaruhi pemilihan rute. ETA yang disimpan selalu waktu tempuh riil.
4. **Fasilitas.** TES/TEA dari `2_TES_TEA_Padang.shp`, duplikat persis dibuang, kelurahan ditentukan secara spasial, dicocokkan dengan verifikasi 2019 untuk jumlah lantai dan kapasitas. TES ≤ 2 lantai dan TEA di dalam area landaan dikeluarkan. Kapasitas kosong diisi dari verifikasi 2019, jejak bangunan, atau median.
5. **Reverse Dijkstra.** Dijalankan dari setiap TES/TEA pada graf terbalik (`scipy.sparse.csgraph.dijkstra`), sehingga satu pencarian menghasilkan biaya dari *semua* node menuju fasilitas itu. *Predecessor* pada graf terbalik adalah *next-hop* pada rute asli. Waktu riil dan flag jembatan sepanjang rute diakumulasi dengan *pointer jumping*.
6. **Aturan menjauhi pantai (filter keras).** Fasilitas hanya menjadi kandidat untuk node asal jika `d_pantai(fasilitas) > d_pantai(node)`.
7. **Zona aman terdekat.** *Multi-source* Dijkstra dari semua node `is_safe = 1`.
8. **Demand & penugasan.** Jiwa terpapar per kelurahan (tabel KRB) disebar ke node zona merah menurut luas jejak bangunan, lalu dialokasikan secara *greedy* berbasis ETA: TES dibatasi kapasitas, TEA dan zona aman tidak. Tujuan ≤ 20 menit didahulukan.
9. **Zona spasial.** Raster landaan dipoligonkan, dipotong per kelurahan menjadi zona merah dan zona hijau, lalu disimpan sebagai WKT.
10. **SQLite.** Tabel ditulis, lalu `VACUUM`. Laporan build (cakupan ≤ 20 menit, ketergantungan jembatan, fasilitas yang dikeluarkan) dicetak di terminal.

Build bersifat deterministik: input yang sama menghasilkan SHA-256 DB yang sama.

## Cara aplikasi memakai database

| Kebutuhan di aplikasi | Tabel |
|---|---|
| Posisi pengguna di zona merah atau aman | `tb_nodes.is_safe` di node terdekat, atau pemeriksaan poligon `tb_inundation_zones` / `tb_safe_zones` |
| Rute ke TES (evakuasi vertikal) | `tb_routes` (hanya ada untuk node zona merah) → `rank_X_path` |
| Rute ke TEA (evakuasi horizontal) | `tb_tea_routes` → rangkai dari `tb_tea_next` dalam satu kueri |
| Rute keluar ke zona aman terdekat | `tb_safe_routes` → rangkai dari `tb_safe_next` |
| Daftar & peta fasilitas | `v_fasilitas_evakuasi` |
| Jalan tidak bisa dilewati | Cek tetangga di `tb_edges` lalu pakai rute tetangga ([konsep_pengalihan_rute_lokal.md](konsep_pengalihan_rute_lokal.md)) |

## Pipeline lama (diarsipkan)

`core.py` → `build_db_v2_with_tea.py` → `spatial/1..5` (sekarang di [`legacy/pipeline_db/`](../legacy/pipeline_db/)) menghasilkan `ranah_siaga.db` → `ranah_siaga_v2.db` → `ranah_siaga_v3.db`. Pipeline ini memakai data TES 2013–2019, zona merah berbasis kelurahan, dan kecepatan 1,2 m/s. Kodenya disimpan di `legacy/pipeline_db/` sebagai rujukan, tetapi tidak boleh dipakai untuk membangun DB.
