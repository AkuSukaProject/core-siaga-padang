import osmnx as ox
import pandas as pd

# Let's geocode specific landmark POIs in Padang using osmnx or requests
queries = [
    ("TEA D1", "Kantor Walikota Padang, Aie Pacah, Padang"),
    ("TEA D2", "TVRI Sumatera Barat, Padang"),
    ("TEA E1", "Gunung Pangilun, Padang"),
    ("TEA A2", "Bukit Anak Air, Padang"),
    ("TEA B2", "Sungai Bangek, Padang"),
    ("TEA A1", "Batipuh Panjang, Padang"),
    ("TEA B1", "Koto Pulai, Padang"),
    ("TEA C1", "Koto Panjang Ikua Koto, Padang"),
    ("TEA F1", "Sungai Sapih, Padang"),
    ("TEA G1", "Kubu Marapalam, Padang"),
    ("TEA H1", "Teluk Kabung Utara, Padang"),
    ("TEA I1", "Banuaran Nan XX, Padang")
]

results = []
for code, q in queries:
    try:
        gdf = ox.geocoder.geocode_to_gdf(q)
        lat = gdf.geometry.centroid.iloc[0].y
        lon = gdf.geometry.centroid.iloc[0].x
        results.append((code, q, lat, lon, "OSM Geocoded"))
    except Exception as e:
        results.append((code, q, None, None, str(e)))

for r in results:
    print(r)
