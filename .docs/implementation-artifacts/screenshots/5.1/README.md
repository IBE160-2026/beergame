# Story 5.1: screenshots

Taken after commit 3623044 (visual fixes), as the demo Faglærer, on a fresh Class. Compared with mockups `02-laerer-klasse.png` and `03-laerer-spill.png`, `DESIGN.md` and `EXPERIENCE.md`. No page scrolls sideways at 390 px; every Klasseøkt state has exactly one primary button («Lagre Klasseøkt»), and the Klasse page has none.

- `klasse-tom-390.png`: Klasse page, «Klasseøkter» with «Ingen Klasseøkter ennå.» and the secondary «Lag Klasseøkt». Matches.
- `klasse-tom-1280.png`: the same at laptop width. Matches.
- `klasse-liste-390.png`: two sessions, one «Ikke lagret ennå», one «Lagret», each status under its link. Matches after the fix (the status used to wrap only on the longer row). Open: two sessions made in the same minute have identical labels.
- `klasse-liste-1280.png`: the same, status right-aligned on each row. Matches; same open point on identical labels.
- `klasseokt-ny-390.png`: new unsaved session with Classic defaults, one column, save button under the choices with the hint below. Matches. Open: the chain diagram scrolls inside its own region, so Detaljist and «Kundene» sit off-screen with no visible scroll cue.
- `klasseokt-ny-1280.png`: same at laptop width: settings list, delay-sources line, «Kjeden ved start» at 13 px labels, choices row, «Du kan lagre uten å endre noe.» beside the primary button. Matches mockup 03, except that the right column (Datoer, Fordeling) is empty by design until Stories 5.2/5.8, the choices are text not Valgknapper/Bryter until 5.5/5.7, and «Kundene» lacks the demand line «4, så 8 fra Uke 5» drawn in the mockup.
- `klasseokt-feil-390.png`: save failed (network aborted): «Det ble ikke lagret. Prøv igjen.» in red under the button, values kept. Matches.
- `klasseokt-feil-1280.png`: the same, right-aligned under the button. Matches.
- `klasseokt-llm-avvist-390.png`: save refused with 409 `llm_unavailable` (mocked): the refusal line under the button. Matches.
- `klasseokt-llm-avvist-1280.png`: the same at laptop width. Matches.
- `klasseokt-uten-modell-390.png`: session created with no default model (GET mocked with `llm_unavailable: no_default_model`): KI-modus «Regelbaserte spillere» with the explanation line. Matches.
- `klasseokt-uten-modell-1280.png`: the same at laptop width. Matches.
- `klasseokt-lagret-390.png`: after a successful save, «Klasseøkten er lagret.» under the button. Matches.
- `klasseokt-lagret-1280.png`: the same, right-aligned. Matches.

Fixed in 3623044: the diagram's labels were 10–11 px (under DESIGN.md's 13 px floor, Typography → Floors) and are now 13 px; the phone list rows now stack consistently.
