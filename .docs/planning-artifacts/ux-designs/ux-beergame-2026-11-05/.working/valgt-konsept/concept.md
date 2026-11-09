# Valgt design: Graf over tabell, med Debrief og kostnad fra Labtime-skjermen

**Tese (én setning):** Som et ekte meteogram står grafen øverst og tabellen rett under, kolonne for kolonne på samme ukeakse, med kjedebåndet over og nå-streken gjennom alt; kostnaden er et fast panel med to kostnadsarter, sum og regnestykket for uka, og Debriefen leder gruppa fra Forklaring til Kjedens regning.

**Sammensetning:** Én grammatikk på alle flater, ovenfra og ned: kjedebånd, graf (netto lager og kost per uke), tabell med én kolonne per uke, og nå-streken gjennom alt. Ordren på 24 står både der den bestilles (Din ordre, Uke 11) og der den kommer (Levering, Uke 15).
- *Telefon (Klassespill):* setets eget ledd som kjedebånd, grafen, seks rader for Uke nå − 7 til nå + 4 og ordrefeltet, som i 04. «Alle rader og kostnad» er ett trykk unna (lenken ved ordrefeltet eller Totalkostnad). Det åpnede panelet har alle rader på samme akse, regnestykket for netto lager og **Kostnad så langt**.
- *Laptop i Labtime:* kjedebånd og graf over tabell til venstre, Uke 1 til 15. Til høyre står ordrefeltet, og rett under det **Kostnad så langt**, alltid synlig, som i 08.
- *Debrief:* 08s fem steg og delte skjerm, portert til 04s grammatikk: klimaksgrafen over en tabell (Uke, Kundene, Ordre inn, Din ordre), hele kjeden med skrubber og ordrestolper for fire Roller over Rolle × Uke som tall i de samme kolonnene, «Dette så du» som graf over tabell, og Kjedens regning som tabell per Rolle og kostnadsart.
- *Faglærer:* klassens median netto lager over matriseveggen 60 spill × 36 uker, med bunnrader og en synlig bryter «Vegg / Vis som tabell».
- *Hva leder hvor:* grafen leder på telefon og i Debriefen, tabellen leder på lærerflaten, kostnadspanelet står fast ved ordren på laptop.

**Kjedens retning (én konvensjon for hele produktet):** Oppstrøms til venstre. Varene går mot høyre, fra Fabrikk mot Detaljist og kunden. Ordrene går mot venstre. Det gjelder setets kjedebånd (Distributør til venstre, Detaljist til høyre), hele kjeden i Debriefen og på delt skjerm, Klasseøkt og kontaktarket. 08s Debrief-kjede er speilvendt for å følge dette. Rader som lister Rollene oppover kjeden (ordrestolpene, delt skjerm), har Fabrikk øverst. Tabeller per Rolle (Kjedens regning) går fra Detaljist til Fabrikk, i den rekkefølgen forsterkningen vokser.

**Faglig kjerne:** P1 og P2 bæres av tabellen: kolonnen regnes nedover (−9 + 4 − 8 = −13 i Uke 11), og ordren står to ganger med en tynn linje mellom. P3 bæres av kjedebåndet (På vei som bokser på røret) og raden På vei. P8 bæres nå av to ting: kostfeltet i grafen (rød stolpe restordre til 1,00, blå lager til 0,50) og kostnadspanelet, der Lagerkostnad 43,00 og Restordrekostnad 25,00 summeres til 68,00 kr og uka regnes ut som 13 restordre × 1,00 = 13,00 kr. P4, P5 og P6 ligger i Debriefens steg 3: ordrestolper for fire Roller med røde punkter for første ordre på 10 eller mer (Uke 6, 11, 13, 15), forsterkning 1,8× → 7,6×, og tallene rett under. P7 står i Ditt øyeblikk og på `10-pedagogikk.svg`. `vlib.py` stopper bygget hvis materialbalansen, ukeskost, kjedekost, klassens kjedekost, kostnadspanelet (43,00 + 25,00 = 68,00), Kjedens regning mot `kost_per_rolle` (901,00 / 1 365,00 / 2 266,00), Simulert 1 507,00 og 1 341,00, skalaregelen for kjedebåndet eller kontrasten ikke stemmer.

