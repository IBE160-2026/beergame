---
title: 'Story 9.15: Ask bounded follow-up questions about my Game'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'ebda19d152077564f2af0367a6284fc284349486'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      No total cap per Student or Class session on follow-up questions; only the per-window rate limits bound them.
    evidence: |-
      Each question is one paid call on the Class session's shared budget (Debrief purposes may spend the reserve). At 10 per 10 minutes a Student can keep asking until the Test deadline, and a spent budget turns other Students' narration and quiz lines into code text. The story names only the rate limits (placeholders); a total cap or a budget share for follow-ups is a product decision.
    location: >-
      backend/app/modules/debrief/follow_up.py:_count
    severity: medium
  - summary: >-
      The scrubbed follow-up question in llm_call.request has no retention or erasure rule yet.
    evidence: |-
      debrief_follow_ups cascades on the user and the Class session, but llm_call rows (owned by app/ai, AD-14 retention) keep the scrubbed request with caller ids and no foreign key. Retention of llm_call bodies is not built yet for any purpose.
    location: >-
      backend/app/ai/models.py llm_calls
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Student past the reflection questions has no way to ask about their own Game; no Student free text has ever reached an LLM, so `platform/pii.terms` still returns nothing for a Class session, and there is no rate limit, close rule or hint-only answer shape for such a question (FR-45, AD-6, AD-7, AD-11).

**Approach:** A follow-up field after the reflection questions sends one question per POST; the api calls `app.ai.text.worded("debrief_follow_up", <Class session scope>, …)` once, synchronously with a deadline, with the scrubbed question, the scrubbed Explanation, the stored facts set and the pinned hint templates; the answer is either a decline flag (fixed line) or 1–3 hint sentences checked by Story 9.14's `validate_ai_text` and rendered by code. `pii.terms` now reads the Roster.

## Boundaries & Constraints

**Always:**
- Output `FollowUpOutput {decline: bool, sentences: AiSentence[0..3]}`; accepted only when `decline` is true with no sentences, or false with 1–3 sentences that `validate_ai_text(..., allowed=HINT ids)` accepts. Hint templates (draft, `[ASSUMPTION]`) point to where to look (a Uke, a row, Varer på vei, a later cost) and fill only the cited facts' numbers; they are version 2 of the `narration_templates` content kind (v1's four + `hint-row`, `hint-supply-line`, `hint-later`, `hint-compare`), so a session locked on v1 has no follow-up. The narration keeps citing narration ids only.
- Prompt `prompts/debrief_follow_up/v1.md` (locked) states: decline anything outside the Game and its concepts; for a test-like question give only hints, never a worked answer. Purpose `debrief_follow_up`, one attempt, not player. `MOCK_SPEC`/`mock.json` list it (zero-config derives the new config row as in 9.14). The mock's answer is decided by code: decline when the question names no game word, else one `hint-row` sentence on the Seat's first moment.
- `pii.terms(scope)` (async) for a Class session: names (whole, and each word of 2+ letters), emails and their local parts of every User on the Roster (removed entries too) and of the Class's staff, plus the non-empty cells (3+ characters) of a staged Roster upload of the Class (student numbers live only there). Tables by name only (`platform` imports no module). Only `app/ai/gateway.py` calls it (import test).
- POST `/api/debriefs/{id}/follow-up {question}` order: own Debrief → Explanation gate → `step_locked` gate → 403 `reflection_required` until every reflection question is answered → 409 `follow_up_off` (pin off, no provider for the pinned config, no hint templates pinned, or a Seat with no citable facts) → 409 `follow_up_closed` (a `debrief_follow_up_closures` row, or DB time past `sessions.student_deadlines` Test deadline) → 422 `validation_error` (blank, >500 chars) → 429 `rate_limited` with `fields.retry_after` and `Retry-After` (per account and per IP, `platform/ratelimit`, settings with placeholder values) → the call. Answer 200 `{outcome: answered|declined|unanswered, question, answer: RenderedTextOut|null, asked_at}`.
- `answered`/`declined` stored once in `debrief_follow_ups(id, user_id, class_session_id, fact_set_id, question, outcome, answer, llm_call_id, asked_at)` (insert-only trigger); `unanswered` is not stored. GET `/api/debriefs/{id}/follow-up` → `{state: off|open|closed, asked: [...]}` (own rows only, oldest first).
- `debrief.commands.close_follow_up(user_id, class_session_id)` (idempotent insert) and `debrief.service.close_follow_up`, the entry point Epic 11 calls; registry entries with no topics.
- Web: `FollowUp` under the reflection questions once all are answered, before step 4; not rendered for `off`; for `closed` a line replaces the field; answers announced politely (`role="status"`), focus stays in the field; accepted text via `DebriefText`/`AiNote`; declined and unanswered lines from `nb.ts`; on failure or 429 the question stays in the field. Copy draft `[ASSUMPTION]`.

