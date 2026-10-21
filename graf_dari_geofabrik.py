"""
GRAF JALAN PEJALAN KAKI KOTA PADANG DARI EKSTRAK GEOFABRIK (PENGGANTI download_peta_full.py SAAT OVERPASS TIDAK BISA DIPAKAI)

Hasilnya setara dengan ox.graph_from_place("Kota Padang, Sumatera Barat, Indonesia", network_type="walk"):
penyaring "walk" OSMnx yang sama, graf dua arah, dipotong ke batas kota + penyangga 500 m, komponen terhubung
terbesar, disederhanakan, lalu dipotong ke batas kota. Bedanya hanya sumber data: berkas .osm.pbf Geofabrik
(diperbarui harian) dibaca langsung, bukan diunduh lewat Overpass API.

Pemakaian:
  env\\Scripts\\python.exe graf_dari_geofabrik.py <sumatra-YYMMDD.osm.pbf> [keluaran.graphml]
Butuh paket `osmium` (pyosmium). Ekstrak: https://download.geofabrik.de/asia/indonesia/sumatra.html
"""
import re
import sys

import networkx as nx
import osmium
import osmnx as ox
from osmnx import graph as ox_graph, projection, simplification, stats, truncate

TEMPAT = "Kota Padang, Sumatera Barat, Indonesia"
PBF = sys.argv[1]
KELUARAN = sys.argv[2] if len(sys.argv) > 2 else "padang_full.graphml"

# Penyaring Overpass network_type="walk" OSMnx 2.1, ditulis ulang untuk tag OSM ("!~" = tidak cocok regex,
# tag yang tidak ada dianggap lolos).
FILTER = ox._overpass._get_network_filter("walk")
SYARAT = [(k, re.compile(v)) for k, v in re.findall(r'\["([^"]+)"!~"([^"]+)"\]', FILTER)]
assert '["highway"]' in FILTER and len(SYARAT) == 9, FILTER


def lolos(tags):
    if "highway" not in tags:
        return False
    return not any(k in tags and pola.search(tags[k]) for k, pola in SYARAT)


batas = ox.geocode_to_gdf(TEMPAT)
polygon = batas.geometry.iloc[0]
poly_proj, crs_utm = projection.project_geometry(polygon)
poly_buff, _ = projection.project_geometry(poly_proj.buffer(500), crs=crs_utm, to_latlong=True)
x0, y0, x1, y1 = poly_buff.bounds
print(f"Batas: {batas.display_name.iloc[0]} (relasi {batas.osm_id.iloc[0]})")


class SimpulKotak(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.ada = set()

    def node(self, n):
        if x0 <= n.location.lon <= x1 and y0 <= n.location.lat <= y1:
            self.ada.add(n.id)


class Jalan(osmium.SimpleHandler):
    def __init__(self, ada):
        super().__init__()
        self.ada, self.jalan, self.perlu = ada, [], set()

    def way(self, w):
        tags = {t.k: t.v for t in w.tags}
        if not lolos(tags):
            return
        refs = [n.ref for n in w.nodes]
        if not any(r in self.ada for r in refs):
            return
        self.jalan.append({"type": "way", "id": w.id, "nodes": refs, "tags": tags})
        self.perlu.update(refs)


class SimpulPerlu(osmium.SimpleHandler):
    def __init__(self, perlu):
        super().__init__()
        self.perlu, self.simpul = perlu, []

    def node(self, n):
        if n.id in self.perlu:
            el = {"type": "node", "id": n.id, "lat": n.location.lat, "lon": n.location.lon}
            if len(n.tags):
                el["tags"] = {t.k: t.v for t in n.tags}
            self.simpul.append(el)


s1 = SimpulKotak(); s1.apply_file(PBF)
s2 = Jalan(s1.ada); s2.apply_file(PBF)
s3 = SimpulPerlu(s2.perlu); s3.apply_file(PBF)
print(f"PBF: {len(s2.jalan):,} way jalan kaki menyentuh kotak, {len(s3.simpul):,} simpul")

# Sama dengan graph_from_polygon OSMnx 2.1 setelah data diunduh.
G_buff = ox_graph._create_graph([{"elements": s3.simpul + s2.jalan}], bidirectional=True)
G_buff = truncate.truncate_graph_polygon(G_buff, poly_buff, truncate_by_edge=False)
G_buff = truncate.largest_component(G_buff, strongly=False)
G_buff = simplification.simplify_graph(G_buff)
G = truncate.truncate_graph_polygon(G_buff, polygon, truncate_by_edge=False)
G = truncate.largest_component(G, strongly=False)
nx.set_node_attributes(G, values=stats.count_streets_per_node(G_buff, nodes=G.nodes), name="street_count")
_r = osmium.io.Reader(PBF, osmium.osm.osm_entity_bits.NOTHING)
_stempel = _r.header().get("osmosis_replication_timestamp") or "tidak tercatat"
_r.close()
G.graph["sumber_data"] = f"ekstrak Geofabrik {PBF.replace(chr(92), '/').split('/')[-1]}, data OSM per {_stempel}"
print(f"Graf: {len(G.nodes):,} simpul, {len(G.edges):,} ruas")
ox.save_graphml(G, KELUARAN)
print(f"Disimpan: {KELUARAN}")
