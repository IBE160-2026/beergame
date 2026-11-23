# Autobuild runbook

The orchestrator session follows this file when it builds the stories without a human in the loop (`/goal`). The founder took the decisions in it on 2026-11-17 (Issue #35). Re-read this file after every compaction or restart.

## Sources of truth

- Stories: `.docs/planning-artifacts/epics/epics-beergame-2026-11-12/epics.md`.
- Progress: `.docs/implementation-artifacts/sprint-status.yaml`. Re-read it at the start of every story. It decides what is next, not memory.
- Decisions and draft copy: `open-assumptions.md` next to `epics.md`. Build the assumptions as they stand (Issue #31 stays open).

## Scope

- Build every story in order, Epic 1 to Epic 15, story by story.
- Leave in `backlog`, do not build: **3.15**, **15.10**, **15.14**. They need production accounts, which come after the founder has approved the site.
- No human in the loop (founder, 2026-11-17). Where a story asks the founder to check something, an independent review agent does it instead, and the story is `done` when the check passes: **1.2** (the agent hand-works the first ten Weeks from the rules, without the builder's table), **2.7** (the agent runs the probe against a real EU endpoint with the key in `.env`), **15.9** and **15.11** (the agent chooses the ops values and records them in an issue), **15.13** (keyboard, focus and accessibility checks with Playwright CLI, `@playwright/cli`, and axe). Record every choice the founder would have made in an issue.
- Tests must be fast (founder, 2026-11-18). Agents run only the tests for the files they touch while working, and the full suite once before the commit. The full backend suite took 42 s locally after the speed-up on 2026-11-18. If it passes about 90 s, measure with `--durations` and fix the slowest tests before the next story.
- Reviews and visual checks use other agents and Playwright CLI (`npx @playwright/cli@0.1.24`, bin `playwright-cli`), never a person.
- Everything runs locally: Postgres in Docker, files in `./.local-storage/`, mail as `[email:mock]`, the AI mock by default (AD-17). Never create a cloud account, project or deploy.
- The LLM provider is OpenRouter with the model `deepseek/deepseek-v4.1-flash-1017` (founder, 2026-11-17, Issue #9). The OpenRouter key in `.env` may be used only where a story asks for a real endpoint (2.7, 2.11). Never print, log or commit a key.

## One story

1. Read `sprint-status.yaml`. The next story is the first `backlog` story in file order that is not on the skip list. Set it to `in-progress`, and its epic to `in-progress` if it was `backlog`.
2. Check the branch: `epic-<N>` from an up-to-date `main`. Create it if it is missing. The working tree must be clean.
3. Launch **one blocking subagent** (never in the background) with this prompt, filled in:
   > Run the skill `bmad-build-auto` with this intent: "Story <N.M> «<title>» from `.docs/planning-artifacts/epics/epics-beergame-2026-11-12/epics.md` (Epic <N>). Build only this story." Work in `D:\IBE160\2026\beergame` on branch `epic-<N>`. When the skill halts, report its final status, the spec file path, the commits it made, and any blocking condition.
4. Read the result.
   - **done**: set the story to `done`, or to `review` if it is on the founder list.
   - **blocked**: solve the problem yourself as well as you can. Read the spec's `## Auto Run Result`, fix the cause (a missing piece of an earlier story, a flaky test, an unclear criterion: choose the reading closest to `epics.md`, the PRD and the spines), set the spec's `status` back to the step it should resume at, and run step 3 again. Open an issue (label `agent`, title `Story <N.M>: …`) that states the problem and every decision you took. After three failed attempts on the same story, leave it `blocked` in `sprint-status.yaml`, record it in the issue, and go on to the next story that does not depend on it.
   - **Deferred findings** in the spec (`deferred:` in its frontmatter) that matter beyond the story: one issue, label `agent`.
5. **Visual check, for every story that adds or changes a screen** (from Story 3.1 on; skip stories with no change under `frontend/`). Launch one blocking subagent that:
   - starts the app with `docker compose up` and reaches the story's screens at `http://localhost:8080` with Playwright, as the Role the story is for, using the same seed and test login as the story's Playwright tests;
   - takes full-page screenshots at 390 px and 1280 px wide of each state the story names (empty, filled, error and so on), and saves them to `.docs/implementation-artifacts/screenshots/<N.M>/` as `<screen>-<state>-<width>.png`;
   - opens each screenshot and compares it with the matching mockup in `.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/mockups/` and with `DESIGN.md` and `EXPERIENCE.md`, which win over the mockup on conflict: layout, tokens, type, copy from `nb.ts`, one primary button, and nothing cut off or scrolling sideways at 390 px;
   - fixes clear deviations on the branch, reruns the story's tests and takes the screenshots again; records any deviation it does not fix, or that needs a judgement, in one issue (label `agent`, title `Story <N.M>: visuelle avvik`) with the screenshot paths;
   - writes `.docs/implementation-artifacts/screenshots/<N.M>/README.md` with one line per screenshot: what it shows and whether it matches;
   - stops the app with `docker compose down`.
   The founder looks at these screenshots when approving the site.
6. Commit fixes from the visual check on their own (`Story <N.M>: visuelle rettinger`), then commit `sprint-status.yaml` and the story's screenshots (`Sprint: Story <N.M> <status>`), and push the branch. The working tree must be clean before the next story.
7. Session log: one log file for the whole run in `.logs/bard-pettersen/`, created once with the naming of the `sesjonslogg` skill (next lower number, title `autobygg-alle-stories`) and reused after that. Add a section per story with Oppgave, Plan, Resultat (spec file, commits, tests, status) and Åpne punkter (`Issue #N`). Write it in Norwegian. Commit only the log file (`Logg: autobygg Story <N.M>`), and push.

## End of an epic

1. When no story of the epic is left in `backlog` or `in-progress`, open a pull request from `epic-<N>` to `main` and wait for CI (`gh pr checks --watch`).
2. CI red: fix it on the branch, as for a blocked story, with an issue that states the decisions. CI green: merge (`gh pr merge --merge`), set `epic-<N>: done`, and start the next epic from the new `main`.
3. Until Story 1.1 has added CI, there is nothing to wait for; run the tests locally instead.

## Rules

- Never `git push --force`, never rewrite pushed history, never delete a branch other than a merged `epic-<N>`.
- Never touch Docker containers, images or volumes that are not this project's compose services. Use `docker compose down`, not `docker rm`.
- Never edit `.env`, `.claude/settings*.json`, or files outside the repo.
- Issues are public: no secrets, no names of other projects, no personal data.
- Ask nobody. The founder is not watching. Decide, record the decision in an issue, and go on.

## Lessons from Epics 1–4 (2026-11-19)

- Sub-agents run in the background here. Tell the builder to implement in its own context. Review sub-agents may be cut off; then resume the builder and have it read their results from the transcripts.
- Give every builder: folders `backend/`/`frontend/`, the OpenRouter decision, no human in the loop, fast tests (targeted while working, full suites once), never drop `olspillet_test*`, never compare DB time with host time (Issue #63), step 1 in about 10 minutes, compose builds as `timeout 900 docker compose up -d --build --wait …`, and `docker compose rm -sf <services>` afterwards with `postgres` left running.
- Test logins (`APP_ENV=local`, password `olspillet-demo`): `admin@`, `faglaerer@`, `admin-faglaerer@`, `assistent@`, `student@`, `student2@`…`student8@example.com`. The demo Class is «class-of-1994». Never archive or change it in tests or visual checks; create fresh data.
- The visual check runs the whole Vitest suite (under 2 s) and `lint:colours`, not only the touched files. Clear UX defects it finds go to the next story on the same page, or to the end-of-epic review.
- At the end of each epic: one follow-up review agent (late patches, collected UX items, races), one e2e stabilisation pass, then the PR.
- The OpenRouter key in `.env` is blocked for agents by the safety filter. Stories that need a real call are built against the mock and set to `review` with the exact commands (Issues #56, #60).

## Lessons from Epics 5–6 (2026-11-21)

- Builders sometimes end their turn while their review sub-agents run, which loses the review. Say in the prompt that this counts as a hand-back; when it happens, resume the builder with SendMessage to read the reviewers' transcripts and finish.
- If a builder has no spec after about 30 minutes, send a status message; it unblocks a stuck step 1.
- The full Playwright suite reached 7 minutes (395 tests, `--workers=2`). From Story 6.14 on, builders run the Playwright files for the screens they touch plus the play-screen and `homes` specs, and keep axe to one check per width. The full suite runs in CI on every push, in a visual check when shared components change, and at the end of each epic.
- Keep a running list of items for the end-of-epic review in the scratchpad while the epic is built (small UX fixes, slow tests, specs with `followup_review_recommended: true`).
- A real started Class game needs the Start date passed and the lock sweep. For local e2e and the end-to-end journeys (GOAL item 4), use the local-only `POST /api/dev/class-sessions/{id}/lock` (Story 6.15).
- From Story 6.15 on, builders use two review sub-agents (blind and edge case), four only for risky changes. This cut a story from about 50 to 20–40 minutes with no visible loss.
- Compose for e2e is `timeout 900 docker compose up -d --build --wait proxy worker-batch worker-ai` (CI starts `worker-ai` too). Playwright launches Chromium with `--lang=nb-NO`, so native date fields show Norwegian format.
- In e2e, never let a live update race a click (commit 07345fa), and remove routes before a test's pages close (commit 1e12ffa).
- Shared backend fixtures in `backend/tests/games/helpers.py` play a game once per run; new tests reuse them instead of playing weeks over the API.

## Two lanes (from Epic 7, 2026-11-21)

The founder asked for more speed (2026-11-21). From Epic 7 on, two epics are built at once, one story at a time in each lane.

- **Lane 1**, the main folder `D:\IBE160\2026\beergame`: Epic 7, then 8. Default stack: project `olspillet`, port 8080, Postgres 5432.
- **Lane 2**, the worktree `D:\IBE160\2026\beergame\.claude\worktrees\lane-2`: Epic 9, then 10, 11, 12. It needs only finished games, which exist since Epic 6. Its stack and tests run with these variables in the same shell command: `COMPOSE_PROJECT_NAME=olspillet-lane2`, `IMAGE_TAG=lane2`, `HTTP_PORT=8081`, `POSTGRES_PORT=5433`, `E2E_BASE_URL=http://127.0.0.1:8081`, `DATABASE_URL=postgresql+psycopg://olspillet:olspillet@localhost:5433/olspillet`. `PUBLIC_BASE_URL` stays at its default, so mailed links still read 8080. Lane 2 never touches lane 1's stack.
- Then Epics 13 and 14, which need both lanes, and 15, which goes in whichever lane is free first.
- The next story of a lane is the first `backlog` story of that lane's epic. If a story needs work from the other lane that is not on `main` yet, skip it for now and take the next one.
- Only the orchestrator edits `sprint-status.yaml` and the run log, and only in lane 1's folder and branch. Lane 2's branch carries code, specs and screenshots only.
- Alembic: lane 1 numbers new migrations from 0051, lane 2 from 0101. Before an epic's PR, merge `main` into the epic branch. If there are two heads, set `down_revision` of the branch's first new migration to `main`'s head.
- Prompts for both lanes: `story-prompt-lanes.md` in the scratchpad (recreate from this section if it is gone).

## Faster flow (founder, 2026-11-21)

- Two lanes use at most `--maxprocesses=8` for pytest and `--workers=4` for Playwright each; more overloads the machine (database timeouts, flaky e2e). `week-advance` holds 2 s in CI and 3 s locally.
- The visual check is off the critical path. When a builder reports `done`, push, start the lane's next builder at once, and run the visual check at the same time. The visual check only takes screenshots, writes the README and reports; it never edits code. Clear defects it finds go into the next builder's prompt on the same page, or into the end-of-epic list. The screenshots are committed with the story's status.
- A report-only visual check runs in its own detached worktree at the story's commit, with its own compose project and ports, unique per check (for example `olspillet-v<story>` on 8095+n / 5435+n), and starts with `docker compose down -v` for that project. Two checks never share a project name or image tag. Screenshots go to the scratchpad; the orchestrator copies them into the story's branch.
- Start the next builder before writing the log section and the issue.
- One review sub-agent for low-risk stories (frontend only, read-only views, copy); two by default; four for risky ones (data model, access, concurrency, money).
- End of an epic in parallel: one agent runs the follow-up review, the stabilisation (full suites with the other lane idle in tests, or accepting its load), the PR and CI on the epic branch, while the lane starts the next epic on a branch made from the finished epic branch. Merge `main` into that branch after the PR is merged.
- Shared files (`nb.ts`, the generated api client, routers) conflict at that merge. Resolve them by keeping both sides, then regenerate the api client and run the full suites.
- Visual check: rebuild only `frontend` (`--build frontend`, the rest from the last build), and skip it for stories with no change under `frontend/`. Review sub-agents and the visual check run on Sonnet; builders stay on Opus. One review sub-agent for low-risk stories, two by default, four for risky ones.
- Lane 1's visual check of story N may run while lane 1 builds story N+1 only in its own worktree. Default: run it after, as before.

## Run plan from 2026-11-22 (founder)

| Lane | Now | Next | Then |
|---|---|---|---|
| 1 (main folder) | Epic 8 (8.8–8.14), then the Epic 8 close-out | **stop for `/compact`** | Epic 11 |
| 2 (`.claude/worktrees/lane-2`) | Epic 10 (10.1–10.9), then the Epic 10 close-out | **stop for `/compact`** | Epic 12 |
| close-out agent | Epic 9 close-out (merge with main, fixes, PR #?) | merge Epic 9, then Epic 8 and 10 when their PRs are green | |

- **Stop rule (founder, 2026-11-22):** do not start Epic 11 or Epic 12 until the founder has run `/compact`. When a lane finishes its epic and close-out, let it wait; tell the founder, and start Epic 11 (lane 1) and Epic 12 (lane 2) only after the compact.
- Epic 12 builds on the Individual test (Epic 11). Start lane 2 with the 12.x stories that stand alone (12.1, 12.7–12.10 Control test setup) and take 12.2–12.6 once the Epic 11 pieces they need are on its branch or `main`; skip a story that needs missing work and come back to it.
- After 11 and 12: Epic 13 and 14 (they need 9–12), and Epic 15 in whichever lane is free. Skip 3.15, 15.10 and 15.14.
- Merge order: Epic 9, then 8, then 10 (each merges `main` first and relinks Alembic: lane 1 numbers 005x, lane 2 01xx; the epic that merges second sets its first migration's `down_revision` to `main`'s head).
- Open items for close-outs are in the scratchpad lists `epic8-todo.md`, `epic9-todo.md` (recreate from the story issues if lost). The «Pause n» filter WIP backend is `pause-filter-wip.patch` in the scratchpad.
- Stories in `review` so far (real-model check for the founder): 2.7 (#56), 2.11 (#60), 9.14 (#173), 9.15 (#176).

## Resume point (2026-11-22, before `/compact`; weekly limit hit, resets 19:00 Europe/Paris)

All stories of Epics 7–10 are built; 7 and 9 are merged to `main` (PRs #165, #179). Both close-outs stopped mid-work on the usage limit:
- **Epic 8 close-out** (main folder, branch `epic-8`): the merge of `origin/main` is committed locally as 420544e («Merge origin/main (Epics 7 and 9) into epic-8»), not pushed and not yet tested. Next: check the Alembic chain has one head (epic-8's 0053 must follow main's 0113), run the full backend suite on a fresh stack (project `olspillet-e8`, 8090/5434), then tasks 2–7 of the close-out (visual 8.14 + 8.1 columns, MUST «Pause n» filter from `pause-filter-wip.patch`, MUST test speed, UX list in `epic8-todo.md`, stabilisation, PR, CI, issue «Epic 8: avslutning»). Resume the agent `close-epic-8` with SendMessage, or start a new one with the same brief.
- **Epic 10 close-out** (`.claude/worktrees/lane-2`, branch `epic-10`): uncommitted fixes in progress (scenario errors, play screen at 200 %, walkthrough chart labels, «Send svar» names, Replay block, test speed in `games/helpers.py`). Resume the agent `close-epic-10`, or start a new one that first reviews `git diff`, finishes the MUSTs from `epic10-todo.md`, then stabilises, opens the PR and reports.
- Merge each PR yourself when CI is green; the second to merge relinks Alembic to `main`'s head. Then set `epic-8`/`epic-10` done in `sprint-status.yaml`, log both close-outs, and **stop: wait for the founder's `/compact` before Epic 11 (lane 1) and Epic 12 (lane 2)** — unless the founder has already run it and says go.
- Stray empty untracked files at the repo root (`policy.py`, `walkthrough-chart.tsx`) are not ours to stage; the founder may delete them.
- Scratchpad lists (`epic8-todo.md`, `epic10-todo.md`, drafts) may vanish; the story issues #143–#195 hold the same items.

## Re-plan after the compact (2026-11-22)

- The founder ran `/compact` and said go. Epic 10 merged first (PR #196, e9817a0); Epic 8's close-out merges `main` again and relinks its 0053 after 0119.
- Epic 12 is not standalone: 12.2–12.10 need Epic 11 (question set, Scoring guide, answers). 12.1 is built on `epic-12` (a753981, migration 0120, a minimal `sessions.lock_test` seam).
- **Lane 2** now builds **Epic 11** on `epic-11`, made from `epic-12` (so it carries 12.1). Migrations from 0121. After Epic 11, lane 2 continues Epic 12 (12.2–12.10) on `epic-12` after merging `epic-11`/`main` into it.
- **Lane 1**, after the Epic 8 close-out merges: **Epic 15** (skip 15.10, 15.14) on `epic-15` from `main`, migrations from 0064 (relinked at merge). A story that needs Epics 11–14 is skipped and taken later.
- Then Epics 13 and 14.
- Faster close-outs: visual checks deferred to a close-out are done there once, in one pass. Only one lane runs the full Playwright suite at a time; the other runs targeted specs. Do not edit files by relative path with .NET (`[IO.File]`): its working directory is not PowerShell's location.
- Memory: Docker's WSL VM can hold 20+ GB page cache after many builds. Free it with `wsl -d docker-desktop -u root sh -c "echo 1 > /proc/sys/vm/drop_caches"` and `echo 1 > /proc/sys/vm/compact_memory`; stop leftover `tail -f` processes older than an hour.

## Resume point (2026-11-23, before the founder's `/compact`)

Merged to `main`: Epics 1–12 (PRs #165, #179, #196, #199, #224, #240). Three folders, at most three builders:
- **Lane 1**, main folder, `epic-15` (holds `sprint-status.yaml` and the run log; commit only these two with explicit paths): 15.2, 15.4–15.9, 15.11, 15.13, 15.6 done; 15.12 `review` (#247, founder decides `REQUIRE_DPA_FOR_INVITATIONS`). Main (Epics 11–12) is merged in; head 0071. Left: **15.1** (needs 13.7) and **15.3** (needs 13.9) after Epic 13 merges; then the Epic 15 close-out. Stack: `POSTGRES_DB=olspillet_e15b`, pytest `olspillet_e15b_t`.
- **Lane 2**, `.claude/worktrees/lane-2`, `epic-13`: 13.1–13.11 done; main (Epic 12) merged in (811cab7: 0301 after 0209, head 0306; one Studentside policy `student_pages.read`; `reports/scope.py` uses 12.7/12.8). Stack: `olspillet_m6`, `POSTGRES_DB=olspillet_app6`. Left: 13.12, 13.13, 13.14, then the Epic 13 close-out (list `epic13-todo.md`).
- **Lane 3**, `.claude/worktrees/lane-3`, `epic-14` (stack 8082/5434): 14.1, 14.2, 14.5, 14.6 done. Left: 14.3 and 14.4 (need 15.3 and 13.9), 14.7 (needs 14.3/14.4), 14.8 (needs 13.13), then the close-out (list `epic14-todo.md`). Epic 14 uses local scope stand-ins to relink to Epic 13's `reports.scope` at merge.
- Order from here: finish Epic 13 → merge 13 → epic-14 and epic-15 merge main → 15.1, 15.3, 14.3, 14.4, 14.7, 14.8 → close-outs of 14 and 15 → merge → user journeys with Playwright (GOAL item 4, a whole game with test users and a test lecturer) → final log section listing review/blocked stories (2.7 #56, 2.11 #60, 9.14 #173, 9.15 #176, 10.7, 15.12 #247).
- Builder briefs are in the scratchpad: `brief-lane1.md`, `brief-lane2.md`, `brief-lane3.md` (agents spawned without a name; no SendMessage reports). Close-out lists `epic13-todo.md`, `epic14-todo.md`; queued log sections in `pending-log.md`.
- Stray untracked root files `policy.py`, `walkthrough-chart.tsx`, `nb.ts` are not ours.

## Done

The goal is reached when every story outside the skip list is `done`, `review` or (after three attempts) `blocked`, every epic is merged to `main` with CI green, and a final log section lists the `review` and `blocked` stories with their issues.
