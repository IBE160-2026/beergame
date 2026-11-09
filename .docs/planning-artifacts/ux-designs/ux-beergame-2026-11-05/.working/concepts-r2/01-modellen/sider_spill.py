"""Spillflatene og pedagogikkarket."""
from modell import *  # noqa: F403

K = 3.4          # målestokk på telefonen: px per enhet
STEP = 14
XNOW = 236
OY = 284
Y0 = 462
MOD = dict(A=170, D=62, H=40, c=48, c2=34, f=31, g=6, dv=28)


def telefon(d, x, y, s=1.0):
    d.open(f"translate({x} {y}) scale({s})")
    d.rect(0, 0, 390, 844, fill=KALK, stroke=KULL, sw=1, rx=30)


def topp(d, w, kost, navn="Sara, Grossist", spill="Spill 17"):
    d.text(16, 52, f"Uke {w}", size=31, w=600)
    d.text(16, 73, f"{navn}. {spill}", size=13, fill=KULL2)
    d.text(374, 36, "Totalkostnad", size=13, fill=KULL2, a="end")
    d.text(374, 58, kr(kost), size=20, w=500, a="end")


def komp_merker(d, w, S, xnow=XNOW, y0=Y0, k=K, step=STEP):
    """Direkte etiketter i kurven, plassert fra data."""
    x_of = lambda i: xnow - (w - i + 1) * step
    y_of = lambda v: y0 - v * k
    d.text(x_of(1) + 3, y_of(12) - 6, "Lager", size=13, fill=KULL2)
    last = w - 1
    topp_v = max(S["ordre"][last - 1], 12)
    if w <= 11:
        d.text(x_of(last) + step * 0.75, y_of(topp_v) - 6, "Ordre", size=13, fill=ORDRE, a="end", w=500)
    else:
        d.text(x_of(last) - 3, y_of(S["ordre"][last - 1] - 8), "Ordre", size=13, fill=ORDRE, a="end", w=500)


def regnestykke(d, y, w, S, new=None, xs=None):
    lag, res, vei = S["lager"][w - 1], S["restordre"][w - 1], S["paa_vei"][w - 1]
    cols = [("Lager", f"{lag}"), ("Restordre", f"{res}"), ("På vei", f"{vei}")]
    if new is not None:
        cols.append(("Ny ordre", f"{new}"))
    tot = lag - res + vei + (new or 0)
    cols.append(("Posisjon", tegn(tot)))
    ops = ["−", "+"] + (["+"] if new is not None else []) + ["="]
    xs = xs or ([16, 80, 166, 228, 306] if new is not None else [16, 96, 196, 296])
    d.line(16, y - 26, 374, y - 26, stroke=LINJE, sw=0.7)
    for i, (lab, val) in enumerate(cols):
        last = i == len(cols) - 1
        d.text(xs[i], y, val, size=22, w=600 if last else 500)
        d.text(xs[i], y + 18, lab, size=13, fill=KULL if last else KULL2, w=500 if last else 400)
        if i < len(ops):
            ow = est(val, 22)
            d.text(xs[i + 1] - 13, y, ops[i], size=18, fill=KULL2, a="middle")


def inntast(d, y, n):
    d.rect(16, y, 92, 58, fill=HVIT, stroke=KULL, sw=1.4)
    d.text(62, y + 39, n, size=30, w=600, a="middle")
    knapp(d, 120, y, 254, 58, f"Send ordre på {n}", fs=16)


def venterad(d, y, tekst="Venter på Jonas (3 min) og deg"):
    d.line(16, y - 18, 374, y - 18, stroke=LINJE, sw=0.7)
    d.text(16, y, tekst, size=13)
    d.text(16, y + 19, "Detaljer og ordrehistorikk", size=13, fill=KULL2)
    pil(d, 364, y + 6)
    d.line(16, y + 32, 374, y + 32, stroke=LINJE, sw=0.7)


def spillskjerm(d, w, S, kost, new=None, bekreftet=False, navn="Sara, Grossist"):
    topp(d, w, kost, navn)
    snitt(d, XNOW, OY, K, w, S, new=new, bekreftet=bekreftet, **MOD)
    kurve(d, XNOW, Y0, K, STEP, w, S, new=new, bekreftet=bekreftet, x_min=46, fs=14)
    na_kant(d, XNOW, OY - 50, Y0 + 20 * K + 2)
    _, _, total = pipeline(S, w)
    r = XNOW + 8
    d.text(r, OY + 46, f"På vei {total}", size=13, w=500)
    d.text(r, OY + 62, "ikke garantert", size=13, fill=KULL2)
    net = netto(S)[w - 1]
    d.text(r, Y0 - net * K + 4, tegn(net), size=13, w=600)
    komp_merker(d, w, S)
    # to tall ved kanten, over nullplanet
    d.text(r, Y0 - 62, "Innkommende ordre", size=13, fill=KULL2)
    d.text(r, Y0 - 43, S["innkommende_ordre"][w - 1], size=17, w=500)
    d.text(r, Y0 - 21, "Levering", size=13, fill=KULL2)
    d.text(r + 62, Y0 - 21, S["levering"][w - 1], size=17, w=500)


