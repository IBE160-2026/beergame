"""Konsept 03 Faseplanet, arbeidsnavn Fase. Tegner alle SVG-er fra ../_shared/fixture.json.

Kjør: uv run python build.py
Alle tall i grafer kommer fra fixture eller regnes ut av den.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAMES = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}
S17 = FX["spill17"]
S = S17["serier"]
BARE = FX["bare_sara_teller_paa_vei"]
ALLE = FX["alle_teller_paa_vei"]
REPLAY = FX["replay_sara"]
KL = FX["klasse"]
G = S["Grossist"]

# Palett
BG = "#E8EDF3"       # lys blågrå flate
SCREEN = "#F6F8FB"   # skjermark
GRIDF = "#E3E9F0"    # fine ruter
GRIDM = "#D3DCE6"    # hovedruter
AXIS = "#8494A8"
INK = "#14356F"      # blekkblå bane
FADE = "#B3C1D3"     # eldste uker
TEXT = "#16233B"
MUTED = "#4A5A72"
WARM = "#C9481A"     # nå
REF = "#0E7C76"      # simulert referanse
KEY = "#E4EAF1"
WHITE = "#FFFFFF"
ROLE_TONE = {"Detaljist": "#8DA2BE", "Grossist": "#5D7AA3", "Distributør": "#34598C", "Fabrikk": "#14356F"}

FONT_IMPORT = ("@import url('https://fonts.googleapis.com/css2?family=STIX+Two+Text:wght@400;500;600;700"
               "&amp;family=Karla:wght@400;500;600;700&amp;display=swap');")


def nf(v, d=0):
    s = f"{abs(v):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("−" if v < 0 else "") + s


def kr(v):
    return nf(v, 2) + " kr"


def fx(v):
    return nf(v, 1) + "×"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lerp_hex(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(pa, pb))


def wrap(s, px, size, f="k", w=400):
    per = (0.505 if f == "k" else 0.475) * size * (1.05 if w >= 600 else 1)
    out, cur = [], ""
    for word in s.split(" "):
        trial = (cur + " " + word).strip()
        if len(trial) * per > px and cur:
            out.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


class Svg:
    def __init__(self, name, w, h, title, desc, bg=BG):
        self.name, self.w, self.h = name, w, h
        self.title, self.desc = title, desc
        self.parts = []
        self.num = name.split("-")[0]
        self.n = 0
        self.rect(0, 0, w, h, fill=bg)

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1, rx=0, op=None, dash=None):
        a = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if rx:
            a += f' rx="{rx}"'
        if op is not None:
            a += f' fill-opacity="{op}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        self.add(a + "/>")

    def line(self, x1, y1, x2, y2, c=TEXT, w=1, dash=None, cap="butt"):
        a = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{w}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if cap != "butt":
            a += f' stroke-linecap="{cap}"'
        self.add(a + "/>")

    def path(self, d, c=TEXT, w=1.5, fill="none", dash=None, op=None, join="round"):
        a = f'<path d="{d}" fill="{fill}" stroke="{c}" stroke-width="{w}" stroke-linejoin="{join}" stroke-linecap="round"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if op is not None:
            a += f' fill-opacity="{op}"'
        self.add(a + "/>")

    def poly(self, pts, fill, op=None):
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        a = f'<polygon points="{d}" fill="{fill}"'
        if op is not None:
            a += f' fill-opacity="{op}"'
        self.add(a + "/>")

    def circ(self, x, y, r, fill=INK, stroke=None, sw=1):
        a = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        self.add(a + "/>")

    def t(self, x, y, s, size=14, f="k", w=400, c=TEXT, a="start", halo=None, rot=None):
        cls = "d03-s" if f == "s" else "d03-k"
        at = f'class="{cls}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{c}"'
        if w != 400:
            at += f' font-weight="{w}"'
        if a != "start":
            at += f' text-anchor="{a}"'
        if halo:
            at += f' paint-order="stroke" stroke="{halo}" stroke-width="3.5" stroke-linejoin="round"'
        if rot is not None:
            at += f' transform="rotate({rot} {x:.1f} {y:.1f})"'
        self.add(f"<text {at}>{esc(s)}</text>")

    def para(self, x, y, s, width, size=14, lh=None, f="k", w=400, c=TEXT, a="start"):
        lh = lh or size * 1.42
        for ln in wrap(s, width, size, f, w):
            self.t(x, y, ln, size, f, w, c, a)
            y += lh
        return y

    def g(self, tx=0, ty=0, scale=1):
        self.add(f'<g transform="translate({tx:.1f} {ty:.1f}) scale({scale})">')

    def end(self):
        self.add("</g>")

    def button(self, x, y, w, h, label, primary=True, size=16, rx=7):
        if primary:
            self.rect(x, y, w, h, fill=INK, rx=rx)
            self.t(x + w / 2, y + h / 2 + size * 0.34, label, size, w=600, c=WHITE, a="middle")
        else:
            self.rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=rx)
            self.t(x + w / 2, y + h / 2 + size * 0.34, label, size, w=600, c=INK, a="middle")

    def save(self):
        style = (f"<style>{FONT_IMPORT}"
                 ".d03-k{font-family:'Karla','Helvetica Neue',Arial,sans-serif;font-variant-numeric:lining-nums tabular-nums}"
                 ".d03-s{font-family:'STIX Two Text','Times New Roman',serif;font-variant-numeric:lining-nums tabular-nums}"
                 "</style>")
        body = "\n".join(self.parts)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
               f"font-family=\"'Karla','Helvetica Neue',Arial,sans-serif\">\n"
               f"<title>{esc(self.title)}</title>\n<desc>{esc(self.desc)}</desc>\n{style}\n"
               f'<g id="d03-{self.num}-rot">\n{body}\n</g>\n</svg>\n')
        (HERE / f"{self.name}.svg").write_text(svg, encoding="utf-8")


# ---------- Data ----------

def points(series, upto=None):
    n = upto or len(series["lager"])
    return [(series["lager"][i] - series["restordre"][i], series["paa_vei"][i]) for i in range(n)]


def m(week, role="Grossist", src=None):
    s = (src or S)[role]
    i = week - 1
    lager, rest, pv = s["lager"][i], s["restordre"][i], s["paa_vei"][i]
    prev_lager = s["lager"][i - 1] if i else 12
    return dict(uke=week, lager=lager, rest=rest, pv=pv, inc=s["innkommende_ordre"][i], lev=s["levering"][i],
                ordre=s["ordre"][i], kost=s["kost_sum"][i], net=lager - rest, pos=lager - rest + pv,
                sendt=prev_lager + s["levering"][i] - lager,
                neste=s["levering"][i + 1] if i + 1 < len(s["levering"]) else None)


def class_points(game, role="Fabrikk"):
    """På vei finnes ikke i klassedataene. Posisjon regnes ut: forrige Posisjon + egen ordre − innkommende ordre."""
    i = ROLES.index(role)
    net = game["netto_lager"][role]
    own = game["ordre"][role]
    down = game["ordre"][ROLES[i - 1]]
    pos = 24
    out = [(net[0], pos - net[0])]
    for t in range(1, len(net)):
        inc = down[t - 2] if t >= 2 else 4
        pos += own[t - 1] - inc
        out.append((net[t], pos - net[t]))
    return out


def shoelace(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


# Sjekk at utregningen stemmer med spill 17 før den brukes på de andre 59.
_g17 = next(g for g in KL["spill"] if g["spill"] == 17)
assert [y for _, y in class_points(_g17, "Fabrikk")] == S["Fabrikk"]["paa_vei"][:len(_g17["netto_lager"]["Fabrikk"])]
assert m(11)["pos"] == 3 and m(11)["pv"] == 16 and m(11)["sendt"] == 4 and m(11)["neste"] == 4
for _r in ROLES:
    _s = S[_r]
    for _t in range(35):
        _n0 = _s["lager"][_t] - _s["restordre"][_t]
        _n1 = _s["lager"][_t + 1] - _s["restordre"][_t + 1]
        assert _n1 == _n0 + _s["levering"][_t + 1] - _s["innkommende_ordre"][_t + 1]
        assert _s["paa_vei"][_t + 1] == _s["paa_vei"][_t] + _s["ordre"][_t] - _s["levering"][_t + 1]

FIN = [g for g in KL["spill"] if g["status"] == "ferdig"]
CW = sum(1 for g in FIN if shoelace(class_points(g, "Fabrikk")) < 0)
CLASS_PTS = {g["spill"]: class_points(g, "Fabrikk") for g in KL["spill"]}
CX = [x for v in CLASS_PTS.values() for x, _ in v]
CY = [y for v in CLASS_PTS.values() for _, y in v]
CLASS_XR = (math.floor(min(CX) / 10) * 10, math.ceil(max(CX) / 10) * 10)
CLASS_YR = (min(0, math.floor(min(CY) / 10) * 10), math.ceil(max(CY) / 10) * 10)


# ---------- Faseplan ----------

class Plane:
    def __init__(self, g, x, y, k, xr, yr):
        self.g, self.x, self.y, self.k, self.xr, self.yr = g, x, y, k, xr, yr
        self.w = (xr[1] - xr[0]) * k
        self.h = (yr[1] - yr[0]) * k

    def X(self, v):
        return self.x + (v - self.xr[0]) * self.k

    def Y(self, v):
        return self.y + (self.yr[1] - v) * self.k

    def grid(self, fine=5, major=10, ticks=20, tsize=13, labels=True, side_labels=True, bg=None):
        g = self.g
        if bg:
            g.rect(self.x, self.y, self.w, self.h, fill=bg)
        def steps(lo, hi, s):
            v = math.ceil(lo / s) * s
            while v <= hi:
                yield v
                v += s
        if fine:
            for v in steps(*self.xr, fine):
                if v % major:
                    g.line(self.X(v), self.y, self.X(v), self.y + self.h, GRIDF, 0.7)
            for v in steps(*self.yr, fine):
                if v % major:
                    g.line(self.x, self.Y(v), self.x + self.w, self.Y(v), GRIDF, 0.7)
        for v in steps(*self.xr, major):
            g.line(self.X(v), self.y, self.X(v), self.y + self.h, GRIDM, 0.8)
        for v in steps(*self.yr, major):
            g.line(self.x, self.Y(v), self.x + self.w, self.Y(v), GRIDM, 0.8)
        g.line(self.X(0), self.y, self.X(0), self.y + self.h, AXIS, 1.1)
        g.line(self.x, self.Y(self.yr[0]), self.x + self.w, self.Y(self.yr[0]), AXIS, 1.1)
        if labels:
            for v in steps(*self.xr, ticks):
                g.t(self.X(v), self.y + self.h + tsize + 3, nf(v), tsize, "s", c=MUTED, a="middle")
            for v in steps(*self.yr, ticks):
                if v > self.yr[0]:
                    g.t(self.x + 3, self.Y(v) - 3, nf(v), tsize, "s", c=MUTED)
        if side_labels:
            yy = self.y + self.h - 6
            g.t(self.x + 4, yy, "Restordre", tsize, c=MUTED, halo=SCREEN)
            g.t(self.x + self.w - 4, yy, "Lager", tsize, c=MUTED, a="end", halo=SCREEN)
            g.t(self.x + 3, self.y + tsize + 1, "På vei", tsize, c=MUTED, w=600, halo=SCREEN)

    def diag(self, c, color=AXIS, w=1.0, dash=None, label=None, at=0.5, size=13, lc=None, weight=500, off=-5):
        x1 = max(self.xr[0], c - self.yr[1])
        x2 = min(self.xr[1], c - self.yr[0])
        if x1 >= x2:
            return
        self.g.line(self.X(x1), self.Y(c - x1), self.X(x2), self.Y(c - x2), color, w, dash)
        if label:
            lx = x1 + (x2 - x1) * at
            px, py = self.X(lx), self.Y(c - lx)
            # tekst langs linjen, litt over
            nx, ny = off * -math.sin(math.radians(45)), off * math.cos(math.radians(45))
            self.g.t(px + nx, py + ny, label, size, w=weight, c=lc or TEXT, a="middle", rot=45, halo=SCREEN)

    def bane(self, pts, fade=None, wmin=1.0, wmax=2.5, dots=True, r=1.8, color=None, tone_from=FADE, tone_to=INK,
             dashed=None, dash="4 3"):
        n = len(pts)
        def tone(i):
            age = n - 1 - i
            t = max(0.0, 1 - age / fade) if fade else (i / max(n - 1, 1))
            return t ** 1.15
        for i in range(n - 1):
            a, b = pts[i], pts[i + 1]
            if a == b:
                continue
            t = tone(i + 1)
            col = color or lerp_hex(tone_from, tone_to, t)
            self.g.line(self.X(a[0]), self.Y(a[1]), self.X(b[0]), self.Y(b[1]), col, round(wmin + (wmax - wmin) * t, 2),
                        dash if dashed and (i + 1) in dashed else None, "round")
        if dots:
            for i, p in enumerate(pts):
                t = tone(i)
                self.g.circ(self.X(p[0]), self.Y(p[1]), r, fill=color or lerp_hex(tone_from, tone_to, t))

    def now(self, p, r=5.5, label=None, dx=10, dy=-8, size=14, ring=SCREEN, a="start"):
        self.g.circ(self.X(p[0]), self.Y(p[1]), r, fill=WARM, stroke=ring, sw=2)
        if label:
            self.g.t(self.X(p[0]) + dx, self.Y(p[1]) + dy, label, size, "k", 600, TEXT, a, halo=SCREEN)

    def mark(self, p, label, dx=8, dy=-6, size=13, a="start", c=TEXT, r=2.6, fill=None, w=500):
        if r:
            self.g.circ(self.X(p[0]), self.Y(p[1]), r, fill=fill or INK)
        self.g.t(self.X(p[0]) + dx, self.Y(p[1]) + dy, label, size, w=w, c=c, a=a, halo=SCREEN)


def arrow(g, x1, y1, x2, y2, c=WARM, w=2.0, head=7):
    """Tegnet pil, ikke tegn."""
    g.line(x1, y1, x2, y2, c, w, cap="round")
    ang = math.atan2(y2 - y1, x2 - x1)
    for s in (-1, 1):
        a = ang + math.pi + s * 0.45
        g.line(x2, y2, x2 + head * math.cos(a), y2 + head * math.sin(a), c, w, cap="round")


def moves(p: Plane, week, labels=True, size=13, src=None, c_up=WARM, role="Grossist"):
    """Tre bevegelser fra Uke week til neste: Ordre opp, Levering langs diagonalen, Innkommende ordre mot venstre."""
    s = (src or S)[role]
    i = week - 1
    a = (s["lager"][i] - s["restordre"][i], s["paa_vei"][i])
    o, l, inc = s["ordre"][i], s["levering"][i + 1], s["innkommende_ordre"][i + 1]
    b = (a[0], a[1] + o)
    c = (b[0] + l, b[1] - l)
    d = (c[0] - inc, c[1])
    assert d == (s["lager"][i + 1] - s["restordre"][i + 1], s["paa_vei"][i + 1])
    g = p.g
    if o:
        arrow(g, p.X(a[0]), p.Y(a[1]), p.X(b[0]), p.Y(b[1]), c_up, 2)
    if l:
        arrow(g, p.X(b[0]), p.Y(b[1]), p.X(c[0]), p.Y(c[1]), INK, 2)
    if inc:
        arrow(g, p.X(c[0]), p.Y(c[1]), p.X(d[0]), p.Y(d[1]), MUTED, 2)
    return dict(a=a, b=b, c=c, d=d, o=o, l=l, inc=inc)


def strip(g, x, y, w, h, series, upto, pxw=None, yr=None, tsize=13, label_w=74, labels=True, now=True, net_label="Netto"):
    """Smal tidsserie med samme tall som planet. Høyre kant er nå."""
    pts_ = points(series, upto)
    n = len(pts_)
    plot_w = w - (label_w if labels else 0)
    pxw = pxw or plot_w / max(n - 1, 1)
    def X(i):
        return x + plot_w - (n - 1 - i) * pxw
    vals = [v for p in pts_ for v in p]
    yr = yr or (min(0, math.floor(min(vals) / 10) * 10), max(10, math.ceil(max(vals) / 10) * 10))
    def Y(v):
        return y + h - (v - yr[0]) / (yr[1] - yr[0]) * h
    g.line(x, Y(0), x + plot_w, Y(0), AXIS, 1)
    for idx, width in ((1, 1.1), (0, 2.2)):
        for i in range(n - 1):
            t = (max(0.0, 1 - (n - 2 - i) / 16)) ** 1.15
            col = lerp_hex(FADE, INK if idx == 0 else "#44608F", t)
            g.line(X(i), Y(pts_[i][idx]), X(i + 1), Y(pts_[i + 1][idx]), col, round(width * (0.6 + 0.4 * t), 2), cap="round")
    if now:
        g.line(X(n - 1), y - 2, X(n - 1), y + h + 2, GRIDM, 1)
        g.circ(X(n - 1), Y(pts_[-1][0]), 3.2, fill=WARM)
    if labels:
        a, b = Y(pts_[-1][0]) + 4, Y(pts_[-1][1]) + 4
        if abs(a - b) < tsize + 1:
            a, b = (a + (tsize + 1) / 2, b - (tsize + 1) / 2) if a >= b else (a - (tsize + 1) / 2, b + (tsize + 1) / 2)
        g.t(x + plot_w + 6, a, f"{net_label} {nf(pts_[-1][0])}", tsize, w=600)
        g.t(x + plot_w + 6, b, f"På vei {nf(pts_[-1][1])}", tsize, c=MUTED)
    return X, Y


def phone(g, x, y, scale=1.0):
    g.g(x, y, scale)
    g.rect(0, 0, 390, 844, fill=SCREEN, stroke="#9AA9BC", sw=1.5, rx=30)


R11 = ((-30, 20), (0, 50))


def header(g, role, navn, uke, kost, y=44):
    g.t(20, y, f"Uke {uke}", 30, "s", 600)
    g.t(20, y + 21, f"{role}, {navn}", 14, c=MUTED)
    g.t(370, y - 14, "Totalkostnad", 13, c=MUTED, a="end")
    g.t(370, y + 8, kr(kost), 21, "s", 500, a="end")


def plane_block(g, week=11, typed=None, xr=R11[0], yr=R11[1], y=84, show_moves=False, confirmed=False):
    mm = m(week)
    k = 350 / (xr[1] - xr[0])
    p = Plane(g, 20, y, k, xr, yr)
    p.grid(fine=5, major=10, ticks=20)
    pts_ = points(G, week)
    p.diag(mm["pos"], AXIS, 1.1, None, f"Posisjon {nf(mm['pos'])}", at=0.86)
    if typed is not None:
        col = INK if confirmed else WARM
        p.diag(mm["pos"] + typed, col, 1.3, "5 4", f"Posisjon {nf(mm['pos'] + typed)}", at=0.72, weight=700)
    p.bane(pts_, fade=14, wmax=2.6)
    if week > 1:
        p.mark(pts_[0], "Uke 1", dx=0, dy=17, r=0, a="middle", c=MUTED)
    if typed is not None:
        top = (mm["net"], mm["pv"] + typed)
        arrow(g, p.X(mm["net"]), p.Y(mm["pv"]), p.X(top[0]), p.Y(top[1]), INK if confirmed else WARM, 2.6, 9)
        g.t(p.X(top[0]) + 9, p.Y((mm["pv"] + top[1]) / 2), f"+{typed}", 18, "s", 600, halo=SCREEN)
    if show_moves:
        pm = moves(p, week - 1)
    p.now(pts_[-1], r=6, label=f"Uke {week}", dx=-10, dy=19, a="end")
    return p


def status_lines(g, y=792, week=11, lines=None):
    lines = lines or ["Ida og Mikkel har bestilt. Jonas venter, 3 min.", "Ordren kan ikke endres etter at du har bestilt."]
    for i, s in enumerate(lines):
        g.t(20, y + i * 19, s, 13.5, c=MUTED)


def pad(g, y=680, active=True):
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
    kw, kh, gap = 52.3, 42, 7.2
    for i, d in enumerate(keys[:6]):
        xx = 20 + i * (kw + gap)
        g.rect(xx, y, kw, kh, fill=KEY, rx=6)
        g.t(xx + kw / 2, y + 28, d, 20, "s", 500, a="middle")
    for i, d in enumerate(keys[6:]):
        xx = 20 + i * (kw + gap)
        g.rect(xx, y + kh + 7, kw, kh, fill=KEY, rx=6)
        g.t(xx + kw / 2, y + kh + 35, d, 20, "s", 500, a="middle")
    # slett-tast, tegnet ikon
    xx = 20 + 4 * (kw + gap)
    wd = kw * 2 + gap
    yy = y + kh + 7
    g.rect(xx, yy, wd, kh, fill=KEY, rx=6)
    cx, cy = xx + wd / 2, yy + kh / 2
    g.path(f"M{cx-13},{cy} L{cx-6},{cy-8} L{cx+13},{cy-8} L{cx+13},{cy+8} L{cx-6},{cy+8} Z", TEXT, 1.4)
    g.line(cx - 1, cy - 3.5, cx + 6, cy + 3.5, TEXT, 1.4)
    g.line(cx + 6, cy - 3.5, cx - 1, cy + 3.5, TEXT, 1.4)


def regnestykke(g, week=11, typed=None, y=556, detail_link=True):
    mm = m(week)
    g.t(20, y, f"Lager {mm['lager']} − Restordre {mm['rest']} + På vei {mm['pv']} = ", 14.5)
    g.t(20 + 277, y, f"Posisjon {mm['pos']}", 14.5, w=700)
    if typed is not None:
        g.t(20, y + 25, f"Posisjon {mm['pos']} + ordre {typed} = ", 14.5)
        g.t(20 + 164, y + 25, f"Posisjon {mm['pos'] + typed}", 14.5, w=700)
    if detail_link:
        g.t(370, y + 25, "Alle tall", 14.5, w=600, c=INK, a="end")
        g.line(370 - 52, y + 28.5, 370, y + 28.5, INK, 1)


def order_input(g, typed=None, y=600):
    g.rect(20, y, 96, 60, fill=WHITE, stroke=INK if typed is not None else AXIS, sw=1.4, rx=7)
    if typed is not None:
        g.t(68, y + 42, str(typed), 36, "s", 600, a="middle")
    else:
        g.line(68, y + 16, 68, y + 44, INK, 1.6)
    if typed is not None:
        g.button(126, y, 244, 60, f"Bestill {typed}", True, 19)
    else:
        g.rect(126, y, 244, 60, fill=KEY, rx=7)
        g.t(248, y + 37, "Tast Ordre", 17, w=600, c=MUTED, a="middle")


def game_screen(g, week=11, typed=24):
    mm = m(week)
    header(g, "Grossist", "Sara", week, mm["kost"])
    p = plane_block(g, week, typed)
    strip(g, 20, 470, 350, 56, G, week, label_w=84, yr=(-20, 30))
    regnestykke(g, week, typed)
    order_input(g, typed)
    pad(g)
    status_lines(g)
    return p


# ---------- 10 pedagogikk ----------

def page_10():
    g = Svg("10-pedagogikk", 2000, 1400, "Fase: grafgrammatikk for Sara ved Uke 5, 11, 18 og 29",
            "Faseplan med netto lager vannrett og På vei loddrett, samme skala, med smal tidsserie under. Viser fire tidspunkter, tre bevegelser, gradvis innføring, Klassespill mot Replay og simulert referanse.", bg=SCREEN)
    g.t(55, 66, "Samme plan fire ganger: hvert punkt er én Uke, og tiden er en bane", 38, "s", 600)
    g.para(55, 98, "Netto lager vannrett, På vei loddrett, samme skala på begge akser. Alt langs en diagonal har samme Posisjon. Nyeste uke er mørkest.", 1700, 17, c=MUTED)
    g.t(1945, 66, "Demodata, Sara, Grossist, spill 17", 15, c=MUTED, a="end")

    k = 5.0
    xr, yr = (-45, 35), (0, 95)
    cols = [55, 530, 1005, 1480]
    weeks = [5, 11, 18, 29]
    notes = {
        5: (["P1", "P2"], "Banen er ett punkt. Lager 12 og På vei 12 gir Posisjon 24, og det som kommer inn går ut igjen.",
            "Neste ordre flytter punktet rett opp. Ingenting annet du gjør flytter det."),
        11: (["P3"], f"Netto er {nf(m(11)['net'])}, men {m(11)['pv']} er på vei, så Posisjon er {m(11)['pos']}. Med ordre 24 flyttes du til diagonalen for {m(11)['pos'] + 24}.",
             "Regn ut Posisjon før du svarer på Restordre. Restordre alene er bare halve bildet."),
        18: (["P2", "P7"], f"Restordre {m(18)['rest']} ser akutt ut, men {m(18)['pv']} er på vei og Posisjon er {m(18)['pos']}. Av 24 bestilt i Uke 11 kom {G['levering'][14]} fram i Uke 15.",
             "Ordrer du gir nå kommer etter at dagens mangel er borte. Hver stor ordre løfter en høy Posisjon."),
        29: (["P5", "P7"], f"Fra Uke 22 til 26 fulgte banen diagonalen ned: Levering flytter varer fra På vei til Lager uten å endre Posisjon. Nå er Lager {m(29)['lager']}, kostet av ordre gitt lenge før.",
             f"Svært lave ordre nå kan bli neste overreaksjon. Posisjon er {m(29)['pos']} og På vei bare {m(29)['pv']}."),
    }
    pnames = {"P1": "Lager er en opphopning", "P2": "Forsinkelse", "P3": "Det som er på vei blir glemt",
              "P5": "Forsterkning og faseforskyvning", "P7": "Overreaksjon forsterker også"}
    for x, w_ in zip(cols, weeks):
        mm = m(w_)
        g.t(x, 146, f"Uke {w_}", 28, "s", 600)
        g.t(x + 110, 146, f"Posisjon {nf(mm['pos'])} = {nf(mm['net'])} + {mm['pv']}", 16, c=MUTED)
        p = Plane(g, x, 160, k, xr, yr)
        p.grid(fine=5, major=10, ticks=20)
        pts_ = points(G, w_)
        p.diag(mm["pos"], AXIS, 1.1, None, f"Posisjon {nf(mm['pos'])}", at=0.42 if w_ != 5 else 0.72)
        if w_ == 11:
            p.diag(27, WARM, 1.2, "5 4", "Posisjon 27", at=0.34, weight=700)
            arrow(g, p.X(mm["net"]), p.Y(mm["pv"]), p.X(mm["net"]), p.Y(mm["pv"] + 24), WARM, 2.4, 8)
            g.t(p.X(mm["net"]) + 8, p.Y(mm["pv"] + 13), "+24", 16, "s", 600, halo=SCREEN)
        p.bane(pts_, fade=16, wmax=2.8)
        if w_ == 18:
            p.mark(points(G)[10], "Uke 11", dx=7, dy=14, r=0, c=MUTED)
        if w_ == 29:
            p.mark(points(G)[21], "Uke 22", dx=30, dy=-3, r=0, c=MUTED)
            p.mark(points(G)[10], "Uke 11", dx=7, dy=14, r=0, c=MUTED)
        p.now(pts_[-1], r=6, label=f"Uke {w_}", dx=11, dy=-9 if w_ != 18 else -7)
        # tidsserie, fast piksler per uke, høyre kant er nå
        strip(g, x, 662, 400, 58, G, w_, pxw=11, yr=(-45, 95), label_w=84, labels=True)
        tags, what, nxt = notes[w_]
        yy = 744
        g.t(x, yy, " · ".join(f"{t} {pnames[t]}" for t in tags), 13.5, w=700, c=INK)
        yy = g.para(x, yy + 21, what, 415, 14.5, 20)
        g.para(x, yy + 3, "Til neste ordre: " + nxt, 415, 14.5, 20, c=MUTED)

    # Rad B
    top = 950
    g.line(55, top - 12, 1945, top - 12, GRIDM, 1)
    # B1 tre bevegelser
    x = 55
    g.t(x, top + 20, "Tre bevegelser, ingen flere", 22, "s", 600)
    g.t(x, top + 41, "P1 Lager er en opphopning", 13.5, w=700, c=INK)
    m12 = m(12)
    z = Plane(g, x, top + 54, 6.3, (-46, 20), (12, 44))
    z.grid(fine=5, major=10, ticks=20, labels=False, side_labels=False)
    z.diag(m(11)["pos"] + 24, AXIS, 1, "4 4")
    mv = moves(z, 11)
    z.now(mv["a"], r=5, label="Uke 11", dx=-9, dy=5, a="end", size=13)
    g.circ(z.X(mv["d"][0]), z.Y(mv["d"][1]), 4, fill=INK)
    g.t(z.X(mv["a"][0]) + 8, z.Y(26), f"Ordre +{mv['o']}: opp", 13.5, w=600, halo=SCREEN)
    g.t(z.X(mv["c"][0]) + 9, z.Y(mv["c"][1]) + 2, f"Levering {mv['l']}: langs", 13.5, w=600, halo=SCREEN)
    g.t(z.X(mv["c"][0]) + 9, z.Y(mv["c"][1]) + 19, "diagonalen", 13.5, w=600, halo=SCREEN)
    g.t(z.X(mv["d"][0]) - 8, z.Y(mv["d"][1]) - 7, "Uke 12", 13.5, w=600, a="end", halo=SCREEN)
    g.t(z.X(mv["d"][0]) - 8, z.Y(mv["d"][1]) + 12, f"Innkommende ordre {mv['inc']}:", 13.5, w=600, a="end", halo=SCREEN)
    g.t(z.X(mv["d"][0]) - 8, z.Y(mv["d"][1]) + 29, "mot venstre", 13.5, w=600, a="end", halo=SCREEN)
    yy = top + 54 + z.h + 22
    yy = g.para(x, yy, f"Regn selv: {nf(m(11)['net'])} + {mv['l']} − {mv['inc']} = {nf(m12['net'])} netto, og {m(11)['pv']} + {mv['o']} − {mv['l']} = {m12['pv']} på vei.", 420, 14.5, 20)
    yy = g.para(x, yy + 4, "Levering endrer aldri Posisjon. Bare to ting gjør det: din Ordre og Innkommende ordre. Du bestemmer bare hvor langt opp.", 420, 14.5, 20, c=MUTED)
    g.para(x, yy + 4, f"P4: Innkommende ordre er det du ser, ikke kundene. P6: Fabrikk går med klokka i {CW} av {len(FIN)} ferdige spill. P8: til venstre for null koster en enhet dobbelt.", 420, 13.5, 18, w=600, c=INK)

    # B2 gradvis
    x = 530
    g.t(x, top + 20, "Planet bygges i de Veiledede ukene", 22, "s", 600)
    g.t(x, top + 41, "Risikoen er at et faseplan er nytt. Derfor kommer det i biter.", 13.5, c=MUTED)
    cell = 205
    steps_ = [
        ("Uke 1", "Bare tallinja: Lager til høyre for null, Restordre til venstre.", "net"),
        ("Uke 2", "På vei legges til som høyde. Punktet har to tall.", "plane"),
        ("Uke 3", "Diagonalen: alle punkter på den har samme Posisjon.", "diag"),
        ("Uke 4", "Ordren er pil rett opp. Fra Uke 5 er alt åpent.", "order"),
    ]
    for i, (w_, txt, kind) in enumerate(steps_):
        cx = x + (i % 2) * (cell + 15)
        cy = top + 54 + (i // 2) * 202
        g.t(cx, cy + 12, w_, 15, "s", 600)
        q = Plane(g, cx, cy + 20, 3.3, (-15, 36) if False else (-20, 40), (0, 30) if kind != "net" else (0, 8))
        if kind == "net":
            g.line(q.x, q.y + 12, q.x + q.w, q.y + 12, AXIS, 1.1)
            g.line(q.X(0), q.y + 2, q.X(0), q.y + 22, AXIS, 1.1)
            g.t(q.X(0) - 6, q.y + 36, "Restordre", 13, c=MUTED, a="end")
            g.t(q.X(0) + 6, q.y + 36, "Lager", 13, c=MUTED)
            g.circ(q.X(12), q.y + 12, 5.5, fill=WARM, stroke=SCREEN, sw=2)
            g.t(q.X(12), q.y + 2, "12", 14, "s", 600, a="middle")
            ty = q.y + 60
        else:
            q.grid(fine=10, major=10, labels=False, side_labels=False)
            g.t(q.x + 3, q.y + 13, "På vei", 13, c=MUTED, w=600, halo=SCREEN)
            if kind in ("diag", "order"):
                q.diag(24, AXIS, 1.1, None, "Posisjon 24" if kind == "diag" else None, at=0.5)
            if kind == "order":
                q.diag(28, WARM, 1.1, "4 3")
                arrow(g, q.X(12), q.Y(12), q.X(12), q.Y(16), WARM, 2.2, 6)
                g.t(q.X(12) + 7, q.Y(14) + 4, "+4", 14, "s", 600, halo=SCREEN)
            q.now((12, 12), r=5)
            ty = q.y + q.h + 16
        g.para(cx, ty, txt, cell - 4, 13, 17, c=TEXT)

    # B3 Hjelpegrad
    x = 1005
    g.t(x, top + 20, "Hjelpegrad: to nivåer", 22, "s", 600)
    g.t(x, top + 41, "Klassespillet lar svingningen skje. Replay gir verktøyene.", 13.5, c=MUTED)
    k2 = 2.68
    xr2, yr2 = (-45, 35), (0, 95)
    a = Plane(g, x, top + 54, k2, xr2, yr2)
    a.grid(fine=None, major=10, ticks=20, tsize=13, side_labels=False, labels=False)
    a.diag(m(11)["pos"], AXIS, 1.1, None, f"Posisjon {m(11)['pos']}", at=0.34)
    a.bane(points(G, 11), fade=14)
    a.now(points(G, 11)[-1], r=5)
    g.t(x, top + 54 + a.h + 18, "Klassespill", 15, "s", 600)
    g.para(x, top + 54 + a.h + 37, "Én diagonal, nå-punktet, banen. Ingen rutenett av Posisjoner, ingen fremtid.", 205, 13, 17)
    x2 = x + 228
    rs = REPLAY["serier"]["Grossist"]
    rw = 14
    rp = points(rs, rw)
    pos_r = rp[-1][0] + rp[-1][1]
    b = Plane(g, x2, top + 54, k2, xr2, yr2)
    b.grid(fine=None, major=10, ticks=20, side_labels=False, labels=False)
    for c in range(-20, 95, 10):
        b.diag(c, GRIDM, 0.9)
    b.diag(pos_r, AXIS, 1.2, None, f"Posisjon {pos_r}", at=0.2)
    b.bane(points(G), fade=None, color="#CDD8E5", dots=False, wmin=1.2, wmax=1.2)
    b.bane(rp, fade=14)
    nxt = rs["levering"][rw]
    b.mark((rp[-1][0] + nxt, rp[-1][1] - nxt), f"Levering {nxt}", dx=6, dy=-6, r=3, c=TEXT)
    b.now(rp[-1], r=5)
    g.t(x2, top + 54 + b.h + 18, "Replay", 15, "s", 600)
    g.para(x2, top + 54 + b.h + 37, "Alle Posisjonene, kjent neste Levering (ikke garantert), Klassespillet som grå bane. Ikke like for like.", 215, 13, 17)

    # B4 referanse
    x = 1480
    g.t(x, top + 20, "Etter Debriefen: mot simulert", 22, "s", 600)
    g.t(x, top + 41, "P3 og P7. Simulert, viser sammenhengen, ikke en fasit.", 13.5, c=MUTED)
    k3 = 3.2
    r = Plane(g, x, top + 54, k3, (-45, 35), (0, 95))
    r.grid(fine=None, major=10, ticks=20, side_labels=False, labels=False)
    r.bane(points(G), wmax=2.2, r=1.2)
    r.bane(points(BARE["serier"]["Grossist"]), color=REF, wmin=1.5, wmax=1.5, dots=False)
    pk = points(G)[21]
    r.mark(pk, "Spill 17", dx=9, dy=2, r=0, w=600)
    pr = points(BARE["serier"]["Grossist"])[20]
    r.mark((-17, 37), "Simulert", dx=0, dy=0, r=0, c=REF, w=700)
    xx = x + r.w + 16
    yy = top + 70
    for label, a_, b_ in (("Grossist-kostnad", nf(S17["kost_per_rolle"]["Grossist"], 2), nf(BARE["kost_per_rolle"]["Grossist"], 2)),
                          ("Forsterkning", fx(S17["forsterkning"]["Grossist"]), fx(BARE["forsterkning"]["Grossist"])),
                          ("Kjeden", nf(S17["kjedekost"], 2), nf(BARE["kjedekost"], 2))):
        g.t(xx, yy, label, 13, c=MUTED)
        g.t(xx, yy + 21, a_, 18, "s", 600)
        g.t(xx, yy + 41, b_, 15, "s", 500, c=REF)
        yy += 66
    g.para(x, top + 54 + r.h + 20, "Samme kjede, men bare Grossist teller alt på vei fra Uke 5. Nyansen: å telle er ikke nok. En regel som jaget siste ordre for hardt ga Fabrikk 12× i simuleringen.", 465, 13.5, 18.5)
    g.save()


# ---------- 05 spill ----------

def page_05():
    g = Svg("05-spill", 1600, 1000, "Fase: Saras skjerm i Uke 11 med 24 tastet inn",
            "Telefon med faseplan, åpnet panel med alle tall, og laptop. Posisjon 3 blir 27 med ordre 24.")
    g.t(40, 50, "Uke 11: du bestemmer hvor langt opp", 32, "s", 600)
    g.t(1560, 50, "Demodata", 15, c=MUTED, a="end")
    phone(g, 40, 78, 1.0)
    game_screen(g)
    g.end()

    # Åpnet panel
    px, py = 452, 78
    g.rect(px, py, 372, 844, fill=SCREEN, stroke=GRIDM, sw=1, rx=12)
    g.t(px + 20, py + 38, "Alle tall", 24, "s", 600)
    g.t(px + 352, py + 36, "Lukk", 15, w=600, c=INK, a="end")
    g.t(px + 20, py + 60, "Ett trykk fra planet. Uke 11, Grossist.", 13.5, c=MUTED)
    mm = m(11)
    rows = [("Lager", mm["lager"]), ("Restordre", mm["rest"]), ("Innkommende ordre", mm["inc"]), ("Levering", mm["lev"]),
            ("Sendt", mm["sendt"]), ("På vei", mm["pv"]), ("Neste levering, ikke garantert", mm["neste"]), ("Posisjon", mm["pos"]), ("Totalkostnad", kr(mm["kost"]))]
    yy = py + 88
    for lab, v in rows:
        g.t(px + 20, yy, lab, 14.5)
        g.t(px + 352, yy, str(v), 16, "s", 500, a="end")
        g.line(px + 20, yy + 7, px + 352, yy + 7, GRIDM, 0.8)
        yy += 27
    # Hvorfor punktet flyttet seg
    yy += 12
    g.t(px + 20, yy, "Slik kom du hit fra Uke 10", 16, "s", 600)
    z = Plane(g, px + 20, yy + 10, 6.0, (-24, 8), (6, 24))
    z.grid(fine=5, major=10, labels=False, side_labels=False)
    mv = moves(z, 10)
    g.circ(z.X(mv["a"][0]), z.Y(mv["a"][1]), 3.5, fill=INK)
    g.t(z.X(mv["a"][0]) + 8, z.Y(mv["a"][1]) + 15, "Uke 10", 13, c=MUTED, halo=SCREEN)
    z.now(mv["d"], r=5)
    g.t(z.X(mv["d"][0]) - 8, z.Y(mv["d"][1]) + 16, "Uke 11", 13, w=600, a="end", halo=SCREEN)
    tx = z.x + z.w + 12
    g.t(tx, yy + 30, f"Opp {mv['o']}: Ordre", 13.5)
    g.t(tx, yy + 52, f"Skrått {mv['l']}: Levering", 13.5)
    g.t(tx, yy + 74, f"Venstre {mv['inc']}:", 13.5)
    g.t(tx, yy + 92, "Innkommende ordre", 13.5)
    yy = z.y + z.h + 28
    # Inn og ut
    g.t(px + 20, yy, "Inn og ut", 16, "s", 600)
    g.t(px + 352, yy, "Avstanden er endringen i netto", 13, c=MUTED, a="end")
    n = 11
    bx, bw, bh = px + 20, 270, 64
    by = yy + 12
    X = lambda i: bx + i * bw / (n - 1)
    Y = lambda v: by + bh - v / 12 * bh
    inn, ut = G["levering"][:n], G["innkommende_ordre"][:n]
    for i in range(n - 1):
        g.poly([(X(i), Y(inn[i])), (X(i + 1), Y(inn[i + 1])), (X(i + 1), Y(ut[i + 1])), (X(i), Y(ut[i]))], INK, 0.13)
    g.line(bx, by + bh, bx + bw, by + bh, AXIS, 1)
    g.path("M" + " L".join(f"{X(i):.1f},{Y(inn[i]):.1f}" for i in range(n)), INK, 2)
    g.path("M" + " L".join(f"{X(i):.1f},{Y(ut[i]):.1f}" for i in range(n)), MUTED, 1.2)
    g.t(bx + bw + 6, Y(inn[-1]) + 4, f"Inn {inn[-1]}", 13, w=600)
    g.t(bx + bw + 6, Y(ut[-1]) + 4, f"Ut {ut[-1]}", 13, c=MUTED)
    yy = by + bh + 28
    # Ordrehistorikk
    g.t(px + 20, yy, "Dine ordre", 16, "s", 600)
    hx = px + 20
    hist = G["ordre"][:10]
    hy = yy + 64
    for i, o in enumerate(hist):
        h_ = o * 2.0
        g.rect(hx + i * 24, hy - h_, 10, h_, fill=INK, rx=1.5)
        g.t(hx + i * 24 + 5, hy + 15, str(o), 13, "s", a="middle")
    h_ = 24 * 2.0
    g.rect(hx + 10 * 24, hy - h_, 10, h_, fill=WARM, rx=1.5)
    g.t(hx + 10 * 24 + 5, hy + 15, "24", 13, "s", 700, a="middle")
    g.t(px + 352, hy + 15, "Uke 1 til nå", 13, c=MUTED, a="end")
    g.t(px + 20, hy + 52, "Hele banen som tabell", 14.5, w=600, c=INK)
    g.line(px + 20, hy + 56, px + 166, hy + 56, INK, 1)

    # Laptop
    lx, ly, lw, lh = 860, 78, 700, 570
    g.rect(lx, ly, lw, lh, fill=SCREEN, stroke="#9AA9BC", sw=1.5, rx=10)
    g.line(lx - 24, ly + lh + 10, lx + lw + 24, ly + lh + 10, "#9AA9BC", 2, cap="round")
    g.t(lx + 26, ly + 44, "Uke 11", 30, "s", 600)
    g.t(lx + 130, ly + 43, "Grossist, Sara, spill 17", 15, c=MUTED)
    g.t(lx + lw - 26, ly + 30, "Totalkostnad", 13, c=MUTED, a="end")
    g.t(lx + lw - 26, ly + 52, kr(mm["kost"]), 21, "s", 500, a="end")
    k = 7.6
    p = Plane(g, lx + 26, ly + 68, k, R11[0], R11[1])
    p.grid()
    pts_ = points(G, 11)
    p.diag(mm["pos"], AXIS, 1.1, None, f"Posisjon {mm['pos']}", at=0.86)
    p.diag(27, WARM, 1.3, "5 4", "Posisjon 27", at=0.72, weight=700)
    p.bane(pts_, fade=14, wmax=2.6)
    arrow(g, p.X(mm["net"]), p.Y(mm["pv"]), p.X(mm["net"]), p.Y(mm["pv"] + 24), WARM, 2.6, 9)
    g.t(p.X(mm["net"]) + 9, p.Y(mm["pv"] + 12), "+24", 18, "s", 600, halo=SCREEN)
    p.mark(pts_[0], "Uke 1", dx=0, dy=17, r=0, a="middle", c=MUTED)
    p.now(pts_[-1], r=6, label="Uke 11", dx=-10, dy=19, a="end")
    strip(g, lx + 26, ly + 68 + p.h + 26, 380, 42, G, 11, label_w=90, yr=(-20, 30))
    # Høyre kolonne
    cx = lx + 440
    cw = lw - 440 - 26
    yy = ly + 92
    for lab, v in rows:
        lab2 = "Neste levering" if lab.startswith("Neste") else lab
        g.t(cx, yy, lab2, 14)
        g.t(cx + cw, yy, str(v), 15.5, "s", 500, a="end")
        g.line(cx, yy + 6, cx + cw, yy + 6, GRIDM, 0.8)
        yy += 25
    yy += 14
    g.t(cx, yy, f"{mm['net']:+d} + {mm['pv']} = Posisjon {mm['pos']}".replace("-", "−"), 14.5)
    g.t(cx, yy + 22, "Posisjon 3 + 24 = 27", 14.5, w=700)
    yy += 40
    g.rect(cx, yy, 72, 52, fill=WHITE, stroke=INK, sw=1.4, rx=6)
    g.t(cx + 36, yy + 37, "24", 32, "s", 600, a="middle")
    g.button(cx + 82, yy, cw - 82, 52, "Bestill 24", True, 17)
    yy += 74
    for s in ["Ida og Mikkel har bestilt.", "Jonas venter, 3 min."]:
        g.t(cx, yy, s, 14, c=MUTED)
        yy += 19
    # Forklaring under laptop
    y0 = ly + lh + 44
    g.t(lx - 24 + 24, y0, "Grafen er tastaturets ekko", 22, "s", 600)
    y1 = g.para(lx, y0 + 26, "Hvert siffer du taster strekker pilen. Ved 24 når den diagonalen for Posisjon 27: 16 på vei og 24 til gir 40 på vei, mens du fortsatt har 13 i Restordre.", 690, 16, 23)
    g.para(lx, y1 + 6, "Grafen sier ikke om 24 er riktig. Den viser regnestykket og hvor du havner. Fra Uke 12 ser du om punktet går over diagonalene eller langs dem.", 690, 16, 23, c=MUTED)
    yy3 = 826
    cols3 = [(lx, "Ordre: rett opp.", "Du bestemmer hvor langt."),
             (lx + 235, "Levering: langs diagonalen.", "Posisjon endres ikke."),
             (lx + 470, "Innkommende ordre: mot venstre.", "Du bestemmer den ikke.")]
    arrow(g, lx + 10, yy3 + 34, lx + 10, yy3 + 2, WARM, 2.2, 7)
    arrow(g, lx + 235, yy3 + 2, lx + 261, yy3 + 28, INK, 2.2, 7)
    arrow(g, lx + 502, yy3 + 18, lx + 470, yy3 + 18, MUTED, 2.2, 7)
    for (cx3, a3, b3), off in zip(cols3, (24, 36, 42)):
        g.t(cx3 + off, yy3 + 14, a3 if off != 42 else "Innkommende ordre:", 14, w=700)
        g.t(cx3 + off, yy3 + 33, b3 if off != 42 else "mot venstre", 14, c=MUTED)
    g.t(lx, 906, "P3 Det som er på vei blir glemt · P1 Lager er en opphopning (panelet) · P7 Overreaksjon forsterker også", 14, w=600, c=INK)
    g.save()


# ---------- 06 dynamikk ----------

def page_06():
    g = Svg("06-spilldynamikk", 2100, 1200, "Fase: en Uke i seks ruter",
            "Seks telefoner: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte og spillet slutter.")
    g.t(54, 54, "Én Uke i seks ruter", 32, "s", 600)
    g.t(2046, 54, "Demodata, spill 17", 15, c=MUTED, a="end")
    sc = 0.8
    w_ = 390 * sc
    gap = (2100 - 108 - 6 * w_) / 5
    xs = [54 + i * (w_ + gap) for i in range(6)]
    tops = 118
    notes = [
        ("A  Uka åpner", "Punktet har flyttet seg: opp, skrått, til venstre. Du ser hvorfor."),
        ("B  Beslutningen", "24 med 16 på vei. Pilen viser Posisjon 3 til 27, uten dom."),
        ("C  Bekreftet", "Ordren er låst. Du ser hvem Uka venter på, og hvor lenge."),
        ("D  Uka går videre", "Tre bevegelser spilles av. Kan hoppes over, aldri over 2 sek."),
        ("E  Jonas er borte", "Pause, så KI-spiller, merket. Stiplet bane er KI-ens uker."),
        ("F  Spillet slutter", "Kjedens Totalkostnad først, så per Rolle, videre til Debrief."),
    ]
    for x, (a, b) in zip(xs, notes):
        g.t(x, 88, a, 18, "s", 600)
    # A
    phone(g, xs[0], tops, sc)
    header(g, "Grossist", "Sara", 11, m(11)["kost"])
    plane_block(g, 11, None, show_moves=True)
    strip(g, 20, 470, 350, 56, G, 11, label_w=84, yr=(-20, 30))
    regnestykke(g, 11, None)
    order_input(g, None)
    pad(g)
    status_lines(g, lines=["Uka venter på deg og Jonas (3 min)."])
    g.end()
    # B
    phone(g, xs[1], tops, sc)
    game_screen(g)
    g.end()
    # C
    phone(g, xs[2], tops, sc)
    header(g, "Grossist", "Sara", 11, m(11)["kost"])
    plane_block(g, 11, 24, confirmed=True)
    strip(g, 20, 470, 350, 56, G, 11, label_w=84, yr=(-20, 30))
    g.t(20, 560, "Du bestilte 24. Posisjon 27.", 19, "s", 600)
    g.t(20, 582, "Ordren er låst.", 14.5, c=MUTED)
    g.t(20, 622, "Uka venter på", 14.5, w=700)
    rows = [("Detaljist", "Ida", "har bestilt"), ("Grossist", "Du", "har bestilt"), ("Distributør", "Mikkel", "har bestilt"), ("Fabrikk", "Jonas", "venter, 3 min")]
    yy = 650
    for r, n, st in rows:
        bold = st.startswith("venter")
        g.t(20, yy, r, 15)
        g.t(130, yy, n, 15, w=600 if bold else 400)
        g.t(370, yy, st, 15, w=700 if bold else 400, a="end", c=TEXT if bold else MUTED)
        g.line(20, yy + 8, 370, yy + 8, GRIDM, 0.8)
        yy += 34
    g.end()
    # D
    phone(g, xs[3], tops, sc)
    m12 = m(12)
    header(g, "Grossist", "Sara", 12, m12["kost"])
    p = Plane(g, 20, 84, 7.0, R11[0], R11[1])
    p.grid()
    p.diag(27, AXIS, 1, "5 4", "Posisjon 27", at=0.72)
    p.diag(m12["pos"], AXIS, 1.1, None, f"Posisjon {m12['pos']}", at=0.74)
    p.bane(points(G, 11), fade=14, wmax=2.2)
    mv = moves(p, 11, c_up=INK)
    p.now(mv["d"], r=6, label="Uke 12", dx=-10, dy=-10, a="end")
    yy = 472
    for t_, c_ in ((f"Ordre 24 legges på veien: opp.", TEXT), (f"Levering {mv['l']} kommer: langs diagonalen.", TEXT), (f"Innkommende ordre {mv['inc']} går ut: mot venstre.", TEXT)):
        g.t(20, yy, t_, 15.5, c=c_)
        yy += 25
    g.t(20, yy + 16, f"Posisjon {m(11)['pos'] + 24} − {mv['inc']} = {m12['pos']}", 20, "s", 600)
    g.button(20, 640, 350, 56, "Hopp over", False, 17)
    g.t(195, 725, "Avspillingen varer under 2 sekunder.", 14, c=MUTED, a="middle")
    g.end()
    # E Jonas
    phone(g, xs[4], tops, sc)
    F = S["Fabrikk"]
    wk = 14
    mj = m(wk, "Fabrikk")
    header(g, "Fabrikk", "Jonas", wk, mj["kost"])
    p = Plane(g, 20, 84, 10.0, (-10, 25), (0, 35))
    p.grid(ticks=10)
    pj = points(F, wk)
    p.diag(mj["pos"], AXIS, 1.1, None, f"Posisjon {mj['pos']}", at=0.8)
    ki_from = 12
    p.bane(pj, fade=14, wmax=2.6, dashed=set(range(ki_from - 1, wk)))
    p.now(pj[-1], r=6)
    g.t(p.X(pj[-1][0]) + 11, p.Y(pj[-1][1]) - 12, "KI-spiller", 14, w=700, halo=SCREEN)
    g.t(20, 480, "Du var borte i 24 timer.", 19, "s", 600)
    yy = g.para(20, 506, f"Spillet tok Pause, så overtok en KI-spiller Fabrikk fra Uke {ki_from} så de tre andre kunne fortsette. Ordrene den ga står merket i loggen.", 350, 15, 21)
    g.button(20, yy + 10, 350, 58, "Ta tilbake setet", True, 18)
    yy += 94
    g.t(20, yy, "De andre ser", 14.5, w=700)
    g.t(20, yy + 26, "Fabrikk", 15)
    g.t(130, yy + 26, "KI-spiller", 15, w=600)
    g.t(370, yy + 26, "Jonas er borte", 15, c=MUTED, a="end")
    g.line(20, yy + 34, 370, yy + 34, GRIDM, 0.8)
    g.t(20, yy + 60, "Du får setet tilbake fra neste Uke.", 14, c=MUTED)
    g.end()
    # F
    phone(g, xs[5], tops, sc)
    g.t(20, 56, "Spillet er ferdig", 28, "s", 600)
    g.t(20, 100, "Kjedens Totalkostnad", 15, c=MUTED)
    g.t(20, 146, kr(S17["kjedekost"]), 44, "s", 600)
    yy = 190
    mx = max(S17["kost_per_rolle"].values())
    for r in ROLES:
        v = S17["kost_per_rolle"][r]
        you = r == "Grossist"
        g.t(20, yy, r + (", du" if you else ""), 15, w=700 if you else 400)
        g.t(370, yy, nf(v, 2), 16, "s", 600 if you else 400, a="end")
        g.rect(20, yy + 7, v / mx * 350, 4, fill=INK if you else "#8DA2BE", rx=1)
        yy += 42
    p = Plane(g, 45, 366, 3.75, (-45, 35), (0, 95) if False else (0, 90))
    p.grid(fine=None, major=10, ticks=20, side_labels=False, labels=False)
    p.bane(points(G), wmax=2.4, r=1.4)
    g.t(45, 366 + p.h + 20, "Din bane. Hvorfor ble den slik?", 15, w=600)
    g.button(20, 758, 350, 56, "Gå til Debrief", True, 18)
    g.end()
    # Notater
    ny = tops + 844 * sc + 28
    for x, (a, b) in zip(xs, notes):
        g.para(x, ny, b, w_ - 6, 15, 21)
    ny2 = ny + 62
    g.line(54, ny2 - 18, 2046, ny2 - 18, GRIDM, 1)
    g.t(54, ny2 + 10, "Det spilleren lærer av grafen uke for uke", 20, "s", 600)
    g.para(54, ny2 + 36, "Først står punktet stille. Så glir det mot venstre og opp, og det ser ut som om ingenting hjelper, selv om På vei vokser. Så bærer Levering punktet langs diagonalen, og Lager kommer tilbake uten at Posisjon endrer seg. Etter noen uker er spørsmålet ikke lenger om ordren var riktig, men hvorfor banen svinger.", 1992, 15.5, 22, c=MUTED)
    fy = ny2 + 90
    weeks = [7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29]
    fw = (1992 - 11 * 16) / 12
    kf = fw / 80
    for i, wk in enumerate(weeks):
        fxx = 54 + i * (fw + 16)
        q = Plane(g, fxx, fy, kf, (-45, 35), (0, 95))
        q.grid(fine=None, major=10, labels=False, side_labels=False)
        q.diag(m(wk)["pos"], AXIS, 0.8)
        q.bane(points(G, wk), fade=16, wmin=0.8, wmax=2.2, r=1.1)
        q.now(points(G, wk)[-1], r=3.6)
        g.t(fxx, fy + q.h + 18, f"Uke {wk}", 14, "s", 600)
        g.t(fxx + fw, fy + q.h + 18, f"Posisjon {nf(m(wk)['pos'])}", 13, c=MUTED, a="end")
    g.save()


# ---------- 07 debrief ----------

def page_07():
    g = Svg("07-debrief", 2100, 1200, "Fase: Gruppedebrief og delt skjerm",
            "Fire faseplan i samme skala fra Detaljist til Fabrikk, med simulert referanse og etterspørselshoppet, og fem steg under.")
    # Delt skjerm
    sx, sy, sw_, sh = 40, 24, 2020, 540
    g.rect(sx, sy, sw_, sh, fill=SCREEN, stroke=GRIDM, sw=1, rx=10)
    g.t(sx + 32, sy + 52, "Fire ledd, samme skala: ett lite hopp ble til fire sløyfer", 34, "s", 600)
    g.t(sx + sw_ - 30, sy + 42, "Delt skjerm, åpner etter steg 2 · Demodata, spill 17 · Grønn er simulert", 15, c=MUTED, a="end")
    k = 3.2
    xr, yr = (-65, 60), (0, 115)
    span = xr[1] - xr[0]
    colx = sx + 32
    py = sy + 72
    # etterspørsel i samme skala
    g.t(colx, py + 14, "Kundeetterspørsel", 16, "s", 600)
    bw = 170
    dem = S["demand"]
    base = py + 66
    X = lambda i: colx + i * bw / 35
    Y = lambda v: base - v * k
    g.line(colx, base, colx + bw, base, AXIS, 1.1)
    d = f"M{X(0):.1f},{Y(dem[0]):.1f}"
    for i in range(1, 36):
        d += f" L{X(i):.1f},{Y(dem[i - 1]):.1f} L{X(i):.1f},{Y(dem[i]):.1f}"
    g.path(d, WARM, 2.4)
    g.t(colx, base + 18, "4 per uke, så 8 fra Uke 5.", 14)
    g.para(colx, base + 40, "Tegnet i samme skala som planene. Hele hoppet er fire enheter.", 190, 14, 19, c=MUTED)
    # form-forklaring
    yy = base + 118
    g.t(colx, yy, "Slik leses det", 16, "s", 600)
    yy = g.para(colx, yy + 21, "Hvert punkt er én Uke, mørkest sist. Alle går med klokka. Grønn er simulert: alle fire teller det som er på vei.", 200, 14, 19, c=MUTED)
    g.para(colx, yy + 6, f"Samme retning i {CW} av {len(FIN)} ferdige spill, for Fabrikk. Struktur, ikke personer.", 200, 14, 19, w=600)
    px0 = colx + 232
    gap = (sx + sw_ - 32 - px0 - 4 * k * span) / 3
    labelpos = {"Detaljist": (21, 2), "Grossist": (21, 8), "Distributør": (18, 12), "Fabrikk": (18, 12)}
    for i, r in enumerate(ROLES):
        x = px0 + i * (span * k + gap)
        p = Plane(g, x, py, k, xr, yr)
        p.grid(fine=None, major=10, ticks=40, tsize=13, side_labels=False)
        p.diag(24, AXIS, 0.9, "3 4", "Posisjon 24 ved start" if i == 0 else None, at=0.14, lc=MUTED, weight=400)
        ptsr = points(ALLE["serier"][r])
        p.bane(ptsr, color=REF, wmin=1.4, wmax=1.4, dots=False)
        pts_ = points(S[r])
        p.bane(pts_, wmax=3.0, wmin=1.0, r=1.8)
        g.t(x + span * k - 6, py + 22, r, 21, "s", 600, a="end", halo=SCREEN)
        cap_y = py + p.h + 42
        g.t(x, cap_y, f"Forsterkning {fx(S17['forsterkning'][r])}", 17, "s", 600)
        g.t(x + 170, cap_y, f"Simulert {fx(ALLE['forsterkning'][r])}", 15, "s", 500, c=REF)
        g.t(x + span * k, cap_y, f"{nf(S17['kost_per_rolle'][r], 2)} kr", 15, "s", a="end", c=MUTED)
        if r == "Distributør":
            g.t(p.X(-6), p.Y(36), "Simulert", 14.5, w=700, c=REF, a="middle", halo=SCREEN)
        if r == "Fabrikk":
            g.t(p.X(pts_[-1][0]), p.Y(pts_[-1][1]) - 12, "Uke 36", 13, c=MUTED, a="middle", halo=SCREEN)

    # Fem steg
    ty = 582
    wd = 392
    gp = (2020 - 5 * wd) / 4
    xs = [40 + i * (wd + gp) for i in range(5)]
    h = 596
    titles = ["1  Skriv Forklaring", "2  Etterspørselen avsløres", "3  Alle fire Roller", "4  Ditt øyeblikk: Uke 11", "5  Debrief-quiz"]
    for x, t_ in zip(xs, titles):
        g.rect(x, ty, wd, h, fill=SCREEN, stroke=GRIDM, sw=1, rx=10)
        g.t(x + 18, ty + 34, t_, 21, "s", 600)
    # Steg 1
    x = xs[0] + 18
    p = Plane(g, x, ty + 50, 2.7, (-45, 35), (0, 95))
    p.grid(fine=None, major=10, side_labels=False, labels=False)
    p.bane(points(G), wmax=2.4, r=1.2)
    tx = x + p.w + 14
    g.para(tx, ty + 68, "Din bane, slik du spilte den.", 130, 14.5, 20, c=MUTED)
    g.para(tx, ty + 136, "Du ser ingen andres tall ennå.", 130, 14.5, 20, c=MUTED)
    yy = ty + 50 + p.h + 30
    g.t(x, yy, "Hvorfor vokste Restordre fra Uke 9?", 16, w=700)
    g.rect(x, yy + 12, wd - 36, 104, fill=WHITE, stroke=AXIS, sw=1, rx=6)
    g.para(x + 12, yy + 36, "Vi fikk flere ordre og det tok lang tid før noe kom. Jeg bestilte mye i Uke 11 fordi jeg trodde det var", wd - 62, 15, 21)
    yy += 140
    g.rect(x, yy - 4, wd - 36, 52, fill=KEY, rx=6)
    g.para(x + 12, yy + 17, "Avsløringen er låst. Den åpner når alle i gruppa har levert Forklaring.", wd - 62, 13.5, 18)
    g.button(x, yy + 58, wd - 36, 44, "Lever Forklaring", True, 16)
    # Steg 2
    x = xs[1] + 18
    g.para(x, ty + 68, "Kundene ville ha 4 per uke, så 8 fra Uke 5. Deretter ingenting nytt.", wd - 36, 21, 27, "s", 500)
    gx, gy, gw, gh = x, ty + 150, wd - 100, 250
    X = lambda i: gx + i * gw / 35
    Y = lambda v: gy + gh - v / 30 * gh
    g.line(gx, Y(0), gx + gw, Y(0), AXIS, 1.1)
    for v in (10, 20, 30):
        g.line(gx, Y(v), gx + gw, Y(v), GRIDM, 0.8)
        g.t(gx - 4, Y(v) - 3, str(v), 13, "s", c=MUTED)
    inc = G["innkommende_ordre"]
    g.path("M" + " L".join(f"{X(i):.1f},{Y(inc[i]):.1f}" for i in range(36)), FADE, 1.4)
    od = G["ordre"]
    g.path("M" + " L".join(f"{X(i):.1f},{Y(od[i]):.1f}" for i in range(36)), INK, 1.5)
    d = f"M{X(0):.1f},{Y(dem[0]):.1f}"
    for i in range(1, 36):
        d += f" L{X(i):.1f},{Y(dem[i - 1]):.1f} L{X(i):.1f},{Y(dem[i]):.1f}"
    g.path(d, WARM, 3)
    g.t(gx + gw + 4, Y(dem[-1]) + 4, "Kundene", 13.5, w=700)
    g.t(X(10) + 8, Y(24) + 2, "Dine ordre", 13.5, c=INK, w=600)
    g.t(gx, Y(0) + 17, "Uke 1", 13, c=MUTED)
    g.t(gx + gw, Y(0) + 17, "Uke 36", 13, c=MUTED, a="end")
    yy = gy + gh + 50
    yy = g.para(x, yy, "Det du så var Innkommende ordre, aldri kundene. Hver Rolle regnet ut sine ordre fra det.", wd - 36, 15, 21)
    g.para(x, yy + 5, "P4 Ordrer er ikke etterspørsel. Øvelsen heter Beer Game.", wd - 36, 14, 19, w=600, c=INK)
    # Steg 3
    x = xs[2] + 18
    gx, gw = x, wd - 36 - 96
    X = lambda i: gx + i * gw / 35
    unit = 3.1
    rows_ = [("Fabrikk", ty + 150), ("Distributør", ty + 234), ("Grossist", ty + 318), ("Detaljist", ty + 402)]
    for r, base in rows_:
        o = S[r]["ordre"]
        Y = lambda v, b_=base: b_ - v * unit
        d = f"M{X(0):.1f},{base:.1f} " + " ".join(f"L{X(i):.1f},{Y(o[i]):.1f}" for i in range(36)) + f" L{X(35):.1f},{base:.1f} Z"
        g.path(d, ROLE_TONE[r], 1.6, fill=SCREEN)
        g.line(gx, base, gx + gw, base, AXIS, 1)
        pk = max(range(36), key=lambda i: o[i])
        if r in ("Distributør", "Detaljist"):
            g.t(X(pk), Y(o[pk]) - 6, f"Uke {pk + 1}", 13, c=MUTED, a="middle", halo=SCREEN)
        else:
            g.t(X(pk) + 7, Y(o[pk]) + 10, f"Uke {pk + 1}", 13, c=MUTED, halo=SCREEN)
        g.t(gx + gw + 8, base - 16, r, 14.5, w=700)
        g.t(gx + gw + 8, base + 2, fx(S17["forsterkning"][r]), 17, "s", 600)
    base = ty + 452
    d = f"M{X(0):.1f},{base - dem[0] * unit:.1f}"
    for i in range(1, 36):
        d += f" L{X(i):.1f},{base - dem[i - 1] * unit:.1f} L{X(i):.1f},{base - dem[i] * unit:.1f}"
    g.path(d, WARM, 2.2)
    g.line(gx, base, gx + gw, base, AXIS, 1)
    g.t(gx + gw + 8, base - 12, "Kundene", 14.5, w=700)
    g.t(gx, base + 16, "Uke 1", 13, c=MUTED)
    g.t(gx + gw, base + 16, "Uke 36", 13, c=MUTED, a="end")
    peaks = {r: max(range(36), key=lambda i: S[r]["ordre"][i]) + 1 for r in ROLES}
    yy = base + 38
    yy = g.para(x, yy, f"Samme akse og skala på alle fire. Fra Grossist til Fabrikk blir toppen høyere og senere: Uke {peaks['Grossist']}, {peaks['Distributør']}, {peaks['Fabrikk']}.", wd - 36, 14.5, 19.5)
    g.t(x, yy + 3, "P5 Forsterkning · P6 Struktur gir atferd", 14, w=600, c=INK)
    # Steg 4
    x = xs[3] + 18
    p = Plane(g, x, ty + 50, 3.5, (-30, 25), (0, 50))
    p.grid(fine=None, major=10, side_labels=False, labels=False)
    p.diag(3, AXIS, 1)
    p.diag(27, WARM, 1.2, "4 3")
    p.bane(points(G, 11), fade=14, wmax=2.4)
    p.now(points(G, 11)[-1], r=5)
    arrow(g, p.X(-13), p.Y(16), p.X(-13), p.Y(40), WARM, 2.2, 7)
    g.t(p.X(-13) + 6, p.Y(28), "+24", 14, "s", 600, halo=SCREEN)
    tx = x + p.w + 12
    mm = m(11)
    g.t(tx, ty + 66, "Du så", 13.5, c=MUTED)
    g.t(tx, ty + 86, f"Restordre {mm['rest']}", 15, w=600)
    g.t(tx, ty + 106, f"På vei {mm['pv']}", 15, w=600)
    g.t(tx, ty + 130, "Du bestilte", 13.5, c=MUTED)
    g.t(tx, ty + 150, "24, Posisjon 27", 15, w=600)
    g.t(tx, ty + 174, "Kostnad etter Uke 11", 13.5, c=MUTED)
    g.t(tx, ty + 194, kr(S17["kost_per_rolle"]["Grossist"] - mm["kost"]), 15, w=600)
    yy = ty + 50 + p.h + 28
    g.t(x, yy, "De andre så samme uke", 15, w=700)
    yy += 22
    for r, txt in (("Ida", f"Restordre {m(11,'Detaljist')['rest']}, inn {m(11,'Detaljist')['inc']}"),
                   ("Mikkel", f"Lager {m(11,'Distributør')['lager']}, inn {m(11,'Distributør')['inc']}"),
                   ("Jonas", f"Lager {m(11,'Fabrikk')['lager']}, inn {m(11,'Fabrikk')['inc']}")):
        g.t(x, yy, r, 14.5, w=600)
        g.t(x + 70, yy, txt, 14.5, c=MUTED)
        yy += 21
    yy += 8
    g.t(x, yy, "Simulert: bare du teller På vei", 15, w=700, c=REF)
    yy += 21
    g.t(x, yy, f"Din kostnad {nf(BARE['kost_per_rolle']['Grossist'],2)} mot {nf(S17['kost_per_rolle']['Grossist'],2)}.", 14.5)
    yy += 20
    g.t(x, yy, f"Forsterkning {fx(BARE['forsterkning']['Grossist'])} mot {fx(S17['forsterkning']['Grossist'])}. Ikke en fasit.", 14.5)
    yy += 26
    yy = g.para(x, yy, f"Mikkel fikk 24 i Uke 13 og bestilte {S['Distributør']['ordre'][12]} samme uke. Hvert sete regner ut sin ordre av det det ser.", wd - 36, 14, 19)
    # hva det kostet senere
    cx0, cw0, ch0 = x, wd - 36 - 62, 46
    cy0 = yy + 2
    ks = G["kost_sum"]
    XK = lambda i: cx0 + i * cw0 / 35
    YK = lambda v: cy0 + ch0 - v / max(ks) * ch0
    g.line(cx0, cy0 + ch0, cx0 + cw0, cy0 + ch0, AXIS, 1)
    g.path("M" + " L".join(f"{XK(i):.1f},{YK(ks[i]):.1f}" for i in range(36)), INK, 1.8)
    g.circ(XK(10), YK(ks[10]), 4, fill=WARM, stroke=SCREEN, sw=1.5)
    g.t(XK(10) + 4, YK(ks[10]) - 10, f"Uke 11: {nf(ks[10], 2)}", 13, c=TEXT, a="end", halo=SCREEN)
    g.t(cx0 + cw0 + 6, YK(ks[-1]) + 11, nf(ks[-1], 2), 14, "s", 600)
    g.t(x, ty + h - 14, "KI-generert, kan ta feil", 13.5, w=600, c=MUTED)
    # Steg 5
    x = xs[4] + 18
    w18 = m(18)
    yy = g.para(x, ty + 66, f"I Uke 18 er netto lager {nf(w18['net'])} og På vei {w18['pv']}. Hva er Posisjon?", wd - 36, 18, 25, "s", 500)
    opts = [(nf(w18["net"]), True, False), (str(w18["pv"]), False, False), (str(w18["pos"]), False, True), (str(w18["pv"] - w18["net"]), False, False)]
    yy += 6
    for lab, wrong, right in opts:
        fill = WHITE
        stroke = GRIDM
        sw_ = 1
        if wrong:
            stroke, sw_ = TEXT, 1.6
        if right:
            stroke, sw_ = INK, 1.6
        g.rect(x, yy, wd - 36, 40, fill=fill, stroke=stroke, sw=sw_, rx=6)
        g.t(x + 14, yy + 26, lab, 17, "s", 500)
        tag = "Ditt svar" if wrong else ("Riktig" if right else "")
        if tag:
            g.t(x + wd - 50, yy + 25, tag, 14, w=700, a="end")
        yy += 47
    yy += 18
    g.t(x, yy, "Slik regnes det", 16, "s", 600)
    pz = Plane(g, x, yy + 12, 1.7, (-45, 35), (0, 95))
    pz.grid(fine=None, major=10, side_labels=False, labels=False)
    pz.diag(w18["pos"], WARM, 1.2)
    pz.bane(points(G, 18), fade=16, wmax=1.8, r=0.9, dots=False)
    pz.now((w18["net"], w18["pv"]), r=4)
    g.para(x + pz.w + 14, yy + 26, f"{nf(w18['net'])} er netto lager, alene. Det som er på vei hører med: {nf(w18['net'])} + {w18['pv']} = {w18['pos']}. Punktet ligger på diagonalen for {w18['pos']}.", wd - 36 - pz.w - 14, 14, 19)
    g.save()


# ---------- 08 oversikt ----------

def page_08():
    g = Svg("08-laerer-oversikt", 1600, 1000, "Fase: Oversikt over 60 Klassespill",
            "Seksti små faseplan i rutenett med status under, og tabell over spill som trenger oppfølging. Trakt og filtre.")
    sp = KL["spill"]
    g.t(40, 50, "Oversikt", 30, "s", 600)
    g.t(165, 49, "class-of-1994, IBE160 · Spillfrist ti. 8. des", 15, c=MUTED)
    g.t(1560, 49, "Demodata", 14, c=MUTED, a="end")
    # Filtre
    fx_ = 40
    near = next(s for s in sp if s["spill"] == 2)
    nfer = len([s for s in sp if s["status"] == "ferdig"])
    npau = len([s for s in sp if s["status"] == "pauset"])
    npaa = len([s for s in sp if s["status"] == "pågår"]) + npau
    nven = len([s for s in sp if s["status"] == "venter"])
    for lab, on in ((f"Alle {len(sp)}", True), (f"Ferdig {nfer}", False), (f"Pågår {npaa}, {npau} i Pause", False), (f"Venter {nven}", False), ("Nær KI-overtakelse 1", False)):
        w_ = len(lab) * 7.5 + 22
        g.rect(fx_, 68, w_, 30, fill=INK if on else "none", stroke=INK if on else AXIS, sw=1, rx=5)
        g.t(fx_ + w_ / 2, 88, lab, 14, w=600, c=WHITE if on else TEXT, a="middle")
        fx_ += w_ + 8
    # Rolle
    g.t(fx_ + 10, 88, "Planene viser", 14, c=MUTED)
    xr2 = fx_ + 104
    for i, r in enumerate(ROLES):
        on = r == "Fabrikk"
        wd = len(r) * 7.3 + 14
        if on:
            g.rect(xr2 - 6, 70, wd, 26, fill=KEY, rx=4)
        g.t(xr2 + 1, 88, r, 14, w=700 if on else 400, c=TEXT if on else MUTED)
        xr2 += wd + 2
    # Rutenett
    k = 100 / (CLASS_XR[1] - CLASS_XR[0])
    cw, ch = 105.0, 122
    x0, y0 = 40, 116
    for idx, s_ in enumerate(sp):
        cx = x0 + (idx % 10) * cw
        cy = y0 + (idx // 10) * ch
        p = Plane(g, cx, cy, k, CLASS_XR, CLASS_YR)
        is_near = s_["spill"] == 2
        g.rect(p.x, p.y, p.w, p.h, fill=WHITE if s_["status"] != "ferdig" else "#FBFCFD", stroke=GRIDM, sw=0.8)
        g.line(p.X(0), p.y, p.X(0), p.y + p.h, GRIDM, 0.8)
        pts_ = CLASS_PTS[s_["spill"]]
        p.bane(pts_, fade=None if s_["status"] == "ferdig" else 16, wmin=0.7, wmax=1.6, dots=False)
        if s_["status"] != "ferdig":
            p.now(pts_[-1], r=2.8, ring=WHITE)
        if is_near:
            g.rect(p.x - 3, p.y - 3, p.w + 6, p.h + 44, fill="none", stroke=WARM, sw=1.8, rx=3)
        ty = cy + p.h + 15
        g.t(cx, ty, f"{s_['spill']}", 13.5, "s", 700)
        st = s_["status"]
        if st == "ferdig":
            g.t(cx + 20, ty, nf(s_["kjedekost"]) + " kr", 12.5, c=MUTED)
            line = "Ferdig" + (f", KI {s_['ki_seter']}" if s_.get("ki_seter") else "")
            col, wt = MUTED, 400
        else:
            g.t(cx + 20, ty, f"Uke {s_['uke']}" + (f", KI {s_['ki_seter']}" if s_.get("ki_seter") else ""), 12.5, c=MUTED)
            if st == "venter":
                line, col, wt = f"{s_['navn']} {s_['ventet_timer']} t", TEXT, 700
            elif st == "pauset":
                line, col, wt = "Pause, 19:00", TEXT, 700
            else:
                line, col, wt = "Pågår", MUTED, 400
        g.t(cx, ty + 15, line, 12.5, w=wt, c=col)
    # Trakt under rutenettet
    ty0 = y0 + 6 * ch + 12
    g.line(40, ty0 - 8, 1080, ty0 - 8, GRIDM, 1)
    g.t(40, ty0 + 20, "Trakten", 20, "s", 600)
    tr = KL["traktA"]
    labs = [("registrert", "Registrert"), ("klassespill_ferdig", "Klassespill ferdig"), ("debrief_ferdig", "Debrief ferdig"), ("quiz_bestått", "Quiz bestått"), ("replay_ferdig", "Replay ferdig"), ("test_levert", "Test levert"), ("ki_vurdering_klar", "KI-vurdering klar")]
    colw = 1040 / 7
    for i, (key, lab) in enumerate(labs):
        v = tr[key]
        tx = 40 + i * colw
        g.t(tx, ty0 + 58, str(v), 25, "s", 500)
        g.rect(tx, ty0 + 68, colw - 12, 5, fill=KEY, rx=1)
        if v:
            g.rect(tx, ty0 + 68, (colw - 12) * v / tr["registrert"], 5, fill=INK, rx=1)
        g.t(tx, ty0 + 91, lab, 13)
    # Tabell
    rx, rw = 1110, 450
    yy = 132
    g.t(rx, yy, "Spill som ikke er ferdige", 20, "s", 600)
    g.t(rx + rw, yy, "Lengst ventetid først", 13, c=MUTED, a="end")
    yy += 25
    colsx = [rx, rx + 40, rx + 82, rx + rw]
    for x, lab, a in ((colsx[0], "Spill", "start"), (colsx[1], "Uke", "start"), (colsx[2], "Status", "start"), (colsx[3], "Handling", "end")):
        g.t(x, yy, lab, 13, w=600, c=MUTED, a=a)
    g.line(rx, yy + 6, rx + rw, yy + 6, AXIS, 1)
    yy += 25
    wait = sorted([x for x in sp if x["status"] == "venter"], key=lambda x: -x["ventet_timer"])
    paused = [x for x in sp if x["status"] == "pauset"]
    going = sorted([x for x in sp if x["status"] == "pågår"], key=lambda x: -x["uke"])
    for s_ in wait + paused + going:
        hot = s_["spill"] == 2
        st = s_["status"]
        if hot:
            g.rect(rx - 6, yy - 16, rw + 12, 42, fill=WHITE, stroke=WARM, sw=1.4, rx=4)
        g.t(colsx[0], yy, str(s_["spill"]), 14.5, "s", 700 if hot else 500)
        g.t(colsx[1], yy, str(s_["uke"]), 14, "s")
        ki = f", KI {s_['ki_seter']}" if s_.get("ki_seter") else ""
        if st == "venter":
            g.t(colsx[2], yy, f"Venter på {s_['navn']} ({s_['venter_paa']}) {s_['ventet_timer']} t", 13.5, w=700 if hot else 400)
            g.t(colsx[3], yy, "Send Melding", 13.5, w=600, c=INK, a="end")
            g.line(colsx[3] - 80, yy + 3.5, colsx[3], yy + 3.5, INK, 0.9)
        elif st == "pauset":
            g.t(colsx[2], yy, f"Pause, fortsetter {s_['fortsetter']}{ki}", 13.5)
            g.t(colsx[3], yy, "Åpne", 13.5, w=600, c=INK, a="end")
        else:
            g.t(colsx[2], yy, f"Pågår{ki}", 13.5, c=MUTED)
            g.t(colsx[3], yy, "Åpne", 13.5, w=600, c=INK, a="end")
        if hot:
            g.t(colsx[2], yy + 18, "KI overtar om 1 t, ved 24 t", 13.5, w=700)
            yy += 18
        yy += 24
    yy += 8
    g.line(rx, yy - 14, rx + rw, yy - 14, GRIDM, 1)
    yy += 12
    fq = KL["ferdige"]
    g.t(rx, yy, f"De {fq['antall']} ferdige", 20, "s", 600)
    yy += 25
    g.t(rx, yy, f"Kjedekost, median {nf(fq['kjedekost']['median'])} kr, midtre halvdel {nf(fq['kjedekost']['q1'])} til {nf(fq['kjedekost']['q3'])}.", 14)
    yy += 20
    fab = fq["forsterkning_per_rolle"]["Fabrikk"]
    g.t(rx, yy, f"Forsterkning Fabrikk, median {fx(fab['median'])}. I fjor {fx(KL['fjoraaret']['median_forsterkning_fabrikk'])}.", 14)
    yy += 20
    g.t(rx, yy, f"Med klokka i {CW} av {len(FIN)}: formen kommer av strukturen.", 14)
    yy += 26
    g.para(rx, yy, "Stor sløyfe er store svingninger. Klikk et plan for Spillinnsikt. På vei er regnet ut av Ordre og netto lager.", rw, 13.5, 19, c=MUTED)
    g.save()


# ---------- 01 landing ----------

def page_01():
    g = Svg("01-landing", 1440, 1200, "Fase: landingsside for faglærere",
            "Landingsside der ett setes faseplan bærer siden. Primærhandling Be om lærertilgang, sekundær Logg inn. Så starten av oversikten.", bg=SCREEN)
    g.t(64, 62, "Fase", 28, "s", 600)
    g.t(1376, 58, "Logg inn", 16, w=600, c=INK, a="end")
    yy = 170
    for ln in ["Hele øvelsen,", "fra invitasjon", "til PDF-rapport"]:
        g.t(64, yy, ln, 62, "s", 500)
        yy += 70
    yy = g.para(64, yy + 2, "Grupper på fire driver hvert sitt ledd i en forsyningskjede, med én beslutning per Uke. Du får alle spillene på én skjerm, og KI-spillere fyller tomme seter.", 500, 20, 29, c=TEXT)
    g.button(64, yy + 14, 240, 58, "Be om lærertilgang", True, 18)
    g.button(320, yy + 14, 130, 58, "Logg inn", False, 18)
    facts = ["Kjører hele øvelsen, uten at du blir dommer.", "Studentlisten kommer fra Canvas-eksport.", "Ett fravær stopper ikke gruppa: KI-spiller overtar, merket.", "Ingen spill blir stående uferdig.", "På mobil og på norsk."]
    fy = yy + 112
    for f_ in facts:
        g.t(64, fy, f_, 16.5)
        g.line(64, fy + 9, 520, fy + 9, GRIDM, 0.8)
        fy += 31
    k = 7.55
    p = Plane(g, 616, 76, k, (-45, 50), (0, 95))
    p.grid(fine=5, major=10, ticks=20, tsize=14)
    pts_ = points(G, 29)
    p.diag(m(29)["pos"], AXIS, 1.0, None, f"Samme Posisjon langs denne linjen: {m(29)['pos']}", at=0.28, size=15)
    p.bane(pts_, fade=20, wmin=1.2, wmax=4, r=2.6)
    p.now(pts_[-1], r=8, label="Nå", dx=-12, dy=26, size=17, a="end")
    p.mark(pts_[10], "Uke 11", dx=12, dy=16, r=0, size=15, c=MUTED)
    g.t(616, 76 + p.h + 44, "Ett sete, Grossist: hvert punkt er én Uke, mørkest nå. Demodata.", 15, c=MUTED)
    y2 = 880
    g.line(64, y2 - 26, 1376, y2 - 26, GRIDM, 1)
    g.t(64, y2 + 22, "Alle spillene på én skjerm", 38, "s", 500)
    g.para(64, y2 + 58, "Klasser på rundt 250 studenter blir rundt 60 spill. Du ser formen på hvert spill, hvem det venter på og hvor lenge, og kan sende en Melding derfra.", 460, 18, 26, c=TEXT)
    kk = 58 / (CLASS_XR[1] - CLASS_XR[0])
    sp = KL["spill"]
    for idx, s_ in enumerate(sp):
        cx = 616 + (idx % 12) * 63.2
        cy = y2 - 6 + (idx // 12) * 54
        q = Plane(g, cx, cy, kk, CLASS_XR, CLASS_YR)
        g.rect(q.x, q.y, q.w, q.h, fill=WHITE, stroke=GRIDM, sw=0.7)
        q.bane(CLASS_PTS[s_["spill"]], fade=None if s_["status"] == "ferdig" else 16, wmin=0.6, wmax=1.2, dots=False)
        if s_["status"] != "ferdig":
            q.now(CLASS_PTS[s_["spill"]][-1], r=2, ring=WHITE)
    g.save()


# ---------- 02 Lag klasse ----------

def field(g, x, y, w, label, value, h=44, note=None):
    g.t(x, y, label, 14.5, w=600)
    g.rect(x, y + 8, w, h, fill=WHITE, stroke=AXIS, sw=1, rx=5)
    g.t(x + 12, y + 8 + h / 2 + 5.5, value, 16)
    if note:
        g.t(x, y + h + 28, note, 13.5, c=MUTED)


def app_head(g, title, sub=None, w=1440):
    g.t(48, 54, "Fase", 22, "s", 600)
    g.t(110, 53, title, 30, "s", 600)
    if sub:
        g.t(w - 48, 50, sub, 15, c=MUTED, a="end")
    g.line(48, 74, w - 48, 74, GRIDM, 1)


def page_02():
    r = KL["roster"]
    g = Svg("02-laerer-klasse", 1440, 1000, "Fase: Lag Klasse",
            "Skjema for navn og emnekode, opplasting av Canvas-fil, valg av e-postkolonne, ugyldige rader og utsending av Invitasjoner med status.", bg=SCREEN)
    app_head(g, "Lag Klasse", "Faglærer Bård")
    x = 48
    field(g, x, 112, 300, "Navn på Klassen", "class-of-1994")
    field(g, x + 316, 112, 150, "Emnekode", "IBE160")
    g.t(x, 202, "Klasseliste fra Canvas", 14.5, w=600)
    g.rect(x, 212, 466, 72, fill=WHITE, stroke=AXIS, sw=1, rx=5, dash="5 4")
    g.t(x + 16, 242, "ibe160-canvas-eksport.xlsx", 16, w=600)
    g.t(x + 16, 266, f"{r['paa_lista']} rader lest", 14.5, c=MUTED)
    g.t(x + 450, 242, "Bytt fil", 14.5, w=600, c=INK, a="end")
    g.t(x, 316, "Hvilken kolonne er e-post?", 14.5, w=600)
    cols = [("SIS Login ID", False), ("Email", True), ("Section", False)]
    cx = x
    for lab, on in cols:
        w_ = len(lab) * 8 + 40
        g.rect(cx, 326, w_, 40, fill=INK if on else "none", stroke=INK if on else AXIS, sw=1, rx=5)
        g.t(cx + w_ / 2, 351, lab, 15, w=600, c=WHITE if on else TEXT, a="middle")
        cx += w_ + 8
    g.t(x, 392, "Første rad er overskrift. Eksempel fra kolonnen: ida.berg@student.example", 13.5, c=MUTED)
    # Invitasjon
    g.t(x, 448, "Send Invitasjoner", 24, "s", 600)
    g.para(x, 476, f"{r['paa_lista'] - r['ugyldige_rader']} gyldige adresser får en lenke. Invitasjonen er gyldig i 14 dager. Studentene registrerer seg selv.", 466, 15.5, 22)
    g.button(x, 530, 340, 54, f"Send {r['paa_lista'] - r['ugyldige_rader']} Invitasjoner", True, 17)
    g.t(x, 612, "Rett de 4 ugyldige radene først, eller send uten dem.", 14, c=MUTED)
    # Status
    g.t(x, 672, "Status etter utsending", 24, "s", 600)
    bx, bw = x, 466
    seg = [("Registrert", r["registrert"], INK), ("Manuelt", r["manuelt_registrert"], "#5D7AA3"), ("Uregistrert", r["uregistrert"], FADE)]
    tot = sum(s[1] for s in seg)
    cur = bx
    for lab, v, c in seg:
        w_ = v / tot * bw
        g.rect(cur, 690, max(w_ - 2, 2), 14, fill=c, rx=1.5)
        cur += w_
    yy = 732
    for lab, v, c in seg:
        g.t(x, yy, lab + (" registrert" if lab == "Manuelt" else ""), 15.5)
        g.t(x + 466, yy, str(v), 17, "s", 500, a="end")
        g.line(x, yy + 7, x + 466, yy + 7, GRIDM, 0.8)
        yy += 30
    g.t(x, yy + 8, f"{tot} av {r['paa_lista']} rader. Purring sendes med ett trykk til de uregistrerte.", 14, c=MUTED)
    # Høyre: ugyldige rader
    x2 = 590
    g.t(x2, 126, "Fire rader må rettes", 30, "s", 600)
    g.t(x2, 154, "Radnummer fra filen din. Skriv inn riktig adresse, eller hopp over raden.", 15.5, c=MUTED)
    bad = [(37, "Mari Holm", "mari.holm@student"), (88, "Jakob Lie", "jakob.lie.student.example"), (141, "Sofie Dahl", "sofie dahl@student.example"), (203, "Emil Aas", "")]
    why = {37: "Mangler domene", 88: "Mangler @", 141: "Mellomrom", 203: "Tom celle"}
    yy = 200
    for lab, xx in (("Rad", x2), ("Student", x2 + 60), ("I filen", x2 + 210), ("Feil", x2 + 440), ("Rett til", x2 + 590)):
        g.t(xx, yy, lab, 13.5, w=600, c=MUTED)
    g.line(x2, yy + 8, 1392, yy + 8, AXIS, 1)
    yy += 44
    for n, name, addr in bad:
        g.t(x2, yy, str(n), 17, "s", 600)
        g.t(x2 + 60, yy, name, 15.5)
        g.t(x2 + 210, yy, addr or "(tom)", 15, c=MUTED)
        g.t(x2 + 440, yy, why[n], 15)
        g.rect(x2 + 590, yy - 24, 212, 36, fill=WHITE, stroke=AXIS, sw=1, rx=4)
        g.line(x2, yy + 20, 1392, yy + 20, GRIDM, 0.8)
        yy += 56
    g.t(x2, yy + 14, "Hopp over disse 4", 15, w=600, c=INK)
    g.line(x2, yy + 18, x2 + 122, yy + 18, INK, 1)
    # Forhåndsvisning
    yy += 76
    g.t(x2, yy, "Slik leste vi filen", 24, "s", 600)
    yy += 30
    rows = [("1", "Ida Berg", "ida.berg@student.example", "Gyldig"), ("2", "Sara Nilsen", "sara.nilsen@student.example", "Gyldig"), ("3", "Mikkel Moe", "mikkel.moe@student.example", "Gyldig"), ("4", "Jonas Vik", "jonas.vik@student.example", "Gyldig"), ("5", "Noah Strand", "noah.strand@student.example", "Gyldig")]
    for lab, xx in (("Rad", x2), ("Student", x2 + 60), ("E-post", x2 + 210), ("Sjekk", x2 + 590)):
        g.t(xx, yy, lab, 13.5, w=600, c=MUTED)
    g.line(x2, yy + 8, 1392, yy + 8, AXIS, 1)
    yy += 32
    for a, b, c, d in rows:
        g.t(x2, yy, a, 15, "s")
        g.t(x2 + 60, yy, b, 15)
        g.t(x2 + 210, yy, c, 15, c=MUTED)
        g.t(x2 + 590, yy, d, 15)
        g.line(x2, yy + 10, 1392, yy + 10, GRIDM, 0.8)
        yy += 32
    g.t(x2, yy + 12, f"og {r['paa_lista'] - 5} rader til. Demodata.", 14, c=MUTED)
    g.save()


# ---------- 03 Klasseøkt ----------

def page_03():
    g = Svg("03-laerer-spill", 1440, 1100, "Fase: Klasseøkt",
            "Forhåndsutfylte Spillinnstillinger, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling i 60 spill. Kan lagres uten endring.", bg=SCREEN)
    app_head(g, "Klasseøkt", "class-of-1994, IBE160")
    x = 48
    g.t(x, 120, "Klassisk", 28, "s", 600)
    g.t(x + 112, 119, "Alt er fylt ut. Du kan lagre uten å endre noe.", 16, c=MUTED)
    g.button(1092, 92, 300, 50, "Lagre uten endring", True, 17)
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"),
            ("Etterspørsel", "4, så 8 i uke 5"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"), ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t")]
    yy = 174
    for a, b in rows:
        g.t(x, yy, a, 16)
        g.t(x + 460, yy, b, 16, "s", 500, a="end")
        g.line(x, yy + 9, x + 460, yy + 9, GRIDM, 0.8)
        yy += 33
    g.para(x, yy + 6, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", 460, 14.5, 20, c=MUTED)
    # Midt
    x2 = 570
    def seg(y, label, opts, on):
        g.t(x2, y, label, 15, w=600)
        cx = x2
        for o in opts:
            w_ = len(o) * 8 + 28
            sel = o == on
            g.rect(cx, y + 10, w_, 38, fill=INK if sel else "none", stroke=INK if sel else AXIS, sw=1, rx=5)
            g.t(cx + w_ / 2, y + 34, o, 15, w=600, c=WHITE if sel else TEXT, a="middle")
            cx += w_ + 6
    seg(174, "KI-modus", ["LLM-spillere", "Regelbaserte"], "LLM-spillere")
    seg(248, "Debrief-modus", ["Gruppedebrief", "Individuell"], "Gruppedebrief")
    seg(322, "Klassespillet er", ["Obligatorisk", "Frivillig"], "Obligatorisk")
    g.t(x2, 416, "Datoer", 24, "s", 600)
    yy = 446
    for a, b in (("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")):
        g.t(x2, yy, a, 16)
        g.t(x2 + 330, yy, b, 16, "s", 500, a="end")
        g.line(x2, yy + 9, x2 + 330, yy + 9, GRIDM, 0.8)
        yy += 33
    # Høyre
    x3 = 980
    g.t(x3, 186, "Labtimer, Datalab A2", 24, "s", 600)
    yy = 218
    for b in ("to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"):
        g.t(x3, yy, b, 16, "s", 500)
        g.line(x3, yy + 9, x3 + 412, yy + 9, GRIDM, 0.8)
        yy += 33
    g.t(x3, yy + 2, "Legg til Labtime", 15, w=600, c=INK)
    g.line(x3, yy + 6, x3 + 106, yy + 6, INK, 1)
    yy += 60
    g.t(x3, yy, "Etterspørselen studentene ikke ser", 24 - 4, "s", 600)
    gx, gy, gw, gh = x3, yy + 18, 412, 92
    dem = S["demand"]
    X = lambda i: gx + i * gw / 35
    Y = lambda v: gy + gh - v / 10 * gh
    g.line(gx, Y(0), gx + gw, Y(0), AXIS, 1)
    d = f"M{X(0):.1f},{Y(dem[0]):.1f}"
    for i in range(1, 36):
        d += f" L{X(i):.1f},{Y(dem[i - 1]):.1f} L{X(i):.1f},{Y(dem[i]):.1f}"
    g.path(d, INK, 2.4)
    g.t(X(0), Y(4) - 6, "4", 14, "s", 600)
    g.t(X(6), Y(8) - 6, "8 fra uke 5", 14, "s", 600)
    g.t(gx, Y(0) + 17, "Uke 1", 13, c=MUTED)
    g.t(gx + gw, Y(0) + 17, "Uke 36", 13, c=MUTED, a="end")
    # Fordeling
    top = 650
    g.line(48, top - 18, 1392, top - 18, GRIDM, 1)
    g.t(48, top + 18, "Fordeling: 240 studenter i 60 spill à 4", 28, "s", 600)
    g.t(48, top + 44, "Tilfeldig trukket. Hver rute er ett spill med Detaljist, Grossist, Distributør og Fabrikk.", 16, c=MUTED)
    g.button(1000, top - 2, 180, 46, "Kjør på nytt", False, 16)
    g.button(1192, top - 2, 200, 46, "Bekreft fordeling", True, 16)
    names = ["Ida", "Sara", "Mikkel", "Jonas"]
    filler = ["Aksel", "Tuva", "Noah", "Emma", "Oskar", "Nora", "Liam", "Maja", "Emil", "Ella", "Jakob", "Sofie", "Theo", "Mari", "Olav", "Vilde", "Sander", "Eva", "Filip", "Thea"]
    cw, ch = 1344 / 15, 78
    for i in range(60):
        cx = 48 + (i % 15) * cw
        cy = top + 66 + (i // 15) * ch
        g.rect(cx, cy, cw - 6, ch - 6, fill=WHITE, stroke=GRIDM, sw=0.8, rx=3)
        g.t(cx + 6, cy + 15, str(i + 1), 12.5, "s", 700)
        for j in range(4):
            if i + 1 == 17:
                nm = names[j]
            else:
                nm = filler[(i * 4 + j * 7 + i // 3) % len(filler)]
            g.t(cx + 6, cy + 27 + j * 12, nm, 11.5, c=MUTED if i + 1 != 17 else TEXT, w=700 if i + 1 == 17 else 400)
    g.t(48, top + 66 + 4 * ch + 16, "Ingen KI-seter trengs ved start: 240 går opp i fire. Demodata.", 14, c=MUTED)
    g.save()


# ---------- 04 student ----------

def page_04():
    g = Svg("04-student-hjem", 1000, 900, "Fase: registrering og hjem for student",
            "To telefoner: registrering fra Invitasjon, og hjem under spill med faseplan, seter, seks steg, neste frist og Labtimer.")
    sc = 0.94
    g.t(40, 40, "Student på mobil", 26, "s", 600)
    g.t(960, 40, "Demodata", 14, c=MUTED, a="end")
    phone(g, 60, 58, sc)
    g.t(20, 60, "Fase", 24, "s", 600)
    g.t(20, 118, "Velkommen til", 16, c=MUTED)
    g.t(20, 150, "class-of-1994, IBE160", 26, "s", 600)
    g.para(20, 186, "Bård har invitert deg. Lag en konto, så får du Sete i et Klassespill når øvelsen starter.", 350, 16, 23)
    field(g, 20, 268, 350, "Navn", "Sara Nilsen")
    field(g, 20, 348, 350, "E-post fra Klasselisten", "sara.nilsen@student.example")
    field(g, 20, 428, 350, "Velg passord", "•••••••••••")
    g.t(20, 502, "Minst 10 tegn.", 13.5, c=MUTED)
    g.button(20, 526, 350, 56, "Opprett konto", True, 18)
    g.t(20, 620, "Slik går øvelsen", 18, "s", 600)
    yy = g.para(20, 646, "Du driver ett ledd i en kjede og tar én beslutning hver Uke. Spillet går over flere dager, på din egen telefon.", 350, 15.5, 22)
    g.t(20, yy + 10, "Starter ti. 24. nov 2026.", 15.5, w=600)
    g.t(20, yy + 34, "Har du konto? Logg inn", 15.5, w=600, c=INK)
    g.end()
    # Hjem
    phone(g, 545, 58, sc)
    g.t(20, 52, "Spill 17, Grossist", 25, "s", 600)
    g.t(20, 74, "Sara", 14, c=MUTED)
    g.rect(20, 90, 350, 80, fill=INK, rx=7)
    g.t(36, 122, "Spillet venter på deg", 20, "s", 600, c=WHITE)
    g.t(36, 147, "Uke 11. Jonas venter også, 3 min.", 14.5, c="#DCE5F0")
    # plan
    p = Plane(g, 20, 184, 3.5, R11[0], R11[1])
    p.grid(fine=None, major=10, labels=False, side_labels=False)
    p.diag(m(11)["pos"], AXIS, 1)
    p.bane(points(G, 11), fade=14, wmax=2.2, r=1.4)
    p.now(points(G, 11)[-1], r=4.5)
    tx = 20 + p.w + 14
    g.t(tx, 204, "Posisjon 3", 18, "s", 600)
    g.t(tx, 226, "Lager 0", 14.5)
    g.t(tx, 246, "Restordre 13", 14.5)
    g.t(tx, 266, "På vei 16", 14.5)
    g.t(tx, 296, "Åpne Uke 11", 15, w=600, c=INK)
    g.line(tx, 300, tx + 80, 300, INK, 1)
    # seter
    yy = 392
    g.t(20, yy, "Setene", 17, "s", 600)
    yy += 24
    for r in ROLES:
        n = NAMES[r]
        g.t(20, yy, r, 14.5, w=700 if r == "Grossist" else 400)
        g.t(130, yy, "Du" if r == "Grossist" else n, 14.5, w=700 if r == "Grossist" else 400)
        st = {"Detaljist": "har bestilt", "Grossist": "venter på deg", "Distributør": "har bestilt", "Fabrikk": "venter, 3 min"}[r]
        g.t(370, yy, st, 14.5, c=MUTED, a="end")
        yy += 22
    yy += 16
    g.t(20, yy, "Dine seks steg", 17, "s", 600)
    yy += 24
    steps_ = [("Klassespill", "Uke 11, pågår", True), ("Debrief", "åpner når spillet er ferdig", False), ("Quiz", "etter Debrief", False), ("Replay", "etter Quiz", False), ("Individuell test", "Testfrist fr. 18. des", False), ("Rapport", "PDF når alt er levert", False)]
    for i, (a, b, on) in enumerate(steps_):
        g.circ(26, yy - 5, 5, fill=INK if on else "none", stroke=INK if on else AXIS, sw=1.2)
        if i < 5:
            g.line(26, yy + 1, 26, yy + 17, AXIS, 1)
        g.t(40, yy, a, 14.5, w=700 if on else 400)
        g.t(370, yy, b, 13.5, c=MUTED, a="end")
        yy += 23
    yy += 16
    g.t(20, yy, "Neste frist", 13.5, c=MUTED)
    g.t(20, yy + 21, "Spillfrist ti. 8. des", 15.5, w=600)
    g.t(200, yy, "Neste Labtime", 13.5, c=MUTED)
    g.t(200, yy + 21, "to. 26. nov 14:15", 15.5, w=600)
    g.t(200, yy + 41, "Datalab A2", 14, c=MUTED)
    g.end()
    g.save()


# ---------- 09 alle sider ----------

def mini_lines(g, x, y, w, n=3, gap=12, c=GRIDM):
    for i in range(n):
        g.rect(x, y + i * gap, w * (1 - 0.14 * (i % 3)), 5, fill=c, rx=1)


def mini_plane(g, x, y, k, pts_, xr=(-45, 35), yr=(0, 95), diag=None, fade=None, now=True):
    p = Plane(g, x, y, k, xr, yr)
    p.grid(fine=None, major=20, labels=False, side_labels=False)
    if diag is not None:
        p.diag(diag, AXIS, 0.8)
    p.bane(pts_, fade=fade, wmin=0.7, wmax=1.7, dots=False)
    if now:
        p.now(pts_[-1], r=2.8, ring=WHITE)
    return p


def thumb(g, kind, x, y, w, h):
    g.rect(x, y, w, h, fill=WHITE, stroke=GRIDM, sw=1, rx=5)
    mx = x + 12
    my = y + 12
    iw = w - 24
    if kind == "reg":
        for i in range(3):
            g.rect(mx, my + i * 34, iw * 0.7, 24, fill="none", stroke=AXIS, sw=0.8, rx=3)
        g.rect(mx, my + 110, iw * 0.7, 26, fill=INK, rx=3)
    elif kind == "login":
        for i in range(2):
            g.rect(mx + iw * 0.15, my + 20 + i * 34, iw * 0.7, 24, fill="none", stroke=AXIS, sw=0.8, rx=3)
        g.rect(mx + iw * 0.15, my + 92, iw * 0.7, 26, fill=INK, rx=3)
    elif kind == "regler":
        mini_lines(g, mx, my, iw * 0.45, 6, 14)
        q = Plane(g, mx + iw * 0.52, my + 6, 1.9, (-20, 40), (0, 60))
        q.grid(fine=None, major=20, labels=False, side_labels=False)
        q.diag(24, AXIS, 0.9)
        q.now((12, 12), r=3, ring=WHITE)
    elif kind == "start":
        q = Plane(g, mx, my, 2.4, (-20, 40), (0, 50))
        q.grid(fine=None, major=20, labels=False, side_labels=False)
        q.diag(24, AXIS, 0.9)
        arrow(g, q.X(12), q.Y(12), q.X(12), q.Y(16), WARM, 1.6, 4)
        q.now((12, 12), r=3, ring=WHITE)
        g.rect(mx + 156, my + 40, 66, 26, fill=INK, rx=3)
    elif kind == "replay":
        rs = REPLAY["serier"]["Grossist"]
        q = mini_plane(g, mx, my, 1.55, points(rs, 20), diag=None, fade=14)
        for c in range(-20, 95, 20):
            q.diag(c, GRIDM, 0.6)
        q.bane(points(G), color="#CDD8E5", wmin=0.8, wmax=0.8, dots=False)
        q.bane(points(rs, 20), fade=14, wmin=0.7, wmax=1.7, dots=False)
        g.rect(mx + 140, my + 104, 76, 24, fill=INK, rx=3)
    elif kind == "replay2":
        q = Plane(g, mx, my, 1.55, (-45, 35), (0, 95))
        q.grid(fine=None, major=20, labels=False, side_labels=False)
        q.bane(points(G), color="#CDD8E5", wmin=1, wmax=1, dots=False)
        q.bane(points(REPLAY["serier"]["Grossist"]), wmin=0.7, wmax=1.7, dots=False)
        mini_lines(g, mx + 140, my + 10, 80, 5, 14)
    elif kind == "test":
        mini_lines(g, mx, my, iw * 0.9, 2, 11)
        q = Plane(g, mx, my + 30, 1.1, (-45, 35), (0, 95) if False else (0, 70))
        q.grid(fine=None, major=20, labels=False, side_labels=False)
        q.now((-13, 16), r=3, ring=WHITE)
        q.diag(3, WARM, 1)
        g.rect(mx + 104, my + 34, 118, 66, fill="none", stroke=AXIS, sw=0.8, rx=3)
        mini_lines(g, mx + 112, my + 44, 100, 3, 14)
    elif kind == "ki":
        mini_lines(g, mx, my + 20, iw, 5, 13)
        g.rect(mx, my, 118, 14, fill=KEY, rx=2)
    elif kind == "pdf":
        g.rect(mx + 40, my, iw - 80, h - 24, fill="none", stroke=AXIS, sw=0.8)
        mini_plane(g, mx + 62, my + 8, 0.9, points(G), now=False)
        mini_lines(g, mx + 50, my + 100, iw - 100, 3, 9)
    elif kind == "alle":
        i = 0
        kk = 34 / max(CLASS_XR[1] - CLASS_XR[0], CLASS_YR[1] - CLASS_YR[0])
        for row in range(3):
            for col in range(6):
                s = KL["spill"][i]
                q = Plane(g, mx + col * 41, my + row * 44, kk, CLASS_XR, CLASS_YR)
                g.rect(q.x, q.y, q.w, q.h, fill=SCREEN, stroke=GRIDM, sw=0.5)
                q.bane(CLASS_PTS[s["spill"]], wmin=0.5, wmax=1, dots=False)
                i += 1
    elif kind == "hjem":
        for i in range(3):
            g.rect(mx, my + i * 44, iw, 36, fill=SCREEN, stroke=GRIDM, sw=0.8, rx=3)
            mini_lines(g, mx + 8, my + 8 + i * 44, iw * 0.5, 2, 10)
    elif kind == "rapport":
        kk = 0.82
        for i, r in enumerate(ROLES):
            q = Plane(g, mx + i * 59, my + 4, kk * 0.72, (-70, 60), (0, 120))
            q.grid(fine=None, major=40, labels=False, side_labels=False)
            q.bane(points(S[r]), wmin=0.5, wmax=1.2, dots=False)
        mini_lines(g, mx, my + 80, iw, 4, 12)
    elif kind == "innsikt":
        mini_plane(g, mx, my, 1.55, points(G, 22), fade=14)
        strip(g, mx + 134, my + 30, 90, 40, G, 22, labels=False, yr=(-45, 95))
        mini_lines(g, mx + 134, my + 90, 90, 3, 11)
    elif kind == "studentside":
        mini_lines(g, mx, my, 100, 6, 14)
        mini_plane(g, mx + 110, my, 1.3, points(G), now=False)
    elif kind == "plenum":
        i = 0
        kk = 25 / max(CLASS_XR[1] - CLASS_XR[0], CLASS_YR[1] - CLASS_YR[0])
        g.rect(x + 1, y + 1, w - 2, h - 2, fill=TEXT, rx=4)
        for row in range(4):
            for col in range(9):
                s = KL["spill"][i]
                q = Plane(g, mx + col * 28.5, my + row * 33, kk, CLASS_XR, CLASS_YR)
                g.rect(q.x, q.y, q.w, q.h, fill=SCREEN)
                q.bane(CLASS_PTS[s["spill"]], wmin=0.4, wmax=0.8, dots=False)
                i += 1
    elif kind == "tverr":
        fq = KL["ferdige"]["kjedekost"]
        fy = KL["fjoraaret"]["median_kjedekost"]
        X = lambda v: mx + v / 3600 * iw
        g.line(mx, my + 40, mx + iw, my + 40, GRIDM, 1)
        g.rect(X(fq["q1"]), my + 26, X(fq["q3"]) - X(fq["q1"]), 28, fill=KEY)
        g.line(X(fq["median"]), my + 22, X(fq["median"]), my + 58, INK, 2)
        g.line(X(fy), my + 22, X(fy), my + 58, MUTED, 1.4, "3 2")
        mini_lines(g, mx, my + 80, iw, 3, 12)
    elif kind == "melding":
        for i in range(4):
            g.rect(mx, my + i * 30, iw, 22, fill=SCREEN, stroke=GRIDM, sw=0.8, rx=3)
        g.rect(mx + iw - 60, my + 124, 60, 18, fill=INK, rx=3)
    elif kind == "testspill":
        p = mini_plane(g, mx, my, 1.55, points(G, 16), fade=14)
        g.rect(mx + 140, my + 30, 76, 24, fill=INK, rx=3)
        mini_lines(g, mx + 140, my + 70, 76, 3, 12)
    elif kind == "laererhjem":
        for i in range(2):
            g.rect(mx, my + i * 56, iw, 46, fill=SCREEN, stroke=GRIDM, sw=0.8, rx=3)
            mini_lines(g, mx + 10, my + 12 + i * 56, 110, 2, 12)
    elif kind == "table":
        for i in range(7):
            g.line(mx, my + i * 19, mx + iw, my + i * 19, GRIDM, 0.8)
            mini_lines(g, mx, my + 6 + i * 19, 60, 1)
            g.rect(mx + 90, my + 6 + i * 19, 40, 5, fill=GRIDM, rx=1)
    elif kind == "kost":
        vals = [c for c in S["Fabrikk"]["kost_sum"]]
        X = lambda i: mx + i * iw / 35
        Y = lambda v: my + 120 - v / 700 * 110
        g.line(mx, my + 120, mx + iw, my + 120, AXIS, 0.8)
        g.path("M" + " L".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals)), INK, 1.5)


def page_09():
    g = Svg("09-alle-sider", 2000, 1400, "Fase: alle andre sider", "Kontaktark over øvrige sider gruppert per rolle, med tittel og én linje.")
    g.t(40, 52, "Alle andre sider", 34, "s", 600)
    g.t(1960, 52, "Demodata", 15, c=MUTED, a="end")
    groups = [
        ("Student", 94, [
            ("reg", "Invitasjon og registrering", "Lenken fra e-post, konto på under ett minutt."),
            ("login", "Logg inn", "E-post og passord. Ingen offentlig registrering."),
            ("regler", "Regler før første ordre", "Ett plan, ett poeng om gangen, under ett minutt."),
            ("start", "Startoppgave", "Tast en ordre og se punktet gå opp. Teller ikke."),
            ("replay", "Replay", "Alle Posisjoner, kjent Levering og Klassespillet som grå bane."),
            ("replay2", "Replay-gjennomgang", "To baner i samme plan, merket ikke like for like."),
            ("test", "Individuell test", "Flervalg, tegn banen, tabelloppgave og langsvar."),
            ("ki", "KI-vurdering", "Teller ikke, er ikke en karakter, og sier det øverst."),
            ("pdf", "Studentrapport (PDF)", "Din bane, dine tall og din Forklaring, klar til arkiv."),
            ("alle", "Alle spill side om side", "Klassens baner etter Debrief, uten navn."),
        ]),
        ("Faglærer", 604, [
            ("laererhjem", "Lærerhjem", "Klassene dine og hva som krever noe nå."),
            ("rapport", "Klasserapport", "Fire plan, kvartiler og mønstre for hele Klassen."),
            ("innsikt", "Spillinnsikt", "Uke for uke: spol banen, se tallene i samme øyeblikk."),
            ("studentside", "Studentside", "Én students bane, Forklaring, test og frister."),
            ("plenum", "Alle spill i plenum", "60 plan på prosjektor, mørkt rom, uten navn."),
            ("tverr", "Tverrklasse-statistikk", "Median mot fjorårets Klasse, samme mål."),
            ("melding", "Meldinger", "Send Melding til ett spill, en gruppe eller alle."),
            ("testspill", "Lærers testspill", "Spill selv mot tre KI-spillere før øvelsen."),
        ]),
        ("Admin", 1114, [
            ("table", "Admin-område", "Institusjoner, Klasser og drift."),
            ("table", "Brukere og roller", "Hvem er Faglærer, assistent eller admin."),
            ("kost", "KI-kostnad", "Løpende forbruk per Klasse, med tak."),
        ]),
    ]
    W, H = 305, 158
    colx = [40 + i * (W + 18.0) for i in range(6)]
    for title, y0, items in groups:
        g.t(40, y0, title, 22, "s", 600)
        g.line(40, y0 + 9, 1960, y0 + 9, AXIS, 1)
        for i, (kind, a, b) in enumerate(items):
            if title == "Admin":
                x = colx[i]
                y = y0 + 22
            else:
                x = colx[i % 6]
                y = y0 + 22 + (i // 6) * (H + 80)
            thumb(g, kind, x, y, W, H)
            g.t(x, y + H + 22, a, 16.5, "s", 600)
            g.para(x, y + H + 41, b, W - 6, 13, 17, c=MUTED)
    g.save()


# ---------- concept ----------

def concept():
    areas = {r: abs(shoelace(points(S[r]))) for r in ROLES}
    ref_areas = {r: abs(shoelace(points(ALLE["serier"][r]))) for r in ROLES}
    txt = f"""# 03 Faseplanet (arbeidsnavn Fase)
