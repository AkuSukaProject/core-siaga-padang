r"""Gambar 5.1 laporan: alur interaksi pengguna, proses sistem, dan tampilan aplikasi (tiga lajur).

Tata letak ditulis tangan (koordinat tetap) supaya kotak sebaris sejajar, garis tidak berimpit, dan panah balik
lewat pinggir kiri. Panah tegas = tanpa internet, putus-putus = perlu internet.
Keluaran: analisis/output/gambar_laporan/gambar_5_1_alur_interaksi.svg dan .png (Chrome/Edge headless, skala 2x).
Pemakaian: env\Scripts\python.exe analisis\gambar_alur_interaksi.py
"""
import os
import subprocess
import sys

from PIL import ImageFont

sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join("analisis", "output", "gambar_laporan", "gambar_5_1_alur_interaksi")
BROWSER = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]

FONT = "Segoe UI, Arial, sans-serif"
UK = 13.5
TEKS, REDUP, GARIS = "#1f2733", "#5b6575", "#3d4757"
# Baris (pusat y). Jarak antarbaris seragam; belah ketupat diberi ruang sedikit lebih.
Y_AB_ATAS, Y_D, Y_E, Y_G, Y_H = 150, 250, 350, 445, 550
Y_K, Y_L, Y_M, Y_O, Y_Q = 670, 770, 885, 1010, 1100
Y_R, Y_T, Y_U, Y_Z, Y_AA = 1235, 1360, 1480, 1600, 1685
LAJUR_BAWAH = Y_AA + 60
W, H = 1360, LAJUR_BAWAH + 85

# Lajur: (judul, x kiri, x kanan, warna latar)
LAJUR = [("Pengguna", 40, 380, "#f4f6f9"), ("Proses Sistem", 380, 960, "#ffffff"),
         ("Tampilan Aplikasi", 960, 1320, "#f4f6f9")]
XP, XS, XS2, XT = 210, 560, 820, 1150      # pusat kolom: pengguna, sistem, sistem samping, tampilan
X_BALIK_LUAR, X_BALIK_DALAM = 58, 80       # jalur panah balik di pinggir kiri
X_KANAN = (1280, 1295, 1310)               # jalur turun di pinggir kanan untuk Q, P, N

# Simpul: kode -> (bentuk, x, y, teks). bentuk: oval / kotak / kotak2 (sempit) / ketupat.
SIMPUL = {
    "A": ("oval", XP, Y_AB_ATAS, "Merasakan guncangan kuat"),
    "B": ("kotak", XS, Y_AB_ATAS, "Menerima peringatan tsunami (server)"),
    "D": ("kotak", XP, Y_D, "Membuka aplikasi lewat widget atau ikon"),
    "C": ("kotak", XT, Y_D, "Layar evakuasi terbuka sendiri, sirene berbunyi"),
    "E": ("kotak", XS, Y_E, "Membaca GPS dan sensor arah"),
    "F": ("kotak", XT, Y_E, "Status lokasi dan kondisi GPS"),
    "G": ("kotak", XS, Y_G, "Memeriksa posisi terhadap zona merah"),
    "H": ("ketupat", XS, Y_H, "Di zona merah?"),
    "K": ("kotak", XS, Y_K, "Memilih tujuan: zona hijau/TEA yang masih sempat; bila tidak ada, TES menurut daya tampung"),
    "I": ("kotak2", XS2, Y_K, "Mencari rute ke TEA yang tetap di zona hijau"),
    "J": ("kotak", XT, Y_K, "“Anda di zona hijau” + tombol “Arah ke TEA”"),
    "L": ("kotak", XT, Y_L, "Tujuan, jarak, dan sisa waktu"),
    "M": ("ketupat", XS, Y_M, "Sudah di jalur?"),
    "N": ("kotak", XT, Y_M, "Garis putus-putus: “… m ke jalan”"),
    "O": ("ketupat", XS, Y_O, "HP searah rute?"),
    "P": ("kotak", XT, Y_O, "“Belok kiri dalam 30 m”"),
    "Q": ("kotak", XT, Y_Q, "“Putar balik” / “Ke kiri” / “Ke kanan”"),
    "R": ("kotak", XP, Y_R, "Berjalan mengikuti arahan"),
    "S": ("kotak", XS, Y_R, "Memperbarui posisi, arah, jarak, dan sisa waktu"),
    "T": ("ketupat", XP, Y_T, "Jalur terhalang?"),
    "X": ("ketupat", XS, Y_T, "Sudah tiba?"),
    "Y": ("kotak", XT, Y_T, "“Anda sudah sampai. Tetap di sini sampai ada info resmi”"),
    "U": ("kotak", XP, Y_U, "Menekan “Ada kendala?”"),
    "V": ("kotak", XS, Y_U, "Mengambil jalan memutar atau alternatif tujuan"),
    "W": ("kotak2", XS2, Y_U, "Mengirim laporan jalan ke posko"),
    "Z": ("kotak", XP, Y_Z, "Menekan “Lapor selamat”"),
    "AA": ("kotak", XS, Y_AA, "Mengirim lapor selamat dan kabar keluarga"),
    "AB": ("oval", XT, Y_AA, "Selesai: menunggu info resmi"),
}
BENTUK = {"oval": (240, 52), "kotak": (240, 56), "kotak2": (200, 56), "ketupat": (170, 90)}
TINGGI = {"K": 74}   # kotak dengan tiga baris teks


