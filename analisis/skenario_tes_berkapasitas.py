r"""Dampak skenario 'hanya TES berkapasitas tercatat' (167 TES) terhadap kandidat TES per simpul zona merah.
Biaya rute, syarat arah, dan jembatan-sebagai-cadangan meniru build_db.py (versi 2026.10.16), dihitung dari DB.
Kandidat dihitung ulang dari semua TES skenario (bukan menyaring rank 1-3 lama).
Pemakaian: env\Scripts\python.exe analisis\skenario_tes_berkapasitas.py <ranah_siaga_v4.db> <keluaran_per_kelurahan.csv>
Contoh (data 2026.10.16 dari Release db-2026.10.16):
  ... analisis\skenario_tes_berkapasitas.py ranah_siaga_v4.db analisis/output/skenario_tes_berkapasitas/2026.10.16/per_kelurahan.csv"""
import sqlite3, sys
import numpy as np, pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from pyproj import Transformer

sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(sys.argv[1])
q = lambda s: c.execute(s).fetchall()
m = dict(q("select kunci, nilai from tb_metadata"))
V = float(m["kecepatan_jalan_ms"]); TOL = float(m["toleransi_mendekat_pantai_m"]); PEN = float(m["penalti_mendekat_pantai"])
BOBOT = float(m["bobot_per_meter_mendekat_pantai"]); PJEMB = float(m["penalti_jembatan"]); FRESMI = float(m["jalur_resmi_faktor"])
SIN, DEKAT = float(m["arah_min_sin"]), float(m["arah_jarak_dekat_m"])
menit = lambda x: x / V / 60.0

nd = pd.read_sql("select n.node_id, n.lat, n.lon, n.is_safe, i.d_pantai_m, i.demand_jiwa, i.kelurahan "
                 "from tb_nodes n join tb_node_info i using(node_id)", c)
N = len(nd); idx = {v: i for i, v in enumerate(nd.node_id)}
x, y = Transformer.from_crs("EPSG:4326", "EPSG:32747", always_xy=True).transform(nd.lon.values, nd.lat.values)
dp = nd.d_pantai_m.to_numpy()

e = pd.read_sql("select edge_id, u, v, length from tb_edges", c)
e["jemb"] = e.edge_id.isin({r[0] for r in q("select edge_id from tb_bridge_edges")})
e["a"], e["b"] = np.minimum(e.u, e.v), np.maximum(e.u, e.v)
e = e.sort_values("length").drop_duplicates(["a", "b"])  # satu ruas per pasangan simpul (yang terpendek)
resmi = {(min(u, v), max(u, v)) for u, v in q("select u, v from tb_jalur_resmi")}
e["resmi"] = [(a, b) in resmi for a, b in zip(e.a, e.b)]
ia, ib = e.a.map(idx).to_numpy(), e.b.map(idx).to_numpy()
src, dst = np.concatenate([ia, ib]), np.concatenate([ib, ia])
L = np.concatenate([e.length.to_numpy()] * 2)
jemb = np.concatenate([e.jemb.to_numpy()] * 2); res = np.concatenate([e.resmi.to_numpy()] * 2)
wr = menit(L)
turun = dp[src] - dp[dst]
biaya = wr * np.where(turun > TOL, PEN, 1.0) * np.where(res, FRESMI, 1.0) + BOBOT * menit(np.maximum(turun, 0))
W_t = csr_matrix((biaya[~jemb], (dst[~jemb], src[~jemb])), shape=(N, N))
W_d = csr_matrix((biaya * np.where(jemb, PJEMB, 1.0), (dst, src)), shape=(N, N))
_WR = csr_matrix((wr, (src, dst)), shape=(N, N))

tes = pd.read_sql("select t.tes_id, t.nama_tes, t.zona, t.kapasitas, t.lat, t.lon, f.d_pantai_m, f.snap_dist_m, f.nearest_node_id "
                  "from tb_tes t join tb_fasilitas_info f on f.facility_id = t.tes_id", c)
tx, ty = Transformer.from_crs("EPSG:4326", "EPSG:32747", always_xy=True).transform(tes.lon.values, tes.lat.values)
merah = np.flatnonzero(nd.is_safe.to_numpy() == 0)
ar = np.arange(N)


