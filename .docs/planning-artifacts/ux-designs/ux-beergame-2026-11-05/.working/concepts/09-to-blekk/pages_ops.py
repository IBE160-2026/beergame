"""Persuade og Operate: landing, lærerflater, kontaktark."""
from core import *  # noqa: F403

GAMES = F["class_games"]


# ---- Felles for lærerflatene --------------------------------------------------------------------


def field(x, y, w, label, value="", h=42, fs=16, cls="c09-m", note=None):
    o = [T(x, y, label, 14, "c09-k"), R(x, y + 7, w, h, PAPER, INK, 2)]
    if value:
        o.append(T(x + 12, y + 7 + h / 2 + fs * .36, value, fs, cls))
    if note:
        o.append(T(x, y + 7 + h + 18, note, 13))
    return "".join(o)


def seg(x, y, w, label, options, selected, h=40):
    """Valgknapper. Valgt er svart plate med hake, så valget aldri bare er farge."""
    o = [T(x, y, label, 14, "c09-k")]
    each = w / len(options)
    for i, opt in enumerate(options):
        bx = x + i * each
        sel = opt == selected
        o.append(R(bx, y + 7, each, h, INK if sel else OR, INK, 2))
        if sel:
            o.append(ic_check(bx + 10, y + 7 + h / 2 + 1, CY))
        o.append(T(bx + (28 if sel else 12), y + 7 + h / 2 + 5, opt, 15, "c09-k" if sel else "c09-m", CY if sel else INK))
    return "".join(o)


def masthead(title, x, y, size=72):
    return A(x, y, title, size, INK, rot=-3)


def margin_rail(d, entries, y0=166, role="Bård, Faglærer", x=32, w=236):
    """Venstre marg: nesten rent som i magasinet, med definisjoner."""
    o = [A(x, 56, "BLEKK", 36), T(x, 82, role, 14, "c09-k"), T(x, 102, "class-of-1994, IBE160", 14, "c09-m"),
         T(x, 122, "Demodata", 13)]
    y = y0
    for term, de in entries:
        o.append(L(x, y - 20, x + w, y - 20, INK, 1.5))
        o.append(T(x, y, term, 15, "c09-k c09-u"))
        o.append(P(x, y + 22, de, 14, w, 19))
        y += 22 + plines(de, 14, w) * 19 + 34
    return "".join(o)


def toc_row(g, x, y, w=396, h=36, fs=14):
    st = g["status"]
    wait = st == "venter"
    near = g.get("ventet_timer", 0) >= 23
    fg = CY if near else INK
    o = []
    if near:
        o.append(R(x, y, w, h, INK))
    elif wait:
        o.append(R(x, y, w, h, CY))
    base = y + h / 2 + fs * .36
    o.append(A(x + 32, base + 1, g["spill"], 20, fg, "end"))
    o.append(status_ic(st, x + 40, y + h / 2, fg, .95))
    plain = st == "ferdig"
    o.append(T(x + 58, base, st, fs, "c09-b" if plain else "c09-k", fg))
    o.append(T(x + 130, base, g["uke"], fs, "c09-b c09-tn" if plain else "c09-k c09-tn", fg, "end"))
    if g["ki_seter"]:
        tag_fg = (INK if near else CY)
        o.append(ki_tag(x + 138, base, tag_fg if not near else INK, CY if near else INK, 11))
        o.append(T(x + 160, base, g["ki_seter"], fs, "c09-k c09-tn", fg))
    note_x = x + 174
    if wait:
        note = f"{g['navn']}, {g['venter_paa']} {g['ventet_timer']} t"
        o.append(T(note_x, base, note, fs, "c09-k", fg))
        note_end = note_x + len(note) * fs * .53
    elif st == "pauset":
        note = g["fortsetter"]
        o.append(T(note_x, base, note, fs, "c09-m", fg))
        note_end = note_x + len(note) * fs * .53
    else:
        note_end = note_x
    kost = kr(g["kjedekost"], False)
    o.append(T(x + w - 6, base, kost, fs, "c09-b c09-tn" if plain else "c09-k c09-tn", fg, "end"))
    lead_to = x + w - 50
    if note_end + 8 < lead_to and not near and not wait:
        o.append(L(note_end + 4, base - 2, lead_to, base - 2, INK, 1.2, 'stroke-dasharray="1 5" stroke-linecap="round"'))
    if not near:
        o.append(L(x, y + h, x + w, y + h, INK, .8))
    return "".join(o)


# ---- 01 Landing ---------------------------------------------------------------------------------


