# Handoff Backend: Dataset Siaga Padang V4

Halo Tim Backend (Sheva)!

Database offline `ranah_siaga_v4.db` versi **2026.10.12** dibangun dari data BPBD Kota Padang (KRB 2023–2027, TES/TEA 2025, daftar resmi BPBD 2019) dan mengikuti kontrak DB di `siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §1 dan §2.1. Sisi aplikasi ada di [handoff_android.md](handoff_android.md) (Mikail).

> **Versi 2026.10.12 menggantikan 2026.10.10 dan 2026.10.11.** Paket 2026.10.10 (`e0fc52de…`) yang sudah disimpan di Supabase belum mengikuti kontrak §2.1 (satuan ETA, kolom baru, syarat arah ±15°, jembatan ≥ 20 m). Mohon ganti paket yang di-*stage* dengan versi ini sebelum aktivasi.

---

## 1. Berkas

Ambil dari folder `hasil_build/` repo engine (atau lampiran GitHub Release tag `db-2026.10.12`):

| Berkas | Untuk |
|---|---|
| `ranah_siaga_v4.db` | Paket yang dilayani `/api/v1/sync/network` (SQLite mentah) dan masukan `stage_dataset_package.py` / `bootstrap_from_android_db.py` |
| `dataset_manifest_android.json` | Argumen `--manifest`: `version`, `checksum` (SHA-256 `.db`), `size_bytes` |
| `ranah_siaga_v4.db.zip` | Hanya bila unduhan awal saat startup (`app/main.py`) tetap memakai zip; isinya bernama `ranah_siaga_v4.db` |

| | `.db` | `.zip` |
|---|---|---|
| Ukuran (byte) | 29.974.528 | 6.287.484 |
| SHA-256 | `077edbc573e175606643decb1a9ed87a8c0bb93711caf27b99a956cb23789680` | `c848d90081359c0f76bc5aba080c680be6b042a744c0b4953ff7842f399f1d83` |

`hasil_build/dataset_manifest.json` (tanpa `_android`) adalah catatan engine; jangan dipakai sebagai manifest backend.

---

## 2. Langkah (mengikuti `backend/DATASET_V4_ROLLOUT.md`)

1. Stage paket: `python scripts/stage_dataset_package.py data/ranah_siaga_v4.db --manifest data/dataset_manifest_android.json`.
2. Setelah build Android 0.2.0 siap: `python scripts/bootstrap_from_android_db.py data/ranah_siaga_v4.db --manifest data/dataset_manifest_android.json --minimum-app-version 0.2.0 --download-url '/api/v1/sync/network?version=2026.10.12'`.
3. Periksa `/api/v1/sync/check`: `network` dan `shelters` versi `2026.10.12`, checksum di atas, ukuran 29.974.528; dropdown operator berisi 269 TES/TEA aktif.

Kecocokan dengan kode backend (branch `feat/final-keselamatan-navigasi`) sudah dicek dari kode sumber:
*   `validate_v4_schema`: `tb_safe_routes` dan `tb_safe_routes_v2` punya `safe_zone_id`, `kelompok`, `safe_node_id`, `safe_eta`, tidak kosong.
*   Bootstrap membaca `tb_tes` (`tes_id`, `nama_tes`, `kapasitas`, `lat`, `lon`, `zona`, **`lantai`**, **`sumber`**), `tb_tea` (ditambah `kelurahan`, `kecamatan`, **`sumber`**), `tb_inundation_zones`, `tb_safe_zones` (WKT `MULTIPOLYGON`), `tb_nodes`, dan `tb_edges`. Kolom tebal kini terisi, jadi `EvacuationPoint.floors` dan `source` (`BPBD`/`WARGA`) ikut terisi.
*   ID fasilitas unik; titik lama otomatis dinonaktifkan oleh bootstrap.

---

## 3. Perubahan isi yang perlu diketahui

*   **`tb_tes.kapasitas` bisa kosong** (77 dari 244 TES): kontrak meminta kapasitas kosong bila tidak ada data BPBD. Bootstrap sudah menyimpannya sebagai `NULL`.
*   **TEA**: 7 bernilai 0 (tidak ada data, disimpan `NULL` oleh bootstrap) dan 18 dengan angka BPBD 2025.
*   **`sumber`**: `BPBD` untuk 45 TES dari daftar resmi BPBD 2019 (3 shelter + 59 bangunan potensial), termasuk 14 TES baru (TES_235–TES_248) yang koordinatnya dari OpenStreetMap; `WARGA` untuk TES/TEA hasil digitasi Kelurahan Tangguh/latihan 2025.
*   **ID tidak berubah** dibanding 2026.10.10, kecuali TES_061, TES_126, TES_164 (titik ganda, digabung) dan TES_208 (Universitas Taman Siswa, "tidak potensial") yang tidak ada lagi.
*   **Satuan ETA** `rank_k_eta` dan `safe_eta` kini 1,2 m/s sesuai kontrak; tidak memengaruhi backend.
*   **`tb_nodes.jarak_pantai_m`** kolom baru; aplikasi lama (0.1.0) tidak bisa membuka DB ini, jadi `minimum_app_version` harus **0.2.0**.
*   `schema_version` tetap `android-v1`, sesuai `SUPPORTED_SCHEMA_VERSION` aplikasi.

---

## 4. Isi data (ringkas)

| Data | Nilai |
|---|---|
| TES / TEA dipakai | 244 / 25 |
| Simpang jalan / ruas / ruas jembatan ≥ 20 m | 31.813 (8.812 di zona merah) / 39.216 / 176 |
| Zona merah / zona hijau | 56 / 98 poligon (per kelurahan) |
| Penduduk terpapar | 242.750 jiwa di 56 kelurahan |

Struktur tabel: [erd_siaga_padang.md](erd_siaga_padang.md). Aturan evakuasi: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md).

---

## 5. Belum diuji dari sisi engine

Pemeriksaan di atas berasal dari kode sumber, belum dijalankan ke PostGIS. Mohon jalankan ulang uji staging seperti untuk 2026.10.10: stage, bootstrap ke DB staging, `/api/v1/sync/check`, dan unduhan dengan checksum yang cocok.
