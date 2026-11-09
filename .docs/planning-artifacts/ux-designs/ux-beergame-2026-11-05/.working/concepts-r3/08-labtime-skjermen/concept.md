# 08 Labtime-skjermen

**Tese (én setning):** Laptopen i Labtime er hovedflaten: ett fast rutenett med fem ruter (Kjede, Graf, Ordre, Tall, Kostnad) som står samtidig og deler tidsakse, og telefonen, Debriefen og plenum er samme rutenett med flere eller færre ruter.

**Sammensetning:**
- *Laptop, 1440 (`05-spill.svg`, `01-landing.svg`):* Kjeden går over hele bredden øverst. Under står meteogrammet til venstre, og rett under det matrisen, kolonne for kolonne på samme uker. Til høyre står Ordre øverst og Kostnad under. Ordren på 24 står fire steder: bakerst i køen i kjeden, som mørk stolpe og åpen ankomst i grafen, i to celler i tabellen og på knappen.
- *Kjeden* er speilvendt i forhold til 04: nedstrøms (Detaljist) til venstre og oppstrøms (Distributør) til høyre, i samme rekkefølge som Rollene står i overalt ellers. Varer går mot venstre og ordre mot høyre. Da leses køen *På vei* i samme retning som tidsaksen: Uke 12 nærmest lageret, Uke 15 lengst ute. Lager og restordre er bokser på sann skala over og under én grunnlinje, med samme fortegn som i grafen.
- *Telefon (`05`, `06`):* den reduserte utgaven av samme rutenett. Kjede og Ordre står fast. Graf, Tall og Kostnad er de tre andre rutene, én om gangen bak faner. Tabellen viser de seks siste ukene og fire uker fram.
- *Debrief og delt skjerm (`07`):* samme ruter for hele kjeden: kjeden med fire ledd og kundene, med en ukeskrubber; fire Rollers netto lager og ordre på samme akse; Rolle × Uke som tall rett under stolpene; kostnad per Rolle og art.
- *Faglærer (`08`) og plenum (`09`):* matriseveggen 60 spill × uker er Tall-ruta for klassen. Ved siden av står klassens kjede (median), klassens netto lager per Rolle over tid (Graf) og klassens kostnad (Kostnad). Plenum har to tilstander: under Labtime bare status, etter Spillfrist hele klassen i rutenettet.
- *Hva leder hvor:* på laptop leder grafen, med tabellen som bevis under. På telefon leder kjeden og ordren. I Debriefen leder kjeden og forsterkningen. På lærerflaten leder «Hva skjer nå» og veggen.

**Faglig kjerne:** Konseptet gjør P1 og P3 best, fordi graf og tall står i samme kolonne. P1: i tabellen står netto lager −9, levering 4 og ordre inn 8 i samme kolonne som den røde stolpedelen på 4, og summen −13 står rett under. P3: kjeden viser det som er på vei som en kø av bokser på samme skala som lageret, så en tom lagerboks ved siden av en lang kø (Uke 18: restordre 38, 80 på vei, 39 uten dato) blir synlig uten regning. P2 sitter i køen og i den dobbelt tegnede ordren. P8 er en egen rad og en egen rute: ukekostnaden farges rød (restordre) eller blå (lager), og kostnadsruta deler totalkostnaden i to arter. P4, P5 og P6 ligger i Debriefen (Rolle × Uke under ordrestolpene, røde punkter for første ordre på 10 eller mer, forsterkning 1,8× → 7,6×). P7 står på `10-pedagogikk.svg` (Uke 18). `e08grid.py` stopper bygget hvis materialbalansen, kostnaden per uke og art, kjedekostnaden, ordre inn = Idas ordre to uker før, eller klassens kjedekost ikke stemmer med loggen.

**Spilldynamikk:** Uka åpner med ny levering og ny ordre inn, og den bakerste plassen i køen står tom og stiplet. Sara taster 24, og boksen legger seg bakerst i køen og i tabellens Levering-rad under Uke 15. Etter bekreftelsen viser skjermen hvem Uka venter på. Neste Uke rykker boksene ett steg mot lageret (under 2 sekunder, kan hoppes over), og i Uke 15 kommer 17 av 24. Kostnaden for Uka står i tabellen og i kostnadsruta, så Sara ser at restordre koster dobbelt før hen bestemmer neste ordre.

**Hjelpegrad:** Standpunkt: tallene vises, summen gjør det ikke, før etter Debriefen.
- *Klassespill:* Kjede, Graf, Tall og Kostnad med setets egne tall. Lager, restordre og På vei står i hver sin rad og som bokser. Posisjon finnes bare som regnestykke ett trykk unna («Regnestykket»), aldri som egen rad eller linje.
- *Replay:* Posisjon blir en egen rad i tabellen, kjeden får linja «Posisjon = 0 − 13 + 16 = 3. Med 24: 27», og meteogrammet får den stiplede projeksjonen.
- *Hvorfor:* Kjeden gjør På vei svært synlig, og det skjerper spenningen i issue #22. Køen viser mengden, men ikke summen. En ferdig Posisjon-rad ved siden av ordrefeltet er ett lite steg fra en bestill-opp-til-regel, og ville gjort fasiten for lett. Studenten skal først kjenne svingningen, så bruke innsikten i Replay. Forskjellen er tegnet på `05-spill.svg` nederst til høyre.
- *Plenum:* under Labtime viser lerretet bare status (spillnummer, Uke, Venter, Pause), ingen tall og ingen navn. Hele klassen vises først etter Spillfrist, fordi andre spills kurver ellers ville røpe svingningene før studentene har opplevd dem.

