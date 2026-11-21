import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { fromOsloInput } from "../src/modules/sessions/dates";
import { labHourLine } from "../src/modules/sessions/lab-hours";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** Lab hours on the Klasseøkt (Story 5.6, FR-19, NFR-6, UX-DR51), on the local stack. Each test
 * makes a fresh Lecturer and Class through the api. The rules on the routes (ended, past, too
 * long, archived, the notices and the digest mail) are pinned by
 * `backend/tests/sessions/test_lab_hours.py`; here the screen. */
const copy = nb.sessions;
const l = copy.labHours;
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

/** The Europe/Oslo date `days` calendar days from today, as a date field takes it. */
function osloDate(days: number): string {
  return new Date(TODAY + days * DAY).toISOString().slice(0, 10);
}

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

type Lab = { id: string; starts_at: string; ends_at: string; place: string; ended: boolean };

/** A Lab hour added through the api, `days` from today, 14:15 to 16:00 in Oslo. */
async function addThroughApi(lecturer: Page, sessionId: string, days: number, place = "Datalab A2"): Promise<Lab> {
  const date = osloDate(days);
  const added = await lecturer.request.post(`/api/class-sessions/${sessionId}/lab-hours`, {
    data: { starts_at: fromOsloInput(`${date}T14:15`), ends_at: fromOsloInput(`${date}T16:00`), place },
    headers: CSRF,
  });
  expect(added.status()).toBe(201);
  return (await added.json()) as Lab;
}

async function labsOf(lecturer: Page, sessionId: string): Promise<Lab[]> {
  return (await (await lecturer.request.get(`/api/class-sessions/${sessionId}`)).json()).lab_hours as Lab[];
}

function datesSection(page: Page) {
  return page.getByRole("region", { name: copy.dates.title });
}

test("the Lecturer adds a Lab hour in place, and it shows on the Datolinje, in the legend and the list", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  const section = datesSection(lecturer);
  await expect(section.getByText(l.none)).toBeVisible();

  await section.getByRole("button", { name: l.add }).click();
  const form = section.getByRole("form", { name: l.addTitle });
  await expect(form.getByLabel(l.date, { exact: true })).toBeFocused();
  await expect(form.getByText(l.consequence)).toBeVisible();
  await form.getByLabel(l.date, { exact: true }).fill(osloDate(2));
  await form.getByLabel(l.start, { exact: true }).fill("14:15");
  await form.getByLabel(l.end, { exact: true }).fill("16:00");
  await form.getByLabel(l.place, { exact: true }).fill("Datalab A2");
  await form.getByRole("button", { name: l.saveAdd }).click();

  // The form closes; focus moves to the result line, and the square, legend and line show.
  await expect(section.getByRole("status").filter({ hasText: l.added })).toBeFocused();
  await expect(form).toHaveCount(0);
  const [saved] = await labsOf(lecturer, id);
  await expect(section.getByTestId("date-line").locator("[data-lab-hour]")).toHaveCount(1);
  await expect(section.getByText(l.legend("Datalab A2"))).toBeVisible();
  await expect(section.getByRole("listitem").filter({ hasText: labHourLine(saved) })).toBeVisible();

  // Saved at once: a reload keeps it.
  await lecturer.reload();
  await expect(datesSection(lecturer).getByTestId("date-line").locator("[data-lab-hour]")).toHaveCount(1);
  await expect(datesSection(lecturer).getByText(labHourLine(saved))).toBeVisible();
});

test("an end before the start, a missing place and a half-typed date are refused under their fields", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  const section = datesSection(lecturer);
  await section.getByRole("button", { name: l.add }).click();
  const form = section.getByRole("form", { name: l.addTitle });
  const date = form.getByLabel(l.date, { exact: true });
  await date.fill(osloDate(2));
  await form.getByLabel(l.start, { exact: true }).fill("14:15");
  await form.getByLabel(l.end, { exact: true }).fill("13:00");
  await form.getByRole("button", { name: l.saveAdd }).click();
  const end = form.getByLabel(l.end, { exact: true });
  await expect(end).toHaveAccessibleDescription(l.errors.endNotAfterStart);
  await expect(end).toHaveAttribute("aria-invalid", "true");
  await expect(end).toBeFocused();
  await expect(form.getByLabel(l.place, { exact: true })).toHaveAccessibleDescription(
    `${l.placeHint} ${l.errors.placeMissing}`,
  );

  // A date typed only in part reads as not filled in, never as no date.
  await date.fill("");
  await date.focus();
  await lecturer.keyboard.type("11");
  await form.getByRole("button", { name: l.saveAdd }).click();
  await expect(date).toHaveAccessibleDescription(l.errors.dateIncomplete);
  await expect(date).toBeFocused();
  expect(await labsOf(lecturer, id)).toEqual([]);

  // «Avbryt» closes the form and returns focus to the Lenke that opened it.
  await form.getByRole("button", { name: l.cancel }).click();
  await expect(form).toHaveCount(0);
  await expect(section.getByRole("button", { name: l.add })).toBeFocused();
});

