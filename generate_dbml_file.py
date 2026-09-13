import os

dbml_detailed_content = """// DBML Schema Definition for dbdiagram.io
// Database: ranah_siaga.db (Sistem Routing Evakuasi Tsunami Kota Padang)

Project SiagaPadangERD {
  database_type: 'SQLite'
  Note: '''
    # ERD DETAIL DATABASE SIAGA PADANG (ranah_siaga.db)
    Spesifikasi Lengkap Primary Key (PK), Foreign Key (FK), Tipe Data & Relasi Entitas.
    Sistem Informasi Geografis & Routing Evakuasi Tsunami Kota Padang.
  '''
}

// ============================================================================
// 1. KELOMPOK GRAF & SPASIAL JALAN (NETWORK GRAPH)
// ============================================================================

Table tb_nodes {
  node_id integer [pk, increment, note: "PRIMARY KEY: ID Unik Simpul Persimpangan Jalan"]
  lat float [not null, note: "Koordinat Lintang (Latitude WGS84)"]
  lon float [not null, note: "Koordinat Bujur (Longitude WGS84)"]
  is_safe integer [not null, default: 0, note: "Flag Status Zona (0 = Rawan Tsunami, 1 = Perbukitan Aman/TEA)"]

  indexes {
    node_id [pk]
    (lat, lon) [name: "idx_nodes_coords"]
  }

  Note: "Master data simpul persimpangan jalan & titik rujukan awal evakuasi warga."
}

Table tb_edges {
  edge_id integer [pk, increment, note: "PRIMARY KEY: ID Unik Ruas Jalan"]
  u integer [not null, ref: > tb_nodes.node_id, note: "FOREIGN KEY -> tb_nodes.node_id (Simpul Asal Persimpangan)"]
  v integer [not null, ref: > tb_nodes.node_id, note: "FOREIGN KEY -> tb_nodes.node_id (Simpul Tujuan Persimpangan)"]
  length float [not null, note: "Panjang Ruas Jalan Faktual (dalam Meter)"]
  geometry text [note: "Geometri Spasial Garis Jalan (LineString WKT)"]

  indexes {
    edge_id [pk]
    u [name: "idx_edges_u"]
    v [name: "idx_edges_v"]
  }

  Note: "Master data ruas jalan penghubung antar persimpangan (Jaringan Graf Kota Padang)."
}

// ============================================================================
// 2. KELOMPOK ENGINE ROUTING & SHELTER EVAKUASI (ROUTING ENGINE)
// ============================================================================

Table tb_tes {
  tes_id varchar(50) [pk, note: "PRIMARY KEY: Kode Unik Shelter Evakuasi (contoh: TES_001, TES_002)"]
  nama_tes varchar(255) [not null, note: "Nama Resmi Gedung / Shelter Evakuasi"]
  zona varchar(100) [note: "Nama Kelurahan / Kecamatan Lokasi Shelter"]
  kapasitas float [not null, default: 0, note: "Kapasitas Daya Tampung Shelter (Satuan: Jiwa / Orang)"]
  lat float [not null, note: "Koordinat Lintang Lokasi Shelter"]
  lon float [not null, note: "Koordinat Bujur Lokasi Shelter"]

  indexes {
    tes_id [pk]
    zona [name: "idx_tes_zona"]
  }

  Note: "Master data Tempat Evakuasi Sementara (TES / Shelter Gedung Bertingkat)."
}

Table tb_routes {
  origin_node_id integer [pk, ref: - tb_nodes.node_id, note: "PRIMARY KEY & FOREIGN KEY -> tb_nodes.node_id (Titik Simpul Awal Warga)"]
  
  // Rekomendasi Prioritas Ke-1 (Top Option)
  rank_1_tes varchar(50) [ref: > tb_tes.tes_id, note: "FOREIGN KEY -> tb_tes.tes_id (Shelter TES Rekomendasi Utama Ke-1)"]
  rank_1_path text [note: "Array Node Path Jalur Rute Ke-1 (Format JSON/Text: [101, 105, 209])"]
  rank_1_eta float [note: "Estimasi Waktu Tempuh / ETA Rute Ke-1 (dalam Menit)"]
  
  // Rekomendasi Prioritas Ke-2 (Alternative Option 1)
  rank_2_tes varchar(50) [ref: > tb_tes.tes_id, note: "FOREIGN KEY -> tb_tes.tes_id (Shelter TES Rekomendasi Alternatif Ke-2)"]
  rank_2_path text [note: "Array Node Path Jalur Rute Ke-2"]
  rank_2_eta float [note: "Estimasi Waktu Tempuh / ETA Rute Ke-2 (dalam Menit)"]
  
  // Rekomendasi Prioritas Ke-3 (Alternative Option 2)
  rank_3_tes varchar(50) [ref: > tb_tes.tes_id, note: "FOREIGN KEY -> tb_tes.tes_id (Shelter TES Rekomendasi Alternatif Ke-3)"]
  rank_3_path text [note: "Array Node Path Jalur Rute Ke-3"]
  rank_3_eta float [note: "Estimasi Waktu Tempuh / ETA Rute Ke-3 (dalam Menit)"]

  indexes {
    origin_node_id [pk]
    rank_1_tes [name: "idx_routes_rank1"]
    rank_2_tes [name: "idx_routes_rank2"]
    rank_3_tes [name: "idx_routes_rank3"]
  }

  Note: "Matriks hasil algoritma Dijkstra / A* pra-kalkulasi rute evakuasi tercepat & teraman."
}

// ============================================================================
// 3. KELOMPOK GEOSPASIAL BENCANA & AMAN (GIS SPATIAL ZONES)
// ============================================================================

Table tb_inundation_zones {
  zone_id integer [pk, increment, note: "PRIMARY KEY: ID Unik Zona Rendaman"]
  nama_zona varchar(100) [not null, note: "Nama Kelurahan / Kawasan Pesisir Rawan"]
  tingkat_bahaya varchar(50) [not null, note: "Tingkat Bahaya Tsunami ('Sangat Rawan', 'Rawan Utama', 'Waspada')"]
  geometry_wkt text [note: "Geometri Poligon Spasial Zona Rendaman (Format WKT MultiPolygon)"]

  indexes {
    zone_id [pk]
    tingkat_bahaya [name: "idx_inundation_level"]
  }

  Note: "Data geospasial zona rawan limpasan gelombang tsunami."
}

Table tb_safe_zones {
  safe_zone_id integer [pk, increment, note: "PRIMARY KEY: ID Unik Zona Aman"]
  nama_zona varchar(100) [not null, note: "Nama Kawasan Perbukitan / Tempat Evakuasi Akhir (TEA)"]
  elevasi_m float [not null, note: "Ketinggian Elevasi dari Permukaan Laut (dalam Meter dpl)"]
  geometry_wkt text [note: "Geometri Poligon Spasial Zona Aman (Format WKT MultiPolygon)"]

  indexes {
    safe_zone_id [pk]
  }

  Note: "Data geospasial kawasan perbukitan timur Padang (Zona Bebas Tsunami)."
}

// ============================================================================
// TABLE GROUPS (PENGELOMPOKAN TABEL DI DBDAGRAM.IO)
// ============================================================================

TableGroup Network_Graph_Layer {
  tb_nodes
  tb_edges
}

TableGroup Routing_Engine_Layer {
  tb_routes
  tb_tes
}

TableGroup GIS_Spatial_Layer {
  tb_inundation_zones
  tb_safe_zones
}
"""

output_path_local = r"c:\gemastik\siaga_padang_erd.dbml"
output_path_artifact = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\6e25ee83-e7a5-43ef-bb35-d49386fe793a\siaga_padang_erd.dbml"

with open(output_path_local, "w", encoding="utf-8") as f:
    f.write(dbml_detailed_content)

os.makedirs(os.path.dirname(output_path_artifact), exist_ok=True)
with open(output_path_artifact, "w", encoding="utf-8") as f:
    f.write(dbml_detailed_content)

print("Detailed DBML file successfully created at:")
print(f" - {output_path_local}")
print(f" - {output_path_artifact}")
