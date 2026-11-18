---
title: 'Story 3.1: See «Logg inn» in the product''s design'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: 'c2f300eaea7ef84bd857f7425b4d3131ec70929e'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
warnings: [oversized]
deferred:
  - summary: >-
      The «Glemt passord?» link leads to a not-found page until Story 3.6 builds /glemt-passord.
    evidence: |-
      login-form.tsx links to /glemt-passord, and no route exists. EXPERIENCE.md puts the link on Logg inn, and Story 3.6 owns the page. Production deploy (3.15) comes after 3.6.
    location: >-
      frontend/src/modules/identity/login-form.tsx
    severity: low
  - summary: >-
      The deactivated-account copy reveals that the account exists, and it tells staff to contact "faglæreren din".
    evidence: |-
      nb.auth.login.deactivated is EXPERIENCE.md's own string (FR-3). The epic rule says login never reveals whether an account exists, and the string is wrong for a deactivated Lecturer or Admin. Settle it in Story 3.2, where it is wired, or in the copy review (Issue #31).
    location: >-
      frontend/src/copy/nb.ts
    severity: medium
  - summary: >-
      Nothing enforces that components, modules and pages hold no literal UI strings outside nb.ts.
    evidence: |-
      check-copy.mjs reads src/copy, the print route and the templates only. JSX text in src/components, src/modules and src/app is not scanned. This holds today by inspection.
    location: >-
      frontend/scripts/check-copy.mjs
    severity: medium
  - summary: >-
      No product test renders pages with 200 % text.
    evidence: |-
      DESIGN.md asks product tests to render at 200 % text (Faglærer pages and Graf over tabell). Story 3.1's ACs name only 320, 360, 1440 px and 400 % zoom. Controls now use min-height, so they grow with text.
    location: >-
      frontend/e2e/
    severity: low
---

<intent-contract>

## Intent

**Problem:** The web app has no theme, no shared controls, no copy home and no browser tests. «Logg inn» is the first real screen, and every later screen depends on the foundation it lays.

**Approach:** Commit DESIGN.md's front-matter tokens as one token file, generate the Tailwind v4 theme from it, and self-host Source Sans 3. Add copy and colour checks, and build Knapper, Lenke and Tekstfelt. Then build a `/logg-inn` page that validates on the client and sends nothing. Vitest covers units and checks. Playwright with axe covers the page through `docker compose` at `http://127.0.0.1:8080`.

## Boundaries & Constraints

**Always:**
- `paper` is the only background. Light theme only. No shadows, no gradients, no all caps and no letter-spacing.
- Text sizes are in `rem`/`em`, and no text on a phone is under 13 px. Controls use `rounded.sm`. Idle borders are `ink-muted`.
- The focus ring is 2 px `ink` with a 2 px `paper` gap (outline plus offset) on every interactive element.
- Lining tabular figures are the app-wide default. Proportional figures appear only on `figure-hero` and `figure-amplification`.
- Every UI string comes from `frontend/src/copy/nb.ts`, written in bokmål with no exclamation marks.
- A control that becomes unavailable takes `aria-disabled="true"` and keeps focus. It never gets the native `disabled`.
- Exact dependency versions, each at least two weeks old: vitest 5.1.0, @playwright/test 1.65.0, @axe-core/playwright 4.14.0, @fontsource/source-sans-3 5.3.1, yaml 2.9.1.
- Tests stay fast: Vitest runs in the node environment, and Playwright runs Chromium only.

