"""Konsept 07 Pikselfabrikken. Arbeidsnavn: Pikselkjeden.

Genererer 9 SVG-filer fra ../_shared/fixture.json. Alle piksler ligger på heltallsrutenett.
Telefonen tegnes på et 4 px-rutenett, slik at skala 0,75 gir nøyaktig 3 px og skala 1,5 gir 6 px.
Kjør: uv run python build.py
"""
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
F = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
CHAIN = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]  # varene går fra venstre mot høyre
WEEKS = F["weeks"]
GAMES = F["class_games"]


def seat(week, role="Grossist"):
    return WEEKS[week - 1]["seats"][role]


def kr(v):
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return s


# --- Palett -----------------------------------------------------------------------------------
PLUM = "#33143F"   # dyp plomme
PLUM2 = "#55316A"  # lys plomme, samme kulør: paneler og bånd
TINT = "#D9C9E0"   # plomme blandet i hvitt: sekundær tekst på plomme
WHITE = "#FFF9EF"  # varm hvit
WHITE2 = "#F3E8D8"  # hvit i skygge: rader og lerret
YEL = "#FFC738"    # varm gul
CY = "#8BE6EA"     # lys cyan
COR = "#FF6B5B"    # koral
PAL = {"P": PLUM, "L": PLUM2, "W": WHITE, "Y": YEL, "C": CY, "O": COR, "T": TINT}

FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;600"
         "&amp;family=Jersey+25&amp;display=swap');")
CSS = FONTS + """
.c07-b{font-family:'Rubik',Verdana,'Segoe UI',sans-serif;font-weight:400}
.c07-bb{font-family:'Rubik',Verdana,'Segoe UI',sans-serif;font-weight:600}
.c07-p,.c07-pb,.c07-s,.c07-sb{font-family:'Jersey 25','Lucida Console','Courier New',monospace;font-weight:400;font-variant-ligatures:none}
.c07-px{shape-rendering:crispEdges}
"""
# Bredde per tegn i em. Jersey tegnes 1,2 ganger oppgitt størrelse, se T().
WID = {"b": .53, "bb": .56, "p": .55, "pb": .55, "s": .62, "sb": .62}


# --- Grunnprimitiver --------------------------------------------------------------------------
def R(x, y, w, h, fill):
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}"/>'


def G(*parts, tr=None, cls="c07-px", extra=""):
    t = f' transform="{tr}"' if tr else ""
    c = f' class="{cls}"' if cls else ""
    return f"<g{c}{t}{extra}>" + "".join(parts) + "</g>"


def T(x, y, s, f="b", sz=13, fill=PLUM, a=None, extra=""):
    if f in ("p", "pb"):
        sz = round(sz * 1.2)  # Jersey er liten på kornet
    elif f in ("s", "sb"):
        sz = round(sz * 1.4)  # tall: større grad, slik at sifferhøyden blir 7/8 av oppgitt størrelse
    anchor = f' text-anchor="{a}"' if a else ""
    return (f'<text x="{x:g}" y="{y:g}" class="c07-{f}" font-size="{sz:g}" fill="{fill}"{anchor}{extra}>'
            f"{escape(str(s))}</text>")


def tw(s, f="b", sz=13):
    return len(str(s)) * WID[f] * sz


def wrap(s, maxw, f="b", sz=13):
    lines, cur = [], ""
    for word in str(s).split():
        test = (cur + " " + word).strip()
        if tw(test, f, sz) > maxw and cur:
            lines.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def para(x, y, s, maxw, f="b", sz=13, lh=None, fill=PLUM, a=None):
    lh = lh or round(sz * 1.35)
    return "".join(T(x, y + i * lh, line, f, sz, fill, a) for i, line in enumerate(wrap(s, maxw, f, sz)))


def plines(s, maxw, f="b", sz=13):
    return len(wrap(s, maxw, f, sz))


def box(x, y, w, h, fill, n=4):
    """Rektangel med trappede hjørner."""
    return R(x + n, y, w - 2 * n, h, fill) + R(x, y + n, w, h - 2 * n, fill)


def frame(x, y, w, h, col, t=4, n=4):
    return (R(x + n, y, w - 2 * n, t, col) + R(x + n, y + h - t, w - 2 * n, t, col)
            + R(x, y + n, t, h - 2 * n, col) + R(x + w - t, y + n, t, h - 2 * n, col))


