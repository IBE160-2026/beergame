---
title: 'Story 4.6: See bounced Invitations and the counts'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '327d021d0b9a990dbf8dc2eafc29429ba384fe74'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-4-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The rules "newest Invitation per Roster entry" and "newest delivery per Invitation" in the bounce list and counts have no test with more than one Invitation or delivery.
    evidence: |-
      Only send_roster_invitations makes Student Invitations, one per new entry, so the case is unreachable until Story 4.7 sends reminders; 4.7 should add a re-sent Invitation (older bounced, newer delivered) to tests/classes/test_invitation_counts.py.
    location: >-
      backend/app/modules/classes/service.py invitation_summary; backend/app/modules/messaging/repo.py deliveries_for_refs
    severity: low
---

<intent-contract>

## Intent

**Problem:** Story 4.4 mails Student Invitations, but nothing tells the Lecturer whether a mail reached its Student: `mail_deliveries` keeps no delivery outcome, there is no provider webhook, and the Class page shows only the Roster count.

**Approach:** `messaging` gains a signed Resend webhook (`POST /api/webhooks/resend`, Svix signature with `RESEND_WEBHOOK_SECRET`) that stores delivery state, bounce class and last event id on the `mail_deliveries` row found by provider message id, and exposes delivery state per Invitation through `messaging.service`. `classes` combines it with `identity`'s Invitation facts into `GET /api/classes/{id}/invitations`: four counts and the bounced Roster addresses, shown on the Class page. Locally a dev-only route makes the mock "bounce" a mail by posting a signed event through the same handler.

## Boundaries & Constraints

**Always:**
- Signature: Svix scheme as Resend sends it — headers `svix-id`, `svix-timestamp`, `svix-signature` (space-separated `v1,<base64>`), HMAC-SHA256 over `{id}.{timestamp}.{raw body}` with the base64 key after `whsec_`, constant-time compare, timestamp within 5 minutes of the api clock. Missing, malformed, wrong or stale → 401 `webhook_signature_invalid`, nothing stored. Body capped at 256 KiB (413 `payload_too_large`). Exempt from `X-Requested-With` by the existing `/api/webhooks/` prefix; the only public webhook route.
- Events: `email.delivered` → state `delivered`; `email.delivery_delayed` → `delayed`; `email.bounced` → `bounced` with class `hard` (`data.bounce.type == "Permanent"`) or `soft` (anything else). States only move forward (delayed < delivered < bounced; hard beats soft), so replays and out-of-order events change nothing. The same `svix-id` as `last_event_id` → no-op. Row locked while updated. Other event types, and events for an unknown `data.email_id`, answer 200 and log `webhook_event_ignored` with the event type only.
- `mail_deliveries` (owned by `messaging`) gains nullable `delivery_state`, `bounce_class`, `last_event_id` with check constraints, and an index on `provider_message_id`; expand-only migration 0028.
- `messaging.service.invitation_deliveries(session?, refs)` → per Invitation id: newest delivery's `sent` (sent_at set), `state`, `bounce_class`. `classes.service` reads it there only; `identity` gives the Class's Student Invitations (id, Roster entry, accepted, expired-at-read, voided, entry registration/removed, address).
- Counts, computed in the api at read time (api clock): sent = Student Invitations of the Class whose delivery was sent; bounced = of those, state `bounced`; accepted = `accepted_at` set; expired = not accepted, not voided, `expires_at <= now`. Bounced list = Roster entries (not removed, not registered) whose newest Invitation bounced, by address, with `registration: "bounced"` and `bounce_class`.
- `GET /api/classes/{id}/invitations` behind `classes.manage` (owners; 4.9 decides Assistants); 403 `forbidden` alike for other/unknown/malformed ids.
- `RESEND_WEBHOOK_SECRET`: local default `whsec_…` built-in value; production refuses empty, the local default, or one that is not `whsec_` + base64.
- Dev bounce: `POST /api/dev/mailbox/bounce` `{to, bounce_class}` on the dev router (never mounted in production): finds the newest sent mail to the address, signs an `email.bounced` event with the configured secret and feeds it to the same verify-and-store function. 404 when no mail was sent there. Logs ids only.
- Logs and responses of the webhook never hold an address; copy in `nb.ts`; result lines/errors as in earlier stories.