**Never:**
- No API call and no login logic (Story 3.2). No TanStack Query and no generated client.
- No request to Google Fonts. No literal colour outside the theme files. No Tailwind default colours, radii, text sizes or shadows.
- No dark theme, no icons, no illustrations.
- Do not edit `sprint-status.yaml`, `.env` or `.claude/settings*.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty submit | Both fields empty, press «Logg inn» (click or Enter) | Both fields invalid: `restordre` border, reason under the field, `aria-invalid`, reason tied by `aria-describedby`. Focus moves to the first invalid field | Nothing is sent |
| Malformed e-mail | `ola`, `a@@b.no`, `ola@` or `ola@uib` | E-mail reason: «Mangler @» / «To @» / «Domene mangler» / «Domene mangler» | Nothing is sent |
| Valid input | `ola@uib.no` plus any password | No error shown, nothing happens (login comes in Story 3.2) | No request to `/api` |
| Fixing a field | The field was invalid, and the user types a valid value | The error clears when the field is left or the form is pressed again | — |

</intent-contract>

## Code Map

- `frontend/package.json` -- scripts and pinned versions. Has typecheck and build so far. Add test, test:e2e, check:copy and lint:colours, with lint:colours as `prebuild`.
- `frontend/src/app/layout.tsx` -- root layout, `lang="nb"`, imports `globals.css`. Add the fontsource imports here.
- `frontend/src/app/globals.css` -- only `@import "tailwindcss"` today. Becomes the import of `theme.css` plus the base rules.
- `frontend/src/app/page.tsx` -- empty `/`. Leave it alone (the Landing page is Story 3.13).
- `frontend/src/lib/utils.ts` -- `cn()` from the shadcn setup (Story 1.1). Reuse it in the components.
- `frontend/components.json` -- shadcn config with the `@/components` alias. The new components go in `src/components/`.
- `frontend/Dockerfile` -- `npm run build` in the build stage. `prebuild` runs there, so `scripts/` must be in the context (it is).
- `docker-compose.yml`, `proxy/Caddyfile` -- the proxy on port 8080 routes everything except `/api` and `/print` to the frontend. No change needed.
- `.github/workflows/ci.yml` -- the frontend job runs `npm ci`, typecheck and build. Add Vitest and the copy check, plus an e2e job against compose.
- `.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md` -- read-only token source (front matter: colors, typography, rounded, spacing). Text-on-tints table under Colors. Interaction states under Components.
- `backend/app/**/templates/` -- none exist yet. The copy check globs these paths so that Story 3.5 is covered.

## Tasks & Acceptance

**Execution:**
- `frontend/package.json`, `frontend/package-lock.json` -- add the pinned devDeps and `@fontsource/source-sans-3`. Add the scripts. Make `prebuild` run the colour lint.
- `frontend/src/theme/tokens.json` -- a verbatim copy of the `colors`, `typography`, `rounded` and `spacing` groups from DESIGN.md's front matter. It is the theme's one source.
- `frontend/scripts/build-theme.mjs` -- generates `src/theme/theme.css` from `tokens.json` as Tailwind `@theme static`. It resets the colour, text, radius and shadow namespaces, writes px font sizes and px line heights as rem, and writes the proportional-figure rule for the two figure roles. Run it, and commit the output.
- `frontend/src/app/globals.css` -- import tailwind and the theme. Base rules: `paper` background, `ink` text, the Source Sans 3 stack, default lining tabular figures, `text-transform: none`, and a `focus-ring` utility.
- `frontend/src/app/layout.tsx` -- import `@fontsource/source-sans-3` 400, 600 and 700.
- `frontend/src/theme/contrast.ts`, `frontend/src/theme/text-on-tint.ts` -- the WCAG ratio, the text-on-tints table plus the interaction-state fill pairs, and `isAllowedTextOn(bg, text)`.
- `frontend/src/copy/nb.ts` -- the PRD-term to UI-string map (`terms`), the voice rules as data, and the `auth.login` strings.
- `frontend/src/components/button.tsx`, `link.tsx`, `text-field.tsx` -- Knapper (primary and secondary), Lenke and Tekstfelt with the shared states. `Button` maps `unavailable` to `aria-disabled` and swallows presses.
- `frontend/src/modules/identity/validate-login.ts`, `login-form.tsx`; `frontend/src/app/(auth)/logg-inn/page.tsx` -- client validation, the form and the page: the «ØL-spillet» header, the h1 «Logg inn», a short lead, E-post, Passord, the primary «Logg inn» and the link «Glemt passord?».
- `frontend/scripts/check-copy.mjs` -- the voice and forbidden-word check over the `nb.ts` strings (TypeScript AST), the Jinja2 templates and the print route. Exits non-zero on a hit.
- `frontend/scripts/lint-colours.mjs` -- fails on hex or colour-function literals and on named CSS colours in `src/` outside `src/theme/`.
- `frontend/vitest.config.ts` plus tests: tokens versus DESIGN.md versus theme.css, contrast, class pairs used in `.tsx` that are outside the table, the copy check (on the repo and on bad samples), the colour lint (on the repo and on bad samples), `validateLogin` edge cases, and the Button and TextField markup.
- `frontend/playwright.config.ts`, `frontend/e2e/logg-inn.spec.ts` -- the page at 320, 360, 1440 and 320×256 (400 % zoom). Checks: axe WCAG 2.1 AA, no horizontal scroll, keyboard path, tap targets ≥ 44 px, text ≥ 13 px, no Google Fonts request, Source Sans 3 loaded, all theme CSS variables present, and the empty or malformed submit with no request.
- `.github/workflows/ci.yml` -- the frontend job runs Vitest and `check:copy`. A new `e2e` job runs `docker compose up --build --wait`, then Playwright, then `down`.
- `README.md` -- the frontend test commands.

**Acceptance Criteria:**
- Given the «Logg inn» page, when it renders at 320, 360 and 1440 px and at 400 % zoom, then axe reports no WCAG 2.1 AA violation, there is no page-level horizontal scroll, and every control is at least 44 px tall on the phone.
- Given the theme, when a token in `tokens.json` is missing from `theme.css` or has another value there, or `tokens.json` differs from DESIGN.md's front matter, then Vitest fails.
- Given a literal colour in `src/` outside `src/theme/`, when `npm run build` runs, then the build fails.
- Given `nb.ts` or a template with «!», «øl» outside «ØL-spillet», «optimal», «fasit», or (before the Debrief) «Beer Game» or «bullwhip», when `npm run check:copy` runs, then it fails.
- Given the page, when it is used by keyboard only, then Tab reaches E-post, Passord, «Logg inn» and «Glemt passord?» in that order, each with a visible focus ring, and Enter on «Logg inn» runs validation.

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 53 findings — high 1, medium 9, low 26, false 6, maybe-false 0. Some low items were patched.
- Blind Hunter:
  - `[medium]` `defer` «Glemt passord?» leads to a not-found page. Story 3.6 builds the route (see `deferred`).
  - `[medium]` `defer` The deactivated copy reveals that the account exists, and its wording is wrong for staff. The string comes from EXPERIENCE.md, and the copy is settled in 3.2 or Issue #31.
  - `[false]` `reject` «Invitasjon» capitalised mid-sentence. The product capitalises glossary terms in running text («Du får Rolle og spill», «Uke 11»).
  - `[low]` `patch` The product name was repeated in the page title. Patch: the layout has the template `%s – ØL-spillet`, and `pageTitle` is now «Logg inn».
  - `[medium]` `patch` Input text under 16 px makes iOS zoom in. Patch: the input uses the `button` size (16 px) at weight 400.
  - `[medium]` `patch` A fixed 50 px height clips content when text grows. Patch: Button and TextField use `min-h-control-height-phone` with vertical padding. Spacing tokens stay px, as DESIGN.md has them.
  - `[low]` `defer` No 200 % text test. That test is not in this story's ACs (see `deferred`).
  - `[medium]` `defer` The copy check does not scan components for literal strings (see `deferred`). Template attributes and entities were patched under the Edge Case Hunter rows.
  - `[medium]` `patch` The colour lint missed shorthand properties and most named colours. Patch: all 148 names; border, outline, box-shadow and text-decoration shorthands; `color()` and `light-dark()`; no hex hits after `href="`, `url(` or `.`.
  - `[low]` `patch` E2E tests had rgb values hard-coded. Patch: they are derived from `tokens.json`.
  - `[low]` `patch` The CI e2e job kept no traces and had no timeout. Patch: an `upload-artifact` step on failure, and `timeout-minutes: 20`.
  - `[low]` `reject` The checks run twice in CI. This is deliberate: the Vitest tests guard the check logic, and the CI steps are the AC gates. Both are fast.
  - `[low]` `reject` The contrast scan reads only double-quoted strings. The current code uses only those. Covering every literal kind and parent backgrounds adds complexity no current component needs.
  - `[low]` `reject` A second invalid field is not announced. Focus moves to the first invalid field, which reads its reason. Each other field's reason is read when it gets focus (WCAG 3.3.1 is met). A live summary is new surface.
  - `[false]` `reject` The spec is left out of the diff. By design, the claims file goes to the edge-case layer only.
  - `[low]` `patch` The tap-target test asserted a count of controls. Patch: it now asserts the known controls by name.
