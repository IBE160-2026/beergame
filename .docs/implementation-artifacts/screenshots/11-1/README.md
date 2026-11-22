# Visual check: Story 11.1 Spørsmål og vekter (Klasseøkt)

## Close-out check

Local stack lane-2 (port 8081); temporary Playwright spec, deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll at any width.

- klasseokt-hele-siden-draft-<width>: Whole Klasseøkt, draft. Block sits after Replay-scenario, Tidsgrense and KI-vurdering; consistent with the other blocks.
- spoersmaal-draft-<width>: Block alone: 10 questions each with type line, Vekt field and «Ta ut», Adapted line at 30 %, «Sum 100 %.» and «Lagre vekter». Matches spec and copy.
- spoersmaal-blokkert-sum-feil-<width>: A quantity item taken out («Tatt ut» / «Ta med igjen») and «abc» in a weight: red field with «Skriv et helt tall fra 0 til 100.», «Sum 87 %. Vektene må bli 100 %.», quantity warning, «Lagre vekter» greyed. Matches. Note: the invalid field counts as 0 in the sum.
- spoersmaal-laast-<width>: Locked: plain text rows, no fields or buttons. Matches.
- klasseokt-hele-siden-laast-<width>: Whole Klasseøkt, locked. Matches.
- Mockup: No mockup covers this screen (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens and the spec.
