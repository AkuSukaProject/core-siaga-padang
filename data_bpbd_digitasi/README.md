# Digitasi peta evakuasi BPBD

`build_db.py` memakai berkas di folder ini untuk zona merah (`tb_inundation_zones`, `tb_nodes.is_safe`).

| Berkas | Isi |
|---|---|
| `zona_rawan_peta_evakuasi_bpbd.geojson` | Fitur `zona_rawan_peta_evakuasi` (zona merah peta evakuasi, 3.393 ha) dan `cakupan_peta` (daratan yang tergambar di peta, 6.509 ha). EPSG:4326 |
| `digitasi_peta_evakuasi.py` | Skrip yang membuat GeoJSON di atas dari gambar sumber |

## Sumber

`Data BPBD/Peta TES dan Potensial Shelter.png`, "Peta Tempat Evakuasi Sementara dan Lokasi Potensial Shelter" BPBD Kota Padang, skala 1:15.000, lengkap dengan Blue Line. Peta ini mencakup Padang bagian tengah dan utara, dari sekitar Tabing sampai Bukit Gado-Gado.

## Mengapa dipakai

Raster bahaya KRB 2023–2027 adalah hasil model landaan dan lebih sempit dari zona rawan di peta evakuasi. Contohnya Masjid Raya Syekh Ahmad Khatib: di raster KRB masjid ini berada sekitar 250 m di luar landaan, sedangkan di peta evakuasi masjid berada di dalam zona merah, sekitar 500 m dari tepinya, dan zona baru berakhir di Blue Line Ampang. Peta evakuasi inilah yang dikenal warga lewat rambu Blue Line. Karena itu zona merah di DB adalah **gabungan** keduanya: landaan KRB ditambah zona rawan peta evakuasi.

## Cara digitasi

1. **Georeferensi.** Gambar tidak punya koordinat. Pola air di peta (laut dan sungai) dicocokkan dengan air nyata, yaitu laut di luar garis pantai OSM dan `Sungai_AR` Basemap BPBD. Skala dicari dulu lewat korelasi silang (hasilnya 1,22 m per piksel), lalu transformasi afin diperhalus.
2. **Ketelitian.**
   - Tepi air peta rata-rata 19 m dari tepi air nyata. Sebagian selisih ini karena sungai di peta digambar disederhanakan.
   - 69 titik kuning "Potensial Shelter" berjarak median 25 m dari koordinat TES di DB; 72% di antaranya dalam 50 m.
   - Untuk peta 1:15.000, perkirakan ketelitian tepi zona ±20–40 m.
3. **Zona.** Piksel merah "Zona Rawan Tsunami" diambil. Jalan, label, panah, dan sungai yang menutupinya diisi dengan kelas terdekat (merah atau krem). Lubang < 1 ha, yang berasal dari teks label, diisi. Hasilnya dipotong ke daratan menurut garis pantai OSM.

## Batasan

- Hasil ini digitasi dari gambar, bukan data vektor asli BPBD. Bila BPBD memberi berkas vektor zona rawan dan Blue Line ([pertanyaan_bpbd.md](../docs/pertanyaan_bpbd.md)), berkas itu yang dipakai.
- Di luar `cakupan_peta` (misalnya Bungus, Teluk Kabung, dan Koto Tangah bagian utara), zona merah hanya dari raster KRB.
- Posisi Blue Line belum didigitasi.

Jalankan ulang hanya bila gambar sumber berganti:
```
env\Scripts\python.exe data_bpbd_digitasi\digitasi_peta_evakuasi.py
```
Hasilnya mengubah isi DB, jadi build sesudahnya harus memakai label versi baru.
