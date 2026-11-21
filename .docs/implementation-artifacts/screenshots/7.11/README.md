# Story 7.11: visuell kontroll av Varselbåndet (avslutning av Epic 7)

Tatt fra commit 9ca3a41 (før rettingene ved avslutningen), som Faglærer, Chromium med `--lang=nb-NO`, fullside. Ferske Klasser med regelbasert KI: spill A med tre Studenter der én har bestilt (venter på to), spill B med to Studenter der én har bestilt (venter på én), så den ventede Studenten i B fjernet fra Klasselista. Bredder 390 px, 1280 px og 1280 px med 200 % tekst. Ingen sidelengs rulling på siden i noen av bildene. Sammenlignet med `08-laerer-oversikt.png`, DESIGN.md og EXPERIENCE.md.

- `oversikt-uten-band-<bredde>.png`: ingen spill venter: ingen band og ingenting i stedet for det, ingen primærknapp. Samsvarer.
- `oversikt-band-en-<bredde>.png`: én Student ventes på: «Spill 1 venter på Spiller1 6964 (Detaljist) i under 1 min.» på `restordre-fill` med `ink`-tekst, «Send Melding» som eneste primærknapp, spillets rad tonet i veggen og spillisten med `ink`-understreket «Melding», «Venter ellers» sier «Ingen andre spill venter.». Samsvarer med mockupens bånd (uten «Pause spillet» og KI-overtakelse, som er Epic 8).
- `oversikt-band-flere-<bredde>.png`: spillet venter på to Studenter: båndet navngir den som har ventet lengst, spillisten lister begge. Samsvarer. Avvik (rettet): på 390 px brøt «min.» alene til ny linje i båndteksten; varighetene bruker nå hardt mellomrom (se `../epic-7-avslutning/oversikt-390.png`).
- `oversikt-band-flere-tabell-<bredde>.png`: «Vis som tabell» med båndets rad tonet. Samsvarer. Vurdering: ved 1280 px er «Venter på» så bred at kolonnene «Kjedekost» og «Melding» ligger utenfor regionens høyre kant og må rulles fram; regionen ruller, siden gjør det ikke.
- `oversikt-band-fjernet-<bredde>.png`: den ventede Studenten er fjernet fra Klassen: «Spill 1 venter på Detaljist i under 1 min.», raden viser «Detaljist: Student». Samsvarer med spesifikasjonen.
- `melding-fra-band-<bredde>.png`: «Send Melding» fra båndet åpner «Melding til Spiller1 6964, Spill 1», «Meldingen går til 1 student.». Samsvarer.
- `melding-fra-rad-<bredde>.png`: radens «Melding» i spillisten åpner Meldingsskjemaet for Klassespillet. Samsvarer.

Øvrige funn: toppen (navn og «Logg ut») brøt på to linjer på 390 px (felles sidehode, rettet ved avslutningen). Ingen andre avvik.
