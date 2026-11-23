import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { formatTime } from "../src/modules/admin/audit";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test, VIEWPORTS } from "./support/classes";

/** «KI-kostnad per Klasseøkt» (Story 15.6, FR-69, NFR-6) on the local stack. Each test makes a fresh
 * Class session through the api. The sums, the limit rules, the reserve, the resume and stop calls
 * and the owners' notice are pinned by `backend/tests/ops/test_ai_cost.py`; the charts and the
 * limit-reached state are drawn here from a fixed answer, since the mock stack spends nothing. */
const copy = nb.admin.aiCost;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;

/** A saved Class session with LLM players (so it has its budget row), and how the page names it. */
async function savedSession(lecturer: Page): Promise<{ id: string; label: string }> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const session = await created.json();
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const saved = await lecturer.request.put(`/api/class-sessions/${session.id}`, {
    data: { ai_mode: "llm", dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  return { id: session.id, label: nb.admin.evaluation.sessions.label(klass.name, 1) };
}

/** The Class session's answer as the api gives it once the players' limit and the reserve are
 * used up, with two Games and two days of spend. */
function usedUp(id: string, label: string, reachedAt: string) {
  return {
    class_session_id: id,
    label,
    institution_name: "USN Bø",
    ai_mode: "llm",
    budget: {
      limit_usd: "2.00000000",
      reserve_usd: "1.00000000",
      spent_usd: "2.00000000",
      reserved_usd: "0.00000000",
      players_exhausted_at: reachedAt,
    },
    total_usd: "2.00000000",
    calls: 412,
    games: 2,
    students: 3,
    per_game_usd: "0.60000000",
    per_student_usd: "0.66666667",
    per_game_above: true,
    per_student_above: true,
    per_game: [
      { game_id: "00000000-0000-7000-8000-000000000001", number: 1, usd: "0.70000000", calls: 200, above: true },
      { game_id: "00000000-0000-7000-8000-000000000002", number: 2, usd: "0.50000000", calls: 180, above: true },
      { game_id: null, number: null, usd: "0.80000000", calls: 32, above: false },
    ],
    per_day: [
      { day: "2026-11-18", usd: "1.20000000", calls: 250 },
      { day: "2026-11-19", usd: "0.80000000", calls: 162 },
    ],
    reserve_used_up: true,
    assessment_stopped_at: null,
    can_stop: true,
  };
}

for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin finds a Class session's cost and sets its limit", async ({ page, browser, lecturerSession }) => {
      const lecturer = await lecturerPage(browser, lecturerSession, vp);
      const { id, label } = await savedSession(lecturer);

      // A Lecturer gets the permission-denied page.
      await lecturer.goto(`/admin/ki-kostnad/klasseokter/${id}`);
      await expect(lecturer.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();

      await loginByApi(page, "admin");
      await page.goto("/admin/ki-kostnad");
      await page.getByRole("link", { name: copy.costs.link }).click();
      await expect(page.getByRole("heading", { level: 1, name: copy.costs.title })).toBeVisible();
      await expect(page.getByRole("heading", { name: copy.costs.evaluations.title })).toBeVisible();
      await expectAccessible(page, vp.phone);

      await page.getByRole("link", { name: label }).click();
      await expect(page.getByRole("heading", { level: 1, name: label })).toBeVisible();
      const budget = page.getByRole("region", { name: copy.cost.budget.title });
      await expect(budget).toContainText("15,00 USD"); // AI_DEFAULT_SESSION_BUDGET_USD
      await expect(page.getByText(copy.cost.games.empty).first()).toBeVisible();

      const field = page.getByLabel(copy.cost.limitLabel);
      await field.fill("tolv");
      await page.getByRole("button", { name: copy.cost.save }).click();
      await expect(page.getByText(copy.cost.invalid)).toBeVisible();
      await field.fill("20,50");
      await page.getByRole("button", { name: copy.cost.save }).click();
      await expect(page.getByText(/^Kostnadsgrensen er 20,50/)).toBeVisible();
      await expect(budget).toContainText("20,50 USD");
      await expectAccessible(page, vp.phone);
    });

    test("a used-up limit and reserve read as text, with both actions and the charts as tables", async ({
      page,
      browser,
      lecturerSession,
    }) => {
      const lecturer = await lecturerPage(browser, lecturerSession, vp);
      const { id, label } = await savedSession(lecturer);
      await loginByApi(page, "admin");
      const reachedAt = new Date().toISOString();
      const route = `**/api/admin/ai/costs/${id}`;
      await page.route(route, (r) => r.fulfill({ json: usedUp(id, label, reachedAt) }));
      try {
        await page.goto(`/admin/ki-kostnad/klasseokter/${id}`);
        const state = page.locator("[data-cost-state]");
        await expect(state).toContainText(copy.cost.reached(label));
        await expect(state).toContainText(copy.cost.reachedAt(formatTime(reachedAt)));
        await expect(state).toContainText(copy.cost.reserveUsed);
        // Each action states its consequence above its button; the limit save is the one primary.
        await expect(page.getByText(copy.cost.raiseConsequence)).toBeVisible();
        await expect(page.getByText(copy.cost.stopConsequence)).toBeVisible();
        await expect(page.getByRole("button", { name: copy.cost.stop })).toBeVisible();
        await expect(page.getByText(copy.costs.above).first()).toBeVisible();

        const games = page.locator('[data-chart-block="cost-games"]');
        await expect(games.locator('[data-chart="cost-games"] li')).toHaveCount(3);
        await games.getByRole("button", { name: nb.admin.operations.showTable }).click();
        await expect(games.getByRole("rowheader", { name: copy.cost.games.game(2) })).toBeVisible();
        await expect(games.getByRole("rowheader", { name: copy.cost.games.noGame })).toBeVisible();
        const days = page.locator('[data-chart-block="cost-days"]');
        await days.getByRole("button", { name: nb.admin.operations.showTable }).click();
        await expect(days.getByRole("row")).toHaveCount(3);
        await expectAccessible(page, vp.phone);
      } finally {
        await page.unroute(route);
      }
    });
  });
}

test("the Lecturer's Klasseøkt says when the players' cost limit was reached", async ({ browser, lecturerSession }) => {
  const vp = VIEWPORTS.find((v) => !v.phone && !v.text200)!;
  const lecturer = await lecturerPage(browser, lecturerSession, vp);
  const { id } = await savedSession(lecturer);
  const route = `**/api/class-sessions/${id}`;
  await lecturer.route(route, async (r) => {
    const response = await r.fetch();
    const body = await response.json();
    await r.fulfill({
      response,
      json: { ...body, locked: true, locked_at: new Date().toISOString(), cost_limit_reached_at: new Date().toISOString() },
    });
  });
  try {
    await lecturer.goto(`/klasseokter/${id}`);
    await expect(lecturer.locator("[data-cost-limit]")).toContainText("Kostnadsgrensen for KI er nådd.");
    await expectAccessible(lecturer, vp.phone);
  } finally {
    await lecturer.unroute(route);
  }
});
