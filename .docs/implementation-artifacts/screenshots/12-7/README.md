# Visual check: Epic 12 Story 12.7 screens

## Close-out check

Local stack lane-3 (port 8082); temporary Playwright spec (zz-visual-epic12), deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll and no tap target under 44 px in main at 390 in any shot. Stand-in = api answer stood in with the shape of the e2e specs; live = real data on the stack (mock AI). Defect ids refer to visual-epic12-findings.md.

- kontrolltest-ingen-operator-<w>: Kontrolltest with no operator Institution: what to do first, link to Institusjoner (stand-in). Verdict: OK.
- institusjoner-operatormerke-liste-<w>: Institution list with the operator mark. Verdict: D13.
- admin-forside-med-kontrolltest-lenke-<w>: Admin-område with the Kontrolltest link. Verdict: OK.
- kontrolltest-oppsett-tom-<w>: Create form, empty list. Verdict: D2.
- kontrolltest-oppsett-tomt-navn-feil-<w>: Empty name: «Skriv navnet på Klassen.» with red field. Verdict: D2.
- kontrolltest-oppsett-opprettet-<w>: Created: status line and list entry with pinned guide and model config. Verdict: D2, D1 (the Sensorer/Resultater links lead to a 500 until dates are set).
- kontrolltest-liste-element-<w>: The list entry alone. Verdict: OK.
- kontrolltest-klasse-side-<w>: The Control test's Class page. Verdict: D7 (breadcrumb).
- kontrolltest-klasseokt-side-<w>: The Control test's Klasseøkt. Verdict: OK.
- Mockup: No mockup covers these screens (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens, EXPERIENCE.md and the spec.
