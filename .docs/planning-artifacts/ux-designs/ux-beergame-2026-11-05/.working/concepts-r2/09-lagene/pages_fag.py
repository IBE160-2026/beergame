"""De faglige flatene: pedagogikkark, Debrief og kontaktark."""
from lib import *

G = S["Grossist"]
UKE = 11
ORDRE = G["ordre"][UKE - 1]
ALL = ("areal", "vei", "inn", "lev", "lager")
SIM = FX["bare_sara_teller_paa_vei"]
SPILL = FX["klasse"]["spill"]
F17 = FX["spill17"]["forsterkning"]
K17 = FX["spill17"]["kost_per_rolle"]


def note(x, y, w, head_, tag, body, q):
    out = [T(x, y, head_, 20, 700)]
    out.append(T(x, y + 24, tag, 14, 700, G1))
    s, yy = P(x, y + 50, body, w, 16, 23)
    out.append(s)
    s, yy = P(x, yy + 6, "Neste ordre: " + q, w, 16, 23, fill=G1)
    out.append(s)
    return out


def page_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Lag: Grafgrammatikken",
            "Saras ene graf ved Uke 5, 11, 18 og 29 i samme målestokk, med prinsippene den lærer bort, forskjellen på Klassespill og Replay, og simulert referanse.")
    d.add(T(58, 84, "Det finnes bare én graf. Den vokser.", 52, 300))
    d.add(T(60, 124, "Saras graf, Grossist i spill 17, i samme målestokk fra Uke 5 til Uke 29. Høyre kant er alltid nå. Demodata.", 18, 400, G1))

    pxw = 27.0     # piksler per Uke
    pyu = 2.45     # piksler per enhet
    x0 = 110
    notex = 1032
    notew = 372
    rows = [
        (5, (0, 16), [0], [1, 5], ("lager", "inn"), ("inn",)),
        (11, (-20, 44), [-20, 0, 20, 40], [1, 5, 10], ALL, ()),
        (18, (-40, 84), [-40, -20, 0, 20, 40, 60, 80], [1, 5, 10, 15], ALL, ()),
        (29, (-40, 92), [-40, -20, 0, 20, 40, 60, 80], [1, 5, 10, 15, 20, 25], ALL, ()),
    ]
    y = 176
    notes = {
        5: note(notex, 176, notew, "Uke 5: Lager og Ordre inn", "P1 Lager er en opphopning",
                f"Lager {num(G['lager'][4])}, Ordre inn {num(G['innkommende_ordre'][4])}. To linjer, og lageret står stille.",
                "Hvor lenge holder lageret hvis det som går ut, øker?"),
    }
    for week, (lo, hi), yt, wks, lay, new in rows:
        h = (hi - lo) * pyu
        sc = Sc(x0, y, week * pxw, h, week, lo, hi)
        d.add(axes(sc, wks, yt, size=13, nowlabel="nå"))
        d.add(plot(d, sc, lay, new=new))
        items = std_labels(sc, week, [l for l in lay if l != "areal"], new=new)
        if week == 11:
            vei = G["paa_vei"][10]
            d.add(L(sc.X(11), sc.Y(vei), sc.X(11), sc.Y(vei + ORDRE), VER, 3))
            items.append((vei + ORDRE, "Med ordren", num(vei + ORDRE), VER))
            # Uke 11: arealet denne uka
            d.add(T(sc.X(11) - 6, sc.Y(-18), f"Inn {num(G['levering'][10])} minus ut {num(G['innkommende_ordre'][10])} = {num(G['levering'][10]-G['innkommende_ordre'][10])}", 13, 400, G1, "end"))
        if week == 18:
            # P2: fra ordre til levering
            ax, bx = sc.X(11) - pxw / 2, sc.X(15) - pxw / 2
            ly = sc.Y(32)
            d.add(L(ax, ly, bx, ly, VER, 1.5))
            d.add(L(ax, ly - 5, ax, ly + 5, VER, 1.5))
            d.add(L(bx, sc.Y(G["levering"][14]), bx, ly + 5, VER, 1.5))
            d.add(T(ax - 8, ly + 5, f"{num(ORDRE)} bestilt i Uke 11, {num(G['levering'][14])} levert i Uke 15", 13, 700, VER, "end", h=True))
        if week == 29:
            # P1: skravert der mer kommer inn enn ut
            d.add(T(sc.X(29) - 8, sc.Y(-36), "Skravert: lageret stiger", 13, 400, G1, "end"))
            d.add(T(sc.X(0) + 4, sc.Y(-22), "Grått: lageret faller", 13, 400, G1))
        d.add(endlabels(sc, items, 13))
        if week == 11:
            notes[11] = note(notex, y, notew, "Uke 11: fire lag", "P1, P2, P3 Det som er på vei blir glemt",
                             f"Restordre {num(G['restordre'][10])} roper høyest. På vei {num(G['paa_vei'][10])} står stille ved siden av: det kommer, om lag 4 uker etter at det ble bestilt, og det teller allerede.",
                             f"{num(ORDRE)} gjør På vei til {num(G['paa_vei'][10] + ORDRE)}. Hva vil du ha der?")
        if week == 18:
            n = net()
            notes[18] = note(notex, y + 40, notew, "Uke 18: forsinkelsen er synlig", "P2 Forsinkelse, P3",
                             f"Restordre {num(-n[17])} og På vei {num(G['paa_vei'][17])}. Regn selv: Det som er på vei, dekker de {num(-n[17])} som skyldes, og {num(G['paa_vei'][17] + n[17])} til.",
                             f"Hva skjer med lageret den uka alt dette kommer fram?")
        if week == 29:
            n = net()
            notes[29] = note(notex, y + 90, notew, "Uke 29: det snudde", "P1, P8 Restordre koster dobbelt",
                             f"Lager {num(n[28])}. Linja stiger bare når inn er større enn ut, og det er det skraverte. Lager koster 0,50 per enhet per uke, Restordre 1,00.",
                             f"Ordre inn er {num(G['innkommende_ordre'][28])}. Hvor mange uker holder {num(n[28])}?")
        y = 346 if week == 5 else y + h + 74
    for k in notes:
        d.add(notes[k])
    d.add(T(60, 1372, "Demodata. P4 og P5 kommer i Debriefen, der samme graf vises i fire utgaver. P6 Struktur gir atferd: de samme lagene gir nesten samme form i alle 60 spill.", 14, 400, G1))

    # Høyre: Hjelpegrad og referanse
    rx = 1486
    rw = 454
    d.add(T(rx, 176, "Hjelpegrad: samme Uke 11, to utgaver", 22, 700))
    s, y = P(rx, 208, "I Klassespillet står På vei for seg, på null. Studenten må selv legge sammen.", rw, 16, 23, fill=G1)
    d.add(s)
    sc = Sc(rx + 26, y + 8, rw - 26 - 118, 190, 11, -22, 44)
    d.add(axes(sc, [1, 5, 10], [-20, 0, 20, 40], size=12))
    d.add(plot(d, sc, ("vei", "lager")))
    d.add(endlabels(sc, std_labels(sc, 11, ("vei", "lager")), 13))
    y = y + 8 + 190 + 58
    s, y = P(rx, y, "I Replay og gjennomgangen løftes samme linje opp på Lager. Toppen får et navn: Posisjon = Lager − Restordre + På vei.", rw, 16, 23, fill=G1)
    d.add(s)
    sc = Sc(rx + 26, y + 8, rw - 26 - 118, 190, 11, -22, 44)
    d.add(axes(sc, [1, 5, 10], [-20, 0, 20, 40], size=12))
    d.add(plot(d, sc, ("band", "lager", "pos"), new=("pos",)))
    p = pos()[10]
    d.add(L(sc.X(11), sc.Y(p), sc.X(11), sc.Y(p + ORDRE), VER, 3))
    d.add(endlabels(sc, [(p, "Posisjon", num(p), VER), (p + ORDRE, "Med ordren", num(p + ORDRE), VER), lagerlabel("Grossist", 11)], 13))
    d.add(T(sc.X(4), sc.Y(18) + 4, "På vei", 13, 400, G1, "middle"))
    y = y + 8 + 190 + 58
    s, y = P(rx, y, f"{num(net()[10])} + {num(G['paa_vei'][10])} = {num(p)}. Dette er P3. Laget kommer etter Debriefen, for studenten skal først ha kjent feilen.", rw, 16, 23)
    d.add(s)

    y += 26
    d.add(T(rx, y, "Etter Debriefen: Simulert referanse, P3 og P7", 22, 700))
    y += 14
    sc = Sc(rx + 26, y + 8, rw - 26 - 118, 200, 36, -42, 34)
    d.add(axes(sc, [1, 10, 20, 30], [-40, -20, 0, 20], now=False, size=12))
    d.add(path(stock(sc, net("Grossist", SIM["serier"])), G1, 1.5, dash="5 4"))
    d.add(path(stock(sc, net()), INK, 2.5))
    d.add(R(sc.X(36) + 8, sc.Y(net()[35]) + 16, [("Spill 17", 700, INK)], 13))
    d.add(T(sc.X(36) + 8, sc.Y(net('Grossist', SIM['serier'])[35]) - 2, "Simulert", 13, 400, G1))
    y = y + 8 + 200 + 52
    d.add(R(rx, y, [("Grossist ", 400, G1), (kr(K17["Grossist"]), 700, INK), (" mot ", 400, G1), (kr(SIM["kost_per_rolle"]["Grossist"]), 700, INK), (" simulert", 400, G1)], 15))
    d.add(R(rx, y + 22, [("Forsterkning ", 400, G1), (x_(F17["Grossist"]), 700, INK), (" mot ", 400, G1), (x_(SIM["forsterkning"]["Grossist"]), 700, INK), (" simulert", 400, G1)], 15))
    s, y = P(rx, y + 50, "Samme kjede, der Grossist regner med alt på vei. Viser sammenhengen, ikke en fasit: En regel som jager siste ordre for hardt, ga Fabrikk 12× i simuleringen (P7).", rw, 15, 21, fill=G1)
    d.add(s)
    d.save()


