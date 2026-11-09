"""01 landing og 09 kontaktark."""
from c06_ink import *  # noqa: F403
from c06_laerer import cover, GAMES


def landing():
    p = Page("01-landing.svg", "land", 1440, 1200, "Uke for uke: landingsside for faglærere",
             "Et album-omslag som viser mekanismen: en Uke er tre ruter, og studenten skriver ett tall i sin egen boble. Under: alle spill på én skjerm, og en stripe om fravær og KI-spiller.")
    # omslag: mettet gul med stort raster
    p.add(f'<rect x="0" y="0" width="1440" height="800" fill="{YEL}"/>')
    p.add(f'<rect x="800" y="0" width="640" height="800" fill="{dots("dM")}" opacity=".55"/>')
    p.add(iline(0, 800, 1440, 800, 4))
    # nav
    p.add(T(56, 62, "Uke for uke", 26, "d"))
    p.add(button(1016, 30, 116, 44, "Logg inn", "sec", 19))
    p.add(button(1146, 26, 246, 52, "Be om lærertilgang", "prim", 16))
    # tittel
    p.add(T(52, 240, "En uke.", 112, "d"))
    p.add(T(52, 352, "Ett tall.", 112, "d"))
    p.add(T(56, 416, "En hel klasse spiller forsyningskjeden.", 34, "hb"))
    txt = ("Fire Roller, én ordre per Uke, på studentenes egen mobil. Du får hele øvelsen, fra Invitasjon til PDF-rapport, "
           "for klasser på rundt 250 studenter.")
    p.add(Pg(56, 462, txt, 610, 26, lh=1.24))
    p.add(button(56, 572, 330, 72, "Be om lærertilgang", "prim", 22))
    p.add(button(404, 572, 170, 72, "Logg inn", "sec", 24))
    p.add(T(56, 678, "Ingen åpen registrering: du får tilgang, og studentene kommer inn med Invitasjon.", 20))
    # figurene langs kjeden
    gy = 790
    xs = [96, 226, 346, 486]
    for x, r in zip(xs, ROLES):
        p.add(fig(x, gy, r, .78 if r != "Distributør" else .55, "rolig"))
    p.add(iline(30, gy + 1, 560, gy + 1, 3))
    # mekanismen: stripen, stor
    st = state(11, "")
    sx, sy, w = 850, 124, 530
    s = w / 374
    # liten demodata-merkelapp
    p.add(g(f"translate({sx} {sy}) scale({s:.3f})",
            rute1(0, 0, 374, 132, st, tilt=(0, 0, 0, 4)),
            rute2(0, 140, 374, 150, st, tilt=(4, 0, 0, -4)),
            rute3(0, 298, 374, 156, st, tilt=(-4, 0, 0, 0))))
    p.add(plain(sx, sy - 40, 340, 34, WHITE, 2))
    p.add(T(sx + 10, sy - 16, "Slik ser en Uke ut for én student.", 20, "hb"))
    p.add(plain(sx + w - 106, sy - 40, 106, 34, WHITE, 2))
    p.add(T(sx + w - 53, sy - 16, "Demodata", 19, "hb", INK, "middle"))
    # neste seksjon: veggen + stripen
    y0 = 816
    p.add(T(56, y0 + 42, "Alle spillene på én skjerm", 38, "d"))
    p.add(Pg(56, y0 + 76, "Du holder 60 grupper på sporet uten å være dommer. Hver forside sier hvem spillet venter på, og hvor lenge.", 760, 23, lh=1.2))
    # et utsnitt av veggen
    wx, wy = 56, y0 + 120
    cols, rows = 7, 2
    cw, ch = 110, 108
    order = [1, 9, 16, 19, 27, 29, 43, 10, 20, 2, 3, 4, 5, 6]
    for i, idx in enumerate(order[:14]):
        r, c = divmod(i, cols)
        p.add(cover(wx + c * cw, wy + r * ch, cw - 6, ch - 6, GAMES[idx]))
    p.add(T(56, wy + 2 * ch + 20, "Utsnitt med 14 av 60. Demodata.", 17, "h", SOFT))
    # stripe om fravær
    bx, by, bw = 860, y0 + 16, 524
    p.add(T(bx, by + 22, "Ett fravær stopper ikke gruppa", 23, "d"))
    pw = (bw - 12) / 3
    py = by + 38
    ph = 208
    p.add(ibox(bx, py, pw, ph, YEL, None, 3))
    p.add(fig(bx + 60, py + ph - 8, "Fabrikk", .95, "rolig"))
    p.add(ic_hour(bx + 136, py + 112, 1.7))
    p.add(plain(bx + 8, py + 8, pw - 16, 50, WHITE, 2))
    p.add(T(bx + 16, py + 29, "Jonas er borte.", 18, "hb"))
    p.add(T(bx + 16, py + 49, "De andre venter.", 17))
    x2 = bx + pw + 6
    p.add(ibox(x2, py, pw, ph, WHITE, "dc", 3, mis=(0, 0)))
    p.add(fig(x2 + 60, py + ph - 8, "Fabrikk", .95, ki=True))
    p.add(plain(x2 + 8, py + 8, pw - 16, 50, WHITE, 2))
    p.add(T(x2 + 16, py + 29, "KI-spiller fyller", 18, "hb"))
    p.add(T(x2 + 16, py + 49, "setet, merket.", 17))
    x3 = x2 + pw + 6
    p.add(ibox(x3, py, pw, ph, WHITE, None, 3, mis=(0, 0)))
    p.add(fig(x3 + 60, py + ph - 8, "Fabrikk", .95, "glad"))
    p.add(plain(x3 + 8, py + 8, pw - 16, 50, WHITE, 2))
    p.add(T(x3 + 16, py + 29, "Jonas tar", 18, "hb"))
    p.add(T(x3 + 16, py + 49, "tilbake setet.", 17))
    # fakta
    fy = py + ph + 30
    facts = ["Ingen spill blir stående uferdig.", "Studentlisten lastes opp fra Canvas-eksport.", "Spilles på mobil, på norsk."]
    for i, t in enumerate(facts):
        p.add(ic_check(bx + 8, fy + i * 30 - 6, .95) + T(bx + 24, fy + i * 30, t, 22))
    p.save()


