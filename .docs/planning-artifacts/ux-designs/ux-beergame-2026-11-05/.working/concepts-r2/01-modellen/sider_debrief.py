"""Debrief og lærerens oversikt."""
from modell import *  # noqa: F403

F = FX["spill17"]
R = FX["bare_sara_teller_paa_vei"]
A_ = FX["alle_teller_paa_vei"]
K = FX["klasse"]


def rute(d, x, y, tittel, w=390, h=590):
    """Telefonrute i Debriefen: samme 390-skala, beskåret i høyden."""
    d.text(x, y - 12, tittel, size=15, w=600)
    d.open(f"translate({x} {y})")
    d.rect(0, 0, w, h, fill=KALK, stroke=KULL, sw=1, rx=18)


def steg1(d):
    d.text(16, 40, "Hvorfor svingte kjeden?", size=22, w=600)
    y = d.wrap(16, 66, "Skriv din Forklaring før dere ser mer. Den kan ikke endres etterpå.", 358, size=14, lh=20, fill=KULL2)
    d.rect(16, y + 4, 358, 158, fill=HVIT, stroke=KULL, sw=1.2)
    d.wrap(28, y + 30, "Vi bestilte for mye fordi vi fikk så lite inn. Ordrene jeg fikk fra Ida steg fort, og da måtte jeg ta høyde for det. Det jeg bestilte kom først mange uker etter.", 330, size=15, lh=22)
    y += 176
    # den låste raden
    d.text(16, y + 14, "Kundenes etterspørsel", size=14, w=500)
    d.rect(16, y + 24, 358, 54, fill="none", stroke=KULL2, sw=0.9, dash="3 3")
    d.text(195, y + 56, "Låst til alle fire har levert", size=14, fill=KULL2, a="middle")
    y += 96
    for navn, rolle, st in [("Ida", "Detaljist", "levert"), ("Sara", "Grossist", "skriver (deg)"),
                            ("Mikkel", "Distributør", "levert"), ("Jonas", "Fabrikk", "levert")]:
        d.text(16, y + 8, f"{navn}, {rolle}", size=13)
        d.text(374, y + 8, st, size=13, fill=KULL2 if st == "levert" else KULL, w=400 if st == "levert" else 500, a="end")
        y += 21
    knapp(d, 16, 504, 358, 50, "Lever Forklaringen", fs=15)


def steg2(d):
    dem = S17["demand"]
    d.text(16, 36, "Dette er det kundene gjorde.", size=22, w=600)
    x0, step, y0, k = 32, 9.5, 300, 7.0
    d.line(x0, y0, x0 + 36 * step, y0, stroke=KULL, sw=1)
    for v in (10, 20, 30):
        d.line(x0, y0 - v * k, x0 + 36 * step, y0 - v * k, stroke=GRID, sw=0.7)
        d.text(x0 - 5, y0 - v * k + 4, v, size=13, fill=KULL2, a="end")
    d.text(x0 - 5, y0 + 4, 0, size=13, fill=KULL2, a="end")
    xs = [x0 + i * step for i in range(37)]
    d.path(path_of(steg(xs, [y0 - v * k for v in dem])), stroke=KULL, sw=2.4)
    na_kant(d, x0 + 4.5 * step, y0 - 30 * k, y0 + 2)
    d.text(x0 + 4.5 * step + 6, y0 - 30 * k + 12, "Uke 5", size=14, w=600)
    d.text(x0 + 5.5 * step, y0 - 8 * k - 8, "8 per uke. Hele veien.", size=14, w=500)
    d.text(x0, y0 + 18, "Uke 1", size=13, fill=KULL2)
    d.text(x0 + 36 * step, y0 + 18, 36, size=13, fill=KULL2, a="end")
    d.text(x0, y0 - 4 * k - 8, "4", size=14, w=500)
    y = 350
    y = d.wrap(16, y, "Ett hopp, fra 4 til 8, i Uke 5. Deretter ingen endring i 31 uker.", 358, size=18, lh=26, w=500)
    y = d.wrap(16, y + 8, "Alt annet dere så, ble skapt inne i kjeden. Øvelsen heter ølspillet, og den gir dette mønsteret nesten hver gang.", 358, size=15, lh=22)
    d.text(16, y + 16, f"Fabrikk bestilte opptil {max(S17['Fabrikk']['ordre'])}.", size=15, w=500)
    knapp(d, 16, 504, 358, 50, "Se alle fire", fs=15)


