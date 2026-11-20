---
title: 'Story 5.18: Create a Class session from an earlier one (cut list, FEATURE_RERUN)'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '99cf629c38c01a55dfa2b0b2bb9277622ee32691'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-17-let-students-choose-class-game-and-seat.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred:
  - summary: >-
      At 360 px the page heading breaks inside a generated Class name («okt-» / «1534091»).
    evidence: |-
      Seen by the visual reviewer on the Klasse page of a fresh test Class; the page shell's h1 uses overflow-wrap:anywhere. Not caused by Story 5.18.
    location: >-
      frontend/src/modules/identity/page-shell.tsx:60
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Lecturer who ran the exercise last year must set every Game setting, AI choice and limit up again for this year's Class session (FR-66, UJ-9).

**Approach:** Behind `FEATURE_RERUN` (`get_settings().feature_rerun`, already in config and compose, default on) the Klasse page offers «Lag fra en tidligere Klasseøkt»: the Lecturer picks one of the Class sessions they may see (any of their Classes, archived ones included) and `sessions.service.copy_from` creates a new Class session in this Class with the source's editable settings, which then opens prefilled on the Klasseøkt.

## Boundaries & Constraints

**Always:**
- Migration 0043: `class_sessions.copied_from UUID NULL` (FK `class_sessions.id` ON DELETE SET NULL) and `effort_level_replaced TEXT NULL` (the source's level name the new config does not offer). Existing rows NULL.
- `GET /api/classes/{class_id}/class-sessions/copy-sources` (`class_sessions.manage` on the target Class, 403 otherwise): items `{id, class_id, class_name, number, start_at, archived}` of every Class session in a Class the User is staff of (repo query scoped by `authz.classes_visible_to`, names via `classes.service.list_classes`), newest first (UUIDv7 id desc). 422 `feature_disabled` `{"rerun": "feature_disabled"}` while the flag is off.
- `POST /api/classes/{class_id}/class-sessions/copy` body `{source_id, keep_seed: bool = false}` → 201 `ClassSessionOut`. Order: route policy 403; flag off 422 `feature_disabled` `{"rerun": "feature_disabled"}`; target not managed by the User, or source not readable (`class_sessions.read`) or unknown/malformed → 403 `forbidden`; target archived → 409 `class_archived`; copied settings the engine refuses → 422 `invalid_settings` (fields as in Story 5.3).
- `copy_from(user, source_id, target_class_id, *, keep_seed, now)`, one transaction, mirrors `create_session`: new id; `game_settings` = the source's stored `class_sessions.game_settings` (never `snapshot`), with `demand_seed` = the source's if `keep_seed` else a fresh `new_seed`; a capacity is dropped (None) while `FEATURE_CAPACITY` is off and both views set off while `FEATURE_INFO_VISIBILITY` is off; then `engine.validate` with the flags must return nothing. `debrief_mode` and `inactivity_limit_hours` copied. Model config = `config.active_default()` (never the source's) with its budget row; AI mode = source's, except `llm` with no active default becomes `rule_based` (as create). With `llm`: Effort level = source's level when the new config offers it, else the config's default and `effort_level_replaced` = source level name (only when the source had one). Not copied: dates, Lab hours, Roster, allocation (`allocation_method` default `random`, no draft), obligatory (False) and its share (config default). `copied_from` = source id. Emits `session:<id>`; registry command `sessions.copy_from` `{session}`.
- `ClassSessionListOut.rerun_enabled` (flag). `ClassSessionOut` adds `copied_from: {id, class_name, number} | null` (null when the source is gone or the User may no longer read it) and `effort_level_replaced: {name, label} | null` (label from the source's config level, else null). The Klasseøkt shows both only while `saved_at` is null.
- Screens: Klasse page (flag on, `canCreate`): under «Lag Klasseøkt» a Lenke «Lag fra en tidligere Klasseøkt» opens an in-place panel (focus to its heading): SelectField «Klasseøkt å kopiere» listing «{klasse}, Klasseøkt N, start {dato}» / «… uten startdato», a Bryter «Behold frøet for etterspørselen», the line «Datoer, Labtimer, Klasselisten, fordelingen og Obligatorisk kopieres ikke.», primary «Lag kopi», secondary «Avbryt»; no source → «Du har ingen tidligere Klasseøkter.». Success opens `/klasseokter/{id}`. Klasseøkt: «Kopiert fra Klasseøkt N i {klasse}.» in place of «Alt er fylt ut med standardene.», and when replaced «Innsatsnivået {label} finnes ikke for den nye modellen. Klasseøkten bruker standardnivået {ny}.». Settings warnings show as Story 5.3 already does. Copy in `nb.ts`, new strings `[ASSUMPTION]`.

**Never:** No copy of the snapshot, model config, dates, Lab hours, Roster, allocation, obligatory mark or share. No change to `create_session` behaviour or the demo Class. No Epic 9–11 fields (they add theirs later). No edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Copy | source with changed settings, debrief personal, limit 30, dates, Lab hour, obligatory, confirmed allocation | new session: same settings, new seed, personal, 30, no dates/Lab hours/draft, not obligatory, default share, active default config + budget | — |
| Keep seed | `keep_seed: true` | seed equals source's | — |
| Other Class | source in Class A, target Class B (both owned) | created in B, `copied_from` names A | — |
| Not visible | source in a Class the User is not staff of | nothing stored | 403 `forbidden` |
| Assistant source | User is Assistant in source Class, owner of target | allowed | — |
| Target not owned | User only Assistant of target | nothing stored | 403 |
| Flag off | either route | nothing stored | 422 `feature_disabled` |
| Level gone | source `careful`, new default offers only `standard` | level `standard`, `effort_level_replaced` `careful` | — |
| No default | source llm, no active default | `rule_based`, `llm_unavailable` | — |
| Cut flags off | source with capacity, FEATURE_CAPACITY off | copy has no capacity | — |
| Locked source | source locked with snapshot | copy uses `game_settings`, unlocked | — |
| Archived | target archived | nothing stored | 409 `class_archived` |

</intent-contract>

## Code Map

- `backend/migrations/versions/0043_copied_from.py` -- new, revises 0042; `backend/app/modules/sessions/models.py:63` two columns.
- `backend/app/modules/sessions/service.py` -- `create_session:635` (pattern to mirror), `get_session:721` (add fields), `list_sessions:784` (`rerun_enabled`), `_class_for:624`, `classic_settings:315`/`new_seed`, `_problem:347` for `InvalidSettings`, `capacity_enabled:417`/`info_visibility_enabled:422`, `FeatureDisabled:295`. New section «Rerun (Story 5.18)»: `rerun_enabled`, `copy_sources`, `copy_from`.
- `backend/app/modules/sessions/repo.py` -- `insert_session:45`; new `copy_sources(s, user, class_ids)` modelled on `staff_sessions:99` (`_numbered`, `authz.classes_visible_to`).
- `backend/app/modules/sessions/schemas.py` -- `ClassSessionOut:150`, `ClassSessionListOut:236`; new `CopyIn`, `CopySourceOut`, `CopySourceListOut`, `CopiedFromOut`, `ReplacedLevelOut`.
- `backend/app/modules/sessions/routes.py` -- two routes next to `create_class_session:60` (declare before any `{session_id}` clash; paths are under `/classes/{class_id}`).
- `backend/app/ai/config` -- `active_default`, `offered_effort_levels`, `get(id).effort_level(name).label`; `budget.set_budget`.
- `backend/app/platform/events/registry.py:33` -- `sessions.copy_from`.
- Tests: new `backend/tests/sessions/test_rerun.py` (fixtures `klass`, `shared`, `second_class`, `two_levels` pattern from `tests/sessions/test_ai_mode.py:50`, flag via `monkeypatch.setenv("FEATURE_RERUN", …)` + `get_settings.cache_clear()`); `backend/tests/test_migrations.py:737` add 0043 (and `HEAD`).
- Frontend: regenerate `frontend/src/lib/api/{openapi.json,schema.ts}`; `frontend/src/modules/sessions/api.ts` (hooks); `class-sessions.tsx` (panel); new pure `rerun.ts` (+ `rerun.test.ts`) for source labels; `class-session-page.tsx:284` (copy lines); `frontend/src/copy/nb.ts` (`sessions.list.rerun`, `sessions.copied`); e2e `frontend/e2e/class-session-rerun.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Migration, models, repo, schemas, service, routes, registry, README -- behaviour above.
- `backend/tests/sessions/test_rerun.py` -- every matrix row.
- Frontend api regenerate, copy, Klasse page panel, Klasseøkt lines; Vitest of `rerun.ts`; e2e: fresh Lecturer, two Classes, source changed and saved; copy from the second Class keeps settings, shows «Kopiert fra …», «Lagre Klasseøkt» unchanged saves; flag-off answer rewritten shows no Lenke; axe at 360 and 1440 px.

**Acceptance Criteria:**
- Given the flag off, when the Klasse page renders, then no copy Lenke shows, and both routes answer 422 `feature_disabled`.
- Given a copy, when the Klasseøkt opens, then it is prefilled with the source's settings and AI choices, names its source, and «Lagre Klasseøkt» saves it unchanged (200), the settings passing the engine again.
- Given a replaced Effort level, when the Klasseøkt opens, then it says which level was replaced by which.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 40 findings — high 0, medium 1, low 31, false 8, maybe-false 0
- findings:
  - `[false]` `[reject]` blind: the replaced level falls back to `offered[0]`, not the config's default. `config.offered_effort_levels` documents the first offered level as the default; `create_session` relies on the same rule.
  - `[false]` `[reject]` blind: an empty `offered` leaves `level` None with `replaced` set. `active_default` only returns a config that offers a level here.
  - `[false]` `[reject]` blind: Debrief mode and Inactivity limit are copied unvalidated. The source row holds them under the same DB CHECKs the copy is inserted under.
  - `[low]` `[patch]` blind: source read and copy written in separate transactions (a source gone between gives an FK 500). Fixed: the source is read again inside the insert transaction with a share lock; gone → 403.
  - `[low]` `[reject]` blind: no index on `copied_from`. Class sessions are deleted only by a Class cascade; negligible, and 0043 already ran on the shared test databases.
  - `[low]` `[reject]` blind: `_copy_notes` reads on every GET; `effort_level_replaced` never cleared. Two cheap reads for copies only; the screen hides the notes after the first save; the stored values are provenance.
  - `[low]` `[reject]` blind: the source list is unbounded and includes never-saved sessions. Recorded design decision; a Lecturer has a handful of Classes.
  - `[false]` `[reject]` blind: `list_classes` may leave Classes out. It returns every Class the User is staff of, archived included, unpaged.
  - `[low]` `[patch]` blind: two sources can have identical labels. Fixed with the visual finding: options grouped by Class in `<optgroup>`.
  - `[low]` `[patch]` blind: copy-sources cache never invalidated. Fixed: «Lag Klasseøkt» and «Lag kopi» invalidate it.
  - `[low]` `[reject]` blind: `forbidden` and `feature_disabled` read «Prøv igjen». Both need access or the flag to change while the panel is open; `class_archived` has its shared message.
  - `[low]` `[patch]` blind: «Samme etterspørsel som forrige gang» assumes the same Class. Reworded to «Etterspørsel uke for uke»: «Den samme som i Klasseøkten du kopierer» / «Ny, med samme mønster».
  - `[low]` `[reject]` blind: missing tests (default not first, LLM source without level, copy of a copy, deleted old config, error messages, load failure, cache, admin caller). Guarded by documented invariants or plain fallbacks; the ones that matter are covered by patched rows.
  - `[low]` `[patch]` edge: source deleted between read and insert. Same entry as the transaction row.
  - `[low]` `[reject]` edge: stored settings that no longer parse give a 500. `GameSettings` reads every stored `schema_version`; such a row would break `get_session` too.
  - `[low]` `[patch]` edge: archived target with refused settings answered 422, not 409. Fixed by the same move: settings judged after `_writable`.
  - `[low]` `[reject]` edge: flag off and a malformed id answers 403. FR-5's one answer for ids that name nothing.
  - `[low]` `[patch]` edge: stale copy-sources cache. Same entry as the blind row.
  - `[low]` `[patch]` edge: no loading state in the panel. Added «Laster …».
  - `[low]` `[reject]` edge: `forbidden`/`feature_disabled` messages. Same as the blind row.
  - `[low]` `[patch]` edge (claim): no test with a confirmed allocation on the source. `changed_source` now stores a confirmed draft; the copy has none.
  - `[low]` `[patch]` intent A: warnings of copied settings untested. Added `test_a_copy_carries_the_engines_warnings_of_its_settings`; the screen shows `settings_warnings` as Story 5.3 does. Refusing invalid settings at copy time is kept (a prefilled screen cannot hold settings the engine refuses).
  - `[low]` `[reject]` intent B: the replaced-level sentence is never rendered in a browser. The page renders `copyLines` generically (the «Kopiert fra» line is rendered in e2e); the sentence is unit-tested.
  - `[false]` `[reject]` intent C: flag-off UI tested with a rewritten answer. The screen reads only `rerun_enabled`; the real flag is tested at the api, as in Stories 5.15–5.17.
  - `[low]` `[reject]` intent D: offer only sessions already run. Recorded design decision.
  - `[low]` `[reject]` intent E: the allocation method resets. Recorded design decision: the method is part of the allocation.
  - `[false]` `[reject]` intent F: no default → Rule-based. Same rule as «Lag Klasseøkt»; CHECK `ck_class_sessions_llm_has_config` allows nothing else.
  - `[false]` `[reject]` intent G: Roster untested. The Roster belongs to the Class; a session has none to copy.
  - `[low]` `[patch]` intent H: the docstring named «Epics 9 to 11». Now: Epic 5's settings only; later stories that own more add theirs.
  - `[low]` `[patch]` verification-gap: `copied_from` hidden from non-readers untested. Added `test_the_source_is_named_only_to_readers_of_its_class`.
  - `[low]` `[patch]` verification-gap: panel `invalid_settings` message untested (filed `defer`). Added an e2e test with a stubbed 422.
  - `[false]` `[reject]` verification-gap (other): order relies on UUIDv7. As every list in the module; pinned by a test.
  - `[low]` `[patch]` visual: panel heading styled like the field label. Now a heading with a hairline rule under it.
  - `[medium]` `[patch]` visual: option cut off at 360 px, losing the date. Options grouped by Class in `<optgroup>`, each «Klasseøkt N, start …».
  - `[low]` `[patch]` visual: «ventetid» and «fordelingen» do not match the screen. Now «Inaktivitetsgrense» and «Fordeling».
  - `[low]` `[patch]` visual: seed help covered one state and «frø» is jargon. Rewritten with one help line for both states.
  - `[low]` `[patch]` visual: mixed text sizes. The copied/not-copied lines use `text-body-phone`.
  - `[low]` `[patch]` visual: panel frame differed from the Canvas box. Now `border-ink-muted`.
  - `[low]` `[reject]` visual (optional): say on the Klasseøkt whether the demand was kept. The seed is in the settings; not asked by the story.
  - `[low]` `[defer]` visual: the h1 breaks inside a generated Class name at 360 px. Pre-existing page-shell behaviour; deferred.

The five reviewers finished, but their completion notices did not reach this builder; their reports were read from their transcripts. The visual reviewer stood in for the founder's eye check; the builder re-captured the panel at 360 px after the patches.

## Design Notes

Founder-level decisions taken here:
- Entry point is the Klasse page's create area (no IA row exists; the validation reports noted it). The source list covers every Class the User is staff of, archived included, since last year's Class is often archived.
- Sources readable by an Assistant lecturer may be copied (they «may see» them); the target needs ownership.
- The obligatory share is part of the obligatory mark and is not copied; the allocation method is part of the allocation and resets to random.
- Cut-list values whose flag is off now are dropped rather than refused, so a copy always succeeds when the engine accepts the rest.
- Provenance and the replaced level are stored (migration 0043) so the notice survives a reload; shown until the first save.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_rerun.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run build && npx playwright test` -- pass

## Auto Run Result

Status: done

**Summary.** Behind `FEATURE_RERUN` (already in config and compose, default on) a Faglærer can make a Class session from an earlier one.
- **Api:** `GET /api/classes/{id}/class-sessions/copy-sources` lists every session of every Class the User is staff of (`authz.classes_visible_to`, archived Classes included, newest first). `POST …/class-sessions/copy` `{source_id, keep_seed}` runs `sessions.service.copy_from`: the source's editable `game_settings` (never the snapshot), judged by the engine again, with a fresh seed unless kept; AI mode, Effort level, Debrief mode and Inactivity limit; the active default model config with its budget row. An Effort level the new config does not offer becomes its default and is stored in `effort_level_replaced`. Not copied: dates, Lab hours, Roster, allocation (method `random`), obligatory mark and share. Flag off: both routes 422 `feature_disabled` and `rerun_enabled` is false. Migration 0043 adds `copied_from` (FK, SET NULL) and `effort_level_replaced`.
- **Screens:** on the Klasse page the Lenke «Lag fra en tidligere Klasseøkt» opens a panel in place: a select grouped by Class, a Bryter «Etterspørsel uke for uke», what is and is not copied, and «Lag kopi». The new Klasseøkt opens prefilled with «Kopiert fra Klasseøkt N i {klasse}.» and, when replaced, «Innsatsnivået … finnes ikke for den nye modellen …», shown until the first save.

**Files.**
- `backend/migrations/versions/0043_copied_from.py` (new); `backend/app/modules/sessions/{models,repo,schemas,service,routes}.py`, `README.md`; `backend/app/platform/events/registry.py` (`sessions.copy_from`).
- Tests: `backend/tests/sessions/test_rerun.py` (new, 15 tests); `backend/tests/test_migrations.py` (HEAD 0043, 0043 folded into the 0037–0042 test).
- `frontend/src/lib/api/{openapi.json,schema.ts}` regenerated; `frontend/src/copy/nb.ts` (`[ASSUMPTION]` draft copy); `frontend/src/modules/sessions/{api.ts,rerun.ts (new),class-sessions.tsx,class-session-page.tsx}`; `rerun.test.ts` (new); `frontend/e2e/class-session-rerun.spec.ts` (new, 5 tests).

**Review.** 40 findings: medium 1, low 31, false 8. Patched: the source is read and its settings judged inside the insert transaction (gone → 403, archived → 409 first); copy-sources cache invalidated; a loading line; options grouped by Class; wording and visual fixes from the visual review; four test gaps closed (non-reader, confirmed draft on the source, warnings, refused-settings message). One low deferred (pre-existing h1 break). Rejections and reasons are in the triage log. Patched counts by entry verdict: medium 1, low 13.

**Follow-up review:** false. No high was patched and only one medium.

**Verification.**
- Backend: 2621 passed (81 s); ruff check and format clean. No new test over 1 s (slowest 0.8 s).
- Frontend: typecheck, Vitest 456 passed, `check:copy`, build. Full Playwright after the patches: 271 passed and 7 failed under load (admin-audit, roster-upload, roster-send, student-registration: the mail/load flakes seen in Story 5.17); all 7 passed on `--last-failed`. `class-session-rerun.spec.ts` 5/5.
- Migration 0043 is new; it ran once on the shared test databases and was not changed after.

**Residual risks.** The source list offers every session the Lecturer may see, unsaved ones too. The replaced-level sentence is checked by a unit test and the api test, not rendered in a browser. Refused settings stop the copy (422) instead of opening a screen with errors.

**Process note.** Per the autobuild runbook, the builder implemented the spec in its own context rather than in an implementation subagent, and applied the review patches itself. A fifth, visual reviewer stood in for the founder's eye check.
