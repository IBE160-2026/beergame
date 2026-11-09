"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from d02lib import *

G = Seat()
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
K = FX["spill17"]


def flow_title(d, x, y, g, wk):
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
        d.t(xx + 14, y, s, 13, 600, INK)
        xx += 14 + text_w(s, 13) + 16


def phone_chart(d, g, wk, typed, proj=False, ghost=None, hn=170):
    m = meteo(d, g, 16, 100, 358, wk, typed, left=30, hn=hn, hf=64, gap=22, t_flow="", t_ord="", proj=proj, ghost=ghost)
    flow_title(d, 16, m["yflow"] - 7, g, wk)
    d.t(16, m["yord"] - 7, "Din ordre", 13, 600, INK)
    pv = g.paavei(wk)
    d.t(16 + 68, m["yord"] - 7, f"På vei {pv}" + (f" + {typed}" if typed is not None else ""), 13, 400, INK2)
    # merknad i høyre flate
    wid = m["fx1"] - m["fx0"] - 10
    ny = m["Y"](g.net(wk))
    top = ny > m["ynet"] + 90
    yy = m["ynet"] + (18 if top else 140)
    for ln in wrap("Bestilt, ikke garantert", wid, 13):
        d.t(m["fx0"] + 6, yy, ln, 13, 400, INK2)
        yy += 16
    return m


