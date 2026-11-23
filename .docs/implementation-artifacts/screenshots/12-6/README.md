# Visual check: Epic 12 Story 12.6 screens

## Close-out check

Local stack lane-3 (port 8082); temporary Playwright spec (zz-visual-epic12), deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll and no tap target under 44 px in main at 390 in any shot. Stand-in = api answer stood in with the shape of the e2e specs; live = real data on the stack (mock AI). Defect ids refer to visual-epic12-findings.md.

- bokstav-blokk-standard-<w>: Fresh Klasseøkt: Veiledende bokstav, three Valgknapper, five bounds. Verdict: D15 (3 options wrap 2+1 at 390).
- bokstav-blokk-grenser-feil-<w>: B = 95 above A: «Grensene må synke fra A til E.». Verdict: D4 (no field marked red).
- bokstav-blokk-alle-<w>: «Vist for alle» chosen. Verdict: OK.
- bokstav-blokk-ikke-tilgjengelig-<w>: «Ikke tilgjengelig» chosen. Verdict: OK.
- bokstav-blokk-institusjonen-forbyr-<w>: Institution ban (stand-in): only «Ikke tilgjengelig», reason, bounds as text. Verdict: OK.
- klasseokt-hele-siden-ny-<w>: Whole fresh Klasseøkt. Verdict: OK.
- klasseokt-bokstav-blokk-etter-lock-<w>: Live Klasseøkt letter block after the Test lock. Verdict: OK.
- student-bokstav-av-sum-<w>: Student total with «Veiledende bokstav» switch off («Skjult») (stand-in). Verdict: OK.
- student-bokstav-av-hele-siden-<w>: Same, whole page. Verdict: OK.
- student-bokstav-paa-sum-<w>: Switch on: «Veiledende bokstav: C» with the KI label. Verdict: D10.
- student-bokstav-paa-hele-siden-<w>: Same, whole page. Verdict: D10.
- student-bokstav-vist-alle-sum-<w>: Letter shown to everyone, no switch (stand-in). Verdict: OK.
- student-bokstav-vist-alle-hele-siden-<w>: Same, whole page. Verdict: OK.
- student-live-bokstav-paa-hele-siden-<w>: Live: letter switched on on the real ready page. Verdict: D10.
- staff-studentside-bokstav-blokk-<w>: Staff Studentside with a letter shown to everyone (stand-in). Verdict: OK.
- admin-institusjoner-bokstav-av-<w>: Admin «Alle Institusjoner»: «Veiledende bokstav» switch (Faglærer velger), fresh Institution. Verdict: D13.
- admin-institusjoner-bokstav-paa-<w>: Switch on «Sperret» with the saved note. Verdict: D13.
- admin-institusjoner-hele-siden-<w>: Whole Institusjoner page. Verdict: D13.
- Mockup: No mockup covers these screens (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens, EXPERIENCE.md and the spec.
