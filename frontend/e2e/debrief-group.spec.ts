import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The Group debrief (Story 9.11, FR-43, UX-DR31, AD-8, NFR-6). Two Students of one real two-Uke
 * Class game, each in a browser context of their own, one at 360 px and one at 1440 px with axe:
 * the first open makes it a Group debrief, Hjem offers the other to join, the reveal stays locked
 * with who has sent and who writes, the second Explanation moves both pages to step 2 over the
 * event stream without reload, and the opener alone moves the group on, refused before the wait
 * (the wait is shortened through the local dev route). The api's rules are
 * `backend/tests/debrief/test_group.py`. */
const copy = nb.debriefEntry;
const group = copy.group;
const CSRF = { "X-Requested-With": "olspillet" };

async function live(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

async function sendExplanation(page: Page, text: string) {
  await page.getByRole("textbox", { name: copy.explanation.prompt }).fill(text);
  await page.getByRole("button", { name: copy.explanation.send }).click();
  await expect(page.locator("[data-explanation-sent]").getByText(text, { exact: true })).toBeVisible();
}

test("two Students go through the shared steps together; the opener moves them on", async ({ browser, lecturerSession }) => {
  test.slow(); // two Invitations through the worker, a Class session, a lock and a played game
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    gameSettings: { weeks: 2, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [sara, ida] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  try {
    for (const week of [1, 2]) {
      await orderByApi(sara, game.gameId, week, 4);
      await orderByApi(ida, game.gameId, week, 4);
    }
    const a = await sara.context.newPage();
    await a.setViewportSize({ width: 360, height: 740 });
    const b = await ida.context.newPage();
    await b.setViewportSize({ width: 1440, height: 900 });

    // Sara opens it first: a Group debrief she opened and joined, with the time guide.
    await a.goto(`/debrief/${game.sessionId}`);
    await expect(a.getByRole("heading", { level: 1 })).toHaveText(copy.title(1));
    await expect(a.locator("[data-group-bar='1'] [data-group-line]")).toHaveText(group.timeGuide);
    await expect(a.getByRole("button", { name: group.moveOn })).toBeVisible();
    const debrief = await (await sara.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })).json();
    expect(debrief.group).toMatchObject({ step: 1, joined: true, opener: true });

    // Ida's Hjem offers to join; its Debrief step leads to the way in.
    await b.goto("/hjem");
    const steps = b.getByRole("region", { name: nb.homes.student.steps });
    await expect(steps.getByText(nb.homes.student.groupOpen)).toBeVisible();
    await steps.getByRole("link", { name: nb.homes.student.stepNames.debrief }).click();
    await expect(b.getByRole("heading", { level: 2, name: group.title })).toBeVisible();
    await expect(b.getByRole("textbox", { name: copy.explanation.prompt })).toHaveCount(0);
    await expectAccessible(b, false);
    await b.getByRole("button", { name: group.join }).click();
    await expect(b.getByRole("heading", { level: 2, name: `${copy.stepOf(1, 5)}: ${copy.firstStep}` })).toBeFocused();
    await expect(b.getByRole("button", { name: group.moveOn })).toHaveCount(0);

    // Sara sends; Ida writes. Sara sees who has sent, never what anyone wrote; no reveal yet.
    await live(a);
    await sendExplanation(a, "Restordren vokste, så jeg bestilte mye.");
    const locked = group.locked(group.everyone(2), "Du", ida.name);
    await expect(a.locator("[data-group-bar='1'] [data-group-line]")).toHaveText(locked);
    await expect(a.locator("[data-debrief-reveal]")).toHaveCount(0);
    const refused = await sara.context.request.get(`/api/debriefs/${debrief.id}/steps/2`);
    expect([refused.status(), (await refused.json()).error.code]).toEqual([403, "step_locked"]);
    await expectAccessible(a, true);

    // Ida sends: both pages move to step 2 over the event stream, and Sara hears it politely.
    await live(b);
    await sendExplanation(b, "Jeg så bare ordrene inn.");
    await expect(a.locator("[data-debrief-reveal]")).toBeVisible();
    await expect(a.locator("[data-group-announce]")).toHaveText(group.unlocked);
    await expect(b.locator("[data-debrief-reveal]")).toBeVisible();
    await expect(a.locator("[data-debrief-chain]")).toHaveCount(0);

    // The opener moves on too early: told when it becomes possible. Ida has no control, and the
    // api refuses her.
    await expect(b.getByRole("button", { name: group.moveOn })).toHaveCount(0);
    const notOpener = await ida.context.request.post(`/api/debriefs/${debrief.id}/move-on`, { headers: CSRF });
    expect(notOpener.status()).toBe(403);
    await a.getByRole("button", { name: group.moveOn }).click();
    await expect(a.locator("[data-group-bar='2']").getByRole("alert")).toContainText("Gruppen kan gå videre fra kl.");
    await expect(a.locator("[data-debrief-chain]")).toHaveCount(0);

    // Once the step has been open the wait (shortened here), the opener moves everyone to step 3.
    expect((await sara.context.request.post(`/api/dev/debriefs/${debrief.id}/backdate`, { headers: CSRF })).ok()).toBe(true);
    await a.getByRole("button", { name: group.moveOn }).click();
    await expect(a.locator("[data-debrief-chain]").first()).toBeVisible();
    await expect(b.locator("[data-debrief-chain]").first()).toBeVisible();
    await expect(b.getByRole("button", { name: group.done })).toBeVisible();
    await expectAccessible(b, false);
    await a.close();
    await b.close();
  } finally {
    await sara.context.close();
    await ida.context.close();
  }
});
