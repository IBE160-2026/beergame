"""Sidene utenom spillskjermene 05 og 06."""
from c04_lib import *
from c04_game import *

CHART = {"Detaljist": "#E09F1F", "Grossist": "#B3322A", "Distributør": "#1496BE", "Fabrikk": "#1B7A4B"}
GAMES = DATA["class_games"]


def topbar(pg, w, crumbs, right=None, h=64):
    out = R(0, 0, w, h, 0, FJORD)
    out += logo(28, 16, 28)
    out += T(170, h / 2 + 5, crumbs, 15, 700, FJORD_P)
    if right:
        out += T(w - 28, h / 2 + 5, right, 14, 700, FJORD_P, "n", "end")
    return out


def button(x, y, w, h, label, kind="primary", size=17, icon=None):
    if kind == "primary":
        out = R(x, y + 3, w, h, 10, FALU_D) + R(x, y, w, h, 10, FALU)
        fg = WHITE
    elif kind == "teal":
        out = R(x, y + 3, w, h, 10, FJORD_D) + R(x, y, w, h, 10, FJORD)
        fg = WHITE
    elif kind == "oker":
        out = R(x, y + 3, w, h, 10, OKER_D) + R(x, y, w, h, 10, OKER_L)
        fg = INK
    elif kind == "ghost-dark":
        out = R(x, y, w, h, 10, "none", WHITE, 2)
        fg = WHITE
    else:
        out = R(x, y, w, h, 10, WHITE, INK, 1.6)
        fg = INK
    tx = x + w / 2
    if icon:
        out += ic(icon, x + 12, y + h / 2 - 8, 16, fg, 2)
        tx += 10
    out += T(tx, y + h / 2 + size * 0.36, label, size, 800, fg, "b", "middle")
    return out


# ---------- Kvartalskartet ----------
STATUS_STYLE = {
    "ferdig": (GRASS_D, "#4C8F44", "Ferdig"),
    "pågår": (FJORD_L, FJORD, "Pågår"),
    "pauset": ("#E7EFF1", "#7E97A3", "Pauset"),
    "venter": (OKER_L, OKER_D, "Venter"),
    "hot": (FALU, FALU_D, "Nær KI"),
}


def block(iso, col, row, g, hot=False, numbers_on=True, size=13):
    x, y, s = col, row, 0.86
    st = "hot" if hot else g["status"]
    top, edge, _ = STATUS_STYLE[st]
    h = 0.16 if not hot else 0.34
    out = iso.box(x, y, 0, s, s, h, (top, mix(top, "#04202B", 0.14), mix(top, "#04202B", 0.3)), edge, 0.5)
    bx, by = x + 0.1, y + 0.08
    if st == "ferdig":
        out += iso.tbox(bx, by, h, 0.42, 0.34, 0.2, "#F4FBFC", "#4C8F44", 0.4)
    elif st == "pågår":
        out += iso.tbox(bx, by, h, 0.42, 0.34, 0.42, WHITE, FJORD_D, 0.4)
        out += iso.poly([(bx, by + 0.34, h + 0.42), (bx + 0.42, by + 0.34, h + 0.42), (bx + 0.42, by + 0.17, h + 0.6), (bx, by + 0.17, h + 0.6)], OKER, OKER_D, 0.4)
        out += iso.win_y(bx + 0.12, by + 0.34, h + 0.14, 0.18, 0.15, GLASS_LIT, FJORD_D)
    elif st == "pauset":
        for off in (0.14, 0.42):
            out += iso.tbox(x + off, y + 0.18, h, 0.16, 0.16, 0.6, "#5E7884", INK, 0.4)
    elif st in ("venter", "hot"):
        out += iso.tbox(bx, by, h, 0.42, 0.34, 0.42, WHITE if st == "venter" else "#FBE5E2", INK, 0.4)
        out += iso.win_y(bx + 0.12, by + 0.34, h + 0.14, 0.18, 0.15, GLASS_DARK, INK)
        px, py = iso.p(x + 0.56, y + 0.1, h)
        tall = iso.u * (1.2 if hot else 0.8)
        out += L(px, py, px, py - tall, INK, 1.6)
        c = FALU if hot else OKER_D
        out += f'<polygon points="{px:.1f},{py - tall:.1f} {px + iso.u * 0.42:.1f},{py - tall + iso.u * 0.12:.1f} {px:.1f},{py - tall + iso.u * 0.26:.1f}" fill="{c}" stroke="{INK}" stroke-width=".6"/>'
    if g.get("ki_seter"):
        px, py = iso.p(x + 0.1, y + 0.72, h)
        r = iso.u * 0.12
        out += f'<polygon points="{px - r:.1f},{py:.1f} {px - r / 2:.1f},{py - r * 0.86:.1f} {px + r / 2:.1f},{py - r * 0.86:.1f} {px + r:.1f},{py:.1f} {px + r / 2:.1f},{py + r * 0.86:.1f} {px - r / 2:.1f},{py + r * 0.86:.1f}" fill="{VIOLET}" stroke="#fff" stroke-width=".7"/>'
    if numbers_on:
        px, py = iso.p(x + 0.64, y + 0.66, h)
        fill = WHITE if hot else INK
        out += T(px, py + size * 0.36, g["spill"], size, 800, fill, "b", "middle", num=True)
    return out


def block_map(iso, numbers_on=True, size=13):
    out = ""
    for g in GAMES:
        n = g["spill"] - 1
        col, row = n % 10, n // 10
        out += block(iso, col, row, g, g["spill"] == 2, False, size)
    if numbers_on:
        for g in GAMES:
            n = g["spill"] - 1
            col, row = n % 10, n // 10
            hot = g["spill"] == 2
            h = 0.34 if hot else 0.16
            px, py = iso.p(col + 0.64, row + 0.66, h)
            halo = FALU_D if hot else WHITE
            out += T(px, py + size * 0.36, g["spill"], size, 800, WHITE if hot else INK, "b", "middle",
                     extra=f'paint-order="stroke" stroke="{halo}" stroke-width="3" stroke-linejoin="round"', num=True)
    return out


def status_legend_icon(st, x, y, s=16):
    top, edge, _ = STATUS_STYLE[st]
    iso = IsoMini(x + s / 2, y + 3, s * 0.48)
    g = {"status": "venter" if st == "hot" else st, "spill": ""}
    return block(iso, 0, 0, g, st == "hot", False)


# ---------- 01 Landing ----------
def page_01():
    pg = Page("01-landing.svg", "land", 1440, 1200, "Kjeden: landingsside for faglærere",
              "En håndlaget modell av en kystby der fire bygg utgjør en forsyningskjede. Viser mekanismen: Lager er kasser på gulvet, På vei er biler på veien, tåka skjuler naboene.", FJORD)
    iso = Iso(pg, 860, 462, 26)
    # bølger på bordet
    w = iso
    out = ""
    for i in range(46):
        a = (i * 73) % 1440
        b = 80 + (i * 137) % 620
        if a < 560 and b < 660:
            continue
        out += PATH(f"M{a} {b} q7 -5 14 0 t14 0", stroke=mix(FJORD_L, "#FFFFFF", 0.3), sw=1.2, op=0.4)
    # sokkel
    x0, x1, y0, y1 = -7, 5.2, -24, 4
    out += iso.poly([(x0 + 0.9, y1 + 0.9, -1), (x1 + 0.9, y1 + 0.9, -1), (x1 + 0.9, y0, -1), (x0 + 0.9, y0, -1)], "#04323D", op=0.35, extra=f'filter="{pg.url("fog")}"')
    out += iso.box(x0, y0, -0.85, x1 - x0, y1 - y0, 0.85, (GRASS, "#7A5A33", "#5F4526"), "#2F2412", 0.6)
    for (a, b, c, d) in [(900, 300, 160, 40), (1180, 300, 130, 34), (760, 430, 110, 30), (1020, 470, 120, 26)]:
        out += f'<ellipse cx="{a}" cy="{b}" rx="{c}" ry="{d}" fill="{GRASS_D}" opacity=".5"/>'
    # kai og vei
    out += iso.poly([(4.4, y0, 0), (x1, y0, 0), (x1, y1, 0), (4.4, y1, 0)], CONCRETE)
    out += iso.poly([(1.9, y0, 0), (3.6, y0, 0), (3.6, y1, 0), (1.9, y1, 0)], ASPHALT)
    out += iso.line((2.75, y0, 0), (2.75, y1, 0), "#E7EFF1", 1.4, "7 8")
    for yy in (-9.4, -12.4):
        out += iso.line((1.9, yy, 0), (3.6, yy, 0), WHITE, 2.6)
    # fergerampe og ferge
    out += iso.tbox(x1, -1.6, -0.1, 1.6, 1.3, 0.1, "#9FB2B9")
    out += iso.shadow(x1 + 1.6, -3, 1.8, 4, 0.5, 0.3)
    out += iso.tbox(x1 + 1.6, -3, -0.5, 1.8, 4, 0.55, WHITE, FJORD_D, 0.6)
    out += iso.box(x1 + 1.6, -3, -0.2, 1.8, 4, 0.1, (WHITE, FALU, FALU_D))
    out += iso.tbox(x1 + 2.1, -2.4, 0.05, 0.8, 1.4, 0.5, FJORD_P, FJORD_D, 0.6)
    # trær og bygg, bakerst først
    tr = Tally()
    items = []
    for a, b, h in [(-5.5, -22, 1.6), (-3.5, -23, 1.3), (-6, -18.4, 1.5), (-5.8, -14, 1.8), (-6.2, -11, 1.5), (-4.6, -11.6, 1.2), (-6.3, -7.5, 1.7), (-5.2, -5.2, 1.5), (-6.3, -3, 1.6),
                    (-4.4, -9.5, 1.3), (-5.6, 0, 1.5), (-4.4, 2.2, 1.3), (0.8, -10.5, 1.4), (0.9, -13, 1.2), (1.0, 2.8, 1.3), (-2.6, 2.6, 1.2), (3.9, -18, 1.1), (3.95, -4, 1.1), (3.95, -13, 1.2), (1.0, -19, 1.3)]:
        items.append((a + b, spruce(iso, a, b, h)))
    items.append((-27, b_fabrikk(iso, -3.4, -22)))
    items.append((-20.5, b_distributor(iso, -2.8, -16.8, True)))
    items.append((-1.5, b_detaljist(iso, -1.6, -1.2, True)))
    h, dx, dy = hall_cut(iso, -3.0, -8.2, 3, 4, 12, "Grossist", tr, "Grossist", None, 22)
    items.append((-11, h))
    for key, part in sorted(items, key=lambda t: t[0]):
        out += part
    out += iso.poly([(-3.0 + dx, -8.2 + dy * 0.34, 0.01), (1.9, -8.2 + dy * 0.34, 0.01), (1.9, -8.2 + dy * 0.66, 0.01), (-3.0 + dx, -8.2 + dy * 0.66, 0.01)], "#6E8290")
    # biler
    out += van(iso, 2.0, -11.8, "+y", 4, 0, FJORD, tr)
    out += van(iso, 2.0, -14.8, "+y", 4, 0, FJORD, tr)
    assert tr.full == 20
    # tåke over naboene
    out += fog(pg, [(1320, 110, 190, 70, 1), (1160, 150, 130, 60, 0.85), (1450, 210, 110, 60, 0.95), (1240, 220, 110, 40, 0.7), (1090, 90, 120, 40, 0.8)])
    pg.add(out)
    # KI-merke på butikkfasaden
    px, py = iso.p(-0.6, 0.3, 1.75)
    pg.add(ki_badge(px - 16, py - 8, None, 22))

    def callout(cx, cy, tx, ty, text, w):
        o = L(cx, cy, tx + w / 2 if ty > cy else tx + w / 2, ty, WHITE, 1.6)
        o += C(cx, cy, 4, WHITE, INK, 1.2)
        o += R(tx, ty + 2, w, 34, 8, "#062430", op=0.3)
        o += R(tx, ty, w, 34, 8, WHITE)
        o += T(tx + w / 2, ty + 22, text, 15, 800, INK, "n", "middle")
        return o

    hx, hy = iso.p(-1.5, -6.6, 0.6)
    vx, vy = iso.p(2.4, -13.8, 0.5)
    fx, fy = iso.p(-1.2, -14.8, 1.2)
    dx_, dy_ = iso.p(-0.8, -0.5, 0.6)
    pg.add(callout(hx, hy, 760, 610, "Lager: kassene på gulvet er tallet", 288))
    pg.add(callout(vx, vy, 1130, 430, "På vei: bilene du ser på veien", 262))
    pg.add(callout(fx, fy, 1120, 410, "Tåka: naboens tall er skjult", 244) if False else "")
    pg.add(R(1140, 112, 236, 34, 8, "#062430", op=0.3) + R(1140, 110, 236, 34, 8, WHITE) + T(1258, 132, "Tåka: naboens tall er skjult", 15, 800, INK, "n", "middle"))
    pg.add(callout(dx_ - 40, dy_ + 30, 570, 532, "KI-spiller i tomt sete, alltid merket", 288))

    # tekst
    pg.add(logo(64, 36, 34))
    y = 170
    for line in ["Fire seter.", "Ett tall i uka.", "Hele klassen", "på én skjerm."]:
        pg.add(T(64, y, line, 66, 800, WHITE, "b"))
        y += 68
    para, yy = P(64, y - 18, "Kjeden kjører hele øvelsen i forsyningskjeder for klasser på rundt 250 studenter, fra Invitasjon til PDF-rapport. Studentene spiller på mobil, på norsk. KI-spillere fyller tomme seter, og ett fravær stopper ikke gruppa.", 450, 18, 1.42, 600, WHITE)
    pg.add(para)
    by = yy + 8
    pg.add(button(64, by, 236, 58, "Be om lærertilgang", "oker", 21))
    pg.add(button(316, by, 124, 58, "Logg inn", "ghost-dark", 20))

    # seksjon 2
    sy = 690
    pg.add(f'<path d="M0 {sy + 34} Q240 {sy - 18} 520 {sy + 22} T1040 {sy + 8} T1440 {sy + 30} V1200 H0 Z" fill="{PAPER}"/>')
    pg.add(T(64, sy + 110, "Alle 60 spillene", 50, 800, INK, "b"))
    pg.add(T(64, sy + 162, "på ett kart.", 50, 800, INK, "b"))
    para2, y2 = P(64, sy + 206, "Hvert Klassespill er et lite kvartal. Du ser på sekunder hvilke som er ferdige, hvilke som går, og hvilket som venter på én student. Ingen spill blir stående uferdig: KI overtar før et sete holder de andre igjen.", 480, 18, 1.42, 600, MUTED)
    pg.add(para2)
    para3, y3 = P(64, y2 + 6, "Studentlisten lastes opp fra Canvas-eksport.", 480, 18, 1.42, 700, INK)
    pg.add(para3)
    # mini-kart
    m = Iso(pg, 830, sy + 78, 33)
    pg.add(m.poly([(-0.4, -0.4, -0.05), (10.3, -0.4, -0.05), (10.3, 6.3, -0.05), (-0.4, 6.3, -0.05)], FJORD_P))
    pg.add(block_map(m, True, 13))
    px, py = m.p(1.5, 0, 0.5)
    pg.add(L(px, py - 20, px + 52, py - 62, FALU, 1.6))
    pg.add(R(px + 40, py - 90, 262, 30, 8, FALU))
    pg.add(T(px + 171, py - 70, "Spill 2 venter på Noah i 23 t", 15, 800, WHITE, "n", "middle"))
    pg.add(T(1376, sy + 110, "Demodata", 14, 700, MUTED, "n", "end"))
    # veien fra invitasjon til rapport
    ry = 1128
    pg.add(T(64, ry - 42, "Hele øvelsen, fra Invitasjon til PDF-rapport.", 26, 800, INK, "b"))
    stations = ["Invitasjon", "Klassespill", "Debrief", "Replay", "Individuell test", "PDF-rapport"]
    d = f"M3 {ry + 64}"
    xc, yc, up = 3, ry + 64, True
    while xc < 1460:
        xc += 118
        yc += -59 if up else 59
        d += f" L{xc} {yc}"
        up = not up
    pg.add(PATH(d, stroke=ASPHALT, sw=22))
    pg.add(PATH(d, stroke="#E7EFF1", sw=1.3, dash="6 7"))
    for i, nm in enumerate(stations):
        cx = 121 + i * 236
        cy = ry - 1
        w = len(nm) * 9.6 + 22
        pg.add(L(cx, cy + 4, cx, cy + 12, "#37505B", 2.4))
        pg.add(R(cx - w / 2, cy - 22, w, 30, 6, WHITE, INK, 1))
        pg.add(T(cx, cy - 2, nm, 16, 800, INK, "n", "middle"))
    pg.write()


