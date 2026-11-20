import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, freshLecturer } from "./support/classes";

/** Creating a Class session with the Classic defaults (Story 5.1, FR-5, FR-11, NFR-6, UX-DR48), on
 * the local stack. A fresh Lecturer makes a fresh Class through the api; the flow from the Klasse
 * page to a saved Class session edits no field. The demo Class is only read, by its Assistant. The
 * rules on every route are pinned by `backend/tests/sessions/test_class_sessions.py`. */
const copy = nb.sessions;
const CSRF = { "X-Requested-With": "olspillet" };

test("from the Klasse page to a saved Class session without editing a field", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  await lecturer.goto(`/klasser/${klass.id}`);
  const sessions = lecturer.getByRole("region", { name: copy.list.title });
  await expect(sessions.getByText(copy.list.empty)).toBeVisible();
  await sessions.getByRole("button", { name: copy.list.create }).click();

  await expect(lecturer.getByRole("heading", { level: 1, name: copy.title(klass.name) })).toBeVisible();
  await expect(lecturer).toHaveURL(/\/klasseokter\/[0-9a-f-]{36}$/);
  await expect(lecturer.getByText(copy.defaults)).toBeVisible();
  await expect(lecturer.getByRole("heading", { name: copy.settingsTitle })).toBeVisible();
  await expect(lecturer.getByText(copy.delaySources)).toBeVisible();
  await expect(lecturer.getByRole("heading", { name: copy.chain.title })).toBeVisible();
  await expect(lecturer.getByText(copy.chain.caption)).toBeVisible();
  // The diagram is named by the same values in text, read from the API's answer.
  const diagram = lecturer.getByRole("img", { name: /Fabrikk, Distributør, Grossist og Detaljist starter med Lager 12/ });
  await expect(diagram).toBeVisible();
  await expect(diagram).toContainText("Lager 12");

  const save = lecturer.getByRole("button", { name: copy.save });
  await save.click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();

  await lecturer.getByRole("link", { name: klass.name }).click();
  const listed = lecturer.getByRole("region", { name: copy.list.title }).getByRole("listitem");
  await expect(listed).toHaveCount(1);
  await expect(listed).toContainText(copy.list.saved);
});

test("a save that fails says so, keeps focus on the button and the values on the screen", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  await lecturer.goto(`/klasseokter/${(await created.json()).id}`);
  const save = lecturer.getByRole("button", { name: copy.save });
  await expect(save).toBeVisible();
  await lecturer.route("**/api/class-sessions/*", (route) =>
    route.request().method() === "PUT" ? route.abort("internetdisconnected") : route.fallback(),
  );
  await save.click();
  await expect(lecturer.getByRole("main").getByRole("alert")).toHaveText(nb.system.actionFailed);
  await expect(save).toBeFocused();
  await expect(lecturer.getByText(copy.defaults)).toBeVisible();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toHaveCount(0);
  // A failure on the server reads the same.
  await lecturer.unrouteAll();
  await lecturer.route("**/api/class-sessions/*", (route) =>
    route.request().method() === "PUT"
      ? route.fulfill({ status: 500, json: { error: { code: "internal_error", message: "x" } } })
      : route.fallback(),
  );
  await save.click();
  await expect(lecturer.getByRole("main").getByRole("alert")).toHaveText(nb.system.actionFailed);
  await expect(save).toBeFocused();
});

test("the owner of an archived Class reads its Klasseøkt with no save and is told why", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect((await lecturer.request.post(`/api/classes/${klass.id}/archive`, { headers: CSRF })).status()).toBe(200);
  await lecturer.goto(`/klasseokter/${(await created.json()).id}`);
  await expect(lecturer.getByText(nb.classes.archive.notice)).toBeVisible();
  await expect(lecturer.getByText(copy.assistantLead)).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveCount(0);
  // The Game settings do not open either (Story 5.3).
  await expect(lecturer.getByRole("button", { name: copy.edit.open })).toHaveCount(0);
  // The dates stand as text, not as fields (Story 5.2, Story 5.11).
  for (const [key, name] of Object.entries(copy.dates.names)) {
    await expect(lecturer.getByRole("group", { name, exact: true })).toContainText(copy.dates.notSet);
    await expect(lecturer.locator(`input#date-${key}`)).toHaveCount(0);
  }
});

test("an Assistant lecturer reads the Class sessions and has no action to create one", async ({ page }) => {
  await loginByApi(page, "assistant");
  await page.goto("/laererhjem");
  await page.getByRole("link", { name: /class-of-1994/ }).click();
  await expect(page.getByRole("heading", { level: 2, name: copy.list.title })).toBeVisible();
  await expect(page.getByRole("button", { name: copy.list.create })).toHaveCount(0);
  const classId = page.url().split("/").pop()!;
  const refused = await page.request.post(`/api/classes/${classId}/class-sessions`, { headers: CSRF });
  expect(refused.status()).toBe(403);
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`the Klasseøkt, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("passes axe with no horizontal scroll, in one column below 1024 px", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const klass = await freshClass(lecturer);
      const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
      await lecturer.goto(`/klasseokter/${(await created.json()).id}`);
      await expect(lecturer.getByRole("heading", { level: 1, name: copy.title(klass.name) })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
      if (vp.width < 1024) {
        const settings = await lecturer.getByRole("heading", { name: copy.settingsTitle }).boundingBox();
        const save = await lecturer.getByRole("button", { name: copy.save }).boundingBox();
        expect(save!.x).toBeLessThanOrEqual(settings!.x + 1);
      }
      await lecturer.goto(`/klasser/${klass.id}`);
      await expect(lecturer.getByRole("heading", { level: 2, name: copy.list.title })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
