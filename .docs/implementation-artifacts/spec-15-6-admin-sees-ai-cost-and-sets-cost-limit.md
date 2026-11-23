---
title: 'Story 15.6: The Admin sees AI cost and sets the cost limit'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'fa64504ca6fd6398b21f3c44c9738434ae4f2ac6'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Admin cannot see what each Class session spends on AI, cannot change a Class session's cost limit, and nobody is told when a Class session's LLM players switch to Rule-based players at the limit (Epic 2 only records `players_exhausted_at`); when the reserve is spent too, the AI assessment just fails (FR-69).

**Approach:** A cost page in the «KI-kostnad» area (`/admin/ki-kostnad/klasseokter`, linked from `/admin/ki-kostnad`) lists every saved Class session's AI cost against its budget row, the simulation budgets apart; a Class session page (`/admin/ki-kostnad/klasseokter/<id>`) shows its cost per Game and per day (charts with «Vis som tabell»), the limit/reserve/spent, the limit form, the limit-reached state and, when the reserve is spent too, the two consequence-labelled actions (raise the limit → `assessment.service.resume_for_session`; stop → `stop_for_session`). A sweep due action tells each owner of the Class once (digest notice, dedupe per Class session and owner), and the Klasseøkt shows the switch.

## Boundaries & Constraints

**Always:**
- Sums only in `app/ai` over `llm_call` (every outcome), unrounded `NUMERIC(18,8)`; budget state only through `ai.budget` (`state`, new `set_limit`, new `class_session_states`). New `ai.calls.session_costs(ids)` (total USD and calls per Class session scope) and `ai.calls.session_breakdown(id)` (per Game: `caller_ref` `game` or `game_id`, else one «Uten spill» line for the Debrief, follow-ups and the AI assessment; per Europe/Oslo day via `oslo_day`/`OSLO` as 15.7), plus `ai.calls.dearest_reserve_call(id)`: the largest `cost_usd` of one non-player (`purpose <> 'player_order'`) attempt on the scope.
- Reserve used up (derived, nothing stored): `players_exhausted_at` set and `limit − spent − reserved` is ≤ 0 or below the dearest reserve call so far.
- Targets (C-3): per Game 0.10 USD, per Student 0.50 USD, constants in `ops`. Per Game = each Class game's sum; the session's «per Spill» = Class-game calls ÷ Class games; «per Student» = session total ÷ distinct Students holding a Seat in its Class games (`games.service.class_games_of`), none when 0. A figure above its target gets the text mark «Over målet».
- `PUT /api/admin/ai/class-sessions/{id}/budget {limit_usd}` (policy `ai_models.manage`): `ai.budget.set_limit` writes only `limit_usd` on the one row (created with the defaults when missing), refuses `limit_below_spent` (limit < spent + reserved) and `reserve_above_limit` (422 with `fields.limit_usd`), 404 for an unknown session; audits `ai_budget.limit_set` (target `class_session_id`, change `{limit_usd, previous_limit_usd}`); same limit = no-op, no audit. A raise while the reserve was used up or the assessment is stopped also calls `resume_for_session(id, actor)` in the same transaction (its own audit row).
- `POST /api/admin/ai/class-sessions/{id}/assessment/stop` calls `stop_for_session(id, actor)` (its own audit row); allowed only while the reserve is used up, else 409 `reserve_not_used_up`.
- `GET /api/admin/ai/costs` (list) and `GET /api/admin/ai/costs/{id}` (one session) answer decimal strings with eight places; the session answer carries `players_exhausted_at`, `reserve_used_up`, `assessment_stopped_at`.
- Due action `ops.cost_limit_notice` (new `ops/cost_limit.py`, before the deadline reminders): finds Class sessions with `players_exhausted_at` set and an owner without notice key `ai_cost_limit:<session>:<owner>`; enqueues kind `ai_cost_limit` (registered `DIGEST` in `messaging.delivery.KINDS`, templates `ai_cost_limit.{txt,html}.j2`: Class, Klasseøkt number, time, link to the Klasseøkt); the resolver returns None when the recipient is no longer an owner. A second sweep sends nothing.
- `ClassSessionOut.cost_limit_reached_at` (from `ai.budget.state`); the Klasseøkt shows «Kostnadsgrensen for KI er nådd. LLM-spillerne er byttet til regelbaserte for resten av Klasseøkten.» when set.
- Copy in `nb.ts`, `[ASSUMPTION] Story 15.6`; the limit-reached line reads «Grensen er nådd for class-of-1994 · Klasseøkt 1. LLM-spillerne er byttet til regelbaserte.» with the time; reserve used up adds that the Debrief now runs from code and the AI assessment waits for the Admin. One primary button per page (the limit save); the stop action is secondary; each action's consequence stands above its button. Charts reuse `ChartBlock` (`modules/ops/ops-charts.tsx`).