**Tese (én setning):** Hver Uke er ett punkt i et plan med netto lager vannrett og På vei loddrett, så tiden blir en bane der overreaksjon tegner sløyfer og Posisjon er en diagonal du enten følger eller krysser.

**Faglig kjerne:** P3 (diagonalen er Posisjon: netto {nf(m(11)['net'])} og {m(11)['pv']} på vei gir 3, ikke {nf(m(11)['net'])}), P5 (fire plan side om side i samme skala) og P7 (pilen rett opp, og sløyfene som følger). Tre-bevegelses-grafen lærer P1: Ordre flytter punktet opp, Levering langs diagonalen, Innkommende ordre mot venstre. Regnestykket er eksakt og sjekkes mot alle 36 uker i `build.py`. Levering endrer aldri Posisjon, og det er konseptets viktigste setning. P2 vises som avstanden mellom pilen og Leveringen som kommer langs diagonalen uker senere. P4 og P6 ligger i Debriefen: etterspørselshoppet i samme skala, og at Fabrikk går med klokka i {CW} av {len(FIN)} ferdige spill. P8: venstre for null koster dobbelt så mye per enhet som høyre.

**Spilldynamikk:** Uka åpner med at punktet har flyttet seg, og forrige ukes tre bevegelser kan leses. Studenten taster ett tall, og hvert siffer strekker pilen rett opp til en ny diagonal med tallet for Posisjon påskrevet. Etter bekreftelsen ser studenten hvem Uka venter på. Neste Uke spilles de tre bevegelsene av på under 2 sekunder, og kan hoppes over. Banen viser om punktet beveger seg over diagonalene eller langs dem, uten å si hva som er riktig. Hele banen finnes som tabell bak Alle tall.

