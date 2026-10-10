import sqlite3
import pandas as pd

conn = sqlite3.connect("ranah_siaga.db")
cursor = conn.cursor()

print("=== CEK NAMA KEMBAR DI tb_tes ===")
df_dup = pd.read_sql_query("""
    SELECT nama_tes, COUNT(*) as jumlah 
    FROM tb_tes 
    GROUP BY nama_tes 
    HAVING COUNT(*) > 1
""", conn)

print("Jumlah Nama Kembar/Duplikat:", len(df_dup))
if not df_dup.empty:
    print(df_dup.to_string(index=False))
else:
    print("[SUKSES AMAN] Tidak ada satu pun nama_tes yang duplikat di tb_tes.")

cursor.execute("SELECT COUNT(*), COUNT(DISTINCT nama_tes), COUNT(DISTINCT tes_id) FROM tb_tes")
total, total_nama_uniq, total_id_uniq = cursor.fetchone()
print(f"\nDetail Jumlah: Total Baris={total}, Nama Unik={total_nama_uniq}, TES_ID Unik={total_id_uniq}")

conn.close()
