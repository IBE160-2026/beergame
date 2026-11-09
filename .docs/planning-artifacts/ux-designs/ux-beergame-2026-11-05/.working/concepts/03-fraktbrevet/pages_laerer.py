"""02 klasse, 03 klasseoekt, 08 oversikt: Lærerflatene som blanketter."""
from c03lib import *  # noqa: F403


def check(x, y, on=True, color=INK, s=20):
    o = R(x, y, s, s, "#fff" if False else "none", color, 1.5)
    if on:
        o += P(f"M{x + 3} {y + 3}L{x + s - 3} {y + s - 3}M{x + s - 3} {y + 3}L{x + 3} {y + s - 3}", "none", color, 2.6)
    return o


# ---------- 02 ----------
ROWS = [
    (1, "Aasen, Maria", "maria.aasen@stud.example.no", ""), (2, "Berg, Elias", "elias.berg@stud.example.no", ""),
    (3, "Dahl, Nora", "nora.dahl@stud.example.no", ""), (36, "Holm, Jakob", "jakob.holm@stud.example.no", ""),
    (37, "Holm, Lena", "lena.holm@stud", "mangler domene"), (38, "Haug, Emil", "emil.haug@stud.example.no", ""),
    (87, "Moen, Sofie", "sofie.moen@stud.example.no", ""), (88, "Myhre, Tor", "tor.myhre.stud.example.no", "mangler @"),
    (89, "Næss, Ella", "ella.naess@stud.example.no", ""), (141, "Rønning, Liv", "", "tom celle"),
    (203, "Sund, Maja", "maja.sund@stud.example,no", "komma i adressen"), (250, "Aas, Theo", "theo.aas@stud.example.no", ""),
]


