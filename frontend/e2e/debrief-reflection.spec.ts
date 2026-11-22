import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, test } from "./support/classes";
import { QUESTIONS } from "./support/reflection";
import { REVEAL } from "./support/reveal";

/** The reflection questions between steps 3 and 4 (Story 9.6, FR-43, FR-45, FR-73, NFR-6,
 * AD-10). From stand-in answers of the Debrief endpoints with the Explanation sent: one question
 * at a time in the order feelings, evidence, structure, answered by keyboard alone, the answered
 * ones read-only above, focus on the next question, a draft kept over a reload, a failed save
 * keeping the text, at 320, 360 and 1440 px with axe. The api's order, storage and privacy are
 * `backend/tests/debrief/test_explanation.py`. */
const copy = nb.debrief.reflection;
const SESSION = "01a1aaaa-0000-7000-8000-000000000096";
const DEBRIEF = "01a1aaaa-0000-7000-8000-0000000009d6";
const OPENED = {
  id: DEBRIEF,
  class_session_id: SESSION,
  game_id: "01a1aaaa-0000-7000-8000-0000000009a6",
  game_number: 17,
  role: "wholesaler",
  step: 1,
};
const SENT = { text: "Restordren vokste, så jeg bestilte mye.", length: 39, saved_at: "2026-11-21T12:00:00Z" };
const ANSWERS = ["Stressende, jeg så bare restordren.", "Fabrikken svingte mest og sist.", "Forsinkelsene i kjeden."];

type Save = "saved" | "failed" | "elsewhere";

