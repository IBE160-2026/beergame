# Felles brief: 10 SVG-designkonsepter for beergame

Du lager ett av 10 parallelle konsepter. Grunnleggeren (faglærer) vurderer alle 10 samlet og velger hvilke vi driller inn i. Konseptene skal være **bredt forskjellige i kreativitet og i selve spillfølelsen**, ikke fargevarianter av samme skjerm. **Spilldynamikken er det viktigste.** Du får ikke spørre brukeren om noe.

Les før du tegner:
- Denne filen, helt.
- `D:\IBE160\2026\beergame\PRODUCT.md`
- `C:\Users\pape\.claude\plugins\cache\impeccable\impeccable\4.8.0\skills\impeccable\reference\craft-floor.md`
- Ved behov: `D:\IBE160\2026\beergame\.docs\planning-artifacts\prds\prd-beergame-2026-10-29\prd.md` (§2.3 reiser, §3 ordliste, §4.5 spill, §4.9 debrief). Bruk Grep eller les deler av den.
- `_shared/fixture.json` (les med `encoding="utf-8"`): tallene alle konseptene skal bruke.

## Produktsannhet som ikke kan brytes

- **Én beslutning per Uke:** ett heltall. Studenten bestemmer, systemet regner. Etter bekreftelse kan ordren ikke endres.
- **Alle seter bestiller i samme Uke.** Uka går videre når alle har bestilt. Spillet viser hvem det venter på, med Rolle og navn eller «KI-spiller», og hvor lenge.
- **Et sete ser på sin egen skjerm:** lager eller restordre, innkommende ordre, innkommende levering, sendt denne uka, det som er på vei, egen ordrehistorikk, løpende totalkostnad og ukenummer. Alt pluss ordre-input skal synes på 360 px bredde uten sideveis scrolling.
- **Skjult:** antall uker og hvor mange som gjenstår (vis «Uke 11», aldri «11 av 36» og aldri framdrift mot slutten), kundeetterspørselen (bare Detaljist ser den, én uke om gangen), andre seters lager og ordre.
- **Ingen chat** mellom spillere. Ingen rangering eller premier for studenter. Lærerens oversikt kan vise kostnad per spill.
- **KI er alltid merket:** KI-spillere, overtatte seter og KI-generert tekst. Merket er alltid mer enn farge.
- **Rolle og status vises aldri med farge alene** (form, tekst, ikon eller mønster i tillegg).
- **Navnet «Beer Game» / «ølspillet» / «øl» brukes ikke i produkttekst før Debriefen,** heller ikke på landingssiden. Vi sier «kasser» eller «enheter». Debriefen kan navngi øvelsen.
- **Landingssiden påstår ingenting udokumentert:** ingen kunder, sitater, priser eller læringsresultater. Ikke ordet «bullwhip», og ikke avslør at etterspørselen hopper. Ingen åpen registrering: primærhandlingen er «Be om lærertilgang», sekundær «Logg inn». Ekte fakta å bruke: kjører hele øvelsen fra invitasjon til PDF-rapport; klasser på rundt 250 studenter; alle spillene på én skjerm; KI-spillere fyller tomme seter; ett fravær stopper ikke gruppa; ingen spill blir stående uferdig; spilles på mobil; på norsk; studentlisten lastes opp fra Canvas-eksport.
- **KI-vurderingen** teller ikke, er aldri en karakter, og sier det der den vises.
- **Debriefen** forklarer gjennom struktur, ikke personer: direkte, konkret, andre person, ingen skyld, ingen tom ros. Sekvens: Forklaring skrives FØR etterspørselen avsløres.
- Merk demodata tydelig med en liten linje: «Demodata» på hver side med tall.
- Produktnavn er ikke bestemt. Bruk konseptets arbeidsnavn, som ikke må avsløre øvelsen.

## Norske begreper (bokmål, bruk disse)