def steg3(d):
    d.text(16, 36, "Svingningen vokser oppover", size=22, w=600)
    x0, step, y0, k = 32, 9.5, 262, 6.4
    for v in (0, 10, 20, 30):
        d.line(x0, y0 - v * k, x0 + 36 * step, y0 - v * k, stroke=GRID if v else KULL, sw=0.7 if v else 1)
        d.text(x0 - 5, y0 - v * k + 4, v, size=13, fill=KULL2, a="end")
    rolle_linjer(d, x0, y0, k, step, 36, demand=S17["demand"])
    wx = lambda i: x0 + (i - 0.5) * step
    d.text(wx(18) + 8, y0 - 31 * k + 4, "Fabrikk", size=13, w=600)
    d.text(wx(11) - 6, y0 - 24 * k + 2, "Grossist", size=13, w=500, a="end")
    d.line(wx(14), y0 - 22 * k, wx(13), y0 - 27.5 * k, stroke=KULL2, sw=0.6)
    d.text(wx(13), y0 - 28 * k, "Distributør", size=13, w=500, a="end")
    d.line(wx(24), y0 - 9 * k, wx(25.5), y0 - 14.5 * k, stroke=KULL2, sw=0.6)
    d.text(wx(25.5), y0 - 15 * k, "Detaljist", size=13, w=500)
    d.line(wx(32), y0 - 8 * k, wx(32), y0 - 11 * k, stroke=KULL2, sw=0.6)
    d.text(wx(30), y0 - 11.5 * k, "Kundene", size=13, w=600)
    d.text(x0, y0 + 16, "Uke 1", size=13, fill=KULL2)
    d.text(x0 + 36 * step, y0 + 16, 36, size=13, fill=KULL2, a="end")
    # forsterkning som rekke
    y = 306
    fs = F["forsterkning"]
    xs = [16, 106, 196, 286]
    for x, r in zip(xs, ROLES):
        d.text(x, y + 26, faktor(fs[r]), size=25, w=600)
        d.text(x, y + 45, r, size=13, fill=KULL2)
    y = d.wrap(16, y + 76, "Forsterkning: hvor mye mer ordrene svinger enn kundene. Toppene kommer også senere for hvert ledd.", 358, size=14, lh=20)
    y = d.wrap(16, y + 6, "Hvert ledd så bare ordrene fra nedstrøms. Du så ordrene fra Ida, ikke kundene.", 358, size=14, lh=20, fill=KULL2)
    knapp(d, 16, 504, 358, 50, "Se ditt øyeblikk", fs=15)


