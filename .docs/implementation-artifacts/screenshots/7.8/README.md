# Story 7.8 visuell sjekk: Spillinnsikt, «Kjeden i grafer»

Spill med 4 studenter, 22 uker spilt, restordre i Distributør, Grossist og Detaljist. Faglærer. Alle etter visuelle rettinger (jevn Uke-kolonnebredde i tabellvisningene).

- `spillinnsikt-diagrammer-390.png`: hele siden ved 390 px; begge diagrammer, Ordre og Lager og restordre, scroller sideways i egne regioner, siden gjør det ikke. Stemmer, bortsett fra utkantfade (se under).
- `spillinnsikt-diagrammer-1280.png`: hele siden ved 1280 px; stolper og tall ligger i samme kolonner, Fabrikk øverst, Kundene nederst, lager blå opp og restordre rød ned. Stemmer; diagrammene fyller bare halve bredden (23 faste kolonner).
- `spillinnsikt-diagrammer-1280-tekst200.png`: 1280 px med 200 % tekst; ingenting kuttet, ingen sidescroll, diagrammene scroller i regionen. Stemmer.
- `spillinnsikt-ordre-fokus-390.png`: tastaturfokus på Ordre-regionen; synlig marineblå ramme. Stemmer.
- `spillinnsikt-ordre-fokus-1280.png`: som over ved 1280 px. Stemmer.
- `spillinnsikt-ordre-fokus-1280-tekst200.png`: som over ved 200 % tekst. Stemmer.
- `spillinnsikt-tabeller-390.png`: begge «Vis som tabell» ved 390 px; jevne kolonner, rader og Uke-kolonner scroller i egen region, Uke-kolonnen er sticky. Stemmer (fade i høyre kant, se under).
- `spillinnsikt-tabeller-1280.png`: begge tabellene ved 1280 px; like brede Uke-kolonner, to rader per Rolle i Lager og restordre. Stemmer (rettet: kolonnene var før ujevne etter sifferantall).
- `spillinnsikt-tabeller-1280-tekst200.png`: tabellene ved 200 % tekst. Stemmer.

## Avvik overlatt til vurdering

- Lager og restordre har ingen skala eller verdietiketter (kun nullinje, «samme skala for alle rollene»); DESIGN.md ber om direkte etiketter. Tallene finnes i «Vis som tabell».
- `ScrollRegion` fader kantene til `paper` (Issue #98), mens DESIGN.md sier «No fades or gradients». Felles komponent, ikke rørt.
- Ordre-diagrammets «Uke n»-markører (felles `order-bars.tsx`) ligger tett over stolpene og bryter litt inn i hverandre ved 390 px. Ikke rørt.
- Mockup `09-alle-sider.png` viser Spillinnsikt som kjedebånd over matrise; bygget bruker Ordrestolper og stolpebånd over tall, i samme kolonnerytme.
