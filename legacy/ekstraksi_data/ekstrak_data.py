import pandas as pd
import osmnx as ox
import json
import urllib.request
import urllib.parse
import re
import os

ox.settings.use_cache = True
ox.settings.log_console = False

print("=" * 70)
print("SIAGA PADANG: EKSTRAKSI & PENGGABUNGAN DATA TES DENGAN GEOCODING INTERNET")
print("=" * 70)

# ---------------------------------------------------------
# 1. FUNGSI PEMBERSIH DAN NORMALISASI
# ---------------------------------------------------------
def clean_coord(val):
    if pd.isna(val) or val is None: return None
    t = str(val).strip().replace(',', '.')
    try:
        v = float(t)
        return v if v != 0.0 else None
    except ValueError:
        return None

def clean_name_key(s):
    if pd.isna(s) or s is None: return ""
    s = re.sub(r'\(.*?\)', '', str(s))
    return re.sub(r'[^A-Z0-9]', '', s.upper())

def koordinat_valid_padang(lat, lon):
    return (-1.05 <= lat <= -0.80) and (100.25 <= lon <= 100.50)

def parse_float_safe(val, decimals=2):
    if pd.isna(val) or val is None: return None
    t = str(val).strip().replace(',', '.')
    try:
        return round(float(t), decimals)
    except ValueError:
        return None

def parse_int_safe(val):
    if pd.isna(val) or val is None: return None
    t = str(val).strip().replace(',', '.')
    try:
        return int(round(float(t)))
    except ValueError:
        return None

# ---------------------------------------------------------
# 2. BACA DARI FILE CSV EXISTING (Koordinat Evakuasi TES)
# ---------------------------------------------------------
csv_existing = "Koordinat Evakuasi TES - Sheet1.csv"
csv_map_num = {}
csv_map_nama = {}

if os.path.exists(csv_existing):
    df_csv = pd.read_csv(csv_existing)
    df_csv['lat_c'] = df_csv['Latitude'].apply(clean_coord)
    df_csv['lon_c'] = df_csv['Longitude'].apply(clean_coord)
    
    for idx, r in df_csv.iterrows():
        lat, lon = r['lat_c'], r['lon_c']
        if lat is not None and lon is not None:
            coords = (lat, lon)
            k_nama = clean_name_key(r.get('Nama_Bersih', ''))
            k_lokasi = clean_name_key(r.get('Lokasi_TES', ''))
            if k_nama: csv_map_nama[k_nama] = coords
            if k_lokasi: csv_map_nama[k_lokasi] = coords
            if pd.notna(r.get('Nomor_TES', None)):
                try:
                    num = int(float(str(r['Nomor_TES']).strip()))
                    csv_map_num[num] = coords
                except ValueError:
                    pass

print(f"[+] Loaded {len(csv_map_nama)} lokasi berkoordinat dari CSV existing.")

# ---------------------------------------------------------
# 3. EKSTRAKSI DATA TES DARI EXCEL LAMPIRAN 1
# ---------------------------------------------------------
excel_path = "LAMP 1 - TABEL IDENTIFIKASI KETERSEDIAAN DAN KEBUTUHAN FASILITAS EVAKUASI TINGKAT ZONA KOTA PADANG (CETAK).xlsx"
print(f"[+] Membaca file master Excel: {excel_path}...")

df_raw = pd.read_excel(excel_path, header=None)

current_sektor = None
current_zona = None
current_luas = None
current_jiwa = None

extracted_rows = []

for idx in range(4, len(df_raw)):
    row = df_raw.iloc[idx]
    
    if pd.isna(row[0]) and pd.isna(row[2]) and pd.isna(row[6]) and pd.isna(row[7]):
        continue
        
    if pd.notna(row[0]):
        current_sektor = str(row[0]).strip()
        
    if pd.notna(row[2]):
        current_zona = str(row[2]).strip()
        current_luas = row[3]
        current_jiwa = row[4]
        
    tes_nomor = row[6]
    tes_lokasi = row[7]
    tes_kapasitas = row[8]
    
    if pd.isna(tes_lokasi) or str(tes_lokasi).strip().upper() == 'LOKASI':
        continue

    if pd.notna(tes_nomor) and "LANGSUNG MENUJU TEA" in str(tes_nomor):
        tes_lokasi = "LANGSUNG MENUJU TEA"
        
    nama_bersih = str(tes_lokasi).split('(')[0].strip() if pd.notna(tes_lokasi) else None
    
    extracted_rows.append({
        'Sektor': current_sektor,
        'Zona': current_zona,
        'Luas_Ha': parse_float_safe(current_luas),
        'Jumlah_Jiwa': parse_int_safe(current_jiwa),
        'Nomor_TES': tes_nomor,
        'Lokasi_TES': str(tes_lokasi).strip(),
        'Kapasitas_TES': parse_int_safe(tes_kapasitas),
        'Nama_Bersih': nama_bersih
    })

df_tes = pd.DataFrame(extracted_rows)
print(f"[+] Total entri TES terekstrak dari Excel Lamp 1: {len(df_tes)} lokasi.")

