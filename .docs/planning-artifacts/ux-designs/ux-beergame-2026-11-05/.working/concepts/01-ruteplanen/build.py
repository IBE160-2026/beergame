"""Konsept 01 Ruteplan. Genererer 9 SVG-er fra ../_shared/fixture.json.

Grafisk grunnregel gjennom hele konseptet (Ibry/Marey-diagram):
  helning = forsinkelse, strekbredde = antall kasser, sporbredde = Lager og Restordre.
  Rødt stiplet = Ordre (det noen ber om). Marineblått heltrukket = kasser (det som finnes).
"""
import html
import json
import random
import textwrap
from pathlib import Path

HERE = Path(__file__).parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WEEKS = FX["weeks"]
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAMES = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

# Palett
PAPER = "#E4ECE7"   # ingeniørpapir
PAPER2 = "#F1F5F2"  # ubrukt papir, framtid
VEIL = "#D5E0DA"    # veiledede uker
GRID = "#C4D2CB"
GRID2 = "#9DB2A8"
INK = "#10264B"     # marineblått blekk
INK2 = "#384E6E"
RED = "#BE1224"     # signalrød
YEL = "#F5B800"     # signalgul
WHITE = "#FFFFFF"

KW = 0.46   # px strekbredde per kasse, telefon
KB = 1.2    # px sporbredde per kasse

FONT_URL = ("https://fonts.googleapis.com/css2?family=Overpass:wght@400;500;600;700;800"
            "&amp;family=Barlow+Condensed:wght@500;600;700&amp;display=swap")
FAM_O = "Overpass, 'Trebuchet MS', 'Segoe UI', sans-serif"
FAM_B = "'Barlow Condensed', 'Arial Narrow', 'Segoe UI', sans-serif"


# ---------- data ----------
def seat(w, role="Grossist"):
    return WEEKS[w - 1]["seats"][role]


def val(w, key, role="Grossist", default=4):
    return seat(w, role)[key] if 1 <= w <= 36 else default


def kr(v):
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return s + " kr"


def tus(v):
    return f"{v:,}".replace(",", " ")


# ---------- svg-primitiver ----------
def esc(s):
    return html.escape(str(s), quote=False)


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def T(x, y, s, sz=14, wt=500, fill=INK, a="start", f="o", halo=None, extra=""):
    cls = "c01-o" if f == "o" else "c01-b"
    h = f' paint-order="stroke" stroke="{halo}" stroke-width="4" stroke-linejoin="round"' if halo else ""
    return (f'<text x="{num(x)}" y="{num(y)}" font-size="{sz}" font-weight="{wt}" fill="{fill}" '
            f'text-anchor="{a}" class="{cls}"{h} {extra}>{esc(s)}</text>')


def TL(x, y, text, n, lh, **kw):
    lines = text if isinstance(text, list) else textwrap.wrap(text, n)
    return "".join(T(x, y + i * lh, ln, **kw) for i, ln in enumerate(lines))


def R(x, y, w, h, fill="none", stroke=None, sw=1, rx=0, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    r = f' rx="{rx}"' if rx else ""
    return f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="{fill}"{st}{r} {extra}/>'


def L(x1, y1, x2, y2, c=INK, sw=1, extra=""):
    return f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" stroke="{c}" stroke-width="{num(sw)}" {extra}/>'


def P(d, fill="none", c=None, sw=1, extra=""):
    st = f' stroke="{c}" stroke-width="{num(sw)}"' if c else ""
    return f'<path d="{d}" fill="{fill}"{st} {extra}/>'


def C(x, y, r, fill=INK, c=None, sw=1):
    st = f' stroke="{c}" stroke-width="{sw}"' if c else ""
    return f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="{fill}"{st}/>'


def order_line(x1, y1, x2, y2, q, kw=KW, op=1.0, c=RED, extra=""):
    w = max(0.8, q * kw)
    d1, d2 = max(5, w * 1.5), max(3, w * 0.7)
    return L(x1, y1, x2, y2, c, w, f'stroke-dasharray="{num(d1)} {num(d2)}" opacity="{op}" {extra}')


def goods_line(x1, y1, x2, y2, q, kw=KW, op=1.0, c=INK, extra=""):
    return L(x1, y1, x2, y2, c, max(0.8, q * kw), f'opacity="{op}" stroke-linecap="butt" {extra}')


class Page:
    def __init__(self, name, W, H, title, desc):
        self.name, self.W, self.H, self.title, self.desc = name, W, H, title, desc
        self.defs, self.b, self.n = [], [], 0
        self.defs.append(
            f'<pattern id="{self.id("hr")}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="6" height="6" fill="#F6D9DC"/><rect width="3" height="6" fill="{RED}"/></pattern>')
        self.defs.append(
            f'<pattern id="{self.id("hn")}" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
            f'<rect width="7" height="7" fill="{PAPER}"/><rect width="1.6" height="7" fill="{GRID2}"/></pattern>')
        self.defs.append(
            f'<pattern id="{self.id("hy")}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="8" height="8" fill="{YEL}"/><rect width="2" height="8" fill="{INK}" opacity=".85"/></pattern>')
        self.defs.append(
            f'<pattern id="{self.id("gr")}" width="24" height="24" patternUnits="userSpaceOnUse">'
            f'<path d="M24 0H0V24" fill="none" stroke="{GRID}" stroke-width=".7"/></pattern>')

    def id(self, x):
        return f"c01-{self.name}-{x}"

    def url(self, x):
        return f"url(#{self.id(x)})"

    def uid(self, x="u"):
        self.n += 1
        return self.id(f"{x}{self.n}")

    def add(self, *parts):
        self.b.extend(parts)

    def paper(self):
        self.add(R(0, 0, self.W, self.H, PAPER), R(0, 0, self.W, self.H, self.url("gr")))

    def save(self):
        css = (f"@import url('{FONT_URL}');"
               f".c01-o{{font-family:{FAM_O};font-variant-numeric:tabular-nums lining-nums;font-feature-settings:'tnum' 1,'lnum' 1}}"
               f".c01-b{{font-family:{FAM_B};font-variant-numeric:tabular-nums lining-nums;font-feature-settings:'tnum' 1,'lnum' 1}}")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" font-family="{FAM_O}">'
               f"<title>{esc(self.title)}</title><desc>{esc(self.desc)}</desc>"
               f"<style>{css}</style><defs>{''.join(self.defs)}</defs>{''.join(self.b)}</svg>")
        path = {"landing": "01-landing", "klasse": "02-laerer-klasse", "oppsett": "03-laerer-spill",
                "hjem": "04-student-hjem", "spill": "05-spill", "dyn": "06-spilldynamikk",
                "debrief": "07-debrief", "oversikt": "08-laerer-oversikt", "alle": "09-alle-sider"}[self.name]
        (HERE / f"{path}.svg").write_text(svg, encoding="utf-8")


# ---------- ikoner, tegnet som former ----------
def sema(x, y, st="stopp", s=1.0):
    """Armsignal: vannrett arm = stopp, hevet arm = fri. Form bærer status, ikke bare farge."""
    o = [L(x + 3 * s, y, x + 3 * s, y + 24 * s, INK, 1.6 * s), L(x, y + 24 * s, x + 6 * s, y + 24 * s, INK, 1.6 * s)]
    if st == "stopp":
        o.append(R(x + 3 * s, y + 3 * s, 14 * s, 5 * s, RED))
        o.append(R(x + 12 * s, y + 3 * s, 2 * s, 5 * s, WHITE))
    else:
        o.append(f'<g transform="rotate(-48 {num(x + 3 * s)} {num(y + 6 * s)})">'
                 + R(x + 3 * s, y + 3.5 * s, 14 * s, 5 * s, INK) + "</g>")
    return "".join(o)


def chip(x, y, s=12, c=INK):
    o = [R(x + s * .2, y + s * .2, s * .6, s * .6, "none", c, 1.3)]
    for t in (.38, .62):
        o.append(L(x + s * t, y, x + s * t, y + s * .2, c, 1.1))
        o.append(L(x + s * t, y + s * .8, x + s * t, y + s, c, 1.1))
        o.append(L(x, y + s * t, x + s * .2, y + s * t, c, 1.1))
        o.append(L(x + s * .8, y + s * t, x + s, y + s * t, c, 1.1))
    o.append(R(x + s * .4, y + s * .4, s * .2, s * .2, c))
    return "".join(o)


def ki_tag(x, y, txt="KI-spiller", sz=13, w=None, bg=WHITE):
    w = w or (len(txt) * sz * .47 + 26)
    h = sz + 8
    return (R(x, y, w, h, bg, INK, 1.2) + chip(x + 4, y + (h - sz) / 2, sz)
            + T(x + sz + 8, y + h - 6, txt, sz, 700, INK, f="b"))


def lock(x, y, s=16, c=INK):
    return (R(x, y + s * .45, s, s * .55, c, rx=1.5)
            + P(f"M{num(x + s * .22)} {num(y + s * .45)}V{num(y + s * .28)}a{num(s * .28)} {num(s * .28)} 0 0 1 {num(s * .56)} 0V{num(y + s * .45)}",
                c=c, sw=max(1.4, s * .11)))


def envelope(x, y, s=16, c=INK):
    return R(x, y + s * .15, s, s * .7, "none", c, 1.3) + P(f"M{x} {num(y + s * .15)}L{num(x + s / 2)} {num(y + s * .55)}L{x + s} {num(y + s * .15)}", c=c, sw=1.3)


def check(x, y, s=16, c=INK, sw=2.4):
    return P(f"M{x} {num(y + s * .55)}L{num(x + s * .38)} {num(y + s * .9)}L{x + s} {num(y + s * .1)}", c=c, sw=sw)


def cross(x, y, s=14, c=RED, sw=2.4):
    return L(x, y, x + s, y + s, c, sw) + L(x + s, y, x, y + s, c, sw)


def backspace(x, y, s=24, c=INK):
    return (P(f"M{num(x + s * .3)} {num(y + s * .15)}H{x + s}V{num(y + s * .85)}H{num(x + s * .3)}L{x} {num(y + s * .5)}Z", c=c, sw=1.6)
            + L(x + s * .48, y + s * .35, x + s * .78, y + s * .65, c, 1.6) + L(x + s * .78, y + s * .35, x + s * .48, y + s * .65, c, 1.6))


def wordmark(x, y, sz=22, c=INK):
    """Ordmerke med en skrå linje, som en togrute."""
    return (L(x, y - sz * .72, x + sz * .55, y, RED, sz * .13, f'stroke-dasharray="{sz*.2:.1f} {sz*.1:.1f}"')
            + L(x + sz * .08, y, x + sz * .63, y - sz * .72, c, sz * .13)
            + T(x + sz * .85, y, "Ruteplan", sz, 800, c))


def demo(x, y, a="start", c=INK2):
    return T(x, y, "Demodata", 13, 600, c, a=a, f="b")


def plate(x, y, w, h, fill=INK, rx=3):
    return R(x, y, w, h, fill, rx=rx) + R(x + 2, y + 2, w - 4, h - 4, "none", WHITE, .8, rx=max(rx - 1, 1), extra='opacity=".55"')


def btn(x, y, w, h, txt, kind="primary", sz=16):
    if kind == "primary":
        return R(x, y, w, h, RED, rx=3) + T(x + w / 2, y + h / 2 + sz * .36, txt, sz, 700, WHITE, a="middle")
    if kind == "ink":
        return R(x, y, w, h, INK, rx=3) + T(x + w / 2, y + h / 2 + sz * .36, txt, sz, 700, WHITE, a="middle")
    return R(x, y, w, h, PAPER2, INK, 1.4, rx=3) + T(x + w / 2, y + h / 2 + sz * .36, txt, sz, 600, INK, a="middle")


# ---------- datobåndet: fast, linjert, samme språk overalt ----------
DATES = [("Spillfrist", "ti. 8. des", 14), ("Debrief-frist", "fr. 11. des", 17), ("Testfrist", "fr. 18. des", 24)]
LABS = [(2, "to. 26. nov 14:15"), (6, "ma. 30. nov 10:15"), (9, "to. 3. des 14:15"), (13, "ma. 7. des 10:15")]
TODAY = 10  # fr. 4. des


def date_band(x, y, w, hi=None, labs=False, today=False, invite=False):
    """Til skala: 1 dag = fast avstand. Start ti. 24. nov til Testfrist fr. 18. des."""
    o = []
    d0 = -5 if invite else 0
    D = lambda d: x + (d - d0) / (24 - d0) * w
    o.append(L(x, y, x + w, y, INK, 2.4))
    for d in range(d0, 25):
        wk = (d + 1) % 7 == 6  # mandager: 24. nov er tirsdag
        o.append(L(D(d), y, D(d), y + (8 if wk else 4), INK, 1.2 if wk else .7))
    if labs:
        for d, lab in LABS:
            o.append(P(f"M{num(D(d))} {y - 3}l-5 -8h10Z", fill=WHITE, c=INK, sw=1.2))
    if invite:
        o.append(L(D(-5), y, D(-5), y + 14, INK, 2))
        o.append(T(D(-5), y + 30, "Invitasjon utløper", 14, 700, INK, f="b"))
        o.append(T(D(-5), y + 47, "to. 19. nov", 14, 500, INK2, f="b"))
    o.append(L(D(0), y, D(0), y + 14, INK, 2))
    o.append(T(D(0), y + 30, "Start", 14, 700, INK, f="b"))
    o.append(T(D(0), y + 47, "ti. 24. nov", 14, 500, INK2, f="b"))
    for name, date, d in DATES:
        strong = name == hi
        anc = "end" if d == 24 else "start"
        o.append(L(D(d), y - (6 if strong else 0), D(d), y + 14, RED if strong else INK, 3 if strong else 2))
        tx = D(d) + (4 if d == 14 else 0) if d != 24 else D(d)
        if d == 14:
            o.append(T(D(d), y + 30, name, 14, 800 if strong else 700, RED if strong else INK, a="end", f="b"))
            o.append(T(D(d), y + 47, date, 14, 500, INK2, a="end", f="b"))
        else:
            o.append(T(tx, y + 30, name, 14, 800 if strong else 700, RED if strong else INK, a=anc, f="b"))
            o.append(T(tx, y + 47, date, 14, 500, INK2, a=anc, f="b"))
    if today:
        o.append(C(D(TODAY), y, 5, YEL, INK, 1.4))
        o.append(T(D(TODAY), y - 12, "i dag fr. 4. des", 14, 600, INK, a="middle", f="b", halo=PAPER))
    return "".join(o)


def band_line(x, y, w, hi=None, sz=13):
    """Samme bånd i én linje, for telefon og smale flater."""
    o = [L(x, y, x + w, y, INK, 2)]
    labels = [f"{n} {d}" for n, d, _ in DATES]
    cw = [len(s) * sz * .405 for s in labels]
    gap = (w - sum(cw)) / 3
    cx = x
    for (n, d, _), label, width in zip(DATES, labels, cw):
        strong = n == hi
        o.append(L(cx, y, cx, y + 16, RED if strong else INK, 2.4 if strong else 1.4))
        o.append(T(cx + 4, y + 15, label, sz, 700 if strong else 500, RED if strong else INK, f="b"))
        cx += width + gap + 1
    return "".join(o)


# ---------- ruteplanen: spillets diagram ----------
def on_way_rows(now, pending=None):
    """Hva Sara vet kommer: neste levering er kjent, resten er ordren hun selv sendte."""
    rows = []
    for a in range(now + 1, now + 4):
        q = val(now, "neste_levering") if a == now + 1 else val(a - 4, "ordre")
        rows.append((a, q))
    if pending is not None:
        rows.append((now + 4, pending))
    return rows


