# `modules/classes`

Classes, their staff and, through `identity.service`, their Roster (Epic 4). Other modules import
only `classes.service`.

## Roster upload staging (Story 4.2, decided)

- The uploaded file is read in memory by the api (`identity/roster_file.py`: openpyxl in read-only
  mode for `.xlsx`; CSV with comma, semicolon or tab, decoded as UTF-8 with or without a byte-order
  mark, or Windows-1252). It is never written to disk or to a bucket.
- Only its cell values are kept, as staged rows in the `identity` tables `roster_uploads` and
  `roster_upload_rows` (upload id, Class id, uploader id, row number, cells as JSONB,
  `expires_at`). `classes` reaches them only through `identity.service` (AD-14). The only tie the
  other way is a database foreign key from `roster_uploads.class_id` to `classes.id` (by name, so
  a deleted Class takes its staging with it); `identity` imports no `classes` code.
- The api reads the file off the event loop, and two uploads for one Class at once are taken one
  after the other (a transaction-scoped lock), so the second replaces the first.
- One staged upload per Class: a new upload replaces the earlier one in one transaction. A file
  that cannot be used (wrong type, unparseable, empty, over a limit) answers 422
  `roster_unreadable`, stages nothing and leaves an earlier staged upload as it was.
- Expiry is configuration, `ROSTER_STAGING_TTL_HOURS` (placeholder 24). An expired upload is never
  returned. `identity.service.purge_expired_roster_uploads(now)` deletes expired uploads, is
  idempotent, and runs on every upload and every read of a Class's staging, so `ops.sweep` can call
  it later unchanged.
- Limits are configuration: `ROSTER_MAX_FILE_MB` (placeholder 5) and `ROSTER_MAX_ROWS`
  (placeholder 5000), both well above a Class of 400 Students. The api reads at most the limit
  from the request body. A workbook whose parts unpack to more than 200 MB is refused before it
  is opened.
- Logs, job arguments and audit rows carry ids and counts only, never a file name, a cell or an
  address.
- The first non-empty row is the header unless one of its cells looks like an address. Empty rows
  are skipped, and each row keeps its number in the file so Story 4.3 can name it.
- The column with the most cells that look like addresses is preselected (the leftmost on a tie).
  None is preselected when no cell looks like one.

## Invalid rows and pasted addresses (Story 4.3, decided)

- One check, `identity.schemas.address_problem`, decides whether a value is an address and why
  not: `empty`, `whitespace`, `missing_at`, `two_at` (two or more), `missing_name`,
  `missing_domain`, in that order. `email_is_valid` (login, access requests) is built on it, so
  every form agrees. `identity.service.evaluate_roster_rows` applies it to the chosen column.
- Addresses are compared trimmed and lower-cased. Only valid addresses can repeat: the first
  occurrence (lowest row number) is valid, and each later one is `duplicate` with `first_row`.
- The staging answer carries `valid_count` (what «Send N Invitasjoner» counts) and every invalid
  row (number, value, reason). With no column chosen, nothing is valid and nothing is listed.
- Pasted text (`POST /api/classes/{id}/roster-paste`) is staged in the same tables, with
  `source = 'paste'`, one column, no header, and rows numbered by their place in the text. It is
  split on line breaks, commas, semicolons, whitespace and NUL; `Navn <adresse>` and
  `"Etternavn, Fornavn" <adresse>` keep only the address; brackets, quotes and `mailto:` around
  a piece are dropped. An empty paste stages no rows. Text over `ROSTER_MAX_FILE_MB` or with more
  pieces than `ROSTER_MAX_ROWS` answers 422 `roster_paste_too_long` and stages nothing.
- «Send N Invitasjoner» and «Registrer manuelt» are drawn now; they act from Stories 4.4 and 4.8.

## The Roster and sending Invitations (Story 4.4, decided)

- `roster_entries` (owned by `identity`) holds one row per address and Class: `registration`
  `invited` or `registered` (later stories add states), `user_id` once known, `removed_at` set by
  a removal. `(class_id, email)` is unique. `classes` reaches it only through `identity.service`.
