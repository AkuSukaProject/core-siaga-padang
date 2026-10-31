# Handoff Android: Database Siaga Padang 2026.10.18

**Untuk:** Mikail (Android) · **Dari:** Habib (engine DB, repo `core-siaga-padang`) · **Tanggal:** 26 Oktober 2026
**Acuan:** kontrak DB di `siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §1 (asumsi kerja) dan §2.1 (isi DB); tugas terkait M-3, M-8, M-9. Sisi server: [handoff_backend.md](handoff_backend.md) (Sheva).

Kode yang dirujuk berasal dari branch `feat/final-keselamatan-navigasi` (commit `fcf0926`, 10 Oktober). Ke-28 kueri `@Query` di branch itu (per 26 Oktober, commit `ed9bb49`) sudah diuji berjalan pada DB ini.

> **Versi ini mengikuti keputusan K-B6 tanggal 12 Oktober** (batas "sempat" 15 menit, zona hijau dulu) dan permintaan Mikail atas paket 2026.10.15. Perubahan §4.1–§4.6 berasal dari kontrak. §4.7 (rute zona aman v2) dan §4.8 (pemilih tujuan) adalah kesepakatan baru yang akan dicatat Mikail di `PEMBAGIAN_TUGAS_BPBD.md`.

---

## 0. Aturan pilihan tujuan (K-B6, 12 Oktober) dan isi DB

| Aturan | Di aplikasi | Di DB 2026.10.18 |
|---|---|---|
| Batas "sempat" | 15 menit pada laju aplikasi: 20 menit dikurangi cadangan 5 menit untuk waktu gempa yang meleset, orang yang lebih lambat, dan jalan tertutup | `tb_metadata.batas_sempat_menit = 15`. Setara `eta`/`safe_eta` tabel ≤ **11,175** menit (15 × 0,894 ÷ 1,2) |
| Keluar zona dulu | Bila TEA atau zona hijau sempat, itu yang dipilih | Simulasi kanonis memakai urutan yang sama. Porsi TES `tb_route_shares` (sejak 2026.10.18) mengikuti aturan ini ([kontrak_porsi_tujuan.md](kontrak_porsi_tujuan.md)) |
| Bila keluar zona tidak sempat | TES terjauh dari pantai | Urutan `rank_1..3` TES tetap: terjauh dari pantai di antara yang ≤ 20 menit, lalu tercepat (tidak diubah, sesuai permintaan) |
| Rute zona hijau (`tb_safe_routes_v2`) | Dipakai untuk navigasi; `tb_safe_routes` untuk status tiba dan cadangan | **Titik terdalam dihitung dengan batas 15 menit** (sebelumnya 20). Bila tidak ada yang sempat, batas zona hijau yang tercepat dicapai |
| Semua tujuan | Lolos syarat arah (menjauhi pantai), jembatan ≥ 20 m hanya cadangan | Sama seperti sebelumnya |

**Masalah di 2026.10.15 yang diperbaiki:**

| | 2026.10.15 | 2026.10.18 |
|---|---|---|
| Rute v2 yang sempat ≤ 15 menit | 446 dari 11.418 | **3.781** dari 11.418 |
| Simpang yang batas zona hijaunya sempat ≤ 15 menit tetapi rute v2-nya lewat 15 menit | 3.101 | **0** |
| Rute v2 ≤ 20 menit | 4.944 | 4.944 dari 11.418 (tidak ada yang hilang) |

Pengecekan sementara di aplikasi ("pakai `tb_safe_routes` bila v2 lewat 15 menit") tidak lagi diperlukan, tetapi aman bila dibiarkan. Di DB ini, setiap simpang yang batas zona hijaunya sempat ≤ 15 menit juga punya rute v2 ≤ 15 menit.

Catatan untuk cadangan v2: di versi uji, cadangan "batas zona hijau termurah" (biaya rute, yang memuat penalti pantai) membuat 107 simpang (3.102 jiwa) kehilangan rute ≤ 20 menit. Karena itu cadangannya kini **batas zona hijau yang tercepat dicapai**. Itu tetap batas zona hijau dan tetap lolos syarat arah.

Simulasi kanonis dengan aturan ini (20.000 agen, laju 0,894 m/s, 313.943 jiwa): **68,2%** selamat, 0 TES kelebihan kapasitas. Baseline: 36,7% dengan 104 TES kelebihan kapasitas (dihitung pada 2026.10.16, yang dasar datanya sama dengan 2026.10.18).

---

## 1. Ringkasan

| | |
|---|---|
| Versi dataset | **2026.10.18** (menggantikan 2026.10.17, 2026.10.16, dan 2026.10.15; versi 2026.10.10–2026.10.14 juga tidak dipakai) |
| Berkas | `ranah_siaga_v4.db`, 36.970.496 byte, SHA-256 `173b8010ace05ad15735a5a6e49cd1589419113325267de17f4ae8bb56b93175` |
| Ukuran (NF-03) | 36,97 MB desimal (batas 75 MB) |
| Versi aplikasi yang memakai DB ini | **0.2.0, versionCode 3** (backend memakainya sebagai `minimum_app_version`) |
| Skema Room | `android-v1` tetap, tetapi `NodeEntity` wajib menambah satu kolom (§4.1) |

Yang berubah dari 2026.10.17:
1. **Porsi TES `tb_route_shares` diganti seluruhnya**: porsi TES per simpang dari program linear berkapasitas (167 TES berkapasitas; 77 TES tanpa kapasitas hanya cadangan), 32.201 baris. **Tabel baru `tb_tes_next`** (rantai simpul ke tiap TES, 40.677 baris), kolom baru `tb_tes.nearest_node_id` dan `snap_dist_m`, serta `tb_tea.snap_dist_m`. Kontrak dan aturan pemakaian: [kontrak_porsi_tujuan.md](kontrak_porsi_tujuan.md). Kode aplikasi saat ini belum membaca `tb_route_shares`, dan `tb_tes`/`tb_tea` bukan `@Entity`, jadi tidak ada kueri yang rusak.
2. **Jaringan jalan kembali ke graf OSM 8 Agustus 2026, sama dengan 2026.10.16** (graf 20 Oktober dari 2026.10.17 tidak dipakai): 31.813 simpul, 39.216 ruas, 11.418 simpul merah, `tb_routes` 10.688 baris, 176 ruas jembatan ≥ 20 m. Semua tabel lain identik dengan 2026.10.16. `edge_id` kembali ke penomoran 2026.10.16, jadi data uji yang menyimpan `edge_id` atau `node_id` dari 2026.10.17 perlu dibaca ulang dari DB ini.

Yang berubah dari 2026.10.16: hanya butir 1 di atas, ditambah `tb_metadata` (kunci baru `skenario_porsi`, `metode_porsi`, `sumber_kapasitas_tes`; `aturan_tujuan` diperbarui).

Yang berubah dari 2026.10.15:
1. **`tb_safe_routes_v2`**: titik terdalam dengan batas 15 menit; cadangan = batas zona hijau tercepat (§0). 864 kelompok, `tb_safe_next_v2` 28.894 baris.
2. **Porsi TES `tb_route_shares` (sejak 2026.10.18)**: porsi TES per simpang dari program linear berkapasitas (167 TES berkapasitas), jalurnya di `tb_tes_next`. Kontrak lengkap, aturan pemakaian, dan pemeriksaan: [kontrak_porsi_tujuan.md](kontrak_porsi_tujuan.md).
3. **`tb_metadata`**: kunci baru `batas_sempat_menit`; `aturan_tujuan` dan `catatan_rute_aman` diperbarui.
4. **`tb_fasilitas_info.alasan_tidak_dipakai`** untuk TEA kini membedakan "landaan tsunami (raster KRB)" dan "zona merah (peta evakuasi BPBD)".
5. Zona, fasilitas, TES rank 1–3, TEA, dan skema sama dengan 2026.10.15.

Yang berubah dari 2026.10.12:
1. **Aturan tujuan** (§0): urutan `rank_1..3` TES dan TEA utama/alternatif terjauh dari pantai, rute zona aman v2, dan penugasan `tb_route_shares`.
2. **`tb_safe_routes_v2`** mencakup **semua 11.418** simpul merah (sebelumnya 8.795 dari 8.812).
3. **Zona merah kini gabungan raster KRB dan zona rawan tsunami peta evakuasi BPBD (Blue Line)**, lebih presisi, dan dipotong ke daratan (§3a). Zona merah naik dari 6.164 ha menjadi 7.272 ha, dari 8.808 menjadi **11.418 simpul**, dan dari 56 menjadi 68 kelurahan. Contohnya Masjid Raya Syekh Ahmad Khatib kini di zona merah, sesuai peta evakuasi.
4. **Penduduk**: `tb_node_info.demand_jiwa` = 242.750 jiwa terpapar KRB + perkiraan 71.193 jiwa di zona merah tambahan = 313.943 jiwa.
5. **TEA 22** (sebelumnya 25): TEA_033 RTH Imam Bonjol, TEA_038 Kuburan Silungkang, dan TEA_044 area Masjid Raya Syekh Ahmad Khatib kini di zona merah, jadi tidak dipakai sebagai TEA. TES_205 Masjid Raya tetap TES (evakuasi vertikal).
6. **`tb_metadata`**: kunci baru `aturan_tujuan` dan `catatan_penduduk`; `sumber_zona_merah` menyebut kedua sumber.
7. Tidak ada perubahan skema tabel kontrak. `tb_kelurahan_info` mendapat kolom `jiwa_tambahan_peta_evakuasi`. TES, ID, nama, dan kapasitas sama dengan 2026.10.12.

Yang berubah dari DB 2026.09.28 yang sekarang terbundel di aplikasi:
1. **Data baru BPBD**: zona merah dari KRB 2023–2027 digabung peta evakuasi BPBD, 244 TES (45 bersumber BPBD, 199 WARGA), 22 TEA, penduduk di zona merah 313.943 jiwa.
2. **Aturan BPBD tertanam di rute**: tujuan harus menjauhi pantai (tidak boleh sejajar), jembatan ≥ 20 m dihindari, tujuan terjauh dari pantai bila sempat.
3. **Satuan ETA tetap 1,2 m/s** (kontrak); aplikasi mengonversi ke 0,89 m/s (M-3).
4. **Kolom dan tabel baru** sesuai kontrak: `jarak_pantai_m`, `sumber`, `lantai`, `tb_bridge_edges`. Ditambah `tb_safe_routes_v2` / `tb_safe_next_v2` untuk navigasi zona aman (§4.7).
5. **Nilai yang boleh kosong**: `tb_tes.kapasitas`, `rank_2_*`, `rank_3_*`.

---

## 2. Berkas dan cara memasang

Ambil dari `hasil_build/` repo engine, lampiran GitHub Release `db-2026.10.18`, atau paket `kirim_siaga_padang_2026.10.18.zip`:

| Berkas | Taruh sebagai |
|---|---|
| `ranah_siaga_v4.db` | `android/app/src/main/assets/ranah_siaga.db` |
| `dataset_manifest_android.json` | `android/app/src/main/assets/dataset_manifest.json` |

Isi manifest:
```json
{
  "version": "2026.10.18",
  "checksum": "173b8010ace05ad15735a5a6e49cd1589419113325267de17f4ae8bb56b93175",
  "size_bytes": 36970496
}
```

Cara paling aman: dari repo engine jalankan `env\Scripts\python.exe salin_db_ke_android.py <repo-aplikasi> --tulis`. Skrip memeriksa checksum, lalu menyalin kedua berkas dengan nama yang benar. `dataset_manifest.json` (tanpa `_android`) dan `.zip` di `hasil_build/` **bukan** untuk aplikasi.

Aset yang terbundel sekarang (`ranah_siaga.db` 13 September, 130 MB) adalah DB lama: belum punya `tb_safe_routes` dan indeks `idx_tb_nodes_lat_lon`, dan manifestnya menyebut versi lain (2026.09.28, 71 MB). Ganti **kedua** berkas sekaligus. `DatasetStorage.refreshBundledCopyIfAssetChanged` lalu menyalin ulang DB karena checksum berubah. Perbarui juga `EvacuationRepository.DEFAULT_DATASET_VERSION` dari `"2026.09.28"` menjadi `"2026.10.18"`.

---

## 3. Isi DB terhadap kontrak §2.1

| Butir kontrak | DB 2026.10.18 |
|---|---|
| `rank_k_tes` berisi nama TES yang unik | Ya. 269 nama fasilitas (TES + TEA) tanpa duplikat |
| `rank_k_path` deretan `node_id` dipisah koma | Ya |
| `rank_k_eta` dan `safe_eta` pada **1,2 m/s** | Ya. 20 menit pada laju FEMA = `eta` ≤ 14,9 menit di tabel |
| `tb_edges` ruas lurus tanpa geometri, urutan lon lat | Ya (18.961 ruas tanpa geometri) |
| `tb_safe_routes.safe_eta = 0` menandai tujuan zona hijau | Ya, tidak pernah 0 di zona merah |
| Pola `tb_tea_*`, `tb_safe_*` | Sama. `tb_safe_routes` / `tb_safe_next` patuh syarat arah. Ditambah `tb_safe_routes_v2` / `tb_safe_next_v2` (§4.7) |
| Poligon WKT `MULTIPOLYGON` 2D, 7 desimal | Ya, semua poligon |
| Ukuran ≤ 75 MB | 36,97 MB |
| `tb_tes`: `sumber`, `jarak_pantai_m`, `kapasitas` kosong bila tidak ada data, `lantai` | Ya |
| `tb_tea.jarak_pantai_m` | Ya (ditambah `sumber`) |
| `tb_nodes.jarak_pantai_m`, `is_safe` dari zona rendaman baru | Ya |
| `tb_inundation_zones` dari zona BPBD | Ya, raster KRB 2023–2027 digabung zona rawan peta evakuasi BPBD, satu baris per kelurahan (68), dipotong ke daratan (§3a) |
| `tb_safe_zones` zona hijau baru | Ya (81) |
| `tb_kelurahan` | Tidak dibuat: poligon zona tetap per kelurahan, jadi tidak diperlukan |
| `tb_bridge_edges(edge_id)` jembatan ≥ 20 m | Ya, 176 ruas (pembanding tim: 177) |
| Rute dihitung ulang dengan aturan arah dan jembatan | Ya. Skrip `docs/audit/analisis_masukan_bpbd.py` pada DB ini: tujuan utama **0% mendekat, 0% sejajar** (DB 2026.09.28: 35,2% dan 18,5%). Verifikasi engine: TES rank 1–3, TEA, dan zona aman v2 juga 0% |
| `rank_2`/`rank_3` boleh kosong | Ya (356 dan 1.174 simpul) |
| `v_fasilitas_evakuasi` + `sumber` | Ya |
| Manifest `version`, `checksum`, `size_bytes` | `dataset_manifest_android.json` |

### 3a. Zona merah dan zona hijau (sejak 2026.10.14, sumber diperluas di 2026.10.15)

**Sumber zona merah (2026.10.15): landaan raster KRB 2023–2027 digabung zona rawan tsunami peta evakuasi BPBD.**
*   Raster KRB adalah model landaan dan lebih sempit dari peta evakuasi BPBD ("Peta Tempat Evakuasi Sementara dan Lokasi Potensial Shelter", 1:15.000), yang dipakai rambu Blue Line. Contohnya Masjid Raya Syekh Ahmad Khatib: di raster KRB masjid ini berada sekitar 250 m di luar landaan, sedangkan di peta evakuasi masjid berada di dalam zona merah dan zona baru berakhir di Blue Line Ampang.
*   Peta evakuasi hanya tersedia sebagai gambar, jadi kami georeferensi dan digitasi sendiri (`data_bpbd_digitasi/` di repo engine). Ketelitiannya ±20–40 m. Hasil digitasi ini akan diganti berkas vektor bila BPBD memberikannya.
*   Peta evakuasi mencakup Padang bagian tengah dan utara (Tabing sampai Bukit Gado-Gado). Di luar itu zona merah hanya dari KRB.
*   Hasilnya, zona merah 7.272 ha (sebelumnya 6.164 ha), 11.418 simpul, dan 68 kelurahan. 12 kelurahan baru berzona merah: Ampang, Andalas, Anduring, Banuaran Nan XX, Gurun Laweh Nan XX, Koto Baru Nan XX, Mato Aie, Parak Gadang Timur, Parak Laweh Pulau Air Nan XX, Sawahan, Sawahan Timur, dan Tanjuang Aur Nan XX.

Bentuk poligonnya juga lebih presisi. Tidak ada perubahan kode:
*   **Tepi zona** mengikuti raster BPBD 30 m dengan kontur sub-piksel, bukan tangga kotak 30 m yang disederhanakan 10 m.
*   **Dipotong ke daratan** menurut garis pantai OSM, garis yang sama dengan `jarak_pantai_m`. Sebelumnya 329 ha zona merah dan 55 ha zona hijau berada di laut, karena batas kelurahan BPBD menjorok ke laut.
*   **Pita pantai tidak lagi hilang.** Dulu zona merah dipotong batas kelurahan BPBD, sehingga 59 ha pantai di darat yang ada di luar batas itu tidak berwarna apa pun. Sekarang pita itu merah dan masuk ke poligon kelurahan terdekat.
*   **Tanpa celah dan tumpang tindih**: zona hijau = bagian darat kelurahan di luar zona merah. Serpihan hijau < 1 ha yang terjepit di zona merah ikut merah.
*   **`tb_nodes.is_safe` sama persis dengan poligon**: 0 simpul yang di poligon merah tetapi `is_safe = 1`, atau sebaliknya. Pemeriksaan "di zona mana saya" lewat poligon dan lewat simpul terdekat kini selalu sepakat (kecuali posisi pengguna yang jauh dari simpul).
*   Kelurahan yang seluruh daratannya kini zona merah tidak punya baris `tb_safe_zones`, jadi `tb_safe_zones` berisi 81 baris (sebelumnya 98).

Di luar cakupan peta evakuasi, tepi zona di sisi darat tetap berundak mengikuti sel raster BPBD 30 m; itu batas ketelitian data BPBD.

---

## 4. Perubahan kode

Wajib dari kontrak: §4.1–§4.6. Kesepakatan K-B6 (§0): §4.7–§4.8.

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

### 4.3 Rute zona aman kontrak lama: tidak berubah
`tb_safe_routes` / `tb_safe_next` tetap berpola sama seperti 2026.10.12: 10.444 simpul merah punya rute ke batas zona hijau terdekat yang lolos syarat arah, 974 simpul merah tanpa baris (aplikasi memakai TES/TEA), dan semua simpul aman punya `safe_eta = 0`. Kueri `ZoneDao.findSafeRouteEta` dan `findSafeZoneTargetGeometries` tetap memakai tabel ini. Tabel ini juga cadangan navigasi; navigasi utama lewat v2 (§4.7).

### 4.4 Satuan waktu tempuh (M-3)
| Sumber waktu di aplikasi | Perlakuan |
|---|---|
| `rank_k_eta`, `safe_eta` dari DB (menit pada 1,2 m/s) | Kalikan 1,2 ÷ 0,89 (`EvacuationRepository.loadRoute` ± baris 256, `buildSafeZoneRoute`) |
| Panjang jalur dibagi laju (TEA, jalan memutar, `RequiredPaceAdvisor`, ± baris 322, 360, 410, 420) | Ganti `WALKING_SPEED_METERS_PER_SECOND` ke 0,89 m/s; **jangan** dikalikan lagi |
| `estimatedDistanceMeters = estimatedSeconds × laju` (± baris 85) | Gunakan laju yang sama dengan yang membentuk `estimatedSeconds`, atau hitung jarak langsung dari panjang ruas |

Bila M-3 belum dikerjakan, jangan memasang DB ini dulu: ETA di DB pada 1,2 m/s akan tampil apa adanya (terlalu cepat untuk orang terlemah).

### 4.5 `DatasetPackageInstaller.kt` (pembaruan lewat jaringan)
`REQUIRED_COLUMNS` saat ini cocok dengan DB ini. Saran (bukan kontrak): untuk 0.2.0, tambahkan pemeriksaan kolom yang kini dibaca aplikasi, supaya paket lama ditolak sebelum diaktifkan:
*   `tb_nodes`: tambah `jarak_pantai_m`
*   `tb_bridge_edges`: `edge_id` (bila M-8 membacanya)
*   `tb_safe_routes_v2` (`origin_node_id`, `kelompok`, `safe_node_id`, `safe_eta`, `safe_d_pantai_m`), `tb_safe_next_v2` (`kelompok`, `node_id`, `next_node_id`)

### 4.6 Versi aplikasi
`android/app/build.gradle.kts`: `versionName = "0.2.0"`, `versionCode = 3` (kesepakatan dengan Sheva untuk `minimum_app_version`).

### 4.7 Navigasi zona aman lewat v2
`tb_safe_routes_v2` berisi satu baris per simpul **zona merah** (11.418, semuanya). Tujuannya titik zona hijau terdalam yang sempat ≤ 15 menit (`safe_eta` ≤ 11,175) dan lolos syarat arah (3.781 simpul); bila tidak ada yang sempat, batas zona hijau yang tercepat dicapai dan lolos syarat arah (7.637 simpul).

```sql
CREATE TABLE tb_safe_routes_v2 (
    origin_node_id INTEGER PRIMARY KEY, kelompok INTEGER NOT NULL, safe_node_id INTEGER NOT NULL,
    safe_zone_nama TEXT, safe_eta REAL, safe_d_pantai_m REAL, mendekat_pantai_maks_m REAL, safe_zone_id INTEGER)
