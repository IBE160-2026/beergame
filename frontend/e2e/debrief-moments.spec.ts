import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, test } from "./support/classes";
import { MOMENTS, MOSTLY_AI } from "./support/moments";
import { QUESTIONS } from "./support/reflection";
import { REVEAL } from "./support/reveal";

/** Debrief step 4, the own moments (Story 9.7, FR-41, FR-43, FR-44, FR-73, NFR-6, UX-DR31, AD-10).
 * From stand-in answers of the Debrief endpoints with the Explanation sent and every reflection
 * question answered: the code-rendered heading, three moments paged by keyboard alone with focus
 * on the new moment's heading, «Dette så du» as the Graf over tabell at that Uke, «Dette regnet
 * du», «Dette kostet det senere», «Dette så de andre i Uke N» and the own Explanation beside them,
 * at 320, 360 and 1440 px with axe; the mostly-AI line; no step 4 before the last answer. The
 * api's rendering, numbers and privacy are `backend/tests/debrief/test_explanation.py`. */
const copy = nb.debrief.moments;
const SESSION = "01a1aaaa-0000-7000-8000-000000000097";
const DEBRIEF = "01a1aaaa-0000-7000-8000-0000000009d7";
const OPENED = {
  id: DEBRIEF,
  class_session_id: SESSION,
  game_id: "01a1aaaa-0000-7000-8000-0000000009a7",
  game_number: 17,
  role: "wholesaler",
  step: 1,
};
const SENT = { text: "Restordren vokste, så jeg bestilte mye.", length: 39, saved_at: "2026-11-21T12:00:00Z" };
const ANSWER = { text: "Svar.", length: 5, saved_at: "2026-11-21T12:10:00Z" };

/** The open Debrief past the reflection questions (all answered unless `unanswered`). */
async function atStepFour(page: Page, { moments = MOMENTS as object, unanswered = false } = {}) {
  const reads: string[] = [];
  const questions = QUESTIONS.map((q, i) => ({ ...q, answer: unanswered && i === 2 ? null : ANSWER }));
  await page.route(`**/api/me/class-sessions/${SESSION}/debrief`, (route) => route.fulfill({ json: OPENED }));
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) =>
    route.fulfill({ json: { weeks: REVEAL.weeks.map((w) => ({ week: w.week, net_inventory: 12 - w.week })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/explanation`, (route) => route.fulfill({ json: { explanation: SENT } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/2`, (route) =>
    route.fulfill({ json: { debrief_id: DEBRIEF, step: 2, reveal: REVEAL, chain: null, moments: null } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/3`, (route) =>
    route.fulfill({ json: { debrief_id: DEBRIEF, step: 3, reveal: null, chain: null, moments: null } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/reflection`, (route) => route.fulfill({ json: { version: 1, questions } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/4`, (route) => {
    reads.push(route.request().url());
    return route.fulfill({ json: { debrief_id: DEBRIEF, step: 4, reveal: null, chain: null, moments } });
  });
  return { reads, unroute: () => page.unrouteAll({ behavior: "ignoreErrors" }) };
}

function section(page: Page) {
  return page.locator("[data-debrief-moments]");
}

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("three own moments beside the Explanation, paged by keyboard alone", async ({ page }) => {
      await loginByApi(page, "student");
      const stub = await atStepFour(page);
      await page.goto(`/debrief/${SESSION}`);
      const step = section(page);
      await expect(step.getByRole("heading", { level: 2 })).toContainText(MOMENTS.heading.text);
      // Code text: no «KI-generert» prefix anywhere in the step.
      await expect(step).not.toContainText(nb.debrief.aiPrefix);
      const heading = step.getByRole("heading", { level: 3 });
      const [first, second, third] = MOMENTS.moments;
      await expect(heading).toHaveText(`${copy.counter(1, 3)}: ${first!.heading.text}`);
      await expect(step.getByRole("heading", { level: 4, name: copy.saw })).toBeVisible();
      await expect(step.getByRole("region", { name: copy.region(11) })).toBeVisible();
      await expect(step.locator("[data-moment-reckoning]")).toHaveText(first!.reckoning.text);
      await expect(step.locator("[data-moment-later]")).toHaveText(first!.later.text);
      await expect(step.locator("[data-moment-pattern]")).toHaveText(first!.patterns.map((p) => p.text));
      const others = step.getByRole("table", { name: copy.others(11) });
      await expect(others.getByRole("row")).toHaveCount(4);
      await expect(others.getByRole("row", { name: /Detaljist/ })).toContainText("12");
      await expect(step.locator("[data-moment-explanation]")).toContainText(SENT.text);
      const previous = step.getByRole("button", { name: copy.previous });
      const next = step.getByRole("button", { name: copy.next });
      await expect(previous).toHaveAttribute("aria-disabled", "true");
      await expectAccessible(page, viewport.phone);

      await next.focus();
      await page.keyboard.press("Enter");
      await expect(heading).toHaveText(`${copy.counter(2, 3)}: ${second!.heading.text}`);
      await expect(heading).toBeFocused();
      await expect(step.locator("[data-moment-later]")).toHaveText(second!.later.text);
      await expect(step.getByRole("table", { name: copy.others(12) })).toBeVisible();
      // From the heading, Tab reaches «Forrige» and then «Neste».
      await page.keyboard.press("Tab");
      await expect(previous).toBeFocused();
      await page.keyboard.press("Tab");
      await expect(next).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(heading).toHaveText(`${copy.counter(3, 3)}: ${third!.heading.text}`);
      await expect(heading).toBeFocused();
      await expect(step.locator("[data-moment-later]")).toHaveText(third!.later.text);
      await expect(next).toHaveAttribute("aria-disabled", "true");
      await previous.focus();
      await page.keyboard.press("Enter");
      await expect(heading).toHaveText(`${copy.counter(2, 3)}: ${second!.heading.text}`);
      await expect(heading).toBeFocused();
      await expectReflow(page, viewport.phone);
      await stub.unroute();
    });
  });
}

test("a game played mostly by AI players says so and shows no moments", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await atStepFour(page, { moments: MOSTLY_AI });
  await page.goto(`/debrief/${SESSION}`);
  const step = section(page);
  await expect(step.getByRole("heading", { level: 2 })).toContainText(copy.heading);
  await expect(step.locator("[data-moments-mostly-ai]")).toHaveText(copy.mostlyAi);
  await expect(step.locator("[data-moment]")).toHaveCount(0);
  await expect(page.locator("[data-debrief-reveal]")).toBeVisible();
  await expectAccessible(page, false);
  await stub.unroute();
});

test("step 4 waits for the last reflection answer", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await atStepFour(page, { unanswered: true });
  await page.goto(`/debrief/${SESSION}`);
  await expect(page.locator("form[data-reflection-question=structure]")).toBeVisible();
  await expect(section(page)).toHaveCount(0);
  expect(stub.reads).toEqual([]);
  await stub.unroute();
});
