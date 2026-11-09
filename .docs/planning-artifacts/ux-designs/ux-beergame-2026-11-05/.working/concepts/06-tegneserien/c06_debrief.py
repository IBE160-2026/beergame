"""07 Debrief: albumet leses tilbake. Fem telefoner og en delt skjerm."""
from c06_ink import *  # noqa: F403
from c06_game import ministrip

W = FX["weeks"]
AMP = FX["amplification"]


def amp(role):
    return f"{AMP[role]:.1f}".replace(".", ",") + "×"


def locked_panel(x, y, w, h):
    o = [ibox(x, y, w, h, INK, None, 3, mis=(0, 0))]
    o.append(ic_lock(x + 46, y + h / 2 - 8, 1.25))
    o.append(T(x + 84, y + 40, "Avsløringen er låst", 22, "hb", WHITE))
    o.append(T(x + 84, y + 66, "Den åpner når alle fire har", 17, "h", WHITE))
    o.append(T(x + 84, y + 87, "skrevet sin Forklaring.", 17, "h", WHITE))
    return "".join(o)


def d1():
    """Skriv din egen bildetekst før avsløringen."""
    o = [T(12, 66, "Debrief", 30, "d")]
    o.append(T(12, 92, "Spill 17. Albumet ditt, lest bakfra.", 17))
    o.append(g("rotate(-1.5 195 150)", ministrip(10, 108, 11, .328)))
    o.append(plain(10, 164, 370, 34, WHITE, 2))
    o.append(T(20, 187, "Uke 11: du sa 24", 19, "hb"))
    o.append(ibox(10, 208, 370, 286, YEL, None, 3))
    o.append(T(24, 240, "Forklaring", 24, "d"))
    o.append(T(24, 266, "Skriv din egen bildetekst til albumet:", 18))
    o.append(T(24, 288, "Hvorfor svingte ordrene så mye i kjeden?", 18, "hb"))
    o.append(plain(22, 300, 346, 142, WHITE, 2.4))
    t = "Kunden må ha kjøpt mer og mer utover i spillet. Jeg bestilte mye fordi jeg aldri fikk nok og trodde det ville fortsette."
    o.append(Pg(34, 328, t, 318, 19, lh=1.2))
    o.append(f'<rect x="248" y="402" width="3" height="22" fill="{MAG}"/>')
    o.append(T(24, 468, "Du er den eneste som ser dette før du lagrer.", 16))
    o.append(locked_panel(10, 504, 370, 112))
    o.append(T(12, 644, "Har skrevet", 17, "hb"))
    rows = [("Detaljist", "Ida", True), ("Grossist", "deg", False), ("Distributør", "Mikkel", True), ("Fabrikk", "Jonas", False)]
    for i, (r, n, ok) in enumerate(rows):
        x = 10 + i * 93
        o.append(mark(x + 10, 666, r, 7))
        o.append(T(x + 22, 672, n, 16.5, "hb"))
        o.append((ic_check if ok else ic_hour)(x + 22 + 8, 690, .8))
        o.append(T(x + 40, 696, "Klar" if ok else "Skriver", 14.5))
    o.append(button(10, 712, 370, 56, "Lagre Forklaringen", "prim", 21))
    o.append(T(12, 796, "Kan ikke endres etter avsløringen.", 15.5, "h", SOFT))
    o.append(T(378, 796, "Demodata", 14.5, "hb", INK, "end"))
    return "".join(o)