def klasse():
    pg = Page("kla", "02-laerer-klasse.svg", 1440, 1000, "Fraktbrev: Faglærer lager Klasse",
              "Klasseblankett med navn, Canvas-fil, e-postkolonne, ugyldige rader, Invitasjoner og status.")
    r = FX["roster"]
    # venstre blankett
    x, y, w, h = 36, 30, 680, 940
    pg.add(pg.paper(x, y, w, h, CAN), tractor(x + 16, y + 18, h - 30, DESK))
    fx = x + 40
    fw = w - 56
    pg.add(T(fx, y + 54, "NY KLASSE", 34, "disp"))
    cy = y + 74
    pg.add(field(fx, cy, fw * .62, 70, "Navn på Klasse", "class-of-1994", size=25))
    pg.add(field(fx + fw * .62, cy, fw * .38, 70, "Emnekode", "IBE160", size=25))
    cy += 70
    pg.add(field(fx, cy, fw, 78, "Canvas-fil", "ibe160-canvas-eksport.xlsx", size=21))
    pg.add(T(fx + 8, cy + 74 - 40 - 0, "", 13))
    pg.add(plain_button(fx + fw - 136, cy + 24, 124, 40, "Bytt fil", INK, 15))
    cy += 78
    # kolonnevalg
    pg.add(R(fx, cy, fw, 108, "none", INK, 1.1), T(fx + 8, cy + 18, "E-POSTKOLONNE", 13, "lab", INK, ls=.5))
    pg.add(T(fx + fw - 8, cy + 18, "Vi fant denne selv. Sjekk at den stemmer.", 14, "nar", INK, "end"))
    cols = [("A", "Student", False), ("B", "ID", False), ("C", "SIS-pålogging", False), ("D", "E-post", True), ("E", "Seksjon", False)]
    cw = (fw - 16) / 5
    for i, (k, lb, on) in enumerate(cols):
        cx = fx + 8 + i * cw
        pg.add(R(cx, cy + 30, cw - 8, 66, CAN_L if on else "none", INK, 2.2 if on else 1))
        pg.add(check(cx + 8, cy + 40, on))
        pg.add(T(cx + 36, cy + 56, f"Kolonne {k}", 13, "nar"))
        pg.add(T(cx + 8, cy + 86, lb, 17 if len(lb) < 10 else 16, "labb"))
    cy += 108
    # oppsummering av fila
    cwh = fw / 3
    for i, (lb, v, c) in enumerate([("Rader lest", r["paa_lista"], INK), ("Gyldige", r["paa_lista"] - r["ugyldige_rader"], INK), ("Ugyldige", r["ugyldige_rader"], RED)]):
        pg.add(field(fx + i * cwh, cy, cwh, 72, lb, str(v), INK, c, 32))
    cy += 72
    # ugyldige
    pg.add(R(fx, cy, fw, 328, "none", INK, 1.1), T(fx + 8, cy + 20, "UGYLDIGE RADER: RETT DEM ELLER REGISTRER MANUELT", 13, "lab", INK, ls=.5))
    bad = [q for q in ROWS if q[3]]
    for i, (rad, nm, mail, why) in enumerate(bad):
        ry = cy + 32 + i * 72
        pg.add(L(fx, ry, fx + fw, ry, INK, .7))
        pg.add(T(fx + 10, ry + 25, f"Rad {rad}", 17, "typb", RED))
        pg.add(T(fx + 10, ry + 52, nm, 16, "labb"))
        pg.add(T(fx + 104, ry + 52, why, 15, "lab", RED))
        pg.add(T(fx + 92, ry + 25, mail or "(tom)", 15.5, "typ", INK))
        if i == 1:
            pg.add(T(fx + 232, ry + 48, "", 13))
        pg.add(plain_button(fx + fw - 186, ry + 16, 78, 40, "Rett", INK, 15))
        pg.add(plain_button(fx + fw - 102, ry + 16, 94, 40, "Manuelt", INK, 15))
    cy += 328
    # stempel
    pg.add(stamp_button(fx, cy + 14, fw, 96, "SEND 246 INVITASJONER", "Gyldig i 14 dager. Ugyldige rader venter til du har rettet dem.", True, 25, subsize=16))
    pg.add(plain_button(fx, cy + 120, fw, 42, "Se e-posten studentene får", INK, 15))
    pg.add(demo(fx, y + h - 8, INK))

    # listing paa endeloespapir
    lx, ly, lw, lh = 744, 30, 660, 470
    pg.add(pg.paper(lx, ly, lw, lh, REC), tractor(lx + 15, ly + 14, lh - 20, DESK), tractor(lx + lw - 15, ly + 14, lh - 20, DESK))
    ix, iw = lx + 34, lw - 68
    pg.add(T(ix, ly + 36, "Klasselista, slik vi leste den", 22, "disp"))
    pg.add(T(ix + 8, ly + 64, "RAD", 13, "lab") + T(ix + 60, ly + 64, "STUDENT", 13, "lab") + T(ix + 230, ly + 64, "E-POST (KOLONNE D)", 13, "lab"))
    for i, (rad, nm, mail, why) in enumerate(ROWS):
        ry = ly + 72 + i * 32
        pg.add(R(ix, ry, iw, 32, BLUE_L if i % 2 == 0 else REC))
        pg.add(T(ix + 8, ry + 22, str(rad), 15, "typ"), T(ix + 60, ry + 22, nm, 15, "typ"), T(ix + 230, ry + 22, mail or "(tom)", 15, "typb" if why else "typ", RED if why else INK))
        if why:
            ww = max(len(mail), 5) * 9 + 16
            pg.add(P(f"M{ix + 220} {ry + 17}C{ix + 220} {ry - 2} {ix + 232 + ww} {ry - 3} {ix + 232 + ww} {ry + 15}C{ix + 234 + ww} {ry + 34} {ix + 218} {ry + 34} {ix + 221} {ry + 12}", "none", RED, 1.8))
        if i in (2, 5, 8, 10):
            pg.add(T(ix + iw - 8, ry + 22, "", 13))
    # status: blaa kopi
    sx, sy, sw, sh = 744, 520, 660, 450
    pg.add(pg.paper(sx, sy, sw, sh, BLUE), tractor(sx + 15, sy + 14, sh - 20, DESK))
    ix = sx + 36
    iw = sw - 52
    pg.add(T(ix, sy + 44, "STATUS PÅ INVITASJONER", 24, "disp", NAVY))
    sent = r["paa_lista"] - r["ugyldige_rader"]
    aks = r["registrert"]
    utl = sent - aks
    cwh = iw / 3
    for i, (lb, v) in enumerate([("Sendt", sent), ("Akseptert", aks), ("Utløpt", utl)]):
        pg.add(field(ix + i * cwh, sy + 62, cwh, 84, lb, str(v), NAVY, NAVY, 40))
    cwh2 = iw / 2
    pg.add(field(ix, sy + 146, cwh2, 70, "Manuelt registrert", str(r["manuelt_registrert"]), NAVY, NAVY, 30))
    pg.add(field(ix + cwh2, sy + 146, cwh2, 70, "Uregistrert", str(r["uregistrert"]), NAVY, NAVY, 30))
    # 250 streker til skala
    ty = sy + 240
    pg.add(T(ix, ty, "HVER STREK ER EN RAD PÅ LISTA", 13, "lab", NAVY, ls=.5))
    tw = iw / 250
    for i in range(250):
        tx = ix + i * tw
        if i < aks:
            pg.add(L(tx, ty + 10, tx, ty + 46, NAVY, 1.3))
        elif i < aks + r["manuelt_registrert"]:
            pg.add(L(tx, ty + 10, tx, ty + 46, VIO, 1.3), C(tx, ty + 52, 1.6, VIO))
        else:
            pg.add(L(tx, ty + 34, tx, ty + 46, NAVY, 1.3))
    pg.add(T(ix, ty + 76, "Hel strek: registrert. Med prikk: manuelt. Kort strek: uregistrert.", 15, "nar", NAVY))
    pg.add(plain_button(ix, ty + 90, 300, 48, "Send 8 utløpte på nytt", NAVY, 16))
    pg.add(plain_button(ix + 312, ty + 90, iw - 312, 48, "Sett opp Klasseøkt", NAVY, 16, NAVY))
    pg.add(T(ix, sy + sh - 18, "Uregistrert: 8 utløpte og 2 ugyldige rader som ikke er rettet.", 15, "nar", NAVY))
    pg.save()


