import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week14 from "../src/modules/games/fixtures/play-week-14.json";
import { DEMO_PASSWORD, DEMO_USERS, untilHydrated } from "./support/auth";
import { expectAccessible } from "./support/classes";
import {
  confirmButton as button,
  confirmedWeek11,
  drafts,
  GAME_ID,
  holdPlay,
  openPlay,
  orderField as field,
} from "./support/play";

/** A send on a bad connection (Story 6.13, FR-24, FR-26, NFR-5, NFR-6, AD-2, AD-10, AD-19,
 * UX-DR59, UX-DR60): never lost, never doubled, and the screen says plainly whether the Order was
 * sent. The stand-in play screen of `support/play.ts`; the order-submit timeout is passed with
 * Playwright's clock, never waited for. The api race is `backend/tests/sessions/test_orders.py`. */
const order = nb.games.play.order;
const TIMEOUT_MS = 10_000; // `ORDER_SUBMIT_TIMEOUT_MS` in `play-page.tsx`

const failure = (page: Page) => page.locator("[data-order-failure]");
const status = (page: Page) => page.locator("[data-order-status]");
const error = (code: string, status = 409) => ({ status, json: { error: { code, message: "x" } } });
/** A POST left unanswered: the page gives up on it. */
const never = () => new Promise<void>(() => undefined);

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const width of [320, 360, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("offline, failed and timed out: plain words, the value kept, focus on the button, no axe violation", async ({
      page,
      context,
    }) => {
      const phone = width < 1024;
      await page.clock.install();
      const stub = await openPlay(page);
      await field(page).fill("24");

      // Offline with a typed Order: the Tilkoblingslinje and the order area say it is not sent.
      await context.setOffline(true);
      await expect(page.locator("[data-connection-notice]")).toContainText(nb.system.offline);
      await expect(status(page)).toHaveText(order.offline("24"));
      await expect(field(page)).toHaveValue("24");
      await expectAccessible(page, phone);
      // Back: still not sent, the normal button, nothing sent on its own.
      await context.setOffline(false);
      await expect(status(page)).toHaveText(order.reconnected);
      await expect(button(page)).toHaveText(order.confirmOn("24"));
      expect(stub.posts).toEqual([]);

      // Submit failed: the server holds no Order.
      stub.answer = (route) => route.fulfill(error("unavailable", 503));
      await button(page).click();
      await expect(failure(page)).toHaveText(order.failed);
      await expect(failure(page)).toHaveAttribute("role", "alert");
      await expect(button(page)).toHaveText(order.retry("24"));
      await expect(button(page)).not.toHaveAttribute("aria-disabled");
      await expect(button(page)).toBeFocused();
      await expect(field(page)).toHaveValue("24");
      await expect(field(page)).not.toHaveAttribute("readonly");
      await expect(status(page)).toHaveText("");
      await expectAccessible(page, phone);
      const targets = await page.locator("[data-order-field] button").evaluateAll((els) =>
        els.map((el) => Math.min(el.getBoundingClientRect().width, el.getBoundingClientRect().height)),
      );
      for (const size of targets) expect(size).toBeGreaterThanOrEqual(44);

      // Timed out: no answer, so the app asks the server, which has the Order.
      stub.answer = never;
      await button(page).click();
      await expect(button(page)).toHaveText(order.sending("24"));
      const release = holdPlay(stub);
      await page.clock.fastForward(TIMEOUT_MS);
      await expect(status(page)).toHaveText(order.checking);
      await expect(status(page)).toHaveAttribute("aria-live", "polite");
      await expect(button(page)).toBeFocused();
      await expect(button(page)).toHaveAttribute("aria-busy", "true");
      await expect(failure(page)).toHaveText("");
      await expectAccessible(page, phone);
      stub.envelope = confirmedWeek11;
      release();
      await expect(page.getByText(order.sent("24"))).toBeFocused();
      expect(stub.posts).toEqual([{ order: 24 }, { order: 24 }]);
      expect(await drafts(page)).toEqual([]);
    });
  });
}

