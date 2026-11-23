# Visual check: Story 12.1 KI-vurdering switch

## Close-out check

Local stack lane-2 (port 8081); temporary Playwright spec, deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll at any width.

- ki-vurdering-paa-<width>: On by default: switch with «På» and help text. Matches.
- ki-vurdering-av-<width>: Switched off: «Av», choice and interactive items still auto-scored. Matches.
- klasseokt-hele-siden-ai-av-<width>: Whole Klasseøkt with it off.
- ki-vurdering-festet-<width>: Pinned after the Testfrist lock: «Låst ved testfristen sø. 22. nov. kl. 20:02.», no switch. Matches.
- Mockup: No mockup covers this screen (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens and the spec.

## Epic 12 visual check, lane-3 (added)

Local stack lane-3 (port 8082); temporary Playwright spec (zz-visual-epic12), deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll and no tap target under 44 px in main at 390 in any shot. Stand-in = api answer stood in with the shape of the e2e specs; live = real data on the stack (mock AI). Defect ids refer to visual-epic12-findings.md.

- klasseokt-ki-blokk-foer-lock-<w>: Live Klasseøkt: KI-vurdering switch «På», «Kan endres fram til testfristen», then Veiledende bokstav and the student list under it. Verdict: OK (D5: student list sits under the letter block).
- klasseokt-hele-siden-foer-lock-<w>: Whole Klasseøkt of the live game, before the lock. Verdict: OK.
- klasseokt-ki-blokk-paa-<w>: Fresh Klasseøkt: KI-vurdering switch on, empty student list. Verdict: OK (D5, D15).
