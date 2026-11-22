# Epic 9 Context: Debrief and Debrief quiz

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Students of a finished Class game write their own Explanation, then see the customer demand revealed, the whole four-Role chain with Order amplification, reflection questions, at least three of their own moments, the chain's bill, and pass a Debrief quiz, alone or in a Group debrief with an optional shared screen. The Debrief is built code-only first, so it works under any AI mode and with no LLM; AI narration and bounded follow-up are layered on top through the AI gateway and always fall back to code-rendered text. The epic owns `modules/debrief` (backend and frontend), adds the quiz, sentence templates and Detected pattern definitions to `modules/content`, and adds the shared facts, validator and renderer to `analysis/`, `ai/` and `modules/games` (`fact_sets`). Replay, the Individual test and the Student report reuse these pieces.

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

- **Debrief content:** reveals the demand series; Orders, inventory and backlog per Role over the Weeks (with text alternative); Order amplification per Role; at least three own moments per Student (Week, what they saw, what they ordered, later cost, matching Detected pattern and mechanism, what the other Roles saw); the Explanation beside the data, to that Student only. Every number matches the Decision log exactly. States that AI explanations can be wrong. Shows the share of chain Total cost incurred in AI-held Seats.
- **Detected patterns:** a closed list of three, worded as patterns, never causes: an Order well above incoming orders after a shortage; a large Order while the Supply line already holds a lot; very low Orders after an overshoot. Thresholds are placeholders marked "to be reviewed by two lecturers before pilot".
- **Moments:** chosen by a documented rule over the Decision log, only from Weeks with `decided_by = student`. A Seat with fewer than 10 such Orders gets no moments, the Debrief says the game was mostly played by AI players, the Student is flagged out of SM-1 and SM-2, and can still finish.
- **Explanation gate:** one per Student per Class session, stored once unchanged (`409 explanation_exists`), written before any reveal. Demand, other Seats' data and later steps return `403 explanation_required`, checked in the API. The number of Weeks is not gated once the game is finished.
- **Availability:** only for finished games (`403 debrief_not_open`); a Lecturer may hold all Debriefs until every Class game has ended (`403 debrief_held`), frozen at the Start date; release is a once-only idempotent sweep action that notifies Students.
- **Quiz:** fixed single-choice questions, server-side scoring by answer key, one immutable `quiz_attempts` row per attempt, unlimited retries until the Test deadline (`409 test_deadline_passed`), counts toward no score. Gate `progress.has_step(debrief)` (`403 debrief_required`). Lecturers may exclude questions (never all) until the Test deadline. Content is placeholder until issue #16.
- **Group debrief:** joined Students share one step pointer, which moves when all have finished the step or the opener moves on after a configured minimum wait (`409 too_early`). Writing, reflection, moments and quiz stay individual on own devices. Dropout after 2 minutes silent; 48-hour fallback to Personal debrief; a game with one active Student is always Personal. All gates still hold in the fallback.
- **Shared screen:** charts by Role only, never names, Explanations, answers, moments or free text; locked until all joined Students have sent.
- **AI text:** no step ever waits on an LLM; text is fixed at a Student's first view; marked «KI-generert, kan ta feil:» from `ai_generated` only. Follow-up declines off-topic questions, gives hints not model answers to test-like questions, closes when the Individual test opens or at the Test deadline, is rate limited (`429 rate_limited`), and is absent when Debrief AI text is off or no provider exists. A Lecturer can switch Debrief AI text off per Class session before the Start date.
- **Copy:** Norwegian bokmål; ask why not who; second person; no praise, blame or exclamation marks. «Beer Game»/«bullwhip» only in a post-reveal section of `nb.ts` exempt from the CI copy check. The «Simulert» block never claims «optimal» or «fasit».
- **Accessibility:** WCAG 2.1 AA; Playwright + axe at 320, 360, 1440 px; keyboard-operable; no page-level horizontal scroll; every chart has a table alternative; reduced motion respected.

## Technical Decisions

