import sqlite3

# Hubungkan ke database Anda
conn = sqlite3.connect("database_evakuasi_padang.sqlite")
cursor = conn.cursor()

# Mengambil informasi kolom dari tabel_rute
cursor.execute("PRAGMA table_info(tabel_rute);")
kolom = cursor.fetchall()

print("Struktur Kolom di tabel_rute:")
for col in kolom:
    # col[0] = indeks, col[1] = nama kolom, col[2] = tipe data
    print(f"- Kolom [{col[1]}] dengan tipe data ({col[2]})")

conn.close()