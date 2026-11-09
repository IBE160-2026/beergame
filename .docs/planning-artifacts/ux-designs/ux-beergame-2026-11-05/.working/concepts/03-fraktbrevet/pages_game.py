"""05 spill, 06 spilldynamikk, 07 debrief."""
from c03lib import *  # noqa: F403


def note(pg, x, y, w, head, body, fill=REC, rot=0):
    """Kvitteringslapp med blyantoverskrift og skrivemaskintekst."""
    lines = wrap(body, w - 24, 15, "nar")
    h = 44 + len(lines) * 20
    g = pg.paper(x, y, w, h, fill)
    g += T(x + 12, y + 27, head, 25, "pen", INK)
    for i, ln in enumerate(lines):
        g += T(x + 12, y + 50 + i * 20, ln, 15, "nar", INK)
    return f'<g transform="rotate({rot} {x + w / 2} {y + h / 2})">{g}</g>', h


def form_with_bunke(pg, week=11, typed=None, stamped=False, ghost=None, seats=SEATS_W11, **kw):
    s = snor(pg, 12, 12, 366, seats, 70)
    f = ordreseddel(pg, week, typed, stamped, ghost, **kw)
    return s, f


# ---------- 05 ----------
def screen_w11(pg):
    s, f = form_with_bunke(pg, 11, "24", False, ghost=24)
    b, ly = bunke(8, 696, 374, 11)
    return s + b + f + demo(14, ly + 22)


