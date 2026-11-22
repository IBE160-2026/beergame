---
title: 'Story 10.7: Read the Replay walkthrough'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'e4be86d02127ef7dc33f744ec4afdf1aba9c6100'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-6-close-unfinished-replays-at-the-test-deadline.md'
  - '{project-root}/.docs/implementation-artifacts/spec-9-14-read-ai-narration-that-only-connects-computed-facts.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A Replay with no moments (fewer than ten own Orders) is not tested end to end.
    evidence: |-
      Reachable only with a Lecturer-set Replay scenario under ten Weeks (engine allows weeks from 1).
      The code path exists (narrate stores an empty line without a call; the walkthrough answers
      moments [] and narration null; the page shows copy.noMoments), but every test Replay has ten
      Weeks. Settle with a short-Replay case once the main test is split.
    location: >-
      backend/app/modules/replay/walkthrough.py narrate / frontend/src/modules/replay/walkthrough-page.tsx Moments
    severity: low
---

<intent-contract>

## Intent

**Problem:** «Gå til gjennomgangen» on «Replay er ferdig» leads to `/spill/<id>/gjennomgang`, which does not exist: the Student cannot see their Replay beside their Class game.

**Approach:** `modules/replay` gets a walkthrough: `GET /api/me/games/{game_id}/walkthrough` built from the stored facts sets of the Replay Seat and of the Student's own Class game Seat (`games.service.fact_set`, unchanged `analysis.facts`), the Week rows of both Games (Decision log `state_seen`), moments rendered by `analysis.moments.render` with the pinned templates, and an AI line from one idempotent `llm-batch` job (shared `app.ai.text.worded`, purpose `replay_walkthrough`, `analysis.validate_ai_text` + the walkthrough's own code renderer). A record `replay_walkthroughs` stores both `fact_set_id`s and the line fixed at the first ready view. The web page shows Totalkostnad, one Netto lager chart with the Replay and the Class game (grey) on one Uke axis with «Vis som tabell», «Ikke like for like.» with its reasons, and the moments; pending, ready, code-fallback, mostly-AI, closed and not-finished states.

## Boundaries & Constraints

**Always:** `modules/replay` reaches other modules only through `games.service`, `games.commands`, `sessions.service`, `progress.service`, `content.service` and `app.ai.{text,budget,gateway}` (AD-6; the import test is widened to that). Own game only through `games.service.student_game`. Facts never rebuilt; every number the api's, from the stored Week rows or the facts set (AD-7, AD-10, NFR-9). Pending judged on database time only (finish Week's `created_at` vs `now()`, Issue #63). The job: ids only, queueing lock `replay-walkthrough:<game>`, stores once per Replay facts set (`replay_narrations`, unique, immutable), emits `user:<owner>`, never retries a call. Only the Replay's own Student reads it (403 `forbidden` for anyone else, staff and Admin included). AI text marked only by `ai_generated` («KI-generert, kan ta feil:»). UI copy in `nb.ts` (`replay` section), draft lines in `open-assumptions.md`. No text ranks, praises or says which run was better.

**Never:** no change to `analysis.facts` or its rules; no rating (10.8); no sweep re-enqueue of a lost job (the wait limit falls back to code); no LLM call on the request; no game per test; no screenshots.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ready, AI on | finished Replay, narration stored | `state: ready`, Replay weeks/total, Class game weeks/total, 2 moments, narration `ai_generated` true; record stored | — |
| Pending | AI on, no narration row, finish < wait ago (db time) | `state: pending`, `retry_after_seconds`, nothing else; no record | page: «Gjennomgangen lages.» + Skjelett, refetch on `user:` and after `retry_after_seconds` |
| Wait passed / AI off / rejected / failed | no AI narration in time | `state: ready`, narration = code text, `ai_generated` false | no prefix |
| First view fixes the line | record exists, AI text stored later | same line as first view | — |
| Mostly AI | Class game Seat < 10 Student Orders | `mostly_ai: true`, `class_game: null`, ≥ 3 Replay moments with patterns/mechanism | page states the Class game was played mostly by AI players |
| Closed Replay | `end_reason = test_deadline` | 409 `replay_closed` | page shows Story 10.6's closed message |
| Not finished | running Replay | 409 `replay_not_finished` | page line + link to the Replay |
| Not the owner | other Student, staff, Admin, unknown/Class game id | 403 `forbidden` | access-denied page |

