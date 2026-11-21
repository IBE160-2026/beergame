# Visual check Stories 8.1-8.2 at 159838f (full-page, nb-NO)
Widths: 390, 1280, 200 (1280 px with root font 200 %). Takeover screens use the stubs of takeover.spec.ts; Spillinnsikt is a real stack game (2 Students, 2 rule-based players).

- spillinnsikt-uker-1280.png: Uke for uke tables with Uke åpnet, Bestilt, Tid brukt; fits, Norwegian Oslo times, empty Bestilt/Tid brukt for the open Uke. Matches.
- spillinnsikt-uker-390.png: per-Role tables scroll inside their own group; Uke åpnet/Bestilt/Tid brukt are off-screen (only up to Lager + clipped Restordre visible). No page scroll. Judgement.
- spillinnsikt-uker-200.png: same, columns cut at Kost, with the faded scroll edge. No page scroll. Judgement.
- spill-gruppe-takeover-{390,1280,200}.png: Setestatus row «Distributør KI-spiller bestiller for Jonas Berg»; own Ordrefelt intact. Matches.
- spill-egen-takeover-obligatorisk-{390,1280,200}.png: «KI-spiller har bestilt for deg.» + requirement warning (no digits) in place of Ordrefelt; row «KI-spiller bestiller for deg». Matches copy; see report for layout notes.
- spill-egen-takeover-uten-krav-{390,1280,200}.png: same, only the one line. Matches.
- hjem-takeover-{390,1280,200}.png: line + warning, no Spillkort, no primary button; row «bestiller for deg». Matches.
