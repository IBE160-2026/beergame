# Visual check: Epic 12 Story 12.9 screens

## Close-out check

Local stack lane-3 (port 8082); temporary Playwright spec (zz-visual-epic12), deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll and no tap target under 44 px in main at 390 in any shot. Stand-in = api answer stood in with the shape of the e2e specs; live = real data on the stack (mock AI). Defect ids refer to visual-epic12-findings.md.

- admin-sensorer-ekte-tom-<w>: Real Sensorer page for a fresh Kontrolltest after a Testfrist was set: 0 answers, no scorers, add form. Verdict: OK (before the Testfrist is set the real page is a 500, D1).
- admin-sensorer-tom-<w>: Sensorer, empty (stand-in with 12 answers). Verdict: OK.
- admin-sensorer-teststudent-feil-<w>: Naming a test student is refused in words. Verdict: OK.
- admin-sensorer-navngitt-<w>: Two named scorers, one with a long name and address. Verdict: OK.
- hjem-sensur-lenke-<w>: Hjem of a named scorer: «Sensur av Kontrolltest». Verdict: D14.
- sensur-oversikt-<w>: /sensur: tests to score. Verdict: OK.
- sensur-oversikt-tom-<w>: /sensur with nothing to score. Verdict: OK.
- sensur-liste-<w>: /sensur/<test>: «Svar N», type, question, Vurdert / Ikke vurdert in text, progress. Verdict: D7.
- sensur-svar-uvurdert-<w>: One answer: question, answer, guide, scale, five Valgknapper, consequence line, «Lagre vurdering». Verdict: D3.
- sensur-svar-valgt-trinn-<w>: Step 3 chosen. Verdict: D3.
- sensur-svar-vurdert-<w>: Saved: own score and the AI's step. Verdict: D16.
- sensur-svar-avvist-allerede-vurdert-<w>: Second save refused in words, page re-read. Verdict: OK.
- Mockup: No mockup covers these screens (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens, EXPERIENCE.md and the spec.
