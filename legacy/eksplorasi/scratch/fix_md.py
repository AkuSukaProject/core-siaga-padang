import re

def process_md():
    with open(r"c:\gemastik\docs\erd_siaga_padang.md", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. tingkat_bahaya: 'Sangat Rawan', 'Rawan Utama', 'Waspada' -> Rendah, Sedang, Tinggi
    content = content.replace("'Sangat Rawan', 'Rawan Utama', 'Waspada'", "Rendah, Sedang, Tinggi")

    # 3. is_safe: "1 = Perbukitan Aman/TEA" -> "Tanda simpul di kawasan aman"
    content = content.replace("1 = Perbukitan Aman/TEA", "1 = Tanda simpul di kawasan aman")

    # 4. tb_safe_zones: disebut "(TEA)" -> 31 poligon kawasan aman, berbeda dengan 12 TEA
    # In table: | | nama_zona | TEXT | - | - | - | Nama kawasan perbukitan. | -> Nama kawasan perbukitan (31 poligon kawasan aman).
    # In mermaid: TEXT nama_zona "Nama Perbukitan" -> TEXT nama_zona "Nama Perbukitan (31 Poligon)"
    # Or just replace "(TEA)" with "(31 poligon kawasan aman)" where relevant.
    content = content.replace("Tempat Evakuasi Akhir (TEA)", "31 poligon kawasan aman")

    # 6. Algoritma: Dijkstra / A* -> Reverse Dijkstra
    content = content.replace("Dijkstra / A*", "Reverse Dijkstra")
    content = content.replace("algoritma Dijkstra / A* pra-kalkulasi", "algoritma Reverse Dijkstra pra-kalkulasi")

    # 7. Istilah shelter -> TES
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
    content = content.replace("Shelter", "TES")
    content = content.replace("shelter", "TES")

    # Now replace the DBML block entirely with the content of siaga_padang_erd.dbml
    with open(r"c:\gemastik\docs\siaga_padang_erd.dbml", "r", encoding="utf-8") as fdbml:
        dbml_content = fdbml.read()

    # Find the dbml block in md
    start_str = "```dbml\n"
    end_str = "```\n"
    
    start_idx = content.find(start_str)
    # The end of dbml block is the first "```" after start_idx + len(start_str)
    end_idx = content.find(end_str, start_idx + len(start_str))
    
    if start_idx != -1 and end_idx != -1:
        new_block = "```dbml\n" + dbml_content + "\n```\n"
        content = content[:start_idx] + new_block + content[end_idx + len(end_str):]

    with open(r"c:\gemastik\docs\erd_siaga_padang.md", "w", encoding="utf-8") as f:
        f.write(content)

process_md()
