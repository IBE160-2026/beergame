import { type Browser, expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { DEMO_PASSWORD } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test } from "./support/classes";

/** Student choice of a Class game and a Seat (Story 5.17, cut list, `FEATURE_STUDENT_CHOICE`,
 * FR-21, UX-DR62), on the local stack, where the flag is on. Each test makes a fresh Class and
 * Class session through the api and registers demo Students in it by hand (one demo Student per
 * test, so their logins never meet the per-account limit). The method's refusals, the race on one
 * Seat, the offer to late registrants and the draw at the lock are pinned by
 * `backend/tests/sessions/test_student_choice.py`; here the screens. */
const a = nb.sessions.allocation;
const sc = nb.sessions.seatChoice;
const CSRF = { "X-Requested-With": "olspillet" };

async function register(lecturer: Page, classId: string, email: string, name = email) {
  const registered = await lecturer.request.post(`/api/classes/${classId}/roster/manual`, {
    data: { email, name },
    headers: CSRF,
  });
  expect(registered.ok()).toBe(true);
}

async function newSession(lecturer: Page, classId: string): Promise<string> {
  const created = await lecturer.request.post(`/api/classes/${classId}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

/** A fresh Class with the demo Students `students` registered and a Class session with Student
 * choice saved through the api. */
async function choosing(lecturer: Page, students: string[]): Promise<string> {
  const klass = await freshClass(lecturer);
  for (const email of students) await register(lecturer, klass.id, email);
  const id = await newSession(lecturer, klass.id);
  const saved = await lecturer.request.put(`/api/class-sessions/${id}`, {
    data: { ai_mode: "rule_based", allocation_method: "student_choice" },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  return id;
}

/** A page logged in as the demo Student `email`, through the api's login. */
async function studentPage(browser: Browser, email: string, width: number, height: number): Promise<Page> {
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, viewport: { width, height } });
  const login = await context.request.post("/api/auth/login", {
    data: { email, password: DEMO_PASSWORD },
    headers: CSRF,
  });
  expect(login.status()).toBe(200);
  return context.newPage();
}

const seatButton = (page: Page, game: number, text: string) =>
  page.getByRole("region", { name: sc.game(game) }).getByRole("button", { name: text, exact: true });

test("the Lecturer chooses Student choice with Valgknapper and saves it", async ({ browser, lecturerSession }) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const klass = await freshClass(lecturer);
  for (let i = 0; i < 5; i++) await register(lecturer, klass.id, `valg-${klass.name}-${i}@example.com`, `Valg${i}`);
  const id = await newSession(lecturer, klass.id);
  await lecturer.goto(`/klasseokter/${id}`);
  const methods = lecturer.getByRole("group", { name: a.method, exact: true });
  await expect(methods).toBeVisible();
  await expect(methods.getByRole("radio", { name: a.methodRandom })).toBeChecked();
  await expect(lecturer.getByText(a.methodRandomHelp)).toBeVisible();
  await methods.getByRole("radio", { name: a.methodChoice }).check();
  await expect(lecturer.getByText(a.methodChoiceHelp)).toBeVisible();
  await expect(lecturer.getByText(a.methodChoicePending)).toBeVisible();
  // Nothing is drawn while Student choice waits for the save.
  await expect(lecturer.getByRole("button", { name: a.open })).toHaveCount(0);
  await expectAccessible(lecturer, false);

  await lecturer.getByRole("button", { name: nb.sessions.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
  await expect(lecturer.getByText(a.choiceState)).toBeVisible();
  await expect(lecturer.getByRole("group", { name: a.method, exact: true })).toHaveCount(0);
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}/allocation`)).json();
  expect(stored.method).toBe("student_choice");
  expect(stored.draft.games).toHaveLength(2);
  // The panel reads the empty Class games, read-only: every Seat «Ledig», nothing to confirm.
  await lecturer.getByRole("button", { name: a.open }).click();
  await expect(lecturer.getByText(a.choiceLead(0))).toBeVisible();
  await expect(lecturer.getByText(a.choiceMissing(5))).toBeVisible();
  // Students who have not chosen are drawn first; only then do empty Seats get AI players (Issue #115).
  await expect(lecturer.getByText(a.choiceEmptySeats)).toBeVisible();
  await expect(lecturer.getByText(a.emptySeats, { exact: true })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: a.confirm })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: a.redraw })).toHaveCount(0);
  // Nobody is moved from the panel: no Seat list with «Flytt eller bytt».
  await expect(lecturer.getByRole("region", { name: a.seatsHeading(1) })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: a.pickShort })).toHaveCount(0);
  await expectAccessible(lecturer, false);
});

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true, student: "student2@example.com" },
  { name: "360 px", width: 360, height: 740, phone: true, student: "student3@example.com" },
  { name: "1440 px", width: 1440, height: 900, phone: false, student: "student4@example.com" },
];

