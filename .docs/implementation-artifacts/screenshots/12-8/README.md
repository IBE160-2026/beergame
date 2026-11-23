# Visual check: Epic 12 Story 12.8 screens

## Close-out check

Local stack lane-3 (port 8082); temporary Playwright spec (zz-visual-epic12), deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll and no tap target under 44 px in main at 390 in any shot. Stand-in = api answer stood in with the shape of the e2e specs; live = real data on the stack (mock AI). Defect ids refer to visual-epic12-findings.md.

- klasseliste-teststudent-venter-<w>: Klasseliste: «Teststudent · Ikke svart ennå». Verdict: OK.
- klasseokt-fordeling-samtykke-mangler-<w>: Fordeling: «1 teststudent har ikke samtykket ennå». Verdict: OK.
- hjem-samtykke-foer-svar-<w>: Test student's Hjem: consent block, purpose, data controller, «Jeg samtykker» / «Nei takk». Verdict: OK.
- hjem-samtykke-blokk-<w>: The consent block alone. Verdict: OK.
- hjem-samtykke-avslatt-<w>: After «Nei takk»: «Jeg samtykker likevel». Verdict: OK.
- hjem-samtykke-gitt-<w>: After consent: one line with the day, block gone. Verdict: OK.
- klasseliste-teststudent-samtykket-<w>: Klasseliste: «Teststudent · Samtykket». Verdict: OK.
- Mockup: No mockup covers these screens (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens, EXPERIENCE.md and the spec.
