"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e10syn import *

G = Seat()
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
K = FX["spill17"]
NAME = "Fri syntese"


# ---------- telefonens deler ----------
def phone_syn(d, g, wk, typed, proj=False, posisjon=False, hnet=100, show_typed=True):
    """Telefonens graf: kjedebånd, din ordre, netto lager og kostnad på én tidsakse. Høyre kant er nå + 4."""
    return syn(d, g, 16, 104, 358, wk, typed, wmin=wk - 7, left=30, u=1.3, ls=13, hord=40, omax=25, hnet=hnet, hcost=30, cmax=40, gap=14,
               x_left=16, netlabel=False, proj=proj, posisjon=posisjon, show_typed=show_typed, maxdn=40 if not posisjon else 58)


def order_input(d, y, wk, typed):
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, f"Din ordre for Uke {wk}", 15, 600, INK)
    d.t(370, y + 28, "Tallene", 14, 600, BLUE, "end", 'text-decoration="underline"')
    yb = y + 42
    d.rect(20, yb, 350, 58, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(78, yb, 78, yb + 58, HAIR2, 1)
    d.line(312, yb, 312, yb + 58, HAIR2, 1)
    d.line(40, yb + 29, 58, yb + 29, INK, 2)
    d.line(332, yb + 29, 350, yb + 29, INK, 2)
    d.line(341, yb + 20, 341, yb + 38, INK, 2)
    if typed is None:
        d.t(195, yb + 39, "Antall enheter", 18, 400, INK3, "middle")
    else:
        d.t(195, yb + 42, typed, 34, 700, INK, "middle")
    return yb + 58


def waiting_rows(d, y, rows, x=20, width=350, lh=30):
    """rows: (rolle, navn, status, ferdig?). Fylt eller åpen ring og tekst, aldri farge alene."""
    for rolle, navn, status, done in rows:
        if done:
            d.circle(x + 6, y - 5, 5, INK)
        else:
            d.circle(x + 6, y - 5, 5, PAPER, INK, 1.5)
        d.t(x + 20, y, rolle, 14, 600, INK)
        d.t(x + 104, y, navn, 14, 400, INK)
        d.t(x + width, y, status, 14, 400, INK2, "end")
        y += lh
    return y


def seat_sara_klar():
    return [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "Jonas", "venter, 3 min", False), ("Grossist", "Sara", "har bestilt", True)]


