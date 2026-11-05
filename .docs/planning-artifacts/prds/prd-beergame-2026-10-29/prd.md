---
title: "PRD: beergame"
status: draft
created: 2026-10-29
updated: 2026-11-05
inputs:
  - .docs/planning-artifacts/briefs/brief-beergame-2026-09-04/brief.md (final)
  - .docs/planning-artifacts/briefs/brief-beergame-2026-09-04/addendum.md
  - .docs/forge/beergame-positioning-b/forge-report.html
  - .docs/planning-artifacts/research/ (competitive, user-voice, technical cost, academic-lit; 2026-10-26)
  - research-regulatory.md (this folder, 2026-10-29)
  - .docs/planning-artifacts/research/academic-lit-beer-game-test-questions-systems-thinkin-2026-11-05/research.md
  - .docs/planning-artifacts/research/domain-beer-game-variants-and-setup-options-2026-11-05/research.md
  - founder brain dump, answers and coaching narration (2026-10-29, 2026-11-02, 2026-11-05)
---

# PRD: beergame

*"beergame" is the repository name, not a product name. Naming is an open item.*

## 0. Document Purpose

This PRD defines what v1 of beergame must do: a Norwegian-language, mobile-first web product that runs the MIT Beer Distribution Game for a whole course, from invitation to a downloadable report. Formal grading is deliberately left to v2. The readers are the founder, who is also the first lecturer customer, and the downstream workflows that turn this into UX specifications, architecture and stories.

It builds on the final product brief and does not repeat its market case. Every domain noun is defined once in §3 Glossary and used verbatim afterwards. Features in §4 hold globally numbered functional requirements (FR-1 to FR-83), each with testable consequences. Inferences the founder has not confirmed carry an inline `[ASSUMPTION]` tag and are indexed in §13. Technical detail, cost tables, regulatory sources and rejected alternatives live in `addendum.md` in this folder.

## 1. Vision

The Beer Game has taught the bullwhip effect for sixty years, and it is disappearing from classrooms because running it is slow and fragile, and students leave unable to explain how their own orders produced the chaos they just lived through. beergame runs the whole exercise for the lecturer: invitations, groups, play, debrief, a second round, an individual test with non-counting AI feedback and a PDF report of it all, with AI players stepping into every seat a student leaves empty.

For the student, the game stops being a single event. After the class game and the group debrief, each student plays again alone against AI players under harder starting conditions, and then shows in an individual test, in their own words and with arguments, what they understood, and gets feedback on it from the AI. For the lecturer, the course stops being refereeing: every game is visible on one screen, no game waits more than a day for a missing student, and the evidence of who understood what arrives as a report per student instead of impressions.

The bet, carried over from the brief: **the product is working AI players plus the explanation.** AI players that behave well enough to teach with, and a debrief that explains each student's own decisions, are the differentiators. Bot-filled seats alone are not; competitors already offer them for free. Whether repetition plus explanation teaches more than one good session is untested, and the first class session in the founder's own course is where that evidence starts.

## 2. Target Users

### 2.1 Jobs To Be Done

- **Lecturer** (teaches supply chain, logistics or operations; courses of about 250 students): run the Beer Game midway through the course without spending weeks as a referee; know that every game finishes; make the exercise obligatory when the course needs it; get documentation per student for approval in the course's own systems; see whether students can explain the mechanism; rerun the exercise next year and compare.
- **Assistant lecturer**: help the lecturer monitor games, staff lab hours and message students in the Classes they are attached to.
- **Student**: get through the exercise on a phone or a laptop, mostly on the group's own schedule; understand why the supply chain oscillated and what their own orders had to do with it; get honest feedback on the individual test and keep a report of the work.
- **Admin** (platform operator; the founder in the pilot): give the right people lecturer access and keep users and AI spending under control.
- **Institution** (payer, not a user in v1): the exercise lands, the data handling passes the data protection officer's review, and someone is accountable when it breaks.

### 2.2 Non-Users (v1)

- Students who are not invited by a Lecturer: there is no public sign-up, free tier or individual subscription in v1.
- Pupils under 18. v1 targets higher education. `[ASSUMPTION: higher education only]`
- Corporate training buyers and researchers wanting raw exports beyond their own classes.
- Users outside Norwegian-speaking classrooms (v1 is Norwegian only).

### 2.3 Key User Journeys

*Narrated by the founder in the coaching round on 2026-11-02 and adjusted on 2026-11-05 when formal grading moved to v2. Names are illustrative; the founder is the model for Bård, the Lecturer.*

- **UJ-1. Kari, the admin, makes Bård a lecturer.**
  Kari runs the platform, opens the Admin area, enters Bård's email with the Lecturer role and sends the Invitation. Bård follows the link, sets a password, fills in a profile and lands on an empty lecturer home screen. **Edge case:** Bård already has an account as an Assistant lecturer in a colleague's course; Kari grants the Lecturer role to that account, and Bård keeps one login.

- **UJ-2. Bård invites 250 students three weeks ahead.**
  Two months into the course, Bård registers the Class "class-of-1994", exports the student list from Canvas as an Excel file, uploads it, and sends Invitations valid for two weeks. Over the next days the Roster fills up; students accept, set a password and fill in their profile. After two weeks, 238 have registered and 12 stand as unregistered. Bård manually registers two students who reported problems; the other ten stay out. **Edge case:** four addresses in the file are malformed; the upload lists them by row and accepts the rest.

- **UJ-3. Bård sets up the games in the last week.**
  A week before the start, Bård creates the Class session with default Game settings (a Lecturer of an advanced course may choose other settings) and LLM players, and marks it as obligatory for the course. The system splits the 240 enrolled students at random into 60 Class games of four and gives each student a random Role. Bård sets the start date and the deadlines and schedules four Lab hours in the computer lab. **Edge case:** with 241 students one Class game gets one student and three AI players.

- **UJ-4. Sara's group plays, mostly on its own schedule.**
  Sara, a logistics student, sees on the start date that the Wholesaler Seat in game 17 is Sara's, with three classmates in the other Seats. They agree to start Tuesday evening, each on their own phone. Every Week Sara sees inventory, backlog, incoming order and delivery, enters one order, and sees which Roles the game is still waiting for. They play 15 Weeks, stop, and continue on Thursday in a Lab hour with Bård in the room. Sara can see that they are in Week 27, but not how many Weeks remain. **Edge case:** Jonas, the Factory, stops answering; 24 hours after the Week opened for that Seat, an AI player takes over automatically, marked as AI, and the game goes on.

- **UJ-5. Sara's group debriefs together, then Sara plays alone.**
  When game 17 ends, the group opens the Group debrief together. First each writes, on their own phone, why the chain behaved as it did. Then the Debrief reveals customer demand (one step from 4 to 8), shows how orders grew from Retailer to Factory, and points at Sara's Week-11 order of 24 while 16 units were already on their way. Then each takes the Debrief quiz; Sara gets two questions wrong, reads why, and answers correctly on the second try. Over the weekend Sara plays the Replay alone against three AI players, with the same average demand as in the Class game but more variation from Week to Week.

- **UJ-6. Sara takes the individual test.**
  The Individual test is open for a week. Sara works on it over several evenings, closing it and coming back: some multiple-choice questions; an interactive task where Sara draws the inventory of a bakery after a jump in orders and works out how many extra units it must produce; and three long answers that require arguing, from Sara's own game and Replay, why the chain oscillated and what to do differently. Sara submits before the Test deadline.

- **UJ-7. Bård keeps 60 games on track.**
  During the play period Bård opens the Lecturer overview: 60 Class games, 41 finished, 15 running, 4 waiting for someone. Bård sees whom each game waits for and for how long, and sends a Message to the players of one game. One game has had an AI player inserted overnight. At the Play deadline, the two unfinished games are played to the end by AI players.

- **UJ-8. Sara reads the AI assessment; Sara and Bård download the reports.**
  After the Test deadline, Sara gets an email that the AI assessment is ready. It shows a score and written feedback per question, quotes Sara's own answers, and says plainly that it is AI-generated and counts toward nothing. Bård has left the Indicative letter off, so Sara turns it on for Sara's own view. Sara downloads a PDF report of the games, the Debrief and the test and uploads it to the course's learning platform. Bård downloads all 240 reports as one ZIP file and a completion list as a spreadsheet, and approves the obligatory requirement in the course's own system, based on completion alone. **Edge case:** a student who never took the test still gets a report, with that step marked as not done.

- **UJ-9. Bård compares and reruns.**
  Bård opens the Class report (test results, typical mistakes, how far orders amplified per Role), compares it with last year's Class session in Cross-class statistics, and creates next year's Class session from this one.

## 3. Glossary

*All later sections use these terms exactly.*

