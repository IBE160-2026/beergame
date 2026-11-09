"""Experience-sidene: spill, dynamikk, debrief, studenthjem."""
from core import *  # noqa: F403


def laptop_game(doc, week=11, typed=24):
    """Samme skjerm som tre-spalters oppslag: 1040 x 660."""
    W, H = 1040, 660
    s = seat(week)
    ch = CYAN
    c = ch["c"]
    o = [R(0, 0, W, H, ch["g"])]
    # Venstre margspalte
    o.append(A(24, 58, "UKE 11", 44))
    o.append(T(24, 84, "Grossist, Spill 17", 15, "c09-k"))
    o.append(T(24, 104, "Totalkostnad", 14, "c09-m"))
    o.append(T(24, 124, f"{kr(s['kost_sum'])} kr", 18, "c09-k c09-tn"))
    o.append(T(24, 146, "Demodata", 13))
    o.append(L(24, 160, 170, 160, INK, 1.5))
    m, yy = margin_waiting(24, 184, default_people(), 14, 18)
    o.append(m)
    yy += 4
    o.append(L(24, yy - 14, 196, yy - 14, INK, 1.5))
    o.append(T(24, yy + 6, "På vei", 15, "c09-k c09-u"))
    o.append(P(24, yy + 28, "Kasser du har bestilt, men ikke fått ennå. Du har 16.", 14, 172, 18))
    o.append(T(24, yy + 98, "Restordre", 14, "c09-m c09-u"))
    o.append(T(24, yy + 120, "Forsinkelse", 14, "c09-m c09-u"))

    # Plakat i midten
    poster = (A(0, 0, s["restordre"], 390, c, stroke=INK, sw=13)
              + A(6, 96, "RESTORDRE", 96, INK)
              + A(6, 152, f"LAGER {s['lager']}", 50, INK))
    o.append(G(poster, 236, 440, rot=ANG))

    # Blokker
    blocks, top = stack(684, 536, [4, 4, 8], typed, ch, bw=28, bh=19, gap=2, cols=4, sg=6)
    o.append(blocks)
    o.append(A(684, 572, "16 PÅ VEI", 30))
    o.append(R(708, top + 18, 72, 44, PAPER))
    o.append(A(744, top + 54, f"+{typed}", 36, anchor="middle"))

    # Høyre spalte: tall og ordre
    x = 830
    items = [("Innkommende ordre", s["innkommende_ordre"]), ("Levering", s["levering"]),
             ("Sendt", s["sendt"]), ("Neste levering", s["neste_levering"])]
    for i, (lab, v) in enumerate(items):
        yy2 = 44 + i * 38
        o.append(T(x, yy2, lab, 14, "c09-m"))
        o.append(A(x + 186, yy2 + 6, v, 32, anchor="end"))
        o.append(L(x, yy2 + 14, x + 186, yy2 + 14, INK, 1))
    o.append(T(x, 216, "Dine ordrer, uke 1–10", 14, "c09-m"))
    hist = history(week)
    for i, v in enumerate(hist):
        o.append(T(x + 8 + i * 19, 238, v, 15, "c09-k c09-tn", anchor="middle"))
    o.append(L(x, 246, x + 186, 246, INK, 1.5))
    o.append(T(x, 272, "Din Ordre. Stryk, eller tast.", 14, "c09-k"))
    o.append(R(x, 282, 122, 104, PAPER, INK, 2.5))
    o.append(A(x + 61, 370, typed, 86, INK, "middle"))
    o.append(R(x + 128, 282, 58, 50, c, INK, 2.5))
    o.append(ic_up(x + 157, 307, INK))
    o.append(R(x + 128, 336, 58, 50, c, INK, 2.5))
    o.append(ic_down(x + 157, 361, INK))
    # slaget
    o.append(poly([(440, 660), (1040, 544), (1040, 660)], INK))
    o.append(A(846, 636, f"BEKREFT {typed}", 54, c, "middle", ANG))
    return "".join(o)


def page_05():
    d = Doc("spill", "05-spill", 1600, 1000, "Spillskjermen i Uke 11",
            "Saras spillskjerm midt i Uke 11 med 24 tastet inn. Hele siden har byttet til cyan blekk fordi hun står i restordre 13. "
            "16 på vei er tellende blokker, 24 ligger hvitt oppå til ordren er bekreftet.", OR)
    d.add(phone(d, 56, 78, game(d, 11, typed=24, shipments=[4, 4, 8]), 1.0, CY))
    d.add(A(56, 56, "TELEFON", 30))
    x0, y0 = 512, 78
    c = d.clip_rect(0, 0, 1040, 660, 6)
    d.add(G(R(-8, -8, 1056, 676, INK, r=12) + f'<g clip-path="url(#{c})">{laptop_game(d)}</g>', x0, y0))
    d.add(A(512, 56, "LAPTOP, SAMME UKE", 30))
    # Tre spalter under, som en magasinside
    notes = [
        ("Blekket er tilstanden",
         "Restordre gir cyan grunn over hele flaten, og ordet RESTORDRE står like stort. Går Sara over til lager, slår hele siden om til oransje i ett hardt skifte."),
        ("Du ser det du glemmer",
         "16 på vei står som 16 blokker. Når Sara stryker opp til 24, legger 24 hvite blokker seg oppå. Da ser hun med øynene hvor mye som kommer, før hun trykker."),
        ("Tre lag trykk",
         "Sifrene er motblekk med kontur. All lesetekst er overtrykk, nær svart, fordi oransje mot cyan bare gir 1,76:1. Hvitt finnes bare der du skriver."),
    ]
    for i, (h, b) in enumerate(notes):
        x = 512 + i * 352
        d.add(A(x, 788, h.upper(), 26))
        d.add(P(x, 816, b, 16, 320, 22))
    d.save()


