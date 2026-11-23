import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, lecturerPage, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** Story 15.1 (FR-75, FR-5, NFR-6, UX-DR67) on the local stack: a fresh Student in a locked Class
 * session with two Orders of their own opens «Mine data» from the Lenke beside their name on Hjem.
 * «Last ned Studentrapport» is at the top and, before the Testfrist, says when it opens; each
 * category has «Vis»; «Ordrer» shows the Student's own Orders, an empty «Forklaring» says
 * «Ingenting er lagret.». Axe and reflow at 320 px, 360 px and 200 % text. What the api reads and
 * refuses is `backend/tests/reports/test_my_data.py`. */
const copy = nb.myData;
const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false },
  { name: "200 % text", width: 1280, height: 800, phone: false, text200: true },
];

test("a Student sees their own data in «Mine data» from Hjem", async ({ browser, lecturerSession }) => {
  test.slow(); // Invitations through the worker, a Class session and its lock
  const { gameId, students } = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  const [sara] = students as [(typeof students)[number]];
  await orderByApi(sara, gameId, 1, 7);
  await orderByApi(sara, gameId, 2, 9);
  const state = await sara.context.storageState();

  for (const vp of VIEWPORTS) {
    const page = await lecturerPage(browser, state, vp);
    try {
      await page.goto("/hjem");
      await page.getByRole("banner").getByRole("link", { name: copy.link }).click();
      await expect(page).toHaveURL(/\/mine-data$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: copy.reportHeading })).toBeVisible();
      // Before the Testfrist the Studentrapport says when it opens.
      await expect(page.locator("[data-report-download='closed']")).toBeVisible();

      const orders = page.locator("[data-category='orders']");
      await expect(orders).toContainText(copy.categories.orders!);
      await orders.getByRole("button", { name: copy.show }).click();
      await expect(orders.getByRole("button", { name: copy.hide })).toHaveAttribute("aria-expanded", "true");
      const own = orders.locator("li").filter({ hasText: nb.myData.codes.decided_by!.student! });
      await expect(own).toHaveCount(2);
      await expect(own.first()).toContainText("7");

      const explanation = page.locator("[data-category='explanation']");
      await explanation.getByRole("button", { name: copy.show }).click();
      await expect(explanation).toContainText(copy.empty);
      await expect(page.locator("[data-category='adjustments']")).toHaveCount(0);

      await expectAccessible(page, vp.phone);
    } finally {
      await page.context().close();
    }
  }
});
