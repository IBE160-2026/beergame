# Regelbasert KI-spiller

Den regelbaserte KI-spilleren bestiller etter en fast regel som kalles forankring og justering. Den tar utgangspunkt i hvor mange enheter den regner med at kunden vil bestille. Så justerer den ordren opp eller ned for å nærme seg et ønsket lager (lager minus restordre) og et passende antall enheter på vei. De samme tallene gir alltid den samme ordren.

Den ser på disse tallene for sitt eget sete:
- eget lager
- egen restordre
- innkommende ordre fra kunden, uke for uke
- enheter på vei, det vil si bestilt, men ikke mottatt

Den bruker innstillingene som gjelder i spillet: forsinkelsene og største tillatte ordre. Den ser ikke tallene til naboene i kjeden, heller ikke når innstillingene lar studentene se dem. Kostnadene for lager og restordre inngår ikke i regelen.

Regelen har fire parametere, som hentes fra en egen parameterfil. Verdiene skal etter planen komme fra Sterman (1989), en studie av hvordan mennesker bestiller i en forsyningskjede. Foreløpig brukes runde plassholderverdier, valgt bare slik at kjeden holder seg i balanse med standardinnstillingene (Klassisk). De er ikke hentet fra studien og er ikke verifisert ennå.