def malestokk(d, x, y, k, fs=13):
    """Målestokk: 10 enheter er like høyt i modellen og i kurven."""
    d.line(x, y, x, y - 10 * k, stroke=KULL, sw=0.9)
    d.line(x - 3, y, x + 3, y, stroke=KULL, sw=0.9)
    d.line(x - 3, y - 10 * k, x + 3, y - 10 * k, stroke=KULL, sw=0.9)
    d.text(x + 7, y - 5 * k + 4, "10 enheter", size=fs, fill=KULL2)


def skjerm_B(d):
    w = 11
    spillskjerm(d, w, GROSSIST, GROSSIST["kost_sum"][w - 1], new=24)
    malestokk(d, 22, 210, K)
    regnestykke(d, 578, w, GROSSIST, new=24)
    inntast(d, 616, 24)
    venterad(d, 712)
    d.text(16, 772, "Ordren kan ikke endres etter at den er sendt.", size=13, fill=KULL2)


def detaljpanel(d, x, y, w_=330):
    w = 11
    S = GROSSIST
    d.open(f"translate({x} {y})")
    d.rect(0, 0, w_, 844, fill=HVIT, stroke=LINJE, sw=0.8)
    pad = 16
    r = w_ - pad
    d.text(pad, 42, "Detaljer, Uke 11", size=20, w=600)
    yy = 74
    rows = [
        ("Innkommende ordre", S["innkommende_ordre"][w - 1]),
        ("Levering", S["levering"][w - 1]),
        ("Sendt denne uka", sendt(S, w)),
        ("Neste levering", S["levering"][w]),
        ("Lager", S["lager"][w - 1]),
        ("Restordre", S["restordre"][w - 1]),
        ("På vei", S["paa_vei"][w - 1]),
    ]
    for lab, v in rows:
        d.text(pad, yy, lab, size=14, fill=KULL2)
        d.text(r, yy, v, size=15, w=500, a="end")
        d.line(pad, yy + 8, r, yy + 8, stroke=GRID, sw=0.7)
        yy += 29
    yy += 18
    d.text(pad, yy, "På vei, felt for felt", size=15, w=500)
    yy += 24
    felt, _, _ = pipeline(S, w)
    for f in felt:
        d.text(pad, yy, f"Uke {f['uke']}", size=13, fill=KULL2)
        d.text(pad + 74, yy, "sendt" if f["sendt"] else "bestilt, ikke sendt", size=13, fill=KULL2)
        d.text(r, yy, f["n"], size=14, w=500, a="end")
        yy += 21
    d.text(pad, yy, f"Uke {w + 4}", size=13, fill=ORDRE, w=500)
    d.text(pad + 74, yy, "tastet nå", size=13, fill=ORDRE, w=500)
    d.text(r, yy, 24, size=14, w=600, fill=ORDRE, a="end")
    yy += 19
    yy = d.wrap(pad, yy + 3, "Ikke garantert. Leverandøren kan mangle varer.", w_ - 2 * pad, size=13, fill=KULL2)
    yy += 14
    d.text(pad, yy, "Dine ordre, Uke 1 til 10", size=15, w=500)
    yy += 12
    cw = (w_ - 2 * pad) / 10
    for i in range(10):
        v = S["ordre"][i]
        d.rect(pad + i * cw, yy, cw, 28, fill="none", stroke=LINJE, sw=0.6)
        d.text(pad + i * cw + cw / 2, yy + 19, v, size=14, w=600 if i == 9 else 400, a="middle")
    yy += 50
    d.text(pad, yy, "Venter på", size=15, w=500)
    yy += 23
    for navn, rolle, st in [("Ida", "Detaljist", "har bestilt"), ("Mikkel", "Distributør", "har bestilt"),
                            ("Jonas", "Fabrikk", "venter, 3 min"), ("Sara", "Grossist", "venter (deg)")]:
        d.text(pad, yy, f"{navn}, {rolle}", size=13)
        d.text(r, yy, st, size=13, fill=KULL2 if "har" in st else KULL, w=400 if "har" in st else 500, a="end")
        yy += 21
    yy += 10
    d.text(pad, yy, "Kostnad per enhet per uke", size=13, fill=KULL2)
    yy += 19
    d.text(pad, yy, "Lager 0,50. Restordre 1,00.", size=13)
    d.close()


