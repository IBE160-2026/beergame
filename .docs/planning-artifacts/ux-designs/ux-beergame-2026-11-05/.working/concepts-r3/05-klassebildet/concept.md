# 05 Klassebildet

**Tese (én setning):** Faglærer ser hele klassen som én matrisevegg med 60 spill × uker i Meteogrammets blå og røde, med klassens kostnad per uke og klassens median på samme tidsakse, kjedekostnad per spill mot fjoråret i samme rad, og klassens kjede med fire ledd ved siden av. Studenten får det samme språket i liten skala: eget ledd som kjedebånd øverst og meteogrammet under.

**Sammensetning:**
- *Lærerflaten (08) leder.* Matriseveggen står til venstre. Øverst ligger klassens kostnad per uke som stablede stolper (41 ferdige spill, alle Roller), så en medianrad med tall, så én rad per spill gruppert som Venter, Pause, Pågår og Ferdig (billigst øverst). Til høyre i hver rad står Uke, kjedekostnad som stablet stolpe (restordre rød, lager blå) med årets median og fjorårets median som loddrette linjer, KI-seter og hvem spillet venter på. Høyre kolonne har fire deler:
  - klassens kjede med fire ledd (median av 41 ferdige spill, med ukeskrubber)
  - kjedekostnad per spill som prikkplott med midtre halvdel og fjorårets median
  - hva klassen betalte for, per Rolle og kostnadsart
  - trakten og Detected patterns
- *Plenum (09, stort ark):* fire Roller med median og midtre halvdel av netto lager, rødt punkt der medianen først går under null (Uke 8 → 9 → 11 → 13), median Forsterkning og klassens fordeling på restordre og lager. Arket har ingen navn, ingen spillnummer og ingen rangering.
- *Telefon (05):* kjedebåndet øverst viser setets ledd: røret med fire rom (ett per Uke til levering, pluss et rom for det som er forsinket uten dato), lageret som boks på sann skala, sendt videre, og ordrene som en tynn marine linje motsatt vei. Under ligger Meteogrammets tre felt og ordrefeltet. Matrise og kostnad ligger ett trykk unna under «Tall og kostnad». På laptop står bånd, graf og matrise samtidig, og matrisen deler tidsakse med grafen.
- *Debrief (07):* hele kjeden med fire ledd og kunde ved Uke 18, med skrubber. Under den står matrisen Rolle × uke for ordre, med ramme rundt første Uke med ordre på 10 eller mer, og Forsterkning til høyre. Klassens median-Forsterkning står som én linje under. Kjedens kostnad vises per Rolle og kostnadsart, mot simulert referanse.

**Faglig kjerne:** P5 og P6 gjør konseptet best, og det skjer i lærer- og plenumsflatene. Veggen viser at nesten alle 41 ferdige spill har samme røde bånd som flytter seg mot høyre (P6, struktur gir atferd). Plenumsarket viser at bølgen kommer senere og går dypere oppover kjeden (P5). Kjedebåndet gjør P2 og P3 konkrete: ordren legger seg bakerst i røret og rykker ett rom per Uke, og rommet «uten dato» viser at bestilt ikke er levert. Matrisen og meteogrammet deler akse, så P1 kan leses som regnestykke (−9 + 4 − 8 = −13). Kostnadsraden i matrisen og de stablede stolpene viser P8 i alle skalaer: sete, kjede og klasse. P7 står på `10-pedagogikk.svg`. `e05lib.py` stopper bygget hvis noe ikke stemmer: materialbalansen for alle fire Roller i 36 uker, at ukeskostnaden summerer til `kost_sum`, `kost_per_rolle` og 2 266,00, de simulerte kjedekostnadene, at klassens kjedekost regnet fra `netto_lager` stemmer med `kjedekost` (±0,5 for avrunding), at spill 17 i klassen er identisk med Saras logg fram til Uke 11, og at kvartiler og medianer stemmer med `klasse.ferdige`.

**Spilldynamikk:** Uka åpner med ny levering og ny ordre inn, og røret har rykket ett rom fram. Sara ser 4, 4 og 8 i rommene og restordre 13 i boksen, taster 24, og 24 står straks bakerst i røret og fire Uker fram i grafen. Etter bekreftelsen viser skjermen hvem Uka venter på. Totalkostnaden øverst vokser med 13,00 kr fordi restordre koster 1,00 per enhet. I Uke 15 kommer 17 av 24, og 7 legger seg i rommet uten dato. Da ser Sara at det hen får nå, er det hen bestemte for fire Uker siden, og at bestilt ikke er levert.

