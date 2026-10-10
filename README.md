# Siaga Padang — Core Engine

Pembangun database rute evakuasi tsunami Kota Padang untuk aplikasi Android Siaga Padang. Data bersumber dari BPBD Kota Padang (KRB 2023–2027, TES/TEA 2025) dan aturan evakuasi hasil wawancara BPBD.

## Struktur

| Lokasi | Isi |
|---|---|
| `build_db.py` | Engine: membangun isi `hasil_build/` dari data BPBD |
| `generate_dbml_file.py` | Membangkitkan ERD `docs/siaga_padang_erd.dbml` dari DB |
| `download_peta_full.py` | Mengunduh graf jalan pejalan kaki Kota Padang dari OSM (`padang_full.graphml`) |
| `hasil_build/` | Keluaran build: `ranah_siaga_v4.db` (database terbaru), `ranah_siaga_v4.db.zip` (paket untuk aplikasi, tidak di-commit), `dataset_manifest.json` (versi & checksum) |
| `analisis/` | Simulasi kanonis dan peta contoh rute (keluaran di `analisis/output/`) |
| `docs/` | Aturan evakuasi BPBD, arsitektur, ERD, hasil simulasi, panduan Android |
| `referensi/` | Dokumen rujukan (PDF KRB, peta jalur evakuasi, proposal) |
| `legacy/` | Skrip, data, dan keluaran pipeline lama (tidak dipakai lagi) |
| `Data BPBD/` | Data mentah BPBD, tidak di-commit (±1,4 GB) |

## Menjalankan

```
env\Scripts\python.exe -m pip install -r requirements.txt
env\Scripts\python.exe build_db.py                       # ±25 detik
env\Scripts\python.exe generate_dbml_file.py
env\Scripts\python.exe analisis\simulasi_resmi_padang.py
env\Scripts\python.exe analisis\contoh_rute_evakuasi.py --buka
```

Sebelum build pertama, ekstrak `Data BPBD/SHP kecamatan.rar` ke `Data BPBD/SHP kecamatan/`.

Mulai membaca dari [docs/README.md](docs/README.md).
