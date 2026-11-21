import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** A Class session made from an earlier one (Story 5.18, cut list, `FEATURE_RERUN`, FR-66), on the
 * local stack, where the flag is on. A fresh Lecturer makes two fresh Classes through the api; the
 * source is changed through the api too. What is and is not copied, the Effort level, the scope and
 * the flag-off refusals are pinned by `backend/tests/sessions/test_rerun.py`; here the screens. */
const copy = nb.sessions;
const r = copy.list.rerun;
const CSRF = { "X-Requested-With": "olspillet" };

async function changedSource(lecturer: Page, classId: string): Promise<string> {
  const created = await lecturer.request.post(`/api/classes/${classId}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const id = (await created.json()).id as string;
  const saved = await lecturer.request.put(`/api/class-sessions/${id}`, {
    headers: CSRF,
    data: { ai_mode: "rule_based", debrief_mode: "personal", game_settings: { order_delay: 3 } },
  });
  expect(saved.status()).toBe(200);
  return id;
}

for (const viewport of [
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test(`a Class session copied from another Class opens prefilled and saves unchanged at ${viewport.name}`, async ({
    page,
    browser,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const lecturer = await freshLecturer(page, browser);
    const last = await freshClass(lecturer);
    const source = await changedSource(lecturer, last.id);
    const next = await freshClass(lecturer);

    await lecturer.goto(`/klasser/${next.id}`);
    const sessions = lecturer.getByRole("region", { name: copy.list.title });
    await sessions.getByRole("button", { name: r.open }).click();
    const panel = lecturer.getByRole("region", { name: r.title });
    // Focus on the first field (EXPERIENCE.md, Issue #116).
    const select = panel.getByLabel(r.source);
    await expect(select).toBeFocused();
    await expect(select).toHaveValue(source);
    // A long Class name breaks between words in the page heading, never inside one (Issue #116).
    const title = lecturer.getByRole("heading", { level: 1 });
    expect(await title.evaluate((h) => getComputedStyle(h).overflowWrap)).not.toBe("anywhere");
    await expect(select.locator("optgroup")).toHaveAttribute("label", last.name);
    await expect(select.locator("option")).toHaveText([r.option(1, r.noStart)]);
    const seed = panel.getByRole("switch", { name: new RegExp(r.keepSeed) });
    await expect(seed).toHaveAttribute("aria-checked", "false");
    await expect(panel.getByText(r.notCopied)).toBeVisible();
    await expectAccessible(lecturer, viewport.phone);

    await seed.click();
    await expect(seed).toHaveAttribute("aria-checked", "true");
    const made = lecturer.waitForResponse(`**/api/classes/${next.id}/class-sessions/copy`);
    await panel.getByRole("button", { name: r.submit }).click();
    expect((await made).status()).toBe(201);

    await expect(lecturer.getByRole("heading", { level: 1, name: copy.title(next.name) })).toBeVisible();
    await expect(lecturer.getByText(copy.copied.from(1, last.name))).toBeVisible();
    await expect(lecturer.getByText(copy.defaults)).toHaveCount(0);
    const delay = lecturer.locator("dl > div").filter({ hasText: copy.settings.orderDelay });
    await expect(delay).toContainText("3");
    const id = lecturer.url().split("/").pop()!;
    const [copied, was] = await Promise.all(
      [id, source].map(async (sessionId) => (await lecturer.request.get(`/api/class-sessions/${sessionId}`)).json()),
    );
    expect(copied.game_settings).toEqual(was.game_settings);
    expect(copied.debrief_mode).toBe("personal");
    await expectAccessible(lecturer, viewport.phone);

    await lecturer.getByRole("button", { name: copy.save }).click();
    await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
    await expect(lecturer.getByText(copy.copied.from(1, last.name))).toHaveCount(0);
  });
}

test("Avbryt closes the panel and returns focus to the Lenke", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  await lecturer.goto(`/klasser/${klass.id}`);
  const open = lecturer.getByRole("button", { name: r.open });
  await open.click();
  const panel = lecturer.getByRole("region", { name: r.title });
  // A new Lecturer's only Class has no session yet: no field, so focus is on the heading.
  await expect(panel.getByText(r.none)).toBeVisible();
  await expect(panel.getByRole("heading", { name: r.title })).toBeFocused();
  await expect(panel.getByRole("button", { name: r.submit })).toHaveCount(0);
  await panel.getByRole("button", { name: r.cancel }).click();
  await expect(panel).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: r.open })).toBeFocused();
});

test("with the flag off no copy option shows", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  // The server's answer with `FEATURE_RERUN` off; its 422 is pinned by the api tests.
  await lecturer.route(`**/api/classes/${klass.id}/class-sessions`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), rerun_enabled: false } });
  });
  await lecturer.goto(`/klasser/${klass.id}`);
  await expect(lecturer.getByRole("button", { name: copy.list.create })).toBeVisible();
  await expect(lecturer.getByRole("button", { name: r.open })).toHaveCount(0);
});

test("a source whose settings the engine refuses now says so in the panel", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  await changedSource(lecturer, klass.id);
  // The api's refusal of settings that no longer pass (pinned by the api tests), stubbed here.
  await lecturer.route(`**/api/classes/${klass.id}/class-sessions/copy`, (route) =>
    route.fulfill({
      status: 422,
      json: { error: { code: "invalid_settings", message: "x", fields: { order_delay: { code: "out_of_range" } } } },
    }),
  );
  await lecturer.goto(`/klasser/${klass.id}`);
  await lecturer.getByRole("button", { name: r.open }).click();
  const panel = lecturer.getByRole("region", { name: r.title });
  await panel.getByRole("button", { name: r.submit }).click();
  await expect(panel.getByRole("alert")).toHaveText(r.refused);
});
