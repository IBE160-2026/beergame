# Story 3.6 — visuell kontroll

Tatt 2026-11-18 på compose-stakken (`http://127.0.0.1:8080`) med `worker-batch`, Chromium, full side, 390 og 1280 px, etter rettingene i «Story 3.6: visuelle rettinger». Mønster: `<skjerm>-<tilstand>-<bredde>.png`. Rate-limit-tilstanden er laget med et fanget 429-svar (`rate_limited`), fordi compose hever grensene lokalt.

| Fil | Viser | Samsvar |
|---|---|---|
| `logg-inn-glemt-passord-lenke-390.png` | «Logg inn» med lenken «Glemt passord?» under knappen | Ja (09-alle-sider, Logg inn) |
| `logg-inn-glemt-passord-lenke-1280.png` | Samme på laptop | Ja |
| `glemt-passord-tom-390.png` | Tom «Glemt passord»: ingress, E-post, én primærknapp «Send lenke», «Til innlogging» | Ja |
| `glemt-passord-tom-1280.png` | Samme på laptop | Ja |
| `glemt-passord-valideringsfeil-390.png` | «ola@»: `restordre`-ramme og «Domene mangler» under feltet | Ja |
| `glemt-passord-valideringsfeil-1280.png` | Samme på laptop | Ja |
| `glemt-passord-for-mange-390.png` | 429: «For mange forespørsler. Prøv igjen om en time.» over knappen | Ja (teksten er [ASSUMPTION]) |
| `glemt-passord-for-mange-1280.png` | Samme på laptop | Ja |
| `glemt-passord-sendt-390.png` | Sendt-linjen mellom to streker, «Til innlogging» | Ja (EXPERIENCE.md-tekst ordrett) |
| `glemt-passord-sendt-1280.png` | Samme på laptop | Ja |
| `nytt-passord-gyldig-390.png` | Gyldig lenke: «Velg et nytt passord for …», feltet, hint «Minst 8 tegn.», «Lagre passord» | Ja |
| `nytt-passord-gyldig-1280.png` | Samme på laptop | Ja |
| `nytt-passord-for-kort-390.png` | «kort»: hint og «Passordet må ha minst 8 tegn.» under feltet | Ja, men hint og feil sier nesten det samme (vurdering) |
| `nytt-passord-for-kort-1280.png` | Samme på laptop | Ja, samme merknad |
| `nytt-passord-lagret-390.png` | «Passordet er endret.», så «Logg inn» (seksjonsoverskrift) med e-posten fylt inn | Ja etter retting (h2 var `title-phone`, nå `headline`) |
| `nytt-passord-lagret-1280.png` | Samme på laptop | Ja etter retting |
| `nytt-passord-utlopt-390.png` | Brukt lenke: «Lenken er utløpt eller brukt.» og «Send ny lenke» | Ja (EXPERIENCE.md-tekst ordrett) |
| `nytt-passord-utlopt-1280.png` | Samme på laptop | Ja |

Ingen side ruller sidelengs på 390 px, og hver tilstand har høyst én primærknapp.
