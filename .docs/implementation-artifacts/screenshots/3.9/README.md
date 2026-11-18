# Story 3.9 – visuell kontroll

Tatt 2026-11-18 på compose-stakken (`http://127.0.0.1:8080`), full side, 390 og 1280 px, og 1280 px med 200 % tekst (`html { font-size: 200% }`), etter rettingen «Story 3.9: visuelle rettinger». Sammenlignet med `mockups/09-alle-sider.png` («Brukere og roller»: rolig liste, navn til venstre, rolle til høyre, hårlinjer), `DESIGN.md` og `EXPERIENCE.md`. Tildeling, fjerning, sidene for «Vis flere» og begge 409-svarene er falske svar via Playwright-ruting, så demobrukerne er uendret. Ingen tilstand ruller sidelengs.

- `admin-brukere-hel-side-390.png` / `-1280.png` / `-1280-tekst200.png` – hele siden: Inviter-skjemaet, søkefeltet og tabellen Navn / E-post / Roller / Status / Endre rolle. Én primærknapp («Send Invitasjon»), rolleknappene er sekundære. Under 60em (390 px og 200 % tekst) er hver rad en blokk med merkede felt og fullbredde knapper. Stemmer. Siden er svært lang fordi den lokale databasen har mange e2e-kontoer (lange `invitasjon-…`-adresser brytes over to–tre linjer).
- `admin-brukere-sok-treff-*.png` – søk «Demo»: de fire demokontoene. Stemmer.
- `admin-brukere-sok-ingen-treff-*.png` – «Ingen treff.» og ingen tabell. Stemmer.
- `admin-brukere-tildelt-*.png` – etter «Gi Demo rollen Faglærer» på Demo Student: Roller «Faglærer», knappen er nå «Fjern rollen Faglærer fra Demo», linjen «Demo har nå rollen Faglærer.» i raden. Stemmer.
- `admin-brukere-fjernet-*.png` – etter «Fjern rollen Faglærer fra Demo» på Demo Admin og Faglærer: «Demo har ikke lenger rollen Faglærer.». Stemmer.
- `admin-brukere-vis-flere-for-*.png` – første side (tre rader, én «Deaktivert» i `ink-secondary`) med sekundærknappen «Vis flere». Stemmer.
- `admin-brukere-vis-flere-etter-*.png` – neste side lagt under. Stemmer.
- `admin-brukere-vis-flere-feil-*.png` – neste side feiler: radene står, «Flere brukere kunne ikke lastes. Prøv igjen.» over «Vis flere». Stemmer. Avvik til vurdering: linjen er 14 px også på laptop (felles `ActionError`), mens radlinjene er 15 px.
- `admin-brukere-blokkert-*.png` – falsk 409 `role_revoke_blocked` (2): «Demo eier 2 Klasser. Legg til en annen Faglærer eller arkiver Klassene først.» i rødt i raden, rollen står. Stemmer.
- `admin-brukere-siste-admin-*.png` – falsk 409 `last_admin`: «Demo er den eneste aktive Admin. Gi en annen bruker rollen Admin først.». Stemmer.

Rettet før disse bildene: tabellradene sto toppjustert, så celleteksten lå ca. 12 px over knappeteksten i samme rad (nå `align-baseline`, første linje flukter), og «Faglærer, Admin» brøt over to linjer ved 1280 px (nå på én linje i tabellvisning).