**Hjelpegrad:** Standpunkt: Klassespillet viser planet, banen, nå-punktet, én diagonal gjennom nå, regnestykket og forrige ukes tre bevegelser. Det tegner ikke rutenett av Posisjoner, kjente ankomster eller referanser i planet, og forteller ikke hva en stor Posisjon betyr. Neste levering står bare som tall bak Alle tall. Replay låser opp alle diagonalene, neste kjente Levering tegnet i planet (merket ikke garantert), tre bevegelser for hvilken som helst uke, og Klassespillet som grå bane, merket ikke like for like. Begrunnelse: Regnestykket er en sannhet studenten har krav på, og Sterman-funnet er nettopp at folk overser det som står foran dem. Hvor mye det demper svingningene vet vi ikke, så issue #22 må testes: kjør en pilot der halve Klassen spiller uten diagonalen, og sammenlign forsterkning. Forskjellen er tegnet i `10-pedagogikk.svg`.

**Gradvis innføring:** Banen er ett punkt de første seks ukene, så planet kan bygges i de Veiledede ukene: Uke 1 tallinje, Uke 2 På vei som høyde, Uke 3 diagonalen, Uke 4 pilen. Det er konseptets svar på at et faseplan er nytt for de fleste.

**Debrief-grep:** Fire faseplan i samme skala på delt skjerm, med simulert referanse inni hver bane og hele etterspørselshoppet tegnet som en strek på fire enheter ved siden av.

