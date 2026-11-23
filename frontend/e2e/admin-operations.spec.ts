import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test, VIEWPORTS } from "./support/classes";

/** «Drift» in the Admin-område (Story 15.8, NFR-8, FR-79, UX-DR58), on the local stack. A fresh
 * Class session reads zeros from the real api; the figures of a busy Lab hour are served from a
 * route, since the stack's mock model costs nothing and fails nothing. How each source is counted
 * is pinned by `backend/tests/ops/test_error_events.py`. */
const copy = nb.admin.operations;
const CSRF = { "X-Requested-With": "olspillet" };

async function savedSession(lecturer: Page): Promise<{ id: string; label: string }> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const session = await created.json();
  const saved = await lecturer.request.put(`/api/class-sessions/${session.id}`, {
    data: { ai_mode: "rule_based" },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  return { id: session.id, label: nb.admin.evaluation.sessions.label(klass.name, 1) };
}

/** The figures of a busy hour: errors in the last three hours, fallbacks, two Effort levels. */
function busy(id: string, label: string, now: Date) {
  const current = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), now.getUTCHours());
  const hours = Array.from({ length: 24 }, (_, i) => ({
    hour: new Date(current - (23 - i) * 3600_000).toISOString(),
    conservation_check: i === 21 ? 1 : 0,
    job_failed: i === 22 ? 2 : 0,
    api_error: i === 23 ? 3 : 0,
  }));
  return {
    class_session_id: id,
    label,
    institution_name: null,
    read_at: now.toISOString(),
    hours,
    totals: { conservation_check: 1, job_failed: 2, api_error: 4 },
    llm_orders: 9,
    fallbacks: [
      { kind: "fallback_timeout", orders: 2, share: "0.2222" },
      { kind: "fallback_invalid_output", orders: 0, share: "0.0000" },
      { kind: "fallback_budget_exhausted", orders: 0, share: "0.0000" },
      { kind: "fallback_provider_error", orders: 1, share: "0.1111" },
    ],
    response_times: [
      { effort_level: "deep", label: "Grundig", calls: 1, median_ms: 1000, p95_ms: 1000 },
      { effort_level: "fast", label: null, calls: 4, median_ms: 200, p95_ms: 400 },
    ],
    llm_seats: 2,
    switched_seats: 1,
    switched_share: "0.5000",
    cost_usd: "0.64000000",
    ai_calls: 6,
  };
}

