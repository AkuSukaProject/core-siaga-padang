import pandas as pd

df_csv = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
if 'Sektor' in df_csv.columns:
    df_csv = df_csv[df_csv['Sektor'].astype(str).str.upper() != 'JUMLAH']

def parse_kapasitas_fixed(val, default=300.0):
    if pd.isna(val) or val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val) if val > 0 else default
    val_str = str(val).strip()
    try:
        val_clean = val_str.replace(',', '.')
        res = float(val_clean)
        return res if res > 0 else default
    except ValueError:
        return default

df_csv['Clean_Cap'] = df_csv['Kapasitas_TES'].apply(parse_kapasitas_fixed)

print("Sample parsed capacities:")
print(df_csv[['Nama_Bersih', 'Kapasitas_TES', 'Clean_Cap']].head(10))

print("\nTotal Sum Correct Capacity:", df_csv['Clean_Cap'].sum())