**Never:**
- No code outside `app/ai` names `llm_call` or `ai_budgets`; `app/ai` imports no module; nothing imports `ops`.
- No new retry rule, no rebuild of the Rule-based switch, no change of `stop_for_session`/`resume_for_session`; no reset of `players_exhausted_at` by a raise.
- No Student name or text anywhere on these pages, answers or mails.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List | two sessions with calls, one evaluation budget | sessions with limit/reserve/spent/total/per Game/per Student; simulations apart | — |
| Raise | limit 15 → 20 | row limit 20, reserve and spent unchanged, audit row | — |
| Below spent | spent 3, limit 2 | nothing changed | 422 `limit_below_spent` |
| Reserve used up + raise | exhausted, remaining 0, assessment failed | limit raised, assessment resumed (`incomplete`, job deferred), two audit rows | — |
| Stop | reserve used up | `stopped_at` set, audit | 409 `reserve_not_used_up` when not used up |
| Exhausted notice | `players_exhausted_at` set, two owners | one `ai_cost_limit` notice each; second sweep none | — |
| Not Admin | Lecturer GET/PUT | 403 | — |

</intent-contract>

## Code Map

- `backend/app/ai/budget.py:114` `set_budget` (resets reserve: do not use for a limit change), `:182` `state`, `_amount`, `BudgetRefused`; add `set_limit`, `class_session_states`.
- `backend/app/ai/calls.py:78` `costs` (per Game by `caller_ref['game']`, UTC days), `:116` `oslo_day`, `:157` `day_spend` pattern, `:333` `PLAYER_PURPOSE`.
- `backend/app/modules/ops/{ai_models.py,ai_schemas.py,ai_routes.py}` -- route/service/refusal pattern (`Refused`, `_refused`, `Manager` = `ai_models.manage`); `spend_alert.py` -- due action pattern; `ops/sweep.py` `DUE_ACTIONS`.
- `backend/app/modules/sessions/service.py:6442` `model_settings` (session names), `:1074` `get_session` (add `cost_limit_reached_at`), `:2051` `assessment_failed_mail_context` (mail-context pattern), `:5016` `classes.owners_of`.
- `backend/app/modules/assessment/service.py:1264` `stop_for_session`, `:1303` `resume_for_session`, `:205` stopped read (`stopped_at` of the switch).
- `backend/app/modules/games/service.py:469` `class_games_of` (Game numbers and Seat occupants).
- `backend/app/modules/messaging/delivery.py:232,298` kinds and `KINDS`; `platform/email/templates/kinds/assessment_failed.*.j2`.
- `frontend/src/modules/admin/{ai-models-page.tsx,api.ts,daily-spend.ts}`, `modules/ops/ops-charts.tsx` `ChartBlock`, `modules/sessions/class-session-page.tsx:425` (lock-refused line), `modules/identity/homes.ts:36`, `app/(app)/admin/ki-kostnad/page.tsx`, `copy/nb.ts:2515` `aiCost`, `lib/number-format.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/ai/{budget,calls}.py` -- `set_limit`, `class_session_states`, `session_costs`, `session_breakdown`, `dearest_reserve_call`.
- `backend/app/modules/ops/{ai_cost.py,cost_limit.py,ai_schemas.py,ai_routes.py,sweep.py}` -- list, session, limit, stop; due action.
- `backend/app/modules/sessions/{schemas,service}.py` -- `cost_limit_reached_at`; `cost_limit_mail_context`; owners reader.
- `backend/app/modules/messaging/delivery.py`, templates `ai_cost_limit.{txt,html}.j2` -- digest kind.
- `backend/tests/ops/test_ai_cost.py` -- every matrix row, sums unrounded, per-Game/day lines, marks, notice once, mail content, 403s.
- `frontend/src/copy/nb.ts`, `src/modules/admin/{ai-cost-page.tsx,ai-cost-session-page.tsx,ai-cost.ts(+test),api.ts}`, routes under `app/(app)/admin/ki-kostnad/klasseokter/`, link on «KI-kostnad», `class-session-page.tsx` line, `src/lib/api/*` (regenerated).
- `frontend/e2e/admin-ai-cost.spec.ts` -- list, session page with charts and «Vis som tabell», limit save, 403 page for a Lecturer; axe at 320/1440.

