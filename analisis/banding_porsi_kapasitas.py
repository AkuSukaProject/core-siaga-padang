r"""Banding porsi TES: skenario 167 TES berkapasitas tercatat (isi DB 2026.10.18) vs skenario estimasi daya tampung
(244 TES; 77 TES tanpa data diisi estimasi tb_fasilitas_info.kapasitas: jejak bangunan RTRW atau median TES BPBD).
Aturan kelompok dan program linear meniru build_db.py (bagian porsi tujuan): pada t = 0 dari simpang, 0,894 m/s,
batas sempat 15 menit; kandidat dihitung ulang dari DB seperti analisis/skenario_tes_berkapasitas.py.
Pemakaian: env\Scripts\python.exe analisis\banding_porsi_kapasitas.py <ranah_siaga_v4.db> <folder_keluaran>
Contoh: ... analisis\banding_porsi_kapasitas.py hasil_build\ranah_siaga_v4.db analisis\output\banding_porsi_kapasitas\2026.10.18"""
import os, sqlite3, sys
import numpy as np, pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import dijkstra
from pyproj import Transformer

sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(sys.argv[1]); OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
q = lambda s: c.execute(s).fetchall()
m = dict(q("select kunci, nilai from tb_metadata"))
V = float(m["kecepatan_jalan_ms"]); VT = float(m["kecepatan_kolom_eta_ms"]); BATAS = float(m["batas_sempat_menit"])
TOL = float(m["toleransi_mendekat_pantai_m"]); PEN = float(m["penalti_mendekat_pantai"])
BOBOT = float(m["bobot_per_meter_mendekat_pantai"]); PJEMB = float(m["penalti_jembatan"]); FRESMI = float(m["jalur_resmi_faktor"])
SIN, DEKAT = float(m["arah_min_sin"]), float(m["arah_jarak_dekat_m"])
menit = lambda x: x / V / 60.0
fmt = lambda v: f"{v:,.0f}".replace(",", ".")
ke_utm = Transformer.from_crs("EPSG:4326", "EPSG:32747", always_xy=True).transform

nd = pd.read_sql("select n.node_id, n.lat, n.lon, n.is_safe, i.d_pantai_m, i.demand_jiwa "
                 "from tb_nodes n join tb_node_info i using(node_id)", c)
N = len(nd); idx = {v: i for i, v in enumerate(nd.node_id)}
x, y = ke_utm(nd.lon.values, nd.lat.values)
dp = nd.d_pantai_m.to_numpy()

e = pd.read_sql("select edge_id, u, v, length from tb_edges", c)
e["jemb"] = e.edge_id.isin({r[0] for r in q("select edge_id from tb_bridge_edges")})
e["a"], e["b"] = np.minimum(e.u, e.v), np.maximum(e.u, e.v)
e = e.sort_values("length").drop_duplicates(["a", "b"])
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
merah = np.flatnonzero(nd.is_safe.to_numpy() == 0)
dem = nd.demand_jiwa.to_numpy()[merah]
ar = np.arange(N)


def eta_pohon(pred):
    nh = pred.copy(); ok = nh >= 0
    w = np.zeros(N); w[ok] = np.asarray(_WR[ar[ok], nh[ok]]).ravel()
    ptr = np.where(ok, nh, ar)
    while True:
        w = w + np.where(ptr != ar, w[ptr], 0.0); p2 = ptr[ptr]
        if np.array_equal(p2, ptr): return w
        ptr = p2


def kandidat(fas):
    """ETA (menit, 0,894 m/s, termasuk snap) dari tiap simpul merah ke tiap fasilitas yang lolos arah; dan apakah lewat jembatan."""
    fx, fy = ke_utm(fas.lon.values, fas.lat.values)
    ETA = np.full((len(fas), len(merah)), np.inf); JB = np.zeros((len(fas), len(merah)), bool)
    for k, r in enumerate(fas.itertuples()):
        s = idx[r.nearest_node_id]
        bt, pt = dijkstra(W_t, indices=s, return_predecessors=True)
        bd, pd_ = dijkstra(W_d, indices=s, return_predecessors=True)
        pakai = np.isfinite(bt); pred = np.where(pakai, pt, pd_)
        eta = eta_pohon(pred) + menit(r.snap_dist_m)
        jarak = np.hypot(x[merah] - fx[k], y[merah] - fy[k])
        with np.errstate(divide="ignore", invalid="ignore"):
            boleh = (jarak <= DEKAT) | ((r.d_pantai_m - dp[merah]) / jarak > SIN)
        ETA[k] = np.where(boleh & np.isfinite(np.where(pakai, bt, bd))[merah], eta[merah], np.inf)
        JB[k] = ~pakai[merah]
    return ETA, JB


