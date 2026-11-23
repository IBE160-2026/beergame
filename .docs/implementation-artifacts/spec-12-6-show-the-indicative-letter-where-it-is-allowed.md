---
title: 'Story 12.6: Show the Indicative letter where it is allowed'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'e819dc0340afe2f067378216caea004774382de9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-12-5-flag-feedback-and-read-assessments-as-staff.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The AI assessment shows a weighted total but no Indicative letter: a Lecturer cannot choose whether the A–F letter is shown, unavailable, or left to each Student; an Institution cannot forbid it; and no Student can turn it on for their own view (FR-56, AD-12, UX-DR66).

**Approach:** Three letter settings and editable thresholds per Class session on `assessment_switches` (saved by «Lagre Klasseøkt», pinned with the switch at the Test deadline); a `no_letter` mark on `institutions` (Admin Bryter on the Institution list, audited, via `identity.service`); the Student's own opt-in on `ai_assessments`; the letter derived only by `analysis.indicative_letter` and handed out only by `assessment.service.letter_for(…, reader=…)`, which decides per reader.

## Boundaries & Constraints

**Always:** Settings: `all` (shown to everyone in the Class session), `student_choice` (default), `unavailable`. The setting and thresholds change only on «Lagre Klasseøkt», only by owners (`ai_assessment.change`), and only while the «KI-vurdering» switch can change (`_ai_assessment_open`); once pinned, 409 `ai_assessment_pinned` with the field. Thresholds: whole percent of the total's maximum, lower bounds for A, B, C, D, E (1–100, strictly falling), F always 0; defaults from config (placeholders `90,80,60,50,40`); stored when a Lecturer saves them and pinned at the lock with whatever is in force; read-only (409 `letter_thresholds_locked`) once any Test attempt of the Class session exists, judged under the save's row lock. Institution `no_letter` on: effective setting is `unavailable` everywhere, only that option can be chosen (409 `letter_unavailable` otherwise), the block says why, and no letter is derived even where a Student had opted in. No letter for any state but `ready`. A Student's opt-in is stored on their own assessment, changeable only while the effective setting is `student_choice` and the view is `ready` (else 409 `letter_not_available`), never in any staff/Admin response. `letter_for` readers: `student` (own view: `all`, or `student_choice` and opted in), `staff` (only `all`), `export` and `zip` (never), `report` (only when `requested_by_student` and the Student's own rule gives one). The letter's label everywhere: AI-generated indication, not a grade. Copy drafts in `nb.ts` marked `[ASSUMPTION]`. Migration 0206 revises 0205. `assessment` imports no new module.

**Never:** No letter in Completion (Epic 13 asserts that), no change to scores, totals, states or flags, no audit of a Student's own opt-in, no letter on the Klasseøkt list, no letter for a Control test beyond the ordinary rules.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Save setting | owner, switch open, `letter_setting` | stored; `ai_assessment.letter.setting` reads it | Assistant: 403; pinned: 409 `ai_assessment_pinned` |
| Save thresholds | owner, no attempt yet | stored; read back | bad order/range: 422 `invalid_session_values` `{letter_thresholds: …}`; attempt exists: 409 `letter_thresholds_locked` |
| Institution forbids | `no_letter` on | `letter.setting` `unavailable`, `letter.forced` true; Student `letter` null, staff `letter` null | sending `all`/`student_choice`: 409 `letter_unavailable` |
| Student opt-in | `student_choice`, ready | `PUT …/test/assessment/letter {"on": true}` → view with `letter.value` | not ready / `all` / unavailable: 409 `letter_not_available`; other's session: 403 |
| Setting `all` | ready | Student and staff views carry the same letter | — |
| Incomplete | any setting | no letter | — |
| Staff never sees opt-in | `student_choice`, opted in | staff `letter` null, no `chosen` key anywhere in staff JSON | — |
| Admin switch | `PUT /api/admin/institutions/{id}/no-letter {"on": bool}` | `InstitutionOut.no_letter`; one audit row per change | unknown: 404; non-Admin: 403 |

</intent-contract>

## Code Map

