# Handoff Android: Integrasi Database Siaga Padang V4

Halo Tim Android (Sheva)!

Database baru `ranah_siaga_v4.db` dibangun ulang dari data BPBD Kota Padang (KRB 2023–2027 dan data TES/TEA 2025) serta aturan evakuasi hasil wawancara BPBD. Dokumen ini merangkum yang perlu Anda sesuaikan di aplikasi (Kotlin/Room).

---

## 1. Berkas yang perlu Anda gunakan

Semua berkas build ada di folder **`hasil_build/`** dan juga dilampirkan di GitHub Release repo engine dengan tag `db-<versi>`. Untuk mengganti aset bawaan aplikasi, jalankan `salin_db_ke_android.py <repo-aplikasi> --tulis` dari repo engine. Skrip ini menyalin `.db` (tanpa zip) sebagai `assets/ranah_siaga.db` dan `hasil_build/dataset_manifest_android.json` sebagai `assets/dataset_manifest.json` (format aplikasi: `version`, `checksum` = SHA-256 file `.db`, `size_bytes`).

| Penerima | Berkas dari `hasil_build/` |
|---|---|
| Aplikasi (aset bawaan) | `ranah_siaga_v4.db` → `assets/ranah_siaga.db`; `dataset_manifest_android.json` → `assets/dataset_manifest.json` |
| Backend (pembaruan lewat jaringan) | `ranah_siaga_v4.db`; versi, checksum, dan ukuran diambil dari `dataset_manifest_android.json` (semuanya milik file `.db`) |

`dataset_manifest.json` milik engine (checksum zip dan `.db`), jangan dipakai sebagai aset aplikasi.

1.  **`ranah_siaga_v4.db` (±30 MB)** atau paketnya **`ranah_siaga_v4.db.zip` (±6 MB)**, keduanya dibuat oleh `build_db.py`.
2.  **`dataset_manifest.json`**: sudah menunjuk ke `ranah_siaga_v4.db.zip`, dengan `checksum_sha256` untuk zip dan `db_checksum_sha256` untuk file `.db`. Seperti sebelumnya, jangan menempelkan manifest pembuat basis data ke `assets/dataset_manifest.json`; pakai checksum yang sesuai dengan file yang benar-benar dibundel.
3.  **[`docs/erd_siaga_padang.md`](erd_siaga_padang.md)** dan **[`docs/siaga_padang_erd.dbml`](siaga_padang_erd.dbml)**: struktur tabel lengkap.
4.  **[`docs/aturan_evakuasi_bpbd.md`](aturan_evakuasi_bpbd.md)**: aturan evakuasi BPBD yang juga berlaku untuk teks dan UI aplikasi.

---

## 2. Kompatibilitas skema

Semua tabel yang sudah dipakai aplikasi (`tb_nodes`, `tb_edges`, `tb_tes`, `tb_routes`, `tb_tea`, `tb_tea_routes`, `tb_tea_next`, `tb_safe_routes`, `tb_safe_next`, `tb_inundation_zones`, `tb_safe_zones`, `tb_route_shares`, dan view `v_fasilitas_evakuasi`) punya skema yang sama dengan v3, ditambah kolom `tb_safe_routes.safe_zone_id` (dipakai `EvacuationDao.findSafeRoute` sejak dataset 2026.09.28). Entity Room tidak perlu diubah, validasi skema Room tidak akan gagal, dan ke-21 kueri `@Query` aplikasi sudah diuji berjalan di DB ini.

Tabel tambahan (`tb_safe_routes_v2`, `tb_safe_next_v2`, `tb_fasilitas_info`, `tb_node_info`, `tb_kelurahan_info`, `tb_jembatan_sungai`, `tb_jalur_resmi`, `tb_metadata`) tidak mengubah tabel lama. Dua tabel zona aman v2 **wajib** dipakai untuk navigasi zona aman (lihat 3.E dan 4); yang lainnya opsional. Jika ingin dibaca, gunakan kueri dengan `@SkipQueryVerification` dan kelas baris biasa, sama seperti tabel TEA. Jangan menambahkan *entity* baru.

---

## 3. Perubahan perilaku yang wajib ditangani

### A. `tb_routes` hanya berisi node zona merah
Baris hanya ada untuk node dengan `is_safe = 0` (8.812 node, sebelumnya 31.813). Jika kueri `tb_routes` untuk node pengguna kosong:
*   Jika `tb_nodes.is_safe = 1`: tampilkan bahwa pengguna sudah berada di zona aman.
*   Jika tidak: gunakan rute `tb_safe_routes_v2` / `tb_tea_routes`.

### B. Aturan menjauhi pantai sudah ada di data
TES di arah laut tidak pernah muncul sebagai rekomendasi untuk posisi itu. Jangan menambahkan logika "TES terdekat" sendiri di aplikasi, karena bisa melanggar aturan ini. Fitur cek tetangga untuk jalan terhalang juga harus mengikuti aturan yang sama (lihat [konsep_pengalihan_rute_lokal.md](konsep_pengalihan_rute_lokal.md)).

