# Epic 3 Context: Accounts and the Admin area

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Give the product its front door and its control room. When this epic is done, the Admin can invite a Lecturer by e-mail, the Lecturer creates an account, logs in and lands on an empty home screen, and every User is held to their account role on every request. The Admin can search Users, grant and revoke roles, deactivate and reactivate Users, resend Invitations, create Institutions and read an audit log. Along the way the epic builds the shared foundations every later epic relies on: auth, authorization, audit, rate limits, the mail pipeline with its sweeper, the web design system and copy home. It ends with the first production deploy on Railway.

## Stories

- Story 3.1: See «Logg inn» in the product's design
- Story 3.2: Log in and log out with e-mail and password
- Story 3.3: Land on your own home and be held to your role
- Story 3.4: See what is happening when a page loads, fails or goes offline
- Story 3.5: Send every mail through one pipeline
- Story 3.6: Reset a forgotten password by e-mail
- Story 3.7: Invite a Lecturer or Admin by e-mail
- Story 3.8: Create an account from an Invitation
- Story 3.9: Find Users and grant or revoke roles
- Story 3.10: Deactivate and reactivate Users and resend Invitations
- Story 3.11: Create Institutions
- Story 3.12: Read the audit log
- Story 3.13: Read the Landing page and ask for lecturer access
- Story 3.14: Prepare a strict production configuration in the repo
- Story 3.15: Reach the product in production

## Requirements & Constraints

- **Invitations:** the Admin invites an e-mail with the Lecturer or Admin role built in; following the link creates the account with that role, no approval step. An expired or used link shows a message and one way to ask for a new Invitation. There is no public sign-up; the Landing only collects access requests.
- **Accounts:** e-mail prefilled and not editable on acceptance; login by e-mail and password; password reset by e-mail without the Admin. Exactly one User per e-mail (case-insensitive); an Invitation to an existing account adds the role.
- **Roles:** grant/revoke takes effect at the next page load with the same login. Revoking Lecturer from someone who owns Classes is blocked (`409 role_revoke_blocked`) until another Lecturer is added or the Classes archived. The last active Admin can never be revoked or deactivated (`last_admin`).
- **Deactivation:** deactivated Users cannot log in, a still-valid cookie is rejected at once, and their reset tokens and Invitations are unusable. No data is deleted.
- **Access:** role check on every request. The Admin sees all Users but no Student answers or AI assessments. Permission-denied answers never reveal whether an item exists; actions a role lacks are not rendered.
- **Audit:** every Admin action (Invitation sent/resent, role granted/revoked, deactivate/reactivate, Institution created/renamed, bootstrap Invitation, access request invited/dismissed) writes exactly one audit row in the same transaction, with actor, time and change. Later epics add Takeover and completion-correction events without changing the audit page.
- **Non-revealing copy:** login, reset and Invitation-renewal responses never say whether an account exists.
- **Language:** every screen and mail is in Norwegian bokmål, no exclamation marks; mails headed «ØL-spillet».
- **Accessibility (WCAG 2.1 AA):** Playwright with axe at 320, 360 and 1440 px (and 400 % zoom / 200 % text where stated), full keyboard operation, tap targets ≥ 44 px, reduced motion respected.
- **Security in production:** HTTPS everywhere, TLS to the database, encryption at rest confirmed; e-mail sending domain authenticated (SPF, DKIM, DMARC). The repo is public: no secret is ever committed.
- Rate-limit thresholds and token validities are configuration with placeholder defaults (`LOGIN_RATE_LIMIT_PER_IP`, `LOGIN_RATE_LIMIT_PER_ACCOUNT`, `PASSWORD_RESET_VALID_MINUTES`=60, `ROLE_INVITATION_VALID_DAYS`=14).

## Technical Decisions

