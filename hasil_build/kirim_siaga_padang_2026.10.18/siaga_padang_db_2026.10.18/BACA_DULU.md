# Paket Database Siaga Padang 2026.10.18

Paket untuk tim mobile (Mikail) dan backend (Sheva). Versi ini **menggantikan** semua paket sebelumnya (2026.10.10 sampai 2026.10.17) dan mengikuti kontrak DB di `siagapadang/docs/PEMBAGIAN_TUGAS_BPBD.md` §1 dan §2.1.

## Yang baru

1. **Porsi TES `tb_route_shares` diganti seluruhnya.** Isinya porsi TES per simpang dari model pergerakan kolektif berkapasitas (program linear atas 167 TES yang kapasitasnya tercatat; 77 TES tanpa kapasitas hanya cadangan). Jalurnya ada di tabel baru `tb_tes_next`. Kontrak lengkap: `dokumen/kontrak_porsi_tujuan.md`.
2. **Kolom baru:** `tb_tes.nearest_node_id`, `tb_tes.snap_dist_m`, `tb_tea.snap_dist_m`.
3. **Jaringan jalan kembali ke graf OSM 8 Agustus 2026, sama dengan 2026.10.16.** Graf 20 Oktober dari 2026.10.17 tidak dipakai. Selain butir 1 dan 2, semua tabel identik dengan 2026.10.16 (31.813 simpul, 11.418 di zona merah). `edge_id` kembali ke penomoran 2026.10.16.

Ke-28 kueri `@Query` aplikasi (branch `feat/final-keselamatan-navigasi`, commit `ed9bb49`) sudah diuji berjalan pada DB ini. Perubahan kode dari handoff sebelumnya (§4: `NodeEntity.jarak_pantai_m`, kolom nullable, konversi ETA 1,2 ÷ 0,894) tetap berlaku.

## Siapa memakai apa

| Berkas | Mobile (Mikail) | Backend (Sheva) |
|---|---|---|
| `data/ranah_siaga_v4.db` | Ganti `android/app/src/main/assets/ranah_siaga.db` | Paket `/api/v1/sync/network`, masukan stage & bootstrap |
| `data/dataset_manifest_android.json` | Ganti `android/app/src/main/assets/dataset_manifest.json` | Argumen `--manifest` |
| `data/ranah_siaga_v4.db.zip` | – | Unduhan awal saat startup (`app/main.py`) |
| `data/beban_tes.csv` | Beban model tiap TES terhadap kapasitas | Rujukan |
| `data/daftar_tes_tea.csv`, `data/peta_celah_kelurahan.csv`, `data/bpbd_2019_tanpa_titik.csv` | Rujukan | Rujukan |
| `dokumen/handoff_android.md` | **Baca dulu** | – |
| `dokumen/handoff_backend.md` | – | **Baca dulu** |
| `dokumen/kontrak_porsi_tujuan.md` | **Kontrak `tb_route_shares` + `tb_tes_next`** | Rujukan |
| `dokumen/erd_siaga_padang.md`, `dokumen/siaga_padang_erd.dbml` | Struktur tabel | Struktur tabel |
| `dokumen/aturan_evakuasi_bpbd.md` | Acuan teks & perilaku UI | Rujukan |
| `dokumen/pertanyaan_bpbd.md` | Hal yang masih ditanyakan ke BPBD | Hal yang masih ditanyakan ke BPBD |
| `gambar/` | Gambar laporan (1.1, 3.1, 5.4, beban TES) dari DB ini | – |
| `gambar/erd/` | ERD: `erd_siaga_padang_dbdiagram.png` (semua kolom, gaya dbdiagram), `_ringkas.png` (Gambar 5.3), `_lengkap.png`, `erd_siaga_padang.html` (kamus data), `.drawio`, `.puml` | – |

Ganti `.db` dan manifest **bersamaan**. Angka di `dokumen/simulasi_kanonis.md` (68,3%) dihitung pada 2026.10.17; pada dasar data yang dipakai versi ini (sama dengan 2026.10.16) hasilnya 68,2%.

## Checksum

| Berkas | Ukuran (byte) | SHA-256 |
|---|---|---|
| `ranah_siaga_v4.db` | 36,970,496 | `173b8010ace05ad15735a5a6e49cd1589419113325267de17f4ae8bb56b93175` |
| `ranah_siaga_v4.db.zip` | 7,615,548 | `fa2a9d82038c14b6125931bd5079c04bd777b0c53bd281a903ace5b47f8a6293` |

Sumber: repo `AkuSukaProject/core-siaga-padang`, folder `hasil_build/`.
