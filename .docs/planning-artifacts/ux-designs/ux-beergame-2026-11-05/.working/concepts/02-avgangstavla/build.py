"""Konsept 02 Avgangstavla («Avgang»): genererer 9 SVG-er fra ../_shared/fixture.json.

Alt språk er bygd av én primitiv: flaps(), en rad split-flap-klaffer. Status er koblingslinjer
(jack()), aldri farge. Kjør: uv run python build.py
"""
import json
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WK = {w["week"]: w for w in FX["weeks"]}
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]


def seat(week, role="Grossist"):
    return WK[week]["seats"][role]


def history(role="Grossist", upto=10):
    return [seat(w, role)["ordre"] for w in range(1, upto + 1)]


def arrivals(week, order_this_week=None):
    """Radene «om N uker» for Grossist, avledet fra ordrehistorikk og Distributørens sendinger."""
    rows = [
        (1, seat(week - 1, "Distributør")["sendt"], "ship"),
        (2, seat(week, "Distributør")["sendt"], "ship"),
        (3, seat(week - 1)["ordre"], "ord"),
    ]
    if order_this_week is not None:
        rows.append((4, order_this_week, "new"))
    return rows


# Sjekk at avledningen stemmer med fixture: 4+4+8 = 16 og 4+8+24 = 36.
assert sum(r[1] for r in arrivals(11)) == seat(11)["paa_vei_foer_ordre"] == 16
assert sum(r[1] for r in arrivals(12)) == seat(12)["paa_vei_foer_ordre"] == 36
assert arrivals(11)[0][1] == seat(11)["neste_levering"] == seat(12)["levering"]
assert seat(13, "Distributør")["innkommende_ordre"] == 24
assert seat(15)["levering"] == seat(13, "Distributør")["sendt"] == 17


def kr(v):
    whole, dec = f"{v:.2f}".split(".")
    if len(whole) > 3:
        whole = whole[:-3] + " " + whole[-3:]
    return f"{whole},{dec}"


# ---- Palett ----
HOUSING = "#2B2926"   # tavlekabinett, matt lakk
HOUSE2 = "#23211E"    # innfelt spor
FLAP_T = "#1F1D1A"
FLAP_B = "#181614"
SEAM = "#050505"
BONE = "#F1EDE2"      # off-white siffer
BONE2 = "#CFCABB"     # sekundær malt tekst på kabinett
DIM = "#A8A395"       # ferdig-rader, fortsatt over 4,5:1 på klaff
YEL = "#F4B822"       # stasjonsgul, eneste aksent
YEL_T = "#F7C037"
YEL_B = "#EFB21C"
WALL = "#E8E3D6"      # hallvegg
WALL2 = "#DAD4C5"
INK = "#1C1B18"
INK2 = "#514C3E"

TONES = {
    "dark": (FLAP_T, FLAP_B, BONE, SEAM),
    "amber": (FLAP_T, FLAP_B, YEL, SEAM),
    "dim": (FLAP_T, FLAP_B, DIM, SEAM),
    "yellow": (YEL_T, YEL_B, INK, "#A47C0C"),
    "paper": ("#F4F0E5", "#E9E4D6", INK, "#B3AD9D"),
    "ghost": ("#35332F", "#302E2A", "#A8A395", "#1A1917"),
}

FONTS = ("https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;800;900"
         "&amp;family=Barlow+Semi+Condensed:wght@500;600;700&amp;family=Barlow:wght@400;500;600&amp;display=swap")
STYLE = f"""@import url('{FONTS}');
.c02-f{{font-family:'Big Shoulders Display','Oswald','Arial Narrow',sans-serif;font-weight:800}}
.c02-c{{font-family:'Barlow Semi Condensed','Barlow','Arial Narrow',sans-serif;font-weight:600;font-variant-numeric:tabular-nums}}
.c02-b{{font-family:'Barlow','Segoe UI',Arial,sans-serif;font-weight:500}}
"""


def esc(s):
    return escape(str(s))


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def svg(name, page, w, h, title, desc, body, defs=""):
    shadow = (f'<filter id="c02-{page}-sh" x="-5%" y="-5%" width="110%" height="115%">'
              '<feDropShadow dx="0" dy="7" stdDeviation="11" flood-color="#3A3320" flood-opacity=".30"/></filter>')
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="\'Barlow\',\'Segoe UI\',Arial,sans-serif">'
           f"<title>{esc(title)}</title><desc>{esc(desc)}</desc><style>{STYLE}</style>"
           f"<defs>{shadow}{defs}</defs>{body}</svg>")
    (HERE / name).write_text(out, encoding="utf-8")


def rect(x, y, w, h, fill, rx=0, extra=""):
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}"' + (f' rx="{f(rx)}"' if rx else "") + f" {extra}/>"


def line(x1, y1, x2, y2, stroke, sw=1, extra=""):
    return f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>'


def path(d, fill="none", stroke=None, sw=None, extra=""):
    s = f'<path d="{d}" fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}"'
    if sw:
        s += f' stroke-width="{f(sw)}"'
    return s + f" {extra}/>"


def T(x, y, s, size=14, cls="b", fill=INK, anchor="start", weight=None, extra=""):
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    wt = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{f(x)}" y="{f(y)}" class="c02-{cls}" font-size="{f(size)}" fill="{fill}"{a}{wt} {extra}>{esc(s)}</text>'


def para(x, y, s, chars, size=14, lh=None, cls="b", fill=INK, anchor="start", weight=None):
    lh = lh or size * 1.34
    return "".join(T(x, y + i * lh, ln, size, cls, fill, anchor, weight)
                   for i, ln in enumerate(textwrap.wrap(s, chars)))


def fw(n, cw, gap=1):
    return n * cw + (n - 1) * gap


def half_paths(x, y, w, h, r):
    cy = y + h / 2
    top = f"M{f(x)} {f(cy)}V{f(y + r)}Q{f(x)} {f(y)} {f(x + r)} {f(y)}H{f(x + w - r)}Q{f(x + w)} {f(y)} {f(x + w)} {f(y + r)}V{f(cy)}Z"
    bot = f"M{f(x)} {f(cy)}V{f(y + h - r)}Q{f(x)} {f(y + h)} {f(x + r)} {f(y + h)}H{f(x + w - r)}Q{f(x + w)} {f(y + h)} {f(x + w)} {f(y + h - r)}V{f(cy)}Z"
    return top, bot


def flaps(x, y, s, cw, ch, fs=None, gap=1, tone="dark", cells=None, align="left", weight=None, cls="f"):
    """En rad klaffer. Tekst står i egne celler, sømmen tegnes over bokstavene."""
    s = str(s)
    n = cells or len(s)
    if len(s) < n:
        s = s.rjust(n) if align == "right" else (s.center(n) if align == "center" else s.ljust(n))
    fs = fs or ch * 0.84
    if any(c in s for c in "MW"):  # brede bokstaver må ikke sprenge cellen
        fs = min(fs, max(cw / .6, fs * .9))
    top, bot, fg, seam = TONES[tone]
    light = tone in ("yellow", "paper")  # mørk søm over mørk tekst gjør bokstavene grøtete
    r = min(2.2, ch * 0.08)
    d_top, d_bot, d_seam, notch = [], [], [], []
    xs = []
    for i in range(n):
        cx = x + i * (cw + gap)
        a, b = half_paths(cx, y, cw, ch, r)
        d_top.append(a)
        d_bot.append(b)
        d_seam.append(f"M{f(cx)} {f(y + ch / 2)}h{f(cw)}")
        if ch >= 30:
            notch.append(f"M{f(cx)} {f(y + ch / 2 - ch * .07)}h1.6v{f(ch * .14)}h-1.6zM{f(cx + cw - 1.6)} {f(y + ch / 2 - ch * .07)}h1.6v{f(ch * .14)}h-1.6z")
        xs.append(cx + cw / 2)
    out = [path("".join(d_top), top), path("".join(d_bot), bot)]
    if light:
        out.append(path("".join(d_seam), stroke=seam, sw=max(.9, ch * .022)))
    base = y + ch / 2 + fs * 0.36
    tsp, i = [], 0
    for word in s.replace("\n", " ").split(" "):
        if word:
            tsp.append(f'<tspan x="{" ".join(f(v) for v in xs[i:i + len(word)])}">{esc(word)}</tspan>')
        i += len(word) + 1
    if tsp:
        wt = f' font-weight="{weight or (700 if ch < 30 else 800)}"'
        out.append(f'<text y="{f(base)}" class="c02-{cls}" font-size="{f(fs)}" fill="{fg}" text-anchor="middle"{wt}>' + " ".join(tsp) + "</text>")
    if not light:
        out.append(path("".join(d_seam), stroke=seam, sw=max(.8, ch * .022), extra='opacity=".62"' if ch < 30 else ""))
    if notch:
        out.append(path("".join(notch), "#000", extra='opacity=".55"'))
    return "".join(out)


def flip(x, y, cw, ch, old, new, fs=None, tone="dark"):
    """Klaff midt i et vipp: øverst ny verdi, nederst gammel, bladet på vei ned."""
    fs = fs or ch * 0.84
    top, bot, fg, seam = TONES[tone]
    cy = y + ch / 2
    a, b = half_paths(x, y, cw, ch, min(2.2, ch * .08))
    out = [path(a, top), path(b, bot)]
    base = ch / 2 + fs * 0.36
    out.append(f'<svg x="{f(x)}" y="{f(y)}" width="{f(cw)}" height="{f(ch / 2)}" viewBox="0 0 {f(cw)} {f(ch / 2)}">'
               + T(cw / 2, base, new, fs, "f", fg, "middle") + "</svg>")
    out.append(f'<svg x="{f(x)}" y="{f(cy)}" width="{f(cw)}" height="{f(ch / 2)}" viewBox="0 {f(ch / 2)} {f(cw)} {f(ch / 2)}">'
               + T(cw / 2, base, old, fs, "f", fg, "middle") + "</svg>")
    k = ch * .2
    d = cw * .06
    out.append(path(f"M{f(x - d)} {f(cy - k)}H{f(x + cw + d)}L{f(x + cw)} {f(cy)}H{f(x)}Z", "#45423C"))
    out.append(line(x, cy, x + cw, cy, seam, max(.9, ch * .03)))
    return "".join(out)


def num(x, y, v, cw, ch, fs=None, tone="dark", cells=2, flip_from=None):
    """Tall høyrejustert i celler. flip_from gir klaffer midt i vipp der sifrene er ulike."""
    s = "" if v is None else str(v)
    s = s.rjust(cells)
    if flip_from is None:
        return flaps(x, y, s, cw, ch, fs, tone=tone)
    o = str(flip_from).rjust(cells)
    out = []
    for i, (old, new) in enumerate(zip(o, s)):
        cx = x + i * (cw + 1)
        out.append(flaps(cx, y, new, cw, ch, fs, tone=tone) if old == new else flip(cx, y, cw, ch, old, new, fs, tone))
    return "".join(out)


def tally(x, y, n, kind="ship", cw=5.7, ch=18, gap=1):
    """Én liten klaff per kasse. Form skiller typene: hel, hul, skråstrek."""
    out = []
    solid, hollow, slash = [], [], []
    for i in range(n):
        cx = x + i * (cw + gap)
        if kind == "ship":
            solid.append(f"M{f(cx)} {f(y)}h{f(cw)}v{f(ch)}h{f(-cw)}z")
        else:
            hollow.append(f"M{f(cx + .5)} {f(y + .5)}h{f(cw - 1)}v{f(ch - 1)}h{f(-cw + 1)}z")
            if kind == "owed":
                slash.append(f"M{f(cx + .5)} {f(y + ch - .5)}L{f(cx + cw - .5)} {f(y + .5)}")
    col = YEL if kind == "new" else BONE
    if solid:
        out.append(path("".join(solid), BONE))
        out.append(path("".join(f"M{f(x + i * (cw + gap))} {f(y + ch / 2)}h{f(cw)}" for i in range(n)), stroke=HOUSING, sw=1))
    if hollow:
        out.append(path("".join(hollow), stroke=col, sw=1.1))
    if slash:
        out.append(path("".join(slash), stroke=col, sw=1.1))
    return "".join(out)


def jack(x, cy, w, kind, col=BONE, sw=2.2):
    """Koblingslinja: hel (spiller), tverrstrek (pauset), hull (KI), dobbel (din), åpen ring (nær overtakelse),
    fylt plugg (ferdig). Radformen er den samme uansett farge."""
    x2 = x + w
    if kind == "hel":
        return line(x, cy, x2, cy, col, sw)
    if kind == "pause":
        m = x + w / 2
        return line(x, cy, x2, cy, col, sw) + line(m, cy - 7, m, cy + 7, col, sw + 1)
    if kind == "ki":
        g = w * .3
        m = x + w / 2
        return (line(x, cy, m - g / 2, cy, col, sw) + line(m + g / 2, cy, x2, cy, col, sw)
                + line(m - g / 2, cy - 4, m - g / 2, cy + 4, col, sw * .8) + line(m + g / 2, cy - 4, m + g / 2, cy + 4, col, sw * .8))
    if kind == "din":
        return line(x, cy - 2.6, x2, cy - 2.6, col, sw * .9) + line(x, cy + 2.6, x2, cy + 2.6, col, sw * .9)
    if kind == "naer":
        return line(x, cy, x2 - 11, cy, col, sw) + f'<circle cx="{f(x2 - 6)}" cy="{f(cy)}" r="5.2" fill="none" stroke="{col}" stroke-width="{f(sw)}"/>'
    if kind == "ferdig":
        return line(x, cy, x2 - 6, cy, col, sw) + rect(x2 - 6, cy - 4, 6, 8, col)
    if isinstance(kind, tuple):  # 4 seter, hull der KI sitter
        seg = w / 4
        out = []
        i = 0
        while i < 4:
            j = i
            while j < 4 and kind[j] == kind[i]:
                j += 1
            if kind[i]:
                out.append(line(x + i * seg, cy, x + j * seg, cy, col, sw))
            else:
                out.append(line(x + i * seg + .6, cy - 4, x + i * seg + .6, cy + 4, col, sw * .8)
                           + line(x + j * seg - .6, cy - 4, x + j * seg - .6, cy + 4, col, sw * .8))
            i = j
        return "".join(out)
    raise ValueError(kind)


def chevron(cx, cy, up=True, size=9, col=BONE, sw=2.6):
    dy = -size * .5 if up else size * .5
    return path(f"M{f(cx - size)} {f(cy - dy)}L{f(cx)} {f(cy + dy)}L{f(cx + size)} {f(cy - dy)}", stroke=col, sw=sw,
                extra='stroke-linecap="square" stroke-linejoin="miter"')


def lock_icon(x, y, s=14, col=BONE):
    return (rect(x, y + s * .42, s, s * .58, col, 1.2)
            + path(f"M{f(x + s * .22)} {f(y + s * .42)}V{f(y + s * .24)}a{f(s * .28)} {f(s * .24)} 0 0 1 {f(s * .56)} 0V{f(y + s * .42)}",
                   stroke=col, sw=max(1.4, s * .13)))