- Edge Case Hunter:
  - `[high]` `patch` A press before hydration made a native GET submit, which put the password in the URL. Patch: `method="post"` on the form.
  - `[medium]` `patch` Focus moved before React committed `aria-invalid` and `aria-describedby`. Patch: focus now moves in a `useEffect` after the commit.
  - `[low]` `patch` A caller's own `aria-describedby` overrode the error tie. Patch: `{...props}` is spread before the aria attributes.
  - `[low]` `patch` A caller's `aria-disabled` could disagree with the click guard. Patch: `aria-disabled` is left out of `ButtonProps`.
  - `[medium]` `patch` The named-colour list was incomplete, and `color()` and `light-dark()` were missing. Patch: see the colour-lint row above.
  - `[low]` `patch` The hex check hit `href="#add"` and private fields. Patch: the lookbehinds above, with tests.
  - `[low]` `reject` A colour value split across lines, or a colour in .json under src/. Rare, and the fix needs a parser.
  - `[medium]` `patch` Copy inside Jinja code, and in alt or title attributes, was not checked. Patch: string literals in Jinja code, the alt, title, aria-label and placeholder attributes, and `&#33;` entities are now read. Tests added.
  - `[low]` `patch` Template line numbers were off. Patch: removed spans keep their newlines, with a test.
  - `[low]` `patch` A className "!" or a literal type in the print route was treated as copy. Patch: className and style attributes and literal types are skipped, with a test.
  - `[low]` `reject` Computed or shorthand section keys in nb.ts. nb.ts uses literal keys only, and the fix adds resolution logic.
  - `[medium]` `patch` Tailwind's letter-spacing utilities were not reset. Patch: `--tracking-*: initial`, with a theme-test update.
  - `[medium]` `patch` `document.fonts.check` passes even when the font is missing. Patch: the test now checks that the Source Sans 3 FontFace entries are loaded at 400, 600 and 700.
  - `[low]` `reject` The contrast scan reads only some literal kinds (same as the Blind Hunter row).
  - `[low]` `patch` A temp dir was left behind when a test failed. Patch: `try/finally`.
  - `[low]` `patch`/`reject` globals.css had no `text-transform: none` and no focus-ring utility. Patch: `text-transform: none` and `letter-spacing: normal` on html. The focus ring is a global `:focus-visible` base rule, which covers every interactive element without a class, so no utility was added.
  - `[low]` `reject` The voice rules are not stored as data. As strings in nb.ts, the "don't" examples would trip the copy check, so the rules live in the doc comment, and the check enforces the hard ones.
  - `[medium]` `patch` (duplicate) Colour-lint AC claim. Patched above.
  - `[medium]` `patch` (duplicate) Template AC claim. Patched above.
  - `[medium]` `patch` (duplicate) Font-loaded claim. Patched above.
