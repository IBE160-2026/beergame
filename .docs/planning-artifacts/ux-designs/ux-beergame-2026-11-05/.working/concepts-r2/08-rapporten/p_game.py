"""05-spill, 06-spilldynamikk og 10-pedagogikk."""
from rlib import *

# Felles byggekloss: Saras hovedgraf på telefonen


def game_chart(d, x, y, w, h, week, vmin, vmax, ticks, size=13):
    """Hovedgrafen: netto lager, min ordre, levering. Høyre kant er nå."""
    c = Chart(d, x, y, w, h, 1, week, vmin, vmax)
    c.grid(ticks, size=size)
    c.step(SARA["levering"], 1, week, SAGE, 1.75)
    c.step(SARA["ordre"], 1, week - 1, FOREST, 1.75)
    c.poly(NETTO, 1, week, OCHRE, 2.5)
    return c


def phone_top(d, week, role="Grossist", spill="spill 17", kost=None):
    d.t(20, 48, f"Uke {week}", 24, "s", INK, 500)
    d.t(370, 42, f"{role}, {spill}", 13, "f", INK2, 400, "end")
    if kost is not None:
        d.t(370, 60, f"Totalkostnad {nb(kost)} kr", 13, "f", INK2, 400, "end")
    if role == "Grossist":
        d.t(20, 84, f"Lager {v(SARA['lager'], week)}, restordre {v(SARA['restordre'], week)}", 17, "s", INK2)


