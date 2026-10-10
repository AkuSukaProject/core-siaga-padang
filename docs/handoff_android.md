# Handoff Android: Integrasi Database Siaga Padang V4

Halo Tim Android (Sheva)!

Database baru `ranah_siaga_v4.db` dibangun ulang dari data BPBD Kota Padang (KRB 2023–2027 dan data TES/TEA 2025) serta aturan evakuasi hasil wawancara BPBD. Dokumen ini merangkum yang perlu Anda sesuaikan di aplikasi (Kotlin/Room).

---

## 1. Berkas yang perlu Anda gunakan

1.  **`ranah_siaga_v4.db` (±29 MB)**: database SQLite terbaru. Belum dipaketkan ke `.zip` dan manifest belum diperbarui; tunggu konfirmasi tim data sebelum mengganti aset di aplikasi.
2.  **`dataset_manifest.json`**: seperti sebelumnya, jangan menempelkan manifest pembuat basis data ke `assets/dataset_manifest.json`. Pakai checksum file `.db`.
3.  **[`docs/erd_siaga_padang.md`](erd_siaga_padang.md)** dan **[`docs/siaga_padang_erd.dbml`](siaga_padang_erd.dbml)**: struktur tabel lengkap.
4.  **[`docs/aturan_evakuasi_bpbd.md`](aturan_evakuasi_bpbd.md)**: aturan evakuasi BPBD yang juga berlaku untuk teks dan UI aplikasi.

---

## 2. Kompatibilitas skema

Semua tabel yang sudah dipakai aplikasi (`tb_nodes`, `tb_edges`, `tb_tes`, `tb_routes`, `tb_tea`, `tb_tea_routes`, `tb_tea_next`, `tb_safe_routes`, `tb_safe_next`, `tb_inundation_zones`, `tb_safe_zones`, `tb_route_shares`, dan view `v_fasilitas_evakuasi`) punya **skema identik dengan v3**. Entity Room tidak perlu diubah dan validasi skema Room tidak akan gagal.

Tabel tambahan (`tb_fasilitas_info`, `tb_node_info`, `tb_kelurahan_info`, `tb_jembatan_sungai`, `tb_jalur_resmi`, `tb_metadata`) bersifat opsional. Jika ingin dibaca, gunakan kueri dengan `@SkipQueryVerification` dan kelas baris biasa, sama seperti tabel TEA. Jangan menambahkan *entity* baru.

---

## 3. Perubahan perilaku yang wajib ditangani

### A. `tb_routes` hanya berisi node zona merah
Baris hanya ada untuk node dengan `is_safe = 0` (8.812 node, sebelumnya 31.813). Jika kueri `tb_routes` untuk node pengguna kosong:
*   Jika `tb_nodes.is_safe = 1`: tampilkan bahwa pengguna sudah berada di zona aman.
*   Jika tidak: gunakan rute `tb_safe_routes` / `tb_tea_routes`.

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

---

## 4. Navigasi (tidak berubah)

*   **TES**: baca `rank_X_path` (ID node dipisah koma, dari asal ke TES).
*   **TEA**: baca `tb_tea_routes` untuk memilih TEA, lalu `SELECT * FROM tb_tea_next WHERE tea_id = ?` sekali dan rangkai rute di memori. Jangan kueri bertahap per simpul.
*   **Zona aman**: baca `tb_safe_routes`, lalu rangkai dari `tb_safe_next`.

---

## 5. Ide fitur dari tabel baru (opsional)

*   **Sorot jalur evakuasi resmi** di peta dari `tb_jalur_resmi`.
*   **Info kelurahan** saat masa tenang (jiwa terpapar, kelompok rentan, kelas risiko) dari `tb_kelurahan_info`.
*   **Label sumber kapasitas** TES (`tb_fasilitas_info.kapasitas_sumber`) di halaman direktori. Sesuai kebijakan UI, informasi ini hanya ditampilkan di masa tenang, tidak di layar navigasi darurat.
