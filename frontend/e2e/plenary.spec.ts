import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, lecturerPage, test } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** «Alle spill i plenum» (Story 14.6, FR-86, NFR-6, UX-DR42, UX-DR72). The view is stubbed with
 * the api's shape (`backend/tests/reports/test_class_report_plenary.py` pins the api: who reads it,
 * the scope and that nothing identifying leaves it): 24 Class games of 36 Uker at 320 and 1440 px,
 * the Matrisevegg with its legend and caption, «Vis som tabell» in game-number order with nothing to
 * sort, and 14.5's Orders charts with no game marked; the page reads nothing but its own endpoint.
 * On the local stack a played-out game opens from the Oversikt's «Vis i plenum». */
const copy = nb.plenary;
const CSRF = { "X-Requested-With": "olspillet" };
const SESSION = "01a1f8ee-35a0-7c6b-8a00-3e2a1c9d4b60";
const ROLES = ["retailer", "wholesaler", "distributor", "factory"] as const;
const WEEKS = 36;
const GAMES = 24;

/** 24 games, deeper backlog the further up the chain: the same wave in every game. */
function plenary() {
  return {
    weeks: WEEKS,
    roles: ROLES.map((role, r) => ({
      role,
      games: Array.from({ length: GAMES }, (_, g) => {
        const played = g === GAMES - 1 ? 0 : WEEKS; // the last game has not started
        return {
          number: g + 1,
          net: Array.from({ length: played }, (_, w) => Math.round(12 - (r + 1) * 9 * Math.sin((w + g) / 5))),
          orders: Array.from({ length: WEEKS }, (_, w) =>
            played === 0 ? null : Math.max(0, Math.round(4 + (w > 4 ? (r + 1) * 3 * Math.sin((w + g) / 4) + r * 4 : 0))),
          ),
        };
      }),
    })),
  };
}

/** The stub, and every api path the page asks for. */
async function stubbed(page: Page, body: unknown = plenary()): Promise<string[]> {
  const asked: string[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/class-sessions/") || path.startsWith("/api/games/")) asked.push(path);
  });
  await page.route(`**/api/class-sessions/${SESSION}/plenary`, (route) =>
    route.fulfill({ status: 200, json: body }).catch(() => undefined),
  );
  return asked;
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the wall with its legend and caption, the table in game order, the Orders charts; axe passes", async ({ page }) => {
      await loginByApi(page, "lecturer");
      const asked = await stubbed(page);
      await page.goto(`/klasseokter/${SESSION}/oversikt/plenum`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
      await expect(page.locator("[data-plenary-line]")).toHaveText(copy.line);
      // The wall: Netto lager for Fabrikk, every game a row in game-number order, only the game column.
      const wall = page.locator("[data-plenary-wall] [data-chart=matrix-wall]");
      await expect(wall.locator("[data-row]")).toHaveCount(GAMES);
      expect(await wall.locator("[data-row]").evaluateAll((rows) => rows.map((r) => r.getAttribute("data-row")))).toEqual(
        Array.from({ length: GAMES }, (_, i) => String(i + 1)),
      );
      await expect(wall.locator("[data-row='1'] [data-week]")).toHaveCount(WEEKS);
      await expect(wall.locator("[data-detail], [data-link], [data-tint], [data-summary]")).toHaveCount(0);
      await expect(page.locator("[data-wall-legend=net]")).toBeVisible();
      await expect(page.locator("[data-plenary-caption]")).toHaveText(copy.caption);
      // Nothing names, costs or sorts a game.
      const main = page.getByRole("main");
      await expect(main.getByText(/kr\b|Kjedekost|Venter|Pågår/)).toHaveCount(0);
      await expect(main.locator("[aria-sort]")).toHaveCount(0);
      if (vp.phone) {
        // Only the wall scrolls, inside its own region.
        const region = page.locator("[data-plenary-wall] [role=region]");
        expect(await region.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
      }
      await expectAccessible(page, vp.phone);

      // Larger cells than the Oversikt's wall: 1.5 × the caption size per row.
      const rowHeight = await wall.locator("[data-row='1'] [data-week='1'] rect").first().getAttribute("height");
      expect(Number(rowHeight)).toBeGreaterThanOrEqual(25);

      // The Rolle filter changes the wall.
      await page.locator("[data-wall-filters] [data-filter=retailer]").click();
      await expect(page.locator("[data-wall-filters] [data-filter=retailer]")).toHaveAttribute("aria-pressed", "true");
      await expect(wall.locator("title")).toHaveText(nb.wall.title(nb.terms.netInventory, "Detaljist"));

      // «Vis som tabell»: games in game-number order, a number in every played Uke, nothing to sort.
      await page.getByText(nb.wall.table.table, { exact: true }).click();
      const table = page.locator("table");
      await expect(table.locator("tbody th[scope=row]")).toHaveText(Array.from({ length: GAMES }, (_, i) => `Spill ${i + 1}`));
      await expect(table.locator("tbody tr").first().locator("td")).toHaveCount(WEEKS);
      await expect(table.locator("[aria-sort], button")).toHaveCount(0);
      await expect(page.locator("[data-wall-filters] [data-filter=retailer]")).toHaveAttribute("aria-pressed", "true");
      await expectReflow(page, vp.phone);

      // Ordre per rolle: 14.5's four charts, Fabrikk first, no game marked.
      await page.getByText(copy.orders, { exact: true }).click();
      const sections = page.locator("[data-plenary-orders] [data-report-section]");
      await expect(sections).toHaveCount(4);
      expect(await sections.evaluateAll((all) => all.map((s) => s.getAttribute("data-report-section")))).toEqual([
        "factory",
        "distributor",
        "wholesaler",
        "retailer",
      ]);
      await expect(page.locator('[data-mark="own-line"]')).toHaveCount(0);
      await expect(page.locator("[data-order-lines=factory] [data-mark=game-line]")).toHaveCount(GAMES);
      await expectAccessible(page, vp.phone);

      // Its one read: never the Oversikt, its aggregates or a game's Weeks.
      expect([...new Set(asked)]).toEqual([`/api/class-sessions/${SESSION}/plenary`]);
    });
  });
}