CREATE TABLE tb_safe_next_v2 (kelompok INTEGER NOT NULL, node_id INTEGER NOT NULL, next_node_id INTEGER NOT NULL,
    PRIMARY KEY (kelompok, node_id)) WITHOUT ROWID
```

Perubahannya:
*   `SafeRouteRow`: tambah `@ColumnInfo(name = "kelompok") val kelompok: Long?` dan `@ColumnInfo(name = "safe_d_pantai_m") val safeDPantaiM: Double?`.
*   `EvacuationDao.findSafeRoute`:
```sql
SELECT route.origin_node_id, route.safe_node_id, route.safe_eta, route.kelompok, route.safe_d_pantai_m, zone.nama_zona
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
*   `safePathNodeIds(originNodeId, row)` memanggilnya dengan `row.kelompok`. Pemeriksaan `pathNodeIds.last() == row.safeNodeId` tetap berlaku. Rantainya pendek, jauh di bawah `MAX_SAFE_PATH_STEPS = 5_000`.
*   `kelompok` milik **simpul asal**. Saat pengguna berpindah, baca ulang baris v2 simpul baru. `tb_safe_routes_v2` hanya berisi simpul merah; untuk tetangga yang sudah di zona aman (tanpa baris v2) di `findSafeZoneDetour`, anggap tetangga itu tujuan.
*   **Status tiba tidak berubah**: tetap dari `tb_safe_routes.safe_eta = 0` / `is_safe = 1`. Rute v2 sengaja berlanjut ke dalam zona hijau; begitu warga masuk zona hijau, aplikasi boleh menyatakan "sudah di zona aman" sambil tetap menampilkan sisa rute sebagai saran "terus menjauh dari pantai".
*   `ZoneDao.findSafeRouteEta` dan `findSafeZoneTargetGeometries` tetap memakai `tb_safe_routes`.

