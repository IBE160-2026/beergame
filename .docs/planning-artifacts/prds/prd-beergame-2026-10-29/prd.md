---
title: "PRD: beergame"
status: final
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

It builds on the final product brief and does not repeat its market case. Every domain noun is defined once in §3 Glossary and used verbatim afterwards. §4 holds the features, with globally numbered functional requirements (FR-1 to FR-89) and their testable consequences. Inferences the founder has not confirmed carry an inline `[ASSUMPTION]` tag and are indexed in §13. Technical detail, cost tables, regulatory sources and rejected alternatives live in `addendum.md` in this folder.

## 1. Vision

The Beer Game has taught the bullwhip effect for sixty years, and at least one published account says it is disappearing from classrooms: running it is slow and fragile, and few students can clearly explain how their own orders produced the chaos they just lived through. `[ASSUMPTION: one account is a signal, not a trend; market size is unknown]` beergame runs the whole exercise for the Lecturer: Invitations, groups, play, Debrief, a second round, an Individual test with non-counting AI feedback and a PDF report of it all. AI players step into every Seat a Student leaves empty.

For the Student, the game stops being a single event. After the Class game and the Group debrief, each Student plays again alone against AI players under harder conditions. The Student then shows in an Individual test, in their own words and with arguments, what they understood, and gets feedback from the AI. For the Lecturer, the course stops being refereeing: every Class game is visible on one screen, a group can pause without losing its game, one missing Student cannot hold the others back, and each Student's work arrives as a report.

The bet, carried over from the brief: **the product is working AI players plus the explanation.** AI players that behave well enough to teach with, and a Debrief that explains each Student's own decisions, are the differentiators. Bot-filled seats alone are not; competitors already offer them for free. Whether repetition plus explanation teaches more than one good Class session is untested, and the first Class session in the founder's own course is where that evidence starts. v1 tests the explanation and one repetition. It has no progression layer, so it cannot show whether many repetitions teach more.

## 2. Target Users

### 2.1 Jobs To Be Done

- **Lecturer** (teaches supply chain, logistics or operations; courses of about 250 students): run the Beer Game midway through the course without spending weeks as a referee; know that every game finishes; make the exercise obligatory when the course needs it; get documentation per student for approval in the course's own systems; follow how the class progresses; rerun the exercise next year and compare.
- **Assistant lecturer**: help the lecturer monitor games, staff lab hours and message students in the Classes they are attached to.
- **Student**: get through the exercise on a phone, a tablet or a laptop, mostly on the group's own schedule; understand why the supply chain oscillated and what their own orders had to do with it; get honest feedback on the Individual test and keep a report of the work.
- **Admin** (platform operator; the founder in the pilot): give the right people lecturer access and keep users and AI spending under control.
- **Institution** (payer, not a user in v1): the exercise lands, the data handling passes the data protection officer's review, there is no IT burden, and someone is accountable when it breaks.

### 2.2 Non-Users (v1)

- Students who are not invited by a Lecturer: there is no public sign-up, free tier or individual subscription in v1.
- Pupils under 18. v1 targets higher education. `[ASSUMPTION: higher education only]`
- Corporate training buyers and researchers wanting raw exports beyond their own classes.
- Users outside Norwegian-speaking classrooms (v1 is Norwegian only).

### 2.3 Key User Journeys

*Narrated by the founder in the coaching round on 2026-11-02 and adjusted on 2026-11-05 when formal grading moved to v2. Names are illustrative; the founder is the model for Bård, the Lecturer.*

- **UJ-1. Kari, the admin, makes Bård a lecturer.**
  Kari runs the platform, opens the Admin area, enters Bård's email with the Lecturer role and sends the Invitation. Bård follows the link, sets a password, fills in a profile and lands on an empty lecturer home screen.

  **Edge case:** Bård already has an account as an Assistant lecturer in a colleague's course; Kari grants the Lecturer role to that account, and Bård keeps one login.

- **UJ-2. Bård invites 250 students three weeks ahead.**
  Two months into the course, Bård registers the Class "class-of-1994", exports the student list from Canvas as an Excel file, uploads it, and sends Invitations valid for two weeks. Over the next days the Roster fills up; students accept, set a password and fill in their profile. After two weeks, 238 have registered and 12 stand as unregistered. Bård manually registers two students who reported problems; the other ten stay out.

  **Edge case:** four addresses in the file are malformed; the upload lists them by row and accepts the rest.

- **UJ-3. Bård sets up the games in the last week.**
  A week before the start, Bård creates the Class session with default Game settings (a Lecturer of an advanced course may choose other settings) and LLM players, and marks it as obligatory for the course, as the course plan states. The system splits the 240 registered students at random into 60 Class games of four and gives each student a random Role. Bård sets the Start date and the deadlines and schedules four Lab hours in the computer lab.

  **Edge case:** with 241 students one Class game gets one student and three AI players.

- **UJ-4. Sara's group plays, mostly on its own schedule.**
  Sara, a logistics student, sees on the Start date that the Wholesaler Seat in game 17 is Sara's, with three classmates in the other Seats. They agree to start Tuesday evening, each on their own phone. Before the first Order Sara reads the rules (lowest cost for the whole chain, no talking about Orders) and does the five-minute Starting task on stocks and flows. Weeks 1 to 4 have fixed Orders of 4 to get the feel of the board. Every Week Sara sees inventory, backlog, incoming order and delivery, enters one Order, and sees which Roles the game is still waiting for.

  They play 15 Weeks, press Pause and agree to continue on Thursday in a Lab hour with Bård in the room. Sara can see that they are in Week 27, but not how many Weeks remain.

  **Edge case:** on Thursday Jonas, the Factory, does not come at the agreed time; Sara puts in an AI player for that Seat, marked as AI, and the game goes on. Jonas can take the Seat back later.

- **UJ-5. Sara's group debriefs together, then Sara plays alone.**
  When game 17 ends, the group opens the Group debrief together. First each writes, on their own phone, why the chain behaved as it did. Then the Debrief reveals customer demand (one step from 4 to 8), shows how Orders grew from Retailer to Factory, and points at Sara's Week-11 Order of 24 while 16 units were already on their way. Then each takes the Debrief quiz; Sara gets two questions wrong, reads why, and answers correctly on the second try. Over the weekend Sara plays the Replay alone against three AI players, with demand at the same levels as in the Class game, but more variation from Week to Week and the change in another Week. A short AI walkthrough of the run follows.

- **UJ-6. Sara takes the individual test.**
  The Individual test is open for a week. Sara works on it over several evenings, closing it and coming back: some multiple-choice questions; two Interactive items, one where Sara draws the inventory of a bakery after a jump in orders and one where Sara works out how many extra units it must produce; and three long answers that require arguing, from Sara's own game and Replay, why the chain oscillated and what to do differently. Sara submits before the Test deadline.

- **UJ-7. Bård keeps 60 games on track.**
  During the play period Bård opens the Lecturer overview: 60 Class games, 41 finished, 15 running, 4 waiting for someone. Bård sees whom each Class game waits for and for how long, and which are paused, and sends a Message to the Students of one Class game. In one Class game, three Students had ordered and an AI player took over the fourth Seat after 24 hours. At the Play deadline, AI players finish the two unfinished Class games.

- **UJ-8. Sara reads the AI assessment; Sara and Bård download the reports.**
  After the Test deadline, Sara gets an email that the AI assessment is ready. It shows a score and written feedback per question, quotes Sara's own answers, and says plainly that it is AI-generated and counts toward nothing. Bård has left the Indicative letter off, so Sara turns it on for Sara's own view. Sara downloads a PDF report of the games, the Debrief and the test and uploads it to the course's learning platform. Bård downloads all 240 reports as one ZIP file and the Completion export as a spreadsheet, and approves the obligatory requirement in the course's own system, based on completion alone.

  **Edge case:** a Student who never took the test still gets a report, with that step marked as not done.

- **UJ-9. Bård compares and reruns.**
  Bård opens the Class report (test results, the most common Detected patterns, Order amplification per Role), shows all 60 Class games side by side in a plenary, compares the results with last year's Class session in Cross-class statistics, and creates next year's Class session from this one.

## 3. Glossary

*All later sections use these terms exactly.*

- **Admin** — the platform operator's account role. Manages Users and account roles in the Admin area.
- **Admin area** — the part of the product where the Admin registers Users, grants account roles and sends Invitations.
- **User** — a person with an account. Holds one or more account roles: Admin, Lecturer, Assistant lecturer, Student.
- **Lecturer** — account role that creates and owns Classes and Class sessions. A Class can have several Lecturers.
- **Assistant lecturer** — account role attached to specific Classes; helps monitor, staff Lab hours and send Messages, but cannot create or delete Classes or Class sessions.
- **Student** — account role of a User on a Class's Roster who has accepted an Invitation or been registered by the Lecturer.
- **Institution** — the school or university a Class belongs to. Used for data separation and reporting.
- **Invitation** — an email with a link that creates an account or adds an account role to an existing account. Has a validity period.
- **Class** — a group of Students taught together (one course in one year), owned by one or more Lecturers. Has a Roster and one or more Class sessions.
- **Roster** — the list of student email addresses in a Class, with each address's registration status (invited, registered, unregistered).
- **Class session** — one run of the exercise for a Class: its Game settings, AI mode, Debrief mode, Individual test, deadlines, Lab hours and Games. Rerunning the exercise creates a new Class session.
- **Game settings** — the parameters every Class game in a Class session shares: starting inventory, supply-line contents, delays, Demand pattern, costs, number of Weeks and Guided Weeks, maximum Order, Information visibility and capacity.
- **Information visibility** — a Game setting that decides which numbers a Seat may see about its neighbouring Seats, for example the upstream Seat's inventory.
- **Demand pattern** — the customer demand series the Retailer faces: fixed series, step, or random from a seed.
- **Game** — one supply chain of four Seats played over Weeks: a Class game, a Replay, or a Lecturer's test Game (FR-87).
- **Class game** — a Game played by a group of up to four Students of the same Class session, with AI players in any empty Seat.
- **Replay** — a Game a single Student plays after the Debrief against three AI players, using a Replay scenario. Each Student plays one Replay in v1.
- **Replay scenario** — the Game settings of a Replay. The Lecturer may set any Game setting, so the Replay can be harder or different through starting conditions, delays, Demand pattern or Information visibility.
- **Role** — a position in the chain: Retailer, Wholesaler, Distributor or Factory. Not an account role (see User).
- **Seat** — one Role in one Game. Occupied by a Student or an AI player.
- **Week** — one turn of a Game. All Seats order in the same Week; the Week advances when every Seat has placed its Order.
- **Order** — the single decision a Seat makes each Week: how many units to order from upstream (for the Factory: to produce, which reaches its inventory after the order delay plus the production delay).
- **Supply line** — the units a Seat has ordered and not yet received, a computed total of ordered minus received.
- **Guided Weeks** — the first Weeks of a Class game, where every Seat's Order is fixed so the game starts in balance.
- **Starting task** — a short task on stocks and flows each Student does before their first Order. It counts toward nothing and is repeated in the Individual test.
- **Total cost** — the sum of holding and backorder costs over a Game, per Seat and for the chain.
- **Order amplification** — the standard deviation of a Seat's Orders divided by the standard deviation of customer demand, over the whole Game. Reported per Role.
- **Detected patterns** — a closed list of patterns the rules find in the Decision log, each with an exact definition and worded as a pattern, not a cause: an Order well above incoming orders after a shortage, a large Order while the Supply line already holds a lot, and very low Orders after an overshoot.
- **AI player** — software occupying a Seat. Either an LLM player or a Rule-based player. Always disclosed as AI. The brief's "AI opponent" means the same thing.
- **LLM player** — an AI player whose Orders come from a large language model, checked against a response schema and the game rules in code.
- **Rule-based player** — an AI player whose Orders follow a documented deterministic rule.
- **AI mode** — the Class session setting that decides whether AI players are LLM players (default) or Rule-based players.
- **Effort level** — the Class session setting that sets how much an LLM player thinks before it answers.
- **Play guard** — the system check that compares an LLM player's weekly Orders with reference players and switches the Seat to a Rule-based player when they fall outside the accepted band (FR-79).
- **Inactivity limit** — how long a Seat may leave its Order open while another Student in the Game waits, before an AI player takes over. Default 24 hours.
- **Share of LLM Orders** — the share of Orders in a Game's AI-held Seats that came from the LLM player and were not replaced. A Game below a set share is left out of §9.1.
- **Pause** — a state a Student sets on a Class game. While it lasts, no AI player takes over automatically.
- **Takeover** — an AI player taking over the Seat of a Student. **Reclaim** — the Student taking the Seat back.
- **Lab hour** — a scheduled time when the Lecturer or an Assistant lecturer is present and Students can play.
- **Start date** — the time from which Class games can be played.
- **Play deadline**, **Debrief deadline**, **Test deadline** — the time by which Class games end, the target for finishing Debrief, Debrief quiz and Replay (lateness is recorded), and the time by which the Individual test must be submitted.
- **Explanation** — the Student's own written account of what happened in their Class game, written during the Debrief, before customer demand is revealed.
- **Debrief** — the guided review after a Class game. Either a **Group debrief** (the Students of one Class game together; default) or a **Personal debrief** (one Student alone). **Debrief mode** chooses between them. The **Debrief summary** is the short per-Student record stored at the end of it (FR-47).
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
- **Completion status** — which steps of the Class session a Student has done, taken from system events and any logged Lecturer correction, never from an AI judgement. The **Completion export** is the file of it for a Class session (FR-60).
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
The Admin can enter an email address and an account role (Lecturer or Admin) in the Admin area and send an Invitation. Realizes UJ-1.
- Following the link lets the recipient create an account with the account role already granted; no further approval is needed.
- An expired or used link shows a message and a way to ask for a new Invitation.

