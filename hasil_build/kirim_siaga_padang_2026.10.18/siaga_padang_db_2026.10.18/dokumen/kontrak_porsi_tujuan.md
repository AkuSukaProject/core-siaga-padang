# Kontrak Tabel Porsi Tujuan

Status: **dibangun di DB 2026.10.18** (keputusan tim 26 Oktober: pilihan A, 2b terjauh dari pantai, LP minimal jiwa × menit,
porsi cadangan dari sisa kapasitas, 77 TES tanpa kapasitas hanya cadangan).
Dasar data: graf, zona, fasilitas, dan penduduk sama persis dengan 2026.10.16 (pembanding); yang berubah hanya
`tb_route_shares`, `tb_tes_next`, kolom baru di `tb_tes`/`tb_tea`, dan metadata.

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
| `kapasitas_tercatat` | INTEGER NOT NULL | 1 = TES berkapasitas tercatat (167). 0 = TES tanpa kapasitas, hanya cadangan; tampilkan "kapasitas belum tercatat" |
| `cadangan` | INTEGER NOT NULL | 1 = simpang yang pada t = 0 keluar zona (TEA/zona hijau sempat); porsinya dari sisa kapasitas dan tidak ikut beban model |

`PRIMARY KEY (origin_node_id, urutan)`, `UNIQUE (origin_node_id, facility_id)` (WITHOUT ROWID).
Hanya simpang zona merah yang punya minimal satu TES lolos syarat arah (10.688 simpang); simpang lain memakai TEA/zona hijau.
Paling banyak 10 baris per simpang (median 3).

### Cara porsi diisi (per simpang, pada t = 0 dari simpang)

| Kelompok | Syarat | Porsi |
|---|---|---|
| beban | Tidak ada TEA/zona hijau sempat ≤ 15 menit; ada TES berkapasitas sempat | Program linear serentak: minimum Σ jiwa × menit tempuh, beban TES ≤ kapasitas. Kelebihan → TES sempat tercepat (dicatat) |
| cadangan (`cadangan` = 1) | TEA/zona hijau sempat ≤ 15 menit | Sebanding sisa kapasitas TES berkapasitas yang sempat (bila sisa habis: sebanding kapasitas). Tanpa TES berkapasitas sempat: seperti dua baris di bawah |
| tanpa kapasitas (`kapasitas_tercatat` = 0) | Tidak ada TES berkapasitas, TEA, atau zona hijau yang sempat; ada TES tanpa kapasitas yang sempat | Porsi 1 ke yang tercepat |
| tidak sempat | Tidak ada TES yang sempat | Porsi 1 ke TES tercepat |

Kandidat lewat jembatan ≥ 20 m hanya dipakai bila tidak ada kandidat tanpa jembatan di kelompok yang sama.
Simpang tanpa penduduk dihitung 0,001 jiwa supaya tetap mendapat porsi yang deterministik. Tanpa bilangan acak;
solusi seri dipecah dengan biaya 1e-6 menit per nomor urut TES. Build ulang menghasilkan SHA-256 yang sama.

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

Diputuskan **pilihan A**: tabel hanya berisi TES. TEA dan zona hijau dipilih Android menurut aturan 3 dari tabel yang
sudah ada.

## Aturan pemakaian (sama untuk Android dan simulator)

1. Anggaran = 15 menit − waktu sejak gempa − jalan lurus posisi → simpang awal (0,894 m/s).
2. Waktu riil kandidat = `eta_tabel` × 1,2 / 0,894. TEA: panjang rantai `tb_tea_next` / 0,894 + `tb_tea.snap_dist_m` / 0,894.
   Zona hijau: `safe_eta` × 1,2 / 0,894 (tujuannya simpul, tanpa jalan tambahan).
3. Ada TEA (utama/alternatif) atau titik zona hijau v2 yang sempat → pilih yang **terjauh dari pantai**.
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
- Porsi > 0 ke TES tanpa kapasitas hanya bila simpang itu tidak punya TES berkapasitas yang sempat.

## Hasil 2026.10.18 (t = 0, dari simpang, 0,894 m/s)

Penyebut: 313.862 jiwa di 11.418 simpang zona merah.

| Kelompok | Simpang | Jiwa |
|---|---|---|
| beban (LP) | 3.039 | 89.158 |
| cadangan (keluar zona) | 3.275 | 95.094 |
| tanpa kapasitas (cadangan TES tanpa kapasitas) | 616 | 15.976 |
| tidak sempat (TES tercepat) | 3.758 | 95.184 |
| tanpa TES lolos arah (hanya TEA/zona hijau) | 730 | 18.451 |

- Jiwa dengan tujuan sempat ≤ 15 menit (TEA, zona hijau, atau TES): 216.561 (69,0%).
- Beban model: 89.158 jiwa ke 122 dari 167 TES berkapasitas (kapasitas total 155.980). 37 TES melebihi kapasitas,
  dengan total kelebihan 23.443 jiwa, karena bagi simpang tersebut hanya TES itu yang sempat. Rincian di
  `hasil_build/beban_tes.csv`.
- `tb_route_shares` 32.201 baris, `tb_tes_next` 40.677 baris; DB 35,26 MB.
