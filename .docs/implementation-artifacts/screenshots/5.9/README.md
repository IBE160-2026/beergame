# Story 5.9 – visuell kontroll

Faglærer (ny Lærer fra invitasjon, nb-NO), ny Klasse per tilstand, studenter registrert via api; 3 og 100 spill med fjernet student er stubbet svar. Sammenlignet med mockup 03, DESIGN.md og EXPERIENCE.md. Tatt etter rettingene (`Story 5.9: visuelle rettinger`). Ingen side ruller sidelengs på 390 px.

- `klasseokt-fordeling-utkast-{390,1280}.png` – åpent utkast, 6 studenter, 2 spill: «Kjør fordeling på nytt» sekundær, «Bekreft fordeling» eneste primærknapp, «Lagre Klasseøkt» sekundær. «Ingen får beskjed før du bekrefter.» brytes under knappene i den smale kolonnen (mockup: ved siden av; spesifikasjonens valg). Stemmer.
- `klasseokt-fordeling-valgt-klikk-{390,1280}.png` – spill 2 valgt med klikk: 1 px `ink`-ramme. Stemmer.
- `klasseokt-fordeling-valgt-tastatur-{390,1280}.png` – ← til spill 1: 3 px fokusramme. Stemmer.
- `klasseokt-fordeling-bekreftet-{390,1280}.png` – etter bekreftelse: blokken lukket, «Fordelingen er bekreftet.» (fokus), «Lagre Klasseøkt» primær igjen. Stemmer.
- `klasseokt-fordeling-bekreftet-aapnet-{390,1280}.png` – bekreftet fordeling åpnet: kun lesing, ingen «Kjør på nytt»/«Bekreft», bare «Lukk». Stemmer; panelet sier ikke selv at fordelingen er bekreftet (vurdering).
- `klasseokt-fordeling-endret-{390,1280}.png` – medeier trakk på nytt: `allocation_changed`, ny trekning vist, «Fordelingen er endret siden du åpnet den …». Stemmer.
- `klasseokt-fordeling-studenter-fjernet-{390,1280}.png` – én student fjernet fra Klasselista før bekreft: 5 studenter, ledig sete som KI-spiller, «En eller flere studenter er ikke lenger i Klassen …». Stemmer.
- `klasseokt-fordeling-fjernet-liten-{390,1280}.png` – 3 spill, fjernet student: `paper`-celle med stiplet `ink`-kant, skiller seg fra student (fylt) og KI-spiller (heltrukken `ink-muted`). Stemmer etter retting (kantene lå på halve piksler og ble grå og 2 px).
- `klasseokt-fordeling-fjernet-stor-{390,1280}.png` – 100 spill (10 px søyler), spill 17 valgt med klikk, fjernede seter i spill 17, 18 og 41: stiplet celle leses også i 8 px bredde, 1 px ramme. Stemmer etter retting (rammen var grå og uskarp).
- `klasseokt-fordeling-fjernet-stor-tastatur-{390,1280}.png` – → til spill 18: 3 px fokusramme, skarp. Stemmer.
- `laererhjem-mangler-fordeling-{390,1280}.png` – «Venter»: ubekreftede økter «… mangler datoer og bekreftet fordeling», bekreftede bare «… mangler datoer». Stemmer etter retting (to-linjers lenker lå tett inntil neste, nå 8 px mellomrom).
