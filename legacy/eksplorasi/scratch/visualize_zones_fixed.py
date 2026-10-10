"""
Regenerate validation map setelah fix untuk memverifikasi pewarnaan zona.
"""
import geopandas as gpd
import pandas as pd
import json
import sqlite3

# Read zone data from FIXED database
conn = sqlite3.connect("ranah_siaga_v2.db")
df_inund = pd.read_sql_query("SELECT nama_zona, tingkat_bahaya FROM tb_inundation_zones", conn)
df_safe = pd.read_sql_query("SELECT nama_zona FROM tb_safe_zones", conn)
conn.close()

inund_map = dict(zip(df_inund['nama_zona'], df_inund['tingkat_bahaya']))
safe_set = set(df_safe['nama_zona'])

# Load GeoJSON
gdf = gpd.read_file("batas_kelurahan_kota_padang.geojson")
kolom_nama = gdf.select_dtypes(include=['object', 'string']).columns[0]
gdf['NAMA_UPPER'] = gdf[kolom_nama].astype(str).str.upper().str.strip()

# Build GeoJSON with correct colors from DB
features = []
for idx, row in gdf.iterrows():
    name = row['NAMA_UPPER']
    geom = row['geometry'].__geo_interface__
    
    if name in safe_set:
        color = 'green'
        bahaya = 'Aman'
    elif name in inund_map:
        bahaya = inund_map[name]
        color = 'red' if bahaya == 'Tinggi' else ('orange' if bahaya == 'Sedang' else 'yellow')
    else:
        color = 'gray'
        bahaya = 'Tidak diketahui'
    
    features.append({
        "type": "Feature",
        "geometry": geom,
        "properties": {
            "nama": name,
            "color": color,
            "bahaya": bahaya
        }
    })

geojson_data = json.dumps({"type": "FeatureCollection", "features": features})

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Validasi Zona Padang (SETELAH FIX)</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
body {{ margin: 0; }}
#map {{ width: 100%; height: 100vh; }}
.legend {{ background: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2); line-height: 2; }}
.legend i {{ width: 18px; height: 18px; display: inline-block; margin-right: 5px; opacity: 0.7; }}
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map('map').setView([-0.95, 100.38], 12);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

var data = {geojson_data};

var colorMap = {{
    'red': '#e74c3c',
    'orange': '#f39c12', 
    'yellow': '#f1c40f',
    'green': '#2ecc71',
    'gray': '#95a5a6'
}};

var borderMap = {{
    'red': '#c0392b',
    'orange': '#e67e22',
    'yellow': '#f39c12',
    'green': '#27ae60',
    'gray': '#7f8c8d'
}};

L.geoJSON(data, {{
    style: function(feature) {{
        var c = feature.properties.color;
        return {{
            fillColor: colorMap[c],
            weight: 2,
            opacity: 1,
            color: borderMap[c],
            fillOpacity: 0.4
        }};
    }},
    onEachFeature: function(feature, layer) {{
        layer.bindPopup('<b>' + feature.properties.nama + '</b><br>Status: ' + feature.properties.bahaya + '<br>Warna: ' + feature.properties.color);
    }}
}}).addTo(map);

// Legend
var legend = L.control({{position: 'bottomright'}});
legend.onAdd = function(map) {{
    var div = L.DomUtil.create('div', 'legend');
    div.innerHTML = '<b>Zona Tsunami Padang</b><br>' +
        '<i style="background:#e74c3c"></i> Risiko Tinggi<br>' +
        '<i style="background:#f39c12"></i> Risiko Sedang<br>' +
        '<i style="background:#f1c40f"></i> Risiko Rendah<br>' +
        '<i style="background:#2ecc71"></i> Zona Aman (Hijau)<br>';
    return div;
}};
legend.addTo(map);
</script>
</body>
</html>"""

with open("validasi_zona_padang_fixed.html", "w") as f:
    f.write(html)
print("File saved: validasi_zona_padang_fixed.html")
print(f"\nRingkasan:")
print(f"  Zona Risiko (inundation): {len(inund_map)} kelurahan")
print(f"  Zona Aman (safe):         {len(safe_set)} kelurahan")
print(f"  Total:                     {len(inund_map) + len(safe_set)} kelurahan")
