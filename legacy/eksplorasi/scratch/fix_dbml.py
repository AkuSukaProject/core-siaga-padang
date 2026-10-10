import re

def process_dbml():
    with open(r"c:\gemastik\docs\siaga_padang_erd.dbml", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. tingkat_bahaya: 'Sangat Rawan', 'Rawan Utama', 'Waspada' -> Rendah, Sedang, Tinggi
    content = content.replace("'Sangat Rawan', 'Rawan Utama', 'Waspada'", "Rendah, Sedang, Tinggi")

    # 2. Indeks: Remove those not mentioned
    # We remove indexes block from tb_nodes, tb_edges, tb_routes, tb_inundation_zones, tb_safe_zones
    content = re.sub(r'Table tb_nodes \{.*?(indexes\s*\{.*?\})', lambda m: m.group(0).replace(m.group(1), ''), content, flags=re.DOTALL)
    content = re.sub(r'Table tb_edges \{.*?(indexes\s*\{.*?\})', lambda m: m.group(0).replace(m.group(1), ''), content, flags=re.DOTALL)
    content = re.sub(r'Table tb_routes \{.*?(indexes\s*\{.*?\})', lambda m: m.group(0).replace(m.group(1), ''), content, flags=re.DOTALL)
    content = re.sub(r'Table tb_inundation_zones \{.*?(indexes\s*\{.*?\})', lambda m: m.group(0).replace(m.group(1), ''), content, flags=re.DOTALL)
    content = re.sub(r'Table tb_safe_zones \{.*?(indexes\s*\{.*?\})', lambda m: m.group(0).replace(m.group(1), ''), content, flags=re.DOTALL)

    # 3. is_safe: "1 = Perbukitan Aman/TEA" -> Tanda simpul di kawasan aman
    content = content.replace("1 = Perbukitan Aman/TEA", "1 = Tanda simpul di kawasan aman")

    # 4. tb_safe_zones: disebut "(TEA)" -> 31 poligon kawasan aman
    content = content.replace("Tempat Evakuasi Akhir (TEA)", "31 poligon kawasan aman")

    # 6. Algoritma: Dijkstra / A* -> Reverse Dijkstra
    content = content.replace("Dijkstra / A*", "Reverse Dijkstra")
    content = content.replace("algoritma Dijkstra / A* pra-kalkulasi", "algoritma Reverse Dijkstra pra-kalkulasi")

    # 7. Istilah shelter -> TES
    # carefully replace shelter with TES where appropriate
    content = content.replace("Shelter Evakuasi", "TES")
    content = content.replace("shelter evakuasi", "TES")
    content = content.replace("Shelter TES", "TES")
    content = content.replace("shelter TES", "TES")
    content = content.replace("Shelter Gedung", "TES Gedung")
    content = content.replace("Shelter TEA", "TEA")
    content = content.replace("shelter TEA", "TEA")
    content = content.replace("Lokasi Shelter", "Lokasi TES")
    content = content.replace("Daya Tampung Shelter", "Daya Tampung TES")
    content = content.replace("Nama Shelter", "Nama TES")
    content = content.replace("Kode Shelter", "Kode TES")
    content = content.replace("Kode Unik Shelter", "Kode Unik TES")

    with open(r"c:\gemastik\docs\siaga_padang_erd.dbml", "w", encoding="utf-8") as f:
        f.write(content)

process_dbml()
