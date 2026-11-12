# Arkitektur for ØL-spillet (bmad-architecture)

## 2026-11-12 kl. 13:15 — Bård Pettersen

### Oppgave
Kjøre `bmad-help` for å finne neste steg, og deretter lage arkitekturen for ØL-spillet v1. Brukerens foretrukne stack i `.docs/planning-artifacts/architecture/technology.md` skulle brukes som utgangspunkt, tilpasset dette prosjektets MVP. Brukeren valgte «fast path» og ba om en oppsettsguide i tillegg til arkitekturdokumentet.

### Plan
- `bmad-help`: lese katalog, konfig og artefakter. Konklusjon: brief, research, PRD og UX er ferdige (`status: final`); arkitektur er neste påkrevde steg.
- `bmad-architecture`, fast path: lese `technology.md`, PRD med tillegg og UX-dokumentene, sjekke versjoner mot npm, PyPI og endoflife.date, logge beslutninger i memlog og skrive dokumentet derfra.
- Reviewer-gate: lint, to avstemminger (mot PRD og mot UX) og tre uavhengige reviewere (sjekkliste, teknologi og versjoner, angrep på hull), og så rette funnene.
- Arbeidsmappe: `.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/`.

### Resultat
Nye filer, ikke committet:
- `ARCHITECTURE-SPINE.md` (status: draft): modulær monolitt med ren kjerne (`engine`, `analysis`) og 25 beslutninger (AD-1 til AD-25). Lint gir 0 funn.
- `SETUP-GUIDE.md`: kontoer, miljøvariabler, Railway- og Supabase-oppsett, CI og sjekkliste før første klasseøkt.
- `.memlog.md`: 53 innførsler med beslutninger, versjoner, antakelser og åpne spørsmål.
- `reviews/`: fem reviewfiler (`review-reconcile-prd.md`, `review-reconcile-ux.md`, `review-rubric.md`, `review-tech-currency.md`, `review-adversary.md`).

Beholdt fra `technology.md`: FastAPI og Python med uv, SQLAlchemy async og Alembic, Next.js, React, Tailwind og shadcn, TanStack Query, Supabase Postgres og Storage, Railway, Resend, pydantic-ai, Caddy som eneste inngang, mock-fallback og `production`-gren som deploy-trigger.

Avvik fra `technology.md`:
- Ingen Redis: Postgres LISTEN/NOTIFY med SSE for live-oppdatering, og procrastinate som jobbkø.
- psycopg 3 i stedet for asyncpg, fordi procrastinate krever det.
- Egen React SVG-grafmodul i stedet for Recharts (antakelse).
- Droppet for MVP: betaling, regnskap, innholdstjeneste, backup-cron, watchdog og Cloudflare-worker.

Reviewene fant ett kritisk funn hver i tre av fem, og alle kritiske og høye funn er rettet:
- Veiledede uker ville gått gjennom i én transaksjon. Rettet med `view_week` og ett uke-steg per transaksjon (AD-2).
- Navn kunne lekket til LLM og beslutningslogg. Rettet ved å dele i `seat_state` (bare tall) og `table_status` (personer) (AD-3).
- Innstillinger ble fryst ved tildeling i stedet for ved startdato. Rettet med `sessions.lock` (AD-4).
- Prototypen hadde ikke noe hjem. Rettet med simuleringskjører på produksjonskoden (AD-22).
- Nye regler: åpne turer og én klokke (AD-20), gruppedebrief (AD-21), innholdsversjoner (AD-23), kompatible deploy (AD-24), oversikt fra vedlikeholdte sammendrag (AD-25).
- Pseudonymnøkkelen er ikke lenger en miljøvariabel. Arbeiderne er delt i `worker-ai` og `worker-batch`.
- To tekniske feil rettet: openapi-typescript 7.13 krever npm-override mot TypeScript 6, og Supabase session pooler har for liten standard pool.

Lukket: Issue #10 (LLM-motstandere som standard med regelbasert innstilling), løst av PRD og AD-4, AD-5, AD-6 og AD-15.

Ikke gjort:
- Dokumentet er ikke satt til `status: final`. Det venter på brukerens gjennomgang.
- Middels og lave reviewfunn er ikke gjennomgått punkt for punkt.
- `bmad-spec` og epics og stories er ikke kjørt.

### Åpne punkter
- Issue #27: founder-gjennomgang av arkitekturen, antakelsene og gjenstående middels og lave reviewfunn, deretter `status: final`.
- Issue #28: drift før piloten (staging, PITR-backup med restoreøvelse, overvåking, lasttest, tilkoblingsbudsjett).
- Issue #29: Resend lagrer kontodata i USA; før i DPIA-pakken eller bytt leverandør før piloten.
- LLM-leverandør og modell avgjøres av prototypen og følges i Issue #8 og Issue #9.