def game_diagram(pg, gx, gy, axis, zone, r, w0, w1, now, pending=None, confirmed=None,
                 labels=True, kw=KW, role_signs=True, stem_sign="Grossist", lab=13, rolled=False):
    """Papiret skjæres opp ved nålinja: en mørk plattform bærer de seks tallene.
    Linjer som ankommer ender på plattformens overkant, linjer som går ut starter på underkanten."""
    Lx = gx + axis
    S = Lx + zone
    Rx = S + zone
    G = lab * 3.7 if labels else 0
    top = gy
    Yb = lambda w: top + (w - w0 + .5) * r
    Y = lambda w: Yb(w) + (G if w > now else 0)
    ny = Yb(now)
    Yd = ny + G
    bot = top + (w1 - w0 + 1) * r + G
    o = [R(Lx, top, 2 * zone, bot - top, PAPER), R(gx, top, axis, bot - top, PAPER)]
    o.append(R(gx, Yd, axis + 2 * zone, bot - Yd, PAPER2))
    if w0 <= 4:
        o.append(R(gx, top, axis + 2 * zone, Yb(4) + r / 2 - top, VEIL))
    for w in range(w0, w1 + 1):
        if w == now and G:
            continue
        heavy = w % 5 == 0
        o.append(L(Lx, Y(w), Rx, Y(w), GRID2 if heavy else GRID, .9 if heavy else .6))
    for i in range(9):
        c = GRID2 if i % 4 == 0 else GRID
        o.append(L(Lx + i * zone / 4, top, Lx + i * zone / 4, bot, c, .9 if i % 4 == 0 else .5))
    o.append(L(Lx, top, Lx, bot, INK2, 1.2))
    o.append(L(Rx, top, Rx, bot, INK2, 1.2))
    g = []
    dim = .36
    for w in range(w0 - 3, now + 1):
        g.append(order_line(Lx, Yb(w - 2), S, Yb(w), val(w, "innkommende_ordre"), kw, 1 if w == now else dim))
    for w in range(w0 - 3, now + 1):
        g.append(goods_line(S, Yb(w), Lx, Yb(w + 2), val(w, "sendt"), kw, 1 if w + 2 > now else dim))
    for w in range(w0 - 5, now):
        q = val(w, "ordre")
        g.append(order_line(S, Yb(w), Rx, Yb(w + 2), q, kw, 1 if w + 2 > now else dim))
        a = w + 4
        if a <= now + 1:
            g.append(goods_line(Rx, Yb(w + 2), S, Yb(a), val(a, "levering"), kw, 1 if a >= now else dim))
        else:
            g.append(L(Rx, Yb(w + 2), S, Yb(a), INK, max(1.2, q * kw), 'opacity=".24"'))
    q = pending if pending is not None else confirmed
    if q is not None:
        if pending is not None:
            g.append(L(S, Yb(now), Rx, Yb(now + 2), YEL, q * kw + 6))
        g.append(order_line(S, Yb(now), Rx, Yb(now + 2), q, kw, 1))
        g.append(L(Rx, Yb(now + 2), S, Yb(now + 4), INK, q * kw, 'opacity=".24"'))
    lines = "".join(g)
    c1, c2 = pg.uid("over"), pg.uid("under")
    pg.defs.append(f'<clipPath id="{c1}"><rect x="{num(Lx)}" y="{num(top)}" width="{num(2 * zone)}" height="{num(ny - top)}"/></clipPath>')
    pg.defs.append(f'<clipPath id="{c2}"><rect x="{num(Lx)}" y="{num(Yd)}" width="{num(2 * zone)}" height="{num(bot - Yd)}"/></clipPath>')
    o.append(f'<g clip-path="url(#{c1})">{lines}</g>')
    o.append(f'<g clip-path="url(#{c2})"><g transform="translate(0 {num(G)})">{lines}</g></g>')
    # sporet: bredden er Lager (høyre) og Restordre (venstre)
    for w in range(max(w0, 1), now + 1):
        d = seat(w)
        y1, h = Yb(w) - r, r
        if y1 < top:
            y1, h = top, Yb(w) - top
        if d["lager"]:
            o.append(R(S, y1, d["lager"] * KB, h, INK))
        if d["restordre"]:
            o.append(R(S - d["restordre"] * KB, y1, d["restordre"] * KB, h, pg.url("hr")))
    o.append(L(S, top, S, ny, INK, 2))
    o.append(L(S, Yd, S, bot, INK, 1.4, 'stroke-dasharray="2 4"'))
    # akse: tabellen over uker og egne ordre
    for w in range(w0, w1 + 1):
        y = Y(w) + lab * .36
        if w == now:
            continue
        o.append(T(gx + axis * .25, y, w, lab, 500, INK2, a="middle", f="b"))
        if w < now:
            q2 = val(w, "ordre")
            o.append(T(gx + axis * .72, y, q2, lab, 700 if q2 != 4 else 500, RED if q2 != 4 else INK, a="middle", f="b"))
    if labels:
        d = seat(now)
        o.append(R(gx, ny, axis + 2 * zone, G, INK))
        o.append(T(gx + axis * .25, ny + G / 2 + lab * .42, now, lab + 6, 800, WHITE, a="middle", f="b"))
        if q is not None:
            o.append(T(gx + axis * .72, ny + G / 2 + lab * .42, q, lab + 6, 800, YEL, a="middle", f="b"))
        cw = zone / 3
        cells = [("Ordre inn", d["innkommende_ordre"], S - 3 * cw), ("Sendt", d["sendt"], S - 2 * cw), ("Restordre", d["restordre"], S - cw),
                 ("Lager", d["lager"], S), ("Levering", d["levering"], S + cw), ("På vei", d["paa_vei_foer_ordre"], S + 2 * cw)]
        for name, v, cx in cells:
            if name == "Restordre" and v:
                o.append(R(cx, ny, cw, G, RED))
            o.append(T(cx + cw / 2, ny + lab + 4, name, lab, 600, WHITE if name in ("Restordre", "Lager") else "#CFDBEA", a="middle", f="b"))
            o.append(T(cx + cw / 2, ny + G - lab * .55, v, lab + 9, 800, WHITE, a="middle"))
        o.append(L(S, ny, S, Yd, WHITE, 2))
        for i, (a, q3) in enumerate(on_way_rows(now, q)):
            if a > w1:
                continue
            ghost = q is not None and a == now + 4
            y = Y(a) + lab * .36
            o.append(T(S - 7, y, q3, lab + (0 if ghost else 1), 700, INK2 if ghost else INK, a="end", f="b", halo=PAPER2))
            o.append(L(S - 3, Y(a), S + 3, Y(a), INK, 2))
            if i == 0:
                o.append(T(S - 22, y, "Neste levering", lab, 500, INK, a="end", f="b", halo=PAPER2))
    else:
        o.append(L(gx, ny, Rx, ny, INK, 2.2))
        tab_h = lab + 9
        o.append(R(gx, ny - tab_h / 2, axis, tab_h, INK))
        o.append(T(gx + axis * .25, ny + lab * .36, now, lab + 1, 700, WHITE, a="middle", f="b"))
        if q is not None:
            o.append(T(gx + axis * .72, ny + lab * .36, q, lab + 1, 700, YEL, a="middle", f="b"))
    hd = 0
    if rolled and w0 > 1:
        hd = 19
        hist = " ".join(str(val(w, "ordre")) for w in range(1, w0))
        o.append(R(gx, top - hd, axis + 2 * zone, hd, VEIL))
        o.append(L(gx, top - hd, Rx, top - hd, GRID2, 1) + L(gx, top - 1, Rx, top - 1, INK2, 1.2) + L(gx, top - 3.5, Rx, top - 3.5, GRID2, .8))
        o.append(T(gx + 8, top - 5.5, f"Uke 1–{w0 - 1} rullet opp. Ordre: {hist}", lab, 600, INK, f="b"))
    if role_signs:
        sy = top - 24 - hd
        o.append(T(gx + axis * .25, top - 7 - hd, "Uke", lab, 600, INK2, a="middle", f="b"))
        o.append(T(gx + axis * .72, top - 7 - hd, "Ordre", lab, 600, INK2, a="middle", f="b"))
        sg = len(stem_sign) * lab * .5 + 14
        o.append(plate(S - sg / 2, sy, sg, 20))
        o.append(T(S, sy + 15, stem_sign, lab, 700, WHITE, a="middle", f="b"))
        o.append(T(Lx + 3, top - 7 - hd, "Detaljist", lab, 600, INK, f="b"))
        o.append(T(Rx - 3, top - 7 - hd, "Distributør", lab, 600, INK, a="end", f="b"))
    return "".join(o), dict(L=Lx, S=S, R=Rx, top=top, bot=bot, Y=Y, Yd=Yd)


# ---------- telefon ----------
def phone(pg, x, y, s, inner):
    cid = pg.uid("skjerm")
    pg.defs.append(f'<clipPath id="{cid}"><rect width="390" height="844" rx="30"/></clipPath>')
    return (f'<g transform="translate({num(x)} {num(y)}) scale({s})">'
            + R(-8, -8, 406, 860, INK, rx=38)
            + f'<g clip-path="url(#{cid})">' + R(0, 0, 390, 844, PAPER) + inner + "</g></g>")


SIG_DEFAULT = [("fri", "Ida, bestilt"), ("stopp", "Deg, venter"), ("fri", "Mikkel, bestilt"), ("stopp", "Jonas, 3 min")]


def phone_head(now, total, sig=SIG_DEFAULT, sub="Spill 17, Grossist"):
    o = [R(0, 0, 390, 106, PAPER2), L(0, 106, 390, 106, INK, 1.4)]
    o.append(T(14, 42, f"Uke {now}", 31, 800, INK))
    o.append(T(142, 26, sub.split(", ")[0], 13, 600, INK2, f="b"))
    o.append(T(142, 42, sub.split(", ")[1], 15, 700, INK, f="b"))
    o.append(T(376, 24, "Totalkostnad", 13, 600, INK2, a="end", f="b"))
    o.append(T(376, 44, kr(total), 20, 800, INK, a="end"))
    for i, (st, tx) in enumerate(sig):
        x = 12 + i * 93
        if st == "ki":
            o.append(R(x - 2, 56, 88, 37, WHITE, INK, 1.2))
            o.append(chip(x + 1, 60, 16))
        else:
            o.append(sema(x, 58, st))
        o.append(T(x + 21, 69, ROLES[i], 13, 700, INK, f="b"))
        o.append(T(x + 21, 85, tx, 13, 700 if st == "ki" else 500, RED if st == "stopp" else (INK if st == "ki" else INK2), f="b"))
    return "".join(o)


