# Aturan & Konvensi Proyek

Untuk memastikan lingkungan pengembangan yang terstandar, dapat direproduksi (*reproducible*), dan bersih, semua modifikasi serta kontribusi pada repositori ini harus mematuhi aturan-aturan berikut:

## 1. Konvensi Kode dan Penamaan File

*   **Engine Kanonis**: Database untuk aplikasi hanya boleh dibangun oleh [`build_db.py`](../build_db.py). Skrip lama (`core.py`, `build_db_v2_with_tea.py`, `spatial/`) sudah dipindah ke `legacy/pipeline_db/` dan hanya rujukan historis.
*   **Arsip Skrip Lama**: Skrip yang tidak dipakai lagi dipindah ke `legacy/` (dengan `git mv` agar riwayat terjaga), bukan dihapus atau dibiarkan di root. Root hanya berisi skrip aktif. Lihat [`legacy/README.md`](../legacy/README.md).
*   **Struktur Root**: Root hanya berisi `README.md`, skrip inti (`build_db.py`, `generate_dbml_file.py`, `salin_db_ke_android.py`, `download_peta_full.py`), `requirements.txt`, `padang_full.graphml`, dan folder `data_osm/` (garis pantai/jembatan OSM yang dipakai build). Semua keluaran build (`ranah_siaga_v4.db`, `ranah_siaga_v4.db.zip` yang tidak di-commit, `dataset_manifest.json`, `dataset_manifest_android.json`) ada di `hasil_build/`. Skrip simulasi, analisis, dan visualisasi ada di `analisis/` (keluaran di `analisis/output/`). Dokumen ada di `docs/`, dokumen rujukan (PDF) di `referensi/`, data mentah BPBD di `Data BPBD/`, dan semua skrip lama di `legacy/`. Folder `cache/` (cache HTTP OSMnx, dibuat ulang otomatis) dan `env/` tidak di-commit.
*   **Prefix Eksperimen**: Semua skrip eksperimen atau uji coba sementara yang tidak terkait dengan keluaran produksi (build `.db` atau simulasi kanonis) harus ditempatkan di direktori `scratch/` di root (diabaikan git). Jika ternyata berguna, pindahkan ke `analisis/` dan buat membaca `ranah_siaga_v4.db`.
*   **Kejelasan Eksekusi**: File generator (seperti pembuatan peta atau ekstraksi data) harus menggunakan awalan deskriptif (contoh: `buat_peta_...`, `generate_...`, `ekstrak_...`).
*   **Encoding Teks**: Setiap pengolahan *String* atau akses standar *output/print* direkomendasikan mengonfigurasi encoding UTF-8 di awal skrip (`sys.stdout.reconfigure(encoding='utf-8')`) mengingat data lapangan di Indonesia banyak menggunakan karakter spasial khusus atau tanda baca lokal.
*   **Dokumen Turunan**: `docs/siaga_padang_erd.dbml` dibangkitkan oleh `generate_dbml_file.py` dari DB, sedangkan seluruh isi `hasil_build/` ditulis oleh `build_db.py`. Jangan diedit manual; jalankan ulang skripnya.

## 2. Aturan Sumber Data

*   **Data BPBD adalah sumber utama.** Fasilitas evakuasi, zona merah, penduduk terpapar, dan jalur evakuasi diambil dari folder `Data BPBD/` (KRB 2023–2027, TES/TEA 2025, verifikasi 2019). Daftar data yang dipakai dan alasannya ada di [build_db_v4.md](build_db_v4.md).
*   **Data lama tidak boleh dipakai** untuk produksi: peta dan tabel berbasis data 2013, peta 2014/2017, serta CSV turunan lama (`data_tes_padang_lengkap_berkoordinat.csv`, `data_tea_padang_lengkap_berkoordinat.csv`, `penduduk_kota_padang.csv`, `batas_kelurahan_kota_padang.geojson`), yang sudah dihapus dari repositori (masih ada di riwayat git, lihat `legacy/README.md`). Menurut BPBD data tersebut sudah tidak relevan.
*   **Jangan mengubah data sumber BPBD.** Koreksi (duplikat, salah ketik kelurahan, kapasitas kosong) dilakukan di dalam skrip dan dicatat, misalnya lewat kolom `kapasitas_sumber` atau `alasan_tidak_dipakai`. Hal yang meragukan dilaporkan ke BPBD, bukan diubah diam-diam.
*   **Folder `Data BPBD/` tidak di-commit** (±1,4 GB). Simpan salinannya di luar git dan ekstrak `SHP kecamatan.rar` ke `Data BPBD/SHP kecamatan/` sebelum build.