### 4.8 `PrimaryRouteSelector` (K-B6, 12 Oktober)
Mikail sudah menerapkan aturan §0 di aplikasi. Yang disediakan DB untuk itu:
*   **Batas sempat**: `estimatedSeconds` ≤ 15 menit setelah konversi M-3, atau `eta`/`safe_eta` tabel ≤ 11,175. Nilainya ada di `tb_metadata.batas_sempat_menit`.
*   **Jarak pantai tujuan** untuk memilih "terjauh dari pantai": TES `tb_tes.jarak_pantai_m` (cari dengan `nama_tes = rank_X_tes`), TEA `tb_tea.jarak_pantai_m`, zona aman `tb_safe_routes_v2.safe_d_pantai_m`.
*   **Urutan `rank_1..3`** sudah terjauh dari pantai di antara yang ≤ 20 menit. Bila aplikasi menyaring TES dengan batas 15 menit, rank 1 bisa saja lewat batas sementara rank 2 atau 3 masih sempat. Ambil TES pertama yang sempat menurut urutan rank.
*   Rute tanpa jembatan ≥ 20 m sudah didahulukan di dalam tiap jenis. Di 8 simpul, TES rank 1 tidak sempat tetapi ada TES lain yang sempat lewat jembatan; DB sengaja memilih yang tanpa jembatan (K-B2).
*   Laju aplikasi 0,89 m/s dan engine 0,894 m/s berbeda 0,5%, jadi tujuan yang ETA-nya tepat di sekitar 15 menit bisa dinilai berbeda. Ini tidak berbahaya.