def step_head(x, y, n, title):
    return [R(x, y, [(f"{n}  ", 700, G1), (title, 700, INK)], 18)]


def page_07():
    d = Doc("07-debrief", 2100, 1200, "Lag: Gruppedebrief",
            "Gruppedebrief i fem steg på delt skjerm: Forklaring, etterspørselen avsløres, alle ordrer i én graf, Uke 11, og quiz.")
    d.add(T(58, 72, "Samme graf, fire utgaver. Gruppa legger på ett lag om gangen.", 40, 300))
    d.add(T(60, 106, "Delt skjerm: Ida, Sara, Mikkel og Jonas ser det samme. Den som trykker Neste lag, gjør det for alle. Øvelsen kan nå navngis: dere har spilt Beer Game.", 16, 400, G1))

    # Steg 1
    x = 60
    d.add(step_head(x, 158, 1, "Skriv Forklaring"))
    s, y = P(x, 188, "Hva tror du skjedde med kundene? Hvorfor ble det slik?", 300, 16, 23, fill=G1)
    d.add(s)
    s, y = P(x, y + 14, "Kundene må ha kjøpt stadig mer, og leveringene uteble. Derfor bestilte jeg mye i Uke 11.", 300, 18, 27)
    d.add(s)
    d.add(L(x, y + 2, x + 300, y + 2, G3, 1))
    d.add(btn(x, y + 22, 240, 50, "Lever Forklaring", 16))
    s, y = P(x, y + 102, "Avsløringen er låst til alle fire har levert.", 300, 16, 23, fill=VER, w=700)
    d.add(s)
    d.add(T(x, y + 6, "Ida har levert", 15, 400, G1), T(x, y + 30, "Mikkel har levert", 15, 400, G1), T(x, y + 54, "Sara skriver", 15, 700), T(x, y + 78, "Jonas skriver", 15, 700))

    # Steg 2: klimaks, fire utgaver med etterspørselen
    x = 440
    d.add(step_head(x, 158, 2, "Etterspørselen avsløres"))
    d.add(T(x, 214, "Kundene: 4 per uke, så 8 fra Uke 5. Stabil resten av spillet.", 28, 300, VER))
    rx = x + 90
    w = 640
    rh = 102
    lo, hi = -64, 58
    y0 = 236
    for i, rolle in enumerate(ROLLER):
        sc = Sc(rx, y0 + i * (rh + 16), w, rh, 36, lo, hi)
        d.add(L(rx, sc.Y(0), rx + w, sc.Y(0), G3, 1))
        d.add(path(stock(sc, net(rolle)), INK, 2.5 if rolle == "Grossist" else 1.5))
        d.add(path(flow(sc, S["Detaljist"]["innkommende_ordre"]), VER, 2, join="miter"))
        d.add(T(rx - 12, sc.Y(0) - 3, rolle, 15, 700 if rolle == "Grossist" else 400, INK, "end"))
        d.add(T(rx - 12, sc.Y(0) + 15, PERSON[rolle], 13, 400, G1, "end"))
    ax = y0 + 4 * (rh + 16) + 4
    for t in [1, 10, 20, 30]:
        lab = f"Uke {t}" if t == 1 else str(t)
        d.add(T(sc.X(t - 1) + 1 if t == 1 else sc.X(t), ax, lab, 13, 400, G1, "start" if t == 1 else "middle"))
    d.add(T(rx + w, ax, "36", 13, 400, G1, "middle"))
    d.add(T(rx + w + 10, y0 + 40, "Lager,", 13, 400, INK), T(rx + w + 10, y0 + 56, "under null", 13, 400, INK), T(rx + w + 10, y0 + 72, "Restordre", 13, 400, INK))

    # Steg 3: alle ordre i én graf
    x = 1250
    d.add(step_head(x, 158, 3, "Ordrene, i én graf"))
    d.add(T(x, 214, "Alt annet kom fra kjeden.", 28, 300))
    sc = Sc(x + 26, 240, 610, 420, 36, 0, 34)
    d.add(axes(sc, [1, 10, 20, 30], [0, 10, 20, 30], now=False))
    d.add(T(sc.X(36), 240 + 420 + 21, "36", 13, 400, G1, "middle"))
    stilart = {"Detaljist": (G2, 1.5, None), "Grossist": (INK, 2.5, None), "Distributør": (G1, 1.25, None), "Fabrikk": (G1, 1.25, "5 4")}
    for rolle in ROLLER:
        c, sw, da = stilart[rolle]
        d.add(path(stock(sc, S[rolle]["ordre"], start=1), c, sw, da))
    d.add(path(flow(sc, S["Detaljist"]["innkommende_ordre"]), VER, 2, join="miter"))
    for rolle, xt, anchor in [("Fabrikk", 18, "middle"), ("Grossist", 10.6, "end"), ("Distributør", 16.2, "end")]:
        v = S[rolle]["ordre"]
        d.add(T(sc.X(xt), sc.Y(max(v)) - 10, f"{rolle} {num(max(v))}", 13, 700 if rolle == "Grossist" else 400, INK, anchor, h=True))
    vd = S["Detaljist"]["ordre"]
    d.add(T(sc.X(6.5), sc.Y(max(vd[:10])) - 8, f"Detaljist {num(max(vd))}", 13, 400, G1, "middle", h=True))
    d.add(T(sc.X(4) - 6, sc.Y(8) + 4, "Kundene 8", 13, 700, VER, "end"))
    # Forsterkning som tall, rett på høyre side
    fx = x + 660
    d.add(T(fx, 262, "Forsterkning", 14, 400, G1))
    for i, rolle in enumerate(reversed(ROLLER)):
        yy = 318 + i * 88
        d.add(T(fx - 2, yy, x_(F17[rolle]), 42, 300))
        d.add(T(fx, yy + 22, rolle, 14, 700 if rolle == "Grossist" else 400))
    d.add(T(x, 712, "Hvert ledd så bare ordrene fra nedstrøms (P4). Svingningene vokser og kommer senere (P5).", 15, 400, G1))

    # Lag-kontroll: gruppa styrer
    ly = 744
    d.add(T(60, ly, "Lag", 15, 400, G1))
    xx = 100
    for navn, st in [("Lager", 0), ("Etterspørsel", 0), ("Ordre", 0), ("Forsterkning", 1)]:
        c = {0: G1, 1: VER}[st]
        d.add(T(xx, ly, navn, 15, 700 if st else 400, c))
        xx += est(navn, 15, 700) + 24
    d.add(T(xx + 12, ly, "Neste lag: Posisjon", 15, 700, INK, u=True))

    # Steg 4: ditt øyeblikk
    x = 60
    top = 800
    d.add(step_head(x, top, 4, "Ditt øyeblikk: Uke 11"))
    n = net()
    rows = [("Du så", f"Restordre {num(G['restordre'][10])}, Ordre inn {num(G['innkommende_ordre'][10])}, På vei {num(G['paa_vei'][10])}."),
            ("Posisjon", f"{num(G['lager'][10])} − {num(G['restordre'][10])} + {num(G['paa_vei'][10])} = {num(pos()[10])}."),
            ("Du bestilte", f"{num(ORDRE)}. Posisjon ble {num(pos()[10] + ORDRE)}."),
            ("Det kostet", f"Restordre {num(max(G['restordre']))} i Uke {G['restordre'].index(max(G['restordre'])) + 1}, Lager {num(max(G['lager']))} i Uke {G['lager'].index(max(G['lager'])) + 1}.")]
    yy = top + 36
    for a, b in rows:
        d.add(T(x, yy, a, 15, 400, G1))
        s, ye = P(x + 90, yy, b, 270, 15, 21)
        d.add(s)
        yy = ye + 8
    s, ye = P(x, yy + 8, "Du svarte på restordren du så. Det du allerede hadde bestilt, sto ikke i regnestykket.", 360, 16, 23)
    d.add(s)
    d.add(T(x, ye + 2, "KI-generert, kan ta feil. Tallene er fra loggen.", 13, 400, G1))

    gx = 490
    sc = Sc(gx, top + 22, 640, 280, 36, -42, 34)
    d.add(axes(sc, [1, 10, 20, 30], [-40, -20, 0, 20], now=False))
    d.add(T(sc.X(36), top + 22 + 280 + 21, "36", 13, 400, G1, "middle"))
    d.add(path(stock(sc, net("Grossist", SIM["serier"])), G1, 1.5, dash="5 4"))
    d.add(path(stock(sc, n), INK, 2.5))
    d.add(L(sc.X(11), sc.y0, sc.X(11), sc.y0 + sc.h, VER, 1))
    d.add(T(sc.X(11) + 6, sc.y0 + 12, f"Uke 11: {num(ORDRE)}", 13, 700, VER))
    d.add(T(sc.X(13), sc.Y(-33), "Spill 17", 13, 700, INK, "middle", h=True))
    d.add(T(sc.X(19.5), sc.Y(-14), "Simulert", 13, 400, G1, "middle", h=True))
    d.add(R(gx, top + 22 + 280 + 46, [("Grossist ", 400, G1), (kr(K17["Grossist"]), 700, INK), (" mot ", 400, G1), (kr(SIM["kost_per_rolle"]["Grossist"]), 700, INK), (" simulert.  Kjeden ", 400, G1), (kr(FX["spill17"]["kjedekost"]), 700, INK), (" mot ", 400, G1), (kr(SIM["kjedekost"]), 700, INK), (".", 400, G1)], 14))
    d.add(T(gx, top + 22 + 280 + 66, "Simulert: samme kjede, men Grossist regner med alt på vei. Viser sammenhengen, ikke en fasit.", 13, 400, G1))

    ox = 1160
    d.add(T(ox, top + 36, "Hva de andre så i Uke 11", 15, 400, G1))
    yy = top + 66
    for rolle in ["Detaljist", "Distributør", "Fabrikk"]:
        r = S[rolle]
        lab = lagerlabel(rolle, 11)
        d.add(T(ox, yy, f"{PERSON[rolle]}, {rolle}", 15, 700))
        d.add(T(ox, yy + 21, f"{lab[1]} {lab[2]}, Ordre inn {num(r['innkommende_ordre'][10])}", 15, 400, INK))
        yy += 54
    D = S["Distributør"]
    s, ye = P(ox, yy + 6, f"Mikkel så tallet ditt i Uke 13, som Ordre inn {num(D['innkommende_ordre'][12])}, og bestilte {num(D['ordre'][12])}. Mikkel så tallet, ikke hvorfor.", 310, 15, 21)
    d.add(s)

    # Steg 5
    qx = 1530
    d.add(step_head(qx, top, 5, "Debrief-quiz"))
    s, y = P(qx, top + 36, f"Uke 11: Lager {num(G['lager'][10])}, Restordre {num(G['restordre'][10])}, På vei {num(G['paa_vei'][10])}. Hva er Posisjon?", 500, 18, 26)
    d.add(s)
    y += 8
    svar = [(num(-G["restordre"][10]), False, False), (num(pos()[10]), True, False), (num(G["paa_vei"][10]), False, True), (num(G["paa_vei"][10] + G["restordre"][10]), False, False)]
    for i, (v, ok, valgt) in enumerate(svar):
        xp = qx + i * 124
        d.add(T(xp, y + 28, v, 34, 300 if not (ok or valgt) else 400, VER if valgt else (INK if ok else G1)))
        if valgt:
            d.add(T(xp, y + 52, "Ditt svar", 13, 700, VER))
        if ok:
            d.add(T(xp, y + 52, "Riktig", 13, 700, INK))
    y += 84
    s, y = P(qx, y, f"{num(G['paa_vei'][10])} er det som kommer. Restordren må trekkes fra, for de enhetene er allerede lovet bort: {num(G['lager'][10])} − {num(G['restordre'][10])} + {num(G['paa_vei'][10])} = {num(pos()[10])}. Du kan prøve igjen.", 500, 16, 23)
    d.add(s)
    d.add(T(60, 1180, "Demodata. Simulerte tall er merket.", 13, 400, G1))
    d.save()