def laptop(d, x, y, W=720, H=492):
    w = 11
    S = GROSSIST
    d.open(f"translate({x} {y})")
    d.rect(0, 0, W, H, fill=KALK, stroke=KULL, sw=1, rx=8)
    d.line(-14, H + 8, W + 14, H + 8, stroke=KULL, sw=1)
    d.line(0, H, 0, H + 8, stroke=KULL, sw=1)
    d.line(W, H, W, H + 8, stroke=KULL, sw=1)
    d.text(20, 42, f"Uke {w}", size=28, w=600)
    d.text(126, 42, "Sara, Grossist. Spill 17", size=13, fill=KULL2)
    d.text(W - 20, 42, f"Totalkostnad  {kr(S['kost_sum'][w - 1])}", size=15, w=500, a="end")
    d.line(20, 56, W - 20, 56, stroke=LINJE, sw=0.7)
    k = 3.0
    xnow = 312
    oy = 226
    y0 = 396
    snitt(d, xnow, oy, k, w, S, new=24, A=150, D=52, H=34, c=42, c2=28, f=28, g=5, dv=24, fs=13)
    kurve(d, xnow, y0, k, 15, w, S, new=24, x_min=70, fs=12)
    na_kant(d, xnow, oy - 42, y0 + 20 * k + 2)
    d.text(xnow + 8, y0 + 13 * k + 4, "−13", size=13, w=600)
    d.text(xnow + 8, oy + 36, "På vei 16, ikke garantert", size=12, fill=KULL2)
    # høyre kolonne: alt er synlig
    cx = 500
    d.line(cx - 16, 56, cx - 16, H - 14, stroke=LINJE, sw=0.7)
    yy = 80
    for lab, v in [("Innkommende ordre", S["innkommende_ordre"][w - 1]), ("Levering", S["levering"][w - 1]),
                   ("Sendt", sendt(S, w)), ("Neste levering", S["levering"][w])]:
        d.text(cx, yy, lab, size=13, fill=KULL2)
        d.text(W - 20, yy, v, size=14, w=500, a="end")
        yy += 22
    yy += 8
    d.line(cx, yy - 14, W - 20, yy - 14, stroke=GRID, sw=0.7)
    d.text(cx, yy + 2, "Dine ordre", size=13, fill=KULL2)
    yy += 8
    cw = (W - 20 - cx) / 10
    for i in range(10):
        d.text(cx + i * cw + cw / 2, yy + 14, S["ordre"][i], size=12, w=600 if i == 9 else 400, a="middle")
    yy += 42
    d.line(cx, yy - 14, W - 20, yy - 14, stroke=GRID, sw=0.7)
    d.text(cx, yy + 2, "0 − 13 + 16 + 24", size=19, w=500)
    yy += 21
    d.text(cx, yy + 2, "Lager, Restordre, På vei, Ny ordre", size=12, fill=KULL2)
    yy += 28
    d.text(cx, yy + 4, "Posisjon 27", size=19, w=600)
    yy += 22
    d.rect(cx, yy, 62, 44, fill=HVIT, stroke=KULL, sw=1.3)
    d.text(cx + 31, yy + 31, 24, size=23, w=600, a="middle")
    knapp(d, cx + 70, yy, W - 20 - cx - 70, 44, "Send ordre på 24", fs=13)
    yy += 66
    d.text(cx, yy, "Venter på Jonas (3 min) og deg", size=13)
    d.close()


def spill05():
    d = Doc("05-spill", 1600, 1000, "Modell: spilleskjermen i Uke 11",
            "Telefon og laptop for Sara, Grossist, Uke 11 med 24 tastet inn. Aksonometrisk snitt rett over kurven, samme målestokk, samme nå-kant.")
    d.text(50, 40, "Telefon, 390 bred. Uke 11 med 24 tastet inn.", size=14, fill=KULL2)
    telefon(d, 50, 56)
    skjerm_B(d)
    d.close()
    d.text(464, 40, "Bak ett trykk på Detaljer", size=14, fill=KULL2)
    detaljpanel(d, 464, 56)
    d.text(830, 40, "Samme tegning på laptop i Labtimen", size=14, fill=KULL2)
    laptop(d, 830, 56)
    # lesing
    x = 830
    y = 612
    d.text(x, y, "Alt du har bestilt, står et sted.", size=34, w=600)
    y += 40
    w_ = 330
    d.wrap(x, y, "Til venstre for den gule kanten har det skjedd, til høyre er det på vei. Hullet under gulvet er Restordre: 13 enheter, like dypt i modellen som i kurven under.", w_, size=15, lh=22)
    d.wrap(x + 370, y, "Stolpene for Uke 8, 9 og 10 er det samme som står utenfor bygget. Tast 24, så reiser det seg en stiplet stabel i felt Uke 15 med en gang. Du ser konsekvensen før du sender. Ingen sier hva som er riktig.", w_, size=15, lh=22)
    y += 136
    d.text(x, y, "Slik leser du tegningen", size=14, w=500)
    y += 26
    rows = [
        ("Skravert", "Restordre, under nullplanet. Koster 1,00 per uke."),
        ("Hvit søyle", "Lager, én linje per enhet. Koster 0,50 per uke."),
        ("Heltrukket blå", "Sendt. Kommer i den uka som står under feltet."),
        ("Stiplet blå", "Bestilt, ikke sendt. Ikke garantert."),
        ("Gul kant", "Nå. Den eneste varme fargen, på alle flater."),
    ]
    for a_, b_ in rows:
        d.text(x, y, a_, size=14, w=500)
        d.text(x + 130, y, b_, size=14, fill=KULL2)
        y += 23
    d.text(50, 930, "Demodata: Spill 17, Sara, Grossist. Tallene kommer fra simuleringen.", size=13, fill=KULL2)
    d.text(50, 950, "Målestokken går ett hakk ned når Restordre og På vei vokser, og den står alltid på tegningen.", size=13, fill=KULL2)
    d.save()


