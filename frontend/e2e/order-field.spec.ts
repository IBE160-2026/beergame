import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** Typing an Order and seeing where it lands (Story 6.11, FR-24, FR-73, NFR-6, AD-10, UX-DR14,
 * UX-DR17, UX-DR20, UX-DR78). As in `guided-week.spec.ts`, the game and its envelope are stand-ins
 * with the api's shapes: the engine's Grossist of a Classic game in Uke 11 (På vei 16, the Order
 * due in Uke 15, Game settings maximum 999), held to the engine by
 * `backend/tests/games/test_play_fixture.py`. Nothing is sent yet: every POST is recorded. */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const copy = nb.games.play;
const order = copy.order;

async function openPlay(page: Page): Promise<string[]> {
  const posts: string[] = [];
  await loginByApi(page, "student");
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().includes(`/api/me/games/${GAME_ID}`)) posts.push(request.url());
  });
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        seats: week11.table_status.seats,
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "running",
        week: 11,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) => route.fulfill({ json: week11 }));
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(11));
  return posts;
}

const field = (page: Page) => page.getByRole("textbox", { name: order.label(11) });
const confirm = (page: Page) => page.getByRole("button", { name: /^Bekreft ordre/ });

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const width of [320, 360, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("empty, typed, invalid and out of range: copy, look and no axe violation", async ({ page }) => {
      const phone = width < 1024;
      const posts = await openPlay(page);
      const input = field(page);
      // Empty.
      await expect(input).toHaveAttribute("type", "text");
      await expect(input).toHaveAttribute("inputmode", "numeric");
      await expect(input).toHaveAttribute("pattern", "[0-9]*");
      await expect(input).toHaveAttribute("placeholder", order.placeholder);
      await expect(input).toHaveValue("");
      await expect(input).toHaveAccessibleDescription(order.help("999"));
      await expect(page.getByText(order.last("8"))).toBeVisible();
      await expect(confirm(page)).toHaveText(order.confirm);
      await expect(confirm(page)).toHaveAttribute("aria-disabled", "true");
      await expectAccessible(page, phone);
      if (phone) {
        // Field and button fill the width at their token heights.
        const sizes = await page.evaluate(() => {
          const box = document.querySelector<HTMLElement>("[data-order-box]")!.getBoundingClientRect();
          const button = [...document.querySelectorAll<HTMLElement>("main button")].find((b) => b.textContent?.startsWith("Bekreft"))!;
          const main = document.querySelector<HTMLElement>("[data-order-field]")!.getBoundingClientRect();
          return { box: [box.width, box.height], button: [button.getBoundingClientRect().width, button.getBoundingClientRect().height], main: main.width };
        });
        expect(sizes.box[0]).toBeCloseTo(sizes.main, 0);
        expect(sizes.button[0]).toBeCloseTo(sizes.main, 0);
        expect(sizes.box[1]).toBe(54);
        expect(sizes.button[1]).toBeGreaterThanOrEqual(44);
        expect(sizes.main).toBeGreaterThan(width - 60);
      }
      // Every control of the field is a tap target of at least 44 px, at every width.
      const targets = await page.locator("[data-order-field] button").evaluateAll((els) =>
        els.map((el) => [el.getBoundingClientRect().width, el.getBoundingClientRect().height]),
      );
      expect(targets).toHaveLength(3);
      for (const [w, h] of targets) expect(Math.min(w!, h!)).toBeGreaterThanOrEqual(44);
      // Typed.
      await input.fill("24");
      await expect(confirm(page)).toHaveText(order.confirmOn("24"));
      await expect(confirm(page)).not.toHaveAttribute("aria-disabled", "true");
      await expect(page.getByText(order.arrives(15))).toBeVisible();
      await expect(page.locator("[data-join-line] line")).toHaveCount(1);
      await expectAccessible(page, phone);
      // Invalid.
      await input.fill("2,5");
      await expect(input).toHaveAttribute("aria-invalid", "true");
      await expect(page.getByText(order.invalid("999"))).toBeVisible();
      await expect(confirm(page)).toHaveAttribute("aria-disabled", "true");
      await expectAccessible(page, phone);
      // Out of range.
      await input.fill("1000");
      await expect(page.getByText(order.tooLarge("1 000", "999"))).toBeVisible();
      await expect(input).toHaveAttribute("aria-invalid", "true");
      const border = await page.locator("[data-order-box]").evaluate((el) => [getComputedStyle(el).borderTopColor, getComputedStyle(el).borderTopWidth]);
      // `restordre`, 1.4 px (drawn as whole device pixels by the browser).
      expect(border[0]).toBe("rgb(181, 66, 58)");
      await expectAccessible(page, phone);
      expect(posts).toEqual([]);
    });
  });
}