def steg4(d):
    G = GROSSIST
    w = 11
    d.text(16, 36, "Ditt øyeblikk: Uke 11", size=22, w=600)
    y = 64
    d.text(16, y, "Du så", size=13, fill=KULL2)
    d.text(80, y, f"Lager {G['lager'][w-1]}, Restordre {G['restordre'][w-1]}, På vei {G['paa_vei'][w-1]}", size=14, w=500)
    y += 22
    d.text(16, y, "Du bestilte", size=13, fill=KULL2)
    pos0 = G['lager'][w-1] - G['restordre'][w-1] + G['paa_vei'][w-1]
    d.text(100, y, f"{G['ordre'][w-1]}. Posisjon {pos0} ble {pos0 + G['ordre'][w-1]}.", size=14, w=500)
    y += 22
    lev = G["levering"][14]
    d.text(16, y, "Det kom", size=13, fill=KULL2)
    d.text(80, y, f"{lev} i Uke 15, resten senere.", size=14, w=500)
    y += 22
    kost_lager = G["kost_sum"][35] - G["kost_sum"][24]
    d.text(16, y, "Senere", size=13, fill=KULL2)
    d.text(80, y, f"Restordre {max(G['restordre'])} i Uke {G['restordre'].index(max(G['restordre'])) + 1}, Lager {max(G['lager'])} i Uke {G['lager'].index(max(G['lager'])) + 1}.", size=14, w=500)
    y += 12
    # kurve med simulert referanse
    x0, st, y0, k = 32, 9.5, y + 74, 1.6
    net = netto(G)
    net_r = netto(R["serier"]["Grossist"])
    xs = [x0 + i * st for i in range(37)]
    for v in (-40, -20, 0, 20):
        d.line(x0, y0 - v * k, x0 + 36 * st, y0 - v * k, stroke=GRID if v else KULL, sw=0.7 if v else 1)
        d.text(x0 - 5, y0 - v * k + 4, tegn(v), size=13, fill=KULL2, a="end")
    d.path(path_of(steg(xs, [y0 - v * k for v in net])), stroke=KULL, sw=1.5)
    d.path(path_of(steg(xs, [y0 - v * k for v in net_r])), stroke=ORDRE, sw=1.5, dash="4 3")
    na_kant(d, x0 + 11 * st, y0 - 30 * k, y0 + 44 * k)
    d.text(x0 + 11 * st + 5, y0 - 22 * k, "Uke 11", size=13, w=600)
    d.text(xs[24], y0 - 34 * k, "Spill 17", size=13, w=500)
    d.text(374, y0 + 15, "Simulert, stiplet", size=13, w=500, fill=ORDRE, a="end")
    y = y0 + 44 * k + 18
    gs = R["kost_per_rolle"]["Grossist"]
    y = d.wrap(16, y, f"Simulert, samme kjede: Grossist teller alt på vei fra Uke 5 og bestiller {R['serier']['Grossist']['ordre'][10]} i Uke 11. Grossist {kr(gs, False)} mot {kr(F['kost_per_rolle']['Grossist'], False)}, Kjeden {kr(R['kjedekost'], False)} mot {kr(F['kjedekost'], False)}. Ikke en fasit.", 358, size=13, lh=18)
    y += 8
    d.line(16, y - 2, 374, y - 2, stroke=LINJE, sw=0.7)
    y += 15
    d.text(16, y, "Hva de andre så i Uke 11", size=14, w=600)
    y += 20
    Sd, Sf, Sm = S17["Detaljist"], S17["Fabrikk"], S17["Distributør"]
    rows = [
        ("Ida", f"Restordre {Sd['restordre'][10]}, kundeordre {Sd['innkommende_ordre'][10]}"),
        ("Mikkel", f"Lager {Sm['lager'][10]}, ordre inn {Sm['innkommende_ordre'][10]}, bestilte {Sm['ordre'][10]}"),
        ("Jonas", f"Lager {Sf['lager'][10]}, ordre inn {Sf['innkommende_ordre'][10]}, bestilte {Sf['ordre'][10]}"),
    ]
    for a, b in rows:
        d.text(16, y, a, size=13, fill=KULL2)
        d.text(70, y, b, size=13)
        y += 18
    y = d.wrap(16, y + 2, f"Dine 24 nådde Mikkel i Uke 13, der ordre inn ble {Sm['innkommende_ordre'][12]}.", 358, size=13, lh=18, w=500)
    d.text(16, 496, "Tekst KI-generert, kan ta feil. Tall fra loggen.", size=13, fill=KULL2)
    knapp(d, 16, 504, 358, 50, "Til Debrief-quiz", fs=15)