for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin opens «Drift» for a Class session and reads its figures", async ({
      page,
      browser,
      lecturerSession,
    }) => {
      const lecturer = await lecturerPage(browser, lecturerSession, vp);
      const { id, label } = await savedSession(lecturer);

      // A Lecturer gets the permission-denied page, on the list and on a Class session.
      for (const path of ["/admin/drift", `/admin/drift/${id}`]) {
        await lecturer.goto(path);
        await expect(lecturer.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
      }

      await loginByApi(page, "admin");
      await page.goto("/admin");
      await page.getByRole("link", { name: nb.admin.sections.operations }).click();
      await expect(page).toHaveURL(/\/admin\/drift$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
      await expect(page.getByText(/Sist oppdatert/)).toBeVisible();
      await expectAccessible(page, vp.phone);

      // The fresh Class session: no errors, no LLM players, no cost.
      const row = page.locator("tbody tr").filter({ hasText: label });
      await expect(row).toContainText("0");
      await row.getByRole("link", { name: label }).click();
      await expect(page).toHaveURL(new RegExp(`/admin/drift/${id}$`));
      await expect(page.getByRole("heading", { level: 1, name: label })).toBeVisible();
      await expect(page.getByText(copy.errors.last24("0"))).toBeVisible();
      await expect(page.getByText(copy.fallback.none)).toBeVisible();
      await expect(page.getByText(copy.times.none)).toBeVisible();
      await expect(page.getByText(copy.guard.none)).toBeVisible();
      await expect(page.getByText(/0,00 USD for 0 KI-kall\./)).toBeVisible();
      await expectAccessible(page, vp.phone);
    });

    test("a busy hour reads as charts and tables, and a failed read keeps the figures", async ({ page }) => {
      await page.clock.install();
      await loginByApi(page, "admin");
      const id = "00000000-0000-7000-8000-000000000158";
      const label = "class-of-2026 · Klasseøkt 1";
      const figures = busy(id, label, new Date());
      let fail = false;
      const route = new RegExp(`/api/admin/operations/class-sessions/${id}$`);
      await page.route(route, (r) =>
        fail ? r.fulfill({ status: 500, json: { error: { code: "internal", message: "", fields: {} } } }) : r.fulfill({ json: figures }),
      );
      try {
        await page.goto(`/admin/drift/${id}`);
        await expect(page.getByRole("heading", { level: 1, name: label })).toBeVisible();
        await expect(page.getByText(copy.errors.last24("6"))).toBeVisible();
        await expect(page.getByText(copy.errors.allTime("7"))).toBeVisible();
        await expect(page.getByText(copy.guard.value("50 %", "1", "2"))).toBeVisible();
        await expect(page.getByText(copy.fallback.base("9"))).toBeVisible();
        await expect(page.locator('[data-chart="error-hours"] [data-mark="hour"]')).toHaveCount(24);
        // The y axis has its round steps from 0, not only its top.
        expect(await page.locator('[data-axis="error-hours"] [data-tick]').count()).toBeGreaterThan(2);
        // An Effort level is named by its config's label; one without a label by its name.
        await expect(page.locator('[data-chart="response-times"]')).toContainText("Grundig");
        await expect(page.locator('[data-chart="response-times"]')).not.toContainText("deep");
        const fallbacks = page.locator('[data-chart="fallbacks"]');
        await expect(fallbacks).toContainText("Tidsavbrudd");
        await expect(fallbacks).toContainText("22,22 % (2)");
        await expect(page.locator('[data-chart="response-times"]')).toContainText("Median 200 ms");
        await expectAccessible(page, vp.phone);

        // «Vis som tabell»: every hour and its sources; and back.
        const errors = page.locator('[data-chart-block="errors"]');
        await errors.getByRole("button", { name: copy.showTable }).click();
        await expect(errors.locator("tbody tr")).toHaveCount(24);
        await expect(errors.locator("tbody tr").last()).toContainText("3");
        await expect(errors.getByRole("columnheader", { name: copy.errors.sources.api_error })).toBeVisible();
        const times = page.locator('[data-chart-block="response-times"]');
        await times.getByRole("button", { name: copy.showTable }).click();
        await expect(times.getByRole("row", { name: /fast/ })).toContainText("400 ms");
        await expect(times.getByRole("row", { name: /Grundig/ })).toContainText(/1\s?000\sms/);
        const fallbackBlock = page.locator('[data-chart-block="fallbacks"]');
        await fallbackBlock.getByRole("button", { name: copy.showTable }).click();
        await expect(fallbackBlock.getByRole("row", { name: /Feil hos leverandøren/ })).toContainText("11,11 %");
        await expectAccessible(page, vp.phone);
        await errors.getByRole("button", { name: copy.showChart }).click();
        await expect(page.locator('[data-chart="error-hours"]')).toBeVisible();

        // The next read, 30 s on, fails: the Tilkoblingslinje says so, the figures stay, «Prøv igjen».
        fail = true;
        await page.clock.fastForward(31_000);
        const line = page.locator("[data-connection-notice]");
        await expect(line).toContainText("Tallene kunne ikke leses på nytt.");
        await expect(page.getByText(copy.errors.last24("6"))).toBeVisible();
        fail = false;
        await line.getByRole("button", { name: nb.system.retry }).click();
        await expect(line).not.toContainText("Tallene kunne ikke leses på nytt.");
      } finally {
        await page.unroute(route);
      }
    });

    test("«Databasetilkoblinger» shows the stack's processes against the budget and the pooler check", async ({
      page,
    }) => {
      const budget = copy.connections;
      await loginByApi(page, "admin");
      await page.goto("/admin/drift");
      const section = page.locator("[data-connection-budget]");
      await expect(section.getByRole("heading", { level: 2, name: budget.title })).toBeVisible();
      // Each process of the stack reported at its start: `DB_POOL_SIZE` 10 and 5, the LISTEN
      // connection of `backend`, the workers' procrastinate pool (docs/ops/connection-budget.md).
      for (const [process, total] of [
        ["backend", "11"],
        ["worker-ai", "7"],
        ["worker-batch", "10"], // and Epic 13's report slots (docs/ops/connection-budget.md)
      ]) {
        const row = section.locator(`tr[data-process="${process}"]`);
        await expect(row.locator("td").nth(0)).toHaveText(total);
        await expect(row.locator("td").nth(1)).toHaveText(total);
      }
      await expect(section.locator("tfoot")).toContainText("28");
      await expect(section.getByText(budget.running.within("28", "28"))).toBeVisible();
      // The stack sets no `DB_POOLER_SIZE`: not checked, never passed.
      await expect(section.getByText(budget.pooler.notChecked("57"))).toBeVisible();
      await expect(section.getByText(budget.need("28", "56", "57"))).toBeVisible();
      await expectAccessible(page, vp.phone);
    });

    test("a process over its line and a pooler too small are named with their numbers", async ({ page }) => {
      await loginByApi(page, "admin");
      const counts = (pool: number, jobs: number, listen: number) => ({
        sqlalchemy_pool: pool,
        procrastinate_pool: jobs,
        listen,
        total: pool + jobs + listen,
      });
      const at = new Date().toISOString();
      const route = /\/api\/admin\/operations\/connections$/;
      await page.route(route, (r) =>
        r.fulfill({
          json: {
            read_at: at,
            processes: [
              { process: "backend", budget: counts(10, 0, 1), configured: counts(20, 0, 1), reported_at: at, over_budget: true },
              { process: "worker-ai", budget: counts(5, 2, 0), configured: counts(5, 2, 0), reported_at: at, over_budget: false },
              { process: "worker-batch", budget: counts(5, 2, 0), configured: null, reported_at: null, over_budget: false },
            ],
            budget_total: 25,
            overlap_total: 50,
            configured_total: 28,
            running: "over",
            pooler: { status: "failed", pooler_size: 15, required: 51 },
          },
        }),
      );
      try {
        await page.goto("/admin/drift");
        const section = page.locator("[data-connection-budget]");
        await expect(section.locator('tr[data-process="backend"]')).toContainText(copy.connections.over("21"));
        await expect(section.locator('tr[data-process="worker-batch"]')).toContainText(copy.connections.notReported);
        await expect(section.getByText(copy.connections.running.over("28", "25"))).toBeVisible();
        await expect(section.getByText(copy.connections.pooler.failed("15", "51"))).toBeVisible();
        await expectAccessible(page, vp.phone);
      } finally {
        await page.unroute(route);
      }
    });
  });
}
