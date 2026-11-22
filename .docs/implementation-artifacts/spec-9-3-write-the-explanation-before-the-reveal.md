---
title: 'Story 9.3: Write the Explanation before the reveal'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'e8ae6b97bb2e8f227bdc7e7a0383c9eac3224bcf'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Debrief step 1 shows only its heading: the Student cannot see their own net inventory over the game, cannot write or send an Explanation, and nothing in the API keeps the reveal (step 2 on, demand, other Seats) behind a saved Explanation.

**Approach:** `modules/debrief` gets `debrief_explanations` (one row per Student per Class session, immutable), `commands.save_explanation` (locks the Debrief row, records `progress` `explanation` in the same transaction, emits `debrief:<id>`), a read of the Student's own Netto lager per Uke from the Decision log, one gate function `require_explanation` that every later step endpoint goes through (403 `explanation_required`), and a staff read through a new Class-scoped `platform/authz` policy. The web app's step 1 draws «Ditt netto lager, hele spillet» with «Vis som tabell», the Tekstfelt «Hvorfor svingte lageret ditt?» with a draft in `lib/drafts.ts`, and «Send Forklaring».

## Boundaries & Constraints

**Always:**
- The game is found only through `games.service.student_game`; Netto lager per Uke comes from `games.service.decision_log` rows of the Student's own Role only (`state_seen.net_inventory`), one point per logged Uke, ordered by Uke. No demand, incoming order or other Role's number in any answer before the Explanation (FR-14, FR-41).
- Every new Debrief route first applies the 9.2 availability and ownership rule (`service.mine`), so `debrief_not_open`, `debrief_held` and `forbidden` answer as before, envelope only.
- Explanation stored once, as typed (no trimming), with `length` (characters) and `saved_at` (database clock), keyed `(user_id, class_session_id)`; insert ON CONFLICT DO NOTHING → `409 explanation_exists`. Text required non-blank, at most 5000 characters (422 `validation_error`).
- `progress.record_step(user, class_session, explanation, at, within=session)` in the save's transaction; registry `debrief.save_explanation: {debrief, session, user}`.
- Gate: `service.require_explanation` reads `progress.has_step(explanation)`; `GET /api/debriefs/{id}/steps/{step}` (2–5) is the step endpoint Stories 9.4–9.9 fill, and answers `403 explanation_required` without it.
- Staff read `GET /api/class-sessions/{session_id}/students/{user_id}/explanation`: policy `explanations.read` (account roles Lecturer, Assistant; Class staff roles owner, assistant), checked with `authz.can` on the Class; Admin without a staff role and every Student refused `403 forbidden`.
- UI copy in `nb.debriefEntry` (pre-reveal rules; draft copy marked `[ASSUMPTION]`); the chart is hand-made SVG in `frontend/src/components/charts` (AD-18), fixed size from the caller, `<title>`, `aria-hidden` with the table as its alternative.
- Migration `0103` (down_revision `0102`).

**Never:** no step 2+ content, no step-pointer move, no Group-debrief locked-reveal line (9.11); no edit or delete of an Explanation; no send without a press on «Send Forklaring»; no import of `modules/players` or of `games` other than `games.service`; no change to `games`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Own net inventory | open Debrief, no Explanation | 200 `{weeks:[{week, net_inventory}]}` own Role, every logged Uke | — |
| First send | `POST …/explanation {text}` | 201 `{text, length, saved_at}`; one row; `progress` explanation; `debrief`, `session`, `user` events | — |
| Second send | Explanation exists | 409 `explanation_exists`, row unchanged | envelope only |
| Blank / too long | `"  "` or 5001 chars | 422 `validation_error`, nothing stored | — |
| Own read | `GET …/explanation` | 200 `{explanation: {…} \| null}` | — |
| Later step, no Explanation | `GET …/steps/2..5` | 403 `explanation_required`, envelope only | — |
| Later step, with Explanation | same | 200 `{debrief_id, step}` | — |
| Not available / other game | any new route | 403 `debrief_not_open` / `debrief_held` / `forbidden` | envelope only |
| Staff read | Assistant lecturer of the Class | 200 the Explanation; none yet → 404 `not_found` | — |
| Staff read refused | other Student, unattached Admin, unattached Lecturer | 403 `forbidden` | — |
| UI empty field | press «Send Forklaring» | button `aria-disabled`, reason beside the field, nothing sent | — |
| UI failed save | 5xx / network | «Det ble ikke lagret. Prøv igjen.», text kept, draft kept | button stays active |

