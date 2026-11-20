# Story 5.7: visual check

Faglærer (demo account) on a fresh Class and Klasseøkt made through the API. Compared with mockup 03, DESIGN.md and EXPERIENCE.md. No sideways scroll at 390 px in any state. No fixes needed.

- `klasseokt-obligatorisk-av-390.png` / `-1280.png`: «Obligatorisk» off: Bryter with an outlined track, knob at the left, state text «Nei», no share field. Matches.
- `klasseokt-bryter-fokus-av-390.png` / `-1280.png`: Bryter off with keyboard focus (Tab): the shared ink focus ring around the whole 44 px target, track plus state text. Matches.
- `klasseokt-bryter-fokus-pa-390.png` / `-1280.png`: after Space with focus kept: ink track, paper knob at the right, «Ja, står i emneplanen», help line, «Andel uker som kreves» at 80. Matches.
- `klasseokt-obligatorisk-pa-390.png` / `-1280.png`: on, without focus: as mockup 03's third column (Bryter, label beside it, help line below), plus the share field with its hint. Matches.
- `klasseokt-andel-feil-390.png` / `-1280.png`: share 0 after blur: error-coloured border, hint kept, «Skriv et helt tall fra 1 til 100.» under it. Matches.
- `klasseokt-ventetid-felt-390.png` / `-1280.png`: settings block open: «Ventetid før KI tar over» at 24 after the demand fields, with the help line always visible. Matches.
- `klasseokt-ventetid-feil-390.png` / `-1280.png`: Ventetid 19 after blur: error border and «Skriv et helt antall timer, 20 eller mer.» under the help line. Matches.
- `klasseokt-lagret-390.png` / `-1280.png`: after «Lagre Klasseøkt»: block closed, the row reads «48 t, så KI overtar», the Bryter stays on with 75, «Klasseøkten er lagret.» under the one primary button. Matches.
- `klasseokt-last-390.png` / `-1280.png`: locked (GET rewritten as started, share 70): «Ja, står i emneplanen», the help line and «Andel uker som kreves: 70 %» as text, no Bryter or settings link, as the KI-modus and Debrief-modus read-only columns. Matches.

Notes (no change made):
- The off knob is `ink-secondary`, not the `ink-muted` of the accessibility review (decision recorded in the spec: no colour pair listed for `ink-muted`). Both pass contrast, and the knob's position carries the state.
- The date fields read «mm/dd/yyyy» because headless Chromium renders native date inputs in its UI locale. This comes from Story 5.3 and is outside 5.7.