# ---- 06 ----

def skjerm_A(d):
    w = 11
    spillskjerm(d, w, GROSSIST, GROSSIST["kost_sum"][w - 1])
    malestokk(d, 22, 210, K)
    regnestykke(d, 578, w, GROSSIST)
    d.rect(16, 616, 92, 58, fill=HVIT, stroke=KULL, sw=1.4)
    d.text(30, 652, "Ordre", size=14, fill=KULL2)
    knapp(d, 120, 616, 254, 58, "Skriv inn en ordre", fs=16, enabled=False)
    venterad(d, 712)


def setestatus(d, y, rad):
    for navn, rolle, st, sterk in rad:
        d.text(16, y, f"{navn}, {rolle}", size=14)
        d.text(374, y, st, size=14, w=500 if sterk else 400, fill=KULL if sterk else KULL2, a="end")
        d.line(16, y + 9, 374, y + 9, stroke=GRID, sw=0.7)
        y += 30
    return y


def skjerm_C(d):
    w = 11
    spillskjerm(d, w, GROSSIST, GROSSIST["kost_sum"][w - 1], new=24, bekreftet=True)
    regnestykke(d, 578, w, GROSSIST, new=24)
    d.line(16, 608, 374, 608, stroke=LINJE, sw=0.7)
    d.text(16, 634, "Ordre 24 er sendt. Den kan ikke endres.", size=14, w=500)
    setestatus(d, 668, [("Ida", "Detaljist", "har bestilt", False), ("Mikkel", "Distributør", "har bestilt", False),
                        ("Sara", "Grossist", "har bestilt (deg)", False), ("Jonas", "Fabrikk", "venter, 3 min", True)])
    d.text(16, 806, "Uka går videre når Jonas har bestilt.", size=13, fill=KULL2)


def skjerm_D(d):
    w = 12
    S = GROSSIST
    spillskjerm(d, w, S, S["kost_sum"][w - 1])
    d.line(16, 552, 374, 552, stroke=LINJE, sw=0.7)
    d.text(16, 578, "Uke 11 er over", size=15, w=500)
    rows = [("Levering inn", f"{S['levering'][w - 1]}"), ("Ordre inn", f"{S['innkommende_ordre'][w - 1]}"),
            ("Sendt videre", f"{sendt(S, w)}"),
            ("Restordre", f"{S['restordre'][w - 2]} blir {S['restordre'][w - 1]}")]
    y = 606
    for a_, b_ in rows:
        d.text(16, y, a_, size=14, fill=KULL2)
        d.text(374, y, b_, size=14, w=500, a="end")
        d.line(16, y + 8, 374, y + 8, stroke=GRID, sw=0.7)
        y += 28
    d.text(16, y + 12, "Kanten flytter seg én uke. Feltene rykker fram.", size=13, fill=KULL2)
    knapp(d, 16, y + 28, 358, 48, "Hopp over", primar=False, fs=15)


def skjerm_E(d):
    w = 14
    S = S17["Fabrikk"]
    topp(d, w, S["kost_sum"][w - 1], "Jonas, Fabrikk")
    snitt(d, XNOW, OY, K, w, S, **MOD)
    kurve(d, XNOW, Y0, K, STEP, w, S, x_min=46, ki_uker=(12, 13), fs=14)
    na_kant(d, XNOW, OY - 50, Y0 + 20 * K + 2)
    net = netto(S)[w - 1]
    d.text(XNOW + 8, Y0 - net * K + 4, tegn(net), size=13, w=600)
    d.text(XNOW - 6, Y0 + 18, "Skravert: KI, Uke 12 og 13", size=13, w=500, a="end")
    d.line(16, 552, 374, 552, stroke=LINJE, sw=0.7)
    y = d.wrap(16, 578, "Du svarte ikke på 24 t. En KI-spiller har bestilt for deg i Uke 12 og 13.", 358, size=15, lh=21, w=500)
    y = d.wrap(16, y + 3, "Skravert stolpe i kurven er KI-spillerens ordre. Gruppa fortsatte uten deg.", 358, size=13, fill=KULL2)
    knapp(d, 16, y + 10, 358, 56, "Ta tilbake setet", fs=16)
    y += 90
    d.text(16, y, "De andre ser:", size=13, fill=KULL2)
    d.text(112, y, "Fabrikk: KI-spiller, Jonas borte", size=13)
    d.wrap(16, y + 22, "Mens uka venter står spillet på Pause. Etter 24 t uten svar overtar en KI-spiller.", 358, size=13, fill=KULL2)


