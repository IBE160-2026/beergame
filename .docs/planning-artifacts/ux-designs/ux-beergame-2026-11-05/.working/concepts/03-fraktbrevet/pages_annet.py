"""01 landing, 04 student hjem, 09 kontaktark."""
from c03lib import *  # noqa: F403
from pages_laerer import fanerad_shape, check

BRAND = "Fraktbrev"


# ---------- 01 ----------
def small_trolley(pg, x, y, w):
    """60 faner med ekte status. Ventende stikker opp."""
    games = FX["class_games"]
    cols, tw = 15, (w - 20) / 15
    o = R(x, y, w, 276, "#34323C", None, 1, 4)
    for r in range(4):
        base = y + 10 + (r + 1) * 64
        for c in range(cols):
            g = games[r * cols + c]
            st = g["status"]
            h, fill = {"ferdig": (26, "#D8D6DF"), "pågår": (36, BLUE), "pauset": (36, BLUE_L), "venter": (58, CAN)}[st]
            o += fanerad_shape(x + 10 + c * tw + 1, base - h, tw - 2, h, fill, INK, .8)
            o += T(x + 10 + c * tw + tw / 2, base - h + 19, str(g["spill"]), 13.5, "typb", INK, "middle")
        o += R(x + 6, base, w - 12, 4, STEEL)
    return o


def landing():
    pg = Page("lan", "01-landing.svg", 1440, 1200, "Fraktbrev: landingssiden for faglærere",
              "Hele siden er en blankett: ett tomt felt i uka, fire seter på snor, og Oversikten som en arkivvogn med 60 faner.")
    x, w = 36, 1368
    # gult hovedark med traktorhull
    pg.add(pg.paper(x, 0, w, 872, CAN), tractor(x + 18, 18, 840), tractor(x + w - 18, 18, 840))
    pg.add(L(x + 36, 0, x + 36, 872, INK, .7, 'stroke-dasharray="2 4"'), L(x + w - 36, 0, x + w - 36, 872, INK, .7, 'stroke-dasharray="2 4"'))
    # hode som feltrad
    hx, hw = x + 36, w - 72
    pg.add(L(hx, 78, hx + hw, 78, INK, 1.4))
    pg.add(T(hx + 24, 52, BRAND.upper(), 28, "disp"))
    pg.add(L(hx + 250, 0, hx + 250, 78, INK, 1))
    pg.add(T(hx + 268, 34, "SENDES TIL", 13, "lab", ls=.5), T(hx + 268, 60, "Faglærere i forsyningskjede og logistikk", 19, "typb"))
    pg.add(plain_button(hx + hw - 136, 18, 116, 44, "Logg inn", INK, 17))
    # overskrift
    lx = hx + 24
    pg.add(T(lx, 192, "Ett tomt felt", 88, "disp"), T(lx, 286, "i uka.", 88, "disp"))
    body = "Fire studenter driver hver sin del av en forsyningskjede. Hver Uke er alt ferdig utfylt, bortsett fra Ordren. Studenten skriver ett tall og slår stempelet. Systemet regner resten."
    pg.add(TW(lx + 2, 346, body, 620, 21, "typ", INK, 30))
    by = 346 + TH(body, 620, 21, "typ", 30) + 18
    pg.add(stamp_button(lx, by, 372, 92, "BE OM LÆRERTILGANG", "Ingen åpen registrering", True, 22))
    pg.add(plain_button(lx + 388, by, 170, 92, "Logg inn", INK, 21))
    # mekanismen: snor
    sy = by + 124
    pg.add(T(lx, sy, "UKA GÅR VIDERE NÅR ALLE FIRE HAR STEMPLET", 14, "labb", INK, ls=.5))
    seats = [("Detaljist", "Ida", "bestilt", ""), ("Grossist", "Sara", "deg", ""), ("Distributør", "Mikkel", "bestilt", ""), ("Fabrikk", "KI", "ki", "")]
    pg.add(G(snor(pg, 0, 0, 390, seats, 70), lx + 10, sy + 12, 1.5))
    pg.add(T(lx, sy + 148, "Tomme seter får en KI-spiller, alltid merket. Demodata.", 16, "lab"))
    # skjemaet til hoeyre: selve mekanismen
    form = ordreseddel(pg, 11, "24", False, ghost=24, top=0, x0=0)
    pg.add(f'<g transform="translate(792 106) rotate(1.4) scale(1.31 1.15)">{form}</g>' if False else f'<g transform="translate(806 104) rotate(1.3) scale(1.2)">{form}</g>')
    # rosa ark
    y2 = 856
    pg.add(f'<g filter="url(#{pg.sh})">{torn_top(x, y2, w, 1200 - y2, PINK)}</g>')
    pg.add(T(lx, y2 + 74, "Alle spillene på én skjerm.", 46, "disp", PLUM))
    pg.add(TW(lx + 2, y2 + 112, "Faner stikker opp der et spill venter, med navn og timer. Du purrer dem som står øverst.", 620, 19, "typ", CARBON, 26))
    # avkrysningslinjer
    facts = ["Kjører hele øvelsen fra Invitasjon til PDF-rapport", "Klasser på rundt 250 studenter, lista fra Canvas-eksport",
             "Ett fravær stopper ikke gruppa", "Ingen spill blir stående uferdig", "Spilles på mobil, på norsk"]
    fy = y2 + 174
    for i, t_ in enumerate(facts):
        pg.add(check(lx, fy + i * 30 - 16, True, PLUM, 19), T(lx + 30, fy + i * 30, t_, 19, "lab", PLUM))
    pg.add(small_trolley(pg, 780, y2 + 40, 570))
    pg.add(T(1350, y2 + 334, "Demodata", 13, "lab", PLUM, "end"))
    pg.save()


