import path from "node:path";

import { expect, type Locator, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshLecturer, VIEWPORTS } from "./support/classes";

/** The Roster upload on the Class page (Story 4.2, FR-7, UX-DR47, NFR-6), on the local stack, by
 * keyboard only. Each test makes a fresh Lecturer and Class, so the demo Class is never staged.
 * The files under `fixtures/roster` are synthetic, with invented names and addresses, in the
 * column layouts of a Canvas people export and a Canvas grade-book export. */
const copy = nb.classes.roster;
const CSRF = { "X-Requested-With": "olspillet" };
const FIXTURES = path.join(__dirname, "fixtures", "roster");
const fixture = (name: string) => path.join(FIXTURES, name);

/** A fresh Lecturer with a Class of their own, on its page. */
async function classPage(page: Page, browser: Parameters<typeof freshLecturer>[1], text200 = false): Promise<Page> {
  const lecturer = await freshLecturer(page, browser, text200);
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const created = await lecturer.request.post("/api/classes", {
    data: { name: `liste-${Date.now() % 100000}`, institution_id: place.id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  await lecturer.goto(`/klasser/${(await created.json()).id}`);
  await expect(lecturer.getByRole("heading", { level: 2, name: copy.title })).toBeVisible();
  return lecturer;
}

/** The answer to the next `method` request to a path ending in `suffix`. */
function answerTo(page: Page, suffix: string, method = "POST") {
  return page.waitForResponse(
    (r) => new URL(r.url()).pathname.endsWith(suffix) && r.request().method() === method,
  );
}

/** Tab forward until `target` has focus: the keyboard is the only way the tests move. */
async function tabTo(page: Page, target: Locator) {
  for (let presses = 0; presses < 40; presses++) {
    if (await target.evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  await expect(target).toBeFocused();
}

/** Press Enter on the focused «Velg fil» and give the file chooser `file`. */
async function chooseFile(page: Page, file: string) {
  const chooser = page.waitForEvent("filechooser");
  const sent = answerTo(page, "/roster-upload");
  await page.keyboard.press("Enter");
  await (await chooser).setFiles(file);
  return sent;
}

const chooseButton = (page: Page) => page.getByRole("button", { name: copy.chooseFile });
const columnSelect = (page: Page) => page.getByLabel(copy.emailColumn, { exact: true });

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a Lecturer uploads a Canvas export, picks the e-mail column and changes the file, by keyboard", async ({
      page,
      browser,
    }) => {
      const lecturer = await classPage(page, browser, vp.text200);

      // No file yet: the outlined box with «Velg fil» and the link to paste instead.
      await expect(chooseButton(lecturer)).toBeVisible();
      await expect(lecturer.getByRole("button", { name: copy.pasteInstead })).toBeVisible();
      await expect(lecturer.locator("#roster-file")).toHaveAttribute("accept", /\.xlsx/);
      await expect(lecturer.locator("#roster-file")).toHaveAttribute("accept", /\.csv/);
      await expectAccessible(lecturer, vp.phone);

      // A Canvas people export: name, rows read, «Bytt fil», and the e-mail column preselected.
      await tabTo(lecturer, chooseButton(lecturer));
      expect((await chooseFile(lecturer, fixture("canvas-people.xlsx"))).status()).toBe(201);
      await expect(lecturer.getByText("canvas-people.xlsx")).toBeVisible();
      await expect(lecturer.getByText(copy.rowsRead(12))).toBeVisible();
      await expect(lecturer.getByRole("button", { name: copy.changeFile })).toBeVisible();
      await expect(columnSelect(lecturer)).toBeFocused();
      await expect(columnSelect(lecturer)).toHaveValue("3");
      await expect(columnSelect(lecturer).locator("option")).toHaveText([
        "Kolonne A, Name",
        "Kolonne B, Login ID",
        "Kolonne C, SIS User ID",
        "Kolonne D, E-post",
        "Kolonne E, Section",
      ]);
      await expect(lecturer.getByText(`Kolonne D, E-post. ${copy.suggested(12, 12)}`)).toBeVisible();
      await expect(lecturer.getByRole("heading", { name: copy.preview })).toBeVisible();
      await expect(lecturer.getByRole("cell", { name: "sara.lund@stud.example.no" })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      // Another column: the api evaluates the staged rows again, with no new upload.
      const evaluated = answerTo(lecturer, "/roster-upload/column", "PUT");
      await lecturer.keyboard.press("ArrowUp");
      expect((await evaluated).status()).toBe(200);
      await expect(columnSelect(lecturer)).toHaveValue("2");
      await expect(lecturer.getByText(`Kolonne C, SIS User ID. ${copy.chosen(0, 0, 12)}`)).toBeVisible();

      // The staging is the api's: it is there after a reload.
      await lecturer.reload();
      await expect(lecturer.getByText(copy.rowsRead(12))).toBeVisible();
      await expect(columnSelect(lecturer)).toHaveValue("2");

      // «Bytt fil» deletes the staging and gives the empty box back, with focus on «Velg fil».
      const removed = answerTo(lecturer, "/roster-upload", "DELETE");
      await tabTo(lecturer, lecturer.getByRole("button", { name: copy.changeFile }));
      await lecturer.keyboard.press("Enter");
      expect((await removed).status()).toBe(204);
      await expect(chooseButton(lecturer)).toBeFocused();
      await expect(lecturer.getByText(copy.rowsRead(12))).toHaveCount(0);
      await expect(columnSelect(lecturer)).toHaveCount(0);

      // A file that cannot be read says so, stages nothing and keeps focus on «Velg fil».
      expect((await chooseFile(lecturer, fixture("ikke-en-liste.xlsx"))).status()).toBe(422);
      await expect(lecturer.getByRole("alert").filter({ hasText: copy.unreadable })).toBeVisible();
      await expect(chooseButton(lecturer)).toBeFocused();
      await expectAccessible(lecturer, vp.phone);

      // The next file clears the line. One with no e-mail column says so and points to pasting.
      expect((await chooseFile(lecturer, fixture("uten-epost.csv"))).status()).toBe(201);
      await expect(lecturer.getByText(copy.unreadable)).toHaveCount(0);
      await expect(lecturer.getByText(copy.noEmailColumn)).toBeVisible();
      await expect(columnSelect(lecturer)).toHaveValue("");
      await expect(lecturer.getByRole("button", { name: copy.pasteInstead })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
      await lecturer.context().close();
    });
  });
}

/** The invalid-row list: one item per row, read as text. */
const invalidItems = (page: Page) =>
  page.getByRole("region", { name: /^Ugyldige rader/ }).locator("li");
const sendButton = (page: Page, valid: number) => page.getByRole("button", { name: copy.send(valid) });

// Story 4.3: invalid rows and pasted addresses (FR-7, UX-DR47, UX-DR9), by keyboard at each viewport.
for (const vp of VIEWPORTS) {
  test.describe(`invalid rows and paste, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a Lecturer sees the invalid rows, then pastes addresses instead, by keyboard", async ({ page, browser }) => {
      const lecturer = await classPage(page, browser, vp.text200);

      // A file with four broken addresses and one repeat: each row with its number, value and reason.
      await tabTo(lecturer, chooseButton(lecturer));
      expect((await chooseFile(lecturer, fixture("ugyldige-rader.csv"))).status()).toBe(201);
      await expect(lecturer.getByRole("heading", { name: copy.invalidTitle(5, 8) })).toBeVisible();
      await expect(invalidItems(lecturer)).toHaveCount(5);
      const lines = [
        ["4", "emma.solberg@stud", copy.reasons.missing_domain],
        ["5", "jakob.lien(at)stud.example.no", copy.reasons.missing_at],
        ["6", "thea.moe@@stud.example.no", copy.reasons.two_at],
        ["7", "", copy.reasons.empty],
        ["9", "Sara.Lund@stud.example.no", copy.duplicate(2)],
      ];
      for (const [index, [row, value, reason]] of lines.entries()) {
        const item = invalidItems(lecturer).nth(index);
        await expect(item).toContainText(row);
        if (value) await expect(item).toContainText(value);
        await expect(item).toContainText(reason);
        await expect(item.getByRole("button", { name: new RegExp(`^${copy.registerManually}`) })).toBeVisible();
      }
      await expect(sendButton(lecturer, 3)).toBeVisible();
      await expect(sendButton(lecturer, 3)).not.toHaveAttribute("aria-disabled", "true");
      await expect(lecturer.getByText(copy.invalidNote)).toBeVisible();
      // The preview marks the chosen column by its tint alone: no visible suffix (Issue #85).
      await expect(lecturer.getByRole("columnheader", { name: /E-post/ })).toHaveText(/^C E-post, valgt som e-postkolonne$/);
      await expect(lecturer.getByText("(e-post)")).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);

      // A column with no address: its reason is an error, and nothing can be sent.
      const evaluated = answerTo(lecturer, "/roster-upload/column", "PUT");
      await tabTo(lecturer, columnSelect(lecturer));
      await lecturer.keyboard.press("ArrowUp");
      expect((await evaluated).status()).toBe(200);
      await expect(columnSelect(lecturer)).toHaveAttribute("aria-invalid", "true");
      await expect(lecturer.locator("#roster-column-error")).toHaveText(`Kolonne B, Student-ID. ${copy.chosen(0, 0, 8)}`);
      // The invalid-row list names the chosen column, not «E-post» (Issue #86).
      await expect(invalidItems(lecturer).first()).toContainText(`${copy.invalidValue("Student-ID", "B")}:`);
      await expect(sendButton(lecturer, 0)).toHaveAttribute("aria-disabled", "true");
      await expect(lecturer.getByText(copy.noValid)).toBeVisible();

      // «Bytt fil», then paste: split on separators, `Navn <adresse>` read as the address.
      await tabTo(lecturer, lecturer.getByRole("button", { name: copy.changeFile }));
      await lecturer.keyboard.press("Enter");
      await expect(chooseButton(lecturer)).toBeFocused();
      await tabTo(lecturer, lecturer.getByRole("button", { name: copy.pasteInstead }));
      await lecturer.keyboard.press("Enter");
      const field = lecturer.getByLabel(copy.pasteLabel, { exact: true });
      await expect(field).toBeFocused();
      await lecturer.keyboard.type("ola@stud.example.no, Kari Berg <kari@stud.example.no>; feil(at)stud.example.no");
      const sent = answerTo(lecturer, "/roster-paste");
      await tabTo(lecturer, lecturer.getByRole("button", { name: copy.pasteContinue }));
      await lecturer.keyboard.press("Enter");
      expect((await sent).status()).toBe(201);
      await expect(lecturer.getByText(copy.addressesRead(3))).toBeFocused();
      await expect(lecturer.getByText(copy.pasted)).toBeVisible();
      await expect(lecturer.getByRole("heading", { name: copy.invalidTitle(1, 3) })).toBeVisible();
      await expect(invalidItems(lecturer).first()).toContainText(copy.reasons.missing_at);
      await expect(sendButton(lecturer, 2)).toBeVisible();
      await expect(columnSelect(lecturer)).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);

      // An empty paste: nothing valid, and the page says so.
      await tabTo(lecturer, lecturer.getByRole("button", { name: copy.startOver }));
      await lecturer.keyboard.press("Enter");
      await expect(chooseButton(lecturer)).toBeFocused();
      await tabTo(lecturer, lecturer.getByRole("button", { name: copy.pasteInstead }));
      await lecturer.keyboard.press("Enter");
      const empty = answerTo(lecturer, "/roster-paste");
      await tabTo(lecturer, lecturer.getByRole("button", { name: copy.pasteContinue }));
      await lecturer.keyboard.press("Enter");
      expect((await empty).status()).toBe(201);
      await expect(sendButton(lecturer, 0)).toHaveAttribute("aria-disabled", "true");
      await expect(lecturer.getByText(copy.noValid)).toBeVisible();
      // No rows, so no note about invalid rows (Issue #86).
      await expect(lecturer.getByText(copy.invalidNote)).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.context().close();
    });
  });
}

test.describe("files and paste", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("a Canvas grade-book export is read without editing", async ({ page, browser }) => {
    const lecturer = await classPage(page, browser);
    await tabTo(lecturer, chooseButton(lecturer));
    expect((await chooseFile(lecturer, fixture("canvas-gradebook.csv"))).status()).toBe(201);
    await expect(lecturer.getByText(copy.rowsRead(13))).toBeVisible();
    await expect(columnSelect(lecturer)).toHaveValue("3");
    await expect(lecturer.getByText(`Kolonne D, SIS Login ID. ${copy.suggested(12, 13)}`)).toBeVisible();
    await expect(lecturer.getByText("Valgt fordi alle rader unntatt én er gyldige adresser.", { exact: false })).toBeVisible();
    await lecturer.context().close();
  });

  test("a file with more than 100 invalid rows lists the first 100 and counts them all", async ({ page, browser }) => {
    const lecturer = await classPage(page, browser);
    await tabTo(lecturer, chooseButton(lecturer));
    expect((await chooseFile(lecturer, fixture("mange-ugyldige.csv"))).status()).toBe(201);
    await expect(lecturer.getByRole("heading", { name: copy.invalidTitle(130, 150) })).toBeVisible();
    await expect(invalidItems(lecturer)).toHaveCount(100);
    await expect(invalidItems(lecturer).last()).toContainText("101");
    await expect(lecturer.getByText(copy.invalidShown(100, 130))).toBeVisible();
    await expect(sendButton(lecturer, 20)).toBeVisible();
    await lecturer.context().close();
  });

  test("a refused paste says so under the field and the line clears as the user types", async ({ page, browser }) => {
    const lecturer = await classPage(page, browser);
    // The api's answer to text over the limits, without sending megabytes through the test.
    await lecturer.route("**/roster-paste", (route) =>
      route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "roster_paste_too_long", message: "The pasted text is too long." } }),
      }),
    );
    await tabTo(lecturer, lecturer.getByRole("button", { name: copy.pasteInstead }));
    await lecturer.keyboard.press("Enter");
    const field = lecturer.getByLabel(copy.pasteLabel, { exact: true });
    await lecturer.keyboard.type("a@stud.example.no");
    await tabTo(lecturer, lecturer.getByRole("button", { name: copy.pasteContinue }));
    await lecturer.keyboard.press("Enter");
    await expect(lecturer.getByRole("alert").filter({ hasText: copy.pasteTooLong })).toBeVisible();
    await expect(field).toHaveAttribute("aria-invalid", "true");
    await expectAccessible(lecturer, false);
    await field.focus();
    await lecturer.keyboard.type(" ");
    await expect(lecturer.getByText(copy.pasteTooLong)).toHaveCount(0);
    await expect(field).not.toHaveAttribute("aria-invalid", "true");
    await lecturer.context().close();
  });

  test("«Lim inn adresser i stedet» opens the multi-line field and «Velg fil i stedet» goes back", async ({
    page,
    browser,
  }) => {
    const lecturer = await classPage(page, browser);
    await tabTo(lecturer, lecturer.getByRole("button", { name: copy.pasteInstead }));
    await lecturer.keyboard.press("Enter");
    const field = lecturer.getByLabel(copy.pasteLabel, { exact: true });
    await expect(field).toBeFocused();
    await expect(field).toHaveJSProperty("tagName", "TEXTAREA");
    await expectAccessible(lecturer, false);
    await tabTo(lecturer, lecturer.getByRole("button", { name: copy.fileInstead }));
    await lecturer.keyboard.press("Enter");
    await expect(chooseButton(lecturer)).toBeFocused();
    await lecturer.context().close();
  });
});
