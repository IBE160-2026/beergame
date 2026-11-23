import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { type Browser, type BrowserContext, expect, type Locator, type Page, test } from "@playwright/test";

import { nb } from "../../src/copy/nb";
import { answerTo, demoContext, latestMail, nextMail, untilHydrated } from "../support/auth";

/**
 * The Key User Journeys UJ-1 … UJ-9 (PRD §2.3) as one whole course, end to end on the local stack
 * (`npm run e2e:journeys`). One Class, fresh people made through the product's own flows: the
 * demo Admin invites a Lecturer, the Lecturer builds a Class from a roster file, five Students
 * register, four of them play one Class game to its end in four browser contexts, and the course
 * runs on through Debrief, Replay, the Individual test, the AI assessment, the reports and the
 * Class report. What a person does is done through the UI; the local dev routes under `/api/dev/`
 * stand in only for time passing (the lock at the Start date, a limit running out, a deadline).
 *
 * The tests are serial and share the state below: a failed journey stops the ones after it.
 */
test.describe.configure({ mode: "serial" });

const CSRF = { "X-Requested-With": "olspillet" };
const PASSWORD = "journey-passord-1";
const TAG = `${Date.now() % 1_000_000}${Math.floor(Math.random() * 100)}`;
const SHOTS = path.join(__dirname, "..", "..", "..", ".docs", "implementation-artifacts", "screenshots", "journeys");
const DAY = 24 * 60 * 60 * 1000;

/** Everything the journeys hand on to each other. */
const course = {
  lecturerEmail: `bard-${TAG}@example.com`,
  lecturerName: `Bård${TAG} Foreleser`,
  className: `class-of-${TAG}`,
  classId: "",
  sessionId: "",
  /** The six valid roster addresses; the first four accept, the fifth is registered by hand. */
  students: Array.from({ length: 6 }, (_, i) => ({
    email: `uj-${TAG}-s${i + 1}@stud.example.no`,
    name: ["Sara", "Jonas", "Emma", "Ola", "Kari", "Per"][i] + ` ${TAG}`,
    password: PASSWORD,
  })),
  /** The four Students of the full Class game, and its id. */
  gameId: "",
  oddGameId: "",
  players: [] as { email: string; name: string; role: string }[],
};

let lecturerContext: BrowserContext;
let lecturer: Page;

async function shot(page: Page, name: string) {
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

/** The path of the first link in `text` that starts with `route`. */
function linkIn(text: string, route: string): string {
  const match = text.match(new RegExp(`https?://[^/\\s]+(${route}#[A-Za-z0-9_-]+)`));
  expect(match, `a ${route} link in the mail`).not.toBeNull();
  return match![1];
}

/** A logged-out browser context at phone width, as a Student has it. */
async function phone(browser: Browser): Promise<BrowserContext> {
  return browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: { width: 390, height: 844 },
    locale: "nb-NO",
    timezoneId: "Europe/Oslo",
  });
}

/** A Student's own context, logged in through «Logg inn». */
async function studentLogin(browser: Browser, email: string, context?: BrowserContext, home = /\/hjem$/): Promise<Page> {
  const page = await (context ?? (await phone(browser))).newPage();
  await page.goto("/logg-inn");
  await untilHydrated(page);
  await page.getByLabel(nb.auth.login.email).fill(email);
  await page.getByLabel(nb.auth.login.password).fill(PASSWORD);
  await page.getByRole("button", { name: nb.auth.login.submit }).click();
  await expect(page).toHaveURL(home);
  return page;
}

/** For working on a later journey: `JOURNEY_RESUME=UJ-5` skips the journeys before the first
 * whose title starts with it and picks up the state the last run saved (the database keeps the
 * rest). Never set in a real run. */
const RESUME = process.env.JOURNEY_RESUME;
const STATE = path.join(os.tmpdir(), "olspillet-journey-state.json");
let resumed = !RESUME;

test.beforeEach(async ({ browser }, info) => {
  if (resumed) return;
  test.skip(!info.title.startsWith(RESUME!), "resuming a later journey");
  Object.assign(course, JSON.parse(fs.readFileSync(STATE, "utf-8")));
  lecturerContext = await browser.newContext({ baseURL: info.project.use.baseURL, viewport: { width: 1440, height: 900 } });
  lecturer = await studentLogin(browser, course.lecturerEmail, lecturerContext, /\/laererhjem$/);
  for (const player of course.players) {
    const own = await studentLogin(browser, player.email);
    if (course.gameId) await own.goto(`/spill/${course.gameId}`);
    phones.push(own);
  }
  resumed = true;
});

test.afterEach(async ({}, info) => {
  if (info.status === "passed") fs.writeFileSync(STATE, JSON.stringify(course));
  if (info.status === info.expectedStatus) return;
  for (const [i, own] of phones.entries()) {
    await own.screenshot({ path: info.outputPath(`phone-${i}.png`), fullPage: true }).catch(() => undefined);
    const tree = await own.locator("body").ariaSnapshot().catch(() => "");
    fs.writeFileSync(info.outputPath(`phone-${i}.yml`), tree);
  }
});

test.afterAll(async () => {
  await lecturerContext?.close();
});

