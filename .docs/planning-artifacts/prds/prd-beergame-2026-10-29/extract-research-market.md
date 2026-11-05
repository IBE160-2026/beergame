# Extract: market and user-voice research for the PRD

Extracted 2026-10-29 from web-only research dated 2026-10-26.

**Citation keys**
- **C** = `research/competitive-beer-game-competitors-2026-10-26/research.md`
- **U** = `research/user-voice-lecturer-need-for-reproducibility-in-bee-2026-10-26/research.md`
- **d/x** = that report's `digests/x.md`
- **[n]** = a source number in the report's appendix
- **[inf]** = my inference, not a research finding

`research/competition.md` holds only the question "What competition exists?".

## 1. Table-stakes features

| Feature | Competitors | Confidence |
|---|---|---|
| Join by link, code or QR, no player account | transentis, Zensimu, En Dash, siemsene (d/offer-r1-b, d/teardown-r3-m) | med-high |
| Self-serve setup, free host account | En Dash, transentis, Zensimu; Fathomd "~2 min"; eBeer and Forio gated (C §1; d/offer-r1-b) | med |
| Random, Excel or host allocation | Zensimu, transentis, eBeer, En Dash; MIT/Forio "autoassign" (d/communities-r1-a) | med |
| Bots fill empty seats | At least 7: En Dash, transentis, Zensimu, Forio Root Beer, eBeer, Skill Dynamics, siemsene (C Exec 1) | high; visible logic is one-line rules |
| Dropout takeover, seat reclaim, missed turns | Zensimu (the computer orders when the timer runs out), eBeer, En Dash; MIT/Forio reuses the previous order (d/redteam-r3-n, d/communities-r1-a) | med |
| Solo play against bots | En Dash, transentis, Zensimu (free), Forio Root Beer, isee, Skill Dynamics, Kearney (C Exec 2) | high |
| Multi-game dashboard, live progress, observers | Zensimu, eBeer, transentis, beergame.org, En Dash; messages, pause and injected events only in Zensimu (C §1; d/zensimu-r2-j) | med (vendor) |
| Demand settings, templates, visibility toggle, two-round format | Zensimu, beergame.org, En Dash, isee, eBeer, Darden (U §3; d/offer-r1-b) | med |
| Debrief report, team comparison, cost ranking, exports, facilitator guide | Zensimu (charts, PDF/Excel, slides), transentis (CSV/JSON/PDF), En Dash (10 scripted questions, replay), eBeer, Cohen, Forio guide (locked); none AI-generated (C §1, §6) | med |
| Quiz or grading | Only an optional quiz on Zensimu's paid plans; no product documents grading (d/zensimu-r2-j) | med (absence) |
| LMS or SSO | No LMS/LTI documented; SSO only on Zensimu Enterprise (C §1; d/incumbents-r2-k) | med (absence) |
| Devices | transentis: desktop, mobile, tablet; Cohen: one shared device, offline; En Dash: 2–3 students per screen (d/offer-r1-b, d/oss-r2-h) | med |
| Languages, accessibility | Zensimu claims 12 languages, but its switcher shows 6; Eureka ~15; Forio MIT is English only; Forio's WCAG claims (2.0 vs 2.1 AA) are inconsistent (d/zensimu-r2-j, d/incumbents-r2-k) | low |

## 2. Where competitors are weak or absent

- **No maintained product pairs a human seat with LLM opponents.** The defensible claim: "no maintained, learner-facing beer game product is documented as using LLM-driven opponents with a human seat or an LLM-generated debrief" (C CE). Only these come close:
  - an abandoned Hugging Face Space (human vs GPT-4o-mini, `BUILD_ERROR`) [32];
  - the GenAI Beer Game, where every role is an LLM [33];
  - SupplyNet, a graph-based game with n=14 and no code [35].
- **Bot personas and difficulty tiers are undocumented.** The nearest are transentis's "advanced preset" and Zensimu's ordering settings (C X1; U §3).
- **Per-run random demand is undocumented.** Fixed or seeded demand is verified only for En Dash, Near Beer and Cohen; Skill Dynamics markets "fluctuating" demand (low) (C Exec 3).
- **No vendor advertises a shared class seed or reproducibility** (U §3, 4–5 pages). U flags the "seeded" Cohen clone as unverified [16]. C read its README: 20 seeded presets plus a custom seed (d/oss-r2-h).
- **No debrief explains decisions.** En Dash's "insight" is hard-coded, and Zensimu's reports mention no AI (C §6). The THE author: "few could clearly explain how their decisions had led them there" (d/voice-r1-e).
- **Analytics stop at charts.** Nobody diagnoses each student's decisions. Dashboards and exports themselves are not a gap (C Exec 3).
- **Asynchronous play with bot takeover is rare.** An HBP chain stops while any member is absent, and no-shows are inactivated by hand (d/evidence-r3-p). Fathomd's asynchronous mode is human-only and dates from 2021 [inf].
- **Undocumented everywhere:** LMS integration, assessment after the debrief, market size, student voice, and willingness to pay beyond price lists (C §5, OQ).

