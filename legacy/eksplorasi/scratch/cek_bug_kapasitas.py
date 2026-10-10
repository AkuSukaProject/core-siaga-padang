import sqlite3
import pandas as pd

df_csv = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
if 'Sektor' in df_csv.columns:
    df_csv = df_csv[df_csv['Sektor'].astype(str).str.upper() != 'JUMLAH']

print("=== SAMPLE KAPASITAS_TES DI CSV ===")
print(df_csv[['Nama_Bersih', 'Kapasitas_TES']].head(10))

print("\nTotal Sum Kapasitas Raw di CSV (tanpa parsing aneh):")
raw_sum = df_csv['Kapasitas_TES'].dropna().sum()
print(f"Total Kapasitas Riil BPBD di CSV: {raw_sum:,.0f} Jiwa")

conn = sqlite3.connect("ranah_siaga.db")
df_db = pd.read_sql_query("SELECT tes_id, nama_tes, kapasitas FROM tb_tes", conn)
conn.close()

print("\n=== SAMPLE KAPASITAS DI SQLITE tb_tes ===")
print(df_db.head(10))
print(f"Total Sum Kapasitas di SQLITE tb_tes: {df_db['kapasitas'].sum():,.0f} Jiwa")
