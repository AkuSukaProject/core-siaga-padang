# Handoff Android: Database Siaga Padang 2026.10.12

**Untuk:** Mikail (Android) · **Dari:** Habib (engine DB, repo `core-siaga-padang`) · **Tanggal:** 11 Oktober 2026
**Acuan:** kontrak DB di `siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §1 (asumsi kerja) dan §2.1 (isi DB); tugas terkait M-3, M-8, M-9. Sisi server: [handoff_backend.md](handoff_backend.md) (Sheva).

Kode yang dirujuk berasal dari branch `feat/final-keselamatan-navigasi` (commit `fcf0926`, 10 Oktober). Ke-21 kueri `@Query` di branch itu sudah diuji berjalan pada DB ini. Perubahan **wajib** di §4.1–§4.6 semuanya berasal dari kontrak §2.1 dan tugas M-3, M-8, M-9; §4.7 adalah tambahan opsional di luar kontrak.

---

## 1. Ringkasan

| | |
|---|---|
| Versi dataset | **2026.10.12** (menggantikan 2026.10.10 dan 2026.10.11; jangan pakai keduanya) |
| Berkas | `ranah_siaga_v4.db`, 29.974.528 byte, SHA-256 `077edbc573e175606643decb1a9ed87a8c0bb93711caf27b99a956cb23789680` |
| Ukuran (NF-03) | 29,97 MB desimal (batas 75 MB) |
| Versi aplikasi yang memakai DB ini | **0.2.0, versionCode 3** (backend memakainya sebagai `minimum_app_version`) |
| Skema Room | `android-v1` tetap, tetapi `NodeEntity` wajib menambah satu kolom (§4.1) |

Yang berubah dari DB 2026.09.28 yang sekarang dipakai aplikasi:
1. **Data baru BPBD**: zona merah dari KRB 2023–2027, 244 TES (45 bersumber BPBD, 199 WARGA), 25 TEA, penduduk terpapar 242.750 jiwa.
2. **Aturan BPBD tertanam di rute**: tujuan harus menjauhi pantai (tidak boleh sejajar), jembatan ≥ 20 m dihindari, keluar zona dulu bila sempat.
3. **Satuan ETA tetap 1,2 m/s** (kontrak); aplikasi mengonversi ke 0,89 m/s (M-3).
4. **Kolom dan tabel baru** sesuai kontrak: `jarak_pantai_m`, `sumber`, `lantai`, `tb_bridge_edges`. Ada juga tabel rute zona aman v2 di luar kontrak, **opsional** (§4.7).
5. **Nilai yang boleh kosong**: `tb_tes.kapasitas`, `rank_2_*`, `rank_3_*`.

---

## 2. Berkas dan cara memasang

Ambil dari `hasil_build/` repo engine, lampiran GitHub Release `db-2026.10.12`, atau paket `kirim_siaga_padang_2026.10.12.zip`:

| Berkas | Taruh sebagai |
|---|---|
| `ranah_siaga_v4.db` | `android/app/src/main/assets/ranah_siaga.db` |
| `dataset_manifest_android.json` | `android/app/src/main/assets/dataset_manifest.json` |

Isi manifest:
```json
{
  "version": "2026.10.12",
  "checksum": "077edbc573e175606643decb1a9ed87a8c0bb93711caf27b99a956cb23789680",
  "size_bytes": 29974528
}
```

Cara paling aman: dari repo engine jalankan `env\Scripts\python.exe salin_db_ke_android.py <repo-aplikasi> --tulis`. Skrip memeriksa checksum lalu menyalin kedua berkas dengan nama yang benar. `dataset_manifest.json` (tanpa `_android`) dan `.zip` di `hasil_build/` **bukan** untuk aplikasi.

Aset yang terbundel sekarang (`ranah_siaga.db` 13 September, 130 MB) adalah DB lama: belum punya `tb_safe_routes` dan indeks `idx_tb_nodes_lat_lon`, dan manifestnya menyebut versi lain (2026.09.28, 71 MB). Ganti **kedua** berkas sekaligus; `DatasetStorage.refreshBundledCopyIfAssetChanged` lalu menyalin ulang DB karena checksum berubah. Perbarui juga `EvacuationRepository.DEFAULT_DATASET_VERSION` dari `"2026.09.28"` menjadi `"2026.10.12"`.

---

## 3. Isi DB terhadap kontrak §2.1

| Butir kontrak | DB 2026.10.12 |
|---|---|
| `rank_k_tes` berisi nama TES yang unik | Ya. 269 nama fasilitas (TES + TEA) tanpa duplikat |
| `rank_k_path` deretan `node_id` dipisah koma | Ya |
| `rank_k_eta` dan `safe_eta` pada **1,2 m/s** | Ya. 20 menit pada laju FEMA = `eta` ≤ 14,9 menit di tabel |
| `tb_edges` ruas lurus tanpa geometri, urutan lon lat | Ya (18.961 ruas tanpa geometri) |
| `tb_safe_routes.safe_eta = 0` menandai tujuan zona hijau | Ya, tidak pernah 0 di zona merah |
| Pola `tb_tea_*`, `tb_safe_*` | Sama. Rute zona aman di `tb_safe_routes` / `tb_safe_next` dihitung ulang dan patuh syarat arah (§4.3) |
| Poligon WKT `MULTIPOLYGON` 2D, 7 desimal | Ya, semua poligon |
| Ukuran ≤ 75 MB | 29,97 MB |
| `tb_tes`: `sumber`, `jarak_pantai_m`, `kapasitas` kosong bila tidak ada data, `lantai` | Ya |
| `tb_tea.jarak_pantai_m` | Ya (ditambah `sumber`) |
| `tb_nodes.jarak_pantai_m`, `is_safe` dari zona rendaman baru | Ya |
| `tb_inundation_zones` dari zona BPBD | Ya, raster KRB 2023–2027, satu baris per kelurahan (56) |
| `tb_safe_zones` zona hijau baru | Ya (98) |
| `tb_kelurahan` | Tidak dibuat: poligon zona tetap per kelurahan, jadi tidak diperlukan |
| `tb_bridge_edges(edge_id)` jembatan ≥ 20 m | Ya, 176 ruas (pembanding tim: 177) |
| Rute dihitung ulang dengan aturan arah dan jembatan | Ya. Skrip `docs/audit/analisis_masukan_bpbd.py` dijalankan apa adanya pada DB ini: tujuan utama **0% mendekat, 0% sejajar** (DB 2026.09.28: 35,2% dan 18,5%) |
| `rank_2`/`rank_3` boleh kosong | Ya (187 dan 869 simpul) |
| `v_fasilitas_evakuasi` + `sumber` | Ya |
| Manifest `version`, `checksum`, `size_bytes` | `dataset_manifest_android.json` |

---

## 4. Perubahan kode (wajib: §4.1–§4.6 dari kontrak; opsional: §4.7)

### 4.1 `NodeEntity.kt`: kolom baru `jarak_pantai_m`
Room memvalidasi `tb_nodes` saat menyalin DB dari aset. Skema baru:
```sql
CREATE TABLE tb_nodes (node_id INTEGER PRIMARY KEY, lat REAL, lon REAL, is_safe INTEGER DEFAULT 0, jarak_pantai_m INTEGER)
-- indeks tetap: CREATE INDEX idx_tb_nodes_lat_lon ON tb_nodes(lat, lon)
```
Tambahkan:
```kotlin
@ColumnInfo(name = "jarak_pantai_m") val jarakPantaiM: Int?,
```
Tanpa ini, Room menolak DB dan aplikasi berhenti saat pertama dibuka. Akibatnya juga, **aplikasi 0.1.0 tidak bisa membuka DB ini**, sehingga backend wajib memakai `minimum_app_version = 0.2.0`.

### 4.2 `DatabaseRows.kt`: kolom yang boleh kosong
| Kelas | Perubahan | Alasan |
|---|---|---|
| `RouteRow` | `rank2Tes`, `rank2Path`, `rank2Eta`, `rank3Tes`, `rank3Path`, `rank3Eta` → nullable (`String?`, `Double?`) | Kontrak: rank 2/3 boleh kosong. 187 simpul tanpa rank 2, 869 tanpa rank 3. Saat ini bertipe non-null, jadi pembacaan baris itu gagal |
| `TesRow` | `kapasitas: Double` → `Double?` | 77 dari 244 TES tidak punya daya tampung dari data BPBD (kontrak: kosong, bukan nilai bawaan) |

Lalu sesuaikan pemakainya di `EvacuationRepository.kt`:
*   `RouteRow.select(rank)` (± baris 609): bila `rankNTes == null`, rank itu tidak ada. `loadRoute(originNodeId, rank)` sebaiknya mengembalikan `null` atau melempar error yang ditangani, bukan crash.
*   `countAlternativeDestinations` (± baris 210): `listOf(row.rank1Tes, row.rank2Tes, row.rank3Tes).filterNotNull().filter(String::isNotBlank)`.
*   `findRouteToFacility` (± baris 233) dan `AlternativeRouteSelector` / F-08: lewati rank yang kosong.
*   Tampilan kapasitas TES (direktori, balon): `null` = "daya tampung belum ada data", bukan 0.

### 4.3 Rute zona aman: tidak ada perubahan kode
Sesuai kontrak, `tb_safe_routes` / `tb_safe_next` tetap berpola sama dan dihitung ulang dengan aturan arah. Kueri `EvacuationDao.findSafeRoute`, `findSafePathSteps`, dan `ZoneDao.findSafeRouteEta`, `findSafeZoneTargetGeometries` **tidak perlu diubah**.

Yang berubah hanya isinya:
*   **Semua rute zona aman di tabel ini lolos syarat arah.** 7.793 simpul merah punya rute; semuanya menjauh dari pantai (atau ≤ 100 m), dan rantai `tb_safe_next` dari tiap simpul berakhir di `safe_node_id`-nya.
*   **1.019 simpul merah tidak punya baris**, karena zona aman terdekatnya tidak lolos syarat arah (misalnya sejajar pantai). Untuk mereka `findSafeRoute` mengembalikan `null`, dan aplikasi memakai TES/TEA, seperti yang sudah ditangani `runCatching`/`?: return` di `EvacuationRepository`. Bila ingin simpul-simpul ini tetap punya rute zona aman, lihat §4.7.
*   Semua simpul aman tetap punya baris dengan `safe_eta = 0`, jadi status "sudah tiba" tidak berubah.

### 4.4 Satuan waktu tempuh (M-3)
| Sumber waktu di aplikasi | Perlakuan |
|---|---|
| `rank_k_eta`, `safe_eta` dari DB (menit pada 1,2 m/s) | Kalikan 1,2 ÷ 0,89 (`EvacuationRepository.loadRoute` ± baris 256, `buildSafeZoneRoute`) |
| Panjang jalur dibagi laju (TEA, jalan memutar, `RequiredPaceAdvisor`, ± baris 322, 360, 410, 420) | Ganti `WALKING_SPEED_METERS_PER_SECOND` ke 0,89 m/s; **jangan** dikalikan lagi |
| `estimatedDistanceMeters = estimatedSeconds × laju` (± baris 85) | Gunakan laju yang sama dengan yang membentuk `estimatedSeconds`, atau hitung jarak langsung dari panjang ruas |

Bila M-3 belum dikerjakan, jangan memasang DB ini dulu: ETA di DB pada 1,2 m/s akan tampil apa adanya (terlalu cepat untuk orang terlemah).

### 4.5 `DatasetPackageInstaller.kt` (pembaruan lewat jaringan)
`REQUIRED_COLUMNS` saat ini cocok dengan DB ini. Saran (bukan kontrak): untuk 0.2.0, tambahkan pemeriksaan kolom yang kini dibaca aplikasi, agar paket lama ditolak sebelum diaktifkan:
*   `tb_nodes`: tambah `jarak_pantai_m`
*   `tb_bridge_edges`: `edge_id` (bila M-8 membacanya)
*   `tb_safe_routes_v2`, `tb_safe_next_v2`: hanya bila memakai §4.7

### 4.6 Versi aplikasi
`android/app/build.gradle.kts`: `versionName = "0.2.0"`, `versionCode = 3` (kesepakatan dengan Sheva untuk `minimum_app_version`).

### 4.7 Opsional, di luar kontrak: rute zona aman v2
DB juga berisi `tb_safe_routes_v2` dan `tb_safe_next_v2`. Isinya rute zona aman per simpul merah yang syarat arahnya dinilai per pasangan warga–tujuan, sehingga **8.795** simpul merah punya rute (tabel lama: 7.793). Tabel ini tidak ada di kontrak §2.1; memakainya adalah keputusan Mikail. Bila tidak dipakai, tidak ada yang rusak.

Bila dipakai, perubahannya:
*   `SafeRouteRow`: tambah `@ColumnInfo(name = "kelompok") val kelompok: Long?`.
*   `EvacuationDao.findSafeRoute`:
```sql
SELECT route.origin_node_id, route.safe_node_id, route.safe_eta, route.kelompok, zone.nama_zona
FROM tb_safe_routes_v2 AS route
LEFT JOIN tb_safe_zones AS zone ON zone.safe_zone_id = route.safe_zone_id
WHERE route.origin_node_id = :originNodeId
LIMIT 1
```
*   `EvacuationDao.findSafePathSteps` (tambah parameter `kelompok`):
```sql
WITH RECURSIVE path AS (
    SELECT node_id, next_node_id, 1 AS step
    FROM tb_safe_next_v2
    WHERE kelompok = :kelompok AND node_id = :originNodeId
    UNION ALL
    SELECT nxt.node_id, nxt.next_node_id, path.step + 1
    FROM tb_safe_next_v2 AS nxt
    INNER JOIN path ON nxt.kelompok = :kelompok AND nxt.node_id = path.next_node_id
    WHERE path.step < :maxSteps
)
SELECT node_id AS nodeId, next_node_id AS nextNodeId FROM path ORDER BY step ASC
```
*   `safePathNodeIds(originNodeId, row)` memanggilnya dengan `row.kelompok`; pemeriksaan `pathNodeIds.last() == row.safeNodeId` tetap berlaku.
*   `kelompok` milik **simpul asal**: saat pengguna berpindah, baca ulang baris v2 simpul baru. `tb_safe_routes_v2` hanya berisi simpul merah; untuk tetangga yang sudah zona aman (tanpa baris v2) di `findSafeZoneDetour`, anggap tetangga itu tujuan.
*   `ZoneDao.findSafeRouteEta` dan `findSafeZoneTargetGeometries` tetap memakai `tb_safe_routes`.

---

## 5. Aturan yang sudah ada di data (jangan dihitung ulang di aplikasi)

| Aturan | Di DB | Akibat untuk aplikasi |
|---|---|---|
| **Arah (K-B1)** | TES rank 1–3, TEA, dan zona aman (`tb_safe_routes`, juga v2) hanya tujuan yang menjauh dari pantai > 15° (rasio > 0,27; ambang skrip audit 0,26 + margin). Tujuan ≤ 100 m tidak dinilai | Jangan menambah logika "TES terdekat" sendiri. Cek tetangga untuk jalan terhalang juga memakai rute prakomputasi tetangga ([konsep_pengalihan_rute_lokal.md](konsep_pengalihan_rute_lokal.md)) |
| **Jembatan (K-B2)** | Rute dicari dulu tanpa jembatan ≥ 20 m. Rute lewat jembatan hanya bila tujuan itu tak terjangkau tanpa jembatan | Keterangan "lewat jembatan" (M-8): `SELECT edge_id FROM tb_bridge_edges WHERE edge_id IN (:edgeIdsRute)` |
| **Keluar zona dulu (K-B6)** | `tb_route_shares` (opsi A) mendahulukan TEA/zona aman yang ≤ 20 menit | `PrimaryRouteSelector` saat ini memilih yang tercepat. Sesuaikan: bila ada TEA/zona aman ≤ 20 menit (`eta` tabel ≤ 14,9), pilih itu sebelum TES |
| **Status zona (K-B4)** | `tb_inundation_zones.tingkat_bahaya` selalu `Tinggi` | Peta hanya merah dan hijau |
| **Kelayakan TES** | Mengikuti penilaian BPBD 2019: yang "tidak potensial" dikeluarkan. Jumlah lantai bukan syarat tersendiri | Kolom `lantai` hanya informasi |

---

## 6. Data fasilitas

*   **244 TES** dan **25 TEA**. Nama semua fasilitas unik, jadi `findTesByName` dengan nama dari `rank_X_tes` selalu menemukan tepat satu TES.
*   **`sumber`**:
    *   `BPBD` (45 TES): bangunan daftar resmi BPBD 2019 (3 shelter + 59 bangunan potensial). Termasuk **14 TES baru TES_235–TES_248** (Hotel Ibis, Basko, Inna Muara, Bumi Minang, Universitas Bung Hatta, dll.) yang koordinatnya diambil dari OpenStreetMap karena data BPBD hanya berupa alamat; lokasinya sedang dikonfirmasi ke BPBD.
    *   `WARGA` (199 TES, 25 TEA): digitasi Kelurahan Tangguh/latihan 2025. Untuk lapis "Kesepakatan warga" (K-B5).
*   **ID**: `TES_001…`, `TEA_001…`. Dibanding 2026.10.10, yang tidak aktif lagi: TES_061, TES_126, TES_164 (titik ganda, digabung) dan TES_208 (Universitas Taman Siswa, "tidak potensial"). ID baru: TES_235–TES_248. ID lain tidak berubah. Rencana keluarga yang menyimpan ID lama (`TES_1`, `TEA_A1`, dst.) perlu dipetakan ulang atau diminta disusun ulang.
*   **Nama yang dibedakan** agar unik: misalnya "Bukit Lampu (Bungus Barat)", "Bukit Simpang Rawang (Bungus Selatan) 1", "FK Unand (area evakuasi)" untuk TEA yang bernama sama dengan TES.
*   **Kapasitas**: `tb_tes.kapasitas` kosong untuk 77 TES. `tb_tea.kapasitas = 0` berarti tidak ada data, bukan nol orang; TEA tidak dibatasi kapasitas.
*   `FacilityCategory` membaca jenis dari nama; nama baru tetap mengikuti pola lama (Hotel, Masjid, Universitas, Bukit, dll.).

---

## 7. Tabel pendukung (opsional, `@SkipQueryVerification`)

| Tabel | Isi | Kegunaan |
|---|---|---|
| `tb_bridge_edges` | `edge_id` jembatan ≥ 20 m | Keterangan "lewat jembatan" (M-8) |
| `tb_safe_routes_v2`, `tb_safe_next_v2` | Rute zona aman v2 (di luar kontrak) | Cakupan rute zona aman lebih luas (§4.7) |
| `tb_route_shares` | Porsi tujuan per simpul (opsi A) | Pemilihan tujuan berbasis daya tampung (RENCANA_KERJA §2.4) |
| `tb_fasilitas_info` | Semua TES/TEA termasuk yang dikeluarkan, alasan, sumber kapasitas, `koordinat_sumber`, nama asli BPBD | Halaman direktori / data wilayah |
| `tb_node_info` | Kelurahan, jarak pantai, jiwa, flag rute lewat jembatan | Analisis |
| `tb_kelurahan_info` | Profil tsunami per kelurahan dari KRB | Data wilayah (masa tenang) |
| `tb_jalur_resmi` | Ruas jalur evakuasi resmi BPBD | Sorot jalur di peta |
| `tb_metadata` | Versi, sumber data, parameter | Halaman Tentang. Catatan: teks `catatan_rute_aman` di versi ini masih menyebut v2 sebagai jalur navigasi; yang berlaku adalah §4.3 dan §4.7 dokumen ini |

---

## 8. Daftar uji di HP (mode pesawat)

1. Pasang aplikasi 0.2.0 dengan aset baru: DB tersalin, tidak ada error Room.
2. Titik di zona merah dekat pantai (misalnya Purus, Ulak Karang): tujuan utama tidak ke arah laut; ETA tampil pada laju 0,89 m/s (± 34% lebih lama dari angka tabel).
3. Titik dengan rank 2/3 kosong (misalnya di Koto Tangah): tidak crash; "Ada kendala?" berpindah ke TEA/zona aman.
4. Rute zona aman: garis berakhir di zona hijau, dan "tiba" terdeteksi saat keluar zona. Titik yang tidak punya rute zona aman tetap diarahkan ke TES/TEA tanpa error.
5. Rute yang melewati jembatan menampilkan keterangan "lewat jembatan".
6. Direktori TES menampilkan TES baru (misalnya Hotel Ibis) dan TES tanpa daya tampung tanpa error.
7. Widget dan rencana keluarga tetap berfungsi dengan ID dan nama baru.
8. Pembaruan lewat jaringan (setelah Sheva mengaktifkan): checksum cocok, DB baru aktif setelah aplikasi dibuka ulang.

---

## 9. Yang masih menunggu BPBD

Daftar lengkap: [pertanyaan_bpbd.md](pertanyaan_bpbd.md). Yang bisa mengubah isi DB berikutnya: batas sejajar 15° dan pengecualian 100 m, bukit di tepi pantai, batas jembatan, koordinat 17 bangunan daftar shelter, verifikasi 14 titik baru, daftar TEA resmi, dan 21 TEA yang berada di zona landaan. Perubahan apa pun akan diterbitkan sebagai versi DB baru dengan handoff yang diperbarui.

Dokumen pendukung: [erd_siaga_padang.md](erd_siaga_padang.md) dan [siaga_padang_erd.dbml](siaga_padang_erd.dbml) (struktur tabel), [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md) (aturan dan teks), [build_db_v4.md](build_db_v4.md) (cara DB dibangun).
