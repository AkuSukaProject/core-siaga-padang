import openpyxl
import pandas as pd

wb = openpyxl.load_workbook("LAMP 1 - TABEL IDENTIFIKASI KETERSEDIAAN DAN KEBUTUHAN FASILITAS EVAKUASI TINGKAT ZONA KOTA PADANG (CETAK).xlsx", data_only=True)
ws = wb['TABEL 2 ']

data = []
current_sektor = None

for r in range(5, ws.max_row + 1):
    sektor_val = ws.cell(r, 1).value
    if sektor_val and str(sektor_val).strip().startswith("SEKTOR"):
        current_sektor = str(sektor_val).strip()
    
    zona_no = ws.cell(r, 3).value
    luas = ws.cell(r, 4).value
    jiwa = ws.cell(r, 5).value
    moda = ws.cell(r, 6).value
    tes_no = ws.cell(r, 7).value
    tes_loc = ws.cell(r, 8).value
    tes_cap = ws.cell(r, 9).value
    rute = ws.cell(r, 10).value
    rekom_jalan = ws.cell(r, 11).value
    tea_no = ws.cell(r, 12).value
    tea_loc = ws.cell(r, 13).value
    tea_cap = ws.cell(r, 14).value
    
    data.append({
        'row': r,
        'sektor': current_sektor,
        'zona_no': zona_no,
        'luas_ha': luas,
        'jiwa': jiwa,
        'moda': moda,
        'tes_no': tes_no,
        'tes_loc': tes_loc,
        'tes_cap': tes_cap,
        'rute': rute,
        'rekom_jalan': rekom_jalan,
        'tea_no': tea_no,
        'tea_loc': tea_loc,
        'tea_cap': tea_cap
    })

df = pd.DataFrame(data)

# Let's aggregate for each TEA:
# 1. Total population assigned to routes leading to this TEA
# 2. All zones feeding into this TEA
# 3. Routes feeding into this TEA
# 4. TEA capacity

print("=== DETAIL ANALISIS TEMPAT EVAKUASI AKHIR (TEA) KOTA PADANG ===")
# Find rows where TEA is defined
tea_defs = df[df['tea_no'].notnull() & ~df['tea_no'].astype(str).str.isdigit() & (df['tea_no'] != 'NO')].copy()

for idx, t in tea_defs.iterrows():
    kode = str(t['tea_no']).strip()
    sektor = t['sektor']
    loc = t['tea_loc']
    cap = t['tea_cap']
    
    # find all rows in this sektor or mentioning this TEA in route
    in_sektor = df[df['sektor'] == sektor]
    rutes_to_tea = in_sektor[in_sektor['rute'].str.contains(kode, case=False, na=False)]
    
    zones = [str(z) for z in in_sektor['zona_no'].dropna().unique() if str(z).strip() != '']
    total_jiwa = in_sektor['jiwa'].apply(lambda x: float(x) if isinstance(x, (int, float)) else 0).sum()
    
    print(f"\n[{kode}] {loc}")
    print(f"  Sektor                 : {sektor}")
    print(f"  Kapasitas Daya Tampung : {cap:,} Jiwa" if isinstance(cap, (int, float)) else f"  Kapasitas Daya Tampung : {cap}")
    print(f"  Zona-zona Terkait      : {', '.join(zones[:8])}{'...' if len(zones)>8 else ''}")
    print(f"  Total Estimasi Warga Sektor : {total_jiwa:,.0f} Jiwa")
    
    # Contoh rute utama
    sample_routes = in_sektor['rute'].dropna().unique()
    valid_routes = [r.replace('\n', ' ') for r in sample_routes if kode in r]
    if valid_routes:
        print(f"  Jalur Evakuasi Utama Menuju TEA:")
        for vr in valid_routes[:3]:
            print(f"    - {vr}")