def skjerm_F(d):
    F = FX["spill17"]
    d.text(16, 96, kr(F["kjedekost"], enhet=False), size=50, w=600)
    d.text(16, 124, "kr, hele kjeden. Spillet er over.", size=16, w=500)
    d.wrap(16, 156, "Det er dette tallet gruppa har spilt om. Ikke ditt ledd alene.", 340, size=14, fill=KULL2)
    # fire haller i rekke, samme skala
    y = 210
    kmax = 258 / max(F["kost_per_rolle"].values())
    for r in ROLES:
        v = F["kost_per_rolle"][r]
        deg = r == "Grossist"
        d.text(16, y, r + (" (deg)" if deg else ""), size=14, w=500 if deg else 400)
        d.text(374, y, kr(v, enhet=False), size=15, w=500 if deg else 400, a="end")
        d.rect(16, y + 8, v * kmax, 12, fill=SKYGGE if not deg else KULL, crisp=True)
        y += 52
    d.line(16, y - 6, 374, y - 6, stroke=LINJE, sw=0.7)
    # kurven er ferdig, kanten står i siste uke
    S = GROSSIST
    w = 36
    y += 8
    kk = 2.0
    y0 = y + 66
    kurve(d, 364, y0, kk, 9, w, S, x_min=40, ytop=30, ybot=40, grid=20, yetiketter=True, ordre=True, siste_blaa=0, fs=14)
    na_kant(d, 364, y0 - 30 * kk - 4, y0 + 40 * kk + 2)
    y += 126
    d.text(16, 736, "Hva skjedde? Det finner dere ut i Debriefen.", size=14)
    knapp(d, 16, 752, 358, 58, "Videre til Debrief", fs=16)


def spill06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Modell: spilldynamikk",
            "Seks telefonruter fra Uka åpner til Spillet slutter. Modellen og kurven er de samme gjennom hele spillet.")
    s = 0.82
    pw = 390 * s
    gap = (2100 - 80 - 6 * pw) / 5
    screens = [
        (skjerm_A, "Uka åpner", "Levering 4 har gått inn over terskelen. Hullet er 13. To tall ved kanten: det som kom, det som ble bestilt."),
        (skjerm_B, "Beslutningen: 24 med 16 på vei", "Stiplet stabel i felt Uke 15 mens du taster. Regnestykket står rett over knappen. Ingen fasit."),
        (skjerm_C, "Bekreftet, venter på de andre", "Stabelen fylles og låses. Du ser hvem det venter på og hvor lenge, med Rolle og navn."),
        (skjerm_D, "Uka går videre", "Kanten flytter seg. Maks 2 sekunder, kan hoppes over. Fire linjer forteller hva som endret hullet."),
        (skjerm_E, "Jonas er borte", "Pause, så KI overtar. KI er merket i tekst og med skravur. Jonas kan alltid ta tilbake setet."),
        (skjerm_F, "Spillet slutter", "Kjedens totalkostnad kommer først, så per Rolle, så Debrief. Tidsaksen viser først nå en slutt."),
    ]
    d.text(40, 62, "Én tegning, uke for uke.", size=38, w=600)
    for i, (fn, tittel, note) in enumerate(screens):
        x = 40 + i * (pw + gap)
        d.text(x, 110, tittel, size=16, w=600)
        telefon(d, x, 124, s)
        fn(d)
        d.close()
        d.wrap(x, 124 + 844 * s + 24, note, pw, size=14, lh=20, fill=KULL2)
    y = 124 + 844 * s + 110
    d.line(40, y, 2060, y, stroke=LINJE, sw=0.7)
    y += 42
    d.wrap(40, y, "Hva spilleren lærer av å se grafen uke for uke", 320, size=26, w=600, lh=33)
    d.wrap(420, y - 4, "Først er tegningen stille: søyla står, feltene er like. Så går søyla ned, hullet åpner seg, og kurven under gjør nøyaktig det samme, til samme dybde. Feltene vokser mens hullet ennå vokser, fordi det du bestiller nå tidligst kommer om fire uker. Når det kommer, går kurven fra skravur til flate og søyla reiser seg, og etter hvert ser du på feltene før du ser på hullet.", 1590, size=22, lh=35)
    d.text(40, 1168, "Demodata: Spill 17. Skjerm E er Jonas, Fabrikk, med illustrert KI-periode.", size=13, fill=KULL2)
    d.save()


