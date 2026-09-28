# Dokumentasi Proyek Siaga Padang (Core Engine)

Selamat datang di direktori dokumentasi `core-siaga-padang`. Proyek ini merupakan repositori utama (*core engine*) untuk pemrosesan spasial, perhitungan rute evakuasi tsunami, dan simulasi akademik untuk wilayah Kota Padang.

## Daftar Isi Dokumentasi

Berikut adalah rincian dokumen yang tersedia di direktori ini untuk membantu Anda memahami standar, arsitektur, dan aturan yang berlaku di dalam proyek:

1. **[Simulasi Kanonis](simulasi_kanonis.md)**
   Menjelaskan konsep simulasi rujukan resmi (*canonical simulation*), parameter yang digunakan (BNPB/BPS), serta perbedaan antara skrip simulasi evaluasi dan skrip *core engine*.

2. **[Arsitektur Sistem & Database](arsitektur.md)**
   Menjelaskan alur kerja spasial (*routing engine*), penggunaan struktur data *NetworkX Graph*, serta skema basis data hibrida SQLite (`ranah_siaga.db`) yang diekspor untuk aplikasi Android.

3. **[Aturan Proyek & Data](aturan_proyek.md)**
   Berisi standar konvensi kode, metodologi ekstraksi data, dan pedoman reproduktibilitas untuk memastikan konsistensi hasil akademik penelitian ini.