test.describe("360 px", () => {
  test.use({ viewport: { width: 360, height: 800 } });

  test("timed out and not there: Submit failed, never left sending", async ({ page }) => {
    await page.clock.install();
    const stub = await openPlay(page);
    stub.answer = never;
    await field(page).fill("24");
    await button(page).click();
    await page.clock.fastForward(TIMEOUT_MS);
    await expect(failure(page)).toHaveText(order.failed);
    await expect(button(page)).toHaveText(order.retry("24"));
    await expect(button(page)).toBeFocused();
    await expect(status(page)).toHaveText("");
  });

  test("a send whose answer was lost but whose Order is stored shows Confirmed", async ({ page }) => {
    const stub = await openPlay(page);
    stub.answer = async (route) => {
      stub.envelope = confirmedWeek11; // it arrived; the answer did not
      await route.abort("connectionreset");
    };
    await field(page).fill("24");
    await button(page).click();
    await expect(page.getByText(order.sent("24"))).toBeFocused();
    await expect(failure(page)).toHaveCount(0);
    expect(await drafts(page)).toEqual([]);
  });

  test("a retry after the Order arrived is refused as already ordered and shows the stored Order", async ({ page }) => {
    const stub = await openPlay(page);
    stub.answer = (route) => route.fulfill(error("unavailable", 503));
    await field(page).fill("24");
    await button(page).click();
    await expect(button(page)).toHaveText(order.retry("24"));
    // The first send did arrive after all: the retry is refused and nothing is placed twice.
    stub.answer = async (route) => {
      stub.envelope = confirmedWeek11;
      await route.fulfill(error("order_exists"));
    };
    await button(page).click();
    await expect(page.getByText(order.sent("24"))).toBeFocused();
    expect(stub.posts).toEqual([{ order: 24 }, { order: 24 }]);
  });

  test("an Uke the game has left: its words in the Uke now shown", async ({ page }) => {
    const stub = await openPlay(page);
    stub.answer = async (route) => {
      stub.envelope = week14;
      await route.fulfill(error("week_not_open"));
    };
    await field(page).fill("24");
    await button(page).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(14));
    await expect(failure(page)).toHaveText(order.weekGone(11, "24"));
    await expect(field(page, 14)).toHaveValue("");
  });

  test("a Seat no longer held: its words, the value kept", async ({ page }) => {
    const stub = await openPlay(page);
    stub.answer = (route) => route.fulfill(error("seat_not_yours"));
    await field(page).fill("24");
    await button(page).click();
    await expect(failure(page)).toHaveText(order.seatGone("24"));
    await expect(field(page)).toHaveValue("24");
    await expect(button(page)).toHaveText(order.confirmOn("24"));
    // A new value clears the words.
    await field(page).fill("25");
    await expect(failure(page)).toHaveText("");
  });

  test("the session ends in the middle of a submit: after logging in, the Uke shows 24 unsent", async ({ page, context }) => {
    const stub = await openPlay(page);
    let answer: () => void = () => undefined;
    const answered = new Promise<void>((resolve) => (answer = resolve));
    stub.answer = async (route) => {
      await answered;
      await route.fulfill(error("session_expired", 401));
    };
    await field(page).fill("24");
    await button(page).click();
    await expect(button(page)).toHaveText(order.sending("24"));
    const [cookie] = (await context.cookies()).filter((c) => c.name === "olspillet_session");
    await context.addCookies([{ ...cookie!, value: "utgatt" }]);
    answer();
    await expect(page).toHaveURL(/\/logg-inn\?neste=%2Fspill%2F.+&utlopt=1$/);
    await untilHydrated(page);
    await page.getByLabel(nb.auth.login.email).fill(DEMO_USERS.student.email);
    await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
    await page.getByRole("button", { name: nb.auth.login.submit }).click();
    await expect(page).toHaveURL(new RegExp(`/spill/${GAME_ID}$`));
    await expect(field(page)).toHaveValue("24");
    await expect(button(page)).toHaveText(order.confirmOn("24"));
    expect(stub.posts).toEqual([{ order: 24 }]);
  });

  test("timed out, and the check gets no answer either: Submit failed, the button free again", async ({ page }) => {
    await page.clock.install();
    const stub = await openPlay(page);
    stub.answer = never;
    await field(page).fill("24");
    await button(page).click();
    holdPlay(stub); // never released
    await page.clock.fastForward(TIMEOUT_MS);
    await expect(status(page)).toHaveText(order.checking);
    await page.clock.fastForward(TIMEOUT_MS);
    await expect(failure(page)).toHaveText(order.failed);
    await expect(button(page)).toHaveText(order.retry("24"));
    await expect(button(page)).not.toHaveAttribute("aria-busy");
    await expect(status(page)).toHaveText("");
  });

  test("an answer lost, and the Uke moved on with this Order: Confirmed, focus on the new Uke", async ({ page }) => {
    const stub = await openPlay(page);
    stub.answer = async (route) => {
      stub.envelope = week14; // its history holds 8 for Uke 11
      await route.abort("connectionreset");
    };
    await field(page).fill("8");
    await button(page).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(14));
    await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
    await expect(failure(page)).toHaveText("");
    expect(await drafts(page)).toEqual([]);
  });

  test("an answer lost, and the Uke moved on with another Order: the Uke is over, 24 not sent", async ({ page }) => {
    const stub = await openPlay(page);
    stub.answer = async (route) => {
      stub.envelope = week14;
      await route.abort("connectionreset");
    };
    await field(page).fill("24");
    await button(page).click();
    await expect(failure(page)).toHaveText(order.weekGone(11, "24"));
    await expect(field(page, 14)).toHaveValue("");
  });

  test("a retry of an Order that arrived and completed the Uke: refused as closed, shown as Confirmed", async ({ page }) => {
    const stub = await openPlay(page);
    stub.answer = async (route) => {
      stub.envelope = week14;
      await route.fulfill(error("week_not_open"));
    };
    await field(page).fill("8");
    await button(page).click();
    await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
    await expect(failure(page)).toHaveText("");
  });
});
