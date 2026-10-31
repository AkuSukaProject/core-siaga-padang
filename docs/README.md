# Dokumentasi Proyek Siaga Padang (Core Engine)

Selamat datang di direktori dokumentasi `core-siaga-padang`. Proyek ini merupakan repositori utama (*core engine*) untuk pemrosesan spasial, perhitungan rute evakuasi tsunami, dan simulasi akademik untuk wilayah Kota Padang.

**Mulai cepat:** ekstrak `Data BPBD/SHP kecamatan.rar` ke `Data BPBD/SHP kecamatan/`, lalu jalankan `env\Scripts\python.exe build_db.py` untuk membangun `hasil_build/ranah_siaga_v4.db` (beserta zip dan manifest), dan `generate_dbml_file.py` untuk memperbarui ERD. DB terbaru (2026.10.18) memakai graf 8 Agustus 2026 lewat `--graf`; perintah lengkapnya di [build_db_v4.md](build_db_v4.md).

## Daftar Isi Dokumentasi

### Aturan
1. **[Aturan Evakuasi BPBD](aturan_evakuasi_bpbd.md)**
   Aturan dan konteks evakuasi tsunami Kota Padang dari wawancara BPBD: batas waktu, kecepatan, menjauhi pantai, jembatan, kriteria TES/TEA, panduan masyarakat, dan masukan aplikasi. Menjadi acuan semua logika engine.
2. **[Aturan Proyek & Data](aturan_proyek.md)**
   Konvensi kode, aturan sumber data (data BPBD vs data lama), pembersihan data, dan pedoman reproduktibilitas.
3. **[Kebijakan Kapasitas TES & TEA](kebijakan_kapasitas_tes_tea.md)**
   Perbedaan perlakuan kapasitas TES (dibatasi) dan TEA (tidak dibatasi), serta kebijakan UI saat darurat.

### Engine & Database
3a. **[Aturan, Konteks, dan Metode Pembuatan DB](metodologi_pembuatan_db.md)**
   Ringkasan satu dokumen: latar masalah, sumber data, aturan BPBD dan kontrak yang diterapkan, langkah metode `build_db.py`, isi tabel, validasi, dan batasan.
4. **[Arsitektur Sistem & Database](arsitektur.md)**
   Alur `build_db.py` dari data BPBD sampai SQLite, cara routing dihitung, dan cara aplikasi memakai tiap tabel.
5. **[Pembangun Database V4](build_db_v4.md)**
   Inventaris data `Data BPBD/` (dipakai dan tidak), parameter, hasil build terbaru, dan hal yang perlu dikonfirmasi ke BPBD.
6. **[Spesifikasi ERD](erd_siaga_padang.md)**, **[gambar ERD](erd/erd_siaga_padang_lengkap.png)**, **[ERD gaya dbdiagram](erd/erd_siaga_padang_dbdiagram.png)**, **[ERD interaktif + kamus data](erd/erd_siaga_padang.html)**, dan **[DBML](siaga_padang_erd.dbml)**
   Struktur tabel `ranah_siaga_v4.db`. DBML dibangkitkan otomatis dari DB.
6a. **[Kontrak Porsi Tujuan](kontrak_porsi_tujuan.md)**
   Isi `tb_route_shares` dan `tb_tes_next` (sejak 2026.10.18): porsi TES berkapasitas, aturan pemakaian di aplikasi, dan pemeriksaan sebelum rilis.
7. **[Simulasi Kanonis](simulasi_kanonis.md)**
   Metodologi, parameter, dan hasil resmi simulasi Baseline vs Siaga Padang (`analisis/simulasi_resmi_padang.py`).

### Integrasi Android
8. **[Handoff Android](handoff_android.md)** dan **[Handoff Backend](handoff_backend.md)**
   Berkas, isi DB terhadap kontrak, perubahan kode yang wajib, langkah rilis, dan daftar uji untuk aplikasi (Mikail) dan backend (Sheva).
9. **[Konsep Pengalihan Rute Lokal](konsep_pengalihan_rute_lokal.md)**
   Pencarian jalan memutar secara offline dengan cek simpang tetangga.

### Lain-lain
10. **[Draft Revisi Proposal](draft_revisi_proposal.md)**
    Draf teks proposal. Angkanya masih dari simulasi data lama; angka baru ada di Simulasi Kanonis.
11. **[Pertanyaan Lanjutan untuk BPBD](pertanyaan_bpbd.md)**
    Hal yang perlu dipastikan ke BPBD setelah data diolah (arah, jembatan, lantai, titik bangunan, TEA), siap kirim beserta lampirannya.
12. **[Transkrip Wawancara BPBD](wawancara%20bpbd/)**
    Sumber asli aturan evakuasi (hasil *speech-to-text*).