**Hjelpegrad:** Standpunkt: rommene i røret synes, men summen gjør det ikke.
- *Klassespill:* kjedebåndet viser hvert rom med tall og «På vei 16 + 24». Meteogrammet har ingen projeksjon. Matrise, regnestykket for Posisjon og kostnadsfordelingen ligger ett trykk unna i «Tall og kostnad».
- *Replay:* Posisjon er tegnet inn under båndet («Posisjon 0 − 13 + 16 = 3. Med 24: 27»), og meteogrammet får den stiplede projeksjonen.
- *Hvorfor:* summen er nettopp det folk lar være å regne (Sterman), og Debriefen trenger at svingningen er opplevd (issue #22). Å se rommene er å se egne data. Å få summen servert er et steg mot en bestillingsregel. Risikoen er at røret alene demper svingningene. Lærerens vegg viser om det skjer, for klassen kan sammenlignes med fjoråret.
- Forskjellen er tegnet på `05-spill.svg` (Hjelpegrad, to bånd) og beskrevet på `10-pedagogikk.svg`.

**Kostnadsbilde:**
- *Under spillet* ser studenten bare sin egen kostnad: Totalkostnad i toppen, og i «Tall og kostnad» en kostnadsrad i matrisen, stolper per uke og fordelingen på restordrekost (25,00) og lagerkost (43,00).
- *Når spillet slutter (06 F og Debrief)* kommer kjedens 2 266,00 kr først, fordelt på restordre 1 365,00 og lager 901,00, og deretter per Rolle. I Debriefen står hver Rolle med en svart strek for simulert referanse (alle teller det som er på vei, 1 341,00) og en tabell mot «bare Sara teller» (1 507,00).
- *Faglærer ser aggregert:*
  - kostnad per uke for 41 ferdige spill (topp 4 832 kr i Uke 18)
  - kjedekostnad per spill som stolpe i veggen og som prikkplott (median 1 954, midtre halvdel 1 165 til 2 869)
  - fjorårets median 2 740
  - kostnad per Rolle og art: restordre 43 578 kr (53 %), lager 38 920 kr
  - hele klassen hittil: 101 037 kr

**Debrief-grep:** Kjeden med fire ledd spoles til Uke 18 over matrisen Rolle × uke. Rammen rundt første store ordre vandrer fra Uke 6 til Uke 15, og under står klassens median-Forsterkning, så gruppa ser at det ikke bare gjaldt dem.

**Lærerflate-grep:** Én matrisevegg der klassens kostnad per uke, klassens median og hvert spills netto lager deler tidsakse, og der hver rad ender i spillets kjedekostnad mot årets og fjorårets median.

**Aggregater regnet i `e05lib.py`:**
- *Median og kvartiler av netto lager* per Rolle og Uke over de 41 ferdige spillene. Kvartilene er lineært interpolert. Brukes i medianraden, klassens kjede, plenum og i 10c.
- *Median ordre* per Rolle og Uke, for tallene på klassens kjede.
- *Ukeskostnad per spill* fra `netto_lager`: positiv × 0,50, negativ × 1,00, summert over fire Roller. Summert over spill gir det klassens kostnad per uke, og summert over uker gir det spillets fordeling på lager og restordre (sjekket mot `kjedekost` og `kost_per_rolle`).
- *Median av `kost_per_rolle`* for kostnaden under klassens kjede.
- *Restordre- og lagerkost per Rolle*, summert over ferdige spill.
- *Fjoråret:* fixture har bare median kjedekost og median Forsterkning for Fabrikk. Derfor vises fjoråret som referanselinje, ikke som fordeling, og skjermen sier det.

**Palett:** Meteogrammets palett uendret. Nye matrisetrinn, kjørt gjennom `validate_palette.js --ordinal` (alle PASS):
- *Netto lager, rød arm:* #DAA09C (−1 til −4), #CB7B75 (−5 til −14), #B5423A (−15 til −29), #7E2C25 (≤ −30).
- *Netto lager, blå arm:* #95B6D1 (1–4), #6B98BF (5–14), #2B6CA3 (15–29), #1A4670 (≥ 30).
- *Null:* #F2F5F8 som nøytralt midtpunkt.
- *Strømmer, marine:* #A7B6C5 (1–4), #8FA2B5 (5–9), #56718D (10–14), #3B5674 (15–24), #0F2A47 (≥ 25).
- *Tekst i cellene:* marine på de lyse trinnene og hvit på de mørke, alle ≥ 4,5:1. Den svakeste er 4,60:1 på #CB7B75.
- *Kostnadsceller:* fyllet #F0D5D2 for restordrekost og #CDDFEE for lagerkost.

Rolle og status står alltid som tekst.

**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i tall, akser og matriser, og proporsjonale sifre i de største tallene (2 266,00 kr, Forsterkning). Veggens spillnummer for ferdige spill er 8 px, tillatt for lærerens vegg, med «Vis som tabell» som alternativ.

**Styrke:** Faglærer får ett bilde der drift (hvem venter, nær overtakelse) og faglig innsikt (samme bølge i 41 spill, hva den kostet, mot fjoråret) står på samme akse. Plenumsarket gjør P5 og P6 til et klassefunn i stedet for en gruppes feil. Studentens bånd, lærerens kjede og Debriefens kjede er samme tegning i tre skalaer.

**Ærlig risiko:**
- 08 er tett. Ferdige spill har 7 px rader, og spillnummeret er bare lesbart på hover eller i tabellen.
- Telefonen er tettere enn i 02: bånd og tre felt på 390 px. Båndet gjentar også ankomstene som meteogrammet viser til høyre for nå, og testen kan vise at ett av dem bør vike.
- Rommene i røret kan hjelpe så mye at svingningen dempes.
- Fjoråret er bare én median, så «fordeling mot fjoråret» er en referanselinje til produktet lagrer hele fordelingen.
- Medianen av 41 spill glatter ut toppene, så plenumsarket må aldri leses som ett spill.

**Gjenbrukbart selv om konseptet velges bort:** Røret i kjedebåndet med ett rom per Uke til levering og et eget rom for det som er forsinket uten dato.
