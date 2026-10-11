# Data OpenStreetMap pendukung

Data di folder ini diambil dari OpenStreetMap lewat Overpass API dan dipakai `build_db.py`. Data © kontributor OpenStreetMap, lisensi ODbL (https://www.openstreetmap.org/copyright).

| Berkas | Isi | Dipakai untuk |
|---|---|---|
| `pantai_osm.json` | `way["natural"="coastline"]` di kotak (-1.20, 100.20, -0.70, 100.60), diunduh 11 Oktober 2026 | `jarak_pantai_m` dan syarat arah (kontrak DB aplikasi H-3) |
| `jembatan_osm.json` | `way["highway"]["bridge"]` di kotak (-1.15, 100.28, -0.78, 100.55), 602 way, diunduh 11 Oktober 2026 | Panjang badan jembatan untuk `tb_bridge_edges` (H-4). Tanpa berkas ini `build_db.py` memperkirakan dari lebar sungai BPBD |

| `geokode_daftar_resmi_bpbd.csv` | 42 bangunan daftar resmi BPBD 2019 tanpa titik di data 2025, dicari lewat OSM Nominatim (11 Oktober 2026) dan diperiksa nama + jalannya: 11 sudah ada di data 2025 dengan nama lain, 14 baru cocok, 6 ragu, 11 tidak ditemukan | Menautkan TES ke daftar resmi BPBD dan menambah 14 TES bersumber BPBD (koordinat perlu verifikasi) |

Kueri Overpass sama dengan `siagapadang/docs/audit/analisis_masukan_bpbd.py`, supaya hasil engine dan skrip audit tim memakai data yang sama. Menambah `jembatan_osm.json` mengubah isi DB, jadi build sesudahnya harus memakai label versi baru.