---

## 5. Aturan yang sudah ada di data (jangan dihitung ulang di aplikasi)

| Aturan | Di DB | Akibat untuk aplikasi |
|---|---|---|
| **Arah (K-B1)** | TES rank 1–3, TEA, dan zona aman (`tb_safe_routes` dan v2) hanya tujuan yang menjauh dari pantai > 15° (rasio > 0,27; ambang skrip audit 0,26 + margin). Tujuan ≤ 100 m tidak dinilai | Jangan menambah logika "TES terdekat" sendiri. Cek tetangga untuk jalan terhalang juga memakai rute prakomputasi tetangga ([konsep_pengalihan_rute_lokal.md](konsep_pengalihan_rute_lokal.md)) |
| **Jembatan (K-B2)** | Rute dicari dulu tanpa jembatan ≥ 20 m. Rute lewat jembatan hanya bila tujuan itu tak terjangkau tanpa jembatan | Keterangan "lewat jembatan" (M-8): `SELECT edge_id FROM tb_bridge_edges WHERE edge_id IN (:edgeIdsRute)` |
| **Pilihan tujuan (K-B6, 12 Oktober, §0)** | Urutan `tb_routes` dan `tb_tea_routes` (terjauh dari pantai), tujuan `tb_safe_routes_v2` (terdalam yang sempat ≤ 15 menit), dan `tb_route_shares` (sempat ≤ 15 menit, keluar zona dulu). Kaidahnya di `tb_metadata.aturan_tujuan` | `PrimaryRouteSelector` (§4.8) |
| **Status zona (K-B4)** | `tb_inundation_zones.tingkat_bahaya` selalu `Tinggi` | Peta hanya merah dan hijau |
| **Kelayakan TES** | Mengikuti penilaian BPBD 2019: yang "tidak potensial" dikeluarkan. Jumlah lantai bukan syarat tersendiri | Kolom `lantai` hanya informasi |