def page_01():
    from core import game
    d = Doc("land", "01-landing", 1440, 1200, "Landingsside for faglærere",
            "Offentlig landingsside. To blekk og en diagonal: siden viser hvordan skjermen bytter blekk fra lager til restordre, "
            "og neste seksjon viser alle spillene på én skjerm.", OR)
    d.add(poly([(0, 860), (1440, 580), (1440, 1200), (0, 1200)], CY))
    # Navigasjon
    d.add(A(48, 58, "BLEKK", 38))
    d.add(T(1112, 52, "Logg inn", 16, "c09-k c09-u"))
    d.add(R(1196, 26, 196, 40, INK))
    d.add(T(1294, 52, "Be om lærertilgang", 15, "c09-k", CY, "middle"))
    # Plakaten
    d.add(G(A(0, 0, "ETT TALL", 150) + A(0, 142, "PER UKE.", 150, CY, stroke=INK, sw=6)
            + A(0, 226, "RESTEN REGNER VI.", 74), 58, 248, rot=ANG))
    d.add(P(48, 590, "Kjører hele øvelsen om forsyningskjeden, fra Invitasjon til PDF-rapport, for klasser på rundt 250 studenter. "
                     "KI-spillere fyller tomme seter, så ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
            20, 640, 28, cls="c09-m"))
    # Handling
    d.add(poly([(48, 790), (398, 722), (398, 778), (48, 846)], INK))
    d.add(A(224, 804, "BE OM LÆRERTILGANG", 36, CY, "middle", ANG))
    d.add(T(430, 770, "Logg inn", 18, "c09-k c09-u"))
    d.add(T(430, 794, "Ingen åpen registrering.", 14, "c09-m"))
    # To telefoner, samme skjerm, to blekk
    s = .66
    d.add(phone(d, 796, 92, game(d, 3, slab=True), s, OR))
    d.add(phone(d, 1096, 92, game(d, 11, typed=24, shipments=[4, 4, 8]), s, CY))
    d.add(T(796, 672, "Demodata", 13))
    d.add(A(796, 708, "HAR DU LAGER,", 30, INK))
    d.add(A(796, 742, "ER SIDEN ORANSJE.", 30, INK))
    d.add(A(1096, 708, "STÅR DU I RESTORDRE,", 30, INK))
    d.add(A(1096, 742, "BYTTER HELE SIDEN BLEKK.", 30, INK))
    # Neste seksjon
    d.add(A(340, 908, "ALLE SPILLENE PÅ ÉN SKJERM.", 66, INK, rot=-3))
    d.add(T(340, 948, "Hver linje er ett spill: status, uke, hvem det venter på og hvor lenge.", 17, "c09-m"))
    # Marg med definisjoner
    defs = [("Sete", "Én av fire plasser i et spill: Detaljist, Grossist, Distributør eller Fabrikk."),
            ("KI-spiller", "Fyller et tomt Sete. Alltid merket, for alle."),
            ("Klasseliste", "Lastes opp fra Canvas-eksport. Ingen integrasjon å sette opp.")]
    y = 900
    for term, de in defs:
        d.add(L(48, y - 18, 300, y - 18, INK, 1.5))
        d.add(T(48, y, term, 15, "c09-k c09-u"))
        d.add(P(48, y + 21, de, 14, 252, 19))
        y += 21 + plines(de, 14, 252) * 19 + 30
    # Utdrag av Oversikten
    d.add(R(340, 966, 756, 234, OR))
    subset = [GAMES[1], GAMES[2], GAMES[9], GAMES[16], GAMES[19], GAMES[29]]
    subset2 = [GAMES[10], GAMES[3], GAMES[43], GAMES[20], GAMES[57], GAMES[5]]
    for i, g in enumerate(subset):
        d.add(toc_row(g, 346, 972 + i * 37, 366))
    for i, g in enumerate(subset2):
        d.add(toc_row(g, 724, 972 + i * 37, 366))
    # Fakta
    facts = [("Spilles på mobil", "Studentene spiller på egen telefon, på norsk."),
             ("Ett tall per uke", "Studenten bestemmer. Systemet regner."),
             ("Ferdig til fristen", "Ingen spill blir stående. KI-spillere tar over seter som står tomme.")]
    y = 900
    for term, de in facts:
        d.add(L(1128, y - 18, 1392, y - 18, INK, 1.5))
        d.add(T(1128, y, term, 15, "c09-k"))
        d.add(P(1128, y + 21, de, 14, 264, 19))
        y += 21 + plines(de, 14, 264) * 19 + 30
    d.add(T(1128, y + 6, "Demodata i utdraget.", 13))
    d.save()


# ---- 02 Klasse ----------------------------------------------------------------------------------


