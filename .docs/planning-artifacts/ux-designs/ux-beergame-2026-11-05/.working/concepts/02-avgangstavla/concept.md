# 02 Avgangstavla («Avgang»)

**Tese (én setning):** Spillet er en mekanisk avgangstavle der hver kasse er en klaff, så studenten kan se med øynene at 13 skyldig står mot 40 på vei, og belønningen er at hele tavla klaffer til neste Uke.

**Spilldynamikk:** Hver verdi står som klaffer i én tavle med faste kolonner: rad, tall, og én liten rute per kasse. Studenten blar to sifferruller til 24, og raden «om 4 uker» klaffer inn før bekreftelsen, slik at lengden på den legger seg under de andre ankomstene. Bekreft låser rullene med en stang, og Sara blir stående mens de andre Rollene står som rader i en avgangsliste («FABRIKK JONAS, VENTER 3 MIN»). Når siste ordre kommer, går en bølge ovenfra og ned, alt rykker én rad opp, under 2 sekunder og mulig å hoppe over. Lager og restordre er rader, på vei er ankomster («om 1 uke 4»), og ingenting sier hvor mange Uker som gjenstår.

**Debrief-grep:** Hele tavla står blank og etterspørselen klaffer fram som én liten rad med 4 til 8, og på delt skjerm står hele spillet som lang logg med kundens rad helt nederst, så de ville ordretallene møter 4 4 4 4 8 8 8 8 samtidig for alle.

**Lærerflate-grep:** Oversikten er en storskjerm-tavle med 60 faste, nummererte rader i tre kolonner, ferdige rader demper seg selv, og status leses av koblingslinjas form (hel, tverrstrek, hull per KI-Sete, ring, plugg) fra andre siden av datalaben.

**Palett:** Klaffsvart `#1F1D1A`/`#181614`, Kabinett `#2B2926`, Benhvit `#F1EDE2`, Dempet `#A8A395`, Stasjonsgul `#F4B822` (eneste aksent), Hallvegg `#E8E3D6`, Veggfuge `#DAD4C5`, Blekk `#1C1B18`.

**Typografi:** Big Shoulders Display 700/800 for alt på klaffer og overskrifter på veggen. Barlow Semi Condensed for malte etiketter på kabinettet. Barlow for brødtekst. Barlow er tegnet etter skilt og bilskilt, så det hører hjemme i en stasjonshall.

**Styrke:** Metaforen bærer selve tallene: rutene gjør på vei og restordre sammenlignbare som lengder, kaskaden er en ekte rytme og belønning uten poeng, og koblingslinjene gir status som aldri er avhengig av farge. Knapper, felt og navigasjon er samme klaff, så produktet henger sammen fra landing til rapport.

**Ærlig risiko:** Tavla er tett. På 360 px er det 10 verdirader, historikk, ruller og fire statusrader på samme flate, og små klaffer med søm leser dårligere enn vanlig tekst, så små statusrader må testes på ekte telefon og i dagslys. Rutene sprenger kolonnen når tall passerer 24 i senere Uker (restordre 40, leveranser 31), så de trenger en skalaregel. Fulltekst i Debriefen faller naturlig ut av klaffene og står som malt tekst på kabinettet, og mørk tavle i 36 Uker må tåle kveldsbruk og lys hall begge deler.

**Gjenbrukbart selv om konseptet velges bort:** Én rute per kasse i faste kolonner, med hel, hul og skråstrek for sendt, bestilt og skyldig, gjør «jeg så ikke det som var på vei» synlig uansett visuelt språk.

Merknad om data: `ki_seter` i fixture gir bare antall, så hvilket Sete hullet står på, er plassert etter spillnummer. Rader per ankomst er avledet fra ordrehistorikk og Distributørens sendinger og sjekket mot `paa_vei_foer_ordre` i `build.py`. Utløpt 3 og venter 5 er mitt demo-oppslag av de 8 uregistrerte med gyldig adresse.
