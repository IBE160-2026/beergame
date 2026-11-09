"""Konsept 06 Matrisen. Bygger 10 SVG-filer fra ../_shared/fixture.json.

Kjør: uv run python build.py
Alle celler og tall i grafer leses fra fixturen. Fargene regnes fra OKLCH og kontrolleres:
kontrast tall/celle >= 4,5:1, monoton lyshet, og CVD-avstand mellom armene.
"""
import json
import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
UP = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]  # oppstrøms øverst

# ---------------------------------------------------------------- farge


def oklch(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l3, m3, s3 = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    b2 = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3

    def gam(v):
        v = max(0.0, min(1.0, v))
        return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return "#%02X%02X%02X" % tuple(round(gam(v) * 255) for v in (r, g, b2))


def lin(hexc):
    out = []
    for i in (1, 3, 5):
        v = int(hexc[i:i + 2], 16) / 255
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return out


def lum(hexc):
    r, g, b = lin(hexc)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def oklab_of_lin(rgb):
    r, g, b = [max(0.0, v) for v in rgb]
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


PROTAN = [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]
DEUTAN = [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]


def sim_lin(hexc, M):
    v = lin(hexc)
    return [max(0.0, min(1.0, sum(M[i][j] * v[j] for j in range(3)))) for i in range(3)]


def lin_hex(rgb):
    def gam(v):
        return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return "#%02X%02X%02X" % tuple(round(gam(v) * 255) for v in rgb)


def de(a, b):
    return 100 * math.dist(a, b)


BG = "#F1F4F5"
PAPER = "#FBFCFC"
INK = "#21272B"
INK2 = "#4C565E"
RULE = "#D2D8DC"
RULE2 = "#98A2A9"
WHITE = "#FFFFFF"

RUST = [oklch(.885, .07, 64), oklch(.76, .09, 47), oklch(.515, .125, 38), oklch(.335, .09, 38)]
TEAL = [oklch(.925, .03, 195), oklch(.77, .055, 195), oklch(.515, .08, 195), oklch(.335, .055, 200)]
NEUTRAL = "#596269"  # grafitt for det som ikke er tall i skalaen
PALE = "#C9D0D5"
MID = oklch(.955, .002, 100)
SEQ = [oklch(.965, .003, 255), oklch(.905, .018, 250), oklch(.81, .036, 250), oklch(.69, .056, 252),
       oklch(.50, .072, 255), oklch(.38, .066, 258), oklch(.255, .045, 260)]


class Scale:
    def __init__(self, name, bins):
        self.name, self.bins = name, bins  # (lo, hi, hex, tekst)

    def fill(self, v):
        for lo, hi, hx, _ in self.bins:
            if lo <= v <= hi:
                return hx
        raise ValueError(v)

    def ink(self, v):
        hx = self.fill(v)
        return WHITE if contrast(WHITE, hx) >= contrast(INK, hx) else INK


INF = 10 ** 6
NET = Scale("Netto lager", [
    (-INF, -73, RUST[3], "73 eller mer i restordre"), (-72, -37, RUST[2], "37–72 i restordre"),
    (-36, -13, RUST[1], "13–36 i restordre"), (-12, -1, RUST[0], "1–12 i restordre"),
    (0, 0, MID, "0"),
    (1, 12, TEAL[0], "1–12 på lager"), (13, 36, TEAL[1], "13–36 på lager"),
    (37, 72, TEAL[2], "37–72 på lager"), (73, INF, TEAL[3], "73 eller mer på lager")])
QTY = Scale("Enheter", [
    (0, 0, SEQ[0], "0"), (1, 4, SEQ[1], "1–4"), (5, 8, SEQ[2], "5–8"), (9, 14, SEQ[3], "9–14"),
    (15, 24, SEQ[4], "15–24"), (25, 44, SEQ[5], "25–44"), (45, INF, SEQ[6], "45 eller mer")])

for s_ in (NET, QTY):
    for lo_, hi_, hx_, tx_ in s_.bins:
        c_ = max(contrast(WHITE, hx_), contrast(INK, hx_))
        assert c_ >= 4.5, (s_.name, tx_, hx_, round(c_, 2))

CVD_REPORT = []
for i_ in range(4):
    for nm_, M_ in (("protanopi", PROTAN), ("deuteranopi", DEUTAN)):
        CVD_REPORT.append((i_, nm_, round(de(oklab_of_lin(sim_lin(RUST[i_], M_)), oklab_of_lin(sim_lin(TEAL[i_], M_))), 1)))

# ---------------------------------------------------------------- data

S17 = FX["spill17"]["serier"]
G = S17["Grossist"]
NETG = [a - b for a, b in zip(G["lager"], G["restordre"])]
POSG = [n + p for n, p in zip(NETG, G["paa_vei"])]
DEM = S17["demand"]
SIM1 = FX["bare_sara_teller_paa_vei"]
SIM4 = FX["alle_teller_paa_vei"]
REPLAY = FX["replay_sara"]
KL = FX["klasse"]
GAMES = KL["spill"]


def net_of(block, role):
    return [a - b for a, b in zip(block[role]["lager"], block[role]["restordre"])]


def sent_of(block, role, t):  # t er ukenummer, 1-basert
    b = block[role]
    prev = b["lager"][t - 2] if t > 1 else 12
    return prev + b["levering"][t - 1] - b["lager"][t - 1]


assert all(NETG[t] == NETG[t - 1] + G["levering"][t] - G["innkommende_ordre"][t] for t in range(1, 36))
assert POSG[10] == 3 and POSG[10] + G["ordre"][10] == 27 and G["kost_sum"][10] == 68 and sent_of(S17, "Grossist", 11) == 4
assert G["ordre"][10] == 24 and G["levering"][14] == 17


def onset(series, limit=10):
    return next(i + 1 for i, v in enumerate(series) if i >= 4 and v >= limit)


def nf(v, d=0):
    s = f"{abs(v):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("−" + s) if v < 0 else s


def kr(v):
    return nf(v, 2) + " kr"


def amp(v):
    return f"{v:.1f}".replace(".", ",") + "×"


# ---------------------------------------------------------------- SVG-verktøy

FONT = "'Public Sans','Franklin Gothic Medium',Arial,sans-serif"
FONT_URL = "https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&amp;display=swap"


def tw(s, size, weight=400):
    factor = .535 if weight < 600 else .565
    w = 0
    for ch in str(s):
        if ch in "iljI.,:;'|·tf ":
            w += .32
        elif ch in "mwMWæÆ":
            w += .85
        elif ch.isupper():
            w += .68
        else:
            w += factor
    return w * size


def wrap(s, width, size, weight=400):
    lines, cur = [], ""
    for word in str(s).split(" "):
        test = (cur + " " + word).strip()
        if tw(test, size, weight) <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def r2(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class C:
    def __init__(self, name, w, h, title, desc, side):
        self.name, self.w, self.h, self.side = name, w, h, side
        self.title, self.desc = title, desc
        self.p = []
        self.rect(0, 0, w, h, fill=BG)

    def add(self, s):
        self.p.append(s)

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1, rx=0, dash=None, op=None):
        a = f'<rect x="{r2(x)}" y="{r2(y)}" width="{r2(w)}" height="{r2(h)}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if rx:
            a += f' rx="{rx}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if op is not None:
            a += f' opacity="{op}"'
        self.p.append(a + "/>")

    def line(self, x1, y1, x2, y2, stroke=RULE, sw=1, dash=None):
        a = f'<line x1="{r2(x1)}" y1="{r2(y1)}" x2="{r2(x2)}" y2="{r2(y2)}" stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        self.p.append(a + "/>")

    def path(self, d, stroke=INK, sw=1.5, fill="none", cap="round"):
        self.p.append(f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}" stroke-linecap="{cap}" stroke-linejoin="round"/>')

    def circle(self, x, y, r, fill="none", stroke=None, sw=1):
        a = f'<circle cx="{r2(x)}" cy="{r2(y)}" r="{r2(r)}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        self.p.append(a + "/>")

    def text(self, x, y, s, size=14, weight=400, fill=INK, anchor="start", tracking=None):
        cls = {400: "d06-r", 500: "d06-m", 600: "d06-s", 700: "d06-b"}[weight]
        if size >= 26:  # store enkeltstående tall står best med proporsjonale sifre
            cls += " d06-p"
        a = f'<text class="{cls}" x="{r2(x)}" y="{r2(y)}" font-size="{size}" fill="{fill}"'
        if anchor != "start":
            a += f' text-anchor="{anchor}"'
        if tracking:
            a += f' letter-spacing="{tracking}"'
        self.p.append(a + f">{escape(str(s))}</text>")

    def para(self, x, y, s, width, size=14, lh=1.42, weight=400, fill=INK):
        for line in wrap(s, width, size, weight):
            self.text(x, y, line, size, weight, fill)
            y += size * lh
        return y

    def group(self, tr):
        self.p.append(f'<g transform="{tr}">')

    def end(self):
        self.p.append("</g>")

    def save(self):
        style = (f"@import url('{FONT_URL}');"
                 ".d06-root{font-variant-numeric:tabular-nums}.d06-p{font-variant-numeric:proportional-nums}"
                 ".d06-r{font-weight:400}.d06-m{font-weight:500}.d06-s{font-weight:600}.d06-b{font-weight:700}")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" id="d06-{self.side}-root" class="d06-root" '
               f'font-family="{FONT}"><title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>'
               f"<style>{style}</style>" + "".join(self.p) + "</svg>")
        (HERE / f"{self.name}.svg").write_text(svg, encoding="utf-8")


def fv(v):
    return nf(v)


def num_w(txt, size):
    """Målt bredde i Public Sans med tabellsifre: ca. 0,655 em per tegn."""
    return len(txt) * .655 * size


def strip(c, x, y, vals, scale, cw, ch, gap=1.5, size=12, weight=500, start=0, numbers=True):
    """Én rad celler. Tallet tegnes bare når det får plass."""
    for i, v in enumerate(vals):
        cx = x + (i + start) * cw
        c.rect(cx, y, cw - gap, ch, fill=scale.fill(v))
        if numbers and num_w(fv(v), size) <= cw - gap:
            c.text(cx + (cw - gap) / 2, y + ch / 2 + size * .36, fv(v), size, weight, scale.ink(v), "middle")


def week_axis(c, x, y, n, cw, size=12, every=5, fill=INK2, first=True):
    for w in range(1, n + 1):
        if w == 1 or w % every == 0:
            label = f"Uke {w}" if (w == 1 and first and cw > 22) else str(w)
            anchor = "start" if (w == 1 and first and cw > 22) else "middle"
            cx = x + (w - 1) * cw + (0 if anchor == "start" else cw / 2)
            c.text(cx, y, label, size, 400, fill, anchor)


def legend_net(c, x, y, cw=38, ch=13, size=12, words=True):
    n = len(NET.bins)
    for i, b in enumerate(NET.bins):
        c.rect(x + i * cw, y, cw - 1.5, ch, fill=b[2])
    ticks = {1: "−72", 2: "−36", 3: "−12", 6: "12", 7: "36", 8: "72"}
    for i, t in ticks.items():
        c.text(x + i * cw - .75, y + ch + size + 2, t, size, 400, INK2, "middle")
    c.text(x + 4.5 * cw - .75, y + ch + size + 2, "0", size, 400, INK2, "middle")
    if words:
        c.text(x, y - 6, "Restordre", size, 500, INK)
        c.text(x + n * cw - 1.5, y - 6, "Lager", size, 500, INK, "end")


def legend_qty(c, x, y, cw=38, ch=13, size=12, title="Enheter"):
    for i, b in enumerate(QTY.bins):
        c.rect(x + i * cw, y, cw - 1.5, ch, fill=b[2])
    c.text(x + cw / 2 - .75, y + ch + size + 2, "0", size, 400, INK2, "middle")
    for i, t in {2: "4", 3: "8", 4: "14", 5: "24", 6: "44"}.items():
        c.text(x + i * cw - .75, y + ch + size + 2, t, size, 400, INK2, "middle")
    if title:
        c.text(x, y - 6, title, size, 500, INK)


def rows_for(block, role, T, typed=None):
    b = block[role]
    n = [a - r for a, r in zip(b["lager"], b["restordre"])]
    own = b["ordre"][:T - 1]
    return [
        ("Ordre inn", b["innkommende_ordre"][:T], QTY),
        ("Levering", b["levering"][:T], QTY),
        ("Lager / restordre", n[:T], NET),
        ("På vei", b["paa_vei"][:T], QTY),
        ("Egen ordre", own + ([typed] if typed is not None else []), QTY),
    ]