- Verification Gap:
  - `[medium]` `patch` The `Button` press guard was not tested through `Button`. Patch: the test calls `Button()` and invokes its `onClick`.
  - `[low]` `patch` A fixed password error clearing was not tested. Patch: an e2e step.
  - `[low]` `patch` A reason before the first press was not tested. Patch: the keyboard test asserts no `aria-invalid` after tabbing through.
  - `[low]` `patch` CI `retries: 1` hid flaky passes. Patch: `retries: 0`.
- Intent Alignment (descriptive divergences):
  - `[low]` `patch` "No dark theme" was not checked on the page. Patch: the e2e test emulates `prefers-color-scheme: dark` and asserts `paper` and `ink`.
  - `[low]` `patch` "No shadows or gradients" was not checked on the page. Patch: the e2e test asserts that `box-shadow`, `text-shadow` and `background-image` are `none` on every element.
  - `[low]` `reject` `aria-disabled` focus retention is not exercised in a browser. No control on this page becomes unavailable, and the Button contract is unit-tested through `Button`.
  - `[low]` `reject` The hover, pressed and disabled states exist only as classes. They are visual states with no behaviour, and the compiled CSS contains them.
  - `[low]` `reject` The reason sits under the field, not beside it. This was a deliberate reading (Design Notes): beside at 320 px would shrink the field. It is adjacent and tied by `aria-describedby`.
  - `[low]` `reject` The source scan of the contrast pairs (same as above).
  - `[medium]` `defer` "Every UI string from nb.ts" is not enforced (same as the deferred item).
  - `[low]` `reject` The lint exempts the whole `src/theme/` folder. That folder is the theme. The other files in it hold token names, not colour literals.
  - `[false]` `reject` No SVG reads the variables. No SVG exists yet, and the e2e test asserts every token on `:root`.
  - `[false]` `reject` 400 % zoom is tested as a 320 px viewport. That is WCAG 1.4.10's own equivalence (1280 px at 400 % = 320 CSS px).
  - `[false]` `reject` CI against compose is unverified. The job is added, and the same command passed locally.
  - `[low]` `reject` "Pre-Debrief" scoping of templates. Mail is pre-Debrief and the print route is post-Debrief, as recorded in the script.
  - `[false]` `reject` The microcopy rules are a comment, and some strings are assumptions. They are marked `[ASSUMPTION]` for Issue #31, as the runbook prescribes.

