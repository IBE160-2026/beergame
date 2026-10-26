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
