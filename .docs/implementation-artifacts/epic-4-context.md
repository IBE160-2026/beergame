# Epic 4 Context: Classes, Roster and Invitations

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Give the Lecturer a place for their Students. When this epic is done, a Lecturer can create a Class, upload the Roster from a Canvas export or by pasting addresses, send Student Invitations with a validity period, follow who has registered (including bounces), send reminders, register Students by hand, share the Class with co-owner Lecturers and class-scoped Assistant lecturers, and archive it. A Student can register through the Invitation and becomes a Student in the Class. The epic owns `backend/app/modules/classes/` and `frontend/src/modules/classes/`, and produces `classes.service.registered_students(class_id)` and `is_writable(class_id)`, which Epic 5's allocation and session setup depend on.

## Stories

- Story 4.1: Create a Class from the Lærerhjem
- Story 4.2: Upload a Roster file and pick the e-mail column
- Story 4.3: See invalid rows and paste addresses instead
- Story 4.4: Send Invitations to the Roster with a validity period
- Story 4.5: Register as a Student through the Invitation
- Story 4.6: See bounced Invitations and the counts
- Story 4.7: Follow registration status and send reminders
- Story 4.8: Register a Student manually and change single addresses
- Story 4.9: Share a Class with co-owner Lecturers and Assistant lecturers
- Story 4.10: Archive a Class

## Requirements & Constraints

- **Class:** name, an Institution and an optional course code; the creator becomes owner. Co-owners have exactly the owner's rights. A Class always keeps at least one owner. Archived Classes are read-only and kept for statistics until the retention period ends.
- **Roster upload:** .xlsx or .csv, or pasted addresses. The Lecturer picks the e-mail column; Canvas people and grade-book exports must be accepted without editing (verified on synthetic fixtures only; real Canvas exports are an open point for the founder). Malformed and duplicate addresses are listed per row with a reason in text; valid ones are accepted. Single addresses can be added or removed later; a removed Student loses access to the Class but keeps their account and other Classes.
- **Invitations:** sent to every Roster address not yet registered; validity defaults to 14 days and can be changed per sending within a stated range. «Send N Invitasjoner» both saves the valid rows and sends; there is no save-now-send-later. The Lecturer sees sent, bounced, accepted and expired counts. Accepting sets password and name and makes the person a Student in the Class; an existing User (e.g. Student of another Class) is reused, never duplicated.
- **Registration status:** invited (with last valid day), registered, registered manually, unregistered after expiry, bounced (hard/soft), asked for new Invitation, not yet invited. Addresses unregistered after expiry or removed are never allocated to Class games. Reminders resend with a new validity, void old tokens, skip registered addresses and leave out hard-bounced ones (named in the result). Manual registration creates or reuses a User without a password and mails a single-use set-password link.
- **Staff:** «Legg til Faglærer» needs an existing User who already has the Lecturer role (rejected otherwise without revealing account details). Assistant lecturers are invited by e-mail for one Class only; they see the Roster but cannot create/archive Classes, change the Roster, send Invitations or manage staff (actions not rendered and rejected by policy).
- **Scale:** a Class of at least 400 Students; send returns once rows commit, mails go out from `worker-batch` within the provider's rate limit. Size/row limits are configuration (`ROSTER_MAX_FILE_MB`, `ROSTER_MAX_ROWS`), plus `ROSTER_STAGING_TTL_HOURS` (24) and `MANUAL_REGISTRATION_LINK_DAYS` (14), placeholder defaults.
- **E-mail delivery:** bounces are reported to the Lecturer; mails in Norwegian headed «ØL-spillet», naming the Class and the last valid day.
- **Accessibility:** Playwright with axe at 320 px, 200 % text and 1440 px (320/360 with correct keyboards and ≥ 44 px targets for Student registration); keyboard-only upload flow; no page-level horizontal scroll.

## Technical Decisions

