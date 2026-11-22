import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { dayUsdText } from "../src/modules/admin/daily-spend";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test, VIEWPORTS } from "./support/classes";

/** «KI-kostnad» in the Admin-område (Story 15.5, FR-68, FR-78, NFR-6), on the local stack with its
 * zero-config mock model. Each test makes a fresh Class session through the api. The rules (the
 * lock refusal, the Effort levels a pin offers, the freeze and its default, audit rows) are pinned
 * by `backend/tests/ops/test_model_pinning.py`. */
const copy = nb.admin.aiCost;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;

/** A saved Class session with LLM players and its four dates, and how the page names it. */
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

/** No freeze left by an earlier run: the stack holds at most one. */
async function noFreeze(admin: Page) {
  const state = await (await admin.request.get("/api/admin/ai/freeze")).json();
  if (state.active) {
    const lifted = await admin.request.post(`/api/admin/ai/freezes/${state.active.id}/lift`, { headers: CSRF });
    expect([200, 409]).toContain(lifted.status());
  }
}

for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin sees the models, pins one before the Start date and sees it read-only once locked", async ({
      page,
      browser,
      lecturerSession,
    }) => {
      const lecturer = await lecturerPage(browser, lecturerSession, vp);
      const { id, label } = await savedSession(lecturer);

      // A Lecturer gets the permission-denied page.
      await lecturer.goto("/admin/ki-kostnad");
      await expect(lecturer.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();

      await loginByApi(page, "admin");
      await page.goto("/admin");
      await page.getByRole("link", { name: nb.admin.sections.aiCost }).click();
      await expect(page).toHaveURL(/\/admin\/ki-kostnad$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();

      // The configs with their facts and the measurement of each Effort level.
      const configs = page.getByRole("region", { name: copy.configs.title });
      await expect(configs.getByRole("article").first()).toBeVisible();
      await expect(configs.getByText(copy.configs.isDefault)).toBeVisible();
      await expect(configs.getByText(copy.configs.mockMeasured).first()).toBeVisible();

      // The pin: the row's model choice and one press; the row says what changed.
      const sessions = page.getByRole("region", { name: copy.sessions.title });
      const row = sessions.locator("tbody tr").filter({ hasText: label });
      await expect(row.getByLabel(copy.sessions.choose(label))).toBeVisible();
      await row.getByRole("button", { name: copy.sessions.pin(label) }).click();
      await expect(row.getByRole("status")).toContainText(`${label} bruker nå`);
      await expectAccessible(page, vp.phone);

      // Locked: the model, its endpoint and prompt versions are shown, and nothing can be pinned.
      const locked = await lecturer.request.post(`/api/dev/class-sessions/${id}/lock`, { headers: CSRF });
      expect(locked.status()).toBe(200);
      await page.reload();
      const lockedRow = page
        .getByRole("region", { name: copy.sessions.title })
        .locator("tbody tr")
        .filter({ hasText: label });
      await expect(lockedRow).toContainText(copy.sessions.lockedNote);
      await expect(lockedRow).toContainText(copy.sessions.prompts);
      await expect(lockedRow).toContainText("mock://local");
      await expect(lockedRow.getByRole("button", { name: copy.sessions.pin(label) })).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });
  });
}

test("the Admin freezes the default model for a study and lifts it", async ({ page, browser, lecturerSession }) => {
  const vp = VIEWPORTS.find((v) => !v.phone && !v.text200)!;
  await page.setViewportSize({ width: vp.width, height: vp.height });
  const lecturer = await lecturerPage(browser, lecturerSession, vp);
  const { label } = await savedSession(lecturer);
  await loginByApi(page, "admin");
  await noFreeze(page);
  await page.goto("/admin/ki-kostnad");

  // The form chooses the default model, so other Class sessions made meanwhile see no change.
  const freeze = page.getByRole("region", { name: copy.freeze.title });
  const configs = (await (await page.request.get("/api/admin/ai/model-configs")).json()).items;
  const fallback = configs.find((item: { active_default: boolean }) => item.active_default);
  await expect(freeze.getByLabel(copy.freeze.model)).toHaveValue(fallback.id);

  // Nothing chosen: the reason under the choice, nothing sent.
  await freeze.getByRole("button", { name: copy.freeze.submit }).click();
  await expect(freeze.getByText(copy.freeze.pickOne)).toBeVisible();

  try {
    await freeze.getByRole("checkbox", { name: label }).check();
    await freeze.getByRole("button", { name: copy.freeze.submit }).click();
    await expect(freeze.getByText(/er fryst for 1 Klasseøkt siden/)).toBeVisible();
    const row = page.getByRole("region", { name: copy.sessions.title }).locator("tbody tr").filter({ hasText: label });
    await expect(row).toContainText(copy.sessions.inStudy);
    await expect(page.getByRole("region", { name: copy.configs.title }).getByText(copy.configs.isFrozen)).toBeVisible();
    await expectAccessible(page, vp.phone);

    await freeze.getByRole("button", { name: copy.freeze.lift }).click();
    await expect(freeze.getByRole("status")).toHaveText(copy.freeze.lifted);
    await expect(row).not.toContainText(copy.sessions.inStudy);
    await expect(freeze.getByRole("button", { name: copy.freeze.submit })).toBeVisible();
  } finally {
    // The freeze is the stack's one: never leave it to the specs that run after this one.
    await noFreeze(page);
  }
});