def wall(w, h, step=170):
    d = "".join(f"M0 {y}H{w}" for y in range(step, h, step)) + "".join(f"M{x} 0V{h}" for x in range(step * 2, w, step * 2))
    return rect(0, 0, w, h, WALL) + path(d, stroke=WALL2, sw=1)


def rods(xs, y1, y2=0):
    return "".join(rect(x - 2, y2, 4, y1 - y2, "#6B6657") for x in xs)


_clip = {"n": 0}


def phone(page, x, y, content, scale=1.0):
    """Enkel telefonramme rundt et 390x844-lerret."""
    _clip["n"] += 1
    cid = f"c02-{page}-tel{_clip['n']}"
    return (f'<g transform="translate({f(x)} {f(y)}) scale({f(scale)})">'
            f'<clipPath id="{cid}"><rect width="390" height="844" rx="26"/></clipPath>'
            + rect(-8, -8, 406, 860, "#3E3B35", 33, f'filter="url(#c02-{page}-sh)"')
            + f'<g clip-path="url(#{cid})">' + rect(0, 0, 390, 844, HOUSING) + content + "</g></g>")


# ---- Spilltavla på telefon (390x844) ----
LBL_X, NUM_X, TAL_X = 16, 154, 204
LCW, NCW = 14, 22
TCW = 5.9


def g_header(week, flip_from=None, role="GROSSIST", who="Sara, spill 17", pause=True):
    o = flaps(16, 14, role, 13.5, 27, 23, cells=max(8, len(role)))
    o += T(16, 60, who, 14, "c", BONE2)
    if pause:
        o += flaps(205, 15, "PAUSE", 11, 25, 20, tone="ghost")
    o += T(305, 44, "UKE", 15, "c", BONE, "end")
    o += num(310, 12, week, 31, 46, 42, flip_from=flip_from)
    return o


def g_row(y, label, v, n=None, kind="ship", tone="dark", flip_from=None, ltone="dark", h=26, note=None, note_fill=BONE2):
    o = flaps(LBL_X, y, label, LCW, 26, 22, cells=9, tone=ltone)
    o += num(NUM_X, y, v, NCW, 26, 22, tone=tone, flip_from=flip_from)
    if n:
        o += tally(TAL_X, y + 4, n, kind, TCW)
    if note:
        o += T(TAL_X + (n or 0) * (TCW + 1) + (5 if n else 0), y + 18, note, 14, "c", note_fill)
    return o


def g_big(y, label, v, n=None, kind="owed", flip_from=None, note=None):
    o = flaps(LBL_X, y + 6, label, LCW, 30, 25, cells=9)
    o += num(NUM_X, y, v, NCW, 42, 38, flip_from=flip_from)
    if n:
        o += tally(TAL_X, y + 12, n, kind, TCW)
    if note:
        o += T(TAL_X, y + 26, note, 13.5, "c", BONE2)
    return o


def g_stock(week, flips=None):
    s = seat(week)
    flips = flips or {}
    o = g_big(66, "LAGER", s["lager"], note="Tomt" if s["lager"] == 0 else None, flip_from=flips.get("lager"))
    o += g_big(112, "RESTORDRE", s["restordre"], s["restordre"] if s["restordre"] <= 24 else 24, flip_from=flips.get("restordre"))
    o += g_row(160, "ORDRE INN", s["innkommende_ordre"], s["innkommende_ordre"], "ship", flip_from=flips.get("inn"))
    o += g_row(189, "LEVERING", s["levering"], s["levering"], "ship", flip_from=flips.get("lev"))
    o += g_row(218, "SENDT UT", s["sendt"], s["sendt"], "ship", flip_from=flips.get("sendt"))
    return o


def g_ontheway(week, order=None, locked=False, legend=True):
    base = seat(week)["paa_vei_foer_ordre"]
    y = 256
    o = line(16, y - 6, 374, y - 6, "#47443D", 1)
    if order is None:
        o += g_row(y, "PÅ VEI", base)
    elif locked:
        o += g_row(y, "PÅ VEI", base + order, note=f"{base} + din ordre {order}", note_fill=BONE2)
    else:
        o += g_row(y, "PÅ VEI", base, note=f"+ {order} = {base + order} med ordren din", note_fill=YEL)
    for i, (n, q, k) in enumerate(arrivals(week, order)):
        lab = f"OM {n} UKE" if n == 1 else f"OM {n} UKER"
        ry = y + 29 * (i + 1)
        if k == "new" and not locked:
            o += g_row(ry, lab, q, q, "new", tone="amber")
        elif k == "new":
            o += g_row(ry, lab, q, q, "ord")
        else:
            o += g_row(ry, lab, q, q, k)
    if legend:
        o += T(16, 420, "Hul rute: bestilt, ikke sendt ennå. Kan komme senere.", 13.5, "c", BONE2)
    return o


def g_history(orders, cost, y=430, last_new=False):
    o = T(16, y + 11, "Dine ordrer", 14, "c", BONE)
    x = 16
    for i, q in enumerate(orders):
        cx = x + i * 21
        tone = "amber" if last_new and i == len(orders) - 1 else "dark"
        o += num(cx, y + 16, q, 9.5, 26, 21, tone=tone) if q > 9 else flaps(cx, y + 16, str(q), 20, 26, 22, tone=tone)
        if i >= 4:
            o += T(cx + 10, y + 57, str(i + 1), 13, "c", BONE2, "middle")
    o += line(x, y + 46, x + 83, y + 46, BONE2, 1.2)
    o += T(x + 41, y + 57, "1–4 veiledet", 13, "c", BONE2, "middle")
    o += T(374, y + 11, "Totalkostnad", 14, "c", BONE, "end")
    o += flaps(374 - fw(8, 12), y + 16, f"{kr(cost)} KR", 12, 26, 21, cells=8, align="right")
    return o


def roller(x, y, d, w=72, tone="amber", locked=False, active=True, flip_from=None):
    """Sifferrull: klaffen midt på, naboene synlig over og under, piler som egne klaffer."""
    o = ""
    if not locked:
        o += flaps(x, y, " ", w, 36, tone="dark" if active else "ghost") + chevron(x + w / 2, y + 18, True)
    dy = y + 39
    o += rect(x, dy, w, 106, HOUSE2, 3)
    nxt, prv = (d + 1) % 10, (d - 1) % 10
    o += f'<svg x="{f(x + 4)}" y="{f(dy)}" width="{f(w - 8)}" height="13" viewBox="0 0 {f(w - 8)} 13">' + flaps(0, -40, str(nxt), w - 8, 53, 46, tone="dim") + "</svg>"
    o += f'<svg x="{f(x + 4)}" y="{f(dy + 93)}" width="{f(w - 8)}" height="13" viewBox="0 0 {f(w - 8)} 13">' + flaps(0, 0, str(prv), w - 8, 53, 46, tone="dim") + "</svg>"
    if flip_from is None:
        o += flaps(x, dy + 13, str(d), w, 80, 76, tone=tone)
    else:
        o += flip(x, dy + 13, w, 80, str(flip_from), str(d), 76, tone)
    if not locked:
        o += flaps(x, dy + 109, " ", w, 36, tone="dark" if active else "ghost") + chevron(x + w / 2, dy + 127, False)
    return o