#### FR-2: Admin grants a role to an existing user
The Admin can search Users by email or name and grant or revoke the Lecturer or Admin role.
- A User who gets the Lecturer role sees the lecturer home screen at next page load, with the same login.
- Revoking the Lecturer role from a User who owns Classes is blocked until another Lecturer is added to those Classes or the Classes are archived.

#### FR-3: Admin manages users
The Admin can list, search, deactivate and reactivate Users, resend Invitations and create Institutions.
- A deactivated User cannot log in; their data stays with their Classes.
- Every Admin action, Takeover by a person and Completion status correction is written to an audit log with actor, time and change.

#### FR-4: Account creation and login
A person following an Invitation can create an account with password and profile (name; email prefilled and not editable), and later log in with email and password. `[ASSUMPTION: email + password]`
- Password reset by email works without Admin involvement.
- One email address maps to exactly one User; an Invitation to an email that already has an account adds the account role to that account.

#### FR-5: Role-scoped access
The system restricts each User to what their account roles allow.
- A Student sees only their own Class sessions, Games, Debriefs, Replays, Individual tests, AI assessments and Student reports.
- An Assistant lecturer sees only the Classes they are attached to, including AI assessments and Student reports. `[ASSUMPTION: Assistant lecturers see AI assessments]`
- The Admin sees all Users but not Students' answers or AI assessments unless also attached to the Class; the export in FR-71 is pseudonymised.

### 4.2 Classes, Rosters and Invitations

**Description:** The Lecturer registers a Class, uploads the student list exported from Canvas, and sends Invitations about three weeks before the games start. Invitations expire; Students who have not accepted stand as unregistered, and the Lecturer can override that by hand. Realizes UJ-2.

#### FR-6: Create a class
A Lecturer can create a Class with a name, an Institution and an optional course code.
- The creating Lecturer becomes owner.
- A Class can be archived; archived Classes are read-only and kept for Cross-class statistics until the retention period ends (§6.1).

#### FR-7: Upload the roster
A Lecturer can upload a student list as an Excel (.xlsx) or CSV file, or paste email addresses, into the Roster. Realizes UJ-2.
- The Lecturer picks which column holds the email addresses; a Canvas grade-book or people export is accepted without editing. `[ASSUMPTION: a real Canvas export must be checked first; it may be CSV with no email column, in which case pasting addresses is the route]`
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
- An Assistant lecturer Invitation grants the account role for that Class only. `[ASSUMPTION: Lecturers, not only the Admin, can invite Assistant lecturers]`
- Co-owners have the same rights as the owner.

### 4.3 Class session setup

**Description:** The Class session holds everything common to the whole class: Game settings, AI mode, Debrief mode, Replay scenario, Individual test, the obligatory mark, dates and Lab hours. Defaults are prefilled; the Lecturer may change any Game setting, and the change applies to every Class game. A private test Game shows what the settings do. Realizes UJ-3.

#### FR-11: Create a class session with defaults
A Lecturer can create a Class session prefilled with classic Game settings and save it without changing anything.
- Defaults: four Roles; starting inventory 12 per Seat; 4 units in every supply-line slot; order delay 2 Weeks; shipping delay 2 Weeks; Factory production delay 2 Weeks; customer demand 4 per Week stepping to 8 in Week 5; holding cost 0.50 and backorder cost 1.00 per unit per Week; 36 Weeks.
- Confirmed by the founder against the course material (2026-11-05). Sources disagree on delays, so these are the product's defaults, not one true classic value, and the setup screen says so.
- The order delay also applies to the Factory, so a Factory Order reaches its inventory after 4 Weeks, and production is unlimited. Founder decision 2026-11-05. The slot layout is in addendum §B.
- Weeks 1 to 4 are Guided Weeks with Orders fixed at the starting demand, for AI players too, and the Lecturer can change their number. Founder decision 2026-11-05.
- A first-time Lecturer can create a Class session with defaults in under 10 minutes without help (SM-5).

#### FR-12: Change game settings
A Lecturer can change every Game setting before the Start date. Founder decision 2026-11-05: the Lecturer configures the game as they wish, with all parameters available.
- Settings: starting inventory or backlog, supply-line contents, order delay, shipping delay and Factory production delay (each 1 to 3 Weeks), costs, number of Weeks and Guided Weeks, maximum Order, Demand pattern (FR-13), Information visibility (FR-83) and capacity.
- The maximum Order defaults to a value that does not bind in normal play, since single Orders reached about ten times the average in one earlier course; a low value triggers a warning.
- Guided Weeks must be fewer than the Week of the first demand change and leave enough Weeks to play; values that break this are rejected.
- Debrief quiz items and Core items are written to hold under any setting, or take their values from the Game settings. The setup says which settings the product's content and Play guard were calibrated for.
- The setup warns, without blocking, when supply-line contents differ from starting demand, backorder cost is not above holding cost, capacity is below peak demand, or the Weeks are too few for a demand change to pass through the chain at the chosen delays (addendum §B).
- Capacity is an optional maximum number of units a Seat can ship per Week, off by default, set for one Seat or for all. It is stated to Students in the briefing (FR-84) and named in the Debrief.
- Units a Seat cannot ship stay as backlog, so a capped Seat can hold inventory and backlog at once. In a four-Role chain each Seat has one customer, so no allocation rule is needed. `[ASSUMPTION: capacity design from research; one platform precedent, no human evidence]`
- Out-of-range values are rejected with the allowed range shown. `[ASSUMPTION: delays 1 to 3 Weeks; other ranges set in UX and architecture]`
- The only preset is "Classic" (FR-11). An advanced course has no preset of its own: the Lecturer decides what is different, and may keep the Classic values. Founder decision 2026-11-05.
- Game settings are locked from the Start date.

#### FR-13: Choose a demand pattern
A Lecturer can choose a Demand pattern: fixed series, step (start level, new level, Week of change) or random. Random demand is drawn each Week from a discrete uniform distribution over the whole numbers from mean minus spread to mean plus spread (never below 0), with a seed.
- The Lecturer can combine them: a step in the mean with random noise around it.
- Every Class game in the Class session uses the same demand series.
- The seed is shown to the Lecturer and stored with the Class session, and the Lecturer can enter or keep a seed.

#### FR-83: Choose information visibility
A Lecturer can set Information visibility for the Class session, as a Game setting. Founder decision 2026-11-05: a Seat seeing the inventory of its upstream neighbour is part of v1. These are teaching choices, and the help text promises no effect on learning or cost: the research tested seeing all Seats in one direction, and nobody has tested seeing only one neighbour (addendum §B).
- Default: off, so a Seat sees only its own numbers (FR-23).
- A Lecturer can switch on a view of the current inventory (and backlog) of the Seat directly upstream, as they stand when the Order is placed, shown on the Seat's screen next to its own numbers. The Factory has no upstream view. `[ASSUMPTION: backlog is shown too]`
- A Lecturer can also switch on the same view of the Seat directly downstream. The Retailer has no downstream view. Founder decision 2026-11-05.
- The setting applies to every Class game of the Class session and can differ in the Replay scenario (FR-49).
- AI players receive exactly the numbers a Student in that Seat would see, and the Decision log records what was visible (FR-67).
- The Student sees which neighbour numbers are shown, labelled with the Role and the Week they refer to.

#### FR-14: Hidden end and demand
Students are never shown the number of Weeks in a Game or the customer demand series while playing.
- Students see the current Week number and their own history, not how many Weeks remain.
- Only the Retailer Seat sees customer demand, one Week at a time.
- Students are told to play as if the business continues, with no number of Weeks, stated or false. Founder decision 2026-11-05.
- The Debrief reveals both (FR-44).

#### FR-15: Choose AI mode
A Lecturer can set the AI mode to LLM players (default) or Rule-based players for the Class session.
- The AI mode applies to every AI player in the Class session's Class games and Replays.
- A Lecturer who prefers not to use AI, or who needs fast and predictable play, chooses Rule-based players when setting up the Class session. LLM players with an Effort level (FR-78) are the alternative.
- A Lecturer who wants no LLM use at all also chooses the code-only Debrief (FR-44) and turns off the AI assessment (FR-61). Debrief follow-up is then off. `[ASSUMPTION: this no-LLM path]`

#### FR-16: Choose debrief mode
A Lecturer can set Debrief mode (Group debrief by default, or Personal debrief).

#### FR-17: Obligatory class session
A Lecturer can mark a Class session as obligatory for the course, until the Start date, and confirms that the course plan states it. Realizes UJ-3.
- Students get an email when it is marked, and see it on their home screen and in deadline reminders.
- The requirement is met by completing every step: Class game, Debrief, Debrief quiz, Replay and submitted Individual test. Only the Completion status decides it; the AI assessment and the Indicative letter never do.
- The Class game step counts as done only if the Student placed Orders in at least a set share of the Weeks after the Guided Weeks, so a Student who leaves the Seat to an AI player does not complete it. Takeover Weeks and playout Weeks count as not ordered. `[ASSUMPTION: Lecturer sets the share, default 80%]`
- The Lecturer overview and the Completion export show when a Student fell short because of playout or the group's pace, so the Lecturer can correct it for a Student who kept up.
- A Student gets a warning at Takeover that it may affect the requirement, in words that do not reveal the number of Weeks.
- A Lecturer can give a Student who fell short, was ill or registered late a make-up: a solo Class game against AI players, open until the Test deadline. `[ASSUMPTION: make-up route]`
- An auto-submitted Individual test counts only if it has content in each required part, and an Explanation has a minimum length. v1 shows participation, not effort; the Lecturer also sees time spent and constant Orders, which never affect the status automatically. `[ASSUMPTION: these minimums]`
- A Lecturer can record a per-Student adjustment of the Inactivity limit, the share and any timed sitting, for Students with a right to it.
- A Lecturer can see who has not met the requirement and send those Students a Message in one action.
- A Lecturer can correct a Student's Completion status with a reason, which is logged.
- The product records completion only; the Lecturer approves in the course's own system. `[ASSUMPTION: no approval action in the product in v1]`

