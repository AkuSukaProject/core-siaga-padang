import networkx as nx

print("Membaca padang.graphml...")
G = nx.read_graphml("padang.graphml")

G_gephi = nx.Graph(G)

# Membersihkan dan MEMAKSA tipe data x dan y menjadi Float (Double)
for n, data in G_gephi.nodes(data=True):
    # Paksa x dan y jadi angka desimal agar terbaca oleh GeoLayout Gephi
    if 'x' in data:
        data['x'] = float(data['x'])
    if 'y' in data:
        data['y'] = float(data['y'])
        
    # Bersihkan tipe data list/array lainnya menjadi string
    for k, v in list(data.items()):
        if isinstance(v, list): 
            G_gephi.nodes[n][k] = str(v)

for u, v, data in G_gephi.edges(data=True):
    for k, val in list(data.items()):
        if isinstance(val, list): 
            G_gephi.edges[u, v][k] = str(val)

# Ekspor ke GEXF baru
output_file = "padang_siap_gephi_fixed.gexf"
nx.write_gexf(G_gephi, output_file)
print(f"Berhasil! Silakan buka '{output_file}' di Gephi.")