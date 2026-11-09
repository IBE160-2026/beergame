"""Konsept 10 Tråden. Bygger 9 SVG-er fra ../_shared/fixture.json. Kjør: uv run python build.py"""
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WEEKS = FX["weeks"]
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]

FONT = "'Schibsted Grotesk','Figtree','Segoe UI',system-ui,sans-serif"
IMPORT = "https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700;800;900&amp;display=swap"

# Mørk tråd (kveld på sofaen)
NIGHT, PANEL, RAISED, LINE = "#1E0E25", "#2C1735", "#3B2146", "#5A3566"
TXT, MUTE = "#F7EFF5", "#C8B5D0"
LIME, MINT, APR, KIC = "#CFF25A", "#86E8C2", "#FFB18A", "#CDBDFF"
INKD = "#1E0E25"
# Lys flate (faglærer, dagtid)
PAPER, CARD, LINEL = "#F6F0F3", "#FFFFFF", "#DFD2DE"
INK, MUTEL, PLUM = "#2A1231", "#64506C", "#4A2157"
URG, GOOD, KID = "#A5350F", "#0E6A49", "#54379F"
URGBG, LIMEBG = "#FBE7DD", "#EEF9C8"
# Diagramserier, validert mot mørk flate #2C1735 (scripts/validate_palette.js)
SER = {"Detaljist": "#3A9FC2", "Grossist": "#86A218", "Distributør": "#9A76EE", "Fabrikk": "#E06A34"}

ICONS = {
    "truck": "M2 6h12v10H2z M14 10h4l3.5 3.2V16H14 M8.5 18a2 2 0 1 1-4 0a2 2 0 1 1 4 0 M19 18a2 2 0 1 1-4 0a2 2 0 1 1 4 0",
    "inbox": "M4 5h4 M16 5h4v14H4V5 M4 13.5h5l1.5 2.5h3l1.5-2.5h5 M12 3v8 M9 8l3 3 3-3",
    "boxout": "M4 10h16v10H4z M6 10l1.6-4h8.8L18 10 M12 17.5v-5 M9.5 15l2.5-2.5 2.5 2.5",
    "lock": "M6 11h12v9H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3",
    "check": "M5 12.5l4.5 4.5L19 7.5",
    "clock": "M21 12a9 9 0 1 1-18 0a9 9 0 1 1 18 0 M12 7v5l3.2 2",
    "pause": "M8 5v14 M16 5v14",
    "play": "M7 4.5l12 7.5-12 7.5z",
    "send": "M4 12h15 M13 6l6 6-6 6",
    "back": "M9 5h12v14H9l-6.5-7z M12.5 9.5l5 5 M17.5 9.5l-5 5",
    "file": "M6 3h8l4 4v14H6z M14 3v4h4",
    "mail": "M3 6h18v13H3z M3 7l9 6.5L21 7",
    "users": "M15 9a3.5 3.5 0 1 1-7 0a3.5 3.5 0 1 1 7 0 M4.5 20c.8-4 3.5-6 7-6s6.2 2 7 6",
    "warn": "M12 4l9 16H3z M12 10v5 M12 17.6v.4",
    "search": "M17 11a6 6 0 1 1-12 0a6 6 0 1 1 12 0 M15.5 15.5L20 20",
    "x": "M6 6l12 12 M18 6L6 18",
    "cal": "M4 6h16v14H4z M4 10.5h16 M8.5 3v5 M15.5 3v5",
    "redo": "M19 12a7 7 0 1 1-2.2-5.1 M19.5 3.5v4.2h-4.2",
    "doc": "M6 3h12v18H6z M9 8h6 M9 12h6 M9 16h4",
    "chart": "M4 4v16h16 M8 15l3.5-4 3 2.5L19 8",
    "home": "M4 11l8-7 8 7 M6 10v10h12V10",
    "grid": "M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z",
    "pen": "M4 20l1-4L16 5l3 3L8 19z",
    "flag": "M6 21V4 M6 5h12l-3 4 3 4H6",
    "reply": "M9 7L4 12l5 5 M4 12h10a6 6 0 0 1 6 6",
    "hour": "M7 3h10 M7 21h10 M8 3c0 5 8 6 8 9s-8 4-8 9 M16 3c0 5-8 6-8 9s8 4 8 9",
}


def esc(s):
    """Escaper tekst og gir bare sifferløp tabellsifre (fonten gjør også komma tabellbredt)."""
    return re.sub(r"\d+", lambda m: f'<tspan class="c10-n">{m.group(0)}</tspan>', escape(s))


def fmt_num(v, dec=2):
    s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def kr(v):
    return fmt_num(v) + " kr"


def seat(role, week):
    return WEEKS[week - 1]["seats"][role]


def sara(week):
    return seat("Grossist", week)


def orders(role):
    return [w["seats"][role]["ordre"] for w in WEEKS]


def est(s, sz, bold=False):
    plain = s.replace("**", "")
    return len(plain) * sz * (0.545 if bold else 0.515)


def wrap(s, width, sz, bold=False):
    """Manuell linjebryting. Beholder **fet** tvers over linjer."""
    lines, cur, open_b = [], [], False
    for word in s.split(" "):
        tentative = " ".join(cur + [word])
        if cur and est(tentative, sz, bold) > width:
            line = " ".join(cur)
            if open_b:
                line += "**"
            lines.append(line)
            cur = ["**" + word] if open_b else [word]
            if word.count("**") % 2 == 1:
                open_b = not open_b
            continue
        cur.append(word)
        if word.count("**") % 2 == 1:
            open_b = not open_b
    if cur:
        lines.append(" ".join(cur))
    return lines


