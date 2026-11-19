# Story 4.9 — visual check

«Faglærere og assistenter» on the demo Class `class-of-1994` (owner faglaerer@example.com), on the live stack, with a fresh co-owner and fresh `…@example.com` addresses per width; everything added was removed or withdrawn again, so the Class ends with its demo owner and demo Assistant. The staff page is spine-only (no mockup); compared with mockup `02-laerer-klasse.png` for style, DESIGN.md and EXPERIENCE.md (UX-DR56, State Patterns → Permission denied). No horizontal scroll at 390 px in any state; at most one primary button in each. Taken after the fix below.

| Screenshot | Shows | Matches |
|---|---|---|
| faglaerere-list-{390,1280}.png | Owner and co-owner under «Faglærere», the demo Assistant under «Assistenter», each «Aktiv» in text, «Fjern» per row; scope sentence under «Assistenter» | Yes |
| faglaerere-add-empty-{390,1280}.png | «Legg til en Faglærer» in place: lead, E-post, primary «Legg til Faglærer», «Avbryt» | Yes (opener and submit share the label, see note) |
| faglaerere-add-not-lecturer-{390,1280}.png | Unknown address refused beside the field: «Adressen tilhører ingen Faglærer. Be Admin gi personen Faglærer-rollen.» | Yes |
| faglaerere-add-success-{390,1280}.png | Result line «… er Faglærer i Klassen.»; two Faglærere listed | Yes |
| faglaerere-invite-empty-{390,1280}.png | «Inviter en Assistent» in place, scope sentence as lead, primary «Send Invitasjon» | Yes (scope sentence shown twice, see note) |
| faglaerere-invite-sent-{390,1280}.png | «Invitasjonen er sendt til …»; pending row «Invitert, gyldig til og med 3. desember» | Yes |
| faglaerere-remove-lecturer-{390,1280}.png | «Fjern» on the co-owner: «… mister tilgangen til Klassen fra neste side de åpner. Kontoen beholdes.» above «Fjern fra Klassen» | Yes |
| faglaerere-removed-{390,1280}.png | «… er fjernet fra Klassen.»; one Faglærer left | Yes |
| faglaerere-withdraw-invitation-{390,1280}.png | «Fjern» on the pending row: «Invitasjonen til … slutter å virke.» above «Trekk tilbake Invitasjonen» | Yes (panel title says «Fjern … fra Klassen» for someone not yet in it, see note) |
| faglaerere-last-owner-{390,1280}.png | «Fjern» on the only Faglærer: «Klassen må ha minst én Faglærer. Legg til en annen Faglærer først.» with «Avbryt» only | Yes (after fix) |
| laererhjem-assistent-{390,1280}.png | Demo Assistent's Lærerhjem: only class-of-1994, no «Ny Klasse» | Yes |
| klasse-assistent-{390,1280}.png | Class page read-only: Assistant lead, Klasseliste count, Invitasjoner counts, status bar and list; no buttons in `main`, no staff Lenke | Yes |
| faglaerere-assistent-nektet-{390,1280}.png | Assistent on the staff page: «Du har ikke tilgang til denne siden.» and «Til Lærerhjem» | Yes |
| invitasjon-assistent-{390,1280}.png | «Du er invitert» from the Assistant link: «Faglærer Demo Faglærer har invitert deg som Assistent i class-of-1994, IBE160. Du får tilgang bare til denne Klassen.», one primary | Yes |

`assistent-invitasjon-mail.txt`: the `invitation` mail, `assistant` branch (Class named, scope sentence, single-use link, valid to 3. desember 2026).

Fixed before these were taken:
- «Fjern» on the only Faglærer said «Du mister tilgangen til Klassen. De andre Faglærerne beholder den.» (false, there are none) above a primary button that could only be refused. The panel now shows the last-owner reason in place of the consequence, with «Avbryt» only (`staff-page.tsx`; e2e in `class-staff.spec.ts`).

Notes needing a judgement:
- The opener «Legg til Faglærer» and the form's submit have the same label, both visible at once (`faglaerere-add-empty-*.png`).
- «Assistenten får tilgang bare til denne Klassen.» appears twice when the invite form is open, as section lead and form lead (`faglaerere-invite-empty-*.png`).
- The withdraw panel's title «Fjern … fra Klassen» names an address that is only invited (`faglaerere-withdraw-invitation-*.png`).
- At 390 px each row stacks name, status and «Fjern» on three lines, so the lists grow tall (`faglaerere-list-390.png`).
- The result line sits at the top of the page, above «Faglærere», away from the action in «Assistenter» (`faglaerere-invite-sent-390.png`); focus moves to it.
