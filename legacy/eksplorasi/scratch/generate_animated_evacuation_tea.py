import sqlite3
import pandas as pd
import folium
from folium import plugins
import math
import random
import os

print("=" * 70)
print("MEMBUAT ANIMASI VISUALISASI EVAKUASI KE TEA (ZONA AMAN)")
print("=" * 70)

WALKING_SPEED_MPS = 1.2

def get_node_coords(conn):
    print("Memuat koordinat node...")
    cur = conn.cursor()
    cur.execute("SELECT node_id, lat, lon, is_safe FROM tb_nodes")
    return {row[0]: (row[1], row[2], row[3]) for row in cur.fetchall()}

def get_tea_info(conn):
    cur = conn.cursor()
    cur.execute("SELECT tea_id, nama_tea, lat, lon FROM tb_tea")
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

def create_animated_map_tea(db_path, output_file, num_agents=100):
    conn = sqlite3.connect(db_path)
    nodes = get_node_coords(conn)
    tea_dict = get_tea_info(conn)
    
    cur = conn.cursor()
    
    # Pilih origin node secara acak dari zona risiko (is_safe = 0)
    cur.execute('''
        SELECT r.origin_node_id, r.nearest_tea_id 
        FROM tb_tea_routes r
        JOIN tb_nodes n ON r.origin_node_id = n.node_id
        WHERE n.is_safe = 0 AND r.nearest_tea_id IS NOT NULL
        ORDER BY RANDOM() LIMIT ?
    ''', (num_agents,))
    
    selected_agents = cur.fetchall()
    
    # Reconstruct paths
    agent_routes = []
    print("Merekontruksi jalur evakuasi ke TEA...")
    for origin, tea_id in selected_agents:
        path = [origin]
        curr = origin
        while True:
            cur.execute("SELECT next_node_id FROM tb_tea_next WHERE tea_id = ? AND node_id = ?", (tea_id, curr))
            row = cur.fetchone()
            if not row:
                break
            nxt = row[0]
            path.append(nxt)
            curr = nxt
        agent_routes.append((origin, tea_id, path))
    
    features = []
    base_time_str = "2026-10-01T10:00:00"
    base_time_pd = pd.to_datetime(base_time_str)
    
    used_tea = set()

    for origin_id, tea_id, node_ids in agent_routes:
        if len(node_ids) < 2:
            continue
            
        used_tea.add(tea_id)
            
        coords = []
        times = []
        current_time = base_time_pd
        
        for i in range(len(node_ids)):
            nid = node_ids[i]
            if nid not in nodes:
                continue
            lat, lon, _ = nodes[nid]
            
            if i == 0:
                coords.append([lon, lat])
                times.append(current_time.strftime("%Y-%m-%dT%H:%M:%S"))
            else:
                prev_lat, prev_lon, _ = nodes[node_ids[i-1]]
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
                
        if len(coords) > 0:
            end_lon, end_lat = coords[-1]
            for _ in range(5):
                current_time += pd.Timedelta(seconds=60)
                coords.append([end_lon, end_lat])
                times.append(current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': coords
            },
            'properties': {
                'times': times,
                'style': {
                    'color': '#3498db',
                    'weight': 3,
                    'opacity': 0.8
                },
                'icon': 'circle',
                'iconstyle': {
                    'fillColor': '#2980b9',
                    'fillOpacity': 1,
                    'stroke': 'true',
                    'radius': 4
                }
            }
        }
        features.append(feature)
        
    print(f"Men-generate fitur animasi untuk {len(features)} agen evakuasi ke TEA...")

    m = folium.Map(location=[-0.94, 100.38], zoom_start=13, tiles='OpenStreetMap')
    
    for tea_id in used_tea:
        if tea_id in tea_dict:
            nama, lat, lon = tea_dict[tea_id]
            folium.Marker(
                [lat, lon],
                popup=nama,
                icon=folium.Icon(color='blue', icon='flag')
            ).add_to(m)
            
    geojson_data = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    plugins.TimestampedGeoJson(
        geojson_data,
        period='PT30S',
        add_last_point=True,
        auto_play=True,
        loop=True,
        max_speed=5,
        loop_button=True,
        date_options='HH:mm:ss',
        time_slider_drag_update=True,
        duration='PT2M'
    ).add_to(m)

    m.save(output_file)
    conn.close()
    print(f"[SUKSES] Animasi disimpan di {output_file}")
    
    return output_file

if __name__ == "__main__":
    db = "ranah_siaga_v2.db"
    out_html = "animasi_evakuasi_tea_padang.html"
    create_animated_map_tea(db, out_html, num_agents=200)
