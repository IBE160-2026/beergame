"""Konsept 05 Tidevann. Genererer 9 SVG-er fra ../_shared/fixture.json.

Bærende grep: kjeden er ÉN sammenhengende linje. All geometri for vannflata kommer
fra kum() og wave(), slik at 1 enhet har samme høyde over og under nullinjen.
"""
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WEEKS = FX["weeks"]
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAVN = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

# Palett
DYP = "#05303A"     # bakgrunn utenfor flatene
HAV = "#08434C"     # over linja
VANN = "#0B5F66"    # under linja
GRUNT = "#167A7E"   # flo, vann over null
HVIT = "#FFFFFF"
SEK = "#CFEDE8"     # sekundærtekst, tonet fra vannet
GUL = "#F0D04E"     # sjøkart-gul: grunne områder, din egen bølge
KORALL = "#FF7A63"  # eneste varselfarge
OKER = "#B9A785"    # tørr grunn
OKER2 = "#8F7E5E"
BLEKK = "#06303A"   # tekst på gul, oker, korall og hvit
RAND = "#2F8A8D"

FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800"
    "&amp;family=Barlow:wght@400;500;600;700&amp;family=Barlow+Semi+Condensed:wght@400;500;600;700&amp;display=swap"
)
STACK = "'Barlow','Segoe UI','Helvetica Neue',Arial,sans-serif"


def luminance(h):
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    x, y = sorted([luminance(a), luminance(b)], reverse=True)
    return (x + 0.05) / (y + 0.05)


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def kr(v):
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",").replace(" ", " ")
    return f"{s} kr"


def wrap(s, width, size, f=0.5):
    maxch = max(1, int(width / (size * f)))
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > maxch:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


class Page:
    def __init__(self, name, w, h, title, desc, bg=DYP):
        self.name, self.w, self.h, self.title, self.desc = name, w, h, title, desc
        self.side = name.split("-", 1)[1]
        self.seq = 0
        self.body = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']

    def uid(self, kind):
        self.seq += 1
        return f"c05-{self.side}-{kind}{self.seq}"

    def add(self, s):
        self.body.append(s)

    def save(self):
        css = (
            f"@import url('{FONT_IMPORT}');"
            ".c05-d{font-family:'Bricolage Grotesque','Trebuchet MS','Segoe UI',sans-serif;letter-spacing:-0.01em}"
            f".c05-t{{font-family:{STACK};font-variant-numeric:tabular-nums lining-nums}}"
            ".c05-c{font-family:'Barlow Semi Condensed','Barlow','Arial Narrow',Arial,sans-serif;"
            "font-variant-numeric:tabular-nums lining-nums}"
        )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" font-family="{STACK}">'
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc><style>{css}</style>"
            + "".join(self.body) + "</svg>"
        )
        (HERE / f"{self.name}.svg").write_text(svg, encoding="utf-8")


# Tekst
def t(x, y, s, size=14, w=400, fill=HVIT, cls="t", a="start", extra=""):
    anchor = "" if a == "start" else f' text-anchor="{a}"'
    return (f'<text x="{n(x)}" y="{n(y)}" class="c05-{cls}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}"{anchor}{" " + extra if extra else ""}>{escape(str(s))}</text>')


def para(x, y, s, width, size=14, lh=None, w=400, fill=HVIT, cls="t", a="start", f=0.5):
    lh = lh or round(size * 1.36)
    return "".join(t(x, y + i * lh, line, size, w, fill, cls, a) for i, line in enumerate(wrap(s, width, size, f)))


def para_h(s, width, size, lh=None, f=0.5):
    lh = lh or round(size * 1.36)
    return len(wrap(s, width, size, f)) * lh


