# Kontrak Tabel Porsi Tujuan (DRAF untuk disepakati)

Status: **draf, belum dibangun**. Disusun untuk butir 4 pesan Mikail. Isi DB baru dibuat setelah butir 1–4 disepakati.
Versi pembanding: 2026.10.16 (tidak diubah).

## Tujuan

Hasil pembagian penduduk dari model (pergerakan kolektif berkapasitas) disimpan di HP, lalu Android memakainya secara luring
untuk memilih TES. Simulator dan Android membaca tabel yang sama dengan aturan yang sama.

## Tabel 1: `tb_route_shares` (menggantikan isi lama)

Isi lama (nama tujuan, tanpa jalur) tidak dibaca Android, jadi tabel ini diganti seluruhnya.

| Kolom | Tipe | Isi |
|---|---|---|
| `origin_node_id` | INTEGER NOT NULL | Simpang asal (`tb_nodes.node_id`), hanya simpul zona merah |
| `urutan` | INTEGER NOT NULL | 1, 2, 3, … Urutan pindah bila tujuan terhalang: porsi terbesar dulu, lalu ETA tercepat, lalu `facility_id` |
| `jenis` | TEXT NOT NULL | `TES` (lihat "Pilihan A/B" di bawah) |
| `facility_id` | TEXT NOT NULL | `TES_xxx` (`tb_tes.tes_id`) |
| `porsi` | REAL NOT NULL | 0–1. Jumlah per `origin_node_id` = 1 (toleransi 1e-6). Boleh 0: kandidat cadangan yang sempat tetapi tidak diberi porsi |
| `sempat_15` | INTEGER NOT NULL | 1 bila waktu riil ≤ 15 menit saat t = 0 (dari simpang, tanpa jalan ke simpang) |
| `eta_tabel` | REAL NOT NULL | Menit pada 1,2 m/s, **sudah termasuk** jalan lurus simpul ujung → titik TES (sama dengan `rank_k_eta`) |
| `sumber_jalur` | TEXT NOT NULL | `tb_tes_next` |

`PRIMARY KEY (origin_node_id, urutan)`, `UNIQUE (origin_node_id, facility_id)`, indeks pada `origin_node_id`.

## Tabel 2: `tb_tes_next` (baru)

Rantai simpul ke tiap TES skenario, sama persis bentuknya dengan `tb_tea_next`:

| Kolom | Tipe | Isi |
|---|---|---|
| `tes_id` | TEXT NOT NULL | `TES_xxx` |
| `node_id` | INTEGER NOT NULL | Simpul sekarang |
| `next_node_id` | INTEGER NOT NULL | Simpul berikutnya |

`PRIMARY KEY (tes_id, node_id)`. Rantai berakhir di simpul terdekat TES (kolom baru `tb_tes.nearest_node_id`).
Android merangkainya dengan kueri rekursif yang sudah dipakai untuk TEA.

Alasan memakai rantai sendiri, bukan merujuk `tb_routes` rank k: kandidat dihitung ulang dari 167 TES dan banyak yang
tidak ada di rank 1–3 lama. Satu bentuk rantai untuk semua kandidat lebih sederhana bagi aplikasi dan simulator.
Satu pohon per TES cukup karena semua jalur ke TES itu berasal dari satu pohon Dijkstra. Perkiraan ukuran: beberapa
puluh sampai ratusan ribu baris (± 3–8 MB); DB tetap di bawah 75 MB. Angka pasti dilaporkan saat build.

## Kolom baru di tabel lama

- `tb_tes.nearest_node_id` INTEGER: simpul tujuan rute (ujung rantai `tb_tes_next`).
- `tb_tes.snap_dist_m` REAL: jarak lurus simpul → titik TES (sudah termasuk di `eta_tabel`; untuk tampilan saja).
- `tb_tea.snap_dist_m` REAL: untuk menambah jalan lurus simpul → titik TEA saat Android menghitung waktu TEA dari panjang rantai.

`tb_routes`, `tb_tea_routes`, `tb_safe_routes_v2` tidak berubah (kompatibilitas).

## Pilihan A/B (perlu diputuskan)

- **A (usul Habib): tabel hanya berisi TES.** TEA dan zona hijau dipilih Android menurut aturan 2b dari tabel yang sudah
  ada; porsi hanya dipakai bila tidak ada TEA/zona hijau yang sempat. Satu jumlah porsi per simpang.
- **B (usul Mikail): TES, TEA, dan ZONA_AMAN dalam satu tabel.** TEA/zona hijau tidak berkapasitas dan dipilih
  deterministik, sehingga barisnya selalu porsi 1. Akibatnya simpang yang di t = 0 ke zona hijau juga butuh porsi TES
  terpisah untuk saat waktu sudah lewat, dan "jumlah porsi = 1" harus dihitung per kelompok jenis.

## Aturan pemakaian (sama untuk Android dan simulator)

1. Anggaran = 15 menit − waktu sejak gempa − jalan lurus posisi → simpang awal (0,894 m/s).
2. Waktu riil kandidat = `eta_tabel` × 1,2 / 0,894. TEA: panjang rantai `tb_tea_next` / 0,894 + `tb_tea.snap_dist_m` / 0,894.
   Zona hijau: `safe_eta` × 1,2 / 0,894 (tujuannya simpul, tanpa jalan tambahan).
3. Ada TEA/titik zona hijau yang sempat → pilih yang [**tercepat** / **terjauh dari pantai**] (belum diputuskan).
4. Tidak ada → TES dari porsi di antara baris dengan waktu riil ≤ anggaran; porsi dinormalkan ulang di antara yang sempat.
   Nilai undian dari kode keluarga, sekali di simpang awal, tujuan dikunci.
5. Tidak ada yang sempat → baris dengan waktu tercepat.
6. Terhalang / tidak lagi memenuhi aturan → baris berikutnya menurut `urutan` yang masih sempat.

## Pemeriksaan sebelum rilis

- Setiap `origin_node_id` zona merah yang punya kandidat TES: jumlah `porsi` = 1.
- Setiap `(origin_node_id, facility_id)` dapat dirangkai lewat `tb_tes_next` sampai `tb_tes.nearest_node_id`, dan panjang
  rantai / 1,2 m/s + snap = `eta_tabel` (selisih ≤ 0,01 menit).
- Semua kandidat lolos syarat arah (menjauh > 15°, ≤ 100 m tidak dinilai); kandidat lewat jembatan ≥ 20 m hanya bila tidak ada
  yang tanpa jembatan.
- `facility_id` hanya dari 167 TES berkapasitas tercatat.