/** The open Debrief past step 3; the reflection endpoints keep the answers the page sends. */
async function reflecting(page: Page, { save = "saved" as Save } = {}) {
  const stored = new Map<string, { text: string; length: number; saved_at: string }>();
  const posts: string[] = [];
  const error = (status: number, code: string) => ({ status, json: { error: { code, message: "x", fields: {} } } });
  const read = () => ({ version: 1, questions: QUESTIONS.map((q) => ({ ...q, answer: stored.get(q.id) ?? null })) });
  await page.route(`**/api/me/class-sessions/${SESSION}/debrief`, (route) => route.fulfill({ json: OPENED }));
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) =>
    route.fulfill({ json: { weeks: REVEAL.weeks.map((w) => ({ week: w.week, net_inventory: 12 - w.week })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/explanation`, (route) => route.fulfill({ json: { explanation: SENT } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/2`, (route) =>
    route.fulfill({ json: { debrief_id: DEBRIEF, step: 2, reveal: REVEAL, chain: null } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/3`, (route) =>
    route.fulfill({ json: { debrief_id: DEBRIEF, step: 3, reveal: null, chain: null } }),
  );
  // Step 4 follows the last answer (Story 9.7, `debrief-moments.spec.ts`): nothing to show here.
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/4`, (route) =>
    route.fulfill({ json: { debrief_id: DEBRIEF, step: 4, reveal: null, chain: null, moments: null } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/reflection`, (route) => route.fulfill({ json: read() }));
  await page.route(`**/api/debriefs/${DEBRIEF}/reflection/*`, (route) => {
    const id = route.request().url().split("/").pop()!;
    const text = (route.request().postDataJSON() as { text: string }).text;
    posts.push(id);
    if (save === "failed") return route.fulfill(error(500, "internal_error"));
    if (save === "elsewhere" && id === "feelings") {
      // Another device answered the first question already: the api answers the stored one.
      const first = { text: "Fra den andre enheten.", length: 22, saved_at: "2026-11-21T11:00:00Z" };
      stored.set(id, first);
      return route.fulfill({ json: { ...QUESTIONS[0], answer: first } });
    }
    const answer = { text, length: text.length, saved_at: "2026-11-21T12:30:00Z" };
    stored.set(id, answer);
    return route.fulfill({ json: { ...QUESTIONS.find((q) => q.id === id)!, answer } });
  });
  return { posts, unroute: () => page.unrouteAll({ behavior: "ignoreErrors" }) };
}

function section(page: Page) {
  return page.locator("[data-debrief-reflection]");
}

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("one question at a time, in order, answered by keyboard alone", async ({ page }) => {
      await loginByApi(page, "student");
      const stub = await reflecting(page);
      await page.goto(`/debrief/${SESSION}`);
      const step = section(page);
      await expect(step.getByRole("heading", { level: 2, name: copy.heading })).toBeVisible();
      await expect(step.locator("form[data-reflection-question]")).toHaveCount(1);
      await expect(step.locator("form")).toHaveAttribute("data-reflection-kind", "feelings");
      await expect(step.getByRole("heading", { level: 3 })).toHaveText(copy.counter(1, 3));
      const next = step.getByRole("button", { name: copy.next });
      await expect(next).toHaveAttribute("aria-disabled", "true");
      await expectAccessible(page, viewport.phone);

      for (const [i, q] of QUESTIONS.entries()) {
        const field = step.getByRole("textbox", { name: q.prompt });
        await field.focus();
        await page.keyboard.type(ANSWERS[i]!);
        await page.keyboard.press("Tab");
        await expect(next).toBeFocused();
        await page.keyboard.press("Enter");
        await expect(step.locator(`[data-reflection-answered=${q.id}]`)).toContainText(ANSWERS[i]!);
        if (i < QUESTIONS.length - 1) {
          // Focus on the next question's heading; its kind follows the order.
          const heading = step.getByRole("heading", { level: 3 });
          await expect(heading).toHaveText(copy.counter(i + 2, 3));
          await expect(heading).toBeFocused();
          await expect(step.locator("form")).toHaveAttribute("data-reflection-kind", QUESTIONS[i + 1]!.kind);
        }
      }
      // The structure question shows its hint; after it, the closing line takes focus.
      await expect(step.locator("[data-reflection-done]")).toBeFocused();
      await expect(step.locator("[data-reflection-done]")).toHaveText(copy.done);
      await expect(step.locator("form")).toHaveCount(0);
      expect(stub.posts).toEqual(["feelings", "evidence", "structure"]);
      await expectReflow(page, viewport.phone);
      await stub.unroute();
    });
  });
}

test("an unsent answer is kept over a reload; a failed save keeps the text", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await reflecting(page, { save: "failed" });
  await page.goto(`/debrief/${SESSION}`);
  const step = section(page);
  const field = step.getByRole("textbox", { name: QUESTIONS[0].prompt });
  await field.fill(ANSWERS[0]!);
  await page.reload();
  await expect(field).toHaveValue(ANSWERS[0]!);

  await step.getByRole("button", { name: copy.next }).click();
  await expect(step.getByRole("alert")).toHaveText(copy.failed);
  await expect(field).toHaveValue(ANSWERS[0]!);
  await expect(step.locator("[data-reflection-answered]")).toHaveCount(0);
  expect(stub.posts).toEqual(["feelings"]);
  await stub.unroute();
});

test("a question answered on another device first: its stored answer stays, and the page says so", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await reflecting(page, { save: "elsewhere" });
  await page.goto(`/debrief/${SESSION}`);
  const step = section(page);
  await step.getByRole("textbox", { name: QUESTIONS[0].prompt }).fill("Herfra.");
  await step.getByRole("button", { name: copy.next }).click();
  await expect(step.locator("[data-reflection-answered=feelings]")).toContainText("Fra den andre enheten.");
  await expect(step.getByText(copy.answeredElsewhere)).toBeVisible();
  await expect(step.locator("[data-reflection-answered=feelings]")).not.toContainText("Herfra.");
  expect(await page.evaluate(() => Object.keys(localStorage).filter((k) => k.includes("debrief-reflection")))).toEqual([]);
  await expect(step.getByRole("heading", { level: 3 })).toHaveText(copy.counter(2, 3));
  await expect(step.getByRole("textbox", { name: QUESTIONS[1].prompt })).toHaveValue("");
  await stub.unroute();
});
