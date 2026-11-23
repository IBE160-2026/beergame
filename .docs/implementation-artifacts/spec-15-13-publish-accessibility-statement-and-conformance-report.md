---
title: 'Story 15.13: Publish the accessibility statement and the conformance report'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '3485446466da849bc772ea074fbfdd566e9a9872'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      Nothing stops the placeholder contact address tilgjengelighet@example.com from reaching production.
    evidence: |-
      nb.accessibility.contact.email is a placeholder; readiness item R14 tracks it, but no build or
      preflight check refuses it. Story 15.14's preflight is the natural place to refuse it.
    location: >-
      frontend/src/copy/nb.ts (accessibility.contact.email)
    severity: medium
  - summary: >-
      The conformance scan sees the Debrief only before it opens; the open Debrief's steps, charts and quiz are not in the report.
    evidence: |-
      The scan's live game is still running, so /debrief/{id} shows its not-open state. Scanning the open
      Debrief needs a played-out game (dev playout route plus the Debrief opening) in the scan's setup;
      the Debrief specs already run axe on those states. The report states the limit under Surfaces.
    location: >-
      frontend/e2e/conformance.spec.ts
    severity: medium
---

<intent-contract>

## Intent

**Problem:** NFR-6 asks for an accessibility statement in the product and a conformance report the founder can hand to Institutions. Neither exists: there is no statement page, no site footer, and the axe checks of the e2e specs leave no record an Institution can read.

**Approach:** A public statement page `/tilgjengelighet` (copy in `nb.accessibility`), linked from a site-wide footer that also stands on the Landing. A report command (`npm run conformance`) runs a dedicated Playwright scan of every surface on this branch at 320, 360 and 1440 px, 400 % zoom and 200 % text with axe, then writes a dated Markdown report under `docs/accessibility/` that lists each surface with pass or its violations, the veraPDF result (or why it was not run), the founder's manual checks (open until filled) and the independent review done in the founder's place, and names the report in the readiness record of Story 15.11.

## Boundaries & Constraints

**Always:** all UI copy in `frontend/src/copy/nb.ts` (bokmål, no exclamation marks, passes `check:copy`); the statement page reflows at 320 px and with 200 % text without horizontal scroll and passes axe (WCAG 2.1 A/AA tags of `e2e/support/axe.ts`); the footer is a `contentinfo` landmark with one Lenke, a 44 px tap target, on every page except the print route and the shared projection screen (`/delt-skjerm`); the scan creates fresh data only (fresh Lecturer via the `lecturerSession` fixture, `liveClassGame`), never changes the demo Class; the report lists surfaces of Epics 11–14 and Story 15.1 as not yet built; the founder's manual checks (screen reader, keyboard only) show `open` until `by` and `date` are filled; the readiness record gets the report as an open item with the report's file name.

**Never:** no backend change; no new dependency; the scan is not part of the normal e2e run (skipped unless `CONFORMANCE=1`); no story marks a founder item passed; no invented provider or contact values beyond a placeholder address flagged in the readiness record; no veraPDF run (no Student report PDF exists on this branch).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean surface | scan result with no violations, no horizontal scroll at a viewport | that cell reads `pass` | — |
| Violations | scan result with axe violations | the cell lists the rule ids; a details section lists rule, impact, help and the node targets | — |
| Horizontal scroll | `scrolls: true` | the cell says `horizontal scroll` (with any rule ids) | — |
| Surface not opened | scan result with `error` | the cell reads `not checked` and the details give the error's first line | — |
| Missing viewport | no result for a surface at a viewport | the cell reads `not checked` | — |
| veraPDF absent | no `--verapdf` file | the report says not run: no Student report PDF on this build (Epic 13) | — |
| veraPDF given | `--verapdf <file>` (veraPDF text/XML summary) | the report states compliant/non-compliant from the file and its path | unreadable file: command exits non-zero with a message |
| Manual check open | entry without `by` or `date` | status `open` | — |
| Manual check filled | entry with `by`, `date`, `result` | status `done`, with who and when | — |
| No results | results dir empty or missing | command exits non-zero, no report written | message names the dir |
| Readiness link | readiness.md has R13 row | R13's report link points at the new dated file | row missing: command exits non-zero |

