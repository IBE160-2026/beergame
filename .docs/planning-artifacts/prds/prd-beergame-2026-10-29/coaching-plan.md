---
title: "Coaching-plan: PRD for beergame"
created: 2026-11-05
updated: 2026-11-05
---

# Coaching-plan: PRD for beergame

Coaching-runden går gjennom de delene av PRD-utkastet der founders vurdering betyr mest. Beslutningene føres inn i `prd.md` og logges i `.memlog.md`. Det som gjenstår, følges også opp i Issue #12.

| Tema | Innhold | Status |
|---|---|---|
| 1 | Brukerreisene | Ferdig |
| 2 | Kvalitetskravene til AI-spillerne | Ferdig (spørsmål 4–7 åpne) |
| 3 | Testen og KI-vurderingen | Ferdig |
| 4 | Standardparametre og replay-scenarier | Ferdig |
| Etterpå | Finalisering av PRD-en | Neste |

## Tema 1: Brukerreisene (ferdig)

Founder beskrev en konkret økt, og brukerreisene og kravene ble skrevet om etter det. Runden førte også til disse beslutningene:

- Formell sensur flyttes til v2. V1 får en KI-vurdering som ikke teller, og en PDF-rapport.
- Læreren kan gjøre spillet obligatorisk.
- Veiledende A–F-bokstav kan slås på av lærer eller student.
- Studenten forklarer seg i debriefen.
- V1 har ingen frivillige ekstra runder.

## Tema 2: Kvalitetskravene til AI-spillerne (ferdig, med åpne spørsmål)

Founder avsluttet temaet 2026-11-05 etter spørsmål 1–3. Beslutninger:

- AI-spilleren vet ikke at den spiller et spill, ikke at det er fire plasser, og ikke at runden animeres når alle har bestilt. Reglene ligger implisitt i prompten, og den ser bare egne data og det som kommer fra nedstrøms og oppstrøms.
- En smart AI-spiller er greit, selv om den demper bullwhip. SM-C3 er skrevet om.
- Faglærer kan velge effort (tenkenivå) for modellen. Prompten kalibreres ved testing før lansering.
- Valget av regelbaserte spillere, for eksempel av tidshensyn eller av prinsipp, er en innstilling faglærer gjør når klassen opprettes.
- Regelen om at regelbaserte spillere blir standard etter piloten, er erstattet av en spillvakt (FR-79) som sammenligner ukentlige ordrer med en regelbasert og en nesten optimal referanse og bytter plassen til regelbasert utenfor båndet. 95 % innenfor fornuftig spill, og ikke nærmere enn 5 % til supersmart.
- Ugyldige ordrer løses med JSON-skjema og opptil 5 nye forsøk, så regelbasert (FR-32). 2 %-grensen i SM-3(a) er fjernet.

Åpent etter temaet: gjelder fallbacken bare uka eller resten av spillet, hvor lenge en student kan vente (spørsmål 6, med forsøk og effort), variasjon mellom kjøringer (spørsmål 4), måling av troverdighet (spørsmål 5), og når avgjørelsen tas (spørsmål 7). Se PRD §12 punkt 12 og 13.

**Mål:** bestemme hva som skal til for å bruke LLM-spillere med 250 studenter, og når regelbaserte spillere blir standard i stedet.

**PRD:** SM-3, FR-30 til FR-34, NFR-2. **Issues:** #8, #9, #10, #11.

Spørsmål:

1. Hva må du se av AI-spillerne før du tør å bruke dem i kurset ditt?
2. Hva ville fått deg til å droppe dem?
3. Hvor stor andel ugyldige eller for sene ordre tåler du? Utkastet sier maks 2 %.
4. Hvor mye kan resultatene variere mellom kjøringer? Utkastet sier omtrent 10–15 %.
5. Hvordan skal troverdighet måles? Utkastet bruker ett spørsmål på en skala fra 1 til 5, med median på minst 4.
6. Hvor lenge kan en student vente på en AI-spiller? Utkastet sier 8 sekunder.
7. Når skal avgjørelsen tas: etter en prototype før piloten, eller etter selve piloten?

## Tema 3: Testen og KI-vurderingen (ferdig)

**PRD:** FR-51 til FR-56, nye FR-80 til FR-82, SM-7, åpent spørsmål 6. Forskningen ligger i `.docs/planning-artifacts/research/academic-lit-beer-game-test-questions-systems-thinkin-2026-11-05/research.md`.

Runden førte til disse beslutningene:

- Testen spør etter det å huske spillet ikke gir: mengder, sammenheng mellom grafer og forklaring av mekanismen.
- Testen tas uten oppsyn. Interaktive grafer, tabeller og diagrammer kommer i tillegg til tekstfelt og flervalg. Det skal gjøre testen vanskeligere å løse med KI, men det er ikke dokumentert. En generell KI prøves derfor på testen før piloten.
- Studenten kan lukke testen og jobbe så mye hen vil fram til fristen. Læreren kan i stedet kreve én økt med tidsgrense.
- De tilpassede spørsmålene teller 30 % som standard og bygger på faste maler.
- KI-en vurderer etter en sensorveiledning. Claude skriver utkast til standardversjonen under implementeringen, og founder godkjenner. Læreren kan endre den for sin klasseøkt.
- KI-en kontrolleres i en egen kontrolltest med teststudenter før piloten (ny FR-82). Founder skårer den alene. Terskelen på 80 % i SM-7 bekreftes etter den første kontrolltesten.
- Bokstavgrensene er en lærerinnstilling.

## Tema 4: Standardparametre og replay-scenarier (ferdig)

**PRD:** FR-11 til FR-13, FR-49, ny FR-83, åpent spørsmål 5. Forskningen ligger i `.docs/planning-artifacts/research/domain-beer-game-variants-and-setup-options-2026-11-05/research.md`.

Runden førte til disse beslutningene:

- Standardverdiene er bekreftet, med ordreforsinkelse på 2 uker og 36 uker.
- Læreren kan sette alle spillparametre selv, også for replay-runden. Eneste forhåndsvalg er Classic.
- Innsyn hos nabo oppstrøms og nedstrøms er med i v1 og er av som standard (FR-83).
- Kapasitetsgrenser er med som en valgfri innstilling.
- Replay-runden har som standard samme snitt som klassespillet, men større variasjon i etterspørselen.

## Etterpå: Finalisering

Rekkefølgen følger `bmad-prd`:

1. Gå gjennom `.memlog.md`: hver beslutning skal stå i PRD-en eller addendumet, eller være bevisst lagt til side.
2. Avstem PRD-en mot kildene: brief, research, forge-rapport og tidligere planer.
3. Kjør reviewer-pass og løs funnene.
4. Gå gjennom åpne spørsmål og `[ASSUMPTION]`-merker. Det som blokkerer UX og arkitektur, løses først.
5. Språkvask `prd.md` og `addendum.md`.
6. Sett status til `final` og commit PRD-mappen. Rydd først bort arbeidsfiler som ikke skal ligge i det offentlige repoet.

Etter finaliseringen bør briefen oppdateres, siden den fortsatt sier at mange repetisjoner er kjernen.
