# Story 4.2 – visuell kontroll

Tatt 2026-11-19 mot compose-stakken (`http://127.0.0.1:8080`), fullside, 390 og 1280 px, som `faglaerer@example.com` på demo-Klassen «class-of-1994» (stagingen slettet igjen etterpå). Sammenlignet med `mockups/02-laerer-klasse.png` (venstre kolonne og «Forhåndsvisning av fila»), `DESIGN.md` (Filopplasting, Layout & Spacing) og `EXPERIENCE.md`. Filer: e2e-fiksturene i `frontend/e2e/fixtures/roster/`, pluss to syntetiske CSV-er (`to-epostkolonner.csv`: Navn, Studentnummer, E-post, Privat e-post med 6 av 12 adresser; `for-mange-rader.csv`: 5001 rader). Ingen side ruller sidelengs i noen av bildene.

Rettet (commit «Story 4.2: visuelle rettinger»): forhåndsvisningen holder «Rad» fast og ruller den valgte kolonnen inn i sitt eget område (før lå valgt kolonne utenfor bildet ved 390 px), og «Adresser»-feltet holder skjemakolonnens bredde (før fylte det hele 1280-bredden).

- `klasse-for-opplasting-390.png` – tom Filopplasting: «Canvas-eksport», rammet boks med «Velg fil», filtypelinje, «Lim inn adresser i stedet». Stemmer.
- `klasse-for-opplasting-1280.png` – samme ved 1280 px, boksen i skjemakolonnens bredde. Stemmer.
- `klasse-lastet-opp-390.png` – Canvas people (.xlsx): filnavn, «12 rader lest», «Bytt fil», «E-postkolonne» = D med grunn; forhåndsvisning med «Rad» fast og D tonet i bildet. Stemmer etter retting.
- `klasse-lastet-opp-1280.png` – samme ved 1280 px, skjema til venstre og forhåndsvisning til høyre som i 02. Stemmer; kolonne E kuttes i høyrekanten (rulleområde) og overskriften har «(e-post)» som ikke står i 02 (vurdering).
- `klasse-karakterbok-390.png` – Canvas karakterbok (.csv): D «SIS Login ID», «alle rader unntatt én», rullet til D. Stemmer.
- `klasse-karakterbok-1280.png` – samme ved 1280 px. Stemmer; «Points Possible»-raden vises som rad 2 (besluttet i spec).
- `klasse-annen-kolonne-gyldig-390.png` – valgt D «Privat e-post»: «6 av 12 rader ser ut som adresser.», D i bildet. Stemmer.
- `klasse-annen-kolonne-gyldig-1280.png` – samme ved 1280 px; området rullet slik at D er helt synlig, A kuttet bak «Rad». Stemmer.
- `klasse-annen-kolonne-ugyldig-390.png` – valgt A «Navn»: «Ingen rader i denne kolonnen ser ut som adresser.» i `ink-secondary`. Stemmer med spec; grunnlinjen har ingen feiltilstand (vurdering).
- `klasse-annen-kolonne-ugyldig-1280.png` – samme ved 1280 px. Som over.
- `klasse-ingen-epostkolonne-390.png` – fil uten adresser: «Velg kolonne», forklaring og «Lim inn adresser i stedet». Stemmer.
- `klasse-ingen-epostkolonne-1280.png` – samme ved 1280 px. Stemmer.
- `klasse-ulesbar-390.png` – ødelagt .xlsx: «Filen kunne ikke leses. …» i `restordre` under boksen. Stemmer.
- `klasse-ulesbar-1280.png` – samme ved 1280 px. Stemmer.
- `klasse-for-mange-rader-390.png` – 5001 rader (ekte 422 fra api): samme linje som ulesbar fil. Stemmer med spec.
- `klasse-for-mange-rader-1280.png` – samme ved 1280 px. Stemmer.
- `klasse-lim-inn-390.png` – «Lim inn adresser i stedet» åpnet: «Adresser», tekstfelt, hjelpetekst, «Velg fil i stedet». Stemmer.
- `klasse-lim-inn-1280.png` – samme ved 1280 px, feltet i skjemakolonnens bredde. Stemmer etter retting.
- `klasse-ikke-eier-admin-390.png` – Admin åpner Klassen: «Du har ikke tilgang til denne siden.» og «Til Admin-område». Stemmer (FR-5).
- `klasse-ikke-eier-admin-1280.png` – samme ved 1280 px. Stemmer.
- `klasse-ikke-eier-admin-faglaerer-390.png` – Admin og Faglærer som ikke eier Klassen: nektet, «Til Lærerhjem». Stemmer.
- `klasse-ikke-eier-admin-faglaerer-1280.png` – samme ved 1280 px. Stemmer.