#### FR-18: Set dates
A Lecturer can set the Start date, Play deadline, Debrief deadline and Test deadline.
- Dates must be in this order.
- The Test deadline defaults to 7 days after the Debrief deadline, and the Lecturer can change it. Founder decision 2026-11-05. `[ASSUMPTION: the 7 days count from the Debrief deadline]`
- Students see their next deadline on their home screen and get an email 24 hours before each deadline that applies to them. `[ASSUMPTION: 24-hour reminders]`
- The Debrief deadline is a target: Debrief, Debrief quiz and Replay stay open until the Test deadline, and lateness is recorded. At the Test deadline, saved answers are submitted (FR-51) and unfinished steps stay not done. `[ASSUMPTION: these deadline rules]`
- An extension applies to the whole Class session or moves one Student's Debrief and Test deadlines together. There is no per-Student Play deadline; a make-up covers that (FR-17).
- A Student with an extended Test deadline gets the AI assessment after that deadline; the rest of the Class session is not held back, and the Scoring guide stays as it was at the original Test deadline.
- The setup warns about date plans that leave too little time for the number of Weeks, once SM-11 is known.
- Last moment to change: the Start date for Game settings, AI mode, Effort level, Debrief mode, Replay scenario, question set, the obligatory mark and Inactivity limit; the Test deadline for the Scoring guide and AI assessment switch-off; any time for deadlines and Lab hours. `[ASSUMPTION: these lock points]`

#### FR-19: Schedule lab hours
A Lecturer can add Lab hours (date, time, place) to a Class session, as many as needed.
- Students see upcoming Lab hours on their home screen and get them by email when added. `[ASSUMPTION: email on creation]`

#### FR-87: Lecturer test game
A Lecturer can play a private test Game with chosen Game settings against three AI players, to see what the settings do before the Start date. Founder decision 2026-11-05.
- Test Games never appear in any report, statistic or export.

### 4.4 Groups and Class games

**Description:** In the last week before the Start date, the system splits the registered Students at random into Class games of up to four and gives each a random Role. If the count does not divide by four, one Class game gets fewer Students and AI players in the empty Seats. Students can instead choose their Class game if the Lecturer prefers. Before their first Order, each Student reads the rules and does the Starting task. Realizes UJ-3, UJ-4.

#### FR-20: Automatic random allocation
A Lecturer can let the system create Class games by placing every registered Student at random into groups of four and assigning each a random Role. Realizes UJ-3.
- If the number of Students is not divisible by four, one Class game at allocation has fewer Students (one to three), and its empty Seats get AI players.
- The Lecturer sees the result before confirming, can re-run the allocation, and can move or swap Students before the Start date.
- A Student registered after allocation is placed in a free AI-held Seat of a Class game that has not started. If there is none, the Student gets a make-up (FR-17).

#### FR-21: Student choice (optional)
A Lecturer can instead let Students choose a Class game and a free Seat.
- A Student can hold only one Seat in one Class game per Class session.
- At the Start date, Students without a Seat are allocated at random.