def d2():
    """Klimaks: stille side-rute. Ingen lydord, nesten bare papir."""
    o = [T(195, 66, "Kundens side", 26, "d", INK, "middle")]
    o.append(T(195, 92, "Denne ruta hadde ingen av dere.", 18, "h", INK, "middle"))
    o.append(ibox(10, 106, 370, 372, WHITE, None, 3, mis=(0, 0)))
    # kunden, helt rolig
    o.append(fig(58, 268, "Kunde", 1.05, "rolig"))
    o.append(iline(20, 269, 370, 269, 2))
    o.append(T(112, 146, "Kunden kjøpte 4 kasser", 22, "hb"))
    o.append(T(112, 172, "i uka. I uke 5 kjøpte", 22, "hb"))
    o.append(T(112, 198, "kunden 8.", 22, "hb"))
    o.append(T(112, 238, "Så skjedde det ikke mer.", 22, "hb"))
    # etterspørsel til skala
    cx, cy, cw, ch = 40, 296, 322, 148
    ymax = 10
    sx = lambda u: cx + (u - 1) * cw / 35
    sy = lambda v: cy + ch - v * ch / ymax
    for v in (0, 4, 8):
        o.append(f'<path d="M{cx} {sy(v):.1f}H{cx+cw}" stroke="{SOFT}" stroke-width="{1.4 if v == 0 else .8}"/>')
        o.append(T(cx - 8, sy(v) + 5, v, 15, "h", INK, "end"))
    d = "M" + "L".join(f"{sx(w['week']):.1f} {sy(w['demand']):.1f}" for w in W)
    # trapp, ikke skrå: kundens tall endrer seg mellom to uker
    step = f"M{sx(1):.1f} {sy(4):.1f}H{sx(5):.1f}V{sy(8):.1f}H{sx(36):.1f}"
    o.append(path(step, stroke=INK, sw=4))
    o.append(circ(sx(5), sy(8), 5, MAG, INK, 2))
    o.append(T(sx(5) + 10, sy(8) - 10, "Uke 5: fra 4 til 8", 17, "hb"))
    for u in (1, 5, 36):
        o.append(T(sx(u), cy + ch + 20, u, 15, "h", INK, "middle"))
    o.append(T(sx(18), cy + ch + 20, "Uke", 15, "h", INK, "middle"))
    # sammenstilling med egen tekst
    o.append(ibox(10, 488, 370, 118, YEL, None, 3))
    o.append(T(24, 516, "Du skrev:", 18, "hb"))
    o.append(T(24, 540, "«Kunden må ha kjøpt mer og mer.»", 20, "hb"))
    o.append(T(24, 566, "Slik så kjeden ut fra din plass. Det du", 18))
    o.append(T(24, 588, "så, var ordrene, ikke kunden.", 18))
    o.append(T(12, 636, "Dette er ølspillet, Beer Game. Kunden gjør", 18))
    o.append(T(12, 658, "nesten ingenting. Kjeden gjør resten.", 18))
    o.append(button(10, 680, 370, 56, "Se hva endringen gjorde", "prim", 19))
    o.append(T(12, 766, "Demodata", 14.5, "hb"))
    return "".join(o)


STYLE_LINE = {"Detaljist": YEL, "Grossist": CYA, "Distributør": MAG, "Fabrikk": PAPER}


