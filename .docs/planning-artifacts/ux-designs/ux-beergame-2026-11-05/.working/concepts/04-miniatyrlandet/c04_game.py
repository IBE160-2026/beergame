"""Spillskjermen: Saras diorama, veivisningen, landskapet og den faste tallraden."""
from c04_lib import *

H_SCENE = 346
SLOT_Y = {1: 0.0, 2: -2.35}


def slots_for(week):
    """Deling av «På vei» for Grossisten. Uke 11: 4 (1 uke), 4 (2 uker), 8 (3 uker) = 16."""
    if week == 11:
        return {1: 4, 2: 4, 3: 8}
    if week == 12:
        return {1: 4, 2: 8, 3: 24}
    if week == 36:
        return {1: 7, 2: 9, 3: 9}
    raise ValueError(week)


def diorama(pg, lager=0, rest=13, slots=None, tally=None, H=H_SCENE, signs=True, name="Sara", gate_van=0,
            courier_at=None, courier_label=None, motion=False, extra_plate=None, W=390):
    """Scenen i W×H. Veien går fra tåka oppstrøms, rundt hallen, forbi porten og ned mot tåka nedstrøms."""
    slots = {1: 4, 2: 4, 3: 8} if slots is None else slots
    tally = tally or Tally()
    iso = Iso(pg, 134, 110, 27)
    clip = pg.clip(0, 0, W, H)
    out = R(0, 0, W, H, 0, GRASS)
    for (a, b, c, d) in [(70, 50, 90, 26), (330, 120, 70, 22), (60, 290, 80, 22), (250, 250, 70, 18)]:
        out += f'<ellipse cx="{a}" cy="{b}" rx="{c}" ry="{d}" fill="{GRASS_D}" opacity=".5"/>'
    # fjord med kaikant
    out += iso.poly([(7.5, -30, -0.35), (40, -30, -0.35), (40, 40, -0.35), (7.5, 40, -0.35)], FJORD_L)
    out += iso.poly([(8.3, -30, -0.35), (40, -30, -0.35), (40, 40, -0.35), (8.3, 40, -0.35)], FJORD)
    out += waves(iso, 8.5, -4, 17, 9, 14)
    out += iso.poly([(7.5, -30, 0), (7.5, 40, 0), (7.5, 40, -0.35), (7.5, -30, -0.35)], "#8FA4AB", "#5B717A", 0.5)
    out += iso.poly([(6.8, -30, 0), (7.5, -30, 0), (7.5, 40, 0), (6.8, 40, 0)], CONCRETE)
    # fergerampe og ferge
    out += iso.tbox(7.5, 3.5, -0.05, 1.6, 1.15, 0.08, "#9FB2B9")
    out += iso.shadow(9.1, 2.7, 1.5, 3.4, 0.5, 0.26)
    out += iso.tbox(9.1, 2.7, -0.35, 1.5, 3.4, 0.42, WHITE, FJORD_D, 0.5)
    out += iso.box(9.1, 2.7, -0.1, 1.5, 3.4, 0.09, (WHITE, FALU, FALU_D))
    out += iso.tbox(9.55, 3.3, 0.07, 0.7, 1.2, 0.4, FJORD_P, FJORD_D, 0.5)
    # vei
    out += iso.poly([(4.35, -5.95, 0), (6.1, -5.95, 0), (6.1, 18, 0), (4.35, 18, 0)], ASPHALT)
    out += iso.poly([(-9, -5.95, 0), (6.1, -5.95, 0), (6.1, -4.2, 0), (-9, -4.2, 0)], ASPHALT)
    out += iso.line((5.23, -5.1, 0), (5.23, 18, 0), "#E7EFF1", 1.2, "5 6")
    out += iso.line((-9, -5.07, 0), (5.23, -5.07, 0), "#E7EFF1", 1.2, "5 6")
    for yy in (-0.5, -2.85):
        out += iso.line((4.35, yy, 0), (6.1, yy, 0), WHITE, 2.4)
    # trær
    for (a, b, h) in [(-1.8, -1.2, 1.5), (-1.3, 2.0, 1.6), (-2.4, 4.4, 1.5), (0.2, -2.6, 1.6), (2.2, -3.0, 1.4), (3.5, -1.5, 1.5), (1.6, -1.5, 1.2), (6.5, -3.0, 1.1), (6.5, 7.5, 1.1)]:
        out += spruce(iso, a, b, h)
    h, dx, dy = hall_cut(iso, 0, 0, 3, 4, lager, "Grossist", tally, "Grossist", name, 18)
    out += h
    gate_y = dy * 0.34
    out += iso.poly([(dx, gate_y, 0.01), (4.35, gate_y, 0.01), (4.35, dy * 0.66, 0.01), (dx, dy * 0.66, 0.01)], "#6E8290")

    # kø ved porten
    q = split_vans(rest)
    qparts = ""
    for i, owed in enumerate(q[:5]):
        qparts += van(iso, 5.3, 3.1 + i * 1.66, "-y", 0, owed, FALU, tally)
    out += qparts

    # bein A: de to nærmeste ukene. bein B: tre uker, langs baksiden.
    a_part = ""
    b_part = ""
    if slots.get(1):
        for i, n in enumerate(split_vans(slots[1])):
            a_part += van(iso, 4.5 if i == 0 else 5.3, SLOT_Y[1], "+y", n, 0, FJORD, tally)
    if slots.get(2):
        for i, n in enumerate(split_vans(slots[2])):
            a_part += van(iso, 4.5 if i == 0 else 5.3, SLOT_Y[2], "+y", n, 0, FJORD, tally)
    if slots.get(3):
        v = split_vans(slots[3])
        spots = [(2.55, -5.0), (0.95, -5.0), (-0.65, -5.0), (2.55, -5.82), (0.95, -5.82), (-0.65, -5.82)]
        for i in sorted(range(len(v)), key=lambda i: spots[i][0] + spots[i][1]):
            b_part += van(iso, spots[i][0], spots[i][1], "+x", v[i], 0, FJORD, tally)
    if motion:
        def anim(vx, vy, body):
            return G(
                f'<animateTransform attributeName="transform" type="translate" dur="5s" repeatCount="indefinite" '
                f'values="{vx:.0f} {vy:.0f};0 0;0 0" keyTimes="0;0.4;1" calcMode="spline" keySplines="0.16 1 0.3 1;0 0 1 1"/>'
                + body
            )
        a_part = anim(2.35 * iso.u, -2.35 * iso.u / 2, a_part)
        b_part = anim(-1.6 * iso.u, -0.8 * iso.u, b_part)
    out += b_part + a_part

    if gate_van:
        out += van(iso, 4.5, 1.72, "+y", gate_van, 0, FJORD, None)
    if courier_at is not None:
        cx, cy = courier_at
        out += courier(iso, cx, cy)
        if courier_label:
            px, py = iso.p(cx + 0.2, cy + 0.2, 1.0)
            out += plate(px, py - 14, courier_label, 13, WHITE, INK, pole=10)

    # tåke i begge ender
    out += fog(pg, [(150, 4, 175, 46, 1), (40, 0, 90, 34, 0.96), (258, 8, 70, 28, 0.9), (W + 2, 34, 36, 50, 0.9),
                    (-10, H + 6, 80, 46, 0.97), (70, H + 22, 70, 22, 0.85)])
    if signs:
        out += plate(*_at(iso, 6.5, 0.5, -14), f"1 uke: {slots.get(1, 0)}", 13, WHITE, INK, w=66, pole=14)
        gx, gy = _at(iso, 6.2, -1.7, -14)
        out += plate(min(gx, W - 38), gy, f"2 uker: {slots.get(2, 0)}", 13, WHITE, INK, w=70, pole=14)
        out += plate(W - 46, 24, f"3 uker: {slots.get(3, 0)}", 13, WHITE, INK, w=76)
        if rest:
            out += plate(58, 240, f"Restordre {rest}", 13, FALU, WHITE, w=102, stroke=FALU_D)
        px, py = iso.p(2.05, 2.5, 0.2)
        out += plate(px, py - 6, f"Lager {lager}", 13, INK, WHITE, w=66)
    if extra_plate:
        out += extra_plate(iso)
    return f'<g clip-path="{clip}">{out}</g>', tally


