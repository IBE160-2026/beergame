# Dyp research: kostnad, reproduserbarhet og læringsevidens

## 2026-10-26 kl. 20:58 — Bård Pettersen

### Oppgave
Brukeren ba om forslag til research- og brainstormingtemaer før PRD, og valgte deretter dyp research på tre temaer (kostnad per spilløkt, behov for reproduserbarhet, evidens for læring ved gjentatt spilling og debrief), kjørt parallelt med subagenter via `bmad-deep-recon`.

### Plan
- Plan godkjent av brukeren: preset `deep`, validering `normal`, red team av, forskningsbrannmur (subagenter fikk bare sin egen brief), kun nettsøk. Tre separate kjøringer: `technical`, `user-voice`, `academic-lit`.
- Runde 1: seks subagenter (to per spor). Runde 2: seks subagenter som fulgte ledetråder. Runde 3: tre subagenter for henting og verifisering (lit ×2, kostnad ×1). Reproduserbarhetssporet stoppet etter runde 2 (tynne offentlige data).
- Syntese i `research.md` per spor, deretter tre uavhengige verifiserere (ferske kontekster) som sjekket sitering og gjorde uavhengige kontroller; formuleringer rettet etter funnene.

### Resultat
Tre ferdige rapporter (`status: complete`) i `.docs/planning-artifacts/research/` (ukommittert; kun loggfila committes av sesjonsloggen):
- `technical-ai-agent-cost-per-beer-game-session-2026-10-26/research.md`: LLM-agenter er billige per økt på små modeller (modellert ca. 3 cent for Haiku 5.5, ca. 0,59 USD for Sonnet 5.5 uten cache; tokentall er våre antakelser, ingen publisert kilde). Ingen leverandør garanterer determinisme; Anthropic støtter ikke temperature/top_p/top_k på Claude 4.7+. RL-agent (DQN) er kostnadsminimerer, ikke menneskelignende. Anbefaling: agentlag bak ett policy-grensesnitt, logg alle agentbeslutninger.
- `user-voice-lecturer-need-for-reproducibility-in-bee-2026-10-26/research.md`: Ingen kilde viser at identisk etterspørsel kreves for rettferdig karaktersetting; klassisk fast 4→8-kortstokk er standard i veiledninger. Én fersk stemme (THE 2026) sier fast etterspørsel blir forutsigbar. Anbefaling: instruktørvalgt etterspørsel og delt seed per klasse, ikke bit-eksakt agentdeterminisme.
- `academic-lit-repeated-play-and-debrief-learning-effec-2026-10-26/research.md`: Kjernepåstanden (repetisjon + AI-debrief gir forståelse) er en uprøvd hypotese. Repetisjon bedrer ytelse (svakt belagt), men Paich & Sterman 1993 viste forbedring uten innsikt. Ingen studie krysser debrief og repetisjon; AI-debrief har lite kontrollert evidens. Anbefaling: måleplan i PRD.
- Verifisering: kostnadstabellen regnet riktig om; rettet 12–23 formuleringer per rapport (blant annet temperature-påstand, «spiller optimalt», Cheng 2014-formulering, Bastani 17 %). Verifiseringsfilene ligger i `digests/verification-*.md` i hver kjøremappe.
- Ikke kjørt: HTML-briefing og `bmad-review`-polering (doc_standards).

### Åpne punkter
- Hent Martin 2004, Fu & Gonzalez 2006 og Jeong & Hong 2011 via bibliotek — Issue #5.
- PRD: læringsmåleplan for første kurs — Issue #6.
- Lærerintervjuer (5–8) om reproduserbarhet — Issue #7.
- Prototype som måler tokens/kostnad/latens/ugyldige ordre, og Sterman-parametre fra primærkilde — Issue #8.
- Briefen må rettes etter funnene (læringspåstand som hypotese m.m.) — lagt som kommentar på eksisterende Issue #2.
- Eksisterende åpne issues #1, #3 og #4 (konkurrentverifisering, posisjonering A/B) er uendret og ikke berørt av denne økten.

## 2026-10-26 kl. 22:26 — Bård Pettersen

