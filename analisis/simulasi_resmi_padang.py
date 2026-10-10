"""
SIMULASI KANONIS EVAKUASI TSUNAMI KOTA PADANG (BASELINE vs SIAGA PADANG) - DATA V4

Membandingkan dua skenario dengan agen yang sama:
  A. Baseline     : warga tanpa aplikasi berjalan ke TES/TEA terdekat (jarak murni), tanpa aturan
                    pantai/jembatan dan tanpa memperhatikan kapasitas.
  B. Siaga Padang : warga mengikuti rekomendasi database (TES rank 1-3 berkapasitas, lalu TEA atau
                    zona aman terdekat), dengan aturan evakuasi BPBD yang sudah tertanam di rute.

Seluruh masukan dibaca dari ranah_siaga_v4.db (hasil build_db.py), sehingga simulasi dan aplikasi
memakai fasilitas, demand penduduk, dan rute yang sama. Parameter: docs/simulasi_kanonis.md.

Keluaran (analisis/output/):
  - peta_simulasi_berdampingan.html : peta Leaflet Baseline vs Siaga Padang
  - hasil_simulasi_fasilitas.csv    : beban tiap TES/TEA di kedua skenario
  - hasil_simulasi_kelurahan.csv    : tingkat keselamatan per kelurahan
"""
import sys
import os
import json
import time
import sqlite3

import numpy as np
import pandas as pd
import shapely
from shapely import wkt as shapely_wkt
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

sys.stdout.reconfigure(encoding="utf-8")

# ==============================================================================
# KONFIGURASI (rujukan: docs/simulasi_kanonis.md, docs/aturan_evakuasi_bpbd.md)
# ==============================================================================
RANDOM_SEED = 42
TOTAL_AGEN = 20000
BATAS_WAKTU_MENIT = 20.0
# Skenario pembanding kecepatan rata-rata (bukan kecepatan resmi).
KECEPATAN_PEMBANDING_MS = 1.2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "hasil_build", "ranah_siaga_v4.db")
DIR_OUTPUT = os.path.join(ROOT, "analisis", "output")

start_total = time.time()


def langkah(teks):
    print(f"\n[{time.time() - start_total:6.1f}s] {teks}")


if not os.path.exists(DB_PATH):
    sys.exit(f"[ERROR] {DB_PATH} tidak ditemukan. Jalankan build_db.py terlebih dahulu.")
os.makedirs(DIR_OUTPUT, exist_ok=True)

print("=" * 90)
print("SIMULASI KANONIS EVAKUASI TSUNAMI KOTA PADANG - BASELINE vs SIAGA PADANG (DATA V4)")
print("=" * 90)

# ==============================================================================
# 1. MEMUAT DATA DARI DATABASE V4
# ==============================================================================
langkah("[1/6] Memuat data dari ranah_siaga_v4.db...")
conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
meta = dict(conn.execute("SELECT kunci, nilai FROM tb_metadata"))
KECEPATAN_MS = float(meta["kecepatan_jalan_ms"])


def menit(meter):
    return np.asarray(meter) / KECEPATAN_MS / 60.0


nodes = pd.read_sql("SELECT n.node_id, n.is_safe, i.kelurahan, i.demand_jiwa FROM tb_nodes n "
                    "JOIN tb_node_info i ON i.node_id = n.node_id", conn)
N = len(nodes)
idx_of = pd.Series(np.arange(N), index=nodes["node_id"].to_numpy())

fas = pd.read_sql("SELECT facility_id, jenis, nama, kelurahan, kapasitas, nearest_node_id, snap_dist_m, lat, lon "
                  "FROM tb_fasilitas_info WHERE dipakai = 1 ORDER BY facility_id", conn)
fas["node_idx"] = idx_of[fas["nearest_node_id"]].to_numpy()
fas["akses_menit"] = menit(fas["snap_dist_m"])
K = len(fas)
k_of = {f: k for k, f in enumerate(fas["facility_id"])}
is_tes = (fas["jenis"] == "TES").to_numpy()
n_tes, n_tea = int(is_tes.sum()), int((~is_tes).sum())