def steg5(d):
    y = d.wrap(16, 42, "Uke 11: Lager 0, Restordre 13, På vei 16. Hva er Posisjonen?", 358, size=19, lh=26, w=600)
    y += 6
    alt = [("−13", "feil"), ("3", "rett"), ("16", None), ("29", None)]
    for s, st in alt:
        d.rect(16, y, 358, 42, fill=HVIT if st else "none", stroke=KULL if st else LINJE, sw=1.3 if st else 0.8)
        d.text(30, y + 27, s, size=17, w=600 if st else 400)
        if st == "feil":
            d.text(360, y + 26, "Ditt svar", size=14, a="end", fill=KULL2)
        if st == "rett":
            d.text(360, y + 26, "Riktig svar", size=14, w=600, a="end")
        y += 50
    y += 2
    y = d.wrap(16, y + 8, "−13 er Lager minus Restordre. Det er det du ser i hullet. Posisjonen regner også med det du allerede har bestilt:", 358, size=15, lh=22)
    d.text(16, y + 12, "0 − 13 + 16 = 3", size=24, w=600)
    y += 42
    d.wrap(16, y, "Nesten alle ser hullet først. Derfor står feltene på samme tegning.", 358, size=14, lh=20, fill=KULL2)
    knapp(d, 16, 504, 358, 50, "Neste spørsmål", fs=15)


def debrief07():
    d = Doc("07-debrief", 2100, 1200, "Modell: Gruppedebrief",
            "Delt skjerm med fire bygg på rekke i samme modell og skala og dragbar nå-kant, og fem steg på telefon, fra Forklaring til quiz.")
    # delt skjerm
    W = 18
    d.text(40, 46, "Delt skjerm: dra kanten gjennom spillet", size=26, w=600)
    d.text(560, 46, f"Spill 17 nå i Uke {W}. Samme modell, samme skala, fire Roller. Under ligger ordrene deres, med kundene som svart linje.", size=15, fill=KULL2)
    col = 505
    x0 = 36
    k = 1.75
    step = 11.5
    oy = 262
    y0 = 520
    ko = 3.2
    ymodtop = 62
    for j, r in enumerate(ROLES):
        S = S17[r]
        cx = x0 + j * col
        xnow = cx + 22 + W * step
        d.text(cx + 22, 92, r, size=20, w=600)
        d.text(cx + 22 + est(r, 20) + 14, 92, faktor(F["forsterkning"][r]), size=20, w=500, fill=KULL2)
        if j:
            d.line(cx - 4, 70, cx - 4, 560, stroke=GRID, sw=0.7)
        snitt(d, xnow, oy, k, W, S, A=118, D=40, H=22, c=32, c2=20, f=22, g=4, dv=16, fs=12, labels=False, uker=False)
        lag, res, vei = S["lager"][W - 1], S["restordre"][W - 1], S["paa_vei"][W - 1]
        # etiketter til venstre for bygget
        lx = cx + 22
        lab = f"Lager {lag}" if res == 0 else f"Restordre {res}"
        d.text(lx, 118, lab, size=14, w=500)
        d.text(lx, 136, f"På vei {vei}", size=14, w=500)
        # ordrekurve, samme tidsakse
        for v in (10, 20, 30):
            d.line(cx + 22, y0 - v * ko, cx + 22 + 36 * step, y0 - v * ko, stroke=GRID, sw=0.7)
            d.text(cx + 18, y0 - v * ko + 4, v, size=11, fill=KULL2, a="end")
        o = S["ordre"]
        bw = 4.2
        for i, v in enumerate(o):
            x = cx + 22 + i * step + (step - bw) / 2
            d.rect(x, y0 - v * ko, bw, v * ko, fill=ORDRE if i < W else SKYGGE_FLATE, crisp=True)
        dem = S17["demand"]
        xs = [cx + 22 + i * step for i in range(37)]
        d.path(path_of(steg(xs, [y0 - v * ko for v in dem])), stroke=KULL, sw=1.2)
        d.line(cx + 22, y0, cx + 22 + 36 * step, y0, stroke=KULL, sw=1)
        na_kant(d, xnow, oy - 60, y0 + 8)
        # håndtak
        d.rect(xnow - 21, y0 + 8, 42, 20, fill=NA)
        d.text(xnow, y0 + 23, f"Uke {W}", size=12, w=600, fill=KULL, a="middle")
        d.text(cx + 22, y0 + 22, "Uke 1", size=12, fill=KULL2)
        d.text(cx + 22 + 36 * step, y0 + 22, 36, size=12, fill=KULL2, a="end")
    d.text(40, 576, "Modellen følger kanten: dra til Uke 5 og alt står stille, dra til Uke 29 og hullene er blitt til søyler. Demodata.", size=14, fill=KULL2)

    # fem steg
    ytop = 616
    gap = (2100 - 80 - 5 * 390) / 4
    steps = [(steg1, "Skriv Forklaring, avsløringen er låst"), (steg2, "Klimaks: etterspørselen avsløres"),
             (steg3, "Alle fire Rollers ordre"), (steg4, "Ditt øyeblikk"), (steg5, "Quiz med feil svar forklart")]
    for i, (fn, t) in enumerate(steps):
        x = 40 + i * (390 + gap)
        rute(d, x, ytop, t, h=566)
        fn(d)
        d.close()
    d.save()