def page_02():
    d = Doc("klasse", "02-laerer-klasse", 1440, 1000, "Faglærer lager Klasse",
            "Skjema: navn og emnekode, opplasting av Canvas-fil, valg av e-postkolonne, ugyldige rader per rad, sending av Invitasjoner "
            "og status for sendt, akseptert og utløpt.", OR)
    d.add(margin_rail(d, [
        ("Klasseliste", "Eksporten fra Canvas slik den er, med én student per rad."),
        ("Invitasjon", "En personlig lenke på e-post. Gjelder i 14 dager. Ingen kommer inn uten."),
        ("Ugyldig rad", "En adresse vi ikke kan sende til. Raden stopper ikke de andre."),
        ("Manuelt registrert", "En student du legger inn selv, for eksempel etter en feil adresse."),
    ]))
    x0 = 300
    d.add(masthead("NY KLASSE", x0, 86))
    # Rad 1
    d.add(field(x0, 146, 360, "Navn på Klassen", "class-of-1994"))
    d.add(field(x0 + 380, 146, 180, "Emnekode", "IBE160"))
    d.add(T(x0 + 580, 146, "Canvas-fil", 14, "c09-k"))
    d.add(R(x0 + 580, 153, 528, 42, PAPER, INK, 2))
    d.add(ic_upload(x0 + 594, 174))
    d.add(T(x0 + 624, 180, "ibe160-canvas-eksport.xlsx", 16, "c09-m"))
    d.add(T(x0 + 1096, 180, f"{F['roster']['paa_lista']} rader", 16, "c09-k c09-tn", anchor="end"))
    # Rad 2 venstre: e-postkolonne
    y = 238
    d.add(T(x0, y, "Velg e-postkolonne", 14, "c09-k"))
    cols = [("Navn", 170), ("SIS-ID", 90), ("E-post", 240), ("Seksjon", 90)]
    rows = [("Sara Nilsen", "118204", "sara.nilsen@student.no", "IBE160-1"),
            ("Ida Moe", "118377", "ida.moe@student.no", "IBE160-1"),
            ("Mikkel Lie", "118412", "mikkel.lie@student.no", "IBE160-2"),
            ("Jonas Hauge", "118533", "jonas.hauge@student.no", "IBE160-2"),
            ("Noah Berg", "118640", "noah.berg@student.no", "IBE160-1")]
    cx = x0
    th = y + 10
    for i, (nm, w) in enumerate(cols):
        sel = nm == "E-post"
        d.add(R(cx, th, w, 36, INK if sel else OR, INK, 1.5))
        if sel:
            d.add(ic_check(cx + 10, th + 19, CY))
        d.add(T(cx + (28 if sel else 10), th + 24, nm, 15, "c09-k", CY if sel else INK))
        for r, row in enumerate(rows):
            yy = th + 58 + r * 28
            d.add(T(cx + 10, yy, row[i], 14, "c09-k" if sel else "c09-b"))
        cx += w
    for r in range(len(rows)):
        yy = th + 66 + r * 28
        d.add(L(x0, yy, x0 + 590, yy, INK, .8))
    d.add(T(x0, th + 216, "Viser 5 av 250. Vi foreslo E-post fordi nesten alle rader har en @.", 14))
    # Rad 2 høyre: ugyldige rader i cyan, samme språk som restordre
    bx = x0 + 620
    d.add(R(bx, y - 16, 488, 276, CY))
    d.add(A(bx + 14, y + 26, "4 UGYLDIGE RADER", 34))
    d.add(T(bx + 474, y + 22, "246 er klare", 15, "c09-k", anchor="end"))
    bad = [(37, "emma.solberg@student", "mangler domene"),
           (88, "liv aas@student.no", "mellomrom"),
           (141, "oskar.vik@@student.no", "to @"),
           (203, "", "tom celle")]
    for i, (rad, addr, why) in enumerate(bad):
        yy = y + 42 + i * 52
        d.add(A(bx + 14, yy + 30, f"RAD {rad}", 22))
        d.add(R(bx + 92, yy + 6, 212, 38, PAPER, INK, 2))
        if addr:
            d.add(T(bx + 102, yy + 30, addr, 14, "c09-m"))
        d.add(T(bx + 316, yy + 30, why, 14, "c09-m"))
        d.add(T(bx + 474, yy + 30, "Rett", 14, "c09-k c09-u", anchor="end"))
    # Rad 3: send og status
    d.add(poly([(x0, 588), (x0 + 460, 564), (x0 + 460, 626), (x0, 650)], INK))
    d.add(A(x0 + 230, 620, "SEND 246 INVITASJONER", 38, CY, "middle", -3))
    d.add(P(x0 + 480, 590, "De fire ugyldige radene får ingen e-post før du har rettet dem. Invitasjonen gjelder i 14 dager.", 15, 600, 20))
    # Status
    d.add(L(x0, 684, x0 + 1108, 684, INK, 3))
    d.add(A(x0, 728, "SLIK GIKK DET", 34))
    d.add(T(x0 + 200, 726, "Sendt 5. nov, gyldig til 19. nov", 15, "c09-m"))
    # 250 tellende blokker
    r = F["roster"]
    kinds = ["reg"] * r["registrert"] + ["man"] * r["manuelt_registrert"] + ["ure"] * r["uregistrert"]
    hatch = d.hatch(INK, 5, 1.4)
    bw, bh, per = 9, 9, 50
    bx0, by0 = x0, 744
    for i, k in enumerate(kinds):
        col, row = i % per, i // per
        fill = INK if k == "reg" else (f"url(#{hatch})" if k == "man" else PAPER)
        d.add(R(bx0 + col * (bw + 2), by0 + row * (bh + 2), bw, bh, fill, INK, 1))
    lx = x0
    ly = by0 + 5 * 11 + 22
    for fill, n, lab in [(INK, r["registrert"], "registrert"), (f"url(#{hatch})", r["manuelt_registrert"], "manuelt registrert"),
                         (PAPER, r["uregistrert"], "uregistrert")]:
        d.add(R(lx, ly - 11, 12, 12, fill, INK, 1))
        d.add(T(lx + 18, ly, f"{n} {lab}", 14, "c09-k c09-tn"))
        lx += 170 if "manuelt" not in lab else 190
    d.add(T(x0, ly + 24, "Hver blokk er én student av 250.", 14))
    # Statuslinjer
    sx = x0 + 590
    counts = [("Sendt", 246, "wait"), ("Akseptert", 238, "check"), ("Venter svar", 5, "wait"), ("Utløpt", 3, "cross")]
    for i, (lab, n, ic) in enumerate(counts):
        xx = sx + i * 130
        d.add(A(xx, 786, n, 44))
        if ic == "check":
            d.add(ic_check(xx, 804))
        elif ic == "cross":
            d.add(G(f'<path d="M0 0 L10 10 M10 0 L0 10" stroke="{INK}" stroke-width="2.4"/>', xx, 798))
        else:
            d.add(ic_wait(xx, 804, INK, .8))
        d.add(T(xx + 18, 809, lab, 14, "c09-m"))
    rows = [("Emma Solberg", "manuelt registrert, rad 37", ""), ("Liv Aas", "utløpt 19. nov", "Send på nytt"),
            ("Oskar Vik", "venter svar, sendt 5. nov", "Purr"), ("Rad 203", "uregistrert, tom e-post", "Legg inn")]
    for i, (nm, st, act) in enumerate(rows):
        yy = 842 + i * 28
        d.add(T(sx, yy, nm, 14, "c09-k"))
        d.add(T(sx + 130, yy, st, 14))
        if act:
            d.add(T(x0 + 1108, yy, act, 14, "c09-k c09-u", anchor="end"))
        d.add(L(sx, yy + 8, x0 + 1108, yy + 8, INK, .8))
    d.save()