def g_order(order, week=11, y=494):
    """Beslutningen: to ruller, fakta ved siden av, gul Bekreft."""
    a, b = (0, 0) if order is None else (order // 10, order % 10)
    tone = "dim" if order is None else "amber"
    o = roller(16, y, a, tone=tone) + roller(92, y, b, tone=tone)
    bx = 176
    o += T(bx, y + 14, f"Din ordre, uke {week}", 16, "c", BONE, weight=700)
    if order is None:
        o += para(bx, y + 40, "Bla med pilene, eller trykk på sifferet for å taste.", 28, 14, 18, "b", BONE2)
        o += flaps(bx, y + 118, "VELG ORDRE", 18.8, 52, 36, tone="ghost")
    else:
        base = seat(week)["paa_vei_foer_ordre"]
        o += T(bx, y + 42, "Restordre", 15, "b", BONE2) + T(374, y + 42, str(seat(week)["restordre"]), 18, "c", BONE, "end", 700)
        o += T(bx, y + 66, "På vei nå", 15, "b", BONE2) + T(374, y + 66, str(base), 18, "c", BONE, "end", 700)
        o += T(bx, y + 90, "På vei med ordren", 15, "b", YEL) + T(374, y + 90, str(base + order), 18, "c", YEL, "end", 700)
        o += flaps(bx, y + 106, f"BEKREFT {order}", 18.8, 52, 35, tone="yellow")
        o += T(bx, y + 176, "Kan ikke endres etterpå.", 14, "b", BONE2)
    return o


def who_row(x, ry, kind, who, status, tone, jw=24, cw=9.7, ch=24, fs=18.5):
    """Én rad i avgangslista: koblingslinje, Rolle og navn, status."""
    o = jack(x, ry + ch / 2, jw, kind, YEL if tone == "yellow" and kind != "din" else BONE)
    lx = x + jw + 4
    o += flaps(lx, ry, who, cw, ch, fs, cells=18)
    sx = lx + fw(18, cw) + 8
    o += flaps(sx, ry, " ", cw, ch, fs, cells=12)
    o += flaps(sx, ry, status, cw, ch, fs, tone=tone)
    return o


def g_who(rows, y=692, head="Tavla venter på"):
    o = T(16, y, head, 14, "c", BONE)
    for i, (kind, who, status, tone) in enumerate(rows):
        o += who_row(16, y + 7 + i * 27, kind, who, status, tone)
    return o


def demo(y=830, x=195, fill=BONE2, anchor="middle"):
    return T(x, y, "Demodata", 13, "c", fill, anchor)


WHO_B = [("hel", "DETALJIST IDA", "KLAR", "dark"), ("din", "GROSSIST SARA", "DIN TUR", "yellow"),
         ("hel", "DISTRIBUTØR MIKKEL", "KLAR", "dark"), ("hel", "FABRIKK JONAS", "VENTER 3 MIN", "dark")]
WHO_C = [("hel", "DETALJIST IDA", "KLAR", "dark"), ("din", "GROSSIST SARA", "KLAR", "dark"),
         ("hel", "DISTRIBUTØR MIKKEL", "KLAR", "dark"), ("hel", "FABRIKK JONAS", "VENTER 3 MIN", "dark")]
WHO_A = [("hel", "DETALJIST IDA", "BESTILLER", "dark"), ("din", "GROSSIST SARA", "DIN TUR", "yellow"),
         ("hel", "DISTRIBUTØR MIKKEL", "BESTILLER", "dark"), ("hel", "FABRIKK JONAS", "BESTILLER", "dark")]


def phone_decide(order=24):
    s = seat(11)
    o = g_header(11) + g_stock(11) + g_ontheway(11, order)
    o += g_history(history(), s["kost_sum"])
    o += g_order(order)
    o += g_who(WHO_B)
    o += demo()
    return o


def phone_open():
    """A: uka åpner, levering og ordre klaffer inn."""
    s = seat(11)
    o = g_header(11, flip_from=10)
    o += g_stock(11, {"restordre": seat(10)["restordre"], "lev": seat(10)["levering"], "inn": seat(10)["innkommende_ordre"]})
    o += g_ontheway(11, None)
    o += g_history(history(), s["kost_sum"])
    o += g_order(None)
    o += g_who(WHO_A)
    o += demo()
    return o


def phone_locked():
    """C: rullene låst, Sara blir stående på tavla."""
    s = seat(11)
    o = g_header(11) + g_stock(11) + g_ontheway(11, 24, locked=True)
    o += g_history(history(upto=10) + [24], s["kost_sum"], last_new=False)
    y = 494
    o += roller(16, y, 2, tone="dark", locked=True) + roller(92, y, 4, tone="dark", locked=True)
    # Låsestang tvers over begge rullene
    o += rect(10, y + 84, 158, 8, "#8B867A", 2) + "".join(f'<circle cx="{cx}" cy="{y + 88}" r="2.2" fill="{HOUSE2}"/>' for cx in (16, 162))
    o += lock_icon(16, y + 8, 16) + T(38, y + 21, "Låst", 16, "c", BONE, weight=700)
    bx = 176
    o += T(bx, y + 22, "Ordren er sendt", 18, "c", BONE, weight=700)
    o += para(bx, y + 48, "Uka går videre når Fabrikk har bestilt. Du kan lukke appen, tavla holder plassen din.", 27, 14.5, 19, "b", BONE2)
    o += g_who(WHO_C, head="Tavla venter på Jonas")
    o += demo()
    return o


def _vis(intervals, dur):
    """Diskret opasitetsanimasjon av tidsintervaller (mod dur). Returnerer (base, animate-tag)."""
    pts = set([0.0, dur])
    norm = []
    for a, b in intervals:
        a, b = a % dur, b % dur
        if a <= b:
            norm.append((a, b))
        else:
            norm.append((a, dur))
            norm.append((0.0, b))
    for a, b in norm:
        pts.add(a)
        pts.add(b)
    pts = sorted(pts)
    on = lambda t: any(a <= t < b for a, b in norm)
    vals = [("1" if on(t) else "0") for t in pts[:-1]]
    keys = [f"{t / dur:.4f}" for t in pts[:-1]]
    tag = (f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" calcMode="discrete" '
           f'keyTimes="{";".join(keys)};1" values="{";".join(vals)};{vals[-1]}"/>')
    return vals[0], tag


def phone_cascade():
    """D: kaskaden. Bølgen går ovenfra og ned: over bølgen står Uke 12, under står Uke 11."""
    old = seat(11)
    new = seat(12)
    dur, hold = 4.0, 2.6
    rows = []  # (id, tegn gammel, tegn ny, flip)
    def row_big(y, lab, a, b):
        ta = g_big(y, lab, a, a if a and lab == "RESTORDRE" else None, note="Tomt" if lab == "LAGER" else None)
        tb = g_big(y, lab, b, b if b and lab == "RESTORDRE" else None, note="Tomt" if lab == "LAGER" else None)
        tf = g_big(y, lab, b, flip_from=a) if a != b else tb
        return (ta, tb, tf)
    def row_sm(y, lab, a, b, ka="ship", kb="ship", tone="dark"):
        ta = g_row(y, lab, a, a or None, ka) if a is not None else g_row(y, "", None)
        tb = g_row(y, lab, b, b or None, kb) if b is not None else g_row(y, "", None)
        tf = g_row(y, lab, b if b is not None else " ", flip_from=a if a is not None else " ") if a != b else tb
        return (ta, tb, tf)
    a11 = arrivals(11, 24)
    a12 = arrivals(12)
    rows.append(row_big(66, "LAGER", old["lager"], new["lager"]))
    rows.append(row_big(112, "RESTORDRE", old["restordre"], new["restordre"]))
    rows.append(row_sm(160, "ORDRE INN", old["innkommende_ordre"], new["innkommende_ordre"]))
    rows.append(row_sm(189, "LEVERING", old["levering"], new["levering"]))
    rows.append(row_sm(218, "SENDT UT", old["sendt"], new["sendt"]))
    rows.append((g_row(256, "PÅ VEI", 40), g_row(256, "PÅ VEI", 36), g_row(256, "PÅ VEI", 36, flip_from=40)))
    labs = ["OM 1 UKE", "OM 2 UKER", "OM 3 UKER"]
    for i in range(3):
        ka = "ord" if a11[i][2] != "ship" else "ship"
        kb = "ord" if a12[i][2] != "ship" else "ship"
        rows.append(row_sm(285 + i * 29, labs[i], a11[i][1], a12[i][1], ka, kb))
    rows.append((g_row(372, "OM 4 UKER", 24, 24, "ord"), g_row(372, "", None), g_row(372, "OM 4 UKER", " ", flip_from=24)))

    o = line(16, 250, 374, 250, "#47443D", 1)
    # Uke-klaffen først
    mid = 5  # bølgen står ved PÅ VEI i stillbildet
    def layered(i, ta, tb, tf):
        w = (i - mid) * .13
        b_new, a_new = _vis([(w, w + hold)], dur)
        b_fl, a_fl = _vis([(w - .08, w + .08)], dur)
        return (ta + f'<g opacity="{b_new}">{a_new}{tb}</g>' + f'<g opacity="{b_fl}">{a_fl}{tf}</g>')
    head_old = g_header(11)
    head_new = g_header(12)
    head_flip = g_header(12, flip_from=11)
    o += layered(-1, head_old, head_new, head_flip)
    for i, (ta, tb, tf) in enumerate(rows):
        o += layered(i, ta, tb, tf)
    o += T(16, 420, "Bestillingene rykker én rad opp.", 13.5, "c", BONE2)
    # Nederst: kostnad oppdateres sist, rullene nullstilles, hopp over
    o += g_history(history(upto=10) + [24], new["kost_sum"])
    y = 494
    o += roller(16, y, 0, tone="dim", flip_from=2) + roller(92, y, 0, tone="dim", flip_from=4)
    bx = 176
    o += T(bx, y + 22, "Siste ordre er inne", 18, "c", BONE, weight=700)
    o += para(bx, y + 48, "Tavla klaffer til neste Uke. Maks 2 sekunder. Du kan bruke tavla med en gang.", 27, 14.5, 19, "b", BONE2)
    o += flaps(bx, y + 122, "HOPP OVER", 21, 44, 34, tone="paper")
    o += g_who([("hel", "DETALJIST IDA", "BESTILLER", "dark"), ("din", "GROSSIST SARA", "DIN TUR", "yellow"),
                ("hel", "DISTRIBUTØR MIKKEL", "BESTILLER", "dark"), ("hel", "FABRIKK JONAS", "BESTILLER", "dark")])
    o += demo()
    return o


def phone_takeover():
    """E: Jonas er borte. Samme rad endrer form: ring, tverrstrek, hull."""
    o = g_header(11, pause=False)
    y = 72
    o += T(16, y + 12, "Fabrikk-raden, slik den endret seg", 15, "c", BONE, weight=700)
    steps = [("naer", "FABRIKK JONAS", "VENTER 23 T", "yellow", "Ida og Mikkel har bestilt. KI overtar ved 24 t."),
             ("pause", "PAUSE AV IDA", "TIL KL 19:00", "dark", "Ingen overtakelse så lenge pausen varer. Gruppa avtaler tid."),
             ("ki", "FABRIKK KI-SPILLER", "BESTILLER", "dark", "Jonas kom ikke kl. 19:00. Mikkel satte inn KI-spiller.")]
    ry = y + 26
    for kind, who, st, tone, note in steps:
        o += who_row(16, ry, kind, who, st, tone)
        o += para(44, ry + 42, note, 50, 13.5, 17, "b", BONE2)
        ry += 78
    y = 340
    o += line(16, y - 8, 374, y - 8, "#47443D", 1)
    o += T(16, y + 10, "Tavla nå", 15, "c", BONE, weight=700)
    now = [("hel", "DETALJIST IDA", "KLAR", "dark"), ("din", "GROSSIST SARA", "KLAR", "dark"),
           ("hel", "DISTRIBUTØR MIKKEL", "KLAR", "dark"), ("ki", "FABRIKK KI-SPILLER", "KLAR", "dark")]
    for i, (kind, who, st, tone) in enumerate(now):
        o += who_row(16, y + 20 + i * 27, kind, who, st, tone)
    o += T(16, y + 146, "Hull i linja betyr KI-spiller. Det står også i raden.", 13.5, "c", BONE2)
    # Jonas sin telefon
    y = 512
    o += rect(0, y, 390, 332, HOUSE2)
    o += T(16, y + 26, "På Jonas sin telefon", 15, "c", BONE, weight=700)
    o += flaps(16, y + 40, "KI-SPILLER HAR SETET", 17, 36, 30)
    o += jack(16, y + 96, 60, "ki")
    o += T(86, y + 101, "FABRIKK, FRA UKE 11", 15, "c", BONE)
    o += para(16, y + 130, "Den bestiller for deg til du tar setet tilbake. Du får det igjen når neste Uke åpner. Ukene den spilte, er merket i loggen.", 48, 14.5, 20, "b", BONE)
    o += flaps(16, y + 200, "TA TILBAKE SETET", 21.4, 56, 44, tone="yellow")
    o += T(195, y + 298, "Demodata", 13, "c", BONE2, "middle")
    return o


def phone_end():
    """F: spillet slutter. Kjeden først, så per Rolle, aldri navn."""
    o = flaps(16, 22, "TAVLA ER FERDIG", 17, 34, 28, cells=15)
    o += para(16, 84, "Spillet er slutt. Dette kostet kjeden dere var en del av.", 42, 16, 22, "b", BONE)
    o += T(16, 160, "Kjeden totalt", 16, "c", BONE, weight=700)
    o += flaps(16, 170, f"{kr(FX['chain_total_cost'])}", 41, 72, 66, cells=8, align="right", gap=2)
    o += T(374, 268, "kr, hele kjeden", 15, "c", BONE2, "end")
    y = 300
    o += line(16, y - 10, 374, y - 10, "#47443D", 1)
    o += T(16, y + 8, "Per Rolle", 16, "c", BONE, weight=700)
    mx = max(FX["total_cost_per_role"].values())
    for i, r in enumerate(ROLES):
        v = FX["total_cost_per_role"][r]
        ry = y + 20 + i * 42
        o += flaps(16, ry, r.upper(), 12.2, 30, 25, cells=11)
        o += flaps(374 - fw(6, 14.5), ry, kr(v), 14.5, 30, 25, cells=6, align="right")
        o += rect(16, ry + 33, 358 * v / mx, 3, BONE)
    y = 520
    o += line(16, y - 6, 374, y - 6, "#47443D", 1)
    o += para(16, y + 28, "Kostnad per Rolle, ikke per navn. Hvorfor det ble slik, er det Debriefen handler om.", 46, 16.5, 23, "b", BONE)
    o += para(16, y + 96, "Først skriver du din egen Forklaring. Så ser dere resten sammen.", 46, 15.5, 21, "b", BONE2)
    o += flaps(16, y + 176, "GÅ TIL DEBRIEF", 24.6, 72, 50, tone="yellow")
    o += T(195, 830, "Demodata", 13, "c", BONE2, "middle")
    return o


# ---- 05 hovedskjerm ----
def page_spill():
    w, h = 1600, 1000
    b = wall(w, h)
    b += T(60, 60, "Hele spillet er én tavle", 46, "f", INK)
    b += phone("spill", 68, 104, phone_decide())
    # Laptop
    lx, ly, lw, lh = 540, 104, 1000, 670
    b += rect(lx - 14, ly - 14, lw + 28, lh + 28, "#3E3B35", 14, 'filter="url(#c02-spill-sh)"')
    b += rect(lx, ly, lw, lh, HOUSING)
    b += path(f"M{lx - 60} {ly + lh + 14}H{lx + lw + 60}L{lx + lw + 30} {ly + lh + 34}H{lx - 30}Z", "#6B6657")
    s = seat(11)
    x0 = lx + 28
    o = flaps(x0, ly + 22, "GROSSIST", 19, 38, 32)
    o += T(x0 + 170, ly + 48, "Sara, spill 17", 19, "c", BONE2)
    o += flaps(lx + 560, ly + 24, "PAUSE", 15, 34, 28, tone="ghost")
    o += T(lx + 880, ly + 62, "UKE", 22, "c", BONE, "end")
    o += num(lx + 888, ly + 16, 11, 42, 62, 56)
    # Venstre kolonne: selve tavla, samme kolonner som telefonen, men større
    lcw, ncw = 19, 30
    nx = x0 + fw(9, lcw) + 8
    tx = nx + fw(2, ncw) + 10
    tcw, tch = 8.9, 26
    def row(y, label, v, n=None, kind="ship", tone="dark", note=None, big=False, nfill=BONE2):
        c = 56 if big else 38
        out = flaps(x0, y + (c - 38) / 2, label, lcw, 38, 31, cells=9)
        out += num(nx, y, v, ncw, c, 50 if big else 32, tone=tone)
        if n:
            out += tally(tx, y + (c - tch) / 2, n, kind, tcw, tch)
        if note:
            out += T(tx + (n or 0) * (tcw + 1) + (8 if n else 0), y + c / 2 + 6, note, 17, "c", nfill)
        return out
    y = ly + 92
    o += row(y, "LAGER", s["lager"], big=True, note="Tomt")
    o += row(y + 62, "RESTORDRE", s["restordre"], s["restordre"], "owed", big=True)
    y += 130
    o += row(y, "ORDRE INN", s["innkommende_ordre"], s["innkommende_ordre"])
    o += row(y + 46, "LEVERING", s["levering"], s["levering"])
    o += row(y + 92, "SENDT UT", s["sendt"], s["sendt"])
    y += 146
    o += line(x0, y - 7, lx + 590, y - 7, "#47443D", 1)
    o += row(y, "PÅ VEI", s["paa_vei_foer_ordre"], note="+ 24 = 40 med ordren din", nfill=YEL)
    for i, (n, q, k) in enumerate(arrivals(11, 24)):
        lab = f"OM {n} UKE" if n == 1 else f"OM {n} UKER"
        o += row(y + 46 * (i + 1), lab, q, q, k, tone="amber" if k == "new" else "dark")
    o += T(x0, ly + lh - 18, "Hel rute: sendt. Hul rute: bestilt, ikke sendt ennå, kan komme senere. Skråstrek: skyldig. Én rute er én kasse.", 15, "c", BONE2)
    # Høyre kolonne: rullene og hvem tavla venter på
    rx = lx + 630
    o += T(rx, ly + 106, "Din ordre, uke 11", 20, "c", BONE, weight=700)
    o += roller(rx, ly + 116, 2, w=76) + roller(rx + 84, ly + 116, 4, w=76)
    bx = rx + 172
    o += T(bx, ly + 148, "Restordre", 16, "b", BONE2) + T(lx + lw - 28, ly + 148, "13", 20, "c", BONE, "end", 700)
    o += T(bx, ly + 174, "På vei nå", 16, "b", BONE2) + T(lx + lw - 28, ly + 174, "16", 20, "c", BONE, "end", 700)
    o += T(bx, ly + 200, "Med ordren", 16, "b", YEL) + T(lx + lw - 28, ly + 200, "40", 20, "c", YEL, "end", 700)
    o += flaps(bx, ly + 216, "BEKREFT 24", 15.9, 52, 31, tone="yellow")
    o += T(bx, ly + 290, "Kan ikke endres etterpå.", 14.5, "b", BONE2)
    y = ly + 330
    o += line(rx, y - 12, lx + lw - 28, y - 12, "#47443D", 1)
    o += T(rx, y + 6, "Tavla venter på", 16, "c", BONE)
    for i, (kind, who, st, tone) in enumerate(WHO_B):
        o += who_row(rx, y + 16 + i * 30, kind, who, st, tone, jw=20, cw=8.9, ch=26, fs=19)
    y = ly + 490
    o += line(rx, y - 8, lx + lw - 28, y - 8, "#47443D", 1)
    o += T(rx, y + 12, "Dine ordrer", 16, "c", BONE)
    for i, q in enumerate(history()):
        cx = rx + i * 25
        o += flaps(cx, y + 20, str(q), 23.5, 34, 28)
        if i >= 4:
            o += T(cx + 12, y + 72, str(i + 1), 14, "c", BONE2, "middle")
    o += line(rx, y + 58, rx + 98, y + 58, BONE2, 1.2)
    o += T(rx + 49, y + 72, "1–4 veiledet", 14, "c", BONE2, "middle")
    o += T(rx, y + 108, "Totalkostnad", 16, "c", BONE)
    o += flaps(rx + 110, y + 90, f"{kr(s['kost_sum'])} KR", 15, 32, 26, cells=8, align="right")
    o += T(lx + lw - 28, y + 170, "Demodata", 14, "c", BONE2, "end")
    b += o
    # Merknader på veggen
    nx0 = lx - 14
    notes = [("Rader, ikke skjema", "Lager, restordre, inn, ut og på vei står i de samme kolonnene. Øynene sammenligner lengder, ikke tall."),
             ("13 skyldig, 40 på vei", "Raden «om 4 uker» klaffer inn mens du blar, før du bekrefter. Rutene viser det tallet ellers skjuler."),
             ("360 px", "Alle rader og rullene får plass uten sideveis scrolling. Rutene krymper, kolonnene står.")]
    for i, (hd, tx0) in enumerate(notes):
        x = nx0 + i * 345
        b += T(x, 860, hd, 26, "f", INK)
        b += para(x, 888, tx0, 44, 15.5, 21, "b", INK2)
    svg("05-spill.svg", "spill", w, h, "Avgang: spillskjermen i Uke 11",
        "Saras tavle i Uke 11 på telefon og laptop. Lager 0, restordre 13, på vei 16, 24 tastet inn. Alle verdier står som klaffer i én tavle. Demodata.", b)


# ---- 06 spilldynamikk ----
def page_dynamikk():
    w, h = 2100, 1200
    b = wall(w, h)
    b += T(44, 62, "Én Uke på tavla", 52, "f", INK)
    b += T(365, 60, "Fra Uke 11 til Uke 12, og det som skjer når noen blir borte.", 24, "c", INK2)
    scale = .8
    pw = 390 * scale
    gap = (w - 88 - 6 * pw) / 5
    frames = [
        ("A", "Uka åpner", "Levering 4 og ordre 8 klaffer inn. Restordre vipper fra 9 til 13. Du leser fra toppen av tavla.", phone_open()),
        ("B", "Beslutningen", "Du blar til 24. Raden «om 4 uker» kommer opp før du bekrefter, ved siden av 16 som alt er på vei.", phone_decide()),
        ("C", "Bekreftet", "Rullene låses med en stang. Du blir stående på tavla og ser Jonas sin rad: venter 3 min.", phone_locked()),
        ("D", "Uka går videre", "Bølgen går fra toppen og ned, alt rykker én rad opp. Under 2 sek, kan hoppes over, stopper aldri input.", phone_cascade()),
        ("E", "Jonas er borte", "Raden skifter form: ring, tverrstrek, hull. KI-spiller står merket, og Jonas kan ta tilbake setet.", phone_takeover()),
        ("F", "Spillet slutter", "Kjedens totalkostnad først, så per Rolle uten navn. Eneste vei videre er Debriefen.", phone_end()),
    ]
    for i, (k, title, note, content) in enumerate(frames):
        x = 44 + i * (pw + gap)
        b += phone("dyn", x, 100, content, scale)
        b += T(x, 816, k, 38, "f", INK)
        b += T(x + 28, 816, title, 34, "f", INK)
        b += para(x, 848, note, 37, 19.5, 26, "b", INK2)
    y = 985
    b += line(44, y, w - 44, y, INK, 2)
    b += T(44, y + 48, "Hva som gjør denne følelsen egen", 34, "f", INK)
    txt = ("Spillet belønner deg ikke med poeng, men med et øyeblikk: når siste ordre kommer inn, klaffer hele tavla til neste Uke, "
           "som i en stasjonshall der alt bytter samtidig. Du venter sammen med tre andre, og du ser dem som rader i en avgangsliste, ikke som avatarer. "
           "Forsinkelsen står der som en liste over ankomster du kan telle, og ordren din står nederst i den og rykker én rad opp per Uke. "
           "Du bestiller for mye med øynene åpne, for tavla viste 40 på vei, men raden du faktisk kjenner, er 13 skyldig.")
    b += para(520, y + 40, txt, 150, 21, 30, "b", INK)
    b += T(w - 44, h - 24, "Demodata", 15, "c", INK2, "end")
    svg("06-spilldynamikk.svg", "dyn", w, h, "Avgang: spilldynamikken i seks ruter",
        "Storyboard A til F: uka åpner, beslutningen om 24, bekreftet og låst, kaskaden til neste Uke, Jonas er borte og KI-spiller tar setet, spillet slutter. Demodata.", b)


# ---- Felles for lærerflatene: tavler på lys hallvegg ----
def board(page, x, y, w, h, rod=None):
    """Hengt tavle. Kabinett i matt lakk med myk skygge mot veggen."""
    o = ""
    if rod is not None:
        o += rods([x + 90, x + w - 90], y + 2, rod)
    return o + rect(x, y, w, h, HOUSING, 5, f'filter="url(#c02-{page}-sh)"')


def nav(w, active, items=("OVERSIKT", "KLASSER", "KLASSEØKT", "MELDINGER")):
    """Navigasjonen er også klaffer: valgt klaff er lys."""
    o = rect(0, 0, w, 62, HOUSING)
    o += flaps(28, 13, "AVGANG", 21, 36, 30, tone="yellow")
    x = 200
    for it in items:
        o += flaps(x, 16, it, 14.5, 30, 24, tone="paper" if it == active else "dark")
        x += fw(len(it), 14.5) + 16
    o += T(w - 28, 38, "Faglærer Bård", 17, "c", BONE, "end")
    return o


def field(x, y, label, value, cells, cw=17, ch=34, fs=27, tone="dark", caret=False, fill=BONE):
    """Skjemafelt: en tom klaffrekke som verdien klaffer inn i."""
    o = T(x, y, label, 15, "c", fill)
    o += flaps(x, y + 7, value, cw, ch, fs, cells=cells, tone=tone)
    if caret:
        cx = x + len(value) * (cw + 1)
        o += flaps(cx, y + 7, " ", cw, ch, tone="yellow")
    return o


def drum(x, y, label, prev, cur, nxt, cells, cw=14, ch=32, fs=26):
    """Rull for valg mellom alternativer: valgt rad i midten, naboene svakt over og under."""
    w = fw(cells, cw)
    o = T(x, y, label, 15, "c", BONE)
    o += T(x + 2, y + 25, prev, 15, "c", DIM)
    o += flaps(x, y + 32, " ", cw, ch, fs, cells=cells)
    o += flaps(x, y + 32, cur, cw, ch, fs, tone="paper")
    o += T(x + 2, y + 32 + ch + 19, nxt, 15, "c", DIM)
    bx = x + w + 6
    o += flaps(bx, y + 32, " ", 30, ch) + chevron(bx + 15, y + 32 + ch / 2, True, 7)
    o += flaps(bx + 33, y + 32, " ", 30, ch) + chevron(bx + 48, y + 32 + ch / 2, False, 7)
    return o


def ki_seats(game):
    """Hvilke seter som er KI er ikke i fixture, bare antallet. Plasseres fast ut fra spillnummer."""
    n = game.get("ki_seter", 0)
    seats = [True, True, True, True]
    i = game["spill"] % 4
    for _ in range(n):
        seats[i] = False
        i = (i + 2) % 4 if n == 2 else (i + 1) % 4
    return tuple(seats)


def jack_game(x, cy, w, game, col=BONE):
    """Rad i Oversikten: fire linjestykker, ett per Sete. Hull der KI sitter. Slutten sier resten."""
    near = game.get("ventet_timer", 0) >= 23
    st = game["status"]
    seats = ki_seats(game)
    end = 12 if (near or st == "ferdig") else 0
    o = jack(x, cy, w - end, seats, col)
    if near:
        o += f'<circle cx="{f(x + w - 6)}" cy="{f(cy)}" r="5.2" fill="none" stroke="{col}" stroke-width="2.2"/>'
    if st == "ferdig":
        o += rect(x + w - 10, cy - 4.5, 7, 9, col)
    if st == "pauset":
        m = x + w * .5
        o += line(m, cy - 8, m, cy + 8, col, 3.2)
    return o


def legend_forms(x, y, col=INK, txt=INK, dy=25, cols=1, colw=200):
    items = [("hel", "Hel: spiller"), ("pause", "Tverrstrek: pauset"), ("ki", "Hull: KI har overtatt"),
             ("din", "Dobbel: din"), ("naer", "Ring: nær overtakelse"), ("ferdig", "Plugg: ferdig")]
    o = ""
    for i, (k, lab) in enumerate(items):
        cx = x + (i % cols) * colw
        cy = y + (i // cols) * dy
        o += jack(cx, cy, 40, k, col) + T(cx + 50, cy + 5, lab, 15.5, "c", txt)
    return o


# ---- 01 landing ----
def page_landing():
    w, h = 1440, 1200
    b = wall(w, h)
    b += flaps(60, 22, "AVGANG", 24, 40, 33, tone="yellow")
    b += flaps(w - 60 - fw(8, 19), 24, "LOGG INN", 19, 36, 29)
    # Hengt hovedtavle
    x, y, bw, bh = 60, 88, 1320, 470
    b += rods([360, w - 360], y, 0) + board("land", x, y, bw, bh)
    b += flaps(x + 24, y + 22, "INGEN SPILL BLIR STÅENDE", 52, 92, 80)
    rows = [("hel", "FØR START", "KLASSELISTE FRA CANVAS-EKSPORT", "250 RADER"),
            ("hel", "FØR START", "INVITASJONER PÅ E-POST", "GYLDIG 14 DAGER"),
            ("ki", "TI 24. NOV", "60 KLASSESPILL ÅPNER", "KI I TOMME SETER"),
            ("ki", "TI 8. DES", "SPILLFRIST, ALLE SPILL FERDIG", "KI SPILLER UT RESTEN"),
            ("hel", "FR 11. DES", "DEBRIEF-FRIST", "BYGGER PÅ EGNE ORDRER"),
            ("hel", "FR 18. DES", "INDIVIDUELL TEST, KI-VURDERING", "VURDERING TELLER IKKE"),
            ("hel", "ETTERPÅ", "PDF-RAPPORT TIL HVER STUDENT", "ALT SAMLET")]
    ry = y + 150
    b += T(x + 90, ry - 8, "Dato", 16, "c", BONE2) + T(x + 90 + 11 * 19, ry - 8, "Avgang", 16, "c", BONE2) + T(x + 90 + 42 * 19, ry - 8, "Slik går det", 16, "c", BONE2)
    for i, (k, t, a, st) in enumerate(rows):
        yy = ry + i * 43
        b += jack(x + 26, yy + 18, 54, k)
        b += flaps(x + 90, yy, t, 18, 37, 28, cells=10)
        b += flaps(x + 90 + 11 * 19, yy, a, 18, 37, 28, cells=30)
        b += flaps(x + 90 + 42 * 19, yy, st, 18, 37, 28, cells=22)
    # Tekst og handling
    yy = y + bh + 44
    b += para(60, yy, "Avgang kjører hele forsyningskjede-øvelsen for emnet ditt, fra Invitasjon til PDF-rapport. Klasser på rundt 250 studenter, alle spillene på én skjerm, på norsk. Du slipper å være dommer.", 64, 22, 31, "b", INK)
    b += flaps(760, yy - 26, "BE OM LÆRERTILGANG", 30.5, 66, 50, tone="yellow")
    b += T(760, yy + 62, "Ingen åpen registrering. Studentene kommer inn med Invitasjon.", 17, "b", INK2)
    b += T(w - 60, yy + 62, "Demodata", 15, "c", INK2, "end")
    # Neste seksjon: mekanismen
    y2 = 722
    b += line(60, y2, w - 60, y2, INK, 2)
    b += T(60, y2 + 66, "Ett fravær stopper ikke gruppa", 54, "f", INK)
    b += para(60, y2 + 104, "Hver rad på tavla har en koblingslinje. Blir en student borte, skifter linja form, og etter Inaktivitetsgrensen tar en KI-spiller setet. Den står alltid merket, og studenten kan ta setet tilbake.", 66, 18.5, 26, "b", INK2)
    bx, by, bbw = 60, y2 + 200, 640
    b += board("land", bx, by, bbw, 238)
    seq = [("naer", "VENTER", "GROSSIST NOAH", "23 T", "dark"), ("pause", "PAUSE", "AVTALT TIL I KVELD", "19:00", "dark"),
           ("ki", "KI-SETE", "GROSSIST KI-SPILLER", "NÅ", "dark"), ("hel", "SPILLER", "NOAH TOK TILBAKE SETET", "UKE 20", "dark")]
    for i, (k, st, wh, t, tone) in enumerate(seq):
        yy = by + 18 + i * 52
        b += flaps(bx + 16, yy, "02", 22, 40, 32, tone="paper")
        b += jack(bx + 72, yy + 20, 46, k, YEL if k == "naer" else BONE)
        b += flaps(bx + 128, yy, st, 13.2, 40, 27, cells=7)
        b += flaps(bx + 236, yy, wh, 11.2, 40, 24, cells=22)
        b += flaps(bx + 236 + 22 * 12.2 + 8, yy, t, 11.2, 40, 24, cells=6)
    # Alle spillene på én skjerm
    cx = 730
    b += T(cx, y2 + 66, "60 spill, én tavle", 40, "f", INK)
    b += para(cx, y2 + 98, "Uten å klikke deg inn i noe ser du hvem hvert spill venter på, og hvor lenge.", 40, 17, 23, "b", INK2)
    gy = y2 + 160
    b += board("land", cx, gy, 340, 300)
    for i, g in enumerate(FX["class_games"]):
        c, r = i % 4, i // 4
        gx = cx + 12 + c * 81
        yy = gy + 12 + r * 18.6
        near = g.get("ventet_timer", 0) >= 23
        tone = "yellow" if near else ("dim" if g["status"] == "ferdig" else "dark")
        b += flaps(gx, yy, f"{g['spill']:02d}", 11, 16, 13.5, tone=tone)
        b += jack_game(gx + 26, yy + 8, 44, g, YEL if near else (DIM if g["status"] == "ferdig" else BONE)).replace('stroke-width="2.2"', 'stroke-width="1.6"')
    # Telefonen, beskåret av nedkanten
    px = 1104
    b += T(px, y2 + 66, "Ett tall i uka", 40, "f", INK)
    b += para(px, y2 + 98, "Studentene spiller på mobil. De bestemmer, systemet regner.", 34, 17, 23, "b", INK2)
    b += phone("land", px + 6, y2 + 160, phone_decide(), .68)
    svg("01-landing.svg", "land", w, h, "Avgang: landingsside for faglærere",
        "Hengt avgangstavle med overskriften Ingen spill blir stående og hele øvelsen som rutetabell fra Klasseliste til PDF-rapport. Hovedhandling Be om lærertilgang. Demodata.", b)


# ---- 02 lærer klasse ----
def page_klasse():
    w, h = 1440, 1000
    r = FX["roster"]
    invalid = r["ugyldige_rader"]
    sent = r["paa_lista"] - invalid
    accepted = r["registrert"]
    expired, waiting = 3, sent - accepted - 3
    still_invalid = invalid - r["manuelt_registrert"]
    assert still_invalid + expired + waiting == r["uregistrert"]
    b = wall(w, h) + nav(w, "KLASSER")
    b += T(40, 118, "Ny Klasse", 44, "f", INK)
    b += T(210, 116, "Fra Canvas-fil til sendte Invitasjoner.", 21, "c", INK2)
    # Venstre tavle: skjemaet
    x, y, bw, bh = 40, 138, 640, 816
    b += board("kl", x, y, bw, bh)
    px = x + 24
    b += field(px, y + 34, "Navn på Klassen", "CLASS-OF-1994", 24, 21.5, 42, 34)
    b += field(px, y + 112, "Emnekode", "IBE160", 10, 21.5, 42, 34)
    b += line(px, y + 178, x + bw - 24, y + 178, "#47443D")
    b += T(px, y + 206, "Klasseliste", 20, "c", BONE, weight=700)
    b += T(px, y + 228, "Eksporter fra Canvas som Excel eller CSV.", 15.5, "b", BONE2)
    b += flaps(px, y + 240, "CANVAS-EKSPORT-IBE160.XLSX", 15.2, 34, 27, cells=26)
    b += flaps(px + fw(26, 15.2) + 10, y + 240, "BYTT", 20, 34, 27, tone="ghost")
    b += T(px, y + 298, "250 rader lest. 4 ugyldige adresser.", 16, "b", BONE)
    b += drum(px, y + 330, "Hvilken kolonne er e-post?", "NAVN", "E-POST", "SIS-ID", 16, 17, 38, 31)
    # Eksempler fra valgt kolonne
    b += T(px + 400, y + 330, "Slik leser vi den", 15, "c", BONE)
    for i, em in enumerate(["ida.berg@stud.example.no", "sara.lund@stud.example.no", "noah.moe@stud.example.no"]):
        b += T(px + 400, y + 358 + i * 24, em, 13.5, "b", BONE2)
    b += line(px, y + 470, x + bw - 24, y + 470, "#47443D")
    b += T(px, y + 500, "Send Invitasjoner", 20, "c", BONE, weight=700)
    b += para(px, y + 526, "Invitasjonen er gyldig i 14 dager og går til alle gyldige adresser. Rader du retter senere, får sin egen Invitasjon.", 66, 16, 23, "b", BONE2)
    b += flaps(px, y + 590, "SEND INVITASJONER", 34, 68, 50, tone="yellow")
    b += T(px, y + 690, f"{sent} sendt ti. 3. nov 09:12.", 16, "b", BONE)
    b += T(px, y + 714, "Knappen sender bare til adresser som ikke har fått Invitasjon.", 15.5, "b", BONE2)
    b += T(px, bh + y - 22, "Demodata", 14, "c", BONE2)
    # Høyre tavle: rader
    x2, bw2 = 700, 700
    b += board("kl", x2, y, bw2, 332)
    qx = x2 + 22
    b += T(qx, y + 34, "Ugyldige rader", 20, "c", BONE, weight=700)
    b += T(x2 + bw2 - 22, y + 34, "Radnummeret følger Canvas-filen", 15, "c", BONE2, "end")
    bad = [(37, "marte.dahl@stud,example.no", "KOMMA", "RETT", "dark"),
           (88, "jon.aas.stud.example.no", "MANGLER @", "MANUELT REG.", "ok"),
           (141, "(tom celle)", "TOM", "RETT", "dark"),
           (203, "lise.hagen@stud.example", "MANGLER .NO", "MANUELT REG.", "ok")]
    for i, (n, em, why, act, st) in enumerate(bad):
        yy = y + 50 + i * 66
        b += flaps(qx, yy, f"{n:03d}", 22, 42, 34, tone="paper")
        b += T(qx + 82, yy + 18, em, 16.5, "b", BONE)
        b += flaps(qx + 82, yy + 26, why, 10.6, 24, 18.5, cells=12)
        if st == "ok":
            b += flaps(x2 + bw2 - 22 - fw(12, 14.5), yy + 6, act, 14.5, 32, 25, cells=12)
        else:
            b += flaps(x2 + bw2 - 22 - fw(4, 19) - 0, yy + 6, act, 19, 32, 25, tone="paper")
            b += flaps(x2 + bw2 - 22 - fw(4, 19) - 12 - fw(9, 14.5), yy + 6, "REGISTRER", 14.5, 32, 25, tone="ghost")
    # Status
    sy = y + 350
    b += board("kl", x2, sy, bw2, 466)
    b += T(qx, sy + 34, "Status for Invitasjoner", 20, "c", BONE, weight=700)
    b += T(x2 + bw2 - 22, sy + 34, f"{r['paa_lista']} rader, én rute per student", 15, "c", BONE2, "end")
    cw = (bw2 - 44) / r["paa_lista"]
    # Strimmel med én rute per rad, form viser status
    tx = qx
    parts = [(accepted, "ship"), (r["manuelt_registrert"], "ship"), (waiting + expired, "ord"), (still_invalid, "owed")]
    for n, k in parts:
        b += tally(tx, sy + 48, n, k, cw - .4, 26, .4)
        tx += n * cw
    rows = [("SENDT", sent, "Alle gyldige adresser"), ("AKSEPTERT", accepted, "Registrert med Invitasjon"),
            ("VENTER", waiting, "Invitasjon ikke brukt ennå"), ("UTLØPT", expired, "Over 14 dager"),
            ("UGYLDIG", still_invalid, "Rad 37 og 141"), ("MANUELT", r["manuelt_registrert"], "Rad 88 og 203, registrert av deg")]
    for i, (lab, v, note) in enumerate(rows):
        yy = sy + 90 + i * 49
        b += flaps(qx, yy, lab, 15.4, 38, 29, cells=9)
        b += num(qx + fw(9, 15.4) + 8, yy, v, 19, 38, 30, cells=3)
        b += T(qx + fw(9, 15.4) + 76, yy + 25, note, 16, "b", BONE2)
        if lab == "UTLØPT":
            b += flaps(x2 + bw2 - 22 - fw(12, 13), yy + 3, "SEND PÅ NYTT", 13, 32, 25, tone="paper")
    b += T(qx, sy + 90 + 6 * 49 + 22, f"{accepted + r['manuelt_registrert']} registrert, {r['uregistrert']} uregistrert av {r['paa_lista']}. Hel rute: registrert. Hul: venter eller utløpt. Skråstrek: ugyldig.", 15, "c", BONE2)
    svg("02-laerer-klasse.svg", "kl", w, h, "Avgang: faglærer lager Klasse",
        "Navn og emnekode, Canvas-fil, valg av e-postkolonne, ugyldige rader per radnummer, send Invitasjoner og status. Demodata.", b)


# ---- 03 lærer spill ----
def page_okt():
    w, h = 1440, 1100
    b = wall(w, h) + nav(w, "KLASSEØKT")
    b += T(40, 118, "Klasseøkt: Klassisk", 44, "f", INK)
    b += T(362, 116, "Alt er forhåndsutfylt. Du kan lagre uten å endre noe.", 21, "c", INK2)
    b += flaps(w - 40 - fw(15, 22), 78, "LAGRE KLASSEØKT", 22, 46, 35, tone="yellow")
    y = 140
    # Spillinnstillinger
    x, bw, bh = 40, 480, 920
    b += board("okt", x, y, bw, bh)
    px = x + 20
    b += T(px, y + 32, "Spillinnstillinger", 20, "c", BONE, weight=700)
    b += T(x + bw - 20, y + 32, "Standard", 15, "c", BONE2, "end")
    rows = [("Startlager", "12"), ("Enheter i hvert ledd", "4"), ("Ordreforsinkelse", "2 UKER"), ("Fraktforsinkelse", "2 UKER"),
            ("Produksjonsforsinkelse", "2 UKER"), ("Etterspørsel", "4 TIL 8 UKE 5"), ("Lagerkost per enhet", "0,50"), ("Restordrekost per enhet", "1,00"),
            ("Antall uker", "36"), ("Veiledede uker", "1-4"), ("Inaktivitetsgrense", "24 T")]
    for i, (lab, v) in enumerate(rows):
        yy = y + 46 + i * 60
        b += T(px, yy + 28, lab, 17.5, "b", BONE)
        b += flaps(x + bw - 20 - fw(13, 16), yy + 6, v, 16, 36, 29, cells=13, align="right")
        if i < len(rows) - 1:
            b += line(px, yy + 54, x + bw - 20, yy + 54, "#3A3833")
    yy = y + 46 + 11 * 60 + 8
    b += line(px, yy - 12, x + bw - 20, yy - 12, "#47443D")
    b += para(px, yy + 16, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", 56, 16, 23, "b", BONE)
    b += para(px, yy + 76, "Antall uker og etterspørselen er skjult for studentene mens de spiller. Bare Detaljist ser etterspørselen, én uke om gangen.", 56, 15.5, 22, "b", BONE2)
    b += T(px, y + bh - 20, "Demodata", 14, "c", BONE2)
    # Moduser og datoer
    x2, bw2 = 540, 450
    b += board("okt", x2, y, bw2, 920)
    qx = x2 + 20
    b += drum(qx, y + 34, "KI-modus", "REGELSTYRTE SPILLERE", "LLM-SPILLERE", "INGEN KI I TOMME SETER", 18, 17, 36, 29)
    b += drum(qx, y + 164, "Debrief-modus", "PERSONLIG DEBRIEF", "GRUPPEDEBRIEF", "", 18, 17, 36, 29)
    # Obligatorisk: bryter av to klaffer
    oy = y + 292
    b += T(qx, oy, "Obligatorisk", 15, "c", BONE)
    b += flaps(qx, oy + 8, "JA", 26, 40, 32, tone="paper")
    b += flaps(qx + 66, oy + 8, "NEI", 26, 40, 32)
    b += para(qx + 164, oy + 18, "Studenten må fullføre Klasseøkten for å få Studentrapport.", 34, 15, 20, "b", BONE2)
    dy = oy + 78
    b += line(qx, dy - 8, x2 + bw2 - 20, dy - 8, "#47443D")
    b += T(qx, dy + 18, "Datoer", 20, "c", BONE, weight=700)
    for i, (lab, v) in enumerate([("START", "TI 24. NOV 2026"), ("SPILLFRIST", "TI 8. DES"), ("DEBRIEF-FRIST", "FR 11. DES"), ("TESTFRIST", "FR 18. DES")]):
        yy = dy + 32 + i * 46
        b += flaps(qx, yy, lab, 13, 34, 26, cells=13)
        b += flaps(qx + fw(13, 13) + 10, yy, v, 13.6, 34, 25, cells=15)
    ly = dy + 32 + 4 * 46 + 12
    b += line(qx, ly - 8, x2 + bw2 - 20, ly - 8, "#47443D")
    b += T(qx, ly + 18, "Labtimer", 20, "c", BONE, weight=700)
    b += T(x2 + bw2 - 20, ly + 18, "Datalab A2", 16, "c", BONE, "end")
    for i, v in enumerate(["TO 26. NOV 14:15", "MA 30. NOV 10:15", "TO 3. DES 14:15", "MA 7. DES 10:15"]):
        yy = ly + 32 + i * 46
        b += flaps(qx, yy, v, 15, 34, 27, cells=17)
        b += flaps(x2 + bw2 - 20 - fw(5, 13), yy, "FJERN", 13, 34, 25, tone="ghost")
    yy = ly + 32 + 4 * 46
    b += flaps(qx, yy, "LEGG TIL LABTIME", 15, 34, 27, tone="dark")
    # Fordeling
    x3, bw3 = 1010, 390
    b += board("okt", x3, y, bw3, 920)
    rx = x3 + 18
    b += T(rx, y + 32, "Fordeling", 20, "c", BONE, weight=700)
    b += para(rx, y + 60, "240 studenter fordeles tilfeldig i 60 spill à 4. Rolle trekkes per spill.", 46, 16, 22, "b", BONE2)
    gy = y + 118
    cols = 6
    cwc = (bw3 - 36 - (cols - 1) * 3) / cols
    for i in range(60):
        cx = rx + (i % cols) * (cwc + 3)
        yy = gy + (i // cols) * 44
        n = i + 1
        b += flaps(cx, yy, f"{n:02d}", cwc / 2 - .5, 24, 19.5, tone="paper" if n == 17 else "dark")
        for s in range(4):
            b += rect(cx + s * (cwc / 4), yy + 27, cwc / 4 - 1.5, 4, BONE)
    yy = gy + 10 * 44 + 4
    b += line(rx, yy, x3 + bw3 - 18, yy, "#47443D")
    b += T(rx, yy + 26, "Spill 17 i denne trekningen", 16, "c", BONE)
    for i, (r, n) in enumerate([("DETALJIST", "IDA"), ("GROSSIST", "SARA"), ("DISTRIBUTØR", "MIKKEL"), ("FABRIKK", "JONAS")]):
        ry = yy + 36 + i * 31
        b += flaps(rx, ry, r, 12.2, 27, 21.5, cells=11)
        b += flaps(rx + fw(11, 12.2) + 8, ry, n, 12.2, 27, 21.5, cells=8)
    ry = yy + 36 + 4 * 31 + 10
    b += para(rx, ry + 12, "Ingen fordeling er låst før du bekrefter. 0 studenter står uten spill.", 46, 15, 21, "b", BONE2)
    ry += 56
    b += flaps(rx, ry, "KJØR PÅ NYTT", 13.2, 44, 27)
    b += flaps(x3 + bw3 - 18 - fw(7, 21), ry, "BEKREFT", 21, 44, 32, tone="paper")
    svg("03-laerer-spill.svg", "okt", w, h, "Avgang: faglærer setter opp Klasseøkt",
        "Forhåndsutfylte Spillinnstillinger, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling av 240 studenter i 60 spill à 4. Kan lagres uten endring. Demodata.", b)


# ---- 04 student hjem ----
STEPS = ["KLASSESPILL", "DEBRIEF", "QUIZ", "REPLAY", "INDIVIDUELL TEST", "RAPPORT"]


def phone_register():
    o = flaps(16, 18, "AVGANG", 20, 34, 28, tone="yellow")
    o += flaps(16, 70, "DU ER INVITERT", 24.6, 58, 44)
    o += para(16, 156, "Faglærer Bård har invitert deg til IBE160, class-of-1994. Lag en konto med denne adressen. Invitasjonen gjelder i 14 dager.", 46, 16, 22, "b", BONE)
    y = 246
    o += field(16, y, "Navn", "SARA LUND", 22, 15.3, 34, 27)
    o += field(16, y + 70, "E-post, fra Klasselista", "SARA.LUND@STUD.EXAMPLE.NO", 25, 13.3, 34, 23)
    o += T(16, y + 140, "Velg passord", 15, "c", BONE)
    o += flaps(16, y + 147, " ", 15.3, 34, cells=22)
    for i in range(9):
        o += f'<circle cx="{f(16 + i * 16.3 + 7.6)}" cy="{f(y + 164)}" r="4" fill="{BONE}"/>'
    o += flaps(16, y + 200, "OPPRETT KONTO", 26.5, 60, 46, tone="yellow")
    y = 530
    o += line(16, y - 8, 374, y - 8, "#47443D")
    o += para(16, y + 18, "Du skal spille med tre andre i en forsyningskjede. Hver Uke tar du én beslutning: ett tall. Rolle og spill får du når Klassespillet åpner ti. 24. nov.", 46, 15.5, 21, "b", BONE)
    y += 104
    o += T(16, y + 6, "Dette skal du gjennom", 14, "c", BONE)
    for i, st in enumerate(STEPS):
        yy = y + 14 + i * 25
        o += flaps(16, yy, str(i + 1), 18, 23, 19)
        o += flaps(38, yy, st, 12, 23, 19, cells=18)
    o += T(374, 830, "Demodata", 13, "c", BONE2, "end")
    return o


def phone_home():
    o = flaps(16, 16, "AVGANG", 16, 28, 23, tone="yellow")
    o += T(374, 36, "Sara", 16, "c", BONE, "end")
    # Spillet venter på deg
    y = 56
    o += flaps(16, y, "SPILLET VENTER PÅ DEG", 16, 40, 31, tone="yellow")
    o += T(16, y + 62, "Uke 11 er åpen. Jonas og du mangler.", 15.5, "b", BONE)
    o += flaps(16, y + 72, "GÅ TIL TAVLA", 28.8, 46, 36, tone="paper")
    y = 188
    o += flaps(16, y, "SPILL 17", 13, 28, 22.5)
    o += flaps(135, y, "GROSSIST", 13, 28, 22.5)
    o += T(374, y + 20, "Din Rolle", 14, "c", BONE2, "end")
    seats = [("hel", "DETALJIST IDA", "KLAR", "dark"), ("din", "GROSSIST SARA", "DIN TUR", "yellow"),
             ("hel", "DISTRIBUTØR MIKKEL", "KLAR", "dark"), ("hel", "FABRIKK JONAS", "VENTER 3 MIN", "dark")]
    for i, (k, wh, st, tone) in enumerate(seats):
        o += who_row(16, y + 36 + i * 26, k, wh, st, tone)
    y = 338
    o += line(16, y, 374, y, "#47443D")
    o += T(16, y + 22, "Seks steg", 15, "c", BONE, weight=700)
    stat = ["UKE 11", "LÅST", "LÅST", "LÅST", "LÅST", "LÅST"]
    for i, (st, s2) in enumerate(zip(STEPS, stat)):
        yy = y + 30 + i * 28
        cur = i == 0
        o += flaps(16, yy, str(i + 1), 18, 25, 21, tone="paper" if cur else "dark")
        o += jack(38, yy + 12, 20, "din" if cur else "hel", BONE if cur else DIM)
        o += flaps(62, yy, st, 12, 25, 20, cells=16, tone="dark" if cur else "dim")
        if cur:
            o += flaps(374 - fw(6, 12), yy, s2, 12, 25, 20)
        else:
            o += lock_icon(374 - 58, yy + 5, 13, DIM)
            o += T(374, yy + 18, "Låst", 14, "c", DIM, "end")
    y = 544
    o += line(16, y, 374, y, "#47443D")
    o += T(16, y + 22, "Neste frist", 15, "c", BONE, weight=700)
    o += flaps(16, y + 30, "SPILLFRIST", 14.6, 32, 26)
    o += flaps(374 - fw(9, 14.6), y + 30, "TI 8. DES", 14.6, 32, 26)
    o += para(16, y + 82, "Da spiller KI-spillere ut det som gjenstår av alle spill. Debrief-frist fr. 11. des, Testfrist fr. 18. des.", 48, 14.5, 19, "b", BONE2)
    y = 678
    o += line(16, y, 374, y, "#47443D")
    o += T(16, y + 22, "Labtimer", 15, "c", BONE, weight=700)
    o += T(374, y + 22, "Datalab A2", 14, "c", BONE2, "end")
    for i, v in enumerate(["TO 26. NOV 14:15", "MA 30. NOV 10:15", "TO 3. DES 14:15", "MA 7. DES 10:15"]):
        o += flaps(16 + (i % 2) * 180, y + 30 + (i // 2) * 30, v, 9.8, 26, 18.5, cells=16)
    o += T(195, 830, "Demodata", 13, "c", BONE2, "middle")
    return o


def page_hjem():
    w, h = 1000, 900
    b = wall(w, h)
    b += phone("hjem", 50, 28, phone_register())
    b += phone("hjem", 560, 28, phone_home())
    b += T(500, 400, "Første", 28, "f", INK, "middle") + T(500, 429, "møte", 28, "f", INK, "middle")
    b += line(446, 444, 500, 444, INK, 2.4) + path("M456 437L446 444L456 451", stroke=INK, sw=2.4)
    b += T(500, 500, "Hjem", 28, "f", INK, "middle") + T(500, 529, "under spill", 22, "f", INK, "middle")
    b += line(500, 544, 554, 544, INK, 2.4) + path("M544 537L554 544L544 551", stroke=INK, sw=2.4)
    svg("04-student-hjem.svg", "hjem", w, h, "Avgang: Sara på mobil",
        "To telefoner. Venstre: Invitasjon og registrering. Høyre: hjem under spill, med Spill 17, Grossist, de andre setene, seks steg, neste frist, Labtimer og Spillet venter på deg. Demodata.", b)


# ---- 07 debrief ----
def ki_tag(x, y, col=BONE2, txt="KI-generert, kan ta feil", size=14):
    return jack(x, y - 5, 26, "ki", col, 1.8) + T(x + 34, y, txt, size, "c", col)


def phone_d1():
    o = flaps(16, 18, "DEBRIEF", 21, 36, 30)
    o += T(374, 42, "Spill 17", 15, "c", BONE2, "end")
    o += flaps(16, 74, "SKRIV FORKLARING", 21.4, 44, 36)
    o += para(16, 146, "Hvorfor oppførte kjeden seg slik den gjorde, og hvilken rolle spilte ordrene dine? Du skriver alene. De andre ser det ikke.", 44, 16, 22, "b", BONE)
    y = 226
    o += rect(16, y, 358, 276, "#F4F0E5", 3)
    o += para(30, y + 30, "Det føltes som om kundene plutselig ville ha mye mer. Restordren bare vokste, så i uke 11 bestilte jeg 24 for å komme ajour. Så ble det altfor mye på lager mot slutten. Jeg tror ikke jeg regnet med det som allerede var på vei.", 42, 17, 25, "b", INK)
    o += rect(30, y + 244, 2, 20, INK)
    o += flaps(16, 516, "LAGRE FORKLARING", 21.4, 56, 42, tone="yellow")
    o += T(16, 598, "Etter lagring kan den ikke endres.", 14, "b", BONE2)
    # Låst rad
    y = 628
    o += rect(16, y, 358, 104, HOUSE2, 3)
    o += lock_icon(30, y + 14, 18)
    o += T(58, y + 29, "Kunden: låst", 18, "c", BONE, weight=700)
    o += flaps(30, y + 44, " ", 25, 38, 30, cells=12)
    o += T(16, 758, "Låses opp for deg når Forklaringen er lagret.", 14.5, "b", BONE2)
    o += T(16, 780, "2 av 4 har lagret.", 14.5, "b", BONE2)
    o += T(195, 830, "Demodata", 13, "c", BONE2, "middle")
    return o


def arrow(x, y, w, col=YEL, sw=3):
    return (line(x, y, x + w - 6, y, col, sw)
            + path(f"M{f(x + w - 10)} {f(y - 7)}L{f(x + w)} {f(y)}L{f(x + w - 10)} {f(y + 7)}", stroke=col, sw=sw))


def phone_d2():
    """Klimakset: hele tavla står blank, unntatt én liten rad."""
    o = ""
    pitch, cw, ch = 43, 31.5, 41
    for r in range(18):
        if 10 <= r <= 14:
            continue
        o += flaps(16, 14 + r * pitch, " ", cw, ch, cells=11)
    # Raden: i rutenettet, like stor som alle andre klaffer
    ry = 14 + 8 * pitch
    o += flaps(16 + 2.5 * (cw + 1), ry - pitch, "KUNDEN", cw, ch, 26)
    o += flaps(16 + 3 * (cw + 1), ry, "4", cw, ch, 36, tone="amber")
    o += flaps(16 + 7 * (cw + 1), ry, "8", cw, ch, 36, tone="amber")
    o += arrow(16 + 4 * (cw + 1) + 5, ry + ch / 2, 3 * (cw + 1) - 11, YEL, 2.6)
    y = 14 + 10 * pitch
    o += para(195, y + 28, "Kundene bestilte 4 kasser i uka.", 48, 18, 25, "b", BONE, "middle")
    o += para(195, y + 53, "I uke 5 ble det 8, og slik var det resten", 48, 18, 25, "b", BONE, "middle")
    o += para(195, y + 78, "av spillet. Det var hele endringen.", 48, 18, 25, "b", BONE, "middle")
    o += para(195, y + 124, "Alle i gruppa ser denne raden nå.", 48, 15.5, 20, "b", BONE2, "middle")
    o += para(195, y + 148, "Øvelsen dere har spilt, heter Beer Game.", 48, 15.5, 20, "b", BONE2, "middle")
    o += flaps(16, 14 + 17 * pitch, " SE ORDRENE", cw, ch, 32, tone="paper")
    o += T(195, 830, "Demodata", 13, "c", BONE2, "middle")
    return o


def order_chart(x, y, w, h, fs=13.5, lab=True, role_styles=None):
    """Ordrer per Rolle over tid, ett diagram, trappelinjer. Rollene skilles med linjeform og direkte navn."""
    weeks = range(1, 37)
    ymax = 32
    sx = lambda wk: x + (wk - 1) * w / 35
    sy = lambda v: y + h - v * h / ymax
    o = ""
    for v in (0, 10, 20, 30):
        o += line(x, sy(v), x + w, sy(v), "#47443D", 1)
        o += T(x - 5, sy(v) + 4.5, v, fs, "c", BONE2, "end")
    for wk in (1, 12, 24, 36):
        o += T(sx(wk), y + h + fs + 4, f"{wk}", fs, "c", BONE2, "middle")
    styles = {"Detaljist": ("#8F8A7D", 1.5, ""), "Grossist": (BONE2, 2, "1.5 3"), "Distributør": (BONE2, 1.8, "7 3"), "Fabrikk": (BONE, 2.6, "")}
    for r in ROLES:
        col, sw, dash = styles[r]
        d = "".join(f"{'M' if wk == 1 else 'L'}{f(sx(wk))} {f(sy(seat(wk, r)['ordre']))}" for wk in weeks)
        o += path(d, stroke=col, sw=sw, extra=(f'stroke-dasharray="{dash}" ' if dash else "") + 'stroke-linejoin="round"')
    # Kunden
    d = ""
    for wk in weeks:
        v = WK[wk]["demand"]
        d += (f"M{f(sx(wk))} {f(sy(v))}" if wk == 1 else f"H{f(sx(wk))}V{f(sy(v))}")
    o += path(d, stroke=YEL, sw=3)
    if lab:
        o += T(sx(1), sy(4) + 18, "Kunden", fs, "c", YEL, "start", 700)
    return o


def phone_d3():
    o = flaps(16, 18, "ORDRER PER ROLLE", 21.4, 44, 36)
    o += para(16, 86, "Alle fire Rollene, samme akse. Kunden er den gule linja. Resten er ordrer fra ledd til ledd.", 46, 15.5, 21, "b", BONE)
    x, y, wd, hg = 42, 146, 332, 330
    o += order_chart(x, y, wd, hg)
    # Direkte navn på toppene
    o += T(x + 17 * wd / 35, y + hg - 31 * hg / 32 - 5, "Fabrikk", 14, "c", BONE, "middle", 700)
    o += T(x + 10 * wd / 35, y + hg - 24 * hg / 32 - 5, "Grossist", 14, "c", BONE2, "middle")
    o += T(x - 10, y + hg + 18, "Uke", 13.5, "c", BONE2, "end")
    # Forklaring av linjeform
    ly = y + hg + 36
    leg = [("Detaljist", "#8F8A7D", 1.5, ""), ("Grossist", BONE2, 2, "1.5 3"), ("Distributør", BONE2, 1.8, "7 3"), ("Fabrikk", BONE, 2.6, "")]
    for i, (r, col, sw, dash) in enumerate(leg):
        lx = 16 + (i % 2) * 180
        yy = ly + (i // 2) * 21
        o += path(f"M{lx} {yy}h30", stroke=col, sw=sw, extra=f'stroke-dasharray="{dash}"' if dash else "")
        o += T(lx + 36, yy + 5, r, 14, "c", BONE)
    y2 = ly + 44
    o += line(16, y2 - 6, 374, y2 - 6, "#47443D")
    o += T(16, y2 + 12, "Ordreforsterkning", 15, "c", BONE, weight=700)
    for i, r in enumerate(ROLES):
        a = FX["amplification"][r]
        yy = y2 + 20 + i * 34
        o += flaps(16, yy, r.upper(), 11.4, 29, 24, cells=11)
        o += flaps(158, yy, f"{a:.1f}".replace(".", ",") + "X", 15, 29, 24, cells=4, align="right")
        o += rect(226, yy + 8, 148 * a / 7.6, 12, BONE)
    o += T(16, y2 + 20 + 4 * 34 + 14, "Vis som tabell", 15, "c", BONE, extra='text-decoration="underline"')
    o += T(195, 830, "Demodata", 13, "c", BONE2, "middle")
    return o


def lager_cost():
    wks = [w for w in range(25, 37) if seat(w)["lager"] > 0]
    peak = max(wks, key=lambda w: seat(w)["lager"])
    win = range(26, 34)
    return peak, seat(peak)["lager"], sum(seat(w)["ukekost"] for w in win)


def phone_d4():
    s = seat(11)
    peak, pv, cost = lager_cost()
    assert seat(24)["lager"] == 0 and seat(25)["lager"] > 0 and pv == 30
    o = flaps(16, 18, "DITT ØYEBLIKK", 18, 36, 30)
    o += T(305, 44, "UKE", 15, "c", BONE, "end") + num(310, 12, 11, 31, 46, 42)
    y = 76
    o += T(16, y, "Dette så du", 15, "c", BONE, weight=700)
    pairs = [("LAGER", s["lager"]), ("RESTORDRE", s["restordre"]), ("ORDRE INN", s["innkommende_ordre"]), ("PÅ VEI", s["paa_vei_foer_ordre"])]
    for i, (lb, v) in enumerate(pairs):
        cx = 16 + (i % 2) * 182
        yy = y + 8 + (i // 2) * 30
        o += flaps(cx, yy, lb, 11, 26, 21, cells=9)
        o += num(cx + 110, yy, v, 19, 26, 22, cells=2)
    y = 148
    o += T(16, y + 16, "Dette bestilte du", 15, "c", BONE, weight=700)
    o += num(176, y, 24, 28, 42, 38, tone="amber")
    o += T(242, y + 26, "på toppen av 16", 15, "c", BONE2)
    y = 204
    o += line(16, y - 6, 374, y - 6, "#47443D")
    o += T(16, y + 14, "Dette skjedde senere", 15, "c", BONE, weight=700)
    d13 = seat(13, "Distributør")
    txt = (f"Ordren på 24 nådde Distributør i uke 13. Distributør hadde lager {seat(12, 'Distributør')['lager']} uka før og fikk restordre {d13['restordre']} den uka. "
           f"Levering til deg kom i uke 15: {seat(15)['levering']} kasser. Fra uke 25 hadde du lager igjen, opp til {pv} kasser i uke {peak}.")
    o += para(16, y + 38, txt, 46, 15.5, 21, "b", BONE)
    o += T(16, y + 160, "Lagerkost uke 26 til 33", 15.5, "b", BONE2)
    o += flaps(374 - fw(9, 14), y + 144, f"{kr(cost)} KR", 14, 28, 23, cells=9, align="right")
    y = 384
    o += line(16, y - 6, 374, y - 6, "#47443D")
    o += T(16, y + 14, "Dette så de andre i uke 11", 15, "c", BONE, weight=700)
    for i, r in enumerate(["Detaljist", "Distributør", "Fabrikk"]):
        st = seat(11, r)
        yy = y + 24 + i * 58
        o += flaps(16, yy, r.upper(), 12, 26, 21.5, cells=11)
        o += T(16, yy + 45, f"Lager {st['lager']}, restordre {st['restordre']}, ordre inn {st['innkommende_ordre']}, på vei {st['paa_vei_foer_ordre']}", 14.5, "b", BONE2)
    y = 594
    o += line(16, y - 6, 374, y - 6, "#47443D")
    o += para(16, y + 18, "Ingen i kjeden så hele bildet. Du så 13 skyldig og en kø som kom sent. Det samme mønsteret kom igjen hos alle fire Rollene: forsinkelse, og ordrer som alt var på vei.", 46, 15.5, 21, "b", BONE)
    o += ki_tag(16, y + 112)
    o += T(16, y + 134, "Tallene er hentet fra spillets logg.", 14, "c", BONE2)
    o += flaps(16, 752, "NESTE ØYEBLIKK", 25, 44, 34, tone="paper")
    o += T(195, 830, "Demodata", 13, "c", BONE2, "middle")
    return o


def phone_d5():
    o = flaps(16, 18, "DEBRIEF-QUIZ", 21, 36, 30)
    o += T(374, 42, "Spørsmål 3", 15, "c", BONE2, "end")
    o += para(16, 86, "Kunden bestilte 8 i uka fra uke 5. Hvorfor ble ordrene så mye større oppover i kjeden?", 42, 18, 25, "b", BONE)
    opts = [("A", "Kundene ville ha stadig mer utover i spillet.", "feil"),
            ("B", "Hvert ledd bestilte på toppen av det som alt var på vei, fordi leveransene kom sent.", "rett"),
            ("C", "Fabrikken produserte for lite.", None)]
    y = 180
    for lt, tx, st in opts:
        lines = textwrap.wrap(tx, 36)
        hh = 26 + len(lines) * 21
        if st == "feil":
            o += rect(16, y, 358, hh, HOUSE2, 3)
        o += flaps(24, y + 8, lt, 22, 32, 26, tone="paper" if st else "dark")
        o += para(58, y + 25, tx, 36, 16, 21, "b", BONE)
        if st == "feil":
            o += path(f"M{350} {y + 12}l14 14m0 -14l-14 14", stroke=BONE, sw=3)
        if st == "rett":
            o += path(f"M{348} {y + 22}l6 7l11 -13", stroke=BONE, sw=3)
        y += hh + 10
    y += 6
    o += flaps(16, y, "A ER FEIL", 19, 34, 27)
    o += para(16, y + 58, "Etterspørselen lå fast på 8 fra uke 5 til slutten. Det var ordrene mellom leddene som vokste. Du så selv 16 på vei da du la 24 på toppen.", 46, 16, 22, "b", BONE)
    o += ki_tag(16, y + 150)
    y += 170
    o += line(16, y, 374, y, "#47443D")
    o += para(16, y + 26, "Du må svare riktig på alle for å gå videre, men kan prøve så mange ganger du vil. Quizen teller ikke.", 46, 15, 21, "b", BONE2)
    o += flaps(16, y + 88, "SVAR PÅ NYTT", 28.8, 56, 42, tone="yellow")
    o += T(195, 830, "Demodata", 13, "c", BONE2, "middle")
    return o


def page_debrief():
    w, h = 2100, 1200
    b = wall(w, h)
    b += T(44, 62, "Debriefen: tavla snur", 52, "f", INK)
    b += T(462, 60, "Fem steg på egen telefon, én delt skjerm for gruppa.", 24, "c", INK2)
    sc = .78
    pw = 390 * sc
    gap = (w - 88 - 5 * pw) / 4
    fr = [("1", "Forklaring", "Du skriver før noe avsløres. Raden for kunden er låst til du har lagret.", phone_d1()),
          ("2", "Avsløringen", "Hele tavla står blank. Én liten rad klaffer fram: 4 til 8. Det er klimakset, og det er lite.", phone_d2()),
          ("3", "Ordrer per Rolle", "Samme diagram for alle. Forsterkning 1,8× hos Detaljist, 7,6× hos Fabrikk.", phone_d3()),
          ("4", "Ditt øyeblikk", "Uke 11: hva du så, hva du bestilte, hva det kostet, hva de andre så. Bare på din telefon.", phone_d4()),
          ("5", "Quiz", "Feil svar forklares. Prøv igjen til alt er riktig. Teller ikke.", phone_d5())]
    for i, (k, title, note, c) in enumerate(fr):
        x = 44 + i * (pw + gap)
        b += phone("deb", x, 92, c, sc)
    for i, (k, title, note, c) in enumerate(fr):
        x = 44 + i * (pw + gap)
        b += T(x, 792, k, 29, "f", INK) + T(x + 22, 792, title, 29, "f", INK)
        b += para(x, 815, note, 44, 16.5, 21, "b", INK2)
    # Delt skjerm: hele spillet som lang logg
    y = 868
    bx, bw, bh = 44, w - 88, 312
    b += board("deb", bx, y, bw, bh)
    px = bx + 20
    b += T(px, y + 30, "Delt skjerm", 20, "c", BONE, weight=700)
    b += T(px + 106, y + 30, "Hele spillet som logg, Ordre per uke. Viser ingen navn og ingen egne øyeblikk.", 16, "c", BONE2)
    b += T(bx + bw - 20, y + 30, "Demodata", 14, "c", BONE2, "end")
    lw = 126
    cw = (bw - 40 - lw) / 36
    cell = (cw - 12) / 2
    for wk in range(1, 37):
        b += T(px + lw + (wk - 1) * cw + cw / 2 - 1.5, y + 54, wk, 14, "c", BONE2, "middle")
    for i, r in enumerate(ROLES):
        ry = y + 62 + i * 40
        b += flaps(px, ry, r.upper(), 10.6, 36, 22, cells=11)
        for wk in range(1, 37):
            b += num(px + lw + (wk - 1) * cw, ry, seat(wk, r)["ordre"], cell, 36, 26, cells=2)
    # Kunden, den lille raden
    ry = y + 62 + 4 * 40 + 18
    b += line(px, ry - 10, bx + bw - 20, ry - 10, BONE2, 1)
    b += T(px, ry + 24, "Kunden", 20, "c", YEL, weight=700)
    for wk in range(1, 37):
        b += num(px + lw + (wk - 1) * cw, ry, WK[wk]["demand"], cell, 36, 26, tone="amber", cells=2)
    b += T(px, ry + 58, "Alt over streken er ordrer mellom leddene. Raden under er alt kunden gjorde: 4 i fire uker, så 8, og aldri mer enn det.", 17, "b", BONE)
    svg("07-debrief.svg", "deb", w, h, "Avgang: Gruppedebrief",
        "Fem telefonruter: Forklaring med låst avsløring, etterspørselen avsløres 4 til 8, ordrer per Rolle, ditt øyeblikk i Uke 11, quiz. Pluss delt skjerm med hele spillet som logg og kunden som én liten rad. Demodata.", b)


# ---- 08 oversikt ----
def page_oversikt():
    w, h = 1600, 1000
    G = FX["class_games"]
    count = lambda s: sum(1 for g in G if g["status"] == s)
    assert (count("ferdig"), count("pågår") + count("pauset"), count("pauset"), count("venter")) == (41, 15, 2, 4)
    ki_total = sum(g["ki_seter"] for g in G if g["status"] != "ferdig")
    b = wall(w, h) + nav(w, "OVERSIKT") + rect(0, 62, w, 44, HOUSING)
    # Filter på samme kabinett som navigasjonen
    y = 66
    fl = [("ALLE", 60, True), ("FERDIG", 41, False), ("PÅGÅR", 15, False), ("PAUSET", 2, False), ("VENTER", 4, False), ("KI-SETER", ki_total, False)]
    x = 20
    for lab, n, act in fl:
        txt = f"{lab} {n}"
        b += flaps(x, y, txt, 13.6, 32, 26, tone="paper" if act else "dark")
        x += fw(len(txt), 13.6) + 10
    b += T(x + 4, y + 22, "IBE160, class-of-1994. Oppdatert nå.", 16, "c", BONE2)
    b += flaps(w - 20 - fw(12, 16.4), y, "SEND MELDING", 16.4, 32, 26, tone="paper")
    b += T(w - 20 - fw(12, 16.4) - 10, y + 22, "Til alle, ett spill eller én student", 15.5, "c", BONE2, "end")
    # Haster
    y = 113
    b += jack(20, y + 19, 44, "naer", INK)
    b += flaps(70, y, "SPILL 02 VENTER PÅ GROSSIST NOAH I 23 T", 15, 38, 30, tone="yellow")
    ax = 70 + fw(39, 15) + 12
    b += T(ax, y + 25, "KI overtar om 1 t.", 19, "c", INK, weight=700)
    b += flaps(w - 20 - fw(10, 15), y + 2, "KI OVERTAR", 15, 34, 27)
    b += flaps(w - 20 - fw(10, 15) - 10 - fw(13, 15), y + 2, "MELD TIL NOAH", 15, 34, 27)
    # Tavla
    by, bh = 160, 670
    b += board("ov", 12, by, w - 24, bh)
    colw = (w - 24 - 24 - 2 * 14) / 3
    cw, ch, fs = 9.5, 27, 21
    rstep = 31.8
    def rowx(cx):
        no = cx
        ln = no + fw(2, 18) + 5
        st = ln + 40 + 7
        uk = st + fw(6, cw) + 7
        wh = uk + fw(2, cw) + 7
        ti = wh + fw(18, cw) + 7
        ko = ti + fw(3, cw) + 7
        ta = ko + fw(4, cw) + 7
        return no, ln, st, uk, wh, ti, ko, ta
    for c in range(3):
        cx = 24 + c * (colw + 14)
        no, ln, st, uk, wh, ti, ko, ta = rowx(cx)
        hy = by + 19
        for xx, t in [(no, "Nr"), (st, "Status"), (uk, "Uke"), (wh, "Venter på"), (ti, "Tid"), (ko, "Kost"), (ta, "Tiltak")]:
            b += T(xx, hy, t, 14, "c", BONE2)
        for r in range(20):
            g = G[c * 20 + r]
            yy = by + 26 + r * rstep
            s = g["status"]
            near = g.get("ventet_timer", 0) >= 23
            tone = "yellow" if near else ("dim" if s == "ferdig" else "dark")
            word = {"ferdig": "FERDIG", "pågår": "PÅGÅR", "pauset": "PAUSE", "venter": "VENTER"}[s]
            who = ""
            if s == "venter":
                who = f"{g['venter_paa']} {g['navn']}".upper()
            elif s == "pauset":
                who = "TIL I KVELD 19:00"
            elif g["ki_seter"]:
                who = f"{g['ki_seter']} KI-SPILLER" + ("E" if g["ki_seter"] > 1 else "")
            tid = f"{g['ventet_timer']}T" if s == "venter" else ""
            act = "MELD" if s in ("venter", "pauset") else ""
            b += flaps(no, yy, f"{g['spill']:02d}", 18, ch, 22, tone="paper" if s != "ferdig" else "dim")
            b += jack_game(ln, yy + ch / 2, 40, g, YEL if near else (DIM if s == "ferdig" else BONE))
            b += flaps(st, yy, word, cw, ch, fs, cells=6, tone=tone)
            b += num(uk, yy, g["uke"], cw, ch, fs, tone=tone)
            b += flaps(wh, yy, who, cw, ch, fs, cells=18, tone=tone)
            b += flaps(ti, yy, tid, cw, ch, fs, cells=3, tone=tone, align="right")
            b += flaps(ko, yy, str(g["kjedekost"]), cw, ch, fs, cells=4, tone=tone, align="right")
            b += flaps(ta, yy, act, cw, ch, fs, cells=4, tone="paper" if act and not near else ("yellow" if near else "dim"))
    # Trakten på veggen
    fy = by + bh + 14
    F = FX["funnel"]
    steps = [("Registrert", F["registrert"]), ("Klassespill ferdig", F["klassespill_ferdig"]), ("Debrief ferdig", F["debrief_ferdig"]),
             ("Quiz bestått", F["quiz_bestått"]), ("Replay ferdig", F["replay_ferdig"]), ("Test levert", F["test_levert"]), ("KI-vurdering klar", F["ki_vurdering_klar"])]
    colf = 158
    bw_f = colf - 14
    for i, (lab, v) in enumerate(steps):
        fx = 20 + i * colf
        b += T(fx, fy + 16, lab, 16, "c", INK)
        b += num(fx, fy + 24, v, 24, 44, 38, cells=3)
        b += rect(fx, fy + 76, bw_f, 8, WALL2)
        if v:
            b += rect(fx, fy + 76, bw_f * v / 240, 8, INK)
    # Forklaring av linjene
    lx = 20 + 7 * colf + 14
    b += T(lx, fy + 16, "Linja i hver rad", 16, "c", INK)
    b += legend_forms(lx, fy + 36, INK, INK, 23, 2, 222)
    b += T(lx, fy + 118, "Fire Seter per linje. Hvert hull er ett KI-Sete.", 15, "c", INK2)
    b += T(20, fy + 106, "Stolpene viser andel av 240 registrerte.", 15, "c", INK2)
    b += T(w - 20, h - 12, "Demodata", 14, "c", INK2, "end")
    svg("08-laerer-oversikt.svg", "ov", w, h, "Avgang: Oversikten, 60 Klassespill på én tavle",
        "Storskjerm-tavle med 60 nummererte rader: status, uke, hvem spillet venter på, ventetid, kostnad og tiltak. Koblingslinjer viser status i form. Spill 2 er nær overtakelse. Trakt nederst. Demodata.", b)


# ---- 09 kontaktark ----
def page_alle():
    w, h = 2000, 1400
    b = wall(w, h)
    b += T(44, 66, "Alle andre sider, samme tavle", 52, "f", INK)
    b += T(w - 44, 62, "Lav detalj. Demodata.", 20, "c", INK2, "end")
    cols = 6
    cw = (w - 88 - 5 * 18) / 6
    mh = 190

    def bars(x, y, lines):
        o = ""
        for i, (txt, tone) in enumerate(lines):
            o += flaps(x, y + i * 24, txt, 10.2, 21, 17, tone=tone)
        return o

    def rows_mini(x, y, n, cols_=20, tone="dark"):
        return "".join(flaps(x, y + i * 18, " ", 11, 15, cells=cols_, tone=tone) for i in range(n))

    M = {}
    M["Invitasjon og registrering"] = lambda x, y: flaps(x, y, "DU ER INVITERT", 13, 28, 22) + flaps(x, y + 40, "SARA LUND", 10, 20, 16, cells=20) + flaps(x, y + 66, "PASSORD", 10, 20, 16, cells=20) + flaps(x, y + 100, "OPPRETT KONTO", 13, 30, 24, tone="yellow")
    M["Logg inn"] = lambda x, y: flaps(x, y, "AVGANG", 14, 26, 21, tone="yellow") + flaps(x, y + 40, "E-POST", 10, 20, 16, cells=20) + flaps(x, y + 66, "PASSORD", 10, 20, 16, cells=20) + flaps(x, y + 100, "LOGG INN", 15, 30, 24, tone="yellow")
    M["Regler før første ordre"] = lambda x, y: flaps(x, y, "SLIK LESER DU TAVLA", 12, 24, 19) + "".join(g_mini_row(x, y + 34 + i * 22, a, b_, k) for i, (a, b_, k) in enumerate([("LAGER", 12, None), ("OM 1 UKE", 4, "ship"), ("OM 3 UKER", 4, "ord"), ("RESTORDRE", 0, None)])) + flaps(x, y + 126, "JEG ER KLAR", 12, 26, 20, tone="yellow")
    M["Startoppgave"] = lambda x, y: flaps(x, y, "STARTOPPGAVE", 12, 24, 19) + flaps(x, y + 36, "OM 1 UKE KOMMER", 10, 20, 16) + num(x + 180, y + 36, 4, 12, 20, 16) + flaps(x, y + 62, "HVOR MYE PÅ VEI?", 10, 20, 16) + num(x + 180, y + 62, 16, 12, 20, 16, tone="amber") + flaps(x, y + 100, "SVAR", 18, 30, 24, tone="yellow")
    M["Replay"] = lambda x, y: flaps(x, y, "REPLAY", 12, 24, 19) + flaps(x + 90, y + 3, "UKE 7", 10, 20, 16) + "".join(who_row(x, y + 34 + i * 24, k, n, s, "dark", jw=16, cw=6.2, ch=20, fs=13.5) for i, (k, n, s) in enumerate([("ki", "DETALJIST KI", "KLAR"), ("din", "GROSSIST DU", "DIN TUR"), ("ki", "DISTRIB. KI", "KLAR"), ("ki", "FABRIKK KI", "KLAR")]))
    M["Replay-gjennomgang"] = lambda x, y: flaps(x, y, "FØR", 12, 24, 19) + num(x + 44, y, 24, 12, 24, 19, tone="amber") + flaps(x + 90, y, "NÅ", 12, 24, 19) + num(x + 118, y, 12, 12, 24, 19) + path("".join(f"{'M' if i == 0 else 'L'}{x + i * 7} {y + 112 - h_}" for i, h_ in enumerate([18, 22, 30, 60, 76, 60, 40, 30, 30, 26, 24, 24, 26, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24])), stroke=DIM, sw=1.6) + path("".join(f"{'M' if i == 0 else 'L'}{x + i * 7} {y + 112 - h_}" for i, h_ in enumerate([18, 22, 26, 34, 40, 34, 30, 28, 26, 26, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24])), stroke=BONE, sw=2)
    M["Individuell test"] = lambda x, y: flaps(x, y, "A", 13, 20, 16, tone="paper") + T(x + 20, y + 15, "Flervalg", 14, "c", BONE) + flaps(x, y + 26, "B", 13, 20, 16) + T(x + 20, y + 41, "Langsvar", 14, "c", BONE) + rect(x + 92, y, 190, 46, "#F4F0E5", 2) + T(x + 100, y + 20, "Ordren i uke 11 ...", 13.5, "b", INK) + "".join(flaps(x + i * 24, y + 60 + (i % 3) * 0, str(v), 22, 22, 17, tone="dark") for i, v in enumerate([4, 8, 8, 12, 16, 24, 16, 8, 4, 4])) + path(f"M{x} {y + 130}L{x + 60} {y + 126}L{x + 100} {y + 96}L{x + 150} {y + 90}L{x + 210} {y + 126}L{x + 280} {y + 130}", stroke=YEL, sw=2.4) + T(x, y + 148, "Tegne- og tabelloppgave", 14, "c", BONE2)
    M["KI-vurdering"] = lambda x, y: ki_tag(x, y + 12, BONE, "KI-generert, kan ta feil") + para(x, y + 36, "Teller ikke og er ingen karakter. Forklaringen din viser forsinkelsen, men ikke ordrene på vei.", 40, 14, 18, "b", BONE) + flaps(x, y + 112, "LES HELE", 12, 26, 20, tone="paper")
    M["Studentrapport (PDF)"] = lambda x, y: rect(x, y, 112, 148, "#F4F0E5", 2) + T(x + 8, y + 22, "Studentrapport", 13.5, "c", INK) + "".join(rect(x + 8, y + 34 + i * 12, 96 - (i % 3) * 14, 3, INK2) for i in range(9)) + flaps(x + 126, y + 100, "LAST NED", 13, 30, 23, tone="yellow") + T(x + 126, y + 22, "Sara, spill 17", 14, "c", BONE) + T(x + 126, y + 44, "Alle seks steg", 14, "c", BONE2)
    M["Alle spill side om side"] = lambda x, y: mini_side(x, y)
    M["Lærerhjem med klasser"] = lambda x, y: "".join(flaps(x, y + i * 40, c, 11, 30, 23, cells=15) + T(x + 188, y + i * 40 + 20, t, 14, "c", BONE2) for i, (c, t) in enumerate([("CLASS-OF-1994", "60 spill, pågår"), ("IBE160 2025", "Ferdig"), ("NY KLASSE", "Lag en ny")]))
    M["Klasserapport"] = lambda x, y: flaps(x, y, "IBE160", 12, 24, 19) + "".join(rect(x, y + 36 + i * 16, [282, 193, 142, 114, 68, 14][i], 10, BONE) for i in range(6)) + flaps(x, y + 130, "LAST NED PDF", 11, 24, 19, tone="paper")
    M["Spillinnsikt (uke for uke)"] = lambda x, y: flaps(x, y, "SPILL 17", 12, 24, 19) + "".join(num(x + i * 28, y + 34 + r * 26, seat(9 + i, ROLES[r])["ordre"], 11, 22, 17) for r in range(4) for i in range(10) if i < 10)
    M["Studentside"] = lambda x, y: flaps(x, y, "SARA LUND", 12, 26, 20) + "".join(jack(x, y + 50 + i * 22, 20, "din" if i == 0 else "hel", BONE) + T(x + 28, y + 55 + i * 22, t, 14, "c", BONE) for i, t in enumerate(["Klassespill, Uke 11", "Debrief: ikke startet", "Forsøk på quiz: 0", "Rapport: ikke klar"]))
    M["Spill alle side om side for plenum"] = lambda x, y: mini_plenum(x, y)
    M["Tverrklasse-statistikk"] = lambda x, y: flaps(x, y, "3 KLASSER", 12, 24, 19) + "".join(rect(x + 20 + i * 48, y + 150 - hh, 26, hh, BONE) + T(x + 33 + i * 48, y + 148 + 0 - hh - 4, v, 13.5, "c", BONE, "middle") for i, (hh, v) in enumerate([(82, "2 266"), (62, "1 780"), (96, "2 610")]))
    M["Meldinger"] = lambda x, y: flaps(x, y, "TIL", 12, 24, 19) + flaps(x + 42, y, "SPILL 02", 12, 24, 19, tone="paper") + rect(x, y + 34, 282, 66, "#F4F0E5", 2) + T(x + 8, y + 56, "Noah, spillet venter på ordren din", 14, "b", INK) + flaps(x, y + 112, "SEND MELDING", 12, 28, 22, tone="yellow")
    M["Lærers testspill"] = lambda x, y: flaps(x, y, "TESTSPILL", 12, 24, 19) + "".join(who_row(x, y + 34 + i * 24, k, n, s, "dark", jw=16, cw=6.2, ch=20, fs=13.5) for i, (k, n, s) in enumerate([("ki", "DETALJIST KI", "KLAR"), ("din", "GROSSIST BÅRD", "DIN TUR"), ("ki", "DISTRIB. KI", "KLAR"), ("ki", "FABRIKK KI", "KLAR")]))
    M["Admin-område"] = lambda x, y: "".join(flaps(x, y + i * 38, t, 12, 30, 23, cells=16, tone="paper" if i == 0 else "dark") for i, t in enumerate(["BRUKERE", "ROLLER", "KI-KOSTNAD", "KLASSER"]))
    M["Brukere og roller"] = lambda x, y: "".join(flaps(x, y + i * 28, a, 9.5, 24, 18, cells=14) + flaps(x + 150, y + i * 28, r_, 9.5, 24, 18, cells=13, tone="paper" if r_ == "ADMIN" else "dark") for i, (a, r_) in enumerate([("BÅRD", "FAGLÆRER"), ("BÅRD", "ADMIN"), ("INGRID", "ASSISTENT"), ("SARA LUND", "STUDENT"), ("NOAH MOE", "STUDENT")]))
    M["KI-kostnad"] = lambda x, y: flaps(x, y, "DENNE KLASSEØKTEN", 11, 24, 19) + flaps(x, y + 34, "SPERRE PÅ", 12, 30, 23, tone="paper") + "".join(rect(x + i * 22, y + 150 - hh, 16, hh, BONE) for i, hh in enumerate([18, 30, 26, 44, 38, 56, 62, 48, 40, 34, 30, 24, 20]))

    def g_mini_row(x, y, a, v, k):
        o = flaps(x, y, a, 9.2, 19, 15, cells=9)
        o += num(x + 92, y, v, 12, 19, 15)
        if k and v:
            o += tally(x + 124, y + 3, v, k, 4.4, 13)
        return o

    def mini_side(x, y):
        # Etter Debriefen: alle seter sammenlignes per Rolle. Ingen navn, ingen rangering.
        o = ""
        for i in range(12):
            cx = x + (i % 4) * 72
            yy = y + (i // 4) * 50
            o += rect(cx, yy, 66, 44, HOUSE2, 2)
            pts = [seat(w_, "Fabrikk")["ordre"] * (1 + (i % 3) * .2) for w_ in range(5, 30, 3)]
            d = "".join(f"{'M' if j == 0 else 'L'}{f(cx + 3 + j * 7.4)} {f(yy + 40 - min(v, 34) * 1.05)}" for j, v in enumerate(pts))
            o += path(d, stroke=BONE, sw=1.3)
        return o

    def mini_plenum(x, y):
        o = ""
        for i in range(30):
            cx = x + (i % 6) * 48
            yy = y + (i // 6) * 31
            g = FX["class_games"][i]
            o += flaps(cx, yy, f"{g['spill']:02d}", 9, 16, 13, tone="dim" if g["status"] == "ferdig" else "dark")
            o += jack_game(cx + 20, yy + 8, 24, g, DIM if g["status"] == "ferdig" else BONE).replace('stroke-width="2.2"', 'stroke-width="1.4"')
        return o

    groups = [("Student", [("Invitasjon og registrering", "Fra e-post til konto. Klaffefelt, ingen åpen registrering."),
                           ("Logg inn", "E-post og passord, én gul klaff."),
                           ("Regler før første ordre", "Tavla forklart rad for rad før første Uke."),
                           ("Startoppgave", "Les tavla: hvor mye er på vei? Teller ikke."),
                           ("Replay", "Én runde til mot KI-spillere, alle merket med hull."),
                           ("Replay-gjennomgang", "Første runde mot Replay, samme akse."),
                           ("Individuell test", "Flervalg, tegne- og tabelloppgave, langsvar."),
                           ("KI-vurdering", "Merket KI. Teller ikke, er ingen karakter."),
                           ("Studentrapport (PDF)", "All dokumentasjon samlet. Klar til å laste ned."),
                           ("Alle spill side om side", "Etter Debriefen: alle spillene, ingen navn, ingen rangering.")]),
              ("Faglærer", [("Lærerhjem med klasser", "Klassene dine, og hva som trenger deg."),
                            ("Klasserapport", "Trakt og resultater for hele Klasseøkten."),
                            ("Spillinnsikt (uke for uke)", "Ett spill åpnet: hver Ordre per Rolle per Uke."),
                            ("Studentside", "Én student: seks steg, forsøk, Forklaring."),
                            ("Spill alle side om side for plenum", "Hele tavla for storskjerm i Labtimen."),
                            ("Tverrklasse-statistikk", "Kjedekostnad mellom klasser, aldri personer."),
                            ("Meldinger", "Til alle, ett spill eller én student. E-post også."),
                            ("Lærers testspill", "Spill selv med tre KI-spillere før du inviterer.")]),
              ("Admin", [("Admin-område", "Inngangen for plattformdrift."),
                         ("Brukere og roller", "Hvem er hva. Rollene står i klaff."),
                         ("KI-kostnad", "Forbruk per Klasseøkt og sperre.")])]
    # Plassering: gruppetittel, rutenett på 6 kolonner, tom plass brukes til linjeforklaringen
    rowh = 298
    y = 86

    def cell(x, y, title, desc):
        o = rect(x, y + 8, cw, mh, HOUSING, 3, 'filter="url(#c02-alle-sh)"')
        o += M[title](x + 10, y + 16)
        o += T(x, y + mh + 36, title, 22, "f", INK)
        o += para(x, y + mh + 58, desc, 46, 14.5, 19, "b", INK2)
        return o

    # Student: rad 1 og 2
    S = groups[0][1]
    F = groups[1][1]
    A = groups[2][1]
    def heading(y, t):
        return T(44, y + 26, t, 30, "f", INK) + line(44 + len(t) * 14 + 14, y + 16, w - 44, y + 16, INK, 2)
    b += heading(y, "Student")
    y += 34
    for i, (t, d) in enumerate(S):
        cx = 44 + (i % 6) * (cw + 18)
        b += cell(cx, y + (i // 6) * rowh, t, d)
    # Linjeforklaring i de to ledige rutene
    lx = 44 + 4 * (cw + 18)
    ly = y + rowh + 8
    b += rect(lx, ly, 2 * cw + 18, mh, HOUSING, 3)
    b += T(lx + 16, ly + 30, "Koblingslinjene følger deg overalt", 19, "c", BONE, weight=700)
    b += legend_forms(lx + 16, ly + 58, BONE, BONE, 30, 2, 310)
    y += 2 * rowh
    b += heading(y, "Faglærer")
    y += 34
    for i, (t, d) in enumerate(F):
        cx = 44 + (i % 6) * (cw + 18)
        if i >= 6:
            b += cell(cx, y + rowh, t, d)
        else:
            b += cell(cx, y, t, d)
    # Admin i samme rad som de to siste Faglærer-sidene
    ax = 44 + 3 * (cw + 18)
    for i, (t, d) in enumerate(A):
        cx = 44 + (i + 3) * (cw + 18)
        b += cell(cx, y + rowh, t, d)
    b += T(ax, y + rowh - 10, "Admin", 30, "f", INK) + line(ax + 84, y + rowh - 20, w - 44, y + rowh - 20, INK, 2)
    svg("09-alle-sider.svg", "alle", w, h, "Avgang: kontaktark over alle andre sider",
        "Alle øvrige sider skissert i klaffespråket, gruppert for Student, Faglærer og Admin. Demodata.", b)


# ---- concept.md skrives for hånd ----
PAGES = [page_landing, page_klasse, page_okt, page_hjem, page_spill, page_dynamikk, page_debrief, page_oversikt, page_alle]

if __name__ == "__main__":
    for p in PAGES:
        p()
    print("bygd", len(PAGES))
