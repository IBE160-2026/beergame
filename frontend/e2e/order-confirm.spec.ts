import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import week14 from "../src/modules/games/fixtures/play-week-14.json";
import { DEMO_PASSWORD, DEMO_USERS, loginAs, untilHydrated } from "./support/auth";
import { expectAccessible } from "./support/classes";
import { confirmButton as confirm, drafts, GAME_ID, openPlay, orderField as field, refetchPlay as refetch } from "./support/play";

/** Confirming the Order and keeping what was typed (Story 6.12, FR-24, FR-73, NFR-6, AD-10,
 * UX-DR59, UX-DR60), on the stand-in play screen of `support/play.ts`. */
const copy = nb.games.play;
const order = copy.order;

const typedBox = (page: Page) => page.locator('svg[data-chart="band"] rect[data-mark="typed"]');

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const width of [320, 360, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("sending, then confirmed: one Order, focus kept then on the message, no axe violation", async ({ page }) => {
      const phone = width < 1024;
      const stub = await openPlay(page);
      let release: () => void = () => undefined;
      const held = new Promise<void>((resolve) => (release = resolve));
      const answer = stub.answer;
      stub.answer = async (route) => {
        await held;
        await answer(route);
      };
      await field(page).fill("24");
      await confirm(page).click();
      // Submitting: the button keeps focus, busy and unavailable; the field is read-only.
      await expect(confirm(page)).toHaveText(order.sending("24"));
      await expect(confirm(page)).toHaveAttribute("aria-busy", "true");
      await expect(confirm(page)).toHaveAttribute("aria-disabled", "true");
      await expect(confirm(page)).toBeFocused();
      await expect(field(page)).toHaveAttribute("readonly", "");
      await page.keyboard.press("Enter"); // a further press is ignored
      await expect(page.locator("[data-order-field] [data-order-announce]")).toHaveText(order.sending("24"));
      const targets = await page.locator("[data-order-field] button").evaluateAll((els) =>
        els.map((el) => Math.min(el.getBoundingClientRect().width, el.getBoundingClientRect().height)),
      );
      for (const size of targets) expect(size).toBeGreaterThanOrEqual(44);
      await expectAccessible(page, phone);
      release();
      // Confirmed: the message has focus; the Order stays in the table and the Kjedebånd.
      const sent = page.getByText(order.sent("24"));
      await expect(sent).toBeFocused();
      await expect(sent).toHaveAttribute("tabindex", "-1");
      await expect(page.getByText(order.next)).toBeVisible();
      await expect(page.locator("[data-order-field] input, [data-order-field] button")).toHaveCount(0);
      expect(stub.posts).toEqual([{ order: 24 }]);
      await expect(page.locator('tr[data-row="order"] [data-join="from"]')).toContainText("24");
      await expect(page.locator('tr[data-row="incomingDelivery"] [data-join="to"]')).toHaveText("24");
      await expect(page.locator("[data-join-line]")).toHaveCount(1);
      await expect(page.locator('svg[data-chart="band"] text[data-label="supplyLine"]')).toHaveText("På vei 16 + 24");
      await expect(typedBox(page)).toHaveCount(1);
      await expectAccessible(page, phone);
      expect(await drafts(page)).toEqual([]);
    });

    test("a typed value comes back after a reload and is not sent", async ({ page }) => {
      const stub = await openPlay(page);
      await field(page).fill("24");
      // Kept under the signed-in User and the field: another User on this browser starts empty.
      const me = (await (await page.request.get("/api/auth/me")).json()) as { user: { id: string } };
      expect(await drafts(page)).toEqual([`olspillet:draft:${me.user.id}:order:${GAME_ID}:11`]);
      await page.reload();
      await expect(field(page)).toHaveValue("24");
      await expect(confirm(page)).toHaveText(order.confirmOn("24"));
      await expect(typedBox(page)).toHaveCount(1);
      await expectAccessible(page, width < 1024);
      expect(stub.posts).toEqual([]);
    });
  });
}