# ---------------------------------------------------------
# 4. FUNGSI GEOCODING INTERNET OPEN SOURCE (PHOTON OSM)
# ---------------------------------------------------------
def ambil_koordinat_internet(nama_clean):
    if not nama_clean or len(nama_clean) < 3:
        return None, None
        
    queries = [f"{nama_clean}, Padang"]
    
    # Ekspansi singkatan nama bangunan Indonesia
    expanded = nama_clean
    expanded = re.sub(r'\bSDN\b', 'SD Negeri', expanded)
    expanded = re.sub(r'\bSMPN\b', 'SMP Negeri', expanded)
    expanded = re.sub(r'\bSMAN\b', 'SMA Negeri', expanded)
    expanded = re.sub(r'\bSMKN\b', 'SMK Negeri', expanded)
    expanded = re.sub(r'\bMESJID\b', 'Masjid', expanded)
    if expanded != nama_clean:
        queries.append(f"{expanded}, Padang")
        
    for q in queries:
        url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(q)}&lat=-0.94&lon=100.36&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'SiagaPadangEvacuation/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if data.get('features'):
                    coords = data['features'][0]['geometry']['coordinates']
                    lon, lat = coords[0], coords[1]
                    if koordinat_valid_padang(lat, lon):
                        return lat, lon
        except Exception:
            pass
            
    return None, None

# ---------------------------------------------------------
# 5. GABUNGKAN DATA & GEOCODING OTOMATIS UNTUK TES TANPA KOORDINAT
# ---------------------------------------------------------
print("[+] Memproses dan mencari koordinat internet untuk TES yang belum memiliki koordinat...")

lat_list = []
lon_list = []
status_list = []

csv_cnt = 0
internet_cnt = 0
tea_cnt = 0
failed_cnt = 0

for idx, row in df_tes.iterrows():
    nama = row['Nama_Bersih']
    lokasi = row['Lokasi_TES']
    norm_n = clean_name_key(nama)
    norm_l = clean_name_key(lokasi)
    
    num = None
    if pd.notna(row['Nomor_TES']):
        try:
            num = int(float(str(row['Nomor_TES']).strip()))
        except ValueError:
            pass

    lat, lon, status = None, None, 'Perlu Cek / Gagal'

    # A. Cek apakah ini entri TEA
    if 'LANGSUNGMENUJU' in norm_n or 'LANGSUNGMENUJU' in norm_l:
        status = 'LANGSUNG MENUJU TEA'
        tea_cnt += 1
    # B. Cek dari database CSV (Skip pencarian internet jika koordinat sudah ada)
    elif num is not None and num in csv_map_num:
        lat, lon = csv_map_num[num]
        status = 'Dari CSV'
        csv_cnt += 1
    elif norm_n in csv_map_nama:
        lat, lon = csv_map_nama[norm_n]
        status = 'Dari CSV'
        csv_cnt += 1
    elif norm_l in csv_map_nama:
        lat, lon = csv_map_nama[norm_l]
        status = 'Dari CSV'
        csv_cnt += 1
    else:
        # C. Ambil koordinat otomatis dari internet (Photon OpenStreetMap API)
        glat, glon = ambil_koordinat_internet(nama)
        if glat is not None:
            lat, lon = glat, glon
            status = 'Dari Internet (Photon OSM)'
            internet_cnt += 1
            print(f"  [INTERNET OK] '{nama}' -> ({lat:.5f}, {lon:.5f})")
        else:
            failed_cnt += 1
            print(f"  [KOSONG] '{nama}' (Sektor: {row['Sektor']}, Zona: {row['Zona']})")

    lat_list.append(lat)
    lon_list.append(lon)
    status_list.append(status)

df_tes['Latitude'] = lat_list
df_tes['Longitude'] = lon_list
df_tes['Status_Koordinat'] = status_list

# ---------------------------------------------------------
# 6. EKSPOR HASIL DALAM FORMAT CSV DAN EXCEL
# ---------------------------------------------------------
file_output_csv = "data_tes_padang_lengkap_berkoordinat.csv"
file_output_excel = "data_tes_padang_lengkap_berkoordinat.xlsx"

df_tes.to_csv(file_output_csv, index=False, encoding='utf-8-sig')
df_tes.to_excel(file_output_excel, index=False)


print("\n" + "=" * 70)
print("LAPORAN AKHIR OPIMASI EKSTRAKSI & GEOCODING DATA TES")
print("=" * 70)
print(f"Total Lokasi TES (Excel Lamp 1) : {len(df_tes)}")
print(f" - Menggunakan Koordinat CSV    : {csv_cnt} lokasi")
print(f" - Ditemukan via Internet OSM   : {internet_cnt} lokasi")
print(f" - Langsung Menuju TEA          : {tea_cnt} lokasi")
print(f" - Belum Ada / Gagal Geocode    : {failed_cnt} lokasi")
print("-" * 70)
print(f"File Output CSV   : {file_output_csv}")
print(f"File Output Excel : {file_output_excel}")
print("=" * 70)