---

## 6. Data fasilitas

Tidak berubah dari 2026.10.12.

*   **244 TES** dan **22 TEA**. Nama semua fasilitas unik, jadi `findTesByName` dengan nama dari `rank_X_tes` selalu menemukan tepat satu TES.
*   **`sumber`**:
    *   `BPBD` (45 TES): bangunan daftar resmi BPBD 2019 (3 shelter + 59 bangunan potensial). Termasuk **14 TES baru TES_235–TES_248** (Hotel Ibis, Basko, Inna Muara, Bumi Minang, Universitas Bung Hatta, dll.) yang koordinatnya diambil dari OpenStreetMap karena data BPBD hanya berupa alamat; lokasinya sedang dikonfirmasi ke BPBD.
    *   `WARGA` (199 TES, 22 TEA): digitasi Kelurahan Tangguh/latihan 2025. Untuk lapis "Kesepakatan warga" (K-B5).
*   **ID**: `TES_001…`, `TEA_001…`. Dibanding 2026.10.10, yang tidak aktif lagi: TES_061, TES_126, TES_164 (titik ganda, digabung) dan TES_208 (Universitas Taman Siswa, "tidak potensial"); sejak 2026.10.15 juga TEA_033, TEA_038, dan TEA_044 (kini di zona merah). ID baru: TES_235–TES_248. ID lain tidak berubah. Rencana keluarga yang menyimpan ID lama (`TES_1`, `TEA_A1`, dst.) perlu dipetakan ulang atau diminta disusun ulang.
*   **Nama yang dibedakan** agar unik: misalnya "Bukit Lampu (Bungus Barat)", "Bukit Simpang Rawang (Bungus Selatan) 1", "FK Unand (area evakuasi)" untuk TEA yang bernama sama dengan TES.
*   **Kapasitas**: `tb_tes.kapasitas` kosong untuk 77 TES. `tb_tea.kapasitas = 0` berarti tidak ada data, bukan nol orang; TEA tidak dibatasi kapasitas.
*   `FacilityCategory` membaca jenis dari nama; nama baru tetap mengikuti pola lama (Hotel, Masjid, Universitas, Bukit, dll.).