def eta_pohon(pred):
    nh = pred.copy(); ok = nh >= 0
    w = np.zeros(N); w[ok] = np.asarray(_WR[ar[ok], nh[ok]]).ravel()
    ptr = np.where(ok, nh, ar)
    while True:
        w = w + np.where(ptr != ar, w[ptr], 0.0); p2 = ptr[ptr]
        if np.array_equal(p2, ptr): return w
        ptr = p2


K = len(tes); ETA = np.full((K, len(merah)), np.inf); JB = np.zeros((K, len(merah)), bool)
for k, r in tes.iterrows():
    s = idx[r.nearest_node_id]
    bt, pt = dijkstra(W_t, indices=s, return_predecessors=True)
    bd, pd_ = dijkstra(W_d, indices=s, return_predecessors=True)
    pakai = np.isfinite(bt); pred = np.where(pakai, pt, pd_)
    eta = eta_pohon(pred) + menit(r.snap_dist_m)
    jarak = np.hypot(x[merah] - tx[k], y[merah] - ty[k])
    with np.errstate(divide="ignore", invalid="ignore"):
        boleh = (jarak <= DEKAT) | ((r.d_pantai_m - dp[merah]) / jarak > SIN)
    sampai = np.isfinite(np.where(pakai, bt, bd))[merah]
    ETA[k] = np.where(boleh & sampai, eta[merah], np.inf); JB[k] = ~pakai[merah]

ber = tes.kapasitas.notna().to_numpy()
dem = nd.demand_jiwa.to_numpy()[merah]; kel = nd.kelurahan.to_numpy()[merah]
hasil = {}
for nama, mask in (("semua_244", np.ones(K, bool)), ("berkapasitas_167", ber)):
    E = ETA[mask]
    hasil[nama] = dict(ada=np.isfinite(E).any(0), s15=(E <= 15).any(0), s20=(E <= 20).any(0),
                       n_kand15=(E <= 15).sum(0), n_kand=np.isfinite(E).sum(0))
a, b = hasil["semua_244"], hasil["berkapasitas_167"]
hilang = a["ada"] & ~b["ada"]; hilang15 = a["s15"] & ~b["s15"]
fmt = lambda v: f"{v:,.0f}".replace(",", ".")
print(f"Simpul zona merah: {len(merah):,}; jiwa di simpul merah: {fmt(dem.sum())}")
for nama, h in hasil.items():
    print(f"  {nama:17s}: punya >=1 TES lolos arah {h['ada'].sum():,} simpul / {fmt(dem[h['ada']].sum())} jiwa | "
          f"TES <= 15 mnt {h['s15'].sum():,} / {fmt(dem[h['s15']].sum())} jiwa | <= 20 mnt {h['s20'].sum():,} / {fmt(dem[h['s20']].sum())} jiwa | "
          f"median kandidat <= 15 mnt (simpul yang punya) {np.median(h['n_kand15'][h['s15']]) if h['s15'].any() else 0:.0f}")
print(f"Kehilangan SEMUA TES karena skenario: {hilang.sum():,} simpul, {fmt(dem[hilang].sum())} jiwa")
print(f"Kehilangan TES <= 15 menit karena skenario: {hilang15.sum():,} simpul, {fmt(dem[hilang15].sum())} jiwa")
df = pd.DataFrame({"kelurahan": kel, "jiwa": dem, "hilang_semua": hilang, "hilang_15": hilang15,
                   "tanpa_tes_167": ~b["ada"], "tanpa_tes15_167": ~b["s15"]})
g = df.groupby("kelurahan").apply(lambda d: pd.Series({
    "simpul_merah": len(d), "jiwa": d.jiwa.sum(),
    "simpul_hilang_semua_tes": d.hilang_semua.sum(), "jiwa_hilang_semua_tes": d.jiwa[d.hilang_semua].sum(),
    "simpul_hilang_tes_15mnt": d.hilang_15.sum(), "jiwa_hilang_tes_15mnt": d.jiwa[d.hilang_15].sum(),
    "simpul_tanpa_tes_15mnt_167": d.tanpa_tes15_167.sum(), "jiwa_tanpa_tes_15mnt_167": d.jiwa[d.tanpa_tes15_167].sum()}),
    include_groups=False).sort_values("jiwa_hilang_tes_15mnt", ascending=False)
