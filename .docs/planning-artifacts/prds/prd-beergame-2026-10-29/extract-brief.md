---
title: "Extract: brief, addendum and forge for the PRD"
created: 2026-10-29
sources: brief.md (final), addendum.md (final), brief .memlog.md, forge-report.html, forge .memlog.md
---

# Extract: brief, addendum, forge → PRD

**Keys.** B = `.docs/planning-artifacts/briefs/brief-beergame-2026-09-04/brief.md`; A = `addendum.md` and BM = `.memlog.md` in the same folder; FR = `.docs/forge/beergame-positioning-b/forge-report.html`, FM = its `.memlog.md`. Section tags: B Exec, Problem, WhyNow, Solution, Different, Serves, Biz, Success, Scope, Risks n, OpenQ, Vision · A Decline, LLM, Comp, Fork, BizR, Founder, Deferred, U:topic (2026-10-29 update notes) · FR Locked, Rejected, Weak, Voices.
**F1–F9** = founder's v1 list: F1 full game + debrief · F2 email invite, enrol · F3 game choice or auto-allocation, bots fill seats · F4 progress overview, messaging · F5 deadline, dropout takeover · F6 self-started group or personal debrief · F7 individual test, grade · F8 lecturer insight, rerun · F9 mobile-first.

## 1. Thesis, vision, the bet