### Oppgave
Brukeren ba om at den tekniske researchen også sjekker OpenRouter, siden det er AI-leverandøren de bruker.

### Plan
- Avgrenset utdyping (Deepen) av kostnadsrapporten: leste OpenRouters offisielle dokumentasjon selv (pris/gebyr, parametre, ruting, caching, structured output, rate limits, personvern/ZDR, fallbacks, reasoning), uten subagenter og uten ny verifiseringsrunde.

### Resultat
- Ny seksjon 4 «OpenRouter as the AI provider» og anbefaling 7–9 i `technical-ai-agent-cost-per-beer-game-session-2026-10-26/research.md`; rå-funn i `digests/openrouter-deepen-r4-a.md` (ukommittert).
- Hovedfunn: OpenRouter tar listepris pluss 5,5 % gebyr ved kjøp av kreditt (8 % på Business), så Haiku 5.5-økt går fra ca. 3,0 til ca. 3,1 cent. Ikke-støttede parametre droppes stille uten `require_parameters`. Standardruting lastbalanserer og faller tilbake mellom leverandører, og standard `data_collection` er «allow», så studentdata krever `deny` og/eller ZDR. EU-ruting krever Business-plan. Determinisme er ikke garantert, så beslutningsloggen må også lagre svarende modell og leverandør.
- Konklusjonen om at kostnad ikke er blokkereren er uendret. Dokumentasjonen er eneste kilde (medium konfidens); ikke uavhengig verifisert.

### Åpne punkter
- OpenRouter-oppfølging lagt som kommentar på Issue #8 (prototype: temperature/seed-oppførsel, latens, DPA og EU-ruting).

## 2026-10-29 kl. 11:56 — Bård Pettersen

### Oppgave
Brukeren ba om å bruke billigere modeller enn Haiku (f.eks. DeepSeek) via OpenRouter og lage logikk som bytter modell ukentlig etter lavest kostnad per oppgave, og presiserte at dette er en del av researchen.

### Plan
- Hentet OpenRouters offentlige modell- og ZDR-endepunktlister (ingen API-nøkkel), filtrerte på ZDR, seed, temperature, structured outputs, oppetid og kontekst, og regnet estimert kostnad per økt.
- Skrev et kjørbart referanseprogram (screen, decide, selftest) og dokumenterte designet som seksjon 5 i den tekniske rapporten.

### Resultat
- Nye filer i `.docs/planning-artifacts/research/technical-ai-agent-cost-per-beer-game-session-2026-10-26/` (ukommittert): `model-switcher/model_switcher.py`, `model-switcher/screen-2026-10-29.json`, `digests/openrouter-switcher-r5-b.md`; `research.md` har ny seksjon 5 og anbefaling 10–13.
- Funn (øyeblikksbilde 2026-10-29): Haiku 5.5 mangler seed og temperature på alle ZDR-endepunkter; DeepSeek V4.1 Flash koster anslått 0,0157–0,0178 USD per økt (ca. 40–47 % under Haiku) og støtter seed/temperature; samme modell varierer 10,7 ganger i pris mellom leverandører, så bytteren må velge endepunkt (modell + leverandør + kvantisering). gpt-oss-20b og mistral-nemo er 80–85 % billigere, men ingen kilde viser spillkvalitet for noen av dem.
- Bytter-logikk: screen, skyggeevaluering på seedede golden games, beslutning på kostnad per gyldig oppgave med kvalitetsgrenser, 15 % hysterese og 7 dagers nedkjøling, canary og rollback. Økter låses til ett endepunkt, og læringsstudien krever frosset modell. Selvtesten (9 beslutningstilfeller, 4 rollback-tilfeller) består. Alle terskler er plassholdere.
- Break-even: ukentlig evaluering koster anslått 3,60 USD og lønner seg først over ca. 260 økter per uke.
- Ikke verifisert av egen verifiserer; estimerte kostnader bygger på antatte tokentall og ignorerer reasoning-tokens.

### Åpne punkter
- Evalueringsharness, kalibrering av fidelity-bånd og tester av billige modeller på spillet — Issue #9.
- OpenRouter-test av seed/temperature for billige kandidater og latens per endepunkt — kommentar på Issue #8.
