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
- The link leads to `/invitasjon`, which takes only role Invitations until Student registration
  (Story 4.5): until then a Student link reads as not valid there. The Admin's invitation list and
  resend show and take role Invitations only.
- The Resend sender paces sends to `MAIL_PROVIDER_PER_SECOND` (2) per process; the mail queue
  runs in the one `worker-batch` process. The mock sender is not paced.

## Open point for the founder: real Canvas exports

The upload is tested only on synthetic fixtures with invented names and addresses, in the column
layouts of a Canvas people export and a Canvas grade-book export
(`frontend/e2e/fixtures/roster/`). Checking real Canvas exports is not part of Story 4.2. Before
the pilot, the founder supplies anonymised real exports (people and grade book), and they are
added as fixtures to the api tests in `backend/tests/classes/test_roster_upload.py`.