class Page:
    def __init__(self, side, w, h, title, desc, bg):
        self.side, self.w, self.h, self.title, self.desc, self.bg = side, w, h, title, desc, bg
        self.o, self.n = [], 0

    def add(self, s):
        self.o.append(s)

    def uid(self, name="u"):
        self.n += 1
        return f"c10-{self.side}-{name}{self.n}"

    def r(self, x, y, w, h, rx=0, fill="none", st=None, sw=1, dash=None, op=None, extra=""):
        a = f'x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"'
        if rx:
            a += f' rx="{rx}"'
        if st:
            a += f' stroke="{st}" stroke-width="{sw}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if op is not None:
            a += f' opacity="{op}"'
        self.add(f"<rect {a} {extra}/>")

    def c(self, x, y, r, fill="none", st=None, sw=1, dash=None, extra=""):
        a = f'cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"'
        if st:
            a += f' stroke="{st}" stroke-width="{sw}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        self.add(f"<circle {a} {extra}/>")

    def l(self, x1, y1, x2, y2, st=LINE, sw=1, dash=None, extra=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{sw}"{d} {extra}/>')

    def path(self, d, fill="none", st=None, sw=1, extra=""):
        s = f' stroke="{st}" stroke-width="{sw}"' if st else ""
        self.add(f'<path d="{d}" fill="{fill}"{s} {extra}/>')

    def t(self, x, y, s, sz=15, w=400, fill=TXT, a="start", bw=700, bfill=None, ls=None, extra=""):
        attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{sz}" font-weight="{w}" fill="{fill}"'
        if a != "start":
            attrs += f' text-anchor="{a}"'
        if ls is not None:
            attrs += f' letter-spacing="{ls}"'
        body = ""
        parts = s.split("**")
        for i, part in enumerate(parts):
            if not part:
                continue
            if i % 2:
                f2 = f' fill="{bfill}"' if bfill else ""
                body += f'<tspan font-weight="{bw}"{f2}>{esc(part)}</tspan>'
            else:
                body += esc(part)
        self.add(f"<text {attrs} {extra}>{body}</text>")

    def para(self, x, y, s, width, sz=15, lh=None, **kw):
        lh = lh or round(sz * 1.38)
        bold = kw.get("w", 400) >= 600
        lines = wrap(s, width, sz, bold)
        for i, line in enumerate(lines):
            self.t(x, y + i * lh, line, sz, **kw)
        return y + len(lines) * lh

    def icon(self, x, y, name, size=20, color=TXT, sw=1.9, fill="none"):
        k = size / 24
        self.add(
            f'<path transform="translate({x:.1f} {y:.1f}) scale({k:.3f})" d="{ICONS[name]}" fill="{fill}" '
            f'stroke="{color}" stroke-width="{sw / k:.2f}" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    def role(self, cx, cy, role, s=7, fill=None, st=TXT, sw=1.6):
        fill = fill or "none"
        if role == "Detaljist":
            self.c(cx, cy, s, fill, st, sw)
        elif role == "Grossist":
            self.path(f"M{cx} {cy - s * 1.2}L{cx + s * 1.2} {cy}L{cx} {cy + s * 1.2}L{cx - s * 1.2} {cy}Z", fill, st, sw)
        elif role == "Distributør":
            self.path(f"M{cx} {cy - s * 1.1}L{cx + s * 1.15} {cy + s * .85}L{cx - s * 1.15} {cy + s * .85}Z", fill, st, sw)
        else:
            self.r(cx - s * .92, cy - s * .92, s * 1.84, s * 1.84, 1, fill, st, sw)

    def hexa(self, cx, cy, s, fill, st=None):
        pts = f"M{cx - s} {cy}L{cx - s * .5} {cy - s * .9}L{cx + s * .5} {cy - s * .9}L{cx + s} {cy}L{cx + s * .5} {cy + s * .9}L{cx - s * .5} {cy + s * .9}Z"
        self.path(pts, fill, st, 1.2)

    def ki(self, x, y, s=9, dark=True):
        """Sekskantet KI-merke, alltid med bokstavene."""
        self.hexa(x, y, s + 1, KIC if dark else KID)
        self.t(x, y + s * .42, "KI", s * 1.15, 800, INKD if dark else "#FFFFFF", "middle", ls=.2)

    def kitag(self, x, y, label="KI-generert, kan ta feil", dark=True, sz=13):
        self.ki(x + 9, y - 4.5, 9, dark)
        self.t(x + 24, y, label, sz, 600, KIC if dark else KID)

    def pips(self, x, y, groups, pw=7, gap=1.6, ggap=5, h=None):
        """Kasser som firkanter. kind: hollow (på vei), solid (lager), slash (restordre), lime (tastet)."""
        h = h or pw
        cx = x
        for n, kind in groups:
            for _ in range(n):
                if kind == "hollow":
                    self.r(cx + .5, y + .5, pw - 1, h - 1, 1, "none", MINT, 1.1)
                elif kind == "lime":
                    self.r(cx, y, pw, h, 1, LIME)
                elif kind == "slash":
                    self.r(cx + .5, y + .5, pw - 1, h - 1, 1, "none", APR, 1.1)
                    self.l(cx + 1, y + h - 1, cx + pw - 1, y + 1, APR, 1.1)
                elif kind == "done":
                    self.r(cx, y, pw, h, 1, LINE)
                elif kind == "darkhollow":
                    self.r(cx + .5, y + .5, pw - 1, h - 1, 1, "none", INKD, 1.1)
                else:
                    self.r(cx, y, pw, h, 1, TXT)
                cx += pw + gap
            cx += ggap - gap
        return cx

    def save(self, name):
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" font-family="{FONT}" class="c10-root">'
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>"
            f"<style>@import url('{IMPORT}');.c10-n{{font-variant-numeric:tabular-nums lining-nums;font-feature-settings:'tnum' 1,'lnum' 1;}}</style>"
            f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>'
        )
        (HERE / name).write_text(head + "".join(self.o) + "</svg>", encoding="utf-8")


def wordmark(p, x, y, color=TXT, sz=22, dot=LIME):
    """Merket: en tråd med to meldinger og en grønn kvittering."""
    k = sz / 22
    p.l(x + 6 * k, y - 18 * k, x + 6 * k, y + 4 * k, color, 2)
    p.c(x + 6 * k, y - 15 * k, 3.4 * k, color)
    p.c(x + 6 * k, y - 6 * k, 3.4 * k, color)
    p.r(x + 2 * k, y, 8 * k, 8 * k, 1.5, dot)
    p.t(x + 18 * k, y + 1 * k, "Tråden", sz, 800, color, ls=-.2)


# ---------------------------------------------------------------- Tråd-elementer

def day(label):
    def draw(p, x, y, w):
        tw = est(label, 13) + 18
        p.l(x, y + 13, x + (w - tw) / 2, y + 13, LINE)
        p.l(x + (w + tw) / 2, y + 13, x + w, y + 13, LINE)
        p.t(x + w / 2, y + 18, label, 13, 500, MUTE, "middle")
    return (28, draw)


def sysm(icon, text, sz=15, tone=None):
    def draw(p, x, y, w):
        p.r(x, y, w - 34, 38, 11, PANEL)
        p.icon(x + 10, y + 9, icon, 20, tone or MINT)
        p.t(x + 38, y + 24.5, text, sz, 400, TXT, bw=800)
    return (41, draw)


def gap(n):
    return (n, lambda p, x, y, w: None)


def ticket_path(x, y, w, h, cut=13, rx=9):
    return (
        f"M{x + rx} {y}H{x + w - cut}L{x + w} {y + cut}V{y + h - rx}Q{x + w} {y + h} {x + w - rx} {y + h}"
        f"H{x + rx}Q{x} {y + h} {x} {y + h - rx}V{y + rx}Q{x} {y} {x + rx} {y}Z"
    )


def order(n, week, state="vei", when=None):
    """Egen ordreboble: fraktlapp med klippet hjørne. Tomme kasser til varene er kommet."""
    pw, g = 7, 1.5
    tw = max(168, 22 + n * (pw + g))
    h = 72 if n else 56

    def draw(p, x, y, w):
        bx = x + w - tw
        new = state == "ny"
        fill = LIME if new else RAISED
        ink = INKD if new else TXT
        mute = INKD if new else MUTE
        p.path(ticket_path(bx, y, tw, h), fill, None if new else LINE, 1)
        p.c(bx + tw - 21, y + 12, 2.6, NIGHT if new else NIGHT)
        p.t(bx + 12, y + 33, str(n), 28, 800, ink)
        nx = bx + 16 + est(str(n), 28, True) + 8
        p.icon(nx, y + 11, "lock", 14, ink, 2)
        p.t(nx + 18, y + 23, "Bestilt", 14, 700, ink)
        p.t(nx, y + 40, when or f"Uke {week}", 13, 400 if not new else 500, mute)
        if n:
            kind = {"ny": "darkhollow", "vei": "hollow", "kom": "done"}[state]
            p.pips(bx + 12, y + h - 18, [(n, kind)], pw, g)
    return (h + 8, draw)


def card(icon, title, body, kitag=None, action=None, ki=False, tone=None, sz=14, width=None):
    """Systemkort med tittel og tekst, og evt. knapp."""
    def height(w):
        tw = w - (width or 0)
        lines = len(wrap(body, tw - 26, sz)) if body else 0
        return 34 + lines * round(sz * 1.36) + (28 if kitag else 0) + (50 if action else 0) + 16

    class C:
        pass

    def draw(p, x, y, w):
        tw = w - (width or 0)
        h = height(w) - 8
        p.r(x, y, tw, h, 13, PANEL, tone or LINE, 1)
        if ki:
            p.ki(x + 21, y + 21, 9)
        else:
            p.icon(x + 11, y + 11, icon, 20, tone or MINT)
        p.t(x + 40, y + 26, title, 15, 700, TXT)
        ny = y + 45
        if body:
            ny = p.para(x + 13, y + 46, body, tw - 26, sz, lh=round(sz * 1.36), fill=TXT)
        if kitag:
            p.kitag(x + 13, ny + 8, kitag)
            ny += 26
        if action:
            p.r(x + 13, ny - 2, tw - 26, 40, 10, LIME)
            p.t(x + tw / 2, ny + 23, action, 15, 700, INKD, "middle")
    C.draw = draw
    return (None, draw, height)


def lay_thread(p, items, x, top, bottom, w, fade=NIGHT):
    """Bunnankret tråd, klippet mot toppen."""
    cid = p.uid("clip")
    p.add(f'<clipPath id="{cid}"><rect x="{x - 4}" y="{top}" width="{w + 8}" height="{bottom - top}"/></clipPath>')
    p.add(f'<g clip-path="url(#{cid})">')
    hs = []
    for it in items:
        anim = None
        if isinstance(it, dict):
            anim, it = it["anim"], it["it"]
        h = it[0] if it[0] is not None else it[2](w)
        hs.append((h, it[1], anim))
    y = bottom - sum(h for h, _, _ in hs)
    for h, fn, anim in hs:
        if anim:
            p.add(f"<g>{anim}")
        fn(p, x, y, w)
        if anim:
            p.add("</g>")
        y += h
    gid = p.uid("fade")
    p.add(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{fade}"/><stop offset="1" stop-color="{fade}" stop-opacity="0"/></linearGradient>')
    p.r(x - 4, top, w + 8, 34, 0, f"url(#{gid})")
    p.add("</g>")


def slide(begin, dur=9.0, span=.6, dy=16):
    """Glir inn og holder resten av løkka. Sluttilstanden er lesbar i stillstand."""
    a, b = begin / dur, (begin + span) / dur
    kt = f"0;{a:.3f};{b:.3f};1"
    return (
        f'<animateTransform attributeName="transform" type="translate" values="0 {dy};0 {dy};0 0;0 0" keyTimes="{kt}" dur="{dur}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;0;1;1" keyTimes="{kt}" dur="{dur}s" repeatCount="indefinite"/>'
    )


# ---------------------------------------------------------------- Spillskjerm

def pipe_groups(week):
    """På vei som grupper. Bruker de tre siste ordrene når de summerer til På vei."""
    pv = sara(week)["paa_vei_foer_ordre"]
    hist = orders("Grossist")[:week - 1]
    last = hist[-3:]
    if sum(last) == pv:
        return [(n, "hollow") for n in last if n]
    return [(pv, "hollow")]


def status_card(p, x, y, w, week, typed=None):
    s = sara(week)
    p.r(x, y, w, 132, 16, RAISED, LINE, 1)
    p.t(x + 13, y + 24, f"Uke {week}", 17, 800)
    p.t(x + w - 13, y + 24, f"Totalkostnad **{kr(s['kost_sum'])}**", 14, 400, MUTE, "end", bw=700, bfill=TXT)
    cols = [("Lager", s["lager"], "solid"), ("Restordre", s["restordre"], "slash"), ("På vei", s["paa_vei_foer_ordre"], "hollow")]
    cw = (w - 26) / 3
    for i, (lab, val, kind) in enumerate(cols):
        cx = x + 13 + i * cw
        p.pips(cx, y + 37, [(1, kind)], 9, 0)
        p.t(cx + 13, y + 45.5, lab, 13, 500, MUTE)
        col = APR if kind == "slash" and val else MINT if kind == "hollow" else TXT
        p.t(cx, y + 72, str(val), 26, 800, col)
    # kassene: på vei + det du taster, side om side
    groups = pipe_groups(week)
    n_total = sum(n for n, _ in groups) + (typed or 0)
    avail = w - 26 - (len(groups) + 1) * 5
    pitch = min(9.5, avail / max(n_total, 1))
    pw = max(pitch - 1.6, 3)
    groups = list(groups) + ([(typed, "lime")] if typed else [])
    p.pips(x + 13, y + 80, groups, pw, 1.6, 5, h=8)
    p.t(x + 13, y + 106, f"Ordre inn {s['innkommende_ordre']} · Levering {s['levering']} · Sendt {s['sendt']} · Neste levering {s['neste_levering']}", 13, 400, TXT)
    hist = orders("Grossist")[:week - 1][-10:]
    lab = "Dine ordrer" if week <= 11 else "Siste ordrer"
    p.t(x + 13, y + 124, f"{lab}  " + " ".join(str(v) for v in hist), 13, 400, MUTE, extra='xml:space="preserve"')
    return 132


def presence(p, x, y, rows, w=366):
    """rows: (rolle, navn, state, tekst). Tynne linjer med form + tekst."""
    for i, (role, name, state, text) in enumerate(rows):
        yy = y + i * 19
        if state == "done":
            p.icon(x, yy - 12, "check", 15, MINT, 2.4)
        elif state == "wait":
            p.icon(x, yy - 12, "clock", 15, APR, 2)
        elif state == "ki":
            p.ki(x + 7.5, yy - 4.5, 7)
        else:
            p.c(x + 7.5, yy - 4.5, 5, "none", MUTE, 1.5, "2 2")
        p.t(x + 21, yy, f"**{role}** {name} {text}" if name else f"**{role}** {text}", 13, 400, MUTE, bw=600, bfill=TXT)


def game_header(p, sub="Demodata · IBE160", title="Spill 17 · Grossist", right="Pause"):
    p.r(160, 11, 70, 5, 2.5, LINE)
    p.role(28, 49, "Grossist", 8, LIME, LIME)
    p.t(46, 47, title, 16, 800)
    p.t(46, 65, sub, 13, 400, MUTE)
    if right:
        p.r(306, 36, 72, 30, 15, "none", LINE, 1)
        p.icon(314, 43, "pause", 16, TXT, 2.2)
        p.t(332, 56, right, 13, 600)


def keypad(p, x, y, w, typed=None, dim=False):
    op = ' opacity=".45"' if dim else ""
    p.add(f"<g{op}>")
    # svarfelt + send
    fw = w - 134
    p.r(x, y, fw, 50, 12, PANEL, LIME if typed else LINE, 1.6 if typed else 1)
    if typed:
        p.t(x + 13, y + 33, str(typed), 25, 800)
        p.t(x + 20 + len(str(typed)) * 15.5, y + 33, "kasser", 14, 400, MUTE)
        p.icon(x + fw - 118, y + 18, "lock", 14, MUTE, 2)
        p.t(x + fw - 101, y + 30, "Låses ved send", 13, 400, MUTE)
    else:
        p.t(x + 13, y + 31, "Skriv et tall", 15, 400, MUTE)
    p.r(x + fw + 8, y, 126, 50, 12, LIME if typed else RAISED, None if typed else LINE)
    p.t(x + fw + 8 + 52, y + 31, "Send ordre", 15, 800, INKD if typed else MUTE, "middle")
    p.icon(x + fw + 8 + 98, y + 16, "send", 18, INKD if typed else MUTE, 2.4)
    # faste snarveier (samme hver uke, aldri tilpasset)
    ky = y + 56
    cw = (w - 5 * 5) / 6
    for i, n in enumerate([0, 4, 8, 12, 16, 20]):
        cx = x + i * (cw + 5)
        p.r(cx, ky, cw, 36, 18, "none", LINE, 1)
        p.t(cx + cw / 2, ky + 23.5, str(n), 15, 600, TXT, "middle")
    ky += 41
    rows = [["1", "2", "3", "4", "5", "del"], ["6", "7", "8", "9", "0", ""]]
    for r_i, row in enumerate(rows):
        for i, n in enumerate(row):
            if not n:
                continue
            cx = x + i * (cw + 5)
            cy = ky + r_i * 45
            if n == "del":
                p.r(cx, cy, cw, 85 + 0, 10, PANEL)
                p.icon(cx + cw / 2 - 11, cy + 31, "back", 22, TXT, 1.9)
            else:
                p.r(cx, cy, cw, 40, 10, PANEL)
                p.t(cx + cw / 2, cy + 27, n, 19, 600, TXT, "middle")
    p.add("</g>")


PRES_11 = [("Detaljist", "Ida", "done", "har bestilt"), ("Distributør", "Mikkel", "done", "har bestilt"), ("Fabrikk", "Jonas", "wait", "tenker, 3 min")]
PRES_OPEN = [("Detaljist", "Ida", "open", "tenker"), ("Distributør", "Mikkel", "open", "tenker"), ("Fabrikk", "Jonas", "open", "tenker")]


def bundle(week, ndiv=None, anim=False, dur=9.0, t0=.5):
    s = sara(week)
    its = [
        sysm("truck", f"Lastebilen kom med **{s['levering']} kasser**"),
        sysm("inbox", f"Ny ordre: **{s['innkommende_ordre']} kasser** fra kunden"),
        sysm("boxout", f"Du sendte **{s['sendt']}**"),
    ]
    if anim:
        its = [{"anim": slide(t0 + i * .55, dur), "it": it} for i, it in enumerate(its)]
    return its


def history_11():
    return [
        day("Mandag 21:05"),
        order(4, 6, "kom", when="Uke 6 · kom uke 10"),
        order(4, 7, "kom", when="Uke 7 · kom uke 11"),
        order(4, 8, "vei"),
        day("I går 22:31"),
        order(4, 9, "vei"),
        order(8, 10, "vei"),
        day("I kveld 20:47"),
    ]


def screen_b(p):
    game_header(p)
    presence(p, 13, 94, PRES_11)
    lay_thread(p, history_11() + bundle(11), 12, 136, 492, 366)
    status_card(p, 12, 496, 366, 11, typed=24)
    keypad(p, 12, 634, 366, typed=24)


def phone(p, x, y, s, draw, screen=NIGHT):
    p.add(f'<g transform="translate({x} {y}) scale({s})">')
    p.r(-7, -7, 404, 858, 52, "#0E0612", "#6A4676", 1.4)
    cid = p.uid("ph")
    p.add(f'<clipPath id="{cid}"><rect width="390" height="844" rx="45"/></clipPath><g clip-path="url(#{cid})">')
    p.r(0, 0, 390, 844, 0, screen)
    draw(p)
    p.add("</g></g>")


# ---------------------------------------------------------------- 01 Landing

def page_landing():
    p = Page("landing", 1440, 1200, "Tråden: landingsside for faglærere",
             "Mørk aubergine forside med en ekte spilltråd i aksjon, og en lys seksjon som viser faglærerens egen tråd fra Invitasjon til PDF-rapport.", NIGHT)
    wordmark(p, 96, 52, TXT, 25)
    p.t(1072, 52, "Logg inn", 16, 600, TXT)
    p.r(1150, 25, 194, 42, 21, "none", MUTE, 1)
    p.t(1247, 52, "Be om lærertilgang", 15, 600, TXT, "middle")
    # venstre: påstand
    y = 186
    for line in ["Hele kjeden,", "i en tråd", "studentene", "åpner selv."]:
        p.t(96, y, line, 74, 800, TXT, ls=-1.6)
        y += 76
    y = p.para(96, y - 14, "Fire studenter, fire Roller, ett tall per Uke. Spillet går over flere kvelder, og ett fravær stopper ikke gruppa: en KI-spiller fyller tomme seter, tydelig merket.", 560, 21, 30, fill=TXT)
    p.r(96, y + 8, 258, 62, 14, LIME)
    p.t(96 + 129, y + 47, "Be om lærertilgang", 20, 800, INKD, "middle")
    p.t(382, y + 46, "Logg inn", 19, 600, TXT)
    p.l(382, y + 53, 462, y + 53, MUTE, 1.4)
    yy = y + 118
    for ic, s in [("file", "Studentlisten lastes opp fra Canvas-eksport"), ("users", "Laget for klasser på rundt 250 studenter"), ("home", "Spilles på mobil, på norsk")]:
        p.icon(96, yy - 16, ic, 21, MINT)
        p.t(128, yy, s, 17, 400, TXT)
        yy += 33

    # høyre: tråden, ekte og i aksjon (uke 3, ingenting avslører etterspørselen)
    tx, ty, tw, th = 748, 96, 596, 672
    p.r(tx, ty, tw, th, 26, "#26122E", LINE, 1)
    p.add(f'<g transform="translate({tx + 14} {ty + 10}) scale(1.36)">')
    k = 1.36
    W = (tw - 28) / k
    p.role(13, 26, "Grossist", 8, LIME, LIME)
    p.t(31, 24, "Spill 17 · Grossist", 16, 800)
    p.t(31, 42, "Demodata", 13, 400, MUTE)
    pres = [("Detaljist", "Ida", "done", "har bestilt"), ("Distributør", "Mikkel", "done", "har bestilt"), ("Fabrikk", "Jonas", "ki", "er borte. KI-spiller har setet")]
    presence(p, 2, 68, pres)
    d = 11.0
    s2, s3, s4 = sara(2), sara(3), sara(4)
    items = [
        day("Mandag 20:14"),
        order(4, 2, "vei"),
        day("Tirsdag 21:02"),
    ] + bundle(3, anim=True, dur=d, t0=.4) + [
        {"anim": slide(2.4, d), "it": order(4, 3, "ny", when="Uke 3 · akkurat nå")},
    ]
    lay_thread(p, items, 0, 112, 374, W, fade="#26122E")
    # kompakt status nederst
    s = sara(3)
    p.r(0, 380, W, 92, 14, RAISED, LINE, 1)
    p.t(12, 402, "Uke 3", 16, 800)
    p.t(W - 12, 402, f"Totalkostnad **{kr(s['kost_sum'])}**", 13, 400, MUTE, "end", bfill=TXT)
    for i, (lab, val, kind) in enumerate([("Lager", s["lager"], "solid"), ("Restordre", s["restordre"], "slash"), ("På vei", s["paa_vei_foer_ordre"] + 4 - s["neste_levering"], "hollow")]):
        cx = 12 + i * 92
        p.pips(cx, 413, [(1, kind)], 9, 0)
        p.t(cx + 13, 422, lab, 13, 500, MUTE)
        p.t(cx, 454, str(val), 25, 800, MINT if kind == "hollow" else TXT)
    p.add("</g>")

    # lys seksjon: faglærerens tråd
    p.r(0, 836, 1440, 364, 0, PAPER)
    yh = p.para(96, 912, "Din tråd er hele kurset.", 520, 46, 52, w=800, fill=INK, ls=-1)
    yb = p.para(96, yh + 8, "Fra Invitasjon til PDF-rapport. Alle spillene på én skjerm, og det som trenger deg ligger øverst. Ingen spill blir stående uferdig.", 480, 19, 28, fill=INK)
    p.t(96, yb + 22, "Demodata", 14, 500, MUTEL)
    rows = [
        ("file", "Klasselisten er lest: **250 rader** fra Canvas-eksport, **4 ugyldige** adresser.", None, False),
        ("users", "**240 studenter** er fordelt i **60 spill** à 4.", None, False),
        ("clock", "**Spill 2** venter på Noah (Grossist), 23 t. KI overtar om 1 t.", "Send Melding", True),
        ("pause", "**Spill 20** er pauset. Fortsetter i kveld 19:00.", None, False),
        ("doc", "Klasserapporten ligger klar som PDF når spillene er over.", None, False),
    ]
    ry = 868
    for ic, s_, act, hot in rows:
        h = 56
        p.r(690, ry, 654, h, 12, URGBG if hot else CARD, URG if hot else LINEL, 1.4 if hot else 1)
        p.icon(704, ry + 16, ic, 24, URG if hot else PLUM, 2)
        p.t(740, ry + 34, s_, 16, 400, INK, bw=700)
        if act:
            p.r(1198, ry + 10, 134, 36, 9, LIME, INK, 1)
            p.t(1265, ry + 33.5, act, 15, 700, INKD, "middle")
        ry += h + 7
    p.save("01-landing.svg")


# ---------------------------------------------------------------- Lærerskall

def rail(p, h, active, sub="IBE160"):
    p.r(0, 0, 220, h, 0, INK)
    wordmark(p, 22, 48, TXT, 22)
    items = [("home", "Lærerhjem"), ("users", "Klasser"), ("cal", "Klasseøkter"), ("grid", "Oversikt"), ("mail", "Meldinger"), ("doc", "Klasserapport")]
    y = 92
    for ic, s in items:
        on = s == active
        if on:
            p.r(12, y - 21, 196, 36, 9, "#47265A")
        p.icon(24, y - 14, ic, 19, LIME if on else MUTE, 1.9)
        p.t(54, y + 2, s, 15, 700 if on else 400, TXT if on else MUTE)
        y += 42
    p.t(22, h - 44, "Bård", 15, 700, TXT)
    p.t(22, h - 24, "Faglærer", 13, 400, MUTE)


def lbtn(p, x, y, w, h, label, fill=LIME, ink=INKD, st=INK, icon=None, sz=15):
    p.r(x, y, w, h, 10, fill, st, 1)
    tx = x + w / 2
    if icon:
        tw = est(label, sz, True)
        p.icon(x + (w - tw) / 2 - 15, y + h / 2 - 9, icon, 18, ink, 2)
        tx += 10
    p.t(tx, y + h / 2 + sz * .36, label, sz, 700, ink, "middle")


def lsys(p, x, y, w, icon, text, h=44):
    p.r(x, y, w, h, 11, CARD, LINEL, 1)
    p.icon(x + 12, y + h / 2 - 10, icon, 20, PLUM, 2)
    p.t(x + 42, y + h / 2 + 5.5, text, 15, 400, INK, bw=700)


def lticket(p, x2, y, w, h, fill=PLUM):
    x = x2 - w
    p.path(ticket_path(x, y, w, h, 11), fill)
    p.c(x + w - 18, y + 10, 2.2, PAPER)


def field(p, x, y, w, label, val, h=42):
    p.t(x, y - 7, label, 13, 600, MUTEL)
    p.r(x, y, w, h, 9, PAPER, LINEL, 1)
    p.t(x + 12, y + h / 2 + 5.5, val, 15, 500, INK)


def page_klasse():
    p = Page("klasse", 1440, 1000, "Tråden: faglærer lager Klasse",
             "Oppsettet går som en tråd: systemet spør, du svarer, ugyldige rader listes per rad, Invitasjoner sendes og status følges til høyre.", PAPER)
    rail(p, 1000, "Klasser")
    x, w = 260, 770
    p.t(x, 62, "Ny Klasse", 34, 800, INK, ls=-.5)
    p.t(x + 170, 60, "Demodata", 14, 500, MUTEL)
    # 1
    y = 92
    p.r(x, y, w, 100, 12, CARD, LINEL, 1)
    p.icon(x + 13, y + 13, "pen", 20, PLUM, 2)
    p.t(x + 42, y + 29, "Hva heter Klassen?", 16, 700, INK)
    field(p, x + 42, y + 50 + 8, 400, "", "class-of-1994", 32)
    p.t(x + 42, y + 50, "Navn", 13, 600, MUTEL)
    p.t(x + 456, y + 50, "Emnekode", 13, 600, MUTEL)
    p.r(x + 456, y + 58, 290, 32, 9, PAPER, LINEL, 1)
    p.t(x + 468, y + 79, "IBE160", 15, 500, INK)
    # 2 fil
    y = 212
    lsys(p, x, y, w - 200, "file", "Last opp studentlisten fra **Canvas-eksport**")
    lticket(p, x + w, y + 50, 330, 42)
    p.icon(x + w - 318, y + 61, "check", 18, LIME, 2.6)
    p.t(x + w - 294, y + 76, "ibe160-canvas-eksport.xlsx · 250 rader", 14, 600, "#FFFFFF")
    # 3 kolonne
    y = 322
    p.r(x, y, w, 112, 12, CARD, LINEL, 1)
    p.icon(x + 13, y + 12, "grid", 20, PLUM, 2)
    p.t(x + 42, y + 28, "Hvilken kolonne er e-post?", 16, 700, INK)
    cols = [("Navn", "Sara Berg", False), ("SIS-bruker", "sbe012", False), ("E-post", "sara.berg@student.example", True), ("Seksjon", "IBE160 H26", False)]
    cx = x + 42
    for name, sample, on in cols:
        cw = 268 if on else 122
        p.r(cx, y + 42, cw, 56, 9, LIMEBG if on else PAPER, INK if on else LINEL, 1.6 if on else 1)
        if on:
            p.icon(cx + cw - 26, y + 49, "check", 17, INK, 2.8)
        p.t(cx + 11, y + 63, name, 14, 700, INK)
        p.t(cx + 11, y + 84, sample, 13, 400, MUTEL)
        cx += cw + 8
    # 4 ugyldige
    y = 452
    bad = [(37, "Tuva Nilsen", "tuva.nilsen@student", "mangler domene"), (88, "Emil Haugen", "emil haugen@student.example", "mellomrom i adressen"),
           (141, "Ada Strand", "ada.strand@@student.example", "to krøllalfa"), (203, "Liam Moe", "", "tom celle")]
    h = 48 + 4 * 38 + 8
    p.r(x, y, w, h, 12, CARD, URG, 1.4)
    p.icon(x + 13, y + 12, "warn", 20, URG, 2)
    p.t(x + 42, y + 28, "**4 rader** har ugyldig adresse. De 246 andre er klare.", 16, 400, INK, bw=800)
    ty = y + 44
    for i, (rad, name, adr, why) in enumerate(bad):
        ry = ty + i * 38
        p.l(x + 14, ry, x + w - 14, ry, LINEL)
        p.t(x + 42, ry + 24, f"Rad {rad}", 14, 700, INK)
        p.t(x + 106, ry + 24, name, 14, 400, INK)
        p.t(x + 216, ry + 24, adr or "(tom)", 14, 400, URG)
        p.t(x + 448, ry + 24, why, 13, 400, MUTEL)
        p.r(x + w - 164, ry + 6, 66, 27, 7, "none", INK, 1)
        p.t(x + w - 131, ry + 24, "Rett", 13, 700, INK, "middle")
        p.r(x + w - 92, ry + 6, 80, 27, 7, "none", LINEL, 1)
        p.t(x + w - 52, ry + 24, "Hopp over", 13, 500, MUTEL, "middle")
    # 5 send
    y = 680
    lsys(p, x, y, w - 200, "mail", "Invitasjonen er gyldig i **14 dager**. Alle får hver sin lenke.")
    lticket(p, x + w, y + 52, 290, 48)
    p.icon(x + w - 276, y + 66, "lock", 17, "#FFFFFF", 2)
    p.t(x + w - 252, y + 74, "Sendt til 246", 16, 800, "#FFFFFF")
    p.t(x + w - 252, y + 92, "to. 5. nov 09:12", 13, 400, "#E6D9EA")
    y = 798
    lsys(p, x, y, w, "check", "**238** har akseptert. **8** har ikke svart ennå, og 3 av disse er utløpt.")
    lbtn(p, x, y + 56, 234, 44, "Send på nytt til de 8", icon="mail")
    lbtn(p, x + 244, y + 56, 194, 44, "Registrer manuelt", CARD, INK, LINEL)
    p.para(x + 454, y + 76, "De 4 ugyldige radene får ingen Invitasjon før de er rettet. To er alt registrert manuelt.", 316, 13, 18, fill=MUTEL)
    # høyre status
    rx, rw = 1060, 350
    p.r(rx, 40, rw, 870, 14, CARD, LINEL, 1)
    p.t(rx + 20, 78, "Klasseliste", 22, 800, INK)
    p.t(rx + 20, 100, "class-of-1994 · IBE160 · 250 rader", 14, 400, MUTEL)
    ro = FX["roster"]
    statuses = [("Registrert", ro["registrert"], "done"), ("Manuelt registrert", ro["manuelt_registrert"], "manual"), ("Uregistrert", ro["uregistrert"], "open")]
    y = 124
    # enhetsstolpe til skala
    bx, bw = rx + 20, rw - 40
    cx = bx
    total = ro["paa_lista"]
    for lab, n, kind in statuses:
        sw = bw * n / total
        col = {"done": PLUM, "manual": "#9B7CA8", "open": URG}[kind]
        p.r(cx, y, max(sw - 2, 3), 14, 2, col)
        cx += sw
    y += 42
    for lab, n, kind in statuses:
        if kind == "done":
            p.icon(bx, y - 15, "check", 18, PLUM, 2.8)
        elif kind == "manual":
            p.icon(bx, y - 15, "pen", 18, MUTEL, 2)
        else:
            p.c(bx + 9, y - 6, 7, "none", URG, 1.8, "2.5 2.5")
        p.t(bx + 28, y, lab, 15, 400, INK)
        p.t(rx + rw - 20, y, str(n), 15, 800, INK, "end")
        y += 28
    y += 14
    p.t(bx, y, "Invitasjoner", 17, 800, INK)
    y += 28
    for lab, n, ic in [("Sendt", 246, "mail"), ("Akseptert", 238, "check"), ("Ikke svart", 5, "clock"), ("Utløpt", 3, "x")]:
        p.icon(bx, y - 15, ic, 18, URG if lab == "Utløpt" else PLUM, 2)
        p.t(bx + 28, y, lab, 15, 400, INK)
        p.t(rx + rw - 20, y, str(n), 15, 800, INK, "end")
        y += 28
    y += 8
    p.l(bx, y, rx + rw - 20, y, LINEL)
    y += 28
    p.t(bx, y, "Rad for rad", 17, 800, INK)
    y += 16
    ppl = [("Sara Berg", "Akseptert", "check", PLUM), ("Ida Lie", "Akseptert", "check", PLUM), ("Noah Vik", "Akseptert", "check", PLUM),
           ("Selma Aas", "Sendt, ikke svart", "clock", PLUM), ("Theo Rud", "Utløpt", "x", URG), ("Mia Dahl", "Utløpt", "x", URG),
           ("Tuva Nilsen", "Ugyldig adresse, rad 37", "warn", URG), ("Ada Strand", "Manuelt registrert", "pen", MUTEL),
           ("Emil Haugen", "Manuelt registrert", "pen", MUTEL), ("Liam Moe", "Ugyldig adresse, rad 203", "warn", URG)]
    for n, st, ic, col in ppl:
        p.l(bx, y, rx + rw - 20, y, LINEL)
        p.t(bx, y + 25, n, 14, 600, INK)
        p.icon(bx + 104, y + 10, ic, 17, col, 2)
        p.t(bx + 126, y + 25, st, 14, 400, col if col == URG else INK)
        y += 38
    p.l(bx, y, rx + rw - 20, y, LINEL)
    p.t(bx, y + 26, "Vis alle 250", 14, 700, PLUM)
    p.save("02-laerer-klasse.svg")


def seg(p, x, y, opts, on, h=38, sz=14):
    cx = x
    for o, w in opts:
        act = o == on
        p.r(cx, y, w, h, 9, LIMEBG if act else CARD, INK if act else LINEL, 1.5 if act else 1)
        if act:
            p.icon(cx + 9, y + h / 2 - 8, "check", 16, INK, 2.8)
        p.t(cx + (29 if act else 13), y + h / 2 + 5, o, sz, 700 if act else 400, INK)
        cx += w + 7


def page_okt():
    p = Page("okt", 1440, 1100, "Tråden: faglærer setter opp Klasseøkt",
             "Forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordelingsforhåndsvisning av 60 spill à 4. Kan lagres uten endring.", PAPER)
    rail(p, 1100, "Klasseøkter")
    x = 260
    p.t(x, 62, "Klasseøkt, IBE160", 34, 800, INK, ls=-.5)
    p.t(x + 352, 60, "Demodata", 14, 500, MUTEL)
    p.t(x, 92, "Alt er forhåndsutfylt. Du kan lagre uten å endre noe.", 17, 400, INK)
    # venstre kolonne
    w = 610
    y = 116
    p.r(x, y, w, 400, 13, CARD, LINEL, 1)
    p.t(x + 18, y + 34, "Spillinnstillinger", 20, 800, INK)
    p.r(x + w - 118, y + 16, 100, 28, 14, INK)
    p.t(x + w - 68, y + 35, "Klassisk", 14, 700, "#FFFFFF", "middle")
    vals = [("Startlager", "12"), ("Enheter i hvert ledd", "4"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"),
            ("Etterspørsel", "4 → 8 i uke 5"), ("Lagerkost", "0,50 kr"), ("Restordrekost", "1,00 kr"), ("Uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t")]
    yy = y + 62
    for i, (k, v) in enumerate(vals):
        col = i % 2
        row = i // 2
        vx = x + 18 + col * (w - 36) / 2
        vy = yy + row * 44
        p.l(vx, vy + 15, vx + (w - 36) / 2 - 16, vy + 15, LINEL)
        p.t(vx, vy + 6, k, 14, 400, MUTEL)
        p.t(vx + (w - 36) / 2 - 16, vy + 6, v, 15, 700, INK, "end")
    yt = yy + 6 * 44 + 2
    p.r(x + 18, yt - 22, w - 36, 54, 10, PAPER)
    p.icon(x + 28, yt - 12, "reply", 20, PLUM, 2)
    p.para(x + 58, yt, "Kildene er uenige om forsinkelsene. Dette er produktets standard. Vil du se hva endringer gjør, kan du kjøre et testspill først.", w - 96, 14, 19, fill=INK)
    # moduser
    y = 530
    p.r(x, y, w, 300, 13, CARD, LINEL, 1)
    p.t(x + 18, y + 32, "KI-modus", 17, 800, INK)
    p.ki(x + 118, y + 26, 9, False)
    seg(p, x + 18, y + 46, [("LLM-spillere", 160), ("Regelbaserte spillere", 196)], "LLM-spillere")
    p.t(x + 18, y + 106, "Fyller alle tomme seter ved start og tar over ved fravær. Alltid merket.", 14, 400, MUTEL)
    p.t(x + 18, y + 146, "Debrief-modus", 17, 800, INK)
    seg(p, x + 18, y + 160, [("Gruppedebrief", 170), ("Personlig debrief", 164)], "Gruppedebrief")
    p.l(x + 18, y + 216, x + w - 18, y + 216, LINEL)
    p.r(x + 18, y + 236, 26, 26, 6, INK)
    p.icon(x + 21, y + 239, "check", 20, LIME, 3)
    p.t(x + 56, y + 247, "Obligatorisk", 17, 800, INK)
    p.t(x + 56, y + 268, "Krever alle steg: Klassespill, Debrief, Quiz, Replay og levert test.", 14, 400, MUTEL)
    # lagre
    y = 846
    p.r(x, y, w, 206, 13, INK)
    p.t(x + 20, y + 42, "Lagre Klasseøkten", 22, 800, "#FFFFFF")
    p.para(x + 20, y + 72, "Fordelingen sendes til studentene når du lagrer. Spillinnstillingene kan endres fram til startdatoen, frister og Labtimer når som helst.", w - 40, 15, 22, fill="#E6D9EA")
    p.r(x + 20, y + 136, 240, 50, 11, LIME)
    p.t(x + 140, y + 167, "Lagre Klasseøkt", 17, 800, INKD, "middle")
    p.r(x + 272, y + 136, 164, 50, 11, "none", "#8D6D98", 1)
    p.t(x + 354, y + 167, "Kjør testspill", 15, 600, "#FFFFFF", "middle")
    # høyre kolonne
    rx, rw = x + w + 20, 530
    y = 40
    p.r(rx, y, rw, 318, 13, CARD, LINEL, 1)
    p.t(rx + 18, y + 34, "Datoer", 20, 800, INK)
    p.l(rx + 28, y + 56, rx + 28, y + 176, PLUM, 2)
    for i, (d, lab) in enumerate([("ti. 24. nov 2026", "Start"), ("ti. 8. des", "Spillfrist"), ("fr. 11. des", "Debrief-frist"), ("fr. 18. des", "Testfrist")]):
        yy = y + 62 + i * 38
        p.c(rx + 28, yy - 5, 6, CARD, PLUM, 2)
        p.t(rx + 46, yy, lab, 15, 400, MUTEL)
        p.t(rx + 170, yy, d, 15, 700, INK)
        p.icon(rx + rw - 44, yy - 15, "cal", 19, PLUM, 1.9)
    p.l(rx + 18, y + 202, rx + rw - 18, y + 202, LINEL)
    p.t(rx + 18, y + 228, "Labtimer, Datalab A2", 15, 800, INK)
    labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    for i, l in enumerate(labs):
        lx = rx + 18 + (i % 2) * 248
        ly = y + 240 + (i // 2) * 34
        p.r(lx, ly, 238, 28, 14, PAPER, LINEL, 1)
        p.icon(lx + 9, ly + 6, "clock", 16, PLUM, 1.9)
        p.t(lx + 32, ly + 19, l, 14, 500, INK)
    # fordeling
    y = 372
    p.r(rx, y, rw, 680, 13, CARD, LINEL, 1)
    p.t(rx + 18, y + 36, "Fordeling", 20, 800, INK)
    p.t(rx + 18, y + 62, "**240 studenter** tilfeldig fordelt i **60 spill** à 4.", 16, 400, INK, bw=800)
    # 60 mini-spill, hvert med fire rolleformer
    gx, gy = rx + 18, y + 80
    cols = 6
    cw = (rw - 36) / cols
    ch = 53
    for i in range(60):
        cx = gx + (i % cols) * cw
        cy = gy + (i // cols) * ch
        hi = i + 1 == 17
        p.r(cx + 1, cy, cw - 6, ch - 7, 7, LIMEBG if hi else PAPER, INK if hi else LINEL, 1.3 if hi else .8)
        p.t(cx + 8, cy + 18, str(i + 1), 13, 700, INK)
        for j, role in enumerate(ROLES):
            p.role(cx + 13 + j * 17.5, cy + 33, role, 4.6, None, PLUM, 1.3)
    y2 = gy + 10 * ch + 6
    lbtn(p, rx + 18, y2, 164, 42, "Kjør på nytt", CARD, INK, INK, icon="redo")
    lbtn(p, rx + 192, y2, 190, 42, "Bekreft fordeling", icon="check")
    p.save("03-laerer-spill.svg")


# ---------------------------------------------------------------- 04 Student

def page_hjem():
    p = Page("hjem", 1000, 900, "Tråden: studenten Sara på mobil",
             "To telefoner. Venstre: Invitasjon og registrering som første melding i tråden. Høyre: hjem under spill, spillet venter på deg, seter, seks steg, frist og Labtimer.", "#160A1C")

    def left(p):
        p.r(160, 11, 70, 5, 2.5, LINE)
        wordmark(p, 16, 56, TXT, 21)
        p.t(374, 54, "Demodata", 13, 400, MUTE, "end")
        lay = 12
        items = [
            day("To. 5. nov 09:12"),
            card("mail", "Bård har invitert deg", "Du er på klasselisten til **class-of-1994**, IBE160. Invitasjonen gjelder i 14 dager.", sz=15),
        ]
        lay_thread(p, items, lay, 70, 196, 366)
        # skjema som kort
        p.r(12, 200, 366, 282, 13, RAISED, LINE, 1)
        p.t(26, 230, "Lag kontoen din", 17, 800)
        for i, (lab, val, ph) in enumerate([("Navn", "Sara Berg", False), ("E-post, fra klasselisten", "sara.berg@student.example", False), ("Velg passord", "Minst 10 tegn", True)]):
            yy = 254 + i * 58
            p.t(26, yy - 4, lab, 13, 500, MUTE)
            p.r(26, yy + 3, 338, 34, 9, PANEL, LIME if ph else LINE, 1.4 if ph else 1)
            p.t(38, yy + 25, val, 15, 400, MUTE if ph else TXT)
        p.r(26, 426, 338, 44, 11, LIME)
        p.t(195, 454, "Bli med i Klassen", 16, 800, INKD, "middle")
        # hva som skjer
        p.t(16, 514, "Slik blir det", 17, 800)
        items = [
            sysm("truck", "Hver Uke kommer noen korte meldinger"),
            sysm("pen", "Du svarer med ett tall. Ikke mer."),
            sysm("users", "Tre andre svarer på sine telefoner"),
            sysm("clock", "Dere spiller når det passer, over kvelder"),
        ]
        y = 528
        for it in items:
            it[1](p, 12, y, 400)
            y += it[0]
        p.icon(14, y + 10, "cal", 20, MINT)
        p.t(44, y + 25, "Rolle og gruppe kommer **ti. 24. nov**.", 15, 400, TXT, bw=700)
        p.para(14, y + 58, "Det finnes ingen chat her. Tråden er mellom deg og systemet.", 360, 14, 19, fill=MUTE)

    def right(p):
        p.r(160, 11, 70, 5, 2.5, LINE)
        p.t(16, 56, "Hei, Sara", 22, 800)
        p.t(374, 54, "Demodata", 13, 400, MUTE, "end")
        # hovedtråd
        p.r(12, 72, 366, 118, 16, LIME)
        p.role(32, 96, "Grossist", 8, INKD, INKD)
        p.t(50, 101, "Spill 17 · Grossist", 16, 800, INKD)
        p.t(26, 134, "Spillet venter på deg", 22, 800, INKD)
        p.t(26, 158, "Uke 11 er åpen. Ida og Mikkel har bestilt.", 14, 500, INKD)
        p.icon(344, 88, "send", 22, INKD, 2.6)
        # andre seter
        p.t(16, 216, "De andre setene", 15, 700)
        rows = [("Detaljist", "Ida", "done", "har bestilt"), ("Distributør", "Mikkel", "done", "har bestilt"), ("Fabrikk", "Jonas", "wait", "tenker, 3 min")]
        y = 234
        for role, n, st, tx in rows:
            p.role(26, y + 8, role, 6.5, None, TXT, 1.5)
            p.t(42, y + 13, f"**{n}**, {role}", 14, 400, TXT, bw=700)
            if st == "done":
                p.icon(240, y + 1, "check", 15, MINT, 2.6)
            else:
                p.icon(240, y + 1, "clock", 15, APR, 2)
            p.t(260, y + 13, tx, 14, 400, MUTE)
            y += 24
        # seks steg som tråd
        p.t(16, 334, "Stegene dine", 15, 700)
        steps = [("Klassespill", "Pågår, frist ti. 8. des", "now"), ("Debrief", "Åpnes når spillet er ferdig", "lock"), ("Quiz", "Etter Debrief", "lock"),
                 ("Replay", "Du mot tre KI-spillere", "ki"), ("Individuell test", "Testfrist fr. 18. des", "lock"), ("Rapport", "PDF når testen er levert", "lock")]
        y = 356
        p.l(26, y, 26, y + 5 * 38, LINE, 2)
        for lab, sub, st in steps:
            if st == "now":
                p.c(26, y, 9, LIME)
                p.icon(21, y - 5, "play", 10, INKD, 1.5, INKD)
            elif st == "ki":
                p.c(26, y, 9, NIGHT)
                p.ki(26, y, 8)
            else:
                p.c(26, y, 9, NIGHT, LINE, 1.5)
                p.icon(20, y - 6, "lock", 12, MUTE, 2)
            p.t(46, y + 5, lab, 15, 700, TXT)
            p.t(374, y + 5, sub, 13, 400, MUTE, "end")
            y += 38
        # frist og labtimer
        y = 586
        p.r(12, y, 366, 96, 13, PANEL, LINE, 1)
        p.icon(24, y + 13, "flag", 20, MINT)
        p.t(52, y + 28, "Neste frist: **Spillfrist ti. 8. des**", 15, 400, TXT, bw=700)
        p.icon(24, y + 53, "cal", 20, MINT)
        p.t(52, y + 68, "Neste Labtime: **to. 26. nov 14:15**", 15, 400, TXT, bw=700)
        p.t(52, y + 87, "Datalab A2, faglærer i rommet", 13, 400, MUTE)
        # labtimeliste
        p.t(16, 712, "Alle Labtimer", 15, 700)
        labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
        for i, l in enumerate(labs):
            lx = 12 + (i % 2) * 186
            ly = 726 + (i // 2) * 42
            p.r(lx, ly, 180, 36, 18, "none", LINE, 1)
            p.t(lx + 90, ly + 23, l, 14, 500, TXT, "middle")

    phone(p, 62, 28, 1, left)
    phone(p, 548, 28, 1, right)
    p.save("04-student-hjem.svg")


# ---------------------------------------------------------------- 05 Spill

def page_spill():
    p = Page("spill", 1600, 1000, "Tråden: spillskjermen midt i Uke 11",
             "Sara har tastet 24 med 16 på vei. Statuskortet viser kassene side om side. Samme skjerm på telefon og laptop.", "#160A1C")
    phone(p, 64, 28, 1.12, screen_b)
    # laptop
    lx, ly, lw, lh = 590, 56, 950, 640
    p.r(lx - 14, ly - 14, lw + 28, lh + 28, 18, "#0E0612", "#6A4676", 1.4)
    p.path(f"M{lx - 44} {ly + lh + 14}H{lx + lw + 44}L{lx + lw + 26} {ly + lh + 34}H{lx - 26}Z", "#2A1832", "#6A4676", 1)
    p.r(lx, ly, lw, lh, 0, NIGHT)
    p.role(lx + 28, ly + 34, "Grossist", 9, LIME, LIME)
    p.t(lx + 48, ly + 31, "Spill 17 · Grossist", 18, 800)
    p.t(lx + 48, ly + 51, "Demodata · IBE160", 13, 400, MUTE)
    presence(p, lx + 20, ly + 86, PRES_11)
    p.l(lx + 16, ly + 132, lx + 500, ly + 132, LINE)
    lay_thread(p, history_11() + bundle(11), lx + 16, ly + 138, ly + lh - 12, 484)
    p.l(lx + 516, ly, lx + 516, ly + lh, LINE)
    rx = lx + 532
    rw = lw - 532 - 16
    p.r(rx + rw - 82, ly + 18, 82, 32, 16, "none", LINE, 1)
    p.icon(rx + rw - 72, ly + 26, "pause", 16, TXT, 2.2)
    p.t(rx + rw - 52, ly + 39, "Pause", 13, 600)
    status_card(p, rx, ly + 62, rw, 11, typed=24)
    keypad(p, rx, ly + 206, rw, typed=24)
    # ordrehistorikk som kort tabell
    oy = ly + 206 + 190
    p.t(rx, oy + 16, "Ordrene dine", 15, 700)
    hist = orders("Grossist")[:10]
    cw = rw / 10
    h = FX and 3.1
    base = oy + 90
    for i, v in enumerate(hist):
        bh = v * h * 1.6
        p.path(ticket_path(rx + i * cw + 3, base - bh, cw - 6, bh, 3, 2), RAISED, LINE, 1)
        p.t(rx + i * cw + cw / 2, base - bh - 5, str(v), 13, 600, TXT, "middle")
        p.t(rx + i * cw + cw / 2, base + 17, str(i + 1), 13, 400, MUTE, "middle")
    p.t(rx, base + 38, "Uke 1 til 10. Tastatur fungerer også: skriv tall, Enter sender.", 13, 400, MUTE)
    # notater
    ny = 770
    notes = [("Svaret er ett tall", "Tre meldinger, ett svar. Snarveiene er de samme hver Uke, så appen foreslår aldri et bestemt tall."),
             ("16 tomme ved siden av 24 grønne", "Det du allerede har bestilt, står som tomme kasser på samme stripe som tallet du taster. Du kan se det, men ingen sier hva du bør gjøre."),
             ("Historikken er bare å rulle i", "Ordreboblene ligger i tråden med sine kasser til de er kommet. Rull opp, og du ser hva du bestilte hvilken kveld.")]
    for i, (h_, b) in enumerate(notes):
        nx = 590 + i * 322
        p.t(nx, ny + 18, h_, 17, 800)
        p.para(nx, ny + 44, b, 292, 15, 21, fill=MUTE)
    p.save("05-spill.svg")


# ---------------------------------------------------------------- 06 Dynamikk

def page_dynamikk():
    p = Page("dynamikk", 2100, 1200, "Tråden: spilldynamikk i seks ruter",
             "Storyboard A til F: Uka åpner, beslutningen, bekreftet, uka går videre, Jonas er borte, spillet slutter. Med korte notater.", "#160A1C")
    p.t(36, 56, "En Uke i tråden", 38, 800, ls=-.6)
    p.t(322, 56, "Demodata", 15, 500, MUTE)
    S = .8
    fw = 390 * S
    gapx = (2100 - 72 - 6 * fw) / 5
    px = [36 + i * (fw + gapx) for i in range(6)]
    top = 86

    def a(p):
        game_header(p)
        presence(p, 13, 94, PRES_OPEN)
        items = history_11() + bundle(11, anim=True, dur=9.0, t0=.3)
        lay_thread(p, items, 12, 136, 492, 366)
        status_card(p, 12, 496, 366, 11)
        keypad(p, 12, 634, 366)

    def c(p):
        game_header(p)
        presence(p, 13, 94, PRES_11)
        items = history_11() + bundle(11) + [
            {"anim": slide(.3, 9.0, .4, 22), "it": order(24, 11, "ny", when="Uke 11 · kan ikke endres")},
            (8, lambda p, x, y, w: None),
        ]
        lay_thread(p, items, 12, 136, 620, 366)
        p.r(12, 622, 366, 60, 12, PANEL)
        p.icon(24, 632, "clock", 18, APR, 2)
        p.t(50, 646, "Venter på **Fabrikk, Jonas**, 3 min", 15, 400, TXT, bw=700)
        p.t(50, 668, "Du kan legge fra deg telefonen nå.", 13, 400, MUTE)
        status_card(p, 12, 690, 366, 11)
        # 132 høyt: går til 822

    def d(p):
        game_header(p)
        presence(p, 13, 94, [("Alle fire har bestilt", "", "done", "")])
        items = [order(4, 8, "vei"), order(4, 9, "vei"), order(8, 10, "vei"), order(24, 11, "vei")]
        items += [{"anim": slide(.2, 6.0, .35, 20), "it": day("Uke 12 · nå")}] + bundle(12, anim=True, dur=6.0, t0=.4)
        lay_thread(p, items, 12, 118, 492, 366)
        # hopp over
        p.r(258, 122, 120, 32, 16, TXT)
        p.t(304, 143, "Hopp over", 14, 700, INKD, "middle")
        p.icon(344, 129, "send", 17, INKD, 2.4)
        status_card(p, 12, 496, 366, 12)
        keypad(p, 12, 634, 366)
        # tidslinje for overgangen
        p.r(12, 492 - 4, 366, 3, 1.5, LINE)
        p.add(f'<rect x="12" y="488" width="290" height="3" rx="1.5" fill="{LIME}"><animate attributeName="width" values="0;366;366" keyTimes="0;.25;1" dur="6s" repeatCount="indefinite"/></rect>')

    def e(p):
        game_header(p, right="Pause")
        presence(p, 13, 94, [("Detaljist", "Ida", "done", "har bestilt"), ("Distributør", "Mikkel", "done", "har bestilt"), ("Fabrikk", "", "ki", "KI-spiller har bestilt")])
        items = [
            order(sara(26)["ordre"], 26, "vei"),
            day("Onsdag 22:10"),
            card("pause", "Ida satte spillet på pause", "Dere fortsetter **to. 3. des 14:15**, Datalab A2. Ingen KI overtar mens spillet er på pause.", sz=14),
            day("To. 3. des 14:32"),
            card("x", "KI-spiller i Fabrikk-setet", "Jonas kom ikke til avtalt tid. Mikkel satte en KI-spiller i setet. Fra nå står den merket KI i tråden.", ki=True, sz=14),
        ]
        lay_thread(p, items, 12, 136, 484, 366)
        # det Jonas ser
        p.r(12, 486, 366, 122, 13, "none", KIC, 1.4, "5 4")
        p.t(26, 510, "Det Jonas ser på sin telefon", 14, 700, KIC)
        p.para(26, 530, "KI-spiller har setet ditt. Du kan ta det tilbake når neste Uke åpner.", 340, 13, 17, fill=TXT)
        p.r(26, 558, 338, 40, 10, LIME)
        p.t(195, 583, "Ta tilbake setet", 15, 800, INKD, "middle")
        status_card(p, 12, 616, 366, 27)
        p.r(12, 756, 366, 50, 12, PANEL, LINE, 1)
        p.icon(24, 772, "lock", 16, MUTE, 2)
        p.t(50, 786, f"Du har bestilt **{sara(27)['ordre']}** denne Uka", 15, 400, TXT, bw=800)
        p.t(372 - 8, 786, "Uke 27", 13, 400, MUTE, "end")

    def f(p):
        p.r(160, 11, 70, 5, 2.5, LINE)
        p.role(28, 49, "Grossist", 8, LIME, LIME)
        p.t(46, 47, "Spill 17 · Grossist", 16, 800)
        p.t(46, 65, "Demodata · IBE160", 13, 400, MUTE)
        s = sara(36)
        items = [day("Fr. 4. des 21:18")] + [
            sysm("truck", f"Lastebilen kom med **{s['levering']} kasser**"),
            sysm("boxout", f"Du sendte **{s['sendt']}**"),
            order(s["ordre"], 36, "vei"),
        ]
        lay_thread(p, items, 12, 80, 290, 366)
        p.r(12, 298, 366, 526, 18, RAISED, LINE, 1)
        p.icon(26, 314, "flag", 22, LIME, 2)
        p.t(56, 332, "Spillet er ferdig", 20, 800)
        p.add(f"<g>{slide(.4, 9.0, .5, 12)}")
        p.t(30, 378, "Hele kjeden, totalkostnad", 15, 500, MUTE)
        p.t(30, 432, f"{fmt_num(FX['chain_total_cost'])} kr", 50, 800, TXT, ls=-1)
        p.add("</g>")
        y = 468
        for i, r_ in enumerate(ROLES):
            p.add(f"<g>{slide(1.0 + i * .28, 9.0, .4, 10)}")
            p.l(30, y, 360, y, LINE)
            p.role(40, y + 25, r_, 7, LIME if r_ == "Grossist" else None, LIME if r_ == "Grossist" else TXT, 1.6)
            p.t(58, y + 30, r_ + (", deg" if r_ == "Grossist" else ""), 16, 700 if r_ == "Grossist" else 400)
            p.t(360, y + 30, kr(FX["total_cost_per_role"][r_]), 17, 700, TXT, "end")
            p.add("</g>")
            y += 46
        p.add(f"<g>{slide(2.4, 9.0, .5, 12)}")
        p.para(30, y + 28, "Dette er ikke en rangering. I Debriefen ser dere hvorfor det ble slik.", 330, 14, 19, fill=MUTE)
        p.r(30, y + 66, 330, 54, 12, LIME)
        p.t(180, y + 99, "Til Debrief", 18, 800, INKD, "middle")
        p.icon(250, y + 82, "send", 22, INKD, 2.6)
        p.add("</g>")

    def b(p):
        screen_b(p)

    frames = [a, b, c, d, e, f]
    notes = [
        ("A  Uka åpner", "Tre meldinger glir inn nederst: levering, ny ordre, det du sendte. Statuskortet følger med."),
        ("B  Beslutningen", "Du taster 24. Hver kasse legger seg ved siden av de 16 tomme som alt er på vei."),
        ("C  Bekreftet", "Send låser boblen. Tastaturet forsvinner, tråden sier hvem det venter på."),
        ("D  Uka går videre", "Nye meldinger glir inn på under 2 sek, eller med ett trykk. 24 er blitt til tomme kasser."),
        ("E  Jonas er borte", "Pause er et kort med avtalt tid. KI-spilleren er merket i tråden, og Jonas får knappen sin."),
        ("F  Spillet slutter", "Tråden kunne ikke rulle hit på forhånd. Kjeden først, så hver Rolle, så Debrief."),
    ]
    for i, fn in enumerate(frames):
        phone(p, px[i] + 3, top, S, fn)
        lab, b_ = notes[i]
        p.t(px[i], top + 844 * S + 36, lab, 18, 800, LIME if i == 1 else TXT)
        p.para(px[i], top + 844 * S + 60, b_, fw, 15, 21, fill=MUTE)
    # under rutene
    y = 900 + 44
    tw = 1000
    p.t(36, y, "Hvorfor dette føles annerledes", 24, 800)
    p.para(36, y + 34, "Tråden gjør spillet til noe du svarer på, ikke noe du setter av tid til. En Uke er tre meldinger og ett tall, så den kan tas på bussen, og Uka venter i tråden til du kommer tilbake. Ordreboblene dine ligger igjen med tomme kasser til varene er kommet, så det du allerede har bestilt er synlig hele tiden og likevel lett å overse. Tråden har ingen slutt å rulle mot, ingen framdrift, bare neste melding.", tw, 18, 27, fill=TXT)
    # kassene forklart
    ly_ = y + 208
    p.t(36, ly_, "Kassene i tall", 17, 800)
    ly_ += 22
    p.pips(36, ly_, [(1, "solid")], 13, 0)
    p.t(58, ly_ + 12, "Lager: fylt", 16, 400)
    p.pips(196, ly_, [(1, "hollow")], 13, 0)
    p.t(218, ly_ + 12, "På vei: tom", 16, 400)
    p.pips(352, ly_, [(1, "slash")], 13, 0)
    p.t(374, ly_ + 12, "Restordre: strøket", 16, 400)
    p.pips(570, ly_, [(1, "lime")], 13, 0)
    p.t(592, ly_ + 12, "Det du taster nå", 16, 400)
    # ti sekunder
    tx, ty = 1160, y - 6
    p.t(tx, ty + 6, "Designmål for én Uke: ti sekunder", 20, 800)
    p.t(tx + 400, ty + 6, "Ikke målt ennå", 14, 500, MUTE)
    x0, x1 = tx, tx + 860
    bar = ty + 60
    steps = [(0, 3, "Les tre meldinger", "truck"), (3, 5, "Se statuskortet", "grid"), (5, 8, "Tast tallet", "pen"), (8, 10, "Send", "send")]
    for s0, s1, lab, ic in steps:
        ax = x0 + (x1 - x0) * s0 / 10
        bx = x0 + (x1 - x0) * s1 / 10
        p.r(ax + 1, bar, bx - ax - 2, 34, 6, LIME if ic == "send" else RAISED, None if ic == "send" else LINE)
        p.icon(ax + 10, bar + 8, ic, 18, INKD if ic == "send" else MINT, 2)
        p.t(ax + 34, bar + 22.5, lab, 14, 600, INKD if ic == "send" else TXT)
    for s_ in range(0, 11, 1):
        ax = x0 + (x1 - x0) * s_ / 10
        p.l(ax, bar + 38, ax, bar + 44, MUTE, 1)
        if s_ in (0, 3, 5, 8, 10):
            p.t(ax, bar + 62, f"{s_} s", 13, 500, MUTE, "middle")
    # tre kvelder
    ky = bar + 96
    p.t(tx, ky, "Tre kvelder i samme tråd", 17, 800)
    evs = [("Mandag", "Uke 1–6", 6), ("Tirsdag", "Uke 7–10", 4), ("I kveld", "Uke 11 …", 1)]
    ex = tx
    for name, lab, n in evs:
        wd = 60 + n * 34
        p.l(ex, ky + 22, ex + wd - 12, ky + 22, LINE, 1)
        p.t(ex, ky + 44, f"**{name}** {lab}", 14, 400, MUTE, bfill=TXT)
        for j in range(n):
            p.path(ticket_path(ex + j * 34, ky + 56, 28, 18, 5, 3), LIME if name == "I kveld" else RAISED, None if name == "I kveld" else LINE, 1)
        ex += wd + 18
    p.save("06-spilldynamikk.svg")


# ---------------------------------------------------------------- 07 Debrief

def chart_orders(p, x, y, w, h, labels=True, sz=13, you="Du: 24"):
    """Ordrer per Rolle, til skala. Én akse, fire serier med form og navn."""
    series = {r: orders(r) for r in ROLES}
    vmax = 32
    def X(i):
        return x + (w - 2) * i / 35
    def Y(v):
        return y + h - h * v / vmax
    for gv in (0, 8, 16, 24, 32):
        p.l(x, Y(gv), x + w, Y(gv), LINE, .8)
        p.t(x - 5, Y(gv) + 4.5, str(gv), sz, 400, MUTE, "end")
    for wk in (1, 12, 24, 36):
        p.t(X(wk - 1), y + h + 17, f"Uke {wk}" if wk == 1 else str(wk), sz, 400, MUTE, "middle" if wk > 1 else "start")
    for r_ in ROLES:
        d = "M" + "L".join(f"{X(i):.1f} {Y(v):.1f}" for i, v in enumerate(series[r_]))
        p.add(f'<path d="{d}" fill="none" stroke="{SER[r_]}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"><title>{escape(r_)}: ordrer uke 1 til 36</title></path>')
    if labels:
        peaks = {"Detaljist": (6, -12, "start"), "Grossist": None, "Distributør": (14, -8, "middle"), "Fabrikk": (19, -8, "start")}
        for r_, spec in peaks.items():
            if not spec:
                continue
            i, dy, anc = spec
            mx = max(series[r_])
            idx = series[r_].index(mx)
            px_, py_ = X(idx), Y(mx)
            p.role(px_, py_, r_, 3.8, NIGHT, SER[r_], 1.6)
    # Saras 24
    sx, sy = X(10), Y(24)
    p.c(sx, sy, 5.5, LIME, NIGHT, 1.6)
    # direkte etiketter i tekstfarge, formen bærer serien
    p.t(X(10) - 9, Y(24) + 4, you, sz, 700, TXT, "end")
    p.t(X(17) + 10, Y(31) + 5, "Fabrikk 31", sz, 600, TXT)
    p.l(X(13), Y(28.2), X(13), Y(22.8), MUTE, 1)
    p.t(X(13), Y(29), "Distributør 22", sz, 600, TXT, "end")
    p.t(X(1), Y(13.5), "Detaljist", sz, 600, TXT)
    return X, Y


def page_debrief():
    p = Page("debrief", 2100, 1200, "Tråden: Gruppedebrief i fem steg",
             "En guidet samtale i tråden. Forklaringen er din melding, så kommer avsløringen som ett stille kort, så diagram, ditt øyeblikk og quiz. Pluss delt skjerm.", "#160A1C")
    p.t(36, 56, "Debriefen er en guidet samtale", 38, 800, ls=-.6)
    p.t(640, 56, "Demodata · Ingen åpen chat: valgte oppfølgingsspørsmål, ikke fritt felt", 15, 500, MUTE)
    S = .82
    fw = 390 * S
    gapx = (2100 - 80 - 5 * fw) / 4
    px = [40 + i * (fw + gapx) for i in range(5)]
    top = 86

    def hdr(p, title="Debrief · Spill 17"):
        p.r(160, 11, 70, 5, 2.5, LINE)
        p.icon(16, 36, "reply", 22, MINT, 2)
        p.t(46, 47, title, 16, 800)
        p.t(46, 65, "Demodata · Gruppedebrief", 13, 400, MUTE)

    def s1(p):
        hdr(p)
        presence(p, 13, 94, [("Detaljist", "Ida", "done", "har skrevet"), ("Distributør", "Mikkel", "open", "skriver"), ("Fabrikk", "Jonas", "done", "har skrevet")])
        items = [
            day("Fr. 4. des 21:20"),
            card("pen", "Først din Forklaring", "Spillet er ferdig. Før noe vises: hvorfor oppførte kjeden seg som den gjorde, og hva gjorde ordrene dine?", sz=15),
        ]
        lay_thread(p, items, 12, 136, 330, 366)
        # låst kort
        p.r(12, 340, 366, 176, 16, PANEL, LINE, 1, "6 5")
        cx = 195
        p.c(cx, 390, 26, RAISED, LINE, 1)
        p.icon(cx - 13, 377, "lock", 26, TXT, 2)
        p.t(cx, 442, "Det kundene faktisk kjøpte", 17, 800, TXT, "middle")
        p.t(cx, 468, "Låst til du har sendt Forklaringen", 14, 400, MUTE, "middle")
        p.t(cx, 492, "Bare du ser den. Den lagres uendret.", 14, 400, MUTE, "middle")
        # svarfelt
        p.r(12, 530, 366, 214, 14, RAISED, LIME, 1.5)
        ny = p.para(26, 560, "Alle manglet varer, så alle bestilte mer. Jeg tror kundene kjøpte mer og mer utover i spillet, og at Fabrikk ikke rakk å følge med.", 336, 16, 23, fill=TXT)
        p.t(26, 730, "25 ord", 13, 400, MUTE)
        p.r(12, 752, 366, 54, 13, LIME)
        p.t(180, 785, "Send Forklaring", 17, 800, INKD, "middle")
        p.icon(268, 768, "send", 22, INKD, 2.6)

    def s2(p):
        hdr(p)
        p.path(ticket_path(100, 84, 278, 62, 11), RAISED, LINE, 1)
        p.icon(112, 96, "lock", 14, MUTE, 2)
        p.t(132, 108, "Din Forklaring", 13, 700, MUTE)
        p.t(112, 130, "«...kundene kjøpte mer og mer...»", 14, 400, MUTE)
        p.add(f"<g>{slide(.5, 12.0, 1.6, 8)}")
        p.t(195, 262, "Det kundene kjøpte", 19, 600, MUTE, "middle")
        # 4 -> 8, drevet av tomrom
        p.t(102, 400, "4", 128, 800, TXT, "middle", ls=-2)
        p.path("M152 360H230 M212 340l20 20-20 20", "none", MINT, 4, 'stroke-linecap="round" stroke-linejoin="round"')
        p.t(288, 400, "8", 128, 800, TXT, "middle", ls=-2)
        # trapp til skala
        x0, w0, y0 = 40, 310, 500
        X = lambda i: x0 + w0 * i / 36
        Y = lambda v: y0 - 7 * v
        d = f"M{X(0)} {Y(4)}H{X(4)}V{Y(8)}H{X(36)}"
        p.l(x0, y0, x0 + w0, y0, LINE)
        p.path(d, "none", TXT, 3, 'stroke-linejoin="round"')
        p.c(X(4), Y(8), 4.5, MINT, NIGHT, 1.4)
        p.t(X(0), y0 + 20, "Uke 1", 13, 400, MUTE)
        p.t(X(4) + 8, Y(8) - 10, "Uke 5", 13, 500, TXT)
        p.t(x0 + w0, y0 + 20, "Uke 36", 13, 400, MUTE, "end")
        p.para(40, 556, "Fra uke 5 kjøpte kundene 8 kasser hver uke. Det endret seg aldri igjen.", 310, 19, 26, fill=TXT)
        p.add("</g>")
        p.para(40, 650, "Øvelsen heter Beer Game. Kjeden er bygd slik at akkurat dette skjer.", 310, 14, 19, fill=MUTE)
        p.t(40, 712, "Fra spillets logg, ikke KI-tekst", 13, 400, MUTE)
        p.r(12, 752, 366, 54, 13, LIME)
        p.t(180, 785, "Se hva det gjorde", 17, 800, INKD, "middle")
        p.icon(262, 768, "send", 22, INKD, 2.6)

    def s3(p):
        hdr(p)
        p.para(14, 106, "Kundene endret seg én gang. Ordrene vokste for hvert ledd.", 356, 18, 24, w=700, fill=TXT)
        p.r(12, 164, 366, 312, 16, PANEL, LINE, 1)
        p.t(26, 192, "Ordrer per Rolle, uke for uke", 15, 700)
        chart_orders(p, 50, 212, 314, 232)
        # forklaring + forsterkning: legend
        y = 490
        for i, r_ in enumerate(ROLES):
            yy = y + i * 34
            p.l(14, yy + 30, 376, yy + 30, LINE)
            p.l(16, yy + 15, 44, yy + 15, SER[r_], 3)
            p.role(30, yy + 15, r_, 5.5, NIGHT, SER[r_], 1.8)
            p.t(56, yy + 21, r_, 15, 400, TXT)
            mult = FX["amplification"][r_]
            bw_ = 120 * mult / 7.6
            p.r(196, yy + 9, bw_, 12, 2, SER[r_])
            p.t(376, yy + 21, f"{str(mult).replace('.', ',')}×", 17, 800, TXT, "end")
        p.kitag(14, 656, "Fra loggen. KI-generert tekst, kan ta feil")
        p.t(14, 690, "Spør videre", 14, 700)
        chips = ["Hvorfor vokser det?", "Hva så Jonas?"]
        cx = 14
        for c_ in chips:
            w_ = est(c_, 14) + 28
            p.r(cx, 700, w_, 36, 18, "none", MINT, 1.2)
            p.t(cx + 14, 723, c_, 14, 500, TXT)
            cx += w_ + 8
        p.t(14, 760, "3 spørsmål igjen. Ingen fritekst her.", 13, 400, MUTE)
        p.r(12, 772, 366, 44, 12, LIME)
        p.t(195, 800, "Til ditt øyeblikk", 16, 800, INKD, "middle")

    def s4(p):
        hdr(p, "Ditt øyeblikk · Uke 11")
        p.t(374, 47, "1 av 3", 13, 500, MUTE, "end")
        s = sara(11)
        # sitert kort fra tråden
        p.r(12, 80, 366, 146, 14, RAISED, LINE, 1)
        p.icon(24, 90, "reply", 16, MUTE, 2)
        p.t(46, 103, "Fra tråden din, Uke 11. Dette så du:", 13, 500, MUTE)
        for i, (lab, val, kind) in enumerate([("Lager", s["lager"], "solid"), ("Restordre", s["restordre"], "slash"), ("Ordre inn", s["innkommende_ordre"], "solid"), ("På vei", s["paa_vei_foer_ordre"], "hollow")]):
            cx = 24 + i * 88
            p.t(cx, 124, lab, 13, 500, MUTE)
            p.t(cx, 151, str(val), 24, 800, APR if kind == "slash" else MINT if kind == "hollow" else TXT)
        p.pips(24, 163, [(4, "hollow"), (4, "hollow"), (8, "hollow"), (24, "lime")], 6.2, 1.5, 5, h=8)
        p.t(24, 192, "Du bestilte **24**, din største ordre i spillet.", 14, 400, TXT, bw=800, bfill=LIME)
        p.t(24, 213, "Kost så langt: 68,00 kr", 13, 400, MUTE)
        # KI-fortelling
        y = 240
        p.t(14, y + 12, "Hva det kostet senere", 15, 800)
        w29 = sara(29)["lager"]
        later = sara(36)["kost_sum"] - sara(24)["kost_sum"]
        y = p.para(14, y + 36, f"Restordren steg til 40 i uke 22. Så kom alt på en gang: i uke 29 hadde du **{w29} kasser** på lager. Fra uke 25 til 36 kostet lageret **{kr(later)}**.", 362, 15, 21, fill=TXT)
        y += 10
        p.t(14, y + 8, "Hva de andre så samme Uke", 15, 800)
        y += 18
        for r_, n in [("Detaljist", "Ida"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]:
            d = seat(r_, 11)
            p.l(14, y, 376, y, LINE)
            p.role(26, y + 16, r_, 6, None, TXT, 1.5)
            p.t(42, y + 21, f"**{n}**", 14, 400, TXT, bw=700)
            p.t(100, y + 21, f"Lager {d['lager']} · Rest {d['restordre']} · Inn {d['innkommende_ordre']}", 13, 400, MUTE)
            p.t(376, y + 21, f"bestilte **{d['ordre']}**", 13, 400, MUTE, "end", bw=800, bfill=TXT)
            y += 30
        p.l(14, y, 376, y, LINE)
        y = p.para(14, y + 26, "Distributør hadde 14 på lager mens du manglet 13. Ordren du la denne uka, nådde Distributør først to uker senere. Ingen i kjeden kunne se det.", 362, 15, 21, fill=TXT)
        p.kitag(14, y + 8, "KI-generert, kan ta feil")
        cx = 14
        y += 26
        for c_ in ["Hvorfor kom ikke 24?", "Hva så Jonas?"]:
            w_ = est(c_, 14) + 28
            p.r(cx, y, w_, 34, 17, "none", MINT, 1.2)
            p.t(cx + 14, y + 22, c_, 14, 500, TXT)
            cx += w_ + 8
        p.t(14, y + 58, "3 spørsmål igjen. Ingen fritekst her.", 13, 400, MUTE)
        p.r(12, 772, 366, 44, 12, LIME)
        p.t(195, 800, "Til Debrief-quiz", 16, 800, INKD, "middle")

    def s5(p):
        hdr(p, "Debrief-quiz")
        p.t(374, 47, "Spørsmål 3", 13, 500, MUTE, "end")
        p.r(12, 84, 366, 100, 14, PANEL, LINE, 1)
        p.para(26, 114, "Kundene kjøpte 8 hver uke fra uke 5. Hvorfor bestilte Fabrikk 31 i uke 18?", 330, 16, 23, w=700, fill=TXT)
        opts = [("Kundene kjøpte stadig mer", "wrong"), ("Hvert ledd så bare ordren fra sin kunde, og det som var på vei kom sent", "open"), ("Fabrikken hadde for lite kapasitet", "open")]
        y = 196
        for s_, st in opts:
            ls_ = wrap(s_, 300, 15)
            h = 22 + len(ls_) * 20
            if st == "wrong":
                x_, w_ = 62, 316
                p.path(ticket_path(x_, y, w_, h + 24, 11), RAISED, APR, 1.5)
                p.t(x_ + 14, y + 26, ls_[0], 15, 500, TXT)
                p.icon(x_ + 12, y + 37, "x", 16, APR, 2.8)
                p.t(x_ + 34, y + 50, "Ikke riktig. Ditt første svar.", 13, 600, APR)
                y += h + 24 + 10
            else:
                p.r(12, y, 366, h, 12, "none", LINE, 1)
                for i, l_ in enumerate(ls_):
                    p.t(26, y + 26 + i * 20, l_, 15, 400, TXT)
                y += h + 8
        y += 6
        p.r(12, y, 366, 196, 14, PANEL, KIC, 1)
        p.t(26, y + 28, "Hvorfor", 15, 800)
        ny = p.para(26, y + 52, "Kundene sto stille på 8. Det Fabrikk så, var ordrene fra Distributør, og Distributør så ordrene fra deg. Hvert ledd la på for å ta igjen det som manglet, og det som allerede var på vei ble ikke regnet med.", 340, 15, 21, fill=TXT)
        p.kitag(26, ny + 8, "KI-generert, kan ta feil")
        y += 212
        p.r(12, y, 366, 54, 13, LIME)
        p.t(195, y + 33, "Prøv igjen", 17, 800, INKD, "middle")
        p.t(195, y + 82, "Quizen gir ingen karakter.", 13, 400, MUTE, "middle")

    fns = [s1, s2, s3, s4, s5]
    caps = [
        ("1  Forklaringen er din melding", "Du skriver først. Avsløringen ligger låst rett over."),
        ("2  Det stille kortet", "Bare 4 og 8. Ingen bakgrunn, ingen ekstra tall. Teksten glir sakte inn."),
        ("3  Samme diagram for alle", "Fire linjer, en akse. 1,8× ved Detaljist, 7,6× ved Fabrikk."),
        ("4  Svar på din egen boble", "KI siterer Uke 11 fra tråden din og forteller hva du ikke kunne se."),
        ("5  Feil svar blir forklart", "Svaret ditt er en boble. Forklaringen svarer på den."),
    ]
    for i, fn in enumerate(fns):
        phone(p, px[i] + 3, top, S, fn)
        p.t(px[i], top + 844 * S + 34, caps[i][0], 18, 800)
        p.para(px[i], top + 844 * S + 58, caps[i][1], fw, 15, 21, fill=MUTE)

    # delt skjerm
    sx, sy, sw, sh = 40, 900, 2020, 280
    p.r(sx, sy, sw, sh, 16, NIGHT, "#6A4676", 1.4)
    p.t(sx + 24, sy + 36, "Delt skjerm: gruppa ser samme steg", 20, 800)
    p.t(sx + 400, sy + 36, "Spill 17 · Bare felles diagrammer. Forklaringen og øyeblikkene dine blir på din egen telefon · Demodata", 14, 400, MUTE)
    rows_ = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
    cw = 270
    for i, r_ in enumerate(rows_):
        yy = sy + 56 + i * 52
        p.path(ticket_path(sx + 24, yy, cw, 46, 11), RAISED, LINE, 1)
        p.role(sx + 46, yy + 23, r_, 7, None, TXT, 1.6)
        p.t(sx + 62, yy + 28, r_, 16, 700)
        p.icon(sx + 182, yy + 15, "lock", 16, MINT, 2.2)
        p.t(sx + 203, yy + 28, "Forseglet", 14, 500, TXT)
    ax = sx + 340
    p.t(ax, sy + 84, "Det kundene kjøpte", 16, 500, MUTE)
    p.t(ax, sy + 196, "4", 112, 800, TXT, ls=-2)
    p.path(f"M{ax + 78} {sy + 158}H{ax + 142} M{ax + 124} {sy + 140}l18 18-18 18", "none", MINT, 4, 'stroke-linecap="round" stroke-linejoin="round"')
    p.t(ax + 154, sy + 196, "8", 112, 800, TXT, ls=-2)
    p.t(ax, sy + 240, "Fra uke 5. Så stille resten.", 17, 400, TXT)
    chx = ax + 300
    p.t(chx, sy + 76, "Ordrer per Rolle, uke for uke", 15, 600, MUTE)
    chart_orders(p, chx + 26, sy + 90, 910, 150, you="Grossist 24", sz=14)
    lx_ = chx + 960
    for i, r_ in enumerate(rows_):
        yy = sy + 88 + i * 38
        p.l(lx_, yy + 8, lx_ + 30, yy + 8, SER[r_], 3)
        p.role(lx_ + 15, yy + 8, r_, 5.5, NIGHT, SER[r_], 1.8)
        p.t(lx_ + 40, yy + 14, r_, 15, 400, TXT)
        p.t(lx_ + 40, yy + 31 - 0, f"{str(FX['amplification'][r_]).replace('.', ',')}×", 15, 800, TXT)
    p.save("07-debrief.svg")


# ---------------------------------------------------------------- 08 Oversikt

def status_mark(p, x, y, st):
    if st == "ferdig":
        p.c(x, y, 7, PLUM)
        p.icon(x - 5.5, y - 5.5, "check", 11, "#FFFFFF", 2.8)
    elif st == "pågår":
        p.c(x, y, 7, "none", PLUM, 1.6)
        p.path(f"M{x - 2.5} {y - 4}L{x + 4} {y}L{x - 2.5} {y + 4}Z", PLUM)
    elif st == "venter":
        p.c(x, y, 7, URGBG, URG, 1.6)
        p.icon(x - 5, y - 5, "clock", 10, URG, 2.6)
    else:
        p.r(x - 7, y - 7, 14, 14, 3, "#E6DDEA", PLUM, 1.2)
        p.icon(x - 5, y - 5, "pause", 10, PLUM, 3)


def page_oversikt():
    p = Page("oversikt", 1600, 1000, "Tråden: faglærerens Oversikt over 60 Klassespill",
             "To-kolonne innboks: Trenger oppmerksomhet øverst sortert etter hastverk, med tiltak i ett trykk. Trakten under. Til høyre tabell over alle 60.", PAPER)
    games = FX["class_games"]
    p.r(0, 0, 1600, 60, 0, INK)
    wordmark(p, 22, 38, TXT, 20)
    p.t(138, 37, "IBE160 · class-of-1994 · Oversikt", 16, 500, "#E6D9EA")
    p.t(1216, 37, "Demodata", 14, 500, "#E6D9EA")
    p.r(1298, 13, 150, 34, 9, LIME)
    p.icon(1309, 21, "mail", 18, INKD, 2)
    p.t(1335, 35.5, "Send Melding", 14, 800, INKD)
    p.t(1462, 37, "Bård, Faglærer", 14, 500, "#E6D9EA")
    # filter
    y = 72
    n = {k: sum(1 for g in games if g["status"] == k) for k in ["ferdig", "pågår", "venter", "pauset"]}
    ki_g = sum(1 for g in games if g["ki_seter"])
    chips = [("Alle", 60, True, None), ("Venter", n["venter"], False, "venter"), ("Pågår", n["pågår"] + n["pauset"], False, "pågår"), ("Herav pauset", n["pauset"], False, "pauset"),
             ("Ferdig", n["ferdig"], False, "ferdig"), ("Med KI-seter", ki_g, False, "ki")]
    cx = 24
    for lab, val, on, kind in chips:
        w_ = est(lab, 14) + est(str(val), 14, True) + (44 if kind else 26)
        p.r(cx, y, w_, 34, 17, INK if on else CARD, INK if on else LINEL, 1)
        tx = cx + 13
        if kind == "ki":
            p.ki(cx + 15, y + 17, 8, False)
            tx = cx + 29
        elif kind:
            status_mark(p, cx + 15, y + 17, kind)
            tx = cx + 29
        p.t(tx, y + 22, f"{lab} **{val}**", 14, 400, "#FFFFFF" if on else INK, bw=800)
        cx += w_ + 7
    p.r(1330, y, 246, 34, 17, CARD, LINEL, 1)
    p.icon(1342, y + 8, "search", 18, MUTEL, 2)
    p.t(1368, y + 22, "Finn spill eller student", 14, 400, MUTEL)
    # venstre: innboks
    lx, lw = 24, 552
    y = 142
    p.t(lx, y, "Trenger oppmerksomhet", 22, 800, INK)
    p.t(lx + lw, y, "Sortert etter tid til KI overtar", 14, 400, MUTEL, "end")
    waiting = sorted([g for g in games if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])
    y += 14
    for i, g in enumerate(waiting):
        hot = i == 0
        h = 106 if hot else 74
        p.r(lx, y, lw, h, 12, INK if hot else CARD, None if hot else LINEL, 1)
        ink = "#FFFFFF" if hot else INK
        mute = "#E6D9EA" if hot else MUTEL
        p.icon(lx + 14, y + 14, "clock", 22, APR if hot else URG, 2)
        p.t(lx + 46, y + 25, f"**Spill {g['spill']}** venter på {g['navn']}, {g['venter_paa']}", 16, 400, ink, bw=800)
        left = 24 - g["ventet_timer"]
        p.t(lx + 46, y + 47, f"Ventet {g['ventet_timer']} t · KI overtar om {left} t · Uke {g['uke']}" + (f" · {g['ki_seter']} KI-sete" if g["ki_seter"] else ""), 14, 400, mute)
        # tid brukt, til skala 0-24 t
        bx, bw_ = lx + 46, 300
        by = y + 56
        p.r(bx, by, bw_, 6, 3, "#5A3566" if hot else LINEL)
        p.r(bx, by, bw_ * g["ventet_timer"] / 24, 6, 3, APR if hot else URG)
        if hot:
            p.t(lx + 46, y + 90, "Ett trykk, så får Noah en Melding.", 14, 400, "#E6D9EA")
            lbtn(p, lx + lw - 164, y + 14, 150, 38, "Send Melding", icon="mail", st=INK, sz=14)
            lbtn(p, lx + lw - 164, y + 58, 150, 38, "KI overtar nå", "#3B2146", "#FFFFFF", "#8D6D98", sz=14)
        else:
            lbtn(p, lx + lw - 134, y + 19, 120, 36, "Send Melding", CARD, INK, INK, sz=14)
        y += h + 7
    # pauser
    y += 5
    p.t(lx, y + 12, "Pauset, ingen tiltak nå", 15, 800, INK)
    y += 22
    for g in [g for g in games if g["status"] == "pauset"]:
        p.r(lx, y, lw, 38, 10, "#ECE3EA")
        status_mark(p, lx + 18, y + 19, "pauset")
        p.t(lx + 36, y + 24.5, f"**Spill {g['spill']}**, Uke {g['uke']}. Fortsetter {g['fortsetter']}." + (f" {g['ki_seter']} KI-sete." if g["ki_seter"] else ""), 14, 400, INK, bw=800)
        y += 43
    # trakt
    y += 12
    p.t(lx, y + 12, "Trakten", 22, 800, INK)
    p.t(lx + lw, y + 12, "Studenter per steg, av 240", 14, 400, MUTEL, "end")
    y += 26
    F = FX["funnel"]
    labs = [("registrert", "Registrert"), ("klassespill_ferdig", "Klassespill ferdig"), ("debrief_ferdig", "Debrief ferdig"), ("quiz_bestått", "Quiz bestått"),
            ("replay_ferdig", "Replay ferdig"), ("test_levert", "Test levert"), ("ki_vurdering_klar", "KI-vurdering klar")]
    bx = lx + 150
    bw_ = lw - 150 - 50
    fh = 24
    avail = 1000 - 18 - y
    fh = min(40, avail / 7)
    for k, lab in labs:
        v = F[k]
        p.t(lx, y + fh * .62, lab, 14, 400, INK)
        ww = max(bw_ * v / 240, 2)
        p.add(f'<rect x="{bx}" y="{y + 2:.1f}" width="{ww:.1f}" height="{fh - 7:.1f}" rx="3" fill="{PLUM}"><title>{escape(lab)}: {v}</title></rect>')
        p.t(lx + lw, y + fh * .62, str(v), 15, 800, INK, "end")
        y += fh
    # høyre: tabell
    tx0 = 600
    p.r(tx0, 124, 976, 866, 13, CARD, LINEL, 1)
    p.t(tx0 + 18, 156, "Alle 60", 22, 800, INK)
    p.t(tx0 + 100, 156, "Etter spillnummer. Kostnaden er kjedens totalkostnad så langt.", 14, 400, MUTEL)
    colw = (976 - 36 - 20) / 2
    rowh = 26.6
    top = 192
    for c_ in range(2):
        cx = tx0 + 18 + c_ * (colw + 20)
        p.t(cx, top - 8, "Spill", 13, 700, MUTEL)
        p.t(cx + 50, top - 8, "Status", 13, 700, MUTEL)
        p.t(cx + 148, top - 8, "Uke", 13, 700, MUTEL, "end")
        p.t(cx + 160, top - 8, "Venter på, pause", 13, 700, MUTEL)
        p.t(cx + colw - 62, top - 8, "KI", 13, 700, MUTEL, "end")
        p.t(cx + colw, top - 8, "Kostnad", 13, 700, MUTEL, "end")
        p.l(cx, top - 1, cx + colw, top - 1, INK, 1)
    for i, g in enumerate(games):
        c_ = 0 if i < 30 else 1
        cx = tx0 + 18 + c_ * (colw + 20)
        ry = top + (i % 30) * rowh
        st = g["status"]
        hot = g.get("ventet_timer", 0) >= 23
        if st == "venter":
            p.r(cx - 6, ry, colw + 12, rowh - 2, 5, URGBG if not hot else INK)
        mine = g["spill"] == 17
        if mine:
            p.r(cx - 6, ry, colw + 12, rowh - 2, 5, LIMEBG)
        ink = "#FFFFFF" if hot else INK
        dimmed = st == "ferdig"
        fill = MUTEL if dimmed else ink
        p.t(cx + 28, ry + 18, str(g["spill"]), 14, 700, ink if not dimmed else MUTEL, "end")
        if hot:
            p.c(cx + 50 + 7, ry + 12, 7, APR)
            p.icon(cx + 52, ry + 7, "clock", 10, INK, 2.6)
        else:
            status_mark(p, cx + 57, ry + 12, st)
        p.t(cx + 71, ry + 18, st.capitalize(), 13, 400, fill)
        p.t(cx + 148, ry + 18, str(g["uke"]), 14, 400, fill, "end")
        if st == "venter":
            p.t(cx + 160, ry + 18, f"**{g['navn']}** {g['venter_paa']}, {g['ventet_timer']} t", 13, 400, ink, bw=700)
        elif st == "pauset":
            p.t(cx + 160, ry + 18, g["fortsetter"].capitalize(), 13, 400, ink)
        if g["ki_seter"]:
            p.ki(cx + colw - 84, ry + 12.5, 7.5, not hot and False)
            p.t(cx + colw - 62, ry + 18, str(g["ki_seter"]), 14, 700, ink if not dimmed else MUTEL, "end")
        p.t(cx + colw, ry + 18, fmt_num(g["kjedekost"], 0), 14, 400, fill, "end")
        if not (st == "venter" or mine) and (i % 30) < 29:
            p.l(cx, ry + rowh - 1, cx + colw, ry + rowh - 1, "#EFE7ED", 1)
    p.save("08-laerer-oversikt.svg")


# ---------------------------------------------------------------- 09 Alle sider

def page_alle():
    p = Page("alle", 2000, 1400, "Tråden: alle andre sider",
             "Kontaktark i konseptets språk, gruppert per rolle: Student, Faglærer og Admin, med tittel og én linje per side.", NIGHT)
    p.t(36, 58, "Resten av produktet, i samme tråd", 36, 800, ls=-.6)
    p.t(700, 58, "Lavere detaljnivå · Demodata", 15, 500, MUTE)

    def m_sys(p, x, y, w, txt, ic="truck", sz=11.5):
        p.r(x, y, w, 24, 7, PANEL)
        p.icon(x + 5, y + 5, ic, 14, MINT, 2)
        p.t(x + 23, y + 16.5, txt, sz, 400, TXT, bw=800)

    def m_tick(p, x2, y, n, lime=False, w=64):
        p.path(ticket_path(x2 - w, y, w, 30, 8, 5), LIME if lime else RAISED, None if lime else LINE, 1)
        p.t(x2 - w + 8, y + 22, str(n), 18, 800, INKD if lime else TXT)

    def m_btn(p, x, y, w, txt, h=26):
        p.r(x, y, w, h, 7, LIME)
        p.t(x + w / 2, y + h / 2 + 4, txt, 11.5, 800, INKD, "middle")

    def m_lines(p, x, y, w, n, col=LINE):
        for i in range(n):
            p.r(x, y + i * 11, w * (1 if i < n - 1 else .62), 5, 2.5, col)

    # ---- Student
    tw, th = 176, 276

    def tile_s(i, row_y, title, line, draw):
        x = 36 + i * ((2000 - 72 - tw) / 9)
        p.add(f'<g transform="translate({x:.1f} {row_y})">')
        p.r(0, 0, tw, th, 18, PANEL, LINE, 1)
        cid = p.uid("t")
        p.add(f'<clipPath id="{cid}"><rect width="{tw}" height="{th}" rx="18"/></clipPath><g clip-path="url(#{cid})">')
        p.r(0, 0, tw, th, 0, NIGHT)
        draw(p)
        p.add("</g>")
        ny = p.para(0, th + 24, title, tw - 4, 15, 19, w=800, fill=TXT)
        p.para(0, ny + 1, line, tw, 13, 17, fill=MUTE)
        p.add("</g>")

    def s_inv(p):
        wordmark(p, 10, 28, TXT, 13)
        m_sys(p, 8, 42, 160, "Bård har invitert deg", "mail")
        for i, l_ in enumerate(["Navn", "E-post", "Passord"]):
            p.t(12, 86 + i * 44, l_, 11, 500, MUTE)
            p.r(12, 91 + i * 44, 152, 22, 5, PANEL, LINE, 1)
        m_btn(p, 12, 226, 152, "Bli med")

    def s_login(p):
        wordmark(p, 10, 28, TXT, 13)
        p.para(12, 70, "Kom inn igjen i tråden din", 150, 15, 19, w=800, fill=TXT)
        for i, l_ in enumerate(["E-post", "Passord"]):
            p.t(12, 122 + i * 44, l_, 11, 500, MUTE)
            p.r(12, 127 + i * 44, 152, 22, 5, PANEL, LINE, 1)
        m_btn(p, 12, 210, 152, "Logg inn")
        p.t(88, 256, "Ny? Bruk Invitasjonen", 11, 400, MUTE, "middle")

    def s_rules(p):
        m_sys(p, 8, 16, 160, "Du er **Grossist**", "users")
        m_sys(p, 8, 44, 160, "Kunden din bestiller", "inbox")
        m_sys(p, 8, 72, 160, "Du sender det du har", "boxout")
        m_sys(p, 8, 100, 160, "Det du bestiller kommer", "truck", 11)
        p.t(12, 142, "Lager 0,50 kr per kasse", 11.5, 400, TXT)
        p.t(12, 158, "Restordre 1,00 kr per kasse", 11.5, 400, TXT)
        p.t(12, 176, "Lavest kostnad for hele kjeden", 10.5, 400, MUTE)
        p.t(12, 192, "Uke 1–4 er Veiledede uker", 11.5, 600, MINT)
        m_btn(p, 12, 226, 152, "Jeg er klar")

    def s_start(p):
        p.t(12, 28, "Startoppgave", 14, 800)
        m_sys(p, 8, 40, 160, "Lager 2, Restordre 0", "grid")
        m_sys(p, 8, 68, 160, "Ny ordre: **5**", "inbox")
        p.para(12, 112, "Hvor mange kan du sende nå?", 150, 12.5, 16, fill=TXT)
        for i, n in enumerate([2, 5, 3]):
            p.r(12 + i * 52, 150, 46, 32, 8, LIMEBG if False else "none", LIME if n == 2 else LINE, 1.4)
            p.t(35 + i * 52, 171, str(n), 15, 700, TXT, "middle")
        p.icon(14, 196, "check", 15, MINT, 2.6)
        p.t(34, 208, "Riktig: du har bare 2", 11.5, 500, TXT)
        m_btn(p, 12, 232, 152, "Neste", 24)

    def s_replay(p):
        p.t(12, 26, "Replay · Grossist", 13, 800)
        p.ki(18, 42, 7)
        p.t(30, 46, "3 KI-spillere", 11.5, 600, KIC)
        m_sys(p, 8, 58, 160, "Lastebilen kom med **4**", "truck")
        m_sys(p, 8, 85, 160, "Ny ordre: **4**", "inbox")
        m_tick(p, 168, 116, 4)
        p.r(8, 152, 160, 58, 10, RAISED, LINE, 1)
        p.t(16, 172, "Uke 5", 13, 800)
        p.t(16, 196, "Lager 12  På vei 12", 11.5, 400, TXT)
        p.r(8, 218, 108, 30, 7, PANEL, LINE, 1)
        p.r(120, 218, 48, 30, 7, LIME)
        p.t(144, 238, "Send", 11.5, 800, INKD, "middle")

    def s_rgj(p):
        p.t(12, 26, "Replay-gjennomgang", 13, 800)
        p.r(8, 38, 160, 74, 9, PANEL, LINE, 1)
        hist = orders("Grossist")[:24]
        p.path("M" + "L".join(f"{14 + j * 6.4:.1f} {104 - v * 2.2:.1f}" for j, v in enumerate(hist)), "none", MINT, 1.6)
        p.para(12, 130, "Her ventet du to uker før du la inn mer. Det ga jevnere lager.", 152, 12, 16, fill=TXT)
        p.ki(18, 208, 7)
        p.t(30, 212, "KI-generert", 11.5, 600, KIC)
        m_btn(p, 12, 232, 152, "Til Individuell test", 24)

    def s_test(p):
        p.t(12, 24, "Individuell test", 13, 800)
        p.t(12, 42, "Flervalg", 11.5, 700, MINT)
        for i in range(2):
            p.r(12, 49 + i * 19, 152, 15, 5, "none", LIME if i == 0 else LINE, 1)
        p.t(12, 104, "Tegn lageret i bakeriet", 11.5, 700, MINT)
        p.r(12, 110, 152, 60, 5, PANEL, LINE, 1)
        p.path("M16 160L44 158L60 126L92 130L124 148L160 150", "none", LIME, 2)
        p.t(12, 188, "Langsvar", 11.5, 700, MINT)
        p.r(12, 194, 152, 40, 5, PANEL, LINE, 1)
        m_lines(p, 18, 202, 138, 3)
        p.t(12, 252, "Lagret. Kan fortsettes.", 11, 400, MUTE)

    def s_vurd(p):
        p.ki(18, 22, 8)
        p.t(32, 27, "KI-vurdering", 13, 800)
        p.para(12, 50, "Teller ikke. Er aldri en karakter.", 150, 12.5, 16, w=700, fill=TXT)
        p.r(8, 92, 160, 62, 9, PANEL, KIC, 1)
        p.para(16, 112, "Du viser til uke 11 og forklarer forsinkelsen presist.", 146, 11.5, 15, fill=TXT)
        p.r(8, 160, 160, 62, 9, PANEL, KIC, 1)
        p.para(16, 180, "Forslaget ditt om lager mangler et tall å støtte seg på.", 146, 11.5, 15, fill=TXT)
        p.t(12, 244, "KI-generert, kan ta feil", 11, 500, KIC)

    def s_pdf(p):
        p.r(16, 16, 144, 200, 3, "#F6F0F3")
        p.t(28, 42, "Studentrapport", 12.5, 800, INK)
        p.t(28, 58, "Sara, IBE160", 11, 400, INK)
        p.l(28, 66, 148, 66, LINEL)
        hist = orders("Grossist")[:30]
        p.path("M" + "L".join(f"{28 + j * 4:.1f} {120 - v * 1.8:.1f}" for j, v in enumerate(hist)), "none", PLUM, 1.4)
        m_lines(p, 28, 132, 120, 5, LINEL)
        p.t(28, 204, "KI-tekst er merket", 10.5, 600, KID)
        m_btn(p, 12, 232, 152, "Last ned PDF", 24)

    def s_all(p):
        p.t(12, 24, "Alle spill side om side", 12, 800)
        for j, g in enumerate(FX["class_games"][:28]):
            pass
        for j in range(4):
            yy = 38 + j * 54
            p.r(8, yy, 160, 48, 7, PANEL, LIME if j == 1 else LINE, 1.2 if j == 1 else 1)
            p.t(14, yy + 18, ["Spill 3", "Spill 17, ditt", "Spill 22", "Spill 40"][j], 11.5, 700)
            vals = orders(ROLES[j])[:30]
            p.path("M" + "L".join(f"{14 + v_i * 5:.1f} {yy + 44 - v * 1:.1f}" for v_i, v in enumerate(vals)), "none", MINT, 1.1)

    p.t(36, 112, "Student", 24, 800)
    y0 = 128
    st = [("Invitasjon og registrering", "Første melding i tråden, og kontoen på ett kort.", s_inv),
          ("Logg inn", "E-post og passord. Rett inn i tråden.", s_login),
          ("Regler før første ordre", "Reglene som korte meldinger, ikke en manual.", s_rules),
          ("Startoppgave", "Øv på lager og restordre før spillet.", s_start),
          ("Replay", "Samme tråd mot tre merkede KI-spillere.", s_replay),
          ("Replay-gjennomgang", "Kort KI-gjennomgang av runden din.", s_rgj),
          ("Individuell test", "Flervalg, tegneoppgave og langsvar over kvelder.", s_test),
          ("KI-vurdering", "Tilbakemelding som sier selv at den ikke teller.", s_vurd),
          ("Studentrapport (PDF)", "Hele reisen samlet i et dokument.", s_pdf),
          ("Alle spill side om side", "Se kurvene fra klassen etter Debriefen.", s_all)]
    for i, (a_, b_, fn) in enumerate(st):
        tile_s(i, y0, a_, b_, fn)

    # ---- Faglærer
    fw_, fh_ = 226, 158

    def tile_f(i, row_y, title, line, draw, n=8):
        x = 36 + i * ((2000 - 72 - fw_) / max(n - 1, 1))
        p.add(f'<g transform="translate({x:.1f} {row_y})">')
        p.r(0, 0, fw_, fh_, 9, PAPER, LINEL, 1)
        cid = p.uid("f")
        p.add(f'<clipPath id="{cid}"><rect width="{fw_}" height="{fh_}" rx="9"/></clipPath><g clip-path="url(#{cid})">')
        draw(p)
        p.add("</g>")
        p.t(0, fh_ + 24, title, 15, 800)
        p.para(0, fh_ + 44, line, fw_ - 6, 13, 17, fill=MUTE)
        p.add("</g>")

    def l_row(p, x, y, w, txt, col=INK, hot=False):
        p.r(x, y, w, 22, 5, URGBG if hot else CARD, URG if hot else LINEL, 1)
        p.t(x + 8, y + 15.5, txt, 11.5, 400, col, bw=800)

    def f_home(p):
        p.t(10, 22, "Lærerhjem", 13, 800, INK)
        l_row(p, 10, 32, 206, "**IBE160** class-of-1994 · 60 spill")
        l_row(p, 10, 58, 206, "**Spill 2** venter 23 t", URG, True)
        l_row(p, 10, 84, 206, "**LOG200** utkast · ingen Invitasjon")
        lbtn(p, 10, 116, 110, 28, "Ny Klasse", sz=12)

    def f_rapp(p):
        p.t(10, 22, "Klasserapport", 13, 800, INK)
        for j, (k, v) in enumerate([("Registrert", 240), ("Ferdig", 164), ("Debrief", 121), ("Quiz", 97), ("Replay", 58)]):
            yy = 34 + j * 20
            p.t(10, yy + 12, k, 11.5, 400, INK)
            p.r(70, yy + 2, 120 * v / 240, 12, 2, PLUM)
            p.t(216, yy + 12, str(v), 11.5, 700, INK, "end")
        p.t(10, 150, "Eksporter PDF", 11.5, 700, PLUM)

    def f_inn(p):
        p.t(10, 22, "Spillinnsikt · Spill 17", 13, 800, INK)
        p.r(10, 32, 206, 76, 5, CARD, LINEL, 1)
        for r_ in ROLES:
            vals = orders(r_)
            p.path("M" + "L".join(f"{14 + j * 5.6:.1f} {104 - v * 2.2:.1f}" for j, v in enumerate(vals)), "none", {"Detaljist": "#1F7A9C", "Grossist": "#5F7610", "Distributør": "#6E4CCB", "Fabrikk": "#B94D1E"}[r_], 1.2)
        p.t(10, 126, "Uke 11: Grossist bestilte 24", 11.5, 700, INK)
        p.t(10, 144, "Uke for uke, med KI-uker merket", 11, 400, MUTEL)

    def f_stud(p):
        p.t(10, 22, "Sara Berg", 13, 800, INK)
        p.t(10, 38, "Spill 17 · Grossist", 11.5, 400, MUTEL)
        for j, s_ in enumerate(["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]):
            yy = 50 + j * 17
            p.c(16, yy + 6, 5, PLUM if j < 1 else "none", PLUM, 1.2)
            p.t(28, yy + 10, s_, 11.5, 400, INK)
            p.t(216, yy + 10, "Pågår" if j == 0 else "Ikke startet", 11, 400, MUTEL, "end")

    def f_plen(p):
        p.r(0, 0, fw_, fh_, 0, NIGHT)
        p.t(10, 22, "Plenum: alle side om side", 12.5, 800, TXT)
        cols = 10
        for j in range(30):
            cx = 10 + (j % cols) * 20.8
            cy = 32 + (j // cols) * 38
            p.r(cx, cy, 18, 34, 2, PANEL)
            vals = orders(ROLES[3 if j % 2 else 1])[::4]
            k_ = (j % 5 + 3) / 7
            p.path("M" + "L".join(f"{cx + 1 + vi * 1.8:.1f} {cy + 32 - v * .9 * k_:.1f}" for vi, v in enumerate(vals)), "none", MINT, .9)

    def f_tverr(p):
        p.t(10, 22, "Tverrklasse-statistikk", 13, 800, INK)
        names = ["class-of-1994", "class-of-1993", "class-of-1992"]
        vals_ = [164, 201, 188]
        for j in range(3):
            yy = 38 + j * 34
            p.t(10, yy + 4, names[j], 11.5, 500, INK)
            p.r(10, yy + 9, 190 * vals_[j] / 240, 10, 2, PLUM)
            p.t(216, yy + 18, str(vals_[j]), 11.5, 700, INK, "end")
        p.t(10, 150, "Illustrasjon: ferdige per klasse", 11, 400, MUTEL)

    def f_med(p):
        p.t(10, 22, "Meldinger", 13, 800, INK)
        p.r(10, 32, 206, 46, 6, CARD, LINEL, 1)
        p.t(18, 50, "Til: alle som venter (4)", 11.5, 700, INK)
        p.t(18, 68, "Spillfrist er ti. 8. des. Bestill i kveld.", 11, 400, INK)
        lbtn(p, 136, 86, 80, 26, "Send", sz=12)
        p.t(10, 130, "Hele Klasseøkten · ett spill · én student", 11, 400, MUTEL)
        p.t(10, 148, "Svar går ikke mellom spillere", 11, 400, MUTEL)

    def f_test(p):
        p.t(10, 22, "Lærers testspill", 13, 800, INK)
        p.t(10, 38, "Privat. Tre KI-spillere. Teller ikke.", 11.5, 400, MUTEL)
        p.r(10, 48, 206, 26, 5, INK)
        p.t(18, 65, "Lastebilen kom med 4", 11.5, 500, "#FFFFFF")
        p.r(10, 78, 206, 26, 5, INK)
        p.t(18, 95, "Lager 12 · På vei 12 · Uke 2", 11.5, 500, "#FFFFFF")
        lticket(p, 216, 110, 70, 30)
        p.t(160, 131, "4", 16, 800, "#FFFFFF")

    p.t(36, 520, "Faglærer", 24, 800)
    y1 = 536
    fg = [("Lærerhjem med klasser", "Klassene som tråder, det som haster øverst.", f_home),
          ("Klasserapport", "Trakt og fullføring, klar som PDF.", f_rapp),
          ("Spillinnsikt", "Ett spill uke for uke, med KI-uker merket.", f_inn),
          ("Studentside", "Én students steg, frister og sete.", f_stud),
          ("Spill alle side om side", "Mørk plenumsvisning for storskjerm.", f_plen),
          ("Tverrklasse-statistikk", "Sammenlign klasser over år. Ikke studenter.", f_tverr),
          ("Meldinger", "Til hele økten, ett spill eller én student.", f_med),
          ("Lærers testspill", "Prøv innstillingene i en privat tråd.", f_test)]
    for i, (a_, b_, fn) in enumerate(fg):
        tile_f(i, y1, a_, b_, fn)

    # ---- Admin
    def a_home(p):
        p.t(10, 22, "Admin-område", 13, 800, INK)
        l_row(p, 10, 32, 206, "**Institusjoner** 1")
        l_row(p, 10, 58, 206, "**Klasseøkter** 1 aktiv")
        l_row(p, 10, 84, 206, "**KI-status** normal")
        l_row(p, 10, 110, 206, "**Lærertilgang** 2 venter", URG, True)

    def a_users(p):
        p.t(10, 22, "Brukere og roller", 13, 800, INK)
        for j, (n_, r_) in enumerate([("Bård", "Faglærer"), ("Hilde", "Hjelpelærer"), ("Sara Berg", "Student"), ("Pia", "Admin")]):
            yy = 34 + j * 28
            p.l(10, yy, 216, yy, LINEL)
            p.t(10, yy + 19, n_, 12, 600, INK)
            p.r(130, yy + 5, 86, 19, 9, CARD, LINEL, 1)
            p.t(173, yy + 19, r_, 11, 500, INK, "middle")

    def a_cost(p):
        p.t(10, 22, "KI-kostnad", 13, 800, INK)
        p.t(10, 38, "Per Klasseøkt. Illustrasjon.", 11, 400, MUTEL)
        vals_ = [12, 18, 24, 30, 22, 16, 28, 34, 26, 14, 20, 12]
        for j, v in enumerate(vals_):
            p.r(10 + j * 17, 134 - v * 2.3, 13, v * 2.3, 2, PLUM)
        p.l(10, 134, 216, 134, INK)
        p.t(10, 150, "Uke for uke", 11, 400, MUTEL)

    p.t(36, 816, "Admin", 24, 800)
    y2 = 832
    ad = [("Admin-område", "Driftsbilde og forespørsler om lærertilgang.", a_home),
          ("Brukere og roller", "Hvem er hva, per institusjon.", a_users),
          ("KI-kostnad", "Forbruk per Klasseøkt, med tak.", a_cost)]
    for i, (a_, b_, fn) in enumerate(ad):
        tile_f(i, y2, a_, b_, fn, n=8)
    # systemforklaring til høyre: legenden for hele konseptet
    lx = 36 + 3 * ((2000 - 72 - fw_) / 7) + 20
    p.t(lx, 846, "Språket går igjen overalt", 24, 800)
    y = 884
    p.pips(lx, y, [(1, "solid")], 12, 0)
    p.t(lx + 24, y + 11, "Lager: fylt kasse", 16, 400)
    p.pips(lx + 300, y, [(1, "hollow")], 12, 0)
    p.t(lx + 324, y + 11, "På vei: tom kasse", 16, 400)
    p.pips(lx + 600, y, [(1, "slash")], 12, 0)
    p.t(lx + 624, y + 11, "Restordre: strøket kasse", 16, 400)
    y += 40
    p.path(ticket_path(lx, y - 4, 22, 20, 6, 3), LIME)
    p.t(lx + 30, y + 11, "Din ordre: fraktlapp med klippet hjørne", 16, 400)
    p.ki(lx + 512, y + 6, 9)
    p.t(lx + 528, y + 11, "KI: alltid sekskant + bokstavene", 16, 400)
    y += 40
    for i, r_ in enumerate(ROLES):
        p.role(lx + 8 + i * 150, y + 6, r_, 7, None, TXT, 1.6)
        p.t(lx + 24 + i * 150, y + 11, r_, 16, 400)
    y += 62
    p.para(lx, y, "Faglærer har lys flate fordi det brukes på dagtid på laptop. Student og Debrief er mørke fordi de brukes om kvelden. Plenumsvisningen er mørk fordi den skal på storskjerm.", 860, 16, 24, fill=MUTE)
    # frister nederst
    p.t(36, 1120, "Fellesdeler", 24, 800)
    y = 1146
    p.r(36, y, 1928, 214, 14, PANEL, LINE, 1)
    for nx_, note in [(60, "Form og tekst, aldri farge alene"), (420, "Tomme kasser til varene er kommet"), (720, "Levering, ordre og sendt, i samme rekkefølge"), (1100, "Avtalt tid står på kortet")]:
        p.t(nx_, y + 190, note, 15, 400, MUTE)
    parts = [
        ("Presence-linje", lambda x, yy: presence(p, x, yy + 18, [("Fabrikk", "Jonas", "wait", "tenker, 3 min"), ("Fabrikk", "", "ki", "KI-spiller har bestilt"), ("Distributør", "Mikkel", "done", "har bestilt")])),
        ("Ordreboble", lambda x, yy: order(8, 10, "vei")[1](p, x, yy, 200)),
        ("Systemmelding", lambda x, yy: sysm("truck", "Lastebilen kom med **4 kasser**")[1](p, x, yy, 320)),
        ("Pausekort", lambda x, yy: card("pause", "Spillet er på pause", "Dere fortsetter to. 3. des 14:15.", sz=14)[1](p, x, yy, 300)),
    ]
    xs = [60, 420, 720, 1100]
    for (name, fn), x in zip(parts, xs):
        p.t(x, y + 36, name, 15, 800, MINT)
        fn(x, y + 54)
    p.t(1460, y + 36, "Tomtilstand i tråden", 15, 800, MINT)
    p.icon(1460, y + 54, "clock", 22, MUTE)
    p.para(1492, y + 70, "Ingen spill ennå. Rollen din kommer når fordelingen er bekreftet.", 430, 16, 23, fill=TXT)
    p.save("09-alle-sider.svg")


def main():
    page_landing()
    page_klasse()
    page_okt()
    page_hjem()
    page_spill()
    page_dynamikk()
    page_debrief()
    page_oversikt()
    page_alle()


if __name__ == "__main__":
    main()
