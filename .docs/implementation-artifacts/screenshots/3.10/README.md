# Story 3.10 — visual check

Taken after the fixes in «Story 3.10: visuelle rettinger». The Invitation list is filtered to the test addresses, or faked (`statuser`, `avvist-*` without `-ekte`) with Playwright routing. Compared with DESIGN.md, EXPERIENCE.md, nb.ts and mockup 09-alle-sider. No sideways scroll at any width; the only primary button is «Send Invitasjon».

- `brukere-aktiv-deaktiver-390.png` — active User block with the full-width «Deaktiver Kari. …» button under the role buttons. Matches.
- `brukere-aktiv-deaktiver-1280.png` — the same row in the table; name and e-mail on one line, buttons wrap in «Endre». Matches (after the fix).
- `brukere-deaktivert-reaktiver-390.png` — status «Deaktivert» (secondary ink), «Aktiver Kari igjen», line «Kari er deaktivert.». Matches.
- `brukere-deaktivert-reaktiver-1280.png` — the same in the table. Matches.
- `brukere-reaktivert-390.png` — after reactivating: «Kari er aktiv igjen.», «Deaktiver …» back. Matches.
- `brukere-reaktivert-1280.png` — the same in the table. Matches.
- `brukere-selv-avvist-390.png` — own row, refusal «Du kan ikke deaktivere deg selv.» in restordre (409 faked). Matches.
- `brukere-selv-avvist-1280.png` — the same; the Admin's three buttons stack in the capped cell. Matches.
- `logg-inn-deaktivert-390.png` — the deactivated User logs in: «Kontoen er deaktivert. Ta kontakt med faglæreren din.». Matches the copy; for a Lecturer the text says «faglæreren din», which needs a judgement.
- `logg-inn-deaktivert-1280.png` — the same at 1280. As above.
- `laererhjem-okt-avsluttet-deaktivert-390.png` — the deactivated User's open page after a reload: «Logg inn» with «Du er logget ut. Logg inn igjen for å fortsette.». Matches (existing session-expired state).
- `laererhjem-okt-avsluttet-deaktivert-1280.png` — the same at 1280. Matches.
- `invitasjoner-statuser-390.png` — Åpen, Utløpt with «Mottakeren har bedt om en ny invitasjon.», Utløpt, Akseptert (no button), «Vis flere invitasjoner». Matches.
- `invitasjoner-statuser-1280.png` — the same as a table. Matches; the resend buttons have ragged widths and the first one wraps (judgement).
- `invitasjoner-sendt-paa-nytt-390.png` — real resend: «Ny invitasjon sendt til … Den er gyldig i 14 dager.». Matches.
- `invitasjoner-sendt-paa-nytt-1280.png` — the same in the table. Matches.
- `invitasjoner-avvist-erstattet-390.png` — resend of a replaced Invitation (409 `invitation_superseded` faked): the general line «Invitasjonen ble ikke sendt på nytt. Prøv igjen.». Matches the spec. Replaced Invitations are never listed (one row per address and role).
- `invitasjoner-avvist-erstattet-1280.png` — the same at 1280. As above.
- `invitasjoner-avvist-deaktivert-390.png` — 409 `account_deactivated` faked: «Kontoen med denne adressen er deaktivert. Aktiver den før du sender på nytt.». Matches.
- `invitasjoner-avvist-deaktivert-1280.png` — the same at 1280. Matches.
- `invitasjoner-foer-deaktivering-390.png` — real: an open Admin Invitation to a fresh Lecturer, before deactivation. Matches.
- `invitasjoner-foer-deaktivering-1280.png` — the same at 1280. Matches.
- `invitasjoner-utlopt-etter-deaktivering-390.png` — real: after the deactivation the same Invitation reads «Utløpt», expiry today (18. nov. 2026). Matches; the row still offers a resend that is always refused (judgement).
- `invitasjoner-utlopt-etter-deaktivering-1280.png` — the same at 1280. As above.
- `invitasjoner-avvist-deaktivert-ekte-390.png` — real refusal of that resend with the deactivated-account line. Matches.
- `invitasjoner-avvist-deaktivert-ekte-1280.png` — the same at 1280. Matches.
