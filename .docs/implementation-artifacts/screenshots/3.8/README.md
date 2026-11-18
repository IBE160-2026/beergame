# Story 3.8 – visuell kontroll

Tatt 2026-11-18 på compose-stakken (`http://127.0.0.1:8080`), full side, 390 og 1280 px, etter rettingen «Story 3.8: visuelle rettinger». Sammenlignet med `mockups/04-student-hjem.png` (Registrering), `DESIGN.md` og `EXPERIENCE.md`.

- `invitasjon-ny-tom-390.png` / `-1280.png` – ny konto, tom: Navn, E-post (skrivebeskyttet, forhåndsutfylt), Velg passord med «Minst 8 tegn.» før skriving, én primærknapp, gyldighetslinje. Stemmer. Avvik: mockupen sier «Minst 10 tegn» (bygget bruker 8, ikke endret), og «Har du konto? Logg inn» mangler (valgt bort i spec). Lange testadresser klippes i det skrivebeskyttede feltet.
- `invitasjon-ny-feil-390.png` / `-1280.png` – trykk uten utfylling: grunner under Navn og passord, fokus på Navn. Stemmer.
- `invitasjon-ny-suksess-390.png` / `-1280.png` – lander på Lærerhjem, innlogget som «Ny Faglærer». Stemmer.
- `invitasjon-eksisterende-tom-390.png` / `-1280.png` – adressen har konto: ingress, E-post skrivebeskyttet, Passord, «Logg inn og legg til rollen», «Glemt passord?». Stemmer.
- `invitasjon-eksisterende-feil-390.png` / `-1280.png` – feil passord: «Feil e-post eller passord.» over knappen. Stemmer.
- `invitasjon-eksisterende-suksess-390.png` / `-1280.png` – Admin + Faglærer lander på Lærerhjem med «Til Admin-område». Stemmer (hjemregelen fra Story 3.3).
- `invitasjon-ugyldig-390.png` / `-1280.png` – utløpt/brukt lenke: linjen «Lenken er utløpt eller brukt.» og én sekundærknapp «Be om ny Invitasjon». Stemmer.
- `invitasjon-ugyldig-bedt-390.png` / `-1280.png` – etter forespørselen: én resultatlinje med linjer over og under, som erstatter tilstanden. Stemmer etter retting (var udekorert tekst under den linjede «utløpt»-linjen).
- `invitasjon-ny-429-390.png` / `-1280.png` – falsk 429 på `accept`: «For mange forsøk. Vent litt og prøv igjen.» over knappen. Stemmer.
- `invitasjon-ugyldig-429-390.png` / `-1280.png` – falsk 429 på `renewal`: samme linje over «Be om ny Invitasjon». Stemmer.
- `admin-brukere-sendt-390.png` / `-1280.png` – «Brukere og roller» etter sending: resultatlinjen under knappen. Stemmer (understrekingen på knappen er hover fra pekeren).
- `admin-brukere-tomt-etter-endring-390.png` / `-1280.png` – etter at adressen er skrevet i: resultatlinjen er borte (Issue #74). Stemmer.

Ingenting ruller sidelengs eller klippes ved 390 px, bortsett fra lange adresser inne i det skrivebeskyttede e-postfeltet.
