---
title: 'Story 2.13: Describe each AI player type in plain Norwegian'
type: 'feature'
created: '2026-11-18'
baseline_revision: '1b6a08de58e53dcdef28f9853d2c5f4a2a1a7369'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer has no plain-language account of how the two AI player types decide, so they cannot choose an AI mode knowingly or explain the AI players to Students (FR-33, FR-72).

**Approach:**
- Two versioned Norwegian bokmål files sit under `backend/app/modules/players/descriptions/v1/`: `rule_based.md` and `llm.md`.
- `players.service.describe(kind)` returns the text with its version.
- `python -m app.sim describe` prints both.
- Tests tie the texts to the rule's code and to the Story 2.4 prompt checks.

## Boundaries & Constraints

**Always:**
- `describe(kind: OccupantKind | str, version: int | None = None) -> Description(kind, version, text)` in `app/modules/players/service.py`:
  - `Description` is a frozen dataclass.
  - `version=None` means the newest `v<N>` folder that holds a file for the kind.
  - `kind` is `rule_based` or `llm`. Any other kind (`student`, `scripted`, unknown) raises `ValueError`, and so does a version with no file.
  - The text is read as UTF-8 with `\r\n` normalised to `\n`.
- The texts:
  - They are original Norwegian bokmål, short (under about 250 words each), and use the product's terms: «KI-spiller», «LLM-spiller», «regelbasert», «ordre», «uke», «lager», «restordre», «på vei», «sete», «spill».
  - Quantities are in «enheter». They never contain «øl», «Beer Game» or «bullwhip» (case-insensitive; «øl» as a whole word).
- `rule_based.md` covers:
  - the fixed rule, «forankring og justering»;
  - one bullet list after a line that ends «ser på disse tallene for sitt eget sete:», naming exactly its own lager, restordre, innkommende bestillinger and enheter på vei;
  - the Game settings in force (delays, the largest allowed Order);
  - that it reads no neighbour numbers, even where Information visibility shows them;
  - the source of its parameters: a named parameter set, meant to come from Sterman (1989), currently round placeholder values;
  - while the default set is `verified: false`, the words «ikke verifisert».
- `llm.md` covers:
  - that behaviour varies between runs;
  - that the model is not told it is playing a game;
  - that it may play better than a typical Student;
  - that a Rule-based Order replaces its Order when the model fails (that Week) or the Play guard switches the Seat (rest of the Game);
  - what the model sees: the same own numbers a Student in that Seat sees, customer demand only for the Retailer, no other business's numbers, no Week count.
- `sim describe`:
  - It prints, for each kind in the order `rule_based`, `llm`, a header line `description <kind> v<N>` and then the text.
  - It is offline: it is in `OFFLINE_COMMANDS`, with no database and no seed.
  - It exits 0. The module docstring lists it.

**Never:**
- No Lecturer material on AI players or the AI assessment (founder-owned, PRD §10.2).
- No frontend change.
- No API route.
- No change to the rule, the prompt or the parameter sets.
- No import in `players/service.py` beyond what `test_imports` allows.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Rule-based | `describe("rule_based")` | `Description(kind="rule_based", version=1, text=…)` | — |
| LLM by enum | `describe(OccupantKind.LLM)` | version 1, the LLM text | — |
| Other kind | `student`, `scripted`, `robot` | — | `ValueError` |
| Missing version | `describe("llm", version=9)` | — | `ValueError` |
| CLI | `python -m app.sim describe` | two header lines and both texts, exit 0, no DB | — |

</intent-contract>

## Code Map

