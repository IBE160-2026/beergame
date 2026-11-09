# Felles brief, runde 2: 10 elegante, datasentriske konsepter

Grunnleggeren (faglærer og fagperson i logistikk) syntes alle konseptene i runde 1 var «litt barnslige». Miniatyrlandet falt best i smak, men ønsket er noe med preg av **kvalitet og gjennomtenkthet**, størst fokus på **pedagogikk**, der **de faglige prinsippene står i sentrum** og studenten får enkel tilgang til å **se effektene gjennom interessante grafer** som viser svingningene og dataene, og som gir innsikten man trenger for å spille best mulig. Stikkord: **eleganse, enkelhet, datasentrisk.**

Du lager ett av 10 parallelle konsepter. Du får ikke spørre brukeren. **Ikke commit, ikke kjør sesjonslogg, ikke opprett issues:** det gjør hovedagenten.

Les først:
- Denne filen, helt.
- `D:\IBE160\2026\beergame\PRODUCT.md`
- `C:\Users\pape\.claude\plugins\cache\impeccable\impeccable\4.8.0\skills\impeccable\reference\craft-floor.md`
- Invoker `dataviz`-skillen via Skill-verktøyet før du tegner den første grafen, og følg metoden. Hold det innenfor dette konseptets palett.
- `_shared/fixture.json` (les med `encoding="utf-8"`). Alle grafer tegnes fra dette, med en sann skala.
- Se gjerne på Miniatyrlandet fra runde 1 for tonen han likte: `..\..\concepts\04-miniatyrlandet\_png\05-spill.png`. Dette er IKKE stilen du skal lage.

## Hva «barnslig» betyr, og hva vi ikke gjør

Ikke: figurer, tegneseriestrek, piksler, treverk, skeuomorfe instrumenter, rund lekefont, mettede fullflater, kostymeverdener, ikoner som pynt, tykke rammer, «spill»-knapper, belønningsanimasjon, utropstegn, muntre mikrotekster. Metaforen skal aldri bære designet. **Grafen er grensesnittet.**

Heller: Et velredigert fagtidsskrift, en årsrapport fra et godt designbyrå, et norsk designprogram fra et seriøst offentlig kontor, en lærebok fra et universitetsforlag. Stram typografi, luft, få farger med klare roller, presis linjeføring, direkte etiketter framfor forklaringsbokser. Test: En professor kan vise skjermen i plenum uten å unnskylde den.

Unngå også AI-klisjeene: varm krem med serif og terrakotta; nesten-svart med én neon; avisstil med hårstreker, kursiv displayserif og små sperrede mono-etiketter.

## De faglige prinsippene (kjernen i hele oppgaven)

Hver graf skal lære bort minst ett prinsipp, merket i `concept.md` og `10-pedagogikk.svg`.

- **P1 Lager er en opphopning.** Lager endres med inn minus ut. Forskning: mange kloke voksne bryter dette (89 % brøt materialbalansen i Bathtub-oppgaven; de antar at beholdningen ser ut som strømmen, «correlation heuristic»). Grafen må gjøre balansen synlig: inn og ut og lageret i samme tidsakse, slik at arealet mellom inn og ut er endringen i lageret.
- **P2 Forsinkelse.** En ordre kommer fram etter om lag 4 uker. Årsak og virkning er adskilt i tid, så det du ser nå kommer av det du gjorde før.
- **P3 Det som er på vei blir glemt.** Klassisk funn: spillere legger lite vekt på det som allerede er bestilt (Sterman: vekten på forsyningslinja er klart under 1). **Posisjon = Lager − Restordre + På vei.** Dette er den viktigste innsikten for å spille bra.
- **P4 Ordrer er ikke etterspørsel.** Hvert ledd ser bare ordrene fra nedstrøms, ikke kundene. Informasjon forvrenges opp gjennom kjeden.
- **P5 Forsterkning og faseforskyvning.** Svingningene vokser oppstrøms og kommer senere (spill 17: 1,8× → 4,1× → 6,0× → 7,6×).
- **P6 Struktur gir atferd.** Nesten alle grupper svinger likt (60 spill). Forklar med struktur, aldri skyld. Målet er at studenten slutter å spørre «hadde jeg rett?» og begynner å spørre «hvorfor skjedde det?».
- **P7 Overreaksjon forsterker også.** Å regne med det som er på vei er ikke nok: i simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17. Rolig tilpasning og å telle det som er på vei må til sammen. Hold deg til denne nyansen.
- **P8 Restordre koster dobbelt.** Restordre 1,00, lager 0,50 per enhet per uke, og målet er lavest kostnad for HELE kjeden.

