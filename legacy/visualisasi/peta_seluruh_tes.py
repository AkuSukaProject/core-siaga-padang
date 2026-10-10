import sqlite3
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import webbrowser
import os

print("=" * 60)
print("SIAGA PADANG: VISUALISASI PETA LOKASI TES DARI DATABASE SQLITE")
print("=" * 60)

db_path = "ranah_siaga.db"
file_csv = "data_tes_padang_lengkap_berkoordinat.csv"

# 1. Membaca Data dari SQLite Database (ranah_siaga.db)
if os.path.exists(db_path):
    print(f"[+] Membaca data TES langsung dari Database Offline SQLite: '{db_path}'...")
    conn = sqlite3.connect(db_path)
    df_shelter = pd.read_sql_query("SELECT tes_id, nama_tes, zona, kapasitas, lat, lon FROM tb_tes", conn)
    conn.close()
    
    df_shelter.rename(columns={
        'nama_tes': 'Nama_Bersih',
        'zona': 'Zona',
        'kapasitas': 'Kapasitas_TES',
        'lat': 'Latitude',
        'lon': 'Longitude'
    }, inplace=True)
    
    # Deteksi Sektor dari Kode Zona atau Default
    df_shelter['Sektor'] = 'SEKTOR A'
    sumber_data = "Database SQLite (ranah_siaga.db)"

elif os.path.exists(file_csv):
    print(f"[!] Database SQLite tidak ditemukan. Fallback membaca CSV: '{file_csv}'...")
    df_shelter = pd.read_csv(file_csv)
    if 'Sektor' in df_shelter.columns:
        df_shelter = df_shelter[df_shelter['Sektor'].astype(str).str.upper() != 'JUMLAH']
    sumber_data = f"File CSV ({file_csv})"

else:
    print(f"[ERROR] Tidak dapat menemukan database '{db_path}' maupun file CSV!")
    exit()

def bersihkan_kordinat(nilai):
    if pd.isna(nilai): return None
    teks = str(nilai).strip().replace(',', '.')
    try: return float(teks)
    except: return None

df_shelter['Latitude'] = df_shelter['Latitude'].apply(bersihkan_kordinat)
df_shelter['Longitude'] = df_shelter['Longitude'].apply(bersihkan_kordinat)

# Filter data dengan koordinat valid di Kota Padang
df_valid = df_shelter.dropna(subset=['Latitude', 'Longitude']).copy()
df_valid = df_valid[(df_valid['Latitude'] >= -1.05) & (df_valid['Latitude'] <= -0.80) & (df_valid['Longitude'] >= 100.25) & (df_valid['Longitude'] <= 100.50)]

print(f"[+] Total lokasi TES berkoordinat valid dari DB: {len(df_valid)} bangunan/lokasi.")

# 2. Membuat Kanvas Peta Interaktif
pusat_lat = df_valid['Latitude'].mean()
pusat_lon = df_valid['Longitude'].mean()

peta_tes = folium.Map(
    location=[pusat_lat, pusat_lon],
    zoom_start=13,
    tiles='CartoDB positron'
)

# Palette warna per Sektor
sektor_colors = {
    'SEKTOR A': 'red', 'SEKTOR B': 'blue', 'SEKTOR C': 'green',
    'SEKTOR D': 'purple', 'SEKTOR E': 'orange', 'SEKTOR F': 'darkred',
    'SEKTOR G': 'cadetblue', 'SEKTOR H': 'darkgreen', 'SEKTOR I': 'darkblue'
}

# 3. Marker Clustering Utama
marker_cluster = MarkerCluster(name="Seluruh TES (Cluster)").add_to(peta_tes)

total_bangunan = len(df_valid)
total_kapasitas = 0

for indeks, baris in df_valid.iterrows():
    nama_gedung = str(baris['Nama_Bersih']).strip() if not pd.isna(baris['Nama_Bersih']) else str(baris.get('Lokasi_TES', 'Gedung TES')).strip()
    sektor = str(baris.get('Sektor', 'SEKTOR A')).strip().upper()
    zona = baris.get('Zona', '-')
    
    raw_cap = baris.get('Kapasitas_TES', None)
    if pd.isna(raw_cap) or raw_cap is None:
        kapasitas_str = "Tidak Diketahui"
    else:
        try:
            val_cap = int(round(float(raw_cap)))
            total_kapasitas += val_cap
            kapasitas_str = f"{val_cap:,} Jiwa"
        except (ValueError, TypeError):
            kapasitas_str = f"{raw_cap}"


    lat = baris['Latitude']
    lon = baris['Longitude']
    
    color = sektor_colors.get(sektor, 'blue')
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"

    # Custom HTML Popup Card dengan styling modern
    info_popup = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; width: 240px; padding: 4px;">
        <div style="background: #1e293b; color: white; padding: 8px 12px; border-radius: 6px 6px 0 0; margin: -4px -4px 8px -4px;">
            <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;">{sektor} • {zona}</span>
            <h4 style="margin: 2px 0 0 0; font-size: 14px; font-weight: 700; color: #38bdf8;">{nama_gedung}</h4>
        </div>
        <div style="font-size: 12px; color: #334155; line-height: 1.5;">
            <b>🏢 Kapasitas BPBD:</b> <span style="color: #059669; font-weight: 700;">{kapasitas_str}</span><br>
            <b>📍 Koordinat:</b> {lat:.5f}, {lon:.5f}<br>
            <b>ℹ️ Sumber:</b> <span style="font-size: 11px; color: #64748b;">{sumber_data}</span>
        </div>
        <div style="margin-top: 10px; text-align: center;">
            <a href="{gmaps_url}" target="_blank" style="display: inline-block; background: #2563eb; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: 600;">
                🧭 Rute Google Maps
            </a>
        </div>
    </div>
    """
    
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(info_popup, max_width=320),
        tooltip=f"<b>{nama_gedung}</b> ({zona})",
        icon=folium.Icon(color=color, icon="home")
    ).add_to(marker_cluster)

# 4. Tambahkan Dashboard Control Floating Legend (HTML Overlay)
legend_html = f"""
<div style="
    position: fixed; 
    bottom: 25px; left: 25px; width: 300px;
    background: rgba(15, 23, 42, 0.92);
    backdrop-filter: blur(8px);
    color: white;
    padding: 14px 16px;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    font-family: 'Segoe UI', Arial, sans-serif;
    z-index: 9999;
    border: 1px solid rgba(255,255,255,0.15);
">
    <div style="font-size: 13px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;">
        🏛️ PETA TES KOTA PADANG (SQLITE)
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12px; border-bottom: 1px solid rgba(255,255,255,0.15); padding-bottom: 6px;">
        <span>Sumber Data:</span>
        <strong style="color: #60a5fa;">SQLite (`tb_tes`)</strong>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12px;">
        <span>Total Gedung Evakuasi:</span>
        <strong style="color: #4ade80;">{total_bangunan} Lokasi</strong>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 12px;">
        <span>Total Daya Tampung:</span>
        <strong style="color: #facc15;">{total_kapasitas:,} Jiwa</strong>
    </div>
</div>
"""
peta_tes.get_root().html.add_child(folium.Element(legend_html))

# 5. Simpan dan Buka di Browser
nama_file_peta = "peta_sebaran_tes_padang.html"
peta_tes.save(nama_file_peta)

print(f"[SUKSES] Peta interaktif berbasis SQLite berhasil disimpan ke '{nama_file_peta}'.")
print("Membuka peta di browser web default Anda...")

filepath = "file://" + os.path.realpath(nama_file_peta)
webbrowser.open(filepath)