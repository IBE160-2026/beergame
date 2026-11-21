import { expect, type Locator, type Page } from "@playwright/test";

import result from "../src/modules/games/fixtures/result-classic.json";
import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { BILL, SUMMARY } from "./support/bill";
import { expectAccessible, expectReflow, test } from "./support/classes";
import { MOMENTS } from "./support/moments";
import { EXPLANATION, KEY, QUESTIONS, stubQuiz } from "./support/quiz";
import { QUESTIONS as REFLECTION } from "./support/reflection";
import { REVEAL } from "./support/reveal";

/** Step 5, the Debrief quiz (Story 9.9, FR-46, NFR-6, UX-DR37, UX-DR76). From stand-in answers of
 * a finished Debrief and a quiz stub that scores by the answer key as the api does: the questions as
 * Quizvalg rows with the placeholder note; a wrong attempt sent by keyboard alone, its summary
 * focused, the wrong row «Ditt svar, ikke riktig», the right one «Riktig» and the explanation;
 * «Prøv igjen» with the questions in a new order; a pass. At 320, 360 and 1440 px with axe. The
 * api's scoring, storage and refusals are `backend/tests/debrief/test_quiz.py`. */
const copy = nb.debrief.quiz;
const SESSION = "01a1aaaa-0000-7000-8000-000000000099";
const DEBRIEF = "01a1aaaa-0000-7000-8000-0000000009d9";
const GAME = "01a1aaaa-0000-7000-8000-0000000009a9";
const OPENED = { id: DEBRIEF, class_session_id: SESSION, game_id: GAME, game_number: 17, role: "wholesaler", step: 1 };
const SENT = { text: "Restordren vokste, så jeg bestilte mye.", length: 39, saved_at: "2026-11-21T12:00:00Z" };
const ANSWER = { text: "Svar.", length: 5, saved_at: "2026-11-21T12:10:00Z" };
const STEP = { debrief_id: DEBRIEF, reveal: null, chain: null, moments: null, bill: null };

