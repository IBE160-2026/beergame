"""Grafgrammatikken i konsept 01 Modellen: aksonometrisk snitt, kurve, nå-kant, tomter.

Alt tegnes fra ../_shared/fixture.json. Ingen tall i en graf tastes inn for hånd.
"""
import html
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
S17 = FX["spill17"]["serier"]
GROSSIST = S17["Grossist"]

# Palett
KALK = "#F5F6F5"     # grunn
HVIT = "#FFFFFF"     # modellens flater
SIDE = "#ECEEEE"     # modellens skyggeside
LINJE = "#B3B9BD"    # tynne linjer i modellen
GRID = "#E1E4E5"     # hjelpelinje
KULL = "#23272B"     # snitt og tekst
KULL2 = "#555C63"    # sekundær tekst
ORDRE = "#225A93"    # ordrer
ORDRE_FLATE = "#E7EEF4"
ORDRE_SIDE = "#D8E3EC"
SKYGGE = "#7C96AB"   # det som har vært, linje
SKYGGE_FLATE = "#DCE4EA"  # det som har vært, flate
NA = "#B08D2E"       # bare nå

TAN = "Epilogue"
FONTS = (
    "@import url('https://fonts.googleapis.com/css2?family=Epilogue:wght@400;500;600"
    "&amp;family=Hanken+Grotesk:wght@400;500;600&amp;display=swap');"
)
NUM = re.compile(r"[−+]?\d[\d ,.:]*\d×?|[−+]?\d×?")
NB = " "


def kr(v, enhet=True):
    s = f"{v:,.2f}".replace(",", NB).replace(".", ",")
    return s + (f"{NB}kr" if enhet else "")


def tusen(v):
    return f"{int(v):,}".replace(",", NB)


def faktor(v):
    return f"{v:.1f}".replace(".", ",") + "×"


def tegn(v):
    return f"−{abs(v)}" if v < 0 else f"{v}"


def est(s, size):
    """Grovt anslag av tekstbredde i Epilogue."""
    return len(s) * size * 0.525


class Doc:
    def __init__(self, name, w, h, title, desc):
        self.name, self.w, self.h = name, w, h
        self.title, self.desc = title, desc
        self.parts = []
        self.defs = []
        self.pid = f"d01-{name}-"
        self.defs.append(
            f'<pattern id="{self.pid}hatch" width="4.2" height="4.2" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)"><rect width="4.2" height="4.2" fill="{HVIT}"/>'
            f'<line x1="0" y1="0" x2="0" y2="4.2" stroke="{KULL}" stroke-width="0.9"/></pattern>'
        )
        self.defs.append(
            f'<pattern id="{self.pid}kihatch" width="3.6" height="3.6" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(-45)"><rect width="3.6" height="3.6" fill="{ORDRE_FLATE}"/>'
            f'<line x1="0" y1="0" x2="0" y2="3.6" stroke="{ORDRE}" stroke-width="0.9"/></pattern>'
        )

    @property
    def hatch(self):
        return f"url(#{self.pid}hatch)"

    @property
    def kihatch(self):
        return f"url(#{self.pid}kihatch)"

    def add(self, s):
        self.parts.append(s)

    def open(self, transform):
        self.add(f'<g transform="{transform}">')

    def close(self):
        self.add("</g>")

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1, rx=0, dash=None, crisp=False):
        a = f'x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if rx:
            a += f' rx="{rx}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if crisp:
            a += ' shape-rendering="crispEdges"'
        self.add(f"<rect {a}/>")

    def line(self, x1, y1, x2, y2, stroke=KULL, sw=1, dash=None, cap=None):
        a = f'x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if cap:
            a += f' stroke-linecap="{cap}"'
        self.add(f"<line {a}/>")

    def poly(self, pts, fill="none", stroke=None, sw=1, dash=None, join="miter"):
        p = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        a = f'points="{p}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="{join}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        self.add(f"<polygon {a}/>")

    def path(self, d, fill="none", stroke=None, sw=1, dash=None, crisp=False, join="miter"):
        a = f'd="{d}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="{join}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if crisp:
            a += ' shape-rendering="crispEdges"'
        self.add(f"<path {a}/>")

    def text(self, x, y, s, size=13, w=400, fill=KULL, a="start", ls=None):
        s = str(s)
        out, pos = [], 0
        for m in NUM.finditer(s):
            if m.start() > pos:
                out.append(html.escape(s[pos:m.start()], quote=False))
            out.append(f'<tspan class="d01-n">{html.escape(m.group(), quote=False)}</tspan>')
            pos = m.end()
        out.append(html.escape(s[pos:], quote=False))
        extra = f' letter-spacing="{ls}"' if ls else ""
        anchor = "" if a == "start" else f' text-anchor="{a}"'
        self.add(
            f'<text class="d01-t" x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}"{anchor}{extra} xml:space="preserve">{"".join(out)}</text>'
        )

    def wrap(self, x, y, s, width, size=13, lh=None, w=400, fill=KULL, a="start"):
        lh = lh or size * 1.42
        for line in wrap_lines(s, width, size):
            self.text(x, y, line, size=size, w=w, fill=fill, a=a)
            y += lh
        return y

    def render(self):
        style = (
            f"{FONTS}"
            f".d01-t{{font-family:'{TAN}','Hanken Grotesk','Helvetica Neue',Arial,sans-serif;}}"
            ".d01-n{font-family:'Hanken Grotesk','Helvetica Neue',Arial,sans-serif;"
            "font-variant-numeric:tabular-nums lining-nums;font-feature-settings:'tnum' 1,'lnum' 1;}"
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
            f"font-family=\"'{TAN}','Hanken Grotesk','Helvetica Neue',Arial,sans-serif\">"
            f"<title>{html.escape(self.title)}</title><desc>{html.escape(self.desc)}</desc>"
            f"<style>{style}</style><defs>{''.join(self.defs)}</defs>"
            f'<rect width="{self.w}" height="{self.h}" fill="{KALK}"/>'
            + "".join(self.parts)
            + "</svg>"
        )

    def save(self):
        (HERE / f"{self.name}.svg").write_text(self.render(), encoding="utf-8")


