import sqlite3
import pandas as pd

conn = sqlite3.connect("ranah_siaga.db")
cursor = conn.cursor()

print("=== SAMPLE 1 BARIS REAL UNTUK DEVELOPER ANDROID ===")

print("\n1. SAMPLE BARIS tb_edges (GEOMETRY WKT LINESTRING):")
df_edge = pd.read_sql_query("SELECT * FROM tb_edges WHERE geometry LIKE 'LINESTRING%' LIMIT 1", conn)
if df_edge.empty:
    df_edge = pd.read_sql_query("SELECT * FROM tb_edges LIMIT 5", conn)
print(df_edge.to_string(index=False))

print("\n2. SAMPLE BARIS tb_routes:")
df_route = pd.read_sql_query("SELECT * FROM tb_routes LIMIT 1", conn)
print(df_route.to_string(index=False))

print("\n3. SAMPLE BARIS tb_tes:")
df_tes = pd.read_sql_query("SELECT * FROM tb_tes LIMIT 2", conn)
print(df_tes.to_string(index=False))

conn.close()