- `backend/app/analysis/letter.py` (new) -- `LETTERS`, `indicative_letter(total, thresholds, out_of=100)`, `judge_thresholds`; pure, `Fraction`.
- `backend/migrations/versions/0206_indicative_letter.py` (new) -- `assessment_switches.letter_setting` (text, default `student_choice`, check), `letter_thresholds` (JSONB null); `ai_assessments.letter_chosen` (bool default false); `institutions.no_letter` (bool default false); trigger `assessment_switches_pinned` extended to the two letter columns.
- `backend/app/modules/assessment/{models,service}.py` -- columns; `Switch.letter_setting/letter_thresholds`; `set_letter(…)`, `pin_switch` stores thresholds in force; `copy_switch` copies letter values; `LetterRules`, `letter_for(rules, *, total, total_max, ready, opted_in, reader, requested_by_student=False)`; `set_letter_choice(attempt_id, on)`; `AssessmentRecord.letter_chosen`.
- `backend/app/platform/config.py` -- `indicative_letter_thresholds: str = "90,80,60,50,40"`.
- `backend/app/modules/identity/{models,repo,service,schemas,routes}.py` -- `no_letter` column, `set_institution_no_letter` (audited `institution.no_letter_changed`), `institution_forbids_letter(id, session=)`, `InstitutionOut.no_letter`, `PUT /api/admin/institutions/{id}/no-letter`.
- `backend/app/modules/sessions/{service,schemas,routes}.py` -- `AiAssessmentOut.letter` (`LetterSettingOut`: setting, stored, forced, thresholds, thresholds_open, can_change); `save_session(letter_setting=, letter_thresholds=)`; `register_attempts_exist`; `letter_rules(s, class_session_id)` for `tests`; errors `LetterUnavailable`, `LetterThresholdsLocked`.
- `backend/app/modules/tests/{assessed,routes,schemas,commands or service}.py` -- `MyAssessmentOut.letter` (`MyLetterOut`: setting, chosen, value), `StaffAssessmentOut.letter: str | None`; `set_letter_choice`; route `PUT /api/me/class-sessions/{id}/test/assessment/letter`; register attempts-exist reader.
- `backend/app/platform/events/registry.py` -- `assessment.set_letter_choice`: {user}.
- Tests: `backend/tests/analysis/test_letter.py` (golden, every bound), `backend/tests/assessment/test_letter.py` (matrix, `letter_for` every reader), `tests/assessment/test_flags.py` key set, `tests/test_migrations.py` head 0206, identity institution tests.
- Frontend: `src/modules/assessment/letter-block.tsx` (Lecturer: Valgknapper + thresholds), `letter-control.tsx` (Student Bryter + letter line), `switch-block.tsx`, `assessment-page.tsx` (letter beside the total for both viewers), `api.ts`; `src/modules/sessions/class-session-page.tsx` (drafts sent on save); `src/modules/admin/{institution-list.tsx,api.ts}` (Bryter column); `src/copy/nb.ts`; `e2e/ai-assessment-letter.spec.ts` (new).

## Tasks & Acceptance

**Execution:**
- Backend as in the Code Map; `npm run api:generate` after the schema change.
- Tests: every matrix row; `letter_for` for `student`, `staff`, `export`, `zip`, `report` (by Student, by staff); exact key set of the staff view; copy_from carries setting and thresholds (FEATURE_RERUN on); audit row on the Institution switch.
- Frontend: Lecturer block, Student control, Admin column; Vitest for threshold parsing and letter text; Playwright for the three settings and the Student control at 320/360/1440 with axe and 44 px targets.