test("UJ-1: the Admin makes a new Lecturer, who lands on an empty Lærerhjem", async ({ page, browser }) => {
  const invite = nb.admin.users.invite;
  const admin = await demoContext(browser, "admin");
  const adminPage = await admin.newPage();
  await adminPage.goto("/admin");
  await adminPage.getByRole("link", { name: nb.admin.sections.users }).click();
  await expect(adminPage).toHaveURL(/\/admin\/brukere$/);
  await untilHydrated(adminPage);
  const before = await latestMail(adminPage, course.lecturerEmail);
  await adminPage.getByLabel(invite.email, { exact: true }).fill(course.lecturerEmail);
  await adminPage.getByRole("radio", { name: invite.roles.lecturer }).check();
  await adminPage.getByRole("button", { name: invite.submit }).click();
  await expect(adminPage.getByText(invite.sent(course.lecturerEmail, invite.roles.lecturer, 14))).toBeFocused();
  await shot(adminPage, "uj-1-admin-invites");
  await admin.close();

  // Bård follows the link from the mail, sets a password and a name, and lands on the Lærerhjem.
  const mail = await nextMail(page, course.lecturerEmail, before);
  lecturerContext = await browser.newContext({ baseURL: test.info().project.use.baseURL, viewport: { width: 1440, height: 900 } });
  lecturer = await lecturerContext.newPage();
  await lecturer.goto(linkIn(mail.text, "/invitasjon"));
  const copy = nb.auth.invitation;
  await expect(lecturer.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
  await expect(lecturer.getByLabel(copy.email)).toHaveValue(course.lecturerEmail);
  await lecturer.getByLabel(copy.name).fill(course.lecturerName);
  await lecturer.getByLabel(copy.password).fill(PASSWORD);
  const created = answerTo(lecturer, "/api/auth/invitation/accept");
  await lecturer.getByRole("button", { name: copy.submit }).click();
  expect((await created).status()).toBe(200);
  await expect(lecturer).toHaveURL(/\/laererhjem$/);
  await expect(lecturer.getByText(nb.classes.home.empty)).toBeVisible();
  await expect(lecturer.getByRole("link", { name: nb.classes.home.newClass })).toBeVisible();
  await shot(lecturer, "uj-1-empty-laererhjem");
});

test("UJ-2: the Lecturer registers the Class, uploads the roster with malformed rows, invites and registers by hand", async ({
  browser,
}) => {
  const create = nb.classes.create;
  const roster = nb.classes.roster;
  await lecturer.getByRole("link", { name: nb.classes.home.newClass }).click();
  await expect(lecturer).toHaveURL(/\/klasser\/ny$/);
  await untilHydrated(lecturer);
  await lecturer.getByLabel(create.name, { exact: true }).fill(course.className);
  await lecturer.getByLabel(create.institution, { exact: true }).selectOption({ label: "Demohøgskolen" });
  await lecturer.getByLabel(create.courseCode, { exact: true }).fill("SCM200");
  const made = answerTo(lecturer, "/api/classes");
  await lecturer.getByRole("button", { name: create.submit }).click();
  expect((await made).status()).toBe(201);
  await expect(lecturer).toHaveURL(/\/klasser\/[0-9a-f-]{36}$/);
  course.classId = lecturer.url().split("/").pop()!;
  await expect(lecturer.getByRole("heading", { level: 1, name: course.className })).toBeVisible();

  // The Canvas export: six good addresses and four malformed ones, which are listed by row.
  const file = test.info().outputPath("canvas-export.csv");
  const rows = [
    "Navn,E-post",
    ...course.students.slice(0, 3).map((s) => `${s.name},${s.email}`),
    `Feil Domene,emma.solberg@stud`,
    `Feil Krøll,jakob.lien(at)stud.example.no`,
    ...course.students.slice(3).map((s) => `${s.name},${s.email}`),
    `To Krøller,thea.moe@@stud.example.no`,
    `Tom Adresse,`,
  ];
  fs.writeFileSync(file, rows.join("\n") + "\n");
  lecturer.on("filechooser", () => undefined);
  const chooser = lecturer.waitForEvent("filechooser");
  const uploaded = lecturer.waitForResponse(
    (r) => new URL(r.url()).pathname.endsWith("/roster-upload") && r.request().method() === "POST",
  );
  await lecturer.getByRole("button", { name: roster.chooseFile }).click();
  await (await chooser).setFiles(file);
  expect((await uploaded).status()).toBe(201);
  await expect(lecturer.getByText(roster.rowsRead(10))).toBeVisible();
  await expect(lecturer.getByRole("heading", { name: roster.invalidTitle(4, 10) })).toBeVisible();
  const invalid = lecturer.getByRole("region", { name: /^Ugyldige rader/ }).locator("li");
  await expect(invalid).toHaveCount(4);
  for (const [i, row] of [5, 6, 10, 11].entries()) await expect(invalid.nth(i)).toContainText(`Rad ${row}`);
  await expect(invalid.nth(0)).toContainText(roster.reasons.missing_domain);
  await expect(invalid.nth(1)).toContainText(roster.reasons.missing_at);
  await expect(invalid.nth(2)).toContainText(roster.reasons.two_at);
  await expect(invalid.nth(3)).toContainText(roster.reasons.empty);
  await shot(lecturer, "uj-2-roster-malformed-rows");

  // Invitations valid for two weeks to the six good addresses.
  await expect(lecturer.getByLabel(roster.validDays, { exact: true })).toHaveValue("14");
  const sent = lecturer.waitForResponse(
    (r) => new URL(r.url()).pathname.endsWith("/invitations") && r.request().method() === "POST",
  );
  await lecturer.getByRole("button", { name: roster.send(6) }).click();
  expect((await sent).status()).toBe(201);
  await expect(lecturer.getByRole("status").filter({ hasText: /^6 Invitasjoner sendt\./ })).toBeVisible();

  // Four Students accept on their phones: a name and a password, and they land on Hjem.
  const copy = nb.auth.invitation;
  for (const student of course.students.slice(0, 4)) {
    const mail = await nextMail(lecturer, student.email, null);
    const context = await phone(browser);
    const own = await context.newPage();
    await own.goto(linkIn(mail.text, "/invitasjon"));
    await expect(own.getByLabel(copy.student.email)).toHaveValue(student.email);
    await own.getByLabel(copy.name).fill(student.name);
    await own.getByLabel(copy.password).fill(PASSWORD);
    const accepted = answerTo(own, "/api/auth/invitation/accept");
    await own.getByRole("button", { name: copy.submit }).click();
    expect((await accepted).status()).toBe(200);
    await expect(own).toHaveURL(/\/hjem$/);
    await expect(own.getByRole("heading", { level: 2, name: new RegExp(course.className) })).toBeVisible();
    if (student === course.students[0]) await shot(own, "uj-2-student-hjem");
    await context.close();
  }

  // The fifth reported problems: Bård registers that Student by hand; the sixth stays out.
  const status = nb.classes.registration;
  const entries = nb.classes.entries;
  await lecturer.reload();
  const section = lecturer.getByRole("region", { name: status.title });
  const list = section.getByRole("region", { name: status.listTitle }).getByRole("listitem");
  const kari = course.students[4];
  const before = await latestMail(lecturer, kari.email);
  await list.filter({ hasText: kari.email }).getByRole("button", { name: entries.manualFor(kari.email) }).click();
  await expect(section.getByLabel(entries.email)).toHaveValue(kari.email);
  await section.getByLabel(entries.name).fill(kari.name);
  await section.getByRole("button", { name: entries.manualSubmit }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: entries.registered(kari.email) })).toBeVisible();
  await expect(section.getByText(status.total(status.registered, 4), { exact: true })).toBeVisible();
  await expect(section.getByText(status.total(status.manual, 1), { exact: true })).toBeVisible();
  await expect(section.getByText(status.total(status.unregistered, 1), { exact: true })).toBeVisible();
  await shot(lecturer, "uj-2-registration-status");

  // Kari sets a password through the mailed link.
  const mail = await nextMail(lecturer, kari.email, before);
  const context = await phone(browser);
  const own = await context.newPage();
  await own.goto(linkIn(mail.text, "/nytt-passord"));
  await expect(own.getByText(nb.auth.reset.firstLead(kari.email))).toBeVisible();
  await untilHydrated(own);
  await own.getByLabel(nb.auth.reset.firstPassword, { exact: true }).fill(PASSWORD);
  await own.getByRole("button", { name: nb.auth.reset.submit }).click();
  await expect(own.getByText(nb.auth.reset.done)).toBeFocused();
  await context.close();
});