# ---------- 04 ----------
def scr_register(pg):
    o = pg.paper(8, 24, 374, 564, CAN) + perf_h(14, 32, 362, DESK, 2.2)
    o += T(22, 74, "INVITASJON", 28, "disp")
    o += T(22, 98, "Fra Bård, faglærer", 16, "lab")
    o += field(20, 112, 350, 66, "Klasse", "class-of-1994, IBE160", size=19)
    o += field(20, 178, 350, 66, "Til", "sara.lund@stud.example.no", size=18)
    o += T(22, 272, "Det eneste du må fylle ut:", 18, "labb")
    o += R(20, 282, 350, 70, CAN_L, INK, 2.2) + T(28, 300, "NAVN", 13, "lab", ls=.5) + T(28, 338, "Sara Lund", 24, "typb")
    o += R(20, 358, 350, 70, CAN_L, INK, 2.2) + T(28, 376, "VELG PASSORD", 13, "lab", ls=.5)
    for i in range(9):
        o += C(36 + i * 18, 404, 5, INK)
    o += R(40 + 9 * 18, 390, 3, 28, INK)
    o += stamp_button(20, 442, 350, 84, "REGISTRER MEG", "Invitasjonen gjelder i 14 dager", True, 21)
    o += T(22, 552, "Du kan ikke melde deg på uten invitasjon.", 15, "nar")
    o += T(22, 572, "Spørsmål? Snakk med faglæreren din.", 15, "nar")
    # kopien
    o += f'<g filter="url(#{pg.sh})">{torn_top(8, 600, 374, 200, PINK)}</g>'
    o += T(22, 638, "Dette skjer så", 22, "disp", PLUM)
    o += TW(22, 668, "Klassespillet åpner ti. 24. nov. Da får du Rolle og tre andre i Spill. Før første Ordre leser du reglene og gjør Startoppgaven.", 340, 19, "nar", PLUM, 27)
    o += demo(14, 826)
    return o