**Kostnadsbilde:**
- *Under spillet:* Sara ser bare sin egen kostnad: Totalkostnad i toppen, ukekostnad som egen rad i tabellen (rød familie for restordre, blå for lager), og kostnadsruta med Lagerkostnad 43,00 og Restordrekostnad 25,00 = 68,00 kr i Uke 11, akkumulert som stablet flate, og «Denne Uka: 13 restordre × 1,00 = 13,00 kr».
- *Etter spillet:* kjedens kostnad først (2 266,00 kr), så per Rolle og art (lager 901,00, restordre 1 365,00, altså 60 %), og kjedens kostnad per Uke. I Debriefen sammenlignes den med Simulert: bare Sara teller på vei 1 507,00 og alle fire teller på vei 1 341,00.
- *Faglærer, aggregert:* kjedekost per spill i veggen, fordeling av 41 ferdige spill med midterste halvdel og median 1 954 mot fjorårets 2 740, og klassens kostnad per Uke delt i lager og restordre.

**Aggregater regnet i `build.py`:**
- Median netto lager og median ordre per Rolle og Uke over de 41 ferdige spillene. De brukes i klassens kjede i Uke 15 og i fire kurver over tid.
- Kostnad per spill og Uke fra `netto_lager`: positiv × 0,50 og negativ × 1,00. Summen er kontrollert mot `kjedekost` innenfor 0,50, fordi fixture runder til hele kroner.
- Klassens kostnad per Uke er summen over ferdige spill, delt i lager og restordre.
- Medianen av kjedekost er kontrollert mot `klasse.ferdige`.
- Kjedens kostnad per Uke i spill 17 er summen av fire Roller, delt i art og kontrollert mot `kjedekost` 2 266,00 og mot simulerte 1 507,00 og 1 341,00.

**Debrief-grep:** Gruppa ser samme fem ruter som i Labtime, nå med fire ledd: kjeden med ukeskrubber øverst, og under den ordrestolpene per Rolle med Rolle × Uke som tall i de samme kolonnene, slik at forsterkningen kan både ses og regnes.

**Lærerflate-grep:** Matriseveggen er klassens Tall-rute, og klassens kjede, netto lager og kostnad står ved siden av, så Oversikt, plenum og studentens skjerm deler samme rutenett.

**Palett:** Meteogrammets palett uten avvik. Nye matrisetrinn:
- *Celler med tall, netto lager:* blå #E3EDF7, #C2D8EC, #9CBFDF ved lager 1–9, 10–19 og 20+. Rød #F9E8E6, #EFC9C4, #E2A49C for restordre med samme grenser. 0 er hvit.
- *Strømmer, marine/grå:* #F2F5F8, #D9E1E9, #BCC9D6.
- *Kostnadscellene* bruker samme blå og røde trinn etter art.
- *Validering:* Tall i cellene står i #0F2A47 med kontrast minst 6,9:1. `validate_palette.js --ordinal` består for monotoni, avstand mellom trinn (ΔL ≥ 0,06) og én kulør. Det lyseste trinnet feiler 2:1-gulvet mot hvit med vilje, fordi tallet i cella bærer verdien og fargen bare er støtte.
- *Matriseveggen uten tall:* blå #97B9D9, #6597C6, #2B6CA3, #1A4670 og rød #E2A9A2, #CD7A70, #B5423A, #7E2C26 ved |verdi| 3–10, 11–25, 26–45 og over 45. Midtpunktet er #EEF1F4 ved |verdi| ≤ 2. Begge armer består alle ordinale kontroller. Veggen har tabellvisning.

**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i tall, akser og matriser, og proporsjonale sifre i de største enkelttallene. Laptopen bruker 12–13 px i ruter og 26 px for Uke. Telefonen bruker minst 13 px. Plenum er tegnet for lerret i 1280 × 720 med 18–40 px.

**Styrke:**
- Alle fire delene står samtidig uten å konkurrere: grafen og tabellen deler kolonner, kjeden deler fortegn og skala med grafen, og kostnaden har fast plass.
- Rutenettet er det samme på alle flater, så Labtime lærer studenten telefonen og Debriefen.
- Speilvendingen gjør at «på vei» og tidsaksen peker samme vei.
- Plenum har en ærlig regel for når klassedata kan vises.

**Ærlig risiko:**
- Laptopen er tett: fem ruter og om lag 120 celler på én skjerm. Det krever disiplin for at den ikke skal bli et instrumentpanel, og den må testes på en vanlig 1366-skjerm.
- Speilvendt kjede bryter med lærebøker som tegner fabrikken til venstre. Noen lærere vil reagere.
- På telefonen er kjedebåndet smalt: boksene for På vei blir små, og «uten dato» får bare et spørsmålstegn.
- Når Posisjon er tatt ut, men køen synes så godt, kan køen alene dempe svingningene mer enn ønsket. Det vet vi ikke uten test.
- Plenum etter Spillfrist kommer sent for studenter som spiller i siste Labtime.

**Gjenbrukbart selv om konseptet velges bort:** Kjeden speilvendt slik at køen *På vei* leses i samme retning som tidsaksen, med tabellen rett under grafen i de samme kolonnene.
