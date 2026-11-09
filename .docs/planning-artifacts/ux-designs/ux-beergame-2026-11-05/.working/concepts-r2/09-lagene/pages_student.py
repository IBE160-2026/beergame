"""Landing, student hjem, hovedskjermen og spilldynamikken."""
from lib import *

G = S["Grossist"]
UKE = 11
ORDRE = G["ordre"][UKE - 1]
ALL = ("areal", "vei", "inn", "lev", "lager")


def play_body(doc, week=UKE, typed=None, new=(), layers=ALL, role="Grossist"):
    """Telefonen: en graf, et tall, en knapp. Alt annet ligger bak Alle tall."""
    r = S[role]
    out = head(week)
    g, sc = game_graph(doc, week, gy=88, gh=346, layers=layers, new=new, role=role, typed=typed)
    out += g
    out.append(T(20, 490, "Din ordre", 15, 400, G1))
    if typed is not None:
        vei = r["paa_vei"][week - 1]
        out.append(R(370, 490, [("På vei ", 400, G1), (f"{num(vei)} + {num(typed)} = ", 400, G1), (num(vei + typed), 700, VER)], 15, "end"))
        out.append(T(16, 572, num(typed), 88, 300))
        out.append(T(370, 566, "Slett", 15, 400, INK, "end", u=True))
    else:
        out.append(L(22, 508, 22, 572, VER, 2))
    out += keypad(600)
    if typed is not None:
        out.append(btn(20, 712, 350, 56, f"Bestill {num(typed)}"))
        out.append(T(195, 794, "Ordren kan ikke endres etter at du har bestilt.", 13, 400, G1, "middle"))
    return out


def venter_rows(x, y, x2, lh=30, size=15, sara="venter (deg)"):
    rows = [
        ("Ida", "Detaljist", "har bestilt", False),
        ("Sara", "Grossist", sara, True),
        ("Mikkel", "Distributør", "har bestilt", False),
        ("Jonas", "Fabrikk", "venter, 3 min", True),
    ]
    out = []
    for i, (n, rolle, st, sterk) in enumerate(rows):
        yy = y + i * lh
        out.append(R(x, yy, [(n, 700 if sterk else 400, INK), (f", {rolle}", 400, G1)], size))
        out.append(T(x2, yy, st, size, 700 if sterk else 400, INK if sterk else G1, "end"))
    return out


def panel_body(week=UKE):
    """FR-23: alle verdier for setet, ett trykk unna. Ingen Posisjon i Klassespillet."""
    out = [T(20, 62, f"Uke {week}", 17, 700), T(370, 62, "Lukk", 15, 400, INK, "end", u=True)]
    out.append(T(20, 112, "Alle tall", 34, 300))
    n = net()[week - 1]
    rader = [
        ("Lager", num(G["lager"][week - 1]), True),
        ("Restordre", num(G["restordre"][week - 1]), True),
        ("Ordre inn", num(G["innkommende_ordre"][week - 1]), True),
        ("Levering", num(G["levering"][week - 1]), True),
        ("Sendt", num(sendt("Grossist", week)), False),
        ("På vei", num(G["paa_vei"][week - 1]), True),
        ("Neste levering", num(G["levering"][week]), False),
        ("Totalkostnad", kr(G["kost_sum"][week - 1]), False),
    ]
    y = 156
    for navn, verdi, i_graf in rader:
        out.append(T(20, y, navn, 16, 400, INK))
        out.append(T(370, y, verdi, 18, 700, INK, "end"))
        y += 33
    y += 18
    out.append(T(20, y, "Din ordre, Uke 1 til 10", 15, 400, G1))
    y += 26
    step = 35
    for i in range(10):
        out.append(T(36 + i * step, y, num(G["ordre"][i]), 17, 700 if i == 9 else 400, INK, "middle"))
    y += 20
    for i in range(10):
        out.append(T(36 + i * step, y, str(i + 1), 13, 400, G1, "middle"))
    y += 44
    out.append(T(20, y, "Spillet venter på", 15, 400, G1))
    y += 28
    out += venter_rows(20, y, 370, 27, 15)
    y += 27 * 4 + 14
    out.append(T(20, y, "Trykk på et navn i grafen for å skru laget", 13, 400, G1))
    out.append(T(20, y + 18, "av og på.", 13, 400, G1))
    return out


