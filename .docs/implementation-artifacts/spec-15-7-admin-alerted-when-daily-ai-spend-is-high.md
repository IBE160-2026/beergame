---
title: 'Story 15.7: The Admin is alerted when daily AI spend is high'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '1d30b541e2d86023e2b5836e4b9f878317630fde'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Epic 2 records AI cost but sends nothing; nobody notices a runaway day of AI spend until the bill (FR-69, AD-9). The amount `AI_DAILY_ALERT_USD` exists only in the setup guide.

**Approach:** A due action in the sweep (Story 3.5) sums today's AI spend (Europe/Oslo day) through `app/ai` and, once it passes `AI_DAILY_ALERT_USD`, records the day's alert in `app/ai` and enqueues one `immediate` notice per active Admin with a dedupe key per date and Admin. The mail and «KI-kostnad» (`/admin/ki-kostnad?dag=YYYY-MM-DD`) show that day's spend, the alert amount and the dearest Class sessions by name; the Admin-område shows today's alert beside the «KI-kostnad» link. Story 15.6's cost page is not built (needs Epic 12), so only the day section it will sit beside is built here.

## Boundaries & Constraints

**Always:**
- Setting `ai_daily_alert_usd: Decimal | None`, default `25.00` USD, a stated placeholder until the prototype (issue #8); an empty `AI_DAILY_ALERT_USD` means not set. Line added to `.env.example` and the comment in `config.py`.
- The day's spend is `ai.calls.day_spend(day, top=…)`: sum of `llm_call.cost_usd` (every outcome, every scope) whose `started_at` lies in the Europe/Oslo calendar day `[00:00, 24:00)`, unrounded `NUMERIC(18,8)`, plus per Class session scope (dearest first, ties by id) and the evaluation scopes as one sum. No sum in `ops` or `messaging`.
- "Passed" means `total > AI_DAILY_ALERT_USD`.
- Table `ai_spend_alerts` (owned by `app/ai`, migration `0068`): `id`, `day DATE UNIQUE`, `alert_usd`, `spent_usd` (both `NUMERIC(18,8)`), `alerted_at` (the sweep's clock). Ids, amounts and times only; listed in `ai.calls.TABLES_WITHOUT_PERSONAL_DATA`. Written and read only through `ai.budget.record_daily_alert` / `daily_alert`.
- Due action `ops.daily_spend_alert` in `ops/sweep.py`: `find(now)` returns `[day]` when the amount is set, the day's total passes it and at least one active Admin has no notice under key `ai_daily_spend:<day>:<user_id>`; `act(day, now)` in one transaction re-reads the total, records the alert (first record wins, idempotent) and calls `notify.enqueue(s, admin, "ai_daily_spend", key, ref=alert.id)` for each active Admin. A second sweep sends nothing; an Admin added later the same day is told once.
- Kind `ai_daily_spend` registered in `messaging/delivery.KINDS` as `IMMEDIATE` with a context resolver; templates `ai_daily_spend.{txt,html}.j2`: date, spend, alert amount, up to three Class sessions «class-of-1994 · Klasseøkt 2» with their spend, and a link `url('/admin/ki-kostnad?dag=<day>')`. No Student data. The resolver returns None (mail skipped) when the recipient is no longer an active Admin.
- `GET /api/admin/ai/daily-spend?day=YYYY-MM-DD` (policy `ai_models.manage`, default today in Oslo, a day after today 422): `day`, `total_usd`, `calls`, `evaluation_usd`, `alert_usd` (null when not set), `passed`, `alerted_at` (null unless recorded), `sessions` (top 10: `class_session_id`, `label`, `institution_name`, `usd`, `calls`), `session_count`. Decimal strings as stored.
- «KI-kostnad» page: a first section «KI-kostnad per dag» with the day, total, alert amount or «Ingen daglig varselgrense er satt …», the alert line when recorded, a table of the dearest Class sessions and the simulation sum, links to the previous and next day (none after today), reading `?dag=`; refetch every 60 s. Admin-område: under the «KI-kostnad» link a line when today's alert is recorded, linking to the day. All copy in `nb.ts`, `[ASSUMPTION] Story 15.7`; no new primary button.
- The spine/architecture registration of the kind choice is recorded in Design Notes (immediate, decided here).

**Never:**
- No code outside `app/ai` names `llm_call` or `ai_spend_alerts`; `app/ai` imports no module; nothing imports `ops`.
- No Student name, email, or free text in the notice, mail, table or response; no user id in `ai_spend_alerts`.
- No cost-limit view or limit setting (Story 15.6); no audit for reads.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Passed | amount 1.00, today 1.50 spent, two Admins | one notice each, kind `ai_daily_spend`, keys per day+Admin; immediate mail with link and session names | — |
| Second sweep | same day, already told | nothing enqueued | — |
| Not passed | total ≤ amount | nothing | — |
| Not set | `AI_DAILY_ALERT_USD` empty | nothing; page says no daily alert is set | — |
| Day boundary | rows at 23:59:59 and 00:00:00 Oslo | each counts in its own day only | — |
| Next day | yesterday alerted, today passed again | new alert row and notices for today | — |
| Future day | `?day=` after today | 422 | — |
| Lecturer | GET daily-spend | 403 `forbidden` | — |

</intent-contract>

## Code Map

- `backend/app/ai/calls.py:75` `costs` -- pattern for sums; add `day_spend`, `DaySpend`, `ScopeSpend`; `TABLES_WITHOUT_PERSONAL_DATA` add the table.
- `backend/app/ai/budget.py` -- add `DailyAlert`, `record_daily_alert`, `daily_alert(day | id)`; `ai.db.transaction(session)` joins a caller's transaction.
- `backend/app/ai/models.py` -- add `spend_alerts`.
- `backend/app/platform/config.py:71` -- AI money settings; add `ai_daily_alert_usd` with empty→None.
- `backend/app/platform/notify/__init__.py:110,154` `enqueue`, `used_keys`.
- `backend/app/modules/messaging/delivery.py:228` `KINDS`, `OSLO`, `oslo_day`; context resolver pattern `_message_context`.
- `backend/app/modules/sessions/service.py:5315` `evaluation_sessions` (names); `identity.service.active_admins:226`.
- `backend/app/modules/ops/sweep.py:246` `DUE_ACTIONS`; `ops/ai_routes.py`, `ai_models.py`, `ai_schemas.py` -- route/service pattern.
- `backend/tests/test_imports.py:154` `AI_TABLES` regex; `tests/conftest.py:176` `AI_TABLES`; `tests/test_migrations.py:115,144,278` head and round trip; `tests/messaging/helpers.py` `drain`, `mails`.
- `frontend/src/modules/admin/{ai-models-page.tsx,ai-models.ts,api.ts}`, `modules/identity/home-page.tsx:63` `AdminSections`, `homes.ts`, `copy/nb.ts:2334` `aiCost`, `lib/number-format.ts`, `e2e/admin-ai-models.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0068_spend_alerts.py` -- table; `tests/test_migrations.py` head 0068 and round trip.
- `backend/app/ai/{models,calls,budget}.py` -- table, `day_spend`, alert record/read.
- `backend/app/platform/config.py`, `.env.example` -- setting.
- `backend/app/modules/ops/{spend_alert.py,sweep.py}` -- finder and action, registered after `messaging.mail`'s peers at the end of `DUE_ACTIONS`.
- `backend/app/modules/messaging/delivery.py`, `backend/app/platform/email/templates/kinds/ai_daily_spend.{txt,html}.j2` -- kind and mail.
- `backend/app/modules/ops/{ai_models,ai_schemas,ai_routes}.py` -- daily-spend read.
- `backend/tests/{conftest,test_imports}.py` -- table names.
- `backend/tests/ops/test_daily_spend_alert.py` -- every matrix row, mail content (names, link, no Student data), boundary.
- `frontend/src/copy/nb.ts`, `src/modules/admin/{ai-models-page.tsx,ai-models.ts,api.ts,daily-spend.ts(+test)}`, `modules/identity/home-page.tsx`, `src/lib/api/*` (regenerated) -- day section and Admin-område line.
- `frontend/e2e/admin-ai-models.spec.ts` -- the day section with no spend, «Ingen…»/alert amount text, day links; axe at 320/1440.

**Acceptance Criteria:**
- Given the alert mail, when the Admin opens it, then it names the dearest Class sessions by Class session name and links to `/admin/ki-kostnad?dag=<day>`, which shows that day's spend.
- Given today's alert recorded, when the Admin opens the Admin-område, then a line under «KI-kostnad» says the daily alert amount was passed and links to the day.
- Given `AI_DAILY_ALERT_USD` unset, when the Admin opens «KI-kostnad», then the day section states that no daily alert is set.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- layers: Blind Hunter and Edge Case Hunter (sonnet); Verification Gap and Intent Alignment skipped, as the lead asked for two reviewers.
- verdicts: 28 findings — high 0, medium 2, low 22, false 4, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind: `day_spend` filters `llm_call.started_at` with no index, read every minute by the sweep and every minute per open page — migration 0068 and `ai/models.py` add `ix_llm_call_started_at`; `test_migrations.py` asserts it.
  - `[low]` `[patch]` Blind: `day_spend` runs four statements that can disagree under READ COMMITTED — total, call count, evaluation sum and session count now come from one statement with `FILTER` aggregates; the top-N list stays its own query.
  - `[false]` `[reject]` Blind: the `alert_at` fixture leaves a stale cached setting — the autouse `_fresh_settings` fixture in `tests/conftest.py` clears the settings cache before and after every test.
  - `[low]` `[reject]` Blind: 25.004 against 25.00 reads as two equal amounts with «passert» — needs a spend within half a cent of the amount; a third decimal everywhere would cost more than it helps.
  - `[low]` `[reject]` Blind: the mail drops a Class session `evaluation_sessions` does not name, the page shows its id — spend needs a saved, locked Class session, and Class sessions and Classes are never deleted, so the case does not arise.
  - `[low]` `[patch]` Blind: `max(total, recorded)` in the mail is unexplained — a comment now says the mail shows the spend when composed and calls only add to it.
  - `[low]` `[patch]` Blind: the page shows the current setting, not the amount an alerted day was alerted at — `daily_spend` answers the recorded `alert_usd` for an alerted day (and judges `passed` against it); the test unsets the setting after an alert and still reads «1.00000000».
  - `[low]` `[reject]` Blind: a future `?dag=` shows the generic page error — reached only by editing the URL; a guard and a message add a branch for it.
  - `[low]` `[patch]` Blind: a very old `day` can overflow into a 500 — `day` now has `ge=2020-01-01` (422); the test asks for 0001-01-01.
  - `[low]` `[reject]` Blind: no catch-up for yesterday when the sweep was down over midnight — the story asks for same-day notice; a look-back adds a branch for an outage across midnight.
  - `[false]` `[reject]` Blind: no second alert when the spend doubles — the intent is one alert per Admin per day.
  - `[low]` `[reject]` Blind: `assert isinstance(day, date)` lets a datetime through and vanishes under `-O` — only the sweep's own finder calls it with a `date`; every due action of `sweep.py` guards its item the same way.
  - `[low]` `[reject]` Blind: `identity/home-page.tsx` now imports from `modules/admin` and polls once a minute — no import cycle (admin's `api.ts` and `daily-spend.ts` do not import `home-page`); one small request a minute on the Admin-område only.
  - `[low]` `[reject]` Blind: no live region for the refetched alert — a background refresh is no status message of a user action (WCAG 4.1.3); the page reads «Sist oppdatert».
  - `[low]` `[patch]` Blind: the e2e hard-codes the 25,00 USD placeholder — it reads the stack's `alert_usd` from the api and writes it with `dayUsdText`.
  - `[false]` `[reject]` Blind: draft copy, duplicated month list, lead implies alerts without an amount — the copy is marked `[ASSUMPTION] Story 15.7` by rule; the month list follows the existing invitation templates; the lead says the alert goes «når summen passerer varselgrensen».
  - `[low]` `[reject]` Blind: the 25.00 placeholder is live in production — the placeholder is a stated configuration value (epic context), recorded as a decision taken in place of the founder.
  - `[false]` `[reject]` Blind: the diff carries an unrelated `.logs` edit for Story 11.5 — that change is the orchestrator's commit `c2fe01be` on the branch after the baseline, not part of this change's working tree.
  - `[low]` `[reject]` Blind: no concurrency, mid-loop failure or deactivated-Admin tests — `record_daily_alert` is insert-on-conflict-do-nothing and each notice is unique on its dedupe key, all in one transaction; the former-Admin case is tested through the resolver.
  - `[medium]` `[patch]` Edge: three `llm_call` scans a minute with no index — same root cause as the Blind index row.
  - `[low]` `[reject]` Edge: a future `?dag=` shows only the page error — same as the Blind row.
  - `[low]` `[patch]` Edge: four statements can disagree — same as the Blind row.
  - `[low]` `[reject]` Edge: the mail lists fewer than three sessions when one has no name — same as the Blind row.
  - `[low]` `[reject]` Edge: the page shows a raw id for an unnamed session — same as the Blind row.
  - `[low]` `[patch]` Edge: a changed setting makes the page and the mail disagree on the amount — same as the Blind row.
  - `[low]` `[reject]` Edge: a datetime passes the `date` assert — same as the Blind row.
  - `[low]` `[reject]` Edge: the spec says the due action is last, the code puts it before the deadline reminders — the fix is to edit this build's spec; Story 5.14's test pins the reminders as the last action, so the alert runs just before them.
  - `[low]` `[patch]` Edge: `alert_usd` («25.00») and the totals («31.25000000») have different scales — every amount of the answer is now written with the column's eight places.

## Design Notes

The notice needs the day at send time, but a notice holds ids only; so the alert is a row (`ai_spend_alerts`) and the notice's `ref` is its id. The row lives in `app/ai` because cost state is `ai`'s (AD-6) and because `messaging` may read `app.ai` but no module may import `ops`. The kind is `immediate` (decided here, since the spine lists only the founder-decided kinds): a runaway cost must be noticed the same day, also in the quiet hours. The placeholder amount 25.00 USD is about 50 Students at the 0.50 USD target in one day.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/ops/test_daily_spend_alert.py tests/test_migrations.py tests/test_imports.py tests/identity/test_personal_data_registry.py tests/messaging/test_delivery.py -q` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test admin-ai-models homes --workers=4` -- expected: pass

## Auto Run Result

Status: done

**Summary.** The sweep's new due action `ops.daily_spend_alert` (`backend/app/modules/ops/spend_alert.py`) sums today's AI spend (the Europe/Oslo day of `llm_call.started_at`, every scope and outcome, unrounded) through the new `ai.calls.day_spend`. Once it passes `AI_DAILY_ALERT_USD` (placeholder 25.00 USD; empty means not set) it records the day in the new `ai_spend_alerts` table (`ai.budget.record_daily_alert`, first record stands) and enqueues one `ai_daily_spend` notice per active Admin, keyed `ai_daily_spend:<day>:<user_id>`, so each Admin is told once a day; an Admin added later that day is told once too. The kind is registered `immediate` in `messaging.delivery.KINDS`; its mail names the day, the spend, the amount and the three dearest Class sessions («class-of-1994 · Klasseøkt 1: 1,50 USD») and links to `/admin/ki-kostnad?dag=<day>`; no Student data; a recipient no longer Admin gets none. `GET /api/admin/ai/daily-spend?day=` (policy `ai_models.manage`) serves «KI-kostnad per dag», now first on «KI-kostnad»: total and calls, the alert amount or «Ingen daglig varselgrense er satt …», the alert line with its time, the ten dearest Class sessions, the simulation runs apart, links to the day before and after (none after today), read again every minute. The Admin-område shows today's alert under the «KI-kostnad» link with a link to the day.

**Seam (Story 15.6).** The cost page of 15.6 (cost per Class session, Game and day, the limit) is not built (needs Epic 12). Only the day section it will sit beside is built here; `ai.calls.day_spend` is the one daily sum 15.6 can reuse.

**Decisions taken in place of the founder.** The kind is `immediate` (also between 22:00 and 07:00). Placeholder amount 25.00 USD (about 50 Students at the 0.50 USD target in a day, issue #8); empty turns the alert off. "Passed" is strictly above. One alert per Admin per day, no second alert at a higher spend, no catch-up of a day missed while the worker was down. The spend counts simulation runs too ("across all scopes"), listed apart. An alerted day keeps the amount it was alerted at. The mail names three Class sessions and the page ten. Days before 2020-01-01 or after today are refused (422). All copy `[ASSUMPTION] Story 15.7`.

**Personal data.** New table `ai_spend_alerts`: a day, two amounts and a time; no `user_id`, no free text; listed as `none` through `ai.calls.TABLES_WITHOUT_PERSONAL_DATA`.

**Files.**
- `backend/migrations/versions/0068_spend_alerts.py`: the alert table and the `llm_call.started_at` index.
- `backend/app/ai/{models,calls,budget}.py`: table and index, `day_spend`/`oslo_day`/`oslo_date`, `record_daily_alert`/`daily_alert`, registry entry.
- `backend/app/platform/config.py`, `.env.example`: `AI_DAILY_ALERT_USD`.
- `backend/app/modules/ops/{spend_alert,sweep,ai_routes,ai_schemas}.py`: finder and action, its place in `DUE_ACTIONS`, the day read and its route.
- `backend/app/modules/messaging/delivery.py`, `backend/app/platform/email/templates/kinds/ai_daily_spend.{txt,html}.j2`: the immediate kind, its context and the mail.
- `backend/tests/ops/test_daily_spend_alert.py` (new), `tests/{conftest,test_imports,test_migrations}.py`.
- `frontend/src/modules/admin/{ai-models-page.tsx,ai-models-page.test.tsx,api.ts,daily-spend.ts,daily-spend.test.ts}`, `src/app/(app)/admin/ki-kostnad/page.tsx`, `src/modules/identity/home-page.tsx`, `src/copy/nb.ts`, `src/lib/api/*` (regenerated), `e2e/admin-ai-models.spec.ts`.

**Review.** Two sonnet sub-agents (blind, edge case); 28 findings. Patched: 1 medium entry (the `started_at` index) and 6 low ones (one aggregate statement, the `max` comment, the recorded alert amount, the earliest day, the e2e amount, eight-place amounts). Deferred: none. Rejected: 21, each with its reason in the triage log.

**Follow-up review: not recommended.** Patched by verdict: medium 1, low 6, high 0.

**Verification.**
- Backend full suite (`-n 8 --maxprocesses=8`, DB `olspillet_e15`): 3461 passed twice after the review patches. One earlier run had one failure that did not repeat in the two later runs; its name was not captured. ruff check and format are clean.
- Frontend: typecheck ok, Vitest 1137 passed, `lint:colours` and `check:copy` passed, `next build` compiled.
- Playwright (`--workers=4`, stack on `olspillet_e15stack`): `admin-ai-models`, `homes`, `order-field`, `playout`, `admin-audit`, 43 passed, with axe at 320 and 1440 px, including the Admin-område alert line and the day links. Screenshots at 360 and 1440 px were checked: one column on phone, the table reflows to labelled rows, the alert link is a full tap target, and the page has no new primary button.
- Matrix: every row is covered in `test_daily_spend_alert.py` (passed, second sweep, not passed at equal, not set, day boundary at 00:00 Oslo, next day, future day 422, Lecturer 403).
- No new test is over 1 s (the slowest is about 0.8 s).

**Residual risks.**
- The e2e serves the alerted day from a route, because the stack's mock model costs nothing. The sweep → api → page path is joined only in the backend tests.
- If the worker is down from before the spend passes the amount until after midnight, that day is never alerted.
