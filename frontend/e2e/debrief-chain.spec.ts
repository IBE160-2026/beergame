import { expect, type Locator, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { CHAIN, chainAnswer } from "./support/chain";
import { expectAccessible, expectReflow, test } from "./support/classes";
import { NO_REFLECTION } from "./support/reflection";
import { REVEAL } from "./support/reveal";

/** Debrief step 3, the whole chain (Story 9.5, FR-44, FR-73, NFR-6, UX-DR33, UX-DR34, UX-DR75,
 * UX-DR76, AD-10). From stand-in answers of the Debrief endpoints with the Explanation sent: the
 * heading, the Ukeskrubber (keys, step buttons, a press on the track), the four-Role Kjedebånd,
 * the Ordrestolper over the Rolle × Uke numbers on the same columns in one sideways scroll region,
 * Forsterkning, the polite reading after 300 ms, at 320, 360 and 1440 px with axe and with reduced
 * motion. The api's numbers against the stored game are `backend/tests/debrief/test_explanation.py`. */
const copy = nb.debrief.chain;
const SESSION = "01a1aaaa-0000-7000-8000-000000000095";
const DEBRIEF = "01a1aaaa-0000-7000-8000-0000000009d5";
const OPENED = {
  id: DEBRIEF,
  class_session_id: SESSION,
  game_id: "01a1aaaa-0000-7000-8000-0000000009a5",
  game_number: 17,
  role: "wholesaler",
  step: 1,
};
const SENT = { text: "Restordren vokste, så jeg bestilte mye.", length: 39, saved_at: "2026-11-21T12:00:00Z" };
const NAMES = ["Fabrikk", "Distributør", "Grossist (deg)", "Detaljist"];

async function chained(page: Page, { sent = true, chain = CHAIN as unknown } = {}) {
  await page.route(`**/api/me/class-sessions/${SESSION}/debrief`, (route) => route.fulfill({ json: OPENED }));
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) =>
    route.fulfill({ json: { weeks: REVEAL.weeks.map((w) => ({ week: w.week, net_inventory: 12 - w.week })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/explanation`, (route) => route.fulfill({ json: { explanation: sent ? SENT : null } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/2`, (route) =>
    route.fulfill({ json: { debrief_id: DEBRIEF, step: 2, reveal: REVEAL, chain: null } }),
  );
  const asked: string[] = [];
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/3`, (route) => {
    asked.push(route.request().url());
    return route.fulfill({ json: { debrief_id: DEBRIEF, step: 3, reveal: null, chain } });
  });
  // The reflection questions (Story 9.6) are `debrief-reflection.spec.ts`; here there are none.
  await page.route(`**/api/debriefs/${DEBRIEF}/reflection`, (route) => route.fulfill({ json: NO_REFLECTION }));
  return { asked, unroute: () => page.unrouteAll({ behavior: "ignoreErrors" }) };
}

async function centreX(locator: Locator): Promise<number> {
  const box = (await locator.boundingBox())!;
  return box.x + box.width / 2;
}

/** The dashed line stands over the chosen Uke's column. */
async function expectChosen(step: Locator, week: number) {
  const line = step.locator("svg[data-chart=order-bars] [data-mark=chosen]");
  const head = step.locator(`th[scope=col][data-col='${week}']`);
  await expect.poll(async () => Math.abs((await centreX(line)) - (await centreX(head)))).toBeLessThanOrEqual(1.5);
  await expect(step.locator("[data-chain-at]")).toHaveText(copy.at(week));
  await expect(step.getByRole("slider", { name: copy.scrubber })).toHaveAttribute("aria-valuetext", copy.week(week));
}

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("step 3: the scrubber spools the four-Role band and the bars, the numbers sit under the bars", async ({ page }) => {
      await loginByApi(page, "student");
      const stub = await chained(page);
      await page.goto(`/debrief/${SESSION}`);
      const step = page.locator("[data-debrief-chain]");
      await expect(step.getByRole("heading", { level: 2 })).toHaveAccessibleName(`${nb.debriefEntry.stepOf(3, 5)}: ${copy.heading}`);

      // The scrubber: a slider over the whole game, standing at the last Uke.
      const slider = step.getByRole("slider", { name: copy.scrubber });
      await expect(slider).toHaveAttribute("aria-valuemin", "1");
      await expect(slider).toHaveAttribute("aria-valuemax", "36");
      await expectChosen(step, 36);
      for (const name of [copy.back, copy.forward]) {
        const box = (await step.getByRole("button", { name }).boundingBox())!;
        expect(box.height).toBeGreaterThanOrEqual(44);
        expect(box.width).toBeGreaterThanOrEqual(44);
      }

      // The four-Role band: hidden from screen readers, own node marked, from Produksjon to Kundene.
      const band = step.locator("svg[data-variant=chain]");
      await expect(band).toBeVisible();
      await expect(band.locator("xpath=..")).toHaveAttribute("aria-hidden", "true");
      await expect(band.locator("[data-mark=node]")).toHaveCount(4);
      await expect(band.locator("[data-mark=node][data-own]")).toHaveCount(1);
      await expect(band.locator("[data-label=upstream]")).toHaveText(copy.production);
      await expect(band.locator("[data-label=downstream]")).toHaveText(copy.customers);
      const bandBox = (await band.boundingBox())!;
      for (const label of await band.locator("text").all()) {
        const box = (await label.boundingBox())!;
        expect(box.x).toBeGreaterThanOrEqual(bandBox.x - 0.5);
        expect(box.x + box.width).toBeLessThanOrEqual(bandBox.x + bandBox.width + 0.5);
      }

      // Keys, then the step buttons; the reading follows once the scrubber stands still.
      await slider.focus();
      await page.keyboard.press("Home");
      await expectChosen(step, 1);
      await page.keyboard.press("PageUp");
      await page.keyboard.press("ArrowRight");
      await expectChosen(step, 6);
      await page.keyboard.press("End");
      await page.keyboard.press("PageDown");
      await page.keyboard.press("ArrowDown");
      await expectChosen(step, 31);
      await step.getByRole("button", { name: copy.back }).click();
      await expectChosen(step, 30);
      const factory = CHAIN.roles[0]!.weeks[29]!;
      const held = factory.backlog > 0 ? `restordre ${factory.backlog}` : `lager ${factory.inventory}`;
      await expect(step.locator("[data-chain-reading]")).toHaveText(new RegExp(`^Uke 30\\. Fabrikk: ${held}, ordre ${factory.order}\\. Distributør: `));
      await expect(step.locator("[data-chain-reading]")).toHaveAttribute("aria-live", "polite");

      // Ordrestolper over the Rolle × Uke numbers: Fabrikk at the top, the api's Orders, each
      // first large Order marked, Forsterkning at the right.
      const table = step.getByRole("table", { name: copy.heading });
      await expect(table.locator("tbody th[scope=row]")).toHaveText(NAMES);
      await expect(table.locator("tr[data-role=factory] td:not([data-amplification])")).toHaveText(CHAIN.roles[0]!.weeks.map((w) => String(w.order)));
      await expect(table.locator("td[data-amplification]")).toHaveText(["7,6×", "6,0×", "4,1×", "1,8×"]);
      const bars = step.locator("svg[data-chart=order-bars]");
      await expect(bars.locator("[data-mark=first-large]")).toHaveCount(4);
      await expect(bars.locator("[data-mark=first-large] text")).toHaveText(CHAIN.roles.map((r) => copy.week(r.first_large_order_week)));
      await expect(step.locator("[data-amplification-line]")).toHaveText(
        copy.amplificationLine(["Detaljist 1,8×", "Grossist 4,1×", "Distributør 6,0×", "Fabrikk 7,6×"]),
      );
      await expect(step.locator("[data-chain-capacity]")).toHaveCount(0);
      await expectAccessible(page, viewport.phone);

      // Narrow: bars and numbers scroll sideways together in their region; the labels stay.
      const region = step.getByRole("region", { name: copy.region });
      const scrolls = await region.evaluate((el) => el.scrollWidth > el.clientWidth);
      expect(scrolls).toBe(viewport.phone);
      if (viewport.phone) {
        const label = table.locator("tbody th[scope=row]").first();
        const before = (await label.boundingBox())!.x;
        await region.evaluate((el) => el.scrollTo(0, 0));
        await slider.focus();
        await page.keyboard.press("End");
        // The chosen Uke's column is brought into view.
        await expect.poll(async () => region.evaluate((el) => el.scrollLeft)).toBeGreaterThan(0);
        await expectChosen(step, 36);
        expect(Math.abs((await label.boundingBox())!.x - before)).toBeLessThanOrEqual(1);
      }
      await expectReflow(page, viewport.phone);
      await stub.unroute();
    });
  });
}

test("with reduced motion the chain shows each Uke at once; a press on the track chooses a Uke", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await loginByApi(page, "student");
  const stub = await chained(page);
  await page.goto(`/debrief/${SESSION}`);
  const step = page.locator("[data-debrief-chain]");
  const slider = step.getByRole("slider", { name: copy.scrubber });
  await slider.focus();
  await page.keyboard.press("Home");
  await expectChosen(step, 1);
  const box = (await slider.boundingBox())!;
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  const chosen = Number(await slider.getAttribute("aria-valuenow"));
  expect(Math.abs(chosen - 18.5)).toBeLessThanOrEqual(1.5);
  await expectChosen(step, chosen);
  await stub.unroute();
});

test("a capped Role states its capacity and reads both stock and backlog", async ({ page }) => {
  await loginByApi(page, "student");
  const chain = chainAnswer({ capacity: { factory: 12 } });
  const stub = await chained(page, { chain });
  await page.goto(`/debrief/${SESSION}`);
  const step = page.locator("[data-debrief-chain]");
  await expect(step.locator("[data-chain-capacity]")).toHaveText(copy.capacity("Fabrikk", "12"));
  const worst = chain.roles[0]!.weeks.find((w) => w.backlog > 0 && w.inventory > 0)!;
  await step.getByRole("slider", { name: copy.scrubber }).focus();
  await page.keyboard.press("Home");
  for (let i = 1; i < worst.week; i++) await page.keyboard.press("ArrowRight");
  await expectChosen(step, worst.week);
  await expect(step.locator("[data-chain-reading]")).toContainText(
    `Fabrikk: lager ${worst.inventory}, restordre ${worst.backlog}, ordre ${worst.order}.`,
  );
  await expect(step.locator("svg[data-variant=chain] [data-label=roleNumbers]").first()).toHaveText(copy.stock(String(worst.inventory)));
  await stub.unroute();
});

test("without a sent Explanation there is no step 3, and it is not asked for", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await chained(page, { sent: false });
  await page.goto(`/debrief/${SESSION}`);
  await expect(page.getByRole("textbox", { name: nb.debriefEntry.explanation.prompt })).toBeVisible();
  await expect(page.locator("[data-debrief-chain]")).toHaveCount(0);
  expect(stub.asked).toEqual([]);
  await stub.unroute();
});

test.describe("1280 px", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("the four-Role band spans the step like the bars under it", async ({ page }) => {
    await loginByApi(page, "student");
    const stub = await chained(page);
    await page.goto(`/debrief/${SESSION}`);
    const step = page.locator("[data-debrief-chain]");
    const band = (await step.locator("svg[data-variant=chain]").boundingBox())!;
    const bars = (await step.getByRole("region", { name: copy.region }).boundingBox())!;
    expect(Math.abs(band.x - bars.x)).toBeLessThanOrEqual(2);
    expect(Math.abs(band.x + band.width - (bars.x + bars.width))).toBeLessThanOrEqual(2);
    await stub.unroute();
  });
});