**Never:** registration-status list, filters or reminders (4.7); changing `roster_entries.registration` on a bounce (status is derived at read); the Resend SDK or an HTTP client library; a real provider account or real mail; comparing DB time with host time or ordering by timestamps in tests; resetting demo accounts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Bounce | signed `email.bounced`, `Permanent`, known mail | 200; row `bounced`/`hard`, `last_event_id` set | – |
| Replay | same event again, or older `delivered` after bounce | 200; row unchanged | – |
| Bad signature | none / wrong secret / altered body / ts 6 min off | 401 `webhook_signature_invalid`; no change | – |
| Unknown mail | valid signature, unknown `email_id` | 200; log type only | – |
| Malformed JSON | valid signature over non-JSON | 400 `invalid_request` | – |
| Counts | 3 sent, 1 hard + 1 soft bounce, 1 accepted, 1 expired | `{sent:3, bounced:2, accepted:1, expired:1, bounces:[…]}` | other Class → 403 |
| Dev bounce | `to` with a sent mail | 200, delivery bounced | no mail → 404; production: route absent |

</intent-contract>

## Code Map

- `backend/app/modules/messaging/models.py` -- `mail_deliveries`; add columns/checks/index.
- `backend/app/modules/messaging/repo.py` -- add `lock_by_provider_id`, `store_event`, `deliveries_for_refs` (DISTINCT ON notice ref, newest by id; join pattern of `latest_sent_for` via `notices.ref` / `notice_ids`).
- `backend/app/modules/messaging/service.py` -- add `receive_webhook(body, headers, now)`, `invitation_deliveries(refs)`, `simulate_bounce(address, cls, now)`.
- new `backend/app/modules/messaging/webhooks.py` -- router `/api/webhooks/resend` (`authz.public`), raw body cap; Svix verify helper (stdlib `hmac`, `base64`).
- `backend/app/modules/messaging/routes.py` -- dev `POST /mailbox/bounce`.
- `backend/app/main.py:96` -- mount webhooks router always.
- `backend/app/platform/config.py` -- `resend_webhook_secret`, production rule.
- `backend/app/modules/identity/{service,repo}.py` -- `class_student_invitations(class_id)`.
- `backend/app/modules/classes/{service,routes,schemas}.py` -- summary + route (declare before nothing conflicting; `POST /{id}/invitations` exists).
- `backend/migrations/versions/0028_mail_delivery_events.py`.
- Tests: `tests/test_imports.py` (allow `classes`→`messaging.service`, `main`→`messaging.webhooks`), `tests/test_authz_rules.py` PUBLIC_ROUTES, `tests/test_config.py`/`test_production_startup.py` (new secret), `tests/test_migrations.py`, new `tests/messaging/test_webhook.py`, new `tests/classes/test_invitation_counts.py` (reuse `klass`, `staged_id`, `send`, `drain`, `clock`).
- Frontend: `src/modules/classes/{api.ts,class-page.tsx}` (+ new `invitation-summary.tsx`), `copy/nb.ts` `classes.invitations`, `lib/api/{openapi.json,schema.ts}`; e2e new `e2e/invitation-bounces.spec.ts` modelled on `roster-send.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `config.py`, migration 0028, `messaging/{models,repo,service,webhooks,routes}.py`, `main.py` -- webhook, state store, dev bounce.
- `identity/{repo,service}.py`, `classes/{schemas,service,routes}.py`, `classes/README.md` -- Invitation facts, summary route.
- Backend tests -- every matrix row, signature variants, idempotency, each count, scope, local-only dev route, no address in logs.
- Frontend -- «Invitasjoner» section on the Class page (owner, once any Invitation exists): four counts as figures, bounced addresses with status text; send invalidates the summary; unit test of copy helpers; regenerate client.
- `frontend/e2e/invitation-bounces.spec.ts` -- send 3, bounce one hard and one soft through the dev route, counts and marks visible, axe at 320 and 1440 px, no horizontal scroll.

**Acceptance Criteria:**
- Given sent Invitations with one hard and one soft bounce, when the Lecturer opens the Class, then «Invitasjoner» shows «Sendt 3», «Kom ikke fram 2», «Akseptert 0», «Utløpt 0» and lists both addresses with «Kom ikke fram, permanent feil» / «… midlertidig feil» in text.
- Given `APP_ENV=production`, then the dev bounce route does not exist and startup refuses a default or empty `RESEND_WEBHOOK_SECRET`.
- Given Playwright with axe at 320 and 1440 px, then the Class page passes with no horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 30 findings — high 0, medium 4, low 22, false 4, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) A soft bounce outranked a later delivery, so a mail that got through after a temporary failure stayed «midlertidig feil» — ranks are now delayed < soft bounce < delivered < hard bounce (`_RANK` on state and class); test `test_a_delivery_after_a_soft_bounce_wins_and_a_late_soft_bounce_does_not`.
  - `[low]` `[patch]` (blind) An older event replayed after a newer one overwrote `last_event_id` and answered `stored` — an event that does not move the state forward now stores nothing and answers `unchanged`; test `test_an_older_event_replayed_after_a_newer_one_changes_nothing`.
  - `[low]` `[reject]` (blind) Non-production deployments accept the public local secret and mount the dev bounce — `APP_ENV` has only local/test/ci/production and every deployment is production (Railway); the Story 3.6 dev mailbox has the same guard.
  - `[low]` `[patch]` (blind) The `PUBLIC_ROUTES` comment allowed only webhooks — reworded to name dev routes never mounted in production.
  - `[false]` `[reject]` (blind) Nothing routes Resend to the webhook or documents its setup — `proxy/Caddyfile` forwards `/api/*` unchanged, and SETUP-GUIDE already lists `RESEND_WEBHOOK_SECRET` with «Point it at `/api/webhooks/resend`».
  - `[low]` `[reject]` (blind) `provider_message_id` gets a plain, not unique, index — one id per mail from provider and mock; a unique index adds a failure mode to `mark_sent` for no named harm.
  - `[low]` `[reject]` (blind) `deliveries_for_refs` joins `ANY(notice_ids)` without a GIN index — v1 holds thousands of Invitation mails at most; `latest_sent_for` (Story 3.6) uses the same join; a new migration for no measured cost.
  - `[medium]` `[patch]` (blind) The counts went stale: «Sendt 0» after a send until a reload — `useInvitationSummary` now refetches every 15 s while the tab is visible.
  - `[low]` `[reject]` (blind) «Utløpt» can exceed «Sendt» — each count follows the story's own definition; an Invitation whose mail was skipped is expired and unsent.
  - `[low]` `[patch]` (blind) The new `invitations` copy block sat under the Roster's doc comment — moved above it with its own `/** */` comment.
  - `[medium]` `[patch]` (blind) The section showed on `roster_count > 0`, not once Invitations exist; the seeded demo Class showed four zeros — the section now renders only when a count or a bounce is non-zero (`hasActivity`, unit-tested).
  - `[low]` `[reject]` (blind) «Kom ikke fram» is read three times — count label, list heading and each row's registration status are separate places the story asks for; the row must name the status in full.
  - `[low]` `[patch]` (blind) Untested behaviours — tests added for a streamed body over the cap and an older id replay; concurrent events, mixed-case headers (lower-cased by Starlette), re-sent Invitations (Story 4.7) and a malformed local secret rejected as low.
  - `[low]` `[reject]` (blind) The e2e leaks its context on failure and may reuse a Class name — same pattern as every Class spec; names are per fresh Lecturer, so a collision is harmless.
  - `[low]` `[reject]` (blind) Migration 0028 takes locks while validating — small table in v1, migrations run before the api starts (as 0027).
  - `[low]` `[reject]` (edge) An event arriving before `send` commits the provider id is acknowledged and lost — `send` commits milliseconds after the provider answers; delivery and bounce events come later; a 5xx for unknown mails would contradict «acknowledged and ignored».
  - `[low]` `[patch]` (edge) A non-stored event type with non-object `data` answered 400 — the type is checked first, so it is ignored with 200; test `test_an_ignored_event_type_needs_no_readable_data`.
  - `[low]` `[reject]` (edge) The dev bounce gives 500 with a malformed local secret — local only; production refuses such a secret at start.
  - `[low]` `[reject]` (edge) The dev route answers 200 when the event changed nothing — it reports which mail it bounced; the provider rules decide the state (a hard bounce stays hard).
  - `[medium]` `[patch]` (edge) Counts stale after a send — grouped with the blind stale-figures row.
  - `[low]` `[patch]` (edge, claim) Section shown before any Invitation — grouped with the blind display-condition row.
  - `[false]` `[reject]` (intent) The bounce is not written into the Roster entry's stored registration — the story asks that the entry shows the bounce in its registration status and that `classes` read delivery state from `messaging`; each bounced entry is returned with `registration: "bounced"` and its class, derived at read; the full status list is Story 4.7's.
  - `[low]` `[reject]` (intent) The bounced count includes registered or removed entries the list leaves out — counts count Invitations as the story says; the list names addresses that still need action (documented in the schema).
  - `[low]` `[patch]` (intent) No test posts to the webhook over HTTP and then reads the counts — `test_a_bounce_posted_to_the_webhook_shows_in_the_counts` added.
  - `[low]` `[reject]` (intent) «Accepted» is set by SQL in the tests — Story 4.5's acceptance writes exactly `accepted_at`, which the count reads; its own tests cover the flow.
  - `[low]` `[reject]` (intent) No case for an expired Invitation whose mail never went out — as the blind «Utløpt > Sendt» row.
  - `[low]` `[patch]` (intent) An older event id replayed answers `stored` — grouped with the blind idempotency row.
  - `[false]` `[reject]` (intent) The section's condition is the Roster count — patched with the blind display row; the condition now matches «Given Invitations have been sent».
  - `[low]` `[patch]` (verification-gap) The streaming branch of the body cap is never exercised — `test_a_streamed_body_over_the_limit_is_refused_without_a_declared_length` added.
  - `[false]` `[defer]` (verification-gap) «Newest Invitation per entry» and «newest delivery per Invitation» are not pinned — no code path makes a second Invitation per entry before Story 4.7; deferred to 4.7.

## Design Notes

- Copy [ASSUMPTION]: heading «Invitasjoner»; labels «Sendt», «Kom ikke fram», «Akseptert», «Utløpt»; list heading «Kom ikke fram»; lead «E-posten nådde ikke disse adressene.»; classes «permanent feil» / «midlertidig feil».
- Counts are Invitations, not addresses (4.7 reminders add Invitations per address); bounced is a subset of sent.
- Layout: four tabular-figure numbers with labels beneath on a hairline row (2×2 under `sm`), list as hairline rows with the address wrapping (`break-all`).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/messaging tests/classes tests/test_imports.py tests/test_authz_rules.py tests/test_config.py -q` -- pass.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt stack with `worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** The Lecturer now sees what became of the Invitations. `POST /api/webhooks/resend` (mounted everywhere, the one mutating route without `X-Requested-With`) verifies Resend's Svix signature under `RESEND_WEBHOOK_SECRET` (5 min tolerance, 256 KiB cap), finds the `mail_deliveries` row by provider message id and stores delivery state, bounce class and last event id (migration 0028). States only move forward (delayed < soft bounce < delivered < hard bounce); a repeated or older event changes nothing; unknown mails and other types are acknowledged and logged by type only. `messaging.service.invitation_deliveries` exposes the state; `GET /api/classes/{id}/invitations` (owners) combines it with `identity`'s Invitation facts into sent / bounced / accepted / expired and the bounced Roster addresses with `registration: "bounced"` and `hard`/`soft`. The Class page shows «Invitasjoner» (four figures, then «Kom ikke fram» rows reading «Kom ikke fram, permanent feil» / «… midlertidig feil»), refreshed every 15 s. Locally `POST /api/dev/mailbox/bounce` signs an `email.bounced` event for the newest mail to an address and runs it through the same handler; it is not mounted in production.

**Process note.** The caller required the implementation in this context. The four review layers ran as sub-agents; their reports were read from their transcripts.

**Files changed**
- `backend/app/platform/config.py`: `RESEND_WEBHOOK_SECRET` (local default; production refuses default, empty or malformed), `webhook_key`.
- `backend/migrations/versions/0028_mail_delivery_events.py`, `messaging/models.py`: three columns, checks, provider-id index.
- `messaging/{signature,webhooks}.py` (new), `messaging/{repo,service,routes}.py`, `app/main.py`: verify, store, read, dev bounce.
- `identity/{repo,service}.py`: `class_student_invitations`.
- `classes/{schemas,service,routes}.py`, `classes/README.md`: summary route and decisions.
- Tests: `tests/messaging/test_webhook.py` (new), `tests/classes/test_invitation_counts.py` (new), `test_imports.py`, `test_authz_rules.py`, `test_config.py`, `test_migrations.py`, `identity/test_csrf.py`.
- Frontend: `modules/classes/invitation-summary.tsx` and its test (new), `api.ts`, `class-page.tsx`, `roster-upload.tsx`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}`, `e2e/invitation-bounces.spec.ts` (new).
- `.env.example`, `railway/backend/railway.toml`: the new secret named.

