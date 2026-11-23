---
title: 'Story 11.6: Write long answers with autosave'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'b077c4e953670012726577e790fd07e95f70b02c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-4-answer-multiple-choice-items-with-autosave.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-5-answer-table-and-number-interactive-items.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Long-answer items of the open Individual test show only their title and `save_answer` refuses every long answer (422), so the Student cannot write the answers that carry most of the weight (FR-51, FR-52, FR-73, AD-10, UX-DR65).

**Approach:** Extend `tests.commands._valid` to take a long answer as text, stored as typed; render each long item as a multi-line Tekstfelt (`TextAreaField`) whose label is the item's question from the pinned question set, with phone-only larger-screen advice above it; autosave through Story 11.4's `useAutosave` with a debounce: every keystroke is kept on the device at once, the save goes when typing pauses, the field loses focus or the page is hidden.

## Boundaries & Constraints

**Always:**
- Save: a long item's value is a JSON string of at most `LONG_ANSWER_MAX = 20_000` characters (`""` = emptied), stored byte-for-byte as sent (no trim, no normalisation). Refused with 422 `invalid_answer`: non-string, longer, containing `\u0000` (Postgres JSONB cannot hold it) or a lone surrogate (not UTF-8 encodable). Same path, lock, revision and refusals as 11.4. Adapted items (11.7) will reuse this validation.
- No LLM call and no score for long answers: `tests.scoring.score_answer` stays None for `long`. No answer text in any log line (the command logs none; a test captures logs during a save and asserts the text is absent).
- Item out unchanged: long items carry `title` (from the attempt's pinned question set version), `options: []`, `table`/`column` null, the stored `answer`. The title is shown as-is (no trimming or rewording) — this is how the item tagged `explanation-wording` shows the Explanation's wording unchanged, whatever its type.
- Frontend `LongItem` (`frontend/src/modules/tests/long-item.tsx`): advice line `copy.long.largerScreen` above the field, visible below `md` only (`md:hidden`); `TextAreaField` id `test-<itemId>`, label = item title, `rows` ≥ 8, `maxLength` = `LONG_ANSWER_MAX`; `SaveLine` under it («Lagret 21:14» polite, failure line, refusal). Focus never moves on save.
- Autosave: `useAutosave` gets `write(value)` (revision +1, draft kept in `lib/drafts.ts` at once, send scheduled after `LONG_ANSWER_PAUSE_MS`, restarting on each keystroke) and `flush()` (send now; on `blur`, on `visibilitychange` to hidden and on `pagehide`, and on unmount with a pending pause). While a pause is pending, a finished save does not send the newer text early. `LONG_ANSWER_PAUSE_MS = 1_500` in `autosave.ts`, the one place to configure it, marked `[PLACEHOLDER]`. Choice/table/number keep sending at once via `pick`.
- Session expired (401 `session_expired`) on a save: the draft stays, the failure line shows, no timed retry, and the test query is invalidated so the app's existing 401 handler sends the Student to «Logg inn» with the way back; on return `initial()` finds the draft above the stored revision and sends it (a higher revision).
- Copy in `nb.ts` (`tests.individual.long`): `largerScreen` [ASSUMPTION] «Langsvar er lettere å skrive på en større skjerm, som en PC. Du kan likevel skrive og lagre her.»

**Never:** No LLM, no score, no right/wrong state; no submit (11.10); no Adapted items (11.7); no migration or new table; no change to the demo Class; no answer text in logs; no character counter or rich text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Save text | `"  Linje 1\n\nLinje 2  "` rev 1 | 200, stored exactly as sent | — |
| Emptied | `""` rev 2 | stored `""` | — |
| Too long | 20 001 chars | nothing stored | 422 `invalid_answer` |
| Not text | `null`, `12`, `["a"]`, `{"t":"a"}` | nothing stored | 422 `invalid_answer` |
| NUL / lone surrogate | `"a\u0000b"`, `"\ud800"` | nothing stored | 422 `invalid_answer` |
| Typing | keystrokes, no pause | draft per keystroke, no PUT until pause | — |
| Pause / blur / hidden | after typing | one PUT with the latest text and revision | — |
| Save fails | 503 / offline | failure line, draft kept, retry 5 s / online | retry |
| Session expired | 401 | failure line, draft kept, to «Logg inn»; after login sent with higher revision | — |
| Reload with draft | draft rev > stored | draft text shown and sent | — |

</intent-contract>

## Code Map

- `backend/app/modules/tests/commands.py` (`_valid` ~199) -- add `long` branch; constant `LONG_ANSWER_MAX` (export, docstring).
- `backend/app/modules/tests/schemas.py` (`TestAnswerIn` ~271) -- docstring: a long item's text.
- `backend/app/modules/tests/scoring.py` -- unchanged (long → None); add a test asserting it.
- `backend/app/modules/tests/README.md` -- long answers in the save section.
- `backend/tests/individual_test/test_answer.py` (~135) -- drop the «long arrives with 11.6» 422 assertion.
- `backend/tests/individual_test/test_long_answer.py` (new; reuse `opened`, `put`, `stored`, `code`, fixtures `klass`/`clock`/`_empty` like `test_interactive.py`) -- matrix rows, logs, score None, the explanation-wording item's title equals the pinned version's title.
- `frontend/src/modules/tests/autosave.ts` -- `LONG_ANSWER_PAUSE_MS`, `LONG_ANSWER_MAX` (mirror of the api's limit, for `maxLength`).
- `frontend/src/modules/tests/use-autosave.tsx` -- `write`, `flush`, pause timer; 401 handling (`isSessionExpired` from `@/lib/api/client`).
- `frontend/src/modules/tests/long-item.tsx` (new) -- `LongItem`.
- `frontend/src/modules/tests/individual-test-page.tsx` (`Items` ~147) -- render `LongItem` for `type === "long"`; docstring.
- `frontend/src/copy/nb.ts` (~2826) -- `long.largerScreen`.
- `frontend/src/modules/tests/autosave.test.ts` -- constants sanity if needed.
- Reuse: `components/text-area-field.tsx` (unchanged), `SaveLine`, `lib/drafts.ts`.
- `frontend/e2e/individual-test.spec.ts` -- per width 320/360/1440: long item typing (no PUT before pause), saved after pause, blur saves, save-failed, restored draft after reload, advice visible only on phones, axe in each state; session-expired 401 then draft sent after return; live: write one long answer, reload shows it.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/tests/commands.py` -- long validation -- the save path refuses long answers today.
- `backend/tests/individual_test/test_long_answer.py`, `test_answer.py` -- cover the matrix and logs.
- `frontend/src/modules/tests/{autosave.ts,use-autosave.tsx,long-item.tsx,individual-test-page.tsx}`, `copy/nb.ts` -- the item and debounced autosave.
- `frontend/e2e/individual-test.spec.ts` -- states per width with axe, 401, live.

**Acceptance Criteria:**
- Given an open attempt with a long-answer item, when it shows, then the question (the pinned set's title, unchanged) is the label above a multi-line Tekstfelt; the explanation-wording item's text equals the pinned version's title.
- Given the Student types, when typing pauses, the field loses focus or the page is hidden, then one save with a rising revision goes and «Lagret HH:MM» shows in the polite status region, focus staying in the field.
- Given a failed save or an expired session, then the text stays on the device, the failure line shows, and after a reload or login it is sent with a revision above the stored one.
- Given a phone width (320/360), then the larger-screen advice shows above the field and saving works; at 1440 it is not shown.
- Given 320/360/1440 px, then typing, saved, save-failed and restored-draft states pass axe.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, since the change touches the answer write path and the autosave timing). Generated `openapi.json`/`schema.ts` and this spec were left out of the review diff.
- verdicts: 33 findings — high 0, medium 0, low 21, false 10, maybe-false 2
- findings:
  - `[low]` `[patch]` Blind: the unmount flush did nothing while a save was in flight, and `live=false` stopped the follow-up send, so text typed during the last save stayed on the device only — the save-completed handler now sends the newer text after unmount too (only the pause gates it).
  - `[low]` `[reject]` Blind: `pagehide`/`visibilitychange` flushes use a fetch without `keepalive` — `visibilitychange` to hidden fires first and its request is usually under way; the draft stays on the device and goes on the next visit; `keepalive` caps bodies at 64 kB, which a 20 000-character answer can pass, so it needs a second send path.
  - `[low]` `[patch]` Blind: after a 401 `session_expired` whose re-read succeeds (a login in another tab) the entry stayed «Ikke lagret» with no retry — the timed retry now runs as for any failure; an ended session still leaves for «Logg inn» on the re-read.
  - `[low]` `[patch]` Blind: the 20 000 limit is two literals with nothing tying them — the backend test pins `LONG_ANSWER_MAX == 20_000` and the e2e asserts the field's `maxlength="20000"`. (`maxLength` counts UTF-16 units, Python code points: the field is stricter, never looser.)
  - `[low]` `[reject]` Blind: `maxLength` truncates a paste silently, no counter — 20 000 characters is about 3 000 words, far past any answer here; the spec's Never excludes a counter.
  - `[low]` `[reject]` Blind: the phone advice is not `aria-describedby` on the field; the label is the whole question — the advice sits directly above the field in reading order; `TextAreaField` owns its `aria-describedby` (shared component); the question as label is the 11.4 choice pattern (legend = title).
  - `[low]` `[patch]` Blind: the no-score test could pass vacuously; the log check covered only the 200 path — the test now asserts long items exist, and refused saves run under `capture_logs` with their text asserted absent.
  - `[false]` `[reject]` Blind: no hook unit tests, no submit/deadline tests, request size vs body limits — the hook paths run in e2e (pause, blur, hidden, `pagehide`, unmount, reply during typing, 401, retry); submit is 11.10 and the deadline refusal is 11.4's tested path; no proxy or app body limit applies to this route (searched), and 20 000 characters of JSON is at most about 60 kB.
  - `[low]` `[reject]` Blind: a live refetch with a higher stored revision from another device replaces the text being typed; draft copy and the pause have no follow-up issue — 11.4's recorded decision (the highest revision wins); revisions rise per keystroke, so only a second device that typed more wins; the founder decisions go to the team lead's report (no issue edits from this lane).
  - `[low]` `[patch]` Edge: unmount flush during an in-flight save — same fix as the Blind row.
  - `[low]` `[patch]` Edge: 401 with a successful re-read never retried — same fix as the Blind row.
  - `[maybe-false]` `[reject]` Edge: a pasted U+0000 or a lone surrogate gets 422, which drops the draft and reverts to the stored text — whether a textarea yields either from a real paste is unverified; if it does, the loss is the text since the last save (seconds), so at most low; a sanitiser adds a branch for a case not shown to occur.
  - `[low]` `[reject]` Edge: `pagehide` fetch without `keepalive` — same as the Blind row.
  - `[low]` `[patch]` Edge: the two limits can drift — same fix as the Blind row.
  - `[low]` `[patch]` Edge (claim): «saved on unmount with a pending pause» was false during an in-flight save — same fix as the Blind row; now true.
  - `[low]` `[patch]` Verification: `pagehide` and the unmount flush had no test — new e2e: a `pagehide` sends at once with the page's clock stopped, and in-app navigation home sends text still in its pause.
  - `[low]` `[patch]` Verification: the «still typing» guard in the save-completed handler had no test — new e2e holds the first PUT, types more, lets the reply come inside the pause and asserts no second PUT until the pause ends.
  - `[low]` `[patch]` Verification: front-end and api limits not tied — same fix as the Blind row.
  - `[low]` `[reject]` Verification (other): the new Vitest case runs functions the diff did not change — it pins that a long text with blank lines and an empty text round-trip through the draft unchanged, which 11.6 relies on; harmless.
  - `[maybe-false]` `[reject]` Verification (other): NUL or a lone surrogate from the field drops the draft — same as the Edge row.
  - `[false]` `[reject]` Intent: page behaviour mostly verified against stand-ins — the repo's pattern; the live test writes a long answer on the stack and reads it back after a reload.
  - `[low]` `[patch]` Intent: `pagehide` and unmount untested — same fix as the Verification row.
  - `[false]` `[reject]` Intent: the redirect to «Logg inn» is the existing global handler — by design (UX-DR59's one handler); the e2e asserts the page lands there and the draft goes after login.
  - `[false]` `[reject]` Intent: `aria-live` not asserted — `role="status"` is polite by definition; `SaveLine` is 11.4's.
  - `[low]` `[patch]` Intent: «label above» asserted by name only — the e2e now checks the label's box is above the field's.
  - `[false]` `[reject]` Intent: the Explanation's wording is checked at the api only — the page renders `item.title` as the label and the e2e asserts the exact accessible name; the api test asserts every title equals the pinned version's.
  - `[low]` `[reject]` Intent: the debounce is a code constant, not runtime configuration — the frontend's configuration pattern (`RETRY_MS`, `STALE_MS`, …); one exported constant marked `[PLACEHOLDER]`; recorded as a founder decision.
  - `[false]` `[reject]` Intent: «higher revision» after login is the draft's own — the draft's revision is above the stored one, which is what the server's rule compares; a further increment would change nothing.
  - `[low]` `[patch]` Intent: only one PUT's logs captured — same fix as the Blind log row.
  - `[false]` `[reject]` Intent: no assertion that no LLM is called — nothing on the save path reaches `app.ai`; `score_answer` returning None is asserted.
  - `[false]` `[reject]` Intent: the 20 000 limit and NUL/surrogate refusals go beyond the story — a store needs a bound; NUL cannot be held in JSONB (it would be a 500); recorded as a founder decision.
  - `[false]` `[reject]` Intent: no unit tests for the hook — same as the Blind coverage row.
  - `[false]` `[reject]` Intent: the 422 assertion moved out of `test_answer.py` — informational; the long-answer refusals now live in `test_long_answer.py`.

## Design Notes

- Revision per keystroke (as for choices): the draft on the device always holds the newest text with its revision; the server keeps the highest. A long essay stays far below the 1 000 000 revision cap.
- Debounce sits in the hook, not the component, so 11.7's Adapted items (answered as long answers) inherit it.

## Verification

**Commands:**
- `uv run pytest tests/individual_test -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests` -- pass
- `npx playwright test e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Student writes the long answers of the open Individual test in a multi-line Tekstfelt whose label, above the field, is the item's question as the pinned question set words it (so the item tagged with the Explanation's wording shows it unchanged). On a phone (below `md`) the advice «Langsvar er lettere å skrive på en større skjerm, som en PC. Du kan likevel skrive og lagre her.» shows above the field. Every keystroke is kept on the device (`lib/drafts.ts`) at once; the text is saved through Story 11.4's `save_answer` path when typing pauses for `LONG_ANSWER_PAUSE_MS` (1 500 ms, `[PLACEHOLDER]`, in `autosave.ts`), when the field loses focus, when the page is hidden or left, and when the item leaves the page. «Lagret 21:14» is announced in the polite status line and focus stays in the field. A failed save shows «Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.» and is retried; an ended session keeps the draft, the test is read again and the app goes to «Logg inn»; back on the page the draft goes with its revision above the stored one. `commands._valid` takes a long answer as a string of at most 20 000 characters, stored exactly as sent (`""` once emptied); a non-string, a longer text, a NUL or a lone surrogate is 422 `invalid_answer`. No LLM call, no score (`score_answer` stays None for long answers), no answer text in any log line.

**Files.**
- `backend/app/modules/tests/commands.py`: `LONG_ANSWER_MAX`, `_text`, the `long` branch of `_valid`.
- `backend/app/modules/tests/{schemas.py,README.md}`: docstring; the long-answer section.
- `backend/tests/individual_test/test_long_answer.py` (new, 4 tests); `test_answer.py` (the old 422 assertion moved).
- `frontend/src/modules/tests/long-item.tsx` (new): `LongItem`.
- `frontend/src/modules/tests/use-autosave.tsx`: `write` (debounced), `flush` (blur, hidden, `pagehide`, unmount), the pause guard after a reply, the ended-session re-read.
- `frontend/src/modules/tests/{autosave.ts,autosave.test.ts,individual-test-page.tsx}`, `frontend/src/copy/nb.ts`: constants, a draft case, the item on the page, the advice copy; generated `lib/api/{openapi.json,schema.ts}` (docstring only).
- `frontend/e2e/individual-test.spec.ts`: long answer per width (typing, saved after the pause, save-failed on leaving the field, restored draft after a reload, advice on phones only, label above, `maxlength`, axe in each state); hidden page and pause with the page's clock stopped; `pagehide`, a reply during typing and in-app navigation; ended session and login; live write + reload.

**Review.** Four sonnet reviewers, 33 findings: high 0, medium 0, low 21, false 10, maybe-false 2. Patched (low entries): the follow-up send after unmount, the retry after a 401 whose re-read succeeds, the limit pinned on both sides, refused saves checked for logged text, a non-vacuous no-score test, and e2e for `pagehide`, unmount, a reply during typing and the label's position. Rejected the rest with reasons in the triage log (no `keepalive`, no counter, no describedby on the advice, the two-device rule of 11.4, a NUL/surrogate sanitiser). Nothing deferred.

**Follow-up review: not recommended.** Patched: high 0, medium 0, low 14 rows (7 entries).

**Verification.**
- Backend: full suite `--maxprocesses=8`: 3272 passed, 4 skipped; `ruff check` and `ruff format --check` clean. New tests over 1 s under parallel load: `test_long_answer.py::test_anything_but_text_within_the_limit_stores_nothing` about 1.1 s (nine refused saves on one opened attempt); the others 0.8–1.0 s.
- Frontend: `tsc` clean, Vitest 1070 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt after the review patches), 111 passed: individual-test (long answers at 320/360/1440 with axe), homes, student-home, order-field, order-confirm, week-table, game-start, guided-week.
- Screenshots at 320 and 1440 px of a saved long answer, checked by eye: advice over the question on the phone only, label above the field, «Lagret 21:14» under it, no sideways scroll.

**Decisions taken for the founder.**
- The question is the field's label (as a choice item's question is its legend); no separate prompt text exists in the draft content.
- Long answers hold at most 20 000 characters; `""` is the emptied answer; NUL and lone surrogates are refused (JSONB cannot hold NUL).
- The pause before a save is 1 500 ms, one exported constant in `autosave.ts` (`[PLACEHOLDER]`), the frontend's configuration pattern; a revision rises per keystroke.
- The phone advice shows below the `md` breakpoint (768 px), copy `[ASSUMPTION]` draft.
- A 401 on a save keeps the draft and re-reads the test, so the app's one session-ended handler takes the Student to «Logg inn».

**Personal data.** No new table. Long answers are stored in `test_answers` (noted by 11.3 for Story 15.2's registry); they are text a User wrote.

**Residual risks.**
- A tab closed within the pause may cancel the last request (no `keepalive`); the text stays in the device's draft and goes on the next visit from that device.
- Whether a browser paste can put a NUL or lone surrogate into the field is unverified; if so, the 422 reverts to the last stored text.
- The implementation was done in the main context, not a subagent, per the team lead's brief.