def phone_key(d, y, extra=None):
    d.key(20, y, [("thick", OCHRE, "Lager / restordre"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering")], gap=12)
    d.ring(24, y + 20)
    d.t(33, y + 24, "Punktet kommentaren gjelder", 13, "f", INK2)
    d.t(370, y + 24, "Demodata", 13, "f", INK3, 400, "end")


def uke11_chart(d, typed=None, confirmed=False, notes=True):
    """Telefonens hovedgraf i Uke 11, y 112 til 500."""
    wk = 11
    c = game_chart(d, 44, 118, 312, 372, wk, -17, 30, [-10, 0, 10, 20])
    c.now(wk)
    c.weeks([1, 5, 9])
    # Direkte etiketter
    d.t(c.X(1) + 4, c.Y(12) - 7, "Lager 12", 13, "f", INK, 500)
    d.t(c.X(1) + 4, c.Y(4) + 17, "Ordre og levering 4", 13, "f", INK2)
    # Restordre: to punkter, én kommentar
    x9, y9 = c.P(9, v(NETTO, 9))
    x11, y11 = c.P(11, v(NETTO, 11))
    d.path(f"M{x9:.1f} {y9:.1f}V{y11:.1f}", stroke=INK2, sw=0.75)
    d.path(f"M{x11:.1f} {y11:.1f}H{c.X(6.1):.1f}", stroke=INK2, sw=0.75)
    d.ring(x9, y9)
    d.ring(x11, y11)
    rest9, rest11 = v(SARA["restordre"], 9), v(SARA["restordre"], 11)
    d.para(c.X(6.1) - 7, y11 - 18, 150, f"Restordre vokste fra **{rest9}** i Uke 9 til **{rest11}** nå.", 14, "s", INK, 18, anchor="end")
    # Ordre og på vei
    x10, y10 = c.P(10, v(SARA["ordre"], 10))
    paa = v(SARA["paa_vei"], 11)
    if typed is None:
        d.note(x10, y10, x10, c.Y(20), f"Ordre **{v(SARA['ordre'], 10)}** i Uke 10. **{paa}** enheter er på vei.", 250, side="l")
    else:
        pos = v(POSISJON, 11)
        xt, yt = c.P(11, typed)
        if confirmed:
            d.path(f"M{x10:.1f} {y10:.1f}V{yt:.1f}H{xt:.1f}", stroke=FOREST, sw=1.75)
            d.note(xt, yt, c.X(9.6), yt - 6, f"Ordre **{typed}** er sendt. Posisjonen er **{pos + typed}**.", 240, side="l", route="hv")
        else:
            d.path(f"M{x10:.1f} {y10:.1f}L{xt:.1f} {yt:.1f}", stroke=FOREST, sw=1.75, dash="4 4")
            d.note(x10, y10, x10, c.Y(18.5), f"Ordre **{v(SARA['ordre'], 10)}** i Uke 10. **{paa}** enheter er på vei.", 250, side="l")
            d.note(xt, yt, c.X(9.6), yt - 6, f"Du har tastet **{typed}**. Posisjonen blir **{pos + typed}**.", 240, side="l", route="hv")
    return c


def input_area(d, typed, y=680):
    """Ordre-input. Det eneste spilleren gjør."""
    d.t(20, y, "Din ordre for Uke 11", 14, "f", INK, 500)
    d.rect(20, y + 12, 130, 66, fill=WASH, rx=4)
    if typed is not None:
        d.t(85, y + 60, str(typed), 40, "f", INK, 500, "middle", prop=True)
    else:
        d.t(85, y + 52, "Antall", 15, "f", INK2, 400, "middle")
    if typed is not None:
        d.button(162, y + 12, 208, 66, f"Bekreft ordre {typed}", True, 17)
    else:
        d.rect(162, y + 12, 208, 66, fill=WASH, rx=4)
        d.t(266, y + 51, "Bekreft ordre", 17, "f", INK2, 500, "middle")
    d.para(20, y + 104, 350, "Kan ikke endres etter bekreftelse. Levering er ikke garantert.", 13, "f", INK2, 18)


def regnskap_row(d, y=586, week=11):
    d.line(20, y - 26, 370, y - 26, GRID, 1)
    cols = [(20, "Inn. ordre", v(SARA["innkommende_ordre"], week)), (104, "Levering", v(SARA["levering"], week)), (178, "Sendt", 4), (236, "På vei", v(SARA["paa_vei"], week))]
    for x, lab, val in cols:
        d.t(x, y - 5, lab, 13, "f", INK2)
        d.t(x, y + 20, str(val), 19, "f", INK, 500)
    d.t(370, y + 18, "Alt", 14, "f", INK, 500, "end")
    d.chevron(378, y + 13, 4, INK)
    d.line(20, y + 36, 370, y + 36, GRID, 1)


# 05 Hovedskjermen

def page_05():
    d = Doc("spill", 1600, 1000, "Rapport: spillskjermen i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn, det åpnede regnskapspanelet og laptopvisningen. "
            "Kommentarene i grafen er festet til punktene de gjelder og er bare regnskap fra egne tall.")
    # Telefon
    d.phone(40, 40)
    phone_top(d, 11, kost=v(SARA["kost_sum"], 11))
    uke11_chart(d, typed=24)
    d.key(20, 526, [("thick", OCHRE, "Lager / restordre"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering")], gap=12)
    regnskap_row(d)
    input_area(d, 24, 656)
    d.end()

    # Panel
    d.phone(452, 40)
    panel(d)
    d.end()

    # Laptop
    d.laptop(868, 40, 692, 844)
    laptop(d)
    d.end()

    d.para(40, 918, 390, "Telefonen: én graf, tre kommentarer. Hver kommentar er festet til punktet den regner på, og sier aldri hva Sara bør gjøre.", 16, "s", INK, 23)
    d.para(452, 918, 390, "Etter ett trykk: hele regnskapet. Her kan Sara kontrollere at gapet mellom inn og ut er det samme som endringen i hovedgrafen.", 16, "s", INK, 23)
    d.para(868, 918, 692, "På laptop står de to grafene over hverandre på samme tidsakse, med tallene og ordren ved siden av. Høyre kant er alltid nå. Aksen sier aldri noe om hvor langt spillet er kommet eller hvor det ender.", 16, "s", INK, 23)
    return d


def panel(d):
    wk = 11
    d.t(20, 48, "Regnskapet, Uke 11", 21, "s", INK, 500)
    # Lukk: tegnet kryss
    d.path("M358 36L370 48M370 36L358 48", stroke=INK, sw=1.4)
    rows = [("Lager", v(SARA["lager"], wk)), ("Restordre", v(SARA["restordre"], wk)),
            ("Innkommende ordre", v(SARA["innkommende_ordre"], wk)), ("Levering", v(SARA["levering"], wk)),
            ("Sendt", 4), ("På vei", v(SARA["paa_vei"], wk)), ("Neste levering", 4)]
    y = 82
    for lab, val in rows:
        d.t(20, y, lab, 14, "f", INK2)
        d.t(370, y, str(val), 14, "f", INK, 500, "end")
        y += 24
    d.t(20, y, "Totalkostnad", 14, "f", INK2)
    d.t(370, y, f"{nb(v(SARA['kost_sum'], wk))} kr", 14, "f", INK, 500, "end")
    y += 26
    # Regnestykket
    d.rect(20, y - 4, 350, 66, fill=WASH, rx=3)
    d.t(32, y + 19, f"Posisjon = {v(SARA['lager'], wk)} − {v(SARA['restordre'], wk)} + {v(SARA['paa_vei'], wk)} = **{v(POSISJON, wk)}**", 16, "f", INK)
    d.t(32, y + 45, f"Med ordre 24: {v(POSISJON, wk)} + 24 = **{v(POSISJON, wk) + 24}**", 16, "f", INK)
    y += 90
    # Inn og ut
    d.t(20, y, "Inn og ut, uke for uke", 16, "s", INK, 500)
    c = Chart(d, 44, y + 12, 312, 140, 1, wk, 0, 14)
    c.grid([0, 4, 8, 12])
    c.gap(SARA["innkommende_ordre"], SARA["levering"], 1, wk)
    c.step(SARA["innkommende_ordre"], 1, wk, INK, 1.75)
    c.step(SARA["levering"], 1, wk, SAGE, 1.75)
    c.now(wk)
    c.weeks([1, 5, 9])
    xk, yk = c.P(wk, v(SARA["innkommende_ordre"], wk))
    d.note(xk, yk, c.X(7), y + 16, f"Denne uka: **{v(SARA['levering'], wk)}** inn, **{v(SARA['innkommende_ordre'], wk)}** bestilt fra deg. Restordre øker med **{v(SARA['innkommende_ordre'], wk) - v(SARA['levering'], wk)}**.", 160, 13, "l", route="vh", lh=17)
    d.key(20, y + 196, [("line", INK, "Inn. ordre"), ("line", SAGE, "Levering"), ("wash", OCHRE_W, "Gapet")], gap=10)
    y += 230
    # Ordrehistorikk
    d.t(20, y, "Mine ordrer", 16, "s", INK, 500)
    bx, bw = 20, 30
    for k in range(1, wk):
        val = v(SARA["ordre"], k)
        xx = bx + (k - 1) * (bw + 3.5)
        d.rect(xx, y + 44 - val * 3, bw, val * 3, fill=FOREST, rx=1)
        d.t(xx + bw / 2, y + 62, str(k), 13, "f", INK3, 400, "middle")
        d.t(xx + bw / 2, y + 40 - val * 3, str(val), 13, "f", INK, 500, "middle")
    d.para(20, y + 88, 350, "En ordre kommer fram etter om lag 4 uker, hvis leverandøren har varene.", 13, "f", INK2, 18)


def laptop(d):
    wk = 11
    d.t(28, 44, "Uke 11", 26, "s", INK, 500)
    d.t(120, 44, "Grossist, spill 17", 14, "f", INK2)
    d.t(664, 44, f"Totalkostnad {nb(v(SARA['kost_sum'], wk))} kr", 14, "f", INK2, 400, "end")
    d.line(28, 60, 664, 60, GRID, 1)
    # Graf 1
    c = game_chart(d, 62, 86, 390, 368, wk, -17, 30, [-10, 0, 10, 20])
    c.now(wk, "nå")
    x10, y10 = c.P(10, 8)
    xt, yt = c.P(11, 24)
    d.path(f"M{x10:.1f} {y10:.1f}L{xt:.1f} {yt:.1f}", stroke=FOREST, sw=1.75, dash="4 4")
    d.t(c.X(1) + 4, c.Y(12) - 7, "Lager 12", 13, "f", INK, 500)
    d.t(c.X(1) + 4, c.Y(4) + 17, "Min ordre og levering 4", 13, "f", INK2)
    x9, y9 = c.P(9, v(NETTO, 9))
    x11, y11 = c.P(11, v(NETTO, 11))
    d.path(f"M{x9:.1f} {y9:.1f}V{y11:.1f}", stroke=INK2, sw=0.75)
    d.path(f"M{x11:.1f} {y11:.1f}H{c.X(6.6):.1f}", stroke=INK2, sw=0.75)
    d.ring(x9, y9)
    d.ring(x11, y11)
    d.para(c.X(6.6) - 7, y11 - 18, 200, f"Restordre vokste fra **{v(SARA['restordre'], 9)}** i Uke 9 til **{v(SARA['restordre'], 11)}** nå.", 14, "s", INK, 18, anchor="end")
    d.note(x10, y10, x10, c.Y(19), f"Ordre **8** i Uke 10. **{v(SARA['paa_vei'], 11)}** enheter er på vei.", 300, side="l")
    d.note(xt, yt, c.X(9.6), yt - 6, f"Du har tastet **24**. Posisjonen blir **{v(POSISJON, 11) + 24}**.", 300, side="l", route="hv")
    # Graf 2 på samme tidsakse
    y2 = 500
    d.t(62, y2 - 4, "Inn og ut på samme tidsakse", 15, "s", INK, 500)
    c2 = Chart(d, 62, y2 + 8, 390, 158, 1, wk, 0, 14)
    c2.grid([0, 4, 8, 12])
    c2.gap(SARA["innkommende_ordre"], SARA["levering"], 1, wk)
    c2.step(SARA["innkommende_ordre"], 1, wk, INK, 1.75)
    c2.step(SARA["levering"], 1, wk, SAGE, 1.75)
    c2.now(wk)
    c2.weeks([1, 5, 9])
    xk, yk = c2.P(wk, v(SARA["innkommende_ordre"], wk))
    d.note(xk, yk, c2.X(6.4), y2 + 18, f"Gapet er endringen i grafen over: **{v(SARA['levering'], wk)}** inn, **{v(SARA['innkommende_ordre'], wk)}** bestilt, **{v(SARA['innkommende_ordre'], wk) - v(SARA['levering'], wk)}** mer i restordre.", 190, 14, "l", route="vh")
    # Nøkkel
    d.key(28, 714, [("thick", OCHRE, "Lager / restordre"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering"), ("line", INK, "Inn. ordre")], gap=14)
    d.key(28, 738, [("wash", OCHRE_W, "Gapet mellom inn og ut"), ("ring", INK, "Punkt kommentaren gjelder")], gap=14)
    d.t(452, 772, "Demodata", 13, "f", INK3, 400, "end")
    d.t(28, 772, "Vis som tabell", 14, "f", INK, 500)
    d.line(28, 776, 28 + tw("Vis som tabell", 14, "f"), 776, INK, 1)
    # Høyre spalte
    sx = 484
    rows = [("Lager", v(SARA["lager"], wk)), ("Restordre", v(SARA["restordre"], wk)), ("Innkommende ordre", v(SARA["innkommende_ordre"], wk)),
            ("Levering", v(SARA["levering"], wk)), ("Sendt", 4), ("På vei", v(SARA["paa_vei"], wk)), ("Neste levering", 4)]
    y = 94
    for lab, val in rows:
        d.t(sx, y, lab, 14, "f", INK2)
        d.t(664, y, str(val), 14, "f", INK, 500, "end")
        y += 25
    d.line(sx, y - 8, 664, y - 8, GRID, 1)
    y += 16
    d.t(sx, y, f"Posisjon = {v(SARA['lager'], wk)} − {v(SARA['restordre'], wk)} + {v(SARA['paa_vei'], wk)}", 14, "f", INK2)
    d.t(664, y, str(v(POSISJON, wk)), 14, "f", INK, 600, "end")
    y += 25
    d.t(sx, y, "Med ordre 24", 14, "f", INK2)
    d.t(664, y, str(v(POSISJON, wk) + 24), 14, "f", INK, 600, "end")
    y += 50
    d.t(sx, y, "Mine ordrer, uke 1 til 10", 14, "f", INK2)
    y += 22
    d.t(sx, y, ", ".join(str(a) for a in SARA["ordre"][:10]), 14, "f", INK)
    y += 62
    d.t(sx, y, "Venter på", 14, "f", INK2)
    y += 24
    for line in ("Ida, Detaljist: har bestilt", "Mikkel, Distributør: har bestilt", "Jonas, Fabrikk: 3 min", "Deg"):
        d.t(sx, y, line, 13, "f", INK)
        y += 21
    # Ordre
    d.t(sx, 642, "Din ordre for Uke 11", 14, "f", INK, 500)
    d.rect(sx, 654, 180, 62, fill=WASH, rx=4)
    d.t(sx + 90, 700, "24", 38, "f", INK, 500, "middle", prop=True)
    d.button(sx, 724, 180, 52, "Bekreft ordre 24", True, 15)
    d.para(sx, 800, 180, "Kan ikke endres etter bekreftelse.", 13, "f", INK2, 18)


# 06 Spilldynamikk

def page_06():
    d = Doc("dynamikk", 2100, 1200, "Rapport: spilldynamikk",
            "Seks telefonruter gjennom en Uke, fra uka åpner til spillet slutter, med kommentarer som regner på egne tall.")
    sc, pw, gap, x0, y0 = 0.8, 312, 32, 38, 44
    xs = [x0 + i * (pw + gap) for i in range(6)]

    # A Uka åpner
    d.phone(xs[0], y0, scale=sc)
    phone_top(d, 11, kost=v(SARA["kost_sum"], 11))
    uke11_chart(d, typed=None)
    d.key(20, 526, [("thick", OCHRE, "Lager / restordre"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering")], gap=12)
    regnskap_row(d)
    input_area(d, None, 656)
    d.end()

    # B Beslutningen
    d.phone(xs[1], y0, scale=sc)
    phone_top(d, 11, kost=v(SARA["kost_sum"], 11))
    uke11_chart(d, typed=24)
    d.key(20, 526, [("thick", OCHRE, "Lager / restordre"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering")], gap=12)
    regnskap_row(d)
    input_area(d, 24, 656)
    d.end()

    # C Bekreftet, venter
    d.phone(xs[2], y0, scale=sc)
    phone_top(d, 11, kost=v(SARA["kost_sum"], 11))
    uke11_chart(d, typed=24, confirmed=True)
    d.key(20, 526, [("thick", OCHRE, "Lager / restordre"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering")], gap=12)
    d.line(20, 556, 370, 556, GRID, 1)
    d.t(20, 590, "Uka går videre når alle har bestilt.", 18, "s", INK, 500)
    yy = 626
    for name, role, state in [("Ida", "Detaljist", "har bestilt"), ("Mikkel", "Distributør", "har bestilt"), ("Du", "Grossist", "har bestilt"), ("Jonas", "Fabrikk", "venter, 3 min")]:
        d.t(20, yy, f"{name}, {role}", 15, "f", INK, 500 if "venter" in state else 400)
        d.t(370, yy, state, 15, "f", INK if "venter" in state else INK2, 500 if "venter" in state else 400, "end")
        if "venter" in state:
            d.circle(10, yy - 5, 3, fill=INK)
        yy += 32
    d.end()

    # D Uka går videre
    d.phone(xs[3], y0, scale=sc)
    wk = 12
    phone_top(d, 12, kost=v(SARA["kost_sum"], 12))
    c = Chart(d, 44, 118, 312, 372, 1, wk, -26, 30)
    c.grid([-20, -10, 0, 10, 20])
    c.step(SARA["levering"], 1, wk, SAGE, 1.75)
    c.step(SARA["ordre"], 1, wk - 1, FOREST, 1.75)
    c.poly(NETTO, 1, wk - 1, OCHRE, 2.5)
    c.poly(NETTO, wk - 1, wk, OCHRE, 3.5)
    c.now(wk)
    c.weeks([1, 5, 9])
    x12, y12 = c.P(12, v(NETTO, 12))
    d.path(f"M{x12:.1f} {y12:.1f}H{c.X(6.6):.1f}", stroke=INK2, sw=0.75)
    d.ring(x12, y12)
    d.para(c.X(6.6) - 7, y12 - 18, 170, f"Ny uke: **{v(SARA['levering'], 12)}** inn, **{v(SARA['innkommende_ordre'], 12)}** bestilt fra deg. Restordre **{v(SARA['restordre'], 12)}**.", 14, "s", INK, 18, anchor="end")
    xt, yt = c.P(11, v(SARA["ordre"], 11))
    d.note(xt, yt, xt, c.Y(29), f"Din **24** er sendt. **{v(SARA['paa_vei'], 12)}** enheter er nå på vei.", 200, side="l")
    d.key(20, 526, [("thick", OCHRE, "Lager / restordre"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering")], gap=12)
    d.line(20, 556, 370, 556, GRID, 1)
    d.t(20, 594, "Uke 12 regnes ut", 18, "s", INK, 500)
    d.rect(20, 612, 350, 3, fill=WASH)
    d.rect(20, 612, 210, 3, fill=INK)
    d.para(20, 644, 350, "Tar aldri mer enn 2 sekunder.", 14, "f", INK2, 20)
    d.t(20, 722, "Hopp over", 16, "f", INK, 500)
    d.line(20, 727, 20 + tw("Hopp over", 16, "f"), 727, INK, 1)
    d.end()

    # E Jonas er borte
    d.phone(xs[4], y0, scale=sc)
    F = S17["Fabrikk"]
    NF = [a - b for a, b in zip(F["lager"], F["restordre"])]
    wk = 14
    d.t(20, 48, "Uke 14", 24, "s", INK, 500)
    d.t(370, 42, "Fabrikk, spill 17", 13, "f", INK2, 400, "end")
    d.t(370, 60, "Jonas", 13, "f", INK2, 400, "end")
    c = Chart(d, 44, 118, 312, 300, 1, wk, -6, 22)
    d.rect(c.X(11), c.y, c.X(14) - c.X(11), c.h, fill=WASH)
    c.grid([0, 10, 20])
    c.step(F["levering"], 1, wk, SAGE, 1.75)
    c.step(F["ordre"], 1, wk, FOREST, 1.75)
    c.poly(NF, 1, wk, OCHRE, 2.5)
    c.now(wk)
    c.weeks([1, 5, 9])
    d.t(c.X(11) + 5, c.y + 18, "KI-spiller", 13, "f", INK, 600)
    xo, yo = c.P(13, v(F["ordre"], 13))
    orders = ", ".join(str(v(F["ordre"], k)) for k in (12, 13, 14))
    d.note(xo, yo, c.X(10.4), c.Y(4.6) + 56, f"KI-spilleren bestilte **{orders}** i Uke 12, 13 og 14.", 170, side="l", route="vh", ring=True)
    d.t(c.X(1) + 4, c.Y(12) - 7, "Lager 12", 13, "f", INK, 500)
    d.line(20, 470, 370, 470, GRID, 1)
    d.t(20, 506, "KI-spiller holder setet ditt.", 20, "s", INK, 500)
    d.para(20, 536, 350, "Setet sto 24 timer uten ordre, så KI overtok. Gruppa kunne gå videre. Alle ser at Fabrikk nå er merket KI-spiller.", 15, "s", INK, 22)
    d.para(20, 628, 350, "Ordrene KI-spilleren har lagt, kan ikke endres. Du tar over fra neste Uke.", 15, "s", INK, 22)
    d.button(20, 714, 350, 62, "Ta tilbake setet", True, 17)
    d.end()

    # F Spillet slutter
    d.phone(xs[5], y0, scale=sc)
    d.t(20, 48, "Spillet er slutt", 24, "s", INK, 500)
    d.t(370, 42, "Spill 17", 13, "f", INK2, 400, "end")
    d.para(20, 92, 350, "Kjedens totalkostnad", 15, "f", INK2)
    d.t(20, 142, f"{nb(FX['spill17']['kjedekost'])} kr", 44, "f", INK, 500, prop=True)
    d.line(20, 172, 370, 172, GRID, 1)
    d.t(20, 206, "Per Rolle, for hele kjeden", 15, "f", INK2)
    y = 240
    mx = max(FX["spill17"]["kost_per_rolle"].values())
    for r in ROLES:
        val = FX["spill17"]["kost_per_rolle"][r]
        d.t(20, y, r + (" (du)" if r == "Grossist" else ""), 15, "f", INK, 500 if r == "Grossist" else 400)
        d.t(370, y, f"{nb(val)} kr", 15, "f", INK, 500 if r == "Grossist" else 400, "end")
        d.rect(20, y + 9, 350 * val / mx, 7, fill=OCHRE if r == "Grossist" else SAGE, rx=1)
        y += 56
    d.para(20, y + 18, 325, "Målet var lavest kostnad for hele kjeden, ikke for ett ledd. Restordre kostet 1,00 og lager 0,50 per enhet per uke.", 15, "s", INK, 22)
    d.para(20, y + 110, 325, "I Debriefen får du se hva som skjedde, og hvorfor. Først ber vi deg skrive din egen Forklaring.", 15, "s", INK, 22)
    d.button(20, 714, 350, 62, "Gå til Debrief", True, 17)
    d.t(20, 804, "Demodata", 13, "f", INK3)
    d.end()

    # Notater
    notes = [
        ("Uka åpner", "Grafen har fått én uke til. To kommentarer regner på det nye. De er skrevet fra Saras egne tall og sier ikke hva hen bør gjøre."),
        ("Beslutningen", "Sara taster 24. Punktet tegnes i grafen med sann skala, og kommentaren regner ut at posisjonen blir 27. Regnestykket er vist, fasiten er det ikke."),
        ("Bekreftet", "Ordren står fast, og streken blir hel. Under grafen står hvem uka venter på, med Rolle, navn og hvor lenge."),
        ("Uka går videre", "Det nye linjestykket tegnes, og den nye kommentaren settes på det. Aldri over 2 sekunder, og det kan hoppes over."),
        ("Jonas er borte", "Etter 24 t holder en KI-spiller setet. Ukene er merket i grafen med ord og band. Jonas kan ta setet tilbake."),
        ("Spillet slutter", "Kjedens totalkostnad kommer først, så Rollene. Ingen navn, ingen rangering. Første side i rapporten er nå skrevet."),
    ]
    for i, (title, body) in enumerate(notes):
        d.t(xs[i], 756, title, 21, "s", INK, 500)
        d.para(xs[i], 786, pw - 4, body, 17, "s", INK2, 24)
    # Under
    d.line(38, 950, 2062, 950, GRID, 1)
    d.t(38, 1000, "Hva Sara lærer av å se grafen uke for uke", 30, "s", INK, 500)
    body = ("Hen ser at det hen gjør, ikke viser seg i grafen med én gang: ordren står der i ukevis før noe skjer med levering. "
            "Hen ser at gapet mellom inn og ut er nøyaktig det restordre vokser med, så regnskapet stemmer hver uke. "
            "Kommentarene gir hen ordene for det hen ser, uten å gi hen svaret. "
            "Svingningene får hen leve med selv, slik at spørsmålet etterpå blir hvorfor det skjedde, ikke om hen hadde rett.")
    d.para(38, 1044, 1700, body, 22, "s", INK, 33)
    return d


# 10 Pedagogikk

def page_10():
    d = Doc("pedagogikk", 2000, 1400, "Rapport: grafgrammatikk og pedagogikk",
            "De samme grafene for Sara ved Uke 5, 11, 18 og 29 på felles tidsakse, med kommentarer festet til punktene, "
            "hjelpegrad, anatomien til regel-kommentaren og sammenligning med simulert referanse.", bg=PAPER)
    d.t(48, 62, "Grafen forteller. Kommentaren regner.", 40, "s", INK, 500)
    d.para(48, 98, 1880, "Fire øyeblikk i samme spill, med samme skala. Hver rad slutter ved nå. Under spillet er kommentarene bare regnskap fra Saras egne tall. Årsaken kommer i Debriefen.", 19, "s", INK2, 27)
    px, pw = 92, 1296
    ry, rh, sh, sp = 132, 144, 42, 218

    def Xw(w):
        return px + (w - 1) / 28 * pw

    info = {
        5: ("P1 Lager er en opphopning", "Inn og ut er like, så lageret er flatt. Ingen flate mellom linjene, ingen endring.", "Til neste ordre: 4 inn og 4 ut holder lageret på 12."),
        11: ("P1 Opphopning, P3 På vei", "Flaten under har åpnet seg: 4 inn, 8 bestilt. Det er nøyaktig det restordre vokser med. Tasten på 24 står i grafen, levering står fortsatt på 4.", "Til neste ordre: det som er på vei, er ennå ikke synlig i levering. Tell det."),
        18: ("P2 Forsinkelse, P8 Restordre koster dobbelt", "24 bestilt ble 17 levert fire uker senere. Hver restordre koster 1,00 per uke, mot 0,50 for lager.", "Til neste ordre: det du ser nå, kommer av det du gjorde før."),
        29: ("P1 Opphopning, P2 Forsinkelse", "Det som var bestilt, er kommet. Fra restordre 40 til lager 30 på sju uker. Ordren har vært lav lenge, og lageret stiger likevel.", "Til neste ordre: en lav ordre nå viser seg om fire uker, ikke i dag."),
    }
    for i, wk in enumerate((5, 11, 18, 29)):
        y = ry + i * sp
        c = Chart(d, px, y, Xw(wk) - px, rh, 1, wk, -42, 34)
        c.grid([-30, 0, 30], x2=px + pw)
        c.step(SARA["levering"], 1, wk, SAGE, 1.5)
        c.step(SARA["ordre"], 1, wk, FOREST, 1.75)
        c.poly(NETTO, 1, wk, OCHRE, 2.5)
        # Strimmel for inn og ut, samme tidsakse
        c2 = Chart(d, px, y + rh + 6, c.w, sh, 1, wk, 0, 32)
        c2.gap(SARA["innkommende_ordre"], SARA["levering"], 1, wk)
        c2.step(SARA["innkommende_ordre"], 1, wk, INK, 1.25)
        c2.step(SARA["levering"], 1, wk, SAGE, 1.25)
        d.line(px, c2.Y(0), px + pw, c2.Y(0), GRID, 0.75)
        d.line(c.X(wk), y, c.X(wk), c2.Y(0) + 4, INK, 1)
        # Innsikt
        ix = 1420
        d.t(ix, y + 16, f"Uke {wk}", 25, "s", INK, 500)
        d.t(ix + 96, y + 15, info[wk][0], 14, "f", INK2, 600)
        ny = d.para(ix, y + 46, 530, info[wk][1], 16, "s", INK, 23)
        d.para(ix, ny + 2, 530, info[wk][2], 16, "s", INK2, 23)
        # Kommentarer
        if wk == 5:
            xx, yy = c.P(5, v(NETTO, 5))
            d.note(xx, yy, xx + 40, y + 12, f"Lager **{v(SARA['lager'], 5)}**, ordre **{v(SARA['ordre'], 5)}**, levering **{v(SARA['levering'], 5)}**. Samme tall alle fem ukene.", 420, route="vh")
        if wk == 11:
            x9, y9 = c.P(9, v(NETTO, 9))
            x11, y11 = c.P(11, v(NETTO, 11))
            d.path(f"M{x9:.1f} {y9:.1f}V{y11:.1f}H{x11:.1f}", stroke=INK2, sw=0.75)
            d.ring(x9, y9)
            d.note(x11, y11, x11 + 40, y11 - 9, f"Restordre vokste fra **{v(SARA['restordre'], 9)}** i Uke 9 til **{v(SARA['restordre'], 11)}** nå.", 420, route="hv")
            xo, yo = c.P(11, v(SARA["ordre"], 11))
            d.note(xo, yo, xo + 40, yo - 9, f"Sara taster **24**. Da er **{v(SARA['paa_vei'], 11)}** enheter på vei.", 420, route="hv")
        if wk == 18:
            x11, y11 = c.P(11, v(SARA["ordre"], 11))
            x15, y15 = c.P(15, v(SARA["levering"], 15))
            ytop = y + 2
            d.bracket(x11, y11, x15, y15, ytop)
            d.t((x11 + x15) / 2, ytop + 15, "4 uker", 13, "f", INK2, 500, "middle", halo=PAPER)
            xr = c.X(18) + 40
            d.path(f"M{x15:.1f} {ytop:.1f}H{xr:.1f}", stroke=INK2, sw=0.75)
            d.para(xr + 7, ytop + 5, 420, "**24** bestilt i Uke 11, **17** levert i Uke 15.", 14, "s", INK, 18)
            xn, yn = c.P(18, v(NETTO, 18))
            d.note(xn, yn, xn + 40, yn - 9, f"Restordre **{v(SARA['restordre'], 18)}**. **{v(SARA['paa_vei'], 18)}** enheter er på vei.", 420, route="hv")
        if wk == 29:
            x22, y22 = c.P(22, v(NETTO, 22))
            d.note(x22, y22, x22 - 30, y22 - 9, f"Restordre **{v(SARA['restordre'], 22)}** i Uke 22.", 240, side="l", route="hv")
            xn, yn = c.P(29, v(NETTO, 29))
            d.ring(xn, yn)
            d.para(xn - 8, c.Y(-6), 165, f"Lager **{v(SARA['lager'], 29)}** nå. Ordre **{v(SARA['ordre'], 29)}**. **{v(SARA['paa_vei'], 29)}** enheter på vei.", 14, "s", INK, 18, anchor="end", halo=PAPER)
        # Akse
        for t in (1, 5, 10, 15, 20, 25):
            if t <= wk - 2:
                d.t(c.X(t), y + rh + sh + 22, f"Uke {t}" if t == 1 else str(t), 13, "f", INK3, 400, "start" if t == 1 else "middle")
        d.t(c.X(wk), y + rh + sh + 22, "nå", 13, "f", INK, 600, "middle")
    ky = ry + 4 * sp + 10
    d.key(px, ky, [("thick", OCHRE, "Lager over 0, restordre under 0"), ("line", FOREST, "Min ordre"), ("line", SAGE, "Levering"),
                   ("line", INK, "Innkommende ordre (strimmelen)"), ("wash", OCHRE_W, "Gapet = endring i netto lager"),
                   ("ring", INK, "Punktet kommentaren gjelder")], gap=20)
    d.t(1952, ky, "Demodata. Felles skala i alle rader.", 13, "f", INK3, 400, "end")

    by = ky + 30
    d.line(48, by - 10, 1952, by - 10, GRID, 1)
    # 1 Dresskoden
    ax = 48
    d.t(ax, by + 24, "Dresskoden", 25, "s", INK, 500)
    a = Chart(d, ax + 20, by + 44, 380, 150, 1, 11, -17, 14)
    a.grid([-10, 0, 10], labels=True)
    a.step(SARA["levering"], 1, 11, SAGE, 1.5)
    a.poly(NETTO, 1, 11, OCHRE, 2.5)
    x11, y11 = a.P(11, v(NETTO, 11))
    d.note(x11, y11, a.X(6.4), y11 - 9, "Restordre **13** nå.", 160, side="l", route="hv")
    a.weeks([1, 5, 9])
    d.key(ax + 20, by + 234, [("thick", OCHRE, "Lager / restordre"), ("line", SAGE, "Levering"), ("ring", INK, "Punktet")], gap=14)
    tx = ax + 430
    yy = by + 58
    for head, body in [("Ringen", "på nøyaktig det punktet teksten regner på."), ("Regelen", "tynn og rett, fra ringen til teksten. Aldri en løs bildetekst."),
                       ("Teksten", "i serif, høyst tre per graf. Tallene i fet."), ("Nøkkelen", "alltid nederst. Etiketten direkte på linja der det er plass.")]:
        d.t(tx, yy, head, 14, "f", INK, 600)
        yy = d.para(tx, yy + 19, 262, body, 14, "f", INK2, 19) + 6

    # 2 Hjelpegrad
    hx = 800
    d.t(hx, by + 24, "Samme uke, to hjelpegrader", 25, "s", INK, 500)
    hw = 186
    for j, (lab, on) in enumerate([("Klassespill", False), ("Replay, etter Debrief", True)]):
        xx0 = hx + 26 + j * (hw + 104)
        d.t(hx + j * (hw + 104), by + 52, lab, 15, "f", INK, 600)
        c3 = Chart(d, xx0, by + 64, hw, 150, 1, 11, -17, 30)
        c3.grid([-10, 0, 10, 20])
        c3.step(SARA["levering"], 1, 11, SAGE, 1.5)
        c3.step(SARA["ordre"], 1, 10, FOREST, 1.75)
        c3.poly(NETTO, 1, 11, OCHRE, 2.5)
        c3.now(11)
        xr = c3.X(11)
        if on:
            net, pv = v(NETTO, 11), v(SARA["paa_vei"], 11)
            d.rect(xr + 5, c3.Y(net + pv), 7, c3.Y(net) - c3.Y(net + pv), fill=FOREST)
            d.t(xr + 16, c3.Y(net + pv) + 5, f"Posisjon {net + pv}", 13, "f", INK, 600)
            d.t(xr + 16, (c3.Y(net + pv) + c3.Y(net)) / 2 + 8, f"På vei {pv}", 13, "f", INK2)
        else:
            x10, y10 = c3.P(10, v(SARA["ordre"], 10))
            d.note(x10, y10, x10, by + 72, f"**{v(SARA['paa_vei'], 11)}** enheter er på vei.", 150, 13, "l", lh=17)
    d.para(hx, by + 256, 560, "I Klassespillet er posisjonen et regnestykke bak ett trykk, så Sara må selv gjøre koblingen (P3). Etter Debriefen tegnes på vei på samme skala som lageret, og hen bruker innsikten i Replay.", 14, "f", INK2, 19)

    # 3 Etter Debrief
    sx = 1420
    d.t(sx, by + 24, "Etter Debriefen: mot Simulert", 25, "s", INK, 500)
    c4 = Chart(d, sx + 26, by + 44, 504, 170, 1, 36, 0, 26)
    c4.grid([0, 10, 20])
    c4.step(SIMS["ordre"], 1, 36, SAGE, 2)
    c4.step(SARA["ordre"], 1, 36, OCHRE, 2)
    c4.weeks([1, 10, 20, 30, 36])
    x1, y1 = c4.P(11, v(SARA["ordre"], 11))
    d.note(x1, y1, c4.X(14), y1 - 9, f"Du: **{v(SARA['ordre'], 11)}** i Uke 11. Simulert: **{v(SIMS['ordre'], 11)}**.", 330, route="hv")
    xk, yk = c4.P(28, v(SARA["ordre"], 28))
    d.note(xk, yk, c4.X(28), by + 76, f"Du: **{v(SARA['ordre'], 28)}** i Uke 28. Simulert: **{v(SIMS['ordre'], 28)}**.", 200, 14, side="l")
    d.key(sx + 26, by + 248, [("line", OCHRE, "Din ordre"), ("line", SAGE, "Simulert: bare Grossist teller på vei")], gap=14)
    d.para(sx + 26, by + 272, 510, f"Simulert kjede {nb(SIM1['kjedekost'])} kr mot {nb(FX['spill17']['kjedekost'])} kr. Grossist {fx(SIM1['forsterkning']['Grossist'])} mot {fx(FX['spill17']['forsterkning']['Grossist'])}. P3 og P7: viser sammenhengen, ikke en fasit. Rolig tilpasning og å telle det som er på vei må til sammen.", 14, "f", INK2, 19)
    return d
