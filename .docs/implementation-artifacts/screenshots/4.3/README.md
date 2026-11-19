# Story 4.3 – visuell kontroll

Klassesiden for class-of-1994, «Klasseliste», ved 390 og 1280 px, tatt etter rettingene. Sammenlignet med mockup 02, DESIGN.md og EXPERIENCE.md. Ingen tilstand ruller sidelengs ved 390 px.

- `klasse-ugyldige-rader-1280.png`: «Ugyldige rader: 6 av 11» med alle sju årsakstyper unntatt «Tom celle», «Registrer manuelt», primær «Send 5 Invitasjoner» og merknaden. Valgt kolonne C bare tonet, uten suffiks (Issue #85). Stemmer. Avvik som må vurderes: «Valgt fordi alle rader unntatt fire» mot 6 ugyldige, fordi dubletter ser ut som adresser.
- `klasse-ugyldige-rader-390.png`: samme tilstand stablet. Stemmer. Send-området står over listen over ugyldige rader (venstre kolonne først). I forhåndsvisningen stikker slutten av «Emma Solberg» fram ved siden av den faste «Rad»-kolonnen.
- `klasse-feil-kolonne-1280.png`: kolonne B valgt, nedtrekkslisten og årsaken i feilstil, «Send 0 Invitasjoner» utilgjengelig med «Ingen gyldige adresser å invitere.». Stemmer. Overskriften «E-post i fila» står over Student-ID-verdier.
- `klasse-feil-kolonne-390.png`: samme tilstand ved 390 px. Stemmer.
- `klasse-over-100-ugyldige-1280.png`: 130 ugyldige av 150. Listen stopper på 100 med «Viser de første 100 av 130 ugyldige radene.». Stemmer.
- `klasse-over-100-ugyldige-390.png`: samme tilstand ved 390 px (lang side). Stemmer.
- `klasse-lim-inn-tom-1280.png`: tomt innlimingsfelt med hjelpetekst, «Fortsett» og «Velg fil i stedet». Stemmer.
- `klasse-lim-inn-tom-390.png`: samme tilstand ved 390 px. Stemmer.
- `klasse-lim-inn-utfylt-1280.png`: blandede linjer med `Navn <adresse>` og `"Moe, Thea" <…>`. Stemmer.
- `klasse-lim-inn-utfylt-390.png`: samme tilstand ved 390 px. Stemmer.
- `klasse-innlimte-adresser-1280.png`: «Innlimte adresser», «7 adresser lest», «Start på nytt», «Ugyldige rader: 3 av 7» med «Nr.» og «Innlimt verdi», «Send 4 Invitasjoner». Ingen kolonnevalg eller forhåndsvisning. Stemmer.
- `klasse-innlimte-adresser-390.png`: samme tilstand ved 390 px. Stemmer.
- `klasse-tom-innliming-1280.png`: tom innliming. «0 adresser lest», utilgjengelig «Send 0 Invitasjoner», «Ingen gyldige adresser å invitere.». Stemmer. Merknaden om ugyldige rader står der selv om det ikke finnes noen.
- `klasse-tom-innliming-390.png`: samme tilstand ved 390 px. Stemmer.
- `klasse-lim-inn-avvist-1280.png`: avvist innliming (422 er forfalsket). Feltet har restordre-ramme og feillinjen står under hjelpeteksten. Stemmer.
- `klasse-lim-inn-avvist-390.png`: samme tilstand ved 390 px. Stemmer.

Rettet i «Story 4.3: visuelle rettinger»:
- Radene for ugyldige rader var omtrent 69 px høye ved bred visning, mot omtrent 54 px i mockupen. De har nå `sm:py-1`.
- «Velg fil i stedet» sto høyere enn «Fortsett». Den er nå sentrert loddrett.
- Det er lagt til en e2e-test for grensen på 100 rader, med fixture `mange-ugyldige.csv`.
