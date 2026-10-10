import sqlite3
import pandas as pd

conn = sqlite3.connect("ranah_siaga_v2.db")
cur = conn.cursor()

print("=== DAFTAR TABEL & VIEW DI ranah_siaga_v2.db ===")
cur.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name")
for t, name in cur.fetchall():
    if not name.startswith("sqlite_"):
        cur.execute(f'SELECT COUNT(*) FROM "{name}"')
        cnt = cur.fetchone()[0]
        print(f"[{t.upper()}] {name:<22} : {cnt:,} baris")

print("\n=== CONTOH ISI TABEL tb_tea ===")
df_tea = pd.read_sql_query("SELECT tea_id, kode_tea, sektor, nama_tea, kapasitas, lat, lon FROM tb_tea LIMIT 5", conn)
print(df_tea.to_string(index=False))

print("\n=== CONTOH ISI TABEL tb_tea_routes ===")
df_routes = pd.read_sql_query("SELECT origin_node_id, nearest_tea_id, nearest_tea_nama, nearest_tea_eta, nearest_tea_dist_m FROM tb_tea_routes LIMIT 5", conn)
print(df_routes.to_string(index=False))

print("\n=== CONTOH QUERY VIEW v_fasilitas_evakuasi (TES vs TEA) ===")
df_view = pd.read_sql_query("""
    SELECT jenis, tipe_evakuasi, COUNT(*) as total_titik, SUM(kapasitas) as total_kapasitas 
    FROM v_fasilitas_evakuasi 
    GROUP BY jenis, tipe_evakuasi
""", conn)
print(df_view.to_string(index=False))

conn.close()