# ---------- 03 ----------
def okt():
    pg = Page("okt", "03-laerer-spill.svg", 1440, 1100, "Fraktbrev: Faglærer setter opp Klasseøkt",
              "Klasseøkt-blankett med forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling i 60 spill.")
    x, y, w, h = 36, 26, 930, 1048
    pg.add(pg.paper(x, y, w, h, CAN), tractor(x + 16, y + 18, h - 30, DESK))
    fx, fw = x + 40, w - 56
    pg.add(T(fx, y + 54, "KLASSEØKT", 36, "disp"))
    pg.add(T(fx, y + 80, "class-of-1994, IBE160. Spillinnstillinger: «Klassisk». Alt er forhåndsutfylt.", 17, "lab"))
    pg.add(stamp(pg, fx + fw - 104, y + 44, "KLASSISK", 20, -4))
    cy = y + 96

    def row(items, h_=90, size=28):
        nonlocal cy
        cw = fw / len(items)
        for i, (lb, v) in enumerate(items):
            pg.add(field(fx + i * cw, cy, cw, h_, lb, v, size=size))
        cy += h_

    row([("Startlager", "12"), ("I hvert ledd", "4 enheter"), ("Antall uker", "36"), ("Veiledede uker", "1-4")])
    row([("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"), ("Inaktivitetsgrense", "24 t")])
    pg.add(R(fx, cy, fw, 48, CAN_L, INK, 1.1))
    pg.add(T(fx + 10, cy + 31, "Kildene er uenige om forsinkelsene. 2 uker er produktets standard, og du kan endre den.", 17, "lab"))
    cy += 48
    row([("Etterspørsel", "4 til 8, uke 5"), ("Lagerkost", "0,50 kr"), ("Restordrekost", "1,00 kr"), ("Mønster", "Klassisk")], size=23)
    row([("Fordeling", "Tilfeldig"), ("Hva spillerne ser", "Eget Sete"), ("Debrief åpner", "Ved spillslutt"), ("Krav til Ordrer", "80 %")], size=23)
    # valg
    half = fw / 2
    for i, (lb, opts) in enumerate([("KI-modus", [("LLM-spillere", True), ("Regelbaserte spillere", False)]),
                                    ("Debrief-modus", [("Gruppedebrief", True), ("Personlig debrief", False)])]):
        ox = fx + i * half
        pg.add(R(ox, cy, half, 110, "none", INK, 1.1), T(ox + 7, cy + 18, lb.upper(), 13, "lab", ls=.5))
        for j, (t_, on) in enumerate(opts):
            pg.add(check(ox + 10, cy + 30 + j * 32, on, INK, 22), T(ox + 42, cy + 48 + j * 32, t_, 19, "labb" if on else "nar"))
    cy += 110
    # obligatorisk
    pg.add(R(fx, cy, fw, 92, CAN_L, INK, 2.2))
    pg.add(check(fx + 12, cy + 16, True, INK, 26))
    pg.add(stamp(pg, fx + 172, cy + 30, "OBLIGATORISK", 17, -2, VIO, ink=False))
    pg.add(T(fx + 12, cy + 74, "Klassespillet teller som gjort bare når studenten selv har bestilt i minst 80 % av ukene etter de Veiledede.", 17, "nar"))
    cy += 92
    # datoer
    pg.add(T(fx, cy + 28, "DATOER", 14, "labb", ls=.5))
    cy += 36
    row([("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")], 74, 19)
    cy += 14
    pg.add(stamp_button(fx, cy, fw, 104, "LAGRE KLASSEØKT", "Du kan lagre uten å endre noe. Fordelingen til høyre følger med.", True, 28, subsize=17))
    pg.add(demo(fx, y + h - 12, INK))

    # labtimer: fraktbrev paa siden
    sx, sw = 996, 408
    pg.add(T(sx, 54, "LABTIMER", 18, "disp", PALE), T(sx + sw, 54, "Datalab A2", 16, "lab", PALE, "end"))
    labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    for i, lb in enumerate(labs):
        ly = 68 + i * 50
        pg.add(R(sx, ly, sw, 46, BLUE, NAVY, .7) + T(sx + 12, ly + 30, lb, 21, "typb", NAVY) + T(sx + sw - 12, ly + 29, "Fjern", 15, "lab", NAVY, "end"))
    pg.add(plain_button(sx, 272, sw, 40, "Legg til Labtime", PALE, 15))
    pg.add(icon_clip(sx + sw / 2 - 22, 50, 44) if False else "")
    # fordeling
    py, ph = 334, 740
    pg.add(pg.paper(sx, py, sw, ph, PINK))
    pg.add(T(sx + 16, py + 40, "FORDELING", 24, "disp", PLUM))
    pg.add(T(sx + 16, py + 66, "240 studenter tilfeldig i 60 spill à 4", 19, "labb", PLUM))
    # 60 smaa grupper paa fire
    gy = py + 84
    cols, rows_ = 10, 6
    cw, ch = (sw - 32) / cols, 56
    for i in range(60):
        cx, cy2 = sx + 16 + (i % cols) * cw, gy + (i // cols) * ch
        hi = i + 1 == 17
        pg.add(R(cx + 1, cy2 + 1, cw - 2, ch - 2, PINK_L if not hi else CAN, PLUM, 1.8 if hi else .6))
        pg.add(T(cx + cw / 2, cy2 + 15, str(i + 1), 13, "lab", PLUM, "middle"))
        for j in range(4):
            pg.add(R(cx + 5 + j * 7.5, cy2 + 24, 6, 22, PLUM))
    ly = gy + rows_ * ch + 18
    pg.add(T(sx + 16, ly + 8, "EKSEMPEL: SPILL 17", 14, "labb", PLUM, ls=.5))
    for i, r in enumerate(ROLES):
        yy = ly + 20 + i * 42
        pg.add(L(sx + 16, yy, sx + sw - 16, yy, PLUM, .6))
        pg.add(icon_role(r, sx + 20, yy + 10, 22, PLUM), T(sx + 52, yy + 27, r, 18, "lab", PLUM), T(sx + sw - 20, yy + 28, NAMES[r], 20, "typb", CARBON, "end"))
    by = ly + 20 + 4 * 42 + 14
    pg.add(plain_button(sx + 16, by, 160, 56, "Kjør på nytt", PLUM, 17))
    pg.add(plain_button(sx + 186, by, sw - 202, 56, "Bekreft fordeling", VIO, 17, VIO))
    pg.save()


# ---------- 08 ----------
def fanerad_shape(x, y, w, h, fill, stroke=INK, sw=1):
    return P(f"M{x} {y + h}V{y + 8}l6 -8H{x + w - 6}l6 8V{y + h}z", fill, stroke, sw)


def fane(pg, g, x, base, w):
    st = g["status"]
    n = g["spill"]
    near = st == "venter" and g.get("ventet_timer", 0) >= 20
    kr = f'{g["kjedekost"]:,}'.replace(",", " ") + " kr"
    if st == "ferdig":
        h, fill, ink = 46, "#D8D6DF", INK
    elif st == "pågår":
        h, fill, ink = 62, BLUE, NAVY
    elif st == "pauset":
        h, fill, ink = 62, BLUE_L, NAVY
    else:
        h, fill, ink = (96, CAN, INK) if near else (80, CAN, INK)
    y = base - h
    o = fanerad_shape(x + 1, y, w - 2, h, fill, RED if near else INK, 2.6 if near else .8)
    o += T(x + 8, y + 22, str(n), 19, "typb", ink)
    if g["ki_seter"]:
        kx = x + w - 48
        o += R(kx, y + 7, 40, 18, "none", VIO if st != "pågår" else VIO, 1.2, 2, 'stroke-dasharray="3 2"') + T(kx + 20, y + 21, f'KI {g["ki_seter"]}', 13, "labb", VIO, "middle")
    if st == "ferdig":
        o += T(x + 8, y + 39, kr, 13.5, "nar", ink)
    elif st == "pågår":
        o += T(x + 8, y + 39, f'Uke {g["uke"]}', 13.5, "lab", ink) + T(x + 8, y + 56, kr, 13.5, "nar", ink)
    elif st == "pauset":
        o += icon_pause(x + 8, y + 28, ink, 12) + T(x + 24, y + 39, f'Uke {g["uke"]}', 13.5, "lab", ink) + T(x + 8, y + 56, "til 19:00", 13.5, "labb", ink)
    else:
        o += T(x + 8, y + 40, f'{g["navn"]}', 15, "labb", ink) + T(x + w - 8, y + 40, f'{g["ventet_timer"]} t', 15, "typb", RED if near else ink, "end")
        o += T(x + 8, y + 56, g["venter_paa"], 13.5, "nar", ink) + T(x + 8, y + 72, f'Uke {g["uke"]}', 13.5, "nar", ink)
        if near:
            o += T(x + 8, y + 89, "KI overtar om 1 t", 13.5, "labb", RED)
    return o


def trolley(pg, x, y, w, pitch, games):
    cols = 10
    tw = (w - 28) / cols
    rows_ = [games[i:i + cols] for i in range(0, 60, cols)]
    o = R(x, y, w, pitch * 6 + 18, "#34323C", "#55525E", 1, 4)
    for i, row in enumerate(rows_):
        base = y + 8 + (i + 1) * pitch
        for j, g in enumerate(row):
            o += fane(pg, g, x + 14 + j * tw, base, tw)
        o += R(x + 6, base, w - 12, 5, STEEL)
    return o


def oversikt():
    pg = Page("ovr", "08-laerer-oversikt.svg", 1600, 1000, "Fraktbrev: Oversikten over 60 Klassespill",
              "Arkivvogn med 60 fargemerkede faner: faner stikker opp ved venting, kvitteringsblokken viser hvem som må purres, trakten står under.")
    games = FX["class_games"]
    cnt = {k: sum(1 for g in games if g["status"] == k) for k in ("ferdig", "pågår", "pauset", "venter")}
    assert cnt["ferdig"] == 41 and cnt["venter"] == 4 and cnt["pågår"] + cnt["pauset"] == 15 and cnt["pauset"] == 2
    ki = sum(g["ki_seter"] for g in games)
    # hode
    pg.add(pg.paper(0, 0, 1600, 86, BLUE))
    pg.add(T(24, 40, "OVERSIKT", 28, "disp", NAVY), T(24, 66, "class-of-1994, IBE160. Klasseøkt Klassisk. Spillfrist ti. 8. des.", 16, "lab", NAVY))
    # filterfaner
    filt = [("Alle", 60, True), ("Venter", cnt["venter"], False), ("Pågår", cnt["pågår"] + cnt["pauset"], False), ("Pause", cnt["pauset"], False), ("Ferdig", cnt["ferdig"], False), ("Med KI-sete", sum(1 for g in games if g["ki_seter"]), False)]
    fx = 548
    for lb, v, on in filt:
        wf = 62 + len(lb) * 9
        pg.add(fanerad_shape(fx, 28, wf, 58, NAVY if on else BLUE_L, NAVY, 1))
        pg.add(T(fx + wf / 2, 50, lb, 15, "labb", "#fff" if on else NAVY, "middle"), T(fx + wf / 2, 74, str(v), 19, "typb", "#fff" if on else NAVY, "middle"))
        fx += wf + 6
    pg.add(plain_button(1400, 22, 176, 44, "Send Melding til alle", NAVY, 15))
    # vogn
    pitch = 102
    pg.add(trolley(pg, 24, 100, 1190, pitch, games))
    # kvitteringsblokk
    rx, ry, rw = 1234, 100, 342
    waits = sorted([g for g in games if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])
    rh = 630
    d = f"M{rx} {ry}h{rw}v{rh}" + "".join(" l-9.5 8 l-9.5 -8" for _ in range(18)) + "z"
    pg.add(f'<g filter="url(#{pg.sh})">{P(d, REC, None)}</g>')
    pg.add(T(rx + 16, ry + 38, "MÅ PURRES", 24, "disp"), T(rx + rw - 16, ry + 36, "4", 26, "typb", INK, "end"))
    yy = ry + 52
    for i, g in enumerate(waits):
        near = g["ventet_timer"] >= 20
        hh = 108 if near else 84
        pg.add(L(rx + 12, yy, rx + rw - 12, yy, INK, 1, 'stroke-dasharray="3 3"'))
        pg.add(T(rx + 16, yy + 26, f'{g["navn"]}', 21, "typb"), T(rx + rw - 16, yy + 26, f'{g["ventet_timer"]} t', 25, "typb", RED if near else INK, "end"))
        pg.add(T(rx + 16, yy + 48, f'Spill {g["spill"]}, {g["venter_paa"]}, Uke {g["uke"]}', 15, "lab"))
        if near:
            pg.add(stamp(pg, rx + 92, yy + 76, "KI OM 1 T", 14, -3, RED))
            pg.add(plain_button(rx + rw - 136, yy + 58, 120, 36, "Send Melding", RED, 14, RED))
        else:
            pg.add(plain_button(rx + rw - 136, yy + 38, 120, 34, "Send Melding", INK, 14))
        yy += hh
    pg.add(L(rx + 12, yy, rx + rw - 12, yy, INK, 1, 'stroke-dasharray="3 3"'))
    pg.add(T(rx + 16, yy + 26, "PAUSE", 15, "labb", INK, ls=.4))
    for i, g in enumerate(g for g in games if g["status"] == "pauset"):
        pg.add(icon_pause(rx + 16, yy + 36 + i * 24, INK, 12))
        pg.add(T(rx + 34, yy + 47 + i * 24, f'Spill {g["spill"]}, Uke {g["uke"]}', 15, "lab"), T(rx + rw - 16, yy + 47 + i * 24, g["fortsetter"], 15, "nar", INK, "end"))
    yy += 92
    pg.add(L(rx + 12, yy, rx + rw - 12, yy, INK, 1, 'stroke-dasharray="3 3"'))
    pg.add(ki_mark(rx + 16, yy + 12, VIO, 24, f"{ki} KI-seter", 15))
    pg.add(T(rx + 118, yy + 30, "i alle 60 spill", 15, "nar"))
    pg.add(plain_button(rx + 16, yy + 50, rw - 32, 40, "Send Melding til alle som venter", INK, 15, INK))
    # trakt
    ty = 748
    pg.add(pg.paper(0, ty, 1600, 252, BLUE))
    pg.add(T(24, ty + 34, "HVOR LANGT STUDENTENE ER KOMMET", 19, "disp", NAVY), T(1576, ty + 32, "Andel av 240 registrerte", 15, "lab", NAVY, "end"))
    fun = FX["funnel"]
    names = [("registrert", "Registrert"), ("klassespill_ferdig", "Klassespill ferdig"), ("debrief_ferdig", "Debrief ferdig"), ("quiz_bestått", "Quiz bestått"),
             ("replay_ferdig", "Replay ferdig"), ("test_levert", "Test levert"), ("ki_vurdering_klar", "KI-vurdering klar")]
    cw = (1600 - 48) / 7
    for i, (k, lb) in enumerate(names):
        v = fun[k]
        cx = 24 + i * cw
        pg.add(R(cx, ty + 46, cw, 112, "none", NAVY, 1.1))
        pg.add(T(cx + 8, ty + 66, lb.upper(), 13.5, "lab", NAVY, ls=.3))
        pg.add(T(cx + 8, ty + 110, str(v), 38, "typb", NAVY))
        bw = (cw - 16) * v / 240
        pg.add(R(cx + 8, ty + 124, cw - 16, 22, "none", NAVY, .8))
        if bw:
            pg.add(R(cx + 8, ty + 124, bw, 22, NAVY))
    # tegnforklaring
    ly = ty + 174
    pg.add(R(0, ly - 6, 1600, 84, "#34323C"))
    pg.add(T(24, ly + 34, "SLIK LESES VOGNA", 13.5, "lab", PALE, ls=.3))
    leg = [("#D8D6DF", 22, "Lav fane: ferdig"), (BLUE, 30, "Vanlig fane: pågår"), (CAN, 44, "Høy gul fane: venter, med navn og timer"), (CAN, 52, "Høyest, rød ramme: like før KI overtar")]
    lx = 180
    for f, h_, t_ in leg:
        near = "rød" in t_
        pg.add(fanerad_shape(lx, ly + 62 - h_, 34, h_, f, RED if near else INK, 2.4 if near else 1))
        pg.add(T(lx + 42, ly + 44, t_, 16, "lab", PALE))
        lx += 62 + len(t_) * 7.6
    pg.add(icon_pause(lx, ly + 32, PALE, 14), T(lx + 20, ly + 44, "Pause", 16, "lab", PALE))
    pg.add(R(lx + 76, ly + 30, 44, 18, BLUE_L, VIO, 1.2, 2, 'stroke-dasharray="3 2"'), T(lx + 98, ly + 44, "KI 2", 13, "labb", VIO, "middle"), T(lx + 128, ly + 44, "KI-seter", 16, "lab", PALE))
    pg.add(T(1576, ty + 244, "Demodata", 13, "lab", PALE, "end"))
    pg.save()