**Acceptance Criteria:**
- Given a Lecturer on the Klasseøkt «KI-vurdering», when they pick one of three Valgknapper and press «Lagre Klasseøkt», then the setting is stored and its scope is stated in help text.
- Given `student_choice` and a ready assessment, when the Student turns «Veiledende bokstav» on, then the letter shows beside the total with «KI-generert indikasjon. Ikke en karakter.», and off again hides it.
- Given the Admin turns the Institution's Bryter on, then the Klasseøkt offers only «Ikke tilgjengelig» with the reason, and no view shows a letter.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (sonnet; four reviewers for a data-model and access change). Findings were read from the reviewers' files in the scratchpad.
- verdicts: 33 findings — high 0, medium 1, low 20, false 9, maybe-false 0, plus 3 descriptive intent notes (counted in low/false)
- findings:
  - `[low]` `[patch]` Blind/Edge: `indicative_letter` snapped the total with `limit_denominator`, so 89.99996 read as 90 — it now reads the total as its decimal string (`Fraction(str(total))`); a non-finite total raises ValueError; tests just under a bound added.
  - `[medium]` `[patch]` Blind/Edge/Verification: switches pinned before 0206 got NULL bounds, so their letters would follow later config changes — 0206 backfills pinned rows with the placeholder bounds before the new trigger.
  - `[low]` `[reject]` Blind/Edge: bounds the Lecturer sends equal to the defaults are not stored, so a config change between the first attempt and the Test deadline would move read-only bounds — needs a deploy-time config change inside that window; the pin stores the bounds in force; the fix needs a new pin path at attempt open.
  - `[low]` `[patch]` Blind/Verification: `LetterBlock.refusal` was dead — removed; the refusals show on the save row.
  - `[low]` `[reject]` Blind: an old opt-in reappears after the Institution ban is lifted or the setting goes back to `student_choice` — the opt-in is the Student's own choice, never cleared by others' settings; recorded as a decision.
  - `[false]` `[reject]` Blind/Intent: export, ZIP and report readers have no caller — no export, ZIP or report exists at this point (Epic 13); the AC asks `assessment.service` to decide for them, tested per reader.
  - `[low]` `[reject]` Blind: the Lecturer's letter changes are not audited — consistent with the switch (Story 12.1); only Admin actions are audited (AD-15).
  - `[low]` `[patch]` Blind/Verification: the config validator was untested and `int()` accepted `+9`, `1_0`, non-ASCII digits — ASCII digits only now; a `Settings` test for a bad and a good value.
  - `[low]` `[patch]` Blind: `PUT …/test/assessment/letter` lacked `Cache-Control: no-store` — added and asserted.
  - `[low]` `[patch]` Blind: the letter appeared without an announcement — wrapped in `aria-live="polite"`.
  - `[false]` `[reject]` Blind: `register_attempts_opened` could be missed silently — `tests.assessed` registers at import with the attempt reader the jobs need; `test_the_bounds_are_read_only_once_a_test_attempt_is_opened` fails without it.
  - `[low]` `[patch]` Blind/Verification: the pin trigger was tested only for `letter_setting` — a direct `letter_thresholds` UPDATE now raises too. Branchy loop and component tests: `[low]` `[reject]` (style; Playwright covers the components).
  - `[false]` `[reject]` Edge: `letter_for` can raise for total > total_max — `total_score` bounds each share to its weight, so total ≤ total_max by construction.
  - `[false]` `[reject]` Edge: `class_facts` missing fails open — a Class session's class row cannot be missing (foreign key).
  - `[low]` `[reject]` Edge: race between the view check and `set_letter_choice` — only the Student's choice is stored; every read applies the current rules, so nothing is shown that is not allowed.
  - `[low]` `[reject]` Edge: no event when the Institution's mark flips — open pages refresh on their next read; emitting to every session of an Institution adds a fan-out for a rare Admin action.
  - `[low]` `[reject]` Edge: bounds beyond ±1000 get a generic 422 — the same pattern as `required_share_percent`.
  - `[low]` `[patch]` Edge: switching off showed the letter until the answer came — the letter follows the optimistic Bryter.
  - `[false]` `[reject]` Edge/Verification: the label differs from the spec AC's wording — the AC paraphrased; the copy follows the spine's disclosure («Teller ikke. Ingen karakter.»); fixing means editing this spec.
  - `[low]` `[patch]` Verification: no `letter_for` row for a Student-requested report without opt-in (and staff without opt-in) — rows added.
  - `[low]` `[patch]` Verification: copy from a pinned source unasserted — the copy test now pins the source and checks the bounds survive a changed default.
  - `[low]` `[reject]` Intent: the Student control and staff letter are browser-tested on stand-ins only — the real path is api-tested; the same pattern as 12.2–12.5.
  - `[false]` `[reject]` Intent: copy runs with `FEATURE_RERUN` off — `copy_from` refuses before `copy_switch` while the flag is off.
  - `[low]` `[reject]` Intent: `staff_list` not asserted for the choice — `AssessmentRowOut` has no letter field.
  - `[false]` `[reject]` Intent: thresholds A to E rather than A to F — F's bound is 0 by definition (decision recorded).

