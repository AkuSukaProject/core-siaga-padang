# Handoff Android: Database Siaga Padang 2026.10.14

**Untuk:** Mikail (Android) · **Dari:** Habib (engine DB, repo `core-siaga-padang`) · **Tanggal:** 12 Oktober 2026
**Acuan:** kontrak DB di `siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §1 (asumsi kerja) dan §2.1 (isi DB); tugas terkait M-3, M-8, M-9. Sisi server: [handoff_backend.md](handoff_backend.md) (Sheva).

Kode yang dirujuk berasal dari branch `feat/final-keselamatan-navigasi` (commit `fcf0926`, 10 Oktober). Ke-21 kueri `@Query` di branch itu sudah diuji berjalan pada DB ini.

> **Versi ini membawa usulan perubahan kontrak (§0) yang perlu persetujuan Mikail.** Perubahan §4.1–§4.6 tetap berasal dari kontrak yang sudah disepakati. §4.7 dan §4.8 adalah usulan baru. Bila usulan ditolak, DB ini tetap bisa dipakai dengan kode lama untuk zona aman (lihat §0, "Bila ditolak").

---

## 0. Usulan perubahan kontrak: tujuan terjauh dari pantai

**Aturan baru (dari tim, 11 Oktober):** bila dalam 20 menit warga bisa menjangkau beberapa tujuan, arahkan ke tujuan yang **paling jauh dari pantai** di antara yang terjangkau, supaya warga menjauh sejauh mungkin dari laut.

| | Kontrak sekarang | Usulan |
|---|---|---|
| K-B6 (pilihan tujuan) | Bila sempat 20 menit, keluar zona dulu (TEA/zona hijau); bila tidak, TES tercepat yang menjauh | Di antara TES, TEA, dan zona aman yang terjangkau ≤ 20 menit (laju 0,894 m/s, `eta` tabel ≤ 14,9), pilih yang **paling jauh dari pantai**. Bila tidak ada yang sempat, tetap tujuan tercepat yang menjauh |
| Tujuan zona aman | Batas zona hijau terdekat (`tb_safe_routes`, pohon global) | Titik zona hijau **terdalam** (paling jauh dari pantai) yang masih terjangkau ≤ 20 menit. Warga terus berjalan masuk ke zona hijau |
| Tabel navigasi zona aman (§2.1) | `tb_safe_routes` / `tb_safe_next` | **`tb_safe_routes_v2` / `tb_safe_next_v2` menjadi wajib** (rute per warga butuh kunci `kelompok`). `tb_safe_routes` tetap ada untuk status tiba (`safe_eta = 0`) |

Mengapa v2 wajib: tujuan "terdalam" berbeda untuk tiap warga, jadi tidak bisa disimpan dalam satu pohon global seperti `tb_safe_next`. Polanya sama dengan `tb_tea_next` (rantai per tujuan).

Dampak (simulasi kanonis, 20.000 agen, laju 0,894 m/s):

| | 2026.10.12 (kontrak sekarang) | 2026.10.14 dengan v2 (usulan) | 2026.10.14 tanpa v2 |
|---|---|---|---|
| Selamat: tiba ≤ 20 menit & tertampung | 68,8% | **72,2%** | 68,9% |
| TES melebihi kapasitas | 0 | 0 | 0 |
| Simpul merah yang punya rute zona aman | 7.793 dari 8.812 | **8.808 dari 8.808 (semua)** | 7.760 dari 8.808 |

**Bila usulan ditolak:** DB ini tetap aman dipakai dengan kode zona aman lama (§4.3 kontrak lama: `tb_safe_routes` tidak berubah dan tetap patuh syarat arah). Urutan `rank_1..3` TES dan TEA utama sudah mengikuti aturan terjauh. Selama `PrimaryRouteSelector` belum diubah, aplikasi tetap memilih yang tercepat di antara kandidat itu. Kabari saya bila ingin urutan TES/TEA dikembalikan ke "tercepat"; saya akan menerbitkan versi DB lain.

---

## 1. Ringkasan

| | |
|---|---|
| Versi dataset | **2026.10.14** (menggantikan 2026.10.12; versi 2026.10.10, 2026.10.11, dan 2026.10.13 juga tidak dipakai) |
| Berkas | `ranah_siaga_v4.db`, 31.522.816 byte, SHA-256 `6fe87165e5b922a634825d8fd1af1bac0b42b632d8a32dd9333e23f7f336f8f0` |
| Ukuran (NF-03) | 31,52 MB desimal (batas 75 MB) |
| Versi aplikasi yang memakai DB ini | **0.2.0, versionCode 3** (backend memakainya sebagai `minimum_app_version`) |
| Skema Room | `android-v1` tetap, tetapi `NodeEntity` wajib menambah satu kolom (§4.1) |

Yang berubah dari 2026.10.12:
1. **Aturan tujuan terjauh dari pantai** (§0): urutan `rank_1..3` TES, TEA utama/alternatif, rute zona aman v2, dan penugasan `tb_route_shares`.
2. **`tb_safe_routes_v2`** kini mencakup **semua 8.808** simpul merah (sebelumnya 8.795 dari 8.812) dan menuju titik terdalam yang sempat; `kelompok` = nomor titik tujuan (945 kelompok, `tb_safe_next_v2` 32.890 baris).
3. **Zona merah dan hijau lebih presisi** (§3a). Akibatnya 22 simpul berpindah ke zona aman dan 18 ke zona merah (zona merah kini 8.808 simpul).
4. **`tb_metadata`**: kunci baru `aturan_tujuan`; teks `catatan_rute_aman` sudah benar.
5. Tidak ada perubahan skema. Tabel, kolom, fasilitas, ID, nama, dan kapasitas sama dengan 2026.10.12.

Yang berubah dari DB 2026.09.28 yang sekarang terbundel di aplikasi:
1. **Data baru BPBD**: zona merah dari KRB 2023–2027, 244 TES (45 bersumber BPBD, 199 WARGA), 25 TEA, penduduk terpapar 242.750 jiwa.
2. **Aturan BPBD tertanam di rute**: tujuan harus menjauhi pantai (tidak boleh sejajar), jembatan ≥ 20 m dihindari, tujuan terjauh dari pantai bila sempat.
3. **Satuan ETA tetap 1,2 m/s** (kontrak); aplikasi mengonversi ke 0,89 m/s (M-3).
4. **Kolom dan tabel baru** sesuai kontrak: `jarak_pantai_m`, `sumber`, `lantai`, `tb_bridge_edges`. Ditambah `tb_safe_routes_v2` / `tb_safe_next_v2` (usulan wajib, §4.7).
5. **Nilai yang boleh kosong**: `tb_tes.kapasitas`, `rank_2_*`, `rank_3_*`.

---

## 2. Berkas dan cara memasang

Ambil dari `hasil_build/` repo engine, lampiran GitHub Release `db-2026.10.14`, atau paket `kirim_siaga_padang_2026.10.14.zip`:

| Berkas | Taruh sebagai |
|---|---|
| `ranah_siaga_v4.db` | `android/app/src/main/assets/ranah_siaga.db` |
| `dataset_manifest_android.json` | `android/app/src/main/assets/dataset_manifest.json` |

Isi manifest:
```json
{
  "version": "2026.10.14",
  "checksum": "6fe87165e5b922a634825d8fd1af1bac0b42b632d8a32dd9333e23f7f336f8f0",
  "size_bytes": 31522816
}
```

Cara paling aman: dari repo engine jalankan `env\Scripts\python.exe salin_db_ke_android.py <repo-aplikasi> --tulis`. Skrip memeriksa checksum, lalu menyalin kedua berkas dengan nama yang benar. `dataset_manifest.json` (tanpa `_android`) dan `.zip` di `hasil_build/` **bukan** untuk aplikasi.

Aset yang terbundel sekarang (`ranah_siaga.db` 13 September, 130 MB) adalah DB lama: belum punya `tb_safe_routes` dan indeks `idx_tb_nodes_lat_lon`, dan manifestnya menyebut versi lain (2026.09.28, 71 MB). Ganti **kedua** berkas sekaligus. `DatasetStorage.refreshBundledCopyIfAssetChanged` lalu menyalin ulang DB karena checksum berubah. Perbarui juga `EvacuationRepository.DEFAULT_DATASET_VERSION` dari `"2026.09.28"` menjadi `"2026.10.14"`.

---

## 3. Isi DB terhadap kontrak §2.1

| Butir kontrak | DB 2026.10.14 |
|---|---|
| `rank_k_tes` berisi nama TES yang unik | Ya. 269 nama fasilitas (TES + TEA) tanpa duplikat |
| `rank_k_path` deretan `node_id` dipisah koma | Ya |
| `rank_k_eta` dan `safe_eta` pada **1,2 m/s** | Ya. 20 menit pada laju FEMA = `eta` ≤ 14,9 menit di tabel |
| `tb_edges` ruas lurus tanpa geometri, urutan lon lat | Ya (18.961 ruas tanpa geometri) |
| `tb_safe_routes.safe_eta = 0` menandai tujuan zona hijau | Ya, tidak pernah 0 di zona merah |
| Pola `tb_tea_*`, `tb_safe_*` | Sama. `tb_safe_routes` / `tb_safe_next` patuh syarat arah. Ditambah `tb_safe_routes_v2` / `tb_safe_next_v2` (usulan §0) |
| Poligon WKT `MULTIPOLYGON` 2D, 7 desimal | Ya, semua poligon |
| Ukuran ≤ 75 MB | 31,52 MB |
| `tb_tes`: `sumber`, `jarak_pantai_m`, `kapasitas` kosong bila tidak ada data, `lantai` | Ya |
| `tb_tea.jarak_pantai_m` | Ya (ditambah `sumber`) |
| `tb_nodes.jarak_pantai_m`, `is_safe` dari zona rendaman baru | Ya |
| `tb_inundation_zones` dari zona BPBD | Ya, raster KRB 2023–2027, satu baris per kelurahan (56), dipotong ke daratan (§3a) |
| `tb_safe_zones` zona hijau baru | Ya (96) |
| `tb_kelurahan` | Tidak dibuat: poligon zona tetap per kelurahan, jadi tidak diperlukan |
| `tb_bridge_edges(edge_id)` jembatan ≥ 20 m | Ya, 176 ruas (pembanding tim: 177) |
| Rute dihitung ulang dengan aturan arah dan jembatan | Ya. Skrip `docs/audit/analisis_masukan_bpbd.py` pada DB ini: tujuan utama **0% mendekat, 0% sejajar** (DB 2026.09.28: 35,2% dan 18,5%). Verifikasi engine: TES rank 1–3, TEA, dan zona aman v2 juga 0% |
| `rank_2`/`rank_3` boleh kosong | Ya (186 dan 860 simpul) |
| `v_fasilitas_evakuasi` + `sumber` | Ya |
| Manifest `version`, `checksum`, `size_bytes` | `dataset_manifest_android.json` |

### 3a. Zona merah dan zona hijau (sejak 2026.10.14)

Poligon zona kini lebih presisi. Tidak ada perubahan kode; yang berubah hanya bentuknya:
*   **Tepi zona** mengikuti raster BPBD 30 m dengan kontur sub-piksel, bukan tangga kotak 30 m yang disederhanakan 10 m.
*   **Dipotong ke daratan** menurut garis pantai OSM, garis yang sama dengan `jarak_pantai_m`. Sebelumnya 329 ha zona merah dan 55 ha zona hijau berada di laut, karena batas kelurahan BPBD menjorok ke laut.
*   **Pita pantai tidak lagi hilang.** Dulu zona merah dipotong batas kelurahan BPBD, sehingga 59 ha pantai di darat yang ada di luar batas itu tidak berwarna apa pun. Sekarang pita itu merah dan masuk ke poligon kelurahan terdekat.
*   **Tanpa celah dan tumpang tindih**: zona hijau = bagian darat kelurahan di luar zona merah. Serpihan hijau < 1 ha yang terjepit di zona merah ikut merah.
*   **`tb_nodes.is_safe` sama persis dengan poligon**: 0 simpul yang di poligon merah tetapi `is_safe = 1`, atau sebaliknya. Pemeriksaan "di zona mana saya" lewat poligon dan lewat simpul terdekat kini selalu sepakat (kecuali posisi pengguna yang jauh dari simpul).
*   Olo dan Air Tawar Barat tidak punya baris `tb_safe_zones` lagi, karena seluruh daratannya masuk landaan. Jadi `tb_safe_zones` berisi 96 baris (sebelumnya 98).

Tepi zona di sisi darat tetap berundak mengikuti sel raster BPBD 30 m; itu batas ketelitian data BPBD.

---

## 4. Perubahan kode

Wajib dari kontrak: §4.1–§4.6. Usulan §0: §4.7–§4.8.

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
`tb_safe_routes` / `tb_safe_next` tetap berpola sama seperti 2026.10.12: 7.760 simpul merah punya rute ke batas zona hijau terdekat yang lolos syarat arah, 1.048 simpul merah tanpa baris (aplikasi memakai TES/TEA), dan semua simpul aman punya `safe_eta = 0`. Kueri `ZoneDao.findSafeRouteEta` dan `findSafeZoneTargetGeometries` tetap memakai tabel ini. Untuk navigasi, usulannya pindah ke v2 (§4.7).

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
*   `tb_safe_routes_v2` (`origin_node_id`, `kelompok`, `safe_node_id`, `safe_eta`, `safe_d_pantai_m`), `tb_safe_next_v2` (`kelompok`, `node_id`, `next_node_id`): bila §4.7 disetujui

### 4.6 Versi aplikasi
`android/app/build.gradle.kts`: `versionName = "0.2.0"`, `versionCode = 3` (kesepakatan dengan Sheva untuk `minimum_app_version`).

### 4.7 Usulan: navigasi zona aman lewat v2
`tb_safe_routes_v2` berisi satu baris per simpul **zona merah** (8.808, semuanya). Tujuannya titik zona hijau terdalam yang terjangkau ≤ 20 menit dan lolos syarat arah (5.116 simpul); bila tidak ada yang sempat, batas zona hijau termurah yang lolos syarat arah (3.692 simpul).

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
*   `safePathNodeIds(originNodeId, row)` memanggilnya dengan `row.kelompok`. Pemeriksaan `pathNodeIds.last() == row.safeNodeId` tetap berlaku. Rantai terpanjang 64 langkah, jauh di bawah `MAX_SAFE_PATH_STEPS = 5_000`.
*   `kelompok` milik **simpul asal**. Saat pengguna berpindah, baca ulang baris v2 simpul baru. `tb_safe_routes_v2` hanya berisi simpul merah; untuk tetangga yang sudah di zona aman (tanpa baris v2) di `findSafeZoneDetour`, anggap tetangga itu tujuan.
*   **Status tiba tidak berubah**: tetap dari `tb_safe_routes.safe_eta = 0` / `is_safe = 1`. Rute v2 sengaja berlanjut ke dalam zona hijau; begitu warga masuk zona hijau, aplikasi boleh menyatakan "sudah di zona aman" sambil tetap menampilkan sisa rute sebagai saran "terus menjauh dari pantai".
*   `ZoneDao.findSafeRouteEta` dan `findSafeZoneTargetGeometries` tetap memakai `tb_safe_routes`.

### 4.8 Usulan: `PrimaryRouteSelector` memilih yang terjauh dari pantai
Sekarang (`domain/PrimaryRouteSelector.kt`) memilih yang **tercepat** di antara TES rank 1, TEA, dan zona aman. Usulan:

1.  `EvacuationRoute`: tambah `val destinationCoastDistanceMeters: Double? = null`, diisi dari:
    *   TES: `tb_tes.jarak_pantai_m` (cari dengan `nama_tes = rank_X_tes`);
    *   TEA: `tb_tea.jarak_pantai_m`;
    *   zona aman: `tb_safe_routes_v2.safe_d_pantai_m` (atau `tb_nodes.jarak_pantai_m` dari `safe_node_id` bila memakai tabel lama).
2.  Urutan baru:
```kotlin
object PrimaryRouteSelector {
    /** Batas "sempat": 20 menit pada laju aplikasi (setelah konversi M-3). */
    private const val SEMPAT_DETIK = 20 * 60

