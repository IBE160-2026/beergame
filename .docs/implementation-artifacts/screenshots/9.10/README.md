# Story 9.10: skjermbilder

Visuell kontroll mot DESIGN.md og EXPERIENCE.md, Klasseøkt-skjermen og Hjem. Breddene er 390 px, 1280 px og 1280 px med 200 % tekst (`-200`). Alle bilder er hele siden. Ingen sideveis rulling og ingenting avkuttet i noen av dem. Alle samsvarer; ingen rettinger var nødvendige.

## Klasseøkten, blokken «Debrief-quiz»

- `klasseokt-quiz-eier-{390,1280,1280-200}.png`: eier av Klassen, alle spørsmål med, ett Bryter per spørsmål, riktig svar under hvert, «Lagre quizvalg» som eneste knapp i blokken (sekundær; «Lagre Klasseøkt» er sidens primærknapp). Samsvarer.
- `klasseokt-quiz-lagret-{390,1280,1280-200}.png`: spørsmål 1 tatt ut og lagret, «Tatt ut» ved Bryteren, «Quizvalgene er lagret.» under knappen. Samsvarer.
- `klasseokt-quiz-siste-spoersmal-{390,1280,1280-200}.png`: alle spørsmål tatt ut, avslått med «Minst ett spørsmål må være med i quizen.» i feilfarge ved knappen. Samsvarer.
- `klasseokt-quiz-assistent-{390,1280,1280-200}.png`: Assistent-faglærer, «Bare Faglærerne i Klassen kan ta ut spørsmål.», ingen Bryter og ingen knapp, status som tekst. Samsvarer.
- `klasseokt-quiz-laast-{390,1280,1280-200}.png`: etter Testfristen, «Testfristen er passert, så quizvalgene kan ikke endres lenger.», skrivebeskyttet. Samsvarer.

## Debrief-sammendrag for ansatte

- `debrief-ansatt-med-forsok-{390,1280,1280-200}.png`: Studentens navn, to quizforsøk («2 forsøk. Bestått …», så ett forsøk per linje med tid og resultat). Samsvarer.
- `debrief-ansatt-fjernet-student-{390,1280,1280-200}.png`: navnet erstattet av «Studenten er ikke lenger i Klassen.». Samsvarer.
- `debrief-ansatt-uten-forsok-{390,1280,1280-200}.png`: Debrief-quiz uten forsøk, teksten for ingen forsøk. Samsvarer.

## Studentens Hjem

- `hjem-quiz-endret-{390,1280,1280-200}.png`: Stegene med Quiz som gjeldende og «pågår, quizen er endret» som notat, lenken til Quiz. Samsvarer.

## Merknader til skjønn

- På 1280 px står spørsmålene i tre kolonner, og Bryteren i kolonne 3 havner noen piksler høyere enn i 1 og 2 når svarene ikke bryter likt (ulik høyde på svarlinjene). Ved 200 % tekst brytes «Med i quizen» på to linjer ved Bryteren. Ikke en avvikende utforming, og ikke rettet.
- Debrief-sammendraget er skjermbilder mot stand-in-svar (som `debrief-bill.spec.ts`); Hjem likeså. Klasseøkt-blokken er mot den virkelige stacken.
