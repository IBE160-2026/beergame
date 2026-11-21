import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** The Student's Hjem (Story 6.1, FR-22, FR-34, UX-DR29, UX-DR62, UX-DR69, UX-DR73), on the local
 * stack as the demo Student. The game card, the Seats and Stegene's states are the api's and are
 * pinned by `backend/tests/sessions/test_student_home.py`; here the server's answer for the demo
 * Student's Class is laid over the real one, so the demo Class is never changed, and the screen
 * is checked in both states at 320, 360 and 1440 px and at 360 px with 200 % text. */
const copy = nb.homes.student;

const LOCKED_STEPS = ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step) => ({
  step,
  state: "locked",
}));

const GAME = {
  id: "01a1f8ee-34f2-70af-8800-f79281ed777e",
  number: 17,
  role: "wholesaler",
  seats: [
    { role: "factory", holder: "student", name: "Jonas Berg", mine: false },
    { role: "distributor", holder: "ai", name: null, mine: false },
    { role: "wholesaler", holder: "student", name: "Demo Student", mine: true },
    { role: "retailer", holder: "ai", name: null, mine: false },
  ],
  briefing_first: true,
  status: "ready",
  week: null,
  rules: {
    order_delay: 2,
    shipping_delay: 2,
    production_delay: 2,
    guided_weeks: 4,
    holding_cost: "0.50",
    backorder_cost: "1.00",
  },
};

/** The demo Student's Class with one Class session in the given state, as the api answers it. */
async function withSession(page: Page, state: { game: typeof GAME | null; steps: object[] }) {
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const item = {
      id: "01a1f8ee-33b9-75e6-9502-79db27b37c0e",
      class_id: klass.id,
      class_name: klass.name,
      number: 1,
      start_at: "2026-11-24T09:00:00Z",
      play_deadline: "2026-12-08T13:00:00Z",
      debrief_deadline: null,
      test_deadline: null,
      next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
      obligatory: true,
      lab_hours: [
        { id: "l1", starts_at: "2026-11-26T13:15:00Z", ends_at: "2026-11-26T15:00:00Z", place: "Datalab A2" },
      ],
      seat_choice_open: false,
      drawn_seat: null,
      ...state,
    };
    await route.fulfill({ response, json: { items: [item] } });
  });
}

