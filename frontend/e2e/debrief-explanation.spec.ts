import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";
import { REVEAL } from "./support/reveal";

/** Debrief step 1, the Explanation before the reveal (Story 9.3, FR-41, FR-73, NFR-6, UX-DR11,
 * UX-DR31, AD-10). The step at 320, 360 (also with 200 % text) and 1440 px with axe and a send by
 * keyboard alone, from stand-in answers of the Debrief endpoints; a failed send that keeps the
 * text; a draft kept over a reload and never sent; and a real two-Uke game whose Student sends
 * their Explanation, which opens the steps after step 1 in the api (the api's rules are
 * `backend/tests/debrief/test_explanation.py`). */
const copy = nb.debriefEntry;
const words = copy.explanation;
const CSRF = { "X-Requested-With": "olspillet" };
const SESSION = "01a1aaaa-0000-7000-8000-000000000093";
const DEBRIEF = "01a1aaaa-0000-7000-8000-0000000009d3";
const OPENED = {
  id: DEBRIEF,
  class_session_id: SESSION,
  game_id: "01a1aaaa-0000-7000-8000-0000000009a3",
  game_number: 17,
  role: "wholesaler",
  step: 1,
};
/** 36 Uker as `07-debrief.png` draws them: stock, a long backlog, stock again. */
const WEEKS = Array.from({ length: 36 }, (_, i) => ({
  week: i + 1,
  net_inventory: i < 6 ? 12 : i < 22 ? Math.round(-38 * Math.sin(((i - 6) / 16) * Math.PI)) : 18 - (i % 5),
}));
const TEXT = "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.";

type Stub = { posts: string[]; unroute: () => Promise<void> };