- **Pure analysis (AD-1):** `analysis` does no I/O, no clock, no unseeded randomness. `analysis.facts`, `analysis.render(fact_set, template_ids)`, `analysis.validate_ai_text(output, fact_set, templates)` and the «Simulert, samme kunder» function (runs `engine.advance` over the stored demand series and settings; ordering parameters from configuration with Rule-based placeholders, issues #8, #17) are pure. The web app computes none of these numbers.
- **Facts sets (AD-7, AD-14):** one `fact_sets(id, game_id, seat_id, analysis_version, payload)` row per Seat, created only through `games.facts.get_or_create(game, seat)`; consumers load by `fact_set_id`, never rebuild; payload holds ids, values and Roles only, no names; chain-level part identical across the four Seats. Fact ids are deterministic `<pattern>:<role>:<week>`. Golden tests (addendum §B trace, a Takeover Game, a fully Rule-based Game); `python -m app.sim facts <game_id>` prints sets for simulation Games.
- **LLM boundary (AD-6, AD-7):** only `app/ai` talks to an LLM, via `ai.run(purpose, budget_scope=<Class session>, …)`; Debrief purposes (`debrief_narration`, `quiz_explanation`, `debrief_follow_up`) may spend the budget `reserve`. The provider is OpenRouter with model `deepseek/deepseek-v4.1-flash-1017` (founder decision 2026-11-17, issue #9); whether an EU provider serves it with ZDR and `allow_fallbacks: false` is still open and checked in Story 2.7. The model config is pinned per Class session and swappable; no automatic fallback model. Each new purpose needs a `prompts` entry in a new immutable model config row (`config edit … --prompt`) and a versioned prompt file under `backend/app/ai/prompts/<purpose>/`. Output schemas reference fact ids and sentence-template ids only; code renders every number and cause; any rejection or typed failure (`timeout`, `invalid_output`, `budget_exhausted`, `provider_error`) yields code text `{text, ai_generated: false, llm_call_id: null}`, never retried. The shared helper takes validator and fallback renderer from its caller (`app/ai` imports only `platform`). Mock provider is default locally and in CI. `modules/debrief` must never import `modules/players` (import-linter); the Debrief must pass on a Rule-based Game with the mock off.
- **Free text to LLM:** follow-up is the first Student free text sent to an LLM; `platform/pii.terms(class_session_id)` then reads the whole Roster, only the gateway calls it, and the scrubbed body is what is stored and sent.
- **Narration timing:** generated on `llm-batch` in `worker-batch`, deferred inside the `finish` transaction via `games.service.on_game_finished(hook)` (Debrief registers; `games` imports nothing from `debrief`); one idempotent job per Seat a Student held, keyed by `fact_set_id`, ids-only arguments, re-enqueued by the sweep if lost.
- **Content versioning (AD-23, AD-4):** pattern definitions, sentence templates, reflection questions and quiz are immutable versioned records in `modules/content`, each pinned by `sessions.lock` as an entry in `SessionRuntime`'s open map (with the AI-text switch), no change to the lock mechanism. Attempts store the quiz version. Quiz exclusions are a Class-session row owned by `modules/debrief`, audited via `platform/audit`.
- **Debrief writes (AD-21, AD-8):** `debrief.commands` (`open`, `join`, `save_explanation`, `complete_step`, `move_on`, `leave`, `finish`, `touch`, `open_personal_fallback`, `close_follow_up`) is the only writer; each locks the Debrief row and emits `debrief:<id>`, except `touch` (no lock, no event). All need entries in `platform/events/registry.py`. Presence is server-side through an `on_heartbeat` hook on the 15 s SSE heartbeat. A Student's game is found only via `games.service.student_game`; availability via `debrief.rules.available`. Topic-to-query-key mapping only in `frontend/src/lib/api/topics.ts`. The anonymised endpoint is `GET /api/debriefs/<id>/shared`; non-joined callers get a plain permission denial.
- **Completion (AD-16):** `progress.record_step` in the same transaction for `explanation`, `debrief`, `quiz_passed`; gates via `progress.has_step`. The Debrief stays open until the Test deadline.
- **Authz/privacy (AD-12, AD-14):** Explanations, reflection answers and follow-up text are keyed by `user_id` and Class session; other Students and an unattached Admin are refused, Assistant lecturers may read. Staff summaries use a link provider registered through `register_insight_links` in `games` `service.py`; reads go through `debrief.service`.
- **Charts and frontend (AD-10, AD-18, AD-19):** Etterspørselsbånd, four-Role Kjedebånd variant, Ukeskrubber and Quizvalg are added to the shared components, never copied; Ordrestolper, Rolle × Uke table, Kjedens regning and Kjedens kostnad over tid are reused from Epics 6 and 7. Charts have fixed width and a table alternative. Typed from the generated API client; copy in `frontend/src/copy/nb.ts`; unsent text in `frontend/src/lib/drafts.ts`; one Norwegian number formatter.

## UX & Interaction Patterns

- **Step order:** 1 «Skriv Forklaringen først» (own net inventory chart only, «Send Forklaring») → 2 reveal (code-rendered heading, Etterspørselsbånd + table) → 3 whole chain («Hele kjeden: svingningene vokser oppstrøms og kommer senere») → reflection questions (feelings, evidence, structure, one at a time; follow-up field after them) → 4 own moments, then Kjedens regning → 5 «Debrief-quiz».
- **Moments:** paged, each with «Dette så du», «Dette regnet du», «Dette kostet det senere», «Dette så de andre i Uke N»; focus moves to the new moment's heading.
- **Ukeskrubber:** `role="slider"` named «Velg uke», keys ±1 and ±4, Home/End, 44 px step buttons, no drag required, polite reading of the chain after 300 ms idle, instant with reduced motion; local to each device on the shared screen.
- **Quiz result:** wrong choice «Ditt svar, ikke riktig», right «Riktig», by text and border, never colour alone; focus moves to the result summary after submit.
- **Group:** the locked-reveal line names who has sent (resolved at read time); polite announcement on unlock; a time guide for writing.
- **Lecturer controls** (open/hold Debriefs, AI text switch, quiz exclusions) sit on Klasseøkt before the Start date, as Valgknapper/Bryter with help text.

## Cross-Story Dependencies

- **Within the epic:** 9.1 (facts, patterns, content pinning) underpins 9.5, 9.7, 9.8, 9.9, 9.14, 9.15. Flow: 9.2 open → 9.3 Explanation gate → 9.4, 9.5, 9.6 → 9.7 → 9.8 → 9.9 → 9.10. 9.11 builds on 9.2/9.3; 9.12 and 9.13 on 9.11. 9.14's helper, validator and finish hook are reused by 9.9 (explanations) and 9.15.
- **From earlier epics:** `student_game`, «Spillet er ferdig» (its «Gå til Debrief» is repointed here), Graf over tabell, Kjedebånd, Kjedens regning with its extra-rows slot, `drafts.ts`, SSE and `topics.ts` (Epic 6); `progress`, `content`, `sessions.lock`, `ops.sweep`, `platform/notify` (Epics 3, 5, 6); Ordrestolper, Rolle × Uke table, Spillinnsikt with its empty `links` slot (Epic 7); AI gateway, model config tooling and the OpenRouter provider check (Epic 2); Takeover and playout reasons in the Decision log (Epic 8).
- **Later epics:** Replay (Epic 10) reuses facts, renderer, validator and the walkthrough; Epic 11 calls `close_follow_up` when an Individual test opens; Student report and Studentside read `debrief.service`; Class report reads Detected pattern counts.
- **Open inputs:** quiz and reflection content (issue #16, placeholders ship); pattern thresholds need two-lecturer review before pilot; Rule-based placeholders (issues #8, #17); the definition of an "active Student" for Group debrief is an unconfirmed assumption; the Debrief budget reserve size is set after the prototype.
