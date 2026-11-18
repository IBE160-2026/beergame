# Story 3.1: visual check of «Logg inn»

Taken 2026-11-18 from `http://127.0.0.1:8080/logg-inn` (docker compose: postgres, backend, frontend, proxy) with the project's `@playwright/test` Chromium. Full-page shots. Compared with `mockups/09-alle-sider.png` (the «Logg inn» card), DESIGN.md, EXPERIENCE.md and `frontend/src/copy/nb.ts`. The page is public, so no seed or test login is needed. It has no loading state, because Story 3.1 sends nothing; loading arrives with the API call in Story 3.2. No horizontal scroll at either width.

- `logg-inn-empty-390.png`: the first visit on a phone. «ØL-spillet» header, h1 «Logg inn», the lead, E-post, Passord, one full-width primary «Logg inn», and the link «Glemt passord?». Matches: the mockup card's two fields and full-width ink button, paper only, `ink-muted` borders, `rounded.sm`, Source Sans 3, 20 px gutter, no shadows or decoration.
- `logg-inn-empty-1280.png`: the same on a laptop. 80 px margin, a 384 px column, h1 at 34 px. Matches.
- `logg-inn-error-empty-390.png`: «Logg inn» pressed with both fields empty. Both fields have a 1.4 px `restordre` border and a reason in `restordre`, and focus is on E-post (ink ring with a paper gap). Matches, with one judgement: the reason sits under the field, where DESIGN.md says "beside it". This was recorded as a deliberate reading in the spec, so the field keeps its width at 320 px.
- `logg-inn-error-empty-1280.png`: the same on a laptop. Matches (same judgement on the reason's position).
- `logg-inn-error-email-390.png`: the e-mail is `ola@uib` with a password filled in. The reason is «Domene mangler», and Passord stays neutral. Matches. Judgement: «Domene mangler» has no full stop, while «Skriv e-postadressen din.» has one. Both strings come from nb.ts, and the [ASSUMPTION] strings go to the copy review in Issue #31.
- `logg-inn-error-email-1280.png`: the same on a laptop. Matches. Judgement: the reason is `body-phone` (14 px) at every width, while the lead steps up to `body` (15 px) on a laptop. DESIGN.md does not name a role for the reason.
- `logg-inn-filled-390.png`: valid input after the error was fixed and the field left. The error is gone and the page stays put. Matches.
- `logg-inn-filled-1280.png`: the same on a laptop. Matches.
- `logg-inn-focus-submit-390.png`: keyboard focus on «Logg inn». A 2 px ink ring with a 2 px paper gap. Matches.
- `logg-inn-focus-submit-1280.png`: the same on a laptop. Matches.
- `logg-inn-nojs-after-press-390.png`: «Logg inn» pressed with JavaScript off, standing in for a press before hydration. The browser sends `POST /logg-inn` and gets the same empty page back. The URL stays `/logg-inn`, and the password is in no URL. The hydrated press sends no request at all. The fix holds. Judgement: a press before hydration clears the fields without saying why. That is acceptable until Story 3.2 replaces this path.