</intent-contract>

## Code Map

- `backend/app/modules/debrief/{commands.py:45 _locked, models.py, service.py:72 mine, routes.py, schemas.py, README.md}` -- 9.2 module to extend; `mine` gives the ownership+availability check to reuse.
- `backend/app/modules/games/service.py:116` -- exports `decision_log(game_id)` (rows with `role`, `week`, `state_seen: SeatState`); `student_game:235`.
- `backend/app/modules/progress/service.py:33` -- `record_step(..., within=)`, `has_step`; `Step.EXPLANATION` exists.
- `backend/app/platform/authz.py:80,133,148` -- `POLICIES`, `CLASS_STAFF_ROLES`, `can(user, action, class)`.
- `backend/app/modules/sessions/service.py:646 _class_for`, `:1266 debrief_session_of` -- add public `class_staff_may(user, session_id, action)` (session row → Class → `authz.can`).
- `backend/app/platform/events/registry.py:100` -- registry entries; `tests/debrief/test_debrief.py` registry style.
- `backend/tests/debrief/test_debrief.py` -- `confirmed`, `sweep.run(LOCKED)`, `start`, `task_done`, `call`, `refused`, `emitted`; `tests/games/helpers.py:41 play_week` plays one Uke cheaply.
- `backend/tests/sessions/...` staff: `tests/classes/test_staff` (Assistant lecturer setup helpers) for the staff read.
- `frontend/src/modules/debrief/{api.ts,debrief-page.tsx}` -- step 1 renders here.
- `frontend/src/components/chain-cost-chart.tsx` -- pattern for chart + «Vis som tabell» toggle (`LINK_BUTTON`, `ScrollRegion`, `useBoxSize`).
- `frontend/src/components/charts/{net-graph.tsx,scales.ts:netDomain,netTicks,palette.ts}` -- fills/colours and tick rules to reuse.
- `frontend/src/components/{text-area-field.tsx,button.tsx,action-error.tsx}`, `lib/drafts.ts`, `lib/api/mutation.ts useAction`.
- `frontend/e2e/{debrief-open.spec.ts,support/live-game.ts,support/classes.ts}` -- stubs, `liveClassGame` (2-Uke game), `expectAccessible`, 200 % text pattern in `student-home.spec.ts:92`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0103_debrief_explanations.py` -- `debrief_explanations(user_id FK users CASCADE, class_session_id FK CASCADE, game_id FK games CASCADE, text TEXT, length INT, saved_at timestamptz)`, PK `(user_id, class_session_id)`, check `length = char_length(text) AND length BETWEEN 1 AND 5000`.
- `backend/app/modules/debrief/{models,commands,service,schemas,routes}.py`, `README.md` -- table; `save_explanation`; `own_net_inventory`, `own_explanation`, `save_mine`, `require_explanation`, `step`, `staff_explanation`; routes `GET /api/debriefs/{id}/net-inventory` (`getMyNetInventory`), `GET`/`POST /api/debriefs/{id}/explanation` (`getMyExplanation`/`sendMyExplanation`), `GET /api/debriefs/{id}/steps/{step}` (`getDebriefStep`), `GET /api/class-sessions/{sid}/students/{uid}/explanation` (`getStudentExplanation`).
- `backend/app/platform/authz.py`, `platform/events/registry.py`, `modules/sessions/service.py` -- policy, registry entry, `class_staff_may`.
- `backend/tests/debrief/test_explanation.py` -- the matrix, the every-endpoint-without-Explanation sweep (asserts no `demand`, `incoming_order` or other Role in any body), staff read, events, progress; `test_migrations.py` if it lists tables.
- `frontend/src/components/charts/net-over-game.tsx` -- whole-game Netto lager SVG (true zero, lager/restordre fills, net ticks, Uke labels).
- `frontend/src/components/net-over-game-chart.tsx` -- titled chart with «Vis som tabell» (Uke, Netto lager) toggle.
- `frontend/src/modules/debrief/{api.ts,debrief-page.tsx,explanation-step.tsx,debrief.test.ts}`, `copy/nb.ts`, regenerated `openapi.json`/`schema.ts` -- step 1 UI, draft, send, sent state.
- `frontend/e2e/debrief-explanation.spec.ts` -- stubbed step 1 at 320/360/1440 + 360 at 200 % text with axe and keyboard send; failed save; live 2-Uke game: draft restored on reload, send, reload shows sent, step 2 gate via API.

**Acceptance Criteria:**
- Given a Student on step 1, when it shows, then «Skriv Forklaringen først», «Ditt netto lager, hele spillet» (own Seat only, no demand), «Vis som tabell» giving Uke/Netto lager, «Hvorfor svingte lageret ditt?» and «Send Forklaring» are shown.
- Given typed text, when the page reloads, then the text is restored and nothing was sent.
- Given a sent Explanation, when the page reloads, then the text shows read-only as sent and no field or send button is offered.
- Given step 1 at 320, 360 (also 200 % text) and 1440 px, when axe runs, then no violations, no page-level horizontal scroll, and the Explanation can be typed and sent by keyboard alone.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), following the orchestrator's two-reviewer rule; verification-gap and intent-alignment were skipped for the same reason. Both reviewers' hand-back failed; their findings were read from the scratchpad files they wrote (`review-blind-9-3.md`, `review-edge-9-3.md`).
- verdicts: 21 findings — high 0, medium 2, low 16, false 3, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) Text with a NUL character passes the judge and fails in Postgres (500, not 422). Real, but a browser textarea does not produce NUL; the fix is a new guard for a case Students do not meet.
  - `[low]` `[reject]` (blind 2) `ExplanationIn.text` has no schema `max_length`; the 5000 limit is written in model, migration and web app. Request size is bounded by the proxy; the constants are pinned by the migration test and the e2e. Cosmetic duplication.
  - `[low]` `[reject]` (blind 3) The field's `maxLength` counts UTF-16 units, the api characters, so a 5000-unit paste of emoji is cut by the browser. The browser cap is always at or under the api limit, so `too_long` never reaches the generic message; silent truncation needs a 5000-character paste.
  - `[low]` `[reject]` (blind 4) The gate is a convention later routes must call; it reads `progress` rather than `debrief_explanations`. `save_explanation` is the only writer of both and writes them in one transaction; later stories add their routes behind `require_explanation` (README). A route enumeration test adds machinery for routes that do not exist yet.
  - `[low]` `[reject]` (blind 5) Concurrency and rollback are untested; availability is judged before the lock. ON CONFLICT and the single transaction make two sends one row and one 409; the availability window is the same as Story 9.2's `open` and only reaches a game that is finished.
  - `[low]` `[patch]` (blind 6) `tests/debrief/test_explanation.py` held double-encoded UTF-8 (a PowerShell rewrite), so the «as typed» fixture had no Norwegian letters. Re-saved with «», å; the single long test is deliberate (one Class-session setup, about 3 s).
  - `[medium]` `[patch]` (blind 7) A failed read of the net inventory hid the chart silently, and a failed read of the own Explanation showed the empty form. Step 1 now shows «Dette steget kunne ikke hentes.» with «Prøv igjen» and no form while the Explanation cannot be read; e2e «a failed read of the step says so and can be tried again».
  - `[low]` `[patch]` (blind 8) The 409 `explanation_exists` path had no test. E2e «sent already from another device» added; the line now shows beside the form until the stored one replaces it.
  - `[low]` `[reject]` (blind 9) «Vis som tabell»/«Vis som graf» changes its label and sets `aria-expanded`; the status line mounts with its text; a lone Uke label is centred at the plot's left. The toggle is the shared pattern of `chain-cost-chart` (axe passes); focus moves to the sent heading, which reads the result; a one-label axis needs a game of one Uke at a tiny width.
  - `[false]` `[reject]` (blind 10) Dead end after sending. The spec's design decision: the step pointer and step 2 come with Stories 9.4/9.11; the endpoint `steps/{n}` exists for them.
  - `[low]` `[reject]` (blind 11) Spec drift (hint wording, trigger not named in the task), long comment line, no audit of staff reads, no test of a staff member of another Class. The fixes edit this build's spec or add an audit the story does not ask for; another Class's Lecturer (`OTHER`) is in the test.
  - `[low]` `[reject]` (blind 12) No index on `debrief_explanations.game_id`, no DB tie of `game_id` to the Student, trigger blocks UPDATE only, undeclared 422 for `steps/1`. The table is small; `game_id` is written only from `student_game`; DELETE and TRUNCATE are administrative.
  - `[low]` `[reject]` (edge 1) NUL or lone surrogate gives 500. Same as blind 1.
  - `[false]` `[reject]` (edge 2) The chart includes Uker an AI held the Seat. The story's chart is «hele spillet» of the Student's Seat; it is meant to show every Uke.
  - `[false]` `[reject]` (edge 3) A finished game with no logged Uker. A finished game has an Order for every Seat in every Uke (`games.finish`), so the list is never empty for an open Debrief.
  - `[medium]` `[patch]` (edge 4) A failed net-inventory read leaves the chart absent with no retry. Same root cause and fix as blind 7.
  - `[low]` `[patch]` (edge 5) After a 409, a failed re-read hid the error and kept the form. Same fix as blind 7 and 8: the 409 line shows, and a failed read shows the step error.
  - `[low]` `[reject]` (edge 6) Silent truncation by `maxLength` on a long paste. Same as blind 3.
  - `[low]` `[reject]` (edge 7) `hasText` (JS trim) and Python `strip` differ on U+001C–U+001F and U+0085. Text of only those characters is not typed in practice.
  - `[low]` `[patch]` (edge 8) Mojibake in the test file. Same fix as blind 6.
  - `[low]` `[reject]` (edge 9) `saved_at = now()` is the transaction start, before a lock wait. The wait is milliseconds under contention; the order of one Student's single save is not affected.
  - `[low]` `[reject]` (edge 10) The staff read applies no availability rule. Intended: staff read an Explanation once it exists; the availability rule is the Student's (spec boundary on student routes).

## Design Notes

Decisions taken for the founder: the step data are separate endpoints (net inventory, Explanation, `steps/{n}`) so each later story adds content to `steps/{n}` behind the one gate; with an Explanation, `steps/{n}` answers only its number until 9.4+. The chart plots `state_seen.net_inventory` of each logged Uke (what the Student saw when ordering). Explanations are limited to 5000 characters and stored unchanged; the length counts characters. After sending, step 1 shows the Explanation read-only with a sent line; the step pointer does not move (step content and moving on come with 9.4/9.11). The mockup's coloured week strip under the chart is left out: it repeats the line in colour only. The staff read answers 404 `not_found` when the Student has not written one.

Draft copy (`[ASSUMPTION]`): reason «Skriv Forklaringen før du sender.»; hint «Bare du og de som underviser Klassen, kan lese Forklaringen.»; sent «Forklaringen er sendt og lagret slik du skrev den.»; «Din Forklaring»; table caption and SVG title.

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief tests/test_migrations.py tests/test_imports.py tests/platform/test_authz.py` -- pass
- full `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-explanation`, `debrief-open`, `homes`, play-screen specs on the lane stack -- pass

