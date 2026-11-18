# Story 3.2: visual check of login and logout

Taken 2026-11-18 from `http://127.0.0.1:8080` (docker compose: postgres, backend, frontend, proxy) with the project's `@playwright/test` Chromium, in a throwaway spec. Full-page shots at 390 × 844 and 1280 × 800. Compared with `mockups/09-alle-sider.png` (the «Logg inn» card), DESIGN.md, EXPERIENCE.md (State Patterns → Account and access) and `frontend/src/copy/nb.ts`. The rate-limited state uses a fresh unknown address pushed to 429 through the API. The deactivated state uses a temporary row `deaktivert@example.com` (`is_active=false`, the demo password's hash), deleted afterwards. No horizontal scroll in any shot. No visual fixes were needed.

- `logg-inn-wrong-password-390.png`: Admin's e-mail with a wrong password. One `restordre` line «Feil e-post eller passord.» above the button, the input kept, focus ring on E-post, neither field marked. Matches (EXPERIENCE.md's exact string, one primary button).
- `logg-inn-wrong-password-1280.png`: the same on a laptop, in the 384 px column at the 80 px margin. Matches.
- `logg-inn-rate-limited-390.png`: «For mange forsøk. Vent noen minutter og prøv igjen.» on one line; the long test address fits the field. Matches. The string is [ASSUMPTION] (Issue #31).
- `logg-inn-rate-limited-1280.png`: the same on a laptop. Matches.
- `logg-inn-deactivated-390.png`: «Kontoen er deaktivert. Ta kontakt med faglæreren din.» after the right password. Matches EXPERIENCE.md. Judgement: «faglæreren din» also reaches deactivated staff (left to Issue #31, as the spec says).
- `logg-inn-deactivated-1280.png`: the same on a laptop. Matches.
- `hjem-signed-in-390.png`: `/` after logging in as Demo Faglærer. Header «ØL-spillet» with a secondary «Logg ut» at the right, h1 with the name, «Du er logget inn.» in `ink-secondary`. No primary button, which is right for a screen with no committing action. No mockup exists for this placeholder (Story 3.3 builds the homes). Matches DESIGN.md tokens. Judgement: because the header centres the label on the 50 px button, «ØL-spillet» sits about 15 px lower here (y≈48) than on «Logg inn» (y≈33), so the product name jumps between the two pages.
- `hjem-signed-in-1280.png`: the same on a laptop; «Logg ut» at the right edge of the 80 px margin. Matches, with the same header judgement.
- `logg-inn-after-logout-390.png`: «Logg ut» pressed. Back on `/logg-inn` with empty fields and no error line. Matches.
- `logg-inn-after-logout-1280.png`: the same on a laptop. Matches.