def order_chart(x, y, w, h, labels=True):
    ymax = 32
    sx = lambda u: x + (u - 1) * w / 35
    sy = lambda v: y + h - v * h / ymax
    o = []
    for v in (0, 10, 20, 30):
        o.append(f'<path d="M{x} {sy(v):.1f}H{x+w}" stroke="{SOFT}" stroke-width="{1.4 if v == 0 else .7}"/>')
        o.append(T(x - 6, sy(v) + 5, v, 14, "h", INK, "end"))
    for u in (1, 11, 20, 36):
        o.append(T(sx(u), y + h + 18, u, 14, "h", INK, "middle"))
    o.append(T(sx(28), y + h + 18, "Uke", 14, "h", INK, "middle"))
    # kunden som tynn stiplet referanse
    o.append(path(f"M{sx(1):.1f} {sy(4):.1f}H{sx(5):.1f}V{sy(8):.1f}H{sx(36):.1f}", stroke=INK, sw=1.6, extra=' stroke-dasharray="3 4"'))
    for role in ROLES:
        ser = orders(role)
        d = "M" + "L".join(f"{sx(i+1):.1f} {sy(v):.1f}" for i, v in enumerate(ser))
        o.append(path(d, stroke=INK, sw=3.8 if role != "Fabrikk" else 2.6))
        if role != "Fabrikk":
            o.append(path(d, stroke=STYLE_LINE[role], sw=2.2))
    if labels:
        peaks = {"Grossist": (11, 24, -9, 0, "end", "Grossist 24"), "Distributør": (14, 22, 2, -13, "start", "Distributør 22"),
                 "Fabrikk": (18, 31, 9, 5, "start", "Fabrikk 31"), "Detaljist": (15, 12, -46, -12, "end", "Detaljist 12")}
        for role, (u, v, dx, dy, a, lab) in peaks.items():
            o.append(mark(sx(u), sy(v), role, 5.5, 1.8))
            tx, ty = sx(u) + dx, sy(v) + dy
            o.append(f'<text x="{tx:.1f}" y="{ty:.1f}" class="c06-hb" font-size="16" fill="{INK}" text-anchor="{a}" stroke="{WHITE}" '
                     f'stroke-width="3.4" paint-order="stroke" style="color:{INK}">{lab}</text>')
    return "".join(o)


def d3():
    o = [T(12, 66, "Fire striper oppå hverandre", 19.5, "d")]
    o.append(T(12, 92, "Samme kunde. Ordrene per Rolle, alle 36 uker.", 17.5))
    o.append(ibox(10, 104, 370, 298, WHITE, None, 3, mis=(0, 0)))
    o.append(order_chart(46, 118, 322, 228))
    o.append(T(46, 394, "Stiplet linje: kunden, 4 og så 8.", 16, "hb"))
    # forsterkning som trapp, figurene vokser i tall ikke i verdi
    o.append(T(12, 428, "Ordreforsterkning", 21, "hb"))
    o.append(T(378, 428, "kunden = 1,0×", 16, "h", INK, "end"))
    base = 612
    k = 18.0  # px per ganger, til skala
    bw = 86
    for i, role in enumerate(ROLES):
        x = 12 + i * (bw + 7)
        hh = AMP[role] * k
        o.append(ibox(x, base - hh, bw, hh, ROLE_FILL[role], "dk" if role == "Fabrikk" else None, 2.4, mis=(1.5, 1.5)))
        o.append(T(x + bw / 2, base - hh - 8, amp(role), 21, "d", INK, "middle"))
        o.append(mark(x + 12, base + 17, role, 7))
        o.append(T(x + 24, base + 22, role[:8] if role != "Distributør" else "Distrib.", 15.5))
    o.append(iline(8, base, 382, base, 2.4))
    o.append(T(12, 664, "Hver Rolle svarte på ordren foran seg. For", 18))
    o.append(T(12, 686, "hvert ledd ble svingningen større, uten at", 18))
    o.append(T(12, 708, "kunden gjorde noe nytt.", 18))
    o.append(T(12, 740, "Tabellvisning", 16, "hb"))
    o.append(iline(12, 744, 92, 744, 1.4))
    o.append(T(12, 776, "Kjeden totalt " + nok(FX["chain_total_cost"]), 16.5, "hb"))
    o.append(T(378, 776, "Demodata", 14.5, "hb", INK, "end"))
    return "".join(o)


