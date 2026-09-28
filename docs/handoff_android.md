# Handoff Android: Panduan Integrasi Database Siaga Padang Hibrida V2

Halo Tim Android (Sheva)!

Dokumen ini berisi rangkuman perubahan pada struktur database terbaru (`ranah_siaga_v2.db`) dan apa saja penyesuaian yang perlu Anda lakukan di kode Android (Kotlin/Room) untuk menyambut konsep Hibrida V2 (TES + TEA).

---

## 1. File Utama yang Perlu Anda Gunakan

1.  **`ranah_siaga_v2.db.zip` (8,5 MB)**: File database SQLite terbaru yang sudah berisi rute evakuasi Hibrida V2 (143 TES bertingkat + 12 TEA lahan perbukitan).
2.  **`dataset_manifest.json`**: Jangan tempel manifest pembuat basis data ke `assets/dataset_manifest.json` di Android. Manifest di aplikasi sudah benar dan menggunakan format serta perhitungan checksum file `.db` (bukan zip). Anda hanya perlu memakai checksum file `.db` untuk verifikasi.
3.  **`docs/erd_siaga_padang.md`**: Referensi ERD lengkap jika Anda ingin memeriksa kolom/relasi secara visual.
4.  **`docs/siaga_padang_erd.dbml`**: Skrip skema ERD untuk diimpor ke `dbdiagram.io`.

---

## 2. Perubahan Penting di Struktur Database (Wajib Dibaca)

### A. View Gabungan (`v_fasilitas_evakuasi`)
Untuk mempermudah Android menampilkan daftar semua tempat evakuasi tanpa membedakan apakah itu gedung (TES) atau bukit (TEA), Anda bisa memanggil *view* `v_fasilitas_evakuasi`. *View* ini menyatukan `tb_tes` dan `tb_tea` ke dalam satu tabel virtual seragam dengan kolom penting seperti:
*   `facility_id`
*   `nama`
*   `jenis` ('TES' atau 'TEA')
*   `tipe_evakuasi` ('Vertikal' atau 'Horizontal')

### B. Konsep Rute Navigasi TEA yang Berbeda (Metode *Next-Node*)
Berbeda dengan rute TES (`tb_routes`) yang menyimpan seluruh panjang *array node* ke dalam satu baris (misal `rank_1_path` = "101,105,110..."), rute menuju TEA dirancang menggunakan tabel transisi khusus bernama **`tb_tea_next`** demi menghemat ukuran database (agar tidak membengkak).

**Cara kerja algoritma rute TEA di Android:**
1.  Dari lokasi *User*, periksa node terdekat (`node_A`).
2.  Baca tabel `tb_tea_routes` untuk mengetahui TEA mana yang paling dekat. (Misalnya yang terpilih adalah `TEA_01`).
3.  Untuk merangkai rute navigasi, lakukan pengambilan data sekaligus (satu kueri) untuk seluruh node:
    *   `SELECT * FROM tb_tea_next WHERE tea_id = 'TEA_01'`
4.  Rangkai jalur dari titik awal pengguna hingga sampai ke TEA di dalam memori. Aplikasi butuh jalur lengkap sejak awal untuk menggambar garis rute, menghitung belokan, dan jarak. Jangan lakukan kueri berulang secara bertahap di setiap simpul.

---

## 3. Tugas Integrasi untuk Tim Android

1.  **Update Skema Room:** Aplikasi sengaja tidak memakai *entity* untuk tabel `tb_tea`, `tb_tea_routes`, dan `tb_tea_next`. Cukup gunakan kueri dengan `@SkipQueryVerification` dan kelas baris biasa (sama seperti tabel TES dan rute yang sudah ada). Menambahkan *entity* berisiko membuat gagal buka basis data karena pemeriksaan struktur yang ketat.
2.  **Ubah Logika Navigasi TEA:** Terapkan perangkaian navigasi *next-node* di memori melalui satu kueri sekaligus (untuk mendapatkan seluruh rute).
3.  **Tampilkan Peta:** Tampilkan titik TEA dengan warna yang berbeda (misalnya hijau) agar pengguna tahu bahwa itu adalah lahan terbuka/bukit (perhatikan tabel `tb_tea` memiliki kapasitas dalam bentuk angka riil), bukan gedung bertingkat (TES).

Semangat integrasi untuk GEMASTIK! Database saat ini ukurannya berhasil ditekan menjadi sangat kecil (hanya 8,5 MB versi zip), sehingga dijamin aman untuk proses sinkronisasi cepat.