# ---- 03 Klasseøkt -------------------------------------------------------------------------------


def page_03():
    d = Doc("okt", "03-laerer-spill", 1440, 1100, "Faglærer setter opp Klasseøkt",
            "Forhåndsutfylte standarder kalt Klassisk, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og forhåndsvisning av fordelingen "
            "i 60 spill à 4. Skjemaet kan lagres uten endring.", OR)
    d.add(margin_rail(d, [
        ("Forsinkelse", "Kildene er uenige om forsinkelser. 2 uker for ordre, frakt og produksjon er produktets standard."),
        ("Veiledede uker", "De første ukene får studentene hjelp til å lese skjermen. Ordren er likevel deres."),
        ("Inaktivitetsgrense", "Etter 24 t uten Ordre tar en KI-spiller setet. Studenten kan ta det tilbake."),
        ("KI-modus", "LLM-spillere bestiller som en person ville gjort. Regelspillere følger en fast regel."),
        ("Obligatorisk", "Klassespillet teller som levert først når studenten har lagt inn nok ordrer selv."),
    ]))
    x0 = 300
    d.add(masthead("KLASSEØKT", x0, 86))
    d.add(T(x0 + 330, 58, "Alt er fylt ut som «Klassisk». Du kan lagre uten å endre noe.", 17, "c09-m"))
    # Spalte A: standarder
    ax = x0
    d.add(A(ax, 136, "SPILLINNSTILLINGER", 28))
    items = [("Startlager", "12"), ("Enheter i hvert ledd", "4"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
             ("Produksjonsforsinkelse", "2 uker"), ("Etterspørsel", "4, så 8 i uke 5"), ("Lagerkost per kasse", "0,50 kr"),
             ("Restordrekost per kasse", "1,00 kr"), ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t")]
    y = 152
    for lab, v in items:
        d.add(T(ax, y + 27, lab, 15, "c09-m"))
        d.add(R(ax + 186, y + 4, 144, 38, PAPER, INK, 2))
        d.add(T(ax + 196, y + 28, v, 15, "c09-k c09-tn"))
        y += 50
    d.add(R(ax, y + 8, 330, 84, CY))
    d.add(P(ax + 12, y + 32, "Kildene er uenige om forsinkelser. Dette er produktets standard, og det er dette tallene i Debriefen regner med.", 14, 306, 19))
    # Spalte B
    bx = x0 + 360
    d.add(A(bx, 136, "ØKTEN", 28))
    d.add(seg(bx, 170, 350, "KI-modus", ["LLM-spillere", "Regelspillere"], "LLM-spillere"))
    d.add(seg(bx, 254, 350, "Debrief-modus", ["Gruppedebrief", "Personlig"], "Gruppedebrief"))
    d.add(T(bx, 338, "Merke", 14, "c09-k"))
    d.add(R(bx, 345, 350, 40, INK, INK, 2))
    d.add(ic_check(bx + 10, 366, CY))
    d.add(T(bx + 28, 370, "Obligatorisk", 15, "c09-k", CY))
    d.add(T(bx + 338, 370, "Slå av", 14, "c09-m c09-u", CY, "end"))
    dates = [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]
    y = 424
    for i, (lab, v) in enumerate(dates):
        col, row = i % 2, i // 2
        d.add(field(bx + col * 180, y + row * 84, 170, lab, v, 40, 15))
    y = 608
    d.add(T(bx, y, "Labtimer, Datalab A2", 14, "c09-k"))
    for i, t in enumerate(["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]):
        col, row = i % 2, i // 2
        d.add(R(bx + col * 180, y + 8 + row * 52, 170, 42, PAPER, INK, 2))
        d.add(T(bx + col * 180 + 10, y + 34 + row * 52, t, 15, "c09-m c09-tn"))
    d.add(T(bx, y + 132, "Legg til Labtime", 14, "c09-k c09-u"))
    # Spalte C: fordeling
    cx = x0 + 740
    d.add(A(cx, 136, "FORDELINGEN", 28))
    d.add(A(cx, 214, "60 SPILL À 4", 66))
    d.add(T(cx, 240, "240 studenter fordelt tilfeldig. 10 er ikke registrert ennå.", 14, "c09-m"))
    # 60 spill, hvert med fire seter
    bs, gp = 10, 1
    for i in range(60):
        col, row = i % 10, i // 10
        gx = cx + col * 37
        gy = 258 + row * 42
        for s in range(4):
            sx = gx + (s % 2) * (bs + gp)
            sy = gy + (s // 2) * (bs + gp)
            fill = CY if i == 16 else OR
            d.add(R(sx, sy, bs, bs, fill if i == 16 else INK, INK, 1))
    # Spill 17
    d.add(T(cx, 530, "Spill 17, til prøve", 14, "c09-k"))
    for i, r in enumerate(ROLES):
        d.add(T(cx, 556 + i * 26, f"{r}", 14, "c09-m"))
        d.add(T(cx + 368, 556 + i * 26, NAMES[r], 14, "c09-k", anchor="end"))
        d.add(L(cx, 564 + i * 26, cx + 368, 564 + i * 26, INK, .8))
    d.add(R(cx, 676, 150, 44, OR, INK, 2))
    d.add(T(cx + 75, 703, "Kjør på nytt", 15, "c09-k", anchor="middle"))
    d.add(R(cx + 158, 676, 210, 44, INK, INK, 2))
    d.add(ic_check(cx + 172, 698, CY))
    d.add(T(cx + 192, 703, "Bekreft fordelingen", 15, "c09-k", CY))
    d.add(T(cx, 744, "Tomme seter får KI-spiller ved Start. De er merket.", 14))
    # Slaget
    d.add(poly([(x0, 902), (x0 + 1108, 844), (x0 + 1108, 944), (x0, 1002)], INK))
    d.add(A(x0 + 554, 946, "LAGRE KLASSEØKTEN", 66, CY, "middle", -3))
    d.add(P(x0, 1038, "Kan lagres uten endring. Standardene gjelder for alle Klassespill i økten.", 16, 700, 20))
    d.save()


# ---- 08 Oversikt --------------------------------------------------------------------------------


def page_08():
    d = Doc("over", "08-laerer-oversikt", 1600, 1000, "Oversikt over 60 spill",
            "En tett innholdsfortegnelse med 60 linjer: statusord, uke, KI-seter, hvem spillet venter på og hvor lenge, og kostnad. "
            "Venter er cyan, nær overtakelse er svart. Trakten og Melding ligger i margen.", OR)
    # Hode
    d.add(masthead("OVERSIKT", 28, 82, 74))
    d.add(T(28, 112, "class-of-1994, IBE160. Klasseøkt «Klassisk».", 14, "c09-m"))
    d.add(T(28, 131, "Demodata", 13))
    x = 340
    tally = [("ferdig", "41 FERDIG", 140), ("pågår", "15 PÅGÅR", 134), ("pauset", "HERAV 2 PAUSET", 214), ("venter", "4 VENTER", 130)]
    for st, lab, w in tally:
        d.add(status_ic(st, x, 44, INK, 1.8))
        d.add(A(x + 28, 62, lab, 38))
        x += 28 + w + 26
    d.add(poly([(1340, 72), (1560, 62), (1560, 110), (1340, 120)], INK))
    d.add(A(1450, 104, "SEND MELDING", 30, CY, "middle", -3))
    # Filtrering
    chips = [("Alle 60", True), ("Venter 4", False), ("Pågår 13", False), ("Pauset 2", False), ("Ferdig 41", False), ("Med KI-seter", False), ("Nær overtakelse 1", False)]
    x = 340
    d.add(T(x, 104, "Filtrer", 14, "c09-k"))
    x += 50
    for lab, sel in chips:
        w = len(lab) * 7.6 + 22
        d.add(R(x, 86, w, 28, INK if sel else OR, INK, 1.5))
        d.add(T(x + 11, 105, lab, 13.5, "c09-k", CY if sel else INK))
        x += w + 6
    # Kolonnehoder og linjene
    ry0, rh = 158, 40
    rows = 20
    for c in range(3):
        cx = 340 + c * 412
        for lab, lx, a in [("Spill", 0, None), ("Status", 40, None), ("Uke", 130, "end"), ("KI", 138, None), ("Venter på", 174, None), ("Kost, kr", 390, "end")]:
            d.add(T(cx + lx, 148, lab, 13, "c09-k", anchor=a))
        d.add(L(cx, 153, cx + 396, 153, INK, 2))
        for r in range(rows):
            g = GAMES[c * rows + r]
            d.add(toc_row(g, cx, ry0 + r * rh, 396, rh, 14))
    # Margen: nær overtakelse
    d.add(poly([(0, 164), (316, 150), (316, 346), (0, 346)], INK))
    d.add(A(28, 202, "SPILL 2", 30, CY, rot=-3))
    d.add(A(28, 286, "23 T", 72, CY))
    d.add(T(156, 240, "Noah, Grossist", 16, "c09-k", CY))
    d.add(T(156, 262, "Uke 19", 15, "c09-m", CY))
    d.add(ki_tag(156, 287, INK, CY, 13))
    d.add(T(186, 287, "overtar om 1 t", 15, "c09-k", CY))
    d.add(R(28, 300, 176, 34, CY))
    d.add(T(116, 322, "Send Melding til Noah", 13.5, "c09-k", anchor="middle"))
    d.add(T(216, 322, "Overta nå", 14, "c09-k c09-u", CY))
    # Venter ellers
    y = 372
    d.add(T(28, y, "Venter ellers, lengst først", 14, "c09-x"))
    others = sorted([g for g in GAMES if g["status"] == "venter" and g["spill"] != 2], key=lambda g: -g["ventet_timer"])
    for i, g in enumerate(others):
        yy = y + 22 + i * 23
        d.add(ic_wait(28, yy - 4, INK, .8))
        d.add(T(44, yy, f"Spill {g['spill']}", 14, "c09-k"))
        d.add(T(100, yy, f"{g['navn']}, {g['venter_paa']}", 14, "c09-m"))
        d.add(T(316, yy, f"{g['ventet_timer']} t", 14, "c09-k c09-tn", anchor="end"))
        d.add(L(28, yy + 7, 316, yy + 7, INK, .8))
    # Trakt
    y = 490
    d.add(A(28, y + 14, "TRAKTEN", 30))
    fn = F["funnel"]
    labels = [("Registrert", "registrert"), ("Klassespill ferdig", "klassespill_ferdig"), ("Debrief ferdig", "debrief_ferdig"),
              ("Quiz bestått", "quiz_bestått"), ("Replay ferdig", "replay_ferdig"), ("Test levert", "test_levert"), ("KI-vurdering klar", "ki_vurdering_klar")]
    yy = y + 40
    for lab, key in labels:
        v = fn[key]
        d.add(T(28, yy, lab, 14, "c09-m"))
        d.add(T(316, yy, v, 15, "c09-k c09-tn", anchor="end"))
        if v:
            d.add(R(28, yy + 6, 288 * v / 240, 13, CY, INK, 1.5))
        else:
            d.add(L(28, yy + 12, 316, yy + 12, INK, 1, 'stroke-dasharray="2 4"'))
        yy += 41
    # Tegnforklaring
    y = yy + 8
    d.add(L(28, y - 18, 316, y - 18, INK, 1.5))
    d.add(R(28, y - 12, 26, 15, CY, INK, 1))
    d.add(T(62, y, "Cyan linje: venter på en student", 14))
    d.add(R(28, y + 10, 26, 15, INK))
    d.add(T(62, y + 22, "Svart linje: KI overtar snart", 14))
    d.add(ki_tag(30, y + 44, CY, INK, 12))
    d.add(T(62, y + 44, "Antall KI-seter i spillet", 14))
    d.save()


# ---- 09 Sideplan -------------------------------------------------------------------------------


def mini_curve(role, x, y, w, h, color=INK, sw=1.5, ymax=33):
    pts = " ".join(f"{x + (k - 1) / 35 * w:.1f},{y + h - WEEKS[k]['seats'][role]['ordre'] / ymax * h:.1f}" for k in range(1, 37))
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{sw}"/>'


def bars(x, y, w, vals, h=9, gap=6, fill=CY):
    return "".join(R(x, y + i * (h + gap), w * v, h, fill, INK, 1) for i, v in enumerate(vals))


def rules(x, y, w, n, gap=13, sw=1.5):
    return "".join(L(x, y + i * gap, x + w, y + i * gap, INK, sw) for i in range(n))


def white(x, y, w, h=20):
    return R(x, y, w, h, PAPER, INK, 1.5)


def slab(w=212, h=210, c=CY, txt=None, size=18):
    o = poly([(0, h - 8), (w, h - 48), (w, h), (0, h)], INK)
    if txt:
        o += A(w / 2, h - 8, txt, size, c, "middle", ANG)
    return o


def S_invite(g):
    return A(14, 74, "DU ER", 38, INK, rot=ANG) + A(14, 112, "INVITERT", 38, g["c"], rot=ANG, stroke=INK, sw=2) + white(14, 122, 184) + white(14, 146, 184)


def S_login(g):
    return A(14, 62, "LOGG INN", 38, INK, rot=ANG) + white(14, 84, 184) + white(14, 114, 184)


def S_rules(g):
    return A(14, 56, "ETT TALL", 30, INK, rot=ANG) + A(14, 88, "PER UKE", 30, INK, rot=ANG) + rules(14, 104, 184, 4, 13)


def S_start(g):
    return A(14, 112, 4, 100, g["c"], rot=ANG, stroke=INK, sw=3) + A(74, 64, "PRØV", 26) + A(74, 94, "ÉN UKE", 26) + white(74, 106, 124, 30)


def S_replay(g):
    o = A(14, 58, "ÉN RUNDE TIL", 30, INK, rot=ANG)
    for i in range(3):
        o += ki_tag(14, 92 + i * 22, g["c"], INK, 13) + L(42, 88 + i * 22, 198, 88 + i * 22, INK, 1.5)
    return o


def S_review(g):
    return (A(14, 42, "RUNDE 1 OG 2", 22) + mini_curve("Fabrikk", 12, 54, 188, 96, INK, 2.5)
            + mini_curve("Detaljist", 12, 54, 188, 96, INK, 1.5).replace('stroke-width="1.5"', 'stroke-width="1.5" stroke-dasharray="1 3"'))


def S_test(g):
    return (A(14, 38, "INDIVIDUELL TEST", 22) + R(14, 48, 12, 12, g["c"], INK, 1.5) + L(32, 54, 198, 54, INK, 1.5)
            + R(14, 66, 12, 12, g["g"], INK, 1.5) + L(32, 72, 198, 72, INK, 1.5)
            + R(14, 88, 184, 46, g["c"], INK, 1.5) + mini_curve("Grossist", 14, 90, 184, 42, INK, 2) + white(14, 142, 184, 28))


def S_ki(g):
    return (R(0, 0, 212, 210, INK) + ki_tag(14, 36, INK, CY, 18)
            + A(52, 38, "VURDERING", 26, CY) + P(14, 66, "Teller ikke. Er aldri en karakter.", 14, 184, 19, fill=CY)
            + "".join(L(14, 118 + i * 14, 198, 118 + i * 14, CY, 1.5) for i in range(4)))


def S_pdf(g):
    return (R(36, 14, 140, 182, PAPER, INK, 2) + A(46, 44, "RAPPORT", 22) + mini_curve("Fabrikk", 46, 54, 120, 60, INK, 2)
            + rules(46, 128, 120, 4, 13, 1.2) + poly([(150, 14), (176, 14), (176, 40)], INK))


def S_small(g):
    o = ""
    for i in range(12):
        x, y = 12 + (i % 4) * 48, 16 + (i // 4) * 62
        role = ROLES[i % 4]
        o += R(x, y, 44, 56, g["c"], INK, 1.2) + mini_curve(role, x + 2, y + 6, 40, 46, INK, 1.2)
    return o


def S_home(g):
    o = A(14, 42, "KLASSER", 30)
    for i, n in enumerate(["class-of-1994", "class-of-1995", "class-of-1996"]):
        o += T(14, 72 + i * 30, n, 14, "c09-k") + L(14, 80 + i * 30, 198, 80 + i * 30, INK, 1.5)
    return o


def S_creport(g):
    return A(14, 42, "KLASSERAPPORT", 26) + bars(14, 58, 184, [1, .68, .5, .4, .24, .05], 12, 5)


def S_insight(g):
    o = A(14, 38, "UKE FOR UKE", 24)
    for r in range(8):
        for c in range(9):
            o += R(14 + c * 20.5, 50 + r * 18, 19, 16, CY if (r + c) % 5 == 0 else g["g"], INK, 1)
    return o


def S_student(g):
    o = A(14, 42, "SARA NILSEN", 30)
    for i in range(6):
        o += (ic_done(14, 66 + i * 22) if i < 2 else ic_lock(14, 68 + i * 22, INK, .9)) + L(36, 66 + i * 22, 198, 66 + i * 22, INK, 1.5)
    return o


def S_plenum(g):
    o = ""
    for i in range(20):
        x, y = 8 + (i % 5) * 40, 10 + (i // 5) * 48
        o += R(x, y, 37, 44, OR, INK, 1) + mini_curve(ROLES[i % 4], x + 2, y + 4, 33, 36, INK, 1)
    return o


def S_cross(g):
    o = A(14, 38, "TVERS AV KLASSER", 22)
    for i, v in enumerate([.5, .8, .62, .9, .7, .44, .76]):
        o += R(16 + i * 26, 180 - 120 * v, 20, 120 * v, CY, INK, 1.5)
    return o + L(14, 180, 198, 180, INK, 2)


def S_msg(g):
    return A(14, 42, "MELDINGER", 30) + rules(14, 62, 184, 4, 15) + white(14, 134, 184, 46)


def S_testgame(g):
    return A(14, 118, 12, 110, g["c"], stroke=INK, sw=3, rot=ANG) + A(118, 62, "TEST", 40) + P(118, 84, "Bare du ser dette spillet.", 13, 88, 17)


def S_admin(g):
    o = A(14, 42, "ADMIN", 34)
    for i in range(4):
        o += L(14, 66 + i * 28, 198, 66 + i * 28, INK, 1.5) + R(14, 74 + i * 28, 40, 8, INK)
    return o


def S_users(g):
    o = A(14, 42, "BRUKERE", 30)
    for i, r in enumerate(["Faglærer", "Assistent", "Student", "Admin"]):
        o += L(14, 62 + i * 30, 104, 62 + i * 30, INK, 1.5) + R(116, 48 + i * 30, 82, 22, INK) + T(122, 64 + i * 30, r, 13, "c09-k", CY)
    return o


def S_kicost(g):
    return (ki_tag(14, 38, CY, INK, 18) + A(52, 40, "KOSTNAD", 30)
            + "".join(R(14 + i * 26, 180 - v * 100, 20, v * 100, CY, INK, 1.5) for i, v in enumerate([.2, .35, .3, .55, .7, .9, .6])) + L(14, 180, 198, 180, INK, 2))


def thumb(d, x, y, sketch, title, line, ch=ORANGE, w=212, h=210):
    c = d.clip_rect(0, 0, w, h, 2)
    o = G(R(-3, -3, w + 6, h + 6, INK) + f'<g clip-path="url(#{c})">{R(0, 0, w, h, ch["g"])}{sketch(ch)}</g>', x, y)
    lines = wrap(title.upper(), 26, w, .42)
    for i, l in enumerate(lines):
        o += A(x, y + h + 40 + i * 28, l, 26)
    o += P(x, y + h + 40 + (len(lines) - 1) * 28 + 22, line, 15, w, 20)
    return o


def page_09():
    d = Doc("alle", "09-alle-sider", 2000, 1400, "Sideplan for alle andre sider",
            "Kontaktark i form av et magasins sideplan: resten av sidene gruppert per rolle, hver med tittel og én linje.", OR)
    d.add(A(40, 76, "SIDEPLANEN", 60))
    d.add(T(340, 72, "Alle andre sider, gruppert per rolle. Blekket følger samme regel overalt. Demodata.", 18, "c09-m"))
    student = [
        (S_invite, "Invitasjon og registrering", "Lenken fra e-posten, tre felt, inn.", ORANGE),
        (S_login, "Logg inn", "E-post og passord. Glemt passord ved siden av.", ORANGE),
        (S_rules, "Regler før første ordre", "Ett tall per uke. Du ser ikke hele kjeden.", ORANGE),
        (S_start, "Startoppgave", "Øv på å lese skjermen med en prøveuke.", ORANGE),
        (S_replay, "Replay", "Én runde til mot tre KI-spillere, alle merket.", CYAN),
        (S_review, "Replay-gjennomgang", "Runde 1 mot runde 2: ordrene dine på samme akse.", CYAN),
        (S_test, "Individuell test", "Flervalg, tegne- og tabelloppgave, langsvar.", ORANGE),
        (S_ki, "KI-vurdering", "Teller ikke og er aldri en karakter.", ORANGE),
        (S_pdf, "Studentrapport (PDF)", "To blekk på papir, uke for uke, kan lastes ned.", ORANGE),
        (S_small, "Alle spill side om side", "Etter Debrief: kurvene fra hele klassen, uten navn.", CYAN),
    ]
    teacher = [
        (S_home, "Lærerhjem med klasser", "Klassene dine og neste frist.", ORANGE),
        (S_creport, "Klasserapport", "Trakt, kostnad og fullføring for hele Klassen.", ORANGE),
        (S_insight, "Spillinnsikt", "Hver Uke og hvert Sete i ett spill.", ORANGE),
        (S_student, "Studentside", "Én student: stegene, ordrene, rapporten.", ORANGE),
        (S_plenum, "Spill alle side om side", "For plenum: 60 spill på storskjerm.", CYAN),
        (S_cross, "Tverrklasse-statistikk", "Samme øvelse, flere Klasseøkter.", ORANGE),
        (S_msg, "Meldinger", "Til ett spill, en gruppe eller hele Klassen.", ORANGE),
        (S_testgame, "Lærers testspill", "Prøv innstillingene alene, mot KI-spillere.", ORANGE),
    ]
    admin = [
        (S_admin, "Admin-område", "Drift og revisjonslogg.", ORANGE),
        (S_users, "Brukere og roller", "Hvem er hva, og hvem har endret det.", ORANGE),
        (S_kicost, "KI-kostnad", "Per Klasseøkt og per måned.", ORANGE),
    ]
    pitch_x, pitch_y = 236, 412
    x0 = 40
    y0 = 158
    d.add(A(x0, 136, "STUDENT", 38))
    d.add(L(x0, 144, x0 + pitch_x * 5 - 24, 144, INK, 3))
    for i, (sk, t, l, ch) in enumerate(student):
        d.add(thumb(d, x0 + (i % 5) * pitch_x, y0 + (i // 5) * pitch_y, sk, t, l, ch))
    tx = x0 + pitch_x * 5 + 24
    d.add(A(tx, 136, "FAGLÆRER", 38))
    d.add(L(tx, 144, tx + pitch_x * 3 - 24, 144, INK, 3))
    for i, (sk, t, l, ch) in enumerate(teacher):
        d.add(thumb(d, tx + (i % 3) * pitch_x, y0 + (i // 3) * pitch_y, sk, t, l, ch))
    ay = y0 + 2 * pitch_y
    d.add(A(x0, ay - 22, "ADMIN", 38))
    d.add(L(x0, ay - 14, x0 + pitch_x * 3 - 24, ay - 14, INK, 3))
    for i, (sk, t, l, ch) in enumerate(admin):
        d.add(thumb(d, x0 + i * pitch_x, ay, sk, t, l, ch))
    # Blekkregelen, i det ledige feltet
    bx = x0 + pitch_x * 3 + 10
    d.add(A(bx, ay - 22, "BLEKKREGELEN", 38))
    d.add(L(bx, ay - 14, bx + 430, ay - 14, INK, 3))
    regler = [(OR, None, "Oransje", "Du har lager. Vanlig tilstand på lærerflatene."),
              (CY, None, "Cyan", "Du står i restordre, eller noe venter på deg."),
              (INK, None, "Overtrykk", "Begge blekk oppå hverandre. All lesetekst og Bekreft."),
              (PAPER, None, "Papir", "Bare der du skriver, og på den stille siden i Debriefen.")]
    for i, (fill, _, navn, tekst) in enumerate(regler):
        yy = ay + i * 56
        d.add(R(bx, yy, 44, 44, fill, INK, 2))
        d.add(T(bx + 58, yy + 16, navn, 16, "c09-k"))
        d.add(T(bx + 58, yy + 37, tekst, 14.5))
    d.save()