**Acceptance Criteria:**
- Given a Class session with spend, when the Admin opens its cost page, then per Game and per day charts each have «Vis som tabell», and the limit, reserve and spent show.
- Given `players_exhausted_at` set, when the Admin opens the session, then «Grensen er nådd for …» shows with the time, and the Lecturer's Klasseøkt shows the switch line.
- Given the reserve is used up, when the Admin opens the session, then both actions show their consequence above the button.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment (sonnet, as the lead's brief asks).
- verdicts: 42 findings — high 0, medium 7, low 23, false 12, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: the 15.7 «Immediate» comment sat above the new digest entry in `delivery.KINDS` — the digest line moved above it with its own comment.
  - `[low]` `[reject]` Blind: `due_sessions` re-checks every ever-exhausted Class session each minute — two small reads per exhausted session; exhausted sessions are a handful a term, and an archived Class has no owners to tell.
  - `[false]` `[reject]` Blind: the dedupe key is not tied to the exhaustion event — `players_exhausted_at` is set once for the scope's life (Epic 2), so there is no second event; a new owner told of the standing state is «every Lecturer of the Class».
  - `[medium]` `[patch]` Blind: the resume decision is read before the row lock, and resumes even when the raise leaves the reserve used up — `waiting` now comes from the row as `ai.budget.set_limit` locked it (`LimitChange.previous`), and the resume needs room for the next call after the raise; tests for a too-small raise and a raise with room.
  - `[low]` `[reject]` Blind: two first PUTs on a missing row race — `set_budget` upserts on the unique key, both writes set a limit and the default reserve; a missing row is rare (made at save with LLM players or a pin).
  - `[medium]` `[patch]` Blind: a malformed `caller_ref` game id raises and fails the page — `calls._game_id` reads a non-id as no Game; tested.
  - `[low]` `[reject]` Blind: the detail's reads are separate statements and a PUT reads twice — the figures come from settled rows; a disagreement lasts until the next minute's read.
  - `[medium]` `[patch]` Blind: per Game divided all Game-named cost, test Games included, by the Class games — `session_costs` now returns per-Game sums and `ops` counts the Class games only; tested with a test Game.
  - `[low]` `[patch]` Blind: `parseLimit` accepted more than eight decimals — it now refuses what the column cannot hold (Vitest). Upper bound/confirmation: rejected, one press per screen is the product rule.
  - `[low]` `[reject]` Blind: no paging or sort on the list — one row per saved Class session, the same as «Modell per Klasseøkt».
  - `[low]` `[patch]` Blind: the session page asked the api before the guard rendered — the read moved inside the guard; the seeded limit field not resyncing is rejected (the save answers the stored limit).
  - `[low]` `[reject]` Blind: `costText` shows «0,1000 USD» beside «Over målet» for 0.10004 — needs a cost within 0.00005 USD of the target.
  - `[low]` `[reject]` Blind: e2e copies the label and default; test gaps listed — the label comes from copy shared with 15.4; the reserved, `game_id`, malformed-id and no-row gaps are now tested; 401 is the shared guard's.
  - `[false]` `[reject]` Blind: a raise leaves the players rule-based and the banner standing — FR-69 and the AC: the switch is «for the rest of the Class session», and the raise consequence says so.
  - `[medium]` `[patch]` Edge: stale `waiting` under concurrency — same root cause as the Blind resume row.
  - `[medium]` `[patch]` Edge: a raise too small to clear the reserve resumes the assessment — same patch.
  - `[low]` `[reject]` Edge: concurrent first `set_limit` on a missing row — same as the Blind row.
  - `[low]` `[patch]` Edge: re-saving the same limit after spend overran it answered 422 — the same-limit check now comes before the rules.
  - `[low]` `[reject]` Edge: with no reserve call yet a small positive remainder is not «used up» — the dearest call is the only cost measure there is before one is made; the state turns once the first one fails and is logged.
  - `[medium]` `[patch]` Edge: per Game counted non-Class Games — same patch as the Blind row.
  - `[medium]` `[patch]` Edge: malformed game id gives a 500 — same patch.
  - `[low]` `[reject]` Edge: the sweep finder grows without bound — same as the Blind row.
  - `[low]` `[patch]` Edge: over-precise limit gave the generic error — same patch as `parseLimit`.
  - `[low]` `[patch]` Edge: a non-UUID path showed the generic error — 422 now reads as «finnes ikke».
  - `[false]` `[reject]` Edge: a Class session deleted between commit and read answers 404 — Class sessions are never deleted.
  - `[low]` `[patch]` Edge: the comment placement in `delivery.py` — same patch as the Blind row.
  - `[low]` `[patch]` Edge: the Klasseøkt line differed from the spec's wording — it now reads the spec's text followed by «Nådd <tid>.».
  - `[low]` `[patch]` Verification: the mail templates were never rendered — the owner test sends the digest the next morning and asserts both bodies.
  - `[low]` `[patch]` Verification: `reserved_usd` was never above zero — new test with spend and held amounts.
  - `[low]` `[patch]` Verification: the resume on a raise was tested only through a stop — new test for a raise while used up (too small, then enough); attempt states stay 12.4's tests.
  - `[low]` `[patch]` Verification: `game_id` key and line order untested — new test asserts both.
  - `[low]` `[patch]` Verification: the delivery comment — same patch.
  - `[low]` `[reject]` Verification: e2e never clicks stop or raises from the used-up state — the flows are the backend's tests; the stack cannot reach the state without spend.
  - `[false]` `[reject]` Intent: the cost view is a sub-page, not one page — «its cost page» in the KI-kostnad area; the area's page links to it.
  - `[false]` `[reject]` Intent: `day_spend` is not reused — the intent says «can reuse»; a per-session day cut is another sum.
  - `[false]` `[reject]` Intent: the list has no per-day/per-Game splits — the AC asks them «for a chosen Class session».
  - `[false]` `[reject]` Intent: the reserve is not configuration — `AI_BUDGET_RESERVE_USD` (placeholder 1.00, issue #8) is it, read by `set_budget`.
  - `[false]` `[reject]` Intent: the in-product notice is a row and a Klasseøkt line — that is how the product shows notices (Story 5.11's refused lock does the same).
  - `[false]` `[reject]` Intent: owners, not every Lecturer — Assistant lecturers hold no Lecturer role in the Class; recorded in Design Notes.
  - `[false]` `[reject]` Intent: evaluation budgets show limit and spent only — the AC asks them apart from Class sessions, which they are.
  - `[false]` `[reject]` Intent: resume/stop audit rows are 12.4's — the AC: «both actions are audited»; they are, by the commands it calls.
  - `[false]` `[reject]` Intent: the exhausted/used-up states are drawn from a fixture in e2e — the backend tests derive them; the e2e checks the screen.

## Design Notes

The reserve is not tracked on the row; "used up" is derived so nothing new is stored: the next non-player call cannot fit when what is left is below the dearest such call so far. A raise resumes the assessment only when it is waiting (reserve used up or stopped), so a routine raise never resets failed assessments. Owners (not Assistant lecturers) are "every Lecturer of the Class", as the lock-refusal notice of Story 5.11.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/ops/test_ai_cost.py tests/test_imports.py tests/identity/test_personal_data_registry.py tests/messaging -q` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test admin-ai-cost admin-ai-models homes --workers=4` -- expected: pass

## Auto Run Result

Status: done

**Summary.** «KI-kostnad per Klasseøkt» (`/admin/ki-kostnad/klasseokter`, linked from «KI-kostnad») lists every saved Class session's AI cost against its budget row. The list shows limit, total, per Game against 0,10 USD and per Student against 0,50 USD, with the text mark «Over målet». Simulation budgets are listed apart. The total comes from the new `ai.calls.session_costs`, unrounded over every outcome. Per Game counts Class games only; per Student counts the Students who hold a Seat in them.

The Class session page (`/admin/ki-kostnad/klasseokter/<id>`) shows:
- limit, reserve, spent and held, from `ai.budget`;
- per Game and per Europe/Oslo day as bar charts with «Vis som tabell» (`ai.calls.session_breakdown`);
- «Grensen er nådd for … LLM-spillerne er byttet til regelbaserte.» with the time;
- when the reserve is also used up, that the Debrief runs from code and the AI assessment waits.

The limit form is the page's one primary button. It calls `PUT /api/admin/ai/class-sessions/{id}/budget`, which goes through `ai.budget.set_limit` under the row lock. The reserve and spend stay. It refuses 422 `limit_below_spent` and `reserve_above_limit`, and is audited as `ai_budget.limit_set`. A raise while the assessment waits, and that leaves room for the next call, also calls `assessment.service.resume_for_session`. «Stopp KI-vurderingen for Klasseøkten» calls `stop_for_session` (`POST …/assessment/stop`, 409 `reserve_not_used_up` otherwise). Each consequence stands above its button.

The sweep's new due action `ops.cost_limit_notice` tells each owner of the Class once, by a `digest` notice `ai_cost_limit` (key `ai_cost_limit:<session>:<owner>`). The mail names the Class, the Klasseøkt, the time and a link. The Klasseøkt shows «Kostnadsgrensen for KI er nådd. …» from `ClassSessionOut.cost_limit_reached_at`. Admin-only (`ai_models.manage`).

**Decisions taken in place of the founder.**
- «Reserve used up» is derived, not stored: the players' limit is reached and what is left is 0, or less than the dearest non-player call so far.
- A raise resumes the assessment only when it was waiting and the new limit leaves room for the next call. A raise never switches the players back (FR-69: for the rest of the Class session).
- The stop is offered only while the reserve is used up.
- «Every Lecturer of the Class» means its owners and co-owners, not Assistant lecturers, as in Story 5.11.
- Per Game means the Game-named calls of Class games divided by the Class games; calls naming no Game (Debrief, assessment) show as «Uten spill».
- Per Student means the total divided by the Students currently in a Seat.
- Amounts under 1 USD show four decimals.
- The cost pages are separate pages in the «KI-kostnad» area.
- All copy is `[ASSUMPTION] Story 15.6`.

**Files.**
- `backend/app/ai/{budget,calls}.py`: `set_limit`, `LimitChange`, `class_session_states`, `exhausted_class_sessions`, `evaluation_states`, `session_costs`, `session_breakdown`.
- `backend/app/modules/ops/{ai_cost.py,cost_limit.py,ai_routes.py,ai_schemas.py,sweep.py}`: service, due action, routes, schemas.
- `backend/app/modules/sessions/{service,schemas}.py`: `class_session_owners`, `cost_limit_mail_context`, `cost_limit_reached_at`.
- `backend/app/modules/messaging/delivery.py` and `platform/email/templates/kinds/ai_cost_limit.{txt,html}.j2`: the digest kind.
- `backend/tests/ops/test_ai_cost.py`: 9 tests.
- `frontend/src/modules/admin/{ai-cost.ts(+test),ai-cost-page.tsx,ai-cost-session-page.tsx,api.ts,ai-models-page.tsx}`, `modules/ops/ops-charts.tsx` (exports `Bar` and `TableRegion`), `modules/sessions/class-session-page.tsx`, `modules/identity/homes.ts`, `app/(app)/admin/ki-kostnad/klasseokter/**`, `copy/nb.ts`, `lib/api/*` (regenerated).
- `frontend/e2e/admin-ai-cost.spec.ts`.

**Review.**
- Findings: 42 (medium 7, low 23, false 12).
- Patched: 3 medium entries and 10 low entries. The medium ones were the resume decision under the lock with room after the raise, per Game over Class games only, and a malformed Game id.
- Low patches: the same-limit no-op, the limit precision, a 422 path read as «finnes ikke», the guarded fetch, the Klasseøkt wording, the delivery comment, and four test gaps (digest mail rendered, held amount, raise while used up, `game_id` and order).
- Deferred: none.
- Rejected: see the triage log.

Follow-up review recommended: true (two or more medium entries patched). The named risk is the resume decision. It now reads the row `set_limit` locked, but the switch's stop mark is read in the same transaction without its row lock, so a stop and a raise made at the same moment are untested.

**Verification.**
- Backend: full suite 4006 passed. Ruff check and format are clean.
- Frontend: Vitest 1265 passed. `typecheck`, `lint:colours` and `check:copy` pass. Docker build (`next build`) OK.
- Playwright: 57 passed (`admin-ai-cost`, `admin-ai-models`, `homes`, `class-session-lock`, `order-confirm`). Earlier in the run, `admin-operations`, `guided-week`, `chain-band` and `class-session` also passed. Axe ran at 320 and 1440 px.

**Residual risks.** The mock stack spends nothing, so the used-up state on screen is checked from a fixed answer. The backend tests derive it. No new table: no personal-data entry.
