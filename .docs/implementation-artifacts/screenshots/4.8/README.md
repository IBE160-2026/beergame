# Story 4.8 — visual check

The Class page `class-of-1994` (faglaerer@example.com) on the live stack, with fresh `…@example.com` addresses per width (the demo Students are untouched; the status list is searched to the address in play). Compared with mockup `02-laerer-klasse.png`, DESIGN.md and EXPERIENCE.md. Taken after the fixes (one form on the page; wider row-action column). No horizontal scroll at 390 px in any state; at most one primary button in each.

| Screenshot | Shows | Matches |
|---|---|---|
| klasse-add-empty-{390,1280}.png | «Legg til adresse» open under «Klasseliste»: title, lead, E-post, primary «Legg til», «Avbryt» | Yes |
| klasse-add-invalid-{390,1280}.png | `sen-…@stud` refused beside the field: «Domene mangler», field in `restordre` | Yes |
| klasse-add-added-{390,1280}.png | Result line «… er lagt til. Ikke invitert ennå.»; the row reads «Ikke invitert ennå», Uregistrert and «Send påminnelse til N» count it | Yes (row link reads «Send ny Invitasjon», see note) |
| klasse-manual-empty-{390,1280}.png | «Registrer manuelt» under «Klasseliste»: E-post, Navn with hint, primary «Registrer studenten» | Yes |
| klasse-manual-error-name-{390,1280}.png | Empty submit: «Skriv navnet til studenten.» beside Navn | Yes |
| klasse-manual-error-email-{390,1280}.png | `kari@` refused by the api: «Domene mangler» beside E-post | Yes |
| klasse-manual-success-{390,1280}.png | «… er registrert manuelt og får en e-post.»; row «Registrert manuelt», «Manuelt» total up | Yes |
| nytt-passord-manual-link-{390,1280}.png | «Nytt passord» from the mail's link, address named, one primary «Lagre passord» | Yes (lead says «nytt» for a first password, see note) |
| klasse-row-manual-open-{390,1280}.png | A not-invited row's «Registrer manuelt» opens under the row, address prefilled, focus on E-post; actions on one line at 1280 | Yes |
| klasse-row-corrected-{390,1280}.png | Address changed in that form: the corrected address «Registrert manuelt», the wrong one gone | Yes |
| klasse-row-remove-not-invited-{390,1280}.png | «Fjern» on a not-invited row: «… har ikke fått noen Invitasjon og får ingen påminnelser.» above «Fjern fra Klasselista» | Yes |
| klasse-row-remove-registered-{390,1280}.png | «Fjern» on a registered row: «… mister tilgangen til Klassen. Kontoen og andre Klasser beholdes.» above the button | Yes |
| klasse-row-removed-{390,1280}.png | «… er fjernet fra Klasselista.»; the search finds no row | Yes |
| klasse-invalid-row-manual-{390,1280}.png | Pasted invalid row «Domene mangler» with its «Registrer manuelt» form open in place, prefilled; «Send 0 Invitasjoner» unavailable | Yes (mockup 02 shows an inline edit field in the row; the in-place form is Story 4.3/4.8's decision) |

`manuell-registrering-mail.txt`: the `manual_registration` mail (subject «Du er registrert i ØL-spillet», names the Class, single-use link valid 14 days).

Fixed before these were taken:
- A form under «Klasseliste» (including an invalid row's) and a form in the status list could be open at once; opening one now closes the others and clears their result lines (`one-form.tsx`, e2e in `roster-entries.spec.ts`).
- At 1280 px a not-registered row's three actions wrapped «Fjern» onto a second line; the action column is now 21rem.

Notes needing a judgement:
- A `not_invited` row offers «Send ny Invitasjon» (and the confirmation says «Send ny Invitasjon til …») although no Invitation has gone out yet (`klasse-add-added-*.png`, `klasse-row-manual-open-1280.png`).
- «Nytt passord» says «Velg et nytt passord for …» when a manually registered Student chooses their first one (`nytt-passord-manual-link-390.png`).
- The demo Class holds leftover addresses from earlier e2e/visual runs (39 entries), as noted in 4.7.
