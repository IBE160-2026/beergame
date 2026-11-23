# Visual check: Epic 12 Story 12.5 screens

## Close-out check

Local stack lane-3 (port 8082); temporary Playwright spec (zz-visual-epic12), deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll and no tap target under 44 px in main at 390 in any shot. Stand-in = api answer stood in with the shape of the e2e specs; live = real data on the stack (mock AI). Defect ids refer to visual-epic12-findings.md.

- student-feilmarkering-av-element-<w>: Item with «Marker som feil» (stand-in). Verdict: D12.
- student-feilmarkering-markert-element-<w>: After the press: «Markert. Faglærer ser det.» and «Angre». Verdict: D12.
- student-feilmarkert-hele-siden-<w>: Whole page with the flagged piece. Verdict: OK.
- student-feilmarkering-feilet-element-<w>: Failed request: «Det ble ikke lagret. Prøv igjen.» in restordre beside the active button. Verdict: OK.
- student-live-markert-element-<w>: Live: flagged item. Verdict: D12.
- staff-studentside-med-flagg-blokk-<w>: Staff Studentside KI-vurdering block, flag count and flag on the item (stand-in, Assistant lecturer). Verdict: OK.
- staff-studentside-med-flagg-hele-siden-<w>: Same, whole page. Verdict: OK.
- staff-studentside-ikke-klar-blokk-<w>: Staff block when the assessment is not ready (stand-in). Verdict: OK.
- staff-studentside-live-blokk-<w>: Live staff block with real assessment and flag. Verdict: OK.
- staff-studentside-live-hele-siden-<w>: Live staff Studentside, whole page. Verdict: OK.
- klasseokt-ki-blokk-med-liste-<w>: Live Klasseøkt: KI-vurdering, letter block and «Studentenes KI-vurderinger» with state and flag count. Verdict: D5.
- klasseokt-studentliste-<w>: The student list alone (Klar · 1 markert som feil; Klar · Ingen markert som feil). Verdict: OK.
- klasseokt-hele-siden-etter-lock-<w>: Live Klasseøkt after the Testfrist lock, whole page. Verdict: D5.
- Mockup: No mockup covers these screens (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens, EXPERIENCE.md and the spec.
