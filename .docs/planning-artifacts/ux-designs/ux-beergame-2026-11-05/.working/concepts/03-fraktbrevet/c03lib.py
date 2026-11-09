"""Blankettbiblioteket for konsept 03 Fraktbrev: primitiver og gjenbrukbare skjemadeler."""
import json
import random
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WEEKS = FX["weeks"]
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAMES = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

# Blankettfarger
CAN = "#FFD400"     # kanarigul original
CAN_L = "#FFF2A0"   # tomt felt
PINK = "#FF9EC7"    # rosa kopi
PINK_L = "#FFC9DF"
BLUE = "#8AD6F8"    # lyseblaa kopi, fraktbrev
BLUE_L = "#C9ECFC"
VIO = "#4A1FB8"     # fiolett stempelblekk
INK = "#14110F"     # svart trykk
RED = "#AE0F1C"     # roedt stempelblekk
DESK = "#24222B"    # pultlinoleum
REC = "#F7F7F2"     # kvitteringspapir
PLUM = "#3D0A26"    # trykk paa rosa
NAVY = "#06304A"    # trykk paa blaa
CARBON = "#1B2A8C"  # gjennomslag paa kopi
STEEL = "#9A9CA6"
PALE = "#E9E7EF"    # tekst paa pult

FONT_IMPORT = ("https://fonts.googleapis.com/css2?family=Archivo+Black&amp;family=Archivo+Narrow:wght@400;500;600;700"
               "&amp;family=Courier+Prime:ital,wght@0,400;0,700;1,400&amp;family=Caveat:wght@500;700&amp;display=swap")
CSS = f"""@import url('{FONT_IMPORT}');
.c03-lab{{font-family:'Archivo Narrow','Arial Narrow',Arial,sans-serif;font-weight:600}}
.c03-labb{{font-family:'Archivo Narrow','Arial Narrow',Arial,sans-serif;font-weight:700}}
.c03-nar{{font-family:'Archivo Narrow','Arial Narrow',Arial,sans-serif;font-weight:500}}
.c03-typ{{font-family:'Courier Prime','Courier New',Courier,monospace;font-weight:400}}
.c03-typb{{font-family:'Courier Prime','Courier New',Courier,monospace;font-weight:700}}
.c03-disp{{font-family:'Archivo Black','Arial Black',Arial,sans-serif;font-weight:400}}
.c03-pen{{font-family:'Caveat','Segoe Print',cursive;font-weight:700}}
"""
WIDTH = {"lab": .47, "labb": .49, "nar": .45, "typ": .6, "typb": .6, "disp": .68, "pen": .40}


def num(v, dec=2):
    s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def T(x, y, s, size=14, cls="lab", fill=INK, a="start", ls=None, extra=""):
    ls_a = f' letter-spacing="{ls}"' if ls else ""
    anc = f' text-anchor="{a}"' if a != "start" else ""
    return (f'<text class="c03-{cls}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"{anc}{ls_a} {extra}>'
            f'{escape(str(s))}</text>')


def wrap(s, maxw, size, cls="nar"):
    cw = WIDTH.get(cls, .5) * size
    out, cur = [], ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if len(trial) * cw > maxw and cur:
            out.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


def TW(x, y, s, maxw, size=14, cls="nar", fill=INK, lh=None, a="start"):
    lh = lh or size * 1.3
    return "".join(T(x, y + i * lh, ln, size, cls, fill, a) for i, ln in enumerate(wrap(s, maxw, size, cls)))


def TH(s, maxw, size=14, cls="nar", lh=None):
    """Hoeyden en TW-blokk tar."""
    lh = lh or size * 1.3
    return len(wrap(s, maxw, size, cls)) * lh


