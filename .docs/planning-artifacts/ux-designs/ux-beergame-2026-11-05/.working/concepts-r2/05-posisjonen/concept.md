# 05 Posisjon

**Tese (én setning):** Hele spillet kan skrives som ett regnestykke, 0 − 13 + 16 = 3, og når det er skjermens hovedelement, kan studenten etterprøve med hoderegning hvorfor en ordre på 24 blir 27.

**Faglig kjerne:** P3 og P1. P3 bæres av ligningen og søylene under: det som er på vei står i ligningen med samme vekt som lageret, og søylen er siste tall i ligningen uke for uke. P1 bæres av tre ting. Panelet «Alle tall» skriver hver beholdning som inn minus ut. Avstemmingen 3 + 24 − 11 = 16 gjør at to regnestykker gir samme tall, og den stemmer for alle 36 uker og alle fire Roller i dataene (`build.py` sjekker det). Grafen «Inn og ut» viser endringen i Posisjon som arealet mellom Ordre ut og Ordre inn. P2 ligger i «Bestilt og levert», P4 i merkingen «Ordre inn», P5 og P6 i tabellgrafen i Debriefen, P7 og P8 i sammenligningen med Simulert.

**Spilldynamikk:** Uka åpner med regnestykket ferdig satt, og Sara leser 0 − 13 + 16 = 3 før hen gjør noe. Tallet hen taster står inne i ligningen, ikke i et eget felt, så hen leser 3 + 24 = 27 mens søylen vokser. Når Uka går videre, står 27 − 11 = 16 over den nye ligningen 0 − 20 + 36 = 16, så forskjellen mellom ordre og Ordre inn blir et tall hen selv kan regne etter. Et trykk på en søyle setter ligningen til den uka. Regnestykket sier aldri hva hen burde bestille, men Posisjon 54 med 31 i restordre er nok til å spørre hvorfor.

**Hjelpegrad:** Regnestykket vises alltid, tolkningen låses.
- *Klassespill:* ligningen, ordrelinjen og søylene, pluss «Alle tall» bak ett trykk. Ingen målstrek, ingen referanse, ingen oppdeling av tallet i graf, ingen forklaring av hva Posisjon bør være.
- *Replay, etter Debriefen:* oppdelingen (Lager, På vei, Restordre og Posisjon i samme søyle), «Inn og ut», «Bestilt og levert», avstemmingen som egen linje, og egne Klassespill-tall ved siden av, merket «Ikke like for like».
- *Hvorfor:* Sterman-funnet handler om at forsyningslinja står synlig og likevel får for lite vekt, så å vise tallet fjerner ikke feilen. I Debriefen kan vi da si «du hadde 16 på vei, det sto på skjermen din» i stedet for å avsløre noe nytt. Forskjellen er tegnet i `05-spill.svg` nederst til høyre og i `10-pedagogikk.svg` under streken «Låses opp etter Debriefen». Standpunktet er en hypotese som må prøves i piloten (issue #22).

**Debrief-grep:** Etter avsløringen «Kundene bestilte 4, så 8» leses forsterkningen rett ut av en tabellgraf der hvert tall er en søyle, fra Kundene til Fabrikk, med Uke 11 markert, og fire ligninger side om side viser hva hver Rolle så i samme uke.

**Lærerflate-grep:** En tabell over spillene gruppert etter hva læreren må gjøre (må følges opp, avtalt Pause, går av seg selv, ferdig), med Posisjon per Rolle fra ekte serier i felles skala, og trakten satt som subtraksjon: 240 − 76 = 164, og videre ned til 0.

**Palett:** Papir `#FFFFFF`, Trykk `#101010`, Grå `#696969` (tekst, 5,5:1) med rastertonene `#C4C4C4` og `#F1F1F1`, Signal `#E2001A` (4,9:1). Regel: ett rødt tall per flate, eller per kolonne på pedagogikkarket. Det er resultatet av regnestykket eller det ene tallet læreren må se. Rødt betyr aldri «feil». Roller skilles med tekst og plassering, aldri med farge.
**Typografi:** Archivo. Vekt 500 i store regnestykker, med operatorene i vekt 400, 400 til 600 i tekst, tabellsifre der tall står under hverandre, proporsjonale sifre i frittstående store tall. Hierarkiet bygges av størrelse og vekt: 52 px mot 13 px på telefon, 212 px på landingssiden.

**Styrke:** Konseptet er det eneste der grafen kan etterprøves med hoderegning. Tallene i ligningen, søylen, panelet, Debriefen og testen er de samme, og det er nettopp konsistens mellom tall og grafer forskningen sier viser forståelse. Telefonen trenger bare én graf, og professoren kan vise skjermen uten å unnskylde den.

**Ærlig risiko:** (1) Ligningen hele tiden kan dempe svingningene i Klassespillet og dermed svekke Debriefen, og det vet vi ikke før piloten. (2) Bevisst strenghet kan oppleves som kald eller som matteprøve for studenter som gruer seg til tall. (3) «Etter ordre» kan leses som en lovnad, selv om levering ikke er garantert, så det må stå i panelet. (4) Tastrekken med 11 taster i én linje gir smale trykkflater på 360 px (cirka 31 px) og må testes, med systemtastatur som reserve. (5) Oversiktens mikrografer er små fordi skalaen er felles, og det rene svart-hvitt gjør at Rollene bare kan skilles på plassering.

**Gjenbrukbart selv om konseptet velges bort:** Avstemmingslinjen når Uka går videre, 27 − 11 = 16 over den nye ligningen, fordi to veier til samme tall gjør materialbalansen synlig i ethvert grensesnitt.
