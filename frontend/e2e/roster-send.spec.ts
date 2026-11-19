import { expect, type Locator, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { latestMail, nextMail } from "./support/auth";
import { expectAccessible, freshLecturer, type Viewport } from "./support/classes";

/** Sending Invitations to the Roster (Story 4.4, FR-8, UX-DR47, UX-DR56, NFR-6), on the local
 * stack, by keyboard only, at 320 and 1440 px. Each test makes a fresh Lecturer and Class, so the
 * demo Class's Roster is never touched; the addresses are invented and unique per run. The mail
 * check needs `worker-batch` running. */
const copy = nb.classes.roster;
const CSRF = { "X-Requested-With": "olspillet" };

const SEND_VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

/** A fresh Lecturer with a Class of their own, on its page; the Class's name. */
async function classPage(page: Page, browser: Parameters<typeof freshLecturer>[1]) {
  const lecturer = await freshLecturer(page, browser);
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const name = `send-${Date.now() % 100000}`;
  const created = await lecturer.request.post("/api/classes", {
    data: { name, institution_id: place.id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  await lecturer.goto(`/klasser/${(await created.json()).id}`);
  await expect(lecturer.getByRole("heading", { level: 2, name: copy.title })).toBeVisible();
  return { lecturer, name };
}

function answerTo(page: Page, suffix: string) {
  return page.waitForResponse(
    (r) => new URL(r.url()).pathname.endsWith(suffix) && r.request().method() === "POST",
  );
}

async function tabTo(page: Page, target: Locator) {
  for (let presses = 0; presses < 40; presses++) {
    if (await target.evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  await expect(target).toBeFocused();
}

/** «Lim inn adresser i stedet», type `text`, «Fortsett». */
async function pasteAddresses(page: Page, text: string) {
  await tabTo(page, page.getByRole("button", { name: copy.pasteInstead }));
  await page.keyboard.press("Enter");
  await expect(page.getByLabel(copy.pasteLabel, { exact: true })).toBeFocused();
  await page.keyboard.type(text);
  const staged = answerTo(page, "/roster-paste");
  await tabTo(page, page.getByRole("button", { name: copy.pasteContinue }));
  await page.keyboard.press("Enter");
  expect((await staged).status()).toBe(201);
}

for (const vp of SEND_VIEWPORTS) {
  test.describe(`send, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a Lecturer sends Invitations with a validity, by keyboard, and sees the Roster count", async ({
      page,
      browser,
    }) => {
      const { lecturer, name } = await classPage(page, browser);
      const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
      const ola = `ola-${tag}@stud.example.no`;
      const kari = `kari-${tag}@stud.example.no`;
      await pasteAddresses(lecturer, `${ola}, ${kari}; feil(at)stud.example.no`);

      // The send form: the validity prefilled with 14 days and the range under it.
      const days = lecturer.getByLabel(copy.validDays, { exact: true });
      await expect(days).toHaveValue("14");
      await expect(lecturer.getByText(copy.validDaysHint(1, 60))).toBeVisible();
      const send = lecturer.getByRole("button", { name: copy.send(2) });
      await expect(send).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      // A validity outside the range is refused under the field, and nothing is sent.
      let posted = 0;
      lecturer.on("request", (r) => {
        if (r.method() === "POST" && new URL(r.url()).pathname.endsWith("/invitations")) posted += 1;
      });
      await tabTo(lecturer, days);
      await lecturer.keyboard.press("ControlOrMeta+a");
      await lecturer.keyboard.type("61");
      await lecturer.keyboard.press("Enter");
      await expect(lecturer.getByText(copy.validDaysError(1, 60))).toBeVisible();
      await expect(days).toHaveAttribute("aria-invalid", "true");
      expect(posted).toBe(0);
      await expectAccessible(lecturer, vp.phone);
      // The refusal clears as the Lecturer types.
      await lecturer.keyboard.press("Backspace");
      await expect(lecturer.getByText(copy.validDaysError(1, 60))).toHaveCount(0);
      await lecturer.keyboard.press("Backspace");
      await lecturer.keyboard.type("7");

      // Send: the result line takes focus, and the box is empty again.
      const before = vp.phone ? null : await latestMail(lecturer, ola);
      const sent = answerTo(lecturer, "/invitations");
      await tabTo(lecturer, send);
      await lecturer.keyboard.press("Enter");
      const answer = await sent;
      expect(answer.status()).toBe(201);
      expect(((await answer.json()) as { sent: number; valid_days: number }).valid_days).toBe(7);
      const result = lecturer.getByRole("status").filter({ hasText: /^2 Invitasjoner sendt\. Gyldige til og med / });
      await expect(result).toBeFocused();
      await expect(lecturer.getByRole("button", { name: copy.chooseFile })).toBeVisible();
      await expect(lecturer.getByText(copy.onRosterCount(2))).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      // «Klassene dine» on the Lærerhjem counts the Roster.
      await tabTo(lecturer, lecturer.getByRole("link", { name: nb.homes.lecturerHome }).first());
      await lecturer.keyboard.press("Enter");
      const item = lecturer.getByRole("listitem").filter({ has: lecturer.getByRole("link", { name }) });
      await expect(item).toContainText(nb.classes.home.rosterCount(2));
      await expectAccessible(lecturer, vp.phone);

      if (!vp.phone) {
        // The one mail check: Norwegian, headed «ØL-spillet», naming the Class and the last day.
        const mail = await nextMail(lecturer, ola, before);
        expect(mail.text.startsWith("ØL-spillet")).toBe(true);
        expect(mail.text).toContain(`Klassen ${name}`);
        expect(mail.text).toMatch(/gyldig til og med \d{1,2}\. [a-z]+ \d{4}/);
        expect(mail.text).toMatch(/\/invitasjon#[A-Za-z0-9_-]+/);
      }
      await lecturer.context().close();
    });
  });
}

/** Stage a two-column file (`Navn`, `E-post`) with two valid addresses through the api. */
async function stageFile(page: Page, classId: string, tag: string) {
  const body = ["Navn,E-post", `Ola,ola-${tag}@stud.example.no`, `Kari,kari-${tag}@stud.example.no`].join("\n");
  const staged = await page.request.post(`/api/classes/${classId}/roster-upload`, {
    data: Buffer.from(body),
    headers: { ...CSRF, "Content-Type": "application/octet-stream", "X-File-Name": "liste.csv" },
  });
  expect(staged.status()).toBe(201);
}

test.describe("a refused send", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("a staging replaced under the page: the line stays and the new staging shows", async ({ page, browser }) => {
    const { lecturer } = await classPage(page, browser);
    const classId = new URL(lecturer.url()).pathname.split("/").pop()!;
    const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
    await stageFile(lecturer, classId, tag);
    await lecturer.reload();
    const send = lecturer.getByRole("button", { name: copy.send(2) });
    await expect(send).toBeVisible();

    // Another tab replaces the staging: the page still holds the old one's id.
    const pasted = await lecturer.request.post(`/api/classes/${classId}/roster-paste`, {
      data: { text: `per-${tag}@stud.example.no` },
      headers: CSRF,
    });
    expect(pasted.status()).toBe(201);

    const refused = answerTo(lecturer, "/invitations");
    await tabTo(lecturer, send);
    await lecturer.keyboard.press("Enter");
    expect((await refused).status()).toBe(404);
    await expect(lecturer.getByRole("alert").filter({ hasText: copy.sendGone })).toBeVisible();
    // The page reloads the staging the api has now, and the line outlives the old send area.
    await expect(lecturer.getByText(copy.pasted)).toBeVisible();
    await expect(lecturer.getByRole("button", { name: copy.send(1) })).toBeVisible();
    await expect(lecturer.getByRole("alert").filter({ hasText: copy.sendGone })).toBeVisible();
    await expectAccessible(lecturer, false);
    await lecturer.context().close();
  });

  test("a staging with no valid row left: the line says why and the button is unavailable", async ({
    page,
    browser,
  }) => {
    const { lecturer } = await classPage(page, browser);
    const classId = new URL(lecturer.url()).pathname.split("/").pop()!;
    const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
    await stageFile(lecturer, classId, tag);
    await lecturer.reload();
    const send = lecturer.getByRole("button", { name: copy.send(2) });
    await expect(send).toBeVisible();

    // Another tab picks the name column: the same staging, with no valid row.
    const chosen = await lecturer.request.put(`/api/classes/${classId}/roster-upload/column`, {
      data: { column: 0 },
      headers: CSRF,
    });
    expect(chosen.status()).toBe(200);

    const refused = answerTo(lecturer, "/invitations");
    await tabTo(lecturer, send);
    await lecturer.keyboard.press("Enter");
    expect((await refused).status()).toBe(422);
    await expect(lecturer.getByRole("alert").filter({ hasText: copy.nothingToSend })).toBeVisible();
    await expect(lecturer.getByRole("button", { name: copy.send(0) })).toHaveAttribute("aria-disabled", "true");
    // The refetched staging says it once under the button; the refusal does not repeat it.
    await expect(lecturer.getByText(copy.noValid, { exact: true })).toHaveCount(1);
    await expectAccessible(lecturer, false);
    await lecturer.context().close();
  });
});
