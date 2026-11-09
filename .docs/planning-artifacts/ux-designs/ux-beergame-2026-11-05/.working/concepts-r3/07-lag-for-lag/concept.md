# 07 Lag for lag

**Tese (én setning):** Telefonen viser alltid bare to ting, kjedebåndet for setets eget ledd og ordrefeltet, mens meteogram, tall og kostnad er lag studenten blar mellom, og lagene som regner for studenten åpnes først når Debriefen har lært hen hvorfor regningen betyr noe.

**Sammensetning:**
- *Telefon (Klassespill):* Øverst står kjedebåndet: fire plasser På vei (lengst unna til venstre), levering, beholdningen som boks på sann skala (blått over null, rødt under), sendt, og ordrene som går motsatt vei under. Verdiene står i en rad øverst med hjelpelinjer ned til tegningen. Under båndet er det en lagvelger med Graf | Tall | Kostnad, og nederst ordrefeltet. Båndet og ordrefeltet flytter seg aldri. Båndet har fast høyde (plass til lager 30 og restordre 40), så telefonen ser lik ut fra uke til uke. De tre lagene deler tidsakse (nå − 6 til nå + 4, samme venstremarg), så Uke 11 står i samme kolonne uansett hvilket lag som er valgt. Laget studenten velger, blir stående til hen bytter.
- *Laptop:* Det er plass til to lag samtidig. Graf og tall står over hverandre på én tidsakse, og kostnad og ordrefelt står i høyre kolonne.
- *Debrief:* Her åpnes lagene. Steg 3 har de fire Rollenes ordre med matrisen Rolle × uke (netto lager som tall) på samme akse. Steg 4 viser hele kjeden med fire ledd pluss kunde i Uke 11, med en ukeskrubber og kostnad hittil under hver node. *Kjedens kostnad* fordeler 2 266,00 kr på Rolle og kostnadsart, viser kostnaden per uke og samlet, og sammenligner med simulert referanse (1 341,00 kr). Quizen åpner laget Posisjon.
- *Faglærer:* Oversikten har samme lagvelger (Netto lager | Ordre | Kostnad, og Rolle). Matriseveggen viser 60 spill × uker med ekte serier. Til høyre står klassens kostnadsbilde (kjedekost per spill mot fjoråret, klassens kostnad per uke), klassens kjede (median netto lager per Rolle × uke) og mønstrene i beslutningsloggen.

**Faglig kjerne:**
- *P2 og P3 (kjedebåndet):* Ordren legger seg bakerst i På vei og rykker én plass per Uke, og tallet over plassene viser det som er på vei som én sum (16 + 24). P3 er synlig hele tiden, men summen Posisjon regnes ikke ut for studenten før laget åpnes.
- *P1 (Tall):* Raden Lager sier −9, så +4 inn og −8 ut, så −13. Grafen og tabellen er samme regnestykke på samme kolonne. `build.py` stopper hvis materialbalansen, kostnaden (lager × 0,50 + restordre × 1,00 = `kost_sum`) eller kjedekosten ikke stemmer med loggen i alle 36 uker. Det gjelder også de to simulerte kjedene.
- *P8 (Kostnad):* Kostnad per uke deles i rødt (restordre) og blått (lager). Samlet kostnad er stablet, så Totalkostnad er toppen.
- *P4, P5 og P6* kommer i Debriefen, med Kunde som node i kjeden og ordrene til fire Roller. *P7* står i `10-pedagogikk.svg` og i Ditt øyeblikk.

**Spilldynamikk:** Uka åpner med ny levering og ordre inn i båndet, og plassen fire uker fram står tom og stiplet. Sara taster 24, og tallet står straks bakerst i På vei og som mørk kant i Tall-laget. Etter bekreftelsen viser telefonen hvem Uka venter på. Så rykker båndet én plass mot høyre (under 2 sekunder, kan hoppes over), og laget hen hadde valgt, står der fortsatt. I Veiledede uker 1–4 åpnes ett lag per uke med én setning første gang: Uke 1 bare båndet, Uke 2 Graf, Uke 3 Tall og Uke 4 Kostnad.

