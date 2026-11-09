"""Bygger de 9 SVG-filene for konsept 04 Miniatyrlandet. Kjør: uv run python build.py [05 06 ...]"""
import sys

from c04_lib import *
from c04_game import *
from c04_pages import page_01, page_02, page_03, page_04, page_07, page_08, page_09


def page_05():
    pg = Page("05-spill.svg", "spill", 1600, 1000, "Kjeden: spillskjermen, Uke 11",
              "Saras lagerhall i Uke 11 sett som diorama: tom hall, kø av varebiler for 13 i restordre, fire biler med 16 kasser på vei, 24 tastet inn. Samme skjerm på telefon og laptop.", FJORD_D)
    scr, tally = game_screen(pg)
    assert tally.full == 16 and tally.owed == 13, (tally.full, tally.owed)
    pg.add(phone(pg, 60, 78, 1.0, scr))
    pg.add(T(60, 48, "Telefon, 390 bred", 15, 800, FJORD_P))

    # laptop
    lx, ly, lw, lh = 500, 44, 1060, 610
    pg.add(T(lx, 34, "Samme hall på laptop i Labtimen", 15, 800, FJORD_P))
    pg.add(R(lx, ly, lw, lh, 18, "#0A1E26", "#33505B", 1.2))
    sx, sy, sw, sh = lx + 12, ly + 12, lw - 24, lh - 24
    pg.add(f'<path d="M{lx - 26} {ly + lh} H{lx + lw + 26} l-20 22 H{lx - 6} Z" fill="#17323D"/>')
    s = WEEKS[11]["seats"]["Grossist"]
    inner = R(0, 0, sw, 58, 0, FJORD)
    inner += T(20, 42, "Uke 11", 36, 800, WHITE, "b")
    inner += role_icon("Grossist", 130, 20, 20, WHITE)
    inner += T(156, 28, "Grossist", 15, 800, WHITE)
    inner += T(156, 46, "Spill 17", 13, 700, FJORD_P)
    inner += T(sw - 20, 24, "Totalkostnad", 13, 700, FJORD_P, "n", "end")
    inner += T(sw - 20, 48, kr(s["kost_sum"]), 24, 800, WHITE, "b", "end", num=True)
    dw = 620
    k = dw / 390
    dh = sh - 58
    d, t2 = diorama(pg, 0, 13, slots_for(11), H=dh / k)
    assert t2.full == 16 and t2.owed == 13
    inner += G(d, f"translate(0 58) scale({k:.4f})")
    rx = dw
    rw = sw - dw
    y = 58
    inner += numbers(y, s, rw, rx)
    y += 126
    inner += history(y, 11, rw, rx)
    y += 56
    inner += waiting(y, STATUS_11, rw, rx)
    y += 106
    # telleregel
    inner += R(rx, y, rw, 52, 0, FJORD_P)
    inner += ic_crate(rx + 12, y + 8, 16)
    inner += T(rx + 34, y + 21, "1 palle = 4 kasser", 13, 800, INK)
    inner += ic_van(rx + 12, y + 30, 20)
    inner += T(rx + 38, y + 42, "1 bil = 4 kasser", 13, 800, INK)
    inner += ic_van(rx + 170, y + 30, 20, dashed=True)
    inner += T(rx + 196, y + 42, "Stiplet = du skylder", 13, 800, INK)
    inner += T(rx + 170, y + 21, "Tell selv: det stemmer.", 13, 700, MUTED)
    y += 52
    inner += order_panel(y, "24", s, "decide", rw, rx, h=sh - y)
    clip = pg.clip(0, 0, sw, sh, 6)
    pg.add(G(f'<g clip-path="{clip}">{inner}</g>', f"translate({sx} {sy})"))

    # notat
    ny = 736
    pg.add(T(lx, ny, "Tell kassene, og du har svaret.", 42, 800, WHITE, "b"))
    pg.add(PS(lx, ny + 42, "Hallen står tom, så Lager er 0. Fire røde biler venter ved porten med 13 tomme rammer, så Restordre er 13. Fire blå biler er på veien med 16 kasser, så På vei er 16.", 500, 18, 1.4, 600, FJORD_P))
    pg.add(PS(lx + 548, ny + 42, "Tallene står likevel fast under modellen, for beslutningen skal ta sekunder, kveld etter kveld. Tastefeltet tegner ordren som biler med en gang: seks stiplede mot fire på veien.", 500, 18, 1.4, 600, FJORD_P))
    pg.add(T(lx + 548, ny + 160, "Tåka i begge ender skjuler naboene og resten av kjeden.", 18, 800, WHITE))
    pg.add(T(60, 960, "Demodata: Spill 17, Sara, Grossist.", 14, 700, FJORD_P))
    pg.write()


