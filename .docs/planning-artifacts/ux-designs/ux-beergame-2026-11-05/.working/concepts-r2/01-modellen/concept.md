# 01 Modellen

Arbeidsnavn: **Modell**

**Tese (én setning):** Kjeden er en målsatt tegning du kan se inn i, der hver enhet står et sted, og et aksonometrisk snitt står rett over kurven i samme målestokk, slik at det du ser i hullet og det du leser i grafen er samme tall.

**Faglig kjerne:** P3 og P1. P3 gjøres av snittet: Lager, Restordre under nullplanet og På vei i felt per ankomstuke på samme tegning, slik at Posisjon kan telles. P1 gjøres av inn-og-ut-grafen på samme tidsakse: arealet mellom Levering og innkommende ordre er endringen i Lager, og regnestykket står ved kanten (fra Uke 11 til Uke 18: inn 46, ut 71, −13 blir −38). P2 ligger i kurven: stolpene for Uke 8, 9 og 10 er det samme som står i feltene, og kurven svarer fire uker etter. P8 ligger i skraveringen, som er det eneste dyre på tegningen. P4, P5 og P6 kommer i Debriefen, når de fire byggene står på rekke, og P7 står som nyanse i `10-pedagogikk.svg`.

**Spilldynamikk:** Du åpner Uka og ser hva som gikk over terskelen: Levering har krysset den gule kanten, og hullet har endret seg. Du taster et tall, og en stiplet stabel reiser seg i feltet for den uka ordren tidligst kan komme, mens regnestykket over knappen oppdateres. Du sender, ser hvem det venter på, og kanten flytter seg én uke. Modellen sier aldri hva som er riktig, men over tid begynner du å se på feltene før du ser på hullet.

**Hjelpegrad:** I Klassespillet vises snitt, kurve og Posisjon som regnestykke for denne uka, altså tilstanden nå. I Replay vises i tillegg Posisjon som kurve over tid og inn-og-ut-grafen, altså din egen regel. Standpunktet: Vi tåler å vise det som er på vei under Klassespillet, fordi det klassiske funnet er at spillere legger for lite vekt på forsyningslinja selv når den ligger synlig på bordet. Det som låses er ikke informasjonen, men mønsteret i egen atferd, for det er det Debriefen skal avsløre. Forskjellen er tegnet nederst i `10-pedagogikk.svg`. Dette må prøves i pilot mot issue #22: hvis gruppene slutter å svinge, flyttes regnestykket bak ett trykk i Klassespillet.

**Debrief-grep:** De fire byggene står på rekke i samme modell og skala med ordrekurvene under, og når du drar den gule kanten gjennom spillet, følger modellene med, slik at hull og felt vokser oppover i kjeden foran hele gruppa.

**Lærerflate-grep:** Et plansnitt over 60 tomter ved siden av tabellen: ferdige spill er skyggeblå og uten kant, aktive er blå med gul kant der spillet står nå, så du ser både svingningene og hvor klassen er i ett blikk.

**Palett:** Kalk `#F5F6F5` (grunn), Modellhvit `#FFFFFF` (flater), Side `#ECEEEE` (modellens skyggeside), Kull `#23272B` (snitt og tekst), Kull 2 `#555C63` (sekundær tekst), Ordreblå `#225A93` (ordrer), Skyggeblå `#7C96AB` og `#DCE4EA` (det som har vært), Nå-gull `#B08D2E` (bare nå, aldri annet enn kanten). Ingen rødfarge: Restordre vises med skravur, slik arkitekter viser snitt, så status bæres aldri av farge alene. Validatoren godkjenner Ordreblå mot grunnen. Skyggeblå er bevisst under kromagulvet og under 3:1, og bærer derfor aldri mening alene: den har alltid direkte etikett, og tallene ligger bak ett trykk i Detaljer.

**Typografi:** Epilogue (tekst og overskrifter, stram grotesk). Hanken Grotesk (alle tall, tabellsifre, og operatorene i regnestykket). Albert Sans og Gantari ble forkastet fordi tabellsifrene ikke virket i testrenderen.

**Styrke:** Målestokken er sann på tvers av modell og kurve, så bildet kan ikke lyve: hullet og kurven er like dype, og på Uke 18 ser du hullet på 38 mot 80 på vei uten å lese en eneste forklaring. Tegningen tåler å bli vist i plenum.

**Ærlig risiko:** Snittet krever mer lesing første gang enn en vanlig graf, og på 360 px er enhetslinjene nær grensen for hva øyet skiller. Skillet mellom sendt, bestilt og «uten dato» er utledet av simuleringen og er nytt produktkrav: det må avklares om studenten skal få se hva leverandøren har sendt. Snittet er tungt å bygge (SVG med egen projeksjon), og lange På vei-rader kan kreve at målestokken går ned, noe som gjør at samme enhet ser forskjellig ut mellom to uker på telefonen, selv om målestokken alltid står på tegningen. Bygget i seg selv er ramme uten data, og kan oppleves som pynt.

**Gjenbrukbart selv om konseptet velges bort:** Den ene gule nå-kanten som går gjennom alle flater, også tomtene i lærerens oversikt, slik at «hvor er vi nå» har samme tegn overalt.
