# 10 Fri syntese (Kjeden langs tidsaksen)

**Tese (én setning):** Kjeden skal ikke ligge over grafen som et eget kart, men være høyre side av den samme tidsaksen: det som er på vei står over uka det ventes, lageret står ved nå-streken, og ordren du taster legger seg bakerst i køen. Da blir kjede, meteogram, tall og kostnad fire lesninger av én akse, ikke fire paneler.

**Sammensetning:** Standpunktet er at oppstrøms tegnes til høyre, fordi det som kommer senere ligger til høyre på en tidsakse. Varene går mot venstre, mot nå og videre til Detaljist; ordrene går mot høyre.
- *Telefon (Klassespill):* fire felt på én akse, Uke 4 til 15 når det er Uke 11. Øverst er kjedebåndet, setets eget ledd: Sendt 4 til Detaljist og Ordre inn 8 til venstre, restordren som boks på sann skala ved nå, og køen 4, 4, 8 og 24 som åpne bokser over Uke 12 til 15. Under står Din ordre, der 24 er en mørk stolpe med en tynn strek opp til boksen sin i køen (P2). Deretter netto lager (Meteogrammets blå og røde flate) og kostnad per uke i kroner. «Tallene» ligger ett trykk unna: en matrise med nøyaktig de samme ukene som kolonner, regnestykket for uka og Totalkostnad over tid delt i restordre og lager.
- *Laptop (Labtime):* samme akse med feltet Inn og ut i tillegg, og tallene i en kolonne ved siden av.
- *Debrief:* kjeden får fire ledd og kundene, på samme notasjon (boks på sann skala, kø mellom leddene). Under står matrisen Ordre, Rolle × uke, der kjeden er én kolonne (Uke 18) og ukene kan spoles. Kostnaden får en egen flate: Kjedens regning.
- *Faglærer:* matrisen leder. Klassens median per Rolle og uke står som tall over veggen med 60 spill × uker, og veggen deler kolonner med den. Kostnadsbildet står i høyre kolonne.
- Hva leder: på telefonen grafen og båndet, i Debriefen avsløringen og deretter kjeden, hos Faglærer matrisen.

**Faglig kjerne:** P2 og P3 får en tegning der begge er én bevegelse: tallet du taster står bakerst i køen, og køen rykker ett steg mot lageret hver Uke (`06-spilldynamikk.svg`, nederst). P1 bæres av matrisen: kolonnen er regnestykket (−9 + 4 levert − 8 ordre inn = −13), og tallene er de samme som i grafen. P8 bæres av kostnadsfeltet: samme uker, blått lager × 0,50 og rødt restordre × 1,00, så halvparten og det doble synes uten forklaring. I Debriefen viser kjeden i Uke 18 P4, P5 og P6: alle fire har restordre (−16, −38, −43, −54), og alt er på vei. Matrisen under viser at første ordre på 10 eller mer kommer i Uke 6, 11, 13 og 15, og forsterkningen er 1,8×, 4,1×, 6,0× og 7,6×. P7 står i Debriefens øyeblikk og på `10-pedagogikk.svg`: en ny ordre kommer ikke før de gamle, den gjør bare køen lengre. `e10syn.py` stopper bygget hvis materialbalansen, kostnaden per uke og per Rolle, kjedekosten (2 266,00, 1 507,00 og 1 341,00) eller klassespillenes kjedekost ikke stemmer med loggen for alle uker.

**Spilldynamikk:** Uka åpner med regnet levering og ordre inn, og plassen fire uker fram i båndet står tom. Sara taster 24, og boksen står bakerst i køen etter 4, 4 og 8, med en strek ned til stolpen i Din ordre. Etter bekreftelsen viser skjermen hvem Uka venter på. Så rykker køen ett steg mot lageret på under 2 sekunder, og overgangen kan hoppes over. I Uke 15 kommer 17 i stedet for 24, og Sara ser at bestilt ikke er levert, og at det hen får nå, er det hen bestilte for fire uker siden. Kostnadsstolpen for uka står rett under, så Sara ser hva restordren koster mens hen bestemmer.

