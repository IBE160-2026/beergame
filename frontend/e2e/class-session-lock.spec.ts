import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { osloDateText, toOsloInput } from "../src/modules/sessions/dates";
import { expectAccessible, freshClass, freshLecturer } from "./support/classes";

/** The locked Klasseøkt (Story 5.11, FR-12, FR-18, UX-DR48, GitHub issue 103), on the local stack. Each
 * test makes a fresh Lecturer, Class and Class session through the api. The sweep's lock and its
 * snapshot are pinned by `backend/tests/sessions/test_lock.py`. Here the server's answer after the
 * lock is laid over the real one, and the screen is checked. */
const copy = nb.sessions;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const ALL_DATES = ["start_at", "play_deadline", "debrief_deadline", "test_deadline"];

async function datedSession(lecturer: Page): Promise<{ id: string; lockedAt: string }> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const session = await created.json();
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const saved = await lecturer.request.put(`/api/class-sessions/${session.id}`, {
    data: { ai_mode: session.ai_mode, dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  return { id: session.id, lockedAt: start_at };
}

/** Every answer about the session, the save's too, as the server gives it once locked. */
async function locked(lecturer: Page, id: string, changes: Record<string, unknown>) {
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    const response = await route.fetch();
    if (!response.ok()) return route.fulfill({ response });
    await route.fulfill({ response, json: { ...(await response.json()), locked: true, ...changes } });
  });
}

test("locked, everything frozen stands as text and «Lagre frister» saves a deadline", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const { id, lockedAt } = await datedSession(lecturer);
  await locked(lecturer, id, { locked_at: lockedAt, passed_dates: ["start_at"] });
  await lecturer.goto(`/klasseokter/${id}`);

  await expect(lecturer.getByText(copy.lock.lockedAt(osloDateText(lockedAt)))).toBeVisible();
  await expect(lecturer.getByText(copy.lock.open)).toBeVisible();
  await expect(lecturer.getByText(copy.defaults)).toHaveCount(0);
  await expect(lecturer.getByText(copy.delaySources)).toHaveCount(0);
  // No control for a frozen value: no Valgknapper, no Bryter, no settings to open.
  await expect(lecturer.getByRole("radio")).toHaveCount(0);
  await expect(lecturer.getByRole("switch")).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.edit.open })).toHaveCount(0);
  await expect(lecturer.getByRole("heading", { name: copy.choices.aiMode })).toBeVisible();
  // The passed Startdato as text; the deadlines ahead stay fields.
  await expect(lecturer.getByRole("group", { name: copy.dates.names.start_at, exact: true })).toContainText(
    osloDateText(lockedAt),
  );
  await expect(lecturer.locator("input#date-start_at")).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveCount(0);
  const save = lecturer.getByRole("button", { name: copy.lock.save });
  await expect(save).toHaveAccessibleDescription(copy.lock.saveHint);

  const testField = lecturer.locator("input#date-test_deadline");
  const later = new Date(Date.now() + 30 * DAY).toISOString();
  await testField.fill(toOsloInput(later));
  await save.click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.lock.saved })).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  expect(toOsloInput(stored.test_deadline)).toBe(toOsloInput(later));
});

test("locked with every date passed, the Klasseøkt has no save at all", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const { id } = await datedSession(lecturer);
  // Locked by the sweep a minute ago or refused: no `locked_at` yet.
  await locked(lecturer, id, { locked_at: null, passed_dates: ALL_DATES });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(copy.lock.pending)).toBeVisible();
  await expect(lecturer.getByText(copy.lock.labHoursOpen, { exact: true })).toBeVisible();
  for (const name of Object.values(copy.dates.names)) {
    await expect(lecturer.getByRole("group", { name, exact: true })).toContainText(copy.dates.passed);
  }
  await expect(lecturer.locator("input[type=datetime-local]")).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.lock.save })).toHaveCount(0);
});

test("locked before the Startdato (an early start), the Startdato stands as text too", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const { id } = await datedSession(lecturer);
  await locked(lecturer, id, { locked_at: new Date().toISOString(), passed_dates: [] });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByRole("group", { name: copy.dates.names.start_at, exact: true })).toContainText(
    copy.dates.lockedStart,
  );
  await expect(lecturer.locator("input#date-start_at")).toHaveCount(0);
  await expect(lecturer.locator("input#date-play_deadline")).toBeEditable();
  // «Lagre frister» sits in the Datoer section, under the fields it saves.
  const dates = lecturer.getByRole("region", { name: copy.dates.title });
  await expect(dates.getByRole("button", { name: copy.lock.save })).toBeVisible();
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of SIZES) {
  test.describe(`the locked Klasseøkt, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("passes axe", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const { id, lockedAt } = await datedSession(lecturer);
      await locked(lecturer, id, { locked_at: lockedAt, passed_dates: ["start_at"] });
      await lecturer.goto(`/klasseokter/${id}`);
      await expect(lecturer.getByRole("button", { name: copy.lock.save })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