test("a Lab hour is changed and removed in place, with the result line", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const first = await addThroughApi(lecturer, id, 2);
  await addThroughApi(lecturer, id, 5, "Rom 101");
  await lecturer.goto(`/klasseokter/${id}`);
  const section = datesSection(lecturer);
  await expect(section.getByText(l.legend("Datalab A2 og Rom 101"))).toBeVisible();
  await expect(section.getByTestId("date-line").locator("[data-lab-hour]")).toHaveCount(2);
  // While the form is open, «Lagre Klasseøkt» steps back and the form's save leads.
  const pageSave = lecturer.getByRole("button", { name: copy.save });
  const primaryColour = await pageSave.evaluate((el) => getComputedStyle(el).backgroundColor);
  const editFirst = section.getByRole("button", { name: l.editLabel(labHourLine(first)) });
  await editFirst.click();
  const form = section.getByRole("form", { name: l.editTitle });
  await expect(form.getByLabel(l.date, { exact: true })).toBeFocused();
  await expect(form.getByRole("button", { name: l.saveEdit })).toHaveCSS("background-color", primaryColour);
  await expect(pageSave).not.toHaveCSS("background-color", primaryColour);
  // «Avbryt» returns focus to the «Endre» that opened the form, and «Lagre Klasseøkt» leads again.
  await form.getByRole("button", { name: l.cancel }).click();
  await expect(editFirst).toBeFocused();
  await expect(pageSave).toHaveCSS("background-color", primaryColour);
  await editFirst.click();
  await expect(form.getByLabel(l.place, { exact: true })).toHaveValue("Datalab A2");
  await form.getByLabel(l.place, { exact: true }).fill("Datalab B1");
  await form.getByRole("button", { name: l.saveEdit }).click();
  await expect(section.getByRole("status").filter({ hasText: l.changed })).toBeFocused();
  const changed = { ...first, place: "Datalab B1" };
  await expect(section.getByText(labHourLine(changed))).toBeVisible();
  await expect(section.getByText(l.legend("Datalab B1 og Rom 101"))).toBeVisible();

  await section.getByRole("button", { name: l.editLabel(labHourLine(changed)) }).click();
  await section.getByRole("form", { name: l.editTitle }).getByRole("button", { name: l.remove }).click();
  await expect(section.getByRole("status").filter({ hasText: l.removed })).toBeFocused();
  await expect(section.getByText(labHourLine(changed))).toHaveCount(0);
  await expect(section.getByTestId("date-line").locator("[data-lab-hour]")).toHaveCount(1);
  expect((await labsOf(lecturer, id)).map((lab) => lab.place)).toEqual(["Rom 101"]);
});

test("for an Assistant the Lab hours are text; once started they still change", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const lab = await addThroughApi(lecturer, id, 2);
  const real = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  let answer = { ...real, can_manage: false };
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({ json: answer });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  const section = datesSection(lecturer);
  await expect(section.getByText(labHourLine(lab))).toBeVisible();
  await expect(section.getByRole("button", { name: l.add })).toHaveCount(0);
  await expect(section.getByRole("button", { name: l.editLabel(labHourLine(lab)) })).toHaveCount(0);

  // Locked (the Start date has passed): Lab hours stay editable; an ended one is marked, with no «Endre».
  answer = { ...real, locked: true, lab_hours: [{ ...lab, ended: true }, { ...lab, id: "x", place: "Rom 101" }] };
  await lecturer.reload();
  await expect(section.getByRole("button", { name: l.add })).toBeVisible();
  await expect(section.getByText(`${labHourLine(lab)} (${l.ended})`)).toBeVisible();
  await expect(section.getByRole("button", { name: l.edit })).toHaveCount(1);
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`the Lab hours, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("pass axe with a Lab hour listed and the form open with a refusal", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await addThroughApi(lecturer, id, 2);
      await lecturer.goto(`/klasseokter/${id}`);
      const section = datesSection(lecturer);
      await expect(section.getByTestId("date-line").locator("[data-lab-hour]")).toHaveCount(1);
      await section.getByRole("button", { name: l.add }).click();
      await section.getByRole("form", { name: l.addTitle }).getByRole("button", { name: l.saveAdd }).click();
      await expect(section.getByText(l.errors.placeMissing)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
