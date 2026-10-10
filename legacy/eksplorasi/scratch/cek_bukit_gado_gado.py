import pandas as pd

df_pend = pd.read_csv("penduduk_kota_padang.csv")
print("=== DUA KELURAHAN DENGAN POPULASI TERPAPAR 0 DI DATASET BPBD ===")
df_zero = df_pend[df_pend['JUMLAH JIWA TERPAPAR (JIWA)'] == 0]
print(df_zero)

print("\n=== SEMUA KELURAHAN PADANG SELATAN DI DATASET BPBD ===")
df_ps = df_pend[df_pend['KECAMATAN'].astype(str).str.upper() == 'PADANG SELATAN']
print(df_ps.to_string(index=False))

excel_lamp2 = "LAMP 2 - TABEL KAJIAN RISIKO BENCANA TSUNAMI KOTA PADANG.xlsx"
df_lamp2 = pd.read_excel(excel_lamp2, sheet_name='TSUNAMI', skiprows=2)
print("\nBaris Bukit Gado-Gado di Excel Lamp 2 BPBD:")
print(df_lamp2[df_lamp2['DESA'].astype(str).str.upper().str.contains('GADO')][['KECAMATAN', 'DESA', 'JUMLAH JIWA TERPAPAR (JIWA)']])