**Lærerflate-grep:** 60 små faseplan i rutenett med status under og tabell ved siden av, så læreren ser form, ikke bare tall, og klikker seg inn fra formen. På vei er regnet ut av Ordre og netto lager, kontrollert mot spill 17.

**Palett:** Skjermark `#F6F8FB`, blågrå flate `#E8EDF3`, ruter `#E3E9F0` og `#D3DCE6`, akse `#8494A8`, blekkblå bane `#14356F` som blekner til `#B3C1D3`, tekst `#16233B`, sekundærtekst `#4A5A72`, nå `#C9481A`, simulert `#0E7C76`. Palettvalidatoren passerer CVD (ΔE 12,1), normalt syn og kontrast. Den feiler på lyshetsbånd for blekket og kroma for grønn: blekket er bevisst mørk ende av en alders-rampe, og den grønne holdes dempet for å være lesbar som tekst. Begge er alltid direkte merket. **Typografi:** STIX Two Text til tall og titler, Karla til etiketter og brødtekst.

**Styrke:** Ett bilde samler lager, restordre, forsinkelse og Posisjon uten bokser, og Debrief-bildet er noe en systemdynamiker vil henge opp. Grafen er sann på en måte som lar seg regne etter: {nf(m(11)['net'])} + 4 − 11 = {nf(m(12)['net'])}.

