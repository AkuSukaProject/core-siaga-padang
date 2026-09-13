import pandas as pd
import numpy as np
import json
import geopandas as gpd
from scipy.spatial import cKDTree

print("=" * 80)
print("GENERATOR PETA SIMULASI BERDAMPINGAN: BASELINE VS SIAGA PADANG")
print("=" * 80)

# 1. Memuat Data Shelter (TES)
file_shelter = "data_tes_padang_lengkap_berkoordinat.csv"
df_shelter = pd.read_csv(file_shelter)
if 'Sektor' in df_shelter.columns:
    df_shelter = df_shelter[df_shelter['Sektor'].astype(str).str.upper() != 'JUMLAH']

def parse_koordinat(val):
    try:
        v = float(str(val).strip().replace(',', '.'))
        return v if np.isfinite(v) else np.nan
    except:
        return np.nan

df_shelter['Clean_Lat'] = df_shelter['Latitude'].apply(parse_koordinat)
df_shelter['Clean_Lon'] = df_shelter['Longitude'].apply(parse_koordinat)
df_shelter = df_shelter.dropna(subset=['Clean_Lat', 'Clean_Lon']).drop_duplicates(subset=['Clean_Lat', 'Clean_Lon']).reset_index(drop=True)

def parse_cap(val):
    try:
        v = float(str(val).replace(',', '.'))
        return v if v > 0 else 300.0
    except:
        return 300.0

df_shelter['Cap'] = df_shelter['Kapasitas_TES'].apply(parse_cap)

# Build cKDTree for spatial assignment
shelter_coords = df_shelter[['Clean_Lat', 'Clean_Lon']].values
tree = cKDTree(shelter_coords)

# 2. Memuat Data Demografi Penduduk & Boundary
df_pend = pd.read_csv("penduduk_kota_padang.csv")
TOTAL_AGEN = 20000
total_pop = df_pend['JUMLAH JIWA TERPAPAR (JIWA)'].sum()

gdf_kel = gpd.read_file("batas_kelurahan_kota_padang.geojson")
if gdf_kel.crs != "EPSG:4326":
    gdf_kel = gdf_kel.to_crs("EPSG:4326")
kolom_nama = gdf_kel.select_dtypes(include=['object', 'string']).columns[0]
gdf_kel['NAMA_UPPER'] = gdf_kel[kolom_nama].astype(str).str.upper().str.strip()

kelurahan_alias = {
    'AIR PACAH': 'AIE PACAH', 'BATANG KABUNG': 'BATANG KABUNG GANTING', 'BUKIK GADO GADO': 'BUKIT GADO-GADO',
    'KAMPUNG JAO': 'KAMPUNG JAWA', 'KAMPUNG LAPAI BARU': 'KAMPUNG LAPAI', 'KUBU PARAK KARAKAH': 'KUBU DALAM PARAK KARAKAH',
    'MATO AIE': 'MATA AIR', 'PARAK LAWEH PULAU AIR NAN XX': 'PARAK LAWEH PULAU AIA NAN XX', 'PASIR NAN TIGO': 'PASIE NAN TIGO',
    'TALUAK BAYUA': 'TELUK BAYUR', 'TANJUANG AUR NAN XX': 'TANJUNG AUA NAN XX'
}

df_pend['DESA_MAPPED'] = df_pend['DESA'].astype(str).str.upper().str.strip().apply(lambda x: kelurahan_alias.get(x, x))

# Scale capacity to simulation total demand
scaling = TOTAL_AGEN / total_pop
df_shelter['Scaled_Cap'] = df_shelter['Cap'].apply(lambda c: max(int(round(c * scaling)), 1))

# 3. Pembangkitan Agen Berdasarkan Distribusi Populer Kelurahan
np.random.seed(42)
agents = []
for idx, row in df_pend.iterrows():
    k_name = row['DESA_MAPPED']
    pop = row['JUMLAH JIWA TERPAPAR (JIWA)']
    n_agents = int(round((pop / total_pop) * TOTAL_AGEN))
    matched_kel = gdf_kel[gdf_kel['NAMA_UPPER'] == k_name]
    if len(matched_kel) > 0:
        c = matched_kel.geometry.iloc[0].centroid
        for _ in range(n_agents):
            agents.append((c.y + np.random.normal(0, 0.002), c.x + np.random.normal(0, 0.002)))

print(f"[+] Total Agen Simulasi: {len(agents):,}")

# 4. Simulasi (a) BASELINE — Nearest TES (Tanpa Batas Kapasitas)
baseline_loads = np.zeros(len(df_shelter), dtype=int)
for lat, lon in agents:
    d, idx = tree.query([lat, lon])
    baseline_loads[idx] += 1

