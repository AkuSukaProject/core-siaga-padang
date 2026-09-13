import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import HeatMap
import os

print("="*70)
print("GENERATOR PETA KONSENTRASI KEPADATAN POPULASI KOTA PADANG")
print("="*70)

# 1. Memuat Batas Kelurahan & Data Demografi
file_geojson = "batas_kelurahan_kota_padang.geojson"
print(f"[1/4] Membaca data batas kelurahan: {file_geojson}...")
gdf_kelurahan = gpd.read_file(file_geojson)
if gdf_kelurahan.crs != "EPSG:4326":
    gdf_kelurahan = gdf_kelurahan.to_crs("EPSG:4326")

kolom_nama = gdf_kelurahan.select_dtypes(include=['object', 'string']).columns[0]
gdf_kelurahan['NAMA_UPPER'] = gdf_kelurahan[kolom_nama].astype(str).str.upper().str.strip()

# Hitung Luas Kelurahan dalam km2
gdf_projected = gdf_kelurahan.to_crs("EPSG:32747") # UTM Zone 47S untuk pengukuran luas presisi
gdf_kelurahan['LUAS_KM2'] = gdf_projected.geometry.area / 1e6

# Memuat Data Populasi BPBD
df_pend = pd.read_csv("penduduk_kota_padang.csv")
kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

df_pend['DESA_MAPPED'] = df_pend['DESA'].astype(str).str.upper().str.strip().apply(lambda x: kelurahan_alias.get(x, x))
pop_dict = dict(zip(df_pend['DESA_MAPPED'], df_pend['JUMLAH JIWA TERPAPAR (JIWA)']))

gdf_kelurahan['POPULASI_JIWA'] = gdf_kelurahan['NAMA_UPPER'].map(pop_dict).fillna(0)

# Tambahkan nilai estimasi untuk kelurahan pesisir muara
gdf_kelurahan.loc[gdf_kelurahan['NAMA_UPPER'] == 'BEROK NIPAH', 'POPULASI_JIWA'] = 4500
gdf_kelurahan.loc[gdf_kelurahan['NAMA_UPPER'] == 'PASA GADANG', 'POPULASI_JIWA'] = 5200

# Hitung Kepadatan Penduduk (Jiwa / km2)
gdf_kelurahan['KEPADATAN_KM2'] = (gdf_kelurahan['POPULASI_JIWA'] / gdf_kelurahan['LUAS_KM2']).round(1)

# Warna Gradasi Kepadatan (Biru-Ungu / BuPu Palette)
def get_density_color(density):
    if density > 8000:
        return '#4d004b' # Sangat Padat Ekstrem
    elif density > 5000:
        return '#810f7c' # Sangat Padat
    elif density > 3000:
        return '#88419d' # Padat
    elif density > 1500:
        return '#8c96c6' # Sedang
    elif density > 500:
        return '#9ebcda' # Rendah
    else:
        return '#bfd3e6' # Sangat Rendah

gdf_kelurahan['WARNA_KEPADATAN'] = gdf_kelurahan['KEPADATAN_KM2'].apply(get_density_color)

print("[2/4] Membangun Kanvas Peta Folium Kepadatan Penduduk & Heatmap...")
center_lat = -0.92
center_lon = 100.36
peta_kepadatan = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='CartoDB positron')

# 3. Layer Choropleth Kepadatan Penduduk (Jiwa/km2)
folium.GeoJson(
    gdf_kelurahan,
    name="🏙️ Kepadatan Penduduk (Jiwa/km²)",
    style_function=lambda feature: {
        'fillColor': feature['properties']['WARNA_KEPADATAN'],
        'color': '#1e293b',
        'weight': 1.0,
        'fillOpacity': 0.7
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['NAMA_UPPER', 'WADMKC', 'POPULASI_JIWA', 'LUAS_KM2', 'KEPADATAN_KM2'],
        aliases=['Kelurahan:', 'Kecamatan:', 'Populasi (Jiwa):', 'Luas (km²):', 'Kepadatan (Jiwa/km²):']
    )
).add_to(peta_kepadatan)

# 4. Heatmap Layer Konsentrasi Titik Populasi (Hotspots)
heatmap_data = []
for idx, row in gdf_kelurahan.iterrows():
    pop = row['POPULASI_JIWA']
    if pop > 0:
        centroid = row.geometry.centroid
        weight = float(pop)
        heatmap_data.append([centroid.y, centroid.x, weight])

HeatMap(
    heatmap_data,
    name="🔥 Heatmap Konsentrasi Titik Populasi",
    radius=25,
    blur=18,
    max_zoom=13
).add_to(peta_kepadatan)

# 5. Floating Legend Overlay Kepadatan Penduduk
legend_html = """
<div style="
    position: fixed; 
    bottom: 25px; left: 25px; width: 320px;
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
    <div style="font-size: 13px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;">
        🏙️ KEPADATAN POPULASI KOTA PADANG
    </div>
    <div style="font-size: 11px; line-height: 1.8;">
        <div style="display: flex; align-items: center;"><span style="background: #4d004b; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> > 8.000 Jiwa / km² (Padat Ekstrem)</div>
        <div style="display: flex; align-items: center;"><span style="background: #810f7c; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 5.000 - 8.000 Jiwa / km² (Sangat Padat)</div>
        <div style="display: flex; align-items: center;"><span style="background: #88419d; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 3.000 - 5.000 Jiwa / km² (Padat)</div>
        <div style="display: flex; align-items: center;"><span style="background: #8c96c6; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 1.500 - 3.000 Jiwa / km² (Sedang)</div>
        <div style="display: flex; align-items: center;"><span style="background: #9ebcda; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 500 - 1.500 Jiwa / km² (Rendah)</div>
        <div style="display: flex; align-items: center;"><span style="background: #bfd3e6; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> < 500 Jiwa / km² (Sangat Jarang)</div>
    </div>
</div>
"""
peta_kepadatan.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl(collapsed=False).add_to(peta_kepadatan)

output_html = "peta_kepadatan_penduduk_padang.html"
peta_kepadatan.save(output_html)
print(f"[SUKSES] Peta Kepadatan Penduduk & Heatmap berhasil disimpan: '{output_html}'")
