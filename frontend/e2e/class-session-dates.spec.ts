import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** The four dates on the Datolinje (Story 5.2, FR-18, NFR-6, UX-DR51, UX-DR56, UX-DR75) and the
 * fixes of Issue #98, on the local stack. Each test makes a fresh Lecturer and Class through the
 * api. The rules on the route (order, past, passed, locked) are pinned by
 * `backend/tests/sessions/test_dates.py`; here the screen. */
const copy = nb.sessions;
const dates = copy.dates;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;

/** Today in Europe/Oslo, read once, so every date of a test counts calendar days from it. */
const TODAY = (() => {
  const parts = new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Europe/Oslo",
  }).formatToParts(new Date());
  const part = (type: string) => Number(parts.find((p) => p.type === type)!.value);
  return Date.UTC(part("year"), part("month") - 1, part("day"));
})();

/** The Europe/Oslo wall time `days` calendar days from today at `hour`:00, as a date field
 * takes it. */
function osloInput(days: number, hour: number): string {
  const day = new Date(TODAY + days * DAY).toISOString().slice(0, 10);
  return `${day}T${String(hour).padStart(2, "0")}:00`;
}

async function newSession(lecturer: Page, classId: string): Promise<string> {
  const created = await lecturer.request.post(`/api/classes/${classId}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

/** Four dates set through the api, days from now. */
async function saveDates(lecturer: Page, sessionId: string, days = [3, 17, 20, 27]) {
  const [start_at, play_deadline, debrief_deadline, test_deadline] = days.map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const session = await (await lecturer.request.get(`/api/class-sessions/${sessionId}`)).json();
  const saved = await lecturer.request.put(`/api/class-sessions/${sessionId}`, {
    data: { ai_mode: session.ai_mode, dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
}

test("the Lecturer sets the dates, the Testfrist is prefilled, and the Datolinje shows them", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const sessionId = await newSession(lecturer, klass.id);
  await lecturer.goto(`/klasseokter/${sessionId}`);
  const section = lecturer.getByRole("region", { name: dates.title });
  await expect(section.getByText(dates.none)).toBeVisible();

  await section.getByLabel(dates.names.start_at, { exact: true }).fill(osloInput(3, 10));
  await section.getByLabel(dates.names.play_deadline, { exact: true }).fill(osloInput(17, 23));
  await section.getByLabel(dates.names.debrief_deadline, { exact: true }).fill(osloInput(20, 23));
  // Prefilled 7 days after the Debrieffrist, and the Lecturer may change it.
  const testField = section.getByLabel(dates.names.test_deadline, { exact: true });
  await expect(testField).toHaveValue(osloInput(27, 23));
  await expect(section.getByText(dates.testPrefilled)).toBeVisible();
  await testField.fill(osloInput(28, 12));
  await expect(section.getByText(dates.testPrefilled)).toHaveCount(0);

  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const line = section.getByTestId("date-line");
  await expect(line.locator("[data-tick]")).toHaveCount(4);
  for (const name of Object.values(dates.names)) await expect(line).toContainText(name);

  // The saved dates come back in the fields, in Europe/Oslo.
  await lecturer.reload();
  await expect(lecturer.getByLabel(dates.names.start_at, { exact: true })).toHaveValue(osloInput(3, 10));
  await expect(lecturer.getByLabel(dates.names.test_deadline, { exact: true })).toHaveValue(osloInput(28, 12));
  await expect(lecturer.getByTestId("date-line").locator("[data-tick]")).toHaveCount(4);
});

test("a Spillfrist before the Startdato is refused with the reason under the field", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const sessionId = await newSession(lecturer, klass.id);
  await lecturer.goto(`/klasseokter/${sessionId}`);
  await lecturer.getByLabel(dates.names.start_at, { exact: true }).fill(osloInput(10, 10));
  const play = lecturer.getByLabel(dates.names.play_deadline, { exact: true });
  await play.fill(osloInput(5, 10));
  const save = lecturer.getByRole("button", { name: copy.save });
  await save.click();
  await expect(lecturer.getByRole("main").getByRole("alert")).toHaveText(dates.refused);
  await expect(save).toBeFocused();
  await expect(play).toHaveAttribute("aria-invalid", "true");
  await expect(play).toHaveAccessibleDescription(dates.errors.order(dates.names.start_at));
  // Nothing was stored.
  const stored = await (await lecturer.request.get(`/api/class-sessions/${sessionId}`)).json();
  expect([stored.start_at, stored.play_deadline]).toEqual([null, null]);
  await expect(lecturer.getByText(dates.none)).toBeVisible();
});

test("a half-typed date is refused under its field, never read as no date (Issue #100)", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const sessionId = await newSession(lecturer, klass.id);
  await saveDates(lecturer, sessionId);
  await lecturer.goto(`/klasseokter/${sessionId}`);
  const start = lecturer.getByLabel(dates.names.start_at, { exact: true });
  await start.fill("");
  await start.focus();
  await lecturer.keyboard.type("11");
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(start).toHaveAccessibleDescription(dates.errors.incomplete);
  await expect(start).toBeFocused();
  // Nothing was sent: the stored Startdato stands.
  const stored = await (await lecturer.request.get(`/api/class-sessions/${sessionId}`)).json();
  expect(stored.start_at).not.toBeNull();
});

test("the Lærerhjem names the session that lacks dates and the next date", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const sessionId = await newSession(lecturer, klass.id);
  await lecturer.goto("/laererhjem");
  const lacks = lecturer.getByRole("link", { name: copy.home.lacks(klass.name, 1, ["dates"]) });
  await expect(lacks).toBeVisible();
  await expect(lecturer.getByText(nb.classes.home.noDeadline)).toBeVisible();

  // A Class with no registered Student has no allocation to confirm (Story 5.9).
  await saveDates(lecturer, sessionId);
  await lecturer.reload();
  await expect(lecturer.getByText(nb.classes.home.nothingWaiting)).toBeVisible();
  const next = lecturer.getByRole("link", { name: copy.home.nextDate(dates.names.start_at, 1, klass.name) });
  await expect(next).toBeVisible();
  await next.click();
  await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${sessionId}$`));
});

