# 09 Lagene

**Tese (én setning):** Det finnes bare én graf i hele produktet, og den vokser, ett lag og ett begrep om gangen, når spillet gjør begrepet relevant.

**Faglig kjerne:** P1 til P3 i pedagogisk rekkefølge, alt i den ene grafen.
- **P1 Lager er en opphopning:** Lager som svart linje, Ordre inn og Levering som flate trapper gjennom Uka, og det grå feltet mellom dem er nøyaktig endringen i lageret. `build.py` kontrollerer at dette stemmer for alle fire Roller i alle Uker.
- **P2 Forsinkelse:** Levering-laget viser det du bestilte, om lag fire uker senere. Bestilt 24 i Uke 11, levert 17 i Uke 15, er merket i pedagogikkarket.
- **P3 Det som er på vei blir glemt:** På vei står på null ved siden av Restordren, og den røde streken viser hva ordren gjør med den. Etter Debriefen løftes samme linje opp på Lager, og toppen får navnet Posisjon.
- **P4, P5 og P6:** Debriefen viser dem med samme graf i fire utgaver, og alle ordrene i én graf.
- **P7:** Står som tekst ved den simulerte referansen.
- **P8:** Restordre får sin ene setning den Uka linja krysser null. Koster dobbelt.

**Lagene kommer slik:** Uke 1 Lager. Uke 5 Ordre inn. Uke 8 Levering. Den Uka linja krysser null: Restordre. Uke 10 På vei. Etter Debriefen: Posisjon og Simulert referanse. Det nye laget er vermilion den første Uka og blir så grått. Et lag kan skrus av og på ved å trykke på navnet i grafen, men først når det er introdusert.

**Spilldynamikk:** Studenten åpner Uka og ser at linja har fått ett nytt stykke fram til høyre kant, som alltid er nå. Så taster studenten ett tall, og det eneste som skjer er at en rød strek viser På vei med ordren: 16 + 24 = 40. Bestill låser tallet, og spillet viser hvem det venter på. Grafen hjelper neste ordre ved at Restordre, Ordre inn og På vei står i samme akse, så spørsmålet stiller seg selv, men regnestykket må studenten gjøre.

**Hjelpegrad:**
- **Klassespillet viser** Lager og Restordre, Ordre inn, Levering og På vei, hver for seg og hver fra null. Alle FR-23-verdier ligger under Alle tall, ett trykk unna. Grafen legger aldri sammen, og ordet Posisjon brukes ikke. Studenten kan regne det selv, men blir ikke servert det.
- **Replay viser** i tillegg laget Posisjon, der På vei er løftet opp på Lager og toppkanten er Posisjon, med hva ordren gjør med den. Replay-gjennomgangen legger til Simulert referanse.
- **Hvorfor:** Svingningene må oppleves før Debriefen kan gi læring (issue #22). Studenten får ærlige data og regnestykket, men ikke den ene summen som gjør feilen lett å unngå. Etter Debriefen er summen ikke lenger en krykke, men et verktøy studenten har en grunn til å bruke. Faglærer kan flytte lagene i Klasseøkten, for eksempel gi Posisjon tidlig til et kull som spiller øvelsen for andre gang. Forskjellen er tegnet i `10-pedagogikk.svg`, øverst til høyre.

**Debrief-grep:** Samme graf i fire utgaver samtidig, og gruppa trykker selv på Neste lag, slik at etterspørselen, ordrene og Forsterkningen kommer ett lag om gangen uten at noen ny grafisk form dukker opp.

**Lærerflate-grep:** Én rolig liste med 60 rader, hver med spillnummer, én kort linje med ekte ordreserie, ett tall og én kort tekst, alt på felles skala og tidsakse, sortert slik at det som trenger læreren står først, og resten er ett trykk unna.

**Palett:**
- Hvit `#FFFFFF` er grunnen.
- Blekk `#111111` er tekst og Lager.
- Grå tekst `#5C5C5C` (6,7:1) er sekundærtekst og eldre lag.
- Grå linje `#9C9C9C` er På vei og eldre linjer.
- Hårstrek `#D4D4D4` og areal `#EDEDED`.
- Vermilion `#DB3A12` (4,5:1) er det nye, eller nå.

Roller og lag skilles med direkte etikett, linjevekt og strek, aldri med farge alene. Det grå og det skraverte feltet skiller «lageret faller» fra «lageret stiger» uten farge. Palettvalidatoren består på CVD og kontrast, men feiler kategoriband-sjekken for blekk, med vilje: Her brukes utheving, ikke kategoriske fargetoner.

**Typografi:** Mulish i tre vekter. 300 for store sifre og overskrifter, 400 for tekst, 700 for tall og det viktigste. Tabellsifre. Ingen rammer og ingen bakgrunnsflater. Eneste fylte flate er den ene knappen på en skjerm som utfører handlingen.

**Styrke:** Ingen annen idé er så lett å forstå, å forklare i plenum eller å bygge: Én grafkomponent, én regel for når et lag kommer, og samme språk fra telefon til Debrief og lærerrad. Fagbegrepene kommer i pedagogisk rekkefølge. Skjermen er rolig nok til at også 60 rader hos læreren kan skannes på sekunder.

**Ærlig risiko:**
- Tre tette grå linjer rundt 4 til 12 er det tetteste området i grafen på en telefon. Det kan bli vanskelig å skille Ordre inn fra Levering, særlig i sterkt lys.
- Ved Uke 18 vokser På vei (80) så mye at skalaen presser Lager og flytene sammen. Studenten kan skru av På vei, men det er nettopp det laget vi vil ha framme.
- Knapper og brytere uten flater og rammer er mindre oppdagbare. Trykk på linjenavnet for å skru av et lag må læres, og må testes.
- Skalaen på y-aksen endrer seg når tallene krever det, og det kan overraske.
- FR-23 sier at alle verdier skal være synlige på 360 px. Her er de ett trykk unna under Alle tall, ikke framme på skjermen. Det må godkjennes som tolkning av kravet.
- Klassespillets hjelpegrad er et standpunkt, ikke et funn: Det må prøves med studenter.
- Ved tastet ordre viser spillet en konsekvens (På vei 40). Det er bevisst, men det er også en liten hjelp som kan svekke opplevelsen, slik issue #22 advarer mot.

**Gjenbrukbart selv om konseptet velges bort:** Regelen om at hvert begrep kommer inn med én setning den Uka det blir relevant, og at det samme laget senere løftes opp på Lager og får navnet Posisjon.