- **Admin** — platform operator role. Manages Users and roles in the Admin area.
- **Admin area** — the part of the product where the Admin registers Users, grants roles and sends Invitations.
- **User** — a person with an account. Holds one or more roles: Admin, Lecturer, Assistant lecturer, Student.
- **Lecturer** — role that creates and owns Classes and Class sessions. A Class can have several Lecturers.
- **Assistant lecturer** — role attached to specific Classes; helps monitor, staff Lab hours and send Messages, but cannot create or delete Classes or Class sessions.
- **Student** — role of a User on a Class's Roster who has accepted an Invitation.
- **Institution** — the school or university a Class belongs to. Used for data separation and reporting.
- **Invitation** — an email with a link that creates an account or adds a role to an existing account. Has a validity period.
- **Class** — a group of Students taught together (one course in one year), owned by one or more Lecturers. Has a Roster and one or more Class sessions.
- **Roster** — the list of student email addresses in a Class, with each address's registration status (invited, registered, unregistered).
- **Class session** — one run of the exercise for a Class: its Game settings, AI mode, Debrief mode, Individual test, deadlines, Lab hours and Games. Rerunning the exercise creates a new Class session.
- **Game settings** — the parameters every Class game in a Class session shares: starting inventory, supply-line contents, delays, Demand pattern, costs, number of Weeks, Information visibility and capacity.
- **Information visibility** — a Game setting that decides which numbers a Seat may see about its neighbouring Seats, for example the upstream Seat's inventory.
- **Demand pattern** — the customer demand series the Retailer faces: fixed series, step, or random from a seed.
- **Game** — one supply chain of four Seats played over Weeks. Either a Class game or a Replay.
- **Class game** — a Game played by a group of up to four Students of the same Class session, with AI players in any empty Seat.
- **Replay** — a Game a single Student plays after the Debrief against three AI players, using a Replay scenario. Each Student plays one Replay in v1.
- **Replay scenario** — the Game settings of a Replay. The Lecturer sets any Game setting differently from the Class game, so the Replay is harder or different through starting conditions, delays, Demand pattern or Information visibility.
- **Role** — Retailer, Wholesaler, Distributor or Factory.
- **Seat** — one Role in one Game. Occupied by a Student or an AI player.
- **Week** — one turn of a Game. All Seats order in the same Week; the Week advances when every Seat has placed its Order.
- **Order** — the single decision a Seat makes each Week: how many units to order from upstream (for the Factory: to produce).
- **Total cost** — the sum of holding and backorder costs over a Game, per Seat and for the chain.
- **AI player** — software occupying a Seat. Either an LLM player or a Rule-based player. Always disclosed as AI. The brief's "AI opponent" means the same thing.
- **LLM player** — an AI player whose Orders come from a large language model, checked against a response schema and the game rules in code.
- **Rule-based player** — an AI player whose Orders follow a documented deterministic rule.
- **AI mode** — the Class session setting that decides whether AI players are LLM players (default) or Rule-based players.
- **Effort** — the Class session setting that sets how much an LLM player thinks before it answers.
- **Play guard** — the system check that compares an LLM player's weekly Orders with reference players and switches the Seat to a Rule-based player when they fall outside the accepted band (FR-79).
- **Inactivity limit** — how long a Seat may leave its Order open before an AI player takes over. Default 24 hours.
- **Takeover** — an AI player taking over the Seat of a Student. **Reclaim** — the Student taking the Seat back.
- **Lab hour** — a scheduled time when the Lecturer or an Assistant lecturer is present and Students can play.
- **Start date** — the time from which Class games can be played.
- **Play deadline**, **Debrief deadline**, **Test deadline** — the times by which Class games must end, Debrief, Debrief quiz and Replay must be done, and the Individual test must be submitted.
- **Explanation** — the Student's own written account of what happened in their Class game, written during the Debrief, before customer demand is revealed.
- **Debrief** — the guided review after a Class game. Either a **Group debrief** (the Students of one Class game together; default) or a **Personal debrief** (one Student alone). **Debrief mode** chooses between them.
- **Debrief quiz** — a short quiz after the Debrief that each Student must answer correctly; retries allowed; wrong answers explained; counts toward nothing.
- **Individual test** — the test each Student takes after the Replay: weighted questions, multiple choice, Interactive items and long answers with argumentation. Consists of Core items and Adapted items. Does not produce a grade in v1.
- **Core items** — Individual test questions that are the same for every Student in a Class session.
- **Adapted items** — Individual test questions generated from the Student's own Class game and Replay.
- **Interactive item** — an Individual test question the Student answers by working in a graph, table or diagram, not by choosing or writing text.
- **Control test** — a separate run of the Individual test taken by test students, where human and AI scores are compared. Not part of any Class session's results.
- **Item weight** — the share of the total score a question carries.
- **Scoring guide** — the guide (sensorveiledning) that tells the AI how to weigh questions and answers. It is the rubric for the AI assessment. The product provides a default; a Lecturer can edit it for a Class session.
- **AI assessment** — the AI's score and written feedback on one Individual test. Formative: it counts toward nothing and is never a grade.
- **Student report** — a PDF document of one Student's Class session: games, Debrief, Individual test and, optionally, the AI assessment.
- **Completion status** — which steps of the Class session a Student has done, taken from system events only (no AI judgement).
- **Indicative letter** — an A–F letter derived from the AI assessment's total score, shown only if turned on. Advisory and never a grade.
- **Obligatory class session** — a Class session the Lecturer has marked as a course requirement, met through the Completion status.
- **Decision log** — the stored record of every Order in every Game, with the state the Seat saw and, for AI players, the model, provider, prompt version and seed.
- **Lecturer overview** — the live view of all Class games in a Class session.
- **Game insight** — the full week-by-week view of one Game.
- **Class report** — the summary of one Class session's results.
- **Cross-class statistics** — comparisons across the Class sessions a Lecturer has access to.
- **Message** — a one-way notice from a Lecturer or Assistant lecturer to a Class session, a Class game or one Student.

## 4. Features

### 4.1 Accounts, roles and the Admin area

**Description:** Every person has one User account, reached through an Invitation; there is no open sign-up. The Admin hands out the Lecturer role, either by inviting a new email with the role built in or by granting it to an existing User. Lecturers invite Students and Assistant lecturers. Realizes UJ-1.

#### FR-1: Admin invites with a role
The Admin can enter an email address and a role (Lecturer or Admin) in the Admin area and send an Invitation. Realizes UJ-1.
- Following the link lets the recipient create an account with the role already granted; no further approval is needed.
- An expired or used link shows a message and a way to ask for a new Invitation.

#### FR-2: Admin grants a role to an existing user
The Admin can search Users by email or name and grant or revoke the Lecturer or Admin role.
- A User who gets the Lecturer role sees the lecturer home screen at next page load, with the same login.
- Revoking the Lecturer role from a User who owns Classes is blocked until another Lecturer is added to those Classes or the Classes are archived.

#### FR-3: Admin manages users
The Admin can list, search, deactivate and reactivate Users and resend Invitations.
- A deactivated User cannot log in; their data stays with their Classes.
- Every Admin action is written to an audit log with actor, time and change.

#### FR-4: Account creation and login
A person following an Invitation can create an account with password and profile (name; email prefilled and not editable), and later log in with email and password. `[ASSUMPTION: email + password]`
- Password reset by email works without Admin involvement.
- One email address maps to exactly one User; an Invitation to an email that already has an account adds the role to that account.

#### FR-5: Role-scoped access
The system restricts each User to what their roles allow.
- A Student sees only their own Class sessions, Games, Debriefs, Replays, Individual tests, AI assessments and Student reports.
- An Assistant lecturer sees only the Classes they are attached to, including AI assessments and Student reports. `[ASSUMPTION: Assistant lecturers see AI assessments]`
- The Admin sees all Users but not Students' answers or AI assessments unless also attached to the Class.

### 4.2 Classes, Rosters and Invitations

**Description:** The Lecturer registers a Class, uploads the student list exported from Canvas, and sends Invitations about three weeks before the games start. Invitations expire; Students who have not accepted stand as unregistered, and the Lecturer can override that by hand. Realizes UJ-2.

#### FR-6: Create a class
A Lecturer can create a Class with a name, an Institution and an optional course code.
- The creating Lecturer becomes owner.
- A Class can be archived; archived Classes are read-only and kept for Cross-class statistics until the retention period ends (§6.1).

#### FR-7: Upload the roster
A Lecturer can upload a student list as an Excel (.xlsx) or CSV file, or paste email addresses, into the Roster. Realizes UJ-2.
- The Lecturer picks which column holds the email addresses; a Canvas grade-book or people export is accepted without editing. `[ASSUMPTION: Canvas export format to be confirmed with a sample file]`
- Malformed or duplicate addresses are listed by row with the reason; valid addresses are accepted.
- The Lecturer can add and remove single addresses later; a removed Student loses access to the Class.

#### FR-8: Send invitations
A Lecturer can send Invitations to all Roster addresses not yet registered, with a validity period. Realizes UJ-2.
- The validity period defaults to 14 days and can be changed per sending.
- The Lecturer sees counts of sent, bounced, accepted and expired Invitations.
- A Student who accepts sets a password and profile and becomes a Student in the Class.

#### FR-9: Registration status and manual override
A Lecturer can see each Roster address's status (invited, registered, unregistered after expiry) and override it.
- After the validity period, addresses that have not accepted are marked unregistered and are not allocated to Class games.
- The Lecturer can resend an Invitation with a new validity period, or register a Student manually (the Student then gets an email to set a password).

#### FR-10: Co-lecturers and assistant lecturers
A Lecturer can add other Lecturers as co-owners of a Class and invite Assistant lecturers by email.
- An Assistant lecturer Invitation grants the role for that Class only. `[ASSUMPTION: Lecturers, not only the Admin, can invite Assistant lecturers]`
- Co-owners have the same rights as the owner.

### 4.3 Class session setup

**Description:** The Class session holds everything common to the whole class: Game settings, AI mode, Debrief mode, Replay scenario, Individual test, dates and Lab hours. Defaults are prefilled; the Lecturer may change any Game setting, and the change applies to every Class game. Realizes UJ-3.

