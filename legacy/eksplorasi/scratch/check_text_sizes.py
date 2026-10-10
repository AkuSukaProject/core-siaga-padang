import sqlite3

conn = sqlite3.connect("ranah_siaga_v2.db")
cur = conn.cursor()

# Check length of path columns
cur.execute("""
SELECT 
    AVG(LENGTH(rank_1_path)), 
    AVG(LENGTH(rank_2_path)), 
    AVG(LENGTH(rank_3_path)),
    MAX(LENGTH(rank_1_path))
FROM tb_routes
""")
r = cur.fetchone()
print(f"Rata-rata panjang path di tb_routes: r1={r[0]:.1f}, r2={r[1]:.1f}, r3={r[2]:.1f}, max={r[3]}")

cur.execute("""
SELECT 
    AVG(LENGTH(nearest_tea_path)), 
    AVG(LENGTH(alt_tea_path)),
    MAX(LENGTH(nearest_tea_path))
FROM tb_tea_routes
""")
r2 = cur.fetchone()
print(f"Rata-rata panjang path di tb_tea_routes: near={r2[0]:.1f}, alt={r2[1]:.1f}, max={r2[2]}")

cur.execute("""
SELECT 
    AVG(LENGTH(geometry)),
    MAX(LENGTH(geometry))
FROM tb_edges
""")
r3 = cur.fetchone()
print(f"Rata-rata panjang geometry di tb_edges: avg={r3[0]:.1f}, max={r3[1]}")

conn.close()