---

## 7. Tabel pendukung (`@SkipQueryVerification`)

| Tabel | Isi | Kegunaan |
|---|---|---|
| `tb_safe_routes_v2`, `tb_safe_next_v2` | Rute zona aman ke titik terdalam yang sempat | Navigasi zona aman (§4.7) |
| `tb_bridge_edges` | `edge_id` jembatan ≥ 20 m | Keterangan "lewat jembatan" (M-8) |
| `tb_route_shares` + `tb_tes_next` | Porsi TES per simpang (LP berkapasitas, 2026.10.18) dan rantai jalurnya; lihat [kontrak_porsi_tujuan.md](kontrak_porsi_tujuan.md) | Pemilihan TES dari porsi, undian dari kode keluarga (butir 5) |
| `tb_fasilitas_info` | Semua TES/TEA termasuk yang dikeluarkan, alasan, sumber kapasitas, `koordinat_sumber`, nama asli BPBD | Halaman direktori / data wilayah |
| `tb_node_info` | Kelurahan, jarak pantai, jiwa, flag rute lewat jembatan | Analisis |
| `tb_kelurahan_info` | Profil tsunami per kelurahan dari KRB | Data wilayah (masa tenang) |
| `tb_jalur_resmi` | Ruas jalur evakuasi resmi BPBD | Sorot jalur di peta |
| `tb_metadata` | Versi, sumber data, parameter, `aturan_tujuan`, `catatan_rute_aman` | Halaman Tentang |

