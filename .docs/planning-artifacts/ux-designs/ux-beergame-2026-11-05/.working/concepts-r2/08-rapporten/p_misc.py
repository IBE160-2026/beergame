"""01-landing, 04-student-hjem og 09-alle-sider."""
from rlib import *
from p_teacher import micro


def page_01():
    W, H = 1440, 1200
    d = Doc("landing", W, H, "Rapport: landingsside for faglærere",
            "En kommentert graf fra ett sete bærer siden. Primærhandling Be om lærertilgang, deretter lærerens oversikt.", bg=PAPER)
    d.t(64, 56, "Rapport", 26, "s", INK, 500)
    d.t(W - 64, 54, "Logg inn", 15, "f", INK, 500, "end")
    d.t(64, 150, "Øvelsen i forsyningskjeder,", 62, "s", INK, 500)
    d.t(64, 222, "fra Invitasjon til rapport", 62, "s", INK, 500)
    d.para(64, 278, 760, "Fire studenter, fire ledd, ett tall i uka. Rapport kjører hele øvelsen for klasser på rundt 250, og hver student sitter igjen med en PDF-rapport om sitt eget spill.", 21, "s", INK2, 31)
    d.button(64, 368, 220, 56, "Be om lærertilgang", True, 16)
    d.button(296, 368, 110, 56, "Logg inn", False, 16)

    # Grafen som bærer siden: ett setes egne tall
    wk = 29
    cx, cy, cw, ch = 110, 480, 1220, 370
    c = Chart(d, cx, cy, cw, ch, 1, wk, -46, 40)
    c.grid([-30, 0, 30])
    c.step(SARA["levering"], 1, wk, SAGE, 1.5)
    c.step(SARA["ordre"], 1, wk, FOREST, 1.75)
    c.poly(NETTO, 1, wk, OCHRE, 3)
    c.weeks([1, 5, 10, 15, 20, 25])
    x11, y11 = c.P(11, v(SARA["ordre"], 11))
    d.note(x11, y11, c.X(9.4), c.Y(36), "En student bestilte **24** i Uke 11.", 300, 16, "l", route="vh", lh=22)
    x15, y15 = c.P(15, v(SARA["levering"], 15))
    d.note(x15, y15, x15, c.Y(38), "Fire uker senere kom **17**.", 240, 16, lh=22)
    x22, y22 = c.P(22, v(NETTO, 22))
    d.note(x22, y22, c.X(16), y22 - 11, f"Restordre **{v(SARA['restordre'], 22)}** i Uke 22.", 240, 16, "l", route="hv", lh=22)
    x29, y29 = c.P(29, v(NETTO, 29))
    d.note(x29, y29, x29, c.Y(-12), f"Lager **{v(SARA['lager'], 29)}** i Uke 29.", 170, 16, "l", lh=22)
    d.key(cx, cy + ch + 50, [("thick", OCHRE, "Lager over 0, restordre under 0"), ("line", FOREST, "Ordre"), ("line", SAGE, "Levering"), ("ring", INK, "Punktet kommentaren gjelder")], 14, 20)
    d.t(W - 110, cy + ch + 50, "Demodata, ett sete, Grossist", 14, "f", INK3, 400, "end")

    # Neste seksjon
    y = 960
    d.line(64, y - 22, W - 64, y - 22, GRID, 1)
    d.t(64, y + 26, "Alle spillene på én skjerm", 36, "s", INK, 500)
    d.para(64, y + 66, 470, "KI-spillere fyller tomme seter, så ett fravær ikke stopper gruppa og ingen spill blir stående uferdig. Studentene spiller på mobil, på norsk. Studentlisten kommer fra Canvas-eksport.", 18, "s", INK, 27)
    sp = [g for g in KL["spill"] if g["spill"] in (2, 30, 10, 20, 46)]
    order = {2: 0, 30: 1, 10: 2, 20: 3, 46: 4}
    sp.sort(key=lambda g: order[g["spill"]])
    hi = max(max(g["netto_lager"]["Grossist"]) for g in KL["spill"])
    lo = min(min(g["netto_lager"]["Grossist"]) for g in KL["spill"])
    tx = 620
    hdr = 960
    for lab, xx, an in [("Spill", tx, "start"), ("Status", tx + 60, "start"), ("Grossistens lager og restordre", tx + 240, "start"), ("Uke", tx + 580, "end"), ("Kost, kr", W - 64, "end")]:
        d.t(xx, y + 14, lab, 14, "f", INK2, 400, an)
    d.line(tx, y + 24, W - 64, y + 24, INK2, 0.75)
    ry = y + 24
    for g in sp:
        if g["status"] == "venter":
            st = f"{g['navn']}, {g['ventet_timer']} t"
        else:
            st = {"pauset": "Pauset til 19:00", "pågår": "Pågår"}[g["status"]]
        d.t(tx, ry + 25, str(g["spill"]), 15, "f", INK, 500)
        d.t(tx + 60, ry + 25, st, 15, "f", INK)
        X = lambda k: tx + 240 + (k - 1) / 35 * 300
        Y = lambda val: ry + 34 - (val - lo) / (hi - lo) * 30
        s = g["netto_lager"]["Grossist"][:g["uke"]]
        d.line(tx + 240, Y(0), tx + 540, Y(0), GRID, 0.75)
        d.path("M" + "L".join(f"{X(k + 1):.1f} {Y(val):.1f}" for k, val in enumerate(s)), stroke=OCHRE, sw=1.5)
        d.t(tx + 580, ry + 25, str(g["uke"]), 15, "f", INK2, 400, "end")
        d.t(W - 64, ry + 25, nb(g["kjedekost"], 0), 15, "f", INK, 400, "end")
        d.line(tx, ry + 38, W - 64, ry + 38, GRID, 0.5)
        ry += 38
    return d


