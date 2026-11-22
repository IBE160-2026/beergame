import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame, type LiveStudent, orderByApi } from "./support/live-game";

/** Bounded follow-up questions about the Student's own Game (Story 9.15, FR-45, FR-34, NFR-6,
 * AD-7, AD-17). A real ten-Uke Class game with two Students, each ordering every Uke, so each Seat
 * has moments to point to. Sara asks about her game at 360 px: the mock's hint shows marked
 * «KI-generert, kan ta feil: «…»» with the note, is announced politely and focus stays in the
 * field; at 320 px she asks something outside the game and gets the fixed decline line, no KI
 * words. Ida, at 1440 px, gets no answer (the api's `unanswered`, given here by a fulfilled route):
 * the line says so, her question stays in the field, and step 4 is there under it; then too many
 * questions (the wait shows) and closed (the field gives way to a line), each a fulfilled api
 * answer. axe at each width. The rules, the scrubbing, the limits and the closing are
 * `backend/tests/debrief/test_follow_up.py`. */
const copy = nb.debrief.followUp;
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

function followUpOf(page: Page) {
  return page.locator("[data-debrief-follow-up='open']");
}

test("a Student asks about their game and gets hints, a decline, or no answer", async ({ browser, lecturerSession }) => {
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
    await pastReflection(sara, game.sessionId);
    const idas = await pastReflection(ida, game.sessionId);

    // Sara at 360 px: a question about her game gets a hint, marked as KI text.
    const phone = await sara.context.newPage();
    await phone.setViewportSize({ width: 360, height: 740 });
    await phone.goto(`/debrief/${game.sessionId}`);
    const section = followUpOf(phone);
    await expect(section.getByRole("heading", { name: copy.heading })).toBeVisible();
    const field = section.getByLabel(copy.label);
    await field.fill("Hvorfor bestilte jeg så mye i uke 5?");
    await section.getByRole("button", { name: copy.send }).click();
    const answer = section.locator("[data-follow-up-asked='answered']");
    await expect(answer.locator("[data-ai-generated='true']")).toHaveText(
      /^KI-generert, kan ta feil: «Se på raden for Uke \d+: der bestilte du \d+, og ordren inn var \d+\.»$/,
    );
    await expect(answer).toContainText(nb.debrief.aiNote);
    await expect(answer).toContainText("Hvorfor bestilte jeg så mye i uke 5?");
    // Announced politely; the field is empty again and keeps the focus.
    await expect(section.getByRole("status")).toHaveText(/^KI-generert, kan ta feil: «Se på raden/);
    await expect(field).toHaveValue("");
    await expect(field).toBeFocused();
    await expectAccessible(phone, true);

    // At 320 px: a question outside the game gets the fixed decline line, no KI words.
    await phone.setViewportSize({ width: 320, height: 740 });
    await field.fill("Hva er hovedstaden i Frankrike?");
    await section.getByRole("button", { name: copy.send }).click();
    const declined = section.locator("[data-follow-up-asked='declined']");
    await expect(declined).toContainText(copy.declined);
    await expect(declined.locator("[data-ai-generated]")).toHaveCount(0);
    await expect(section.getByRole("status")).toHaveText(copy.declined);
    await expect(field).toBeFocused();
    await expectAccessible(phone, true);
    // Both stay after a reload, in the order asked.
    await phone.reload();
    await expect(followUpOf(phone).locator("[data-follow-up-asked]")).toHaveCount(2);
    await phone.close();

    // Ida at 1440 px: no answer could be given. The line says so, the question stays in the
    // field, and the Debrief goes on: step 4 is under it.
    const laptop = await ida.context.newPage();
    await laptop.setViewportSize({ width: 1440, height: 900 });
    const route = `**/api/debriefs/${idas.id}/follow-up`;
    // What the api answers next: no answer, then too many questions, then closed (Epic 11's
    // close or the Testfrist) — each a fixed api answer, so no live update races a click.
    let next: "unanswered" | "limited" | "closed" = "unanswered";
    const json = (status: number, body: unknown) => ({ status, contentType: "application/json", body: JSON.stringify(body) });
    await laptop.route(route, (served) => {
      if (served.request().method() === "GET") {
        return next === "closed" ? served.fulfill(json(200, { state: "closed", asked: [] })) : served.fallback();
      }
      if (next === "unanswered") {
        return served.fulfill(json(200, { outcome: "unanswered", question: "Hva skjedde i uke 4?", answer: null, asked_at: null }));
      }
      if (next === "limited") {
        return served.fulfill(
          json(429, { error: { code: "rate_limited", message: "Too many questions.", fields: { retry_after: 120 } } }),
        );
      }
      return served.fulfill(json(409, { error: { code: "follow_up_closed", message: "Closed.", fields: {} } }));
    });
    await laptop.goto(`/debrief/${game.sessionId}`);
    const idaSection = followUpOf(laptop);
    const idaField = idaSection.getByLabel(copy.label);
    await idaField.fill("Hva skjedde i uke 4?");
    await idaSection.getByRole("button", { name: copy.send }).click();
    await expect(idaSection.locator("[data-follow-up-unanswered]")).toHaveText(copy.unanswered);
    await expect(idaField).toHaveValue("Hva skjedde i uke 4?");
    await expect(idaField).toBeFocused();
    await expect(idaSection.locator("[data-follow-up-asked]")).toHaveCount(0);
    await expect(laptop.getByRole("heading", { name: nb.debrief.moments.narration })).toBeVisible();
    await expectAccessible(laptop, false);
    // Too many questions: the wait shows, the question stays.
    next = "limited";
    await idaSection.getByRole("button", { name: copy.send }).click();
    await expect(idaSection.locator("[data-follow-up-limited]")).toHaveText(copy.rateLimited(2));
    await expect(idaField).toHaveValue("Hva skjedde i uke 4?");
    // Closed meanwhile: the field gives way to the line that says so.
    next = "closed";
    await idaSection.getByRole("button", { name: copy.send }).click();
    await expect(laptop.locator("[data-follow-up-closed]")).toHaveText(copy.closed);
    await expect(laptop.getByLabel(copy.label)).toHaveCount(0);
    await laptop.unroute(route);
    await laptop.close();
  } finally {
    await sara.context.close();
    await ida.context.close();
  }
});
