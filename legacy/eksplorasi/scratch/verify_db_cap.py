import sqlite3
import pandas as pd

conn = sqlite3.connect("ranah_siaga.db")
df = pd.read_sql_query("SELECT tes_id, nama_tes, kapasitas FROM tb_tes", conn)
conn.close()

print("Sample tb_tes capacities:")
print(df.head(10))
print("\nTOTAL DAYA TAMPUNG KOTA PADANG DI SQLITE `tb_tes`:", f"{int(df['kapasitas'].sum()):,} Jiwa")