def page_05():
    d = Doc("05-spill", 1600, 1000, "Lag: Spillet, Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn, det åpnede panelet Alle tall, og samme skjerm på laptop.")
    px, py = 60, 78
    d.add(phone(px, py, 1, play_body(d, UKE, ORDRE)))
    d.add(phone(px + 430, py, 1, panel_body()))

    # Laptop: samme graf, større. Ingen ekstra elementer.
    lx, ly, lw, lh = 930, 78, 610, 402
    d.add(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="10" fill="{WHITE}" stroke="{G3}"/>')
    d.add(T(lx + 24, ly + 36, f"Uke {UKE}", 15, 700), T(lx + lw - 24, ly + 36, "Alle tall", 13, 400, INK, "end", u=True))
    lo, hi, yt = yd(UKE)
    sc = Sc(lx + 48, ly + 58, 276, 288, UKE, lo, hi)
    d.add(axes(sc, weeks_for(UKE), yt, size=12))
    d.add(plot(d, sc, ALL))
    items = std_labels(sc, UKE)
    top = G["paa_vei"][UKE - 1] + ORDRE
    d.add(L(sc.X(UKE), sc.Y(G["paa_vei"][UKE - 1]), sc.X(UKE), sc.Y(top), VER, 3))
    items.append((top, "Med ordren", num(top), VER))
    d.add(endlabels(sc, items, 12))
    cx = lx + 438
    d.add(T(cx, ly + 142, "Din ordre", 13, 400, G1))
    d.add(T(cx - 3, ly + 212, num(ORDRE), 72, 300))
    d.add(btn(cx, ly + 236, 148, 44, f"Bestill {num(ORDRE)}", 15))
    d.add(T(cx, ly + 304, "Kan ikke endres", 12, 400, G1), T(cx, ly + 320, "etter at du har bestilt.", 12, 400, G1))

    # Forklaring med få ord.
    tx = 930
    y = 548
    d.add(T(tx, y, "Ett tall, en graf.", 40, 300))
    s, y2 = P(tx, y + 44, f"Sara har Restordre {num(G['restordre'][UKE-1])} og {num(G['paa_vei'][UKE-1])} på vei. Hen taster {num(ORDRE)}, og den røde streken viser hva det gjør med På vei. Hen må selv tenke på resten: Spillet legger ikke tallene sammen og foreslår ingen ordre.", 560, 18, 27, fill=G1)
    d.add(s)
    y2 += 16
    s, y3 = P(tx, y2, "Grafen er det eneste som ligger framme. Linjenavnene er bryterne: Trykk på Ordre inn, så blir den borte. Alle verdier ligger under Alle tall, ett trykk unna, også på 360 px.", 560, 18, 27, fill=G1)
    d.add(s)
    y3 += 16
    s, y4 = P(tx, y3, "Lageret er den svarte linja. Under null heter den Restordre. Det grå feltet er Ordre inn minus Levering, og det er akkurat det lageret endrer seg med.", 560, 18, 27, fill=G1)
    d.add(s)
    d.add(T(tx, 922, "Demodata", 13, 400, G1))
    d.save()


def mini_intro(d, x, y, w, h, week, layers, new, name, sentence, under=False):
    lo, hi, yt = yd(week)
    sc = Sc(x + 26, y, w - 26 - 96, h, week, lo, hi)
    out = axes(sc, [1, week] if week > 2 else [1], [v for v in yt if v == 0 or abs(v) >= 20 and abs(v) <= 40][:3], size=12, nowlabel="")
    out += plot(d, sc, layers, new=new)
    labs = std_labels(sc, week, [l for l in layers if l != "areal"], new=new)
    if under:  # Bare delen under null er det nye
        n = net()
        a, b = n[week - 2], n[week - 1]
        cross = (week - 1) + a / (a - b)
        out.append(path([(sc.X(cross), sc.Y(0)), (sc.X(week), sc.Y(b))], VER, 2.5))
        labs = [(v, nm, t, VER) if nm == "Restordre" else (v, nm, t, c) for v, nm, t, c in labs]
    out += endlabels(sc, labs, 12)
    out.append(T(x, y + h + 48, f"Uke {week}: {name}", 16, 700, VER))
    s, _ = P(x, y + h + 72, sentence, w - 8, 15, 21, fill=INK)
    out.append(s)
    return out


def page_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Lag: En Uke i spillet",
            "Seks telefoner: Uka åpner, beslutningen, venter, Uka går videre, KI-spiller overtar, spillet slutter. Under: hvordan lagene kommer inn uke for uke.")
    s = 0.78
    pw = 390 * s
    gap = (2100 - 120 - 6 * pw) / 5
    y0 = 142
    d.add(T(60, 70, "En Uke er ett tall.", 40, 300))

    def tag(i, navn, tekst):
        x = 60 + i * (pw + gap)
        d.add(T(x, 112, navn, 15, 700))
        d.add(T(x, 132, tekst, 13, 400, G1))
        return x

    # A Uka åpner
    x = tag(0, "A  Uka åpner", "Den nye Uka er det siste stykket av linja.")
    body = head(UKE)
    g, sc = game_graph(d, UKE, gy=88, gh=346)
    body += g
    n = net()
    body.append(path([(sc.X(UKE - 1), sc.Y(n[UKE - 2])), (sc.X(UKE), sc.Y(n[UKE - 1]))], VER, 2.5))
    body.append(T(20, 490, "Din ordre", 15, 400, G1))
    body.append(L(22, 508, 22, 572, VER, 2))
    body += keypad(600)
    d.add(phone(x, y0, s, body))

    # B Beslutningen
    x = tag(1, "B  Beslutningen", f"{num(ORDRE)} med {num(G['paa_vei'][UKE-1])} på vei. Konsekvensen, ikke fasiten.")
    d.add(phone(x, y0, s, play_body(d, UKE, ORDRE)))

    # C Bekreftet
    x = tag(2, "C  Bekreftet", "Låst. Spillet viser hvem det venter på.")
    body = head(UKE)
    g, sc = game_graph(d, UKE, gy=88, gh=346)
    body += g
    vei, top = G["paa_vei"][UKE - 1], G["paa_vei"][UKE - 1] + ORDRE
    body.append(L(sc.X(UKE), sc.Y(vei), sc.X(UKE), sc.Y(top), INK, 3))
    body += [T(sc.X(UKE) + 8, sc.Y(top) + 5, "Bestilt", 13, 400), T(sc.X(UKE) + 58, sc.Y(top) + 5, num(top), 13, 700)]
    body.append(T(20, 500, f"Du bestilte {num(ORDRE)}.", 28, 300))
    body.append(T(20, 548, "Spillet venter på", 15, 400, G1))
    body += venter_rows(20, 582, 370, 34, 16, sara="har bestilt (deg)")
    d.add(phone(x, y0, s, body))

    # D Uka går videre
    x = tag(3, "D  Uka går videre", "Under 2 sek. Kan hoppes over.")
    w12 = UKE + 1
    body = [T(20, 62, f"Uke {w12}", 17, 700), T(370, 62, "Hopp over", 15, 400, INK, "end", u=True)]
    g, sc = game_graph(d, w12, gy=88, gh=346)
    body += g
    body.append(path([(sc.X(w12 - 1), sc.Y(n[w12 - 2])), (sc.X(w12), sc.Y(n[w12 - 1]))], VER, 2.5))
    body.append(R(20, 500, [("Levering ", 400, G1), (num(G["levering"][w12 - 1]), 700, INK)], 22))
    body.append(R(20, 536, [("Ordre inn ", 400, G1), (num(G["innkommende_ordre"][w12 - 1]), 700, INK)], 22))
    body.append(R(20, 572, [("Restordre ", 400, G1), (num(G["restordre"][w12 - 1]), 700, INK)], 22))
    s_, _ = P(20, 620, f"Ordren din på {num(ORDRE)} er ikke her ennå. Den ligger i På vei.", 340, 15, 21, fill=G1)
    body.append(s_)
    d.add(phone(x, y0, s, body))

    # E KI overtar
    x = tag(4, "E  Jonas er borte", "Jonas sin skjerm. KI-spiller er alltid merket.")
    F = S["Fabrikk"]
    w13 = 13
    body = [T(20, 62, f"Uke {w13}", 17, 700), T(370, 62, "Fabrikk", 15, 400, G1, "end")]
    lo, hi, yt = (-22, 44, [-20, 0, 20, 40])
    sc = Sc(40, 88, 238, 300, w13, lo, hi)
    body += axes(sc, [1, 5, 10], yt)
    body += plot(d, sc, ("areal", "vei", "inn", "lev"), role="Fabrikk")
    nf = net("Fabrikk")
    body.append(path(stock(sc, nf, 10), INK, 2.5))
    pts = [(sc.X(t), sc.Y(nf[t - 1])) for t in range(10, 14)]
    body.append(path(pts, INK, 2.5, dash="2 6"))
    body.append(T(sc.X(11), sc.Y(27), "KI-spiller", 13, 700, INK, "middle", h=True))
    body.append(L(sc.X(11), sc.Y(25), sc.X(11), sc.Y(nf[10] + 1), G1, 1))
    body += endlabels(sc, std_labels(sc, w13, ("lager", "inn", "lev", "vei"), "Fabrikk"), 13)
    s_, ye = P(20, 452, "Spillet tok Pause etter 24 t uten ordre. En KI-spiller har bestilt for deg i Uke 11 og 12.", 340, 16, 23)
    body.append(s_)
    s_, ye = P(20, ye + 8, "De andre ser «Fabrikk: KI-spiller».", 340, 15, 21, fill=G1)
    body.append(s_)
    body.append(btn(20, 712, 350, 56, "Ta tilbake setet"))
    d.add(phone(x, y0, s, body))

    # F Spillet slutter
    x = tag(5, "F  Spillet slutter", "Kjeden først. Så per Rolle, ikke per navn.")
    body = [T(20, 62, "Spillet er ferdig", 17, 700)]
    sc = Sc(40, 88, 310, 170, 36, -42, 34)
    body += axes(sc, [1, 10, 20, 30], [-40, -20, 0, 20], now=False)
    body.append(path(stock(sc, n), INK, 2))
    body.append(T(20, 346, "Kjeden, totalkostnad", 15, 400, G1))
    body.append(T(16, 414, num(FX["spill17"]["kjedekost"], 2), 64, 300))
    body.append(T(370, 414, "kr", 22, 300, INK, "end"))
    y = 472
    for rolle in ROLLER:
        v = FX["spill17"]["kost_per_rolle"][rolle]
        body.append(T(20, y, rolle, 17, 700 if rolle == "Grossist" else 400))
        body.append(T(370, y, num(v, 2) + " kr", 17, 700 if rolle == "Grossist" else 400, INK, "end"))
        y += 34
    body.append(T(20, y + 8, "Du var Grossist.", 15, 400, G1))
    body.append(btn(20, 712, 350, 56, "Videre til Debrief"))
    d.add(phone(x, y0, s, body))

    # Under: tekst og lagene som kom
    by = 842
    s_, ye = P(60, by, "Du ser én linje vokse mot høyre, og høyre kant er alltid nå. Hver Uke kan du holde det grå feltet opp mot det lageret faktisk gjorde: Lager er summen av inn og ut. Etter noen uker ser du at det du bestilte, kommer fram om lag fire uker senere. På vei vokser mens Restordren også gjør det, og regnestykket mellom dem er spørsmålet i neste ordre.", 560, 18, 27, fill=G1)
    d.add(s_)
    d.add(T(60, 1158, "Demodata", 13, 400, G1))

    xs = [690, 1040, 1390, 1740]
    w = 320
    d.add(mini_intro(d, xs[0], by - 8, w, 140, 5, ("lager", "inn"), ("inn",), "Ordre inn",
                     "Ordre inn er det som ber om å gå ut av lageret ditt."))
    d.add(mini_intro(d, xs[1], by - 8, w, 140, 8, ("areal", "lager", "inn", "lev"), ("lev",), "Levering",
                     "Levering er det som kommer inn. Inn minus ut er det lageret endrer seg med."))
    d.add(mini_intro(d, xs[2], by - 8, w, 140, 9, ("areal", "lager", "inn", "lev"), (), "Restordre",
                     "Under null heter lageret Restordre. Det koster 1,00 per enhet per uke, mot 0,50 for lager.", under=True))
    d.add(mini_intro(d, xs[3], by - 8, w, 140, 10, ("areal", "vei", "lager", "inn", "lev"), ("vei",), "På vei",
                     "På vei er det du har bestilt og ikke fått. Det kommer fram om lag 4 uker etter at du bestilte."))
    d.save()