- **Personal data stays in `identity`:** Roster entries (`roster_entries`: Class id, email, optional `user_id`, `registration`, `removed_at`) and staged uploads (`roster_uploads`, `roster_upload_rows` with cells as JSONB and `expires_at`) are `identity` tables; `classes` reaches them only through `identity.service`. Job args, logs and audit rows hold ids only; staged rows never reach logs or job args.
- **Upload staging:** the file is parsed in memory (openpyxl read-only; CSV with comma/semicolon and UTF-8/Windows-1252 detection) and never written to disk or a bucket. One staged upload per Class (a new one replaces it). Expired uploads are never returned; idempotent `identity.purge_expired_roster_uploads()` runs on every upload and staging read so `ops.sweep` can call it later. Column changes re-evaluate from staged cells.
- **Validation:** one validation function in `identity.service` for upload, paste and single-address add; addresses compared trimmed and case-insensitive; duplicates within the file name the first row; duplicates against the Roster are flagged.
- **`classes` owns** `classes` and `class_staff` (owner / co-owner / Assistant lecturer), plus `archived_at`. Archived Classes reject every mutation with the stable code `class_archived` from one check in `classes.service`.
- **Authorization:** `platform/authz` gains `classes_visible_to(user)` and Class read/manage policies (4.1) and a Student scope helper (4.5); every `classes` repository query joins through a scope helper; no `if role ==` in modules; the route-policy test must keep passing. Non-staff and non-existent Classes give the same permission-denied state. Only owning Lecturers pass mutating policies.
- **Registries instead of imports:** `classes.service` registers the Lecturer-revoke blocker (counts active, non-archived owned Classes) and, from 4.9, an acceptance handler for Invitation kind `assistant` in a new `identity.service` acceptance-handler registry. `identity` imports no `classes` code (import check).
- **Invitations:** the Epic 3 `invitations` table is extended expand-only with Class reference, Roster entry reference and kinds `student`/`assistant`. Send is one transaction in `classes.service` (Roster write, staging delete, Invitations), idempotent on the Roster entry and `dedupe_key`. Mail goes via `platform/notify.enqueue` as `immediate` kind `invitation`, addressed by reference (`user_id` empty, `ref` = Invitation id, no `user:<id>` emit). Expiry is read from `expires_at`, not a job. Acceptance attempts are rate-limited via `platform/ratelimit`; expired-link renewal sets `renewal_requested_at`.
- **Bounces:** `/api/webhooks/resend` verifies the signature with `RESEND_WEBHOOK_SECRET` (only route exempt from `X-Requested-With`), is idempotent on the provider event id, and updates `mail_deliveries` (owned by `messaging`, adds delivery-state, bounce-class, last-event-id columns). Unknown mails are acknowledged and logged without addresses. `classes` reads delivery state through `messaging.service`, never the table. Counts are computed in the api, not the browser.
- **Events/audit:** emit `user:<id>` on Student acceptance, removal, staff add/remove and archive; staff changes and archive write an audit row through `platform/audit`.
- **Local seed (`APP_ENV=local` only):** one demo Class owned by the demo Lecturer (4.1); 8 registered demo Students with linked Roster entries (4.5). Mock mail sender records deliveries; a test helper posts signed bounce events.

## UX & Interaction Patterns

- **Lærerhjem:** empty state with «Ny Klasse» as the only action; otherwise «Klassene dine» (name, course code, Roster count, each a Lenke) with places for what is waiting and next deadline (empty until Epic 5); archived Classes under their own heading, marked in text.
- **Lag Klasse:** one column, title in `title-page`, Tekstfelt/Knapper from `frontend/src/components/`. Filopplasting: outlined box with «Velg fil» and «Lim inn adresser i stedet»; after reading, file name, «250 rader lest», «Bytt fil»; «E-postkolonne» native select styled as Tekstfelt listing every column by letter and header, preselected with its reason («Kolonne C, E-post. Valgt fordi alle rader unntatt fire ser ut som adresser.»). Unreadable file: «Filen kunne ikke leses. Bruk .xlsx eller .csv, eller lim inn adressene.»
- **Invalid rows:** «Ugyldige rader: 4 av 250», one line per row (number, value, reason: «Domene mangler», «Mangler @», «To @», «Tom celle», duplicate), never colour alone, stacked at 320 px with wrapping; «Registrer manuelt» per row; «Ugyldige rader får ingen e-post før de er rettet.»; primary «Send 246 Invitasjoner» with the real count, disabled (not secondary) when nothing is valid.
- **Status etter utsending:** totals in text («Registrert 238», «Manuelt 2», «Uregistrert 10»), «Send påminnelse til 10», list filterable by status and searchable by address.
- **Forms and actions:** manual registration is an in-place form with focus to the first field and «Avbryt» returning focus to the link; removal and archive buttons state the consequence before being pressed; reminders are confirmed with a validity period prefilled with 14 days. «Faglærere og assistenter» lists both groups with status, «Legg til Faglærer», «Inviter Assistent» and «Assistenten får tilgang bare til denne Klassen.»
- **Student side:** «Du er invitert» reused with e-mail locked, Class name and «Invitasjonen er gyldig i 14 dager. Du får Rolle og spill på startdatoen.» (draft copy); Hjem names the Class. Missing copy (expired Invitation, duplicate Roster row, archive consequence) is added as draft to `nb.ts`.

## Cross-Story Dependencies

- 4.1 creates `classes`/`class_staff`, the authz scope helper and the revoke blocker; everything else builds on it. 4.2 creates staging tables used by 4.3 and consumed by 4.4. 4.4 creates `roster_entries` and the Invitation extension that 4.5–4.8 read. 4.5 adds the Student scope and the seeded Students. 4.6 bounce data feeds 4.7 statuses; 4.8 adds «not yet invited» to 4.7's list and gives 4.3's «Registrer manuelt» its form. 4.9 adds the acceptance-handler registry. 4.10 adds `is_writable` and must cover every mutating `classes` route.
- Builds on Epic 3: `platform/authz`, `audit`, `notify`/`messaging`/`mail_deliveries`, `ratelimit`, the revoke-blocker registry, «Du er invitert», «Nytt passord», `renewal_requested_at`, homes and shared components.
- Feeds Epic 5 (`registered_students`, `is_writable`, Lærerhjem waiting/deadline slots) and Epic 15 (`ops.sweep` purge, deletion of unregistered Roster addresses and Invitations).