tes = pd.read_sql("select t.tes_id, t.nama_tes, t.zona, t.kapasitas, f.kapasitas as kap_estimasi, f.kapasitas_sumber, "
                  "t.lat, t.lon, f.d_pantai_m, f.snap_dist_m, f.nearest_node_id "
                  "from tb_tes t join tb_fasilitas_info f on f.facility_id = t.tes_id order by t.rowid", c)
tea = pd.read_sql("select t.tea_id, t.lat, t.lon, f.d_pantai_m, f.snap_dist_m, t.nearest_node_id "
                  "from tb_tea t join tb_fasilitas_info f on f.facility_id = t.tea_id", c)
ETA, JB = kandidat(tes)
ETA_TEA, _ = kandidat(tea)
# Keluar zona pada t = 0: TEA utama/alternatif (tb_tea_routes) atau titik zona hijau v2.
pos_tea = {t: i for i, t in enumerate(tea.tea_id)}
tr = {o: (a, b) for o, a, b in q("select origin_node_id, nearest_tea_id, alt_tea_id from tb_tea_routes")}
v2 = dict(q("select origin_node_id, safe_eta from tb_safe_routes_v2"))
keluar = np.full(len(merah), np.inf)
for j, nid in enumerate(nd.node_id.to_numpy()[merah]):
    for t in tr.get(nid, ()):
        if t in pos_tea:
            keluar[j] = min(keluar[j], ETA_TEA[pos_tea[t], j])
    if v2.get(nid) is not None:
        keluar[j] = min(keluar[j], v2[nid] * VT / V)


def tanpa_jembatan(ks, j):
    t = ks[~JB[ks, j]]
    return t if len(t) else ks


def porsi(kap):
    """Kelompok simpang dan beban model per TES untuk kapasitas kap (NaN = tanpa kapasitas)."""
    berkap = ~np.isnan(kap)
    kel, pasangan = {}, []
    for j in range(len(merah)):
        fin = np.flatnonzero(np.isfinite(ETA[:, j]))
        if len(fin) == 0:
            kel[j] = ("tanpa_tes_lolos_arah", fin); continue
        sempat = fin[ETA[fin, j] <= BATAS]
        cap_s = tanpa_jembatan(sempat[berkap[sempat]], j) if berkap[sempat].any() else sempat[:0]
        if keluar[j] <= BATAS:
            kel[j] = ("cadangan_keluar", cap_s)
        elif len(cap_s):
            kel[j] = ("beban", cap_s); pasangan += [(j, k) for k in cap_s]
        elif len(sempat):
            kel[j] = ("tanpa_kapasitas", tanpa_jembatan(sempat, j))
        else:
            kel[j] = ("tidak_sempat", tanpa_jembatan(fin, j))
    lj = np.array([p[0] for p in pasangan]); lk = np.array([p[1] for p in pasangan])
    sj = np.unique(lj); bs = {j: i for i, j in enumerate(sj)}
    perlu = np.maximum(dem[sj], 1e-3); nv, ns = len(pasangan), len(sj)
    c_lp = np.concatenate([ETA[lk, lj] + 1e-6 * lk, np.full(ns, 1e4)])
    A_eq = coo_matrix((np.ones(nv + ns), (np.concatenate([[bs[j] for j in lj], np.arange(ns)]), np.arange(nv + ns))),
                      shape=(ns, nv + ns))
    tl = np.unique(lk); bt = {k: i for i, k in enumerate(tl)}
    A_ub = coo_matrix((np.ones(nv), ([bt[k] for k in lk], np.arange(nv))), shape=(len(tl), nv + ns))
    lp = linprog(c_lp, A_ub=A_ub.tocsr(), b_ub=kap[tl], A_eq=A_eq.tocsr(), b_eq=perlu, bounds=(0, None), method="highs")
    assert lp.status == 0, lp.message
    beban = np.bincount(lk, weights=lp.x[:nv], minlength=len(tes))
    for i, j in enumerate(sj):  # tidak tertampung -> TES sempat tercepat
        if lp.x[nv + i] > 1e-9:
            k = min(kel[j][1], key=lambda k: (ETA[k, j], k)); beban[k] += lp.x[nv + i]
    # Beban di luar LP (tanpa batas kapasitas): porsi 1 ke TES tercepat
    beban_luar = np.zeros(len(tes))
    for j, (g, ks) in kel.items():
        if g in ("tanpa_kapasitas", "tidak_sempat"):
            beban_luar[min(ks, key=lambda k: (ETA[k, j], k))] += dem[j]
    g = pd.Series({j: v[0] for j, v in kel.items()})
    return g, beban, beban_luar, lp.x[nv:].sum()


