"""Tegnebibliotek for konsept 04 Miniatyrlandet: isometriske bokser, tak, biler, kasser, bygg og tåke.

Dioramaet er data: crate-tellingen i Tally skal alltid stemme med tallet som vises.
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
DATA = json.loads((HERE / ".." / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WEEKS = {w["week"]: w for w in DATA["weeks"]}
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAMES = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

# Palett
FJORD = "#0B7285"
FJORD_D = "#07505F"
FJORD_L = "#2AA7B8"
FJORD_P = "#D4EEF2"
INK = "#0C2E38"
MUTED = "#3A5A65"
FURU = "#1E6B46"
FURU_D = "#134B30"
FURU_L = "#3C9A5F"
GRASS = "#86C96E"
GRASS_D = "#6DB85E"
OKER = "#E09F1F"
OKER_D = "#8F5E0B"
OKER_L = "#F6C552"
FALU = "#B3322A"
FALU_D = "#84231E"
FALU_L = "#D2513F"
WHITE = "#FFFFFF"
PAPER = "#F2FAFB"
LINE = "#BCD6DC"
FOG = "#EEF6F8"
ASPHALT = "#46596A"
ASPHALT_L = "#56697A"
CONCRETE = "#D6E0E3"
WOOD = "#C9985B"
GLASS_LIT = "#FFDD6B"
GLASS_DARK = "#20404C"
VIOLET = "#3C2F7A"  # bare KI-merket

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800"
    "&amp;family=Nunito:wght@500;600;700;800;900&amp;display=swap');"
)
CSS = (
    FONT_IMPORT
    + ".c04-b{font-family:'Baloo 2','Nunito','Trebuchet MS','Segoe UI',sans-serif}"
    ".c04-n{font-family:'Nunito','Baloo 2','Trebuchet MS','Segoe UI',sans-serif}"
    ".c04-t{font-variant-numeric:tabular-nums lining-nums}"
)


def fnum(v, dec=2):
    """Norsk tall: 2 266,00"""
    s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def kr(v):
    return fnum(v) + " kr"


def mix(a, b, t):
    a = a.lstrip("#")
    b = b.lstrip("#")
    ca = [int(a[i : i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i : i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def tone(c):
    return mix(c, "#FFFFFF", 0.2), c, mix(c, "#04202B", 0.26)


# ---------- SVG-primitiver ----------
def T(x, y, s, size=14, w=700, fill=INK, f="n", a="start", extra="", num=False):
    cls = f"c04-{f}" + (" c04-t" if num else "")
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" font-weight="{w}" '
        f'fill="{fill}" text-anchor="{a}"{(" " + extra) if extra else ""}>{escape(str(s))}</text>'
    )


def wrap(text, width, size, k=0.53):
    limit = max(4, int(width / (size * k)))
    lines, cur = [], ""
    for word in str(text).split():
        trial = (cur + " " + word).strip()
        if len(trial) > limit and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def P(x, y, text, width, size=14, lh=1.36, w=600, fill=INK, f="n", a="start", k=0.53):
    """Avsnitt med manuell linjebryting. Returnerer (svg, y etter siste linje)."""
    out = []
    lines = wrap(text, width, size, k)
    for i, line in enumerate(lines):
        out.append(T(x, y + i * size * lh, line, size, w, fill, f, a))
    return "".join(out), y + len(lines) * size * lh


def PS(*args, **kw):
    return P(*args, **kw)[0]


def R(x, y, w, h, rx=0, fill="none", stroke="none", sw=0, op=None, dash=None, extra=""):
    a = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"'
    if rx:
        a += f' rx="{rx}"'
    if stroke != "none":
        a += f' stroke="{stroke}" stroke-width="{sw}"'
    if op is not None:
        a += f' opacity="{op}"'
    if dash:
        a += f' stroke-dasharray="{dash}"'
    if extra:
        a += " " + extra
    return a + "/>"


def L(x1, y1, x2, y2, stroke=INK, sw=1, dash=None, op=None, cap=None):
    a = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"'
    if dash:
        a += f' stroke-dasharray="{dash}"'
    if op is not None:
        a += f' opacity="{op}"'
    if cap:
        a += f' stroke-linecap="{cap}"'
    return a + "/>"


def C(x, y, r, fill="none", stroke="none", sw=0, op=None):
    a = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}"'
    if stroke != "none":
        a += f' stroke="{stroke}" stroke-width="{sw}"'
    if op is not None:
        a += f' opacity="{op}"'
    return a + "/>"


def PATH(d, fill="none", stroke="none", sw=0, op=None, cap="round", dash=None, extra=""):
    a = f'<path d="{d}" fill="{fill}"'
    if stroke != "none":
        a += f' stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}" stroke-linejoin="round"'
    if op is not None:
        a += f' opacity="{op}"'
    if dash:
        a += f' stroke-dasharray="{dash}"'
    if extra:
        a += " " + extra
    return a + "/>"


def G(content, tr=None, extra=""):
    a = "<g"
    if tr:
        a += f' transform="{tr}"'
    if extra:
        a += " " + extra
    return a + ">" + content + "</g>"


# ---------- Side ----------
class Page:
    def __init__(self, fname, page, w, h, title, desc, bg=PAPER):
        self.fname, self.page, self.w, self.h = fname, page, w, h
        self.title, self.desc, self.bg = title, desc, bg
        self.defs = []
        self.parts = []
        self.n = 0
        self.defs.append(
            f'<filter id="c04-{page}-soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.6"/></filter>'
            f'<filter id="c04-{page}-fog" x="-40%" y="-60%" width="180%" height="220%"><feGaussianBlur stdDeviation="13"/></filter>'
            f'<filter id="c04-{page}-puff" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="1.4"/></filter>'
        )

    def uid(self, kind="x"):
        self.n += 1
        return f"c04-{self.page}-{kind}{self.n}"

    def url(self, name):
        return f"url(#c04-{self.page}-{name})"

    def clip(self, x, y, w, h, rx=0):
        i = self.uid("clip")
        self.defs.append(f'<clipPath id="{i}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></clipPath>')
        return f"url(#{i})"

    def add(self, *parts):
        self.parts.extend(parts)

    def write(self):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
            f"font-family=\"'Nunito','Baloo 2','Trebuchet MS','Segoe UI',sans-serif\">"
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>"
            f"<style>{CSS}</style><defs>{''.join(self.defs)}</defs>"
            f'{R(0, 0, self.w, self.h, 0, self.bg)}{"".join(self.parts)}</svg>'
        )
        (HERE / self.fname).write_text(svg, encoding="utf-8")


class Tally:
    """Teller tegnede kasser, slik at build.py kan bevise at diorama = tall."""

    def __init__(self):
        self.full = 0
        self.owed = 0


# ---------- Isometri ----------
class Iso:
    def __init__(self, pg, ox, oy, u, zk=1.0):
        self.pg, self.ox, self.oy, self.u, self.zk = pg, ox, oy, u, zk

    def p(self, x, y, z=0):
        return (self.ox + (x - y) * self.u, self.oy + (x + y) * self.u / 2 - z * self.u * self.zk)

    def pts(self, pts):
        return " ".join(f"{a:.1f},{b:.1f}" for a, b in (self.p(*q) for q in pts))

    def poly(self, pts, fill, stroke="none", sw=0, op=None, dash=None, extra=""):
        a = f'<polygon points="{self.pts(pts)}" fill="{fill}"'
        if stroke != "none":
            a += f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"'
        if op is not None:
            a += f' opacity="{op}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if extra:
            a += " " + extra
        return a + "/>"

    def line(self, a, b, stroke, sw=1, dash=None, op=None):
        x1, y1 = self.p(*a)
        x2, y2 = self.p(*b)
        return L(x1, y1, x2, y2, stroke, sw, dash, op, "round")

    def box(self, x, y, z, dx, dy, dz, colors, stroke="none", sw=0):
        top, left, right = colors
        X, Y, Z = x + dx, y + dy, z + dz
        return (
            self.poly([(x, Y, z), (X, Y, z), (X, Y, Z), (x, Y, Z)], left, stroke, sw)
            + self.poly([(X, Y, z), (X, y, z), (X, y, Z), (X, Y, Z)], right, stroke, sw)
            + self.poly([(x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)], top, stroke, sw)
        )

    def tbox(self, x, y, z, dx, dy, dz, c, stroke=None, sw=0.5):
        st = stroke if stroke else mix(c, "#04202B", 0.42)
        return self.box(x, y, z, dx, dy, dz, tone(c), st, sw)

    def shadow(self, x, y, dx, dy, h=1.0, op=0.24):
        s = 0.55 * h
        return self.poly(
            [(x, y + dy), (x + dx, y + dy), (x + dx + s, y + dy - s), (x + dx + s, y - s), (x + s, y - s), (x, y)],
            "#062430",
            op=op,
            extra=f'filter="{self.pg.url("soft")}"',
        )

    def wall_text(self, run, x, y, z, s, size, fill=WHITE, w=800, f="b", a="start"):
        """Tekst malt på vegg. run='+x' synker mot høyre, run='-y' stiger mot høyre."""
        px, py = self.p(x, y, z)
        b = 0.5 if run == "+x" else -0.5
        return (
            f'<text transform="matrix(1 {b} 0 1 {px:.1f} {py:.1f})" class="c04-{f}" font-size="{size}" '
            f'font-weight="{w}" fill="{fill}" text-anchor="{a}">{escape(str(s))}</text>'
        )

    def win_y(self, x, y, z, w, h, fill, frame=WHITE):
        """Vindu på synlig venstre fasade (planet y=konstant)."""
        return self.poly([(x, y, z), (x + w, y, z), (x + w, y, z + h), (x, y, z + h)], fill, frame, 0.8)

    def win_x(self, x, y, z, w, h, fill, frame=WHITE):
        """Vindu på synlig høyre fasade (planet x=konstant)."""
        return self.poly([(x, y + w, z), (x, y, z), (x, y, z + h), (x, y + w, z + h)], fill, frame, 0.8)


# ---------- Kasser og paller ----------
def crate(iso, x, y, z, s=0.46, c=OKER, tally=None):
    if tally is not None:
        tally.full += 1
    edge = mix(c, "#2A1500", 0.55)
    out = iso.box(x, y, z, s, s, s, (mix(c, "#FFFFFF", 0.32), c, mix(c, "#04202B", 0.2)), edge, 0.6)
    if iso.u * s >= 7:
        out += iso.line((x, y + s, z + s * 0.5), (x + s, y + s, z + s * 0.5), edge, 0.5, op=0.75)
        out += iso.line((x + s, y + s, z + s * 0.5), (x + s, y, z + s * 0.5), edge, 0.5, op=0.75)
    return out


def ghost_crate(iso, x, y, z, s=0.34, c=FALU, tally=None):
    """Tom ramme: en kasse du skylder."""
    if tally is not None:
        tally.owed += 1
    d = "1.8 1.4" if iso.u * s > 6 else "1 1"
    X, Y, Z = x + s, y + s, z + s
    f = mix(c, "#FFFFFF", 0.82)
    return (
        iso.poly([(x, Y, z), (X, Y, z), (X, Y, Z), (x, Y, Z)], f, c, 0.9, dash=d)
        + iso.poly([(X, Y, z), (X, y, z), (X, y, Z), (X, Y, Z)], f, c, 0.9, dash=d)
        + iso.poly([(x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)], WHITE, c, 0.9, dash=d)
    )


CRATE_S = 0.46
PALLET_DX = 1.15
PALLET_DY = 1.22


def pallet(iso, x, y, n, s=CRATE_S, c=OKER, tally=None):
    """Palle med plass til 4 kasser: 2 brede, 2 høye. Alle fire synes alltid."""
    w = s * 2 + 0.04
    out = iso.box(x, y, 0, w, s + 0.02, 0.07, (mix(WOOD, "#FFFFFF", 0.2), WOOD, mix(WOOD, "#04202B", 0.25)), mix(WOOD, "#2A1500", 0.5), 0.4)
    spots = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for i in range(min(n, 4)):
        cx, lv = spots[i]
        out += crate(iso, x + 0.01 + cx * (s + 0.01), y + 0.01, 0.07 + lv * s, s, c, tally)
    return out


def pallets_needed(n):
    return (n + 3) // 4


def bays(iso, x0, y0, cols, rows, lager, tally=None, dx=PALLET_DX, dy=PALLET_DY, s=CRATE_S, c=OKER):
    """Tegner alle bås med paller; fyller fra bakerst ved porten og framover."""
    out = ""
    rest = lager
    for j in range(rows):
        for i in range(cols):
            px, py = x0 + i * dx, y0 + j * dy
            n = min(4, rest)
            rest -= n
            out += pallet(iso, px, py, n, s, c, tally)
    if rest:
        raise ValueError(f"Ikke plass til {lager} kasser i {cols}x{rows}")
    return out


# ---------- Biler ----------
def van(iso, x, y, heading, full=0, owed=0, body=FJORD, tally=None, trailer=None):
    """Varebil med plass til 4 kasser i planet. Lengde 1,5 og bredde 0,72.

    heading: '+y' kjører mot venstre ned, '-y' mot høyre opp, '+x' mot høyre ned.
    (x, y) er hjørnet med lavest x og y.
    """
    W, LEN = 0.72, 1.5
    cab = 0.52
    out = ""
    along_y = heading in ("+y", "-y")
    dx, dy = (W, LEN) if along_y else (LEN, W)
    out += iso.shadow(x, y, dx, dy, 0.5, 0.2)
    dark = "#0E2A33"

    def wheel(px, py):
        cx, cy = iso.p(px, py, 0.12)
        r = max(1.8, iso.u * 0.13)
        return C(cx, cy, r, dark) + C(cx, cy, r * 0.42, "#B9CBD1")

    def chassis():
        return iso.tbox(x, y, 0.13, dx, dy, 0.1, "#2B4552", sw=0.3)

    def slots(bx, by, cols_x):
        s = 0.3
        res = ""
        spots = []
        for j in range(2):
            for i in range(2):
                spots.append((i, j))
        n = 0
        for j in range(2):
            for i in range(2):
                if cols_x:
                    px, py = bx + 0.03 + i * 0.32, by + 0.05 + j * 0.42
                else:
                    px, py = bx + 0.05 + i * 0.42, by + 0.03 + j * 0.32
                if along_y:
                    px, py = bx + 0.03 + i * 0.34, by + 0.06 + j * 0.44
                else:
                    px, py = bx + 0.06 + i * 0.44, by + 0.03 + j * 0.34
                if n < full:
                    res += crate(iso, px, py, 0.24, s, OKER, tally)
                elif n < full + owed:
                    res += ghost_crate(iso, px, py, 0.24, s, FALU, tally)
                n += 1
        return res

    def bed(bx, by, bdx, bdy):
        return iso.box(bx, by, 0.23, bdx, bdy, 0.01, ("#7C94A0", "#5C7682", "#4A626E"), "#233B46", 0.3)

    def cab_box(cx_, cy_, cdx, cdy, wind):
        res = iso.tbox(cx_, cy_, 0.23, cdx, cdy, 0.42, body, sw=0.4)
        glass = "#BFE4EC"
        if wind == "y+":
            res += iso.win_y(cx_ + 0.08, cy_ + cdy, 0.39, cdx - 0.16, 0.2, glass, mix(body, "#000000", 0.3))
            res += iso.win_x(cx_ + cdx, cy_ + 0.08, 0.39, cdy - 0.2, 0.2, glass, mix(body, "#000000", 0.3))
        elif wind == "x+":
            res += iso.win_x(cx_ + cdx, cy_ + 0.08, 0.39, cdy - 0.16, 0.2, glass, mix(body, "#000000", 0.3))
            res += iso.win_y(cx_ + 0.08, cy_ + cdy, 0.39, cdx - 0.2, 0.2, glass, mix(body, "#000000", 0.3))
        else:
            res += iso.win_x(cx_ + cdx, cy_ + 0.14, 0.39, cdy - 0.22, 0.2, glass, mix(body, "#000000", 0.3))
        return res

    out += chassis()
    if heading == "+y":
        bedy = y
        out += bed(x, bedy, W, LEN - cab - 0.02)
        out += slots(x, bedy, True)
        out += cab_box(x, y + LEN - cab, W, cab, "y+")
        out += wheel(x + W, y + 0.3) + wheel(x + W, y + LEN - 0.3)
    elif heading == "-y":
        out += cab_box(x, y, W, cab, "side")
        bedy = y + cab + 0.02
        out += bed(x, bedy, W, LEN - cab - 0.02)
        out += slots(x, bedy, True)
        out += wheel(x + W, y + 0.3) + wheel(x + W, y + LEN - 0.3)
    else:  # '+x'
        out += bed(x, y, LEN - cab - 0.02, W)
        out += slots(x, y, False)
        out += cab_box(x + LEN - cab, y, cab, W, "x+")
        fx, fy = iso.p(x + 0.3, y + W, 0.12)
        out += wheel(x + 0.3, y + W) + wheel(x + LEN - 0.3, y + W)
    return out


def courier(iso, x, y, label=None, heading="-y"):
    """Liten budbil med ordreseddel på taket."""
    out = iso.shadow(x, y, 0.52, 0.9, 0.5, 0.2)
    out += iso.tbox(x, y, 0.1, 0.52, 0.9, 0.42, WHITE, FJORD_D, 0.5)
    out += iso.win_x(x + 0.52, y + 0.08, 0.26, 0.3, 0.17, "#BFE4EC", FJORD_D)
    for py in (0.2, 0.7):
        cx, cy = iso.p(x + 0.52, y + py, 0.1)
        out += C(cx, cy, max(1.5, iso.u * 0.1), "#0E2A33")
    return out


def split_vans(n, cap=4):
    res = []
    while n > 0:
        res.append(min(n, cap))
        n -= cap
    return res


# ---------- Natur ----------
def spruce(iso, x, y, h=1.5, c=FURU):
    px, py = iso.p(x, y, 0)
    u = iso.u
    w = 0.5 * u
    H = h * u
    out = f'<ellipse cx="{px + w * 0.8:.1f}" cy="{py + 0.5:.1f}" rx="{w * 1.25:.1f}" ry="{w * 0.5:.1f}" fill="#062430" opacity=".2" filter="{iso.pg.url("soft")}"/>'
    out += R(px - u * 0.05, py - u * 0.2, u * 0.1, u * 0.22, 0, "#5B3A1E")
    light, dark = mix(c, "#7CD08A", 0.22), mix(c, "#04202B", 0.2)
    for i in range(3):
        k = 1 - i * 0.26
        base = py - u * 0.14 - i * H * 0.24
        tip = base - H * 0.5 * (1 - i * 0.12)
        out += f'<polygon points="{px - w * k:.1f},{base:.1f} {px:.1f},{tip:.1f} {px:.1f},{base + w * k * 0.2:.1f}" fill="{light}"/>'
        out += f'<polygon points="{px:.1f},{tip:.1f} {px + w * k:.1f},{base:.1f} {px:.1f},{base + w * k * 0.2:.1f}" fill="{dark}"/>'
    return out


def fog(pg, ellipses, op=1.0):
    """ellipses: (cx, cy, rx, ry, opacity)"""
    body = "".join(
        f'<ellipse cx="{a}" cy="{b}" rx="{c}" ry="{d}" fill="{FOG}" opacity="{e}"/>' for a, b, c, d, e in ellipses
    )
    return f'<g filter="{pg.url("fog")}" opacity="{op}">{body}</g>'


def waves(iso, x0, y0, x1, y1, n=12, seed=3):
    out = ""
    a = seed
    for i in range(n):
        a = (a * 37 + 11) % 101
        b = (a * 53 + 7) % 97
        x = x0 + (x1 - x0) * (a / 100)
        y = y0 + (y1 - y0) * (b / 96)
        px, py = iso.p(x, y)
        ln = iso.u * (0.35 + (a % 5) * 0.1)
        out += PATH(f"M{px - ln:.1f} {py:.1f} q{ln / 2:.1f} {-ln * 0.22:.1f} {ln:.1f} 0 t{ln:.1f} 0", stroke=mix(FJORD_L, "#FFFFFF", 0.35), sw=1.1, op=0.55)
    return out


# ---------- Tak ----------
def gable(iso, x, y, z, dx, dy, rise, c, wall, ridge="x", over=0.1):
    """Saltak. ridge='x' betyr møne langs x-aksen."""
    light, base, dark = tone(c)
    st = mix(c, "#2A1500", 0.45)
    out = ""
    if ridge == "x":
        m = y + dy / 2
        out += iso.poly([(x + dx, y, z), (x + dx, y + dy, z), (x + dx, m, z + rise)], mix(wall, "#04202B", 0.2), mix(wall, "#04202B", 0.45), 0.5)
        out += iso.poly([(x - over, y - over, z), (x + dx + over, y - over, z), (x + dx + over, m, z + rise), (x - over, m, z + rise)], dark, st, 0.5)
        out += iso.poly([(x - over, m, z + rise), (x + dx + over, m, z + rise), (x + dx + over, y + dy + over, z), (x - over, y + dy + over, z)], light, st, 0.5)
    else:
        m = x + dx / 2
        out += iso.poly([(x, y + dy, z), (x + dx, y + dy, z), (m, y + dy, z + rise)], wall, mix(wall, "#04202B", 0.45), 0.5)
        out += iso.poly([(x - over, y - over, z), (m, y - over, z + rise), (m, y + dy + over, z + rise), (x - over, y + dy + over, z)], light, st, 0.5)
        out += iso.poly([(m, y - over, z + rise), (x + dx + over, y - over, z), (x + dx + over, y + dy + over, z), (m, y + dy + over, z + rise)], base, st, 0.5)
    return out


# ---------- Lukkede bygg, form følger Rolle ----------
def b_detaljist(iso, x, y, lit=True):
    """Butikk: gul trebygning, falurødt saltak, stripet markise."""
    dx, dy, h = 2.0, 1.5, 0.95
    wall = OKER_L
    out = iso.shadow(x, y, dx, dy, 1.4)
    out += iso.tbox(x, y, 0, dx, dy, h, wall)
    glass = GLASS_LIT if lit else GLASS_DARK
    out += iso.win_y(x + 0.2, y + dy, 0.2, 0.75, 0.48, glass)
    out += iso.win_y(x + 1.1, y + dy, 0.0, 0.35, 0.62, FJORD_D)
    out += iso.win_x(x + dx, y + 0.35, 0.34, 0.4, 0.34, glass)
    out += iso.win_x(x + dx, y + 0.95, 0.34, 0.4, 0.34, glass)
    # markise
    n = 6
    for i in range(n):
        a = x + 0.08 + i * (dx - 0.16) / n
        b = a + (dx - 0.16) / n
        col = WHITE if i % 2 else FALU_L
        out += iso.poly([(a, y + dy, 0.82), (b, y + dy, 0.82), (b, y + dy + 0.3, 0.62), (a, y + dy + 0.3, 0.62)], col, mix(FALU, "#000000", 0.2), 0.25)
    out += gable(iso, x, y, h, dx, dy, 0.55, FALU, wall, "x")
    return out


def b_grossist(iso, x, y, lit=True):
    """Lagerhus: falurødt, oker saltak, stor port."""
    dx, dy, h = 2.5, 2.0, 1.05
    out = iso.shadow(x, y, dx, dy, 1.5)
    out += iso.tbox(x, y, 0, dx, dy, h, FALU)
    glass = GLASS_LIT if lit else GLASS_DARK
    for i in range(3):
        out += iso.win_y(x + 0.28 + i * 0.75, y + dy, 0.45, 0.42, 0.34, glass)
    out += iso.win_x(x + dx, y + 0.5, 0, 1.0, 0.72, mix(FALU, "#FFFFFF", 0.82), FALU_D)
    for i in range(1, 4):
        out += iso.line((x + dx, y + 0.5, i * 0.18), (x + dx, y + 1.5, i * 0.18), MUTED, 0.5)
    out += gable(iso, x, y, h, dx, dy, 0.65, OKER, FALU, "y")
    return out


def b_distributor(iso, x, y, lit=True):
    """Terminal: lang og lav, hvit, flatt fjordblått tak, rekke av dokkporter."""
    dx, dy, h = 3.0, 1.6, 0.85
    w = "#E3EEF0"
    out = iso.shadow(x, y, dx, dy, 1.1)
    out += iso.tbox(x, y, 0, dx, dy, h, w)
    for i in range(4):
        out += iso.win_y(x + 0.16 + i * 0.7, y + dy, 0, 0.5, 0.56, "#7E97A3", FJORD_D)
    glass = GLASS_LIT if lit else GLASS_DARK
    out += iso.win_x(x + dx, y + 0.2, 0.42, 0.52, 0.28, glass, FJORD_D)
    out += iso.win_x(x + dx, y + 0.9, 0.42, 0.52, 0.28, glass, FJORD_D)
    out += iso.tbox(x - 0.05, y - 0.05, h, dx + 0.1, dy + 0.1, 0.13, FJORD)
    return out


def b_fabrikk(iso, x, y, lit=True, smoke=True):
    """Fabrikk: furugrønn, sagtak, høy skorstein."""
    dx, dy, h = 2.7, 2.0, 0.9
    out = iso.shadow(x, y, dx, dy, 1.6)
    # skorstein bak
    out += iso.tbox(x + 0.2, y + 0.15, 0, 0.42, 0.42, 2.25, FALU)
    out += iso.box(x + 0.2, y + 0.15, 1.75, 0.42, 0.42, 0.18, (WHITE, WHITE, CONCRETE))
    if smoke:
        for i, (a, b, r) in enumerate([(0.1, 2.55, 0.17), (0.28, 2.82, 0.23), (0.58, 3.08, 0.3)]):
            px, py = iso.p(x + 0.4 + a, y + 0.3 - a, b)
            out += C(px, py, r * iso.u, "#F4F9FA", op=0.92 - i * 0.13)
    out += iso.tbox(x, y, 0, dx, dy, h, FURU)
    glass = GLASS_LIT if lit else GLASS_DARK
    for i in range(4):
        out += iso.win_y(x + 0.2 + i * 0.62, y + dy, 0.35, 0.4, 0.34, glass)
    out += iso.win_x(x + dx, y + 0.5, 0, 0.9, 0.62, mix(FURU, "#FFFFFF", 0.8), FURU_D)
    # sagtak: tre tenner langs x
    t = dx / 3
    for i in range(3):
        a = x + i * t
        b = a + t
        out += iso.poly([(b, y, h), (b, y + dy, h), (b, y + dy, h + 0.45), (b, y, h + 0.45)], "#BFE4EC", FURU_D, 0.5)
        out += iso.poly([(a, y, h), (b, y, h + 0.45), (b, y + dy, h + 0.45), (a, y + dy, h)], OKER_L, OKER_D, 0.5)
        out += iso.poly([(a, y + dy, h), (b, y + dy, h), (b, y + dy, h + 0.45)], mix(FURU, "#FFFFFF", 0.1), FURU_D, 0.4)
    return out


BUILD = {"Detaljist": b_detaljist, "Grossist": b_grossist, "Distributør": b_distributor, "Fabrikk": b_fabrikk}
ROLE_WALL = {"Detaljist": OKER_L, "Grossist": FALU, "Distributør": "#E3EEF0", "Fabrikk": FURU}
ROLE_ROOF = {"Detaljist": FALU, "Grossist": OKER, "Distributør": FJORD, "Fabrikk": OKER_L}
ROLE_INK = {"Detaljist": OKER_D, "Grossist": FALU, "Distributør": FJORD, "Fabrikk": FURU}


# ---------- Åpen hall ----------
def hall_cut(iso, x, y, cols, rows, lager, role="Grossist", tally=None, wall_label=None, sub_label=None, label_size=17):
    """Hall sett ovenfra med avtatt tak. Kassene på gulvet ER lagertallet."""
    margin_x, margin_y = 0.32, 0.42
    dx = margin_x * 2 + (cols - 1) * PALLET_DX + 0.96
    dy = margin_y + 0.34 + (rows - 1) * PALLET_DY + 0.5
    H = 1.45
    wall = ROLE_WALL[role]
    roof = ROLE_ROOF[role]
    light, base, dark = tone(wall)
    edge = mix(wall, "#04202B", 0.45)
    out = iso.shadow(x, y, dx, dy, 0.5, 0.2)
    # gulv
    floor = "#E7EFF1"
    out += iso.poly([(x, y, 0), (x + dx, y, 0), (x + dx, y + dy, 0), (x, y + dy, 0)], floor, "#A9BEC5", 0.6)
    # gulvplanker
    for i in range(1, int(dy) + 2):
        yy = y + i * 0.9
        if yy < y + dy:
            out += iso.line((x, yy, 0), (x + dx, yy, 0), "#C9D7DB", 0.6)
    # bakvegger (innsiden)
    out += iso.poly([(x, y + dy, 0), (x, y, 0), (x, y, H), (x, y + dy, H)], dark, edge, 0.5)
    out += iso.poly([(x, y, 0), (x + dx, y, 0), (x + dx, y, H), (x, y, H)], base, edge, 0.5)
    # bordkledning
    st = mix(wall, "#04202B", 0.34)
    step = 0.45
    k = 1
    while k * step < dx:
        out += iso.line((x + k * step, y, 0), (x + k * step, y, H), st, 0.5, op=0.65)
        k += 1
    k = 1
    while k * step < dy:
        out += iso.line((x, y + k * step, 0), (x, y + k * step, H), st, 0.5, op=0.65)
        k += 1
    # gesims som gir takfølelse
    out += iso.poly([(x, y + dy, H), (x, y, H), (x, y, H + 0.13), (x, y + dy, H + 0.13)], roof, mix(roof, "#2A1500", 0.45), 0.5)
    out += iso.poly([(x, y, H), (x + dx, y, H), (x + dx, y, H + 0.13), (x, y, H + 0.13)], mix(roof, "#FFFFFF", 0.15), mix(roof, "#2A1500", 0.45), 0.5)
    if role == "Grossist":  # gavl som tar imot det avtatte taket
        m = x + dx / 2
        out += iso.poly([(x, y, H + 0.13), (x + dx, y, H + 0.13), (m, y, H + 0.85)], base, edge, 0.5)
        out += iso.line((x, y, H + 0.13), (m, y, H + 0.85), roof, 3)
        out += iso.line((x + dx, y, H + 0.13), (m, y, H + 0.85), roof, 3)
    elif role == "Fabrikk":
        out += iso.tbox(x - 0.45, y - 0.45, 0, 0.4, 0.4, 2.3, FALU)
        out += iso.box(x - 0.45, y - 0.45, 1.8, 0.4, 0.4, 0.17, (WHITE, WHITE, CONCRETE))
    elif role == "Distributør":
        for i in range(int(dx // 0.9)):
            out += iso.poly([(x + 0.2 + i * 0.9, y, 0), (x + 0.8 + i * 0.9, y, 0), (x + 0.8 + i * 0.9, y, 0.8), (x + 0.2 + i * 0.9, y, 0.8)], "#8EA5B0", FJORD_D, 0.5)
    elif role == "Detaljist":
        n = int(dx / 0.3)
        for i in range(n):
            a = x + i * 0.3
            col = WHITE if i % 2 else FALU_L
            out += iso.poly([(a, y, 1.28), (a + 0.3, y, 1.28), (a + 0.3, y + 0.28, 1.05), (a, y + 0.28, 1.05)], col, FALU_D, 0.2)
    if wall_label:
        fill = INK if role in ("Detaljist", "Distributør") else WHITE
        out += iso.wall_text("+x", x + 0.16, y, 1.02, wall_label, label_size, fill)
        if sub_label:
            out += iso.wall_text("+x", x + 0.18, y, 0.48, sub_label, max(13, label_size - 4), fill, 700, "n")
    # paller
    out += bays(iso, x + margin_x, y + margin_y, cols, rows, lager, tally)
    # lav front
    fr = 0.26
    out += iso.box(x, y + dy - 0.1, 0, dx, 0.1, fr, tone(wall), edge, 0.4)
    gate0, gate1 = y + dy * 0.34, y + dy * 0.66
    out += iso.box(x + dx - 0.1, y, 0, 0.1, gate0 - y, fr, tone(wall), edge, 0.4)
    out += iso.box(x + dx - 0.1, gate1, 0, 0.1, y + dy - gate1, fr, tone(wall), edge, 0.4)
    # portstolper
    out += iso.tbox(x + dx - 0.12, gate0 - 0.1, 0, 0.14, 0.1, 0.8, wall)
    out += iso.tbox(x + dx - 0.12, gate1, 0, 0.14, 0.1, 0.8, wall)
    return out, dx, dy


# ---------- 2D-ikoner, tegnet som former ----------
def ic_crate(x, y, s=16, c=OKER):
    k = s / 16
    e = mix(c, "#2A1500", 0.55)
    return G(
        f'<polygon points="8,1 15,4.5 8,8 1,4.5" fill="{mix(c, "#FFFFFF", 0.32)}" stroke="{e}" stroke-width=".8" stroke-linejoin="round"/>'
        f'<polygon points="1,4.5 8,8 8,15.5 1,12" fill="{c}" stroke="{e}" stroke-width=".8" stroke-linejoin="round"/>'
        f'<polygon points="15,4.5 8,8 8,15.5 15,12" fill="{mix(c, "#04202B", 0.2)}" stroke="{e}" stroke-width=".8" stroke-linejoin="round"/>',
        f"translate({x:.1f} {y:.1f}) scale({k:.3f})",
    )


def ic_van(x, y, s=24, body=FJORD, dashed=False, fill=None):
    """Sideprofil av varebil, 24 bred, 13 høy."""
    k = s / 24
    if dashed:
        shape = (
            f'<path d="M1 3.5h13v7.5h-13z M14 5.5h4.5l4 3v2.5h-8.5z" fill="{mix(FALU, "#FFFFFF", 0.9)}" stroke="{FALU}" stroke-width="1.2" stroke-dasharray="2 1.5" stroke-linejoin="round"/>'
            f'<circle cx="6" cy="11.5" r="2" fill="#FFFFFF" stroke="{FALU}" stroke-width="1.1"/><circle cx="18" cy="11.5" r="2" fill="#FFFFFF" stroke="{FALU}" stroke-width="1.1"/>'
        )
    else:
        cargo = fill if fill else OKER
        shape = (
            f'<rect x="1" y="3" width="13" height="8" rx="1" fill="{cargo}" stroke="{mix(cargo, "#2A1500", 0.5)}" stroke-width=".7"/>'
            f'<path d="M14 5.5h4.5l4 3v2.5h-8.5z" fill="{body}"/>'
            f'<rect x="1" y="10.5" width="21.5" height="1.2" fill="#0E2A33"/>'
            f'<circle cx="6" cy="11.5" r="2.1" fill="#0E2A33"/><circle cx="18" cy="11.5" r="2.1" fill="#0E2A33"/>'
        )
    return G(shape, f"translate({x:.1f} {y:.1f}) scale({k:.3f})")


def ic(name, x, y, s=16, c=INK, sw=1.8):
    """Enkle strektegnede ikoner i 16-rute."""
    k = s / 16
    d = {
        "check": "M2.5 8.5l3.6 3.6L13.5 4",
        "clock": "M8 1.8a6.2 6.2 0 1 0 0 12.4 6.2 6.2 0 0 0 0-12.4zM8 4.5V8l2.6 1.6",
        "lock": "M3.5 7.5h9v6.5h-9zM5.2 7.5V5a2.8 2.8 0 0 1 5.6 0v2.5",
        "pause": "M5.5 3v10M10.5 3v10",
        "arrow": "M2.5 8h11M9 3.5L13.5 8 9 12.5",
        "letter": "M1.8 3.8h12.4v8.6H1.8zM2 4l6 5 6-5",
        "upload": "M8 11V2.5M4.5 6L8 2.5 11.5 6M2.5 13.5h11",
        "search": "M7 2.4a4.6 4.6 0 1 0 0 9.2 4.6 4.6 0 0 0 0-9.2zM10.4 10.4l3.4 3.4",
        "warn": "M8 2L14.6 13.6H1.4zM8 6.4v3.6M8 12v.2",
        "x": "M3.5 3.5l9 9M12.5 3.5l-9 9",
        "plus": "M8 3v10M3 8h10",
        "flag": "M3.5 14.5V2M3.5 2.5h9L10 6l2.5 3.5h-9",
        "skip": "M2.5 3l6 5-6 5zM9.5 3l-.0 0M12.5 3v10",
        "refresh": "M13.5 8a5.5 5.5 0 1 1-1.8-4M13.5 2v3.2h-3.2",
        "cal": "M2.5 3.5h11v10h-11zM2.5 6.8h11M5.5 2v2.6M10.5 2v2.6",
        "pin": "M8 14.5s4.6-4.6 4.6-8a4.6 4.6 0 0 0-9.2 0c0 3.4 4.6 8 4.6 8zM8 5v.4",
        "doc": "M3.5 1.8h6l3 3v9.4h-9zM9.5 1.8v3h3M5.6 8.4h4.8M5.6 11h4.8",
        "key": "M10.5 1.8a3.7 3.7 0 1 1-3.3 5.4L2 12.4v2h2.2v-1.6h1.6v-1.6h1.4l1.8-1.8",
        "person": "M8 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM2.5 14.5c.6-3.3 2.8-5 5.5-5s4.9 1.7 5.5 5",
        "chev": "M6 3l5 5-5 5",
        "down": "M3 6l5 5 5-5",
        "chart": "M2 13.8h12M4 11V7M8 11V3M12 11V5.5",
        "grid": "M2.5 2.5h4.5v4.5h-4.5zM9 2.5h4.5v4.5H9zM2.5 9h4.5v4.5h-4.5zM9 9h4.5v4.5H9z",
    }[name]
    return G(PATH(d, stroke=c, sw=sw / max(k, 0.01) * k if False else sw), f"translate({x:.1f} {y:.1f}) scale({k:.3f})")


def ki_badge(x, y, label="KI-spiller", h=20, bg=VIOLET, size=13):
    """Sekskantet KI-merke: form og tekst, aldri bare farge."""
    w = h * 1.25
    pts = f"{x + w * 0.22:.1f},{y:.1f} {x + w * 0.78:.1f},{y:.1f} {x + w:.1f},{y + h / 2:.1f} {x + w * 0.78:.1f},{y + h:.1f} {x + w * 0.22:.1f},{y + h:.1f} {x:.1f},{y + h / 2:.1f}"
    out = f'<polygon points="{pts}" fill="{bg}" stroke="#FFFFFF" stroke-width="1"/>'
    fs = max(13, h * 0.62)
    out += T(x + w / 2, y + h / 2 + fs * 0.36, "KI", fs, 800, WHITE, "b", "middle")
    if label:
        out += T(x + w + 4, y + h * 0.72, label, size, 800, bg, "n")
    return out


def plate(cx, y, s, size=13, fill=WHITE, ink=INK, w=None, h=None, pole=None, weight=800, f="n", stroke=INK):
    """Lite skilt. pole = lengde på stolpe ned til bakken."""
    h = h or size + 8
    w = w or (len(str(s)) * size * 0.56 + 12)
    out = ""
    if pole:
        out += L(cx, y + h, cx, y + h + pole, "#37505B", 2)
    out += R(cx - w / 2, y + 1.2, w, h, 4, "#062430", op=0.25)
    out += R(cx - w / 2, y, w, h, 4, fill, stroke, 0.7)
    out += T(cx, y + h * 0.5 + size * 0.36, s, size, weight, ink, f, "middle")
    return out


def role_icon(role, x, y, s=20, c=None):
    """Silhuett per Rolle: form, ikke farge, bærer identiteten."""
    k = s / 20
    col = c or ROLE_INK[role]
    if role == "Detaljist":
        body = f'<path d="M2 8.5h16V18H2z" fill="{col}"/><path d="M1 8.5L3 3h14l2 5.5z" fill="{col}" opacity=".78"/><rect x="5" y="11" width="4" height="4.5" fill="#fff"/><rect x="11" y="11" width="4" height="7" fill="#fff"/>'
    elif role == "Grossist":
        body = f'<path d="M1.5 9L10 2.5 18.5 9V18h-17z" fill="{col}"/><path d="M6 18v-6.5h8V18z" fill="#fff"/><path d="M6 13.5h8M6 15.7h8" stroke="{col}" stroke-width="1"/>'
    elif role == "Distributør":
        body = f'<rect x="1" y="5" width="18" height="13" fill="{col}"/><rect x="1" y="3.2" width="18" height="2.2" fill="{col}" opacity=".7"/><rect x="3" y="9.5" width="3.8" height="8.5" fill="#fff"/><rect x="8.1" y="9.5" width="3.8" height="8.5" fill="#fff"/><rect x="13.2" y="9.5" width="3.8" height="8.5" fill="#fff"/>'
    else:
        body = f'<path d="M1 18V10l5.5-3.8V10l5.5-3.8V10L18 6v12z" fill="{col}"/><rect x="2" y="1.5" width="3" height="8" fill="{col}"/><rect x="4" y="12.5" width="3" height="3" fill="#fff"/><rect x="9" y="12.5" width="3" height="3" fill="#fff"/><rect x="14" y="12.5" width="3" height="3" fill="#fff"/>'
    return G(body, f"translate({x:.1f} {y:.1f}) scale({k:.3f})")


def logo(x, y, size=26, fill=WHITE):
    """Arbeidsnavn: Kjeden. Tre kasser på en stigende linje, tegnet."""
    out = ic_crate(x, y + size * 0.1, size * 0.8)
    out += T(x + size * 0.95, y + size * 0.82, "Kjeden", size, 800, fill, "b")
    return out


# ---------- Rammer ----------
def phone(pg, x, y, scale, inner, bg=FJORD):
    clip = pg.clip(0, 0, 390, 844, 38)
    body = (
        R(-9, -9, 408, 862, 46, "#0A1E26")
        + R(-9, -9, 408, 862, 46, "none", "#33505B", 1.2)
        + f'<g clip-path="{clip}">{R(0, 0, 390, 844, 0, bg)}{inner}</g>'
    )
    return G(body, f"translate({x} {y}) scale({scale})")


def status_row(fill=WHITE):
    return T(26, 22, "19:42", 13, 800, fill) + R(342, 12, 24, 11, 3, "none", fill, 1.2) + R(344, 14, 15, 7, 1.5, fill)


def demo_line(x, y, fill=MUTED, size=13, a="start"):
    return T(x, y, "Demodata", size, 700, fill, "n", a)