def phone_frame(c, x, y, s=1.0, h=844):
    c.group(f"translate({r2(x)} {r2(y)}) scale({s})")
    c.rect(0, 0, 390, h, fill=PAPER, stroke=RULE2, sw=1.2, rx=30)


def phone_matrix(c, block, role, T, typed=None, y=112, pitch=56, ch=33, x=18, w=354, now_w=54, committed=False, label3=None):
    rows = rows_for(block, role, T, typed)
    hist = w - now_w - 6
    cw = hist / max(T - 1, 1)
    yy = y
    for k, (label, vals, sc) in enumerate(rows):
        lab = label
        if k == 2:
            lab = label3 or f"Lager {block[role]['lager'][T - 1]} · Restordre {block[role]['restordre'][T - 1]}"
        c.text(x, yy, lab, 13, 500, INK)
        cy = yy + 6
        strip(c, x, cy, vals[:T - 1], sc, cw, ch, gap=1.5 if cw > 27 else 1, size=13)
        nx = x + hist + 6
        if k < 4 or typed is not None:
            v = vals[T - 1]
            c.rect(nx, cy, now_w, ch, fill=sc.fill(v))
            c.text(nx + now_w / 2, cy + ch / 2 + 6.4, fv(v), 18, 600, sc.ink(v), "middle")
            if k == 4 and not committed:
                c.rect(nx - 1, cy - 1, now_w + 2, ch + 2, stroke=INK, sw=2)
        else:
            c.rect(nx, cy, now_w, ch, fill=PAPER, stroke=INK, sw=1.4)
            c.line(nx + now_w / 2, cy + 8, nx + now_w / 2, cy + ch - 8, stroke=INK, sw=1.6)
        yy += pitch
    # akse: nå er høyre kant, aldri en slutt
    ay = y + 4 * pitch + 6 + ch + 16
    for wk in range(1, T):
        if wk == 1 or wk % 5 == 0:
            c.text(x + (wk - 1) * cw + cw / 2, ay, str(wk), 13, 400, INK2, "middle")
    c.text(x + hist + 6 + now_w / 2, ay, "nå", 13, 600, INK, "middle")
    return ay


def game_header(c, T, kost, role="Grossist", spill=17, name=None):
    c.text(18, 58, f"Uke {T}", 30, 700)
    c.text(18, 82, f"{role}, Spill {spill}" + (f", {name}" if name else ""), 13, 400, INK2)
    c.text(372, 42, "Totalkostnad", 13, 400, INK2, "end")
    c.text(372, 62, kr(kost), 18, 600, INK, "end")


def pos_lines(c, y, T, typed=None, block=S17, role="Grossist"):
    b = block[role]
    l, r, p = b["lager"][T - 1], b["restordre"][T - 1], b["paa_vei"][T - 1]
    pos = l - r + p
    c.text(18, y, "Posisjon", 14, 500)
    c.text(372, y, f"{l} − {r} + {p} = {fv(pos)}", 14, 500, INK, "end")
    if typed is not None:
        c.text(18, y + 22, "Med ordren", 14, 400, INK2)
        c.text(372, y + 22, f"{fv(pos)} + {typed} = {fv(pos + typed)}", 14, 600, INK, "end")


def input_row(c, y, T, typed=None):
    c.text(18, y, f"Din ordre, Uke {T}", 13, 400, INK2)
    fy = y + 8
    c.rect(18, fy, 104, 58, fill=WHITE, stroke=INK, sw=1.4, rx=4)
    if typed is not None:
        c.text(70, fy + 40, typed, 32, 700, INK, "middle")
        c.rect(134, fy, 238, 58, fill=INK, rx=4)
        c.text(253, fy + 35, f"Bekreft ordre {typed}", 17, 600, WHITE, "middle")
    else:
        c.line(70, fy + 14, 70, fy + 44, stroke=INK, sw=1.8)
        c.rect(134, fy, 238, 58, fill=BG, stroke=RULE, rx=4)
        c.text(253, fy + 35, "Bekreft ordre", 17, 500, INK2, "middle")
    return fy + 58


def seat_list(c, y, seats, x=18, w=354, pitch=30):
    """seats: (rolle, navn, statustekst, ferdig?)"""
    for role, name, status, done, *ki in seats:
        if done:
            c.circle(x + 6, y - 5, 5, fill=INK)
        else:
            c.circle(x + 6, y - 5, 4.5, fill=PAPER, stroke=INK, sw=1.4)
        c.text(x + 20, y, f"{name}, {role}", 14, 500 if not done else 400)
        c.text(x + w, y, status, 14, 400 if done else 600, INK2 if done else INK, "end")
        y += pitch
    return y


# ---------------------------------------------------------------- spill-telefoner


def phone_main(c, x, y, s=1.0):
    phone_frame(c, x, y, s)
    game_header(c, 11, G["kost_sum"][10])
    ay = phone_matrix(c, S17, "Grossist", 11, typed=24)
    pos_lines(c, ay + 30, 11, 24)
    ey = input_row(c, ay + 84, 11, 24)
    c.text(18, ey + 22, "Kan ikke endres etter bekreftelse.", 13, 400, INK2)
    c.line(18, ey + 44, 372, ey + 44)
    c.text(18, ey + 68, "Venter på Jonas, 3 min, og deg", 14, 500)
    c.text(18, ey + 90, "Ida og Mikkel har bestilt.", 13, 400, INK2)
    c.text(18, ey + 126, "Vis uka som regnestykke", 14, 600)
    c.line(18, ey + 132, 18 + tw("Vis uka som regnestykke", 14, 600), ey + 132, stroke=INK)
    c.text(18, 822, "Demodata", 13, 400, INK2)
    c.end()


def phone_A(c, x, y, s):
    phone_frame(c, x, y, s)
    game_header(c, 11, G["kost_sum"][10])
    ay = phone_matrix(c, S17, "Grossist", 11)
    pos_lines(c, ay + 30, 11)
    ey = input_row(c, ay + 62, 11)
    c.text(18, ey + 24, "Tast et helt tall.", 13, 400, INK2)
    c.text(18, ey + 60, "Ida og Mikkel har bestilt.", 13, 400, INK2)
    c.end()