## 3. Aturan Data & Pembersihan

*   **Pembersihan Numerik Otomatis**: Data dari CSV/Excel resmi pemerintah sering kali mengandung notasi yang tidak konsisten (misal: "3000 Jiwa", "1.500", atau angka dalam list Python jika terpotong). Selalu gunakan fungsi pembersih *string-to-float* tahan banting (seperti `bersihkan_angka_osm()` atau `pd.to_numeric(..., errors="coerce")`) sebelum komputasi matematis.
*   **Pemisah Desimal**: Data lokal cenderung menggunakan tanda koma (`,`) sebagai pemisah desimal koordinat/kapasitas. Penguraian *string* menjadi *float* harus menangani substitusi `,` ke `.` terlebih dahulu.
*   **Validasi Koordinat**: Koordinat yang bernilai 0.0, bernilai *NaN*, atau tidak rasional (berada jauh dari ekuator/wilayah Sumatera Barat) harus difilter secara langsung (dijatuhkan/di-*drop* dari *Dataframe*).
*   **Proyeksi**: Perhitungan jarak dan luas memakai UTM 47S (`EPSG:32747`). Data BPBD memakai beberapa CRS (World Mercator `EPSG:3395`, UTM), jadi selalu transformasikan sebelum dibandingkan. Koordinat yang disimpan ke DB memakai WGS84 (`EPSG:4326`).
*   **Pencocokan Nama**: Saat mencocokkan nama gedung antar dataset, nomor di nama (SMPN 3 vs SMPN 36) harus sama persis. Kemiripan teks saja tidak cukup.

## 4. Aturan Evakuasi

Isi DB wajib mengikuti **kontrak DB aplikasi** di repo `siagapadang` (`docs/PEMBAGIAN_TUGAS_BPBD.md` §1 asumsi kerja dan §2.1 isi DB). Bila kontrak berubah, sesuaikan engine dan terbitkan versi DB baru; jangan memakai satu label versi untuk dua isi DB.


Semua logika routing dan simulasi wajib mengikuti [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md), terutama: batas waktu 20 menit, kecepatan orang terlemah 0,894 m/s, menjauhi pantai (mutlak), penalti jembatan sungai, dan istilah "berjalan cepat" (bukan "berlari"). Bila aturan berubah, perbarui dokumen itu lebih dulu, lalu engine.

## 5. Reproduktibilitas Ilmiah

Karena proyek ini menghasilkan data evaluasi fisik untuk pengajuan riset akademik / kompetisi (Tabel 6.4 Proposal), ketegasan ilmiah adalah suatu keharusan:
*   **Fix Random Seed**: Semua proses pemilihan sampel (*random sampling* agen populasi demografi) harus menetapkan seed statis (misal `np.random.seed(42)`). Jika di-run 100 kali, harus keluar 100 hasil simulasi yang persis sama.
*   **Build Deterministik**: `build_db.py` dengan input yang sama harus menghasilkan SHA-256 yang sama. Jika berubah tanpa perubahan input, cari sumber ketidakpastiannya.
*   **Parameter Tidak Boleh Hard-Coded Asal-asalan**: Jauhi penggunaan *magic numbers*. Setiap konstanta kecepatan, penalti, konversi EPSG, dan batas waktu evakuasi harus dideklarasikan sebagai variabel konfigurasi di bagian atas skrip dan diberi anotasi rujukan asalnya (misal: `"Kecepatan orang terlemah FEMA P-646 = 0.894 m/s"`). Parameter build juga dicatat di tabel `tb_metadata`.
*   **Hindari Duplikasi Skrip Engine Inti**: Perubahan logika routing atau penugasan dilakukan di `build_db.py` dan disinkronkan ke simulasi kanonis, bukan dengan membuat variasi duplikat (misal `build_db_v5.py`) di *root directory*.
*   **Verifikasi Setelah Build**: Setiap perubahan engine harus dicek minimal: skema tabel inti tetap sama dengan versi sebelumnya (kontrak Room Android), tidak ada rute yang melanggar aturan pantai, jalur tersambung, dan ETA sesuai panjang rute.