---

## 8. Daftar uji di HP (mode pesawat)

1. Pasang aplikasi 0.2.0 dengan aset baru: DB tersalin, tidak ada error Room.
2. Titik di zona merah dekat pantai (misalnya Purus, Ulak Karang): tujuan utama tidak ke arah laut; ETA tampil pada laju 0,89 m/s (± 34% lebih lama dari angka tabel).
3. **Pilihan tujuan (§0, §4.8):** di titik yang zona hijau atau TEA-nya sempat ≤ 15 menit, tujuan utama keluar zona; bila tidak, TES terjauh dari pantai yang sempat; bila tidak ada yang sempat (misalnya Batang Kabung), yang tercepat. Di titik yang batas zona hijaunya ≤ 15 menit, rute v2 juga ≤ 15 menit.
4. **Rute zona aman v2 (§4.7):** garis berlanjut masuk ke zona hijau sampai `safe_node_id`; "sudah di zona aman" muncul saat melewati batas zona; semua titik zona merah punya rute zona aman tanpa error.
5. **Peta zona (§3a):** Masjid Raya Syekh Ahmad Khatib dan sekitarnya (sampai Blue Line Ampang di Jl. Alai–Ampang) berwarna merah; zona merah sampai garis pantai (misalnya di Purus dan Air Tawar), tidak ada zona hijau di laut, dan status "di zona merah/aman" di layar sama dengan warna peta di posisi yang sama.
6. Titik dengan rank 2/3 kosong (misalnya di Koto Tangah): tidak crash; "Ada kendala?" berpindah ke TEA/zona aman.
7. Rute yang melewati jembatan menampilkan keterangan "lewat jembatan".
8. Direktori TES menampilkan TES baru (misalnya Hotel Ibis) dan TES tanpa daya tampung tanpa error.
9. Widget dan rencana keluarga tetap berfungsi dengan ID dan nama baru.
10. Pembaruan lewat jaringan (setelah Sheva mengaktifkan): checksum cocok, DB baru aktif setelah aplikasi dibuka ulang.

