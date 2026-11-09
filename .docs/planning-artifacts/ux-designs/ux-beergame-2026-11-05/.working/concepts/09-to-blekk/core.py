"""Felles byggeklosser for konsept 09 To blekk (arbeidsnavn Blekk).

To blekk og en trykkregel:
  OR og CY er de to blekkene. INK er overtrykk (begge blekk oppå hverandre, nær svart).
  PAPER er utsparing: papiret skinner bare gjennom der brukeren skriver.
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
F = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WEEKS = {w["week"]: w for w in F["weeks"]}
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAMES = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

OR = "#FF5A1F"
CY = "#00D4FF"
INK = "#12060B"
PAPER = "#FFFFFF"
ANG = -11

CYAN = {"g": CY, "c": OR}     # restordre: cyan grunn, oransje motblekk
ORANGE = {"g": OR, "c": CY}   # lager: oransje grunn, cyan motblekk

FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?family=Anton&amp;"
    "family=Libre+Franklin:wght@400;500;700;800&amp;display=swap"
)
BODY_STACK = "'Libre Franklin','Franklin Gothic Book','Arial Narrow',Arial,sans-serif"
POSTER_STACK = "Anton,'Haettenschweiler','Franklin Gothic Demi Cond','Arial Narrow',sans-serif"

CSS = f"""@import url('{FONT_IMPORT}');
.c09-a{{font-family:{POSTER_STACK};font-weight:400;letter-spacing:0}}
.c09-b{{font-family:{BODY_STACK};font-weight:400}}
.c09-m{{font-family:{BODY_STACK};font-weight:500}}
.c09-k{{font-family:{BODY_STACK};font-weight:700}}
.c09-x{{font-family:{BODY_STACK};font-weight:800}}
.c09-tn{{font-variant-numeric:tabular-nums lining-nums}}
.c09-u{{text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1.5px}}
"""


def kr(v, dec=True):
    s = f"{v:,.2f}" if dec else f"{v:,.0f}"
    return s.replace(",", " ").replace(".", ",")


def seat(week, role="Grossist"):
    return WEEKS[week]["seats"][role]


def history(week, role="Grossist"):
    return [WEEKS[w]["seats"][role]["ordre"] for w in range(1, week)]


class Doc:
    def __init__(self, side, name, w, h, title, desc, ground=OR):
        self.side, self.name, self.w, self.h = side, name, w, h
        self.title, self.desc, self.ground = title, desc, ground
        self.n = 0
        self.defs = []
        self.out = []

    def id(self, tag):
        self.n += 1
        return f"c09-{self.side}-{tag}{self.n}"

    def add(self, *parts):
        self.out.extend(parts)

    def clip_rect(self, x, y, w, h, r=0):
        i = self.id("clip")
        self.defs.append(f'<clipPath id="{i}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath>')
        return i

    def clip_poly(self, pts, inner=""):
        i = self.id("clip")
        self.defs.append(f'<clipPath id="{i}"><polygon points="{pts}">{inner}</polygon></clipPath>')
        return i

    def hatch(self, color=INK, gap=7, width=2):
        i = self.id("hatch")
        self.defs.append(
            f'<pattern id="{i}" width="{gap}" height="{gap}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate({ANG + 45})"><rect width="{gap}" height="{gap}" fill="none"/>'
            f'<line x1="0" y1="0" x2="0" y2="{gap}" stroke="{color}" stroke-width="{width}"/></pattern>'
        )
        return i

    def save(self):
        body = "\n".join(self.out)
        defs = "".join(self.defs)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" font-family="{BODY_STACK}">\n'
            f"<title>{escape(self.title)}</title>\n<desc>{escape(self.desc)}</desc>\n"
            f"<style>{CSS}</style>\n<defs>{defs}</defs>\n"
            f'<rect width="{self.w}" height="{self.h}" fill="{self.ground}"/>\n{body}\n</svg>\n'
        )
        (HERE / f"{self.name}.svg").write_text(svg, encoding="utf-8")


def T(x, y, s, size=14, cls="c09-b", fill=INK, anchor=None, rot=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    r = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    return f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}"{a}{r} {extra}>{escape(str(s))}</text>'


def A(x, y, s, size=40, fill=INK, anchor=None, rot=None, stroke=None, sw=0):
    extra = ""
    if stroke:
        extra = f'stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="miter" paint-order="stroke"'
    return T(x, y, s, size, "c09-a", fill, anchor, rot, extra)


def est(s, size, per=0.54):
    return len(s) * size * per


def wrap(s, size, width, per=0.52):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if len(t) * size * per > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def P(x, y, s, size=14, width=300, lead=None, cls="c09-b", fill=INK, anchor=None, per=0.52, rot=None):
    lead = lead or round(size * 1.34, 1)
    lines = wrap(s, size, width, per)
    if rot is not None:
        inner = "".join(T(x, y + i * lead, l, size, cls, fill, anchor) for i, l in enumerate(lines))
        return f'<g transform="rotate({rot} {x} {y})">{inner}</g>'
    return "".join(T(x, y + i * lead, l, size, cls, fill, anchor) for i, l in enumerate(lines))


def plines(s, size, width, per=0.52):
    return len(wrap(s, size, width, per))


def R(x, y, w, h, fill=INK, stroke=None, sw=0, r=0, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    rr = f' rx="{r}"' if r else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{st}{rr} {extra}/>'


def L(x1, y1, x2, y2, stroke=INK, sw=1, extra=""):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def poly(pts, fill=INK, extra=""):
    p = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    return f'<polygon points="{p}" fill="{fill}" {extra}/>'


def G(body, x=0, y=0, s=1, rot=None, extra=""):
    t = f"translate({x} {y})"
    if s != 1:
        t += f" scale({s})"
    if rot is not None:
        t += f" rotate({rot})"
    return f'<g transform="{t}" {extra}>{body}</g>'


# ---- Ikoner, tegnet med én strek og samme vekt -------------------------------------------------


def ic_check(x, y, c=INK, s=1):
    return (f'<path d="M{x} {y-1*s} l{4*s} {4*s} l{7*s} {-8*s}" fill="none" stroke="{c}" '
            f'stroke-width="{2.4*s}" stroke-linecap="square"/>')


def ic_wait(x, y, c=INK, s=1):
    """Timeglass, form for venter."""
    return (f'<path d="M{x} {y-6*s} h{10*s} l{-10*s} {12*s} h{10*s} Z" fill="none" stroke="{c}" '
            f'stroke-width="{2*s}" stroke-linejoin="miter"/>')


def ic_run(x, y, c=INK, s=1):
    """Halvfull sirkel, form for pågår."""
    r = 5.5 * s
    cx, cy = x + r, y
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="{2*s}"/>'
            f'<path d="M{cx} {cy-r} A{r} {r} 0 0 1 {cx} {cy+r} Z" fill="{c}"/>')


def ic_done(x, y, c=INK, s=1):
    """Fylt sirkel, form for ferdig."""
    r = 5.5 * s
    return f'<circle cx="{x+r}" cy="{y}" r="{r}" fill="{c}"/>'


def ic_pause(x, y, c=INK, s=1):
    return R(x + 1 * s, y - 6 * s, 3.4 * s, 12 * s, c) + R(x + 6.6 * s, y - 6 * s, 3.4 * s, 12 * s, c)


def ic_lock(x, y, c=INK, s=1):
    return (f'<path d="M{x+2.5*s} {y-3*s} v{-3*s} a{3.5*s} {3.5*s} 0 0 1 {7*s} 0 v{3*s}" fill="none" '
            f'stroke="{c}" stroke-width="{2*s}"/>' + R(x, y - 3 * s, 12 * s, 9.5 * s, c))


def ic_up(x, y, c=INK, s=1):
    return (f'<path d="M{x-10*s} {y+6*s} L{x} {y-6*s} L{x+10*s} {y+6*s}" fill="none" stroke="{c}" '
            f'stroke-width="{4*s}" stroke-linecap="square"/>')


def ic_down(x, y, c=INK, s=1):
    return (f'<path d="M{x-10*s} {y-6*s} L{x} {y+6*s} L{x+10*s} {y-6*s}" fill="none" stroke="{c}" '
            f'stroke-width="{4*s}" stroke-linecap="square"/>')


def ic_arrow(x1, y, x2, c=INK, sw=2):
    d = 6 if x2 > x1 else -6
    return (f'<path d="M{x1} {y} H{x2} M{x2-d} {y-5} L{x2} {y} L{x2-d} {y+5}" fill="none" '
            f'stroke="{c}" stroke-width="{sw}"/>')


def ic_skip(x, y, c=INK, s=1):
    return (poly([(x, y - 7 * s), (x + 9 * s, y), (x, y + 7 * s)], c)
            + poly([(x + 9 * s, y - 7 * s), (x + 18 * s, y), (x + 9 * s, y + 7 * s)], c)
            + R(x + 18 * s, y - 7 * s, 3 * s, 14 * s, c))


def ic_upload(x, y, c=INK, s=1):
    return (f'<path d="M{x} {y+7*s} h{16*s} M{x+8*s} {y+3*s} v{-12*s} M{x+3*s} {y-4*s} L{x+8*s} {y-9*s} '
            f'L{x+13*s} {y-4*s}" fill="none" stroke="{c}" stroke-width="{2.2*s}"/>')


def ki_tag(x, y, fg=OR, bg=INK, size=13):
    """KI-merket: alltid tekst i en svart plate, aldri bare farge."""
    w = size * 1.7
    return R(x, y - size + 1, w, size + 3, bg) + T(x + w / 2, y, "KI", size, "c09-x", fg, "middle")


def status_ic(status, x, y, c=INK, s=1):
    return {"ferdig": ic_done, "pågår": ic_run, "pauset": ic_pause, "venter": ic_wait}[status](x, y, c, s)


# ---- Telefon og spillskjerm --------------------------------------------------------------------


def phone(doc, x, y, inner, s=1.0, ground=OR, w=390, h=844):
    """Enkel ramme. Innhold tegnes i 390x844 og klippes i ramma."""
    c = doc.clip_rect(0, 0, w, h, 34)
    return G(
        R(-7, -7, w + 14, h + 14, INK, r=40)
        + f'<g clip-path="url(#{c})">{R(0, 0, w, h, ground)}{inner}</g>'
        + f'<rect x="-1" y="-1" width="{w+2}" height="{h+2}" rx="35" fill="none" stroke="{INK}" stroke-width="3"/>',
        x, y, s,
    )


def stack(x, ybase, shipments, ghost, ch, bw=37, bh=14.5, gap=2, cols=2, sg=5):
    """Teller blokker nedenfra. shipments = sendinger på vei. ghost = det du taster, hvitt til du bekrefter."""
    out, y, col, row_y = [], ybase, 0, ybase
    positions = []
    for si, n in enumerate(list(shipments) + ([ghost] if ghost else [])):
        is_ghost = ghost and si == len(shipments)
        for i in range(n):
            bx = x + col * (bw + gap)
            positions.append((bx, row_y - bh, is_ghost))
            col += 1
            if col == cols:
                col = 0
                row_y -= bh + gap
        if col != 0:
            col = 0
            row_y -= bh + gap
        row_y -= sg
    for bx, by, g in positions:
        out.append(R(bx, round(by, 1), bw, bh, PAPER if g else ch["c"], INK, 1.6))
    top = positions[-1][1] if positions else ybase
    return "".join(out), top


def margin_waiting(x, y, people, size=13, lead=16):
    """people: (status, navn, rolle/tid). status: done, wait, you, ki"""
    out = [T(x, y, "Venter på", size, "c09-k")]
    yy = y + lead + 3
    for st, name, sub in people:
        if st == "done":
            out.append(ic_check(x + 1, yy - 4))
        elif st == "ki":
            out.append(ki_tag(x - 1, yy, OR if True else CY, INK, 10))
        else:
            out.append(ic_wait(x + 1, yy - 4, INK, .8))
        out.append(T(x + 17, yy, name, size, "c09-k" if st in ("wait", "you", "ki") else "c09-m"))
        out.append(T(x + 17, yy + lead - 1, sub, size, "c09-b"))
        yy += lead * 2 + 1
    return "".join(out), yy


def default_people(jonas="3 min"):
    return [
        ("done", "Ida", "Detaljist"),
        ("done", "Mikkel", "Distributør"),
        ("wait", "Jonas " + jonas, "Fabrikk"),
        ("you", "Sara, deg", "Grossist"),
    ]


def game(doc, week, role="Grossist", typed=None, confirmed=None, shipments=None, hl=(), people=None,
         stroke_digit=True, ordliste=True, spill=17, slab=True, who="Grossist"):
    """Spillskjermen i 390x844. Blekket velges av tilstanden: restordre gir cyan, ellers oransje."""
    s = seat(week, role)
    debt = s["restordre"] > 0
    ch = CYAN if debt else ORANGE
    g, c = ch["g"], ch["c"]
    pv = s["paa_vei_foer_ordre"]
    out = [R(0, 0, 390, 844, g)]

    # Hode
    out.append(A(16, 50, f"UKE {week}", 34))
    out.append(T(374, 30, f"{role}, Spill {spill}", 14, "c09-k", anchor="end"))
    out.append(T(374, 49, f"Totalkostnad {kr(s['kost_sum'])} kr", 14, "c09-m c09-tn", anchor="end"))
    out.append(T(16, 70, "Demodata", 13, "c09-b"))

    # Plakaten, vinklet 11 grader. Sifrene er motblekk med overtrykk-kontur.
    big = s["restordre"] if debt else s["lager"]
    word = "RESTORDRE" if debt else "LAGER"
    small = f"LAGER {s['lager']}" if debt else f"RESTORDRE {s['restordre']}"
    digit_size = 206 if big < 100 else 170
    poster = (
        A(0, 0, big, digit_size, c, stroke=INK, sw=9)
        + A(4, 60, word, 57, INK)
        + A(4, 104, small, 38, INK)
    )
    out.append(G(poster, 38, 306, rot=ANG))

    # 16 PÅ VEI: tellende blokker
    ships = shipments or ([s["neste_levering"], pv - s["neste_levering"]] if pv > s["neste_levering"] else [pv])
    ghost = typed if typed and not confirmed else 0
    all_ships = list(ships) + ([confirmed] if confirmed else [])
    blocks, top = stack(296, 402, all_ships, ghost, ch)
    out.append(blocks)
    if ghost:
        ghost_rows = (ghost + 1) // 2
        gy = top + (ghost_rows * 16.5) / 2 - 16
        out.append(R(308, gy, 54, 32, PAPER))
        out.append(A(335, gy + 28, f"+{ghost}", 28, anchor="middle"))
    label_total = pv + (confirmed or 0)
    out.append(A(296, 436, f"{label_total} PÅ VEI", 26))

    # Fire datatall
    cells = [
        ("inn", "Innkommende ordre", s["innkommende_ordre"], 16, 428),
        ("lev", "Levering", s["levering"], 160, 428),
        ("sendt", "Sendt", s["sendt"], 16, 486),
        ("neste", "Neste levering", s["neste_levering"], 160, 486),
    ]
    for key, lab, val, x, y in cells:
        if key in hl:
            out.append(R(x - 6, y - 15, 134 if key in ("inn", "sendt") else 124, 56, INK))
            out.append(T(x, y, lab, 13, "c09-k", c if c == CY else OR))
            out.append(A(x, y + 35, val, 32, c))
        else:
            out.append(T(x, y, lab, 13, "c09-m"))
            out.append(A(x, y + 35, val, 32, INK))

    # Ordrehistorikk
    hist = history(week, role)[-10:]
    first = week - len(hist)
    out.append(T(16, 554, f"Dine ordrer, uke {first}–{week-1}", 13, "c09-m"))
    for i, v in enumerate(hist):
        out.append(T(24 + i * 25.4, 574, v, 15, "c09-k c09-tn", anchor="middle"))
    out.append(L(16, 581, 272, 581, INK, 1.5))

    # Ordre
    if confirmed:
        out.append(T(16, 601, "Din Ordre, kan ikke endres", 13, "c09-k"))
        out.append(A(16, 696, confirmed, 92, INK))
        out.append(ic_lock(112, 636, INK, 1.1))
        out.append(P(132, 641, "Bekreftet", 15, 130, cls="c09-k"))
        out.append(P(112, 664, "Uka går når alle har bestilt.", 13, 150, 17))
    else:
        out.append(T(16, 601, "Din Ordre. Stryk, eller tast.", 13, "c09-k"))
        out.append(R(16, 608, 170, 108, PAPER, INK, 2.5))
        if typed:
            out.append(A(101, 700, typed, 92, INK, "middle"))
            out.append(R(160, 628, 3, 68, INK))
        else:
            out.append(A(101, 700, "0", 92, INK, "middle"))
        out.append(R(194, 608, 78, 52, c, INK, 2.5))
        out.append(ic_up(233, 634, INK))
        out.append(R(194, 664, 78, 52, c, INK, 2.5))
        out.append(ic_down(233, 690, INK))

    # Marginspalten
    ppl = people if people is not None else default_people()
    if confirmed:
        ppl = [("done", "Ida", "Detaljist"), ("done", "Mikkel", "Distributør"),
               ("wait", "Jonas 3 min", "Fabrikk"), ("done", "Sara, deg", "Grossist")]
    m, yy = margin_waiting(290, 462, ppl)
    out.append(m)
    if ordliste:
        yy += 2
        for term in ("På vei", "Restordre", "Forsinkelse"):
            out.append(T(290, yy, term, 13, "c09-m c09-u"))
            yy += 19

    # Bekreft: et vinklet slag i overtrykk
    if slab:
        out.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
        if confirmed:
            out.append(A(196, 806, "VENTER PÅ JONAS", 44, c, "middle", ANG))
        elif typed:
            out.append(A(196, 808, f"BEKREFT {typed}", 56, c, "middle", ANG))
        else:
            out.append(A(196, 808, "BEKREFT", 56, c, "middle", ANG))
    return "".join(out)
