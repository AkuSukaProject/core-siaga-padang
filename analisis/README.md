# Analisis & Visualisasi

Skrip di folder ini membaca `hasil_build/ranah_siaga_v4.db` (hasil `build_db.py`) untuk analisis, simulasi, dan visualisasi. Skrip tidak mengubah database. Semua keluaran ditulis ke `analisis/output/`.

Jalankan dari root repositori atau dari mana saja (path diatur relatif terhadap lokasi skrip):

```
env\Scripts\python.exe analisis\simulasi_resmi_padang.py
```

| Skrip | Fungsi | Keluaran |
|---|---|---|
| `simulasi_resmi_padang.py` | Simulasi kanonis Baseline vs Siaga Padang (20.000 agen, seed 42). Tujuan: terjauh dari pantai di antara yang sempat ≤ 20 menit. Bawaan memakai rute zona aman `tb_safe_routes_v2`; `--rute-aman kontrak` untuk pembanding tabel lama | `peta_simulasi_berdampingan.html`, `hasil_simulasi_fasilitas.csv`, `hasil_simulasi_kelurahan.csv` (akhiran `_kontrak` untuk pembanding) |
| `contoh_rute_evakuasi.py` | Peta contoh rute evakuasi untuk satu posisi warga: TES rank 1–3, TEA, zona aman (`tb_safe_routes_v2`), zona merah, radius 1 km, jembatan sungai | `contoh_rute_<node>.html` (tidak di-commit) |

Contoh pemakaian `contoh_rute_evakuasi.py`:

```
env\Scripts\python.exe analisis\contoh_rute_evakuasi.py                    # TES acak + warga acak yang rute utamanya ke TES itu
env\Scripts\python.exe analisis\contoh_rute_evakuasi.py --tes "Hotel HW"   # TES tertentu (nama atau tes_id)
env\Scripts\python.exe analisis\contoh_rute_evakuasi.py --node 6080424191  # posisi warga tertentu
env\Scripts\python.exe analisis\contoh_rute_evakuasi.py --seed 7 --jumlah 3 --buka
```

Metodologi dan hasil resmi simulasi: [docs/simulasi_kanonis.md](../docs/simulasi_kanonis.md).

Skrip analisis atau visualisasi baru (peta, grafik, gambar proposal) diletakkan di folder ini dan harus membaca data dari `hasil_build/ranah_siaga_v4.db` atau `Data BPBD/`, bukan dari data lama di riwayat `legacy/`.
