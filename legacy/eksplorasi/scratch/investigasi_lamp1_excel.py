import pandas as pd
import openpyxl

excel_path = "LAMP 1 - TABEL IDENTIFIKASI KETERSEDIAAN DAN KEBUTUHAN FASILITAS EVAKUASI TINGKAT ZONA KOTA PADANG (CETAK).xlsx"
print("Membaca file excel:", excel_path)

excel_file = pd.ExcelFile(excel_path)
print("Sheet names:", excel_file.sheet_names)

df_lamp1 = pd.read_excel(excel_path, sheet_name=0)
print("\nShape sheet 1:", df_lamp1.shape)
print("\nSample Head 20 baris:")
print(df_lamp1.head(20).to_string())

# Load CSV dataset data_tes_padang_lengkap_berkoordinat.csv
df_csv = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
print("\nTotal sum Kapasitas_TES di CSV (semua 184 baris):", df_csv['Kapasitas_TES'].dropna().sum())

# Breakdown 29 lokasi yang tanpa koordinat / gagal geocoding
df_no_coords = df_csv[df_csv['Latitude'].isna() | df_csv['Longitude'].isna() | (df_csv['Latitude'] == 0.0)]
print("\nJumlah Lokasi Tanpa Koordinat di CSV:", len(df_no_coords))
print("Total Sum Kapasitas 29 lokasi tanpa koordinat tersebut:", df_no_coords['Kapasitas_TES'].dropna().sum())

# Breakdown 143 lokasi valid di SQLite
df_valid = df_csv.dropna(subset=['Latitude', 'Longitude'])
df_valid = df_valid[(df_valid['Latitude'] != 0.0) & (df_valid['Longitude'] != 0.0)]
df_unique = df_valid.drop_duplicates(subset=['Latitude', 'Longitude'])

print("\nTotal Sum Kapasitas 143 Lokasi Unik Valid di SQLite:", df_unique['Kapasitas_TES'].dropna().sum())
print("Total Sum Kapasitas 155 Lokasi Valid (sebelum drop dup):", df_valid['Kapasitas_TES'].dropna().sum())
