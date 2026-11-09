"""Spillsidene: 04 student-hjem, 05 hovedskjermen, 06 storyboardet."""
from c06_ink import *  # noqa: F403


def ministrip(x, y, week, s=.3):
    st = state(week, str(orders()[week - 1]))
    h = 150
    return g(f"translate({x:.1f} {y:.1f}) scale({s})",
             rute1(0, 0, 374, h, st, loud=False, tilt=(0, 0, 0, 0)),
             rute2(382, 0, 374, h, st, tilt=(0, 0, 0, 0)),
             rute3(764, 0, 374, h, st, tilt=(0, 0, 0, 0), confirmed=True, ghost_on=False))


def neighbor(x, y, w, h, role, status, wait=None, me=False, ki=False, dot=None):
    name = "Sara (deg)" if me else NAMES[role]
    o = [ibox(x, y, w, h, WHITE if status == "Klar" else YEL, dot, 2.6)]
    fy = y + h - 74
    s = {"Detaljist": .72, "Grossist": .66, "Distributør": .56, "Fabrikk": .66}[role]
    o.append(fig(x + w / 2, fy, role, s, "tenker" if status != "Klar" else "rolig", ki=ki))
    o.append(iline(x + 6, fy, x + w - 6, fy, 1.8))
    o.append(T(x + w / 2, fy + 18, name, 15, "hb", INK, "middle"))
    o.append(T(x + w / 2, fy + 34, role, 13.5, "h", INK, "middle"))
    if status == "Klar":
        o.append(ic_check(x + w / 2 - 19, fy + 50, .85) + T(x + w / 2 - 8, fy + 55, "Klar", 16, "hb"))
    else:
        o.append(ic_hour(x + 12, fy + 51, .75))
        o.append(T(x + 20, fy + 54, status, 13.5, "hb"))
        if wait:
            o.append(T(x + 20, fy + 69, wait, 13.5, "hb"))
    return "".join(o)


def chain_status(x, y, w, h, sara_ready=True):
    nw = (w - 3 * 5) / 4
    o = []
    for i, role in enumerate(ROLES):
        me = role == "Grossist"
        if role == "Fabrikk":
            o.append(neighbor(x + i * (nw + 5), y, nw, h, role, "Tenker...", "3 min"))
        elif me and not sara_ready:
            o.append(neighbor(x + i * (nw + 5), y, nw, h, role, "Tenker...", me=True))
        else:
            o.append(neighbor(x + i * (nw + 5), y, nw, h, role, "Klar", me=me))
    return "".join(o)


def compact_numbers(x, y, w, st, h=50):
    items = [("Lager", st["lager"]), ("Restordre", st["restordre"]), ("Ordre", st["innkommende_ordre"]), ("Levering", st["levering"]), ("Sendt", st["sendt"])]
    widths = [58, 88, 62, 80, 62]
    k = (w - 4 * 3) / sum(widths)
    o = []
    cx = x
    for (lab, val), wd in zip(items, widths):
        wd *= k
        o.append(plain(cx, y, wd, h, WHITE, 2))
        o.append(T(cx + 5, y + 17, lab, 14, "hb"))
        o.append(T(cx + 5, y + h - 7, val, 20, "d"))
        cx += wd + 3
    return "".join(o)


# ---- skjermene i storyboardet ---------------------------------------------------------------------
def screen_c():
    st = state(11, "24")
    st2 = dict(st, paa_vei_foer_ordre=40)
    o = [head(st), rute3(8, 88, 374, 170, st2, confirmed=True)]
    o.append(compact_numbers(8, 266, 374, st))
    o.append(chain_status(8, 324, 374, 246))
    o.append(ic_hour(16, 593, .9))
    o.append(T(28, 599, "Venter på Jonas (Fabrikk), 3 min", 19, "hb"))
    o.append(T(12, 624, "Uka går videre når alle har bestilt.", 17))
    o.append(T(12, 645, "Du kan legge fra deg telefonen.", 17))
    o.append(history(8, 656, 374, st, extra=24))
    o.append(button(8, 716, 374, 54, "Bla tilbake i albumet", "sec", 19))
    o.append(T(12, 796, "Ordren din er låst.", 15.5, "h", SOFT))
    o.append(T(300, 796, "Demodata", 14.5, "hb"))
    return "".join(o)


