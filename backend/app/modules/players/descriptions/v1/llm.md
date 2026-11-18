# LLM-spiller

LLM-spilleren er en KI-spiller som får ordren sin fra en stor språkmodell. Hver uke får modellen tallene for sitt eget sete: eget lager, egen restordre, innkommende ordre, enheter på vei, kostnadene og sine egne tidligere uker. Hos forhandleren er innkommende ordre sluttkundenes etterspørsel; de andre setene ser bare ordrene fra kunden sin i kjeden. Modellen ser ikke tallene til de andre leddene i kjeden, heller ikke når innstillingene lar studentene se dem, og den får ikke vite hvor mange uker som er igjen.

Modellen får ikke vite at den spiller et spill. Den får beskjed om at den har ansvaret for vareflyten i en bedrift og skal holde bedriftens egne kostnader så lave som mulig over tid. Svaret må være et helt antall enheter mellom minste og største tillatte ordre, og systemet kontrollerer svaret før ordren legges inn.

Atferden varierer fra gang til gang: den samme situasjonen kan gi ulike ordrer. LLM-spilleren kan spille bedre enn en typisk student.

Når modellen svikter, legges den regelbaserte ordren inn i stedet, bare for den uken. Det skjer når modellen ikke svarer i tide, når svaret ikke er en gyldig ordre, når tjenesten som leverer modellen, gir en feil, eller når det ikke er budsjett igjen til å spørre modellen.

En automatisk kontroll (spillvakten) sammenligner ordrene over de siste ukene med to referanser: ordren den regelbaserte spilleren ville lagt inn, og en nesten optimal ordre. Spillvakten bytter setet til den regelbaserte spilleren for resten av spillet når ordrene avviker for mye fra den regelbaserte ordren, eller når de ligger mistenkelig nær den nesten optimale ordren. Grensene er foreløpige og ikke kalibrert ennå.

Når kostnadsgrensen for KI er nådd, byttes alle LLM-seter som bruker av det samme budsjettet, til den regelbaserte spilleren for resten av spillet, ikke bare for den uken.