- `backend/app/modules/players/service.py` -- the home of `describe`, per the AC. Allowed imports are in `tests/test_imports.py:35`: other modules only `games.service`/`games.commands`, and no LLM libraries.
- `backend/app/modules/games/schemas.py:38` -- `OccupantKind` (StrEnum: student, llm, rule_based, scripted), re-exported as `games_service.OccupantKind`.
- `backend/app/engine/rule_based.py:70` -- `order()` reads `seat_view.{inventory, backlog, incoming_orders, supply_line, role}` and `settings.{order_delay, shipping_delay, production_delay, max_order, roles}`. `DEFAULT_SET_ID = "placeholder-unverified"`.
- `backend/app/engine/rule_based.md` -- the English rule doc and the source of truth for the wording.
- `backend/app/engine/view.py` -- `SeatView` fields: role, inventory, backlog, incoming_orders, supply_line, order_history, neighbour_numbers.
- `backend/app/parameter_sets/rule_based/placeholder-unverified.json` -- `verified: false`, the source text. `app.sim.load_rule_based_params(id)` loads it.
- `backend/app/ai/prompts/player_order/v1.md` -- the LLM prompt.
- `backend/tests/players/test_llm_prompt.py` -- the Story 2.4 checks to reuse:
  - `prompts(CLASSIC)`, `BANNED` (:157);
  - the customer-demand-only-for-the-Retailer check (:114);
  - the other-Seats test (:128);
  - the no-Week-count test (:95);
  - "There is no last week" (:175).