def P(k, sisi, geser=0):
    """Titik di tepi simpul k (atas/bawah/kiri/kanan), digeser sepanjang tepi bila perlu."""
    bentuk, x, y, _ = SIMPUL[k]
    w, h = BENTUK[bentuk]
    h = TINGGI.get(k, h)
    return {"atas": (x + geser, y - h / 2), "bawah": (x + geser, y + h / 2),
            "kiri": (x - w / 2, y + geser), "kanan": (x + w / 2, y + geser)}[sisi]


def titik_sisi_ketupat(k, x=None, y=None):
    """Titik pada sisi atas belah ketupat k: beri x (sisi kanan-atas) atau y (sisi kiri-atas)."""
    _, xc, yc, _ = SIMPUL[k]
    w, h = BENTUK["ketupat"]
    if x is not None:
        return yc - h / 2 + (h / 2) * abs(x - xc) / (w / 2)
    return xc - (w / 2) * (y - (yc - h / 2)) / (h / 2)


def antara(a, b):
    return (a + b) / 2


# y garis mendatar di celah antarbaris
Y_CE = antara(P("C", "bawah")[1], P("E", "atas")[1])
Y_LM = P("L", "bawah")[1] + 16                      # L -> M
Y_JM = Y_LM + 18                                    # J -> M (sejajar di bawah L -> M)
Y_MASUK_V = Y_M - 22                                # V -> M masuk sisi kiri-atas M
Y_QPN = [P("Q", "bawah")[1] + 14 + 16 * i for i in range(3)]   # Q, P, N -> R
Y_ST = antara(P("S", "bawah")[1], P("T", "atas")[1])
Y_XM = antara(P("X", "bawah")[1], P("U", "atas")[1])           # X -> M (panah balik dalam)
Y_VM = P("V", "bawah")[1] + 22                                  # V -> M (panah balik luar)
M_KANAN_ATAS = titik_sisi_ketupat("M", x=XS + 60)
M_KIRI_ATAS = titik_sisi_ketupat("M", y=Y_MASUK_V)

