# Arsip Skrip Lama

Skrip di folder ini **tidak dipakai lagi**. Semuanya bergantung pada data lama (LAMP 1/2 berbasis data 2013, CSV turunan 143 TES / 12 TEA, `penduduk_kota_padang.csv`, `batas_kelurahan_kota_padang.geojson`) atau pada database lama (`ranah_siaga.db`, `ranah_siaga_v3.db`, `database_evakuasi_padang.sqlite`). Menurut BPBD, data tersebut sudah tidak relevan.

Skrip yang masih aktif ada di root repositori:

| Skrip | Fungsi |
|---|---|
| `build_db.py` | Membangun `ranah_siaga_v4.db` dari data BPBD |
| `generate_dbml_file.py` | Membangkitkan `docs/siaga_padang_erd.dbml` dari DB |
| `download_peta_full.py` | Mengunduh graf jalan `padang_full.graphml` dari OSM |
| `simulasi_resmi_padang.py` | Simulasi kanonis (belum diselaraskan dengan data v4, lihat `docs/simulasi_kanonis.md`) |

## Isi arsip

| Folder | Isi | Dulu dipakai untuk |
|---|---|---|
| `pipeline_db/` | `core.py`, `build_db_v2_with_tea.py`, `spatial/` | Pembangun `ranah_siaga.db` → v2 → v3 (lihat README di dalamnya) |
| `ekstraksi_data/` | `ekstrak_*.py` | Mengekstrak TES dan penduduk dari LAMP 1/2 menjadi CSV lama |
| `simulasi/` | `simulasi_bpr_*.py`, `tarik_jalan_padang.py` | Simulasi mikro BPR Padang Barat (kemungkinan sumber angka 74,49% di proposal BAB V) dan prototipe DB awal |
| `visualisasi/` | `buat_peta_*.py`, `generate_gambar_5_*.py`, `generate_*`, `peta_seluruh_tes.py`, `visualisasi_graf.py`, `konversi_gephi.py` | Peta HTML/PNG dan gambar proposal (Gambar 5.5, 5.6, peta zona rawan, dll.) |
| `uji/` | `tes_*.py`, `cek_*.py`, `test_old.py` | Uji coba dan pemeriksaan DB lama |
| `data/` | CSV/XLSX TES, TEA, dan penduduk lama, GeoJSON batas kelurahan & wilayah sekitar, `padang.graphml` (Padang Barat), `.gexf`, `database_evakuasi_padang.sqlite`, folder `excel/`, `shapefile/` (proyek QGIS), `shp_output/` | Masukan skrip lama dan `simulasi_resmi_padang.py` |
| `output/` | Peta HTML dan gambar PNG | Keluaran skrip lama, termasuk gambar proposal |

## Catatan

- Skrip tidak dijamin bisa dijalankan dari lokasi ini: path data di dalamnya relatif terhadap root repositori (data lamanya sekarang di `legacy/data/`), dan sebagian berkas masukannya sudah dihapus (masih bisa diambil dari riwayat git).
- Pengecualian: `simulasi_resmi_padang.py` di root sudah diarahkan ke `legacy/data/` dan menulis petanya ke `legacy/output/`, sampai skrip itu diselaraskan dengan data v4.
- Jika salah satu peta atau gambar proposal perlu dibuat ulang, buat skrip baru di root yang membaca `ranah_siaga_v4.db` atau `Data BPBD/`, dengan skrip lama di sini sebagai rujukan tampilan.