**Hjelpegrad:** Standpunkt: *Lagene som viser fakta er åpne i Klassespillet. Lagene som legger sammen eller spår, åpnes etter Debriefen.* Systemet er tegnet som en lagtrappe, med lag som rader og trinn som kolonner (`10-pedagogikk.svg`, `03-laerer-spill.svg`, steg i `04-student-hjem.svg`).
- *Klassespill:* Kjedebånd og ordrefelt, Graf, Tall og Kostnad. Bare setets egne tall. På vei står som fire plasser og én sum, men Posisjon står ikke ferdig regnet. Det er ingen projeksjon og ingen kjedekost.
- *Etter Debriefen:* Posisjon (Lager − Restordre + På vei regnet ut i båndet, med «Med 24: 27»), Hele kjeden og Simulert referanse. Posisjon åpnes når quizen om nettopp den regningen er bestått.
- *Replay:* Alle lag, også Projeksjon (stiplet netto lager fire uker fram, «ikke garantert»).
- *Hvorfor:* Kjedebåndet gjør På vei svært synlig, og det er godt, for det er fakta. Men summen og projeksjonen er bare ett regnesteg fra en ordre-opp-til-regel. Hvis de er åpne fra start, kan studenten unngå svingningene uten å ha forstått dem, og da får Debriefen mindre å vise (issue #22). Ved å åpne regningen etter at hen har regnet den selv i quizen, blir Replay stedet der innsikten brukes. Forskjellen er tegnet nederst til høyre i `05-spill.svg`: samme bånd, uten og med Posisjon.

**Kostnadsbilde:**
- *Student under spillet:* Totalkostnad i toppen hele tiden. Laget Kostnad viser kostnad per uke, delt i restordre og lager, og samlet kostnad (stablet), med regnestykket for denne uka.
- *Etter spillet (rute F og Debrief):* Kjedens totalkostnad først, så per Rolle og per art. Deretter kostnad per uke og samlet for kjeden, med simulert referanse.
- *Faglærer:* Kjedekost per spill som prikkplott med median, midterste halvdel og fjorårets median. Klassens kostnad per uke delt i to arter. Kjedekost står i hver rad i matriseveggen, og ferdige spill er sortert lavest øverst. Det er bare Faglærer som ser denne sorteringen.
- *Aggregater i `build.py`, fra `klasse.spill`:* (1) ukeskostnad per spill = positiv netto × 0,50 + negativ netto × 1,00. Summen er kontrollert mot `kjedekost` (avvik ≤ 0,50, fordi fixturen runder til hele kroner). (2) Median kjedekost over 41 ferdige spill, kontrollert mot `ferdige.kjedekost.median` (1 954). (3) Klassens kostnad per uke = sum over ferdige spill og fire Roller, delt i lager og restordre. (4) Median netto lager per Rolle og uke over ferdige spill.

**Debrief-grep:** Debriefen er der lagene åpnes. Hele kjeden med skrubber, matrisen Rolle × uke og kjedens regning kommer etter avsløringen, og quizen om posisjon låser opp Posisjon-laget i Replay.

**Lærerflate-grep:** Den samme lagvelgeren styrer matriseveggen (netto lager, ordre eller kostnad for valgt Rolle). Ved siden av står klassens kostnadsfordeling og klassens kjede som median, så Faglærer skanner status og mønster på samme skjerm.

**Palett:** Meteogrammets palett uten avvik. Nye matrisetrinn, validert med dataviz `validate_palette.js --ordinal` (monoton lyshet, ΔL ≥ 0,06, lys ende ≥ 2:1, én kulør, alle PASS):
- Lager: 1–9 #9ABBD9, 10–19 #6E9CC6, ≥ 20 #2B6CA3 (hvit tekst).
- Restordre: 1–9 #E2A29A, 10–19 #CF7B71, ≥ 20 #B5423A (hvit tekst).
- Null: hvit, eller #EEF1F4 i veggen.
- Strømmer: 0–4 hvit, 5–9 #A6B8CB, 10–14 #7F97B0, 15–24 #4F6A87 (hvit), ≥ 25 #0F2A47 (hvit).

Celletall har kontrast fra 4,66:1 til 14,6:1. Minus foran restordre gjør at farge aldri bærer status alene. Lagtrappa bruker #4F6A87 for åpent lag (hvit tekst 5,6:1), marine for «åpnes» og stiplet kant for låst, og hver celle har tekst.
**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i tall, akser og matriser, proporsjonale sifre i 2 266,00 kr og Forsterkning.

**Styrke:** Telefonen er rolig: to faste flater og ett lag om gangen, og lagene deler kolonner, så det å bytte lag føles som å bytte linse og ikke side. Hjelpegrad er ikke en skjult innstilling, men et synlig system som student, Faglærer og Debrief deler, og opplåsingen gir Debriefen og Replay en tydelig rolle.

**Ærlig risiko:** Studenter som aldri bytter lag, ser kanskje aldri tallene eller kostnaden. Telemetri må vise om lagene brukes. Kjedebåndet gjør På vei så tydelig at det alene kan dempe svingningene mer enn ønsket, og det er ikke testet. Det kan oppleves som tilbakeholdelse at Posisjon er låst, selv om tallene står der. Den faste båndhøyden gir tomrom i rolige uker, og en sann skala på 0,95 px per enhet gjør små leveranser tynne. Ukeskrubberen, overgangen i rute D og opplåsingen må prøves i prototype.

**Gjenbrukbart selv om konseptet velges bort:** Lagtrappa: en tegnet matrise lag × trinn (Veiledede uker, Klassespill, Etter Debriefen, Replay) som gjør Hjelpegrad til et synlig og justerbart system for både student og Faglærer.