def scr_home(pg):
    o = T(14, 28, BRAND.upper(), 15, "disp", PALE) + T(376, 28, "Sara", 15, "typb", PALE, "end")
    y = 38
    o += pg.paper(8, y, 374, 186, CAN) + perf_h(14, y + 8, 362, DESK, 2.2)
    o += T(22, y + 50, "Spillet venter", 30, "disp") + T(22, y + 84, "på deg", 30, "disp")
    o += T(372, y + 40, "Uke 11", 22, "typb", INK, "end")
    o += stamp_button(20, y + 100, 350, 74, "ÅPNE ORDRESEDDELEN", "Spill 17, Grossist", True, 20)
    y = 232
    o += snor(pg, 12, y + 4, 366, SEATS_W11, 70)
    # seks steg, kuponger
    y = 322
    o += T(14, y + 12, "DE SEKS STEGENE", 13, "lab", PALE, ls=.5)
    steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "Rapport"]
    cw, ch = 374 / 3, 66
    for i, s_ in enumerate(steps):
        cx, cy = 8 + (i % 3) * cw, y + 20 + (i // 3) * ch
        on = i == 0
        o += R(cx, cy, cw, ch, CAN if on else "#3A3844", INK if on else "#6B6878", .8)
        c = INK if on else PALE
        wrapd = wrap(s_, cw - 18, 15, "lab")
        for j, ln in enumerate(wrapd):
            o += T(cx + 9, cy + 22 + j * 17, ln, 15, "labb" if on else "lab", c)
        if on:
            o += T(cx + 9, cy + 56, "pågår", 14, "typb", INK)
        else:
            o += icon_lock(cx + cw - 22, cy + ch - 22, c, 14)
    for i in range(1, 3):
        o += perf_v(8 + i * cw, y + 24, 2 * ch - 8, DESK, 1.8, 8)
    o += perf_h(12, y + 20 + ch, 366, DESK, 1.8, 8)
    # frist og labtimer
    y = 482
    o += pg.paper(8, y, 374, 78, PINK)
    o += T(20, y + 22, "NESTE FRIST", 13, "lab", PLUM, ls=.5) + T(20, y + 58, "Spillfrist", 22, "labb", PLUM) + T(370, y + 58, "ti. 8. des", 22, "typb", CARBON, "end")
    y = 572
    o += T(14, y + 12, "LABTIMER, DATALAB A2", 13, "lab", PALE, ls=.5)
    labs = ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]
    for i, lb in enumerate(labs):
        yy = y + 22 + i * 46
        o += R(8, yy, 374, 42, BLUE, NAVY, .7) + T(20, yy + 28, lb, 18, "typb", NAVY)
    o += demo(14, 826)
    return o


def hjem():
    pg = Page("hjm", "04-student-hjem.svg", 1000, 900, "Fraktbrev: Sara på mobil",
              "To telefoner: registrering med Invitasjon til venstre, hjem under spill til høyre med seter på snor, seks kuponger, frist og Labtimer.")
    pg.add(phone(pg, 70, 28, scr_register(pg)), phone(pg, 540, 28, scr_home(pg)))
    pg.save()


# ---------- 09 ----------
def mf(x, y, w, h=24, fill=None, c=INK):
    return R(x, y, w, h, fill or "none", c, 1)


def lines(x, y, w, n=3, step=12, c=INK):
    return "".join(L(x, y + i * step, x + (w if i % 3 != 2 else w * .7), y + i * step, c, 1.3) for i in range(n))


def mstamp(x, y, w, h=30, c=VIO):
    return R(x, y, w, h, c, None, 1, 3) + icon_stamp(x + 6, y + h / 2 - 9, 18, "#fff") + R(x + 32, y + h / 2 - 3, w - 44, 5, "#fff")


def s_inv(pg, x, y):
    return mf(x, y, 220, 26) + mf(x, y + 26, 220, 26) + mf(x, y + 62, 220, 34, CAN_L) + mf(x, y + 102, 220, 34, CAN_L) + mstamp(x, y + 146, 220, 36)


def s_login(pg, x, y):
    return mf(x + 20, y + 24, 180, 36, CAN_L) + mf(x + 20, y + 70, 180, 36, CAN_L) + mstamp(x + 20, y + 120, 180, 36)


def s_rules(pg, x, y):
    o = ""
    for i, r in enumerate(ROLES):
        o += icon_role(r, x + i * 56 + 6, y + 8, 34, PLUM)
        if i < 3:
            o += P(f"M{x + i * 56 + 44} {y + 25}h12M{x + i * 56 + 51} {y + 20}l5 5l-5 5", "none", PLUM, 1.5)
    return o + lines(x, y + 66, 220, 5, 14, PLUM) + mstamp(x, y + 146, 220, 36)


def s_start(pg, x, y):
    o = mf(x, y, 108, 44) + mf(x + 112, y, 108, 44) + mf(x, y + 44, 108, 44) + mf(x + 112, y + 44, 108, 44)
    o += R(x, y + 96, 220, 52, CAN_L, INK, 2) + T(x + 10, y + 136, "4", 36, "typb")
    o += T(x + 46, y + 132, "skriv 4 her", 24, "pen", INK) + mstamp(x, y + 154, 220, 30)
    return o


def s_replay(pg, x, y):
    o = ""
    for i in range(4):
        o += R(x + i * 56, y, 52, 42, CAN if i == 1 else PINK, INK, .6)
        if i != 1:
            o += R(x + i * 56 + 5, y + 14, 42, 16, "none", VIO, 1.1, 2, 'stroke-dasharray="3 2"') + T(x + i * 56 + 26, y + 26.5, "KI", 12, "labb", VIO, "middle")
    o += mf(x, y + 54, 150, 50) + mf(x, y + 104, 150, 26) + R(x + 160, y + 54, 60, 34, BLUE, NAVY, .7) + R(x + 160, y + 88, 60, 42, BLUE, NAVY, .7) + mstamp(x, y + 146, 220, 36)
    return o


