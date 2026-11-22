# Visual check: Story 11.12 timed sitting

## Close-out check

Local stack lane-2 (port 8081); temporary Playwright spec, deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll at any width.

- tidsgrense-av-<width>: Klasseøkt block, off: toggle and help text. Matches.
- tidsgrense-paa-<width>: On: minutes field (90) and range. Matches.
- tidsgrense-feil-<width>: 500 minutes: red field; the range line and the error line both say 15 to 240 (redundant, minor).
- tidsgrense-laast-<width>: Locked: «Én økt med tidsgrense: 75 minutter.» and «Låst fra startdatoen.». Matches.
- student-egen-arbeid-med-tidsgrense-<width>: Statement with «Testen har en tidsgrense på 90 minutter. ... kan ikke stoppes.» before the button. Matches.
- student-tid-igjen-38-<width>: Sticky «Tid igjen 38 min» at the top. Matches.
- student-fem-minutter-<width>: «Tid igjen 5 min»; the line «5 minutter igjen. Svarene dine er lagret.» is sr-only and not visible to sighted users (spec says polite; possibly intended).
- student-tiden-er-ute-<width>: «Tiden er ute. Testen er levert.» and read-only answers. Matches.
- student-autolevert-ved-tidsslutt-<width>: Handed in by the sweep at the sitting's end: same line. Matches.
- Mockup: No mockup covers this screen (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens and the spec.