edges = pd.read_sql("SELECT u, v, length FROM tb_edges", conn)
edges["a"] = idx_of[edges["u"]].to_numpy()
edges["b"] = idx_of[edges["v"]].to_numpy()
edges = edges[edges["a"] != edges["b"]]
edges[["a", "b"]] = np.sort(edges[["a", "b"]].to_numpy(), axis=1)
edges = edges.groupby(["a", "b"], as_index=False)["length"].min()
panjang_ruas = {(a, b): l for a, b, l in edges.itertuples(index=False)}

total_jiwa = nodes["demand_jiwa"].sum()
print(f"      Kecepatan: {KECEPATAN_MS} m/s | Fasilitas: {n_tes} TES & {n_tea} TEA | "
      f"Penduduk terpapar: {total_jiwa:,.0f} jiwa | Node: {N:,}")

# ==============================================================================
# 2. PEMBANGKITAN AGEN (PROPORSIONAL TERHADAP DEMAND KRB PER NODE)
# ==============================================================================
langkah(f"[2/6] Membangkitkan {TOTAL_AGEN:,} agen dari demand per node (seed {RANDOM_SEED})...")
rng = np.random.default_rng(RANDOM_SEED)
p = nodes["demand_jiwa"].to_numpy() / total_jiwa
asal_agen = rng.choice(N, size=TOTAL_AGEN, p=p)
jiwa_per_agen = total_jiwa / TOTAL_AGEN
# Kapasitas TES diskalakan ke jumlah agen; TEA dan zona aman tidak dibatasi.
kap_agen = np.where(is_tes, np.maximum(np.round(fas["kapasitas"].to_numpy() / jiwa_per_agen), 1), np.inf)
print(f"      1 agen = {jiwa_per_agen:.2f} jiwa | node asal unik: {len(np.unique(asal_agen)):,} "
      f"| agen di zona merah: {(nodes['is_safe'].to_numpy()[asal_agen] == 0).mean() * 100:.1f}%")

# ==============================================================================
# 3. SKENARIO A - BASELINE: FASILITAS TERDEKAT (JARAK MURNI, TANPA ATURAN & KAPASITAS)
# ==============================================================================
langkah("[3/6] Skenario A: Baseline (TES/TEA terdekat, jarak murni)...")
# Graf tak berarah + satu node virtual per fasilitas (terhubung ke node snap dengan jarak snap).
a, b, w = edges["a"].to_numpy(), edges["b"].to_numpy(), edges["length"].to_numpy()
virt = N + np.arange(K)
src = np.concatenate([a, b, virt, fas["node_idx"].to_numpy()])
dst = np.concatenate([b, a, fas["node_idx"].to_numpy(), virt])
bobot = np.concatenate([w, w, fas["snap_dist_m"].to_numpy() + 1e-6, fas["snap_dist_m"].to_numpy() + 1e-6])
G_murni = csr_matrix((bobot, (src, dst)), shape=(N + K, N + K))
jarak_terdekat, _, sumber = dijkstra(G_murni, directed=False, indices=virt, min_only=True, return_predecessors=True)
tujuan_a = sumber[asal_agen] - N
eta_a = menit(jarak_terdekat[asal_agen])
terjangkau_a = tujuan_a >= 0

urut_a = np.argsort(np.where(terjangkau_a, eta_a, np.inf), kind="stable")
beban_a = np.zeros(K)
masuk_a = np.zeros(TOTAL_AGEN, dtype=bool)
for i in urut_a:
    if not terjangkau_a[i]:
        continue
    k = tujuan_a[i]
    masuk_a[i] = beban_a[k] < kap_agen[k]
    beban_a[k] += 1

