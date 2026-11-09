"""Landing, lærerflater, studenthjem og kontaktark."""
from modell import *  # noqa: F403

G = GROSSIST
K = FX["klasse"]
F = FX["spill17"]


def felt(d, x, y, w, lab, val, h=38, fs=15):
    d.text(x, y, lab, size=13, fill=KULL2)
    d.rect(x, y + 6, w, h, fill=HVIT, stroke=LINJE, sw=0.9)
    d.text(x + 10, y + 6 + h / 2 + fs * 0.35, val, size=fs)


def rad(d, x, y, w, a, b, fs=14, bw=500):
    d.text(x, y, a, size=fs, fill=KULL2)
    d.text(x + w, y, b, size=fs, w=bw, a="end")
    d.line(x, y + 8, x + w, y + 8, stroke=GRID, sw=0.7)


def landing01():
    d = Doc("01-landing", 1440, 1200, "Modell: landingsside for faglærere",
            "Første skjermbilde med ett setes snitt og kurve, og starten av neste seksjon med lærerens plansnitt over 60 spill.")
    d.text(64, 56, "Modell", size=22, w=600)
    d.text(1376, 54, "Logg inn", size=15, w=500, a="end")
    y = d.wrap(64, 186, "Hele kjedeøvelsen for et kurs, fra Invitasjon til PDF-rapport.", 590, size=52, lh=60, w=600)
    y = d.wrap(64, y + 2, "Fire Roller, én forsyningskjede, ett tall per Uke. Studenten bestemmer, systemet regner. KI-spillere fyller tomme seter. Etterpå forklarer Debriefen hver students egne valg, med tall fra loggen.", 520, size=19, lh=29, fill=KULL2)
    knapp(d, 64, y + 18, 230, 56, "Be om lærertilgang", fs=17)
    knapp(d, 306, y + 18, 120, 56, "Logg inn", primar=False, fs=17)
    d.text(64, y + 106, "For klasser på rundt 250 studenter. På norsk.", size=15, fill=KULL2)
    # stor tegning: ett sete
    w = 18
    k = 3.3
    xnow = 1020
    oy = 362
    y0 = 584
    snitt(d, xnow, oy, k, w, G, A=270, D=90, H=56, c=70, c2=44, f=40, g=8, dv=34, fs=15, theta=24)
    kurve(d, xnow, y0, k, 16, w, G, x_min=700, fs=14, ytop=20, ybot=40, grid=10)
    na_kant(d, xnow, oy - 110, y0 + 40 * k + 2, sw=2.2)
    d.text(xnow + 10, y0 + 38 * k + 5, "−38", size=16, w=600)
    d.text(xnow + 10, oy + 62, "På vei 80", size=16, w=500)
    d.text(xnow + 10, oy + 82, "ikke garantert", size=15, fill=KULL2)
    d.text(xnow + 10, y0 + 2, "Lager 0", size=15, fill=KULL2)
    d.text(xnow + 10, y0 + 22, "Restordre 38", size=15, fill=KULL2)
    d.text(xnow + 10, y0 + 42, "Posisjon 42", size=15, w=500)
    d.wrap(1180, y0 + 92, "Ett setes egen skjerm, ved Uke 18. Bare det setet selv kan se. Demodata.", 200, size=14, lh=20, fill=KULL2)

    # neste seksjon
    y = 800
    d.line(64, y, 1376, y, stroke=KULL, sw=1)
    d.text(64, y + 64, "Alle spillene på én skjerm.", size=38, w=600)
    d.wrap(64, y + 104, "Du ser hvor hvert spill står, hvem det venter på og hvor lenge. Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.", 470, size=17, lh=26)
    fakta = ["Kjører hele øvelsen, fra Invitasjon til PDF-rapport", "Studentlisten kommer fra Canvas-eksport",
             "KI-spillere fyller tomme seter, alltid merket", "Spilles på mobil, på norsk"]
    yy = y + 216
    for f in fakta:
        d.text(64, yy, f, size=16)
        d.line(64, yy + 11, 534, yy + 11, stroke=GRID, sw=0.8)
        yy += 34
    cols = 10
    pw, ph = 76, 70
    gx = 610
    gy = y + 40
    for i, g in enumerate(K["spill"][:50]):
        tomt(d, gx + (i % cols) * pw, gy + (i // cols) * ph, pw - 3, ph - 3, g, roller=("Grossist",), fs=11)
    d.save()


def klasse02():
    d = Doc("02-laerer-klasse", 1440, 1000, "Modell: Lag Klasse",
            "Skjema for navn, emnekode, Canvas-fil, e-postkolonne og Invitasjoner, ved siden av et plansnitt over 250 rader.")
    R_ = K["roster"]
    d.text(48, 62, "Lag Klasse", size=34, w=600)
    d.text(1392, 56, "Bård, Faglærer", size=14, fill=KULL2, a="end")
    x, w_ = 48, 500
    felt(d, x, 104, 310, "Navn", "class-of-1994")
    felt(d, x + 326, 104, 174, "Emnekode", "IBE160")
    d.text(x, 182, "Klasseliste fra Canvas-eksport", size=13, fill=KULL2)
    d.rect(x, 190, w_, 62, fill=HVIT, stroke=KULL2, sw=0.9, dash="4 3")
    d.text(x + 14, 216, "ibe160-h26-eksport.xlsx", size=15, w=500)
    d.text(x + 14, 238, f"{R_['paa_lista']} rader lest. Bytt fil", size=13, fill=KULL2)
    d.text(x, 282, "Hvilken kolonne er e-post?", size=13, fill=KULL2)
    cols = [("Navn", ["Sara Lie", "Noah Berg"]), ("SIS-ID", ["104417", "104418"]), ("E-post", ["sara.lie@student.no", "noah.berg@student.no"]), ("Seksjon", ["A", "B"])]
    cwid = [120, 80, 220, 80]
    cx = x
    for j, (h, vals) in enumerate(cols):
        sel = h == "E-post"
        d.rect(cx, 290, cwid[j], 96, fill=HVIT if sel else "none", stroke=KULL if sel else LINJE, sw=1.4 if sel else 0.7)
        d.text(cx + 8, 310, h, size=13, w=600 if sel else 400)
        for q, v in enumerate(vals):
            d.text(cx + 8, 338 + q * 24, v, size=13, fill=KULL if sel else KULL2)
        cx += cwid[j]
    d.text(x, 418, "E-post er valgt. Fire rader må rettes.", size=15, w=500)
    bad = [(37, "ingrid.moe@student"), (88, "jonas.dale.student.no"), (141, "amira@@student.no"), (203, "(tom celle)")]
    yy = 448
    for r_, v in bad:
        d.text(x, yy + 4, f"Rad {r_}", size=14, w=500)
        d.rect(x + 68, yy - 16, 300, 30, fill=HVIT, stroke=KULL, sw=1)
        d.text(x + 78, yy + 4, v, size=14)
        d.text(x + w_, yy + 4, "Hopp over", size=13, fill=KULL2, a="end")
        yy += 38
    gyldige = R_["paa_lista"] - R_["ugyldige_rader"]
    knapp(d, x, yy + 10, 310, 52, f"Send Invitasjoner til {gyldige}", fs=16)
    d.text(x + 324, yy + 32, "Gyldig i 14 dager.", size=14, fill=KULL2)
    d.text(x + 324, yy + 52, "Kan sendes på nytt.", size=14, fill=KULL2)
    yy += 96
    d.line(x, yy, x + w_, yy, stroke=KULL, sw=1)
    yy += 32
    d.text(x, yy, "Status etter utsending", size=20, w=600)
    yy += 30
    for a, b in [("Registrert", R_["registrert"]), ("Manuelt registrert", R_["manuelt_registrert"]), ("Uregistrert", R_["uregistrert"]),
                 ("Herav ugyldig adresse", R_["ugyldige_rader"])]:
        rad(d, x, yy, w_, a, b, fs=15)
        yy += 32
    pamin = R_["uregistrert"] - R_["ugyldige_rader"]
    knapp(d, x, yy + 2, 310, 46, f"Send påminnelse til {pamin}", primar=False, fs=15)
    d.text(x + 324, yy + 30, "Neste: Ny Klasseøkt", size=14, fill=KULL2)

    # plansnitt over 250 rader
    px, py = 620, 104
    d.text(px, py + 8, "Klasselista, rad for rad", size=20, w=600)
    d.text(px, py + 32, "Hver rute er én rad i fila. Rutene fylles etter hvert som studentene registrerer seg.", size=14, fill=KULL2)
    cell, gap = 35, 3
    cols_ = 20
    ugyldig = {37, 88, 141, 203}
    manuelt = {15, 190}
    # uregistrerte: de fire ugyldige og seks til, spredt fast
    ureg = ugyldig | {23, 64, 117, 158, 222, 241}
    assert len(ureg) == R_["uregistrert"] and len(manuelt) == R_["manuelt_registrert"]
    gy = py + 52
    for i in range(1, R_["paa_lista"] + 1):
        c, r_ = (i - 1) % cols_, (i - 1) // cols_
        x_, y_ = px + c * (cell + gap), gy + r_ * (cell + gap)
        if i in ugyldig:
            d.rect(x_, y_, cell, cell, fill=d.hatch, stroke=KULL, sw=1)
            d.rect(x_ + 4, y_ + 10, cell - 8, 15, fill=HVIT)
            d.text(x_ + cell / 2, y_ + 22, i, size=12, w=600, a="middle")
        elif i in ureg:
            d.rect(x_, y_, cell, cell, fill=HVIT, stroke=KULL2, sw=0.9)
        elif i in manuelt:
            d.rect(x_, y_, cell, cell, fill=SKYGGE_FLATE, stroke=KULL, sw=0.9)
            d.text(x_ + cell / 2, y_ + 23, "M", size=13, w=600, a="middle")
        else:
            d.rect(x_, y_, cell, cell, fill=SKYGGE_FLATE)
    rows_ = (R_["paa_lista"] + cols_ - 1) // cols_
    yl = gy + rows_ * (cell + gap) + 24
    d.rect(px, yl, 16, 16, fill=SKYGGE_FLATE)
    d.text(px + 22, yl + 13, f"Registrert {R_['registrert']}", size=14)
    d.rect(px + 160, yl, 16, 16, fill=SKYGGE_FLATE, stroke=KULL, sw=0.9)
    d.text(px + 182, yl + 13, f"Manuelt {R_['manuelt_registrert']}", size=14)
    d.rect(px + 290, yl, 16, 16, fill=HVIT, stroke=KULL2, sw=0.9)
    d.text(px + 312, yl + 13, f"Uregistrert {R_['uregistrert']}", size=14)
    d.rect(px + 450, yl, 16, 16, fill=d.hatch, stroke=KULL, sw=1)
    d.text(px + 472, yl + 13, f"Ugyldig adresse {R_['ugyldige_rader']}", size=14)
    d.wrap(px, yl + 54, "Du trenger ikke telle. Lista over hvem som mangler kan kopieres, og hver rute kan åpnes for å rette en adresse eller registrere manuelt.", 720, size=15, lh=23)
    d.text(48, 972, "Demodata. Plasseringen av uregistrerte rader er illustrert, antallene kommer fra klasselista.", size=13, fill=KULL2)
    d.save()


def kjedesnitt(d, x, y, W_):
    """Kjeden i oppriss med målsetting: forsinkelsene som arkitektens mål."""
    roles = ROLES[::-1]
    bw = 112
    gap = (W_ - 4 * bw) / 3
    h = 60
    base = y + 112
    # kunder helt til høyre uten etikett på etterspørsel her
    xs = []
    for i, r in enumerate(["Fabrikk", "Distributør", "Grossist", "Detaljist"]):
        xb = x + i * (bw + gap)
        xs.append(xb)
        d.rect(xb, base - h, bw, h, fill=HVIT, stroke=KULL, sw=1.2)
        d.line(xb, base - 12 * 3.2, xb + bw, base - 12 * 3.2, stroke=LINJE, sw=0.7)
        d.text(xb + bw / 2, base - 40, r, size=14, w=500, a="middle")
        d.text(xb + bw / 2, base - 14, "Lager 12", size=13, fill=KULL2, a="middle")
    d.line(x - 30, base, x + W_ + 30, base, stroke=KULL, sw=1.6)
    for i in range(3):
        xa = xs[i] + bw
        xb = xs[i + 1]
        mid = (xa + xb) / 2
        # to mål: frakt under, ordre over
        for yy, lab in [(base - 66, "ordre 2 uker"), (base + 22, "frakt 2 uker")]:
            d.line(xa + 4, yy, xb - 4, yy, stroke=KULL2, sw=0.7)
            d.line(xa + 4, yy - 4, xa + 4, yy + 4, stroke=KULL2, sw=0.7)
            d.line(xb - 4, yy - 4, xb - 4, yy + 4, stroke=KULL2, sw=0.7)
            d.text(mid, yy - 6 if yy < base else yy + 16, lab, size=13, fill=KULL2, a="middle")
    d.text(xs[0] + bw - 2, base + 26, "Produksjon 2 uker", size=13, fill=KULL2, a="end")


def klasseokt03():
    d = Doc("03-laerer-spill", 1440, 1100, "Modell: Klasseøkt",
            "Forhåndsutfylte standarder med kjeden tegnet i oppriss og målsatt, KI-modus, Debrief-modus, datoer, Labtimer og fordeling i 60 spill.")
    d.text(48, 62, "Ny Klasseøkt", size=34, w=600)
    d.text(320, 62, "class-of-1994, IBE160", size=15, fill=KULL2)
    d.text(1392, 50, "Klassisk er ferdig utfylt. Du kan lagre uten å endre noe.", size=15, w=500, a="end")
    knapp(d, 1132, 70, 260, 44, "Lagre Klasseøkten uendret", fs=14)

    d.text(48, 142, "Kjeden slik den er satt opp", size=20, w=600)
    kjedesnitt(d, 88, 150, 780)
    y = d.wrap(48, 342, "Kildene er uenige om forsinkelsene. Dette er produktets standard.", 800, size=14, fill=KULL2)
    # innstillinger
    x, w_ = 48, 400
    y = 396
    d.text(x, y, "Spillinnstillinger", size=20, w=600)
    y += 32
    for a, b in [("Startlager", "12"), ("I hvert ledd", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
                 ("Produksjonsforsinkelse", "2 uker"), ("Etterspørsel", "4, så 8 i Uke 5"), ("Lagerkost", "0,50"), ("Restordrekost", "1,00"),
                 ("Lengde", "36 uker"), ("Veiledede uker", "1 til 4"), ("Inaktivitetsgrense", "24 t")]:
        rad(d, x, y, w_, a, b)
        y += 36
    d.text(x, y + 6, "Studentene ser aldri lengden eller etterspørselen.", size=13, fill=KULL2)

    x2 = 490
    w2 = 400
    y = 396
    d.text(x2, y, "Spillere og Debrief", size=20, w=600)
    y += 30
    d.text(x2, y, "KI-modus", size=13, fill=KULL2)
    y += 6
    for i, o in enumerate(["LLM-spillere", "Regelspillere"]):
        d.rect(x2 + i * 200, y, 196, 38, fill=KULL if i == 0 else "none", stroke=KULL if i == 0 else LINJE, sw=0.9)
        d.text(x2 + i * 200 + 98, y + 24, o, size=14, fill=KALK if i == 0 else KULL, a="middle")
    y += 66
    d.text(x2, y, "Debrief-modus", size=13, fill=KULL2)
    y += 6
    for i, o in enumerate(["Gruppedebrief", "Individuell"]):
        d.rect(x2 + i * 200, y, 196, 38, fill=KULL if i == 0 else "none", stroke=KULL if i == 0 else LINJE, sw=0.9)
        d.text(x2 + i * 200 + 98, y + 24, o, size=14, fill=KALK if i == 0 else KULL, a="middle")
    y += 58
    d.rect(x2, y, 18, 18, fill=KULL)
    d.path(f"M{x2 + 4} {y + 9}L{x2 + 8} {y + 13}L{x2 + 14} {y + 5}", stroke=KALK, sw=1.6)
    d.text(x2 + 28, y + 14, "Obligatorisk", size=15, w=500)
    y += 52
    d.text(x2, y, "Datoer", size=20, w=600)
    y += 28
    for a, b in [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]:
        rad(d, x2, y, w2, a, b)
        y += 34
    y += 18
    d.text(x2, y, "Labtimer, Datalab A2", size=15, w=500)
    y += 24
    for t in ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]:
        d.text(x2, y, t, size=14)
        y += 22
    # fordeling
    x3 = 950
    d.text(x3, 142, "Fordeling", size=20, w=600)
    d.text(x3, 168, "240 studenter fordelt tilfeldig i 60 spill à 4.", size=15)
    cols, rows = 8, 8
    cw, ch = 54, 50
    names = "Ida Sara Mikkel Jonas".split()
    gy = 186
    for i in range(60):
        c, r_ = i % cols, i // cols
        xx, yy = x3 + c * cw, gy + r_ * ch
        d.rect(xx, yy, cw - 3, ch - 3, fill=HVIT, stroke=LINJE, sw=0.6)
        d.text(xx + 5, yy + 16, i + 1, size=11, fill=KULL2)
        for s in range(4):
            d.rect(xx + 5 + s * 10.5, yy + 26, 8.5, 8.5, fill=SKYGGE_FLATE, stroke=SKYGGE, sw=0.5)
    y = gy + 8 * ch + 10
    d.line(x3, y, x3 + 442, y, stroke=LINJE, sw=0.7)
    y += 26
    d.text(x3, y, "Spill 17, slik det er nå", size=14, w=500)
    y += 24
    for n, r_ in zip(names, ROLES):
        d.text(x3, y, n, size=14)
        d.text(x3 + 90, y, r_, size=14, fill=KULL2)
        y += 22
    y += 16
    knapp(d, x3, y, 150, 46, "Kjør på nytt", primar=False, fs=15)
    knapp(d, x3 + 162, y, 280, 46, "Bekreft fordelingen", fs=15)
    y += 72
    d.wrap(x3, y, "Sendes til studentene først når du bekrefter. Tomme seter fylles av KI-spillere, og det står på skjermen.", 440, size=14, lh=20, fill=KULL2)
    d.text(48, 1064, "Demodata. Standarden heter Klassisk.", size=13, fill=KULL2)
    d.save()


def hjem04():
    d = Doc("04-student-hjem", 1000, 900, "Modell: Sara på mobil",
            "To telefoner: registrering fra Invitasjon, og hjem under spill med seter, seks steg, frist og Labtimer.")
    # registrering
    d.text(40, 24, "Registrering fra Invitasjon", size=14, fill=KULL2)
    d.open("translate(40 36)")
    d.rect(0, 0, 390, 844, fill=KALK, stroke=KULL, sw=1, rx=30)
    d.text(16, 60, "Modell", size=18, w=600)
    y = d.wrap(16, 116, "Bård har invitert deg til IBE160.", 340, size=28, lh=34, w=600)
    y = d.wrap(16, y + 4, "Du spiller en Rolle i en forsyningskjede sammen med tre andre. Du bruker noen minutter per Uke, på mobil, når det passer gruppa.", 350, size=15, lh=22, fill=KULL2)
    y += 16
    felt(d, 16, y, 358, "Navn", "Sara Lie", h=46)
    y += 74
    felt(d, 16, y, 358, "E-post, fra Klasselisten", "sara.lie@student.no", h=46)
    y += 74
    felt(d, 16, y, 358, "Velg passord", "••••••••••••", h=46)
    y += 66
    d.text(16, y + 8, "Minst 10 tegn.", size=13, fill=KULL2)
    y += 26
    knapp(d, 16, y, 358, 56, "Opprett konto", fs=16)
    y += 88
    d.wrap(16, y, "Invitasjonen er gyldig i 14 dager. Spillet starter ti. 24. nov.", 358, size=14, lh=20, fill=KULL2)
    d.close()
    # hjem
    d.text(540, 24, "Hjem under spill", size=14, fill=KULL2)
    d.open("translate(540 36)")
    d.rect(0, 0, 390, 844, fill=KALK, stroke=KULL, sw=1, rx=30)
    d.text(16, 60, "Spill 17, Grossist", size=26, w=600)
    d.text(16, 82, "IBE160, class-of-1994", size=14, fill=KULL2)
    # handling
    d.rect(16, 100, 358, 104, fill=HVIT, stroke=KULL, sw=1.2)
    d.text(30, 130, "Spillet venter på deg: Uke 11", size=18, w=600)
    d.text(30, 152, "Jonas venter også, 3 min.", size=14, fill=KULL2)
    knapp(d, 30, 160, 330, 34, "Gå til Uke 11", fs=14)
    # setene som fire tomter, med nå-kant over Grossist
    y = 236
    d.text(16, y, "Setene", size=15, w=600)
    y += 12
    cw = 358 / 4
    seats = [("Ida", "Detaljist", "bestilt"), ("Sara", "Grossist", "venter"), ("Mikkel", "Distributør", "bestilt"), ("Jonas", "Fabrikk", "venter")]
    for i, (n, r_, st) in enumerate(seats):
        x = 16 + i * cw
        d.rect(x, y, cw - 3, 72, fill=HVIT, stroke=KULL if n == "Sara" else LINJE, sw=1.3 if n == "Sara" else 0.7)
        d.text(x + 7, y + 20, n + (" (deg)" if n == "Sara" else ""), size=13, w=600 if n == "Sara" else 500)
        d.text(x + 7, y + 40, r_, size=13, fill=KULL2)
        d.text(x + 7, y + 60, st, size=13, w=500 if st == "venter" else 400, fill=KULL if st == "venter" else KULL2)
    y += 104
    d.text(16, y, "Stegene", size=15, w=600)
    y += 8
    steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "Rapport"]
    y += 14
    na_kant(d, 22, y - 8, y + 12, sw=2.4)
    for i, s in enumerate(steps):
        yy = y + 6 + i * 28
        if i == 0:
            d.text(36, yy, s, size=15, w=600)
            d.text(374, yy, "pågår", size=14, w=500, a="end")
        else:
            d.text(36, yy, s, size=15, fill=KULL2)
            d.text(374, yy, "åpner etter forrige", size=13, fill=KULL2, a="end")
        d.line(36, yy + 9, 374, yy + 9, stroke=GRID, sw=0.7)
    y += 6 * 28 + 18
    rad(d, 16, y, 358, "Neste frist: Spillfrist", "ti. 8. des", fs=15)
    y += 36
    d.text(16, y, "Labtimer, Datalab A2", size=15, w=600)
    y += 24
    for t in ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]:
        d.text(16, y, t, size=14, fill=KULL)
        y += 20
    d.close()
    d.text(40, 894, "Demodata. Telefonene er i 390×844-skala.", size=12, fill=KULL2)
    d.save()


