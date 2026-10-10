import folium
import geopandas as gpd
import pandas as pd
import json

print("=== MEMBUAT PETA INTERAKTIF TEA KOTA PADANG ===")

tea_data = [
    {
        "kode": "TEA A1",
        "sektor": "SEKTOR A",
        "nama": "Lahan Kosong Batipuh Panjang (Rekomendasi)",
        "kelurahan": "Batipuh Panjang",
        "kecamatan": "Koto Tangah",
        "kapasitas": 22919,
        "lat": -0.82285,
        "lon": 100.33633,
        "tipe": "Lahan Terbuka Aman",
        "jalur": "Jl. Adinegoro -> Perum. Pondok Citra -> Jl. By Pass -> TEA A1",
        "warna": "blue"
    },
    {
        "kode": "TEA A2",
        "sektor": "SEKTOR A",
        "nama": "BUKIT ANAK AIA (Kawasan Perbukitan Alami)",
        "kelurahan": "Batipuh Panjang",
        "kecamatan": "Koto Tangah",
        "kapasitas": 21857,
        "lat": -0.81432,
        "lon": 100.33415,
        "tipe": "Perbukitan Alami",
        "jalur": "Jl. Adinegoro -> Jl. Bukito Taruna SMAN 7 -> Jl. By Pass -> Bukit Anak Air",
        "warna": "blue"
    },
    {
        "kode": "TEA B1",
        "sektor": "SEKTOR B",
        "nama": "Lahan Kosong Koto Pulai (Rekomendasi)",
        "kelurahan": "Koto Pulai",
        "kecamatan": "Koto Tangah",
        "kapasitas": 21233,
        "lat": -0.84522,
        "lon": 100.34904,
        "tipe": "Lahan Terbuka Aman",
        "jalur": "Jl. Pasir Sebelah -> Jl. Adinegoro -> Jl. Kelurahan Koto Pulai -> TEA B1",
        "warna": "lightblue"
    },
    {
        "kode": "TEA B2",
        "sektor": "SEKTOR B",
        "nama": "Lahan Sungai Bangek, Balai Gadang (Rekomendasi)",
        "kelurahan": "Balai Gadang",
        "kecamatan": "Koto Tangah",
        "kapasitas": 6603,
        "lat": -0.79650,
        "lon": 100.39200,
        "tipe": "Lahan Terbuka & Perbukitan",
        "jalur": "Jl. Adinegoro -> Jl. Kampung Jambak -> Jl. By Pass -> Jl. Sungai Bangek -> TEA B2",
        "warna": "lightblue"
    },
    {
        "kode": "TEA C1",
        "sektor": "SEKTOR C",
        "nama": "Lahan Kosong Koto Panjang Ikua Koto",
        "kelurahan": "Koto Panjang Ikua Koto",
        "kecamatan": "Koto Tangah",
        "kapasitas": 12614,
        "lat": -0.85447,
        "lon": 100.36709,
        "tipe": "Lahan Terbuka Aman",
        "jalur": "Jl. Gn. Merapi -> Jl. Adinegoro -> Jl. Kelurahan Bungo Pasang -> Ikua Koto -> TEA C1",
        "warna": "green"
    },
    {
        "kode": "TEA D1",
        "sektor": "SEKTOR D",
        "nama": "Areal Kantor Balai Kota Padang (By Pass Aie Pacah)",
        "kelurahan": "Aie Pacah",
        "kecamatan": "Koto Tangah",
        "kapasitas": 18801,
        "lat": -0.86877,
        "lon": 100.38421,
        "tipe": "Kompleks Perkantoran Pemerintah",
        "jalur": "Jl. Diklat / Jl. Maransi -> Simp. Air Pacah -> Kompleks Balai Kota By Pass -> TEA D1",
        "warna": "orange"
    },
    {
        "kode": "TEA D2",
        "sektor": "SEKTOR D",
        "nama": "Areal Kantor TVRI Sumatera Barat (By Pass)",
        "kelurahan": "Dadok Tunggul Hitam / Kuranji",
        "kecamatan": "Koto Tangah / Nanggalo",
        "kapasitas": 56398,
        "lat": -0.86553,
        "lon": 100.37616,
        "tipe": "Kompleks Perkantoran Luas",
        "jalur": "Jl. Prof. Dr. Hamka -> Jl. Tunggul Hitam -> Dadok Tunggul Hitam -> Jl. By Pass TVRI -> TEA D2",
        "warna": "orange"
    },
    {
        "kode": "TEA E1",
        "sektor": "SEKTOR E",
        "nama": "GUNUNG PANGILUN (Kawasan Perbukitan Alami)",
        "kelurahan": "Gunung Pangilun",
        "kecamatan": "Padang Utara",
        "kapasitas": 80684,
        "lat": -0.91245,
        "lon": 100.36420,
        "tipe": "Perbukitan Alami (Bukit Bebas Banjir)",
        "jalur": "Jl. Raden Saleh / Jl. Kyai Ahmad Dahlan -> Jl. Gajah Mada -> Gn. Pangilun -> TEA E1",
        "warna": "red"
    },
    {
        "kode": "TEA F1",
        "sektor": "SEKTOR F",
        "nama": "Lahan Kosong Kelurahan Sungai Sapih",
        "kelurahan": "Sungai Sapih",
        "kecamatan": "Kuranji",
        "kapasitas": 32625,
        "lat": -0.88924,
        "lon": 100.39185,
        "tipe": "Lahan Terbuka Aman",
        "jalur": "Jl. Gurun Lawas -> Jl. Kampung Marapak -> Jl. Balai Baru -> Jl. Sungai Sapih -> TEA F1",
        "warna": "purple"
    },
    {
        "kode": "TEA G1",
        "sektor": "SEKTOR G",
        "nama": "Lahan Kosong Kelurahan Kubu Marapalam",
        "kelurahan": "Kubu Marapalam",
        "kecamatan": "Padang Timur",
        "kapasitas": 106327,
        "lat": -0.95178,
        "lon": 100.38676,
        "tipe": "Lahan Terbuka Luas (Kapasitas Terbesar)",
        "jalur": "Jl. Thamrin -> Jl. Parak Pisang -> Jl. Sisingamangaraja -> Jl. Dr. Sutomo -> TEA G1",
        "warna": "darkred"
    },
    {
        "kode": "TEA H1",
        "sektor": "SEKTOR H",
        "nama": "Lahan Kosong Kelurahan Teluk Kabung Utara",
        "kelurahan": "Teluk Kabung Utara",
        "kecamatan": "Bungus Teluk Kabung",
        "kapasitas": 16411,
        "lat": -1.04150,
        "lon": 100.41850,
        "tipe": "Lahan Terbuka & Ketinggian Pesisir",
        "jalur": "Jl. Teluk Kabung -> Jl. Raya Padang - Painan -> Lereng Perbukitan -> TEA H1",
        "warna": "cadetblue"
    },
    {
        "kode": "TEA I1",
        "sektor": "SEKTOR I",
        "nama": "Lahan Kosong Kelurahan Banuaran Nan XX",
        "kelurahan": "Banuaran Nan XX",
        "kecamatan": "Lubuk Begalung",
        "kapasitas": 41389,
        "lat": -0.96861,
        "lon": 100.38816,
        "tipe": "Lahan Terbuka Aman",
        "jalur": "Jl. Gates Nan XX / Jl. Tanjung Priok -> Jl. By Pass Banuaran -> TEA I1",
        "warna": "darkgreen"
    }
]

