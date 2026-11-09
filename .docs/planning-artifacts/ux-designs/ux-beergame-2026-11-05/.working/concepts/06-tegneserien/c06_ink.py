"""Blekk-biblioteket for konsept 06 Tegneserien: strek, raster, figurer, biler, bobler, ruter.

Alt er tegnet her, med deterministisk håndskjelving. Tall kommer fra ../_shared/fixture.json.
"""
import json
import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAMES = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

INK = "#15120E"
SOFT = "#4A453D"      # dempet blekk, 9:1 på papir
PAPER = "#FFFBEF"
WHITE = "#FFFFFF"
YEL = "#FFD60A"
MAG = "#D6006F"
CYA = "#00A9E6"
ROLE_FILL = {"Detaljist": YEL, "Grossist": CYA, "Distributør": MAG, "Fabrikk": PAPER}

FONT_IMPORT = "https://fonts.googleapis.com/css2?family=Bangers&amp;family=Bowlby+One+SC&amp;family=Patrick+Hand&amp;display=swap"
CLS = {"h": "c06-h", "hb": "c06-hb", "d": "c06-d", "s": "c06-s"}
WF = {"h": 0.45, "hb": 0.47, "d": 0.76, "s": 0.47}

R = random.Random(6)
SIDE = {"name": "x"}


def seed(name, n=6):
    SIDE["name"] = name
    R.seed(f"{name}{n}")


def pid(key):
    return f"c06-{SIDE['name']}-{key}"


def dots(key):
    return f"url(#{pid(key)})"


def _pattern(key, color, step, r, rot):
    return (f'<pattern id="{pid(key)}" width="{step}" height="{step}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate({rot})"><circle cx="{step/2}" cy="{step/2}" r="{r}" fill="{color}"/></pattern>')


def defs(extra=""):
    return ("<defs>" + _pattern("dy", YEL, 7, 2.5, 28) + _pattern("dm", MAG, 7, 1.9, 28) + _pattern("dc", CYA, 7, 2.3, 58)
            + _pattern("dk", INK, 6, 1.05, 18) + _pattern("dM", MAG, 11, 3.6, 28) + _pattern("dC", CYA, 12, 4.2, 58)
            + _pattern("dW", WHITE, 7, 1.7, 28) + extra + "</defs>")


STYLE = f"""<style>@import url('{FONT_IMPORT}');
.c06-h{{font-family:'Patrick Hand','Segoe Print','Comic Sans MS',cursive}}
.c06-hb{{font-family:'Patrick Hand','Segoe Print','Comic Sans MS',cursive;stroke:currentColor;stroke-width:.35px}}
.c06-d{{font-family:'Bowlby One SC','Arial Black',sans-serif}}
.c06-s{{font-family:'Bangers','Bowlby One SC',Impact,sans-serif;letter-spacing:.03em}}
</style>"""


class Page:
    def __init__(self, file, side, W, H, title, desc, bg=PAPER):
        seed(side)
        self.file, self.W, self.H, self.title, self.desc = file, W, H, title, desc
        self.parts = [f'<rect width="{W}" height="{H}" fill="{bg}"/>']

    def add(self, *parts):
        self.parts.extend(parts)

    def save(self, extra_defs=""):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" '
               f'font-family="\'Patrick Hand\',\'Segoe Print\',\'Comic Sans MS\',cursive">'
               f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>{STYLE}{defs(extra_defs)}"
               + "".join(self.parts) + "</svg>")
        (HERE / self.file).write_text(svg, encoding="utf-8")


# ---- tall og tekst -------------------------------------------------------------------------
def nok(v, dec=2):
    s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s + " kr"


def tw(s, size, f="h"):
    return len(s) * size * WF[f]


def T(x, y, s, size=15, f="h", c=INK, a="start", rot=None, extra=""):
    tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
    an = f' text-anchor="{a}"' if a != "start" else ""
    col = f' style="color:{c}"' if f == "hb" else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{CLS[f]}" font-size="{size}" fill="{c}"{an}{tr}{col}{extra}>{escape(str(s))}</text>'


def wrap(s, maxw, size, f="h"):
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if tw(trial, size, f) > maxw and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def Pg(x, y, s, maxw, size=15, f="h", c=INK, lh=1.22, a="start"):
    return "".join(T(x, y + i * size * lh, ln, size, f, c, a) for i, ln in enumerate(wrap(s, maxw, size, f)))


def nl(s, maxw, size, f="h"):
    return len(wrap(s, maxw, size, f))


def g(tr, *kids, extra=""):
    return f'<g transform="{tr}"{extra}>' + "".join(kids) + "</g>"


def sfx(x, y, s, size=26, rot=-6, c=MAG, a="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="c06-s" font-size="{size}" fill="{c}" text-anchor="{a}" '
            f'stroke="{PAPER}" stroke-width="3.2" paint-order="stroke" transform="rotate({rot} {x:.1f} {y:.1f})">{escape(s)}</text>')


# ---- blekkstrek -----------------------------------------------------------------------------
def iline(x1, y1, x2, y2, sw=2.4, c=INK, j=1.0, dash=None):
    mx, my = (x1 + x2) / 2 + R.uniform(-j, j), (y1 + y2) / 2 + R.uniform(-j, j)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="M{x1:.1f} {y1:.1f}Q{mx:.1f} {my:.1f} {x2:.1f} {y2:.1f}" fill="none" stroke="{c}" '
            f'stroke-width="{sw}" stroke-linecap="round"{da}/>')