# ==============================================================================
# 4. SKENARIO B - SIAGA PADANG: REKOMENDASI DATABASE (KAPASITAS-AWARE + ATURAN BPBD)
# ==============================================================================
langkah("[4/6] Skenario B: Siaga Padang (rekomendasi database)...")
# 4a. ETA ke TEA tidak disimpan di DB; dihitung dari rantai tb_tea_next (panjang riil) + jarak akses.
eta_tea = {}
for tea_id, grup in pd.read_sql("SELECT tea_id, node_id, next_node_id FROM tb_tea_next", conn).groupby("tea_id"):
    if tea_id not in k_of:
        continue
    asal = idx_of[grup["node_id"]].to_numpy()
    lanjut = idx_of[grup["next_node_id"]].to_numpy()
    ptr = np.arange(N)
    ptr[asal] = lanjut
    jarak = np.zeros(N)
    jarak[asal] = [panjang_ruas[(min(x, y), max(x, y))] for x, y in zip(asal, lanjut)]
    ar = np.arange(N)
    while True:
        jarak = jarak + np.where(ptr != ar, jarak[ptr], 0.0)
        ptr_baru = ptr[ptr]
        if np.array_equal(ptr_baru, ptr):
            break
        ptr = ptr_baru
    k = k_of[tea_id]
    eta_tea[k] = menit(jarak) + fas.at[k, "akses_menit"]

# 4b. Kandidat per node asal: TES rank 1-3, TEA utama & alternatif, zona aman terdekat (urut ETA).
tes_by_nama_node = {(r.nama, r.nearest_node_id): k for k, r in fas[is_tes].iterrows()}
kandidat = {}
for r in pd.read_sql("SELECT * FROM tb_routes", conn).itertuples(index=False):
    n = idx_of[r.origin_node_id]
    daftar = []
    for nama, path, eta in [(r.rank_1_tes, r.rank_1_path, r.rank_1_eta), (r.rank_2_tes, r.rank_2_path, r.rank_2_eta),
                            (r.rank_3_tes, r.rank_3_path, r.rank_3_eta)]:
        k = tes_by_nama_node[(nama, int(path.rsplit(",", 1)[-1]))]
        if all(k != d[0] for d in daftar):
            daftar.append((k, float(eta)))
    kandidat[n] = daftar
for r in pd.read_sql("SELECT * FROM tb_tea_routes", conn).itertuples(index=False):
    n = idx_of[r.origin_node_id]
    for tea_id in dict.fromkeys([r.nearest_tea_id, r.alt_tea_id]):
        k = k_of[tea_id]
        kandidat.setdefault(n, []).append((k, float(eta_tea[k][n])))
eta_aman = np.full(N, np.inf)
# Rute zona aman v2: tujuan selalu lebih jauh dari pantai daripada titik asal (aturan BPBD).
safe = pd.read_sql("SELECT origin_node_id, safe_eta FROM tb_safe_routes_v2", conn)
eta_aman[idx_of[safe["origin_node_id"]].to_numpy()] = safe["safe_eta"].to_numpy()
ZONA_AMAN = -1
for n in np.unique(asal_agen):
    if np.isfinite(eta_aman[n]):
        kandidat.setdefault(n, []).append((ZONA_AMAN, float(eta_aman[n])))
    kandidat[n] = sorted(kandidat.get(n, []), key=lambda c: c[1])

# 4c. Agen diproses berurutan menurut ETA kandidat pertama; TES penuh dilewati.
pertama = np.array([kandidat[n][0][1] if kandidat[n] else np.inf for n in asal_agen])
urut_b = np.argsort(pertama, kind="stable")
beban_b = np.zeros(K)
tujuan_b = np.full(TOTAL_AGEN, -2)
eta_b = np.full(TOTAL_AGEN, np.inf)
for i in urut_b:
    for k, eta in kandidat[asal_agen[i]]:
        if k == ZONA_AMAN or beban_b[k] < kap_agen[k]:
            tujuan_b[i], eta_b[i] = k, eta
            if k != ZONA_AMAN:
                beban_b[k] += 1
            break
teralokasi_b = tujuan_b != -2
detour_b = np.where(teralokasi_b, eta_b - pertama, np.nan)

# ==============================================================================
# 5. METRIK
# ==============================================================================
langkah("[5/6] Menghitung metrik...")


def pct(x):
    return f"{x / TOTAL_AGEN * 100:5.1f}%"


