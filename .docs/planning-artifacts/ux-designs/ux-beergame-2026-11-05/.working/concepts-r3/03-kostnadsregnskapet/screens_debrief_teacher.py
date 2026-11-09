"""07 Debrief og 08 lærerens oversikt."""
from e03kost import *
from screens_core import G, BARE, ALLE, K, PN

SEATS = {r: Seat(r) for r in ROLES}
DEM = FX["spill17"]["serier"]["demand"]
KL = FX["klasse"]


def sec_title(d, x, y, n, title, width):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    if n:
        d.t(x, y, str(n), 22, 700, INK)
        return d.para(x + 24, y, title, width - 24, 22, 27, 600, INK)
    return d.para(x, y, title, width, 22, 27, 600, INK)


def demand_band(d, ax, y0, h, scale):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(1):.1f} {base:.1f}"
    for w in range(1, 37):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(36):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(1), base, ax.xr(36), base, HAIR2, 1)


def role_cost_matrix(d, x, y, w, ls=13, rh=30, num_w=78, label_w=104, src="07-rolle-uke"):
    """Rolle × uke i kroner: hver celle er én Rolles kostnad den uka, farget etter art og beløp.
    Til høyre: summene som tall. Under: kjedens kostnad per uke, på samme kolonner."""
    cols_x = x + label_w
    grid_w = w - label_w - 3 * num_w
    ax = Axis(cols_x, grid_w, 1, 36)
    cw = ax.slot - 1
    # kolonnehoder
    for k in (1, 6, 12, 18, 24, 30, 36):
        d.t(ax.xc(k), y, k, ls - 1, 400, INK3, "middle")
    nx = [ax.x1 + num_w * (i + 1) for i in range(3)]
    for c, h in zip(nx, ("Lager", "Restordre", "Sum")):
        d.t(c, y, h, ls, 600, INK2, "end")
    yy = y + 10
    for r in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        S = SEATS[r]
        d.t(x, yy + rh / 2 + ls * 0.36, r, ls, 700 if r == "Grossist" else 400, INK)
        for k in range(1, 37):
            kind = "rk" if S.rest[k - 1] else "lk"
            v = S.wc(k)
            DRAWN.append((src, r, k, "Ukekost", v))
            fill, _ = cost_fill(kind, v)
            d.rect(ax.xl(k) + 0.5, yy + 2, cw, rh - 4, fill if fill != PAPER else TINT)
        vals = (S.cum_lk(36), S.cum_rk(36), S.kostsum(36))
        for c, v in zip(nx, vals):
            d.t(c, yy + rh / 2 + ls * 0.36, nf(v), ls, 600 if c == nx[2] else 400, INK, "end")
        d.line(x, yy + rh, nx[2], yy + rh, HAIR, 1)
        yy += rh
    tl = sum(SEATS[r].cum_lk(36) for r in ROLES)
    tr = sum(SEATS[r].cum_rk(36) for r in ROLES)
    d.t(x, yy + 22, "Kjeden", ls, 700, INK)
    for c, v in zip(nx, (tl, tr, tl + tr)):
        d.t(c, yy + 22, nf(v), ls, 700, INK, "end")
    assert abs(tl + tr - K["kjedekost"]) < 1e-9
    # kjedens kostnad per uke, stablet: lager nederst, restordre over
    hb = 60
    yb = yy + 52
    kmax = 170
    u = hb / kmax
    for k in range(1, 37):
        lk = sum(SEATS[r].lk(k) for r in ROLES)
        rk = sum(SEATS[r].rk(k) for r in ROLES)
        bw = ax.slot - 2
        d.rect(ax.xc(k) - bw / 2, yb + hb - lk * u, bw, lk * u, BLUE)
        if rk:
            d.rect(ax.xc(k) - bw / 2, yb + hb - lk * u - rk * u - 1, bw, rk * u, RED)
    d.line(ax.x0, yb + hb, ax.x1, yb + hb, HAIR2, 1)
    d.t(ax.x1 + 8, yb + 12, "Kjedens kostnad", ls, 600, INK)
    d.t(ax.x1 + 8, yb + 12 + ls + 4, "per uke, kr", ls, 400, INK2)
    pk = max(range(1, 37), key=lambda k: sum(SEATS[r].wc(k) for r in ROLES))
    pv = sum(SEATS[r].wc(k) for r in ROLES for k in (pk,))
    d.t(ax.xc(pk), yb + hb - pv * u - 5, f"Uke {pk}: {nf(pv)}", ls - 1, 600, INK, "middle")
    return yb + hb, ax