---

## 9. Yang masih menunggu

*   **Mikail:** memperbarui K-B6 (§1) dan tabel zona aman v2 (§2.1) di `PEMBAGIAN_TUGAS_BPBD.md` sesuai §0.
*   **BPBD:** daftar lengkap di [pertanyaan_bpbd.md](pertanyaan_bpbd.md). Yang bisa mengubah isi DB berikutnya: batas sejajar 15° dan pengecualian 100 m, bukit di tepi pantai, batas jembatan, koordinat 17 bangunan daftar shelter, verifikasi 14 titik baru, daftar TEA resmi, 24 TEA yang berada di zona merah, dan berkas vektor zona rawan serta Blue Line. Perubahan apa pun akan diterbitkan sebagai versi DB baru dengan handoff yang diperbarui.

Dokumen pendukung: [erd_siaga_padang.md](erd_siaga_padang.md) dan [siaga_padang_erd.dbml](siaga_padang_erd.dbml) (struktur tabel), [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md) (aturan dan teks, termasuk 5.1.2 tujuan terjauh), [build_db_v4.md](build_db_v4.md) (cara DB dibangun), [simulasi_kanonis.md](simulasi_kanonis.md) (angka 68,3% dihitung pada 2026.10.17; pada dasar data 2026.10.16 = 2026.10.18: 68,2%).