# ---------- 02 Klasse ----------
def field(x, y, w, label, value, h=44, hint=None):
    out = T(x, y, label, 14, 800, MUTED)
    out += R(x, y + 8, w, h, 8, WHITE, "#7E97A3", 1.2)
    out += T(x + 14, y + 8 + h / 2 + 6, value, 17, 700, INK)
    if hint:
        out += T(x + w, y, hint, 13, 600, MUTED, "n", "end")
    return out


def page_02():
    pg = Page("02-laerer-klasse.svg", "klas", 1440, 1000, "Kjeden: faglærer lager Klasse",
              "Navn og emnekode, Canvas-fil, e-postkolonne, ugyldige rader, Invitasjoner og status. 250 kasser på gulvet er 250 rader.", PAPER)
    pg.add(topbar(pg, 1440, "Klasser  /  Ny Klasse", "Bård, faglærer"))
    pg.add(T(40, 118, "Ny Klasse", 40, 800, INK, "b"))
    pg.add(T(1400, 112, "Demodata", 14, 700, MUTED, "n", "end"))
    # venstre kolonne
    x = 40
    pg.add(field(x, 158, 400, "Navn", "class-of-1994"))
    pg.add(field(x + 420, 158, 200, "Emnekode", "IBE160"))
    # fil
    y = 248
    pg.add(T(x, y, "Klasseliste fra Canvas", 14, 800, MUTED))
    pg.add(R(x, y + 8, 620, 58, 8, FJORD_P, FJORD, 1.2))
    pg.add(ic("doc", x + 14, y + 26, 22, FJORD_D, 1.7))
    pg.add(T(x + 48, y + 32, "ibe160-canvas-eksport.xlsx", 16, 800, INK))
    pg.add(T(x + 48, y + 53, "250 rader lest", 14, 700, MUTED))
    pg.add(button(x + 470, y + 18, 136, 38, "Bytt fil", "ghost", 15, "upload"))
    # kolonnevalg
    y = 346
    pg.add(T(x, y, "Hvilken kolonne er e-post?", 14, 800, MUTED))
    cols = [("Navn", ["Sara Nilsen", "Ida Holm", "Mikkel Berg"], 170, False), ("SIS-bruker", ["sn4412", "ih2219", "mb7730"], 110, False),
            ("E-post", ["sara.nilsen@student.no", "ida.holm@student.no", "mikkel.berg@student.no"], 240, True), ("Seksjon", ["IBE160-1", "IBE160-1", "IBE160-2"], 100, False)]
    cx = x
    for name, vals, w, sel in cols:
        if sel:
            pg.add(R(cx, y + 8, w, 128, 8, mix(OKER_L, "#FFFFFF", 0.55), OKER_D, 2))
            pg.add(ic("check", cx + w - 26, y + 16, 16, OKER_D, 2.4))
        else:
            pg.add(R(cx, y + 8, w, 128, 8, WHITE, LINE, 1))
        pg.add(T(cx + 10, y + 30, name, 15, 800, INK))
        pg.add(L(cx + 8, y + 40, cx + w - 8, y + 40, LINE, 1))
        for i, v in enumerate(vals):
            pg.add(T(cx + 10, y + 62 + i * 26, v, 14, 600, MUTED))
        cx += w
    # ugyldige rader
    y = 524
    pg.add(ic("warn", x, y - 14, 18, FALU, 1.9))
    pg.add(T(x + 26, y, "4 ugyldige adresser", 22, 800, INK, "b"))
    pg.add(T(x + 620, y, "Rett raden, eller registrer manuelt", 14, 600, MUTED, "n", "end"))
    rows = [(37, "Jonas Lie", "jonas.lie@student", "Mangler domene", "Ugyldig"), (88, "Emma Dahl", "emma.dahl.student.no", "Mangler @", "Manuelt registrert"),
            (141, "Noah Moe", "noah moe@student.no", "Mellomrom i adressen", "Ugyldig"), (203, "Lea Aas", "(tom)", "Tom celle", "Manuelt registrert")]
    ty = y + 14
    heads = [(0, "Rad"), (50, "Navn"), (160, "Adresse i fila"), (335, "Problem"), (488, "Status")]
    for dx, h in heads:
        pg.add(T(x + 10 + dx, ty + 18, h, 13, 800, MUTED))
    pg.add(L(x, ty + 26, x + 620, ty + 26, INK, 1.2))
    for i, r in enumerate(rows):
        ry = ty + 26 + i * 36
        pg.add(T(x + 10, ry + 24, r[0], 15, 800, FALU, "b", num=True))
        pg.add(T(x + 60, ry + 24, r[1], 14, 700))
        pg.add(T(x + 170, ry + 24, r[2], 14, 600, MUTED))
        pg.add(T(x + 345, ry + 24, r[3], 14, 600))
        if r[4] == "Ugyldig":
            pg.add(ghost_box(x + 498, ry + 12, FALU))
            pg.add(T(x + 520, ry + 24, "Ugyldig", 14, 800, FALU))
        else:
            pg.add(ic("check", x + 498, ry + 12, 15, FJORD, 2.4))
            pg.add(T(x + 518, ry + 24, "Registrert", 14, 800, FJORD_D))
        pg.add(L(x, ry + 36, x + 620, ry + 36, LINE, 1))
    # send
    y = 756
    pg.add(button(x, y, 300, 58, "Send 246 Invitasjoner", "primary", 22, "letter"))
    pg.add(PS(x + 320, y + 22, "Invitasjonen er gyldig i 14 dager. De 4 ugyldige radene får ingen e-post før de er rettet.", 300, 14, 1.34, 600, MUTED))

    # høyre: hallen
    rx = 720
    pg.add(R(rx, 92, 680, 462, 14, FJORD))
    pg.add(T(rx + 24, 136, "250 kasser, 250 rader", 30, 800, WHITE, "b"))
    pg.add(T(rx + 24, 160, "Hver kasse er én student. Tell selv.", 15, 600, FJORD_P))
    iso = Iso(pg, rx + 196, 214, 28)
    cw, rw = 25, 10
    pit = 0.52
    w, d = cw * pit + 0.3, rw * pit + 0.3
    pg.add(iso.box(-0.15, -0.15, -0.3, w, d, 0.3, ("#E7EFF1", "#A9BEC5", "#8EA5B0"), "#5B717A", 0.5))
    pg.add(iso.poly([(-0.15, d - 0.15, 0), (-0.15, -0.15, 0), (-0.15, -0.15, 1.1), (-0.15, d - 0.15, 1.1)], FALU_D, "#5E1712", 0.5))
    pg.add(iso.poly([(-0.15, -0.15, 0), (w - 0.15, -0.15, 0), (w - 0.15, -0.15, 1.1), (-0.15, -0.15, 1.1)], FALU, "#5E1712", 0.5))
    pg.add(iso.poly([(-0.15, -0.15, 1.1), (w - 0.15, -0.15, 1.1), (w - 0.15, -0.15, 1.24), (-0.15, -0.15, 1.24)], OKER, OKER_D, 0.5))
    pg.add(iso.poly([(-0.15, d - 0.15, 1.1), (-0.15, -0.15, 1.1), (-0.15, -0.15, 1.24), (-0.15, d - 0.15, 1.24)], OKER_D, OKER_D, 0.5))
    pg.add(iso.wall_text("+x", 0.6, -0.15, 0.42, "Klasselista", 19, WHITE))
    plan = ["a"] * 238 + ["m"] * 2 + ["s"] * 6 + ["u"] * 2 + ["i"] * 2
    tally = Tally()
    counts = {"a": 0, "m": 0, "s": 0, "u": 0, "i": 0}
    k = 0
    parts = ""
    for r in range(rw):
        for c in range(cw):
            kind = plan[k]
            k += 1
            counts[kind] += 1
            px, py = c * pit, r * pit
            if kind == "a":
                parts += crate(iso, px, py, 0, 0.42, OKER, tally)
            elif kind == "m":
                parts += crate(iso, px, py, 0, 0.42, FJORD_L, tally)
            elif kind == "s":
                parts += ghost_crate(iso, px, py, 0, 0.42, FJORD_D, tally)
            elif kind == "u":
                parts += crate(iso, px, py, 0, 0.42, "#8EA5B0", tally)
            else:
                parts += ghost_crate(iso, px, py, 0, 0.42, FALU, tally)
    assert tally.full + tally.owed == 250
    pg.add(parts)
    # status
    y = 590
    pg.add(T(rx, y, "Status for Invitasjonene", 22, 800, INK, "b"))
    stat = [("Akseptert", 238, "a"), ("Manuelt registrert", 2, "m"), ("Sendt, venter", 6, "s"), ("Utløpt", 2, "u"), ("Ugyldig adresse", 2, "i")]
    sx = rx
    for label, n, kind in stat:
        pg.add(status_crate(sx, y + 16, kind))
        pg.add(T(sx + 26, y + 32, n, 26, 800, INK, "b", num=True))
        pg.add(T(sx, y + 56, label, 13, 700, MUTED))
        sx += 136
    # tabell
    ty = y + 70
    pg.add(L(rx, ty + 26, rx + 680, ty + 26, INK, 1.2))
    for dx, h in [(0, "Navn"), (180, "E-post"), (420, "Status"), (540, "Sendt"), (610, "Handling")]:
        pg.add(T(rx + 8 + dx, ty + 18, h, 13, 800, MUTED))
    sample = [("Sara Nilsen", "sara.nilsen@student.no", "Akseptert", "2. nov", ""), ("Oskar Vik", "oskar.vik@student.no", "Sendt, venter", "2. nov", "Purr"),
              ("Tuva Rud", "tuva.rud@student.no", "Sendt, venter", "2. nov", "Purr"), ("Elias Sand", "elias.sand@student.no", "Utløpt", "19. okt", "Send ny"),
              ("Nora Foss", "nora.foss@student.no", "Utløpt", "19. okt", "Send ny")]
    for i, r in enumerate(sample):
        ry = ty + 26 + i * 34
        pg.add(T(rx + 8, ry + 23, r[0], 14, 700))
        pg.add(T(rx + 188, ry + 23, r[1], 14, 600, MUTED))
        icon = {"Akseptert": ("check", FJORD), "Sendt, venter": ("clock", MUTED), "Utløpt": ("x", FALU)}[r[2]]
        pg.add(ic(icon[0], rx + 428, ry + 11, 14, icon[1], 2.2))
        pg.add(T(rx + 446, ry + 23, r[2].replace("Sendt, venter", "Sendt"), 14, 700))
        pg.add(T(rx + 548, ry + 23, r[3], 14, 600, MUTED))
        if r[4]:
            pg.add(T(rx + 618, ry + 23, r[4], 14, 800, FJORD, extra='text-decoration="underline"'))
        pg.add(L(rx, ry + 34, rx + 680, ry + 34, LINE, 1))
    pg.add(button(1110, 900, 290, 54, "Sett opp Klasseøkt", "teal", 20, "chev"))
    pg.add(T(1092, 934, "Du kan gjøre dette før alle har svart.", 15, 600, MUTED, "n", "end"))
    pg.add(T(40, 934, "Demodata", 14, 700, MUTED))
    pg.write()