tiba_a = terjangkau_a & (eta_a <= BATAS_WAKTU_MENIT)
selamat_a = tiba_a & (masuk_a | ~is_tes[np.clip(tujuan_a, 0, None)])
over_a = int(((beban_a > kap_agen) & is_tes).sum())
tiba_b = teralokasi_b & (eta_b <= BATAS_WAKTU_MENIT)
selamat_b = tiba_b
over_b = int(((beban_b > kap_agen) & is_tes).sum())
faktor = KECEPATAN_MS / KECEPATAN_PEMBANDING_MS
selamat_a_12 = terjangkau_a & (eta_a * faktor <= BATAS_WAKTU_MENIT) & (masuk_a | ~is_tes[np.clip(tujuan_a, 0, None)])
selamat_b_12 = teralokasi_b & (eta_b * faktor <= BATAS_WAKTU_MENIT)

jenis_b = np.where(tujuan_b == ZONA_AMAN, "ZONA_AMAN", np.where(tujuan_b >= 0, fas["jenis"].to_numpy()[np.clip(tujuan_b, 0, None)], "-"))
jenis_a = np.where(terjangkau_a, fas["jenis"].to_numpy()[np.clip(tujuan_a, 0, None)], "-")

print("\n" + "=" * 90)
print("HASIL SIMULASI EVAKUASI TSUNAMI KOTA PADANG (DATA V4)")
print("=" * 90)
print(f"Seed {RANDOM_SEED} | {TOTAL_AGEN:,} agen (1 agen = {jiwa_per_agen:.2f} jiwa dari {total_jiwa:,.0f} jiwa terpapar) | "
      f"{n_tes} TES & {n_tea} TEA | kecepatan {KECEPATAN_MS} m/s | batas {BATAS_WAKTU_MENIT:.0f} menit")
print("-" * 90)
print(f"{'Metrik':<48} | {'Baseline (terdekat)':<18} | {'Siaga Padang':<18}")
print("-" * 90)
baris = [
    ("TES melebihi kapasitas", f"{over_a} dari {n_tes}", f"{over_b} dari {n_tes}"),
    ("Tiba <= 20 menit (tanpa melihat kapasitas)", f"{tiba_a.sum():,} {pct(tiba_a.sum())}", f"{tiba_b.sum():,} {pct(tiba_b.sum())}"),
    ("SELAMAT: tiba <= 20 menit & tertampung", f"{selamat_a.sum():,} {pct(selamat_a.sum())}", f"{selamat_b.sum():,} {pct(selamat_b.sum())}"),
    ("Tiba di TES tapi tidak tertampung", f"{(terjangkau_a & ~masuk_a & is_tes[np.clip(tujuan_a, 0, None)]).sum():,}", "0"),
    ("Rata-rata waktu tempuh (menit)", f"{np.nanmean(np.where(terjangkau_a, eta_a, np.nan)):.2f}", f"{np.nanmean(np.where(teralokasi_b, eta_b, np.nan)):.2f}"),
    ("Rata-rata tambahan waktu karena pengalihan", "0.00", f"{np.nanmean(detour_b):.2f}"),
    ("Tujuan TES / TEA / zona aman (agen)",
     f"{(jenis_a == 'TES').sum():,} / {(jenis_a == 'TEA').sum():,} / 0",
     f"{(jenis_b == 'TES').sum():,} / {(jenis_b == 'TEA').sum():,} / {(jenis_b == 'ZONA_AMAN').sum():,}"),
    (f"Pembanding {KECEPATAN_PEMBANDING_MS} m/s: SELAMAT", f"{selamat_a_12.sum():,} {pct(selamat_a_12.sum())}",
     f"{selamat_b_12.sum():,} {pct(selamat_b_12.sum())}"),
]
for nama, x, y in baris:
    print(f"{nama:<48} | {x:<18} | {y:<18}")
print("-" * 90)
print("Catatan: Baseline tidak mengikuti aturan menjauhi pantai/jembatan; agen yang tiba di TES penuh dianggap")
print("tidak selamat. Siaga Padang tidak pernah melebihi kapasitas karena TES penuh dilewati.")
print("=" * 90)

# Keluaran tabel.
fas_out = fas[["facility_id", "jenis", "nama", "kelurahan", "kapasitas", "lat", "lon"]].copy()
fas_out["kapasitas_agen"] = np.where(is_tes, kap_agen, np.nan)
fas_out["beban_baseline_agen"] = beban_a
fas_out["beban_siaga_agen"] = beban_b
fas_out.to_csv(os.path.join(DIR_OUTPUT, "hasil_simulasi_fasilitas.csv"), index=False, encoding="utf-8-sig")

