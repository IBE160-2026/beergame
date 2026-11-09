# 09 Kjedens regning

**Tese (én setning):** Kostnaden er tråden som binder kjeden, grafen og tallene sammen: hver Uke legger en linje til regningen, setet ser bare sin egen del under spillet, og etter spillet bygges kjedens 2 266,00 kr opp linje for linje (fire Roller × to kostnadsarter × 36 uker) og legges mot simulert referanse 1 341,00 kr.

**Sammensetning:**
- *Telefon (Klassespill):* kjedebåndet øverst viser setets eget ledd. Det som er på vei, står som fire bokser i et rør (nærmest leddet kommer først), deretter inn, lager eller restordre i leddet på samme skala, og ut. Ordre inn kommer som en tynn marine linje fra høyre. Under båndet står hva Uka koster, og hvorfor («13 i restordre × 1,00»). Meteogrammet fra 02 ligger under med fire felt på én akse: netto lager, inn og ut, egen ordre og **kostnad per uke** (blå stolpe for lager, rød for restordre). Toppen viser «Din del av regningen». Ett trykk unna ligger «Din regning» som matrise (uker som kolonner: lager, restordre, kostnad, sum så langt) og regnestykket for Posisjon.
- *Debrief:* steg 3 viser hele kjeden som en loddrett ryggrad (Fabrikk → Distributør → Grossist → Detaljist → Kundene) der hvert ledd har sine ordrer, Forsterkning og hva leddet betalte, delt i lager og restordre. Steg 4 er hovedgrepet: akkumulert kjedekostnad (stablet lager/restordre, stiplet simulert referanse) står rett over **matrisen Rolle × uke i kroner** på samme tidsakse, med raden Kjeden og totaler per Rolle og kostnadsart. Under kommer «Regningen, linje for linje» som fossefall mot Simulert.
- *Faglærer:* matriseveggen viser kjedens kostnad per uke for alle 60 spill, ved siden av en stolpe per spill delt i lager og restordre, med median, fjoråret og Simulert som streker. Høyre kolonne har nær overtakelse, klassens regning (sum, fordeling, median per Rolle og kostnadsart) og trakten.
- Kostnaden leder i Debrief og hos Faglærer. Under spillet leder ledd og graf, og kostnaden er et rolig fjerde felt.

**Faglig kjerne:** P8 og P5 gjør konseptet best. Kostnadsmatrisen er netto lager målt i kroner, så den samme ubalansen blir dobbelt så mørk på rød side (P8), og radene viser at regningen vokser oppover i kjeden selv om Distributør og Fabrikk aldri så en kunde (P5, P6). Kjedebåndet gjør P3 synlig som et fullt rør ved siden av et tomt ledd, og P2 som boksen som rykker én plass per Uke (06, nederst). P1 sitter i inn og ut-feltet og i matrisen: ukas kostnad er nøyaktig leddet × sats, og summen går opp mot loggen. P4 og P7 står i Debriefen og på `10-pedagogikk.svg`.

**Spilldynamikk:** Uka åpner med ny levering, ny ordre inn og en ny linje i regningen. Sara ser røret med 4, 4 og 8 og en tom plass ytterst; hen taster 24, og boksen legger seg ytterst i røret og som åpen stolpe fire Uker fram i grafen. Etter bekreftelsen viser skjermen hvem Uka venter på, og når Uka går videre, rykker røret én plass og kostnadsfeltet får en stolpe til. Røde stolper som vokser mens røret er fullt, er selve spørsmålet for neste ordre: hva koster det som allerede er på vei når det kommer?

