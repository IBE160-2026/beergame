# 02 Meteogrammet (arbeidsnavn Prognose)

**Tese (én setning):** Forsyningskjeden leses som værvarselet: stablede felt på én tidsakse, en loddrett nå-strek, historikk til venstre og bare det som er kjent til høyre, slik at Sara ser ordren sin stå der den kommer fram fire uker senere.

**Faglig kjerne:** P2 og P3 gjør konseptet best. Hver ordre står to ganger, som mørk stolpe i feltet Din ordre og som åpen stolpe fire Uker fram i feltet over, med en tynn diagonal mellom dem. Det er forsinkelsen, tegnet (P2). De åpne stolpene er på vei-tallet delt ut på uker, og summen blir Posisjon (P3). P1 sitter i midtfeltet: stablet stolpe med levering og ordre inn, der rød eller blå del er nøyaktig det netto lager endrer seg den Uka. Regnestykket stemmer med loggen på alle 36 uker, og `d02lib.py` stopper bygget hvis det ikke gjør det. Debriefen dekker P4, P5 og P6 med fire felt på samme akse og kundene som et rolig bånd nederst. P7 og P8 står i Ditt øyeblikk og på `10-pedagogikk.svg`.

**Spilldynamikk:** Uka åpner med ny levering og ny ordre inn, og plassen fire Uker fram står tom. Sara taster et tall, og tallet står straks to steder: nederst der hen bestemmer det, og i Uke 15 der det kommer. Etter bekreftelsen viser skjermen hvem Uka venter på. Så flytter nå-streken seg én Uke på under 2 sekunder, og kan hoppes over. Fra Uke til Uke rykker den åpne stolpen mot streken, og i Uke 15 blir det 17 i stedet for 24. Da lærer hen at det hen får nå, er det hen bestemte for fire Uker siden, og at bestilt ikke er det samme som levert.

**Hjelpegrad:** Standpunkt: den stiplede projeksjonen av netto lager er av i Klassespillet og åpnes i Replay, etter Debriefen.
- *Klassespill:* de tre feltene, kjente ankomster til høyre for nå, merket «Bestilt, ikke garantert». Posisjon ligger ett trykk unna under Alle tall, som regnestykke uten fasit.
- *Replay:* samme skjerm, med stiplet linje og usikkerhetsbånd. Når Sara taster, flytter linja seg med en gang.
- *Hvorfor:* Linja er summen øvelsen handler om. Sluttpunktet er Posisjon + ordre − 4 × ordre inn (27 − 32 = −5 i Uke 11), og det er bare ett lite regnesteg unna en ordre-opp-til-regel. Med linja på ville studenten dra den til null og få fasiten uten at vi sier den. Det ville svekket den erfaringen Debriefen trenger (issue #22). Simuleringen peker samme vei: når alle teller det som er på vei, faller Fabrikk fra 7,6× til 3,3×. Ankomstene er setets egne, kjente tall og løser ikke summen for hen, men vi vet ikke uten test hvor mye de alene demper svingningene.
- Forskjellen er tegnet på `05-spill.svg` (nederst til høyre) og beskrevet på `10-pedagogikk.svg`.
- *Projeksjonen er bevisst ærlig:* fra Uke 15 har Sara bestilt varer som er forsinket hos leverandøren (opptil 63 enheter). De har ingen dato, så de legges ikke inn som ankomst, men vises som et bånd. I Uke 18 viser den «Planlagt −18 til 21». Det ble −40. Høyre kant er alltid nå + 4 og aldri slutten av spillet.

**Debrief-grep:** Avsløringen legger Saras ordrer og ordre inn over et rolig bånd med kundenes 4 og 8 på sann skala, og deretter står fire Roller på samme akse med en rød linje gjennom første Uke med ordre på 10 eller mer (Uke 6, 11, 13, 15).

**Lærerflate-grep:** En rolig liste over 60 spill med «Hva skjer nå» øverst, der hvert spill har en stripe med netto lager for fire Roller, slik at Faglærer ser svingningene og hvor langt spillet er kommet i samme rad.

**Palett:** Hvit #FFFFFF, marine #0F2A47 (tekst og ordre), sekundær #44586F, dempet #5E6F82, rolig blå #2B6CA3 med fyll #CDDFEE (over null), dempet rød #B5423A med fyll #F0D5D2 (under null), grå #6B7785 (projeksjon), stolpegrå #B4C4D4 og #5F7A95, flate #F2F5F8 (til høyre for nå). Blå og rød bestod `validate_palette.js` med CVD-avstand 16,2. Rolle og status bæres alltid av tekst, ikke farge.
**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i tall og akser, proporsjonale sifre i de største tallene.

**Styrke:** Grammatikken er kjent fra før, og hver ordre synes der den kommer. Arket i `10-pedagogikk.svg` viser projeksjon mot fasit fire ganger, så studenten ser hvorfor linja er regning og ikke løfte. Samme graf går igjen fra telefon til Debrief og lærerflate.

**Ærlig risiko:** Tre felt er mye på en telefon, selv om de deler akse: testen av at studenten forstår uten forklaring er ikke gjort. Rød stolpedel krever litt lesing første gang. Selv uten linja kan ankomstene dempe svingningene mer enn vi vil, og da må også de vurderes. Og når leverandøren henger etter, bommer linja kraftig. Det er ærlig, men kan oppleves som at grafen «tar feil». Tegningene er statiske, så flyttingen av tallet og overgangen i rute D må prøves i prototype.

**Gjenbrukbart selv om konseptet velges bort:** Ordren tegnet to ganger på samme tidsakse, med en diagonal mellom beslutningen og ankomsten.