- **Session (one origin):** Caddy is the only public entry: `/api/*` to `backend` with immediate flush, 404 for `/print/*`, everything else to `frontend`. Password is SHA-256 → base64 → bcrypt. Session is an HS256 JWT carrying only `user_id` in an `httpOnly; Secure; SameSite=Lax` cookie. Every mutating request must carry `X-Requested-With: olspillet` (only `/api/webhooks/*` is exempt, verified by signature). Every request loads the User and roles from the database and rejects deactivated Users.
- **Tokens:** Invitation and reset tokens are random, single-use, stored only as a hash, with expiry. Rate limits are Postgres-backed in `platform/ratelimit`, per IP and per account/Invitation.
- **Authorization:** all checks go through `platform/authz` (`can(user, action, resource)` plus scoped query helpers); every route declares a policy as a FastAPI dependency; a test walks all routes and fails on a route with no policy outside the short public list (login, password reset, Invitation acceptance, access request, health, webhooks). A CI check forbids `if role ==` in `backend/app/modules/`. Class-scoped helpers are added by the epic that creates their tables.
- **Personal data:** names and e-mails live only in `identity` tables. Audit rows, notices, job arguments and log lines hold ids only; names are resolved at read time. Search query text is not logged.
- **Audit:** `platform/audit` exposes `record(actor, action, target, change)` and read functions only; no update or delete. System actions have an empty actor.
- **Notifications and mail:** modules call `platform/notify.enqueue(user_id, kind, dedupe_key, ref, not_before)` in their own transaction (unique `dedupe_key`, ids only, emits `user:<id>`). A notice may address its recipient by reference (`user_id=None`, `ref` = e.g. Invitation id) and `messaging` resolves the address through the owning module's `service.py`. `messaging` is the only reader of notices and the only module that defers the idempotent `mail` job (queue `mail`, run by `worker-batch`); one `mail_deliveries` row per mail prevents double sends. `immediate` kinds (Invitation, password reset) leave at once, any hour; `digest` kinds send at most one mail per User per Oslo day, never 22:00–07:00. `platform/notify` imports no module.
- **Timers:** `ops.sweep` in `modules/ops` is the one per-minute periodic task (`worker-batch --sweeper`); it only finds due work and calls the owner, one item per transaction. No other cron. Invitation expiry is read from `expires_at`, no background job.
- **Events:** `platform/events.emit` inside the mutating transaction; topics are a closed registry with a test. Role grant, deactivation and notices emit `user:<id>`.
- **Email:** `platform/email` with Jinja2 templates, Resend sender, deterministic `[email:mock]` sender when `RESEND_API_KEY` is missing outside production. Sent from `EMAIL_FROM`, links from `PUBLIC_BASE_URL`.
- **Config:** zero-config locally (mocks, local-only seed of one demo Admin and one demo Lecturer). With `APP_ENV=production` api and workers refuse to start if `JWT_SECRET`, `DATABASE_URL`, `RESEND_API_KEY`, `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` is missing or default. First Admin comes from `BOOTSTRAP_ADMIN_EMAILS` (production: one Invitation at startup, audited as system).
- **Data/schema:** UUIDv7 ids, `timestamptz` UTC shown in Europe/Oslo, Alembic owns all schema changes (expand-then-contract), one owning module per table. `identity` owns `users`, `user_roles`, `password_resets`, `invitations`, `institutions`, `access_requests`; `platform/notify` owns `notices`; `messaging` owns `mail_deliveries`. List and error envelopes with stable error codes (`invalid_credentials`, `rate_limited`, `role_revoke_blocked`, `last_admin`). Module layout `routes.py, service.py, repo.py, models.py, schemas.py, jobs.py`.
- **Web:** presentation only; typed client generated with `openapi-typescript` + `openapi-fetch` into `frontend/src/lib/api/` with a CI drift check; server state in TanStack Query (one `QueryClient`). All UI copy in `frontend/src/copy/nb.ts`; a CI copy check (voice rules, «Beer Game»/«bullwhip», «øl», «optimal», «fasit») covers `nb.ts`, mail/PDF templates and the print route. Fonts self-hosted via `@fontsource/source-sans-3`.
- **Deploy:** Railway project `olspillet`, EU West, five services (`proxy`, `frontend`, `backend`, `worker-ai`, `worker-batch`), only `proxy` public; backend and workers built from one image; only `backend` runs `alembic upgrade head` pre-deploy. Supabase Postgres in eu-central-1 via session pooler on port 5432 with a written connection budget (`DB_POOL_SIZE`). `production` branch auto-deploys, `main` is the working branch. Resend in eu-west-1.