**Hjelpegrad:** Standpunkt: setet ser innholdet i røret og sin egen regning, men ikke summen.
- *Klassespill:* eget ledd med røret og kjente ankomster («Bestilt, ikke garantert»; forsinket hos Distributør uten dato vises som egen linje), egen graf, egen kostnad per uke og samlet. Posisjon ligger ett trykk unna som regnestykke uten fasit. Ingen projeksjon, ingen kjedekostnad, ingen andres tall.
- *Replay (etter Debriefen):* samme bånd, men Posisjon tegnes som en klamme under rør og ledd med regnestykket ved siden av (`0 − 13 + 40 = 27`). Kjedens regning fra Klassespillet er tilgjengelig som egen referanse, merket «Ikke like for like».
- *Hvorfor:* Røret gjør På vei svært synlig, men summen er det folk lar være å regne (P3), og den er ett lite steg unna en bestillingsregel. Med summen tegnet under spillet ville vi svekke erfaringen Debriefen trenger (issue #22). Når studenten har sett regningen, er summen innsikt, ikke fasit. Forskjellen er tegnet nederst til høyre på `05-spill.svg`.

**Kostnadsbilde:**
- *Student under spillet:* «Din del av regningen» øverst, ukas kostnad og forklaringen under kjedebåndet, kostnad per uke som felt i grafen, og «Din regning» som tabell bak ett trykk.
- *Gruppa etter spillet:* først kjedens regning (2 266,00 kr, lager 901,00 og restordre 1 365,00), så per Rolle (342,00 · 553,50 · 691,00 · 679,50) og per kostnadsart. I Debriefen: akkumulert kostnad mot Simulert 1 341,00, matrisen Rolle × uke i kroner, og regningen linje for linje.
- *Faglærer:* matrisevegg (60 spill × uker, kjedens kostnad per uke), kjedekost per spill delt i lager og restordre, prikkplott over 41 ferdige spill med midtre halvdel, median 1 954, fjoråret 2 740 og Simulert 1 341, median per Rolle og kostnadsart, og klassens samlede regning.
- *Aggregater regnet i `e09cost.py`/`screens_debrief_teacher.py` fra `klasse.spill`:* ukeskostnad per spill = sum over Roller av (netto lager > 0) × 0,50 + (netto lager < 0) × 1,00, delt i lager og restordre. Kontrollert mot `kjedekost` (avvik ≤ 0,5 kr per spill fordi den er avrundet) og mot `kost_per_rolle` for ferdige spill. Median per uke (lager og restordre hver for seg) over 41 ferdige spill gir søylene over veggen. Klassens sum: 82 498 kr, lager 38 920 og restordre 43 578 (53 %). Median per Rolle er regnet for lager og restordre hver for seg. Cellefargen i veggen følger kostnadsarten som var størst den uka. Kvartiler og median for kjedekost er hentet fra `klasse.ferdige` (median er kontrollert).
- *Kontroller i bygget:* for spill 17 og begge simuleringene stopper `build.py` hvis ukeskostnaden ikke summerer til `kost_sum` uke for uke, hvis lager og restordre opptrer samme uke, hvis materialbalansen ikke holder, eller hvis per Rolle eller kjeden ikke går opp mot `kost_per_rolle` og `kjedekost`. Fossefallet sjekker at linjene summerer til kjeden.

**Debrief-grep:** Kjedens regning står som akkumulert kurve rett over matrisen Rolle × uke i kroner, på samme tidsakse og med Uke 11 markert, slik at gruppa kan lese både mønsteret og regnestykket bak 2 266,00 kr.

**Lærerflate-grep:** Én matrisevegg der hver rad er ett spills kjedekostnad uke for uke, med en lager/restordre-stolpe per spill og median, fjoråret og Simulert som streker, slik at Faglærer ser både hvor spillene er og hva de har kostet.

**Palett:** Meteogrammets palett uendret. Nye trinn for kostnadsmatrisen, validert med `validate_palette.js --ordinal` (lys ende ≥ 2:1 mot hvit, monoton lyshet, én hue) og med tekstkontrast ≥ 4,5:1 sjekket i bygget:
- Lagerkost: #94B8D9 → #6A99C6 → #2B6CA3 (marine tekst på de to lyse, hvit på den mørke).
- Restordrekost: #E0A099 → #D07B72 → #B5423A (samme regel). Restordretall står i tillegg halvfete, så arten ikke bæres av farge alene.
- Trinn: per ledd og uke opptil 10, 10–25 og over 25 kr. For kjeden i Oversikten: under 40, 40–100 og over 100 kr. Blå og rød bestod CVD-sjekken (ΔE 16,2).
- Sekvensiell marine/grå for strømmer er definert (#A9B6C4, #7F93A8, #44586F, #0F2A47) og validert, men brukes lite fordi kostnaden bærer matrisen.

**Typografi:** Source Sans 3 i 400, 600 og 700. Tabellsifre i tall, akser, matriser og tabeller. Proporsjonale sifre i de største enkelttallene (kjedens regning, Forsterkning).

**Styrke:** Kostnaden er spillets mål, og her blir den det samme regnestykket på alle flater: én celle per ledd og uke, som summerer til ledd, kjede og klasse. Tall og graf deler tidsakse og kan kontrolleres mot hverandre. Kjedebåndet gjør det som er på vei like konkret som det som mangler.

**Ærlig risiko:** Telefonen bærer nå bånd og fire felt, og det er i overkant tett. Det må prøves på ekte skjermer, og kostnadsfeltet er det første som kan flyttes bak ett trykk. En så tydelig regning kan bli lest som karakter eller rangering i gruppa, selv om vi bare viser per Rolle og aldri mellom spill for studenter. Celletallene i Debriefen er 12 px på 2100-lerret og må testes på storskjerm. Matriseveggen hos Faglærer bruker 10,5 px og trenger tabellvisningen. Fjoråret har bare median i dataene, ikke fordeling.

**Gjenbrukbart selv om konseptet velges bort:** Kostnadsmatrisen Rolle × uke i kroner, der fargen viser kostnadsarten og summene går opp mot kjedens regning.