Testforskningen sier: «det svinger» er det lett å huske, mens materialbalanse og konsistens mellom grafer viser forståelse. Vis derfor tall og grafer som stemmer med hverandre, og legg merke til at det er regnestykket og ikke bare mønsteret som er poenget.

## Produktsannhet som ikke kan brytes

- **Én beslutning per Uke:** ett heltall. Studenten bestemmer, systemet regner. Etter bekreftelse kan ordren ikke endres. Beslutningen må fortsatt kunne tas på sekunder.
- **Alle seter bestiller i samme Uke.** Uka går videre når alle har bestilt. Spillet viser hvem det venter på, med Rolle og navn eller «KI-spiller», og hvor lenge.
- **Et sete ser på sin egen skjerm:** lager eller restordre, innkommende ordre, innkommende levering, sendt denne uka, det som er på vei, egen ordrehistorikk, løpende totalkostnad og ukenummer. Alt pluss ordre-input skal kunne nås på 360 px bredde uten sideveis scrolling.
- **Under spillet kan grafer bare vise setets egne data.** Høyre kant på tidsaksen er **nå**. Tidsaksen viser aldri en slutt, antall uker eller framdrift. Skriv aldri «11 av 36». Sara er Grossist, så hun ser ikke kundeetterspørselen og heller ikke andres lager. Innkommende ordre er ikke merket som etterspørsel.
- **Framover i tid:** Du kan vise kjente ankomster og en utregnet projeksjon, men det må stå at det ikke er garantert (leverandøren kan mangle varer; 24 bestilt ble 17 levert i Uke 15). Projeksjon bygger bare på setets egne tall.
- **Ingen anbefalt ordre under spillet.** Vis regnestykket og konsekvensen, aldri fasiten. Studenten bestemmer. Det er forskjell på å gjøre posisjonen synlig og å si hva som er riktig.
- **Ingen chat** mellom spillere. Ingen rangering eller premier for studenter. Lærer kan se kostnad per spill.
- **KI er alltid merket:** KI-spillere, overtatte seter, KI-generert tekst. **Rolle og status vises aldri med farge alene.**
- **Navnet «Beer Game» / «ølspillet» / «øl» brukes ikke før Debriefen,** heller ikke på landingssiden. Vi sier «enheter» eller «kasser». Debriefen kan navngi øvelsen.
- **Landingssiden:** ingen kunder, sitater, priser eller læringsresultater. Ikke ordet «bullwhip». Ikke vis firerollers forsterkning eller hoppet i etterspørselen, for studenter kan se siden. Du kan vise ett setes egne grafer og lærerens oversikt. Primærhandling «Be om lærertilgang», sekundær «Logg inn». Fakta: kjører hele øvelsen fra invitasjon til PDF-rapport; klasser på rundt 250 studenter; alle spillene på én skjerm; KI-spillere fyller tomme seter; ett fravær stopper ikke gruppa; ingen spill blir stående uferdig; på mobil; på norsk; studentlisten fra Canvas-eksport.
- **KI-vurderingen** teller ikke, er aldri en karakter, og sier det der den vises.
- **Debriefen:** Forklaring skrives FØR etterspørselen avsløres. Alle tall fra loggen. Stemme: direkte, konkret, andre person, ingen skyld, ingen tom ros. KI-tekst merkes «KI-generert, kan ta feil».
- Merk tall med en liten linje «Demodata». Simulerte referanser merkes «Simulert». Produktnavn er ikke bestemt: bruk konseptets arbeidsnavn.

## Hjelpegrad: ta et standpunkt