def keypad(y, active=True):
    o = []
    kw_, kh = 68, 44
    for i, ch in enumerate("1234567890"):
        x = 12 + (i % 5) * (kw_ + 6)
        yy = y + (i // 5) * (kh + 6)
        o.append(R(x, yy, kw_, kh, PAPER2 if active else PAPER, GRID2 if active else GRID, 1, rx=3))
        o.append(T(x + kw_ / 2, yy + 29, ch, 21, 600, INK if active else INK2, a="middle"))
    return "".join(o)


def order_panel(y, now, value=None, pos=566):
    """Stasjonsskiltet: her settes ordrenummeret."""
    o = [R(0, y, 390, 844 - y, PAPER2), L(0, y, 390, y, INK, 1.4)]
    o.append(plate(12, y + 8, 132, 56))
    if value is not None:
        o.append(T(78, y + 50, value, 42, 800, WHITE, a="middle"))
    else:
        o.append(L(78, y + 20, 78, y + 54, YEL, 2.4))
    o.append(T(156, y + 28, f"Ordren din for Uke {now}", 14, 700, INK, f="b"))
    o.append(T(156, y + 47, "Ikke sendt ennå" if value is not None else "Hvor mange kasser?", 13, 500, INK2, f="b"))
    o.append(R(322, y + 14, 56, 44, PAPER2, GRID2, 1, rx=3))
    o.append(backspace(337, y + 24, 26))
    o.append(keypad(y + 74))
    by = y + 74 + 94 + 6
    if value is not None:
        o.append(btn(12, by, 366, 52, f"Bekreft ordre på {value} kasser", "primary", 18))
    else:
        o.append(R(12, by, 366, 52, PAPER, GRID2, 1.2, rx=3))
        o.append(T(195, by + 32, "Tast en ordre først", 16, 600, INK2, a="middle"))
    return "".join(o)


def game_screen(pg, state="B"):
    now = 11
    D, _ = game_diagram(pg, 0, 153, 58, 160, 33.2, 5, 15, now, pending=24 if state == "B" else None, rolled=True)
    return (phone_head(now, 68) + D + order_panel(566, now, 24 if state == "B" else None) + band_line(10, 811, 370))


# ---------- marey: hele planen, tid til høyre, Fabrikk øverst ----------
def lop(q):
    """Lavvolum-linjer svake, høyvolum sterke: floka skal tre fram av mønsteret."""
    return .26 if q <= 4 else min(.95, .34 + (q - 4) * .045)


def marey(pg, x, y, w, h, kw=.33, rails=True, sign_sz=14, labels=True, highlight=True, op=.86, upto=36):
    names = ["Produksjon", "Fabrikk", "Distributør", "Grossist", "Detaljist", "Kunde"]
    ys = {n: y + h * i / 5 for i, n in enumerate(names)}
    X = lambda t: x + (t - 1) / 35 * w
    cid = pg.uid("marey")
    pg.defs.append(f'<clipPath id="{cid}"><rect x="{x - 1}" y="{y - 6}" width="{w + 2}" height="{h + 12}"/></clipPath>')
    o = []
    for t in range(1, 37):
        c = GRID2 if t % 5 == 0 else GRID
        o.append(L(X(t), y, X(t), y + h, c, .8 if t % 5 == 0 else .4))
    g = []
    mb = 'style="mix-blend-mode:multiply"'
    chain = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
    for i, role in enumerate(chain):
        for t in range(-3, upto + 1):
            q = val(t, "ordre", role)
            up = names[names.index(role) - 1]
            g.append(order_line(X(t), ys[role], X(t + 2), ys[up], q, kw, lop(q), RED, mb))
            if i < 3:
                s = val(t, "sendt", chain[i + 1])
                g.append(goods_line(X(t), ys[up], X(t + 2), ys[role], s, kw, lop(s), INK, mb))
            else:
                g.append(goods_line(X(t + 2), ys[up], X(t + 4), ys[role], q, kw, lop(q), INK, mb))
    o.append(f'<g clip-path="url(#{cid})">{"".join(g)}</g>')
    # kundelinja: samme ene knekk som i klimaks-ruta
    gap = ys["Kunde"] - ys["Detaljist"]
    lv = lambda q: ys["Kunde"] - q * gap * .085
    o.append(L(x, lv(4), X(5), lv(4), RED, max(1.2, 4 * kw)))
    o.append(L(X(5), lv(4), X(5) + w * .012, lv(8), RED, max(1.6, 8 * kw)))
    o.append(L(X(5) + w * .012, lv(8), x + w, lv(8), RED, max(1.6, 8 * kw)))
    if highlight:
        o.append(L(X(11), ys["Grossist"], X(13), ys["Distributør"], YEL, 24 * kw + 5, f'opacity=".9" {mb}'))
    for n in names:
        o.append(L(x, ys[n], x + w, ys[n], INK, 1.5 if n in chain else .9))
    return "".join(o), ys, X


# ---------- laptop ----------
def laptop_game(pg, x, y):
    W_, H_ = 1040, 800
    o = [R(x - 10, y - 10, W_ + 20, H_ + 20, INK, rx=12), R(x, y, W_, H_, PAPER)]
    o.append(R(x, y, W_, 64, PAPER2) + L(x, y + 64, x + W_, y + 64, INK, 1.4))
    o.append(T(x + 18, y + 44, "Uke 11", 34, 800, INK))
    o.append(T(x + 150, y + 28, "Spill 17", 14, 600, INK2, f="b"))
    o.append(T(x + 150, y + 46, "Grossist, Sara", 16, 700, INK, f="b"))
    o.append(T(x + W_ - 18, y + 26, "Totalkostnad", 14, 600, INK2, a="end", f="b"))
    o.append(T(x + W_ - 18, y + 50, kr(68), 24, 800, INK, a="end"))
    # diagram
    D, _ = game_diagram(pg, x, y + 96, 62, 292, 37.6, 1, 15, 11, pending=24, kw=.6, lab=15)
    o.append(D)
    # kolonne
    cx = x + 662
    o.append(L(cx, y + 64, cx, y + H_ - 84, INK, 1))
    cx += 18
    o.append(T(cx, y + 92, "Uka venter på", 16, 700, INK, f="b"))
    for i, (st, tx) in enumerate(SIG_DEFAULT):
        yy = y + 104 + i * 34
        o.append(sema(cx, yy, st))
        o.append(T(cx + 26, yy + 18, ROLES[i], 15, 700, INK, f="b"))
        o.append(T(cx + 340, yy + 18, tx, 15, 600 if st == "stopp" else 500, RED if st == "stopp" else INK2, a="end", f="b"))
    yy = y + 272
    o.append(T(cx, yy - 16, "Samme tall som tabell", 16, 700, INK, f="b"))
    o.append(L(cx, yy - 8, cx + 340, yy - 8, INK, 1))
    d = seat(11)
    rows = [("Lager", d["lager"]), ("Restordre", d["restordre"]), ("Ordre inn", d["innkommende_ordre"]),
            ("Levering", d["levering"]), ("Sendt", d["sendt"]), ("På vei", d["paa_vei_foer_ordre"]), ("Neste levering", d["neste_levering"])]
    for i, (lb, v) in enumerate(rows):
        yr = yy + 12 + i * 25
        o.append(T(cx, yr, lb, 15, 500, INK, f="b"))
        o.append(T(cx + 340, yr, v, 16, 800, RED if lb == "Restordre" else INK, a="end"))
        o.append(L(cx, yr + 7, cx + 340, yr + 7, GRID2, .7))
    yy = y + 476
    o.append(plate(cx, yy, 150, 72))
    o.append(T(cx + 75, yy + 55, "24", 52, 800, WHITE, a="middle"))
    o.append(T(cx + 164, yy + 22, "Ordren din for Uke 11", 15, 700, INK, f="b"))
    o.append(T(cx + 164, yy + 42, "Tast tall på tastaturet.", 14, 500, INK2, f="b"))
    o.append(T(cx + 164, yy + 60, "Enter bekrefter.", 14, 500, INK2, f="b"))
    o.append(btn(cx, yy + 84, 340, 54, "Bekreft ordre på 24 kasser", "primary", 18))
    o.append(T(cx, yy + 160, "Kan ikke endres etterpå.", 14, 500, INK2, f="b"))
    # bånd
    o.append(date_band(x + 40, y + H_ - 62, W_ - 80, hi="Spillfrist"))
    return "".join(o)


# ---------- 05 spill ----------
def page_spill():
    pg = Page("spill", 1600, 1000, "Ruteplan: Spillskjermen, Uke 11",
              "Saras spor i ruteplanen midt i Uke 11 med 24 tastet inn. Tiden renner nedover. "
              "Hver Ordre er en rød stiplet linje oppstrøms, hver levering en blå linje tilbake. Linjer under nålinja er på vei. Samme skjerm på telefon og laptop.")
    pg.paper()
    pg.add(wordmark(46, 50, 26))
    pg.add(T(214, 50, "Spillskjermen, Uke 11", 22, 600, INK))
    pg.add(demo(1560, 50, "end"))
    pg.add(phone(pg, 52, 92, 1, game_screen(pg, "B")))
    pg.add(laptop_game(pg, 520, 92))
    # tegnforklaring under laptop
    x, y = 520, 930
    pg.add(order_line(x, y + 14, x + 70, y - 8, 8), T(x + 80, y + 8, "Ordre", 15, 700, RED, f="b"))
    pg.add(goods_line(x + 150, y + 14, x + 220, y - 8, 8), T(x + 230, y + 8, "Kasser", 15, 700, INK, f="b"))
    pg.add(L(x + 310, y + 14, x + 380, y - 8, INK, 5, 'opacity=".22"'), T(x + 390, y + 8, "På vei, ikke sendt ennå", 15, 600, INK, f="b"))
    pg.add(T(x + 590, y + 8, "Helning er forsinkelse. Bredde er antall kasser.", 15, 500, INK2, f="b"))
    return pg


# ---------- 06 spilldynamikk ----------
def wait_panel(y, now, q):
    o = [R(0, y, 390, 844 - y, PAPER2), L(0, y, 390, y, INK, 1.4)]
    o.append(plate(12, y + 8, 132, 56, INK2))
    o.append(T(78, y + 50, q, 42, 800, WHITE, a="middle"))
    o.append(lock(156, y + 12, 16))
    o.append(T(178, y + 26, "Ordren er sendt", 16, 700, INK, f="b"))
    o.append(T(156, y + 50, "Den kan ikke endres.", 14, 500, INK2, f="b"))
    yy = y + 82
    o.append(T(12, yy + 4, "Uka går videre når alle har bestilt.", 15, 600, INK, f="b"))
    sig = [("fri", "Ida", "bestilt"), ("fri", "Deg", "bestilt"), ("fri", "Mikkel", "bestilt"), ("stopp", "Jonas", "venter 3 min")]
    for i, (st, n, tx) in enumerate(sig):
        yr = yy + 14 + i * 30
        o.append(sema(14, yr, st, .85))
        o.append(T(38, yr + 17, f"{ROLES[i]}, {n}", 14, 700, INK, f="b"))
        o.append(T(376, yr + 17, tx, 14, 600, RED if st == "stopp" else INK2, a="end", f="b"))
    return "".join(o)


def pass_panel(y):
    """Ruta D: overgangen. Ruller én rad, aldri over 2 sek, kan hoppes over."""
    o = [R(0, y, 390, 844 - y, PAPER2), L(0, y, 390, y, INK, 1.4)]
    o.append(T(195, y + 56, "Uke 12", 44, 800, INK, a="middle"))
    o.append(T(195, y + 88, "Ruteplanen ruller én rad opp.", 16, 500, INK2, a="middle", f="b"))
    # rulle-pil
    o.append(P(f"M195 {y + 118}v-14m-7 7l7 -7l7 7", c=INK, sw=2))
    o.append(btn(107, y + 136, 176, 48, "Hopp over", "ghost", 17))
    return "".join(o)


def ki_panel(y):
    o = [R(0, y, 390, 844 - y, PAPER2), L(0, y, 390, y, INK, 1.4)]
    o.append(ki_tag(12, y + 10, "KI-spiller", 14))
    o.append(T(112, y + 25, "kjører Fabrikk nå", 15, 700, INK, f="b"))
    o.append(TL(12, y + 54, "Jonas var borte i 24 t mens dere ventet. Uka gikk videre, og spillet deres stopper ikke.", 48, 19, sz=14, wt=500, fill=INK, f="b"))
    o.append(btn(12, y + 96, 366, 42, "Sett Pause og avtal tid", "ghost", 16))
    o.append(T(12, y + 156, "Under Pause tar ingen KI-spiller over.", 14, 500, INK2, f="b"))
    # Jonas sin skjerm
    yy = y + 168
    o.append(R(12, yy, 366, 60, PAPER, INK, 1.2, rx=3))
    o.append(T(22, yy + 22, "Jonas ser:", 14, 700, INK, f="b"))
    o.append(T(22, yy + 42, "Gjelder fra neste Uke.", 13, 500, INK2, f="b"))
    o.append(btn(190, yy + 9, 178, 42, "Ta tilbake setet", "ink", 15))
    return "".join(o)


def end_screen(pg):
    o = [R(0, 0, 390, 844, PAPER2)]
    # hele Saras spor som en tynn søyle til høyre
    o.append(T(18, 50, "Spillet er ferdig", 30, 800, INK))
    o.append(T(18, 74, "Det gikk 36 uker. Nå kan du se det.", 15, 500, INK2, f="b"))
    o.append(L(0, 92, 390, 92, INK, 1.4))
    o.append(T(18, 126, "Kjeden totalt", 16, 700, INK, f="b"))
    o.append(T(18, 176, kr(FX["chain_total_cost"]), 44, 800, INK))
    o.append(L(18, 196, 372, 196, GRID2, 1))
    o.append(T(18, 224, "Per Rolle", 16, 700, INK, f="b"))
    mx = max(FX["total_cost_per_role"].values())
    for i, r_ in enumerate(ROLES):
        yy = 242 + i * 56
        v = FX["total_cost_per_role"][r_]
        o.append(T(18, yy + 14, r_ + (", deg" if r_ == "Grossist" else ""), 15, 700, INK, f="b"))
        o.append(T(372, yy + 15, kr(v), 16, 800, INK, a="end"))
        o.append(L(18, yy + 28, 18 + 354 * v / mx, yy + 28, INK, 9))
        o.append(L(18, yy + 38, 372, yy + 38, GRID, .7))
    # sporende: bufferstopp
    yy = 482
    o.append(L(18, yy + 60, 300, yy + 60, INK, 3))
    for i in range(16):
        o.append(L(24 + i * 18, yy + 53, 24 + i * 18, yy + 67, INK, 1.4))
    o.append(R(300, yy + 42, 7, 36, RED))
    o.append(L(307, yy + 46, 320, yy + 60, INK, 3))
    o.append(L(307, yy + 74, 320, yy + 60, INK, 3))
    o.append(T(18, yy + 28, "Sporet slutter her. Forklaringen venter.", 15, 600, INK, f="b"))
    o.append(TL(18, yy + 104, "Du skriver din egen Forklaring før dere får se hele ruteplanen sammen.", 44, 21, sz=16, wt=500, fill=INK, f="b"))
    o.append(btn(12, yy + 170, 366, 56, "Videre til Debrief", "primary", 18))
    o.append(band_line(10, 811, 370, hi="Debrief-frist"))
    return "".join(o)


def page_dyn():
    pg = Page("dyn", 2100, 1200, "Ruteplan: Spillets dynamikk",
              "Seks telefonruter: uka åpner, beslutningen, bekreftet, uka går videre, Jonas er borte, spillet slutter.")
    pg.paper()
    pg.add(wordmark(36, 54, 28))
    pg.add(T(226, 54, "Én Uke i ruteplanen, og det som kan skje mellom Ukene", 26, 600, INK))
    pg.add(demo(2064, 54, "end"))
    s = .8
    xs = [36 + i * (312 + 30.4) for i in range(6)]
    fy = 132
    titles = ["Uka åpner", "Beslutningen", "Bekreftet", "Uka går videre", "Jonas er borte", "Spillet slutter"]
    letters = "ABCDEF"
    notes = [
        "Levering og ordre treffer sporet. Tallene står på plattformen, der linjene ender. Under den: 16 kasser, tre linjer, ennå ikke framme.",
        "24 tastet. Linja tegnes mens du taster, tykk og gul, rett over de tre som allerede er på vei. Du ser den før du bekrefter.",
        "Linja skytes av gårde og låses. Armsignalene viser hvem kjeden venter på. Her venter du på Jonas, 3 min.",
        "Papiret ruller én rad, de eldste ukene rulles opp, og tallene lander i Uke 12. Aldri over 2 sek, kan hoppes over. Ingen slutt synes.",
        "Etter 24 t tar en KI-spiller setet, merket med brikke og tekst. Pause stanser det. Jonas kan ta setet tilbake fra neste Uke.",
        "Sporet ender i en bufferstopp. Kjedens totalkostnad kommer først, deretter per Rolle uten rangering, så Debrief.",
    ]
    # rutelinje mellom rutene
    path = "M" + " L".join(f"{num(x + 156)} {fy - 18}" for x in xs)
    pg.add(L(xs[0], fy - 18, xs[-1] + 312, fy - 18, INK, 2))
    for i, x in enumerate(xs):
        pg.add(R(x, fy - 34, 30, 30, INK, rx=2), T(x + 15, fy - 12, letters[i], 19, 800, WHITE, a="middle"))
        pg.add(R(x + 30, fy - 34, 180, 30, PAPER), T(x + 40, fy - 12, titles[i], 20, 700, INK, f="b"))
    pg.add(f'<circle r="6" fill="{YEL}" stroke="{INK}" stroke-width="1.5"><animateMotion dur="9s" repeatCount="indefinite" path="{path}"/></circle>')

    d11, _ = game_diagram(pg, 0, 153, 58, 160, 33.2, 5, 15, 11, rolled=True)
    a = phone_head(11, 68, [("stopp", "Ida, venter"), ("stopp", "Deg, venter"), ("stopp", "Mikkel, venter"), ("stopp", "Jonas, venter")]) + d11 + order_panel(566, 11) + band_line(10, 811, 370)
    pg.add(phone(pg, xs[0], fy, s, a))

    pg.add(phone(pg, xs[1], fy, s, game_screen(pg, "B")))

    d11c, g = game_diagram(pg, 0, 153, 58, 160, 33.2, 5, 15, 11, confirmed=24, rolled=True)
    mv = (f'<circle r="7" fill="{YEL}" stroke="{INK}" stroke-width="1.5"><animateMotion dur="2.6s" repeatCount="indefinite" '
          f'path="M{g["S"]} {num(g["Yd"])}L{g["R"]} {num(g["Y"](13))}"/></circle>')
    sigc = [("fri", "Ida, bestilt"), ("fri", "Deg, bestilt"), ("fri", "Mikkel, bestilt"), ("stopp", "Jonas, 3 min")]
    c = phone_head(11, 68, sigc) + d11c + mv + wait_panel(566, 11, 24) + band_line(10, 811, 370)
    pg.add(phone(pg, xs[2], fy, s, c))

    d12, g12 = game_diagram(pg, 0, 153, 58, 160, 33.2, 6, 16, 12, rolled=True)
    sigd = [("stopp", "Ida, venter"), ("stopp", "Deg, venter"), ("stopp", "Mikkel, venter"), ("stopp", "Jonas, venter")]
    d = phone_head(12, 88, sigd) + f"<g>{d12}</g>" + pass_panel(566) + band_line(10, 811, 370)
    pg.add(phone(pg, xs[3], fy, s, d))

    d14, _ = game_diagram(pg, 0, 153, 58, 160, 33.2, 8, 18, 14, confirmed=val(14, "ordre"), rolled=True)
    sige = [("fri", "Ida, bestilt"), ("fri", "Deg, bestilt"), ("fri", "Mikkel, bestilt"), ("ki", "KI-spiller")]
    e_head = phone_head(14, seat(14)["kost_sum"], sige)
    e = e_head + d14 + ki_panel(566) + band_line(10, 811, 370)
    pg.add(phone(pg, xs[4], fy, s, e))

    pg.add(phone(pg, xs[5], fy, s, end_screen(pg)))

    for x, note in zip(xs, notes):
        pg.add(TL(x, fy + 706, note, 40, 22, sz=17, wt=500, fill=INK, f="b"))

    # under rutene
    y = 958
    pg.add(L(36, y, 2064, y, INK, 2))
    pg.add(T(36, y + 44, "Hvorfor dette føles annerledes", 30, 800, INK))
    txt = [
        "Skjemaet er borte: det du fyller ut, er selve diagrammet. Det du bestilte for tre uker siden, ligger fremdeles i ruta som en linje som ikke har nådd stasjonen din, og den nye ordren legger seg oppå.",
        "Beslutningen tar sekunder fordi blikket bare trenger ett sted: der linjene møter sporet. Tallene står på plattformen rett under, og bredden på sporet er Lager og Restordre.",
        "Du ser aldri mer enn det som berører sporet ditt. Linjene forsvinner ut på kanten mot naboene, og ventingen vises med armsignaler, ikke med en stolpe mot slutten.",
        "Etter 36 uker og mange kvelder har du en plan du kan lese bakover: hele spillet står i ruta, og det er den samme ruta som åpnes i Debriefen.",
    ]
    for i, t_ in enumerate(txt):
        pg.add(TL(36 + i * 512, y + 88, t_, 56, 25, sz=19, wt=500, fill=INK, f="b"))
    return pg


# ---------- 07 debrief ----------
STEP_NAMES = ["Forklaring", "Etterspørsel", "Ruteplan", "Ditt øyeblikk", "Quiz"]


def debrief_head(i):
    o = [R(0, 0, 390, 62, PAPER2), L(0, 62, 390, 62, INK, 1.4)]
    o.append(T(14, 25, "Debrief, Spill 17", 15, 700, INK, f="b"))
    o.append(L(14, 42, 376, 42, INK, 2))
    for k in range(5):
        x = 14 + k * 90.5
        o.append(C(x, 42, 6 if k == i else 4, YEL if k == i else (INK if k < i else PAPER2), INK, 1.6))
    o.append(T(376, 25, STEP_NAMES[i], 15, 700, INK, a="end", f="b"))
    return "".join(o)


def step1(pg):
    o = [debrief_head(0)]
    o.append(TL(14, 100, ["Skriv Forklaringen din", "før du får se mer"], 30, 31, sz=26, wt=800, fill=INK))
    o.append(TL(14, 170, "Hva tror du kundene kjøpte, uke for uke? Hvorfor gikk lageret ditt som det gjorde?", 44, 21, sz=16, wt=500, fill=INK, f="b"))
    o.append(R(14, 220, 362, 158, WHITE, INK, 1.4, rx=2))
    o.append(TL(26, 248, "Jeg tror kundene kjøpte mye mer midtveis og sluttet etterpå. Derfor gikk jeg tom, og så kom alt på én gang.", 40, 22, sz=16, wt=500, fill=INK, f="b"))
    o.append(L(112, 298, 112, 316, INK, 1.6))
    o.append(T(366, 368, "Bare du ser dette", 13, 500, INK2, a="end", f="b"))
    # lukker
    o.append(R(14, 396, 362, 196, pg.url("hn"), INK, 1.4))
    o.append(R(44, 432, 302, 124, PAPER2, INK, 1.4))
    o.append(lock(60, 448, 26))
    o.append(T(98, 464, "Etterspørselen er låst", 17, 800, INK))
    o.append(TL(60, 492, "Den åpnes når du har levert Forklaringen.", 34, 20, sz=15, wt=500, fill=INK, f="b"))
    o.append(T(60, 540, "Ida har levert. Jonas skriver.", 14, 500, INK2, f="b"))
    o.append(btn(14, 608, 362, 54, "Lever Forklaringen", "primary", 18))
    o.append(T(14, 688, "Du ser ikke de andres Forklaringer.", 14, 500, INK2, f="b"))
    o.append(band_line(10, 811, 370, hi="Debrief-frist"))
    return "".join(o)


def step2(pg):
    o = [debrief_head(1)]
    o.append(R(0, 62, 390, 782, PAPER2))
    o.append(TL(14, 102, ["Dette var hele", "etterspørselen"], 30, 31, sz=26, wt=800, fill=INK))
    px, top, r = 118, 176, 10
    Y = lambda w: top + (w - 1) * r
    for w in range(1, 37):
        o.append(L(70, Y(w), 330, Y(w), GRID2 if w % 5 == 0 else GRID, .8 if w % 5 == 0 else .4))
        if w in (1, 5, 10, 15, 20, 25, 30, 35):
            o.append(T(62, Y(w) + 4, w, 13, 500, INK2, a="end", f="b"))
    o.append(T(62, top - 12, "Uke", 13, 600, INK2, a="end", f="b"))
    # ett lite knekk
    x4, x8 = px, px + 4 * 12
    d = f"M{x4} {top}V{num(Y(5))}"
    o.append(L(x4, top, x4, Y(5), RED, 4 * .9))
    o.append(L(x4, Y(5), x8, Y(5.9), RED, 8 * .9))
    length = Y(36) - Y(5.9)
    o.append(f'<line x1="{x8}" y1="{num(Y(5.9))}" x2="{x8}" y2="{num(Y(36))}" stroke="{RED}" stroke-width="7.2" stroke-dasharray="{num(length)}">'
             f'<animate attributeName="stroke-dashoffset" from="{num(length)}" to="0" dur="2.4s" fill="freeze"/></line>')
    o.append(T(x4 + 12, Y(2) + 5, "4 kasser i uka", 17, 800, RED))
    o.append(T(x8 + 14, Y(7) + 8, "8 kasser i uka", 17, 800, RED))
    o.append(T(x8 + 14, Y(9) + 8, "fra uke 5, stabilt", 15, 600, INK, f="b"))
    o.append(T(x8 + 14, Y(11) + 6, "resten av spillet", 15, 600, INK, f="b"))
    o.append(L(14, 546, 376, 546, INK, 1))
    o.append(TL(14, 576, "Det er hele endringen. Én gang, fra 4 til 8.", 44, 22, sz=17, wt=700, fill=INK, f="b"))
    o.append(T(14, 616, "Du skrev:", 14, 600, INK2, f="b"))
    o.append(TL(14, 636, "«Jeg tror kundene kjøpte mye mer midtveis og sluttet etterpå.»", 46, 20, sz=15, wt=500, fill=INK, f="b"))
    o.append(T(14, 696, "Øvelsen heter Beer Game.", 15, 600, INK, f="b"))
    o.append(btn(14, 722, 362, 52, "Åpne hele ruteplanen", "primary", 18))
    o.append(band_line(10, 811, 370, hi="Debrief-frist"))
    return "".join(o)


def step3(pg):
    o = [debrief_head(2), R(0, 62, 390, 782, PAPER2)]
    o.append(T(14, 98, "Hele ruteplanen", 26, 800, INK))
    o.append(TL(14, 122, "Papiret er snudd: tiden går mot høyre, Kunde nederst.", 46, 19, sz=15, wt=500, fill=INK, f="b"))
    x, y, w, h = 16, 176, 358, 520
    D, ys, X = marey(pg, x, y, w, h, kw=.2, highlight=False)
    o.append(R(x, y, w, h, PAPER) + D)
    amp = FX["amplification"]
    for n in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        o.append(T(x + 4, ys[n] - 7, n, 15, 800, INK, f="b", halo=PAPER))
        o.append(T(x + w - 4, ys[n] - 7, f"{str(amp[n]).replace('.', ',')}×", 19, 800, RED, a="end", halo=PAPER))
    o.append(T(x + 4, ys["Produksjon"] - 7, "Produksjon", 13, 600, INK2, f="b", halo=PAPER2))
    o.append(T(x + 4, ys["Kunde"] + 18, "Kunde: 4, så 8 fra uke 5", 15, 800, RED, f="b"))
    o.append(T(x + w, ys["Kunde"] + 18, "uke 36", 13, 500, INK2, a="end", f="b"))
    o.append(TL(14, 738, "Samme to uker mellom hvert spor. Ingen så hele planen. Svingningene vokser for hvert ledd.", 46, 20, sz=15, wt=600, fill=INK, f="b"))
    o.append(band_line(10, 811, 370, hi="Debrief-frist"))
    return "".join(o)


def step4(pg):
    o = [debrief_head(3)]
    o.append(T(14, 98, "Ditt øyeblikk: Uke 11", 25, 800, INK))
    D, _ = game_diagram(pg, 10, 136, 44, 142, 22, 7, 15, 11, confirmed=24, labels=False, kw=.36, role_signs=False, lab=13)
    o.append(T(54, 130, "Detaljist", 13, 600, INK, f="b"))
    o.append(T(196, 130, "Du", 13, 700, INK, a="middle", f="b"))
    o.append(T(338, 130, "Distributør", 13, 600, INK, a="end", f="b"))
    o.append(D)
    d = seat(11)
    y = 352
    late_cost = sum(seat(w)["lager"] for w in range(25, 37)) * .5
    o.append(T(14, y, "Du så", 15, 800, INK))
    o.append(T(100, y, f"Lager {d['lager']}, Restordre {d['restordre']}, ordre inn {d['innkommende_ordre']}", 15, 500, INK, f="b"))
    o.append(T(100, y + 20, f"16 på vei, ikke framme ennå", 15, 500, INK, f="b"))
    o.append(T(14, y + 48, "Du bestilte", 15, 800, RED))
    o.append(T(100, y + 48, "24", 19, 800, RED))
    o.append(L(14, y + 60, 376, y + 60, GRID2, .8))
    o.append(T(14, y + 84, "Senere", 15, 800, INK))
    peak = max(seat(w)["lager"] for w in range(25, 37))
    o.append(TL(100, y + 84, [f"Lageret nådde {peak} i uke 29. Lagerkost", f"uke 25 til 36: {kr(late_cost)}."], 40, 20, sz=15, wt=500, fill=INK, f="b"))
    o.append(L(14, y + 118, 376, y + 118, GRID2, .8))
    o.append(T(14, y + 142, "De andre", 15, 800, INK))
    ri, ds, fa = seat(11, "Detaljist"), seat(11, "Distributør"), seat(11, "Fabrikk")
    o.append(T(100, y + 142, f"Detaljist: Restordre {ri['restordre']}, ordre inn {ri['innkommende_ordre']}", 15, 500, INK, f="b"))
    o.append(T(100, y + 162, f"Distributør: Lager {ds['lager']}, ordre inn {ds['innkommende_ordre']}", 15, 500, INK, f="b"))
    o.append(T(100, y + 182, f"Fabrikk: Lager {fa['lager']}, ordre inn {fa['innkommende_ordre']}", 15, 500, INK, f="b"))
    o.append(R(14, y + 198, 362, 196, WHITE, INK, 1.2, rx=2))
    o.append(ki_tag(24, y + 208, "KI-generert, kan ta feil", 13))
    o.append(TL(24, y + 250, "Du så restordre, og det pekte mot å bestille mer. De 16 på vei sto ikke på lageret ennå. Ordren din nådde Distributør i Uke 13, med 24 inn mot 8 uka før. De bestilte 20 samme uke, mot 8 uka før.", 44, 21, sz=15, wt=500, fill=INK, f="b"))
    o.append(band_line(10, 811, 370, hi="Debrief-frist"))
    return "".join(o)


def step5(pg):
    o = [debrief_head(4)]
    o.append(T(14, 98, "Debrief-quiz", 25, 800, INK))
    o.append(TL(14, 132, "Du bestilte 24 i Uke 11. Når kunne den ordren tidligst nå lageret ditt?", 40, 24, sz=18, wt=700, fill=INK, f="b"))
    opts = [("Uke 12", None), ("Uke 13", "feil"), ("Uke 15", "riktig"), ("Uke 17", None)]
    for i, (t_, st) in enumerate(opts):
        y = 190 + i * 56
        if st == "feil":
            o.append(R(14, y, 362, 48, PAPER2, RED, 2, rx=2))
            o.append(cross(28, y + 17, 14))
            o.append(T(376 - 12, y + 30, "Du valgte", 14, 700, RED, a="end", f="b"))
        elif st == "riktig":
            o.append(R(14, y, 362, 48, PAPER2, INK, 2.4, rx=2))
            o.append(check(26, y + 15, 18))
            o.append(T(376 - 12, y + 30, "Riktig svar", 14, 700, INK, a="end", f="b"))
        else:
            o.append(R(14, y, 362, 48, PAPER2, GRID2, 1, rx=2))
        o.append(T(56, y + 31, t_, 18, 700 if st else 500, INK))
    # forklaring med helning
    y = 424
    o.append(L(14, y, 376, y, INK, 1.4))
    o.append(T(14, y + 28, "Uke 13 er når ordren når Distributør", 17, 800, INK, f="b"))
    ox, oy, r = 64, y + 48, 26
    yk = lambda w: oy + (w - 11) * r
    for w in range(11, 16):
        o.append(T(ox - 10, yk(w) + 5, f"Uke {w}", 13, 500, INK2, a="end", f="b"))
        o.append(L(ox, yk(w), 376, yk(w), GRID, .7))
    o.append(L(ox, oy, ox, yk(15), INK, 2))
    o.append(L(376 - 6, oy, 376 - 6, yk(15), INK2, 1.2))
    o.append(order_line(ox, yk(11), 370, yk(13), 24, .3))
    o.append(goods_line(370, yk(13), ox, yk(15), 17, .3))
    o.append(T(ox + 58, yk(11) + 7, "2 uker opp", 14, 700, RED, f="b", halo=PAPER))
    o.append(T(ox + 70, yk(15) - 8, "2 uker tilbake", 14, 700, INK, f="b", halo=PAPER))
    o.append(TL(14, yk(15) + 30, "Så skal kassene fraktes tilbake: Uke 15. Da kom 17 av de 24.", 46, 21, sz=16, wt=500, fill=INK, f="b"))
    o.append(btn(14, 740, 362, 52, "Neste spørsmål", "ink", 18))
    o.append(band_line(10, 811, 370, hi="Debrief-frist"))
    return "".join(o)


def page_debrief():
    pg = Page("debrief", 2100, 1200, "Ruteplan: Gruppedebrief i 5 steg",
              "Fem telefonruter og én delt skjerm. Hele ruteplanen åpnes: en liten endring nederst blir en tett floke øverst.")
    pg.paper()
    pg.add(wordmark(32, 42, 24))
    pg.add(T(196, 42, "Debrief: papiret snus, og hele ruteplanen åpnes", 24, 600, INK))
    pg.add(demo(2068, 42, "end"))
    s = .7
    fy = 64
    notes = [
        ["Forklaring", "Lukkeren står over", "planen. Hver skriver", "på sin telefon, før", "noen ser noe."],
        ["Klimaks", "Nesten tomt papir.", "Én rød strek som", "knekker én gang,", "fra 4 til 8."],
        ["Ruteplanen", "Papiret snus 90°.", "Forsterkning står", "på sporet: 1,8× til", "7,6×."],
        ["Ditt øyeblikk", "Uke 11, med de", "linjene du faktisk", "så, og det de tre", "andre så."],
        ["Quiz", "Feil svar forklares", "med helningen,", "ikke med et rødt", "kryss alene."],
    ]
    fns = [step1, step2, step3, step4, step5]
    for i, fn in enumerate(fns):
        x = 32 + i * 412
        pg.add(phone(pg, x, fy, s, fn(pg)))
        tx = x + 288
        pg.add(T(tx, fy + 30, notes[i][0], 19, 800, INK))
        for k, line in enumerate(notes[i][1:]):
            pg.add(T(tx, fy + 54 + k * 20, line, 15, 500, INK, f="b"))
    # delt skjerm
    x0, y0, w0, h0 = 32, 668, 2036, 516
    pg.add(R(x0 - 6, y0 - 6, w0 + 12, h0 + 12, INK, rx=8), R(x0, y0, w0, h0, PAPER))
    pg.add(T(x0 + 22, y0 + 38, "Delt skjerm: Spill 17, hele ruteplanen", 26, 800, INK))
    pg.add(TL(x0 + 760, y0 + 36, ["Ingen i kjeden gjorde noe rart. Samme to uker mellom hvert spor, og ingen så mer enn sitt eget."], 110, 20, sz=18, wt=500, fill=INK, f="b"))
    px, py, pw, ph = x0 + 138, y0 + 66, 1640, 370
    pg.add(R(px, py, pw, ph, PAPER2))
    D, ys, X = marey(pg, px, py, pw, ph, kw=.46)
    pg.add(D)
    amp = FX["amplification"]
    cost = FX["total_cost_per_role"]
    for n in ["Produksjon", "Fabrikk", "Distributør", "Grossist", "Detaljist", "Kunde"]:
        if n in amp:
            w_ = len(n) * 8.2 + 16
            pg.add(plate(px - w_ - 8, ys[n] - 12, w_, 24), T(px - 16, ys[n] + 5, n, 15, 700, WHITE, a="end", f="b"))
            pg.add(T(px + pw + 12, ys[n] + 2, f"{str(amp[n]).replace('.', ',')}×", 28, 800, RED))
            pg.add(T(px + pw + 12, ys[n] + 20, f"{kr(cost[n])}", 14, 600, INK, f="b"))
        else:
            pg.add(T(px - 12, ys[n] + 5, n, 15, 600, INK2 if n == "Produksjon" else RED, a="end", f="b"))
    for t in (1, 5, 10, 15, 20, 25, 30, 36):
        pg.add(T(X(t), py + ph + 18, f"Uke {t}" if t in (1, 36) else t, 14, 500, INK2, a="start" if t == 1 else ("end" if t == 36 else "middle"), f="b"))
    # to merkelapper: knekket og floka
    kx, ky = X(5), ys["Kunde"]
    pg.add(T(kx + 26, ky - 9, "Her er det lille knekket: kundene går fra 4 til 8 i uke 5, og så er det stabilt.", 17, 800, RED))
    bx = X(26.6)
    pg.add(R(bx, ys["Produksjon"] + 6, 368, 56, PAPER2, INK, 1.2))
    pg.add(T(bx + 12, ys["Produksjon"] + 28, "Her er floka: samme ene endringen,", 17, 800, INK))
    pg.add(T(bx + 12, ys["Produksjon"] + 50, "ett ledd og to uker opp for hvert spor.", 17, 800, INK))
    hx, hy = X(13) + 10, (ys["Grossist"] + ys["Distributør"]) / 2 - 14
    pg.add(R(hx, hy, 146, 24, YEL, INK, 1), T(hx + 8, hy + 17, "Grossist, Uke 11: 24", 15, 700, INK, f="b"))
    pg.add(T(x0 + 22, y0 + h0 - 48, "Kjeden totalt", 15, 700, INK, f="b"))
    pg.add(T(x0 + 22, y0 + h0 - 24, kr(FX["chain_total_cost"]), 20, 800, INK))
    pg.add(band_line(px, y0 + h0 - 34, pw, hi="Debrief-frist", sz=15))
    return pg


# ---------- simulering av de andre 59 spillene, bare ordre, for miniatyrene ----------
def sim_orders(seed, cost_norm):
    rng = random.Random(seed)
    th, a_s, a_sl = .35, .22 + .38 * cost_norm, .24 - .16 * cost_norm
    inv, back = [12] * 4, [0] * 4
    ship_in = [[4, 4] for _ in range(4)]
    order_in = [[4, 4] for _ in range(3)]
    prod, fac = [4, 4], [4, 4]
    exp, sup = [4.0] * 4, [16] * 4
    out = {r_: [] for r_ in ROLES}
    for w in range(1, 37):
        inc = [4 if w < 5 else 8] + [order_in[i][0] for i in range(3)]
        de = [ship_in[i][0] for i in range(3)] + [prod[0]]
        sh = [0] * 4
        for i in range(4):
            inv[i] += de[i]
            sup[i] -= de[i]
            due = back[i] + inc[i]
            sh[i] = min(inv[i], due)
            inv[i] -= sh[i]
            back[i] = due - sh[i]
        od = [4] * 4
        for i in range(4):
            exp[i] = th * inc[i] + (1 - th) * exp[i]
            if w > 4:
                od[i] = max(0, round(exp[i] + a_s * (12 - inv[i] + back[i]) + a_sl * (16 - sup[i]) + rng.gauss(0, .9)))
            sup[i] += od[i]
            out[ROLES[i]].append(od[i])
        for i in range(3):
            ship_in[i] = [ship_in[i][1], sh[i + 1]]
            order_in[i] = [order_in[i][1], od[i]]
        prod = [prod[1], fac[0]]
        fac = [fac[1], od[3]]
    return out


GAMES = FX["class_games"]
_costs = [g["kjedekost"] for g in GAMES if g["status"] == "ferdig"]
SERIES = {}
for g_ in GAMES:
    if g_["spill"] == 17:
        SERIES[17] = {r_: [seat(w, r_)["ordre"] for w in range(1, 37)] for r_ in ROLES}
    else:
        wk = max(1, g_["uke"])
        norm = min(1, max(0, (g_["kjedekost"] / wk * 36 - 1800) / 4400))
        SERIES[g_["spill"]] = sim_orders(g_["spill"] * 13 + 7, norm)
_rw = random.Random(1994)
_names = ["Emma", "Ola", "Nora", "Elias", "Maja", "Liam", "Thea", "Vilde", "Oskar", "Ingrid", "Sander", "Hanna", "Tobias", "Sofie", "Henrik", "Amalie", "Jakob"]
for g_ in GAMES:
    if g_["status"] == "pågår":
        g_.setdefault("venter_paa", _rw.choice(ROLES))
        g_.setdefault("navn", _rw.choice(_names))
        g_.setdefault("ventet_min", _rw.randint(2, 170))
        if g_["spill"] == 17:
            g_.update(venter_paa="Fabrikk", navn="Jonas", ventet_min=3)
    if g_["ki_seter"]:
        g_["ki_rail"] = _rw.sample(range(4), g_["ki_seter"])


def mini(pg, g, x, y, w, h, flat=False, kw=.095):
    """Miniatyr-ruteplan: fire spor, tid mot høyre, bare ordre. Stopper der spillet står."""
    wk = g["uke"]
    X = lambda t: x + (t - 1) / 35 * w
    ry = [y + h - h * i / 3 for i in range(4)]
    done = g["status"] == "ferdig"
    o = [R(x, y - 3, w, h + 6, PAPER2 if not done else PAPER)]
    if not done:
        o.append(R(X(wk), y - 3, x + w - X(wk), h + 6, PAPER))
    paths = {}
    series = SERIES[g["spill"]]
    for i in range(3):
        for t in range(1, wk - 1, 6 if flat else 1):
            q = 4 if flat else series[ROLES[i]][t - 1]
            ww = max(.5, round(q * kw, 1))
            bucket = .38 if q <= 6 else (.7 if q <= 12 else 1)
            paths.setdefault((ww, bucket), []).append(f"M{num(X(t))} {num(ry[i])}L{num(X(t + 2))} {num(ry[i + 1])}")
    col = INK2 if flat else (INK if done else RED)
    for (ww, bucket), segs in paths.items():
        o.append(P("".join(segs), c=col, sw=ww, extra=f'opacity="{bucket}"'))
    for i in range(4):
        ki = i in g.get("ki_rail", [])
        o.append(L(x, ry[i], x + w, ry[i], INK, .8))
        if ki:
            o.append(L(x, ry[i] - 2, x + w, ry[i] - 2, INK, .8))
    if done:
        o.append(R(x + w - 1, y - 3, 3, h + 6, INK))
    else:
        o.append(L(X(wk), y - 3, X(wk), y + h + 3, INK, 1.6))
    return "".join(o)


def status_glyph(x, y, st):
    if st == "ferdig":
        return L(x, y + 6, x + 11, y + 6, INK, 1.4) + R(x + 11, y, 3, 12, INK)
    if st == "pågår":
        return L(x + 6, y, x + 6, y + 12, INK, 2) + L(x, y + 6, x + 12, y + 6, RED, 1.4, 'stroke-dasharray="3 2"')
    if st == "pauset":
        return R(x + 2, y, 3.6, 12, INK) + R(x + 8, y, 3.6, 12, INK)
    if st == "venter":
        return sema(x, y - 3, "stopp", .68)
    if st == "ki":
        return chip(x, y, 12)
    return ""


def funnel_rail(pg, x, y, w, h):
    f = FX["funnel"]
    keys = [("registrert", "Registrert"), ("klassespill_ferdig", "Klassespill ferdig"), ("debrief_ferdig", "Debrief ferdig"),
            ("quiz_bestått", "Quiz bestått"), ("replay_ferdig", "Replay ferdig"), ("test_levert", "Test levert"), ("ki_vurdering_klar", "KI-vurdering klar")]
    n = len(keys)
    o = []
    xs = [x + i * w / (n - 1) * .94 for i in range(n)]
    ys = [y + h - f[k] / 240 * h for k, _ in keys]
    # fall mellom stasjonene
    d = f"M{num(xs[0])} {y + h}" + "".join(f"L{num(a)} {num(b)}" for a, b in zip(xs, ys)) + f"L{num(xs[-1])} {y + h}Z"
    o.append(P(d, fill=pg.url("hn")))
    o.append(P("M" + "L".join(f"{num(a)} {num(b)}" for a, b in zip(xs, ys)), c=INK, sw=2.4))
    o.append(L(x, y + h, xs[-1] + 40, y + h, INK, 1.2))
    for (k, lab), a, b in zip(keys, xs, ys):
        o.append(C(a, b, 4, PAPER2, INK, 1.8))
        o.append(T(a + 8, b - 7 if f[k] > 20 else b - 8, f[k], 19, 800, INK, halo=PAPER))
        o.append(T(a, y + h + 19, lab, 14, 600, INK, f="b"))
    return "".join(o)


def page_oversikt():
    pg = Page("oversikt", 1600, 1000, "Ruteplan: Oversikt over 60 Klassespill",
              "Seksti miniatyr-ruteplaner og en togleder-tabell. Spill 2 venter på Noah i 23 timer, like før KI overtar.")
    pg.paper()
    pg.add(wordmark(24, 42, 22))
    pg.add(T(170, 42, "Oversikt", 24, 800, INK))
    pg.add(T(274, 42, "class-of-1994, IBE160, 240 studenter i 60 Klassespill", 17, 500, INK2, f="b"))
    pg.add(demo(1270, 42, "end"))
    pg.add(btn(1290, 18, 150, 36, "Send Melding", "ink", 15), btn(1450, 18, 126, 36, "Klasserapport", "ghost", 14))
    pg.add(L(0, 64, 1600, 64, INK, 1.4))
    # filter
    games = GAMES
    cnt = {"ferdig": 41, "pågår": 15, "venter": 4, "pauset": 2}
    fx = 24
    filt = [("Alle", 60, None, True), ("Ferdig", 41, "ferdig", False), ("Pågår", 15, "pågår", False), ("herav Pauset", 2, "pauset", False),
            ("Venter", 4, "venter", False), ("Med KI-sete", sum(1 for g in games if g["ki_seter"]), "ki", False), ("Nær overtakelse", 1, "nær", False)]
    for lab, n, st, on in filt:
        w_ = 44 + len(lab) * 7.8 + (22 if st else 0)
        pg.add(R(fx, 76, w_, 30, INK if on else PAPER2, INK, 1, rx=2))
        tx = fx + 8
        if st == "nær":
            pg.add(R(fx + 6, 82, 14, 18, YEL, INK, 1))
            pg.add(T(fx + 13, 96, "!", 13, 800, INK, a="middle"))
        elif st:
            pg.add(status_glyph(fx + 7, 85, st))
        if st:
            tx += 20
        pg.add(T(tx, 96, f"{lab} {n}", 15, 700, WHITE if on else INK, f="b"))
        fx += w_ + 6
    # søk
    pg.add(R(1010, 76, 280, 30, PAPER2, GRID2, 1, rx=2), T(1020, 96, "Finn spill eller student", 15, 500, INK2, f="b"))
    # 60 miniatyrer
    cw, ch = 97.2, 101
    gx, gy = 24, 118
    for g in games:
        i = g["spill"] - 1
        x = gx + (i % 10) * cw
        y = gy + (i // 10) * ch
        st = g["status"]
        near = st == "venter" and g.get("ventet_timer", 0) >= 23
        tw, th = cw - 6, ch - 6
        if near:
            pg.add(R(x - 2, y - 2, tw + 4, th + 4, YEL, RED, 2.6))
        elif st == "venter":
            pg.add(R(x, y, tw, th, "#FBE9B0", INK, 1.2))
        elif st == "pauset":
            pg.add(R(x, y, tw, th, pg.url("hn"), INK, 1))
        else:
            pg.add(R(x, y, tw, th, PAPER2 if st == "pågår" else PAPER, INK if st == "pågår" else GRID2, 1 if st == "pågår" else .8))
        pg.add(T(x + 5, y + 16, g["spill"], 15, 800, INK))
        pg.add(T(x + tw - 5, y + 15, f"Uke {g['uke']}", 13, 500, INK, a="end", f="b"))
        if g["ki_seter"]:
            pg.add(chip(x + 26, y + 5, 12), T(x + 39, y + 15, g["ki_seter"], 13, 700, INK, f="b"))
        pg.add(mini(pg, g, x + 5, y + 25, tw - 10, 42))
        if st == "ferdig":
            line = f"{tus(g['kjedekost'])} kr"
            pg.add(status_glyph(x + 5, y + th - 15, st))
            pg.add(T(x + 24, y + th - 5, line, 13, 500, INK, f="b"))
        elif st == "pågår":
            mins = g["ventet_min"]
            tt = f"{mins} min" if mins < 60 else f"{mins // 60} t {mins % 60:02d}"
            pg.add(T(x + 5, y + th - 5, f"{g['navn']} {tt}", 13, 500, INK, f="b"))
        elif st == "venter":
            pg.add(sema(x + 4, y + th - 19, "stopp", .68))
            pg.add(T(x + 20, y + th - 5, f"{g['navn']} +{g['ventet_timer']} t", 13.5, 800, INK, f="b"))
        else:
            pg.add(status_glyph(x + 5, y + th - 15, st))
            pg.add(R(x + 20, y + th - 17, tw - 24, 15, PAPER2))
            pg.add(T(x + 22, y + th - 5, "til " + g["fortsetter"].replace("i kveld ", ""), 13, 700, INK, f="b"))
    # togleder-tabell
    tx, ty = 1012, 118
    tw = 564
    pg.add(T(tx, ty + 16, "Togleder", 21, 800, INK))
    pg.add(T(tx + tw, ty + 16, "Skala til 24 t: da overtar KI", 14, 500, INK2, a="end", f="b"))
    cols = dict(sp=tx + 26, uke=tx + 66, who=tx + 80, bar=tx + 278, ki=tx + 500, msg=tx + 546)
    hy = ty + 40
    pg.add(T(cols["sp"], hy, "Spill", 14, 600, INK2, a="end", f="b"), T(cols["uke"], hy, "Uke", 14, 600, INK2, a="end", f="b"),
           T(cols["who"], hy, "Venter på", 14, 600, INK2, f="b"), T(cols["bar"], hy, "Forsinkelse", 14, 600, INK2, f="b"),
           T(cols["ki"], hy, "KI", 14, 600, INK2, a="middle", f="b"))
    pg.add(L(tx, hy + 7, tx + tw, hy + 7, INK, 1.6))
    wait = sorted([g for g in games if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])
    paused = [g for g in games if g["status"] == "pauset"]
    run = sorted([g for g in games if g["status"] == "pågår"], key=lambda g: -g["ventet_min"])
    rows = wait + paused + run
    rh = 28.4
    bw = 200
    for i, g in enumerate(rows):
        y = hy + 12 + i * rh
        st = g["status"]
        if st == "venter" and g["ventet_timer"] >= 23:
            pg.add(R(tx - 4, y, tw + 8, rh - 2, YEL, RED, 2))
        pg.add(T(cols["sp"], y + 19, g["spill"], 15, 800, INK, a="end"))
        pg.add(T(cols["uke"], y + 19, g["uke"], 15, 500, INK, a="end", f="b"))
        bx = cols["bar"]
        by = y + rh / 2 - 1
        if st == "pauset":
            pg.add(status_glyph(cols["who"], y + 7, "pauset"))
            pg.add(T(cols["who"] + 18, y + 19, "Pause", 15, 700, INK, f="b"))
            pg.add(T(bx, y + 19, f"Siden {'14:20' if g['spill'] == 20 else 'i går'}, til {g['fortsetter']}", 15, 500, INK, f="b"))
        else:
            hours = g.get("ventet_timer", g.get("ventet_min", 0) / 60)
            st_ = "stopp"
            pg.add(sema(cols["who"], y + 5, st_, .68))
            nm = f"{g['venter_paa']}, {g['navn']}"
            pg.add(T(cols["who"] + 16, y + 19, nm, 15, 700 if st == "venter" else 500, INK, f="b"))
            lbl = f"+{g['ventet_timer']} t" if st == "venter" else (f"+{g['ventet_min']} min" if g["ventet_min"] < 60 else f"+{g['ventet_min'] // 60} t {g['ventet_min'] % 60:02d}")
            pg.add(L(bx, by, bx + bw * .74, by, GRID2, 1))
            pg.add(L(bx + bw * .74, by - 5, bx + bw * .74, by + 5, RED, 1.6))
            pg.add(L(bx, by, bx + bw * .74 * min(1, hours / 24), by, INK, 5 if st == "venter" else 3))
            pg.add(T(bx + bw * .78, y + 19, lbl, 15, 800 if st == "venter" else 500, RED if hours >= 23 else INK, f="b"))
        if g["ki_seter"]:
            pg.add(chip(cols["ki"] - 11, y + 8, 12), T(cols["ki"] + 4, y + 19, g["ki_seter"], 14, 700, INK, f="b"))
        pg.add(envelope(cols["msg"], y + 6, 17))
        pg.add(L(tx, y + rh - 1, tx + tw, y + rh - 1, GRID2, .6))
    pg.add(T(tx, hy + 12 + len(rows) * rh + 22, "Spill 2: KI overtar Grossist om 1 t hvis ingen Pause settes.", 15, 700, RED, f="b"))
    # trakt
    pg.add(T(24, 742, "Trakten", 19, 800, INK))
    pg.add(T(100, 742, "studenter per steg", 15, 500, INK2, f="b"))
    pg.add(funnel_rail(pg, 40, 778, 920, 98))
    # bånd
    pg.add(date_band(24, 930, 1552, hi="Spillfrist", today=True, labs=True))
    return pg


# ---------- 01 landing ----------
def lattice(pg, rails, top, bot, r, now, focus=1, kw=.75):
    """Vanlig mønster, 4 kasser i hvert ledd. Sporet som er i fokus er blekk, resten svakt."""
    w0, w1 = 1, int((bot - top) / r)
    Y = lambda w: top + (w - .5) * r
    o = []
    for w in range(w0, w1 + 1):
        o.append(L(rails[0] - 34, Y(w), rails[-1] + 34, Y(w), GRID2 if w % 5 == 0 else GRID, .8 if w % 5 == 0 else .5))
        o.append(T(rails[0] - 42, Y(w) + 5, w, 14, 500, INK2, a="end", f="b"))
    for i in range(len(rails) - 1):
        z = rails[i + 1] - rails[i]
        for k in range(1, 4):
            o.append(L(rails[i] + k * z / 4, top, rails[i] + k * z / 4, bot, GRID, .5))
    cid = pg.uid("gitter")
    pg.defs.append(f'<clipPath id="{cid}"><rect x="{rails[0]}" y="{top}" width="{rails[-1] - rails[0]}" height="{bot - top}"/></clipPath>')
    g = []
    for i in range(3):
        touch = i == focus or i == focus - 1
        for w in range(-3, now + 1):
            a = i == focus and True
            # ordre oppstrøms
            is_open = w + 2 > now
            op = 1 if touch and (w == now - 0 or is_open) else (.5 if touch else .2)
            g.append(order_line(rails[i], Y(w), rails[i + 1], Y(w + 2), 4, kw, op))
            is_open2 = w + 2 > now
            op2 = 1 if touch and is_open2 else (.5 if touch else .2)
            g.append(goods_line(rails[i + 1], Y(w), rails[i], Y(w + 2), 4, kw, op2))
    o.append(f'<g clip-path="url(#{cid})">{"".join(g)}</g>')
    for i, x in enumerate(rails):
        o.append(L(x, top, x, bot, INK, 3 if i == focus else 1.2))
    o.append(L(rails[0] - 34, Y(now), rails[-1] + 34, Y(now), INK, 2.2))
    return "".join(o), Y


def page_landing():
    pg = Page("landing", 1440, 1200, "Ruteplan: For faglærere",
              "Landingsside. Fire vertikale spor og et regelmessig mønster av linjer viser mekanismen: en ordre tar to uker opp, en levering to uker tilbake, og hver student ser bare sitt eget spor.")
    pg.paper()
    pg.add(wordmark(64, 58, 28))
    pg.add(T(1260, 53, "Logg inn", 17, 600, INK, a="end"))
    pg.add(demo(1376, 53, "end"))
    pg.add(L(0, 80, 1440, 80, INK, 1.4))
    pg.add(R(0, 81, 640, 760, PAPER))
    pg.add(TL(64, 170, ["Hver ordre", "er en linje.", "Hver forsinkelse", "er en helning."], 20, 74, sz=70, wt=800, fill=INK, extra='letter-spacing="-1.4"'))
    pg.add(TL(64, 462, "Ruteplan kjører hele forsyningskjede-øvelsen for klassen din, fra Invitasjon til PDF-rapport. Fire roller i hvert spill, klasser på rundt 250 studenter, alt på norsk.", 52, 32, sz=23, wt=500, fill=INK, f="b"))
    pg.add(btn(64, 580, 268, 62, "Be om lærertilgang", "primary", 20))
    pg.add(btn(346, 580, 130, 62, "Logg inn", "ghost", 18))
    # fakta som rutetabell
    facts = [("Spilles på mobil", "En ordre i uka, ett heltall. Systemet regner."),
             ("Ett fravær stopper ikke gruppa", "KI-spillere fyller tomme seter, alltid merket."),
             ("Ingen spill blir stående uferdig", "Ved Spillfrist spiller KI-spillere ferdig.")]
    for i, (a, b) in enumerate(facts):
        y = 680 + i * 50
        pg.add(L(64, y, 610, y, GRID2, 1))
        pg.add(T(64, y + 22, a, 18, 700, INK, f="b"), T(64, y + 42, b, 16, 500, INK2, f="b"))
    # rutegitter
    rails = [706, 918, 1130, 1342]
    top, bot = 148, 846
    D, Y = lattice(pg, rails, top, bot, 34, 11, focus=1, kw=.7)
    pg.add(R(640, 81, 800, 780, PAPER), D)
    for i, x in enumerate(rails):
        w_ = len(ROLES[i]) * 9 + 18
        tx = x - w_ / 2
        pg.add(plate(tx, 104, w_, 28, INK if i == 1 else PAPER2), T(x, 124, ROLES[i], 16, 700, WHITE if i == 1 else INK, a="middle", f="b"))
    pg.add(T(rails[0] - 42, 146, "Uke", 14, 600, INK2, a="end", f="b"))
    # åpne linjer: på vei
    ny = Y(11)
    def tag(x, y, lines, c=INK, a="start"):
        return "".join(T(x, y + i * 21, ln, 17, 700, c, a=a, f="b", halo=PAPER) for i, ln in enumerate(lines))
    z = rails[2] - rails[1]
    pg.add(order_line(rails[1], Y(11), rails[2], Y(13), 8, .7), L(rails[2], Y(13), rails[1], Y(15), INK, 5, 'opacity=".22"'))
    def note(x, y, w, lines, c=INK):
        o_ = R(x, y, w, 12 + len(lines) * 21, PAPER2, INK, 1)
        return o_ + "".join(T(x + 10, y + 21 + i * 21, ln, 17, 700, c, f="b") for i, ln in enumerate(lines))
    pg.add(note(rails[2] + 10, Y(13) - 12, 170, ["Ordre: to uker opp"], RED))
    pg.add(note(rails[1] + 10, Y(15) + 14, 196, ["Levering: to uker tilbake"]))
    pg.add(note(rails[1] - 190, Y(12) + 12, 176, ["Linjer under nålinja", "er på vei, og studenten", "ser dem i ruta."]))
    pg.add(note(rails[1] - 190, Y(3) - 8, 176, ["Grossisten ser bare", "linjene som berører", "sitt eget spor."]))
    # nålinje-merke og signal
    pg.add(R(rails[0] - 62, ny - 12, 30, 24, INK), T(rails[0] - 47, ny + 6, "11", 15, 700, WHITE, a="middle", f="b"))
    pg.add(R(rails[2] + 6, Y(5) - 16, 204, 54, PAPER2, INK, 1))
    pg.add(sema(rails[2] + 16, Y(5) - 10, "stopp"))
    pg.add(T(rails[2] + 40, Y(5) + 6, "Uka venter på Fabrikk", 16, 700, INK, f="b"))
    pg.add(T(rails[2] + 40, Y(5) + 26, "Vist med Rolle og tid: 3 min", 15, 500, INK2, f="b"))
    pg.add(R(rails[2] + 10, Y(16), 196, 66, PAPER2, INK, 1))
    pg.add(ki_tag(rails[2] + 20, Y(16) + 9, "KI-spiller", 14, bg=WHITE))
    pg.add(T(rails[2] + 20, Y(16) + 54, "fyller tomme seter, merket", 16, 600, INK, f="b"))
    pg.add(L(rails[3] - 3, top, rails[3] - 3, bot, INK, 1))
    # neste seksjon
    y = 868
    pg.add(R(0, y - 6, 1440, 340, PAPER2), L(0, y - 6, 1440, y - 6, INK, 2))
    pg.add(T(64, y + 44, "Hele øvelsen ligger på samme linje", 38, 800, INK))
    stops = [("Canvas-eksport", ["Studentlisten lastes", "opp fra fil."]), ("Invitasjon", ["Ingen åpen", "registrering."]),
             ("Klassespill", ["Fire seter, fylt med", "KI-spillere ved behov."]), ("Debrief", ["Forklarer egne ordre", "gjennom strukturen."]),
             ("Replay", ["En runde til mot", "KI-spillere."]), ("Individuell test", ["KI-vurderingen teller", "ikke, og er aldri karakter."]),
             ("PDF-rapport", ["Dokumentasjon til", "hver student."])]
    lx0, lx1 = 76, 1320
    ly = y + 88
    pg.add(L(lx0, ly, lx1 + 40, ly, INK, 5))
    for i, (a, b) in enumerate(stops):
        x = lx0 + i * (lx1 - lx0) / 6 * .985
        pg.add(C(x, ly, 9, PAPER2, INK, 3))
        pg.add(T(x - 9, ly + 34, a, 19, 800, INK, f="b"))
        for k, ln in enumerate(b):
            pg.add(T(x - 9, ly + 56 + k * 19, ln, 15, 500, INK, f="b"))
    # 60 små planer + bånd
    pg.add(T(64, y + 212, "Alle spillene på én skjerm", 22, 800, INK))
    pg.add(T(64, y + 234, "60 små ruteplaner, ett blikk.", 16, 500, INK2, f="b"))
    sx, sy = 64, y + 244
    for g in GAMES:
        i = g["spill"] - 1
        x_ = sx + (i % 30) * 20.6
        y_ = sy + (i // 30) * 33
        gg = dict(g)
        gg["uke"] = {"ferdig": 36}.get(g["status"], g["uke"])
        pg.add(mini(pg, gg, x_, y_ + 3, 17.5, 22, flat=True, kw=.1))
    pg.add(T(760, y + 212, "Fristene ligger på én linje", 22, 800, INK))
    pg.add(T(760, y + 234, "Eksempel: en Klasseøkt på fire uker.", 16, 500, INK2, f="b"))
    pg.add(date_band(760, y + 262, 616))
    return pg


# ---------- 02 klasse ----------
def field(x, y, w, label, value, sz=18):
    return (T(x, y, label, 14, 600, INK2, f="b") + R(x, y + 8, w, 40, PAPER2, INK, 1.2, rx=2)
            + T(x + 12, y + 34, value, sz, 600, INK))


def page_klasse():
    pg = Page("klasse", 1440, 1000, "Ruteplan: Ny Klasse",
              "Faglærer lager Klasse, laster opp Canvas-fil, velger e-postkolonne, ser ugyldige rader og sender Invitasjoner.")
    pg.paper()
    pg.add(wordmark(32, 44, 22))
    pg.add(T(180, 44, "Klasser", 16, 500, INK2, f="b"), T(232, 44, "/", 16, 500, INK2, f="b"), T(244, 44, "class-of-1994", 16, 700, INK, f="b"))
    pg.add(demo(1408, 44, "end"))
    pg.add(L(0, 62, 1440, 62, INK, 1.4))
    pg.add(T(32, 108, "Klasse og Klasseliste", 34, 800, INK))
    # tre spalter
    c1, c2, c3 = 32, 410, 1020
    pg.add(field(c1, 146, 240, "Navn på Klassen", "class-of-1994"))
    pg.add(field(c1 + 252, 146, 96, "Emnekode", "IBE160"))
    # fil
    pg.add(T(c1, 222, "Canvas-eksport", 14, 600, INK2, f="b"))
    pg.add(R(c1, 230, 348, 72, PAPER2, INK, 1.2, rx=2))
    pg.add(P(f"M{c1 + 14} 242h22l8 8v40h-30z", fill=WHITE, c=INK, sw=1.4), P(f"M{c1 + 36} 242v8h8", c=INK, sw=1.4))
    pg.add(T(c1 + 56, 258, "ibe160-canvas-eksport.xlsx", 17, 600, INK))
    pg.add(T(c1 + 56, 282, "250 rader lest. Bytt fil", 15, 500, INK2, f="b"))
    # kolonnevalg
    pg.add(T(c1, 330, "Hvilken kolonne er e-post?", 14, 600, INK2, f="b"))
    cols = [("Navn", False, "Sara Lund"), ("SIS-ID", False, "S104417"), ("Seksjon", False, "IBE160-1"), ("E-post", True, "246 gyldige av 250")]
    for i, (n, on, prev) in enumerate(cols):
        y = 340 + i * 38
        pg.add(R(c1, y, 348, 34, INK if on else PAPER2, INK, 1, rx=2))
        pg.add(C(c1 + 18, y + 17, 6, PAPER2 if on else WHITE, INK if not on else WHITE, 1.4))
        if on:
            pg.add(C(c1 + 18, y + 17, 3, INK))
        pg.add(T(c1 + 34, y + 23, n, 16, 700 if on else 500, WHITE if on else INK, f="b"))
        pg.add(T(c1 + 336, y + 23, prev, 15, 600 if on else 500, WHITE if on else INK2, a="end", f="b"))
    # ugyldige rader
    pg.add(T(c2, 138, "Ugyldige rader", 22, 800, INK))
    pg.add(T(c2 + 164, 138, "4 rader får ingen Invitasjon før de er rettet", 16, 500, INK, f="b"))
    pg.add(T(c2, 170, "Rad", 14, 600, INK2, f="b"), T(c2 + 50, 170, "Navn", 14, 600, INK2, f="b"), T(c2 + 180, 170, "E-post i fila", 14, 600, INK2, f="b"), T(c2 + 366, 170, "Feil", 14, 600, INK2, f="b"))
    pg.add(L(c2, 178, c2 + 580, 178, INK, 1.6))
    bad = [(37, "Elias Moe", "elias.moe@stud", "mangler domene", "rettet"), (88, "Vilde Berg", "vilde..berg@stud.example.no", "to punktum", "rettet"),
           (141, "Oskar Lie", "", "tom celle", "open"), (203, "Thea Dahl", "thea dahl@stud.example.no", "mellomrom", "open")]
    for i, (rad, n, m, feil, st) in enumerate(bad):
        y = 182 + i * 42
        pg.add(T(c2, y + 26, rad, 17, 800, RED))
        pg.add(T(c2 + 50, y + 26, n, 16, 500, INK, f="b"))
        pg.add(T(c2 + 180, y + 26, m or "(tom)", 16, 500, INK, f="b"))
        pg.add(T(c2 + 366, y + 26, feil, 16, 500, INK, f="b"))
        if st == "rettet":
            pg.add(check(c2 + 490, y + 14, 14), T(c2 + 510, y + 26, "Manuelt", 15, 600, INK, f="b"))
        else:
            pg.add(R(c2 + 490, y + 7, 90, 30, PAPER2, INK, 1.2, rx=2), T(c2 + 535, y + 27, "Rett rad", 15, 600, INK, a="middle", f="b"))
        pg.add(L(c2, y + 40, c2 + 580, y + 40, GRID2, .7))
    # send
    pg.add(T(c3, 138, "Invitasjoner", 22, 800, INK))
    pg.add(btn(c3, 154, 388, 54, "Send på nytt til 8 som ikke har svart", "primary", 17))
    pg.add(T(c3, 232, "246 Invitasjoner sendt 5. nov.", 16, 700, INK, f="b"))
    pg.add(T(c3, 254, "Gyldig i 14 dager, utløper to. 19. nov.", 16, 500, INK, f="b"))
    # status
    pg.add(T(c3, 298, "Status", 16, 800, INK))
    st = [("Akseptert", 238, "fill"), ("Manuelt registrert", 2, "chk"), ("Sendt, ikke svart", 6, "line"), ("Utløpt", 2, "x"), ("Ingen Invitasjon, ugyldig", 2, "hatch")]
    for i, (lab, n, kind) in enumerate(st):
        y = 312 + i * 30
        if kind == "fill":
            pg.add(R(c3, y + 4, 14, 14, INK))
        elif kind == "chk":
            pg.add(check(c3, y + 5, 13))
        elif kind == "line":
            pg.add(R(c3, y + 4, 14, 14, PAPER2, INK, 1.2))
        elif kind == "x":
            pg.add(cross(c3 + 1, y + 5, 12))
        else:
            pg.add(R(c3, y + 4, 14, 14, pg.url("hr"), RED, 1))
        pg.add(T(c3 + 24, y + 17, lab, 16, 500, INK, f="b"), T(c3 + 388, y + 18, n, 17, 800, INK, a="end"))
        pg.add(L(c3, y + 25, c3 + 388, y + 25, GRID2, .6))
    # hele klasselista som linjal
    y = 524
    pg.add(T(32, y, "Klasselista som linjal", 22, 800, INK))
    pg.add(T(274, y, "Hver strek er en rad i fila, i samme rekkefølge. Rader som krever noe, står der de står.", 17, 500, INK, f="b"))
    rx0, rw = 32, 1376
    ry = y + 48
    tick = lambda i: rx0 + (i - .5) / 250 * rw
    rand = random.Random(250)
    rows_ = ["ok"] * 250
    invalid = {37: "man", 88: "man", 141: "bad", 203: "bad"}
    pool = [i for i in range(1, 251) if i not in invalid]
    rand.shuffle(pool)
    for i in pool[:6]:
        rows_[i - 1] = "wait"
    for i in pool[6:8]:
        rows_[i - 1] = "exp"
    for i, kind in invalid.items():
        rows_[i - 1] = kind
    for i, kind in enumerate(rows_, 1):
        x = tick(i)
        if kind == "ok":
            pg.add(L(x, ry, x, ry + 130, INK, 2.6))
        elif kind == "man":
            pg.add(L(x, ry, x, ry + 130, INK, 2.6), C(x, ry - 8, 4, PAPER2, INK, 1.6))
        elif kind == "wait":
            pg.add(L(x, ry + 66, x, ry + 130, INK, 2.6))
        elif kind == "exp":
            pg.add(L(x, ry + 100, x, ry + 130, INK, 2.6))
        else:
            pg.add(R(x - 3, ry - 14, 6, 158, RED))
    pg.add(L(rx0, ry + 130, rx0 + rw, ry + 130, INK, 1.4))
    for i in (1, 50, 100, 150, 200, 250):
        pg.add(T(tick(i), ry + 150, i, 14, 500, INK2, a="middle", f="b"))
    for i in (37, 88, 141, 203):
        tx = tick(i)
        pg.add(T(tx, ry - 22, f"Rad {i}", 15, 800, RED if i in (141, 203) else INK, a="middle", f="b", halo=PAPER))
    # forklaring for linjal
    lx = 32
    ly = ry + 182
    for lab, kind in [("Akseptert: full strek", "ok"), ("Sendt, ikke svart: halv strek", "wait"), ("Utløpt: kort strek", "exp"), ("Manuelt registrert: ring", "man"), ("Ugyldig: rød stolpe gjennom", "bad")]:
        x = lx + 4
        if kind == "ok":
            pg.add(L(x, ly - 14, x, ly + 4, INK, 2.6))
        elif kind == "wait":
            pg.add(L(x, ly - 5, x, ly + 4, INK, 2.6))
        elif kind == "exp":
            pg.add(L(x, ly - 1, x, ly + 4, INK, 2.6))
        elif kind == "man":
            pg.add(L(x, ly - 6, x, ly + 4, INK, 2.6), C(x, ly - 12, 4, PAPER2, INK, 1.6))
        else:
            pg.add(R(x - 3, ly - 15, 6, 22, RED))
        pg.add(T(lx + 16, ly + 3, lab, 15, 500, INK, f="b"))
        lx += len(lab) * 7 + 44
    pg.add(T(1408, ly + 3, "250 på lista = 238 + 2 + 10 uregistrert", 15, 700, INK, a="end", f="b"))
    # neste
    pg.add(L(32, 806, 1408, 806, GRID2, 1))
    pg.add(T(32, 842, "Når 240 er registrert, kan du sette opp Klasseøkta. Resten følges opp her.", 18, 500, INK, f="b"))
    pg.add(btn(1168, 816, 240, 44, "Sett opp Klasseøkt", "ink", 16))
    pg.add(date_band(32, 912, 1376, invite=True))
    return pg


# ---------- 03 Klasseøkt ----------
def page_oppsett():
    pg = Page("oppsett", 1440, 1100, "Ruteplan: Klasseøkt",
              "Faglærer setter opp Klasseøkt med forhåndsutfylte standarder. Forsinkelsene vises som helninger til skala. Kan lagres uten endring.")
    pg.paper()
    pg.add(wordmark(32, 44, 22))
    pg.add(T(180, 44, "class-of-1994", 16, 700, INK, f="b"), T(280, 44, "/", 16, 500, INK2, f="b"), T(292, 44, "Klasseøkt", 16, 500, INK2, f="b"))
    pg.add(demo(1408, 44, "end"))
    pg.add(L(0, 62, 1440, 62, INK, 1.4))
    pg.add(T(32, 110, "Klasseøkt, standard «Klassisk»", 34, 800, INK))
    pg.add(T(32, 140, "Alt er forhåndsutfylt. Du kan lagre uten å endre noe.", 19, 500, INK, f="b"))
    pg.add(btn(1168, 84, 240, 56, "Lagre Klasseøkt", "primary", 19))
    # innstillinger
    x, y = 32, 178
    pg.add(T(x, y, "Spillinnstillinger", 22, 800, INK))
    rows = [("Startlager", "12"), ("Enheter i hvert ledd", "4"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Etterspørsel", "4 → 8 i uke 5"), ("Lagerkost", "0,50"), ("Restordrekost", "1,00"),
            ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t")]
    for i, (k, v) in enumerate(rows):
        yy = y + 14 + i * 38
        delay = "forsinkelse" in k
        pg.add(L(x, yy, x + 380, yy, GRID2 if i else INK, .7 if i else 1.6))
        pg.add(T(x, yy + 25, k, 17, 500, INK, f="b"))
        if delay:
            pg.add(R(x + 258, yy + 5, 122, 28, PAPER2, INK, 1.2, rx=2))
            pg.add(T(x + 270, yy + 25, v, 17, 700, INK))
            pg.add(P(f"M{x + 360} {yy + 16}l5 -5l5 5M{x + 360} {yy + 23}l5 5l5 -5", c=INK, sw=1.4))
        else:
            pg.add(T(x + 380, yy + 25, v.replace("→", "til"), 17, 700, INK, a="end"))
    yy = y + 14 + len(rows) * 38
    pg.add(L(x, yy, x + 380, yy, INK, 1))
    pg.add(TL(x, yy + 24, "Kildene er uenige om forsinkelser. To uker i hvert ledd er produktets standard.", 50, 21, sz=16, wt=500, fill=INK, f="b"))
    # helningene
    mx, my = 452, 178
    pg.add(T(mx, my, "Helningen viser forsinkelsen", 22, 800, INK))
    pg.add(T(mx, my + 24, "Endre et tall, og linjene her endrer seg før du lagrer.", 16, 500, INK, f="b"))
    rails = [mx + 16, mx + 150, mx + 284, mx + 418]
    rr = 39
    top = my + 72
    Y = lambda w: top + w * rr
    for w in range(0, 11):
        pg.add(L(mx + 16, Y(w), mx + 460, Y(w), GRID, .6))
    for i, x_ in enumerate(rails):
        pg.add(L(x_, top, x_, Y(10), INK, 1.8))
        pg.add(T(x_, top - 10, ROLES[i], 15, 700, INK, a="middle", f="b"))
    pg.add(L(mx + 460, top, mx + 460, Y(10), INK2, 1))
    for i in range(3):
        pg.add(order_line(rails[i], Y(1 + i * 2), rails[i + 1], Y(3 + i * 2), 8, .5))
    pg.add(order_line(rails[3], Y(7), mx + 460, Y(9), 8, .5))
    pg.add(goods_line(rails[2 + 1], Y(1), rails[2], Y(3), 8, .5))
    pg.add(goods_line(rails[2], Y(3), rails[1], Y(5), 8, .5))
    pg.add(goods_line(rails[1], Y(5), rails[0], Y(7), 8, .5))
    pg.add(T(rails[0] + 8, Y(2) + 34, "Ordre, 2 uker", 15, 700, RED, f="b", halo=PAPER))
    pg.add(T(rails[3] - 130, Y(1) - 4, "Frakt, 2 uker", 15, 700, INK, f="b", halo=PAPER))
    pg.add(T(rails[3] - 8, Y(8) + 18, "Produksjon,", 15, 700, RED, a="end", f="b", halo=PAPER))
    pg.add(T(rails[3] - 8, Y(8) + 36, "2 uker", 15, 700, RED, a="end", f="b", halo=PAPER))
    # valg
    vx, vy = 952, 178
    def radio(x_, y_, label, on, sub=None):
        o = C(x_ + 9, y_ + 9, 8, WHITE, INK, 1.4)
        if on:
            o += C(x_ + 9, y_ + 9, 4, INK)
        o += T(x_ + 26, y_ + 15, label, 17, 700 if on else 500, INK, f="b")
        if sub:
            o += T(x_ + 200, y_ + 15, sub, 15, 500, INK2, f="b")
        return o
    pg.add(T(vx, vy, "KI-modus", 22, 800, INK))
    pg.add(radio(vx, vy + 14, "LLM-spillere", True, "standard"), radio(vx, vy + 44, "Regelbaserte spillere", False))
    pg.add(T(vx, vy + 104, "Debrief-modus", 22, 800, INK))
    pg.add(radio(vx, vy + 118, "Gruppedebrief", True, "standard"), radio(vx, vy + 148, "Personlig debrief", False))
    pg.add(T(vx, vy + 208, "Obligatorisk", 22, 800, INK))
    pg.add(R(vx + 150, vy + 190, 56, 26, INK, rx=13), C(vx + 192, vy + 203, 10, WHITE), T(vx + 218, vy + 209, "På", 17, 700, INK, f="b"))
    pg.add(TL(vx, vy + 234, "Merkes «Obligatorisk» hos studentene.", 50, 20, sz=15, wt=500, fill=INK2, f="b"))
    pg.add(T(vx, vy + 286, "Labtimer", 22, 800, INK))
    lab = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    for i, l_ in enumerate(lab):
        yy = vy + 298 + i * 32
        pg.add(P(f"M{vx + 6} {yy + 19}l-6 -9h12Z", fill=WHITE, c=INK, sw=1.2))
        pg.add(T(vx + 22, yy + 20, l_, 17, 500, INK, f="b"), T(vx + 200, yy + 20, "Datalab A2", 17, 500, INK2, f="b"))
        pg.add(L(vx, yy + 28, vx + 400, yy + 28, GRID2, .6))
    pg.add(T(vx + 400, vy + 298 + 4 * 32 + 16, "Legg til Labtime", 16, 700, INK, a="end", f="b"))
    # fordeling
    fy = 716
    pg.add(L(32, fy - 28, 1408, fy - 28, INK, 1.4))
    pg.add(T(32, fy, "Fordeling", 22, 800, INK))
    pg.add(T(136, fy, "240 studenter fordeles tilfeldig i 60 spill à 4. Se over før du bekrefter.", 18, 500, INK, f="b"))
    # 60 små kryss à 4 seter
    rand = random.Random(60)
    gx0, gy0 = 32, fy + 20
    cw, ch = 22.93, 22
    for i in range(60):
        x_ = gx0 + (i % 60) * cw
        y_ = gy0
        for k in range(4):
            pg.add(R(x_, y_ + k * 7, 18, 5, INK if not (i == 16) else RED))
    pg.add(T(gx0 + 16 * cw + 6, gy0 + 46, "Spill 17", 15, 800, RED, a="middle", f="b"))
    # Eksempel-gruppe
    ex = [("Detaljist", "Ida"), ("Grossist", "Sara"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]
    yy = fy + 86
    pg.add(T(32, yy + 18, "Spill 17:", 18, 800, INK))
    for i, (r_, n) in enumerate(ex):
        xx = 120 + i * 196
        pg.add(T(xx, yy + 18, f"{r_}, {n}", 18, 600, INK, f="b"))
    pg.add(btn(956, yy - 8, 196, 44, "Kjør på nytt", "ghost", 17), btn(1164, yy - 8, 244, 44, "Bekreft fordeling", "ink", 17))
    pg.add(T(32, yy + 50, "Tomme seter får KI-spiller ved start. Fordelingen kan kjøres på nytt så lenge den ikke er bekreftet.", 16, 500, INK2, f="b"))
    # bånd
    pg.add(T(32, 934, "Datoer", 22, 800, INK))
    pg.add(T(112, 934, "Alle kan endres. Trekantene er Labtimer.", 16, 500, INK, f="b"))
    pg.add(date_band(32, 984, 1376, hi=None, labs=True))
    return pg


# ---------- 04 student hjem ----------
def invite_screen(pg):
    o = [R(0, 0, 390, 844, PAPER)]
    o.append(wordmark(18, 46, 22))
    o.append(L(0, 62, 390, 62, INK, 1.4))
    o.append(TL(18, 112, ["Bård har invitert deg", "til IBE160"], 30, 34, sz=29, wt=800, fill=INK))
    o.append(TL(18, 178, "Du spiller én Rolle i en kjede på fire. Én ordre per Uke, på din egen telefon, når dere vil.", 44, 22, sz=17, wt=500, fill=INK, f="b"))
    # et tomt spor venter: lite bilde
    top, bot = 262, 430
    o.append(R(0, top, 390, bot - top, PAPER2))
    for k in range(1, 7):
        o.append(L(0, top + k * 24, 390, top + k * 24, GRID, .6))
    for x in (65, 195, 325):
        o.append(L(x, top, x, bot, INK if x == 195 else INK2, 3 if x == 195 else 1))
    o.append(order_line(195, top + 24, 325, top + 72, 8, .5))
    o.append(goods_line(325, top + 72, 195, top + 120, 8, .5))
    o.append(T(203, top + 22, "Din ordre", 15, 700, RED, f="b", halo=PAPER2))
    o.append(T(203, top + 139, "Kassene, to uker senere", 15, 700, INK, f="b", halo=PAPER2))
    o.append(T(18, 456, "Rollen får du når gruppa er trukket.", 15, 500, INK2, f="b"))
    o.append(field(18, 490, 354, "Navn", "Sara Lund"))
    o.append(field(18, 562, 354, "E-post, fra Klasselista", "sara.lund@stud.example.no", 16))
    o.append(field(18, 634, 354, "Velg passord", "••••••••••"))
    o.append(btn(18, 696, 354, 54, "Registrer og gå til Klassen", "primary", 18))
    o.append(T(18, 778, "Invitasjonen er gyldig til to. 19. nov.", 15, 500, INK2, f="b"))
    o.append(band_line(10, 811, 370))
    return "".join(o)


class Bag(list):
    def append(self, *parts):
        self.extend(parts)


def home_screen(pg):
    o = Bag([R(0, 0, 390, 844, PAPER)])
    o.append(R(0, 0, 390, 62, PAPER2), L(0, 62, 390, 62, INK, 1.4))
    o.append(T(14, 28, "Spill 17", 13, 600, INK2, f="b"))
    o.append(T(14, 48, "Grossist, Sara", 19, 800, INK))
    o.append(T(376, 42, "Obligatorisk", 15, 700, INK, a="end", f="b"))
    # venter på deg
    o.append(R(12, 74, 366, 112, INK, rx=3))
    o.append(R(26, 92, 30, 44, PAPER2, rx=2), f'<g transform="translate(-6 0)">{sema(40, 96, "stopp", 1.3)}</g>')
    o.append(T(72, 110, "Spillet venter på deg", 22, 800, WHITE))
    o.append(T(72, 134, "Uke 11. Du og Jonas har ikke bestilt.", 15, 500, WHITE, f="b"))
    o.append(R(72, 144, 150, 32, YEL, rx=2), T(147, 165, "Gå til Uke 11", 16, 800, INK, a="middle"))
    # de andre setene
    o.append(T(14, 214, "Setene", 17, 800, INK))
    seats = [("fri", "Detaljist", "Ida", "bestilt"), ("stopp", "Grossist", "Sara", "det er deg"), ("fri", "Distributør", "Mikkel", "bestilt"), ("stopp", "Fabrikk", "Jonas", "venter 3 min")]
    for i, (st, r_, n, tx) in enumerate(seats):
        y = 224 + i * 31
        o.append(sema(14, y, st, .85))
        o.append(T(38, y + 18, r_, 15, 700, INK, f="b"), T(120, y + 18, n, 15, 500, INK, f="b"))
        o.append(T(376, y + 18, tx, 15, 600, RED if st == "stopp" else INK2, a="end", f="b"))
        o.append(L(14, y + 27, 376, y + 27, GRID2, .6))
    # seks steg: stasjoner
    o.append(T(14, 372, "Stegene dine", 17, 800, INK))
    steps = [("Klassespill", "Pågår", "Spillfrist ti. 8. des"), ("Debrief", "", "Debrief-frist fr. 11. des"), ("Quiz", "", ""), ("Replay", "", ""),
             ("Individuell test", "", "Testfrist fr. 18. des"), ("Rapport", "", "PDF")]
    rx, ry0, rr = 22, 392, 29
    o.append(L(rx, ry0, rx, ry0 + 5 * rr, INK, 3))
    for i, (n, s_, d) in enumerate(steps):
        y = ry0 + i * rr
        o.append(C(rx, y, 7 if i == 0 else 5, YEL if i == 0 else PAPER2, INK, 2))
        o.append(T(rx + 18, y + 5, n, 16, 800 if i == 0 else 500, INK, f="b"))
        if s_:
            o.append(T(rx + 106, y + 5, s_, 15, 700, INK, f="b"))
        if d:
            o.append(T(376, y + 5, d, 15, 500, INK if i == 0 else INK2, a="end", f="b"))
    # neste frist og labtimer
    y = 552
    o.append(L(14, y, 376, y, INK, 1.4))
    o.append(T(14, y + 26, "Neste frist", 15, 600, INK2, f="b"))
    o.append(T(14, y + 52, "Spillfrist ti. 8. des", 23, 800, RED))
    o.append(T(14, y + 74, "Om 4 dager. KI-spillere spiller ferdig da.", 15, 500, INK, f="b"))
    y = 644
    o.append(L(14, y, 376, y, GRID2, 1))
    o.append(T(14, y + 26, "Labtimer, Datalab A2", 15, 600, INK2, f="b"))
    labs = [("to. 26. nov 14:15", False), ("ma. 30. nov 10:15", False), ("to. 3. des 14:15", False), ("ma. 7. des 10:15", True)]
    for i, (l_, nxt) in enumerate(labs):
        x = 14 + (i % 2) * 186
        yy = y + 52 + (i // 2) * 24
        o.append(P(f"M{x + 6} {yy + 3}l-6 -9h12Z", fill=YEL if nxt else WHITE, c=INK, sw=1.2))
        o.append(T(x + 18, yy, l_, 15, 800 if nxt else 500, INK if nxt else INK2, f="b"))
        if not nxt:
            o.append(L(x + 18, yy - 5, x + 18 + len(l_) * 5.25, yy - 5, INK2, .9))
    o.append(band_line(10, 811, 370, hi="Spillfrist"))
    return "".join(o)


def page_hjem():
    pg = Page("hjem", 1000, 900, "Ruteplan: Sara på mobil",
              "To telefoner: registrering fra Invitasjon, og hjem under spill der spillet venter på Sara.")
    pg.paper()
    pg.add(phone(pg, 62, 28, 1, invite_screen(pg)))
    pg.add(phone(pg, 548, 28, 1, home_screen(pg)))
    pg.add(T(40, 450, "Første møte", 18, 700, INK, a="middle", extra='transform="rotate(-90 40 450)"'))
    pg.add(T(526, 450, "Hjem under spill", 18, 700, INK, a="middle", extra='transform="rotate(-90 526 450)"'))
    pg.add(demo(503, 892, "middle"))
    return pg


# ---------- 09 alle sider ----------
def tiny_phone(pg, x, y, w, h, fn):
    return R(x, y, w, h, INK, rx=8) + R(x + 3, y + 3, w - 6, h - 6, PAPER2, rx=5) + fn(x + 8, y + 10, w - 16, h - 20)


def tiny_screen(pg, x, y, w, h, fn):
    return R(x, y, w, h, INK, rx=4) + R(x + 3, y + 3, w - 6, h - 6, PAPER2, rx=2) + fn(x + 10, y + 10, w - 20, h - 20)


def bars(x, y, w, n, h=4, gap=10, c=INK2, lens=None):
    lens = lens or [.9, .7, .85, .6, .75, .5, .8, .65]
    return "".join(R(x, y + i * gap, w * lens[i % len(lens)], h, c, extra='opacity=".55"') for i in range(n))


def tiny_lat(x, y, w, h, tracks=3, rows=4, heavy=False, seed=1):
    o = []
    rand = random.Random(seed)
    for i in range(tracks):
        xi = x + i * w / (tracks - 1)
        o.append(L(xi, y, xi, y + h, INK, 1.1))
    for i in range(tracks - 1):
        xa, xb = x + i * w / (tracks - 1), x + (i + 1) * w / (tracks - 1)
        for k in range(rows):
            dy = h / (rows + 1)
            sw = (.8 + (i * rand.random() * 2.2 if heavy else 0))
            o.append(L(xa, y + k * dy, xb, y + (k + 2) * dy, RED, sw, 'stroke-dasharray="3 1.5" opacity=".9"'))
            o.append(L(xb, y + k * dy, xa, y + (k + 2) * dy, INK, sw))
    return "".join(o)


def page_alle():
    pg = Page("alle", 2000, 1400, "Ruteplan: Alle andre sider",
              "Kontaktark med øvrige sider i konseptets språk, gruppert per rolle: Student, Faglærer og Admin.")
    pg.paper()
    pg.add(wordmark(32, 48, 28))
    pg.add(T(220, 48, "Alle andre sider, på papiret", 28, 700, INK))
    pg.add(demo(1968, 48, "end"))

    def s_invite(x, y, w, h):
        return T(x, y + 12, "Bård inviterte deg", 11, 700, INK, f="b") + tiny_lat(x + 10, y + 22, w - 20, h * .32, 3, 2) + bars(x, y + h * .55, w, 3, 6, 14) + R(x, y + h - 18, w, 16, RED)

    def s_login(x, y, w, h):
        return wordmarkish(x, y) + bars(x, y + h * .35, w, 2, 8, 22) + R(x, y + h * .35 + 50, w, 16, RED) + T(x, y + h - 10, "Glemt passord", 11, 600, INK, f="b")

    def wordmarkish(x, y):
        return L(x, y + 2, x + 8, y + 12, RED, 2) + L(x + 1, y + 12, x + 9, y + 2, INK, 2) + T(x + 14, y + 12, "Ruteplan", 12, 800, INK)

    def s_rules(x, y, w, h):
        return tiny_lat(x + 4, y + 2, w - 8, h * .42, 3, 3) + T(x, y + h * .56, "Linja er ordren din", 11, 700, RED, f="b") + T(x, y + h * .56 + 14, "To uker hver vei", 11, 700, INK, f="b") + bars(x, y + h * .56 + 22, w, 2) + R(x, y + h - 16, w, 14, INK)

    def s_start(x, y, w, h):
        return T(x, y + 10, "Hvor mye er på vei?", 11, 700, INK, f="b") + tiny_lat(x + 4, y + 18, w - 8, h * .45, 3, 2) + "".join(R(x + i * (w / 3), y + h * .72, w / 3 - 4, 16, PAPER, INK, .8) for i in range(3)) + check(x, y + h - 14, 12)

    def s_replay(x, y, w, h):
        o = [tiny_lat(x, y + 2, w, h * .62, 3, 4, seed=3)]
        o.append(chip(x, y + h * .72, 11) + chip(x + 16, y + h * .72, 11) + chip(x + 32, y + h * .72, 11))
        o.append(T(x + 50, y + h * .72 + 10, "3 KI-spillere", 11, 700, INK, f="b"))
        o.append(R(x, y + h - 15, w, 13, RED))
        return "".join(o)

    def s_replay_g(x, y, w, h):
        return (T(x, y + 10, "Første mot andre runde", 11, 700, INK, f="b") + tiny_lat(x, y + 18, w * .46, h * .55, 3, 3, True, 2) + tiny_lat(x + w * .54, y + 18, w * .46, h * .55, 3, 3, False, 2) + bars(x, y + h * .78, w, 2, 4, 9))

    def fri(x, y, w, label):
        return L(x, y, x + w, y, INK, 1.4) + L(x + 1, y, x + 1, y + 10, INK, 1.4) + T(x + 5, y + 10, label, 10.5, 600, INK, f="b")

    def s_test(x, y, w, h):
        o = [T(x, y + 10, "Flervalg", 11, 700, INK, f="b"), fri(x, y + h - 10, w, "Testfrist fr. 18. des")]
        for i in range(3):
            o.append(C(x + 5, y + 20 + i * 10, 3, WHITE, INK, 1) + R(x + 13, y + 18 + i * 10, w * .4, 4, INK2, extra='opacity=".55"'))
        ax = x + w * .56
        o.append(T(ax, y + 10, "Tegn linjene", 11, 700, RED, f="b") + L(ax, y + 15, ax, y + h * .5, INK, 1) + L(ax + w * .4, y + 15, ax + w * .4, y + h * .5, INK, 1) + L(ax, y + 20, ax + w * .4, y + h * .4, RED, 1.6, 'stroke-dasharray="3 2"'))
        o.append(T(x, y + h * .58, "Langsvar", 11, 700, INK, f="b") + R(x, y + h * .62, w, h * .26, WHITE, INK, .8))
        return "".join(o)

    def s_assess(x, y, w, h):
        return (ki_tag(x, y, "KI-vurdering", 10, w=78) + T(x, y + 32, "Teller ikke. Ikke karakter.", 11, 700, INK, f="b") + bars(x, y + 42, w, 5, 4, 10) + L(x, y + h - 8, x + w, y + h - 8, INK, 1))

    def s_report(x, y, w, h):
        return (R(x + w * .1, y, w * .8, h, WHITE, INK, 1) + T(x + w * .16, y + 14, "PDF", 11, 800, INK, f="b") + tiny_lat(x + w * .2, y + 20, w * .6, h * .3, 3, 3, True, 5) + bars(x + w * .16, y + h * .55, w * .68, 5, 3, 8))

    def s_side(x, y, w, h):
        o = []
        for i in range(4):
            xx = x + i * (w / 4)
            o.append(tiny_lat(xx + 2, y + 2, w / 4 - 8, h - 22, 2, 5, i > 0, i))
            o.append(T(xx + 2, y + h - 6, ["Spill 17", "Spill 3", "Spill 9", "Spill 41"][i], 10.5, 600, INK, f="b"))
        return "".join(o)

    def l_home(x, y, w, h):
        o = [T(x, y + 12, "Klasser", 13, 800, INK), fri(x, y + h - 12, w, "Spillfrist ti. 8. des, Debrief-frist fr. 11. des, Testfrist fr. 18. des")]
        for i, n in enumerate(["class-of-1994 IBE160", "class-of-1993 IBE160"]):
            yy = y + 22 + i * 50
            o.append(T(x, yy + 12, n, 12, 700, INK, f="b") + L(x, yy + 26, x + w, yy + 26, INK, 1.8) + C(x + w * (.72 if i == 0 else 1), yy + 26, 4, YEL if i == 0 else INK, INK, 1))
        return "".join(o)

    def l_report(x, y, w, h):
        o = [T(x, y + 12, "Klasserapport", 13, 800, INK)]
        vals = [240, 164, 121, 97, 58, 12]
        o.append(P("M" + "L".join(f"{num(x + i * w / 5)} {num(y + 20 + (240 - v) / 240 * (h - 60))}" for i, v in enumerate(vals)), c=INK, sw=2))
        o.append(bars(x, y + h - 30, w, 3, 3, 9))
        return "".join(o)

    def l_insight(x, y, w, h):
        return T(x, y + 12, "Spill 17, uke for uke", 13, 800, INK) + tiny_lat(x, y + 18, w, h - 42, 4, 6, True, 8) + "".join(T(x + i * w / 4, y + h - 6, f"Uke {9 + i * 2}", 10.5, 600, INK2, f="b") for i in range(4))

    def l_student(x, y, w, h):
        o = [T(x, y + 12, "Sara, Spill 17, Grossist", 12.5, 800, INK)]
        for i, (n, on) in enumerate([("Klassespill", 1), ("Debrief", 0), ("Quiz", 0), ("Replay", 0), ("Test", 0), ("Rapport", 0)]):
            yy = y + 26 + i * 14
            o.append(C(x + 5, yy, 3.6, YEL if on else PAPER2, INK, 1) + T(x + 14, yy + 4, n, 11, 500, INK, f="b"))
        o.append(tiny_lat(x + w * .5, y + 22, w * .5, h - 36, 2, 5, False, 1))
        return "".join(o)

    def l_plenum(x, y, w, h):
        o = []
        cols = 6
        for i in range(18):
            xx = x + (i % cols) * (w / cols)
            yy = y + (i // cols) * ((h) / 3)
            o.append(tiny_lat(xx + 2, yy + 2, w / cols - 6, h / 3 - 8, 3, 3, i % 3 != 0, i))
        return "".join(o)

    def l_cross(x, y, w, h):
        o = [T(x, y + 12, "Tverrklasse, 3 Klasser", 13, 800, INK)]
        for i, v in enumerate([.74, .62, .81]):
            yy = y + 28 + i * 26
            o.append(T(x, yy + 3, ["1992", "1993", "1994"][i], 11, 600, INK, f="b") + L(x + 34, yy, x + 34 + (w - 40) * v, yy, INK, 5))
        return "".join(o)

    def l_msg(x, y, w, h):
        o = [envelope(x, y + 2, 14), T(x + 20, y + 13, "Melding til Spill 2", 12.5, 800, INK)]
        o.append(bars(x, y + 26, w, 3, 4, 10))
        o.append(R(x, y + 62, w * .55, 15, INK))
        o.append(L(x, y + h - 26, x + w, y + h - 26, GRID2, 1) + bars(x, y + h - 18, w, 2, 3, 8))
        return "".join(o)

    def l_test(x, y, w, h):
        return (T(x, y + 12, "Lærers testspill", 13, 800, INK) + tiny_lat(x, y + 20, w * .62, h - 30, 3, 4, False, 4) + chip(x + w * .68, y + 22, 13) + chip(x + w * .68 + 18, y + 22, 13) + chip(x + w * .68 + 36, y + 22, 13) + T(x + w * .68, y + 52, "Du: Grossist", 11, 700, INK, f="b") + T(x + w * .68, y + 66, "Teller ikke", 11, 500, INK2, f="b"))

    def a_home(x, y, w, h):
        o = [T(x, y + 12, "Admin-område", 13, 800, INK)]
        for i, n in enumerate(["Brukere og roller", "KI-kostnad", "Revisjonslogg"]):
            yy = y + 26 + i * 26
            o.append(L(x, yy + 18, x + w, yy + 18, GRID2, 1) + T(x, yy + 12, n, 12, 600, INK, f="b"))
        return "".join(o)

    def a_users(x, y, w, h):
        o = [T(x, y + 12, "Brukere", 13, 800, INK)]
        for i, (n, r_) in enumerate([("Bård", "Faglærer"), ("Sara", "Student"), ("Kari", "Assistent"), ("Ola", "Student")]):
            yy = y + 24 + i * 20
            o.append(T(x, yy + 10, n, 11.5, 600, INK, f="b") + T(x + w, yy + 10, r_, 11.5, 500, INK2, a="end", f="b") + L(x, yy + 16, x + w, yy + 16, GRID, .7))
        return "".join(o)

    def a_cost(x, y, w, h):
        pts = [.2, .25, .4, .55, .5, .7, .62, .8]
        o = [T(x, y + 12, "KI-kostnad per Klasseøkt", 12.5, 800, INK)]
        o.append(P("M" + "L".join(f"{num(x + i * w / 7)} {num(y + h - 14 - p * (h - 40))}" for i, p in enumerate(pts)), c=INK, sw=2))
        o.append(L(x, y + h - 14, x + w, y + h - 14, INK, 1))
        return "".join(o)

    groups = [
        ("Student", [
            ("Invitasjon og registrering", "Lenke fra Bård, navn og passord.", s_invite, "p"),
            ("Logg inn", "E-post og passord, ingen åpen registrering.", s_login, "p"),
            ("Regler før første ordre", "Linjene forklart med ditt eget spor.", s_rules, "p"),
            ("Startoppgave", "Les av linjene: hvor mye er på vei?", s_start, "p"),
            ("Replay", "Samme spor, tre merkede KI-spillere.", s_replay, "p"),
            ("Replay-gjennomgang", "Første og andre plan side om side.", s_replay_g, "p"),
            ("Individuell test", "Flervalg, tegn linjene, langsvar.", s_test, "p"),
            ("KI-vurdering", "Merket, teller ikke, er aldri karakter.", s_assess, "p"),
            ("Studentrapport (PDF)", "Din plan, dine ordre, dine svar, på papir.", s_report, "s"),
            ("Alle spill side om side", "Klassens planer etter Debrief, anonymt.", s_side, "s"),
        ]),
        ("Faglærer", [
            ("Lærerhjem med klasser", "Klasser med datobånd og i dag-merke.", l_home, "s"),
            ("Klasserapport", "Trakten og Klassens kostnader.", l_report, "s"),
            ("Spillinnsikt", "Ett spill uke for uke, KI-uker merket.", l_insight, "s"),
            ("Studentside", "Én students steg og egen plan.", l_student, "s"),
            ("Spill alle side om side", "Plenumsvisning av alle planene.", l_plenum, "s"),
            ("Tverrklasse-statistikk", "Samme mål på tvers av Klasser.", l_cross, "s"),
            ("Meldinger", "Til Klasseøkt, spill eller student.", l_msg, "s"),
            ("Lærers testspill", "Prøv innstillingene mot KI-spillere.", l_test, "s"),
        ]),
        ("Admin", [
            ("Admin-område", "Inngang for plattformdrift.", a_home, "s"),
            ("Brukere og roller", "Hvem er hva, med logg over endringer.", a_users, "s"),
            ("KI-kostnad", "Kostnad over tid per Klasseøkt.", a_cost, "s"),
        ]),
    ]
    cols = 6
    cw, chh = 326, 315
    gx, gy = 40, 84
    # plasser
    positions = []
    r_, c_ = 0, 0
    for g_i, (gname, items) in enumerate(groups):
        for it in items:
            positions.append((gname, it, r_, c_))
            c_ += 1
            if c_ == cols:
                r_, c_ = r_ + 1, 0
        if g_i == 0:
            r_, c_ = r_ + 1, 0
    seen = set()
    for gname, (title, line, fn, kind), rr, cc in positions:
        x = gx + cc * cw
        y = gy + rr * chh
        if gname not in seen:
            seen.add(gname)
            pg.add(R(x, y, len(gname) * 12 + 22, 30, INK), T(x + 11, y + 22, gname, 19, 800, WHITE))
            pg.add(L(x, y + 30, 1960, y + 30, INK, 2))
        ty = y + 40
        if kind == "p":
            pg.add(tiny_phone(pg, x, ty, 150, 196, fn))
        else:
            pg.add(tiny_screen(pg, x, ty + 6, 300, 186, fn))
        pg.add(T(x, ty + 216, title, 18, 800, INK))
        pg.add(T(x, ty + 236, line, 15, 500, INK, f="b"))
    return pg


# ---------- kjør ----------
def main():
    for fn in (page_landing, page_klasse, page_oppsett, page_hjem, page_spill, page_dyn, page_debrief, page_oversikt, page_alle):
        fn().save()
    print("9 SVG skrevet")


if __name__ == "__main__":
    main()