def page_04():
    W, H = 1000, 900
    d = Doc("student", W, H, "Rapport: student på mobil",
            "To telefoner: Saras registrering fra Invitasjonen og hjem under spill med Rolle, seter, de seks stegene, frist og Labtimer.")
    # Registrering
    d.phone(60, 28)
    d.t(20, 54, "Rapport", 22, "s", INK, 500)
    d.t(20, 112, "Du er invitert til", 26, "s", INK, 500)
    d.t(20, 146, "IBE160", 26, "s", INK, 500)
    d.para(20, 186, 350, "Faglærer Bård har invitert deg til en øvelse i forsyningskjeder. Dere spiller i grupper på fire, på tiden dere selv velger.", 17, "s", INK, 25)
    y = 310
    for lab, val in [("Navn", "Sara Lunde"), ("E-post", "sara.lunde@student.example.no"), ("Passord", "••••••••••")]:
        d.t(20, y, lab, 14, "f", INK, 500)
        d.rect(20, y + 10, 350, 50, fill=WASH, rx=3)
        d.t(32, y + 41, val, 15, "f", INK)
        y += 86
    d.button(20, y + 4, 350, 58, "Opprett konto", True, 17)
    d.para(20, y + 92, 350, "E-posten kommer fra klasselisten. Invitasjonen er gyldig i 14 dager.", 14, "f", INK2, 20)
    d.para(20, y + 150, 350, "Du får vite hvem som leser svarene dine før du skriver dem.", 14, "f", INK2, 20)
    d.end()

    # Hjem
    d.phone(550, 28)
    d.t(20, 54, "Sara", 22, "s", INK, 500)
    d.t(370, 52, "Grossist, spill 17", 14, "f", INK2, 400, "end")
    # Spillet venter på deg
    d.rect(20, 72, 350, 96, fill=WASH, rx=4)
    d.t(34, 102, "Spillet venter på deg", 21, "s", INK, 500)
    d.t(34, 128, "Uke 11. Ida og Mikkel har bestilt.", 14, "f", INK2)
    d.t(34, 150, "Jonas har ikke bestilt ennå, 3 min.", 14, "f", INK2)
    d.button(20, 178, 350, 54, "Åpne Uke 11", True, 16)
    # Liten graf
    c = Chart(d, 44, 254, 312, 104, 1, 11, -17, 16)
    c.grid([-10, 0, 10])
    c.poly(NETTO, 1, 11, OCHRE, 2.25)
    x11, y11 = c.P(11, v(NETTO, 11))
    d.note(x11, y11, c.X(7), y11 - 9, f"Restordre **{v(SARA['restordre'], 11)}** nå.", 150, 14, "l", route="hv")
    # Setene
    d.t(20, 394, "Setene", 17, "s", INK, 500)
    yy = 420
    for name, role in [("Ida", "Detaljist"), ("Sara (du)", "Grossist"), ("Mikkel", "Distributør"), ("Jonas", "Fabrikk")]:
        d.t(20, yy, name, 14, "f", INK, 600 if "du" in name else 400)
        d.t(370, yy, role, 14, "f", INK2, 400, "end")
        yy += 22
    # Stegene
    d.t(20, yy + 16, "Stegene", 17, "s", INK, 500)
    yy += 42
    steps = [("Klassespill", "Pågår", True), ("Debrief", "Frist fr. 11. des", False), ("Quiz", "Etter Debrief", False), ("Replay", "Etter quiz", False), ("Individuell test", "Frist fr. 18. des", False), ("Rapport", "PDF, når du er ferdig", False)]
    for i, (lab, st, on) in enumerate(steps):
        d.circle(26, yy - 5, 5, fill=INK if on else PAPER, stroke=INK if on else INK2, sw=1.25)
        if i < 5:
            d.line(26, yy + 1, 26, yy + 19, INK3, 0.75)
        d.t(42, yy, lab, 14, "f", INK, 600 if on else 400)
        d.t(370, yy, st, 13, "f", INK2, 400, "end")
        yy += 25
    # Frist og Labtimer
    d.line(20, yy + 2, 370, yy + 2, GRID, 1)
    d.t(20, yy + 26, "Spillfrist ti. 8. des", 14, "f", INK, 600)
    d.t(20, yy + 48, "Labtimer, Datalab A2: to. 26. nov 14:15, ma. 30. nov", 13, "f", INK2)
    d.t(20, yy + 66, "10:15, to. 3. des 14:15, ma. 7. des 10:15", 13, "f", INK2)
    d.end()
    return d


