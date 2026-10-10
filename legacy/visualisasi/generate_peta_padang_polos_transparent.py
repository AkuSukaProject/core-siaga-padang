import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import geopandas as gpd

print("=" * 80)
print("GENERATOR PETA KOTA PADANG POLOS (SELARAS & UNIFORM, TRANSPARENT BACKGROUND)")
print("========================================================================")

# 1. Memuat Data Geometri Wilayah Kota Padang
file_kota = "batas_kelurahan_kota_padang.geojson"

print(f"[1/3] Membaca GeoJSON batas kelurahan Kota Padang...")
gdf_kota = gpd.read_file(file_kota)
if gdf_kota.crs != "EPSG:4326":
    gdf_kota = gdf_kota.to_crs("EPSG:4326")

print(f"      Total Kelurahan Ditemukan: {len(gdf_kota)} kelurahan")

# Bounding Box Seluruh Kota Padang
min_lon, min_lat, max_lon, max_lat = gdf_kota.total_bounds
lon_margin = (max_lon - min_lon) * 0.02
lat_margin = (max_lat - min_lat) * 0.02

# 2. Merender Peta Varian 1: Outline Garis Putih Murni Selaras (White Lines Uniform)
print("[2/3] Merender Gambar Peta Outline Garis Putih Selaras (300 DPI, Transparent)...")

fig1, ax1 = plt.subplots(figsize=(12, 14), dpi=300)
fig1.patch.set_alpha(0.0)
ax1.patch.set_alpha(0.0)

# Render seluruh kelurahan dengan garis putih murni yang 100% selaras
gdf_kota.boundary.plot(
    ax=ax1, 
    color='#ffffff', 
    linewidth=1.0, 
    alpha=0.95
)

ax1.axis('off')
ax1.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax1.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

output_white_outline_png = r"c:\gemastik\peta_padang_white_outline_transparent.png"
plt.savefig(
    output_white_outline_png, 
    transparent=True, 
    dpi=300, 
    bbox_inches='tight', 
    pad_inches=0.05
)
plt.close()

# 3. Merender Peta Varian 2: Outline Garis Biru Murni Selaras (Blue Lines Uniform)
fig2, ax2 = plt.subplots(figsize=(12, 14), dpi=300)
fig2.patch.set_alpha(0.0)
ax2.patch.set_alpha(0.0)

gdf_kota.boundary.plot(
    ax=ax2, 
    color='#0284c7', 
    linewidth=1.0, 
    alpha=0.95
)

ax2.axis('off')
ax2.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax2.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

output_outline_png = r"c:\gemastik\peta_padang_outline_transparent.png"
plt.savefig(
    output_outline_png, 
    transparent=True, 
    dpi=300, 
    bbox_inches='tight', 
    pad_inches=0.05
)
plt.close()

# 4. Merender Peta Varian 3: Polos Isian Warna Soft Blue Selaras (Filled Uniform)
fig3, ax3 = plt.subplots(figsize=(12, 14), dpi=300)
fig3.patch.set_alpha(0.0)
ax3.patch.set_alpha(0.0)

gdf_kota.plot(
    ax=ax3, 
    facecolor='#38bdf8', 
    edgecolor='#0284c7', 
    linewidth=0.8, 
    alpha=0.35
)

ax3.axis('off')
ax3.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
ax3.set_ylim(min_lat - lat_margin, max_lat + lat_margin)

output_filled_png = r"c:\gemastik\peta_padang_polos_transparent.png"
plt.savefig(
    output_filled_png, 
    transparent=True, 
    dpi=300, 
    bbox_inches='tight', 
    pad_inches=0.05
)
plt.close()

print(f"[3/3] [SUKSES] Seluruh varian gambar peta polos selaras telah disimpan:")
print(f"      1. Outline Putih Selaras   : '{output_white_outline_png}'")
print(f"      2. Outline Biru Selaras    : '{output_outline_png}'")
print(f"      3. Polos Isian Warna Selaras: '{output_filled_png}'")
print("=" * 80)