def screen_d():
    st = state(12)
    o = [f'<rect x="0" y="0" width="390" height="844" rx="32" fill="{CYA}"/>',
         f'<rect x="0" y="0" width="390" height="844" rx="32" fill="{dots("dW")}"/>']
    # Uke 11 blir lagt i albumet
    o.append(g("rotate(-4 195 90)", ministrip(26, 44, 11, .295)))
    o.append(plain(24, 122, 342, 44, WHITE, 2))
    o.append(T(36, 151, "Uke 11: du sa 24. Lagt i albumet.", 20, "hb"))
    # ny side
    o.append(ibox(24, 180, 342, 150, YEL, None, 3.4))
    o.append(T(195, 276, "UKE 12", 58, "d", INK, "middle"))
    o.append(sfx(320, 208, "FLIPP!", 28, 7, MAG))
    # bilene har rykket ett hakk fram
    o.append(plain(24, 348, 342, 104, WHITE, 2.6))
    o.append(T(36, 372, "Bilene rykker ett hakk", 17, "hb"))
    gr = 420
    o.append(iline(30, gr + 1, 360, gr + 1, 2))
    x = 44
    anim = ('<animateTransform attributeName="transform" type="translate" values="66 0;0 0;0 0" keyTimes="0;.28;1" '
            'calcMode="spline" keySplines=".16 1 .3 1;0 0 1 1" dur="6s" repeatCount="indefinite" additive="sum"/>')
    cars = []
    for u, l in st["vans"]:
        cars.append(van(x, gr, l))
        cars.append(T(x + van_w(l) / 2, gr + 19, f"Uke {u}", 14, "h", INK, "middle"))
        x += max(van_w(l), 40) + 18
    o.append(f'<g>{"".join(cars)}{anim}</g>')
    # nye tall
    o.append(plate(24, 466, 108, 62, "Levering", str(st["levering"]), 26))
    o.append(plate(141, 466, 108, 62, "Ordre", str(st["innkommende_ordre"]), 26))
    o.append(plate(258, 466, 108, 62, "Restordre", str(st["restordre"]), 26))
    o.append(plate(24, 536, 108, 62, "På vei", str(st["paa_vei_foer_ordre"]), 26))
    o.append(plate(141, 536, 225, 62, "Totalkostnad", nok(st["kost_sum"]), 22))
    # bladhjørne
    o.append(path("M326 330L366 290V330Z", WHITE, INK, 2.8))
    o.append(button(24, 632, 342, 62, "Hopp over", "sec", 24))
    o.append(plain(24, 704, 342, 90, WHITE, 2))
    o.append(T(195, 729, "Går videre av seg selv,", 17, "hb", INK, "middle"))
    o.append(T(195, 751, "aldri over 2 sekunder.", 17, "hb", INK, "middle"))
    o.append(T(195, 780, "Demodata", 14, "hb", INK, "middle"))
    o.append(f'<rect x="165" y="11" width="60" height="7" rx="3.5" fill="{INK}"/>')
    return "".join(o)