### C. Nilai kolom yang maknanya berubah
*   `rank_X_tes` tetap berisi **nama gedung**. Beberapa nama muncul di dua lokasi (misal "Bukit Lampu"); cocokkan ke `tb_tes` dengan nama ditambah node terakhir di `rank_X_path` bila perlu.
*   `tb_inundation_zones.tingkat_bahaya` selalu `Tinggi`. Peta evakuasi hanya memakai **merah** (zona landaan) dan **hijau** (aman); jangan menampilkan gradasi merah–kuning–hijau. Satu baris mewakili satu kelurahan.
*   `tb_safe_zones.elevasi_m` bernilai `NULL`.
*   `tb_tea.kapasitas = 0` berarti kapasitas tidak tersedia, bukan nol orang. TEA tidak dibatasi kapasitas.
*   ID fasilitas sekarang `TES_001…` dan `TEA_001…`; `tb_tea.kode_tea` berformat `TEA 001`; `tb_tea.sektor` berisi nama kecamatan.
*   ETA dihitung dengan kecepatan orang terlemah 0,894 m/s, jadi angkanya lebih besar daripada versi lama (1,2 m/s).

### D. Jumlah fasilitas
234 TES dan 25 TEA (sebelumnya 143 TES dan 12 TEA). 21 TEA dari data BPBD dikeluarkan karena berada di area landaan; daftarnya ada di `tb_fasilitas_info` (`dipakai = 0`).

### E. Rute zona aman pindah ke tabel v2
`tb_safe_routes` / `tb_safe_next` adalah satu pohon rute untuk seluruh kota, sehingga tidak bisa menyaring tujuan per warga. Akibatnya 1.175 node zona merah diarahkan ke titik zona aman yang **lebih dekat ke pantai** daripada posisinya, sehingga melanggar aturan BPBD. Dua tabel itu tetap diisi hanya supaya aplikasi versi lama tidak rusak.

Aplikasi baru membaca `tb_safe_routes_v2` + `tb_safe_next_v2`. Perubahan di `EvacuationDao.kt` cukup dua:
*   `findSafeRoute`: ganti `FROM tb_safe_routes` menjadi `FROM tb_safe_routes_v2` (kolom `safe_zone_id`, `safe_node_id`, `safe_eta` tetap ada), dan ikut ambil kolom `kelompok`.
*   `findSafePathSteps`: ganti `tb_safe_next` menjadi `tb_safe_next_v2` di kedua tempat, dan tambahkan `kelompok = :kelompok` di kedua `WHERE`/`JOIN`.

Dua kueri lain di `ZoneDao.kt` **tetap** memakai `tb_safe_routes`: `findSafeRouteEta` dan `findSafeZoneTargetGeometries`. Tabel lama berisi semua simpang (31.813), dan `safe_eta = 0` tepat pada simpang tujuan kawasan aman (zona hijau, bukan kantong aman kecil), sehingga cocok untuk menentukan "sudah tiba di kawasan aman". `tb_safe_routes_v2` hanya berisi simpang zona merah, jadi tidak bisa dipakai untuk dua kueri ini.

Rinciannya:
*   Baris hanya ada untuk node zona merah (8.812). Semua tujuannya lebih jauh dari pantai daripada titik asal.
*   Kolom `kelompok` adalah kunci pohon rute. Rangkai dengan `SELECT node_id, next_node_id FROM tb_safe_next_v2 WHERE kelompok = ?` (kelompok milik **node asal**), lalu ikuti next-hop sampai node tanpa baris; node itu sama dengan `safe_node_id`.
*   Jangan mengganti kelompok di tengah jalan. Saat pengguna bergerak, yang dipakai adalah node asal baru beserta `kelompok`-nya sendiri.

---

## 4. Navigasi

*   **TES**: baca `rank_X_path` (ID node dipisah koma, dari asal ke TES).
*   **TEA**: baca `tb_tea_routes` untuk memilih TEA, lalu `SELECT * FROM tb_tea_next WHERE tea_id = ?` sekali dan rangkai rute di memori. Jangan kueri bertahap per simpul.
*   **Zona aman**: baca `tb_safe_routes_v2` untuk node pengguna, lalu `SELECT node_id, next_node_id FROM tb_safe_next_v2 WHERE kelompok = ?` sekali dan rangkai di memori (sama seperti TEA). Kueri DAO lama ke `tb_safe_routes`/`tb_safe_next` diganti ke tabel v2 dengan `@SkipQueryVerification`.

---

## 5. Ide fitur dari tabel baru (opsional)

*   **Sorot jalur evakuasi resmi** di peta dari `tb_jalur_resmi`.
*   **Info kelurahan** saat masa tenang (jiwa terpapar, kelompok rentan, kelas risiko) dari `tb_kelurahan_info`.
*   **Label sumber kapasitas** TES (`tb_fasilitas_info.kapasitas_sumber`) di halaman direktori. Sesuai kebijakan UI, informasi ini hanya ditampilkan di masa tenang, tidak di layar navigasi darurat.