# ---------- kontaktark ----------
def mini(d, x, y, w, h, series, ymin, ymax, upto=None):
    upto = upto or max(len(v) for v, *_ in series)
    sc = Sc(x, y, w, h, upto, ymin, ymax, start=1)
    out = []
    if ymin < 0 < ymax:
        out.append(L(x, sc.Y(0), x + w, sc.Y(0), G3, 1))
    for vals, c, sw, *da in series:
        out.append(path([(sc.X(t), sc.Y(vals[t - 1])) for t in range(1, len(vals) + 1)], c, sw, da[0] if da else None))
    return out


def lines(x, y, rows, size=12, lh=18):
    out = []
    for i, r in enumerate(rows):
        t, w, c = r if isinstance(r, tuple) else (r, 400, INK)
        out.append(T(x, y + i * lh, t, size, w, c))
    return out


def page_09():
    d = Doc("09-alle-sider", 2000, 1400, "Lag: Alle sider",
            "Kontaktark over de andre sidene, gruppert per rolle. Samme graf og samme luft overalt.")
    R_ = FX["replay_sara"]
    RS = R_["serier"]
    n = net()
    d.add(T(58, 72, "Alle andre sider", 40, 300))
    d.add(T(60, 104, "Ingen nye grafiske former. Hver side har én graf, én tabell eller én tekst. Demodata.", 16, 400, G1))

    cw, rh = 232, 418
    gy0 = 180

    def cell(col_x, c, r_, title, one, content):
        x, y = col_x + c * cw, gy0 + r_ * rh
        d.add(content(x, y))
        d.add(T(x, y + 262, title, 15, 700))
        s, _ = P(x, y + 284, one, cw - 26, 13, 18, fill=G1)
        d.add(s)

    W = cw - 28
    # ---------- Student ----------
    sx = 60
    d.add(T(sx, 150, "Student", 22, 300))
    cell(sx, 0, 0, "Invitasjon og registrering", "Klassen du er invitert til, navn og passord.",
         lambda x, y: lines(x, y + 30, [("Du er invitert", 300, INK), "", ("E-post", 400, G1), "sara@student.example.no", "", ("Passord", 400, G1)], 15, 26))
    cell(sx, 1, 0, "Logg inn", "E-post og passord. Glemt passord under.",
         lambda x, y: lines(x, y + 30, [("Logg inn", 300, INK), "", ("E-post", 400, G1), "", ("Passord", 400, G1)], 15, 26))
    cell(sx, 2, 0, "Regler før første ordre", "Du bestemmer ett tall per Uke. Systemet regner resten.",
         lambda x, y: mini(d, x, y + 70, W, 60, [([12] * 4, INK, 2)], 0, 18) + lines(x, y + 30, [("Ett tall per Uke", 300, INK)], 18))
    cell(sx, 3, 0, "Startoppgave", "Inn og ut er gitt. Tegn lageret. Materialbalansen før spillet.",
         lambda x, y: mini(d, x, y + 40, W, 90, [(G["levering"][:12], G1, 1.25, "1 3.5"), (G["innkommende_ordre"][:12], G1, 1.25)], 0, 16)
         + mini(d, x, y + 140, W, 60, [([12, 12, 12, 12, 12, 12], INK, 2)], -10, 18, upto=12)
         + lines(x, y + 225, [("Tegn videre", 400, VER)], 13))
    cell(sx, 0, 1, "Replay", "Tre KI-spillere, ny etterspørsel. Posisjon er nå et eget lag.",
         lambda x, y: (lambda sc: plot(d, sc, ("band", "lager", "pos"), data=RS, upto=18, new=("pos",)))(Sc(x, y + 20, W, 200, 18, -30, 50)))
    cell(sx, 1, 1, "Replay-gjennomgang", "Klassespillet og Replay side om side. Ikke like for like.",
         lambda x, y: lines(x, y + 20, [("Klassespill", 400, G1)], 12) + mini(d, x, y + 28, W, 90, [(n, INK, 1.5)], -42, 34) + lines(x, y + 142, [("Replay", 400, G1)], 12) + mini(d, x, y + 150, W, 90, [(net("Grossist", RS), INK, 1.5)], -42, 34, upto=33))
    cell(sx, 2, 1, "Individuell test: flervalg", "Spørsmål fra spillet ditt, med grafen som kilde.",
         lambda x, y: lines(x, y + 30, [("Hva endrer lageret?", 300, INK), "", "Inn minus ut", ("Ordren du la nå", 400, G1), ("Restordren", 400, G1), ("Prisen", 400, G1)], 15, 26))
    cell(sx, 3, 1, "Individuell test: tegne, tabell", "Dra punktene, eller skriv i tabellen. Grafen fanger tallene.",
         lambda x, y: mini(d, x, y + 30, W, 110, [(G["ordre"][:14], INK, 1.5)], 0, 28)
         + [f'<circle cx="{x + W:.1f}" cy="{y + 30 + 110 - G["ordre"][13] / 28 * 110:.1f}" r="5" fill="{VER}"/>']
         + [T(x + i * 46, y + 172, f"Uke {w}" if i == 0 else str(w), 13, 400, G1) for i, w in enumerate([14, 15, 16, 17])]
         + [T(x + i * 46, y + 196, num(G["ordre"][13]) if i == 0 else "?", 14, 700 if i == 0 else 400, INK if i == 0 else VER) for i in range(4)])
    cell(sx, 0, 2, "Individuell test: langsvar", "Forklar med egne ord. Spilleloggen ligger ved siden av.",
         lambda x, y: lines(x, y + 30, [("Hvorfor skjedde det?", 300, INK), "", "Da Restordren steg,", "bestilte jeg uten å", "regne med det som", "allerede var på vei."], 15, 26))
    cell(sx, 1, 2, "KI-vurdering", "Teller ikke. Er aldri en karakter. KI-generert, kan ta feil.",
         lambda x, y: lines(x, y + 30, [("KI-generert, kan ta feil", 700, INK), "", "Du forklarer hvorfor", "ordren ble stor. Du", "nevner ikke hvor lenge", "den var underveis.", "", ("Teller ikke.", 700, G1)], 14, 24))
    cell(sx, 2, 2, "Studentrapport (PDF)", "Hele reisen på ett ark: graf, Forklaring, test.",
         lambda x, y: lines(x, y + 30, [("Sara, Grossist", 700, INK), ("Spill 17, IBE160", 400, G1)], 13) + mini(d, x, y + 70, W, 90, [(n, INK, 1.5)], -42, 34)
         + lines(x, y + 190, [(f"Totalkostnad {kr(K17['Grossist'])}", 400, INK), (f"Forsterkning {x_(F17['Grossist'])}", 400, INK)], 13, 20))

    def smalls(x, y):
        out = []
        ferdige = [g for g in SPILL if g["status"] == "ferdig"][:16]
        cw2, ch2 = W / 4, 52
        for i, g in enumerate(ferdige):
            cx = x + (i % 4) * cw2
            cy = y + 24 + (i // 4) * ch2
            out += mini(d, cx, cy, cw2 - 6, ch2 - 8, [(g["ordre"]["Fabrikk"], INK, 0.9)], 0, 40)
        return out
    cell(sx, 3, 2, "Alle spill side om side", "Etter Debriefen: spillene har samme form, uten navn.", smalls)

    # ---------- Faglærer ----------
    fx = 1040
    d.add(T(fx, 150, "Faglærer", 22, 300))
    cell(fx, 0, 0, "Lærerhjem", "Klassene dine og neste frist.",
         lambda x, y: lines(x, y + 30, [("class-of-1994", 300, INK), ("IBE160, 60 Klassespill", 400, G1), "", ("Spillfrist ti. 8. des", 700, INK), ("Labtime to. 26. nov", 400, INK)], 15, 26))
    mo = FX["klasse"]["moenstre"]
    ks = list(mo.items())

    def rap(x, y):
        tot = max(mo.values())
        out = lines(x, y + 30, [("Klasserapport", 300, INK)], 18)
        for i, (k, v) in enumerate(ks):
            yy = y + 66 + i * 58
            for j, part in enumerate(wrap(k, W, 12)):
                out.append(T(x, yy + j * 15, part, 12, 400, G1))
            out.append(L(x, yy + 36, x + v / tot * (W - 30), yy + 36, INK, 2))
            out.append(T(x + v / tot * (W - 30) + 6, yy + 40, num(v), 12, 700))
        return out
    cell(fx, 1, 0, "Klasserapport", "Hva klassen gjorde, med Detected patterns og trakt.", rap)
    cell(fx, 2, 0, "Spillinnsikt", "Ett spill uke for uke, alle fire seter i samme graf.",
         lambda x, y: mini(d, x, y + 30, W, 170, [(S["Detaljist"]["ordre"], G2, 1), (S["Grossist"]["ordre"], INK, 1.8), (S["Distributør"]["ordre"], G1, 1), (S["Fabrikk"]["ordre"], G1, 1, "4 3")], 0, 34)
         + [L(x + W * 10 / 35, y + 30, x + W * 10 / 35, y + 200, VER, 1), T(x + W * 10 / 35 + 4, y + 42, "Uke 11", 12, 700, VER)])
    cell(fx, 0, 1, "Studentside", "En student: steg, Forklaring, test og rapport.",
         lambda x, y: lines(x, y + 30, [("Sara", 300, INK), ("Grossist, spill 17", 400, G1), "", ("Klassespill ferdig", 400, INK), ("Debrief ferdig", 400, INK), ("Quiz bestått", 400, INK), ("Replay ikke startet", 400, G1)], 15, 26))

    def plenum(x, y):
        out = []
        for i, g in enumerate(sorted(SPILL, key=lambda g: g["spill"])[:40]):
            cx = x + (i % 5) * (W / 5)
            cy = y + 30 + (i // 5) * 26
            out += mini(d, cx, cy, W / 5 - 5, 22, [(g["ordre"]["Fabrikk"], INK, 0.7)], 0, 40, upto=36)
        return out
    cell(fx, 1, 1, "Alle spill i plenum", "Stor skjerm: alle linjene, uten navn på studenter.", plenum)
    fj = FX["klasse"]["fjoraaret"]
    fe = FX["klasse"]["ferdige"]
    cell(fx, 2, 1, "Tverrklasse-statistikk", "Denne klassen mot fjorårets, på samme akse.",
         lambda x, y: lines(x, y + 30, [("Median kjedekost", 400, G1), (f"{num(fe['kjedekost']['median'])} kr i år", 700, INK), (f"{num(fj['median_kjedekost'])} kr i fjor", 400, INK), "", ("Median forsterkning, Fabrikk", 400, G1), (f"{x_(fe['forsterkning_per_rolle']['Fabrikk']['median'])} i år", 700, INK), (f"{x_(fj['median_forsterkning_fabrikk'])} i fjor", 400, INK)], 14, 25))
    cell(fx, 0, 2, "Meldinger", "Skriv til ett spill, en gruppe eller hele Klassen.",
         lambda x, y: lines(x, y + 30, [("Til Noah, Grossist", 300, INK), ("Spill 2, venter 23 t", 400, G1), "", "Gruppa di venter på", "ordren din. Rekker du", "den før KI overtar?"], 15, 26))
    cell(fx, 1, 2, "Lærers testspill", "Spill selv mot tre KI-spillere. Teller ikke i Klassen.",
         lambda x, y: (lambda sc: axes(sc, [1], [], nowlabel="nå", size=12, ygutter=False) + plot(d, sc, ("lager", "inn"), role="Fabrikk"))(Sc(x, y + 30, W, 180, 8, 0, 18)))

    # ---------- Admin ----------
    ax = 1760
    d.add(T(ax, 150, "Admin", 22, 300))
    cell(ax, 0, 0, "Admin-område", "Driften på ett sted.",
         lambda x, y: lines(x, y + 30, [("Admin", 300, INK), "", "Lærertilganger", "Brukere og roller", "KI-kostnad"], 15, 26))
    cell(ax, 0, 1, "Brukere og roller", "Hvem er Faglærer, hvem er assistent.",
         lambda x, y: lines(x, y + 30, [("Bård", 700, INK), ("Faglærer", 400, G1), "", ("Assistent", 400, G1), "", ("Be om tilgang", 400, G1)], 15, 26))
    cell(ax, 0, 2, "KI-kostnad", "Kostnad per Klasse, per modell og per måned.",
         lambda x, y: lines(x, y + 30, [("Per Klasse", 300, INK), ("Per modell", 300, INK), ("Per måned", 300, INK), "", ("Tall fra drift, ikke", 400, G1), ("demodata her.", 400, G1)], 15, 26))
    d.save()
