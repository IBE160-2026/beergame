# Story 7.5 visuell kontroll (Oversikt, «Oppdater automatisk» og Tilkoblingslinje)

Referanse: `08-laerer-oversikt` (tegner ikke bryteren; den er spine-only), DESIGN.md og EXPERIENCE.md (Tilkoblingslinje, State Patterns → Oversikt). Ingen rettinger var nødvendige.

- `oversikt-pa-390.png`, `oversikt-pa-1280.png`: bryteren «Oppdater automatisk» På, «Oppdatert hh:mm:ss» under tellingene, ingen primærknapp, ingen sideveis side-scroll. Matcher.
- `oversikt-av-ventende-390.png`, `oversikt-av-ventende-1280.png`, `oversikt-av-ventende-1280-tekst200.png`: bryteren Av, «1 endring siden hh:mm» med sekundærknappen «Oppdater» (på 390 under bryteren, 44 px høy), veggen uendret. Matcher.
- `oversikt-av-ventende-fokus-390.png`: samme med fokus på bryteren. Matcher.
- `oversikt-utdatert-390.png`, `oversikt-utdatert-1280.png`, `oversikt-utdatert-1280-tekst200.png`: Tilkoblingslinje «Ikke oppdatert siden hh:mm. Prøver igjen.» med «Last inn på nytt» til høyre, mellom to 1 px linjer, ingen fyll eller ikon, veggen beholder siste verdier. Matcher; linken er ikke avskåret på 390.
- `oversikt-lesefeil-390.png`, `oversikt-lesefeil-1280.png`, `oversikt-lesefeil-1280-tekst200.png`: Tilkoblingslinje «Ikke oppdatert siden hh:mm.» med «Prøv igjen» (bakgrunnslesing feilet mens strømmen er live); bryteren står På, siden uendret. Matcher.

Kjent og akseptert: på 390 ruller selve Matrisevegg-raden («Venter på Spiller1 …») sideveis i sin egen region (Story 7.2, EXPERIENCE.md), ikke siden.
