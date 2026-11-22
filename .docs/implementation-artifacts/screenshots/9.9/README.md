# Story 9.9: skjermbilder (Debrief-quiz, steg 5)

Student, Debrief `/debrief/{classSessionId}#debrief-quiz`, svar fra api-stub (`frontend/e2e/support/quiz.ts`). Helside, nb-NO. Bredder: 390 px, 1280 px og 390 px med 200 % tekst (`-390-tekst200`). Ingen mockup finnes for quizen (`09-alle-sider.png` og `07-debrief.png` viser den ikke), så sammenlikningen er mot DESIGN.md (Quizvalg, `quiz-option`) og EXPERIENCE.md (Quizvalg, FR-46). Ingen sideveis scrolling i noen av dem, alle valg er minst 44 px høye.

- `debrief-quiz-ubesvart-{390,1280,390-tekst200}.png`: tre spørsmål som Quizvalg-rader med «Spørsmål n av 3», ett primærvalg «Send svarene». Samsvarer.
- `debrief-quiz-delvis-besvart-{...}.png`: ett spørsmål besvart, «Send svarene» trykket, ingenting sendt, «Velg et svar på hvert spørsmål før du sender.» i `restordre` ved knappen. Samsvarer.
- `debrief-quiz-tastaturfokus-{...}.png`: fokus på et valg via piltaster, 2 px `ink`-ramme med avstand rundt raden, valgt rad 1,4 px `ink` med fylt prikk. Samsvarer.
- `debrief-quiz-feil-forsok-{...}.png`: «Forsøk 1: 2 av 3 riktige», feil rad 1,4 px `restordre` med «Ditt svar, ikke riktig», riktig rad 1,4 px `ink` med «Riktig», forklaring som brødtekst under, sekundær «Prøv igjen». Samsvarer. Ved 200 % tekst ble «Ditt svar, ikke riktig» kuttet i høyre kant; rettet, merket brytes nå over to linjer inne i raden.
- `debrief-quiz-nytt-forsok-{...}.png`: nytt forsøk, spørsmålene i ny rekkefølge, ingen valg gjort. Samsvarer.
- `debrief-quiz-bestatt-{...}.png`: «Forsøk 2: 3 av 3 riktige. Alle svarene er riktige.», alle riktige rader merket «Riktig», ingen «Prøv igjen» og ingen knapp. Samsvarer.
- `debrief-quiz-testfrist-avslag-{...}.png`: alle valg gjort, «Testfristen er passert, så svarene kan ikke sendes lenger.» ved knappen, ingen resultatlinje. Samsvarer.
- `stegene-quiz-lenke-{390,1280}.png`: Hjem med Stegene der Quiz er gjeldende steg og navnet er en understreket Lenke til `#debrief-quiz`, «pågår» i tekst. Samsvarer.