- `POST /api/classes/{id}/invitations` with the staging's `upload_id` and `valid_days` is one
  command in `classes.service`, one transaction: under the staging lock it writes the valid
  addresses to the Roster (ON CONFLICT DO NOTHING), deletes the staging, and creates one
  `invitations` row of kind `student` (Class and Roster entry set, `role` NULL) per new entry,
  with its `invitation` notice addressed by reference and its claim job deferred in one statement
  (`notify.enqueue_by_ref`, `jobs.defer_many`). A repeat, a replaced staging or an expired one
  answers 404 `not_found`; a staging with nothing valid 422 `nothing_to_send`.
- A staged address already on the Roster, invited or registered, is listed as `on_roster` and
  is not counted or sent. Re-inviting listed addresses is the reminder of Story 4.7.
- The validity is 1–60 whole days, 14 by default ([ASSUMPTION]: FR-8 asks for a stated range).
  An Invitation works through the last valid day in Europe/Oslo: `expires_at` is the Oslo
  midnight after today + N days, so the mail and the result line can say «til og med 3. desember».
- The mail names the Class through a resolver `classes.service` registers with `identity` at
  import (`messaging.delivery` imports `classes.service` so the worker has it); `identity` imports
  no `classes` code.
- The link leads to `/invitasjon` («Du er invitert», Story 4.5). The Admin's invitation list and
  resend show and take role Invitations only.
- The Resend sender paces sends to `MAIL_PROVIDER_PER_SECOND` (2) per process; the mail queue
  runs in the one `worker-batch` process. The mock sender is not paced.

## Student registration (Story 4.5, decided)

- «Du er invitert» and the Story 3.8 routes (`check`, `accept`, `accept-login`, `renewal`, same
  rate limits) take Student Invitations too. A Student link names its Class («name, course code»,
  through the label resolver this module registers) and the Lecturer who sent it, and counts the
  days left to its last valid day in Europe/Oslo (a 14-day sending reads «14 dager» that day).
- Accepting is one transaction in `identity.service`: the Invitation locked, the User created
  without an account role (or the existing User proven by its password: never a second User), the
  Roster entry locked, linked to the User and set `registered`, the Invitation accepted, and
  `user:<id>` emitted. A Roster entry removed meanwhile refuses the link and writes nothing. Student
  acceptance writes no audit row (the epic audits staff changes and archive only).
- The Student scope is `authz.classes_enrolled_by`: Roster entries linked to the User and not
  removed (migration 0027 indexes `roster_entries.user_id`). `GET /api/classes/enrolled` lists
  them for Hjem; `GET /api/classes/enrolled/{id}` answers one or 403 `forbidden`.
- Local seed: on every start the demo Class gets `student@example.com` and `student2`…`student8`
  `@example.com` («Demo Student N», password `olspillet-demo`) as registered Students; existing
  Users and Roster addresses are left as they are.

### Bounces and counts (Story 4.6)

- The mail provider posts delivery, delay and bounce events to `POST /api/webhooks/resend`
  (`messaging/webhooks.py`), admitted by their Svix signature under `RESEND_WEBHOOK_SECRET`
  (5 minutes' tolerance), the one mutating route without `X-Requested-With`. The event is stored on
  the `mail_deliveries` row with the provider's message id (migration 0028: `delivery_state`,
  `bounce_class`, `last_event_id`). States only move forward (delayed, delivered, bounced) and a
  hard bounce stays hard, so a repeated or late event changes nothing; the same event id twice is
  `repeated`. Events for unknown mails, and other event types, are acknowledged and logged with
  their type only.
- `GET /api/classes/{id}/invitations` (owners) counts the Class's Student Invitations at read
  time: `sent` and `bounced` from the mails (`messaging.service.invitation_deliveries`, never the
  table), `accepted` from `accepted_at`, `expired` from `expires_at` (not voided). It lists the
  Roster addresses (not registered, not removed) whose newest Invitation bounced, with
  `registration: "bounced"` and the class: `hard` for Resend's `Permanent`, else `soft`. The
  Roster entry's stored `registration` is not changed by a bounce.
