# Felles brief, runde 3: Meteogrammet med kjede, matrise og kostnad

Grunnleggeren (faglærer og fagperson i logistikk) har valgt retning etter runde 2. Beslutningene står ordrett i `D:\IBE160\2026\beergame\.docs\planning-artifacts\ux-designs\ux-beergame-2026-11-05\decisions.md`. Les den først. Kort:

- **Hoveddesign: 02 Meteogrammet.** Det overordnede designet hentes herfra: farger, tekststørrelser, typografi, luft og tone. Debriefen var veldig bra, og Klasseøkt (oppsett av spill) var bra.
- **Tillegg 1, fra 04 Strukturen:** forsyningskjedevisningen øverst ("fronten"), som gir oversikt over selve flyten av varer, med grafene under.
- **Tillegg 2, fra 06 Matrisen:** matrisevisningen som viser selve tallene og gir god innsikt. Den kan ligge under kjedevisningen eller være en alternativ visning. Den er særlig god som aggregert visning for klassen. Grunnleggeren vil ha **både tall og grafer**.
- **Tillegg 3, fra 10 Kostnadskurven:** et skikkelig kostnadsbilde. Målet med hele spillet er å redusere kostnadene, gjerne som **aggregert kostnad**.

Runde 3 er altså ikke 10 nye retninger, men **10 ulike svar på hvordan disse fire delene settes sammen til ett produkt**. Alle 10 konsepter bruker Meteogrammets visuelle språk. Det som skiller dem, er komposisjonen, hva som leder på hver flate, og hvor dypt hvert tillegg går. Hvert konsept har fått en egen vinkel (se tabellen under). Hold deg til den, så gallerimøtet gir reelle valg.

Du lager ett av 10 parallelle konsepter. Du får ikke spørre brukeren. **Ikke commit, ikke kjør sesjonslogg, ikke opprett issues:** det gjør hovedagenten.