def order_input(d, y, wk, typed, arrival_week=None):
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, f"Din ordre for Uke {wk}", 15, 600, INK)
    d.t(370, y + 28, "Alle tall", 14, 600, BLUE, "end", 'text-decoration="underline"')
    yb = y + 42
    d.rect(20, yb, 350, 58, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(78, yb, 78, yb + 58, HAIR2, 1)
    d.line(312, yb, 312, yb + 58, HAIR2, 1)
    # stepper tegnet som former
    d.line(40, yb + 29, 58, yb + 29, INK, 2)
    d.line(332, yb + 29, 350, yb + 29, INK, 2)
    d.line(341, yb + 20, 341, yb + 38, INK, 2)
    if typed is None:
        d.t(195, yb + 39, "Antall enheter", 18, 400, INK3, "middle")
    else:
        d.t(195, yb + 42, typed, 34, 700, INK, "middle")
    return yb + 58


def waiting_rows(d, y, rows, x=20, width=350, lh=30):
    """rows: (rolle, navn, status, ferdig?)"""
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


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, "Prognose, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn, panelet Alle tall åpnet, samme skjerm på laptop, og forskjellen mellom Klassespill og Replay.")
    d.t(40, 46, "Uke 11. Sara har tastet 24, og tallet står allerede der det kommer fram.", 26, 600, INK)

    # Telefon
    phone(d, 40, 84, 1.0)
    game_header(d, 11, G.kostsum(11))
    m = phone_chart(d, G, 11, 24, hn=192)
    yb = order_input(d, m["axisbot"] + 14, 11, 24)
    d.t(20, yb + 26, "Kommer fram om lag Uke 15. Kan ikke endres", 13, 400, INK2)
    d.t(20, yb + 44, "etter at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 58, 350, 54, "Bekreft ordre på 24")
    d.t(20, yb + 136, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 136, a="end")
    d.end()
    d.t(235, 952, "Telefon, Klassespill: én graf med tre felt på samme tidsakse.", 14, 400, INK2, "middle")

    # Åpnet panel
    px = 460
    phone(d, px, 84, 1.0)
    d.t(20, 66, "Alle tall, Uke 11", 24, 700, INK)
    d.t(370, 62, "Lukk", 15, 600, BLUE, "end", 'text-decoration="underline"')
    rows = [("Lager", G.lager[10]), ("Restordre", G.rest[10]), ("Ordre inn", G.inn(11)), ("Levering", G.levering(11)),
            ("Sendt", G.sendt(11)), ("På vei", G.paavei(11)), ("Neste levering", G.order(8))]
    y = 104
    for lab, val in rows:
        d.t(20, y, lab, 15, 400, INK)
        d.t(370, y, val, 15, 600, INK, "end")
        d.line(20, y + 9, 370, y + 9, HAIR, 1)
        y += 32
    d.t(20, y, "Totalkostnad", 15, 400, INK)
    d.t(370, y, f"{nf(G.kostsum(11))} kr", 15, 600, INK, "end")
    d.line(20, y + 9, 370, y + 9, HAIR, 1)
    y += 26
    d.t(20, y, f"Denne Uka: {G.rest[10]} restordre × 1,00 = {nf(G.kostsum(11) - G.kostsum(10))} kr", 13, 400, INK2)
    y += 42
    d.t(20, y, "Regnestykket", 17, 600, INK)
    y += 28
    d.t(20, y, "Lager − Restordre + På vei", 14, 400, INK2)
    y += 24
    d.t(20, y, "Posisjon", 15, 400, INK)
    d.t(370, y, f"{G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}", 15, 600, INK, "end")
    y += 28
    d.t(20, y, "Med ordren på 24", 15, 400, INK)
    d.t(370, y, f"{G.posisjon(11)} + 24 = {G.posisjon(11) + 24}", 15, 600, INK, "end")
    y += 46
    d.t(20, y, "Ordrehistorikk", 17, 600, INK)
    y += 16
    ax = Axis(20, 350, 1, 11)
    u = 2.0
    base = y + 56
    for w in range(1, 12):
        v = G.order(w) if w < 11 else 24
        hh = v * u
        d.rect(ax.xc(w) - ax.slot / 2 + 2, base - hh, ax.slot - 4, hh, INK if w == 11 else ORD)
        d.t(ax.xc(w), base - hh - 4, v, 13, 700 if w == 11 else 400, INK, "middle")
    d.line(20, base, 370, base, HAIR2, 1)
    for w in (1, 5, 10, 11):
        d.t(ax.xc(w), base + 16, w, 13, 700 if w == 11 else 400, INK if w == 11 else INK3, "middle")
    d.t(20, base + 44, "Vis alt som tabell", 14, 600, BLUE, "start", 'text-decoration="underline"')
    d.demodata(20, 830)
    d.end()
    d.t(655, 952, "Ett trykk unna: alle tallene, og regnestykket uten fasit.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 84, 680, 448
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 104, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    d.t(lx + lw - 24, ly + 40, f"Totalkostnad {nf(G.kostsum(11))} kr", 14, 600, INK, "end")
    m2 = meteo(d, G, lx + 16, ly + 56, 440, 11, 24, left=30, hn=150, hf=56, gap=18, t_flow="", t_ord="", sendt=True)
    flow_title(d, lx + 16, m2["yflow"] - 7, G, 11)
    d.t(lx + 196, m2["yflow"] - 7, f"Sendt {G.sendt(11)} (mørk strek)", 13, 400, INK2)
    d.t(lx + 16, m2["yord"] - 7, "Din ordre", 13, 600, INK)
    cx = lx + 476
    y = ly + 74
    for lab, val in [("Lager", G.lager[10]), ("Restordre", G.rest[10]), ("Ordre inn", G.inn(11)), ("Levering", G.levering(11)),
                     ("Sendt", G.sendt(11)), ("På vei", f"{G.paavei(11)} + 24"), ("Neste levering", G.order(8))]:
        d.t(cx, y, lab, 14, 400, INK)
        d.t(lx + lw - 24, y, val, 14, 600, INK, "end")
        d.line(cx, y + 7, lx + lw - 24, y + 7, HAIR, 1)
        y += 27
    y += 14
    d.t(cx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, y + 10, lx + lw - 24 - cx, 48, PAPER, INK, 1.4, 6)
    d.t((cx + lx + lw - 24) / 2, y + 45, 24, 30, 700, INK, "middle")
    d.button(cx, y + 70, lx + lw - 24 - cx, 44, "Bekreft ordre på 24", size=15)
    d.t(cx, y + 136, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(lx + lw - 24, ly + lh - 14, a="end")

    # Hjelpegrad
    hy = 572
    d.t(lx, hy, "Hjelpegrad: samme Uke på to nivåer", 20, 600, INK)
    panel_w = 330
    hh = 180
    y0 = hy + 46
    ax1 = Axis(lx + 30, panel_w - 30, 1, 15)
    d.t(lx, hy + 30, "Klassespill: ankomster, ingen linje", 14, 600, INK)
    d.rect(ax1.xr(11), y0, ax1.xr(15) - ax1.xr(11), hh, TINT)
    Y = grid(d, ax1, y0, hh, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax1, y0, hh, G.net, 1, 11)
    d.circle(ax1.xc(11), Y(G.net(11)), 4, RED, PAPER, 2)
    d.line(ax1.xr(11), y0 - 4, ax1.xr(11), y0 + hh, INK, 1.4)
    d.t(ax1.xr(11) + 6, Y(G.net(11)) + 5, "Restordre 13", 13, 600, INK)
    xaxis(d, ax1, y0 + hh + 18, [1, 3, 5, 7, 9, 11, 13, 15], 11)

    bx = lx + panel_w + 20
    ax2 = Axis(bx + 30, panel_w - 30, 1, 15)
    d.t(bx, hy + 30, "Replay, etter Debriefen: projeksjonen åpnes", 14, 600, INK)
    d.rect(ax2.xr(11), y0, ax2.xr(15) - ax2.xr(11), hh, TINT)
    Y2 = grid(d, ax2, y0, hh, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax2, y0, hh, G.net, 1, 11)
    p24 = G.projection(11, 24)
    p0 = G.projection(11, 0)
    d.path("M" + " L".join(f"{ax2.xc(a):.1f} {Y2(v):.1f}" for a, v in p0), stroke=GREY, sw=1, dash="2 4")
    d.path("M" + " L".join(f"{ax2.xc(a):.1f} {Y2(v):.1f}" for a, v in p24), stroke=GREY, sw=2, dash="6 4")
    d.circle(ax2.xc(15), Y2(p24[-1][1]), 3.5, PAPER, GREY, 2)
    d.circle(ax2.xc(11), Y2(G.net(11)), 4, RED, PAPER, 2)
    d.line(ax2.xr(11), y0 - 4, ax2.xr(11), y0 + hh, INK, 1.4)
    d.t(ax2.xc(15) - 8, Y2(p24[-1][1]) - 10, f"Med 24: {sg(p24[-1][1])}", 13, 600, INK, "end")
    d.t(ax2.xc(15) + 6, Y2(p0[-1][1]) + 17, f"Med 0: {sg(p0[-1][1])}", 13, 400, INK2, "end")
    xaxis(d, ax2, y0 + hh + 18, [1, 3, 5, 7, 9, 11, 13, 15], 11)
    yn = y0 + hh + 46
    d.para(lx, yn, "I Klassespillet ser Sara når varene kommer, men må legge dem sammen selv. Det er denne summen folk flest lar være å regne, og Debriefen skal vise hva det koster.", panel_w - 6, 14, 19, fill=INK2)
    d.para(bx, yn, f"I Replay regner linja: {G.posisjon(11) + 24} i posisjon − 4 × {G.inn(11)} i ordre inn = {sg(p24[-1][1])}. Hvis ordre inn holder seg. Ikke garantert.", panel_w - 6, 14, 19, fill=INK2)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Prognose, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 188
    d.t(40, 50, "En Uke i Prognose: stolpene flytter seg, nå-streken flytter seg, og grafen husker hva du gjorde.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Levering og ordre inn er nye, og restordren er allerede oppdatert. Plassen fire uker fram står tom."),
        ("B  Beslutningen: 24", "Sara taster, og 24 står i Uke 15, etter 4, 4 og 8. 16 var allerede på vei. Ingen fasit ved siden av."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Nå-streken flytter seg én Uke. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle. Spørsmålet går videre til Debrief."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 94, h, 20, 600, INK)
        d.para(x, 120, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone(d, px(0), y0, s)
    game_header(d, 11, G.kostsum(11))
    m = phone_chart(d, G, 11, None)
    yb = order_input(d, m["axisbot"] + 14, 11, None)
    d.t(20, yb + 26, f"Sist Uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.button(20, yb + 58, 350, 54, "Bekreft ordre", primary=False)
    d.demodata(20, 830)
    d.end()

    # B
    phone(d, px(1), y0, s)
    game_header(d, 11, G.kostsum(11))
    m = phone_chart(d, G, 11, 24)
    yb = order_input(d, m["axisbot"] + 14, 11, 24)
    d.t(20, yb + 26, "Kommer fram om lag Uke 15. Kan ikke endres", 13, 400, INK2)
    d.t(20, yb + 44, "etter at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 58, 350, 54, "Bekreft ordre på 24")
    d.demodata(20, 830)
    d.end()

    # C
    phone(d, px(2), y0, s)
    game_header(d, 11, G.kostsum(11))
    m = phone_chart(d, G, 11, 24)
    y = m["axisbot"] + 14
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
    m = phone_chart(d, G, w, None)
    ax = m["ax"]
    # gammel nå-strek
    d.line(ax.xr(11), m["ynet"] - 2, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["axisbot"] + 14
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, f"Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 28, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    rr = [("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w))]
    yy = y + 58
    for lab, v in rr:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 24
    d.t(20, yy, "Restordre", 14, 400, INK)
    d.t(370, yy, f"{G.rest[w - 2]} blir {G.rest[w - 1]}", 14, 600, INK, "end")
    d.demodata(20, 830)
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    game_header(d, w, G.kostsum(w))
    m = phone_chart(d, G, w, G.order(w), hn=150)
    y = m["axisbot"] + 10
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller for Jonas", "bestiller", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 56, rows, lh=26)
    d.rect(20, yy - 8, 350, 84, TINT, None, 1, 6)
    d.t(32, yy + 16, "Slik ser Jonas det etter fraværet:", 13, 400, INK2)
    d.t(32, yy + 36, "KI-spiller bestiller for deg.", 14, 600, INK)
    d.button(240, yy + 22, 120, 42, "Ta tilbake setet", primary=False, size=13)
    d.demodata(20, 830)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 66, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 88, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 136, "Kjedens totalkostnad", 15, 400, INK2)
    d.t(20, 176, f"{nf(K['kjedekost'])} kr", 40, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    y = 216
    mx = max(K["kost_per_rolle"].values())
    for r in ROLES:
        v = K["kost_per_rolle"][r]
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        d.t(370, y, f"{nf(v)} kr", 14, 600, INK, "end")
        d.rect(20, y + 7, 350 * v / mx, 7, INK if r == "Grossist" else ORD)
        y += 46
    y += 16
    d.t(20, y, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(50, 324, 1, G.n)
    Y = grid(d, ax, y + 12, 130, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax, y + 12, 130, G.net, 1, G.n)
    xaxis(d, ax, y + 160, [1, 12, 24, 36], None)
    d.t(20, y + 198, "Hvorfor svingte det? Det finner dere ut i", 14, 400, INK2)
    d.t(20, y + 217, "Debriefen, med alle fire Rollene.", 14, 400, INK2)
    d.button(20, 750, 350, 54, "Gå til Debrief")
    d.demodata(20, 830)
    d.end()

    # Under: hva lærer spilleren
    yt = y0 + 844 * s + 54
    d.t(40, yt, "Hva spilleren lærer av å se grafen uke for uke", 24, 600, INK)
    tekst = [
        "Grafen er den samme hver Uke, med samme skala og samme tre felt. En stor Uke ser derfor stor ut, og ingenting skaleres vekk.",
        "Hver ordre står to ganger: som mørk stolpe nederst der den ble lagt, og som åpen stolpe fire Uker fram der den kommer. Sara lærer at det hen får nå, er det hen bestemte for fire Uker siden.",
        "Rødt i midtfeltet er ordre inn utover levering, og nøyaktig så mye faller netto lager den Uka. Summen er regnestykket, ikke bare mønsteret.",
        "I Klassespillet må hen selv legge sammen det som er på vei. Etter Debriefen vet hen hvorfor det er verdt å gjøre det, og i Replay er linja der.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 36, tx, colw, 16, 22, fill=INK)
    ys = yt + 150
    d.t(40, ys, "Ordren på 24 sett fra fem Uker: den rykker mot nå-streken, og i Uke 15 kommer det 17.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 24) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 24)
        typed = 24 if wk == 11 else G.order(wk)
        ax = Axis(xx, pw2, wk - 7, wk + 4)
        hh = 62
        y1 = ys + 14
        u = hh / 32
        d.rect(ax.xr(wk), y1, ax.xr(wk + 4) - ax.xr(wk), hh, TINT)
        flow_bars(d, ax, y1, hh, G, wk - 7, wk, 32, x1=ax.xr(wk + 4))
        bw = ax.slot - 3.5
        for week, qty in G.arrivals(wk, typed):
            is24 = week == 15
            d.rect(ax.xc(week) - bw / 2, y1 + hh - qty * u, bw, qty * u, PAPER, INK if is24 else BLUE, 1.6 if is24 else 1.1)
        if wk == 15:
            d.rect(ax.xc(15) - bw / 2, y1 + hh - 24 * u, bw, 24 * u, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
        d.line(ax.xr(wk), y1 - 4, ax.xr(wk), y1 + hh + 2, INK, 1.2)
        cap = {11: "Uke 11: 24 bestilt", 12: "Uke 12: tre Uker igjen", 13: "Uke 13: to Uker igjen", 14: "Uke 14: neste Uke",
               15: f"Uke 15: {G.levering(15)} kom, {G.overdue(15)} forsinket"}[wk]
        d.t(xx, y1 + hh + 18, cap, 14, 400, INK2)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Prognose, grafgrammatikken over tid",
            "Saras meteogram i Uke 5, 11, 18 og 29 på én felles tidsakse, med projeksjon mot det som faktisk skjedde, og sammenligning med simulert referanse etter Debriefen.")
    d.t(40, 56, "Samme meteogram i fire Uker av Saras spill", 36, 700, INK)
    d.para(40, 90, "Radene deler tidsakse og skala, så nå-streken vandrer mot høyre. Det åpne til høyre for streken blir historie i raden under, og da ser du hva som holdt.", 1400, 17, 23, fill=INK2)

    # Nøkkel: direkte etiketter øverst i høyre kolonne
    keyx = 1500
    d.t(keyx, 56, "Slik leses raden", 17, 600, INK)
    d.path(f"M{keyx} 76 L{keyx + 34} 76", stroke=GREY, sw=2, dash="6 4")
    d.t(keyx + 42, 81, "Projeksjon. Bare i Replay, aldri i Klassespillet.", 14, 400, INK2)
    d.line(keyx, 98, keyx + 34, 98, INK, 1)
    d.t(keyx + 42, 103, "Det som faktisk skjedde. Bare på dette arket.", 14, 400, INK2)
    d.rect(keyx + 10, 112, 14, 16, PAPER, BLUE, 1.2)
    d.t(keyx + 42, 125, "Bestilt, med plan om å komme denne Uka.", 14, 400, INK2)

    rows = [
        (5, G.order(5), [
            ("P2 Forsinkelse", "Alt er 4, og linja er flat. Bevegelsen som kommer i Uke 7, er ikke synlig fra Saras plass ennå."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte, ikke det kundene gjorde. Sara har ingen annen kilde."),
            ("Til neste ordre", "En rolig graf betyr bare at ingenting har nådd deg ennå."),
        ]),
        (11, 24, [
            ("P3 Det som er på vei", f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir den {G.posisjon(11) + 24}, og linja ender på {G.posisjon(11) + 24} − 4 × {G.inn(11)} = {sg(G.projection(11, 24)[-1][1])}."),
            ("P1 Lager er en opphopning", f"Rød del av stolpen er det netto lager faller: {G.inn(11)} inn minus {G.levering(11)} levert gir {sg(G.net(11) - G.net(10))} denne Uka."),
            ("Til neste ordre", f"Det ble {sg(G.net(15))}, ikke {sg(G.projection(11, 24)[-1][1])}: {G.levering(15)} av 24 kom i Uke 15, og ordre inn ble høyere. Linja er regning, ikke løfte."),
        ]),
        (18, G.order(18), [
            ("P3 og P2 igjen", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem er over fire Uker gamle. Båndet er like bredt som det du ikke kan tidfeste."),
            ("P7 Overreaksjon forsterker", "En ny ordre kommer ikke raskere enn de gamle. Den legger seg bakerst, og leverandøren får et større tall å svare på."),
            ("Til neste ordre", f"Restordre {G.rest[17]} er det du ser. Spør hva {G.paavei(18)} på vei gjør når de kommer."),
        ]),
        (29, G.order(29), [
            ("P8 Restordre koster dobbelt", f"Lager {G.lager[28]} × 0,50 = {nf(G.lager[28] * 0.5)} kr per Uke. Restordre {max(G.rest)} kostet {nf(max(G.rest) * 1.0)} kr per Uke. Begge teller."),
            ("P1 Samme regning, motsatt fortegn", "Blå stolper i Uke 23 til 26 er det som kom nesten samtidig. Toppen er summen av gamle ordrer."),
            ("Til neste ordre", "Linja viser hvor raskt overskuddet tæres. Hvor mye du vil ha igjen, må du bestemme selv."),
        ]),
    ]
    y = 146
    x0, wplot = 170, 1290
    hn, hf = 108, 40
    rh = 236
    for now, typed, notes in rows:
        m = meteo(d, G, x0, y, wplot, now, typed, wmin=1, wmax=36, hn=hn, hf=hf, gap=7, titles=False, left=34, xstep=4,
                  proj=True, actual=True, nowlabel="Nå", overduenote=True, connector=True, ordlabel=False, netlabel=False, overdue_out=True)
        ax = m["ax"]
        d.t(40, y + 26, f"Uke {now}", 26, 700, INK)
        lab = f"Lager {G.lager[now - 1]}" if G.net(now) >= 0 else f"Restordre {G.rest[now - 1]}"
        d.t(40, y + 48, lab, 15, 600, INK)
        d.t(40, y + 67, f"På vei {G.paavei(now)}", 15, 400, INK2)
        d.t(40, y + 86, f"Posisjon {sg(G.posisjon(now))}", 15, 400, INK2)
        d.t(40, m["yflow"] + hf - 4, "Inn og ut, P1", 13, 400, INK2)
        d.t(40, m["yord"] + m["ho"] - 2, "Egen ordre, P2 P3", 13, 400, INK2)
        # projeksjonens endepunkt mot fasit
        p = G.projection(now, typed)[-1][1]
        over = G.overdue(now)
        ex = ax.xr(now + 4) + 8
        Y = m["Y"]
        if now == 18:
            d.t(ex, Y(p + over) + 5, f"Planlagt {sg(p)} til {sg(p + over)}", 14, 600, INK2)
            d.t(ex, Y(G.net(now + 4)) + 2, f"Det ble {sg(G.net(now + 4))}", 14, 600, INK)
        else:
            act = G.net(now + 4)
            if abs(Y(p) - Y(act)) < 18:
                d.t(ex, Y(p) - 2, f"Planlagt {sg(p)}", 14, 600, INK2)
                d.t(ex, Y(p) + 15, f"Det ble {sg(act)}", 14, 600, INK)
            else:
                d.t(ex, Y(p) + 5, f"Planlagt {sg(p)}", 14, 600, INK2)
                d.t(ex, Y(act) + 5, f"Det ble {sg(act)}", 14, 600, INK)
        # notater
        ny = y + 16
        for head, body in notes:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 19, body, 460, 14, 18, fill=INK2) + 4
        d.line(40, y + rh - 8, 1960, y + rh - 8, HAIR, 1)
        y += rh

    # Etter Debriefen
    y += 8
    d.t(40, y + 22, "Etter Debriefen: samme graf, med simulert referanse", 24, 600, INK)
    d.t(40, y + 46, "Samme kjede, samme kunder. Tallene viser en sammenheng, de er ingen fasit. Simulert.", 15, 400, INK2)
    gy = y + 62
    gh = 158
    ax = Axis(80, 900, 1, 36)
    Y = grid(d, ax, gy, gh, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax, gy, gh, G.net, 1, 36)
    for S, col, sw in ((BARE, INK, 1.6), (ALLE, GREY, 1.6)):
        d.path("M" + " L".join(f"{ax.xc(w):.1f} {Y(S.net(w)):.1f}" for w in range(1, 37)), stroke=col, sw=sw)
    d.t(ax.xc(16), Y(-36), f"Spill 17, lavest {sg(min(G.net_))}", 14, 600, RED, "end")
    d.t(ax.xc(33) + 2, Y(BARE.net(33)) - 8, "Bare Sara teller på vei", 14, 600, INK, "end")
    d.t(ax.xc(27) + 6, Y(ALLE.net(27)) + 16, "Alle fire teller på vei", 14, 600, GREY)
    xaxis(d, ax, gy + gh + 17, [1, 5, 10, 15, 20, 25, 30, 36], None)

    tx = 1010
    cols = [tx + 170, tx + 280, tx + 400]
    d.t(cols[0], gy + 10, "Spill 17", 14, 600, INK, "end")
    d.t(cols[1], gy + 10, "Bare Sara", 14, 600, INK, "end")
    d.t(cols[2], gy + 10, "Alle fire", 14, 600, INK, "end")
    d.line(tx, gy + 18, cols[2], gy + 18, HAIR2, 1)
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    rr = [("Kjeden, kr", nf(K["kjedekost"], 0), nf(B["kjedekost"], 0), nf(A["kjedekost"], 0)),
          ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"], 2), nf(B["kost_per_rolle"]["Grossist"], 2), nf(A["kost_per_rolle"]["Grossist"], 2)),
          ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]), fx1(A["forsterkning"]["Grossist"])),
          ("Forsterkning, Fabrikk", fx1(K["forsterkning"]["Fabrikk"]), fx1(B["forsterkning"]["Fabrikk"]), fx1(A["forsterkning"]["Fabrikk"]))]
    yy = gy + 40
    for row in rr:
        d.t(tx, yy, row[0], 14, 400, INK)
        for c, v in zip(cols, row[1:]):
            d.t(c, yy, v, 14, 400, INK, "end")
        d.line(tx, yy + 8, cols[2], yy + 8, HAIR, 1)
        yy += 27
    d.para(tx, yy + 8, "P5 og P6: forsterkningen faller også for de andre Rollene når ett ledd teller det som er på vei. Formen består, for strukturen er den samme.", 400, 13, 17, fill=INK2)

    # Hjelpegrad og P7
    d.t(keyx, y + 22, "Hjelpegrad", 20, 600, INK)
    ny = d.para(keyx, y + 48, "Klassespill: tre felt og kjente ankomster, ingen linje. Posisjonen ligger ett trykk unna som regnestykke.", 460, 15, 20, fill=INK)
    ny = d.para(keyx, ny + 6, "Replay: den stiplede linja åpnes, med båndet. Studenten har da selv kjent på hva den gjør synlig.", 460, 15, 20, fill=INK)
    ny = d.para(keyx, ny + 12, "P7: Å telle det som er på vei er ikke nok alene. I simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17.", 460, 14, 18, fill=INK2)
    d.demodata(1960, 1388, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