</intent-contract>

## Code Map

- `frontend/src/app/layout.tsx` -- root layout; add `<SiteFooter />` after `{children}` inside `Providers`.
- `frontend/src/components/app-header.tsx` -- header pattern (gutters `px-gutter-phone lg:px-margin-laptop`) the footer mirrors.
- `frontend/src/components/link.tsx` -- `Link` (Lenke, `standalone` = 44 px tap target) for the footer and statement links.
- `frontend/src/app/(auth)/laerertilgang/page.tsx` -- public page pattern (AppHeader, main, ConnectionLine, h1) for `/tilgjengelighet`.
- `frontend/src/modules/landing/landing-page.tsx` -- the Landing; the footer appears under it (no change needed beyond the layout).
- `frontend/src/copy/nb.ts` -- add `accessibility` section (sibling of `landing`, NOT inside it: the `landing` section bans quotes).
- `frontend/scripts/check-copy.mjs` -- copy rules the new section must pass.
- `frontend/e2e/support/axe.ts`, `frontend/e2e/support/classes.ts` (`test`, `lecturerPage`, `expectAccessible`, `VIEWPORTS`), `frontend/e2e/support/live-game.ts` (`liveClassGame`), `frontend/e2e/support/auth.ts` (`demoSession`, `untilFontsLoaded`) -- reuse in the scan.
- `frontend/e2e/replay-finish.spec.ts:157` -- real path to a Replay: `liveClassGame(..., 1, {aiMode: "rule_based"})`, `POST /api/dev/class-sessions/{id}/quiz-passed`, `POST /api/me/class-sessions/{id}/replay`.
- `frontend/e2e/landing.spec.ts` -- 400 % zoom = 320 × 256 viewport; 200 % text via `html { font-size: 200% }` init script.
- `frontend/scripts/scripts.test.mjs` -- existing Vitest home for script tests (`scripts/**/*.test.mjs`).
- `docs/ops/readiness.md` -- readiness record (Story 15.11); add R13 (conformance report incl. founder's manual checks) and R14 (statement contact address).
- `.github/workflows/ci.yml` (`e2e` job) -- add a scan step and upload its results as an artifact.

## Tasks & Acceptance

**Execution:**
- `frontend/src/copy/nb.ts` -- add `accessibility`: `footerLink`, `pageTitle`, `title`, `updated`, sections (scope and standard WCAG 2.1 AA; status «delvis i samsvar»; known deviations list; how it was tested; contact route: Students tell their Faglærer, others write to the placeholder address; Uutilsynet as complaint route) -- one copy source.
- `frontend/src/components/site-footer.tsx` -- client component: `<footer>` with hairline top, the Lenke «Tilgjengelighetserklæring» to `/tilgjengelighet`; renders nothing on `/print/*` and `/delt-skjerm/*`.
- `frontend/src/app/layout.tsx` -- render the footer.
- `frontend/src/app/(auth)/tilgjengelighet/page.tsx` + `frontend/src/modules/accessibility/statement.tsx` -- the statement page, public, metadata title.
- `frontend/e2e/accessibility-statement.spec.ts` -- footer link from Landing, a logged-in page and «Logg inn» reaches the statement; no footer on `/delt-skjerm`; statement at 320, 1440 px and 200 % text: no horizontal scroll, axe clean, h1, contact route and known deviations visible.
- `frontend/e2e/conformance.spec.ts` -- skipped unless `CONFORMANCE=1`; one test per viewport (320, 360, 1440, 400 % zoom, 200 % text) that opens every surface (public; Student Hjem, Spill, Regler, Debrief, Replay; Lecturer Lærerhjem, Klasse, Klasseøkt, Oversikt, Spillinnsikt; Admin pages) and writes `{surface, role, path, viewport, violations[{id, impact, help, targets}], scrolls, error}` JSON to `CONFORMANCE_OUT` (default `test-results/conformance`).
- `frontend/scripts/conformance-report.mjs` -- pure `renderReport()` + `updateReadiness()` and a CLI: `--results <dir>`, `--verapdf <file>`, `--date`, `--out`; writes `docs/accessibility/conformance-report-<date>.md` and repoints R13's report link in `docs/ops/readiness.md`.
- `frontend/scripts/conformance.mjs` + `package.json` script `conformance` -- runs the scan with `CONFORMANCE=1` (exit code ignored), then the report; `--from <dir>` skips the scan (a CI artifact).
- `frontend/scripts/conformance-report.test.mjs` -- Vitest for every matrix row.
- `docs/accessibility/manual-checks.json` -- founder's checks (screen reader NVDA+Chrome, VoiceOver iOS, keyboard only, 200 % text by eye) all open; `independentReview` with the review agent's keyboard/focus/axe results.
- `docs/accessibility/conformance-report-2026-11-22.md` -- generated by the command on the local stack, committed.
- `docs/ops/readiness.md` -- R13, R14 rows and a short section on the report.
- `.github/workflows/ci.yml` -- scan step + artifact upload (`if: always()`), job timeout raised.

**Acceptance Criteria:**
- Given any page but print and `/delt-skjerm`, when it renders, then a footer with «Tilgjengelighetserklæring» links to `/tilgjengelighet`, including on the Landing.
- Given a visitor not logged in, when they open `/tilgjengelighet`, then the statement in bokmål shows scope, status, known deviations, the contact route and the complaint route.
- Given the statement page at 320 and 1440 px and with 200 % text, when axe runs, then no violations and no horizontal scroll.
- Given the local stack, when `npm run conformance` runs, then a dated report is written listing each surface per viewport with pass or violations, the veraPDF status, the founder's checks as open, and the readiness record names that file in R13.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- Layers: blind hunter and edge case hunter (the brief sets two reviewers; verification-gap and intent-alignment skipped), plus the independent accessibility check (keyboard, focus, axe across every Role, Playwright CLI), which found no defect.
- verdicts: 31 findings — high 0, medium 11, low 15, false 2, maybe-false 3
- findings:
  - `medium` `patch` [blind] Committed report stale against its generator (5 columns, 6 viewports) — report regenerated last; the "agree" test now checks the committed report's columns and viewport count against VIEWPORTS.
  - `medium` `patch` [blind] Scan can pass a redirected page (expired session → «Logg inn») — scan records an error when the final path differs from the surface's; it also waits for no Skjelett.
  - `medium` `patch` [blind] Runner ignores the scan's outcome and can reuse stale results — runner clears the results dir before a scan, fails when the scan cannot start; the report names viewports with no results.
  - `low` `patch` [blind] «pass» overstates WCAG coverage — Surfaces section now says pass = no axe violation and no sideways scroll, tools test only part of WCAG.
  - `medium` `patch` [blind] Scan covers only default states, not disclosed — `scanLimits` in the inputs are rendered under Surfaces; the statement's «Ikke kontrollert ennå» names error states and confirmation steps; open-Debrief scanning deferred.
  - `low` `patch` [blind] Statement copy claims more than shown («med tastatur alene») — copy now says a scripted keyboard walk found no faults; screen reader and keyboard by a person listed as not done; «Kjente avvik» shows none found.
  - `low` `patch` [blind] Statement lacks assessment method/date and an alternative route — added «Vurderingen er vår egen, gjort 22. november 2026» and the alternative-format sentence; response-time commitment and legal wording left to the founder (copy review, Issue #31).
  - `medium` `defer` [blind] Placeholder address can ship — R14 open; deferred to 15.14's preflight.
  - `low` `patch` [blind] Footer "every page" vs exclusions — readiness text names the two exclusions; tab-last check kept (Shift+Tab from the footer reaches the page's last link).
  - `low` `patch` [blind] Build identification ignores untracked files; "29 screens" vs 24 — `git status --porcelain` without the untracked filter; summary corrected to 24 screens.
  - `medium` `patch` [blind] veraPDF ignores failedJobs — a batch with failedJobs > 0 is not compliant; attribute order no longer matters; tested.
  - `medium` `patch` [blind] CI upload lost on scan failure; R13/R14 without issues — upload step `if: always()`, `if-no-files-found: ignore`. Issues not created: the brief forbids editing GitHub issues in this run; reported to the lead.
  - `low` `patch` [blind] Script nits (escape shadowing, backticks, 200 % simulation) — helper renamed `md`, backticks replaced in code spans (tested), report states how 200 % text is simulated.
  - `medium` `patch` [edge] CI upload has no condition — same fix as the CI row above.
  - `medium` `patch` [edge] Committed report stale — same fix as the stale-report row above.
  - `low` `patch` [edge] Spec names `--out`, not parsed — `--out <dir>` writes a trial report and leaves the readiness record alone.
  - `medium` `patch` [edge] Redirect recorded as pass — same fix as the redirect row above.
  - `maybe-false` `patch` [edge] axe may run on a skeleton state — would be settled by a loaded marker; cheap guard added (wait for no `[data-skeleton]`).
  - `low` `patch` [edge] class_id undefined → `/klasser/undefined` — the scan asserts the read is 200 and `class_id` is set.
  - `low` `patch` [edge] Setup throws → no file for that viewport — the report names viewports with no results and no longer says "None … at any viewport".
  - `medium` `patch` [edge] "None" while cells unchecked — summary distinguishes unchecked checks; tested.
  - `low` `patch` [edge] Empty results files → empty report — readResults refuses files with no surface; tested.
  - `low` `patch` [edge] Truncated JSON → stack trace — parse errors become ReportError; tested.
  - `low` `patch` [edge] `--from` without a value — `argument()` refuses a flag without its value; tested.
  - `low` `patch` [edge] spawnSync error ignored — runner fails with the error.
  - `low` `patch` [edge] `--verapdf` without a value silently ignored — refused by `argument()`; tested.
  - `false` `reject` [edge] veraPDF failedJobs — duplicate of the blind row, already patched there (no separate defect).
  - `false` `reject` [edge] untracked files hide a dirty tree — duplicate of the build-identification row, patched there.
  - `maybe-false` `patch` [edge] Backticks in selectors — duplicate claim of the script-nits row; patched there.
  - `maybe-false` `patch` [edge] `/delt-skjerm` test passes vacuously — the exclusion is by address; the test now asserts the address before counting the footer.
  - `low` `patch` [edge] "agree" test checks existence only — same fix as the stale-report row.

## Design Notes

- Implemented by the builder in its own context, not by a step-03 sub-agent: the lead's brief for this run says "Do the implementation yourself, in your own context".

- The independent review agent (no human in the loop, runbook) does the keyboard, focus and axe checks with Playwright CLI across every Role's main screens; its findings go into `manual-checks.json` → `independentReview` and so into the report. It does not close the founder's rows: a screen reader check cannot be done by an agent.
- Contact address: placeholder `tilgjengelighet@example.com` (decision for the founder, R14 open).
- The scan uses real data (one rule-based live game) rather than stand-ins, so the report describes what a User sees; the Debrief is scanned in the state the running game gives (not yet open), which the report notes.

## Verification

**Commands:**
- `cd frontend && npx vitest run scripts/conformance-report.test.mjs` -- pass
- `cd frontend && npm run typecheck && npm run check:copy && npm run lint:colours` -- pass
- `cd frontend && npx playwright test e2e/accessibility-statement.spec.ts e2e/landing.spec.ts` -- pass
- `cd frontend && npm run conformance` -- writes `docs/accessibility/conformance-report-2026-11-22.md`

## Auto Run Result

Status: done

**Summary.** The accessibility statement is public at `/tilgjengelighet` (copy `nb.accessibility`), linked from a site-wide footer (a `contentinfo` landmark with one Lenke) under every page, the Landing's included, except the print route and `/delt-skjerm`. `npm run conformance` (frontend) runs a scan of 24 surfaces of every Role with fresh data at 320, 360, 1440 px, 400 % zoom, and 200 % text at 1280 and 320 px (axe WCAG 2.1 A/AA and the sideways-scroll check), then writes `docs/accessibility/conformance-report-<date>.md` and points readiness item R13 at it. The committed report (2026-11-22): 144 checks, 144 pass; veraPDF not run (no Student report PDF on this branch); four founder checks (two screen readers, keyboard by a person, zoom by eye) open; the independent review in the founder's place recorded. CI runs the scan and keeps its results as an artifact.

**Independent accessibility check (in place of the founder).** A sonnet review agent walked 24 screens (public, Student play/Hjem/Regler/Debrief/Replay, Lecturer Lærerhjem/Klasse/Klasseøkt/Oversikt/Spillinnsikt, seven Admin pages) with the Playwright CLI 0.1.24 (Tab, Shift+Tab, Enter, Space, Escape) and axe at 320 and 1440 px: no defect, no axe violation, focus visible everywhere, footer link the last tab stop. Its observations (no Escape on inline panels, no skip link, 18 px Matrisevegg cells, 4.51:1 lowest SVG text contrast) are in the report; none is a WCAG 2.1 AA failure. The scan's new 320 px + 200 % text case then found three pages that scrolled sideways (Oversikt's inline «Visning» segments, Brukere's long names in cells and buttons, KI-kostnad's «Testmåling uten tall»); fixed by letting them wrap (`segmented-choice.tsx` inline variant, `user-list.tsx` `Cell` and row buttons). The footer link itself first pushed the play screen sideways at 320 px + 200 % text (caught by `graph-over-table.spec.ts`); it now breaks.

**Files.**
- `frontend/src/copy/nb.ts` — `accessibility` section (statement, footer link, placeholder contact address).
- `frontend/src/components/site-footer.tsx`, `frontend/src/app/layout.tsx` — the footer.
- `frontend/src/app/tilgjengelighet/page.tsx`, `frontend/src/modules/accessibility/statement.tsx` — the statement page.
- `frontend/src/components/segmented-choice.tsx`, `frontend/src/modules/admin/user-list.tsx` — reflow fixes at 320 px + 200 % text.
- `frontend/e2e/accessibility-statement.spec.ts` — footer and statement, axe and reflow at 320, 1440, 200 % text, 320 + 200 % text.
- `frontend/e2e/conformance.spec.ts` — the scan (skipped unless `CONFORMANCE=1`).
- `frontend/scripts/conformance-report.mjs`, `frontend/scripts/conformance.mjs`, `frontend/scripts/conformance-report.test.mjs`, `frontend/package.json` — the report command and its tests.
- `docs/accessibility/conformance-inputs.json`, `docs/accessibility/conformance-report-2026-11-22.md` — inputs and the dated report.
- `docs/ops/readiness.md` — R13 (report and founder checks), R14 (contact address), how to remake the report.
- `.github/workflows/ci.yml`, `.gitignore` — CI scan step and artifact.

**Review.** Two reviewers (blind, edge case) plus the accessibility check; 31 findings: 28 routed to patch (duplicates share one fix), 1 deferred (the placeholder-address guard, for Story 15.14's preflight), 2 rejected as duplicates (false); scanning the open Debrief was deferred out of the otherwise patched default-state finding. Patched by verdict: medium 10, low 15, maybe-false 3. Follow-up review: not recommended (no high patched; the medium patches are covered by new unit tests and the regenerated report).

**Decisions the founder would otherwise have taken.** Statement route `/tilgjengelighet` and its wording (status «delvis i samsvar» until a screen-reader check is done; no response-time promise); contact route (Students via their Faglærer, others by e-mail to a placeholder `tilgjengelighet@example.com`, R14 open); Uutilsynet named as the complaint route; footer left out on the print route and `/delt-skjerm`; the four founder checks listed; the scan's surfaces and the added 320 px + 200 % text viewport; the report's location `docs/accessibility/`.

**Verification.** `npx vitest run` (89 files, 1158 tests) pass; `npm run typecheck`, `lint:colours`, `check:copy` pass; `next build` passed in the frontend image build; full Playwright suite earlier in the run 638 passed, 6 skipped; after the last changes the touched and play-screen specs (accessibility-statement, landing, homes, admin-users, admin-ai-models, admin-invite, admin-delete, overview, starting-task, game-insight, replay-finish, debrief-chain, graph-over-table, order-field, week-table, class-session-settings) pass; `npm run conformance` 6 viewports pass and wrote the report. No backend change; backend suite run once: 3534 passed. No new personal-data table.

**Residual risks.** The placeholder address ships until R14 is done; the open Debrief and error/confirmation states are outside the scan; no person has used a screen reader on the product.
