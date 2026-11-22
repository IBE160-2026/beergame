# Visual check Story 8.9 (ffc06e1). Widths: 390, 1280, 1280t200 (200 % text). No page scroll sideways in any shot.
- studentside-none-{w}.png: Lecturer Studentside, «Tilrettelegging», «Ingen tilrettelegging.», one secondary button. Matches.
- studentside-form-{w}.png: open form, «Mer tid før KI tar over» (Som klassen, 1,5 ×, 2 ×, 3 ×), «Andel uker som kreves», «Klassen: 80 %.», scope line, one primary «Lagre tilrettelegging», «Avbryt». Matches nb.ts. No visible focus ring on «Som klassen» after open (judgement).
- studentside-error-{w}.png: 81 refused, red field, «Skriv et helt tall fra 0 til 80.». Matches.
- studentside-saved-{w}.png: «Lagret. Gjelder fra nå.» + «Mer tid: 2 ×. Andel uker: 60 %.». Matches.
- spillstyring-extra-time-{w}.png: Spillinnsikt/Spillstyring with «<name> har tilrettelegging med mer tid.» on the Seat. Matches. (390: tables in «Uke for uke» scroll inside own box, not Story 8.9.)
- hjem-own-{w}.png: Student's two lines under Stegene. Matches. hjem-other-{w}.png: nothing about Tilrettelegging.
- spill-own-{w}.png, spill-other-{w}.png (1280, 390): no Tilrettelegging text for either.
- studentside-assistant-refused-{w}.png: «Du har ikke tilgang til denne siden.» + «Til Lærerhjem»; api 403. spillinnsikt-assistant-390.png. Assistant was the demo Assistant (not staff of the new Class), same 403 as an Assistant of it per spec.
