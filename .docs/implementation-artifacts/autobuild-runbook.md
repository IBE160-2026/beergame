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

## Done

The goal is reached when every story outside the skip list is `done`, `review` or (after three attempts) `blocked`, every epic is merged to `main` with CI green, and a final log section lists the `review` and `blocked` stories with their issues.