test("UJ-1 edge case: an Assistant lecturer is granted the Lecturer role and keeps one login", async ({ browser }) => {
  const staff = nb.classes.staff;
  const address = `kollega-${TAG}@example.com`;
  await lecturer.goto(`/klasser/${course.classId}`);
  await lecturer.getByRole("link", { name: nb.classes.page.staff }).click();
  const assistants = lecturer.getByRole("region", { name: staff.assistants });
  await assistants.getByRole("button", { name: staff.inviteAssistant, exact: true }).click();
  await assistants.getByLabel(staff.email).fill(address);
  await assistants.getByRole("button", { name: staff.inviteAssistantSubmit }).click();
  await expect(assistants.getByRole("status").filter({ hasText: address })).toBeVisible();
  const mail = await nextMail(lecturer, address, null);
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const own = await context.newPage();
  await own.goto(linkIn(mail.text, "/invitasjon"));
  await own.getByLabel(nb.auth.invitation.name).fill(`Kollega${TAG} Assistent`);
  await own.getByLabel(nb.auth.invitation.password).fill(PASSWORD);
  await own.getByRole("button", { name: nb.auth.invitation.submit }).click();
  await expect(own).toHaveURL(/\/laererhjem$/);
  await expect(own.getByRole("link", { name: nb.classes.home.newClass })).toHaveCount(0);

  // Kari, the Admin, grants the Lecturer role to that account.
  const list = nb.admin.users.list;
  const admin = await demoContext(browser, "admin");
  const adminPage = await admin.newPage();
  await adminPage.goto("/admin/brukere");
  await adminPage.getByLabel(list.search).fill(address);
  const grant = adminPage.getByRole("button", { name: list.grant(`Kollega${TAG}`, list.roles.lecturer) });
  await grant.click();
  await expect(adminPage.getByRole("status").filter({ hasText: list.granted(`Kollega${TAG}`, list.roles.lecturer) })).toBeVisible();
  await admin.close();

  // The same login now makes Classes of its own and still reaches the colleague's Class.
  await own.goto("/laererhjem");
  await expect(own.getByRole("link", { name: nb.classes.home.newClass })).toBeVisible();
  await expect(own.getByRole("link", { name: new RegExp(course.className) })).toBeVisible();
  await shot(own, "uj-1-edge-assistant-granted-lecturer");
  await context.close();
});