def _at(iso, x, y, dy=0):
    px, py = iso.p(x, y, 0)
    return px, py + dy


def road_view(pg, statuses, H=346, W=390, courier_at=None, courier_label=None, signs=True):
    """Kameraet trekker seg ut: fire lukkede bygg langs en svingete kystvei. Tak på, naboenes lager er skjult."""
    clip = pg.clip(0, 0, W, H)
    out = R(0, 0, W, H, 0, GRASS)
    for (a, b, c, d) in [(90, 70, 90, 26), (300, 120, 80, 26), (70, 240, 70, 24)]:
        out += f'<ellipse cx="{a}" cy="{b}" rx="{c}" ry="{d}" fill="{GRASS_D}" opacity=".5"/>'
    # fjord nede til høyre
    out += f'<polygon points="{W},214 {W},{H} 196,{H}" fill="{FJORD}"/>'
    out += f'<polygon points="{W},214 {W},232 232,{H} 196,{H}" fill="{FJORD_L}"/>'
    out += L(W, 214, 196, H + 3, CONCRETE, 5)
    # svingete vei i 2:1
    pts = [(-30, 336), (300, 171), (120, 81), (420, -69)]
    d = "M" + " L".join(f"{a} {b}" for a, b in pts)
    out += PATH(d, stroke=ASPHALT, sw=19)
    out += PATH(d, stroke="#E7EFF1", sw=1.1, dash="5 6")
    u = 14
    anchors = {"Fabrikk": (52, 24), "Distributør": (276, 58), "Grossist": (66, 158), "Detaljist": (156, 270)}
    for a, b, h in [(18, 110, 1.4), (190, 12, 1.2), (350, 150, 1.3), (22, 215, 1.5), (250, 134, 1.1), (196, 150, 1.3), (345, 14, 1.2), (120, 215, 1.1), (64, 306, 1.3)]:
        iso_t = Iso(pg, a, b, u)
        out += spruce(iso_t, 0, 0, h)
    st = {r[0]: r for r in statuses}
    for role in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        ax, ay = anchors[role]
        out += BUILD[role](Iso(pg, ax, ay, u), 0, 0, st[role][3])
    if courier_at is not None:
        cx, cy = courier_at
        out += courier(Iso(pg, cx, cy, u), 0, 0)
    out += fog(pg, [(W + 10, -6, 90, 40, 0.92), (-20, H + 10, 70, 30, 0.85)])
    if signs:
        pos = {"Fabrikk": (178, 12), "Distributør": (316, 112), "Grossist": (130, 178), "Detaljist": (306, 290)}
        for role in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
            px, py = pos[role]
            s = st[role]
            w = 138
            out += R(px - w / 2, py + 1.5, w, 42, 6, "#062430", op=0.22)
            out += R(px - w / 2, py, w, 42, 6, WHITE, INK, 0.8)
            out += role_icon(role, px - w / 2 + 6, py + 4, 15)
            out += T(px - w / 2 + 25, py + 16, role, 13, 800, INK)
            if s[3]:
                out += ic("check", px - w / 2 + 7, py + 23, 13, FURU, 2.4)
                out += T(px - w / 2 + 25, py + 35, f"{s[1]}: bestilt", 13, 700, MUTED)
            else:
                short = "din tur" if s[1] == "Sara" else s[2].replace("Venter ", "")
                out += ic("clock", px - w / 2 + 7, py + 23, 13, FALU, 1.9)
                out += T(px - w / 2 + 25, py + 35, f"{s[1]}: {short}", 13, 800, FALU)
            if s[4]:
                out += ki_badge(px + w / 2 - 22, py - 11, None, 20)
    if courier_at is not None and courier_label:
        cx, cy = courier_at
        out += plate(cx + 72, cy + 1, courier_label, 13, OKER_L, INK, w=68, stroke=OKER_D)
    return f'<g clip-path="{clip}">{out}</g>'


