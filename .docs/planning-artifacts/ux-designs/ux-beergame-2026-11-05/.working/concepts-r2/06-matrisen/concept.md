# 06 Matrisen

Arbeidsnavn: Matrise.

**Tese (én setning):** Hver uke er en kolonne og hver størrelse en rad, så svingningene blir et mønster du kan lese, og hver kolonne er samtidig regnestykket bak mønsteret.

**Faglig kjerne:** P4 og P5 gjør konseptet best: i Debriefen blir radene til Roller, og bølgen leses som en trapp oppover kjeden (første ordre på 10 eller mer i Uke 6, 11, 13 og 15) med mørkere bånd for hvert ledd (1,8× til 7,6×), mens etterspørselen ligger som én rolig rad under. P1 læres som kolonneregning: −9 + 4 − 8 = −13. P3 læres ved at På vei står rett under saldoraden, og Posisjon legger dem sammen: 0 − 13 + 16 = 3. P2 ses når 24 bestilt i Uke 11 blir 17 levert i Uke 15. P6 er klassebildet: 60 rader med nesten samme form. P7 og P8 står med tall i `10-pedagogikk.svg`.

**Spilldynamikk:** Studenten ser fem rader med en ny kolonne ved høyre kant, som alltid er nå, og taster ordren rett inn i den siste cellen i raden Egen ordre. Under matrisen regnes Posisjon ut med og uten ordren, men systemet anbefaler ingenting. Etter hvert blir cellene smalere: først forsvinner tallene, så står fargebåndet igjen, mens nå-kolonnen alltid har tall. Mønsteret i radene gir et spørsmål til neste ordre, og kolonnen gir tallene til å svare.

**Hjelpegrad:** Standpunkt: tallet nå, mønsteret senere.
- **Klassespill:** de fem rådatarekkene, og Posisjon som ett tall for denne uka, med konsekvensen av ordren du taster. Ingen historikk for Posisjon. Studenten får regnestykket, men ser ikke hvordan posisjonen stiger over tid, så svingningene kan fortsatt oppleves før Debriefen.
- **Replay:** sjette rad med hele historikken for Posisjon, låst opp etter Debriefen. Da vet studenten hva raden betyr, og den blir et verktøy. Forskjellen er tegnet øverst til høyre i `10-pedagogikk.svg` med ekte data for begge: Klassespill og Replay, begge Uke 18.
- **Hvorfor:** forskningen sier at spillere legger lite vekt på det som er på vei selv når det står der, så ett tall tar neppe bort opplevelsen. En farget rad over tid viser derimot overskytingen direkte. Dette er en antakelse som bør prøves mot issue #22.

**Debrief-grep:** Samme matrise med Roller som rader, slik at etterspørselen avsløres som én rolig rad under bølgen, og faseforskyvningen leses som helningen på en trapp uten forklaringsboks.

**Lærerflate-grep:** Stor matrise med 60 spill × uker, sortert etter status og deretter kostnad, med valgbar Rolle og størrelse, der pågående spill slutter der de er, og tabell og tiltak står ved siden av.

**Palett:** Grunn #F1F4F5, flate #FBFCFC, grafitt #21272B, sekundær tekst #4C565E, hårstrek #D2D8DC. Grafitt #596269 og #C9D0D5 brukes der fargen ikke er et tall.
- *Divergerende, netto lager (enheter):* ≤−73 #5C220F · −72 til −37 #A2492D · −36 til −13 #E1A080 · −12 til −1 #FBD0A9 · 0 #F0F0EF · 1 til 12 #D0EDEC · 13 til 36 #8BC0BF · 37 til 72 #1C7676 · ≥73 #043F42. Grensene er 1×, 3× og 6× startlageret.
- *Sekvensiell, ordre inn, levering, på vei, egen ordre (enheter):* 0 #F2F3F5 · 1–4 #D7E1EB · 5–8 #B0C3D8 · 9–14 #839EBE · 15–24 #47658C · 25–44 #2C4365 · ≥45 #162338.
- *Signal:* ingen egen farge. Invertert grafitt med tekst, for eksempel «Spill 2 venter på Noah. KI overtar om 1 t».

**Typografi:** Public Sans 400–700, ett snitt for alt. Tabellsifre (`tnum`) i celler og tabeller, proporsjonale sifre i store enkelttall. Libre Franklin ble valgt bort fordi Google-versjonen ikke har `tnum`; det ble målt i fontfila.

**Fargekontroll (kjørt, ikke anslått):**
- Kontrast mellom celletall og celle er minst 5,4:1 i alle klasser. `build.py` stopper hvis en klasse faller under 4,5:1.
- Rust mot blågrønn på samme steg, protanopi og deuteranopi (Machado 2009): ΔE 8,3 til 11,6 i OKLab×100. Målet på 8 er nådd. Armene har 0,04 forskjell i lyshet på det bleke steget for å klare dette uten at det blir cyan.
- `validate_palette.js --ordinal`: monoton lyshet, ΔL ≥ 0,06 og én kulør gir PASS på alle tre rampene. **Lys ende mot flaten gir FAIL** (1,20–1,39:1 mot kravet 2:1). Dette er bevisst: rolig tilstand skal se rolig ut. Tall i cellen og tabellvisning er kompensasjonen, og i smale bånd er tabellen eneste presise kilde.
- Status er aldri bare farge: grupper og rader har tekst, ugyldige rader har kryss, og polaritet har minustegn der tallet får plass.

**Styrke:** Klassebildet kan vises i plenum som det er, og samme grammatikk og samme skala går igjen fra telefonen til storskjermen. Du lærer ett språk én gang. Tallene ligger i selve grafen, så mønster og regnestykke stemmer overens per konstruksjon.

**Ærlig risiko:**
- **P1 er svakere enn briefens ideal.** Inn og ut og saldo står på felles tidsakse, men arealet mellom inn og ut vises ikke. Kolonneregningen er presis, men krever at studenten leser tall. En linjegraf viser opphopning mer direkte.
- **Sene uker på telefon.** Rundt Uke 29 er cellene om lag 10 px og uten tall. Farge alene er grovere enn en linje for å sammenligne verdier, og sene uker er bare tegnet som ferdigskjermen i rute F, ikke som et eget spillende steg.
- **Ukjent uttrykk.** Varmekart må læres. Første møte krever regelsiden, og det er ikke testet med studenter.
- **Liten tekst i Oversikt.** Tabellen ved siden av veggen bruker 11 px for å holde 60 rader på én skjerm. Det er greit for skanning og svakt for lesing på avstand.
- **Landingssiden viser veggen.** Briefen tillater lærerens oversikt, men studenter som ser siden, kan ane at lageret svinger. Aksen har ingen tall, og etterspørselen vises ikke.
- **Trappa er et valgt mål.** Grensen «10 eller mer» er satt av oss. Den er sann for spill 17 og referansen, men flytter seg om grensen endres.

**Gjenbrukbart selv om konseptet velges bort:** Klasseveggen med 60 spill × uker og felles skala, sortert etter status og kostnad, kan stå som egen Oversikt og plenumsvisning i et hvilket som helst annet konsept.
