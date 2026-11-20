# Story 5.3: skjermbilder

Tatt 2026-11-19 mot lokal stack (127.0.0.1:8080) som demo-Faglærer, med en fersk Klasse og Klasseøkt per bredde (Playwright, `locale: nb-NO`). Datofeltene viser `mm/dd/yyyy` fordi headless Chromium bruker en-US-format i `datetime-local` uansett locale (som i 5.2). Låst-tilstanden er tegnet fra et serversvar med `locked: true`, slik e2e-testen gjør; datofeltene er derfor fortsatt redigerbare der. Ingen sidelengs rulling på 390 i noen tilstand. Ingen visuelle rettinger var nødvendige.

- `klasseokt-lesevisning-390.png`, `klasseokt-lesevisning-1280.png`: lesevisning, «Spillinnstillinger: Klassisk», tretten rader med Startrestordre og Største ordre, Lenke-knappen «Endre spillinnstillinger» under lista. Én primærknapp. Stemmer med mockup 03.
- `klasseokt-endre-klassisk-390.png`, `klasseokt-endre-klassisk-1280.png`: blokken åpnet på stedet med elleve Tekstfelt (etikett over), Klassisk-verdier, kostnader med komma («0,50», «1,00»), hjelpetekster under; én kolonne på 390, to på 1280. Etterspørsel og Inaktivitetsgrense står som lesrader, «Avbryt endringene» som Lenke. Stemmer.
- `klasseokt-omradefeil-390.png`, `klasseokt-omradefeil-1280.png`: Ordreforsinkelse 4 gir `restordre`-kant og «Må være fra 1 til 3.» under feltet. Stemmer.
- `klasseokt-advarsel-390.png`, `klasseokt-advarsel-1280.png`: Restordrekost 0,50 gir «Advarsel: Restordrekost (0,50) er ikke høyere enn Lagerkost (0,50). …» i `ink` under hjelpeteksten, uten rød kant. Stemmer.
- `klasseokt-feil-ettersporsel-390.png`, `klasseokt-feil-ettersporsel-1280.png`: Antall uker 4 gir advarsel under Antall uker, feil med område under Veiledede uker (0 til 3) og «Etterspørselen endres etter siste uke. …» under raden «Etterspørsel». Stemmer.
- `klasseokt-lagret-kalibrering-390.png`, `klasseokt-lagret-kalibrering-1280.png`: lagret med Startlager 15; overskrift «Spillinnstillinger», standardlinja borte, kalibreringslinja med Klassisk-verdiene, advarselen under Restordrekost, «Kjeden ved start» tegner Lager 15, «Klasseøkten er lagret.» ved knappen. Stemmer.
- `klasseokt-last-390.png`, `klasseokt-last-1280.png`: låst; linja «Klasseøkten har startet. Spillinnstillingene kan ikke endres.», ingen «Endre spillinnstillinger». Stemmer.

Til vurdering (ikke endret): mens blokken er åpen, står overskriften «Spillinnstillinger: Klassisk» og «Alt er fylt ut med standardene.» til utkastet er lagret (de viser den lagrede tilstanden). Linja «Kildene er uenige om forsinkelsene …» vises fortsatt etter at forsinkelsene er endret.