def d4():
    s = state(11, "24")
    o = [T(12, 62, "Ditt øyeblikk: Uke 11", 22, "d")]
    # hva du så
    o.append(ibox(10, 74, 370, 118, PAPER, "dm", 3, mis=(0, 0)))
    o.append(plain(18, 82, 354, 102, WHITE, 2))
    o.append(T(28, 104, "Dette så du", 19, "hb"))
    o.append(T(28, 128, "Lager 0, restordre 13, ordre 8.", 18))
    o.append(road(366, 170, s["vans"], False, 6, None, roadfrom=210))
    o.append(T(28, 156, "16 på vei:", 18, "hb"))
    o.append(T(28, 176, "tre små biler", 18))
    # hva du bestilte
    o.append(fig(40, 280, "Grossist", .78, "rolig"))
    o.append(bubble(84, 200, 126, 80, (58, 232), "l", WHITE, 3))
    o.append(T(147, 258, "24", 46, "d", INK, "middle"))
    o.append(T(220, 222, "Dette bestilte du", 18, "hb"))
    o.append(van(220, 266, 24))
    o.append(T(220, 280, "Bil nummer fire.", 15.5))
    # kostnad senere
    G = [seat(i + 1) for i in range(36)]
    peak_rest = max(x["restordre"] for x in G)
    peak_lager = max(x["lager"] for x in G)
    hold = sum(x["lager"] * .5 for x in G[24:])
    o.append(ibox(10, 290, 370, 136, YEL, None, 3))
    o.append(T(24, 316, "Dette kostet det senere", 19, "hb"))
    lines = [f"Uke 15 kom {seat(15)['levering']} av de 24: Distributør var tom.",
             f"Restordren din nådde {peak_rest} i uke 22.",
             f"I uke 29 hadde du {peak_lager} på lager, og fra uke 25",
             f"kostet lageret deg {nok(hold)}."]
    for i, ln in enumerate(lines):
        o.append(T(24, 342 + i * 21, ln, 17))
    # de andre
    o.append(T(12, 450, "Dette så de andre", 19, "hb"))
    rows = [("Detaljist", "Ida, uke 11", "Ordre 8, restordre 4. Bestilte 10."),
            ("Distributør", "Mikkel, uke 13", "Din 24 kom etter 4, 4, 4, 8. Lager fra 12 til 0. Bestilte 20."),
            ("Fabrikk", "Jonas, uke 15", "Ordre 20 etter 8. Bestilte 17, og 31 i uke 18.")]
    y = 458
    for role, who, txt in rows:
        ln = wrap(txt, 302, 16)
        hh = 26 + len(ln) * 19 + 6
        o.append(plain(10, y, 370, hh, WHITE, 2))
        o.append(mark(30, y + 18, role, 8))
        o.append(T(50, y + 22, who, 17, "hb"))
        for i, l in enumerate(ln):
            o.append(T(50, y + 41 + i * 19, l, 16))
        y += hh + 4
    # KI-merking
    o.append(ibox(10, y + 2, 370, 86, WHITE, None, 2.6, mis=(0, 0)))
    o.append(ki_tag(36, y + 26, 1.05))
    o.append(T(66, y + 28, "KI-generert, kan ta feil", 18, "hb"))
    o.append(T(20, y + 52, "Ingen i kjeden så hele bildet, så hver ordre var et", 16))
    o.append(T(20, y + 72, "svar på det dere så. Tallene er regnet av systemet.", 16))
    o.append(T(378, y + 108, "Demodata", 14.5, "hb", INK, "end"))
    return "".join(o)