test("dates saved on the Klasseøkt show on the Lærerhjem at once, without a reload", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  await newSession(lecturer, klass.id);
  await lecturer.goto("/laererhjem");
  await lecturer.getByRole("link", { name: copy.home.lacks(klass.name, 1, ["dates"]) }).click();
  await lecturer.getByLabel(dates.names.start_at, { exact: true }).fill(osloInput(3, 10));
  await lecturer.getByLabel(dates.names.play_deadline, { exact: true }).fill(osloInput(17, 23));
  await lecturer.getByLabel(dates.names.debrief_deadline, { exact: true }).fill(osloInput(20, 23));
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  // Back through the breadcrumb, inside the app: the cached «Venter» was read again.
  await lecturer.getByRole("link", { name: nb.homes.lecturerHome }).click();
  await expect(lecturer.getByText(nb.classes.home.nothingWaiting)).toBeVisible();
  await expect(
    lecturer.getByRole("link", { name: copy.home.nextDate(dates.names.start_at, 1, klass.name) }),
  ).toBeVisible();
});

test("a passed date is read-only, and a short play time is said without blocking", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const sessionId = await newSession(lecturer, klass.id);
  await saveDates(lecturer, sessionId);
  // The server's answer after the Start date with the least playing time configured; the rules
  // themselves are pinned by the api tests.
  await lecturer.route(`**/api/class-sessions/${sessionId}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({ response, json: { ...body, locked: true, passed_dates: ["start_at"], play_time_warning: true } });
  });
  await lecturer.goto(`/klasseokter/${sessionId}`);
  // The passed Startdato stands as text (Story 5.11, GitHub issue 103); the deadlines are still fields.
  const start = lecturer.getByRole("group", { name: dates.names.start_at, exact: true });
  await expect(start).toContainText(dates.passed);
  await expect(lecturer.locator("input#date-start_at")).toHaveCount(0);
  await expect(lecturer.locator("input#date-play_deadline")).toBeEditable();
  await expect(lecturer.getByText(dates.playTimeShort(36))).toBeVisible();
  await expect(lecturer.getByRole("button", { name: copy.lock.save })).toBeEnabled();
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveCount(0);
});

test("two sessions made in the same minute have labels of their own (Issue #98)", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  await newSession(lecturer, klass.id);
  await newSession(lecturer, klass.id);
  await lecturer.goto(`/klasser/${klass.id}`);
  const links = lecturer.getByRole("region", { name: copy.list.title }).getByRole("link");
  await expect(links).toHaveCount(2);
  const labels = await links.allTextContents();
  expect(new Set(labels).size).toBe(2);
  expect(labels[0]).toMatch(/^Klasseøkt 2, opprettet /);
  expect(labels[1]).toMatch(/^Klasseøkt 1, opprettet /);
});

test.describe("on a phone, 390 px", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("the chain diagram and the Datolinje show by a fading edge that they scroll (Issue #98)", async ({
    page,
    browser,
  }) => {
    const lecturer = await freshLecturer(page, browser);
    const klass = await freshClass(lecturer);
    const sessionId = await newSession(lecturer, klass.id);
    await saveDates(lecturer, sessionId);
    await lecturer.goto(`/klasseokter/${sessionId}`);
    for (const name of [copy.chain.title, dates.title]) {
      const region = lecturer.getByRole("group", { name });
      await expect(region).toBeVisible();
      const frame = region.locator("..");
      await expect(frame.locator('[data-fade="right"]')).toHaveAttribute("data-visible", "true");
      await expect(frame.locator('[data-fade="left"]')).toHaveAttribute("data-visible", "false");
      await region.evaluate((el) => el.scrollTo({ left: el.scrollWidth }));
      await expect(frame.locator('[data-fade="right"]')).toHaveAttribute("data-visible", "false");
      await expect(frame.locator('[data-fade="left"]')).toHaveAttribute("data-visible", "true");
    }
  });
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`the Datoer, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("pass axe with no page scroll, the fields in one column below 1024 px", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const klass = await freshClass(lecturer);
      const sessionId = await newSession(lecturer, klass.id);
      await saveDates(lecturer, sessionId);
      await lecturer.goto(`/klasseokter/${sessionId}`);
      await expect(lecturer.getByTestId("date-line").locator("[data-tick]")).toHaveCount(4);
      await expectAccessible(lecturer, vp.phone);
      if (vp.width < 1024) {
        const start = await lecturer.getByLabel(dates.names.start_at, { exact: true }).boundingBox();
        const play = await lecturer.getByLabel(dates.names.play_deadline, { exact: true }).boundingBox();
        expect(play!.y).toBeGreaterThan(start!.y + start!.height - 1);
        expect(Math.abs(play!.x - start!.x)).toBeLessThan(1);
      }
      await lecturer.goto("/laererhjem");
      await expect(lecturer.getByText(nb.classes.home.nothingWaiting)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