def screen_e():
    o = []
    # rute 1: Pause
    o.append(ibox(8, 36, 374, 208, PAPER, "dc", 3))
    o.append(ibox(16, 44, 358, 60, WHITE, None, 2.2, mis=(0, 0)))
    o.append(ic_pause(36, 74, 1.5))
    o.append(T(58, 66, "Pause til i kveld 19:00", 21, "hb"))
    o.append(T(58, 90, "Mikkel satte pausen. Ingen KI tar over nå.", 15.5))
    for i, r in enumerate(ROLES):
        o.append(fig(66 + i * 86, 232, r, .85 if r != "Distributør" else .7, "rolig"))
    o.append(iline(16, 233, 374, 233, 2))
    # rute 2: KI-spiller tar setet
    o.append(ibox(8, 252, 374, 268, YEL, None, 3))
    o.append(plain(16, 260, 358, 60, WHITE, 2))
    o.append(T(26, 283, "19:00 er passert. Jonas er borte.", 20, "hb"))
    o.append(T(26, 306, "Sara satte inn KI-spiller, så dere kan spille videre.", 15.5))
    # tom plass for Jonas, stiplet, og roboten i setet
    o.append(path("M-32 -74H32L17 -22H-17Z", fill="none", sw=2, extra=' stroke-dasharray="5 5" transform="translate(70 451) scale(.92)"'))
    o.append(circ(70, 451 - 88 * .92, 12, "none", INK, 2).replace("/>", ' stroke-dasharray="5 5"/>'))
    o.append(T(70, 345, "Jonas", 17, "hb", INK, "middle"))
    o.append(arrow(112, 400, 156, 400, bend=-4))
    o.append(fig(208, 450, "Fabrikk", 1.0, ki=True))
    o.append(iline(16, 451, 374, 451, 2))
    o.append(T(250, 366, "KI-spiller", 22, "hb"))
    o.append(T(250, 388, "i setet til Jonas", 16))
    o.append(T(250, 408, "Rolle: Fabrikk", 16))
    o.append(T(250, 428, "Ingen venter nå.", 16))
    o.append(T(16, 478, "Ukene KI-spilleren bestiller, står merket i", 15.5))
    o.append(T(16, 498, "albumet med KI, for alle fire.", 15.5))
    # rute 3: Jonas sin telefon
    o.append(ibox(8, 528, 374, 282, WHITE, None, 3.4, mis=(0, 0)))
    o.append(fig(58, 656, "Fabrikk", .95, "overrasket"))
    o.append(bubble(112, 540, 258, 96, (84, 588), "l", YEL, 2.6))
    o.append(T(128, 566, "Jonas: setet mitt spilles", 18, "hb"))
    o.append(T(128, 588, "av KI-spiller nå.", 18, "hb"))
    o.append(T(128, 614, "Jeg vil tilbake.", 18, "h"))
    o.append(iline(16, 657, 374, 657, 2))
    o.append(button(20, 670, 350, 56, "Ta tilbake setet", "prim", 22))
    o.append(T(20, 750, "Gjelder fra neste Uke.", 16, "hb"))
    o.append(T(20, 772, "Uker med KI-spiller teller ikke med i", 15))
    o.append(T(20, 791, "kravet ditt til Klassespillet.", 15))
    o.append(T(300, 791, "Demodata", 14, "hb"))
    return "".join(o)


def screen_f():
    o = []
    o.append(ibox(8, 36, 374, 66, YEL, None, 3))
    o.append(T(195, 86, "SLUTT", 44, "d", INK, "middle"))
    o.append(ibox(8, 110, 374, 138, WHITE, "dk", 3.4, mis=(0, 0)))
    o.append(plain(22, 122, 346, 114, WHITE, 2.4))
    o.append(T(195, 154, "Kjeden totalt", 24, "hb", INK, "middle"))
    o.append(T(195, 212, nok(FX["chain_total_cost"]), 36, "d", INK, "middle"))
    o.append(T(195, 276, "Slik fordeler regningen seg per Rolle", 18, "hb", INK, "middle"))
    pw, ph = 183, 170
    pos = [(8, 288), (199, 288), (8, 464), (199, 464)]
    for (px, py), role in zip(pos, ROLES):
        o.append(ibox(px, py, pw, ph, PAPER, None, 2.8, mis=(0, 0)))
        fy = py + ph - 8
        s = {"Detaljist": .95, "Grossist": .95, "Distributør": .84, "Fabrikk": .95}[role]
        o.append(T(px + 10, py + 32, nok(FX["total_cost_per_role"][role]), 19, "d"))
        o.append(iline(px + 8, py + 42, px + pw - 8, py + 42, 1.6))
        o.append(fig(px + 42, fy, role, s * (.92 if role != "Distributør" else .84), "rolig"))
        o.append(T(px + 88, py + 88, NAMES[role], 21, "hb"))
        o.append(T(px + 88, py + 112, role, 16))
    o.append(T(12, 662, "Samme kjede, samme regning. Hva som skjedde", 17))
    o.append(T(12, 684, "og hvorfor, leser dere sammen i Debriefen.", 17))
    o.append(button(8, 702, 374, 62, "Videre til Debrief", "prim", 22))
    o.append(T(12, 792, "Demodata", 14, "hb"))
    return "".join(o)


