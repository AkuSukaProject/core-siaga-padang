import geopandas as gpd
import pandas as pd
import folium
import os

print("="*70)
print("GENERATOR PETA GRADASI RISIKO TSUNAMI KOTA PADANG (SEMPURNA & PRESISI)")
print("="*70)

# 1. Memuat Batas Kelurahan GeoJSON
file_geojson = "batas_kelurahan_kota_padang.geojson"
print(f"[1/4] Membaca data batas kelurahan: {file_geojson}...")
gdf_kelurahan = gpd.read_file(file_geojson)
if gdf_kelurahan.crs != "EPSG:4326":
    gdf_kelurahan = gdf_kelurahan.to_crs("EPSG:4326")

kolom_nama = gdf_kelurahan.select_dtypes(include=['object', 'string']).columns[0]
gdf_kelurahan['NAMA_UPPER'] = gdf_kelurahan[kolom_nama].astype(str).str.upper().str.strip()

# Memuat Data Populasi Terpapar BPBD
df_pend = pd.read_csv("penduduk_kota_padang.csv")
kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

df_pend['DESA_MAPPED'] = df_pend['DESA'].astype(str).str.upper().str.strip().apply(lambda x: kelurahan_alias.get(x, x))
pop_dict = dict(zip(df_pend['DESA_MAPPED'], df_pend['JUMLAH JIWA TERPAPAR (JIWA)']))

gdf_kelurahan['JIWA_TERPAPAR'] = gdf_kelurahan['NAMA_UPPER'].map(pop_dict).fillna(0)

# Penyesuaian khusus kelurahan pesisir muara & pantai langsung
gdf_kelurahan.loc[gdf_kelurahan['NAMA_UPPER'] == 'BEROK NIPAH', 'JIWA_TERPAPAR'] = 4500
gdf_kelurahan.loc[gdf_kelurahan['NAMA_UPPER'] == 'PASA GADANG', 'JIWA_TERPAPAR'] = 5200

# Fungsi Penentu Warna Gradasi Risiko Tsunami Spasial
def get_spatial_risk_color(row):
    nama = row['NAMA_UPPER']
    jiwa = row['JIWA_TERPAPAR']
    
    # Khusus Balai Gadang (99.8% wilayahnya dataran tinggi perbukitan aman, hanya 31 jiwa di perbatasan barat)
    if nama == 'BALAI GADANG':
        return '#22c55e', 'Zona Aman (99.8% Dataran Tinggi - Hanya 31 Jiwa Terpapar)'
    
    # Khusus Bukit Gado-Gado & Air Manis (Pesisir Pantai Langsung -> Risiko Spasial Pesisir)
    if nama in ['BUKIT GADO-GADO', 'AIR MANIS']:
        return '#fdbb84', 'Risiko Pesisir (Sensitif Garis Pantai)'
    
    if jiwa > 25000:
        return '#7f0000', '> 25.000 Jiwa Terpapar (Ekstrem)'
    elif jiwa > 15000:
        return '#b30000', '15.000 - 25.000 Jiwa (Sangat Tinggi)'
    elif jiwa > 7000:
        return '#d7301f', '7.000 - 15.000 Jiwa (Tinggi)'
    elif jiwa > 2000:
        return '#ef6548', '2.000 - 7.000 Jiwa (Sedang)'
    elif jiwa > 0:
        return '#fdbb84', '< 2.000 Jiwa (Rendah)'
    else:
        return '#22c55e', 'Zona Aman / Blue Line (Daratan Tinggi Pegunungan)'

results = gdf_kelurahan.apply(get_spatial_risk_color, axis=1)
gdf_kelurahan['WARNA_RISIKO'] = [r[0] for r in results]
gdf_kelurahan['KATEGORI_TEXT'] = [r[1] for r in results]

print("[2/4] Membangun Kanvas Peta Folium Gradasi Risiko Spasial...")
center_lat = -0.92
center_lon = 100.36
peta_risiko = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='CartoDB positron')

# 3. Layer Folium GeoJSON Gradasi
folium.GeoJson(
    gdf_kelurahan,
    name="Gradasi Tingkat Risiko Tsunami (BPBD & Spasial Pesisir)",
    style_function=lambda feature: {
        'fillColor': feature['properties']['WARNA_RISIKO'],
        'color': '#334155',
        'weight': 0.8,
        'fillOpacity': 0.78
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['NAMA_UPPER', 'WADMKC', 'JIWA_TERPAPAR', 'KATEGORI_TEXT'],
        aliases=['Kelurahan:', 'Kecamatan:', 'Jiwa Terpapar:', 'Kategori Risiko:']
    )
).add_to(peta_risiko)

# 4. Floating Legend Overlay Gradasi Warna
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
        🌊 GRADASI RISIKO TSUNAMI (BPBD & SPASIAL)
    </div>
    <div style="font-size: 11px; line-height: 1.8;">
        <div style="display: flex; align-items: center;"><span style="background: #7f0000; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> > 25.000 Jiwa Terpapar (Ekstrem)</div>
        <div style="display: flex; align-items: center;"><span style="background: #b30000; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 15.000 - 25.000 Jiwa (Sangat Tinggi)</div>
        <div style="display: flex; align-items: center;"><span style="background: #d7301f; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 7.000 - 15.000 Jiwa (Tinggi)</div>
        <div style="display: flex; align-items: center;"><span style="background: #ef6548; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> 2.000 - 7.000 Jiwa (Sedang)</div>
        <div style="display: flex; align-items: center;"><span style="background: #fdbb84; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> < 2.000 Jiwa & Risiko Pesisir Langsung</div>
        <div style="display: flex; align-items: center;"><span style="background: #22c55e; width: 14px; height: 14px; display: inline-block; margin-right: 8px; border-radius: 3px;"></span> Zona Aman / Blue Line (Pegunungan Inland)</div>
    </div>
</div>
"""
peta_risiko.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl().add_to(peta_risiko)

output_html = "peta_zona_risiko_dan_pemukiman_padang.html"
peta_risiko.save(output_html)
print(f"[SUKSES] Peta Gradasi Risiko Spasial Pesisir berhasil diperbarui: '{output_html}'")