</intent-contract>

## Code Map

- `backend/app/modules/replay/{service,repo,models,routes,jobs,README.md}` -- `replays` table, `repo.replay_owner`, finish hook pattern `_record_replay_step`, route error style (`error_response`).
- `backend/app/modules/debrief/narration.py` -- pattern to mirror: `enabled_pin`, `_defer_on_finish`, `_validator`, `narrate` via `ai_text.worded`, `fact_lines`; `debrief/service.py:636 _moments`, `:753 _rendered` (pinned moment templates, pattern set of `stored.patterns_version`), `:722 _narration` (first-view fixing).
- `backend/app/analysis/{moments.py render, narration.py validate_ai_text/render_output/AiTextOutput/NARRATION_TEMPLATES, facts.py FactSet/MIN_STUDENT_ORDERS}` -- read-only.
- `backend/app/ai/{text.py worded, purposes.py, seed.py MOCK_SPEC, prompts/hashes.json}`, `backend/ai-configs/mock.json`, `backend/tests/ai/{conftest.py,test_prompt_files.py}` -- new purpose lists.
- `backend/app/modules/games/{service.py fact_set/decision_log/get_game/student_game/database_now/on_game_finished, repo.py finished_student_seats (finish Week = `game_weeks.finished`)}` -- add `finished_age`.
- `backend/app/modules/sessions/service.py:3140 DEBRIEF_AI_TEXT_PIN`; `backend/app/platform/config.py` (placeholder settings), `platform/events/registry.py` (command topics).
- `backend/tests/replay/test_finish.py`, `tests/debrief/test_explanation.py played/play_own_week/OWN_ORDERS`, `tests/analysis/test_moments.assert_every_number_from_the_facts`, `tests/test_imports.py:69`, `tests/test_migrations.py` (HEAD 0117).
- Frontend: `components/charts/net-over-game.tsx` (add a grey comparison series), `components/net-over-game-chart.tsx` (toggle/table pattern), `components/skeleton.tsx`, `modules/debrief/ai-text.tsx` (`DebriefText`, `AiNote`), `modules/replay/{replay-end,replay-closed,api}.tsx/ts`, `modules/identity/homes.ts walkthroughPath`, `app/(app)/spill/[gameId]/regler/page.tsx` (route pattern), `modules/games/api.ts myGameKey` (`["games","mine",id]` is invalidated by `user:`), `lib/api/topics.ts`, `copy/nb.ts`, e2e `replay-close.spec.ts` (stub pattern).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0118_replay_walkthrough.py`, `replay/models.py` -- `replay_narrations(fact_set_id pk, text, ai_generated, llm_call_id, created_at)` and `replay_walkthroughs(replay_game_id pk, user_id, class_session_id, replay_fact_set_id, compared_game_id, compared_fact_set_id, narration_text, narration_ai_generated, narration_llm_call_id, created_at)`, both immutable (trigger), marking check.
- `backend/app/ai/{purposes.py,seed.py,prompts/replay_walkthrough/v1.md,prompts/hashes.json}`, `backend/ai-configs/mock.json` -- purpose `replay_walkthrough` (1 attempt, not a player); the zero-config seed derives a new config row with it (Story 2.2 `config.derive`).
- `backend/app/platform/config.py` -- `replay_walkthrough_wait_seconds` placeholder 45.
- `backend/app/modules/games/{service,repo}.py` -- `finished_age(game_id)`: database now minus the finish Week's `created_at`, None when not finished.
- `backend/app/modules/replay/walkthrough.py` (new) -- finish hook (defer job when the Replay's pin is on), `narrate(game_id)`, `code_output`, `walkthrough(user, game_id)`, `Unavailable`; `replay/schemas.py` (new) the out models; `routes.py` the GET; `jobs.py` the task; `registry.py` `replay.store_narration` → `user`; README.
- `backend/tests/replay/test_walkthrough.py` (new) -- one Class session (14-Uke Class game, two Students: one with own Orders, one mostly AI), two Replays of 10 Uker: golden numbers vs `seat_weeks`, record with both ids, pending → job (mock) → AI line, outage fallback, first view fixes, mostly AI, AI off (code), closed, not finished, refused readers, hook defers once. `test_imports.py`, `test_migrations.py`, `tests/ai/*` lists.
- Frontend: `components/charts/net-over-game.tsx` (+`compare`), `modules/replay/{walkthrough-page.tsx,walkthrough-chart.tsx,walkthrough.ts,api.ts}`, `app/(app)/spill/[gameId]/gjennomgang/page.tsx`, `copy/nb.ts`, `open-assumptions.md`, api client; Vitest for the model and chart.
- `frontend/e2e/replay-walkthrough.spec.ts` (new) -- stubbed pending, ready (AI), code fallback and mostly-AI at 320/360/1440 with axe; closed and not-finished states; real api refusal for another Student and Admin.

**Acceptance Criteria:**
- Given a finished Replay, when its Student opens «Gå til gjennomgangen», then the page shows Totalkostnad, one chart with the Replay and Class game Netto lager on one Uke axis with «Vis som tabell», «Ikke like for like.» with the three reasons, and one or two moments from their own Replay Orders; no ranking or praise.
- Given the walkthrough data, then a golden test asserts every number equals the `seat_weeks` rows of the two Games and the record stores both `fact_set_id`s.
- Given a finished Replay with Debrief AI text on, when it finishes, then one job is deferred on `llm-batch`; its accepted text shows with «KI-generert, kan ta feil:»; a rejection, failure, AI off or the wait limit shows the code text unmarked.
- Given the pending, ready and code-fallback states at 320/360/1440 px, then axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Four layers (sonnet; the story uses the LLM): blind hunter, edge-case hunter, verification gap, intent alignment. Every hand-back failed; findings were read from `review-{blind,edge,verification,intent}-10-7.md` in the scratchpad.
- verdicts: 39 findings — high 0, medium 1, low 28, false 10, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind 1) `NetOverGame` passes synthetic first/last points to `weekLabels` — `weekLabels` reads only the first and last Uke, so the labels are the same; its own test still covers 1/12/24/36.
  - `[low]` `[patch]` (blind 2) `RuntimeError` on a compared facts set mismatch, a permanent 500 — `_record` now reads the compared Seat by the Replay's Role, the Role every later view reads, so the two reads cannot differ.
  - `[low]` `[patch]` (blind 3) «Kostnad så langt» vs Totalkostnad off by one — false in effect (`state_seen.total_cost` includes the Uke's own cost); the golden test now also asserts the last row equals Totalkostnad.
  - `[low]` `[patch]` (blind 4) pending refetch waits the whole `retry_after_seconds` — `pendingRefetch` caps it at 10 s; Vitest.
  - `[low]` `[reject]` (blind 5) pending is time-based, a lost job waits the full limit — by design: the wait limit (45 s placeholder) is the lost job's fallback; no sweep re-enqueue.
  - `[low]` `[reject]` (blind 6) an AI line stored after the first ready view is paid and never shown — the first view fixes the line, as the Debrief's narration (9.14); only reached when the job runs past the wait limit.
  - `[low]` `[reject]` (blind 7) list of missing backend tests — (c) false: the finish deferral is asserted in the main test; (d)/(f) the deferred no-moments case; (e) unreachable (a Replay starts only with an own game); (a)/(b)/(g) small.
  - `[low]` `[reject]` (blind 8) e2e 403 on a made-up id proves no ownership — the real other-Student, Lecturer and Admin refusals are in `test_walkthrough.py`; the e2e checks the deployed route.
  - `[low]` `[patch]` (blind 9) silent empty cells for the shorter run — they print «–» (`copy.noWeek`).
  - `[false]` `[reject]` (blind 10) grey line contrast; one-point compare not drawn — `ink-muted` is a text colour held to text contrast; a one-Uke Class game does not exist.
  - `[low]` `[reject]` (blind 11) every GET recomputes — bounded: the facts are stored once, a pending page polls at most every 10 s for 45 s.
  - `[low]` `[reject]` (blind 12) no indexes on cascading FKs; `""` sentinel — one row per Replay; cascades are rare deletes.
  - `[low]` `[patch]` (blind 13) `ViewError` statuses undocumented — `documented(401, 403, 404, 409)`, client regenerated.
  - `[false]` `[reject]` (blind 14) the line is caption-size and muted — the Debrief's step 4 line has the same treatment (`07-debrief.png`).
  - `[medium]` `[patch]` (edge 1) the AI line may cite facts the page does not show — `_fact_lines` offers and `_validator` accepts only the two moments ranked first (`_top`), which every walkthrough shows.
  - `[low]` `[patch]` (edge 2) «Din ordre» for the Class game may show an AI player's Order — the column reads «Ordre, Klassespill».
  - `[low]` `[patch]` (edge 3) = blind 2.
  - `[false]` `[reject]` (edge 4) `_record` None gives the own Student 403 — unreachable: `replay.start` requires `student_game`.
  - `[false]` `[reject]` (edge 5) `moment_text.render` ValueError — pinned content versions never change; the Debrief's step 4 reads the same way.
  - `[low]` `[patch]` (edge 6) open-assumptions says "no line" for mostly AI — reworded: no grey chart line, the tying line stays.
  - `[false]` `[reject]` (edge 7) the demand reason shown although demand may be equal — the story names it as a reason; every Replay draws a fresh seed.
  - `[low]` `[reject]` (edge 8) = blind 6.
  - `[low]` `[patch]` (edge 9) = blind 13.
  - `[low]` `[reject]` (edge 10) = blind 12.
  - `[low]` `[reject]` (edge 11, claim) no `games.service.finished_age` — the existing `finished_at` and `database_now` in one session give the same database-time age; the fix would be a spec edit.
  - `[false]` `[reject]` (edge 12, claim) later views do not re-derive through `student_game` — the compared game is chosen through it at the first view and cited by id after (AD-7).
  - `[low]` `[patch]` (verification 1) the moment ranking is not pinned — the test computes the expected two ids by the rule and asserts the code line ties them; the mostly-AI case asserts all moments by Uke.
  - `[low]` `[defer]` (verification 2) a Replay without moments is untested end to end — deferred (frontmatter).
  - `[low]` `[patch]` (verification 3) the `user:` invalidation of the walkthrough key is not pinned — `topics.test.ts` asserts it.
  - `[low]` `[reject]` (verification other 1) "the record tells no one" asserts the registry only — the style of the other registry asserts.
  - `[low]` `[reject]` (verification other 2) `narrate` guards untested — covered one hop earlier by the hook test.
  - `[low]` `[reject]` (verification other 3) `RuntimeError`/None branches untested — unreachable after the blind 2 patch / by `replay.start`.
  - `[low]` `[reject]` (intent 1) the job's queue key is the Game, not the `fact_set_id` — the facts set does not exist inside the finishing transaction; storage is keyed by it.
  - `[false]` `[reject]` (intent 2) the record's timing — it stores both `fact_set_id`s at the first ready view, before any data is shown.
  - `[low]` `[reject]` (intent 3) mostly AI drops the whole Class game side — recorded decision: the comparison is the Class game side.
  - `[false]` `[reject]` (intent 4) no new config row — the zero-config seed derives a new row with the purpose (`config.derive`, Story 2.2); production uses `config edit`.
  - `[low]` `[reject]` (intent 5) = blind 6.
  - `[low]` `[reject]` (intent 6) Playwright on stand-ins — as Stories 10.5/10.6; the real data path is `test_walkthrough.py`.
  - `[false]` `[reject]` (intent 7) scope additions — `replay_not_finished` is the page's need; docs are draft copy and ownership.

## Design Notes

One chart carries both «a chart of the run» and «the comparison on one axis» (`09-alle-sider.png`): the Replay's Netto lager as `NetOverGame` draws it (line + area) and the Class game's as a thin `ink-muted` line, x from Uke 1 to the longer run; the table gives both runs' Netto lager, Din ordre and Kostnad så langt. Moments: the facts give three; the two shown are ranked pattern-first, then later cost, then Week (shown by Week); mostly AI shows all three. The code line cites the top two (`narration-orders` + `narration-supply-line` of the larger supply line), the same choice the mock answers. The job is keyed by the Game in the queue (the facts set does not exist inside the finishing transaction) and by the Replay's `fact_set_id` in storage.

## Verification

**Commands:**
- `uv run pytest tests/replay tests/test_imports.py tests/test_migrations.py tests/ai -q` -- pass
- `npm run typecheck && npx vitest run src/modules/replay src/components/charts` -- pass
- full gate per runbook before commit

## Auto Run Result

Status: done

**Summary.** `GET /api/me/games/{game_id}/walkthrough` (`modules/replay/walkthrough.py`, route `getMyReplayWalkthrough`) for the Replay's own Student only (403 `forbidden` for anyone else; 409 `replay_closed` for a Replay Story 10.6 closed, `replay_not_finished` before the end). It answers both runs of the Student's Role from the Decision log (`state_seen`: Netto lager, Order, Kostnad så langt), each Totalkostnad from the stored facts sets (`games.service.fact_set`, `analysis.facts` unchanged), and the Replay moments rendered by `analysis.moments.render` with the pinned templates: the two ranked first (pattern, later cost, Uke), every one when the Class game Seat has fewer than 10 Student Orders (`mostly_ai`, Class game left out). The game compared with comes only from `games.service.student_game`. The first ready view stores `replay_walkthroughs` (both `fact_set_id`s and the line shown then). Narration: a finish hook defers one `llm-batch` job (`replay.narrate_walkthrough`, lock `replay-walkthrough:<game>`) when the session's pinned Debrief AI text is on. The job calls `app.ai.text.worded("replay_walkthrough", …)` with `analysis.validate_ai_text` (restricted to the two shown moments) and the walkthrough's own code renderer, stores the line once in `replay_narrations` and emits `user:<id>`. While it is live and within `replay_walkthrough_wait_seconds` (placeholder 45) of the finish (database time) the answer is `pending`. After that, or with AI text off, a rejection or a failure, the code line shows unmarked. New purpose, prompt `replay_walkthrough/v1.md` (locked), mock config/seed (the seed derives a new config row through `config.derive`). Web page `/spill/<id>/gjennomgang`: totals, one `NetOverGame` chart with the Class game as a grey `compare` line, legend in words, «Vis som tabell» (both runs' Netto lager, Ordre, Kostnad så langt), «Ikke like for like.» with three reasons, the line (AI marked through the Debrief's `DebriefText`/`AiNote`) and the moments. Pending is «Gjennomgangen lages.» in a Skjelett of the chart, refetched on `user:` and at most every 10 s. Mostly AI, closed and not-finished states.

**Files.** Backend: `migrations/versions/0118_replay_walkthrough.py` (new); `modules/replay/{walkthrough,schemas}.py` (new), `{models,routes,jobs}.py`, `README.md`; `ai/{purposes,seed}.py`, `ai/prompts/replay_walkthrough/v1.md` (new), `ai/prompts/hashes.json`, `ai-configs/mock.json`; `platform/config.py` (wait placeholder), `platform/events/registry.py`. Tests: `tests/replay/test_walkthrough.py` (new), `tests/test_imports.py` (replay may use `content.service` and `app.ai.text`), `tests/test_migrations.py`, `tests/ai/{conftest,test_prompt_files}.py`. Frontend: `app/(app)/spill/[gameId]/gjennomgang/page.tsx`, `modules/replay/{walkthrough-page,walkthrough-chart}.tsx`, `walkthrough.ts`, `walkthrough.test.ts` (new); `modules/replay/api.ts`; `components/charts/net-over-game.tsx` (`compare`), `charts.test.tsx`; `lib/api/topics.test.ts`; `copy/nb.ts` (`replay.walkthrough`); regenerated `lib/api/{openapi.json,schema.ts}`; e2e `replay-walkthrough.spec.ts` (new). Docs: `epic-10-context.md` (recompiled: planning docs were newer), `ARCHITECTURE-SPINE.md` (walkthrough owned by `replay`), `open-assumptions.md` (draft copy).

**Decisions the founder would otherwise take.** (1) One chart carries both the run and the comparison (`09-alle-sider.png`): the Replay coloured, the Class game grey on one Uke axis to the longer run. (2) Two moments shown, ranked pattern-first, then later cost, then Uke. With a mostly-AI Class game, all three, and the whole Class game side (total, grey line, reasons) is left out with a sentence. (3) The line cites only the two shown moments; the code line is `narration-orders` of the two plus the supply line of the one with more on the way. (4) The line is fixed at the first ready view; an AI line stored later is not shown to that Student (as the Debrief 9.14). (5) Pending lasts until the line is stored or 45 s after the finish (placeholder); no sweep re-enqueue. (6) The queue lock is keyed by the Game (no facts set exists inside the finishing transaction); storage is keyed by the Replay's `fact_set_id`. (7) The walkthrough lives in `modules/replay` (spine row updated, not `debrief`); the import test lets `replay` use `content.service` and `app.ai.text`. (8) The table column reads «Ordre», not «Din ordre» (a KI-spiller may have ordered in the Class game); «–» marks Uker the shorter run lacks. (9) Three «Ikke like for like.» reasons, the third gives both runs' Uke counts. (10) All page copy beyond «Gjennomgangen lages.» and «Ikke like for like.» is draft copy (`open-assumptions.md`). (11) Implemented in this context, not by a sub-agent (runbook); four sonnet review layers. (12) Real-call check (Issue #9): built and tested against the mock only; no real provider call was made (no key, no cloud). A config needs `python -m app.ai.cli config edit <id> --prompt replay_walkthrough=1`, then measure and pin, before a real call can be checked.

**Review.** 39 findings: 13 patched (1 medium: the line restricted to the shown moments; low: the compared Seat read by the Replay's Role, poll cap 10 s, «–» cells, `404` documented, column «Ordre», doc wording, and test gaps for ranking, last-row total and the `user:` key), 1 deferred (no-moments Replay end to end), the rest rejected with reasons above. `followup_review_recommended: false` (one medium patched, no high).

**Verification.** Full backend suite `--maxprocesses=8` after the last change: 3148 passed, 4 skipped (134.6 s). ruff format/check clean on changed files. Frontend typecheck, full Vitest 1038 passed, `lint:colours`, `check:copy`, `next build` (image) passed. Playwright `--workers=4` after the stack rebuild: replay-walkthrough (14, axe at 320/360/1440 in pending, ready and code fallback, plus 360 px on table and mostly-AI), replay-close, replay-finish, replay-play, replay-start, class-session-replay, debrief-{explanation,moments,narration,bill,chain,open,shared}, game-end, graph-over-table, homes, student-home: 143 passed, none flaky. New test over 1 s: `tests/replay/test_walkthrough.py::test_the_walkthrough_sets_the_replay_beside_the_class_game` (about 13–15 s: a 14-Uke Class game, three Replays, two played ten Uker; same setup as the Debrief narration test). No test failed once and passed on rerun.

**Residual risks.** Draft copy. A late AI line is paid but not shown to a Student who already saw the code line. Real provider not exercised (Issue #9). The no-moments path is untested end to end (deferred).