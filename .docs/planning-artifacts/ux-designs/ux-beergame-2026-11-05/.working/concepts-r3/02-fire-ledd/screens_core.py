"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e02chain import *

G = Seat()
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
K = FX["spill17"]
SEATS = {r: Seat(r) for r in ROLES}
SIM = {r: Seat(r, FX["alle_teller_paa_vei"]) for r in ROLES}
DEM = K["serier"]["demand"]
NAME = "Fire ledd"

# Kryssjekk: kjede, matrise, graf og kostnad bygger på de samme tallene for alle uker og alle Roller.
for _r in ROLES:
    _S = SEATS[_r]
    for _w in range(1, 37):
        _st = state(_S, _w)
        assert _st["net"] == _S.lager[_w - 1] - _S.rest[_w - 1]
        if _w > 1:
            assert _S.net(_w) == _S.net(_w - 1) + _S.levering(_w) - _S.inn(_w), (_r, _w)
            assert abs(_S.kostsum(_w) - _S.kostsum(_w - 1) - week_cost(_S, _w)) < 1e-6
    assert abs(_S.kostsum(36) - K["kost_per_rolle"][_r]) < 1e-6
assert abs(sum(K["kost_per_rolle"].values()) - K["kjedekost"]) < 1e-6
# ordre fra et ledd er ordre inn hos leverandøren to uker senere (ordreforsinkelse 2)
for _a, _b in zip(CHAIN[1:], CHAIN[:-1]):
    assert all(SEATS[_a].order(w - 2) == SEATS[_b].inn(w) for w in range(1, 37)), (_a, _b)
assert all(SEATS["Detaljist"].inn(w) == DEM[w - 1] for w in range(1, 37))
S11 = state(G, 11)
assert (S11["lager"], S11["rest"], S11["inn"], S11["lev"], S11["sendt"], S11["pv"]) == (0, 13, 8, 4, 4, 16)
assert S11["cost"] == 68.0 and G.posisjon(11) == 3


def states(w, src=SEATS):
    return {r: state(src[r], w) for r in ROLES}


def phone_meteo(d, g, wk, typed, y=None, hn=96, proj=False, ghost=None):
    m = meteo(d, g, 16, y, 358, wk, typed, left=30, hn=hn, hf=40, gap=16, t_flow="", t_ord="", proj=proj, ghost=ghost,
              arrnums=False, futnote=None, ticks=(-40, -20, 0, 20))
    lev, inn = g.levering(wk), g.inn(wk)
    xx = 16
    for lab, val, col in (("Levering", lev, BASE), ("Ordre inn utover levering", max(inn - lev, 0), RED)):
        d.rect(xx, m["yflow"] - 17, 10, 10, col)
        s = f"{lab} {val}"
        d.t(xx + 14, m["yflow"] - 7, s, 13, 600, INK)
        xx += 14 + text_w(s, 13) + 14
    d.t(16, m["yord"] - 7, "Din ordre", 13, 600, INK)
    return m


def order_input(d, y, wk, typed, link="Alle tall"):
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, f"Din ordre for Uke {wk}", 15, 600, INK)
    if link:
        d.t(370, y + 26, link, 14, 600, BLUE, "end", 'text-decoration="underline"')
    yb = y + 38
    d.rect(20, yb, 350, 54, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(76, yb, 76, yb + 54, HAIR2, 1)
    d.line(314, yb, 314, yb + 54, HAIR2, 1)
    d.line(39, yb + 27, 57, yb + 27, INK, 2)
    d.line(333, yb + 27, 351, yb + 27, INK, 2)
    d.line(342, yb + 18, 342, yb + 36, INK, 2)
    if typed is None:
        d.t(195, yb + 33, "Antall enheter", 17, 400, INK3, "middle")
    else:
        d.t(195, yb + 40, typed, 32, 700, INK, "middle")
    return yb + 54


def game_header(d, wk, role="Grossist", spill="Spill 17", right=None):
    d.t(20, 62, f"Uke {wk}", 30, 700, INK)
    d.t(122 if wk >= 10 else 106, 62, f"{role}, {spill}", 14, 400, INK2)
    if right:
        d.t(370, 62, right, 14, 600, BLUE, "end", 'text-decoration="underline"')


def waiting_rows(d, y, rows, x=20, width=350, lh=28, size=14):
    """rows: (rolle, navn, status, ferdig?). Status står alltid som tekst, ikke bare som fylt sirkel."""
    for rolle, navn, status, done in rows:
        if done:
            d.circle(x + 6, y - 5, 5, INK)
        else:
            d.circle(x + 6, y - 5, 5, PAPER, INK, 1.5)
        d.t(x + 20, y, rolle, size, 600, INK)
        d.t(x + 110, y, navn, size, 400, INK)
        d.t(x + width, y, status, size, 400, INK2, "end")
        y += lh
    return y


def seat_sara_klar():
    return [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "Jonas", "venter, 3 min", False), ("Grossist", "Sara", "har bestilt", True)]