def d5():
    F = [w["seats"]["Fabrikk"] for w in W]
    o = [T(12, 66, "Debrief-quiz", 28, "d")]
    o.append(T(378, 64, "Spørsmål 3", 17, "h", INK, "end"))
    o.append(ibox(10, 80, 370, 112, YEL, None, 3))
    o.append(Pg(24, 112, "Kunden var stabil på 8 fra uke 5. Hvorfor bestilte Fabrikk 31 i uke 18?", 340, 22, "hb", lh=1.18))
    opts = [
        ("A", "Fabrikk så at kunden kjøpte mer.", "wrong"),
        ("B", "Fabrikk så bare ordrene fra Distributør, og de var blitt store.", "right"),
        ("C", "Lagerkosten var for lav til å bry seg om.", None),
    ]
    y = 204
    for let, txt, stt in opts:
        ln = wrap(txt, 280, 18.5)
        hh = 18 + len(ln) * 23
        fill = WHITE
        o.append(plain(10, y, 370, hh, fill, 3.2 if stt else 2))
        o.append(rr(22, y + hh / 2 - 14, 28, 28, 14, WHITE, INK, 2))
        o.append(T(36, y + hh / 2 + 6, let, 17, "hb", INK, "middle"))
        for i, l in enumerate(ln):
            o.append(T(62, y + 26 + i * 23, l, 18.5, "hb" if stt else "h"))
        if stt == "wrong":
            o.append(ic_x(362, y + hh / 2, 1.2, MAG))
        if stt == "right":
            o.append(ic_check(362, y + hh / 2, 1.2))
        y += hh + 7
    y += 2
    o.append(ibox(10, y, 370, 192, PAPER, "dm", 3, mis=(0, 0)))
    o.append(plain(18, y + 8, 354, 176, WHITE, 2))
    o.append(ic_x(36, y + 30, 1.1, MAG))
    o.append(T(52, y + 36, "Du svarte A. Det er ikke riktig.", 19, "hb"))
    inn = [F[i]["innkommende_ordre"] for i in range(14, 18)]
    txt = (f"Fabrikk ser aldri kunden. Det Fabrikk så i uke 15 til 18 var ordrene {inn[0]}, {inn[1]}, {inn[2]} og {inn[3]} fra Distributør, "
           "etter uker med 2 til 8. Fra den plassen ser det ut som kundene strømmer til.")
    o.append(Pg(28, y + 62, txt, 330, 17.5, lh=1.2))
    o.append(ki_tag(40, y + 168, .85))
    o.append(T(62, y + 171, "KI-generert, kan ta feil", 15.5, "hb"))
    y += 202
    o.append(button(10, y, 370, 54, "Neste spørsmål", "prim", 20))
    o.append(T(12, y + 80, "Teller ikke som karakter.", 15.5, "h", SOFT))
    o.append(T(378, y + 80, "Demodata", 14.5, "hb", INK, "end"))
    return "".join(o)


