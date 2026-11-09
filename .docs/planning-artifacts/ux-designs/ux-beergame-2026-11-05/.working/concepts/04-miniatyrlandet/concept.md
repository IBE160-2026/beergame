# 04 Miniatyrlandet

**Tese (én setning):** Spillet er en håndlaget modell av en liten norsk kystby, der tallene dine er gjenstander du kan telle: kasser på paller, biler på veien og kø ved porten.

**Spilldynamikk:** Du står i din egen lagerhall, sett ovenfra på skrå med taket av. En tom hall er Lager 0, fire røde biler med 13 tomme rammer er Restordre 13, og fire blå biler med 16 kasser er På vei 16, plassert etter hvor mange uker de har igjen. Du taster 24, ser seks stiplede biler dukke opp under de fire ekte, og sender ordren med én stor knapp, så kjører budbilen seddelen inn i tåka. Mens du venter trekker kameraet seg ut: tente vinduer og skilt viser hvem som har bestilt, naboene har taket på, og når alle har bestilt, rykker alt ett hakk på 2 sekunder (Hopp over står framme). Tallene står fast under modellen, så beslutningen tar sekunder selv kveld nummer tre.

**Debrief-grep:** Tåka letter og du ser alle fire haller med kassene og køene talt opp, med en tidslinje du kan dra, fra køene som bygger seg mot Fabrikk i Uke 18 til stablene som fyller hallene i Uke 29.

**Lærerflate-grep:** Et kart over 60 små kvartaler der status er form (lav kloss, hus, pausestolper, flagg, rødt hevet kvartal) står ved siden av en ekte tabell sortert etter hastverk, og klikk på et kvartal viser setene i spillet.

**Palett:** Fjord `#0B7285`, Dyp fjord `#07505F`, Lys fjord `#2AA7B8`, Furugrønn `#1E6B46`, Gress `#86C96E`, Oker `#E09F1F`, Lys oker `#F6C552`, Falurød `#B3322A`, Blekk `#0C2E38`, KI-fiolett `#3C2F7A` (bare KI-merket). Diagramfarger for Rollene er validert for fargeblindhet: `#E09F1F, #B3322A, #1496BE, #1B7A4B` (oker er under 3:1 mot hvit, så linjene har direkte etiketter og tall i tabell). **Typografi:** Baloo 2 for tall og overskrifter, runde og vennlige som modellbyskilt. Nunito for brødtekst og tabeller, med tabulære tall.

**Styrke:** Dette er konseptet som ser mest ut som et ekte dataspill, og det er ikke pynt: `build.py` stopper hvis tegnede kasser og rammer ikke stemmer med tallene i `fixture.json`, så «tell kassene» er bevist i hver render. Studenten kjenner køen før et eneste tall er lest, og det er nøyaktig den følelsen Debriefen senere peker på.

**Ærlig risiko:** Telleregelen sprenger ved store tall: Fabrikk har 54 i restordre i Uke 18, og på telefon får en kø på 40 eller mer ikke plass, så rutene må zoome ut eller samle biler i rekker. Bilene i tre-ukers-feltet lover også for mye, for Saras 24 kommer ikke som 24 i Uke 15 (17 kommer fram), så modellen må vise at de ikke er lastet ennå. Isometrisk grafikk er dyrt å animere og å gjøre tilgjengelig, og kartet over 60 kvartaler er pent, men skannes dårligere enn tabellen ved siden av.

**Gjenbrukbart selv om konseptet velges bort:** Rett før ordren sendes tegnes tastet ordre som stiplede biler rett under bilene som allerede er på vei, så «24 mot 16» blir synlig uten regning.
