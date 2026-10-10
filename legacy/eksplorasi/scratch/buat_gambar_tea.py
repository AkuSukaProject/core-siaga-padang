import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

print("=== MEMBUAT GAMBAR STATIC PETA SEBARAN TEA PADANG ===")

# Read GeoJSON
gdf_padang = gpd.read_file("batas_kelurahan_kota_padang.geojson").to_crs("EPSG:4326")

# Read TEA CSV
df_tea = pd.read_csv("data_tea_padang_lengkap_berkoordinat.csv")
geometry = [Point(xy) for xy in zip(df_tea['lon'], df_tea['lat'])]
gdf_tea = gpd.GeoDataFrame(df_tea, geometry=geometry, crs="EPSG:4326")

# Setup Figure
fig, ax = plt.subplots(figsize=(14, 18), dpi=200)
fig.patch.set_facecolor('#f8f9fa')
ax.set_facecolor('#e9ecef')

# Plot Mainland Kelurahan
gdf_padang.plot(ax=ax, color='#ffffff', edgecolor='#adb5bd', linewidth=0.7, alpha=0.9)

# Color mapping per Sektor
sektor_colors = {
    'SEKTOR A': '#1f77b4', 'SEKTOR B': '#17becf', 'SEKTOR C': '#2ca02c',
    'SEKTOR D': '#ff7f0e', 'SEKTOR E': '#d62728', 'SEKTOR F': '#9467bd',
    'SEKTOR G': '#8c564b', 'SEKTOR H': '#e377c2', 'SEKTOR I': '#336600'
}

# Plot TEA Markers
for idx, row in gdf_tea.iterrows():
    c = sektor_colors.get(row['sektor'], '#333333')
    ax.scatter(row['lon'], row['lat'], color=c, s=160, edgecolor='black', linewidth=1.5, zorder=5)
    
    # Label
    label_text = f"{row['kode']}\n({row['kapasitas']:,} Jiwa)"
    offset_x = 0.006
    offset_y = 0.002
    
    # Adjust collision for close labels
    if row['kode'] == 'TEA D2':
        offset_x = -0.045
    elif row['kode'] == 'TEA E1':
        offset_x = -0.040
    elif row['kode'] == 'TEA A2':
        offset_y = 0.006
    elif row['kode'] == 'TEA B2':
        offset_x = 0.008
        
    ax.annotate(
        label_text,
        xy=(row['lon'], row['lat']),
        xytext=(row['lon'] + offset_x, row['lat'] + offset_y),
        fontsize=9,
        fontweight='bold',
        color='#111111',
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=c, alpha=0.9, lw=1.2),
        zorder=6
    )

# Zoom limits on mainland Padang
ax.set_xlim(100.28, 100.48)
ax.set_ylim(-1.07, -0.78)

ax.set_title("PETA DISTRIBUSI KOORDINAT TEMPAT EVAKUASI AKHIR (TEA) KOTA PADANG\n(Berdasarkan Dokumen Resmi BPBD Kota Padang)", fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel("Longitude (Bujur Timur)", fontsize=10)
ax.set_ylabel("Latitude (Lintang Selatan)", fontsize=10)
ax.grid(True, linestyle='--', alpha=0.4, color='#999999')

output_png = "peta_sebaran_tea_padang.png"
plt.savefig(output_png, bbox_inches='tight', dpi=200)
plt.close()
print(f"Gambar peta TEA berhasil disimpan: '{output_png}'")