PANAH = [
    # 1. A -> D -> E
    ([P("A", "bawah"), P("D", "atas")], False),
    ([P("D", "kanan"), (XS - 30, Y_D), (XS - 30, P("E", "atas")[1])], False),
    # 2. B ⇢ C -> E
    ([P("B", "kanan"), (XT, Y_AB_ATAS), P("C", "atas")], True),
    ([P("C", "bawah"), (XT, Y_CE), (XS + 30, Y_CE), (XS + 30, P("E", "atas")[1])], False),
    # 3-4. E -> F, E -> G -> H
    ([P("E", "kanan"), P("F", "kiri")], False),
    ([P("E", "bawah"), P("G", "atas")], False),
    ([P("G", "bawah"), P("H", "atas")], False),
    # 5. H Tidak -> I -> J -> M (J masuk sisi kanan-atas M; titik atas dipakai L)
    ([P("H", "kanan"), (XS2, Y_H), P("I", "atas")], False),
    ([P("I", "kanan"), P("J", "kiri")], False),
    ([P("J", "kanan"), (1290, Y_K), (1290, Y_JM), (XS + 60, Y_JM), (XS + 60, M_KANAN_ATAS)], False),
    # 6. H Ya -> K -> L -> M
    ([P("H", "bawah"), P("K", "atas")], False),
    ([P("K", "bawah"), (XS, Y_L), P("L", "kiri")], False),
    ([P("L", "bawah"), (XT, Y_LM), (XS, Y_LM), P("M", "atas")], False),
    # 7-10. M Belum -> N; M Sudah -> O; O Ya -> P; O Tidak -> Q
    ([P("M", "kanan"), P("N", "kiri")], False),
    ([P("M", "bawah"), P("O", "atas")], False),
    ([P("O", "kanan"), P("P", "kiri")], False),
    ([P("O", "bawah"), (XS, Y_Q), P("Q", "kiri")], False),
    # N, P, Q -> R: jalur bertingkat (dalam ke luar), masuk ke tiga titik di atas R tanpa bersilangan
    ([P("Q", "kanan"), (X_KANAN[0], Y_Q), (X_KANAN[0], Y_QPN[0]), (XP - 60, Y_QPN[0]), P("R", "atas", -60)], False),
    ([P("P", "kanan"), (X_KANAN[1], Y_O), (X_KANAN[1], Y_QPN[1]), (XP, Y_QPN[1]), P("R", "atas")], False),
    ([P("N", "kanan"), (X_KANAN[2], Y_M), (X_KANAN[2], Y_QPN[2]), (XP + 60, Y_QPN[2]), P("R", "atas", 60)], False),
    # 11. R -> S -> T
    ([P("R", "kanan"), P("S", "kiri")], False),
    ([P("S", "bawah"), (XS, Y_ST), (XP, Y_ST), P("T", "atas")], False),
    # 12. T Ya -> U -> V -> M (panah balik luar, masuk sisi kiri-atas M)
    ([P("T", "bawah"), P("U", "atas")], False),
    ([P("U", "kanan"), P("V", "kiri")], False),
    ([P("V", "bawah"), (XS, Y_VM), (X_BALIK_LUAR, Y_VM), (X_BALIK_LUAR, Y_MASUK_V), (M_KIRI_ATAS, Y_MASUK_V)], False),
    # 13. V ⇢ W
    ([P("V", "kanan"), P("W", "kiri")], True),
    # 14-15. T Tidak -> X; X Belum -> M (panah balik dalam, masuk titik kiri M)
    ([P("T", "kanan"), P("X", "kiri")], False),
    ([P("X", "bawah"), (XS, Y_XM), (X_BALIK_DALAM, Y_XM), (X_BALIK_DALAM, Y_M), P("M", "kiri")], False),
    # 16. X Ya -> Y -> Z ⇢ AA ⇢ AB
    ([P("X", "kanan"), P("Y", "kiri")], False),
    ([P("Y", "bawah"), (XT, Y_Z), P("Z", "kanan")], False),
    ([P("Z", "bawah"), (XP, Y_AA), P("AA", "kiri")], True),
    ([P("AA", "kanan"), P("AB", "kiri")], True),
]
# Persilangan yang digambar dengan lompatan: indeks panah -> [(x, y)]. X -> M melompati T -> U.
LOMPAT = {next(i for i, (t, _) in enumerate(PANAH) if t[1] == (XS, Y_XM)): [(XP, Y_XM)]}

