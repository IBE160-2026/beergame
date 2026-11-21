import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, test } from "./support/classes";
import { REVEAL } from "./support/reveal";

/** Debrief step 2, the reveal of customer demand (Story 9.4, FR-44, FR-73, FR-84, NFR-6, UX-DR31,
 * UX-DR32, UX-DR75, AD-10). From stand-in answers of the Debrief endpoints with the Explanation
 * sent: the api's heading, the Etterspørselsbånd over the table Uke / Kundene / Ordre inn / Din
 * ordre in one sideways scroll region with a sticky label column, the exercise named, at 320, 360
 * (also 200 % text) and 1440 px with axe. The api's rules and its numbers against the stored game
 * are `backend/tests/debrief/test_explanation.py`; a live game in `debrief-explanation.spec.ts`. */
const copy = nb.debrief.reveal;
const SESSION = "01a1aaaa-0000-7000-8000-000000000094";
const DEBRIEF = "01a1aaaa-0000-7000-8000-0000000009d4";
const OPENED = {
  id: DEBRIEF,
  class_session_id: SESSION,
  game_id: "01a1aaaa-0000-7000-8000-0000000009a4",
  game_number: 17,
  role: "wholesaler",
  step: 1,
};
const SENT = { text: "Restordren vokste, så jeg bestilte mye.", length: 39, saved_at: "2026-11-21T12:00:00Z" };
const BAR_11 = "[data-mark=order][data-week='11']";

/** The open Debrief with the Explanation sent (or not); step 2 answers the reveal, or fails
 * `failures` times first. */
async function revealed(page: Page, { failures = 0, sent = true } = {}) {
  let left = failures;
  await page.route(`**/api/me/class-sessions/${SESSION}/debrief`, (route) => route.fulfill({ json: OPENED }));
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) =>
    route.fulfill({ json: { weeks: REVEAL.weeks.map((w) => ({ week: w.week, net_inventory: 12 - w.week })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/explanation`, (route) => route.fulfill({ json: { explanation: sent ? SENT : null } }));
  const asked: string[] = [];
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/2`, (route) => {
    asked.push(route.request().url());
    if (left-- > 0) return route.fulfill({ status: 500, json: { error: { code: "internal_error", message: "x", fields: {} } } });
    return route.fulfill({ json: { debrief_id: DEBRIEF, step: 2, reveal: REVEAL } });
  });
  return { asked, unroute: () => page.unrouteAll({ behavior: "ignoreErrors" }) };
}

function stepHeading(page: Page) {
  return page.locator("[data-debrief-reveal]").getByRole("heading", { level: 2 });
}

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false },
  { name: "360 px with 200 % text", width: 360, height: 740, phone: true, text200: true },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("step 2: the heading, the band over the table on the same columns, the exercise named", async ({ page }) => {
      if (viewport.text200) {
        await page.addInitScript(() => {
          document.addEventListener("DOMContentLoaded", () => {
            const style = document.createElement("style");
            style.textContent = "html { font-size: 200% !important; }";
            document.head.appendChild(style);
          });
        });
      }
      await loginByApi(page, "student");
      const stub = await revealed(page);
      await page.goto(`/debrief/${SESSION}`);
      const step = page.locator("[data-debrief-reveal]");
      await expect(stepHeading(page)).toHaveAccessibleName(`${nb.debriefEntry.stepOf(2, 5)}: ${REVEAL.heading}`);

      // The band: not interactive, hidden from screen readers; the table is its alternative.
      const band = step.locator("svg[data-chart=demand-band]");
      await expect(band).toBeVisible();
      await expect(band).toHaveAttribute("aria-hidden", "true");
      await expect(band.locator("[data-mark=order]")).toHaveCount(36);
      await expect(band.locator("[data-label=largest]")).toHaveText(copy.largestOrder("24", 11));
      await expect(band.locator("[data-label=demand]")).toHaveText(copy.demandLabel("8"));
      await expect(step.getByText(copy.incomingKey, { exact: true })).toBeVisible();

      // The table: Uke / Kundene / Ordre inn / Din ordre with `th` scopes, the api's numbers.
      const table = step.getByRole("table", { name: REVEAL.heading });
      await expect(table.locator("th[scope=col]")).toHaveCount(36);
      await expect(table.locator("tbody th[scope=row]")).toHaveText([copy.rows.demand, copy.rows.incoming, copy.rows.order]);
      await expect(table.locator("tr[data-row=demand] td")).toHaveText(REVEAL.weeks.map((w) => String(w.demand)));
      await expect(table.locator("tr[data-row=incoming_order] td")).toHaveText(REVEAL.weeks.map((w) => String(w.incoming_order)));
      await expect(table.locator("tr[data-row=order] td")).toHaveText(REVEAL.weeks.map((w) => String(w.order)));

      // Each bar stands over its own column.
      const bar = await band.locator(BAR_11).boundingBox();
      const head = await table.locator("th[data-col='11']").boundingBox();
      expect(Math.abs(bar!.x + bar!.width / 2 - (head!.x + head!.width / 2))).toBeLessThanOrEqual(1);

      await expect(step.getByText(copy.named, { exact: true })).toBeVisible();
      await expect(step.getByText(copy.saw(copy.definite.retailer), { exact: true })).toBeVisible();
      await expectAccessible(page, viewport.phone);

      // Narrow: band and table scroll sideways together in one region; the labels stay.
      const region = step.getByRole("region", { name: copy.region });
      const label = table.locator("tbody th[scope=row]").first();
      const before = await label.boundingBox();
      const scrolls = await region.evaluate((el) => el.scrollWidth > el.clientWidth);
      expect(scrolls).toBe(viewport.phone);
      if (viewport.phone) {
        const barBefore = await band.locator(BAR_11).boundingBox();
        await region.evaluate((el) => el.scrollTo(el.scrollWidth, 0));
        await expect.poll(async () => (await band.locator(BAR_11).boundingBox())!.x).toBeLessThan(barBefore!.x);
        const headAfter = await table.locator("th[data-col='11']").boundingBox();
        const barAfter = await band.locator(BAR_11).boundingBox();
        expect(Math.abs(barAfter!.x + barAfter!.width / 2 - (headAfter!.x + headAfter!.width / 2))).toBeLessThanOrEqual(1);
        expect(Math.abs((await label.boundingBox())!.x - before!.x)).toBeLessThanOrEqual(1);
      }
      await expectReflow(page, viewport.phone);
      await stub.unroute();
    });
  });
}

test("a failed read of step 2 says so and can be tried again", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await revealed(page, { failures: 1 });
  await page.goto(`/debrief/${SESSION}`);
  const failed = page.locator("[data-debrief-reveal=failed]");
  await expect(failed.getByRole("alert")).toHaveText(copy.loadFailed);
  await failed.getByRole("button", { name: nb.system.retry }).click();
  await expect(stepHeading(page)).toHaveAccessibleName(`${nb.debriefEntry.stepOf(2, 5)}: ${REVEAL.heading}`);
  await stub.unroute();
});

test("without a sent Explanation there is no step 2, and it is not asked for", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await revealed(page, { sent: false });
  await page.goto(`/debrief/${SESSION}`);
  await expect(page.getByRole("textbox", { name: nb.debriefEntry.explanation.prompt })).toBeVisible();
  await expect(page.locator("[data-debrief-reveal]")).toHaveCount(0);
  expect(stub.asked).toEqual([]);
  await stub.unroute();
});
