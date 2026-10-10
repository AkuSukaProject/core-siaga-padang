# Handoff Backend: Dataset Siaga Padang V4

Halo Tim Backend (Sheva)!

Database offline baru `ranah_siaga_v4.db` versi **2026.10.11** dibangun ulang dari data BPBD Kota Padang (KRB 2023–2027, TES/TEA 2025) dan aturan evakuasi hasil wawancara BPBD. Dokumen ini merangkum yang perlu disiapkan di backend (repo `siagapadang/backend`): sinkronisasi titik evakuasi ke PostGIS dan pembaruan dataset lewat jaringan. Sisi aplikasi ada di [handoff_android.md](handoff_android.md) (Mikail).

> **Versi resmi: 2026.10.11.** `.db` berukuran 31.068.160 byte, SHA-256 `8545cfd217990509cec61c0d88f0f7355428dc1c090d2a0126746504778b0584`. Paket berlabel 2026.10.10 (baik di Release maupun ZIP kiriman sebelumnya) sudah **tidak dipakai**.
>
> Perubahan dari 2026.10.10: (1) kolom `safe_zone_id` di `tb_safe_routes` dan `tb_safe_routes_v2`; (2) nama fasilitas unik: 3 titik ganda digabung (TES_061 Incasi Raya → TES_060, TES_126 Youth Center → TES_127, TES_164 FK Unand → TES_163), 3 TEA yang bernama sama dengan TES diberi "(area evakuasi)", dan 8 TES bernama sama di lokasi berbeda diberi nama kelurahan; (3) TES_208 Universitas Taman Siswa dikeluarkan (verifikasi BPBD 2019 "tidak potensial"); (4) nama wilayah "Nan XX" (sebelumnya "Nan Xx"). ID fasilitas lain tidak berubah.

---

## 1. Berkas

Ambil dari folder `hasil_build/` repo engine (atau lampiran GitHub Release tag `db-<versi>`):

| Berkas | Untuk |
|---|---|
| `ranah_siaga_v4.db` | File yang dilayani endpoint unduhan dataset (SQLite mentah, tanpa zip) dan masukan skrip bootstrap |
| `dataset_manifest_android.json` | Argumen `--manifest` skrip bootstrap: `version`, `checksum` (SHA-256 file `.db`), `size_bytes` |
| `ranah_siaga_v4.db.zip` | Hanya bila unduhan awal saat startup (`app/main.py`) tetap memakai zip |

Nilai untuk versi ini:

| | `.db` | `.zip` |
|---|---|---|
| Ukuran (byte) | 31.068.160 | 6.495.756 |
| SHA-256 | `8545cfd217990509cec61c0d88f0f7355428dc1c090d2a0126746504778b0584` | `a452e2b87fcd3547c2ec6df71a1bbd9eac262c769adac90a867cd0b687688cf5` |

`hasil_build/dataset_manifest.json` adalah catatan engine (berisi checksum zip dan `.db`); jangan dipakai sebagai manifest backend atau aplikasi.

---

## 2. Langkah pemasangan

1. Simpan `ranah_siaga_v4.db` di lokasi `DATASET_PACKAGE_PATH` (default `backend/data/ranah_siaga.db`; ganti nama berkasnya atau atur variabel lingkungan).
2. Jalankan bootstrap:
   ```
   python scripts/bootstrap_from_android_db.py data/ranah_siaga.db \
     --manifest dataset_manifest_android.json --download-url <url-unduhan>
   ```
   Format manifest sudah sesuai yang diminta skrip ini (`verify_package` mencocokkan ukuran dan checksum). Kolom yang dibaca skrip (`tb_tes`: `tes_id`, `nama_tes`, `kapasitas`, `lat`, `lon`; `tb_tea`: `tea_id`, `nama_tea`, ...; `tb_nodes`; `tb_edges`) sudah dicek ada di DB ini.
3. Periksa baris `DataVersion` untuk `shelters` dan `network`: `version = 2026.10.11`, `checksum` = SHA-256 `.db`, `size_bytes = 31068160`, `download_url` terisi.

---

## 3. Yang perlu ditangani