# ---- 09 kontaktark --------------------------------------------------------------------------------
def line(x, y, w, sw=2):
    return iline(x, y, x + w, y, sw, j=.5)


def thumb_phone(x, y, *kids, h=186, w=98):
    return g(f"translate({x} {y})", rr(0, 0, w, h, 11, WHITE, INK, 3), *kids)


def thumb_wide(x, y, w, h, *kids):
    return g(f"translate({x} {y})", rr(0, 0, w, h, 3, WHITE, INK, 3),
             f'<rect x="0" y="0" width="{w}" height="14" fill="{YEL}" stroke="{INK}" stroke-width="2"/>', *kids)


def bars(x, y, w, h, vals, fill=CYA):
    vmax = max(vals) or 1
    cw = w / len(vals)
    return "".join(f'<rect x="{x+i*cw:.1f}" y="{y+h-v/vmax*h:.1f}" width="{cw-1.5:.1f}" height="{v/vmax*h:.1f}" fill="{fill}" stroke="{INK}" stroke-width="1"/>' for i, v in enumerate(vals))


def tile(x, y, w, h, thumb, title, one, flat=PAPER, tx=None, ty=None, tw_=None):
    o = [ibox(x, y, w, h, flat, None, 2.6, mis=(0, 0)), thumb]
    tx = tx if tx is not None else x + 10
    ty = ty if ty is not None else y + 22
    o.append(Pg(tx, ty, title, tw_ or w - 20, 19, "hb", lh=1.1))
    n = nl(title, tw_ or w - 20, 19, "hb")
    o.append(Pg(tx, ty + n * 21 + 2, one, tw_ or w - 20, 16.5, lh=1.16))
    return "".join(o)


def mini_strip(x, y, w=78, h=20):
    return (f'<rect x="{x}" y="{y}" width="{w/3:.1f}" height="{h}" fill="{CYA}" stroke="{INK}" stroke-width="1.4"/>'
            f'<rect x="{x+w/3:.1f}" y="{y}" width="{w/3:.1f}" height="{h}" fill="{dots("dm")}" stroke="{INK}" stroke-width="1.4"/>'
            f'<rect x="{x+2*w/3:.1f}" y="{y}" width="{w/3:.1f}" height="{h}" fill="{YEL}" stroke="{INK}" stroke-width="1.4"/>')