- `backend/app/sim.py` -- the docstring (:1-128), `build_parser` (:1414), `OFFLINE_COMMANDS` (:1566), `main`. Handlers take `(args, parser)` and return an exit code.
- `backend/tests/test_sim.py:12` -- the `run(capsys, *argv)` pattern.
- `README.md` -- the per-story sections (Story 2.12 is the latest).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/players/descriptions/v1/rule_based.md`, `.../v1/llm.md` (new) -- the texts.
- `backend/app/modules/players/service.py` -- `Description`, `DESCRIPTIONS_DIR`, `DESCRIBED_KINDS`, `describe`; add to `__all__`.
- `backend/app/sim.py` -- the `describe` subcommand, the docstring and `OFFLINE_COMMANDS`.
- `README.md` -- a short Story 2.13 section.
- `backend/tests/players/test_descriptions.py` (new, no DB) -- the matrix rows and these checks:
  - Forbidden words, and «enheter» present.
  - Rule inputs: the bullet list maps through a term→field table (lager→inventory, restordre→backlog, innkommende bestillinger→incoming_orders, på vei→supply_line, tidligere ordre→order_history, nabo→neighbour_numbers). Each bullet maps to exactly one field. The set equals the `seat_view.<attr>` reads that an AST walk of `rule_based.py` finds, minus `role`. The test fails on an unmapped bullet or a field the rule does not read. Outside the list, «nabo» appears only in a sentence with «ikke».
  - It reads no cost setting: an AST walk finds no `settings.*cost*`/`*rate*`, and the text says costs are not part of the rule.
  - «ikke verifisert» is in the text exactly when the default set is unverified. «Sterman (1989)» is named.
  - LLM claims: each claim phrase in the description is paired with a Story 2.4 check run on `prompts(CLASSIC)`:
    - «får ikke vite at den spiller et spill» ↔ no `BANNED` match;
    - «Bare forhandleren ser kundenes etterspørsel» ↔ the demand check;
    - «ser ikke tallene til de andre» ↔ the tampered-neighbours equality;
    - «hvor mange uker» (negated) ↔ the same prompts with `weeks=50`, and "There is no last week".
  - The required FR-33 phrases are present: varierer, bedre enn en typisk student, regelbasert ordre, spillvakt.
  - `sim describe` output and exit code.

**Acceptance Criteria:**
- Given the CI commands run locally, then ruff is clean and the full suite passes. Any new test over 1 s is reported.
- Given an independent Norwegian-language review subagent, when it reads both texts against FR-33 and the code facts, then it finds them plain, correct bokmål and accurate. The verdict is recorded in this spec in place of the founder.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 53 findings — high 0, medium 5, low 48, false 0, maybe-false 0 (descriptive intent findings graded low)
- findings:
  - Blind hunter:
    - `[medium]` `[patch]` (b1) `llm.md` said the Play guard switches only when Orders are too far from the references. It also switches when they are suspiciously close to the near-optimal Order (`analysis/play_guard.md`, upper limit). Fixed: both limits are now named, and a test ties the sentences to `placeholder-0` (`lower_share`, `upper_margin`).
    - `[low]` `[patch]` (b2) The LLM text hid that the guard values are placeholders. Added «Grensene er foreløpige og ikke kalibrert ennå.», tested against the set's `verified`.
    - `[medium]` `[patch]` (b3) «de samme tallene som en student i samme sete» is wrong under neighbour visibility. It now reads «tallene for sitt eget sete … heller ikke når innstillingene lar studentene se dem».
    - `[low]` `[patch]` (b4) The listed numbers were not paired with prompt lines. The test now parses the text's list and requires it to equal `SHOWN`, one prompt line each.
    - `[low]` `[patch]` (b5) «fire parametere» was not tied to the code. The test now counts the value fields of `RuleBasedParams`.
    - `[low]` `[patch]` (b6) A shipped text could be edited in place. `test_shipped_texts_never_change` now pins the sha256 of every `v*/*.md`.
    - `[low]` `[reject]` (b7) No record of which description version a Lecturer saw. There is no Lecturer surface until Epic 5, which owns the AI mode choice.
    - `[low]` `[patch]` (b8) Weak error handling in `describe`. Same root as e1 to e3, patched there.
    - `[low]` `[reject]` (b9a) The CLI cannot select a kind or version. The AC asks it to print both, and `describe(kind, version)` is the API.
    - `[low]` `[reject]` (b9b) `reconfigure` changes stdout for the whole process. In the CLI that is the intent. In tests it touches only the capture stream, which is already UTF-8.
    - `[low]` `[reject]` (b10) The test imports from another test module, and `prompts()` plays a Game. It reuses the Story 2.4 checks on purpose, and its slowest test takes 0.5 s.
    - `[low]` `[reject]` (b11) Technical terms are left unexplained. «LLM-spiller» is explained as «stor språkmodell», and the independent language review passed the terms.
  - Edge-case hunter:
    - `[low]` `[patch]` (e1) `version=True` or `1.0` passed the membership check. It is now refused unless its type is exactly int (parametrised test).
    - `[low]` `[patch]` (e2) A missing `DESCRIPTIONS_DIR` raised FileNotFoundError. It now gives ValueError (test).
    - `[low]` `[patch]` (e3) The message read «version None». It now reads «no description file for <kind>».
    - `[low]` `[reject]` (e4) Non-UTF-8 bytes or a lone CR in a file. The files ship with the code and are pinned by hash.
    - `[low]` `[reject]` (e5) The CLI ends in a traceback when a file is missing. That is a loud failure on a broken install, and a branch for it is not worth it.
    - `[low]` `[reject]` (e6) A stdout wrapper that is neither a TextIOWrapper nor UTF-8. Unlikely in use; Docker and CI are UTF-8.
    - `[low]` `[reject]` (e7) `reconfigure` is process-wide. Same as b9b.
    - `[low]` `[patch]` (e8) StopIteration when the list heading is missing. It is now an assert with a message.
    - `[low]` `[patch]` (e9) The neighbours claim only cited the Story 2.4 test. The test now calls the 2.4 checks directly: game words, demand for the Retailer only, other Seats, no Week count.
  - Verification gap:
    - `[medium]` `[patch]` (vg1) The UTF-8 reconfigure had no test. Added `test_sim_describe_writes_utf_8_on_a_windows_console` (a cp1252 stream). It was also checked by hand before the patch: exit 0, UTF-8 out.
    - `[low]` `[patch]` (vg2) The README overstated what is checked. It now says what each check covers, and that switching itself is tested in Stories 2.5, 2.8 and 2.10.
  - Intent alignment (descriptive):
    - `[low]` `[reject]` (i1) The CLI is tested in-process. The cp1252 test covers the console path, and the CLI was also run as a program.
    - `[low]` `[reject]` (i2) Only the list of inputs is checked, not the prose. The list holds the declared inputs. The prose names only the expected order and the targets, and the language review checked it against the rule.
    - `[low]` `[reject]` (i3) The checks are string-coupled. This is intended: reworded text is a new version, and the test changes with it.
    - `[low]` `[patch]` (i4) Versioning was not enforced. Same fix as b6.
    - `[low]` `[reject]` (i5) The caveat is tied to the default set, not to a Game's set. Recorded decision: the description is shown before any Game exists.
    - `[low]` `[patch]` (i6) The «øl» regex missed compounds. It is now `\bøl|øl\b`.
  - Independent Norwegian review, pass 1 (stands in for the founder; verdicts (a) FAIL, (b) FAIL, (c) PASS, (d) FAIL minor):
    - `[low]` `[patch]` (n1) «ulike ordre» → «ulike ordrer».
    - `[low]` `[patch]` (n2) «i stedet for den uken» → «i stedet, bare for den uken».
    - `[low]` `[patch]` (n3) «ett helt antall … innenfor tillatt ordre» and «koden sjekker» → «et helt antall enheter mellom minste og største tillatte ordre» and «systemet kontrollerer».
    - `[low]` `[patch]` (n4) «ville sett»: the sentence was rewritten (n7).
    - `[low]` `[patch]` (n5) The guard sentence was loose. It was rewritten (b1).
    - `[low]` `[patch]` (n6) «er ikke med i regelen» → «inngår ikke i regelen»; «navngitt parametersamling» → «egen parameterfil».
    - `[medium]` `[patch]` (n7) The «same numbers as a student» claim. Same root as b3.
    - `[low]` `[patch]` (n8) «Bare forhandleren ser kundenes etterspørsel» → «Hos forhandleren er innkommende ordre sluttkundenes etterspørsel; …».
    - `[low]` `[patch]` (n9) Two fallback cases were missing. All four `FailureKind`s are now named, and a test checks them against `gateway.FailureKind`.
    - `[medium]` `[patch]` (n10) The guard description was too vague. Same root as b1.
    - `[low]` `[patch]` (n11) The cost-limit scope was missing. It now reads «alle LLM-seter som bruker av det samme budsjettet».
    - `[low]` `[patch]` (n12) «leder innkjøpet» does not fit the Factory → «har ansvaret for vareflyten».
    - `[low]` `[patch]` (n13) The text understated the placeholder values → «De er ikke hentet fra studien og er ikke verifisert ennå».
    - `[low]` `[patch]` (n14) The values only fit Classic → «med standardinnstillingene (Klassisk)».
    - `[low]` `[patch]` (n15) The rule closes part of the gap in stock minus backlog → «nærme seg et ønsket lager (lager minus restordre)».
    - `[low]` `[patch]` (n16) «innkommende bestillinger» → «innkommende ordre». The test now forbids «bestilling».
  - Independent Norwegian review, pass 2 on the revised texts (verdicts (a) FAIL on one sentence, (b) PASS, (c) PASS, (d) PASS):
    - `[low]` `[patch]` (r1) «leverandøren av modellen» clashes with the supplier role → «tjenesten som leverer modellen».
    - `[low]` `[patch]` (r2, optional) «budsjett igjen til kallet» → «til å spørre modellen».
    - `[low]` `[patch]` (r3, optional) «belastes det samme budsjettet» → «bruker av det samme budsjettet».
    - `[low]` `[patch]` (r4, optional) Added «ikke bare for den uken» to the cost-limit sentence.
    - `[low]` `[reject]` (r5, optional) «blant annet» before the list. The list is exact on purpose and is paired with the prompt lines.
    - `[low]` `[reject]` (r6, optional) Rephrase «ser bare ordrene fra kunden sin». Style preference.
    - `[low]` `[reject]` (r7, optional) Rephrase the bracket «(lager minus restordre)». Style preference.
    - `[low]` `[reject]` (r8, optional) The costs sentence is fine as written. No action.

## Design Notes

Decisions taken in place of the founder:
- The texts are static versioned files. While `placeholder-unverified` is the default, the Rule-based text states that its parameters are unverified. When a verified set becomes the default, the test fails until a `v2` text is written. `describe` does not splice text in at run time.
- The version is an int, like prompt versions, taken from the folder `v<N>`.
- The Play guard is described as «en automatisk kontroll (spillvakten)». The product has no Norwegian term yet.
- The cost limit is described together with the Play guard as a switch for the rest of the Game. Model failures replace only that Week's Order.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest -n0 tests/players/test_descriptions.py tests/test_imports.py tests/test_sim.py -q` -- expected: pass
- `cd backend && uv run pytest --durations=10` -- expected: pass, once before commit

## Auto Run Result

Status: done

**Summary:**
- Two Norwegian bokmål descriptions are in `backend/app/modules/players/descriptions/v1/` (`rule_based.md`, `llm.md`).
- `players.service.describe(kind, version=None)` returns `Description(kind, version, text)`. The default is the newest version. Another kind, or a version with no file, raises ValueError.
- `python -m app.sim describe` prints both texts, each after `description <kind> v<N>`. It uses no database, and it writes UTF-8 even on a Windows console.
- Tests tie the texts to the code:
  - The Rule-based input list equals the `seat_view` reads in `engine/rule_based.py` (AST walk). It names no costs and no neighbours, and «fire parametere» is checked against `RuleBasedParams`. «ikke verifisert» appears exactly when the default set is unverified.
  - The LLM claims run the Story 2.4 prompt checks. Its four fallback cases equal `gateway.FailureKind`. Its guard sentences are checked against the `placeholder-0` set.
  - The shipped texts are pinned by sha256.

**Files:**
- `backend/app/modules/players/descriptions/v1/rule_based.md`, `llm.md` (new): the texts.
- `backend/app/modules/players/service.py`: `describe`, `Description`, `DESCRIBED_KINDS`, `DESCRIPTIONS_DIR`.
- `backend/app/sim.py`: the `describe` subcommand, docstring, `OFFLINE_COMMANDS`.
- `backend/tests/players/test_descriptions.py` (new): 24 tests, no DB.
- `README.md`: a Story 2.13 section.

**Review:**
- One code pass with 4 layers, plus 2 independent Norwegian-language passes standing in for the founder. 53 findings in all.
- Patched:
  - 3 medium entries: the guard's two limits, the claim «same numbers as a student», the UTF-8 test.
  - Every language finding that was not optional, and 3 optional ones.
  - Low code fixes.
- Deferred: none.
- Rejected: 17, with reasons in the triage log.
- Founder check, done by an agent: the second language pass gave PASS for facts, AC coverage and copy rules. Its one bokmål FAIL («leverandøren av modellen») is fixed.

**Follow-up review recommended:** true.
- 3 medium entries were patched.
- Unverified risk: no code-review layer has seen the patched tests or the final wording. The patched tests are the hash lock, the direct calls into the Story 2.4 test functions, and the couplings to failure kinds and the guard.

**Verification:**
- ruff check and format: clean.
- `tests/players/test_descriptions.py`: 24 passed in 0.9 s. No new test is over 1 s; the slowest takes 0.49 s.
- Full suite:
  - Before the patches: 1538 passed in 59 s.
  - After the patches: three runs of 75–89 s, each with 2 failures. All of them come from three timing tests: `test_llm_jobs.py::test_a_burst_of_429s…`, `test_sim_llm.py::test_a_whole_game_with_the_provider_down…`, `test_rescue.py::test_the_job_keeps_a_hanging_model…`.
  - The same failures appear with the new test file deselected. The three files pass when run alone (30 passed).
  - Other agents were loading the machine. This story touches no job, gateway or rescue code.
- `python -m app.sim describe` was run as a program.
- No migration.

**Decisions taken in place of the founder:**
1. The texts are static, versioned files. Tests tie the caveats «not verified» and «not calibrated» to the default sets, so a verified set forces a v2.
2. The version is an int taken from the folder name `v<N>`.
3. The Play guard is called «en automatisk kontroll (spillvakten)». Both of its limits are named, and the text says it is not calibrated.
4. The texts name all four fallback cases and the switch at the cost limit, beyond what the AC asks.
5. The texts say «innkommende ordre», not «bestillinger» (the UI term), and «standardinnstillingene (Klassisk)».
6. `sim describe` forces UTF-8 on stdout.
7. Implementation ran in this session, not in a subagent (a runbook constraint).

**Residual risks:**
- Three timing-sensitive tests fail under machine load. This is pre-existing and not caused by this story.
- Nothing records which description version a Lecturer saw (Epic 5).
