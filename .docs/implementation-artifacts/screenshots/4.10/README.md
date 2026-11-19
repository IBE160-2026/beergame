# Story 4.10 — visual check

«Arkiver Klassen» on a fresh Class `arkiv-visuell-…` owned by the demo Faglærer (faglaerer@example.com), with the demo Assistent joined from its Invitation and two fresh Student addresses sent (one accepted, one left unused). The demo Class was not touched. Live stack; full-page screenshots at 390 and 1280 px. The archive flow is spine-only (no mockup); compared with mockup `02-laerer-klasse.png` and `09-alle-sider.png` for style, DESIGN.md and EXPERIENCE.md. No horizontal scroll at 390 px in any state; at most one primary button in each. Taken after the fix below. Two runs were needed, so the demo Faglærer has two archived test Classes.

| Screenshot | Shows | Matches |
|---|---|---|
| klasse-aktiv-{390,1280}.png | Active Class page as owner; «Arkiver Klassen» as a Lenke last, under a hairline | Yes (after fix) |
| klasse-arkiver-panel-{390,1280}.png | In-place panel: title, consequence above the one primary «Arkiver nå», «Avbryt» | Yes (opener and panel title share the label, see note) |
| klasse-arkivert-eier-{390,1280}.png | Owner after archiving: notice under the facts, staff Lenke kept, Klasseliste count, counts, status bar and list read-only; no buttons in `main` | Yes (row status vs. count, see note) |
| faglaerere-arkivert-eier-{390,1280}.png | Staff page read-only: notice, Faglærer and Assistent listed «Aktiv», no forms, no «Fjern» | Yes |
| laererhjem-arkivert-{390,1280}.png | Lærerhjem: class-of-1994 under «Klassene dine», archived Classes under «Arkiverte Klasser», «Arkivert · N adresser på Klasselista» | Yes |
| klasse-aapen-side-foer-{390,1280}.png | A second owner tab left open with «Legg til én adresse» filled in, after the Class was archived elsewhere | Yes (stale by design) |
| klasse-aapen-side-etter-{390,1280}.png | The same tab after pressing «Legg til»: page read again, read-only, focus on the notice | Yes (refusal line not seen, see note) |
| klasse-arkivert-assistent-{390,1280}.png | Demo Assistent on the archived Class: notice, Assistant lead, read-only Roster, counts and status list | Yes |
| laererhjem-arkivert-assistent-{390,1280}.png | Demo Assistent's Lærerhjem: class-of-1994 and the archived Class under «Arkiverte Klasser»; no «Ny Klasse» | Yes |
| hjem-student-foer-arkivering-{390,1280}.png | Fresh Student's Hjem before: the Class with «Du får Rolle og spill på startdatoen.» | Yes |
| hjem-student-etter-arkivering-{390,1280}.png | The same Hjem after: the Class is gone; only the heading «Hjem» | Partly (empty Hjem, see note) |
| invitasjon-utloept-arkivert-{390,1280}.png | The unused Student link: «Du er invitert», «Lenken er utløpt eller brukt.», secondary «Be om ny Invitasjon» | Yes (renewal offer, see note) |

Fixed before these were taken:
- The hairline above «Arkiver Klassen» ran the full container width (1120 px at 1280), past the right edge of the status list above it (896 px). The section now takes `max-w-4xl`, so the rule ends with the content (`archive-class.tsx`).

Notes needing a judgement:
- The voided Invitation's row reads «Uregistrert, Invitasjonen er utløpt» while the counts show «Utløpt 0» (`klasse-arkivert-eier-*.png`). Voided Invitations show as expired in rows but are not counted; this predates 4.10 but archiving makes it visible on every unused address.
- A Student whose only Class was archived sees a Hjem with the heading alone and no line saying why (`hjem-student-etter-arkivering-*.png`). Story 4.5 chose «only the heading» for a User on no Roster.
- The archived link still offers «Be om ny Invitasjon», which on an archived Class marks nothing (`invitasjon-utloept-arkivert-*.png`). The same state as any expired link, by the spec.
- After a refused action the page shows the notice, not «Klassen er arkivert og kan ikke endres.», because the form that would hold the line closes (`klasse-aapen-side-etter-*.png`). The notice says the same.
- The opener «Arkiver Klassen» and the panel title «Arkiver Klassen» are the same words, both visible (`klasse-arkiver-panel-*.png`), as in 4.9.
