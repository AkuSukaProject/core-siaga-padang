import openpyxl
import pandas as pd

wb = openpyxl.load_workbook("LAMP 1 - TABEL IDENTIFIKASI KETERSEDIAAN DAN KEBUTUHAN FASILITAS EVAKUASI TINGKAT ZONA KOTA PADANG (CETAK).xlsx", data_only=True)
ws = wb['TABEL 2 ']

print("--- HEADER INSPECTION (Rows 1 to 5) ---")
for r in range(1, 6):
    row_vals = [f"Col {c}: {ws.cell(r, c).value}" for c in range(1, ws.max_column + 1) if ws.cell(r, c).value is not None]
    print(f"Row {r} -> {row_vals}")

print("\n--- ALL UNIQUE TEA ENTRIES IN LAMP 1 ---")
tea_list = []
for r in range(4, ws.max_row + 1):
    sektor = ws.cell(r, 1).value
    zona = ws.cell(r, 2).value
    rute = ws.cell(r, 10).value
    keterangan = ws.cell(r, 7).value
    col12 = ws.cell(r, 12).value
    col13 = ws.cell(r, 13).value
    col14 = ws.cell(r, 14).value
    col15 = ws.cell(r, 15).value
    
    vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
    vals_str = " | ".join(str(v) for v in vals if v is not None)
    
    tea_list.append({
        'row': r,
        'sektor': sektor,
        'zona': zona,
        'col7_tes': keterangan,
        'col10_rute': rute,
        'col12': col12,
        'col13': col13,
        'col14': col14,
        'col15': col15,
        'raw': vals_str
    })

df_tea = pd.DataFrame(tea_list)
print(f"Total baris data: {len(df_tea)}")

# Look at rows where col12 or col13 or col14 or col15 is not null
tea_cols = df_tea[df_tea['col12'].notnull() | df_tea['col13'].notnull() | df_tea['col14'].notnull() | df_tea['col15'].notnull()]
print("\nRows where Col 12-15 have data:")
for idx, r in tea_cols.head(20).iterrows():
    print(f"Row {r['row']} | Sektor: {r['sektor']} | Zona: {r['zona']} | Col 12: {r['col12']} | Col 13: {r['col13']} | Col 14: {r['col14']} | Col 15: {r['col15']}")
    print(f"   Rute: {r['col10_rute']}")