def wrap_lines(s, width, size):
    lines, cur = [], ""
    for word in s.split(" "):
        t = (cur + " " + word).strip()
        if est(t, size) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


# ---- data ----

def pipeline(S, w):
    """Hva som er på vei ved Uke w, før ukas ordre.

    Levering neste to uker er allerede sendt. Ordren fra forrige uke er bestilt, ikke sendt.
    Resten er bestilt tidligere og ikke sendt av leverandøren: ingen kjent ankomstuke.
    """
    n = len(S["levering"])
    sendt1 = S["levering"][w] if w < n else 0
    sendt2 = S["levering"][w + 1] if w + 1 < n else 0
    forrige = S["ordre"][w - 2] if w >= 2 else 4
    total = S["paa_vei"][w - 1]
    rest = total - sendt1 - sendt2 - forrige
    felt = [
        {"uke": w + 1, "n": sendt1, "sendt": True},
        {"uke": w + 2, "n": sendt2, "sendt": True},
        {"uke": w + 3, "n": forrige, "sendt": False},
    ]
    return felt, max(rest, 0), total


def sendt(S, w):
    """Sendt i Uke w, regnet fra lagerbalansen: forrige Lager + Levering − Lager."""
    forrige = S["lager"][w - 2] if w >= 2 else 12
    return forrige + S["levering"][w - 1] - S["lager"][w - 1]


def netto(S):
    return [a - b for a, b in zip(S["lager"], S["restordre"])]


def posisjon(S):
    return [a - b + c for a, b, c in zip(S["lager"], S["restordre"], S["paa_vei"])]


# ---- aksonometri ----

class Axo:
    """Planoblikk: planen er sann og rotert theta grader, høyder er sanne."""

    def __init__(self, ox, oy, theta=24):
        self.ox, self.oy = ox, oy
        self.c, self.s = math.cos(math.radians(theta)), math.sin(math.radians(theta))

    def pt(self, u, v, z=0):
        return (self.ox + u * self.c - v * self.s, self.oy - u * self.s - v * self.c - z)


