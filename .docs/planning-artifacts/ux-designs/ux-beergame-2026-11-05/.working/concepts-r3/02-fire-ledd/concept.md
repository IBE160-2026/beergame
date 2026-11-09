# 02 Fire ledd

**Tese (én setning):** Kjeden er ryggraden: hver flate åpner med leddet eller hele kjeden tegnet på sann skala (røret med det som er på vei, boksen med lager eller restordre, kostnaden ved noden), og meteogrammet og matrisen under forklarer hvordan kjeden kom dit.

**Sammensetning:**
- *Telefon (Klassespill):* setets eget ledd øverst. Leverandøren og kunden nedstrøms står bare som navn i stiplet ramme, uten tall. Røret er delt i ukeplasser (4, 4, 8 og den nye ordren bakerst), og forsinket vare uten dato står som en egen stiplet boks lengst unna. Boksen viser lager over grunnlinja og restordre under. Ordrene går mot venstre på en tynn linje øverst. Under leddet står Totalkostnad, delt i lager og restordre. Under det ligger et kompakt meteogram med tre felt, og ordrefeltet nederst. Alle tall ligger ett trykk unna som matrise for uke 6–11 (`05`).
- *Laptop i Labtime:* samme ledd øverst, så meteogrammet og setets matrise på samme tidsakse, kolonne for kolonne.
- *Debrief og delt skjerm:* hele kjeden med fire ledd og kundene som én flyt, med en ukeskrubber som står på samme tidsakse som matrisen Rolle × uke under. Skrubberen flytter rammen i matrisen og spoler kjeden, så beholdningene vokser og krymper. Skalaen ligger fast for alle 36 uker (`fit_chain`), så boksene aldri skaleres om. Kostnaden står ved hver node, akkumulert til uka.
- *Faglærer:* klassens kjede med median netto lager og median ordre per Rolle i valgt uke, og klassens samlede kostnad ved hver node. Skrubberen styrer rammen i matriseveggen (60 spill × 36 uker, fire striper per spill i samme rekkefølge som kjeden).
- Kjeden leder overalt. Meteogrammet leder ikke noe sted, men står alltid rett under som historikk. Matrisen ligger alltid under kjeden.

**Faglig kjerne:** P3 og P1 gjør konseptet best, og det skjer i kjeden. Røret gjør *På vei* til en ting med plass og størrelse på samme skala som lageret, så det er vanskelig å glemme. Ordren man taster, legger seg bakerst og rykker én plass per uke (`06`, stripen nederst: 24 kommer som 17 i Uke 15, og 7 ligger hos leverandøren uten dato). Boksen er en beholdning som bare endres med inn minus ut (P1), og matrisen viser regnestykket kolonne for kolonne. P5 står i Debriefens steg 3: røde rammer i matrisen markerer første uke med ordre på 10 eller mer (Uke 6, 11, 13, 15), og forsterkningen står til høyre. P8 ligger ved hver node (todelt kostnadsstrek) og i steg 4 (kjedens regning per Rolle og kostnadsart mot simulert referanse). P2 er røret og «om lag 4 uker». P4 og P6 kommer med avsløringen. P7 står i `10-pedagogikk.svg`.
- `build.py` stopper hvis noe av dette ikke stemmer for alle 36 uker og alle fire Roller: materialbalansen, at røret pluss forsinket vare er lik På vei, at ukeskostnaden er lager × 0,50 + restordre × 1,00, at summen er `kost_sum` og `kost_per_rolle`, at summen av Roller er kjedekost, at ordre fra et ledd er ordre inn hos leverandøren to uker senere, og at Detaljistens ordre inn er etterspørselen.
- Bygget stopper også hvis klassens kostnad regnet fra `netto_lager` ikke stemmer med `kjedekost` per spill, eller hvis et tall i en matrisecelle får kontrast under 4,5:1.

**Spilldynamikk:** Uka åpner med ny levering og ny ordre inn, og plassen bakerst i røret står tom og stiplet. Sara taster 24, og tallet legger seg straks bakerst i røret, bak 4, 4 og 8, og samtidig som åpen stolpe fire uker fram i meteogrammet. Etter bekreftelsen viser skjermen hvem uka venter på. Når uka går videre, rykker røret én plass mot noden, boksen svarer, og kostnaden ved noden øker med ukas beløp. Sara ser altså hver uke at det hen får nå, ble bestemt for fire uker siden, og at røret allerede er fullt før neste ordre.