#### FR-11: Create a class session with defaults
A Lecturer can create a Class session prefilled with classic Game settings and save it without changing anything.
- Defaults: four Roles; starting inventory 12 per Seat; 4 units in every supply-line slot; order delay 2 Weeks; shipping delay 2 Weeks; Factory production delay 2 Weeks; customer demand 4 per Week stepping to 8 in Week 5; holding cost 0.50 and backorder cost 1.00 per unit per Week; 36 Weeks. Confirmed by the founder against the course material (2026-11-05). The initial supply line holds 4 units in every slot, so the longer order delay adds slots; the exact slot layout is set in architecture.
- A Lecturer who has used the product once can create a Class session with defaults in under 10 minutes without help (SM-5).

#### FR-12: Change game settings
A Lecturer can change every Game setting before the Start date. Founder decision 2026-11-05: the Lecturer configures the game as they wish, with all parameters available.
- Settings: starting inventory, supply-line contents, order delay, shipping delay and Factory production delay (each 1 to 3 Weeks), costs, number of Weeks, Demand pattern (FR-13), Information visibility (FR-83) and capacity.
- Capacity is an optional maximum number of units a Seat can ship per Week, off by default, set for one Seat or for all. Units a Seat cannot ship stay as backlog. In a four-Role chain each Seat has one customer, so no allocation rule is needed. `[ASSUMPTION: capacity design from research; one platform precedent, no human evidence]`
- Out-of-range values are rejected with the allowed range shown. `[ASSUMPTION: ranges set in UX/architecture, e.g. 20–60 Weeks]`
- The only preset is "Classic" (FR-11). An advanced course has no preset of its own: the Lecturer decides what is different, and may keep the Classic values. Founder decision 2026-11-05.
- Game settings are locked from the Start date.

#### FR-13: Choose a demand pattern
A Lecturer can choose a Demand pattern: fixed series, step (start level, new level, Week of change) or random. Random demand is drawn each Week from a discrete uniform distribution over the whole numbers from mean minus spread to mean plus spread (never below 0), with a seed.
- The Lecturer can combine them: a step in the mean with random noise around it.
- Every Class game in the Class session uses the same demand series.
- The seed is shown to the Lecturer and stored with the Class session.

#### FR-83: Choose information visibility
A Lecturer can set Information visibility for the Class session, per Game settings. Founder decision 2026-11-05: a Seat seeing the inventory of its upstream neighbour is part of v1.
- Default: off, so a Seat sees only its own numbers (FR-23).
- A Lecturer can switch on that each Seat sees the current inventory (and backlog) of the Seat directly upstream, shown on the Seat's screen next to its own numbers.
- A Lecturer can also switch on the same view of the Seat directly downstream. Founder decision 2026-11-05: good idea, because the research finds downstream information the best-supported variant (see addendum).
- A Lecturer can switch on customer demand for every Seat (FR-14 otherwise limits it to the Retailer). `[ASSUMPTION: this option, from the research]`
- The setting applies to every Class game of the Class session and can differ in the Replay scenario (FR-49).
- AI players receive exactly the numbers a Student in that Seat would see, and the Decision log records what was visible (FR-67).
- The Student sees which neighbour numbers are shown, labelled with the Role and the Week they refer to.

#### FR-14: Hidden end and demand
Students are never shown the number of Weeks in a Game or the customer demand series while playing.
- Students see the current Week number and their own history, not how many Weeks remain.
- Only the Retailer Seat sees customer demand, one Week at a time, unless the Lecturer has switched it on for every Seat (FR-83).
- The Debrief reveals both (FR-44).

#### FR-15: Choose AI mode
A Lecturer can set the AI mode to LLM players (default) or Rule-based players for the Class session.
- The AI mode applies to every AI player in the Class session's Class games and Replays.
- A Lecturer who prefers not to use AI, or who needs fast and predictable play, chooses Rule-based players when the Class session is created. LLM players with an Effort level (FR-78) are the alternative.

#### FR-16: Choose debrief mode
A Lecturer can set Debrief mode (Group debrief by default, or Personal debrief).

#### FR-17: Obligatory class session
A Lecturer can mark a Class session as obligatory for the course, until the Start date. Realizes UJ-3.
- Students get an email when it is marked, and see it on their home screen and in deadline reminders.
- The requirement is met by completing every step: Class game, Debrief, Debrief quiz, Replay and submitted Individual test. Only the Completion status decides it; the AI assessment and the Indicative letter never do.
- The Class game step counts as done only if the Student placed Orders in at least a set share of the Weeks, so a Student who leaves the Seat to an AI player does not complete it. `[ASSUMPTION: Lecturer sets the share, default 80%]`
- A Lecturer can see who has not met the requirement and send those Students a Message in one action.
- The product records completion only; the Lecturer approves in the course's own system. `[ASSUMPTION: no approval action in the product in v1]`

#### FR-18: Set dates
A Lecturer can set the Start date, Play deadline, Debrief deadline and Test deadline.
- Dates must be in this order.
- The Test deadline defaults to 7 days after the Debrief deadline, and the Lecturer can change it. Founder decision 2026-11-05. `[ASSUMPTION: the 7 days count from the Debrief deadline]`
- Students see their next deadline on their home screen and get an email 24 hours before each deadline that applies to them. `[ASSUMPTION: 24-hour reminders]`
- A Lecturer can extend a deadline for the whole Class session or for one Student.

#### FR-19: Schedule lab hours
A Lecturer can add Lab hours (date, time, place) to a Class session, as many as needed.
- Students see upcoming Lab hours on their home screen and get them by email when added. `[ASSUMPTION: email on creation]`

### 4.4 Groups and Class games

**Description:** In the last week before the Start date, the system splits the registered Students at random into Class games of up to four and gives each a random Role. If the count does not divide by four, one Class game gets fewer Students and AI players in the empty Seats. Students can instead choose their game if the Lecturer prefers. Realizes UJ-3.

#### FR-20: Automatic random allocation
A Lecturer can let the system create Class games by placing every registered Student at random into groups of four and assigning each a random Role. Realizes UJ-3.
- If the number of Students is not divisible by four, exactly one Class game has fewer Students (one to three), and its empty Seats get AI players.
- The Lecturer sees the result before confirming, can re-run the allocation, and can move or swap Students before the Start date.
- Students registered after allocation are placed in a free AI-held Seat of a Class game that has not started, or a new Class game.

#### FR-21: Student choice (optional)
A Lecturer can instead let Students choose a Class game and a free Seat.
- A Student can hold only one Seat in one Class game per Class session.
- At the Start date, Students without a Seat are allocated at random.