**Spilldynamikk:** Uka åpner med en ny kolonne der Ordre inn og Levering allerede står, og cellen under Din ordre er stiplet. Sara taster 24, og tallet står straks i to celler: nå, og under Levering i Uke 15; kjedebåndet viser 16 + 24 på røret. Etter bekreftelsen sier skjermen hvem Uka venter på, og nå-streken flytter én kolonne på under 2 sekunder. Når uka er regnet, står regnestykket for uka («Denne uka: 20 restordre × 1,00 = 20,00 kr»), og Kostnad så langt er ett trykk unna, så neste ordre bygger på regnestykket og ikke på en fasit.

**Hjelpegrad:** Standpunkt: delene vises, summen låses opp i Replay.
- *Klassespill:* kjedebånd, graf, Netto lager og På vei i hver sin rad, kjente ankomster merket som bestilt, ikke garantert, og kostnaden med regnestykket. Ingen Posisjon-rad og ingen projeksjon.
- *Replay (etter Debriefen):* raden Posisjon og den stiplede linja åpnes (3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg, ikke garantert).
- *Hvorfor:* En ferdig Posisjon-rad er ett lite steg fra en ordre-opp-til-regel og tar bort erfaringen Debriefen trenger (issue #22). Kostnadspanelet viser hva det koster, ikke hva som er riktig å bestille. Forskjellen er tegnet på `05-spill.svg` nederst til høyre.

**Kostnadsbilde:**
- *Under spillet (setet):* Totalkostnad øverst, kostfeltet i grafen og raden Kost, kr i tabellen (uke for uke), og panelet **Kostnad så langt**: Lagerkostnad og Restordrekostnad med strek og sum, Totalkostnad, Totalkostnad over tid som stablet areal fra Uke 1 til nå, og regnestykket for uka. Panelet står fast ved ordrefeltet på laptop og er ett trykk unna på telefon. Raden «Sum, hele kr» er tatt ut der panelet står (laptop, Alle rader, pedagogikk), fordi den sa det samme som panelet med svakere form.
- *Spillslutt (gruppa):* kjedens totalkostnad 2 266,00 kr først, så Kjedens regning per Rolle og kostnadsart med strek og sum, og kjedens kostnad over tid som stablet areal.
- *Debrief:* Kjedens regning med Kjeden 901,00 / 1 365,00 / 2 266,00 under en strek, og Simulert (bare Sara teller på vei 1 507,00, alle fire 1 341,00). Restordre er 60 % av regningen.
- *Faglærer, aggregert:* kjedekost per spill i veggen, fordeling i 41 ferdige spill med fjorårets median, snitt per Rolle delt i lager og restordre, og kjedekost per uke, snitt per spill.
- *Aggregater:* regnet i `screens_debrief_teacher.py` fra `klasse.spill` som i 04: median og kvartiler av netto lager per Rolle og uke; ukeskost per spill fra netto lager (positiv × 0,50, negativ × 1,00), snitt per spill som har spilt uka; snitt per Rolle og kostnadsart i ferdige spill, kontrollert mot `kost_per_rolle`; kjedekost per spill kontrollert mot netto lager for alle 60. Kjedens kostnad over tid (`ChainSum` i `vlib.py`) er summen av fire Rollers akkumulerte lager- og restordrekost, kontrollert mot 901,00 og 1 365,00.

**Debrief-grep:** Gruppa skriver Forklaringen før avsløringen, ser kundene bestille 4 og så 8, spoler hele kjeden med skrubberen over ordrestolper og Rolle × Uke i samme kolonner, og ender i Kjedens regning, der 2 266,00 kr står mot Simulert 1 341,00.

**Lærerflate-grep:** Klassens median netto lager står over matriseveggen 60 spill × 36 uker på samme kolonner, med bunnrader, og «Vis som tabell» er en synlig bryter rett over veggen.

**Palett:** Meteogrammets palett uendret, og 04s matrisetrinn: netto lager under null #E1A098, #CF776D, #B5423A, #8C2C25; over null #93B8DB, #6A9AC8, #2B6CA3, #1B4A75; null #F2F5F8; strømmer #A7B6C6, #8396AC, #56708B, #0F2A47. Tall i cellene er marine på de to lyse trinnene og hvite på de to mørke, alle ≥ 4,5:1 (kontrollert i `vlib.py`). Kostnadspanelet bruker blå #2B6CA3 / #CDDFEE for lager og rød #B5423A / #F0D5D2 for restordre, samme roller som overalt ellers. Ingen nye farger.
**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i celler, akser og tabeller; proporsjonale sifre bare i de største enkelttallene (2 266,00 kr, forsterkning). Telefon minst 13 px. Ingen tekst under 9 px utenom kontaktarket (kontrollert i bygget og i `sjekk.py`).

**Styrke:** Graf og tall kan alltid kontrolleres mot hverandre i samme kolonne, og kostnaden er nå et regnestykke med fast plass, ikke bare en stolpe. Debriefen har en tydelig bue fra Forklaring til Kjedens regning, og kjeden går samme vei på alle flater.

**Ærlig risiko:** Telefonen er like tett som i 04 (kjedebånd, to felt og seks rader), og 360 px må prøves med ekte studenter. Laptopen er tettere enn i 04, fordi kostnadspanelet står fast ved ordren. Kostnadspanelet gjør kostnaden svært synlig, og det er ikke testet om det frister til overreaksjon (P7). Skalaregelen gjør at boksen for forsinket uten dato ikke lenger er på sann skala; tallet over boksen bærer mengden. Landingssiden er roligere og mindre overbevisende når den bare kan vise en Veiledet uke. Lærerveggens celler er fortsatt små; tabellvisningen er tegnet som bryter, ikke som eget ark. Fjoråret har bare median i fixture.

**Gjenbrukbart selv om konseptet velges bort:** Kostnadspanelet med to kostnadsarter, sum, stablet areal og regnestykket for uka.

**Opphav:**
- `01-landing`: 04s grammatikk og layout; kostnadspanelet fra 08; seksjon to er ny (status og framdrift uten lagerkurver).
- `02-laerer-klasse`, `03-laerer-spill`, `04-student-hjem`: fra 04 (som bygget på 02s Klasseøkt og skjema).
- `05-spill`: telefon og hjelpegrad fra 04; «Alle rader og kostnad» fra 04 med 08s kostnadspanel; laptop fra 04 med ordrefelt og Kostnad så langt fra 08.
- `06-spilldynamikk`: fra 04; D har regnestykket for uka og lenken til panelet; F har Kjedens regning i 08s form og kjedens kostnad over tid i 08s stablede areal.
- `07-debrief`: struktur, innhold og rekkefølge fra 08 (som bygget på 02s Debrief); steg 1 og 2 i 04s graf-over-tabell-form; kjeden fra 04 (speilvendt i forhold til 08); Rolle × Uke-tabellen med 04s trinn; «Dette så du» fra 04.
- `08-laerer-oversikt`: fra 04, med synlig «Vis som tabell» og tekst ≥ 9 px.
- `09-alle-sider`: fra 04.
- `10-pedagogikk`: fra 04; kostnadsdelen for Uke 5, 11, 18 og 29 i 08s panelform; skalaregelen for kjedebåndet er ny.

**Endret etter runde 3 (issue #24):**
- *Retning i kjeden:* én konvensjon på alle flater (over); 08s Debrief-kjede speilvendt.
- *Landingssiden:* viser ikke lenger Ordre inn som stiger. Setet vises i Uke 4 (Veiledet uke), før noe har endret seg, og lærerens oversikt viser status, framdrift og hvem spillet venter på, uten lagerkurver. `sjekk.py` kjører truthscan-logikken på mappa: 0 treff.
- *Lærerveggen:* synlig bryter «Vegg / Vis som tabell» over veggen, og ingen tekst under 9 px (bygget stopper ellers).
- *Kjedebånd på sann skala:* skalaregel. Kjente ankomster (de fire neste ukene) står alltid på sann skala, 1,4 px per enhet på telefon. Det som er forsinket uten dato, får fast bredde med merket brudd og tallet skrevet over. Bygget kontrollerer at båndet passer på telefonen i alle 36 uker. Vist i `10-pedagogikk.svg`, Uke 18 (39 uten dato).
- *Gjenstår:* tett telefon må prøves på 360 px med studenter; om tydelig kostnad frister til overreaksjon er ikke testet; fjoråret har bare median.
