import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** The Klasseøkt's «Debrief-quiz» block (Story 9.10, FR-46, UX-DR12, AD-12), on the local stack:
 * a fresh Lecturer's fresh Class session shows the latest quiz (it is not locked yet) with each
 * answer key and a Bryter per question; «Lagre quizvalg» stores the change. The rules (the last
 * question, the Test deadline, the Assistant lecturer, the audit row and the Students' notices)
 * are pinned by `backend/tests/debrief/test_quiz_exclusions.py`; the read-only states here answer
 * through a route. */
const copy = nb.debrief.quizExclusions;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

const block = (page: Page) => page.locator("[data-quiz-exclusions]");

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test(`an owner takes a question out and saves it at ${viewport.name}`, async ({ page, browser }) => {
    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    });
    const lecturer = await freshLecturer(page, browser);
    const id = await newSession(lecturer);
    const stored = await (await lecturer.request.get(`/api/class-sessions/${id}/debrief-quiz`)).json();
    await lecturer.goto(`/klasseokter/${id}`);

    const quiz = block(lecturer);
    await expect(quiz.getByRole("heading", { level: 2, name: copy.heading })).toBeVisible();
    await expect(quiz).toContainText(copy.latest);
    await expect(quiz.locator("[data-quiz-question]")).toHaveCount(stored.questions.length);
    const switches = quiz.getByRole("switch");
    await expect(switches).toHaveCount(stored.questions.length);
    const first = switches.first();
    await expect(first).toHaveAccessibleDescription(copy.help);
    await expect(first).toHaveAccessibleName(`${stored.questions[0].prompt} ${copy.included}`);
    await expect(quiz.locator("[data-quiz-answer]").first()).toHaveText(/^Riktig svar: /);
    await expectAccessible(lecturer, viewport.phone);

    // Switched, it applies only on «Lagre quizvalg».
    await first.click();
    await expect(first).toHaveAttribute("aria-checked", "false");
    await expect(first).toContainText(copy.excluded);
    let now = await (await lecturer.request.get(`/api/class-sessions/${id}/debrief-quiz`)).json();
    expect(now.questions[0].excluded).toBe(false);
    await quiz.getByRole("button", { name: copy.save }).click();
    await expect(quiz.getByRole("status")).toHaveText(copy.saved);
    now = await (await lecturer.request.get(`/api/class-sessions/${id}/debrief-quiz`)).json();
    expect(now.questions.map((q: { excluded: boolean }) => q.excluded)).toEqual(
      stored.questions.map((_: unknown, i: number) => i === 0),
    );

    if (!viewport.phone) {
      // Every question out: refused, with the reason beside the button.
      for (const each of await switches.all())
        if ((await each.getAttribute("aria-checked")) === "true") await each.click();
      await quiz.getByRole("button", { name: copy.save }).click();
      await expect(quiz.getByRole("alert")).toHaveText(copy.lastQuestion);
    }
  });
}

test("an Assistant lecturer, or anyone after the Test deadline, reads the choices with no Bryter", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  for (const [changes, line] of [
    [{ can_exclude: false }, copy.assistant],
    [{ open: false }, copy.closed],
  ] as const) {
    await lecturer.route(`**/api/class-sessions/${id}/debrief-quiz`, async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.questions[1].excluded = true;
      await route.fulfill({ response, json: { ...json, ...changes } });
    });
    await lecturer.goto(`/klasseokter/${id}`);
    const quiz = block(lecturer);
    await expect(quiz).toContainText(line);
    await expect(quiz.getByRole("switch")).toHaveCount(0);
    await expect(quiz.getByRole("button", { name: copy.save })).toHaveCount(0);
    await expect(quiz.locator("[data-quiz-state]").nth(0)).toHaveText(copy.included);
    await expect(quiz.locator("[data-quiz-state]").nth(1)).toHaveText(copy.excluded);
    await lecturer.unrouteAll({ behavior: "ignoreErrors" });
  }
});
