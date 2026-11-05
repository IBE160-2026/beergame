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
| 2 | Kvalitetskravene til AI-spillerne | Neste |
| 3 | Testen og KI-vurderingen | Ikke startet |
| 4 | Standardparametre og replay-scenarier | Ferdig |
| Etterpå | Finalisering av PRD-en | Ikke startet |

## Tema 1: Brukerreisene (ferdig)

Founder beskrev en konkret økt, og brukerreisene og kravene ble skrevet om etter det. Runden førte også til disse beslutningene:

- Formell sensur flyttes til v2. V1 får en KI-vurdering som ikke teller, og en PDF-rapport.
- Læreren kan gjøre spillet obligatorisk.
- Veiledende A–F-bokstav kan slås på av lærer eller student.
- Studenten forklarer seg i debriefen.
- V1 har ingen frivillige ekstra runder.

## Tema 2: Kvalitetskravene til AI-spillerne (neste)

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

## Tema 3: Testen og KI-vurderingen

**Mål:** gjøre testen og KI-vurderingen konkrete nok til å bygges.

**PRD:** FR-51 til FR-56, SM-2, SM-7, åpent spørsmål 7.

Spørsmål:

1. Hvilke temaer og spørsmålstyper skal den første spørsmålsbanken ha, og hvem skriver den?
2. Hvor mye skal de tilpassede spørsmålene telle? Utkastet sier 30 %.
3. Skal testen tas under oppsyn, for eksempel i en spilletime, eller hvor som helst?
4. Er 60 minutter og ett forsøk riktig?
5. Hvilke grenser skal gjelde for den veiledende bokstaven?
6. Hvem skårer utvalget som kontrollerer KI-vurderingen (SM-7), og hvordan ser rubrikken ut?

## Tema 4: Standardparametre og replay-scenarier

**Mål:** bekrefte spillverdiene mot kursmaterialet ditt.

**PRD:** FR-11, FR-12, FR-49, åpne spørsmål 5 og 6.

Spørsmål:

1. Stemmer standardverdiene: startlager 12, 4 enheter per plass i forsyningslinjen, etterspørsel 4 som hopper til 8 i uke 5, lagerkostnad 0,50, restordrekostnad 1,00 og 36 uker?
2. Er ordreforsinkelsen 1 eller 2 uker?
3. Hva skal være annerledes i innstillingene for et videregående kurs?
4. Hvordan skal replay-runden gjøres vanskeligere: startbetingelser, etterspørsel eller begge deler?

## Etterpå: Finalisering

Rekkefølgen følger `bmad-prd`:

1. Gå gjennom `.memlog.md`: hver beslutning skal stå i PRD-en eller addendumet, eller være bevisst lagt til side.
2. Avstem PRD-en mot kildene: brief, research, forge-rapport og tidligere planer.
3. Kjør reviewer-pass og løs funnene.
4. Gå gjennom åpne spørsmål og `[ASSUMPTION]`-merker. Det som blokkerer UX og arkitektur, løses først.
5. Språkvask `prd.md` og `addendum.md`.
6. Sett status til `final` og commit PRD-mappen. Rydd først bort arbeidsfiler som ikke skal ligge i det offentlige repoet.

Etter finaliseringen bør briefen oppdateres, siden den fortsatt sier at mange repetisjoner er kjernen.