kel = nodes["kelurahan"].fillna("-").to_numpy()[asal_agen]
df_kel = pd.DataFrame({"kelurahan": kel, "baseline": selamat_a, "siaga": selamat_b}).groupby("kelurahan").agg(
    agen=("baseline", "size"), selamat_baseline=("baseline", "sum"), selamat_siaga=("siaga", "sum"))
df_kel["persen_baseline"] = (df_kel["selamat_baseline"] / df_kel["agen"] * 100).round(1)
df_kel["persen_siaga"] = (df_kel["selamat_siaga"] / df_kel["agen"] * 100).round(1)
df_kel.sort_values("persen_siaga").to_csv(os.path.join(DIR_OUTPUT, "hasil_simulasi_kelurahan.csv"), encoding="utf-8-sig")

# ==============================================================================
# 6. PETA BERDAMPINGAN
# ==============================================================================
langkah("[6/6] Membuat peta berdampingan...")
fas_json = []
for k, r in fas.iterrows():
    cap = None if not is_tes[k] else int(kap_agen[k])
    fas_json.append({
        "nama": r["nama"], "tipe": r["jenis"], "kel": r["kelurahan"], "lat": round(float(r["lat"]), 6), "lon": round(float(r["lon"]), 6),
        "cap": cap, "cap_bpbd": int(r["kapasitas"]) if is_tes[k] else None,
        "b_load": int(beban_a[k]), "s_load": int(beban_b[k]),
    })
zona = [{"type": "Feature", "properties": {"nama": nm},
         "geometry": shapely.geometry.mapping(shapely_wkt.loads(g).simplify(0.0002))}
        for nm, g in conn.execute("SELECT nama_zona, geometry_wkt FROM tb_inundation_zones")]
zona_json = json.dumps({"type": "FeatureCollection", "features": zona}, separators=(",", ":"))