def s_gjenn(pg, x, y):
    o = ""
    vals = [4, 4, 8, 24, 16, 13, 12, 8]
    vals2 = [4, 4, 6, 8, 8, 8, 8, 8]
    for i, (a, b) in enumerate(zip(vals, vals2)):
        o += R(x + 2 + i * 13, y + 84 - a * 3, 10, a * 3, PINK, PLUM, .5)
        o += R(x + 118 + i * 13, y + 84 - b * 3, 10, b * 3, BLUE, NAVY, .5)
    o += L(x, y + 84, x + 106, y + 84, INK) + L(x + 116, y + 84, x + 222, y + 84, INK)
    o += T(x, y + 104, "Klassespill", 15, "lab") + T(x + 116, y + 104, "Replay", 15, "lab") + lines(x, y + 122, 220, 4, 14)
    return o


def s_test(pg, x, y):
    o = ""
    for i in range(3):
        o += check(x, y + 2 + i * 22, i == 1, INK, 15) + L(x + 22, y + 10 + i * 22, x + 100, y + 10 + i * 22, INK, 1.3)
    o += R(x + 112, y, 108, 68, "none", INK, 1)
    for i in range(1, 5):
        o += L(x + 112, y + i * 13.6, x + 220, y + i * 13.6, INK, .4) + L(x + 112 + i * 21.6, y, x + 112 + i * 21.6, y + 68, INK, .4)
    o += P(f"M{x + 114} {y + 56}C{x + 140} {y + 56} {x + 150} {y + 8} {x + 170} {y + 10}S{x + 200} {y + 50} {x + 218} {y + 40}", "none", VIO, 2)
    o += R(x, y + 80, 220, 104, CAN_L, INK, 1.6) + lines(x + 8, y + 98, 200, 6, 14, CARBON)
    return o


def s_ki(pg, x, y):
    o = ki_mark(x, y, VIO, 24, "KI-vurdering", 14)
    o += T(x, y + 50, "Teller ikke. Aldri en karakter.", 15, "labb") + lines(x, y + 68, 220, 6, 14)
    o += R(x, y + 152, 220, 30, "none", INK, 1)
    return o


def s_rapp(pg, x, y):
    o = ""
    for i in range(6, 0, -1):
        o += R(x + 30 + i * 3, y + i * 3, 150, 180, PINK if i % 2 else BLUE, PLUM, .5)
    o += R(x + 30, y, 150, 180, REC, INK, .8) + T(x + 44, y + 34, "RAPPORT", 18, "disp") + lines(x + 44, y + 54, 120, 6, 14)
    o += R(x + 40, y - 3, 22, 4, STEEL) + stamp(pg, x + 120, y + 156, "PDF", 13, -5, VIO, False)
    return o


def s_sidevis(pg, x, y):
    ser = {r: [w["seats"][r]["ordre"] for w in WEEKS] for r in ROLES}
    o = ""
    for j, (r, c) in enumerate(zip(ROLES, (REC, BLUE, PINK, CAN))):
        cx = x + j * 56
        o += icon_role(r, cx + 12, y, 24, INK)
        for i, v in enumerate(ser[r][::2]):
            o += R(cx, y + 34 + i * 8, max(v * 1.6, 2), 6.5, c, INK, .4)
    return o


def s_lhome(pg, x, y):
    o = ""
    for i, t_ in enumerate(["class-of-1994", "class-of-1993", "Testklasse"]):
        o += fanerad_shape(x + i * 12, y + i * 52, 210, 70, [CAN, BLUE, PINK][i], INK, .8) + T(x + i * 12 + 14, y + i * 52 + 28, t_, 17, "typb")
    return o


def s_krapp(pg, x, y):
    o = ""
    for i, v in enumerate(FX["funnel"].values()):
        o += R(x, y + i * 22, 220 * v / 240, 16, NAVY) + R(x, y + i * 22, 220, 16, "none", NAVY, .8)
    o += stamp(pg, x + 160, y + 170, "PDF", 12, -5, VIO, False)
    return o