#### FR-22: Class games open at the start date
From the Start date, every Student sees their Class game, Role and the other Seats (Students' names or "AI player").
- The Class game starts when the first Student in it opens it and presses start; from then on the inactivity rules apply (FR-36).
- The Lecturer can start any Class game, or all at once.

### 4.5 Gameplay

**Description:** All four Seats order in the same Week, and the Week advances when every Seat has ordered; AI players order at once. The game shows clearly whom it waits for. A Class game can run in one sitting in a Lab hour or stretch over several days. The playing screen is portrait-first: one Seat's facility, goods flowing down and orders flowing up, one number to enter. Realizes UJ-4.

#### FR-23: Weekly state shown to a Seat
A Student sees, for their own Seat: current inventory or backlog, incoming order this Week, incoming delivery this Week, the contents of their supply line, their own Order history, their running Total cost and the current Week number.
- The Student does not see other Seats' inventory, backlog or Orders during the Class game, except what the Lecturer has switched on in Information visibility (FR-83).
- On a 360-pixel-wide screen, all of this plus the Order input is visible without horizontal scrolling.

#### FR-24: Place an order
A Student can enter one Order per Week as a whole number from 0 to a maximum set in Game settings, and confirm it.
- Invalid input is rejected inline before submission.
- After confirmation the Order cannot be changed.

#### FR-25: Who the game waits for
Every Student in a Class game sees which Seats have ordered this Week and which the game is waiting for, by Role and name or "AI player", and how long it has waited. Realizes UJ-4.
- The Student whose Order is missing sees that the game waits for them, on the Class game screen and on their home screen.

#### FR-26: Week advance
When every Seat has placed its Order, the system advances the Week following the game rules (receive delivery, fill orders and backlog, ship, pass Orders upstream, charge costs).
- The new Week is shown to all connected Students within 2 seconds of the last Order, excluding AI player thinking time.
- Each Week's state is stored before it is shown; a reload or device switch resumes at the same Week with nothing lost.

#### FR-27: Notification when it is your turn
A Student gets an email when their Class game has been waiting for their Order for a set time. `[ASSUMPTION: after 2 hours, then again 4 hours before Takeover]`

#### FR-28: Game end
A Class game ends after the last Week in Game settings, or at the Play deadline (FR-38).
- On end, every Student in the Class game sees the final Total cost per Seat and is led to the Debrief (FR-41).

#### FR-29: Correct bookkeeping
The game arithmetic is correct by construction: inventory and backlog are never both positive for a Seat, units are conserved across the chain, and costs equal the rates times units.
- An automated check over every finished Game confirms conservation of units and cost totals; any violation is logged as an error.

### 4.6 AI players

**Description:** AI players are the product's first differentiator and the first thing built. LLM players are the default; Rule-based players are the Lecturer's choice when comparable, cheap or fully reproducible results matter more than realism. An AI player sees only what a Student in that Seat would see and decides as a supply chain manager would, without knowing it plays a game. Its Orders must match a fixed response schema, a Play guard (FR-79) compares them with reference players week by week, and every decision is logged. A smart LLM player is acceptable: the game is a team game with no winners, and the aim of every player is the best Order given the information available. Students always know which Seats are AI. Realizes UJ-4, UJ-5.

#### FR-30: AI players fill seats
The system places an AI player in every empty Seat of a Class game at the Start date, in the three other Seats of a Replay, and in a Seat at Takeover.

#### FR-31: Same information as a human
An AI player receives only the information a Student in that Seat would see (FR-23): its own data and what arrives from its downstream and upstream neighbours. The game rules are part of the prompt sent when it is the AI player's turn.
- The prompt describes the situation of a supply chain manager. An AI player is not told that it plays a game, that there are four Seats, or that Weeks advance after all Seats have ordered.
- No AI player receives customer demand unless it holds the Retailer Seat, or any other Seat's private state, except what Information visibility shows a Student in that Seat (FR-83).
- No AI player receives any Student's name, email or other personal data; Seats are referred to by Role.

#### FR-32: Validated orders and fallback
Every request to an LLM player asks for a response in a specific JSON format and carries the JSON schema; the Order is checked against the schema and the game rules before it takes effect.
- A response that does not match the schema is retried, at most 5 times. When the retries are used up, the Rule-based player's Order is used for that Week, and the replacement is marked in the Decision log.
- An Order that is missing, not a whole number or outside the allowed range counts as a response that does not match. `[ASSUMPTION: range violations handled like schema failures]`
- An Order that arrives later than 8 seconds is replaced by the Rule-based player's Order. `[ASSUMPTION: 8-second limit; retries and the Effort setting (FR-78) may need a longer limit, to be set after the prototype, issue #8]`
- The fallback applies to that Week only; the LLM player is asked again the next Week. `[ASSUMPTION: Week only, not the rest of the Game; not yet confirmed]`
- LLM players operate with an order bound so a single Order cannot exceed a set multiple of recent incoming orders. `[ASSUMPTION: 2×, per the research guardrail; not yet revisited after the Play guard was decided]`

#### FR-33: Documented AI behaviour
Each AI player type has a short plain-language description of how it decides, visible to Lecturers.
- The Rule-based player follows a documented anchoring-and-adjustment rule with published parameters.
- The LLM player's description states that its behaviour varies between runs.
- The description states that the LLM player is not told it is playing a game and may play better than a typical Student.

#### FR-34: Disclosure of AI players
Every AI player is labelled as AI wherever Seats are shown to Students, from the first moment the Student sees the Game.
- A Seat that has been taken over shows that it is now played by an AI player.
- A Seat whose LLM player has been switched to a Rule-based player by the Play guard (FR-79) shows this too.
- AI-generated text (Debrief narration, Debrief quiz explanations, Adapted items, AI assessment) is marked as AI-generated.

#### FR-78: Effort setting
A Lecturer who has chosen LLM players can set an Effort level for the Class session, which sets how much the model thinks before it answers.
- The Effort level applies to every LLM player in the Class session's Class games and Replays, and is stored with the Class session and in the Decision log.
- The default Effort level and the effect of each level on speed and cost are set after the prototype. `[ASSUMPTION: levels and default decided by prototype testing, issues #8, #9]`
- The prompt is calibrated by testing before launch, so that LLM players play sensibly at each offered Effort level.

#### FR-79: Play guard
The system compares every Order from an LLM player with two reference Orders computed for the same Week and the same information, and switches the Seat to a Rule-based player when the LLM player's Orders over time fall outside an accepted band.
- The lower reference is the Rule-based player (FR-33), standing for average sensible play. The upper reference is a near-optimal player computed by the system, which may use information the LLM player never sees.
- The comparison is made on weekly Orders, not on chain Total cost, because an LLM player does not see the whole chain.
- The band: in at least 95% of Weeks the LLM player's Order is within average sensible play, not nonsense; and its Orders are never closer to the near-optimal reference than a set margin of 5%. `[ASSUMPTION: the founder's wording is read as two limits; the distance measure, the number of Weeks compared and the confidence level are set in prototype testing, issues #9, #11]`
- A Seat the guard has switched stays Rule-based for the rest of the Game, is marked in the Decision log and shown to Students (FR-34). `[ASSUMPTION: switch is permanent for the Game; not yet confirmed]`
- The guard also applies when the Lecturer has changed the Game settings, and the Rule-based reference is computed for the settings in use. Founder decision 2026-11-05.
- The band is calibrated on Classic settings and the default Replay scenario. Under other settings, a large deviation from sensible play still switches the Seat. `[ASSUMPTION: what counts as large is set in prototype testing; the 5% limit is not applied on uncalibrated settings]`
- The guard applies to a Seat's LLM player only; it does not judge Students.

### 4.7 Inactivity, Takeover and deadlines

**Description:** The system measures activity. A Seat that leaves its Order open longer than the Inactivity limit is taken over by an AI player automatically, so no Class game waits more than about a day for one person. The Lecturer can also insert an AI player by hand. At the Play deadline, AI players finish any unfinished Class game. Realizes UJ-4, UJ-7.

#### FR-35: Activity tracking
The system records, per Seat, when each Week opened for it and when the Student ordered.

#### FR-36: Automatic takeover
When a Student has not ordered within the Inactivity limit after the Week opened for their Seat, an AI player takes over the Seat. Realizes UJ-4.
- The Lecturer sets the Inactivity limit per Class session; default 24 hours.
- The Student, the other Students in the Class game and the Lecturer overview are notified at Takeover.
- The Inactivity limit does not apply before the first Order in a Class game. `[ASSUMPTION: the clock starts once someone has started the game]`

#### FR-37: Manual takeover and reclaim
A Lecturer or Assistant lecturer can trigger Takeover of any Seat at any time. A Student whose Seat was taken over can reclaim it at the start of any later Week. `[ASSUMPTION: reclaim allowed]`
- Weeks played by the AI player stay marked as AI Weeks in the Decision log and Game insight.

#### FR-38: Play deadline playout
At the Play deadline, every unfinished Class game is played to its last Week, with AI players in all Seats. `[ASSUMPTION: playout rather than stopping the game]`
- Students in those Class games see that their game ended at the deadline and are led to the Debrief.
- No Class game remains unfinished after the Play deadline (SM-4).

### 4.8 Lecturer overview, Lab hours and Messages

**Description:** One screen shows every Class game in a Class session and what needs attention. The Lecturer and Assistant lecturers can message the whole Class session, one Class game, or one Student. Realizes UJ-7.

#### FR-39: Lecturer overview
A Lecturer or Assistant lecturer can see all Class games in a Class session with: current Week, status (not started, running, waiting, finished), whom each game waits for and for how long, each Seat's occupant (Student or AI player, Takeover marked) and running chain Total cost.
- Class games approaching Takeover are highlighted.
- The view updates without reload within 5 seconds of a change.
- The overview shows the Class session funnel: registered, Class game finished, Debrief done, Debrief quiz passed, Replay done, Individual test submitted, AI assessment ready.

#### FR-40: Send messages
A Lecturer or Assistant lecturer can send a Message to all Students in a Class session, to the Students of one Class game, or to one Student.
- The Message appears in the product and is sent by email.
- Students cannot reply in the product in v1. `[NON-GOAL for MVP: communication between players is planned for v2]`

### 4.9 Debrief and Debrief quiz

**Description:** When a Class game ends, the group goes through the Debrief together. Each Student explains in the Debrief what happened, and afterwards takes the Debrief quiz until every answer is right. All numbers in the Debrief come from the Decision log; the LLM only narrates and asks. The Debrief follows a proven sequence: how it felt, what happened, why the structure produced it, and what each Student's own Orders did. The Debrief and the Debrief quiz are formative and count toward nothing. Realizes UJ-5.

#### FR-41: Explanation in the Debrief
Early in the Debrief, before customer demand is revealed, each Student writes an Explanation of why their supply chain behaved as it did and what role their own Orders played. `[ASSUMPTION: the step comes before the reveal, so the Explanation still works as the before-measure in §9.1]`
- The Debrief does not move on for a Student until their Explanation is saved.
- In a Group debrief each Student writes on their own device and does not see the others' Explanations.
- The Explanation is stored unchanged and shown later in Game insight and in the Student report.

#### FR-42: Debrief availability
The Debrief becomes available when the Student's Class game has ended, and must be done before the Debrief deadline.
- `[ASSUMPTION: the Lecturer can hold all Debriefs until every Class game has ended, so the Demand pattern is not revealed to Students still playing]`

#### FR-43: Group debrief
With Group debrief, any Student of a Class game can open a shared Debrief for the Students of that Class game; the others are notified and can join. Realizes UJ-5.
- All joined Students see the same Debrief step at the same time, on their own devices or on one shared screen; each sees their own moments as well as the shared charts.
- A Student who has not joined a Group debrief by 48 hours before the Debrief deadline is offered a Personal debrief. `[ASSUMPTION: fallback rule]`
- A Class game with one Student always uses Personal debrief.

#### FR-44: Debrief content
The Debrief shows, for the Class game:
- the customer demand series, revealed;
- Orders, inventory and backlog per Role over the Weeks, in one chart, with a text alternative;
- how much Orders amplified from Retailer to Factory;
- for each Student, at least three specific moments from their own Seat: the Week, what they saw, what they ordered, and what it caused later; `[ASSUMPTION: moments chosen by rules over the Decision log]`
- what the neighbouring Seats saw at those moments;
- each Student's Explanation next to what the data shows (shown only to that Student in a Group debrief).
- Every number shown matches the Decision log exactly; narration that cites numbers not in the computed facts is rejected.
- The share of the cost caused by AI players' Orders is shown, so no Student's own share is overstated.

#### FR-45: Guided questions and follow-up
The Debrief asks reflection questions in sequence (feelings, then evidence, then structure) and lets Students ask follow-up questions about their Game. `[ASSUMPTION: structured walkthrough with bounded follow-up, not open chat]`
- Follow-up answers stay within the Game and Beer Game concepts; off-topic requests are declined.

#### FR-46: Debrief quiz
After the Debrief each Student takes the Debrief quiz individually and must answer every question correctly to continue. Realizes UJ-5.
- After each attempt the Student sees which answers were wrong and an explanation of why.
- The Student can retry without limit until the Debrief deadline. `[ASSUMPTION: unlimited retries; questions may be reshuffled]`
- The Debrief quiz result counts toward nothing; the number of attempts is visible to the Lecturer.

#### FR-47: Debrief summary
At the end of the Debrief, the system stores a short summary per Student: key moments, answers to reflection questions, Debrief quiz attempts and completion time.
- Lecturers and Assistant lecturers can read every summary.

### 4.10 Replay

**Description:** After passing the Debrief quiz, each Student plays one Replay alone against three AI players under harder conditions, so the Student meets the same structure without being able to rely on memory. The Replay ends with short feedback. Realizes UJ-5.

#### FR-48: Start the replay
A Student who has passed the Debrief quiz can start the Replay at any time before the Debrief deadline.
- The Student plays the same Role as in the Class game. `[ASSUMPTION: same Role]`
- Three AI players in the Class session's AI mode take the other Seats.
- The Replay can be paused and resumed on any device; AI players order at once, so there is no waiting.

#### FR-49: Replay scenario
The Replay uses a Replay scenario that differs from the Class game and is harder, through starting conditions (for example starting with backlog or low inventory), delays, Information visibility or Demand pattern (for example a larger or later step, or random demand).
- Default: the Class game's Demand pattern with larger variance, meaning random demand drawn from a discrete uniform distribution around the Class game's mean in each Week (mean 4, then 8 from Week 5) with a spread of 2, so each Week's demand is the mean minus 2 to plus 2. The average demand stays the same as in the Class game, so Total cost can be compared. Founder decision 2026-11-05: larger variance in demand; distribution chosen by the product team. `[ASSUMPTION: spread of 2]`
- The Lecturer can set every Game setting freely for the Replay scenario, starting from the Class session's settings. Founder decision 2026-11-05: the Lecturer configures all parameters as they wish.
- The Lecturer can accept the default or change any setting.
- Every Replay uses a fresh demand seed per Student, stored in the Decision log, so a Student cannot rely on remembering the Class game's demand.
- The end of the Replay and its demand stay hidden while playing (as FR-14).

#### FR-50: Replay feedback
At the end of the Replay the Student sees their Total cost, a chart of the run, a comparison with their Class game, and one or two specific observations about their own Orders, computed from the Decision log.
- Every number matches the Decision log.
- The Student is asked one optional question: would you have wanted to play another round? (SM-10)

### 4.11 Individual test

**Description:** Each Student shows what they learned in an individual test after the Replay: multiple-choice questions, Interactive items and long answers that require argument, some of them about the Student's own Class game and Replay. The test asks for what remembering the game cannot give: a quantity, a consistent set of graphs, or an explanation of the mechanism. It is not supervised; Interactive items and Adapted items are there to make it harder to answer with outside AI tools. The product provides the question set with Item weights. The test produces no grade in v1. Realizes UJ-6.

#### FR-51: Test availability
A Student can open the Individual test once they have completed the Replay, until the Test deadline, by default 7 days after the Debrief deadline (FR-18).
- By default the Student can close the test, return and work as much as they want until the Test deadline; answers are saved automatically and the Student submits once.
- A Lecturer can instead require one sitting with a time limit.
- `[ASSUMPTION: saved answers not yet submitted are submitted automatically at the Test deadline; no retakes]`

#### FR-52: Question set and item weights
The product provides a Norwegian question set for the Individual test with an Item weight for each question, covering stocks and flows, delays and the supply line, demand amplification and its causes, and the Student's own decisions.
- Core items include multiple-choice questions scored by answer key, Interactive items (FR-80) and long-answer questions.
- Multiple-choice questions cover definitions and causes, with wrong options built from known misperceptions, including a cause unrelated to the chain.
- Long-answer questions ask the Student to explain the behaviour from the structure of the chain (delay, supply line, own ordering rule), not from what other players did.
- A Lecturer can review the question set before the Start date, exclude questions and change Item weights; weights always sum to 100%.

#### FR-53: Adapted items
The Individual test includes Adapted items generated from the Student's own Class game and Replay, each referring to a specific Week, Order or outcome.
- Adapted items follow the same question templates for every Student, filled with facts from the Student's own games, so difficulty varies as little as possible.
- Every fact an Adapted item cites matches the Decision log.
- Adapted items carry a fixed total Item weight set by the Lecturer, default 30%, so scores stay comparable between Students with different games.
- A Lecturer can preview Adapted items for any Student before the Test opens for them.

#### FR-80: Interactive items
The Individual test includes Interactive items where the Student answers in an interactive graph, table or diagram, for example by drawing a stock after a jump in demand, filling in a table of weekly stocks, or connecting the causes in a diagram.
- At least one Interactive item uses a business other than the beer chain, so it tests reasoning rather than recall of the game.
- Interactive items are scored on quantities and consistency (units added equal units missing; the stock agrees with its flows), never on whether the answer looks like oscillation. `[ASSUMPTION: scored by computed rules, not by the LLM]`
- Each Interactive item asks for one output.
- Every Interactive item can be answered by keyboard and screen reader, for example through a table alternative (NFR-6).
- `[ASSUMPTION: works on a phone from 360 pixels wide, as FR-73 requires, but best on a laptop]`

#### FR-81: Scoring guide
The AI assessment scores long-answer and Adapted items against one Scoring guide, which states for each question or question template what is asked for, how the parts weigh, and what strong and weak answers look like.
- The default guide is written during implementation and approved by the founder before the first Class session.
- A Lecturer can edit the guide for a Class session. `[ASSUMPTION: edits are possible until the Test deadline; the version in force at the deadline scores the whole Class session, as the model is fixed by FR-68]`
- An edited guide is checked only if a Control test is run with it (FR-82).

### 4.12 AI assessment and reports

**Description:** After the Test deadline, the AI gives each Student a score and written feedback on the Individual test. The AI assessment is formative: it counts toward nothing, and no human has to review it. Students and Lecturers can download a PDF report of the games, the Debrief and the test. All formal grading is out of v1 (§8.3); if a course grades this work, it does so outside the product under its own rules. Realizes UJ-8.

#### FR-54: AI assessment
After the Test deadline, the system produces an AI assessment for each submitted Individual test: the score on answer-key and Interactive items, one overall score with written feedback for each long-answer and Adapted item following the Scoring guide (FR-81), and a total score using the Item weights. `[ASSUMPTION: produced after the Test deadline so feedback does not leak to Students who have not taken the test]`
- Each piece of feedback quotes the part of the Student's answer it refers to.
- Every fact about the Student's games matches the Decision log.
- The AI assessment contains no pass/fail result, and no letter unless the Indicative letter is turned on (FR-56).
- `[NOTE FOR PM]` The AI assessment stays outside the EU AI Act's high-risk category only while it is formative; see §6.2.

#### FR-55: Seeing the AI assessment
A Student gets an email when the AI assessment is ready and can read it in the product; Lecturers and Assistant lecturers can read it for every Student in their Classes.
- Every view states that the AI assessment is AI-generated, can be wrong, counts toward nothing and is not a grade.

#### FR-56: Indicative letter
A Lecturer can turn on the Indicative letter for a whole Class session; where it is off, each Student can turn it on for their own AI assessment.
- The letter is derived from the total score by thresholds with defaults the Lecturer can change before the Individual test opens. `[ASSUMPTION: default thresholds; A–F only]`
- It is labelled as an AI-generated indication that is not a grade, wherever it is shown.
- A letter a Student turned on only for themselves is not shown to Lecturers. `[ASSUMPTION]`
- It never appears in the Completion export and never affects the Completion status.

#### FR-57: Student downloads the report
A Student can download their Student report as a PDF once the Test deadline has passed, and until the data is deleted (FR-77), for example for approval or to upload to another application. Realizes UJ-8.
- A single Student report is ready within 30 seconds. `[ASSUMPTION: placeholder]`
- Students are told before the deletion date that they should download their report.

#### FR-58: Report content
The Student report holds, in Norwegian:
- the Student's name, the Class and Class session, the dates, and the time the report was generated;
- the Completion status, and whether an obligatory requirement is met;
- the Class game: Role, Weeks played, final Total cost, a week-by-week table for the Student's own Seat, and a chart of Orders, inventory and backlog for all four Roles plus customer demand, with AI players and Takeover Weeks marked;
- the Explanation, the Debrief summary and the number of Debrief quiz attempts;
- the Replay: scenario, Total cost, and a chart;
- the Individual test: questions, the Student's answers including Interactive items as images with table alternatives, and the scores on answer-key and Interactive items;
- if the person downloading adds it, the AI assessment in its own section, labelled as AI-generated and not a grade.

**Consequences (testable):**
- The AI assessment section is left out by default, because the report is meant for approval and for other applications. `[ASSUMPTION: default off, can be added]`
- Other Students appear by Role only, never by name, and their Explanations are never included.
- Steps not done are marked as not done.
- Every report states that it documents the Student's work and is not a grade.

#### FR-59: Lecturer downloads reports
A Lecturer or Assistant lecturer can download the Student report of any Student at any time, or all Student reports in a Class session as one ZIP file.
- A ZIP file for 250 Students is ready within 10 minutes, and the Lecturer is notified. `[ASSUMPTION: placeholder]`

#### FR-60: Completion export
A Lecturer can export the Completion status of a Class session as a CSV or Excel file: Student name, email, the date each step was done, the share of Class game Weeks the Student ordered in, and whether an obligatory requirement is met (FR-17).
- The file holds no AI scores or AI feedback, so a completion requirement does not rest on an AI judgement.

#### FR-61: AI assessment can be switched off
A Lecturer can turn off the AI assessment for a Class session, for example if the Institution's data protection officer requires it.
- Answer-key and Interactive items are still scored automatically, and the Student report is still available.

#### FR-82: Control test
The Admin can set up a Control test: a separate run of the Individual test taken by test students, used to check the AI assessment against human scoring before real Students depend on it.
- Test students are marked as such. Their games, answers and scores never appear in a Class session's overview, Class report, Cross-class statistics or Completion export.
- A human scores each long-answer and Adapted item with the Scoring guide without seeing the AI's score. The product then shows both scores side by side, with exact agreement, agreement within one step and any systematic offset.
- A Control test can be run with the default Scoring guide or with a Lecturer's edited one, so an edited guide can be checked too. `[ASSUMPTION: the Admin runs it for a Lecturer on request in v1]`
- `[ASSUMPTION: test students are people outside the course; each plays a Class game and Replay, so Adapted items rest on a real Decision log]`

### 4.13 Insight, Class reports and Cross-class statistics

**Description:** The Lecturer can see everything that happened, from one Order to the whole class, and compare Class sessions over years. Realizes UJ-7, UJ-9.

#### FR-62: Game insight
A Lecturer or Assistant lecturer can open any Game (Class game or Replay) and see, per Week and per Seat: incoming order, incoming delivery, inventory, backlog, Order and cost; who played the Seat (Student or AI player, Takeover marked); and whether an LLM player's Order was replaced by the fallback.
- Charts of Orders, inventory and backlog for all four Roles plus customer demand.
- Links to the Students' Explanations and Debrief summaries.

#### FR-63: Student page for lecturers
A Lecturer can open one Student and see their Class game, Explanation, Debrief summary, Debrief quiz attempts, Replays, Individual test and AI assessment on one page, with a link to the Student report.

#### FR-64: Class report
A Lecturer can see a Class report for a Class session: the funnel (FR-39); distribution of Total cost per Role; order amplification per Role; the most common mistakes detected across Class games (for example ignoring the supply line); results per Individual test question; distribution of AI assessment scores; the share of Seats played by AI players.
- The Class report updates as Students progress.

#### FR-65: Cross-class statistics
A Lecturer can compare the Class sessions they have access to on the Class report measures, filtered by Game settings and AI mode.
- Class sessions with different Game settings or AI mode are labelled as such in every comparison.
- Comparisons across Institutions show only anonymised aggregates over groups of at least 10 Students and are visible only to the Admin in v1. `[ASSUMPTION: threshold of 10]`

### 4.14 Rerun

#### FR-66: New class session from an earlier one
A Lecturer can create a new Class session in the same or another Class by copying an earlier Class session's settings (Game settings, AI mode, Debrief mode, Replay scenario, question set and Item weights, Scoring guide, Inactivity limit), then adjust them. Realizes UJ-9.
- Dates, Lab hours and Roster are not copied.

### 4.15 Decision log and AI operations

**Description:** The evidence for issues #6, #8, #9, #10 and #11 becomes a by-product of normal use.

#### FR-67: Decision log
The system stores every Order in every Game with: Game, Week, Seat, Role, the state the Seat saw, the Order, and whether a Student or an AI player placed it.
- For LLM players it also stores model identifier (exact version), provider, prompt version, Effort level, seed and temperature where supported, tokens, cost, response time, the number of retries, whether the fallback replaced the Order, the two reference Orders of the Play guard (FR-79), and the Week a Seat was switched.

#### FR-68: Model pinned per class session
All LLM players in a Class session and its Replays use the same model version and prompt version for the whole Class session.
- If a provider fails and the fallback is used, the Class session is marked as mixed in reports.
- The Admin can freeze the model for chosen Class sessions so no model change happens during a learning study.

#### FR-69: AI spending controls
The Admin can see AI cost per Class session, per Game and per day, and set a cost limit per Class session.
- When a Class session reaches its cost limit, its LLM players switch to Rule-based players for the rest of the Class session, and the Lecturer is notified.
- The Admin gets an alert when daily AI spend exceeds a set amount.

#### FR-70: Plausibility rating
After the Class game, each Student is asked one optional question about how believable the AI players' ordering felt (five-point scale).
- Results are shown per AI mode in the Class report and Cross-class statistics (SM-3).

#### FR-71: Anonymised export for evaluation
The Admin can export the Decision log, Explanations and Individual test answers of chosen Class sessions in anonymised form (Students replaced by stable pseudonyms) for evaluating AI players and learning outcomes, where the Institution has agreed.

### 4.16 Language and devices

#### FR-72: Norwegian interface
All screens, emails, Debriefs, Debrief quiz, Individual test, AI assessments and Student reports are in Norwegian (bokmål). `[ASSUMPTION: bokmål only in v1]`

#### FR-73: Mobile-first, classroom laptop equal
Every Student flow (registration, Class game, Debrief, Debrief quiz, Replay, Individual test) works on a phone from 360 pixels wide and on a laptop browser.
- Long-answer questions in the Individual test are comfortable to write on a laptop; on a phone the Student is advised to use a larger screen. `[ASSUMPTION]`
- Lecturer overview and Game insight are designed for laptop first and remain usable on a tablet.

#### FR-74: Group debrief on one screen
A Group debrief can be shown on one shared screen (for example a laptop in a Lab hour), with each joined Student still answering on their own device.

### 4.17 Data rights

#### FR-75: Student data access
A Student can see all data the product stores about them: account and profile, Explanations, Debrief summaries, Individual test answers and AI assessments. The Student report covers most of it.

#### FR-76: Deletion on request
The Admin can delete a User and their personal data on the Institution's instruction; their Seats remain in Game data as anonymous Seats so other Students' Games stay intact.

#### FR-77: Retention
Student personal data in a Class session is deleted automatically a set period after the Test deadline, configurable per Institution. `[ASSUMPTION: default course end plus appeal period, e.g. 12 months]`

## 5. Cross-Cutting Non-Functional Requirements

- **NFR-1 Responsiveness.** A Week advances for connected Students within 2 seconds after the last Order (excluding AI player thinking time). Pages a Student uses during play load within 3 seconds on a 4G connection.
- **NFR-2 AI player latency.** 95% of LLM player Orders arrive within 8 seconds, retries included; slower Orders are replaced by fallback (FR-32). `[ASSUMPTION: placeholder pending prototype, issue #8; the limit may differ per Effort level (FR-78) and the coaching question on acceptable waiting time is still open]`
- **NFR-3 Scale.** One Class session supports at least 400 Students (100 Class games); a full Lab hour with 250 Students playing at the same time works without degradation. The platform supports at least 5 such Class sessions at once. `[ASSUMPTION: launch scale]`
- **NFR-4 Reliability.** No Class game waits longer than the Inactivity limit for an absent Student, and none stalls because an AI provider fails. Availability during Lab hours is at least 99.5%. Game state is never lost once a Week has been shown.
- **NFR-5 Reconnection.** A Student who loses connection resumes at the current Week on any device without action from others.
- **NFR-6 Accessibility.** Student and Lecturer screens meet WCAG 2.1 AA. Charts have text or table alternatives. Student reports are tagged PDFs with table alternatives for charts. Role and status are never shown by colour alone. An accessibility statement and conformance report are available to Institutions.
- **NFR-7 Security.** Role-based access on every request (FR-5). Data encrypted in transit and at rest. Audit log for Admin actions. Student reports are generated only for a logged-in User allowed to see them, and download links expire.
- **NFR-8 Observability.** Per Class session the Admin can see error counts, fallback rate, AI response times and AI cost.
- **NFR-9 Correctness.** Game arithmetic is verified on every finished Game (FR-29). Every number the AI shows a Student or Lecturer is drawn from computed facts (FR-44, FR-50, FR-53).
- **NFR-10 Email delivery.** Invitations and notifications are sent from an authenticated domain; bounces are reported to the Lecturer (FR-8).

## 6. Constraints and Guardrails

### 6.1 Privacy and data protection

- The Institution is the data controller for Student data; beergame is the processor and signs a data processing agreement before any Institution's Students are invited, including the founder's own Institution for the pilot.
- No LLM provider receives names, emails, student numbers or free text that identifies a Student. Seats are identified by Role and pseudonymous IDs. Free-text answers sent for AI assessment and Debrief follow-up are filtered for names and emails first.
- LLM providers are used only under terms that exclude training on the data and keep no or minimal retention; they are listed as sub-processors. EU-region processing is preferred; providers processing in countries without an adequacy decision are not used (this excludes, for example, DeepSeek's own API).
- The product supplies a DPIA support pack (data flows, sub-processors, risks, mitigations) for each Institution; a DPIA is mandatory for evaluating learning in Norwegian higher education.
- Retention follows FR-77. Anonymised data may be kept for evaluation (FR-71).

### 6.2 AI regulation and examination law

- AI players, Debrief narration, Debrief quiz explanations and the AI assessment are disclosed as AI from first interaction, and AI-generated text is marked (EU AI Act Art. 50, applies in the EU from 2 August 2026).
- v1 has no formal grading. The Debrief, Debrief quiz, Replay feedback and AI assessment are formative and feed no grade in the product.
- The intended purpose of the AI assessment is formative feedback. The Commission's draft guidelines (May 2026; final version expected end of 2026) put formative feedback outside EU AI Act Annex III 3(b), but put a learning assistant whose reports inform the teacher's grades inside it, and human review does not change that. v1 therefore states the purpose in the product, the terms and every Student report; keeps AI scores out of the Completion export (FR-60); leaves the AI assessment out of the Student report by default (FR-58); and allows the AI assessment to be switched off (FR-61).
- An Obligatory class session (FR-17) rests on system events and answer-key scores only, because the regulatory research treats AI evaluation behind a pass/fail gate for exam eligibility as a grey zone to be handled as summative.
- `[NOTE FOR PM]` A course that grades or approves from the AI assessment could pull it into the high-risk category. The Indicative letter (FR-56) makes that more likely, since a letter reads as a grade; the research did not assess such a letter specifically. Check both against the final guidelines and with the Institution's data protection officer before launch.
- Formal assessment under the Universities Act (examiners appointed by the Institution, impartial assessment) stays outside the product in v1, under the Institution's own process.
- No emotion recognition from voice or other biometric data; no AI proctoring.
- Formal grading with an AI proposal, planned for v2, would likely be high-risk (obligations apply in the EU from 2 December 2027; Norwegian bill expected spring 2027). See addendum §V and §R.

### 6.3 Cost

- AI cost per Class game is at most USD 0.10 including provider fees; AI cost per Student per Class session (share of the Class game, Replay, Debrief, Debrief quiz, Adapted items, AI assessment) is at most USD 0.50. `[ASSUMPTION: envelope from the research's modelled cost; issue #8 must verify]`
- FR-69 enforces a per-Class session limit and falls back to Rule-based players rather than stopping play.

### 6.4 Content and intellectual property

- All game graphics, texts, Debrief content and test questions are original. Third-party classroom materials for the Beer Game may inform parameters but are not copied; at least one such licence forbids online hosting and redistribution.

## 7. Non-Goals (Explicit)

- Not an open consumer product: no public sign-up, free tier, individual subscriptions or in-app payment in v1.
- Not a general simulation platform: only the classic four-Role Beer Game in v1; no custom topologies or other games. The Lecturer does set the Game settings and the Replay scenario's settings freely (FR-12, FR-49).
- No Feide login, Canvas/LTI or other LMS integration in v1.
- No communication between players in v1, and no student-to-lecturer chat. (v2: Students replay in the same group with communication.)
- No formal grading of any kind in v1: no examiners, grades or appeals (planned for v2, §8.3). The AI assessment and its optional Indicative letter are never a grade.
- No AI proctoring, emotion inference or monitoring of Students outside the product.
- No native mobile apps.
- No language other than Norwegian in v1.
- No bit-exact reproducibility of LLM players; reproducibility comes from Rule-based players and the Decision log.
- No reinforcement-learning AI players in v1.

## 8. MVP Scope

### 8.1 In Scope

- Accounts by Invitation; roles Admin, Lecturer, Assistant lecturer, Student; Admin area (FR-1 to FR-5).
- Classes, Roster upload from Canvas export, Invitations with expiry and manual override, co-Lecturers, Assistant lecturers (FR-6 to FR-10).
- Class session setup with classic defaults, adjustable Game settings, Demand pattern, AI mode, Debrief mode, Obligatory class session, dates and Lab hours, Information visibility and capacity (FR-11 to FR-19, FR-83).
- Random allocation into Class games of up to four with random Roles, optional student choice (FR-20 to FR-22).
- Simultaneous-order gameplay with hidden end and a clear "waiting for" view (FR-23 to FR-29).
- LLM players by default, Rule-based players per Class session, schema-checked Orders with retries and fallback, disclosure, Effort setting, Play guard (FR-30 to FR-34, FR-78, FR-79).
- Automatic Takeover after the Inactivity limit, manual Takeover, Reclaim, Play deadline playout (FR-35 to FR-38).
- Lecturer overview and one-way Messages (FR-39, FR-40).
- Group and Personal debrief with the Explanation inside it, Debrief quiz (FR-41 to FR-47).
- One Replay with a harder Replay scenario (FR-48 to FR-50).
- Individual test with weighted Core, Interactive and Adapted items and one Scoring guide (FR-51 to FR-53, FR-80, FR-81).
- Non-counting AI assessment with optional Indicative letter, downloadable PDF Student reports, Completion export, Control test (FR-54 to FR-61, FR-82).
- Game insight, Class report, Cross-class statistics, rerun (FR-62 to FR-66).
- Decision log, model pinning, spending controls, plausibility rating, anonymised export (FR-67 to FR-71).
- Norwegian, mobile-first, data rights and retention (FR-72 to FR-77).

### 8.2 Out of Scope for MVP

- Feide and Canvas/LTI. `[NOTE FOR PM]` The research says these are the main ways into Norwegian higher education; revisit before the second paying Institution.
- Communication between players and group Replays (v2, founder-requested).
- English and other languages (v2).
- Information-sharing variant of the game (a classic second session; v2 candidate).
- Institution admin role (the Admin handles institutions in v1).
- Billing, licences and invoicing in the product.
- Lecturer-authored questions beyond excluding questions and changing Item weights.
- PDF export of the Class report.
- Voluntary extra Replays. `[NOTE FOR PM]` The founder removed them from v1 on 2026-11-05, so v1 tests one repetition, not many, and the brief's kill bar (median solo Replays above 3) cannot be measured. SM-10 collects a first signal for the v2 decision.

### 8.3 Planned for v2: formal grading

Founder decision, 2026-11-05: everything concerning formal grading moves to v2. The design narrated so far is kept in addendum §V and is not built in v1:

- Examiner role, with the course lecturer and an external examiner per Student, registered by the Lecturer.
- AI proposal of a grade, advisory only, reviewed by the Examiners.
- Independent proposed grades, a follow-up until the Examiners agree on one joint grade, and tracking of the statutory grading deadline.
- Grading scale (A–F or Pass/Fail) and thresholds for formal grades, set by the Lecturer.
- Release of grades with email notice, grade export, appeals and re-grading, and anonymous grading by candidate number.

## 9. Success Metrics

*All thresholds are placeholders until the pilot Class session; the founder sets the final values.*

**Primary**
- **SM-1 Second-round behaviour.** Share of Students whose Orders in the Replay take more account of the supply line and amplify demand less than in their Class game, computed from the Decision log and adjusted for the harder Replay scenario. Target: at least 60%. `[ASSUMPTION: measure and target set with the founder before the pilot]` Replaces the brief's kill bar, which needs voluntary Replays (§8.2). Validates FR-48 to FR-50.
- **SM-2 Explanation gain.** Share of Students whose long answers in the Individual test explain the mechanism (delays, supply line, own Orders), compared with the share whose Explanation early in the Debrief does, scored by the founder with one rubric on an anonymised export (FR-71), not by the AI assessment. Target: at least double, and at least 60% in the Individual test. `[ASSUMPTION: rubric and targets set with the founder before the pilot]` Validates FR-41, FR-44, FR-52.
- **SM-3 AI players fit for teaching.** (a) Share of LLM Orders replaced by fallback after the 5 retries (FR-32), and share of Seats switched by the Play guard (FR-79): both reported per Class session, no fixed limit in v1. `[ASSUMPTION: the earlier 2% bound is replaced by the retry rule; the founder may still want a limit]` (b) Run-to-run variation (coefficient of variation) of chain Total cost on fixed test games: about 10–15% with order bounds. `[ASSUMPTION: not yet discussed with the founder]` (c) Plausibility rating (FR-70): median at least 4 of 5. `[ASSUMPTION: not yet discussed with the founder]` The Play guard (FR-79) protects every Class session while it runs; there is no end-of-pilot rule that makes Rule-based players the default. Validates FR-30 to FR-34, FR-78, FR-79. Issues #8, #9, #11.

**Secondary**
- **SM-4 Completion.** 100% of Class games end by the Play deadline; at least 95% of registered Students submit the Individual test by the Test deadline. Validates FR-36 to FR-38.
- **SM-5 Setup time.** A Lecturer who has used the product once creates a Class session with defaults in under 10 minutes; uploading a Canvas export and sending Invitations takes under 5 minutes. Validates FR-7, FR-8, FR-11.
- **SM-6 AI cost.** At most USD 0.10 per Class game and USD 0.50 per Student per Class session. Validates FR-69.
- **SM-7 AI assessment quality.** In a Control test (FR-82) of at least 30 tests before the pilot, including Adapted items, scored by the founder alone with the Scoring guide, the AI's score for long answers is within one step of the guide's scale for at least 80%; no feedback cites a fact that contradicts the Decision log. The founder also reports exact agreement and any systematic offset. If this is not met, the AI assessment is switched off until it is. `[ASSUMPTION: 30 tests; 80% is provisional and confirmed after the first Control test, since no published benchmark exists; test students' answers resemble real Students' answers well enough]` Validates FR-54, FR-81, FR-82.
- **SM-8 First external Institution.** One paying Institution other than the founder's own, using a Class session end to end.
- **SM-9 Report use.** At least 50% of Students download their Student report, and a Lecturer can produce every report for a Class session without help. `[ASSUMPTION: placeholder]` Validates FR-57 to FR-59.
- **SM-10 Appetite for repetition.** Share of Students who answer yes to wanting another round (FR-50), reported separately for obligatory and non-obligatory Class sessions. No target in v1; it informs whether v2 adds voluntary Replays. Validates the repetition half of the bet.

**Counter-metrics (do not optimise)**
- **SM-C1 Total cost.** Lower Total cost in Replays is not learning; performance and understanding are known to dissociate. Counterbalances SM-1.
- **SM-C2 Average AI assessment score.** A generous AI pleases students and teaches nothing; rising scores are not evidence of learning. Counterbalances SM-7.
- **SM-C3 AI player skill.** A smart LLM player is acceptable and is not tuned down to imitate Students, but near-optimal play would remove the bullwhip the game exists to show. The Play guard (FR-79) keeps LLM play away from near-optimal. Counterbalances SM-3.
- **SM-C4 Debrief quiz attempts.** Fewer attempts is not better learning if questions get easier. Counterbalances SM-2.
- **SM-C5 Takeovers.** Lowering the Inactivity limit makes games finish faster but replaces Students with AI players. Counterbalances SM-4.
- **SM-C6 Completion under obligation.** An Obligatory class session raises completion without showing that the exercise is valuable. Counterbalances SM-4.

### 9.1 Learning measurement in the first Class session (issue #6)

The founder has no capacity for a split-group study in the first semester. The pilot collects evidence without changing the course design: every Student's Explanation (FR-41) is the before-measure; the long answers in the Individual test are the after-measure, both scored with the same rubric; behaviour in the Class game and the Replay is compared (SM-1); the model is frozen for the Class session (FR-68). A later Class session can compare groups by varying the Debrief, using the same instruments. `[ASSUMPTION: same rubric scores both texts; Explanations are scored blind to whether they are before or after]`

## 10. Rollout

- **Pilot:** one Class session in the founder's own course (about 250 Students). Preconditions: data processing agreement with the founder's Institution; DPIA support pack; prototype evidence for the retry rule (FR-32), the Play guard (FR-79) and SM-6 on test games (issues #8, #20); one rehearsal Class session with test users; one Control test (FR-82). If the Control test does not meet SM-7, the pilot runs with the AI assessment switched off (FR-61).
- **Launch to further Institutions:** after SM-7 is met and the pilot meets SM-4 and SM-5, and the founder accepts the SM-3 results; WCAG 2.1 AA conformance report available; licences kept under the Norwegian procurement threshold (NOK 500,000 excluding VAT) where possible.

## 11. Risks

- **AI players do not behave like human players** (too erratic or too good). Mitigation: schema-checked Orders with retries and fallback (FR-32), order bounds, the Play guard (FR-79), Rule-based mode (FR-15).
- **The AI assessment is used as a grade anyway**, which could make it regulated high-risk AI. Mitigation: the Indicative letter is off by default, labels in the product and in every Student report, reports without the AI assessment section by default (FR-58), Completion export without AI scores (FR-60), switch-off (FR-61).
- **The AI assessment is wrong and no human has checked it.** Mitigation: quotes from the answer, facts checked against the Decision log, Control test (FR-82, SM-7), plain statement that it can be wrong and counts toward nothing, switch-off (FR-61).
- **Without a grade, Students skip the steps.** The flow only works if students finish it. Mitigation: the Lecturer can mark the Class session as obligatory (FR-17).
- **Groups never meet for the Group debrief.** Mitigation: fallback to Personal debrief (FR-43).
- **Debriefs reveal the Demand pattern to Students still playing.** Mitigation: Lecturer option to hold Debriefs (FR-42).
- **Students use outside AI tools in the Individual test.** This weakens the learning evidence (SM-2, SM-7) more than it threatens fairness, now that the test does not count toward a grade. The test is unsupervised and open for days, and studies of unsupervised written exams show AI answers often go undetected. v1 relies on Interactive items (FR-80) and Adapted items tied to the Student's own games. No evidence shows that Interactive items stop these tools, which can read screenshots, so the founder tries a general AI on the test before the pilot (open question 6).
- **Many Takeovers hollow out the Class game.** Mitigation: Lecturer sees Takeovers in the overview; Inactivity limit adjustable; Reclaim.
- **AI cost runs away with long reasoning or retries.** Mitigation: per-Class session limit with fallback (FR-69).

## 12. Open Questions

1. Product name.
2. Prices for Institutions and whether Students ever pay directly.
3. v2: compliance path for formal grading with an AI proposal: meet high-risk obligations, or have Examiners grade without it? When does Norwegian law apply?
4. Does the final Commission guidance keep the AI assessment and the Student report outside Annex III 3(b)? Check when it is published (expected end of 2026).
5. Is a spread of 2 around the Class game's mean the right default demand variance for the Replay (FR-49)? Check against the first pilot's Replay results.
6. How well does a general AI tool do on the unsupervised Individual test, Interactive items included, and how far can SM-2 be trusted as a result? Answered by trying one on the test before the pilot.
7. How must the obligatory requirement be described in the course plan, and does it count as an exam-eligibility requirement under the Universities Act § 11-4? The Lecturer and the Institution decide.
8. Which other applications will receive the Student report, and must they be able to verify that it is authentic?
9. Do lecturers in other courses need identical results across Class sessions (interviews, issue #7)?
10. Which LLM and provider meet the privacy constraints in §6.1 and the cost in §6.3 (issues #8, #9)?
11. Should the Admin role later split into platform admin and institution admin?
12. AI player quality (coaching topic 2, left open): when a Seat falls back after 5 failed retries, is it for that Week only or for the rest of the Game; how long may a Student wait for an AI player (NFR-2, with retries and Effort); do retries and higher Effort stay within the cost limit in §6.3; how much run-to-run variation is acceptable (SM-3b); how is plausibility measured (SM-3c); is the decision on LLM players taken after a prototype or after the pilot? (issues #8, #9, #11)
13. Play guard (FR-79): which reference players are used, how the 95% and 5% limits are measured on weekly Orders, over how many Weeks, what counts as a large deviation under changed Game settings, and whether the switch is permanent for the Game.

## 13. Assumptions Index

- FR-4 — Login by email and password.
- FR-5 — Assistant lecturers see AI assessments.
- FR-7 — Canvas export accepted without editing; format to be confirmed.
- FR-10 — Lecturers can invite Assistant lecturers.
- FR-12 — Parameter ranges; capacity design.
- FR-83 — Customer-demand visibility option.
- FR-17 — Share of Weeks required, default 80%; no approval action in the product.
- FR-18 — 24-hour deadline reminders; the 7-day Test window counts from the Debrief deadline.
- FR-19 — Lab hours emailed on creation.
- FR-27 — Turn notifications after 2 hours and 4 hours before Takeover.
- FR-32 — 8-second limit for LLM Orders; order bound 2×; range violations handled like schema failures; fallback for that Week only.
- FR-78 — Effort levels and default set after prototype testing.
- FR-79 — Play guard limits (95%, 5%) read from the founder's wording; permanent switch for the Game; what counts as large under changed settings.
- SM-3 — 2% bound dropped, variation and plausibility targets not yet confirmed.
- FR-36 — Inactivity clock starts once the game has started.
- FR-37 — Reclaim allowed.
- FR-38 — Unfinished Class games played out by AI at the Play deadline.
- FR-41 — Explanation comes before the demand reveal.
- FR-42 — Lecturer can hold Debriefs until all Class games end.
- FR-43 — Fallback from Group debrief to Personal debrief 48 hours before the deadline.
- FR-44 — Debrief moments chosen by rules over the Decision log.
- FR-45 — Structured Debrief with bounded follow-up.
- FR-46 — Unlimited Debrief quiz retries.
- FR-48 — Replay in the same Role.
- FR-49 — Default Replay demand spread of 2.
- FR-51 — Unsubmitted answers submitted automatically at the Test deadline; no retakes.
- FR-54 — AI assessment produced after the Test deadline.
- FR-56 — Default letter thresholds, A–F only; a letter a Student turned on is hidden from Lecturers.
- FR-57 — A single Student report ready within 30 seconds.
- FR-58 — AI assessment section off by default, can be added.
- FR-59 — ZIP file for 250 Students ready within 10 minutes.
- FR-65 — Anonymisation threshold of 10; cross-Institution view for the Admin only.
- FR-72 — Bokmål only.
- FR-73 — Long answers best on a laptop.
- FR-77 — Retention default, e.g. 12 months.
- FR-80 — Interactive items scored by computed rules; best on a laptop.
- FR-81 — Lecturer can edit the Scoring guide until the Test deadline; one version scores the whole Class session.
- FR-82 — Admin runs Control tests in v1; test students are people outside the course who play a Class game and Replay.
- §2.2 — Higher education only.
- NFR-2 — 8-second latency placeholder.
- NFR-3 — 400 Students per Class session, 5 concurrent Class sessions.
- §6.3 — Per-Student cost envelope of USD 0.50.
- §9 SM-1 — Measure and target for second-round behaviour.
- §9 SM-2, §9.1 — Rubric, targets and blind scoring.
- §9 SM-7 — 30 tests, provisional threshold, test students' answers resemble real ones.
- §9 SM-9 — Report use placeholder.
