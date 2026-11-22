import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** Opening the Debrief (Story 9.2, FR-42, NFR-6, UX-DR12, UX-DR31). The Debrief page's three
 * states at 320, 360 and 1440 px with axe, from stand-in answers of the Debrief endpoint (the api's
 * rules, refusals and release are `backend/tests/debrief/test_debrief.py`); a real two-Uke game
 * that ends and opens the Debrief through «Gå til Debrief» and Stegene; and the Faglærer's choice
 * on the Klasseøkt. */
const copy = nb.debriefEntry;
const c = nb.sessions.choices;
const CSRF = { "X-Requested-With": "olspillet" };
const SESSION = "01a1aaaa-0000-7000-8000-000000000001";

const OPENED = {
  id: "01a1aaaa-0000-7000-8000-0000000000d1",
  class_session_id: SESSION,
  game_id: "01a1aaaa-0000-7000-8000-0000000000a1",
  game_number: 17,
  role: "wholesaler",
  step: 1,
};

/** The Debrief endpoint answers `state`; the route is removed before the page closes. */
async function openWith(page: Page, state: "open" | "debrief_not_open" | "debrief_held") {
  const path = `**/api/me/class-sessions/${SESSION}/debrief`;
  await page.route(path, (route) =>
    state === "open"
      ? route.fulfill({ json: OPENED })
      : route.fulfill({ status: 403, json: { error: { code: state, message: "x", fields: {} } } }),
  );
  await page.goto(`/debrief/${SESSION}`);
  return () => page.unroute(path);
}

for (const viewport of [
  { width: 320, height: 640, phone: true },
  { width: 360, height: 740, phone: true },
  { width: 1440, height: 900, phone: false },
]) {
  test.describe(`${viewport.width} px`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("the open, locked and held Debrief", async ({ page }) => {
      await loginByApi(page, "student");
      const main = page.getByRole("main");

      let unroute = await openWith(page, "open");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title(17));
      await expect(main.getByText(copy.roleGame("Grossist", 17), { exact: true })).toBeVisible();
      const step = main.getByRole("heading", { level: 2 });
      await expect(step).toHaveAccessibleName(`${copy.stepOf(1, 5)}: ${copy.firstStep}`);
      await expect(page.locator("[data-debrief-step]")).toHaveAttribute("data-debrief-step", "1");
      await expectAccessible(page, viewport.phone);
      await unroute();

      unroute = await openWith(page, "debrief_not_open");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.locked);
      await expect(main.getByText(copy.notOpen, { exact: true })).toBeVisible();
      await expect(main.getByRole("link", { name: nb.navigation.toHome })).toHaveAttribute("href", "/hjem");
      await expectAccessible(page, viewport.phone);
      await unroute();

      unroute = await openWith(page, "debrief_held");
      await expect(main.getByText(copy.held, { exact: true })).toBeVisible();
      await expect(main.getByText(/\d/)).toHaveCount(0);
      await expectAccessible(page, viewport.phone);
      await unroute();
    });
  });
}

test("another Student's or an unknown Class session shows the permission-denied page", async ({ page }) => {
  await loginByApi(page, "student");
  await page.goto("/debrief/not-a-session");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.access.denied);
});

test("live: before the end the Debrief is locked; «Gå til Debrief» and Stegene open it at step 1", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 1, {
    aiMode: "rule_based",
    gameSettings: { weeks: 2, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [me] = game.students as [(typeof game.students)[0]];
  try {
    const page = await me.context.newPage();
    // Running: the Debrief says it opens when the Klassespill is finished; Stegene says the same.
    await page.goto(`/debrief/${game.sessionId}`);
    await expect(page.getByRole("main").getByText(copy.notOpen, { exact: true })).toBeVisible();
    await page.goto("/hjem");
    await expect(page.getByRole("main").getByText(nb.homes.student.locked.debrief, { exact: true })).toBeVisible();

    await orderByApi(me, game.gameId, 1, 4);
    await orderByApi(me, game.gameId, 2, 4);
    await page.goto(`/spill/${game.gameId}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.end.title);
    const toDebrief = page.getByRole("link", { name: nb.games.play.end.toDebrief });
    await expect(toDebrief).toHaveAttribute("href", `/debrief/${game.sessionId}`);
    await toDebrief.click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title(1));
    await expect(page.getByRole("main").getByRole("heading", { level: 2 })).toContainText(copy.firstStep);

    // Stegene's Debrief step leads to the same Debrief, opened once.
    await page.goto("/hjem");
    const steps = page.getByRole("region", { name: nb.homes.student.steps });
    const link = steps.getByRole("link", { name: nb.homes.student.stepNames.debrief });
    await expect(link).toHaveAttribute("href", `/debrief/${game.sessionId}`);
    const first = await (await me.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })).json();
    await link.click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title(1));
    const again = await (await me.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })).json();
    expect([again.id, again.step]).toEqual([first.id, 1]);
  } finally {
    await me.context.close();
  }
});

test("the Faglærer chooses to hold the Debriefs; it takes effect on save", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  const id = (await created.json()).id as string;
  await lecturer.goto(`/klasseokter/${id}`);
  const release = lecturer.getByRole("group", { name: c.debriefRelease, exact: true });
  await expect(release.getByRole("radio", { name: c.releaseOpen })).toBeChecked();
  await expect(release).toHaveAccessibleDescription(c.releaseOpenHelp);
  await release.getByText(c.releaseHold, { exact: true }).click();
  await expect(release).toHaveAccessibleDescription(c.releaseHoldHelp);
  expect((await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).debrief_release).toBe("open");
  await lecturer.getByRole("button", { name: nb.sessions.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
  expect((await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).debrief_release).toBe("hold");
  await lecturer.reload();
  await expect(
    lecturer.getByRole("group", { name: c.debriefRelease, exact: true }).getByRole("radio", { name: c.releaseHold }),
  ).toBeChecked();
});