# Simpan ke CSV data TEA resmi
df_tea = pd.DataFrame(tea_data)
df_tea.to_csv("data_tea_padang_lengkap_berkoordinat.csv", index=False)
print("Berhasil menyimpan 'data_tea_padang_lengkap_berkoordinat.csv'")

# Buat Peta Folium
m = folium.Map(location=[-0.9000, 100.3800], zoom_start=11, tiles="CartoDB positron")

# Load Batas Kelurahan
try:
    gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
    folium.GeoJson(
        gdf_kel,
        name="Batas Kelurahan Kota Padang",
        style_function=lambda x: {
            "fillColor": "#3388ff",
            "color": "#666666",
            "weight": 1,
            "fillOpacity": 0.05
        },
        tooltip=folium.GeoJsonTooltip(fields=["NAMOBJ"], aliases=["Kelurahan:"])
    ).add_to(m)
    print("Layer batas kelurahan berhasil ditambahkan.")
except Exception as e:
    print("Error loading kelurahan GeoJSON:", e)

# Tambahkan Marker TEA
for t in tea_data:
    popup_html = f"""
    <div style="font-family: Arial, sans-serif; width: 280px; font-size: 13px;">
        <div style="background-color: #d9534f; color: white; padding: 6px 10px; border-radius: 4px; font-weight: bold;">
            🚩 {t['kode']} - {t['sektor']}
        </div>
        <div style="margin-top: 8px;">
            <p style="margin: 4px 0;"><b>Lokasi:</b> {t['nama']}</p>
            <p style="margin: 4px 0;"><b>Kelurahan / Kec:</b> {t['kelurahan']}, {t['kecamatan']}</p>
            <p style="margin: 4px 0;"><b>Karakteristik:</b> <span style="background:#eee; padding:2px 6px; border-radius:3px;">{t['tipe']}</span></p>
            <p style="margin: 4px 0;"><b>Kapasitas Daya Tampung:</b> <span style="color:#d9534f; font-weight:bold;">{t['kapasitas']:,} Jiwa</span></p>
            <p style="margin: 4px 0;"><b>Koordinat:</b> {t['lat']:.5f}, {t['lon']:.5f}</p>
            <p style="margin: 4px 0; font-size: 11px; color: #555;"><b>Rute Akses:</b> {t['jalur']}</p>
        </div>
    </div>
    """
    
    # Icon khusus untuk perbukitan vs lahan terbuka
    icon_name = "mountain" if "Perbukitan" in t['tipe'] else "flag"
    
    folium.Marker(
        location=[t['lat'], t['lon']],
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=f"<b>{t['kode']}</b>: {t['nama']} ({t['kapasitas']:,} Jiwa)",
        icon=folium.Icon(color=t['warna'], icon="info-sign")
    ).add_to(m)

    # Tambahkan lingkaran radius aman di sekitar TEA
    folium.Circle(
        location=[t['lat'], t['lon']],
        radius=500,
        color=t['warna'],
        weight=1,
        fill=True,
        fill_opacity=0.15
    ).add_to(m)

folium.LayerControl().add_to(m)
html_file = "peta_sebaran_tea_padang.html"
m.save(html_file)
print(f"Peta Interaktif TEA tersimpan: '{html_file}'")