def alle_sider():
    p = Page("09-alle-sider.svg", "alle", 2000, 1400, "Alle andre sider, i albumets språk",
             "Kontaktark gruppert per rolle: Student, Faglærer og Admin, med tittel og én linje per side.")
    p.add(T(40, 54, "Resten av boka", 38, "d"))
    p.add(T(450, 52, "Alle andre sider, på lavere detaljnivå. Demodata.", 23))
    # STUDENT 5x2
    SX, SY = 40, 110
    tw0, th0 = 268, 306
    p.add(ibox(SX - 8, SY - 40, 5 * (tw0 + 6) + 10, 34, CYA, None, 2.6))
    p.add(T(SX + 4, SY - 15, "Student", 22, "d"))
    st = state(11)
    def ph(col, row, *kids):
        return thumb_phone(SX + col * (tw0 + 6) + 16, SY + row * (th0 + 6) + 110, *kids)
    S = [
        ("Invitasjon og registrering", "Lenken fra Bård, navn og passord.",
         fig(49, 100, "Grossist", .6) + rr(10, 112, 78, 16, 2, WHITE) + rr(10, 134, 78, 16, 2, WHITE) + rr(10, 158, 78, 18, 2, MAG)),
        ("Logg inn", "E-post og passord, så rett til albumet ditt.",
         T(49, 44, "UKE FOR UKE", 9, "d", INK, "middle") + rr(10, 70, 78, 18, 2, WHITE) + rr(10, 96, 78, 18, 2, WHITE) + rr(10, 124, 78, 24, 2, MAG)),
        ("Regler før første ordre", "De fire figurene forklarer kjeden i én stripe.",
         mini_strip(10, 26) + "".join(fig(20 + i * 20, 96, r, .24, mis=False) for i, r in enumerate(ROLES)) + line(10, 112, 78) + line(10, 124, 66) + line(10, 136, 72) + rr(10, 152, 78, 22, 2, YEL)),
        ("Startoppgave", "Øv på én tom boble før spillet teller.",
         bubble(14, 60, 70, 46, (10, 118), "b", YEL, 2.2) + T(49, 92, "?", 26, "d", INK, "middle") + rr(10, 136, 78, 30, 2, WHITE)),
        ("Replay", "Du spiller igjen, tre KI-spillere i de andre setene.",
         mini_strip(10, 26) + "".join(ki_tag(32 + i * 0, 64 + i * 26, .78) for i in range(3)) + bubble(14, 138, 70, 34, (10, 170), "l", WHITE, 2)),
        ("Replay-gjennomgang", "To album side om side: første og andre gang.",
         mini_strip(10, 24) + mini_strip(10, 48) + bars(10, 80, 36, 80, [2, 3, 5, 8, 7, 4]) + bars(52, 80, 36, 80, [2, 2, 3, 3, 2, 3], MAG)),
        ("Individuell test", "Flervalg, tegne- og tabelloppgave, langsvar. Lukk og kom tilbake.",
         circ(16, 34, 5) + line(26, 34, 58) + circ(16, 52, 5, YEL) + line(26, 52, 50) + path("M10 118L30 88L46 112L66 78L88 96", stroke=MAG, sw=2.6) + rr(10, 128, 78, 44, 2, WHITE) + line(16, 142, 60, 1.4) + line(16, 156, 50, 1.4)),
        ("KI-vurdering", "Teller ikke og er aldri en karakter. Det står øverst.",
         ki_tag(30, 44, .9) + line(10, 66, 78) + line(10, 80, 70) + line(10, 94, 74) + rr(10, 112, 78, 34, 2, YEL) + T(49, 134, "Teller ikke", 11.5, "hb", INK, "middle")),
        ("Studentrapport (PDF)", "Hele reisen din som ett hefte å laste ned.",
         ic_page(49, 70, 3, f=WHITE) + mini_strip(10, 124) + rr(10, 152, 78, 22, 2, MAG)),
        ("Alle spill side om side", "Etter Debrief: hele klassens kurver, uten rangering.",
         "".join(bars(10 + c * 28, 30 + r * 46, 24, 38, [1, 2, 4, 6 + c, 5, 3 + r], [CYA, MAG, YEL][c]) for c in range(3) for r in range(3))),
    ]
    for i, (ttl, one, th) in enumerate(S):
        r, c = divmod(i, 5)
        x = SX + c * (tw0 + 6)
        y = SY + r * (th0 + 6)
        tp = thumb_phone(x + 85, y + 110, th, h=186, w=98)
        p.add(tile(x, y, tw0, th0, tp, ttl, one, tw_=tw0 - 20))
    # ADMIN til høyre
    AX = SX + 5 * (tw0 + 6) + 20
    aw = 2000 - AX - 40
    p.add(ibox(AX - 4, SY - 40, aw + 6, 34, MAG, None, 2.6))
    p.add(T(AX + 8, SY - 15, "Admin", 22, "d", WHITE))
    ah = 200
    A = [
        ("Admin-område", "Status, revisjonslogg og Klasser på tvers.",
         "".join(rr(14 + i * 62, 26, 54, 34, 2, [YEL, CYA, WHITE][i]) for i in range(3)) + line(14, 76, 170) + line(14, 92, 150) + line(14, 108, 170)),
        ("Brukere og roller", "Faglærer, Studentassistent, Student, Admin.",
         "".join(fig(24 + i * 44, 94, r, .36, mis=False) for i, r in enumerate(ROLES)) + line(14, 110, 170) + line(14, 124, 170)),
        ("KI-kostnad", "Forbruk per Klasseøkt og tak på KI-spillere.",
         bars(14, 28, 172, 96, [3, 4, 6, 5, 8, 12, 9, 6, 4, 3], MAG)),
    ]
    for i, (ttl, one, th) in enumerate(A):
        y = SY + i * (ah + 9)
        tp = thumb_wide(AX + aw - 212, y + 26, 200, 148, th)
        p.add(tile(AX, y, aw, ah, tp, ttl, one, tw_=aw - 240))
    # FAGLÆRER 4x2
    FY = SY + 2 * (th0 + 6) + 54
    fw = (2000 - 80 - 3 * 8) / 4
    fh = (1400 - FY - 28 - 8) / 2
    p.add(ibox(SX - 8, FY - 40, 2000 - 64, 34, YEL, None, 2.6))
    p.add(T(SX + 4, FY - 15, "Faglærer", 22, "d"))
    tt = 204
    tth = fh - 28
    F = [
        ("Lærerhjem med klasser", "Klassene dine, og hva som trenger deg i dag.",
         "".join(rr(12 + (i % 2) * 94, 24 + (i // 2) * 44, 86, 36, 2, [CYA, WHITE, YEL, WHITE][i]) for i in range(4))),
        ("Klasserapport", "Hele Klassen som PDF, ingen rangering av studenter.",
         ic_page(36, 56, 2.6) + bars(70, 28, 120, 66, [8, 7, 6, 5, 4, 2]) + line(12, 104, 178)),
        ("Spillinnsikt (uke for uke)", "Blar i ett spill: alle fire striper, KI-uker merket.",
         "".join(mini_strip(12, 24 + i * 24, 150, 20) for i in range(4)) + ki_tag(186, 66, .7)),
        ("Studentside", "Én student: album, frister, status per kapittel.",
         fig(36, 110, "Grossist", .78) + mini_strip(70, 28, 124, 20) + line(70, 62, 120) + line(70, 78, 100) + line(70, 94, 120)),
        ("Spill alle side om side for plenum", "Stor skjerm, 60 kurver, ingen navn.",
         "".join(bars(12 + c * 31, 24 + r * 28, 27, 24, [1, 2, 4 + c, 5, 3 + r % 2], [CYA, MAG, YEL][(c + r) % 3]) for c in range(6) for r in range(3))),
        ("Tverrklasse-statistikk", "Klasse mot Klasse over år, med samme mål.",
         path("M14 100L60 80L104 88L148 54L190 44", stroke=INK, sw=3) + path("M14 112L60 106L104 92L148 90L190 72", stroke=MAG, sw=3) + line(14, 118, 176, 1.6)),
        ("Meldinger", "Skriv til ett spill, alle som venter, eller Klassen.",
         ic_mail(36, 44, 2.1) + line(70, 34, 120) + line(70, 50, 100) + ic_mail(36, 90, 2.1, f=YEL) + line(70, 80, 120) + line(70, 96, 80)),
        ("Lærers testspill", "Spill selv mot KI og se hva innstillingene gjør.",
         fig(34, 112, "Kunde", .72) + "".join(ki_tag(88 + i * 36, 62, .7) for i in range(3)) + bubble(66, 76, 124, 34, (56, 92), "l", YEL, 2)),
    ]
    for i, (ttl, one, th) in enumerate(F):
        r, c = divmod(i, 4)
        x = SX + c * (fw + 8)
        y = FY + r * (fh + 8)
        k = 1.56
        tp = g(f"translate({x + (fw - tt * k) / 2:.1f} {y + 66:.1f}) scale({k})", thumb_wide(0, 0, tt, 130, th))
        p.add(tile(x, y, fw, fh, tp, ttl, one, tw_=fw - 20))
    p.save()
