# Key User Journeys, end to end

`frontend/e2e/journeys/whole-course.spec.ts`, run with `npm run e2e:journeys` against the local
stack (`playwright.journeys.config.ts`; not part of the default Playwright run). One serial whole
course with one Class and fresh people made through the product's own flows; what a person does
goes through the UI, and only the local `/api/dev/` routes stand in for time passing (the lock at
the Start date, the Debrief's move-on wait, the Play deadline playout, the Test deadline).

Run of 2026-11-23 on branch `journeys` (main at `bbb3a250` plus the fix `1004e7f5`): 15 tests in two files, all passed, 7.6 min.

- UJ-1 pass: the Admin invites a new address as Faglærer in «Brukere og roller»; the mailed link
  becomes an account (name, password) that lands on the empty Lærerhjem. `uj-1-*.png`
- UJ-1 edge pass: an Assistent of the Class (invited from «Faglærere og assistenter») is granted
  Faglærer by the Admin and keeps one login: «Ny Klasse» appears, the colleague's Class stays.
- UJ-2 pass: «Lag Klasse», a Canvas-style CSV with 6 good and 4 malformed addresses (rows 5, 6, 10,
  11 listed with their reasons), 6 Invitations valid 14 days, 4 Students accept on phones, one is
  registered by hand from the status list and sets a password from the mail, one stays out
  (Registrert 4, Manuelt 1, Uregistrert 1). `uj-2-*.png`
- UJ-3 pass: «Lag Klasseøkt» with defaults and LLM players, Gruppedebrief, Obligatorisk, the four
  dates and four Labtimer; «Fordeling» draws 2 games for 5 Students (4, and 1 with 3 AI players)
  and is confirmed. `uj-3-*.png`
- UJ-4 pass: on the Start date (dev lock) four Students read the rules, do the Startoppgave, start
  the game and play 15 Weeks in four browser contexts (Veiledede uker, Setestatus, no week total);
  the Grossist pauses and everyone reads it. `uj-4-*.png`
- UJ-4 edge pass: a Labtime now, Bård marks the game «I rommet» with 2 min; three order (the Pause
  ends), the Fabrikk stays away, after 2 min the Grossist presses «Sett inn KI-spiller for …», the
  absent Student later presses «Ta tilbake setet» and plays again from the next Week; the game is
  played to its hidden end (36 Weeks). Found and fixed a bug here (below).
- UJ-5 pass: the Group debrief from the end screen, the other three join from Hjem, four
  Explanations unlock the reveal (customer demand 4 then 8), the opener moves the group to the chain
  (amplification per Role) and to step 4; Sara's reflection answers, her moments (Uke 11: 24 with
  27 on the way), «Fullfør Debriefen»; the quiz 1 of 3 right, the explanations read, passed on the
  second try; the Replay alone against three AI players to its end, and the walkthrough with
  «Ikke like for like» and the AI text. `uj-5-*.png`
- UJ-6 pass: the own-work statement, half the items one evening, the test closed and opened again,
  the rest (choices, the bakery table and the number item, long answers and the two Adapted items
  argued from the own game and Replay), every answer «Lagret», handed in. The shipped question set
  has no drawn item yet (content README, issue #16), so the drawing part is not exercised.
- UJ-7 pass: the Oversikt (1 finished with chain cost, the odd Student's game with 3 AI players),
  «Start spill som ikke har startet (1)», a Melding to all in Spill 2 that reaches the Student by
  e-mail, and at the Play deadline (dev playout) the AI players finish Spill 2. `uj-7-*.png`
- UJ-8 pass: after the Test deadline Hjem says «KI-vurderingen er klar.»; the assessment shows a
  score and feedback per item, quotes the Student's own answer, says it is AI-generated and counts
  toward nothing; Sara turns the Veiledende bokstav on; her Studentrapport PDF downloads; Bård
  downloads the ZIP of all five reports and the Completion export (.xlsx); the odd Student, who
  never took the test, gets a report too. The «ready» e-mail is a digest notice, which is never
  sent at night, so a night run does not see it. `uj-8-*.png`
- UJ-9 pass: the Klasserapport (funnel, chain cost, cost and amplification per Role,
  patterns, learning results per question), «Alle spill i plenum» with no Student names, and a
  Class session for next year's Class made with «Lag fra en tidligere Klasseøkt» and saved. In the
  whole course Tverrklasse-statistikk shows its empty state (one Class session only); the
  comparison itself is `uj-9-cross-class.spec.ts`: one fresh Lecturer, one Class of 10 registered
  Students, last year's (rule-based) and this year's (LLM) Class session set up through the api,
  games started and played out (dev `playout`), Test deadlines passed and locked (dev routes); the
  sweep writes both aggregates. The UI then compares both Class sessions, the KI-modus filter
  («LLM-spillere 1») brings the comparison to 1 of 2 and «Alle» back to 2, and this year's
  Klasserapport marks «Fjoråret» on the Kostnadsfordeling (last year's does not).
  `uj-9-*.png`

Bug found and fixed: after the lock, the late-registrant sweep treated a Student whose Seat an AI
player had taken over as unseated and moved them into an AI player's Seat of a Class game that had
not started. They lost their own game page (403) and could not take the Seat back. Commit
`1004e7f5`, with `test_a_student_whose_seat_was_taken_over_is_never_seated_again`.