    private val ORDER = compareBy<EvacuationRoute>(
        { if (it.estimatedSeconds <= SEMPAT_DETIK) 0 else 1 },                    // yang sempat lebih dulu
        { if (it.estimatedSeconds <= SEMPAT_DETIK) -(it.destinationCoastDistanceMeters ?: 0.0) else 0.0 }, // terjauh dari pantai
        { it.estimatedSeconds },                                                  // tidak sempat: tercepat
        { kindPriority(it.destinationKind) },
    )
    // select() dan ordered() tetap memakai ORDER
}
```
3.  `ordered()` dipakai daftar alternatif (± baris 585), jadi urutannya ikut aturan yang sama.

Catatan:
*   Urutan `rank_1..3` di `tb_routes` dan `nearest_tea_id` / `alt_tea_id` **sudah** mengikuti aturan ini. Rank 1 adalah TES terjauh yang sempat, dan aplikasi tidak perlu mengurutkan ulang di dalam satu jenis.
*   Rute tanpa jembatan ≥ 20 m sudah didahulukan di dalam tiap jenis. Di 8 simpul, TES rank 1 tidak sempat tetapi ada TES lain yang sempat lewat jembatan; DB sengaja memilih yang tanpa jembatan (K-B2).
*   Laju aplikasi 0,89 m/s dan engine 0,894 m/s berbeda 0,5%, jadi tujuan yang ETA-nya tepat di sekitar 20 menit bisa dinilai berbeda. Ini tidak berbahaya.
*   Dalam praktik, titik zona hijau yang sempat hampir selalu lebih jauh dari pantai daripada TES, sehingga sekitar 81% warga tetap diarahkan keluar zona (sama semangatnya dengan K-B6 lama).

---

## 5. Aturan yang sudah ada di data (jangan dihitung ulang di aplikasi)

| Aturan | Di DB | Akibat untuk aplikasi |
|---|---|---|
| **Arah (K-B1)** | TES rank 1–3, TEA, dan zona aman (`tb_safe_routes` dan v2) hanya tujuan yang menjauh dari pantai > 15° (rasio > 0,27; ambang skrip audit 0,26 + margin). Tujuan ≤ 100 m tidak dinilai | Jangan menambah logika "TES terdekat" sendiri. Cek tetangga untuk jalan terhalang juga memakai rute prakomputasi tetangga ([konsep_pengalihan_rute_lokal.md](konsep_pengalihan_rute_lokal.md)) |
| **Jembatan (K-B2)** | Rute dicari dulu tanpa jembatan ≥ 20 m. Rute lewat jembatan hanya bila tujuan itu tak terjangkau tanpa jembatan | Keterangan "lewat jembatan" (M-8): `SELECT edge_id FROM tb_bridge_edges WHERE edge_id IN (:edgeIdsRute)` |
| **Tujuan terjauh dari pantai (usulan K-B6 baru, §0)** | Urutan `tb_routes`, `tb_tea_routes`, tujuan `tb_safe_routes_v2`, dan `tb_route_shares` (opsi A). Kaidahnya di `tb_metadata.aturan_tujuan` | `PrimaryRouteSelector` (§4.8) |
| **Status zona (K-B4)** | `tb_inundation_zones.tingkat_bahaya` selalu `Tinggi` | Peta hanya merah dan hijau |
| **Kelayakan TES** | Mengikuti penilaian BPBD 2019: yang "tidak potensial" dikeluarkan. Jumlah lantai bukan syarat tersendiri | Kolom `lantai` hanya informasi |

---

## 6. Data fasilitas

Tidak berubah dari 2026.10.12.

*   **244 TES** dan **25 TEA**. Nama semua fasilitas unik, jadi `findTesByName` dengan nama dari `rank_X_tes` selalu menemukan tepat satu TES.
*   **`sumber`**:
    *   `BPBD` (45 TES): bangunan daftar resmi BPBD 2019 (3 shelter + 59 bangunan potensial). Termasuk **14 TES baru TES_235–TES_248** (Hotel Ibis, Basko, Inna Muara, Bumi Minang, Universitas Bung Hatta, dll.) yang koordinatnya diambil dari OpenStreetMap karena data BPBD hanya berupa alamat; lokasinya sedang dikonfirmasi ke BPBD.
    *   `WARGA` (199 TES, 25 TEA): digitasi Kelurahan Tangguh/latihan 2025. Untuk lapis "Kesepakatan warga" (K-B5).
*   **ID**: `TES_001…`, `TEA_001…`. Dibanding 2026.10.10, yang tidak aktif lagi: TES_061, TES_126, TES_164 (titik ganda, digabung) dan TES_208 (Universitas Taman Siswa, "tidak potensial"). ID baru: TES_235–TES_248. ID lain tidak berubah. Rencana keluarga yang menyimpan ID lama (`TES_1`, `TEA_A1`, dst.) perlu dipetakan ulang atau diminta disusun ulang.
*   **Nama yang dibedakan** agar unik: misalnya "Bukit Lampu (Bungus Barat)", "Bukit Simpang Rawang (Bungus Selatan) 1", "FK Unand (area evakuasi)" untuk TEA yang bernama sama dengan TES.
*   **Kapasitas**: `tb_tes.kapasitas` kosong untuk 77 TES. `tb_tea.kapasitas = 0` berarti tidak ada data, bukan nol orang; TEA tidak dibatasi kapasitas.
*   `FacilityCategory` membaca jenis dari nama; nama baru tetap mengikuti pola lama (Hotel, Masjid, Universitas, Bukit, dll.).

---

## 7. Tabel pendukung (`@SkipQueryVerification`)

| Tabel | Isi | Kegunaan |
|---|---|---|
| `tb_safe_routes_v2`, `tb_safe_next_v2` | Rute zona aman ke titik terdalam yang sempat | Navigasi zona aman (§4.7, usulan wajib) |
| `tb_bridge_edges` | `edge_id` jembatan ≥ 20 m | Keterangan "lewat jembatan" (M-8) |
| `tb_route_shares` | Porsi tujuan per simpul (opsi A), urut aturan terjauh | Pemilihan tujuan berbasis daya tampung (RENCANA_KERJA §2.4) |
| `tb_fasilitas_info` | Semua TES/TEA termasuk yang dikeluarkan, alasan, sumber kapasitas, `koordinat_sumber`, nama asli BPBD | Halaman direktori / data wilayah |
| `tb_node_info` | Kelurahan, jarak pantai, jiwa, flag rute lewat jembatan | Analisis |
| `tb_kelurahan_info` | Profil tsunami per kelurahan dari KRB | Data wilayah (masa tenang) |
| `tb_jalur_resmi` | Ruas jalur evakuasi resmi BPBD | Sorot jalur di peta |
| `tb_metadata` | Versi, sumber data, parameter, `aturan_tujuan`, `catatan_rute_aman` | Halaman Tentang |

---

## 8. Daftar uji di HP (mode pesawat)

1. Pasang aplikasi 0.2.0 dengan aset baru: DB tersalin, tidak ada error Room.
2. Titik di zona merah dekat pantai (misalnya Purus, Ulak Karang): tujuan utama tidak ke arah laut; ETA tampil pada laju 0,89 m/s (± 34% lebih lama dari angka tabel).
3. **Aturan terjauh (§4.8):** di titik yang punya beberapa tujuan ≤ 20 menit, tujuan utama adalah yang paling jauh dari pantai, bukan yang tercepat, dan ETA-nya tetap ≤ 20 menit. Di titik yang tidak punya tujuan ≤ 20 menit (misalnya Batang Kabung), tujuan utama adalah yang tercepat.
4. **Rute zona aman v2 (§4.7):** garis berlanjut masuk ke zona hijau sampai `safe_node_id`; "sudah di zona aman" muncul saat melewati batas zona; semua titik zona merah punya rute zona aman tanpa error.
5. **Peta zona (§3a):** zona merah sampai garis pantai (misalnya di Purus dan Air Tawar), tidak ada zona hijau di laut, dan status "di zona merah/aman" di layar sama dengan warna peta di posisi yang sama.
6. Titik dengan rank 2/3 kosong (misalnya di Koto Tangah): tidak crash; "Ada kendala?" berpindah ke TEA/zona aman.
7. Rute yang melewati jembatan menampilkan keterangan "lewat jembatan".
8. Direktori TES menampilkan TES baru (misalnya Hotel Ibis) dan TES tanpa daya tampung tanpa error.
9. Widget dan rencana keluarga tetap berfungsi dengan ID dan nama baru.
10. Pembaruan lewat jaringan (setelah Sheva mengaktifkan): checksum cocok, DB baru aktif setelah aplikasi dibuka ulang.

---

## 9. Yang masih menunggu

*   **Mikail:** setuju atau tidak dengan usulan §0 (v2 wajib dan aturan terjauh). Bila setuju, butir kontrak §1 (K-B6) dan §2.1 (tabel zona aman) di `PEMBAGIAN_TUGAS_BPBD.md` perlu diperbarui di repo aplikasi.
*   **BPBD:** daftar lengkap di [pertanyaan_bpbd.md](pertanyaan_bpbd.md). Yang bisa mengubah isi DB berikutnya: batas sejajar 15° dan pengecualian 100 m, bukit di tepi pantai, batas jembatan, koordinat 17 bangunan daftar shelter, verifikasi 14 titik baru, daftar TEA resmi, dan 21 TEA yang berada di zona landaan. Perubahan apa pun akan diterbitkan sebagai versi DB baru dengan handoff yang diperbarui.

Dokumen pendukung: [erd_siaga_padang.md](erd_siaga_padang.md) dan [siaga_padang_erd.dbml](siaga_padang_erd.dbml) (struktur tabel), [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md) (aturan dan teks, termasuk 5.1.2 tujuan terjauh), [build_db_v4.md](build_db_v4.md) (cara DB dibangun), [simulasi_kanonis.md](simulasi_kanonis.md) (angka 72,2%).
