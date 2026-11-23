# Visual check: Story 11.13 Frister on the Studentside

## Close-out check

Local stack lane-2 (port 8081); temporary Playwright spec, deleted afterwards. Widths: 390, 1280, 1280-text200 (html font-size 200 %); file name = name-width.png. No horizontal page scroll at any width.

- studentside-hele-siden-<width>: Studentside: Tilrettelegging and Frister blocks. Matches.
- frister-blokk-<width>: Frister: Testfrist, Debrieffrist, «Som klassen.», «Forleng testfrist». Matches.
- frister-skjema-aapent-<width>: Form open: date field «Ny testfrist», hint, scope line, «Lagre frist», «Avbryt». Matches.
- frister-skjema-feil-<width>: Date not later than the class's: red field; hint and error both give the class date (redundant, minor).
- frister-lagret-<width>: Saved: «Lagret. Ny testfrist for ...», new dates, «Forlenget. Klassens testfrist: ...». Matches.
- studentside-etter-forlengelse-<width>: Whole Studentside after the extension. Matches.
- student-egen-testfrist-egen-arbeid-<width>: The extended Student's statement shows their own Testfrist (ma. 21. des.). Matches.
- Mockup: No mockup covers this screen (mockups 01-10 are landing, Lag Klasse, spill, debrief, overview); judged against DESIGN.md tokens and the spec.
