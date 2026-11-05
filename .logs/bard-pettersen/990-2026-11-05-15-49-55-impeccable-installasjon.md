# Impeccable-installasjon

## 2026-11-05 kl. 15:49 — Bård Pettersen

### Oppgave
Installere design-skillen Impeccable for Claude Code før UX-arbeidet starter. Brukeren ba om at kommandoen ble funnet på nett og kjørt. Økten startet med `/bmad-help`, som viste at PRD-finaliseringen venter på ni beslutninger; brukeren valgte likevel å gå videre mot UX-design.

### Plan
- Søke opp installasjonsmåten og kontrollere den mot originalrepoet, siden kildene var uenige og ett treff var en fork.
- Lese pluginens manifest og hooks før installasjon.
- Installere med `claude plugin` og scope `local`, slik at hooks ikke slår inn i andre prosjekter eller hos andre som bruker repoet.

### Resultat
- Kilde: `pbakaus/impeccable`, Apache-2.0, ikke fork, aktivt vedlikeholdt.
- Kjørt: `claude plugin marketplace add pbakaus/impeccable --scope local` og `claude plugin install impeccable@impeccable --scope local`.
- Verifisert med `claude plugin list` og `claude plugin details`: versjon 4.8.0, scope local, 1 skill, 4 agenter, 3 hooks (SessionStart, PostToolUse på Edit/Write, Stop), omtrent 439 tokens fast kostnad per økt.
- Skrevet til `.claude/settings.local.json`, som er git-ignorert. Ingen sporede prosjektfiler er endret av installasjonen.
- Skillen er ikke prøvd ennå. Den lastes først når Claude Code startes på nytt.
- Fra README-en, ikke testet her: motoren kan lastes ned til `~/.impeccable/bin/` ved første hook-kjøring. Telemetri om valgte visuelle retninger er på som standard og slås av med `npx impeccable telemetry off`.
- Ingen endringer i PRD-en. De ukommitterte `reconcile-*.md`-filene og `.memlog.md` er ikke rørt.

### Åpne punkter
- Ingen nye. PRD-finaliseringen følges opp i Issue #12.