**Hjelpegrad:** Standpunkt: røret vises, men summen tegnes ikke før Replay.
- *Klassespill:* eget ledd med røret i ukeplasser og tallene på hver plass, boksen, kostnaden og meteogrammet med kjente ankomster («Bestilt, ikke garantert»). Posisjon ligger ett trykk unna som regnestykke under Alle tall. Ingen projeksjon og ingen Posisjon-strek.
- *Replay (etter Debriefen):* samme ledd med en Posisjon-klamme under røret og noden («Posisjon 0 − 13 + 16 = 3. Med 24: 27»), og meteogrammets projeksjon er åpnet. Forskjellen er tegnet nederst til høyre i `05-spill.svg`.
- *Hvorfor:* Kjeden gjør På vei svært synlig, og det skjerper spørsmålet fra issue #22. Vi vil ikke skjule røret, for det er setets egne tall, og produktet lover at studenten ser det som er på vei. Men å legge røret og noden sammen til ett tall er nettopp den regningen folk flest lar være. Hvis skjermen gjør den, svekkes erfaringen Debriefen bygger på. Derfor tegnes summen først i Replay. Vi vet ikke uten test hvor mye røret alene demper svingningene, og det er konseptets største usikkerhet.

**Kostnadsbilde:**
- *Under spillet:* setet ser bare sin egen Totalkostnad ved noden, delt i lager og restordre. I Alle tall står kostnad per uke som en matriserad, sammen med regnestykket 86 × 0,50 + 25 × 1,00 = 68,00 kr.
- *Når spillet er ferdig:* skjermen viser kjedens totalkostnad først (2 266,00 kr, lager 901,00 + restordre 1 365,00), så hele kjeden og kostnaden per Rolle.
- *I Debriefen:* kostnaden står ved hver node mens gruppa spoler. Steg 4 viser kjedens regning per Rolle og kostnadsart, med simulert kostnad som stiplet strek. Under står akkumulert kjedekost over tid, med lager og restordre som stablede flater og Simulert 1 341 som stiplet linje.
- *Faglærer:* klassens kostnad ved hver node i kjeden (sum til valgt uke), kjedekost per ferdig spill som punkter med kvartilbånd, median og fjoråret, og klassens kostnad per uke delt i lager og restordre.
- *Aggregater regnet i `build.py`:*
  - Median netto lager og median ordre per Rolle i uke *w*, over spill med `uke ≥ w`.
  - Klassens kostnad per Rolle til og med *w*, som sum over de samme spillene. Positivt netto lager × 0,50 og negativt × 1,00.
  - Klassens kostnad per uke, som sum over alle spill som har nådd uka, delt i lager og restordre.
  - Median kjedekost for ferdige spill. Den kontrolleres mot `klasse.ferdige`.

**Debrief-grep:** Gruppa spoler hele kjeden med fire ledd over matrisen Rolle × uke, og ser beholdningene vokse oppstrøms mens den røde rammen vandrer fra Uke 6 til Uke 15.

**Lærerflate-grep:** Klassens kjede i valgt uke over en matrisevegg med fire striper per spill, slik at én skrubber styrer både kjeden og den uthevede kolonnen for alle 60 spill.

**Palett:** Meteogrammets palett uten avvik. Nye trinn for matrisen, validert med `validate_palette.js --ordinal` mot hvit flate (alle fire sjekker bestått, også lys ende ≥ 2:1):
- Lager: #97BADA, #6E9FCB, #2B6CA3, #1D4E7A (1–9, 10–19, 20–39, 40+).
- Restordre: #E2A199, #D47A70, #B5423A, #8E2F28.
- Null: #F2F5F8.
- Ordre: #F2F5F8, #A6B8CA, #7F95AC, #44586F, #0F2A47 (0–4, 5–9, 10–15, 16–23, 24+).
- Celletall bruker marine eller hvit, etter hva som gir kontrast ≥ 4,5:1. `ink_on` sjekker dette i bygget.
- Status og Rolle står alltid som tekst. Trinnforklaringen har tallene inne i trinnene.
- I kjeden er lager blå boks, restordre rød boks, det som er på vei åpne blå bokser, og forsinket vare uten dato en grå stiplet boks.

**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i tall, akser og matriser, og proporsjonale sifre i de største enkelttallene (kjedens totalkostnad, Forsterkning).

**Styrke:** Én tegning bærer hele produktet: samme notasjon for røret, boksen og kostnaden går igjen fra telefonen til Debriefen og lærerens oversikt. Bare målestokken og antall ledd endrer seg. På vei blir en fysisk mengde, ikke et tall i en liste. Skrubberen over matrisen gjør at tall og tegning alltid peker på samme uke.

**Ærlig risiko:**
- Kjeden tar plass på telefonen. Med ledd, graf og ordrefelt er skjermen full, og meteogrammet blir kompakt.
- Røret kan hjelpe så mye at svingningene dempes før Debriefen. Det er motsatt av hva #22 ber om, og det må testes.
- Sann skala betyr at små tall gir små bokser: restordre 13 er bare 22 px høy på telefonen.
- Den grå boksen for forsinket vare kan bli høy, og over 44 enheter får den et bruddmerke.
- Hele kjeden på 420 px (delt skjerm, ferdig spill på telefonen) er tett og blir lesbar først i fullskjerm.
- Skrubberen er tegnet statisk. Animasjonen må prøves i prototype.

**Gjenbrukbart selv om konseptet velges bort:** Røret delt i ukeplasser på samme skala som lageret, med den nye ordren bakerst og forsinket vare uten dato som egen stiplet boks.
