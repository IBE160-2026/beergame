import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";
import { liveClassGame, type LiveStudent, orderByApi } from "./support/live-game";

/** AI narration that only connects computed facts (Story 9.14, FR-34, FR-15, FR-44, AD-7, AD-17).
 * A real ten-Uke Class game with two Students, each ordering every Uke, so each Seat has its own
 * moments. The narration of Sara's Seat is worded by the mock provider (`POST
 * /api/dev/games/{id}/seats/{role}/narrate`, the `llm-batch` job's own code run now); Ida's with the
 * mock failing. Sara's step 4 shows the marked line «KI-generert, kan ta feil: «…»» with its
 * machine-readable marker and the note that it can be wrong; Ida's shows the code text in the same
 * place, unmarked. axe at 360 and 1440 px. And the Faglærer's Bryter on the Klasseøkt. The rules,
 * the validator and the job are `backend/tests/debrief/test_narration.py`. */
const copy = nb.debrief.moments;
const c = nb.sessions.choices;
const CSRF = { "X-Requested-With": "olspillet" };
const ORDERS = [4, 12, 0, 8, 16, 4, 8, 2, 8, 20];

/** The Student's Personal debrief past the reflection questions, through the api. */
async function pastReflection(student: LiveStudent, sessionId: string) {
  const request = student.context.request;
  const debrief = await (await request.post(`/api/me/class-sessions/${sessionId}/debrief`, { headers: CSRF })).json();
  const path = `/api/debriefs/${debrief.id}`;
  expect((await request.post(`${path}/explanation`, { data: { text: "Jeg bestilte mye." }, headers: CSRF })).status()).toBe(201);
  const reflection = await (await request.get(`${path}/reflection`)).json();
  for (const question of reflection.questions as { id: string }[]) {
    const answered = await request.post(`${path}/reflection/${question.id}`, { data: { text: "Svar." }, headers: CSRF });
    expect(answered.status()).toBe(200);
  }
  return debrief as { id: string; role: string };
}

function narrationOf(page: Page) {
  return page.locator("[data-moments-narration]");
}

test("step 4 shows the AI line marked, and the code text when the mock fails", async ({ browser, lecturerSession }) => {
  test.slow(); // two Invitations through the worker, a Class session, a lock and a ten-Uke game
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    debriefMode: "personal",
    gameSettings: { weeks: 10, demand: { kind: "step", start: 4, new_level: 8, change_week: 4 } },
  });
  const [sara, ida] = game.students as [LiveStudent, LiveStudent];
  try {
    for (const [i, order] of ORDERS.entries()) {
      await orderByApi(sara, game.gameId, i + 1, order);
      await orderByApi(ida, game.gameId, i + 1, ORDERS[ORDERS.length - 1 - i]!);
    }
    const saras = await pastReflection(sara, game.sessionId);
    const idas = await pastReflection(ida, game.sessionId);
    const narrate = (role: string, outage: boolean) =>
      sara.context.request.post(`/api/dev/games/${game.gameId}/seats/${role}/narrate?outage=${outage}`, { headers: CSRF });
    expect((await narrate(saras.role, false)).status()).toBe(200);
    expect((await narrate(idas.role, true)).status()).toBe(200);

    // Sara: the AI line, marked by `ai_generated` alone, with the note.
    const phone = await sara.context.newPage();
    await phone.setViewportSize({ width: 360, height: 740 });
    await phone.goto(`/debrief/${game.sessionId}`);
    const line = narrationOf(phone);
    await expect(line.getByRole("heading", { name: copy.narration })).toBeVisible();
    const marked = line.locator("[data-ai-generated='true']");
    await expect(marked).toHaveText(/^KI-generert, kan ta feil: «I Uke \d+ bestilte du .+»$/);
    await expect(line).toContainText(nb.debrief.aiNote);
    // Only the narration is AI text: the moments themselves stay the code's.
    await expect(phone.locator("[data-ai-generated]")).toHaveCount(1);
    await expectAccessible(phone, true);

    // The quiz (FR-46): a wrong answer gets the AI's own-game line under the fixed explanation,
    // marked the same way. Sara finishes the Debrief and answers every question with its first
    // choice through the api; the page then shows that attempt's result.
    const path = `/api/debriefs/${saras.id}`;
    expect((await sara.context.request.post(`${path}/finish`, { headers: CSRF })).status()).toBe(200);
    const quiz = await (await sara.context.request.get(`${path}/quiz`)).json();
    const answers = (quiz.questions as { id: string; choices: { id: string }[] }[]).map((q) => ({
      question_id: q.id,
      choice_id: q.choices[0]!.id,
    }));
    const attempt = await (await sara.context.request.post(`${path}/quiz/attempts`, { data: { answers }, headers: CSRF })).json();
    const wrong = (attempt.results as { correct: boolean; ai_explanation: unknown }[]).filter((r) => !r.correct);
    expect(wrong.length).toBeGreaterThan(0);
    for (const each of wrong) expect(each.ai_explanation).toMatchObject({ ai_generated: true });
    await phone.reload();
    const quizLine = phone.locator("[data-quiz-ai-explanation]");
    await expect(quizLine).toHaveCount(wrong.length);
    await expect(quizLine.first().locator("[data-ai-generated='true']")).toHaveText(/^KI-generert, kan ta feil: «.+»$/);
    await expect(quizLine.first()).toContainText(nb.debrief.aiNote);
    await phone.close();

    // Ida: the mock failed, so the same place holds the code text, without prefix or marker.
    const laptop = await ida.context.newPage();
    await laptop.setViewportSize({ width: 1440, height: 900 });
    await laptop.goto(`/debrief/${game.sessionId}`);
    const plain = narrationOf(laptop);
    await expect(plain.getByRole("heading", { name: copy.narration })).toBeVisible();
    await expect(plain.locator("p").first()).toHaveText(/^I Uke \d+ bestilte du /);
    await expect(plain).not.toContainText(nb.debrief.aiPrefix);
    await expect(plain).not.toContainText(nb.debrief.aiNote);
    await expect(laptop.locator("[data-ai-generated]")).toHaveCount(0);
    await expectAccessible(laptop, false);
    await laptop.close();
  } finally {
    await sara.context.close();
    await ida.context.close();
  }
});

test("the Faglærer switches the Debrief's AI text off; it takes effect on save", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  const id = (await created.json()).id as string;
  await lecturer.goto(`/klasseokter/${id}`);
  const group = lecturer.getByRole("group", { name: c.debriefAiText, exact: true });
  const toggle = group.getByRole("switch", { name: c.debriefAiText });
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(toggle).toHaveAccessibleDescription(c.debriefAiTextOnHelp);
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(toggle).toHaveAccessibleDescription(c.debriefAiTextOffHelp);
  expect((await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).debrief_ai_text).toBe(true);
  await lecturer.getByRole("button", { name: nb.sessions.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
  expect((await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).debrief_ai_text).toBe(false);
  await lecturer.reload();
  await expect(lecturer.getByRole("group", { name: c.debriefAiText, exact: true }).getByRole("switch")).toHaveAttribute(
    "aria-checked",
    "false",
  );
});