# ---- 09 kontaktark ----

TW, TH = 300, 186


def tom(d, x, y, tittel, linje):
    d.rect(x, y, TW, TH, fill=HVIT, stroke=LINJE, sw=0.8)
    d.text(x, y + TH + 22, tittel, size=15, w=600)
    d.wrap(x, y + TH + 42, linje, TW - 4, size=13, lh=18, fill=KULL2)


def lines(d, x, y, widths, lh=12, col=GRID, sw=3):
    for i, w_ in enumerate(widths):
        d.line(x, y + i * lh, x + w_, y + i * lh, stroke=col, sw=sw)


def t_reg(d, x, y):
    d.text(x + 14, y + 26, "Bård har invitert deg", size=14, w=600)
    for i in range(3):
        d.rect(x + 14, y + 42 + i * 34, TW - 28, 26, fill="none", stroke=LINJE, sw=0.8)
    knapp(d, x + 14, y + 146, TW - 28, 28, "Opprett konto", fs=12)


def t_login(d, x, y):
    d.text(x + 14, y + 40, "Logg inn", size=20, w=600)
    for i in range(2):
        d.rect(x + 14, y + 56 + i * 36, TW - 28, 28, fill="none", stroke=LINJE, sw=0.8)
    knapp(d, x + 14, y + 134, 120, 30, "Logg inn", fs=12)