### A. Titik evakuasi lama akan dobel
ID fasilitas berubah: dulu `TES_1…TES_143` dan `TEA_A1…`, sekarang `TES_001…TES_234` dan `TEA_001…TEA_046` (yang aktif 230 TES dan 25 TEA; ID yang tidak dipakai tercatat di `tb_fasilitas_info` dengan `dipakai = 0`). Skrip bootstrap hanya menambah atau memperbarui `EvacuationPoint` berdasarkan `external_id`, jadi ±155 titik lama tetap ada di samping 255 titik baru (beberapa adalah gedung yang sama). Bila staging sudah memuat 2026.10.10, empat titik ini juga harus dinonaktifkan: TES_061, TES_126, TES_164, TES_208. Setelah bootstrap, hapus atau nonaktifkan `EvacuationPoint` yang `external_id`-nya tidak ada di `tb_tes.tes_id` / `tb_tea.tea_id` DB baru, dan periksa data yang merujuk titik lama (laporan kondisi, kejadian, rencana keluarga di aplikasi).

### B. Kapasitas TEA = 0 berarti "tidak ada data"
`tb_tea.kapasitas` bernilai 0 untuk semua TEA karena BPBD tidak membatasi kapasitas TEA. Skrip bootstrap menyimpannya sebagai `capacity = 0`; sebaiknya simpan `NULL` untuk TEA agar tidak terbaca "nol orang". Kapasitas TES: 157 dari BPBD 2025, sisanya estimasi (sumbernya ada di `tb_fasilitas_info.kapasitas_sumber`).

### C. `minimum_app_version` dan `schema_version`
- `schema_version` tetap **`android-v1`** (Entity Room tidak berubah; `SUPPORTED_SCHEMA_VERSION` aplikasi sama).
- Skrip bootstrap mengisi `minimum_app_version = 0.1.0`; ubah menjadi **`0.2.0`** (build Mikail yang memakai `tb_safe_routes_v2`, versionCode 3). DB ini tetap bisa dibuka aplikasi 0.1.0, tetapi rute kawasan amannya belum menjamin aturan menjauhi pantai.

### D. Unduhan awal saat startup
`app/main.py` mengunduh DB dari URL Google Drive bila berkas belum ada. URL itu masih menunjuk ke DB lama. Ganti ke `ranah_siaga_v4.db.zip` yang baru; isi zip bernama `ranah_siaga_v4.db`, jadi ganti nama setelah ekstraksi atau sesuaikan `DATASET_PACKAGE_PATH`.

### E. Zona rendaman dan kawasan aman di PostGIS (bila dipakai)
Skrip bootstrap tidak menyentuh `InundationZone` dan `SafeZone`. Jika backend menyajikan poligon zona, perbarui dari `tb_inundation_zones` (56 poligon zona merah per kelurahan, dari raster bahaya tsunami KRB 2023–2027) dan `tb_safe_zones` (98 poligon zona hijau). Geometri disimpan sebagai WKT WGS84 di kolom `geometry_wkt`.

---

## 4. Isi data (ringkas)

| Data | Nilai |
|---|---|
| TES / TEA dipakai | 230 / 25 (4 TES digabung/tidak potensial dan 21 TEA BPBD dikeluarkan karena berada di area landaan; daftar di `tb_fasilitas_info`, `dipakai = 0`) |
| Simpang jalan / ruas | 31.813 (8.812 di zona merah) / 39.216 |
| Penduduk terpapar | 242.750 jiwa di 56 kelurahan |
| Kecepatan & batas waktu | 0,894 m/s (orang terlemah), 20 menit |

Struktur tabel lengkap: [erd_siaga_padang.md](erd_siaga_padang.md). Aturan evakuasi: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md).

---

## 5. Belum diuji dari sisi engine

Kecocokan DB dengan skrip bootstrap dan endpoint sudah dicek dari kode sumber, tetapi belum dijalankan ke PostGIS. Mohon uji: bootstrap ke basis data dev, endpoint daftar versi dataset, dan unduhan dataset dari aplikasi (cek checksum dan `size_bytes` cocok).