**Hjelpegrad:** Standpunkt: Klassespillet viser delene, Replay viser summen.
- *Klassespill:* båndet med hver kjente ankomst for seg (setets egne tall), merket «På vei 16 + 24, fra Distributør». Ingen sum er tegnet, og det er ingen projeksjon. Posisjon finnes ett trykk unna i Tallene, som regnestykke uten fasit (0 − 13 + 16 = 3, med 24: 27). Køen gjør det som er på vei svært synlig, så vi tegner den bevisst som enkeltbokser: det er summen folk lar være å regne, og den vil vi at Debriefen skal sette ord på.
- *Replay (etter Debriefen):* en klamme under båndet fra lageret til siste boks med «Posisjon 0 − 13 + 16 = 3, med 24: 27», og Meteogrammets stiplede linje som ender på −5. Forskjellen er tegnet på `05-spill.svg`, nederst til høyre.
- *Hvorfor:* summen og linja er bare ett regnesteg fra en ordre-opp-til-regel. Med dem på i Klassespillet ville studenten fått fasiten uten at vi sier den, og det svekker erfaringen Debriefen trenger (issue #22). Ærlig forbehold: køen alene kan dempe svingningene mer enn Meteogrammets åpne stolper gjorde. Det må testes.

**Kostnadsbilde:**
- *Studenten under spillet:* Totalkostnad i toppen, kostnad per uke som eget felt på samme akse, «Kostnad denne uka» i tallene, og Totalkostnad over tid delt i restordre (25,00) og lager (43,00) bak ett trykk. Bare egne tall.
- *Når spillet er ferdig:* kjedens totalkostnad først (2 266,00 kr), så per Rolle med restordre og lager som to deler av samme stolpe.
- *Gruppa i Debriefen:* Kjedens regning, akkumulert over 36 uker, med lager nederst og restordre over, mot to simulerte referanser (1 507,00 og 1 341,00). Under står en tabell Rolle × kostnadsart med Kjeden som sum: restordre utgjør 1 365,00 av 2 266,00 kr, altså 60 %. Kostnad hittil står ved hver node i kjeden.
- *Faglærer:* kjedekostnad per spill som prikker (fylt for ferdig, ring for pågår) med midtre halvdel, median 1 954 og fjorårets 2 740. Under står klassens kostnad per uke, summert over alle spill, delt i lager og restordre.
- *Aggregater regnet i `screens_debrief_teacher.py`:*
  - Median netto lager per Rolle og uke, over spillene der `uke ≥ k`, avrundet til heltall.
  - Klassens kostnad per uke: Σ over spill og Roller av positiv × 0,50 og negativ × 1,00 av `netto_lager`.
  - Kontroll: summen av ukeskostnadene er lik summen av `kjedekost`, og hvert spills kjedekost stemmer med netto lager innenfor 0,50.
  - Kjedens regning: `lager` og `restordre` per Rolle i spill 17, og `kost_sum` for de simulerte kjedene.

**Debrief-grep:** Etter avsløringen står hele kjeden i Uke 18 med fire restordrebokser og fulle køer mellom leddene, og rett under står ordrene som tall, Rolle × uke, med den uka innrammet. Bildet og tallene er samme kolonne.

**Lærerflate-grep:** Klassens median netto lager per Rolle og uke står som tall over matriseveggen med 60 spill og deler kolonnene med den. Faglærer leser mønsteret i veggen og tallet i raden over, og kostnaden per spill og per uke står i høyre kolonne.

**Palett:** Meteogrammets palett uten avvik. Nye trinn for matrisen, sjekket med `validate_palette.js --ordinal` mot hvit (alle PASS) og med en kontrastsjekk i bygget (tall i celler ≥ 4,5:1):
- *Restordre:* #E3A7A0 (1–9), #D1837A (10–24), #B5423A (25+, hvit tekst). Lyseste trinn 2,04:1 mot hvit.
- *Lager:* #97BBDC (1–9), #6F9DC8 (10–24), #2B6CA3 (25+, hvit tekst). Lyseste trinn 2,01:1.
- *Strøm, marine/grå:* #A5B8CA (6–11), #8399B0 (12–19), #4D6680 (20+, hvit tekst). Lyseste trinn 2,04:1. 0–5 og 0 har ingen fyll, bare hårstrek.
- *Kostnadsceller:* Meteogrammets fyll #F0D5D2 (restordre) og #CDDFEE (lager).
- *Kontrast og identitet:* marine på mellomtrinnene gir 5,0–5,2:1, hvit på de mørkeste 5,5–6,0:1. Blå mot rød ga CVD-avstand 16,2. Tallet står alltid i cellen, så farge bærer aldri status alene.

**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i akser, celler og tabeller, proporsjonale sifre i 2 266,00 kr og forsterkningstallene.

**Styrke:** Én akse gjør at ingenting står to ganger. Kjente ankomster vises bare i båndet, ikke både i et kjedekart og i grafen, og telefonen får plass til kjede, graf og kostnad uten bryter. Ordren tegnes som en bevegelse inn i kjeden, og «bestilt er ikke levert» blir noe Sara ser skje i Uke 15. Matrisen deler kolonner med grafen på alle flater, slik at tall og graf kontrollerer hverandre. Det er dette som gjør komposisjonen bedre enn den direkte sammensmeltingen i 01: der står kjedebåndet over grafen som en egen tegning med egen logikk, og Graf/Tall er en bryter. Her er kjeden høyre side av grafen, og tallene er de samme kolonnene bak ett trykk.

**Ærlig risiko:**
- Oppstrøms til høyre bryter vanen fra lærebøker, der kjeden ofte går fra fabrikk til kunde mot høyre. Noen vil lese pilene feil første gang.
- Venstresiden av båndet bruker tidsaksen til en pil som ikke er tid, og det er en kompromiss i grammatikken.
- På telefonen er boksene små, 24 rundt 31 px høy, fordi de må følge ukebredden.
- Køen gjør På vei svært synlig også i Klassespillet, og vi vet ikke uten test om den demper svingningene Debriefen trenger.
- Tegningene er statiske, så at køen rykker og at 24 legger seg bakerst, må prøves i prototype.

**Gjenbrukbart selv om konseptet velges bort:** Køen over ukene den ventes, på samme akse som grafen, med ordren du taster bakerst. Det er P2 og P3 i én bevegelse.
