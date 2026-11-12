# Merge prd-beergame til main

## 2026-11-12 kl. 12:15 — Bård Pettersen

### Oppgave
Slå grenen `prd-beergame` sammen med `main` og bytte over til `main`.

### Plan
- Kontrollere at arbeidskopien var ren og at `main` ikke hadde egne commits utover grenen.
- `git fetch`, bytte til `main`, `git pull --ff-only`, `git merge prd-beergame`.

### Resultat
- `main` hadde 0 egne commits som grenen manglet; `prd-beergame` lå 14 commits foran, så merge ble en fast-forward (ingen merge-commit). `main` peker nå på `59cbaa1` («Oppdatering av UX og PRD …»).
- Aktiv gren er nå `main`. Lokal `main` er 39 commits foran `origin/main`; ingenting er pushet.
- Ingen konflikter.

### Åpne punkter
Ingen.