async function textAtLeast13px(page: Page) {
  const small = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("main *")]
      .filter((el) => el.offsetParent !== null && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent?.trim()))
      .map((el) => ({ text: el.textContent?.trim(), size: parseFloat(getComputedStyle(el).fontSize) }))
      .filter((el) => el.size < 13),
  );
  expect(small).toEqual([]);
}

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false },
  { name: "360 px with 200 % text", width: 360, height: 740, phone: true, text200: true },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false },
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test.beforeEach(async ({ page }) => {
      if (vp.text200) {
        await page.addInitScript(() => {
          document.addEventListener("DOMContentLoaded", () => {
            const style = document.createElement("style");
            style.textContent = "html { font-size: 200% !important; }";
            document.head.appendChild(style);
          });
        });
      }
      await loginByApi(page, "student");
    });

    test("before the Start date: no game card, the Start-date line and Stegene greyed out", async ({ page }) => {
      await withSession(page, { game: null, steps: LOCKED_STEPS });
      await page.goto("/hjem");
      const main = page.getByRole("main");
      await expect(main.getByText(nb.homes.startDate)).toBeVisible();
      await expect(main.getByRole("heading", { name: /^Spill \d+ · / })).toHaveCount(0);
      const steps = main.getByRole("region", { name: copy.steps }).getByRole("listitem");
      await expect(steps).toHaveCount(6);
      await expect(steps.nth(0)).toHaveText(copy.locked.class_game);
      await expect(steps.nth(3)).toHaveText(copy.locked.replay);
      await expect(main.getByText(copy.current)).toHaveCount(0);
      await expect(main.getByText("Spillfrist ti. 8. des.")).toBeVisible();
      await expect(main.getByText("to. 26. nov. 14:15, Datalab A2")).toBeVisible();
      await expect(main.getByText(copy.obligatory, { exact: true })).toBeVisible();
      await expectAccessible(page, vp.phone);
      await textAtLeast13px(page);
    });

    test("with a Seat: «Spill 17 · Du er Grossist», the Seats Fabrikk first and Klassespill «pågår»", async ({
      page,
    }) => {
      await withSession(page, {
        game: GAME,
        steps: LOCKED_STEPS.map((step, i) => (i === 0 ? { ...step, state: "current" } : step)),
      });
      await page.goto("/hjem");
      const main = page.getByRole("main");
      await expect(main.getByRole("heading", { name: "Spill 17 · Du er Grossist" })).toBeVisible();
      await expect(main.getByText(nb.homes.startDate)).toHaveCount(0);
      const seats = main.getByRole("region", { name: copy.seats }).getByRole("listitem");
      await expect(seats).toHaveText([
        /^Fabrikk\s*Jonas Berg$/,
        /^Distributør\s*KI-spiller$/,
        /^Grossist\s*Demo Student \(deg\)$/,
        /^Detaljist\s*KI-spiller$/,
      ]);
      const steps = main.getByRole("region", { name: copy.steps }).getByRole("listitem");
      await expect(steps.nth(0)).toHaveText(/Klassespill\s*pågår/);
      await expect(steps.nth(4)).toHaveText(copy.locked.test);
      // Story 6.2: until the Starting task, Hjem's one primary button leads to the briefing.
      await expect(main.getByRole("link", { name: copy.readRules })).toHaveAttribute("href", `/spill/${GAME.id}/regler`);
      await expectAccessible(page, vp.phone);
      await textAtLeast13px(page);
    });
  });
}

test("a failed read shows the page error, and «Prøv igjen» loads Hjem", async ({ page }) => {
  await loginByApi(page, "student");
  let fail = true;
  await page.route("**/api/me/class-sessions", async (route) => {
    if (fail) return route.fulfill({ status: 500, json: { error: { code: "internal", message: "", fields: {} } } });
    return route.fallback();
  });
  await page.goto("/hjem");
  await expect(page.getByRole("alert").filter({ hasText: nb.system.pageError })).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: nb.system.retry }).click();
  await expect(page.getByRole("heading", { level: 2, name: /class-of-1994/ })).toBeVisible();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("a Student in two Classes sees each Message's Class name; in one Class, none (Story 7.10)", async ({ page }) => {
  await loginByApi(page, "student");
  const message = (id: string, className: string, text: string) => ({
    id,
    class_id: `c-${id}`,
    class_name: className,
    sender_name: "Lene Lærer",
    sent_at: "2026-11-26T13:15:00Z",
    text,
  });
  await page.route("**/api/me/messages", (route) =>
    route.fulfill({
      json: { items: [message("m2", "class-of-2027", "Husk fristen."), message("m1", "Logistikk 2", "Velkommen.")] },
    }),
  );
  // The demo Student's one Class, and a second laid over it.
  let second = true;
  await page.route("**/api/classes/enrolled", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    const items = second
      ? [...body.items, { ...body.items[0], id: "01a1f8ee-0000-7000-8000-000000000002", name: "Logistikk 2" }]
      : body.items;
    await route.fulfill({ response, json: { ...body, items } });
  });
  await page.goto("/hjem");
  const meldinger = page.getByRole("main").getByRole("region", { name: nb.messages.mine.title });
  await expect(meldinger.getByRole("listitem")).toHaveCount(2);
  await expect(meldinger.getByRole("listitem").nth(0)).toContainText("class-of-2027");
  await expect(meldinger.getByRole("listitem").nth(1)).toContainText("Logistikk 2");

  second = false;
  await page.reload();
  await expect(meldinger.getByRole("listitem")).toHaveCount(2);
  await expect(meldinger).not.toContainText("class-of-2027");
  await page.unrouteAll({ behavior: "ignoreErrors" });
});
