# Story 3.3: visual check of the homes, refusal and not-found pages

Taken 2026-11-18 from `http://127.0.0.1:8080` (docker compose: postgres, backend, frontend, proxy) with the project's `@playwright/test` Chromium in a throwaway spec, logging in through the API (`loginByApi`). Full-page shots at 390 × 844 and 1280 × 844. Compared with `mockups/09-alle-sider.png` (Lærerhjem, Admin-område cards), `mockups/01-landing.png` (header), `mockups/04-student-hjem.png`, DESIGN.md, EXPERIENCE.md (Navigation, State Patterns → All) and `frontend/src/copy/nb.ts`. In every shot: the product name's top is at y = 24 px (Issue #68 holds across «Logg inn», the homes, the refusal and not-found pages), `scrollWidth` equals the viewport (no sideways scroll), and there is at most one primary button (one on «Logg inn», none elsewhere). No visual fixes were needed.

- `logg-inn-anonym-390.png`: «Logg inn» as the height reference for the header. Matches.
- `logg-inn-anonym-1280.png`: the same on a laptop, 80 px margin. Matches.
- `admin-admin-390.png`: Demo Admin at `/` lands on `/admin`, h1 «Admin-område», name in `ink-secondary` and secondary «Logg ut». No cross-link (no Lecturer role). Matches.
- `admin-admin-1280.png`: the same on a laptop. Matches.
- `laererhjem-faglaerer-390.png`: Demo Faglærer at `/` lands on `/laererhjem`, h1 «Lærerhjem», no link to the Admin-område. Matches.
- `laererhjem-faglaerer-1280.png`: the same on a laptop. Matches.
- `hjem-student-390.png`: a User with no role at `/` lands on `/hjem`, h1 «Hjem», nothing else (Hjem content is Epic 6). Matches.
- `hjem-student-1280.png`: the same on a laptop. Matches.
- `laererhjem-admin-faglaerer-390.png`: Admin+Faglærer at `/` lands on `/laererhjem` with the Lenke «Til Admin-område»; the long name «Demo Admin og Faglærer» and «Logg ut» still fit on one header line. Matches.
- `laererhjem-admin-faglaerer-1280.png`: the same on a laptop. Matches.
- `admin-admin-faglaerer-390.png`: the same User on `/admin`, h1 «Admin-område» with the Lenke «Til Lærerhjem», so the two homes link to each other. Matches.
- `admin-admin-faglaerer-1280.png`: the same on a laptop. Matches.
- `ingen-tilgang-student-390.png`: a Student opening `/admin`: «Du har ikke tilgang til denne siden.» (wraps to two lines) and «Til Hjem», same URL. Matches EXPERIENCE.md.
- `ingen-tilgang-student-1280.png`: the same on a laptop, one line. Matches.
- `ingen-tilgang-faglaerer-390.png`: a Faglærer opening `/admin`, «Til Lærerhjem». Matches.
- `ingen-tilgang-faglaerer-1280.png`: the same on a laptop. Matches.
- `ikke-funnet-innlogget-390.png`: Demo Admin on `/finnes-ikke`: «Fant ikke siden.» and «Til Admin-område», signed-in header. Matches.
- `ikke-funnet-innlogget-1280.png`: the same on a laptop. Matches.
- `ikke-funnet-anonym-390.png`: anonymous on `/finnes-ikke`: «Fant ikke siden.» and «Til innlogging», header with the product name only. Matches.
- `ikke-funnet-anonym-1280.png`: the same on a laptop. Matches.

Not shot: the `Breadcrumb` is built for later epics but mounted on no page yet (spec, triage log), so it cannot be reached in the app; its markup and tokens (Lenke crumbs, `ink-muted` «/», current item `ink` with `aria-current`) were checked in code only.

Judgement (left as is): `01-landing.png` draws the product name larger (about 20 px, bold) with a hairline rule under the header; the app header sets «ØL-spillet» in `label` 15/600 with no rule. DESIGN.md names no token for the header, and its hairline is "never component boundaries", so the rule is out; the name size was accepted in the 3.2 check and is left for the founder.
