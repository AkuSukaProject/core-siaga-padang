import pandas as pd

excel_path = "LAMP 1 - TABEL IDENTIFIKASI KETERSEDIAAN DAN KEBUTUHAN FASILITAS EVAKUASI TINGKAT ZONA KOTA PADANG (CETAK).xlsx"
df_lamp1 = pd.read_excel(excel_path, sheet_name=0, skiprows=2)

print("Jumlah baris Excel:", len(df_lamp1))
print("Kolom Excel:")
for i, col in enumerate(df_lamp1.columns):
    print(f"  Col {i}: {col}")

# Print last 10 rows of Excel to inspect row TOTAL (row 437,861)
print("\n10 Baris Terakhir Excel Lamp 1:")
print(df_lamp1.tail(10).to_string())
