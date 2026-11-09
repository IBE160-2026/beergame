# 04 Strukturen

**Arbeidsnavn:** Struktur.

**Tese (én setning):** Fagets eget språk er grensesnittet: Forresters stock-and-flow-notasjon, tegnet med ekte tall og sann skala, slik at studenten lærer å lese et system ved å spille i det.

**Faglig kjerne:**
- **P1 Lager er en opphopning.** Felles tidsakse: flaten mellom Levering og Innkommende ordre er uke for uke lik endringen i Lager minus Restordre (`build.py` nekter å tegne hvis balansen ikke stemmer for alle 36 uker). Søylene under er summen av flatene.
- **P2 Forsinkelse.** Forsinkelsesmerket `//` på Levering, «om lag 4 uker», og buen i Ordre og Levering: 24 bestilt i Uke 11, 17 levert i Uke 15.
- **P3 Det som er på vei blir glemt.** På vei er en boks på samme skala som Lager. Taster Sara 24, vokser den fra 16 til 40 foran øynene på hen.
- **P6 Struktur gir atferd.** Tegningen er lik hver uke og lik for alle. Bare tallene endrer seg. Debriefen sier det rett ut: «Slik er strukturen. Det er den som svinger, ikke dere.»
- **P4, P5** i Debriefens bånd: Kunde 4 så 8, deretter ordrene som tykner og forskyves oppover (1,8× til 7,6×). **P7, P8** i sammenligningen mot simulert referanse og i Totalkostnad som egen beholdning med innstrømmen 13 × 1,00 + 0 × 0,50 = 13,00.

**Spilldynamikk:** Uka åpner med at strømmene har gått: Levering inn, Innkommende ordre inn, Sendt ut. Sara leser boksene, taster ett heltall, og tallet går langs en rød informasjonspil inn i Ordre-ventilen og videre inn i På vei. Hen bekrefter, ser hvem det venter på, og neste Uke viser regnestykket i maks 2 sekunder (40 − 4 = 36, 13 + 11 − 4 = 20) før tegningen står klar igjen. Fordi tegningen aldri flytter seg, ser hen det som vokser: hen trenger ingen forklaring for å se at det hen har bestilt hoper seg opp lenge før noe kommer fram. Høyre kant på tidsaksen er alltid nå, og aksen viser aldri en slutt.

**Hjelpegrad:** Tegningen er åpen, sløyfen er lukket.
- **Klassespillet:** alle Saras beholdninger og strømmer vises på samme skala, så På vei kan sees av den som ser etter. Men ingen legger dem sammen for hen: Posisjon er ikke på tegningen, og det er ingen pil tilbake til Ordre. Regnestykket (0 − 13 + 16 = 3, 3 + 24 = 27) og kjente ankomster ligger bak ett trykk, merket som regnestykke og ikke råd. Standpunktet er at den som vil regne, får regne, mens de fleste vil gjøre den klassiske feilen og derfor ha noe å forklare i Debriefen.
- **Replay:** etter Debriefen får Sara Posisjon som node på selve tegningen, og den røde sløyfen B tilbake til Ordre. Begrepene er nå navngitt, og hen bruker dem. Fortsatt ingen anbefalt ordre. Forskjellen er tegnet nederst til høyre i `10-pedagogikk.svg`.
- **Hvorfor:** Innsikten i Debriefen trenger en opplevelse å feste seg til (issue #22), men studenten må ikke holdes for narr. Tallene er sanne og tilgjengelige hele tiden, bare sammenstillingen låses.

**Debrief-grep:** Forklaringen skrives før avsløringen, så kommer én rett kundestrek mot alt hen tok imot, og til slutt én lang kjede med ordrebånd som tykner uke for uke, ved siden av den balanserende sløyfen der fagets begreper får navn.

**Lærerflate-grep:** Listevisning med en mikrotegning av kjeden per spill (fire små beholdninger til skala, strøm mellom), ordrespor mot en felles 36-ukers akse, status med ord og form, det som haster øverst og trakten som en kjede av beholdninger.

**Palett:** Betong #E8E8E4 (grunn), betong mørk #D8D9D5 (lerret), papir #F4F4F1 (inni beholdning), nær-svart #15181B (linje, tekst), grafitt #2B2E32 (fyll i beholdning), sekundær #484C50, hjelpelinje #A9ABA7, dempet blå #2F5F85 (bare strøm), rød #B3241A (bare det aktive signalet: nå, ordren som tastes, tilbakekoblingen).

**Typografi:** Red Hat Text til all tekst. Red Hat Mono bare til målte verdier.

**Disiplin:** Verdier er festet til nodene på tynne hjelpelinjer. Ingen frittstående kort med tall. Layouten følger strukturen: inndatafeltet er festet til Ordre-ventilen, Spillinnstillingene sitter på kjeden, de seks stegene og setene er kjeder. Også Totalkostnad og trakten er beholdninger.

**Styrke:** Studenten lærer notasjonen uten å ha lest om den og kan bruke den i Individuell test, der hen selv tegner beholdning og strøm. Tegningen forklarer P1 og P3 med geometri i stedet for tekst, og en professor kan vise den i plenum som ekte fagstoff. Den gjør også regnestykket, ikke bare mønsteret, til det man ser.

**Ærlig risiko:** Tegningen er mer krevende å lese enn en enkelt linje, særlig de første ukene, og på 390 px er det mye strek. Tykke rør og sorte bokser kan se tunge ut når På vei er stor, og fordi skalaen er sann må boksens skala ned når På vei passerer rundt 60 på telefon (toppen er 90). Flaten bruker Innkommende ordre som «ut» for å holde balansen med Restordre, mens tegningen viser Sendt: det er riktig fag, men må testes med studenter. Forresters sky kan leses som pynt av den som ikke kjenner notasjonen.

**Gjenbrukbart selv om konseptet velges bort:** Regelen om at hver verdi er festet til en node med hjelpelinje, og at det du taster, vises som vekst i På vei på samme skala som Lager.

Tallene er demodata fra `_shared/fixture.json`. Simulerte referanser er merket Simulert og er verken optimale eller fasit.
