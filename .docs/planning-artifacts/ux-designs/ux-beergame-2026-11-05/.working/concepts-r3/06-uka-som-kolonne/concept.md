# 06 Uka som kolonne

**Tese (én setning):** Kjeden, meteogrammet og matrisen er samme ting sett fra tre avstander: hver Uke er en kolonne med kjedens tilstand som tall, meteogrammet tegner de samme kolonnene, og kjedevisningen øverst er én kolonne forstørret, koblet til den med to tynne linjer.

**Sammensetning:**
- *Telefon (Klassespill):* tre lag på én kolonneakse. Øverst står setets ledd for den valgte uka (standard: nå): Sendt, Lager eller Restordre, Levering og På vei med fire bokser på sann skala. Boksene står i samme rekkefølge som kolonnene for Uke 12 til 15. I midten ligger netto lager fra Meteogrammet. Nederst står matrisen med 12 kolonner (nå − 7 til nå + 4) og radene Ordre inn, Levering, Lager, På vei, Din ordre, Kostnad og Sum. Kostnad per uke er nest siste rad, akkumulert kostnad er siste rad. Trykker studenten på en tidligere kolonne, viser kjeden den uka, og en «Tilbake til Uke 11» tar hen tilbake. Ordren tegnes to ganger, i Din ordre og i Levering fire kolonner fram, med Meteogrammets diagonal mellom dem.
- *Retning:* Ordrene går mot høyre (oppstrøms), og varene kommer mot venstre, mot nå. Det er motsatt av 04, men slik ligger boksene på vei i samme rekkefølge som kolonnene. Med fire ledd står kjeden derfor som Kunde, Detaljist, Grossist, Distributør, Fabrikk fra venstre.
- *Debrief:* steg 3 er hele kjeden med fire ledd og kunden i Uke 18, med zoomlinjer ned til kolonnen i ordregrafen (fire rader) og i tabellen Kunde/Rolle × uke. Steg 4 viser Uke 11 for alle fire ledd, tabellen Rolle × uke for netto lager med radene Kjeden, kr og Kjeden, sum, og kjedens kostnad som Rolle × kostnadsart.
- *Faglærer:* veggen 60 spill × 36 uker (netto lager for valgt Rolle). Over den står klassens kjede for valgt uke (median over spillene som har nådd uka), og zoomlinjene går ned til kolonnen. Under veggen står klassens rader med median og kroner per uke, på de samme kolonnene.
- *Hva leder:* På telefonen leder tabellen med kjeden som «lupe», og grafen er bindeleddet. I Debriefen leder grafen, med tallene rett under. På lærerflaten leder veggen.

**Faglig kjerne:**
- *P1:* lager etter forrige Uke + levering − ordre inn står loddrett i kolonnen, og grafen over viser det samme. Startoppgaven er å fylle inn én slik kolonne.
- *P2:* ordren står i Din ordre og i Levering fire kolonner fram, og nå-streken rykker mot den (06, nederst).
- *P3:* de fire boksene på vei står ved siden av restordren i kjeden og under den i tabellen. Summen gjør studenten selv.
- *P8:* restordre gir rød kostnadscelle, og Sum-raden gjør kostnaden synlig Uke for Uke. Debriefen deler kjedens 2 266,00 kr på Rolle og kostnadsart.
- *P4, P5, P6:* Debriefens Kunde/Rolle × uke viser at kunden står på 8 mens ordrene vokser oppstrøms.
- *P7:* står i Debriefen og på `10-pedagogikk.svg`.
- *Kontroll:* `e06lib.py` stopper bygget hvis noe ikke stemmer med loggen for alle uker, alle Roller og alle fire datasett. Den sjekker materialbalansen, På vei-balansen, sendt ≤ tilgjengelig, ukeskostnad = lager × 0,50 + restordre × 1,00 = endringen i kost_sum, summen per Rolle, kjedekost, at klassens kjedekost stemmer med netto_lager, og Saras skjerm i Uke 11.

**Spilldynamikk:** Uka åpner med en ny kolonne der levering, ordre inn, lager og kostnad er fylt ut og Din ordre står tom. Sara taster 24. Tallet står i kolonnen nå, i Levering fire kolonner fram og som siste boks i kjeden. Etter bekreftelsen ser hen hvem Uka venter på. Så flytter nå-streken seg én kolonne, og kjeden viser Uke 12. Uke for Uke rykker streken mot 24-cellen, og i Uke 15 står det 17. Tabellen gjør det mulig å kontrollere bildet: det som er tegnet, kan regnes.

