import pandas as pd

df = pd.read_csv("data_tes_padang_lengkap_berkoordinat.csv")
if 'Sektor' in df.columns:
    df = df[df['Sektor'].astype(str).str.upper() != 'JUMLAH']

tea_keywords = ['BUKIT', 'TEA', 'AKHIR', 'KETINGGIAN', 'PERBUKITAN', 'LAPANGAN', 'LAHAN']

def check_tea(val):
    val_str = str(val).upper()
    return any(k in val_str for k in tea_keywords)

df['is_tea'] = df['Lokasi_TES'].apply(check_tea) | df['Nama_Bersih'].apply(check_tea)
tea_df = df[df['is_tea']]

print("Total Fasilitas di Dataset:", len(df))
print("Jumlah Berindikasi TEA (Tempat Evakuasi Akhir / Perbukitan / Lahan Tinggi):", len(tea_df))

print("\nDaftar Gedung / Fasilitas dengan indikasi TEA:")
print(tea_df[['Nomor_TES', 'Sektor', 'Zona', 'Lokasi_TES', 'Nama_Bersih']])