def circle(cx, cy, r, p, fill):
    """Pikselsirkel på rutenett med sidelengde p."""
    out = []
    n = int(r // p)
    for j in range(-n, n):
        yc = (j + .5) * p
        half = int(math.sqrt(max(r * r - yc * yc, 0)) // p)
        if half:
            out.append(R(cx - half * p, cy + j * p, 2 * half * p, p, fill))
    return "".join(out)


def sprite(x, y, rows, p=4, remap=None):
    """Tegner et bitmap-mønster. Horisontale løp slås sammen til én rect."""
    pal = dict(PAL)
    if remap:
        pal.update({k: PAL.get(v, v) for k, v in remap.items()})
    out = []
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            ch = row[i]
            if ch == ".":
                i += 1
                continue
            k = i
            while k < len(row) and row[k] == ch:
                k += 1
            out.append(R(x + i * p, y + j * p, (k - i) * p, p, pal[ch]))
            i = k
    return "".join(out)


def sw(rows, p=4):
    return len(rows[0]) * p


def sh(rows, p=4):
    return len(rows) * p


# --- Sprites: egentegnet, eget univers --------------------------------------------------------
CRATE = ["WWW", "YYY", "YYY"]
GHOST = ["CCC", "C.C", "CCC"]
PACKET = ["OOWOO", "OOWOO", "OOWOO", "OOOOO", "OOWOO"]
CHECK = ["......C", ".....CC", "C...CC.", "CC.CC..", ".CCC...", "..C...."]
HOUR = ["YYYYY", ".Y.Y.", ".YYY.", "..Y..", ".Y.Y.", ".YYY.", "YYYYY"]
PAUSE = ["CC.CC", "CC.CC", "CC.CC", "CC.CC", "CC.CC", "CC.CC"]
LOCK = ["..PPP..", ".P...P.", ".P...P.", "PPPPPPP", "PPP.PPP", "PPP.PPP", "PPPPPPP"]
ROBOT = ["....C....", "....C....", ".CCCCCCC.", "CCPPCPPCC", "CCCCCCCCC", "CCPCPCPCC", ".CCCCCCC.", "..C...C.."]
PERSON = ["..YYY..", ".YYYYY.", "..WWW..", "..WWW..", ".CCCCC.", "C.CCC.C", "..CCC..", "..C.C.."]
PERSON_OUT = ["..TTT..", ".TTTTT.", "..TTT..", "..TTT..", ".TTTTT.", "T.TTT.T", "..TTT..", "..T.T.."]
ARROW_R = ["....W..", "....WW.", "WWWWWWW", "....WW.", "....W.."]
ARROW_L = ["..W....", ".WW....", "WWWWWWW", ".WW....", "..W...."]
TRI_UP = ["..Y..", ".YYY.", "YYYYY"]
TRI_DN = ["YYYYY", ".YYY.", "..Y.."]
REW = ["...W...W", "..WW..WW", ".WWW.WWW", "WWWWWWWW", ".WWW.WWW", "..WW..WW", "...W...W"]
SKIP = ["W...W.W", "WW..W.W", "WWW.W.W", "WWWWW.W", "WWW.W.W", "WW..W.W", "W...W.W"]
CROSS = ["O...O", ".O.O.", "..O..", ".O.O.", "O...O"]
SLIP = ["WWWWW", "WPPPW", "WWWWW", "WPPWW", "WWWWW"]
FILE = ["WWWWW..", "WPPPWW.", "WWWWWWW", "WPPPPPW", "WWWWWWW", "WPPPPPW", "WWWWWWW", "WPPPPPW", "WWWWWWW"]
MAIL = ["WWWWWWWWW", "WPWWWWWPW", "WWPWWWPWW", "WWWPPPWWW", "WWWWWWWWW", "WWWWWWWWW"]
TAPE = ["WWWWWWWWWWWWW", "WPPPPPPPPPPPW", "WPWWWPPPWWWPW", "WPWPWPPPWPWPW", "WPWWWPPPWWWPW", "WPPPPPPPPPPPW",
        "WWWWWWWWWWWWW"]
QUEST = ["PPPPP", ".YYY.", "Y...Y", "...Y.", "..Y..", ".....", "..Y.."]
DOC = ["WWWWWWW", "WPPPPPW", "WWWWWWW", "WPPPWWW", "WWWWWWW", "WPPPPPW", "WWWWWWW", "WYYYYYW", "WWWWWWW"]
CHECKLIST = ["WWWWWWWWW", "WPWWPPPPW", "WWWWWWWWW", "WPWWPPPPW", "WWWWWWWWW", "WPWWPPPPW", "WWWWWWWWW", "WPWWPPWWW", "WWWWWWWWW"]
BAR_CH = ["PPPPPPP", "P.....P", "P.PPP.P", "P.P.P.P", "PPPPPPP"]

FABRIKK = ["........WW.", ".......WWW.", ".Y..Y..YY..", "YY.YY..YY..", "YYYYYYYYYYY", "YPPYPPYPPYY", "YPPYPPYPPYY",
           "YYYYYYYYYYY", "YYYYYYYYYYY"]
DISTRIB = ["CCCCCCCC.....", "CCCCCCCC.YYY.", "CCCCCCCC.YWWY", "CCCCCCCC.YWWY", "CCCCCCCCCYYYY", "CCCCCCCCCYYYY",
           "CCCCCCCCCYYYY", ".WW.....WW...", ".WW.....WW..."]
GROSSIST = [".....Y.....", "...YYYYY...", ".YYYYYYYYY.", "YYYYYYYYYYY", "YWWWWWWWWWY", "YWPPPPPPPWY", "YWPCCPCCPWY",
            "YWPCCPCCPWY", "YWPPPPPPPWY"]
DETALJ = ["OWOWOWOWOWO", "OWOWOWOWOWO", "OWOWOWOWOWO", "WWWWWWWWWWW", "WCCCWPPPWCW", "WCCCWPPPWCW", "WCCCWPYPWCW",
          "WWWWWPPPWWW", "WWWWWPPPWWW"]
ROLE_SP = {"Fabrikk": FABRIKK, "Distributør": DISTRIB, "Grossist": GROSSIST, "Detaljist": DETALJ}
# I lys variant (gul eller hvit bakgrunn) byttes lyse flater til plomme
ON_LIGHT = {"Y": "P", "W": "L", "C": "P", "P": "W"}
ON_LIGHT2 = {"Y": "P", "W": "T", "C": "L", "P": "W", "O": "O"}


# --- SVG-skall --------------------------------------------------------------------------------
def write_svg(name, w, h, title, desc, body, bg=WHITE2):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f"font-family=\"Rubik, Verdana, sans-serif\">"
           f"<title>{escape(title)}</title><desc>{escape(desc)}</desc><style>{CSS}</style>"
           f'<rect class="c07-px" width="{w}" height="{h}" fill="{bg}"/>{body}</svg>').replace('<g class="c07-px"></g>', "")
    (HERE / f"{name}.svg").write_text(svg, encoding="utf-8")


def demodata(x, y, fill=PLUM, a="start", sz=13):
    return T(x, y, "Demodata", "bb", sz, fill, a)


def btn(x, y, w, h, label, kind="pri", sz=16, f="pb"):
    """Pikselknapp. pri gul, sek plommeramme, dan koral, mork plomme med hvit tekst."""
    fg, parts = PLUM, []
    if kind == "pri":
        parts = [box(x, y, w, h, YEL), R(x + 4, y + h - 4, w - 8, 4, PLUM)]
    elif kind == "dan":
        parts = [box(x, y, w, h, COR), R(x + 4, y + h - 4, w - 8, 4, PLUM)]
    elif kind == "cy":
        parts = [box(x, y, w, h, CY), R(x + 4, y + h - 4, w - 8, 4, PLUM)]
    elif kind == "sek":
        parts = [box(x, y, w, h, WHITE), frame(x, y, w, h, PLUM)]
    elif kind == "mork":
        parts = [box(x, y, w, h, PLUM)]
        fg = WHITE
    return G(*parts) + T(x + w / 2, y + h / 2 + sz * .35, label, f, sz, fg, "middle")


def pframe(body, x, y, s=1, w=390, h=844, top=YEL):
    """Enkel telefonramme på rutenettet: trappede hjørner og tynn kant. Ingen merkevare."""
    tr = f"translate({x:g},{y:g}) scale({s:g})" if s != 1 else f"translate({x:g},{y:g})"
    return G(
        G(box(-8, -8, w + 16, h + 16, PLUM, 8), box(0, 0, w, h, top, 4)),
        body, tr=tr, cls=None)


# --- Spillflaten: scene, tallrad, historikk, kontrollflate ------------------------------------
def people(mode="c"):
    """De fire setene i kjederekkefølge, ut fra Uke 11-situasjonen."""
    base = [
        dict(name="Jonas", role="Fabrikk", stat="Venter 3 min", kind="wait"),
        dict(name="Mikkel", role="Distributør", stat="Har bestilt", kind="done"),
        dict(name="Sara (deg)", role="Grossist", stat="Venter på deg", kind="you"),
        dict(name="Ida", role="Detaljist", stat="Har bestilt", kind="done"),
    ]
    if mode == "sent":
        base[2].update(stat="Har bestilt", kind="youdone")
    if mode == "alldone":
        base[0].update(stat="Har bestilt", kind="done")
        base[2].update(stat="Har bestilt", kind="youdone")
    if mode == "open":
        for b in base:
            b.update(stat="Bestiller", kind="open")
        base[2].update(stat="Venter på deg", kind="you")
    if mode == "pause":
        base[0].update(stat="Pause", kind="pause")
    if mode == "ki":
        base[0].update(name="KI-spiller", stat="Jonas borte", kind="ki")
    return base


def seat_window(x, y, p, w=84):
    k = p["kind"]
    parts = [box(x, y, w, 48, PLUM2)]
    if k in ("you", "youdone"):
        parts.append(frame(x, y, w, 48, WHITE))
    if k == "ki":
        parts.append(frame(x, y, w, 48, CY))
        parts.append(sprite(x + 24, y + 8, ROBOT))
    else:
        parts.append(sprite(x + 8, y + 8, PERSON_OUT if k == "pause" else PERSON))
        if k in ("done", "youdone"):
            parts.append(sprite(x + 44, y + 12, CHECK))
        elif k in ("wait", "you"):
            parts.append(sprite(x + 50, y + 10, HOUR))
        elif k == "pause":
            parts.append(sprite(x + 50, y + 12, PAUSE))
    txt = T(x, y + 64, p["name"], "bb", 13, CY if k == "ki" else WHITE)
    txt += T(x, y + 80, p["role"], "b", 13, TINT)
    col = {"wait": YEL, "you": YEL, "done": CY, "youdone": CY, "ki": CY, "pause": CY}.get(k, TINT)
    txt += T(x, y + 96, p["stat"], "b", 13, col)
    return G(*parts) + txt


def stack(x, base, n, rows=CRATE, cols=4, p=4):
    """Kasser i rader. Nederste rad står på y = base."""
    out = []
    pitch = (len(rows[0]) + 1) * p
    h = len(rows) * p
    for i in range(n):
        c, r = i % cols, i // cols
        out.append(sprite(x + c * pitch, base - h - r * pitch, rows, p))
    return "".join(out)


def belt_strip(x, y, w):
    parts = [R(x, y, w, 16, PLUM2), R(x, y, w, 4, TINT)]
    for i in range(0, w, 16):
        parts.append(R(x + i + 4, y + 8, 8, 4, PLUM))
    return "".join(parts)


def shelf(x, y, lager, extra_new=0):
    """Hylle med plass til 12 kasser, fylt nedenfra. Tomme plasser vises som svake ruter."""
    parts = [R(x, y, 4, 132, TINT), R(x + 72, y, 4, 132, TINT)]
    for j in range(3):
        parts.append(R(x, y + 40 + j * 44, 76, 4, TINT))
        for i in range(4):
            idx = (2 - j) * 4 + i
            cx, cy = x + 6 + i * 16, y + 28 + j * 44
            if idx < min(lager, 12) + extra_new:
                parts.append(sprite(cx, cy, CRATE))
            else:
                parts.append(R(cx, cy, 12, 12, PLUM2))
    return "".join(parts)


def scene(st):
    """Skjermen, øvre halvdel. Koordinater i telefonens 390-skala, y 44 til 428."""
    o = [G(box(12, 44, 366, 384, PLUM))]
    for i, p in enumerate(st["people"]):
        o.append(seat_window(16 + i * 90, 52, p))
    o.append(T(16, 172, "Fra Distributør, om de har kasser", "b", 13, TINT))
    o.append(T(298, 172, "Lager", "bb", 13, WHITE))
    o.append(T(374, 172, st["lager"], "sb", 16, COR if st["lager"] == 0 and not st.get("newshelf") else WHITE, "end"))

    base = 296
    belt = [belt_strip(12, base, 288)]
    shift = st.get("shift", 0)
    stacks = []
    for i, (wk, n) in enumerate(st["segs"]):
        x = 16 + i * 68
        stacks.append(stack(x, base, n))
        if st.get("ghost") and i == 0:
            stacks.append(stack(x, base, st["ghost"], GHOST))
    moving = "".join(stacks)
    if st.get("animate"):
        moving = (f'<g><animateTransform attributeName="transform" type="translate" dur="6s" '
                  f'repeatCount="indefinite" values="{shift} 0;{shift} 0;68 0;0 0;{shift} 0" '
                  f'keyTimes="0;.72;.86;.86;1"/>{moving}</g>')
    elif shift:
        moving = f'<g transform="translate({shift},0)">{moving}</g>'
    o.append(G(*belt, moving))
    o.append(G(shelf(298, 180, st["lager"], st.get("newshelf", 0))))

    if st.get("segcount", True):
        for i, (wk, n) in enumerate(st["segs"]):
            x = 16 + i * 68
            label, col = str(n), WHITE
            if st.get("ghost") and i == 0:
                label, col = f"+{st['ghost']}", CY
            o.append(T(x, 332, label, "sb", 16, col))
            o.append(T(x, 349, f"Uke {wk}", "b", 13, TINT))
    o.append(T(16, 370, st["line"], "bb", 13, st.get("linecol", CY)))
    # Restordre
    o.append(T(16, 390, "Restordre", "bb", 13, COR))
    o.append(T(16, 422, st["rest"], "sb", 24, COR))
    pk = []
    for i in range(min(st["rest"], 24)):
        c, r = i % 12, i // 12
        pk.append(sprite(88 + c * 24, 378 + r * 24, PACKET))
    o.append(G(*pk))
    return "".join(o)


def numbers(st, y0=434):
    cells = [("Lager", st["lager"]), ("Restordre", st["rest"]), ("Ordre inn", st["inn"]), ("Levering", st["lev"]),
             ("Sendt", st["sendt"]), ("På vei", st["paavei"]), ("Kost, kr", st["kost"]), ("Uke", st["week"])]
    o = []
    for i, (lab, val) in enumerate(cells):
        c, r = i % 4, i // 4
        x, y = 16 + c * 91, y0 + r * 52
        o.append(T(x, y + 15, lab, "bb", 13, PLUM))
        o.append(T(x, y + 43, val, "sb", 24, PLUM))
    return G(R(12, y0 + 49, 366, 2, PLUM)) + "".join(o)


def history(st, y0=542):
    o = [T(16, y0 + 14, "Dine ordre", "bb", 13)]
    o.append(T(374, y0 + 14, "Uke 1–4 var veiledet" if st["week"] < 13 else "", "b", 13, PLUM, "end"))
    hist = st["hist"]
    start = max(0, len(hist) - 10)
    for k, i in enumerate(range(start, len(hist))):
        x = 16 + k * 32
        o.append(T(x + 13, y0 + 33, i + 1, "b", 13, PLUM, "middle"))
        o.append(T(x + 13, y0 + 53, hist[i], "pb", 18, PLUM, "middle"))
    x = 16 + (len(hist) - start) * 32
    if st.get("typed") is not None:
        o.append(T(x + 16, y0 + 33, st["week"], "bb", 13, PLUM, "middle"))
        o.append(G(box(x - 2, y0 + 37, 38, 22, PLUM)))
        o.append(T(x + 17, y0 + 54, st["typed"], "pb", 18, WHITE, "middle"))
    return "".join(o)


def wheel(x, y, d, locked=False):
    h = 160
    parts = [box(x, y, 64, h, PLUM), box(x + 4, y + 52, 56, 56, WHITE)]
    if not locked:
        parts.append(sprite(x + 22, y + 8, TRI_UP))
        parts.append(sprite(x + 22, y + 140, TRI_DN))
    o = [G(*parts)]
    if not locked:
        o.append(T(x + 32, y + 43, (d + 9) % 10, "s", 16, TINT, "middle"))
        o.append(T(x + 32, y + 131, (d + 1) % 10, "s", 16, TINT, "middle"))
    o.append(T(x + 32, y + 101, d, "sb", 48, PLUM, "middle"))
    return "".join(o)


def console(st, y0=612):
    v = st.get("typed") or 0
    digits = [v // 100 % 10, v // 10 % 10, v % 10]
    locked = st.get("locked")
    label = f"Din ordre, Uke {st['week']}" if not locked else f"Din ordre, Uke {st['week']}, er sendt"
    o = [T(16, y0 + 14, label, "bb", 13)]
    wy = y0 + 24
    for i, d in enumerate(digits):
        o.append(wheel(16 + i * 68, wy, d, locked))
    cx, cy = 296, wy + 80
    if locked:
        o.append(G(circle(cx, cy, 68, 4, PLUM), sprite(cx - 14, cy - 32, CHECK)))
        o.append(T(cx, cy + 26, "SENDT", "sb", 24, WHITE, "middle"))
    else:
        o.append(G(circle(cx, cy, 72, 4, PLUM), circle(cx, cy, 64, 4, COR)))
        o.append(T(cx, cy + 6, "BESTILL", "sb", 24, PLUM, "middle"))
        o.append(T(cx, cy + 28, f"{v} kasser", "bb", 13, PLUM, "middle"))
    note = st.get("note", "Kan ikke endres etter at du har bestilt.")
    o.append(T(16, wy + 178, note, "b", 13))
    if st.get("note2"):
        o.append(T(16, wy + 195, st["note2"], "bb", 13))
    return "".join(o)


def head(st):
    o = [G(sprite(14, 6, GROSSIST, 3, ON_LIGHT))]
    o.append(T(56, 21, "Sara, Grossist", "bb", 16))
    o.append(T(56, 38, "Spill 17", "b", 13))
    o.append(demodata(374, 21, PLUM, "end"))
    return "".join(o)


def state11(**kw):
    s = seat(11)
    st = dict(week=11, lager=s["lager"], rest=s["restordre"], inn=s["innkommende_ordre"], lev=s["levering"],
              sendt=s["sendt"], paavei=s["paa_vei_foer_ordre"], kost=kr(s["kost_sum"]),
              segs=[(15, 0), (14, 8), (13, 4), (12, 4)], ghost=24, typed=24,
              hist=[seat(w)["ordre"] for w in range(1, 11)],
              people=people(), line=f"På vei {s['paa_vei_foer_ordre']} + 24 = 40. Neste levering {s['neste_levering']}.")
    st.update(kw)
    return st


def state12(**kw):
    s = seat(12)
    st = dict(week=12, lager=s["lager"], rest=s["restordre"], inn=s["innkommende_ordre"], lev=s["levering"],
              sendt=s["sendt"], paavei=s["paa_vei_foer_ordre"], kost=kr(s["kost_sum"]),
              segs=[(16, 0), (15, 24), (14, 8), (13, 4)], ghost=None, typed=None,
              hist=[seat(w)["ordre"] for w in range(1, 12)],
              people=people("open"), line=f"På vei {s['paa_vei_foer_ordre']}. Neste levering {s['neste_levering']}.")
    st.update(kw)
    return st


def phone_game(st):
    return head(st) + scene(st) + numbers(st) + history(st) + console(st)


# --- Tastetrykk for storyboard ----------------------------------------------------------------
def phone_tick():
    """D: overgangen. Scene midt i flytting, og tydelig hopp-knapp."""
    st = state12(people=people("alldone"), shift=34, animate=True, segcount=False,
                 line="Båndet flytter seg ett felt mot Lager.", linecol=WHITE)
    st["segs"] = [(15, 24), (14, 8), (13, 4), (12, 4)]
    o = [head(st), scene(st), numbers(state12(typed=None))]
    y = 542
    o.append(T(195, y + 54, "UKE 12", "sb", 48, PLUM, "middle"))
    o.append(T(195, y + 80, "4 kasser inn. 11 nye i ordre fra Detaljist.", "b", 13, PLUM, "middle"))
    o.append(G(R(39, y + 96, 312, 16, PLUM), R(43, y + 100, 196, 8, YEL)))
    o.append(T(195, y + 132, "Tar under 2 sekunder", "b", 13, PLUM, "middle"))
    o.append(btn(87, y + 146, 216, 56, "Hopp over", "mork", 24))
    o.append(T(195, y + 226, "Trykk hvor som helst for å hoppe over.", "b", 13, PLUM, "middle"))
    return "".join(o)


def phone_ki():
    st = state11(people=people("ki"), ghost=None, typed=None, line="På vei 16. Neste levering 4.", linecol=CY)
    o = [head(st), scene(st), numbers(st)]
    y = 542
    o.append(G(box(12, y, 366, 76, PLUM), sprite(24, y + 14, PAUSE)))
    o.append(T(60, y + 24, "Sara satte Pause: fortsetter to. 14:15", "b", 13, WHITE))
    o.append(T(60, y + 43, "Jonas kom ikke. Da kan en annen i", "b", 13, TINT))
    o.append(T(60, y + 61, "gruppa sette inn KI-spiller.", "b", 13, TINT))
    y2 = y + 84
    o.append(G(box(12, y2, 366, 76, PLUM), frame(12, y2, 366, 76, CY), sprite(24, y2 + 22, ROBOT)))
    o.append(T(76, y2 + 24, "KI-spiller har Fabrikk fra nå", "bb", 13, CY))
    o.append(T(76, y2 + 43, "Merket i alle Uker den spiller.", "b", 13, WHITE))
    o.append(T(76, y2 + 61, "Spillet går videre uten Jonas.", "b", 13, WHITE))
    y3 = y2 + 92
    o.append(T(16, y3 + 8, "Slik ser Jonas det på sin telefon:", "bb", 13))
    o.append(T(16, y3 + 27, "KI-spiller holder setet ditt. Gjelder fra neste Uke:", "b", 13))
    o.append(btn(16, y3 + 36, 358, 48, "Ta tilbake setet", "mork", 20))
    return "".join(o)


def phone_end():
    """F: kjedens totalkostnad først, så per Rolle, ikke per navn og ingen rekkefølge etter kostnad."""
    o = [G(box(0, 0, 390, 844, PLUM, 4))]
    o.append(demodata(370, 28, WHITE, "end"))
    o.append(T(20, 70, "Spillet er ferdig", "pb", 32, WHITE))
    o.append(T(20, 98, "Båndene har stoppet.", "b", 16, TINT))
    o.append(T(20, 160, "Hele kjeden, totalkostnad", "bb", 16, YEL))
    o.append(T(20, 216, kr(F["chain_total_cost"]) + " kr", "sb", 48, YEL))
    o.append(T(20, 244, "Dere bar denne kostnaden sammen.", "b", 16, WHITE))
    o.append(G(R(20, 264, 350, 4, PLUM2)))
    o.append(T(20, 296, "Per Rolle", "bb", 16, WHITE))
    y = 310
    mx = max(F["total_cost_per_role"].values())
    for i, r in enumerate(CHAIN):
        cost = F["total_cost_per_role"][r]
        o.append(G(sprite(20, y + i * 76 + 4, ROLE_SP[r], 4)))
        o.append(T(84, y + i * 76 + 18, r, "bb", 16, WHITE))
        o.append(T(370, y + i * 76 + 18, kr(cost) + " kr", "bb", 16, WHITE, "end"))
        w = int(round(cost / mx * 284 / 4)) * 4
        o.append(G(R(84, y + i * 76 + 30, 284, 12, PLUM2), R(84, y + i * 76 + 30, w, 12, CY)))
    o.append(T(20, 646, "Kost er ikke poeng. Ingen rangering, ingen", "b", 16, TINT))
    o.append(T(20, 668, "vinner. Nå ser dere hvorfor det ble slik.", "b", 16, TINT))
    o.append(btn(20, 700, 350, 68, "Videre til Debrief", "pri", 24))
    return "".join(o)


# =================================== 05 SPILL =================================================
def build_05():
    o = []
    o.append(T(60, 54, "Uke 11: Sara har tastet 24 og ser dem stå på båndet", "pb", 32, PLUM))
    st = state11()
    o.append(pframe(phone_game(st), 60, 112))

    # Laptop: scene i skala 1,5 (6 px-rutenett), konsoll i skala 1
    lx, ly, lw, lh = 540, 112, 1000, 650
    lap = [G(box(lx - 12, ly - 12, lw + 24, lh + 24, PLUM, 8), box(lx, ly, lw, lh, YEL, 4),
             R(lx - 44, ly + lh + 12, lw + 88, 16, PLUM2), R(lx + lw // 2 - 72, ly + lh + 12, 144, 8, PLUM))]
    lap.append(G(sprite(lx + 16, ly + 8, GROSSIST, 3, ON_LIGHT)))
    lap.append(T(lx + 60, ly + 24, "Sara, Grossist", "bb", 16))
    lap.append(T(lx + 60, ly + 42, "Spill 17", "b", 13))
    lap.append(demodata(lx + lw - 16, ly + 26, PLUM, "end"))
    lap.append(G(scene(st), tr=f"translate({lx - 8},{ly + 52 - 66}) scale(1.5)", cls=None))
    rx = lx + 582
    lap.append(G(numbers(st), tr=f"translate({rx},{ly + 60 - 434})", cls=None))
    lap.append(G(history(st), tr=f"translate({rx},{ly + 176 - 542})", cls=None))
    lap.append(G(console(st), tr=f"translate({rx},{ly + 256 - 612})", cls=None))
    lap.append(T(rx + 16, ly + 512 + 18, "På tastatur: skriv tallet, trykk Enter.", "bb", 14))
    lap.append(T(rx + 16, ly + 512 + 38, "Piltaster ruller hjulene.", "b", 14))
    o += lap

    # Merknader under laptopen
    nx = 540
    notes = [
        ("16 kasser er 16 ruter",
         "Båndet har ett felt per ankomstuke: 4, 4 og 8. Tell dem, så stemmer tallet På vei."),
        ("24 står der før du bestiller",
         "Hule kasser viser ordren du har tastet. Du ser hva den gjør med båndet, og hjulene er fortsatt åpne."),
        ("Ett blikk, så en beslutning",
         "Tallraden viser alt i klartekst. Hjul og BESTILL ligger under tommelen, og alt får plass på 360 px."),
    ]
    for i, (h, b) in enumerate(notes):
        x = nx + i * 340
        o.append(T(x, 826, h, "pb", 20))
        o.append(para(x, 852, b, 315, "b", 16, 22))
    return write_svg("05-spill", 1600, 1000, "Spillskjermen, Uke 11",
                     "Sara på telefon og laptop midt i Uke 11. Pikselscene med bånd der 16 kasser er på vei, "
                     "24 hule kasser for ordren hun har tastet, tom hylle og 13 restordrepakker. "
                     "Under: tallrad, ordrehistorikk, tre sifferhjul og BESTILL.", "".join(o))


# =================================== 06 SPILLDYNAMIKK =========================================
def build_06():
    o = [T(28, 48, "En Uke i Pikselkjeden: fra levering til neste beslutning", "pb", 32)]
    s = .75
    pitch = 350
    px0 = 36

    # A
    a = state11(ghost=None, typed=None, people=people("open"), newshelf=4, line="Restordre 9 + 8 inn − 4 sendt = 13",
                note="Du har ikke bestilt ennå. Hjulene står på 0.", linecol=WHITE)
    a["segs"] = [(15, 0), (14, 8), (13, 4), (12, 4)]
    frame_a = phone_game(a)
    # B
    b = state11()
    frame_b = phone_game(b)
    # C
    c = state11(ghost=None, typed=24, locked=True, people=people("sent"),
                line="På vei 40. 24 er nye. Ordren er på vei til Distributør.",
                note="Ordren kan ikke endres.", note2="Venter på Jonas, Fabrikk, i 3 min.")
    c["segs"] = [(15, 24), (14, 8), (13, 4), (12, 4)]
    c["paavei"] = 40
    frame_c = phone_game(c)

    frames = [frame_a, frame_b, frame_c, phone_tick(), phone_ki(), phone_end()]
    tops = [YEL, YEL, YEL, YEL, YEL, PLUM]
    heads = ["A  Uka åpner", "B  Beslutningen", "C  Bekreftet", "D  Uka går videre", "E  Jonas er borte",
             "F  Spillet slutter"]
    texts = [
        "4 kasser ruller opp på hylla og går rett ut igjen. 8 nye pakker kommer i køen. Regnestykket står der, du trenger ikke gjøre det.",
        "Du taster 24 og ser 24 hule kasser tårne seg opp over de 16 som allerede er på vei. Bestem deg, eller rull hjulet ned.",
        "Kassene blir faste og hjulene låses. Vinduene viser at Jonas er den eneste det venter på, og hvor lenge.",
        "Alle har bestilt. Båndet går ett felt, Uke 12 lyser opp. Under 2 sekunder, og et trykk hopper over.",
        "Pause med avtalt tid. Kommer ikke Jonas, tar KI-spiller setet, med egen figur og tekst. Jonas kan ta det tilbake.",
        "Først hele kjeden, så per Rolle, aldri per navn. Ingen topplister, kost er ikke poeng. Neste knapp er Debrief.",
    ]
    for i, fr in enumerate(frames):
        x = px0 + i * pitch
        o.append(pframe(fr, x, 76, s, top=tops[i]))
        o.append(T(x - 4, 740, heads[i], "pb", 20))
        o.append(para(x - 4, 766, texts[i], 300, "b", 15, 20))

    # flytpiler mellom rutene
    for i in range(5):
        x = px0 + i * pitch + 304
        o.append(G(sprite(x, 372, ARROW_R, 4, {"W": "P"})))

    # Under rutene: Tekst + animert uke-løkke
    y = 900
    o.append(G(R(28, y - 12, 2044, 4, PLUM)))
    o.append(T(28, y + 32, "Hva som gjør denne spillefølelsen unik", "pb", 24))
    txt = ("Du leser ikke tabeller, du ser et lite verksted. Tallet På vei er kasser du kan telle, og ordren din står "
           "på båndet før du trykker, så «jeg bestilte for mye fordi jeg ikke så det som var på vei» blir noe du "
           "kan se med øynene: 24 hule kasser over 16 faste. Hele løkka er som et lite spill på bussen, med tommelen "
           "på et hjul og en rund knapp, og overgangen er så kort at den tåler 36 runder uten at du lærer å hate den. "
           "Samtidig finnes det ingen score: kost er ett tall i raden, aldri et rekordtall.")
    o.append(para(28, y + 70, txt, 1100, "b", 20, 30))
    # Uke-løkka
    lx = 1200
    o.append(T(lx, y + 32, "Slik ser løkka ut for tommelen", "pb", 24))
    steps = [("Se", "Bånd, hylle, kø"), ("Still hjul", "Ett heltall"), ("BESTILL", "Låses"), ("Vent", "Hvem og hvor lenge"),
             ("Bånd går", "Under 2 sek")]
    for i, (h, b) in enumerate(steps):
        x = lx + i * 172
        o.append(G(box(x, y + 52, 156, 72, PLUM)))
        o.append(T(x + 78, y + 82, h, "pb", 20, WHITE, "middle"))
        o.append(T(x + 78, y + 106, b, "b", 14, TINT, "middle"))
    belt = [belt_strip(lx, y + 142, 860)]
    crate = sprite(lx + 8, y + 130, CRATE)
    crate_anim = (f'<g>{crate}<animateTransform attributeName="transform" type="translate" dur="7s" '
                  f'repeatCount="indefinite" values="0 0;172 0;172 0;344 0;344 0;516 0;516 0;688 0;688 0;832 0" '
                  f'keyTimes="0;.1;.2;.3;.4;.5;.6;.7;.8;1"/></g>')
    o.append(G(*belt, crate_anim))
    o.append(T(lx, y + 186, "1 kasse = 1 enhet. Over 24 i ett felt brukes pall (10 kasser) med tall på, så båndet", "b", 15))
    o.append(T(lx, y + 206, "tåler de største ukene. Demodata viser opptil 90 på vei.", "b", 15))
    o.append(demodata(2072, 48, PLUM, "end", 16))
    return write_svg("06-spilldynamikk", 2100, 1200, "Storyboard av spilldynamikken",
                     "Seks telefonruter: Uka åpner, Beslutningen 24 med 16 på vei, Bekreftet, Uka går videre, "
                     "Jonas er borte med Pause og KI-spiller, Spillet slutter. Notater og tekst om spillefølelsen under.",
                     "".join(o))


# =================================== 07 DEBRIEF ===============================================
def mini_chart(x, y, role, colw=8, unit=2, h=64, col=None, seats=None):
    """Ordrer per uke for en Rolle, til skala. Søyle av piksler."""
    vals = [w["seats"][role]["ordre"] for w in WEEKS]
    out = [R(x, y + h, colw * 36, 2, TINT)]
    for i, v in enumerate(vals):
        hh = v * unit
        if hh:
            out.append(R(x + i * colw, y + h - hh, colw - 1 if colw > 2 else colw, hh, col or YEL))
    return "".join(out)


def demand_tile(x, y, colw=8, unit=4, fg=CY):
    out = []
    h = 8 * unit
    for i, w in enumerate(WEEKS):
        hh = w["demand"] * unit
        out.append(R(x + i * colw, y + h - hh, colw, hh, fg))
    return "".join(out)


def d1():
    o = [G(box(0, 0, 390, 844, PLUM, 4))]
    o.append(T(20, 48, "Opptaket er låst", "pb", 32, WHITE))
    o.append(G(sprite(20, 70, TAPE, 8)))
    o.append(G(sprite(128, 72, LOCK, 8, {"P": "Y"})))
    o.append(T(200, 90, "Ingen avsløring før", "bb", 16, YEL))
    o.append(T(200, 110, "du har forklart", "bb", 16, YEL))
    o.append(T(200, 130, "med egne ord.", "bb", 16, YEL))
    o.append(T(20, 168, "Forklaring", "pb", 24, WHITE))
    o.append(para(20, 194, "Hvorfor oppførte kjeden seg slik, og hvilken del hadde ordrene dine i det?", 350, "b", 16, 22,
                  WHITE))
    o.append(G(box(20, 248, 350, 300, WHITE)))
    ex = ("Vi var tomme fra uke 9. Jeg trodde leveringene ble borte og at kunden kjøpte mye mer, så jeg bestilte 24 i "
          "uke 11. Så kom det alt for mange kasser senere.")
    o.append(para(36, 280, ex, 318, "b", 16, 24))
    o.append(G(R(36, 412, 4, 20, PLUM)))
    o.append(T(36, 530, "Lagres uendret. De andre ser den ikke.", "b", 14))
    o.append(btn(20, 572, 350, 64, "Lagre Forklaring", "pri", 24))
    o.append(T(20, 668, "Forklaringen teller ikke, og den er ingen", "b", 16, TINT))
    o.append(T(20, 690, "prøve. Den er utgangspunktet for resten.", "b", 16, TINT))
    o.append(T(20, 734, "I gruppa: Ida er ferdig. Mikkel skriver.", "b", 16, WHITE))
    o.append(T(20, 756, "Jonas skriver. Dere går videre sammen.", "b", 16, WHITE))
    o.append(demodata(370, 820, TINT, "end"))
    return "".join(o)


def d2():
    o = [G(box(0, 0, 390, 844, PLUM, 4))]
    o.append(G(sprite(20, 26, REW, 4)))
    o.append(T(64, 50, "Opptak spoles tilbake", "pb", 24, WHITE))
    for i, r in enumerate(CHAIN):
        y = 76 + i * 34
        o.append(T(20, y + 20, r, "b", 13, TINT))
        o.append(G(belt_strip(104, y + 10, 268)))
        w = seat(18, r)["ordre"]
        crates = "".join(sprite(112 + (k * 16), y - 2, CRATE) for k in range(min(w // 2, 15)))
        o.append(G(f'<g>{crates}<animateTransform attributeName="transform" type="translate" dur="5s" '
                   f'repeatCount="indefinite" values="0 0;0 0;-48 0;0 0" keyTimes="0;.75;.95;1"/></g>'))
    o.append(T(20, 234, "Uke 36, 35, 34 ... ned til Uke 1", "b", 14, TINT))
    # rute: kundens to trappetrinn
    o.append(T(195, 296, "Kunden, hele spillet", "pb", 24, WHITE, "middle"))
    tx = 51
    o.append(G(box(tx - 16, 312, 320, 88, WHITE), demand_tile(tx, 356, 8, 4, PLUM)))
    o.append(T(tx + 34, 346, "Uke 5", "bb", 13))
    o.append(T(tx, 420, "Uke 1", "b", 14, TINT))
    o.append(T(tx + 288, 420, "Uke 36", "b", 14, TINT, "end"))
    # Tallene
    o.append(T(146, 500, "4", "sb", 64, YEL, "end"))
    o.append(G(sprite(160, 458, ARROW_R, 8, {"W": "T"})))
    o.append(T(232, 500, "8", "sb", 64, YEL))
    o.append(T(195, 532, "én gang, i uke 5", "bb", 16, YEL, "middle"))
    o.append(para(20, 572, "Det er alt kunden gjorde. 4 per uke, så 8 per uke fra uke 5, og stabilt helt til slutt.", 350, "b",
                  18, 26, WHITE))
    o.append(para(20, 666, "Alt annet du så, kom fra ordrer som gikk gjennom kjeden.", 350, "bb", 18, 26, CY))
    o.append(btn(20, 730, 350, 60, "Se hva ordrene gjorde", "pri", 20))
    o.append(demodata(370, 826, TINT, "end"))
    return "".join(o)


def d3():
    o = [G(box(0, 0, 390, 844, PLUM, 4))]
    o.append(T(20, 46, "Dette er Beer Game", "pb", 28, WHITE))
    o.append(para(20, 72, "En klassisk øvelse i forsyningskjeder. Ordrene deres, Uke for Uke, til samme skala:", 350, "b", 15,
                  20, TINT))
    y = 118
    o.append(G(box(20, y, 350, 56, PLUM2)))
    o.append(T(32, y + 20, "Kunden", "bb", 15, WHITE))
    o.append(T(358, y + 20, "4, så 8", "bb", 15, CY, "end"))
    o.append(G("".join(R(70 + i * 8, y + 48 - WEEKS[i]["demand"] * 2, 8, WEEKS[i]["demand"] * 2, CY) for i in range(36))))
    y2 = y + 66
    labels = F["amplification"]
    for i, r in enumerate(ROLES):
        yy = y2 + i * 104
        o.append(G(sprite(20, yy + 2, ROLE_SP[r], 2)))
        o.append(T(52, yy + 16, r, "bb", 15, WHITE))
        o.append(T(370, yy + 16, str(labels[r]).replace(".", ",") + "×", "sb", 16, YEL, "end"))
        o.append(G(mini_chart(70, yy + 24, r, 8, 2, 64, YEL)))
    yb = y2 + 4 * 104
    o.append(T(70, yb + 8, "Uke 1", "b", 13, TINT))
    o.append(T(358, yb + 8, "Uke 36", "b", 13, TINT, "end"))
    t = ("Fra 1,8× hos Detaljist til 7,6× hos Fabrikk. Hvert ledd så bare ordren fra leddet under, og leveringene kom "
         "fire uker etter.")
    o.append(para(20, yb + 34, t, 350, "b", 15, 20, WHITE))
    o.append(T(20, yb + 112, "Se de samme tallene som tabell", "bb", 14, CY))
    o.append(G(R(20, yb + 116, 214, 2, CY)))
    o.append(demodata(370, yb + 112, TINT, "end"))
    return "".join(o)


def d4():
    o = [G(box(0, 0, 390, 844, PLUM, 4))]
    o.append(T(20, 46, "Ditt øyeblikk: Uke 11", "pb", 28, WHITE))
    y = 58
    o.append(G(belt_strip(20, y + 96, 284)))
    segs = [(15, 24, GHOST), (14, 8, CRATE), (13, 4, CRATE), (12, 4, CRATE)]
    for i, (wk, n, spr) in enumerate(segs):
        x = 24 + i * 70
        o.append(G(stack(x, y + 96, n, spr)))
        o.append(T(x, y + 132, ("+24" if i == 0 else str(n)), "sb", 16, CY if i == 0 else WHITE))
        o.append(T(x, y + 149, f"Uke {wk}", "b", 13, TINT))
    o.append(T(314, y + 76, "Lager", "bb", 13, WHITE))
    o.append(T(314, y + 104, "0", "sb", 24, COR))
    yy = 234
    o.append(T(20, yy, "Du så", "bb", 16, YEL))
    o.append(T(20, yy + 22, "Lager 0, Restordre 13, Ordre inn 8, På vei 16.", "b", 14, WHITE))
    o.append(T(20, yy + 52, "Du bestilte", "bb", 16, YEL))
    o.append(T(20, yy + 80, "24", "sb", 24, WHITE))
    o.append(T(62, yy + 79, "selv om 16 allerede var på vei.", "b", 15, WHITE))
    o.append(T(20, yy + 110, "Hva det kostet senere", "bb", 16, YEL))
    later = kr(seat(36)["kost_sum"] - seat(24)["kost_sum"])
    peak = max(range(25, 37), key=lambda w: seat(w)["lager"])
    t1 = (f"Da kassene kom, sto Lager på opptil {seat(peak)['lager']} i uke {peak}. "
          f"Uke 25 til 36 kostet {later} kr i lagerkost.")
    o.append(para(20, yy + 132, t1, 350, "b", 15, 20, WHITE))
    y3 = yy + 132 + plines(t1, 350, "b", 15) * 20 + 10
    o.append(T(20, y3, "Hva de andre så i Uke 11", "bb", 16, YEL))
    for i, r in enumerate(["Detaljist", "Distributør", "Fabrikk"]):
        s = seat(11, r)
        y1 = y3 + 22 + i * 19
        o.append(T(20, y1, r, "bb", 14, WHITE))
        o.append(T(112, y1, f"Lager {s['lager']}, Restordre {s['restordre']}, Inn {s['innkommende_ordre']}", "b", 14, WHITE))
    y4 = y3 + 22 + 3 * 19 + 4
    t2 = "Distributør så Inn 4 denne uka. To uker senere så den Inn 24: din ordre, uten forklaring."
    o.append(para(20, y4, t2, 350, "b", 15, 20, WHITE))
    y5 = y4 + plines(t2, 350, "b", 15) * 20 + 4
    o.append(T(20, y5, "Mønster: forsinkelse skjuler det som er på vei.", "bb", 14, CY))
    y6 = y5 + 12
    o.append(G(box(20, y6, 350, 58, PLUM2), sprite(32, y6 + 12, ROBOT, 4)))
    o.append(T(84, y6 + 24, "KI-generert, kan ta feil", "bb", 15, CY))
    o.append(T(84, y6 + 44, "Tallene er beregnet fra spilloggen.", "b", 14, WHITE))
    o.append(btn(20, 752, 350, 52, "Neste øyeblikk", "pri", 20))
    o.append(demodata(370, 828, TINT, "end"))
    return "".join(o)


def d5():
    o = [G(box(0, 0, 390, 844, PLUM, 4))]
    o.append(T(20, 46, "Debrief-quiz", "pb", 28, WHITE))
    o.append(T(20, 72, "Teller ikke. Du kan prøve igjen.", "b", 15, TINT))
    o.append(para(20, 112, "Kunden gikk fra 4 til 8. Hvorfor bestilte Fabrikk opptil 31 i uka?", 350, "bb", 18, 26, WHITE))
    opts = [("Kunden kjøpte mye mer enn tallene viser.", "wrong"),
            ("Hvert ledd reagerte på ordren fra leddet under, mens levering var forsinket.", "none"),
            ("Fabrikken bestilte feil i de siste ukene.", "none")]
    y = 182
    for txt, st in opts:
        lines = wrap(txt, 278, "b", 15)
        h = 26 + 20 * len(lines)
        o.append(G(box(20, y, 350, h, WHITE)))
        if st == "wrong":
            o.append(G(frame(20, y, 350, h, COR), sprite(32, y + 12, CROSS, 4, {"O": "P"})))
        else:
            o.append(G(frame(32, y + 12, 20, 20, PLUM, 4, 0)))
        for k, line in enumerate(lines):
            o.append(T(66, y + 26 + k * 20, line, "bb" if st == "wrong" else "b", 15))
        y += h + 10
    o.append(T(20, y + 22, "Du valgte første svar. Det er feil.", "bb", 16, YEL))
    t = ("Kundens ordre står i opptaket: 4, så 8, og stabil. Tallene over 8 oppsto i kjeden, fordi hvert ledd bestilte "
         "mer for å ta igjen det som manglet, mens kassene fortsatt var på vei.")
    o.append(para(20, y + 48, t, 350, "b", 15, 21, WHITE))
    y3 = y + 48 + plines(t, 350, "b", 15) * 21 + 2
    o.append(G(sprite(20, y3, ROBOT, 2)))
    o.append(T(46, y3 + 13, "KI-generert, kan ta feil", "bb", 14, CY))
    o.append(btn(20, 716, 350, 60, "Svar på nytt", "pri", 20))
    o.append(T(195, 800, "Alle svar må være riktige for å gå videre.", "b", 14, TINT, "middle"))
    o.append(demodata(370, 828, TINT, "end"))
    return "".join(o)


def build_07():
    o = [T(28, 46, "Debrief: opptaket spoles tilbake", "pb", 32)]
    s = .75
    frames = [d1(), d2(), d3(), d4(), d5()]
    heads = ["1  Skriv Forklaring", "2  Klimaks: kunden avsløres", "3  Ordrene i ett diagram", "4  Ditt øyeblikk", "5  Quiz"]
    notes = ["Avsløringen er låst til Forklaringen er lagret. Hver skriver på sin egen telefon.",
             "Opptaket spoles over alle fire båndene og stopper på en liten rute: to trappetrinn.",
             "Samme skala for alle. Trappetrinnene er små, tårnene er det ikke. Første gang øvelsen får navn.",
             "Struktur, ikke personer: hva du så, hva du bestilte, hva det kostet, hva de andre så.",
             "Feil svar forklares. Uten rangering og uten karakter."]
    for i, fr in enumerate(frames):
        x = 40 + i * 410
        o.append(pframe(fr, x + 48, 66, s, top=PLUM))
        o.append(T(x + 40, 722, heads[i], "pb", 20))
        o.append(para(x + 40, 746, notes[i], 310, "b", 15, 19))

    # Delt skjerm: opptak + pikseldiagram
    x0, y0, sw_, sh_ = 28, 796, 2044, 392
    o.append(G(box(x0, y0, sw_, sh_, PLUM, 8)))
    o.append(T(x0 + 28, y0 + 42, "Delt skjerm i Labtimen", "pb", 28, WHITE))
    o.append(T(x0 + 28, y0 + 68, "Spill 17. Bare felles diagrammer. Forklaring og øyeblikk blir på hver telefon.", "b", 16, TINT))
    o.append(T(x0 + sw_ - 24, y0 + 68, "Ordrer per Uke. 1 enhet = 2 piksler for kunden og alle Roller.", "b", 16, TINT, "end"))
    o.append(demodata(x0 + sw_ - 24, y0 + 36, TINT, "end", 16))
    # Kundens rute, til samme skala som søylene
    tx, ty = x0 + 28, y0 + 90
    o.append(G(box(tx, ty, 260, 200, PLUM2)))
    o.append(T(tx + 20, ty + 36, "Kunden", "pb", 24, WHITE))
    o.append(T(tx + 20, ty + 62, "4, så 8 fra uke 5", "bb", 16, CY))
    o.append(G("".join(R(tx + 22 + i * 6, ty + 150 - WEEKS[i]["demand"] * 2, 6, WEEKS[i]["demand"] * 2, CY)
                       for i in range(36))))
    o.append(G(R(tx + 22, ty + 150, 216, 2, WHITE)))
    o.append(T(tx + 22, ty + 172, "Uke 1", "b", 14, WHITE))
    o.append(T(tx + 238, ty + 172, "Uke 36", "b", 14, WHITE, "end"))
    o.append(G(sprite(tx + 6, y0 + 320, REW, 4)))
    o.append(T(tx + 50, y0 + 342, "Spol opptaket igjen", "bb", 16, WHITE))
    # De fire båndene som søyler
    lx = x0 + 500
    lane_h = 66
    colw = 40
    for i, r in enumerate(ROLES):
        yy = y0 + 86 + i * lane_h
        o.append(G(sprite(lx - 186, yy + 20, ROLE_SP[r], 2)))
        o.append(T(lx - 152, yy + 38, r, "bb", 16, WHITE))
        amp = str(F["amplification"][r]).replace(".", ",") + "×"
        o.append(T(lx - 16, yy + 62, amp, "sb", 16, YEL, "end"))
        vals = [w["seats"][r]["ordre"] for w in WEEKS]
        bars = [R(lx, yy + lane_h - 2, colw * 36, 2, TINT)]
        for k, v in enumerate(vals):
            if v:
                bars.append(R(lx + k * colw, yy + lane_h - 2 - v * 2, colw - 4, v * 2, YEL))
        o.append(G(*bars))
    # Spillehode som spoler tilbake og stopper på Saras øyeblikk
    mx = lx + 10 * colw + 18
    head_line = R(mx, y0 + 86, 2, 4 * lane_h, CY)
    o.append(G(f'<g>{head_line}<animateTransform attributeName="transform" type="translate" dur="9s" repeatCount="indefinite" '
               f'values="0 0;0 0;{25 * colw} 0;0 0" keyTimes="0;.7;.72;1"/></g>'))
    o.append(T(mx + 8, y0 + 100, "Uke 11: Grossist bestilte 24", "bb", 14, CY))
    ay = y0 + 86 + 4 * lane_h + 18
    for w in (1, 5, 11, 20, 30, 36):
        o.append(T(lx + (w - 1) * colw + 18, ay, w, "b", 14, TINT, "middle"))
    o.append(T(lx - 16, ay, "Uke", "b", 14, TINT, "end"))
    return write_svg("07-debrief", 2100, 1200, "Gruppedebrief i fem steg",
                     "Fem telefonruter: Forklaring med låst avsløring, opptak og kundens to trappetrinn, ordrer per Rolle "
                     "med forsterkning 1,8× til 7,6×, ditt øyeblikk i Uke 11, quiz med forklart feil svar. Under: delt skjerm.",
                     "".join(o))


# =================================== 01 LANDING ===============================================
LOGO = ["WWW.YYY.WWW", "WWW.YYY.WWW", "WWW.YYY.WWW"]


def logo(x, y, name_fill=WHITE, sz=24):
    return G(sprite(x, y + 4, ["YYY.YYY.YYY", "YYY.YYY.YYY", "YYY.YYY.YYY"], 4), R(x + 12, y + 12, 4, 4, name_fill),
             R(x + 28, y + 12, 4, 4, name_fill)) + T(x + 56, y + 22, "Pikselkjeden", "pb", sz, name_fill)


def station_land(x, y, role, order, ki=False):
    o = [G(sprite(x, y, ROLE_SP[role], 8))]
    bw = sw(ROLE_SP[role], 8)
    o.append(T(x + bw / 2, y + 104, role, "pb", 24, WHITE, "middle"))
    o.append(G(box(x + bw / 2 - 28, y + 114, 56, 52, WHITE)))
    # ett tall
    o.append(T(x + bw / 2, y + 152, order, "sb", 32, PLUM, "middle"))
    if ki:
        o.append(G(sprite(x + bw - 8, y - 56, ROBOT, 4)))
        o.append(T(x + bw + 34, y - 26, "KI-spiller", "bb", 16, CY))
    return "".join(o)


def build_01():
    o = [G(R(0, 0, 1440, 860, PLUM))]
    o.append(logo(72, 28))
    o.append(btn(1228, 24, 140, 44, "Logg inn", "sek", 16))
    h = ["Fire Seter. Ett tall i uka.", "Hele øvelsen kjører", "uten at du blir dommer."]
    for i, line in enumerate(h):
        o.append(T(72, 150 + i * 72, line, "pb", 64, YEL if i == 0 else WHITE))
    p = ("Pikselkjeden kjører en forsyningskjede-øvelse fra Invitasjon til PDF-rapport, for klasser på rundt 250 "
         "studenter. Studentene spiller på mobil, på norsk. Du laster opp studentlisten fra Canvas-eksport og ser alle "
         "spillene på én skjerm.")
    o.append(para(72, 340, p, 830, "b", 22, 32, WHITE))
    o.append(btn(72, 452, 300, 68, "Be om lærertilgang", "pri", 24))
    o.append(btn(392, 452, 140, 68, "Logg inn", "sek", 20))

    # Kjeden: fire stasjoner, kasser mot høyre, ordrelapper mot venstre
    gy = 600
    xs = [64, 310, 556, 802]
    orders = [6, 2, 8, 4]
    belt_y = gy + 56
    o.append(G(belt_strip(0, belt_y, 960), R(0, belt_y - 56, 960, 4, TINT)))
    for i in range(3):
        bx = xs[i] + 96
        seq = "".join(sprite(bx + k * 24, belt_y - 16, CRATE, 4) for k in range(4 + (i % 2)))
        o.append(G(f'<g>{seq}<animateTransform attributeName="transform" type="translate" dur="6s" repeatCount="indefinite" '
                   f'values="0 0;0 0;24 0;0 0" keyTimes="0;.7;.9;1"/></g>'))
        slip = sprite(bx + 56, belt_y - 52, SLIP, 4)
        o.append(G(f'<g>{slip}<animateTransform attributeName="transform" type="translate" dur="6s" repeatCount="indefinite" '
                   f'values="0 0;0 0;-40 0;0 0" keyTimes="0;.7;.9;1"/></g>'))
    for i, r in enumerate(CHAIN):
        o.append(station_land(xs[i], gy, r, orders[i], ki=(i == 0)))
    o.append(G(sprite(70, gy + 186, ARROW_R, 4)))
    o.append(T(106, gy + 204, "Kasser går denne veien.", "bb", 16, WHITE))
    o.append(G(sprite(310, gy + 186, ARROW_L, 4)))
    o.append(T(346, gy + 204, "Ordre går andre veien.", "bb", 16, WHITE))
    o.append(T(576, gy + 204, "Hver Rolle bestiller ett heltall. Systemet regner.", "bb", 16, WHITE))
    o.append(demodata(1368, 848, TINT, "end"))

    # Telefon på høyre side, står i verdenen
    o.append(pframe(phone_game(state11()), 1076, 110, .75))

    # Neste seksjon
    y = 860
    o.append(T(72, y + 64, "Ett bånd fra Canvas-fil til PDF", "pb", 40))
    o.append(T(72, y + 98, "Ett fravær stopper ikke gruppa: KI-spillere fyller tomme Seter, og ingen spill blir stående uferdig.", "b", 20))
    stops = [("Canvas-eksport", FILE, "Studentliste inn"), ("Invitasjon", MAIL, "Sendes til alle"),
             ("Klassespill", CRATE, "Spill på mobil"), ("Debrief", TAPE, "Opptak og Forklaring"),
             ("Replay", REW, "Én runde til"), ("Individuell test", CHECKLIST, "Med KI-vurdering som ikke teller"),
             ("PDF-rapport", DOC, "Til hver student")]
    by = y + 214
    o.append(G(R(0, by, 1440, 24, PLUM), *[R(i * 24 + 4, by + 10, 12, 4, TINT) for i in range(60)]))
    remap = {"W": "W", "P": "P"}
    for i, (name, spr, desc) in enumerate(stops):
        x = 72 + i * 196
        p = 6 if len(spr[0]) <= 9 else 4
        if spr is CRATE:
            p = 12
        hh = len(spr) * p
        o.append(G(box(x, by - 76, 76, 72, PLUM), sprite(x + 38 - len(spr[0]) * p // 2, by - 40 - hh // 2, spr, p)))
        o.append(T(x, by + 56, name, "pb", 20))
        o.append(para(x, by + 80, desc, 170, "b", 15, 20))
    return write_svg("01-landing", 1440, 1200, "Pikselkjeden, landingsside for faglærere",
                     "Pikselkjeden. Fire Seter og ett tall i uka. Be om lærertilgang. Kjeden med fire stasjoner viser at "
                     "kasser går én vei og ordre den andre, og båndet under viser hele øvelsen fra Canvas-fil til PDF.",
                     "".join(o), WHITE)


# =================================== LÆRERSKALL ===============================================
def teacher_head(w, title, sub):
    o = [G(R(0, 0, w, 72, PLUM))]
    o.append(logo(28, 22, WHITE, 20))
    o.append(T(250, 46, title, "pb", 28, YEL))
    o.append(T(w - 28, 34, sub, "bb", 15, WHITE, "end"))
    o.append(demodata(w - 28, 54, TINT, "end"))
    return "".join(o)


def field(x, y, w, label, value, h=44, sz=16, hint=None):
    o = [T(x, y, label, "bb", 14)]
    o.append(G(box(x, y + 8, w, h, WHITE), frame(x, y + 8, w, h, PLUM, 2, 4)))
    o.append(T(x + 14, y + 8 + h / 2 + sz * .35, value, "b", sz))
    if hint:
        o.append(T(x, y + h + 26, hint, "b", 14))
    return "".join(o)


def seg(x, y, w, label, options, sel):
    """Valgknapper: valgt vises med fylt felt, hake-sprite og fet tekst."""
    o = [T(x, y, label, "bb", 14)]
    each = w // len(options)
    for i, opt in enumerate(options):
        xx = x + i * each
        if i == sel:
            o.append(G(box(xx, y + 8, each - 4, 40, PLUM), sprite(xx + 10, y + 16, CHECK, 3)))
            o.append(T(xx + 36, y + 33, opt, "bb", 15, WHITE))
        else:
            o.append(G(box(xx, y + 8, each - 4, 40, WHITE), frame(xx, y + 8, each - 4, 40, PLUM, 2, 4)))
            o.append(T(xx + 14, y + 33, opt, "b", 15))
    return "".join(o)


# =================================== 02 KLASSE ================================================
def build_02():
    o = [teacher_head(1440, "Ny Klasse", "Bård, Faglærer")]
    # transportbånd-progresjon
    stations = ["Navn", "Fil", "Kolonne", "Invitasjoner", "Status"]
    y = 96
    o.append(G(belt_strip(40, y + 24, 1360)))
    for i, s in enumerate(stations):
        x = 80 + i * 300
        o.append(G(box(x, y, 40, 40, PLUM), sprite(x + 10, y + 8, CHECK, 3)))
        o.append(T(x + 52, y + 18, s, "pb", 20))
    # Venstre
    lx = 40
    o.append(T(lx, 186, "Klasse", "pb", 24))
    o.append(field(lx, 214, 400, "Navn", "class-of-1994"))
    o.append(field(lx + 420, 214, 220, "Emnekode", "IBE160"))
    o.append(T(lx, 306, "Studentliste", "pb", 24))
    o.append(G(box(lx, 320, 640, 72, PLUM), sprite(lx + 16, 338, FILE, 4)))
    o.append(T(lx + 64, 350, "ibe160-canvas-eksport.xlsx", "bb", 18, WHITE))
    o.append(T(lx + 64, 374, "250 rader lest fra Canvas-eksport", "b", 15, TINT))
    o.append(btn(lx + 520, 334, 104, 44, "Bytt fil", "pri", 16))
    o.append(T(lx, 430, "Hvilken kolonne er e-post?", "pb", 24))
    cols = [("Navn", 170), ("Student-ID", 110), ("Seksjon", 90), ("Kolonne D: E-post", 270)]
    rows = [("Emma Berg", "410221", "IBE160-01", "emma.berg@student.example.no"),
            ("Ola Haugen", "410237", "IBE160-01", "ola.haugen@student.example.no"),
            ("Sara Moe", "410318", "IBE160-02", "sara.moe@student.example.no"),
            ("Jonas Lie", "410355", "IBE160-02", "jonas.lie@student.example.no")]
    ty = 446
    cx = lx
    for (c, wd) in cols:
        o.append(T(cx + 8, ty + 18, c, "bb", 14))
        cx += wd
    o.append(G(R(lx, ty + 26, 640, 2, PLUM)))
    for j, r in enumerate(rows):
        cx = lx
        for k, (c, wd) in enumerate(cols):
            o.append(T(cx + 8, ty + 50 + j * 28, r[k], "b", 14))
            cx += wd
    hx = lx + 370
    o.append(G(frame(hx, ty - 4, 270, 34 + 4 * 28 + 2, PLUM, 4, 4)))
    o.append(seg(lx, 620, 640, "E-post hentes fra", ["Kolonne D: E-post", "Kolonne E: Sekundær", "Velg annen"], 0))
    o.append(T(lx, 694, "246 gyldige adresser i kolonne D, 4 ugyldige.", "bb", 16))
    # Invitasjon
    o.append(T(lx, 742, "Send Invitasjoner", "pb", 24))
    o.append(para(lx, 768, "Går til de 246 gyldige adressene. Invitasjonen er gyldig i 14 dager. Studentene kan ikke registrere seg uten den.",
                  640, "b", 16, 22))
    o.append(btn(lx, 824, 320, 64, "Send 246 Invitasjoner", "pri", 22))
    o.append(T(lx + 340, 852, "Første runde sendt 5. nov 09:12.", "b", 15))
    o.append(T(lx + 340, 872, "Du kan sende på nytt når som helst.", "b", 15))

    # Høyre
    rx = 730
    o.append(T(rx, 186, "4 ugyldige rader", "pb", 24))
    bad = [(37, "Thea Lund", "thea.lund@student", "Mangler domene"),
           (88, "Oskar Dahl", "oskar.dahl(at)student.example.no", "Ugyldig tegn"),
           (141, "Ingrid Vik", "ingrid.vik@@student.example.no", "To @"),
           (203, "Liam Ås", "", "Tom celle")]
    y = 204
    for j, (n, name, adr, why) in enumerate(bad):
        yy = y + j * 64
        o.append(G(box(rx, yy, 670, 56, WHITE), sprite(rx + 12, yy + 18, CROSS, 4)))
        o.append(T(rx + 44, yy + 24, f"Rad {n}", "bb", 16))
        o.append(T(rx + 120, yy + 24, name, "bb", 15))
        o.append(T(rx + 44, yy + 44, (adr or "(ingen adresse)") + ": " + why, "b", 14))
        lab = "Manuelt registrert" if n in (37, 141) else "Registrer manuelt"
        if n in (37, 141):
            o.append(G(sprite(rx + 500, yy + 20, CHECK, 3, {"C": "P"})))
            o.append(T(rx + 526, yy + 34, lab, "bb", 14))
        else:
            o.append(btn(rx + 500, yy + 10, 158, 36, lab, "sek", 14, "bb"))
    # Status
    o.append(T(rx, 492, "Status for Invitasjoner", "pb", 24))
    # 250 kasser i rutenett, hver form betyr noe
    akseptert, venter, utlopt, ugyldig = 238, 5, 3, 4
    cells = ["a"] * akseptert + ["v"] * venter + ["u"] * utlopt + ["x"] * ugyldig
    grid = []
    gx, gy = rx, 510
    for i, c in enumerate(cells):
        cc, rr = i % 50, i // 50
        px, py = gx + cc * 13, gy + rr * 13
        if c == "a":
            grid.append(R(px, py, 10, 10, PLUM))
        elif c == "v":
            grid.append(R(px, py, 10, 2, PLUM) + R(px, py + 8, 10, 2, PLUM) + R(px, py, 2, 10, PLUM) + R(px + 8, py, 2, 10, PLUM))
        elif c == "u":
            grid.append(R(px, py, 10, 10, YEL) + R(px + 4, py + 2, 2, 6, PLUM))
        else:
            grid.append(R(px, py, 10, 10, COR) + R(px + 4, py + 2, 2, 4, PLUM) + R(px + 4, py + 7, 2, 2, PLUM))
    o.append(G(*grid))
    # tabell over status
    rows2 = [("Akseptert", akseptert, "Har registrert seg", None), ("Sendt, ikke svart", venter, "Venter på registrering", None),
             ("Utløpt", utlopt, "Gikk ut etter 14 dager", "Send på nytt"), ("Ugyldig adresse", ugyldig, "2 manuelt registrert, 2 gjenstår", None)]
    y = 594
    o.append(T(rx + 20, y, "Status", "bb", 14))
    o.append(T(rx + 230, y, "Antall", "bb", 14, PLUM, "end"))
    o.append(T(rx + 250, y, "Merknad", "bb", 14))
    o.append(G(R(rx, y + 8, 670, 2, PLUM)))
    for j, (a, n, m, b) in enumerate(rows2):
        yy = y + 34 + j * 40
        icon = {0: R(rx, yy - 12, 10, 10, PLUM),
                1: frame(rx, yy - 12, 10, 10, PLUM, 2, 0),
                2: R(rx, yy - 12, 10, 10, YEL) + R(rx + 4, yy - 10, 2, 6, PLUM),
                3: R(rx, yy - 12, 10, 10, COR) + R(rx + 4, yy - 10, 2, 4, PLUM)}[j]
        o.append(G(icon))
        o.append(T(rx + 20, yy, a, "b", 16))
        o.append(T(rx + 230, yy, n, "bb", 16, PLUM, "end"))
        o.append(T(rx + 250, yy, m, "b", 15))
        if b:
            o.append(btn(rx + 520, yy - 22, 150, 34, b, "sek", 14, "bb"))
    o.append(G(R(rx, 780, 670, 2, PLUM)))
    o.append(T(rx, 812, "På Klasselisten: 250. Registrert: 238 + 2 manuelt = 240. Uregistrert: 10.", "bb", 16))
    o.append(T(rx, 836, "Oppdateres når studentene registrerer seg.", "b", 15))
    o.append(btn(rx, 856, 300, 44, "Gå videre til Klasseøkt", "mork", 16))
    return write_svg("02-laerer-klasse", 1440, 1000, "Faglærer lager Klasse",
                     "Navn og emnekode, Canvas-fil, valg av e-postkolonne, fire ugyldige rader, send Invitasjoner og status "
                     "for 250 rader: akseptert, sendt, utløpt og ugyldig.", "".join(o), WHITE)


# =================================== 03 KLASSEØKT =============================================
def build_03():
    o = [teacher_head(1440, "Klasseøkt: IBE160", "class-of-1994, 240 studenter")]
    # Kolonne 1: standarder
    x = 40
    o.append(T(x, 112, "Spillinnstillinger: Klassisk", "pb", 24))
    o.append(T(x, 138, "Forhåndsutfylt. Du kan lagre uten å endre noe.", "bb", 15))
    y = 154
    o.append(G(box(x, y, 430, 150, PLUM)))
    for i, r in enumerate(CHAIN):
        sx = x + 16 + i * 104
        o.append(G(sprite(sx, y + 14, ROLE_SP[r], 4)))
        o.append(T(sx, y + 72, r, "b", 13, WHITE))
    o.append(T(x + 16, y + 104, "2 uker ordre og 2 uker frakt mellom hvert ledd.", "b", 14, TINT))
    o.append(T(x + 16, y + 126, "2 uker produksjon hos Fabrikk.", "b", 14, TINT))
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Etterspørsel", "4, så 8 i uke 5"), ("Lagerkost", "0,50 kr"), ("Restordrekost", "1,00 kr"),
            ("Antall Uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t")]
    y = 336
    for i, (a, b) in enumerate(rows):
        yy = y + i * 38
        o.append(T(x, yy, a, "b", 16))
        o.append(T(x + 430, yy, b, "bb", 16, PLUM, "end"))
        o.append(G(R(x, yy + 11, 430, 2, WHITE2)))
    y = y + 11 * 38 + 4
    o.append(para(x, y, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", 430, "b", 15, 20))
    o.append(T(x, y + 56, "Studentene ser aldri antall Uker eller etterspørselen.", "bb", 15))

    # Kolonne 2
    x2 = 510
    o.append(T(x2, 112, "Valg", "pb", 24))
    o.append(seg(x2, 140, 430, "KI-modus", ["LLM-spillere", "Regelbaserte"], 0))
    o.append(seg(x2, 222, 430, "Debrief-modus", ["Gruppedebrief", "Personlig debrief"], 0))
    o.append(T(x2, 304, "Merke", "bb", 14))
    o.append(G(box(x2, 312, 150, 40, PLUM), sprite(x2 + 10, 320, CHECK, 3)))
    o.append(T(x2 + 36, 337, "Obligatorisk", "bb", 15, WHITE))
    o.append(T(x2 + 166, 337, "Vises for alle studentene.", "b", 15))
    o.append(T(x2, 410, "Datoer", "pb", 24))
    dates = [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]
    for i, (a, b) in enumerate(dates):
        o.append(field(x2 + (i % 2) * 220, 440 + (i // 2) * 84, 208, a, b))
    o.append(T(x2, 632, "Labtimer, Datalab A2", "pb", 24))
    labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    for i, l in enumerate(labs):
        xx, yy = x2 + (i % 2) * 220, 650 + (i // 2) * 56
        o.append(G(box(xx, yy, 208, 44, WHITE), frame(xx, yy, 208, 44, PLUM, 2, 4)))
        o.append(T(xx + 14, yy + 28, l, "b", 16))
    o.append(btn(x2, 766, 208, 44, "Legg til Labtime", "sek", 14, "bb"))

    # Kolonne 3: fordeling
    x3 = 980
    o.append(T(x3, 112, "Fordeling: 60 spill à 4", "pb", 24))
    o.append(para(x3, 138, "240 studenter fordeles tilfeldig. KI-spillere fyller Seter som blir tomme under spillet.", 420, "b", 16, 22))
    gx, gy = x3, 192
    tile, txt = [], []
    for i in range(60):
        cc, rr = i % 10, i // 10
        px, py = gx + cc * 42, gy + rr * 66
        tile.append(box(px, py, 38, 60, PLUM, 2))
        if i == 16:
            tile.append(frame(px - 2, py - 2, 42, 64, COR, 2, 2))
        for k in range(4):
            sx, sy = px + 5 + (k % 2) * 16, py + 24 + (k // 2) * 16
            tile.append(R(sx + 2, sy, 8, 4, YEL) + R(sx, sy + 4, 12, 8, CY))
        txt.append(T(px + 19, py + 17, i + 1, "bb", 13, WHITE, "middle"))
    o.append(G(*tile))
    o.append("".join(txt))
    y = gy + 6 * 66 + 22
    o.append(T(x3, y, "Ingen Sete står tomt. 0 KI-spillere ved start.", "bb", 16))
    o.append(btn(x3, y + 16, 200, 48, "Kjør på nytt", "sek", 16))
    o.append(btn(x3 + 214, y + 16, 206, 48, "Bekreft fordeling", "pri", 16))
    y += 104
    o.append(T(x3, y, "Eksempel: Spill 17", "pb", 20))
    seats17 = [("Jonas", "Fabrikk"), ("Mikkel", "Distributør"), ("Sara", "Grossist"), ("Ida", "Detaljist")]
    for i, (n, r) in enumerate(seats17):
        xx = x3 + i * 106
        o.append(G(box(xx, y + 12, 100, 48, PLUM), sprite(xx + 18, y + 18, ROLE_SP[r], 4)))
        o.append(T(xx, y + 80, n, "bb", 15))
        o.append(T(xx, y + 98, r, "b", 14))

    # Bunnstripe
    o.append(G(R(0, 1008, 1440, 92, PLUM)))
    o.append(T(40, 1046, "Klar til å lagre uten endringer.", "pb", 24, WHITE))
    o.append(T(40, 1074, "Studentene får beskjed når Klasseøkten starter ti. 24. nov.", "b", 16, TINT))
    o.append(btn(1098, 1022, 300, 64, "Lagre Klasseøkt", "pri", 24))
    return write_svg("03-laerer-spill", 1440, 1100, "Faglærer setter opp Klasseøkt",
                     "Forhåndsutfylte Spillinnstillinger, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og "
                     "forhåndsvisning av 60 spill à 4 med kjør på nytt og bekreft.", "".join(o), WHITE)


# =================================== 04 STUDENT HJEM ==========================================
def student_reg():
    o = [G(box(0, 0, 390, 844, PLUM, 4))]
    o.append(logo(20, 24, WHITE, 24))
    o.append(T(20, 106, "Hei, Sara", "pb", 40, YEL))
    o.append(para(20, 140, "Bård har invitert deg til Klasse class-of-1994, IBE160.", 340, "b", 18, 25, WHITE))
    # lite verksted
    o.append(G(belt_strip(0, 268, 390)))
    for i in range(8):
        o.append(G(sprite(16 + i * 48, 256, CRATE)))
    o.append(G(sprite(150, 186, GROSSIST, 6)))
    o.append(para(20, 316, "Du får et Sete i en forsyningskjede. Hver Uke bestemmer du ett tall. Resten regner systemet.", 350, "b",
                  18, 25, WHITE))
    y = 412
    o.append(T(20, y, "E-post", "bb", 15, WHITE))
    o.append(G(box(20, y + 8, 350, 52, WHITE)))
    o.append(T(36, y + 40, "sara.moe@student.example.no", "b", 16))
    y = 492
    o.append(T(20, y, "Velg passord", "bb", 15, WHITE))
    o.append(G(box(20, y + 8, 350, 52, WHITE)))
    pw = "".join(R(36 + i * 16, y + 28, 8, 8, PLUM) for i in range(9))
    o.append(G(pw))
    o.append(T(20, y + 82, "Minst 10 tegn.", "b", 15, TINT))
    o.append(btn(20, 600, 350, 68, "Opprett konto", "pri", 24))
    o.append(para(20, 700, "Invitasjonen er gyldig i 14 dager. Spørsmål går til faglæreren din.", 350, "b", 16, 22, TINT))
    o.append(T(20, 770, "Har du konto allerede?", "b", 16, WHITE))
    o.append(T(196, 770, "Logg inn", "bb", 16, CY))
    o.append(G(R(196, 774, 62, 2, CY)))
    o.append(demodata(370, 822, TINT, "end"))
    return "".join(o)


def student_home():
    o = [G(box(0, 0, 390, 844, WHITE, 4))]
    o.append(G(R(0, 0, 390, 176, PLUM)))
    o.append(T(20, 42, "Spill 17", "pb", 28, WHITE))
    o.append(demodata(370, 28, TINT, "end"))
    o.append(G(sprite(20, 56, GROSSIST, 4)))
    o.append(T(76, 78, "Grossist", "pb", 24, YEL))
    o.append(T(76, 98, "Sara, du har dette Setet", "b", 15, WHITE))
    o.append(G(sprite(20, 112, HOUR, 4)))
    o.append(T(48, 128, "Spillet venter på deg", "bb", 18, YEL))
    o.append(T(48, 146, "Uke 11. Jonas venter også, 3 min.", "b", 15, WHITE))
    o.append(btn(20, 192, 350, 60, "Gå til Uke 11", "pri", 24))
    # Seter
    o.append(T(20, 288, "Setene i Spill 17", "pb", 20))
    pp = [("Jonas", "Fabrikk", "wait"), ("Mikkel", "Distributør", "done"), ("Sara", "Grossist", "you"), ("Ida", "Detaljist", "done")]
    for i, (n, r, k) in enumerate(pp):
        x = 20 + i * 88
        o.append(G(box(x, 306, 84, 44, PLUM), sprite(x + 6, 316, ROLE_SP[r], 2)))
        if k == "done":
            o.append(G(sprite(x + 44, 318, CHECK, 3)))
        else:
            o.append(G(sprite(x + 48, 318, HOUR, 3)))
        o.append(T(x, 368, n, "bb", 14))
        o.append(T(x, 384, r, "b", 13))
    # Steg
    o.append(T(20, 420, "Seks steg", "pb", 20))
    steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "Rapport"]
    y = 434
    o.append(G(R(32, y + 8, 4, 6 * 28 - 16, PLUM)))
    for i, s in enumerate(steps):
        yy = y + i * 28
        if i == 0:
            o.append(G(box(20, yy - 2, 28, 24, PLUM), sprite(26, yy + 2, CRATE, 5)))
            o.append(T(58, yy + 16, s, "bb", 16))
            o.append(T(370, yy + 16, "Nå", "bb", 16, PLUM, "end"))
        else:
            o.append(G(box(20, yy - 2, 28, 24, WHITE2), frame(20, yy - 2, 28, 24, PLUM, 2, 4)))
            o.append(T(58, yy + 16, s, "b", 16))
            o.append(T(370, yy + 16, "Låst", "b", 14, PLUM, "end"))
    # Frist
    y = 612
    o.append(G(R(20, y, 350, 2, PLUM)))
    o.append(T(20, y + 26, "Neste frist", "pb", 20))
    o.append(T(370, y + 26, "Spillfrist ti. 8. des", "bb", 16, PLUM, "end"))
    o.append(para(20, y + 48, "Ved fristen spiller KI-spillere ferdig alle spill som ikke er ferdige.", 350, "b", 15, 20))
    y = 712
    o.append(T(20, y, "Labtimer, Datalab A2", "pb", 20))
    labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    for i, l in enumerate(labs):
        o.append(T(20 + (i % 2) * 180, y + 26 + (i // 2) * 24, l, "b", 16))
    o.append(T(20, y + 92, "Melding fra Bård: Husk Labtime torsdag.", "bb", 15))
    return "".join(o)


def build_04():
    o = []
    o.append(pframe(student_reg(), 80, 34, top=PLUM))
    o.append(pframe(student_home(), 530, 34, top=WHITE))
    return write_svg("04-student-hjem", 1000, 900, "Sara på mobil, første møte og hjem",
                     "Venstre: Invitasjon og registrering. Høyre: hjem under spill med Spill 17, Rolle, setene, seks steg, "
                     "neste frist, Labtimer og beskjed om at spillet venter på deg.", "".join(o))


# =================================== 08 OVERSIKT ==============================================
def status_tile(x, y, g, s=76):
    st = g["status"]
    near = g.get("ventet_timer", 0) >= 23
    fill = COR if near else (PLUM2 if st == "ferdig" else PLUM)
    p = [box(x, y, s, s, fill, 4)]
    fg = PLUM if near else WHITE
    if st == "ferdig":
        p.append(sprite(x + 44, y + 8, CHECK, 3, {"C": "T"}))
    elif st == "pågår":
        p.append(R(x + 8, y + 56, 60, 8, TINT))
        p.append(sprite(x + 20, y + 40, CRATE, 4))
        p.append(sprite(x + 38, y + 40, CRATE, 4))
    elif st == "pauset":
        p.append(sprite(x + 26, y + 32, PAUSE, 4))
    elif st == "venter":
        if near:
            p.append(frame(x - 4, y - 4, s + 8, s + 8, WHITE, 4, 4))
        p.append(sprite(x + 56, y + 6, HOUR, 3, {"Y": "P"} if near else None))
    if g.get("ki_seter") and not near:
        rx, ry = (x + 46, y + 40) if st == "ferdig" else (x + 50, y + 8) if st == "pågår" else (x + 54, y + 52)
        p.append(sprite(rx, ry, ROBOT, 2))
    out = [G(*p)]
    out.append(T(x + 7, y + 23, g["spill"], "sb", 16, fg))
    if st == "ferdig":
        out.append(T(x + 8, y + 66, "Ferdig", "b", 13, TINT))
    if st == "venter":
        out.append(T(x + 8, y + 45, g["navn"], "bb", 13, fg))
        out.append(T(x + 8, y + 66, f"{g['ventet_timer']} t", "bb", 16, fg))
    return "".join(out)


def build_08():
    games = GAMES
    o = [teacher_head(1600, "Kontrollrom", "IBE160, class-of-1994. Oppdatert for 3 s siden")]
    # filter
    y = 84
    filt = [("Alle 60", True), ("Venter 4", False), ("Pauset 2", False), ("Pågår 13", False), ("Ferdig 41", False),
            ("Med KI-sete", False), ("Nær overtakelse 1", False)]
    x = 28
    o.append(T(x, y + 26, "Filtrering", "bb", 14))
    x += 80
    for lab, on in filt:
        w = int(tw(lab, "bb", 15) + 34)
        if on:
            o.append(G(box(x, y + 2, w, 36, PLUM)))
            o.append(T(x + w / 2, y + 26, lab, "bb", 15, WHITE, "middle"))
        else:
            o.append(G(box(x, y + 2, w, 36, WHITE), frame(x, y + 2, w, 36, PLUM, 2, 4)))
            o.append(T(x + w / 2, y + 26, lab, "bb", 15, PLUM, "middle"))
        x += w + 6

    # Monitorvegg
    wx, wy = 28, 134
    o.append(G(box(wx, wy, 800, 512, PLUM, 8)))
    o.append(T(wx + 16, wy + 26, "Alle 60 Klassespill", "pb", 20, WHITE))
    o.append(T(wx + 784, wy + 26, "41 ferdig, 15 pågår (2 pauset), 4 venter", "b", 15, TINT, "end"))
    for i, g in enumerate(games):
        c, r = i % 10, i // 10
        o.append(status_tile(wx + 12 + c * 78, wy + 38 + r * 78, g))
    # Tegnforklaring
    ly = 660
    leg = [("Ferdig", sprite(wx, ly, CHECK, 3, {"C": "L"})), ("Pågår", sprite(wx, ly, CRATE, 5)), ("Pauset", sprite(wx, ly, PAUSE, 3, {"C": "P"})),
           ("Venter, navn og tid", sprite(wx, ly, HOUR, 3, {"Y": "P"})), ("KI i sete", sprite(wx, ly, ROBOT, 2, {"C": "P", "P": "W"}))]
    x = wx
    for lab, sp in leg:
        o.append(G(f'<g transform="translate({x - wx},0)">{sp}</g>'))
        o.append(T(x + 28, ly + 15, lab, "b", 14))
        x += 28 + int(tw(lab, "b", 14)) + 28
    o.append(G(box(x, ly, 18, 18, COR, 2)))
    o.append(T(x + 24, ly + 15, "Nær overtakelse", "bb", 14))

    # Trakt
    fy = 704
    o.append(T(28, fy, "Trakt for hele Klasseøkten", "pb", 20))
    fun = [("Registrert", "registrert"), ("Klassespill ferdig", "klassespill_ferdig"), ("Debrief ferdig", "debrief_ferdig"),
           ("Quiz bestått", "quiz_bestått"), ("Replay ferdig", "replay_ferdig"), ("Test levert", "test_levert"),
           ("KI-vurdering klar", "ki_vurdering_klar")]
    for i, (lab, key) in enumerate(fun):
        yy = fy + 14 + i * 36
        v = F["funnel"][key]
        o.append(T(28, yy + 19, lab, "b", 15))
        bw = int(v / 240 * 540 / 4) * 4
        o.append(G(R(180, yy + 2, 540, 24, WHITE2), R(180, yy + 2, bw, 24, PLUM)))
        o.append(T(730, yy + 21, v, "sb", 16))
    # Tabell
    tx = 852
    twd = 720
    o.append(G(box(tx, 134, twd, 96, COR)))
    o.append(G(sprite(tx + 16, 150, HOUR, 4, {"Y": "P"})))
    o.append(T(tx + 52, 164, "Spill 2 venter på Noah (Grossist) i 23 t", "pb", 24))
    o.append(T(tx + 52, 194, "KI overtar om 1 t. Andre Seter har bestilt.", "b", 16))
    o.append(btn(tx + 490, 182, 214, 40, "Send Melding til Noah", "mork", 15, "bb"))

    cols = [("Spill", 0, "start"), ("Status", 56, "start"), ("Venter på", 160, "start"), ("Tid", 374, "end"), ("Uke", 424, "end"),
            ("Kost, kr", 500, "end"), ("KI", 548, "end"), ("Handling", 566, "start")]
    hy = 258
    for lab, dx, a in cols:
        o.append(T(tx + dx, hy, lab, "bb", 14, PLUM, a if a != "start" else None))
    o.append(G(R(tx, hy + 7, twd, 2, PLUM)))
    order = sorted([g for g in games if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])
    order += [g for g in games if g["status"] == "pauset"]
    order += [g for g in games if g["status"] == "pågår"]
    y = hy + 24
    rh = 30
    for j, g in enumerate(order):
        yy = y + j * rh
        if j % 2:
            o.append(G(R(tx, yy - 20, twd, rh, WHITE2)))
        o.append(T(tx + 4, yy, g["spill"], "bb", 15))
        st = g["status"]
        ic = {"venter": sprite(tx + 56, yy - 14, HOUR, 2, {"Y": "P"}),
              "pauset": sprite(tx + 56, yy - 13, PAUSE, 2, {"C": "P"}),
              "pågår": sprite(tx + 56, yy - 12, CRATE, 3, {"W": "P", "Y": "P"})}[st]
        o.append(G(ic))
        o.append(T(tx + 72, yy, st.capitalize(), "b", 15))
        if st == "venter":
            o.append(T(tx + 160, yy, f"{g['navn']} ({g['venter_paa']})", "b", 15))
            o.append(T(tx + 374, yy, f"{g['ventet_timer']} t", "bb", 15, PLUM, "end"))
        elif st == "pauset":
            o.append(T(tx + 160, yy, f"Fortsetter {g['fortsetter']}", "b", 15))
            o.append(T(tx + 374, yy, "–", "b", 15, PLUM, "end"))
        else:
            if g["spill"] == 17:
                o.append(T(tx + 160, yy, "Jonas og Sara", "b", 15))
                o.append(T(tx + 374, yy, "3 min", "b", 15, PLUM, "end"))
            else:
                o.append(T(tx + 160, yy, "Bestiller nå", "b", 15))
                o.append(T(tx + 374, yy, "–", "b", 15, PLUM, "end"))
        o.append(T(tx + 424, yy, g["uke"], "b", 15, PLUM, "end"))
        o.append(T(tx + 500, yy, f"{g['kjedekost']:,}".replace(",", " "), "b", 15, PLUM, "end"))
        o.append(T(tx + 548, yy, g["ki_seter"] if g["ki_seter"] else "–", "bb" if g["ki_seter"] else "b", 15, PLUM, "end"))
        o.append(T(tx + 566, yy, "Melding", "bb", 14))
        o.append(G(R(tx + 566, yy + 3, 50, 1, PLUM)))
    yend = y + len(order) * rh
    o.append(G(R(tx, yend - 14, twd, 2, PLUM)))
    o.append(T(tx + 4, yend + 8, "41 ferdige spill er skjult i tabellen", "b", 15))
    o.append(T(tx + 566, yend + 8, "Vis alle", "bb", 14))
    o.append(G(R(tx + 566, yend + 11, 50, 1, PLUM)))

    # Melding
    my = yend + 30
    o.append(T(tx, my + 12, "Send Melding", "pb", 20))
    for i, (lab, on) in enumerate([("Hele Klasseøkten", False), ("Ett spill", True), ("Én student", False)]):
        xx = tx + 140 + i * 158
        o.append(G(box(xx, my - 12, 150, 34, PLUM if on else WHITE), frame(xx, my - 12, 150, 34, PLUM, 2, 4)))
        o.append(T(xx + 75, my + 10, lab, "bb", 14, WHITE if on else PLUM, "middle"))
    o.append(G(box(tx, my + 30, 590, 44, WHITE), frame(tx, my + 30, 590, 44, PLUM, 2, 4)))
    o.append(T(tx + 14, my + 58, "Spill 2: Husk ordren for Uke 19, Noah.", "b", 15))
    o.append(btn(tx + 600, my + 30, 120, 44, "Send", "pri", 16))
    return write_svg("08-laerer-oversikt", 1600, 1000, "Kontrollrom for 60 Klassespill",
                     "Monitorvegg med 60 pikselvinduer for status, ærlig tabell med hvem hvert spill venter på og hvor lenge, "
                     "Spill 2 uthevet like før KI overtar, trakt, Filtrering og Send Melding.", "".join(o), WHITE)


# =================================== 09 ALLE SIDER ============================================
def mini_lines(x, y, w, n, col=PLUM2, gap=10, h=4):
    return "".join(R(x, y + i * gap, w if i < n - 1 else w * .6, h, col) for i in range(n))


def phone_mini(x, y, draw, w=170, h=300):
    inner = draw(x + 6, y + 6, w - 12, h - 12)
    return G(box(x, y, w, h, PLUM, 6), box(x + 6, y + 6, w - 12, h - 12, WHITE, 2)) + inner


def wide_mini(x, y, draw, w=280, h=170):
    inner = draw(x + 6, y + 6, w - 12, h - 12)
    return G(box(x, y, w, h, PLUM, 6), box(x + 6, y + 6, w - 12, h - 12, WHITE, 2)) + inner


def m_invite(x, y, w, h):
    return G(R(x, y, w, h * .3, PLUM), sprite(x + 12, y + 14, MAIL, 4), box(x + 10, y + 120, w - 20, 28, WHITE2),
             box(x + 10, y + 156, w - 20, 28, WHITE2), box(x + 10, y + 210, w - 20, 36, YEL), mini_lines(x + 10, y + 98, w - 40, 1))


def m_login(x, y, w, h):
    return G(sprite(x + 50, y + 28, GROSSIST, 5), box(x + 10, y + 112, w - 20, 28, WHITE2), box(x + 10, y + 150, w - 20, 28, WHITE2),
             box(x + 10, y + 200, w - 20, 36, YEL))


def m_rules(x, y, w, h):
    return G(R(x, y, w, 76, PLUM), belt_strip(x, y + 54, w), sprite(x + 12, y + 42, CRATE, 4), sprite(x + 60, y + 42, CRATE, 4),
             mini_lines(x + 10, y + 92, w - 20, 6), box(x + 10, y + 212, w - 20, 36, YEL))


def m_start(x, y, w, h):
    return G(mini_lines(x + 10, y + 16, w - 20, 3), R(x + 10, y + 66, w - 20, 72, WHITE2), box(x + 20, y + 110, 26, 22, PLUM), box(x + 56, y + 90, 26, 42, PLUM),
             box(x + 92, y + 100, 26, 32, PLUM), box(x + 10, y + 156, 40, 40, WHITE2), box(x + 58, y + 156, 40, 40, YEL), box(x + 106, y + 156, 40, 40, WHITE2),
             box(x + 10, y + 216, w - 20, 36, YEL))


def m_replay(x, y, w, h):
    return G(R(x, y, w, 110, PLUM), belt_strip(x, y + 84, w), stack(x + 12, y + 80, 8), stack(x + 90, y + 80, 4),
             sprite(x + 8, y + 8, ROBOT, 2), sprite(x + 56, y + 8, ROBOT, 2), sprite(x + 104, y + 8, ROBOT, 2),
             mini_lines(x + 10, y + 124, w - 20, 3), box(x + 12, y + 172, 40, 66, PLUM), box(x + 58, y + 172, 40, 66, PLUM), circle(x + 128, y + 204, 22, 2, COR))


def m_replay_rev(x, y, w, h):
    bars = "".join(R(x + 12 + i * 5, y + 90 - v * 2, 4, v * 2, PLUM) for i, v in enumerate([4, 4, 6, 9, 14, 20, 17, 12, 9, 7, 8, 6, 6, 5, 4, 4, 5, 4, 4, 4, 4, 4, 5, 4, 4]))
    return G(bars, R(x + 12, y + 92, 126, 2, PLUM), box(x + 10, y + 104, w - 20, 72, WHITE2), mini_lines(x + 18, y + 116, w - 40, 4), sprite(x + 12, y + 190, ROBOT, 2), mini_lines(x + 40, y + 192, 100, 2))


def m_test(x, y, w, h):
    o = [mini_lines(x + 10, y + 12, w - 20, 2)]
    for i in range(3):
        o.append(frame(x + 10, y + 36 + i * 22, 14, 14, PLUM, 2, 0) + R(x + 32, y + 40 + i * 22, 100, 4, PLUM2))
    o.append(R(x + 10, y + 104, w - 20, 66, WHITE2))
    for i in range(5):
        o.append(R(x + 16 + i * 26, y + 160 - (i + 2) * 7, 18, (i + 2) * 7, CY))
    o.append(box(x + 10, y + 180, w - 20, 62, WHITE2) + mini_lines(x + 18, y + 192, w - 40, 4))
    return G(*o)


def m_ki(x, y, w, h):
    return G(box(x + 10, y + 12, w - 20, 44, CY), sprite(x + 16, y + 18, ROBOT, 3), mini_lines(x + 10, y + 70, w - 20, 8),
             box(x + 10, y + 172, w - 20, 70, WHITE2), mini_lines(x + 18, y + 184, w - 40, 4))


def m_report(x, y, w, h):
    return G(sprite(x + 12, y + 12, FILE, 8, {"W": "T", "P": "P"}), mini_lines(x + 76, y + 18, 66, 4), mini_lines(x + 10, y + 100, w - 20, 5), box(x + 10, y + 170, w - 20, 26, WHITE2), box(x + 10, y + 208, w - 20, 36, YEL))


def m_allgames(x, y, w, h):
    o = []
    for i in range(6):
        for j in range(4):
            o.append(R(x + 10 + j * 36, y + 12 + i * 44, 30, 36, PLUM if (i + j) % 3 else PLUM2))
            hh = ((i * 7 + j * 5) % 20) + 4
            o.append(R(x + 14 + j * 36, y + 44 + i * 44 - hh, 22, hh, YEL))
    return G(*o)


def m_home(x, y, w, h):
    o = [R(x, y, w, 26, PLUM)]
    for i in range(3):
        o.append(box(x + 10 + i * 88, y + 40, 80, 56, WHITE2) + sprite(x + 18 + i * 88, y + 52, CRATE, 6) + R(x + 44 + i * 88, y + 58, 34, 4, PLUM2) + R(x + 44 + i * 88, y + 70, 24, 4, PLUM2))
    o.append(box(x + 10, y + 110, 120, 30, YEL))
    return G(*o)


def m_classrep(x, y, w, h):
    bars = [8, 12, 16, 22, 28, 20, 14]
    o = ["".join(R(x + 12 + i * 16, y + 90 - v * 2, 12, v * 2, PLUM) for i, v in enumerate(bars)),
         "".join(R(x + 140, y + 16 + i * 16, [110, 84, 60, 44][i], 10, [PLUM, PLUM2, PLUM2, PLUM2][i]) for i in range(4)),
         mini_lines(x + 12, y + 104, w - 30, 4)]
    return G(*o)


def m_insight(x, y, w, h):
    o = []
    for r in range(4):
        vals = [WEEKS[k]["seats"][ROLES[r]]["ordre"] for k in range(36)]
        o.append("".join(R(x + 12 + k * 6, y + 34 + r * 34 - v, 5, v, YEL if r == 1 else PLUM) for k, v in enumerate(vals) if v))
    o.append(R(x + 12 + 10 * 6, y + 2, 2, 140, COR))
    return G(*o)


def m_student(x, y, w, h):
    return G(sprite(x + 12, y + 12, PERSON, 4), mini_lines(x + 56, y + 16, 120, 3), box(x + 12, y + 62, 80, 76, WHITE2), box(x + 100, y + 62, 80, 76, WHITE2), box(x + 188, y + 62, 66, 76, WHITE2),
             mini_lines(x + 20, y + 74, 60, 4), mini_lines(x + 108, y + 74, 60, 4), mini_lines(x + 196, y + 74, 46, 4))


def m_plenum(x, y, w, h):
    o = [R(x, y, w, h, PLUM)]
    for i in range(4):
        for j in range(8):
            hh = (i * 11 + j * 7) % 22 + 6
            o.append(R(x + 8 + j * 32, y + 8 + i * 37 + 32 - hh, 26, hh, YEL if (i + j) % 5 else COR))
    return G(*o)


def m_cross(x, y, w, h):
    o = []
    for j, ser in enumerate([[60, 72, 66, 80], [40, 48, 56, 62], [20, 30, 28, 38]]):
        o.append("".join(R(x + 12 + j * 84 + i * 18, y + 110 - v, 14, v, [PLUM, PLUM2, CY][i % 3]) for i, v in enumerate(ser)))
    o.append(mini_lines(x + 12, y + 122, w - 30, 2))
    return G(*o)


def m_msg(x, y, w, h):
    o = []
    for i in range(3):
        o.append(R(x + 10, y + 10 + i * 36, 110, 30, WHITE2) + sprite(x + 16, y + 16 + i * 36, MAIL, 2) + R(x + 46, y + 20 + i * 36, 64, 4, PLUM2))
    o.append(box(x + 128, y + 10, 130, 106, WHITE2) + mini_lines(x + 136, y + 22, 110, 6) + box(x + 196, y + 122, 62, 24, YEL))
    return G(*o)


def m_testgame(x, y, w, h):
    return G(R(x, y, w, h, PLUM), belt_strip(x, y + 94, w), stack(x + 12, y + 90, 12), stack(x + 90, y + 90, 4), stack(x + 170, y + 90, 8),
             sprite(x + 14, y + 8, ROBOT, 2), sprite(x + 64, y + 8, ROBOT, 2), sprite(x + 114, y + 8, ROBOT, 2), sprite(x + 164, y + 8, PERSON, 3), box(x + 12, y + 118, 110, 24, YEL))


def m_admin(x, y, w, h):
    o = [R(x, y, 60, h, PLUM)]
    o.append("".join(R(x + 8, y + 12 + i * 20, 44, 8, TINT) for i in range(5)))
    o.append(box(x + 72, y + 12, 86, 60, WHITE2) + box(x + 166, y + 12, 86, 60, WHITE2) + mini_lines(x + 72, y + 90, 180, 3))
    return G(*o)


def m_users(x, y, w, h):
    o = []
    for i in range(6):
        o.append(R(x + 10, y + 8 + i * 24, 240, 20, WHITE2 if i % 2 else WHITE) + sprite(x + 14, y + 10 + i * 24, PERSON, 2) + R(x + 40, y + 16 + i * 24, 90, 4, PLUM2) + box(x + 180, y + 10 + i * 24, 60, 16, CY if i % 3 else YEL, 2))
    return G(*o)


def m_cost(x, y, w, h):
    vals = [12, 16, 22, 18, 30, 44, 36, 52, 28, 20, 14, 10]
    return G("".join(R(x + 12 + i * 20, y + 100 - v, 16, v, PLUM) for i, v in enumerate(vals)), R(x + 12, y + 44, 240, 2, COR),
             R(x + 12, y + 102, 240, 2, PLUM), mini_lines(x + 12, y + 114, 200, 2))


def m_game(x, y, w, h):
    return G(R(x, y, w, 150, PLUM), belt_strip(x, y + 96, w), stack(x + 8, y + 92, 8), stack(x + 88, y + 92, 4), box(x + 10, y + 166, 40, 70, PLUM), box(x + 54, y + 166, 40, 70, PLUM), circle(x + 128, y + 200, 24, 2, COR))


def build_09():
    o = [T(40, 56, "Alle andre sider i Pikselkjeden", "pb", 40)]
    o.append(T(40, 86, "Lav detalj. Samme bånd, samme figurer, samme fem farger. Lærerflatene holder dataene i ren tekst.", "b", 18))
    o.append(demodata(1960, 40, PLUM, "end", 16))
    # Student
    student = [("Invitasjon og registrering", "Lenke fra e-post, velg passord.", m_invite),
               ("Logg inn", "E-post og passord. Ingen åpen registrering.", m_login),
               ("Regler før første ordre", "Båndet forklart på én skjerm.", m_rules),
               ("Startoppgave", "Gjett utviklingen, teller ikke.", m_start),
               ("Replay", "Én runde til, mot tre KI-spillere.", m_replay),
               ("Replay-gjennomgang", "Kjøringen din og KI-tekst, merket.", m_replay_rev),
               ("Individuell test", "Flervalg, tegne- og tabelloppgave, langsvar.", m_test),
               ("KI-vurdering", "Teller ikke, er ingen karakter. Står øverst.", m_ki),
               ("Studentrapport (PDF)", "Forklaring, øyeblikk, resultat. Last ned.", m_report),
               ("Alle spill side om side", "Etter Debrief: alle kjeder, uten navn.", m_allgames)]
    o.append(T(40, 136, "Student", "pb", 28))
    for i, (t, d, fn) in enumerate(student):
        c, r = i % 5, i // 5
        x, y = 40 + c * 200, 152 + r * 424
        o.append(phone_mini(x, y, fn))
        o.append(para(x, y + 322, t, 176, "bb", 15, 19))
        lines = plines(t, 176, "bb", 15)
        o.append(para(x, y + 322 + lines * 19, d, 176, "b", 14, 18))
    # Admin nederst til venstre
    o.append(T(40, 1040, "Admin", "pb", 28))
    admin = [("Admin-område", "Klasser, drift og tilstand.", m_admin), ("Brukere og roller", "Faglærer, assistent, admin.", m_users),
             ("KI-kostnad", "Forbruk per Klasseøkt, med tak.", m_cost)]
    for i, (t, d, fn) in enumerate(admin):
        x, y = 40 + i * 320, 1056
        o.append(wide_mini(x, y, fn))
        o.append(T(x, y + 196, t, "bb", 16))
        o.append(para(x, y + 216, d, 280, "b", 15, 19))
    # Faglærer
    fx = 1080
    o.append(T(fx, 136, "Faglærer", "pb", 28))
    teach = [("Lærerhjem med klasser", "Alle Klasser og hva som haster.", m_home),
             ("Klasserapport", "Trakt, kost per Rolle, forsterkning.", m_classrep),
             ("Spillinnsikt, uke for uke", "Ett spill, alle Seter, KI-uker merket.", m_insight),
             ("Studentside", "Forklaring, quiz-forsøk, test.", m_student),
             ("Alle spill side om side", "For plenum, uten navn.", m_plenum),
             ("Tverrklasse-statistikk", "Samme mål over flere kull.", m_cross),
             ("Meldinger", "Til alle, ett spill eller én student.", m_msg),
             ("Lærers testspill", "Prøv selv med tre KI-spillere.", m_testgame)]
    for i, (t, d, fn) in enumerate(teach):
        c, r = i % 3, i // 3
        x, y = fx + c * 300, 152 + r * 390
        o.append(wide_mini(x, y, fn))
        o.append(T(x, y + 196, t, "bb", 16))
        o.append(para(x, y + 216, d, 276, "b", 15, 19))
    # Et lite hint om hovedspillet i siste celle
    x, y = fx + 2 * 300, 152 + 2 * 390
    o.append(G(box(x, y, 280, 170, PLUM, 6), belt_strip(x + 6, y + 110, 268)))
    o.append(G(stack(x + 16, y + 106, 8), stack(x + 100, y + 106, 4), stack(x + 186, y + 106, 4)))
    o.append(T(x + 16, y + 34, "Samme bånd overalt", "pb", 20, WHITE))
    o.append(T(x + 16, y + 150, "Se 05, 06 og 07", "bb", 15, WHITE))
    return write_svg("09-alle-sider", 2000, 1400, "Kontaktark, alle andre sider",
                     "Skisser i lav detalj av alle andre sider gruppert per rolle: Student, Faglærer og Admin.", "".join(o))


# ==============================================================================================
if __name__ == "__main__":
    build_01()
    build_02()
    build_03()
    build_04()
    build_05()
    build_06()
    build_07()
    build_08()
    build_09()
    print("Laget 9 SVG-filer i", HERE)