Faglærer, Klasse, Klasseliste, Invitasjon, Klasseøkt, Spillinnstillinger, Klassespill, Sete, Rolle: Detaljist, Grossist, Distributør, Fabrikk. Uke, Ordre, Lager, Restordre, På vei, Totalkostnad, Veiledede uker, Pause, KI-spiller, KI overtar, Ta tilbake setet, Labtime, Startoppgave, Debrief, Forklaring, Debrief-quiz, Replay, Individuell test, KI-vurdering, Studentrapport, Oversikt, Klasserapport, Melding, Spillfrist, Debrief-frist, Testfrist.

## Demodata (hele historien ligger i fixture.json)

**Personer:** Sara (Grossist, spill 17), Ida (Detaljist), Mikkel (Distributør), Jonas (Fabrikk). Faglærer Bård. Klasse `class-of-1994`, IBE160.

**Saras skjerm, Uke 11:** Lager 0 · Restordre 13 · Innkommende ordre 8 · Levering 4 · Sendt 4 · På vei 16 · Neste levering 4 · Totalkostnad 68,00 kr. Sara taster **24** (dette er øyeblikket Debriefen senere peker på). Ordrehistorikk uke 1 til 10: 4, 4, 4, 4, 4, 4, 4, 4, 4, 8. Uke 1 til 4 er Veiledede uker. Uke 12 står i fixture.json.

**Venter på:** Ida har bestilt, Mikkel har bestilt, Jonas venter (3 min), Sara venter (deg).

**Slutt:** Kjeden totalt 2 266,00 kr. Per Rolle: Detaljist 342,00 · Grossist 553,50 · Distributør 691,00 · Fabrikk 679,50. Ordreforsterkning: Detaljist 1,8× · Grossist 4,1× · Distributør 6,0× · Fabrikk 7,6×. Kundeetterspørsel: 4 per uke, hopper til 8 i uke 5, deretter stabil.

**Oversikt:** 60 Klassespill. 41 ferdig, 15 pågår (herav 2 pauset), 4 venter. Spill 2 venter på Noah (Grossist) i 23 t, like før KI overtar ved 24 t. Trakt: registrert 240 → klassespill ferdig 164 → debrief ferdig 121 → quiz bestått 97 → replay ferdig 58 → test levert 12 → KI-vurdering klar 0.

**Klasseliste:** 250 rader fra Canvas-eksport, 4 ugyldige adresser (rad 37, 88, 141, 203), 238 registrert, 2 manuelt registrert, 10 uregistrert. Invitasjon gyldig i 14 dager.

**Klasseøkt, standarder («Klassisk»):** startlager 12, 4 enheter i hvert ledd, ordreforsinkelse 2 uker, fraktforsinkelse 2 uker, produksjonsforsinkelse 2 uker, etterspørsel 4 → 8 i uke 5, lagerkost 0,50, restordrekost 1,00, 36 uker, Veiledede uker 1–4, KI-modus LLM-spillere, Debrief-modus Gruppedebrief, Inaktivitetsgrense 24 t. Skjermen sier at kildene er uenige om forsinkelser og at dette er produktets standard. Merket «Obligatorisk». 240 studenter blir tilfeldig fordelt i 60 spill à 4.
**Datoer:** Start ti. 24. nov 2026 · Spillfrist ti. 8. des · Debrief-frist fr. 11. des · Testfrist fr. 18. des. **Labtimer:** to. 26. nov 14:15, ma. 30. nov 10:15, to. 3. des 14:15, ma. 7. des 10:15, Datalab A2.

## Leveranse: 9 SVG-filer + concept.md i din mappe

