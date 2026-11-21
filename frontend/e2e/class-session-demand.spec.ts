import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { GROUP } from "../src/lib/number-format";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** Choosing the Demand pattern and its seed on the Klasseøkt (Story 5.4, FR-13, NFR-6, Issue #98),
 * on the local stack. Each test makes a fresh Lecturer and Class through the api. Every rule and
 * range is pinned through the routes by `backend/tests/sessions/test_demand.py`; here the screen. */
const copy = nb.sessions;
const edit = copy.edit;
const d = edit.demand;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

const field = (page: Page, label: string) => page.getByLabel(label, { exact: true });
const chainText = (page: Page) => page.locator("figcaption");

test("a random pattern keeps the server's seed, saves, and its series shows as a table", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const seed = String((await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).game_settings.demand_seed);
  await lecturer.goto(`/klasseokter/${id}`);
  // Classic: «Kundene» in the chain has the demand under it, as mockup 03 (Issue #98).
  const chain = lecturer.getByRole("img", { name: /Kundenes etterspørsel: 4, så 8 fra Uke 5/ });
  await expect(chain).toBeVisible();
  await expect(chain.getByText("4, så 8", { exact: true })).toBeVisible();
  await expect(chain.getByText("fra Uke 5", { exact: true })).toBeVisible();
  // The Classic series, read before the change: Week 5 steps to 8.
  await lecturer.getByRole("button", { name: edit.series.show }).click();
  const table = lecturer.getByRole("table", { name: edit.series.caption });
  const cell = (week: number) => table.getByRole("row").nth(week).getByRole("cell");
  await expect(cell(4)).toHaveText("4");
  await expect(cell(5)).toHaveText("8");

  await lecturer.getByRole("button", { name: edit.open }).click();
  const pattern = field(lecturer, d.pattern);
  await expect(pattern).toHaveValue("step");
  await expect(field(lecturer, d.changeWeek)).toHaveValue("5");
  await expect(field(lecturer, d.seed)).toHaveCount(0);
  await pattern.selectOption("random");
  // The step's start carries over as the mean; the seed is the one drawn at creation.
  await expect(field(lecturer, d.mean)).toHaveValue("4");
  await expect(field(lecturer, d.seed)).toHaveValue(seed);
  await field(lecturer, d.mean).fill("8");
  await field(lecturer, d.spread).fill("2");
  // A seed out of range stands under «Frø» with its range.
  const seedField = field(lecturer, d.seed);
  await seedField.fill("-1");
  const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/settings-check`);
  await seedField.blur();
  await checked;
  await expect(seedField).toHaveAttribute("aria-invalid", "true");
  await expect(seedField).toHaveAccessibleDescription(
    `${d.seedHint} ${edit.errors.outOfRange("0", `999${GROUP}999${GROUP}999`)}`,
  );
  await seedField.fill("42");
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();

  await expect(lecturer.getByText(copy.values.random(8, 2), { exact: true })).toBeVisible();
  // The list names the seed of a pattern that draws.
  await expect(lecturer.getByRole("definition").filter({ hasText: /^42$/ })).toBeVisible();
  await expect(chain).toHaveCount(0);
  await expect(chainText(lecturer)).toContainText("Kundenes etterspørsel: Tilfeldig, 8 ± 2.");
  await expect(lecturer.getByRole("img").getByText("8 ± 2", { exact: true })).toBeVisible();

  // Asked for again after the save, the table holds the new series, not the Classic one.
  await lecturer.getByRole("button", { name: edit.series.show }).click();
  await expect(table).toBeVisible();
  await expect(lecturer.getByRole("button", { name: edit.series.hide })).toHaveAttribute("aria-expanded", "true");
  const series = (await (await lecturer.request.get(`/api/class-sessions/${id}/demand-series`)).json()).demand as number[];
  expect(series).toHaveLength(36);
  await expect(table.getByRole("row")).toHaveCount(37);
  await expect(table.getByRole("columnheader")).toHaveText([edit.series.week, edit.series.demand]);
  for (const week of [1, 36]) {
    const row = table.getByRole("row").nth(week);
    await expect(row.getByRole("rowheader")).toHaveText(String(week));
    await expect(row.getByRole("cell")).toHaveText(String(series[week - 1]));
  }
  expect(series.slice(0, 5)).not.toEqual([4, 4, 4, 4, 8]);
  const stored = (await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).game_settings;
  expect([stored.demand, stored.demand_seed]).toEqual([{ kind: "random", mean: 8, spread: 2 }, 42]);
});

test("a fixed series of the wrong length is refused under its field and stores nothing", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await lecturer.getByRole("button", { name: edit.open }).click();
  await field(lecturer, d.pattern).selectOption("fixed");
  const values = field(lecturer, d.values);
  // Several lines: a series of 36–52 numbers is read whole (Issue #102).
  await expect(values).toHaveJSProperty("tagName", "TEXTAREA");
  // The «Mønster» select is set in Source Sans 3, as the fields are.
  expect(
    await field(lecturer, d.pattern).evaluate((element) => getComputedStyle(element).fontFamily),
  ).toContain("Source Sans 3");
  await values.fill("4 4 4 4 8 8");
  const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/settings-check`);
  await values.blur();
  await checked;
  await expect(values).toHaveAttribute("aria-invalid", "true");
  await expect(values).toHaveAccessibleDescription(`${d.valuesHint} ${edit.errors.fixedLength("36")}`);

  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("alert").filter({ hasText: edit.refused })).toBeVisible();
  const stored = (await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).game_settings;
  expect(stored.demand.kind).toBe("step");

  // 36 Weeks, typed with commas and over two lines: saved, and named in the list and the chain.
  const series = Array.from({ length: 36 }, (_, i) => (i < 10 ? 4 : 6));
  await values.fill(`${series.slice(0, 18).join(", ")}\n${series.slice(18).join(", ")}`);
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  await expect(lecturer.getByText(copy.values.fixed(36), { exact: true })).toBeVisible();
  await expect(chainText(lecturer)).toContainText("Fast serie over 36 uker");
});

test("a session that has started shows the Demand pattern read-only, and its series", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  // The server's answer after the Start date; the 409 itself is pinned by the api tests.
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), locked: true } });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(nb.sessions.lock.pending)).toBeVisible();
  await expect(lecturer.getByRole("button", { name: edit.open })).toHaveCount(0);
  await expect(field(lecturer, d.pattern)).toHaveCount(0);
  await lecturer.getByRole("button", { name: edit.series.show }).click();
  await expect(lecturer.getByRole("table", { name: edit.series.caption }).getByRole("row")).toHaveCount(37);
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`the Demand pattern, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("passes axe with the pattern's fields, an error and the series showing", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      await lecturer.getByRole("button", { name: edit.series.show }).click();
      await expect(lecturer.getByRole("table", { name: edit.series.caption })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      await lecturer.getByRole("button", { name: edit.open }).click();
      await field(lecturer, d.pattern).selectOption("step+noise");
      const spread = field(lecturer, d.spread);
      await spread.fill("30");
      const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/settings-check`);
      await spread.blur();
      await checked;
      await expect(spread).toHaveAttribute("aria-invalid", "true");
      await expect(field(lecturer, d.seed)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
