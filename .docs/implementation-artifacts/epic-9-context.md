# Epic 9 Context: Debrief and Debrief quiz

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Students of a finished Class game write their own Explanation, then see the customer demand revealed, the whole four-Role chain with Order amplification, reflection questions, at least three of their own moments, the chain's bill, and pass a Debrief quiz, alone or in a Group debrief with an optional shared screen. The Debrief is built code-only first, so it works under any AI mode and with no LLM; AI narration and bounded follow-up are layered on top through the AI gateway and always fall back to code text. The epic owns `modules/debrief` (backend and frontend) and adds the quiz, sentence templates and Detected pattern definitions to `modules/content`, plus the shared facts, validator and renderer in `analysis/`, `ai/` and `modules/games` (`fact_sets`). Replay (Epic 10), the Individual test and Student report reuse these pieces.

## Stories

- Story 9.1: Compute the facts of a finished Game
- Story 9.2: Open the Debrief when the Class game has ended
- Story 9.3: Write the Explanation before the reveal
- Story 9.4: See the reveal of customer demand
- Story 9.5: Scrub the whole chain and see the amplification
- Story 9.6: Answer the reflection questions
- Story 9.7: See my own moments, rendered from the facts
- Story 9.8: See the chain's bill and finish the Debrief
- Story 9.9: Pass the Debrief quiz
- Story 9.10: Exclude a quiz question and see quiz attempts
- Story 9.11: Go through the Debrief together as a group
- Story 9.12: Continue alone when the group is not there
- Story 9.13: Show the Group debrief on a shared screen
- Story 9.14: Read AI narration that only connects computed facts
- Story 9.15: Ask bounded follow-up questions about my Game

## Requirements & Constraints

- **Debrief content:** reveals the demand series; Orders, inventory and backlog per Role over the Weeks (with text alternative); Order amplification from Retailer to Factory; per Student at least three own moments (Week, what they saw, what they ordered, later cost, matching Detected pattern and mechanism: delay, Supply line, demand information lost in orders; what the other Roles saw); the Student's Explanation beside the data (to that Student only). Every number matches the Decision log exactly. States that AI explanations can be wrong. Shows the share of chain Total cost incurred in AI-held Seats.
- **Detected patterns:** a closed list of three, worded as patterns and never as causes: an Order well above incoming orders after a shortage; a large Order while the Supply line already holds a lot; very low Orders after an overshoot. Thresholds are placeholders marked "to be reviewed by two lecturers before pilot".
- **Moments:** chosen by documented rules over the Decision log, only from Weeks with `decided_by = student`. A Seat with fewer than 10 such Orders gets no moments, the Debrief says the game was played mostly by AI players, and the Student is flagged out of SM-1 and SM-2; the Debrief can still be finished.
- **Explanation gate:** one Explanation per Student per Class session, stored once and unchanged (`409 explanation_exists`), written before any reveal. Demand, other Seats' data and later steps return `403 explanation_required` without it, checked in the API, not the UI. The number of Weeks is not gated once the game is finished.
- **Availability:** Debrief only for finished games (`403 debrief_not_open`); a Lecturer may hold all Debriefs until every Class game has ended (`403 debrief_held`), a setting frozen at the Start date. Release is a once-only, idempotent sweep action that notifies Students.
- **Quiz:** fixed single-choice questions, server-side scoring by answer key, one immutable `quiz_attempts` row per attempt, unlimited retries until the Test deadline (`409 test_deadline_passed`, read via `sessions.service.effective_test_deadline`), counts toward no score. Gate: `progress.has_step(debrief)` (`403 debrief_required`). Lecturers can exclude questions (not the last one) until the Test deadline; Assistant lecturers read only. Questions are placeholders until issue #16 delivers content.
- **Group debrief:** all joined Students share one step pointer; the step moves when all joined have finished it, or the opener moves on after a configured minimum wait (`409 too_early`). Writing, reflection, moments and quiz stay individual and on own devices. Dropout after 2 min silence, 48 h fallback to Personal debrief; a Class game with one active Student is always Personal. Every gate still holds in the fallback.
- **Shared screen:** shows only charts by Role, never names, Explanations, answers, moments or any free text; locked until all joined Students have sent their Explanation.
- **AI text:** no step ever waits on an LLM; the rendered text is fixed at a Student's first view. Marked «KI-generert, kan ta feil:» driven only by `ai_generated`. Follow-up declines off-topic questions, gives hints not model answers to test-like questions, closes when the Individual test opens or at the Test deadline, is rate limited (`429 rate_limited`), and is absent when Debrief AI text is off or no provider exists. Lecturer can switch Debrief AI text off per Class session before the Start date.
- **Copy:** Norwegian bokmål; ask why not who; second person; no praise, blame or exclamation marks; «Beer Game»/«bullwhip» allowed only in a post-reveal section of `nb.ts` that the CI copy check exempts. «Simulert» block never claims «optimal» or «fasit».
- **Accessibility:** WCAG 2.1 AA; Playwright + axe at 320, 360, 1440 px (200 % text on step 1); keyboard-operable; no page-level horizontal scroll; every chart has a table alternative; reduced motion respected.

