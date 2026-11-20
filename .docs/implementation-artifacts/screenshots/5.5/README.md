# Story 5.5 — skjermbilder (390 og 1280 px)

Fersk Klasse og Klasseøkt gjennom api-et, innlogget som faglaerer@example.com (Admin-skjemaet som admin@example.com), `locale: 'nb-NO'`. Tilstandene uten lokal motpart (to nivåer, utilgjengelig, leverandør mangler, låst) er laget ved å omskrive GET-svaret i nettleseren. Sammenlignet med mockup 03, DESIGN.md og EXPERIENCE.md. Ingen siderulling sideveis i noe bilde; én primærknapp («Lagre Klasseøkt» / «Send Invitasjon»). Retting i 3a56c65: på brede skjermer er Valgknapper på Klasseøkten like brede som etikettene (som mockup 03); før fylte de kolonnen, og ett enkelt nivå ble en mørk blokk over hele kolonnen. På telefon deler segmentene raden.

- `klasseokt-llm-390.png` / `-1280.png`: KI-modus «LLM-spillere» valgt, hjelpelinje, Innsatsnivå med ett nivå «standard» og plassholderlinjen «ikke målt ennå», Debrief-modus, Obligatorisk som tekst. Stemmer. (Nivånavnet «standard» med liten forbokstav kommer fra mock-konfigurasjonen seedet før historien, uten `label`.)
- `klasseokt-innsatsniva-to-390.png` / `-1280.png`: to nivåer «Lav» / «Høy», én effektlinje hver (konfigurasjonens tekst, og målte tall «Ca. 4,2 s per ordre, 0,31 USD per spill.»). Stemmer.
- `klasseokt-beskrivelser-apne-390.png` / `-1280.png`: begge «Slik bestiller …» åpne, avsnitt og punktliste i `body`, lesebredde begrenset. Stemmer.
- `klasseokt-regelbasert-personlig-390.png` / `-1280.png`: utkast med «Regelbaserte spillere» (Innsatsnivå skjult) og «Personlig debrief» med hjelpelinjen «Hver student går gjennom det alene.». Stemmer.
- `klasseokt-llm-utilgjengelig-390.png` / `-1280.png`: «LLM-spillere» i deaktivert utseende (`future-tint`, `ink-muted`), grunnen som tekst under, regelbaserte valgt. Stemmer.
- `klasseokt-leverandor-mangler-390.png` / `-1280.png`: advarselslinjen om KI-leverandøren i `ink`, Innsatsnivå som tekst (ingen nivå tilbys). Stemmer.
- `klasseokt-last-390.png` / `-1280.png`: låst økt, valgene som tekst uten kontroll. Valgene stemmer. Merk: «Lagre Klasseøkt» og datofeltene vises fortsatt når økten er låst (eldre oppførsel fra 5.2/5.3, ikke endret her; avgjøres separat).
- `admin-invitasjon-390.png` / `-1280.png`: Inviter-skjemaet med Rolle «Faglærer» / «Admin». Stemmer, men segmentene er nå litt ulike brede (størrelse etter etikett, rest fordelt likt) der de før var to like halvdeler. Ikke endret.
