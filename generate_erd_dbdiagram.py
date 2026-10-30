"""
Gambar ERD gaya dbdiagram.io dari docs/siaga_padang_erd.dbml.

Tabel putih dengan header berwarna per TableGroup, semua kolom (nama kiri, tipe kanan), garis relasi
siku yang menempel ke baris kolom, label kardinalitas 1 / *.

Garis tidak pernah berimpit: setiap relasi punya jalur vertikal sendiri di kanal antarkolom, dan baris yang
menerima banyak garis dipertinggi supaya tiap garis punya titik masuk sendiri. Urutan jalur dan sisi garis
dalam satu kolom dicari dengan pencarian lokal yang meminimalkan persilangan; persilangan yang tersisa
digambar dengan lompatan kecil.

Keluaran: docs/erd/erd_siaga_padang_dbdiagram.svg dan .png (Chrome/Edge headless, skala 2x).
Pemakaian: env\\Scripts\\python.exe generate_erd_dbdiagram.py
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

import numpy as np
from PIL import ImageFont

sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

DBML_PATH = os.path.join("docs", "siaga_padang_erd.dbml")
OUT_DIR = os.path.join("docs", "erd")
NAMA = "erd_siaga_padang_dbdiagram"
BROWSER = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]

# Tata letak: kolom kiri ke kanan, tabel atas ke bawah. Disusun supaya hampir semua relasi menghubungkan
# kolom yang bersebelahan (tb_nodes di tengah karena dirujuk 23 relasi).
TATA = [
    ["tb_route_shares", "tb_fasilitas_info", "v_fasilitas_evakuasi"],
    ["tb_routes", "tb_tes", "tb_tes_next", "tb_tea_next", "tb_tea_routes", "tb_tea"],
    ["tb_bridge_edges", "tb_edges", "tb_nodes", "tb_jalur_resmi", "tb_node_info"],
    ["tb_safe_routes_v2", "tb_safe_next_v2", "tb_safe_routes", "tb_safe_next", "tb_metadata"],
    ["tb_safe_zones", "tb_inundation_zones", "tb_kelurahan_info"],
]
# Jarak tambahan di atas tabel (px) untuk merapatkan garis.
GESER = {"tb_bridge_edges": 120, "tb_safe_routes_v2": 200, "tb_safe_zones": 330, "tb_route_shares": 160,
         "tb_metadata": 60}

WARNA_GRUP = {
    "Graf_Jalan": "#2f5d8a",
    "Rute_TES_Vertikal": "#b45309",
    "Rute_TEA_Horizontal": "#2f7d4f",
    "Rute_Zona_Aman": "#0f7285",
    "Zona_Spasial": "#a83232",
    "Penugasan": "#6b46a8",
    "Info_V4_Tambahan": "#5b6170",
}
GARIS, TEKS, TEKS_REDUP, BATAS = "#7d8aa0", "#1f2733", "#8a93a3", "#d5d9e0"

FONT = "Segoe UI, Inter, Arial, sans-serif"
UK_KOLOM, UK_TIPE, UK_HEADER = 12.5, 11, 13
ROW, HEAD, PAD = 24, 32, 12
GAP_Y, MARGIN = 36, 40
LANE, PORT = 12, 14          # jarak antarjalur vertikal; jarak antartitik masuk dalam satu baris
TEPI_KANAL = 22              # jarak jalur terluar ke tepi tabel
KUNCI_W = 34                 # lebar kolom penanda PK / FK di kiri nama kolom
WARNA_PK, WARNA_FK = "#b7791f", "#2f5d8a"
_ft = {}


def lebar(teks, uk, tebal=False):
    kunci = (uk, tebal)
    if kunci not in _ft:
        _ft[kunci] = ImageFont.truetype("C:/Windows/Fonts/" + ("segoeuib.ttf" if tebal else "segoeui.ttf"), uk * 4)
    return _ft[kunci].getlength(teks) / 4


def e(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- baca DBML
def baca_dbml(path):
    teks = open(path, encoding="utf-8").read()
    tabel, grup, refs = {}, {}, []
    for m in re.finditer(r"^Table (\w+) \{\n(.*?)^\}", teks, re.M | re.S):
        nama, isi = m.group(1), m.group(2)
        kolom, pk_gabung = [], set()
        isi_idx = re.search(r"indexes \{(.*?)\}", isi, re.S)
        if isi_idx:
            for g in re.finditer(r"\(([^)]*)\)\s*\[pk\]", isi_idx.group(1)):
                pk_gabung |= {c.strip() for c in g.group(1).split(",")}
            isi = isi[:isi_idx.start()]
        for baris in isi.splitlines():
            b = re.match(r"\s+(\w+) (\w+)(?: \[(.*)\])?\s*$", baris)
            if not b:
                continue
            kol, tipe, atr = b.group(1), b.group(2), b.group(3) or ""
            atr = re.sub(r'note: "[^"]*"', "", atr)
            kolom.append({"nama": kol, "tipe": tipe.lower(), "pk": "pk" in atr or kol in pk_gabung,
                          "nn": "not null" in atr})
            r = re.search(r"ref: ([<>\-]+) (\w+)\.(\w+)", atr)
            if r:
                refs.append((nama, kol, r.group(1), r.group(2), r.group(3)))
        tabel[nama] = kolom
    for m in re.finditer(r"^TableGroup (\w+) \{\n(.*?)^\}", teks, re.M | re.S):
        for t in m.group(2).split():
            grup[t] = m.group(1)
    for m in re.finditer(r"^Ref: (\w+)\.(\w+) ([<>\-]+) (\w+)\.(\w+)", teks, re.M):
        refs.append(m.groups())
    return tabel, grup, refs


# ---------------------------------------------------------------- geometri
class Diagram:
    def __init__(self, tabel, refs):
        self.tabel = tabel
        hilang = set(tabel) - {t for k in TATA for t in k}
        assert not hilang, f"tabel belum ditata: {hilang}"
        self.kol = {t: i for i, k in enumerate(TATA) for t in k}
        self.lebar_kol = [max(self._lebar_tabel(t) for t in k) for k in TATA]
        self.rel = []
        for (ta, ka, op, tb, kb) in refs:
            kar = {">": ("*", "1"), "<": ("1", "*"), "-": ("1", "1"), "<>": ("*", "*")}[op]
            self.rel.append({"a": (ta, ka), "b": (tb, kb), "kar": kar})
        # FK = kolom perujuk (sisi kiri ref DBML; untuk "<" sisi kanan)
        self.fk = {(ta, ka) if op != "<" else (tb, kb) for (ta, ka, op, tb, kb) in refs}

    def _lebar_tabel(self, t):
        w_head = lebar(t, UK_HEADER, True) + 2 * PAD + (34 if t.startswith("v_") else 0)
        w_baris = max(KUNCI_W + lebar(c["nama"], UK_KOLOM, c["pk"]) + 18 + lebar(c["tipe"], UK_TIPE) + 2 * PAD
                      for c in self.tabel[t])
        return max(w_head, w_baris)

    @staticmethod
    def kanal(i_kol, sisi):  # 0 = kiri kolom 0; k = antara kolom k-1 dan k
        return i_kol if sisi == "L" else i_kol + 1

    def sisi_dan_jalur(self, sisi_u):
        """Sisi tiap ujung relasi dan kunci jalur per kanal."""
        ujung, jalur = [], defaultdict(list)
        for ri, r in enumerate(self.rel):
            ia, ib = self.kol[r["a"][0]], self.kol[r["b"][0]]
            if ia == ib:
                sa = sb = sisi_u[ri]
                jalur[self.kanal(ia, sa)].append((ri, "u"))
            else:
                sa, sb = ("R", "L") if ia < ib else ("L", "R")
                if abs(ia - ib) == 1:
                    jalur[self.kanal(ia, sa)].append((ri, "m"))
                else:
                    jalur[self.kanal(ia, sa)].append((ri, "a"))
                    jalur[self.kanal(ib, sb)].append((ri, "b"))
            ujung.append((sa, sb))
        return ujung, jalur

    def bangun(self, sisi_u, urutan):
        """Geometri lengkap: posisi tabel, tinggi baris, titik masuk, dan polyline tiap relasi."""
        tabel, rel = self.tabel, self.rel
        ujung, jalur = self.sisi_dan_jalur(sisi_u)
        # urutan jalur per kanal: pakai urutan yang diberikan, kunci baru ditambahkan di belakang
        urut = {}
        for kn, kunci in jalur.items():
            lama = [k for k in urutan.get(kn, []) if k in kunci]
            urut[kn] = lama + [k for k in kunci if k not in lama]

        # titik masuk per (tabel, kolom, sisi)
        port = defaultdict(list)
        for ri, r in enumerate(rel):
            sa, sb = ujung[ri]
            port[r["a"] + (sa,)].append((ri, "a"))
            port[r["b"] + (sb,)].append((ri, "b"))
        tinggi_baris = {}
        for t, kolom in tabel.items():
            for c in kolom:
                n = max(len(port.get((t, c["nama"], s), [])) for s in "LR")
                tinggi_baris[(t, c["nama"])] = max(ROW, n * PORT + 10)

        # posisi tabel
        n_kanal = len(TATA) + 1
        lebar_kanal = []
        for kn in range(n_kanal):
            n = len(urut.get(kn, []))
            if kn in (0, n_kanal - 1):
                lebar_kanal.append(MARGIN if n == 0 else 2 * TEPI_KANAL + LANE * (n - 1))
            else:
                lebar_kanal.append(max(70, 2 * TEPI_KANAL + LANE * (n - 1)))
        x_kol, x = [], MARGIN + lebar_kanal[0]
        for i, w in enumerate(self.lebar_kol):
            x_kol.append(x)
            x += w + lebar_kanal[i + 1]
        W = x + MARGIN
        pos, baris_y = {}, {}
        for i, k in enumerate(TATA):
            y = MARGIN
            for t in k:
                y += GESER.get(t, 0)
                y0 = y
                y += HEAD
                for c in tabel[t]:
                    baris_y[(t, c["nama"])] = (y, tinggi_baris[(t, c["nama"])])
                    y += tinggi_baris[(t, c["nama"])]
                pos[t] = (x_kol[i], y0, self.lebar_kol[i], y - y0)
                y += GAP_Y
        H = max(y + h for (x, y, w, h) in pos.values()) + MARGIN + 34

        def x_kanal(kn):
            kiri = x_kol[kn - 1] + self.lebar_kol[kn - 1] if kn > 0 else MARGIN
            kanan = x_kol[kn] if kn < len(TATA) else W - MARGIN
            return kiri, kanan

        x_jalur = {}
        for kn, daftar in urut.items():
            kiri, kanan = x_kanal(kn)
            if kn == 0:
                x0 = kanan - TEPI_KANAL - LANE * (len(daftar) - 1)
            elif kn == len(TATA):
                x0 = kiri + TEPI_KANAL
            else:
                x0 = (kiri + kanan) / 2 - LANE * (len(daftar) - 1) / 2
            for i, k in enumerate(daftar):
                x_jalur[k] = x0 + LANE * i

        def y_tengah(t, c):
            y, h = baris_y[(t, c)]
            return y + h / 2

        # y titik masuk: dalam satu baris diurutkan menurut y ujung seberangnya (mengurangi silang)
        y_port = {}
        for (t, c, s), daftar in port.items():
            def kunci(p):
                ri, ae = p
                lawan = rel[ri]["b" if ae == "a" else "a"]
                return (y_tengah(*lawan), ri)
            daftar = sorted(daftar, key=kunci)
            yc = y_tengah(t, c)
            for i, p in enumerate(daftar):
                y_port[p] = yc + (i - (len(daftar) - 1) / 2) * PORT

        # koridor untuk relasi yang melompati kolom: y di celah antartabel yang bebas di semua kolom yang dilewati
        koridor_y, celah_pakai = {}, defaultdict(list)
        for ri, r in enumerate(rel):
            ia, ib = self.kol[r["a"][0]], self.kol[r["b"][0]]
            if abs(ia - ib) <= 1:
                continue
            lewat = range(min(ia, ib) + 1, max(ia, ib))
            calon = sorted({pos[t][1] - GAP_Y / 2 for c in lewat for t in TATA[c]} |
                           {pos[t][1] + pos[t][3] + GAP_Y / 2 for c in lewat for t in TATA[c]})

            def bebas(y):
                return all(not (pos[t][1] - 10 <= y <= pos[t][1] + pos[t][3] + 10) for c in lewat for t in TATA[c])
            ya, yb = y_port[(ri, "a")], y_port[(ri, "b")]
            yk = min((y for y in calon if bebas(y)), key=lambda y: abs(y - ya) + abs(y - yb))
            celah_pakai[yk].append(ri)
            koridor_y[ri] = yk
        for yk, daftar in celah_pakai.items():
            for i, ri in enumerate(sorted(daftar)):
                koridor_y[ri] = yk + (i - (len(daftar) - 1) / 2) * 10

        def tepi(t, s):
            x, y, w, h = pos[t]
            return x if s == "L" else x + w

        poly = []
        for ri, r in enumerate(rel):
            sa, sb = ujung[ri]
            xa, ya = tepi(r["a"][0], sa), y_port[(ri, "a")]
            xb, yb = tepi(r["b"][0], sb), y_port[(ri, "b")]
            if (ri, "a") in x_jalur:
                xla, xlb, yk = x_jalur[(ri, "a")], x_jalur[(ri, "b")], koridor_y[ri]
                titik = [(xa, ya), (xla, ya), (xla, yk), (xlb, yk), (xlb, yb), (xb, yb)]
            else:
                xl = x_jalur[(ri, "u")] if (ri, "u") in x_jalur else x_jalur[(ri, "m")]
                titik = [(xa, ya), (xl, ya), (xl, yb), (xb, yb)]
            poly.append(titik)
        return {"pos": pos, "baris_y": baris_y, "poly": poly, "ujung": ujung, "urut": urut, "W": W, "H": H}


def segmen(poly):
    """Segmen horizontal (y, x1, x2, rel) dan vertikal (x, y1, y2, rel) dari semua polyline."""
    hs, vs = [], []
    for ri, titik in enumerate(poly):
        for (x0, y0), (x1, y1) in zip(titik, titik[1:]):
            if abs(y0 - y1) < 1e-6 and abs(x0 - x1) > 1e-6:
                hs.append((y0, min(x0, x1), max(x0, x1), ri))
            elif abs(x0 - x1) < 1e-6 and abs(y0 - y1) > 1e-6:
                vs.append((x0, min(y0, y1), max(y0, y1), ri))
    return np.array(hs, dtype=float), np.array(vs, dtype=float)


def biaya(poly):
    """Persilangan + hukuman besar untuk garis yang berimpit atau saling menyentuh."""
    H, V = segmen(poly)
    eps = 0.5
    hy, hx1, hx2, hr = (H[:, i][:, None] for i in range(4))
    vx, vy1, vy2, vr = (V[:, i][None, :] for i in range(4))
    beda = hr != vr
    silang = (hx1 + eps < vx) & (vx < hx2 - eps) & (vy1 + eps < hy) & (hy < vy2 - eps) & beda
    sentuh = (hx1 - eps <= vx) & (vx <= hx2 + eps) & (vy1 - eps <= hy) & (hy <= vy2 + eps) & beda & ~silang
    imp = 0
    for A in (H, V):  # segmen sejajar yang berimpit
        a0, a1, a2, ar = (A[:, i] for i in range(4))
        sama = (np.abs(a0[:, None] - a0[None, :]) < 3) & (ar[:, None] != ar[None, :])
        tumpang = (np.minimum(a2[:, None], a2[None, :]) - np.maximum(a1[:, None], a1[None, :])) > -2
        imp += np.sum(np.triu(sama & tumpang, 1))
    return int(silang.sum()) + 30 * int(sentuh.sum()) + 200 * int(imp)


def optimasi(d, n_ulang=12):
    """Pencarian lokal dari beberapa titik awal (deterministik); hasil dengan biaya terkecil dipakai."""
    rng = np.random.default_rng(0)
    terbaik = None
    for ulang in range(n_ulang):
        hasil = _optimasi_sekali(d, rng if ulang else None)
        if terbaik is None or hasil[2] < terbaik[2]:
            terbaik = hasil
    return terbaik


def _optimasi_sekali(d, rng):
    """Pencarian lokal: tukar urutan dua jalur dalam satu kanal, atau balik sisi relasi sekolom."""
    sekolom = [ri for ri, r in enumerate(d.rel) if d.kol[r["a"][0]] == d.kol[r["b"][0]]]
    sisi_u = {ri: ("R" if rng is None or rng.random() < 0.5 else "L") for ri in sekolom}
    g = d.bangun(sisi_u, {})
    # urutan awal: jalur dengan rentang vertikal pendek paling dekat ke tabelnya (atau acak)
    urutan = {}
    for kn, daftar in g["urut"].items():
        def rentang(k):
            ys = [p[1] for p in g["poly"][k[0]]]
            return max(ys) - min(ys)
        urutan[kn] = sorted(daftar, key=rentang) if rng is None else [daftar[i] for i in rng.permutation(len(daftar))]
    terbaik = biaya(d.bangun(sisi_u, urutan)["poly"])
    membaik = True
    while membaik:
        membaik = False
        for ri in list(sisi_u):
            coba = dict(sisi_u)
            coba[ri] = "L" if sisi_u[ri] == "R" else "R"
            b = biaya(d.bangun(coba, urutan)["poly"])
            if b < terbaik:
                terbaik, sisi_u, membaik = b, coba, True
                urutan = d.bangun(sisi_u, urutan)["urut"]
        for kn in list(urutan):
            daftar = urutan[kn]
            for i in range(len(daftar)):
                for j in range(i + 1, len(daftar)):
                    coba = list(daftar)
                    coba[i], coba[j] = coba[j], coba[i]
                    b = biaya(d.bangun(sisi_u, {**urutan, kn: coba})["poly"])
                    if b < terbaik:
                        terbaik, membaik = b, True
                        urutan[kn] = daftar = coba
    return sisi_u, urutan, terbaik


# ---------------------------------------------------------------- gambar
def jalur_svg(titik, lompat, rad=6, r_lompat=4):
    """Polyline siku dengan sudut membulat; lompat = {indeks segmen: [x persilangan]} untuk segmen horizontal."""
    p = [titik[0]]
    for q in titik[1:]:
        if abs(q[0] - p[-1][0]) > 0.01 or abs(q[1] - p[-1][1]) > 0.01:
            p.append(q)
    # sudut membulat: titik masuk/keluar tiap sudut
    masuk, keluar = [p[0]], [p[0]]
    for i in range(1, len(p) - 1):
        (x0, y0), (x1, y1), (x2, y2) = p[i - 1], p[i], p[i + 1]
        r1 = min(rad, (abs(x1 - x0) + abs(y1 - y0)) / 2, (abs(x2 - x1) + abs(y2 - y1)) / 2)
        u0, u2 = _arah(x0, y0, x1, y1), _arah(x1, y1, x2, y2)
        masuk.append((x1 - u0[0] * r1, y1 - u0[1] * r1))
        keluar.append((x1 + u2[0] * r1, y1 + u2[1] * r1))
    masuk.append(p[-1])
    d = f"M{p[0][0]:.1f},{p[0][1]:.1f}"
    for i in range(len(p) - 1):
        (xs, ys), (xe, ye) = keluar[i], masuk[i + 1]
        if abs(ys - ye) < 0.01:  # horizontal: sisipkan lompatan
            arah = 1 if xe > xs else -1
            for xc in sorted(lompat.get((round(p[i][1], 1), min(p[i][0], p[i + 1][0])), []), key=lambda v: v * arah):
                if min(xs, xe) + r_lompat < xc < max(xs, xe) - r_lompat:
                    d += (f" L{xc - arah * r_lompat:.1f},{ys:.1f}"
                          f" A{r_lompat},{r_lompat} 0 0 {1 if arah > 0 else 0} {xc + arah * r_lompat:.1f},{ys:.1f}")
        d += f" L{xe:.1f},{ye:.1f}"
        if i + 1 < len(p) - 1:
            d += f" Q{p[i + 1][0]:.1f},{p[i + 1][1]:.1f} {keluar[i + 1][0]:.1f},{keluar[i + 1][1]:.1f}"
    return d


def _arah(x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    n = (dx * dx + dy * dy) ** 0.5 or 1
    return dx / n, dy / n


def gambar_tabel(t, kolom, x, y, w, h, warna, baris_y, fk):
    o = [f'<g>',
         f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="5" fill="#fff" '
         f'stroke="{BATAS}" filter="url(#bayang)"/>',
         f'<path d="M{x:.1f},{y + HEAD:.1f} V{y + 5:.1f} Q{x:.1f},{y:.1f} {x + 5:.1f},{y:.1f} '
         f'H{x + w - 5:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + 5:.1f} V{y + HEAD:.1f} Z" fill="{warna}"/>',
         f'<text x="{x + PAD:.1f}" y="{y + HEAD / 2 + 4.5:.1f}" font-size="{UK_HEADER}" font-weight="700" '
         f'fill="#fff">{e(t)}</text>']
    if t.startswith("v_"):
        o.append(f'<text x="{x + w - PAD:.1f}" y="{y + HEAD / 2 + 4:.1f}" font-size="11" fill="#fff" '
                 f'fill-opacity="0.8" text-anchor="end">view</text>')
    for i, c in enumerate(kolom):
        yb, hb = baris_y[(t, c["nama"])]
        if i:
            o.append(f'<line x1="{x + 1:.1f}" x2="{x + w - 1:.1f}" y1="{yb:.1f}" y2="{yb:.1f}" stroke="#eef0f3"/>')
        ty = yb + hb / 2 + 4.3
        tebal = ' font-weight="700"' if c["pk"] else ""
        tanda = [("PK", WARNA_PK)] * c["pk"] + [("FK", WARNA_FK)] * ((t, c["nama"]) in fk)
        for j, (lbl, wr) in enumerate(tanda):
            o.append(f'<text x="{x + PAD + j * 16:.1f}" y="{ty - 0.8:.1f}" font-size="9" font-weight="700" '
                     f'letter-spacing="0.3" fill="{wr}">{lbl}</text>')
        o.append(f'<text x="{x + PAD + KUNCI_W:.1f}" y="{ty:.1f}" font-size="{UK_KOLOM}"{tebal} fill="{TEKS}">'
                 f'{e(c["nama"])}</text>')
        o.append(f'<text x="{x + w - PAD:.1f}" y="{ty - 0.3:.1f}" font-size="{UK_TIPE}" fill="{TEKS_REDUP}" '
                 f'text-anchor="end">{e(c["tipe"])}</text>')
    o.append("</g>")
    return "".join(o)


def main():
    tabel, grup, refs = baca_dbml(DBML_PATH)
    d = Diagram(tabel, refs)
    sisi_u, urutan, nilai = optimasi(d)
    g = d.bangun(sisi_u, urutan)
    pos, poly, W, H = g["pos"], g["poly"], g["W"], g["H"]
    Hs, Vs = segmen(poly)
    n_silang = int(sum(1 for h in Hs for v in Vs
                       if h[3] != v[3] and h[1] < v[0] < h[2] and v[1] < h[0] < v[2]))

    # lompatan: segmen horizontal melompati segmen vertikal relasi lain yang memotongnya
    lompat = defaultdict(list)
    for h in Hs:
        for v in Vs:
            if h[3] != v[3] and h[1] + 1 < v[0] < h[2] - 1 and v[1] + 1 < h[0] < v[2] - 1:
                lompat[(round(h[0], 1), h[1])].append(v[0])

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONT}">',
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         '<defs><filter id="bayang" x="-5%" y="-5%" width="110%" height="115%">'
         '<feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#0b1220" flood-opacity="0.10"/></filter></defs>']
    o.append(f'<g fill="none" stroke="{GARIS}" stroke-width="1.3" stroke-linejoin="round">')
    for titik in poly:
        o.append(f'<path d="{jalur_svg(titik, lompat)}"/>')
    o.append("</g>")
    for t, (x, y, w, h) in pos.items():
        o.append(gambar_tabel(t, tabel[t], x, y, w, h, WARNA_GRUP[grup[t]], g["baris_y"], d.fk))
    # kardinalitas di atas garis, tepat di luar tepi tabel
    o.append('<g font-size="10.5" font-weight="700" fill="#4a5568">')
    for ri, (titik, r) in enumerate(zip(poly, d.rel)):
        for (x, y), s, lbl in ((titik[0], g["ujung"][ri][0], r["kar"][0]), (titik[-1], g["ujung"][ri][1], r["kar"][1])):
            dx, anchor = (5, "start") if s == "R" else (-5, "end")
            o.append(f'<text x="{x + dx:.1f}" y="{y - 3:.1f}" text-anchor="{anchor}">{lbl}</text>')
    o.append("</g>")

    ly = H - MARGIN + 2
    lx = MARGIN
    for grp, warna in WARNA_GRUP.items():
        o.append(f'<rect x="{lx}" y="{ly - 9}" width="11" height="11" rx="2" fill="{warna}"/>')
        label = grp.replace("_", " ")
        o.append(f'<text x="{lx + 16}" y="{ly}" font-size="12" fill="{TEKS}">{e(label)}</text>')
        lx += 16 + lebar(label, 12) + 22
    for lbl, wr, arti in (("PK", WARNA_PK, "primary key"), ("FK", WARNA_FK, "foreign key (logis)")):
        o.append(f'<text x="{lx}" y="{ly}" font-size="10" font-weight="700" fill="{wr}">{lbl}</text>')
        o.append(f'<text x="{lx + 18}" y="{ly}" font-size="12" fill="{TEKS}">{arti}</text>')
        lx += 18 + lebar(arti, 12) + 22
    catatan = "1 / * = kardinalitas  ·  relasi logis (SQLite tanpa foreign key)  ·  sumber: siaga_padang_erd.dbml"
    o.append(f'<text x="{W - MARGIN}" y="{ly}" font-size="12" fill="{TEKS_REDUP}" text-anchor="end">{e(catatan)}</text>')
    o.append("</svg>")

    os.makedirs(OUT_DIR, exist_ok=True)
    svg = os.path.join(OUT_DIR, NAMA + ".svg")
    with open(svg, "w", encoding="utf-8") as f:
        f.write("\n".join(o))
    ke_png(svg, os.path.join(OUT_DIR, NAMA + ".png"), W, H)
    print(f"{svg} ({W:.0f}x{H:.0f}), {len(tabel)} tabel, {len(refs)} relasi, "
          f"{n_silang} persilangan, nilai biaya {nilai} (0 berimpit bila = persilangan)")


def ke_png(svg_path, png_path, W, H):
    browser = next((b for b in BROWSER if os.path.exists(b)), None)
    if not browser:
        print("  [lewati PNG] Chrome/Edge tidak ditemukan")
        return
    wadah = os.path.abspath(svg_path) + ".html"
    with open(wadah, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html><body style='margin:0;background:#fff'>"
                f"<img src='{os.path.basename(svg_path)}' width='{W:.0f}' height='{H:.0f}'></body></html>")
    try:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size={W:.0f},{H:.0f}", f"--screenshot={os.path.abspath(png_path)}",
                        "file:///" + wadah.replace(os.sep, "/")], check=True, capture_output=True, timeout=120)
    finally:
        os.remove(wadah)


if __name__ == "__main__":
    main()