def wave(x, y, w):
    """Delt skjerm: kundens side-rute og fire striper oppå hverandre, samme skala."""
    o = []
    col = (w - 110 - 110) / 36
    rx = x + 112
    rowh = 56
    k = rowh / 32
    rows = [("Kunde", [i["demand"] for i in W])] + [(r, orders(r)) for r in ROLES]
    for i, (name, ser) in enumerate(rows):
        yb = y + 40 + (i + 1) * (rowh + 5) - 5
        if name != "Kunde":
            o.append(mark(x + 12, yb - 26, name, 8))
            o.append(T(x + 26, yb - 26, name, 18, "hb"))
            o.append(T(x + 26, yb - 8, NAMES[name], 16))
        else:
            o.append(fig(x + 12, yb, "Kunde", .42, mis=False))
            o.append(T(x + 28, yb - 8, "Kunden", 18, "hb"))
        o.append(f'<path d="M{rx:.1f} {yb:.1f}H{rx+col*36:.1f}" stroke="{INK}" stroke-width="1.8"/>')
        for j, v in enumerate(ser):
            hh = v * k
            fill = WHITE if name == "Kunde" else ROLE_FILL[name]
            o.append(f'<rect x="{rx+j*col+1:.1f}" y="{yb-hh:.1f}" width="{col-2:.1f}" height="{hh:.1f}" fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
        if name != "Kunde":
            o.append(T(rx + col * 36 + 12, yb - 12, amp(name), 26, "d"))
        else:
            o.append(T(rx + col * 36 + 12, yb - 12, "4 til 8", 18, "hb"))
    # bølgen: 24 i uke 11 når Distributør i uke 13 og Fabrikk i uke 15
    def pt(role_i, wk, v):
        yb = y + 40 + (role_i + 1) * (rowh + 5) - 5
        return rx + (wk - 1) * col + col / 2, yb - v * k
    a = pt(2, 11, 24)
    o.append(circ(a[0], a[1] - 6, 4, MAG, INK, 1.6))
    o.append(T(a[0] - 8, a[1] - 3, "Saras 24", 15.5, "hb", INK, "end"))
    b = pt(3, 13, 20)
    c = pt(4, 15, 17)
    o.append(arrow(a[0] + 4, a[1] + 8, b[0] + col, b[1] - 3, 2.2, INK, bend=-12, head=8))
    o.append(arrow(b[0] + col + 2, b[1] + 14, c[0] + col, c[1] - 3, 2.2, INK, bend=-12, head=8))
    return "".join(o)


def debrief():
    p = Page("07-debrief.svg", "deb", 2100, 1200, "Gruppedebrief: albumet leses tilbake",
             "Fem telefonruter og en delt skjerm: skriv Forklaring med låst avsløring, kundens rolige side-rute, ordrer per Rolle med forsterkning 1,8 til 7,6, ditt øyeblikk i Uke 11, quiz med feil svar forklart.")
    s = .8
    pw = 390 * s
    gap = (2100 - 5 * pw - 72) / 4
    p.add(f'<rect x="0" y="0" width="2100" height="98" fill="{CYA}"/>')
    p.add(iline(0, 98, 2100, 98, 3))
    heads = [("1", "Skriv Forklaring", "Din bildetekst først. Avsløringen er låst."),
             ("2", "Kundens side", "Klimaks i stillhet: 4 til 8, og så ingenting."),
             ("3", "Fire striper", "Samme uker, ett diagram: 1,8× til 7,6×."),
             ("4", "Ditt øyeblikk", "Uke 11: du så, du bestilte, det kostet."),
             ("5", "Quiz", "Feil svar blir forklart, ikke bare merket.")]
    fns = [d1, d2, d3, d4, d5]
    for i, ((n, ttl, note), fn) in enumerate(zip(heads, fns)):
        x = 36 + i * (pw + gap)
        p.add(plain(x, 14, 44, 44, WHITE, 2.4))
        p.add(T(x + 22, 47, n, 28, "d", INK, "middle"))
        p.add(T(x + 54, 42, ttl, 23, "d"))
        p.add(T(x + 54, 72 + 14, note, 19, "hb")) if False else p.add(T(x + 2, 86, note, 18.5, "hb"))
        p.add(phone(x, 118, fn(), s))
        if i < 4:
            p.add(arrow(x + pw + 18, 470, x + pw + gap - 18, 470, 3, INK, bend=-14, head=12))
    # delt skjerm
    sx, sy, sw, sh = 36, 812, 1420, 372
    p.add(rr(sx - 8, sy - 8, sw + 16, sh + 16, 10, INK, INK, 2))
    p.add(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{PAPER}"/>')
    p.add(T(sx + 16, sy + 30, "Delt skjerm: gruppa leser det samme albumet", 24, "d"))
    p.add(wave(sx + 14, sy + 8, sw - 28))
    # notat
    nx = 1490
    p.add(ibox(nx, 812, 574, 372, YEL, None, 3))
    p.add(T(nx + 20, 852, "Slik snakker Debriefen", 26, "d"))
    txt = ("Du skriver før du ser, så du møter din egen forklaring etter avsløringen. "
           "Teksten sier du og viser til ukene dine, men skylder ikke på noen: hver Rolle svarte rimelig på det den så. "
           "Lydordene er borte i kundens rute. Etter 36 uker med DUNK og RRRING er det stillheten som forteller.")
    p.add(Pg(nx + 20, 888, txt, 530, 22, lh=1.24))
    p.add(fig(nx + 62, 1176, "Kunde", 1.1, "rolig"))
    for i, r in enumerate(ROLES):
        p.add(fig(nx + 190 + i * 90, 1176, r, .95 if r != "Distributør" else .8, "rolig"))
    p.add(iline(nx + 8, 1177, nx + 566, 1177, 2.4))
    p.add(T(sx + sw - 92, sy + 30, "Demodata", 17, "hb"))
    p.save()
