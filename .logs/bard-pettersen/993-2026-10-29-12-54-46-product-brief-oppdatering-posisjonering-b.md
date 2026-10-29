# Product brief: oppdatering etter research og posisjonering B

## 2026-10-29 kl. 12:54 — Bård Pettersen

### Oppgave
Starte med `/bmad-help`, få A vs B-posisjoneringen forklart, pressure-teste B med `bmad-forge-idea`, og oppdatere product brief til en endelig versjon basert på research gjort 2026-10-26.

### Plan
- Forklare A vs B ut fra addendum, issue #3 og konkurranserapporten.
- Forge på B (`.docs/forge/beergame-positioning-b/`), lukket som CLARIFIED fordi founder ikke har tid til å teste.
- `bmad-product-brief` i Update-modus: konkurranse- og kostnadsrapportene, brukerstemme og litteratur (tre sistnevnte via utdrag fra en agent, ikke lest i fulltekst).
- To avgjørelser tatt av founder via spørsmål: LLM-motstandere som standard (med regelbasert innstilling), og lett læringsmåling.
- Oppdatere i samme mappe, ikke ny datert mappe (mappedato = opprettelsesdato; memlog og git bevarer historikken).

### Resultat
- `.docs/planning-artifacts/briefs/brief-beergame-2026-09-04/brief.md` og `addendum.md` omskrevet/utvidet, status `final`, updated 2026-10-29. Endringer: konkurransepåstand rettet (En Dash, transentis, Zensimu, Forio), LLM-evidens blandet, SSRN 5266281 fjernet fra briefen og merket uverifisert i addendumet, B som uprøvd hypotese med fallback, kostnadstall (modellert), reproduserbarhet, debrief-risiko, personvern, prisankre, scope.
- Forge: `.docs/forge/beergame-positioning-b/` (memlog, `forge-report.html`, utfall CLARIFIED).
- Brief-memlog (27 linjer) oppdatert med alle beslutninger.
- Ikke gjort: digests, `imports/` og `model-switcher/` i research-mappen er ikke lest; ingen automatisk struktur-/språkgjennomgang med agenter; briefen og forge-mappen er ikke committet (brukeren har ikke bedt om det).
- Issues: #2 og #3 lukket, #6 kommentert, #10 opprettet.

### Åpne punkter
- Issue #10: PRD/arkitektur: LLM som standard med regelbasert innstilling per klasse (reproduserbarhet, kostnad, logging).
- Issue #6 (læringsmåleplan i PRD) oppdatert med terskelen fra briefen.
- Issue #1, #4, #5, #7, #8, #9 er uendret åpne.
- Neste BMad-steg: PRD (`bmad-prd`).

## 2026-10-29 kl. 13:50 — Bård Pettersen

### Oppgave
Sjekke om andre ølspill faktisk kjører LLM-drevne boter med suksess (setningen «The moat is not the AI model» i briefen), og deretter løfte fungerende LLM-boter som kjernen i differensieringen.

### Plan
- Lese egen research (`llm-r2-i.md`, `ai-bots-r1-d.md`, `bots-r2-g.md`) og gjøre to raske nettsøk for nyere funn.
- Skrive om moat-punktet, executive summary, fallback og risiko 1 i briefen, med løftet formulert som noe vi må bevise, ikke et bevist faktum.

### Resultat
- Funn: ingen vedlikeholdt løsning med LLM-boter til studenter. LLM-spillere finnes bare i forskningsdemoer (GenAI Beer Game uten menneskeplass, Long/Simchi-Levi, SupplyNet-prototype uten kode, Happily.ai-markedsføring) og en forlatt Hugging Face Space (Lilli98, «Build error»). Nettsøk 2026-10-29 ga ingen nye produkter.
- `brief.md` endret (ikke committet): moat-punktet («getting LLM opponents to work»), forsvarbar posisjon, executive summary («working AI opponents plus the explanation»), ny fallback-linje i Success Criteria, risiko 1.
- Issue #11 opprettet, #10 kommentert.

### Åpne punkter
- Issue #11: bevis at LLM-motstandere fungerer som undervisningsmotstandere (variasjon ca. 12–13 %, ugyldige ordre, troverdighet, realistisk bullwhip).
- Issue #10, #8 og #6 er uendret åpne; briefen er fortsatt ukommittert.