# ---- 05 hovedskjermen -----------------------------------------------------------------------------
def spill():
    p = Page("05-spill.svg", "spill", 1600, 1000,
             "Spillskjermen, Uke 11 med 24 tastet inn",
             "Tegneserie-konseptet: Uka er en stripe i tre ruter. Levering på kassen, ordre på telefonen, tomme hyller og restordre som lapper, og et tall i din egen snakkeboble. Telefon og laptop.")
    p.add(f'<rect x="0" y="0" width="480" height="1000" fill="{CYA}"/>',
          f'<rect x="0" y="0" width="480" height="1000" fill="{dots("dW")}"/>')
    st = state(11, "24")
    p.add(phone(42, 72, screen_week(st)))
    p.add(plain(30, 14, 396, 34, WHITE, 2.2))
    p.add(T(42, 38, "Telefon, 390 bred. Alt uten sideveis scrolling.", 20, "hb"))

    # laptop
    lx, ly, lw, lh = 512, 60, 1056, 700
    p.add(rr(lx - 12, ly - 12, lw + 24, lh + 24, 18, INK, INK, 2))
    p.add(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="4" fill="{PAPER}"/>')
    p.add(path(f"M{lx-60} {ly+lh+12}H{lx+lw+60}L{lx+lw+20} {ly+lh+40}H{lx-20}Z", INK, INK, 2))
    p.add(f'<rect x="{lx+lw/2-60}" y="{ly+lh+14}" width="120" height="7" rx="3" fill="{SOFT}"/>')
    # topplinje
    p.add(ibox(lx + 12, ly + 10, 150, 48, YEL, None, 3))
    p.add(T(lx + 22, ly + 46, "UKE 11", 30, "d"))
    p.add(mark(lx + 186, ly + 34, "Grossist", 9))
    p.add(T(lx + 204, ly + 32, "Grossist", 20, "hb"))
    p.add(T(lx + 204, ly + 52, "Sara, Spill 17", 16))
    p.add(ic_hour(lx + 350, ly + 34, 1))
    p.add(T(lx + 366, ly + 40, "Venter på deg og Jonas (Fabrikk), 3 min", 18))
    tx = lx + lw - 180
    p.add(plain(tx, ly + 10, 168, 48, WHITE, 2))
    p.add(T(tx + 8, ly + 27, "Totalkostnad", 15, "hb"))
    p.add(T(tx + 8, ly + 51, nok(st["kost_sum"]), 19, "d"))
    p.add(plain(tx - 92, ly + 14, 80, 40, WHITE, 2))
    p.add(ic_pause(tx - 76, ly + 34, .9) + T(tx - 64, ly + 40, "Pause", 16, "hb"))
    # stripen
    s = .925
    stripe = rute1(0, 0, 374, 262, st, tilt=(0, 0, 0, 0)) + rute2(380, 0, 374, 262, st, tilt=(0, 0, 0, 0)) + rute3(760, 0, 374, 262, st, tilt=(0, 0, 0, 0))
    p.add(g(f"translate({lx+6} {ly+70}) scale({s})", stripe))
    # albumet + venter
    ay = ly + 322
    p.add(T(lx + 14, ay + 18, "Albumet ditt: tidligere uker er ekte striper", 20, "hb"))
    for i, wk in enumerate([10, 9, 8]):
        y = ay + 32 + i * 66
        p.add(T(lx + 14, y + 20, f"Uke {wk}", 17, "hb"))
        p.add(T(lx + 14, y + 40, f"du sa {orders()[wk-1]}", 16))
        p.add(ministrip(lx + 84, y, wk, .48 * .92))
    y = ay + 32 + 3 * 66
    p.add(history(lx + 14, y + 12, 560, st, h=40))
    # høyre: venter og bekreft
    rx = lx + 610
    p.add(T(rx, ay + 18, "Hvem spillet venter på", 20, "hb"))
    nw = (lw - 610 - 14 - 15) / 4
    p.add(chain_status(rx, ay + 30, lw - 610 - 14, 176, sara_ready=False))
    p.add(button(rx, ay + 216, lw - 610 - 14, 56, "Bekreft ordre: 24", "prim", 22))
    p.add(T(rx, ay + 296, "Skriv tallet rett i boblen. Enter bekrefter.", 17))
    p.add(T(rx, ay + 318, "Ordren kan ikke endres etterpå.", 17, "h", SOFT))
    p.add(T(lx + lw - 76, ay + 342, "Demodata", 15, "hb"))

    # lesenøkkel under laptopen
    ky = 820
    p.add(ibox(512, ky, 330, 158, YEL, None, 3))
    p.add(T(528, ky + 34, "Bilens lengde er antall kasser.", 22, "hb"))
    p.add(Pg(528, ky + 60, "16 på vei er tre små biler. 24 blir en lang bil bak dem, før du bekrefter.", 296, 19))
    p.add(ibox(858, ky, 340, 158, WHITE, "dm", 3, mis=(0, 0)))
    p.add(plain(868, ky + 10, 320, 138, WHITE, 2))
    p.add(T(880, ky + 38, "En lapp per restordre.", 22, "hb"))
    p.add(Pg(880, ky + 64, "Snoren fylles mens hyllene står tomme. Tallet står alltid ved siden av, så tegningen gjemmer ingenting.", 296, 19))
    p.add(ibox(1214, ky, 354, 158, WHITE, None, 3, mis=(0, 0)))
    p.add(T(1230, ky + 38, "Boblen er hele beslutningen.", 22, "hb"))
    p.add(Pg(1230, ky + 64, "Ett tall i din egen boble, ingen knapper å lete etter. Systemet regner resten, og uka blir en side i albumet ditt.", 322, 19))
    p.save()


# ---- 06 storyboard ---------------------------------------------------------------------------------
def dynamikk():
    p = Page("06-spilldynamikk.svg", "dyn", 2100, 1200,
             "Spilldynamikken i seks ruter",
             "Storyboard: uka åpner, beslutningen, venter på de andre, uka går videre, Jonas er borte og KI-spiller tar setet, spillet slutter med kjedens totalkostnad.")
    s = .8
    pw = 390 * s
    gap = (2100 - 6 * pw) / 7
    notes = [
        ("A", "Uka åpner", "Varebilen dunker inn med levering, så ringer telefonen med ordren. To ruter, under ett sekund."),
        ("B", "Beslutningen", "Du skriver 24 i boblen. Tre små biler har 16 på vei, og den lange bilen dukker opp bak dem."),
        ("C", "Bekreftet", "Boblen får stempel og låses. Naboene kommer inn i smale ruter: Klar eller Tenker... 3 min."),
        ("D", "Uka går videre", "Stripen legges i albumet, bilene rykker ett hakk og Uke 12 er oppe. Maks 2 sekunder, kan hoppes over."),
        ("E", "Jonas er borte", "Pause først. Etter avtalt tid setter gruppa inn KI-spiller, merket KI. Jonas kan ta tilbake setet."),
        ("F", "Spillet slutter", "Ingen nedtelling, bare SLUTT. Kjedens totalkostnad først, så hver Rolle, så videre til Debrief."),
    ]
    screens = []
    screens.append(screen_week(state(11, "")))
    screens.append(screen_week(state(11, "24")))
    screens.append(screen_c())
    screens.append(screen_d())
    screens.append(screen_e())
    screens.append(screen_f())
    # bakgrunn: svakt raster som holder rutene sammen
    p.add(f'<rect x="0" y="0" width="2100" height="178" fill="{YEL}"/>')
    p.add(iline(0, 178, 2100, 178, 3))
    for i, ((let, ttl, note), sc) in enumerate(zip(notes, screens)):
        x = gap + i * (pw + gap)
        p.add(plain(x, 20, 50, 50, WHITE, 2.6))
        p.add(T(x + 25, 58, let, 32, "d", INK, "middle"))
        p.add(T(x + 60, 56, ttl, 25, "d"))
        p.add(Pg(x, 96, note, pw + 6, 20, "hb", lh=1.16))
        p.add(phone(x, 196, sc, s))
    # veien under rutene, en bil går gjennom hele storyboardet
    ry = 898
    p.add(iline(30, ry, 2070, ry, 3.4, j=2))
    car = g("translate(0 0) scale(1.4)", van(0, ry / 1.4, 8))
    p.add(f'<g>{car}<animateTransform attributeName="transform" type="translate" values="60 0;1960 0" dur="16s" repeatCount="indefinite"/></g>')
    for i in range(6):
        x = gap + i * (pw + gap) + pw / 2
        p.add(f'<rect x="{x-1}" y="{ry-6}" width="3" height="12" fill="{INK}"/>')
    # hva som gjør følelsen unik
    tx = 56
    p.add(T(tx, 958, "Du fyller ikke ut et skjema, du svarer i en stripe.", 40, "d"))
    text = ("Hver Uke er tre ruter du leser på sekunder, og den eneste handlingen er å skrive et tall i din egen snakkeboble. "
            "Bilene er tegnet til skala: 16 på vei er tre små biler, og 24 blir en lang bil som dukker opp bak dem før du bekrefter, så du ser med øynene at du legger lass på lass. "
            "Restordre er lapper på en snor mens hyllene står tomme, og tallet står alltid ved siden av tegningen. "
            "Etter noen kvelder har du ikke en tabell, men et album å bla i, og det er det albumet Debriefen leser tilbake.")
    p.add(Pg(tx, 1006, text, 1500, 28, lh=1.24))
    p.add(fig(1730, 1180, "Detaljist", 1.5, "rolig"))
    p.add(fig(1830, 1180, "Grossist", 1.5, "rolig"))
    p.add(fig(1920, 1180, "Distributør", 1.25, "rolig"))
    p.add(fig(2020, 1180, "Fabrikk", 1.5, "rolig", ki=True))
    p.add(iline(1660, 1181, 2090, 1181, 3))
    p.add(T(1660, 960, "Demodata", 18, "hb"))
    p.save()


# ---- 04 student-hjem --------------------------------------------------------------------------------
def screen_reg():
    o = []
    o.append(f'<rect x="0" y="0" width="390" height="250" rx="32" fill="{YEL}"/>')
    o.append(f'<rect x="0" y="0" width="390" height="250" rx="32" fill="{dots("dM")}" opacity=".35"/>')
    o.append(T(195, 74, "UKE", 44, "d", INK, "middle"))
    o.append(T(195, 118, "FOR UKE", 44, "d", INK, "middle"))
    for i, r in enumerate(ROLES):
        o.append(fig(70 + i * 84, 244, r, .9 if r != "Distributør" else .68, "glad" if r == "Grossist" else "rolig"))
    o.append(iline(0, 245, 390, 245, 3))
    o.append(bubble(20, 262, 350, 96, (70, 248), "t", WHITE, 2.8))
    o.append(T(38, 296, "Hei, Sara!", 25, "hb"))
    o.append(T(38, 322, "Bård har invitert deg til IBE160,", 18))
    o.append(T(38, 343, "Klasse class-of-1994.", 18))
    o.append(T(20, 388, "E-post", 16, "hb"))
    o.append(plain(20, 396, 350, 44, "#F1EBD8", 2))
    o.append(T(32, 424, "sara.nilsen@stud.example.no", 18, "h", SOFT))
    o.append(T(20, 464, "Navnet ditt", 16, "hb"))
    o.append(plain(20, 472, 350, 44, WHITE, 2))
    o.append(T(32, 500, "Sara Nilsen", 18))
    o.append(T(20, 540, "Velg passord", 16, "hb"))
    o.append(plain(20, 548, 350, 44, WHITE, 2))
    for i in range(8):
        o.append(f'<circle cx="{36+i*14}" cy="570" r="4" fill="{INK}"/>')
    o.append(button(20, 608, 350, 56, "Bli med i Klassen", "prim", 21))
    o.append(T(20, 692, "Invitasjonen er gyldig i 14 dager.", 17))
    o.append(T(20, 716, "Du får Spill og Rolle når Klasseøkten starter,", 17))
    o.append(T(20, 738, "ti. 24. nov. Du spiller på mobilen, når gruppa", 17))
    o.append(T(20, 760, "vil. Reglene får du før første ordre.", 17))
    o.append(T(20, 800, "Har du konto?", 17))
    o.append(T(118, 800, "Logg inn", 17, "hb"))
    o.append(iline(118, 804, 172, 804, 1.6))
    o.append(T(300, 800, "Demodata", 15, "hb"))
    o.append(f'<rect x="165" y="11" width="60" height="7" rx="3.5" fill="{INK}"/>')
    return "".join(o)


def screen_home():
    st = state(11)
    o = []
    # albumomslag
    o.append(ibox(8, 34, 374, 212, CYA, None, 3.4))
    o.append(T(22, 74, "Spill 17", 32, "d"))
    o.append(mark(30, 94, "Grossist", 8))
    o.append(T(44, 100, "Du er Grossist", 20, "hb"))
    o.append(plain(22, 112, 196, 120, WHITE, 2.4))
    o.append(T(32, 136, "Spillet venter på deg", 19, "hb"))
    o.append(T(32, 174, "Uke 11", 34, "d"))
    o.append(T(32, 200, "Jonas tenker også, 3 min", 16))
    o.append(T(32, 220, "Ida og Mikkel har bestilt", 16))
    o.append(fig(298, 236, "Grossist", 1.45, "tenker", arm="opp"))
    o.append(iline(226, 237, 380, 237, 2.4))
    o.append(button(8, 254, 374, 56, "Åpne Uke 11", "prim", 23))
    # sete-rekke
    o.append(T(12, 336, "Kjeden din", 18, "hb"))
    seats = [("Detaljist", "Ida"), ("Grossist", "deg"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]
    w = 92
    for i, (r, n) in enumerate(seats):
        x = 8 + i * (w + 2.6)
        o.append(ibox(x, 344, w, 90, WHITE, None, 2.2, mis=(0, 0)))
        o.append(T(x + w / 2, 364, n, 17, "hb", INK, "middle"))
        o.append(T(x + w / 2, 381, r, 14, "h", INK, "middle"))
        o.append(fig(x + w / 2, 431, r, .42 if r != "Distributør" else .36, mis=False))
    o.append(T(12, 460, "Kapitlene dine", 18, "hb"))
    steps = [("Klassespill", "pågår", "now"), ("Debrief", "etter spillet", "lock"), ("Quiz", "etter Debrief", "lock"),
             ("Replay", "etter quizen", "lock"), ("Individuell test", "etter Replay", "lock"), ("Rapport", "PDF til slutt", "lock")]
    for i, (a, b, k) in enumerate(steps):
        y = 468 + i * 34
        fill = YEL if k == "now" else WHITE
        o.append(plain(8, y, 374, 32, fill, 1.8, j=.4))
        o.append(ic_page(24, y + 16, .75, f=WHITE))
        o.append(T(38, y + 22, a, 18, "hb" if k == "now" else "h"))
        o.append(T(374, y + 22, b, 15.5, "hb" if k == "now" else "h", INK, "end"))
    y = 682
    o.append(plain(8, y, 183, 92, WHITE, 2))
    o.append(T(16, y + 22, "Neste frist", 16, "hb"))
    o.append(T(16, y + 50, "Spillfrist", 19))
    o.append(T(16, y + 76, "ti. 8. des", 19, "hb"))
    o.append(plain(199, y, 183, 92, WHITE, 2))
    o.append(T(207, y + 22, "Labtimer, Datalab A2", 16, "hb"))
    o.append(T(207, y + 47, "to. 26. nov 14:15", 16.5))
    o.append(T(207, y + 68, "ma. 30. nov 10:15", 16.5))
    o.append(T(207, y + 87, "+ 2 til", 14, "h", SOFT))
    o.append(T(12, 800, "Demodata", 15, "hb"))
    o.append(T(378, 800, nok(st["kost_sum"]) + " så langt", 15, "h", INK, "end"))
    return "".join(o)


def student_hjem():
    p = Page("04-student-hjem.svg", "hjem", 1000, 900,
             "Student: registrering og hjem under spill",
             "To telefoner. Venstre: Sara møter albumet første gang og registrerer seg. Høyre: hjem under spill med Spill 17, Rolle, kjeden, seks kapitler, frist og Labtimer.")
    p.add(f'<rect x="440" y="0" width="120" height="900" fill="{MAG}"/>',
          f'<rect x="440" y="0" width="120" height="900" fill="{dots("dW")}"/>')
    p.add(phone(30, 28, screen_reg()))
    p.add(phone(580, 28, screen_home()))
    p.add(plain(452, 90, 96, 80, WHITE, 2.2))
    p.add(T(500, 120, "Første", 17, "hb", INK, "middle") + T(500, 142, "møte", 17, "hb", INK, "middle"))
    p.add(arrow(460, 190, 432, 240, bend=-8))
    p.add(plain(452, 670, 96, 80, WHITE, 2.2))
    p.add(T(500, 700, "Under", 17, "hb", INK, "middle") + T(500, 722, "spill", 17, "hb", INK, "middle"))
    p.add(arrow(540, 640, 570, 590, bend=-8))
    p.save()