def matrix_seat(d, g, x, y, wfrom, wto, now, typed=None, lw=92, cw=32, rh=30, size=13, rows=None, head=True):
    """Setets egen matrise: uker som kolonner, samme rekkefølge som grafen. Tallene er de samme som i grafen."""
    rows = rows or [("Ordre inn", "flow", g.inn), ("Levering", "flow", g.levering), ("Sendt", "flow", g.sendt),
                    ("Netto lager", "net", g.net), ("På vei", "flow", g.paavei), ("Din ordre", "flow", g.order),
                    ("Kostnad, kr", "cost", None)]
    yy = y
    if head:
        for k in range(wfrom, wto + 1):
            d.t(x + lw + (k - wfrom + 0.5) * cw, yy, k, 13, 700 if k == now else 400, INK if k == now else INK3, "middle")
        yy += 8
    for lab, kind, fn in rows:
        d.t(x, yy + rh / 2 + 5, lab, 14 if size >= 13 else 12, 400, INK)
        for k in range(wfrom, wto + 1):
            cx = x + lw + (k - wfrom) * cw
            if kind == "cost":
                cost_cell(d, cx, yy, cw, rh, g, k, size, bold=(k == now), outline=(k == now))
                continue
            v = fn(k)
            if lab == "Din ordre" and k == now and typed is not None:
                v = typed
            mcell(d, cx, yy, cw, rh, v, kind, size, bold=(k == now), outline=(k == now))
        yy += rh
    return yy


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, f"{NAME}, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn: kjedebåndet langs tidsaksen, din ordre, netto lager og kostnad per uke. "
            "Ved siden av: tallene bak ett trykk, samme skjerm på laptop, og forskjellen mellom Klassespill og Replay.")
    d.t(40, 46, "Uke 11. Det som er på vei, står over uka det kommer, og 24 legger seg bakerst i køen.", 26, 600, INK)

    # Telefon
    phone(d, 40, 84, 1.0)
    game_header(d, 11, G.kostsum(11))
    m = phone_syn(d, G, 11, 24)
    yb = order_input(d, m["axisbot"] + 12, 11, 24)
    d.t(20, yb + 24, "Kommer fram om lag Uke 15. Kan ikke endres", 13, 400, INK2)
    d.t(20, yb + 42, "etter at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 56, 350, 52, "Bekreft ordre på 24")
    d.t(20, yb + 132, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 132, a="end")
    d.end()
    d.t(235, 952, "Telefon, Klassespill: kjeden og grafen deler tidsakse.", 14, 400, INK2, "middle")

    # Ett trykk: tallene
    px = 460
    phone(d, px, 84, 1.0)
    d.t(20, 66, "Tallene, Uke 4 til 11", 24, 700, INK)
    d.t(370, 62, "Lukk", 15, 600, BLUE, "end", 'text-decoration="underline"')
    d.t(20, 88, "Samme uker som grafen. Sveip for eldre uker.", 13, 400, INK2)
    y = matrix_seat(d, G, 20, 118, 4, 11, 11, 24, lw=94, cw=32, rh=30)
    y += 30
    d.t(20, y, "Uke 11 som regnestykke", 17, 600, INK)
    y += 26
    calc = [("Restordre", f"{G.rest[9]} + {G.inn(11)} inn − {G.levering(11)} levert = {G.rest[10]}"),
            ("Kostnad denne uka", f"{G.rest[10]} × 1,00 = {nf(G.uke_kost(11))} kr"),
            ("Totalkostnad", f"{nf(G.kostsum(10))} + {nf(G.uke_kost(11))} = {nf(G.kostsum(11))} kr"),
            ("Posisjon", f"{G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}"),
            ("Med ordren på 24", f"{G.posisjon(11)} + 24 = {G.posisjon(11) + 24}")]
    for lab, v in calc:
        d.t(20, y, lab, 14, 400, INK)
        d.t(370, y, v, 14, 600, INK, "end")
        d.line(20, y + 8, 370, y + 8, HAIR, 1)
        y += 27
    y += 22
    d.t(20, y, "Totalkostnad, Uke 1 til 11", 17, 600, INK)
    ax = Axis(50, 220, 1, 11)
    gy = y + 14
    gh = 96
    Yc, a, b = cum_cost_area(d, ax, gy, gh, G.lagerkost, G.restkost, 1, 11, 80)
    for v in (0, 40, 80):
        d.line(ax.x0, Yc(v), ax.x1, Yc(v), HAIR, 1)
        d.t(ax.x0 - 5, Yc(v) + 4, v, 13, 400, INK3, "end")
    d.t(ax.x1 + 6, Yc(a + b) + 4, f"{nf(a + b)}", 13, 700, INK)
    d.t(ax.x1 + 6, Yc(a + b) + 22, f"restordre {nf(b)}", 13, 400, INK2)
    d.t(ax.x1 + 6, Yc(a / 2) + 4, f"lager {nf(a)}", 13, 400, INK2)
    xaxis(d, ax, gy + gh + 16, [1, 3, 5, 7, 9, 11], 11)
    d.demodata(20, 830)
    d.end()
    d.t(655, 952, "Ett trykk unna: tallene på samme uker, og regnestykket uten fasit.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 84, 680, 500
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 104, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    m2 = syn(d, G, lx + 16, ly + 56, 446, 11, 24, left=30, u=0.75, ls=13, hord=30, hflow=36, hnet=96, hcost=24, gap=12,
             x_left=lx + 16, netlabel=False)
    cx = lx + 486
    rx = lx + lw - 24
    y = ly + 34
    d.t(rx, y, f"Totalkostnad {nf(G.kostsum(11))} kr", 15, 600, INK, "end")
    y += 36
    for lab, val in [("Lager", G.lager[10]), ("Restordre", G.rest[10]), ("Ordre inn", G.inn(11)), ("Levering", G.levering(11)),
                     ("Sendt", G.sendt(11)), ("På vei", f"{G.paavei(11)} + 24"), ("Kostnad denne uka", f"{nf(G.uke_kost(11))} kr")]:
        d.t(cx, y, lab, 14, 400, INK)
        d.t(rx, y, val, 14, 600, INK, "end")
        d.line(cx, y + 7, rx, y + 7, HAIR, 1)
        y += 27
    y += 18
    d.t(cx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, y + 10, rx - cx, 48, PAPER, INK, 1.4, 6)
    d.t((cx + rx) / 2, y + 45, 24, 30, 700, INK, "middle")
    d.button(cx, y + 70, rx - cx, 44, "Bekreft ordre på 24", size=15)
    d.t(cx, y + 138, "Venter på: Jonas (3 min)", 13, 400, INK2)
    d.t(cx, y + 156, "og deg.", 13, 400, INK2)
    d.t(cx, y + 190, "Tallene", 14, 600, BLUE, "start", 'text-decoration="underline"')
    d.demodata(rx, ly + lh - 14, a="end")

    # Hjelpegrad
    hy = 626
    d.t(lx, hy, "Hjelpegrad: delene i Klassespillet, summen i Replay", 20, 600, INK)
    pw = 330
    for i, (title, posi, proj) in enumerate((("Klassespill: hver ankomst for seg", False, False),
                                              ("Replay, etter Debriefen: summen og linja", True, True))):
        bx = lx + i * (pw + 20)
        d.t(bx, hy + 28, title, 14, 600, INK)
        mm = syn(d, G, bx, hy + 40, pw, 11, 24, wmin=4, left=28, u=0.75, ls=13, hord=0, omax=25, hnet=96, hcost=0, gap=10,
                 titles=False, x_left=bx, netlabel=False, posisjon=posi, proj=proj, maxdn=62, connector=False, head_left=False)
        if proj:
            p = mm["proj"][-1][1]
            d.t(mm["fx1"] - 4, mm["Y"](p) - 9, f"{sg(p)}", 13, 700, INK, "end")
    d.para(lx, 948, "I Klassespillet står hver ankomst for seg, og summen må Sara regne selv. Det er den summen de fleste lar være å regne, og Debriefen viser hva det kostet.", pw, 13, 17, fill=INK2)
    p24 = G.projection(11, 24)[-1][1]
    d.para(lx + pw + 20, 948, f"I Replay står summen under båndet, og linja regner {G.posisjon(11) + 24} − 4 × {G.inn(11)} = {sg(p24)} hvis ordre inn holder seg. Ikke garantert.", pw, 13, 17, fill=INK2)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, f"{NAME}, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter. "
            "Under: ordren på 24 som rykker fram i kjedebåndet.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 176
    d.t(40, 50, "En Uke: tallet du taster legger seg bakerst i køen, og køen rykker én uke fram.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Levering og ordre inn er regnet. Plassen fire uker fram i båndet står tom og venter på tallet ditt."),
        ("B  Beslutningen: 24", "Sara taster 24, og boksen står bakerst i køen, etter 4, 4 og 8. Ingen fasit ved siden av."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Båndet rykker én uke mot lageret. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle og per kostnadsart. Videre til Debrief."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 92, h, 20, 600, INK)
        d.para(x, 118, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone(d, px(0), y0, s)
    game_header(d, 11, G.kostsum(11))
    m = phone_syn(d, G, 11, None)
    yb = order_input(d, m["axisbot"] + 12, 11, None)
    d.t(20, yb + 24, f"Sist Uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.button(20, yb + 56, 350, 52, "Bekreft ordre", primary=False)
    d.demodata(20, 830)
    d.end()

    # B
    phone(d, px(1), y0, s)
    game_header(d, 11, G.kostsum(11))
    m = phone_syn(d, G, 11, 24)
    yb = order_input(d, m["axisbot"] + 12, 11, 24)
    d.t(20, yb + 24, "Kommer fram om lag Uke 15. Kan ikke endres", 13, 400, INK2)
    d.t(20, yb + 42, "etter at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 56, 350, 52, "Bekreft ordre på 24")
    d.demodata(20, 830)
    d.end()

    # C
    phone(d, px(2), y0, s)
    game_header(d, 11, G.kostsum(11))
    m = phone_syn(d, G, 11, 24)
    y = m["axisbot"] + 12
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 62, seat_sara_klar())
    d.t(20, y + 196, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 830)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    game_header(d, w, G.kostsum(w))
    m = phone_syn(d, G, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["yord"] - 2, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["axisbot"] + 12
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 28, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    rr = [("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w)),
          ("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}"), ("Kostnad denne uka", f"{nf(G.uke_kost(w))} kr")]
    yy = y + 58
    for lab, v in rr:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 24
    d.demodata(20, 830)
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    game_header(d, w, G.kostsum(w))
    m = phone_syn(d, G, w, G.order(w), hnet=84)
    y = m["axisbot"] + 8
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller for Jonas", "bestiller", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 54, rows, lh=25)
    d.rect(20, yy - 8, 350, 80, TINT, None, 1, 6)
    d.t(32, yy + 16, "Slik ser Jonas det etter fraværet:", 13, 400, INK2)
    d.t(32, yy + 36, "KI-spiller bestiller for deg.", 14, 600, INK)
    d.button(240, yy + 20, 120, 40, "Ta tilbake setet", primary=False, size=13)
    d.demodata(20, 830)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 66, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 88, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 132, "Kjedens totalkostnad", 15, 400, INK2)
    d.t(20, 172, f"{nf(K['kjedekost'])} kr", 40, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    S4 = {r: Seat(r) for r in ROLES}
    tl = sum(S4[r].cum(36, "lager") for r in ROLES)
    tr = sum(S4[r].cum(36, "rest") for r in ROLES)
    d.t(20, 200, f"Restordre {nf(tr)} kr · lager {nf(tl)} kr", 14, 400, INK)
    y = 244
    mx = max(K["kost_per_rolle"].values())
    for r in ROLES:
        S = S4[r]
        lv, rv = S.cum(36, "lager"), S.cum(36, "rest")
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        d.t(370, y, f"{nf(lv + rv)} kr", 14, 600, INK, "end")
        wr = 350 * rv / mx
        wl = 350 * lv / mx
        d.rect(20, y + 8, wr - 1, 10, RED)
        d.rect(20 + wr + 1, y + 8, wl - 1, 10, BLUE)
        y += 48
    d.t(20, y, "Rødt: restordre × 1,00. Blått: lager × 0,50.", 13, 400, INK2)
    y += 36
    d.t(20, y, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(50, 324, 1, G.n)
    grid(d, ax, y + 12, 110, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax, y + 12, 110, G.net, 1, G.n)
    xaxis(d, ax, y + 140, [1, 12, 24, 36], None)
    d.t(20, y + 176, "Hvorfor ble det slik? Det finner dere ut", 14, 400, INK2)
    d.t(20, y + 195, "i Debriefen, med hele kjeden.", 14, 400, INK2)
    d.button(20, 756, 350, 52, "Gå til Debrief")
    d.demodata(20, 830)
    d.end()

    # Under
    yt = y0 + 844 * s + 50
    d.t(40, yt, "Hva spilleren lærer av å se kjeden, grafen og kostnaden uke for uke", 24, 600, INK)
    tekst = [
        "Båndet øverst bruker samme tidsakse som grafen. Det som er på vei, står over uka det ventes, så ventetiden er en avstand Sara kan se, ikke et tall i en liste.",
        "Tallet du taster, legger seg bakerst i køen. Hver Uke rykker køen ett steg mot lageret, og Sara ser at en ny ordre ikke kommer raskere enn de gamle.",
        "Under grafen står kostnaden for hver Uke på samme akse. Restordre koster dobbelt så mye per enhet som lager, og stolpene viser det uten forklaring.",
        "I Klassespillet står hver ankomst for seg. Summen, posisjonen, ligger bak ett trykk som regnestykke. I Replay står summen under båndet.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 34, tx, colw, 16, 22, fill=INK)
    ys = yt + 158
    d.t(40, ys, f"Ordren på 24 i båndet, Uke 11 til 15: den rykker mot lageret, og i Uke 15 kom {G.levering(15)}.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 24) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 24)
        ax = Axis(xx + 60, pw2 - 60, wk - 1, wk + 4)
        uu = 1.5
        if wk < 15:
            b = chain_band(d, G, ax, ys + 4, wk, G.order(wk), u=uu, ls=13, header=False, left=False, labels=False,
                           maxup=26, maxdn=30, mark_week=15)
        else:
            b = chain_band(d, G, ax, ys + 4, wk, G.order(wk), u=uu, ls=13, header=False, left=False, labels=False,
                           maxup=26, maxdn=30, mark_week=-1)
            d.rect(b["xsb"], b["yb"] - 24 * uu, b["bw"], 24 * uu, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
            d.rect(b["xsb"], b["yb"] - 17 * uu, b["bw"], 17 * uu, "none", INK, 1.6)
        L, R = G.lager[wk - 1], G.rest[wk - 1]
        d.t(b["xsb"] - 6, b["yb"] + 15, f"Restordre {R}" if R else f"Lager {L}", 13, 400, INK2, "end")
        bh = b["bottom"] - ys - 4
        d.line(ax.xr(wk), b["yb"] - 44, ax.xr(wk), b["yb"] + 30, INK, 1.2)
        cap = {11: "Uke 11: 24 bakerst", 12: "Uke 12: tre plasser igjen", 13: "Uke 13: to plasser igjen", 14: "Uke 14: neste Uke",
               15: f"Uke 15: {G.levering(15)} av 24 kom, {G.overdue(15)} uten dato"}[wk]
        d.t(xx, ys + 4 + bh + 18, cap, 14, 600 if wk in (11, 15) else 400, INK)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, f"{NAME}, grafgrammatikken over tid",
            "Saras kjedebånd, ordre, netto lager og kostnad i Uke 5, 11, 18 og 29 på én felles tidsakse, med uka som tall ved siden av, "
            "og sammenligning med simulert referanse etter Debriefen.")
    d.t(40, 54, "Én tidsakse, fire lesninger: hvor varene er, hva du bestilte, hva lageret ble, og hva det kostet", 32, 700, INK)
    d.para(40, 88, "Hver rad er Saras skjerm i én Uke, tegnet på hele spillets akse. Båndet øverst er kjeden: det som er på vei står over uka det ventes. Til høyre står samme Uke som tall, og tallene er de samme som i grafen.", 1400, 16, 22, fill=INK2)

    rows = [
        (5, [("P2 Forsinkelse", "Alt er 4. Det som skjer hos kundene, har ikke nådd Sara ennå, og grafen er flat."),
             ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte. Sara har ingen annen kilde.")],
         "En rolig graf betyr bare at ingenting har nådd deg ennå."),
        (11, [("P3 Det som er på vei", f"Køen er {', '.join(str(q) for _, q in G.arrivals(11, 24)[:3])}. Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir den {G.posisjon(11) + 24}."),
              ("P1 Lager er en opphopning", f"Kolonnen er regnestykket: {sg(G.net(10))} + {G.levering(11)} levert − {G.inn(11)} ordre inn = {sg(G.net(11))}.")],
         f"24 legger seg bakerst. I Uke 15 kom {G.levering(15)}: bestilt er ikke levert."),
        (18, [("P3 og P7", f"{G.paavei(18)} på vei, {G.overdue(18)} av dem uten dato. En ny ordre kommer ikke før de gamle; den gjør bare køen lengre."),
              ("P8 Restordre koster dobbelt", f"Restordre {G.rest[17]} koster {nf(G.uke_kost(18))} kr i uka. Rødt dominerer kostnaden.")],
         f"Restordre {G.rest[17]} er det du ser. Køen på {G.paavei(18)} er det som kommer."),
        (29, [("P1 Samme regning, motsatt fortegn", "Køen kom nesten samtidig i Uke 23 til 26. Toppen i lageret er summen av gamle ordrer."),
              ("P8 Lager koster også", f"Lager {G.lager[28]} × 0,50 = {nf(G.uke_kost(29))} kr i uka. Halvparten av restordre, men det teller.")],
         "Køen er nesten tom. Hvor mye lager du vil ha igjen, må du bestemme selv."),
    ]
    y = 128
    x0, wplot = 250, 1190
    rh = 258
    for now, notes, nxt in rows:
        typed = G.order(now)
        m = syn(d, G, x0, y, wplot, now, typed, wmin=1, wmax=36, left=34, u=0.8, ls=13, hord=24, omax=25, hnet=62, hcost=22,
                cmax=40, gap=6, titles=False, x_left=x0 + 34, netlabel=False, xstep=4, connector=True, maxup=30, maxdn=40,
                head_left=False, overdue_note=True, cost_label=False)
        ax = m["ax"]
        d.t(40, y + 30, f"Uke {now}", 28, 700, INK)
        d.t(40, y + 52, f"Totalkostnad {nf(G.kostsum(now))} kr", 14, 400, INK2)
        lab = [("Kjeden nå, P2 P3", m["b"]["yb"] + 4), ("Din ordre, P2", m["yord"] + 22),
               ("Netto lager, P1", m["ynet"] + 38), ("Kostnad per uke, P8", m["ycost"] + 18)]
        for t_, yy in lab:
            d.t(x0 - 8, yy, t_, 13, 600, INK2, "end")
        # uka som tall
        tx = 1470
        cw = 46
        lw = 104
        d.t(tx + lw + cw * 0.5, y + 16, now - 1, 13, 400, INK3, "middle")
        d.t(tx + lw + cw * 1.5, y + 16, now, 13, 700, INK, "middle")
        rws = [("Ordre inn", "flow", G.inn), ("Levering", "flow", G.levering), ("Netto lager", "net", G.net),
               ("På vei", "flow", G.paavei), ("Din ordre", "flow", G.order), ("Kostnad, kr", "cost", None)]
        yy = y + 24
        for lb, kind, fn in rws:
            d.t(tx, yy + 18, lb, 13, 400, INK)
            for j, k in enumerate((now - 1, now)):
                if kind == "cost":
                    cost_cell(d, tx + lw + j * cw, yy, cw, 26, G, k, 13, bold=(k == now))
                else:
                    mcell(d, tx + lw + j * cw, yy, cw, 26, fn(k), kind, 13, bold=(k == now))
            yy += 26
        nx = tx + lw + 2 * cw + 22
        nw = 1960 - nx
        ny = y + 14
        for head, body in notes:
            d.t(nx, ny, head, 14, 600, INK)
            ny = d.para(nx, ny + 18, body, nw, 13, 17, fill=INK2) + 6
        d.t(nx, ny, "Til neste ordre", 14, 600, INK)
        d.para(nx, ny + 18, nxt, nw, 13, 17, fill=INK)
        d.line(40, y + rh - 5, 1960, y + rh - 5, HAIR, 1)
        y += rh

    # Etter Debriefen
    d.t(40, y + 22, "Etter Debriefen: kostnaden, mot simulert referanse", 24, 600, INK)
    d.t(40, y + 46, "Samme kjede, samme kunder. Linjene viser en sammenheng, de er ingen fasit. Simulert.", 15, 400, INK2)
    gy = y + 76
    gh = 126
    ax = Axis(80, 820, 1, 36)
    Yc, a, b = cum_cost_area(d, ax, gy, gh, G.lagerkost, G.restkost, 1, 36, 600,
                             refs=[([(k, BARE.kostsum(k)) for k in range(1, 37)], "Bare Sara"), ([(k, ALLE.kostsum(k)) for k in range(1, 37)], "Alle fire")])
    for v in (0, 200, 400):
        d.line(ax.x0, Yc(v), ax.x1, Yc(v), HAIR, 1)
        d.t(ax.x0 - 6, Yc(v) + 4, v, 13, 400, INK3, "end")
    d.t(ax.x1 + 8, Yc(G.kostsum(36)) + 4, f"Spill 17: {nf(G.kostsum(36))} kr", 14, 700, INK)
    d.t(ax.x1 + 8, Yc(BARE.kostsum(36)) + 4, f"Bare Sara teller på vei: {nf(BARE.kostsum(36))}", 14, 400, INK2)
    d.t(ax.x1 + 8, Yc(ALLE.kostsum(36)) + 4, f"Alle fire teller på vei: {nf(ALLE.kostsum(36))}", 14, 400, INK2)
    d.t(ax.xc(28), Yc(G.cum(28, "lager") + 70) + 4, f"Restordre {nf(b)} kr", 14, 600, INK, "middle")
    d.t(ax.xc(33), Yc(G.cum(33, "lager") / 2) + 6, f"Lager {nf(a)} kr", 14, 600, INK, "middle")
    xaxis(d, ax, gy + gh + 17, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.t(80, gy - 12, "Grossist, akkumulert kostnad, kr", 13, 600, INK)

    tx = 1200
    gy = y + 52
    cols = [tx + 250, tx + 360, tx + 470]
    d.t(cols[0], gy + 10, "Spill 17", 14, 600, INK, "end")
    d.t(cols[1], gy + 10, "Bare Sara", 14, 600, INK, "end")
    d.t(cols[2], gy + 10, "Alle fire", 14, 600, INK, "end")
    d.line(tx, gy + 18, cols[2], gy + 18, HAIR2, 1)
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    rr = [("Kjedekostnad, kr", nf(K["kjedekost"]), nf(B["kjedekost"]), nf(A["kjedekost"])),
          ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"]), nf(A["kost_per_rolle"]["Grossist"])),
          ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]), fx1(A["forsterkning"]["Grossist"])),
          ("Forsterkning, Fabrikk", fx1(K["forsterkning"]["Fabrikk"]), fx1(B["forsterkning"]["Fabrikk"]), fx1(A["forsterkning"]["Fabrikk"]))]
    yy = gy + 42
    for row in rr:
        d.t(tx, yy, row[0], 14, 400, INK)
        for c, v in zip(cols, row[1:]):
            d.t(c, yy, v, 14, 400, INK, "end")
        d.line(tx, yy + 8, cols[2], yy + 8, HAIR, 1)
        yy += 27
    d.para(tx, yy + 8, "P5, P6 og P8: når ett ledd teller det som er på vei, faller kostnaden for hele kjeden, ikke bare for det leddet. Formen består, for strukturen er den samme.", 470, 13, 17, fill=INK2)

    hx = 1720
    d.t(hx, y + 22, "Hjelpegrad", 20, 600, INK)
    ny = d.para(hx, y + 48, "Klassespill: båndet med hver ankomst for seg. Summen ligger bak ett trykk.", 240, 14, 19, fill=INK)
    ny = d.para(hx, ny + 6, "Replay: summen under båndet og den stiplede linja.", 240, 14, 19, fill=INK)
    d.para(hx, ny + 10, "P7: å telle det som er på vei er ikke nok alene. En regel som jaget siste ordre for hardt, ga Fabrikk 12× i simuleringen.", 240, 13, 17, fill=INK2)
    d.demodata(1960, 1390, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