def build_07():
    d = Doc("07-debrief", 2100, 1200, "Kostnadsregnskapet, Gruppedebrief i fem steg",
            "Forklaring med egen regning, avsløring av etterspørselen, alle fire Rollers ordre og kjeden med fire ledd, "
            "ditt øyeblikk i Uke 11 med kostnad på snittet og simulert referanse, kjedens kostnad som matrise Rolle × uke, quiz, og delt skjerm med fire regnskap.")
    d.t(40, 44, "Debrief, Spill 17: kjeden betalte 2 266,00 kr. Hvorfor?", 28, 600, INK)

    # Steg 1
    x, w = 40, 330
    y = 104
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 34, "Du betalte", 14, 400, INK2)
    d.t(x, y + 66, f"{nf(G.kostsum(36))} kr", 30, 700, INK, extra=PN)
    cost_split_bar(d, x, y + 80, w, G.cum_lk(36), G.cum_rk(36), h=8, labels=False)
    d.t(x, y + 104, f"Lager {nf(G.cum_lk(36))} kr", 13, 400, INK2)
    d.t(x + w, y + 104, f"Restordre {nf(G.cum_rk(36))} kr", 13, 400, INK2, "end")
    ax = Axis(x + 26, w - 26, 1, 36)
    yk, hk = y + 140, 56
    for v in (0, 20, 40):
        d.line(ax.x0, yk + hk - v * hk / 40, ax.x1, yk + hk - v * hk / 40, HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 5, yk + hk - v * hk / 40 + 4, v, 12, 400, INK3, "end")
    cost_bars(d, ax, yk, hk, G, 1, 36, 40)
    xaxis(d, ax, yk + hk + 16, [1, 12, 24, 36], None, 12)
    d.t(x, yk - 6, "Kostnad per uke, kr", 13, 600, INK)
    d.t(x, y + 244, "Hvorfor ble regningen din slik?", 15, 600, INK)
    d.rect(x, y + 248, w, 104, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 272, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Da alt kom, ble det liggende på lager.", w - 24, 15, 20)
    d.button(x, y + 364, w, 44, "Send Forklaring", size=15)
    d.circle(x + 7, y + 431, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 436, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 14, 19, fill=INK2)

    # Steg 2: klimaks
    x2, w2 = 410, 560
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0, h, scale = y + 54, 330, 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    for k in range(1, 37):
        d.rect(ax2.xc(k) - 2.5, y0 + h - G.order(k) * u, 5, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundeetterspørsel: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(18) + 6, y0 + h - 13.5 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 44, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20)
    d.t(x2, y0 + h + 110, "P4, P6", 13, 400, INK3)

    # Steg 3: alle fire, og kjeden med fire ledd
    x3, w3 = 1010, 700
    sec_title(d, x3, y, 3, "Oppstrøms vokser svingningene, og de kommer senere", w3)
    d.t(x3, y + 40, "Kjeden i Uke 18: alle fire står i restordre samtidig", 14, 600, INK)
    chain_full(d, x3, y + 50, w3, SEATS, wk=18, ls=13, cost=False, kunde=True, node_w=62, names=False)
    ax3 = Axis(x3 + 104, w3 - 104 - 64, 1, 36)
    order = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    y3 = y + 166
    rh, fs = 62, 32
    onset = {}
    for i, r in enumerate(order):
        yy = y3 + i * (rh + 6)
        S = SEATS[r]
        d.line(ax3.x0, yy, ax3.x1, yy, HAIR, 1)
        order_bars(d, ax3, yy, rh, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        d.t(x3, yy + rh - 22, r, 15, 600, INK)
        d.t(x3, yy + rh - 4, NAVN[r] if r != "Grossist" else "Sara, du", 13, 400, INK2)
        d.t(ax3.x1 + 64, yy + rh - 4, fx1(K["forsterkning"][r]), 22, 700, INK, "end", PN)
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rh - S.order(first) * rh / fs, first)
    pts = [onset[r] for r in order]
    d.path("M" + " L".join(f"{a:.1f} {b - 3:.1f}" for a, b, _ in pts), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 4, RED, PAPER, 1.5)
        d.t(a - 8, b - 6, f"Uke {k}", 13, 600, RED, "end")
    yd = y3 + 4 * (rh + 6)
    demand_band(d, ax3, yd, 8 * rh / fs + 1, 8)
    d.t(x3, yd + 16, "Kundene", 15, 600, INK)
    xaxis(d, ax3, yd + 8 * rh / fs + 19, [1, 5, 10, 15, 20, 25, 30, 36])
    d.t(x3, yd + 8 * rh / fs + 42, "Rødt punkt: første Uke med ordre på 10 eller mer. Samme skala i alle rader. Tallet til høyre er Forsterkning. P5.", 13, 400, INK2)

    # Delt skjerm: fire regnskap
    xs, ws = 1750, 310
    sec_title(d, xs, y, None, "Delt skjerm: fire regnskap, samme skala", ws)
    fy = y + 46
    d.rect(xs, fy, ws, 404, PAPER, HAIR2, 1.4, 8)
    axs = Axis(xs + 14, ws - 28, 1, 36)
    yr = fy + 24
    for r in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        S = SEATS[r]
        d.t(xs + 14, yr, f"{r}, {NAVN[r]}", 13, 600, INK)
        d.t(xs + ws - 14, yr, f"{nf(S.kostsum(36))} kr", 13, 600, INK, "end")
        cost_bars(d, axs, yr + 6, 50, S, 1, 36, 64)
        sc = (ws - 28) / 700
        d.rect(axs.x0, yr + 62, S.cum_lk(36) * sc, 6, BLUE)
        d.rect(axs.x0 + S.cum_lk(36) * sc + 1, yr + 62, S.cum_rk(36) * sc, 6, RED)
        yr += 92
    d.para(xs, fy + 426, "Kostnad per uke og summen delt i lager og restordre. Gruppa ser alle fire sammen, mens hver student ser sitt eget steg på telefonen.", ws, 13, 18, fill=INK2)

    # Rad 2
    yb = 690
    x4, w4 = 40, 1650
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei, og det kostet senere.", w4)
    mm = meteo3(d, G, x4, yb + 20, 320, 11, 24, hk=34, hn=104, ho=34, gap=10, left=28, sidev=40, ls=12, kmax=40,
                t_cost="Kostnad per uke", t_net="Dette så du", t_ord="Din ordre", vlabel=False)
    tx, tw = x4 + 350, 290
    d.t(tx, yb + 34, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb + 56, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 14, 19)
    d.t(tx, ny + 10, "Dette kostet det senere", 15, 600, INK)
    rk_later = G.kostsum(24) - G.kostsum(11)
    lk_late = G.kostsum(36) - G.kostsum(24)
    ny = d.para(tx, ny + 32, f"{G.levering(15)} av de 24 kom i Uke 15. Restordre i Uke 12 til 24 kostet {nf(rk_later)} kr. Så kom alt, og lager i Uke 25 til 36 kostet {nf(lk_late)} kr.", tw, 14, 19)
    d.t(tx, ny + 10, "Dette så de andre i Uke 11", 15, 600, INK)
    yy = ny + 32
    for r in ("Detaljist", "Distributør", "Fabrikk"):
        S = SEATS[r]
        st = f"lager {S.lager[10]}" if S.net(11) >= 0 else f"restordre {S.rest[10]}"
        d.t(tx, yy, f"{NAVN[r]}, {r}", 14, 400, INK)
        d.t(tx + tw, yy, f"{st}, ordre inn {S.inn(11)}", 14, 400, INK2, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 23
    d.para(tx, yy + 8, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Mikkel fikk 24 fra deg uten å vite hvorfor.»", tw, 13, 18, fill=INK2)

    # Kostnad på snittet og simulert referanse
    sx, sw = tx + tw + 30, 270
    avg, steady, paid = avg_cost(G)
    d.t(sx, yb + 34, "Kostnad på snittet mot det du betalte", 15, 600, INK)
    d.para(sx, yb + 56, f"Netto lager var i snitt {nf(avg, 1)}. Jevn drift der ville kostet {nf(steady)} kr på 36 uker. Du betalte {nf(paid)} kr: svingningen kostet, ikke snittet. Et regnestykke, ikke et mål.", sw, 14, 19)
    yt = yb + 166
    d.t(sx, yt, "Samme kjede, Sara teller alt på vei", 15, 600, INK)
    d.t(sx, yt + 19, "Simulert. Viser sammenhengen, ikke en fasit.", 13, 400, INK2)
    B = FX["bare_sara_teller_paa_vei"]
    rows = [("", "Spill 17", "Simulert"),
            ("Grossist, lager", nf(G.cum_lk(36)), nf(BARE.cum_lk(36))),
            ("Grossist, restordre", nf(G.cum_rk(36)), nf(BARE.cum_rk(36))),
            ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"])),
            ("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"])),
            ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]))]
    assert abs(BARE.kostsum(36) - B["kost_per_rolle"]["Grossist"]) < 1e-9
    yy = yt + 46
    for i, row in enumerate(rows):
        bold = 600 if i in (0, 4) else 400
        d.t(sx, yy, row[0], 14, bold, INK)
        d.t(sx + 186, yy, row[1], 14, bold, INK, "end")
        d.t(sx + sw, yy, row[2], 14, bold, INK, "end")
        d.line(sx, yy + 7, sx + sw, yy + 7, HAIR, 1)
        yy += 24
    d.t(sx, yy + 10, "P3, P7, P8", 13, 400, INK3)

    # Kjedens kostnad
    kx = sx + sw + 34
    kw = x4 + w4 - kx
    d.t(kx, yb + 34, "Kjedens kostnad", 15, 600, INK)
    d.t(kx, yb + 70, f"{nf(K['kjedekost'])} kr", 30, 700, INK, extra=PN)
    d.para(kx + 210, yb + 54, "Målet var lavest kostnad for hele kjeden. Rødt band flytter seg oppstrøms og kommer senere.", kw - 200, 14, 19, fill=INK2)
    yend, axm = role_cost_matrix(d, kx, yb + 104, kw, ls=13, rh=30, num_w=68, label_w=86)
    d.para(kx, yend + 24, "Celle: én Rolles kostnad den uka. Blått lager, rødt restordre, mørkere er dyrere, med samme kronegrenser for begge. P5, P8.", kw, 13, 18, fill=INK2)

    # Steg 5
    x5, w5 = 1730, 330
    sec_title(d, x5, yb, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb + 34, "Netto lager er −20 én uke og +20 uka etter. Hva koster de to ukene til sammen?", w5, 16, 22, 600)
    opts = [("0,00 kr: snittet er null", "wrong"), ("15,00 kr", None), ("30,00 kr", "right"), ("40,00 kr", None)]
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
    assert wcost(-20) + wcost(20) == 30
    ny = d.para(x5, yy + 8, "Kostnaden regnes for hver uke, ikke på snittet. 20 i restordre × 1,00 + 20 på lager × 0,50 = 30,00 kr. Uker på hver side av null veier ikke hverandre opp.", w5, 15, 20)
    d.t(x5, ny + 12, "Det samme ser du på V-en i din egen graf. P8.", 13, 400, INK2)
    d.demodata(2060, 1190, "Demodata. Simulerte tall er merket Simulert. Alle tall fra loggen.", 13, "end")
    d.save()