def header(week, cost, role="Grossist", spill=17, sub=None):
    out = status_row()
    out += T(20, 62, f"Uke {week}", 36, 800, WHITE, "b")
    out += role_icon(role, 128, 40, 19, WHITE)
    out += T(151, 49, role, 14, 800, WHITE)
    out += T(151, 67, sub or f"Spill {spill}", 13, 700, FJORD_P)
    out += T(370, 44, "Totalkostnad", 13, 700, FJORD_P, "n", "end")
    out += T(370, 69, kr(cost), 24, 800, WHITE, "b", "end", num=True)
    return out


def numbers(y, s, w=390, x=0):
    """Fast tallrad. Teller nøyaktig det dioramaet viser."""
    h1, h2 = 64, 62
    out = R(x, y, w, h1 + h2, 0, WHITE)
    col = w / 3
    big = [("Lager", s["lager"], "crate", INK), ("Restordre", s["restordre"], "owed", FALU), ("På vei", s["paa_vei_foer_ordre"], "van", INK)]
    for i, (lab, v, icon, c) in enumerate(big):
        cx = x + 14 + i * col
        if icon == "crate":
            out += ic_crate(cx, y + 9, 15)
        elif icon == "owed":
            out += ic_van(cx - 1, y + 10, 22, dashed=True)
        else:
            out += ic_van(cx - 1, y + 10, 22)
        tx = cx + (19 if icon == "crate" else 25)
        out += T(tx, y + 21, lab, 13, 800, MUTED)
        out += T(cx, y + 57, v, 36, 800, c, "b", num=True)
        if i:
            out += L(x + i * col, y + 8, x + i * col, y + h1 - 6, LINE, 1)
    out += L(x + 12, y + h1, x + w - 12, y + h1, LINE, 1)
    widths = [0.27, 0.23, 0.26, 0.24]
    small = [(["Innkommende", "ordre"], s["innkommende_ordre"]), (["Levering", "inn"], s["levering"]),
             (["Sendt", "denne uka"], s["sendt"]), (["Neste", "levering"], s["neste_levering"])]
    cur = x
    for i, (lab, v) in enumerate(small):
        cw = widths[i] * w
        out += T(cur + 9, y + h1 + 19, lab[0], 13, 700, MUTED)
        out += T(cur + 9, y + h1 + 34, lab[1], 13, 700, MUTED)
        out += T(cur + cw - 9, y + h1 + 56, v, 24, 800, INK, "b", "end", num=True)
        if i:
            out += L(cur, y + h1 + 6, cur, y + h1 + h2 - 6, LINE, 1)
        cur += cw
    return out