## Design Notes

- Thresholds are percent of `total_max`, so a selection whose weights do not sum to 100 still maps right; `indicative_letter` compares `total * 100 >= bound * out_of` exactly.
- The setting freezes with the switch at the original Test deadline (12.1's pin), the same moment as everything else the assessment depends on; the Institution switch stays live as the data protection officer's override. Recorded as a decision.
- Staff view: `StaffAssessmentOut` is built from the Student's view without `letter`, then given `letter_for(reader="staff")`, so the opt-in never crosses.
- F's bound is 0 and not editable; the five bounds A to E are the Lecturer's.
- A Student's opt-in survives later setting changes and an Institution ban; it shows again only where the rules allow it.

## Verification

**Commands:**
- `uv run pytest tests/analysis/test_letter.py tests/assessment tests/admin tests/test_migrations.py -q --maxprocesses=8` -- pass
- `npm run typecheck && npx vitest run src/modules/assessment src/modules/admin src/modules/sessions` -- pass
- `npx playwright test e2e/ai-assessment-letter.spec.ts e2e/ai-assessment.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The AI assessment now has an Indicative letter (A–F) where it is allowed.
- **Klasseøkt.** The «KI-vurdering» block has «Veiledende bokstav» with three Valgknapper: «Vist for alle», «Studenten velger» (the default) and «Ikke tilgjengelig». The help text states the scope of the chosen setting. Under it are the lower bounds of A to E, in whole percent of the total's maximum and strictly falling; F is what is left under E. Both apply on «Lagre Klasseøkt», by owners only, while the switch can change. The bounds become read-only (409 `letter_thresholds_locked`) once any Test attempt exists. The Test-deadline lock pins the setting and the bounds in force with the switch, and the trigger refuses later changes.
- **Institution ban.** The Admin's Bryter on «Alle Institusjoner» (`PUT /api/admin/institutions/{id}/no-letter`, audited `institution.no_letter_changed`, `identity.service`) makes every Class session of the Institution read `unavailable`. The block says why and only «Ikke tilgjengelig» can be chosen (409 `letter_unavailable`). No letter is derived anywhere.
- **Student.** On a ready «KI-vurdering» where the setting is «Studenten velger», a Bryter turns the letter on for their own view only (`PUT …/test/assessment/letter`, stored as `ai_assessments.letter_chosen`). The letter shows beside the total with «KI-generert indikasjon. Teller ikke. Ingen karakter.». With «Vist for alle» the Student and the staff read the same letter.
- **Single gate.** `assessment.letter_for(…, reader=)` decides who gets a letter: the Student's own view; the staff only when it is shown to everyone; never an export or a ZIP; a report only when the Student asks. The letter comes only from `analysis.indicative_letter`, and never for an assessment that is not ready.
- **Copy.** «Lag kopi» copies the setting and the stored bounds.

**Process.** Implemented in the build agent's own context, as the lane brief requires; review fixes were applied by the build agent.

**Decisions taken here (founder would otherwise):**
- **Setting freezes at the Test deadline.** The setting changes until the original Test deadline, with the switch, and is pinned with it. The Institution Bryter stays live as the override after that.
- **Bounds are percent of the maximum.** They are whole percent of the total's maximum (`total_max`), not points. F is fixed at 0, and only A–E are edited.
- **Placeholder defaults.** The defaults are `90,80,60,50,40`, from `INDICATIVE_LETTER_THRESHOLDS`, placeholders until a Control test. A pin stores the bounds in force. Rows pinned before 0206 get these placeholders.
- **Opt-in persists.** A Student's opt-in survives setting changes and bans. It shows again only where allowed.
- **Not audited.** Neither the Lecturer's letter changes (as with the switch) nor the Student's opt-in is audited.
- **Draft copy.** All new copy is draft `[ASSUMPTION]` in `nb.ts`, under `assessment.letterBlock`, `assessment.letter` and `admin.institutions.noLetter`.

**Files.**
- `backend/app/analysis/letter.py` (new): `indicative_letter`, `judge_thresholds`, `parse_thresholds`.
- `backend/migrations/versions/0206_indicative_letter.py` (new).
- `backend/app/modules/assessment/{models,service}.py` and its README: the columns; `set_letter`, `letter_rules`, `letter_for`, `set_letter_choice`; pin and copy.
- `backend/app/modules/identity/{models,repo,service,schemas,routes}.py`: `no_letter`, its Admin route and audit.
- `backend/app/modules/sessions/{service,schemas,routes}.py`: `AiAssessmentOut.letter`; `_judge_letter`; `letter_rules`; `register_attempts_opened`; the save fields and errors.
- `backend/app/modules/tests/{assessed,schemas,routes}.py`: `MyLetterOut`, the staff `letter`, the Student route, `attempts_opened`.
- `backend/app/platform/{config.py,events/registry.py}`.
- Tests: `tests/analysis/test_letter.py` and `tests/assessment/test_letter.py` (new). Also updated: `test_flags.py` (key set), `test_assess.py`, `test_ai_assessment_switch.py` and `test_migrations.py`.
- Frontend:
  - New: `src/modules/assessment/{letter.ts,letter-block.tsx,letter-control.tsx,letter.test.ts}`.
  - Changed: `switch-block.tsx`, `assessment-page.tsx`, `api.ts`, `src/modules/sessions/{class-session-page.tsx,api.ts}`, `src/modules/admin/{institution-list.tsx,api.ts}` and `src/copy/nb.ts`.
  - Api client regenerated.
  - E2E: `e2e/ai-assessment-letter.spec.ts` (new). `class-session-lock.spec.ts` and `class-session-choices.spec.ts` were updated, because the letter radios stay open after the start.

**Review.** Four sonnet reviewers. Patched: 1 medium (backfill of pinned rows) and 11 low. Rejected: 9 false and 9 low, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** Patched entries: high 0, medium 1, low 11.

**Verification.**
- **Backend.**
  - Full suite with `--maxprocesses=8`: 3824 passed, 4 skipped, 1 failed. The failure, `tests/sessions/test_orders.py::test_an_order_already_placed_is_not_placed_again`, is unrelated; it passed alone (5/5).
  - `ruff check` and `ruff format` are clean.
- **Frontend.** `tsc` is clean. Vitest: 1188 passed. `lint:colours` and `check:copy` pass. `next build` passed in the compose image.
- **Playwright** on the lane-3 stack (8082), `--workers=4`, after the patches:
  - 130 passed across `ai-assessment-letter`, `ai-assessment`, `ai-assessment-switch`, `admin-institutions`, `class-session`, `class-session-lock`, `class-session-rerun`, `tilrettelegging`, `homes`, `order-field`, `week-table` and `game-start`. The 3 `class-session-lock` failures were fixed, and the spec passed 12/12 on rerun.
  - The other `class-session-*` specs: 86 passed. The one stale radio count was fixed and passed.
  - The letter spec runs the three settings and the Student control at 320/360/1440 with axe and 44 px checks.
- **Matrix audit.** Every row has a passing test in `tests/assessment/test_letter.py`.
- **New tests over 1 s.** The api tests in `tests/assessment/test_letter.py` take about 2 s each, from the shared locked-session fixture (as in 12.5). The Klasseøkt Playwright test takes about 8 s.

**Residual risks.**
- The default bounds are placeholders. A config change between the first attempt and the Test deadline would move bounds that are already shown as read-only.
- Open pages do not refresh at once when the Institution's mark flips.
- Exports, ZIPs and reports do not exist yet. Epic 13 must call `letter_for` with its reader.

**Personal data.**
- No new table.
- New column `ai_assessments.letter_chosen`: the Student's own choice, tied to `user_id` on that row. Lane 1's registry (Story 15.2) should list it with the `ai_assessments` row.
- `institutions.no_letter` is not personal data.