| Fil | Innhold | Lerret (viewBox) |
|---|---|---|
| `01-landing.svg` | Offentlig landingsside for faglærere. Første skjermbilde + starten av neste seksjon. Viser mekanismen, ikke en stemning. | 1440×1200 |
| `02-laerer-klasse.svg` | Faglærer lager Klasse: navn og emnekode, last opp Canvas-fil, velg e-postkolonne, ugyldige rader listet per rad, send Invitasjoner, status (sendt/akseptert/utløpt). | 1440×1000 |
| `03-laerer-spill.svg` | Faglærer setter opp Klasseøkt: forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer, fordelingsforhåndsvisning (60 spill à 4, kjør på nytt, bekreft). Skal kunne lagres uten endring. | 1440×1100 |
| `04-student-hjem.svg` | Sara på mobil: Spill 17 og Rolle, de andre setene, de seks stegene (Klassespill, Debrief, Quiz, Replay, Individuell test, Rapport), neste frist, Labtimer, «spillet venter på deg». To telefoner: venstre registrering/første møte, høyre hjem under spill. | 1000×900 |
| `05-spill.svg` | **HOVEDSKJERMEN.** Spillskjermen på telefon (390×844 stor og tydelig) midt i Uke 11 med 24 tastet inn, pluss samme skjerm på laptop eller nettbrett. | 1600×1000 |
| `06-spilldynamikk.svg` | **VIKTIGST.** Storyboard av spillets dynamikk i 6 telefonruter med korte norske notater: (A) Uka åpner: levering og ordre kommer inn. (B) Beslutningen: 24 med 16 på vei. (C) Bekreftet: venter på de andre. (D) Uka går videre: overgangen, kan hoppes over, aldri over 2 sek. (E) Jonas er borte: Pause og KI-spiller som tar setet, merket, og «Ta tilbake setet». (F) Spillet slutter: kjedens totalkostnad først, så per Rolle, videre til Debrief. Under rutene: 3–4 setninger om hva som gjør denne spillefølelsen unik. Bruk gjerne SMIL-animasjon for flyten, men hver ramme skal være lesbar i stillstand. | 2100×1200 |
| `07-debrief.svg` | Gruppedebrief i 5 steg som telefonruter + én delt skjerm: (1) skriv Forklaring, avsløringen er låst; (2) **klimaks: etterspørselen avsløres**, liten endring fra 4 til 8; (3) ordrer per Rolle over tid i ett diagram, forsterkning 1,8× → 7,6×; (4) ditt øyeblikk: Uke 11, hva du så, hva du bestilte, hva det kostet senere, og hva de andre Rollene så; (5) quiz med feil svar forklart. Merk KI-tekst: «KI-generert, kan ta feil». | 2100×1200 |
| `08-laerer-oversikt.svg` | Faglærer holder 60 spill på sporet på én skjerm, 1440 bred laptop: status for alle 60, hvem hvert spill venter på og hvor lenge, pause, KI-seter, nær overtakelse uthevet, trakten, send Melding, Filtrering. Må kunne skannes på sekunder. | 1600×1000 |
| `09-alle-sider.svg` | Kontaktark som skisserer ALLE andre sider på lavere detaljnivå i konseptets språk, gruppert per rolle, med tittel og én linje per side: Student: Invitasjon og registrering, Logg inn, Regler før første ordre, Startoppgave, Replay, Replay-gjennomgang, Individuell test (flervalg, interaktiv tegne-/tabelloppgave, langsvar), KI-vurdering, Studentrapport (PDF), Alle spill side om side. Faglærer: Lærerhjem med klasser, Klasserapport, Spillinnsikt (uke for uke), Studentside, Spill alle side om side for plenum, Tverrklasse-statistikk, Meldinger, Lærers testspill. Admin: Admin-område, Brukere og roller, KI-kostnad. | 2000×1400 |
| `concept.md` | Se mal nederst. | |

## Designkrav