## Auto Run Result

Status: done

**Summary.** Debrief step 1 works. `modules/debrief` stores the Explanation in `debrief_explanations` (one per Student per Class session, as typed, with its length in characters and the database time, never changed: a trigger refuses updates). `commands.save_explanation` locks the Debrief row, inserts once (409 `explanation_exists` after that) and records the `explanation` step in the same transaction. The Student reads their own Netto lager per logged Uke from the Decision log (own Role only, no demand), reads their own Explanation, and sends it (422 `validation_error` for white space only or over 5000 characters). `service.require_explanation` is the one gate; `GET /api/debriefs/{id}/steps/{2..5}` answers 403 `explanation_required` until the Explanation is saved. The Class's owners and Assistant lecturers read a Student's Explanation through the new `explanations.read` policy; another Student, an Admin without a staff role and another Class's Lecturer are refused. The web app's step 1 draws «Ditt netto lager, hele spillet» (new hand-made SVG in the chart module) with «Vis som tabell» (Uke, Netto lager), «Hvorfor svingte lageret ditt?» with a draft kept on the device, «Send Forklaring» (`aria-disabled` with its reason while empty), the failure line with the text kept, and after sending the Explanation read-only.

**Files.**
- `backend/migrations/versions/0103_debrief_explanations.py`: the table, its length check and the immutability trigger.
- `backend/app/modules/debrief/{models,commands,service,schemas,routes}.py`, `README.md`: table, `save_explanation`, step-1 reads, the gate, `steps/{n}`, the staff read.
- `backend/app/modules/sessions/service.py`: `class_staff_may` (Class-scoped check for other modules).
- `backend/app/platform/authz.py`, `platform/events/registry.py`, `migrations/env.py`: `explanations.read`, `debrief.save_explanation`.
- `backend/tests/debrief/test_explanation.py` (new), `tests/test_migrations.py` (0103 up and down).
- `frontend/src/components/charts/net-over-game.tsx`, `components/net-over-game-chart.tsx` (new): the chart and its table toggle; `charts.test.tsx`.
- `frontend/src/modules/debrief/{api.ts,explanation-step.tsx,debrief-page.tsx,debrief.test.ts}`, `copy/nb.ts` (`debriefEntry.explanation`), regenerated `openapi.json`/`schema.ts`.
- `frontend/e2e/debrief-explanation.spec.ts` (new).