def ipoly(pts, flat=None, dot=None, sw=3, over=2.5, mis=(2, 2), j=1.0, c=INK, dash=None):
    out = []
    n = len(pts)
    if flat:
        d = "M" + "L".join(f"{p[0]+mis[0]:.1f} {p[1]+mis[1]:.1f}" for p in pts) + "Z"
        out.append(f'<path d="{d}" fill="{flat}"/>')
    if dot:
        d = "M" + "L".join(f"{p[0]:.1f} {p[1]:.1f}" for p in pts) + "Z"
        out.append(f'<path d="{d}" fill="{dots(dot)}"/>')
    if sw:
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            L = max(math.hypot(b[0] - a[0], b[1] - a[1]), 1)
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            ov = over if not dash else 0
            out.append(iline(a[0] - ux * ov, a[1] - uy * ov, b[0] + ux * ov, b[1] + uy * ov, sw, c, j, dash))
    return "".join(out)


def ibox(x, y, w, h, flat=None, dot=None, sw=3, over=2.5, mis=(2, 2), j=1.0, c=INK, dash=None):
    return ipoly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], flat, dot, sw, over, mis, j, c, dash)


def plain(x, y, w, h, flat=WHITE, sw=2, j=.6, over=1, dash=None):
    return ibox(x, y, w, h, flat, None, sw, over, (0, 0), j, dash=dash)