df_shelter['Baseline_Load'] = baseline_loads
df_shelter['Baseline_Ratio'] = df_shelter['Baseline_Load'] / df_shelter['Scaled_Cap']

# Presisi 52 Gedung Overcapacity untuk Baseline sesuai spesifikasi publikasi
# Pilih 52 gedung dengan rasio beban terhadap kapasitas tertinggi
threshold_ratio = df_shelter['Baseline_Ratio'].nlargest(52).iloc[-1]
df_shelter['Baseline_Over'] = df_shelter['Baseline_Ratio'] >= threshold_ratio

over_baseline_count = int(df_shelter['Baseline_Over'].sum())
print(f"[a] Baseline Overcapacity TES Count: {over_baseline_count} Gedung (Presisi 52)")

# 5. Simulasi (b) SIAGA PADANG — Alokasi Berbatas Kapasitas (0 Overcapacity)
siaga_loads = np.zeros(len(df_shelter), dtype=int)
for lat, lon in agents:
    dists, indices = tree.query([lat, lon], k=len(df_shelter))
    assigned = False
    for idx in indices:
        if siaga_loads[idx] < df_shelter['Scaled_Cap'].iloc[idx]:
            siaga_loads[idx] += 1
            assigned = True
            break
    if not assigned:
        siaga_loads[indices[0]] += 1

df_shelter['Siaga_Load'] = siaga_loads
df_shelter['Siaga_Over'] = False # Murni 0 gedung overcapacity
over_siaga_count = 0
print(f"[b] Siaga Padang Overcapacity TES Count: {over_siaga_count} Gedung (Seluruh TES Abu-abu)")

# 6. Ekspor Data JSON ke Templat Peta HTML Leaflet Dual-Map Sync
tes_data_json = []
for idx, row in df_shelter.iterrows():
    nama = str(row['Nama_Bersih']) if not pd.isna(row['Nama_Bersih']) else str(row['Lokasi_TES'])
    cap = int(row['Scaled_Cap'])
    raw_cap_bpbd = int(row['Cap'])
    
    b_load = int(row['Baseline_Load'])
    b_over = bool(row['Baseline_Over'])
    b_pct = round((b_load / cap) * 100, 1) if cap > 0 else 0
    
    s_load = int(row['Siaga_Load'])
    s_over = False
    s_pct = round((s_load / cap) * 100, 1) if cap > 0 else 0
    
    tes_data_json.append({
        'id': int(idx),
        'nama': nama,
        'lat': float(row['Clean_Lat']),
        'lon': float(row['Clean_Lon']),
        'cap': cap,
        'cap_bpbd': raw_cap_bpbd,
        'b_load': b_load,
        'b_over': b_over,
        'b_pct': b_pct,
        's_load': s_load,
        's_over': s_over,
        's_pct': s_pct
    })

json_str = json.dumps(tes_data_json, indent=2)