## Auto Run Result

Status: done

**Summary.** This change builds the web foundation and the «Logg inn» page:
- **Theme.** Generated from `src/theme/tokens.json`, a copy of DESIGN.md's front matter, as Tailwind v4 `@theme static`. Tailwind's defaults are reset, sizes are in rem, and proportional figures apply only to the two figure roles.
- **Font.** Source Sans 3 is self-hosted.
- **Components.** Knapper, Lenke and Tekstfelt.
- **Copy.** `nb.ts` holds the term table and the page copy.
- **Checks.**
  - The copy check runs over `nb.ts`, the Jinja2 templates and the print route.
  - A colour lint runs as `prebuild`.
  - Vitest covers the tokens, contrast, the components, validation and the scripts.
  - Playwright runs with axe through compose at 320, 360, 1440 px and 400 % zoom.
  - CI has an e2e job.
- **Page.** `/logg-inn` validates on the client and sends nothing.

**Files changed:**
- `frontend/package.json`, `package-lock.json`: exact pins. Vitest 5.1.0, @playwright/test 1.64.1, @axe-core/playwright 4.14.0, @fontsource/source-sans-3 5.3.1, yaml 2.9.1 and vite 8.3.5, plus overrides for axe-core, playwright-core, rolldown and @rolldown/pluginutils. Also the scripts.
- `frontend/src/theme/{tokens.json,theme.css,contrast.ts,text-on-tint.ts}` and tests: the theme source, the generated CSS and the contrast table.
- `frontend/scripts/{build-theme,check-copy,lint-colours}.mjs` and `scripts.test.mjs`: the generator and both checks.
- `frontend/src/app/{globals.css,layout.tsx}`, `src/app/(auth)/logg-inn/page.tsx`: base styles, fonts, the title template and the page.
- `frontend/src/components/{button,link,text-field}.tsx` and tests: the shared controls.
- `frontend/src/copy/nb.ts`: all UI copy.
- `frontend/src/modules/identity/{validate-login.ts,login-form.tsx}` and tests: the form.
- `frontend/src/lib/utils.ts`: tailwind-merge now knows the token names.
- `frontend/{vitest,playwright}.config.ts`, `e2e/logg-inn.spec.ts`: the test setup.
- `.github/workflows/ci.yml`: Vitest and the copy check, plus the e2e job.
- `README.md`, `.gitignore`, `frontend/.dockerignore`.
- `.docs/implementation-artifacts/epic-3-context.md`: the compiled epic context.

