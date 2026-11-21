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
    const mail = await nextMail(page, student.email, before[i]!, "Husk ordren denne uken.");
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

/** Story 7.10: a Message sent while the Student has Hjem open, by the api so no live update races
 * a click; the Student's page reads it from `user:<id>`. */
async function sendByApi(page: Page, sessionId: string, text: string, to: { student_id?: string } = {}) {
  const sent = await page.request.post(`/api/class-sessions/${sessionId}/messages`, {
    data: { key: crypto.randomUUID(), text, ...to },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
}

test("a Student reads Messages on Hjem as they arrive, and the staff read them in «Meldinger»", async ({ browser, lecturerSession }) => {
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based", width: 320 });
  const [student] = game.students as [(typeof game.students)[number]];
  const lecturer = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);

  // Hjem, before any Message: no «Meldinger» section.
  const hjem = await student.context.newPage();
  await hjem.goto("/hjem");
  const home = hjem.getByRole("main");
  await expect(home.getByRole("heading", { level: 3 }).first()).toBeVisible();
  await expect(home.getByRole("heading", { name: nb.messages.mine.title })).toHaveCount(0);
  const focused = home.locator("a, button").first();
  await focused.focus();

  // Two Messages arrive while Hjem is open: listed newest first, announced, focus kept.
  const markup = "<b>Hei</b> & velkommen\nhttps://example.com/<script>";
  await sendByApi(lecturer, game.sessionId, markup);
  const meldinger = home.getByRole("region", { name: nb.messages.mine.title });
  await expect(meldinger.getByRole("listitem")).toHaveCount(1);
  const said = hjem.locator("[data-my-messages-said]");
  await expect(said).toHaveText(/^Ny melding fra .+\.\s?$/);
  await expect(focused).toBeFocused();
  const studentId = (await (await lecturer.request.get(`/api/games/${game.gameId}/insight`, { headers: CSRF })).json()).seats.find(
    (s: { name: string | null }) => s.name === student.name,
  ).user_id as string;
  await sendByApi(lecturer, game.sessionId, "Bare til deg.", { student_id: studentId });
  await expect(meldinger.getByRole("listitem")).toHaveCount(2);
  await expect(focused).toBeFocused();
  const items = meldinger.getByRole("listitem");
  await expect(items.nth(0)).toContainText("Bare til deg.");
  // Plain text: the markup is shown as written, its line break kept, and nothing is a link.
  const text = items.nth(1).locator("p").last();
  await expect(text).toHaveText(markup);
  expect(await text.evaluate((p) => (p as HTMLElement).innerText)).toContain("velkommen\nhttps://");
  await expect(items.nth(1).locator("b, script, a")).toHaveCount(0);
  await expect(meldinger.getByRole("button")).toHaveCount(0);
  await expect(meldinger.getByRole("textbox")).toHaveCount(0);
  await expectAccessible(hjem, true);
  // And with 200 % text at 1280 px.
  const larger = await student.context.newPage();
  await larger.setViewportSize({ width: 1280, height: 800 });
  await larger.addInitScript(() => {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = "html { font-size: 200% !important; }";
      document.head.appendChild(style);
    });
  });
  await larger.goto("/hjem");
  await expect(larger.getByRole("region", { name: nb.messages.mine.title }).getByRole("listitem")).toHaveCount(2);
  await expectAccessible(larger, false);

  // The staff's «Meldinger», from the Oversikt header: newest first, with a way back to the form.
  const main = lecturer.getByRole("main");
  await lecturer.goto(`/klasseokter/${game.sessionId}/oversikt`);
  await main.getByRole("link", { name: nb.messages.sentList.link, exact: true }).click();
  await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${game.sessionId}/meldinger$`));
  await expect(main.getByRole("heading", { level: 1, name: nb.messages.sentList.title })).toBeVisible();
  const sent = main.locator("[data-sent-messages] > li");
  await expect(sent).toHaveCount(2);
  await expect(sent.nth(0).getByRole("heading", { level: 2 })).toHaveText(`Til ${student.name}`);
  await expect(sent.nth(0)).toContainText(nb.messages.sentList.reach(1));
  await expect(sent.nth(1).getByRole("heading", { level: 2 })).toHaveText(/^Til alle i Klasseøkt \d+$/);
  await expectAccessible(lecturer, false);
  await sent.nth(0).getByRole("link", { name: `Skriv ny melding til ${student.name}` }).click();
  await expect(main.getByRole("heading", { level: 1, name: `Melding til ${student.name}` })).toBeVisible();
  await main.getByRole("link", { name: nb.messages.sentList.fromForm }).click();
  await expect(lecturer).toHaveURL(new RegExp(`/meldinger$`));
  await lecturer.context().close();
});

test("«Meldinger» reflows at 320 px and with 200 % text", async ({ browser, lecturerSession }) => {
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  const setup = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await sendByApi(setup, game.sessionId, "En lang melding ".repeat(40));
  await setup.context().close();
  for (const viewport of [VIEWPORTS[0]!, VIEWPORTS[1]!]) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    await page.goto(`/klasseokter/${game.sessionId}/meldinger`);
    await expect(page.locator("[data-sent-messages] > li")).toHaveCount(1);
    await expectAccessible(page, viewport.phone);
    await page.context().close();
  }
});
