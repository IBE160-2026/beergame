"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e03kost import *

G = Seat()
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
K = FX["spill17"]
PN = 'style="font-variant-numeric:lining-nums proportional-nums"'


def game_head(d, wk, x=20, role="Grossist", spill="Spill 17"):
    d.t(x, 64, f"Uke {wk}", 30, 700, INK)
    d.t(x + text_w(f"Uke {wk}", 30) + 10, 64, f"{role}, {spill}", 14, 400, INK2)


def order_input(d, y, wk, typed, link="Regnskapet"):
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, f"Din ordre for Uke {wk}", 15, 600, INK)
    if link:
        d.t(370, y + 28, link, 14, 600, BLUE, "end", 'text-decoration="underline"')
    yb = y + 42
    d.rect(20, yb, 350, 56, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(78, yb, 78, yb + 56, HAIR2, 1)
    d.line(312, yb, 312, yb + 56, HAIR2, 1)
    d.line(40, yb + 28, 58, yb + 28, INK, 2)
    d.line(332, yb + 28, 350, yb + 28, INK, 2)
    d.line(341, yb + 19, 341, yb + 37, INK, 2)
    if typed is None:
        d.t(195, yb + 35, "Antall enheter", 18, 400, INK3, "middle")
    else:
        d.t(195, yb + 40, typed, 34, 700, INK, "middle")
    return yb + 56


def waiting_rows(d, y, rows, x=20, width=350, lh=30):
    """rows: (rolle, navn, status, ferdig?)"""
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


def phone_game(d, g, wk, typed, hn=124, ho=42, chain=True, proj=False):
    """Telefonen i Klassespillet: regnskapslinja først, så kjedebåndet, så meteogrammet med V-en på siden."""
    game_head(d, wk)
    y = ledger(d, 20, 100, 350, g, wk, ls=13, big=26)
    y += 14
    if chain:
        d.line(20, y, 370, y, HAIR, 1)
        y = chain_seat(d, 20, y + 10, 350, g, wk, typed) + 16
    m = meteo3(d, g, 16, y, 358, wk, typed, hk=0, hn=hn, ho=ho, gap=14, left=30, sidev=54, ls=13, proj=proj,
               t_net="Lager og restordre", t_ord="Din ordre, og når den kommer")
    return m


def regnskap_rows(g):
    return [
        ("Lager", lambda k: g.lager[k - 1], "n"),
        ("Restordre", lambda k: g.rest[k - 1], "n"),
        (None, None, None),
        ("Lagerkostnad", g.lk, "lk"),
        ("Restordrekostnad", g.rk, "rk"),
        ("Uka kostet", g.wc, "wc"),
        ("Totalkostnad", g.kostsum, "cum"),
    ]


def flow_rows(g, typed_now=None, now=None):
    return [
        ("Ordre inn", g.inn, "n"),
        ("Levering", g.levering, "n"),
        ("Sendt", g.sendt, "n"),
        ("Din ordre", lambda k: (typed_now if k == now and typed_now is not None else g.order(k)), "n"),
        ("På vei", g.paavei, "n"),
    ]


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, "Kostnadsregnskapet, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn. Skjermen åpner med hva uka og spillet har kostet, så kjedebåndet og meteogrammet med V-en på siden. Ved siden av: Regnskapet åpnet som matrise, samme skjerm på laptop, og forskjellen mellom Klassespill og Replay.")
    d.t(40, 46, f"Uke 11 kostet {nf(G.wc(11))} kr. Kjeden og grafen under viser hvorfor.", 26, 600, INK)

    # Telefon
    phone(d, 40, 84, 1.0)
    m = phone_game(d, G, 11, 24)
    yb = order_input(d, m["axisbot"] + 12, 11, 24)
    d.t(20, yb + 22, "Kommer fram om lag Uke 15. Kan ikke endres etter", 13, 400, INK2)
    d.t(20, yb + 39, "at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 52, 350, 50, "Bekreft ordre på 24")
    d.t(20, yb + 126, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 126, a="end")
    d.end()
    d.t(235, 952, "Telefon, Klassespill: kostnaden først, så kjeden og grafen som forklarer den.", 14, 400, INK2, "middle")

    # Åpnet panel: Regnskapet
    px = 460
    phone(d, px, 84, 1.0)
    d.t(20, 64, "Regnskapet", 26, 700, INK)
    d.t(370, 60, "Lukk", 15, 600, BLUE, "end", 'text-decoration="underline"')
    d.t(20, 88, "Grossist, Spill 17, Uke 6 til 11", 14, 400, INK2)
    ax = Axis(150, 220, 6, 11)
    # kostnad per uke som stolper, samme kolonner som tabellen
    yk, hk = 124, 70
    d.t(20, 116, "Kostnad per uke, kr", 13, 600, INK)
    for v in (0, 10, 20):
        yy = yk + hk - v * hk / 25
        d.line(ax.x0, yy, ax.x1, yy, HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 6, yy + 4, v, 13, 400, INK3, "end")
    cost_bars(d, ax, yk, hk, G, 6, 11, kmax=25)
    for k in range(6, 12):
        c = G.wc(k)
        d.t(ax.xc(k), yk + hk - c * hk / 25 - 5, nf(c, 2) if c != int(c) else str(int(c)), 13, 600 if k == 11 else 400, INK, "middle")
    y = matrix(d, ax, yk + hk + 10, regnskap_rows(G), list(range(6, 12)), 20, rh=27, ls=13, src="05-regnskap", now=11)
    y = matrix(d, ax, y + 12, flow_rows(G, 24, 11), list(range(6, 12)), 20, rh=27, ls=13, src="05-regnskap", head=False, now=11)
    y += 30
    d.t(20, y, "Regnestykket for Uke 11", 16, 600, INK)
    y += 24
    d.t(20, y, f"{G.lager[10]} på lager × 0,50 + {G.rest[10]} restordre × 1,00 = {nf(G.wc(11))} kr", 14, 400, INK)
    y += 22
    d.t(20, y, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir den {G.posisjon(11) + 24}.", 14, 400, INK)
    y += 22
    d.t(20, y, "Regnestykket, ikke et råd. Tidligere uker: sveip.", 13, 400, INK2)
    d.demodata(20, 826)
    d.end()
    d.t(655, 952, "Ett trykk unna: graf over tabell, kolonne for kolonne.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 84, 680, 652
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 104, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    ledger(d, lx + 300, ly + 22, 356, G, 11, ls=13, big=22)
    d.line(lx + 24, ly + 98, lx + lw - 24, ly + 98, HAIR, 1)
    chain_seat(d, lx + 24, ly + 106, 400, G, 11, 24)
    cx = lx + 456
    d.t(cx, ly + 128, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, ly + 138, lx + lw - 24 - cx, 44, PAPER, INK, 1.4, 6)
    d.t((cx + lx + lw - 24) / 2, ly + 170, 24, 28, 700, INK, "middle")
    d.button(cx, ly + 192, lx + lw - 24 - cx, 40, "Bekreft ordre på 24", size=15)
    d.t(cx, ly + 254, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.line(lx + 24, ly + 272, lx + lw - 24, ly + 272, HAIR, 1)
    m2 = meteo3(d, G, lx + 24, ly + 284, lw - 48, 11, 24, wmin=4, hk=48, hn=104, ho=36, gap=12, left=112, sidev=44, ls=12,
                kmax=20, kticks=(0, 10, 20), xstep=2, t_net="Lager og restordre", t_ord="Din ordre")
    ax2 = m2["ax"]
    rows = [("Lagerkostnad", G.lk, "lk"), ("Restordrekostnad", G.rk, "rk"), ("Totalkostnad", G.kostsum, "cum")]
    matrix(d, ax2, m2["axisbot"] + 8, rows, list(range(4, 12)), lx + 24, rh=22, ls=12, src="05-laptop", head=False, now=11, dec=2)
    d.demodata(lx + lw - 24, ly + lh - 12, a="end")

    # Hjelpegrad
    hy = 772
    d.t(lx, hy, "Hjelpegrad: samme Uke på to nivåer", 20, 600, INK)
    pw = 330
    for i, (title, proj) in enumerate((("Klassespill: det som har kostet", False), ("Replay, etter Debriefen: det som kan koste", True))):
        bx = lx + i * (pw + 20)
        d.t(bx, hy + 30, title, 14, 600, INK)
        mm = meteo3(d, G, bx, hy + 48, pw, 11, 24, wmin=1, hk=34, hn=56, ho=0, gap=8, left=28, sidev=0, ls=12, kmax=25,
                    kticks=(0, 20), proj=proj, titles=False, xstep=2, ticks=(-40, 0, 20), netlabel=False, cost_label=False)
        if proj:
            tot = sum(wcost(v) for _, v in G.projection(11, 24)[1:])
            p = G.projection(11, 24)[-1][1]
            d.t(mm["fx0"] - 4, mm["yk"] + 8, f"Neste fire uker: om lag {nf(tot, 0)} kr", 12, 600, INK, "end")
            d.t(mm["ax"].xc(15), mm["Y"](p) + 18, sg(p), 12, 600, INK, "middle")
    yn = hy + 198
    d.para(lx, yn, "Klassespill: bare det som allerede har kostet. Hva de neste ukene koster, må Sara tenke ut selv fra På vei.", pw - 6, 13, 18, fill=INK2)
    tot = sum(wcost(v) for _, v in G.projection(11, 24)[1:])
    d.para(lx + pw + 20, yn, f"Replay: med ordre inn på {G.inn(11)} og kjente ankomster koster de fire neste ukene om lag {nf(tot, 0)} kr. Ikke garantert.", pw - 6, 13, 18, fill=INK2)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Kostnadsregnskapet, en Uke i spillet",
            "Seks telefonruter: Uka åpner med hva den kostet, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter med kjedens totalkostnad. Under: ordren på 24 sett fra fem uker i kjedebåndet, med ukas kostnad.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 190
    d.t(40, 50, "En Uke i Kostnadsregnskapet: regningen kommer først, og kjeden og grafen forklarer den.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", f"Først regningen: Uke 11 kostet {nf(G.wc(11))} kr, alt i restordre. Under står kjeden og grafen som forklarer hvorfor."),
        ("B  Beslutningen: 24", f"{G.paavei(11)} er allerede på vei. Sara taster 24, og tallet havner bakerst i røret og fire uker fram i grafen. Ingen fasit."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", f"Uke 12 regnes: restordren vokser til {G.rest[11]}, og uka koster {nf(G.wc(12))} kr. Under 2 sekunder, kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle og per kostnadsart. Hvorfor, tar gruppa i Debriefen."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 94, h, 20, 600, INK)
        d.para(x, 120, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone(d, px(0), y0, s)
    m = phone_game(d, G, 11, None)
    yb = order_input(d, m["axisbot"] + 12, 11, None)
    d.t(20, yb + 22, f"Sist Uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.button(20, yb + 40, 350, 50, "Bekreft ordre", primary=False)
    d.demodata(20, 826)
    d.end()

    # B
    phone(d, px(1), y0, s)
    m = phone_game(d, G, 11, 24)
    yb = order_input(d, m["axisbot"] + 12, 11, 24)
    d.t(20, yb + 22, "Kommer fram om lag Uke 15. Kan ikke endres etter", 13, 400, INK2)
    d.t(20, yb + 39, "at du har bekreftet.", 13, 400, INK2)
    d.button(20, yb + 52, 350, 50, "Bekreft ordre på 24")
    d.demodata(20, 826)
    d.end()

    # C
    phone(d, px(2), y0, s)
    m = phone_game(d, G, 11, 24)
    y = m["axisbot"] + 12
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 60, seat_sara_klar(), lh=28)
    d.t(20, y + 184, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 826)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    m = phone_game(d, G, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["yn"] - 2, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["axisbot"] + 12
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 28, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    rr = [("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w)), ("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}"),
          ("Uka kostet", f"{nf(G.wc(w))} kr")]
    yy = y + 56
    for lab, v in rr:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 23
    d.demodata(20, 826)
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    m = phone_game(d, G, w, G.order(w), hn=104)
    y = m["axisbot"] + 8
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 24, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller", "bestiller for Jonas", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 52, rows, lh=25)
    d.rect(20, yy - 8, 350, 70, TINT, None, 1, 6)
    d.t(32, yy + 14, "Slik ser Jonas det etter fraværet:", 13, 400, INK2)
    d.t(32, yy + 34, "KI-spiller bestiller for deg.", 14, 600, INK)
    d.button(236, yy + 8, 124, 40, "Ta tilbake setet", primary=False, size=13)
    d.demodata(20, 826)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 64, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 88, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 132, "Kjedens totalkostnad", 15, 400, INK2)
    d.t(20, 172, f"{nf(K['kjedekost'])} kr", 40, 700, INK, extra=PN)
    seats = {r: Seat(r) for r in ROLES}
    tlk = sum(seats[r].cum_lk(36) for r in ROLES)
    trk = sum(seats[r].cum_rk(36) for r in ROLES)
    assert abs(tlk + trk - K["kjedekost"]) < 1e-9
    cost_split_bar(d, 20, 190, 350, tlk, trk, h=10, ls=13, labels=False)
    d.t(20, 220, f"Lagerkostnad {nf(tlk)}", 13, 400, INK2)
    d.t(370, 220, f"Restordrekostnad {nf(trk)}", 13, 400, INK2, "end")
    y = 262
    d.t(20, y, "Per Rolle, samme skala", 14, 600, INK)
    y += 26
    sc = 260 / 700
    for r in ["Detaljist", "Grossist", "Distributør", "Fabrikk"]:
        S = seats[r]
        lk, rk = S.cum_lk(36), S.cum_rk(36)
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        d.t(370, y, f"{nf(lk + rk)} kr", 14, 600, INK, "end")
        d.rect(20, y + 8, lk * sc, 8, BLUE)
        d.rect(20 + lk * sc + 1, y + 8, rk * sc, 8, RED)
        y += 44
    y += 4
    d.para(20, y, f"Blått er lagerkostnad, rødt er restordrekostnad. Restordre koster dobbelt, og de {nf(trk, 0)} kronene i rødt er {round(trk / (tlk + trk) * 100)} % av regningen.", 350, 14, 19, fill=INK2)
    d.para(20, y + 82, "Målet var lavest kostnad for hele kjeden. Hvorfor den ble slik, finner dere ut sammen.", 350, 14, 19, fill=INK)
    d.button(20, 740, 350, 52, "Gå til Debrief")
    d.demodata(20, 826)
    d.end()

    # Under: hva lærer spilleren
    yt = y0 + 844 * s + 42
    d.t(40, yt, "Hva spilleren lærer av å se regningen, kjeden og grafen uke for uke", 24, 600, INK)
    tekst = [
        "Regningen kommer først, men den er en følge, ikke en beslutning. Uka koster det lageret og restordren står på nå, og de står der fordi ordre ble lagt for flere uker siden.",
        "V-en på siden av grafen deler høyde med lageret. En enhet under null gir dobbelt så lang strek som en enhet over. Sara ser hva restordre koster uten å regne (P8).",
        "Kjedebåndet viser at varene ligger i et rør. Ordren på 24 legger seg bakerst og rykker fram uke for uke. Mens den reiser, fortsetter regningen å løpe (P2, P3).",
        "Regnskapet bak ett trykk gir de samme tallene som tabell. Grafen og tallene stemmer for hver uke, så studenten kan sjekke regnestykket, ikke bare mønsteret (P1).",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 36, tx, colw, 16, 22, fill=INK)
    ys = yt + 126
    d.t(40, ys, f"Ordren på 24 sett fra fem uker: den rykker fram i røret, og i Uke 15 kommer {G.levering(15)}. Imens løper regningen.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 30) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 30)
        typed = 24 if wk == 11 else G.order(wk)
        if wk < 15:
            chain_seat(d, xx, ys + 4, pw2, G, wk, typed, ls=13, mark_week=15, show_cost=False)
        else:
            chain_seat(d, xx, ys + 4, pw2, G, wk, typed, ls=13, show_cost=False)
        cap = {11: "Uke 11: 24 bestilt", 12: "Uke 12", 13: "Uke 13", 14: "Uke 14: neste uke",
               15: f"Uke 15: {G.levering(15)} kom, {G.overdue(15)} forsinket"}[wk]
        d.t(xx, ys + 132, cap, 14, 600, INK)
        d.t(xx + pw2, ys + 132, f"Uka kostet {nf(G.wc(wk))} kr", 14, 400, INK2, "end")
    d.save()


# ---------- 10 ----------
def compact_kr(v):
    """Matrisetall på pedagogikkarket: hele kroner uten øre, ellers én desimal (alle beløp er hele eller halve)."""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.1f}".replace(".", ",")


def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Kostnadsregnskapet, grafgrammatikken over tid",
            "Saras regnskap, kjedebånd og meteogram i Uke 5, 11, 18 og 29 på én felles tidsakse, med V-en på siden, kostnad per uke som matrise, "
            "og etter Debriefen: totalkostnad mot simulert referanse og kostnad på snittet.")
    d.t(40, 56, "Saras regnskap i fire uker, og grafene som forklarer det", 36, 700, INK)
    d.para(40, 90, "Hver rad åpner med hva uka og spillet har kostet. Kjedebåndet viser hvor varene var, grafen viser hvordan det ble slik, "
                   "og V-en til høyre gjør lager og restordre om til kroner. Radene deler tidsakse og skala.", 1420, 17, 23, fill=INK2)

    keyx = 1510
    d.t(keyx, 56, "Slik leses raden", 17, 600, INK)
    d.rect(keyx, 70, 12, 12, "none", INK, 1)
    d.t(keyx + 20, 81, "Det de neste fire ukene faktisk kostet. Bare på dette arket.", 14, 400, INK2)
    d.rect(keyx, 92, 12, 12, "none", GREY, 1.2, extra='stroke-dasharray="3 2"')
    d.t(keyx + 20, 103, "Regnet kostnad, hvis ordre inn holder seg. Bare i Replay.", 14, 400, INK2)
    d.circle(keyx + 6, 120, 2.6, INK3)
    d.t(keyx + 20, 125, "Tidligere uker på V-en.", 14, 400, INK2)
    d.para(keyx, 147, "Øverst kostnad per uke i kr, i midten lager og restordre, nederst egen ordre.", 450, 14, 18, fill=INK2)

    rows = [
        (5, G.order(5), [
            ("P8 Lager koster også", f"{G.lager[4]} på lager × 0,50 = {nf(G.wc(5))} kr i uka. Alt så langt er lagerkostnad: {nf(G.kostsum(5))} kr."),
            ("P2 og P4", "Ordre inn er det Ida bestilte, ikke det kundene gjorde. Det som har skjedd hos dem, har ikke nådd røret ditt ennå."),
            ("Til neste ordre", "En rolig regning betyr bare at ingenting har nådd deg ennå."),
        ]),
        (11, 24, [
            ("P8 Restordre koster dobbelt", f"{G.rest[10]} i restordre koster {nf(G.wc(11))} kr i uka, like mye som 26 på lager. Streken på V-en er dobbelt så lang per enhet."),
            ("P3 Det som er på vei", f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir den {G.posisjon(11) + 24}. Ingen av de 24 når regningen før Uke 15."),
            ("Til neste ordre", f"Regnet for fire uker: {nf(sum(wcost(v) for _, v in G.projection(11, 24)[1:]), 0)} kr. Det ble {nf(sum(G.wc(k) for k in range(12, 16)), 0)} kr: {G.levering(15)} av 24 kom, og ordre inn steg."),
        ]),
        (18, G.order(18), [
            ("P2 og P3 igjen", f"{G.paavei(18)} på vei, {G.overdue(18)} av dem over fire uker gamle. Restordre {G.rest[17]} koster {nf(G.wc(18))} kr i uka, og regningen er {nf(G.kostsum(18))} kr."),
            ("P7 Overreaksjon forsterker", "En ny stor ordre kommer ikke raskere enn de gamle. Når alt kommer, blir restordre til lager, og regningen bytter farge, men stopper ikke."),
            ("Til neste ordre", f"Spør hva {G.paavei(18)} på vei vil koste når de kommer."),
        ]),
        (29, G.order(29), [
            ("P1 Lager er en opphopning", f"Lager {G.lager[28]} er summen av inn minus ut, uke for uke, etter at alt på vei kom fram. {G.lager[28]} × 0,50 = {nf(G.wc(29))} kr i uka."),
            ("P8 Begge armer koster", f"Lager i Uke 25 til 36 kostet {nf(G.kostsum(36) - G.kostsum(24))} kr. Restordre i Uke 9 til 24 kostet {nf(sum(G.wc(k) for k in range(9, 25)))} kr."),
            ("Til neste ordre", "Lager koster halvparten, men det koster hver uke det blir liggende."),
        ]),
    ]
    y = 176
    x0, wplot = 330, 1150
    rh = 194
    for now, typed, notes in rows:
        # venstre: regnskap og kjedebånd
        d.t(40, y + 22, f"Uke {now}", 26, 700, INK)
        d.t(40, y + 46, f"Uka kostet {nf(G.wc(now))} kr", 15, 600, INK)
        d.t(40, y + 66, f"Totalt {nf(G.kostsum(now))} kr", 15, 400, INK2)
        cost_split_bar(d, 160, y + 56, 120, G.cum_lk(now), G.cum_rk(now), h=8, labels=False)
        chain_seat(d, 40, y + 74, 260, G, now, typed, ls=12, show_cost=False)
        m = meteo3(d, G, x0, y + 6, wplot, now, typed, wmin=1, wmax=36, hk=36, hn=70, ho=24, gap=6, ls=12, left=34, sidev=58,
                   proj=True, actual=True, titles=False, xstep=4, kmax=40, kticks=(0, 20, 40), ticks=(-40, 0, 20), trail=True,
                   netlabel=False, ordlabel=False, arrnums=False, cost_label=True, overduenote=False)
        ny = y + 14
        for head, body in notes:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 19, body, 450, 14, 18, fill=INK2) + 4
        d.line(40, y + rh - 6, 1960, y + rh - 6, HAIR, 1)
        y += rh
    ax = m["ax"]

    # Matrisen: kostnad per uke, samme kolonner som grafene
    y += 4
    d.t(40, y + 14, "Saras regnskap som tall", 17, 600, INK)
    d.t(40, y + 34, "kr, uten øre der beløpet er helt.", 13, 400, INK2)
    d.t(40, y + 52, "Hver celle er regnet fra loggen.", 13, 400, INK2)
    yy = y
    for k in range(1, 37):
        bold = k in (5, 11, 18, 29)
        d.t(ax.xc(k), yy + 12, k, 11, 700 if bold else 400, INK if bold else INK3, "middle")
    yy += 18
    rows_m = [("Lagerkostnad", G.lk, "lk"), ("Restordrekostnad", G.rk, "rk"), ("Totalkostnad", G.kostsum, "cum")]
    cw = ax.slot - 2
    for lab, fn, kind in rows_m:
        d.t(x0 - 110, yy + 15, lab, 12, 600 if kind == "cum" else 400, INK)
        for k in range(1, 37):
            v = fn(k)
            DRAWN.append(("10-matrise", "Grossist", k, lab, v))
            if kind in ("lk", "rk"):
                fill, tc = cost_fill(kind, v)
                if fill != PAPER:
                    d.rect(ax.xc(k) - cw / 2, yy + 1, cw, 20, fill)
            else:
                tc = INK
            d.t(ax.xc(k), yy + 15, compact_kr(v), 11, 600 if kind == "cum" else 400, tc, "middle")
        d.line(x0 - 110, yy + 22, ax.xr(36), yy + 22, HAIR, 1)
        yy += 22
    for k in (5, 11, 18, 29):
        d.rect(ax.xl(k) + 0.5, y + 18, ax.slot - 1, yy - y - 18, "none", INK, 1.2)
    d.t(keyx, y + 14, "Hjelpegrad", 17, 600, INK)
    ny = d.para(keyx, y + 36, "Klassespill: regnskapet, kjedebåndet, grafen og V-en med det som har skjedd. Posisjon ligger ett trykk unna som regnestykke.", 450, 14, 18)
    d.para(keyx, ny + 2, "Replay: de stiplede kostnadsstolpene for de fire neste ukene åpnes, og sammenligningen under.", 450, 14, 18)

    # Etter Debriefen
    y = yy + 34
    d.line(40, y - 14, 1960, y - 14, HAIR2, 1)
    d.t(40, y + 14, "Etter Debriefen: samme regnskap mot simulert referanse", 24, 600, INK)
    d.t(40, y + 38, "Samme kjede, samme kunder. Tallene viser en sammenheng, ingen fasit. Simulert.", 15, 400, INK2)
    gy, gh = y + 78, 190
    axc = Axis(80, 640, 1, 36)
    Yc = yscale(gy, gh, 0, 600)
    for v in (0, 200, 400, 600):
        d.line(axc.x0, Yc(v), axc.x1, Yc(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(axc.x0 - 6, Yc(v) + 4, v, 12, 400, INK3, "end")
    # Spill 17: stablet akkumulert, lager nederst, restordre over
    lo_pts = [(axc.xc(k), Yc(G.cum_lk(k))) for k in range(1, 37)]
    hi_pts = [(axc.xc(k), Yc(G.kostsum(k))) for k in range(1, 37)]
    base = f"L{axc.xc(36):.1f} {Yc(0):.1f} L{axc.xc(1):.1f} {Yc(0):.1f} Z"
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in lo_pts) + " " + base, BLUEF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in hi_pts) + " L" + " L".join(f"{a:.1f} {b:.1f}" for a, b in reversed(lo_pts)) + " Z", REDF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in hi_pts), stroke=INK, sw=2)
    for S, col, dash in ((BARE, INK, "6 4"), (ALLE, GREY, None)):
        d.path("M" + " L".join(f"{axc.xc(k):.1f} {Yc(S.kostsum(k)):.1f}" for k in range(1, 37)), stroke=col, sw=1.6, dash=dash)
    ex = axc.xc(36) + 8
    d.t(ex, Yc(G.kostsum(36)) + 4, f"Spill 17: {nf(G.kostsum(36))} kr", 13, 700, INK)
    d.t(ex, Yc(BARE.kostsum(36)) + 4, f"Bare Sara teller på vei: {nf(BARE.kostsum(36))} kr", 13, 600, INK)
    d.t(ex, Yc(ALLE.kostsum(36)) + 4, f"Alle fire teller: {nf(ALLE.kostsum(36))} kr", 13, 600, GREY)
    d.t(axc.xc(21), Yc(G.cum_lk(21) + 80), f"Restordrekostnad {nf(G.cum_rk(36))}", 13, 600, INK, "middle")
    d.t(axc.xc(31), Yc(G.cum_lk(31) / 2) + 4, f"Lagerkostnad {nf(G.cum_lk(36))}", 13, 600, INK, "middle")
    xaxis(d, axc, gy + gh + 17, [1, 6, 12, 18, 24, 30, 36], None, 12)
    d.t(40, gy - 8, "Grossistens totalkostnad, kr", 13, 600, INK)

    # Kostnad på snittet
    vx = 1060
    avg, steady, paid = avg_cost(G)
    d.t(vx, gy - 8, "Kostnad på snittet mot det du betalte", 13, 600, INK)
    Yv = yscale(gy, gh, -40, 30)
    d.line(vx, Yv(0), vx + 120, Yv(0), HAIR2, 1)
    side_v(d, vx + 10, 110, Yv, -40, 30, None, 40, 12, trail=G.net_, head=False)
    d.t(vx + 10 + 15 * 110 / 40 + 4, Yv(30) + 10, "Lager, 0,50", 12, 400, INK2)
    d.t(vx + 10 + 110 - 4, Yv(-40) + 4, "Restordre, 1,00", 12, 400, INK2, "end")
    sxa = vx + 10 + wcost(avg) * 110 / 40
    d.line(vx + 10, Yv(avg), sxa, Yv(avg), INK, 2.4)
    d.circle(sxa, Yv(avg), 4, PAPER, INK, 2)
    d.t(vx + 130, Yv(avg) + 4, f"Snitt {nf(avg, 1)}", 13, 600, INK)
    ty = gy + 16
    tx = vx + 210
    d.para(tx, ty, f"Netto lager var i snitt {nf(avg, 1)} enheter. Jevn drift der ville kostet {nf(wcost(avg))} kr per uke, {nf(steady)} kr på 36 uker.", 220, 14, 19)
    d.para(tx, ty + 86, f"Du betalte {nf(paid)} kr. Uker på hver side av null veier ikke hverandre opp. Et regnestykke, ikke et oppnåelig mål.", 220, 14, 19, fill=INK2)

    # Tabell
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    tx2 = 1510
    cols = [tx2 + 250, tx2 + 345, tx2 + 450]
    yy = gy - 8
    for c, h in zip(cols, ("Spill 17", "Bare Sara", "Alle fire")):
        d.t(c, yy, h, 13, 600, INK, "end")
    d.line(tx2, yy + 7, cols[2], yy + 7, HAIR2, 1)
    rr = [("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"]), nf(A["kjedekost"])),
          ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"]), nf(A["kost_per_rolle"]["Grossist"])),
          ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]), fx1(A["forsterkning"]["Grossist"])),
          ("Forsterkning, Fabrikk", fx1(K["forsterkning"]["Fabrikk"]), fx1(B["forsterkning"]["Fabrikk"]), fx1(A["forsterkning"]["Fabrikk"]))]
    yy += 26
    for row in rr:
        d.t(tx2, yy, row[0], 13, 400, INK)
        for c, v in zip(cols, row[1:]):
            d.t(c, yy, v, 13, 400, INK, "end")
        d.line(tx2, yy + 7, cols[2], yy + 7, HAIR, 1)
        yy += 23
    d.para(tx2, yy + 8, "P7: å telle det som er på vei er ikke nok alene. En regel som jaget siste ordre for hardt, ga Fabrikk høyere forsterkning (12×) enn spill 17.", 450, 13, 17, fill=INK2)
    d.demodata(1960, 1390, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