def page_04():
    d = Doc("04-student-hjem", 1000, 900, "Lag: Saras hjem",
            "To telefoner: registrering fra Invitasjon, og hjem mens spillet venter på Sara.")
    # Registrering
    b = [T(20, 62, "Lag", 17, 700)]
    b.append(T(20, 148, "Du er invitert", 34, 300))
    s, y = P(20, 186, "Bård har invitert deg til Klassen class-of-1994 i IBE160. Invitasjonen er gyldig i 14 dager.", 340, 16, 23, fill=G1)
    b.append(s)
    y += 36
    for label, val, mark in [("E-post", "sara@student.example.no", False), ("Navn", "Sara", False), ("Passord", "", True)]:
        b.append(T(20, y, label, 15, 400, G1))
        if mark:
            b.append(L(21, y + 12, 21, y + 34, VER, 2))
        else:
            b.append(T(20, y + 30, val, 18, 400))
        b.append(L(20, y + 42, 370, y + 42, G3, 1))
        y += 78
    b.append(T(20, y + 4, "Minst 10 tegn.", 13, 400, G1))
    b.append(btn(20, 712, 350, 56, "Opprett konto"))
    d.add(phone(60, 28, 1, b))

    # Hjem under spill
    b = [T(20, 62, "Spill 17", 17, 700), T(370, 62, "Sara", 15, 400, G1, "end")]
    b.append(T(20, 124, "Spillet venter på deg.", 30, 300, VER))
    s, y = P(20, 158, "Du er Grossist. Jonas har heller ikke bestilt. Det har gått 3 min.", 340, 15, 21, fill=G1)
    b.append(s)
    b.append(btn(20, y + 10, 350, 56, f"Åpne Uke {UKE}"))
    y += 104
    b.append(T(20, y, "Setene", 15, 400, G1))
    b += venter_rows(20, y + 28, 370, 27, 15)
    y += 28 + 27 * 4 + 12
    b.append(T(20, y, "Stegene", 15, 400, G1))
    y += 28
    for i, navn in enumerate(["Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "Rapport"]):
        forst = i == 0
        b.append(T(20, y, navn, 16, 700 if forst else 400, INK if forst else G1))
        if forst:
            b.append(T(370, y, "nå", 15, 700, VER, "end"))
        y += 27
    y += 14
    b.append(R(20, y, [("Neste frist  ", 400, G1), ("Spillfrist ti. 8. des", 700, INK)], 15))
    b.append(R(20, y + 26, [("Labtime  ", 400, G1), ("to. 26. nov 14:15, Datalab A2", 400, INK)], 15))
    d.add(phone(550, 28, 1, b))
    d.add(T(60, 892, "Demodata", 13, 400, G1))
    d.save()


def page_01():
    d = Doc("01-landing", 1440, 1200, "Lag: For faglærere",
            "Landingsside for faglærere: en stor graf for ett sete, og starten av lærerens oversikt.")
    d.add(T(80, 66, "Lag", 22, 700))
    lines = ["En forsyningskjedeøvelse for hele kullet,", "fra Invitasjon til PDF-rapport."]
    y = 160
    for l in lines:
        d.add(T(76, y, l, 58, 300))
        y += 70
    s, y2 = P(80, y + 4, "Studentene spiller hvert sitt ledd på mobilen, og ser én graf som vokser med spillet. Nye begreper kommer når spillet gjør dem relevante. Du ser alle spillene på én skjerm.", 720, 20, 30, fill=G1)
    d.add(s)
    d.add(btn(80, y2 + 22, 240, 58, "Be om lærertilgang"))
    d.add(T(348, y2 + 58, "Logg inn", 17, 400, INK, u=True))

    wk = 29
    gy = y2 + 120
    lo, hi = (-42, 92)
    sc = Sc(120, gy, 1100, 340, wk, lo, hi)
    d.add(axes(sc, [1, 10, 20], [-40, 0, 40, 80], nowlabel="nå", size=14))
    d.add(plot(d, sc, ALL, sw=1.2))
    d.add(endlabels(sc, std_labels(sc, wk), 15, xoff=12))
    d.add(T(120, gy + 340 + 50, "Ett setes egen graf. Den svarte linja er lageret, under null er det Restordre. Demodata.", 14, 400, G1))

    # Neste seksjon: lærerens oversikt, ekte rader
    sy = gy + 340 + 118
    d.add(T(76, sy, "Alle spillene på én skjerm.", 36, 300))
    rows = sorted(FX["klasse"]["spill"], key=lambda g: {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}[g["status"]])
    d.add(teacher_rows(d, rows[:5], 80, sy + 34, 680, 36))
    fx = 760
    fakta = ["Klasser på rundt 250 studenter", "KI-spillere fyller tomme seter", "Ett fravær stopper ikke gruppa", "Ingen spill blir stående uferdig"]
    fakta2 = ["Studentene spiller på mobil", "Alt er på norsk", "Studentlisten fra Canvas-eksport"]
    for i, f in enumerate(fakta):
        d.add(T(fx, sy + 58 + i * 32, f, 17, 400))
    for i, f in enumerate(fakta2):
        d.add(T(fx + 320, sy + 58 + i * 32, f, 17, 400))
    d.save()


def teacher_rows(d, rows, x, y, w, lh):
    from pages_laerer import teacher_row
    out = []
    for i, g in enumerate(rows):
        out += teacher_row(g, x, y + i * lh, w, lh)
    return out