def laptop_screen(pg, x, y, w, h):
    """Samme skjema, tastaturet skriver. Bunken til venstre, snora over, fraktbrev til hoeyre."""
    out = [R(x, y, w, h, DESK)]
    d = WEEKS[10]["seats"]["Grossist"]
    # snor
    out.append(snor(pg, x + 250, y + 16, w - 300, SEATS_W11, 70))
    # bunke: stor side med faner som liste
    bx, by = x + 22, y + 104
    out.append(T(bx, by - 8, "BUNKEN", 13, "lab", PALE, ls=.5))
    orders = [v["seats"]["Grossist"]["ordre"] for v in WEEKS]
    out.append(pg.paper(bx, by, 190, 392, PINK))
    out.append(T(bx + 10, by + 22, "UKE", 13, "lab", PLUM) + T(bx + 180, by + 22, "ORDRE", 13, "lab", PLUM, "end"))
    for i in range(10):
        ry = by + 30 + i * 33
        out.append(L(bx, ry, bx + 190, ry, PLUM, .6))
        out.append(T(bx + 10, ry + 23, str(i + 1), 15, "lab", PLUM))
        out.append(T(bx + 180, ry + 25, str(orders[i]), 21, "typb", CARBON, "end"))
        if i < 4:
            out.append(T(bx + 40, ry + 22, "Veiledet", 13, "nar", PLUM))
    # papirkanter under
    for i in range(10):
        out.append(R(bx + 2 + (i * 13 % 5), by + 394 + i * 2.2, 186 - (i * 7 % 5), 1.6, PINK if i % 2 == 0 else PINK_L))
    out.append(T(bx + 2, by + 438, "Bla i bunken", 14, "labb", PALE) + icon_chev(bx + 82, by + 433, PALE))
    # skjema
    fx, fy, fw = x + 232, y + 104, 500
    out.append(pg.paper(fx, fy, fw, h - 104 - 18, CAN))
    out.append(perf_h(fx + 6, fy + 8, fw - 12, DESK, 2.2))
    out.append(icon_role("Grossist", fx + 12, fy + 18, 30))
    out.append(T(fx + 50, fy + 34, "ORDRESEDDEL", 19, "disp") + T(fx + 50, fy + 52, "Spill 17 · Grossist · Sara", 15, "lab"))
    out.append(R(fx + fw - 108, fy + 16, 96, 42, "none", INK, 1.4) + T(fx + fw - 102, fy + 31, "UKE", 13, "lab") + T(fx + fw - 18, fy + 51, "11", 32, "typb", INK, "end"))
    gx, gy = fx + 12, fy + 68
    c = (fw - 24) / 3
    rows = [("Lager", str(d["lager"])), ("Restordre", str(d["restordre"])), ("Ordre inn", str(d["innkommende_ordre"])),
            ("Levering", str(d["levering"])), ("Sendt", str(d["sendt"])), ("Totalkostnad", num(d["kost_sum"]) + " kr")]
    for i, (lb, v) in enumerate(rows):
        cx, cy = gx + (i % 3) * c, gy + (i // 3) * 84
        col = RED if lb == "Restordre" else INK
        out.append(field(cx, cy, c, 84, lb, v, INK, col, 24 if lb == "Totalkostnad" else 38))
        if lb == "Restordre":
            out.append(tally(cx + 62, cy + 42, 13, RED, 22, wrap_at=3))
    oy = gy + 178
    out.append(R(gx, oy, fw - 24, 134, CAN_L, INK, 2.2))
    out.append(T(gx + 10, oy + 20, "ORDRE", 15, "labb", INK, ls=.6) + T(gx + fw - 34, oy + 20, "kasser, ett heltall", 13, "nar", INK, "end"))
    out.append(T(gx + 14, oy + 112, "24", 84, "typb") + R(gx + 120, oy + 48, 3, 68, INK))
    out.append(stamp_button(gx, oy + 144, fw - 24, 92, "STEMPLE BESTILT", "Trykk Enter. Ordren kan ikke endres etterpå.", True, 22, subsize=15))
    # fraktbrev
    sx = fx + fw + 16
    sw = x + w - sx - 18
    out.append(R(sx, fy + 16, sw, 42, BLUE, NAVY, .8) + T(sx + 7, fy + 31, "PÅ VEI", 13, "lab", NAVY) + T(sx + 7, fy + 50, "kasser", 13, "nar", NAVY) + T(sx + sw - 8, fy + 50, str(d["paa_vei_foer_ordre"]), 26, "typb", NAVY, "end"))
    col, _ = slip_col(pg, sx, fy + 58, sw, slips_for(11), 11.0, ghost=24, avail=h - 104 - 18 - 58 - 8)
    out.append(col + icon_clip(sx + sw / 2 - 22, fy - 2, 44))
    return "".join(out)


def spill():
    pg = Page("spill", "05-spill.svg", 1600, 1000, "Fraktbrev: spillskjermen, Uke 11",
              "Saras ordreseddel på telefon og laptop med 24 skrevet i det eneste tomme feltet, fraktbrev klipset på siden og bunken under.")
    pg.add(phone(pg, 56, 70, screen_w11(pg)))
    lx, ly, lw, lh = 500, 60, 1050, 640
    pg.add(R(lx - 12, ly - 12, lw + 24, lh + 24, "#0B0A0D", "#55525E", 2, 14, f'filter="url(#{pg.sh})"'))
    i = pg.clip(lx, ly, lw, lh, 2)
    pg.add(f'<g clip-path="url(#{i})">{laptop_screen(pg, lx, ly, lw, lh)}</g>')
    pg.add(P(f"M{lx - 40} {ly + lh + 12}h{lw + 80}l-24 20H{lx - 16}z", "#3B3944", None))
    pg.add(demo(lx + lw - 2, ly + lh + 56, PALE, "end"))
    a, _ = note(pg, 500, 770, 330, "ett tomt felt", "Lager, restordre, ordre inn og levering er ferdig skrevet. Blikket går rett til ORDRE.", rot=-.5)
    b, _ = note(pg, 850, 770, 330, "høyden er kassene", "Hvert fraktbrev er så høyt som kassene det frakter. Du ser 24 ved siden av 16 før du stempler.", BLUE_L, rot=.4)
    c, _ = note(pg, 1200, 770, 340, "bunken er klokka", "En kant per uke. Den vokser, og ingen ende synes. Aldri «av 36».", PINK_L, rot=-.3)
    pg.add(a, b, c)
    pg.save()


# ---------- 06 ----------
BY = 696
SEATS_OPEN = [("Detaljist", "Ida", "venter", "nå"), ("Grossist", "Sara", "deg", ""),
              ("Distributør", "Mikkel", "venter", "nå"), ("Fabrikk", "Jonas", "venter", "nå")]


def ring(cx, cy, rx=30, ry=21, color=INK):
    return P(f"M{cx - rx} {cy}C{cx - rx} {cy - ry * 1.3} {cx + rx} {cy - ry * 1.3} {cx + rx} {cy}C{cx + rx} {cy + ry * 1.2} {cx - rx - 4} {cy + ry * 1.2} {cx - rx + 2} {cy - 5}", "none", color, 1.8)


def fA(pg):
    s, f = form_with_bunke(pg, 11, None, seats=SEATS_OPEN)
    b, ly = bunke(8, BY, 374, 11)
    # det som kom inn: arket fra Rollen under og fraktbrevet som ble framme
    y2 = 154 + 78
    over = ring(38, y2 + 54) + ring(162, y2 + 54)
    over += G(R(0, 0, 70, 50, CAN, INK, .8) + T(6, 19, "fra", 13, "lab") + T(6, 38, "Detaljist", 14, "labb"), 68, y2 + 24, rot=-5)
    over += G(R(0, 0, 70, 50, BLUE, NAVY, .8) + T(6, 19, "4 kasser", 13, "labb", NAVY) + T(6, 38, "framme", 14, "lab", NAVY), 192, y2 + 22, rot=5)
    return s + b + f + over + demo(14, ly + 22)


def fB(pg):
    s, f = form_with_bunke(pg, 11, "24", False, ghost=24)
    b, ly = bunke(8, BY, 374, 11)
    return s + b + f + demo(14, ly + 22)


def fC(pg):
    seats = [("Detaljist", "Ida", "bestilt", ""), ("Grossist", "Sara", "deg-bestilt", ""),
             ("Distributør", "Mikkel", "bestilt", ""), ("Fabrikk", "Jonas", "venter", "3 min")]

    def body(fx, oy, w):
        o = R(fx, oy, w, 100, PINK_L, PLUM, 2.2)
        o += T(fx + 9, oy + 19, "ORDRE", 15, "labb", PLUM, ls=.6)
        o += T(fx + 12, oy + 84, "24", 66, "typb", CARBON)
        o += stamp(pg, fx + w - 82, oy + 60, "BESTILT", 21, -8)
        o += icon_lock(fx + w - 24, oy + 6, PLUM, 16)
        y = oy + 138
        o += T(fx, y, "Venter på Jonas", 25, "disp", PLUM)
        o += icon_clock(fx + 10, y + 24, 8, PLUM) + T(fx + 24, y + 30, "3 min. Fabrikk har ikke stemplet.", 15, "lab", PLUM)
        return o
    s = snor(pg, 12, 12, 366, seats, 70)
    f = ordreseddel(pg, 11, "24", True, paper=PINK, extra_solid=24, pv=40, body=body)
    b, ly = bunke(8, BY, 374, 11)
    # originalen: hviler lesbart nederst, flyr ut oppstroems og kommer tilbake i loekka
    orig = (R(0, 0, 150, 92, CAN, INK, .8) + perf_h(5, 5, 142, PINK, 1.8, 8) + T(8, 27, "ORIGINAL", 13, "labb") + T(8, 76, "24", 44, "typb")
            + stamp(pg, 100, 56, "BESTILT", 10, -7, VIO, False, False))
    orig_g = f'<g transform="translate(24 590) rotate(-6)">{orig}</g>'
    orig_anim = f'<g>{orig_g}<animateTransform attributeName="transform" type="translate" values="0 0;0 0;120 -720;120 -720;0 0" keyTimes="0;.72;.86;.98;1" dur="8s" repeatCount="indefinite"/></g>'
    return s + b + f + orig_anim + T(182, 672, "oppstrøms", 24, "pen", PLUM) + P("M200 650C212 630 196 612 222 590M222 590l-13 3M222 590l-2 14", "none", PLUM, 2) + demo(14, ly + 22)


def fD(pg):
    seats = [("Detaljist", "Ida", "bestilt", ""), ("Grossist", "Sara", "deg-bestilt", ""),
             ("Distributør", "Mikkel", "bestilt", ""), ("Fabrikk", "Jonas", "bestilt", "")]
    s = snor(pg, 12, 12, 366, seats, 70)
    b, ly = bunke(8, BY, 374, 12, highlight=11)
    pink_under = f'<g transform="rotate(-2.5 195 400)">{pg.paper(4, 110, 374, 580, PINK)}{T(30, 676, "KOPI Uke 11: 24, BESTILT", 15, "typb", CARBON)}</g>'

    def body(fx, oy, w):
        o = R(fx, oy, w, 100, CAN_L, INK, 2.2) + T(fx + 9, oy + 19, "ORDRE", 15, "labb", INK, ls=.6)
        o += T(fx, oy + 128, "Bunken ble en kant tykkere.", 15, "lab", INK)
        return o
    new = ordreseddel(pg, 12, None, form_h=550, body=body)
    new += plain_button(16, 584, 248, 48, "Hopp over", INK, 18, INK)
    new = f'<g>{new}<animateTransform attributeName="transform" type="translate" values="0 -560;0 0;0 0" keyTimes="0;.2;1" calcMode="spline" keySplines=".16 1 .3 1;0 0 1 1" dur="6s" repeatCount="indefinite"/></g>'
    return s + b + pink_under + new + demo(14, ly + 22)


def fE(pg):
    seats = [("Detaljist", "Ida", "bestilt", ""), ("Grossist", "Sara", "deg-bestilt", ""),
             ("Distributør", "Mikkel", "bestilt", ""), ("Fabrikk", "Jonas", "ki", "")]
    out = snor(pg, 12, 12, 366, seats, 70)
    y = 96
    out += pg.paper(8, y, 374, 90, BLUE_L)
    out += icon_pause(20, y + 13, NAVY, 18) + T(46, y + 28, "PAUSE, SATT AV IDA", 16, "labb", NAVY, ls=.3)
    out += T(20, y + 54, "«Fortsetter i kveld 19:00.» Jonas kom ikke.", 15, "nar", NAVY)
    out += T(20, y + 76, "Ida satte KI-spiller i setet 19:15.", 15, "nar", NAVY)
    y2 = 196
    out += pg.paper(8, y2, 374, 106, PINK)
    out += T(20, y2 + 28, "KOPI, Uke 11: 24", 18, "typb", CARBON)
    out += T(20, y2 + 56, "Ordren din står. Fabrikk spilles nå av", 16, "lab", PLUM)
    out += T(20, y2 + 78, "KI-spiller. Uka går videre når den har bestilt.", 16, "lab", PLUM)
    y3 = 312
    out += pg.paper(8, y3, 374, 374, CAN)
    out += perf_h(14, y3 + 8, 362, DESK, 2.2)
    out += T(20, y3 + 44, "Samme øyeblikk på telefonen til Jonas", 26, "pen", INK)
    out += icon_role("Fabrikk", 20, y3 + 62, 28)
    out += T(56, y3 + 82, "Setet ditt, Fabrikk", 19, "disp", INK)
    out += ki_mark(20, y3 + 104, VIO, 26, "KI-spiller har setet", 16)
    out += TW(20, y3 + 160, "Ukene KI-spilleren bestiller står merket i bunken din, og de teller ikke som dine egne Ordrer.", 346, 16, "nar", INK, 22)
    out += stamp_button(20, y3 + 252, 350, 86, "TA TILBAKE SETET", "Gjelder fra neste Uke", True, 21)
    b, ly = bunke(8, BY, 374, 11)
    return out + b + demo(14, ly + 22)


def fF(pg):
    y = 26
    out = pg.paper(8, y, 374, 618, CAN)
    out += perf_h(14, y + 8, 362, DESK, 2.2)
    out += T(22, y + 48, "SLUTTOPPGJØR", 25, "disp", INK)
    out += T(22, y + 70, "Spill 17. Spillet er slutt.", 15, "lab", INK)
    out += field(20, y + 86, 350, 118, "Kjeden totalt", num(FX["chain_total_cost"]) + " kr", INK, INK, 44, lsize=14)
    out += stamp(pg, 286, y + 124, "AVSLUTTET", 14, -5, VIO)
    ry = y + 226
    out += T(22, ry, "PER ROLLE", 13, "lab", INK, ls=.5)
    for i, r in enumerate(ROLES):
        yy = ry + 8 + i * 58
        out += R(20, yy, 350, 58, "none", INK, 1.1)
        out += icon_role(r, 30, yy + 17, 24)
        out += T(64, yy + 36, r, 18, "lab", INK)
        out += T(360, yy + 38, num(FX["total_cost_per_role"][r]) + " kr", 22, "typb", INK, "end")
    out += T(22, ry + 262, "Kostnaden står per Rolle, ikke per navn.", 15, "nar", INK)
    out += stamp_button(20, ry + 278, 350, 80, "VIDERE TIL DEBRIEF", "Bunkene legges på bordet", True, 20)
    b, ly = bunke(8, y + 624, 374, 37, tab_h=46)
    return b + out + demo(14, ly + 18)


def storyboard():
    pg = Page("dyn", "06-spilldynamikk.svg", 2100, 1200, "Fraktbrev: spilldynamikk i seks ruter",
              "Storyboard: uka åpner, beslutningen, stemplet, uka går videre, Jonas borte med KI-spiller, spillet slutter.")
    frames = [
        ("A", "Uka åpner", "Arket ligger øverst, ferdig skrevet. Blyanten ringer inn det som kom: 8 inn, 4 levert. Bare ORDRE er tomt.", fA),
        ("B", "Beslutningen", "Sara skriver 24. Et stiplet fraktbrev tegner seg under de tre som allerede er på vei: 24 mot 16. Stempelet våkner.", fB),
        ("C", "Bekreftet", "Stempelet slår. Originalen rives av og flyr oppstrøms, den ser hun aldri igjen. Skjermen er nå den rosa kopien, og 24 er blitt et ekte fraktbrev.", fC),
        ("D", "Uka går videre", "Kopien legger seg i bunken, en kant tykkere. Uke 12 glir over. Under 2 sek, og «Hopp over» tar det med en gang.", fD),
        ("E", "Jonas er borte", "Pause holder KI-spilleren unna. Når avtalen ryker, setter gruppa inn KI-spiller, merket med tekst på snora. Jonas kan ta tilbake setet.", fE),
        ("F", "Spillet slutter", "Bunken stopper uten forvarsel. Først kjedens totalkostnad, så per Rolle, aldri per navn. Så Debrief.", fF),
    ]
    S = .8
    fw = 390 * S
    gap = (2100 - 6 * fw - 2 * 34) / 5
    for i, (lt, head, txt, fn) in enumerate(frames):
        x = 34 + i * (fw + gap)
        pg.add(T(x, 56, lt, 44, "disp", CAN) + T(x + 46, 54, head, 30, "disp", PALE))
        pg.add(phone(pg, x, 86, fn(pg), S))
        lines = wrap(txt, fw - 24, 17, "nar")
        h = 22 + len(lines) * 23
        pg.add(pg.paper(x, 790, fw, h, REC))
        for j, ln in enumerate(lines):
            pg.add(T(x + 12, 790 + 26 + j * 23, ln, 17, "nar", INK))
    # tekst under
    y = 948
    pg.add(pg.paper(34, y, 2032, 222, CAN))
    pg.add(perf_h(42, y + 8, 2016, DESK, 2.2))
    pg.add(T(58, y + 66, "Hva som gjør", 36, "disp", INK) + T(58, y + 110, "dette unikt", 36, "disp", INK))
    txt = ("Du fyller ikke ut et skjema, du signerer et som allerede er ferdig. Alt systemet vet står skrevet, og det eneste tomme feltet er ditt, så beslutningen tar sekunder også i Uke 30. "
           "Stempelet er ugjenkallelig, og det føles: originalen rives av og er borte, mens kopien blir igjen. "
           "Det som er på vei er ikke et tall, men en søyle av papir klipset på siden, så høy som kassene, og det stiplede fraktbrevet viser 24 ved siden av 16 før du slår. "
           "Ingenting forsvinner: hver uke er et ark du kan bla i, og bunkens tykkelse er eneste klokke.")
    pg.add(TW(430, y + 52, txt, 1780, 27, "nar", INK, 38))
    pg.save()


# ---------- 07 ----------
def role_series(key="ordre"):
    return {r: [w["seats"][r][key] for w in WEEKS] for r in ROLES}


LINE = {"Detaljist": (INK, 2, ""), "Grossist": (VIO, 3, ""), "Distributør": ("#0A6C9E", 2.2, "7 4"), "Fabrikk": (RED, 2.2, "2 3")}


def chart(x, y, w, h, labels=True, size=13, mark_w11=True):
    """Ordrer per Rolle over tid. Felles akse, til skala fra fixture."""
    ser = role_series()
    ymax = 32
    px = lambda wk: x + (wk - 1) / 35 * w
    py = lambda v: y + h - v / ymax * h
    o = ""
    for v in (0, 8, 16, 24, 32):
        o += L(x, py(v), x + w, py(v), INK, .5, 'opacity=".35"') + T(x - 5, py(v) + 4, str(v), size, "nar", INK, "end")
    for wk in (1, 12, 24, 36):
        o += T(px(wk), y + h + size + 3, f"{wk}", size, "nar", INK, "middle")
    # etterspoersel smalt og rolig
    dem = [w_["demand"] for w_ in WEEKS]
    d = " ".join(("M" if i == 0 else "L") + f"{px(i + 1):.1f} {py(v):.1f}" for i, v in enumerate(dem))
    o += P(d, "none", "#6B6B6B", 5, 'opacity=".45"')
    for r in ROLES:
        c, sw, dash = LINE[r]
        d = " ".join(("M" if i == 0 else "L") + f"{px(i + 1):.1f} {py(v):.1f}" for i, v in enumerate(ser[r]))
        da = f'stroke-dasharray="{dash}"' if dash else ""
        o += P(d, "none", c, sw, da)
    if mark_w11:
        o += C(px(11), py(24), 4.5, VIO, "#fff", 1.5) + T(px(11) - 8, py(24) + 4, "24", size + 1, "typb", VIO, "end")
    return o


def debrief_1(pg):
    o = pg.paper(8, 24, 374, 470, PINK)
    o += T(22, 62, "FORKLARING", 24, "disp", PLUM)
    o += T(22, 84, "Bare du ser det du skriver her.", 15, "lab", PLUM)
    o += T(22, 118, "Hvorfor oppførte kjeden seg slik,", 17, "labb", PLUM)
    o += T(22, 140, "og hvilken del spilte Ordrene dine?", 17, "labb", PLUM)
    o += R(20, 154, 350, 240, PINK_L, PLUM, 1.6)
    txt = "Vi gikk tomme rundt Uke 9. Restordren vokste selv om jeg bestilte mer, så jeg bestilte enda mer. Da alt kom, satt vi med for mye."
    o += TW(30, 182, txt, 330, 17, "typ", CARBON, 25)
    o += R(30, 318, 2, 20, CARBON)
    o += stamp_button(20, 408, 350, 74, "LAGRE FORKLARING", "Da åpnes neste steg for deg", True, 20)
    # forseglet
    y = 510
    o += pg.paper(8, y, 374, 170, REC)
    o += perf_v(16, y + 6, 158, DESK, 2)
    o += perf_v(374, y + 6, 158, DESK, 2)
    o += icon_lock(34, y + 22, INK, 24) + T(66, y + 42, "LÅST", 24, "disp", INK)
    o += TW(34, y + 74, "Noe ligger forseglet her. Det åpnes først når Forklaringen din er lagret.", 320, 16, "nar", INK, 22)
    o += stamp(pg, 290, y + 34, "FORSEGLET", 11, 4, RED, False, False)
    # gruppa
    y = 696
    o += T(14, y + 6, "GRUPPEDEBRIEF", 13, "lab", PALE, ls=.5)
    for i, (n, st) in enumerate([("Ida", "lagret"), ("Mikkel", "skriver"), ("Jonas", "skriver"), ("Sara", "deg")]):
        o += T(14 + (i % 2) * 180, y + 30 + (i // 2) * 24, n, 16, "typb", PALE) + T(84 + (i % 2) * 180, y + 30 + (i // 2) * 24, st, 15, "nar", PALE)
    o += demo(14, 800)
    return o


def peaks():
    return {r: max(role_series()[r]) for r in ROLES}


def debrief_2(pg):
    pk = peaks()
    o = T(14, 30, "Høyeste Ordre per Rolle. Alle i samme skala.", 15, "lab", PALE)
    pos = {"Fabrikk": (12, 178, -4, CAN), "Distributør": (224, 178, 4, PINK), "Grossist": (22, 590, 3, BLUE), "Detaljist": (262, 582, -4, REC)}
    for r, (x, y, rot, col) in pos.items():
        v = pk[r]
        g = T(0, 0, str(v), v * 5.2, "disp", col, extra=f'filter="url(#{pg.ink})"') + T(4, 22, r, 15, "labb", PALE)
        o += f'<g transform="translate({x} {y}) rotate({rot})">{g}</g>'
    # kvittering: liten og rolig
    rx, ry, rw, rh = 104, 222, 182, 208
    d = f"M{rx} {ry}h{rw}v{rh}" + "".join(" l-10.1 8 l-10.1 -8" for _ in range(9)) + "z"
    o += f'<g filter="url(#{pg.sh})">{P(d, REC, None)}</g>'
    o += T(rx + rw / 2, ry + 26, "BUTIKKEN", 16, "disp", INK, "middle")
    o += T(rx + rw / 2, ry + 44, "kunder per uke", 13, "typ", INK, "middle")
    o += L(rx + 10, ry + 53, rx + rw - 10, ry + 53, INK, 1, 'stroke-dasharray="3 3"')
    o += T(rx + 12, ry + 74, "Uke 1-4", 15, "typ", INK) + T(rx + rw - 12, ry + 74, "4", 17, "typb", INK, "end")
    o += T(rx + 12, ry + 96, "Uke 5-36", 15, "typ", INK) + T(rx + rw - 12, ry + 96, "8", 17, "typb", INK, "end")
    o += L(rx + 10, ry + 106, rx + rw - 10, ry + 106, INK, 1, 'stroke-dasharray="3 3"')
    gx, gy, gw, gh = rx + 14, ry + 146, rw - 28, 80
    px = lambda w_: gx + (w_ - 1) / 35 * gw
    py = lambda v: gy - v / 32 * gh
    dm = " ".join(("M" if i == 0 else "L") + f"{px(i + 1):.1f} {py(w_['demand']):.1f}" for i, w_ in enumerate(WEEKS))
    o += L(gx, gy, gx + gw, gy, INK, .8) + P(dm, "none", INK, 2)
    o += T(rx + rw / 2, gy + 22, "Det var alt.", 16, "typb", INK, "middle")
    o += T(rx + rw / 2, gy + 42, "Takk for handelen", 13, "typ", INK, "middle")
    o += T(14, 662, "Dette heter ølspillet.", 24, "disp", CAN)
    o += TW(14, 692, "Kundene endret seg én gang, i Uke 5. Alt det andre kom fra kjeden.", 370, 18, "nar", PALE, 24)
    o += plain_button(14, 750, 362, 46, "Neste steg", PALE, 16)
    o += demo(14, 824)
    return o


def debrief_3(pg):
    o = pg.paper(8, 24, 374, 660, REC)
    o += T(22, 62, "Ordrene ble større", 24, "disp", INK)
    o += T(22, 84, "for hvert ledd", 24, "disp", INK)
    o += chart(46, 112, 318, 250)
    o += T(46, 392, "Uke. Tykk grå strek er kundene. Ring er din 24.", 13, "nar", INK)
    # forklaring med linjestil
    y = 412
    o += T(22, y + 6, "ORDREFORSTERKNING MOT KUNDENE", 13, "lab", INK, ls=.3)
    for i, r in enumerate(ROLES):
        c, sw, dash = LINE[r]
        yy = y + 18 + i * 50
        da = f'stroke-dasharray="{dash}"' if dash else ""
        o += L(22, yy + 22, 52, yy + 22, c, sw, da) + icon_role(r, 60, yy + 10, 22)
        o += T(90, yy + 28, r, 16, "lab", INK)
        a = FX["amplification"][r]
        bw = a / 7.6 * 110
        o += R(190, yy + 12, bw, 20, c if r != "Fabrikk" else RED)
        o += T(366, yy + 30, num(a, 1) + "×", 22, "typb", INK, "end")
    o += TW(22, y + 232, "Ingen i kjeden gjorde noe rart. Hvert ledd så bare ordren fra leddet under.", 340, 15, "nar", INK, 20)
    o += T(22, 690 - 0, "", 13)
    o += plain_button(20, 700, 170, 40, "Vis som tabell", PALE, 15)
    o += plain_button(200, 700, 170, 40, "Neste steg", PALE, 15)
    o += demo(14, 770)
    return o


def debrief_4(pg):
    d = WEEKS[10]["seats"]
    g = d["Grossist"]
    later = WEEKS[35]["seats"]["Grossist"]["kost_sum"] - WEEKS[23]["seats"]["Grossist"]["kost_sum"]
    peak_lager = max(w["seats"]["Grossist"]["lager"] for w in WEEKS)
    o = f'<g filter="url(#{pg.sh})">{torn_top(8, 20, 374, 300, PINK)}</g>'
    o += T(22, 52, "DITT ØYEBLIKK: UKE 11", 21, "disp", PLUM)
    fy = 66
    for i, (lb, v, c) in enumerate([("Lager", g["lager"], CARBON), ("Restordre", g["restordre"], CARBON), ("Ordre inn", g["innkommende_ordre"], CARBON), ("På vei", g["paa_vei_foer_ordre"], CARBON)]):
        o += field(20 + i * 87.5, fy, 87.5, 66, lb, str(v), PLUM, c, 26)
    o += R(20, fy + 74, 350, 88, PINK_L, PLUM, 2)
    o += T(30, fy + 94, "DU BESTILTE", 13, "lab", PLUM)
    o += T(30, fy + 150, str(g["ordre"]), 54, "typb", CARBON)
    o += stamp(pg, 270, fy + 120, "BESTILT", 19, -6)
    o += T(22, fy + 186, "Du så 13 i restordre.", 16, "typb", CARBON)
    o += T(22, fy + 208, "De 16 på vei var allerede bestilt.", 15, "typ", CARBON)
    o += T(22, fy + 228, "De kom, men uker etter stempelet.", 15, "typ", CARBON)
    # senere
    y = 328
    o += pg.paper(8, y, 374, 134, BLUE)
    o += T(20, y + 26, "HVA DET KOSTET SENERE", 14, "labb", NAVY, ls=.3)
    o += T(20, y + 52, f"Uke 13: Mikkel fikk {WEEKS[12]['seats']['Distributør']['innkommende_ordre']}, uka før {WEEKS[11]['seats']['Distributør']['innkommende_ordre']}.", 15, "typ", NAVY)
    o += T(20, y + 74, f"Uke 25-36: lageret ditt nådde {peak_lager}.", 15, "typ", NAVY)
    o += T(20, y + 96, "Kostnad disse ukene:", 15, "typ", NAVY)
    o += T(20, y + 122, f"{num(later)} kr", 24, "typb", NAVY)
    # de andre
    y = 470
    o += pg.paper(8, y, 374, 136, REC)
    o += T(20, y + 24, "SAMME UKE SÅ DE ANDRE", 14, "labb", INK, ls=.3)
    rows = [("Detaljist", "Ida"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]
    for i, (r, n) in enumerate(rows):
        s = d[r]
        yy = y + 50 + i * 28
        o += icon_role(r, 20, yy - 15, 20)
        o += T(46, yy, r, 15, "lab", INK)
        o += T(370, yy, f"lager {s['lager']} · rest {s['restordre']} · på vei {s['paa_vei_foer_ordre']}", 13.5, "typ", INK, "end")
    # KI-tekst
    y = 614
    o += pg.paper(8, y, 374, 150, CAN)
    o += ki_mark(20, y + 12, VIO, 22, "KI-generert, kan ta feil", 14)
    o += TW(20, y + 58, "Forsinkelsen skilte beslutningen fra virkningen: fire uker fra Ordre til levering. Mønsteret heter å overse forsyningslinja.", 350, 15, "nar", INK, 20)
    o += plain_button(20, y + 106, 350, 34, "Spør om Uke 11", INK, 15)
    o += demo(14, 790)
    return o


def debrief_5(pg):
    o = pg.paper(8, 24, 374, 680, CAN)
    o += T(22, 62, "DEBRIEF-QUIZ", 24, "disp", INK)
    o += T(22, 84, "Teller ikke. Du kan prøve igjen.", 15, "lab", INK)
    o += TW(22, 120, "Du hadde 13 i restordre og 16 på vei. Hvorfor vokste restordren videre etter at du bestilte 24?", 340, 18, "labb", INK, 24)
    opts = [("A", "Mikkel holdt tilbake kasser", "feil"), ("B", "Ordren brukte uker på å bli til levering", "rett"),
            ("C", "Kundene kjøpte stadig mer", "feil"), ("D", "Du bestilte for lite", "")]
    y = 214
    for i, (k, txt, st) in enumerate(opts):
        yy = y + i * 52
        o += R(20, yy, 350, 46, "none" if k != "A" else CAN_L, INK, 1.2)
        o += R(30, yy + 13, 20, 20, "#fff", INK, 1.4)
        if k == "A":
            o += P(f"M32 {yy + 15}l16 16M48 {yy + 15}l-16 16", "none", RED, 3)
        o += T(60, yy + 29, txt, 16, "lab", INK)
    # forklart
    y = 432
    o += pg.paper(20, y, 350, 190, PINK)
    o += T(32, y + 28, "A er feil", 22, "disp", PLUM)
    o += TW(32, y + 56, "Mikkel sendte det han hadde. Ordren din var underveis i to uker, frakten to til. Restordren vokste fordi Ordre inn var større enn Levering i de ukene.", 326, 15, "nar", PLUM, 20)
    o += ki_mark(32, y + 152, VIO, 24, "KI-generert, kan ta feil", 14)
    o += stamp_button(20, 632, 350, 62, "SVAR PÅ NYTT", None, True, 18)
    o += demo(14, 740)
    return o


def shared_screen(pg, x, y, w, h):
    """Delt skjerm: bunkene ligger paa bordet, sortert per Rolle. Alle stolper i samme skala."""
    o = R(x, y, w, h, DESK)
    o += T(x + 22, y + 36, "Bunkene på bordet", 26, "disp", PALE)
    o += T(x + w - 22, y + 34, "Spill 17. Bare felles diagrammer her. Samme skala i alle rader.", 15, "lab", PALE, "end")
    ser = role_series()
    lx = x + 214
    colw = (w - 214 - 22) / 36
    rows = [("Fabrikk", CAN), ("Distributør", PINK), ("Grossist", BLUE), ("Detaljist", REC), ("Kundene", "#fff")]
    rh = (h - 62 - 26) / 5
    unit = (rh - 6) / 32
    for i, (r, fill) in enumerate(rows):
        by = y + 56 + (i + 1) * rh
        vals = ser[r] if r != "Kundene" else [w_["demand"] for w_ in WEEKS]
        if r != "Kundene":
            o += icon_role(r, x + 22, by - 30, 24, PALE)
            o += T(x + 54, by - 12, r, 17, "labb", PALE) + T(x + 204, by - 10, num(FX["amplification"][r], 1) + "×", 21, "typb", PALE, "end")
        else:
            o += T(x + 22, by - 12, "Kvitteringen", 17, "labb", CAN) + T(x + 204, by - 10, "4, så 8", 17, "typb", CAN, "end")
        for wk, v in enumerate(vals):
            hh = max(v * unit, 1)
            o += R(lx + wk * colw + 1, by - hh, colw - 2.2, hh, fill)
        o += L(lx, by + .5, x + w - 22, by + .5, STEEL, .8)
    o += T(lx, y + h - 8, "Uke 1", 13, "nar", PALE) + T(x + w - 22, y + h - 8, "Uke 36", 13, "nar", PALE, "end")
    o += demo(x + 22, y + h - 8)
    return o


def debrief():
    pg = Page("deb", "07-debrief.svg", 2100, 1200, "Fraktbrev: Gruppedebrief i fem steg",
              "Fem telefoner og en delt skjerm: Forklaring og forsegling, kvitteringen fra butikken, ordrer per Rolle, ditt øyeblikk i Uke 11, quiz med forklart feil.")
    S = .82
    fw = 390 * S
    frames = [("1", "Skriv Forklaringen", debrief_1), ("2", "Kvitteringen", debrief_2), ("3", "Hele kjeden", debrief_3),
              ("4", "Ditt øyeblikk", debrief_4), ("5", "Quiz", debrief_5)]
    gap = (2100 - 68 - 5 * fw) / 4
    for i, (n, head, fn) in enumerate(frames):
        x = 34 + i * (fw + gap)
        pg.add(T(x, 56, n, 42, "disp", CAN) + T(x + 36, 54, head, 28, "disp", PALE))
        pg.add(phone(pg, x, 82, fn(pg), S))
    sx, sy, sw, sh = 42, 806, 1130, 374
    pg.add(R(sx - 8, sy - 8, sw + 16, sh + 16, "#0B0A0D", "#55525E", 2, 10))
    i = pg.clip(sx, sy, sw, sh)
    pg.add(f'<g clip-path="url(#{i})">{shared_screen(pg, sx, sy, sw, sh)}</g>')
    # grep
    y = 806
    pg.add(pg.paper(1210, y, 856, 374, CAN))
    pg.add(perf_h(1218, y + 8, 840, DESK, 2.2))
    pg.add(T(1236, y + 62, "Skrikende ordrer,", 34, "disp") + T(1236, y + 104, "en rolig kvittering", 34, "disp"))
    txt = ("Du skriver først, med kvitteringen forseglet. Så legges bunkene ut på bordet, og midt mellom ordrer på 31, 24 og 22 ligger en liten lapp fra butikken: kundene gikk fra 4 til 8, og så skjedde det ikke mer. "
           "Etterpå trekker du din egen rosa kopi ut av bunken og leser Uke 11 med det du nå vet. Alt du gjorde står der fortsatt.")
    pg.add(TW(1236, y + 150, txt, 800, 23, "nar", INK, 32))
    pg.add(T(1236, y + 350, "Forklaring og egne øyeblikk blir på hver sin telefon. Det delte lerretet viser bare felles diagrammer.", 16, "lab", INK))
    pg.save()
