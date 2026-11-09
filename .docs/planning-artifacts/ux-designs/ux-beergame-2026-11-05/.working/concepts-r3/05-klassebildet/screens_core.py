"""Kjerneflatene for 05 Klassebildet: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e05lib import *

G = Seat()
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
K = FX["spill17"]
PU, PCAP = 1.2, 40   # kjedebåndets skala på telefon: 1,2 px per enhet, ±40 enheter


def flow_title(d, x, y, g, wk, ls=13):
    """Tittellinja i inn og ut-panelet bærer ukas tall. Lavest først, slik stolpen er stablet."""
    lev, inn = g.levering(wk), g.inn(wk)
    first = ("Levering", lev, BASE)
    second = ("Ordre inn", inn, RED if inn > lev else BASE)
    if lev > inn:
        first, second = ("Ordre inn", inn, BASE), ("Levering", lev, BLUE)
    xx = x
    for lab, val, col in (first, second):
        d.rect(xx, y - 10, 10, 10, col)
        s = f"{lab} {val}"
        d.t(xx + 14, y, s, ls, 600, INK)
        xx += 14 + text_w(s, ls) + 16


def phone_chart(d, g, wk, typed, y=100, proj=False, ghost=None, hn=120, hf=48):
    m = meteo(d, g, 16, y, 358, wk, typed, left=30, hn=hn, hf=hf, gap=16, t_flow="", t_ord="", proj=proj, ghost=ghost)
    flow_title(d, 16, m["yflow"] - 7, g, wk)
    d.t(16, m["yord"] - 7, "Din ordre", 13, 600, INK)
    wid = m["fx1"] - m["fx0"] - 10
    ny = m["Y"](g.net(wk))
    top = ny > m["ynet"] + hn * 0.4
    yy = m["ynet"] + (18 if top else hn - 26)
    for ln in wrap("Bestilt, ikke garantert", wid, 13):
        d.t(m["fx0"] + 6, yy, ln, 13, 400, INK2)
        yy += 16
    return m


def phone_top(d, g, wk, typed, hn=108, show_pos=False, proj=False):
    """Telefonens faste topp: Uke og Totalkostnad, kjedebåndet, meteogrammet."""
    game_header(d, wk, g.kostsum(wk))
    c = chain_seat(d, 20, 104, 350, g, wk, typed, u=PU, cap=PCAP, show_pos=show_pos)
    return phone_chart(d, g, wk, typed, y=c["bottom"] + 12, hn=hn, proj=proj)


def order_input(d, y, wk, typed, link="Tall og kostnad"):
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, f"Din ordre for Uke {wk}", 15, 600, INK)
    d.t(370, y + 26, link, 14, 600, BLUE, "end", 'text-decoration="underline"')
    yb = y + 38
    d.rect(20, yb, 350, 54, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(78, yb, 78, yb + 54, HAIR2, 1)
    d.line(312, yb, 312, yb + 54, HAIR2, 1)
    d.line(40, yb + 27, 58, yb + 27, INK, 2)
    d.line(332, yb + 27, 350, yb + 27, INK, 2)
    d.line(341, yb + 18, 341, yb + 36, INK, 2)
    if typed is None:
        d.t(195, yb + 34, "Antall enheter", 18, 400, INK3, "middle")
    else:
        d.t(195, yb + 39, typed, 32, 700, INK, "middle")
    return yb + 54


def waiting_rows(d, y, rows, x=20, width=350, lh=30):
    """rows: (rolle, navn, status, ferdig?). Status bæres av tekst og fylt/åpen sirkel, aldri farge alene."""
    for rolle, navn, status, done in rows:
        if done:
            d.circle(x + 6, y - 5, 5, INK)
        else:
            d.circle(x + 6, y - 5, 5, PAPER, INK, 1.5)
        d.t(x + 20, y, rolle, 14, 600, INK)
        d.t(x + 100, y, navn, 14, 400, INK)
        d.t(x + width, y, status, 14, 400, INK2, "end")
        y += lh
    return y


def seat_sara_klar():
    return [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "Jonas", "venter, 3 min", False), ("Grossist", "Sara", "har bestilt", True)]


def seat_matrix_rows(g, typed_week=None, typed=None):
    return [
        ("Ordre inn", g.inn, "flow"),
        ("Levering", g.levering, "flow"),
        ("Sendt", g.sendt, "flow"),
        ("Netto lager", g.net, "net"),
        ("På vei", g.paavei, "flow"),
        ("Din ordre", (lambda k: typed if k == typed_week else g.order(k)), "flow"),
        ("Kostnad, kr", (lambda k: seat_week_cost(g, k)), "cost"),
    ]


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, "Klassebildet, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn: kjedebånd øverst, meteogram under og ordrefelt. Ved siden av panelet Tall og kostnad, samme skjerm på laptop og forskjellen mellom Klassespill og Replay.")
    d.t(40, 46, "Uke 11. Kjedebåndet viser hvor varene er nå, grafen viser hvordan det ble slik.", 26, 600, INK)

    # Telefon
    phone(d, 40, 84, 1.0)
    m = phone_top(d, G, 11, 24)
    yb = order_input(d, m["axisbot"] + 12, 11, 24)
    d.t(20, yb + 22, "Kommer fram om lag Uke 15. Kan ikke endres", 13, 400, INK2)
    d.t(20, yb + 38, "etter at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 50, 350, 50, "Bekreft ordre på 24")
    d.t(20, yb + 124, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 124, a="end")
    d.end()
    d.t(235, 952, "Telefon, Klassespill: eget ledd øverst, tiden under.", 14, 400, INK2, "middle")

    # Åpnet panel: Tall og kostnad
    px = 460
    phone(d, px, 84, 1.0)
    d.t(20, 66, "Tall og kostnad", 24, 700, INK)
    d.t(370, 62, "Lukk", 15, 600, BLUE, "end", 'text-decoration="underline"')
    d.t(20, 88, "Grossist, Spill 17. Uke 6 til 11", 14, 400, INK2)
    ax = Axis(112, 258, 6, 11)
    for k in range(6, 12):
        d.t(ax.xc(k), 118, k, 13, 700 if k == 11 else 400, INK if k == 11 else INK3, "middle")
    d.t(20, 118, "Uke", 13, 400, INK3)
    ye = matrix(d, ax, 126, seat_matrix_rows(G, 11, 24), 6, 11, ch=30, ls=14, label_x=20, label_size=14, hi_week=11)
    d.t(20, ye + 22, "Rød celle: restordre eller restordrekost. Blå: lager.", 13, 400, INK2)
    y = ye + 58
    d.t(20, y, "Regnestykket", 17, 600, INK)
    y += 26
    d.t(20, y, "Posisjon = Lager − Restordre + På vei", 14, 400, INK2)
    y += 24
    d.t(20, y, "Før ordren", 15, 400, INK)
    d.t(370, y, f"{G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}", 15, 600, INK, "end")
    y += 26
    d.t(20, y, "Med ordren på 24", 15, 400, INK)
    d.t(370, y, f"{G.posisjon(11)} + 24 = {G.posisjon(11) + 24}", 15, 600, INK, "end")
    y += 44
    lk = sum(G.lager[:11]) * LAGERKOST
    rk = sum(G.rest[:11]) * RESTKOST
    assert abs(lk + rk - G.kostsum(11)) < 1e-9
    d.t(20, y, "Totalkostnad hittil", 17, 600, INK)
    d.t(370, y, f"{nf(G.kostsum(11))} kr", 17, 700, INK, "end")
    y += 14
    split_bar(d, 20, y, 350, 14, lk, rk, G.kostsum(11))
    y += 34
    d.t(20, y, f"Restordrekost {nf(rk)} kr", 14, 600, INK)
    d.t(370, y, f"Lagerkost {nf(lk)} kr", 14, 600, INK, "end")
    y += 22
    d.para(20, y, f"Denne Uka: {G.rest[10]} i restordre × 1,00 = {nf(G.kostsum(11) - G.kostsum(10))} kr. Restordre koster dobbelt så mye som lager.", 350, 13, 18, fill=INK2)
    yc = 724
    d.t(20, yc, "Kostnad per uke, kr", 15, 600, INK)
    axc = Axis(20, 350, 1, 11)
    cost_bars(d, axc, yc + 8, 48, lambda k: seat_week_cost(G, k), 1, 11, 14)
    for k in range(1, 12):
        lk_, rk_ = seat_week_cost(G, k)
        d.t(axc.xc(k), yc + 72, cell_text(lk_ + rk_, "cost"), 12, 700 if k == 11 else 400, INK, "middle")
    d.t(20, 826, "Vis alle uker som tabell", 14, 600, BLUE, "start", 'text-decoration="underline"')
    d.demodata(370, 826, a="end")
    d.end()
    d.t(655, 952, "Ett trykk unna: setets egen matrise, regnestykket og kostnaden.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 84, 680, 588
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 104, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    c = chain_seat(d, lx + 24, ly + 58, 420, G, 11, 24, u=0.8, cap=40, slot=44)
    m2 = meteo(d, G, lx + 16, c["bottom"] + 8, 428, 11, 24, left=50, hn=110, hf=44, gap=14, t_flow="", t_ord="", sendt=False, axislabel=False)
    flow_title(d, lx + 16, m2["yflow"] - 7, G, 11)
    d.t(lx + 16, m2["yord"] - 7, "Din ordre", 13, 600, INK)
    ax2 = m2["ax"]
    rows = [("Netto", G.net, "net"), ("Inn", G.inn, "flow"), ("Ordre", lambda k: 24 if k == 11 else G.order(k), "flow"),
            ("kr", lambda k: seat_week_cost(G, k), "cost")]
    ym = matrix(d, ax2, m2["ybot"] + 8, rows, 1, 11, ch=18, ls=11, label_x=lx + 16, label_size=12, hi_week=11)
    xaxis(d, ax2, ym + 15, [1, 3, 5, 7, 9, 11, 13, 15], 11)
    cx = lx + 476
    y = ly + 74
    d.t(lx + lw - 24, ly + 40, f"Totalkostnad {nf(G.kostsum(11))} kr", 14, 600, INK, "end")
    for lab, val in [("Lager", G.lager[10]), ("Restordre", G.rest[10]), ("Ordre inn", G.inn(11)), ("Levering", G.levering(11)),
                     ("Sendt", G.sendt(11)), ("På vei", f"{G.paavei(11)} + 24"), ("Neste levering", G.order(8))]:
        d.t(cx, y, lab, 14, 400, INK)
        d.t(lx + lw - 24, y, val, 14, 600, INK, "end")
        d.line(cx, y + 7, lx + lw - 24, y + 7, HAIR, 1)
        y += 27
    y += 16
    d.t(cx, y, "Kostnad hittil", 14, 600, INK)
    split_bar(d, cx, y + 10, lx + lw - 24 - cx, 10, lk, rk, G.kostsum(11))
    d.t(cx, y + 40, f"Restordre {nf(rk)}", 13, 400, INK2)
    d.t(lx + lw - 24, y + 40, f"Lager {nf(lk)}", 13, 400, INK2, "end")
    y += 74
    d.t(cx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, y + 10, lx + lw - 24 - cx, 48, PAPER, INK, 1.4, 6)
    d.t((cx + lx + lw - 24) / 2, y + 45, 24, 30, 700, INK, "middle")
    d.button(cx, y + 70, lx + lw - 24 - cx, 44, "Bekreft ordre på 24", size=15)
    d.t(cx, y + 136, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(lx + lw - 24, ly + lh - 14, a="end")
    d.t(lx, ly + lh + 22, "Laptop: bånd, graf og tall på samme tidsakse. Hver Uke har både strek og tall.", 14, 400, INK2)

    # Hjelpegrad
    hy = 722
    d.t(lx, hy, "Hjelpegrad: samme kjedebånd på to nivåer", 20, 600, INK)
    pw = 330
    d.t(lx, hy + 28, "Klassespill: rommene, ingen sum", 14, 600, INK)
    chain_seat(d, lx, hy + 40, pw, G, 11, 24, u=0.8, cap=40, slot=30, ls=12)
    bx = lx + pw + 20
    d.t(bx, hy + 28, "Replay, etter Debriefen: Posisjon tegnet inn", 14, 600, INK)
    chain_seat(d, bx, hy + 40, pw, G, 11, 24, u=0.8, cap=40, slot=30, ls=12, show_pos=True)
    yn = hy + 206
    d.para(lx, yn, "I Klassespillet ser Sara hvert rom i røret, men må legge sammen selv. Det er denne summen de fleste lar være å regne, og Debriefen viser hva det kostet.", pw - 6, 14, 19, fill=INK2)
    d.para(bx, yn, "I Replay står summen under båndet, og meteogrammet får den stiplede projeksjonen. Ingen anbefalt ordre, bare regnestykket.", pw - 6, 14, 19, fill=INK2)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Klassebildet, en Uke i spillet",
            "Seks telefonruter med kjedebånd og meteogram: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter med kjedens kostnad.")
    s = 0.76
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 180
    d.t(40, 50, "En Uke i Klassebildet: røret rykker fram, nå-streken flytter seg, og kostnaden vokser med restordren.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Levering og ordre inn er nye. Røret har rykket ett rom fram, og rommet fire uker fram står tomt."),
        ("B  Beslutningen: 24", "Sara taster, og 24 står i røret ved Uke 15, bak 4, 4 og 8. Ingen fasit ved siden av."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Nå-streken og røret flytter seg én Uke. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens kostnad først, så per Rolle og per kostnadsart. Hele kjeden kommer i Debriefen."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 94, h, 20, 600, INK)
        d.para(x, 120, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone(d, px(0), y0, s)
    m = phone_top(d, G, 11, None)
    yb = order_input(d, m["axisbot"] + 12, 11, None)
    d.t(20, yb + 24, f"Sist Uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.button(20, yb + 44, 350, 50, "Bekreft ordre", primary=False)
    d.demodata(20, 830)
    d.end()

    # B
    phone(d, px(1), y0, s)
    m = phone_top(d, G, 11, 24)
    yb = order_input(d, m["axisbot"] + 12, 11, 24)
    d.t(20, yb + 24, "Kommer fram om lag Uke 15. Kan ikke endres.", 13, 400, INK2)
    d.button(20, yb + 44, 350, 50, "Bekreft ordre på 24")
    d.demodata(20, 830)
    d.end()

    # C
    phone(d, px(2), y0, s)
    m = phone_top(d, G, 11, 24)
    y = m["axisbot"] + 12
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 60, seat_sara_klar(), lh=28)
    d.t(20, y + 186, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 830)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    m = phone_top(d, G, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["ynet"] - 2, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["axisbot"] + 12
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 28, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    rr = [("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w))]
    yy = y + 56
    for lab, v in rr:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 22
    d.t(20, yy, "Restordre", 14, 400, INK)
    d.t(370, yy, f"{G.rest[w - 2]} blir {G.rest[w - 1]}", 14, 600, INK, "end")
    yy += 22
    d.t(20, yy, "Totalkostnad", 14, 400, INK)
    d.t(370, yy, f"+ {nf(G.kostsum(w) - G.kostsum(w - 1))} kr", 14, 600, INK, "end")
    d.demodata(20, 830)
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    m = phone_top(d, G, w, G.order(w), hn=100)
    y = m["axisbot"] + 8
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 24, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller for Jonas", "bestiller", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 52, rows, lh=24)
    d.rect(20, yy - 8, 350, 70, TINT, None, 1, 6)
    d.t(32, yy + 14, "Slik ser Jonas det etter fraværet:", 13, 400, INK2)
    d.t(32, yy + 34, "KI-spiller bestiller for deg.", 14, 600, INK)
    d.button(240, yy + 12, 120, 40, "Ta tilbake setet", primary=False, size=13)
    d.demodata(20, 830)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 66, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 88, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 128, "Kjedens kostnad", 15, 400, INK2)
    d.t(20, 166, f"{nf(K['kjedekost'])} kr", 38, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    splits = {r: series_split(K, r) for r in ROLES}
    tl = sum(a for a, b in splits.values())
    tr = sum(b for a, b in splits.values())
    assert abs(tl + tr - K["kjedekost"]) < 1e-9
    split_bar(d, 20, 180, 350, 14, tl, tr, K["kjedekost"])
    d.t(20, 214, f"Restordre {nf(tr)} kr", 14, 600, INK)
    d.t(370, 214, f"Lager {nf(tl)} kr", 14, 600, INK, "end")
    y = 256
    mx = max(K["kost_per_rolle"].values())
    for r in ROLES:
        v = K["kost_per_rolle"][r]
        a, b = splits[r]
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        d.t(370, y, f"{nf(v)} kr", 14, 600, INK, "end")
        split_bar(d, 20, y + 7, 350 * v / mx, 8, a, b, v)
        y += 42
    y += 6
    d.para(20, y, "Rødt er restordrekost, blått lagerkost. Hver Rolle betalte mest for det som manglet.", 350, 13, 18, fill=INK2)
    y += 50
    d.t(20, y, "Ditt netto lager, hele spillet", 14, 600, INK)
    axf = Axis(50, 320, 1, G.n)
    grid(d, axf, y + 12, 120, -40, 30, (-40, -20, 0, 20))
    net_area(d, axf, y + 12, 120, G.net, 1, G.n)
    xaxis(d, axf, y + 150, [1, 12, 24, 36], None)
    d.para(20, y + 182, "Hvorfor svingte det, og hva så de andre? Hele kjeden vises i Debriefen.", 350, 14, 19, fill=INK2)
    d.button(20, 750, 350, 50, "Gå til Debrief")
    d.demodata(20, 830)
    d.end()

    # Under: hva lærer spilleren
    yt = y0 + 844 * s + 48
    d.t(40, yt, "Hva spilleren lærer av å se kjeden, grafen og kostnaden uke for uke", 24, 600, INK)
    tekst = [
        "Kjedebåndet viser røret som fire rom, ett per Uke. En ordre legger seg bakerst og rykker ett rom fram hver Uke. Det du får nå, bestemte du for fire Uker siden.",
        "Lageret står som boks på samme skala som røret. Når restordren vokser og røret er fullt, ser Sara begge deler på én gang, og kan spørre hva som allerede er på vei.",
        "Grafen under husker hver Uke. Rødt i midtfeltet er ordre inn utover levering, og nøyaktig så mye faller netto lager. Summen er regnestykket, ikke bare mønsteret.",
        "Totalkostnaden øverst vokser med 1,00 per enhet i restordre og 0,50 per enhet på lager. Først når spillet slutter, ser Sara hva kjeden betalte til sammen.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 34, tx, colw, 15, 20, fill=INK)
    ys = yt + 150
    d.t(40, ys, "Ordren på 24 i røret, Uke 11 til 15: den rykker ett rom fram hver Uke, og i Uke 15 kommer det 17.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 30) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 30)
        typed = 24 if wk == 11 else G.order(wk)
        chain_seat(d, xx, ys + 10, pw2, G, wk, typed, u=0.8, cap=30, slot=38, ls=12)
        cap_ = {11: "Uke 11: 24 bestilt", 12: "Uke 12: tre rom igjen", 13: "Uke 13: to rom igjen", 14: "Uke 14: neste Uke",
                15: f"Uke 15: {G.levering(15)} kom, {G.overdue(15)} forsinket uten dato"}[wk]
        d.t(xx, ys + 162, cap_, 14, 600 if wk in (11, 15) else 400, INK if wk in (11, 15) else INK2)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Klassebildet, grafgrammatikken over tid",
            "Saras kjedebånd, meteogram, matrise og kostnad i Uke 5, 11, 18 og 29 på én felles tidsakse, med sammenligning mot simulert referanse og klassens 41 ferdige spill etter Debriefen.")
    d.t(40, 52, "Ett ledd, fire Uker: bånd, graf, tall og kostnad på samme akse", 34, 700, INK)
    d.para(40, 84, "Kjedebåndet til venstre er Uka slik Sara ser den. Til høyre står de samme tallene over tid, og nå-streken vandrer mot høyre. Det åpne til høyre for streken blir historie i raden under.", 1420, 16, 22, fill=INK2)

    keyx = 1500
    d.t(keyx, 52, "Slik leses raden", 17, 600, INK)
    d.path(f"M{keyx} 72 L{keyx + 34} 72", stroke=GREY, sw=2, dash="6 4")
    d.t(keyx + 42, 77, "Projeksjon. Bare i Replay, aldri i Klassespillet.", 14, 400, INK2)
    d.line(keyx, 94, keyx + 34, 94, INK, 1)
    d.t(keyx + 42, 99, "Det som faktisk skjedde. Bare på dette arket.", 14, 400, INK2)
    d.rect(keyx + 10, 108, 14, 16, PAPER, BLUE, 1.2)
    d.t(keyx + 42, 121, "Bestilt, med plan om å komme den Uka.", 14, 400, INK2)

    rows = [
        (5, G.order(5), [
            ("P2 Forsinkelse", "Røret har fire like rom med 4. Hoppet hos kundene i Uke 5 har ikke nådd Sara, og det gjør det først i Uke 7."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte, ikke det kundene kjøpte. Sara har ingen annen kilde."),
            ("Til neste ordre", "Et rolig bånd betyr bare at ingenting har nådd deg ennå."),
        ]),
        (11, 24, [
            ("P3 Det som er på vei", f"Røret holder {G.paavei(11)}. Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir den {G.posisjon(11) + 24}."),
            ("P1 Lager er en opphopning", f"Matrisen viser regnestykket: {sg(G.net(10))} + {G.levering(11)} levert − {G.inn(11)} inn = {sg(G.net(11))}."),
            ("P8 Restordre koster dobbelt", f"{G.rest[10]} i restordre koster {nf(G.rest[10] * RESTKOST)} kr denne Uka. Samme antall på lager hadde kostet {nf(G.rest[10] * LAGERKOST)}."),
        ]),
        (18, G.order(18), [
            ("P2 og P3 igjen", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem ligger uten dato hos leverandøren. Rommet lengst til venstre er det du ikke kan tidfeste."),
            ("P7 Overreaksjon forsterker", "En ny ordre kommer ikke raskere enn de gamle. Den legger seg bakerst og gir leverandøren et større tall å svare på."),
            ("Til neste ordre", f"Restordre {G.rest[17]} er det du ser. Spør hva {G.paavei(18)} i røret gjør når de kommer."),
        ]),
        (29, G.order(29), [
            ("P8 Begge deler koster", f"Lager {G.lager[28]} × 0,50 = {nf(G.lager[28] * LAGERKOST)} kr per Uke. Kostnadsraden skifter fra rødt til blått, men slutter ikke å telle."),
            ("P1 Samme regning, motsatt fortegn", "Blå stolper i Uke 23 til 26 er det som kom nesten samtidig. Toppen er summen av gamle ordrer."),
            ("Til neste ordre", "Røret er nesten tomt. Hvor mye du vil ha igjen, må du bestemme selv."),
        ]),
    ]
    y = 140
    xm, wplot = 520, 940
    hn, hf = 80, 28
    rh = 242
    for now, typed, notes in rows:
        d.t(40, y + 22, f"Uke {now}", 26, 700, INK)
        d.t(160, y + 22, f"Totalkostnad {nf(G.kostsum(now))} kr", 14, 600, INK)
        chain_seat(d, 40, y + 36, 420, G, now, typed, u=0.8, cap=40, slot=44, ls=12)
        m = meteo(d, G, xm, y, wplot, now, typed, wmin=1, wmax=36, hn=hn, hf=hf, gap=6, titles=False, left=96, xstep=4,
                  proj=True, actual=True, nowlabel="Nå", overduenote=False, connector=True, ordlabel=False, netlabel=False, axislabel=False,
                  ticks=(-40, 0, 20))
        ax = m["ax"]
        d.t(xm, m["ynet"] + 12, "Netto lager", 12, 600, INK2)
        d.t(xm, m["yflow"] + hf - 2, "Inn og ut, P1", 12, 400, INK2)
        d.t(xm, m["yord"] + m["ho"] - 2, "Egen ordre, P2", 12, 400, INK2)
        mrows = [("Netto lager", G.net, "net"), ("Din ordre", lambda k, t=typed, n=now: t if k == n else G.order(k), "flow"),
                 ("Kostnad, kr", lambda k: seat_week_cost(G, k), "cost")]
        ye = matrix(d, ax, m["ybot"] + 6, mrows, 1, now, ch=15, ls=10, label_x=xm, label_size=12, gap=1.2)
        d.rect(ax.xr(now), m["ybot"] + 6, ax.xr(36) - ax.xr(now), 45, TINT)
        xaxis(d, ax, ye + 13, [1, 5, 9, 13, 17, 21, 25, 29, 33, 36], now, 12)
        # projeksjon mot det som skjedde
        p = G.projection(now, typed)[-1][1]
        act = G.net(now + 4)
        Y = m["Y"]
        ex = ax.xr(now + 4) + 6
        if now == 29:
            ex = ax.xr(now + 4) + 4
        if abs(Y(p) - Y(act)) < 16:
            d.t(ex, Y(p) - 2, f"Planlagt {sg(p)}", 13, 600, INK2, extra=halo())
            d.t(ex, Y(p) + 13, f"Det ble {sg(act)}", 13, 600, INK, extra=halo())
        else:
            d.t(ex, Y(p) + 4, f"Planlagt {sg(p)}", 13, 600, INK2, extra=halo())
            d.t(ex, Y(act) + 4, f"Det ble {sg(act)}", 13, 600, INK, extra=halo())
        ny = y + 14
        for head, body in notes:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 19, body, 460, 14, 18, fill=INK2) + 4
        d.line(40, y + rh - 8, 1960, y + rh - 8, HAIR, 1)
        y += rh

    # Etter Debriefen
    y += 6
    d.t(40, y + 22, "Etter Debriefen: samme kjede mot simulert referanse, og mot klassen", 22, 600, INK)
    d.t(40, y + 44, "Simulert: samme kjede, samme kunder. Tallene viser en sammenheng og er ingen fasit.", 14, 400, INK2)
    gy = y + 66
    gh = 150
    # a) netto lager
    ax = Axis(76, 430, 1, 36)
    d.t(40, gy - 4, "Saras netto lager", 14, 600, INK)
    Y = grid(d, ax, gy + 8, gh, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax, gy + 8, gh, G.net, 1, 36)
    d.path("M" + " L".join(f"{ax.xc(w):.1f} {Y(BARE.net(w)):.1f}" for w in range(1, 37)), stroke=INK, sw=1.6)
    d.path("M" + " L".join(f"{ax.xc(w):.1f} {Y(ALLE.net(w)):.1f}" for w in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax.xc(16), Y(-36), f"Spill 17, lavest {sg(min(G.net_))}", 13, 600, RED, "end")
    d.t(ax.xc(34), Y(BARE.net(33)) - 8, "Bare Sara teller", 13, 600, INK, "end", halo())
    d.t(ax.xc(27) + 6, Y(ALLE.net(27)) + 16, "Alle fire teller", 13, 600, GREY, extra=halo())
    xaxis(d, ax, gy + gh + 24, [1, 12, 24, 36], None)

    # b) kjedens kostnad akkumulert
    bx = 560
    d.t(bx, gy - 4, "Kjedens kostnad, akkumulert", 14, 600, INK)
    axb = Axis(bx + 44, 400, 1, 36)
    Yb = grid(d, axb, gy + 8, gh, 0, 2400, (0, 1000, 2000), 12)

    def cum(src):
        acc, out = 0.0, []
        for i in range(36):
            acc += sum(src["serier"][r]["lager"][i] * LAGERKOST + src["serier"][r]["restordre"][i] * RESTKOST for r in ROLES)
            out.append(acc)
        return out
    for src, col, sw, lab in ((K, INK, 2, None), (FX["bare_sara_teller_paa_vei"], INK2, 1.4, None), (FX["alle_teller_paa_vei"], GREY, 1.4, None)):
        c = cum(src)
        assert abs(c[-1] - src["kjedekost"]) < 1e-9
        d.path("M" + " L".join(f"{axb.xc(w):.1f} {Yb(c[w - 1]):.1f}" for w in range(1, 37)), stroke=col, sw=sw)
    d.t(axb.xc(36) - 4, Yb(K["kjedekost"]) - 8, f"Spill 17: {nf(K['kjedekost'])} kr", 13, 700, INK, "end", halo())
    d.t(axb.xc(36) + 4, Yb(FX['bare_sara_teller_paa_vei']['kjedekost']) + 4, f"{nf(FX['bare_sara_teller_paa_vei']['kjedekost'], 0)}", 13, 600, INK2)
    d.t(axb.xc(36) + 4, Yb(FX['alle_teller_paa_vei']['kjedekost']) + 14, f"{nf(FX['alle_teller_paa_vei']['kjedekost'], 0)}", 13, 600, GREY)
    xaxis(d, axb, gy + gh + 24, [1, 12, 24, 36], None)
    tl = sum(series_split(K, r)[0] for r in ROLES)
    tr = sum(series_split(K, r)[1] for r in ROLES)
    d.para(bx, gy + gh + 46, f"Spill 17: restordre {nf(tr)} kr, lager {nf(tl)} kr. Simulert: bare Sara teller {nf(FX['bare_sara_teller_paa_vei']['kjedekost'])}, alle fire teller {nf(FX['alle_teller_paa_vei']['kjedekost'])}.", 470, 13, 17, fill=INK2)

    # c) klassen
    cx0 = 1060
    d.t(cx0, gy - 4, "Grossist i 41 ferdige spill, og Sara", 14, 600, INK)
    axc = Axis(cx0 + 36, 384, 1, 36)
    Yc = grid(d, axc, gy + 8, gh, -50, 50, (-40, -20, 0, 20, 40), 12)
    q = [class_quart_net("Grossist", w) for w in range(1, 37)]
    band = "M" + " L".join(f"{axc.xc(w):.1f} {Yc(q[w - 1][2]):.1f}" for w in range(1, 37)) + " L" + " L".join(
        f"{axc.xc(w):.1f} {Yc(q[w - 1][0]):.1f}" for w in range(36, 0, -1)) + " Z"
    d.path(band, BASE, extra='fill-opacity="0.55"')
    d.path("M" + " L".join(f"{axc.xc(w):.1f} {Yc(q[w - 1][1]):.1f}" for w in range(1, 37)), stroke=INK2, sw=1.4, dash="4 3")
    d.path("M" + " L".join(f"{axc.xc(w):.1f} {Yc(G.net(w)):.1f}" for w in range(1, 37)), stroke=INK, sw=2)
    d.t(axc.xc(30), Yc(q[29][2]) - 8, "Midtre halvdel av klassen", 12, 600, INK2, "middle", halo())
    d.t(axc.xc(17) - 6, Yc(G.net(17)) + 4, "Sara", 13, 700, INK, "end", halo())
    xaxis(d, axc, gy + gh + 24, [1, 12, 24, 36], None)
    d.para(cx0, gy + gh + 46, "P6: Nesten alle Grossister svinger likt, også de med andre studenter. Sammenligner form, ikke kostnad, og viser ingen rangering.", 420, 13, 17, fill=INK2)

    d.t(keyx, y + 22, "Hjelpegrad", 20, 600, INK)
    ny = d.para(keyx, y + 48, "Klassespill: kjedebåndet med rom og tall, meteogrammet uten linje, matrise og kostnad ett trykk unna. Posisjon står bare som regnestykke i Tall.", 460, 14, 19, fill=INK)
    ny = d.para(keyx, ny + 4, "Replay: Posisjon tegnet under båndet og den stiplede projeksjonen åpnes. Studenten har da selv kjent på hva den gjør synlig.", 460, 14, 19, fill=INK)
    ny = d.para(keyx, ny + 8, "P7: Å telle det som er på vei er ikke nok alene. I simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17.", 460, 13, 17, fill=INK2)
    d.demodata(1960, 1390, "Demodata. Simulerte referanser er merket Simulert. Klassetall regnet fra 41 ferdige spill.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
