# Siaga Padang — Core Engine

Pembangun database rute evakuasi tsunami Kota Padang untuk aplikasi Android Siaga Padang. Data bersumber dari BPBD Kota Padang (KRB 2023–2027, TES/TEA 2025, daftar resmi 2019) dan aturan evakuasi hasil wawancara BPBD. Isi DB mengikuti kontrak DB aplikasi di repo `siagapadang` (`docs/PEMBAGIAN_TUGAS_BPBD.md` §2.1).

## Struktur

| Lokasi | Isi |
|---|---|
| `build_db.py` | Engine: membangun isi `hasil_build/` dari data BPBD |
| `generate_dbml_file.py` | Membangkitkan ERD `docs/siaga_padang_erd.dbml` dari DB |
| `generate_erd_gambar.py` | Menggambar ERD dari DB: `docs/erd/` (PNG/SVG lengkap dan ringkas, berkas draw.io dan PlantUML, halaman interaktif + kamus data) |
| `generate_erd_dbdiagram.py` | Menggambar ERD gaya dbdiagram.io dari `docs/siaga_padang_erd.dbml`: `docs/erd/erd_siaga_padang_dbdiagram.png` / `.svg` (semua kolom, garis siku per kolom, label 1/*) |
| `salin_db_ke_android.py` | Menyalin DB hasil build ke `android/app/src/main/assets/` repo aplikasi, beserta manifest berformat aplikasi |
| `download_peta_full.py` | Mengunduh graf jalan pejalan kaki Kota Padang dari OSM lewat Overpass (`padang_full.graphml`) |
| `graf_dari_geofabrik.py` | Membangun `padang_full.graphml` yang setara dari ekstrak Geofabrik (`.osm.pbf`), bila Overpass tidak bisa dipakai. `padang_full.graphml` di repo: OSM per 20 Oktober 2026 (dipakai DB 2026.10.17). DB terbaru 2026.10.18 dibangun di atas graf 8 Agustus 2026 yang sama dengan 2026.10.16 (lihat Menjalankan) |
| `analisis/gambar_laporan.py` | Gambar laporan akhir (Gambar 1.1, 3.1, 5.4, beban TES) langsung dari DB, ke `analisis/output/gambar_laporan/<versi>/`; `--db`/`--graf` untuk versi lama |
| `analisis/gambar_alur_interaksi.py` | Gambar 5.1 laporan (alur interaksi tiga lajur), ke `analisis/output/gambar_laporan/gambar_5_1_alur_interaksi.png` / `.svg` |
| `analisis/skenario_tes_berkapasitas.py` | Dampak skenario 167 TES berdaya tampung tercatat terhadap kandidat TES per simpul (keluaran `analisis/output/skenario_tes_berkapasitas/<versi>/`) |
| `analisis/banding_porsi_kapasitas.py` | Banding porsi TES skenario 167 TES tercatat (isi DB) vs skenario estimasi daya tampung 244 TES, dengan program linear yang sama dengan `build_db.py` (keluaran `analisis/output/banding_porsi_kapasitas/<versi>/`) |
| `hasil_build/` | Keluaran build: `ranah_siaga_v4.db` (database terbaru), `ranah_siaga_v4.db.zip` (paket untuk aplikasi, tidak di-commit), `dataset_manifest.json` (versi & checksum zip dan .db), `dataset_manifest_android.json` (manifest berformat aset aplikasi) |
| `data_osm/` | Garis pantai (dan jembatan) OpenStreetMap yang dipakai build, ODbL |
| `data_bpbd_digitasi/` | Zona rawan tsunami hasil digitasi peta evakuasi BPBD (Blue Line) dan skrip pembuatnya; dipakai build untuk zona merah |
| `analisis/` | Simulasi kanonis dan peta contoh rute (keluaran di `analisis/output/`) |
| `docs/` | Aturan evakuasi BPBD, arsitektur, ERD, hasil simulasi, panduan Android |
| `referensi/` | Dokumen rujukan (PDF KRB, peta jalur evakuasi, proposal) |
| `legacy/` | Skrip, data, dan keluaran pipeline lama (tidak dipakai lagi) |
| `Data BPBD/` | Data mentah BPBD, tidak di-commit (±1,4 GB) |

## Menjalankan

```
env\Scripts\python.exe -m pip install -r requirements.txt
git show 23854a4:padang_full.graphml > cache\graf_2026.10.16.graphml          # graf 8 Agustus 2026
env\Scripts\python.exe build_db.py --versi 2026.10.18 --graf cache\graf_2026.10.16.graphml   # ±3 menit; hasil identik (SHA-256 173b8010…)
env\Scripts\python.exe generate_dbml_file.py
env\Scripts\python.exe generate_erd_gambar.py
env\Scripts\python.exe analisis\simulasi_resmi_padang.py
env\Scripts\python.exe analisis\contoh_rute_evakuasi.py --buka
```

## Rilis DB untuk aplikasi

Repositori aplikasi (`AkuSukaProject/siagapadang`) terpisah dari engine ini. Setiap DB baru:

1. Jalankan `build_db.py --versi <versi baru>`, commit `hasil_build/`, lalu buat tag `db-<versi>` (misal `db-2026.10.18`). Satu label versi hanya untuk satu isi DB.
2. Terbitkan GitHub Release dari tag itu dengan lampiran `ranah_siaga_v4.db`, `ranah_siaga_v4.db.zip`, `dataset_manifest.json`, dan `dataset_manifest_android.json`.
3. Di komputer yang memiliki repo aplikasi: `env\Scripts\python.exe salin_db_ke_android.py <repo-aplikasi> --tulis`, lalu commit di repo aplikasi.

Sebelum build pertama, ekstrak `Data BPBD/SHP kecamatan.rar` ke `Data BPBD/SHP kecamatan/`.

Mulai membaca dari [docs/README.md](docs/README.md).
