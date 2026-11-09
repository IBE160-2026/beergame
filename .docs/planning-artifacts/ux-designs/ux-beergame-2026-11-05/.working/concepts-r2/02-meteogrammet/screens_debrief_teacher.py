"""07 debrief og 08 lærerens oversikt."""
from d02lib import *
from screens_core import G, BARE, ALLE, K

SEATS = {r: Seat(r) for r in ROLES}
DEM = FX["spill17"]["serier"]["demand"]
KL = FX["klasse"]


def sec_title(d, x, y, n, title, width):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    d.t(x, y, str(n), 22, 700, INK)
    return d.para(x + 24, y, title, width - 24, 22, 27, 600, INK)


def demand_band(d, ax, y0, h, scale, label=True, ls=14):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(1):.1f} {base:.1f}"
    for w in range(1, 37):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(36):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(1), base, ax.xr(36), base, HAIR2, 1)


def build_07():
    d = Doc("07-debrief", 2100, 1200, "Prognose, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, alle fire Rollers ordre, ditt øyeblikk i Uke 11, og quiz. Delt skjerm med fire meteogrammer.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)

    # Steg 1
    x, w = 40, 340
    y = 104
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 32, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(x + 30, w - 30, 1, 36)
    Y = grid(d, ax, y + 42, 96, -40, 30, (-40, 0, 20), 13)
    net_area(d, ax, y + 42, 96, G.net, 1, 36)
    xaxis(d, ax, y + 156, [1, 12, 24, 36])
    d.t(x, y + 192, "Hvorfor svingte lageret ditt?", 15, 600, INK)
    d.rect(x, y + 202, w, 112, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 226, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.", w - 24, 15, 20)
    d.button(x, y + 324, w, 44, "Send Forklaring", size=15)
    d.circle(x + 7, y + 391, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 396, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 14, 19, fill=INK2)

    # Steg 2: klimaks
    x2, w2 = 420, 680
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 26
    h = 366
    scale = 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    bars = lambda k: G.order(k)
    # Din ordre som tynne stolper over båndet
    bw = 5
    for k in range(1, 37):
        d.rect(ax2.xc(k) - bw / 2, y0 + h - bars(k) * u, bw, bars(k) * u, INK)
    # Ordre inn som linje
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    # etiketter
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundeetterspørsel: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 42, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 92, "P4, P6", 13, 400, INK3)

    # Steg 3
    x3, w3 = 1140, 920
    sec_title(d, x3, y, 3, "Oppstrøms vokser svingningene, og de kommer senere", w3)
    ax3 = Axis(x3 + 130, w3 - 130 - 90, 1, 36)
    order = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    y3 = y + 24
    rh = 86
    fs = 32
    onset = {}
    for i, r in enumerate(order):
        yy = y3 + i * (rh + 6)
        S = SEATS[r]
        ou = rh / fs
        d.line(ax3.x0, yy, ax3.x1, yy, HAIR, 1)
        order_bars(d, ax3, yy, rh, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        d.t(x3, yy + rh - 24, r, 16, 600, INK)
        d.t(x3, yy + rh - 6, NAVN[r] if r != "Grossist" else "Sara, du", 14, 400, INK2)
        d.t(ax3.x1 + 90, yy + rh - 6, fx1(K["forsterkning"][r]), 22, 700, INK, "end",
            'style="font-variant-numeric:lining-nums proportional-nums"')
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rh - S.order(first) * ou, first)
    # forskyvningen: første Uke med ordre på 10 eller mer
    pts = [onset[r] for r in order]
    d.path("M" + " L".join(f"{a:.1f} {b - 3:.1f}" for a, b, _ in pts), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 4, RED, PAPER, 1.5)
    for r in order:
        a, b, k = onset[r]
        d.t(a - 8, b - 6, f"Uke {k}", 13, 600, RED, "end")
    yd = y3 + 4 * (rh + 6)
    demand_band_h = rh * 0.5
    demand_band(d, ax3, yd, 8 * rh / fs + 1, 8)
    d.t(x3, yd + 18, "Kundene", 16, 600, INK)
    d.t(ax3.xc(30), yd + 15, "4, så 8", 14, 600, BLUE, "middle")
    xaxis(d, ax3, yd + 8 * rh / fs + 19, [1, 5, 10, 15, 20, 25, 30, 36])
    d.t(x3 + 130, yd + 8 * rh / fs + 40, "Rødt punkt: første Uke med ordre på 10 eller mer. Samme skala i alle rader. Tallet til høyre er Forsterkning. P5.", 14, 400, INK2)

    # Rad 2
    yb = 700
    # Steg 4
    x4, w4 = 40, 1100
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    mm = meteo(d, G, x4, yb + 18, 340, 11, 24, left=30, hn=150, hf=56, gap=16, t_flow="", t_ord="Din ordre", t_net="Dette så du", futnote=None)
    d.t(x4, mm["yflow"] - 7, f"Levering {G.levering(11)}, ordre inn {G.inn(11)}", 13, 600, INK)

    tx = x4 + 372
    tw = 320
    d.t(tx, yb + 32, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb + 54, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 15, 20)
    d.t(tx, ny + 14, "Dette kostet det senere", 15, 600, INK)
    late = G.kostsum(36) - G.kostsum(24)
    assert all(G.rest[k - 1] == 0 for k in range(25, 37))
    ny = d.para(tx, ny + 36, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}, og i Uke {G.lager.index(max(G.lager)) + 1} sto du med lager {max(G.lager)}. Lager i Uke 25 til 36 kostet {nf(late)} kr.", tw, 15, 20)
    d.t(tx, ny + 14, "Dette så de andre i Uke 11", 15, 600, INK)
    yy = ny + 36
    for r in ("Detaljist", "Distributør", "Fabrikk"):
        S = SEATS[r]
        d.t(tx, yy, f"{NAVN[r]}, {r}", 14, 400, INK)
        st = f"lager {S.lager[10]}" if S.net(11) >= 0 else f"restordre {S.rest[10]}"
        d.t(tx + tw, yy, f"{st}, ordre inn {S.inn(11)}", 14, 400, INK2, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 25
    yy += 8
    d.para(tx, yy, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Mikkel fikk 24 fra deg uten å vite hvorfor.»", tw, 14, 19, fill=INK2)

    # Referanse
    rx = x4 + 730
    rw = 370
    d.t(rx, yb + 32, "Samme kjede, Sara teller alt på vei", 15, 600, INK)
    d.t(rx, yb + 52, "Simulert. Viser sammenhengen, ikke en fasit.", 14, 400, INK2)
    ax4 = Axis(rx + 30, rw - 30, 1, 36)
    y4 = yb + 66
    hh = 170
    Y4 = grid(d, ax4, y4, hh, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax4, y4, hh, G.net, 1, 36)
    d.path("M" + " L".join(f"{ax4.xc(k):.1f} {Y4(BARE.net(k)):.1f}" for k in range(1, 37)), stroke=INK, sw=1.6)
    d.t(ax4.xc(36), Y4(BARE.net(33)) - 8, "Simulert", 14, 600, INK, "end")
    d.t(ax4.xc(12), Y4(-30), "Spill 17", 14, 600, RED, "end")
    xaxis(d, ax4, y4 + hh + 18, [1, 12, 24, 36])
    B = FX["bare_sara_teller_paa_vei"]
    rows = [("", "Spill 17", "Simulert"),
            ("Din ordre, Uke 11", "24", str(BARE.order(11))),
            ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"])),
            ("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"])),
            ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]))]
    yy = y4 + hh + 46
    for i, row in enumerate(rows):
        bold = 600 if i == 0 else 400
        d.t(rx, yy, row[0], 14, bold, INK)
        d.t(rx + 268, yy, row[1], 14, bold, INK, "end")
        d.t(rx + rw, yy, row[2], 14, bold, INK, "end")
        d.line(rx, yy + 7, rx + rw, yy + 7, HAIR, 1)
        yy += 25
    d.t(rx, yy + 12, "P3, P7, P8", 13, 400, INK3)

    # Steg 5
    x5, w5 = 1180, 420
    sec_title(d, x5, yb, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb + 34, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 16, 22, 600)
    opts = [(sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)]
    yy = ny + 6
    for lab, st in opts:
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(x5, yy, w5, 42, PAPER, col, 1.4 if st else 1, 6)
        d.t(x5 + 14, yy + 27, lab, 16, 600, INK)
        if st == "wrong":
            d.t(x5 + w5 - 14, yy + 27, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if st == "right":
            d.t(x5 + w5 - 14, yy + 27, "Riktig", 14, 600, INK, "end")
        yy += 50
    ny = d.para(x5, yy + 10, "−13 er lager minus restordre. Da mangler det du allerede har bestilt: 0 − 13 + 16 = 3.", w5, 15, 20)
    d.t(x5, ny + 8, "Det samme regnestykket står i Uke 11 i din egen graf.", 14, 400, INK2)
    d.t(x5, ny + 34, "P3", 13, 400, INK3)

    # Delt skjerm
    xs, ws = 1640, 420
    sec_title(d, xs, yb, " ", "Delt skjerm: fire meteogrammer", ws)
    fy = yb + 18
    d.rect(xs, fy, ws, 372, PAPER, HAIR2, 1.4, 8)
    axs = Axis(xs + 92, ws - 106, 1, 36)
    yr = fy + 14
    rh2 = 66
    for r in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        S = SEATS[r]
        Ys = yscale(yr, rh2, -70, 60)
        d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
        net_area(d, axs, yr, rh2, S.net, 1, 36, -70, 60, lw=1.6)
        d.t(xs + 12, Ys(0) - 2, r, 14, 600, INK)
        d.t(xs + 12, Ys(0) + 15, NAVN[r], 13, 400, INK2)
        yr += rh2 + 6
    demand_band(d, axs, yr, 20, 8)
    d.t(xs + 12, yr + 16, "Kundene", 14, 600, INK)
    xaxis(d, axs, yr + 38, [1, 12, 24, 36])
    d.para(xs, fy + 396, "Netto lager, samme skala i alle fire. Gruppa ser dette sammen, mens hver student ser sitt eget steg på telefonen.", ws, 14, 19, fill=INK2)
    d.demodata(2060, 1188, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def heat(v, cap=45):
    """Divergerende: blå over null, rød under, grå midtpunkt."""
    a = min(abs(v) / cap, 1.0) ** 0.75
    n = (238, 241, 244)
    pole = (43, 108, 163) if v > 0 else (181, 66, 58)
    if abs(v) <= 1:
        a = 0
    c = tuple(int(n[i] + (pole[i] - n[i]) * a) for i in range(3))
    return "#%02X%02X%02X" % c


def strip(d, x, y, sp, cw=4.3, lane=4, roles=("Fabrikk", "Distributør", "Grossist", "Detaljist")):
    for i, r in enumerate(roles):
        vals = sp["netto_lager"][r]
        for k, v in enumerate(vals):
            d.rect(x + k * cw, y + i * (lane + 0.5), cw + 0.2, lane, heat(v))


def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Prognose, Oversikt for Faglærer",
            "60 Klassespill på én skjerm med netto lager per Rolle som stripe, status, hvem spillet venter på, KI-seter og trakten.")
    fx0, fy0, fw, fh = 80, 30, 1440, 940
    d.rect(fx0, fy0, fw, fh, PAPER, HAIR2, 1.2, 8)
    X = fx0 + 24
    d.t(X, fy0 + 36, "Oversikt", 24, 700, INK)
    d.t(X + 104, fy0 + 36, "class-of-1994, IBE160", 15, 400, INK2)
    d.t(fx0 + fw - 24, fy0 + 36, "Spillfrist ti. 8. des", 15, 400, INK2, "end")

    spill = KL["spill"]
    near = [s for s in spill if s["status"] == "venter"]
    near.sort(key=lambda s: -s["ventet_timer"])
    top = near[0]
    # Hva skjer nå
    yn = fy0 + 74
    d.t(X, yn, "Hva skjer nå", 16, 600, INK)
    y = yn + 26
    d.rect(X, y - 18, 690, 30, REDF, None, 1, 4)
    d.t(X + 10, y + 2, f"Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 15, 600, INK)
    d.button(X + 590, y - 15, 94, 24, "Send Melding", size=13)
    y += 28
    others = near[1:]
    d.t(X + 10, y, "Venter også: " + ", ".join(f"spill {s['spill']} {s['navn']} {s['ventet_timer']} t" for s in others), 14, 400, INK)
    y += 22
    pa = [s for s in spill if s["status"] == "pauset"]
    d.t(X + 10, y, "Pause: " + ", ".join(f"spill {s['spill']}" for s in pa) + f", fortsetter {pa[0]['fortsetter']}.", 14, 400, INK)
    y += 22
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    kisum = sum(s["ki_seter"] for s in spill)
    F = KL["ferdige"]
    FJ = KL["fjoraaret"]
    d.t(X + 10, y, f"{kisum} KI-spillere i {ki} spill. Median kjedekost i ferdige spill: {nf(F['kjedekost']['median'], 0)} kr (fjoråret {nf(FJ['median_kjedekost'], 0)} kr).", 14, 400, INK)

    # Trakt
    tx = fx0 + 800
    d.t(tx, yn, "Trakten", 16, 600, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    # kolonnerad: bar + tall
    col_w = (fx0 + fw - 24 - tx) / 7
    for i, (lab, v) in enumerate(steps):
        xx = tx + i * col_w
        hh = 44 * v / steps[0][1]
        base = yn + 56
        d.rect(xx, base - hh, col_w - 8, hh, ORD if v else HAIR)
        d.t(xx, base + 18, v, 15, 600, INK)
        for j, ln in enumerate(wrap(lab, col_w - 6, 13)):
            d.t(xx, base + 34 + j * 15, ln, 13, 400, INK2)

    # Filter
    yf = fy0 + 212
    d.line(X, yf - 20, fx0 + fw - 24, yf - 20, HAIR, 1)
    counts = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    labs = [("Alle", len(spill)), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]), ("Ferdig", counts["ferdig"]), ("Med KI-spiller", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s = f"{lab} {c}"
        wd = text_w(s, 14) + 22
        d.rect(xx, yf - 13, wd, 26, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 5, s, 14, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 8
    # forklaring til stripa
    lx = fx0 + 700
    d.t(lx, yf + 5, "Stripa: netto lager, Uke 1 til 36. Fabrikk øverst, Detaljist nederst.", 13, 400, INK2)
    sx = fx0 + fw - 24 - 150
    for i, v in enumerate((-40, -20, 0, 20, 40)):
        d.rect(sx + i * 22, yf - 8, 20, 12, heat(v))
    d.t(sx - 6, yf + 5, "Restordre", 13, 400, INK2, "end")
    d.t(sx + 112, yf + 5, "Lager", 13, 400, INK2)

    # Rader
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    ordered = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"] if s["status"] == "pågår" else s["spill"]))
    ncol = 30
    colw = (fw - 48 - 30) / 2
    yh = yf + 36
    rowh = 21
    for c in range(2):
        cx = X + c * (colw + 30)
        heads = [(0, "Spill", "start"), (44, "Status", "start"), (102, "Netto lager", "start"), (288, "Uke", "end"), (352, "Kost, kr", "end"), (396, "KI", "end"), (412, "Venter på" if c == 0 else "Forsterkning, Fabrikk", "start")]
        for off, h, a in heads:
            d.t(cx + off, yh, h, 13, 600, INK2, a)
        d.line(cx, yh + 6, cx + colw, yh + 6, HAIR2, 1)
        extra = 0
        for i in range(ncol):
            sp = ordered[c * ncol + i]
            if c == 0 and sp["status"] == "ferdig" and not extra:
                extra = rowh + 2
                yy = yh + 22 + i * rowh + 2
                d.line(cx, yy - 13, cx + colw, yy - 13, HAIR2, 1)
                d.t(cx, yy + 2, "Ferdige", 13, 600, INK2)
                d.t(cx + 412, yy + 2, "Forsterkning, Fabrikk", 13, 600, INK2)
            y = yh + 22 + i * rowh + extra
            isnear = sp["spill"] == top["spill"]
            if isnear:
                d.rect(cx - 6, y - 15, colw + 12, rowh, REDF, None, 1, 3)
            d.t(cx, y, sp["spill"], 14, 600, INK)
            d.t(cx + 44, y, status_txt(sp), 14, 600 if sp["status"] in ("venter", "pauset") else 400, INK if sp["status"] != "ferdig" else INK2)
            strip(d, cx + 102, y - 14, sp, cw=4.5, lane=3.8)
            d.t(cx + 288, y, sp["uke"], 14, 400, INK, "end")
            d.t(cx + 352, y, nf(sp["kjedekost"], 0), 14, 400, INK, "end")
            d.t(cx + 396, y, sp["ki_seter"] if sp["ki_seter"] else "", 14, 400, INK, "end")
            if sp["status"] == "venter":
                d.t(cx + 412, y, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", 14, 600 if isnear else 400, INK)
                d.t(cx + colw, y, "Melding", 13, 600, BLUE, "end", 'text-decoration="underline"')
            elif sp["status"] == "pauset":
                d.t(cx + 412, y, f"Fortsetter {sp['fortsetter']}", 14, 400, INK2)
            elif sp["status"] == "ferdig":
                d.t(cx + 412, y, fx1(sp["forsterkning"]["Fabrikk"]), 14, 400, INK2)
    d.demodata(fx0 + fw - 24, fy0 + fh - 8, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
