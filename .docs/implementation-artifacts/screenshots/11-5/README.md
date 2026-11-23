# Visual check: Story 11.5 table and number items

## Close-out check

Local stack lane-2 (port 8081); temporary Playwright spec, deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll at any width.

- student-tabell-ubesvart-<width>: Fill-the-column table, rows as Uke, «Ikke besvart» under each empty row. Matches.
- student-tabell-delvis-<width>: Two cells answered (12, 30), rest «Ikke besvart». Matches.
- student-tall-ubesvart-<width>: Number item (column of Legg til). Matches.
- student-tall-besvart-<width>: Number item answered 16. Matches.
- student-startoppgave-ubesvart-<width>: Starting-task number item with the formula hint. Matches.
- Mockup: No mockup covers this screen (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens and the spec.