for (const vp of VIEWPORTS) {
  test(`${vp.name}: a Student opens «Velg spill og sete» from Hjem and takes a free Seat`, async ({
    browser,
    lecturerSession,
  }) => {
    const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
    const id = await choosing(lecturer, [vp.student]);
    const student = await studentPage(browser, vp.student, vp.width, vp.height);
    await student.goto("/hjem");
    const link = student.getByRole("link", { name: sc.open }).and(student.locator(`[href$="${id}/velg-sete"]`));
    await expect(link).toBeVisible();
    await link.click();
    await expect(student.getByRole("heading", { level: 1, name: sc.title })).toBeVisible();
    await expect(student.getByText(sc.none)).toBeVisible();
    // One Klassespill, four Seats in words, Fabrikk first.
    const game = student.getByRole("region", { name: sc.game(1) });
    const seats = game.getByRole("button");
    await expect(seats).toHaveCount(4);
    for (const [i, name] of ["Fabrikk, ledig", "Distributør, ledig", "Grossist, ledig", "Detaljist, ledig"].entries()) {
      await expect(seats.nth(i)).toHaveAccessibleName(name);
    }
    await expect(student.getByRole("button", { name: sc.take("Grossist", 1) })).toHaveCount(0);
    await seatButton(student, 1, "Grossist, ledig").click();
    await expect(seatButton(student, 1, "Grossist, ledig")).toHaveAttribute("aria-pressed", "true");
    const take = student.getByRole("button", { name: sc.take("Grossist", 1) });
    await expect(take).toBeVisible();
    await expectAccessible(student, vp.phone);
    // Tap targets are at least 44 px.
    const box = await seatButton(student, 1, "Fabrikk, ledig").boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(44);

    await take.click();
    await expect(student.getByText(sc.mine("Grossist", 1))).toBeFocused();
    await expect(game.getByText(sc.own("Grossist"))).toBeVisible();
    await expect(game.getByRole("button")).toHaveCount(3);
    // Another free Seat now moves the Student, which the screen says before the press.
    await seatButton(student, 1, "Detaljist, ledig").click();
    await expect(student.getByText(sc.leaves("Grossist", 1))).toBeVisible();
    await expectAccessible(student, vp.phone);
    await student.context().close();
  });
}

test("a Seat taken by another first moves focus to the conflict line above the new list", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const id = await choosing(lecturer, ["student5@example.com", "student6@example.com"]);
  const student = await studentPage(browser, "student5@example.com", 360, 740);
  await student.goto(`/klasseokter/${id}/velg-sete`);
  await seatButton(student, 1, "Detaljist, ledig").click();
  // Another Student takes it first.
  const other = await studentPage(browser, "student6@example.com", 360, 740);
  const taken = await other.request.put(`/api/me/class-sessions/${id}/seat-choice`, {
    data: { game_number: 1, role: "retailer" },
    headers: CSRF,
  });
  expect(taken.status()).toBe(200);
  await student.getByRole("button", { name: sc.take("Detaljist", 1) }).click();
  const conflict = student.getByText(sc.conflict);
  await expect(conflict).toBeFocused();
  await expect(conflict).toHaveAttribute("tabindex", "-1");
  // The refreshed list names the holder and offers the Seat no more.
  const game = student.getByRole("region", { name: sc.game(1) });
  await expect(game.getByText(/^Detaljist, /)).not.toHaveText("Detaljist, ledig");
  await expect(seatButton(student, 1, "Detaljist, ledig")).toHaveCount(0);
  await expect(student.getByRole("main").getByRole("alert")).toHaveCount(0);
  await expectAccessible(student, true);
  await other.context().close();
  await student.context().close();
});

test("with the flag off the route is not found and Hjem shows the drawn Seat once locked", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const id = await choosing(lecturer, ["student7@example.com"]);
  const student = await studentPage(browser, "student7@example.com", 360, 740);
  // The server's answers once the lock drew a Seat; the draw is pinned by the api tests.
  await student.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    for (const item of body.items) {
      if (item.id === id) {
        item.seat_choice_open = false;
        item.drawn_seat = { game_number: 3, role: "wholesaler" };
      }
    }
    await route.fulfill({ response, json: body });
  });
  await student.goto("/hjem");
  await expect(student.getByText(sc.drawn("Grossist", 3))).toBeVisible();
  await expectAccessible(student, true);
  // `FEATURE_STUDENT_CHOICE` off: the api answers not found (pinned by the api tests).
  await student.route(`**/api/me/class-sessions/${id}/seat-choice`, (route) =>
    route.fulfill({ status: 404, json: { error: { code: "not_found", message: "", fields: {} } } }),
  );
  await student.goto(`/klasseokter/${id}/velg-sete`);
  await expect(student.getByRole("heading", { level: 1, name: nb.access.notFound })).toBeVisible();
  await student.context().close();

  // The Klasseøkt with the flag off offers no method.
  const other = await newSession(lecturer, (await freshClass(lecturer)).id);
  await lecturer.route(`**/api/class-sessions/${other}`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), student_choice_enabled: false } });
  });
  await lecturer.goto(`/klasseokter/${other}`);
  await expect(lecturer.getByRole("heading", { name: a.title })).toBeVisible();
  await expect(lecturer.getByRole("group", { name: a.method, exact: true })).toHaveCount(0);
});