## UX & Interaction Patterns

- **Design foundation:** DESIGN.md tokens are the single theme source (full token set, committed token file, test for drift); light theme only, `paper` background; Source Sans 3 400/600/700; `rem`/`em`, ≥ 13 px on phone; no all caps, letter-spacing, shadows or gradients; `rounded.sm` controls; tabular lining figures by default. Lint fails on literal colours outside the theme; contrast test on the text-on-tint table.
- **Controls:** Knapper (one primary per screen, labelled with its effect), Lenke (`lager`, 600, underlined, never commits), Tekstfelt (label above, `restordre` invalid border with reason beside). Shared states incl. focus-visible with `focus-ring`; unavailable-while-focused uses `aria-disabled`, never native `disabled`.
- **Homes and navigation:** Admin → «Admin-område»; Lecturer → empty Lærerhjem; others → empty Hjem; Admin+Lecturer lands on Lærerhjem with links both ways. No global nav bar on phone; staff breadcrumb Lærerhjem → Klasse → Klasseøkt / Oversikt.
- **System states:** Skjelett loading in real layout, «Laster …» after 1 s, page error after 10 s, no spinners; Tilkoblingslinje for offline / reconnected / page error; inline mutation error with `role="alert"`, input and focus kept; session-expired returns to the same page after login; permission denied and not-found pages with a link home.
- **Account surfaces:** Landing, Logg inn, Glemt passord, Nytt passord, «Du er invitert», with the exact Norwegian copy from the UX spine (e.g. «Feil e-post eller passord.», «Kontoen er deaktivert. Ta kontakt med faglæreren din.»).
- **Admin lists:** tables reflow to one labelled block per row at 320 px with no sideways scroll; grant/revoke/deactivate are buttons stating their effect and the User's name, no confirmation dialogs; «Ingen treff.» for empty search.
- **Landing:** synthetic numbers labelled «Demodata»; no week counts, amplification, prices, quotes or learning claims; no chart code yet.

## Cross-Story Dependencies

- Story 3.1 creates the design tokens, shared form components, `nb.ts`, the copy check and the Playwright/axe setup that every later story reuses. Story 3.2 adds `identity` tables, `platform/auth`, `platform/ratelimit`, the generated client and TanStack Query. Story 3.3 adds `platform/authz` and the homes. Story 3.4 adds the shared mutation helper and state components.
- Story 3.5 (notify, email, messaging delivery, `ops.sweep`) must precede 3.6, 3.7 and 3.8, which register their `immediate` kinds. Story 3.7 introduces `platform/audit`, used by 3.8–3.13. Story 3.8 adds `renewal_requested_at`, shown in 3.10. Story 3.13's access requests prefill 3.7's invite form.
- Story 3.14 must precede 3.15; 3.15 needs the founder to carry out account/DNS steps from a runbook.
- Builds on Epic 1's repo scaffold, proxy rules and shadcn setup, and Epic 2's Admin model pinning («KI-kostnad» lives in the «Admin-område»).
- Forward hooks for later epics: Lecturer-revoke blocker registry (Epic 4 registers Class ownership), Class-scoped authz helpers (Epic 4+), Student Invitations (Epic 4), Lærerhjem/Hjem content (Epics 4 and 6), `frontend/src/lib/drafts.ts` for keeping input across reload/login (Epic 6), charts (Epics 6–7), further sweep actions and audit events (later epics).