/** The Debrief endpoints answer the open step 1; `send` is how «Send Forklaring» is answered. */
async function stepOne(page: Page, send: "saved" | "failed" | "exists" = "saved", netFails = false): Promise<Stub> {
  const posts: string[] = [];
  let stored: { text: string; length: number; saved_at: string } | null = null;
  const error = (status: number, code: string) => ({ status, json: { error: { code, message: "x", fields: {} } } });
  await page.route(`**/api/me/class-sessions/${SESSION}/debrief`, (route) => route.fulfill({ json: OPENED }));
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) =>
    route.fulfill(netFails ? error(500, "internal_error") : { json: { weeks: WEEKS } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/explanation`, (route) => {
    if (route.request().method() !== "POST") return route.fulfill({ json: { explanation: stored } });
    const text = (route.request().postDataJSON() as { text: string }).text;
    posts.push(text);
    if (send === "saved") return route.fulfill({ status: 201, json: { text, length: text.length, saved_at: "2026-11-21T12:00:00Z" } });
    if (send === "failed") return route.fulfill(error(500, "internal_error"));
    // Sent from another device: the api keeps the first one.
    stored = { text: "Fra den andre enheten.", length: 22, saved_at: "2026-11-21T11:00:00Z" };
    return route.fulfill(error(409, "explanation_exists"));
  });
  // Once the Explanation is stored, step 2 follows under step 1 (Story 9.4).
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/2`, (route) =>
    route.fulfill(stored || posts.length ? { json: { debrief_id: DEBRIEF, step: 2, reveal: REVEAL, chain: null } } : error(403, "explanation_required")),
  );
  // Step 3 (Story 9.5) is `debrief-chain.spec.ts`; here it has nothing to show.
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/3`, (route) =>
    route.fulfill(stored || posts.length ? { json: { debrief_id: DEBRIEF, step: 3, reveal: null, chain: null } } : error(403, "explanation_required")),
  );
  return { posts, unroute: () => page.unrouteAll({ behavior: "ignoreErrors" }) };
}

function field(page: Page) {
  return page.getByRole("textbox", { name: words.prompt });
}

function sendButton(page: Page) {
  return page.getByRole("button", { name: words.send });
}

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false },
  { name: "360 px with 200 % text", width: 360, height: 740, phone: true, text200: true },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("step 1: the own Netto lager, its table, the field and a send by keyboard", async ({ page }) => {
      if (viewport.text200) {
        await page.addInitScript(() => {
          document.addEventListener("DOMContentLoaded", () => {
            const style = document.createElement("style");
            style.textContent = "html { font-size: 200% !important; }";
            document.head.appendChild(style);
          });
        });
      }
      await loginByApi(page, "student");
      const stub = await stepOne(page);
      await page.goto(`/debrief/${SESSION}`);
      const main = page.getByRole("main");
      await expect(main.getByRole("heading", { level: 2 })).toHaveAccessibleName(`${copy.stepOf(1, 5)}: ${copy.firstStep}`);
      await expect(main.getByRole("heading", { level: 3, name: words.netTitle })).toBeVisible();
      const chart = page.locator("svg[data-chart=net-over-game]");
      await expect(chart).toBeVisible();
      await expect(chart.locator("[data-mark=net]")).toHaveAttribute("data-weeks", WEEKS.map((w) => w.week).join(" "));
      // Empty: the button cannot act and says why beside the field.
      await expect(sendButton(page)).toHaveAttribute("aria-disabled", "true");
      await expect(sendButton(page)).toHaveAccessibleDescription(words.empty);
      await expectAccessible(page, viewport.phone);

      // «Vis som tabell»: Uke and Netto lager for every Uke, in place of the chart.
      await main.getByRole("button", { name: words.showTable }).click();
      const table = main.getByRole("table", { name: words.tableCaption });
      await expect(table.getByRole("row")).toHaveCount(WEEKS.length + 1);
      await expect(table.getByRole("columnheader")).toHaveText([nb.terms.week, words.netColumn]);
      await expect(chart).toHaveCount(0);
      // The table is capped and scrolls inside its region, so the field stays near (Story 9.4 fix).
      const region = main.getByRole("group", { name: words.netTitle });
      const box = await region.evaluate((el) => ({
        capped: el.scrollHeight > el.clientHeight,
        lines: el.clientHeight / parseFloat(getComputedStyle(el).fontSize),
      }));
      expect(box.capped).toBe(true);
      expect(box.lines).toBeLessThanOrEqual(22.5);
      // Scrolled down, the header row stays in view.
      await region.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      await expect(table.getByRole("columnheader").first()).toBeInViewport();
      await expectReflow(page, viewport.phone);
      await main.getByRole("button", { name: words.showChart }).click();
      await expect(chart).toBeVisible();

      // Keyboard alone: into the field, type, on to the button, send.
      await field(page).focus();
      await page.keyboard.type(TEXT);
      await expect(sendButton(page)).not.toHaveAttribute("aria-disabled", "true");
      await page.keyboard.press("Tab");
      await expect(sendButton(page)).toBeFocused();
      await page.keyboard.press("Enter");
      const sent = main.locator("[data-explanation-sent]");
      await expect(sent.getByText(TEXT, { exact: true })).toBeVisible();
      await expect(sent.getByRole("status")).toHaveText(words.sent);
      await expect(main.getByRole("heading", { level: 3, name: words.sentTitle })).toBeFocused();
      await expect(field(page)).toHaveCount(0);
      expect(stub.posts).toEqual([TEXT]);
      await expectReflow(page, viewport.phone);
      await stub.unroute();
    });
  });
}

test("a failed send keeps the text and says so; nothing is sent without the press", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await stepOne(page, "failed");
  await page.goto(`/debrief/${SESSION}`);
  await field(page).fill(TEXT);
  // A reload restores the draft from this device and sends nothing.
  await page.reload();
  await expect(field(page)).toHaveValue(TEXT);
  expect(stub.posts).toEqual([]);
  await sendButton(page).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText(words.failed);
  await expect(field(page)).toHaveValue(TEXT);
  await expect(sendButton(page)).not.toHaveAttribute("aria-disabled", "true");
  expect(stub.posts).toEqual([TEXT]);
  // The draft is still kept after the failure.
  await page.reload();
  await expect(field(page)).toHaveValue(TEXT);
  await stub.unroute();
});

test("live: the Student's Explanation is sent once and opens the steps after step 1", async ({ browser, lecturerSession }) => {
  test.slow(); // an Invitation through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 1, {
    aiMode: "rule_based",
    gameSettings: { weeks: 2, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [me] = game.students as [(typeof game.students)[0]];
  try {
    await orderByApi(me, game.gameId, 1, 4);
    await orderByApi(me, game.gameId, 2, 4);
    const page = await me.context.newPage();
    await page.goto(`/debrief/${game.sessionId}`);
    const debrief = await (await me.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })).json();
    await expect(page.locator("svg[data-chart=net-over-game] [data-mark=net]")).toHaveAttribute("data-weeks", "1 2");

    // Before the Explanation the api refuses the next step.
    const step2 = `/api/debriefs/${debrief.id}/steps/2`;
    const before = await me.context.request.get(step2);
    expect(before.status()).toBe(403);
    expect((await before.json()).error.code).toBe("explanation_required");

    await field(page).fill(TEXT);
    await page.reload();
    await expect(field(page)).toHaveValue(TEXT);
    await sendButton(page).click();
    await expect(page.locator("[data-explanation-sent]").getByText(TEXT, { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.locator("[data-explanation-sent]").getByText(TEXT, { exact: true })).toBeVisible();
    await expect(field(page)).toHaveCount(0);

    const after = await me.context.request.get(step2);
    expect(after.status()).toBe(200);
    // Step 2 shows under step 1 with the api's numbers: demand 4, then 8 from Uke 2 (Story 9.4).
    const reveal = (await after.json()).reveal;
    expect(reveal.heading).toBe("Kundene bestilte 4, så 8. Etter det endret de seg aldri.");
    expect(reveal.weeks.map((w: { demand: number; order: number }) => [w.demand, w.order])).toEqual([
      [4, 4],
      [8, 4],
    ]);
    const shown = page.locator("[data-debrief-reveal]");
    await expect(shown.getByRole("heading", { level: 2 })).toHaveAccessibleName(`${copy.stepOf(2, 5)}: ${reveal.heading}`);
    await expect(shown.locator("tr[data-row=demand] td")).toHaveText(["4", "8"]);
    const again = await me.context.request.post(`/api/debriefs/${debrief.id}/explanation`, {
      data: { text: "Noe annet." },
      headers: CSRF,
    });
    expect(again.status()).toBe(409);
    await page.close();
  } finally {
    await me.context.close();
  }
});

test("sent already from another device: the stored Explanation shows, and the draft is dropped", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await stepOne(page, "exists");
  await page.goto(`/debrief/${SESSION}`);
  await field(page).fill(TEXT);
  await sendButton(page).click();
  const sent = page.locator("[data-explanation-sent]");
  await expect(sent.getByText("Fra den andre enheten.", { exact: true })).toBeVisible();
  await expect(sent.getByRole("status")).toHaveText(words.exists);
  await page.reload();
  await expect(sent.getByText("Fra den andre enheten.", { exact: true })).toBeVisible();
  await expect(field(page)).toHaveCount(0);
  await stub.unroute();
});

test("a failed read of the step says so and can be tried again", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await stepOne(page, "saved", true);
  await page.goto(`/debrief/${SESSION}`);
  const failed = page.locator("[data-step-failed]");
  await expect(failed.getByRole("alert")).toHaveText(words.loadFailed);
  await page.unroute(`**/api/debriefs/${DEBRIEF}/net-inventory`);
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) => route.fulfill({ json: { weeks: WEEKS } }));
  await failed.getByRole("button", { name: nb.system.retry }).click();
  await expect(page.locator("svg[data-chart=net-over-game]")).toBeVisible();
  await expect(failed).toHaveCount(0);
  await stub.unroute();
});
