# 01 Kjedebåndet

**Tese (én setning):** Den direkte sammensmeltingen: et smalt kjedebånd øverst viser hvor setets varer er akkurat nå, meteogrammet under viser hvordan det ble slik, en bryter Graf / Tall bytter grafen mot de samme tallene i de samme kolonnene, og kostnaden er meteogrammets fjerde felt.

**Sammensetning:**
- *Telefon (Klassespill):* topptekst med Uke og Totalkostnad, så kjedebåndet (cirka 110 px): varer går mot høyre fra «Fra Distributør» gjennom På vei (én boks per leveranse, sann skala, nærmest lageret kommer først) til Lager (blå boks over linja) eller Restordre (rød boks under linja), og videre til «Til Detaljist». Ordrene går mot venstre: «Ordre inn 8» inn fra høyre og «Din ordre 24» ut mot venstre. Under båndet sitter bryteren Graf / Tall og meteogrammet med fire felt: netto lager, inn og ut, din ordre og kostnad per uke. Ordrefeltet ligger nederst på én rad (stepper og Bekreft). Tidsaksen er nå − 7 til nå + 4, og den er den samme i Graf og Tall.
- *Tall:* matrisen erstatter grafen på samme plass og i de samme kolonnene: netto lager (divergerende blå/rød), ordre inn, levering (kjente ankomster som åpne celler til høyre for nå), din ordre, på vei, kostnad per uke og Totalkostnad.
- *Laptop (Labtime):* båndet over hele bredden, og graf og tall står samtidig: matrisen ligger rett under meteogrammet, kolonne for kolonne.
- *Debrief:* steg 3 viser hele kjeden med fire ledd i samme båndgrammatikk (Produksjon → Fabrikk → Distributør → Grossist → Detaljist → Kundene) med ukeskrubber, over alle fire Rollers ordre. Steg 4 har Saras meteogram med kostnadsfelt. Kjedens kostnad står ved siden av, og den delte skjermen er matrisen Rolle × uke.
- *Lærerflate:* matriseveggen 60 spill × 36 uker leder, med status, Uke, kjedekost, KI og hvem spillet venter på i samme rad. Klassens kostnadsbilde står i høyre kolonne.
- Hva leder: båndet leder på telefonen (nå), grafen leder i Debriefen (hvorfor), matrisen leder for Faglærer (alle spill).

**Faglig kjerne:**
- *P3, båndet:* På vei står som bokser på samme skala som restordre og lager. I Uke 11 er restordren 13 og det som er på vei 16, og de ser like store ut fordi de er det. Bestilt er like synlig som det som står på lager.
- *P2, båndet og grafen:* ordren legger seg bakerst i båndet og rykker ett steg mot lageret hver Uke (`06`, stripa nederst). I meteogrammet står den to ganger. I Uke 15 kom bare 17 av 24, og resten står stiplet som «uten dato».
- *P1, grafen og matrisen:* den røde delen av inn og ut-stolpen er det netto lager faller. I Tall-visningen står de samme tallene i samme kolonne, så materialbalansen kan regnes.
- *P8, kostnadsfeltet:* restordre 13 gir en stolpe dobbelt så høy som et lager på 13. Lager er blått og restordre rødt overalt.
- *P4, P5, P6:* Debriefen dekker dette med avsløringen, fire Rollers ordre på samme skala, rød forskyvningslinje og matrisen Rolle × uke der tallene vokser oppover i kjeden.
- *P7:* står i `10-pedagogikk.svg` og i Debriefens simulerte sammenligning.
- `build.py` stopper hvis materialbalansen, ukeskostnaden (lager × 0,50 + restordre × 1,00 = differansen i `kost_sum`), sum per Rolle, kjedekost (spill 17 og begge referansene) eller kjedekost per Klassespill ikke stemmer med loggen. Graf, matrise og kostnad tegnes fra samme `Seat`-objekt.

**Spilldynamikk:** Uka åpner med ny levering og ny ordre inn i båndet, og kostnadsfeltet får en ny stolpe. Sara taster 24, og tallet legger seg bakerst i båndet («På vei 16 + 24») og fire Uker fram i grafen. Etter bekreftelsen viser skjermen hvem Uka venter på. Så rykker alt i båndet ett steg mot høyre på under 2 sekunder, og det kan hoppes over. Fra Uke til Uke ser hen at det som kommer nå, ble bestilt for fire Uker siden, og at hver Uke med restordre koster dobbelt så mye som en Uke med like mye lager.