test("the typed number clears when the Uke moves on (deferred from Story 6.11)", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const stub = await openPlay(page);
  await field(page).fill("30");
  await expect(page.locator("[data-join-line]")).toHaveCount(1);
  stub.envelope = week14;
  await refetch(page);
  const next = page.getByRole("textbox", { name: order.label(14) });
  await expect(next).toHaveValue("");
  await expect(typedBox(page)).toHaveCount(0);
  await expect(page.locator("[data-join-line]")).toHaveCount(0);
  await expect(page.locator('[data-join="from"], [data-join="to"]')).toHaveCount(0);
  await expect(page.locator('svg[data-chart="band"] text[data-label="order"]')).toHaveText(nb.games.play.band.order);
  expect(await drafts(page)).toEqual([]); // Uke 11's draft is of no use any more
  expect(stub.posts).toEqual([]);
});

test("the Order that completes the Uke shows the next Uke with focus on its heading", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const stub = await openPlay(page);
  stub.answer = async (route) => {
    stub.envelope = week14;
    await route.fulfill({ status: 204 });
  };
  await field(page).fill("24");
  await confirm(page).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(14));
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(page.getByRole("textbox", { name: order.label(14) })).toHaveValue("");
});

test("a send that fails keeps the value, editable, with focus on the button", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const stub = await openPlay(page);
  stub.answer = (route) => route.fulfill({ status: 503, json: { error: { code: "unavailable", message: "x" } } });
  await field(page).fill("24");
  await confirm(page).click();
  // Story 6.13 says so in words; `order-failures.spec.ts` covers the failure states.
  await expect(confirm(page)).toHaveText(order.retry("24"));
  await expect(confirm(page)).not.toHaveAttribute("aria-busy");
  await expect(confirm(page)).toBeFocused();
  await expect(field(page)).toHaveValue("24");
  await expect(field(page)).not.toHaveAttribute("readonly");
  expect(stub.posts).toHaveLength(1);
  // The draft is still kept: a reload after the failure brings 24 back.
  await page.reload();
  await expect(field(page)).toHaveValue("24");
});

test("a send refused as already ordered reads the envelope again and shows the stored Order", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const stub = await openPlay(page);
  stub.answer = async (route) => {
    stub.envelope = { ...week11, turn: { ...week11.turn, order: 9 } }; // another device's Order
    await route.fulfill({ status: 409, json: { error: { code: "order_exists", message: "x" } } });
  };
  await field(page).fill("24");
  await confirm(page).click();
  await expect(page.getByText(order.sent("9"))).toBeVisible();
  await expect(page.locator("[data-order-field] input")).toHaveCount(0);
  expect(stub.posts).toEqual([{ order: 24 }]);
});

test("after the session ends, logging in again brings the typed value back unsent", async ({ page, context }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const stub = await openPlay(page);
  await field(page).fill("24");
  const [cookie] = (await context.cookies()).filter((c) => c.name === "olspillet_session");
  await context.addCookies([{ ...cookie!, value: "utgatt" }]);
  await refetch(page);
  await expect(page).toHaveURL(/\/logg-inn\?neste=%2Fspill%2F.+&utlopt=1$/);
  await expect(page.getByText(nb.auth.login.sessionExpired)).toBeVisible();
  await untilHydrated(page);
  await page.getByLabel(nb.auth.login.email).fill(DEMO_USERS.student.email);
  await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: nb.auth.login.submit }).click();
  await expect(page).toHaveURL(new RegExp(`/spill/${GAME_ID}$`));
  await expect(field(page)).toHaveValue("24");
  await expect(confirm(page)).toHaveText(order.confirmOn("24"));
  expect(stub.posts).toEqual([]);
});

test("«Logg ut» clears every draft", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  // A session of its own: logging out must not end the demo session other tests share.
  await loginAs(page, "student");
  await openPlay(page, false);
  await field(page).fill("24");
  expect(await drafts(page)).toHaveLength(1);
  await page.getByRole("button", { name: nb.auth.session.logout }).click();
  await expect(page).toHaveURL(/\/logg-inn$/);
  expect(await drafts(page)).toEqual([]);
});
