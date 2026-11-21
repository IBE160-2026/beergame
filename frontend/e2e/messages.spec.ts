import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { latestMail, nextMail } from "./support/auth";
import { expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** The Meldingsskjema (Story 7.9, FR-40, FR-72, UX-DR46, NFR-6) on the local stack: opened from the
 * Oversikt header (the whole Class session), Spillinnsikt's «Melding» (the Class game) and a
 * Seat's «Melding» (one Student), each titled with its recipient; «Send Melding» waits for text,
 * a send reaches each Student by e-mail, its result takes focus, Back returns where it was opened,
 * a failed send keeps the text and its retry never sends twice. What the api stores and refuses
 * is `backend/tests/messaging/test_messages.py`. */
const copy = nb.messages;
const CSRF = { "X-Requested-With": "olspillet" };

async function write(page: Page, text: string) {
  const main = page.getByRole("main");
  const send = main.getByRole("button", { name: copy.send });
  await expect(send).toHaveAttribute("aria-disabled", "true");
  await main.getByRole("textbox", { name: copy.field }).fill(text);
  await expect(send).not.toHaveAttribute("aria-disabled");
  return send;
}

test("a Message goes from the Oversikt, Spillinnsikt and a Seat to its Students, once", async ({ browser, lecturerSession }) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students as [(typeof game.students)[number], (typeof game.students)[number]];
  const overview = `/klasseokter/${game.sessionId}/oversikt`;
  const insight = `${overview}/spill/${game.gameId}`;

  // A Student is refused the staff's form, the same as any outsider (FR-5).
  expect((await first.context.request.get(`/api/class-sessions/${game.sessionId}/messages/form`)).status()).toBe(403);

  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  const main = page.getByRole("main");
  await page.goto(overview);
  await main.getByRole("link", { name: copy.toSession }).click();
  await expect(page).toHaveURL(new RegExp(`/klasseokter/${game.sessionId}/melding$`));
  await expect(main.getByRole("heading", { level: 1, name: /^Melding til alle i Klasseøkt \d+$/ })).toBeVisible();
  await expect(main.getByText(copy.reach(2))).toBeVisible();
  await expect(main.getByText(copy.sentBefore(0))).toBeVisible();
  // Empty: «Send Melding» is unavailable and keeps focus when pressed.
  const send = main.getByRole("button", { name: copy.send });
  await send.focus();
  await send.press("Enter");
  await expect(send).toBeFocused();
  await expect(send).toHaveAttribute("aria-disabled", "true");
  await expectAccessible(page, false);

  const before = await Promise.all([latestMail(page, first.email), latestMail(page, second.email)]);
  await write(page, "Husk ordren denne uken.\nDere er snart ferdige.");
  await send.click();
  const result = main.getByText(copy.sent(2));
  await expect(result).toBeFocused();
  await expect(main.getByText(copy.sentBefore(1))).toBeVisible();
  await expect(main.getByRole("textbox", { name: copy.field })).toHaveCount(0);
  for (const [i, student] of [first, second].entries()) {
    const mail = await nextMail(page, student.email, before[i]!);
    expect(mail.text).toContain("Husk ordren denne uken.\nDere er snart ferdige.");
    expect(mail.text).toContain("/hjem");
  }
  // Browser Back returns to the Oversikt.
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${overview}$`));

  // Spillinnsikt's «Melding»: the whole Class game.
  await page.goto(insight);
  await main.getByRole("link", { name: copy.toGameLabel(1) }).click();
  await expect(main.getByRole("heading", { level: 1, name: "Melding til Spill 1" })).toBeVisible();
  await expect(main.getByText(copy.reach(2))).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${insight}$`));

  // A Seat's «Melding»: one Student, titled with the game.
  await main.getByRole("link", { name: copy.toStudentLabel(first.name) }).click();
  await expect(main.getByRole("heading", { level: 1, name: `Melding til ${first.name}, Spill 1` })).toBeVisible();
  await expect(main.getByText(copy.reach(1))).toBeVisible();
  // The first send is stored, but its answer is lost: the line shows, the text stays, the button
  // stays active, and the retry carries the same key, so nothing is sent twice.
  const path = `**/api/class-sessions/${game.sessionId}/messages`;
  await page.route(path, async (route) => {
    await route.fetch();
    await route.fulfill({ status: 503, body: "" });
  });
  const button = await write(page, "Bare til deg.");
  await button.click();
  await expect(main.getByRole("alert")).toHaveText(nb.system.actionFailed);
  await expect(main.getByRole("textbox", { name: copy.field })).toHaveValue("Bare til deg.");
  await expect(button).not.toHaveAttribute("aria-disabled");
  await page.unroute(path);
  await button.click();
  await expect(main.getByText(copy.sent(1))).toBeFocused();
  await expect(main.getByText(copy.sentBefore(1))).toBeVisible();
  const form = await page.request.get(`/api/class-sessions/${game.sessionId}/messages/form`, {
    params: { game_id: game.gameId, student_id: (await studentId(page, game.gameId, first.name))! },
  });
  expect((await form.json()).sent_before).toBe(1);
  // «Skriv en ny melding» brings the form back, focused on the field.
  await main.getByRole("button", { name: copy.writeAnother }).click();
  await expect(main.getByRole("textbox", { name: copy.field })).toBeFocused();
  await page.context().close();
});

/** The Student's id as Spillinnsikt gives it for the Seat's «Melding». */
async function studentId(page: Page, gameId: string, name: string): Promise<string | null> {
  const answer = await (await page.request.get(`/api/games/${gameId}/insight`, { headers: CSRF })).json();
  return (answer.seats as { name: string | null; user_id: string | null }[]).find((s) => s.name === name)?.user_id ?? null;
}

test("the Meldingsskjema reflows at 320 px and with 200 % text", async ({ browser, lecturerSession }) => {
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  for (const viewport of [VIEWPORTS[0]!, VIEWPORTS[1]!]) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    await page.goto(`/klasseokter/${game.sessionId}/melding?spill=${game.gameId}`);
    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { level: 1, name: "Melding til Spill 1" })).toBeVisible();
    await main.getByRole("textbox", { name: copy.field }).fill("En lang melding ".repeat(20));
    await expectAccessible(page, viewport.phone);
    await page.context().close();
  }
});
