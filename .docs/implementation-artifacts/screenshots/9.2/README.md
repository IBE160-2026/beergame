# Story 9.2: skjermbilder

Tatt mot lane-stacken (proxy 8081), Chromium `--lang=nb-NO`, helside, 390 px og 1280 px. Ekte data fra et nytt Klassespill (en Student, KI regelbasert, to uker), unntatt de «holdt»-tilstandene, der api-svaret er patchet (ett Klassespill kan ikke holdes tilbake i en ekte kjøring). Ingen sideveis rulling på noen skjerm.

- `debrief-ikke-apen-{390,1280}.png`: /debrief mens spillet pågår: «Debrief», «Debriefen åpner når Klassespillet ditt er ferdig.», «Til Hjem». Matcher.
- `debrief-apen-steg1-{390,1280}.png`: /debrief åpen på steg 1: «Debrief, Spill 1», «Fabrikk, Spill 1», «1 Skriv Forklaringen først». Matcher stegets nummer og overskrift i `07-debrief.png`; innholdet i steget kommer med Story 9.3, og mockupens lengre tittel («fra «hadde jeg rett?» til …») er ikke i denne storyen.
- `debrief-holdt-{390,1280}.png`: /debrief når Faglæreren holder Debriefene: «Debriefen åpner når alle Klassespillene er ferdige.», ingen tall. Matcher.
- `spillet-er-ferdig-apen-{390,1280}.png`: «Spillet er ferdig» med én primærknapp «Gå til Debrief». Matcher.
- `spillet-er-ferdig-holdt-{390,1280}.png`: samme skjerm, knappen erstattet av «Debriefen åpner når alle Klassespillene er ferdige.» og «Til Hjem»; ingen primærknapp. Matcher.
- `hjem-spillet-pagar-{390,1280}.png`: Hjem mens spillet pågår: Stegene sier «Debrief, åpnes når Klassespillet er ferdig.». Matcher.
- `hjem-debrief-apen-{390,1280}.png`: Hjem etter spillet: Stegene med «Debrief» som lenke (lager, 600, understreket) og «pågår». Matcher.
- `hjem-debrief-holdt-{390,1280}.png`: Hjem med holdt Debrief: «Debrief, åpnes når alle Klassespillene er ferdige.». Matcher.
- `klasseokt-apen-valg-{390,1280}.png`: Klasseøkt (ulåst) med «Når Debriefen åpner», «Når eget spill er ferdig» valgt og hjelpetekst. Matcher; to valg legges under hverandre i smal kolonne, som de andre Valgknappene gjør når de ikke får plass.
- `klasseokt-holdt-valg-{390,1280}.png`: samme, «Når alle spill er ferdige» valgt, hjelpeteksten byttet. Matcher.
- `klasseokt-last-{390,1280}.png`: låst Klasseøkt: valget står som tekst («Når eget spill er ferdig») med hjelpetekst. Matcher.