**Review findings.** 30: 4 medium (3 entries after grouping), 22 low, 4 false. Patched: 3 medium entries and 8 low entries. Deferred: 1 (multi-Invitation cases, Story 4.7). Rejected: the rest, each with its reason in the Review Triage Log.

**Follow-up review recommended: true.** Three medium entries were patched. Named unverified risk: the 15 s refetch and the hide-when-empty rule of «Invitasjoner» are covered by a unit test of `hasActivity` and the e2e after bounces, but no e2e watches the counts change on an open page.

**Verification**
- Backend: ruff clean; full pytest 2171 passed (82 s).
- Frontend: typecheck, `npm test` (354), `check:copy`, `lint:colours`, build pass; Playwright 149 passed against the rebuilt stack with `worker-batch`, including `invitation-bounces.spec.ts` at 320 and 1440 px with axe and no horizontal scroll.
- No new test over 1 s (slowest 0.93 s, the 0028 downgrade test).
- Shared test databases: revision 0028 added and migrated once; not changed after it ran.
- Layout checked on screenshots at 390 and 1280 px (`screenshots/4.6/`).

**Decisions taken in place of the founder**
- Bounce source: Resend's Svix-signed webhook; `Permanent` = hard, `Transient`/`Undetermined` = soft; `email.delivered` and `email.delivery_delayed` stored too; a later delivery beats a soft bounce, nothing beats a hard one.
- Local simulation: a dev-only route `POST /api/dev/mailbox/bounce` (not a reserved domain), signing with a built-in local secret that production refuses.
- `RESEND_WEBHOOK_SECRET` is required in production (`whsec_` + base64).
- Counts count Invitations, not addresses; `sent` = mail handed to the provider; `expired` leaves out accepted and voided; the bounced list leaves out registered and removed addresses.
- A bounce is not written into `roster_entries.registration`; it is derived at read time.
- Only owners see the counts (Assistants are Story 4.9's); the section appears once any count is non-zero and refreshes every 15 s.
- Copy [ASSUMPTION]: «Invitasjoner», «Sendt», «Kom ikke fram», «Akseptert», «Utløpt», «E-posten nådde ikke disse adressene.», «Kom ikke fram, permanent feil / midlertidig feil», «Tallene for Invitasjonene kunne ikke hentes.».

**Residual risks**
- Re-sent Invitations (Story 4.7) are not yet tested in the counts (deferred).
- An event that arrives before `send` commits the provider id is acknowledged and lost.
- Resend payloads are checked only against the documented format, not a live account.
