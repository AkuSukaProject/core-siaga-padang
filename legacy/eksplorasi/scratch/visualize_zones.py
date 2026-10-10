"""
Buat peta HTML interaktif untuk memvalidasi pewarnaan zona secara visual.
Ini akan menunjukkan zona mana yang salah warnanya.
"""
import geopandas as gpd
import pandas as pd
import json

gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

df_pop = pd.read_csv("penduduk_kota_padang.csv")
kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH',
    'BATANG KABUNG': 'BATANG KABUNG GANTING',
    'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA',
    'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI',
    'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR',
    'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX',
    'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR',
    'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

exposed_map = dict(zip(
    df_pop['DESA'].astype(str).str.upper().str.strip().apply(lambda x: kelurahan_alias.get(x, x)),
    df_pop['JUMLAH JIWA TERPAPAR (JIWA)']
))
exposed_map['BEROK NIPAH'] = 20000
exposed_map['PASA GADANG'] = 20000

def get_current_color(nama_kel):
    """Warna SAAT INI (dari core.py is_kelurahan_safe)"""
    if nama_kel == 'BALAI GADANG':
        return 'green'
    terpapar = exposed_map.get(nama_kel, 0)
    if terpapar == 0:
        return 'green'
    elif terpapar > 15000:
        return 'red'
    elif terpapar > 5000:
        return 'orange'
    else:
        return 'yellow'

# Build GeoJSON with colors
features = []
for idx, row in gdf.iterrows():
    name = row['NAMA_UPPER']
    color = get_current_color(name)
    terpapar = exposed_map.get(name, 0)
    
    geom = row['geometry'].__geo_interface__
    
    features.append({
        "type": "Feature",
        "geometry": geom,
        "properties": {
            "nama": name,
            "color": color,
            "terpapar": terpapar
        }
    })

geojson_data = json.dumps({"type": "FeatureCollection", "features": features})

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Validasi Zona Padang</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
body {{ margin: 0; }}
#map {{ width: 100%; height: 100vh; }}
.info {{ padding: 8px; background: white; border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2); }}
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map('map').setView([-0.95, 100.38], 12);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

var data = {geojson_data};

L.geoJSON(data, {{
    style: function(feature) {{
        var c = feature.properties.color;
        var fillColor = c === 'red' ? '#e74c3c' : c === 'orange' ? '#f39c12' : c === 'yellow' ? '#f1c40f' : '#2ecc71';
        return {{
            fillColor: fillColor,
            weight: 2,
            opacity: 1,
            color: fillColor === '#2ecc71' ? '#27ae60' : '#c0392b',
            fillOpacity: 0.4
        }};
    }},
    onEachFeature: function(feature, layer) {{
        layer.bindPopup('<b>' + feature.properties.nama + '</b><br>Terpapar: ' + feature.properties.terpapar + '<br>Zona: ' + feature.properties.color);
    }}
}}).addTo(map);
</script>
</body>
</html>"""

with open("validasi_zona_padang.html", "w") as f:
    f.write(html)
print("File saved: validasi_zona_padang.html")