- Locally, `POST /api/dev/mailbox/bounce` `{to, bounce_class}` signs an `email.bounced` event for
  the newest mail sent to an address and passes it through the same handler. Like the dev mailbox
  it is not mounted in production; production also refuses the local default secret.

### Registration status and reminders (Story 4.7)

- `GET /api/classes/{id}/registrations` (owners) reads every Roster address that is not removed
  with its status, derived at read time and never stored: `registered`, `registered_manually`
  (migration 0029 allows the value; Story 4.8 writes it), `renewal_requested` (a Student asked for
  a new Invitation from a link that no longer works), `bounced` (+`bounce_class`, the newest
  Invitation's mail), `invited` (+`last_valid_day`), `unregistered` (newest Invitation expired or
  voided). The first that applies wins. Totals: registered, manual, and the rest as unregistered;
  `reminder_count` is the unregistered total.
- `POST /api/classes/{id}/reminders` `{valid_days, roster_entry_id?}` sends a new Invitation to
  every address that has not registered, or to one. In one transaction under the Roster staging
  lock, `identity.service.send_entry_reminders` voids the entries' open Invitations, reads the
  entries again (an acceptance that committed meanwhile gets nothing), clears their renewal
  requests and enqueues one `invitation` notice per new Invitation. An address whose newest
  Invitation bounced hard is left out, for all and for one, and named in `left_out`. Nothing to
  send and nothing left out is 422 `nothing_to_send`.
- `service.registered_students(class_id)` gives Epic 5 the Users of registered and manually
  registered entries that are not removed; an address unregistered after expiry is never among
  them.

### Manual registration and single addresses (Story 4.8)

- Three owner-only commands, each one transaction through `identity.service` under the Roster
  staging lock. The open Invitations of an entry are voided before the entry is locked, the order
  an acceptance takes its locks in. Each answers the entry's status as the status list reads it.
- `POST /api/classes/{id}/roster/manual` `{email, name, roster_entry_id?, upload_row?}`: the
  User of the address is reused unchanged, or created with the name, no password (migration 0030
  makes `users.password_hash` nullable; such an account never logs in) and no account role. Its
  entry (new, waiting, or removed and put back) is linked and set `registered_manually`: the
  Student is in the Class at once. A registered address is refused as `already_registered`.
  `roster_entry_id` is the row the form opened from: when another address is typed, that row is
  removed if it is not registered (how a wrong address is corrected). `upload_row` deletes the
  staged invalid row it corrected. Whether the address had an account is never answered.
- The Student gets a `manual_registration` mail (`immediate`, to the User, `ref` = the entry). A
  User with no password gets a single-use `password_resets` link to «Nytt passord», valid to the
  end of the `MANUAL_REGISTRATION_LINK_DAYS`-th day in Europe/Oslo (placeholder 14); a User with a
  password is told to log in as usual. The mail is skipped when the entry was removed or the link
  is used or expired.
- `POST /api/classes/{id}/roster/entries` `{email}` adds one address, checked by
  `address_problem` (or refused as `on_roster`), with no Invitation: status `not_invited`, counted
  as unregistered and remindable, so a reminder sends its first Invitation. A removed address is
  put back as it was; a registered Student has access again without a new registration or mail.
  A Roster send of a removed address puts it back too, and invites it unless it is registered.
- `DELETE /api/classes/{id}/roster/entries/{entry_id}` marks the entry removed, voids its open
  Invitations and emits `user:<id>`; the Student scope (`authz.classes_enrolled_by`) and
  `registered_students` leave it out from the next request. The User and other Classes stay.
- An address of a registered Student is never edited in place: the account e-mail is the
  Student's login, used in every Class. The Lecturer removes it and adds the new address.

## Open point for the founder: real Canvas exports

The upload is tested only on synthetic fixtures with invented names and addresses, in the column
layouts of a Canvas people export and a Canvas grade-book export
(`frontend/e2e/fixtures/roster/`). Checking real Canvas exports is not part of Story 4.2. Before
the pilot, the founder supplies anonymised real exports (people and grade book), and they are
added as fixtures to the api tests in `backend/tests/classes/test_roster_upload.py`.