Les først:
- Denne filen, helt, og `decisions.md` (sti over).
- `D:\IBE160\2026\beergame\PRODUCT.md`
- `C:\Users\pape\.claude\plugins\cache\impeccable\impeccable\4.8.0\skills\impeccable\reference\craft-floor.md`
- Invoker `dataviz`-skillen via Skill-verktøyet før du tegner den første grafen, og følg metoden. Kjør palett-validatoren på nye farger du innfører (f.eks. matrisens trinn).
- `_shared/fixture.json` (les med `encoding="utf-8"`). Alle grafer tegnes fra dette, med en sann skala.
- **Forbildene fra runde 2** (alle i `..\..\concepts-r2\`). Se på PNG-ene i `_png/` og les `concept.md`:
  - `02-meteogrammet\` er grunnlaget. Se særlig `05-spill`, `07-debrief`, `03-laerer-spill` og `10-pedagogikk`. Koden (`d02lib.py`, `screens_*.py`, `build.py`) kan du **kopiere inn i din egen mappe og bygge videre på**. Det sparer tid og gir riktig stil. Bytt prefiks `d02-` til ditt eget overalt. Ikke importer på tvers av mapper.
  - `04-strukturen\` for kjedevisningen: `01-landing` og `05-spill` (beholdninger som bokser på sann skala, strømmer med ventil, «om lag 4 uker», verdier festet til nodene med hjelpelinjer, og grafene under).
  - `06-matrisen\` for matrisen: `05-spill`, `07-debrief` og særlig `08-laerer-oversikt` (60 spill × uker).
  - `10-kostnadskurven\` for kostnadsbildet: `05-spill`, `07-debrief`, `08-laerer-oversikt` og `10-pedagogikk` (V-en, Totalkostnad over tid, «kostnad på snittet mot det du betalte», kjedekost per spill mot fjoråret).

## Det faste: Meteogrammets visuelle språk

Dette deler alle 10 konsepter. Avvik bare der vinkelen din krever det, og skriv i så fall hvorfor i `concept.md`.

- **Palett (fra 02):** Hvit #FFFFFF, marine #0F2A47 (tekst og ordre), sekundær #44586F, dempet #5E6F82, rolig blå #2B6CA3 med fyll #CDDFEE (over null, lager), dempet rød #B5423A med fyll #F0D5D2 (under null, restordre), grå #6B7785 (projeksjon), stolpegrå #B4C4D4 og #5F7A95, flate #F2F5F8 (til høyre for nå).
- **Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre (`tnum`) i tall, akser, matriser og tabeller. Proporsjonale sifre i de største enkelttallene.
- **Kjedevisningen** tegnes i Meteogrammets palett, ikke i 04s betong og sort: tynne linjer, rolige flater, blått for lager, rødt for restordre, marine for ordre. Notasjonen fra 04 (beholdning som boks på sann skala, strøm, forsinkelsesmerke, verdier på hjelpelinjer) kan beholdes eller forenkles.
- **Matrisen** bruker Meteogrammets blå og røde som divergerende skala for netto lager (blå over null, rød under) og en marine/grå sekvensiell skala for strømmer. Lag trinnene selv, kjør validatoren, og sørg for at tall i celler har kontrast ≥ 4,5:1. Farge bærer aldri status alene.
- **Kostnad:** to kostnadsarter med faste roller i alle konsepter: **restordrekost** (1,00 per enhet per uke) i rød-familien, **lagerkost** (0,50) i blå-familien. Totalkostnad er summen. Kjedens kostnad er summen for fire Roller.
- Hvit grunn, luft, ingen dekorasjon. Samme graf går igjen fra telefon til Debrief og lærerflate.

## De fire delene, og hva de skal gjøre

1. **Meteogrammet (tidsakse med nå-strek):** historikk til venstre, kjente ankomster til høyre, ordren tegnet to ganger (beslutning og ankomst om lag 4 uker senere).
2. **Kjedevisningen (flyt av varer):** øverst. Viser hvor varene er akkurat nå og hva som strømmer inn og ut. For en student i Klassespillet: bare setets eget ledd (innkommende ordre fra nedstrøms, levering fra oppstrøms, sendt, lager/restordre, på vei). Etter spillet, i Debrief og for Faglærer: **hele kjeden med fire ledd**, og gjerne kunden.
3. **Matrisen (tallene):** uker som kolonner, størrelser eller Roller eller spill som rader. Både som setets egen tabell, som Debriefens Rolle × uke, og som **aggregert klassevisning** (60 spill × uker) for Faglærer. Grunnleggeren vil ha tall og grafer, så tall og graf skal stemme med hverandre og helst dele tidsakse.
4. **Kostnadsbildet:** Målet er lavest kostnad for **hele kjeden**. Vis kostnaden ordentlig: per uke og akkumulert, fordelt på lager og restordre, per Rolle og for kjeden, og for klassen. Aggregert kostnad er et uttrykkelig ønske. Under Klassespillet ser studenten bare sin egen kostnad. Kjedens kostnad og de andres kostnad vises først når spillet er ferdig.

## Vinkel per konsept

Hvert konsept skal levere alle fire delene, men vinkelen avgjør komposisjonen og hva som leder. Navnet er et arbeidsnavn for konseptet, ikke et produktnavn.

| Nr | Arbeidsnavn | Vinkel |
|---|---|---|
| 01 | **Kjedebåndet** | Den direkte sammensmeltingen. Telefonen har et smalt kjedebånd øverst (setets ledd som strøm og beholdninger med tall), meteogrammet under, og en bryter Graf / Tall som bytter meteogrammet til matrise på samme tidsakse. Kostnaden er et fjerde felt i meteogrammet: kostnad per uke, delt i lager og restordre, med akkumulert sum. Gjør dette så rent og lettlest som mulig. |
| 02 | **Fire ledd** | Kjedevisningen er ryggraden i hele produktet. Telefonen viser setets ledd, Debriefen og Faglærer viser alle fire ledd pluss kunde som én flyt, med en ukeskrubber som spoler tiden og lar beholdningene vokse og krympe. Matrisen ligger under kjeden med én rad per Rolle, og kostnaden står ved hver node. |
| 03 | **Kostnadsregnskapet** | Kostnaden leder for setet. Hver flate åpner med hva uka og spillet har kostet, fordelt på lager og restordre. Ta med V-en fra 10 eller en bedre løsning, og «kostnad på snittet mot det du betalte» i Debriefen. Kjedebåndet og meteogrammet forklarer hvorfor kostnaden ble som den ble. Matrisen viser kostnad per uke som tall. |
| 04 | **Graf over tabell** | Som et ekte meteogram (yr.no): grafen øverst og tabellen rett under, kolonne for kolonne på samme tidsakse, slik at hver uke har både strek og tall. Dette prinsippet gjelder alle flater: setet, Debriefen (Rolle × uke) og Faglærers klassevisning. Kjedebåndet ligger over grafen. Kostnaden er egne rader i tabellen og et eget felt i grafen. |
| 05 | **Klassebildet** | Lærerflatene leder. Lag den sterkeste aggregerte klassevisningen: matriseveggen (60 spill × uker) i Meteogrammets farger, klassens kjede med fire ledd (median eller sum over spill), kjedekostnad per spill og fordeling mot fjorårets klasse, og en plenumsvisning. Studentflatene holdes nær Meteogrammet med kjedebånd øverst. Lever i tillegg til 08 gjerne et ekstra ark for plenum i `09-alle-sider.svg`. |
| 06 | **Uka som kolonne** | Kjeden og matrisen er samme ting sett fra to vinkler: hver uke er en kolonne der kjedens tilstand står som tall, og kjedevisningen øverst er bare den siste kolonnen, forstørret. Når studenten trykker på en tidligere uke, viser kjedevisningen den uka. Meteogrammet ligger mellom. Kostnad per uke er en rad, og akkumulert kostnad er siste rad. |
| 07 | **Lag for lag** | Telefonen er så rolig som mulig: kjedebånd og ordrefelt synes alltid, og meteogram, tall og kostnad er lag man blar mellom. Lagene låses opp i trinn: noen i Klassespillet, flere etter Debriefen, alle i Replay. Gjør Hjelpegrad til et tydelig, tegnet system. |
| 08 | **Labtime-skjermen** | Laptop og storskjerm leder. Komposisjonen er et rutenett der kjede, meteogram, matrise og kostnad står samtidig, på 1440 og i plenum. Telefonen er den reduserte utgaven av samme rutenett. Vis både Sara på laptop i Labtime og Faglærers plenumsvisning. |
| 09 | **Kjedens regning** | Det aggregerte kostnadsbildet etter spillet: hvordan 2 266,00 kr for kjeden bygges opp av fire Roller og to kostnadsarter uke for uke (matrise Rolle × uke i kroner, fossefall eller stablet areal), sammenlignet med simulert referanse 1 341,00 kr, og for Faglærer klassens fordeling av kjedekostnad. Under spillet ser setet bare sin egen del av regningen. Kjedevisningen kan vise kostnad per node. |
| 10 | **Fri syntese** | Ditt eget beste svar på hvordan de fire delene blir ett produkt. Ta et tydelig standpunkt, og forklar i `concept.md` hvorfor sammensetningen din er bedre enn den direkte sammensmeltingen (01). |

## De faglige prinsippene (kjernen i hele oppgaven)

Hver graf skal lære bort minst ett prinsipp, merket i `concept.md` og `10-pedagogikk.svg`.

- **P1 Lager er en opphopning.** Lager endres med inn minus ut. Forskning: mange kloke voksne bryter dette (89 % brøt materialbalansen i Bathtub-oppgaven; de antar at beholdningen ser ut som strømmen, «correlation heuristic»). Grafen må gjøre balansen synlig: inn og ut og lageret i samme tidsakse, slik at arealet mellom inn og ut er endringen i lageret. Kjedevisningen og matrisen gir nye måter å vise dette på.
- **P2 Forsinkelse.** En ordre kommer fram etter om lag 4 uker. Årsak og virkning er adskilt i tid, så det du ser nå kommer av det du gjorde før.
- **P3 Det som er på vei blir glemt.** Klassisk funn: spillere legger lite vekt på det som allerede er bestilt (Sterman: vekten på forsyningslinja er klart under 1). **Posisjon = Lager − Restordre + På vei.** Dette er den viktigste innsikten for å spille bra.
- **P4 Ordrer er ikke etterspørsel.** Hvert ledd ser bare ordrene fra nedstrøms, ikke kundene. Informasjon forvrenges opp gjennom kjeden.
- **P5 Forsterkning og faseforskyvning.** Svingningene vokser oppstrøms og kommer senere (spill 17: 1,8× → 4,1× → 6,0× → 7,6×).
- **P6 Struktur gir atferd.** Nesten alle grupper svinger likt (60 spill). Forklar med struktur, aldri skyld. Målet er at studenten slutter å spørre «hadde jeg rett?» og begynner å spørre «hvorfor skjedde det?».
- **P7 Overreaksjon forsterker også.** Å regne med det som er på vei er ikke nok: i simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17. Rolig tilpasning og å telle det som er på vei må til sammen. Hold deg til denne nyansen.
- **P8 Restordre koster dobbelt.** Restordre 1,00, lager 0,50 per enhet per uke, og målet er lavest kostnad for HELE kjeden. I runde 3 er dette løftet fram: kostnadsbildet skal gjøre P8 og kjedemålet tydelig.

Testforskningen sier: «det svinger» er det lett å huske, mens materialbalanse og konsistens mellom grafer viser forståelse. Vis derfor tall og grafer som stemmer med hverandre, og legg merke til at det er regnestykket og ikke bare mønsteret som er poenget. Matrisen gjør nettopp dette mulig: kontroller i `build.py` at tallene i matrisen, grafene og kostnaden stemmer med loggen for alle uker, og stopp bygget hvis de ikke gjør det.

## Produktsannhet som ikke kan brytes

- **Én beslutning per Uke:** ett heltall. Studenten bestemmer, systemet regner. Etter bekreftelse kan ordren ikke endres. Beslutningen må fortsatt kunne tas på sekunder.
- **Alle seter bestiller i samme Uke.** Uka går videre når alle har bestilt. Spillet viser hvem det venter på, med Rolle og navn eller «KI-spiller», og hvor lenge.
- **Et sete ser på sin egen skjerm:** lager eller restordre, innkommende ordre, innkommende levering, sendt denne uka, det som er på vei, egen ordrehistorikk, løpende totalkostnad og ukenummer. Alt pluss ordre-input skal kunne nås på 360 px bredde uten sideveis scrolling. Med kjedebånd + graf + ordrefelt på telefonen må du være streng med plassen: detaljer bak ett trykk.
- **Under spillet kan grafer, kjedevisning, matrise og kostnad bare vise setets egne data.** Høyre kant på tidsaksen er **nå** (eller nå + kjente ankomster). Tidsaksen viser aldri en slutt, antall uker eller framdrift. Skriv aldri «11 av 36». Sara er Grossist, så Sara ser ikke kundeetterspørselen og heller ikke andres lager eller kostnad. Innkommende ordre er ikke merket som etterspørsel. Kjeden med fire ledd vises først etter spillet.
- **Framover i tid:** Du kan vise kjente ankomster og en utregnet projeksjon, men det må stå at det ikke er garantert (leverandøren kan mangle varer; 24 bestilt ble 17 levert i Uke 15). Projeksjon bygger bare på setets egne tall.
- **Ingen anbefalt ordre under spillet.** Vis regnestykket og konsekvensen, aldri fasiten. Studenten bestemmer. Det er forskjell på å gjøre posisjonen synlig og å si hva som er riktig.
- **Ingen chat** mellom spillere. Ingen rangering eller premier for studenter. Faglærer kan se kostnad per spill. Ingen studentvendt sammenligning av spill etter kostnad som kan leses som rangering.
- **KI er alltid merket:** KI-spillere, overtatte seter, KI-generert tekst. **Rolle og status vises aldri med farge alene.**
- **Navnet «Beer Game» / «ølspillet» / «øl» brukes ikke før Debriefen,** heller ikke på landingssiden. Vi sier «enheter» eller «kasser». Debriefen kan navngi øvelsen.
- **Landingssiden:** ingen kunder, sitater, priser eller læringsresultater. Ikke ordet «bullwhip». Ikke vis firerollers forsterkning eller hoppet i etterspørselen, for studenter kan se siden. Du kan vise ett setes egne grafer og lærerens oversikt. Primærhandling «Be om lærertilgang», sekundær «Logg inn». Fakta: kjører hele øvelsen fra invitasjon til PDF-rapport; klasser på rundt 250 studenter; alle spillene på én skjerm; KI-spillere fyller tomme seter; ett fravær stopper ikke gruppa; ingen spill blir stående uferdig; på mobil; på norsk; studentlisten fra Canvas-eksport.
- **KI-vurderingen** teller ikke, er aldri en karakter, og sier det der den vises.
- **Debriefen:** Forklaring skrives FØR etterspørselen avsløres. Alle tall fra loggen. Stemme: direkte, konkret, andre person, ingen skyld, ingen tom ros. KI-tekst merkes «KI-generert, kan ta feil».
- Merk tall med en liten linje «Demodata». Simulerte referanser merkes «Simulert» og kalles aldri optimale eller fasit. Produktnavn er ikke bestemt: bruk konseptets arbeidsnavn.
- **Ingen kjønnede pronomen** om personene i eksemplene. Bruk navnet eller «hen».

## Hjelpegrad: ta et standpunkt

Her er en reell spenning. Studenten må først oppleve svingningene for at Debriefen skal gi læring. Grafer som gjør feilen for lett å unngå kan svekke nettopp det (issue #22). Grunnleggeren vil samtidig ha grafer og tall som gir innsikt i å spille godt. Kjedevisningen gjør På vei svært synlig, og det skjerper spørsmålet. Hvert konsept skal svare på dette i `concept.md`, under **Hjelpegrad:**: hva vises i Klassespillet, hva vises i Replay, og hvorfor. Et legitimt grep er at grafer og begreper **låses opp etter Debriefen**, slik at Replay er der studenten bruker innsikten. Vis forskjellen på minst én tegning.

## Norske begreper (bokmål)

Faglærer, Klasse, Klasseliste, Invitasjon, Klasseøkt, Spillinnstillinger, Klassespill, Sete, Rolle: Detaljist, Grossist, Distributør, Fabrikk. Uke, Ordre, Lager, Restordre, På vei, Posisjon, Totalkostnad, Lagerkostnad, Restordrekostnad, Kjedekostnad, Veiledede uker, Pause, KI-spiller, KI overtar, Ta tilbake setet, Labtime, Startoppgave, Debrief, Forklaring, Debrief-quiz, Replay, Individuell test, KI-vurdering, Studentrapport, Oversikt, Klasserapport, Spillinnsikt, Melding, Spillfrist, Debrief-frist, Testfrist, Forsterkning.

## Data i fixture.json

- `spill17`: Hele det spilte spillet. `serier` har `demand` og per Rolle lister på 36 uker (`ordre`, `lager`, `restordre`, `innkommende_ordre`, `levering`, `paa_vei`, `kost_sum`; indeks 0 er Uke 1). Også `forsterkning`, `kost_per_rolle`, `kjedekost` (2 266,00). Ukeskostnaden per Rolle er `lager × 0,50 + restordre × 1,00`, og summen er `kost_sum`. Sjekk at det stemmer, og bruk det til å dele kostnaden i to arter.
- `bare_sara_teller_paa_vei`: Simulert: samme kjede, men Grossist regner med alt på vei. Kjede 1 507,00, Grossist-kostnad 464,50 (mot 553,50) og forsterkning 2,2× (mot 4,1×). Viser sammenhengen, ikke en fasit.
- `alle_teller_paa_vei`: Simulert referanse med rolig regel for alle fire. Kjede 1 341,00, Fabrikk 3,3×. Regelen er valgt for å illustrere, så kall den aldri optimal eller fasit.
- `replay_sara`: Saras Replay: Tilfeldig etterspørsel, 33 uker, tre KI-spillere. «Ikke like for like.»
- `klasse.spill`: 60 Klassespill med `spill`, `status` (`ferdig`, `pågår`, `pauset`, `venter`), `uke`, `kjedekost`, `ki_seter`, `venter_paa`, `navn`, `ventet_timer`, `fortsetter`, og **ekte serier**: `ordre` og `netto_lager` per Rolle fram til gjeldende uke. Ferdige har også `forsterkning` og `kost_per_rolle`.
- `klasse.ferdige`: Kvartiler for kjedekost og forsterkning per Rolle. `klasse.moenstre`: antall Detected patterns. `klasse.fjoraaret`: fjorårets klasse.
- `klasse.traktA`, `klasse.roster`: trakt og klasseliste.

Aggregerte klassetall (median netto lager per Rolle og uke, kostnad per uke for klassen, fordeling av kjedekostnad) regner du ut fra `klasse.spill` i `build.py`. Ukeskostnad for klassespill kan regnes fra `netto_lager` (positiv × 0,50, negativ × 1,00). Skriv i `concept.md` hvilke aggregater du har regnet ut og hvordan.

**Personer:** Sara (Grossist, spill 17), Ida (Detaljist), Mikkel (Distributør), Jonas (Fabrikk). Faglærer Bård. Klasse `class-of-1994`, IBE160.

**Saras skjerm, Uke 11:** Lager 0 · Restordre 13 · Innkommende ordre 8 · Levering 4 · Sendt 4 · På vei 16 · Neste levering 4 · Totalkostnad 68,00 kr. Posisjon = 0 − 13 + 16 = **3**. Sara taster **24**, og da blir posisjonen 27. Ordrehistorikk uke 1 til 10: 4, 4, 4, 4, 4, 4, 4, 4, 4, 8. Uke 1 til 4 er Veiledede uker. Senere går restordre opp mot 40 og lager opp mot 30: grafene må tåle skalaen.

**Venter på:** Ida har bestilt, Mikkel har bestilt, Jonas venter (3 min), Sara venter (deg).

**Slutt:** Kjeden 2 266,00 kr. Detaljist 342,00 · Grossist 553,50 · Distributør 691,00 · Fabrikk 679,50. Forsterkning 1,8× · 4,1× · 6,0× · 7,6×. Kundeetterspørsel: 4 per uke, hopper til 8 i uke 5, deretter stabil.

**Oversikt:** 60 Klassespill. 41 ferdig, 15 pågår (herav 2 pauset), 4 venter. Spill 2 venter på Noah (Grossist) i 23 t, like før KI overtar ved 24 t. Trakt: registrert 240 → klassespill ferdig 164 → debrief ferdig 121 → quiz bestått 97 → replay ferdig 58 → test levert 12 → KI-vurdering klar 0.

**Klasseliste:** 250 rader fra Canvas-eksport, 4 ugyldige adresser (rad 37, 88, 141, 203), 238 registrert, 2 manuelt registrert, 10 uregistrert. Invitasjon gyldig i 14 dager.

**Klasseøkt, standarder («Klassisk»):** startlager 12, 4 enheter i hvert ledd, ordreforsinkelse 2, fraktforsinkelse 2, produksjonsforsinkelse 2 uker, etterspørsel 4 → 8 i uke 5, lagerkost 0,50, restordrekost 1,00, 36 uker, Veiledede uker 1–4, KI-modus LLM-spillere, Gruppedebrief, Inaktivitetsgrense 24 t. Skjermen sier at kildene er uenige om forsinkelser og at dette er produktets standard. Merket «Obligatorisk». 240 studenter fordeles tilfeldig i 60 spill à 4.
**Datoer:** Start ti. 24. nov 2026 · Spillfrist ti. 8. des · Debrief-frist fr. 11. des · Testfrist fr. 18. des. **Labtimer:** to. 26. nov 14:15, ma. 30. nov 10:15, to. 3. des 14:15, ma. 7. des 10:15, Datalab A2.

## Leveranse: 10 SVG-filer + concept.md i din mappe

Mappa di er `concepts-r3\NN-<arbeidsnavn-med-små-bokstaver>\` (f.eks. `01-kjedebaandet`, `02-fire-ledd`, `03-kostnadsregnskapet`, `04-graf-over-tabell`, `05-klassebildet`, `06-uka-som-kolonne`, `07-lag-for-lag`, `08-labtime-skjermen`, `09-kjedens-regning`, `10-fri-syntese`). Ingen æ, ø, å i mappenavn.

| Fil | Innhold | Lerret |
|---|---|---|
| `10-pedagogikk.svg` | **VIKTIGST.** Konseptets grafgrammatikk: kjedevisning, meteogram, matrise og kostnad for Sara ved Uke 5, 11, 18 og 29, slik at svingningene og kostnaden blir synlige over tid. Merk hvilket prinsipp (P1–P8) hver del lærer bort og hvilken innsikt den gir for neste ordre. Inkluder sammenligningen med en simulert referanse slik den vises etter Debriefen. | 2000×1400 |
| `05-spill.svg` | **HOVEDSKJERMEN.** Telefon (390×844) midt i Uke 11 med 24 tastet inn, og laptop. Kjedevisning øverst, graf under, ordrefelt. Telefonen skal ha luft og ikke virke tett: legg detaljer bak ett trykk, og vis det åpnede panelet eller den alternative visningen (matrise / tall) ved siden av. | 1600×1000 |
| `06-spilldynamikk.svg` | 6 telefonruter med korte notater: (A) Uka åpner. (B) Beslutningen: 24 med 16 på vei. (C) Bekreftet, venter på de andre. (D) Uka går videre, kan hoppes over, aldri over 2 sek. (E) Jonas er borte: Pause og KI-spiller, merket, og «Ta tilbake setet». (F) Spillet slutter: kjedens totalkostnad først, så per Rolle og per kostnadsart, videre til Debrief. Under: 3–4 setninger om hva spilleren lærer av å se kjeden, grafen og kostnaden uke for uke. | 2100×1200 |
| `07-debrief.svg` | Gruppedebrief i 5 steg + delt skjerm, bygd på Meteogrammets Debrief: (1) skriv Forklaring, avsløringen er låst; (2) **klimaks: etterspørselen avsløres**; (3) alle fire Rollers ordre i én graf, forsterkning 1,8× → 7,6×, og hele kjeden med fire ledd; (4) ditt øyeblikk: Uke 11, hva du så, hva du bestilte, hva det kostet senere, og hva de andre Rollene så, med sammenligning mot simulert referanse; **kjedens kostnad** fordelt på Rolle og kostnadsart; (5) quiz med feil svar forklart. Ta med matrisen Rolle × uke der den gir innsikt. | 2100×1200 |
| `08-laerer-oversikt.svg` | Faglærer holder 60 spill på sporet på én 1440-skjerm: status, hvem hvert spill venter på og hvor lenge, pause, KI-seter, nær overtakelse uthevet, trakten, send Melding, filtrering. **Aggregert klassevisning:** matrisen 60 spill × uker med ekte serier, og klassens kostnadsbilde (kjedekostnad per spill, fordeling, fjoråret). | 1600×1000 |
| `01-landing.svg` | Landingsside for faglærere: første skjermbilde + starten av neste seksjon. Kjedevisningen og en elegant graf kan bære siden (husk landingsreglene). | 1440×1200 |
| `02-laerer-klasse.svg` | Lag Klasse: navn og emnekode, last opp Canvas-fil, velg e-postkolonne, ugyldige rader per rad, send Invitasjoner, status. | 1440×1000 |
| `03-laerer-spill.svg` | Klasseøkt: bygg på Meteogrammets versjon, som grunnleggeren likte. Forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer, fordelingsforhåndsvisning (60 spill à 4, kjør på nytt, bekreft). Kan lagres uten endring. Kjedevisningen kan gjerne vise forsinkelsene og startlageret slik innstillingene står. | 1440×1100 |
| `04-student-hjem.svg` | Sara på mobil: spill og Rolle, setene, de seks stegene (Klassespill, Debrief, Quiz, Replay, Individuell test, Rapport), neste frist, Labtimer, «spillet venter på deg». To telefoner: registrering og hjem under spill. | 1000×900 |
| `09-alle-sider.svg` | Kontaktark over ALLE andre sider på lavere detaljnivå, gruppert per rolle, med tittel og én linje: Student: Invitasjon og registrering, Logg inn, Regler før første ordre, Startoppgave, Replay, Replay-gjennomgang, Individuell test (flervalg, interaktiv tegne-/tabelloppgave, langsvar), KI-vurdering, Studentrapport (PDF), Alle spill side om side. Faglærer: Lærerhjem, Klasserapport, Spillinnsikt (uke for uke), Studentside, Alle spill i plenum, Tverrklasse-statistikk, Meldinger, Lærers testspill. Admin: Admin-område, Brukere og roller, KI-kostnad. | 2000×1400 |
| `concept.md` | Se mal nederst. | |

## Designkrav

- **Enkelhet:** Fire deler på én flate er lett å gjøre for tett. Ett hovedbudskap per flate. Det som kan fjernes, fjernes. Tall som ikke brukes i beslutningen ligger bak ett trykk. Hold deg til Meteogrammets få farger.
- **Grafkvalitet:** direkte etiketter i stedet for forklaringsbokser, svak hjelpelinje, tabellsifre, sann null, felles tidsakse mellom grafer (og mellom graf og matrise), et tydelig «nå». Teksten forklarer hva grafen viser, ikke at den er en graf.
- **Lærerflater** er Operate: skanning på sekunder. **Spill og Debrief** er kjernen: Grafen leder. **Landing** er Persuade: tydelig hovedhandling, og en graf som viser noe bare dette produktet kan.
- **Forbudt:** eyebrow/kicker over overskrifter, gradienttekst, emoji eller unicode-tegn som ikon (tegn ikoner som SVG-former, helst ingen ikoner), like kort med ikon + tittel + tekst, hero-metric-malen, seksjonsnummer som pynt, tykk farget kant på kortenes side, hard offset-skygge, dekorative skygger, kopier av eksisterende merker eller spill. Ingen figurer, tegneseriestrek, piksler, treverk, skeuomorfe instrumenter, mettede fullflater, «spill»-knapper, belønningsanimasjon, utropstegn eller muntre mikrotekster.
- **Lesbarhet:** minst 13 px tekst på telefonskjermer (390-skala), kontrast ≥ 4,5:1 for brødtekst og celletall. Mindre tekst er greit på kontaktarket. Lærerens matrisevegg kan bruke mindre tall, men må ha en tabellvisning.
- **Tekst:** Ekte, kort norsk fagtekst. Ingen lorem ipsum. Knapper sier hva som skjer.

## Tekniske krav til SVG

1. **Generer med `build.py` i din mappe** (`uv run python build.py`). Les tall fra `../_shared/fixture.json`, med hjelpefunksjoner for skala, akser, linjer og tekstbryting. Ingen tall i grafer eller matriser tastes inn for hånd. Kopier gjerne 02s kode som utgangspunkt (se over).
2. Hver fil: gyldig, frittstående `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" font-family="...">` med `<title>` og `<desc>` på norsk.
3. **Prefiks alt:** CSS-klasser begynner med `eNN-` (NN = konseptnummer, e for runde 3), `id`-er med `eNN-<side>-`. Ingen selektorer på bare elementnavn. Ingen `<script>`. Ingen rester av `d02-`.
4. **Fonter:** Øverst i `<style>`: `@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&amp;display=swap');` med ekte fallback. Bare Google Fonts. Ingen eksterne bilder.
5. **Tekst må passe.** SVG bryter ikke linjer selv. Bruk en bryte-hjelper og god plass.
6. **Verifiser ved å se.** `uv run python ../_shared/render.py .` fra mappa di validerer XML og lager `_png/<navn>.png`. Åpne PNG-ene med Read, se etter overlapp, klipping, feil font og tett layout, og rett i bolker. Maks to synsrunder per fil, utenom `05`, `06`, `07`, `08` og `10`, som får tre.
7. Telefoner i 390×844-skala med diskret ramme. Ingen fotorealistiske mockups.

## concept.md-mal

```markdown
# <nummer> <Arbeidsnavn>
**Tese (én setning):** …
**Sammensetning:** hvordan kjede, meteogram, matrise og kostnad henger sammen på telefon, Debrief og lærerflate, og hva som leder hvor.
**Faglig kjerne:** hvilke prinsipper (P1–P8) konseptet gjør best, og med hvilken del.
**Spilldynamikk:** 3–4 setninger om hva studenten gjør, ser og forstår i en Uke, og hvordan kjeden, grafen og kostnaden hjelper neste ordre.
**Hjelpegrad:** hva vises i Klassespillet, hva vises i Replay, og hvorfor.
**Kostnadsbilde:** hva studenten ser under spillet, hva gruppa ser etter, og hva Faglærer ser aggregert.
**Debrief-grep:** én setning.
**Lærerflate-grep:** én setning.
**Palett:** avvik fra Meteogrammet og nye trinn (matrise), med hex. **Typografi:** fonter og roller.
**Styrke:** … **Ærlig risiko:** …
**Gjenbrukbart selv om konseptet velges bort:** én idé.
```

## Rapport tilbake

Maks 8 linjer: mappe, filer, hva du faktisk så i renderen, kjente svakheter, og om alle 10 SVG-er validerte. Ikke lim inn SVG eller kode.