def s_innsikt(pg, x, y):
    o = ""
    for i in range(10):
        o += P(f"M{x + i * 22} {y}h20v22h-20z", PINK if i != 6 else CAN, PLUM, .5)
        o += T(x + i * 22 + 10, y + 16, str(i + 6), 12, "lab", PLUM, "middle")
    for j, r in enumerate(ROLES):
        o += R(x + j * 56, y + 34, 52, 110, [REC, CAN, BLUE, PINK][j], INK, .6) + icon_role(r, x + j * 56 + 14, y + 42, 24)
        o += lines(x + j * 56 + 7, y + 80, 38, 5, 12)
    o += T(x, y + 172, "Uke 12: Ordrer og lager per Sete", 15, "lab")
    return o


def s_stud(pg, x, y):
    o = T(x, y + 18, "Sara Lund", 21, "typb") + T(x, y + 38, "Spill 17, Grossist", 15, "lab")
    for i in range(6):
        o += R(x + (i % 3) * 74, y + 50 + (i // 3) * 40, 72, 38, CAN if i < 1 else "none", INK, 1)
    return o + lines(x, y + 142, 220, 3, 14)


def s_plenum(pg, x, y):
    o = R(x, y, 220, 150, DESK)
    for j in range(5):
        for i in range(10):
            hh = (i * 7 + j * 11) % 22 + 3
            o += R(x + 8 + i * 21, y + 26 + j * 28 - hh, 18, hh, [CAN, BLUE, PINK, REC, BLUE][j])
    return o + R(x + 90, y + 150, 40, 12, STEEL) + R(x + 60, y + 162, 100, 5, STEEL)


def s_tverr(pg, x, y):
    o = ""
    for i in range(4):
        v = [62, 80, 54, 92][i]
        o += fanerad_shape(x + i * 56, y + 150 - v * 1.5, 50, v * 1.5, [PINK, BLUE, CAN, REC][i], INK, .7)
        o += T(x + i * 56 + 25, y + 170, str(1991 + i), 15, "typb", INK, "middle")
    return o


def s_meld(pg, x, y):
    o = ""
    for i, t_ in enumerate(["Hele Klasseøkta", "Ett spill", "Én student"]):
        o += check(x, y + i * 26, i == 1, INK, 17) + T(x + 26, y + 14 + i * 26, t_, 16, "lab")
    o += R(x, y + 84, 220, 66, CAN_L, INK, 1.4) + lines(x + 8, y + 102, 200, 3, 14, CARBON) + mstamp(x, y + 156, 220, 30)
    return o


def s_lest(pg, x, y):
    o = mf(x, y, 108, 44) + mf(x + 112, y, 108, 44) + R(x, y + 54, 220, 62, CAN_L, INK, 2) + T(x + 10, y + 102, "8", 42, "typb")
    o += stamp(pg, x + 140, y + 88, "TEST", 18, -6, RED, False)
    o += ki_mark(x, y + 128, VIO, 22, "3 KI-spillere", 14) + T(x, y + 174, "Teller ikke i noen statistikk", 15, "nar")
    return o


def s_admin(pg, x, y):
    o = ""
    for i, t_ in enumerate(["Brukere og roller", "Revisjonslogg", "KI-kostnad"]):
        o += R(x, y + i * 62, 220, 56, STEEL, INK, 1) + R(x + 80, y + i * 62 + 14, 60, 10, DESK) + T(x + 110, y + i * 62 + 44, t_, 15, "labb", INK, "middle")
    return o


def s_users(pg, x, y):
    o = ""
    roles = ["Faglærer", "Assistent", "Student", "Admin", "Student"]
    for i, rr in enumerate(roles):
        yy = y + i * 37
        o += L(x, yy + 34, x + 220, yy + 34, INK, .7) + R(x, yy + 12, 90, 8, INK) + R(x + 128, yy + 3, 92, 26, "none", VIO, 1.4, 2) + T(x + 174, yy + 21, rr, 14, "labb", VIO, "middle")
    return o


def s_kost(pg, x, y):
    o = R(x + 30, y, 160, 184, REC, INK, .6) + T(x + 110, y + 24, "KI-KOSTNAD", 15, "disp", INK, "middle")
    for i, v in enumerate([92, 64, 110, 40, 74]):
        o += R(x + 42, y + 42 + i * 22, v, 12, VIO)
    o += L(x + 42, y + 158, x + 178, y + 158, INK, 1, 'stroke-dasharray="3 3"')
    return o + R(x + 124, y + 164, 54, 8, INK)


PAGES = [
    ("Student", PINK, PLUM, [
        ("Invitasjon og registrering", "Blanketten kommer utfylt. Du velger bare navn og passord.", CAN, s_inv),
        ("Logg inn", "To felt og et stempel. Rett tilbake til det som venter.", CAN, s_login),
        ("Regler før første ordre", "Kjeden på ett ark. Ingen fasit, ingen uketall.", PINK, s_rules),
        ("Startoppgave", "Første skjema med blyantnotat: skriv 4 og slå stempelet.", CAN, s_start),
        ("Replay", "Samme skjema, tre KI-spillere på snora, merket.", CAN, s_replay),
        ("Replay-gjennomgang", "To bunker side om side: første spill og andre runde.", REC, s_gjenn),
        ("Individuell test", "Flervalg, tegne- og tabelloppgave, langsvar på samme blankett.", CAN, s_test),
        ("KI-vurdering", "Lapp med KI-merke. Teller ikke, og sier det.", REC, s_ki),
        ("Studentrapport (PDF)", "Hele bunken stiftet: Forklaring, øyeblikk, quiz, test.", BLUE, s_rapp),
        ("Alle spill side om side", "Fire stabler per Rolle, spill for spill, etter Debrief.", REC, s_sidevis),
    ]),
    ("Faglærer", BLUE, NAVY, [
        ("Lærerhjem med klasser", "Arkivskuff: en fane per Klasse.", REC, s_lhome),
        ("Klasserapport", "Trakten som blankett, klar til PDF.", BLUE, s_krapp),
        ("Spillinnsikt (uke for uke)", "Bla i ett spill: fire kopier per Uke.", REC, s_innsikt),
        ("Studentside", "Én student: kupongene, spillet, Meldinger.", CAN, s_stud),
        ("Spill alle side om side", "Bunkene på lerretet for plenum, uten navn.", REC, s_plenum),
        ("Tverrklasse-statistikk", "Klasser som mapper med samme mål over år.", REC, s_tverr),
        ("Meldinger", "Til alle, ett spill eller én student. Ingen svar i appen.", CAN, s_meld),
        ("Lærers testspill", "Prøv selv mot KI. Stemplet TEST.", CAN, s_lest),
    ]),
    ("Admin", CAN, INK, [
        ("Admin-område", "Stålskapet: tre skuffer.", REC, s_admin),
        ("Brukere og roller", "Liste med rollestempel per person.", REC, s_users),
        ("KI-kostnad", "Lang kvittering per Klasseøkt.", REC, s_kost),
    ]),
]


def thumb(pg, x, y, w, h, title, line, fill, fn):
    ink = PLUM if fill == PINK else NAVY if fill == BLUE else INK
    o = pg.paper(x, y, w, h, fill)
    o += fn(pg, x + (w - 220) / 2, y + 16)
    o += L(x + 12, y + 212, x + w - 12, y + 212, ink, .8)
    o += T(x + 12, y + 238, title, 17 if len(title) < 27 else 15.5, "labb", ink)
    o += TW(x + 12, y + 262, line, w - 24, 16, "nar", ink, 21)
    return o


def alle():
    pg = Page("all", "09-alle-sider.svg", 2000, 1400, "Fraktbrev: alle andre sider som blanketter",
              "Kontaktark gruppert per rolle: Student, Faglærer og Admin, hver side med tittel og én linje.")
    cols = 7
    tw, th, gap = 258, 336, 16
    mx = (2000 - cols * tw - (cols - 1) * gap) / 2
    flat = []
    for role, col, ink, ps in PAGES:
        for p in ps:
            flat.append((role, col, ink, p))
    rowy = [56, 506, 956]
    for r in range(3):
        cells = flat[r * cols:(r + 1) * cols]
        # grupper i raden
        i = 0
        while i < len(cells):
            role, col, ink = cells[i][:3]
            j = i
            while j < len(cells) and cells[j][0] == role:
                j += 1
            bx = mx + i * (tw + gap) - 8
            bw = (j - i) * (tw + gap) - gap + 16
            pg.add(fanerad_shape(bx, rowy[r] - 42, 190, 44, col, None if False else col, 1))
            pg.add(T(bx + 16, rowy[r] - 12, role, 22, "disp", ink))
            pg.add(R(bx, rowy[r], bw, th + 20, "#34323C", col, 2))
            i = j
        for k, (role, col, ink, (title, line, fill, fn)) in enumerate(cells):
            pg.add(thumb(pg, mx + k * (tw + gap), rowy[r] + 10, tw, th, title, line, fill, fn))
    pg.add(demo(mx, 1370))
    pg.save()