LABEL = [  # (x, y, teks, anchor): label cabang tepat di luar titik keluar
    (XS + 92, Y_H - 8, "Tidak", "start"), (XS + 8, Y_H + 62, "Ya", "start"),
    (XS + 92, Y_M - 8, "Belum", "start"), (XS + 8, Y_M + 62, "Sudah", "start"),
    (XS + 92, Y_O - 8, "Ya", "start"), (XS + 8, Y_O + 62, "Tidak", "start"),
    (XP + 92, Y_T - 8, "Tidak", "start"), (XP - 8, Y_T + 62, "Ya", "end"),
    (XS + 92, Y_T - 8, "Ya", "start"), (XS - 8, Y_XM - 6, "Belum", "end"),
    (300, Y_XM - 6, "arahan terus diperbarui", "start"),
    (300, Y_VM - 6, "kembali dengan rute baru", "start"),
]
Y_LABEL_J = antara(Y_K, Y_JM)
CATATAN_X = ["Tiba bila \u2264 20 m dari TES/TEA,", "keluar zona merah 3\u00d7, atau",
             "tombol \u201cSaya sudah sampai\u201d"]

_ft = {}


def lebar(teks, uk=UK, tebal=False):
    k = (uk, tebal)
    if k not in _ft:
        _ft[k] = ImageFont.truetype("C:/Windows/Fonts/" + ("segoeuib.ttf" if tebal else "segoeui.ttf"), int(uk * 4))
    return _ft[k].getlength(teks) / 4


def bungkus(teks, maks):
    baris, kini = [], ""
    for kata in teks.split():
        coba = (kini + " " + kata).strip()
        if lebar(coba) <= maks:
            kini = coba
        else:
            baris.append(kini)
            kini = kata
    return baris + [kini]