def phone_B(c, x, y, s):
    phone_frame(c, x, y, s)
    game_header(c, 11, G["kost_sum"][10])
    ay = phone_matrix(c, S17, "Grossist", 11, typed=24, pitch=48, ch=27)
    pos_lines(c, ay + 26, 11, 24)
    ey = input_row(c, ay + 78, 11, 24)
    ky = ey + 12
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "Slett"]
    kw, kh = 118, 48
    for i, k in enumerate(keys):
        kx = 18 + (i % 3) * kw
        kyy = ky + (i // 3) * kh
        c.rect(kx, kyy, kw - 2, kh - 2, fill=BG if k else PAPER, rx=3)
        if k:
            c.text(kx + kw / 2 - 1, kyy + 31, k, 19 if k != "Slett" else 14, 500, INK, "middle")
    c.end()


def phone_C(c, x, y, s):
    phone_frame(c, x, y, s)
    game_header(c, 11, G["kost_sum"][10])
    ay = phone_matrix(c, S17, "Grossist", 11, typed=24, committed=True)
    c.text(18, ay + 36, "Ordre 24 er bekreftet.", 17, 600)
    c.text(18, ay + 58, "Uka går videre når alle har bestilt.", 14, 400, INK2)
    c.line(18, ay + 76, 372, ay + 76)
    seat_list(c, ay + 104, [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
                            ("Grossist", "Sara (deg)", "har bestilt", True), ("Fabrikk", "Jonas", "venter, 3 min", False)])
    c.end()


def phone_D(c, x, y, s):
    phone_frame(c, x, y, s)
    game_header(c, 12, G["kost_sum"][11])
    ay = phone_matrix(c, S17, "Grossist", 12)
    prev, cur = 10, 11
    lines = [("Ordre inn", G["innkommende_ordre"][prev], G["innkommende_ordre"][cur]),
             ("Levering", G["levering"][prev], G["levering"][cur]),
             ("Restordre", G["restordre"][prev], G["restordre"][cur]),
             ("På vei", G["paa_vei"][prev], G["paa_vei"][cur])]
    c.text(18, ay + 34, "Ny kolonne fra høyre", 17, 600)
    yy = ay + 62
    for lab, a, b in lines:
        c.text(18, yy, lab, 14, 400, INK2)
        c.text(372, yy, f"{a} til {b}", 14, 600, INK, "end")
        yy += 25
    c.rect(18, yy + 6, 354, 48, fill=PAPER, stroke=INK, sw=1.2, rx=4)
    c.text(195, yy + 36, "Hopp over", 15, 600, INK, "middle")
    c.end()


def phone_E(c, x, y, s):
    """Jonas ser sin egen matrise, KI-ukene er merket."""
    phone_frame(c, x, y, s)
    F = S17["Fabrikk"]
    game_header(c, 14, F["kost_sum"][13], "Fabrikk", 17, "Jonas")
    ay = phone_matrix(c, S17, "Fabrikk", 14, typed=F["ordre"][13], committed=True)
    # KI-merking over egne ordre i ukene KI la dem
    hist = 354 - 54 - 6
    cw = hist / 13
    ry = 112 + 4 * 56
    x1 = 18 + 12 * cw
    x2 = 18 + 354
    c.line(x1, ry + 2, x2, ry + 2, stroke=INK, sw=1.6)
    c.text(x2, ry - 2, "KI-spiller, Uke 13–14", 13, 600, INK, "end")
    c.rect(18, ay + 18, 354, 90, fill=INK, rx=4)
    c.text(32, ay + 46, "KI-spiller overtok setet ditt.", 16, 600, WHITE)
    c.para(32, ay + 70, "Pause etter 24 t uten ordre. Nå spiller gruppa videre, og du kan komme tilbake.", 325, 13, 1.35, 400, WHITE)
    c.rect(18, ay + 120, 354, 56, fill=WHITE, stroke=INK, sw=1.4, rx=4)
    c.text(195, ay + 154, "Ta tilbake setet", 17, 600, INK, "middle")
    c.text(18, ay + 202, "Ordre lagt av KI-spiller er merket i loggen din.", 13, 400, INK2)
    c.end()


def phone_F(c, x, y, s):
    phone_frame(c, x, y, s)
    c.text(18, 58, "Spillet er ferdig", 26, 700)
    c.text(18, 82, "Grossist, Spill 17", 13, 400, INK2)
    c.text(18, 128, "Kjeden", 15, 500, INK2)
    c.text(18, 170, kr(FX["spill17"]["kjedekost"]), 38, 700)
    c.text(18, 194, "Totalkostnad for alle fire Roller", 13, 400, INK2)
    yy = 236
    for r in ROLES:
        cost = FX["spill17"]["kost_per_rolle"][r]
        c.line(18, yy + 10, 372, yy + 10)
        c.text(18, yy, r + (" (deg)" if r == "Grossist" else ""), 15, 600 if r == "Grossist" else 400)
        c.text(372, yy, kr(cost), 15, 600 if r == "Grossist" else 400, INK, "end")
        yy += 34
    yy += 22
    c.text(18, yy, "Din matrise, alle uker", 13, 500)
    yy += 8
    cw = 354 / 36
    for lab, vals, sc in rows_for(S17, "Grossist", 36)[:5]:
        vv = vals if lab != "Egen ordre" else G["ordre"]
        strip(c, 18, yy, vv, sc, cw, 21, gap=1, numbers=False)
        yy += 23
    c.text(18, yy + 14, "Ordre inn, levering, lager / restordre, på vei, egen ordre", 13, 400, INK2)
    c.rect(18, 740, 354, 56, fill=INK, rx=4)
    c.text(195, 774, "Gå videre til Debrief", 17, 600, WHITE, "middle")
    c.text(18, 822, "Demodata", 13, 400, INK2)
    c.end()


# ---------------------------------------------------------------- 05 hovedskjerm


def page_05():
    c = C("05-spill", 1600, 1000, "Matrise: spillskjermen, Uke 11",
          "Saras telefon i Uke 11 med 24 tastet inn, åpnet regnestykke-panel og laptopvisning. Rader over uker, fargen er et tall.", "spill")
    c.text(50, 40, "Spillet: fem rader, én kolonne per uke, høyre kant er nå", 22, 700)
    phone_main(c, 50, 62)
    # åpnet panel
    px, py, pw = 468, 62, 312
    c.rect(px, py, pw, 844, fill=PAPER, stroke=RULE2, sw=1.2, rx=4)
    c.text(px + 20, py + 42, "Uke 11 som regnestykke", 18, 700)
    c.text(px + 20, py + 64, "Åpnes med ett trykk på telefonen", 13, 400, INK2)

    def ledger(y, items, title=None):
        xl, xr = px + 20, px + pw - 20
        if title:
            c.text(xl, y, title, 14, 600)
            y += 24
        for lab, val, strong in items:
            c.text(xl, y, lab, 14, 600 if strong else 400, INK if strong else INK2)
            c.text(xr, y, val, 14, 600 if strong else 400, INK, "end")
            if strong:
                c.line(xl, y - 16, xr, y - 16, stroke=INK, sw=1)
            y += 24
        return y
    prev_net = NETG[9]
    y = ledger(py + 104, [("Lager / restordre, Uke 10", fv(prev_net), False), ("Levering", "+ " + fv(G["levering"][10]), False),
                          ("Ordre inn", "− " + fv(G["innkommende_ordre"][10]), False),
                          ("Lager / restordre nå", fv(NETG[10]), True)], "Kolonnen går opp")
    c.text(px + 20, y, f"Sendt {sent_of(S17, 'Grossist', 11)} av {-prev_net + G['innkommende_ordre'][10]} du skyldte", 13, 400, INK2)
    y += 44
    y = ledger(y, [("Lager", fv(G["lager"][10]), False), ("Restordre", "− " + fv(G["restordre"][10]), False), ("På vei", "+ " + fv(G["paa_vei"][10]), False),
                   ("Posisjon", fv(POSG[10]), True), ("Ordre 24", "+ 24", False), ("Posisjon med ordren", fv(POSG[10] + 24), True)], "Posisjon")
    y += 22
    y = ledger(y, [("Neste levering", fv(G["levering"][11]), False)], "Det som er på vei")
    y = c.para(px + 20, y, "Ikke garantert. Leverandøren kan mangle varer.", pw - 40, 13, 1.35, 400, INK2) + 20
    y = ledger(y, [(f"Restordre {G['restordre'][10]} × 1,00", nf(G["restordre"][10], 2), False), ("Lager 0 × 0,50", nf(0, 2), False),
                   ("Totalkostnad", kr(G["kost_sum"][10]), True)], "Kostnad denne uka")
    c.line(px + 20, py + 766, px + pw - 20, py + 766)
    c.text(px + 20, py + 792, "Vis som tabell", 14, 600)
    c.line(px + 20, py + 798, px + 20 + tw("Vis som tabell", 14, 600), py + 798, stroke=INK)
    c.text(px + pw - 20, py + 792, "Fargeskala", 14, 600, INK, "end")
    c.line(px + pw - 20 - tw("Fargeskala", 14, 600), py + 798, px + pw - 20, py + 798, stroke=INK)
    # laptop
    lx, ly, lw, lh = 812, 62, 738, 486
    c.rect(lx, ly, lw, lh, fill=PAPER, stroke=RULE2, sw=1.2, rx=8)
    c.line(lx - 16, ly + lh + 8, lx + lw + 16, ly + lh + 8, stroke=RULE2, sw=2)
    c.text(lx + 26, ly + 46, "Uke 11", 28, 700)
    c.text(lx + 122, ly + 46, "Grossist, Spill 17", 14, 400, INK2)
    c.text(lx + lw - 26, ly + 46, kr(G["kost_sum"][10]), 18, 600, INK, "end")
    c.text(lx + lw - 26 - tw(kr(G["kost_sum"][10]), 18, 600) - 10, ly + 46, "Totalkostnad", 14, 400, INK2, "end")
    mx, cw, nw = lx + 150, 46, 64
    my = ly + 74
    rows = rows_for(S17, "Grossist", 11, 24)
    for k, (lab, vals, sc) in enumerate(rows):
        yy = my + k * 44
        c.text(lx + 26, yy + 24, lab, 14, 500)
        strip(c, mx, yy, vals[:10], sc, cw, 38, gap=2, size=14)
        v = vals[10]
        c.rect(mx + 10 * cw + 4, yy, nw, 38, fill=sc.fill(v))
        c.text(mx + 10 * cw + 4 + nw / 2, yy + 26, fv(v), 20, 600, sc.ink(v), "middle")
        if k == 4:
            c.rect(mx + 10 * cw + 3, yy - 1, nw + 2, 40, stroke=INK, sw=2)
    ay = my + 5 * 44 + 14
    week_axis(c, mx, ay, 10, cw, 13)
    c.text(mx + 10 * cw + 4 + nw / 2, ay, "nå", 13, 600, INK, "middle")
    by = ay + 30
    c.text(lx + 26, by + 2, "Posisjon", 15, 500)
    c.text(lx + 150, by + 2, "0 − 13 + 16 = 3", 15, 500)
    c.text(lx + 26, by + 28, "Med ordren", 15, 400, INK2)
    c.text(lx + 150, by + 28, "3 + 24 = 27", 15, 600)
    c.rect(lx + 368, by - 18, 90, 54, fill=WHITE, stroke=INK, sw=1.4, rx=4)
    c.text(lx + 413, by + 19, "24", 30, 700, INK, "middle")
    c.rect(lx + 470, by - 18, 242, 54, fill=INK, rx=4)
    c.text(lx + 591, by + 15, "Bekreft ordre 24", 17, 600, WHITE, "middle")
    c.text(lx + 26, ly + lh - 16, "Venter på Jonas, 3 min, og deg. Ida og Mikkel har bestilt.", 13, 400, INK2)
    # lesing og skala
    x0 = 812
    c.text(x0, 600, "Hvordan cellene leses", 18, 700)
    legend_net(c, x0, 636, 40, 15)
    c.text(x0, 684, "Bare raden Lager / restordre. Tallet i cellen er alltid fasit.", 13, 400, INK2)
    legend_qty(c, x0 + 400, 636, 40, 15)
    c.text(x0 + 400, 684, "Ordre inn, levering, på vei, egen ordre.", 13, 400, INK2)
    notes = [("P1", "Kolonnen er regnestykket: forrige saldo + levering − ordre inn."),
             ("P3", "På vei står rett under saldoen, og Posisjon legger dem sammen."),
             ("P2", "En stor egen ordre kommer først fram som levering noen uker senere.")]
    yy = 730
    for tag, tx in notes:
        c.text(x0, yy, tag, 14, 700)
        c.text(x0 + 34, yy, tx, 14)
        yy += 28
    c.para(x0, yy + 14, "Cellene blir smalere etter hvert som ukene går. Først forsvinner tallene, så blir bare fargebåndet igjen, og høyre kolonne har alltid tall. Aksen sier aldri hvor mange uker som gjenstår.", 720, 14, 1.42, 400, INK2)
    c.text(50, 935, "Telefon 390×844", 13, 400, INK2)
    c.text(468, 935, "Detaljer bak ett trykk", 13, 400, INK2)
    c.text(812, 935, "Demodata. Skalaene er felles for alle flater i produktet.", 13, 400, INK2)
    c.save()


# ---------------------------------------------------------------- 06 spilldynamikk


def page_06():
    c = C("06-spilldynamikk", 2100, 1200, "Matrise: spilldynamikk",
          "Seks telefonruter gjennom en Uke, fra åpning til spillets slutt.", "spilldynamikk")
    c.text(44, 48, "Én uke i matrisen, og slutten av spillet", 26, 700)
    s = .8
    w = 390 * s
    gap = (2100 - 88 - 6 * w) / 5
    px = [44 + i * (w + gap) for i in range(6)]
    py = 76
    phone_A(c, px[0], py, s)
    phone_B(c, px[1], py, s)
    phone_C(c, px[2], py, s)
    phone_D(c, px[3], py, s)
    phone_E(c, px[4], py, s)
    phone_F(c, px[5], py, s)
    notes = [("A  Uka åpner", "Ny kolonne står ved høyre kant med ukas tall. Egen ordre er tom, og markøren står der."),
             ("B  Beslutningen", "24 med 16 på vei: Posisjon går fra 3 til 27. Tallet regnes ut, men aldri anbefales."),
             ("C  Bekreftet", "Cellen låses og fylles. Lista viser hvem som mangler, med navn og tid."),
             ("D  Uka går videre", "Kolonnen skyves inn fra høyre på 1,2 s, aldri over 2 s, og kan hoppes over."),
             ("E  Jonas er borte", "Sara ser først Pause, så «Fabrikk: KI-spiller» i setelista. Jonas ser sine KI-uker merket og kan ta setet tilbake."),
             ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle. Etterspørselen er fortsatt skjult.")]
    for i, (h, tx) in enumerate(notes):
        c.text(px[i], py + 844 * s + 30, h, 16, 700)
        c.para(px[i], py + 844 * s + 54, tx, w - 4, 14, 1.38, 400, INK2)
    yy = 930
    c.line(44, yy, 2056, yy)
    c.text(44, yy + 40, "Hva spilleren lærer av å se matrisen uke for uke", 18, 700)
    c.para(44, yy + 72, "I Uke 5 er alle radene bleke og nesten like. Så begynner saldoraden å gå over i rust, og når du taster en stor ordre, ser du at raden På vei rett under blir mørkere uka etter. Levering følger etter med ujevne utslag, og noen uker senere går saldoraden fra rust til blågrønn. Mønsteret kommer av det du bestilte og når det kom fram, og hver kolonne viser regnestykket bak.", 1180, 18, 1.5)
    c.text(1300, yy + 40, "Tall i Uke 11 og 12", 18, 700)
    c.para(1300, yy + 72, f"Uke 11: Restordre {G['restordre'][10]}, På vei {G['paa_vei'][10]}. Uke 12: Restordre {G['restordre'][11]}, På vei {G['paa_vei'][11]} ({G['paa_vei'][10]} + 24 − {G['levering'][10]}). Den ene ordren flytter På vei med 20 på én uke, og lageret merker ingenting ennå.", 750, 18, 1.5)
    c.text(44, 1140, "Demodata. E er tegnet som eksempel: Spill 17 hadde ingen KI-seter.", 13, 400, INK2)
    c.save()


# ---------------------------------------------------------------- matrise for kjeden


def chain(c, x, y, block, cw, ch, gap=2, size=13, labw=96, pitch=None, ampv=None, showdiag=True, demgap=14, labsize=14, onset_labels=True, ampsize=15):
    pitch = pitch or ch + gap
    pos = {}
    for k, r in enumerate(UP):
        yy = y + k * pitch
        c.text(x, yy + ch / 2 + labsize * .36, r, labsize, 500)
        strip(c, x + labw, yy, block[r]["ordre"], QTY, cw, ch, gap=gap, size=size)
        pos[r] = yy
        if ampv:
            c.text(x + labw + 36 * cw + 8, yy + ch / 2 + ampsize * .36, amp(ampv[r]), ampsize, 700)
    dy = y + 4 * pitch + demgap
    c.text(x, dy + ch / 2 + labsize * .36, "Etterspørsel", labsize, 500)
    strip(c, x + labw, dy, block["demand"], QTY, cw, ch, gap=gap, size=size)
    on = {r: onset(block[r]["ordre"]) for r in ROLES}
    if showdiag:
        # trapp langs cellekantene: dekker ingen tall
        xs = {r: x + labw + (on[r] - 1) * cw - gap / 2 for r in UP}
        d = f"M{r2(xs['Detaljist'])} {r2(pos['Detaljist'] + ch)}"
        seq = list(reversed(UP))
        for a, b in zip(seq, seq[1:]):
            d += f" V{r2(pos[a] - gap / 2)} H{r2(xs[b])}"
        d += f" V{r2(pos['Fabrikk'] - gap / 2)}"
        c.path(d, stroke=WHITE, sw=5, cap="butt")
        c.path(d, stroke=INK, sw=2.2, cap="butt")
    week_axis(c, x + labw, dy + ch + 18, 36, cw, max(12, size - 1))
    return on, dy + ch


# ---------------------------------------------------------------- 10 pedagogikk


def page_10():
    c = C("10-pedagogikk", 2000, 1400, "Matrise: grafgrammatikk",
          "Saras matrise ved Uke 5, 11, 18 og 29 med prinsippene merket, sammenligning med simulert referanse etter Debriefen, hjelpegrad og dokumentert fargeskala.", "pedagogikk")
    c.text(60, 58, "Matrise: samme fem rader, uke for uke", 30, 700)
    c.text(60, 88, "Hver kolonne er en uke og hver rad en størrelse. Samme farge betyr samme tallområde på alle flater.", 16, 400, INK2)
    x0, labw, cw, ch = 60, 124, 31, 21
    y = 128
    frames = [
        (5, "P1  Lager er en opphopning", f"Kolonnen går opp: {NETG[3]} + {G['levering'][4]} − {G['innkommende_ordre'][4]} = {NETG[4]}. Inn og ut er like, så saldoen står stille.",
         "Til neste ordre: ingen rad beveger seg ennå. Det du bestiller nå, ser du tidligst om noen uker."),
        (11, "P3  Det som er på vei blir glemt", f"Rust i saldoraden, men På vei ligger rett under: {fv(NETG[10])} + {G['paa_vei'][10]} = {POSG[10]}. Posisjonen er ikke så dårlig som lageret.",
         f"Til neste ordre: tast 24 og se {POSG[10]} bli {POSG[10] + 24}. Du bestemmer, regnestykket er ditt."),
        (18, "P2  Forsinkelse", f"På vei er {G['paa_vei'][17]} og restordre {G['restordre'][17]}. Ordren på 24 i Uke 11 ble {G['levering'][14]} levert i Uke 15: båndet fra egen ordre dukker opp ujevnt i Levering.",
         f"Til neste ordre: saldoen er {fv(NETG[17])} og Posisjon {fv(POSG[17])}. Se begge før du taster."),
        (29, "P8  Restordre koster dobbelt, lager koster også", f"Båndet har snudd. Lager {G['lager'][28]} gir {nf(G['lager'][28] * .5, 2)} kr per uke. Restordre {max(G['restordre'])} i Uke {G['restordre'].index(max(G['restordre'])) + 1} kostet {nf(max(G['restordre']), 2)} kr den uka.",
         "Til neste ordre: lageret tømmes bare av ordre inn. Lave egne ordre merkes først om noen uker."),
    ]
    for T, head, body, ins in frames:
        rows = rows_for(S17, "Grossist", T)
        c.text(x0, y + 15, f"Uke {T}", 18, 700)
        yy = y + 26
        for k, (lab, vals, sc) in enumerate(rows):
            c.text(x0, yy + ch / 2 + 4.6, lab, 13, 500 if k == 2 else 400, INK if k == 2 else INK2)
            vv = vals if k < 4 else G["ordre"][:T - 1]
            strip(c, x0 + labw, yy, vv, sc, cw, ch, gap=1.5, size=12)
            yy += ch + 1.5
        # nå-markør: høyre kant
        nx = x0 + labw + (T) * cw - 1.5
        c.line(nx + 3, y + 22, nx + 3, yy + 2, stroke=INK, sw=1.6)
        c.text(nx + 8, y + 36, "nå", 13, 600)
        week_axis(c, x0 + labw, yy + 14, T, cw, 12, first=False)
        tx = 1124
        c.text(tx, y + 15, head, 16, 700)
        a = c.para(tx, y + 38, body, 420, 14, 1.36)
        c.para(tx, a + 4, ins, 420, 14, 1.36, 500, INK2)
        y += 160
    # hjelpegrad, høyre kolonne
    hx = 1590
    c.text(hx, 143, "Hjelpegrad", 18, 700)
    c.para(hx, 168, "Klassespill: fem rader og Posisjon som ett tall for denne uka. Tallet er der, mønsteret er det ikke.", 350, 14, 1.36)
    T = 18
    c.text(hx, 244, "Klassespill, Uke 18", 14, 600)
    yy = 252
    cwm = 19.2 * .58 * 1.0 + 8
    cwm = 350 / 18
    for lab, vals, sc in rows_for(S17, "Grossist", T):
        vv = vals if lab != "Egen ordre" else G["ordre"][:T - 1]
        strip(c, hx, yy, vv, sc, cwm, 13, gap=1, numbers=False)
        yy += 14
    c.text(hx, yy + 16, f"Posisjon {fv(POSG[17])}, bare denne uka", 13, 400, INK2)
    yy += 48
    c.text(hx, yy, "Replay etter Debriefen, Uke 18", 14, 600)
    yy += 8
    RG = REPLAY["serier"]["Grossist"]
    RPOS = [a - b + p for a, b, p in zip(RG["lager"], RG["restordre"], RG["paa_vei"])]
    for lab, vals, sc in rows_for(REPLAY["serier"], "Grossist", T):
        vv = vals if lab != "Egen ordre" else RG["ordre"][:T - 1]
        strip(c, hx, yy, vv, sc, cwm, 13, gap=1, numbers=False)
        yy += 14
    strip(c, hx, yy + 3, RPOS[:T], NET, cwm, 19, gap=1, size=11, numbers=False)
    c.rect(hx - 1, yy + 2, 350 + 1, 21, stroke=INK, sw=1.2)
    yy += 40
    c.para(hx, yy, f"Sjette rad: Posisjon, hele historikken ({fv(RPOS[T - 1])} nå). Etter Debriefen er raden et verktøy. Før den ville den tatt bort opplevelsen Debriefen bygger på.", 350, 14, 1.36)
    # skala
    sy = 580
    c.text(hx, sy, "Skala, sann og felles", 18, 700)
    legend_net(c, hx, sy + 34, 38, 14)
    c.text(hx, sy + 82, "Grenser: 1×, 3× og 6× startlageret (12).", 13, 400, INK2)
    legend_qty(c, hx, sy + 120, 38, 14)
    # deuteranopi-simulering
    c.text(hx, sy + 170, "Deuteranopi-simulert", 13, 500)
    for i, b in enumerate(NET.bins):
        c.rect(hx + i * 38, sy + 176, 36.5, 12, fill=lin_hex(sim_lin(b[2], DEUTAN)))
    worst = min(v for *_, v in CVD_REPORT)
    c.text(hx, sy + 204, f"Armene skilles med ΔE ≥ {nf(worst, 1)} (OKLab×100).", 13, 400, INK2)
    # Etter debrief
    by = 800
    c.line(60, by, 1940, by, stroke=RULE2)
    c.text(60, by + 40, "Etter Debriefen: Rollene blir radene, og bølgen blir en diagonal", 22, 700)
    labw2, cw2, ch2 = 94, 20.5, 50
    on, bot = chain(c, 60, by + 96, S17, cw2, ch2, gap=1.5, size=11, labw=labw2, ampv=FX["spill17"]["forsterkning"], labsize=13)
    c.text(60, by + 80, f"Spill 17, ordre. Kjeden {kr(FX['spill17']['kjedekost'])}", 15, 600)
    x2 = 1000
    on2, _ = chain(c, x2, by + 96, SIM4["serier"], cw2, ch2, gap=1.5, size=11, labw=labw2, ampv=SIM4["forsterkning"], labsize=13)
    c.text(x2, by + 80, f"Simulert referanse: alle teller det som er på vei. Kjeden {kr(SIM4['kjedekost'])}", 15, 600)
    # Tekst under
    ty = bot + 58
    c.text(60, ty, "P5  Forsterkning og faseforskyvning", 15, 700)
    c.para(60, ty + 22, f"Første ordre på 10 eller mer: Uke {on['Detaljist']}, {on['Grossist']}, {on['Distributør']}, {on['Fabrikk']}. Helningen er forsinkelsen, og mørkere bånd oppover er forsterkningen ({amp(FX['spill17']['forsterkning']['Detaljist'])} til {amp(FX['spill17']['forsterkning']['Fabrikk'])}).", 450, 14, 1.36)
    c.text(540, ty, "P4  Ordrer er ikke etterspørsel", 15, 700)
    c.para(540, ty + 22, "Nederste rad er alt kundene gjorde: 4, så 8. Hver Rolle så bare raden rett under seg, aldri denne.", 420, 14, 1.36)
    c.text(1000, ty, "P6  Struktur gir atferd", 15, 700)
    c.para(1000, ty + 22, f"Samme form går igjen i klassen: {KL['ferdige']['antall']} ferdige spill, median Fabrikk {amp(KL['ferdige']['forsterkning_per_rolle']['Fabrikk']['median'])}. Spør hvorfor raden ble slik, ikke hvem som gjorde feil.", 420, 14, 1.36)
    c.text(1470, ty, "P7  Overreaksjon forsterker også", 15, 700)
    c.para(1470, ty + 22, f"Referansen er ikke en fasit. Fabrikk har fortsatt {amp(SIM4['forsterkning']['Fabrikk'])}. I simuleringen ga en regel som jaget siste ordre for hardt, 12× hos Fabrikk, selv med det som er på vei talt med. Rolig tilpasning må med.", 470, 14, 1.36)
    c.text(60, 1384, "Demodata. Referansen er simulert, med en regel valgt for å illustrere. Forsterkning = standardavvik i ordre / standardavvik i kundeetterspørsel.", 13, 400, INK2)
    c.save()


# ---------------------------------------------------------------- 07 debrief


def panel(c, x, y, w, h, title=None, size=19):
    c.rect(x, y, w, h, fill=PAPER, stroke=RULE, rx=3)
    if title:
        c.text(x + 22, y + 36, title, size, 700)


def page_07():
    c = C("07-debrief", 2100, 1200, "Matrise: Gruppedebrief",
          "Fem steg og delt skjerm. Forklaring før avsløring, etterspørselen avsløres, fire Rollers ordre som en diagonal, ditt øyeblikk i Uke 11 og quiz.", "debrief")
    c.text(40, 44, "Gruppedebrief: fem steg, felles skjerm", 26, 700)
    c.text(2060, 44, "Spill 17. Demodata.", 14, 400, INK2, "end")
    # Steg 1
    panel(c, 40, 66, 590, 300, "1  Skriv Forklaringen din")
    c.para(62, 128, "Hvorfor svingte lageret og ordrene dine slik? Bruk din egen matrise. Resten av kjeden er skjult til alle har skrevet.", 546, 14, 1.36, 400, INK2)
    yy = 174
    cw = 546 / 36
    for lab, vals, sc in rows_for(S17, "Grossist", 36):
        vv = vals if lab != "Egen ordre" else G["ordre"]
        strip(c, 62, yy, vv, sc, cw, 12, gap=1, numbers=False)
        yy += 13
    c.rect(62, 248, 546, 66, fill=WHITE, stroke=RULE2, rx=3)
    c.para(74, 271, "Ordrene inn økte og lageret gikk tomt. Jeg bestilte mye i Uke 11 fordi restordren vokste, og det kom fram mye senere.", 520, 14, 1.36)
    c.rect(62, 324, 13, 11, fill=INK, rx=2)
    c.path("M64.5 324 v-3.5 a4 4 0 0 1 8 0 v3.5", sw=1.4)
    c.text(84, 335, "Avsløringen er låst. 3 av 4 Forklaringer er levert.", 14, 500)
    # Steg 2
    panel(c, 40, 380, 590, 322, "2  Kundene bestilte 4, så 8. Og så 8 hver uke.", 22)
    cw2 = 546 / 36
    c.text(62, 442, "Kundeetterspørsel", 14, 600)
    strip(c, 62, 450, DEM, QTY, cw2, 58, gap=1.5, size=11, weight=600)
    c.text(62, 526, "Ordre inn hos deg, Grossist", 14, 500, INK2)
    strip(c, 62, 534, G["innkommende_ordre"], QTY, cw2, 30, gap=1.5, size=9.5, numbers=False)
    week_axis(c, 62, 582, 36, cw2, 12, first=True)
    c.para(62, 608, f"Hoppet skjedde i Uke 5. Det du så var {min(G['innkommende_ordre'])} til {max(G['innkommende_ordre'])}, uke for uke. Ingen i kjeden, utenom Ida, så kundene, og bare én uke om gangen.", 546, 14, 1.36)
    c.para(62, 672, "Nå kan øvelsen få navnet sitt: ølspillet.", 546, 14, 1.36, 400, INK2)
    # Steg 3 delt skjerm
    panel(c, 650, 66, 1410, 636, "3  Bølgen vandrer oppover kjeden og vokser", 26)
    c.text(2038, 102, "Delt skjerm", 14, 600, INK2, "end")
    sx = 672
    on, bot = chain(c, sx, 124, S17, 32.5, 88, gap=2, size=15, labw=110, ampv=FX["spill17"]["forsterkning"], labsize=16, ampsize=18, demgap=14)
    # etiketter ved diagonalen
    for r, k in zip(UP, range(4)):
        ox2 = sx + 110 + (on[r] - 1) * 32.5 - 7
        c.text(ox2, 124 + k * 90 + 17, f"Uke {on[r]}", 14, 700, INK, "end")
    legend_qty(c, sx + 110, 660, 34, 11, 12, title=None)
    c.text(sx, 670, "Ordre", 13, 500)
    c.para(sx + 370, 672, f"Trappa går gjennom første ordre på 10 eller mer. Helningen er {on['Fabrikk'] - on['Detaljist']} uker fra Detaljist til Fabrikk. Forsterkning står til høyre.", 900, 14, 1.36, 400, INK2)
    # Steg 4
    panel(c, 40, 716, 1440, 454, "4  Ditt øyeblikk: Uke 11")
    x0, labw, cw3, ch3 = 62, 112, 23.5, 30
    yy = 786
    rows = rows_for(S17, "Grossist", 36)
    colx = x0 + labw + 10 * cw3
    for k, (lab, vals, sc) in enumerate(rows):
        vv = vals if lab != "Egen ordre" else G["ordre"]
        c.text(x0, yy + 19, lab, 13, 500)
        strip(c, x0 + labw, yy, vv, sc, cw3, ch3, gap=1.5, size=11)
        yy += ch3 + 2
    c.rect(colx - 1.5, 784, cw3 + 1.5, 5 * (ch3 + 2) + 2, stroke=INK, sw=2)
    # kobling 24 -> 17: klamme over raden, ingen strek gjennom tall
    bx1 = colx + cw3 / 2
    bx2 = x0 + labw + 14 * cw3 + cw3 / 2 - .75
    c.path(f"M{r2(bx1)} 782 V772 H{r2(bx2)} V782", sw=1.6, cap="butt")
    c.text(bx2 + 10, 778, "24 bestilt i Uke 11, 17 levert i Uke 15", 13, 600)
    lev_y = 786 + (ch3 + 2)
    c.rect(x0 + labw + 14 * cw3 - 1, lev_y - 1, cw3 + .5, ch3 + 2, stroke=INK, sw=2)
    week_axis(c, x0 + labw, yy + 12, 36, cw3, 12)
    ts = yy + 40
    kost_etter = G["kost_sum"][35] - G["kost_sum"][24]
    lager_peak = max(G["lager"])
    col1, col2, col3 = x0, x0 + 300, x0 + 640
    c.text(col1, ts, "Hva du så", 15, 700)
    c.para(col1, ts + 22, f"Ordre inn {G['innkommende_ordre'][10]}, Levering {G['levering'][10]}, Restordre {G['restordre'][10]}, På vei {G['paa_vei'][10]}. Posisjon {POSG[10]}.", 270, 14, 1.36)
    c.text(col2, ts, "Hva du bestilte", 15, 700)
    c.para(col2, ts + 22, f"24. Fire uker senere kom {G['levering'][14]} fram, ikke 24: leverandøren manglet varer.", 310, 14, 1.36)
    c.text(col3, ts, "Hva det kostet senere", 15, 700)
    c.para(col3, ts + 22, f"På vei toppet på {max(G['paa_vei'])} i Uke {G['paa_vei'].index(max(G['paa_vei'])) + 1}. Lager nådde {lager_peak} i Uke {G['lager'].index(lager_peak) + 1}. Uke 26–36 kostet deg {kr(kost_etter)}.", 290, 14, 1.36)
    ts2 = ts + 84
    c.text(col1, ts2, "Dette kommer fra loggen. KI-generert, kan ta feil:", 13, 500, INK2)
    D, F, Di = S17["Detaljist"], S17["Fabrikk"], S17["Distributør"]
    c.para(col1, ts2 + 20, f"Du så Restordre {G['restordre'][10]} og bestilte 24 med {G['paa_vei'][10]} på vei. To uker senere fikk Mikkel 24 inn, mot {Di['innkommende_ordre'][11]} uka før, og bestilte {Di['ordre'][12]}.", 905, 14, 1.36)
    # Høyre del steg 4: de andre + sammenligning
    rx = 1072
    c.text(rx, 752, "Hva de andre så i Uke 11", 15, 700)
    yy = 778
    for r, nm in (("Detaljist", "Ida"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")):
        b = S17[r]
        c.text(rx, yy, f"{nm}, {r}", 14, 500)
        c.text(rx + 386, yy, f"Inn {b['innkommende_ordre'][10]} · Lager {b['lager'][10]} · Restordre {b['restordre'][10]}", 14, 400, INK2, "end")
        c.line(rx, yy + 8, rx + 386, yy + 8)
        yy += 28
    yy += 16
    c.text(rx, yy, "Simulert: samme kjede, Grossist teller alt på vei", 15, 700)
    yy += 12
    cw4 = 386 / 36
    c.text(rx, yy + 14, "Din egen ordre", 13, 400, INK2)
    strip(c, rx, yy + 20, G["ordre"], QTY, cw4, 20, gap=.8, numbers=False)
    c.text(rx, yy + 60, "Simulert", 13, 400, INK2)
    strip(c, rx, yy + 66, SIM1["serier"]["Grossist"]["ordre"], QTY, cw4, 20, gap=.8, numbers=False)
    yy += 110
    pairs = [("Grossist-kostnad", kr(FX["spill17"]["kost_per_rolle"]["Grossist"]), kr(SIM1["kost_per_rolle"]["Grossist"])),
             ("Kjeden", kr(FX["spill17"]["kjedekost"]), kr(SIM1["kjedekost"])),
             ("Forsterkning, Grossist", amp(FX["spill17"]["forsterkning"]["Grossist"]), amp(SIM1["forsterkning"]["Grossist"]))]
    c.text(rx + 258, yy - 2, "Du", 13, 500, INK2, "end")
    c.text(rx + 386, yy - 2, "Simulert", 13, 500, INK2, "end")
    yy += 20
    for lab, a, b in pairs:
        c.text(rx, yy, lab, 14)
        c.text(rx + 258, yy, a, 14, 600, INK, "end")
        c.text(rx + 386, yy, b, 14, 600, INK, "end")
        yy += 22
    c.text(rx, yy + 2, "Viser sammenhengen, ikke en fasit.", 13, 400, INK2)
    # Steg 5
    panel(c, 1500, 716, 560, 454, "5  Quiz: Posisjon i Uke 11")
    c.para(1522, 780, f"Du hadde Lager {G['lager'][10]}, Restordre {G['restordre'][10]} og {G['paa_vei'][10]} på vei. Hva var Posisjonen?", 516, 15, 1.36, 500)
    opts = [(G["paa_vei"][10], "Ditt svar. Feil."), (POSG[10], "Riktig svar."), (G["paa_vei"][10] + G["restordre"][10], ""), (-G["restordre"][10], "")]
    yy = 838
    for v, tag in opts:
        chosen = bool(tag)
        c.rect(1522, yy, 516, 40, fill=WHITE if chosen else PAPER, stroke=INK if chosen else RULE, sw=1.5 if chosen else 1, rx=3)
        c.text(1538, yy + 26, fv(v), 16, 600 if chosen else 400)
        if tag:
            c.text(2024, yy + 26, tag, 14, 600, INK, "end")
        yy += 46
    c.text(1522, yy + 18, f"Hvorfor {G['paa_vei'][10]} er feil", 15, 700)
    c.para(1522, yy + 42, f"{G['paa_vei'][10]} er bare det som er på vei. Restordren må trekkes fra: {G['lager'][10]} − {G['restordre'][10]} + {G['paa_vei'][10]} = {POSG[10]}. Se etter kolonnen for Uke 11 i matrisen din.", 516, 14, 1.38)
    c.save()


# ---------------------------------------------------------------- vegg


ORDER = [("venter", "Venter"), ("pauset", "Pauset"), ("pågår", "Pågår"), ("ferdig", "Ferdig")]


def groups():
    out = []
    for key, lab in ORDER:
        gs = [g for g in GAMES if g["status"] == key]
        if key == "venter":
            gs.sort(key=lambda g: -g["ventet_timer"])
        elif key == "ferdig":
            gs.sort(key=lambda g: g["kjedekost"])
        else:
            gs.sort(key=lambda g: -g["uke"])
        out.append((key, lab, gs))
    return out


def wall(c, x, y, cw, rh, role="Fabrikk", metric="netto_lager", gap=1.0, group_gap=0, rowfn=None, headfn=None):
    yy = y
    pos = {}
    scale = NET if metric == "netto_lager" else QTY
    for key, lab, gs in groups():
        if headfn:
            yy = headfn(key, lab, len(gs), yy)
        for g in gs:
            vals = g[metric][role]
            for i, v in enumerate(vals):
                c.rect(x + i * cw, yy, cw - gap, rh - gap, fill=scale.fill(v))
            if key != "ferdig":
                c.rect(x + len(vals) * cw - gap, yy - .5, 2, rh, fill=INK)
            pos[g["spill"]] = yy
            if rowfn:
                rowfn(g, yy)
            yy += rh
        yy += group_gap
    return pos, yy


def page_08():
    c = C("08-laerer-oversikt", 1600, 1000, "Matrise: Oversikt for faglærer",
          "60 Klassespill som ett bilde: netto lager for valgt Rolle over uker, sortert etter status. Tabell og tiltak ved siden av.", "laerer-oversikt")
    c.text(30, 42, "Oversikt", 26, 700)
    c.text(150, 42, "class-of-1994, IBE160", 14, 400, INK2)
    c.text(1180 - 30, 42, "41 ferdig · 15 pågår (2 pauset) · 4 venter", 15, 600, INK, "end")
    # filterrad
    fy = 78
    c.text(30, fy, "Rolle", 13, 400, INK2)
    xx = 68
    for r in ROLES:
        sel = r == "Fabrikk"
        c.text(xx, fy, r, 13, 700 if sel else 400)
        if sel:
            c.line(xx, fy + 5, xx + tw(r, 13, 700), fy + 5, stroke=INK, sw=2)
        xx += tw(r, 13, 700) + 14
    xx += 16
    c.text(xx, fy, "Størrelse", 13, 400, INK2)
    xx += 62
    for t, sel in (("Netto lager", True), ("Ordre", False)):
        c.text(xx, fy, t, 13, 700 if sel else 400)
        if sel:
            c.line(xx, fy + 5, xx + tw(t, 13, 700), fy + 5, stroke=INK, sw=2)
        xx += tw(t, 13, 700) + 14
    xx += 16
    c.text(xx, fy, "Status", 13, 400, INK2)
    xx += 46
    for t, sel in (("Alle 60", True), ("Venter 4", False), ("Pauset 2", False), ("Pågår 13", False), ("Ferdig 41", False)):
        c.text(xx, fy, t, 13, 700 if sel else 400)
        if sel:
            c.line(xx, fy + 5, xx + tw(t, 13, 700), fy + 5, stroke=INK, sw=2)
        xx += tw(t, 13, 700) + 12
    # kolonner
    mx, cw, rh = 66, 21, 12.4
    ty = 110
    top = 120
    for w in (1, 5, 10, 15, 20, 25, 30, 36):
        c.text(mx + (w - 1) * cw + cw / 2, ty, str(w), 12, 400, INK2, "middle")
    c.text(30, ty, "Spill", 12, 500, INK2)
    tx = mx + 36 * cw + 10
    cols = {"uke": tx + 24, "status": tx + 36, "ki": tx + 226, "kost": tx + 330}
    c.text(cols["uke"], ty, "Uke", 12, 500, INK2, "end")
    c.text(cols["status"], ty, "Venter på / neste", 12, 500, INK2)
    c.text(cols["ki"], ty, "KI", 12, 500, INK2)
    c.text(cols["kost"], ty, "Kjede, kr", 12, 500, INK2, "end")

    def head(key, lab, n, yy):
        yy += 15
        word = {"venter": "Venter", "pauset": "Pauset", "pågår": "Pågår", "ferdig": "Ferdig, billigst øverst"}[key]
        c.text(30, yy, f"{word}  {n}", 12, 700)
        return yy + 4

    def row(g, yy):
        base = yy + rh - 3.4
        c.text(58, base, g["spill"], 11, 400 if g["spill"] != 17 else 700, INK2, "end")
        c.text(cols["uke"], base, g["uke"], 11, 400, INK, "end")
        st = ""
        if g["status"] == "venter" and g["spill"] != 2:  # spill 2 får egen uthevet tekst
            st = f"{g['navn']}, {g['venter_paa']}, {g['ventet_timer']} t"
        elif g["status"] == "pauset":
            st = f"Pauset, fortsetter {g['fortsetter']}"
        if st:
            c.text(cols["status"], base, st, 11, 600 if g["status"] == "venter" else 400)
        if g["ki_seter"]:
            c.text(cols["ki"], base, f"KI {g['ki_seter']}", 11, 400)
        c.text(cols["kost"], base, nf(g["kjedekost"]), 11, 400, INK, "end")

    pos, bot = wall(c, mx, top, cw, rh, "Fabrikk", "netto_lager", rowfn=row, headfn=head)
    # uthevet rad: spill 2
    y2 = pos[2]
    c.rect(26, y2 - 1.5, cols["kost"] - 26 + 4, rh + .4, stroke=INK, sw=1.4)
    c.rect(cols["status"] - 4, y2 - 1.5, 186, rh + .4, fill=INK)
    c.text(cols["status"], y2 + rh - 3.4, "Noah, Grossist, 23 t. KI om 1 t", 11, 600, WHITE)
    # høyre rail
    rx, rw = 1180, 390
    c.line(rx - 14, 24, rx - 14, 976)
    c.text(rx, 42, "Hele klassen, Fabrikk", 15, 700)
    legend_net(c, rx, 76, 40, 15)
    c.para(rx, 124, "Rust er restordre, blågrønt er lager. Svart strek er nå: pågående spill slutter der de er. Nesten alle rader har samme form.", rw, 13, 1.36, 400, INK2)
    c.text(rx, 196, "Nær overtakelse", 15, 700)
    c.rect(rx, 208, rw, 124, fill=INK, rx=3)
    c.text(rx + 16, 234, "Spill 2 venter på Noah (Grossist)", 15, 600, WHITE)
    c.text(rx + 16, 256, "23 t. KI overtar om 1 t.", 15, 400, WHITE)
    c.rect(rx + 16, 272, 186, 44, fill=WHITE, rx=3)
    c.text(rx + 109, 299, "Send Melding til Noah", 14, 600, INK, "middle")
    c.rect(rx + 214, 272, 160, 44, stroke=WHITE, sw=1.2, rx=3)
    c.text(rx + 294, 299, "Pause spillet", 14, 600, WHITE, "middle")
    c.text(rx, 362, "Venter ellers", 15, 700)
    yy = 386
    others = [g for g in groups()[0][2] if g["spill"] != 2]
    for g in others:
        c.text(rx, yy, f"Spill {g['spill']}", 13, 500)
        c.text(rx + 70, yy, f"{g['navn']}, {g['venter_paa']}, {g['ventet_timer']} t", 13)
        c.text(rx + rw, yy, "Send Melding", 13, 600, INK, "end")
        c.line(rx + rw - tw("Send Melding", 13, 600), yy + 4, rx + rw, yy + 4, stroke=INK)
        yy += 25
    for g in groups()[1][2]:
        c.text(rx, yy, f"Spill {g['spill']}", 13, 500)
        c.text(rx + 70, yy, f"Pauset i Uke {g['uke']}, fortsetter {g['fortsetter']}", 13)
        yy += 25
    yy += 16
    c.text(rx, yy, "Trakt", 15, 700)
    yy += 12
    fun = KL["traktA"]
    labs = [("registrert", "Registrert"), ("klassespill_ferdig", "Klassespill ferdig"), ("debrief_ferdig", "Debrief ferdig"), ("quiz_bestått", "Quiz bestått"),
            ("replay_ferdig", "Replay ferdig"), ("test_levert", "Test levert"), ("ki_vurdering_klar", "KI-vurdering klar")]
    bw = rw - 170
    for k, lab in labs:
        v = fun[k]
        c.text(rx, yy + 13, lab, 13)
        c.text(rx + 150, yy + 13, v, 13, 600, INK, "end")
        c.rect(rx + 160, yy + 3, max(bw * v / 240, 1), 12, fill=NEUTRAL)
        yy += 22
    c.text(rx, yy + 18, f"Ferdige spill: median kjede {nf(KL['ferdige']['kjedekost']['median'])} kr", 13, 500)
    c.text(rx, yy + 37, f"Fjorårets klasse: {nf(KL['fjoraaret']['median_kjedekost'])} kr ({KL['fjoraaret']['spill']} spill)", 13, 400, INK2)
    # handlinger nederst
    c.rect(rx, 918, 150, 42, stroke=INK, sw=1.2, rx=3)
    c.text(rx + 75, 944, "Vis i plenum", 14, 600, INK, "middle")
    c.rect(rx + 162, 918, 150, 42, stroke=RULE2, rx=3)
    c.text(rx + 237, 944, "Vis som tabell", 14, 500, INK, "middle")
    c.text(1570, 990, "Demodata", 12, 400, INK2, "end")
    c.save()


# ---------------------------------------------------------------- 01 landing


def page_01():
    c = C("01-landing", 1440, 1200, "Matrise: landingsside for faglærere",
          "Første skjermbilde med klassens matrise som hovedbilde, og starten på neste seksjon med ett setes egne rader.", "landing")
    c.text(64, 54, "Matrise", 21, 700)
    c.text(1376, 54, "Logg inn", 15, 600, INK, "end")
    c.line(1376 - tw("Logg inn", 15, 600), 60, 1376, 60, stroke=INK)
    y = c.para(64, 158, "Alle spillene i klassen, på én skjerm", 430, 54, 1.08, 700)
    y = c.para(64, y + 8, "Fire roller i en forsyningskjede, ett heltall per uke. Dette kjører hele øvelsen fra invitasjon til PDF-rapport, for klasser på rundt 250 studenter.", 400, 18, 1.45, 400, INK2)
    c.rect(64, y + 22, 228, 56, fill=INK, rx=4)
    c.text(178, y + 57, "Be om lærertilgang", 17, 600, WHITE, "middle")
    c.text(316, y + 57, "Logg inn", 17, 600)
    c.line(316, y + 63, 316 + tw("Logg inn", 17, 600), y + 63, stroke=INK)
    wx, cw, rh = 540, 23.2, 10.6
    pos, bot = wall(c, wx, 98, cw, rh, "Grossist", "netto_lager", gap=1.0, group_gap=7)
    c.para(wx, bot + 14, "Hver rad er ett Klassespill, hver kolonne én uke. Fargen er netto lager for samme Rolle i alle spill. Pågående spill slutter der de er. Demodata.", 560, 14, 1.4, 400, INK2)
    legend_net(c, wx + 36 * cw - 9 * 26, bot + 26, 26, 12, 12)
    # neste seksjon
    sy = 838
    c.line(64, sy, 1376, sy)
    c.para(64, sy + 62, "Studenten ser bare sitt eget sete", 500, 34, 1.1, 700)
    c.para(64, sy + 104 + 34, "Fem rader og ett tall å bestemme hver uke, på mobilen. Andres tall er skjult.", 430, 17, 1.45, 400, INK2)
    x0, labw, cw2 = 620, 128, 49
    yy = sy + 42
    for lab, vals, sc in rows_for(S17, "Grossist", 11):
        vv = vals if lab != "Egen ordre" else G["ordre"][:10]
        c.text(x0, yy + 22, lab, 14, 500)
        strip(c, x0 + labw, yy, vv, sc, cw2, 34, gap=2, size=14)
        yy += 37
    week_axis(c, x0 + labw, yy + 12, 11, cw2, 13)
    c.text(x0 + labw + 11 * cw2, yy + 12, "nå", 13, 600, INK, "end")
    c.text(x0, yy + 12, "Demodata", 13, 400, INK2)
    facts = ["KI-spillere fyller tomme seter", "Ett fravær stopper ikke gruppa", "Ingen spill blir stående uferdig",
             "På mobil og på norsk", "Studentlisten fra Canvas-eksport"]
    fy = sy + 288
    fx = 64
    for f in facts:
        c.text(fx, fy, f, 15, 500)
        fx += tw(f, 15, 500) + 32
    c.save()


# ---------------------------------------------------------------- 02 lærer klasse


def field(c, x, y, w, label, value, h=42, fill=WHITE, weight=400, size=15):
    c.text(x, y, label, 13, 500, INK2)
    c.rect(x, y + 7, w, h, fill=fill, stroke=RULE2, rx=3)
    c.text(x + 12, y + 7 + h / 2 + size * .36, value, size, weight)


def page_02():
    c = C("02-laerer-klasse", 1440, 1000, "Matrise: Lag Klasse",
          "Navn og emnekode, Canvas-fil, e-postkolonne, ugyldige rader per rad, send Invitasjoner og status.", "laerer-klasse")
    c.text(64, 54, "Lag Klasse", 28, 700)
    c.text(1376, 54, "Faglærer Bård", 14, 400, INK2, "end")
    lx = 64
    field(c, lx, 96, 360, "Navn på Klasse", "class-of-1994")
    field(c, lx + 380, 96, 180, "Emnekode", "IBE160")
    c.text(lx, 188, "Klasseliste fra Canvas-eksport", 16, 700)
    c.rect(lx, 202, 560, 60, fill=WHITE, stroke=RULE2, rx=3)
    c.text(lx + 16, 228, "ibe160-eksport.xlsx", 15, 600)
    c.text(lx + 16, 248, f"{KL['roster']['paa_lista']} rader, 6 kolonner", 13, 400, INK2)
    c.text(lx + 544, 238, "Bytt fil", 14, 600, INK, "end")
    c.text(lx, 300, "Velg e-postkolonnen", 16, 700)
    heads = ["Student", "ID", "SIS Login", "E-post", "Seksjon", "Karakter"]
    wid = [122, 56, 82, 170, 62, 68]
    rows = [["Sara Berg", "20417", "saber", "sara.berg@student.example.no", "A", ""],
            ["Noah Dahl", "20418", "nodah", "noah.dahl@student.example.no", "A", ""],
            ["Ida Lunde", "20419", "idlun", "ida.lunde@student.example.no", "B", ""]]
    xx = lx
    for i, h in enumerate(heads):
        sel = i == 3
        if sel:
            c.rect(xx, 312, wid[i], 136, fill=WHITE)
            c.rect(xx, 312, wid[i], 136, stroke=INK, sw=1.6)
        c.text(xx + 8, 334, h, 13, 700 if sel else 500)
        yy = 362
        for r in rows:
            v = r[i]
            if i == 3:
                v = v.split("@")[0] + "@…"
            c.text(xx + 8, yy, v, 13, 400, INK if sel else INK2)
            yy += 28
        xx += wid[i]
    c.line(lx, 342, lx + 560, 342)
    c.text(lx, 472, "Kolonnen «E-post» valgt: 246 gyldige adresser, 4 ugyldige.", 14, 500)
    c.text(lx, 516, "Ugyldige rader", 16, 700)
    bad = [(37, "oskar.hansen@student", "mangler domene"), (88, "ida lunde@student.example.no", "mellomrom i adressen"),
           (141, "", "tom celle"), (203, "mikkel.aas@student,example.no", "komma i stedet for punktum")]
    yy = 546
    for rad, adr, why in bad:
        c.text(lx, yy, f"Rad {rad}", 14, 600)
        c.text(lx + 66, yy, adr or "(tom)", 14)
        c.text(lx + 330, yy, why, 14, 400, INK2)
        c.text(lx + 560, yy, "Rett", 14, 600, INK, "end")
        c.line(lx + 560 - tw("Rett", 14, 600), yy + 4, lx + 560, yy + 4, stroke=INK)
        c.line(lx, yy + 12, lx + 560, yy + 12)
        yy += 36
    c.rect(lx, yy + 14, 300, 56, fill=INK, rx=4)
    c.text(lx + 150, yy + 49, "Send 246 Invitasjoner", 17, 600, WHITE, "middle")
    c.text(lx + 316, yy + 38, "Gyldig i 14 dager. De 4 ugyldige", 13, 400, INK2)
    c.text(lx + 316, yy + 56, "får ingen Invitasjon før de er rettet.", 13, 400, INK2)
    # høyre: status som matrise
    rx = 700
    c.line(rx - 36, 90, rx - 36, 950)
    c.text(rx, 110, "Status", 22, 700)
    c.text(rx, 134, "Én celle per rad i fila, i samme rekkefølge. Rad 1 øverst til venstre.", 14, 400, INK2)
    random.seed(1994)
    invalid = [37, 88, 141, 203]
    manual = [37, 88]
    others = [i for i in range(1, 251) if i not in invalid]
    unreg = sorted(random.sample(others, KL["roster"]["uregistrert"] - 2)) + [141, 203]
    cell, gapc = 26.5, 2
    gy = 160
    cols_ = 25
    for i in range(1, 251):
        cx = rx + ((i - 1) % cols_) * cell
        cy = gy + ((i - 1) // cols_) * cell
        s = cell - gapc
        if i in unreg:
            c.rect(cx + .6, cy + .6, s - 1.2, s - 1.2, fill=PAPER, stroke=INK, sw=1.2)
        elif i in manual:
            c.rect(cx, cy, s, s, fill=PALE)
            c.rect(cx + .6, cy + .6, s - 1.2, s - 1.2, stroke=INK, sw=1.2)
        else:
            c.rect(cx, cy, s, s, fill=NEUTRAL)
        if i in invalid:
            c.path(f"M{r2(cx + 6)} {r2(cy + 6)} L{r2(cx + s - 6)} {r2(cy + s - 6)} M{r2(cx + s - 6)} {r2(cy + 6)} L{r2(cx + 6)} {r2(cy + s - 6)}", sw=1.8)
            c.text(cx + s / 2, cy - 0 + s + 12, "", 10)
    ly = gy + 10 * cell + 30
    items = [("full", f"{KL['roster']['registrert']} registrert"), ("half", f"{KL['roster']['manuelt_registrert']} manuelt registrert"),
             ("empty", f"{KL['roster']['uregistrert']} uregistrert")]
    lxx = rx
    for kind, tx in items:
        if kind == "full":
            c.rect(lxx, ly - 13, 16, 16, fill=NEUTRAL)
        elif kind == "half":
            c.rect(lxx, ly - 13, 16, 16, fill=PALE, stroke=INK, sw=1.2)
        else:
            c.rect(lxx, ly - 13, 16, 16, fill=PAPER, stroke=INK, sw=1.2)
        c.text(lxx + 24, ly, tx, 15, 500)
        lxx += 24 + tw(tx, 15, 500) + 28
    c.path(f"M{lxx} {ly - 13} l14 14 M{lxx + 14} {ly - 13} l-14 14", sw=1.8)
    c.text(lxx + 24, ly, "4 ugyldige rader", 15, 500)
    y2 = ly + 44
    c.text(rx, y2, "Uregistrert, ikke utløpt", 16, 700)
    rows2 = [("Rad 141", "Tom e-postcelle", "Legg inn adresse"), ("Rad 203", "Skrivefeil i adressen", "Rett og send"), ("Rad 12", "Invitasjon sendt, ikke åpnet", "Send påminnelse")]
    yy = y2 + 28
    for a, b, d in rows2:
        c.text(rx, yy, a, 14, 600)
        c.text(rx + 72, yy, b, 14)
        c.text(rx + 660, yy, d, 14, 600, INK, "end")
        c.line(rx + 660 - tw(d, 14, 600), yy + 4, rx + 660, yy + 4, stroke=INK)
        yy += 28
    c.text(rx, yy + 16, "Rad 37 og 88 er rettet og registrert manuelt. Hele lista kan vises som tabell.", 13, 400, INK2)
    c.text(64, 978, "Demodata", 13, 400, INK2)
    c.save()


# ---------------------------------------------------------------- 03 lærer spill


def page_03():
    c = C("03-laerer-spill", 1440, 1100, "Matrise: Klasseøkt",
          "Forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling av 60 spill à 4.", "laerer-spill")
    c.text(64, 54, "Klasseøkt", 28, 700)
    c.text(214, 54, "class-of-1994, IBE160", 14, 400, INK2)
    c.rect(1376 - 196, 26, 196, 44, fill=INK, rx=4)
    c.text(1376 - 98, 54, "Lagre uten endring", 15, 600, WHITE, "middle")
    c.text(64, 82, "Spillinnstillinger: «Klassisk». Alt er forhåndsutfylt, og du kan lagre som det står.", 14, 400, INK2)
    lx, w = 64, 620
    c.text(lx, 124, "Etterspørsel", 16, 700)
    cw = w / 36
    strip(c, lx, 134, DEM, QTY, cw, 44, gap=1.5, size=11)
    week_axis(c, lx, 196, 36, cw, 12)
    c.text(lx + w, 220, "Under spillet ser bare Detaljist denne raden, én uke om gangen.", 13, 400, INK2, "end")
    params = [("Startlager", "12"), ("Enheter i hvert ledd", "4"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
              ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50"), ("Restordrekost", "1,00"), ("Lengde", "36 uker"),
              ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t")]
    yy = 262
    for i, (a, b) in enumerate(params):
        xx = lx + (i % 2) * 320
        y_ = yy + (i // 2) * 40
        c.text(xx, y_, a, 14, 400, INK2)
        c.text(xx + 296, y_, b, 14, 600, INK, "end")
        c.line(xx, y_ + 11, xx + 296, y_ + 11)
    yy += 5 * 40 + 8
    c.para(lx, yy, "Kildene er uenige om forsinkelsene. Disse er produktets standard, og du kan endre dem.", w, 13, 1.35, 400, INK2)
    yy += 50
    field(c, lx, yy, 300, "KI-modus", "LLM-spillere")
    field(c, lx + 320, yy, 300, "Debrief-modus", "Gruppedebrief")
    yy += 88
    c.rect(lx, yy, 20, 20, fill=INK, rx=2)
    c.path(f"M{lx + 4.5} {yy + 10} l4 4 l7 -8", stroke=WHITE, sw=2)
    c.text(lx + 30, yy + 15, "Obligatorisk", 15, 600)
    c.text(lx + 130, yy + 15, "for hele Klassen", 14, 400, INK2)
    yy += 66
    c.text(lx, yy, "Datoer", 16, 700)
    yy += 12
    dates = [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]
    for i, (a, b) in enumerate(dates):
        field(c, lx + i * 157, yy + 12, 148, a, b, h=38, size=14)
    yy += 98
    c.text(lx, yy, "Labtimer, Datalab A2", 16, 700)
    labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    yy += 28
    for i, t in enumerate(labs):
        c.text(lx + i * 157, yy, t, 14)
        c.line(lx + i * 157, yy + 10, lx + i * 157 + 145, yy + 10)
    # høyre: fordeling
    rx = 760
    c.line(rx - 38, 110, rx - 38, 1040)
    c.text(rx, 124, "Fordeling", 22, 700)
    c.text(rx, 150, "240 studenter fordelt tilfeldig i 60 spill à 4.", 15, 400, INK2)
    # matrise: 60 spill x 4 roller
    ty = 196
    cell, rw2 = 7.5, 0
    colsn, rowsn = 10, 6
    tile_w, tile_h = 60, 84
    for i in range(60):
        cx = rx + (i % colsn) * tile_w
        cy = ty + (i // colsn) * tile_h
        c.text(cx, cy + 12, i + 1, 12, 700 if i + 1 == 17 else 400, INK if i + 1 == 17 else INK2)
        for k in range(4):
            c.rect(cx, cy + 18 + k * 12, 50, 10.5, fill=PALE)
        if i + 1 == 17:
            c.rect(cx - 3, cy + 15, 56, 52, stroke=INK, sw=1.6)
    by = ty + rowsn * tile_h + 14
    c.text(rx, by, "Hver rute er ett spill med fire seter, fra Detaljist øverst til Fabrikk nederst.", 13, 400, INK2)
    c.text(rx, by + 38, "Spill 17", 16, 700)
    seats = [("Detaljist", "Ida"), ("Grossist", "Sara"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]
    for i, (a, b) in enumerate(seats):
        c.text(rx + i * 150, by + 64, a, 13, 400, INK2)
        c.text(rx + i * 150, by + 84, b, 15, 600)
    bb = by + 118
    c.rect(rx, bb, 180, 48, stroke=INK, sw=1.2, rx=4)
    c.text(rx + 90, bb + 30, "Kjør på nytt", 15, 600, INK, "middle")
    c.rect(rx + 192, bb, 238, 48, fill=INK, rx=4)
    c.text(rx + 311, bb + 30, "Bekreft fordeling", 15, 600, WHITE, "middle")
    c.para(rx, bb + 78, "Tomme seter fylles av KI-spillere og merkes. Fordelingen kan kjøres på nytt til du bekrefter.", 560, 14, 1.4, 400, INK2)
    c.text(64, 1078, "Demodata", 13, 400, INK2)
    c.save()


# ---------------------------------------------------------------- 04 student hjem


def page_04():
    c = C("04-student-hjem", 1000, 900, "Matrise: student på mobil",
          "To telefoner: registrering fra Invitasjon, og hjem under spill med seter, seks steg, frist og Labtimer.", "student-hjem")
    s = .96
    x1, x2, y = 68, 558, 50
    c.text(x1, 34, "Registrering fra Invitasjon", 15, 600)
    c.text(x2, 34, "Hjem under spill", 15, 600)
    phone_frame(c, x1, y, s)
    c.text(18, 66, "Matrise", 15, 700)
    y_ = c.para(18, 116, "Du er invitert til IBE160", 340, 28, 1.12, 700)
    y_ = c.para(18, y_ + 2, "Faglærer Bård har lagt deg til i Klassen class-of-1994. Invitasjonen er gyldig i 14 dager.", 350, 15, 1.42, 400, INK2) + 20
    field(c, 18, y_, 354, "Navn", "Sara Berg", h=48)
    field(c, 18, y_ + 82, 354, "E-post, fra Klasselista", "sara.berg@student.example.no", h=48, fill=BG, size=14)
    field(c, 18, y_ + 164, 354, "Velg passord", "••••••••••", h=48)
    c.rect(18, y_ + 244, 354, 56, fill=INK, rx=4)
    c.text(195, y_ + 278, "Opprett konto", 17, 600, WHITE, "middle")
    c.para(18, y_ + 326, "Du trenger konto for å spille. Du spiller på denne telefonen, og du kan fortsette fra en annen.", 354, 14, 1.42, 400, INK2)
    c.end()
    phone_frame(c, x2, y, s)
    c.text(18, 58, "Sara", 26, 700)
    c.text(372, 58, "Spill 17, Grossist", 15, 500, INK, "end")
    c.rect(18, 76, 354, 92, fill=INK, rx=4)
    c.text(32, 106, "Spillet venter på deg", 18, 600, WHITE)
    c.text(32, 128, "Uke 11. Ida og Mikkel har bestilt.", 14, 400, WHITE)
    c.text(32, 152, "Gå til spillet", 15, 600, WHITE)
    c.line(32, 157, 32 + tw("Gå til spillet", 15, 600), 157, stroke=WHITE)
    yy = 200
    c.text(18, yy, "Setene", 15, 700)
    yy += 26
    seat_list(c, yy, [("Detaljist", "Ida", "har bestilt", True), ("Grossist", "Sara (deg)", "venter", False),
                      ("Distributør", "Mikkel", "har bestilt", True), ("Fabrikk", "Jonas", "venter, 3 min", False)], pitch=26)
    yy += 4 * 26 + 12
    c.text(18, yy, "Stegene", 15, 700)
    yy += 12
    steps = [("Klassespill", "pågår", True), ("Debrief", "", False), ("Quiz", "", False), ("Replay", "", False), ("Individuell test", "", False), ("Rapport", "", False)]
    for i, (a, st, act) in enumerate(steps):
        c.rect(18, yy, 354, 28, fill=NEUTRAL if act else BG)
        col = WHITE if act else INK2
        c.text(30, yy + 19, a, 14, 600 if act else 400, col)
        c.text(360, yy + 19, st or "ikke åpnet", 13, 500 if act else 400, col, "end")
        yy += 30
    yy += 22
    c.text(18, yy, "Neste frist", 14, 400, INK2)
    c.text(372, yy, "Spillfrist ti. 8. des", 14, 600, INK, "end")
    c.line(18, yy + 10, 372, yy + 10)
    yy += 32
    c.text(18, yy, "Labtimer, Datalab A2", 14, 400, INK2)
    c.text(372, yy, "to. 26. nov 14:15", 14, 600, INK, "end")
    c.text(372, yy + 20, "ma. 30. nov 10:15", 14, 400, INK, "end")
    c.text(372, yy + 40, "to. 3. des 14:15", 14, 400, INK, "end")
    c.text(18, 824, "Demodata", 13, 400, INK2)
    c.end()
    c.save()


# ---------------------------------------------------------------- 09 kontaktark


def tile_header(c, x, y, title, line, w):
    c.text(x, y, title, 15, 700)
    c.para(x, y + 19, line, w, 12, 1.3, 400, INK2)


def mini_rows(c, x, y, w, block, role, T, h=9):
    cw = w / T
    for lab, vals, sc in rows_for(block, role, T):
        vv = vals if lab != "Egen ordre" else block[role]["ordre"][:T]
        strip(c, x, y, vv, sc, cw, h, gap=.6, numbers=False)
        y += h + 1
    return y


def mini_lines(c, x, y, w, ws):
    for fr in ws:
        c.rect(x, y, w * fr, 5, fill=RULE)
        y += 11
    return y


def page_09():
    c = C("09-alle-sider", 2000, 1400, "Matrise: alle andre sider",
          "Kontaktark over øvrige sider gruppert per rolle: Student, Faglærer og Admin.", "alle-sider")
    c.text(50, 50, "Alle andre sider, samme grammatikk", 28, 700)
    TW, TH = 352, 232
    GX, GY = 14, 16
    x0 = 150

    def tile(col, row_y, title, line):
        x = x0 + col * (TW + GX)
        c.rect(x, row_y, TW, TH, fill=PAPER, stroke=RULE, rx=3)
        tile_header(c, x + 14, row_y + 24, title, line, TW - 28)
        return x + 14, row_y + 68, TW - 28

    Y1, Y2, Y3, Y4, Y5 = 76, 76 + TH + GY, 76 + 2 * (TH + GY) + 18, 76 + 3 * (TH + GY) + 18, 76 + 4 * (TH + GY) + 36
    c.text(50, Y1 + 24, "Student", 18, 700)
    c.text(50, Y3 + 24, "Faglærer", 18, 700)
    c.text(50, Y5 + 24, "Admin", 18, 700)
    # Student
    x, y, w = tile(0, Y1, "Invitasjon og registrering", "Lenke fra e-post, navn og passord, konto i Klassen.")
    mini_lines(c, x, y, w, [.8, .5])
    c.rect(x, y + 34, w * .5, 22, fill=INK, rx=2)
    c.text(x + 10, y + 50, "Opprett konto", 12, 600, WHITE)
    x, y, w = tile(1, Y1, "Logg inn", "E-post og passord. Ingen offentlig registrering.")
    c.rect(x, y, w * .7, 24, stroke=RULE2, rx=2)
    c.rect(x, y + 32, w * .7, 24, stroke=RULE2, rx=2)
    c.rect(x, y + 66, w * .34, 24, fill=INK, rx=2)
    c.text(x + 10, y + 82, "Logg inn", 12, 600, WHITE)
    x, y, w = tile(2, Y1, "Regler før første ordre", "Fem rader forklart med ekte celler, ett heltall per uke.")
    mini_rows(c, x, y, w * .55, S17, "Grossist", 5, 13)
    c.para(x + w * .6, y + 10, "Lager endres med levering minus ordre inn.", w * .4, 12, 1.3)
    x, y, w = tile(3, Y1, "Startoppgave", "Veiledet Uke 1–4: Hvor mye står på vei?")
    mini_rows(c, x, y, w * .5, S17, "Grossist", 4, 13)
    c.para(x + w * .56, y + 10, f"Posisjon {G['lager'][0]} − {G['restordre'][0]} + {G['paa_vei'][0]} = {POSG[0]}. Tast svaret ditt.", w * .44, 12, 1.3)
    x, y, w = tile(4, Y1, "Replay", "Ny runde mot KI-spillere, 33 uker, tilfeldig etterspørsel. Rad 6 er Posisjon.")
    RG = REPLAY["serier"]["Grossist"]
    yy = mini_rows(c, x, y, w, REPLAY["serier"], "Grossist", 20, 13)
    pp = [a - b + d for a, b, d in zip(RG["lager"], RG["restordre"], RG["paa_vei"])][:20]
    strip(c, x, yy + 2, pp, NET, w / 20, 16, gap=.6, numbers=False)
    x, y, w = tile(0, Y2, "Replay-gjennomgang", "Klassespill og Replay over hverandre. «Ikke like for like.»")
    n1 = NETG[:33]
    n2 = [a - b for a, b in zip(RG["lager"], RG["restordre"])]
    c.text(x, y + 10, "Klassespill", 12, 400, INK2)
    strip(c, x, y + 14, n1, NET, w / 33, 26, gap=.6, numbers=False)
    c.text(x, y + 56, "Replay", 12, 400, INK2)
    strip(c, x, y + 60, n2, NET, w / 33, 26, gap=.6, numbers=False)
    x, y, w = tile(1, Y2, "Individuell test", "Flervalg, tegne-/tabelloppgave der du fyller celler, og langsvar.")
    cwt = w / 14
    strip(c, x, y, NETG[10:18], NET, cwt, 22, gap=1, size=11)
    for i in range(8, 14):
        c.rect(x + i * cwt, y, cwt - 1, 22, fill=WHITE, stroke=RULE2)
    c.text(x, y + 42, "Fyll inn saldoraden for Uke 19–24.", 12)
    mini_lines(c, x, y + 56, w, [.9, .7, .8])
    x, y, w = tile(2, Y2, "KI-vurdering", "Teller ikke, er aldri en karakter. KI-generert, kan ta feil.")
    c.para(x, y + 8, "Du regner med det som er på vei i svar 2, men ikke i tegneoppgaven.", w, 13, 1.35)
    mini_lines(c, x, y + 56, w, [.8, .6])
    x, y, w = tile(3, Y2, "Studentrapport (PDF)", "Din matrise, Forklaring, Replay og test på noen få sider.")
    c.rect(x, y, 96, 130, fill=WHITE, stroke=RULE2)
    mini_rows(c, x + 6, y + 8, 84, S17, "Grossist", 36, 5)
    mini_lines(c, x + 6, y + 50, 84, [.9, .7, .8, .6])
    mini_lines(c, x + 112, y + 6, w - 112, [.9, .7, .8, .5])
    x, y, w = tile(4, Y2, "Alle spill side om side", "Etter Debriefen: din matrise i klassen, uten navn eller rangering.")
    random.seed(17)
    done = [g for g in GAMES if g["status"] == "ferdig"][:15]
    cw_ = w / 36
    yy = y
    for g in done:
        vals = g["netto_lager"]["Grossist"]
        for i, v in enumerate(vals):
            c.rect(x + i * cw_, yy, cw_ - .4, 8.4, fill=NET.fill(v))
        yy += 9
    # Faglærer
    x, y, w = tile(0, Y3, "Lærerhjem", "Klasser, neste frist, hvor mange som venter nå.")
    mini_lines(c, x, y, w, [.6, .85, .5])
    c.rect(x, y + 40, w, 26, fill=INK, rx=2)
    c.text(x + 10, y + 57, "Spill 2 venter på Noah, 23 t", 12, 600, WHITE)
    x, y, w = tile(1, Y3, "Klasserapport", "Trakt, kjedekost og Forsterkning per Rolle for de ferdige spillene.")
    yy = y
    for r in UP:
        q = KL["ferdige"]["forsterkning_per_rolle"][r]
        c.text(x, yy + 12, r, 12)
        sc = (w - 100) / 13
        c.rect(x + 86 + q["q1"] * sc, yy + 2, (q["q3"] - q["q1"]) * sc, 12, fill=PALE)
        c.rect(x + 86 + q["median"] * sc - 1, yy, 2.5, 16, fill=INK)
        c.text(x + w, yy + 12, amp(q["median"]), 12, 600, INK, "end")
        yy += 22
    c.text(x, yy + 12, "Boks: kvartiler. Strek: median.", 12, 400, INK2)
    x, y, w = tile(2, Y3, "Spillinnsikt", "Uke for uke for ett spill: fire Roller, ordre, med logg.")
    cw_ = w / 36
    yy = y
    for r in UP:
        strip(c, x, yy, S17[r]["ordre"], QTY, cw_, 22, gap=.6, numbers=False)
        yy += 23
    strip(c, x, yy + 4, DEM, QTY, cw_, 18, gap=.6, numbers=False)
    x, y, w = tile(3, Y3, "Studentside", "Én student: steg, Forklaring, ordre per uke, KI-vurdering.")
    mini_rows(c, x, y, w, S17, "Grossist", 36, 10)
    mini_lines(c, x, y + 66, w, [.9, .6])
    x, y, w = tile(4, Y3, "Alle spill i plenum", "Hele bildet på storskjerm, bare spillnummer, Rolle kan byttes.")
    gs = [g for grp in groups() for g in grp[2]]
    cw_, rh_ = w / 36, 2.65
    yy = y
    for g in gs:
        for i, v in enumerate(g["netto_lager"]["Fabrikk"]):
            c.rect(x + i * cw_, yy, cw_ - .3, rh_ - .2, fill=NET.fill(v))
        yy += rh_
    x, y, w = tile(0, Y4, "Tverrklasse-statistikk", "Denne klassen mot fjorårets, median Kjede og Fabrikk.")
    a = KL["ferdige"]["kjedekost"]["median"]
    b = KL["fjoraaret"]["median_kjedekost"]
    sc = (w - 100) / 3000
    for i, (lab, v) in enumerate(((KL["fjoraaret"]["klasse"], b), ("class-of-1994", a))):
        c.text(x, y + 16 + i * 34, lab, 12)
        c.rect(x + 90, y + 4 + i * 34, v * sc, 18, fill=NEUTRAL if i else PALE)
    c.text(x, y + 90, f"{nf(a)} kr mot {nf(b)} kr. Fabrikk {amp(KL['ferdige']['forsterkning_per_rolle']['Fabrikk']['median'])} mot {amp(KL['fjoraaret']['median_forsterkning_fabrikk'])}.", 12)
    x, y, w = tile(1, Y4, "Meldinger", "Til ett sete, ett spill eller hele Klassen. Ingen chat mellom spillere.")
    for i, t in enumerate(["Noah, Spill 2: Gruppa venter på deg", "Hele Klassen: Labtime to. 26. nov", "Spill 30: Ida, ordre mangler"]):
        c.text(x, y + 14 + i * 26, t, 12)
        c.line(x, y + 22 + i * 26, x + w, y + 22 + i * 26)
    x, y, w = tile(2, Y4, "Lærers testspill", "Spill selv med tre KI-spillere, merket som test.")
    mini_rows(c, x, y, w, REPLAY["serier"], "Detaljist", 18, 12)
    x, y, w = tile(3, Y4, "Mønstre i klassen", "Detected patterns i Spillinnsikt, med antall spill.")
    yy = y + 14
    for k, v in KL["moenstre"].items():
        c.para(x, yy, k, w - 50, 12, 1.3)
        c.text(x + w, yy, v, 12, 700, INK, "end")
        yy += 36
    # Admin
    x, y, w = tile(0, Y5, "Admin-område", "Klasser, drift, feillogg, for plattformeieren.")
    mini_lines(c, x, y, w, [.9, .7, .8, .5])
    x, y, w = tile(1, Y5, "Brukere og roller", "Faglærer, assistent, student, admin. Tilgang via Invitasjon.")
    for i, t in enumerate(["Bård, Faglærer", "Assistent, Faglærer", "Sara, Student"]):
        c.text(x, y + 14 + i * 26, t, 12)
        c.line(x, y + 22 + i * 26, x + w, y + 22 + i * 26)
    x, y, w = tile(2, Y5, "KI-kostnad", "Per Klasse og per uke, med grense og varsel.")
    mini_lines(c, x, y, w, [.7, .9, .5])
    c.text(1950, 1384, "Lavere detaljnivå. Grafene bruker ekte serier fra demodata.", 13, 400, INK2, "end")
    c.save()


if __name__ == "__main__":
    for fn in (page_01, page_02, page_03, page_04, page_05, page_06, page_07, page_08, page_09, page_10):
        fn()
    print("Skalaer")
    for s_ in (NET, QTY):
        print(s_.name, [(b[3], b[2], round(contrast(s_.ink(b[0] if b[0] > -INF else b[1]), b[2]), 1)) for b in s_.bins])
    print("CVD rust/blågrønn samme steg", CVD_REPORT)