# ---- 10 ----

INNSIKT = {
    5: ("Alt ser likt ut", "Søyla er 12, feltene er 4, 4 og 4. Posisjonen er 24, som den har vært. Ingen bevegelse å reagere på. Spørsmålet er hva denne tegningen skal være."),
    11: ("Hullet åpner seg", "Posisjonen har falt fra 24 til 3. Det du bestiller nå, kommer tidligst i Uke 15. Hullet du ser er 13, men hvor stort er det da, med det som allerede er på vei?"),
    18: ("Hullet er dypt, feltene er fulle", "Hullet er 38, men 80 står ute. Det er posisjon 42, den høyeste så langt. Hullet ber om mer. Hva har du allerede bedt om, og hva koster det når det kommer?"),
    29: ("Alt kom", "Søyla er 30: 15,00 kr per uke. Ordrene dine er nede på 2. Du kjenner igjen svingningen, nå med motsatt fortegn. Hva skal du be om når lite er på vei og mye står inne?"),
}


def p_merke(d, x, y, s):
    d.text(x, y, s, size=14, w=600, fill=KULL)


def pedagogikk10():
    d = Doc("10-pedagogikk", 2000, 1400, "Modell: grafgrammatikk",
            "Samme snitt og samme kurve for Sara ved Uke 5, 11, 18 og 29, samme målestokk, med prinsippene merket, og sammenligning med simulert referanse etter Debriefen.")
    S = GROSSIST
    d.text(40, 58, "Samme tegning, fire uker.", size=38, w=600)
    d.text(560, 44, "Samme målestokk i alle ruter og på alle rader: 10 enheter er like høye i modellen og i kurvene.", size=15)
    d.text(560, 66, "Sara, Grossist, Spill 17. Demodata. Gul kant er nå. Alt her er hens egne tall.", size=15, fill=KULL2)

    x_lab = 40
    x0 = 232
    cw = 438
    k = 2.8
    step = 7
    oy = 300
    y_k = 526      # null i kurven
    ybase = 756    # null i inn og ut
    y_r = 806      # regnestykke

    d.text(x_lab, 150, "Snittet", size=17, w=600)
    y = d.wrap(x_lab, 174, "P3: Det som er på vei blir glemt.", 170, size=14, w=600, lh=19)
    y = d.wrap(x_lab, y + 6, "P8: Restordre koster dobbelt.", 170, size=14, w=600, lh=19)
    d.wrap(x_lab, y + 6, "Hvor enhetene er. Hullet og feltene står i samme tegning, så Posisjon kan telles. Skravert koster 1,00 per enhet, hvitt 0,50.", 170, size=13, fill=KULL2, lh=18)

    d.text(x_lab, y_k - 60, "Kurven", size=17, w=600)
    y = d.wrap(x_lab, y_k - 36, "P2: Forsinkelse.", 170, size=14, w=600, lh=19)
    d.wrap(x_lab, y + 4, "Stolper er egne ordrer, flate og skravur er netto Lager. Stolpene vokser, kurven svarer fire uker senere.", 170, size=13, fill=KULL2, lh=18)

    d.text(x_lab, ybase - 70, "Inn og ut", size=17, w=600)
    y = d.wrap(x_lab, ybase - 46, "P1: Lager er en opphopning.", 170, size=14, w=600, lh=19)
    d.wrap(x_lab, y + 2, "Heltrukket er Levering, stiplet er innkommende ordre. Arealet mellom er endringen i Lager.", 170, size=13, fill=KULL2, lh=17)

    d.text(x_lab, y_r + 44, "Regnestykket", size=17, w=600)
    d.wrap(x_lab, y_r + 66, "Innsikt for neste ordre, uten fasit.", 170, size=13, fill=KULL2, lh=18)

    weeks = [5, 11, 18, 29]
    for j, w in enumerate(weeks):
        cx = x0 + j * cw
        xnow = cx + 228
        tit, ins = INNSIKT[w]
        d.text(cx, 118, f"Uke {w}", size=24, w=600)
        d.text(cx + 92, 118, tit, size=15, fill=KULL2)
        if j:
            d.line(cx - 12, 100, cx - 12, 930, stroke=GRID, sw=0.7)

        snitt(d, xnow, oy, k, w, S, A=150, D=50, H=30, c=40, c2=28, f=33, g=6, dv=24, fs=13)
        net = netto(S)[w - 1]
        kurve(d, xnow, y_k, k, step, w, S, x_min=cx + 22, fs=12, ytop=30, ybot=40, grid=20)
        d.text(xnow + 7, y_k - net * k + 4, tegn(net), size=13, w=600)
        if w >= 18:
            d.text(xnow - (w - 1 + 1) * step + 2, y_k - 12 * k - 5, "Lager", size=12, fill=KULL2)
        inn_ut(d, xnow, ybase, k, step, w, S, x_min=cx + 22, ymax=30)
        na_kant(d, xnow, 192, ybase + 2)
        prev = {5: 1, 11: 5, 18: 11, 29: 18}[w]
        inn = sum(S["levering"][prev:w])
        ut = sum(S["innkommende_ordre"][prev:w])
        n0 = netto(S)[prev - 1]
        n1 = netto(S)[w - 1]
        d.text(xnow + 7, ybase - 36, f"Fra Uke {prev}:", size=12, fill=KULL2)
        d.text(xnow + 7, ybase - 19, f"inn {inn}, ut {ut}", size=13)
        d.text(xnow + 7, ybase - 2, f"{tegn(n0)} blir {tegn(n1)}", size=13, w=600)

        y = y_r + 22
        lag, res, vei = S["lager"][w - 1], S["restordre"][w - 1], S["paa_vei"][w - 1]
        d.text(cx, y, f"{lag} − {res} + {vei} = {lag - res + vei}", size=24, w=600)
        d.text(cx, y + 19, "Lager − Restordre + På vei = Posisjon", size=12, fill=KULL2)
        d.text(cx + 300, y, f"Ordre {S['ordre'][w - 1]}", size=15, w=500, fill=ORDRE)
        d.wrap(cx, y + 43, ins, cw - 42, size=14, lh=20)

    # etter Debriefen
    yb = 950
    d.line(40, yb, 1960, yb, stroke=KULL, sw=1)
    yb += 12
    d.text(40, yb + 26, "Etter Debriefen", size=20, w=600)
    d.wrap(40, yb + 50, "Disse grafene er låst i Klassespillet. I Replay er de åpne.", 170, size=14, lh=20, fill=KULL2)

    # sammenligning
    R = FX["bare_sara_teller_paa_vei"]
    A_ = FX["alle_teller_paa_vei"]
    x1 = 232
    kk = 2.7
    y0 = yb + 170
    stp = 12.4
    xr = x1 + 36 * stp + 28
    d.text(x1, yb + 22, "Samme kjede, Sara regner med alt på vei", size=17, w=600)
    d.text(x1, yb + 42, "P3, P5. Simulert. Viser sammenhengen, ikke en fasit.", size=13, fill=KULL2)
    net = netto(S)
    netR = netto(R["serier"]["Grossist"])
    xs = [x1 + 28 + i * stp for i in range(37)]
    for v in range(-40, 31, 20):
        yy = y0 - v * kk
        d.line(x1 + 28, yy, x1 + 28 + 36 * stp, yy, stroke=GRID if v else KULL, sw=0.7 if v else 1)
        d.text(x1 + 22, yy + 4, tegn(v), size=12, fill=KULL2, a="end")
    d.path(path_of(steg(xs, [y0 - v * kk for v in net])), stroke=KULL, sw=1.6)
    d.path(path_of(steg(xs, [y0 - v * kk for v in netR])), stroke=ORDRE, sw=1.6, dash="5 3")
    d.text(xs[25], y0 - net[27] * kk - 8, "Spill 17", size=13, w=500, a="middle")
    d.text(xs[33], y0 - netR[32] * kk - 8, "Simulert", size=13, w=500, fill=ORDRE, a="middle")
    ay = y0 + 40 * kk + 3
    for i in (1, 5, 10, 15, 20, 25, 30, 36):
        d.text(x1 + 28 + (i - 0.5) * stp, ay + 14, i if i != 1 else "Uke 1", size=12, fill=KULL2, a="middle")
    t = xr + 8
    for yy_, lab, a_, b_ in [
        (yb + 72, "Grossist", kr(FX["spill17"]["kost_per_rolle"]["Grossist"], False), kr(R["kost_per_rolle"]["Grossist"], False)),
        (yb + 142, "Kjeden", kr(FX["spill17"]["kjedekost"], False), kr(R["kjedekost"], False)),
        (yb + 212, "Forsterkning", faktor(FX["spill17"]["forsterkning"]["Grossist"]), faktor(R["forsterkning"]["Grossist"])),
    ]:
        d.text(t, yy_, lab, size=13, fill=KULL2)
        d.text(t, yy_ + 20, a_, size=17, w=500)
        d.text(t, yy_ + 38, f"{b_} simulert", size=13, fill=ORDRE, w=500)

    # forsterkning, fire linjer
    x2 = 866
    st2 = 8.6
    px = x2 + 20
    d.text(x2, yb + 22, "Alle fire Rollers ordre", size=17, w=600)
    d.text(x2, yb + 42, "P4, P5, P6. Hvert ledd ser bare ordrene nedstrøms.", size=13, fill=KULL2)
    y2 = yb + 362
    k2 = 8.4
    for v in (0, 10, 20, 30):
        d.line(px, y2 - v * k2, px + 36 * st2, y2 - v * k2, stroke=GRID if v else KULL, sw=0.7 if v else 1)
        d.text(px - 5, y2 - v * k2 + 4, v, size=12, fill=KULL2, a="end")
    rolle_linjer(d, px, y2, k2, st2, 36, demand=S17["demand"])
    F_ = FX["spill17"]["forsterkning"]
    wx = lambda i: px + (i - 0.5) * st2
    d.text(wx(18) + 8, y2 - 31 * k2 + 2, f"Fabrikk {faktor(F_['Fabrikk'])}", size=13, w=600)
    d.text(wx(11) - 6, y2 - 24 * k2, f"Grossist {faktor(F_['Grossist'])}", size=13, w=500, a="end")
    d.line(wx(14), y2 - 22 * k2, wx(13), y2 - 28 * k2 + 3, stroke=KULL2, sw=0.6)
    d.text(wx(13), y2 - 28 * k2, f"Distributør {faktor(F_['Distributør'])}", size=13, w=500, a="end")
    d.line(wx(24), y2 - 9 * k2, wx(25.5), y2 - 15.5 * k2, stroke=KULL2, sw=0.6)
    d.text(wx(25.5), y2 - 16 * k2, f"Detaljist {faktor(F_['Detaljist'])}", size=13, w=500)
    d.line(wx(32), y2 - 8 * k2, wx(32), y2 - 12 * k2, stroke=KULL2, sw=0.6)
    d.text(wx(36), y2 - 12.5 * k2, "Kundene: 4, så 8", size=13, w=600, a="end")
    d.text(px, y2 + 16, "Uke 1", size=12, fill=KULL2)
    d.text(px + 36 * st2, y2 + 16, 36, size=12, fill=KULL2, a="end")

    # hjelpegrad
    x3 = 1210
    d.text(x3, yb + 22, "Hjelpegrad: samme tegning, to tilstander", size=17, w=600)
    d.text(x3, yb + 42, "Klassespillet viser nå. Replay viser også regelen din over tid.", size=13, fill=KULL2)
    w = 11
    k3 = 2.4
    y3 = yb + 204
    xa = x3 + 196
    d.text(x3, yb + 76, "Klassespill, Uke 11", size=14, w=600)
    kurve(d, xa, y3, k3, 14, w, S, x_min=x3 + 26, fs=12, ytop=30, ybot=20, grid=20)
    na_kant(d, xa, y3 - 30 * k3, y3 + 20 * k3 + 2)
    y_ = d.wrap(x3, y3 + 20 * k3 + 36, "Snitt, kurve og regnestykke for denne uka. Du ser ikke din egen Posisjon over tid.", 210, size=13, fill=KULL2, lh=18)
    RP = FX["replay_sara"]["serier"]["Grossist"]
    wr = 14
    xb = x3 + 416
    x3b = x3 + 240
    d.text(x3b, yb + 76, "Replay, Uke 14", size=14, w=600)
    kurve(d, xb, y3, k3, 11, wr, RP, x_min=x3b + 16, fs=12, ytop=30, ybot=20, grid=20, pos=True)
    na_kant(d, xb, y3 - 30 * k3, y3 + 20 * k3 + 2)
    ps = posisjon(RP)
    d.text(xb + 6, y3 - ps[wr - 1] * k3 + 4, f"{ps[wr - 1]}", size=13, w=600, fill=ORDRE)
    d.text(x3b + 22, y3 - 30 * k3 - 4, "Posisjon, blå linje", size=13, w=500, fill=ORDRE)
    d.wrap(x3b, y3 + 20 * k3 + 36, "Samme grammatikk pluss Posisjon. Tilfeldig etterspørsel, tre KI-spillere. Ikke like for like.", 210, size=13, fill=KULL2, lh=18)

    # P7
    x4 = 1700
    d.text(x4, yb + 22, "P7: Rolig må til også", size=17, w=600)
    yy = d.wrap(x4, yb + 48, "Å telle det som er på vei er ikke nok. I simuleringen ga en regel som jaget siste ordre for hardt Fabrikk 12×, høyere enn Spill 17.", 250, size=14, lh=20)
    f7 = A_["forsterkning"]["Fabrikk"]
    yy = d.wrap(x4, yy + 10, f"Simulert referanse med rolig regel for alle fire: Kjeden {kr(A_['kjedekost'], False)}, Fabrikk {faktor(f7)}. Regelen er valgt for å illustrere, ikke som fasit.", 250, size=14, lh=20, fill=KULL2)
    d.wrap(x4, yy + 10, "P6: Nesten alle 60 grupper svinger likt. Spørsmålet er hvorfor det skjedde, ikke om du hadde rett.", 250, size=14, lh=20, w=500)
    d.save()
