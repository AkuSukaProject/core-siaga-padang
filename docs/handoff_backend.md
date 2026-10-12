# Handoff Backend: Dataset Siaga Padang 2026.10.14

**Untuk:** Sheva (backend) · **Dari:** Habib (engine DB, repo `core-siaga-padang`) · **Tanggal:** 12 Oktober 2026
**Acuan:** kontrak DB `siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §2.1 dan tugas S-6; alur rilis di `backend/DATASET_V4_ROLLOUT.md`. Sisi aplikasi: [handoff_android.md](handoff_android.md) (Mikail).

Kode yang dirujuk berasal dari branch `feat/final-keselamatan-navigasi` (commit `fcf0926`, 10 Oktober).

---

## 1. Ringkasan

| | |
|---|---|
| Versi dataset | **2026.10.14** |
| `.db` | 31.522.816 byte, SHA-256 `6fe87165e5b922a634825d8fd1af1bac0b42b632d8a32dd9333e23f7f336f8f0` |
| `.zip` | 6.677.497 byte, SHA-256 `e167927f29d19130cbffb9898c0ffcb25a5c61992cf386759ae88455d8819de6` |
| `schema_version` | `android-v1` (sama dengan `SUPPORTED_SCHEMA_VERSION` aplikasi) |
| `minimum_app_version` | **0.2.0** (aplikasi 0.1.0 tidak bisa membuka DB ini, lihat §4) |

> **Versi ini menggantikan 2026.10.12** (dan paket 2026.10.10 `e0fc52de…` yang sudah di-*stage* di Supabase, serta 2026.10.11 dan 2026.10.13 yang tidak dirilis). Bila 2026.10.12 sudah di-*stage*, biarkan tidak aktif dan *stage* versi ini. Mohon perbarui `backend/DATASET_V4_ROLLOUT.md` serta bagian "Dataset baru" di `docs/backend_documentation.md` ke versi, checksum, dan ukuran di atas.
>
> **Yang berubah dari 2026.10.12:** (1) isi rute, karena aturan baru "tujuan terjauh dari pantai yang masih sempat ≤ 20 menit" (handoff Android §0); (2) **poligon zona merah dan zona hijau lebih presisi** (§5.3). Skema, fasilitas, ID, nama, dan kapasitas sama, jadi langkah backend tidak berubah. `tb_safe_routes_v2` kini 8.808 baris dan diusulkan menjadi tabel navigasi wajib di aplikasi (menunggu persetujuan Mikail).

---

## 2. Berkas

Ambil dari `hasil_build/` repo engine, lampiran GitHub Release `db-2026.10.14`, atau paket `kirim_siaga_padang_2026.10.14.zip`:

| Berkas | Untuk |
|---|---|
| `ranah_siaga_v4.db` | Paket yang dilayani `/api/v1/sync/network` (SQLite mentah), masukan `stage_dataset_package.py` dan `bootstrap_from_android_db.py` |
| `dataset_manifest_android.json` | Argumen `--manifest`: `{"version": "2026.10.14", "checksum": "6fe87165…", "size_bytes": 31522816}` |
| `ranah_siaga_v4.db.zip` | Hanya bila unduhan awal saat startup (`app/main.py`) tetap memakai zip; isinya bernama `ranah_siaga_v4.db` |

`hasil_build/dataset_manifest.json` (tanpa `_android`) adalah catatan engine (checksum zip dan `.db`); jangan dipakai sebagai manifest.

---

## 3. Langkah rilis (mengikuti `DATASET_V4_ROLLOUT.md`)

1. **Simpan berkas** di komputer backend: `data/ranah_siaga_v4.db` dan `data/dataset_manifest_android_v4.json` (isi = `dataset_manifest_android.json`).
2. **Stage paket** ke database server, tanpa aktivasi:
   ```sh
   python scripts/stage_dataset_package.py data/ranah_siaga_v4.db \
     --manifest data/dataset_manifest_android_v4.json
   ```
3. **Uji di staging** (`siaga_padang_v4_staging`), seperti uji 10 Oktober: migrasi, stage, bootstrap, `/api/v1/sync/check`, unduhan dengan checksum cocok.
4. **Setelah build Android 0.2.0 siap dan diuji di HP** (Mikail):
   ```sh
   python scripts/bootstrap_from_android_db.py data/ranah_siaga_v4.db \
     --manifest data/dataset_manifest_android_v4.json \
     --minimum-app-version 0.2.0 \
     --download-url '/api/v1/sync/network?version=2026.10.14'
   ```
5. **Periksa:**
   *   `/api/v1/sync/check`: `network` dan `shelters` versi `2026.10.14`, checksum `6fe87165…`, `size_bytes` 31522816, `minimum_app_version` 0.2.0.
   *   `/api/v1/sync/network?version=2026.10.14`: SHA-256 hasil unduhan sama.
   *   Dropdown TES/TEA operator berisi **269** titik aktif (244 TES + 25 TEA).
   *   Lapor selamat ke salah satu TES baru (misalnya TES_246 Hotel Ibis) diterima.
6. **Kabari Mikail** bila versi sudah aktif, supaya pembaruan lewat jaringan diuji dari HP.

---

## 4. Kecocokan dengan kode backend

Dicek dari kode sumber (belum dijalankan ke PostGIS):

| Pemeriksaan backend | DB 2026.10.14 |
|---|---|
| `validate_v4_schema`: `tb_safe_routes` (`origin_node_id`, `safe_node_id`, `safe_eta`, `safe_zone_id`) dan `tb_safe_routes_v2` (+ `kelompok`), tidak kosong | Lolos (30.765 dan 8.808 baris) |
| `validate_v4_minimum_app_version` menolak `0.1.0` | Gunakan `0.2.0` |
| Bootstrap `tb_tes`: `tes_id`, `nama_tes`, `kapasitas`, `lat`, `lon`, opsional `zona`, `lantai`, `sumber` | Semua ada. `lantai` dan `sumber` kini terisi |
| Bootstrap `tb_tea`: `tea_id`, `nama_tea`, `kapasitas`, `lat`, `lon`, opsional `kelurahan`, `kecamatan`, `sumber` | Semua ada |
| ID fasilitas unik | Ya (bootstrap menolak ID ganda) |
| `tb_inundation_zones` / `tb_safe_zones`: `nama_zona`, `geometry_wkt`, `tingkat_bahaya` | Ada; WKT `MULTIPOLYGON` 2D 7 desimal |
| `tb_nodes` (`node_id`, `lon`, `lat`) dan `tb_edges` (`edge_id`, `u`, `v`, `geometry`) untuk `RouteEdge` | Ada (31.813 simpul, 39.216 ruas) |
| `verify_package` (ukuran + SHA-256) | Cocok dengan manifest |

Kolom baru `tb_nodes.jarak_pantai_m` (kontrak §2.1) membuat `NodeEntity` aplikasi 0.1.0 menolak DB ini (validasi Room). Karena itu `minimum_app_version` **wajib** 0.2.0, bukan sekadar disarankan. Alasannya kolom ini. Tabel `tb_safe_routes_v2` sudah ada sejak versi sebelumnya, jadi `validate_v4_schema` tetap lolos.

---

## 5. Perubahan data yang memengaruhi backend

### 5.1 Titik evakuasi (`EvacuationPoint`)
| | Jumlah | Catatan |
|---|---|---|
| TES aktif | 244 | 45 `source = BPBD`, 199 `source = WARGA` |
| TEA aktif | 25 | semua `WARGA` (digitasi Kelurahan Tangguh/latihan 2025) |
| **TES baru** dibanding 2026.10.10 | 14 | TES_235–TES_248: bangunan daftar resmi BPBD 2019 (Hotel Inna Muara, Hotel Rocky, Axana Hotel, Bumi Minang Hotel, Damar Plaza, Masjid Al Wustha, PT Sutan Kasim, Rusunawa, Hotel Grand Zuri, Dinas Peternakan Prov. Sumbar, Basko Hotel & Plaza, Hotel Ibis, Daihatsu & ACC Finance, Universitas Bung Hatta). Koordinat dari OpenStreetMap; sedang dikonfirmasi ke BPBD |
| **Tidak aktif lagi** dibanding 2026.10.10 | 4 | TES_061, TES_126, TES_164 (titik ganda, digabung ke TES_060, TES_127, TES_163) dan TES_208 (Universitas Taman Siswa, "tidak potensial"). Bootstrap otomatis menonaktifkannya (`is_active = false`) |
| ID dataset 2026.09.28 di produksi (`TES_1…TES_143`, `TEA_A1…`) | – | Juga dinonaktifkan otomatis. Rekap lapor selamat lama tetap tersimpan |
| Nama berubah agar unik | 11 | misalnya "Bukit Lampu (Bungus Barat)", "FK Unand (area evakuasi)" (TEA). Snapshot nama di latihan lama tidak berubah |

ID lain tidak berubah. Bila ada sesi latihan atau data uji yang memakai ID yang dinonaktifkan, perbarui ke ID baru.

### 5.2 Kapasitas
*   `tb_tes.kapasitas` **kosong (NULL) untuk 77 TES**: kontrak meminta kapasitas kosong bila tidak ada data daya tampung BPBD. Bootstrap menyimpannya sebagai `capacity = NULL`.
*   167 TES punya angka dari BPBD: data 2025 (155), daftar resmi 2019 (11), verifikasi 2019 (1).
*   TEA: 7 bernilai 0 (disimpan `NULL` oleh bootstrap), 18 punya angka BPBD 2025.
*   Rekap Pusdalops sebaiknya menampilkan "daya tampung belum ada data" untuk `NULL`, bukan 0.

### 5.3 Zona
`tb_inundation_zones` 56 poligon (zona merah per kelurahan dari raster KRB 2023–2027, `tingkat_bahaya` selalu `Tinggi`) dan `tb_safe_zones` 96 poligon. Bootstrap mengganti seluruh isi `InundationZone` dan `SafeZone`.

Sejak 2026.10.14 poligonnya lebih presisi: tepi mengikuti raster tanpa tangga 30 m, dipotong ke daratan menurut garis pantai OSM (sebelumnya 329 ha zona merah dan 55 ha zona hijau berada di laut), dan pita pantai yang di luar batas kelurahan BPBD (59 ha) kini ikut zona merah. Olo dan Air Tawar Barat tidak lagi punya zona hijau, karena seluruh daratannya masuk landaan; "zona hijau" lamanya hanya serpihan 0,5 ha dan 0,15 ha. Bila operator melihat peta zona di dasbor, bentuknya akan sedikit berbeda dari versi sebelumnya.

### 5.4 Jaringan jalan
Graf tetap 31.813 simpul dan 39.216 ruas (sama dengan versi lama), jadi `RouteEdge` hanya dibuat ulang untuk `dataset_version` baru. Ruas jembatan ≥ 20 m ada di `tb_bridge_edges` (176) bila nanti dibutuhkan untuk laporan jalan terhalang.

---

## 6. Hal lain di sisi backend

1. **Unduhan awal saat startup** (`app/main.py`): URL Google Drive masih menunjuk ke DB lama. Ganti ke paket 2026.10.14 (Release `db-2026.10.14` atau Drive baru). Isi zip bernama `ranah_siaga_v4.db`, jadi ganti nama setelah ekstraksi atau atur `DATASET_PACKAGE_PATH`. Karena paket kini disimpan di database server, langkah ini hanya cadangan.
2. **Rollback:** bila versi baru bermasalah, aktifkan kembali `DataVersion` sebelumnya. Aplikasi 0.2.0 menolak dataset lama tanpa kolom baru bila `DatasetPackageInstaller` sudah diperketat (handoff Android §4.5).
3. **Dokumen:** perbarui `backend/DATASET_V4_ROLLOUT.md` dan `docs/backend_documentation.md` (bagian "Dataset baru") ke 2026.10.14.

---

## 7. Isi data (ringkas)

| Data | Nilai |
|---|---|
| TES / TEA aktif | 244 / 25 |
| Simpang / ruas / ruas jembatan ≥ 20 m | 31.813 (8.808 di zona merah) / 39.216 / 176 |
| Zona merah / zona hijau | 56 / 96 poligon |
| Penduduk terpapar | 242.750 jiwa di 56 kelurahan |
| Laju & batas waktu (engine) | 0,894 m/s, 20 menit; kolom ETA di DB pada 1,2 m/s |

Struktur tabel: [erd_siaga_padang.md](erd_siaga_padang.md). Aturan evakuasi: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md). Hal yang masih ditanyakan ke BPBD (bisa memunculkan versi DB berikutnya): [pertanyaan_bpbd.md](pertanyaan_bpbd.md).