def rect(x, y, w, h, fill="none", rx=0, stroke=None, sw=1, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{rx}" fill="{fill}"{st} {extra}/>'


def line(x1, y1, x2, y2, stroke=HVIT, sw=1, extra=""):
    return f'<line x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def path(d, stroke=HVIT, sw=3.5, fill="none", extra=""):
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def button(x, y, w, h, label, kind="gul", size=18, rx=8):
    if kind == "gul":
        return rect(x, y, w, h, GUL, rx) + t(x + w / 2, y + h / 2 + size * 0.34, label, size, 700, BLEKK, "d", "middle")
    if kind == "korall":
        return rect(x, y, w, h, KORALL, rx) + t(x + w / 2, y + h / 2 + size * 0.34, label, size, 700, BLEKK, "d", "middle")
    return (rect(x, y, w, h, "none", rx, HVIT, 1.5)
            + t(x + w / 2, y + h / 2 + size * 0.34, label, size, 600, HVIT, "d", "middle"))


# Egentegnede ikoner
def fyr(x, base, lit=True, ki=False, s=1.0, ray=19):
    g = [f'<g transform="translate({n(x)},{n(base)}) scale({s})">']
    if lit:
        g.append(f'<path d="M-3,-33 L{-ray},-39 L{-ray},-27 Z M3,-33 L{ray},-39 L{ray},-27 Z" fill="{GUL}" fill-opacity="0.6"/>')
    if lit or ki:
        dash = ' stroke-dasharray="2.5 2"' if ki else ""
        fill = "none" if ki else HVIT
        g.append(f'<path d="M-7,0 L-4.5,-26 L4.5,-26 L7,0 Z" fill="{fill}" stroke="{HVIT}" stroke-width="1.4"{dash}/>')
        if not ki:
            g.append(f'<path d="M-6.1,-11 L-5.6,-17 L5.6,-17 L6.1,-11 Z" fill="{KORALL}"/>')
    else:
        g.append(f'<path d="M-7,0 L-4.5,-26 L4.5,-26 L7,0 Z" fill="none" stroke="{SEK}" stroke-width="1.4"/>')
    edge = HVIT if lit or ki else SEK
    g.append(rect(-6.5, -28, 13, 2, edge))
    lamp = GUL if lit else "none"
    if ki:
        g.append(f'<path d="M0,-38 L4,-35.5 L4,-30.5 L0,-28 L-4,-30.5 L-4,-35.5 Z" fill="{GUL}" stroke="{HVIT}" stroke-width="1"/>')
    else:
        g.append(rect(-3.5, -37, 7, 9, lamp, 0, edge, 1.4))
        g.append(f'<path d="M-4.5,-37 L0,-42 L4.5,-37 Z" fill="{edge}"/>')
    g.append("</g>")
    return "".join(g)


def bouy(x, y, s=1.0, handle=True):
    g = [f'<g transform="translate({n(x)},{n(y)}) scale({s})">']
    g.append(rect(-1.2, -28, 2.4, 16, BLEKK))
    g.append(f'<path d="M-6,-28 L0,-37 L6,-28 Z" fill="{GUL}" stroke="{BLEKK}" stroke-width="1.5"/>')
    g.append(f'<path d="M-10,0 L10,0 L6,-14 L-6,-14 Z" fill="{GUL}" stroke="{BLEKK}" stroke-width="1.5"/>')
    g.append(rect(-7.8, -8, 15.6, 3.6, BLEKK))
    if handle:
        g.append(f'<path d="M-15,-20 L-20,-14 L-15,-8 M15,-20 L20,-14 L15,-8" fill="none" stroke="{GUL}" stroke-width="2" stroke-linecap="round" transform="rotate(90 0 -14)"/>')
    g.append("</g>")
    return "".join(g)


def lock(x, y, c=HVIT, s=1.0):
    return (f'<g transform="translate({n(x)},{n(y)}) scale({s})">'
            f'<path d="M-4.5,-1 V-5 a4.5,4.5 0 0 1 9,0 V-1" fill="none" stroke="{c}" stroke-width="2"/>'
            f'{rect(-7, -1, 14, 10.5, c, 2)}</g>')


def pause_icon(x, y, c=HVIT, s=1.0):
    return f'<g transform="translate({n(x)},{n(y)}) scale({s})">{rect(-6, -8, 4, 16, c, 1)}{rect(2, -8, 4, 16, c, 1)}</g>'


def cross(x, y, c=KORALL, s=1.0):
    return (f'<path transform="translate({n(x)},{n(y)}) scale({s})" d="M-5,-5 L5,5 M5,-5 L-5,5" fill="none" '
            f'stroke="{c}" stroke-width="2.6" stroke-linecap="round"/>')


def check(x, y, c=GUL, s=1.0):
    return (f'<path transform="translate({n(x)},{n(y)}) scale({s})" d="M-6,0 L-2,4.5 L6,-5" fill="none" '
            f'stroke="{c}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>')


def arrow(x1, y1, x2, y2, c=HVIT, sw=2):
    ang = math.atan2(y2 - y1, x2 - x1)
    a = 8
    p1 = (x2 - a * math.cos(ang - 0.5), y2 - a * math.sin(ang - 0.5))
    p2 = (x2 - a * math.cos(ang + 0.5), y2 - a * math.sin(ang + 0.5))
    return (line(x1, y1, x2, y2, c, sw, 'stroke-linecap="round"')
            + f'<path d="M{n(p1[0])},{n(p1[1])} L{n(x2)},{n(y2)} L{n(p2[0])},{n(p2[1])}" fill="none" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')


def hex_mark(x, y, c=HVIT, s=1.0, fill="none"):
    pts = " ".join(f"{n(x + 7 * s * math.cos(math.radians(a)))},{n(y + 7 * s * math.sin(math.radians(a)))}" for a in range(30, 390, 60))
    return f'<polygon points="{pts}" fill="{fill}" stroke="{c}" stroke-width="1.6"/>'


def ki_tag(x, y, label="KI-generert, kan ta feil", c=HVIT, size=13):
    return hex_mark(x + 7, y - 4.5, c) + t(x + 19, y, label, size, 600, c, "c")


def demodata(x, y, a="start", c=SEK, size=13):
    return t(x, y, "Demodata", size, 500, c, "c", a)


def wordmark(x, y, size=24, c=HVIT):
    d = f"M{n(x)},{n(y - size * .28)} c{n(size * .24)},0 {n(size * .24)},{n(-size * .5)} {n(size * .46)},{n(-size * .5)} s{n(size * .2)},{n(size * .5)} {n(size * .5)},{n(size * .5)}"
    return path(d, c, max(2.2, size * 0.11)) + t(x + size * 1.14, y, "Tidevann", size, 700, c, "d")


# Vannflata: én sammenhengende linje
def wave(x0, w, h, y0):
    """Dønning med bratt forside mot kaia. h er mengde x skala, så høyden er sann."""
    return (f"C{n(x0 + .22 * w)},{n(y0)} {n(x0 + .24 * w)},{n(y0 - h)} {n(x0 + .42 * w)},{n(y0 - h)} "
            f"C{n(x0 + .62 * w)},{n(y0 - h)} {n(x0 + .66 * w)},{n(y0)} {n(x0 + w)},{n(y0)}")


def slots(cfg, qs):
    """Dønningens bredde vokser med mengden, så en stor ordre er en stor vannmasse og ikke en nål."""
    x, out = cfg["slot_x"], []
    for q in qs:
        w = (36 + 1.5 * q) * cfg.get("wf", 1)
        out.append((x, w, q))
        x += w
    return out


def geo_of(cfg, qs):
    return [(x, w, q * cfg["sc"]) for x, w, q in slots(cfg, qs)]


def surface(level_y, hole_end, rise_end, y0, swells, x_end, x_start=0.0):
    d = f"M{n(x_start)},{n(level_y)} L{n(hole_end)},{n(level_y)} C{n(hole_end + (rise_end - hole_end) * .55)},{n(level_y)} {n(hole_end + (rise_end - hole_end) * .45)},{n(y0)} {n(rise_end)},{n(y0)} "
    for x0, w, h in swells:
        d += f"L{n(x0)},{n(y0)} " + wave(x0, w, h, y0) + " "
    d += f"L{n(x_end)},{n(y0)}"
    return d


def kum(pg, cfg, st, anim=True):
    """Tegner kummen fra tilstand.

    cfg: sc, y0, stave_w, hole_end, rise_end, slot_x, slot_w, right, top, stave_top, stave_bot, bottom
    st:  lager, rest, swells [(uke, mengde)], draft, sent, ghost_level, tail
    """
    sc, y0 = cfg["sc"], cfg["y0"]
    hs = cfg.get("hs", 1.0)
    level = y0 - st.get("lager", 0) * sc + st.get("rest", 0) * sc
    swells = st.get("swells", [])
    sent = st.get("sent")
    qs = [q for _, q in swells] + ([sent] if sent else [])
    geo = geo_of(cfg, qs)
    d = surface(level, cfg["hole_end"], cfg["rise_end"], y0, geo, cfg["right"])
    tail = st.get("tail", "")
    out = []
    # Vann under linja
    water = d + f" L{cfg['W']},{y0} L{cfg['W']},{cfg['bottom']} L0,{cfg['bottom']} Z"
    wid = pg.uid("vann")
    anim_w = ""
    anim_l = ""
    d_var = None
    if anim and geo and not st.get("from_d"):
        geo2 = [(x - 3, w, max(h - 2, 0) if h else 0) for x, w, h in geo]
        d_var = surface(level, cfg["hole_end"], cfg["rise_end"], y0, geo2, cfg["right"])
        w2 = d_var + f" L{cfg['W']},{y0} L{cfg['W']},{cfg['bottom']} L0,{cfg['bottom']} Z"
        anim_w = f'<animate attributeName="d" dur="7s" repeatCount="indefinite" values="{water};{w2};{water}" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" keyTimes="0;.5;1"/>'
        anim_l = f'<animate attributeName="d" dur="7s" repeatCount="indefinite" values="{d};{d_var};{d}" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" keyTimes="0;.5;1"/>'
    if st.get("from_d"):
        fd = st["from_d"]
        hold = st.get("hold", "0;.34;1")
        fw = fd + f" L{cfg['W']},{y0} L{cfg['W']},{cfg['bottom']} L0,{cfg['bottom']} Z"
        anim_w = f'<animate attributeName="d" dur="5.4s" repeatCount="indefinite" values="{fw};{water};{water}" keyTimes="{hold}" calcMode="spline" keySplines=".16 1 .3 1;0 0 1 1"/>'
        anim_l = f'<animate attributeName="d" dur="5.4s" repeatCount="indefinite" values="{fd};{d};{d}" keyTimes="{hold}" calcMode="spline" keySplines=".16 1 .3 1;0 0 1 1"/>'
    out.append(f'<path id="{wid}" d="{water}" fill="{VANN if not st.get("lager") else VANN}">{anim_w}</path>')
    # Flo: vann over null får lysere tone
    if st.get("lager"):
        cid = pg.uid("flo")
        out.append(f'<clipPath id="{cid}"><path d="{water}"/></clipPath>')
        out.append(f'<rect x="0" y="{n(y0 - 40 * sc)}" width="{cfg["W"]}" height="{n(40 * sc)}" fill="{GRUNT}" clip-path="url(#{cid})"/>')
    # Tørr grunn
    if st.get("rest"):
        he, re_ = cfg["hole_end"], cfg["rise_end"]
        gd = (f"M0,{n(y0)} L{n(re_)},{n(y0)} C{n(he + (re_ - he) * .45)},{n(y0)} {n(he + (re_ - he) * .55)},{n(level)} {n(he)},{n(level)} L0,{n(level)} Z")
        out.append(f'<path d="{gd}" fill="{OKER}"/>')
        # Sprekker i tørr grunn, så tilstanden har mønster og ikke bare farge
        cracks = ""
        for i, frac in enumerate((.3, .55, .8)):
            cx = he * (.62 + i * .13)
            cy = y0 + (level - y0) * frac
            cracks += f"M{n(cx)},{n(cy)} l{n(10 * sc / 6)},{n(4 * sc / 6)} l{n(5 * sc / 6)},{n(-5 * sc / 6)} l{n(9 * sc / 6)},{n(3 * sc / 6)} "
        out.append(path(cracks, OKER2, 1.4))
    # Kai-linje merket 0
    out.append(line(cfg["stave_w"], y0, cfg["right"], y0, SEK, 1.5))
    # Ghost av forrige nivå
    if st.get("ghost") is not None:
        gy = y0 + st["ghost"] * sc
        out.append(line(cfg["stave_w"], gy, cfg["hole_end"], gy, OKER2, 2, 'stroke-dasharray="5 5"'))
    # Den ene linja
    full = d + tail
    extra = anim_l
    if d_var and tail:
        extra = f'<animate attributeName="d" dur="7s" repeatCount="indefinite" values="{d}{tail};{d_var}{tail};{d}{tail}" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" keyTimes="0;.5;1"/>'
    if st.get("from_d") and tail:
        fd = st["from_d"]
        hold = st.get("hold", "0;.34;1")
        extra = f'<animate attributeName="d" dur="5.4s" repeatCount="indefinite" values="{fd}{tail};{d}{tail};{d}{tail}" keyTimes="{hold}" calcMode="spline" keySplines=".16 1 .3 1;0 0 1 1"/>'
    out.append(f'<path d="{full}" fill="none" stroke="{HVIT}" stroke-width="{cfg.get("lw", 3.5)}" stroke-linecap="round" stroke-linejoin="round">{extra}</path>')
    # Din bølge før bekreftelse
    if st.get("draft"):
        q = st["draft"]
        x0, w, _ = slots(cfg, [p for _, p in swells] + [q])[-1]
        dw = f"M{n(x0)},{n(y0)} " + wave(x0, w, q * sc, y0)
        out.append(f'<path d="{dw} Z" fill="{GUL}" fill-opacity="0.22"/>')
        out.append(path(dw, GUL, cfg.get("lw", 3.5), extra='stroke-dasharray="7 6"'))
    # Kaistav
    out.append(stave(cfg, sc, y0))
    return "".join(out), level


def stave(cfg, sc, y0):
    w = cfg["stave_w"]
    top, bot = cfg["stave_top"], cfg["stave_bot"]
    step = cfg.get("step", 5)
    s = [rect(0, top, w, bot - top, HVIT)]
    lo = int((y0 - bot) / sc)
    hi = int((y0 - top) / sc)
    size = cfg.get("stave_size", 13)
    for u in range(lo, hi + 1):
        y = y0 - u * sc
        if y < top + 1 or y > bot - 1:
            continue
        major = u % step == 0
        if major:
            s.append(rect(w - 8, y - 1.2, 8, 2.4, BLEKK))
            label = "0" if u == 0 else (f"−{-u}" if u < 0 else str(u))
            s.append(t(w - 10, y + size * .36, label, size, 700 if u == 0 else 600, BLEKK, "c", "end"))
        elif cfg.get("minor", True):
            s.append(rect(w - 4, y - .5, 4, 1, BLEKK))
    return "".join(s)


PHONE = dict(W=390, sc=6, y0=306, stave_w=32, hole_end=132, rise_end=174, slot_x=176, wf=1.0,
             right=384, stave_top=156, stave_bot=432, bottom=844)


def seat_status(uke=11):
    return [("Detaljist", "Ida", "Har bestilt", True, False),
            ("Grossist", "Sara", "Venter: deg", False, False),
            ("Distributør", "Mikkel", "Har bestilt", True, False),
            ("Fabrikk", "Jonas", "Venter 3 min", False, False)]


def strip(lights, y=124, w=390):
    col = (w - 8) / 4
    s = []
    for i, (rolle, navn, status, lit, ki) in enumerate(lights):
        x = 8 + i * col
        s.append(fyr(x + 11, y, lit, ki, 1.0, ray=10))
        s.append(t(x + 25, y - 43, rolle, 13, 600, HVIT, "c"))
        s.append(t(x + 25, y - 27, navn, 13, 400, SEK, "c"))
        s.append(t(x + 25, y - 11, status, 13, 400, HVIT if lit or ki else SEK, "c"))
    return "".join(s)


def data_cell(x, y, label, value, size=30, hi=False):
    s = t(x, y, label, 13, 500, SEK, "c")
    s += t(x, y + 30, value, size, 700, GUL if hi else HVIT, "d")
    return s


def history(x, y, hist, first=1, w=372):
    cols = len(hist)
    x0 = x + 44
    cw = (w - x0) / cols
    s = t(x, y, "Uke", 13, 500, SEK, "c") + t(x, y + 20, "Ordre", 13, 500, SEK, "c")
    for i, v in enumerate(hist):
        cx = x0 + cw * (i + .5)
        s += t(cx, y, first + i, 13, 400, SEK, "t", "middle")
        big = v > 4
        s += t(cx, y + 20, v, 15, 700 if big else 500, HVIT, "t", "middle")
    return s


def phone_open(pg, x, y, s, screen_bg=HAV):
    cid = pg.uid("skjerm")
    return (f'<g transform="translate({n(x)},{n(y)}) scale({s})">'
            f'<clipPath id="{cid}"><rect width="390" height="844" rx="38"/></clipPath>'
            f'<g clip-path="url(#{cid})"><rect width="390" height="844" fill="{screen_bg}"/>')


def phone_close():
    return f'</g><rect width="390" height="844" rx="38" fill="none" stroke="{SEK}" stroke-width="2.5"/></g>'


def game_header(uke, rolle="Grossist", spill=17):
    return (t(18, 50, f"Uke {uke}", 34, 800, HVIT, "d")
            + t(372, 33, rolle, 17, 700, HVIT, "d", "end")
            + t(372, 52, f"Spill {spill}", 13, 400, SEK, "c", "end"))


def game_screen(pg, st, cfg=PHONE, exit_right=False):
    """Telefonen i 390x844-koordinater."""
    y0 = cfg["y0"]
    out = [game_header(st["uke"])]
    chain_y = 124
    tail = f" Q384,{y0} 384,{y0 - 10} L384,{chain_y + 10} Q384,{chain_y} 374,{chain_y} L0,{chain_y}"
    st = dict(st)
    st["tail"] = tail
    drawn, level = kum(pg, cfg, st, anim=st.get("anim", True))
    out.append(drawn)
    if exit_right:
        out.append(line(384, chain_y, 392, chain_y, HVIT, 3.5))
    if st.get("lights"):
        out.append(strip(st["lights"], chain_y))
    if st.get("top_note"):
        out.append(st["top_note"])
    sc = cfg["sc"]
    # I situ: lager og restordre
    if st.get("rest"):
        out.append(t(40, y0 - 9, f"Lager {st.get('lager', 0)}", 15, 700, HVIT, "t"))
        out.append(t(40, y0 + 17, "Restordre", 14, 700, BLEKK, "t"))
        rest_size = 62 if st["rest"] < 16 else 84
        out.append(t(40, level - 10, st["rest"], rest_size, 800, BLEKK, "d"))
    elif st.get("lager"):
        out.append(t(40, y0 - 10, "Lager", 15, 700, HVIT, "t"))
        out.append(t(40, y0 - 30, st["lager"], 70, 800, HVIT, "d"))
        out.append(t(40, y0 + 18, "Restordre 0", 14, 700, HVIT, "t"))
    # Dønninger
    allsw = list(st.get("swells", []))
    own = st.get("draft") or st.get("sent")
    sl = slots(cfg, [q for _, q in allsw] + ([own] if own else []))
    for i, (u, q) in enumerate(allsw):
        x0, w, _ = sl[i]
        crest = x0 + .42 * w
        out.append(t(crest, y0 - q * sc - 7, q, 22, 800, HVIT, "d", "middle"))
        out.append(t(x0 + w / 2, y0 + 17, f"Uke {u}", 13, 500, HVIT, "c", "middle"))
    if own:
        x0, w, _ = sl[-1]
        crest = x0 + .42 * w
        col = GUL
        out.append(t(crest - 18, y0 - own * sc + 24, own, 30, 800, col, "d", "end"))
        out.append(t(x0 + w / 2, y0 + 17, f"Uke {st['own_uke']}", 13, 700, GUL, "c", "middle"))
        if st.get("draft"):
            out.append(bouy(crest, y0 - own * sc + 2, 0.9))
    # På vei-klamme
    pv = st.get("pv_label")
    if pv is not None and allsw:
        count = len(allsw) + (1 if st.get("sent") else 0)
        bx0 = sl[0][0] + 4
        bx1 = sl[count - 1][0] + sl[count - 1][1] - 4
        by = y0 + 28
        out.append(f'<path d="M{n(bx0)},{by - 4} L{n(bx0)},{by} L{n(bx1)},{by} L{n(bx1)},{by - 4}" fill="none" stroke="{HVIT}" stroke-width="1.6"/>')
        out.append(t((bx0 + bx1) / 2, by + 24, f"På vei {pv}", 21, 700, HVIT, "d", "middle"))
    if st.get("kum_note"):
        out.append(st["kum_note"])
    # Tabell
    y = 454
    cols = [18, 146, 268]
    out.append(data_cell(cols[0], y, "Innkommende ordre", st["inn"], hi=st.get("hi_inn")))
    out.append(data_cell(cols[1], y, "Levering", st["lev"], hi=st.get("hi_lev")))
    out.append(data_cell(cols[2], y, "Sendt", st["sendt"]))
    y2 = y + 52
    out.append(data_cell(cols[0], y2, "På vei", st["pv"]))
    out.append(data_cell(cols[1], y2, "Neste levering", st["neste"]))
    out.append(data_cell(cols[2], y2, "Totalkostnad", n_kr(st["kost"]), size=22))
    out.append(line(18, 567, 372, 567, RAND, 1))
    out.append(history(18, 584, st["hist"], st.get("hist_first", 1)))
    if st.get("lower"):
        out.append(st["lower"])
    return "".join(out)


def n_kr(v):
    return kr(v)


def order_input(uke, value=None, tidligst=None):
    y = 636
    s = t(18, y, f"Din ordre for Uke {uke}", 16, 700, HVIT, "d")
    if tidligst:
        s += t(372, y, f"inne tidligst Uke {tidligst}", 13, 500, SEK, "c", "end")
    fy = y + 10
    s += f'<circle cx="46" cy="{fy + 30}" r="28" fill="none" stroke="{HVIT}" stroke-width="2"/>' + line(36, fy + 30, 56, fy + 30, HVIT, 3, 'stroke-linecap="round"')
    s += f'<circle cx="344" cy="{fy + 30}" r="28" fill="none" stroke="{HVIT}" stroke-width="2"/>' + line(334, fy + 30, 354, fy + 30, HVIT, 3, 'stroke-linecap="round"') + line(344, fy + 20, 344, fy + 40, HVIT, 3, 'stroke-linecap="round"')
    s += rect(84, fy, 222, 60, HVIT, 8)
    if value is not None:
        s += t(195, fy + 46, value, 48, 800, BLEKK, "d", "middle")
        s += t(296, fy + 37, "kasser", 14, 500, BLEKK, "t", "end")
        s += rect(222, fy + 11, 2.2, 38, BLEKK)
        by = fy + 70
        s += button(18, by, 354, 58, f"Send ut {value} kasser", "gul", 22)
        s += t(195, by + 80, "Ordren kan ikke endres etterpå.", 14, 500, SEK, "t", "middle")
    else:
        s += rect(195, fy + 11, 2.2, 38, BLEKK)
        s += t(296, fy + 37, "kasser", 14, 500, BLEKK, "t", "end")
        by = fy + 70
        s += rect(18, by, 354, 58, "none", 8, SEK, 1.5) + t(195, by + 37, "Velg et tall, eller dra bøyen", 18, 600, SEK, "d", "middle")
        s += t(195, by + 80, "Du bestemmer. Systemet regner.", 14, 500, SEK, "t", "middle")
    return s


# Tilstander fra fixture
def seat(week, role="Grossist"):
    return WEEKS[week - 1]["seats"][role]


def arrivals(week, role="Grossist"):
    """Det som er på vei etter ukens ordre er summen av de neste leveringene i fixture."""
    return [(u, seat(u, role)["levering"]) for u in range(week + 1, week + 4)]


S11 = seat(11)
SWELLS_11 = arrivals(11)
assert sum(q for _, q in SWELLS_11) == S11["paa_vei_foer_ordre"] == 16, "På vei må stemme med dønningene"
HIST_11 = [seat(u)["ordre"] for u in range(1, 11)]
assert HIST_11 == [4, 4, 4, 4, 4, 4, 4, 4, 4, 8]


def base_state():
    return dict(uke=11, lager=S11["lager"], rest=S11["restordre"], inn=S11["innkommende_ordre"], lev=S11["levering"],
                sendt=S11["sendt"], pv=S11["paa_vei_foer_ordre"], neste=S11["neste_levering"], kost=S11["kost_sum"],
                hist=HIST_11, swells=SWELLS_11, pv_label=16, lights=seat_status(), own_uke=15)


# 05 Spill
def page_spill():
    pg = Page("05-spill", 1600, 1000, "Tidevann: spillskjermen i Uke 11",
              "Saras telefon og laptop i Uke 11. Lager er vann over nullinjen, Restordre 13 er tørr grunn under, "
              "tre dønninger på 4, 4 og 8 er På vei 16, og Saras ordre på 24 er en gul stiplet bølge i samme skala.")
    pg.add(t(50, 58, "Hovedskjermen: samme skala over og under null", 34, 800, HVIT, "d"))
    pg.add(t(50, 86, "Sara, Grossist, Spill 17. Uke 11 med 24 tastet inn. Hele skjermen er et snitt av vann, og ett heltall er alt Sara bestemmer.", 17, 400, SEK, "t"))
    pg.add(demodata(1550, 58, "end", size=14))
    st = base_state()
    st["draft"] = 24
    st["lower"] = order_input(11, 24, 15)
    pg.add(phone_open(pg, 50, 118, 1.0))
    pg.add(game_screen(pg, st))
    pg.add(phone_close())

    # Laptop
    lx, ly, lw, lh = 500, 136, 1050, 700
    pg.add(rect(lx - 12, ly - 12, lw + 24, lh + 24, DYP, 18, SEK, 2.5))
    cid = pg.uid("laptop")
    pg.add(f'<g transform="translate({lx},{ly})"><clipPath id="{cid}"><rect width="{lw}" height="{lh}" rx="6"/></clipPath><g clip-path="url(#{cid})">')
    pg.add(rect(0, 0, lw, lh, HAV))
    # Venstre: kummen
    cfg = dict(W=760, sc=9, y0=376, stave_w=42, hole_end=238, rise_end=300, slot_x=304, wf=2.0, right=724,
               stave_top=140, stave_bot=524, bottom=lh, stave_size=14, minor=True, lw=4)
    chain = 112
    st2 = dict(base_state(), draft=24)
    st2["tail"] = f" Q740,{cfg['y0']} 740,{cfg['y0'] - 14} L740,{chain + 14} Q740,{chain} 726,{chain} L0,{chain}"
    # Forleng linja til høyre kant av kummen, så halen starter riktig
    drawn, level = kum(pg, cfg, st2)
    pg.add(rect(760, 0, lw - 760, lh, DYP))
    pg.add(drawn)
    pg.add(t(24, 46, "Uke 11", 36, 800, HVIT, "d"))
    pg.add(t(150, 34, "Grossist", 18, 700, HVIT, "d") + t(150, 53, "Spill 17", 14, 400, SEK, "c"))
    colw = 182
    for i, (rolle, navn, status, lit, ki) in enumerate(seat_status()):
        x = 32 + i * colw
        pg.add(fyr(x, chain, lit, ki, 1.0, ray=12))
        pg.add(t(x + 20, chain - 28, f"{rolle} · {navn}", 14, 600, HVIT, "c"))
        pg.add(t(x + 20, chain - 10, status, 14, 400, HVIT if lit else SEK, "c"))
    y0 = cfg["y0"]
    sc = cfg["sc"]
    pg.add(t(54, y0 - 12, "Lager 0", 20, 700, HVIT, "t"))
    pg.add(t(54, y0 + 22, "Restordre", 18, 700, BLEKK, "t"))
    pg.add(t(54, level - 14, 13, 84, 800, BLEKK, "d"))
    sl = slots(cfg, [q for _, q in SWELLS_11] + [24])
    for i, (u, q) in enumerate(SWELLS_11):
        x0, w, _ = sl[i]
        crest = x0 + .42 * w
        pg.add(t(crest, y0 - q * sc - 10, q, 30, 800, HVIT, "d", "middle"))
        pg.add(t(x0 + w / 2, y0 + 22, f"Uke {u}", 15, 500, HVIT, "c", "middle"))
    x0, w, _ = sl[3]
    crest = x0 + .42 * w
    pg.add(t(crest - 30, y0 - 24 * sc + 36, 24, 44, 800, GUL, "d", "end"))
    pg.add(t(x0 + w / 2, y0 + 22, "Uke 15", 15, 700, GUL, "c", "middle"))
    pg.add(bouy(crest, y0 - 24 * sc + 2, 1.0))
    bx0, bx1, by = sl[0][0] + 6, sl[2][0] + sl[2][1] - 6, y0 + 36
    pg.add(f'<path d="M{bx0},{by - 5} L{bx0},{by} L{bx1},{by} L{bx1},{by - 5}" fill="none" stroke="{HVIT}" stroke-width="1.8"/>')
    pg.add(t((bx0 + bx1) / 2, by + 32, "På vei 16", 28, 700, HVIT, "d", "middle"))
    # Ordrehistorikk under kummen
    hy = 560
    pg.add(t(24, hy, "Dine ordre", 15, 700, HVIT, "t"))
    x0h = 124
    cw = 58
    for i, v in enumerate(HIST_11):
        cx = x0h + cw * i
        pg.add(t(cx, hy + 26, f"Uke {i + 1}", 14, 400, SEK, "c", "middle"))
        pg.add(t(cx, hy + 54, v, 21, 700, HVIT, "t", "middle"))
    pg.add(f'<path d="M{x0h - 20},{hy + 66} L{x0h - 20},{hy + 72} L{x0h + 3 * cw + 20},{hy + 72} L{x0h + 3 * cw + 20},{hy + 66}" fill="none" stroke="{SEK}" stroke-width="1.5"/>')
    pg.add(t(x0h + 1.5 * cw, hy + 92, "Veiledede uker", 14, 500, SEK, "c", "middle"))
    # Høyre: tall og ordre
    rx = 788
    y = 44
    rows = [("Innkommende ordre", S11["innkommende_ordre"]), ("Levering", S11["levering"]), ("Sendt", S11["sendt"]),
            ("På vei", S11["paa_vei_foer_ordre"]), ("Neste levering", S11["neste_levering"])]
    pg.add(t(rx, y, "Denne uka", 19, 700, HVIT, "d"))
    y += 34
    for label, v in rows:
        pg.add(t(rx, y, label, 16, 500, SEK, "t") + t(lw - 28, y + 2, v, 26, 700, HVIT, "t", "end"))
        pg.add(line(rx, y + 13, lw - 28, y + 13, RAND, 1))
        y += 46
    pg.add(t(rx, y, "Totalkostnad", 16, 500, SEK, "t") + t(lw - 28, y + 2, kr(S11["kost_sum"]), 22, 700, HVIT, "t", "end"))
    y += 62
    pg.add(t(rx, y, "Din ordre for Uke 11", 19, 700, HVIT, "d"))
    y += 14
    pg.add(rect(rx, y, lw - 28 - rx, 76, HVIT, 8) + t((rx + lw - 28) / 2, y + 58, 24, 60, 800, BLEKK, "d", "middle"))
    pg.add(t(lw - 42, y + 45, "kasser", 15, 500, BLEKK, "t", "end"))
    y += 88
    pg.add(button(rx, y, lw - 28 - rx, 60, "Send ut 24 kasser", "gul", 22))
    pg.add(t((rx + lw - 28) / 2, y + 86, "Ordren kan ikke endres etterpå.", 14, 500, SEK, "t", "middle"))
    pg.add(t((rx + lw - 28) / 2, y + 108, "Dra bøyen eller skriv tallet.", 14, 500, SEK, "t", "middle"))
    pg.add("</g></g>")
    # Laptop-fot
    pg.add(f'<path d="M{lx - 12},{ly + lh + 14} L{lx + lw + 12},{ly + lh + 14} L{lx + lw + 30},{ly + lh + 36} L{lx - 30},{ly + lh + 36} Z" fill="{HAV}" stroke="{SEK}" stroke-width="2"/>')
    pg.add(t(lx, ly + lh + 76, "Stående telefon er grunnformen. På bred skjerm blir kummen større, ikke annerledes. 1 enhet er alltid like høy over og under null.", 16, 400, SEK, "t"))
    pg.add(t(lx, ly + lh + 100, "Alle verdier står også som tall. Hva Sara ikke ser: hvor mange uker som gjenstår, kundens etterspørsel, de andres Lager og ordre.", 16, 400, SEK, "t"))
    pg.save()


# 06 Spilldynamikk
def frame_end(pg, base=372):
    """(F) Spillet slutter. Rollene står på linja, kostnaden som dybde under dem."""
    s = [rect(0, 0, 390, 844, HAV)]
    s.append(t(18, 56, "Spillet er ferdig", 30, 800, HVIT, "d"))
    s.append(t(18, 84, "Uke 36 var siste Uke.", 15, 400, SEK, "t"))
    s.append(f'<path d="M0,{base} L390,{base} L390,844 L0,844 Z" fill="{VANN}"/>')
    s.append(t(18, 150, "Kjeden totalt", 18, 600, HVIT, "t"))
    s.append(t(18, 212, kr(FX["chain_total_cost"]), 58, 800, HVIT, "d"))
    s.append(t(18, 250, "Kostnaden er kjedens, ikke én persons.", 16, 500, HVIT, "t"))
    s.append(t(18, 274, "Slik fordelte den seg på Rollene:", 16, 400, SEK, "t"))
    colw = 88
    costs = FX["total_cost_per_role"]
    for i, r in enumerate(ROLES):
        x = 62 + i * colw
        s.append(fyr(x, base, True, False, 1.3, ray=15))
        s.append(t(x, base + 22, r, 14, 600, HVIT, "c", "middle"))
        s.append(t(x, base + 39, NAVN[r], 14, 400, SEK, "c", "middle"))
        s.append(t(x, base + 64, kr(costs[r]), 16, 700, HVIT, "t", "middle"))
        depth = costs[r] * 0.21
        s.append(rect(x - 22, base + 76, 44, depth, GRUNT, 0, HVIT, 1.2))
    s.append(path(f"M0,124 Q7,124 7,134 L7,{base - 10} Q7,{base} 17,{base} L392,{base}", HVIT, 3.5))
    s.append(button(18, 640, 354, 60, "Gå til Debrief", "gul", 22))
    s.append(t(195, 728, "Dere kan åpne Debriefen sammen.", 15, 500, HVIT, "t", "middle"))
    s.append(t(195, 750, "Hver skriver sin Forklaring først.", 15, 400, SEK, "t", "middle"))
    return "".join(s)


def page_dyn():
    pg = Page("06-spilldynamikk", 2100, 1200, "Tidevann: spilldynamikken i seks ruter",
              "Seks telefoner i samme vannlinje: Uka åpner, beslutningen på 24 med 16 på vei, venter på de andre under "
              "fire fyrlykter, tidevannet skifter under 2 sekunder, Jonas erstattes av en merket KI-spiller, spillet slutter med kjedens totalkostnad.")
    pg.add(t(60, 62, "Spilldynamikken: én linje gjennom hele uka", 36, 800, HVIT, "d"))
    pg.add(demodata(2040, 62, "end", size=14))
    sc = 0.80
    fw = 390 * sc
    gap = (1980 - 6 * fw) / 5
    y = 92
    xs = [60 + i * (fw + gap) for i in range(6)]
    # Linja over mellomrommene
    cy = y + 124 * sc
    for i in range(5):
        pg.add(line(xs[i] + fw - 2, cy, xs[i + 1] + 2, cy, HVIT, 2.7))
    Q11 = [q for _, q in SWELLS_11]

    # A
    a = base_state()
    a["ghost"] = seat(10)["restordre"]
    a["hi_inn"] = a["hi_lev"] = True
    a["from_d"] = surface(PHONE["y0"] + 9 * 6, PHONE["hole_end"], PHONE["rise_end"], PHONE["y0"], geo_of(PHONE, Q11), 384)
    a["kum_note"] = t(40, 408, "Var 9. Ordre 8 inn, levering 4 inn: nå 13.", 15, 600, HVIT, "t")
    a["lower"] = order_input(11)
    # B
    b = base_state()
    b["draft"] = 24
    b["lower"] = order_input(11, 24, 15)
    # C
    c = base_state()
    c["sent"] = 24
    c["pv"] = 40
    c["pv_label"] = 40
    c["lights"] = None
    c["hist"] = HIST_11[1:] + [24]
    c["hist_first"] = 2
    geo_flat = geo_of(PHONE, Q11 + [24])
    geo_flat[-1] = (geo_flat[-1][0], geo_flat[-1][1], 0)
    c["from_d"] = surface(PHONE["y0"] + 13 * 6, PHONE["hole_end"], PHONE["rise_end"], PHONE["y0"], geo_flat, 384)
    c["top_note"] = (lock(26, 92) + t(42, 92, "Ordre 24 sendt ut", 19, 700, HVIT, "d") + t(42, 112, "Kan ikke endres. Inne tidligst Uke 15.", 13, 500, SEK, "c"))
    lights = [("Detaljist", "Ida", "Har bestilt", True, False), ("Grossist", "Sara", "Du har bestilt", True, False),
              ("Distributør", "Mikkel", "Har bestilt", True, False), ("Fabrikk", "Jonas", "Venter, 3 min", False, False)]
    low = t(18, 634, "Venter på Jonas, Fabrikk", 21, 800, HVIT, "d") + t(372, 634, "3 min", 21, 700, HVIT, "t", "end")
    coast = 722
    low += line(384, 306, 384, coast - 10, HVIT, 3.5) + path(f"M384,{coast - 10} Q384,{coast} 374,{coast} L0,{coast}", HVIT, 3.5)
    for i, (rolle, navn, status, lit, ki) in enumerate(lights):
        cx = 54 + i * 94
        low += fyr(cx, coast, lit, ki, 1.5)
        low += t(cx, coast + 22, rolle, 14, 600, HVIT, "c", "middle")
        low += t(cx, coast + 40, navn, 14, 400, SEK, "c", "middle")
        low += t(cx, coast + 58, status, 13, 400, HVIT if lit else SEK, "c", "middle")
    low += t(195, coast + 90, "Uka går videre når alle fire har bestilt.", 14, 500, SEK, "t", "middle")
    c["lower"] = low
    # D
    s12 = seat(12)
    d = dict(uke=12, lager=0, rest=s12["restordre"], inn=s12["innkommende_ordre"], lev=s12["levering"], sendt=s12["sendt"],
             pv=s12["paa_vei_foer_ordre"], neste=s12["neste_levering"], kost=s12["kost_sum"],
             hist=[seat(u)["ordre"] for u in range(2, 12)], hist_first=2,
             swells=[(13, 4), (14, 8), (15, 24)], pv_label=36, own_uke=None, lights=None)
    assert 4 + 8 + 24 == s12["paa_vei_foer_ordre"]
    # Forrige posisjon: de samme dønningene én plass lenger ute, nivå -13
    d["from_d"] = surface(PHONE["y0"] + 13 * 6, PHONE["hole_end"], PHONE["rise_end"], PHONE["y0"], geo_of(PHONE, Q11 + [24])[1:], 384)
    d["hold"] = "0;.33;1"
    d["top_note"] = (t(18, 92, "Tidevannet skifter", 19, 700, HVIT, "d") + t(18, 112, "Alt rykker én uke inn mot kaia. Under 2 sek.", 13, 500, SEK, "c"))
    d["ghost"] = 13
    lowd = arrow(262, 214, 190, 214, HVIT, 2.4) + t(226, 204, "Inn mot kaia", 13, 600, HVIT, "c", "middle")
    lowd += button(18, 640, 354, 58, "Hopp over", "ut", 20)
    lowd += t(195, 724, "Levering 4 fylte på. Ordre 11 tok mer.", 15, 500, HVIT, "t", "middle")
    lowd += t(195, 746, "Tørr grunn gikk fra 13 til 20.", 15, 500, HVIT, "t", "middle")
    lowd += t(195, 770, "Bølgen din er nå 3 uker unna.", 15, 400, SEK, "t", "middle")
    d["lower"] = lowd
    # E
    s27 = seat(27)
    e = dict(uke=27, lager=s27["lager"], rest=0, inn=s27["innkommende_ordre"], lev=s27["levering"], sendt=s27["sendt"],
             pv=s27["paa_vei_foer_ordre"], neste=s27["neste_levering"], kost=s27["kost_sum"],
             hist=[seat(u)["ordre"] for u in range(17, 27)], hist_first=17,
             swells=arrivals(27), pv_label=s27["paa_vei_foer_ordre"], own_uke=None,
             lights=[("Detaljist", "Ida", "Har bestilt", True, False), ("Grossist", "Sara", "Venter: deg", False, False),
                     ("Distributør", "Mikkel", "Har bestilt", True, False), ("Fabrikk", "KI-spiller", "for Jonas", True, True)])
    assert sum(q for _, q in e["swells"]) == s27["paa_vei_foer_ordre"]
    lowe = pause_icon(28, 630) + t(44, 636, "Pause: fortsetter to. 14:15", 18, 700, HVIT, "d")
    lowe += hex_mark(25, 653, GUL) + t(44, 658, "Jonas kom ikke. Sara satte inn KI-spiller.", 14, 500, HVIT, "c")
    lowe += t(44, 676, "Fabrikk er merket KI til setet tas tilbake.", 14, 400, SEK, "c")
    lowe += rect(18, 688, 354, 124, DYP, 10, SEK, 1.5)
    lowe += t(34, 714, "På Jonas sin telefon", 14, 600, SEK, "c")
    lowe += t(34, 736, "KI-spiller holder setet ditt.", 16, 700, HVIT, "d")
    lowe += button(34, 748, 322, 50, "Ta tilbake setet", "gul", 19)
    e["lower"] = lowe

    frames = [
        ("A", a, "Uka åpner", "Levering og ordre kommer inn. Vannet trekker seg: 9 blir 13. Du leser tilstanden før du leser et tall."),
        ("B", b, "Beslutningen", "Du drar bøyen opp eller taster 24. Bølgen din reiser seg ved siden av de 16 som allerede ruller inn, i samme skala."),
        ("C", c, "Bekreftet", "Bølgen går ut og låses. Fire fyrlykter viser hvem som har bestilt, og Jonas er den slukkede, i 3 minutter."),
        ("D", d, "Uka går videre", "Ett tidevannsskift: alt rykker én uke inn. Stiplet linje viser forrige nivå. Kortere enn 2 sek, og kan hoppes over."),
        ("E", e, "Jonas er borte", "Pause holder klokka. Når avtalen ryker, står fyret stiplet med sekskant og navnet KI-spiller. Jonas kan ta setet tilbake."),
        ("F", None, "Spillet slutter", "Kjedens tall kommer først. Rollene står etterpå, langs samme linje, og neste steg er Debrief."),
    ]
    for i, (key, st, title, note) in enumerate(frames):
        x = xs[i]
        pg.add(phone_open(pg, x, y, sc))
        if st is None:
            pg.add(frame_end(pg))
        else:
            pg.add(game_screen(pg, st, exit_right=True))
        pg.add(phone_close())
        ny = y + 844 * sc + 34
        pg.add(t(x, ny, f"{key}. {title}", 22, 800, HVIT, "d"))
        pg.add(para(x, ny + 26, note, fw - 4, 16, 22, 400, SEK, "t", f=.48))
    # Unikt
    ty = 958
    pg.add(line(60, ty - 34, 2040, ty - 34, RAND, 1))
    pg.add(t(60, ty, "Det spilleren føler", 24, 800, HVIT, "d"))
    txt = ("Du leser vannet før du leser tallene: tørr grunn under null er en mangel du kan se, og det som er på vei står som dønninger på samme skala. "
           "Derfor er feilen synlig med øynene i det du gjør den: bølgen på 24 reiser seg over tre dønninger som allerede summerer til mer enn hullet på 13. "
           "Dønningene kommer alltid, men bare etter forsinkelsen, så utålmodigheten kjennes uke etter uke. "
           "Skiftet er under 2 sekunder og kan hoppes over, så 36 uker over flere kvelder blir en rytme og ikke en venteskjerm.")
    pg.add(para(60, ty + 34, txt, 880, 18, 26, 400, HVIT, "t", f=.47))
    # Saras 36 uker, samme linje videre fra rute F. Vises aldri under spill.
    cx0, cx1, cy0, usc = 1040, 2000, 1046, 2.5
    wx = lambda i: cx0 + i * (cx1 - cx0) / 35
    lv = [seat(u)["lager"] - seat(u)["restordre"] for u in range(1, 37)]
    pg.add(t(cx0, ty - 2, "Saras linje, Uke 1 til 36. Spilleren ser den samlet først i Debrief.", 16, 600, HVIT, "c"))
    pts = [(wx(i), cy0 - v * usc) for i, v in enumerate(lv)]
    poly = " L".join(f"{n(x_)},{n(y_)}" for x_, y_ in pts)
    pg.add(f'<path d="M{n(cx0)},{cy0} L{poly} L{n(cx1)},{cy0} Z" fill="{VANN}"/>')
    neg = " L".join(f"{n(x_)},{n(max(y_, cy0))}" for x_, y_ in pts)
    pg.add(f'<path d="M{n(cx0)},{cy0} L{neg} L{n(cx1)},{cy0} Z" fill="{OKER}"/>')
    pg.add(line(cx0, cy0, cx1, cy0, SEK, 1.5))
    pg.add(t(cx0 - 8, cy0 + 5, "0", 15, 700, HVIT, "t", "end"))
    # Rute F fortsetter ned i kurven fra høyre
    fx_end = xs[5] + fw
    fy_end = y + 372 * sc
    d = f"M{n(fx_end)},{n(fy_end)} Q2062,{n(fy_end)} 2062,{n(fy_end + 18)} L2062,{n(pts[-1][1] - 18)} Q2062,{n(pts[-1][1])} 2044,{n(pts[-1][1])} L{n(pts[-1][0])},{n(pts[-1][1])}"
    d += " " + " ".join(f"L{n(x_)},{n(y_)}" for x_, y_ in reversed(pts[:-1]))
    pg.add(path(d, HVIT, 2.7))
    for wk in (11, 12, 27, 36):
        x_, y_ = pts[wk - 1]
        if wk in (11, 12):
            pg.add(line(x_, y_, x_, cy0 - 10, GUL, 1.4))
        pg.add(f'<circle cx="{n(x_)}" cy="{n(y_)}" r="4.5" fill="{GUL}" stroke="{BLEKK}" stroke-width="1"/>')
    pg.add(t(pts[10][0] - 4, cy0 - 16, "A B C", 15, 800, GUL, "d", "end"))
    pg.add(t(pts[11][0] + 4, cy0 - 16, "D", 15, 800, GUL, "d"))
    pg.add(t(pts[26][0] - 4, pts[26][1] - 10, "E", 15, 800, GUL, "d", "end"))
    pg.add(t(pts[35][0], pts[35][1] - 12, "F", 15, 800, GUL, "d", "middle"))
    pk = min(range(36), key=lambda i: lv[i])
    pg.add(t(pts[pk][0], pts[pk][1] + 20, f"Restordre {-lv[pk]}, Uke {pk + 1}", 14, 600, HVIT, "c", "middle"))
    mx = max(range(36), key=lambda i: lv[i])
    pg.add(t(pts[mx][0] - 8, pts[mx][1] - 10, f"Lager {lv[mx]}, Uke {mx + 1}", 14, 600, HVIT, "c"))
    pg.add(t(cx0, 1178, "Ved utslag over kummens høyde rulles staven. Tallene endres aldri.", 15, 400, SEK, "t"))
    pg.save()


# Debrief: tidevannsdiagram i etasjer med én linje
def series(role):
    if role == "Kunde":
        return [w["demand"] for w in WEEKS]
    return [w["seats"][role]["ordre"] for w in WEEKS]


def floors(x, y, w, sc, label_size=13, gap=16, show_amp=True, x_pad=0, lw=2.6, label_x=None, amp_x=None, lab_w=0):
    """Fem etasjer: Kunde nederst, Fabrikk øverst. Alt er samme skala og én eneste path.

    Linja går fra venstre til høyre gjennom Kunde, svinger opp, går tilbake langs neste etasjes nullinje,
    og fortsetter som neste etasjes ordre. Datum og serie er samme strek.
    """
    order = ["Fabrikk", "Distributør", "Grossist", "Detaljist", "Kunde"]
    heights = {r: max(series(r)) * sc + gap for r in order}
    total = sum(heights.values())
    base = {}
    yy = y
    for r in order:
        yy += heights[r]
        base[r] = yy
    xw = lambda i: x + x_pad + i * (w - x_pad) / 35
    fills, d = [], ""
    seq = list(reversed(order))
    for k, r in enumerate(seq):
        vals = series(r)
        b = base[r]
        pts = [(xw(i), b - v * sc) for i, v in enumerate(vals)]
        # Trappeform fordi ordre er ukentlige heltall
        seg = ""
        for i, (px, py) in enumerate(pts):
            if i == 0:
                seg += f"{n(px)},{n(py)} "
            else:
                seg += f"{n(px)},{n(pts[i - 1][1])} {n(px)},{n(py)} "
        fills.append(f'<path d="M{n(pts[0][0])},{n(b)} L{seg} L{n(pts[-1][0])},{n(b)} Z" fill="{GRUNT}"/>')
        if k == 0:
            d += f"M{n(x)},{n(b)} L{n(pts[0][0])},{n(b)} L{n(pts[0][0])},{n(pts[0][1])} L{seg}"
        else:
            d += f"L{n(pts[0][0])},{n(pts[0][1])} L{seg}"
        if k < len(seq) - 1:
            nb = base[seq[k + 1]]
            right = x + w + 8
            left = x - 8
            d += (f"L{n(pts[-1][0])},{n(pts[-1][1])} Q{n(right)},{n(pts[-1][1])} {n(right)},{n(pts[-1][1] - 8)} "
                  f"L{n(right)},{n(nb + 6)} Q{n(right)},{n(nb)} {n(right - 8)},{n(nb)} L{n(left + 8)},{n(nb)} "
                  f"Q{n(left)},{n(nb)} {n(left)},{n(nb - 4)} ")
            # ny etasje starter med oppstigning
            nvals = series(seq[k + 1])
            ny = nb - nvals[0] * sc
            d += f"L{n(left)},{n(ny + 4)} Q{n(left)},{n(ny)} {n(left + 8)},{n(ny)} "
    return dict(d=d, fills="".join(fills), base=base, heights=heights, total=total, xw=xw, order=order)


def phone_debrief_header(step, title_lines, size=30):
    s = t(18, 40, f"Debrief, Spill 17", 14, 500, SEK, "c")
    s += t(372, 40, step, 14, 500, SEK, "c", "end")
    y = 78
    for ln in title_lines:
        s += t(18, y, ln, size, 800, HVIT, "d")
        y += size + 4
    return s, y


def page_debrief():
    pg = Page("07-debrief", 2100, 1200, "Tidevann: Gruppedebrief i fem steg",
              "Fem telefoner og en delt skjerm. Forklaring skrives før avsløring. Etterspørselen er en liten krusning fra 4 til 8. "
              "Ordrene stables i fire etasjer til en flodbølge ved Fabrikk, 1,8 til 7,6 ganger.")
    pg.add(t(60, 58, "Debrief: de fire kummene stables", 34, 800, HVIT, "d"))
    pg.add(demodata(2040, 58, "end", size=14))
    sc = 0.74
    fw = 390 * sc
    gap = (1980 - 5 * fw) / 4
    y = 80
    xs = [60 + i * (fw + gap) for i in range(5)]
    captions = [
        ("1. Skriv Forklaring", "Avsløringen er låst til du har lagret. Du ser ikke de andres tekst."),
        ("2. Avsløringen", "Alt kundene gjorde var dette. Samme skala som bølgen du sendte."),
        ("3. Ordrene stables", "Kundens krusning nederst, flodbølge ved Fabrikk. Ett diagram, én linje."),
        ("4. Ditt øyeblikk", "Uke 11 slik du så den, hva den kostet, og hva de andre så."),
        ("5. Quiz", "Feil svar forklares. Teller ikke. Alt riktig for å gå videre."),
    ]
    line_ys = {}
    # 1 Forklaring
    s1, yy = phone_debrief_header("Steg 1 av 5", ["Hvorfor gikk det", "som det gikk?"])
    s = [s1]
    s.append(t(18, yy + 6, "Skriv først. Hva gjorde kjeden, og hva var din del?", 15, 400, SEK, "t"))
    bx = yy + 22
    s.append(rect(18, bx, 354, 210, HVIT, 8))
    typed = ("Ordrene fra Detaljist vokste, og det kom for lite fra Distributør. Jeg bestilte mer og mer for å ta igjen Restordren. "
             "Så kom alt på en gang, og da satt jeg med for mye på Lager.")
    s.append(para(32, bx + 30, typed, 322, 16, 24, 500, BLEKK, "t", f=.5))
    s.append(rect(32, bx + 180, 2, 18, BLEKK))
    s.append(button(18, bx + 224, 354, 58, "Lagre Forklaring", "gul", 21))
    ly = bx + 340
    s.append(path(f"M0,{ly} L392,{ly}", HVIT, 3.5))
    s.append(path(f"M0,{ly} L390,{ly} L390,844 L0,844 Z", "none", 0, VANN))
    s.append(path(f"M0,{ly} L392,{ly}", HVIT, 3.5))
    s.append(rect(50, ly + 34, 290, 148, HAV, 10, SEK, 1.5, 'stroke-dasharray="5 5"'))
    s.append(lock(195, ly + 76, HVIT, 1.5))
    s.append(t(195, ly + 118, "Kundenes etterspørsel", 18, 700, HVIT, "d", "middle"))
    s.append(t(195, ly + 142, "Låst til du har lagret", 15, 500, SEK, "t", "middle"))
    s.append(t(195, ly + 216, "2 av 4 har lagret. Dere venter på hverandre.", 14, 500, SEK, "t", "middle"))
    line_ys[0] = ly
    # 2 Avsløring
    s2 = []
    hd, yy = phone_debrief_header("Steg 2 av 5", ["Dette var alt", "kundene gjorde."])
    ly2_y0 = 590
    usc = 6
    wx = lambda i: 20 + i * (370 - 20) / 35
    dem = [w["demand"] for w in WEEKS]
    seg = ""
    for i, v in enumerate(dem):
        px, py = wx(i), ly2_y0 - v * usc
        seg += f"L{n(px)},{n(py)} " if i == 0 else f"L{n(px)},{n(ly2_y0 - dem[i - 1] * usc)} L{n(px)},{n(py)} "
    d2 = f"M0,{ly2_y0 - 4 * usc} {seg}L392,{ly2_y0 - 8 * usc}"
    water2 = d2 + f" L392,844 L0,844 Z"
    s2.append(rect(0, 0, 390, 844, HAV))
    s2.append(hd)
    s2.append(t(18, yy + 66, "4", 112, 800, HVIT, "d"))
    s2.append(arrow(100, yy + 30, 182, yy + 30, HVIT, 3))
    s2.append(t(200, yy + 66, "8", 112, 800, GUL, "d"))
    s2.append(para(18, yy + 110, "4 kasser i uka. I Uke 5 ble det 8. Deretter stabilt 8, helt til slutt.", 354, 18, 25, 500, HVIT, "t", f=.48))
    # Ghost av Saras 24 i samme skala
    gx = wx(10)
    gw = wave(gx - 30, 72, 24 * usc, ly2_y0)
    s2.append(path(f"M{n(gx - 30)},{ly2_y0} {gw}", GUL, 2.4, extra='stroke-dasharray="6 6"'))
    s2.append(t(gx + 44, ly2_y0 - 24 * usc + 14, "Din ordre i Uke 11: 24", 14, 700, GUL, "c"))
    s2.append(t(gx + 44, ly2_y0 - 24 * usc + 32, "Samme skala", 13, 500, SEK, "c"))
    s2.append(path(water2, "none", 0, VANN))
    s2.append(line(0, ly2_y0, 390, ly2_y0, SEK, 1.5))
    cid = pg.uid("avsl")
    s2.append(f'<clipPath id="{cid}"><rect x="0" y="300" width="392" height="400"><animate attributeName="width" values="392;392" dur="1s"/></rect></clipPath>')
    s2.append(path(d2, HVIT, 3.5))
    s2.append(line(wx(4), ly2_y0 + 6, wx(4), ly2_y0 + 18, HVIT, 1.6))
    s2.append(t(wx(4), ly2_y0 + 36, "Uke 5", 14, 700, HVIT, "c", "middle"))
    s2.append(t(wx(0) + 2, ly2_y0 + 20, "0", 14, 700, SEK, "c"))
    s2.append(t(18, ly2_y0 + 72, "Øvelsen heter Beer Game. Forsinkelser, ikke", 15, 500, HVIT, "t"))
    s2.append(t(18, ly2_y0 + 94, "kunder, er det dere nå skal se på.", 15, 500, HVIT, "t"))
    s2.append(button(18, ly2_y0 + 118, 354, 54, "Vis ordrene", "gul", 20))
    line_ys[1] = ly2_y0 - 4 * usc
    line_exit2 = ly2_y0 - 8 * usc
    # 3 Etasjer
    s3 = [rect(0, 0, 390, 844, HAV)]
    hd, yy = phone_debrief_header("Steg 3 av 5", ["Krusningen blir", "en flodbølge."], 28)
    s3.append(hd)
    fl = floors(88, yy - 2, 232, 4.2, gap=18)
    s3.append(fl["fills"])
    s3.append(path(fl["d"] + f" L392,{n(fl['base']['Fabrikk'] - series('Fabrikk')[-1] * 4.2)}", HVIT, 2.2))
    labels = {"Kunde": "Kunde", "Detaljist": "Detaljist", "Grossist": "Grossist", "Distributør": "Distribu-\ntør", "Fabrikk": "Fabrikk"}
    amps = FX["amplification"]
    for r in fl["order"]:
        b = fl["base"][r]
        s3.append(t(10, b - 6, r, 13, 600, HVIT, "c"))
        if r in amps:
            s3.append(t(378, b - 6, f"{amps[r]:.1f}×".replace(".", ","), 21 if r == "Fabrikk" else 17, 800, GUL if r == "Fabrikk" else HVIT, "t", "end"))
        else:
            s3.append(t(378, b - 6, "4 til 8", 13, 600, HVIT, "c", "end"))
    fend = yy + fl["total"]
    s3.append(t(88, fend + 18, "Uke 1", 13, 400, SEK, "c"))
    s3.append(t(320, fend + 18, "Uke 36", 13, 400, SEK, "c", "end"))
    s3.append(para(18, fend + 44, "Samme skala i alle etasjer. Hvert ledd ser bare ordren fra leddet under, ikke kundene.", 354, 15, 20, 500, HVIT, "t", f=.47))
    s3.append(button(18, 770, 170, 46, "Vis som tabell", "ut", 16))
    s3.append(button(202, 770, 170, 46, "Ditt øyeblikk", "gul", 17))
    # 4 Ditt øyeblikk
    s4 = [rect(0, 0, 390, 844, HAV)]
    hd, yy = phone_debrief_header("Steg 4 av 5", ["Uke 11: du", "bestilte 24."], 30)
    s4.append(hd)
    mcfg = dict(W=390, sc=3.4, y0=yy + 96, stave_w=22, hole_end=92, rise_end=120, slot_x=122, wf=1.25, right=392,
                stave_top=yy + 8, stave_bot=yy + 96 + 50, bottom=yy + 170, step=10, stave_size=13, minor=False, lw=3)
    mst = dict(lager=0, rest=13, swells=SWELLS_11, sent=24)
    tail4 = ""
    k4, lvl = kum(pg, mcfg, dict(mst, tail=tail4), anim=False)
    s4.append(k4)
    s4.append(t(30, mcfg["y0"] + 32, 13, 32, 800, BLEKK, "d"))
    msl = slots(mcfg, [q for _, q in SWELLS_11] + [24])
    for i, (u, q) in enumerate(SWELLS_11):
        s4.append(t(msl[i][0] + msl[i][1] * .42, mcfg["y0"] - q * 3.4 - 6, q, 15, 700, HVIT, "t", "middle"))
    s4.append(t(msl[3][0] + msl[3][1] * .42 - 16, mcfg["y0"] - 24 * 3.4 + 18, 24, 22, 800, GUL, "d", "end"))
    s4.append(t((msl[0][0] + msl[2][0] + msl[2][1]) / 2, mcfg["y0"] + 22, "16 var på vei", 15, 700, HVIT, "t", "middle"))
    ty = yy + 196
    s4.append(ki_tag(18, ty, "Tall fra loggen. Tekst er KI-generert, kan ta feil", SEK))
    ty += 28
    rows = [("Hva du så", f"Lager 0, Restordre 13, ordre 8 inn, levering 4 inn. På vei 16 var mer enn hullet."),
            ("Hva du bestilte", "24 kasser. Av dem kom 17 i Uke 15, resten senere."),
            ("Hva det kostet senere", f"Uke 25 til 36 lå du med opptil 30 kasser på Lager: {kr(seat(36)['kost_sum'] - seat(24)['kost_sum'])}."),
            ("Hva de andre så", "Ida: Restordre 4. Mikkel: Lager 14, og ordren din traff i Uke 13: Lager 12 ble Restordre 7. Jonas: Lager 9.")]
    for head, body in rows:
        s4.append(t(18, ty, head, 16, 700, HVIT, "d"))
        s4.append(para(18, ty + 21, body, 354, 15, 20, 400, SEK, "t", f=.46))
        ty += 24 + para_h(body, 354, 15, 20, f=.46) + 10
    s4.append(t(18, 768, "Øyeblikk 1 av 3", 14, 500, SEK, "c"))
    s4.append(button(150, 744, 222, 46, "Neste øyeblikk", "gul", 18))
    # 5 Quiz
    s5 = [rect(0, 0, 390, 844, HAV)]
    hd, yy = phone_debrief_header("Steg 5 av 5", ["Hvorfor vokste", "ordrene oppover?"], 28)
    s5.append(hd)
    s5.append(t(18, yy + 2, "Spørsmål 3 av 5", 14, 500, SEK, "c"))
    opts = [("Fabrikk produserte for sakte.", False, True), ("Kundene bestilte stadig mer.", False, False),
            ("Hvert ledd så bare ordren under seg, og det som var på vei ble glemt.", True, False)]
    oy = yy + 20
    for label, right, wrong in opts:
        lines = wrap(label, 280, 16, .47)
        h = 26 + len(lines) * 22
        stroke = KORALL if wrong else RAND
        s5.append(rect(18, oy, 354, h, "none", 8, stroke, 2))
        if wrong:
            s5.append(cross(42, oy + h / 2))
        else:
            s5.append(f'<circle cx="42" cy="{n(oy + h / 2)}" r="8" fill="none" stroke="{SEK}" stroke-width="1.6"/>')
        for i, ln in enumerate(lines):
            s5.append(t(66, oy + 24 + i * 22, ln, 16, 600 if wrong else 400, HVIT, "t"))
        tag = "Ditt svar" if wrong else ("Riktig" if right else "")
        oy += h + 10
    s5.append(rect(18, oy + 2, 354, 216, VANN, 8))
    s5.append(t(34, oy + 32, "Ditt svar var ikke riktig", 18, 700, HVIT, "d"))
    expl = ("Fabrikk hadde ledig kapasitet de første ukene: Lager 9 i Uke 11. Ordrene vokste før de nådde Fabrikk. Forsinkelsen på 4 uker gjør at det som er på vei er lett å glemme, og da bestiller hvert ledd på nytt.")
    s5.append(para(34, oy + 56, expl, 322, 15, 21, 400, HVIT, "t", f=.46))
    s5.append(ki_tag(34, oy + 200, "Forklaring KI-generert, kan ta feil", SEK))
    s5.append(button(18, oy + 232, 354, 54, "Svar på nytt", "gul", 20))
    s5.append(t(195, oy + 312, "Quizen teller ikke. Du må ha alt riktig for å gå videre.", 14, 500, SEK, "c", "middle"))
    q_line = 776
    s5.append(path(f"M0,{q_line} L392,{q_line}", HVIT, 3.5))

    bodies = ["".join(s), "".join(s2), "".join(s3), "".join(s4), "".join(s5)]
    # Linje mellom telefonene på én felles høyde: bunnlinje rett over skjermbildets nedre del
    entry = [ly, ly2_y0 - 4 * usc, None, lvl, None]
    for i in range(5):
        x = xs[i]
        pg.add(phone_open(pg, x, y, sc))
        pg.add(bodies[i])
        pg.add(phone_close())
        cy = y + 844 * sc + 30
        pg.add(t(x, cy, captions[i][0], 21, 800, HVIT, "d"))
        pg.add(para(x, cy + 24, captions[i][1], fw - 4, 15, 20, 400, SEK, "t", f=.47))
    # Bro mellom ruter: samme linje
    def bridge(x1, y1, x2, y2):
        m = (x1 + x2) / 2
        return path(f"M{n(x1)},{n(y1)} C{n(m)},{n(y1)} {n(m)},{n(y2)} {n(x2)},{n(y2)}", HVIT, 2.7)
    pg.add(bridge(xs[0] + fw, y + ly * sc, xs[1], y + (ly2_y0 - 4 * usc) * sc))
    pg.add(bridge(xs[1] + fw, y + line_exit2 * sc, xs[2], y + fl["base"]["Kunde"] * sc))
    f_end = fl["base"]["Fabrikk"] - series("Fabrikk")[-1] * 4.2
    pg.add(bridge(xs[2] + fw, y + f_end * sc, xs[3], y + lvl * sc))
    pg.add(bridge(xs[3] + fw, y + mcfg["y0"] * sc, xs[4], y + q_line * sc))
    # Delt skjerm
    sx, sy, sw, sh = 60, 806, 1500, 360
    pg.add(rect(sx - 8, sy - 8, sw + 16, sh + 16, DYP, 12, SEK, 2.5))
    pg.add(rect(sx, sy, sw, sh, HAV, 4))
    pg.add(t(sx + 24, sy + 36, "Delt skjerm: ordre per Rolle, Uke 1 til 36", 24, 800, HVIT, "d"))
    pg.add(t(sx + sw - 24, sy + 34, "Bare felles diagram. Egne øyeblikk og Forklaringer blir på telefonen.", 15, 500, SEK, "t", "end"))
    fl2 = floors(sx + 150, sy + 50, sw - 330, 1.76, gap=13)
    pg.add(fl2["fills"])
    # Uke 5-merke
    x5 = fl2["xw"](4)
    pg.add(line(x5, sy + 52, x5, sy + sh - 24, SEK, 1.2, 'stroke-dasharray="3 5"'))
    pg.add(t(x5 + 8, sy + sh - 8, "Uke 5: kundene går fra 4 til 8", 14, 600, HVIT, "c"))
    kb = fl2["base"]["Kunde"]
    # Linja fra quiz: ut til høyre, under alt, inn fra venstre til Kundens etasje
    q_y = y + q_line * sc
    pg.add(path(f"M{n(xs[4] + fw)},{n(q_y)} Q2072,{n(q_y)} 2072,{n(q_y + 16)} L2072,1172 Q2072,1188 2056,1188 L44,1188 Q28,1188 28,1172 L28,{n(kb + 14)} Q28,{n(kb)} 44,{n(kb)} L{sx + 150},{n(kb)}", HVIT, 2.6))
    pg.add(path(fl2["d"], HVIT, 2.6))
    for r in fl2["order"]:
        b = fl2["base"][r]
        pg.add(t(sx + 24, b - 5, r, 16, 700, HVIT, "d"))
        if r in amps:
            pg.add(t(sx + sw - 24, b - 4, f"{amps[r]:.1f}×".replace(".", ","), 28 if r == "Fabrikk" else 21, 800, GUL if r == "Fabrikk" else HVIT, "t", "end"))
        else:
            pg.add(t(sx + sw - 24, b - 4, "4 til 8", 16, 600, HVIT, "t", "end"))
    # Kostnadstabell
    tx = 1600
    pg.add(t(tx, sy + 24, "Som tabell", 22, 800, HVIT, "d"))
    pg.add(t(tx, sy + 56, "Rolle", 14, 500, SEK, "c"))
    pg.add(t(tx + 300, sy + 56, "Forsterkning", 14, 500, SEK, "c", "end"))
    pg.add(t(tx + 440, sy + 56, "Totalkostnad", 14, 500, SEK, "c", "end"))
    pg.add(line(tx, sy + 66, tx + 440, sy + 66, RAND, 1))
    yy2 = sy + 92
    for r in ROLES:
        pg.add(t(tx, yy2, r, 17, 600, HVIT, "t"))
        pg.add(t(tx + 300, yy2, f"{amps[r]:.1f}×".replace(".", ","), 18, 700, HVIT, "t", "end"))
        pg.add(t(tx + 440, yy2, kr(FX["total_cost_per_role"][r]), 18, 500, HVIT, "t", "end"))
        pg.add(line(tx, yy2 + 10, tx + 440, yy2 + 10, RAND, 1))
        yy2 += 36
    pg.add(t(tx, yy2 + 2, "Kjeden totalt", 17, 700, HVIT, "t") + t(tx + 440, yy2 + 2, kr(FX["chain_total_cost"]), 20, 800, HVIT, "t", "end"))
    pg.add(para(tx, yy2 + 44, "Kundene gikk fra 4 til 8. Fabrikk bestilte opptil 31. Ingen gjorde noe rart: alle svarte på det de så.", 440, 17, 24, 500, HVIT, "t", f=.46))
    pg.add(ki_tag(tx, yy2 + 134, "Tekst KI-generert, kan ta feil", SEK, 14))
    pg.save()


# 08 Oversikt: sjøkart
def stave_mini(x, base, h, status, uke, ki, sc=1.0):
    """Liten målestav for ett spill. Høyde = Uke (36 = full). Form viser status."""
    out = []
    W = 15 * sc
    H = h
    out.append(rect(x - W / 2, base - H, W, H, "none", 0, SEK, 1))
    lvl = H * min(uke, 36) / 36
    if status == "ferdig":
        out.append(rect(x - W / 2, base - lvl, W, lvl, GRUNT))
        out.append(line(x - W / 2, base - lvl, x + W / 2, base - lvl, HVIT, 2))
    elif status == "pågår":
        out.append(rect(x - W / 2, base - lvl, W, lvl, GRUNT))
        out.append(line(x - W / 2 - 2, base - lvl, x + W / 2 + 2, base - lvl, HVIT, 2.2))
    elif status == "pauset":
        out.append(rect(x - W / 2, base - lvl, W, lvl, GRUNT))
        out.append(line(x - W / 2 - 2, base - lvl, x + W / 2 + 2, base - lvl, HVIT, 2.2))
    return "".join(out)


def page_oversikt():
    pg = Page("08-laerer-oversikt", 1600, 1000, "Tidevann: Oversikt over 60 Klassespill",
              "Sjøkart over 60 målestaver. Spill som venter står fremst og i korall, Spill 2 venter på Noah i 23 timer. "
              "Tabell for presisjon til høyre, og trakten som dybdeprofil nederst.", HAV)
    games = FX["class_games"]
    pg.add(wordmark(32, 42, 22))
    pg.add(t(180, 41, "class-of-1994 · IBE160 · Klasseøkt: Oversikt", 17, 600, HVIT, "t"))
    pg.add(t(1568, 41, "Faglærer Bård", 15, 500, SEK, "t", "end"))
    pg.add(demodata(1568, 60, "end"))
    # Tellinger
    c = {"ferdig": 0, "pågår": 0, "venter": 0, "pauset": 0}
    for g in games:
        c[g["status"]] += 1
    assert c["ferdig"] == 41 and c["venter"] == 4 and c["pauset"] == 2 and c["pågår"] + c["pauset"] == 15
    pg.add(t(32, 104, "4", 44, 800, HVIT, "d") + t(62, 86, "venter", 15, 600, HVIT, "c") + t(62, 104, "kraftig avvik", 14, 400, SEK, "c"))
    pg.add(t(180, 104, "15", 44, 800, HVIT, "d") + t(232, 86, "pågår", 15, 600, HVIT, "c") + t(232, 104, "herav 2 pauset", 14, 400, SEK, "c"))
    pg.add(t(350, 104, "41", 44, 800, HVIT, "d") + t(402, 86, "ferdig", 15, 600, HVIT, "c") + t(402, 104, "rolig kyst", 14, 400, SEK, "c"))
    # Filtre
    fx = 560
    filters = [("Alle 60", True), ("Venter 4", False), ("Pauset 2", False), ("KI-seter", False), ("Ferdig 41", False)]
    pg.add(t(fx, 84, "Filtrer", 14, 500, SEK, "c"))
    px = fx
    for label, on in filters:
        w = len(label) * 8 + 26
        pg.add(rect(px, 92, w, 30, HVIT if on else "none", 15, HVIT if on else SEK, 1.2))
        pg.add(t(px + w / 2, 112, label, 14, 700 if on else 500, BLEKK if on else HVIT, "t", "middle"))
        px += w + 8
    # Sjøkart: bakgrunn og koter
    cx, cy, cw, ch = 32, 138, 1040, 610
    pg.add(rect(cx, cy, cw, ch, VANN, 4))
    cid = pg.uid("kart")
    pg.add(f'<clipPath id="{cid}"><rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="4"/></clipPath><g clip-path="url(#{cid})">')
    # Grunna: spill som står fast ligger på sjøkart-gul grunne
    shoal = (f"M{cx},{cy} L{cx + 764},{cy} C{cx + 776},{cy + 60} {cx + 744},{cy + 120} {cx + 752},{cy + 166} "
             f"L{cx + 752},{cy + 208} L{cx},{cy + 208} Z")
    pg.add(f'<path d="{shoal}" fill="{GUL}"/>')
    for off in (400, 520):
        pg.add(f'<path d="M{cx},{cy + off} C{cx + 260},{cy + off - 18} {cx + 520},{cy + off + 18} {cx + cw},{cy + off - 10}" fill="none" stroke="{RAND}" stroke-width="1"/>')
    pg.add("</g>")
    # Sorter: venter først etter timer, så pauset, pågår, ferdig
    venter = sorted([g for g in games if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])
    pauset = [g for g in games if g["status"] == "pauset"]
    pag = sorted([g for g in games if g["status"] == "pågår"], key=lambda g: g["uke"])
    ferd = sorted([g for g in games if g["status"] == "ferdig"], key=lambda g: g["spill"])
    ax = cx + 44
    ay = cy + 166
    H = 136
    colw = 182
    for i, g in enumerate(venter):
        x = ax + i * colw
        h = g["ventet_timer"] / 24 * H
        near = g["ventet_timer"] >= 23
        pg.add(rect(x - 11, ay - H, 22, H, HVIT, 0, BLEKK, 1.2))
        for u in range(0, 25, 6):
            yy = ay - u / 24 * H
            pg.add(line(x + 3, yy, x + 11, yy, BLEKK, 1.4))
        pg.add(rect(x - 11, ay - h, 12, h, KORALL, 0, BLEKK, 1))
        pg.add(line(x - 16, ay - H, x + 16, ay - H, BLEKK, 3))
        pg.add(t(x + 22, ay - H + 16, f"Spill {g['spill']}", 20, 800, BLEKK, "d"))
        pg.add(t(x + 22, ay - H + 38, g["venter_paa"], 15, 600, BLEKK, "c"))
        pg.add(t(x + 22, ay - H + 56, g["navn"], 15, 500, BLEKK, "c"))
        pg.add(t(x + 22, ay - 30, f"{g['ventet_timer']} t", 32, 800, BLEKK, "d"))
        pg.add(t(x + 22, ay - 10, f"Uke {g['uke']}", 14, 500, BLEKK, "c"))
        if near:
            pg.add(rect(x - 11, ay + 8, 150, 26, KORALL, 4, BLEKK, 1) + t(x - 3, ay + 26, "KI overtar om 1 t", 15, 700, BLEKK, "c"))
    # Pauset
    for i, g in enumerate(pauset):
        x = ax + 4 * colw + 30 + i * 106
        h = H * .55
        pg.add(rect(x - 11, ay - h, 22, h, "none", 0, HVIT, 1.5))
        lvl = h * g["uke"] / 36
        pg.add(rect(x - 11, ay - lvl, 22, lvl, GRUNT))
        pg.add(pause_icon(x, ay - h - 16, HVIT, .9))
        pg.add(t(x, ay + 20, f"Spill {g['spill']}", 14, 700, HVIT, "c", "middle"))
        pg.add(t(x, ay + 37, f"Uke {g['uke']}", 13, 400, HVIT, "c", "middle"))
    pg.add(t(ax + 4 * colw + 12, ay - H + 12, "Pause: fortsetter", 15, 600, HVIT, "c"))
    pg.add(t(ax + 4 * colw + 12, ay - H + 30, "i kveld 19:00", 14, 400, HVIT, "c"))
    # Pågår
    py = cy + 342
    px0 = cx + 40
    pw = (cw - 80) / 13
    pH = 88
    pg.add(t(px0 - 12, cy + 226, "Pågår, lengst bak først. Vannhøyde er Uke.", 15, 600, HVIT, "c"))
    for i, g in enumerate(pag):
        x = px0 + i * pw + pw / 2 - 12
        lvl = pH * g["uke"] / 36
        pg.add(rect(x - 9, py - pH, 18, pH, "none", 0, SEK, 1))
        pg.add(rect(x - 9, py - lvl, 18, lvl, GRUNT))
        pg.add(line(x - 12, py - lvl, x + 12, py - lvl, HVIT, 2.2))
        pg.add(t(x, py + 18, g["spill"], 14, 700, HVIT, "t", "middle"))
        pg.add(t(x, py + 35, f"U{g['uke']}", 13, 400, SEK, "c", "middle"))
        if g["ki_seter"]:
            pg.add(hex_mark(x, py - pH - 12, GUL) + t(x + 11, py - pH - 7, g["ki_seter"], 13, 700, GUL, "c"))
    # Ferdig: rolig kyst, stavhøyde er kjedekostnad
    fy0 = cy + 408
    fw_ = (cw - 72) / 21
    pg.add(t(px0 - 12, fy0 - 6, "Ferdig: rolig kyst. Stavhøyde og tall er kjedekostnad i 1 000 kr.", 15, 600, HVIT, "c"))
    rows = [ferd[:21], ferd[21:]]
    bases = []
    maxk = max(g["kjedekost"] for g in ferd)
    for r, row in enumerate(rows):
        base = fy0 + 44 + r * 82
        bases.append(base)
        for i, g in enumerate(row):
            x = px0 + i * fw_ + 8
            hh = 30 * g["kjedekost"] / maxk
            pg.add(rect(x - 6, base - hh, 12, hh, GRUNT))
            pg.add(line(x - 8, base - hh, x + 8, base - hh, HVIT, 1.6))
            pg.add(t(x, base + 15, g["spill"], 13, 600, HVIT, "t", "middle"))
            pg.add(t(x, base + 31, f"{g['kjedekost'] / 1000:.1f}".replace(".", ","), 13, 400, SEK, "c", "middle"))
            if g["ki_seter"]:
                pg.add(hex_mark(x + 8, base - hh - 8, GUL, .7))
    pg.add(t(cx + cw - 14, cy + ch - 10, "Sekskant: KI-sete", 14, 500, HVIT, "c", "end"))
    # Den ene linja: stavene står på den, rad for rad, og den fortsetter ned i trakten
    R_ = cx + cw - 10
    L_ = cx + 10
    rr = 12
    fy_top = 776 + 58
    d = (f"M{cx},{ay} L{R_ - rr},{ay} Q{R_},{ay} {R_},{ay + rr} L{R_},{py - rr} Q{R_},{py} {R_ - rr},{py} "
         f"L{L_ + rr},{py} Q{L_},{py} {L_},{py + rr} L{L_},{bases[0] - rr} Q{L_},{bases[0]} {L_ + rr},{bases[0]} "
         f"L{R_ - rr},{bases[0]} Q{R_},{bases[0]} {R_},{bases[0] + rr} L{R_},{bases[1] - rr} Q{R_},{bases[1]} {R_ - rr},{bases[1]} "
         f"L{cx + 6},{bases[1]} Q{cx - 12},{bases[1]} {cx - 12},{bases[1] + 18} L{cx - 12},{fy_top - 12} Q{cx - 12},{fy_top} {cx},{fy_top}")
    # Mørk kant under linja der den går over gul grunne, så den ikke forsvinner
    pg.add(line(cx, ay, cx + 752, ay, BLEKK, 5))
    pg.add(path(d, HVIT, 2.4))
    # Tabell til høyre
    tx = 1092
    tw = 476
    pg.add(t(tx, 158, "Venter og Pause", 22, 800, HVIT, "d"))
    head_y = 186
    cols = [tx, tx + 66, tx + 214, tx + 296]
    for x, lab in zip(cols, ["Spill", "Venter på", "Ventet", "Uke"]):
        pg.add(t(x, head_y, lab, 14, 500, SEK, "c"))
    pg.add(line(tx, head_y + 8, tx + tw, head_y + 8, RAND, 1))
    y = head_y + 32
    for g in venter:
        near = g["ventet_timer"] >= 23
        if near:
            pg.add(rect(tx - 8, y - 20, tw + 16, 34, KORALL, 4))
        col = BLEKK if near else HVIT
        pg.add(t(cols[0], y, g["spill"], 17, 700, col, "t"))
        pg.add(t(cols[1], y, f"{g['navn']}, {g['venter_paa']}", 16, 600, col, "c"))
        pg.add(t(cols[2], y, f"{g['ventet_timer']} t", 17, 700, col, "t"))
        pg.add(t(cols[3], y, g["uke"], 17, 500, col, "t"))
        pg.add(t(tx + tw, y, "Melding", 15, 700, col, "c", "end", 'text-decoration="underline"'))
        if not near:
            pg.add(line(tx, y + 13, tx + tw, y + 13, RAND, 1))
        y += 36
    for g in pauset:
        pg.add(pause_icon(cols[0] + 36, y - 6, HVIT, .7))
        pg.add(t(cols[0], y, g["spill"], 17, 700, HVIT, "t"))
        pg.add(t(cols[1], y, f"Pause, fortsetter {g['fortsetter']}", 16, 500, HVIT, "c"))
        pg.add(t(cols[3], y, g["uke"], 17, 500, HVIT, "t"))
        pg.add(t(tx + tw, y, "Melding", 15, 700, HVIT, "c", "end", 'text-decoration="underline"'))
        pg.add(line(tx, y + 13, tx + tw, y + 13, RAND, 1))
        y += 36
    ki_pag = [g for g in pag + pauset if g["ki_seter"]]
    y += 12
    pg.add(t(tx, y, "KI-seter i spill som ikke er ferdige", 18, 800, HVIT, "d"))
    y += 26
    for g in sorted(ki_pag, key=lambda g: g["spill"]):
        pg.add(hex_mark(tx + 7, y - 5, GUL))
        pg.add(t(tx + 22, y, f"Spill {g['spill']}", 16, 600, HVIT, "t"))
        pg.add(t(tx + 110, y, f"{g['ki_seter']} KI-spiller{'e' if g['ki_seter'] > 1 else ''}, Uke {g['uke']}", 16, 400, HVIT, "c"))
        y += 26
    pg.add(button(tx, 562, 232, 50, "Send Melding til 4", "gul", 18))
    pg.add(button(tx + 244, 562, 232, 50, "Fyll alle tomme seter", "ut", 17))
    pg.add(t(tx, 640, "Du trenger ikke følge med hele tiden:", 16, 600, HVIT, "t"))
    pg.add(para(tx, 662, "KI-spiller tar setet etter 24 t. Du ser det her, og studenten kan ta setet tilbake. Ved Spillfrist ti. 8. des fullføres resten av KI.", tw, 15, 21, 400, SEK, "t", f=.46))
    # Trakt som dybdeprofil
    fy = 776
    fh = 196
    pg.add(rect(32, fy, 1536, fh, VANN, 4))
    pg.add(t(48, fy + 28, "Trakten: 240 studenter fra start til KI-vurdering", 19, 800, HVIT, "d"))
    fn = FX["funnel"]
    steps = [("Registrert", fn["registrert"]), ("Klassespill ferdig", fn["klassespill_ferdig"]), ("Debrief ferdig", fn["debrief_ferdig"]),
             ("Quiz bestått", fn["quiz_bestått"]), ("Replay ferdig", fn["replay_ferdig"]), ("Test levert", fn["test_levert"]), ("KI-vurdering klar", fn["ki_vurdering_klar"])]
    sw = 1472 / 7
    top = fy + 58
    bh = 100
    d = ""
    area = ""
    for i, (lab, v) in enumerate(steps):
        x = 64 + i * sw
        yy = top + (1 - v / 240) * bh
        if i == 0:
            d = f"M32,{n(yy)} L{n(x + sw - 8)},{n(yy)} "
        else:
            d += f"L{n(x)},{n(yy)} L{n(x + sw - 8)},{n(yy)} "
    d_full = d + f"L1568,{n(top + bh)}"
    pg.add(f'<path d="{d_full} L1568,{top + bh} L32,{top + bh} Z" fill="{GRUNT}"/>')
    pg.add(path(d_full, HVIT, 2.6))
    pg.add(line(32, top + bh, 1568, top + bh, SEK, 1.2))
    for i, (lab, v) in enumerate(steps):
        x = 64 + i * sw
        yy = top + (1 - v / 240) * bh
        pg.add(t(x + 6, max(yy - 8, top + 12) if yy > top + 24 else yy + 32, v, 26, 800, HVIT, "d"))
        pg.add(t(x + 6, top + bh + 22, lab, 15, 600, HVIT, "c"))
    pg.save()


# 01 Landing
def page_landing():
    pg = Page("01-landing", 1440, 1200, "Tidevann: landingsside for faglærere",
              "Et stort snitt av vann. En student har 13 i Restordre, 16 er på vei, og en ordre på 24 tårner seg opp. "
              "Under: fire seter på samme linje og fakta om øvelsen.", HAV)
    y0 = 616
    cfg = dict(W=1440, sc=14, y0=y0, stave_w=62, hole_end=330, rise_end=430, slot_x=440, wf=3.8, right=1220,
               stave_top=y0 - 14 * 25, stave_bot=y0 + 14 * 16, bottom=1200, stave_size=19, minor=True, lw=6)
    tail = f" L1400,{y0} Q1420,{y0} 1420,{y0 + 20} L1420,916 Q1420,936 1400,936 L640,936"
    st = dict(lager=0, rest=13, swells=SWELLS_11, tail=tail, draft=None)
    drawn, level = kum(pg, cfg, st)
    # Stor gul bølge
    pg.add(drawn)
    lsl = slots(cfg, [q for _, q in SWELLS_11] + [24])
    x0, w0, _ = lsl[3]
    h = 24 * 14
    dw = f"M{n(x0)},{y0} " + wave(x0, w0, h, y0)
    pg.add(f'<path d="{dw} Z" fill="{GUL}" fill-opacity="0.2"/>')
    pg.add(path(dw, GUL, 6, extra='stroke-dasharray="12 10"'))
    crest = x0 + .42 * w0
    pg.add(bouy(crest, y0 - h + 2, 1.5, handle=False))
    pg.add(t(crest + 88, y0 - h + 44, 24, 92, 800, GUL, "d"))
    pg.add(t(crest + 88, y0 - h + 74, "ordren som vurderes", 18, 600, GUL, "t"))
    # Nav
    pg.add(wordmark(100, 58, 30))
    pg.add(t(1040, 56, "Logg inn", 18, 600, HVIT, "t", extra='text-decoration="underline"'))
    pg.add(button(1130, 28, 230, 48, "Be om lærertilgang", "gul", 18))
    # Hero
    pg.add(t(100, 158, "Hele øvelsen om", 74, 800, HVIT, "d"))
    pg.add(t(100, 238, "forsyningskjeder,", 74, 800, HVIT, "d"))
    pg.add(t(100, 318, "for hele klassen.", 74, 800, HVIT, "d"))
    pg.add(para(100, 366, "Fire studenter på samme vann, ett tall i uka. Tidevann kjører alt fra Invitasjon til PDF-rapport for klasser på rundt 250 studenter.", 700, 21, 30, 400, HVIT, "t", f=.47))
    pg.add(button(100, 442, 240, 58, "Be om lærertilgang", "gul", 20))
    pg.add(button(356, 442, 130, 58, "Logg inn", "ut", 20))
    # Annotasjoner i snittet
    pg.add(t(82, y0 - 18, "Lager 0", 24, 700, HVIT, "t"))
    pg.add(t(82, y0 + 32, "Restordre: tørr grunn under null", 19, 700, BLEKK, "t"))
    pg.add(t(82, level - 28, 13, 124, 800, BLEKK, "d"))
    for i, (u, q) in enumerate(SWELLS_11):
        x, w_, _ = lsl[i]
        c = x + .42 * w_
        pg.add(t(c, y0 - q * 14 - 12, q, 44, 800, HVIT, "d", "middle"))
        pg.add(t(x + w_ / 2, y0 + 30, f"Uke {u}", 19, 500, HVIT, "c", "middle"))
    bx1 = lsl[2][0] + lsl[2][1] - 8
    bmid = (448 + bx1) / 2
    pg.add(f'<path d="M448,{y0 + 46} L448,{y0 + 54} L{n(bx1)},{y0 + 54} L{n(bx1)},{y0 + 46}" fill="none" stroke="{HVIT}" stroke-width="2"/>')
    pg.add(t(bmid, y0 + 96, "16 er allerede på vei", 36, 800, HVIT, "d", "middle"))
    pg.add(t(bmid, y0 + 126, "Det er ikke lett å se når hullet er 13.", 19, 400, SEK, "t", "middle"))
    pg.add(t(x0 + w0 / 2, y0 + 30, "Uke 15", 19, 700, GUL, "c", "middle"))
    pg.add(para(1244, y0 + 30, "Dette ser en Grossist i Uke 11. Beslutningen er ett heltall.", 170, 18, 25, 500, HVIT, "t", f=.46))
    pg.add(demodata(82, level + 28, size=15))
    # Neste seksjon
    sy = 884
    pg.add(t(100, sy, "Fire seter,", 46, 800, HVIT, "d"))
    pg.add(t(100, sy + 52, "samme vann.", 46, 800, HVIT, "d"))
    pg.add(para(100, sy + 92, "Hver student ser sitt eget Lager, sin egen Restordre og det som er på vei. Ingen ser de andres tall.", 470, 19, 27, 400, HVIT, "t", f=.46))
    coast = 936
    labels = [("Fabrikk", "Har bestilt", True, False), ("Distributør", "KI-spiller", True, True), ("Grossist", "Venter 3 min", False, False), ("Detaljist", "Har bestilt", True, False)]
    for i, (rolle, status, lit, ki) in enumerate(reversed(labels)):
        x = 700 + i * 200
        pg.add(fyr(x, coast, lit, ki, 1.9))
        pg.add(t(x, coast + 30, rolle, 22, 700, HVIT, "d", "middle"))
        pg.add(t(x, coast + 54, status, 18, 500, HVIT if lit or ki else SEK, "c", "middle"))
    # Fakta som tidevannstabell
    fy = 1040
    facts = [("Studentlisten", "lastes opp fra Canvas-eksport"), ("Tomme seter", "fylles av KI-spillere, alltid merket"),
             ("Ett fravær", "stopper ikke gruppa"), ("Uferdige spill", "ingen blir stående"),
             ("Alle spillene", "på én skjerm"), ("Studentene", "spiller på mobil, på norsk")]
    for i, (a, b) in enumerate(facts):
        col, row = i % 2, i // 2
        x = 100 + col * 640
        y = fy + row * 46
        pg.add(line(x, y + 16, x + 600, y + 16, RAND, 1))
        pg.add(t(x, y, a, 21, 700, HVIT, "d"))
        pg.add(t(x + 190, y, b, 20, 400, HVIT, "t"))
    pg.save()


# Felles lærertopp
def teacher_top(pg, title, right=None):
    pg.add(wordmark(32, 42, 22))
    pg.add(t(180, 41, title, 17, 600, HVIT, "t"))
    pg.add(t(pg.w - 32, 41, right or "Faglærer Bård", 15, 500, SEK, "t", "end"))
    pg.add(demodata(pg.w - 32, 60, "end"))


def page_klasse():
    pg = Page("02-laerer-klasse", 1440, 1000, "Tidevann: faglærer lager Klasse",
              "Skjema langs én linje: navn, Canvas-fil, e-postkolonne, ugyldige rader, send Invitasjoner. "
              "Til høyre står Klasselista på en målestav fra 0 til 250 med status.", HAV)
    teacher_top(pg, "Klasser / Ny Klasse")
    pg.add(t(90, 106, "Ny Klasse", 40, 800, HVIT, "d"))
    lx = 54
    pts = [152, 252, 362, 592, 832]
    pg.add(path(f"M0,{pts[0] - 28} L{lx - 10},{pts[0] - 28} Q{lx},{pts[0] - 28} {lx},{pts[0] - 18} L{lx},{pts[-1] + 74} Q{lx},{pts[-1] + 84} {lx + 10},{pts[-1] + 84} L836,{pts[-1] + 84} Q846,{pts[-1] + 84} 846,{pts[-1] + 74} L846,120 Q846,110 856,110 L1440,110", HVIT, 3))
    for i, py in enumerate(pts):
        pg.add(check(lx, py, BLEKK, .8) if False else "")
        pg.add(f'<circle cx="{lx}" cy="{py - 6}" r="10" fill="{GUL}" stroke="{BLEKK}" stroke-width="1.5"/>')
        pg.add(check(lx, py - 6, BLEKK, .85))
    X = 90
    # Navn
    pg.add(t(X, pts[0], "Navn og emnekode", 21, 700, HVIT, "d"))
    pg.add(t(X, pts[0] + 26, "Navn", 14, 500, SEK, "c") + rect(X, pts[0] + 32, 330, 40, HVIT, 6) + t(X + 12, pts[0] + 58, "class-of-1994", 17, 600, BLEKK, "t"))
    pg.add(t(X + 350, pts[0] + 26, "Emnekode", 14, 500, SEK, "c") + rect(X + 350, pts[0] + 32, 150, 40, HVIT, 6) + t(X + 362, pts[0] + 58, "IBE160", 17, 600, BLEKK, "t"))
    # Fil
    pg.add(t(X, pts[1], "Last opp Canvas-fil", 21, 700, HVIT, "d"))
    pg.add(rect(X, pts[1] + 14, 700, 56, VANN, 6))
    pg.add(t(X + 16, pts[1] + 39, "ibe160-canvas-eksport.xlsx", 18, 600, HVIT, "t"))
    pg.add(t(X + 16, pts[1] + 60, "250 rader lest. Excel eller CSV.", 15, 400, SEK, "t"))
    pg.add(t(X + 684, pts[1] + 48, "Bytt fil", 16, 600, HVIT, "t", "end", 'text-decoration="underline"'))
    # Kolonne
    pg.add(t(X, pts[2], "Velg e-postkolonne", 21, 700, HVIT, "d"))
    cols = [("Navn", ["Ida Solberg", "Sara Lien", "Mikkel Berg"], False, 190), ("E-post", ["ida.s@student.example", "sara.l@student.example", "mikkel.b@student.example"], True, 290), ("Studentnr.", ["210417", "210533", "210682"], False, 150)]
    cxx = X
    for name, vals, on, w in cols:
        if on:
            pg.add(rect(cxx, pts[2] + 12, w, 146, VANN, 6, GUL, 2))
        rad = f'<circle cx="{cxx + 18}" cy="{pts[2] + 34}" r="8" fill="{GUL if on else "none"}" stroke="{GUL if on else SEK}" stroke-width="2"/>'
        pg.add(rad + t(cxx + 34, pts[2] + 40, name, 17, 700, HVIT, "t"))
        for j, v in enumerate(vals):
            pg.add(t(cxx + 14, pts[2] + 72 + j * 26, v, 16, 400, HVIT if on else SEK, "c"))
        cxx += w + 12
    pg.add(t(X, pts[2] + 184, "Forslag ut fra innholdet. 246 av 250 rader ser ut som gyldige adresser.", 15, 500, SEK, "t"))
    # Ugyldige
    pg.add(t(X, pts[3], "Ugyldige rader: 4", 21, 700, HVIT, "d"))
    rows = [(37, "noah.berg@student", "Mangler domene", "Rett"), (88, "emma.lund@@student.example", "To krøllalfa", "Manuelt registrert"),
            (141, "(tom celle)", "Ingen adresse", "Manuelt registrert"), (203, "jon haug@student.example", "Mellomrom i adressen", "Rett")]
    pg.add(t(X, pts[3] + 30, "Rad", 14, 500, SEK, "c") + t(X + 56, pts[3] + 30, "Adresse i fila", 14, 500, SEK, "c") + t(X + 336, pts[3] + 30, "Problem", 14, 500, SEK, "c") + t(X + 700, pts[3] + 30, "Handling", 14, 500, SEK, "c", "end"))
    for i, (rad, adr, prob, hand) in enumerate(rows):
        y = pts[3] + 58 + i * 38
        pg.add(line(X, y - 22, X + 700, y - 22, RAND, 1))
        pg.add(cross(X + 42, y - 5, KORALL, .7))
        pg.add(t(X, y, rad, 17, 700, HVIT, "t"))
        pg.add(t(X + 56, y, adr, 16, 500, HVIT, "c"))
        pg.add(t(X + 336, y, prob, 16, 400, SEK, "c"))
        if hand == "Rett":
            pg.add(rect(X + 618, y - 18, 82, 28, "none", 5, HVIT, 1.3) + t(X + 659, y + 1, "Rett", 15, 700, HVIT, "t", "middle"))
        else:
            pg.add(check(X + 560, y - 5, GUL, .7) + t(X + 700, y, hand, 15, 600, HVIT, "c", "end"))
    # Send
    pg.add(t(X, pts[4], "Send Invitasjoner", 21, 700, HVIT, "d"))
    pg.add(t(X + 212, pts[4] - 1, "246 gyldige rader. Hver Invitasjon er gyldig i 14 dager.", 16, 400, SEK, "t"))
    pg.add(button(X, pts[4] + 12, 300, 54, "Send 246 Invitasjoner", "gul", 20))
    pg.add(t(X + 318, pts[4] + 45, "Sendt. Nye rader kan sendes senere.", 16, 500, HVIT, "t"))
    # Status
    sx = 880
    pg.add(t(sx, 158, "Status på Klasselista", 26, 800, HVIT, "d"))
    pg.add(t(sx, 184, "Etter at Invitasjonene har stått ute i 14 dager", 15, 400, SEK, "t"))
    # Stav 0 til 250
    r = FX["roster"]
    sent_open, utlopt, ugyldig_igjen = 3, 5, 2
    assert r["registrert"] + r["manuelt_registrert"] + sent_open + utlopt + ugyldig_igjen == r["paa_lista"]
    top, bot = 224, 806
    scale = (bot - top) / 250
    W = 60
    pg.add(rect(sx, top - 16, W, bot - top + 32, HVIT))
    for u in range(0, 251, 10):
        yy = bot - u * scale
        major = u % 50 == 0
        pg.add(rect(sx + W - (14 if major else 6), yy - .7, 14 if major else 6, 1.4, BLEKK))
        if major:
            pg.add(t(sx + W - 18, yy + 6, u, 16, 700, BLEKK, "c", "end"))
    # Vann
    lev = bot - 240 * scale
    pg.add(rect(sx + W, lev, 460, bot - lev, VANN))
    pg.add(rect(sx + W, bot - 250 * scale, 460, 10 * scale, OKER))
    pg.add(line(sx + W, lev, sx + W + 460, lev, HVIT, 3))
    pg.add(t(sx + W + 22, lev + 92, "240", 110, 800, HVIT, "d"))
    pg.add(t(sx + W + 22, lev + 126, "registrert", 24, 700, HVIT, "d"))
    pg.add(t(sx + W + 22, lev + 152, "238 via Invitasjon, 2 manuelt", 17, 500, SEK, "t"))
    pg.add(t(sx + W + 22, bot - 250 * scale + 17.5, "10 uregistrert", 16, 700, BLEKK, "t"))
    # Liste
    y = lev + 210
    pg.add(t(sx + W + 22, y, "Status per Invitasjon", 19, 800, HVIT, "d"))
    y += 30
    st_rows = [(r["registrert"], "Akseptert"), (sent_open, "Sendt, ikke svart"), (utlopt, "Utløpt"), (r["manuelt_registrert"], "Manuelt registrert"), (ugyldig_igjen, "Ugyldig adresse, ikke rettet")]
    for v, lab in st_rows:
        pg.add(t(sx + W + 80, y, v, 21, 700, HVIT, "t", "end"))
        pg.add(t(sx + W + 96, y, lab, 18, 500, HVIT, "t"))
        pg.add(line(sx + W + 22, y + 10, sx + W + 440, y + 10, RAND, 1))
        y += 36
    pg.add(button(sx + W + 22, y + 2, 300, 46, "Send på nytt til 8", "ut", 17))
    pg.add(t(sx + W + 334, y + 31, "3 sendt + 5 utløpt", 15, 500, SEK, "c"))
    pg.add(t(sx, 852, "Fordeling på Klassespill skjer i Klasseøkt.", 16, 500, SEK, "t"))
    pg.add(button(sx + 296, 868, 224, 52, "Lag Klasseøkt", "gul", 19))
    pg.save()


def page_oekt():
    pg = Page("03-laerer-spill", 1440, 1100, "Tidevann: faglærer setter opp Klasseøkt",
              "Standardene Klassisk er forhåndsutfylt og kan lagres uten endring. Forsinkelsene står på kjedelinja, "
              "datoene på en tidslinje, og 60 spill à 4 kan forhåndsvises og bekreftes.", HAV)
    teacher_top(pg, "class-of-1994 / Klasseøkt")
    pg.add(t(32, 112, "Klasseøkt: Klassisk", 40, 800, HVIT, "d"))
    pg.add(t(32, 142, "Alt er forhåndsutfylt. Du kan lagre uten å endre noe.", 18, 400, SEK, "t"))
    pg.add(button(1148, 80, 260, 58, "Lagre Klasseøkt", "gul", 21))
    # Kjeden med forsinkelser på linja
    Y = 228
    roles = list(reversed(ROLES))
    xs = [70, 330, 590, 850]
    for i, r in enumerate(roles):
        pg.add(fyr(xs[i], Y, True, False, 1.4))
        pg.add(t(xs[i], Y + 24, r, 17, 700, HVIT, "d", "middle"))
        pg.add(t(xs[i], Y + 44, "Startlager 12", 14, 500, SEK, "c", "middle"))
    pg.add(t(xs[0] + 44, Y + 44, "Produksjon 2 uker", 14, 500, HVIT, "c"))
    delay = ["Fraktforsinkelse 2 uker", "Fraktforsinkelse 2 uker", "Fraktforsinkelse 2 uker"]
    for i in range(3):
        mx = (xs[i] + xs[i + 1]) / 2
        pg.add(t(mx, Y - 12, delay[i], 15, 600, HVIT, "c", "middle"))
        pg.add(t(mx, Y + 22, "Ordreforsinkelse 2 uker", 15, 500, SEK, "c", "middle"))
        pg.add(arrow(mx - 28, Y - 30, mx + 28, Y - 30, HVIT, 1.6))
        pg.add(arrow(mx + 28, Y + 32, mx - 28, Y + 32, SEK, 1.6))
    pg.add(t(1048, Y - 12, "Kundene", 16, 700, HVIT, "d"))
    pg.add(t(1048, Y + 22, "Etterspørsel 4, så 8 i uke 5", 15, 600, HVIT, "c"))
    pg.add(t(1048, Y + 42, "Studentene ser den ikke", 14, 400, SEK, "c"))
    # Tabell venstre
    tx, ty = 32, 318
    pg.add(t(tx, ty, "Spillinnstillinger", 22, 800, HVIT, "d"))
    pg.add(para(tx + 220, ty - 1, "Kildene er uenige om forsinkelser. Dette er produktets standard.", 500, 15, 20, 400, SEK, "t", f=.46))
    rows = [("Startlager", "12"), ("Enheter i hvert ledd", "4"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"),
            ("Etterspørsel", "4, så 8 i uke 5"), ("Lagerkost", "0,50 kr"), ("Restordrekost", "1,00 kr"), ("Antall uker", "36"), ("Veiledede uker", "1–4")]
    y = ty + 36
    for i, (a, b) in enumerate(rows):
        col = i % 2
        row = i // 2
        cx = tx + col * 372
        yy = y + row * 46
        pg.add(line(cx, yy + 12, cx + 350, yy + 12, RAND, 1))
        pg.add(t(cx, yy, a, 17, 500, SEK, "t"))
        pg.add(rect(cx + 214, yy - 21, 136, 30, HVIT, 4))
        pg.add(t(cx + 342, yy, b, 16, 700, BLEKK, "c", "end"))
    # Valg
    y = ty + 288
    def seg(x, y, label, options, chosen, w=170):
        out = t(x, y, label, 18, 700, HVIT, "d")
        for i, o in enumerate(options):
            on = o == chosen
            out += rect(x + i * (w + 8), y + 12, w, 44, HVIT if on else "none", 6, HVIT if on else SEK, 1.4)
            if on:
                out += check(x + i * (w + 8) + 18, y + 34, BLEKK, .8)
            out += t(x + i * (w + 8) + (34 if on else 14), y + 40, o, 16, 700 if on else 500, BLEKK if on else HVIT, "c")
        return out
    pg.add(seg(tx, y, "KI-modus", ["LLM-spillere", "Regelbaserte"], "LLM-spillere"))
    pg.add(seg(tx + 372, y, "Debrief-modus", ["Gruppedebrief", "Personlig"], "Gruppedebrief", 170))
    y += 84
    pg.add(t(tx, y + 20, "Inaktivitetsgrense", 18, 700, HVIT, "d"))
    pg.add(rect(tx + 176, y, 90, 32, HVIT, 4) + t(tx + 258, y + 22, "24 t", 16, 700, BLEKK, "c", "end"))
    pg.add(t(tx, y + 48, "Så tar KI-spiller setet.", 14, 400, SEK, "c"))
    pg.add(t(tx + 372, y + 20, "Obligatorisk", 18, 700, HVIT, "d"))
    pg.add(rect(tx + 500, y, 60, 32, GUL, 16, BLEKK, 1) + f'<circle cx="{tx + 544}" cy="{y + 16}" r="11" fill="{BLEKK}"/>')
    pg.add(t(tx + 372, y + 48, "Merket vises for studentene. Slått på.", 14, 400, SEK, "c"))
    # Forhåndsvisning: Uke 1 med disse innstillingene, i kummens eget språk
    py0 = 920
    pg.add(t(tx, y + 92, "Slik ser Uke 1 ut med disse innstillingene", 18, 700, HVIT, "d"))
    pcfg = dict(W=740, sc=5, y0=py0, stave_w=26, hole_end=200, rise_end=250, slot_x=262, wf=1.5, right=732, stave_top=py0 - 80, stave_bot=py0 + 30,
                bottom=py0 + 116, step=5, stave_size=13, lw=3, minor=False)
    pg.add(f'<g transform="translate({tx},0)">')
    drawn, _ = kum(pg, pcfg, dict(lager=12, rest=0, swells=[(2, 4), (3, 4), (4, 4)]), anim=False)
    pg.add(drawn)
    pg.add(t(36, py0 - 12, "Lager 12", 18, 700, HVIT, "t"))
    psl = slots(pcfg, [4, 4, 4])
    for (x_, w_, q_), u_ in zip(psl, (2, 3, 4)):
        pg.add(t(x_ + w_ * .42, py0 - q_ * 5 - 6, q_, 17, 700, HVIT, "t", "middle"))
        pg.add(t(x_ + w_ / 2, py0 + 20, f"Uke {u_}", 14, 500, HVIT, "c", "middle"))
    pg.add(t(psl[-1][0] + psl[-1][1] + 16, py0 + 20, "På vei 12", 17, 700, HVIT, "d"))
    pg.add(button(36, py0 + 34, 250, 44, "Prøv i et testspill", "ut", 17))
    pg.add("</g>")
    # Datoer, tidslinje
    rx = 800
    ry = 318
    pg.add(t(rx, ry, "Datoer og Labtimer", 22, 800, HVIT, "d"))
    lx0, lx1 = rx + 20, 1400
    dayw = (lx1 - lx0) / 24
    TL = ry + 110
    day = lambda nov: lx0 + (nov - 24) * dayw
    deadlines = [(24, "Start", "ti. 24. nov", True), (38, "Spillfrist", "ti. 8. des", True), (41, "Debrief-frist", "fr. 11. des", True), (48, "Testfrist", "fr. 18. des", True)]
    for d, a, b, _ in deadlines:
        x = day(d)
        pg.add(rect(x - 3, TL - 26, 6, 26, GUL))
        anchor = "start" if d == 24 else ("end" if d == 48 else "middle")
        ax = x if d != 41 else x + 18
        ax = ax if d != 38 else x - 18
        pg.add(t(ax, TL - 52, a, 17, 700, HVIT, "d", anchor))
        pg.add(t(ax, TL - 33, b, 15, 500, HVIT, "c", anchor))
    labs = [(26, "to. 26. nov", "14:15"), (30, "ma. 30. nov", "10:15"), (33, "to. 3. des", "14:15"), (37, "ma. 7. des", "10:15")]
    for d, a, b in labs:
        x = day(d)
        pg.add(f'<circle cx="{n(x)}" cy="{TL}" r="8" fill="{HAV}" stroke="{HVIT}" stroke-width="2.4"/>')
        pg.add(t(x, TL + 30, a, 15, 500, HVIT, "c", "middle"))
        pg.add(t(x, TL + 48, b, 15, 500, SEK, "c", "middle"))
    pg.add(t(lx0, TL + 76, "Sirkel: Labtime, Datalab A2. Gul strek: Start og frister.", 14, 500, SEK, "c"))
    pg.add(t(lx0 + 400, TL + 76, "Legg til Labtime", 15, 700, HVIT, "c", extra='text-decoration="underline"'))
    # Fordeling
    fy = ry + 226
    pg.add(t(rx, fy, "Fordeling: 60 spill à 4", 22, 800, HVIT, "d"))
    pg.add(t(rx, fy + 26, "240 studenter fordelt tilfeldig. Ingen er låst før du bekrefter.", 16, 400, SEK, "t"))
    gx, gy = rx, fy + 44
    cols = 15
    cw = 40
    chh = 70
    pg.add(rect(gx, gy, cols * cw, 4 * chh, VANN, 4))
    d = ""
    for r_ in range(4):
        yy = gy + r_ * chh + 42
        if r_ % 2 == 0:
            d += (f"M{gx},{yy} " if r_ == 0 else "") + f"L{gx + cols * cw},{yy} "
        else:
            d += f"L{gx},{yy} "
        if r_ < 3:
            pass
    for i in range(60):
        cx = gx + (i % cols) * cw + cw / 2
        cy = gy + (i // cols) * chh
        pg.add(t(cx, cy + 18, i + 1, 14, 600 if i != 16 else 800, GUL if i == 16 else HVIT, "t", "middle"))
        for k in range(4):
            pg.add(f'<circle cx="{n(cx - 10.5 + k * 7)}" cy="{cy + 32}" r="3" fill="{GUL if i == 16 else HVIT}"/>')
    # Linja: kjeden, ned til tidslinja, gjennom alle 60 spill, inn i forhåndsvisningen
    yy0 = gy + 50
    dd = (f"M0,{Y} L1412,{Y} Q1424,{Y} 1424,{Y + 12} L1424,{TL - 12} Q1424,{TL} 1412,{TL} L800,{TL} Q788,{TL} 788,{TL + 12} "
          f"L788,{yy0 - 12} Q788,{yy0} 800,{yy0}")
    for r_ in range(4):
        yy = gy + r_ * chh + 50
        if r_ % 2 == 0:
            dd += f" L{gx + cols * cw - 8},{yy}"
            dd += f" Q{gx + cols * cw},{yy} {gx + cols * cw},{yy + 8} L{gx + cols * cw},{yy + chh - 8} Q{gx + cols * cw},{yy + chh} {gx + cols * cw - 8},{yy + chh}"
        else:
            dd += f" L{gx + 8},{yy}"
            if r_ < 3:
                dd += f" Q{gx},{yy} {gx},{yy + 8} L{gx},{yy + chh - 8} Q{gx},{yy + chh} {gx + 8},{yy + chh}"
    last = gy + 3 * chh + 50
    dd += f" L800,{last} Q788,{last} 788,{last + 12} L788,{py0 - 12} Q788,{py0} 776,{py0} L764,{py0}"
    pg.add(path(dd, HVIT, 2.6))
    # Fyrlyktene og sirklene må ligge over linja
    for i, r in enumerate(roles):
        pg.add(fyr(xs[i], Y, True, False, 1.4))
    for d_, a_, b_ in labs:
        pg.add(f'<circle cx="{n(day(d_))}" cy="{TL}" r="8" fill="{HAV}" stroke="{HVIT}" stroke-width="2.4"/>')
    for d_, _a, _b, _c in deadlines:
        pg.add(rect(day(d_) - 3, TL - 26, 6, 26, GUL))
    # Rulletabell eksempel
    ey = gy + 4 * chh + 30
    pg.add(t(gx, ey, "Spill 17: Ida (Detaljist), Sara (Grossist), Mikkel (Distributør), Jonas (Fabrikk)", 16, 600, HVIT, "c"))
    pg.add(button(gx, ey + 16, 200, 52, "Kjør på nytt", "ut", 18))
    pg.add(button(gx + 212, ey + 16, 240, 52, "Bekreft fordeling", "gul", 18))
    pg.add(t(gx + 464, ey + 40, "Reglene kan endres", 14, 500, SEK, "c"))
    pg.add(t(gx + 464, ey + 58, "fram til Start.", 14, 500, SEK, "c"))
    pg.add(button(1148, ey + 84, 260, 54, "Lagre Klasseøkt", "gul", 20))
    pg.add(t(1136, ey + 116, "Lagres som den står, uten endring.", 15, 500, SEK, "t", "end"))
    pg.save()


def page_hjem():
    pg = Page("04-student-hjem", 1000, 900, "Tidevann: Sara på mobil, første møte og hjem",
              "To telefoner. Venstre er Invitasjon og registrering. Høyre er hjem under spill med Spill 17, Grossist, "
              "de andre setene, seks steg på én linje, neste frist og Labtimer.")
    px1, px2 = 28, 582
    y = 26
    # Venstre
    pg.add(phone_open(pg, px1, y, 1.0))
    s = [wordmark(20, 58, 24)]
    s.append(t(18, 122, "Bård har invitert", 36, 800, HVIT, "d"))
    s.append(t(18, 162, "deg til IBE160.", 36, 800, HVIT, "d"))
    s.append(para(18, 198, "class-of-1994. Du skal spille en forsyningskjede sammen med tre andre. Det gjør du på mobilen, gjerne over flere kvelder.", 350, 17, 24, 400, HVIT, "t", f=.48))
    fy = 306
    s.append(t(18, fy, "Navn", 14, 500, SEK, "c") + rect(18, fy + 8, 354, 48, HVIT, 6) + t(32, fy + 39, "Sara Lien", 18, 600, BLEKK, "t"))
    s.append(t(18, fy + 82, "E-post fra Klasselista", 14, 500, SEK, "c") + rect(18, fy + 90, 354, 48, VANN, 6) + t(32, fy + 121, "sara.l@student.example", 17, 500, HVIT, "t"))
    s.append(t(18, fy + 164, "Lag passord", 14, 500, SEK, "c") + rect(18, fy + 172, 354, 48, HVIT, 6))
    for i in range(10):
        s.append(f'<circle cx="{36 + i * 15}" cy="{fy + 196}" r="4" fill="{BLEKK}"/>')
    s.append(button(18, fy + 238, 354, 58, "Opprett konto", "gul", 21))
    s.append(t(195, fy + 322, "Invitasjonen er gyldig i 14 dager.", 14, 500, SEK, "t", "middle"))
    wy = 700
    s.append(f'<path d="M0,{wy} L390,{wy} L390,844 L0,844 Z" fill="{VANN}"/>')
    s.append(path(f"M0,{wy} L392,{wy}", HVIT, 3.5))
    s.append(t(18, wy + 40, "Når du er inne, ser du setet ditt, de", 15, 400, HVIT, "t"))
    s.append(t(18, wy + 62, "andre tre og hva som skjer når.", 15, 400, HVIT, "t"))
    s.append(demodata(18, wy + 92))
    pg.add("".join(s))
    pg.add(phone_close())
    # Midten
    mx = px1 + 390 + 18
    pg.add(t(mx, 70, "Første møte", 18, 800, HVIT, "d"))
    pg.add(para(mx, 94, "Stille vann. Ingen tall ennå. Linja ligger klar.", 134, 14, 19, 400, SEK, "t", f=.47))
    pg.add(t(mx, 178, "Hjem under spill", 17, 800, HVIT, "d"))
    pg.add(para(mx, 202, "Samme linje, nå med fyrlykter og steg. Gul flate: noen venter på deg.", 134, 14, 19, 400, SEK, "t", f=.47))
    # Bro: fra vannlinja i første møte til kysten i spillet
    pg.add(path(f"M{px1 + 390},{y + 700} C{mx + 90},{y + 700} {mx + 40},{y + 268} {px2},{y + 268}", HVIT, 3))
    # Høyre
    pg.add(phone_open(pg, px2, y, 1.0))
    s = [t(18, 50, "Spill 17", 34, 800, HVIT, "d"), t(372, 33, "Grossist", 17, 700, HVIT, "d", "end"), t(372, 52, "class-of-1994", 13, 400, SEK, "c", "end")]
    # Venter på deg
    s.append(rect(18, 70, 354, 112, GUL, 10))
    s.append(t(34, 102, "Spillet venter på deg", 23, 800, BLEKK, "d"))
    s.append(t(34, 126, "Uke 11. Du er nest siste. Jonas venter også.", 15, 500, BLEKK, "t") if False else t(34, 126, "Uke 11. Jonas har heller ikke bestilt.", 15, 500, BLEKK, "t"))
    s.append(rect(34, 136, 322, 36, BLEKK, 6) + t(195, 160, "Gå til Uke 11", 18, 700, HVIT, "d", "middle"))
    # Seter
    chain = 268
    s.append(t(18, 212, "Setene", 17, 700, HVIT, "d"))
    light = [("Detaljist", "Ida", "Har bestilt", True), ("Grossist", "Sara (du)", "Venter", False), ("Distributør", "Mikkel", "Har bestilt", True), ("Fabrikk", "Jonas", "Venter 3 min", False)]
    for i, (rolle, navn, status, lit) in enumerate(light):
        cx = 54 + i * 94
        s.append(fyr(cx, chain, lit, False, 1.15))
        s.append(t(cx, chain + 20, rolle, 14, 600, HVIT, "c", "middle"))
        s.append(t(cx, chain + 37, navn, 13, 400, SEK, "c", "middle"))
        s.append(t(cx, chain + 53, status, 13, 400, HVIT if lit else SEK, "c", "middle"))
    # Linja + steg
    sty = 396
    s.append(t(18, sty - 22, "Stegene dine", 17, 700, HVIT, "d"))
    step = [("Klassespill", "nå", True), ("Debrief", "", False), ("Quiz", "", False), ("Replay", "", False), ("Individuell test", "", False), ("Rapport", "", False)]
    wy = sty + 6
    s.append(f'<path d="M0,{wy} L390,{wy} L390,844 L0,844 Z" fill="{VANN}"/>')
    # Dagens linje: fra kyst (venstre kant) gjennom stegene
    s.append(path(f"M0,{chain} L14,{chain} Q6,{chain} 6,{chain + 10} L6,{wy - 10} Q6,{wy} 16,{wy} L392,{wy}", HVIT, 3.5) if False else "")
    s.append(path(f"M0,{chain} L392,{chain}", HVIT, 3.5))
    s.append(path(f"M392,{chain} Q384,{chain} 384,{chain + 10} L384,{wy - 10} Q384,{wy} 374,{wy} L0,{wy}", HVIT, 3.5))
    col = 354 / 6
    for i, (name, tag, on) in enumerate(step):
        cx = 18 + i * col + col / 2
        if on:
            s.append(f'<circle cx="{n(cx)}" cy="{wy}" r="9" fill="{GUL}" stroke="{BLEKK}" stroke-width="1.5"/>')
        else:
            s.append(f'<circle cx="{n(cx)}" cy="{wy}" r="7" fill="{VANN}" stroke="{HVIT}" stroke-width="2"/>')
        words = {"Individuell test": ["Individuell", "test"]}.get(name, [name])
        for k, w in enumerate(words):
            s.append(t(cx, wy + 28 + k * 16, w, 13, 700 if on else 500, GUL if on else HVIT, "c", "middle"))
    s.append(t(18 + col / 2, wy + 45, "Nå", 13, 700, GUL, "c", "middle"))
    # Frist og lab
    y2 = wy + 104
    s.append(t(18, y2, "Neste frist", 15, 500, SEK, "c"))
    s.append(t(18, y2 + 30, "Spillfrist ti. 8. des", 25, 800, HVIT, "d"))
    s.append(t(18, y2 + 52, "Etterpå fullfører KI-spillere det som gjenstår.", 15, 400, SEK, "t"))
    y3 = y2 + 104
    s.append(t(18, y3, "Labtimer, Datalab A2", 17, 700, HVIT, "d"))
    labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    for i, l_ in enumerate(labs):
        cx = 18 + (i % 2) * 180
        yy = y3 + 28 + (i // 2) * 26
        s.append(t(cx, yy, l_, 16, 500, HVIT, "t"))
    s.append(demodata(18, y3 + 118))
    s.append(t(372, y3 + 118, "Pause og regler", 15, 600, HVIT, "c", "end", 'text-decoration="underline"'))
    pg.add("".join(s))
    pg.add(phone_close())
    pg.save()


# 09 Kontaktark
def page_alle():
    pg = Page("09-alle-sider", 2000, 1400, "Tidevann: alle andre sider",
              "Kontaktark med 21 sider gruppert per rolle. Én linje løper gjennom hver miniatyr, rad for rad.")
    pg.add(t(40, 60, "Alle andre sider: samme linje gjennom hele produktet", 36, 800, HVIT, "d"))
    pg.add(demodata(1960, 60, "end", size=14))
    CW, CH = 306, 206
    GX = 16
    x_of = lambda c: 40 + c * (CW + GX)
    groups = [
        ("Student", [
            ("Invitasjon og registrering", "Navn, passord, stille vann.", "inv"),
            ("Logg inn", "E-post og passord. Tilbake til setet ditt.", "login"),
            ("Regler før første ordre", "Null, grunn, dønning. Ett tall per Uke.", "regler"),
            ("Startoppgave", "Prøv kummen med én ordre før spillet.", "start"),
            ("Replay", "Spill alene mot tre merkede KI-spillere.", "replay"),
            ("Replay-gjennomgang", "Linja di med to øyeblikk, KI-merket.", "gjenn"),
            ("Individuell test", "Flervalg, tegne- og tabelloppgave, langsvar.", "test"),
            ("KI-vurdering", "Teller ikke, er aldri en karakter.", "vurd"),
            ("Studentrapport (PDF)", "Forklaring, øyeblikk, kurver, fullføring.", "pdf"),
            ("Alle spill side om side", "Etter Debrief: alle kjedene på samme skala.", "sammen"),
        ]),
        ("Faglærer", [
            ("Lærerhjem med klasser", "Hver Klasse som en stav med status.", "hjem"),
            ("Klasserapport", "Trakt og kostnader for hele Klassen.", "krapp"),
            ("Spillinnsikt, uke for uke", "Fire etasjer. Dra deg gjennom ukene.", "innsikt"),
            ("Studentside", "Sete, seks steg, Forklaring, forsøk.", "stud"),
            ("Spill alle side om side", "Plenum: 60 kurver, ingen navn.", "plenum"),
            ("Tverrklasse-statistikk", "Klasser på samme skala, kull mot kull.", "tverr"),
            ("Meldinger", "Til ett spill, en gruppe eller hele Klassen.", "meld"),
            ("Lærers testspill", "Prøv innstillingene mot tre KI-spillere.", "testspill"),
        ]),
        ("Admin", [
            ("Admin-område", "Klasser, tilganger og systemstatus.", "adm"),
            ("Brukere og roller", "Faglærer, assistent, student, admin.", "brukere"),
            ("KI-kostnad", "Bruk per Klasseøkt og modus.", "kikost"),
        ]),
    ]
    # Plassering
    pos = []
    row = 0
    rows_y = [112, 416, 748, 1052]
    # Student: 6 + 4, tegnforklaring i siste to celler
    cells = []
    for i, it in enumerate(groups[0][1]):
        cells.append((i % 6, i // 6, it))
    for i, it in enumerate(groups[1][1]):
        if i < 6:
            cells.append((i, 2, it))
        else:
            cells.append((i - 6, 3, it))
    for i, it in enumerate(groups[2][1]):
        cells.append((3 + i, 3, it))
    # Rolleoverskrifter
    pg.add(t(40, rows_y[0] - 14, "Student", 24, 800, HVIT, "d"))
    pg.add(t(40, rows_y[2] - 14, "Faglærer", 24, 800, HVIT, "d"))
    pg.add(t(x_of(3), rows_y[3] - 14, "Admin", 24, 800, HVIT, "d"))
    LY = 128  # linjehøyde i miniatyren
    # Miniatyrer
    for c, r, (title, sub, kind) in cells:
        x, y = x_of(c), rows_y[r]
        pg.add(rect(x, y, CW, CH, HAV, 4))
        pg.add(f'<path d="M{x},{y + LY} L{x + CW},{y + LY} L{x + CW},{y + CH} L{x},{y + CH} Z" fill="{VANN}"/>')
        pg.add(mini(pg, kind, x, y, CW, CH, LY))
        pg.add(t(x, y + CH + 24, title, 19, 800, HVIT, "d"))
        pg.add(t(x, y + CH + 46, sub, 15, 400, SEK, "t"))
    # Tegnforklaring
    lx = x_of(4)
    ly = rows_y[1]
    pg.add(t(lx, ly + 18, "Slik leses linja", 22, 800, HVIT, "d"))
    items = [("line", "Hvit linje: kjeden. Den brytes aldri."), ("oker", "Oker: tørr grunn. Restordre under null."), ("swell", "Dønning: det som er på vei, høyde er mengde."),
             ("gul", "Gul og stiplet: din ordre, ikke sendt ennå."), ("ki", "Sekskant og stiplet fyr: KI-spiller."), ("korall", "Korall: den eneste varselfargen.")]
    yy = ly + 50
    for k, lab in items:
        if k == "line":
            pg.add(line(lx, yy - 5, lx + 36, yy - 5, HVIT, 3.5))
        elif k == "oker":
            pg.add(rect(lx, yy - 13, 36, 16, OKER))
        elif k == "swell":
            pg.add(path(f"M{lx},{yy + 2} " + wave(lx, 36, 14, yy + 2), HVIT, 2.4))
        elif k == "gul":
            pg.add(path(f"M{lx},{yy + 2} " + wave(lx, 36, 14, yy + 2), GUL, 2.4, extra='stroke-dasharray="4 3"'))
        elif k == "ki":
            pg.add(hex_mark(lx + 16, yy - 5, GUL))
        elif k == "korall":
            pg.add(rect(lx, yy - 13, 36, 16, KORALL, 3))
        pg.add(t(lx + 48, yy, lab, 16, 500, HVIT, "t"))
        yy += 32
    # Den ene linja gjennom alle rader
    d = ""
    lastcols = [5, 3, 5, 5]
    for r in range(4):
        y = rows_y[r] + LY
        x0, x1 = x_of(0), x_of(5) + CW
        if r == 1:
            x1 = x_of(3) + CW
        if r % 2 == 0:
            d += (f"M0,{y} " if r == 0 else "") + f"L{x1},{y} "
        else:
            d += f"L{x0},{y} "
        if r < 3:
            ny = rows_y[r + 1] + LY
            if r % 2 == 0:
                edge = 1980 if r == 0 else 1980
                if r == 0:
                    # Rundt tegnforklaringen: tilbake i mellomrommet over raden, så ned foran den
                    g = rows_y[1] - 26
                    xr = x_of(4) - 8
                    d += (f"L1970,{y} Q1984,{y} 1984,{y + 14} L1984,{g - 14} Q1984,{g} 1970,{g} L{xr + 14},{g} Q{xr},{g} {xr},{g + 14} L{xr},{ny - 14} Q{xr},{ny} {xr - 14},{ny} ")
                else:
                    d += (f"L1970,{y} Q1984,{y} 1984,{y + 14} L1984,{ny - 14} Q1984,{ny} 1970,{ny} ")
            else:
                d += (f"L30,{y} Q16,{y} 16,{y + 14} L16,{ny - 14} Q16,{ny} 30,{ny} ")
    d += f"L{x_of(0) - 40},{rows_y[3] + LY}"
    pg.add(path(d, HVIT, 3))
    pg.save()


def mini(pg, kind, x, y, W, H, LY):
    """Lavdetalj-skisser. Innhold over linja, tall og stav under."""
    s = []
    A = lambda a, b, c, d: rect(x + a, y + b, c, d, HVIT, 3)
    Sx = lambda a, b, c, d: rect(x + a, y + b, c, d, "none", 3, SEK, 1.2)
    L = lambda a, b, txt, size=14, w=500, fill=HVIT, an="start": t(x + a, y + b, txt, size, w, fill, "c", an)
    B = lambda a, b, c, d, txt: rect(x + a, y + b, c, d, GUL, 4) + t(x + a + c / 2, y + b + d / 2 + 5, txt, 14, 700, BLEKK, "c", "middle")
    bar = lambda a, b, c: rect(x + a, y + b, c, 5, SEK, 2)
    wave_at = lambda a, w_, h: path(f"M{x + a},{y + LY} " + wave(x + a, w_, h, y + LY), HVIT, 2.4)
    if kind == "inv":
        s.append(L(14, 24, "Bård har invitert deg", 16, 700))
        s.append(A(14, 34, 170, 18) + A(14, 58, 170, 18) + B(198, 34, 92, 42, "Opprett"))
    elif kind == "login":
        s.append(A(70, 18, 166, 18) + A(70, 42, 166, 18) + B(70, 66, 166, 26, "Logg inn"))
    elif kind == "regler":
        s.append(rect(x + 12, y + 18, 14, H - 30, HVIT))
        s.append(L(36, 30, "Over null: Lager", 14) + L(36, 50, "Under null: Restordre", 14) + L(36, 70, "Dønning: på vei", 14) + L(36, 90, "Ett heltall per Uke", 14, 700))
    elif kind in ("start", "replay", "testspill"):
        s.append(rect(x + 8, y + 20, 14, H - 30, HVIT))
        s.append(f'<path d="M{x + 22},{y + LY} L{x + 110},{y + LY} C{x + 124},{y + LY} {x + 118},{y + LY + 38} {x + 90},{y + LY + 38} L{x + 22},{y + LY + 38} Z" fill="{OKER}"/>')
        s.append(wave_at(130, 46, 22) + wave_at(180, 46, 40))
        if kind == "start":
            s.append(L(32, 34, "Startoppgave", 15, 700))
            s.append(B(232, 26, 62, 30, "Send"))
        elif kind == "replay":
            for k in range(3):
                s.append(fyr(x + 44 + k * 34, y + 62, True, True, .7))
            s.append(L(150, 30, "3 KI-spillere", 14, 700, GUL))
        else:
            for k in range(3):
                s.append(fyr(x + 44 + k * 34, y + 62, True, True, .7))
            s.append(L(150, 30, "Testspill, teller ikke", 14, 700, HVIT))
        s.append(t(x + 36, y + LY + 30, "13", 26, 800, BLEKK, "d"))
    elif kind == "gjenn":
        s.append(wave_at(40, 90, 62) + wave_at(150, 90, 34))
        s.append(hex_mark(x + 20, y + 22, GUL) + L(34, 27, "KI-generert, kan ta feil", 14, 600))
        s.append(L(14, H - 24, "Uke 9", 14) + L(150, H - 24, "Uke 22", 14))
    elif kind == "test":
        s.append(L(14, 22, "Flervalg", 14, 700))
        for k in range(3):
            s.append(f'<circle cx="{x + 22}" cy="{y + 36 + k * 18}" r="5" fill="{GUL if k == 1 else "none"}" stroke="{HVIT}" stroke-width="1.5"/>' + bar(34, 33 + k * 18, 56))
        s.append(L(112, 22, "Tegn Lager", 14, 700))
        s.append(Sx(112, 30, 86, 62))
        s.append(path(f"M{x + 116},{y + 84} L{x + 136},{y + 84} L{x + 154},{y + 50} L{x + 194},{y + 44}", GUL, 2))
        s.append(L(212, 22, "Langsvar", 14, 700))
        for k in range(4):
            s.append(bar(212, 34 + k * 14, 80))
        s.append(L(14, H - 18, "Egen Uke 11 inngår i spørsmålene", 14, 500))
    elif kind == "vurd":
        s.append(rect(x + 14, y + 16, 120, 26, KORALL, 4) + L(22, 34, "Teller ikke", 15, 700, BLEKK))
        s.append(hex_mark(x + 152, y + 29, GUL) + L(166, 34, "KI-generert", 14, 700))
        for k in range(3):
            s.append(bar(14, 56 + k * 13, 270 - k * 40))
        s.append(L(14, H - 22, "Aldri en karakter", 15, 600))
    elif kind == "pdf":
        s.append(rect(x + 110, y + 12, 96, 146, HVIT, 2))
        s.append(path(f"M{x + 110},{y + 70} C{x + 140},{y + 70} {x + 150},{y + 44} {x + 170},{y + 44} S{x + 190},{y + 70} {x + 206},{y + 70}", BLEKK, 2))
        for k in range(3):
            s.append(rect(x + 120, y + 84 + k * 13, 76 - k * 8, 5, BLEKK, 2))
        s.append(L(14, 34, "Sara", 15, 700) + L(14, 54, "PDF", 14))
    elif kind == "sammen":
        for k in range(6):
            xx = 20 + k * 46
            s.append(wave_at(xx, 36, 18 + (k * 17) % 50))
        s.append(L(14, H - 22, "Spill 17 er uthevet for deg", 14, 600))
    elif kind == "hjem":
        for k, name in enumerate(("class-of-1994", "class-of-1995")):
            yy = 16 + k * 40
            s.append(L(20, yy + 16, name, 15, 700) + L(20, yy + 33, "60 spill, 41 ferdig" if k == 0 else "Ikke startet", 14, 400, SEK))
            s.append(rect(x + 196, y + yy + 4, 92, 12, "none", 0, HVIT, 1.2))
            if k == 0:
                s.append(rect(x + 196, y + yy + 4, 62, 12, HVIT))
    elif kind == "krapp":
        d = f"M{x},{y + 34} L{x + 70},{y + 34} L{x + 70},{y + 62} L{x + 130},{y + 62} L{x + 130},{y + 82} L{x + 190},{y + 82} L{x + 190},{y + 100} L{x + 250},{y + 100} L{x + 250},{y + 120} L{x + 306},{y + 120}"
        s.append(path(d, HVIT, 2.4))
        s.append(L(14, 22, "240", 18, 700) + L(14, H - 22, "Studenter per steg, kostnad per Rolle", 14))
    elif kind == "innsikt":
        for k, r in enumerate(("Fabrikk", "Distributør", "Grossist", "Detaljist")):
            yy = 22 + k * 22
            vals = series(r)
            scx = 186 / 35
            d = "M" + " L".join(f"{n(x + 96 + i * scx)},{n(y + yy - vals[i] * .55)}" for i in range(36))
            s.append(path(d, HVIT, 1.6))
            s.append(L(12, yy + 3, r, 14, 500))
        s.append(line(x + 150, y + 6, x + 150, y + H - 8, GUL, 2) + L(158, H - 16, "Uke 11", 14, 700, GUL))
    elif kind == "stud":
        s.append(L(14, 24, "Sara Lien, Spill 17", 16, 700) + L(14, 44, "Grossist. Debrief ferdig.", 14))
        for k in range(6):
            cx = 26 + k * 50
            s.append(f'<circle cx="{x + cx}" cy="{y + LY}" r="6" fill="{GUL if k < 3 else VANN}" stroke="{HVIT}" stroke-width="1.6"/>')
        s.append(L(14, H - 20, "Forklaring, 2 forsøk på quiz", 14))
    elif kind == "plenum":
        for k in range(12):
            cx = 14 + (k % 6) * 48
            cy = 16 + (k // 6) * 40
            s.append(path(f"M{x + cx},{y + cy + 30} c10,0 12,{-10 - (k * 7) % 20} 22,{-10 - (k * 7) % 20} s8,{10 + (k * 7) % 20} 18,{10 + (k * 7) % 20}", SEK, 1.6))
        s.append(L(14, H - 22, "Alle 60 på storskjerm", 14, 600))
    elif kind == "tverr":
        for k, off in enumerate((0, 16, 34)):
            s.append(path(f"M{x + 10},{y + 90 - off} C{x + 80},{y + 80 - off} {x + 140},{y + 30 - off * .4} {x + 200},{y + 44 - off * .3} S{x + 270},{y + 60 - off * .5} {x + 296},{y + 60 - off * .5}", SEK if k else HVIT, 1.8))
        s.append(L(14, H - 22, "Kull for kull", 14, 600))
    elif kind == "meld":
        for k, (to, msg) in enumerate((("Spill 2", "Noah, setet ditt venter"), ("Alle", "Labtime to. 14:15"), ("Spill 21", "Husk avtalen i kveld"))):
            yy = 22 + k * 26
            s.append(L(14, yy, to, 15, 700) + L(84, yy, msg, 14))
    elif kind == "adm":
        for k, lab in enumerate(("Klasser", "Tilganger", "Systemstatus")):
            s.append(L(20, 28 + k * 24, lab, 15, 600))
        s.append(check(x + 262, y + 74, GUL))
    elif kind == "brukere":
        for k, (nm, ro) in enumerate((("Bård", "Faglærer"), ("Assistent", "Assistent"), ("Sara", "Student"))):
            yy = 26 + k * 24
            s.append(L(20, yy, nm, 15, 700) + L(150, yy, ro, 14))
    elif kind == "kikost":
        heights = [18, 34, 26, 52, 42, 60]
        for k, h in enumerate(heights):
            s.append(rect(x + 26 + k * 44, y + LY - h, 26, h, SEK))
        s.append(L(14, H - 22, "Per Klasseøkt og KI-modus", 14, 600))
    return "".join(s)


if __name__ == "__main__":
    print("Kontrast hvit/vann", round(contrast(HVIT, VANN), 2), "sek/vann", round(contrast(SEK, VANN), 2),
          "sek/hav", round(contrast(SEK, HAV), 2), "blekk/oker", round(contrast(BLEKK, OKER), 2),
          "blekk/gul", round(contrast(BLEKK, GUL), 2), "blekk/korall", round(contrast(BLEKK, KORALL), 2),
          "gul/hav", round(contrast(GUL, HAV), 2), "hvit/grunt", round(contrast(HVIT, GRUNT), 2))
    page_landing()
    page_klasse()
    page_oekt()
    page_hjem()
    page_spill()
    page_dyn()
    page_debrief()
    page_oversikt()
    page_alle()
    print("Ferdig")