def ghost_box(x, y, c):
    return R(x, y, 14, 14, 2, mix(c, "#FFFFFF", 0.85), c, 1.2, dash="2.5 2")


def status_crate(x, y, kind):
    if kind == "a":
        return ic_crate(x, y, 20)
    if kind == "m":
        return ic_crate(x, y, 20, FJORD_L)
    if kind == "u":
        return ic_crate(x, y, 20, "#8EA5B0")
    c = FJORD_D if kind == "s" else FALU
    return R(x + 1, y + 2, 17, 17, 3, mix(c, "#FFFFFF", 0.85), c, 1.4, dash="3 2.2")


# ---------- 03 Klasseøkt ----------
def page_03():
    pg = Page("03-laerer-spill.svg", "okt", 1440, 1100, "Kjeden: faglærer setter opp Klasseøkt",
              "Klassisk er forhåndsutfylt og kan lagres uten endring. Modellen viser forsinkelsene som veilengde, og fordelingen viser 240 studenter i 60 spill à 4.", PAPER)
    pg.add(topbar(pg, 1440, "class-of-1994  /  Ny Klasseøkt", "Demodata"))
    pg.add(T(40, 118, "Klasseøkt", 40, 800, INK, "b"))
    pg.add(T(40, 146, "Klassisk er ferdig utfylt. Du kan lagre uten å endre noe.", 16, 600, MUTED))
    # obligatorisk
    pg.add(R(1176, 88, 224, 44, 22, FJORD))
    pg.add(C(1200, 110, 13, WHITE))
    pg.add(ic("check", 1192, 102, 16, FJORD_D, 2.6))
    pg.add(T(1222, 116, "Obligatorisk: på", 16, 800, WHITE, "b"))

    x, w = 40, 640
    y = 176
    pg.add(T(x, y, "Spillinnstillinger", 22, 800, INK, "b"))
    pg.add(T(x + w, y, "Standard: Klassisk", 14, 700, MUTED, "n", "end"))
    rows = [("Startlager", "12", "kasser"), ("I hvert ledd", "4", "kasser"), ("Ordreforsinkelse", "2", "uker"), ("Fraktforsinkelse", "2", "uker"),
            ("Produksjonsforsinkelse", "2", "uker"), ("Etterspørsel", "4 til 8", "i uke 5"), ("Lagerkost", "0,50", "kr per kasse per uke"),
            ("Restordrekost", "1,00", "kr per kasse per uke"), ("Antall uker", "36", "uker"), ("Veiledede uker", "1–4", ""), ("Inaktivitetsgrense", "24", "timer")]
    y += 12
    pg.add(L(x, y, x + w, y, INK, 1.2))
    for i, (a, b, c) in enumerate(rows):
        ry = y + i * 32
        pg.add(T(x + 6, ry + 22, a, 15, 700))
        pg.add(R(x + 290, ry + 4, 84, 25, 5, WHITE, "#7E97A3", 1))
        pg.add(T(x + 366, ry + 22, b, 15, 800, INK, "b", "end", num=True))
        pg.add(T(x + 386, ry + 22, c, 14, 600, MUTED))
        pg.add(L(x, ry + 32, x + w, ry + 32, LINE, 1))
    yy = y + 11 * 32 + 10
    pg.add(ic("warn", x, yy, 16, OKER_D, 1.8))
    pg.add(PS(x + 24, yy + 13, "Kildene er uenige om forsinkelsene. Dette er produktets standard.", w - 24, 14, 1.3, 700, INK))
    # modus
    yy += 36
    def seg(px, py, label, a, b):
        o = T(px, py, label, 14, 800, MUTED)
        o += R(px, py + 8, 300, 40, 8, WHITE, "#7E97A3", 1.2)
        o += R(px + 2, py + 10, 148, 36, 7, INK)
        o += ic("check", px + 10, py + 20, 15, WHITE, 2.4)
        o += T(px + 86, py + 33, a, 14, 800, WHITE, "n", "middle")
        o += T(px + 225, py + 33, b, 14, 700, INK, "n", "middle")
        return o
    pg.add(seg(x, yy + 12, "KI-modus", "LLM-spillere", "Regelstyrte"))
    pg.add(seg(x + 330, yy + 12, "Debrief-modus", "Gruppedebrief", "Personlig"))

    # høyre: modellen
    rx, rw = 712, 688
    pg.add(R(rx, 88 + 56, rw, 262, 14, FJORD))
    pg.add(T(rx + 22, 88 + 88, "Slik ser forsinkelsene ut i modellen", 20, 800, WHITE, "b"))
    pg.add(T(rx + 22, 88 + 110, "Veilengden mellom byggene er ukene.", 14, 600, FJORD_P))
    clip = pg.clip(rx, 144, rw, 262, 14)
    iso = Iso(pg, rx + 110, 290, 15)
    sc = ""
    pts = [(rx - 20, 372), (rx + 170, 340), (rx + 340, 310), (rx + 510, 280), (rx + 700, 250)]
    # sokkel
    sc += f'<polygon points="{rx - 10},410 {rx + rw + 10},316 {rx + rw + 10},306 {rx - 10},400" fill="#7A5A33"/>'
    sc += f'<polygon points="{rx - 10},400 {rx + rw + 10},306 {rx + rw + 10},238 {rx - 10},326" fill="{GRASS}"/>'
    sc += PATH("M" + " L".join(f"{a} {b}" for a, b in [(rx - 10, 373), (rx + rw + 10, 279)]), stroke=ASPHALT, sw=16)
    sc += PATH("M" + " L".join(f"{a} {b}" for a, b in [(rx - 10, 373), (rx + rw + 10, 279)]), stroke="#E7EFF1", sw=1, dash="5 6")
    anchors = [("Detaljist", rx + 72, 300), ("Grossist", rx + 244, 278), ("Distributør", rx + 420, 252), ("Fabrikk", rx + 580, 232)]
    for a, b in [(rx + 40, 318), (rx + 196, 286), (rx + 372, 262), (rx + 540, 240), (rx + 670, 226)]:
        sc += spruce(Iso(pg, a, b, 15), 0, 0, 1.4)
    for role, a, b in anchors:
        sc += BUILD[role](Iso(pg, a, b, 15), 0, 0, True)
    pg.add(f'<g clip-path="{clip}">{sc}</g>')
    for i, (role, a, b) in enumerate(anchors):
        pg.add(role_icon(role, a - 34, b + 74 - 10 * i + 0, 16, WHITE) if False else "")
    labels = [(rx + 76, 382, "Detaljist"), (rx + 248, 360, "Grossist"), (rx + 424, 338, "Distributør"), (rx + 592, 316, "Fabrikk")]
    for a, b, s_ in labels:
        pg.add(plate(a, b, s_, 13, WHITE, INK, w=len(s_) * 7.6 + 12))
    for a, b, s_ in [(rx + 160, 246, "2 uker ordre"), (rx + 335, 224, "2 uker frakt"), (rx + 508, 200, "2 uker frakt"), (rx + 646, 196, "")]:
        if s_:
            pg.add(plate(a, b, s_, 13, OKER_L, INK, w=98, stroke=OKER_D))
    pg.add(plate(rx + 620, 168, "2 uker produksjon", 13, OKER_L, INK, w=132, stroke=OKER_D))

    # datoer
    y = 432
    pg.add(T(rx, y, "Datoer", 22, 800, INK, "b"))
    dates = [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]
    for i, (a, b) in enumerate(dates):
        ry = y + 12 + i * 32
        pg.add(ic("cal", rx, ry + 8, 16, FJORD_D, 1.6))
        pg.add(T(rx + 24, ry + 22, a, 15, 700))
        pg.add(T(rx + 320, ry + 22, b, 15, 800, INK, "n", "end"))
        pg.add(L(rx, ry + 32, rx + 320, ry + 32, LINE, 1))
    lx = rx + 356
    pg.add(T(lx, y, "Labtimer, Datalab A2", 22, 800, INK, "b"))
    for i, b in enumerate(["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]):
        ry = y + 12 + i * 32
        pg.add(ic("pin", lx, ry + 8, 16, FJORD_D, 1.6))
        pg.add(T(lx + 24, ry + 22, b, 15, 700))
        pg.add(L(lx, ry + 32, lx + 332, ry + 32, LINE, 1))
    pg.add(T(lx + 332, y + 12 + 4 * 32 + 24, "Legg til Labtime", 14, 800, FJORD, "n", "end", extra='text-decoration="underline"'))

    # fordeling
    fy = 690
    pg.add(R(0, fy, 1440, 410, 0, FJORD_D))
    pg.add(T(40, fy + 46, "Fordelingen", 28, 800, WHITE, "b"))
    pg.add(T(40, fy + 72, "240 studenter tilfeldig i 60 spill à 4. Ingen ser dette før du bekrefter.", 16, 600, FJORD_P))
    # 60 kvartaler à 4 hus
    gx, gy = 40, fy + 92
    cols = 15
    shapes = 0
    for n in range(60):
        cx = gx + (n % cols) * 50
        cy = gy + (n // cols) * 50
        pg.add(R(cx, cy, 44, 44, 5, FJORD, "#2A7686", 1))
        for j, role in enumerate(ROLES):
            pg.add(role_icon(role, cx + 3 + (j % 2) * 20, cy + 3 + (j // 2) * 20, 17, WHITE))
            shapes += 1
    assert shapes == 240
    pg.add(T(gx, gy + 222, "Hver rute er ett Klassespill med fire seter: Detaljist, Grossist, Distributør, Fabrikk.", 14, 700, FJORD_P))
    # eksempelrader
    tx = 810
    pg.add(T(tx, fy + 46, "Eksempel fra fordelingen", 20, 800, WHITE, "b"))
    heads = [(0, "Spill"), (60, "Detaljist"), (180, "Grossist"), (300, "Distributør"), (430, "Fabrikk")]
    ty = fy + 62
    for dx, h in heads:
        pg.add(T(tx + dx, ty + 16, h, 13, 800, FJORD_P))
    pg.add(L(tx, ty + 24, tx + 590, ty + 24, FJORD_P, 1))
    sample = [(1, "Emil", "Nora", "Tuva", "Elias"), (2, "Emma", "Noah", "Aksel", "Lea"), (17, "Ida", "Sara", "Mikkel", "Jonas"), (28, "Hedda", "Filip", "Mikkel B.", "Vilde"), (60, "Sofie", "Isak", "Maja", "Theo")]
    for i, r in enumerate(sample):
        ry = ty + 24 + i * 29
        pg.add(T(tx, ry + 20, r[0], 15, 800, WHITE, "b", num=True))
        for j, dx in enumerate([60, 180, 300, 430]):
            pg.add(T(tx + dx, ry + 20, r[j + 1], 15, 600, WHITE))
        pg.add(L(tx, ry + 29, tx + 590, ry + 29, "#2A7686", 1))
    by = fy + 244
    pg.add(button(tx, by, 170, 48, "Kjør på nytt", "ghost-dark", 17, "refresh"))
    pg.add(button(tx + 186, by, 240, 48, "Bekreft fordelingen", "oker", 18))
    # lagre
    pg.add(L(0, 1020, 1440, 1020, "#2A7686", 1))
    pg.add(T(40, 1068, "Du kan lagre nå og justere datoer og Labtimer senere.", 16, 600, FJORD_P))
    pg.add(button(1130, 1038, 270, 54, "Lagre Klasseøkt", "primary", 21))
    pg.write()


# ---------- 04 Student hjem ----------
def page_04():
    pg = Page("04-student-hjem.svg", "hjem", 1000, 900, "Kjeden: Sara på mobil",
              "Venstre telefon: Invitasjon og registrering. Høyre telefon: hjem under spill, spillet venter på Sara.", FJORD_D)
    # venstre
    a = status_row()
    a += logo(20, 40, 26)
    clip = pg.clip(0, 0, 390, 350)
    iso = Iso(pg, 170, 120, 26)
    s = R(0, 0, 390, 350, 0, GRASS)
    s += iso.poly([(7.8, -30, -0.35), (40, -30, -0.35), (40, 40, -0.35), (7.8, 40, -0.35)], FJORD)
    s += iso.poly([(7.8, -30, 0), (7.8, 40, 0), (7.8, 40, -0.35), (7.8, -30, -0.35)], "#8FA4AB")
    s += iso.poly([(3.6, -14, 0), (5.2, -14, 0), (5.2, 20, 0), (3.6, 20, 0)], ASPHALT)
    s += iso.line((4.4, -14, 0), (4.4, 20, 0), "#E7EFF1", 1.2, "5 6")
    for p, q, h in [(-1.4, -0.6, 1.5), (-1.8, 2.6, 1.6), (0.6, -2.4, 1.4), (2.6, -2.2, 1.3), (6.4, 1.2, 1.2), (6.2, -3, 1.2), (-0.5, 4.4, 1.4), (1.2, 1.6, 1.7), (2.2, 5.6, 1.3), (6.3, 5.4, 1.2)]:
        s += spruce(iso, p, q, h)
    s += pallet(iso, 1.6, -0.6, 4, 0.5)
    s += courier(iso, 3.8, 2.2)
    s += plate(226, 150, "Invitasjon til Sara", 13, WHITE, INK, w=130, pole=26)
    s += fog(pg, [(380, 30, 110, 80, 1), (-10, 330, 110, 60, 1), (70, 0, 110, 34, 0.95), (200, 0, 120, 26, 0.8)])
    a += G(f'<g clip-path="{clip}">{s}</g>', "translate(0 84)")
    y = 424
    a += R(0, y, 390, 844 - y, 0, WHITE)
    a += T(20, y + 40, "Bård har invitert deg", 28, 800, INK, "b")
    a += T(20, y + 64, "IBE160, Klasse class-of-1994", 15, 700, MUTED)
    fy = y + 88
    for i, (lab, val) in enumerate([("Navn", "Sara Nilsen"), ("E-post", "sara.nilsen@student.no"), ("Velg passord", "············")]):
        ry = fy + i * 68
        a += T(20, ry, lab, 14, 800, MUTED)
        a += R(20, ry + 7, 350, 46, 8, WHITE, "#7E97A3", 1.2)
        a += T(34, ry + 36, val, 16, 700, INK)
    ry = fy + 3 * 68 + 2
    a += button(20, ry, 350, 56, "Bli med i Klassen", "primary", 21)
    a += PS(20, ry + 78, "Invitasjonen er gyldig i 14 dager. Du får Rolle og gruppe når spillet starter.", 350, 14, 1.3, 600, MUTED)
    pg.add(T(50, 26, "Første møte", 15, 800, FJORD_P))
    pg.add(phone(pg, 50, 40, 1.0 * 0.97, a))

    # høyre
    b = status_row()
    b += T(20, 62, "Hei, Sara", 32, 800, WHITE, "b")
    b += role_icon("Grossist", 200, 42, 19, WHITE)
    b += T(224, 50, "Grossist", 14, 800, WHITE)
    b += T(224, 67, "Spill 17, IBE160", 13, 700, FJORD_P)
    clip2 = pg.clip(0, 0, 390, 240)
    iso = Iso(pg, 192, 74, 25)
    s = R(0, 0, 390, 240, 0, GRASS)
    s += iso.poly([(3.3, -14, 0), (4.7, -14, 0), (4.7, 18, 0), (3.3, 18, 0)], ASPHALT)
    s += iso.line((4, -14, 0), (4, 18, 0), "#E7EFF1", 1.2, "5 6")
    for p, q, h in [(-1.2, -0.8, 1.4), (-1.4, 2.4, 1.5), (0.8, -2.0, 1.2), (5.4, 1, 1.2)]:
        s += spruce(iso, p, q, h)
    s += b_grossist(iso, 0, 0, False)
    s += van(iso, 3.4, 3.4, "-y", 0, 4, FALU)
    s += van(iso, 3.4, -2.4, "+y", 4, 0, FJORD)
    s += fog(pg, [(400, 10, 90, 50, 1), (-14, 240, 90, 40, 1)])
    b += G(f'<g clip-path="{clip2}">{s}</g>', "translate(0 84)")
    y = 324
    b += R(0, y, 390, 66, 0, FALU)
    b += ic("clock", 16, y + 13, 18, WHITE, 2)
    b += T(42, y + 28, "Spillet venter på deg", 19, 800, WHITE, "b")
    b += T(42, y + 49, "Uke 11. Ordren din mangler.", 14, 700, WHITE)
    b += R(262, y + 13, 114, 40, 9, WHITE)
    b += T(319, y + 39, "Gå til Uke 11", 15, 800, INK, "b", "middle")
    y += 66
    b += waiting(y, STATUS_11, h=106)
    y += 106
    b += R(0, y, 390, 844 - y, 0, WHITE)
    b += T(16, y + 26, "Stegene dine", 18, 800, INK, "b")
    steps = [("Klassespill", "Pågår", "now"), ("Debrief", "Etter spillet", "next"), ("Quiz", "", "next"), ("Replay", "", "next"), ("Individuell test", "", "next"), ("Rapport", "PDF", "next")]
    sy = y + 38
    b += L(26, sy + 8, 26, sy + 5 * 29 + 8, ASPHALT, 9, cap="round")
    b += L(26, sy + 8, 26, sy + 5 * 29 + 8, "#E7EFF1", 1, dash="4 4")
    for i, (nm, note, st) in enumerate(steps):
        ry = sy + i * 29
        if st == "now":
            b += C(26, ry + 8, 10, FALU, WHITE, 2)
            b += T(46, ry + 13, nm, 15, 800, INK)
            b += T(374, ry + 13, note, 13, 800, FALU, "n", "end")
        else:
            b += C(26, ry + 8, 8, WHITE, ASPHALT, 2)
            b += T(46, ry + 13, nm, 14, 700, MUTED)
            if note:
                b += T(374, ry + 13, note, 13, 600, MUTED, "n", "end")
    y2 = sy + 6 * 29
    b += L(14, y2, 376, y2, LINE, 1)
    b += ic("cal", 16, y2 + 10, 16, FJORD_D, 1.6)
    b += T(40, y2 + 23, "Neste frist: Spillfrist ti. 8. des", 15, 800, INK)
    b += ic("pin", 16, y2 + 34, 16, FJORD_D, 1.6)
    b += T(40, y2 + 47, "Labtimer i Datalab A2", 14, 800, INK)
    b += T(40, y2 + 66, "to. 26. nov 14:15, ma. 30. nov 10:15", 13, 600, MUTED)
    b += T(40, y2 + 83, "to. 3. des 14:15, ma. 7. des 10:15", 13, 600, MUTED)
    b += T(374, y2 + 23, "Demodata", 13, 600, MUTED, "n", "end")
    pg.add(T(560, 26, "Under spill", 15, 800, FJORD_P))
    pg.add(phone(pg, 560, 40, 0.97, b))
    pg.write()


# ---------- 07 Debrief ----------
def demand_stacks(x, y, weeks=12, cs=13):
    out = ""
    for i in range(weeks):
        wk = i + 1
        n = WEEKS[wk]["demand"]
        cx = x + i * 29
        for j in range(n):
            out += ic_crate(cx + 8, y - (j + 1) * (cs * 0.86) + 2, cs)
        out += T(cx + 14, y + 20, wk, 13, 700, MUTED, "n", "middle", num=True)
    return out


def order_chart(x, y, w, h):
    weeks = list(range(1, 37))
    ymax = 32
    def sx(week):
        return x + (week - 1) / 35 * w
    def sy(v):
        return y + h - v / ymax * h
    out = ""
    for v in (0, 8, 16, 24, 32):
        out += L(x, sy(v), x + w, sy(v), LINE if v else INK, 1)
        out += T(x - 6, sy(v) + 4, v, 13, 600, MUTED, "n", "end", num=True)
    for wk in (1, 12, 24, 36):
        out += T(sx(wk), y + h + 17, wk, 13, 600, MUTED, "n", "middle", num=True)
    out += T(x + w, y + h + 34, "Uke", 13, 700, MUTED, "n", "end")
    d = [f"{sx(w_):.1f} {sy(WEEKS[w_]['demand']):.1f}" for w_ in weeks]
    out += PATH("M" + " L".join(d), stroke=INK, sw=1.6, dash="4 3")
    for role in ROLES:
        pts = [f"{sx(w_):.1f} {sy(WEEKS[w_]['seats'][role]['ordre']):.1f}" for w_ in weeks]
        out += PATH("M" + " L".join(pts), stroke=WHITE, sw=4)
        out += PATH("M" + " L".join(pts), stroke=CHART[role], sw=2.2)
    peak = {"Fabrikk": (18, 31), "Distributør": (14, 22), "Grossist": (11, 24), "Detaljist": (15, 12)}
    lab = {"Fabrikk": (7, 2, "start"), "Distributør": (8, -7, "start"), "Grossist": (-7, -3, "end"), "Detaljist": (8, -5, "start")}
    halo = 'paint-order="stroke" stroke="#FFFFFF" stroke-width="3.5" stroke-linejoin="round"'
    for role, (wk, v) in peak.items():
        px, py = sx(wk), sy(WEEKS[wk]["seats"][role]["ordre"])
        out += C(px, py, 4.5, CHART[role], WHITE, 1.4)
        dx, dy, a = lab[role]
        out += T(px + dx, py + dy, f"{role} {WEEKS[wk]['seats'][role]['ordre']}", 13, 800, INK, "n", a, extra=halo)
    out += T(sx(30), sy(8) - 8, "Kunden 8", 13, 700, INK, "n", "middle")
    return out


def page_07():
    pg = Page("07-debrief.svg", "deb", 2100, 1200, "Kjeden: Gruppedebrief der tåka letter",
              "Fem telefonruter og én delt skjerm: Forklaring, avsløringen av etterspørselen, ordrer per Rolle, ditt øyeblikk i Uke 11, quiz. Den delte skjermen viser hele landskapet uke for uke.", FJORD_D)
    scale = 0.76
    pw = 390 * scale
    gap = 18
    xs = [30 + i * (pw + gap) for i in range(5)]
    top = 76
    pg.add(T(30, 50, "Debrief: tåka letter", 34, 800, WHITE, "b"))

    def head(title, sub=None):
        o = status_row()
        o += T(20, 66, title, 30, 800, WHITE, "b")
        if sub:
            o += T(370, 64, sub, 13, 700, FJORD_P, "n", "end")
        return o

    # 1 Forklaring
    p1 = head("Debrief", "Spill 17")
    clip1 = pg.clip(0, 0, 390, 210)
    iso = Iso(pg, 190, 50, 22)
    sc = R(0, 0, 390, 210, 0, GRASS)
    sc += iso.poly([(3.6, -14, 0), (5, -14, 0), (5, 20, 0), (3.6, 20, 0)], ASPHALT)
    for a, b, h in [(-1.2, -0.8, 1.4), (-1.4, 2.4, 1.5), (0.8, -2, 1.2), (5.8, 0, 1.2)]:
        sc += spruce(iso, a, b, h)
    sc += b_grossist(iso, 0, 0, True)
    sc += fog(pg, [(390, 30, 110, 80, 1), (10, 170, 110, 70, 1), (195, 0, 200, 34, 0.9), (360, 190, 80, 40, 0.9)])
    p1 += G(f'<g clip-path="{clip1}">{sc}</g>', "translate(0 84)")
    p1 += R(112, 172, 166, 36, 18, INK)
    p1 += ic("lock", 124, 182, 16, WHITE, 2)
    p1 += T(148, 195, "Tåka står ennå", 14, 800, WHITE)
    y = 294
    p1 += R(0, y, 390, 844 - y, 0, WHITE)
    p1 += T(20, y + 34, "Skriv Forklaringen din", 24, 800, INK, "b")
    p1 += PS(20, y + 60, "Hva tror du skjedde med kundene? Hvorfor ble kjeden dyr? Svar før du ser fasiten.", 350, 15, 1.32, 600, MUTED)
    p1 += R(20, y + 104, 350, 164, 10, WHITE, FJORD, 2)
    p1 += PS(34, y + 130, "Jeg tror kundene ville ha stadig mer utover i spillet. Da køen min vokste, trodde jeg det ville fortsette, så jeg bestilte mye for å ta den igjen.", 322, 16, 1.36, 600, INK)
    p1 += T(20, y + 296, "Gruppa", 14, 800, MUTED)
    for i, (n, done) in enumerate([("Ida", True), ("Sara", False), ("Mikkel", True), ("Jonas", False)]):
        gx = 20 + i * 88
        p1 += ic("check" if done else "clock", gx, y + 306, 15, FURU if done else OKER_D, 2.2)
        p1 += T(gx + 20, y + 319, n, 14, 700, INK)
    p1 += T(20, y + 356, "Avsløringen åpner når alle fire har skrevet.", 14, 700, MUTED)
    p1 += R(20, y + 372, 350, 56, 12, FALU_D) + R(20, y + 369, 350, 56, 12, FALU)
    p1 += T(195, y + 405, "Send Forklaringen", 21, 800, WHITE, "b", "middle")
    p1 += T(370, y + 444, "Demodata", 13, 600, MUTED, "n", "end")

    # 2 Klimaks
    p2 = head("Fasiten", "Spill 17")
    p2 += R(0, 84, 390, 760, 0, WHITE)
    p2 += T(20, 128, "Dette kjøpte kundene.", 26, 800, INK, "b")
    p2 += T(120, 262, "4", 136, 800, INK, "b", "middle", num=True)
    p2 += PATH("M172 214 H226 M206 192 l22 22 l-22 22", stroke=FALU, sw=9)
    p2 += T(290, 262, "8", 136, 800, FALU, "b", "middle", num=True)
    p2 += PS(20, 300, "4 kasser i uka. I Uke 5 ble det 8. Etter det endret det seg aldri.", 350, 21, 1.3, 800, INK, "b", k=0.5)
    p2 += T(20, 382, "Kundeetterspørsel, kasser per Uke", 14, 800, MUTED)
    p2 += demand_stacks(20, 492, 12, 11.5)
    p2 += T(376, 530, "... 8 hver uke ut spillet", 14, 700, MUTED, "n", "end")
    p2 += L(20, 548, 370, 548, LINE, 1)
    p2 += PS(20, 580, "Bare Ida så dette tallet, én uke om gangen. Alle dere andre så bare ordren fra leddet foran.", 350, 17, 1.36, 700, INK)
    p2 += PS(20, 668, "Øvelsen heter Beer Game. Så liten var endringen som satte alt i gang.", 350, 15, 1.36, 600, MUTED)
    p2 += R(20, 738, 350, 56, 12, FJORD_D) + R(20, 735, 350, 56, 12, FJORD)
    p2 += T(195, 771, "Se hva det ble til i kjeden", 20, 800, WHITE, "b", "middle")
    p2 += T(370, 824, "Demodata", 13, 600, MUTED, "n", "end")

    # 3 ordrer
    p3 = head("Ordrene", "Spill 17")
    p3 += R(0, 84, 390, 760, 0, WHITE)
    p3 += T(20, 124, "Samme endring, stadig større ordre", 21, 800, INK, "b")
    p3 += T(20, 146, "Ordre per Uke, kasser", 14, 700, MUTED)
    p3 += order_chart(44, 164, 326, 270)
    # forsterkning, tall i rekkefølge oppover kjeden
    y = 484
    p3 += T(20, y, "Forsterkning fra kunde til Fabrikk", 15, 800, INK)
    amp = DATA["amplification"]
    for i, role in enumerate(ROLES):
        ry = y + 14 + i * 40
        v = amp[role]
        p3 += role_icon(role, 20, ry + 6, 20, CHART[role] if role != "Detaljist" else OKER_D)
        p3 += T(48, ry + 22, role, 15, 800, INK)
        p3 += R(148, ry + 9, 158 * v / 7.6, 14, 2, CHART[role])
        p3 += T(370, ry + 24, f"{fnum(v, 1)}×", 24, 800, INK, "b", "end", num=True)
    p3 += PS(20, y + 192, "Hvert ledd så bare ordren foran seg, og hver ordre kom to uker for sent. Forsterkningen kommer av strukturen.", 350, 15, 1.32, 700, INK)
    p3 += T(20, 800, "Egen tabell: uke for uke", 14, 800, FJORD, extra='text-decoration="underline"')
    p3 += T(370, 824, "Demodata", 13, 600, MUTED, "n", "end")

    # 4 ditt øyeblikk
    s = WEEKS[11]["seats"]
    costs = sum(WEEKS[w]["seats"]["Grossist"]["ukekost"] for w in range(26, 33))
    assert abs(costs - 93.0) < 0.01, costs
    p4 = head("Ditt øyeblikk", "Uke 11")
    d4, tt = diorama(pg, 0, 13, slots_for(11), H=196, signs=False)
    assert tt.full == 16
    p4 += G(d4, "translate(0 84)")
    y = 280
    p4 += R(0, y, 390, 844 - y, 0, WHITE)
    p4 += T(20, y + 26, "Du så", 14, 800, MUTED)
    for i, (lab, val) in enumerate([("Lager", 0), ("Restordre", 13), ("Inn", 8), ("På vei", 16)]):
        gx = 20 + i * 88
        p4 += T(gx, y + 62, val, 32, 800, FALU if lab == "Restordre" else INK, "b", num=True)
        p4 += T(gx, y + 80, lab, 13, 700, MUTED)
    p4 += L(20, y + 92, 370, y + 92, LINE, 1)
    p4 += T(20, y + 134, "Du bestilte", 16, 800, MUTED)
    p4 += T(370, y + 138, "24", 52, 800, FALU, "b", "end", num=True)
    p4 += L(20, y + 152, 370, y + 152, LINE, 1)
    p4 += T(20, y + 176, "De andre så i samme uke", 14, 800, MUTED)
    for i, (role, nm) in enumerate([("Detaljist", "Ida"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]):
        q = s[role]
        ry = y + 186 + i * 26
        p4 += role_icon(role, 20, ry, 17)
        txt = f"{nm}: lager {q['lager']}, restordre {q['restordre']}, bestilte {q['ordre']}"
        p4 += T(44, ry + 14, txt, 14, 700, INK)
    y2 = y + 276
    p4 += L(20, y2, 370, y2, LINE, 1)
    p4 += T(20, y2 + 24, "Det kostet senere", 14, 800, MUTED)
    p4 += PS(20, y2 + 46, "24 nådde Mikkel i Uke 13: lageret gikk fra 12 til 0. Dine kasser kom da køen var borte: 93,00 kr i lagerkost i uke 26 til 32.", 350, 15, 1.32, 700, INK)
    p4 += ki_badge(20, y2 + 108, "KI-generert, kan ta feil", 20, size=13)
    p4 += T(370, y2 + 122, "Demodata", 13, 600, MUTED, "n", "end")
    p4 += R(20, y2 + 136, 350, 46, 10, FJORD)
    p4 += T(195, y2 + 165, "Videre til quiz", 18, 800, WHITE, "b", "middle")

    # 5 quiz
    p5 = head("Debrief-quiz", "Spørsmål 2")
    p5 += R(0, 84, 390, 760, 0, WHITE)
    p5 += PS(20, 124, "Kundene gikk fra 4 til 8 én gang. Hvorfor bestilte Fabrikk 31 på det meste?", 350, 21, 1.26, 800, INK, "b", k=0.5)
    opts = [
        ("Kundene kjøpte mer og mer utover i spillet.", "wrong"),
        ("Hvert ledd svarte på ordren foran, sent og med litt ekstra.", "right"),
        ("Fabrikk produserte for lite i starten.", ""),
    ]
    y = 214
    for t_, st in opts:
        lines = wrap(t_, 296, 15)
        h = 26 + len(lines) * 21
        fill = {"wrong": mix(FALU, "#FFFFFF", 0.9), "right": mix(FURU, "#FFFFFF", 0.88), "": WHITE}[st]
        edge = {"wrong": FALU, "right": FURU, "": LINE}[st]
        p5 += R(20, y, 350, h, 10, fill, edge, 2 if st else 1)
        if st == "wrong":
            p5 += ic("x", 32, y + h / 2 - 9, 18, FALU, 2.6)
        elif st == "right":
            p5 += ic("check", 32, y + h / 2 - 9, 18, FURU, 2.6)
        else:
            p5 += C(41, y + h / 2, 8, WHITE, MUTED, 1.4)
        p5 += PS(62, y + 24, t_, 296, 15, 1.36, 700, INK)
        y += h + 10
    p5 += T(20, y + 24, "Du svarte det øverste", 16, 800, FALU, "b")
    p5 += PS(20, y + 50, "Se kurven: etterspørselen sto stille på 8 fra Uke 5. Det som vokste, var ordrene. Fabrikk så en ordre på 22 uten å kunne se at kunden fortsatt kjøpte 8.", 350, 15, 1.36, 600, INK)
    # liten kurve
    cy = y + 150
    sx = lambda w_: 20 + (w_ - 1) / 35 * 350
    sy_ = lambda v: cy + 66 - v / 32 * 66
    p5 += L(20, cy + 66, 370, cy + 66, INK, 1)
    p5 += PATH("M" + " L".join(f"{sx(w_):.1f} {sy_(WEEKS[w_]['demand']):.1f}" for w_ in range(1, 37)), stroke=INK, sw=1.6, dash="4 3")
    p5 += PATH("M" + " L".join(f"{sx(w_):.1f} {sy_(WEEKS[w_]['seats']['Fabrikk']['ordre']):.1f}" for w_ in range(1, 37)), stroke=CHART["Fabrikk"], sw=2.2)
    p5 += T(sx(19) + 6, cy + 10, "Fabrikk 31", 13, 800, INK)
    p5 += T(370, sy_(8) - 5, "Kunden 8", 13, 700, INK, "n", "end")
    p5 += ki_badge(20, 744, "KI-generert, kan ta feil", 20)
    p5 += R(20, 772, 350, 46, 10, FJORD)
    p5 += T(195, 801, "Neste spørsmål", 18, 800, WHITE, "b", "middle")

    frames = [p1, p2, p3, p4, p5]
    caps = [("1  Forklaring først", "Avsløringen er låst. Du skriver hva du tror før du ser fasiten."),
            ("2  Klimaks", "Tåka letter over butikken. 4 til 8. Så liten var endringen."),
            ("3  Ett diagram", "Fire linjer til skala, fra 1,8× hos Ida til 7,6× hos Jonas."),
            ("4  Ditt øyeblikk", "Din hall i Uke 11: hva du så, bestilte og betalte, og hva de andre så."),
            ("5  Quiz", "Feil svar forklares med kurvene fra spillet deres.")]
    for i, fr in enumerate(frames):
        pg.add(phone(pg, xs[i], top, scale, fr))
        pg.add(T(xs[i], top + 844 * scale + 28, caps[i][0], 18, 800, WHITE, "b"))
        pg.add(PS(xs[i], top + 844 * scale + 48, caps[i][1], pw, 14, 1.3, 600, FJORD_P))

    # delt skjerm
    wk = 18
    sx0, sy0, sw, sh = 30, 816, 1552, 368
    pg.add(R(sx0 - 8, sy0 - 8, sw + 16, sh + 16, 12, "#0A1E26", "#33505B", 1.2))
    bar = 42
    pg.add(R(sx0, sy0, sw, bar, 0, FJORD))
    pg.add(T(sx0 + 16, sy0 + 29, "Delt skjerm: hele kjeden, Spill 17", 19, 800, WHITE, "b"))
    pg.add(T(sx0 + sw - 16, sy0 + 28, "Dere ser dette sammen, Demodata", 14, 700, FJORD_P, "n", "end"))
    lw = 1090
    lh = sh - bar - 58
    tally = Tally()
    land, tally = landscape(pg, sx0, sy0 + bar, lw, lh, wk, 13.5, tally)
    pg.add(land)
    data = WEEKS[wk]["seats"]
    assert tally.full == sum(data[r]["lager"] for r in ROLES), tally.full
    assert tally.owed == sum(data[r]["restordre"] for r in ROLES), tally.owed
    # tidslinje
    ty = sy0 + bar + lh
    pg.add(R(sx0, ty, lw, 58, 0, FJORD_D))
    tlx = sx0 + 16
    tlw = lw - 32
    totals = {w: sum(WEEKS[w]["seats"][r]["restordre"] for r in ROLES) for w in WEEKS}
    mx = max(totals.values())
    for w, v in totals.items():
        bx = tlx + (w - 1) / 36 * tlw
        h = 26 * v / mx
        pg.add(R(bx, ty + 32 - h, tlw / 36 - 2, max(h, 1), 1, OKER_L if w <= wk else "#2A7686"))
    hx = tlx + (wk - 0.5) / 36 * tlw
    pg.add(L(hx, ty + 2, hx, ty + 44, WHITE, 2))
    pg.add(C(hx, ty + 38, 8, WHITE, INK, 1.4))
    pg.add(T(tlx, ty + 52, "Uke 1", 13, 700, FJORD_P))
    pg.add(T(tlx + tlw, ty + 52, "Uke 36", 13, 700, FJORD_P, "n", "end"))
    pg.add(T(hx + 14, ty + 52, "Dra for å spole. Søylene er samlet restordre.", 13, 700, WHITE))
    # sidepanel med tabell
    px = sx0 + lw
    pw2 = sw - lw
    pg.add(R(px, sy0 + bar, pw2, sh - bar, 0, WHITE))
    pg.add(T(px + 20, sy0 + bar + 50, f"Uke {wk}", 44, 800, INK, "b"))
    tot = sum(data[r]["kost_sum"] for r in ROLES)
    pg.add(T(px + pw2 - 20, sy0 + bar + 28, "Kjeden så langt", 14, 700, MUTED, "n", "end"))
    pg.add(T(px + pw2 - 20, sy0 + bar + 52, kr(tot), 24, 800, INK, "b", "end", num=True))
    ty2 = sy0 + bar + 66
    for dx, h, a in [(20, "Rolle", "start"), (250, "Lager", "end"), (350, "Restordre", "end"), (pw2 - 20, "Ordre", "end")]:
        pg.add(T(px + dx, ty2 + 18, h, 14, 800, MUTED, "n", a))
    pg.add(L(px + 20, ty2 + 26, px + pw2 - 20, ty2 + 26, INK, 1.2))
    for i, role in enumerate(ROLES):
        ry = ty2 + 26 + i * 40
        q = data[role]
        pg.add(role_icon(role, px + 20, ry + 10, 20))
        pg.add(T(px + 48, ry + 26, role, 16, 800, INK))
        pg.add(T(px + 250, ry + 28, q["lager"], 22, 800, INK, "b", "end", num=True))
        pg.add(T(px + 350, ry + 28, q["restordre"], 22, 800, FALU, "b", "end", num=True))
        pg.add(T(px + pw2 - 20, ry + 28, q["ordre"], 22, 800, INK, "b", "end", num=True))
        pg.add(L(px + 20, ry + 40, px + pw2 - 20, ry + 40, LINE, 1))
    pg.add(T(px + 20, ty2 + 26 + 4 * 40 + 24, "Modellen og tabellen viser de samme tallene.", 14, 700, MUTED))

    # høyre spalte
    rx = 1620
    pg.add(T(rx, 120, "Tåka var", 52, 800, WHITE, "b"))
    pg.add(T(rx, 174, "hele poenget.", 52, 800, WHITE, "b"))
    para, y = P(rx, 224, "I 36 uker sto du i ett hus og så en kø ved porten. Nå ser du alle fire, med kassene og køene talt opp.", 440, 20, 1.42, 600, FJORD_P)
    pg.add(para)
    para, y = P(rx, y + 16, "Dra i tidslinjen. Du ser køene bygge seg bakover mot Fabrikk, og etter uke 25 ser du stablene fylle hallene etter tur.", 440, 20, 1.42, 600, FJORD_P)
    pg.add(para)
    para, y = P(rx, y + 16, "Ingen peker på noen. Alle bestilte ut fra det de så, og modellen viser hva hver av dere ikke kunne se.", 440, 20, 1.42, 700, WHITE)
    pg.add(para)
    yy = y + 36
    pg.add(L(rx, yy, rx + 440, yy, "#2A7686", 1))
    pg.add(T(rx, yy + 40, "Telleregelen gjelder her også", 22, 800, WHITE, "b"))
    pg.add(ic_crate(rx, yy + 58, 24))
    pg.add(T(rx + 36, yy + 78, "1 palle = 4 kasser", 18, 700, FJORD_P))
    pg.add(ic_van(rx, yy + 96, 28, dashed=True))
    pg.add(T(rx + 36, yy + 112, "1 rød bil = 4 kasser i restordre", 18, 700, FJORD_P))
    pg.add(ki_badge(rx, yy + 136, None, 24))
    pg.add(PS(rx + 40, yy + 153, "Personlige avsnitt er KI-skrevet og merket. Tallene kommer fra loggen.", 400, 16, 1.36, 700, FJORD_P))
    iy = yy + 226
    pg.add(T(rx, iy, "Dra til Uke 29: nå er det stablene", 24, 800, WHITE, "b"))
    t29 = Tally()
    land29, t29 = landscape(pg, rx, iy + 14, 440, 300, 29, 6.8, t29, plates=False)
    pg.add(R(rx - 3, iy + 11, 446, 306, 8, "#0A1E26"))
    pg.add(land29)
    d29 = WEEKS[29]["seats"]
    assert t29.full == sum(d29[r]["lager"] for r in ROLES) and t29.owed == 0
    pg.add(T(rx, iy + 342, "Lager i Uke 29: " + ", ".join(f"{r} {d29[r]['lager']}" for r in ROLES[:2]) + ",", 15, 700, FJORD_P))
    pg.add(T(rx, iy + 362, ", ".join(f"{r} {d29[r]['lager']}" for r in ROLES[2:]) + ". Kundene kjøper fortsatt 8.", 15, 700, FJORD_P))
    pg.write()


# ---------- 08 Oversikt ----------
NAMES_POOL = ["Vilde", "Isak", "Maja", "Theo", "Sofie", "Filip", "Hedda", "Aksel", "Tuva", "Elias", "Nora", "Emil", "Lea"]
ROLE_POOL = ["Fabrikk", "Detaljist", "Distributør", "Grossist"]


def table_rows():
    rows = []
    idx = 0
    for g in GAMES:
        st = g["status"]
        if st == "ferdig":
            continue
        rec = dict(g)
        if st == "venter":
            rec["wait"] = f"{g['venter_paa']}: {g['navn']}"
            rec["time"] = f"{g['ventet_timer']} t"
            rec["sort"] = (0, -g["ventet_timer"])
        elif st == "pauset":
            rec["wait"] = f"Pause til {g['fortsetter']}"
            rec["time"] = "Pause"
            rec["sort"] = (1, g["spill"])
        else:
            if g["spill"] == 17:
                rec["wait"] = "Fabrikk: Jonas, Grossist: Sara"
                mins = 3
            else:
                idx += 1
                mins = 3 + (g["spill"] * 17) % 94
                rec["wait"] = f"{ROLE_POOL[g['spill'] % 4]}: {NAMES_POOL[g['spill'] % 13]}"
            rec["time"] = f"{mins} min"
            rec["sort"] = (2, -mins)
        rows.append(rec)
    rows.sort(key=lambda r: r["sort"])
    return rows


def page_08():
    pg = Page("08-laerer-oversikt.svg", "over", 1600, 1000, "Kjeden: Oversikt over 60 Klassespill",
              "Kart over 60 kvartaler med status i form og farge, tabell over alle spill som ikke er ferdige, utheving av spillet som er nær KI-overtakelse, trakten og filtrering.", PAPER)
    pg.add(topbar(pg, 1600, "class-of-1994  /  Klasseøkt  /  Oversikt", "Demodata"))
    counts = {k: sum(1 for g in GAMES if g["status"] == k) for k in ("ferdig", "pågår", "pauset", "venter")}
    assert counts == {"ferdig": 41, "pågår": 13, "pauset": 2, "venter": 4}, counts
    # filter
    y = 78
    filt = [("Alle", 60, None, True), ("Ferdig", 41, "ferdig", False), ("Pågår", 15, "pågår", False), ("Pauset", 2, "pauset", False), ("Venter", 4, "venter", False), ("Nær KI", 1, "hot", False)]
    fx = 20
    for lab, n, st, on in filt:
        w = 70 + len(lab) * 9 + (34 if st else 0)
        pg.add(R(fx, y, w, 40, 20, INK if on else WHITE, INK if on else "#7E97A3", 1.2))
        tx = fx + 14
        if st:
            pg.add(status_legend_icon(st, fx + 8, y + 7, 22))
            tx += 22
        pg.add(T(tx, y + 26, lab, 15, 800, WHITE if on else INK))
        pg.add(T(fx + w - 14, y + 27, n, 17, 800, WHITE if on else INK, "b", "end", num=True))
        fx += w + 8
    n_ki = sum(1 for g in GAMES if g.get("ki_seter"))
    pg.add(R(fx, y, 170, 40, 20, WHITE, "#7E97A3", 1.2))
    pg.add(ki_badge(fx + 10, y + 10, None, 20))
    pg.add(T(fx + 42, y + 26, "Har KI-sete", 15, 800, INK))
    pg.add(T(fx + 158, y + 27, n_ki, 17, 800, INK, "b", "end", num=True))
    fx += 178
    pg.add(R(fx, y, 216, 40, 20, WHITE, "#7E97A3", 1.2))
    pg.add(ic("search", fx + 14, y + 12, 16, MUTED, 1.8))
    pg.add(T(fx + 38, y + 26, "Søk spill eller student", 15, 600, MUTED))
    pg.add(button(1360, y - 2, 220, 42, "Send Melding", "teal", 17, "letter"))

    # kart
    mx, my, mw, mh = 20, 130, 720, 572
    pg.add(R(mx, my, mw, mh, 14, FJORD))
    for i in range(24):
        a = mx + 20 + (i * 137) % (mw - 40)
        b = my + 20 + (i * 211) % (mh - 40)
        pg.add(PATH(f"M{a} {b} q6 -4 12 0 t12 0", stroke=mix(FJORD_L, "#FFFFFF", 0.3), sw=1.1, op=0.4))
    iso = Iso(pg, mx + 278, my + 30, 42)
    pg.add(iso.box(-0.3, -0.3, -0.26, 10.5, 6.5, 0.26, (GRASS, "#7A5A33", "#5F4526"), "#2F2412", 0.6))
    pg.add(block_map(iso, True, 14))
    # utheving av spill 2
    px, py = iso.p(1.56, 0.1, 0.34)
    # hjørnet øverst til høyre: varsel
    ax, ay = mx + 396, my + 14
    pg.add(R(ax, ay, 310, 62, 10, FALU))
    pg.add(ic("warn", ax + 12, ay + 12, 20, WHITE, 2))
    pg.add(T(ax + 40, ay + 26, "Spill 2 venter på Noah (Grossist)", 15, 800, WHITE))
    pg.add(T(ax + 40, ay + 47, "23 t. KI overtar om 1 t.", 15, 800, WHITE))
    pg.add(L(px + 18, py - 46, ax, ay + 24, FALU, 2.4))
    # zoom på kvartal
    zx, zy, zw, zh = mx + 14, my + 416, 692, 144
    pg.add(R(zx, zy, zw, zh, 10, WHITE))
    pg.add(T(zx + 14, zy + 26, "Spill 2, Uke 19", 19, 800, INK, "b"))
    pg.add(T(zx + zw - 14, zy + 24, "Klikk et kvartal for å zoome", 13, 700, MUTED, "n", "end"))
    seats = [("Detaljist", "Emma", True), ("Grossist", "Noah", False), ("Distributør", "Aksel", True), ("Fabrikk", "Lea", True)]
    for i, (role, nm, done) in enumerate(seats):
        cx = zx + 14 + i * 122
        pg.add(mini_building(role, cx + 46, zy + 46, 10, done))
        pg.add(T(cx, zy + 108, nm, 14, 800, INK if done else FALU))
        if done:
            pg.add(ic("check", cx, zy + 114, 14, FURU, 2.4))
            pg.add(T(cx + 18, zy + 126, "Bestilt", 13, 700, MUTED))
        else:
            pg.add(ic("clock", cx, zy + 114, 14, FALU, 2))
            pg.add(T(cx + 18, zy + 126, "Venter 23 t", 13, 800, FALU))
    bx = zx + 508
    pg.add(button(bx, zy + 40, 170, 40, "Send Melding til Noah", "teal", 13))
    pg.add(button(bx, zy + 88, 170, 40, "La KI overta nå", "ghost", 14))

    # tabell
    tx, ty, tw = 760, 130, 820
    cols = [(0, "Spill", "start"), (52, "Status", "start"), (168, "Uke", "end"), (190, "Venter på", "start"), (448, "Ventet", "end"), (510, "KI-seter", "end"), (620, "Kjedekost", "end"), (800, "Handling", "end")]
    pg.add(R(tx, ty, tw, 32, 6, INK))
    for dx, h, a in cols:
        pg.add(T(tx + 10 + dx, ty + 22, h, 14, 800, WHITE, "n", a))
    rows = table_rows()
    assert len(rows) == 19
    rh = 26.2
    for i, r in enumerate(rows):
        ry = ty + 32 + i * rh
        hot = r["spill"] == 2
        if hot:
            pg.add(R(tx, ry, tw, rh, 0, mix(FALU, "#FFFFFF", 0.86)))
        elif r["status"] == "venter":
            pg.add(R(tx, ry, tw, rh, 0, mix(OKER_L, "#FFFFFF", 0.7)))
        tb = ry + rh / 2 + 5
        pg.add(T(tx + 10, tb, r["spill"], 15, 800, INK, "b", num=True))
        st = "hot" if hot else r["status"]
        pg.add(status_legend_icon(st, tx + 60, ry + 2, 19))
        lab = "Nær KI" if hot else STATUS_STYLE[r["status"]][2]
        pg.add(T(tx + 88, tb, lab, 14, 800 if hot or r["status"] == "venter" else 600, FALU if hot else INK))
        pg.add(T(tx + 178, tb, r["uke"], 14, 700, INK, "n", "end", num=True))
        pg.add(T(tx + 200, tb, r["wait"], 14, 700 if r["status"] == "venter" else 600, INK))
        pg.add(T(tx + 458, tb, r["time"], 14, 800 if r["status"] == "venter" else 600, FALU if hot else INK, "n", "end", num=True))
        if r.get("ki_seter"):
            pg.add(ki_badge(tx + 478, ry + 5, None, 16))
            pg.add(T(tx + 520, tb, r["ki_seter"], 14, 800, INK, "n", "end", num=True))
        pg.add(T(tx + 630, tb, f"{r['kjedekost']:,}".replace(",", " ") + " kr", 14, 600, INK, "n", "end", num=True))
        if r["status"] == "venter":
            pg.add(T(tx + 810, tb, "Send Melding", 14, 800, FJORD, "n", "end", extra='text-decoration="underline"'))
        elif r["status"] == "pauset":
            pg.add(T(tx + 810, tb, "Se avtale", 14, 700, FJORD, "n", "end", extra='text-decoration="underline"'))
        else:
            pg.add(T(tx + 810, tb, "Åpne", 14, 700, FJORD, "n", "end", extra='text-decoration="underline"'))
        pg.add(L(tx, ry + rh, tx + tw, ry + rh, LINE, 1))
    fy = ty + 32 + 19 * rh
    pg.add(status_legend_icon("ferdig", tx + 8, fy + 3, 19))
    pg.add(T(tx + 36, fy + 20, "41 ferdige spill er skjult. Vis dem i tabellen", 14, 700, FJORD, extra='text-decoration="underline"'))

    # trakt
    y0 = 716
    pg.add(L(20, y0, 1580, y0, LINE, 1))
    pg.add(T(20, y0 + 36, "Trakten: hvor langt studentene er kommet", 22, 800, INK, "b"))
    pg.add(T(1580, y0 + 34, "Antall studenter av 240", 14, 700, MUTED, "n", "end"))
    f = DATA["funnel"]
    steps = [("Registrert", f["registrert"]), ("Klassespill ferdig", f["klassespill_ferdig"]), ("Debrief ferdig", f["debrief_ferdig"]), ("Quiz bestått", f["quiz_bestått"]),
             ("Replay ferdig", f["replay_ferdig"]), ("Test levert", f["test_levert"]), ("KI-vurdering klar", f["ki_vurdering_klar"])]
    fw = 1560 / 7
    base = y0 + 214
    for i, (lab, v) in enumerate(steps):
        bx = 20 + i * fw
        hh = 130 * v / 240
        # søyle av kasser, skalert
        pg.add(R(bx, base - hh, fw - 18, max(hh, 2), 4, OKER if i < 6 and v else "#BCD6DC"))
        if v and hh > 6:
            lines = int(hh // 13)
            for k in range(1, lines + 1):
                pg.add(L(bx, base - k * 13, bx + fw - 18, base - k * 13, OKER_D, 0.5, op=0.5))
        pg.add(T(bx, base - hh - 8, v, 28, 800, INK, "b", num=True))
        pg.add(T(bx, base + 22, lab, 15, 700, INK))
        if i:
            prev = steps[i - 1][1]
            pct = round(v / prev * 100) if prev else 0
            pg.add(T(bx + fw - 22, base + 22, f"{pct} %", 14, 600, MUTED, "n", "end", num=True))
    pg.write()


# ---------- 09 Kontaktark ----------
def page_09():
    pg = Page("09-alle-sider.svg", "alle", 2000, 1400, "Kjeden: alle andre sider",
              "Kontaktark med skisser av alle øvrige sider, gruppert per rolle: Student, Faglærer og Admin.", FJORD_D)
    pg.add(T(30, 54, "Resten av byen", 38, 800, WHITE, "b"))
    pg.add(T(1970, 50, "Lav detalj. Tallene er Demodata.", 15, 700, FJORD_P, "n", "end"))

    def tile_phone(x, y, w, h, draw):
        clip = pg.clip(x, y, w, h, 14)
        return R(x - 4, y - 4, w + 8, h + 8, 18, "#0A1E26") + f'<g clip-path="{clip}">{R(x, y, w, h, 0, WHITE)}{draw(x, y, w, h)}</g>'

    def tile_screen(x, y, w, h, draw):
        clip = pg.clip(x, y, w, h, 6)
        return R(x - 3, y - 3, w + 6, h + 6, 8, "#0A1E26") + f'<g clip-path="{clip}">{R(x, y, w, h, 0, WHITE)}{draw(x, y, w, h)}</g>'

    def band(x, y, w, h, c=FJORD, title=None):
        o = R(x, y, w, h, 0, c)
        if title:
            o += T(x + 10, y + h - 9, title, 13, 800, WHITE, "b")
        return o

    def lines(x, y, w, n, step=13, c=LINE, sw=5):
        o = ""
        for i in range(n):
            o += R(x, y + i * step, w * (0.94 if i % 3 else 0.72), sw, 2.5, c)
        return o

    def scene(x, y, w, h, build, u=11, ax=None, ay=None, foggy=True):
        o = R(x, y, w, h, 0, GRASS)
        iso = Iso(pg, ax or x + w / 2 - 6, ay or y + h * 0.28, u)
        o += build(iso)
        if foggy:
            o += fog(pg, [(x + w, y, 50, 30, 0.95), (x, y + h, 50, 26, 0.95)])
        return o

    # --- studentskisser
    def s_invite(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Invitasjon")
        o += scene(x, y + 34, w, 96, lambda iso: b_grossist(iso, 0, 0, False), 13)
        o += T(x + 10, y + 154, "Bård har invitert deg", 13, 800, INK, "b")
        o += R(x + 10, y + 166, w - 20, 22, 4, WHITE, "#7E97A3", 1) + R(x + 10, y + 196, w - 20, 22, 4, WHITE, "#7E97A3", 1)
        o += R(x + 10, y + 232, w - 20, 30, 6, FALU) + T(x + w / 2, y + 252, "Bli med", 13, 800, WHITE, "b", "middle")
        return o

    def s_login(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Logg inn")
        o += scene(x, y + 34, w, 96, lambda iso: spruce(iso, 2, 2, 1.6) + spruce(iso, 4, 0, 1.3) + spruce(iso, 0, 4, 1.4), 13, foggy=True)
        o += R(x + 10, y + 148, w - 20, 22, 4, WHITE, "#7E97A3", 1) + R(x + 10, y + 178, w - 20, 22, 4, WHITE, "#7E97A3", 1)
        o += R(x + 10, y + 214, w - 20, 30, 6, FJORD) + T(x + w / 2, y + 234, "Logg inn", 13, 800, WHITE, "b", "middle")
        return o

    def s_rules(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Regler")
        o += scene(x, y + 34, w, 96, lambda iso: pallet(iso, 0, 0, 4) + pallet(iso, 1.4, 0, 2), 18, foggy=False, ay=y + 70)
        o += ic_crate(x + 10, y + 142, 15) + T(x + 30, y + 154, "1 palle = 4", 13, 700)
        o += ic_van(x + 8, y + 166, 20) + T(x + 32, y + 178, "1 bil = 4", 13, 700)
        o += ic_van(x + 8, y + 190, 20, dashed=True) + T(x + 32, y + 202, "Du skylder", 13, 700)
        o += R(x + 10, y + 232, w - 20, 30, 6, FALU) + T(x + w / 2, y + 252, "Forstått", 13, 800, WHITE, "b", "middle")
        return o

    def s_start(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Startoppgave")
        o += T(x + 10, y + 56, "Hva tror du skjer?", 13, 800, INK, "b")
        o += lines(x + 10, y + 68, w - 20, 3)
        o += R(x + 10, y + 112, w - 20, 80, 6, WHITE, FJORD, 1.4) + lines(x + 18, y + 124, w - 36, 4, c="#D4E2E6")
        o += R(x + 10, y + 232, w - 20, 30, 6, FALU) + T(x + w / 2, y + 252, "Lever", 13, 800, WHITE, "b", "middle")
        return o

    def s_replay(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Replay")
        o += scene(x, y + 34, w, 118, lambda iso: hall_cut(iso, 0, 0, 2, 2, 7, "Grossist")[0], 12, ay=y + 60)
        o += ki_badge(x + 8, y + 160, "Tre KI-spillere", 16, size=13)
        o += R(x + 10, y + 186, 50, 34, 5, WHITE, INK, 1.4) + R(x + 68, y + 186, w - 78, 34, 6, FALU)
        o += T(x + 68 + (w - 78) / 2, y + 208, "Send", 13, 800, WHITE, "b", "middle")
        return o

    def s_review(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Gjennomgang")
        o += T(x + 10, y + 56, "Runde 1 mot runde 2", 13, 800, INK, "b")
        base = y + 150
        vals = [4, 8, 24, 16, 10, 4]
        vals2 = [4, 6, 10, 9, 8, 8]
        for i, (a, b) in enumerate(zip(vals, vals2)):
            o += R(x + 12 + i * 26, base - a * 3, 10, a * 3, 2, OKER)
            o += R(x + 23 + i * 26, base - b * 3, 10, b * 3, 2, FJORD)
        o += L(x + 10, base, x + w - 10, base, INK, 1)
        o += lines(x + 10, y + 164, w - 20, 4)
        return o

    def s_test(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Individuell test")
        o += T(x + 10, y + 54, "Flervalg", 13, 800, INK)
        for i in range(3):
            o += C(x + 18, y + 68 + i * 15, 5, WHITE if i else FJORD, MUTED, 1.2) + R(x + 30, y + 65 + i * 15, w - 50, 5, 2, LINE)
        o += T(x + 10, y + 128, "Tegn kurven", 13, 800, INK)
        o += R(x + 10, y + 134, w - 20, 50, 4, PAPER, LINE, 1)
        o += PATH(f"M{x + 14} {y + 176} q18 -2 28 -16 t30 -14 t40 12", stroke=FALU, sw=2)
        o += T(x + 10, y + 204, "Langsvar", 13, 800, INK)
        o += R(x + 10, y + 210, w - 20, 50, 4, WHITE, "#7E97A3", 1) + lines(x + 16, y + 218, w - 32, 3, 11, "#D4E2E6", 4)
        return o

    def s_assess(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "KI-vurdering")
        o += ki_badge(x + 8, y + 44, "Teller ikke", 18, size=13)
        o += T(x + 10, y + 84, "Ikke en karakter.", 13, 800, INK)
        o += lines(x + 10, y + 96, w - 20, 5)
        o += R(x + 10, y + 168, w - 20, 54, 6, FJORD_P) + lines(x + 18, y + 178, w - 36, 3, 13, "#9CC6CF")
        o += T(x + 10, y + 244, "Kan ta feil", 13, 700, MUTED)
        return o

    def s_report(x, y, w, h):
        o = R(x, y, w, h, 0, "#DCE7EA")
        o += R(x + 16, y + 16, w - 32, h - 44, 3, WHITE, LINE, 1)
        o += ic_crate(x + 26, y + 26, 14) + T(x + 46, y + 38, "Studentrapport", 13, 800, INK, "b")
        o += lines(x + 26, y + 52, w - 52, 4)
        base = y + 160
        for i, v in enumerate([4, 6, 24, 16, 9, 7]):
            o += R(x + 28 + i * 18, base - v * 2.4, 12, v * 2.4, 2, FALU if v == 24 else OKER)
        o += lines(x + 26, y + 172, w - 52, 4)
        o += T(x + w / 2, y + h - 10, "Last ned PDF", 13, 800, FJORD_D, "n", "middle")
        return o

    def s_sidebyside(x, y, w, h):
        o = band(x, y, w, 34, FJORD, "Alle spill")
        for i in range(8):
            cx = x + 10 + (i % 2) * ((w - 26) / 2 + 6)
            cy = y + 44 + (i // 2) * 56
            o += R(cx, cy, (w - 26) / 2, 50, 4, GRASS)
            iso = IsoMini(cx + 28, cy + 8, 5.5)
            o += iso.tbox(0, 0, 0, 2, 2, 1, FALU) if i % 3 else iso.tbox(0, 0, 0, 2, 2, 1, FJORD)
            o += T(cx + 4, cy + 46, f"{(i + 1) * 7}", 13, 800, INK, "b", num=True)
        return o

    student = [("Invitasjon og registrering", "Lenke fra e-post, navn og passord.", s_invite),
               ("Logg inn", "E-post og passord. Ingen åpen registrering.", s_login),
               ("Regler før første ordre", "Telleregelen, så første Uke.", s_rules),
               ("Startoppgave", "Skriv hva du tror før du spiller.", s_start),
               ("Replay", "Ny runde mot tre KI-spillere, samme hall.", s_replay),
               ("Replay-gjennomgang", "Runde 1 mot runde 2, uke for uke.", s_review),
               ("Individuell test", "Flervalg, tegneoppgave, langsvar.", s_test),
               ("KI-vurdering", "Teller ikke og er aldri en karakter.", s_assess),
               ("Studentrapport (PDF)", "Dine valg og hva de førte til.", s_report),
               ("Alle spill side om side", "Alle kjedene etter Debriefen.", s_sidebyside)]

    # --- lærerskisser
    def t_home(x, y, w, h):
        o = band(x, y, w, 30, FJORD, "Lærerhjem")
        for i, (nm, n) in enumerate([("class-of-1994", "60 spill"), ("class-of-1995", "Utkast"), ("Testspill", "Privat")]):
            ry = y + 42 + i * 44
            o += R(x + 10, ry, w - 20, 38, 5, PAPER, LINE, 1)
            o += role_icon("Grossist", x + 16, ry + 9, 18)
            o += T(x + 42, ry + 24, nm, 14, 800, INK)
            o += T(x + w - 18, ry + 24, n, 13, 600, MUTED, "n", "end")
        return o

    def t_report(x, y, w, h):
        o = band(x, y, w, 30, FJORD, "Klasserapport")
        for i, v in enumerate([164, 121, 97, 58, 12]):
            ry = y + 42 + i * 22
            o += R(x + 10, ry, (w - 70) * v / 164, 15, 2, OKER)
            o += T(x + w - 12, ry + 13, v, 13, 800, INK, "b", "end", num=True)
        o += lines(x + 10, y + 158, w - 20, 2)
        return o

    def t_insight(x, y, w, h):
        o = band(x, y, w, 30, FJORD, "Spillinnsikt")
        return o + G(mini_land(x, y, w, h))

    def mini_land(x, y, w, h):
        o = R(x, y + 30, w, h - 30, 0, GRASS)
        iso = Iso(pg, x + 42, y + 96, 6.5)
        for i, role in enumerate(ROLES):
            ii = Iso(pg, x + 28 + i * 52, y + 78 - (i % 2) * 18, 5.2)
            o += hall_cut(ii, 0, 0, 2, 2, [0, 8, 4, 12][i], role)[0]
        o += R(x + 10, y + h - 26, w - 20, 14, 7, FJORD_D)
        o += C(x + 10 + (w - 20) * 0.45, y + h - 19, 9, WHITE, INK, 1.2)
        return o

    def t_student(x, y, w, h):
        o = band(x, y, w, 30, FJORD, "Studentside")
        o += C(x + 28, y + 56, 15, FJORD_P) + ic("person", x + 18, y + 46, 20, FJORD_D, 1.7)
        o += T(x + 52, y + 54, "Sara Nilsen", 14, 800, INK) + T(x + 52, y + 71, "Grossist, Spill 17", 13, 600, MUTED)
        steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
        for i, s in enumerate(steps):
            cx = x + 20 + i * ((w - 40) / 5)
            o += C(cx, y + 104, 7, FJORD if i < 1 else WHITE, FJORD, 1.6)
        o += L(x + 20, y + 104, x + w - 20, y + 104, FJORD, 1)
        o += lines(x + 10, y + 126, w - 20, 4)
        return o

    def t_plenum(x, y, w, h):
        o = band(x, y, w, 30, INK, "Spill alle side om side, plenum")
        for i in range(12):
            cx = x + 8 + (i % 4) * ((w - 16) / 4)
            cy = y + 38 + (i // 4) * 50
            o += R(cx, cy, (w - 16) / 4 - 4, 46, 3, FJORD_D)
            pts = [f"{cx + 3 + k * ((w - 16) / 4 - 10) / 8:.1f} {cy + 40 - ((k * 37 + i * 11) % 30):.1f}" for k in range(9)]
            o += PATH("M" + " L".join(pts), stroke=OKER_L, sw=1.4)
        return o

    def t_cross(x, y, w, h):
        o = band(x, y, w, 30, FJORD, "Tverrklasse-statistikk")
        for j in range(3):
            base = y + h - 36
            for i, v in enumerate([3, 5, 8, 6, 4]):
                o += R(x + 16 + j * ((w - 20) / 3) + i * 13, base - v * (7 - j), 10, v * (7 - j), 1.5, [OKER, FJORD, FURU][j])
            o += T(x + 16 + j * ((w - 20) / 3), base + 18, f"202{4 + j}", 13, 700, INK)
        return o

    def t_messages(x, y, w, h):
        o = band(x, y, w, 30, FJORD, "Meldinger")
        for i, (nm, stext) in enumerate([("Til alle som venter", "4 spill"), ("Til Noah", "Sendt 14:02"), ("Labtime torsdag", "Utkast")]):
            ry = y + 40 + i * 36
            o += ic("letter", x + 12, ry + 6, 18, FJORD_D, 1.6)
            o += T(x + 38, ry + 20, nm, 14, 700, INK)
            o += T(x + w - 12, ry + 20, stext, 13, 600, MUTED, "n", "end")
            o += L(x + 10, ry + 31, x + w - 10, ry + 31, LINE, 1)
        o += R(x + 10, y + h - 38, w - 20, 28, 6, FALU) + T(x + w / 2, y + h - 19, "Skriv Melding", 13, 800, WHITE, "b", "middle")
        return o

    def t_testgame(x, y, w, h):
        o = band(x, y, w, 30, FJORD, "Lærers testspill")
        o += R(x, y + 30, w, h - 30, 0, GRASS)
        iso = Iso(pg, x + 52, y + 62, 9)
        o += hall_cut(iso, 0, 0, 2, 3, 6, "Grossist")[0]
        o += ki_badge(x + w - 130, y + 46, "3 KI-seter", 18, size=13)
        o += R(x + w - 130, y + 76, 116, 28, 5, FALU) + T(x + w - 72, y + 95, "Spill neste uke", 13, 800, WHITE, "b", "middle")
        o += plate(x + w - 72, y + 124, "Privat", 13, WHITE, INK, w=56)
        return o

    teacher = [("Lærerhjem med klasser", "Alle Klasser og Klasseøkter.", t_home),
               ("Klasserapport", "Fullføring per steg, klar til nedlasting.", t_report),
               ("Spillinnsikt", "Ett spill uke for uke, med tidslinje.", t_insight),
               ("Studentside", "Én student: steg, ordre, leveranser.", t_student),
               ("Spill alle side om side", "Ordrekurver for plenum i Labtimen.", t_plenum),
               ("Tverrklasse-statistikk", "Sammenlign Klasseøkter over år.", t_cross),
               ("Meldinger", "Til spill, grupper eller enkeltstudenter.", t_messages),
               ("Lærers testspill", "Prøv innstillingene mot KI, privat.", t_testgame)]

    # --- admin
    def a_area(x, y, w, h):
        o = band(x, y, w, 30, INK, "Admin-område")
        for i, (a, b) in enumerate([("Institusjoner", "1"), ("Klasser", "3"), ("Revisjonslogg", "212")]):
            ry = y + 40 + i * 34
            o += T(x + 14, ry + 18, a, 14, 700, INK) + T(x + w - 14, ry + 18, b, 14, 800, INK, "b", "end", num=True)
            o += L(x + 10, ry + 28, x + w - 10, ry + 28, LINE, 1)
        return o

    def a_users(x, y, w, h):
        o = band(x, y, w, 30, INK, "Brukere og roller")
        for i, (a, b) in enumerate([("Bård", "Faglærer"), ("Kari", "Hjelpelærer"), ("Sara", "Student")]):
            ry = y + 40 + i * 34
            o += ic("person", x + 12, ry + 4, 18, FJORD_D, 1.6)
            o += T(x + 38, ry + 18, a, 14, 700, INK)
            o += R(x + w - 104, ry + 2, 92, 22, 4, FJORD_P)
            o += T(x + w - 58, ry + 18, b, 13, 700, INK, "n", "middle")
        return o

    def a_cost(x, y, w, h):
        o = band(x, y, w, 30, INK, "KI-kostnad")
        o += ki_badge(x + 10, y + 42, None, 20)
        o += T(x + 44, y + 58, "Forbruk per Klasseøkt", 13, 800, INK)
        base = y + h - 24
        for i, v in enumerate([12, 20, 34, 28, 40, 22, 16, 30]):
            o += R(x + 14 + i * ((w - 28) / 8), base - v * 2, (w - 28) / 8 - 5, v * 2, 2, VIOLET)
        o += L(x + 10, base, x + w - 10, base, INK, 1)
        return o

    admin = [("Admin-område", "Drift av plattformen.", a_area), ("Brukere og roller", "Hvem er hva, med revisjonslogg.", a_users), ("KI-kostnad", "Forbruk og tak per Klasseøkt.", a_cost)]

    # plassering
    y = 88
    pg.add(T(30, y, "Student", 26, 800, OKER_L, "b"))
    pg.add(role_icon("Grossist", 136, y - 19, 22, OKER_L))
    y += 16
    cw = (2000 - 60) / 10
    for i, (nm, line, fn) in enumerate(student):
        x = 30 + i * cw
        pg.add(tile_phone(x + 4, y + 4, cw - 22, 280, fn))
        pg.add(T(x + 2, y + 316, nm, 15, 800, WHITE, "b") if len(nm) < 22 else T(x + 2, y + 316, nm.split(" ")[0] + " " + nm.split(" ")[1], 15, 800, WHITE, "b") + T(x + 2, y + 334, " ".join(nm.split(" ")[2:]), 15, 800, WHITE, "b"))
        pg.add(PS(x + 2, y + (336 if len(nm) < 22 else 354), line, cw - 18, 13, 1.3, 600, FJORD_P))
    y = 520
    pg.add(T(30, y, "Faglærer", 26, 800, OKER_L, "b"))
    pg.add(role_icon("Fabrikk", 152, y - 19, 22, OKER_L))
    y += 16
    cw = (2000 - 60) / 8
    for i, (nm, line, fn) in enumerate(teacher):
        x = 30 + i * cw
        pg.add(tile_screen(x + 3, y + 4, cw - 18, 200, fn))
        pg.add(T(x + 2, y + 234, nm, 16, 800, WHITE, "b"))
        pg.add(PS(x + 2, y + 254, line, cw - 18, 13, 1.3, 600, FJORD_P))
    y = 830
    pg.add(T(30, y, "Admin", 26, 800, OKER_L, "b"))
    pg.add(role_icon("Distributør", 124, y - 19, 22, OKER_L))
    y += 16
    for i, (nm, line, fn) in enumerate(admin):
        x = 30 + i * cw
        pg.add(tile_screen(x + 3, y + 4, cw - 18, 200, fn))
        pg.add(T(x + 2, y + 234, nm, 16, 800, WHITE, "b"))
        pg.add(PS(x + 2, y + 254, line, cw - 18, 13, 1.3, 600, FJORD_P))
    # byggeklossene
    kx, ky = 30, 1140
    pg.add(T(kx, ky, "Byggeklossene", 26, 800, WHITE, "b"))
    pg.add(R(kx, ky + 14, 715, 216, 12, GRASS))
    ki_iso = Iso(pg, kx + 74, ky + 58, 22)
    pg.add(pallet(ki_iso, 0, 0, 4))
    pg.add(T(kx + 40, ky + 142, "Palle", 14, 800, INK) + T(kx + 40, ky + 160, "4 kasser", 13, 700, INK))
    v1 = Iso(pg, kx + 180, ky + 50, 26)
    pg.add(van(v1, 0, 0, "+y", 4, 0, FJORD))
    pg.add(T(kx + 130, ky + 142, "På vei", 14, 800, INK) + T(kx + 130, ky + 160, "4 kasser", 13, 700, INK))
    v2 = Iso(pg, kx + 290, ky + 50, 26)
    pg.add(van(v2, 0, 0, "-y", 0, 4, FALU))
    pg.add(T(kx + 240, ky + 142, "I kø", 14, 800, INK) + T(kx + 240, ky + 160, "4 du skylder", 13, 700, INK))
    for i, role in enumerate(ROLES):
        bx = kx + 400 + i * 80
        pg.add(mini_building(role, bx, ky + 60 + (10 if role != "Fabrikk" else 12), 9, True))
        pg.add(T(bx - 26, ky + 142, role, 13, 800, INK))
    pg.add(T(kx + 374, ky + 160, "Formen på bygget sier Rollen", 13, 700, INK))
    pg.add(ki_badge(kx + 40, ky + 178, "KI-merket: sekskant og tekst, alltid på fasaden", 22, size=14))
    # stor modell: byen som helhet, gir arket et sted å lande
    ax = 30 + 3 * cw + 16
    ay = 816
    aw = 2000 - 30 - ax
    ah = 560
    clip = pg.clip(ax, ay, aw, ah, 14)
    iso = Iso(pg, ax + aw * 0.44, ay + 236, 22)
    sc = R(ax, ay, aw, ah, 0, GRASS)
    sc += f'<polygon points="{ax + aw},{ay + 220} {ax + aw},{ay + ah} {ax + 500},{ay + ah}" fill="{FJORD}"/>'
    sc += waves(iso, 12, -8, 24, 6, 18)
    sc += iso.poly([(3, -22, 0), (4.5, -22, 0), (4.5, 22, 0), (3, 22, 0)], ASPHALT)
    sc += iso.line((3.75, -22, 0), (3.75, 22, 0), "#E7EFF1", 1.2, "5 6")
    pieces = []
    for a, b, h in [(-3.5, -12, 1.4), (-4, -7, 1.6), (-3.2, -2, 1.3), (-3.6, 3, 1.5), (-2.5, 8, 1.5), (5.4, -9, 1.3), (5.4, -2, 1.4), (5.6, 4, 1.2), (5, 9, 1.4), (-6, 1, 1.7), (-6, -5, 1.5), (-5, 6, 1.5)]:
        pieces.append((a + b, spruce(iso, a, b, h)))
    pieces.append((-14, b_fabrikk(iso, -0.4, -13.4)))
    pieces.append((-7, b_distributor(iso, -1, -7.6)))
    h_, dx, dy = hall_cut(iso, -1.4, -2, 3, 4, 12, "Grossist", None, "Grossist", None, 17)
    pieces.append((0, h_))
    pieces.append((6, b_detaljist(iso, 0.4, 5.8)))
    for k, p in sorted(pieces, key=lambda t: t[0]):
        sc += p
    sc += van(iso, 3.15, -6, "+y", 4, 0, FJORD)
    sc += van(iso, 3.85, 6, "-y", 0, 4, FALU)
    sc += fog(pg, [(ax + aw, ay, 150, 70, 0.9), (ax, ay + ah, 130, 60, 0.8)])
    pg.add(f'<g clip-path="{clip}">{sc}</g>')
    pg.add(R(ax + 20, ay + ah - 124, 560, 104, 10, WHITE))
    pg.add(T(ax + 38, ay + ah - 88, "Samme modell på alle sider", 24, 800, INK, "b"))
    pg.add(PS(ax + 38, ay + ah - 64, "Telleregelen, tåka og KI-merket følger med overalt. Studentene møter huset, lærerne kartet, og tabellen står alltid ved siden av.", 520, 14, 1.32, 600, MUTED))
    pg.write()