def stabel(d, ax, u0, u1, v0, v1, h, k, kind="lager", dash=None, tick=True):
    """En søyle til skala: én linje per enhet, sterkere hver femte."""
    if kind == "lager":
        stroke, front, left, top, t1, t5 = KULL, HVIT, SIDE, HVIT, "#B9BEC2", "#6A7178"
    elif kind == "ny":
        stroke, front, left, top, t1, t5 = ORDRE, HVIT, HVIT, HVIT, "#BCCFDF", "#7EA0BF"
    else:
        stroke, front, left, top, t1, t5 = ORDRE, ORDRE_FLATE, ORDRE_SIDE, "#F3F6F9", "#A9C0D3", "#5F88AC"
    p = ax.pt
    if h <= 0:
        return
    d.poly([p(u0, v0, 0), p(u0, v1, 0), p(u0, v1, h), p(u0, v0, h)], fill=left)
    d.poly([p(u0, v0, 0), p(u1, v0, 0), p(u1, v0, h), p(u0, v0, h)], fill=front)
    if tick:
        units = round(h / k)
        each = 1 if k >= 1.9 else 5
        for i in range(each, units, each):
            z = i * k
            col, sw = (t5, 0.55) if i % 5 == 0 else (t1, 0.35)
            a, b, c = p(u0, v1, z), p(u0, v0, z), p(u1, v0, z)
            d.path(f"M{a[0]:.2f} {a[1]:.2f}L{b[0]:.2f} {b[1]:.2f}L{c[0]:.2f} {c[1]:.2f}", stroke=col, sw=sw)
    d.poly([p(u0, v0, h), p(u1, v0, h), p(u1, v1, h), p(u0, v1, h)], fill=top, stroke=stroke, sw=0.9, dash=dash)
    d.poly([p(u0, v0, 0), p(u1, v0, 0), p(u1, v0, h), p(u0, v0, h)], stroke=stroke, sw=0.9, dash=dash)
    a, b, c = p(u0, v0, 0), p(u0, v1, 0), p(u0, v1, h)
    d.path(f"M{a[0]:.2f} {a[1]:.2f}L{b[0]:.2f} {b[1]:.2f}L{c[0]:.2f} {c[1]:.2f}", stroke=stroke, sw=0.9, dash=dash)


def na_kant(d, x, y1, y2, sw=1.8):
    """Den ene varme linja. Samme kant i modell, kurve, debrief og oversikt."""
    d.line(x, y1, x, y2, stroke=NA, sw=sw)