def e(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def gambar_simpul(k):
    bentuk, x, y, teks = SIMPUL[k]
    w, h = BENTUK[bentuk]
    h = TINGGI.get(k, h)
    o = []
    if bentuk == "oval":
        o.append(f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="{h / 2}" '
                 f'fill="#e6f2ea" stroke="#2f7d4f" stroke-width="1.6"/>')
        maks = w - 36
    elif bentuk == "ketupat":
        o.append(f'<path d="M{x},{y - h / 2} L{x + w / 2},{y} L{x},{y + h / 2} L{x - w / 2},{y} Z" '
                 f'fill="#fff8e8" stroke="#b7791f" stroke-width="1.5"/>')
        maks = w - 70
    else:
        o.append(f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="6" '
                 f'fill="#ffffff" stroke="#8f9aab" stroke-width="1.3"/>')
        maks = w - 24
    baris = bungkus(teks, maks)
    tinggi_baris = UK * 1.3
    y0 = y - (len(baris) - 1) * tinggi_baris / 2 + UK * 0.35
    for i, b in enumerate(baris):
        o.append(f'<text x="{x}" y="{y0 + i * tinggi_baris:.1f}" font-size="{UK}" fill="{TEKS}" '
                 f'text-anchor="middle">{e(b)}</text>')
    return "".join(o)


def path_panah(titik, lompat_x=(), r=5):
    d = f"M{titik[0][0]:.1f},{titik[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(titik, titik[1:]):
        if abs(y0 - y1) < 0.1:   # horizontal: sisipkan lompatan
            arah = 1 if x1 > x0 else -1
            for xc in sorted((x for x, y in lompat_x if abs(y - y0) < 0.1), key=lambda v: v * arah):
                if min(x0, x1) + r < xc < max(x0, x1) - r:
                    d += f" L{xc - arah * r:.1f},{y0:.1f} A{r},{r} 0 0 {1 if arah > 0 else 0} {xc + arah * r:.1f},{y0:.1f}"
        d += f" L{x1:.1f},{y1:.1f}"
    return d


def main():
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         f'<defs><marker id="kepala" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="{GARIS}"/></marker></defs>']
    # lajur
    for judul, x0, x1, warna in LAJUR:
        o.append(f'<rect x="{x0}" y="40" width="{x1 - x0}" height="{LAJUR_BAWAH - 40}" fill="{warna}" stroke="#d5d9e0"/>')
        o.append(f'<rect x="{x0}" y="40" width="{x1 - x0}" height="44" fill="#2f3b4c"/>')
        o.append(f'<text x="{(x0 + x1) / 2}" y="68" font-size="15" font-weight="700" fill="#ffffff" '
                 f'text-anchor="middle">{e(judul)}</text>')
    # panah
    for i, (titik, putus) in enumerate(PANAH):
        gaya = ' stroke-dasharray="7 5"' if putus else ""
        o.append(f'<path d="{path_panah(titik, LOMPAT.get(i, ()))}" fill="none" stroke="{GARIS}" '
                 f'stroke-width="1.5" stroke-linejoin="round"{gaya} marker-end="url(#kepala)"/>')
    for k in SIMPUL:
        o.append(gambar_simpul(k))
    for x, y, teks, anchor in LABEL:
        miring = ' font-style="italic"' if teks[0].islower() else ' font-weight="700"'
        o.append(f'<text x="{x}" y="{y}" font-size="12"{miring} fill="{REDUP}" text-anchor="{anchor}">{e(teks)}</text>')
    # label panah J -> M, tegak di sepanjang jalur pinggir kanan
    o.append(f'<text transform="translate(1303,{Y_LABEL_J:.0f}) rotate(90)" font-size="12" font-style="italic" '
             f'fill="{REDUP}" text-anchor="middle">{e("bila menekan “Arah ke TEA”")}</text>')
    for i, b in enumerate(CATATAN_X):
        o.append(f'<text x="{XS + 98}" y="{Y_T + 34 + i * 15}" font-size="11.5" font-style="italic" fill="{REDUP}">{e(b)}</text>')

    # legenda
    ly = LAJUR_BAWAH + 45
    lx = 40
    o.append(f'<rect x="{lx}" y="{ly - 9}" width="34" height="18" rx="9" fill="#e6f2ea" stroke="#2f7d4f" stroke-width="1.4"/>')
    o.append(f'<text x="{lx + 42}" y="{ly + 4.5}" font-size="12.5" fill="{TEKS}">Mulai / selesai</text>')
    lx += 42 + lebar("Mulai / selesai", 12.5) + 28
    o.append(f'<rect x="{lx}" y="{ly - 9}" width="34" height="18" rx="3" fill="#fff" stroke="#8f9aab" stroke-width="1.3"/>')
    o.append(f'<text x="{lx + 42}" y="{ly + 4.5}" font-size="12.5" fill="{TEKS}">Langkah</text>')
    lx += 42 + lebar("Langkah", 12.5) + 28
    o.append(f'<path d="M{lx},{ly} L{lx + 17},{ly - 11} L{lx + 34},{ly} L{lx + 17},{ly + 11} Z" fill="#fff8e8" '
             f'stroke="#b7791f" stroke-width="1.4"/>')
    o.append(f'<text x="{lx + 42}" y="{ly + 4.5}" font-size="12.5" fill="{TEKS}">Pertanyaan Ya/Tidak</text>')
    lx += 42 + lebar("Pertanyaan Ya/Tidak", 12.5) + 28
    for putus, teks in ((False, "Tanpa internet"), (True, "Perlu internet")):
        gaya = ' stroke-dasharray="7 5"' if putus else ""
        o.append(f'<path d="M{lx},{ly} H{lx + 40}" stroke="{GARIS}" stroke-width="1.5"{gaya} marker-end="url(#kepala)"/>')
        o.append(f'<text x="{lx + 50}" y="{ly + 4.5}" font-size="12.5" fill="{TEKS}">{teks}</text>')
        lx += 50 + lebar(teks, 12.5) + 28
    o.append("</svg>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".svg", "w", encoding="utf-8") as f:
        f.write("\n".join(o))
    ke_png(OUT + ".svg", OUT + ".png")
    print(OUT + ".svg/.png", f"({W}x{H})")


def ke_png(svg_path, png_path):
    browser = next((b for b in BROWSER if os.path.exists(b)), None)
    if not browser:
        print("  [lewati PNG] Chrome/Edge tidak ditemukan")
        return
    wadah = os.path.abspath(svg_path) + ".html"
    with open(wadah, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html><body style='margin:0;background:#fff'>"
                f"<img src='{os.path.basename(svg_path)}' width='{W}' height='{H}'></body></html>")
    try:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size={W},{H}", f"--screenshot={os.path.abspath(png_path)}",
                        "file:///" + wadah.replace(os.sep, "/")], check=True, capture_output=True, timeout=120)
    finally:
        os.remove(wadah)


if __name__ == "__main__":
    main()