**Deviations and decisions.** The builder implemented in its own context, as the orchestrator instructed, instead of a step-03 subagent, and ran two review layers (orchestrator rule). Decisions for the founder (also in Design Notes): separate step-1 endpoints and one `steps/{n}` endpoint behind one gate, which answers only the step number until Stories 9.4+; the chart plots `state_seen.net_inventory` of every logged Uke of the Seat; a 5000-character limit counted in characters; no step-pointer move and no next-step link after sending (9.4/9.11); the mockup's coloured week strip left out (it repeats the line in colour only); the staff read answers 404 `not_found` when none is sent; an immutability trigger on the table; draft copy marked `[ASSUMPTION]` (hint, reason, sent, exists, load failure, table caption, SVG title). The blank and too-long refusals use the code `validation_error` with `fields.text` = `blank`/`too_long` (the generic body-shape error stays `invalid_request`).

**Review.** 21 findings (high 0, medium 2, low 16, false 3): 3 entries patched (one medium: step-1 read failures now say so with «Prøv igjen» and never show the form in place of an unreadable Explanation; two low: the 409 path shows its line and has an e2e, and the test file's double-encoded UTF-8 was repaired); nothing deferred; 13 rejected with reasons in the triage log. followup_review_recommended: false (no high patched, one medium entry).

**Verification.**
- Full backend suite: 2861 passed, 4 skipped in 72 s; `ruff check` and `ruff format --check` clean; the migration walk covers 0103 up and down. After the review patch, `tests/debrief` again: 8 passed.
- Frontend: typecheck, Vitest (55 files, 725 tests), `check:copy`, `lint:colours` and `next build` pass.
- Playwright on the lane stack (port 8081), after the review patch: `debrief-explanation` (step 1 at 320, 360, 360 with 200 % text and 1440 px with axe and a send by keyboard; failed send; draft over reload; 409; failed read; a live two-Uke game: draft, send, reload, `steps/2` 403 then 200, second send 409), `debrief-open`, `homes`, `game-end`, `student-home`, `order-confirm`, `week-advance`: 66 passed.
- Screens checked by eye at 360, 360 with 200 % text and 1440 px: chart, table toggle, field, reason, sent state.

Tests over 1 s: `test_step_one_the_one_send_the_gate_and_the_readers` (about 3 s): a Class session with two Class games, a lock through the api and three played Uker, set up once for every assertion of the story (the two tests were merged to pay the setup once).

**Residual risks.** Draft copy awaits the founder's copy review (Issue #31). The gate holds only if Stories 9.4–9.9 call `require_explanation` on every route they add (documented in the README and `steps/{n}`). After sending, step 1 has no next action until Story 9.4.