def frame_A(d):
    o = [game(d, 11, shipments=[4, 4, 8], hl=("inn", "lev"))]
    bl = ""
    for i in range(4):
        bl += R(240 + (i % 2) * 22, 366 + (i // 2) * 15, 20, 13, OR, INK, 1.6)
    o.append(bl)
    o.append(f'<path d="M294 384 H288" stroke="{INK}" stroke-width="2.5" fill="none"/>')
    return "".join(o)


def frame_C(d):
    return game(d, 11, confirmed=24, shipments=[4, 4, 8])


def frame_D(d):
    """Bladskiftet: et oransje bånd feier over, ny side over, gammel under."""
    new = game(d, 12, slab=False, ordliste=False)
    old = game(d, 11, confirmed=24, shipments=[4, 4, 8], slab=False, ordliste=False)
    motion_vals = "0 0;0 560;0 -760;0 0"
    motion = (f'<animateTransform attributeName="transform" type="translate" values="{motion_vals}" '
              'keyTimes="0;0.45;0.4501;1" dur="2s" repeatCount="indefinite"/>')
    clip = d.clip_poly("0,-1400 390,-1400 390,366 0,442", motion)
    band = (poly([(0, 442), (390, 366), (390, 476), (0, 552)], OR, f'stroke="{INK}" stroke-width="3"')
            + A(196, 494, "UKE 12", 100, INK, "middle", ANG))
    o = [old, f'<g clip-path="url(#{clip})">{new}</g>', f"<g>{band}{motion}</g>"]
    o.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
    o.append(G(ic_skip(0, -14, OR, 1.6), 64, 806, rot=ANG))
    o.append(A(210, 806, "HOPP OVER", 54, OR, "middle", ANG))
    return "".join(o)


def frame_E(d):
    """Uke 26. Saras side er oransje, hun har lager. Jonas er borte, KI-spiller har setet."""
    s = seat(26)
    o = [R(0, 0, 390, 844, OR)]
    o.append(A(16, 50, "UKE 26", 34))
    o.append(T(374, 30, "Grossist, Spill 17", 14, "c09-k", anchor="end"))
    o.append(T(374, 49, f"Totalkostnad {kr(s['kost_sum'])} kr", 14, "c09-m c09-tn", anchor="end"))
    o.append(T(16, 70, "Demodata", 13))
    o.append(G(A(0, 0, s["lager"], 150, CY, stroke=INK, sw=7) + A(2, 50, "LAGER", 50), 22, 232, rot=ANG))
    o.append(T(192, 94, "Sara ser", 14, "c09-k"))
    m = [("done", "Ida", "Detaljist"), ("done", "Mikkel", "Distributør"), ("you", "Sara, deg", "Grossist")]
    my = 116
    for st, nm, sub in m:
        o.append(ic_check(192, my - 4) if st == "done" else ic_wait(192, my - 4, INK, .8))
        o.append(T(210, my, f"{nm}, {sub}", 13, "c09-m"))
        my += 19
    o.append(R(186, my - 14, 196, 44, INK))
    o.append(ki_tag(192, my + 2, INK, CY, 13))
    o.append(T(220, my + 2, "Jonas er KI-spiller", 13, "c09-k", CY))
    o.append(T(192, my + 22, "Fabrikk, 24 t uten Ordre", 13, "c09-m", CY))
    # Pause
    o.append(R(186, my + 38, 196, 44, OR, INK, 2.5))
    o.append(ic_pause(198, my + 60))
    o.append(T(218, my + 65, "Sett Pause", 15, "c09-k"))
    # Jonas sin side
    o.append(poly([(0, 410), (390, 334), (390, 844), (0, 844)], INK))
    o.append(A(20, 468, "JONAS, NÅR HAN ER TILBAKE", 32, CY, rot=ANG))
    o.append(T(20, 508, "Fabrikk, Spill 17", 14, "c09-k", CY))
    o.append(R(20, 526, 350, 118, CY))
    o.append(ki_tag(32, 556, CY, INK, 16))
    o.append(T(68, 556, "KI-spiller har setet ditt", 17, "c09-k"))
    o.append(P(32, 582, "Den har bestilt for deg siden Uke 25. Du kan ta setet tilbake når en ny Uke begynner.", 14, 322, 19))
    o.append(P(20, 668, "Uker med KI-spiller teller ikke som dine ordrer.", 14, 350, 19, fill=CY))
    o.append(poly([(0, 788), (390, 712), (390, 844), (0, 844)], CY))
    o.append(A(198, 806, "TA TILBAKE SETET", 40, INK, "middle", ANG))
    return "".join(o)


def frame_F(d):
    o = [R(0, 0, 390, 844, OR)]
    o.append(A(16, 50, "SPILLET ER SLUTT", 34))
    o.append(T(374, 46, "Demodata", 13, anchor="end"))
    o.append(G(A(0, 0, kr(F["chain_total_cost"]), 100, CY, stroke=INK, sw=6)
               + A(2, 46, "KR, HELE KJEDEN", 42), 22, 214, rot=ANG))
    y = 322
    o.append(T(16, y, "Slik fordelte det seg per Rolle", 14, "c09-k"))
    y += 12
    mx = max(F["total_cost_per_role"].values())
    for r in ROLES:
        v = F["total_cost_per_role"][r]
        nm = NAMES[r] + (", deg" if r == "Grossist" else "")
        o.append(T(16, y + 18, f"{r}, {nm}", 14, "c09-k" if r == "Grossist" else "c09-m"))
        o.append(T(374, y + 18, f"{kr(v)} kr", 14, "c09-k c09-tn", anchor="end"))
        o.append(R(16, y + 25, 358 * v / mx, 22, CY, INK, 2))
        if r == "Fabrikk":
            o.append(ki_tag(22, y + 41, CY, INK, 13))
            o.append(T(50, y + 41, "Uke 25, KI-spiller", 13, "c09-k"))
        y += 66
    o.append(P(16, y + 14, "Kostnaden er kjedens. Hvorfor den ble slik, ser dere i Debriefen.", 14, 340, 19))
    o.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
    o.append(A(196, 808, "VIDERE TIL DEBRIEF", 48, CY, "middle", ANG))
    return "".join(o)


def crop(d, week, x, y, s, h=440):
    c = d.clip_rect(0, 0, 390, h, 8)
    return G(R(-5, -5, 400, h + 10, INK, r=12) + f'<g clip-path="url(#{c})">{game(d, week, slab=False)}</g>', x, y, s)


def page_06():
    d = Doc("dyn", "06-spilldynamikk", 2100, 1200, "Spilldynamikk i seks ruter",
            "Storyboard: uka åpner, beslutningen 24 med 16 på vei, bekreftet og venter, bladskiftet til neste uke som kan hoppes over, "
            "Jonas er borte og KI-spiller tar setet, og spillet slutter med kjedens totalkostnad.", OR)
    d.add(A(39, 74, "EN UKE I TO BLEKK", 56))
    d.add(T(470, 72, "Demodata. Sara, Grossist, Spill 17.", 18, "c09-m"))
    scale = .8
    frames = [
        ("A", CY, frame_A(d), "Uka åpner",
         "Levering 4 og Ordre 8 lyser i svart plate. Fire blokker forlater stabelen. Restordre går fra 9 til 13, og siden er allerede cyan."),
        ("B", CY, game(d, 11, typed=24, shipments=[4, 4, 8]), "Beslutningen",
         "Sara stryker til 24. Hvite blokker legger seg oppå de 16. Alt annet ligger stille, og valget tar sekunder."),
        ("C", CY, frame_C(d), "Bekreftet",
         "Slaget låser tallet. Blokkene får blekk, og 40 er på vei. Marginen viser hvem det venter på: Jonas, Fabrikk, 3 min."),
        ("D", CY, frame_D(d), "Uka går",
         "Motblekket feier over som et bladskift. Under 2 sek, hopp over med ett trykk. Restordre 20 står på den nye siden."),
        ("E", OR, frame_E(d), "Jonas er borte",
         "Uke 26: Sara har lager, og siden er oransje. KI-spiller tar setet etter 24 t, merket i marginen. Pause holder KI-en ute. Jonas tar setet tilbake."),
        ("F", OR, frame_F(d), "Spillet slutter",
         "Kjedens totalkostnad kommer først og størst. Så per Rolle, uten plassering. Deretter ett trykk videre til Debrief."),
    ]
    for i, (letter, g, inner, h, note) in enumerate(frames):
        x = 39 + i * 342
        d.add(phone(d, x, 102, inner, scale, g))
        d.add(A(x, 846, f"{letter}. {h.upper()}", 34))
        d.add(P(x, 876, note, 18, 312, 24))
    # Bunnen: hva som er unikt
    d.add(L(39, 1000, 2061, 1000, INK, 3))
    d.add(A(39, 1050, "DU LESER DET IKKE. DU STÅR I DET.", 40))
    para = ("Blekket skifter over hele flaten i samme øyeblikk du går i restordre, så underskuddet kjennes før det er lest, "
            "og ordet står der likevel. Blokkene gjør det du ikke får se til noe du teller: 16 på vei står ved siden av 13 i restordre, "
            "og 24 hvite blokker legger seg oppå før du trykker. Du kan se at det blir mye, og likevel bestille det. "
            "Den erfaringen er det Debriefen senere bygger på.")
    d.add(P(39, 1084, para, 20, 1320, 28))
    # Første blekkskifte
    d.add(A(1430, 1036, "UKE 8", 30))
    d.add(crop(d, 8, 1430, 1046, .32))
    d.add(ic_arrow(1572, 1116, 1636, INK, 4))
    d.add(A(1650, 1036, "UKE 9: FØRSTE SKIFTE", 30))
    d.add(crop(d, 9, 1650, 1046, .32))
    d.add(P(1800, 1066, "Lager 4 blir Restordre 3, og hele siden bytter blekk.", 18, 250, 24))
    d.save()


def orders_chart(d, x, y, w, h, ground=CY, fs=14, sw=1.0, ymax=33, ticks=True):
    """Ordrer per Rolle over tid, til skala fra fixture. Rollene skilles med form, ikke bare farge."""
    def px(wk):
        return x + (wk - 1) / 35 * w

    def py(v):
        return y + h - v / ymax * h

    def series(role):
        return [(px(k), py(WEEKS[k]["seats"][role]["ordre"])) for k in range(1, 37)]

    def pts(ps):
        return " ".join(f"{a:.1f},{b:.1f}" for a, b in ps)

    o = []
    # Rutenett, svakt og tilbaketrukket
    for v in (10, 20, 30):
        o.append(L(x, py(v), x + w, py(v), INK, 1, 'stroke-dasharray="1 5"'))
        if ticks:
            o.append(T(x + 2, py(v) - 4, v, fs - 1, "c09-m c09-tn"))
    # Fabrikk: fylt motblekk. Distributør: skravert flate.
    fab = series("Fabrikk")
    o.append(poly([(x, y + h)] + fab + [(x + w, y + h)], OR if ground == CY else CY))
    o.append(f'<polyline points="{pts(fab)}" fill="none" stroke="{INK}" stroke-width="{2.5*sw}"/>')
    dis = series("Distributør")
    hid = d.hatch(INK, 7, 1.6)
    o.append(poly([(x, y + h)] + dis + [(x + w, y + h)], f"url(#{hid})"))
    o.append(f'<polyline points="{pts(dis)}" fill="none" stroke="{INK}" stroke-width="{2*sw}"/>')
    # Grossist: tykk strek med ring. Detaljist: prikket.
    gro = series("Grossist")
    o.append(f'<polyline points="{pts(gro)}" fill="none" stroke="{ground}" stroke-width="{10*sw}"/>')
    o.append(f'<polyline points="{pts(gro)}" fill="none" stroke="{INK}" stroke-width="{5.5*sw}"/>')
    det = series("Detaljist")
    o.append(f'<polyline points="{pts(det)}" fill="none" stroke="{ground}" stroke-width="{7*sw}"/>')
    o.append(f'<polyline points="{pts(det)}" fill="none" stroke="{INK}" stroke-width="{3*sw}" '
             f'stroke-dasharray="{1*sw} {6*sw}" stroke-linecap="round"/>')
    o.append(L(x, y + h, x + w, y + h, INK, 2))
    # Akse
    for wk in (1, 11, 36):
        a = "start" if wk == 1 else ("end" if wk == 36 else "middle")
        o.append(T(px(wk), y + h + fs + 3, f"Uke {wk}", fs - 1, "c09-m", anchor=a))

    # Direkte etiketter på toppene
    def tag(role, wk, lx, lval):
        """Etikett i svart plate. lx er venstre kant i uker, lval er høyden i kasser."""
        v = WEEKS[wk]["seats"][role]["ordre"]
        lab = f"{role} {str(F['amplification'][role]).replace('.', ',')}×"
        tw = len(lab) * fs * .56 + 10
        ax, ay = px(lx), py(lval)
        return (L(px(wk), py(v), min(ax + tw, max(ax, px(wk))), ay + 5, INK, 1.5)
                + R(ax, ay - fs + 1, tw, fs + 6, INK)
                + T(ax + 5, ay + 2, lab, fs, "c09-k", ground))

    o.append(tag("Fabrikk", 18, 20, 32.2))
    o.append(tag("Grossist", 11, 1.4, 27))
    o.append(tag("Distributør", 15, 1.4 if w < 500 else 4, 30.8))
    o.append(tag("Detaljist", 34, 27 if w < 500 else 28.5, 16))
    return "".join(o)


def legend_row(d, x, y, fs=13, step=None, ground=CY):
    """Tegnforklaring: form pluss navn, slik at ingen rolle er bare en farge."""
    o = []
    step = step or 90
    hid = d.hatch(INK, 6, 1.4)
    items = [
        ("Detaljist", f'<line x1="0" y1="-4" x2="26" y2="-4" stroke="{INK}" stroke-width="3" stroke-dasharray="1 6" stroke-linecap="round"/>'),
        ("Grossist", f'<line x1="0" y1="-4" x2="26" y2="-4" stroke="{INK}" stroke-width="5.5"/>'),
        ("Distributør", R(0, -10, 26, 12, f"url(#{hid})", INK, 1.5)),
        ("Fabrikk", R(0, -10, 26, 12, OR if ground == CY else CY, INK, 1.5)),
    ]
    for i, (n, mark) in enumerate(items):
        col, row = i % 2, i // 2
        o.append(G(mark + T(32, 0, n, fs, "c09-m"), x + col * step, y + row * 21))
    return "".join(o)


SARA_TEXT = ("Vi lå etter og bestilte mer og mer. Jeg tror kundene ville ha stadig flere kasser, "
             "så jeg la inn 24 for å ta det igjen.")


def debrief_1(d):
    o = [R(0, 0, 390, 844, OR)]
    o.append(A(16, 50, "DEBRIEF, SPILL 17", 34))
    o.append(T(16, 70, "Demodata", 13))
    o.append(G(A(0, 0, "HVA SKJEDDE", 64) + A(0, 62, "I KJEDEN?", 64), 18, 178, rot=ANG))
    o.append(P(16, 276, "Kjeden kostet 2 266,00 kr. Skriv med egne ord hvorfor. Forklaringen din blir ingressen i artikkelen om spillet.", 15, 356, 21))
    o.append(T(16, 368, "Din Forklaring", 14, "c09-k"))
    o.append(R(16, 376, 358, 186, PAPER, INK, 2.5))
    o.append(P(28, 404, SARA_TEXT, 16, 334, 23, cls="c09-m"))
    o.append(R(84, 458, 2, 20, INK))
    o.append(T(16, 590, "De andre", 14, "c09-k"))
    for i, (nm, r, st) in enumerate([("Ida", "Detaljist", "levert"), ("Mikkel", "Distributør", "skriver"), ("Jonas", "Fabrikk", "levert")]):
        yy = 612 + i * 21
        o.append(ic_check(17, yy - 4) if st == "levert" else ic_wait(18, yy - 4, INK, .8))
        o.append(T(36, yy, f"{nm}, {r}: {st}", 14, "c09-m"))
    # Låst avsløring
    o.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
    o.append(A(198, 808, "LEVER FORKLARINGEN", 44, CY, "middle", ANG))
    o.append(ic_lock(17, 684, INK, 1))
    o.append(T(36, 690, "Neste side er låst til alle har levert", 14, "c09-k"))
    return "".join(o)


def debrief_2(d):
    """Den stille siden. Etter hele spillet: papir, og nesten ingenting."""
    o = [R(0, 0, 390, 844, PAPER)]
    cx = 195
    o.append(T(cx, 424, "Kundeetterspørsel", 13, "c09-m", anchor="middle"))
    o.append(T(cx - 22, 452, "4", 21, "c09-k c09-tn", anchor="middle"))
    o.append(ic_arrow(cx - 11, 445, cx + 11, INK, 2))
    o.append(T(cx + 22, 452, "8", 21, "c09-k c09-tn", anchor="middle"))
    o.append(T(cx, 476, "i Uke 5. Så aldri mer.", 13, "c09-b", anchor="middle"))
    o.append(T(cx, 826, "Demodata", 13, "c09-b", anchor="middle"))
    return "".join(o)


def debrief_3(d):
    o = [R(0, 0, 390, 844, CY)]
    o.append(G(A(0, 0, "KUNDEN BESTILTE 8.", 46) + A(0, 50, "FABRIKKEN", 46) + A(0, 100, "BESTILTE 31.", 46), 22, 114, rot=ANG))
    o.append(orders_chart(d, 0, 246, 390, 410, CY, 13, 1.0, ticks=True))
    o.append(R(0, 677, 390, 76, CY))
    o.append(legend_row(d, 16, 694, 13, 130))
    o.append(T(16, 742, "Ordrer per uke, kasser. Demodata.", 13))
    o.append(poly([(0, 800), (390, 724), (390, 844), (0, 844)], INK))
    o.append(A(198, 822, "DITT ØYEBLIKK", 42, CY, "middle", ANG))
    return "".join(o)


def debrief_4(d):
    s = seat(11)
    o = [R(0, 0, 390, 844, CY)]
    o.append(G(A(0, 0, "UKE 11", 72, OR, stroke=INK, sw=4) + A(176, -34, "DITT", 30) + A(176, 0, "ØYEBLIKK", 30), 22, 112, rot=ANG))
    o.append(T(374, 30, "Demodata", 13, anchor="end"))
    y = 148
    o.append(T(16, y, "Hva du så", 14, "c09-x"))
    for i, (lab, v) in enumerate([("Lager", s["lager"]), ("Restordre", s["restordre"]), ("Ordre inn", s["innkommende_ordre"]), ("På vei", s["paa_vei_foer_ordre"])]):
        xx = 16 + i * 69
        o.append(T(xx, y + 20, lab, 13, "c09-m"))
        o.append(A(xx, y + 54, v, 32))
    # Hva du bestilte
    o.append(T(300, y, "Du bestilte", 14, "c09-x"))
    o.append(A(300, y + 72, 24, 76, OR, stroke=INK, sw=4))
    y = 240
    o.append(L(16, y, 374, y, INK, 1.5))
    o.append(T(16, y + 22, "Hva det kostet senere", 14, "c09-x"))
    o.append(P(16, y + 42, "Ordren kunne tidligst komme i Uke 15. I Uke 29 hadde du Lager 30. Lageret fra Uke 25 til 36 kostet deg 111,50 kr.", 14, 356, 19))
    y = 348
    o.append(L(16, y, 374, y, INK, 1.5))
    o.append(T(16, y + 22, "Hva de andre så i Uke 11", 14, "c09-x"))
    rows = [("Detaljist", "Ida"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]
    yy = y + 44
    for r, n in rows:
        ss = seat(11, r)
        state = f"Restordre {ss['restordre']}" if ss["restordre"] else f"Lager {ss['lager']}"
        o.append(T(16, yy, f"{n}, {r}", 14, "c09-m"))
        o.append(T(374, yy, f"{state}, bestilte {ss['ordre']}", 14, "c09-k c09-tn", anchor="end"))
        yy += 21
    o.append(P(16, yy + 4, "24-en din nådde Mikkel i Uke 13. Der gikk Lager 12 til Restordre 7.", 14, 356, 19))
    # KI-tekst
    y = 520
    o.append(R(0, y, 390, 152, INK))
    o.append(ki_tag(16, y + 26, INK, CY, 13))
    o.append(T(46, y + 26, "KI-generert, kan ta feil", 14, "c09-k", CY))
    o.append(P(16, y + 52, "Du så 13 i restordre og 16 på vei. Det som var på vei, lå ikke i lageret ditt ennå, og 24 ble lagt oppå det. Samtidig så Mikkel Lager 14 og bestilte 2.", 14, 356, 20, fill=CY))
    # slag
    o.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
    o.append(A(198, 808, "TIL DEBRIEF-QUIZ", 48, CY, "middle", ANG))
    return "".join(o)


def debrief_5(d):
    o = [R(0, 0, 390, 844, OR)]
    o.append(A(16, 50, "DEBRIEF-QUIZ", 34))
    o.append(T(374, 46, "Demodata", 13, anchor="end"))
    o.append(P(16, 90, "Kundeetterspørselen endret seg én gang. Hvorfor ble ordrene større jo lenger fra kunden du kom?", 18, 356, 25, cls="c09-k"))
    # Svar A, valgt og feil
    y = 188
    o.append(R(16, y, 358, 62, INK))
    cross = f'<path d="M0 0 L12 12 M12 0 L0 12" stroke="{OR}" stroke-width="3"/>'
    o.append(G(cross, 28, y + 15))
    o.append(T(52, y + 26, "Ditt svar: Kundene ville ha", 15, "c09-k", OR))
    o.append(T(52, y + 47, "stadig mer.", 15, "c09-k", OR))
    y += 70
    o.append(R(16, y, 358, 82, CY, INK, 2.5))
    o.append(ic_check(28, y + 22))
    o.append(P(52, y + 26, "Hvert ledd så bare ordren fra leddet foran, og svarte på den med forsinkelse.", 15, 306, 21, cls="c09-k"))
    y += 90
    o.append(R(16, y, 358, 44, OR, INK, 2))
    o.append(T(52, y + 27, "Fabrikken laget for lite.", 15, "c09-m"))
    y += 66
    o.append(A(16, y + 10, "DERFOR VAR DET FEIL", 30))
    o.append(P(16, y + 40, "Kundene bestilte 8 hver uke fra Uke 5 og endret seg aldri mer. Det var ordrene som svingte: 1,8× hos Detaljist og 7,6× hos Fabrikk.", 15, 356, 21))
    o.append(P(16, y + 134, "Du så bare ordrene fra Ida: 11, 10 og 8 i Uke 9 til 11. Kundens tall så du aldri.", 15, 356, 21))
    o.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
    o.append(A(198, 808, "NESTE SPØRSMÅL", 50, CY, "middle", ANG))
    return "".join(o)


def shared_screen(d, W, H):
    o = [R(0, 0, W, H, CY)]
    # Venstre: tittel vinklet, ingress
    o.append(G(A(0, 0, "KUNDEN BESTILTE 8.", 50) + A(0, 54, "FABRIKKEN BESTILTE 31.", 50), 18, 140, rot=ANG))
    o.append(T(18, 228, "Ingress, Sara, Grossist", 14, "c09-k"))
    o.append(P(18, 250, "«" + SARA_TEXT + "»", 15, 390, 21, cls="c09-m"))
    o.append(T(18, H - 16, "Spill 17. Demodata.", 13))
    # Midten: de fire kurvene
    o.append(orders_chart(d, 478, 18, 616, H - 58, CY, 14, 1.0))
    # Høyre: kostnad og spørsmål til gruppa
    x = 1118
    o.append(T(x, 40, "Kjeden totalt", 15, "c09-k"))
    o.append(A(x, 98, f"{kr(F['chain_total_cost'])} KR", 52))
    yy = 130
    for r in ROLES:
        o.append(T(x, yy, r, 15, "c09-m"))
        o.append(T(W - 20, yy, kr(F["total_cost_per_role"][r]), 15, "c09-k c09-tn", anchor="end"))
        o.append(L(x, yy + 7, W - 20, yy + 7, INK, 1))
        yy += 27
    o.append(legend_row(d, x, yy + 16, 14, 130))
    return "".join(o)


def page_07():
    d = Doc("debrief", "07-debrief", 2100, 1200, "Gruppedebrief som artikkel",
            "Fem telefonruter og en delt skjerm: Forklaringen skrives først og blir ingress, avsløringen er en stille, blank side med 4 til 8, "
            "så kommer fire overlappende kurver, ditt øyeblikk i Uke 11 og quiz med feil svar forklart.", OR)
    d.add(A(39, 72, "SPILLET DITT BLIR EN ARTIKKEL", 54))
    frames = [
        (OR, debrief_1(d), "1. Forklaringen", "Du skriver før du vet. Sara tror kundene ville ha mer. Teksten blir ingressen, og neste side er låst."),
        (PAPER, debrief_2(d), "2. Den stille siden", "Første side uten blekk i hele spillet. 4 til 8 i liten skrift. Ingen trenger å si noe."),
        (CY, debrief_3(d), "3. Oppslaget", "Fire overlappende kurver i full bredde. 1,8× blir 7,6×, og kundens 8 ligger langs bunnen."),
        (CY, debrief_4(d), "4. Ditt øyeblikk", "Uke 11: hva du så, hva du bestilte, hva det kostet senere, og hva de andre så samtidig."),
        (OR, debrief_5(d), "5. Quiz", "Feil svar forklares med dine egne tall. Svaret ditt blir stående, uten poeng og uten skyld."),
    ]
    s = .68
    for i, (g, inner, h, note) in enumerate(frames):
        x = 39 + i * 285
        d.add(phone(d, x, 92, inner, s, g))
        d.add(A(x, 700, h.upper(), 28))
        d.add(P(x, 726, note, 15, 262, 20))
    # Margspalten: ordene man nå forstår
    x = 1480
    d.add(A(x, 132, "ORDENE DU NÅ", 62))
    d.add(A(x, 212, "FORSTÅR", 62))
    entries = [
        ("PÅ VEI", "Kasser du har bestilt, men ikke fått ennå. I Uke 11 hadde du 16. De lå ikke i lageret, og derfor var de lette å regne bort."),
        ("RESTORDRE", "Det du skylder leddet foran. 1,00 kr per kasse per uke, dobbelt så dyrt som lager. Din høyeste var 40, i Uke 22."),
        ("FORSINKELSE", "2 uker for ordre og 2 uker for frakt. Ordren du la i Uke 11, kunne tidligst komme i Uke 15."),
        ("BEER GAME", "Øvelsen dere nettopp spilte, heter Beer Game. Kassene var øl. Nå kan vi si det."),
    ]
    y = 278
    for term, de in entries:
        d.add(A(x, y, term, 36))
        d.add(L(x, y + 8, 2061, y + 8, INK, 2))
        d.add(P(x, y + 36, de, 20, 570, 27))
        y += 36 + plines(de, 20, 570) * 27 + 40
    # Delt skjerm
    W, H = 1400, 362
    c = d.clip_rect(0, 0, W, H, 6)
    d.add(G(R(-7, -7, W + 14, H + 14, INK, r=10) + f'<g clip-path="url(#{c})">{shared_screen(d, W, H)}</g>', 39, 818))
    d.add(A(1480, 866, "DELT SKJERM", 36))
    d.add(L(1480, 874, 2061, 874, INK, 2))
    d.add(P(1480, 902, "Gruppa ser oppslaget samtidig, på en skjerm i Labtimen eller hver på sin. Sara leser ingressen sin høyt ved siden av kurvene.", 20, 570, 27))
    d.add(R(1480, 1020, 581, 112, INK))
    d.add(ki_tag(1496, 1054, INK, CY, 16))
    d.add(T(1536, 1054, "KI-generert, kan ta feil", 20, "c09-k", CY))
    d.add(P(1496, 1086, "Står på all KI-tekst. Tallene kommer fra loggen over beslutninger, ikke fra KI-en.", 17, 548, 22, fill=CY))
    d.save()


def reg_phone(d):
    o = [R(0, 0, 390, 844, OR)]
    o.append(A(16, 50, "BLEKK", 34))
    o.append(T(374, 46, "Invitasjon", 14, "c09-m", anchor="end"))
    o.append(G(A(0, 0, "DU ER", 92) + A(0, 90, "INVITERT", 92, CY, stroke=INK, sw=5), 20, 166, rot=ANG))
    o.append(P(16, 300, "Bård har invitert deg til class-of-1994, IBE160. Invitasjonen gjelder i 14 dager.", 15, 356, 21))
    y = 366
    for lab, val, cur in [("Navn", "Sara Nilsen", False), ("E-post", "sara.nilsen@student.no", False), ("Velg passord", "", True)]:
        o.append(T(16, y, lab, 14, "c09-k"))
        o.append(R(16, y + 8, 358, 50, PAPER, INK, 2.5))
        if val:
            o.append(T(30, y + 40, val, 17, "c09-m"))
        if cur:
            o.append(R(30, y + 20, 2, 26, INK))
        y += 80
    o.append(P(16, y + 6, "Du får ett Sete i et Klassespill sammen med tre andre. Spillet starter ti. 24. nov. Rollen din får du da.", 14, 356, 20))
    o.append(T(16, y + 76, "Har du konto?", 14, "c09-m"))
    o.append(T(112, y + 76, "Logg inn", 14, "c09-k c09-u"))
    o.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
    o.append(A(198, 808, "REGISTRER DEG", 54, CY, "middle", ANG))
    return "".join(o)


def home_phone(d):
    o = [R(0, 0, 390, 844, CY)]
    o.append(A(16, 50, "SPILL 17", 34))
    o.append(T(374, 30, "Grossist, Sara", 14, "c09-k", anchor="end"))
    o.append(T(374, 49, "Demodata", 13, anchor="end"))
    o.append(G(A(0, 0, "SPILLET VENTER", 46) + A(0, 96, "PÅ DEG", 84, OR, stroke=INK, sw=5), 22, 156, rot=ANG))
    # De seks stegene, som innholdsfortegnelse
    y = 290
    steps = [("Klassespill", "pågår, Uke 11", "run"), ("Debrief", "låst", "lock"), ("Quiz", "låst", "lock"),
             ("Replay", "låst", "lock"), ("Individuell test", "låst", "lock"), ("Rapport", "låst", "lock")]
    for i, (n, st, kind) in enumerate(steps):
        yy = y + i * 25
        o.append(ic_run(16, yy - 5) if kind == "run" else ic_lock(16, yy - 2, INK, .9))
        o.append(T(38, yy, n, 15, "c09-k" if kind == "run" else "c09-m"))
        o.append(T(374, yy, st, 14, "c09-k" if kind == "run" else "c09-b", anchor="end"))
        o.append(L(16, yy + 8, 374, yy + 8, INK, 1))
    y = 454
    o.append(T(16, y, "De andre setene", 14, "c09-x"))
    seats = [("done", "Ida", "Detaljist, har bestilt"), ("done", "Mikkel", "Distributør, har bestilt"), ("wait", "Jonas", "Fabrikk, venter 3 min")]
    for i, (st, nm, sub) in enumerate(seats):
        yy = y + 22 + i * 21
        o.append(ic_check(17, yy - 4) if st == "done" else ic_wait(18, yy - 4, INK, .8))
        o.append(T(36, yy, nm, 14, "c09-k"))
        o.append(T(92, yy, sub, 14, "c09-m"))
    y = 552
    o.append(L(16, y - 12, 374, y - 12, INK, 2))
    o.append(T(16, y + 8, "Neste frist", 14, "c09-x"))
    o.append(A(16, y + 50, "TI. 8. DES", 36))
    o.append(T(16, y + 72, "Spillfrist", 14, "c09-m"))
    o.append(T(196, y + 8, "Labtimer, Datalab A2", 14, "c09-x"))
    for i, t in enumerate(["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]):
        o.append(T(196, y + 30 + i * 20, t, 14, "c09-m c09-tn"))
    o.append(poly([(0, 778), (390, 702), (390, 844), (0, 844)], INK))
    o.append(A(198, 808, "SPILL UKE 11", 60, OR, "middle", ANG))
    return "".join(o)


def page_04():
    d = Doc("hjem", "04-student-hjem", 1000, 900, "Sara på mobil",
            "To telefoner. Venstre: registrering fra Invitasjon. Høyre: hjem under spill, cyan fordi Sara står i restordre, med spillet som venter, "
            "de andre setene, de seks stegene, neste frist og Labtimer.", OR)
    d.add(phone(d, 56, 28, reg_phone(d), 1.0, OR))
    d.add(phone(d, 554, 28, home_phone(d), 1.0, CY))
    d.add(A(486, 460, "FØRSTE MØTE", 26, INK, "middle", -90))
    d.add(A(528, 460, "HJEM UNDER SPILL", 26, INK, "middle", -90))
    d.save()