## 3. Lecturer needs and pains (user voice)

- **Reproducibility.** No source requires identical demand for fair grading. Identical demand is a by-product of the physical deck; every Calgary board carries four 4s, forty-six 8s and one stop card (U Exec 1, §2).
  - Confidence: low-medium that this is a real gap, low that it reflects lecturers' needs.
  - Basis: about 40 queries. HN, Medium and r/professors were not searched.
- **Comparability serves the debrief and a competitive frame.** "Different people in the same structure produce qualitatively similar results" [1]. Calgary collects costs "for comparison purposes during the debrief session" (d/educator-lit-r2-c). No source covers comparing sections (U OQ).
- **Grading.**
  - Calgary: the game counts 2% of the grade, for attendance. Prizes across about 100 parallel games create "an incentive to ignore the game rules".
  - UW grades the team reports; its syllabus never mentions the score (U Exec 2, §2).
  - MERLOT: "challenging to assess the success of the learning outcomes, and debriefing after the game is crucial" (U §1).
- **Demand patterns.**
  - The SDS guide calls the 4→8 step "most effective for first-time players". The deck "should not be revealed in advance" (U Exec 3).
  - One educator, who also promotes a tool: fixed patterns let students "anticipate outcomes after just a round or two".
  - Counter-evidence: a 2011 abstract found the demand pattern "not" significant (low) (U §2).
  - Calgary hides the game's name to avoid spoilers (U §1).
- **Session length:**
  - Forio MIT: 1.75–2.75 h, including a 30–60 min debrief.
  - Root Beer: 2 h.
  - Zensimu: 1.5–2 h.
  - eBeer: 30–40 min.
  - MA-system: 30–60 s per round.
  - SDS: plays about 35 of the 50 announced weeks.
  - Calgary: debriefs within ~48 h.

  Sources: d/offer-r1-a, d/offer-r1-b, d/teaching-notes-r1-b, d/educator-lit-r2-c.
- **Sizes.**
  - Teams: four roles, with up to 2 students per role at Zensimu and 2–3 per screen at En Dash (d/voice-r1-e, d/teardown-r3-m).
  - Classes: 400 at Calgary (about 100 boards), 280 at Fathomd and 500 at Bocconi (vendor claim) (U §2; d/teardown-r3-m; d/zensimu-r2-j).
- **Absentees.** Up to 25% missed the game, per a single unverified poster. Four vendors built workarounds, which suggests but does not establish the need (low-medium). One review: "computer did not play very well" (low) (C §5).
- **Fragility.** The manual game is "slow to run" and "surprisingly fragile", and "small errors in tracking orders or inventory can distort results" (C §5). "You cannot begin the debrief until everyone has finished play" (d/communities-r1-a).
- **Devices.** No lecturer voice was found on devices (gap).
- **Vocabulary.** Say "debrief", "demand pattern" and "consumer demand", not "reproducible" (U Rec 5).

## 4. Implications for functional requirements

1. **Seat continuity.** A bot fills the seat at the start, takes over for a dropout and hands the seat back. Define a policy for missed deadlines.
2. **Lecturer-set demand:** fixed, step or random. Provide a visible seed that can be shared per class and a fresh seed per replay. Hide the pattern until the debrief (U Rec 1–2; [1]).
3. **Log every agent decision and seed** so any run can be replayed exactly, instead of requiring deterministic agents (U Rec 3).
4. **Documented bot personas and difficulty**, for both LLM and rule-based bots (C Rec 2).
5. **A decision-level causal debrief**, which is the product itself (C Rec 2–3).
6. **Analytics per game, per class and across classes**, with per-student diagnosis, cost ranking and CSV/PDF export (C Rec 2).
7. **Parity features:** visibility modes, a second-round variant, messaging, pause, observers, templates and a facilitator guide.
8. **Optional ranking.** Grade the test, not the cost (U §2).
9. **Spoiler control.** Offer a neutral game name, and prevent early debriefs from leaking the pattern to students still playing [inf, from [1]].

## 5. Implications for non-functional requirements

- **Pacing.** Live rounds run 30–60 s, so each bot decision must fit inside one round [inf]. The debrief takes 30–60 min or runs later.
- **Concurrency.** Plan for about 100 parallel games per class [inf, from Calgary]. Vendor claims of 600–1000+ are low confidence.
- **Resilience.** A chain must never stall on an absent human, as HBP chains do. Players can reconnect from another device, which MA-system does not allow (d/offer-r1-b).
- **LLM variance.** Run-to-run variation (CV) is 26–52% with default settings and about 12–13% with guardrails or post-training (C §6). Some models broke the ordering rules in more than 25% of cases (d/llm-r2-i), so orders need validation and caps.
- **Cost.** $0.25–2.00 per session (SupplyNet, a different game, gpt-4o, debrief excluded; low) (C X4).
- **Classroom networks** were not researched. Cohen's offline mode is the only fallback seen.

