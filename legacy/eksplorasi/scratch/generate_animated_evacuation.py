import sqlite3
import pandas as pd
import folium
from folium import plugins
import math
import random

print("=" * 70)
print("MEMBUAT ANIMASI VISUALISASI EVAKUASI PREMIUM")
print("=" * 70)

WALKING_SPEED_MPS = 1.2

def get_node_coords(conn):
    cur = conn.cursor()
    cur.execute("SELECT node_id, lat, lon FROM tb_nodes")
    return {row[0]: (row[1], row[2]) for row in cur.fetchall()}

def get_tes_info(conn):
    cur = conn.cursor()
    cur.execute("SELECT nama_tes, lat, lon, kapasitas FROM tb_tes")
    return {row[0]: (row[1], row[2], row[3]) for row in cur.fetchall()}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def create_premium_map(db_path, output_file, num_agents=150):
    conn = sqlite3.connect(db_path)
    nodes = get_node_coords(conn)
    tes_dict = get_tes_info(conn)
    
    cur = conn.cursor()
    
    # Ambil 150 rute secara acak
    cur.execute('''
        SELECT r.origin_node_id, r.rank_1_tes, r.rank_1_path, r.rank_1_eta
        FROM tb_routes r
        JOIN tb_nodes n ON r.origin_node_id = n.node_id
        WHERE n.is_safe = 0 AND r.rank_1_path IS NOT NULL
        ORDER BY RANDOM() LIMIT ?
    ''', (num_agents,))
    
    agent_routes = cur.fetchall()
    
    # 1. Inisialisasi Peta - Menggunakan ESRI Dark Gray yang sangat elegan dan gratis (tanpa API key)
    m = folium.Map(
        location=[-0.93, 100.38], 
        zoom_start=13,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        attr='Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS User Community'
    )
    
    # 2. Tambahkan Polygon Zona (Background)
    # Zona Rendaman (Merah)
    import geopandas as gpd
    from shapely import wkt
    import json
    
    try:
        cur.execute("SELECT nama_zona, tingkat_bahaya, geometry_wkt FROM tb_inundation_zones")
        inundation_features = []
        for nama, bahaya, geom_str in cur.fetchall():
            geom = wkt.loads(geom_str)
            color = '#e74c3c' if bahaya == 'Tinggi' else ('#e67e22' if bahaya == 'Sedang' else '#f1c40f')
            inundation_features.append({
                "type": "Feature",
                "geometry": geom.__geo_interface__,
                "properties": {"nama": nama, "bahaya": bahaya, "color": color}
            })
            
        folium.GeoJson(
            {"type": "FeatureCollection", "features": inundation_features},
            name="Zona Rawan Tsunami",
            style_function=lambda x: {
                'fillColor': x['properties']['color'],
                'color': x['properties']['color'],
                'weight': 1,
                'fillOpacity': 0.15,
                'opacity': 0.4
            },
            tooltip=folium.GeoJsonTooltip(fields=['nama', 'bahaya'], aliases=['Kelurahan:', 'Risiko:'])
        ).add_to(m)
        
        # Zona Aman (Hijau)
        cur.execute("SELECT nama_zona, geometry_wkt FROM tb_safe_zones")
        safe_features = []
        for nama, geom_str in cur.fetchall():
            geom = wkt.loads(geom_str)
            safe_features.append({
                "type": "Feature",
                "geometry": geom.__geo_interface__,
                "properties": {"nama": nama}
            })
            
        folium.GeoJson(
            {"type": "FeatureCollection", "features": safe_features},
            name="Zona Aman Perbukitan",
            style_function=lambda x: {
                'fillColor': '#2ecc71',
                'color': '#27ae60',
                'weight': 1,
                'fillOpacity': 0.15,
                'opacity': 0.4
            },
            tooltip=folium.GeoJsonTooltip(fields=['nama'], aliases=['Kawasan Aman:'])
        ).add_to(m)
    except Exception as e:
        print(f"Gagal memuat poligon zona: {e}")

    # 3. Kumpulkan Data Jalur dan Agen
    features = []
    base_time_pd = pd.to_datetime("2026-10-01T10:00:00")
    used_tes = set()
    
    # Layer Group untuk Jalur Statis
    fg_routes = folium.FeatureGroup(name="Lintasan Evakuasi Aktif", show=True)

    for idx, (origin_id, tes_name, path_str, eta) in enumerate(agent_routes):
        node_ids = [int(x) for x in path_str.split(',') if x.strip()]
        if len(node_ids) < 2: continue
            
        used_tes.add(tes_name)
        coords = []
        times = []
        static_line_coords = []
        current_time = base_time_pd
        
        for i in range(len(node_ids)):
            nid = node_ids[i]
            if nid not in nodes: continue
            lat, lon = nodes[nid]
            static_line_coords.append([lat, lon])
            
            if i == 0:
                coords.append([lon, lat])
                times.append(current_time.strftime("%Y-%m-%dT%H:%M:%S"))
            else:
                prev_lat, prev_lon = nodes[node_ids[i-1]]
                dist_m = haversine(prev_lat, prev_lon, lat, lon)
                time_taken_sec = dist_m / WALKING_SPEED_MPS
                
                num_chunks = int(dist_m / 10.0)
                if num_chunks > 1:
                    lat_step = (lat - prev_lat) / num_chunks
                    lon_step = (lon - prev_lon) / num_chunks
                    time_step = time_taken_sec / num_chunks
                    
                    for j in range(1, num_chunks):
                        int_lat = prev_lat + (lat_step * j)
                        int_lon = prev_lon + (lon_step * j)
                        current_time += pd.Timedelta(seconds=time_step)
                        coords.append([int_lon, int_lat])
                        times.append(current_time.strftime("%Y-%m-%dT%H:%M:%S"))
                
                current_time += pd.Timedelta(seconds=time_taken_sec)
                coords.append([lon, lat])
                times.append(current_time.strftime("%Y-%m-%dT%H:%M:%S"))
                
        if coords:
            # Diam sejenak di shelter saat tiba
            end_lon, end_lat = coords[-1]
            for _ in range(5):
                current_time += pd.Timedelta(seconds=60)
                coords.append([end_lon, end_lat])
                times.append(current_time.strftime("%Y-%m-%dT%H:%M:%S"))
                
            # Gambar jalur tipis di background
            folium.PolyLine(
                static_line_coords, 
                color="#e74c3c", 
                weight=1, 
                opacity=0.3,
                tooltip=f"Rute ke {tes_name} (ETA: {eta} mnt)"
            ).add_to(fg_routes)
        
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {
                'times': times,
                'style': {'color': '#ff4757', 'weight': 2, 'opacity': 0.7},
                'icon': 'circle',
                'iconstyle': {
                    'fillColor': '#ff4757',
                    'fillOpacity': 1,
                    'stroke': 'true',
                    'color': '#ffffff',
                    'weight': 1,
                    'radius': 5
                }
            }
        })

    fg_routes.add_to(m)
    print(f"Men-generate fitur animasi untuk {len(features)} agen evakuasi...")

    # 4. Tambahkan Gedung TES (Marker Interaktif)
    fg_tes = folium.FeatureGroup(name="Lokasi Shelter (TES)", show=True)
    for tes_name in used_tes:
        if tes_name in tes_dict:
            lat, lon, cap = tes_dict[tes_name]
            html_popup = f"""
            <div style="font-family: Arial; min-width: 150px;">
                <h4 style="margin-bottom: 5px; color: #2ecc71;">{tes_name}</h4>
                <b>Kapasitas:</b> {int(cap)} jiwa<br>
                <b>Status:</b> Shelter Vertikal
            </div>
            """
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(html_popup, max_width=300),
                icon=folium.Icon(color='green', icon='home', prefix='fa'),
                tooltip=tes_name
            ).add_to(fg_tes)
    fg_tes.add_to(m)
            
    # 5. Animasi TimestampedGeoJson
    geojson_data = {'type': 'FeatureCollection', 'features': features}
    
    plugins.TimestampedGeoJson(
        geojson_data,
        period='PT15S',
        add_last_point=True,
        auto_play=True,
        loop=True,
        max_speed=5,
        loop_button=True,
        date_options='HH:mm:ss',
        time_slider_drag_update=True,
        duration='PT1M'
    ).add_to(m)

    # 6. Kontrol Layer
    folium.LayerControl(position='topright', collapsed=False).add_to(m)

    m.save(output_file)
    conn.close()
    print(f"[SUKSES] Animasi Premium disimpan di {output_file}")

if __name__ == "__main__":
    db = "ranah_siaga_v2.db"
    out_html = "animasi_evakuasi_padang.html"
    create_premium_map(db, out_html, num_agents=200)
