# Story 4.1 – visuell kontroll

Tatt 2026-11-18 mot compose-stakken (`http://127.0.0.1:8080`), fullside, 390 og 1280 px. Sammenlignet med `mockups/09-alle-sider.png` (Lærerhjem), `mockups/02-laerer-klasse.png` (Lag Klasse), `DESIGN.md` og `EXPERIENCE.md`. Ingen kodeendringer var nødvendige.

- `laererhjem-tom-390.png` – ny Faglærer (fra Invitasjon), tomt Lærerhjem: én linje og «Ny Klasse» som eneste handling. Stemmer (EXPERIENCE.md UJ-1).
- `laererhjem-tom-1280.png` – samme ved 1280 px. Stemmer.
- `laererhjem-fylt-390.png` – fire Klasser (rutet `/api/classes`), «Klassene dine» som Lenker med hårlinjer, «Ny Klasse» under, «Venter»/«Neste frist» stablet under. Stemmer; ingen sidelengs rulling, lange navn brytes.
- `laererhjem-fylt-1280.png` – samme ved 1280 px, «Venter»/«Neste frist» i høyre kolonne. Stemmer i hovedsak; høyre kolonnes topplinje står på høyde med «Klassene dine»-overskriften, ikke med listas første hårlinje (vurdering).
- `lag-klasse-tom-390.png` – «Lag Klasse», tomt skjema: Navn, Institusjon, Emnekode (valgfri), én primærknapp i full bredde. Stemmer.
- `lag-klasse-tom-1280.png` – samme ved 1280 px, skjemakolonne som i 02. Stemmer; rekkefølgen Navn → Institusjon → Emnekode skiller seg fra 02s Navn → Emnekode (Institusjon finnes ikke i mockupen; vurdering).
- `lag-klasse-feil-390.png` – lagret tomt: restordre-kant og grunn under Navn og Institusjon, fokus på Navn. Stemmer.
- `lag-klasse-feil-1280.png` – samme ved 1280 px. Stemmer.
- `lag-klasse-lagringsfeil-390.png` – rutet 500 ved lagring: «Klassen ble ikke laget. Prøv igjen.» over knappen, verdiene står. Stemmer.
- `lag-klasse-lagringsfeil-1280.png` – samme ved 1280 px. Stemmer.
- `klasse-lagret-390.png` – Klassesiden etter lagring: smuler, h1 «class-of-1994», «IBE160 · Demohøgskolen». Stemmer (minimal side i 4.1).
- `klasse-lagret-1280.png` – samme ved 1280 px. Stemmer.
- `klasse-student-nektet-390.png` – Student åpner `/klasser/{id}`: «Du har ikke tilgang til denne siden.» og «Til Hjem». Stemmer (EXPERIENCE.md, FR-5).
- `klasse-student-nektet-1280.png` – samme ved 1280 px. Stemmer.
