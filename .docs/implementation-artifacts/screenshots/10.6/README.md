Shots for Story 10.6 (b211c33). Widths: 390, 1280, 200 (1280 px wide with html font-size 200 %). No page side scroll in any shot.

- play-nothing-{390,1280}.png: running Replay, nothing typed; dashed line to nå+4, labels Posisjon/Restordre above the line, sum on one line. Matches.
- play-order24-{390,1280}.png: Order 24; dashed line flat at -20, Restordre label above it, dot clear. Matches.
- play-order80-{390,1280}.png: Order 80; line rises, labels sit below the line, sum "-4 + 80 - 4 x 10 = 36" on one line. Matches.
- play-{nothing,order24,order80}-200.png: two-column layout; chart column narrow, chart title, legend and the in-graph labels (Posisjon, Restordre) are cut off. Deviates.
- play-refused-{390,1280,200}.png: Order refused before the sweep; bold line "Testfristen er ute. Ordren på 24 ble ikke sendt." Matches copy; the primary "Bekreft ordre på 24" stays live. Judgement.
- replay-closed-{390,1280,200}.png: "Replay stengt", lead and kept lines, only "Til Hjem" link, no primary, no Totalkostnad. Matches.
- hjem-closed-{390,1280,200}.png: Hjem Replay block with the closed line, no "Se Replay"; Stegene "stengt ved Testfristen, ikke fullført". Matches; seat list still reads "har bestilt/venter" (judgement).
- insight-closed-{390,1280,200}.png: staff Spillinnsikt, status "Stengt ved Testfristen, ikke fullført" in the header (stubbed insight). Matches; per-Role tables scroll in their own regions at 390.

## After the Epic 10 close-out fixes (lane 2, port 8081)
- play-order80-after-{390,1280,200}.png: the play screen picks its columns by the content's width in rem (container query). At 200 % text it is one column: chain band, chart title «Lager over null, restordre under», cost legend and the in-graph «Posisjon −4» / «Restordre 20» are whole; the Ordrefelt follows the table. 390 and 1280 as before. Matches.
- After a Testfrist refusal the Ordrefelt is read-only and «Bekreft ordre på …» unavailable (unit test in order-field.test.tsx; not shot).
