# 07 Horisonten

Arbeidsnavn: **Horisont**. Det eneste mørke konseptet: kveld på hybelen eller et nedblendet datalab, der grafen lyser av innhold og ikke av effekter.

**Tese (én setning):** Når hvert tall i spillet er en tynn stripe på felles tidsakse, kan Sara lese sine fire tall på ett blikk, og etter Debriefen kan hele klassen se 60 spill på én skjerm og forstå at formen kommer av strukturen.

**Faglig kjerne:** P6 og P5.
- **P6:** 60 spill for samme Rolle, stripe under stripe, med eget spill anonymt markert (`07-debrief.svg`, delt skjerm). Formen går igjen, og alle 42 ferdige spill i demodataene går under null som Grossist.
- **P5:** ordre per Rolle i fire striper med felles skala og en strek ved første uke med ordre over 8: Uke 6, 11, 13, 15, og Forsterkning 1,8× → 7,6×.
- **Andre prinsipper:**
  - P3: På vei-stripa legger seg tone på tone mens restordren roper.
  - P1: `−9 + 4 − 8 = −13`, bak ett trykk.
  - P2: 24 bestilt ble 17 levert fire uker etter.
  - P4: Ordre inn er aldri merket som etterspørsel.
  - P8: `13 × 1,00 + 0 × 0,50`.
  - P7: simulert referanse med nyansen om overreaksjon.

**Spilldynamikk:** Studenten ser fire striper på én akse (Netto lager, Ordre inn, Egen ordre, På vei), der høyre kant er nå og hvert tall også står som tall. Sara taster ett heltall, og da tegnes konsekvensen med hvit strek i Egen ordre og På vei, sammen med regnestykket `0 − 13 + 16 + 24 = 27`, før hen bekrefter. I Veiledede uker står lesemåten skrevet rett på stripa: «Lager 12: står på gulvet», og første restordre henger fra taket. Grafen hjelper neste ordre ved å gjøre det stille tallet (På vei) like synlig som det høylytte (Restordre), uten å si hva som er riktig.

**Hjelpegrad:**
- **Klassespill:** fire rå striper med egne tall. Posisjon finnes ikke som stripe, bare som regnestykke når et tall er tastet. Det viser konsekvensen av valget, men gir ingen retning før valget. Studenten skal oppleve svingningen selv, og issue #22 er grunnen til at stripa ikke er med.
- **Replay:** Posisjon får egen, alltid synlig femte stripe, slik at innsikten fra Debriefen kan brukes. Replay-gjennomgangen viser Replay over Klassespillet, merket «Ikke like for like».
- **Forskjellen er tegnet** i `10-pedagogikk.svg` (nederst til høyre) og `09-alle-sider.svg` (Replay).
- **Etter Debriefen** låses også firerollerstriper, 60-stripe-visningen og simulert referanse opp.

**Debrief-grep:** Fire striper for ett spill, så 60 striper for hele klassen uten navn og rangering, forløst av én setning: «60 grupper. Samme kjede. Nesten samme form.»

**Lærerflate-grep:** 60 rader i fire Rolle-kolonner med ekte `netto_lager`, sortert slik at det som trenger læreren står øverst; pågående spill slutter på gjeldende uke, så status og framdrift leses som en trapp i selve grafen, og Spill 2 (23 t) er uthevet med ramme og tekst.

**Palett** (kjørt gjennom dataviz-skriptet: alle tre rampene passerer `--ordinal` mot brønnen, og polparet blågrønn/kobber i tone 2 har CVD ΔE over 12. Paret feiler skriptets kategoriske lyshetsbånd og delvis kroma, fordi dette er rampetrinn på mørk flate. Gulv og tak bærer derfor retningen uten farge):
- **Grunn og tekst:** Skifer `#1F272C` (grunn), Lerret `#192025`, Brønn `#2A343A`, Hårstrek `#3D4A52`, Tekst `#EAEFEE`, Sekundær `#B7C3C5`, Dempet `#98A7AA`.
- **Over null, Blågrønn:** `#3A928C` `#56B8AC` `#9FE0D3` `#DDF5EF`.
- **Under null, Kobber:** `#B26E3E` `#D08B4B` `#F0B982` `#FBE3C9`.
- **Strømmer, Nøytral skifer:** `#6D7E88` `#93A3AC` `#BAC6CC` `#E2E8EA`.
- **Signal, Blek gul:** `#EFD66B`, bare for nær overtakelse.
- **Fire toner, ikke tre:** klassen når ±159, så 40 enheter per tone krever fire trinn. Fjerde tone er sjelden: 26 av 7 496 ukeverdier for netto lager er over 120.

**Typografi:** Commissioner (Google Fonts) med vekt 300 til 700: lett 300 i store titler, 400 og 500 i tekst og etiketter, tabellsifre der tall står i kolonner. Ingen andre fonter.

**Styrke:**
- En stripe på 40 px bærer det en vanlig graf bruker 150 px på, med samme regel overalt: én tone er 40 enheter. Lager står på gulvet og restordre henger fra taket, så retningen kan leses uten farge.
- Lærer og student kan faktisk lese hele klassen på én skjerm, og en professor kan vise den i plenum.

**Ærlig risiko:**
- Horisontgrafer er uvanlige. Lesemåten er forenklet til én setning, men dette er ikke testet på studenter.
- Ved Uke 11 er stripene lave og nesten flate (4 mot 8 er 6 mot 13 px på 64 px stripe). Felles skala gjør at små tall ser små ut, og de store tonene dukker først opp sent i spillet.
- Rader på 12,75 px med 11 px tekst i Oversikt er tett på 1440. Det er skanning, ikke lesing.
- Mørk flate i et lyst auditorium må testes.
- Hero-bildet på landingssiden viser formen på svingningen, uten akse og uten navn. Det er innenfor briefen, men en student kan se det før spillet. Vurder å bytte det ut.
- 42 ferdige og 18 pågående i Debrief-snittet forutsetter at spill 17 er ferdig mens fixturen viser det ved Uke 11. Det er en konstruert stillbilde-situasjon.

**Gjenbrukbart selv om konseptet velges bort:** 60 spill som striper med eget spill anonymt markert, som P6-avslutning på Debriefen i et hvilket som helst visuelt språk.

Demodata. Simulerte referanser er merket Simulert.