- **Moder:** Landing er Persuade: verdenen bærer hele siden, tydelig hovedhandling, leseorden som fungerer, og viser noe bare dette produktet kan. Spill og Debrief er Experience: verdenen leder, full forpliktelse. Lærerflatene er Operate: presisjon og skannbarhet går foran uttrykk, men de skal åpenbart høre til samme verden, ikke være en generisk SaaS-tabell med tema på toppen.
- **Spillet må føles.** Konseptets metafor skal bære selve tallene (lager, restordre, på vei), ikke være pynt rundt et skjema. En student skal forstå «jeg bestilte for mye fordi jeg ikke så det som var på vei» med øynene.
- **Tilbakeføring:** Spill-språket må tåle 36 uker og flere kvelder. Beslutningen må ta sekunder.
- **Tekst:** Bare ekte norsk produkttekst. Kort. Knapper sier hva som skjer. Ingen lorem ipsum, ingen placeholder-bokser utenom i 09-kontaktarket der lavdetalj er greit.
- **Forbudt:** eyebrow/kicker over overskrifter, gradienttekst, emoji eller unicode-tegn som ikon (tegn ikoner som SVG-former), like kort med ikon + tittel + tekst som sidestruktur, hero-metric-malen, seksjonsnummer som pynt, tykk farget kant på kortenes side, hard offset-skygge utenfor en verden som faktisk krever det, kopier av eksisterende spill, merker eller figurer.
- **Fontvalg:** Velg ansikter med et ståsted fra konseptets verden. Ikke bruk: Fraunces, Playfair Display, Cormorant, Lora, Crimson, Newsreader, Syne, Space Grotesk, Space Mono, IBM Plex, Inter, DM Sans, DM Serif, Outfit, Plus Jakarta Sans, Instrument Sans.
- **Lesbarhet:** minst 13 px tekst på telefonskjermene (i 390-skala), kontrast ≥ 4,5:1 for brødtekst. Diagrammer tegnes til skala fra fixture.json.

## Tekniske krav til SVG

1. **Generer med et Python-skript** `build.py` i din mappe (kjør med `uv run python build.py`). Les tallene fra `../_shared/fixture.json`, slik at grafene er sanne, og bruk hjelpefunksjoner for gjentatte deler. Ikke tegn 60 spill for hånd.
2. Hver fil: ren, gyldig, frittstående `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" font-family="...">` med `<title>` og `<desc>` på norsk.
3. **Prefiks alt:** Alle CSS-klasser begynner med `cNN-` (NN = konseptnummer) og alle `id`-er med `cNN-<side>-` (f.eks. `c05-spill-gradA`). SVG-ene settes inn inline i samme HTML-side, så CSS uten prefiks eller gjenbrukte id-er vil krasje med andre sider. Ingen selektorer på bare elementnavn. Ingen `<script>`.
4. **Fonter:** Øverst i `<style>`: `@import url('https://fonts.googleapis.com/css2?family=...&display=swap');` med ekte fallback-stack. Bare Google Fonts. Ingen eksterne bilder. Alle grafikker er egentegnede vektorer. `<text>` er ekte tekst, ikke paths.
5. **Tekst må passe.** SVG bryter ikke linjer selv. Skriv en hjelpefunksjon for manuell linjebryting, og ha god plass, for lengden varierer med font.
6. **Verifiser ved å se.** Kjør `uv run python ../_shared/render.py .` fra mappa di. Den validerer XML og lager `_png/<navn>.png` via headless Edge. Åpne PNG-ene med Read-verktøyet og se etter overlapp, klipping, feil font, kollisjon og ulogiske tall. Batch rettelsene. Maks to runder med syn per fil, utenom `05` og `06`, som får tre. Se alltid på resultatet minst én gang.
7. Bruk 390×844-skala for telefoner, med en enkel ramme. Ingen fotorealistiske mockups av kjente merker.

## concept.md-mal

```markdown
# <nummer> <Navn>
**Tese (én setning):** …
**Spilldynamikk:** 3–4 setninger om hva spilleren gjør, ser og føler i en Uke, og hvordan metaforen bærer lager/restordre/på vei.
**Debrief-grep:** én setning.
**Lærerflate-grep:** én setning.
**Palett:** navngitte farger med hex. **Typografi:** fonter og roller.
**Styrke:** … **Ærlig risiko:** …
**Gjenbrukbart selv om konseptet velges bort:** én idé.
```

## Rapport tilbake

Maks 8 linjer: mappe, filer laget, hva du faktisk så i renderen, kjente svakheter, og om alle 9 SVG-er validerte. Ikke lim inn SVG eller kode. Si fra om noe du ikke rakk.