def t_regler(d, x, y):
    snitt(d, x + 150, y + 96, 2.2, 5, G, A=86, D=32, H=18, c=26, c2=18, f=20, g=4, dv=14, fs=11, labels=False, uker=False, tall=False)
    na_kant(d, x + 150, y + 36, y + 130)
    d.text(x + 14, y + 22, "Ett tall per Uke. Slik leser du tegningen.", size=12, w=500)
    d.text(x + 14, y + 172, "Skravert 1,00. Hvitt 0,50.", size=12, fill=KULL2)


def t_start(d, x, y):
    d.text(x + 14, y + 24, "Veiledede uker: første ordre", size=12, w=500)
    kurve(d, x + 200, y + 110, 3, 18, 4, G, x_min=x + 40, fs=10, ytop=12, ybot=0, grid=10, akse=False, yetiketter=False)
    na_kant(d, x + 200, y + 60, y + 116)
    d.text(x + 210, y + 80, "Prøv 4", size=12, w=500)
    knapp(d, x + 14, y + 140, TW - 28, 30, "Send ordre på 4", fs=12)


def t_replay(d, x, y):
    RP = FX["replay_sara"]["serier"]["Grossist"]
    kurve(d, x + 190, y + 104, 1.3, 7, 20, RP, x_min=x + 40, fs=10, ytop=45, ybot=20, grid=20, pos=True, yetiketter=False, akse=False)
    na_kant(d, x + 190, y + 40, y + 132)
    d.text(x + 14, y + 22, "Replay: Posisjon er åpnet", size=12, w=500)
    d.text(x + 196, y + 60, "Posisjon", size=12, fill=ORDRE, w=500)
    d.text(x + 14, y + 172, "Tre KI-spillere. Tilfeldig etterspørsel.", size=12, fill=KULL2)