## Technical Decisions

- **Pure analysis (AD-1):** `analysis` does no I/O, reads no clock, and uses no randomness. `analysis.facts(decision_log, seat, pattern_definitions)`, `analysis.render(fact_set, template_ids)`, `analysis.validate_ai_text(output, fact_set, templates)`, and the «Simulert, samme kunder» function (runs `engine.advance` over the stored demand series and settings; ordering parameters from configuration with Rule-based placeholders, issues #8, #17) are all pure. The web app computes none of these numbers.
- **Facts sets (AD-7, AD-14):** one `fact_sets(id, game_id, seat_id, analysis_version, payload)` row per Seat, created only through `games.facts.get_or_create(game, seat)`; consumers load by `fact_set_id` and never rebuild; payload holds ids, values and Roles only, no names. Chain-level part is identical for all four Seats. Fact ids are deterministic `<pattern>:<role>:<week>`; each occurrence carries `state_seen`, the Order, later cost and what the other Roles saw. Golden tests (addendum §B trace, a Takeover Game, a fully Rule-based Game) fix the sets; full branch coverage aimed for. `python -m app.sim facts <game_id>` prints them for simulation Games (AD-22).
- **LLM output boundary (AD-7):** the output schema references fact ids and sentence-template ids only; code renders every number and cause; any failure or rejection yields the code text as `{text, ai_generated: false, llm_call_id: null}`, never retried. A shared helper in `app/ai` takes validator and fallback renderer as arguments (`app/ai` imports only `platform`). `ai.run(purpose=debrief_narration | quiz_explanation | debrief_follow_up, budget_scope=<Class session>)`; each purpose needs a new model config row with a `prompts` entry, versioned prompt files. `modules/debrief` must never import `modules/players` (import-linter), and the whole Debrief must pass on a Rule-based Game with the mock provider off.
- **Narration timing:** generated on `llm-batch` in `worker-batch`, deferred at game finish through an `on_game_finished(hook)` in `games` `service.py` (the Debrief registers; `games` imports nothing from `debrief`), one idempotent job per Student keyed by `fact_set_id`, re-enqueued by the sweep if lost. Follow-up is the first Student free text sent to an LLM, so `platform/pii.terms(class_session_id)` now reads the whole Roster, only the gateway calls it.
- **Content versioning (AD-23, AD-4):** Detected pattern definitions, sentence templates, reflection questions and the quiz are immutable versioned records in `modules/content`; each is pinned at `sessions.lock` as a new entry in `SessionRuntime`'s open map, with the Debrief AI-text switch, with no change to the lock mechanism. Scored attempts store the quiz version. Quiz exclusions are a separate Class session row owned by `modules/debrief`, audited via `platform/audit`, never an edit of the content record.
- **Debrief writes (AD-21, AD-8):** `debrief.commands` (`open`, `join`, `save_explanation`, `complete_step`, `move_on`, `leave`, `finish`, `touch`, `open_personal_fallback`, `close_follow_up`) is the only writer; each locks the Debrief row and emits `debrief:<id>`, except `touch` (no lock, no event). Every command has a registry entry in `platform/events/registry.py`. Presence is server-side via an `on_heartbeat` hook added to `platform/events` on the 15 s SSE heartbeat. `debrief.rules.available(user, class_session)` reads Game status through `games.service`; the Debrief finds a Student's game only through `games.service.student_game`. Topic mapping lives only in `frontend/src/lib/api/topics.ts`. `GET /api/debriefs/<id>/shared` is the anonymised shared endpoint; non-joined callers get a plain permission denial.
- **Completion (AD-16):** `progress.record_step` in the same transaction for `explanation`, `debrief`, `quiz_passed`; gates read with `progress.has_step`. A Debrief stays open until the Test deadline; lateness against the Debrief deadline is derived from stored time.
- **Authz/privacy (AD-12, AD-14):** Explanations, reflection answers and follow-up text are keyed by `user_id` and Class session; another Student and an unattached Admin are refused, Assistant lecturers may read. Staff reach Debrief summaries through a link provider registered with `register_insight_links` in `games` `service.py`; reads go through `debrief.service`.
- **Charts:** Etterspørselsbånd, four-Role Kjedebånd variant, Ukeskrubber (and Quizvalg in `frontend/src/components/`) are added to the shared chart module, never copied; Ordrestolper, Rolle × Uke table, Kjedens regning and Kjedens kostnad over tid are reused from Epics 6 and 7. Numbers through the single Norwegian formatter; UI strings in `frontend/src/copy/nb.ts`; unsent text in `frontend/src/lib/drafts.ts`.

## UX & Interaction Patterns

- **Five steps:** 1 «Skriv Forklaringen først» (own net inventory chart only, «Send Forklaring») → 2 reveal (code-rendered heading from demand series, Etterspørselsbånd + table) → 3 whole chain («Hele kjeden: svingningene vokser oppstrøms og kommer senere») → reflection questions (feelings, evidence, structure, one at a time; follow-up field after them) → 4 own moments, then Kjedens regning → quiz (step 5 «Debrief-quiz»).
- **Moments:** paged, each with «Dette så du», «Dette regnet du», «Dette kostet det senere», «Dette så de andre i Uke N»; focus moves to the new moment's heading.
- **Ukeskrubber:** `role="slider"` named «Velg uke», keys ±1 and ±4, Home/End, 44 px step buttons, no drag required, polite reading of the chain after 300 ms idle, instant result with reduced motion. On the shared screen it is local to that device.
- **Quiz result:** wrong choice «Ditt svar, ikke riktig», right «Riktig», by text and border, never colour alone; focus moves to the result summary after submit.
- **Group:** locked-reveal line names who has sent (resolved at read time, Students only); polite announcement on unlock; a time guide for writing.
- Lecturer controls on Klasseøkt (open/hold Debriefs, AI text switch, quiz exclusions) sit before the Start date, Valgknapper/Bryter, with help text.

## Cross-Story Dependencies

- **Within the epic:** 9.1 (facts, patterns, content pinning) underpins 9.5, 9.7, 9.8, 9.9, 9.14, 9.15. 9.2 (open, `debrief.commands`) → 9.3 Explanation gate → 9.4, 9.5, 9.6 → 9.7 → 9.8 → 9.9 → 9.10. 9.11 builds on 9.2/9.3; 9.12 and 9.13 build on 9.11. 9.14 helper, validator and finish hook are reused by 9.9 (explanations) and 9.15.
- **From earlier epics:** `student_game`, «Gå til Debrief» (repointed here from Hjem), Graf over tabell, Kjedebånd (own link), Kjedens regning with its extra-rows slot, number formatter, `drafts.ts`, SSE and `topics.ts` (Epic 6); `progress`, `content`, `sessions.lock`, `ops.sweep`, `platform/notify` (Epics 3, 5, 6); Ordrestolper, Rolle × Uke table, Spillinnsikt with its empty `links` slot (Epic 7); AI gateway and model config tooling (Epic 2); Takeover and playout reasons in the Decision log (Epic 8).
- **Later epics:** Epic 10 Replay reuses facts, renderer and validator and the Debrief walkthrough; `close_follow_up` is called when an Individual test opens (Epic 11); Student report and Studentside read `debrief.service`; Class report reads Detected pattern counts.
- **Open inputs:** quiz and reflection content from issue #16 (placeholders ship now); pattern thresholds need two-lecturer review before pilot; Rule-based placeholders (issues #8, #17); the "active Student" definition for Group debrief is an unconfirmed assumption.