#### FR-22: Class games open at the start date
From the Start date, every Student sees their Class game, Role and the other Seats (Students' names or "AI player").
- The Class game starts when the first Student in it opens it and presses start; from then on the inactivity rules apply (FR-36).
- The Lecturer can start any Class game, or all at once.
- Students in a Class game can propose and accept a time to play in the product, with no free text, so they can arrange play without a chat. `[ASSUMPTION: this scheduling aid]`

#### FR-84: Rules before the first Order
Before their first Order, each Student sees a short briefing. Founder decision 2026-11-05.
- The objective is the lowest Total cost for the whole chain.
- It explains that all Seats order in the same Week, the delays, that stock must be shipped when it exists, and that the game has Guided Weeks.
- Students may arrange when to play, but may not discuss Orders or numbers with other players.
- Product text never uses the name "Beer Game" before the Debrief, so Students do not look up the answer, and the product's own name respects this. What the course plan says is the Lecturer's choice.

#### FR-85: Starting task
Before their first Order, or before their Debrief if they placed none, each Student does the Starting task, about five minutes, scored by computed rules. Founder decision 2026-11-05. Realizes UJ-4.
- It counts toward nothing. The same items are repeated in the Individual test (FR-52), so the two can be compared.
- It ends with one optional question, describing the game without naming it, on whether the Student has played it before.

### 4.5 Gameplay

**Description:** All four Seats order in the same Week, and the Week advances when every Seat has ordered. The Student only decides; the system does all the arithmetic. The game shows clearly whom it waits for. A Class game can run in one sitting in a Lab hour or stretch over several days. The playing screen is portrait-first: one Seat's facility, goods flowing down and orders flowing up, one number to enter. Realizes UJ-4.

#### FR-23: Weekly state shown to a Seat
A Student sees, for their own Seat: current inventory or backlog (both on a capped Seat), incoming order this Week, incoming delivery this Week, units shipped this Week, the contents of their Supply line, their own Order history, their running Total cost and the current Week number.
- The Student does not see other Seats' inventory, backlog or Orders during the Class game, except what the Lecturer has switched on in Information visibility (FR-83).
- On a 360-pixel-wide screen, all of this plus the Order input is visible without horizontal scrolling.

#### FR-24: Place an order
A Student can enter one Order per Week as a whole number from 0 to the maximum in Game settings, and confirm it. In Guided Weeks the Order is fixed and placed automatically, the Week advances once every Student in the Class game has opened it, and the clock for the Inactivity limit does not run.
- Invalid input is rejected inline before submission.
- After confirmation the Order cannot be changed.

#### FR-25: Who the game waits for
Every Student in a Class game sees which Seats have ordered this Week and which the game is waiting for, by Role and name or "AI player", and how long it has waited. Realizes UJ-4.
- The Student whose Order is missing sees that the game waits for them, on the Class game screen and on their home screen.

#### FR-26: Week advance
A Week has one sequence: when it opens, each Seat receives its delivery and incoming order, fills orders and backlog as far as stock and capacity allow, and ships; Seats then see the result and place Orders; when every Seat has ordered, costs are charged on end-of-Week balances and all slots advance.
- The new Week is shown to all connected Students within 2 seconds of the last Order, excluding AI player thinking time and any animation, which can be skipped and never blocks input.
- Each Week's state is stored before it is shown; a reload or device switch resumes at the same Week with nothing lost.

#### FR-27: Notification when it is your turn
A Student gets an email when their Class game has been waiting for their Order for a set time, gathered in one message per day and never at night. `[ASSUMPTION: after 2 hours, then again 4 hours before Takeover]`

#### FR-28: Game end
A Class game ends after the last Week in Game settings, or through the playout at the Play deadline (FR-38).
- The last Week runs in full. Units still in slots carry no cost and count in the conservation check.
- On end, every Student in the Class game sees the chain's Total cost first and the cost per Role, not per name, and is led to the Debrief (FR-41).

#### FR-29: Correct bookkeeping
The game arithmetic is correct by construction: inventory and backlog are never both positive for a Seat without capacity, units are conserved across the chain, and costs equal the rates times units.
- An automated check over every finished Game confirms conservation of units and cost totals; any violation is logged as an error.

### 4.6 AI players

**Description:** AI players are the product's first differentiator and the first thing built. LLM players are the default; Rule-based players are the Lecturer's choice when comparable, cheap or fully reproducible results matter more than realism. An AI player sees only what a Student in that Seat would see and decides as a supply chain manager would, without knowing it plays a game. Its Orders must match a fixed response schema, a Play guard (FR-79) compares them with reference players week by week, and every decision is logged.

A smart LLM player is acceptable: the game is a team game with no winners, and the aim of every player is the best Order given the information available. Students always know which Seats are AI. Realizes UJ-4, UJ-5.

#### FR-30: AI players fill seats
The system places an AI player in every empty Seat of a Class game at the Start date, in the three other Seats of a Replay, and in a Seat at Takeover.

#### FR-31: Same numbers as a human
An AI player receives only the information a Student in that Seat would see (FR-23): its own data and what arrives from its downstream and upstream neighbours. The game rules are part of the prompt sent when it is the AI player's turn. No model call is made in Guided Weeks.
- The prompt describes the situation of a supply chain manager. An AI player is not told that it plays a game, that there are four Seats, or that Weeks advance after all Seats have ordered. Like a Student, it is told to act as if the business continues.
- Its objective is the best Order for its own part of the chain, so unlike a Student it is not told about the chain's total. Prompt calibration checks whether a model recognises the game.
- No AI player receives customer demand unless it holds the Retailer Seat, or any other Seat's private state beyond what Information visibility shows a Student in that Seat (FR-83).
- No AI player receives any Student's name, email or other personal data; Seats are referred to by Role.

#### FR-32: Validated orders and fallback
Every request to an LLM player asks for a response in a specific JSON format and carries the JSON schema; the Order is checked against the schema and the game rules before it takes effect.
- A response that does not match the schema is retried, at most 5 times. When the retries are used up, the Rule-based player's Order is used for that Week, and the replacement is marked in the Decision log.
- An Order that is missing, not a whole number or outside the allowed range counts as a response that does not match. `[ASSUMPTION: range violations handled like schema failures]`
- Each attempt has a timeout and each Order a total time budget, set per Effort level (NFR-2). An Order not ready in time is replaced by the Rule-based player's Order. No limit applies in the playout at the Play deadline, when no Student is waiting. `[ASSUMPTION: values set after the prototype, issue #8]`
- The fallback applies to that Week only; the LLM player is asked again the next Week. Founder accepted recommendation 2026-11-05.

#### FR-33: Documented AI behaviour
Each AI player type has a short plain-language description of how it decides, visible to Lecturers.
- The Rule-based player follows a documented anchoring-and-adjustment rule. Its parameters come from the primary source (issue #8), and it uses no neighbour numbers from Information visibility and only the Game settings in force. `[ASSUMPTION: ignores neighbour numbers]`
- The LLM player's description states that its behaviour varies between runs.
- The description states that the LLM player is not told it is playing a game and may play better than a typical Student.
- Lecturers get short material on how the AI players and the AI assessment work and on why not to grade from them (EU AI Act Art. 4).

#### FR-34: Disclosure of AI players
Every AI player is labelled as AI wherever Seats are shown to Students, from the first moment the Student sees the Game.
- A Seat that has been taken over shows that it is now played by an AI player.
- A Seat whose LLM player has been switched to a Rule-based player by the Play guard (FR-79) shows this too.
- AI-generated text (Debrief narration, follow-up answers, Debrief quiz explanations, Replay walkthrough, Adapted items, AI assessment) is marked as AI-generated, for people and in machine-readable form, including in PDF files.

#### FR-78: Effort setting
A Lecturer who has chosen LLM players can set an Effort level for the Class session, which sets how much the model thinks before it answers.
- The Effort level applies to every LLM player in the Class session's Class games and Replays, and is stored with the Class session and in the Decision log.
- The default Effort level and the effect of each level on speed and cost are set after the prototype. `[ASSUMPTION: levels and default decided by prototype testing, issues #8, #9]`
- Lecturers are offered only levels the pinned endpoint supports and that were measured inside the cost limit in §6.3 and the time budget in NFR-2, retries included. The Decision log stores actual reasoning tokens.
- The prompt is calibrated by testing before launch, so that LLM players stay inside the Play guard's band at each offered Effort level.

#### FR-79: Play guard
The system compares every Order from an LLM player with two reference Orders computed for the same Week, and switches the Seat to a Rule-based player when the LLM player's Orders over time fall outside an accepted band.
- The lower reference is the Rule-based player (FR-33), standing for average sensible play, with the information FR-33 gives it. The upper reference is a near-optimal player computed by the system, which may use information the LLM player never sees.
- The comparison is made on weekly Orders, not on chain Total cost, because an LLM player does not see the whole chain. Guided Weeks and fallback Orders are left out, because a fallback Order would look like perfect sensible play.
- The band: over a rolling window of Weeks, at least 95% of the LLM player's Orders are within a set distance of the lower reference, and in Weeks where the two references differ, they are on average no closer to the near-optimal reference than a margin of 5%. In calm Weeks both references coincide, and those Weeks do not count against the upper limit. `[ASSUMPTION: the founder's wording is read as two limits; the distance measure, window and confidence level are set in prototype testing, issues #9, #11, #20]`
- No switch happens before a minimum number of Weeks.
- A Seat the guard has switched stays Rule-based for the rest of the Game, is marked in the Decision log and shown to Students (FR-34). Founder accepted recommendation 2026-11-05.
- The guard also applies when the Lecturer has changed the Game settings, and the Rule-based reference is computed for the settings in use. Founder decision 2026-11-05.
- The band is calibrated on Classic settings and the default Replay scenario. Under other settings, a large deviation from sensible play still switches the Seat. `[ASSUMPTION: what counts as large is set in prototype testing; the 5% limit is not applied on uncalibrated settings]`
- The guard applies to a Seat's LLM player only; it does not judge Students. The share of switched Seats is reported, and §10.1 sets its limit for the prototype.

### 4.7 Inactivity, Takeover and deadlines

**Description:** The system measures activity. A group can pause its Class game and agree when to continue. When one Student holds the others up, an AI player takes over after the Inactivity limit. In a paused Class game the others can put one in if the Student misses the agreed time. If nobody plays, nothing happens until the Play deadline, when AI players finish the Class game. Founder decision 2026-11-05. Realizes UJ-4, UJ-7.

#### FR-35: Activity tracking
The system records, per Seat, when each Week opened for it and when the Student ordered.

#### FR-36: Automatic takeover
When a Student has not ordered and at least one other Student in the Class game has ordered and waited for the Inactivity limit, an AI player takes over the Seat. Realizes UJ-4.
- If no Student in the Class game has ordered that Week, nothing happens until the Play deadline. No AI player plays a Class game on its own before then.
- No automatic Takeover happens while the Class game is paused (FR-89).
- The Lecturer sets the Inactivity limit per Class session; default 24 hours.
- The Student, the other Students in the Class game and the Lecturer overview are notified at Takeover.
- The clock starts when the first other Student has ordered that Week. `[ASSUMPTION: this start of the clock]`
- The Lecturer can mark a Class game as in the room during a Lab hour and set a shorter limit for it. `[ASSUMPTION: a shorter limit applies only to marked games, because the product does not know who is present]`

#### FR-37: Manual takeover and reclaim
A Lecturer or Assistant lecturer can trigger Takeover of any Seat at any time. A Student whose Seat was taken over can reclaim it at the start of any later Week.
- A Reclaim is a queued request that takes effect when the next Week opens, and restarts the clock. A Play guard switch outlasts a Reclaim: if the Student later loses the Seat again, a Rule-based player takes it.
- A Lecturer can fill all absent Seats in one Class game or in all of them in one action, for example at the start of a Lab hour.
- Weeks played by the AI player stay marked as AI Weeks in the Decision log and Game insight.

#### FR-89: Pause
Any Student in a Class game can pause it and state when the group will continue. Founder decision 2026-11-05. Realizes UJ-4.
- While the Class game is paused, no AI player takes over automatically, and the other Students see the pause and the agreed time. Any Student can end the pause by ordering.
- If a Student does not come at the agreed time, or after the Inactivity limit if no time was stated, another Student in the Class game can put an AI player in that Seat (FR-37 applies for reclaiming it).
- The Lecturer overview shows which Class games are paused, and since when.
- A Pause does not move the Play deadline.

#### FR-38: Play deadline playout
At the Play deadline, every unfinished Class game is played to its last Week, with AI players in all Seats, so the Debrief can open.
- Students in those Class games see that their game ended at the deadline and are led to the Debrief.
- No Class game remains unfinished after the Play deadline (SM-4).

### 4.8 Lecturer overview and Messages

**Description:** One screen shows every Class game in a Class session and what needs attention. The Lecturer and Assistant lecturers can message the whole Class session, one Class game, or one Student. Realizes UJ-7.

#### FR-39: Lecturer overview
A Lecturer or Assistant lecturer can see all Class games in a Class session with: current Week, status (not started, running, waiting, paused, finished), whom each Class game waits for and for how long, each Seat's occupant (Student or AI player, Takeover marked) and running chain Total cost.
- Class games approaching Takeover are highlighted.
- The view updates without reload within 5 seconds of a change.
- The overview shows the Class session funnel: registered, Class game finished, Debrief done, Debrief quiz passed, Replay done, Individual test submitted, AI assessment ready.

#### FR-40: Send messages
A Lecturer or Assistant lecturer can send a Message to all Students in a Class session, to the Students of one Class game, or to one Student.
- The Message appears in the product and is sent by email.
- Students cannot reply in the product in v1. `[NON-GOAL for MVP: communication between players is planned for v2]`

### 4.9 Debrief and Debrief quiz

**Description:** When a Class game ends, the group by default goes through the Debrief together. Each Student explains in the Debrief what happened, and afterwards takes the Debrief quiz until every answer is right. All numbers in the Debrief come from the Decision log; the LLM only narrates and asks.

The Debrief follows a classic sequence: how it felt, what happened, why the structure produced it, and what each Student's own Orders did. Its voice is direct and concrete, in the second person: here is where you over-ordered, here is what it cost four Weeks later, here is what the other Roles saw. It explains causes through structure, not people, assigns no blame and adds no padding praise. The goal is that Students stop asking whether they were right and start asking why it happened. The Debrief and the Debrief quiz are formative and count toward nothing. Realizes UJ-5.

#### FR-41: Explanation in the Debrief
Early in the Debrief, before customer demand is revealed, each Student writes an Explanation of why their supply chain behaved as it did and what part their own Orders played. `[ASSUMPTION: the step comes before the reveal, so the Explanation still works as the before-measure in §9.1]`
- The Debrief does not move on for a Student until their Explanation is saved.
- In a Group debrief each Student writes on their own device and does not see the others' Explanations.
- The Explanation is stored unchanged and shown later in Game insight and in the Student report.

#### FR-42: Debrief availability
The Debrief becomes available when the Student's Class game has ended, with the Debrief deadline as its target (FR-18).
- At setup the Lecturer chooses between open Debriefs and holding all Debriefs until every Class game has ended, and the screen explains that open Debriefs can reveal the Demand pattern to Students still playing. `[ASSUMPTION: open by default]`

#### FR-43: Group debrief
With Group debrief, any Student of a Class game can open a shared Debrief for the Students of that Class game; the others are notified and can join. Realizes UJ-5.
- All joined Students see the same Debrief step. The step moves on when every joined Student has finished it, or when the Student who opened the Group debrief moves it on, at the earliest after a short wait. Writing the Explanation is individual and has a time guide. `[ASSUMPTION: step control]`
- Customer demand is revealed to a Student only after that Student's Explanation is saved. A late joiner writes the Explanation first and then enters at the current step.
- On one shared screen only the shared charts show; each Student's own moments and Explanation stay on their own device (FR-74).
- A Student who missed the Group debrief, or whose group has not met 48 hours after the Class game ended, can take a Personal debrief at once. A joined Student who dropped out continues in a Personal debrief from where they were. `[ASSUMPTION: fallback rule]`
- One joined Student can go through a Group debrief alone, and a Class game with one active Student uses Personal debrief.

#### FR-44: Debrief content
The Debrief shows, for the Class game:
- the customer demand series, revealed;
- Orders, inventory and backlog per Role over the Weeks, in one chart, with a text alternative;
- how much Orders amplified from Retailer to Factory;
- for each Student, at least three specific moments from their own Seat: the Week, what they saw, what they ordered, what it cost over the following Weeks, and which Detected pattern and mechanism it matches (delay, Supply line, demand information lost in orders); `[ASSUMPTION: moments chosen by rules over the Decision log]`
- what the other Roles saw at those moments;
- each Student's Explanation next to what the data shows (shown only to that Student in a Group debrief).
- Every number shown matches the Decision log exactly; narration that cites numbers or causes not in the computed facts is rejected.
- The Debrief states that the AI's explanation can be wrong.
- Causes in narration may only come from Detected patterns and computed facts. The LLM connects approved sentences with these in slots, which is how causes are checked. Two lecturers review the patterns before they are built on. `[ASSUMPTION: template approach]`
- If narration is rejected or the provider fails, the Student gets the same content from code, without LLM text. `[ASSUMPTION: code-only fallback]`
- A Student with fewer than 10 own Orders sees the Class game as played mostly by AI players, gets moments from their Replay, and is left out of SM-1 and SM-2. `[ASSUMPTION: threshold of 10 Orders]`
- The share of chain Total cost incurred in AI-held Seats is shown, so no Student's own share is overstated.

#### FR-45: Guided questions and follow-up
The Debrief asks reflection questions in sequence (feelings, then evidence, then structure) and lets Students ask follow-up questions about their Game. `[ASSUMPTION: structured walkthrough with bounded follow-up, not open chat]`
- Follow-up answers stay within the Game and Beer Game concepts; off-topic requests are declined.
- Follow-up answers use the same computed facts as FR-44, give prompts and hints instead of model answers to test-like questions, and close for a Student once their Individual test opens.

#### FR-46: Debrief quiz
After the Debrief each Student takes the Debrief quiz individually and must answer every question correctly to continue. Realizes UJ-5.
- The questions are fixed and scored by answer key. The LLM may only word the explanations.
- After each attempt the Student sees which answers were wrong and an explanation of why.
- The Student can retry until the Test deadline. A Lecturer can exclude a question. `[ASSUMPTION: no limit on retries; questions may be reshuffled]`
- The Debrief quiz result counts toward nothing; the number of attempts is visible to the Lecturer.

#### FR-47: Debrief summary
At the end of the Debrief, the system stores a short summary per Student: key moments, answers to reflection questions and completion time. Debrief quiz attempts are added when the Debrief quiz is passed.
- Lecturers and Assistant lecturers can read every summary.

### 4.10 Replay

**Description:** After passing the Debrief quiz, each Student plays one Replay alone against three AI players under harder conditions, so the Student meets the same structure again. The Replay ends with a short AI walkthrough. `[ASSUMPTION: changing the run makes it harder and limits what memory can do; no source defines difficulty or shows this]` Realizes UJ-5.

#### FR-48: Start the replay
A Student who has passed the Debrief quiz can start the Replay at any time before the Test deadline.
- The Student plays the same Role as in the Class game. `[ASSUMPTION: same Role]`
- Three AI players in the Class session's AI mode take the other Seats.
- The Student can leave the Replay and resume it on any device. No other human holds it up; the Student waits only for the AI players' answers (NFR-2).

#### FR-49: Replay scenario
The Replay uses a Replay scenario. By default it differs from the Class game, and the Lecturer may set any values, including the Class game's. Levers are starting conditions (for example starting with backlog or low inventory), delays, Information visibility and Demand pattern (for example a larger or later step, or random demand). The setup warns about changes that are likely to make it easier, such as shorter delays or more information.
- Default: the Class game's demand levels with larger variance, meaning random demand drawn from a discrete uniform distribution around the mean in each Week (mean 4, then 8 after the step) with a spread of 2. Founder decision 2026-11-05: larger variance in demand; distribution chosen by the product team. `[ASSUMPTION: spread of 2]`
- By default the step Week and the number of Weeks also vary per Student and stay hidden, because the Debrief has just revealed them. Founder decision 2026-11-05. `[ASSUMPTION: step Week between 5 and 12, 30 to 40 Weeks; no Guided Weeks]`
- The Lecturer can accept the default or set every Game setting freely, starting from the Class session's settings. Founder decision 2026-11-05: the Lecturer configures all parameters as they wish.
- Every Replay uses a fresh demand seed per Student, stored in the Decision log.
- The end of the Replay and its demand stay hidden while playing (as FR-14).

#### FR-50: Replay feedback
At the end of the Replay the Student gets a short AI walkthrough, under the same rules as FR-44: their Total cost, a chart of the run, a comparison with their Class game, and one or two specific moments from their own Orders, computed from the Decision log. Founder decision 2026-11-05.
- Every number matches the Decision log. The comparison says that it is not like for like: the neighbours are AI players, demand differs and the run may be shorter.
- The Student is asked two optional questions: how believable the AI players' ordering felt (FR-70), and whether they would have wanted to play another round (SM-10).

### 4.11 Individual test

**Description:** Each Student shows what they learned in the Individual test after the Replay: multiple-choice questions, Interactive items and long answers that require argument, some of them about the Student's own Class game and Replay. The test asks for what remembering the game cannot give: a quantity, a consistent set of graphs, or an explanation of the mechanism. It is not supervised; Interactive items and Adapted items are there to make it harder to answer with outside AI tools. The product provides the question set with Item weights. The test produces no grade in v1. Realizes UJ-6.

#### FR-51: Test availability
A Student can open the Individual test once they have completed the Replay, until the Test deadline, by default 7 days after the Debrief deadline (FR-18).
- By default the Student can close the test, return and work as much as they want until the Test deadline; answers are saved automatically and the Student submits once.
- A Lecturer can instead require one sitting with a time limit.
- `[ASSUMPTION: saved answers not yet submitted are submitted automatically at the Test deadline; no retakes]`
- When opening the Individual test the Student states that the work is their own.

#### FR-52: Question set and item weights
The product provides a Norwegian question set for the Individual test with an Item weight for each question, covering stocks and flows, delays and the Supply line, demand amplification and its causes, and the Student's own decisions.
- Core items include multiple-choice questions scored by answer key, Interactive items (FR-80) and long-answer questions.
- Multiple-choice questions cover definitions and causes, with wrong options built from known misperceptions, including a cause unrelated to the chain.
- Items that reward remembering that the game oscillates are not used. By default most of the weight sits on Interactive items and long answers. The product warns a Lecturer who removes the quantity items. `[ASSUMPTION: default weights set when the question set is written]`
- The test repeats the items in the Starting task (FR-85), asks once with the same wording as the Explanation (for SM-2), and includes one item on a Demand pattern the Student has not seen. Founder decision 2026-11-05.
- Long-answer questions ask the Student to explain the behaviour from the structure of the chain (delay, Supply line, own ordering rule), not from what other players did.
- A Lecturer can review the question set before the Start date, exclude questions and change Item weights; weights always sum to 100%.

#### FR-53: Adapted items
The Individual test includes Adapted items generated from the Student's own Class game and Replay, each referring to a specific Week, Order or outcome.
- Adapted items follow the same question templates for every Student, filled with facts from the Student's own games, so difficulty varies as little as possible.
- Every fact an Adapted item cites matches the Decision log.
- Adapted items carry a fixed total Item weight set by the Lecturer, default 30%, so scores stay comparable between Students with different games.
- A Lecturer can preview the Adapted item templates with a sample Student before the Start date.
- A Student with fewer than 10 own Orders gets Core items in their place.

#### FR-80: Interactive items
The Individual test includes Interactive items where the Student answers in an interactive graph, table or diagram, for example by drawing a stock after a jump in demand, filling in a table of weekly stocks, or connecting the causes in a diagram (scored by answer key).
- Two to three Interactive items use a business other than the beer chain, so they test reasoning rather than recall of the game. All items are written fresh, with their own stories and numbers.
- Interactive items are scored on quantities and consistency (units added equal units missing; the stock agrees with its flows), never on whether the answer looks like oscillation, with partial credit per coded criterion. Students are told that these items are hard, also for well-educated adults. `[ASSUMPTION: scored by computed rules, not by the LLM]`
- Each Interactive item asks for one output and shows a computed explanation in the AI assessment. Table and number entry are built first; drawn items follow when computed scoring has been checked against hand scoring in the rehearsal. `[ASSUMPTION: this order]`
- Every Interactive item can be answered by keyboard and screen reader, for example through a table alternative (NFR-6).
- `[ASSUMPTION: works on a phone from 360 pixels wide, as FR-73 requires, but best on a laptop]`

#### FR-81: Scoring guide
The AI assessment scores long-answer and Adapted items against one Scoring guide, which states for each question or question template what is asked for, 5 to 8 coded criteria, how they weigh, what strong and weak answers look like, and one fixed score scale. `[ASSUMPTION: a five-step scale]`
- The default guide is written during implementation and approved by the founder before the first Class session.
- A Lecturer can edit the guide for a Class session. `[ASSUMPTION: edits are possible until the Test deadline; the version in force at the deadline scores the whole Class session, as the model is fixed by FR-68]`
- An edited guide is checked only if a Control test is run with it (FR-82). Until then, the Lecturer and the feedback are told it has not been checked.

### 4.12 AI assessment and reports

**Description:** After the Test deadline, the AI gives each Student a score and written feedback on the Individual test. The AI assessment is formative: it counts toward nothing, and no human has to review it. Students and Lecturers can download a PDF report of the games, the Debrief and the test. A Control test checks the AI assessment before real Students depend on it. All formal grading is out of v1 (§8.3); if a course grades this work, it does so outside the product under its own rules. Realizes UJ-8.

#### FR-54: AI assessment
After the Test deadline, the system produces an AI assessment for each submitted Individual test: the score on answer-key and Interactive items, one overall score with written feedback for each long-answer and Adapted item following the Scoring guide (FR-81), and a total score using the Item weights. `[ASSUMPTION: produced after the Test deadline so feedback does not leak to Students who have not taken the test]`
- Each piece of feedback quotes the part of the Student's answer it refers to, from the original text, and says plainly what is missing.
- Every fact about the Student's games matches the Decision log; feedback that fails this check is regenerated once and then left out, with a note to the Student.
- All AI assessments are ready within 24 hours of the Test deadline. `[ASSUMPTION: 24 hours]`
- The AI assessment contains no pass/fail result, and no letter unless the Indicative letter is turned on (FR-56).
- `[NOTE FOR PM]` The AI assessment stays outside the EU AI Act's high-risk category only while it is formative; see §6.2.

#### FR-55: Seeing the AI assessment
A Student gets an email when the AI assessment is ready and can read it in the product; Lecturers and Assistant lecturers can read it for every Student in their Classes.
- Every view states that the AI assessment is AI-generated, can be wrong, counts toward nothing and is not a grade.
- A Student can flag a piece of feedback with one click, and the Lecturer sees the flags. `[ASSUMPTION: one-click flag]`

#### FR-56: Indicative letter
A Lecturer can turn on the Indicative letter for a whole Class session; where it is off, each Student can turn it on for their own AI assessment. An Institution or Lecturer can also make it unavailable, for example if the data protection officer requires it. `[ASSUMPTION: this third setting]`
- The letter is derived from the total score by thresholds with defaults the Lecturer can change before the Individual test opens. Founder decision 2026-11-05 (A–F, thresholds a Lecturer setting). `[ASSUMPTION: default values set after the first Control test, because Interactive items are hard]`
- It is labelled as an AI-generated indication that is not a grade, wherever it is shown.
- A letter a Student turned on only for themselves is not shown to Lecturers. `[ASSUMPTION: hidden from Lecturers]`
- It never appears in the Completion export and never affects the Completion status. It appears in a Student report only if the Student adds it.

#### FR-57: Student downloads the report
A Student can download their Student report as a PDF once the Test deadline has passed, and until the data is deleted (FR-77), for example for approval or to upload to another application. Realizes UJ-8.
- A single Student report is ready within 30 seconds. `[ASSUMPTION: placeholder]`
- Students are told before the deletion date that they should download their report.

#### FR-58: Report content
The Student report holds, in Norwegian:
- the Student's name, the Class and Class session, the dates, and the time the report was generated;
- the Completion status, and whether an obligatory requirement is met;
- the Class game: Role, Weeks played, final Total cost, a week-by-week table for the Student's own Seat, and a chart of Orders, inventory and backlog for all four Roles plus customer demand, with AI players and Takeover Weeks marked;
- the Explanation, the key moments and the number of Debrief quiz attempts; answers to reflection questions on feelings are left out by default, and Students are told who reads them;
- the Replay: scenario, Total cost, and a chart;
- the Individual test: questions, the Student's answers including Interactive items as images with table alternatives, and the scores on answer-key and Interactive items;
- if the person downloading adds it, the AI assessment in its own section, labelled as AI-generated and not a grade.
- The AI assessment section is left out by default, because the report is meant for approval and for other applications. Founder decision 2026-11-05. `[ASSUMPTION: can be added]`
- Other Students appear by Role only, never by name, and their Explanations are never included.
- Steps not done are marked as not done.
- Every report states that it documents the Student's work and is not a grade.

#### FR-59: Lecturer downloads reports
A Lecturer or Assistant lecturer can download the Student report of any Student at any time, or all Student reports in a Class session as one ZIP file. The ZIP file never holds the AI assessment section.
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
- A human scores each long-answer and Adapted item with the Scoring guide without seeing the AI's score. `[ASSUMPTION: scored blind]` The product then shows both scores side by side, with exact agreement, agreement within one step, any systematic offset, compression of the scale, and agreement by answer length.
- beergame is the data controller for test students' data; they are told what it is for and consent. `[ASSUMPTION: controller and basis, to be checked with counsel]`
- A Control test can be run with the default Scoring guide or with a Lecturer's edited one, so an edited guide can be checked too. `[ASSUMPTION: the Admin runs it for a Lecturer on request in v1]`
- `[ASSUMPTION: test students are people outside the course; each plays a Class game and Replay, so Adapted items rest on a real Decision log]`

### 4.13 Insight, Class reports and Cross-class statistics

**Description:** The Lecturer can see everything that happened, from one Order to the whole class, and compare Class sessions over years. Realizes UJ-7, UJ-9.

#### FR-62: Game insight
A Lecturer or Assistant lecturer can open any Game (Class game or Replay) and see, per Week and per Seat: incoming order, incoming delivery, inventory, backlog, Order and cost; who played the Seat (Student or AI player, Takeover marked); and whether an LLM player's Order was replaced by the fallback.
- Charts of Orders, inventory and backlog for all four Roles plus customer demand.
- Links to the Students' Explanations and Debrief summaries.

#### FR-63: Student page for lecturers
A Lecturer or Assistant lecturer can open one Student and see their Class game, Explanation, Debrief summary, Debrief quiz attempts, Replay, Individual test and AI assessment on one page, with a link to the Student report.

#### FR-64: Class report
A Lecturer can see a Class report for a Class session: the funnel (FR-39); distribution of Total cost per Role; Order amplification per Role; the most common Detected patterns across Class games; Starting task results and the matching Individual test items; results per Individual test question; distribution of AI assessment scores, with a Core-only subscore next to the total, because Adapted items differ between Students; the share of Seats played by AI players.
- The Class report updates as Students progress.

#### FR-65: Cross-class statistics
A Lecturer can compare the Class sessions they have access to on the Class report measures, filtered by Game settings, AI mode, model, prompt version and Effort level, on Core-only scores.
- Class sessions that differ on any of these, or on question set, Item weights or Scoring guide version, are labelled as such in every comparison, and scores are called comparable only when the test and guide are the same.
- An anonymised aggregate of each Class session, over groups of at least 10 Students, survives deletion under FR-77, so next year's comparison still works. `[ASSUMPTION: aggregate survives]`
- Comparisons across Institutions show only anonymised aggregates over groups of at least 10 Students and are visible only to the Admin in v1. `[ASSUMPTION: threshold of 10]`

#### FR-86: All games side by side
After the Play deadline, Students can see an anonymised chart of every Class game's Orders per Role in their Class session, with their own Class game marked, so they can see whether all teams behaved alike. It opens for a Student once their own Debrief is done. Founder decision 2026-11-05. Realizes UJ-9.
- The Lecturer gets a view of all Class games that can be shown in a plenary.
- No names appear, and no Class game is ranked.

#### FR-88: Game data export
A Lecturer can export a Class session's week-by-week Game data as a CSV file. Founder decision 2026-11-05.
- The file holds no AI assessments.

### 4.14 Rerun

#### FR-66: New class session from an earlier one
A Lecturer can create a new Class session in the same or another Class by copying an earlier Class session's settings (Game settings, AI mode, Debrief mode, Replay scenario, question set and Item weights, Scoring guide, Inactivity limit), then adjust them. Realizes UJ-9.
- Dates, Lab hours and Roster are not copied. A fresh seed is drawn unless the Lecturer keeps the old one.

### 4.15 Decision log and AI operations

**Description:** The evidence for issues #6, #8, #9, #10 and #11 becomes a by-product of normal use.

#### FR-67: Decision log
The system stores every Order in every Game with: Game, Week, Seat, Role, the state the Seat saw, the Order, and whether a Student or an AI player placed it.
- For every Seat it stores the Rule-based reference Order for that Week, also for Students' Seats, so SM-1 can be computed.
- Other LLM calls (Debrief, Debrief quiz explanations, Adapted items, AI assessment) are logged with model, endpoint and prompt version, tokens and cost.
- For LLM players it also stores model identifier (exact version), provider, endpoint and quantisation, prompt version, Effort level, seed and temperature where supported, tokens, cost, response time, the number of retries, whether the fallback replaced the Order, the two reference Orders of the Play guard (FR-79), and the Week a Seat was switched.

#### FR-68: Model pinned per class session
The Admin selects the model for a Class session after a check on all-AI test runs. All LLM use in a Class session and its Replays (players, Debrief, AI assessment) stays on the same model version, endpoint and prompt versions for the whole Class session, with no automatic router fallback, because Institutions must know every sub-processor.
- Reports show the Share of LLM Orders per Game, and record when a cost limit or Play guard switch took effect.
- The Admin can freeze a model across several Class sessions, so no model change happens during a learning study.

#### FR-69: AI spending controls
The Admin can see AI cost per Class session, per Game and per day, and set a cost limit per Class session.
- When a Class session reaches its cost limit, its LLM players switch to Rule-based players for the rest of the Class session, and the Lecturer is notified. Budget is reserved for the Debrief and the AI assessment, which have no Rule-based form; if that also runs out, the Debrief runs from code (FR-44) and the Admin decides on the AI assessment. `[ASSUMPTION: reservation rule]`
- The Admin gets an alert when daily AI spend exceeds a set amount.

#### FR-70: Plausibility rating
At the end of the Replay, and after any Class game with AI players, each Student is asked one optional question about how believable the AI players' ordering felt (five-point scale).
- Results are shown per AI mode in the Class report and Cross-class statistics (SM-3).

#### FR-71: Pseudonymised export for evaluation
The Admin can export the Decision log, Starting task results, Explanations and Individual test answers of chosen Class sessions in pseudonymised form (Students replaced by stable pseudonyms) for evaluating AI players and learning outcomes, where the Institution has agreed.
- The data stays personal data: it follows the retention in FR-77 and the Institution's instruction, and the agreement states who is controller for this evaluation.

### 4.16 Language and devices

#### FR-72: Norwegian interface
All screens, emails, Debriefs, Debrief quiz, Individual test, AI assessments and Student reports are in Norwegian (bokmål). `[ASSUMPTION: bokmål only in v1]`

#### FR-73: Mobile-first, classroom laptop equal
Every Student flow (registration, Starting task, Class game, Debrief, Debrief quiz, Replay, Individual test) works on a phone from 360 pixels wide, on a tablet and on a laptop browser.
- Long-answer questions in the Individual test are comfortable to write on a laptop; on a phone the Student is advised to use a larger screen. `[ASSUMPTION: this advice]`
- Lecturer overview and Game insight are designed for laptop first and remain usable on a tablet.

#### FR-74: Group debrief on one screen
A Group debrief can be shown on one shared screen (for example a laptop in a Lab hour), with each joined Student still answering on their own device.

### 4.17 Data rights

#### FR-75: Student data access
A Student can see all data the product stores about them, for example account and profile, Orders, Explanations, reflection and follow-up text, Debrief summaries, Debrief quiz attempts, Individual test answers, AI assessments and the Indicative letter. The Student report covers most of it.

#### FR-76: Deletion on request
The Admin can delete a User and their personal data on the Institution's instruction; their Seats remain in Game data as anonymous Seats so other Students' Games stay intact.

#### FR-77: Retention
Student personal data in a Class session is deleted automatically a set period after the Test deadline, configurable per Institution. `[ASSUMPTION: default course end plus six months, for reports and the course's own approval; an Institution can extend it]`

## 5. Cross-Cutting Non-Functional Requirements

- **NFR-1 Responsiveness.** A Week advances for connected Students within 2 seconds after the last Order (excluding AI player thinking time). Pages a Student uses during play load within 3 seconds on a 4G connection.
- **NFR-2 AI player latency.** Each Effort level has a per-attempt timeout and a per-Order time budget, retries included, and a Student waits at most that budget for an AI player; slower Orders are replaced by fallback (FR-32).
  - The research's only figure is a placeholder gate of p95 at or below 8 seconds with reasoning off, and six attempts within 8 seconds leave about 1.3 seconds each, so the values come from the prototype. `[ASSUMPTION: values set after the prototype, issue #8; the coaching question on acceptable waiting time is still open]`
- **NFR-3 Scale.** One Class session supports at least 400 Students (100 Class games); a full Lab hour with 250 Students playing at the same time works without degradation, shown by a load test that includes the LLM provider's rate limits; rate-limit errors do not cause mass fallback. The platform supports at least 5 such Class sessions at once. `[ASSUMPTION: launch scale]`
- **NFR-4 Reliability.** No Student who has ordered waits longer than the Inactivity limit for an absent Student, unless the Class game is paused, and no Class game stalls because an AI provider fails. Availability during Lab hours is at least 99.5%. Game state is never lost once a Week has been shown. During Lab hours there is a named contact with a stated response route.
- **NFR-5 Reconnection.** A Student who loses connection resumes at the current Week on any device without action from others.
- **NFR-6 Accessibility.** Student and Lecturer screens meet WCAG 2.1 AA. Charts have text or table alternatives. Student reports are tagged PDFs with table alternatives for charts. Role and status are never shown by colour alone. An accessibility statement and conformance report are available to Institutions.
- **NFR-7 Security.** Access is checked against account roles on every request (FR-5). Data encrypted in transit and at rest. Audit log for Admin actions. Student reports are generated only for a logged-in User allowed to see them, and download links expire.
- **NFR-8 Observability.** Per Class session the Admin can see error counts, fallback rate, AI response times and AI cost.
- **NFR-9 Correctness.** Game arithmetic is verified on every finished Game (FR-29). Every number the AI shows a Student or Lecturer is drawn from computed facts (FR-44, FR-50, FR-53).
- **NFR-10 Email delivery.** Invitations and notifications are sent from an authenticated domain; bounces are reported to the Lecturer (FR-8).

## 6. Constraints and Guardrails

### 6.1 Privacy and data protection

- The Institution is the data controller for Student data; beergame is the processor and signs a data processing agreement before any Institution's Students are invited, including the founder's own Institution for the pilot.
- No LLM provider receives names, emails or student numbers from the system. Seats are identified by Role and pseudonymous IDs.
- All free text sent to an LLM (Explanations, reflection and follow-up text, test answers) is first filtered for the whole Roster's names, emails and student numbers. This reduces the risk but does not remove it, and free text stays personal data; the DPIA pack records the remaining risk. Quotes shown to the Student come from the original text.
- LLM providers and routers are used only under terms that exclude training on the data, with zero retention and data collection denied, and they are listed as sub-processors. EU-region inference is the default. A US provider must be listed under the EU–US Data Privacy Framework or covered by standard contractual clauses with a transfer impact assessment. Providers processing in a country with neither, such as DeepSeek's own API, are not used. Providers stay swappable.
- The product supplies a DPIA and risk-assessment support pack (data flows, sub-processors, risks, mitigations) for each Institution; a DPIA is mandatory for evaluating learning in Norwegian higher education. The pack puts the question of legal basis to the Institution, especially for an Obligatory class session, where consent is weak.
- Retention follows FR-77, for pseudonymised data too (FR-71).

### 6.2 AI regulation and examination law

- AI players, Debrief narration, follow-up answers, Debrief quiz explanations and the AI assessment are disclosed as AI from first interaction, and AI-generated text is marked (EU AI Act Art. 50, applies in the EU from 2 August 2026).
- v1 has no formal grading. The Debrief, Debrief quiz, Replay feedback and AI assessment are formative and feed no grade in the product.
- The intended purpose of the AI assessment is formative feedback. The Commission's draft guidelines (May 2026; final version expected end of 2026) put formative feedback outside EU AI Act Annex III 3(b), but put a learning assistant whose reports inform the teacher's grades inside it, and human review does not change that.
- v1 therefore states the purpose in the product, the terms (the Institution does not grade from it) and every Student report; keeps AI scores out of the Completion export (FR-60) and the ZIP file (FR-59); leaves the AI assessment out of the Student report by default (FR-58); and allows the AI assessment to be switched off (FR-61).
- Lecturers can still read it per Student (FR-55, FR-63), which is why the data protection officer's review is a pilot precondition (§10).
- An Obligatory class session (FR-17) rests on the Completion status only: system events, and for the Debrief quiz an answer key. This is because the regulatory research treats AI evaluation behind a pass/fail gate for exam eligibility as a grey zone to be handled as summative.
- `[NOTE FOR PM]` A course that grades or approves from the AI assessment could pull it into the high-risk category. The Indicative letter (FR-56) makes that more likely, since a letter reads as a grade; the research did not assess such a letter specifically. Check both against the final guidelines and with the Institution's data protection officer before the pilot.
- Formal assessment under the Universities Act (examiners appointed by the Institution, impartial assessment) stays outside the product in v1, under the Institution's own process.
- No emotion recognition from voice or other biometric data; no AI proctoring.
- Product and sales text make no learning or bullwhip claim until it has been measured.
- Formal grading with an AI proposal, planned for v2, would likely be high-risk (obligations apply in the EU from 2 December 2027; Norwegian bill expected spring 2027). See addendum §V and §R.

### 6.3 Cost

- AI cost per Game is at most USD 0.10 including provider fees and retries, at EU prices. The research supports this limit only for a small model with thinking off or low: at about 2,000 output tokens per call a Game costs about USD 0.15–0.27 (modelled, addendum §A), so only Effort levels measured inside the limit are offered (FR-78). `[ASSUMPTION: issue #8 must verify]`
- AI cost per Student per Class session (share of the Class game, Replay, Debrief, Debrief quiz, Adapted items, AI assessment) is at most USD 0.50. `[ASSUMPTION: from the brief; only the game load and one debrief call are modelled]`
- FR-69 enforces a limit per Class session and falls back to Rule-based players rather than stopping play.

### 6.4 Content and intellectual property

- All game graphics, texts, Debrief content and test questions are original. Third-party classroom materials for the Beer Game may inform parameters but are not copied; at least one such licence forbids online hosting and redistribution.

## 7. Non-Goals (Explicit)

- Not an open consumer product: no public sign-up, free tier, individual subscriptions or in-app payment in v1.
- Not a general simulation platform: only the classic four-Role Beer Game in v1; no custom topologies or other games. The Lecturer does set the Game settings and the Replay scenario's settings freely (FR-12, FR-49).
- No Feide login, Canvas/LTI or other LMS integration in v1.
- No communication between players in the product in v1, beyond agreeing a time (FR-22, FR-89), and no Student-to-Lecturer chat. (v2: Students replay in the same group with communication.)
- No formal grading of any kind in v1: no examiners, grades or appeals (planned for v2, §8.3). The AI assessment and its optional Indicative letter are never a grade.
- No AI proctoring, emotion inference or monitoring of Students outside the product.
- No Student-facing ranking of Class games, and no prizes.
- The flow is fixed: a Lecturer cannot leave out the Debrief, Replay or Individual test in v1.
- No native mobile apps.
- No language other than Norwegian in v1.
- No bit-exact reproducibility of LLM players; reproducibility comes from Rule-based players and the Decision log.
- No reinforcement-learning AI players in v1.

## 8. MVP Scope

### 8.1 In Scope

- Accounts by Invitation; roles Admin, Lecturer, Assistant lecturer, Student; Admin area (FR-1 to FR-5).
- Classes, Roster upload from Canvas export, Invitations with expiry and manual override, co-Lecturers, Assistant lecturers (FR-6 to FR-10).
- Class session setup with classic defaults, adjustable Game settings, Demand pattern, AI mode, Debrief mode, Obligatory class session, dates and Lab hours, Information visibility and capacity, Lecturer test Game (FR-11 to FR-19, FR-83, FR-87).
- Random allocation into Class games of up to four with random Roles, optional student choice, rules briefing and Starting task (FR-20 to FR-22, FR-84, FR-85).
- Simultaneous-order gameplay with hidden end and a clear "waiting for" view (FR-23 to FR-29).
- LLM players by default, Rule-based players per Class session, schema-checked Orders with retries and fallback, disclosure, Effort level, Play guard (FR-30 to FR-34, FR-78, FR-79).
- Automatic Takeover after the Inactivity limit, manual Takeover, Reclaim, Pause, Play deadline playout (FR-35 to FR-38, FR-89).
- Lecturer overview and one-way Messages (FR-39, FR-40).
- Group and Personal debrief with the Explanation inside it, Debrief quiz (FR-41 to FR-47).
- One Replay with a Replay scenario and a short AI walkthrough (FR-48 to FR-50).
- Individual test with weighted Core, Interactive and Adapted items and one Scoring guide (FR-51 to FR-53, FR-80, FR-81).
- Non-counting AI assessment with optional Indicative letter, downloadable PDF Student reports, Completion export, Control test (FR-54 to FR-61, FR-82).
- Game insight, Class report, Cross-class statistics, all games side by side, Game data export, rerun (FR-62 to FR-66, FR-86, FR-88).
- Decision log, model pinning, spending controls, plausibility rating, pseudonymised export (FR-67 to FR-71).
- Norwegian, mobile-first, data rights and retention (FR-72 to FR-77).

**Scope kind and build order.** This is a problem-solving MVP: the first course must work from invitation to report. All of the above is in v1, in this order, so the risky parts come first:

1. The prototype (§10.1), game engine and AI players.
2. Accounts, Class session setup, allocation and the Lecturer overview.
3. Debrief, Debrief quiz, Replay, Individual test and AI assessment.
4. Student report, Completion export and Class report.
5. If time is short before the pilot, these wait until after it: FR-21, FR-65 across Institutions, FR-66, FR-83, FR-87, FR-88 and capacity in FR-12. `[ASSUMPTION: this order]`

`[NOTE FOR PM]` The adversarial review argues for cutting further, and these reverse founder decisions, so none is applied: (1) Rule-based players in the first pilot with LLM players behind the prototype, since a full class has few AI Seats outside the Replay; (2) FR-83, capacity and free Replay settings, since no pilot Lecturer needs them and content is calibrated on Classic; (3) FR-56, FR-53 and editing in FR-81. Revisit when the course date and build estimate are known.

### 8.2 Out of Scope for MVP

- Feide and Canvas/LTI. `[NOTE FOR PM]` The research says these are the main ways into Norwegian higher education; revisit before the second paying Institution.
- Communication between players and group Replays (v2, founder-requested).
- English and other languages (v2).
- A dedicated information-sharing round (a classic follow-up; v2 candidate). A Lecturer can already approximate it through Information visibility in the Replay scenario.
- A computed "what if I had ordered differently?" in the Debrief (v2 candidate).
- Institution admin role (the Admin handles Institutions in v1).
- Billing, licences and invoicing in the product.
- Lecturer-authored questions beyond excluding questions and changing Item weights.
- PDF export of the Class report.
- Voluntary extra Replays. `[NOTE FOR PM]` The founder removed them from v1 on 2026-11-05, so v1 tests one repetition, not many, and the brief's kill bar (median solo Replays above 3) cannot be measured. SM-10 collects a first signal for the v2 decision.

### 8.3 Planned for v2: formal grading

Founder decision 2026-11-05: everything concerning formal grading moves to v2. The design narrated so far is kept in addendum §V and is not built in v1:

- Examiner role, with the course lecturer and an external examiner per Student, registered by the Lecturer.
- AI proposal of a grade, advisory only, reviewed by the Examiners.
- Independent proposed grades, a follow-up until the Examiners agree on one joint grade, and tracking of the statutory grading deadline.
- Grading scale (A–F or Pass/Fail) and thresholds for formal grades, set by the Lecturer.
- Release of grades with email notice, grade export, appeals and re-grading, and anonymous grading by candidate number.

## 9. Success Metrics

*All thresholds are placeholders. The founder writes down the final values before the first Student places an Order, and they are not changed after that.*

**Primary**
- **SM-1 Second-round behaviour.** For each Student, the standard deviation of their Orders is divided by that of the Rule-based reference Orders for the same Seat and Weeks, after the Guided Weeks and before the final Weeks. SM-1 is the share of Students whose ratio is lower in the default Replay scenario than in their Class game. Validates FR-48 to FR-50.
  - Constant Orders, Students with Takeovers and Students with AI neighbours in both Games are left out.
  - Scripted no-learning players run through both scenarios in the prototype set the baseline, and the target is above it; `[ASSUMPTION: at least 60%, or the baseline plus 15 points if that is higher]`.
  - With no comparison group this is a signal, not proof. How well a Student accounts for the Supply line is reported as exploratory, since nothing validates it as a measure.
  - Replaces the brief's kill bar, which needs voluntary Replays (§8.2).
- **SM-2 Explanation gain.** Share of a random sample of 60 Students whose long answers in the Individual test explain the mechanism (delays, Supply line, own Orders). It compares the Explanation with the test item asked in the same words (FR-52). Target: at least 60%, and at least double the share in the same Students' Explanations. `[ASSUMPTION: sample, second scorer and targets]` Validates FR-41, FR-44, FR-52, FR-85.
  - The founder scores with the Scoring guide's criteria on a pseudonymised export (FR-71), not the AI assessment, with a second scorer on 15 of them.
  - The gain is an upper bound: the after-text follows the Debrief and Debrief quiz and may use outside AI tools. v1 tests whether Students reach a level, not whether the design caused it.
  - The Starting task repeat is the unprompted check next to it.
- **SM-3 AI players fit for teaching.** The Play guard (FR-79) protects play while a Class session runs, not its teaching value, and there is no end-of-pilot rule that makes Rule-based players the default. Validates FR-30 to FR-34, FR-78, FR-79. Issues #8, #9, #11.
  - (a) Share of LLM Orders replaced by fallback after the 5 retries (FR-32), and share of Seats switched by the Play guard (FR-79): both reported per Class session, no fixed limit in v1. `[ASSUMPTION: the earlier 2% bound is replaced by the retry rule; the founder may still want a limit]`
  - (b) Run-to-run variation (coefficient of variation) of chain Total cost on fixed all-AI test runs: reported, with the target set after the prototype. The research found 12% on one model with a spend cap and budget rule; the retry rule in FR-32 has no published figure. `[ASSUMPTION: not yet discussed with the founder]`
  - (c) Plausibility rating (FR-70): median at least 4 of 5. `[ASSUMPTION: not yet discussed with the founder]`

**Secondary**
- **SM-4 Completion.** At least 95% of registered Students submit the Individual test by the Test deadline, and Students place at least 80% of Orders after the Guided Weeks in Class games. `[ASSUMPTION: 80% and 95%]` Validates FR-36 to FR-38, FR-89.
- **SM-5 Setup time.** A first-time Lecturer creates a Class session with defaults in under 10 minutes; uploading a Canvas export and sending Invitations takes under 5 minutes. Measured with one or two outside lecturers in the rehearsal, since the founder designed the product. Validates FR-7, FR-8, FR-11.
- **SM-6 AI cost.** At most USD 0.10 per Game with AI Seats, including every Replay, and USD 0.50 per Student per Class session. Validates FR-69.
- **SM-7 AI assessment quality.** In a Control test (FR-82) of at least 30 tests before the pilot, including Adapted items, scored by the founder alone with the Scoring guide, the AI's score for long answers is within one step of the guide's five-step scale for at least 80%, with exact agreement of at least 50%; no feedback cites a fact that contradicts the Decision log. `[ASSUMPTION: 30 tests; 80% and 50% are fixed before any data, since no published benchmark exists; test students' answers resemble real Students' answers well enough]` Validates FR-54, FR-81, FR-82.
  - The founder also reports any systematic offset and compression.
  - If this is not met, the AI assessment is switched off until it is.
- **SM-8 First external Institution.** One paying Institution other than the founder's own, using a Class session end to end.
- **SM-9 Report use.** At least 50% of Students download their Student report, and a Lecturer can produce every report for a Class session without help. `[ASSUMPTION: placeholder]` Validates FR-57 to FR-59.
- **SM-10 Appetite for repetition.** Share of Students who answer yes to wanting another round (FR-50). No target in v1; it is a preference signal that informs whether v2 adds voluntary Replays, and it does not validate the repetition half of the bet.
- **SM-11 Time to play.** Median time per Week and for a whole Class game, measured in the rehearsal, so a Lecturer can size Lab hours. Target set after the prototype. Validates FR-23 to FR-26.

**Counter-metrics (do not optimise)**
- **SM-C1 Total cost.** Lower Total cost in Replays is not learning; the evidence suggests performance and understanding dissociate. Counterbalances SM-1.
- **SM-C2 Average AI assessment score.** A generous AI pleases Students and teaches nothing, and a harsh or compressed one misleads them; studies point in both directions. Rising scores are not evidence of learning. Counterbalances SM-7.
- **SM-C3 AI player skill.** A smart LLM player is acceptable and is not tuned down to imitate Students, but near-optimal play would remove the bullwhip the game exists to show. The Play guard (FR-79) keeps LLM play away from near-optimal. Counterbalances SM-3.
- **SM-C4 Debrief quiz attempts.** Fewer attempts is not better learning if questions get easier. Counterbalances SM-2.
- **SM-C5 Takeovers.** Lowering the Inactivity limit makes games finish faster but replaces Students with AI players. Counterbalances SM-4.
- **SM-C6 Completion under obligation.** An Obligatory class session raises completion without showing that the exercise is valuable. Counterbalances SM-4.

### 9.1 Learning measurement in the first Class session (issue #6)

The founder has no capacity for a split-group study in the first semester. The pilot collects evidence without changing the course design:

- The Starting task (FR-85) is the before-measure on stocks and flows and is repeated in the Individual test, with one item on unseen demand.
- Every Student's Explanation (FR-41), written after playing, is compared with the long answers in the Individual test, both scored with the same criteria. `[ASSUMPTION: same criteria score both texts, blind where possible, though long answers can give themselves away by citing the Replay]`
- Behaviour in the Class game and the Replay is compared (SM-1).
- The model is frozen for the Class session (FR-68). Games with a low Share of LLM Orders are left out. `[ASSUMPTION: below 90%]`
- The pilot holds Debriefs until all Class games have ended (FR-42), to protect the Explanations.
- In the rehearsal the founder also compares the Debrief with a scripted one and reads narration for causal errors.

v1 has no delayed measure, so it cannot show retention. The pilot has one AI mode and one Replay, so it cannot show that LLM players teach better than Rule-based players or that repetition adds to one good Debrief. A later Class session can compare groups by varying the Debrief or the AI mode, using the same instruments.

**What the results lead to.** SM-1 and SM-2 are conditions for launch to further Institutions (§10). Founder decision 2026-11-05. The table is a Founder accepted recommendation 2026-11-05:

| SM-1 | SM-2 | Action |
|---|---|---|
| Met | Met | Launch can go ahead. |
| Met | Missed | The second round works, the explanation does not. Rework the Debrief and test, and rerun before launch. |
| Missed | Met | The explanation works, the second round adds little. The brief's fallback applies: a Debrief-centred product with simple bots, not a stronger bot engine. |
| Missed | Missed | No launch. The thesis is re-examined before more is built. |

Architecture therefore keeps the Debrief separable from LLM players.

## 10. Rollout

- **Before architecture locks:** two or three of the lecturer interviews (issue #7), since all setup choices so far rest on one lecturer. `[ASSUMPTION]`
- **Pilot:** one Class session in the founder's own course (about 250 Students). Preconditions:
  - written clarification from the Institution of the legal entity behind the product, conflict of interest, ownership, who is controller for the evaluation, the legal basis, and making it obligatory, with someone other than the founder holding the pseudonym key;
  - a named provider, plan, region, terms and rate limit, confirmed in writing;
  - data processing agreement with the founder's Institution;
  - DPIA support pack;
  - the data protection officer's review of the AI assessment's classification, the Indicative letter included;
  - WCAG 2.1 AA testing evidence;
  - prototype evidence for the retry rule (FR-32), the Play guard (FR-79) and SM-6 on all-AI test runs (issues #8, #20);
  - one rehearsal Class session with test students and one or two outside lecturers, measuring run-to-run variation, plausibility and time to play, and trying the Individual test items;
  - one Control test (FR-82);
  - one attempt with a general AI tool on the Individual test.
- **If the Control test does not meet SM-7:** the pilot runs with the AI assessment switched off (FR-61).
- **Dates:** the plan works backwards from the course date, with a go or no-go date for each precondition. If the date is at risk, the fallback is §8.1's cut list and, at the last resort, Rule-based players and the code-only Debrief, since missing the course costs a year of evidence. `[ASSUMPTION: this fallback]`
- **Launch to further Institutions:** requires:
  - SM-7 met, the pilot meeting SM-1, SM-2, SM-4 and SM-5, and the founder accepting the SM-3 results;
  - 5 to 8 lecturer interviews held (issue #7);
  - a Norwegian Lecturer guide with original intro and Debrief slides ready;
  - the competitor check rerun with Nordic searches and issues #1 and #4 closed;
  - WCAG 2.1 AA conformance report available;
  - licences kept under the Norwegian procurement threshold (NOK 500,000 excluding VAT) where possible.

### 10.1 The prototype

The prototype comes first, because seven requirements depend on it (FR-32, FR-78, FR-79, NFR-2, SM-3, SM-6, SM-11). It covers issues #8, #9, #11, #19 and #20.

- **It answers:** tokens, cost, retries and waiting time per Order at each Effort level, on endpoints that meet §6.1; how often the LLM player leaves the Play guard's band, with the distance measure, window and near-optimal reference settled; run-to-run variation; the Rule-based player's parameters from the primary source.
- **It passes when:** at least one model and Effort level costs at most USD 0.10 per Game with AI Seats, keeps a time budget a Student can accept, and stays inside the band in most Seats on Classic settings and the default Replay scenario, with no more than a set share of Seats switched. Automated all-AI test runs provide this. `[ASSUMPTION: pass lines; the numbers are written down before it runs]`
- **If it fails:** the pilot runs with Rule-based players as the AI mode and keeps the Debrief. This is a readiness rule before the pilot, not the end-of-pilot rule the founder rejected. Founder accepted recommendation 2026-11-05.
- **In parallel:** accounts, setup and the game engine do not depend on it.

### 10.2 Deliverables that are not code

| Deliverable | Owner | Needed by |
|---|---|---|
| DPIA and risk-assessment support pack, data processing agreement | Founder, with the Institution | Pilot |
| Question set, Debrief quiz, Starting task, Scoring guide (issue #16) | Claude drafts, founder approves | Rehearsal |
| Accessibility statement and testing evidence | Founder | Pilot |
| Lecturer material on AI (FR-33) | Founder | Pilot |
| Lecturer guide and slides, conformance report | Founder | Launch |

## 11. Risks

- **AI players do not behave like human players** (too erratic or too good). Mitigation: schema-checked Orders with retries and fallback (FR-32), the Play guard (FR-79), Rule-based players (FR-15).
- **The AI assessment is used as a grade anyway**, which could make it regulated high-risk AI. Mitigation: the Indicative letter can be made unavailable (FR-56), labels in the product and in every Student report, reports without the AI assessment section by default (FR-58), Completion export without AI scores (FR-60), switch-off (FR-61).
- **The AI assessment is wrong and no human has checked it.** Mitigation: quotes from the answer, facts checked against the Decision log, Control test (FR-82, SM-7), plain statement that it can be wrong and counts toward nothing, switch-off (FR-61).
- **The Debrief invents causes or explains the log wrongly.** No evidence exists on how accurately an LLM explains simulation logs. Mitigation: causes only from Detected patterns and computed facts (FR-44), a statement that it can be wrong, the founder's reading in the rehearsal, a code-only fallback.
- **One good Debrief may be enough**, which would make the Replay over-engineering. Mitigation: SM-10, the later comparison in §9.1, and the fallback there.
- **Students share the answer.** Class games finish days apart with the same demand and length, and groups know each other. Mitigation: the rule in FR-84, neutral naming, the hold option in FR-42, a Replay that varies. This cannot be stopped entirely.
- **The founder has several roles.** The same person is Lecturer, Admin, product owner and scorer of the evidence, and can make their own product obligatory for their own Students. Mitigation: the Institution's clearance (§10), a second scorer on SM-2, and targets fixed in advance. Whether a Student who objects can get an alternative is for the Institution to decide (open question 7).
- **Without a grade, Students skip the steps.** The flow only works if Students finish it. Mitigation: the Lecturer can mark the Class session as obligatory (FR-17).
- **Groups never meet for the Group debrief.** Mitigation: fallback to Personal debrief (FR-43).
- **Debriefs reveal the Demand pattern to Students still playing.** Mitigation: Lecturer option to hold Debriefs (FR-42).
- **Students use outside AI tools in the Individual test.** This weakens the learning evidence (SM-2, SM-7) more than it threatens fairness, now that the test does not count toward a grade. The test is unsupervised and open for days, and studies of unsupervised written exams show AI answers often go undetected. v1 relies on Interactive items (FR-80) and Adapted items tied to the Student's own games. No evidence shows that Interactive items stop these tools, which can read screenshots, so the founder tries a general AI on the test before the pilot (open question 6).
- **Many Takeovers hollow out the Class game.** Mitigation: Pause; Lecturer sees Takeovers in the Lecturer overview; Inactivity limit adjustable; Reclaim.
- **Groups pause too long and meet the deadline unfinished.** Mitigation: deadline reminders, the waiting view, and the Lecturer overview of paused games.
- **AI cost runs away with long reasoning or retries.** Mitigation: only measured Effort levels (FR-78), limit per Class session with fallback (FR-69).
- **Digital play is seen as weaker than the board game.** One small, self-selected study has online-only play scoring lowest. Expect it as a sales objection.

## 12. Open Questions

1. Product name, which must not reveal the game before the Debrief (FR-84).
2. Prices for Institutions and whether Students ever pay directly.
3. v2: compliance path for formal grading with an AI proposal: meet high-risk obligations, or have Examiners grade without it? When does Norwegian law apply?
4. Does the final Commission guidance keep the AI assessment and the Student report outside Annex III 3(b), and do pass/fail obligatory activities count as summative? Check when it is published (expected end of 2026).
5. Is a spread of 2 around the Class game's mean the right default demand variance for the Replay (FR-49)? Check against the first pilot's Replay results.
6. How well does a general AI tool do on the unsupervised Individual test, Interactive items included, and how far can SM-2 be trusted as a result? Answered by trying one on the test before the pilot.
7. How must the obligatory requirement be described in the course plan, and does it count as an exam-eligibility requirement under the Universities Act § 11-4? Does the 80% rule raise an automated-decision question under GDPR Art. 22? The Lecturer and the Institution decide.
8. Which other applications will receive the Student report, and must they be able to verify that it is authentic?
9. How do other lecturers debrief, compare teams, pace the game and buy, and do they need identical results across Class sessions (interviews, issue #7)?
10. Which LLM and provider meet the privacy constraints in §6.1 and the cost in §6.3 (issues #8, #9)?
11. Should the Admin role later split into platform admin and institution admin?
12. AI player quality: how long may a Student wait for an AI player (NFR-2), and how much run-to-run variation is acceptable (SM-3b)? Settled by the prototype, §10.1 (issues #8, #9, #11, #19).
13. Play guard (FR-79): how the near-optimal reference is computed, how the 95% and 5% limits are measured on weekly Orders, over how many Weeks, what counts as a large deviation under changed Game settings, and whether the guard needs changes after the pilot (issue #20).
14. What does the founder see in the course today: how is the game and debrief run, and what could earlier students explain? This is the baseline for SM-2.
15. Market size: how many courses run this exercise, and where?

### 12.1 Triage

- **Blocks architecture:** none left open. Pause, Takeover, Reclaim, playout, fallback scope, the dropped Order bound and the guard's switch are decided; time budgets are settled by the prototype.
- **Blocks the pilot:** questions 4, 6 and 7, and the prototype.
- **Blocks launch:** questions 2, 8, 9, 10 and 15.
- **For v2:** question 3.
- **Safe defaults:** every remaining `[ASSUMPTION]` in §13 is a default the build can start from and change later, unless named above.

## 13. Assumptions Index

- FR-4 — Login by email and password.
- FR-5 — Assistant lecturers see AI assessments.
- FR-7 — Canvas export accepted without editing; format to be confirmed.
- FR-10 — Lecturers can invite Assistant lecturers.
- FR-12 — Delays 1 to 3 Weeks and other ranges; capacity design.
- FR-83 — Backlog shown too.
- FR-15 — No-LLM path.
- FR-17 — Share of Weeks required, default 80%; make-up route; minimums for completion; no approval action in the product.
- FR-18 — 24-hour deadline reminders; the 7-day Test window counts from the Debrief deadline; deadline rules; lock points.
- FR-19 — Lab hours emailed on creation.
- FR-22 — Scheduling aid with no free text.
- FR-27 — Turn notifications after 2 hours and 4 hours before Takeover.
- FR-32 — Time budgets from the prototype; range violations handled like schema failures.
- FR-33 — Rule-based player ignores neighbour numbers.
- FR-78 — Effort levels and default set after prototype testing.
- FR-79 — Play guard limits (95%, 5%) read from the founder's wording; what counts as large under changed settings.
- FR-36 — Start of the clock; shorter limit only for games marked as in the room.
- FR-41 — Explanation comes before the demand reveal.
- FR-42 — Debriefs open by default.
- FR-43 — Fallback to Personal debrief 48 hours after the Class game ended; step control.
- FR-44 — Debrief moments chosen by rules; template approach for causes; code-only fallback; path for few Orders.
- FR-45 — Structured Debrief with bounded follow-up.
- FR-46 — No limit on retries; questions may be reshuffled.
- FR-48 — Replay in the same Role.
- FR-49 — Default Replay demand spread of 2; step Week 5 to 12; 30 to 40 Weeks; no Guided Weeks. §4.10 — Changing the run makes it harder.
- FR-51 — Unsubmitted answers submitted automatically at the Test deadline; no retakes.
- FR-52 — Default weights set when the question set is written.
- FR-80 — Interactive items scored by computed rules; table and number entry built before drawn items; best on a laptop.
- FR-81 — Five-step scale; edits possible until the Test deadline; one version scores the whole Class session.
- FR-54 — AI assessment produced after the Test deadline, within 24 hours.
- FR-55 — One-click flag on feedback.
- FR-56 — Default letter thresholds set after the first Control test; a letter can be made unavailable; a letter a Student turned on is hidden from Lecturers.
- FR-57 — A single Student report ready within 30 seconds.
- FR-58 — AI assessment section can be added.
- FR-59 — ZIP file for 250 Students ready within 10 minutes.
- FR-82 — Human scoring blind; controller and basis; Admin runs Control tests in v1; test students are people outside the course who play a Class game and Replay.
- FR-65 — Anonymisation threshold of 10; aggregate survives deletion; cross-Institution view for the Admin only.
- FR-69 — Budget reservation rule.
- FR-72 — Bokmål only.
- FR-73 — Long answers best on a laptop.
- FR-77 — Retention default of course end plus six months.
- §1 — One published account of decline is a signal, not a trend.
- §2.2 — Higher education only.
- NFR-2 — Time budgets from the prototype.
- NFR-3 — 400 Students per Class session, 5 concurrent Class sessions.
- §6.3 — USD 0.10 per Game to be verified; USD 0.50 per Student from the brief.
- §8.1 — Build order.
- §9 SM-1 — Measure and target for second-round behaviour.
- §9 SM-2, §9.1 — Sample, second scorer, targets and blind scoring; Share of LLM Orders below 90%.
- §9 SM-3 — 2% bound dropped, variation and plausibility targets not yet confirmed.
- §9 SM-4 — 80% and 95%.
- §9 SM-7 — 30 tests, thresholds fixed in advance, test students' answers resemble real ones.
- §9 SM-9 — Report use placeholder.
- §10 — Interviews before architecture locks; last-resort fallback for the course date; §10.1 prototype pass lines.