skenario = {
    "tercatat_167": tes.kapasitas.to_numpy(dtype=float),
    "estimasi_244": tes.kap_estimasi.to_numpy(dtype=float),
}
ringkas, per_tes = {}, {"tes_id": tes.tes_id, "nama": tes.nama_tes, "kelurahan": tes.zona,
                        "kapasitas_tercatat": tes.kapasitas, "kapasitas_estimasi": tes.kap_estimasi,
                        "sumber_kapasitas": tes.kapasitas_sumber}
for nama, kap in skenario.items():
    g, beban, luar, tak_tertampung = porsi(kap)
    berkap = ~np.isnan(kap)
    lebih = berkap & (beban > np.nan_to_num(kap) + 0.5)
    r = {"TES dengan kapasitas": int(berkap.sum()), "kapasitas total (jiwa)": np.nansum(kap)}
    for kel in ("beban", "cadangan_keluar", "tanpa_kapasitas", "tidak_sempat", "tanpa_tes_lolos_arah"):
        mk = (g == kel).to_numpy()
        r[f"{kel}: simpang"] = int(mk.sum()); r[f"{kel}: jiwa"] = dem[g.index[mk]].sum()
    r["TES menerima beban model"] = int((beban > 0.5).sum())
    r["TES melebihi kapasitas"] = int(lebih.sum())
    r["jiwa di atas kapasitas"] = float(np.sum(np.where(lebih, beban - np.nan_to_num(kap), 0)))
    r["jiwa ke TES tanpa kapasitas (tanpa batas)"] = float(luar[~berkap].sum())
    ringkas[nama] = r
    per_tes[f"beban_{nama}"] = (beban + np.where(berkap, 0, luar)).round(1)
    per_tes[f"rasio_{nama}"] = np.where(berkap, beban / np.where(berkap, kap, 1), np.nan).round(3)

ok15 = np.minimum(keluar, ETA.min(0)) <= BATAS
print(f"Penyebut: {fmt(dem.sum())} jiwa di {fmt(len(merah))} simpang zona merah (t = 0, dari simpang, {V} m/s)")
print(f"Tujuan layak <= {BATAS:.0f} menit (TEA/zona hijau/TES lolos arah; sama untuk kedua skenario): "
      f"{ok15.sum():,} simpang / {fmt(dem[ok15].sum())} jiwa ({dem[ok15].sum() / dem.sum() * 100:.1f}%); "
      f"tanpa: {(~ok15).sum():,} simpang / {fmt(dem[~ok15].sum())} jiwa ({dem[~ok15].sum() / dem.sum() * 100:.1f}%)".replace(",", "."))
tabel = pd.DataFrame(ringkas)
print(tabel.map(lambda v: fmt(v) if isinstance(v, (int, float, np.floating)) else v).to_string())
tabel.round(1).to_csv(os.path.join(OUT, "ringkasan.csv"), encoding="utf-8")
pd.DataFrame(per_tes).to_csv(os.path.join(OUT, "beban_per_tes.csv"), index=False, encoding="utf-8")
