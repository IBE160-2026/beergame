# Konkurrentresearch beergame

## 2026-10-26 kl. 20:30 — Bård Pettersen

### Oppgave
Kjøre `bmad-deep-recon` (competitive, deep-preset) for å svare på om noen allerede tilbyr bot-fylte roller eller repeterbar solo-trening med AI-debrief, og som en tilleggsavgrensning sjekke AI-styrte spillmotorer/boter. Resultatet skal informere PRD-differensiering og valget mellom positionering A og B. Brukeren ba om å bli spurt før GitHub Issue #1 lukkes.

### Plan
- Plan-gate godkjent av brukeren: 9 kjente konkurrenter pluss oppdagelse av nye, seks dimensjoner (tilbud, pris, posisjonering, trajektorie, kundestemme, AI-boter/motorer), `deep` (6 assistenter, 12 kilder/runde, dybde 3), validering `normal`.
- Runde 1: seks parallelle assistenter. Runde 2: seks oppfølgingsassistenter på leads (bot-logikk, OSS, LLM-systemer, Zensimu, Forio/eBeer, etterspørselsevidens). Runde 3: fire (teardown av En Dash m.fl., skeptiker-søk, uavhengig verifisering, replay-evidens).
- Sluttsjekk: mekanisk sitatsjekk (`recon_kit.py citations`) og semantisk sitatsjekk med fersk assistent (35 funn, rettet i rapporten).
- Kjøringsmappe: `.docs/planning-artifacts/research/competitive-beer-game-competitors-2026-10-26/` (research.md, .memlog.md, digests/).

### Resultat
- `research.md` ferdig (status: complete) med eksekutivsammendrag, seks dimensjoner, kryssinnsikter, motbevis, anbefalinger, åpne spørsmål, 52 kilder og staleness-kart. Ledger: 9 verifisert, 5 uverifisert, 1 omstridt, 1 omstøtt (numeriske refs).
- Hovedfunn: briefens nyhetspåstand holder ikke. Minst sju produkter fyller tomme roller med enkle regelbaserte boter, og beergame.endash.us (gratis, lansert 2026-08-25) har solo mot AI-roller, replay og debrief; klientkoden ble lest og botene er regler, ikke LLM. Ingen vedlikeholdt lærerprodukt dokumenterer LLM-motstandere med menneskesete eller LLM-debrief; kun forskningsprototyper (bl.a. HF-Space med GPT-4o-mini, bygge-feil).
- LLM-evidensen er blandet: arXiv 2605.17036 gir opptil 80 % lavere kostnad enn studentlag, men default-CV 26-52 %. SSRN 5266281, som briefen siterer, ble ikke funnet. Prisanker: gratis (transentis, En Dash, Cohen) til Forio $168 per person; eBeer $10-20 uendret siden 2021.
- Evidensen for replay-tesen er tynn, og uavhengig lærer-/studentstemme mangler nesten helt.
- Ingen kode eller konfig i repoet er endret; kun researchmappen er lagt til (ukommittert, utenfor loggcommiten). HTML-briefing og `bmad-review` (structure, prose) er ikke kjørt.

### Åpne punkter
- Issue #2: rett opp product brief (En Dash, LLM-påstander, SSRN-kilde).
- Issue #3: beslutning om positionering A vs B.
- Issue #4: hands-on verifisering (En Dash multiplayer-boter, Skill Dynamics, Zensimu solo, MA-system /Rules) og lærerintervjuer.
- Issue #1 (konkurrentverifisering): i hovedsak besvart av research.md; lukkes først etter at brukeren har bekreftet.
