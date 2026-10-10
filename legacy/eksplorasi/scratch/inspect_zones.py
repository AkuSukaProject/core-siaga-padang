import sqlite3

conn = sqlite3.connect('ranah_siaga_v2.db')
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' OR type='view'")
print('Tables/Views:', [r[0] for r in cur.fetchall()])
print()

# Inundation zones
cur.execute('SELECT COUNT(*) FROM tb_inundation_zones')
print('Inundation zones:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM tb_safe_zones')
print('Safe zones:', cur.fetchone()[0])
print()

cur.execute('SELECT nama_zona, tingkat_bahaya FROM tb_inundation_zones ORDER BY nama_zona')
print('=== INUNDATION ZONES (Risiko) ===')
for r in cur.fetchall():
    print(f'  {r[0]:40s} -> {r[1]}')

print()
cur.execute('SELECT nama_zona, elevasi_m FROM tb_safe_zones ORDER BY nama_zona')
print('=== SAFE ZONES (Aman/Hijau) ===')
for r in cur.fetchall():
    print(f'  {r[0]:40s} -> elevasi {r[1]}m')

# Check nodes is_safe distribution
print()
cur.execute('SELECT is_safe, COUNT(*) FROM tb_nodes GROUP BY is_safe')
print('=== NODE is_safe distribution ===')
for r in cur.fetchall():
    print(f'  is_safe={r[0]}: {r[1]} nodes')

conn.close()
