# 01 Ruteplan

**Tese (én setning):** Spillet er en grafisk togruteplan der hver Ordre og hver levering er en skrå linje, forsinkelsen er helningen, og det som er på vei synes som linjer som ennå ikke har nådd stasjonen din.

**Spilldynamikk:** Tiden renner nedover, og studenten har ett vertikalt spor med en kant mot hver nabo. Sporets bredde er Lager (høyre) og Restordre (hatchet venstre), og en mørk plattform skjærer papiret ved nålinja og bærer de seks tallene der linjene ender. Under plattformen ligger det som er på vei: tre linjer som ikke er framme, og en bred, gul ordrelinje som tegnes mens du taster, slik at 24 legger seg oppå 16 før du bekrefter. Ventingen vises med armsignaler (vannrett arm = stopp), tiden har ingen ende på papiret, og gamle uker rulles opp i en stripe.

**Debrief-grep:** Papiret snus 90° til en ekte Marey-plan med alle fire spor, der den ene røde kundelinjen med ett lite knekk nederst blir en tett floke øverst, med 1,8× til 7,6× skrevet på sporene.

**Lærerflate-grep:** 60 miniatyr-ruteplaner, simulert og skalert slik at urolige spill blir mørke, ved siden av en togleder-tabell der ventetid leses som forsinkelse (+23 t) på en skala som ender ved KI overtar.

**Palett:** Ingeniørpapir #E4ECE7, ubrukt papir #F1F5F2, rutenett #C4D2CB og #9DB2A8, marineblått blekk #10264B og #384E6E, signalrød #BE1224, signalgul #F5B800. Rødt stiplet er alltid det noen ber om (Ordre, Restordre). Blått heltrukket er alltid det som finnes (kasser, Lager).

**Typografi:** Overpass (avledet av motorveiskilt-skrift) for overskrifter, tall og skilt. Barlow Condensed for tett tekst, akser og etiketter. Tabellsifre overalt.

**Styrke:** Diagrammet er spillet, ikke en illustrasjon. Samme grammatikk (helning, bredde, to blekk) går fra første ordre til plenumsskjerm, og studenten kan lese hele spillet bakover. Datobåndet er tegnet til skala og ligger i bunnen av alle flater som bærer frister.

**Ærlig risiko:** Grepet kan virke mot læringen. Når det som er på vei blir så synlig, kan forsterkningen bli svakere enn i en vanlig kjøring, og da blir avsløringen tammere; dette må testes med ekte studenter. Diagrammet krever også en kort opplæring (Regler og Startoppgave), og første uke kan føles teknisk for studenter uten erfaring med grafer. Tallene for de 59 andre miniatyrene er simulert i `build.py`, ikke hentet fra fixture. Plenumsplanen er bredere enn en vanlig 16:9-skjerm og må beskjæres eller få større høyde i bygget produkt.

**Gjenbrukbart selv om konseptet velges bort:** Forhåndsvisningen av ordren som en linje oppå det som allerede er på vei, tegnet mens studenten taster.
