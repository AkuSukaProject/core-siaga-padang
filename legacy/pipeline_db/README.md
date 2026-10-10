# Pipeline Lama (Arsip)

Folder ini berisi pipeline pembangun database sebelum versi 4. **Tidak dipakai lagi.** Database sekarang dibangun oleh [`build_db.py`](../../build_db.py) dari data BPBD (lihat [docs/build_db_v4.md](../../docs/build_db_v4.md)).

| Berkas | Dulu menghasilkan |
|---|---|
| `core.py` | `ranah_siaga.db` (143 TES, zona merah berbasis kelurahan) |
| `build_db_v2_with_tea.py` | `ranah_siaga_v2.db` (+ 12 TEA) |
| `spatial/1..5` | `ranah_siaga_v3.db` (kapasitas, rute zona aman, porsi, pengecilan DB, simulasi agen) |

Alasan diarsipkan: memakai data TES 2013–2019 dan CSV turunannya, kecepatan 1,2 m/s, belum menerapkan aturan menjauhi pantai dan jembatan, dan zona merah berbasis kelurahan, bukan raster bahaya BPBD.

Skrip di sini tidak dijamin bisa dijalankan dari lokasi barunya. Path relatifnya masih mengacu ke root repositori, dan berkas DB lama sudah dihapus dari folder kerja (masih bisa diambil dari riwayat git). Simpan hanya sebagai rujukan metodologi.
