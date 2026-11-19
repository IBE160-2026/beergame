# Story 4.4 – visuell sjekk

Tatt 2026-11-19 mot compose-stacken (`http://127.0.0.1:8080`) som `faglaerer@example.com` på class-of-1994, fullside, 390 og 1280 px. Sammenlignet med mockup 02 (`02-laerer-klasse.png`), DESIGN.md og EXPERIENCE.md. Tatt på nytt etter rettingene i «Story 4.4: visuelle rettinger». 404 og 422 er forfalsket med route-intercept her; den nye Playwright-testen kjører dem mot ekte api.

- `klasse-sendeklar-390.png` – fil med 4 gyldige og 2 ugyldige rader, «Gyldig i antall dager» 14, «Mellom 1 og 60 dager.», én primærknapp «Send 4 Invitasjoner», merknaden under. Stemmer. Issue #86: «unntatt to» = «2 av 6», og overskriften er «E-post». Ingen sidelengs rulling.
- `klasse-sendeklar-1280.png` – samme, i to kolonner som mockup 02. Stemmer, men se avvik A og B.
- `klasse-gyldighet-61-390.png` / `-1280.png` – 61 dager: rød ramme og «Velg et helt antall dager mellom 1 og 60.» under hinten. Stemmer etter rettingen (feilen brøt før over to linjer i et 14rem-felt).
- `klasse-gyldighet-0-390.png` / `-1280.png` – 0 dager, samme feil. Stemmer etter rettingen.
- `klasse-sending-avvist-404-390.png` / `-1280.png` – «Klasselista er endret siden du lastet den. Se over og send igjen.» i restordre under merknaden. Stemmer.
- `klasse-sending-avvist-422-390.png` / `-1280.png` – `nothing_to_send` med den nye teksten «… Ingen av adressene kan inviteres nå.». Stemmer etter rettingen (før var teksten lik «Ingen gyldige adresser å invitere.» og sto to ganger når staging ble lastet på nytt).
- `klasse-sendt-390.png` / `-1280.png` – «4 Invitasjoner sendt. Gyldige til og med 3. desember.», antallet på Klasselista over, og tom boks med «Velg fil». Stemmer.
- `klasse-allerede-paa-lista-390.png` / `-1280.png` – samme fil på nytt: fire rader «Står allerede på Klasselista», «Ugyldige rader: 6 av 6», «Send 0 Invitasjoner» utilgjengelig og «Ingen gyldige adresser å invitere.». Stemmer, se avvik A.
- `klasse-tom-innliming-390.png` / `-1280.png` – tom innliming: «0 adresser lest», ingen merknad (Issue #86). Stemmer.
- `laererhjem-antall-390.png` / `-1280.png` – «Klassene dine» med «N adresser på Klasselista». Stemmer (ingen egen mockup).
- `elev-invitasjon-mail.txt` – Elev-e-posten fra dev-postkassa: navngir Klassen og «gyldig til og med 3. desember 2026». Stemmer med spec.

## Avvik som krever en vurdering

- A. Ved 1280 px er verdikolonnen i «Ugyldige rader» smal (rundt 190 px), så lange adresser brytes midt i ordet («…example.co / m»). Den lange grunnen «Står allerede på Klasselista» gjør det verre. Mockup 02 har bredere verdikolonne og en Navn-kolonne. Se `klasse-allerede-paa-lista-1280.png`.
- B. Hinten under «E-postkolonne» gjentar valgt kolonne («Kolonne C, E-post. Valgt fordi …»). Mockup 02 har bare grunnen. Dette er fra Story 4.2, ikke 4.4. Se `klasse-sendeklar-1280.png`.
- C. Mockup 02 viser ugyldige verdier som røde inputfelt og «Status etter utsending». Det tilhører 4.6–4.8.