/** Today in Europe/Oslo plus `days`, at `hour`:00, as a date field takes it. */
function osloInput(days: number, hour: number): string {
  const parts = new Intl.DateTimeFormat("en-GB", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Europe/Oslo" })
    .formatToParts(new Date());
  const part = (type: string) => Number(parts.find((p) => p.type === type)!.value);
  const day = new Date(Date.UTC(part("year"), part("month") - 1, part("day")) + days * DAY).toISOString().slice(0, 10);
  return `${day}T${String(hour).padStart(2, "0")}:00`;
}

test("UJ-3: the Lecturer creates the Class session with defaults, obligatory, dates, Lab hours, and games of four with an odd Student", async () => {
  const copy = nb.sessions;
  const c = copy.choices;
  await lecturer.goto(`/klasser/${course.classId}`);
  const sessions = lecturer.getByRole("region", { name: copy.list.title });
  await sessions.getByRole("button", { name: copy.list.create }).click();
  await expect(lecturer).toHaveURL(/\/klasseokter\/[0-9a-f-]{36}$/);
  course.sessionId = lecturer.url().split("/").pop()!;
  await expect(lecturer.getByText(copy.defaults)).toBeVisible();
  await untilHydrated(lecturer, "main");

  // Default Game settings and LLM players; a Group debrief that opens when the own game ends.
  const group = (name: string) => lecturer.getByRole("group", { name, exact: true });
  await expect(group(c.aiMode).getByRole("radio", { name: c.llm })).toBeChecked();
  await group(c.debriefMode).getByText(c.group, { exact: true }).click();
  await expect(group(c.debriefMode).getByRole("radio", { name: c.group })).toBeChecked();
  await expect(group(c.debriefRelease).getByRole("radio", { name: c.releaseOpen })).toBeChecked();

  // Obligatory, as the course plan states.
  const toggle = lecturer.getByRole("switch", { name: new RegExp(`^${c.obligatory}`) });
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");

  // The Start date in three days, and the deadlines after it.
  const dates = copy.dates;
  const section = lecturer.getByRole("region", { name: dates.title });
  await section.getByLabel(dates.names.start_at, { exact: true }).fill(osloInput(3, 10));
  await section.getByLabel(dates.names.play_deadline, { exact: true }).fill(osloInput(17, 23));
  await section.getByLabel(dates.names.debrief_deadline, { exact: true }).fill(osloInput(20, 23));
  await expect(section.getByLabel(dates.names.test_deadline, { exact: true })).toHaveValue(osloInput(27, 23));
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  await expect(section.getByTestId("date-line").locator("[data-tick]")).toHaveCount(4);

  // Four Lab hours in the computer lab.
  const l = copy.labHours;
  for (const days of [4, 6, 9, 11]) {
    await section.getByRole("button", { name: l.add }).click();
    const form = section.getByRole("form", { name: l.addTitle });
    await form.getByLabel(l.date, { exact: true }).fill(osloInput(days, 0).slice(0, 10));
    await form.getByLabel(l.start, { exact: true }).fill("14:15");
    await form.getByLabel(l.end, { exact: true }).fill("16:00");
    await form.getByLabel(l.place, { exact: true }).fill("Datalab A2");
    await form.getByRole("button", { name: l.saveAdd }).click();
    await expect(section.getByRole("status").filter({ hasText: l.added })).toBeVisible();
  }
  await expect(section.getByTestId("date-line").locator("[data-lab-hour]")).toHaveCount(4);

  // The draw: five registered Students make one game of four and one Student with three AI players.
  const a = copy.allocation;
  await lecturer.getByRole("button", { name: a.open }).click();
  await expect(lecturer.getByRole("heading", { name: a.heading(2) })).toBeVisible({ timeout: 30_000 });
  await expect(lecturer.getByText(a.lead(5))).toBeVisible();
  await shot(lecturer, "uj-3-allocation");
  await lecturer.getByRole("button", { name: a.confirm }).click();
  await expect(lecturer.getByText(a.confirmed, { exact: true })).toBeFocused();

  const stored = (await (await lecturer.request.get(`/api/class-sessions/${course.sessionId}/allocation`)).json()) as {
    draft: { games: { number: number; seats: { role: string; user_id: string | null; name: string | null }[] }[] };
  };
  const counts = stored.draft.games.map((g) => g.seats.filter((s) => s.user_id).length).sort();
  expect(counts).toEqual([1, 4]);
  const full = stored.draft.games.find((g) => g.seats.every((s) => s.user_id))!;
  course.players = full.seats.map((s) => {
    const student = course.students.find((st) => st.name === s.name)!;
    return { email: student.email, name: student.name, role: s.role };
  });
  expect(course.players.every((p) => p.email)).toBe(true);
  await lecturer.reload();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await shot(lecturer, "uj-3-class-session");
});

/** «Les reglene» from Hjem, «Jeg har lest reglene», and the Startoppgave answered (wrongly, with
 * 0: it never counts) up to its optional last question, which is skipped. */
async function rulesAndStartingTask(own: Page, shoot: boolean) {
  const task = nb.games.startingTask;
  await own.goto("/hjem");
  await own.getByRole("link", { name: nb.homes.student.readRules }).click();
  await expect(own.getByRole("heading", { level: 1, name: nb.games.briefing.title })).toBeVisible();
  // The rules: lowest cost for the whole chain, and no talking about Orders.
  await expect(own.getByText(nb.games.briefing.goal.text)).toBeVisible();
  await expect(own.getByText(nb.games.briefing.together.arrange)).toBeVisible();
  if (shoot) await shot(own, "uj-4-rules");
  await own.getByRole("button", { name: nb.games.briefing.done }).or(own.getByRole("link", { name: nb.games.briefing.done })).click();
  await expect(own.getByRole("heading", { level: 1, name: task.title })).toBeVisible();
  const send = own.getByRole("button", { name: task.send });
  for (let item = 1; item <= 10; item++) {
    await expect(send.or(own.getByRole("button", { name: task.final.skip })).first()).toBeVisible();
    if (await own.getByRole("button", { name: task.final.skip }).isVisible()) break;
    await own.getByRole("main").getByRole("textbox").last().fill("0");
    await send.click();
    await expect(own.getByText(/^Ikke riktig\. Svaret er|^Riktig\. Svaret er/)).toHaveCount(item);
  }
  if (shoot) await shot(own, "uj-4-starting-task");
  await own.getByRole("button", { name: task.final.skip }).click();
  await expect(own.getByText(task.done, { exact: true })).toBeVisible();
  const start = own.getByRole("button", { name: nb.games.start.start });
  const toWeek = own.getByRole("link", { name: nb.games.start.toWeek(1) }).or(own.getByRole("button", { name: nb.games.start.toWeek(1) }));
  await expect(start.or(toWeek).first()).toBeVisible();
  if (await start.isVisible()) {
    await expect(own.getByText(nb.games.start.consequence)).toBeVisible();
    await start.click();
  } else {
    await toWeek.first().click();
  }
  await expect(own.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(1));
}

/** The Oslo wall clock now: today's date, and the time `minutes` before now as «HH:MM». */
function osloNow() {
  const at = (offset: number) =>
    new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Oslo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
      .format(new Date(Date.now() - offset * 60_000));
  return { date: at(0).slice(0, 10), minus: (minutes: number) => at(minutes).slice(11, 16) };
}

/** The Order a Seat places in `week`: the fixed 4 at first, then more as the step in demand comes
 * through; the Grossist orders 24 in Week 11 while units are already on their way (UJ-5). */
function orderFor(own: Page, week: number): number {
  const seat = phones.indexOf(own);
  if (seat === 2 && week === 11) return 24;
  if (week < 8) return 4;
  return [6, 7, 8, 8][seat]! + (week % 3);
}

/** One Order through the Ordrefelt, with «Bekreft ordre». */
async function order(own: Page, week: number, units: number) {
  const field = own.getByRole("textbox", { name: nb.games.play.order.label(week) });
  const confirm = own.getByRole("main").getByRole("button", { name: /^Bekreft ordre/ });
  // The field can be drawn again as the Week's numbers arrive: type until the button takes it.
  await expect(async () => {
    await field.fill(String(units));
    await expect(confirm).toBeEnabled({ timeout: 1_000 });
    await expect(field).toHaveValue(String(units), { timeout: 500 });
  }).toPass({ timeout: 20_000 });
  const posted = own.waitForResponse((r) => r.url().endsWith(`/weeks/${week}/order`) && r.request().method() === "POST");
  await confirm.click();
  expect((await posted).status()).toBe(204);
  // Sent; or, from the last of the four, the next Week (or the end) is already on the screen.
  await expect(
    own.getByText(new RegExp(`^Ordren på ${units} er sendt`)).or(own.getByRole("heading", { level: 1, name: new RegExp(`^(?!${nb.games.play.week(week)}$)`) })).first(),
  ).toBeVisible();
}

/** Week `week` on all four phones: each waits until the Week is on its screen, then orders (a
 * Veiledet uke places its fixed Order by itself). True when the game is over instead. */
async function playWeek(week: number): Promise<boolean> {
  for (const own of phones) {
    const heading = own.getByRole("heading", { level: 1 });
    await expect(heading).toHaveText(new RegExp(`^(${nb.games.play.week(week)}|${nb.games.play.end.title})$`), { timeout: 60_000 });
    if ((await heading.textContent()) === nb.games.play.end.title) return true;
    const field = own.getByRole("textbox", { name: nb.games.play.order.label(week) });
    if (await own.getByText(nb.games.play.order.guided).isVisible()) continue;
    await expect(field).toBeEditable();
    await order(own, week, orderFor(own, week));
  }
  return false;
}

/** The four players' own phones, logged in, through UJ-4 and UJ-5. */
const phones: Page[] = [];

test("UJ-4: four Students read the rules, do the Starting task and play 15 Weeks on their phones, then Pause", async ({
  browser,
}) => {
  // The Start date comes: the local dev lock stands in for the days passing.
  const locked = await lecturer.request.post(`/api/dev/class-sessions/${course.sessionId}/lock`, { headers: CSRF });
  expect(locked.status()).toBe(200);
  for (const player of course.players) phones.push(await studentLogin(browser, player.email));
  for (const [i, own] of phones.entries()) await rulesAndStartingTask(own, i === 2);
  course.gameId = phones[0]!.url().match(/\/spill\/([0-9a-f-]{36})/)![1];
  // By Seat: Fabrikk, Distributør, Grossist, Detaljist. The Grossist plays Sara's part; the
  // Fabrikk plays Jonas, who does not come on Thursday.
  const sara = phones[2]!;

  // Weeks 1 to 15: every Week each sees the numbers, enters one Order and sees whom the game waits for.
  for (let week = 1; week <= 15; week++) await playWeek(week);
  await expect(sara.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(16));
  // The Week is shown, never how many remain.
  await expect(sara.getByRole("main")).not.toContainText(/av 36|36 uker|uker igjen/i);
  await shot(sara, "uj-4-week-16");

  // They press Pause and agree to go on in a Lab hour with Bård in the room.
  const pause = nb.homes.student.pause;
  await sara.getByRole("main").getByRole("button", { name: pause.open }).click();
  await sara.locator("[data-pausevalg]").getByRole("button", { name: pause.confirm }).click();
  await expect(sara.getByRole("main").locator("[data-pause-line] p")).toHaveText(pause.pausedByYou);
  for (const own of phones.filter((p) => p !== sara)) {
    await expect(own.getByRole("main").locator("[data-pause-line] p")).toHaveText(pause.pausedBy(course.players[2]!.name));
  }
  await shot(sara, "uj-4-paused");
});

test("UJ-4 edge case: in the room on Thursday, Jonas is absent, Sara puts in an AI player, Jonas takes the Seat back; to the end", async () => {
  test.setTimeout(30 * 60_000);
  const [jonas, , sara] = phones as [Page, Page, Page, Page];
  const jonasName = course.players[0]!.name;
  const pause = nb.homes.student.pause;

  // Thursday: a Lab hour now, and Bård marks the game as in the room with a short limit.
  const l = nb.sessions.labHours;
  await lecturer.goto(`/klasseokter/${course.sessionId}`);
  const section = lecturer.getByRole("region", { name: nb.sessions.dates.title });
  await section.getByRole("button", { name: l.add }).click();
  const form = section.getByRole("form", { name: l.addTitle });
  const now = osloNow();
  await form.getByLabel(l.date, { exact: true }).fill(now.date);
  // Within today's date: from just before now to 110 min later, or to 23:59 near midnight.
  const from = now.minus(5) > now.minus(0) ? "00:00" : now.minus(5);
  const to = now.minus(-110) < now.minus(0) ? "23:59" : now.minus(-110);
  await form.getByLabel(l.start, { exact: true }).fill(from);
  await form.getByLabel(l.end, { exact: true }).fill(to);
  await form.getByLabel(l.place, { exact: true }).fill("Datalab A2");
  await form.getByRole("button", { name: l.saveAdd }).click();
  await expect(section.getByRole("status").filter({ hasText: l.added })).toBeVisible();
  const inRoom = nb.spillstyring.inRoom;
  await lecturer.goto(`/klasseokter/${course.sessionId}/oversikt/spill/${course.gameId}`);
  const block = lecturer.locator("[data-spillstyring]");
  await block.locator("[data-in-room-open]").click();
  const roomForm = block.locator("[data-in-room-form]");
  await roomForm.getByLabel(inRoom.field).fill("2");
  await roomForm.getByRole("button", { name: inRoom.confirm(2) }).click();
  await expect(block.locator("[data-in-room-marked]")).toContainText("KI tar over etter 2");
  await shot(lecturer, "uj-4-in-room");

  // Jonas does not come. The three order Week 16, which ends the Pause and starts his clock.
  const others = phones.filter((p) => p !== jonas);
  for (const own of others) await order(own, 16, orderFor(own, 16));
  await expect(sara.getByRole("main").locator("[data-pause-line] p")).toHaveText(/^Pausen er over\./);

  // Once the shorter limit has passed, Sara puts in an AI player for his Seat. (The sweep takes
  // the Seat over at the same due time; Sara presses first unless the sweep's minute came first.)
  const insert = sara.getByRole("main").getByRole("button", { name: nb.spillstyring.takeover(jonasName) });
  const seats = sara.getByRole("main").getByRole("region", { name: nb.homes.student.seats });
  await expect(async () => {
    await sara.reload();
    await expect(insert.or(seats.getByRole("listitem").first().filter({ hasText: "KI-spiller" })).first()).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 5 * 60_000, intervals: [3_000] });
  if (await insert.isVisible()) {
    await expect(sara.getByText(nb.spillstyring.thisWeek(jonasName))).toBeVisible();
    await shot(sara, "uj-4-insert-offered");
    await insert.click();
  } else {
    console.log("UJ-4: the sweep took Jonas's Seat over before Sara's press");
  }
  await expect(seats.getByRole("listitem").first()).toContainText("KI-spiller");
  await shot(sara, "uj-4-ai-in-jonas-seat");

  // The AI player orders for Jonas, and the game goes on.
  for (const own of others) {
    await expect(own.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(17), { timeout: 60_000 });
  }

  // Jonas comes back and asks for his Seat; he gets it when the next Week opens.
  const takeover = nb.homes.student.takeover;
  await jonas.reload();
  await expect(jonas.locator("[data-taken-over]")).toContainText(takeover.takenOver);
  await jonas.getByRole("main").getByRole("button", { name: takeover.reclaim }).click();
  await expect(jonas.locator("[data-reclaim-queued]")).toHaveText(takeover.reclaimQueued);
  await shot(jonas, "uj-4-reclaim-queued");
  for (const own of phones.filter((p) => p !== jonas)) await order(own, 17, orderFor(own, 17));
  await expect(jonas.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(18), { timeout: 60_000 });
  await expect(jonas.getByRole("textbox", { name: nb.games.play.order.label(18) })).toBeEditable({ timeout: 30_000 });

  // On to the hidden end.
  for (let week = 18; week <= 60; week++) {
    if (await playWeek(week)) break;
  }
  for (const own of phones) await expect(own.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.end.title);
  await shot(sara, "uj-4-game-finished");
});

test("UJ-5: game 17 has ended; the group opens the Group debrief, writes the Explanations and goes through the reveal and the chain together", async () => {
  test.setTimeout(30 * 60_000);
  const entry = nb.debriefEntry;
  const group = entry.group;
  const sara = phones[2]!;
  const others = phones.filter((p) => p !== sara);

  // Game 17 has ended: Sara opens the Group debrief from the end screen.
  await sara.goto(`/spill/${course.gameId}`);
  await expect(sara.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.end.title);
  const opened = sara.waitForResponse((r) => r.url().endsWith(`/api/me/class-sessions/${course.sessionId}/debrief`) && r.request().method() === "POST");
  await sara.getByRole("main").getByRole("link", { name: nb.games.play.end.toDebrief }).click();
  const debriefId = ((await (await opened).json()) as { id: string }).id;
  await expect(sara.getByRole("heading", { level: 1 })).toHaveText(entry.title(1));
  await expect(sara.getByRole("button", { name: group.moveOn })).toBeVisible();

  // The others join from Hjem, each on their own phone.
  for (const own of others) {
    await own.goto("/hjem");
    const steps = own.getByRole("region", { name: nb.homes.student.steps });
    await expect(steps.getByText(nb.homes.student.groupOpen)).toBeVisible();
    await steps.getByRole("link", { name: nb.homes.student.stepNames.debrief }).click();
    await own.getByRole("button", { name: group.join }).click();
    await expect(own.getByRole("heading", { level: 2, name: `${entry.stepOf(1, 5)}: ${entry.firstStep}` })).toBeFocused();
  }

  // First each writes, on their own phone, why the chain behaved as it did; the reveal opens.
  const why = [
    "Restordren vokste, så jeg bestilte mye for å få varer fram.",
    "Ordrene inn hoppet, og jeg trodde det ville fortsette.",
    "Jeg glemte det som allerede var på vei, og bestilte for mye.",
    "Lageret svingte fordi alle reagerte på forsinkede leveranser.",
  ];
  for (const [i, own] of phones.entries()) {
    await own.getByRole("textbox", { name: entry.explanation.prompt }).fill(why[i]!);
    await own.getByRole("button", { name: entry.explanation.send }).click();
    await expect(own.locator("[data-explanation-sent]").getByText(why[i]!, { exact: true })).toBeVisible();
  }
  for (const own of phones) await expect(own.locator("[data-debrief-reveal]")).toBeVisible();
  await shot(sara, "uj-5-reveal");

  // The opener moves the group on once the step has been open its while (shortened locally).
  expect((await sara.request.post(`/api/dev/debriefs/${debriefId}/backdate`, { headers: CSRF })).ok()).toBe(true);
  await sara.getByRole("button", { name: group.moveOn }).click();
  for (const own of phones) await expect(own.locator("[data-debrief-chain]").first()).toBeVisible();
  await shot(sara, "uj-5-chain");
  expect((await sara.request.post(`/api/dev/debriefs/${debriefId}/backdate`, { headers: CSRF })).ok()).toBe(true);
  await sara.getByRole("button", { name: group.moveOn }).click();
  for (const own of phones) await expect(own.getByRole("region", { name: nb.debrief.reflection.heading })).toBeVisible();
});

test("UJ-5: Sara answers the reflection questions, reads her moments (the Week-11 Order of 24) and finishes the Debrief", async () => {
  test.setTimeout(30 * 60_000);
  const sara = phones[2]!;
  const d = nb.debrief;
  await sara.goto(`/debrief/${course.sessionId}`);

  // The reflection questions, each answered and gone on from.
  const reflection = sara.getByRole("region", { name: d.reflection.heading });
  for (let i = 0; i < 10; i++) {
    const next = reflection.getByRole("button", { name: d.reflection.next });
    await expect(next.or(reflection.getByText(d.reflection.done)).first()).toBeVisible();
    if (await reflection.getByText(d.reflection.done).isVisible()) break;
    await expect(async () => {
      await reflection.getByRole("textbox").last().fill("Det var uvant å vente på varene, og jeg ble stresset av restordren.");
      await expect(next).not.toHaveAttribute("aria-disabled", "true", { timeout: 1_000 });
    }).toPass({ timeout: 20_000 });
    await next.click();
    await expect(reflection.getByText(d.reflection.answered).nth(i)).toBeVisible();
  }

  // Her own moments: the Orders she placed, with what was already on the way.
  const paging = sara.getByRole("group", { name: d.moments.paging });
  const counter = sara.getByRole("heading", { level: 3, name: /^Øyeblikk \d+ av \d+/ });
  const moments: string[] = [];
  for (let i = 0; i < 6; i++) {
    moments.push((await counter.textContent()) ?? "");
    const next = paging.getByRole("button", { name: d.moments.next });
    if (!(await next.isEnabled()) || (await next.getAttribute("aria-disabled")) === "true") break;
    await next.click();
    await expect(counter).not.toHaveText(moments.at(-1)!);
  }
  expect(moments.some((m) => /Uke 11\. Du bestilte 24/.test(m))).toBe(true);
  await shot(sara, "uj-5-moments");

  // Kjedens regning, and the Debrief finished.
  await sara.getByRole("button", { name: d.bill.finish }).click();
  await expect(sara.getByText(/^Debriefen er fullført /)).toBeVisible();
});

type QuizResult = { question_id: string; prompt: string; chosen: string; right_choice: string; choices: { id: string; text: string }[] };

test("UJ-5: Sara takes the Debrief quiz, gets some wrong, reads why and passes on the second try", async () => {
  const sara = phones[2]!;
  const q = nb.debrief.quiz;
  await sara.goto(`/debrief/${course.sessionId}`);
  const quiz = sara.locator("#debrief-quiz");
  await expect(quiz.getByRole("heading", { name: q.heading })).toBeVisible();
  // The first attempt: the position right, the two others wrong.
  const form = quiz.locator("[data-quiz-form]");
  const question = (scope: Locator, prompt: RegExp) => scope.getByRole("group", { name: prompt });
  await expect(form.or(quiz.locator("[data-quiz-result]")).first()).toBeVisible();
  if (await form.isVisible()) {
    await question(form, /posisjonen din/).getByRole("radio", { name: "3", exact: true }).check();
    await question(form, /Når kommer varene fram/).getByRole("radio", { name: "Samme uke" }).check();
    await question(form, /svinger ordrene mest/).getByRole("radio", { name: "Hos Detaljisten" }).check();
    await form.getByRole("button", { name: q.send }).click();
    await expect(quiz.locator("[data-quiz-summary]")).toHaveText(new RegExp(`^${q.result(1, 1, 3)}`));
  }
  // She reads why: each wrong answer marked, the right one named, an explanation under it.
  const result = quiz.locator("[data-quiz-result]").last();
  await expect(result.locator("[data-quiz-explanation]").first()).toBeVisible();
  const right = new Map<string, string>();
  for (const group of await result.getByRole("group").all()) {
    const name = (await group.getAttribute("aria-label")) ?? (await group.locator("legend").textContent()) ?? "";
    const correct = ((await group.getByRole("radio", { name: / Riktig$/ }).first().evaluate((r) => r.closest("label")?.textContent)) ?? "")
      .replace(/Riktig$/, "")
      .trim();
    right.set(name.replace(/^Spørsmål \d+ av \d+/, "").trim(), correct);
  }
  expect([...right.values()].every(Boolean)).toBe(true);
  await shot(sara, "uj-5-quiz-wrong");

  // The second try, in a new order: every answer right.
  await quiz.getByRole("button", { name: q.retry }).click();
  for (const [prompt, text] of right) {
    await form.getByRole("group", { name: prompt }).getByRole("radio", { name: text, exact: true }).check();
  }
  await form.getByRole("button", { name: q.send }).click();
  await expect(quiz.locator("[data-quiz-passed]")).toBeVisible();
  await expect(quiz.locator("[data-quiz-summary]").last()).toContainText(q.passed(2));
  await shot(sara, "uj-5-quiz-passed");
});

test("UJ-5: over the weekend Sara plays the Replay alone against three AI players and reads the walkthrough", async () => {
  test.setTimeout(30 * 60_000);
  const sara = phones[2]!;
  const replay = nb.homes.student.replay;
  await sara.goto("/hjem");
  const main = sara.getByRole("main");
  const block = main.getByRole("region", { name: replay.heading, exact: true });
  // Started (or, on a second look, resumed at its open Uke from Hjem).
  const start = block.getByRole("button", { name: replay.start });
  const resume = main.getByRole("link", { name: /^Fortsett Replay, Uke / });
  await expect(start.or(resume).first()).toBeVisible();
  if (await start.isVisible()) {
    await expect(block.getByText(replay.consequence)).toBeVisible();
    await start.click();
  } else {
    await resume.click();
  }
  await expect(sara.getByRole("heading", { level: 1 })).toHaveText(/^Uke \d+$/);
  await expect(sara.getByText(nb.games.play.roleReplay(nb.terms.wholesaler))).toBeVisible();
  // Three AI players, named as such.
  await expect(main.getByRole("region", { name: nb.homes.student.seats }).getByRole("listitem").filter({ hasText: "KI-spiller" })).toHaveCount(3);
  await shot(sara, "uj-5-replay-week-1");

  // Week by week against the AI players, to the Replay's end.
  const heading = sara.getByRole("heading", { level: 1 });
  const first = Number((await heading.textContent())!.replace(/\D/g, ""));
  for (let week = first; week <= 80; week++) {
    await expect(heading).toHaveText(new RegExp(`^(${nb.games.play.week(week)}|${nb.games.play.replayEnd.title})$`), { timeout: 60_000 });
    if ((await heading.textContent()) === nb.games.play.replayEnd.title) break;
    if (await sara.getByText(nb.games.play.order.guided).isVisible()) continue;
    await order(sara, week, week < 5 ? 4 : 8);
  }
  await expect(heading).toHaveText(nb.games.play.replayEnd.title);
  await shot(sara, "uj-5-replay-finished");

  // The short AI walkthrough of the run.
  const walk = nb.replay.walkthrough;
  await main.getByRole("link", { name: nb.games.play.replayEnd.toWalkthrough }).click();
  await expect(sara.getByRole("heading", { level: 1, name: walk.title })).toBeVisible();
  await expect(main.getByText(walk.pending)).toHaveCount(0, { timeout: 60_000 });
  await expect(main.getByText(walk.unlike)).toBeVisible();
  await expect(main.getByText(walk.unlikeNeighbours)).toBeVisible();
  await expect(main.getByText(walk.totalLabel)).toBeVisible();
  await shot(sara, "uj-5-replay-walkthrough");
});

/** One Individual test item answered: a choice, the cells of a table, a number or a drawn graph
 * typed into its table, or a long answer argued from the Student's own game and Replay. */
async function answerItem(item: Locator, n: number) {
  const radios = item.getByRole("radio");
  if (await radios.count()) {
    await radios.first().check();
  } else if (await item.locator("textarea").count()) {
    await item.locator("textarea").fill(
      `Svar ${n}. I Klassespillet økte jeg ordren til 24 i Uke 11 mens 16 enheter allerede var på vei. ` +
        "Restordren fikk meg til å glemme forsinkelsen, og kjeden svingte fordi hvert ledd forsterket ordrene. " +
        "I Replay holdt jeg øye med det som var på vei og bestilte jevnere. Neste gang regner jeg posisjonen før jeg bestiller.",
    );
    await item.locator("textarea").blur();
  } else {
    const cells = item.getByRole("textbox");
    for (let i = 0; i < (await cells.count()); i++) await cells.nth(i).fill(String(10 + i));
    await cells.last().blur();
  }
  await expect(item.getByRole("status").first()).toHaveText(/^Lagret \d{2}:\d{2}$/, { timeout: 20_000 });
}

test("UJ-6: Sara takes the Individual test over several evenings: choices, Interactive items and long answers", async () => {
  const copy = nb.tests.individual;
  const sara = phones[2]!;
  await sara.goto("/hjem");
  const steps = sara.getByRole("main").getByRole("region", { name: nb.homes.student.steps });
  await steps.getByRole("link", { name: new RegExp(nb.homes.student.stepNames.test) }).click();
  await expect(sara).toHaveURL(new RegExp(`/individuell-test/${course.sessionId}$`));
  await expect(sara.getByText(copy.statement)).toBeVisible();
  await sara.getByRole("button", { name: copy.accept }).click();
  await expect(sara.getByRole("heading", { name: copy.itemsHeading })).toBeFocused();
  const items = sara.locator("[data-test-item]");
  const count = await items.count();
  expect(count).toBeGreaterThan(3);
  await expect(items.filter({ has: sara.locator("[data-value-table]") }).first()).toBeVisible();
  await expect(items.filter({ has: sara.locator("textarea") }).first()).toBeVisible();

  // The first evening: half the items; she closes the test and comes back another evening.
  const half = Math.ceil(count / 2);
  for (let i = 0; i < half; i++) await answerItem(items.nth(i), i + 1);
  await shot(sara, "uj-6-first-evening");
  await sara.goto("/hjem");
  await sara.goto(`/individuell-test/${course.sessionId}`);
  await expect(sara.getByRole("button", { name: copy.accept })).toHaveCount(0);
  await expect(items).toHaveCount(count);
  for (let i = half; i < count; i++) await answerItem(items.nth(i), i + 1);

  // Submitted before the Test deadline.
  await sara.getByRole("button", { name: copy.submit.button }).first().click();
  const review = sara.getByRole("region", { name: copy.submit.reviewHeading });
  await expect(review.locator("[data-all-answered]")).toHaveCount(1);
  await review.getByRole("button", { name: copy.submit.button }).click();
  await expect(sara.locator("[data-submitted-line]")).toHaveText(/^Levert .+ Du kan ikke endre svarene\.$/u);
  await shot(sara, "uj-6-submitted");
});

test("UJ-7: the Lecturer overview, a Message to a game, and AI players finishing at the Play deadline", async () => {
  const overview = `/klasseokter/${course.sessionId}/oversikt`;
  const main = lecturer.getByRole("main");
  const wall = main.getByRole("grid");
  await lecturer.goto(overview);
  await expect(main.getByRole("heading", { level: 1, name: nb.overview.title })).toBeVisible();
  // Game 1 finished, with its chain cost; game 2 of the odd Student and three AI players.
  await expect(wall.getByRole("rowheader", { name: /^Spill 1, ferdig, kjedekost / })).toBeVisible();
  await expect(main.getByText(/3 KI-spillere i 1 spill, alle merket\./)).toBeVisible();

  // The odd Student never started game 2: Bård starts it from the Oversikt.
  const start = nb.overview.start;
  const startLink = main.getByRole("link", { name: start.link(1) });
  if (await startLink.isVisible()) {
    await startLink.click();
    await expect(lecturer.getByText(start.consequence)).toBeVisible();
    await lecturer.getByRole("button", { name: start.confirm(1) }).click();
    await expect(main.getByText(start.done(1))).toBeVisible();
  }
  await lecturer.goto(overview);
  // Whom it waits for, and since when.
  const game2 = wall.getByRole("rowheader", { name: /^Spill 2, / });
  await expect(game2).toBeVisible();
  await expect(main).toContainText(/1 ferdig · 1 (pågår|venter)/);
  await shot(lecturer, "uj-7-overview");

  // A Message to the Students of game 2: the odd Student reads it on Hjem and by e-mail.
  const odd = course.students.slice(0, 5).find((s) => !course.players.some((p) => p.email === s.email))!;
  const before = await latestMail(lecturer, odd.email);
  const m = nb.messages;
  const toGame2 = wall.getByRole("link", { name: m.toGameLabel(2) });
  course.oddGameId = new URL((await toGame2.getAttribute("href"))!, "http://x").searchParams.get("spill")!;
  await toGame2.click();
  await expect(main.getByRole("heading", { level: 1, name: "Melding til Spill 2" })).toBeVisible();
  await expect(main.getByText(m.reach(1))).toBeVisible();
  const text = "Husk å legge inn ordren for Spill 2 før Spillfristen.";
  await main.getByRole("textbox", { name: m.field }).fill(text);
  await main.getByRole("button", { name: m.send }).click();
  await expect(main.getByText(m.sent(1))).toBeFocused();
  const mail = await nextMail(lecturer, odd.email, before, "Spill 2");
  expect(mail.text).toContain(text);
  await shot(lecturer, "uj-7-message-sent");

  // The Play deadline: AI players finish game 2 (the local dev playout stands in for the sweep at
  // the deadline).
  const played = await lecturer.request.post(`/api/dev/games/${course.oddGameId}/playout`, { headers: CSRF });
  expect(played.status()).toBe(200);
  // The AI players' last Weeks are computed after the answer; the Oversikt reads it once done.
  await expect(async () => {
    await lecturer.goto(overview);
    await expect(main).toContainText(/2 ferdig · 0 pågår · 0 venter/, { timeout: 5_000 });
  }).toPass({ timeout: 3 * 60_000, intervals: [5_000] });
  await expect(wall.getByRole("rowheader", { name: /^Spill 2, ferdig/ })).toBeVisible();
  await shot(lecturer, "uj-7-all-finished");
});

test("UJ-8: after the Test deadline Sara reads the AI assessment, turns on the letter and downloads her report; Bård downloads the ZIP and the Completion export", async ({
  browser,
}) => {
  test.setTimeout(15 * 60_000);
  const sara = phones[2]!;
  const saraEmail = course.players[2]!.email;
  const before = await latestMail(sara, saraEmail);
  // The Test deadline passes (the local dev routes move the dates and run the lock and the close).
  // The sweep closes each attempt at the deadline; the dev close does Sara's at once.
  for (const [who, route, status] of [
    [lecturer, "test-deadline-passed", 200],
    [lecturer, "lock-test", 200],
    [sara, "test/close", 204],
  ] as const) {
    const done = await who.request.post(`/api/dev/class-sessions/${course.sessionId}/${route}`, { headers: CSRF });
    expect(done.status(), route).toBe(status);
  }

  // Sara learns the AI assessment is ready: on Hjem at once. (The e-mail is a digest notice,
  // which is never sent at night; a run in the daytime gets it here.)
  const a = nb.assessment.student;
  await expect(async () => {
    await sara.goto("/hjem");
    await expect(sara.getByRole("main").getByText(a.readyOnHjem)).toBeVisible({ timeout: 3_000 });
  }).toPass({ timeout: 120_000, intervals: [5_000] });
  const mail = await nextMail(sara, saraEmail, before, "/ki-vurdering/").catch(() => null);
  console.log(`UJ-8: the assessment mail ${mail ? `arrived: ${mail.subject}` : "did not come within 30 s (digest, quiet hours)"}`);
  await sara.getByRole("main").getByRole("link", { name: a.link }).click();
  await expect(sara).toHaveURL(new RegExp(`/ki-vurdering/${course.sessionId}$`));
  const main = sara.getByRole("main");
  // A score and written feedback per question, her own words quoted, AI-generated and counting
  // toward nothing.
  await expect(main.getByText(a.disclosure)).toBeVisible();
  await expect(main.getByText(/^\d+(,\d+)? av \d+ poeng$/).first()).toBeVisible();
  await expect(main.getByText(/^KI-generert, kan ta feil: Du skriver Svar \d+/).first()).toBeVisible();
  await expect(main.getByText(/^Vektet sum: .+ av 100 poeng$/)).toBeVisible();

  // Bård left the Indicative letter to each Student: Sara turns it on for her own view.
  const letter = nb.assessment.letter;
  const toggle = sara.locator("[data-total]").getByRole("switch");
  await expect(toggle).toHaveAccessibleName(`${letter.control} ${letter.off}`);
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(sara.locator("[data-total] [data-letter]")).toContainText(letter.label);
  await shot(sara, "uj-8-ai-assessment-letter");

  // Sara downloads the PDF report of the games, the Debrief and the test.
  const r = nb.reports.download;
  await sara.goto("/hjem");
  const report = sara.locator(`section[aria-labelledby="steps-${course.sessionId}"]`).locator("li[data-state]").last();
  await report.getByRole("button", { name: r.make }).click();
  const link = report.getByRole("link", { name: r.link });
  await expect(link).toBeVisible({ timeout: 60_000 });
  const saved = sara.waitForEvent("download");
  await link.click();
  const pdf = fs.readFileSync(await (await saved).path());
  expect(pdf.subarray(0, 5).toString()).toBe("%PDF-");
  await shot(sara, "uj-8-student-report");

  // Bård downloads all the reports as one ZIP and the Completion export as a spreadsheet.
  const e = nb.reports.export;
  await lecturer.goto(`/klasseokter/${course.sessionId}`);
  const block = lecturer.locator("[data-export]");
  await block.getByRole("button", { name: e.zip.action }).click();
  const zipLink = block.getByRole("link", { name: e.zip.action });
  await expect(zipLink).toBeVisible({ timeout: 120_000 });
  const zipSaved = lecturer.waitForEvent("download");
  await zipLink.click();
  const zip = fs.readFileSync(await (await zipSaved).path());
  expect(zip.subarray(0, 2).toString()).toBe("PK");
  for (const student of course.students.slice(0, 5)) expect(zip.includes(Buffer.from(`${student.name}.pdf`))).toBe(true);
  await block.getByRole("button", { name: e.completion.action }).click();
  const xlsxSaved = lecturer.waitForEvent("download");
  await block.getByRole("link", { name: e.completion.xlsx }).click();
  const xlsx = await xlsxSaved;
  expect(xlsx.suggestedFilename()).toMatch(/^fullforingsliste-klasseokt-\d+\.xlsx$/);
  expect(fs.readFileSync(await xlsx.path()).subarray(0, 2).toString()).toBe("PK");
  await shot(lecturer, "uj-8-export");

  // Edge case: the odd Student never took the test, and still gets a report with that step not done.
  const odd = course.students.slice(0, 5).find((s) => !course.players.some((p) => p.email === s.email))!;
  const own = await studentLogin(browser, odd.email);
  const steps = own.locator(`section[aria-labelledby="steps-${course.sessionId}"]`);
  const testStep = steps.locator("li[data-state]").filter({ hasText: nb.homes.student.stepNames.test });
  await expect(testStep).not.toHaveAttribute("data-state", "done");
  const oddReport = steps.locator("li[data-state]").last();
  await oddReport.getByRole("button", { name: r.make }).click();
  const oddLink = oddReport.getByRole("link", { name: r.link });
  await expect(oddLink).toBeVisible({ timeout: 60_000 });
  const oddSaved = own.waitForEvent("download");
  await oddLink.click();
  expect(fs.readFileSync(await (await oddSaved).path()).subarray(0, 5).toString()).toBe("%PDF-");
  await shot(own, "uj-8-edge-odd-student-report");
  await own.context().close();
});

test("UJ-9: the Lecturer opens the Class report, shows all games in a plenary, compares across classes and creates next year's Class session", async () => {
  const report = nb.classReport;
  const overview = `/klasseokter/${course.sessionId}/oversikt`;
  const main = lecturer.getByRole("main");
  await lecturer.goto(overview);
  await main.getByRole("link", { name: report.link, exact: true }).click();
  await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${course.sessionId}/klasserapport$`));
  await expect(lecturer.getByRole("heading", { level: 1, name: report.title })).toBeVisible();
  // Test results, the most common Detected patterns, Order amplification per Role.
  await expect(main.getByText("Alle 2 spill er med.")).toBeVisible();
  for (const name of ["Trakt", "Kjedekost", "Forsterkning per Rolle", "Mønstre", "Læringsresultater"]) {
    await expect(main.getByRole("region", { name, exact: true })).toBeVisible();
  }
  await expect(main.getByRole("region", { name: "Resultater per spørsmål" })).toBeVisible();
  await shot(lecturer, "uj-9-class-report");

  // All Class games side by side in a plenary: no names, no ranking.
  await lecturer.goto(overview);
  await main.getByRole("link", { name: nb.plenary.button, exact: true }).click();
  await expect(lecturer.getByRole("heading", { level: 1, name: nb.plenary.title })).toBeVisible();
  await expect(main.getByRole("grid")).toBeVisible();
  for (const student of course.students) await expect(main).not.toContainText(student.name);
  await shot(lecturer, "uj-9-plenary");

  // Cross-class statistics: this Lecturer has one Class session with results, so there is no
  // earlier one to compare with yet (a second year's run would show the comparison).
  await lecturer.goto(`/klasser/${course.classId}`);
  await lecturer.getByRole("link", { name: nb.crossClass.title }).first().click();
  await expect(lecturer.getByRole("heading", { level: 1, name: nb.crossClass.title })).toBeVisible();
  await expect(main.getByText(nb.crossClass.empty)).toBeVisible();
  await shot(lecturer, "uj-9-cross-class");

  // Next year's Class, and its Class session made from this one.
  const create = nb.classes.create;
  const next = `${course.className}-neste`;
  await lecturer.goto("/klasser/ny");
  await untilHydrated(lecturer);
  await lecturer.getByLabel(create.name, { exact: true }).fill(next);
  await lecturer.getByLabel(create.institution, { exact: true }).selectOption({ label: "Demohøgskolen" });
  await lecturer.getByLabel(create.courseCode, { exact: true }).fill("SCM200");
  await lecturer.getByRole("button", { name: create.submit }).click();
  await expect(lecturer.getByRole("heading", { level: 1, name: next })).toBeVisible();
  const r = nb.sessions.list.rerun;
  await lecturer.getByRole("region", { name: nb.sessions.list.title }).getByRole("button", { name: r.open }).click();
  const panel = lecturer.getByRole("region", { name: r.title });
  const source = panel.getByLabel(r.source);
  await expect(source.locator("optgroup")).toHaveAttribute("label", course.className);
  await expect(panel.getByText(r.notCopied)).toBeVisible();
  const made = lecturer.waitForResponse((res) => res.url().endsWith("/class-sessions/copy"));
  await panel.getByRole("button", { name: r.submit }).click();
  expect((await made).status()).toBe(201);
  await expect(lecturer.getByRole("heading", { level: 1, name: nb.sessions.title(next) })).toBeVisible();
  await expect(lecturer.getByText(nb.sessions.copied.from(1, course.className))).toBeVisible();
  await lecturer.getByRole("button", { name: nb.sessions.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
  await shot(lecturer, "uj-9-next-year-session");
});