def phone_game(d, wk, typed, proj=False, posisjon=False, ghost=None, link="Alle tall"):
    """Spilleskjermen: kjeden øverst, grafen under, ordrefeltet nederst."""
    game_header(d, wk)
    st = state(G, wk)
    c = chain_seat(d, 20, 84, 350, st, typed, posisjon=posisjon, empty_slot=True)
    m = phone_meteo(d, G, wk, typed, y=c["bottom"] + 6, proj=proj, ghost=ghost)
    return c, m


def seat_table(d, ax, y, wfrom, wto, ch=24, ls=13, sel=None, typed=None, label_x=None, rows=None):
    """Setets egen matrise: samme tall som kjeden og grafen, uke for uke."""
    def v(f):
        return lambda k: f(k) if wfrom <= k <= wto else None
    allrows = {
        "inn": {"label": "Ordre inn", "vals": v(G.inn)},
        "lev": {"label": "Levering", "vals": v(G.levering)},
        "sendt": {"label": "Sendt", "vals": v(G.sendt)},
        "net": {"label": "Netto lager", "vals": v(G.net), "kind": "div"},
        "pv": {"label": "På vei", "vals": v(G.paavei)},
        "ord": {"label": "Din ordre", "vals": lambda k: (typed if (typed is not None and k == wto) else G.order(k)) if wfrom <= k <= wto else None, "kind": "seq"},
        "kost": {"label": "Kostnad, kr", "vals": v(lambda k: week_cost(G, k)), "kind": "cost"},
    }
    keys = rows or ["inn", "lev", "sendt", "net", "pv", "ord", "kost"]
    return matrix(d, ax, y, [allrows[k] for k in keys], ch=ch, ls=ls, sel=sel, wmin=wfrom, wmax=wto, label_x=label_x)


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, f"{NAME}, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn: eget ledd i kjeden øverst, meteogrammet under, ordrefeltet nederst. Ved siden av: Alle tall som matrise, laptop i Labtime, og Hjelpegrad i Klassespill mot Replay.")
    d.t(40, 46, "Uke 11. Saras ledd står øverst, og 24 ligger allerede bakerst i røret.", 26, 600, INK)

    # Telefon
    phone(d, 40, 84, 1.0)
    c, m = phone_game(d, 11, 24)
    yb = order_input(d, m["axisbot"] + 6, 11, 24)
    d.t(20, yb + 22, "Kommer fram om lag Uke 15. Kan ikke endres etter", 13, 400, INK2)
    d.t(20, yb + 39, "at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 50, 350, 50, "Bekreft ordre på 24")
    d.t(20, yb + 124, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 124, a="end")
    d.end()
    d.t(235, 952, "Telefon, Klassespill: eget ledd, graf og ordre.", 14, 400, INK2, "middle")

    # Åpnet panel: Alle tall som matrise
    px = 460
    phone(d, px, 84, 1.0)
    d.t(20, 62, "Alle tall", 26, 700, INK)
    d.t(132, 62, "Uke 6 til 11", 14, 400, INK2)
    d.t(370, 60, "Lukk", 15, 600, BLUE, "end", 'text-decoration="underline"')
    ax = Axis(122, 248, 6, 11)
    week_ticks(d, ax, 100, range(6, 12), 11, 13)
    yy = seat_table(d, ax, 110, 6, 11, ch=27, ls=13, sel=11, typed=24, label_x=114)
    d.t(20, yy + 22, "Samme tall som i kjeden og grafen. Uke 11 er nå.", 13, 400, INK2)
    y = yy + 56
    d.t(20, y, "Kostnad til og med Uke 11", 16, 600, INK)
    y += 26
    lk = sum(G.lager[:11]) * LK
    rk = sum(G.rest[:11]) * RK
    rows = [("Lagerkostnad", f"{sum(G.lager[:11])} × 0,50", lk, BLUE), ("Restordrekostnad", f"{sum(G.rest[:11])} × 1,00", rk, RED)]
    for lab, calc, val, col in rows:
        d.rect(20, y - 10, 10, 10, col)
        d.t(36, y, lab, 14, 400, INK)
        d.t(256, y, calc, 14, 400, INK2, "end")
        d.t(370, y, f"{nf(val)} kr", 14, 600, INK, "end")
        d.line(20, y + 8, 370, y + 8, HAIR, 1)
        y += 26
    d.t(36, y, "Totalkostnad", 14, 600, INK)
    d.t(370, y, f"{nf(lk + rk)} kr", 14, 700, INK, "end")
    y += 20
    d.para(20, y, "Enhetsuker: summen av lager og restordre over alle uker. Restordre koster det dobbelte.", 350, 13, 17, fill=INK2)
    y += 52
    d.t(20, y, "Regnestykket", 16, 600, INK)
    y += 24
    d.t(20, y, "Lager − Restordre + På vei", 14, 400, INK2)
    y += 24
    d.t(20, y, "Posisjon", 15, 400, INK)
    d.t(370, y, f"{G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}", 15, 600, INK, "end")
    y += 26
    d.t(20, y, "Med ordren på 24", 15, 400, INK)
    d.t(370, y, f"{G.posisjon(11)} + 24 = {G.posisjon(11) + 24}", 15, 600, INK, "end")
    d.t(20, y + 34, "Vis alle uker", 14, 600, BLUE, "start", 'text-decoration="underline"')
    d.demodata(20, 830)
    d.end()
    d.t(655, 952, "Ett trykk unna: matrisen, kostnaden og regnestykket, uten fasit.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 84, 680, 640
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 110, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    st = state(G, 11)
    cc = chain_seat(d, lx + 24, ly + 56, 400, st, 24, sw=36, nw=64, ext_w=64)
    cx = lx + 456
    rx = lx + lw - 24
    y = ly + 76
    d.t(cx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, y + 10, rx - cx, 50, PAPER, INK, 1.4, 6)
    d.t((cx + rx) / 2, y + 46, 24, 30, 700, INK, "middle")
    d.para(cx, y + 84, "Kommer fram om lag Uke 15. Kan ikke endres etter at du har bekreftet.", rx - cx, 13, 17, fill=INK2)
    d.button(cx, y + 124, rx - cx, 44, "Bekreft ordre på 24", size=15)
    d.t(cx, y + 192, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    # meteogram og matrise på samme tidsakse
    mx0 = lx + 24
    m2 = meteo(d, G, mx0, ly + 278, lw - 48 - 130, 11, 24, wmin=1, left=78, hn=90, hf=36, gap=12, t_flow="", t_ord="",
               arrnums=True, futnote=None, ticks=(-40, -20, 0, 20), xstep=1, axislabel=False, overduenote=False)
    d.t(mx0, m2["yflow"] - 5, "Inn og ut", 13, 600, INK)
    d.t(mx0, m2["yord"] - 5, "Din ordre", 13, 600, INK)
    ax2 = m2["ax"]
    week_ticks(d, ax2, m2["ybot"] + 16, range(1, 16), 11, 12)
    yy = seat_table(d, ax2, m2["ybot"] + 26, 1, 11, ls=12, sel=None, typed=24, label_x=ax2.x0 - 8,
                    rows=["inn", "lev", "net", "pv", "ord", "kost"], ch=17)
    for k, q in G.arrivals(11, 24):
        pass
    tx = ax2.x1 + 14
    d.para(tx, m2["ynet"] + 14, "Til høyre for nå står bare det som er bestilt. Ikke garantert.", rx - tx, 12.5, 16, fill=INK2)
    d.para(tx, m2["ybot"] + 40, "Hver kolonne er én uke, med samme tall som i kjeden.", rx - tx, 12.5, 16, fill=INK2)
    lh = yy + 24 - ly
    d.rect(lx, ly, lw, lh, "none", HAIR2, 1.4, 10)
    d.demodata(rx, ly + lh - 12, a="end")
    d.t(lx, ly + lh + 20, "Laptop i Labtime: kjeden, grafen og tallene deler tidsakse.", 14, 400, INK2)

    # Hjelpegrad
    hy = ly + lh + 56
    d.t(lx, hy, "Hjelpegrad: samme ledd, to nivåer", 20, 600, INK)
    pw_ = 330
    d.t(lx, hy + 28, "Klassespill: røret og tallene, ingen sum", 14, 600, INK)
    chain_seat(d, lx, hy + 40, pw_, st, 24, u=1.2, cost=False, small=12, sw=30, nw=52, ext_w=52)
    bx = lx + pw_ + 20
    d.t(bx, hy + 28, "Replay, etter Debriefen: Posisjon tegnes", 14, 600, INK)
    chain_seat(d, bx, hy + 40, pw_, st, 24, u=1.2, cost=False, posisjon=True, small=12, sw=30, nw=52, ext_w=52)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, f"{NAME}, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter med kjedens kostnad og hele kjeden. Under: røret sett fra fem uker.")
    s = 0.78
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 176
    d.t(40, 50, "En Uke i Fire ledd: røret flytter seg mot deg, beholdningen svarer, og kostnaden står ved noden.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Levering og ordre inn er nye. I røret står tre uker med kjente ankomster, og plassen bakerst er tom."),
        ("B  Beslutningen: 24", "Sara taster, og 24 legger seg bakerst i røret, bak 4, 4 og 8. Ingen fasit ved siden av."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Røret rykker én plass mot noden. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først. Så åpnes hele kjeden, med kostnad per Rolle og kostnadsart."),
    ]

    def px(i):
        return 40 + i * (pw + gapx)

    for i, (h, n) in enumerate(notes):
        d.t(px(i), 92, h, 20, 600, INK)
        d.para(px(i), 118, n, pw, 15, 20, fill=INK2)

    # A
    phone(d, px(0), y0, s)
    c, m = phone_game(d, 11, None)
    yb = order_input(d, m["axisbot"] + 6, 11, None)
    d.t(20, yb + 24, f"Sist Uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.button(20, yb + 40, 350, 50, "Bekreft ordre", primary=False)
    d.demodata(20, 830)
    d.end()

    # B
    phone(d, px(1), y0, s)
    c, m = phone_game(d, 11, 24)
    yb = order_input(d, m["axisbot"] + 6, 11, 24)
    d.t(20, yb + 24, "Kommer fram om lag Uke 15. Kan ikke endres.", 13, 400, INK2)
    d.button(20, yb + 40, 350, 50, "Bekreft ordre på 24")
    d.demodata(20, 830)
    d.end()

    # C
    phone(d, px(2), y0, s)
    c, m = phone_game(d, 11, 24)
    y = m["axisbot"] + 6
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 58, seat_sara_klar(), lh=26)
    d.t(20, y + 176, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 830)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    c, m = phone_game(d, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["ynet"] - 2, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["axisbot"] + 6
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 26, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    yy = y + 54
    for lab, v in [("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w)),
                   ("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}"), ("Totalkostnad", f"+ {nf(week_cost(G, w))} kr")]:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 23
    d.demodata(20, 830)
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    c, m = phone_game(d, w, G.order(w))
    y = m["axisbot"] + 6
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 24, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller", "bestiller", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 52, rows, lh=24)
    d.rect(20, yy - 8, 350, 66, TINT, None, 1, 6)
    d.t(32, yy + 14, "Jonas ser: KI-spiller bestiller", 13, 400, INK2)
    d.t(32, yy + 33, "for Fabrikk.", 13, 400, INK2)
    d.button(234, yy + 4, 126, 40, "Ta tilbake setet", primary=False, size=13)
    d.demodata(20, 830)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 62, "Spillet er ferdig", 28, 700, INK)
    d.t(20, 84, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 124, "Kjedens totalkostnad", 15, 400, INK2)
    d.t(20, 162, f"{nf(K['kjedekost'])} kr", 38, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    s36 = states(36)
    tl = sum(s36[r]["cl"] for r in CHAIN)
    tr = sum(s36[r]["cr"] for r in CHAIN)
    cost_bar(d, 20, 176, 350, tl, tr, tl + tr, 8)
    d.t(20, 204, f"Lager {nf(tl)}", 13, 400, INK2)
    d.t(370, 204, f"Restordre {nf(tr)}", 13, 400, INK2, "end")
    d.t(20, 240, "Hele kjeden, Uke 36", 15, 600, INK)
    cc = chain4(d, 16, 252, 358, s36, u=0.55, fit=[s36], customer=None, cost=False, ls=13, sub_names=False, pv_label=False,
                orders=False, frame_me=True, production=False)
    y = cc["bottom"] + 34
    cmax = max(K["kost_per_rolle"].values())
    for r in CHAIN:
        st = s36[r]
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 700 if r == "Grossist" else 400, INK)
        d.t(370, y, f"{nf(st['cost'])} kr", 14, 600, INK, "end")
        cost_bar(d, 20, y + 7, 350, st["cl"], st["cr"], cmax, 7)
        y += 40
    d.t(20, y + 4, "Hvorfor ble det slik? Det finner dere ut", 14, 400, INK2)
    d.t(20, y + 23, "sammen i Debriefen.", 14, 400, INK2)
    d.button(20, 760, 350, 50, "Gå til Debrief")
    d.demodata(20, 830)
    d.end()

    # Under: hva lærer spilleren
    yt = y0 + 844 * s + 48
    d.t(40, yt, "Hva spilleren lærer av å se kjeden, grafen og kostnaden uke for uke", 24, 600, INK)
    tekst = [
        "Røret er det som er på vei, delt i uker og tegnet på samme skala som lageret. Det du bestiller i dag, står bakerst og rykker én plass per uke.",
        "Grafen under viser historien: lageret faller med akkurat det ordre inn er større enn levering. Regnestykket står i tallene, ikke bare i formen.",
        "Kostnaden står ved noden, delt i lager og restordre. Hver uke med restordre koster dobbelt så mye som en uke med like mye lager.",
        "I Klassespillet må du selv legge sammen røret og noden. Først etter Debriefen tegner skjermen summen som Posisjon, i Replay.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 34, tx, colw, 15, 20, fill=INK)
    ys = yt + 132
    d.t(40, ys, "Røret sett fra fem uker: 24 rykker mot noden, og i Uke 15 kommer 17. Resten ligger hos leverandøren uten dato.", 17, 600, INK)
    cw5 = (2100 - 80 - 4 * 36) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (cw5 + 36)
        typed = 24 if wk == 11 else G.order(wk)
        st = state(G, wk)
        cap = {11: "Uke 11: 24 bestilt", 12: "Uke 12: tre plasser igjen", 13: "Uke 13: to plasser igjen", 14: "Uke 14: neste uke",
               15: f"Uke 15: {G.levering(15)} kom, {G.overdue(15)} uten dato"}[wk]
        d.t(xx, ys + 28, cap, 14, 600, INK2)
        chain_seat(d, xx, ys + 34, cw5, st, typed, u=1.1, up=58, down=36, cost=False, small=12, mark=15, title=True, typed_bold=False)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, f"{NAME}, grafgrammatikken over tid",
            "Saras ledd, meteogram, matrise og kostnad i Uke 5, 11, 18 og 29 på én felles tidsakse, med hvilket prinsipp hver del lærer bort, og hele kjeden mot simulert referanse slik den vises etter Debriefen.")
    d.t(40, 54, "Fire deler, én tidsakse: Saras ledd i Uke 5, 11, 18 og 29", 34, 700, INK)
    d.para(40, 88, "Til venstre er leddet slik telefonen tegner det den uka. I midten står meteogrammet, og nederst samme tall i matrisen, kolonne for kolonne. Rammene i matrisen er de fire ukene.", 1400, 16, 22, fill=INK2)
    keyx = 1500
    weeks = [5, 11, 18, 29]
    sts = {w: state(G, w) for w in weeks}
    up = max(max([q for _, q in sts[w]["pipe"]] + [G.order(w), sts[w]["lager"], min(sts[w]["over"], OVER_CAP)]) for w in weeks) * 1.0 + 21
    down = max(sts[w]["rest"] for w in weeks) * 1.0 + 21
    notes = {
        5: [("P1 Lager er en opphopning", "Inn 4, ut 4, lager 12. Boksen står stille fordi strømmene er like, ikke fordi ingenting skjer."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte. Sara har ingen annen kilde."),
            ("Til neste ordre", "En rolig node betyr bare at ingenting har nådd deg ennå.")],
        11: [("P3 Det som er på vei", f"Røret holder {G.paavei(11)}, noden {sg(G.net(11))}. Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}, med 24 blir den {G.posisjon(11) + 24}."),
             ("P2 Forsinkelse", "24 legger seg bakerst og kommer om lag Uke 15. Det som skjer de neste tre ukene er allerede bestemt."),
             ("Til neste ordre", "Se på hele røret, ikke bare den røde boksen.")],
        18: [("P3 og P7", f"{G.paavei(18)} på vei, {G.overdue(18)} av dem uten dato hos leverandøren. En ny stor ordre legger seg bakerst og gir leverandøren et større tall å svare på."),
             ("P8 Restordre koster dobbelt", f"Restordre {G.rest[17]} koster {nf(G.rest[17] * RK)} kr denne uka. Totalkostnaden har vokst fra {nf(G.kostsum(11))} til {nf(G.kostsum(18))} kr på sju uker."),
             ("Til neste ordre", "Spør hva røret gjør med noden når det kommer fram.")],
        29: [("P1 Samme regning, motsatt fortegn", f"Røret tømte seg nesten samtidig, og noden ble til lager {G.lager[28]}. Lager koster {nf(G.lager[28] * LK)} kr per uke."),
             ("P8 og kjeden", f"Saras regning endte på {nf(G.kostsum(36))} kr, hvorav {nf(sum(G.rest) * RK)} kr restordre. Målet er lavest kostnad for hele kjeden."),
             ("Til neste ordre", "Hvor mye du vil ha igjen, må du bestemme selv.")],
    }
    y = 130
    x0, wplot = 560, 900
    rh = 200
    m = None
    for wk in weeks:
        st = sts[wk]
        d.t(40, y + 26, f"Uke {wk}", 26, 700, INK)
        d.t(40, y + 50, f"Posisjon {sg(G.posisjon(wk))}", 15, 600, INK)
        d.t(40, y + 70, f"Totalkostnad", 14, 400, INK2)
        d.t(40, y + 89, f"{nf(st['cost'])} kr", 16, 700, INK)
        cost_bar(d, 40, y + 97, 104, st["cl"], st["cr"], G.kostsum(36), 6)
        d.t(40, y + 120, f"lager {nf(st['cl'])}", 12, 400, INK2)
        d.t(40, y + 136, f"restordre {nf(st['cr'])}", 12, 400, INK2)
        chain_seat(d, 150, y + 4, 392, st, G.order(wk), u=1.0, up=up, down=down, cost=False, small=12, sw=28, nw=52, ext_w=58)
        m = meteo(d, G, x0, y + 4, wplot, wk, G.order(wk), wmin=1, wmax=36, hn=96, hf=30, gap=6, titles=False, left=40, xstep=4,
                  proj=False, actual=False, nowlabel="Nå", overduenote=False, connector=True, ordlabel=False, netlabel=False,
                  ls=12, axislabel=False, arrnums=False)
        ny = y + 14
        for head, body in notes[wk]:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 18, body, 460, 13.5, 17, fill=INK2) + 4
        d.line(40, y + rh - 6, 1960, y + rh - 6, HAIR, 1)
        y += rh
    # Matrisen på samme tidsakse
    ax = m["ax"]
    week_ticks(d, ax, y + 12, [1, 4, 8, 12, 16, 20, 24, 28, 32, 36] + weeks, None, 12)
    for wk in weeks:
        d.t(ax.xc(wk), y + 12, wk, 12, 700, INK, "middle")
    rows = [{"label": "Ordre inn", "vals": G.inn}, {"label": "Levering", "vals": G.levering},
            {"label": "Netto lager", "vals": G.net, "kind": "div"}, {"label": "På vei", "vals": G.paavei},
            {"label": "Din ordre", "vals": G.order, "kind": "seq"},
            {"label": "Kostnad per uke", "vals": lambda k: week_cost(G, k), "kind": "cost"},
            {"label": "Akkumulert, kr", "vals": lambda k: G.kostsum(k), "kind": "cost"}]
    ym = y + 22
    ye = matrix(d, ax, ym, rows, ch=19, ls=10.5, label_x=ax.x0 - 6)
    for wk in weeks:
        d.rect(ax.xl(wk), ym - 2, ax.slot, ye - ym + 2, "none", INK, 1.5)
    d.t(160, ym + 14, "Matrisen", 15, 600, INK)
    d.para(160, ym + 34, "Samme tall som noden, røret og grafen. Netto lager i uke 11: 0 − 13 = −13. Kostnaden: 13 × 1,00 = 13.", 230, 13, 17, fill=INK2)
    d.t(keyx, ym + 14, "P1 i matrisen", 15, 600, INK)
    d.para(keyx, ym + 34, "Netto lager endres med levering minus ordre inn, kolonne for kolonne. Akkumulert kostnad er summen av raden over. Bygget stopper hvis tallene ikke stemmer med loggen.", 460, 13.5, 17, fill=INK2)

    # Etter Debriefen: hele kjeden mot simulert referanse
    yb = ye + 40
    d.line(40, yb - 18, 1960, yb - 18, INK, 1.2)
    d.t(40, yb + 8, "Etter Debriefen: hele kjeden i Uke 18, mot simulert referanse", 22, 600, INK)
    d.t(40, yb + 30, "Simulert: samme kunder, men alle fire teller det som er på vei. Viser en sammenheng, ingen fasit.", 14, 400, INK2)
    allst = ALL4 = [states(w) for w in range(1, 37)] + [states(w, SIM) for w in range(1, 37)]
    s18 = states(18)
    sim18 = states(18, SIM)
    cmax = max(max(s18[r]["cost"], sim18[r]["cost"]) for r in CHAIN)
    d.t(40, yb + 60, "Spill 17", 15, 700, INK)
    chain4(d, 40, yb + 66, 690, s18, u=0.42, fit=allst, customer=DEM[17], cost=True, cmax=cmax, ls=12, cost_label=False, pv_label=True)
    d.t(770, yb + 60, "Simulert", 15, 700, INK)
    chain4(d, 770, yb + 66, 690, sim18, u=0.42, fit=allst, customer=DEM[17], cost=True, cmax=cmax, ls=12, cost_label=False, pv_label=True)
    tx = keyx
    cols = [tx + 220, tx + 340, tx + 460]
    yy = yb + 8
    d.t(cols[0], yy, "Spill 17", 13, 600, INK, "end")
    d.t(cols[1], yy, "Bare Sara", 13, 600, INK, "end")
    d.t(cols[2], yy, "Alle fire", 13, 600, INK, "end")
    d.line(tx, yy + 7, cols[2], yy + 7, HAIR2, 1)
    Bf, Af = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    rr = [("Kjeden, kr", nf(K["kjedekost"], 0), nf(Bf["kjedekost"], 0), nf(Af["kjedekost"], 0)),
          ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(Bf["kost_per_rolle"]["Grossist"]), nf(Af["kost_per_rolle"]["Grossist"])),
          ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(Bf["forsterkning"]["Grossist"]), fx1(Af["forsterkning"]["Grossist"])),
          ("Forsterkning, Fabrikk", fx1(K["forsterkning"]["Fabrikk"]), fx1(Bf["forsterkning"]["Fabrikk"]), fx1(Af["forsterkning"]["Fabrikk"]))]
    yy += 26
    for row in rr:
        d.t(tx, yy, row[0], 13, 400, INK)
        for c_, v in zip(cols, row[1:]):
            d.t(c_, yy, v, 13, 400, INK, "end")
        d.line(tx, yy + 7, cols[2], yy + 7, HAIR, 1)
        yy += 23
    ny = d.para(tx, yy + 10, "P5, P6: når ledd teller røret, faller forsterkningen også hos de andre. Formen består, for strukturen er den samme.", 460, 13, 17, fill=INK2)
    ny = d.para(tx, ny + 4, "P7: å telle røret er ikke nok alene. En regel som jaget siste ordre for hardt, ga Fabrikk 12× i simuleringen.", 460, 13, 17, fill=INK2)
    ny = d.para(tx, ny + 6, "Hjelpegrad: Klassespillet viser røret, men ikke summen. Replay tegner Posisjon og projeksjonen.", 460, 13, 17, 600, INK)
    d.demodata(40, 1392, "Demodata. Simulerte referanser er merket Simulert.", 13)
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
