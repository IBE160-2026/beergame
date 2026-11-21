# Story 7.4 – visuell sjekk av Oversikten (`/klasseokter/{id}/oversikt`)

Fersk Faglærer, tre Klassespill (4 + 2 + 4 seter, 2–4 uker spilt, ett spill som venter), Chromium `--lang=nb-NO`. Hver tilstand er tatt i tre bredder: `-390` (telefon), `-1280` (laptop), `-200pct` (1280 px med 200 % tekst). Ingen sideveis sidescroll i noen av dem (målt: scrollWidth minus clientWidth = 0). Ingen kodeendringer var nødvendig, så skjermbildene er tatt én gang.

- `oversikt-standard-<bredde>.png`: standardvegg (Fabrikk, Netto lager, Alle) med medianlinje og bånd over veggen, «Median, Fabrikk» og «Kjedekost/uke, snitt» under. Samsvarer med `08-laerer-oversikt`; Visning-bryteren sitter ved overskriften.
- `oversikt-celler-ordre-<bredde>.png`: Celler = Ordre, flytfargeskala (Under 5 … 30 og over), median over Ordre. Samsvarer.
- `oversikt-celler-kost-<bredde>.png`: Celler = Kost per uke, samme flytskala. Samsvarer. Ved 390 klippes «Venter på …»-teksten av høyre kant av veggregionen (regionen scroller, siden gjør det ikke). Se avvik.
- `oversikt-rolle-detaljist-kost-<bredde>.png`: Rolle = Detaljist (kost). Samsvarer; radene heter «Median, Detaljist».
- `oversikt-status-venter-<bredde>.png`: Status = Venter, ett spill; medianen er spillets egen verdi, uten bånd. Samsvarer.
- `oversikt-status-tom-<bredde>.png`: Status Venter valgt mens spillet går videre, «Ingen spill i dette utvalget.» i stedet for veggen; «Venter 0» blir stående som valgt. Samsvarer.
- `oversikt-tabell-<bredde>.png`: Vis som tabell med Rolle = Detaljist; tabellen fyller regionen, «Venter på» på én linje (1280), «Median, Detaljist» og «Kjedekost/uke, snitt» i bunnteksten. Samsvarer. Ved 390 scroller tabellen sideveis inne i regionen.
- `oversikt-vegg-320.png`, `oversikt-ordre-320.png`, `oversikt-tabell-320.png`, `oversikt-vegg-1280.png`, `oversikt-ordre-1280.png`: fra byggeren, ikke tatt på nytt. `oversikt-tabell-1280.png` er overskrevet av denne kjøringen.

## Avvik overlatt til skjønn
- Ved 390 er «Venter på Spiller2 0461 (Distribu…» avkuttet i veggregionen (`oversikt-celler-kost-390.png`, `oversikt-standard-390.png`). Samme grep som tidligere stories (regionen scroller, tabindex 0); full tekst står i «Spill og seter» under.
- Tallene i veggcellene og medianradene er svært små (rundt 8 px) ved 390. Som i mockupen; tabellvisningen gir alle tall i 13 px.
