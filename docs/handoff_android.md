# Handoff Android: Integrasi Database Siaga Padang V4

Halo Tim Android (Mikail)!

Database `ranah_siaga_v4.db` dibangun dari data BPBD Kota Padang (KRB 2023–2027, TES/TEA 2025, daftar resmi BPBD 2019) dan **mengikuti kontrak DB** di `siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §1 (asumsi kerja) dan §2.1 (isi DB). Dokumen ini merangkum yang perlu disesuaikan di aplikasi (Kotlin/Room). Sisi backend: [handoff_backend.md](handoff_backend.md) (Sheva).

> **Versi: 2026.10.12.** `.db` berukuran 29.974.528 byte, SHA-256 `077edbc573e175606643decb1a9ed87a8c0bb93711caf27b99a956cb23789680`. Versi ini menggantikan 2026.10.10 dan 2026.10.11.
>
> Build aplikasi yang memakai DB ini direncanakan **0.2.0 (versionCode 3)**. Backend memakai versi itu sebagai `minimum_app_version`.

---

## 1. Berkas

Ambil dari folder `hasil_build/` repo engine (atau lampiran GitHub Release tag `db-2026.10.12`):

| Berkas | Taruh sebagai |
|---|---|
| `ranah_siaga_v4.db` | `android/app/src/main/assets/ranah_siaga.db` |
| `dataset_manifest_android.json` | `android/app/src/main/assets/dataset_manifest.json` |

Cara paling aman: jalankan `salin_db_ke_android.py <repo-aplikasi> --tulis` dari repo engine. Skrip ini memeriksa checksum lalu menyalin kedua berkas dengan nama yang benar. `dataset_manifest.json` (tanpa `_android`) dan `.zip` di `hasil_build/` **bukan** untuk aplikasi.

Aset yang terbundel sekarang (`ranah_siaga.db` 13 September, 130 MB) adalah DB lama dan manifestnya tidak cocok. Ganti kedua berkas sekaligus.

---

## 2. Kesesuaian dengan kontrak §2.1

| Butir kontrak | Isi DB 2026.10.12 |
|---|---|
| `rank_k_tes` berisi nama TES yang unik | Ya. 269 nama fasilitas (TES + TEA) tanpa duplikat |
| `rank_k_eta` dan `safe_eta` dihitung pada **1,2 m/s** | Ya. Aplikasi mengalikan 1,2 ÷ 0,89 (M-3). Batas 20 menit pada laju FEMA setara `eta` ≤ 14,9 di tabel |
| `tb_edges` ruas lurus tanpa geometri, urutan lon lat | Ya |
| `tb_safe_routes.safe_eta = 0` menandai tujuan zona hijau | Ya (tidak pernah 0 di zona merah) |
| Pola `tb_tea_*`, `tb_safe_*` | Sama |
| Poligon WKT `MULTIPOLYGON` 2D, 7 desimal | Ya |
| Ukuran ≤ 75 MB | 29,97 MB |
| `tb_tes`: `sumber`, `jarak_pantai_m`, `kapasitas` kosong bila tidak ada data, `lantai` | Ya (lihat 3.B) |
| `tb_tea.jarak_pantai_m` | Ya (ditambah `sumber`) |
| `tb_nodes.jarak_pantai_m`, `is_safe` dari zona rendaman baru | Ya (lihat 3.A) |
| `tb_inundation_zones` dari data zona BPBD | Ya, raster KRB 2023–2027, satu baris per kelurahan, `tingkat_bahaya` selalu `Tinggi` |
| `tb_kelurahan` | Tidak dibuat: poligon zona tetap per kelurahan |
| `tb_bridge_edges(edge_id)` jembatan ≥ 20 m | Ya, 176 ruas (badan jembatan OSM ≥ 20 m; pembanding tim 177) |
| Rute dihitung ulang dengan aturan arah dan jembatan; `rank_2`/`rank_3` boleh kosong | Ya (lihat 3.C) |
| `v_fasilitas_evakuasi` + kolom `sumber` | Ya |
| `dataset_manifest.json` (`version`, `checksum`, `size_bytes`) | `dataset_manifest_android.json` |

Ke-21 kueri `@Query` aplikasi (branch `feat/final-keselamatan-navigasi`) sudah diuji berjalan pada DB ini.

---

## 3. Yang wajib disesuaikan di aplikasi (M-9)

### A. `NodeEntity` mendapat kolom baru
`tb_nodes` sekarang `(node_id INTEGER PRIMARY KEY, lat REAL, lon REAL, is_safe INTEGER DEFAULT 0, jarak_pantai_m INTEGER)`. Room memvalidasi tabel ini saat menyalin DB dari aset, jadi tambahkan field `@ColumnInfo(name = "jarak_pantai_m") val jarakPantaiM: Int?` di `NodeEntity`. Tanpa itu aplikasi berhenti saat membuka DB. Indeks `idx_tb_nodes_lat_lon` tetap ada.

### B. `tb_tes.kapasitas` bisa kosong
Kontrak meminta kapasitas kosong bila tidak ada data daya tampung BPBD (nilai bawaan tidak dipakai lagi). 77 dari 244 TES kosong. `TesRow.kapasitas` sekarang `Double` non-null; ubah menjadi `Double?`. `FacilityRow.kapasitas` sudah nullable.

Kolom baru `tb_tes`: `sumber` (`BPBD` atau `WARGA`), `jarak_pantai_m`, `lantai` (boleh kosong).

### C. Rute
*   **Syarat arah (K-B1)** sudah diterapkan saat prakomputasi untuk TES rank 1–3, TEA, dan rute zona aman v2: tujuan harus menjauh dari pantai lebih dari 15° (engine memakai rasio > 0,27, sedikit di atas ambang 0,26 skrip audit, agar tahan pembulatan); tujuan ≤ 100 m tidak dinilai. Skrip `docs/audit/analisis_masukan_bpbd.py` yang dijalankan apa adanya pada DB ini: **tujuan utama 0% mendekat, 0% sejajar** (DB 2026.09.28: 35,2% dan 18,5%). Jangan menambah logika "TES terdekat" sendiri.
*   **Jembatan ≥ 20 m (K-B2)** dihindari. Rute lewat jembatan hanya dipakai bila tujuan itu tidak terjangkau tanpa jembatan. Ruasnya ada di `tb_bridge_edges`, sehingga keterangan "lewat jembatan" (M-8) bisa dibaca dari `edge_id` ruas rute.
*   **`rank_2_*` dan `rank_3_*` boleh `NULL`** (187 dan 869 simpul). `RouteRow` perlu menerimanya.
*   `tb_routes` hanya berisi simpul **zona merah** yang punya TES lolos syarat (8.728 dari 8.812). Bila tidak ada baris: `is_safe = 1` berarti sudah di zona aman; selain itu pakai TEA atau zona aman v2.

### D. Rute zona aman memakai tabel v2
`tb_safe_routes` / `tb_safe_next` adalah satu pohon untuk semua simpang dan tidak menjamin syarat arah. Untuk **navigasi**, pakai `tb_safe_routes_v2` + `tb_safe_next_v2`. Perubahan di `EvacuationDao.kt` cukup dua:
*   `findSafeRoute`: `FROM tb_safe_routes` → `FROM tb_safe_routes_v2` (kolom `safe_zone_id`, `safe_node_id`, `safe_eta` sama), ambil juga `kelompok`.
*   `findSafePathSteps`: `tb_safe_next` → `tb_safe_next_v2` di kedua tempat, tambahkan `kelompok = :kelompok` di kedua `WHERE`/`JOIN`.

`kelompok` adalah kunci rantai (nomor gerbang tujuan) milik **simpul asal**; ikuti next-hop sampai simpul tanpa baris, yang sama dengan `safe_node_id`. Saat pengguna berpindah, pakai simpul asal baru beserta `kelompok`-nya.

`tb_safe_routes` tidak lagi berisi baris untuk 1.019 simpul merah yang tujuan pohon global-nya tidak lolos syarat arah, sehingga tabel lama pun tidak pernah menawarkan rute ke arah pantai.

Dua kueri di `ZoneDao.kt` **tetap** memakai `tb_safe_routes`: `findSafeRouteEta` dan `findSafeZoneTargetGeometries`. Tabel lama berisi semua simpang, dan `safe_eta = 0` tepat pada tujuan zona hijau (bukan kantong aman < 50 ha), sehingga cocok untuk status "sudah tiba".

`tb_safe_routes_v2` berisi 8.795 dari 8.812 simpul merah. 17 simpul tidak punya zona aman yang lolos syarat arah; untuk mereka TES/TEA tetap ada.

### E. Nilai kolom lain
*   `tb_inundation_zones.tingkat_bahaya` selalu `Tinggi`: peta hanya merah dan hijau (K-B4).
*   `tb_tea.kapasitas = 0` berarti tidak ada data, bukan nol orang. TEA tidak dibatasi kapasitas.
*   ID fasilitas `TES_001…`, `TEA_001…`. Dibanding 2026.10.10, TES_061, TES_126, TES_164 (titik ganda) dan TES_208 (Universitas Taman Siswa, "tidak potensial") tidak ada lagi; ID lain tidak berubah. Beberapa nama diberi kelurahan agar unik, misalnya "Bukit Lampu (Bungus Barat)".
*   244 TES (45 bersumber BPBD, 199 WARGA) dan 25 TEA. 14 bangunan daftar resmi BPBD 2019 yang tidak punya titik di data 2025 ditambahkan sebagai TES_235–TES_248 (koordinat dari OpenStreetMap, nama dan jalannya cocok dengan alamat BPBD; ditandai di `tb_fasilitas_info.koordinat_sumber`, perlu verifikasi lapangan). 11 TES lama ternyata bangunan daftar resmi dengan nama lain, sehingga kini bersumber BPBD.

### F. Lapis "Kesepakatan warga" (K-B5)
`sumber = 'BPBD'` hanya untuk TES yang cocok dengan daftar resmi BPBD 2019 (3 shelter + 59 bangunan potensial, Bidang RR). Selebihnya hasil digitasi Kelurahan Tangguh/latihan 2025 (`WARGA`). Keduanya dipakai routing. Label sumber ditampilkan di aplikasi sesuai keputusan K-B5.

---

## 4. Navigasi

*   **TES**: `rank_X_path` (ID node dipisah koma, dari asal ke TES).
*   **TEA**: `tb_tea_routes` untuk memilih TEA, lalu `SELECT * FROM tb_tea_next WHERE tea_id = ?` sekali dan rangkai di memori.
*   **Zona aman**: `tb_safe_routes_v2` untuk simpul pengguna, lalu `SELECT node_id, next_node_id FROM tb_safe_next_v2 WHERE kelompok = ?` sekali.
*   **Tujuan utama (K-B6)**: bila sempat dalam 20 menit pada laju rujukan, keluar zona (TEA atau zona aman) didahulukan; bila tidak, TES tercepat. `tb_route_shares` (opsi A) sudah memakai kebijakan ini.

---

## 5. Data pendukung (opsional)

*   `tb_jalur_resmi`: ruas yang mengikuti jalur evakuasi resmi BPBD.
*   `tb_kelurahan_info`: profil tsunami per kelurahan (jiwa terpapar, kelompok rentan, kelas risiko).
*   `tb_fasilitas_info`: semua TES/TEA termasuk yang tidak dipakai beserta alasannya, sumber kapasitas, dan estimasi kapasitas untuk TES tanpa data BPBD.
*   `tb_route_shares`: porsi tujuan per simpul (opsi A).
*   Di `hasil_build/`: `daftar_tes_tea.csv` (H-1), `peta_celah_kelurahan.csv` (H-7), `bpbd_2019_tanpa_titik.csv` (17 bangunan daftar resmi BPBD yang belum punya titik koordinat).