# ---- 08 ----

def trakt(d, x, y, w, h):
    T = K["traktA"]
    steps = [("Registrert", T["registrert"]), ("Klassespill ferdig", T["klassespill_ferdig"]), ("Debrief ferdig", T["debrief_ferdig"]),
             ("Quiz bestått", T["quiz_bestått"]), ("Replay ferdig", T["replay_ferdig"]), ("Test levert", T["test_levert"]),
             ("KI-vurdering klar", T["ki_vurdering_klar"])]
    cw = w / len(steps)
    mx = steps[0][1]
    for i, (lab, v) in enumerate(steps):
        cx = x + i * cw
        d.text(cx, y + 15, v, size=17, w=600)
        d.text(cx + 34, y + 15, lab, size=12, fill=KULL2)
        d.rect(cx, y + 24, (cw - 12), 6, fill=GRID, crisp=True)
        d.rect(cx, y + 24, (cw - 12) * v / mx, 6, fill=SKYGGE, crisp=True)


def oversikt08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Modell: Oversikt for faglærer",
            "Plansnitt over 60 tomter ved siden av tabellen. Hver tomt viser ekte ordreserier. Nå-kanten står der spillet er.")
    X, Y, W_, H_ = 80, 40, 1440, 900
    d.rect(X, Y, W_, H_, fill=KALK, stroke=KULL, sw=1, rx=6)
    d.open(f"translate({X} {Y})")
    sp = K["spill"]
    cnt = lambda s: sum(1 for g in sp if g["status"] == s)
    n_paa = cnt("pågår") + cnt("pauset")
    d.text(24, 44, "Oversikt", size=30, w=600)
    d.text(170, 44, "class-of-1994, IBE160. Spillfrist ti. 8. des.", size=14, fill=KULL2)
    d.text(1416, 44, "Bård, Faglærer", size=14, fill=KULL2, a="end")
    d.text(24, 80, f"{len(sp)} Klassespill: {cnt('ferdig')} ferdig, {n_paa} pågår (herav {cnt('pauset')} pauset), {cnt('venter')} venter.", size=17, w=500)
    # filter
    fx = 24
    for i, f in enumerate(["Alle 60", f"Venter {cnt('venter')}", f"Pauset {cnt('pauset')}", f"Pågår {cnt('pågår')}", f"Ferdig {cnt('ferdig')}", "Med KI-seter", "Nær KI-overtakelse 1"]):
        wd = est(f, 13) + 22
        d.rect(fx, 96, wd, 28, fill=KULL if i == 0 else "none", stroke=KULL if i == 0 else LINJE, sw=0.8)
        d.text(fx + wd / 2, 115, f, size=13, fill=KALK if i == 0 else KULL, a="middle")
        fx += wd + 6

    # plansnitt
    cols, rows = 10, 6
    pw, ph = 86, 92
    gx, gy = 24, 160
    d.text(gx, 150, "Plansnitt: blå linje er Fabrikkens ordre, lys er Detaljist. Gul kant er der spillet står nå. Felles skala.", size=13, fill=KULL2)
    for i, g in enumerate(sp):
        c, r = i % cols, i // cols
        tomt(d, gx + c * pw, gy + r * ph, pw - 3, ph - 3, g, valgt=g["spill"] == 2, fs=11)

    # tabell
    tx = 908
    tw = 508
    d.text(tx, 150, "Trenger oppmerksomhet", size=15, w=600)
    d.text(tx + tw, 150, "Sortert etter ventetid", size=13, fill=KULL2, a="end")
    colx = [tx, tx + 44, tx + 112, tx + 238, tx + 288, tx + 328, tx + 396]
    y = 176
    for cx_, lab in zip(colx, ["Spill", "Status", "Venter på", "Tid", "KI", "Uke", ""]):
        d.text(cx_, y, lab, size=12, fill=KULL2)
    d.line(tx, y + 8, tx + tw, y + 8, stroke=KULL, sw=0.8)
    y += 28
    waiting = sorted([g for g in sp if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])
    paused = [g for g in sp if g["status"] == "pauset"]
    going = sorted([g for g in sp if g["status"] == "pågår"], key=lambda g: g["uke"])
    rh = 32
    for g in waiting + paused + going[:8]:
        first = g["spill"] == 2
        if first:
            d.rect(tx - 8, y - 21, tw + 16, rh + 26, fill=HVIT, stroke=KULL, sw=1.4)
        fw = 600 if first else 400
        d.text(colx[0], y, g["spill"], size=14, w=fw)
        st = {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår"}[g["status"]]
        d.text(colx[1], y, st, size=14, w=fw if g["status"] != "pågår" else 400, fill=KULL if g["status"] != "pågår" else KULL2)
        if g["status"] == "venter":
            d.text(colx[2], y, f"{g['navn']}, {g['venter_paa']}", size=13, w=fw)
            d.text(colx[3], y, f"{g['ventet_timer']} t", size=14, w=fw)
        elif g["status"] == "pauset":
            d.text(colx[2], y, f"Fortsetter {g['fortsetter']}", size=12, fill=KULL2)
        if g["ki_seter"]:
            d.text(colx[4], y, g["ki_seter"], size=14)
        d.text(colx[5], y, g["uke"], size=14)
        # samme kant: liten akse
        ax0, axw = colx[5] + 22, 36
        d.line(ax0, y - 4, ax0 + axw, y - 4, stroke=LINJE, sw=0.8)
        na_kant(d, ax0 + axw * g["uke"] / 36, y - 10, y + 2, sw=1.6)
        if g["status"] == "venter":
            knapp(d, colx[6], y - 16, tw - 396, 24, "Send Melding", primar=first, fs=12)
        if first:
            d.text(colx[1], y + 21, "KI overtar om 1 t, ved 24 t. Noah kan fortsatt bestille.", size=13, w=500)
            y += 26
        y += rh
        d.line(tx, y - 21, tx + tw, y - 21, stroke=GRID, sw=0.7) if not first else None
    d.text(tx, y + 2, f"Ytterligere {len(going) - 8} pågår uten ventetid. {cnt('ferdig')} ferdige er skjult.", size=13, fill=KULL2)

    # klassens forsterkning og trakt
    yb = 730
    d.line(24, yb, 1416, yb, stroke=LINJE, sw=0.7)
    fq = K["ferdige"]["forsterkning_per_rolle"]
    fj = K["fjoraaret"]
    y = yb + 26
    d.text(24, y, "Klassen så langt", size=15, w=600)
    tt = "  ".join(f"{r} {faktor(fq[r]['median'])}" for r in ROLES)
    d.text(160, y, f"Median Forsterkning: {tt}", size=14)
    d.text(1416, y, f"{K['ferdige']['antall']} ferdige. Median Kjeden {tusen(K['ferdige']['kjedekost']['median'])} kr. Fjoråret {tusen(fj['median_kjedekost'])} kr.", size=14, fill=KULL2, a="end")
    y += 24
    trakt(d, 24, y, 1392, 40)
    y += 60
    d.text(24, y, "Trakten teller studenter. Oversikten viser kostnad per spill bare til Faglærer.", size=13, fill=KULL2)
    d.text(1416, y, "Demodata", size=13, fill=KULL2, a="end")
    d.close()
    d.save()