**Hjelpegrad:** Standpunkt: delene vises i Klassespillet, summen vises i Replay.
- *Klassespill:* båndet med Lager, Restordre og hver leveranse på vei på sann skala, meteogrammet med kjente ankomster («Bestilt, ikke garantert»), Tall-visningen og egen kostnad. Ingen Posisjon-rad, ingen klamme og ingen projeksjon.
- *Replay (etter Debriefen):* båndet får en klamme over restordre og alt på vei med «Posisjon 0 − 13 + 16 = 3. Med 24: 27», matrisen får raden Posisjon, og meteogrammet får den stiplede projeksjonen.
- *Hvorfor:* Båndet gjør På vei svært synlig, og det er ærlig: dette er setets egne tall, og produktet skal vise det som er på vei. Men summen er nøyaktig det spillerne lar være å regne (Sterman), og ferdig regnet sum er ett steg fra en ordre-opp-til-regel. Uten summen får gruppa fortsatt oppleve svingningene som Debriefen trenger (issue #22). Vi vet ikke uten test hvor mye selve båndet demper svingningene. Forskjellen er tegnet nederst til høyre i `05-spill.svg` og beskrevet i `10-pedagogikk.svg`.

**Kostnadsbilde:**
- *Under spillet (student):* Totalkostnad i toppteksten, kostnadsfeltet med blå og røde stolper per uke og «Sum 68,00 kr» ved nå-streken. I Tall-visningen finnes radene «Kostnad per uke» og «Totalkostnad». På laptop står «Kostnad så langt» delt i lager (43,00) og restordre (25,00). Bare egne tall.
- *Etter spillet (gruppa):* Spillets sluttskjerm åpner med kjedens 2 266,00 kr delt i lager (901,00) og restordre (1 365,00), så per Rolle delt på de to artene. I Debriefen står kjedens akkumulerte kostnad over tid (stablet lager og restordre) mot simulert referanse 1 341,00 kr, og matrisen har raden «Kjeden, kr per uke».
- *Faglærer (aggregert):* kjedekostnad per spill som prikkstripe (fylt: ferdig, ring: pågår), med median 1 954 og fjorårets 2 740, og «Klassens kostnad per uke, snitt per spill» delt i lager og restordre. Kjedekost står også i hver rad i matriseveggen.
- *Utregnede aggregater (i `screens_debrief_teacher.py`):*
  - Ukeskostnad per Klassespill: sum over fire Roller av positivt `netto_lager` × 0,50 og negativt × 1,00. Kontrollert mot `kjedekost` for alle 60 spill.
  - Klassens kostnad per uke: snitt per spill over spillene som har nådd uka (60 i Uke 1, 41 i Uke 36), delt i lager og restordre. Høyest i Uke 18.
  - Antall per status og median kjedekost for ferdige spill, kontrollert mot `klasse.ferdige`.
  - Kjedens ukeskostnad for spill 17 og for referansen «alle teller på vei».

**Debrief-grep:** Hele kjeden står i samme båndgrammatikk som studenten brukte på telefonen, med en skrubber som spoler Ukene, over alle fire Rollers ordre. Matrisen Rolle × uke på delt skjerm viser at det er regnestykket, ikke bare mønsteret.

**Lærerflate-grep:** Matriseveggen med 60 spill × uker i Meteogrammets blå og røde, gruppert etter status. En mørk strek viser hvor hvert pågående spill står, og spill 2 (23 t, KI overtar om 1 t) er uthevet. Kostnadsbildet for klassen står ved siden av, og «Vis som tabell» gir tabellvisningen.

**Palett:** Meteogrammets palett er uendret. Nye trinn i matrisen:
- *Netto lager, divergerende:* restordre #EBC3BD (1–10), #D98D84 (11–25) og #B5423A (over 25, hvit tekst). Lager #C3D8EA, #84AED3 og #2B6CA3 (hvit tekst). Null er #EEF1F4.
- *Strømmer, sekvensiell marine/grå:* #E3E8EE (≤4), #C9D3DE (5–8), #9EB0C3 (9–14), #536D88 (15–22, hvit tekst) og #0F2A47 (23+, hvit tekst).
- *Validator (`validate_palette.js --ordinal`):* hver rampe er én hue med monoton lyshet og synlige trinn. De mørke polene har CVD-avstand 16,2, og midttrinnene 11,6. Lyseste trinn har kontrast under 2:1 mot hvitt, og de to lyseste polene skilles dårlig med CVD (5,9). Det er bare lovlig fordi hver celle bærer tallet og fortegnet.
- *Celletall:* kontrast ≥ 4,5:1 i alle trinn (marine på lyse trinn 5,6–12,8:1, hvit på mørke 5,4–14,6:1).
- *Ekstra:* kjedebåndets typede ordre er en marine kontur, forsinket uten dato er stiplet #5E6F82, og den uthevede leveransen i `06` har fyll #E3E8EE.

**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i bånd, akser, matriser og tabeller, proporsjonale sifre i de største enkelttallene (kjedens totalkostnad, Forsterkning).

**Styrke:** Én grammatikk på alle flater: boks på sann skala for beholdninger, strek for tid, celle for tall. Båndet gir det 02 manglet: et øyeblikksbilde av kjeden som leses på ett sekund, mens grafen og tallene deler kolonner, slik at «tall og grafer» er samme ting sett to ganger. Kostnaden er alltid til stede uten egen skjerm.

**Ærlig risiko:** Telefonen bærer nå bånd, bryter, fire felt og ordre. Det er luft, men ikke mye, og det må prøves på ekte 360 px. Båndets sanne skala sprenger bredden når det er mye på vei (Uke 18: 80 på vei og 38 i restordre). Telefonen bruker en fast skala som holder i de tidlige Ukene, men trenger en regel for brudd senere. Båndet kan dempe svingningene mer enn ønsket, selv uten summen. Tall-visningens 26 px-kolonner tåler tresifrede kronebeløp bare så vidt.

**Gjenbrukbart selv om konseptet velges bort:** Det som er på vei, tegnet som bokser per leveranse på samme skala som lager og restordre, med ordren som rykker ett steg mot lageret hver Uke.