def t_replay_g(d, x, y):
    RP = FX["replay_sara"]["serier"]["Grossist"]
    net_a, net_b = netto(G), netto(RP)
    st = 7.4
    x0 = x + 14
    y0 = y + 88
    k = 0.9
    d.line(x0, y0, x0 + 36 * st, y0, stroke=KULL, sw=0.8)
    d.path(path_of(steg([x0 + i * st for i in range(37)], [y0 - v * k for v in net_a])), stroke=KULL, sw=1.2)
    d.path(path_of(steg([x0 + i * st for i in range(34)], [y0 - v * k for v in net_b])), stroke=ORDRE, sw=1.2)
    d.text(x0, y + 22, "Klassespill og Replay, ikke like for like", size=12, w=500)
    d.text(x0, y + 172, "Replay er blått. Klassespill er kull.", size=12, fill=KULL2)


def t_test(d, x, y, kind):
    if kind == "fler":
        d.text(x + 14, y + 26, "Hva er Posisjonen?", size=13, w=600)
        for i, s in enumerate(["−13", "3", "16"]):
            d.rect(x + 14, y + 40 + i * 42, TW - 28, 34, fill="none", stroke=KULL if s == "3" else LINJE, sw=0.9)
            d.text(x + 24, y + 62 + i * 42, s, size=13)
    elif kind == "tegne":
        d.text(x + 14, y + 26, "Tegn Lager når inn og ut er gitt", size=13, w=600)
        x0, st, y0 = x + 24, 18, y + 110
        d.line(x0, y0, x0 + 14 * st, y0, stroke=KULL, sw=0.9)
        vals = [12, 12, 10, 4, -3, -9, -13]
        for i, v in enumerate(vals):
            d.rect(x0 + i * st + 5, y0 - v * 3 if v > 0 else y0, 8, abs(v) * 3, fill=SKYGGE_FLATE if v > 0 else d.hatch, stroke=KULL, sw=0.5)
        d.line(x0 + 7 * st, y + 40, x0 + 7 * st, y + 170, stroke=NA, sw=1.4)
        d.text(x0 + 7 * st + 8, y + 58, "Dra søyler", size=12, fill=KULL2)
    else:
        d.text(x + 14, y + 26, "Forklar med egne ord", size=13, w=600)
        d.rect(x + 14, y + 40, TW - 28, 130, fill="none", stroke=LINJE, sw=0.8)
        lines(d, x + 26, y + 60, [230, 240, 200, 220, 120], lh=20)


