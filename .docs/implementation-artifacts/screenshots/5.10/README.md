# Story 5.10 – visuell kontroll

Demo-Faglærer (faglaerer@example.com, nb-NO, Europe/Oslo), ny Klasse med 5 studenter registrert via api; ett trekk (4 + 1). «avvist» er et stubbet 422 `invalid_move`/`last_student` (ikke nåbart fra en fersk trekning). Sammenlignet med mockup 03, DESIGN.md og EXPERIENCE.md. Tatt etter rettingen (`Story 5.10: visuelle rettinger`). Ingen side ruller sidelengs på 390 px; ingen tekst under 13 px; alle knapper i `main` ≥ 44 px; høyst én primærknapp.

- `klasseokt-fordeling-flytt-liste-{390,1280}.png` – åpent utkast, «Seter i Spill 1» med Fabrikk først, «Flytt eller bytt» sekundær på hver studentrad (fullbredde på telefon, egen kolonne på bred skjerm). «Bekreft fordeling» eneste primærknapp. Stemmer.
- `klasseokt-fordeling-valgt-{390,1280}.png` – student valgt: statuslinjen «… skal flyttes. Velg et spill …», raden i halvfet med «Avbryt flyttingen», de andre radene «Bytt». Stemmer.
- `klasseokt-fordeling-valgt-spill2-{390,1280}.png` – valget beholdt mens Spill 2 er valgt i diagrammet: «Flytt» på ledige seter (KI-spiller i `ink-muted`), «Bytt» på studenten. Stemmer.
- `klasseokt-fordeling-flyttet-{390,1280}.png` – etter flytt: diagram og liste oppdatert, Spill 2 valgt, fokus på den flyttede studentens rad, resultatlinjen «… er flyttet til …». Stemmer.
- `klasseokt-fordeling-byttet-{390,1280}.png` – etter bytte: «… har byttet plass.», fokus på den byttede raden i Spill 1. Stemmer.
- `klasseokt-fordeling-avvist-{390,1280}.png` – avvist flytt: «Spillet ville stått uten studenter …» i `restordre` rett under setelista, valget beholdt. Stemmer etter retting (feilen sto under «Lukk», ~400 px fra knappen på 390 px; EXPERIENCE.md vil ha den ved handlingen).
- `klasseokt-fordeling-endret-{390,1280}.png` – utdatert utkast: «Fordelingen er endret siden du åpnet den …» under setelista, valget nullstilt, gjeldende utkast vist. Stemmer etter samme retting.
- `klasseokt-fordeling-bekreftet-{390,1280}.png` – etter bekreftelse: blokken lukket, «Fordelingen er bekreftet.» (fokus), «Lagre Klasseøkt» primær igjen. Stemmer.
- `klasseokt-fordeling-bekreftet-aapnet-{390,1280}.png` – bekreftet fordeling åpnet av eier: «Fordelingen er bekreftet fr. 20. nov. kl. 04:59.» i halvfet under overskriften (Issue #107), flytteknapper, «De som flyttes eller byttes, får beskjed på e-post.» i stedet for «Ingen får beskjed …», ingen «Kjør på nytt»/«Bekreft». Stemmer.
- `klasseokt-fordeling-bekreftet-flyttet-{390,1280}.png` – flytt etter bekreftelse til ledig sete i Spill 2: bekreftet-linjen står, resultatlinjen og fokus på raden. Stemmer.
- `klasseokt-fordeling-bekreftet-lesing-{390,1280}.png` – bekreftet fordeling lest uten rett til å endre (stubbet `can_manage: false`): bekreftet-linjen vises (Issue #107), spill-linje i stedet for setelista, ingen knapper utenom «Lukk», ingen e-postlinje. Stemmer.