/** «KI-kostnad per dag» (Story 15.7, FR-69). The stack's mock model costs nothing and the sweep's
 * alert is pinned by `backend/tests/ops/test_daily_spend_alert.py`, so the alerted day is served
 * from a route here to show how the page and the Admin-område read it. */
for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test(`${vp.name}: the Admin reads the AI spend of a day and the alert of today`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await loginByApi(page, "admin");
    const today = (await (await page.request.get("/api/admin/ai/daily-spend")).json()) as {
      day: string;
      alert_usd: string | null;
    };
    // The stack's amount, as the page writes it (the placeholder unless the stack sets another).
    const limit = today.alert_usd === null ? null : dayUsdText(today.alert_usd);
    const [year, month, date] = today.day.split("-").map(Number);
    const yesterday = new Date(Date.UTC(year, month - 1, date - 1)).toISOString().slice(0, 10);

    // Today, unless `?dag=` names a real day: the total, the alert amount, no later day.
    await page.goto("/admin/ki-kostnad?dag=ikke-en-dag");
    const section = page.getByRole("region", { name: copy.day.title });
    await expect(section.getByText(limit === null ? copy.day.noAlert : copy.day.alertLimit(limit))).toBeVisible();
    await expect(section.getByText(/USD for .* KI-kall\./)).toBeVisible();
    const days = section.getByRole("navigation", { name: copy.day.days });
    await expect(days.getByRole("link", { name: /^Neste dag/ })).toHaveCount(0);
    await days.getByRole("link", { name: /^Forrige dag/ }).click();
    await expect(page).toHaveURL((url) => url.searchParams.get("dag") === yesterday);
    await expect(days.getByRole("link", { name: /^Neste dag/ })).toBeVisible();
    await expectAccessible(page, vp.phone);

    // An alerted day: the page says when, and the Admin-område shows it under «KI-kostnad».
    const alerted = {
      day: today.day,
      today: today.day,
      total_usd: "31.25000000",
      calls: 4210,
      evaluation_usd: "1.00000000",
      alert_usd: "25.00",
      passed: true,
      alerted_at: new Date().toISOString(),
      sessions: [
        {
          class_session_id: "00000000-0000-7000-8000-000000000001",
          label: "class-of-2026 · Klasseøkt 1",
          institution_name: "USN Bø",
          usd: "30.25000000",
          calls: 4100,
        },
      ],
      session_count: 1,
    };
    const route = /\/api\/admin\/ai\/daily-spend(\?.*)?$/;
    await page.route(route, (r) => r.fulfill({ json: alerted }));
    try {
      await page.goto("/admin");
      const line = page.getByText(copy.day.homeAlert(`25,00 USD`));
      await expect(line).toBeVisible();
      await expectAccessible(page, vp.phone);
      await page.getByRole("link", { name: copy.day.homeAlertLink }).click();
      await expect(page).toHaveURL(
        (url) => url.pathname === "/admin/ki-kostnad" && url.searchParams.get("dag") === today.day,
      );
      await expect(section.getByText(copy.day.passed)).toBeVisible();
      await expect(section.getByRole("cell", { name: /class-of-2026 · Klasseøkt 1/ })).toBeVisible();
      await expectAccessible(page, vp.phone);
    } finally {
      await page.unroute(route);
    }
  });
}