Her er en reell spenning. Studenten må først oppleve svingningene for at Debriefen skal gi læring. Grafer som gjør feilen for lett å unngå kan svekke nettopp det (issue #22). Grunnleggeren vil samtidig ha grafer som gir innsikt i å spille godt. Hvert konsept skal svare på dette i `concept.md`, under **Hjelpegrad:**: hva vises i Klassespillet, hva vises i Replay, og hvorfor. Et legitimt grep er at grafer og begreper **låses opp etter Debriefen**, slik at Replay er der studenten bruker innsikten. Vis forskjellen på minst én tegning.

## Norske begreper (bokmål)

Faglærer, Klasse, Klasseliste, Invitasjon, Klasseøkt, Spillinnstillinger, Klassespill, Sete, Rolle: Detaljist, Grossist, Distributør, Fabrikk. Uke, Ordre, Lager, Restordre, På vei, Posisjon, Totalkostnad, Veiledede uker, Pause, KI-spiller, KI overtar, Ta tilbake setet, Labtime, Startoppgave, Debrief, Forklaring, Debrief-quiz, Replay, Individuell test, KI-vurdering, Studentrapport, Oversikt, Klasserapport, Spillinnsikt, Melding, Spillfrist, Debrief-frist, Testfrist, Forsterkning.

## Data i fixture.json

- `spill17`: Hele det spilte spillet. `serier` har `demand` og per Rolle lister på 36 uker (`ordre`, `lager`, `restordre`, `innkommende_ordre`, `levering`, `paa_vei`, `kost_sum`; indeks 0 er Uke 1). Også `forsterkning`, `kost_per_rolle`, `kjedekost` (2 266,00).
- `bare_sara_teller_paa_vei`: Simulert: samme kjede, men Grossist regner med alt på vei. Kjede 1 507,00, Grossist-kostnad 464,50 (mot 553,50) og forsterkning 2,2× (mot 4,1×). Viser sammenhengen, ikke en fasit.
- `alle_teller_paa_vei`: Simulert referanse med rolig regel for alle fire. Kjede 1 341,00, Fabrikk 3,3×. Regelen er valgt for å illustrere, så kall den aldri optimal eller fasit.
- `replay_sara`: Saras Replay: Tilfeldig etterspørsel, 33 uker, tre KI-spillere. «Ikke like for like.»
- `klasse.spill`: 60 Klassespill med `spill`, `status` (`ferdig`, `pågår`, `pauset`, `venter`), `uke`, `kjedekost`, `ki_seter`, `venter_paa`, `navn`, `ventet_timer`, `fortsetter`, og **ekte serier**: `ordre` og `netto_lager` per Rolle fram til gjeldende uke. Ferdige har også `forsterkning` og `kost_per_rolle`.
- `klasse.ferdige`: Kvartiler for kjedekost og forsterkning per Rolle. `klasse.moenstre`: antall Detected patterns. `klasse.fjoraaret`: fjorårets klasse.
- `klasse.traktA`, `klasse.roster`: trakt og klasseliste.

**Personer:** Sara (Grossist, spill 17), Ida (Detaljist), Mikkel (Distributør), Jonas (Fabrikk). Faglærer Bård. Klasse `class-of-1994`, IBE160.

**Saras skjerm, Uke 11:** Lager 0 · Restordre 13 · Innkommende ordre 8 · Levering 4 · Sendt 4 · På vei 16 · Neste levering 4 · Totalkostnad 68,00 kr. Posisjon = 0 − 13 + 16 = **3**. Sara taster **24**, og da blir posisjonen 27. Ordrehistorikk uke 1 til 10: 4, 4, 4, 4, 4, 4, 4, 4, 4, 8. Uke 1 til 4 er Veiledede uker. Senere går restordre opp mot 40 og lager opp mot 30: grafene må tåle skalaen.

**Venter på:** Ida har bestilt, Mikkel har bestilt, Jonas venter (3 min), Sara venter (deg).

**Slutt:** Kjeden 2 266,00 kr. Detaljist 342,00 · Grossist 553,50 · Distributør 691,00 · Fabrikk 679,50. Forsterkning 1,8× · 4,1× · 6,0× · 7,6×. Kundeetterspørsel: 4 per uke, hopper til 8 i uke 5, deretter stabil.

**Oversikt:** 60 Klassespill. 41 ferdig, 15 pågår (herav 2 pauset), 4 venter. Spill 2 venter på Noah (Grossist) i 23 t, like før KI overtar ved 24 t. Trakt: registrert 240 → klassespill ferdig 164 → debrief ferdig 121 → quiz bestått 97 → replay ferdig 58 → test levert 12 → KI-vurdering klar 0.

**Klasseliste:** 250 rader fra Canvas-eksport, 4 ugyldige adresser (rad 37, 88, 141, 203), 238 registrert, 2 manuelt registrert, 10 uregistrert. Invitasjon gyldig i 14 dager.

**Klasseøkt, standarder («Klassisk»):** startlager 12, 4 enheter i hvert ledd, ordreforsinkelse 2, fraktforsinkelse 2, produksjonsforsinkelse 2 uker, etterspørsel 4 → 8 i uke 5, lagerkost 0,50, restordrekost 1,00, 36 uker, Veiledede uker 1–4, KI-modus LLM-spillere, Gruppedebrief, Inaktivitetsgrense 24 t. Skjermen sier at kildene er uenige om forsinkelser og at dette er produktets standard. Merket «Obligatorisk». 240 studenter fordeles tilfeldig i 60 spill à 4.
**Datoer:** Start ti. 24. nov 2026 · Spillfrist ti. 8. des · Debrief-frist fr. 11. des · Testfrist fr. 18. des. **Labtimer:** to. 26. nov 14:15, ma. 30. nov 10:15, to. 3. des 14:15, ma. 7. des 10:15, Datalab A2.

## Leveranse: 10 SVG-filer + concept.md i din mappe

| Fil | Innhold | Lerret |
|---|---|---|
| `10-pedagogikk.svg` | **VIKTIGST.** Konseptets grafgrammatikk: samme grafer for Sara ved Uke 5, 11, 18 og 29, slik at svingningene blir synlige over tid. Merk hvilket prinsipp (P1–P8) hver graf lærer bort og hvilken innsikt den gir for neste ordre. Inkluder sammenligningen med en simulert referanse slik den vises etter Debriefen. | 2000×1400 |
| `05-spill.svg` | **HOVEDSKJERMEN.** Telefon (390×844) midt i Uke 11 med 24 tastet inn, og laptop. Telefonen skal ha én hovedgraf, luft, og ikke virke tett: legg detaljer bak ett trykk (vis det åpnede panelet ved siden av). | 1600×1000 |
| `06-spilldynamikk.svg` | 6 telefonruter med korte notater: (A) Uka åpner. (B) Beslutningen: 24 med 16 på vei. (C) Bekreftet, venter på de andre. (D) Uka går videre, kan hoppes over, aldri over 2 sek. (E) Jonas er borte: Pause og KI-spiller, merket, og «Ta tilbake setet». (F) Spillet slutter: kjedens totalkostnad først, så per Rolle, videre til Debrief. Under: 3–4 setninger om hva spilleren lærer av å se grafen uke for uke. | 2100×1200 |
| `07-debrief.svg` | Gruppedebrief i 5 steg + delt skjerm: (1) skriv Forklaring, avsløringen er låst; (2) **klimaks: etterspørselen avsløres**; (3) alle fire Rollers ordre i én graf, forsterkning 1,8× → 7,6×; (4) ditt øyeblikk: Uke 11, hva du så, hva du bestilte, hva det kostet senere, og hva de andre Rollene så, med sammenligning mot simulert referanse; (5) quiz med feil svar forklart. Dette er konseptets faglige høydepunkt. | 2100×1200 |
| `08-laerer-oversikt.svg` | Faglærer holder 60 spill på sporet på én 1440-skjerm: status, hvem hvert spill venter på og hvor lenge, pause, KI-seter, nær overtakelse uthevet, trakten, send Melding, filtrering. Bruk de ekte seriene: læreren skal se svingningene i klassen, ikke bare statuser. | 1600×1000 |
| `01-landing.svg` | Landingsside for faglærere: første skjermbilde + starten av neste seksjon. Lar en elegant graf bære siden. | 1440×1200 |
| `02-laerer-klasse.svg` | Lag Klasse: navn og emnekode, last opp Canvas-fil, velg e-postkolonne, ugyldige rader per rad, send Invitasjoner, status. | 1440×1000 |
| `03-laerer-spill.svg` | Klasseøkt: forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer, fordelingsforhåndsvisning (60 spill à 4, kjør på nytt, bekreft). Kan lagres uten endring. | 1440×1100 |
| `04-student-hjem.svg` | Sara på mobil: spill og Rolle, setene, de seks stegene (Klassespill, Debrief, Quiz, Replay, Individuell test, Rapport), neste frist, Labtimer, «spillet venter på deg». To telefoner: registrering og hjem under spill. | 1000×900 |
| `09-alle-sider.svg` | Kontaktark over ALLE andre sider på lavere detaljnivå, gruppert per rolle, med tittel og én linje: Student: Invitasjon og registrering, Logg inn, Regler før første ordre, Startoppgave, Replay, Replay-gjennomgang, Individuell test (flervalg, interaktiv tegne-/tabelloppgave, langsvar), KI-vurdering, Studentrapport (PDF), Alle spill side om side. Faglærer: Lærerhjem, Klasserapport, Spillinnsikt (uke for uke), Studentside, Alle spill i plenum, Tverrklasse-statistikk, Meldinger, Lærers testspill. Admin: Admin-område, Brukere og roller, KI-kostnad. | 2000×1400 |
| `concept.md` | Se mal nederst. | |

## Designkrav

- **Enkelhet:** Ett hovedbudskap per flate. Hver skjerm har én tydelig graf eller tabell. Det som kan fjernes, fjernes. Tall som ikke brukes i beslutningen ligger bak ett trykk. Bruk færre farger enn du tror: en grunn, en tekstfarge, en til to datafarger, ett signal.
- **Grafkvalitet:** direkte etiketter i stedet for forklaringsbokser, svak hjelpelinje, tabellsifre, sann null, felles tidsakse mellom grafer, et tydelig «nå». Teksten forklarer hva grafen viser, ikke at den er en graf. Tegn gjerne komposisjoner som er uvanlige, men sanne.
- **Lærerflater** er Operate: skanning på sekunder. **Spill og Debrief** er kjernen: Grafen leder. **Landing** er Persuade: tydelig hovedhandling, og en graf som viser noe bare dette produktet kan.
- **Forbudt:** eyebrow/kicker over overskrifter, gradienttekst, emoji eller unicode-tegn som ikon (tegn ikoner som SVG-former, helst ingen ikoner), like kort med ikon + tittel + tekst, hero-metric-malen, seksjonsnummer som pynt, tykk farget kant på kortenes side, hard offset-skygge, dekorative skygger, kopier av eksisterende merker eller spill.
- **Fontvalg:** Ikke bruk: Fraunces, Playfair Display, Cormorant, Lora, Crimson, Newsreader, Syne, Space Grotesk, Space Mono, IBM Plex, Inter, DM Sans, DM Serif, Outfit, Plus Jakarta Sans, Instrument Sans. Må ha tabellsifre og norske tegn. Sjekk æ, ø, å i renderen.
- **Lesbarhet:** minst 13 px tekst på telefonskjermer (390-skala), kontrast ≥ 4,5:1 for brødtekst. Mindre tekst er greit på kontaktarket.
- **Tekst:** Ekte, kort norsk fagtekst. Ingen lorem ipsum. Knapper sier hva som skjer.

## Tekniske krav til SVG

1. **Generer med `build.py` i din mappe** (`uv run python build.py`). Les tall fra `../_shared/fixture.json`, med hjelpefunksjoner for skala, akser, linjer og tekstbryting. Ingen tall i grafer tastes inn for hånd.
2. Hver fil: gyldig, frittstående `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" font-family="...">` med `<title>` og `<desc>` på norsk.
3. **Prefiks alt:** CSS-klasser begynner med `dNN-` (NN = konseptnummer), `id`-er med `dNN-<side>-`. Ingen selektorer på bare elementnavn. Ingen `<script>`.
4. **Fonter:** Øverst i `<style>`: `@import url('https://fonts.googleapis.com/css2?family=...&amp;display=swap');` med ekte fallback. Bare Google Fonts. Ingen eksterne bilder.
5. **Tekst må passe.** SVG bryter ikke linjer selv. Bruk en bryte-hjelper og god plass.
6. **Verifiser ved å se.** `uv run python ../_shared/render.py .` fra mappa di validerer XML og lager `_png/<navn>.png`. Åpne PNG-ene med Read, se etter overlapp, klipping, feil font og tett layout, og rett i bolker. Maks to synsrunder per fil, utenom `05`, `06`, `07` og `10`, som får tre.
7. Telefoner i 390×844-skala med diskret ramme. Ingen fotorealistiske mockups.

## concept.md-mal

```markdown
# <nummer> <Navn>
**Tese (én setning):** …
**Faglig kjerne:** hvilke prinsipper (P1–P8) konseptet gjør best, og med hvilken graf.
**Spilldynamikk:** 3–4 setninger om hva studenten gjør, ser og forstår i en Uke, og hvordan grafen hjelper neste ordre.
**Hjelpegrad:** hva vises i Klassespillet, hva vises i Replay, og hvorfor.
**Debrief-grep:** én setning.
**Lærerflate-grep:** én setning.
**Palett:** navngitte farger med hex. **Typografi:** fonter og roller.
**Styrke:** … **Ærlig risiko:** …
**Gjenbrukbart selv om konseptet velges bort:** én idé.
```

## Rapport tilbake

Maks 8 linjer: mappe, filer, hva du faktisk så i renderen, kjente svakheter, og om alle 10 SVG-er validerte. Ikke lim inn SVG eller kode.