def t_kivurd(d, x, y):
    d.text(x + 14, y + 26, "KI-vurdering", size=14, w=600)
    d.text(x + 14, y + 46, "KI-generert, kan ta feil. Teller ikke.", size=12, w=500)
    lines(d, x + 14, y + 68, [260, 240, 250, 180], lh=16)
    d.text(x + 14, y + 150, "Er aldri en karakter.", size=12, fill=KULL2)


def t_rapport(d, x, y):
    d.rect(x + 86, y + 12, 128, 164, fill=KALK, stroke=LINJE, sw=0.7)
    d.text(x + 96, y + 32, "Studentrapport", size=11, w=600)
    snitt(d, x + 160, y + 72, 1.2, 11, G, A=46, D=16, H=8, c=14, c2=10, f=7, g=2, dv=7, labels=False, uker=False, tall=False)
    kurve(d, x + 204, y + 140, 0.7, 3, 36, G, x_min=x + 96, ytop=30, ybot=40, grid=40, akse=False, yetiketter=False, siste_blaa=0)


def t_side(d, x, y):
    cols = 4
    for i, g in enumerate(K["spill"][:12]):
        tomt(d, x + 12 + (i % cols) * 70, y + 14 + (i // cols) * 54, 67, 50, g, tekst=False)


def t_laererhjem(d, x, y):
    d.text(x + 14, y + 26, "class-of-1994, IBE160", size=13, w=600)
    d.text(x + 14, y + 46, "Spillfrist ti. 8. des. 4 venter.", size=12, fill=KULL2)
    knapp(d, x + 14, y + 60, 130, 28, "Åpne Oversikt", fs=11)
    d.line(x + 14, y + 104, x + TW - 14, y + 104, stroke=GRID, sw=0.8)
    d.text(x + 14, y + 124, "Forrige: class-of-1993", size=12, fill=KULL2)
    d.text(x + 14, y + 144, "Ny Klasse, Ny Klasseøkt", size=12, fill=KULL2)


def t_klrapport(d, x, y):
    q = K["ferdige"]["kjedekost"]
    d.text(x + 14, y + 26, "Klasserapport", size=13, w=600)
    d.text(x + 14, y + 46, f"Median Kjeden {tusen(q['median'])} kr", size=12)
    x0, w_ = x + 14, TW - 28
    sc = lambda v: x0 + (v - q["min"]) / (q["max"] - q["min"]) * w_
    d.line(sc(q["min"]), y + 90, sc(q["max"]), y + 90, stroke=KULL, sw=0.8)
    d.rect(sc(q["q1"]), y + 78, sc(q["q3"]) - sc(q["q1"]), 24, fill=SKYGGE_FLATE, stroke=KULL, sw=0.7)
    d.line(sc(q["median"]), y + 74, sc(q["median"]), y + 106, stroke=KULL, sw=1.6)
    i = 0
    for lab, n in K["moenstre"].items():
        d.text(x + 14, y + 128 + i * 16, f"{n}", size=11, w=600)
        d.text(x + 38, y + 128 + i * 16, lab, size=10, fill=KULL2)
        i += 1


def t_innsikt(d, x, y):
    st = 7.6
    x0 = x + 12
    y0 = y + 150
    rolle_linjer(d, x0, y0, 3.8, st, 36, sw=0.9)
    d.line(x0, y0, x0 + 36 * st, y0, stroke=KULL, sw=0.8)
    na_kant(d, x0 + 18 * st, y + 20, y0 + 4)
    d.text(x + 14, y + 22, "Spill 17, uke for uke", size=12, w=500)
    d.text(x0 + 18 * st + 6, y + 38, "Uke 18", size=12, w=500)


def t_studentside(d, x, y):
    d.text(x + 14, y + 26, "Sara Lie, Grossist, Spill 17", size=13, w=600)
    steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
    for i, s in enumerate(steps):
        d.text(x + 14, y + 50 + i * 20, s, size=12, fill=KULL2)
        d.line(x + 110, y + 46 + i * 20, x + TW - 14, y + 46 + i * 20, stroke=GRID, sw=3)
    d.line(x + 110, y + 46, x + TW - 60, y + 46, stroke=SKYGGE, sw=3)


def t_plenum(d, x, y):
    cols = 5
    for i, g in enumerate(K["spill"][:20]):
        tomt(d, x + 8 + (i % cols) * 57, y + 8 + (i // cols) * 43, 54, 40, g, tekst=False, roller=("Fabrikk",))


def t_tverr(d, x, y):
    d.text(x + 14, y + 26, "Tverrklasse: Kjeden, median", size=12, w=500)
    fj = K["fjoraaret"]
    q = K["ferdige"]["kjedekost"]
    mx = fj["median_kjedekost"]
    for i, (lab, v) in enumerate([(fj["klasse"], fj["median_kjedekost"]), ("class-of-1994", q["median"])]):
        yy = y + 60 + i * 50
        d.text(x + 14, yy, lab, size=12, fill=KULL2)
        d.rect(x + 14, yy + 6, (TW - 90) * v / mx, 14, fill=SKYGGE_FLATE if i == 0 else SKYGGE, crisp=True)
        d.text(x + 14 + (TW - 90) * v / mx + 6, yy + 18, tusen(v), size=12, w=500)


def t_meld(d, x, y):
    d.text(x + 14, y + 26, "Meldinger", size=13, w=600)
    for i, s in enumerate(["Til Noah, Spill 2: Du er neste", "Til Oskar, Spill 10", "Til alle: Labtime torsdag"]):
        d.text(x + 14, y + 52 + i * 24, s, size=12, fill=KULL2)
        d.line(x + 14, y + 60 + i * 24, x + TW - 14, y + 60 + i * 24, stroke=GRID, sw=0.7)
    knapp(d, x + 14, y + 138, 130, 30, "Ny Melding", fs=12)


def t_testspill(d, x, y):
    snitt(d, x + 160, y + 80, 1.8, 7, G, A=70, D=28, H=14, c=22, c2=14, f=16, g=3, dv=12, fs=11, labels=False, uker=False, tall=False)
    na_kant(d, x + 160, y + 30, y + 112)
    d.text(x + 14, y + 22, "Testspill: du er Grossist, resten er KI", size=12, w=500)
    d.text(x + 14, y + 168, "Teller ikke i Klassen.", size=12, fill=KULL2)


def t_admin(d, x, y):
    d.text(x + 14, y + 26, "Admin-område", size=13, w=600)
    for i, s in enumerate(["Institusjoner", "Klasser", "Drift og feillogg"]):
        d.text(x + 14, y + 56 + i * 28, s, size=13)
        d.line(x + 14, y + 66 + i * 28, x + TW - 14, y + 66 + i * 28, stroke=GRID, sw=0.8)


def t_brukere(d, x, y):
    d.text(x + 14, y + 26, "Brukere og roller", size=13, w=600)
    for i, (n, r_) in enumerate([("Bård", "Faglærer"), ("Hjelpelærer 1", "Hjelpelærer"), ("Sara Lie", "Student"), ("Drift", "Admin")]):
        d.text(x + 14, y + 54 + i * 26, n, size=13)
        d.text(x + TW - 14, y + 54 + i * 26, r_, size=12, fill=KULL2, a="end")
        d.line(x + 14, y + 62 + i * 26, x + TW - 14, y + 62 + i * 26, stroke=GRID, sw=0.7)


def t_kikost(d, x, y):
    d.text(x + 14, y + 26, "KI-kostnad per Klasseøkt", size=13, w=600)
    bars = [g["ki_seter"] for g in K["spill"][:36]]
    x0, y0 = x + 14, y + 140
    for i, v in enumerate(bars):
        d.rect(x0 + i * 7.4, y0 - v * 30, 4, v * 30, fill=SKYGGE, crisp=True)
    d.line(x0, y0, x0 + 36 * 7.4, y0, stroke=KULL, sw=0.8)
    d.text(x0, y0 + 20, "KI-seter per spill. Demodata.", size=12, fill=KULL2)


def alle09():
    d = Doc("09-alle-sider", 2000, 1400, "Modell: alle andre sider",
            "Kontaktark over alle andre sider, gruppert per rolle.")
    d.text(40, 56, "Alle andre sider", size=34, w=600)
    d.text(380, 56, "Samme snitt, samme kurve, samme kant der det er data. Ellers tabell og tekst.", size=15, fill=KULL2)
    gridx = [40 + i * 324 for i in range(6)]
    student = [
        ("Invitasjon og registrering", "Fra e-post til konto, uten passordregler å lese.", t_reg),
        ("Logg inn", "E-post og passord. Glemt passord.", t_login),
        ("Regler før første ordre", "Tegningen forklarer seg selv, med kostnadene.", t_regler),
        ("Startoppgave", "Veiledede uker: prøv én ordre og se stabelen.", t_start),
        ("Replay", "Posisjon-kurven er åpnet. Tre KI-spillere.", t_replay),
        ("Replay-gjennomgang", "Klassespill og Replay. Ikke like for like.", t_replay_g),
        ("Individuell test: flervalg", "Regnestykket, med svar som kan forklares.", lambda d_, x, y: t_test(d_, x, y, "fler")),
        ("Individuell test: tegne og tabell", "Tegn Lager ut fra inn og ut. Materialbalansen testes.", lambda d_, x, y: t_test(d_, x, y, "tegne")),
        ("Individuell test: langsvar", "Forklar hvorfor, med egne tall.", lambda d_, x, y: t_test(d_, x, y, "lang")),
        ("KI-vurdering", "Teller ikke, er aldri karakter, merket.", t_kivurd),
        ("Studentrapport (PDF)", "Snitt, kurve og egne valg på papir.", t_rapport),
        ("Alle spill side om side", "Klassens tomter i Debriefen, uten kostnadsrangering.", t_side),
    ]
    laerer = [
        ("Lærerhjem", "Hva trenger oppmerksomhet nå.", t_laererhjem),
        ("Klasserapport", "Kvartiler og mønstre for hele Klassen.", t_klrapport),
        ("Spillinnsikt (uke for uke)", "Dra kanten gjennom ett spill.", t_innsikt),
        ("Studentside", "Én students steg og status.", t_studentside),
        ("Alle spill i plenum", "Tomtene alene, stort, for lerret.", t_plenum),
        ("Tverrklasse-statistikk", "Denne Klassen mot fjoråret.", t_tverr),
        ("Meldinger", "Til én, til ett spill eller til alle.", t_meld),
        ("Lærers testspill", "Spill selv mot KI-spillere.", t_testspill),
    ]
    admin = [
        ("Admin-område", "Institusjoner, Klasser, drift.", t_admin),
        ("Brukere og roller", "Hvem er hva.", t_brukere),
        ("KI-kostnad", "Per Klasseøkt.", t_kikost),
    ]
    row_h = 318
    y = 96
    d.text(40, y, "Student", size=20, w=600)
    y += 14
    for i, (t, l, fn) in enumerate(student):
        x = gridx[i % 6]
        yy = y + (i // 6) * row_h
        tom(d, x, yy, t, l)
        fn(d, x, yy)
    y += 2 * row_h + 6
    d.text(40, y, "Faglærer", size=20, w=600)
    y += 14
    for i, (t, l, fn) in enumerate(laerer):
        x = gridx[i % 6]
        yy = y + (i // 6) * row_h
        tom(d, x, yy, t, l)
        fn(d, x, yy)
    y2 = y + row_h
    d.text(gridx[2], y2 - 14, "Admin", size=20, w=600)
    for i, (t, l, fn) in enumerate(admin):
        x = gridx[2 + i]
        tom(d, x, y2, t, l)
        fn(d, x, y2)
    d.text(1960, 56, "Demodata", size=14, fill=KULL2, a="end")
    d.save()