ringkas_a = f"{selamat_a.sum() / TOTAL_AGEN * 100:.1f}%"
ringkas_b = f"{selamat_b.sum() / TOTAL_AGEN * 100:.1f}%"
html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simulasi Evakuasi Padang: Baseline vs Siaga Padang</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/leaflet.sync@0.2.4/L.Map.Sync.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #0f172a; color: #f8fafc; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}
  .top {{ padding: 10px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,.1); gap: 12px; flex-wrap: wrap; }}
  .title {{ font-size: 15px; font-weight: 800; color: #7dd3fc; }}
  .stats {{ display: flex; gap: 10px; font-size: 11px; flex-wrap: wrap; }}
  .badge {{ background: rgba(30,41,59,.85); border: 1px solid rgba(255,255,255,.12); padding: 5px 12px; border-radius: 20px; }}
  .maps {{ flex: 1; display: flex; position: relative; }}
  .wrap {{ flex: 1; position: relative; border-right: 2px solid rgba(255,255,255,.15); }}
  .wrap:last-child {{ border-right: none; }}
  .map {{ width: 100%; height: 100%; }}
  .card {{ position: absolute; top: 14px; left: 50%; transform: translateX(-50%); z-index: 999; background: rgba(15,23,42,.94); border: 1px solid rgba(255,255,255,.15); border-radius: 12px; padding: 10px 16px; width: 92%; max-width: 480px; }}
  .card h3 {{ font-size: 13px; margin-bottom: 4px; }}
  .card p {{ font-size: 11px; color: #94a3b8; line-height: 1.45; }}
  .legend {{ position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 999; background: rgba(15,23,42,.94); border: 1px solid rgba(255,255,255,.15); border-radius: 30px; padding: 8px 22px; display: flex; gap: 18px; font-size: 11px; flex-wrap: wrap; justify-content: center; }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 6px; vertical-align: middle; }}
  .leaflet-popup-content-wrapper, .leaflet-popup-tip {{ background: #1e293b !important; color: #f8fafc !important; }}
</style>
</head>
<body>
<div class="top">
  <div class="title">SIMULASI EVAKUASI TSUNAMI KOTA PADANG — DATA BPBD V4</div>
  <div class="stats">
    <span class="badge">Agen: <b>{TOTAL_AGEN:,}</b> ({total_jiwa:,.0f} jiwa)</span>
    <span class="badge">Fasilitas: <b>{n_tes} TES &amp; {n_tea} TEA</b></span>
    <span class="badge">Kecepatan: <b>{KECEPATAN_MS} m/s</b>, batas <b>{BATAS_WAKTU_MENIT:.0f} menit</b></span>
    <span class="badge">Seed: <b>{RANDOM_SEED}</b></span>
  </div>
</div>
<div class="maps">
  <div class="wrap">
    <div class="card"><h3>(a) Baseline — ke TES/TEA terdekat</h3>
      <p>Tanpa aturan pantai/jembatan dan tanpa memperhatikan kapasitas. <b>{over_a} TES</b> melebihi kapasitas. Selamat (tiba &le; 20 menit &amp; tertampung): <b>{ringkas_a}</b>.</p></div>
    <div id="map-a" class="map"></div>
  </div>
  <div class="wrap">
    <div class="card"><h3>(b) Siaga Padang — rekomendasi aplikasi</h3>
      <p>TES penuh dilewati, sisa warga ke TEA atau zona aman terdekat. <b>{(jenis_b == 'ZONA_AMAN').sum():,} agen</b> diarahkan ke zona aman. Selamat: <b>{ringkas_b}</b>.</p></div>
    <div id="map-b" class="map"></div>
  </div>
  <div class="legend">
    <span><span class="dot" style="background:#22c55e"></span>TEA</span>
    <span><span class="dot" style="background:#ef4444"></span>TES melebihi kapasitas</span>
    <span><span class="dot" style="background:#64748b"></span>TES dalam kapasitas</span>
    <span><span class="dot" style="background:rgba(239,68,68,.35)"></span>Zona merah (landaan)</span>
  </div>
</div>
<script>
const fas = {json.dumps(fas_json, separators=(",", ":"))};
const zona = {zona_json};
const opsi = {{center: [-0.93, 100.37], zoom: 12}};
const mapA = L.map('map-a', opsi), mapB = L.map('map-b', opsi);
const tile = 'https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png';
[mapA, mapB].forEach(m => {{
  L.tileLayer(tile, {{maxZoom: 19, attribution: '&copy; OpenStreetMap &copy; CARTO'}}).addTo(m);
  L.geoJSON(zona, {{style: {{color: '#ef4444', weight: 0.5, fillColor: '#ef4444', fillOpacity: 0.18}}, interactive: false}}).addTo(m);
}});
mapA.sync(mapB); mapB.sync(mapA);
function tambah(m, f, siaga) {{
  const beban = siaga ? f.s_load : f.b_load;
  const tea = f.tipe === 'TEA';
  const lebih = !tea && beban > f.cap;
  const warna = tea ? '#22c55e' : (lebih ? '#ef4444' : '#64748b');
  const persen = tea ? '' : ` (${{Math.round(beban / f.cap * 100)}}% kapasitas)`;
  L.circleMarker([f.lat, f.lon], {{radius: Math.max(tea ? 7 : 4, Math.min(22, Math.sqrt(beban) * 1.5)),
    fillColor: warna, color: '#0f172a', weight: 1, fillOpacity: 0.85}})
   .bindPopup(`<b>${{f.nama}}</b> (${{f.tipe}})<br>Kelurahan: ${{f.kel}}<br>Beban: ${{beban.toLocaleString()}} agen${{persen}}` +
              (tea ? '<br>Kapasitas: tidak dibatasi' : `<br>Kapasitas: ${{f.cap.toLocaleString()}} agen (BPBD: ${{f.cap_bpbd.toLocaleString()}} jiwa)`))
   .addTo(m);
}}
fas.forEach(f => {{ tambah(mapA, f, false); tambah(mapB, f, true); }});
</script>
</body>
</html>
"""
path_html = os.path.join(DIR_OUTPUT, "peta_simulasi_berdampingan.html")
with open(path_html, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nKeluaran di {os.path.relpath(DIR_OUTPUT, ROOT)}/: peta_simulasi_berdampingan.html, "
      f"hasil_simulasi_fasilitas.csv, hasil_simulasi_kelurahan.csv")
print(f"Total waktu: {time.time() - start_total:.1f} detik")