**Never:** free LLM text shown; the LLM call retried; the original question or a Roster term in the `llm_call` request; follow-up blocking a step; another Student's follow-ups readable; `modules/debrief` importing `app/ai` beyond `text`, `budget`, `gateway`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Answered | «Hvorfor bestilte jeg så mye i uke 5?» | `answered`, marked text, row with `llm_call_id` | — |
| Off-topic | «Hva er hovedstaden i Frankrike?» (mock declines) | `declined`, fixed line, row stored | — |
| Failure | mock outage / rejected output / budget spent | `unanswered`, nothing stored, question kept | never retried |
| Roster name | «Kari Nordmann sa at …» in question and Explanation | `[REDACTED]` in `llm_call.request` | — |
| Too many | over the account or IP limit | 429 `rate_limited`, `retry_after` | inline line |
| Closed | `close_follow_up` called, or Test deadline passed | 409 `follow_up_closed`; GET `state: closed` | line replaces field |
| Off | pin off / no provider / v1 templates / no moments | 409 `follow_up_off`; GET `state: off` | field absent |

</intent-contract>

## Code Map

- `backend/app/analysis/narration.py` -- `NARRATION_TEMPLATES`, `NarrationTemplates._complete` (exact id set; loosen to NARRATION ⊆ ids ⊆ NARRATION ∪ HINT), `validate_ai_text` (arity from `NARRATION_TEMPLATES`, later-cost rule by id; generalize: `allowed`, arity map, rule by `later_first/last_week` slot use), `citable`, `_values`.
- `backend/app/ai/{text.py (worded; add can_word), purposes.py, seed.py:24 MOCK_SPEC, gateway.py:268 _prepare/:309 preview (pii.terms → await), adapters.availability}`, `ai-configs/mock.json`, `prompts/hashes.json`; tests `tests/ai/conftest.py:13`, `test_prompt_files.py:26/:61`.
- `backend/app/platform/pii.py` -- today returns []; `authz.py:185` table-by-name pattern.
- `backend/app/platform/ratelimit.py` (`hit`, `seconds_left`, `client_ip`); `identity/service.py:251` usage; `platform/config.py` settings.
- `backend/app/modules/debrief/{service.py:968 own_reflection,:554 step,:618 _moments; commands.py:1156 store_ai_text; narration.py:130 _template_lines, enabled_pin; routes.py:136 _answer; schemas.py; models.py; README.md}`; `platform/events/registry.py`.
- `backend/app/modules/sessions/service.py:1412 student_deadlines`; `content/service.py:203 narration_templates`.
- `backend/migrations/versions/0112_debrief_narration.py` (pattern); tests `tests/analysis/test_narration.py`, `tests/debrief/test_narration.py` (`played_long`, `reflect`, `pins` v1 assertion), `tests/test_imports.py`, `tests/test_migrations.py`.
- Frontend: `modules/debrief/{debrief-page.tsx:167,reflection-step.tsx,ai-text.tsx,api.ts}`, `components/text-area-field`, `copy/nb.ts` (`debrief.reflection`), `e2e/debrief-narration.spec.ts` (`pastReflection`, `liveClassGame`).

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/narration.py`, `analysis/follow_up.py` (new) -- hint ids, generalized validator, `FollowUpOutput`, `validate_follow_up`, `mock_output`.
- `backend/migrations/versions/0113_debrief_follow_up.py` -- narration templates v2, `debrief_follow_ups` (insert-only), `debrief_follow_up_closures`.
- `backend/app/ai/*` + `prompts/debrief_follow_up/v1.md` -- purpose, prompt, mock spec, `can_word`, async `pii.terms` call.
- `backend/app/platform/{pii,config}.py` -- Roster terms; follow-up limits and deadline.
- `backend/app/modules/debrief/*`, `platform/events/registry.py` -- follow-up module, commands, service, routes, schemas, narration ids filter, README.
- Tests: `tests/analysis/test_follow_up.py` (pure, hand-built facts), `tests/platform/test_pii.py` (terms), `tests/debrief/test_follow_up.py` (ONE played game: every matrix row, scrub in request and stored body, close via service, deadline, rate limit), import test, migration/prompt/narration updates.
- Frontend: `follow-up.tsx` (new), `debrief-page.tsx`, `api.ts`, `nb.ts`, `debrief.test.ts`, regenerated api; `e2e/debrief-follow-up.spec.ts` (one 10-Uke game: answered at 360, declined at 320, failure via a fulfilled route at 1440, axe at each width).

**Acceptance Criteria:**
- Given a Student past the reflection questions with AI text on, when they send a question, then one `llm_call` row with purpose `debrief_follow_up` and the Class session scope exists, its request holds the question with Roster terms scrubbed, and the page shows «KI-generert, kan ta feil: «…»» announced in a status region while focus stays in the field.
- Given the mock declines, then the fixed decline line shows with no AI marking and no LLM text.
- Given a failure, then «no answer» shows inline, the question stays in the field, and step 4 is reachable.
- Given `debrief.service.close_follow_up` was called, then POST answers 409 `follow_up_closed` and the page shows the closed line.
- Given AI text off, then no follow-up field is rendered.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run (sonnet): blind hunter (with a prompt-injection and data-leak angle), edge-case hunter, verification gap, intent alignment. Every hand-back failed; the findings were read from `review-{blind,edge,verification,intent}-9-15.md` in the scratchpad. The diff left out the generated `openapi.json`/`schema.ts` and `.docs`.
- verdicts: 51 findings — high 0, medium 8, low 34, false 9, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind 1) Student numbers are almost never scrubbed: the only store is a staged Roster upload, gone once confirmed. `app.ai.scrub` now also scrubs every run of 6+ digits and every e-mail address whenever a Class session has terms (backstop); a staged cell stays a term. No identity table holds a student number (pre-existing).
  - `[low]` `[patch]` (blind 2) Inflected names («Karis») slipped through. The scrub takes a genitive «s» after a term; diacritic and nickname variants rejected (needs fuzzy matching).
  - `[medium]` `[patch]` (blind 3) No pattern backstop for addresses or numbers outside the Roster. As blind 1; test `test_a_genitive_any_address_and_a_long_number_are_scrubbed_with_any_term`.
  - `[low]` `[reject]` (blind 4) The Explanation is sent. The story's own test puts a Roster name in the Explanation and checks the request; it is scrubbed, quoted and capped at 5000 characters.
  - `[medium]` `[patch]` (blind 5) The question could close its `<question>` block. `follow_up._quoted` turns angle brackets into look-alikes in the prompt (stored text unchanged); the api test asserts only the prompt's own `</question>` remains. Output is still bounded by the validator.
  - `[low]` `[patch]` (blind 6) Name words scrub structured inputs (facts, templates). Name words are now letters only, 3+ (`[^\W\d_]{3,}`), so «de», «av» or a number never becomes a term; scrubbing every string value stays the gateway's design (AD-6).
  - `[low]` `[patch]` (blind 7) The privacy line promised staff could read the question, with no staff route. Copy now says the question goes to a KI with names and addresses removed and is stored with the answer.
  - `[low]` `[defer]` (blind 8) No retention for the scrubbed `llm_call` body. Pre-existing for every purpose (AD-14 retention not built); deferred.
  - `[low]` `[patch]` (blind 9) A close during the call still stored the answer. `ask` checks `closed` again before storing (409). Failing closed with no Test deadline rejected: the AC makes the deadline the backstop and Epic 11 the caller.
  - `[medium]` `[defer]` (blind 10) No total per-Student cap; one Student can drain the shared budget. Product decision beyond the AC's rate limits; deferred.
  - `[low]` `[patch]` (blind 11) 60 per address per window would refuse a lecture hall behind one address. Placeholder raised to 300 (the login per-address value); copy no longer blames the Student.
  - `[low]` `[patch]` (blind 12) The 429 line vanished on typing. The field no longer resets a rate-limited error.
  - `[low]` `[reject]` (blind 13) Downgrade deletes a pinned version 2. Same as every content migration (9.14's 0112); downgrade is a dev operation.
  - `[low]` `[reject]` (blind 14) `prepare` reads on every GET. A handful of indexed reads; the facts set is stored once.
  - `[low]` `[reject]` (blind 15) No schema `max_length` before the reads. Same as the Explanation and reflection bodies; the 422 keeps its field reason.
  - `[false]` `[reject]` (blind 16) The mock's keyword test proves nothing about a real model. It is the deterministic mock (AD-17); the real model's behaviour is the recorded residual risk.
  - `[false]` `[reject]` (blind 17) Isolation unproven. The mate's GET, with two of Sara's rows stored, returns `asked: []`; another id is 403 through `_own`. The `pii.terms` gaps it names are patched under verification 2.
  - `[low]` `[patch]` (edge 1) As blind 6.
  - `[low]` `[patch]` (edge 2) Short or numeric name parts became terms. As blind 6.
  - `[false]` `[reject]` (edge 3) Roster queries on every Class-session call. Class-session LLM players raise `scope_unresolved` before `terms`; only Debrief calls reach it.
  - `[low]` `[patch]` (edge 4) Per-address limit and campus NAT. As blind 11.
  - `[low]` `[patch]` (edge 5) Close race. As blind 9.
  - `[false]` `[reject]` (edge 6) Parallel POSTs pass the count. `ratelimit.hit` is one atomic upsert per request; the limit holds.
  - `[medium]` `[defer]` (edge 7) Concurrent calls each cost budget. As blind 10.
  - `[medium]` `[defer]` (edge 8) No total cap. As blind 10.
  - `[low]` `[patch]` (edge 9) Text typed while waiting was erased. The field clears only when it still holds the sent question.
  - `[low]` `[patch]` (edge 10) Rate-limit copy blamed the Student for the address limit. As blind 11.
  - `[low]` `[reject]` (edge 11) Downgrade. As blind 13.
  - `[low]` `[patch]` (edge 12) The mock could hint on a pattern occurrence. `mock_output` takes the earliest moment.
  - `[false]` `[reject]` (edge 13) `prepare` raises on `ViewError` or a missing pin. `_own` serves finished games only; a missing pin reads the latest version.
  - `[low]` `[reject]` (edge 14) A 403 `reflection_required` would show the load-failed block. The field mounts only once the same server state says every question is answered.
  - `[low]` `[reject]` (edge 15) A later-cost-only template is not gated. No template does it; versions are validated content.
  - `[false]` `[reject]` (edge 16) `LATER_COST_TEMPLATE` removed. No importer anywhere; the slot rule gives the same verdicts (9.14 tests pass).
  - `[low]` `[patch]` (edge 17) `\w{2,}` matched digits. As blind 6.
  - `[low]` `[patch]` (edge 18) Mock claim "first moment". As edge 12.
  - `[low]` `[reject]` (edge 19) Off for no moments, not "no citable facts". Decision: the matrix row's «no moments», the narration's rule (a Rule-based Seat has pattern occurrences of Weeks the Student never decided).
  - `[medium]` `[defer]` (edge 20) "Bounded" is a rate only. As blind 10.
  - `[low]` `[patch]` (verification 1) The narration prompt's template list was unpinned. `test_narration` asserts the narration request names its four ids and no `hint-`.
  - `[low]` `[patch]` (verification 2) `pii.terms` staged cells, `MIN_CELL` and removed members untested. The api test stages an upload (`240117`, `Ja`, a name) and removes the mate from the Roster.
  - `[low]` `[patch]` (verification 3) The per-address bucket untested. The api test pushes `follow_up_ip` over and expects 429. The deadline argument rejected: the gateway's deadline has its own tests.
  - `[low]` `[patch]` (verification 4) Closed, 429 and off not checked in the web app. The e2e spec now drives a 429 (the wait in minutes, question kept) and a closed answer (the line replaces the field) through fulfilled api answers; `off` stays an api check.
  - `[false]` `[reject]` (verification other 1) Fixture re-exports. Plumbing, as other test modules.
  - `[false]` `[reject]` (verification other 2) Generated client not in the diff. Regenerated and committed with the change.
  - `[low]` `[patch]` (intent a) Web states only at the api. As verification 4.
  - `[low]` `[patch]` (intent b) The deadline backstop only via GET. The api test now posts under the passed deadline and gets 409 `follow_up_closed`.
  - `[medium]` `[patch]` (intent c) Student numbers not from identity. As blind 1.
  - `[low]` `[reject]` (intent d) Only the mock config gets the prompt. No real config row is in the repository; the README and Design Notes give the `config edit … --prompt debrief_follow_up=1` command.
  - `[false]` `[reject]` (intent e) `worded`, not `ai.run`. `worded` makes exactly one `gateway.run` (the spine's `ai.run`) with the Class session scope; the test reads that call's row.
  - `[low]` `[reject]` (intent f) 9.14's surfaces changed (version 2, validator parameter). Decision: the hints are versioned content of the same kind; 9.14's tests pass unchanged in substance.
  - `[low]` `[reject]` (intent g) A test-like question is never put to a model double. Structural bound: only hint templates validate, so no worked answer can render; a real model's judgement is the residual risk.
  - `[low]` `[reject]` (intent h) Off also for no moments and version 1. Decision (Design Notes, Auto Run Result).
- Found while verifying (not a reviewer finding): the e2e spec failed once under `--workers=4` because the dev narration's mock outage (`?outage=true`, 9.14) was process-global and failed Sara's decline call at the same moment. `app.ai.mock.outage_here` (a context variable) now fails only the calling task's attempts; `ai.text.provider_failing` uses it; new test `test_the_dev_outage_fails_only_the_calling_tasks_attempts`.
- Also fixed: three test fixtures (`test_content`, `test_starting_task`, `test_facts`) deleted every content version above 1, which removed migration 0113's version 2 from the shared test databases; they now delete only versions a test published (`UNSHIPPED`), and the lane's test databases were given version 2 back.

## Design Notes

The follow-up call is on the request path (spine diagram: «api → ai gateway: Debrief follow-up»), unlike the narration: the Student is waiting for an answer, but no step waits on it, and a deadline (`follow_up_deadline_seconds`, 20 s) bounds the request. A decline is a validated AI output: stored, but shown as a fixed code line without the AI marking (no AI words are shown). Hints only, always (the user story: hints, not answers), so a test-like question cannot get a worked answer even if the model misjudges it. Real-call check once the OpenRouter key is set: `python -m app.ai.cli config edit <id> --prompt debrief_follow_up=1`, measure and pin, lock a session, ask a question, then `SELECT outcome, request->>'prompt', response FROM llm_call WHERE purpose = 'debrief_follow_up'`.

## Verification

**Commands:**
- `uv run pytest -n0 tests/analysis/test_follow_up.py tests/analysis/test_narration.py tests/platform/test_pii.py tests/debrief/test_follow_up.py tests/test_imports.py` -- pass
- full backend `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-follow-up`, `debrief-*`, `homes`, play-screen specs `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A follow-up field under the reflection questions, before step 4: a Student asks about their own Game and gets hints grounded in its numbers. `POST /api/debriefs/{id}/follow-up` makes one `debrief_follow_up` call through `app.ai.text.worded` on the Class session's scope and pinned config (deadline 20 s, never retried) with the scrubbed, quoted question and Explanation, the stored facts set and the pinned hint templates. The answer (`analysis.follow_up.FollowUpOutput`) is a decline flag or 1–3 hints that Story 9.14's `validate_ai_text` checks with the hint ids only and code renders; a decline shows a fixed line, a hint shows «KI-generert, kan ta feil: «…»». Answered and declined questions are stored once in `debrief_follow_ups` (user, Class session, facts set, call); a failure, rejection or spent budget stores nothing and keeps the question in the field. `platform/pii.terms` now reads the Class's Roster and staff (names, words of names, addresses, staged Roster cells) and only the gateway calls it; the scrub adds a genitive «s», any e-mail address and any 6+ digit run. Rate limits per account and address (429 with `retry_after`), `follow_up_off`, `follow_up_closed` (`debrief.service.close_follow_up` for Epic 11, or the Test deadline). Hint templates are version 2 of `narration_templates` (migration 0113).

**Files.**
- `backend/app/analysis/narration.py` (hint ids, `allowed`, slot-based later rule, `lines`, `has_hints`), `analysis/follow_up.py` (new): output, validator, mock answer.
- `backend/app/ai/{purposes,seed,text,gateway,scrub,mock}.py`, `prompts/debrief_follow_up/v1.md`, `hashes.json`, `ai-configs/mock.json`: purpose, prompt, `can_word`, awaited terms, backstop scrub, task-scoped dev outage.
- `backend/app/platform/{pii,config}.py`, `events/registry.py`: Roster terms, placeholder limits and deadline, two commands.
- `backend/migrations/versions/0113_debrief_follow_up.py` (new): templates v2, `debrief_follow_ups` (insert-only), `debrief_follow_up_closures`.
- `backend/app/modules/debrief/{follow_up.py (new),commands,models,schemas,service,routes,narration,README}`, `content/README.md`.
- Tests: `tests/analysis/test_follow_up.py`, `tests/debrief/test_follow_up.py` (new); updates to `test_imports`, `test_migrations`, `ai/{conftest,test_gateway,test_prompt_files,test_scrub,test_text}`, `content/test_content`, `sessions/test_lock`, `debrief/test_narration`, `starting_task/test_starting_task`, `games/test_facts`.
- Frontend: `modules/debrief/follow-up.tsx` (new), `{api,debrief-page,debrief.test}`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/debrief-follow-up.spec.ts` (new).

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), four sonnet review layers. (1) Answers are always hints (never statements), so a test-like question cannot get a worked answer even if the model misjudges it. (2) The hint templates are version 2 of `narration_templates` (`hint-row`, `hint-supply-line`, `hint-later`, `hint-compare`, draft copy); a session locked on version 1, or before this story, has no follow-up. (3) The call runs on the api request (the spine's diagram), bounded by `follow_up_deadline_seconds` = 20; no step waits on it. (4) The Student's Explanation is sent with the question (scrubbed and quoted), as the AC's Explanation test implies. (5) The field is off for a Seat with no moments (mostly AI players), as the narration. (6) A decline is stored with its call but shown as a fixed line without the AI marking (no AI words are shown). (7) `pii.terms` also covers the Class's staff and removed Roster entries; name words are letters only, 3+; no identity table holds student numbers, so the scrub's 6+ digit backstop and staged Roster cells cover them. (8) The question is stored as typed (keyed by the Student); the `llm_call` row holds the scrubbed text. (9) Placeholder limits: 10 questions per account and 300 per address per 10 minutes. (10) `close_follow_up` emits `user` so an open page closes the field. (11) The dev narration's outage now fails only its own request's calls (`mock.outage_here`). (12) Copy is draft `[ASSUMPTION]`.

**Review.** 51 findings (high 0, medium 8, low 34, false 9). Patched 2 medium entries (no scrub backstop for student numbers and addresses; the question could close its prompt block) and 15 low root causes (genitive names, short or numeric name words, privacy copy, close race, address limit and copy, 429 line kept while typing, typed text kept during the wait, mock on moments, narration prompt pinned, pii terms, address bucket, deadline POST, web closed and 429 states). Deferred 2 (total per-Student cap, medium; `llm_call` body retention, low). The rest rejected with reasons in the triage log. followup_review_recommended: true (patched medium 2, low 15): no real model has answered a follow-up (the OpenRouter key is blocked for agents, Issue #9), so how a real model handles an off-topic, test-like or injected question, and how often its output passes `validate_follow_up`, is unverified. Real-call check once a key is set: `python -m app.ai.cli config edit <id> --prompt debrief_follow_up=1` (with the narration prompts), measure and pin, lock a Class session, finish a game, ask through `POST /api/debriefs/{id}/follow-up`, then `SELECT outcome, request->>'prompt', response FROM llm_call WHERE purpose = 'debrief_follow_up'`.

**Verification.**
- Backend after the last patch: full suite `--maxprocesses=8` 3004 passed (106 s); `ruff check`, `ruff format --check` clean. Migration 0113 up and down in `test_migrations`.
- Frontend: typecheck, Vitest (55 files, 785 tests), `lint:colours`, `check:copy`; `next build` in the lane image build.
- Playwright on the lane stack (8081), rebuilt after the last change, `--workers=4`: `debrief-follow-up` (320, 360, 1440 px with axe), every `debrief-*`, `homes`, `student-home`, `live-updates`, `game-end`, `order-confirm`, `week-advance`, `game-card`, `order-field`, `seat-status`, `guided-week`: 141 of 141.
- Failed once, passed after a fix: `debrief-follow-up` under `--workers=4` (the dev narration's process-wide mock outage, fixed with `outage_here`); `test_content` and `test_lock` once, when a fixture deleted version 2 from shared test databases (fixed).
- Tests over 1 s: `tests/debrief/test_follow_up.py::test_a_student_asks_bounded_follow_up_questions` 6.5 s alone, about 12 s under the full run (one 14-Uke game carries every case). `tests/debrief/test_narration.py` was not changed to share one game: its tests take the function-scoped `klass`/`_empty` fixtures that empty the database per test, so sharing a module-scoped game is not cheap; its times are 5.1, 3.0, 1.3 and 1.3 s alone (8.6, 3.8, 1.8, 1.7 s in 9.14's run).

**Residual risks.** No real-provider run (above). No total per-Student cap (deferred). Names typed with other spellings (no diacritics, nicknames) are not scrubbed. Draft copy and hint templates await review.