**Ærlig risiko:** Faseplan er uvant, og en student på telefon om kvelden kan velge å bare lese tallene. Tidsserien under er sikkerhetsnettet, men planet må brukertestes med ekte studenter før det velges. Sløyfeflaten vokser ikke strengt oppover kjeden: {nf(areas['Detaljist'])}, {nf(areas['Grossist'])}, {nf(areas['Distributør'])}, {nf(areas['Fabrikk'])} enheter². Fabrikk er bredest, Distributør størst, så bildet må leses sammen med forsterkningen 1,8× til 7,6×, som er målt på ordre. Referansen krymper heller ikke helt til ett punkt innen Uke 36: flatene er {nf(ref_areas['Detaljist'])}, {nf(ref_areas['Grossist'])}, {nf(ref_areas['Distributør'])}, {nf(ref_areas['Fabrikk'])}, og banen er på vei inn, ikke framme. Vi sier «mindre sløyfe», ikke «likevekt». Under spillet kjenner ingen likevekten, så den tegnes aldri.

**Gjenbrukbart selv om konseptet velges bort:** Tre-bevegelses-regelen: vis Ordre, Levering og Innkommende ordre som tre flytt med et regnestykke som går opp, og pilen som vokser mens studenten taster.
"""
    (HERE / "concept.md").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    print("Klasse-skala", CLASS_XR, CLASS_YR, "med klokka", CW, "av", len(FIN))
    page_10()
    page_05()
    page_06()
    page_07()
    page_08()
    page_01()
    page_02()
    page_03()
    page_04()
    page_09()
    concept()
