# Visual check: Epic 12 Story 12.2 screens

## Close-out check

Local stack lane-3 (port 8082); temporary Playwright spec (zz-visual-epic12), deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll and no tap target under 44 px in main at 390 in any shot. Stand-in = api answer stood in with the shape of the e2e specs; live = real data on the stack (mock AI). Defect ids refer to visual-epic12-findings.md.

- student-ikke-klar-<w>: Student KI-vurdering, not ready (stand-in): disclosure, «kommer innen ett døgn etter testfristen». Verdict: OK.
- student-slaatt-av-<w>: Switched off (stand-in): Faglærer's line. Verdict: OK.
- student-feilet-<w>: Failed (stand-in): computed points are in the Studentrapport. Verdict: OK.
- student-klar-uten-tilbakemelding-<w>: Ready, no feedback (stand-in): four items, points in words, weighted total. Verdict: OK (D8: points wrap under heading for long item types).
- student-ufullstendig-<w>: Incomplete (stand-in): item 4 not assessed, no total. Verdict: D9 (Ikke vurdert ennå shown twice).
- student-annen-students-okt-403-<w>: Another student's session: permission-denied page. Verdict: OK.
- student-live-ikke-klar-<w>: Live: handed-in test before the Testfrist, not ready. Verdict: OK.
- student-live-klar-<w>: Live: ready with real mock assessment, 12 items, one piece of feedback, letter switch off. Verdict: OK (D8, D12).
- Mockup: No mockup covers these screens (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens, EXPERIENCE.md and the spec.
