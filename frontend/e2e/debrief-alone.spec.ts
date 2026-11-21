import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** Continue alone (Story 9.12, FR-43, AD-8, AD-21). Two Students of one real two-Uke Class game,
 * one at 360 px and one at 1440 px with axe: Sara opens the Group debrief, Ida joins; Sara, the
 * opener, leaves through the confirmation and goes on as a Personal debrief (the line under step 1
 * takes focus, and once she has sent, the reveal follows without the group), while Ida, the
 * earliest joined Student still there, gets «Gå videre for alle» over the event stream. Dropout and
 * the 48-hour fallback are the sweep's, in `backend/tests/debrief/test_group_alone.py`. */
const copy = nb.debriefEntry;
const group = copy.group;
const CSRF = { "X-Requested-With": "olspillet" };

async function live(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("the opener leaves and goes on alone; the group passes to the next Student", async ({ browser, lecturerSession }) => {
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

    // Sara opens it: a Group debrief she leads. Ida sees the way to join and the way alone.
    await a.goto(`/debrief/${game.sessionId}`);
    await expect(a.getByRole("button", { name: group.moveOn })).toBeVisible();
    await b.goto(`/debrief/${game.sessionId}`);
    await expect(b.getByRole("button", { name: group.goAlone })).toBeVisible();
    await expectAccessible(b, false);
    await b.getByRole("button", { name: group.join }).click();
    await expect(b.getByRole("button", { name: group.leave })).toBeVisible();
    await expect(b.getByRole("button", { name: group.moveOn })).toHaveCount(0);

    // Sara leaves: first a confirmation that says it is final, then the Personal debrief.
    await live(a);
    await live(b);
    await a.getByRole("button", { name: group.leave }).click();
    await expect(a.locator("[data-group-leave-confirm]")).toContainText(group.leaveConfirm);
    await expect(a.locator("[data-group-leave-confirm]").getByRole("button", { name: group.cancel })).toBeFocused();
    await a.locator("[data-group-leave-confirm]").getByRole("button", { name: group.leave }).click();
    const line = a.locator("[data-group-alone='left']");
    await expect(line).toHaveText(group.aloneLine.left);
    await expect(line).toBeFocused();
    await expect(a.locator("[data-group-bar]")).toHaveCount(0);
    await expect(a.getByRole("button", { name: group.moveOn })).toHaveCount(0);
    await expectAccessible(a, false);

    // Ida, still in the group, may now move it on, without reload.
    await expect(b.getByRole("button", { name: group.moveOn })).toBeVisible();

    // Sara sends and reads on alone: the reveal follows at once, while the group is on step 1.
    await a.getByRole("textbox", { name: copy.explanation.prompt }).fill("Jeg bestilte for mye etter restordren.");
    await a.getByRole("button", { name: copy.explanation.send }).click();
    await expect(a.locator("[data-debrief-reveal]")).toBeVisible();
    const debrief = await (await ida.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })).json();
    expect(debrief.group).toMatchObject({ step: 1, joined: true, opener: true });
    const rejoin = await sara.context.request.post(`/api/debriefs/${debrief.id}/join`, { headers: CSRF });
    expect([rejoin.status(), (await rejoin.json()).error.code]).toEqual([409, "group_closed"]);
    await expectAccessible(b, false);
    await a.close();
    await b.close();
  } finally {
    await sara.context.close();
    await ida.context.close();
  }
});
