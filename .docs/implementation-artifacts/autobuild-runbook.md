# Autobuild runbook

The orchestrator session follows this file when it builds the stories without a human in the loop (`/goal`). The founder took the decisions in it on 2026-11-17 (Issue #35). Re-read this file after every compaction or restart.

## Sources of truth

- Stories: `.docs/planning-artifacts/epics/epics-beergame-2026-11-12/epics.md`.
- Progress: `.docs/implementation-artifacts/sprint-status.yaml`. Re-read it at the start of every story. It decides what is next, not memory.
- Decisions and draft copy: `open-assumptions.md` next to `epics.md`. Build the assumptions as they stand (Issue #31 stays open).

## Scope

- Build every story in order, Epic 1 to Epic 15, story by story.
- Leave in `backlog`, do not build: **3.15**, **15.10**, **15.14**. They need production accounts, which come after the founder has approved the site.
- Build, then set to `review` with an issue for the founder: **1.2** (the founder checks the hand-worked first ten Weeks), **2.7** (hand-run probe against a real EU endpoint), **15.9** and **15.11** (the founder fills in ops values), **15.13** (manual screen reader and keyboard checks). Say in the issue exactly what the founder must do. Later stories build on the code as if the story were done.
- Everything runs locally: Postgres in Docker, files in `./.local-storage/`, mail as `[email:mock]`, the AI mock by default (AD-17). Never create a cloud account, project or deploy.
- The LLM provider key in `.env` may be used only where a story asks for a real endpoint (2.7, 2.11). Never print, log or commit a key.

## One story

1. Read `sprint-status.yaml`. The next story is the first `backlog` story in file order that is not on the skip list. Set it to `in-progress`, and its epic to `in-progress` if it was `backlog`.
2. Check the branch: `epic-<N>` from an up-to-date `main`. Create it if it is missing. The working tree must be clean.
3. Launch **one blocking subagent** (never in the background) with this prompt, filled in:
   > Run the skill `bmad-build-auto` with this intent: "Story <N.M> «<title>» from `.docs/planning-artifacts/epics/epics-beergame-2026-11-12/epics.md` (Epic <N>). Build only this story." Work in `D:\IBE160\2026\beergame` on branch `epic-<N>`. When the skill halts, report its final status, the spec file path, the commits it made, and any blocking condition.
4. Read the result.
   - **done**: set the story to `done`, or to `review` if it is on the founder list.
   - **blocked**: solve the problem yourself as well as you can. Read the spec's `## Auto Run Result`, fix the cause (a missing piece of an earlier story, a flaky test, an unclear criterion: choose the reading closest to `epics.md`, the PRD and the spines), set the spec's `status` back to the step it should resume at, and run step 3 again. Open an issue (label `agent`, title `Story <N.M>: …`) that states the problem and every decision you took. After three failed attempts on the same story, leave it `blocked` in `sprint-status.yaml`, record it in the issue, and go on to the next story that does not depend on it.
   - **Deferred findings** in the spec (`deferred:` in its frontmatter) that matter beyond the story: one issue, label `agent`.
5. Commit `sprint-status.yaml` (`Sprint: Story <N.M> <status>`), then push the branch.
6. Session log: one log file for the whole run in `.logs/bard-pettersen/`, created once with the naming of the `sesjonslogg` skill (next lower number, title `autobygg-alle-stories`) and reused after that. Add a section per story with Oppgave, Plan, Resultat (spec file, commits, tests, status) and Åpne punkter (`Issue #N`). Write it in Norwegian. Commit only the log file (`Logg: autobygg Story <N.M>`), and push.

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

## Done

The goal is reached when every story outside the skip list is `done`, `review` or (after three attempts) `blocked`, every epic is merged to `main` with CI green, and a final log section lists the `review` and `blocked` stories with their issues.
