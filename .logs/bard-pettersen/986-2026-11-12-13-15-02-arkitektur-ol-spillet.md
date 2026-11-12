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
Nye filer (committet senere i økten som `20b0f66`):
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

Senere samme økt (etter brukerens tilbakemeldinger):
- Recharts er tatt inn igjen for vanlige linje- og søylediagrammer (brukerens avgjørelse). Bare kjedebåndet og matriseveggen håndlages som SVG. Første graf-story er en prøve på kolonnejustering mot tabell og PDF-resultat (AD-18). Punktet over om «egen SVG-grafmodul i stedet for Recharts» gjelder derfor ikke lenger.
- Andre retterunde med tre subagenter: 53 forslag i `reviews/proposals-a.json`, `-b.json` og `-c.json`, lagt inn med skript uten feil. Dokumentet har nå 26 beslutninger (AD-27 ny: kontrolltest som egen type klasseøkt; AD-26 og AD-28 er ikke brukt). Lint gir 0 funn.
- Nye regler i runden: pause og utspilling (AD-2), referanseordre og spillvakt beregnes ett sted (AD-5, AD-20), budsjett med reservasjon og låst modellkonfig (AD-6), lagrede faktasett og sitater som tegnposisjoner (AD-7), hendelseskatalog (AD-8), én eier av varsler og fast rekkefølge ved testfristen (AD-9), to navngitte Admin-unntak (AD-12), delt ordrekilde i beslutningsloggen (AD-15), fast `SeatState`-modell (AD-3), statistikk bare fra aggregater (AD-14) og felles form på KI-tekst.
- 13 funn er ført som utsatte punkter i dokumentets Deferred-liste, hvert med når det må avgjøres.
- Memloggen har 63 innførsler.
- Arkitekturmappa er committet som `20b0f66` og pushet til `origin/main` på brukerens forespørsel.
- Brukeren ba om `status: final` på arkitekturdokumentet og oppsettsguiden. Det er satt og ført i memloggen. Epics og stories skal ikke lages før brukeren sier ifra.

### Åpne punkter
- Issue #27: founder-gjennomgang av arkitekturen og antakelsene (blant annet stille tid 22–07 for e-post, Takeover-e-post i daglig samlemelding, PITR-mål, eu-central-1), deretter `status: final`. Reviewfunnene er nå enten rettet eller ført som utsatte punkter.
- Issue #28: drift før piloten (staging, PITR-backup med restoreøvelse, overvåking, lasttest, tilkoblingsbudsjett).
- Issue #29: Resend lagrer kontodata i USA; før i DPIA-pakken eller bytt leverandør før piloten.
- LLM-leverandør og modell avgjøres av prototypen og følges i Issue #8 og Issue #9.
