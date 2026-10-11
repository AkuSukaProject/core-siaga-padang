# Konsep Pengalihan Rute Dinamis (Dynamic Detour) secara Offline di Android

Dokumen ini disusun sebagai panduan konseptual bagi Tim Android untuk mengimplementasikan fitur "Pencarian Jalan Alternatif / Rute Memutar" secara cerdas, tanpa membebani memori HP atau memperbesar ukuran database.

## Latar Belakang Masalah
Dalam kondisi evakuasi Tsunami, rute utama pra-komputasi (Rank 1) menuju sebuah Shelter (TES/TEA) bisa saja terhalang puing atau banjir. 
* **Pertanyaan:** Bisakah aplikasi mencarikan "jalan tikus" atau jalan memutar ke *TES yang sama*?
* **Tantangan:** Menjalankan algoritma pencarian graf (*Dijkstra / A-Star*) penuh di HP saat bencana akan menguras baterai dan memori. Menyimpan semua jalur alternatif di database akan melanggar batas maksimum file (75 MB).

## Solusi: Algoritma *Neighbor Lookup* (Cek Tetangga)
Alih-alih menghitung rute dari nol, aplikasi Android cukup memanfaatkan konsep **"Cek Simpang Sebelah"**. Database kita (yang murni statis) sebenarnya menyimpan rute terbaik dari **setiap simpang yang ada di Padang**.

Ketika *user* terhalang, HP hanya perlu melihat simpang apa saja yang ada di kiri/kanannya, lalu "menyontek" rute dari simpang tetangga tersebut.

### Alur Kerja (Step-by-Step Logic)

1. **Deteksi Rute Terhalang:**
   Anggap *user* berada di **Node X**, dan jalan utama di depannya (menuju Node Y) terlaporkan hancur.
   
2. **Cari Simpang Tetangga:**
   Aplikasi menjalankan kueri SQLite ke tabel `tb_edges` untuk melihat daftar semua persimpangan yang terhubung langsung secara fisik dengan posisi *user* saat ini (Node X).
   
3. **Filter Tetangga:**
   Aplikasi mencoret Node Y dari daftar tetangga karena jalan ke arah sana hancur. Tersisa tetangga yang aman (misalnya **Node W** dan **Node Z**).
   
   **[PENTING] Aplikasi wajib melakukan dua pengecekan krusial pada rute milik tetangga ini:**
   * **Mencegah Jalur Berputar (Backtracking):** Rute Rank 1 milik tetangga (misal Node W) tidak boleh melewati kembali ruas jalan yang terhalang (X → Y). Hal ini karena rute di *database* dihitung *sebelum* hambatan terjadi.
   * **Memastikan Tujuan Sama:** Pastikan rute Rank 1 milik Node W memang menuju **TES A**. Jika rutenya menuju TES lain, maka itu bukan "jalan memutar ke TES yang sama", melainkan pengalihan murni ke TES alternatif.

4. **Kalkulasi Cost Sederhana (Penjumlahan):**
   Aplikasi melakukan kalkulasi ringan (1 langkah) untuk tetangga yang aman:
   
   * **Via Tetangga W:** 
     *(Jarak jalan kaki Node X → W)* **+** *(ETA dari Node W ke TES A di `tb_routes`)*
   * **Via Tetangga Z:** 
     *(Jarak jalan kaki Node X → Z)* **+** *(ETA dari Node Z ke TES A di `tb_routes`)*
     
5. **Pemilihan Rute:**
   Bandingkan hasil dari kedua perhitungan di atas. Angka terkecil (waktu tercepat) adalah pemenangnya. Aplikasi lalu memunculkan instruksi: *"Berbeloklah ke Simpang W, lalu ikuti panduan baru menuju TES A"*.

---

## Referensi Query SQLite untuk Android

Berikut adalah contoh gambaran operasi pencarian tetangga yang sangat ringan:

```sql
-- 1. Mendapatkan daftar tetangga dari posisi user (Misal: user di Node 123)
-- Menggunakan OR karena ruas jalan (edge) disimpan satu arah di database.
SELECT CASE WHEN u = 123 THEN v ELSE u END AS id_tetangga, length AS jarak_meter 
FROM tb_edges 
WHERE u = 123 OR v = 123;
```

