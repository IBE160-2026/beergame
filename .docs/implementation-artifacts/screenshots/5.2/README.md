# Story 5.2: skjermbilder

Tatt 2026-11-19 mot lokal stack (127.0.0.1:8080), fersk Faglærer og Klasse per bredde. Datofeltene vises i nettleserens locale (en-US i Playwright). Låst/passert-tilstanden er tegnet fra et serversvar som e2e-testen bruker (`locked`, `passed_dates: ["start_at"]`, `play_time_warning`). Studenthjem: denne storyen har ingen studentvisning (Epic 6), så det finnes ikke noe skjermbilde av det.

- `klasse-liste-390.png`, `klasse-liste-1280.png`: Klassesiden med to Klasseøkter fra samme minutt, «Klasseøkt 2/1, opprettet …», med ulike etiketter (#98 b). Stemmer.
- `laererhjem-venter-390.png`, `laererhjem-venter-1280.png`: Lærerhjem, «Venter» lister begge øktene som Lenker, «Neste frist» viser «Ingen frist ennå.». Stemmer.
- `laererhjem-neste-frist-390.png`, `laererhjem-neste-frist-1280.png`: Økt 1 har datoer, økt 2 venter. «Neste frist» viser «Startdato, Klasseøkt 1, …» og tidspunktet i Oslo-tid. Stemmer.
- `klasseokt-tom-390.png`, `klasseokt-tom-1280.png`: «Datoer» med «Ingen datoer ennå.» og fire tomme felt, to kolonner på 1280 og én på 390. Stemmer med mockup 03.
- `klasseokt-forhandsutfylt-390.png`, `klasseokt-forhandsutfylt-1280.png`: Testfrist er fylt ut 7 dager etter Debrieffrist, med en hjelpetekst. Stemmer.
- `klasseokt-datoer-390.png`, `klasseokt-datoer-1280.png`: lagret; Datolinjen har fire merkede streker med dag og tid, og Debrieffrist er løftet til andre rad for å unngå kollisjon. På 390 har kjeden og Datolinjen en tonet høyrekant (#98 a). Én primærknapp. Stemmer.
- `klasseokt-datoer-rullet-390.png`: begge regionene er rullet, så nå toner venstrekanten ut. Stemmer.
- `klasseokt-feil-rekkefolge-390.png`, `klasseokt-feil-rekkefolge-1280.png`: Spillfrist før Startdato; rød kant, «Må komme etter Startdato.» under feltet og varsellinjen ved knappen. Stemmer.
- `klasseokt-feil-fortid-390.png`, `klasseokt-feil-fortid-1280.png`: Startdato i fortiden gir «Velg et tidspunkt fram i tid.» under feltet. Stemmer.
- `klasseokt-passert-last-390.png`, `klasseokt-passert-last-1280.png`: passert Startdato er skrivebeskyttet med «Passert. Datoen kan ikke flyttes.», og advarselen om kort spilletid vises som tekst mens lagring er tillatt. Stemmer.