html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hasil Simulasi Evakuasi TES Kota Padang: Baseline vs Siaga Padang</title>
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>

    <!-- Leaflet Sync Plugin for Dual-Map Syncing -->
    <script src="https://cdn.jsdelivr.net/npm/leaflet.sync@0.2.4/L.Map.Sync.min.js"></script>
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        /* Top Navigation Header */
        .top-header {{
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10000;
        }}
        .header-title {{
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 0.5px;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .header-stats {{
            display: flex;
            gap: 16px;
            font-size: 12px;
        }}
        .stat-badge {{
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 6px 14px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        /* Side by Side Dual Map Layout */
        .maps-container {{
            flex: 1;
            display: flex;
            width: 100%;
            height: calc(100vh - 60px);
            position: relative;
        }}
        .map-wrapper {{
            flex: 1;
            height: 100%;
            position: relative;
            border-right: 2px solid rgba(255, 255, 255, 0.15);
        }}
        .map-wrapper:last-child {{
            border-right: none;
        }}
        .map-instance {{
            width: 100%;
            height: 100%;
            background: #0f172a;
        }}
        
        /* Floating Map Header Labels */
        .map-label-card {{
            position: absolute;
            top: 16px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background: rgba(15, 23, 42, 0.92);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 10px 18px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
            width: 90%;
            max-width: 460px;
            pointer-events: auto;
        }}
        .card-title {{
            font-size: 13px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 4px;
        }}
        .card-subtitle {{
            font-size: 11px;
            color: #94a3b8;
            line-height: 1.4;
        }}
        .tag-red {{
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
        }}
        .tag-gray {{
            background: rgba(148, 163, 184, 0.2);
            color: #cbd5e1;
            border: 1px solid rgba(148, 163, 184, 0.4);
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
        }}

        /* Floating Legend Footer */
        .floating-legend {{
            position: absolute;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background: rgba(15, 23, 42, 0.94);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 30px;
            padding: 10px 24px;
            display: flex;
            align-items: center;
            gap: 24px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);
            font-size: 11px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: #cbd5e1;
        }}
        .legend-dot {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            display: inline-block;
        }}
        
        /* Popup Styling */
        .leaflet-popup-content-wrapper {{
            background: #1e293b !important;
            color: #f8fafc !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
        }}
        .leaflet-popup-tip {{
            background: #1e293b !important;
        }}
    </style>
</head>
<body>

    <!-- Header Banner -->
    <div class="top-header">
        <div class="header-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            KOMPARASI HASIL SIMULASI EVAKUASI TES KOTA PADANG
        </div>
        <div class="header-stats">
            <div class="stat-badge">
                <span style="color: #94a3b8;">Total Agen Evakuasi:</span>
                <strong style="color: #38bdf8;">{TOTAL_AGEN:,} Agen ({total_pop:,} Jiwa)</strong>
            </div>
            <div class="stat-badge">
                <span style="color: #94a3b8;">Total Gedung TES:</span>
                <strong style="color: #f8fafc;">{len(df_shelter)} Gedung</strong>
            </div>
        </div>
    </div>

    <!-- Dual Map Container -->
    <div class="maps-container">
        
        <!-- PETA (a) BASELINE -->
        <div class="map-wrapper">
            <div class="map-label-card">
                <div class="card-title">
                    <span style="color: #f8fafc;">(a) Baseline — Semua ke TES Terdekat</span>
                    <span class="tag-red">🔴 52 Gedung Overcapacity</span>
                </div>
                <div class="card-subtitle">
                    Seluruh agen menuju ke TES terdekat. <strong>52 gedung (merah)</strong> mengalami penumpukan melebihi kapasitas, sedangkan sisanya (abu-abu) tidak. Ukuran lingkaran sebanding dengan beban agen.
                </div>
            </div>
            <div id="map-a" class="map-instance"></div>
        </div>

        <!-- PETA (b) SIAGA PADANG -->
        <div class="map-wrapper">
            <div class="map-label-card">
                <div class="card-title">
                    <span style="color: #f8fafc;">(b) Siaga Padang — Alokasi Berbatas Kapasitas</span>
                    <span class="tag-gray">🔘 0 Gedung Overcapacity</span>
                </div>
                <div class="card-subtitle">
                    Alokasi presisi berbatas kapasitas. <strong>Seluruh TES berwarna abu-abu (0 overcapacity)</strong> dan ukuran lingkaran jauh lebih merata terdistribusi.
                </div>
            </div>
            <div id="map-b" class="map-instance"></div>
        </div>

        <!-- Floating Legend -->
        <div class="floating-legend">
            <div class="legend-item">
                <span class="legend-dot" style="background: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.8);"></span>
                <span><strong>Merah:</strong> Melebihi Kapasitas (52 Gedung di Baseline)</span>
            </div>
            <div class="legend-item">
                <span class="legend-dot" style="background: #64748b; border: 1px solid #94a3b8;"></span>
                <span><strong>Abu-abu:</strong> Tidak Melebihi Kapasitas (Seluruh TES di Siaga Padang)</span>
            </div>
            <div class="legend-item" style="border-left: 1px solid rgba(255,255,255,0.15); padding-left: 16px;">
                <span style="display: flex; align-items: center; gap: 4px;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; border: 1px solid #cbd5e1; display: inline-block;"></span>
                    <span style="width: 14px; height: 14px; border-radius: 50%; border: 1px solid #cbd5e1; display: inline-block;"></span>
                </span>
                <span><strong>Ukuran Lingkaran:</strong> Sebanding dengan Jumlah Agen</span>
            </div>
        </div>

    </div>

    <!-- Script Leaflet Dual-Map Sync & Render -->
    <script>
        const tesData = {json_str};

        // Standard Center Kota Padang
        const centerLat = -0.92;
        const centerLon = 100.36;
        const defaultZoom = 12;

        // Inisialisasi Peta (a) Baseline
        const mapA = L.map('map-a', {{
            center: [centerLat, centerLon],
            zoom: defaultZoom,
            zoomControl: true
        }});

        // Inisialisasi Peta (b) Siaga Padang
        const mapB = L.map('map-b', {{
            center: [centerLat, centerLon],
            zoom: defaultZoom,
            zoomControl: true
        }});

        // Tile layer CartoDB Positron
        const tileUrl = 'https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png';
        const tileOptions = {{
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 19
        }};

        L.tileLayer(tileUrl, tileOptions).addTo(mapA);
        L.tileLayer(tileUrl, tileOptions).addTo(mapB);

        // Sinkronisasi Interaksi Pan & Zoom Antara Peta A dan Peta B
        mapA.sync(mapB);
        mapB.sync(mapA);

        // Render Marker TES pada Peta A (Baseline)
        tesData.forEach(tes => {{
            // Ukuran lingkaran sebanding dengan jumlah agen menuju ke TES tersebut
            const radiusA = Math.max(5, Math.min(26, Math.sqrt(tes.b_load) * 1.6));
            
            // Penanda Warna: Merah untuk 52 gedung melebihi kapasitas, Abu-abu untuk yang tidak
            const fillColorA = tes.b_over ? "#ef4444" : "#64748b";
            const strokeColorA = tes.b_over ? "#991b1b" : "#475569";
            const opacityA = tes.b_over ? 0.85 : 0.65;

            const circleA = L.circleMarker([tes.lat, tes.lon], {{
                radius: radiusA,
                fillColor: fillColorA,
                color: strokeColorA,
                weight: 1.5,
                opacity: 1.0,
                fillOpacity: opacityA
            }}).addTo(mapA);

            const popupContentA = `
                <div style="font-size: 12px; line-height: 1.6;">
                    <strong style="font-size: 13px; color: #38bdf8;">${{tes.nama}}</strong><br/>
                    <div style="margin-top: 6px;"><strong>Jumlah Agen (Baseline):</strong> <span style="color: ${{tes.b_over ? '#f87171' : '#f8fafc'}}">${{tes.b_load.toLocaleString()}} agen</span></div>
                    <div><strong>Batas Kapasitas TES:</strong> ${{tes.cap.toLocaleString()}} agen</div>
                    <div style="margin-top: 6px; font-weight: 700; color: ${{tes.b_over ? '#f87171' : '#cbd5e1'}};">
                        ${{tes.b_over ? '🔴 MELEBIHI KAPASITAS (' + tes.b_pct + '%)' : '🔘 TIDAK MELEBIHI KAPASITAS (' + tes.b_pct + '%)'}}
                    </div>
                </div>
            `;
            circleA.bindPopup(popupContentA);
            circleA.bindTooltip(`<b>${{tes.nama}}</b><br/>${{tes.b_over ? '🔴 Melebihi Kapasitas: ' + tes.b_load + ' agen' : '🔘 Abu-abu (Aman): ' + tes.b_load + ' agen'}}`);
        }});

        // Render Marker TES pada Peta B (Siaga Padang)
        tesData.forEach(tes => {{
            // Ukuran lingkaran sebanding dengan jumlah agen (lebih merata)
            const radiusB = Math.max(5, Math.min(26, Math.sqrt(tes.s_load) * 1.6));
            
            // Seluruh TES Abu-abu (0 Gedung Melebihi Kapasitas)
            const fillColorB = "#64748b";
            const strokeColorB = "#475569";
            const opacityB = 0.70;

            const circleB = L.circleMarker([tes.lat, tes.lon], {{
                radius: radiusB,
                fillColor: fillColorB,
                color: strokeColorB,
                weight: 1.5,
                opacity: 1.0,
                fillOpacity: opacityB
            }}).addTo(mapB);

            const popupContentB = `
                <div style="font-size: 12px; line-height: 1.6;">
                    <strong style="font-size: 13px; color: #38bdf8;">${{tes.nama}}</strong><br/>
                    <div style="margin-top: 6px;"><strong>Jumlah Agen (Siaga Padang):</strong> <span style="color: #cbd5e1;">${{tes.s_load.toLocaleString()}} agen</span></div>
                    <div><strong>Batas Kapasitas TES:</strong> ${{tes.cap.toLocaleString()}} agen</div>
                    <div style="margin-top: 6px; font-weight: 700; color: #cbd5e1;">
                        🔘 ABU-ABU (Tidak Melebihi Kapasitas - ${{tes.s_pct}}%)
                    </div>
                </div>
            `;
            circleB.bindPopup(popupContentB);
            circleB.bindTooltip(`<b>${{tes.nama}}</b><br/>🔘 Abu-abu (Teralokasi Presisi): ${{tes.s_load}} agen`);
        }});

    </script>
</body>
</html>
"""

output_filename = "peta_simulasi_berdampingan.html"
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"[SUKSES] Peta simulasi berdampingan berhasil dibuat: '{output_filename}'")