def snitt(d, ox, oy, k, w, S, new=None, bekreftet=False, A=150, D=56, H=36, c=42, c2=30, f=30, g=6,
          dv=26, fs=13, labels=True, uker=True, rad=True, theta=24, tall=True, kant=True):
    """Seksjonen: hall, Lager, Restordre under nullplanet, På vei utenfor bygget.

    (ox, oy) er der snittet og nå-planet møtes. Alt til venstre har skjedd, alt til høyre er på vei.
    """
    ax = Axo(ox, oy, theta)
    p = ax.pt
    lager = S["lager"][w - 1]
    rest = S["restordre"][w - 1]
    felt, uten, total = pipeline(S, w)

    # Tomt utenfor hallen
    n_felt = 4 + (1 if uten else 0)
    if rad:
        end = g + n_felt * (f + g)
        d.poly([p(0, 0), p(end, 0), p(end, dv + 8), p(0, dv + 8)], fill=HVIT, stroke=LINJE, sw=0.6)

    # Hallen: gulv, to vegger bak. Fronten er skåret bort.
    d.poly([p(-A, 0), p(0, 0), p(0, D), p(-A, D)], fill=HVIT, stroke=LINJE, sw=0.6)
    n = int(A // 15)
    for i in range(1, n):
        a, b = p(-i * 15, 0), p(-i * 15, D)
        d.line(a[0], a[1], b[0], b[1], stroke=GRID, sw=0.4)
    for i in range(1, int(D // 15) + 1):
        a, b = p(-A, i * 15), p(0, i * 15)
        d.line(a[0], a[1], b[0], b[1], stroke=GRID, sw=0.4)
    d.poly([p(-A, D, 0), p(0, D, 0), p(0, D, H), p(-A, D, H)], fill=SIDE, stroke=LINJE, sw=0.6)
    d.poly([p(0, 0, 0), p(0, D, 0), p(0, D, H), p(0, 0, H)], fill=HVIT, stroke=LINJE, sw=0.6)
    d.poly([p(-A, 0, 0), p(-A, D, 0), p(-A, D, H), p(-A, 0, H)], fill="none", stroke=LINJE, sw=0.4)

    # Lager
    stabel(d, ax, -c, 0, 0, c2, lager * k, k, "lager")

    # Restordre: skravert snitt under nullplanet
    if rest > 0:
        d.poly([p(-c, 0, 0), p(0, 0, 0), p(0, 0, -rest * k), p(-c, 0, -rest * k)],
               fill=d.hatch, stroke=KULL, sw=0.9)

    # På vei, lengst borte først
    if rad:
        items = []
        for i, it in enumerate(felt):
            items.append((i, it["n"], "vei", None if it["sendt"] else "3 2", it["uke"]))
        if new is not None:
            items.append((3, new, "vei" if bekreftet else "ny", "3 2", felt[-1]["uke"] + 1))
        if uten:
            items.append((4, uten, "vei", "3 2", None))
        for i, n_u, kind, dash, uke in sorted(items, key=lambda t: -t[0]):
            u0 = g + i * (f + g)
            stabel(d, ax, u0, u0 + f, 0, dv, n_u * k, k, kind, dash=dash)

    # Snittlinja er den tyngste linja på tegningen
    end = g + n_felt * (f + g) if rad else 0
    a, b = p(-A, 0), p(0, 0)
    d.line(a[0], a[1], b[0], b[1], stroke=KULL, sw=1.6)
    if rad:
        e = p(end, 0)
        d.line(b[0], b[1], e[0], e[1], stroke=KULL, sw=0.9)

    # Terskelen: nå-kanten går over gulvet og opp gjennom søyla
    if kant:
        t = p(0, D)
        d.line(ox, oy, t[0], t[1], stroke=NA, sw=1.8)
        top = p(0, D, H)
        d.line(t[0], t[1], top[0], top[1], stroke=NA, sw=0.9)

    # Tall og etiketter
    if rad and tall:
        for i, n_u, kind, dash, uke in items:
            u0 = g + i * (f + g)
            m = p(u0 + f / 2, dv / 2, n_u * k)
            d.text(m[0], m[1] - 5, n_u, size=fs, w=600 if kind == "ny" or (bekreftet and uke == felt[-1]["uke"] + 1) else 500,
                   fill=ORDRE if kind == "ny" else KULL, a="middle")
            if uker and uke:
                q = p(u0 + f / 2, 0)
                d.text(q[0], q[1] + fs + 2, uke, size=fs, fill=KULL2, a="middle")
            elif uker:
                q = p(u0 + f / 2, 0)
                d.text(q[0], q[1] + fs + 4, "uten dato", size=fs, fill=KULL2, a="middle")
    if labels:
        tanv = ax.s / ax.c
        xe = p(-c, 0)[0] - 8
        base = p(-c, 0)[1]
        xl = xe - (c2 * ax.s if lager else 0)
        d.text(xl, base - max(lager * k / 2, 6) - 4, f"Lager {lager}", size=fs, w=500, a="end")
        if rest > 0:
            s = f"Restordre {rest}"
            tw = est(s, fs)
            y = base + (tw + 8) * tanv + fs + 2
            d.text(xe, max(y, base + rest * k * 0.5), s, size=fs, w=500, a="end")
    return ax, total


# ---- kurven ----

def steg(xs, ys):
    out = []
    for x0, x1, y in zip(xs[:-1], xs[1:], ys):
        out += [(x0, y), (x1, y)]
    return out


def path_of(pts):
    return "M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in pts)


def kurve(d, xnow, y0, k, step, w, S, new=None, bekreftet=False, ytop=26, ybot=20, x_min=0, fs=13, etiketter=True,
          akse=True, grid=10, pos=False, ki_uker=(), siste_blaa=3, yetiketter=True, ordre=True):
    """Netto lager som stegflate (skravert under null) og egne ordrer som stolper. Høyre kant er nå."""
    net = netto(S)
    first = max(1, w - int((xnow - x_min) / step) + 1)
    x_of = lambda i: xnow - (w - i + 1) * step
    y_of = lambda v: y0 - v * k

    # hjelpelinjer
    xl = x_of(first)
    v = grid
    while v <= ytop:
        d.line(xl, y_of(v), xnow, y_of(v), stroke=GRID, sw=0.7)
        if yetiketter:
            d.text(xl - 5, y_of(v) + fs * 0.34, v, size=fs - 1, fill=KULL2, a="end")
        v += grid
    v = grid
    while v <= ybot:
        d.line(xl, y_of(-v), xnow, y_of(-v), stroke=GRID, sw=0.7)
        if yetiketter:
            d.text(xl - 5, y_of(-v) + fs * 0.34, f"−{v}", size=fs - 1, fill=KULL2, a="end")
        v += grid
    if yetiketter:
        d.text(xl - 5, y0 + fs * 0.34, "0", size=fs - 1, fill=KULL2, a="end")

    # netto: over null flate, under null skravur
    pos_d, neg_d = "", ""
    for i in range(first, w + 1):
        x = x_of(i)
        v = net[i - 1]
        if v > 0:
            pos_d += f"M{x:.2f} {y_of(v):.2f}h{step:.2f}V{y0:.2f}h{-step:.2f}Z"
        elif v < 0:
            neg_d += f"M{x:.2f} {y0:.2f}h{step:.2f}V{y_of(v):.2f}h{-step:.2f}Z"
    if pos_d:
        d.path(pos_d, fill=SKYGGE_FLATE, crisp=True)
    if neg_d:
        d.path(neg_d, fill=d.hatch, crisp=True)
    xs = [x_of(i) for i in range(first, w + 2)]
    ys = [y_of(net[i - 1]) for i in range(first, w + 1)]
    d.path(path_of(steg(xs, ys)), stroke=KULL, sw=1)

    # null
    d.line(xl, y0, xnow, y0, stroke=KULL, sw=1)

    # ordrer som stolper
    bw = max(1.4, step * 0.42)
    if ordre:
        for i in range(first, w):
            x = x_of(i) + (step - bw) / 2
            v = S["ordre"][i - 1]
            col = ORDRE if i >= w - siste_blaa else SKYGGE
            fill = d.kihatch if i in ki_uker else col
            d.rect(x, y_of(v), bw, v * k, fill=fill, stroke=ORDRE if i in ki_uker else None, sw=0.6, crisp=True)
    if new is not None and ordre:
        x = x_of(w) + (step - bw) / 2
        if bekreftet:
            d.rect(x, y_of(new), bw, new * k, fill=ORDRE, crisp=True)
        else:
            d.rect(x, y_of(new), bw, new * k, fill=HVIT, stroke=ORDRE, sw=0.9, dash="3 2")

    # posisjon: bare etter Debriefen
    if pos:
        ps = posisjon(S)
        ys2 = [y_of(ps[i - 1]) for i in range(first, w + 1)]
        d.path(path_of(steg(xs, ys2)), stroke=ORDRE, sw=1.6)

    # tidsakse uten slutt
    if akse:
        ay = y_of(-ybot) + 2
        d.line(xl, ay, xnow, ay, stroke=KULL2, sw=0.7)
        for i in range(first, w + 1):
            if (i == 1) or (i % 5 == 0 and (first > 1 or (i - 1) * step >= 44)):
                x = x_of(i) + step / 2
                d.line(x, ay, x, ay + 3, stroke=KULL2, sw=0.7)
                d.text(x, ay + fs + 3, i if i != 1 else "Uke 1", size=fs - 1, fill=KULL2, a="middle" if i != 1 else "start")
    return x_of, y_of


def inn_ut(d, xnow, ybase, k, step, w, S, fs=12, x_min=0, ymax=32):
    """P1: levering og innkommende ordre på samme akse. Arealet mellom er endringen i lageret."""
    first = max(1, w - int((xnow - x_min) / step) + 1)
    x_of = lambda i: xnow - (w - i + 1) * step
    y_of = lambda v: ybase - v * k
    xl = x_of(first)
    for v in range(10, ymax + 1, 10):
        d.line(xl, y_of(v), xnow, y_of(v), stroke=GRID, sw=0.7)
        d.text(xl - 5, y_of(v) + fs * 0.34, v, size=fs - 1, fill=KULL2, a="end")
    d.text(xl - 5, ybase + fs * 0.34, 0, size=fs - 1, fill=KULL2, a="end")
    pos_d, neg_d = "", ""
    for i in range(first, w + 1):
        x = x_of(i)
        a, b = S["levering"][i - 1], S["innkommende_ordre"][i - 1]
        if a > b:
            pos_d += f"M{x:.2f} {y_of(a):.2f}h{step:.2f}V{y_of(b):.2f}h{-step:.2f}Z"
        elif b > a:
            neg_d += f"M{x:.2f} {y_of(b):.2f}h{step:.2f}V{y_of(a):.2f}h{-step:.2f}Z"
    if pos_d:
        d.path(pos_d, fill=SKYGGE_FLATE, crisp=True)
    if neg_d:
        d.path(neg_d, fill=d.hatch, crisp=True)
    xs = [x_of(i) for i in range(first, w + 2)]
    d.path(path_of(steg(xs, [y_of(S["levering"][i - 1]) for i in range(first, w + 1)])), stroke=KULL, sw=1.2)
    d.path(path_of(steg(xs, [y_of(S["innkommende_ordre"][i - 1]) for i in range(first, w + 1)])), stroke=KULL2, sw=0.9, dash="3 2")
    d.line(xl, ybase, xnow, ybase, stroke=KULL, sw=0.8)
    return x_of, y_of


def rolle_linjer(d, x0, y0, k, step, w, serier=None, demand=None, labels=True, fs=12, sw=1.3):
    """Alle fire Rollers ordre i én graf. Blåtonen mørkner oppstrøms, og hver linje har navn."""
    serier = serier or S17
    cols = {"Detaljist": "#A6B9C9", "Grossist": "#7C96AB", "Distributør": "#4F7596", "Fabrikk": ORDRE}
    for r in ROLES:
        o = serier[r]["ordre"][:w]
        pts = [(x0 + (i + 0.5) * step, y0 - v * k) for i, v in enumerate(o)]
        d.path(path_of(pts), stroke=cols[r], sw=sw if r != "Fabrikk" else sw + 0.4, join="round")
    if demand:
        pts = steg([x0 + i * step for i in range(w + 1)], [y0 - v * k for v in demand[:w]])
        d.path(path_of(pts), stroke=KULL, sw=1.4)
    return cols


def tomt(d, x, y, w, h, sp, roller=("Detaljist", "Fabrikk"), ymax=32, valgt=False, label=True, fs=11, tekst=True):
    """Ett Klassespill i plansnittet. Ferdig er skyggeblått, aktivt er blått med nå-kant."""
    ferdig = sp["status"] == "ferdig"
    venter = sp["status"] == "venter"
    pauset = sp["status"] == "pauset"
    d.rect(x, y, w, h, fill=HVIT if not ferdig else "#FAFBFA", stroke=KULL if valgt else LINJE, sw=1.6 if valgt else 0.6)
    top = y + (17 if tekst else 3)
    bot = y + h - (17 if tekst else 3)
    px = x + 4
    pw = w - 8
    ky = (bot - top) / ymax
    sx = pw / 36
    d.line(px, bot, px + pw, bot, stroke=LINJE, sw=0.6)
    for i, r in enumerate(roller):
        o = sp["ordre"][r]
        pts = [(px + (j + 0.5) * sx, bot - min(v, ymax) * ky) for j, v in enumerate(o)]
        col = SKYGGE if ferdig else (ORDRE if i == len(roller) - 1 else SKYGGE)
        d.path(path_of(pts), stroke=col, sw=1 if i == len(roller) - 1 else 0.6, join="round")
    if not ferdig:
        gx = px + sp["uke"] * sx
        d.line(gx, top - 1, gx, bot + 1, stroke=NA, sw=1.6)
    if tekst:
        d.text(x + 5, y + 13, sp["spill"], size=fs, w=500 if not ferdig else 400, fill=KULL if not ferdig else KULL2)
        if sp.get("ki_seter"):
            d.text(x + w - 5, y + 13, f"KI {sp['ki_seter']}", size=fs, fill=KULL2, a="end")
        if venter:
            d.text(x + 5, y + h - 5, f"Venter {sp['ventet_timer']} t", size=fs, w=500)
        elif pauset:
            d.text(x + 5, y + h - 5, "Pause", size=fs, w=500)
        elif not ferdig:
            d.text(x + 5, y + h - 5, f"Uke {sp['uke']}", size=fs, fill=KULL2)
        else:
            d.text(x + 5, y + h - 5, tusen(sp["kjedekost"]), size=fs, fill=KULL2)


def knapp(d, x, y, w, h, s, primar=True, fs=15, enabled=True):
    if primar:
        d.rect(x, y, w, h, fill=KULL if enabled else SIDE)
        d.text(x + w / 2, y + h / 2 + fs * 0.35, s, size=fs, w=500, fill=KALK if enabled else KULL2, a="middle")
    else:
        d.rect(x, y, w, h, fill="none", stroke=KULL, sw=1)
        d.text(x + w / 2, y + h / 2 + fs * 0.35, s, size=fs, w=500, a="middle")


def pil(d, x, y, size=6, stroke=KULL2):
    """Tegnet pil til høyre for en rad som åpnes."""
    d.path(f"M{x} {y - size}L{x + size} {y}L{x} {y + size}", stroke=stroke, sw=1.1)