Setelah ID tetangga (misal 456 dan 789) didapat di *code* Kotlin/Java:

```sql
-- 2. Mengambil contekan sisa rute dari tetangga yang valid
SELECT rank_1_tes, rank_1_eta, rank_1_path 
FROM tb_routes 
WHERE origin_node_id IN (456, 789);
```

## Penyesuaian untuk Database V4

Dua perubahan di `ranah_siaga_v4.db` memengaruhi logika cek tetangga:

1. **Tetangga di zona aman tidak punya baris `tb_routes`.** Jika kueri langkah 2 tidak mengembalikan baris untuk sebuah tetangga, periksa `tb_nodes.is_safe` tetangga itu. Jika `1`, tetangga tersebut sudah di zona aman: arahkan pengguna ke sana (jarak X → tetangga saja), karena itu pilihan terbaik.
2. **Aturan menjauhi pantai berlaku juga untuk pengalihan.** Jangan memilih tetangga yang lebih dekat ke pantai daripada posisi pengguna, kecuali selisihnya kecil (≤ 50 m, sama dengan toleransi engine). Jarak ke pantai tersedia di `tb_nodes.jarak_pantai_m`. Tujuan akhir rute tetangga sudah lolos syarat arah (menjauh > 15°) karena dihitung di prakomputasi.

```sql
-- Jarak ke pantai untuk posisi user dan tetangganya
SELECT node_id, jarak_pantai_m FROM tb_nodes WHERE node_id IN (123, 456, 789);
```

Jika semua tetangga tersaring, aplikasi langsung beralih ke TES Rank 2/3 atau ke rute zona aman (`tb_safe_routes`, atau `tb_safe_routes_v2` bila dipakai).

> Angka efektivitas di bagian "Ekspektasi Realistis" berasal dari simulasi dengan database lama (v2) dan perlu dihitung ulang dengan v4.

## Keunggulan Arsitektur Ini
* **Performa Tinggi (O(1) / O(N) Lookup):** HP tidak melakukan komputasi algoritma *Graph* yang rumit, hanya melakukan `SELECT` SQLite sederhana.
* **Tidak Merusak Ukuran Database:** Fitur ini murni memakai tabel yang sudah ada di `ranah_siaga_v4.db` (±29 MB). Tidak ada kolom tambahan yang diperlukan.
* ***Self-Healing Route*:** Rute seolah-olah "hidup" dan bisa mengoreksi dirinya sendiri mengikuti pergerakan berjalan cepat *user* di lapangan.

---

## Ekspektasi Realistis (Berdasarkan Hasil Simulasi)

Berdasarkan pengujian simulasi, harap dicatat bahwa fitur jalan memutar 1-langkah (*1-hop detour*) ini memiliki efektivitas spesifik:
* **Penemuan Rute ke TES yang Sama:** Jalan memutar ke TES asal (TES A) hanya akan ditemukan pada **±22% kasus**.
* **Kecepatan Relatif:** Dari persentase tersebut, hanya pada **21% kasus** hasilnya terbukti lebih cepat daripada langsung memindahkan warga ke TES Rank 2. Pada sisa kasus lainnya, aplikasi tetap akan memandu warga untuk beralih secara logis ke TES Rank 2 atau Rank 3.
* **Mengapa tidak diperluas?** Jika jangkauan pencarian diperluas ke 2–3 langkah persimpangan, rasio penemuan jalan memutar akan naik menjadi 35–45%. Namun, hal ini mewajibkan algoritma penelusuran graf (seperti BFS) beroperasi murni di dalam HP, yang **dilarang keras** demi menjaga performa memori dan baterai tetap ringan.

**Kesimpulan Akhir:** Fitur pencarian tetangga 1-langkah ini tetap **sangat layak dan efisien** untuk diterapkan sebagai langkah pertama (*fallback*) saat *user* menekan opsi "Jalan tidak bisa dilewati", sebelum pengalihan penuh ke gedung TES berikutnya (Rank 2) diputuskan.
