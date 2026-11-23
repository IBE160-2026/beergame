import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";

/** «Alle spill side om side» (Story 14.5, FR-86, NFR-6, UX-DR64, UX-DR72, UX-DR75). The view is
 * stubbed with the api's shape (`backend/tests/reports/test_class_report_all_games.py` pins the
 * api: the gate, the scope, the own game and that nothing identifying leaves it): 24 Class games
 * of 36 Uker at 320, 360 and 1440 px, each Role a chart with «Vis som tabell», the own game named
 * in text and drawn thick with points; on a phone only the chart and the table scroll. Hjem's
 * entry is laid over the demo Student's real Class, so the demo Class is never changed. */
const copy = nb.allGames;
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c50";
const LOCKED_SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c51";
const ROLES = ["retailer", "wholesaler", "distributor", "factory"] as const;
const WEEKS = 36;
const OWN = 7;

/** 24 games, Orders rising more the further up the chain: the bullwhip in every game. */
function classGames() {
  return {
    weeks: WEEKS,
    own_game: OWN,
    roles: ROLES.map((role, r) => ({
      role,
      games: Array.from({ length: 24 }, (_, g) => ({
        number: g + 1,
        own: g + 1 === OWN,
        orders: Array.from({ length: WEEKS }, (_, w) =>
          g === 23 && w > 30 ? null : Math.max(0, Math.round(4 + (w > 4 ? (r + 1) * 3 * Math.sin((w + g) / 4) + r * 4 : 0))),
        ),
      })),
    })),
  };
}

async function stubbed(page: Page, status = 200, body: unknown = classGames()) {
  await page.route(`**/api/me/class-sessions/${SESSION}/all-games`, (route) =>
    route.fulfill({ status, json: body }).catch(() => undefined),
  );
}

/** The demo Student's Class with two finished Class sessions: one open, one locked. */
async function hjemWithEntries(page: Page) {
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const session = (id: string, number: number, open: boolean) => ({
      id,
      class_id: klass.id,
      class_name: klass.name,
      number,
      start_at: "2026-10-24T09:00:00Z",
      play_deadline: "2026-11-08T13:00:00Z",
      debrief_deadline: null,
      test_deadline: null,
      next_deadline: null,
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      steps: [
        { step: "class_game", state: "done" },
        { step: "debrief", state: open ? "done" : "current" },
      ],
      game: {
        id: `${id.slice(0, -2)}9${number}`,
        number,
        role: "wholesaler",
        seats: [],
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 0, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "finished",
        week: null,
        server_now: "2026-11-23T10:00:00Z",
        seat_state: null,
        turn: null,
        played_out: true,
      },
      all_games_open: open,
    });
    await route.fulfill({ response, json: { items: [session(SESSION, 1, true), session(LOCKED_SESSION, 2, false)] } });
  });
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("every Class game per Role, Fabrikk first, the own game named and drawn thick; tables in game order; axe passes", async ({
      page,
    }) => {
      await loginByApi(page, "student");
      await stubbed(page);
      await page.goto(`/alle-spill/${SESSION}`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
      await expect(page.locator("[data-own-line]")).toHaveText(copy.own(OWN));
      const sections = page.locator("[data-report-section]");
      await expect(sections).toHaveCount(4);
      expect(await sections.evaluateAll((all) => all.map((s) => s.getAttribute("data-report-section")))).toEqual([
        "factory",
        "distributor",
        "wholesaler",
        "retailer",
      ]);
      await expect(sections.first().getByRole("heading", { level: 2 })).toHaveText("Fabrikk");
      // The own game is drawn apart from the others in every chart: thick, with a point per Uke.
      for (const role of ROLES) {
        const chart = page.locator(`[data-order-lines=${role}]`);
        await expect(chart.locator('[data-mark="game-line"]')).toHaveCount(23);
        await expect(chart.locator(`[data-mark="own-line"][data-game="${OWN}"] circle`)).toHaveCount(WEEKS);
      }
      // Nothing ranks a game: no cost, no result, no sorting control.
      const main = page.getByRole("main");
      await expect(main.getByText(/kr\b|Totalkostnad|Kjedekost/)).toHaveCount(0);
      await expect(main.locator("[aria-sort]")).toHaveCount(0);
      if (vp.phone) {
        // Only the chart scrolls, inside its own region.
        const region = page.locator("[data-order-lines=factory] [role=region]");
        expect(await region.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
      }
      await expectAccessible(page, vp.phone);

      // «Vis som tabell»: games in game-number order, the own row named in text.
      const factory = sections.first();
      await factory.getByRole("button", { name: nb.classReport.showTable }).click();
      const table = factory.locator("[data-report-table=factory]");
      const heads = await table.locator("tbody th[scope=row]").allTextContents();
      expect(heads).toEqual(Array.from({ length: 24 }, (_, i) => (i + 1 === OWN ? copy.ownGame(OWN) : copy.game(i + 1))));
      await expect(table.locator("thead th")).toHaveCount(WEEKS + 1);
      await expect(table.locator("tbody tr").last().locator("td").last()).toHaveText(copy.noOrder);
      await expectAccessible(page, vp.phone);
    });
  });
}

test.describe("320 px", () => {
  test.use({ viewport: { width: 320, height: 640 } });

  test("Hjem: the entry is a Lenke once open and reads what opens it while locked; axe passes", async ({ page }) => {
    await loginByApi(page, "student");
    await hjemWithEntries(page);
    await stubbed(page);
    await page.goto("/hjem");
    const open = page.locator("[data-all-games-entry=open]");
    const locked = page.locator("[data-all-games-entry=locked]");
    await expect(open).toHaveCount(1);
    await expect(locked).toHaveCount(1);
    await expect(locked).toContainText(copy.locked);
    await expect(locked.getByRole("link")).toHaveCount(0);
    await expectAccessible(page, true);
    await open.getByRole("link", { name: copy.entry }).click();
    await expect(page).toHaveURL(new RegExp(`/alle-spill/${SESSION}$`));
    await expect(page.locator("[data-own-line]")).toHaveText(copy.own(OWN));
  });

  test("a session with no Class game says so and draws no chart", async ({ page }) => {
    await loginByApi(page, "student");
    await stubbed(page, 200, { weeks: 0, own_game: null, roles: ROLES.map((role) => ({ role, games: [] })) });
    await page.goto(`/alle-spill/${SESSION}`);
    await expect(page.locator("[data-all-games=none]")).toHaveText(copy.none);
    await expect(page.locator("[data-order-lines]")).toHaveCount(0);
  });

  test("opened while locked, the page says what opens it and shows no game", async ({ page }) => {
    await loginByApi(page, "student");
    await stubbed(page, 403, { error: { code: "all_games_locked", message: "locked", fields: {} } });
    await page.goto(`/alle-spill/${SESSION}`);
    await expect(page.locator("[data-all-games=locked]")).toHaveText(copy.locked);
    await expect(page.locator("[data-order-lines]")).toHaveCount(0);
    await expectAccessible(page, true);
  });
});

test("live api: Hjem says whether the view is open, and another session is refused as forbidden", async ({ page }) => {
  await loginByApi(page, "student");
  const sessions = await (await page.request.get("/api/me/class-sessions")).json();
  for (const item of sessions.items as { all_games_open: unknown }[]) expect(typeof item.all_games_open).toBe("boolean");
  const refused = await page.request.get(`/api/me/class-sessions/${SESSION}/all-games`);
  expect(refused.status()).toBe(403);
  expect((await refused.json()).error.code).toBe("forbidden");
  await page.goto(`/alle-spill/${SESSION}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.access.denied);
});