- "Our bet, stated as a bet: **the product is working AI opponents plus the explanation.**" … "making them work is the first thing we build." [B Exec]
- "AI opponents fill any empty role, which turns a once-per-semester group event into something a single student can replay as many times as it takes for the pattern to click." [B Exec]
- "Whether repetition against those opponents plus that debrief actually teaches students more than one good session is untested. It is the first thing this venture has to prove" [B Exec]
- "**The core move is repetition plus explanation.**" [B Solution] "If the debrief is not clearly better than a scripted one, positioning B loses its edge." [B Different]
- Positioning B, "From one session to a hundred", decided 2026-10-29 as "an untested hypothesis"; "B holds only if the debrief and progression layer is the product" [A Fork; FR Locked; FM].
- Vision: "Start by saving one exercise." … "the platform where experiential business simulations stop being annual events and become practice" (3 years; the pattern generalises to negotiation, market-entry and prisoner's-dilemma games) [B Vision].
- Tension: B Exec makes LLM opponents co-core; FR Locked and A Fork make bots the enabler and the debrief the product. The PRD should pick one.

## 2. Users, roles, jobs-to-be-done

- **Lecturer**, "primary buyer-influencer", teaches supply chain, operations or logistics. Wants the exercise to land "without spending the hour as a referee"; success = students "explain the mechanism back". Jobs: create class, "invite or roster students", run and watch a live session, debrief "built from real data rather than recollection", choose opponent type and demand pattern [B Serves, Solution].
- **Student**, "primary user": understand bullwhip, "not just witness it once"; replay "on the bus, on an iPad, at 23:00 before an exam" [B Serves]. Also a possible direct buyer [BM].
- **Institution**, "payer": "measurable engagement, curriculum fit, no IT burden" [B Serves]; "someone accountable when it breaks mid-lecture" [A BizR]; will ask for a DPA [B Risks 7].
- **Founder**: his course is design partner, test bed and evidence source [A Founder].
- Never named: the "classic four roles" [B Scope], TA/co-lecturer, platform admin.

## 3. Problem evidence

- *Times Higher Education* Campus, June 2026, "Less beer, more couscous: gamifying supply chain education": the game "may have had its last orders" [B Exec; A Decline]. Complaints [B Problem; A Decline]: "The effort required to run the game can end up distracting from the bigger picture"; "Few could clearly explain how their decisions had led them there" ("the expensive one"); "Slow to run and proves surprisingly fragile"; "Fixed demand patterns make it easier for students to anticipate outcomes."
- Root constraint: "in the classic format you get one attempt." [B Problem]
- Counter-evidence: the THE author's fix used no AI and no replay, and his students moved from asking "if their answers were correct" to "questioning why certain outcomes occurred". It is "the strongest argument against needing AI at all" [A Decline].
- One account is "a signal, not a trend" [B WhyNow 1]. The founder never said what he sees in his own course [FR Weak].
- LLMs: default configurations vary 26–52% run to run (paper text: 26–45%), guardrails bring it to about 12–13%, human-likeness not measured [A LLM; B WhyNow 2].
- Learning evidence is "thin"; Paich and Sterman 1993 found repetition did not bring insight [A U:Learning evidence].

## 4. Capabilities committed

- In B Scope "In": accounts and persistent history; lecturer classes and live multiplayer sessions; AI in any empty role, **LLM default, rule-based per class**; full single-player mode, solo "as often as they like" [B Solution]; variable demand (fixed series, step or random) with per-class seed; debrief "computed in code and narrated by an LLM"; decision logging with seed, model and prompt version, plus provider [A U:Reproducibility]; responsive desktop, tablet, phone.
- Debrief voice: "here is where you over-ordered, here is what it cost four weeks later, here is what the other roles saw when you did it" [B Solution]. The student explains first [B Risks 6].
- Opponent hardening: order guardrails, documented personas, fixed prompt versions, rule-based fallback [B Different].
- Promised elsewhere but missing from Scope "In": AI-evaluated "precreated tasks" and AI grading "A to F or passed/not passed … Groupwise or independently" [B Solution]; lecturer and cohort analytics, roster integration, support [B Different, Biz]; replays from recorded decisions that "call no model" (mode undefined) [B Success].

## 5. Non-goals and deferrals

- Out of v1 [B Scope]: native apps; LMS (Canvas, Blackboard, Moodle); variants beyond the classic four roles; instructor-authored scenarios; institutional SSO, procurement, invoicing; RL opponents; "Anything multi-language".
- Deferred [A Deferred]: name; market sizing; hands-on checks of En Dash, Skill Dynamics, Zensimu; whether cohort reproducibility is required (5–8 lecturer interviews).
- No split-cohort test in semester one; the design goes to the PRD (issue #6) [B Success; BM].
- Rejected: positioning A, "crowded and free … hard to charge for" [FR Rejected; A Fork]. The fallback is "not a stronger bot engine" [B Success].

## 6. Success criteria, thresholds, fallbacks

All are "placeholders … the numbers need your judgement" [B Success].
- **Median solo replays per student per course > 3.** "If students play once and stop, the core thesis is wrong." This is the only kill bar [B Success; A Fork].
- Explanation: replay log plus "a simple written explanation task" [B Success].
- Opponents: run-to-run variation about 12–13%, "a low invalid-order rate" (no number), "plausible" to students (no scale) [B Success].
- Fallback 1: the LLM becomes optional, documented rule-based personas become default [B Success]. Fallback 2: "a debrief-first product with simple bots" [B Success]; forge variant: bots deferred, "which would change the architecture" [FR Weak].
- The debrief must beat a scripted one [B Different]; benchmark: En Dash's "10 scripted debrief questions" [A Comp]. No test is defined.
- Product: signup → running session "in under 10 minutes, unaided"; on time with fewer than four humans [B Success].
- Business: first paying institution outside the founder's own, "the real validation milestone"; session cost below student price; guardrail ≤ $0.10 per session, issue #8 [B Success; A U:Cost].
- Study design for the PRD: arms single session / replay only / replay plus AI debrief; pre/post stock-flow test; scored explanations; transfer to an unseen demand pattern [A U:Learning evidence].

## 7. Business model, pricing, buyer

- Two tiers, "deliberately asymmetric": cheap for students ("an impulse decision against free alternatives"), premium for institutions; no prices set [B Biz].
- Anchors: free (transentis, En Dash); eBeer $10–20 per student; Forio $168 per person; Zensimu 2024 €17.5 per participant [B Biz; A Comp].
- The student tier is an adoption channel (inferred) [B Biz]. Procurement is "measured in quarters" while inference costs from day one [A BizR]. Harvard Business Publishing is the institutional incumbent [A Comp].
- B Scope "In" has no payment flow.

## 8. Constraints and guardrails

- No vendor guarantees determinism; some Claude models reject temperature and seed; comparable cohorts need rule-based opponents [B Risks 5; A U:Reproducibility].
- Log seed, model, provider, prompt version; pin an exact model slug; freeze the model during studies [A U:Reproducibility].
- "a schema-valid order is not necessarily a legal game move" [A U:Validation].
- All numbers from the decision log; the LLM only narrates [A U:Debrief design].
- Cost: 3 AI roles × 36 turns = 108 calls; can move "by an order of magnitude" [A U:Cost; B Risks 4].
- OpenRouter data collection deny, zero retention; DPA before the first institutional sale [A U:Privacy].

## 9. Open questions and assumptions

- Name, prices, market size, hands-on competitor checks [B OpenQ].
- Thesis unproven; a no-AI product may be enough [B Risks 2–3; FR Weak].
- Unknown whether lecturers need identical results [B Risks 5].
- LLM default overrides the research advice; consequences "must be handled in the PRD and architecture" [A U:Opponent default].
- "Per-replay inference cost pulls against replay frequency" [FR Weak].
- Ambiguous [B Solution]: "This is a choice to be made be the lecturer" (which choice?); "Groupwise or independently" (tasks, grading or debrief?); who writes the "precreated tasks"?
- Stale: A Fork still calls B "a reversible drafting decision"; A Comp's "might be" contradicts its own Correction.

## 10. Conflicts and gaps vs founder v1 scope

**(a) In the sources, not in F1–F9**
- **Solo replay**: B's core and its only kill metric [B Exec, Scope, Success]. The founder's early idea included it [BM].
- Demand pattern and per-class seed; a live session that starts on time; a lecturer-run class debrief; explain-first [B Solution, Success, Risks 6].
- Instrumentation (log fields, variation, invalid orders, plausibility rating, replays, tokens); onboarding under 10 minutes; pricing tiers, roster, support; DPA; pre-test and transfer task [B Scope, Success, Biz; A U:Cost, U:Privacy, U:Learning evidence].

**(b) In F1–F9, missing or thin in the sources**
- F2: B says only "invite or roster students"; transentis needs "no accounts" [A Comp].
- F3: several games per class, game choice, auto-allocation, role choice: absent.
- F4: B has only "watch it unfold"; messaging absent.
- F5: deadlines and dropout takeover absent; B fills seats only at the start.
- F6: self-started, group or personal, deadline-bound debrief: absent.
- F7: B has only optional AI-graded tasks, outside Scope "In".
- F8: only "lecturer analytics" and "cohort analytics".
- F9: B is device-neutral.
- Undefined everywhere: game length (36 turns appears only in A U:Cost), pacing, dropout rule, notifications, deadline behaviour, a glossary (class / class session / game), who pays in v1, the cost of AI test grading and group debriefs.
- *Extractor note, not from the sources (verify):* the pilot handles student emails and grades before any "institutional sale". The EU AI Act lists AI that evaluates learning outcomes as high-risk (Annex III), and no source covers review or appeal of AI grades.

**(c) Direct contradictions**
1. **Repetition vs one game.** B: replay "as often as they like", median > 3. F1/F5/F7: one deadline-bound game → debrief → test. Without replay the kill metric cannot be measured and only the explanation half of B is tested. F1–F9 keep both differentiators (LLM opponents, decision-level debrief); bot seats and solo replay already exist at competitors [B WhyNow 3].
2. **Live vs asynchronous.** B: live sessions "the way they always have". F4–F6 imply asynchronous play. Pick a turn model or support both (F9 laptop in class).
3. **Debrief.** B: automatic "After every run", plus a lecturer-led debrief. F6: student-started, group or personal. No group AI debrief is designed anywhere.
4. **Assessment.** B: optional, "during or after the debrief", "Groupwise or independently", "done by AI". F7: always final and individual, grader unstated.
5. **Comparability.** "A shared per-class seed makes live sessions comparable" [B Solution], but LLM opponents are non-deterministic [B Risks 5], so F8 cross-class stats are confounded.
6. **Cost envelope.** A U:Cost assumes 3 AI roles; F5 takeovers can make all 4 seats AI (144 calls), and the purpose of an all-bot game is undefined.

## 11. Tone, voice, feel

- Candour: "Honest version, because the alternative gets found out in due diligence" [B Different]. B was written for investors [B frontmatter].
- Invisible mechanics: students should be "watching a supply chain oscillate", not "moving tokens and doing arithmetic" [B Problem].
- Debrief: second person, concrete, consequences, other roles' view [B Solution]; counterfactuals: "what if I had not panic-ordered in week six?" [B Problem].
- Quality bar: from "if their answers were correct" to "questioning why certain outcomes occurred" [A Decline].
- Opponents should mis-order like humans; raw LLMs "tend to optimise better than humans" [B Different].
- Moments: "for the pattern to click"; "until the intuition is theirs" [B Exec, Vision]. Reliability: starts "on time"; "accountable when it breaks mid-lecture" [B Solution; A BizR].
- Sceptic to design against: generated persona Prof. Ingrid Solheim, procurement committee: "a good debrief makes ten rounds unnecessary" [FR Voices].
- "beergame" is a working name [B header].

## 12. For a PRD addendum, not the PRD

- Cost table: per session Haiku 5.5 about $0.03, gpt-5-mini $0.09, Sonnet 5.5 $0.59, DeepSeek V4.1 Flash about $0.016; reasoning outputs Haiku about $0.13, Sonnet about $2.60; debrief about $0.003; OpenRouter +5.5% to 8% [A U:Cost].
- Provider mechanics: slug pinning, temperature and seed behaviour, ZDR [A U:Reproducibility, U:Privacy].
- LLM research figures; SSRN 5266281 "do not cite"; RL options and why rejected [A LLM, Deferred].
- Competitor tables; positioning A vs B; the research case for rules by default [A Comp, Fork, U:Opponent default; FR].
- Learning literature and full study protocol (the PRD keeps the requirement and instrumentation); runway reasoning; founder pitch angle [A U:Learning evidence, BizR, Founder].
- Generalising to other simulations: at most a note not to rule it out [B Vision].