def R(x, y, w, h, fill="none", stroke=None, sw=1, rx=0, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    rr = f' rx="{rx}"' if rx else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{st}{rr} {extra}/>'


def L(x1, y1, x2, y2, stroke=INK, sw=1, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def C(x, y, r, fill="none", stroke=None, sw=1, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}"{st} {extra}/>'


def P(d, fill="none", stroke=INK, sw=1.6, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"' if stroke else ""
    return f'<path d="{d}" fill="{fill}"{st} {extra}/>'


def G(inner, x=0, y=0, s=1, rot=0, extra=""):
    tf = []
    if x or y:
        tf.append(f"translate({x:.1f} {y:.1f})")
    if rot:
        tf.append(f"rotate({rot})")
    if s != 1:
        tf.append(f"scale({s})")
    t = f' transform="{" ".join(tf)}"' if tf else ""
    return f"<g{t} {extra}>{inner}</g>"


class Page:
    def __init__(self, side, fname, w, h, title, desc, bg=DESK):
        self.side, self.fname, self.w, self.h = side, fname, w, h
        self.title, self.desc, self.bg = title, desc, bg
        self.n = 0
        self.body = []
        self.sh = f"c03-{side}-sh"
        self.ink = f"c03-{side}-ink"
        self.hatch = f"c03-{side}-hatch"
        self.defs = [
            f'<filter id="{self.sh}" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#000" flood-opacity=".38"/></filter>',
            f'<filter id="{self.ink}" x="-6%" y="-14%" width="112%" height="128%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="4" result="n"/>'
            '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2.6 2.3" result="h"/>'
            '<feComposite in="SourceGraphic" in2="h" operator="in" result="s"/>'
            '<feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="9" result="w"/>'
            '<feDisplacementMap in="s" in2="w" scale="2"/></filter>',
            f'<pattern id="{self.hatch}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="{INK}" stroke-width="1.4"/></pattern>',
        ]

    def uid(self, name="x"):
        self.n += 1
        return f"c03-{self.side}-{name}{self.n}"

    def add(self, *parts):
        self.body.extend(parts)

    def clip(self, x, y, w, h, rx=0):
        i = self.uid("clip")
        self.defs.append(f'<clipPath id="{i}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></clipPath>')
        return i

    def paper(self, x, y, w, h, fill=CAN, rot=0, stroke=None):
        tr = f'transform="rotate({rot} {x + w / 2:.1f} {y + h / 2:.1f})"' if rot else ""
        st = f'stroke="{stroke}" stroke-width="1"' if stroke else ""
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" filter="url(#{self.sh})" {st} {tr}/>'

    def save(self):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
               f'font-family="\'Archivo Narrow\',\'Arial Narrow\',Arial,sans-serif">'
               f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>"
               f"<style>{CSS}</style><defs>{''.join(self.defs)}</defs>"
               f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>' + "".join(self.body) + "</svg>")
        (HERE / self.fname).write_text(svg, encoding="utf-8")


# ---------- Perforering og papir ----------
def perf_h(x, y, w, color=DESK, r=2.4, step=9):
    return "".join(C(x + i * step, y, r, color) for i in range(int(w // step) + 1))


def perf_v(x, y, h, color=DESK, r=2.4, step=9):
    return "".join(C(x, y + i * step, r, color) for i in range(int(h // step) + 1))


def tractor(x, y, h, color=DESK, step=38, r=7):
    return "".join(C(x, y + i * step, r, color) for i in range(int(h // step) + 1))


def torn_top(x, y, w, h, fill, teeth=9):
    """Ark med avrevet perforert overkant."""
    d = f"M{x} {y + h} L{x} {y}"
    n = int(w // teeth)
    tw = w / n
    for i in range(n):
        d += f" q{tw / 2:.2f} 5 {tw:.2f} 0"
    d += f" L{x + w} {y + h} Z"
    return f'<path d="{d}" fill="{fill}"/>'


# ---------- Ikoner: egentegnede, samme strek ----------
def icon_role(role, x, y, s=24, color=INK, sw=1.8):
    k = s / 24
    d = {
        "Detaljist": "M3 10h18l-2-6H5zM3 10c0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0M5 13v8h14v-8M10 21v-5h4v5",
        "Grossist": "M3 21v-7h8v7zM13 21v-7h8v7zM8 14V7h8v7M7 17h0M17 17h0M12 10h0",
        "Distributør": "M2 7h12v10H2zM14 11h4l4 3v3h-8zM6.5 19.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17.5 19.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
        "Fabrikk": "M3 21V11l5 3v-3l5 3v-3l5 3V4h3v17zM7 18h2M12 18h2M17 18h2",
    }[role]
    return f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.3f})">{P(d, "none", color, sw / k if k < 1 else sw)}</g>'


def icon_stamp(x, y, s=28, color="#fff"):
    k = s / 28
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.3f})">'
            + P("M14 2a5 5 0 0 1 3 9c-.6.5-1 1.4-1 2.2V16h5a2 2 0 0 1 2 2v3H5v-3a2 2 0 0 1 2-2h5v-2.8c0-.8-.4-1.7-1-2.2a5 5 0 0 1 3-9z", color, None)
            + R(4, 23, 20, 3, color) + "</g>")


def icon_back(x, y, color=INK):
    return P(f"M{x + 8} {y + 3}h15v16H{x + 8}l-7-8zM{x + 12} {y + 8}l6 6M{x + 18} {y + 8}l-6 6", "none", color, 1.8)


def icon_lock(x, y, color=INK, s=20):
    k = s / 20
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.3f})">' + R(3, 9, 14, 10, color)
            + P("M6 9V6a4 4 0 0 1 8 0v3", "none", color, 2) + "</g>")


def icon_clip(x, y, w=44, color=INK):
    """Binders: bulldogklype sett forfra."""
    return (P(f"M{x} {y + 14}L{x + 7} {y}h{w - 14}L{x + w} {y + 14}z", color, None)
            + P(f"M{x + 12} {y}C{x + 10} {y - 13} {x + w - 10} {y - 13} {x + w - 12} {y}", "none", STEEL, 2)
            + R(x, y + 14, w, 4, "#3A3840"))


def icon_chev(x, y, color=INK, d=1):
    return P(f"M{x} {y - 5}l{6 * d} 5l{-6 * d} 5", "none", color, 2)


def icon_pause(x, y, color=INK, s=14):
    return R(x, y, s * .32, s, color) + R(x + s * .62, y, s * .32, s, color)


def icon_clock(x, y, r=7, color=INK):
    return C(x, y, r, "none", color, 1.6) + P(f"M{x} {y - r + 2.5}V{y}l{r - 3} 2", "none", color, 1.6)


def ki_mark(x, y, color=VIO, h=20, label="KI-spiller", size=13):
    """KI-merket: stiplet ramme og tekst, aldri bare farge."""
    w = len(label) * size * .5 + 14
    return (R(x, y, w, h, "none", color, 1.4, 2, 'stroke-dasharray="3 2"')
            + T(x + w / 2, y + h - 5.5, label, size, "labb", color, "middle"))


# ---------- Stempel ----------
def stamp(pg, x, y, text, size=30, rot=-7, color=VIO, ink=True, double=True, pad=None):
    """x,y er midten av stempelet."""
    w = len(text) * size * .78 + size * 1.0
    h = size * 1.7
    f = f'filter="url(#{pg.ink})"' if ink else ""
    inner = R(-w / 2, -h / 2, w, h, "none", color, max(2, size * .09), 4)
    if double:
        inner += R(-w / 2 + size * .16, -h / 2 + size * .16, w - size * .32, h - size * .32, "none", color, max(1, size * .035), 2)
    inner += T(0, size * .36, text, size, "disp", color, "middle", ls=round(size * .05, 1))
    return f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot})" {f}>{inner}</g>'


def stamp_button(x, y, w, h, text, sub=None, enabled=True, size=20, fill=VIO, subsize=13):
    if enabled:
        out = R(x, y, w, h, fill, None, 1, 4)
        out += R(x + 4, y + 4, w - 8, h - 8, "none", "#fff", 1.2, 2, 'opacity=".55"')
        ic = "#fff"
    else:
        out = R(x, y, w, h, "none", INK, 1.5, 4, 'stroke-dasharray="5 3"')
        ic = INK
    out += icon_stamp(x + 14, y + h / 2 - 15, 30, ic)
    if sub:
        out += T(x + 54, y + h / 2 + 1, text, size, "disp", ic)
        out += T(x + 54, y + h / 2 + 8 + subsize, sub, subsize, "lab", ic)
    else:
        out += T(x + 54, y + h / 2 + size * .36, text, size, "disp", ic)
    return out


def plain_button(x, y, w, h, text, color=INK, size=15, fill="none", cls="labb", a="middle"):
    tx = x + w / 2 if a == "middle" else x + 12
    return R(x, y, w, h, fill, color, 1.6, 3) + T(tx, y + h / 2 + size * .35, text, size, cls, color if fill == "none" else "#fff", a)


# ---------- Felt ----------
def field(x, y, w, h, label, value="", lc=INK, vc=INK, size=30, stroke=None, sub=None, cls="typb", fill="none", lsize=13):
    stroke = stroke or lc
    out = R(x, y, w, h, fill, stroke, 1.1)
    out += T(x + 7, y + 16, label.upper(), lsize, "lab", lc, ls=.5)
    if value != "":
        out += T(x + 7, y + h - 11, value, size, cls, vc)
    if sub:
        out += T(x + w - 6, y + h - 11, sub, 13, "nar", lc, "end")
    return out


def tally(x, y, n, color=INK, h=17, wrap_at=4):
    """Blyantstreker: fem og fem. Alltid til skala med tallet."""
    rng = random.Random(n * 7 + 3)
    out = []
    step, gap = 4.4, 7
    gx, gy = x, y
    for g in range(n // 5 + (1 if n % 5 else 0)):
        k = 5 if (g + 1) * 5 <= n else n % 5
        for i in range(min(k, 4)):
            j = rng.uniform(-.8, .8)
            out.append(L(gx + i * step, gy + j, gx + i * step + rng.uniform(-.7, .7), gy + h - j, color, 1.6, 'stroke-linecap="round"'))
        if k == 5:
            out.append(L(gx - 2, gy + h - 3, gx + 3 * step + 2, gy + 3, color, 1.6, 'stroke-linecap="round"'))
        gx += 3 * step + gap + 2
        if (g + 1) % wrap_at == 0:
            gx = x
            gy += h + 4
    return "".join(out)


# ---------- Snora: de fire ventende Rollene ----------
SEATS_W11 = [("Detaljist", "Ida", "bestilt", ""), ("Grossist", "Sara", "deg", ""),
             ("Distributør", "Mikkel", "bestilt", ""), ("Fabrikk", "Jonas", "venter", "3 min")]


def snor(pg, x, y, w, seats=SEATS_W11, h=70, cw=None, sag=5):
    """Fire smaa kopier paa snor. Rolle og navn i tekst, stemplet eller ikke."""
    n = len(seats)
    gap = 6
    cw = cw or (w - gap * (n - 1)) / n
    out = [P(f"M{x - 12} {y}Q{x + w / 2} {y + sag * 2} {x + w + 12} {y}", "none", "#D9D4C5", 1.8)]
    for i, (role, name, state, note) in enumerate(seats):
        cx = x + i * (cw + gap)
        rot = [-1.1, .8, -.6, 1.2][i % 4]
        fill = PINK if state in ("bestilt", "ki-bestilt", "deg-bestilt") else CAN
        print_c = PLUM if fill == PINK else INK
        top = y + 7
        g = pg.paper(cx, top, cw, h, fill)
        g += T(cx + 6, top + 19, name, 15, "typb", print_c)
        g += icon_role(role, cx + cw - 22, top + 5, 16, print_c, 1.5)
        g += T(cx + 6, top + 35, role, 13, "lab", print_c)
        if state == "bestilt" or state == "deg-bestilt":
            sx = cx + cw / 2
            g += f'<g transform="translate({sx:.1f} {top + 54}) rotate(-5)">' + R(-34, -10, 68, 19, "none", VIO, 1.6, 2) + T(0, 4.5, "BESTILT", 13, "labb", VIO, "middle", ls=.8) + "</g>"
        elif state == "venter":
            g += icon_clock(cx + 13, top + 53, 6, print_c) + T(cx + 23, top + 58, f"venter {note}", 13, "nar", print_c)
        elif state == "deg":
            g += T(cx + 6, top + 58, "venter: deg", 13, "labb", print_c)
        elif state == "ki":
            g += ki_mark(cx + 5, top + 42, VIO, 20, "KI-spiller", 13)
        elif state == "ki-bestilt":
            g += ki_mark(cx + 5, top + 42, VIO, 20, "KI-spiller", 13)
        elif state == "pause":
            g += icon_pause(cx + 7, top + 47, print_c, 12) + T(cx + 23, top + 58, note or "Pause", 13, "nar", print_c)
        g += R(cx + cw / 2 - 5, y - 2, 10, 15, INK, None, 1, 1)
        out.append(f'<g transform="rotate({rot} {cx + cw / 2:.1f} {y})">{g}</g>')
    return "".join(out)


# ---------- Fraktbrev ----------
def slips_for(week):
    """Forsendelser paa vei inn til Sara: Ordre uke w kommer i uke w+4."""
    g = [w["seats"]["Grossist"]["ordre"] for w in WEEKS]
    items = []
    for w in range(week - 3, week):
        items.append((g[w - 1], w))
    assert sum(i[0] for i in items) == WEEKS[week - 1]["seats"]["Grossist"]["paa_vei_foer_ordre"]
    return items


def slip(x, y, w, n, line, unit, kind="solid", first=False):
    h = max(n * unit, 42)
    cells = ""
    cw = 12
    k = (h - 4) / n if n else 0
    is_ghost = kind == "ghost"
    col = VIO if is_ghost else NAVY
    for i in range(n):
        cells += R(x + w - cw - 4, y + 2 + i * k + .8, cw, max(k - 1.6, 1.2), "none" if is_ghost else BLUE_L, col, .9)
    if is_ghost:
        body = R(x, y, w, h, CAN_L, VIO, 1.8, 0, 'stroke-dasharray="6 4"')
    else:
        body = R(x, y, w, h, BLUE, NAVY, .7)
    return body + cells + T(x + 7, y + 19, f"{n} kasser", 15, "typb", col) + T(x + 7, y + 36, line, 13, "lab", col)


def slip_col(pg, x, y, w, items, unit=11, ghost=None, extra_solid=None, avail=None, week=None):
    """Kolonne med fraktbrev klipset paa siden av skjemaet. Hoeyden foelger antall kasser."""
    total = sum(i[0] for i in items) + (ghost or 0) + (extra_solid or 0)
    if avail:
        unit = min(unit, avail / max(total, 1))
    out = []
    cy = y
    for idx, (n, w_) in enumerate(items):
        line = "neste levering" if idx == 0 else f"bestilt uke {w_}"
        out.append(slip(x, cy, w, n, line, unit))
        cy += max(n * unit, 42)
    if extra_solid:
        out.append(slip(x, cy, w, extra_solid, f"bestilt uke {week}", unit))
        cy += extra_solid * unit
    if ghost:
        out.append(slip(x, cy, w, ghost, "om du stempler", unit, "ghost"))
        cy += ghost * unit
    return "".join(out), cy


# ---------- Bunken ----------
def bunke(x, y, w, week, orders=None, highlight=None, tabs=10, label_c=PALE, show_label=True, tab_h=48):
    """Sidesnitt av bunken pluss faner med egen ordrehistorikk. Ingen ende synes: den vokser bare."""
    orders = orders or [v["seats"]["Grossist"]["ordre"] for v in WEEKS]
    done = week - 1
    out = []
    # tykkelse: en papirkant per ferdig uke
    edge = 2.0 if done <= 22 else 1.4
    for i in range(done):
        wob = (i * 13 % 7) - 3
        out.append(R(x + 2 + wob * .5, y + i * edge, w - 4 - wob * .3, edge - .4, PINK if i % 2 == 0 else PINK_L))
    ty = y + done * edge + 2
    shown = list(range(max(1, done - tabs + 1), done + 1))
    tw = (w - 0) / tabs
    for j, wk in enumerate(shown):
        tx = x + j * tw
        hi = wk == highlight
        d = f"M{tx + 1} {ty}h{tw - 2}v{tab_h - 5}l-4 5h{-(tw - 10)}l-4 -5z"
        out.append(P(d, PINK, PLUM, .6))
        out.append(T(tx + tw / 2, ty + 16, str(wk), 13, "lab", PLUM, "middle"))
        out.append(T(tx + tw / 2, ty + 36, str(orders[wk - 1]), 18, "typb", VIO if hi else CARBON, "middle"))
        if wk <= 4:
            out.append(L(tx + 7, ty + 20, tx + tw - 7, ty + 20, PLUM, 1, 'stroke-dasharray="2 2"'))
    ly = ty + tab_h + 21
    if show_label:
        out.append(T(x + 2, ly, "BUNKEN: ordre per uke", 13, "lab", label_c, ls=.4))
        out.append(T(x + w - 16, ly, "Bla i bunken", 14, "labb", label_c, "end") + icon_chev(x + w - 10, ly - 5, label_c))
    return "".join(out), ly


# ---------- Telefon ----------
def phone(pg, x, y, inner, s=1.0, frame=INK):
    i = pg.clip(0, 0, 390, 844, 26)
    return (f'<g transform="translate({x} {y}) scale({s})">'
            + R(-9, -9, 408, 862, "#0B0A0D", "#55525E", 2, 34, f'filter="url(#{pg.sh})"')
            + f'<g clip-path="url(#{i})">{R(0, 0, 390, 844, DESK)}{inner}</g></g>')


def demo(x, y, color=PALE, a="start", size=13):
    return T(x, y, "Demodata", size, "lab", color, a)


# ---------- Ordreseddelen ----------
def ordreseddel(pg, week=11, typed=None, stamped=False, ghost=None, paper=CAN, top=92, extra_solid=None,
                keypad=True, button=True, hi=(), body=None, pv=None, form_h=None, x0=8, role="Grossist"):
    """Hele skjemaet paa 390-skala. Toppen av arket starter paa y=top."""
    d = WEEKS[week - 1]["seats"][role]
    lc = INK if paper == CAN else PLUM
    vc = INK if paper == CAN else CARBON
    W = 374
    form_h = form_h or 600
    out = []
    if paper == CAN:
        out.append(pg.paper(x0, top, W, form_h, paper))
        out.append(perf_h(x0 + 6, top + 8, W - 12, DESK, 2.2))
    else:
        out.append(f'<g filter="url(#{pg.sh})">{torn_top(x0, top, W, form_h, paper)}</g>')
    # hode
    hy = top + 16
    out.append(icon_role(role, x0 + 10, hy + 2, 28, lc, 1.8))
    out.append(T(x0 + 44, hy + 17, "ORDRESEDDEL" if paper == CAN else "KOPI", 17, "disp", lc))
    out.append(T(x0 + 44, hy + 34, f"Spill 17 · {role} · {NAMES[role]}", 14, "lab", lc))
    out.append(R(x0 + 200, hy - 2, 84, 42, "none", lc, 1.4))
    out.append(T(x0 + 206, hy + 13, "UKE", 13, "lab", lc))
    out.append(T(x0 + 278, hy + 34, str(week), 32, "typb", vc, "end"))
    # felt
    fx, fy = x0 + 8, top + 62
    cw, rh = 124, 78
    vals = [("Lager", str(d["lager"])), ("Restordre", str(d["restordre"])),
            ("Ordre inn", str(d["innkommende_ordre"])), ("Levering", str(d["levering"])),
            ("Sendt", str(d["sendt"])), ("Totalkostnad", num(d["kost_sum"]) + " kr")]
    for i, (lb, v) in enumerate(vals):
        cx = fx + (i % 2) * cw
        cy = fy + (i // 2) * rh
        size = 21 if lb == "Totalkostnad" else 32
        col = RED if (lb == "Restordre" and d["restordre"] > 0) else vc
        out.append(field(cx, cy, cw, rh, lb, v, lc, col, size))
        if lb == "Restordre" and d["restordre"]:
            out.append(tally(cx + 54, cy + 30, d["restordre"], RED, 18, wrap_at=3))
        if lb == "Lager" and d["lager"]:
            out.append(tally(cx + 54, cy + 30, d["lager"], vc, 18, wrap_at=3))
    # paa vei
    sx = fx + 2 * cw + 4
    sw = W - (sx - x0) - 4
    pv_val = pv if pv is not None else d["paa_vei_foer_ordre"] + (extra_solid or 0)
    items = slips_for(week)
    col, end = slip_col(pg, sx, fy + 42, sw, items, 12, ghost, extra_solid, avail=(form_h - 62 - 42 - 8), week=week)
    head = R(sx, fy, sw, 42, BLUE, NAVY, .8) + T(sx + 7, fy + 15, "PÅ VEI", 13, "lab", NAVY, ls=.5)
    head += T(sx + sw - 8, fy + 34, str(pv_val), 26, "typb", NAVY, "end") + T(sx + 7, fy + 33, "kasser", 13, "nar", NAVY)
    out.append(col + head + icon_clip(sx + sw / 2 - 22, fy - 18, 44))
    # ordre
    oy = fy + 3 * rh + 8
    if body is None:
        out.append(R(fx, oy, 2 * cw, 100, CAN_L if paper == CAN else PINK_L, lc, 2.2))
        out.append(T(fx + 9, oy + 19, "ORDRE", 15, "labb", lc, ls=.6))
        out.append(T(fx + 2 * cw - 9, oy + 19, "kasser, ett heltall", 13, "nar", lc, "end"))
        if typed is not None:
            out.append(T(fx + 12, oy + 84, typed, 66, "typb", vc))
            cx_ = fx + 16 + len(typed) * 39.6
        else:
            cx_ = fx + 14
        if not stamped:
            out.append(R(cx_, oy + 36, 3, 52, INK))
        if stamped:
            out.append(stamp(pg, fx + 2 * cw - 86, oy + 56, "BESTILT", 22, -7))
        ky = oy + 108
        if keypad:
            kw, kh = 2 * cw / 6, 50
            keys = list("123456") + list("7890") + ["back"]
            for i, k in enumerate(keys):
                kx = fx + (i % 6) * kw
                kyy = ky + (i // 6) * kh
                wk = kw if k != "back" else 2 * kw
                out.append(R(kx + 1.5, kyy + 1.5, wk - 3, kh - 3, CAN_L, INK, 1.2, 3))
                if k == "back":
                    out.append(icon_back(kx + wk / 2 - 12, kyy + 14))
                else:
                    out.append(T(kx + kw / 2, kyy + 32, k, 22, "typb", INK, "middle"))
            ky += 2 * kh + 6
        if button and not stamped:
            ok = typed is not None
            out.append(stamp_button(fx, ky, 2 * cw, 78, "STEMPLE BESTILT" if ok else "SKRIV ET TALL", "Kan ikke endres etterpå" if ok else "Stempelet låser ordren", ok, 18))
    else:
        out.append(body(fx, oy, 2 * cw))
    return "".join(out)
