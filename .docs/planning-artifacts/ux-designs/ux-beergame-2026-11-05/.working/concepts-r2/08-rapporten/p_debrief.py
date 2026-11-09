"""07-debrief: en lang, rolig artikkel om ditt spill, lagt ut som et oppslag."""
from rlib import *

KI_TAG = "KI-generert, kan ta feil"


def tag_ki(d, x, y, anchor="start"):
    """Tydelig merke for KI-tekst. Tallene kommer alltid fra loggen."""
    d.t(x, y, KI_TAG, 13, "f", INK2, 600, anchor)


def page_07():
    d = Doc("debrief", 2100, 1200, "Rapport: Debrief som artikkel",
            "Gruppedebrief i fem steg som en lang artikkel: Forklaring, avsløring av etterspørselen som stille mellomtittel, "
            "alle fire Rollers ordre, ditt øyeblikk i Uke 11 og quiz, pluss delt skjerm. Alle tall fra loggen.", bg=PAPER)
    cost = FX["spill17"]["kost_per_rolle"]
    forst = FX["spill17"]["forsterkning"]
    fer = KL["ferdige"]["forsterkning_per_rolle"]

    # Artikkelhode
    d.t(40, 60, "Du bestilte 24 da 16 var på vei", 44, "s", INK, 500)
    d.para(40, 96, 1100, "Artikkelen om spill 17 fra ditt sete. Grossist, 36 uker. Tallene er hentet fra loggen. Teksten mellom dem er KI-generert og kan ta feil.", 18, "s", INK2, 25)
    steps = ["Forklaring", "Etterspørselen", "Alle fire Roller", "Ditt øyeblikk", "Quiz"]
    sx = 1270
    for i, s in enumerate(steps):
        w = 158
        d.t(sx + i * w, 66, s, 14, "f", INK, 500)
        d.rect(sx + i * w, 76, w - 8, 2, fill=INK)
    d.line(40, 122, 2060, 122, GRID, 1)

    # Spalte 1: Følelse, Forklaring, avsløring
    x1, w1 = 40, 400
    y = 160
    d.t(x1, y, "Slik så det ut fra ditt sete", 25, "s", INK, 500)
    y = d.para(x1, y + 30, w1, "Før du får se mer: dette er grafen du spilte med, til siste uke. Du så bare dette.", 16, "s", INK, 23)
    c = Chart(d, x1 + 26, y + 2, w1 - 26, 330, 1, 36, -44, 50)
    c.grid([-30, 0, 30])
    c.poly(NETTO, 1, 36, OCHRE, 2.5)
    c.weeks([1, 10, 20, 30, 36])
    xa, ya = c.P(22, v(NETTO, 22))
    d.note(xa, ya, c.X(20), ya - 9, f"Restordre **{v(SARA['restordre'], 22)}** i Uke 22.", 180, side="l", route="hv")
    xb, yb = c.P(29, v(NETTO, 29))
    d.note(xb, yb, xb, c.Y(48), f"Lager **{v(SARA['lager'], 29)}** i Uke 29.", 170, side="l")
    d.key(x1 + 26, y + 2 + 330 + 44, [("thick", OCHRE, "Lager / restordre"), ("ring", INK, "Punktet kommentaren gjelder")], gap=12)
    y += 412
    d.t(x1, y, "Hva tror du skjedde?", 19, "s", INK, 500)
    y = d.para(x1, y + 24, w1, "Skriv Forklaringen din først. Du kan ikke endre den etterpå.", 15, "s", INK2, 21)
    d.rect(x1, y - 8, w1, 124, fill=WASH, rx=3)
    d.para(x1 + 14, y + 16, w1 - 28, "Ida bestilte plutselig mye mer, og jeg fikk aldri nok varer. Så jeg måtte bestille stort for å ta igjen. Etterpå kom alt på en gang.", 15, "s", INK, 22)
    d.t(x1 + 14, y + 102, "Sara, lagret", 13, "f", INK2)
    y += 138
    d.lock(x1, y - 11)
    d.t(x1 + 18, y, "Etterspørselen vises når alle har lagret.", 13, "f", INK2)
    y += 34
    # Avsløringen: stille mellomtittel og én liten graf
    d.line(x1, y - 12, x1 + w1, y - 12, GRID, 1)
    d.t(x1, y + 18, "Kundene kjøpte 8", 25, "s", INK, 500)
    y = d.para(x1, y + 46, w1, "Fra Uke 5 og ut spillet. Det var hele endringen. Øvelsen heter Beer Game.", 16, "s", INK, 23)
    c = Chart(d, x1 + 26, y - 6, 240, 62, 1, 36, 0, 10)
    c.grid([0, 8], size=13)
    c.step(S17["demand"], 1, 36, INK, 2)
    c.weeks([1, 36], size=13)
    xd, yd = c.P(5, 8)
    d.note(xd, yd, c.X(36) + 14, yd - 9, "**4** til **8**, i Uke 5.", 120, 14, route="hv")

    # Spalte 2: Alle fire Roller
    x2, w2 = 480, 560
    y = 160
    d.t(x2, y, "Ordrene vokste for hvert ledd", 25, "s", INK, 500)
    y = d.para(x2, y + 30, w2, "Kundene endret seg én gang. Ordrene svingte i ukevis, og de svingte mer og senere jo lenger de kom fra kundene.", 16, "s", INK, 23)
    ch = 556
    c = Chart(d, x2 + 26, y + 2, w2 - 26, ch, 1, 36, 0, 34)
    c.grid([0, 10, 20, 30])
    c.step(S17["Detaljist"]["ordre"], 1, 36, SAGE, 1.5)
    c.step(S17["Distributør"]["ordre"], 1, 36, FOREST, 1.5)
    c.step(S17["Fabrikk"]["ordre"], 1, 36, INK, 1.75)
    c.step(S17["Grossist"]["ordre"], 1, 36, OCHRE, 2.5)
    c.weeks([1, 10, 20, 30, 36])
    xg, yg = c.P(11, 24)
    d.note(xg, yg, c.X(9), yg - 9, "Du: **24** i Uke 11.", 120, side="l", route="hv")
    dp = max(S17["Distributør"]["ordre"])
    wkp = S17["Distributør"]["ordre"].index(dp) + 1
    xp, yp = c.P(wkp, dp)
    d.note(xp, yp, c.X(10), c.Y(29), f"Distributør: **{dp}** i Uke {wkp}.", 150, side="l", route="vh")
    fp = max(S17["Fabrikk"]["ordre"])
    wkf = S17["Fabrikk"]["ordre"].index(fp) + 1
    xf, yf = c.P(wkf, fp)
    d.note(xf, yf, c.X(wkf + 3), yf - 9, f"Fabrikk: **{fp}** i Uke {wkf}, sju uker etter deg.", 250, route="hv")
    xc, yc = c.P(30, 8)
    yy = y + 2 + ch + 44
    d.key(x2 + 26, yy, [("line", SAGE, "Detaljist"), ("thick", OCHRE, "Grossist (du)"), ("line", FOREST, "Distributør"), ("line", INK, "Fabrikk")], gap=14)
    d.t(x2 + w2, yy, "Vis som tabell", 13, "f", INK, 500, "end")
    d.line(x2 + w2 - tw("Vis som tabell", 13, "f"), yy + 3, x2 + w2, yy + 3, INK, 1)
    y = yy + 44
    d.t(x2, y, "Forsterkningen, og klassen rundt deg", 19, "s", INK, 500)
    y += 8
    sc = lambda val: x2 + 96 + val / 13 * (w2 - 96 - 44)
    for r in ROLES:
        y += 28
        q = fer[r]
        d.t(x2, y + 4, r, 14, "f", INK, 600 if r == "Grossist" else 400)
        d.line(sc(q["min"]), y, sc(q["max"]), y, GRID, 2)
        d.line(sc(q["q1"]), y, sc(q["q3"]), y, SAGE, 5)
        d.circle(sc(forst[r]), y, 5.5, fill=OCHRE if r == "Grossist" else INK, stroke=PAPER, sw=2)
        d.t(x2 + w2, y + 4, fx(forst[r]), 15, "f", INK, 600, "end")
    y += 28
    d.key(x2 + 96, y, [("line", SAGE, "Midterste halvdel av 41 spill"), ("line", GRID, "Hele spennet")], gap=14)
    assert all(fer[r]["q1"] <= forst[r] <= fer[r]["q3"] for r in ROLES)
    d.para(x2, y + 32, w2, "Alle fire Rollene i spill 17 ligger i den midterste halvdelen. Nesten alle gruppene svinger likt, uten å ha snakket sammen. Da er det kjeden, ikke personene, som gir mønsteret.", 16, "s", INK, 23)

    # Spalte 3: Ditt øyeblikk
    x3, w3 = 1080, 590
    y = 160
    d.t(x3, y, "Uke 11: tre tall og én ordre", 25, "s", INK, 500)
    tag_ki(d, x3 + w3, y - 3, "end")
    y += 30
    p = v(POSISJON, 11)
    y = d.para(x3, y, w3, f"Du så lager {v(SARA['lager'], 11)}, restordre {v(SARA['restordre'], 11)} og {v(SARA['innkommende_ordre'], 11)} i innkommende ordre. Du så også at {v(SARA['paa_vei'], 11)} var på vei, så posisjonen var {p}. Du bestilte 24. Uka etter var {v(SARA['paa_vei'], 12)} på vei, og du bestilte {v(SARA['ordre'], 12)} til.", 16, "s", INK, 23)
    c = Chart(d, x3 + 26, y + 2, w3 - 26, 280, 1, 36, -44, 76)
    c.grid([-40, -20, 0, 20, 40, 60])
    c.poly(POSISJON, 1, 36, FOREST, 1.75)
    c.poly(NETTO, 1, 36, OCHRE, 2.5)
    c.weeks([1, 10, 20, 30, 36])
    x_, y_ = c.P(11, p)
    d.note(x_, y_, x_, c.Y(50), f"Posisjon **{p}** i Uke 11.", 150, side="l")
    x_, y_ = c.P(22, v(POSISJON, 22))
    d.note(x_, y_, x_, c.Y(74), f"Posisjon **{v(POSISJON, 22)}** i Uke 22, med restordre **{v(SARA['restordre'], 22)}** samtidig.", 230)
    d.key(x3 + 26, y + 2 + 280 + 44, [("thick", OCHRE, "Lager / restordre, det du så"), ("line", FOREST, "Posisjon, med det som var på vei")], gap=14)
    y += 2 + 280 + 70
    k11, k22 = v(SARA["kost_sum"], 11), v(SARA["kost_sum"], 22)
    y = d.para(x3, y, w3, f"Kostnaden din gikk fra {nb(k11)} kr i Uke 11 til {nb(k22)} kr i Uke 22. Mønsteret kalles «Stor ordre mens mye allerede er på vei». Mekanismen er forsyningslinja: det du har bestilt, finnes selv om du ikke ser det ennå.", 15, "s", INK, 21)
    y += 18
    d.t(x3, y, "Samme kjede, Grossist teller alt på vei", 19, "s", INK, 500)
    d.t(x3 + w3, y, "Simulert", 13, "f", INK, 600, "end")
    c = Chart(d, x3 + 26, y + 12, w3 - 26, 186, 1, 36, 0, 26)
    c.grid([0, 10, 20])
    c.step(SIMS["ordre"], 1, 36, SAGE, 2)
    c.step(SARA["ordre"], 1, 36, OCHRE, 2.5)
    c.weeks([1, 10, 20, 30, 36])
    x_, y_ = c.P(11, v(SARA["ordre"], 11))
    d.note(x_, y_, c.X(16), y_ - 9, f"Du: **{v(SARA['ordre'], 11)}**. Simulert: **{v(SIMS['ordre'], 11)}**.", 240, route="hv")
    d.key(x3 + 26, y + 12 + 186 + 44, [("thick", OCHRE, "Din ordre"), ("line", SAGE, "Simulert"), ("ring", INK, "Punkt kommentaren gjelder")], gap=14)
    y += 12 + 186 + 70
    y = d.para(x3, y, w3, f"Kostnad for Grossist {nb(SIM1['kost_per_rolle']['Grossist'])} kr mot dine {nb(cost['Grossist'])} kr. Kjeden {nb(SIM1['kjedekost'])} kr mot {nb(FX['spill17']['kjedekost'])} kr. Det viser sammenhengen, ikke en fasit: en regel som jaget siste ordre for hardt, ga Fabrikk høyere forsterkning (12×) enn dere fikk.", 15, "s", INK2, 21)
    y += 14
    # Hva de andre så
    d.t(x3, y, "Hva de andre så i Uke 11", 19, "s", INK, 500)
    hdr = [("Rolle", x3), ("Lager", x3 + 150), ("Restordre", x3 + 220), ("Inn. ordre", x3 + 310), ("Bestilte", x3 + 400)]
    y += 26
    for lab, xx in hdr:
        d.t(xx, y, lab, 13, "f", INK2)
    for r in ROLES:
        y += 21
        s = S17[r]
        mine = r == "Grossist"
        wt = 600 if mine else 400
        vals = [r + (" (du)" if mine else ""), v(s["lager"], 11), v(s["restordre"], 11), v(s["innkommende_ordre"], 11), v(s["ordre"], 11)]
        for (lab, xx), val in zip(hdr, vals):
            d.t(xx, y, str(val), 14, "f", INK, wt)
    d13 = S17["Distributør"]
    d.para(x3 + 468, y - 66, 122, f"Din 24 kom til Distributør i Uke 13. Deres ordre gikk fra {v(d13['ordre'], 12)} til {v(d13['ordre'], 13)}.", 14, "s", INK, 19)

    # Spalte 4: Quiz og delt skjerm
    x4, w4 = 1710, 350
    y = 160
    d.t(x4, y, "Tre spørsmål", 25, "s", INK, 500)
    y = d.para(x4, y + 30, w4, "Debrief-quiz. Den teller ikke, og du kan ta den om igjen.", 15, "s", INK2, 21)
    y += 8
    y = d.para(x4, y, w4, "Lager 0, restordre 13, 16 på vei. Hva er posisjonen?", 17, "s", INK, 24, weight=500)
    y += 16
    for lab, state in [("−13", "wrong"), ("3", "right"), ("16", None), ("29", None)]:
        h = 36
        if state == "wrong":
            d.rect(x4, y - 23, w4, h, fill=OCHRE_W, rx=3)
        elif state == "right":
            d.rect(x4, y - 23, w4, h, fill=WASH, rx=3)
        else:
            d.rect(x4, y - 23, w4, h, fill="none", stroke=GRID, rx=3)
        d.t(x4 + 12, y + 1, lab, 15, "f", INK, 500)
        if state == "wrong":
            d.t(x4 + w4 - 12, y + 1, "Du svarte dette", 13, "f", INK, 500, "end")
        if state == "right":
            d.t(x4 + w4 - 12, y + 1, "Riktig svar", 13, "f", INK, 600, "end")
        y += 42
    y = d.para(x4, y + 6, w4, "Du svarte −13, som er lager minus restordre. De 16 på vei hører også med: de er allerede bestilt, og de kommer. 0 − 13 + 16 = 3.", 15, "s", INK, 22)
    d.button(x4, y + 2, w4, 44, "Neste spørsmål", True, 15)
    y += 84

    # Delt skjerm
    d.t(x4, y, "Delt skjerm", 25, "s", INK, 500)
    y = d.para(x4, y + 28, w4, "Det gruppa ser sammen. Forklaringen din og Uke 11 vises bare på din egen skjerm.", 15, "s", INK2, 21)
    fh = 400
    d.rect(x4, y, w4, fh, fill=WHITE, stroke=FRAME, rx=4)
    d.t(x4 + 14, y + 30, "Ordrene vokste for hvert ledd", 17, "s", INK, 500)
    c = Chart(d, x4 + 14, y + 44, w4 - 28, 278, 1, 36, 0, 34)
    c.grid([0, 10, 20, 30], labels=False)
    c.step(S17["Detaljist"]["ordre"], 1, 36, SAGE, 1.25)
    c.step(S17["Distributør"]["ordre"], 1, 36, FOREST, 1.25)
    c.step(S17["Fabrikk"]["ordre"], 1, 36, INK, 1.5)
    c.step(S17["Grossist"]["ordre"], 1, 36, OCHRE, 1.5)
    d.key(x4 + 14, y + 346, [("line", SAGE, f"Detaljist {fx(forst['Detaljist'])}"), ("line", OCHRE, f"Grossist {fx(forst['Grossist'])}")], 13, 14)
    d.key(x4 + 14, y + 370, [("line", FOREST, f"Distributør {fx(forst['Distributør'])}"), ("line", INK, f"Fabrikk {fx(forst['Fabrikk'])}")], 13, 14)
    y += fh + 24
    d.t(x4, y, "Demodata. Alle tall fra loggen.", 13, "f", INK3)
    return d