def history(y, week, w=390, x=0, label="Dine ordre fra uke 1"):
    vals = [WEEKS[i]["seats"]["Grossist"]["ordre"] for i in range(1, week)]
    out = R(x, y, w, 56, 0, PAPER)
    out += T(x + 12, y + 18, label, 13, 800, MUTED)
    out += T(x + w - 12, y + 18, "Demodata", 13, 700, MUTED, "n", "end")
    n = max(len(vals), 1)
    gap = 3
    sw = min(32.0, (w - 24 - gap * (n - 1)) / n)
    for i, v in enumerate(vals):
        px = x + 12 + i * (sw + gap)
        big = v > 4
        out += R(px, y + 25, sw, 24, 3, OKER_L if big else WHITE, OKER_D if big else LINE, 1)
        out += T(px + sw / 2, y + 42, v, 14, 800, INK, "b", "middle", num=True)
    return out


class IsoMini(Iso):
    """Mini-isometri uten blur, til små fasader i ventelista."""

    def __init__(self, x, y, u):
        class _P:
            def url(self, n):
                return "none"

        super().__init__(_P(), x, y, u)

    def shadow(self, *a, **k):
        return ""


def mini_building(role, x, y, u=6.5, lit=True):
    return BUILD[role](IsoMini(x, y, u), 0, 0, lit)


STATUS_11 = [
    ("Detaljist", "Ida", "Har bestilt", True, False),
    ("Grossist", "Sara", "Venter: deg", False, False),
    ("Distributør", "Mikkel", "Har bestilt", True, False),
    ("Fabrikk", "Jonas", "Venter 3 min", False, False),
]
STATUS_11_DONE = [
    ("Detaljist", "Ida", "Har bestilt", True, False),
    ("Grossist", "Sara", "Har bestilt", True, False),
    ("Distributør", "Mikkel", "Har bestilt", True, False),
    ("Fabrikk", "Jonas", "Venter 3 min", False, False),
]


