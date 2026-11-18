# Story 3.7 — visuell kontroll

Tatt 2026-11-18 på compose-stakken (`http://127.0.0.1:8080`) med `worker-batch`, Chromium, full side, 390 og 1280 px, etter rettingen i «Story 3.7: visuelle rettinger». Mønster: `<skjerm>-<tilstand>-<bredde>.png`. Sendefeilen er laget med et fanget 500-svar på `/api/admin/invitations`. Referanse: `09-alle-sider.png` (Admin-område, Brukere og roller), DESIGN.md (`segmented-choice`, `text-field`, `button-primary`) og EXPERIENCE.md (UJ-1).

| Fil | Viser | Samsvar |
|---|---|---|
| `admin-omrade-lenke-390.png` | «Admin-område» med én rad, Lenke «Brukere og roller», mellom hårstreker | Ja (radene i mockupen er i `ink`; Lenke-stilen er fra Story 3.3) |
| `admin-omrade-lenke-1280.png` | Samme på laptop, raden i skjemakolonnen | Ja |
| `brukere-tom-390.png` | Brødsmule, h1, «Inviter» med ingress, E-post tom, Rolle med Faglærer valgt, én primærknapp | Ja |
| `brukere-tom-1280.png` | Samme på laptop; ingressen holder seg i skjemakolonnen | Ja etter retting (ingressen var `max-w-xl`, bredere enn skjemaet) |
| `brukere-ugyldig-390.png` | «kari@»: `restordre`-ramme og «Domene mangler» under feltet, fokus i feltet | Ja (samme som «Glemt passord») |
| `brukere-ugyldig-1280.png` | Samme på laptop | Ja |
| `brukere-sendt-390.png` | Feltet tømt, Faglærer beholdt, resultatlinjen mellom to streker med adresse, rolle og 14 dager | Ja (understreken på knappen er musens hover) |
| `brukere-sendt-1280.png` | Samme på laptop | Ja |
| `brukere-admin-valgt-390.png` | Admin valgt (fylt `ink`), ny adresse skrevet; forrige resultatlinje står til neste trykk | Ja, men resultatlinjen «… som Faglærer» står ved siden av valgt Admin (vurdering) |
| `brukere-admin-valgt-1280.png` | Samme på laptop | Ja, samme merknad |
| `brukere-sendefeil-390.png` | 500: «Invitasjonen ble ikke sendt. Prøv igjen.» over knappen, adresse og rolle beholdt | Ja (teksten er [ASSUMPTION]) |
| `brukere-sendefeil-1280.png` | Samme på laptop | Ja |
| `brukere-ingen-tilgang-390.png` | Faglærer på `/admin/brukere`: «Du har ikke tilgang til denne siden.» og «Til Lærerhjem», ingen skjema | Ja (EXPERIENCE.md-tekst ordrett) |
| `brukere-ingen-tilgang-1280.png` | Samme på laptop | Ja |
| `invitasjon-mail.txt` | Invitasjons-e-posten (tekst og HTML) fra dev-postkassen: «Invitasjon til ØL-spillet», overskrift «ØL-spillet», lenke `/invitasjon#…`, «gyldig i 14 dager» | Ja (teksten er utkast; lenken gir «Fant ikke siden.» til Story 3.8) |

Ingen side ruller sidelengs på 390 px, og hver tilstand har høyst én primærknapp.