## 6. Pricing and business-model signals

- **Free:** transentis, En Dash, Cohen, beergame.org and siemsene, mostly as lead magnets for consulting (C §2).
- **eBeer:** $20 list, $12 student, $10 academic, flat 2021–2026 (high; the page is stale). Volume pricing starts at 600 students a year, invoiced after the first simulation (d/offer-r1-b).
- **Zensimu:**
  - 2024: €17.5 per participant, or €2,040 a year.
  - Now: Free, Conference and Enterprise plans with at least 50% off for universities. No public prices (low).
  - Prepaid, with seats counted at first connection (C §2; d/zensimu-r2-j).
- **Forio:** $168 per person (high), with annual plans from 15 seats. A third-party figure of $16 is unverified (C §2).
- **isee:** $15 for a single user.
- **Anchor:** $10–20 per student institutionally, with $168 as the ceiling. A student tier would compete with free (medium) (C Rec 5).
- **Market size: unknown.** Zensimu ApS has one employee and a net profit of DKK 449k, a weak signal (C §4, X3).

## 7. Risks to the positioning (red-team findings)

- **The brief's novelty claim fails.** Bot-filled seats and solo replay already exist, for free (C Exec).
- **The Hugging Face counterexample forces narrow wording.** Unchecked so far (C CE):
  - En Dash's multiplayer bots run on the server;
  - Skill Dynamics sits behind a sign-up form;
  - the GPT Store and Gems are poorly indexed;
  - there were no Nordic-language or app-store searches.

  Re-check En Dash by 2026-12-17 (C Stale).
- **Entry is cheap.** About 8 tiny LLM beer-game repos appeared in 2025–26, and Cohen's game was built with Claude (d/oss-r2-h) [inf].
- **"AI bots" are not a wedge.** Positioning A is crowded and free. Positioning B's repetition already exists, so what remains distinct is explanation (C X1, Rec 3).
- **LLM opponents are not a free win** (C Exec 4, §6; d/llm-r2-i):
  - "agent bullwhip": erratic orders that majority voting did not fix;
  - human-likeness has not been measured;
  - they reproduce the direction of human biases, not their distributions;
  - the best setup cost up to 80% less than student teams, so it may dampen the bullwhip the game teaches (low).
- **Reproducibility conflicts with LLM opponents** (C X2).
- **Thin evidence.** No study separates repetition from the debrief. The one fresh educator voice is a tool promoter (C Exec; U Exec). Unheard social-media voices may want comparability (U CE).

## 8. Open questions and unverified claims

| Item | Next step | Issue |
|---|---|---|
| Do En Dash's server bots use rules or an LLM? | Play a mixed game (C OQ) | #1 (C `.memlog`: close only after asking the user); #4 |
| Skill Dynamics bots | Sign-up form; needs the user's go-ahead | #4 |
| SSRN 5266281 | Not found in any registry (C §6) | #2 (closed) |
| Does repetition teach? (Jeong & Hong 2011, Martin 2004) | Abstracts only so far (C OQ; U §2) | #5, #6 |
| Absentee frequency, grading, need for identical demand, comparing sections | 5–8 lecturer interviews (U Rec 4) | #7 |
| Calgary "up to 25%"; Zensimu's current prices; MA-system ghost players (disputed) | Unverified; ask for a quote; re-fetch the rules page | — |
| Couscous repo; Forio and transentis controls; memorising across cohorts | Not found, locked or 404 (C OQ; U OQ) | — |

Only #1 is named in these files. I mapped the other issues from `gh issue list`. #10 and #11 cover the LLM-default decision.

## 9. Conflicts with the founder's v1 scope and the LLM-default decision

- **LLM opponents by default.** C (X2, Rec 4) prefers a rule-based or RL default, with LLMs for the debrief and optional personas (medium). U X3 softens this: grading comparability is not an evidenced need, so bit-exact reproducibility is "not required", and seeds plus decision logs suffice (U Rec 3). Bot quality remains open (#10, #11).
- **"Explains the student's own decisions."** With CV of 26–52%, part of each outcome is bot noise, so the debrief must separate the student's share of the cost from the bots' share [inf].
- **"Working LLM opponents" as the differentiator** clashes with C X1: "the wedge cannot be AI bots". It holds only if bot behaviour is documented and distinct. Never sell seat-filling as new.
- **Email invites plus registration** add friction compared with rivals' no-account join. This is justified by tests and cross-class insight, and LMS/SSO is not table stakes (C §1).
- **Self-started or personal debriefs** break with the tradition of a lecturer-led debrief after everyone has finished (U §1). They also risk spoiling the game for students still playing [inf].
- **Students choosing their game:** HBP hides chain membership, and Calgary saw rule-breaking to "win". Consider auto-allocation as the default [inf].
- **The individual test, cross-class statistics and mobile-first** have no supporting evidence, which is an absence rather than a contradiction. Validate them in the interviews (#7).