/** A finished Debrief whose step 5 is the stubbed quiz. */
async function atTheQuiz(page: Page, options: { refuse?: string | null } = {}) {
  await page.route(`**/api/me/class-sessions/${SESSION}/debrief`, (route) => route.fulfill({ json: OPENED }));
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) =>
    route.fulfill({ json: { weeks: REVEAL.weeks.map((w) => ({ week: w.week, net_inventory: 12 - w.week })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/explanation`, (route) => route.fulfill({ json: { explanation: SENT } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/2`, (route) => route.fulfill({ json: { ...STEP, step: 2, reveal: REVEAL } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/3`, (route) => route.fulfill({ json: { ...STEP, step: 3 } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/reflection`, (route) =>
    route.fulfill({ json: { version: 1, questions: REFLECTION.map((q) => ({ ...q, answer: ANSWER })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/4`, (route) =>
    route.fulfill({ json: { ...STEP, step: 4, moments: MOMENTS, bill: BILL } }),
  );
  await page.route(`**/api/me/games/${GAME}/result`, (route) => route.fulfill({ json: result }));
  await page.route(`**/api/debriefs/${DEBRIEF}/summary`, (route) => route.fulfill({ json: { summary: SUMMARY } }));
  const stub = await stubQuiz(page, DEBRIEF, { refuse: options.refuse ?? null });
  return { ...stub, unroute: () => page.unrouteAll({ behavior: "ignoreErrors" }) };
}

function quiz(page: Page): Locator {
  return page.locator("[data-debrief-quiz]");
}

/** Chooses `choice` in the question group `prompt` by keyboard: focus the group's checked or first
 * radio, then the arrow keys to the choice (a native radio group). */
async function choose(page: Page, prompt: string, choice: string) {
  const group = quiz(page).getByRole("group", { name: prompt });
  const radios = group.getByRole("radio");
  await radios.first().focus();
  const texts = await group.locator("[data-quiz-option]").evaluateAll((rows) => rows.map((row) => row.getAttribute("data-quiz-option")));
  // Focusing an unchecked group's first radio does not check it; Space does.
  await page.keyboard.press("Space");
  for (let i = 0; i < texts.indexOf(choice); i++) await page.keyboard.press("ArrowDown");
  await expect(group.locator(`[data-quiz-option="${choice}"] input`)).toBeChecked();
}

const prompt = (id: string) => QUESTIONS.find((q) => q.id === id)!.prompt;

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("a wrong attempt is explained, «Prøv igjen» reshuffles, every answer right passes", async ({ page }) => {
      await loginByApi(page, "student");
      const stub = await atTheQuiz(page);
      await page.goto(`/debrief/${SESSION}#debrief-quiz`);
      const step = quiz(page);
      await expect(step.getByRole("heading", { level: 2, name: /Debrief-quiz/ })).toBeVisible();
      await expect(step.locator("[data-quiz-placeholder]")).toHaveText(copy.placeholder);
      await expect(step.getByRole("group")).toHaveCount(3);
      await expect(step.getByRole("radio")).toHaveCount(9);

      // By keyboard alone: −13 for Posisjon, the right choice for the rest, then Enter.
      await choose(page, prompt("posisjon"), "netto");
      await choose(page, prompt("forsinkelse"), KEY.forsinkelse!);
      await choose(page, prompt("forsterkning"), KEY.forsterkning!);
      await step.getByRole("button", { name: copy.send }).focus();
      await page.keyboard.press("Enter");

      const summary = step.locator("[data-quiz-summary]");
      await expect(summary).toHaveText(`${copy.result(1, 2, 3)} ${copy.retryHint}`);
      await expect(summary).toBeFocused();
      const posisjon = step.getByRole("group", { name: prompt("posisjon") });
      await expect(posisjon.locator("[data-quiz-mark=wrong]")).toContainText(["−13", nb.quizChoice.wrong].join(""));
      await expect(posisjon.locator("[data-quiz-mark=right]")).toContainText(nb.quizChoice.right);
      await expect(posisjon.locator("[data-quiz-explanation]")).toHaveText(EXPLANATION);
      await expect(step.locator("[data-quiz-explanation]")).toHaveCount(1);
      await expectAccessible(page, viewport.phone);

      // «Prøv igjen»: a new attempt, its questions in a new order, focus on it.
      await step.getByRole("button", { name: copy.retry }).click();
      const form = step.locator("[data-quiz-form]");
      await expect(form).toHaveAttribute("data-quiz-form", "2");
      await expect(form.getByRole("heading", { level: 3 })).toBeFocused();
      await expect(form.locator("legend")).toHaveText(
        [...QUESTIONS].reverse().map((q, i) => `${copy.questionOf(i + 1, 3)}${q.prompt}`),
      );
      await expect(form.getByRole("radio", { checked: true })).toHaveCount(0);
      for (const question of QUESTIONS) await choose(page, question.prompt, KEY[question.id]!);
      await form.getByRole("button", { name: copy.send }).click();
      await expect(summary).toHaveText(`${copy.result(2, 3, 3)} ${copy.passed(2)}`);
      await expect(summary).toBeFocused();
      await expect(step.locator("[data-quiz-passed]")).toBeVisible();
      await expect(step.getByRole("button", { name: copy.retry })).toHaveCount(0);
      await expect(step.locator("[data-quiz-explanation]")).toHaveCount(0);
      await expectReflow(page, viewport.phone);
      expect(stub.posts.map((answers) => answers.map((a) => a.question_id))).toEqual([
        QUESTIONS.map((q) => q.id),
        [...QUESTIONS].reverse().map((q) => q.id),
      ]);
      await stub.unroute();
    });
  });
}

test("nothing is sent while a question has no choice", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await atTheQuiz(page);
  await page.goto(`/debrief/${SESSION}`);
  await choose(page, prompt("posisjon"), KEY.posisjon!);
  await quiz(page).getByRole("button", { name: copy.send }).click();
  await expect(quiz(page)).toContainText(copy.unanswered);
  expect(stub.posts).toEqual([]);
  await stub.unroute();
});

test("an attempt after the Testfrist is refused with the reason beside the button", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await atTheQuiz(page, { refuse: "test_deadline_passed" });
  await page.goto(`/debrief/${SESSION}`);
  for (const question of QUESTIONS) await choose(page, question.prompt, KEY[question.id]!);
  await quiz(page).getByRole("button", { name: copy.send }).click();
  await expect(quiz(page)).toContainText(copy.deadlinePassed);
  await expect(quiz(page).locator("[data-quiz-summary]")).toHaveCount(0);
  expect(stub.posts).toHaveLength(1);
  await stub.unroute();
});
