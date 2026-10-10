import geopandas as gpd
import pandas as pd
import folium
import os

print("="*70)
print("GENERATOR PETA KEPADATAN PENDUDUK KOTA PADANG PER KECAMATAN (BPS)")
print("="*70)

# 1. Memuat GeoJSON Batas Kelurahan/Kecamatan
file_geojson = "batas_kelurahan_kota_padang.geojson"
print(f"[1/4] Membaca GeoJSON: {file_geojson}...")
gdf_kelurahan = gpd.read_file(file_geojson)
if gdf_kelurahan.crs != "EPSG:4326":
    gdf_kelurahan = gdf_kelurahan.to_crs("EPSG:4326")

gdf_kelurahan['WADMKC_UPPER'] = gdf_kelurahan['WADMKC'].astype(str).str.upper().str.strip()

# 2. Memuat Data CSV BPS Kepadatan Per Kecamatan
file_csv = "kepadatan_penduduk_padang_perkecamatan.csv"
print(f"[2/4] Membaca CSV BPS Kepadatan per Kecamatan: {file_csv}...")
df_bps = pd.read_csv(file_csv)

# Hapus baris total 'Padang' paling bawah jika ada
df_bps = df_bps[df_bps['Kecamatan'].astype(str).str.upper() != 'PADANG'].copy()
df_bps['KEC_UPPER'] = df_bps['Kecamatan'].astype(str).str.upper().str.strip()

# Map data BPS ke GeoJSON berdasarkan WADMKC (Nama Kecamatan)
dict_pop_ribu = dict(zip(df_bps['KEC_UPPER'], df_bps['Jumlah Penduduk (Ribu)']))
dict_kepadatan = dict(zip(df_bps['KEC_UPPER'], df_bps['Kepadatan Penduduk per km persegi (Km2)']))
dict_persen = dict(zip(df_bps['KEC_UPPER'], df_bps['Persentase Penduduk']))

gdf_kelurahan['POPULASI_RIBU'] = gdf_kelurahan['WADMKC_UPPER'].map(dict_pop_ribu).fillna(0)
gdf_kelurahan['KEPADATAN_BPS'] = gdf_kelurahan['WADMKC_UPPER'].map(dict_kepadatan).fillna(0)
gdf_kelurahan['PERSEN_POP'] = gdf_kelurahan['WADMKC_UPPER'].map(dict_persen).fillna(0)

# Pembersihan Nilai Kepadatan BPS (Satuan Ribu vs Jiwa murni)
# Jika nilai kepadatan < 100 (misal 10 untuk Padang Timur), dikalikan 1000 agar jadi Jiwa/km2 (10.000)
def fix_density_bps(val):
    if val < 50 and val > 0:
        return val * 1000
    return val

gdf_kelurahan['KEPADATAN_JIWA_KM2'] = gdf_kelurahan['KEPADATAN_BPS'].apply(fix_density_bps)

# Gradasi Warna Kepadatan BPS per Kecamatan (Biru - Ungu / BuPu)
def get_kecamatan_density_color(density):
    if density >= 8000:
        return '#4d004b' # Ungu Gelap / Indigo (Sangat Padat Ekstrem: Padang Timur ~10.000/km2)
    elif density >= 6000:
        return '#810f7c' # Ungu Pekat (Padat Tinggi: Padang Barat, Padang Utara, Padang Selatan ~6.000-7.000/km2)
    elif density >= 3000:
        return '#88419d' # Ungu Medium (Padat: Lubuk Begalung, Kuranji ~3.000-4.000/km2)
    elif density >= 800:
        return '#8c96c6' # Biru-Ungu Sedang (Sedang: Koto Tangah, Lubuk Kilangan ~700-900/km2)
    elif density >= 200:
        return '#bfd3e6' # Biru Muda / Lavender (Rendah: Bungus Teluk Kabung, Pauh ~300-400/km2)
    else:
        return '#edf8fb' # Cyan/Biru Sangat Muda

gdf_kelurahan['WARNA_KEC'] = gdf_kelurahan['KEPADATAN_JIWA_KM2'].apply(get_kecamatan_density_color)

print("[3/4] Membangun Peta Choropleth Kepadatan Penduduk per Kecamatan...")
center_lat = -0.92
center_lon = 100.36
peta_kec = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles='CartoDB positron')

folium.GeoJson(
    gdf_kelurahan,
    name="🏙️ Kepadatan Penduduk BPS per Kecamatan",
    style_function=lambda feature: {
        'fillColor': feature['properties']['WARNA_KEC'],
        'color': '#0f172a',
        'weight': 1.2,
        'fillOpacity': 0.75
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['WADMKC', 'NAMOBJ', 'POPULASI_RIBU', 'KEPADATAN_JIWA_KM2', 'PERSEN_POP'],
        aliases=['Kecamatan:', 'Kelurahan:', 'Total Penduduk Kec (Ribu):', 'Kepadatan (Jiwa/km²):', 'Proporsi Penduduk Kota (%):']
    )
).add_to(peta_kec)

# Overlay Floating Legend
legend_html = """
<div style="
    position: fixed; 
    bottom: 25px; left: 25px; width: 330px;
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
        🏙️ KEPADATAN BPS PER KECAMATAN
    </div>
    <div style="font-size: 11px; line-height: 1.8;">
        <div style="display: flex; align-items: center;"><span style="background: #4d004b; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> ≥ 8.000 Jiwa / km² (Padang Timur)</div>
        <div style="display: flex; align-items: center;"><span style="background: #810f7c; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 6.000 - 8.000 Jiwa / km² (Padang Barat, Utara, Selatan)</div>
        <div style="display: flex; align-items: center;"><span style="background: #88419d; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 3.000 - 6.000 Jiwa / km² (Lubuk Begalung, Kuranji, Nanggalo)</div>
        <div style="display: flex; align-items: center;"><span style="background: #8c96c6; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 700 - 3.000 Jiwa / km² (Koto Tangah, Lubuk Kilangan)</div>
        <div style="display: flex; align-items: center;"><span style="background: #bfd3e6; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> < 700 Jiwa / km² (Bungus Teluk Kabung, Pauh)</div>
    </div>
</div>
"""
peta_kec.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl().add_to(peta_kec)

output_html = "peta_kepadatan_perkecamatan_padang.html"
peta_kec.save(output_html)
print(f"[SUKSES] Peta Kepadatan per Kecamatan BPS berhasil disimpan: '{output_html}'")
