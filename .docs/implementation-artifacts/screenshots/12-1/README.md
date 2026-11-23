# Visual check: Story 12.1 KI-vurdering switch

## Close-out check

Local stack lane-2 (port 8081); temporary Playwright spec, deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll at any width.

- ki-vurdering-paa-<width>: On by default: switch with «På» and help text. Matches.
- ki-vurdering-av-<width>: Switched off: «Av», choice and interactive items still auto-scored. Matches.
- klasseokt-hele-siden-ai-av-<width>: Whole Klasseøkt with it off.
- ki-vurdering-festet-<width>: Pinned after the Testfrist lock: «Låst ved testfristen sø. 22. nov. kl. 20:02.», no switch. Matches.
- Mockup: No mockup covers this screen (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens and the spec.