# ---------- 08 ----------
def game_week_cost(sp):
    """Kjedekostnad per uke for ett Klassespill, regnet fra ekte netto lager: positiv × 0,50, negativ × 1,00, summert over fire Roller."""
    n = len(sp["netto_lager"]["Grossist"])
    return [sum(wcost(sp["netto_lager"][r][i]) for r in ROLES) for i in range(n)]


def game_week_split(sp):
    n = len(sp["netto_lager"]["Grossist"])
    lk = [sum(max(sp["netto_lager"][r][i], 0) * LK for r in ROLES) for i in range(n)]
    rk = [sum(max(-sp["netto_lager"][r][i], 0) * RK for r in ROLES) for i in range(n)]
    return lk, rk


def class_aggregates():
    spill = KL["spill"]
    for sp in spill:
        assert abs(sum(game_week_cost(sp)) - sp["kjedekost"]) < 0.51, sp["spill"]
    fer = [s for s in spill if s["status"] == "ferdig"]
    mean_lk = [sum(game_week_split(s)[0][k] for s in fer) / len(fer) for k in range(36)]
    mean_rk = [sum(game_week_split(s)[1][k] for s in fer) / len(fer) for k in range(36)]
    ks = sorted(s["kjedekost"] for s in fer)
    med = (ks[len(ks) // 2] if len(ks) % 2 else (ks[len(ks) // 2 - 1] + ks[len(ks) // 2]) / 2)
    assert med == KL["ferdige"]["kjedekost"]["median"]
    return fer, mean_lk, mean_rk, med


def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Kostnadsregnskapet, Oversikt for Faglærer",
            "60 Klassespill på én skjerm: hva som haster, en matrisevegg med kjedekostnad per uke for hvert spill, "
            "klassens kostnadsbilde med kjedekostnad per spill mot fjoråret og kostnad per uke delt i lager og restordre, og trakten.")
    fx0, fy0, fw, fh = 40, 24, 1520, 952
    d.rect(fx0, fy0, fw, fh, PAPER, HAIR2, 1.2, 8)
    X = fx0 + 24
    spill = KL["spill"]
    cnt = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    d.t(X, fy0 + 38, "Oversikt", 26, 700, INK)
    d.t(X + 116, fy0 + 38, "class-of-1994, IBE160", 15, 400, INK2)
    d.t(X + 290, fy0 + 38, f"{cnt['ferdig']} ferdig · {cnt['pågår'] + cnt['pauset']} pågår (herav {cnt['pauset']} pauset) · {cnt['venter']} venter", 15, 600, INK)
    d.button(fx0 + fw - 24 - 180, fy0 + 16, 180, 34, "Send Melding til klassen", size=14)

    # Det som haster
    near = sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    y = fy0 + 70
    d.rect(X, y, 960, 36, REDF, None, 1, 4)
    d.t(X + 12, y + 23, f"Nær overtakelse: Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 15, 600, INK)
    d.button(X + 700, y + 5, 120, 26, f"Send Melding", size=13)
    d.button(X + 830, y + 5, 120, 26, "Pause spillet", primary=False, size=13)
    d.t(X, y + 58, "Venter også: " + ", ".join(f"spill {s['spill']} på {s['navn']} {s['ventet_timer']} t" for s in near[1:]) + ".", 14, 400, INK)
    pa = [s for s in spill if s["status"] == "pauset"]
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    d.t(X, y + 78, "Pause: " + ", ".join(f"spill {s['spill']}" for s in pa) + f", fortsetter {pa[0]['fortsetter']}. KI-spillere i {ki} spill.", 14, 400, INK)

    # Filter
    yf = y + 112
    labs = [("Alle", len(spill)), ("Venter", cnt["venter"]), ("Pause", cnt["pauset"]), ("Pågår", cnt["pågår"]), ("Ferdig", cnt["ferdig"]), ("Med KI-spiller", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s = f"{lab} {c}"
        wd = text_w(s, 13) + 20
        d.rect(xx, yf - 13, wd, 24, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 4, s, 13, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 6
    d.t(xx + 10, yf + 4, "Størrelse:", 13, 400, INK2)
    d.t(xx + 76, yf + 4, "Kjedekostnad", 13, 700, INK, extra='text-decoration="underline"')
    d.t(xx + 168, yf + 4, "Netto lager per Rolle", 13, 400, INK2)

    # Matriseveggen
    cw, rowh = 17.4, 10.2
    wx = X + 78
    yh = yf + 34
    cols = {"spill": X + 22, "status": X + 30, "uke": wx + 36 * cw + 26, "neste": wx + 36 * cw + 36, "ki": wx + 36 * cw + 216, "kost": wx + 36 * cw + 268}
    d.t(X, yh, "Spill", 12, 600, INK2)
    d.t(cols["status"], yh, "Status", 12, 600, INK2)
    for k in (1, 6, 12, 18, 24, 30, 36):
        d.t(wx + (k - 0.5) * cw, yh, k, 12, 400, INK3, "middle")
    d.t(cols["uke"], yh, "Uke", 12, 600, INK2, "end")
    d.t(cols["neste"], yh, "Venter på", 12, 600, INK2)
    d.t(cols["ki"], yh, "KI", 12, 600, INK2, "end")
    d.t(cols["kost"], yh, "Kjede, kr", 12, 600, INK2, "end")
    d.line(X, yh + 5, cols["kost"], yh + 5, HAIR2, 1)
    groups = [("Venter", sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])),
              ("Pause", [s for s in spill if s["status"] == "pauset"]),
              ("Pågår", sorted([s for s in spill if s["status"] == "pågår"], key=lambda s: -s["uke"])),
              ("Ferdig, sortert etter kjedekostnad", sorted([s for s in spill if s["status"] == "ferdig"], key=lambda s: s["kjedekost"]))]
    yy = yh + 10
    for gname, rows in groups:
        yy += 13
        d.t(X, yy, f"{gname} {len(rows)}", 12, 700, INK)
        yy += 3
        for sp in rows:
            wc = game_week_cost(sp)
            assert len(wc) == sp["uke"]
            if sp["spill"] == top["spill"]:
                d.rect(X - 6, yy - 0.5, cols["kost"] - X + 12, rowh + 1, REDF)
            d.t(cols["spill"], yy + rowh - 1.6, sp["spill"], 10, 600, INK, "end")
            d.t(cols["status"], yy + rowh - 1.6, status_txt(sp), 10, 400, INK if sp["status"] != "ferdig" else INK2)
            for k, v in enumerate(wc):
                fill, _ = chain_fill(v)
                d.rect(wx + k * cw, yy, cw - 1, rowh - 1, fill)
            if sp["uke"] < 36:
                xe = wx + sp["uke"] * cw
                d.line(xe, yy - 1, xe, yy + rowh, INK, 1.4)
            d.t(cols["uke"], yy + rowh - 1.6, sp["uke"], 10, 400, INK, "end")
            if sp["status"] == "venter":
                d.t(cols["neste"], yy + rowh - 1.6, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", 10, 600 if sp is top else 400, INK)
            elif sp["status"] == "pauset":
                d.t(cols["neste"], yy + rowh - 1.6, f"Fortsetter {sp['fortsetter']}", 10, 400, INK2)
            if sp["ki_seter"]:
                d.t(cols["ki"], yy + rowh - 1.6, f"KI {sp['ki_seter']}", 10, 400, INK, "end")
            d.t(cols["kost"], yy + rowh - 1.6, nf(sp["kjedekost"], 0), 10, 400, INK, "end")
            yy += rowh
    # forklaring til veggen
    ly = yy + 22
    d.t(X, ly, "Celle: kjedens kostnad den uka, fire Roller summert, kr.", 13, 400, INK2)
    lx = X + 360
    for i, (lab, col) in enumerate(zip(("under 20", "20–40", "40–80", "over 80"), M_STEPS)):
        d.rect(lx + i * 82, ly - 11, 14, 12, col)
        d.t(lx + i * 82 + 19, ly, lab, 13, 400, INK2)
    d.t(lx + 340, ly, "Strek: nå i pågående spill.", 13, 400, INK2)
    d.t(cols["kost"], ly, "Vis som tabell", 13, 600, BLUE, "end", 'text-decoration="underline"')

    # Klassens kostnadsbilde
    fer, mean_lk, mean_rk, med = class_aggregates()
    rx = fx0 + 1040
    rw = fx0 + fw - 24 - rx
    ry = fy0 - 20
    d.t(rx, ry + 112, "Kjedekostnad per spill", 17, 600, INK)
    d.para(rx, ry + 132, "Hvert punkt er ett spill. Fylt: ferdig. Ring: pågår, foreløpig kostnad. Bare Faglærer ser dette.", rw, 13, 17, fill=INK2)
    q = KL["ferdige"]["kjedekost"]
    FJ = KL["fjoraaret"]
    axk = (rx, rx + rw)
    kmax = 4000

    def kxp(v):
        return axk[0] + v / kmax * (axk[1] - axk[0])

    yb = ry + 260
    d.rect(kxp(q["q1"]), yb - 92, kxp(q["q3"]) - kxp(q["q1"]), 92, TINT)
    # stablede punkter, 100 kr per bøtte
    stacks = {}
    for s in sorted(spill, key=lambda s: s["kjedekost"]):
        b = int(s["kjedekost"] // 120)
        n = stacks.get(b, 0)
        stacks[b] = n + 1
        cx = kxp(b * 120 + 60)
        cy = yb - 6 - n * 9
        if s["status"] == "ferdig":
            d.circle(cx, cy, 3.6, INK)
        else:
            d.circle(cx, cy, 3.4, PAPER, INK, 1.2)
    d.line(axk[0], yb, axk[1], yb, HAIR2, 1)
    for v in (0, 1000, 2000, 3000, 4000):
        d.line(kxp(v), yb, kxp(v), yb + 4, HAIR2, 1)
        d.t(kxp(v), yb + 18, nf(v, 0), 12, 400, INK3, "middle")
    d.line(kxp(med), yb - 100, kxp(med), yb, INK, 1.4)
    d.t(kxp(med) - 4, yb - 104, f"Median {nf(med, 0)}", 13, 600, INK, "end")
    d.line(kxp(FJ["median_kjedekost"]), yb - 100, kxp(FJ["median_kjedekost"]), yb, INK, 1, dash="3 3")
    d.t(kxp(FJ["median_kjedekost"]) + 4, yb - 104, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 13, 400, INK2)
    d.t(rx, yb + 40, f"Midtre halvdel av {len(fer)} ferdige: {nf(q['q1'], 0)} til {nf(q['q3'], 0)} kr. Fjoråret: {FJ['klasse']}, {FJ['spill']} spill.", 13, 400, INK2)

    # Kostnad per uke, snitt for ferdige
    y2 = yb + 84
    tl, tr = sum(mean_lk), sum(mean_rk)
    d.t(rx, y2, "Hva kjedekostnaden består av", 17, 600, INK)
    d.para(rx, y2 + 20, f"Snitt per ferdig spill og uke. Av {nf(tl + tr, 0)} kr per spill er {nf(tr, 0)} restordrekostnad og {nf(tl, 0)} lagerkostnad.", rw, 13, 17, fill=INK2)
    axw = Axis(rx + 30, rw - 30, 1, 36)
    gy, gh = y2 + 62, 96
    km = 120
    for v in (0, 50, 100):
        yv = gy + gh - v * gh / km
        d.line(axw.x0, yv, axw.x1, yv, HAIR2 if v == 0 else HAIR, 1)
        d.t(axw.x0 - 5, yv + 4, v, 12, 400, INK3, "end")
    for k in range(36):
        bw = axw.slot - 2
        x = axw.xc(k + 1) - bw / 2
        lh = mean_lk[k] * gh / km
        rh_ = mean_rk[k] * gh / km
        d.rect(x, gy + gh - lh, bw, lh, BLUE)
        if rh_:
            d.rect(x, gy + gh - lh - rh_ - 1, bw, rh_, RED)
    xaxis(d, axw, gy + gh + 16, [1, 6, 12, 18, 24, 30, 36], None, 12)
    pk = max(range(36), key=lambda k: mean_rk[k])
    d.t(axw.xc(13), gy + 22, f"Restordre, topp i Uke {pk + 1}", 13, 600, INK, "end")
    lk_end = max(range(24, 36), key=lambda k: mean_lk[k])
    d.t(axw.xc(36), gy + gh - (mean_lk[lk_end] + mean_rk[lk_end]) * gh / km - 8, "Lager", 13, 600, INK, "end")

    # Trakt
    y3 = gy + gh + 54
    d.t(rx, y3, "Trakten", 17, 600, INK)
    tr_ = KL["traktA"]
    steps = [("Registrert", tr_["registrert"]), ("Klassespill ferdig", tr_["klassespill_ferdig"]), ("Debrief ferdig", tr_["debrief_ferdig"]),
             ("Quiz bestått", tr_["quiz_bestått"]), ("Replay ferdig", tr_["replay_ferdig"]), ("Test levert", tr_["test_levert"]), ("KI-vurdering klar", tr_["ki_vurdering_klar"])]
    yy = y3 + 22
    for lab, v in steps:
        d.t(rx, yy, lab, 13, 400, INK)
        d.t(rx + 166, yy, v, 13, 600, INK, "end")
        if v:
            d.rect(rx + 176, yy - 10, (rw - 176) * v / steps[0][1], 11, ORD)
        else:
            d.line(rx + 176, yy - 10, rx + 176, yy + 1, INK, 1)
        yy += 19
    yy += 22
    d.t(rx, yy, "Mønstre i ordrene", 17, 600, INK)
    yy += 22
    for lab, v in KL["moenstre"].items():
        d.t(rx, yy, lab, 13, 400, INK)
        d.t(rx + rw, yy, v, 13, 600, INK, "end")
        d.line(rx, yy + 6, rx + rw, yy + 6, HAIR, 1)
        yy += 20
    d.t(rx, yy + 6, "Antall funn i klassens spill. Forklares med struktur, ikke skyld.", 13, 400, INK2)
    d.button(rx, fy0 + fh - 56, 150, 36, "Vis i plenum", primary=False, size=14)
    d.demodata(fx0 + fw - 24, fy0 + fh - 14, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