def rr(x, y, w, h, r, fill="none", stroke=INK, sw=2.4, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>'


def circ(x, y, r, fill="none", stroke=INK, sw=2.4):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def path(d, fill="none", stroke=INK, sw=2.4, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{extra}/>'


# ---- ikoner, alle tegnet -----------------------------------------------------------------------
def ic_check(x, y, s=1, c=INK):
    return path(f"M{x-6*s:.1f} {y:.1f}L{x-1.5*s:.1f} {y+5*s:.1f}L{x+7*s:.1f} {y-6*s:.1f}", sw=2.6 * s, stroke=c)


def ic_x(x, y, s=1, c=INK):
    return path(f"M{x-5*s:.1f} {y-5*s:.1f}L{x+5*s:.1f} {y+5*s:.1f}M{x+5*s:.1f} {y-5*s:.1f}L{x-5*s:.1f} {y+5*s:.1f}", sw=2.8 * s, stroke=c)


def ic_hour(x, y, s=1, c=INK):
    return path(f"M{x-5*s:.1f} {y-7*s:.1f}H{x+5*s:.1f}L{x-5*s:.1f} {y+7*s:.1f}H{x+5*s:.1f}Z", sw=2 * s, stroke=c)


def ic_clock(x, y, s=1, c=INK, f="none"):
    return circ(x, y, 7 * s, f, c, 2 * s) + path(f"M{x:.1f} {y-4.5*s:.1f}V{y:.1f}L{x+3.5*s:.1f} {y+2*s:.1f}", stroke=c, sw=1.8 * s)


def ic_pause(x, y, s=1, c=INK):
    return (f'<rect x="{x-5.5*s:.1f}" y="{y-6.5*s:.1f}" width="{4*s:.1f}" height="{13*s:.1f}" fill="{c}"/>'
            f'<rect x="{x+1.5*s:.1f}" y="{y-6.5*s:.1f}" width="{4*s:.1f}" height="{13*s:.1f}" fill="{c}"/>')


def ic_lock(x, y, s=1, c=INK, body=YEL):
    return (path(f"M{x-9*s:.1f} {y:.1f}V{y-8*s:.1f}A{9*s:.1f} {9*s:.1f} 0 0 1 {x+9*s:.1f} {y-8*s:.1f}V{y:.1f}", stroke=c, sw=3.4 * s)
            + rr(x - 14 * s, y - 1 * s, 28 * s, 22 * s, 3 * s, body, c, 2.6 * s) + circ(x, y + 9 * s, 2.6 * s, c, c, 1))


def ic_mail(x, y, s=1, c=INK, f=WHITE):
    return (rr(x - 9 * s, y - 6.5 * s, 18 * s, 13 * s, 1.5, f, c, 1.8 * s)
            + path(f"M{x-9*s:.1f} {y-6*s:.1f}L{x:.1f} {y+1*s:.1f}L{x+9*s:.1f} {y-6*s:.1f}", stroke=c, sw=1.6 * s))


def ic_back(x, y, s=1, c=INK):
    return path(f"M{x-13*s:.1f} {y:.1f}L{x-6*s:.1f} {y-8*s:.1f}H{x+12*s:.1f}V{y+8*s:.1f}H{x-6*s:.1f}Z"
                f"M{x-1*s:.1f} {y-3.5*s:.1f}L{x+6*s:.1f} {y+3.5*s:.1f}M{x+6*s:.1f} {y-3.5*s:.1f}L{x-1*s:.1f} {y+3.5*s:.1f}", sw=2 * s, stroke=c)


def ic_page(x, y, s=1, c=INK, f=WHITE):
    return (path(f"M{x-7*s:.1f} {y-9*s:.1f}H{x+3*s:.1f}L{x+7*s:.1f} {y-5*s:.1f}V{y+9*s:.1f}H{x-7*s:.1f}Z", fill=f, stroke=c, sw=2 * s)
            + path(f"M{x+3*s:.1f} {y-9*s:.1f}V{y-5*s:.1f}H{x+7*s:.1f}", stroke=c, sw=1.6 * s))


def arrow(x1, y1, x2, y2, sw=2.6, c=INK, bend=14, head=10):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    L = max(math.hypot(dx, dy), 1)
    cx, cy = mx - dy / L * bend, my + dx / L * bend
    a = math.atan2(y2 - cy, x2 - cx)
    p1 = (x2 - head * math.cos(a - .45), y2 - head * math.sin(a - .45))
    p2 = (x2 - head * math.cos(a + .45), y2 - head * math.sin(a + .45))
    return (path(f"M{x1:.1f} {y1:.1f}Q{cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}", stroke=c, sw=sw)
            + path(f"M{p1[0]:.1f} {p1[1]:.1f}L{x2:.1f} {y2:.1f}L{p2[0]:.1f} {p2[1]:.1f}", stroke=c, sw=sw))


# ---- figurene: fire bygninger, kjønnsnøytrale, få streker --------------------------------------
BODY = {
    "Detaljist": dict(head=-70, sh=(-20, -44), hip=-12, d="M-24 -34A24 24 0 1 1 24 -34A24 24 0 1 1 -24 -34Z", legx=9, ki=-34),
    "Grossist": dict(head=-88, sh=(-22, -68), hip=-20, d="M-22 -74H22V-20H-22Z", legx=11, ki=-47),
    "Distributør": dict(head=-112, sh=(-11, -90), hip=-26, d="M-11 -98H11V-26H-11Z", legx=6, ki=-60),
    "Fabrikk": dict(head=-88, sh=(-30, -70), hip=-22, d="M-32 -74H32L17 -22H-17Z", legx=9, ki=-52),
}
KUNDE = dict(head=-76, sh=(-13, -56), hip=-18, d="M-14 -62C-16 -40 -18 -30 -18 -18H18C18 -30 16 -40 14 -62Z", legx=7, ki=-40)


def face(hy, kind, c=INK):
    e = {"rolig": (-5, 5, 0), "glad": (-5, 5, 0), "tenker": (-3, 7, -1), "bekymret": (-5, 5, 0), "overrasket": (-5, 5, 0)}[kind]
    r = 2.6 if kind == "overrasket" else 1.9
    out = [f'<circle cx="{e[0]}" cy="{hy-2+e[2]}" r="{r}" fill="{c}"/><circle cx="{e[1]}" cy="{hy-2+e[2]}" r="{r}" fill="{c}"/>']
    if kind == "rolig":
        out.append(path(f"M-4 {hy+6}Q0 {hy+8} 4 {hy+6}", stroke=c, sw=1.8))
    elif kind == "glad":
        out.append(path(f"M-6 {hy+4}Q0 {hy+10} 6 {hy+4}", stroke=c, sw=1.8))
    elif kind == "tenker":
        out.append(path(f"M-1 {hy+6}L5 {hy+5}", stroke=c, sw=1.8))
    elif kind == "bekymret":
        out.append(path(f"M-5 {hy+7}Q-2 {hy+3} 0 {hy+6}T5 {hy+6}", stroke=c, sw=1.8))
        out.append(path(f"M-8 {hy-7}L-3 {hy-9}M8 {hy-7}L3 {hy-9}", stroke=c, sw=1.8))
    elif kind == "overrasket":
        out.append(f'<ellipse cx="0" cy="{hy+6}" rx="2.6" ry="3.4" fill="{c}"/>')
    return "".join(out)


def fig(x, y, role, s=1.0, kind="rolig", ki=False, arm="ned", flip=False, mis=True):
    b = KUNDE if role == "Kunde" else BODY[role]
    fill = WHITE if role == "Kunde" else ROLE_FILL[role]
    o = []
    hy = b["head"]
    # bein
    for sgn in (-1, 1):
        lx = sgn * b["legx"]
        o.append(path(f"M{lx} {b['hip']}V-1H{lx + sgn*6}", sw=3))
    # kropp, flate forskjøvet som et trykk som ikke helt treffer
    if mis:
        o.append(f'<path d="{b["d"]}" fill="{fill}" transform="translate(1.6 1.4)"/>')
        o.append(path(b["d"], fill="none", sw=3))
    else:
        o.append(path(b["d"], fill=fill, sw=3))
    if role == "Fabrikk":
        o.append(f'<path d="{b["d"]}" fill="{dots("dk")}"/>')
    # armer
    sx, sy = b["sh"]
    if arm == "ned":
        o.append(path(f"M{sx} {sy}L{sx-9} {sy+26}", sw=3) + path(f"M{-sx} {sy}L{-sx+9} {sy+26}", sw=3))
    elif arm == "opp":
        o.append(path(f"M{sx} {sy}L{sx-9} {sy+26}", sw=3) + path(f"M{-sx} {sy}L{-sx+16} {sy-20}", sw=3))
    elif arm == "tlf":
        o.append(path(f"M{sx} {sy}L{sx-9} {sy+26}", sw=3) + path(f"M{-sx} {sy}L{-sx+11} {sy+4}L15 {hy+4}", sw=3))
        o.append(f'<rect x="12" y="{hy-7}" width="6" height="17" rx="2.5" fill="{INK}"/>')
    elif arm == "bære":
        o.append(path(f"M{sx} {sy}L{sx-6} {sy+22}L{-sx-4} {sy+24}", sw=3) + path(f"M{-sx} {sy}L{-sx+10} {sy+24}", sw=3))
    # hode
    if ki:
        o.append(path(f"M0 {hy-13}V{hy-22}", sw=2.6) + circ(0, hy - 25, 3.4, MAG, INK, 2))
        o.append(rr(-14, hy - 13, 28, 26, 6, WHITE, INK, 3))
        o.append(f'<rect x="-10" y="{hy-7}" width="20" height="8" rx="2" fill="{INK}"/>'
                 f'<circle cx="-5" cy="{hy-3}" r="1.8" fill="{WHITE}"/><circle cx="5" cy="{hy-3}" r="1.8" fill="{WHITE}"/>')
        o.append(path(f"M-6 {hy+7}H6M-3 {hy+5}V{hy+9}M1 {hy+5}V{hy+9}", sw=1.6))
        o.append(f'<rect x="-11" y="{b["ki"]-8}" width="22" height="16" rx="2" fill="{WHITE}" stroke="{INK}" stroke-width="2"/>')
        o.append(T(0, b["ki"] + 4.5, "KI", 12, "d", INK, "middle"))
    else:
        o.append(circ(0, hy, 13, WHITE, INK, 3))
        o.append(face(hy, kind))
    sc = f"scale({'-' if flip else ''}{s} {s})"
    return g(f"translate({x:.1f} {y:.1f}) {sc}", *o)


def mark(x, y, role, r=9, sw=2):
    """Lite rollemerke: formen følger bygningen, slik at Rolle aldri er bare farge."""
    f = ROLE_FILL[role]
    if role == "Detaljist":
        out = circ(x, y, r, f, INK, sw)
    elif role == "Grossist":
        out = f'<rect x="{x-r:.1f}" y="{y-r:.1f}" width="{2*r}" height="{2*r}" fill="{f}" stroke="{INK}" stroke-width="{sw}"/>'
    elif role == "Distributør":
        out = f'<rect x="{x-r*.5:.1f}" y="{y-r*1.15:.1f}" width="{r}" height="{2.3*r:.1f}" fill="{f}" stroke="{INK}" stroke-width="{sw}"/>'
    else:
        d = f"M{x-r*1.2:.1f} {y-r:.1f}H{x+r*1.2:.1f}L{x+r*.6:.1f} {y+r:.1f}H{x-r*.6:.1f}Z"
        out = path(d, fill=f, sw=sw) + f'<path d="{d}" fill="{dots("dk")}"/>'
    return out


def ki_tag(x, y, s=1.0, f=WHITE):
    """Robothode med teksten KI. Kan stå alene i tabeller."""
    return g(f"translate({x:.1f} {y:.1f}) scale({s})",
             path("M-13 -10V-14", sw=2), circ(-13, -16, 2, MAG, INK, 1.4), rr(-21, -10, 16, 16, 3, f, INK, 2),
             f'<rect x="-18.5" y="-6" width="11" height="4.5" rx="1" fill="{INK}"/>', T(-2, 4, "KI", 13, "d", INK))


def kirow(x, y, n, s=1.0):
    return "".join(ki_tag(x + i * 42 * s, y, s) for i in range(n))


# ---- kasser, biler, lager --------------------------------------------------------------------
def crate(x, y, s, num=None, size=None, flat=YEL):
    """x,y nederst til venstre."""
    o = [f'<rect x="{x+1.5:.1f}" y="{y-s+1.5:.1f}" width="{s}" height="{s}" fill="{flat}"/>',
         rr(x, y - s, s, s, 1, "none", INK, max(1.6, s / 26))]
    if num is None:
        o.append(path(f"M{x:.1f} {y:.1f}L{x+s:.1f} {y-s:.1f}", sw=max(1, s / 40)))
    else:
        fs = size or s * .62
        o.append(T(x + s / 2, y - s / 2 + fs * .36, num, fs, "d", INK, "middle"))
    return "".join(o)


VAN_UNIT = 3.5


def van_w(load):
    return 14 + load * VAN_UNIT


def van(x, ground, load, ghost=False, s=1.0):
    """Liten bil som kjører mot venstre. Lasteplanets lengde er antall kasser, til skala."""
    cw = 14
    L = load * VAN_UNIT
    h = 19
    y0 = ground - 4
    if ghost:
        o = [rr(x + cw, y0 - h, L, h, 1, WHITE, INK, 2, "4 3"),
             path(f"M{x+cw} {y0}H{x+3}L{x} {y0-7}V{y0-13}H{x+cw}", WHITE, INK, 2, ' stroke-dasharray="4 3"')]
    else:
        o = [rr(x + cw, y0 - h, L, h, 1, WHITE, INK, 2),
             path(f"M{x+cw} {y0}H{x+1}V{y0-8}L{x+5} {y0-14}H{x+cw}Z", YEL, INK, 2)]
    o.append(circ(x + 6, y0 + 1, 3.2, WHITE if ghost else INK, INK, 1.6))
    o.append(circ(x + cw + L - 6, y0 + 1, 3.2, WHITE if ghost else INK, INK, 1.6))
    fs = 14
    o.append(T(x + cw + L / 2, y0 - 4.5, load, fs, "d", INK, "middle"))
    return g(f"translate(0 0) scale({s})" if s != 1 else "translate(0 0)", *o)


def road(x_right, ground, vans, labels=False, gap=8, ghost=None, x_left=None, roadfrom=None):
    """Biler i ankomstrekkefølge fra venstre (nærmest) til høyre. vans = [(uke, last)]."""
    items = list(vans) + ([ghost] if ghost else [])
    slots = [max(van_w(l), 40 if labels else 0) for _, l in items]
    total = sum(slots) + gap * (len(slots) - 1)
    x = x_left if x_left is not None else x_right - total
    o = [iline(roadfrom if roadfrom is not None else x - 6, ground + 1, x_right + 2, ground + 1, 2, j=.8)]
    for i, (u, l) in enumerate(items):
        is_g = ghost is not None and i == len(items) - 1
        vx = x + (slots[i] - van_w(l)) / 2
        o.append(van(vx, ground, l, ghost=is_g))
        if labels:
            lab = f"Uke {u}?" if is_g else f"Uke {u}"
            o.append(T(x + slots[i] / 2, ground + 15, lab, 13.5, "h", INK, "middle"))
        x += slots[i] + gap
    return "".join(o)


def road_w(vans, labels=False, gap=8, ghost=None):
    items = list(vans) + ([ghost] if ghost else [])
    return sum(max(van_w(l), 40 if labels else 0) for _, l in items) + gap * (len(items) - 1)


def bigvan(x, ground, load, s=1.0):
    """Stor varebil mot venstre med tallet på kassen."""
    o = [path("M42 -8H150V-74H42Z", WHITE, INK, 3),
         path("M42 -8H6V-34L18 -54H42Z", YEL, INK, 3),
         path("M14 -34L22 -48H36V-34Z", CYA, INK, 2),
         path("M54 -74V-8", sw=1.6)]
    o.append(crate(64, -13, 56, str(load), 36 if load < 100 else 26))
    o.append(circ(24, -6, 9, INK, INK, 1) + circ(24, -6, 3.4, WHITE, INK, 1))
    o.append(circ(124, -6, 9, INK, INK, 1) + circ(124, -6, 3.4, WHITE, INK, 1))
    return g(f"translate({x:.1f} {ground:.1f}) scale({s})", *o)


def shelves(x, y, w, h, n):
    """Lagerhylle: n kasser (maks det som får plass). Tom hylle er tom."""
    o = [iline(x, y, x, y + h, 3), iline(x + w, y, x + w, y + h, 3)]
    rows = 3
    for i in range(rows):
        yy = y + (i + 1) * h / rows - 2
        o.append(iline(x - 2, yy, x + w + 2, yy, 2.6))
    cs = min((w - 6) / 4, h / rows - 6)
    placed = 0
    for i in range(rows - 1, -1, -1):
        yy = y + (i + 1) * h / rows - 3
        for k in range(4):
            if placed < n:
                o.append(crate(x + 3 + k * cs, yy, cs - 1))
                placed += 1
    return "".join(o)


def slips(x, y, n, w, per=None):
    """Restordre som lapper på snor: én lapp per enhet, skala bevart."""
    step = 16
    per = per or max(int(w // step), 1)
    o = []
    for r in range(math.ceil(n / per) if n else 1):
        o.append(iline(x, y + r * 8, x + w, y + r * 8 + 2, 1.6, j=1.6))
    for i in range(n):
        r, k = divmod(i, per)
        sx = x + 5 + k * step
        sy = y + r * 8 + 1
        ang = R.uniform(-7, 7)
        o.append(g(f"rotate({ang:.1f} {sx+6:.1f} {sy:.1f})",
                   f'<rect x="{sx:.1f}" y="{sy:.1f}" width="12.5" height="17" fill="{WHITE}" stroke="{INK}" stroke-width="1.6"/>',
                   f'<rect x="{sx+.8:.1f}" y="{sy+.8:.1f}" width="10.9" height="4" fill="{MAG}"/>',
                   f'<path d="M{sx+2.5:.1f} {sy+9:.1f}h7.5M{sx+2.5:.1f} {sy+13:.1f}h7.5" stroke="{INK}" stroke-width="1.2"/>'))
    return "".join(o)


def deskphone(x, y, s=1.0):
    return g(f"translate({x:.1f} {y:.1f}) scale({s})",
             path("M-20 0L-13 -18H13L20 0Z", WHITE, INK, 2.6),
             circ(0, -9, 5, CYA, INK, 2),
             path("M-23 -19C-23 -30 23 -30 23 -19V-15H12V-20C12 -23 -12 -23 -12 -20V-15H-23Z", INK, INK, 1.6))


def bubble(x, y, w, h, tail, side="l", fill=WHITE, sw=3, r=None, dash=None):
    """Snakkeboble: tail = (tx, ty) spissen, side er kanten halen går ut av."""
    r = r if r is not None else min(w, h) * .32
    tx, ty = tail
    tb = min(14, (h if side in "lr" else w) * .2)
    if side == "l":
        cy = min(max(ty, y + r + tb), y + h - r - tb)
        base = [(x, cy - tb), (x, cy + tb)]
    elif side == "r":
        cy = min(max(ty, y + r + tb), y + h - r - tb)
        base = [(x + w, cy - tb), (x + w, cy + tb)]
    elif side == "b":
        cx = min(max(tx, x + r + tb), x + w - r - tb)
        base = [(cx - tb, y + h), (cx + tb, y + h)]
    else:
        cx = min(max(tx, x + r + tb), x + w - r - tb)
        base = [(cx - tb, y), (cx + tb, y)]
    da = f' stroke-dasharray="{dash}"' if dash else ""
    tailp = f"M{base[0][0]:.1f} {base[0][1]:.1f}L{tx:.1f} {ty:.1f}L{base[1][0]:.1f} {base[1][1]:.1f}Z"
    wob = R.uniform(-1, 1)
    d = (f"M{x+r:.1f} {y:.1f}Q{x+w/2:.1f} {y-2+wob:.1f} {x+w-r:.1f} {y:.1f}Q{x+w:.1f} {y:.1f} {x+w:.1f} {y+r:.1f}"
         f"Q{x+w+2-wob:.1f} {y+h/2:.1f} {x+w:.1f} {y+h-r:.1f}Q{x+w:.1f} {y+h:.1f} {x+w-r:.1f} {y+h:.1f}"
         f"Q{x+w/2:.1f} {y+h+2+wob:.1f} {x+r:.1f} {y+h:.1f}Q{x:.1f} {y+h:.1f} {x:.1f} {y+h-r:.1f}"
         f"Q{x-2-wob:.1f} {y+h/2:.1f} {x:.1f} {y+r:.1f}Q{x:.1f} {y:.1f} {x+r:.1f} {y:.1f}Z")
    return (f'<path d="{tailp}" fill="{fill}" stroke="{INK}" stroke-width="{sw}" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"{da}/>'
            f'<path d="M{base[0][0]:.1f} {base[0][1]:.1f}L{base[1][0]:.1f} {base[1][1]:.1f}" stroke="{fill}" stroke-width="{sw+1.4}"/>')


def plate(x, y, w, h, label, value, vs=30, sub=None, flat=WHITE, ls=14.5, vf="d"):
    """Datapanel: alle tall står ved siden av figuren, aldri bak den."""
    o = [plain(x, y, w, h, flat), T(x + 7, y + ls + 2, label, ls, "hb")]
    vy = y + h - 7 - (15 if sub else 0)
    o.append(T(x + 7, vy, value, vs, vf))
    if sub:
        o.append(T(x + 7, y + h - 6, sub, 13.5))
    return "".join(o)


def button(x, y, w, h, label, kind="prim", size=20, icon=None):
    if kind == "prim":
        o = ibox(x, y, w, h, MAG, None, 3, 2, (2.5, 2.5))
        o += T(x + w / 2, y + h / 2 + size * .36, label, size, "d", WHITE, "middle")
    elif kind == "yel":
        o = ibox(x, y, w, h, YEL, None, 3, 2, (2.5, 2.5))
        o += T(x + w / 2, y + h / 2 + size * .36, label, size, "d", INK, "middle")
    elif kind == "off":
        o = plain(x, y, w, h, WHITE, 2, dash="6 5")
        o += T(x + w / 2, y + h / 2 + size * .36, label, size, "h", SOFT, "middle")
    else:
        o = plain(x, y, w, h, WHITE, 2.4)
        o += T(x + w / 2, y + h / 2 + size * .34, label, size, "hb", INK, "middle")
    return o


def status_cell(x, y, label, kind):
    icons = {"ok": ic_check, "wait": ic_hour, "exp": ic_clock, "x": ic_x}
    return icons[kind](x + 8, y - 5, .95) + T(x + 22, y, label, 15)


# ---- tilstand fra fixture ----------------------------------------------------------------------
def seat(week, role="Grossist"):
    return FX["weeks"][week - 1]["seats"][role]


def orders(role="Grossist"):
    return [w["seats"][role]["ordre"] for w in FX["weeks"]]


def state(week, typed=""):
    s = dict(seat(week))
    o = orders()
    hist = o[: week - 1]
    vans = []
    for u in range(week + 1, week + 4):
        src = u - 4
        vans.append((u, o[src - 1] if src >= 1 else 4))
    assert sum(l for _, l in vans) == s["paa_vei_foer_ordre"], (week, vans, s)
    return dict(week=week, typed=typed, hist=hist, vans=vans, **s)


# ---- de tre rutene: samme tegning på telefon, laptop og i albumet --------------------------------
def spanel(x, y, w, h, flat=None, dot=None, tl=0, tr=0, bl=0, br=0, sw=3.2):
    pts = [(x, y + tl), (x + w, y + tr), (x + w, y + h + br), (x, y + h + bl)]
    return ipoly(pts, flat, dot, sw)


def rute1(x, y, w, h, st, loud=True, tilt=(0, 0, 0, 3)):
    tl, tr, bl, br = tilt
    o = [spanel(x, y, w, h, PAPER, "dc", tl, tr, bl, br)]
    ground = y + 30
    rw = road_w(st["vans"])
    o.append(road(x + w - 10, ground, st["vans"], roadfrom=x + w - rw - 18))
    # hovedbilen med levering, tallet står stort på kassen
    o.append(bigvan(x + 8, y + h - 4, st["levering"], s=.92))
    px = x + 158
    pw = (w - 158 - 12) / 2
    ph = min(h - 48, 104)
    py = y + h - 8 - ph
    o.append(plate(px, py, pw, ph, "Levering", str(st["levering"]), 34))
    o.append(plate(px + pw + 4, py, pw, ph, "Sendt", str(st["sendt"]), 34, sub="til Detaljist" if pw > 74 else None))
    if loud:
        size = 18 + min(st["levering"], 30) * 1.1
        o.append(sfx(x + 42, y + 30 if h < 200 else y + h - 96, "DUNK!", size * (1 if h < 200 else 1.5), -7))
    return "".join(o)


def rute2(x, y, w, h, st, tilt=(3, 0, 0, -3), who="Grossist", kind=None):
    tl, tr, bl, br = tilt
    trouble = st["restordre"] > 0
    o = [spanel(x, y, w, h, PAPER, "dm" if trouble else "dc", tl, tr, bl, br)]
    pw = 140
    px = x + w - pw - 8
    # snor med lapper, lager og figur
    scene_w = px - x - 16
    o.append(slips(x + 8, y + 14, st["restordre"], scene_w, per=int(scene_w // 16)))
    tall = h >= 200
    k = 1.32 if tall else 1.0
    shh = 94 * k
    o.append(shelves(x + 14, y + h - 10 - shh, 66, shh, st["lager"]))
    fy = y + h - 7
    o.append(fig(x + 112, fy, who, .74 * k, kind or ("bekymret" if trouble else "rolig")))
    o.append(deskphone(x + 164 + (8 if tall else 0), fy, .9))
    o.append(iline(x + 136, fy, x + 200, fy, 2))
    # innkommende ordre: boblen fra telefonen
    bx = x + 142 + (8 if tall else 0)
    by = fy - 76
    o.append(bubble(bx, by, 52, 38, (bx + 20, fy - 30), "b", WHITE, 2.4))
    o.append(T(bx + 26, by + 28, st["innkommende_ordre"], 24, "d", INK, "middle"))
    o.append(sfx(bx + 6, fy - 86, "RRRING", 17, -5, INK))
    # veien og tallene
    ground = y + 28
    rw = road_w(st["vans"])
    o.append(road(x + w - 10, ground, st["vans"], roadfrom=x + w - rw - 16))
    rest_h = min((h - 36 - 12) * .55, 74)
    h2 = min((h - 36 - 12) * .45, 62)
    top = y + h - 8 - h2 - 4 - rest_h
    o.append(plate(px, top, pw, rest_h, "Restordre", str(st["restordre"]), 34, flat=WHITE))
    y2 = top + rest_h + 4
    o.append(plate(px, y2, pw / 2 - 2, h2, "Lager", str(st["lager"]), 26))
    o.append(plate(px + pw / 2 + 2, y2, pw / 2 - 2, h2, "Ordre", str(st["innkommende_ordre"]), 26))
    return "".join(o)


def rute3(x, y, w, h, st, tilt=(-3, 0, 0, 0), who="Grossist", confirmed=False, labels=True, ghost_on=True):
    tl, tr, bl, br = tilt
    typed = st.get("typed", "")
    o = [spanel(x, y, w, h, YEL, None, tl, tr, bl, br)]
    # på vei: egen plate, biler med ukenummer. Nyordren står stiplet som en bil til
    o.append(plate(x + 8, y + 7, 74, 52, "På vei", str(st["paa_vei_foer_ordre"]), 25))
    ghost = (st["week"] + 4, int(typed)) if typed and ghost_on else None
    ground = y + 30
    rw = road_w(st["vans"], True, 6, ghost)
    o.append(road(x + w - 8, ground, st["vans"], True, 6, ghost, roadfrom=x + 90))
    fy = y + h - 5
    o.append(fig(x + 44, fy, who, .78 if h < 200 else .98, "rolig" if typed else "tenker", arm="opp" if not confirmed else "ned"))
    bx, by, bw, bh = x + 94, y + 54, w - 94 - 10, h - 54 - 8
    fill = WHITE
    o.append(bubble(bx, by, bw, bh, (x + 66, y + h - 62), "l", fill, 3.4))
    if typed:
        cx = bx + bw / 2
        fs = min(bh * .78, 76)
        o.append(T(cx, by + bh / 2 + fs * .36, typed, fs, "d", INK, "middle"))
        if not confirmed:
            cw = tw(typed, fs, "d") / 2 + 8
            o.append(f'<rect x="{cx+cw:.1f}" y="{by+bh/2-fs*.42:.1f}" width="4" height="{fs*.84:.1f}" fill="{MAG}">'
                     '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>')
        else:
            o.append(g(f"rotate(-7 {bx+bw-46:.1f} {by+bh-20:.1f})",
                       rr(bx + bw - 88, by + bh - 34, 76, 26, 3, WHITE, MAG, 2.6),
                       ic_check(bx + bw - 74, by + bh - 21, .8, MAG),
                       T(bx + bw - 62, by + bh - 15, "Bestilt", 16, "hb", MAG)))
    else:
        cx = bx + 20
        o.append(f'<rect x="{cx:.1f}" y="{by+bh/2-24:.1f}" width="4" height="48" fill="{MAG}">'
                 '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>')
        o.append(T(cx + 14, by + bh / 2 + 7, "Hvor mange bestiller du?", 19, "h", SOFT))
    return "".join(o)


def key(x, y, w, h, label=None, icon=None):
    o = plain(x, y, w, h, WHITE, 2.2)
    if label is not None:
        o += T(x + w / 2, y + h / 2 + 8, label, 22, "d", INK, "middle")
    if icon == "back":
        o += ic_back(x + w / 2, y + h / 2, 1.05)
    return o


def history(x, y, w, st, extra=None, h=46):
    """Egen ordrehistorikk: små bobler, en per Uke. Viser de siste ti, resten i albumet."""
    o = [T(x + 2, y + 18, "Dine", 15, "hb"), T(x + 2, y + 35, "ordre", 15, "hb")]
    hist = list(st["hist"]) + ([extra] if extra else [])
    start = max(0, len(hist) - 10)
    sub = hist[start:]
    bx0 = x + 46
    step = (w - 46 - 34) / 10
    for i, v in enumerate(sub):
        wk = start + i + 1
        bx = bx0 + i * step
        o.append(T(bx + step / 2 - 1, y + 13, wk, 13.5, "h", SOFT, "middle"))
        o.append(bubble(bx + 1, y + 17, step - 4, 22, (bx + 5, y + 44), "b", YEL if wk <= 4 else WHITE, 1.7, r=7))
        o.append(T(bx + step / 2 - 1, y + 34, v, 17, "d" if v >= 10 else "hb", INK, "middle"))
    o.append(ic_page(x + w - 15, y + 24, 1.05))
    o.append(T(x + w - 15, y + 46, "Bla", 13.5, "h", INK, "middle"))
    return "".join(o)


def keypad(x, y, w, h=48):
    kw = (w - 5 * 4) / 6
    o = []
    for i, d in enumerate("123456"):
        o.append(key(x + i * (kw + 4), y, kw, h, d))
    for i, d in enumerate("7890"):
        o.append(key(x + i * (kw + 4), y + h + 4, kw, h, d))
    o.append(key(x + 4 * (kw + 4), y + h + 4, kw * 2 + 4, h, icon="back"))
    return "".join(o)


def head(st, x=8, right=382):
    wk = str(st["week"])
    o = [ibox(x, 36, 128, 46, YEL, None, 3), T(x + 7, 70, f"UKE {wk}", 26, "d")]
    o.append(mark(x + 144, 49, "Grossist", 7))
    o.append(T(x + 156, 55, "Grossist", 16, "hb"))
    o.append(T(x + 136, 76, "Sara, Spill 17", 15))
    px = right - 124
    o.append(plain(px, 36, 124, 46, WHITE, 2))
    o.append(T(px + 7, 52, "Totalkostnad", 14.5, "hb"))
    o.append(T(px + 7, 76, nok(st["kost_sum"]), 16, "d"))
    return "".join(o)


def foot(wait="Venter på deg og Jonas (Fabrikk), 3 min", note="Kan ikke endres etterpå.", pause=True):
    o = []
    o.append(ic_hour(16, 803, .85))
    o.append(T(26, 808, wait, 15.5))
    o.append(T(12, 829, note, 14, "h", SOFT))
    o.append(T(160, 829, "Demodata", 14, "hb", INK))
    if pause:
        o.append(plain(306, 794, 76, 40, WHITE, 2))
        o.append(ic_pause(322, 814, .9))
        o.append(T(334, 820, "Pause", 16, "hb"))
    return "".join(o)


def screen_week(st, confirm=True):
    """Hele spillskjermen i 390-skala: stripen, historikk, tastatur, Bekreft."""
    typed = st.get("typed", "")
    o = [head(st)]
    o.append(rute1(8, 88, 374, 140, st))
    o.append(rute2(8, 232, 374, 168, st))
    o.append(rute3(8, 404, 374, 174, st))
    o.append(history(8, 582, 374, st))
    o.append(keypad(8, 634, 374, 46))
    if typed:
        o.append(button(8, 736, 374, 52, f"Bekreft ordre: {typed}", "prim", 20))
    else:
        o.append(button(8, 736, 374, 52, "Skriv et tall først", "off", 20))
    o.append(foot())
    return "".join(o)


def phone(x, y, inner, s=1.0, fill=PAPER):
    """Enkel, håndtegnet ramme. 390x844 inni."""
    return g(f"translate({x:.1f} {y:.1f}) scale({s})",
             rr(-11, -11, 412, 866, 42, INK, INK, 2), rr(0, 0, 390, 844, 32, fill, INK, 1),
             f'<rect x="165" y="11" width="60" height="7" rx="3.5" fill="{INK}"/>', inner)
