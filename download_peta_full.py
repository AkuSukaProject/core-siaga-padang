import osmnx as ox

print("="*60)
print("DOWNLOADER GRAF JARINGAN JALAN FULL KOTA PADANG")
print("="*60)

# Mengaktifkan cache agar jika gagal di tengah jalan tidak download dari nol
ox.settings.use_cache = True
ox.settings.log_console = True

tempat = "Kota Padang, Sumatera Barat, Indonesia"

print(f"Meminta data batas wilayah: {tempat}...")
print("Proses ini bisa memakan waktu 2-10 menit tergantung koneksi internet.")
print("Mengunduh jaringan jalan untuk pejalan kaki (walk)...")

try:
    # Mengunduh graf. network_type='walk' karena kita fokus evakuasi jalan kaki
    # Jika ingin seluruh jalan (termasuk tol/jalan raya besar), ganti menjadi 'all'
    G_full = ox.graph_from_place(tempat, network_type='walk')
    
    print(f"\n[SUKSES] Graf berhasil diunduh!")
    print(f"Jumlah Persimpangan (Nodes): {len(G_full.nodes)}")
    print(f"Jumlah Ruas Jalan (Edges): {len(G_full.edges)}")
    
    file_output = "padang_full.graphml"
    print(f"Menyimpan ke dalam format GraphML: {file_output}...")
    ox.save_graphml(G_full, file_output)
    
    print("✅ PROSES SELESAI! File siap digunakan.")

except Exception as e:
    print(f"\n[ERROR] Terjadi kesalahan saat mengunduh: {e}")