def caption(x, y, w, head, body):
    out = T(x, y, head, 20, 800, WHITE, "b")
    out += PS(x, y + 25, body, w, 15, 1.34, 600, FJORD_P)
    return out


def page_06():
    pg = Page("06-spilldynamikk.svg", "dyn", 2100, 1200, "Kjeden: spilldynamikk i seks ruter",
              "Storyboard av én Uke og ett spill: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter.", FJORD_D)
    scale = 0.82
    pw = 390 * scale
    gap = 24
    xs = [30 + i * (pw + gap) for i in range(6)]
    top = 84
    pg.add(T(30, 54, "En Uke i modellen: seks øyeblikk", 34, 800, WHITE, "b"))
    pg.add(T(2070, 54, "Demodata", 15, 700, FJORD_P, "n", "end"))

    # A: uka åpner
    def plate_a(iso):
        o = plate(150, 262, "Levering 4 kom, 4 gikk rett ut", 13, OKER_L, INK, w=210, stroke=OKER_D)
        return o

    a, t = game_screen(pg, 11, "", "open", gate_van=4, extra_plate=lambda iso: (
        plate(306, 236, "Levering 4 ved porten", 13, OKER_L, INK, w=156, stroke=OKER_D)
        + plate(306, 264, "Ny ordre inn: 8", 13, OKER_L, INK, w=118, stroke=OKER_D)))
    # B: beslutningen
    def plate_b(iso):
        return plate(*(iso.p(6.9, -6.3, 0)[0] - 42, iso.p(6.9, -6.3, 0)[1] + 44), "", 1) if False else ""

    b, t = game_screen(pg, 11, "24")
    assert t.full == 16 and t.owed == 13
    # C: sendt, kameraet trekker seg ut
    s11 = WEEKS[11]["seats"]["Grossist"]
    c = header(11, s11["kost_sum"])
    c += G(road_view(pg, STATUS_11_DONE, H_SCENE, courier_at=(214, 20), courier_label="Ordre 24"), "translate(0 84)")
    y = 84 + H_SCENE
    c += numbers(y, s11)
    y += 126
    c += history(y, 11)
    y += 56
    c += waiting(y, STATUS_11_DONE)
    y += 106
    c += order_panel(y, "24", s11, "sent")
    # D: uka går videre
    s12 = WEEKS[12]["seats"]["Grossist"]
    d, t = diorama(pg, 0, 20, slots_for(12), motion=True, H=H_SCENE)
    assert t.full == 36 and t.owed == 20, (t.full, t.owed)
    dd = header(12, s12["kost_sum"]) + G(d, "translate(0 84)")
    y = 84 + H_SCENE
    dd += numbers(y, s12)
    y += 126
    dd += history(y, 12, label="Ordre på 24 ligger i historikken")
    y += 56
    dd += R(0, y, 390, 844 - y, 0, FJORD_D)
    dd += T(195, y + 40, "Alt kjører ett hakk", 26, 800, WHITE, "b", "middle")
    dd += PS(195, y + 66, "Bilene rykker én uke nærmere, køen vokser fra 13 til 20, kosten øker med 20,00 kr.", 340, 14, 1.3, 600, FJORD_P, a="middle")
    # framdrift for overgangen, aldri over 2 sek
    bx, by, bw = 24, y + 118, 342
    dd += R(bx, by, bw, 10, 5, "#2A7686")
    dd += R(bx, by, bw * 0.55, 10, 5, OKER_L, extra=None) if False else (
        f'<rect x="{bx}" y="{by}" height="10" rx="5" fill="{OKER_L}" width="{bw * 0.7:.0f}">'
        f'<animate attributeName="width" dur="5s" repeatCount="indefinite" values="0;{bw};{bw}" keyTimes="0;0.4;1"/></rect>')
    dd += T(bx, by + 30, "Maks 2 sekunder", 14, 700, FJORD_P)
    dd += R(232, by + 22, 134, 44, 10, WHITE)
    dd += ic("skip", 248, by + 36, 16, INK, 2)
    dd += T(272, by + 50, "Hopp over", 17, 800, INK, "b")
    # E: Jonas er borte
    s13 = WEEKS[13]["seats"]["Grossist"]
    st_e = [("Detaljist", "Ida", "Har bestilt", True, False), ("Grossist", "Sara", "Venter: deg", False, False),
            ("Distributør", "Mikkel", "Har bestilt", True, False), ("Fabrikk", "KI-spiller", "Har bestilt", True, True)]
    e = header(13, s13["kost_sum"])
    e += G(road_view(pg, st_e, H_SCENE), "translate(0 84)")
    y = 84 + H_SCENE
    e += numbers(y, s13)
    y += 126
    e += R(0, y, 390, 844 - y, 0, WHITE)
    e += ic("pause", 14, y + 8, 18, FJORD_D, 2.6)
    e += PS(40, y + 21, "Dere satte Pause til i går 19:00, og Jonas kom ikke. Ida satte inn en KI-spiller.", 340, 14, 1.26, 700)
    e += ki_badge(14, y + 50, None, 20)
    e += PS(48, y + 62, "KI-spiller bestiller for Fabrikk. Merket står på fasaden. Jonas er varslet.", 330, 14, 1.26, 700)
    jy = y + 94
    e += R(14, jy, 362, 108, 10, FJORD_P)
    e += T(28, jy + 22, "Dette ser Jonas", 13, 800, FJORD_D)
    e += T(28, jy + 41, "KI-spiller bestiller for deg nå.", 14, 700, INK)
    e += R(28, jy + 52, 196, 44, 10, FJORD)
    e += T(126, jy + 80, "Ta tilbake setet", 19, 800, WHITE, "b", "middle")
    e += T(236, jy + 70, "Gjelder fra", 13, 700, INK)
    e += T(236, jy + 86, "neste Uke", 13, 700, INK)
    e += T(14, jy + 138, "Din ordre", 14, 800, INK)
    e += R(84, jy + 118, 66, 34, 6, WHITE, INK, 1.8)
    e += R(160, jy + 118, 216, 34, 8, "#DCE7EA")
    e += T(268, jy + 141, "Send ordre", 16, 800, "#4A6570", "b", "middle")
    # F: spillet slutter
    f = status_row()
    f += T(20, 66, "Spillet er ferdig", 34, 800, WHITE, "b")
    all_done = [("Detaljist", "Ida", "", True, False), ("Grossist", "Sara", "", True, False), ("Distributør", "Mikkel", "", True, False), ("Fabrikk", "Jonas", "", True, False)]
    f += G(road_view(pg, all_done, H_SCENE, signs=False), "translate(0 84)")
    f += plate(232, 84 + 318, "Alle vinduer lyser. Tåka står til Debriefen.", 13, WHITE, INK, w=296)
    y = 84 + H_SCENE
    f += R(0, y, 390, 844 - y, 0, WHITE)
    f += T(20, y + 26, "Kjeden totalt", 16, 800, MUTED)
    f += T(20, y + 70, kr(DATA["chain_total_cost"]), 46, 800, INK, "b", num=True)
    f += L(20, y + 84, 370, y + 84, LINE, 1)
    f += T(20, y + 106, "Per Rolle, i kjedens rekkefølge", 14, 800, MUTED)
    ty = y + 116
    mx = max(DATA["total_cost_per_role"].values())
    for i, role in enumerate(ROLES):
        v = DATA["total_cost_per_role"][role]
        ry = ty + i * 44
        f += role_icon(role, 20, ry + 3, 20)
        f += T(48, ry + 18, role, 15, 800, INK)
        f += T(370, ry + 18, kr(v), 17, 800, INK, "b", "end", num=True)
        f += R(48, ry + 25, 322 * v / mx, 9, 2, ROLE_INK[role])
    by = ty + 4 * 44 + 4
    f += R(20, by + 3, 350, 56, 12, FALU_D)
    f += R(20, by, 350, 56, 12, FALU)
    f += T(195, by + 36, "Gå videre til Debrief", 22, 800, WHITE, "b", "middle")

    frames = [a, b, c, dd, e, f]
    caps = [
        ("A  Uka åpner", "En bil ruller inn med 4 kasser, og de går rett ut til køen. 8 nye bestillinger legger seg bak. Hallen er fortsatt tom."),
        ("B  Beslutningen", "Sara taster 24. Seks stiplede biler dukker opp under fire ekte. 16 er alt på vei, men køen er rød og tett."),
        ("C  Bekreftet", "Kameraet trekker seg ut. Budbilen tar ordren inn i tåka. Tente vinduer sier hvem som har bestilt, og skiltene sier det samme."),
        ("D  Uka går videre", "Alt rykker ett hakk på 2 sekunder, og Hopp over står alltid framme. Ordren på 24 er nå seks biler i tre-ukers-feltet."),
        ("E  Jonas er borte", "Pause holder KI-spilleren unna til avtalen ryker. Da får Fabrikk et sekskantet KI-merke på fasaden, og Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle. Ingen rangering. Eneste vei videre er Debrief, der tåka letter."),
    ]
    for i, fr in enumerate(frames):
        pg.add(phone(pg, xs[i], top, scale, fr))
        pg.add(caption(xs[i], top + 844 * scale + 38, pw, *caps[i]))

    # piler mellom rutene
    ay = top + 844 * scale / 2
    for i in range(5):
        x = xs[i] + pw + 6
        pg.add(PATH(f"M{x} {ay - 8} l6 8 l-6 8", stroke=OKER_L, sw=3))

    by = 1000
    pg.add(L(30, by - 14, 2070, by - 14, "#2A7686", 1))
    pg.add(T(30, by + 26, "Du står i ditt eget hus.", 36, 800, WHITE, "b"))
    txt = ("Tall blir gjenstander her: en tom hall, biler som står i kø ved porten, kasser som kommer nærmere for hver uke. "
           "Du kjenner at køen er for lang før du har lest et eneste tall, og det er nettopp derfor du taster 24. "
           "Bilene som allerede er på vei står rett foran deg, men tåka gjemmer hvor de kommer fra og hva naboene gjør. "
           "Når Debriefen løfter tåka, ser du hele modellen du har stått i, og hvorfor køen flyttet seg oppover kjeden.")
    pg.add(PS(30, by + 62, txt, 1180, 19, 1.42, 600, FJORD_P))
    # telleregel
    tx = 1320
    pg.add(T(tx, by + 26, "Telleregelen", 24, 800, WHITE, "b"))
    pg.add(ic_crate(tx, by + 42, 24))
    pg.add(T(tx + 36, by + 62, "1 palle = 4 kasser. 2 brede og 2 høye, så alle synes.", 17, 700, FJORD_P))
    pg.add(ic_van(tx, by + 80, 28))
    pg.add(T(tx + 36, by + 96, "1 blå bil = 4 kasser på vei.", 17, 700, FJORD_P))
    pg.add(ic_van(tx, by + 114, 28, dashed=True))
    pg.add(T(tx + 36, by + 130, "1 rød bil = 4 tomme rammer: det du skylder.", 17, 700, FJORD_P))
    pg.write()


PAGES = {"01": page_01, "02": page_02, "03": page_03, "04": page_04, "05": page_05, "06": page_06, "07": page_07, "08": page_08, "09": page_09}

if __name__ == "__main__":
    only = sys.argv[1:] or PAGES.keys()
    for key in only:
        PAGES[key]()
        print("bygd", key)