**Review.**
- 26 patches applied: 1 high, 9 medium, 16 low.
- 4 items deferred (see `deferred`).
- The other findings were rejected, with reasons in the triage log.

**Follow-up review recommended: true.** One high was patched: the pre-hydration native submit, now `method="post"`. What a POST to the statically rendered `/logg-inn` returns (the Next.js response) has not been checked in a browser before hydration. Story 3.2 replaces this path with the API call.

**Verification:**
- `npm run typecheck`: passed.
- `npx vitest run`: 181 tests passed, in about 0.6 s.
- `npm run check:copy`: passed.
- `npm run build`: the colour lint passed and the build succeeded.
- `docker compose up -d --build --wait proxy`, then `npx playwright test`: 7 passed. With one worker, each viewport test takes about 1.1 s (two axe runs), and the others take 0.3–0.7 s.
- Backend `uv run pytest`: 1549 passed and 1 failed. The failure is the timing test `tests/players/test_llm_jobs.py::test_the_turns_read_time_is_when_the_read_ended`. It was 0.198 s against a 0.2 s floor, under load from the running stack. It passed twice when run alone. It is pre-existing; no backend code changed.
- Matrix audit:
  - empty submit: Vitest plus the e2e keyboard test;
  - malformed e-mail: Vitest plus the e2e malformed test;
  - valid input: Vitest plus the e2e test's last part;
  - fixing a field: e2e, for both the e-mail and the password.

**Decisions taken in place of the founder:**
- @playwright/test is pinned to 1.64.1, not the spine's 1.65.0. 1.65.0 was 13 days old, under the two-week rule.
- Young transitive dependencies are pinned through overrides.
- `/logg-inn` is the route.
- The lead sentence and several validation reasons are marked `[ASSUMPTION]`.
- The reason sits under the field.
- Errors use the 1.4 px error border.
- «Logg inn» is the primary button on its own page.
- The colour lint is a script, not ESLint.
- The tokens file holds the four token groups, not `components`.
- Mail templates count as pre-Debrief, and the print route as post-Debrief.
- 400 % zoom is tested as a 320 × 256 viewport.
- The implementation was done in the orchestrating context, not in a subagent, as the caller instructed.

**Residual risks:**
- The CI e2e job has not run on GitHub yet.
- The `/glemt-passord` link is dead until Story 3.6.

## Design Notes

- **Tailwind v4 keys.** `--color-<token>`, `--text-<role>` (with `--line-height` and `--font-weight` sub-keys), `--radius-<token>` and `--spacing-<token>`. With `@theme static`, every variable is emitted on `:root`, so hand-made SVG can read `var(--color-lager)`. The colour, text, radius and shadow defaults are reset with `initial`. The numeric `--spacing` base stays.
- **Focus ring.** It uses outline with offset, not box-shadow, so it survives forced colours. The gap shows `paper`, because `paper` is the only background.
- **Error border.** The error state uses 1.4 px `restordre`, from DESIGN.md's shared Interaction states table, over the 1 px in the `text-field` token, because the AC names the shared states. The reason sits directly under the input, so the field keeps its full width at 320 px.
- **«Logg inn» is primary on its own page.** The UX spine lists it as secondary on the Landing page. The story names it this page's one primary button.

## Verification

**Commands:**
- `cd frontend && npm run typecheck && npx vitest run && npm run check:copy && npm run build` -- expected: all pass
- `docker compose up -d --build --wait frontend proxy backend && cd frontend && npx playwright test` -- expected: all pass, each test under 1 s