def waiting(y, statuses, w=390, x=0, h=106, title=None):
    """Hvem Uka venter på. Tente vinduer = har bestilt, og teksten sier det samme."""
    out = R(x, y, w, h, 0, FJORD_D)
    wait = [s for s in statuses if not s[3]]
    if title is None:
        parts = []
        for s in wait:
            if s[1] == "Sara":
                parts.append("deg")
            else:
                parts.append(f"{s[1]} ({s[2].replace('Venter ', '')})")
        title = "Uka venter på " + " og ".join(parts) if parts else "Alle har bestilt"
    out += T(x + 12, y + 18, title, 14, 800, WHITE)
    col = w / 4
    for i, (role, name, state, done, ki) in enumerate(statuses):
        cx = x + i * col
        if i:
            out += L(cx, y + 28, cx, y + h - 8, "#2A7686", 1)
        offs = {"Detaljist": (15, 32), "Grossist": (14, 33), "Distributør": (15, 35), "Fabrikk": (14, 34)}[role]
        mx, my = cx + 40 + offs[0] - 14, y + offs[1] - 2
        out += mini_building(role, mx, my, 6.0, done)
        ty = y + 72
        out += T(cx + 7, ty, name if not ki else name, 13, 800, WHITE)
        out += T(cx + 7, ty + 15, "" if False else role, 13, 600, FJORD_P)
        # lite statusmerke oppe til venstre i kolonnen
        if done:
            out += ic("check", cx + 7, y + 34, 15, OKER_L, 2.4)
        else:
            out += ic("clock", cx + 7, y + 34, 15, WHITE, 1.9)
        if ki:
            out += ki_badge(cx + 7, y + 30, None, 16)
    return out


def order_panel(y, typed, s, mode="decide", w=390, x=0, h=None):
    """Tallfelt og stor knapp. To bil-rader gjør 24 mot 16 synlig uten regning."""
    out = R(x, y, w, h or (844 - y), 0, WHITE)
    pv = s["paa_vei_foer_ordre"]
    vx = x + 92
    out += T(x + 12, y + 19, f"På vei {pv}", 13, 800, INK)
    for i, _ in enumerate(split_vans(pv)):
        if i < 11:
            out += ic_van(vx + i * 26, y + 7, 23)
    fy = y + 50
    if mode == "decide":
        out += T(x + 12, y + 40, f"Ny ordre {typed}", 13, 800, FALU)
        for i, _ in enumerate(split_vans(int(typed))):
            out += ic_van(vx + i * 26, y + 28, 23, dashed=True)
        out += R(x + 12, fy, 92, 58, 10, WHITE, INK, 2.4)
        out += T(x + 58, fy + 45, typed, 44, 800, INK, "b", "middle", num=True)
        out += R(x + 114, fy + 3, w - 126, 58, 12, FALU_D)
        out += R(x + 114, fy, w - 126, 58, 12, FALU)
        out += T(x + 114 + (w - 126) / 2, fy + 37, f"Send ordre på {typed}", 22, 800, WHITE, "b", "middle")
    elif mode == "open":
        out += T(x + 12, y + 40, "Ny ordre", 13, 800, MUTED)
        out += T(vx, y + 40, "Tast et tall. Du bestemmer, systemet regner.", 13, 600, MUTED)
        out += R(x + 12, fy, 92, 58, 10, WHITE, FJORD, 2.4)
        out += L(x + 58, fy + 14, x + 58, fy + 44, FJORD, 2.4)
        out += R(x + 114, fy, w - 126, 58, 12, "#DCE7EA")
        out += T(x + 114 + (w - 126) / 2, fy + 37, "Send ordre", 22, 800, "#4A6570", "b", "middle")
    elif mode == "sent":
        out += T(x + 12, y + 40, f"Din ordre {typed}", 13, 800, FJORD)
        for i, _ in enumerate(split_vans(int(typed))):
            out += ic_van(vx + i * 26, y + 28, 23, dashed=True)
        out += R(x + 12, fy, w - 24, 58, 12, FJORD_P)
        out += ic("lock", x + 25, fy + 20, 18, FJORD_D)
        out += T(x + 52, fy + 26, f"Ordre på {typed} er sendt", 17, 800, INK, "b")
        out += T(x + 52, fy + 45, "Kan ikke endres. Uka går når alle har bestilt.", 13, 700, MUTED)
    return out