def tile(d, x, y, w, h, title, line, draw=None):
    d.rect(x, y, w, h, fill=PAPER, stroke=FRAME, rx=3)
    d.g(x, y)
    if draw:
        draw(d, w, h)
    d.end()
    d.t(x, y + h + 20, title, 15, "s", INK, 600)
    d.para(x, y + h + 37, w, line, 12, "f", INK2, 15)


def lines(d, w, y, n, step=9, x=10, sh=1.0):
    for i in range(n):
        d.rect(x, y + i * step, (w - 2 * x) * (sh if i < n - 1 else 0.6), 3, fill=WASH)


def mini_graph(d, x, y, w, h, wk=36, sim=False):
    c = Chart(d, x, y, w, h, 1, wk, -44, 34)
    c.grid([0], labels=False)
    c.poly(NETTO, 1, wk, OCHRE, 1.5)
    return c


def page_09():
    W, H = 2000, 1400
    d = Doc("alle", W, H, "Rapport: alle andre sider",
            "Kontaktark over alle øvrige sider, gruppert per rolle, med Studentrapporten som konseptets endepunkt.", bg=PAPER)
    d.t(40, 56, "Alle andre sider", 36, "s", INK, 500)
    d.para(40, 88, 1500, "Samme stemme overalt: en graf eller tabell per flate, kommentert der det gjelder. Rapporten til høyre er stedet resten av produktet leder fram til.", 17, "s", INK2, 24)

    tw_, th = 205, 138
    gx, gy = 22, 92
    x0, y0 = 40, 158

    # Studentrapporten stor til høyre
    rx, ry, rw, rh = 1400, 112, 560, 1110
    d.rect(rx, ry, rw, rh, fill=WHITE, stroke=FRAME, sw=1)
    d.g(rx, ry)
    d.t(36, 58, "Du bestilte 24 da 16 var på vei", 27, "s", INK, 500)
    d.para(36, 86, rw - 72, "Sara Lunde. IBE160, class-of-1994. Grossist, spill 17. Generert 18. des 2026. Dokumenterer arbeidet, er ikke en karakter.", 13, "f", INK2, 18)
    c = Chart(d, 62, 134, rw - 98, 190, 1, 36, -44, 34)
    c.grid([-30, 0, 30], size=12)
    c.poly(NETTO, 1, 36, OCHRE, 2)
    c.weeks([1, 10, 20, 30, 36], size=12)
    x22, y22 = c.P(22, v(NETTO, 22))
    d.note(x22, y22, c.X(16), y22 - 9, f"Restordre **{v(SARA['restordre'], 22)}** i Uke 22.", 170, 13, "l", route="hv")
    x29, y29 = c.P(29, v(NETTO, 29))
    d.note(x29, y29, x29, c.Y(-10), f"Lager **{v(SARA['lager'], 29)}** i Uke 29.", 120, 13, "l")
    y = d.para(36, 376, rw - 72, "Din Forklaring sa at du ikke fikk nok varer. Tallene viser det samme: levering lå på 4 i tretten uker. De viser også noe du ikke kunne se: kundene kjøpte 8 hele veien fra Uke 5, og Ida bestilte for å ta igjen. Din ordre på 24 kom til Distributør i Uke 13.", 15, "s", INK, 22)
    d.t(36, y + 2, "KI-generert, kan ta feil. Alle tall er fra loggen.", 12, "f", INK2, 600)
    c = Chart(d, 62, y + 22, rw - 98, 130, 1, 36, 0, 34)
    c.grid([0, 10, 20, 30], size=12)
    c.step(S17["Detaljist"]["ordre"], 1, 36, SAGE, 1)
    c.step(S17["Distributør"]["ordre"], 1, 36, FOREST, 1)
    c.step(S17["Fabrikk"]["ordre"], 1, 36, INK, 1.25)
    c.step(S17["Grossist"]["ordre"], 1, 36, OCHRE, 1.75)
    c.step(S17["demand"], 1, 36, INK3, 1.25)
    d.key(36, y + 176, [("line", SAGE, "Detaljist"), ("thick", OCHRE, "Grossist"), ("line", FOREST, "Distributør"), ("line", INK, "Fabrikk")], 12, 10)
    yy = y + 202
    d.t(36, yy, "Uke for uke fra ditt sete", 15, "s", INK, 600)
    hdr = [("Uke", 36), ("Inn. ordre", 90), ("Levering", 170), ("Lager", 240), ("Restordre", 296), ("På vei", 376), ("Ordre", 436), ("Kost", 524)]
    yy += 18
    for lab, xx in hdr:
        d.t(xx, yy, lab, 12, "f", INK2, 400, "end" if lab == "Kost" else "start")
    for wk in (10, 11, 12):
        yy += 16
        vals = [wk, v(SARA["innkommende_ordre"], wk), v(SARA["levering"], wk), v(SARA["lager"], wk), v(SARA["restordre"], wk), v(SARA["paa_vei"], wk), v(SARA["ordre"], wk), nb(v(SARA["kost_sum"], wk))]
        for (lab, xx), val in zip(hdr, vals):
            d.t(xx, yy, str(val), 12, "f", INK, 600 if wk == 11 else 400, "end" if lab == "Kost" else "start")
    # Replay i rapporten
    yy += 40
    d.t(36, yy, "Andre runde: Replay", 21, "s", INK, 500)
    R = FX["replay_sara"]
    RG = R["serier"]["Grossist"]
    NR = [a - b for a, b in zip(RG["lager"], RG["restordre"])]
    yy = d.para(36, yy + 26, rw - 72, f"Tilfeldig etterspørsel, tre KI-spillere, 33 uker. Kostnad for Grossist {nb(R['kost_per_rolle']['Grossist'])} kr. Ikke like for like med Klassespillet, men du kan se hva du gjorde annerledes.", 15, "s", INK, 22)
    c = Chart(d, 62, yy + 2, rw - 98, 150, 1, 33, -44, 34)
    c.grid([-30, 0, 30], size=12)
    c.poly(NR, 1, 33, OCHRE, 2)
    c.weeks([1, 10, 20, 30, 33], size=12)
    peak = max(RG["restordre"])
    wk = RG["restordre"].index(peak) + 1
    xr_, yr_ = c.P(wk, -peak)
    d.note(xr_, yr_, c.X(wk) + 26, yr_ + 8, f"Restordre **{peak}** i Uke {wk}, mot **{max(SARA['restordre'])}** i Klassespillet.", 180, 13, route="hv")
    d.t(36, rh - 22, "Demodata. Viser side 2 og 3 av 6. Dokumenterer arbeidet, er ikke en karakter.", 12, "f", INK3)
    d.end()
    d.t(rx, ry + rh + 26, "Studentrapport (PDF)", 19, "s", INK, 500)
    d.para(rx, ry + rh + 50, rw - 40, "Konseptets endepunkt: artikkelen fra Debriefen, ferdig satt for utskrift, med Replay, test og uke-for-uke-tabell. Andre studenter står bare som Rolle. KI-vurderingen er utelatt, om den ikke legges til.", 15, "s", INK2, 21)

    def form(d, w, h):
        lines(d, w, 16, 2, 9)
        d.rect(10, 44, w - 20, 16, fill=WASH)
        d.rect(10, 66, w - 20, 16, fill=WASH)
        d.rect(10, 92, w - 20, 22, fill=INK, rx=2)

    def login(d, w, h):
        d.rect(10, 30, w - 20, 18, fill=WASH)
        d.rect(10, 56, w - 20, 18, fill=WASH)
        d.rect(10, 86, w - 20, 22, fill=INK, rx=2)

    def rules(d, w, h):
        c = mini_graph(d, 12, 56, w - 24, 70, 5)
        d.para(10, 22, w - 34, "En ordre kommer fram etter om lag 4 uker. Du bestiller én gang per Uke.", 12, "s", INK, 15)

    def start(d, w, h):
        c = mini_graph(d, 12, 42, w - 40, 88, 11)
        x, y = c.P(11, v(NETTO, 11))
        d.ring(x, y, 2.5)
        d.t(10, 24, "Startoppgave: hva er posisjonen?", 12, "s", INK)

    def replay(d, w, h):
        R = FX["replay_sara"]["serier"]["Grossist"]
        NR = [a - b for a, b in zip(R["lager"], R["restordre"])]
        c = Chart(d, 12, 22, w - 42, 100, 1, 18, -20, 20)
        c.grid([0], labels=False)
        c.poly(NR, 1, 18, OCHRE, 1.5)
        n, p = v(NR, 18), v(R["paa_vei"], 18)
        ytop = c.Y(min(n + p, 20))
        d.rect(c.X(18) + 4, ytop, 5, c.Y(n) - ytop, fill=FOREST)
        d.t(10, 15, "Replay: posisjonen tegnet", 12, "f", INK2)

    def replay_g(d, w, h):
        R = FX["replay_sara"]["serier"]["Grossist"]
        c = Chart(d, 12, 28, w - 24, 96, 1, 33, -20, 26)
        c.grid([0], labels=False)
        NR = [a - b for a, b in zip(R["lager"], R["restordre"])]
        c.poly(NR, 1, 33, OCHRE, 1.5)
        d.t(10, 18, f"{nb(FX['replay_sara']['kost_per_rolle']['Grossist'])} kr. Ikke like for like.", 12, "f", INK2)

    def test_mc(d, w, h):
        d.t(10, 20, "Flervalg", 12, "f", INK2)
        for i in range(4):
            d.rect(10, 28 + i * 25, w - 20, 19, fill=WASH if i == 1 else "none", stroke=None if i == 1 else GRID)

    def test_draw(d, w, h):
        c = Chart(d, 12, 26, w - 24, 96, 1, 12, 0, 12)
        c.grid([0, 4, 8, 12], labels=False)
        c.step(S17["demand"], 1, 12, INK, 1.5)
        d.t(10, 18, "Tegn lageret, eller fyll tabellen", 12, "f", INK2)

    def test_long(d, w, h):
        d.t(10, 20, "Langsvar", 12, "f", INK2)
        d.rect(10, 28, w - 20, 96, fill=WASH)
        lines(d, w, 38, 4, 12, 18)

    def ki_v(d, w, h):
        d.t(10, 20, "KI-generert, teller ikke", 12, "f", INK, 600)
        lines(d, w, 34, 8, 11)

    def side(d, w, h):
        fe = [g for g in KL["spill"] if g["status"] == "ferdig"][:9]
        cw_, ch_ = (w - 20) / 3, 28
        for i, g in enumerate(fe):
            micro(d, 10 + (i % 3) * cw_, 26 + (i // 3) * (ch_ + 2), cw_ - 6, ch_, g, 48)
        d.t(10, 18, "Spillene side om side", 12, "f", INK2)

    def home_t(d, w, h):
        d.t(10, 22, "Tre ting krever deg", 13, "s", INK, 500)
        lines(d, w, 34, 3, 12)
        for i, g in enumerate(KL["spill"][:4]):
            micro(d, 10 + i * ((w - 20) / 4), 92, (w - 20) / 4 - 6, 30, g, 48)

    def klrap(d, w, h):
        fe = [g for g in KL["spill"] if g["status"] == "ferdig"]
        fe.sort(key=lambda g: g["kjedekost"])
        bw = (w - 20) / len(fe)
        mx = fe[-1]["kjedekost"]
        for i, g in enumerate(fe):
            hh = g["kjedekost"] / mx * 90
            d.rect(10 + i * bw, 126 - hh, max(bw - 1, 1), hh, fill=OCHRE if g["kjedekost"] == 1954 else SAGE)
        d.t(10, 22, "Kjedekost, 41 spill", 12, "f", INK2)

    def innsikt(d, w, h):
        c = Chart(d, 12, 26, w - 24, 100, 1, 36, 0, 34)
        c.grid([0, 20], labels=False)
        for r, col in zip(ROLES, (SAGE, OCHRE, FOREST, INK)):
            c.step(S17[r]["ordre"], 1, 36, col, 1)
        d.t(10, 18, "Spill 17, uke for uke", 12, "f", INK2)

    def studside(d, w, h):
        d.t(10, 22, "Sara: steg og tid", 13, "s", INK, 500)
        for i in range(6):
            d.circle(20 + i * ((w - 40) / 5), 44, 5, fill=INK if i < 1 else PAPER, stroke=INK2)
        lines(d, w, 64, 5, 11)

    def plenum(d, w, h):
        cols, rows = 10, 6
        cw = (w - 16) / cols
        chh = (h - 16) / rows
        for i, g in enumerate(KL["spill"]):
            micro(d, 8 + (i % cols) * cw, 8 + (i // cols) * chh, cw - 3, chh - 4, g, 48)

    def tverr(d, w, h):
        fer = KL["ferdige"]["kjedekost"]
        fj = KL["fjoraaret"]
        sc = lambda val: 12 + val / 3600 * (w - 24)
        d.t(10, 20, "Kjedekost per klasse", 12, "f", INK2)
        d.line(sc(fer["min"]), 56, sc(fer["max"]), 56, GRID, 2)
        d.line(sc(fer["q1"]), 56, sc(fer["q3"]), 56, SAGE, 6)
        d.circle(sc(fer["median"]), 56, 4.5, fill=OCHRE, stroke=PAPER, sw=1.5)
        d.t(10, 42, "class-of-1994", 12, "f", INK2)
        d.circle(sc(fj["median_kjedekost"]), 104, 4.5, fill=INK, stroke=PAPER, sw=1.5)
        d.line(12, 104, w - 12, 104, GRID, 1)
        d.t(10, 90, f"{fj['klasse']}, median", 12, "f", INK2)

    def msg(d, w, h):
        d.t(10, 22, "Meldinger", 13, "s", INK, 500)
        for i in range(4):
            d.rect(10, 34 + i * 24, 40, 6, fill=SAGE)
            d.rect(58, 34 + i * 24, w - 68, 6, fill=WASH)

    def lartest(d, w, h):
        c = mini_graph(d, 12, 28, w - 24, 98, 18)
        d.t(10, 18, "Lærers testspill, tre KI-spillere", 12, "f", INK2)

    def admin(d, w, h):
        d.t(10, 22, "Admin", 13, "s", INK, 500)
        lines(d, w, 36, 6, 14)

    def users(d, w, h):
        d.t(10, 22, "Brukere og roller", 13, "s", INK, 500)
        for i in range(5):
            d.rect(10, 34 + i * 18, 70, 6, fill=WASH)
            d.rect(90, 34 + i * 18, 40, 6, fill=SAGE if i == 0 else WASH)

    def kikost(d, w, h):
        d.t(10, 22, "KI-kostnad per Klasse", 13, "s", INK, 500)
        lines(d, w, 36, 7, 12)

    groups = [
        ("Student", [("Invitasjon og registrering", "Lenken fra e-posten, konto på ett skjermbilde.", form), ("Logg inn", "E-post og passord.", login),
                     ("Regler før første ordre", "Forsinkelsen og Uke 1 til 4 forklart med en graf.", rules), ("Startoppgave", "Ett regnestykke før spillet starter.", start),
                     ("Replay", "Saras andre runde. Posisjonen er tegnet i grafen.", replay), ("Replay-gjennomgang", "Kostnad, graf, to øyeblikk. Ikke like for like.", replay_g),
                     ("Individuell test: flervalg", "Samme spørsmål som i quizen.", test_mc), ("Individuell test: tegne og tabell", "Tegn lageret, med tabell som alternativ.", test_draw),
                     ("Individuell test: langsvar", "Forklar med egne ord og egne tall.", test_long), ("KI-vurdering", "Teller ikke og er aldri en karakter.", ki_v),
                     ("Alle spill side om side", "Ditt spill blant de andre, uten navn.", side)]),
        ("Faglærer", [("Lærerhjem", "Redaksjonsmøtet for alle Klasser.", home_t), ("Klasserapport", "Kostnad, mønstre, trakt, til nedlasting.", klrap),
                      ("Spillinnsikt", "Ett spill uke for uke, alle Roller.", innsikt), ("Studentside", "Steg, tid og Forklaring for én student.", studside),
                      ("Alle spill i plenum", "60 mikrografer på storskjerm. Ingen navn.", plenum), ("Tverrklasse-statistikk", "Klassen mot class-of-1993.", tverr),
                      ("Meldinger", "Til spill, gruppe eller hele Klassen.", msg), ("Lærers testspill", "Prøv spillet med tre KI-spillere.", lartest)]),
        ("Admin", [("Admin-område", "Klasser, drift og status.", admin), ("Brukere og roller", "Hvem er faglærer, hjelpelærer, admin.", users), ("KI-kostnad", "Forbruk per Klasse og måned.", kikost)]),
    ]
    y = y0 - 20
    cols = 6
    for name, items in groups:
        d.t(x0, y + 8, name, 22, "s", INK, 500)
        y += 22
        for i, (title, line, fn) in enumerate(items):
            r, cc = divmod(i, cols)
            tile(d, x0 + cc * (tw_ + gx), y + r * (th + gy - 14), tw_, th, title, line, fn)
        rowsn = (len(items) + cols - 1) // cols
        y += rowsn * (th + gy - 14) + 8
    d.t(1960, 1384, "Demodata", 12, "f", INK3, 400, "end")
    return d