test("before any game has an opened Uke the page says so and draws no wall", async ({ page }) => {
  await loginByApi(page, "lecturer");
  await stubbed(page, { weeks: 0, roles: ROLES.map((role) => ({ role, games: [] })) });
  await page.goto(`/klasseokter/${SESSION}/oversikt/plenum`);
  await expect(page.locator("[data-plenary=none]")).toContainText(copy.none);
  await expect(page.locator("[data-chart=matrix-wall]")).toHaveCount(0);
});

test("live: «Vis i plenum» on the Oversikt opens the played game, and a Student is refused", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock and a playout
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  try {
    const played = await game.students[0]!.context.request.post(`/api/dev/games/${game.gameId}/playout`, { headers: CSRF });
    expect(played.status()).toBe(200);
    await lecturer.goto(`/klasseokter/${game.sessionId}/oversikt`);
    await lecturer.getByRole("link", { name: copy.button, exact: true }).click();
    await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${game.sessionId}/oversikt/plenum$`));
    await expect(lecturer.getByRole("heading", { level: 1 })).toHaveText(copy.title);
    const row = lecturer.locator("[data-plenary-wall] [data-row='1']");
    await expect(row.locator("[data-week]")).toHaveCount(3);
    // No Student name reaches the projector.
    for (const student of game.students) await expect(lecturer.getByText(student.name)).toHaveCount(0);
    const refused = await game.students[0]!.context.request.get(`/api/class-sessions/${game.sessionId}/plenary`);
    expect(refused.status()).toBe(403);
    expect((await refused.json()).error.code).toBe("forbidden");
    const student = await game.students[0]!.context.newPage();
    await student.goto(`/klasseokter/${game.sessionId}/oversikt/plenum`);
    await expect(student.getByRole("heading", { level: 1 })).toHaveText(nb.access.denied);
  } finally {
    await lecturer.context().close();
    for (const student of game.students) await student.context.close();
  }
});