def game_screen(pg, week=11, typed="24", mode="decide", statuses=None, tally=None, slots=None, **dio):
    s = WEEKS[week]["seats"]["Grossist"]
    tally = tally or Tally()
    d, tally = diorama(pg, s["lager"], s["restordre"], slots or slots_for(week), tally, **dio)
    out = header(week, s["kost_sum"])
    out += G(d, "translate(0 84)")
    y = 84 + H_SCENE
    out += numbers(y, s)
    y += 126
    out += history(y, week)
    y += 56
    out += waiting(y, statuses or STATUS_11)
    y += 106
    out += order_panel(y, typed, s, mode)
    return out, tally


# ---------- Landskapet når tåka letter ----------
def site(iso, x, y, role, lager, rest, tally, label=True):
    """Åpen hall med kasser + parkeringsplass med ventende biler. Rutene følger Rollene."""
    out = ""
    h, dx, dy = hall_cut(iso, x, y, 3, 5, lager, role, tally, role if label else None, None, max(13, iso.u * 0.95))
    # gårdsplass
    px0, py0 = x + dx + 0.15, y - 0.2
    vans = split_vans(rest)
    lanes = max(1, (len(vans) + 3) // 4) if vans else 0
    yard_w = max(1, lanes) * 0.86 + 0.2
    if vans:
        out += iso.poly([(px0, py0, 0), (px0 + yard_w + 0.1, py0, 0), (px0 + yard_w + 0.1, y + dy + 0.5, 0), (px0, y + dy + 0.5, 0)], "#9AAFBA", "#6E8290", 0.5)
    out += h
    for i, owed in enumerate(vans):
        lane = i // 4
        pos = i % 4
        out += van(iso, px0 + 0.1 + lane * 0.86, py0 + 0.14 + pos * 1.62, "-y", 0, owed, FALU, tally)
    return out, dx, dy


def landscape(pg, x, y, w, h, week, u=15, tally=None, plates=True):
    """Hele kjeden uke for uke. Fire haller, sikksakkvei, og ingen tåke mellom."""
    tally = tally or Tally()
    clip = pg.clip(x, y, w, h)
    data = WEEKS[week]["seats"]
    iso = Iso(pg, x + 30 + 7.5 * u, y + h * 0.56, u)
    out = R(x, y, w, h, 0, GRASS)
    # fjordkant nederst
    out += f'<path d="M{x} {y + h - 34} Q{x + w * 0.35} {y + h - 64} {x + w * 0.6} {y + h - 24} T{x + w} {y + h - 50} V{y + h} H{x} Z" fill="{FJORD}"/>'
    spots = [("Detaljist", 0, 0), ("Grossist", 0, -16), ("Distributør", 16, -16), ("Fabrikk", 16, -32)]
    pts = []
    pts.append(iso.p(2, 20))
    pts.append(iso.p(2, -7.4))
    pts.append(iso.p(18, -7.4))
    pts.append(iso.p(18, -23.4))
    pts.append(iso.p(30, -23.4))
    # sikksakkvei med bredde
    road_d = "M" + " L".join(f"{p[0]:.1f} {p[1]:.1f}" for p in pts)
    out += PATH(road_d, stroke=ASPHALT, sw=u * 1.4, cap="round")
    out += PATH(road_d, stroke="#E7EFF1", sw=1.1, dash="5 6")
    for role, a, b in spots:
        s = data[role]
        part, dx, dy = site(iso, a, b, role, s["lager"], s["restordre"], tally, label=False)
        out += part
        if not plates:
            continue
        rx_, ry_ = iso.p(a, b, 1.6)
        pw_ = len(role) * 8 + 32
        out += R(rx_ - pw_ - 8, ry_ - 8, pw_, 24, 5, WHITE, INK, 0.8)
        out += role_icon(role, rx_ - pw_ - 3, ry_ - 5, 17)
        out += T(rx_ - pw_ + 18, ry_ + 9, role, 14, 800, INK)
        px, py = iso.p(a + 0.5, b + dy, 0)
        out += plate(px - 2, py + 10, f"Lager {s['lager']}", 13, INK, WHITE, w=66)
        if s["restordre"]:
            qx, qy = iso.p(a + dx + 1.3, b + dy + 0.6, 0)
            out += plate(qx + 18, qy + 8, f"Restordre {s['restordre']}", 13, FALU, WHITE, w=104, stroke=FALU_D)
    return f'<g clip-path="{clip}">{out}</g>', tally
