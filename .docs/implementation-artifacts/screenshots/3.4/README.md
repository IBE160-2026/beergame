# Story 3.4 – visuell kontroll

Tatt mot `http://127.0.0.1:8080` med Playwright (ruting, `setOffline`, sideklokke), 390 og 1280 px, helside. Ingen av tilstandene har egen mockup (spine-only); målt mot DESIGN.md → System og EXPERIENCE.md → State Patterns. Ingen siderulling ved 390 px i noen tilstand.

- `admin-loading-390.png`, `admin-loading-1280.png` – Skjelett på `/admin` mens `/me` henger, før 1 s: overskriftsfelt, `ink-muted` radetikett, `hairline`-linje, ingen tekst. Stemmer, med forbehold: overskriftsfeltet er en fylt `hairline`-blokk med `rounded.sm`, som DESIGN.md ikke nevner for Skjelett (vurdering).
- `admin-loading-slow-390.png`, `admin-loading-slow-1280.png` – samme Skjelett med «Laster …» i `ink-secondary` etter 1 s. Stemmer.
- `laererhjem-pageerror-390.png`, `laererhjem-pageerror-1280.png` – `/me` svarer 500: Tilkoblingslinje «Siden kunne ikke lastes.» med «Prøv igjen» som Lenke til høyre, ingen Skjelett. Stemmer.
- `admin-offline-390.png`, `admin-offline-1280.png` – frakoblet på Admin-område: «Frakoblet. Det du har skrevet, er tatt vare på på denne enheten.» og «Sist oppdatert 21:14» i `ink-secondary`, mellom to `ink-muted`-linjer. Stemmer.
- `hjem-offline-390.png`, `hjem-offline-1280.png` – samme linje på Hjem (Student). Stemmer.
- `logginn-offline-390.png`, `logginn-offline-1280.png` – frakoblet på «Logg inn» med utfylt e-post som står igjen; ingen «Sist oppdatert», siden siden ikke har levende data. Stemmer.
- `admin-reconnected-390.png`, `admin-reconnected-1280.png` – «Tilkoblet igjen.» etter at forbindelsen kom tilbake. Stemmer.
- `admin-logout-failed-390.png`, `admin-logout-failed-1280.png` – «Logg ut» svarer 500: «Utloggingen gikk ikke. Prøv igjen.» under knappen, fokus på knappen. Stemmer etter retting (før: feillinjen gjorde hodet bredere, og navn og «Logg ut» brøt til ny rad ved 390 px). Den generelle «Det ble ikke lagret. Prøv igjen.» er ikke tatt: ingen side har en lagrende handling ennå.
- `logginn-session-expired-390.png`, `logginn-session-expired-1280.png` – utløpt økt sendt til `/logg-inn?neste=%2Fadmin&utlopt=1`: «Du er logget ut. Logg inn igjen for å fortsette.» mellom to linjer, med fokus og synlig fokusring. Stemmer; fokusringen ligger tett på linjene og teksten (vurdering).