g.round(0).astype(int).to_csv(sys.argv[2], encoding="utf-8")
print(g[g.jiwa_hilang_tes_15mnt > 0].round(0).astype(int).head(15).to_string())
# Kelurahan (bertitik merah) tanpa TES berkapasitas di wilayahnya
tk = tes.groupby("zona").kapasitas.agg(semua="size", berkap="count")
kel_merah = set(df.kelurahan.dropna().str.upper())
tk.index = tk.index.str.upper()
nol = sorted(k for k in kel_merah if k in tk.index and tk.loc[k, "berkap"] == 0)
print("Kelurahan bertitik merah yang punya TES tetapi tidak satu pun berkapasitas:", len(nol), nol)
print("Kapasitas total 167 TES:", fmt(tes.kapasitas.sum()), "jiwa")

# --- TEA dan zona hijau v2: siapa yang masih punya tujuan sempat walau TES-nya hilang
tea = pd.read_sql("select t.tea_id, t.lat, t.lon, f.d_pantai_m, f.snap_dist_m, t.nearest_node_id from tb_tea t "
                  "join tb_fasilitas_info f on f.facility_id = t.tea_id", c)
ax_, ay_ = Transformer.from_crs("EPSG:4326", "EPSG:32747", always_xy=True).transform(tea.lon.values, tea.lat.values)
ETA_TEA = np.full((len(tea), len(merah)), np.inf)
for k, r in tea.iterrows():
    s = idx[r.nearest_node_id]
    bt, pt = dijkstra(W_t, indices=s, return_predecessors=True)
    bd, pd_ = dijkstra(W_d, indices=s, return_predecessors=True)
    pakai = np.isfinite(bt); pred = np.where(pakai, pt, pd_)
    eta = eta_pohon(pred) + menit(r.snap_dist_m)
    jarak = np.hypot(x[merah] - ax_[k], y[merah] - ay_[k])
    with np.errstate(divide="ignore", invalid="ignore"):
        boleh = (jarak <= DEKAT) | ((r.d_pantai_m - dp[merah]) / jarak > SIN)
    ETA_TEA[k] = np.where(boleh & np.isfinite(np.where(pakai, bt, bd))[merah], eta[merah], np.inf)
v2 = dict(q("select origin_node_id, safe_eta from tb_safe_routes_v2"))
VT = float(m["kecepatan_kolom_eta_ms"])
eta_hijau = np.array([v2.get(n, np.inf) * VT / V for n in nd.node_id.to_numpy()[merah]])
keluar = np.minimum(ETA_TEA.min(0), eta_hijau)
for batas in (15, 20, 30):
    for nama, mask in (("semua_244", np.ones(K, bool)), ("berkapasitas_167", ber)):
        t_min = np.minimum(keluar, ETA[mask].min(0))
        ok = t_min <= batas
        print(f"Tujuan apa pun <= {batas} mnt [{nama}]: {ok.sum():,} simpul / {fmt(dem[ok].sum())} jiwa "
              f"({dem[ok].sum() / dem.sum() * 100:.1f}% dari {fmt(dem.sum())}); tanpa: {(~ok).sum():,} simpul / {fmt(dem[~ok].sum())} jiwa")
hanya_tes = (keluar > 15) & hasil["semua_244"]["s15"] & ~hasil["berkapasitas_167"]["s15"]
print(f"Kehilangan SATU-SATUNYA tujuan <= 15 mnt (tak ada TEA/zona hijau <= 15): {hanya_tes.sum():,} simpul, {fmt(dem[hanya_tes].sum())} jiwa")
butuh_tes = keluar > 15
print(f"Simpul yang di t=0 harus ke TES (tak ada TEA/zona hijau <= 15 mnt): {butuh_tes.sum():,} simpul / {fmt(dem[butuh_tes].sum())} jiwa; "
      f"di antaranya punya TES 167 <= 15: {(butuh_tes & hasil['berkapasitas_167']['s15']).sum():,} / {fmt(dem[butuh_tes & hasil['berkapasitas_167']['s15']].sum())} jiwa")
dk = pd.DataFrame({"kelurahan": kel, "jiwa": dem, "h": hanya_tes}).groupby("kelurahan").apply(
    lambda d: pd.Series({"simpul": d.h.sum(), "jiwa": d.jiwa[d.h].sum()}), include_groups=False)
dk = dk[dk.simpul > 0].sort_values("jiwa", ascending=False).round(0).astype(int)
dk.to_csv(sys.argv[2].replace(".csv", "_hilang_satu2nya.csv"), encoding="utf-8")
print(dk.to_string())
