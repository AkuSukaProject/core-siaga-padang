import openpyxl
import pandas as pd

wb = openpyxl.load_workbook("LAMP 1 - TABEL IDENTIFIKASI KETERSEDIAAN DAN KEBUTUHAN FASILITAS EVAKUASI TINGKAT ZONA KOTA PADANG (CETAK).xlsx", data_only=True)
ws = wb['TABEL 2 ']

all_tea = []
current_sektor = None

for r in range(5, ws.max_row + 1):
    sektor_val = ws.cell(r, 1).value
    if sektor_val and str(sektor_val).strip().startswith("SEKTOR"):
        current_sektor = str(sektor_val).strip()
    
    tea_no = ws.cell(r, 12).value
    tea_lokasi = ws.cell(r, 13).value
    tea_kapasitas = ws.cell(r, 14).value
    
    # Check if this row has a valid TEA entry (tea_no not None and not 'JUMLAH' and not numeric sum)
    if tea_no is not None and str(tea_no).strip() != '' and str(tea_no).strip() != 'None':
        # filter out summary rows where tea_no is an integer count
        tea_no_str = str(tea_no).strip()
        if not tea_no_str.isdigit():
            all_tea.append({
                'row': r,
                'sektor': current_sektor,
                'tea_kode': tea_no_str,
                'tea_lokasi': str(tea_lokasi).strip() if tea_lokasi else '',
                'tea_kapasitas': tea_kapasitas,
                'contoh_rute': ws.cell(r, 10).value
            })

df = pd.DataFrame(all_tea)
print("=== DAFTAR LENGKAP TEMPAT EVAKUASI AKHIR (TEA) KOTA PADANG DARI DOKUMEN RESMI BPBD ===")
print(f"Total TEA Resmi Teridentifikasi: {len(df)}")
for idx, r in df.iterrows():
    print(f"\n[{r['tea_kode']}] {r['sektor']}")
    print(f"   Lokasi     : {r['tea_lokasi']}")
    print(f"   Kapasitas  : {r['tea_kapasitas']:,} Jiwa" if isinstance(r['tea_kapasitas'], (int, float)) else f"   Kapasitas  : {r['tea_kapasitas']}")
    print(f"   Contoh Jalur Utama : {r['contoh_rute']}")
