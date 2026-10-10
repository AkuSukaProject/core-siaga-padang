# Dokumentasi Proyek Siaga Padang (Core Engine)

Selamat datang di direktori dokumentasi `core-siaga-padang`. Proyek ini merupakan repositori utama (*core engine*) untuk pemrosesan spasial, perhitungan rute evakuasi tsunami, dan simulasi akademik untuk wilayah Kota Padang.

**Mulai cepat:** ekstrak `Data BPBD/SHP kecamatan.rar` ke `Data BPBD/SHP kecamatan/`, lalu jalankan `env\Scripts\python.exe build_db.py` untuk membangun `ranah_siaga_v4.db`, dan `generate_dbml_file.py` untuk memperbarui ERD.

## Daftar Isi Dokumentasi

### Aturan
1. **[Aturan Evakuasi BPBD](aturan_evakuasi_bpbd.md)**
   Aturan dan konteks evakuasi tsunami Kota Padang dari wawancara BPBD: batas waktu, kecepatan, menjauhi pantai, jembatan, kriteria TES/TEA, panduan masyarakat, dan masukan aplikasi. Menjadi acuan semua logika engine.
2. **[Aturan Proyek & Data](aturan_proyek.md)**
   Konvensi kode, aturan sumber data (data BPBD vs data lama), pembersihan data, dan pedoman reproduktibilitas.
3. **[Kebijakan Kapasitas TES & TEA](kebijakan_kapasitas_tes_tea.md)**
   Perbedaan perlakuan kapasitas TES (dibatasi) dan TEA (tidak dibatasi), serta kebijakan UI saat darurat.

### Engine & Database
4. **[Arsitektur Sistem & Database](arsitektur.md)**
   Alur `build_db.py` dari data BPBD sampai SQLite, cara routing dihitung, dan cara aplikasi memakai tiap tabel.
5. **[Pembangun Database V4](build_db_v4.md)**
   Inventaris data `Data BPBD/` (dipakai dan tidak), parameter, hasil build terbaru, dan hal yang perlu dikonfirmasi ke BPBD.
6. **[Spesifikasi ERD](erd_siaga_padang.md)** dan **[DBML](siaga_padang_erd.dbml)**
   Struktur tabel `ranah_siaga_v4.db`. DBML dibangkitkan otomatis dari DB.
7. **[Simulasi Kanonis](simulasi_kanonis.md)**
   Parameter resmi simulasi dan status `simulasi_resmi_padang.py` (belum diselaraskan dengan data v4).

### Integrasi Android
8. **[Handoff Android](handoff_android.md)**
   Perubahan perilaku database v4 yang perlu ditangani aplikasi.
9. **[Konsep Pengalihan Rute Lokal](konsep_pengalihan_rute_lokal.md)**
   Pencarian jalan memutar secara offline dengan cek simpang tetangga.

### Lain-lain
10. **[Draft Revisi Proposal](draft_revisi_proposal.md)**
    Draf teks proposal. Angkanya masih dari simulasi data lama.
11. **[Transkrip Wawancara BPBD](wawancara%20bpbd/)**
    Sumber asli aturan evakuasi (hasil *speech-to-text*).
