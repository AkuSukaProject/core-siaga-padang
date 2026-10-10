# Arsip Skrip Lama

Skrip di folder ini **tidak dipakai lagi**. Semuanya bergantung pada data lama (LAMP 1/2 berbasis data 2013, CSV turunan 143 TES / 12 TEA, `penduduk_kota_padang.csv`, `batas_kelurahan_kota_padang.geojson`) atau pada database lama (`ranah_siaga.db`, `ranah_siaga_v3.db`, `database_evakuasi_padang.sqlite`). Menurut BPBD, data tersebut sudah tidak relevan.

Skrip yang masih aktif ada di root repositori dan di `analisis/`:

| Skrip | Fungsi |
|---|---|
| `build_db.py` | Membangun `hasil_build/ranah_siaga_v4.db` (beserta zip & manifest) dari data BPBD |
| `generate_dbml_file.py` | Membangkitkan `docs/siaga_padang_erd.dbml` dari DB |
| `download_peta_full.py` | Mengunduh graf jalan `padang_full.graphml` dari OSM |
| `analisis/simulasi_resmi_padang.py` | Simulasi kanonis berbasis `ranah_siaga_v4.db` (lihat `docs/simulasi_kanonis.md`) |
| `analisis/contoh_rute_evakuasi.py` | Peta contoh rute evakuasi untuk satu posisi warga |

## Isi arsip

| Folder | Isi | Dulu dipakai untuk |
|---|---|---|
| `pipeline_db/` | `core.py`, `build_db_v2_with_tea.py`, `spatial/` | Pembangun `ranah_siaga.db` → v2 → v3 (lihat README di dalamnya) |
| `ekstraksi_data/` | `ekstrak_*.py` | Mengekstrak TES dan penduduk dari LAMP 1/2 menjadi CSV lama |
| `simulasi/` | `simulasi_bpr_*.py`, `tarik_jalan_padang.py` | Simulasi mikro BPR Padang Barat (kemungkinan sumber angka 74,49% di proposal BAB V) dan prototipe DB awal |
| `visualisasi/` | `buat_peta_*.py`, `generate_gambar_5_*.py`, `generate_*`, `peta_seluruh_tes.py`, `visualisasi_graf.py`, `konversi_gephi.py` | Peta HTML/PNG dan gambar proposal (Gambar 5.5, 5.6, peta zona rawan, dll.) |
| `uji/` | `tes_*.py`, `cek_*.py`, `test_old.py` | Uji coba dan pemeriksaan DB lama |
| `data/` (dihapus) | CSV/XLSX TES, TEA, dan penduduk lama, GeoJSON, `padang.graphml` (Padang Barat), `.gexf`, `excel/`, `shapefile/`, `shp_output/` | Masukan skrip lama. Dihapus dari working tree; pulihkan dengan `git checkout 700660d -- legacy/data` |
| `output/` | Gambar PNG lama (Gambar 5.5, 5.6, peta zona rawan, outline Padang). Peta HTML-nya dihapus; pulihkan dengan `git checkout 700660d -- legacy/output` | Keluaran skrip lama, termasuk gambar proposal |
| `eksplorasi/scratch/` | ±60 skrip `cek_*`, `inspect_*`, `investigasi_*`, `fix_*`, `verify_*`, `visualize_*`, animasi evakuasi; `eksplorasi/database_evakuasi_padang.sqlite` (prototipe DB pertama) | Eksplorasi & perbaikan ad hoc DB v1–v3 (Agustus–September 2026), sebelumnya di `scratch/` lokal dan tidak pernah di-commit |
| `eksplorasi/peta_zona_rawan_v1-v7/` | `buat_peta_zona_rawan_tsunami*.py` | Tujuh iterasi peta zona rawan, sebelumnya di `archive/` lokal |

## Catatan

- Skrip tidak dijamin bisa dijalankan dari lokasi ini: path data di dalamnya relatif terhadap root repositori dan data masukannya sudah dihapus (masih bisa diambil dari riwayat git, lihat tabel di atas).
- Jika salah satu peta atau gambar proposal perlu dibuat ulang, buat skrip baru di `analisis/` yang membaca `ranah_siaga_v4.db` atau `Data BPBD/`, dengan skrip lama di sini sebagai rujukan tampilan.
