import sqlite3
import pandas as pd

def check_db_integrity():
    print("=" * 60)
    print("VERIFIKASI INTEGRITAS DATABASE ranah_siaga_v2.db")
    print("=" * 60)

    try:
        conn = sqlite3.connect('ranah_siaga_v2.db')
        cur = conn.cursor()

        # 1. Tabel Nodes
        print("\n--- 1. TABEL NODES ---")
        cur.execute("SELECT COUNT(*) FROM tb_nodes")
        total_nodes = cur.fetchone()[0]
        cur.execute("SELECT is_safe, COUNT(*) FROM tb_nodes GROUP BY is_safe")
        node_dist = dict(cur.fetchall())
        print(f"Total Nodes: {total_nodes}")
        print(f"  Aman (is_safe=1)  : {node_dist.get(1, 0)}")
        print(f"  Risiko (is_safe=0): {node_dist.get(0, 0)}")

        # 2. Tabel TES dan TEA
        print("\n--- 2. FASILITAS EVAKUASI ---")
        cur.execute("SELECT COUNT(*) FROM tb_tes")
        print(f"Total TES (Vertikal)   : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM tb_tea")
        print(f"Total TEA (Horizontal) : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM v_fasilitas_evakuasi")
        print(f"Total View Gabungan    : {cur.fetchone()[0]}")

        # 3. Tabel Rute
        print("\n--- 3. DATA RUTE ---")
        cur.execute("SELECT COUNT(*) FROM tb_routes")
        print(f"Rute ke TES            : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM tb_tea_routes")
        print(f"Rute ke TEA            : {cur.fetchone()[0]}")

        # 4. Zona
        print("\n--- 4. ZONA (POLYGON) ---")
        cur.execute("SELECT COUNT(*) FROM tb_safe_zones")
        safe_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tb_inundation_zones")
        inundation_count = cur.fetchone()[0]
        print(f"Total Zona Aman        : {safe_count}")
        print(f"Total Zona Risiko      : {inundation_count}")
        
        # Cek kelurahan spesifik yang dipindah
        moved_kel = ['AIR MANIS', 'BUNGUS TIMUR', 'TELUK KABUNG UTARA', 'GUNUNG SARIK']
        print("\nCek Status Kelurahan Hasil Perbaikan:")
        for kel in moved_kel:
            cur.execute("SELECT 1 FROM tb_safe_zones WHERE nama_zona=?", (kel,))
            in_safe = bool(cur.fetchone())
            cur.execute("SELECT 1 FROM tb_inundation_zones WHERE nama_zona=?", (kel,))
            in_inundation = bool(cur.fetchone())
            
            status = []
            if in_safe: status.append("SAFE")
            if in_inundation: status.append("INUNDATION (ERROR)")
            
            print(f"  - {kel:20s}: {', '.join(status)}")

        # 5. Cek Null atau Anomali (Basic)
        print("\n--- 5. CEK ANOMALI KECIL ---")
        cur.execute("SELECT COUNT(*) FROM tb_nodes WHERE lat IS NULL OR lon IS NULL")
        null_coords = cur.fetchone()[0]
        print(f"Node dengan koordinat kosong : {null_coords}")
        
        cur.execute("SELECT COUNT(*) FROM tb_routes WHERE rank_1_tes IS NULL")
        null_routes = cur.fetchone()[0]
        print(f"Origin tanpa rute TES utama  : {null_routes}")

        conn.close()
        print("\nStatus: Database tampaknya konsisten dan valid.")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    check_db_integrity()