test("a valid 24 lands in the table and the Kjedebånd; Posisjon and Totalkostnad stay", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const posts = await openPlay(page);
  const position = page.locator('tr[data-row="position"]');
  const positionBefore = await position.innerText();
  const totalCost = page.getByText(nb.terms.totalCost, { exact: true }).locator("..");
  const total = await totalCost.innerText();
  await expect(page.locator("[data-join-line]")).toHaveCount(0);
  await field(page).fill("24");
  // Din ordre at nå and Levering in Uke 15, joined by a line from the one to the other.
  const from = page.locator('tr[data-row="order"] [data-join="from"]');
  const to = page.locator('tr[data-row="incomingDelivery"] [data-join="to"]');
  await expect(from).toContainText("24");
  await expect(to).toHaveText("24");
  const columns = await page.locator('thead th[scope="col"]').evaluateAll((ths) => ths.map((th) => th.getAttribute("data-col")));
  const toCol = await to.evaluate((el) => [...el.closest("tr")!.children].indexOf(el.closest("td")!));
  expect(columns[toCol - 1]).toBe("15");
  const ends = await page.evaluate(() => {
    const line = document.querySelector("[data-join-line] line")!;
    const origin = document.querySelector("[data-join-line]")!.getBoundingClientRect();
    const a = document.querySelector("[data-join=from]")!.getBoundingClientRect();
    const b = document.querySelector("[data-join=to]")!.getBoundingClientRect();
    const at = (name: string) => Number(line.getAttribute(name));
    return {
      start: [origin.left + at("x1") - a.right, origin.top + at("y1") - a.top],
      end: [origin.left + at("x2") - b.left, origin.top + at("y2") - b.bottom],
    };
  });
  for (const value of [...ends.start, ...ends.end]) expect(Math.abs(value)).toBeLessThan(1);
  // The Kjedebånd: «Din ordre 24», «På vei 16 + 24», the new box with its 1.5 px `ink` border.
  const band = page.locator('svg[data-chart="band"]');
  await expect(band.locator('text[data-label="order"]')).toHaveText("Din ordre 24");
  await expect(band.locator('text[data-label="supplyLine"]')).toHaveText("På vei 16 + 24");
  await expect(band.locator('rect[data-mark="typed"]')).toHaveAttribute("stroke-width", "1.5");
  await expect(page.locator("[data-chain-band] p.sr-only")).toHaveText(/På vei 16 pluss 24$/);
  // Nothing else moves while typing.
  expect(await position.innerText()).toBe(positionBefore);
  expect(await totalCost.innerText()).toBe(total);
  // A press with a valid value sends nothing yet (Story 6.12).
  await confirm(page).click();
  expect(posts).toEqual([]);
  // Clearing the field takes the preview away.
  await field(page).fill("");
  await expect(page.locator('rect[data-mark="typed"]')).toHaveCount(0);
  await expect(page.locator("[data-join-line]")).toHaveCount(0);
  await expect(band.locator('text[data-label="supplyLine"]')).toHaveText("På vei 16");
});

test("keyboard: Enter moves to the button, errors are announced on leaving or pressing, − and + keep focus at their limits", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const posts = await openPlay(page);
  const input = field(page);
  const alert = page.locator('[data-order-field] [role="alert"]');
  // The empty button is focusable and, pressed, gives the reason.
  await confirm(page).focus();
  await page.keyboard.press("Enter");
  await expect(alert).toHaveText(order.invalid("999"));
  await expect(page.locator("[data-order-field]").getByText(order.invalid("999")).first()).toBeVisible();
  await expect(confirm(page)).toBeFocused();
  // Typing: the reason shows at once but is not announced until the field is left.
  await input.fill("2a");
  await expect(alert).toHaveText("");
  await expect(input).toHaveAttribute("aria-invalid", "true");
  await input.press("Enter");
  await expect(confirm(page)).toBeFocused();
  await expect(alert).toHaveText(order.invalid("999"));
  // A valid value: Enter moves focus to the button and sends nothing.
  await input.fill("7");
  await input.press("Enter");
  await expect(confirm(page)).toBeFocused();
  await expect(confirm(page)).toHaveText(order.confirmOn("7"));
  // − and +: step by one, announce politely, keep focus where they cannot act.
  const fewer = page.getByRole("button", { name: order.fewer });
  const more = page.getByRole("button", { name: order.more });
  await input.fill("");
  await expect(fewer).toHaveAttribute("aria-disabled", "true");
  await more.click();
  await expect(input).toHaveValue("1");
  await expect(page.locator("[data-order-field] [aria-live=polite]")).toHaveText(order.stepped("1"));
  await fewer.click();
  await expect(input).toHaveValue("0");
  await expect(fewer).toHaveAttribute("aria-disabled", "true");
  await fewer.focus();
  await page.keyboard.press("Enter");
  await expect(input).toHaveValue("0");
  await expect(fewer).toBeFocused();
  await input.fill("998");
  await more.click();
  await expect(input).toHaveValue("999");
  await expect(more).toHaveAttribute("aria-disabled", "true");
  await expect(more).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(input).toHaveValue("999");
  expect(posts).toEqual([]);
});