**Hjelpegrad:** Standpunkt: Klassespillet viser bare det loggen inneholder. Avledede størrelser låses opp i Replay.
- *Klassespill:* kjeden, netto lager og radene Ordre inn, Levering, Lager, På vei, Din ordre, Kostnad og Sum. Kjente ankomster står til høyre for nå, merket som bestilt (åpne celler). Det finnes ingen Posisjon-rad, ingen projeksjon og ingen anbefalt ordre. «Kolonnen som regnestykke» viser P1-regningen for kolonnen, ikke posisjonen.
- *Replay (etter Debriefen):* raden Posisjon kommer under Din ordre, med «3→27» i nå-kolonnen. Projeksjonen fra Meteogrammet åpnes også.
- *Hvorfor:* Kjeden gjør På vei svært synlig allerede, med fire bokser ved siden av restordren. Studenten skal få legge sammen selv, eller la være, og kjenne kostnaden av det før Debrief-quizen spør etter summen (issue #22). En egen Posisjon-rad ville vært ett lite steg fra en ordre-opp-til-regel. Forskjellen er tegnet nederst til høyre på `05-spill.svg` og beskrevet på `10-pedagogikk.svg`.

**Kostnadsbilde:**
- *Under spillet:* studenten ser bare sin egen kostnad, i raden Kostnad (rød fyll for restordre, blå for lager) og Sum, og som Totalkostnad i toppen.
- *Når spillet slutter (06 F):* først kjedens 2 266,00 kr, så restordre 1 365,00 og lager 901,00. Deretter per Rolle, med stolpen delt på art.
- *Debriefen:* Kjeden, kr per uke og Kjeden, sum på samme kolonner som netto lager. Tabellen Rolle × kostnadsart. Simulert sammenligning: Grossist 553,50 mot 464,50, kjede 2 266,00 mot 1 507,00, og «alle fire teller» 1 341,00. Alt merket Simulert.
- *Faglærer:* klassens kroner per uke (sum over spill, delt på restordre og lager), akkumulert 101 037 kr så langt, median kjedekost per uke i den valgte kolonnen, og kjedekost per ferdig spill som prikkstripe med median 1 954 kr mot fjorårets 2 740 kr.
- *Aggregater regnet i `e06lib.class_aggregates()` fra `klasse.spill`:* for hver uke k brukes spillene med uke ≥ k (n), og vi regner ut median netto lager per Rolle, ukeskostnad per spill = Σ over Roller av (positiv × 0,50, negativ × 1,00), median og sum av disse, og akkumulert sum. Delingen i restordre og lager regnes i `build_08`. Summen per spill kontrolleres mot `kjedekost`.

**Debrief-grep:** Kjeden med fire ledd er bare kolonnen for den valgte uka, forstørret over ordregrafen og tabellen Kunde/Rolle × uke. Gruppa trykker på en kolonne og ser hvor varene og restordrene sto akkurat da.

**Lærerflate-grep:** Klassens kjede (median netto lager per Rolle) står over veggen med 60 spill × uker og er koblet til den valgte kolonnen. Under veggen står klassens kroner per uke på de samme kolonnene.

**Palett:** Meteogrammets palett uendret. Nye matrisetrinn er validert med `validate_palette.js --ordinal`, og alle sjekker bestod.
- *Lager:* #98B8D8, #6E9BC7, #2B6CA3, #1B4870.
- *Restordre:* #E3A79F, #D27A70, #B5423A, #82302A.
- *Strømmer (10+, 15+, 20+):* #A3B4C7, #7F96AD, #2C4763.
- *Null:* ingen fyll, eller #EEF1F4 på veggen.
- *Kontrast og trinn:* celletall i marine på de to lyse trinnene og hvitt på de to mørke, alle ≥ 4,5:1. Trinnene ligger ved 10, 20 og 30 enheter, og på veggen ved 13, 25 og 49. Fortegnet står alltid i tallet, så farge bærer ikke status alene.
- *Kostnad:* restordre i rød familie, lager i blå. Stolpene bruker polfargene #B5423A og #2B6CA3, som bestod med CVD-avstand 16,2.

**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i alle celler, akser og tabeller, og proporsjonale sifre i de største enkelttallene (24, 2 266,00 kr).

**Styrke:** Tall og graf kan ikke komme i utakt, for de er samme kolonne. Studenten kan alltid kontrollere tegningen med regnestykket, og det er det testforskningen sier viser forståelse. Kjeden blir ikke et fjerde panel, men en lupe på tabellen. Samme grammatikk bærer telefonen, Debriefen og veggen med 60 spill.

**Ærlig risiko:**
- Telefonen er tett. 12 kolonner × 7 rader med 13 px tall er lesbart på 390 px, men krever disiplin, og det er ikke testet på 360 px.
- Varer mot venstre kan forvirre dem som har sett kjeden tegnet motsatt vei.
- Zoomlinjene er svake og kan oppfattes som pynt før noen har trykket på en kolonne.
- Tallene i cellene kan gjøre det lettere å regne ut posisjonen selv i Klassespillet enn med en ren graf.

**Gjenbrukbart selv om konseptet velges bort:** Ordrene på vei i kjeden tegnet som bokser i samme rekkefølge som de kommende kolonnene, slik at kjedevisningen og tabellen kan leses som samme ting.
