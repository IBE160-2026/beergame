# Story 7.9 Meldingsskjema, visuell kontroll

Bredder: 390, 1280 og 1280-200pct (200 % tekst). Alle skjermbilder er fullside, som Faglærer, i nb-NO. Ingen visuelle rettinger var nødvendig.

- `inngang-oversikt-<bredde>.png`: Oversikt med Lenken «Skriv melding til alle» i toppen (ved siden av tittelen). Samsvarer; Lenke, ikke knapp, så det er ingen ekstra primærknapp.
- `inngang-spillinnsikt-<bredde>.png`: Spillinnsikt med «Melding» ved Spill-tittelen (Klassespillet) og ved hvert Student-sete. Samsvarer. På 390 beskjæres Uke for uke-tabellen i egen rullebeholder (ikke Story 7.9; siden ruller ikke sideveis).
- `skjema-alle-tom-<bredde>.png`: Melding til alle i Klasseøkt, tomt. Tittel med mottaker, «Meldingen går til 2 studenter.», felt med merkelapp «Melding», hint, utilgjengelig «Send Melding», «Sendt tidligere: 0». Samsvarer med `09-alle-sider` (tittel, tekstfelt, Send, Sendt tidligere).
- `skjema-alle-utfylt-<bredde>.png`: samme, utfylt; «Send Melding» aktiv, eneste primærknapp. Samsvarer.
- `skjema-spill-tom-<bredde>.png`: Melding til Spill 1 (Klassespill), tomt. Samsvarer.
- `skjema-student-tom-<bredde>.png`: Melding til Student, Spill 1, tomt. Samsvarer med mockupens «Melding til Noah, Spill 2».
- `skjema-student-utfylt-<bredde>.png`: Student, utfylt. Samsvarer.
- `skjema-student-feil-no_recipients-<bredde>.png`: feil `no_recipients` («Ingen studenter får denne meldingen nå.») i rød linje under knappen, teksten beholdt. Samsvarer.
- `skjema-student-feil-message_too_long-<bredde>.png`: «Meldingen er for lang. Høyst 2 000 tegn.» under knappen. Samsvarer.
- `skjema-student-feil-unknown-<bredde>.png`: ukjent kode gir «Det ble ikke lagret. Prøv igjen.», teksten beholdt, knappen aktiv. Samsvarer.
- `skjema-student-sendt-<bredde>.png`: «Meldingen er sendt til 1 student.» mellom to linjer, «Sendt tidligere: 1» og «Skriv en ny melding» (sekundær). Samsvarer med EXPERIENCE (resultat erstatter skjemaet); ingen primærknapp i resultatet.

Merknader: ingen sideveis rulling på noen bredde; kontrollene er minst 44 px på 390. Primærknappen vises understreket i feil- og utfylt-bildene fordi musen står over den (hover-stilen i `button.tsx`). Toppen (brukernavn og «Logg ut») bryter på to linjer på 390; det er felles sideskall, ikke Story 7.9.
