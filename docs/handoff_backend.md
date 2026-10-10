# Handoff Backend: Dataset Siaga Padang V4

Halo Tim Backend (Sheva)!

Database offline baru `ranah_siaga_v4.db` versi **2026.10.10** dibangun ulang dari data BPBD Kota Padang (KRB 2023–2027, TES/TEA 2025) dan aturan evakuasi hasil wawancara BPBD. Dokumen ini merangkum yang perlu disiapkan di backend (repo `siagapadang/backend`): sinkronisasi titik evakuasi ke PostGIS dan pembaruan dataset lewat jaringan. Sisi aplikasi ada di [handoff_android.md](handoff_android.md) (Mikail).

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
| Ukuran (byte) | 31.055.872 | 6.493.360 |
| SHA-256 | `e0fc52de166ead654d70f8c22ff8c739e0203ee6835b5691caff72407d2e8fd4` | `ad768c966bc27cffd9aa2b9339732549d85ad1f5322fc1459cca14901c9ee08a` |

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
3. Periksa baris `DataVersion` untuk `shelters` dan `network`: `version = 2026.10.10`, `checksum` = SHA-256 `.db`, `size_bytes = 31055872`, `download_url` terisi.

---

## 3. Yang perlu ditangani

### A. Titik evakuasi lama akan dobel
ID fasilitas berubah: dulu `TES_1…TES_143` dan `TEA_A1…`, sekarang `TES_001…TES_234` dan `TEA_001…TEA_025`. Skrip bootstrap hanya menambah atau memperbarui `EvacuationPoint` berdasarkan `external_id`, jadi ±155 titik lama tetap ada di samping 259 titik baru (beberapa adalah gedung yang sama). Setelah bootstrap, hapus atau nonaktifkan `EvacuationPoint` yang `external_id`-nya tidak ada di `tb_tes.tes_id` / `tb_tea.tea_id` DB baru, dan periksa data yang merujuk titik lama (laporan kondisi, kejadian, rencana keluarga di aplikasi).

### B. Kapasitas TEA = 0 berarti "tidak ada data"
`tb_tea.kapasitas` bernilai 0 untuk semua TEA karena BPBD tidak membatasi kapasitas TEA. Skrip bootstrap menyimpannya sebagai `capacity = 0`; sebaiknya simpan `NULL` untuk TEA agar tidak terbaca "nol orang". Kapasitas TES: 157 dari BPBD 2025, sisanya estimasi (sumbernya ada di `tb_fasilitas_info.kapasitas_sumber`).

### C. `minimum_app_version` dan `schema_version`
- `schema_version` tetap **`android-v1`** (Entity Room tidak berubah; `SUPPORTED_SCHEMA_VERSION` aplikasi sama).
- Skrip bootstrap mengisi `minimum_app_version = 0.1.0`. Sebaiknya isi dengan versi aplikasi pertama yang sudah memakai `tb_safe_routes_v2` (perubahan di sisi Mikail). DB ini tetap bisa dibuka aplikasi lama, tetapi rute kawasan amannya belum menjamin aturan menjauhi pantai.

### D. Unduhan awal saat startup
`app/main.py` mengunduh DB dari URL Google Drive bila berkas belum ada. URL itu masih menunjuk ke DB lama. Ganti ke `ranah_siaga_v4.db.zip` yang baru; isi zip bernama `ranah_siaga_v4.db`, jadi ganti nama setelah ekstraksi atau sesuaikan `DATASET_PACKAGE_PATH`.

### E. Zona rendaman dan kawasan aman di PostGIS (bila dipakai)
Skrip bootstrap tidak menyentuh `InundationZone` dan `SafeZone`. Jika backend menyajikan poligon zona, perbarui dari `tb_inundation_zones` (56 poligon zona merah per kelurahan, dari raster bahaya tsunami KRB 2023–2027) dan `tb_safe_zones` (98 poligon zona hijau). Geometri disimpan sebagai WKT WGS84 di kolom `geometry_wkt`.

---

## 4. Isi data (ringkas)

| Data | Nilai |
|---|---|
| TES / TEA dipakai | 234 / 25 (21 TEA BPBD dikeluarkan karena berada di area landaan; daftar di `tb_fasilitas_info`, `dipakai = 0`) |
| Simpang jalan / ruas | 31.813 (8.812 di zona merah) / 39.216 |
| Penduduk terpapar | 242.750 jiwa di 56 kelurahan |
| Kecepatan & batas waktu | 0,894 m/s (orang terlemah), 20 menit |

Struktur tabel lengkap: [erd_siaga_padang.md](erd_siaga_padang.md). Aturan evakuasi: [aturan_evakuasi_bpbd.md](aturan_evakuasi_bpbd.md).

---

## 5. Belum diuji dari sisi engine

Kecocokan DB dengan skrip bootstrap dan endpoint sudah dicek dari kode sumber, tetapi belum dijalankan ke PostGIS. Mohon uji: bootstrap ke basis data dev, endpoint daftar versi dataset, dan unduhan dataset dari aplikasi (cek checksum dan `size_bytes` cocok).
